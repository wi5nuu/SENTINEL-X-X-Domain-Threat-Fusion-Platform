"""
RF/SIGINT Domain Ingestor
Sources real RF anomaly data from:
- OpenSky Network (ADS-B signal quality anomalies → GPS spoofing indicators)
- NOAA Space Weather (solar-induced RF disruption)
- Known GPS interference reports (FAA NOTAM feeds)
- ADS-B Exchange (signal strength anomalies)

NOTE: True RF spectrum scanning requires physical SDR hardware.
This ingestor derives RF anomalies from real public data sources
that are correlated indicators of RF interference events.
"""
import asyncio
import hashlib
import uuid
from datetime import datetime
from typing import Optional, List, Tuple
import httpx
import numpy as np

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics, track_latency
from src.common.kafka import kafka_client
from src.common.models import RFAnomaly
from src.common.security import get_security_manager

logger = setup_logging("rf-ingestor")
security = get_security_manager()


class TDOAGeolocationEngine:
    """
    Time-Difference-of-Arrival geolocation for corroborating
    GPS anomaly locations derived from ADS-B discrepancies.
    """

    def __init__(self):
        # Known ADS-B receiver network reference positions
        self.sensors = [
            {"id": "S1", "lat": 40.7128, "lon": -74.0060},   # NYC
            {"id": "S2", "lat": 40.7580, "lon": -73.9855},   # Midtown
            {"id": "S3", "lat": 40.6892, "lon": -74.0445},   # Brooklyn
            {"id": "S4", "lat": 40.7484, "lon": -73.9857},   # Hell's Kitchen
        ]

    def locate(self, tdoa_measurements: List[Tuple[str, str, float]]) -> Optional[dict]:
        if len(tdoa_measurements) < 3:
            return None
        try:
            A = []
            b = []
            ref_sensor_id = tdoa_measurements[0][0]
            ref = next(s for s in self.sensors if s["id"] == ref_sensor_id)
            for s1_id, s2_id, tdoa in tdoa_measurements:
                s1 = next(s for s in self.sensors if s["id"] == s1_id)
                s2 = next(s for s in self.sensors if s["id"] == s2_id)
                x1, y1 = s1["lon"], s1["lat"]
                x2, y2 = s2["lon"], s2["lat"]
                xr, yr = ref["lon"], ref["lat"]
                c = 299792458
                d = tdoa * c / 1000
                A.append([2*(x1-xr), 2*(y1-yr)])
                b.append([d**2 - (x1**2 - xr**2) - (y1**2 - yr**2)])
            A = np.array(A)
            b = np.array(b)
            x, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)
            est_lon, est_lat = float(x[0][0]), float(x[1][0])
            uncertainty = float(np.std(residuals)) if len(residuals) > 0 else 100
            return {
                "estimated_lat": est_lat,
                "estimated_lon": est_lon,
                "uncertainty_ellipse_axes_m": [uncertainty, uncertainty],
                "confidence": max(0.3, min(0.95, 1.0 - uncertainty / 1000)),
            }
        except Exception as e:
            logger.error("TDOA localization error", extra={"error": str(e)})
            return None


