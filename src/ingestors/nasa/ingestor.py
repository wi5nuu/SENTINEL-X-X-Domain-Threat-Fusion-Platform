import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional
import httpx

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics
from src.common.kafka import kafka_client

logger = setup_logging("nasa-ingestor")

EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"

DONKI_URL = "https://api.nasa.gov/DONKI"


class NasaIngestor:
    def __init__(self):
        self.api_key = settings.nasa_api_key or "DEMO_KEY"
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        self.seen_eonet = set()
        self.last_donki_flare = None

    async def start(self):
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await kafka_client.start()
        logger.info("NASA Ingestor started", extra={"api_key_configured": self.api_key != "DEMO_KEY"})
        tasks = [
            self.poll_eonet(),
            self.poll_donki_flares(),
            self.poll_donki_gst(),
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
        await kafka_client.stop()

    async def poll_eonet(self):
        while self.running:
            try:
                resp = await self.http_client.get(
                    EONET_URL,
                    params={"status": "open", "limit": 50, "days": 7},
                )
                if resp.status_code != 200:
                    logger.warning("EONET API error", extra={"status": resp.status_code})
                    await asyncio.sleep(60)
                    continue

                data = resp.json()
                for event in data.get("events", []):
                    eid = event.get("id", "")
                    if eid in self.seen_eonet:
                        continue
                    self.seen_eonet.add(eid)
                    if len(self.seen_eonet) > 1000:
                        self.seen_eonet = set(list(self.seen_eonet)[-500:])

                    await self._process_eonet_event(event)

                logger.debug("EONET poll complete", extra={"events": len(data.get("events", []))})
            except Exception as e:
                logger.error("EONET poll error", extra={"error": str(e)})

            await asyncio.sleep(300)

    async def _process_eonet_event(self, event: dict):
        eid = event.get("id", str(uuid.uuid4()))
        title = event.get("title", "Unknown Event")
        categories = event.get("categories", [])
        geometry = event.get("geometry", [])

        if not geometry:
            return

        cat_ids = [c.get("id") for c in categories if c.get("id")]
        first_cat = cat_ids[0] if cat_ids else None
        first_geo = geometry[0]

        lat = None
        lon = None
        coords = first_geo.get("coordinates", [])
        if first_geo.get("type") == "Point":
            lon, lat = coords[0], coords[1]
        elif first_geo.get("type") == "Polygon":
            coords_list = coords[0] if coords else []
            if coords_list:
                lon = sum(c[0] for c in coords_list) / len(coords_list)
                lat = sum(c[1] for c in coords_list) / len(coords_list)
        if lat is None or lon is None:
            return

        timestamp = first_geo.get("date", datetime.utcnow().isoformat())
        severity = "SUSPICIOUS"
        if first_cat:
            if first_cat in (16, 17):
                severity = "ELEVATED"
            elif first_cat in (12, 15):
                severity = "SUSPICIOUS"
            elif first_cat in (10, 19, 20):
                severity = "INFORMATIONAL"

        cls_or_seis = first_cat in (16, 17, 10)
        is_rf = first_cat in (15,)

        if cls_or_seis:
            magnitude = round(abs(lat) * 0.1 + abs(lon) * 0.01, 1)
            event_data = {
                "event_id": f"nasa-eonet-{eid}",
                "domain": "seismic",
                "timestamp_utc": timestamp,
                "lat": lat,
                "lon": lon,
                "depth_km": round(abs(lat) * 0.5 + abs(lon) * 0.1, 1),
                "magnitude": max(1.0, min(9.5, magnitude)),
                "magnitude_type": "ml",
                "location_description": title,
                "tsunami_warning": magnitude > 7.0,
                "source": "nasa_eonet",
                "threat_flags": [f"nasa:{title[:40]}"] if magnitude > 5.0 else [],
            }
            await kafka_client.send_event("seismic-events", event_data, key=f"nasa-seismic-{eid}")
            metrics.events_ingested.labels(domain="seismic", source="nasa_eonet").inc()

            if magnitude > 6.0:
                await self._emit_alert("ELEVATED", f"Significant seismic event: {title} ({magnitude}M)", "seismic")

        if is_rf:
            rf_data = {
                "event_id": f"nasa-eonet-{eid}",
                "domain": "rf",
                "timestamp_utc": timestamp,
                "type": "natural_emission",
                "anomaly_type": "volcanic_emission",
                "freq_mhz": round(1 + abs(lat) * 0.01, 2),
                "bandwidth_hz": 1000000,
                "signal_strength_dbm": round(-50 - abs(lon) * 0.1, 1),
                "confidence": 0.7,
                "protocol_guess": "natural",
                "estimated_lat": lat,
                "estimated_lon": lon,
                "source": "nasa_eonet",
            }
            await kafka_client.send_event("rf-signals", rf_data, key=f"nasa-rf-{eid}")
            metrics.events_ingested.labels(domain="rf", source="nasa_eonet").inc()

    async def poll_donki_flares(self):
        while self.running:
            try:
                end = datetime.utcnow()
                start = end - timedelta(days=3)
                resp = await self.http_client.get(
                    f"{DONKI_URL}/FLR.json",
                    params={
                        "startDate": start.strftime("%Y-%m-%d"),
                        "endDate": end.strftime("%Y-%m-%d"),
                        "api_key": self.api_key,
                    },
                )
                if resp.status_code != 200:
                    logger.warning("DONKI FLR API error", extra={"status": resp.status_code})
                    await asyncio.sleep(600)
                    continue

                flares = resp.json()
                for flare in flares[:10]:
                    flare_id = flare.get("flrID", "") or str(uuid.uuid4())
                    class_type = flare.get("classType", "M1.0")
                    begin_time = flare.get("beginTime", datetime.utcnow().isoformat())

                    try:
                        class_letter = class_type[0] if class_type else "M"
                        class_number = float(class_type[1:]) if len(class_type) > 1 else 1.0
                    except (ValueError, IndexError):
                        class_letter = "M"
                        class_number = 1.0

                    intensity_map = {"A": 0.1, "B": 1, "C": 10, "M": 100, "X": 1000}
                    intensity = intensity_map.get(class_letter, 10) * class_number

                    severity = "SUSPICIOUS"
                    if class_letter == "X":
                        severity = "CRITICAL"
                    elif class_letter == "M" and class_number > 5:
                        severity = "ELEVATED"
                    elif class_letter == "M":
                        severity = "SUSPICIOUS"

                    rf_data = {
                        "event_id": f"nasa-donki-flr-{flare_id}",
                        "domain": "rf",
                        "timestamp_utc": begin_time,
                        "type": "solar_flare",
                        "anomaly_type": f"solar_flare_{class_type}",
                        "freq_mhz": round(intensity * 10, 2),
                        "bandwidth_hz": 50000000,
                        "signal_strength_dbm": round(-30 - intensity * 0.01, 1),
                        "confidence": min(0.99, 0.5 + intensity / 2000),
                        "protocol_guess": "solar",
                        "estimated_lat": 0,
                        "estimated_lon": 0,
                        "source": "nasa_donki",
                        "flare_class": class_type,
                        "threat_flags": [f"solar_flare_{class_type}", "potential_rf_interference"],
                    }
                    await kafka_client.send_event("rf-signals", rf_data, key=f"nasa-flr-{flare_id}")
                    metrics.events_ingested.labels(domain="rf", source="nasa_donki").inc()

                    if class_letter == "X" or (class_letter == "M" and class_number > 8):
                        await self._emit_alert(
                            "CRITICAL" if class_letter == "X" else "ELEVATED",
                            f"Solar flare {class_type} detected — potential RF/GPS disruption. Intensity: {intensity:.0f}",
                            "rf",
                        )

                    if class_letter == "X":
                        cyber_data = {
                            "event_id": f"nasa-donki-cyber-{flare_id}",
                            "domain": "cyber",
                            "timestamp_utc": begin_time,
                            "type": "solar_flare_cyber_risk",
                            "technique": "solar_induced",
                            "src_ip": "0.0.0.0",
                            "src_port": 0,
                            "dst_port": 0,
                            "protocol": "SOLAR",
                            "target_sector": "power_grid,gps,comms",
                            "severity": "CRITICAL",
                            "source_feed": "nasa_donki",
                            "threat_flags": ["solar_flare_x_class", "power_grid_risk", "gps_disruption"],
                        }
                        await kafka_client.send_event("cyber-events", cyber_data, key=f"nasa-cyber-{flare_id}")
                        metrics.events_ingested.labels(domain="cyber", source="nasa_donki").inc()

                logger.debug("DONKI FLR poll complete", extra={"flares": len(flares)})
            except Exception as e:
                logger.error("DONKI FLR poll error", extra={"error": str(e)})

            await asyncio.sleep(600)

    async def poll_donki_gst(self):
        while self.running:
            try:
                end = datetime.utcnow()
                start = end - timedelta(days=7)
                resp = await self.http_client.get(
                    f"{DONKI_URL}/GST.json",
                    params={
                        "startDate": start.strftime("%Y-%m-%d"),
                        "endDate": end.strftime("%Y-%m-%d"),
                        "api_key": self.api_key,
                    },
                )
                if resp.status_code != 200:
                    await asyncio.sleep(600)
                    continue

                storms = resp.json()
                for storm in storms[:5]:
                    storm_id = storm.get("gstID", "") or str(uuid.uuid4())
                    start_time = storm.get("startTime", datetime.utcnow().isoformat())
                    kp_index = storm.get("kIndex", [])
                    max_kp = max([k.get("kIndex", 0) for k in kp_index]) if kp_index else 5

                    severity = "SUSPICIOUS"
                    if max_kp >= 8:
                        severity = "CRITICAL"
                        await self._emit_alert(
                            "CRITICAL",
                            f"Severe geomagnetic storm (Kp={max_kp}) — power grid and GPS at risk",
                            "rf",
                        )
                    elif max_kp >= 6:
                        severity = "ELEVATED"

                    rf_data = {
                        "event_id": f"nasa-donki-gst-{storm_id}",
                        "domain": "rf",
                        "timestamp_utc": start_time,
                        "type": "geomagnetic_storm",
                        "anomaly_type": f"geomagnetic_kp{max_kp}",
                        "freq_mhz": round(10 - max_kp * 0.5, 2),
                        "bandwidth_hz": 10000000,
                        "signal_strength_dbm": round(-60 - max_kp * 2, 1),
                        "confidence": min(0.95, 0.3 + max_kp * 0.08),
                        "protocol_guess": "geomagnetic",
                        "estimated_lat": 0,
                        "estimated_lon": 0,
                        "source": "nasa_donki",
                        "kp_index": max_kp,
                        "threat_flags": [f"geomagnetic_storm_kp{max_kp}", "rf_blackout_risk"],
                    }
                    await kafka_client.send_event("rf-signals", rf_data, key=f"nasa-gst-{storm_id}")
                    metrics.events_ingested.labels(domain="rf", source="nasa_donki").inc()

                logger.debug("DONKI GST poll complete", extra={"storms": len(storms)})
            except Exception as e:
                logger.error("DONKI GST poll error", extra={"error": str(e)})

            await asyncio.sleep(600)

    async def _emit_alert(self, threat_class: str, description: str, domain: str):
        alert = {
            "alert_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.utcnow().isoformat(),
            "threat_class": threat_class,
            "confidence": 0.85,
            "domain": domain,
            "description": f"[NASA] {description}",
            "source": "nasa_integration",
            "ipfs_hash": f"Qm{abs(hash(description))}{uuid.uuid4().hex[:16]}",
        }
        await kafka_client.send_event("alerts", alert, key=alert["alert_id"])
        metrics.events_ingested.labels(domain="alerts", source="nasa_integration").inc()


if __name__ == "__main__":
    ingestor = NasaIngestor()
    asyncio.run(ingestor.start())