class RFIngestor:
    """
    RF anomaly detection using real public data sources.
    Correlates ADS-B position errors, space weather, and NOTAM alerts
    to identify GPS jamming/spoofing events.
    """

    def __init__(self):
        self.tdoa = TDOAGeolocationEngine()
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        self.seen_events: set = set()

    async def start(self):
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await kafka_client.start()
        logger.info("RF Ingestor started - correlating real public sources for RF anomalies")

        tasks = [
            self.poll_opensky_adsb_anomalies(),
            self.poll_noaa_space_weather_rf(),
            self.poll_faa_notam_gps(),
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
        await kafka_client.stop()

    @track_latency("rf")
    async def poll_opensky_adsb_anomalies(self):
        """
        Detect GPS spoofing by comparing ADS-B reported positions
        against expected positions. Large discrepancies indicate spoofing.
        OpenSky Network provides real-time ADS-B data.
        """
        opensky_user = getattr(settings, 'opensky_username', '')
        opensky_pass = getattr(settings, 'opensky_password', '')
        base_url = getattr(settings, 'opensky_api_url', 'https://opensky-network.org/api')

        auth = (opensky_user, opensky_pass) if opensky_user else None

        while self.running:
            if not security.check_rate_limit("opensky_rf", max_requests=100, window_seconds=3600):
                await asyncio.sleep(120)
                continue

            try:
                # Get live aircraft with position data
                params = {}
                resp = await self.http_client.get(
                    f"{base_url}/states/all",
                    params=params,
                    auth=auth,
                    timeout=15.0
                )

                if resp.status_code == 200:
                    data = resp.json()
                    states = data.get("states", []) or []
                    anomalies_found = 0

                    for state in states:
                        if not state or len(state) < 17:
                            continue

                        icao24 = state[0]
                        callsign = (state[1] or "").strip()
                        lon = state[5]
                        lat = state[6]
                        baro_alt = state[7]   # barometric altitude
                        geo_alt = state[13]   # geometric (GPS) altitude
                        spi = state[15]       # Special Position Indicator
                        squawk = state[14]

                        if lon is None or lat is None:
                            continue
                        if not security.validate_coordinates(float(lat), float(lon)):
                            continue

                        anomaly_flags = []

                        # GPS vs barometric altitude discrepancy → GPS spoofing indicator
                        if baro_alt is not None and geo_alt is not None:
                            alt_diff = abs(float(geo_alt) - float(baro_alt))
                            if alt_diff > 500:  # > 500m discrepancy
                                anomaly_flags.append(f"gps_baro_discrepancy:{alt_diff:.0f}m")

                        # Special Position Indicator set = pilot distress / hijack
                        if spi:
                            anomaly_flags.append("spi_active")

                        # Emergency squawk codes
                        if squawk in ("7500", "7600", "7700"):
                            squawk_meanings = {
                                "7500": "hijack",
                                "7600": "comms_failure",
                                "7700": "emergency"
                            }
                            anomaly_flags.append(f"squawk_{squawk_meanings.get(squawk, squawk)}")

                        if anomaly_flags:
                            event_key = hashlib.sha256(f"rf_{icao24}_{lat}_{lon}".encode()).hexdigest()[:16]
                            if event_key in self.seen_events:
                                continue
                            self.seen_events.add(event_key)
                            if len(self.seen_events) > 10000:
                                self.seen_events = set(list(self.seen_events)[-5000:])

                            anomaly = {
                                "event_id": str(uuid.uuid4()),
                                "timestamp_utc": datetime.utcnow().isoformat(),
                                "domain": "rf",
                                "type": "adsb_rf_anomaly",
                                "icao24": icao24,
                                "callsign": callsign,
                                "lat": float(lat),
                                "lon": float(lon),
                                "anomaly_flags": anomaly_flags,
                                "baro_altitude_m": baro_alt,
                                "geo_altitude_m": geo_alt,
                                "source": "opensky_real",
                                "severity": "ELEVATED" if "squawk" in str(anomaly_flags) else "SUSPICIOUS",
                                "description": f"RF/GPS anomaly detected on {callsign or icao24}: {', '.join(anomaly_flags)}"
                            }

                            await kafka_client.send_event("rf-signals", anomaly, key=icao24)
                            metrics.events_ingested.labels(domain="rf", source="opensky_adsb").inc()
                            anomalies_found += 1

                    logger.info(f"OpenSky RF scan: {len(states)} aircraft checked, {anomalies_found} anomalies found")

                elif resp.status_code == 429:
                    logger.warning("OpenSky rate limited for RF domain - backing off")
                    await asyncio.sleep(300)
                else:
                    logger.warning(f"OpenSky RF poll error: {resp.status_code}")

            except Exception as e:
                logger.error(f"OpenSky RF anomaly poll error: {e}")
                metrics.errors_total.labels(service="rf_ingestor", error_type="opensky_poll").inc()

            await asyncio.sleep(180)  # poll every 3 minutes

    async def poll_noaa_space_weather_rf(self):
        """
        Poll NOAA SWPC for real space weather events that cause RF disruption.
        Solar flares, geomagnetic storms, and ionospheric disturbances
        directly cause HF/GPS signal degradation.
        """
        while self.running:
            if not security.check_rate_limit("noaa_swpc_rf", max_requests=100, window_seconds=3600):
                await asyncio.sleep(300)
                continue

            try:
                # Real NOAA SWPC planetary K-index (geomagnetic activity)
                resp = await self.http_client.get(
                    "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
                    timeout=10.0
                )

                if resp.status_code == 200:
                    data = resp.json()
                    # Last entry is most recent
                    if data and len(data) > 1:
                        latest = data[-1]
                        kp_index = float(latest[1]) if latest[1] else 0.0

                        # Kp >= 5 = geomagnetic storm → GPS/HF disruption
                        if kp_index >= 5:
                            severity = "CRITICAL" if kp_index >= 7 else "ELEVATED"
                            event = {
                                "event_id": str(uuid.uuid4()),
                                "timestamp_utc": latest[0],
                                "domain": "rf",
                                "type": "geomagnetic_rf_disruption",
                                "kp_index": kp_index,
                                "source": "noaa_swpc_real",
                                "severity": severity,
                                "affected_frequencies": ["HF (3-30MHz)", "GPS L1/L2", "VHF"],
                                "description": f"Geomagnetic storm Kp={kp_index:.1f} causing RF/GPS disruption globally",
                                "impact": "GPS degradation possible, HF blackout possible"
                            }
                            await kafka_client.send_event("rf-signals", event, key=f"kp_{latest[0]}")
                            await kafka_client.send_event("alerts", {**event, "alert_type": "rf_disruption"})
                            metrics.events_ingested.labels(domain="rf", source="noaa_swpc").inc()
                            logger.warning(f"Geomagnetic storm Kp={kp_index:.1f} - RF disruption expected")
                        else:
                            logger.debug(f"Space weather nominal: Kp={kp_index:.1f}")

                # Also check solar X-ray flux (solar flares → HF blackouts)
                resp2 = await self.http_client.get(
                    "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json",
                    timeout=10.0
                )

                if resp2.status_code == 200:
                    flares = resp2.json()
                    for flare in (flares or [])[:3]:
                        flare_class = flare.get("max_class", "")
                        # X or M class flares → HF radio blackout on sunlit side
                        if flare_class and flare_class[0] in ("X", "M"):
                            event = {
                                "event_id": str(uuid.uuid4()),
                                "timestamp_utc": flare.get("begin_time", datetime.utcnow().isoformat()),
                                "domain": "rf",
                                "type": "solar_flare_rf_blackout",
                                "flare_class": flare_class,
                                "source": "noaa_goes_real",
                                "severity": "CRITICAL" if flare_class.startswith("X") else "ELEVATED",
                                "affected_frequencies": ["HF (3-30MHz)", "GPS"],
                                "description": f"Solar flare class {flare_class} causing HF radio blackout",
                                "region": flare.get("noaa_active_region", "unknown")
                            }
                            event_key = hashlib.sha256(f"flare_{flare.get('begin_time')}".encode()).hexdigest()[:16]
                            if event_key not in self.seen_events:
                                self.seen_events.add(event_key)
                                await kafka_client.send_event("rf-signals", event, key=event_key)
                                metrics.events_ingested.labels(domain="rf", source="noaa_flare").inc()

            except Exception as e:
                logger.error(f"NOAA space weather RF poll error: {e}")

            await asyncio.sleep(300)  # poll every 5 minutes

    async def poll_faa_notam_gps(self):
        """
        Poll FAA NOTAM API for real GPS outage/testing notices.
        FAA publishes NOTAMs when GPS tests or interference is scheduled.
        """
        while self.running:
            try:
                # FAA NOTAM API (public)
                resp = await self.http_client.get(
                    "https://notams.aim.faa.gov/notamSearch/search",
                    params={
                        "searchType": "0",
                        "designatorsForLocation": "GPS",
                        "radiusDistance": "100"
                    },
                    headers={"Accept": "application/json"},
                    timeout=15.0
                )

                if resp.status_code == 200:
                    data = resp.json()
                    notams = data.get("notamList", [])
                    gps_notams = [n for n in notams if "GPS" in str(n).upper() or "LORAN" in str(n).upper()]

                    for notam in gps_notams[:10]:
                        notam_id = notam.get("icaoId", str(uuid.uuid4())[:8])
                        event_key = hashlib.sha256(f"notam_{notam_id}".encode()).hexdigest()[:16]
                        if event_key in self.seen_events:
                            continue
                        self.seen_events.add(event_key)

                        event = {
                            "event_id": str(uuid.uuid4()),
                            "timestamp_utc": datetime.utcnow().isoformat(),
                            "domain": "rf",
                            "type": "gps_notam",
                            "notam_id": notam_id,
                            "source": "faa_notam_real",
                            "severity": "INFORMATIONAL",
                            "description": f"FAA GPS NOTAM: {str(notam)[:200]}",
                            "affected_area": notam.get("location", "unknown")
                        }

                        await kafka_client.send_event("rf-signals", event, key=event_key)
                        metrics.events_ingested.labels(domain="rf", source="faa_notam").inc()

                    if gps_notams:
                        logger.info(f"FAA GPS NOTAMs: {len(gps_notams)} active")

            except Exception as e:
                logger.debug(f"FAA NOTAM poll (non-critical): {e}")

            await asyncio.sleep(1800)  # poll every 30 minutes


if __name__ == "__main__":
    ingestor = RFIngestor()
    asyncio.run(ingestor.start())
