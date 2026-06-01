import asyncio
import time
from datetime import datetime
from typing import Optional
import httpx

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics, track_latency
from src.common.kafka import kafka_client
from src.common.models import SeismicEvent

logger = setup_logging("seismic-ingestor")

SEISMIC_THRESHOLDS = {
    "magnitude_warning": 5.0,
    "magnitude_elevated": 6.5,
    "magnitude_critical": 7.5,
    "magnitude_catastrophic": 8.5,
    "depth_km_shallow_threshold": 70,
    "population_radius_km": 100,
    "tsunami_hazard_depth_m": 100,
}

SPACE_WEATHER_THRESHOLDS = {
    "kp_watch": 4,
    "kp_warning": 5,
    "kp_severe": 7,
    "kp_extreme": 9,
}

FEEDS = {
    "usgs_earthquake": {
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
        "poll_interval": 60,
        "min_magnitude": 2.5,
    },
    "noaa_swpc_solar_wind": {
        "url": "https://services.swpc.noaa.gov/products/solar-wind/mag-1-m.json",
        "poll_interval": 60,
    },
    "noaa_swpc_kp_index": {
        "url": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json",
        "poll_interval": 900,
    },
}


class SeismicDomainIngestor:
    def __init__(self):
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        self.last_kp: Optional[float] = None

    async def start(self):
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await kafka_client.start()
        logger.info("Seismic Domain Ingestor started")
        tasks = [
            self.poll_usgs(),
            self.poll_noaa_solar_wind(),
            self.poll_noaa_kp(),
        ]
        await asyncio.gather(*tasks)

    async def stop(self):
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
        await kafka_client.stop()

    @track_latency("seismic")
    async def poll_usgs(self):
        feed = FEEDS["usgs_earthquake"]
        while self.running:
            try:
                resp = await self.http_client.get(feed["url"])
                if resp.status_code != 200:
                    await asyncio.sleep(feed["poll_interval"])
                    continue
                data = resp.json()
                for feature in data.get("features", []):
                    props = feature.get("properties", {})
                    mag = props.get("mag", 0)
                    if mag < feed["min_magnitude"]:
                        continue
                    coords = feature.get("geometry", {}).get("coordinates", [0, 0, 0])
                    event = SeismicEvent(
                        event_id=props.get("net", "us") + props.get("code", ""),
                        timestamp_utc=datetime.fromtimestamp(props.get("time", 0) / 1000),
                        lat=coords[1],
                        lon=coords[0],
                        depth_km=coords[2],
                        magnitude=mag,
                        magnitude_type=props.get("magType", "ml"),
                        location_description=props.get("place", ""),
                        felt_reports=props.get("felt", 0) or 0,
                        tsunami_warning=props.get("tsunami", 0) == 1,
                        source="usgs",
                    )
                    metrics.events_ingested.labels(domain="seismic", source="usgs").inc()
                    await self._evaluate_thresholds(event)
                    await kafka_client.send_event("seismic-events", event.model_dump(), key=event.event_id)
            except httpx.TimeoutException:
                logger.warning("USGS poll timeout")
            except Exception as e:
                metrics.errors_total.labels(service="seismic_ingestor", error_type="usgs_poll").inc()
                logger.error("USGS poll error", extra={"error": str(e)})
            await asyncio.sleep(feed["poll_interval"])

    async def poll_noaa_solar_wind(self):
        feed = FEEDS["noaa_swpc_solar_wind"]
        while self.running:
            try:
                resp = await self.http_client.get(feed["url"])
                if resp.status_code == 200:
                    data = resp.json()
                    if len(data) > 1:
                        latest = data[-1]
                        solar_wind = {
                            "timestamp_utc": datetime.utcnow().isoformat(),
                            "source": "noaa_swpc",
                            "type": "solar_wind",
                            "bt_nT": latest[1] if len(latest) > 1 else None,
                            "bz_nT": latest[2] if len(latest) > 2 else None,
                            "speed_kms": latest[3] if len(latest) > 3 else None,
                            "density_ncc": latest[4] if len(latest) > 4 else None,
                        }
                        await kafka_client.send_event("seismic-events", solar_wind, key="solar-wind")
            except Exception as e:
                logger.error("NOAA solar wind poll error", extra={"error": str(e)})
            await asyncio.sleep(feed["poll_interval"])

    async def poll_noaa_kp(self):
        feed = FEEDS["noaa_swpc_kp_index"]
        while self.running:
            try:
                resp = await self.http_client.get(feed["url"])
                if resp.status_code == 200:
                    data = resp.json()
                    for entry in data:
                        kp = entry.get("kp_index")
                        if kp is not None:
                            self.last_kp = float(kp)
                            kp_event = {
                                "timestamp_utc": datetime.utcnow().isoformat(),
                                "source": "noaa_swpc",
                                "type": "kp_index",
                                "kp_index": self.last_kp,
                                "severity": self._kp_severity(self.last_kp),
                            }
                            await kafka_client.send_event("seismic-events", kp_event, key="kp-index")
            except Exception as e:
                logger.error("NOAA Kp poll error", extra={"error": str(e)})
            await asyncio.sleep(feed["poll_interval"])

    async def _evaluate_thresholds(self, event: SeismicEvent):
        alerts = []
        if event.magnitude >= SEISMIC_THRESHOLDS["magnitude_catastrophic"]:
            alerts.append(f"CATASTROPHIC: Magnitude {event.magnitude} earthquake detected")
        elif event.magnitude >= SEISMIC_THRESHOLDS["magnitude_critical"]:
            alerts.append(f"CRITICAL: Magnitude {event.magnitude} earthquake")
        elif event.magnitude >= SEISMIC_THRESHOLDS["magnitude_elevated"]:
            alerts.append(f"ELEVATED: Magnitude {event.magnitude} earthquake")
        elif event.magnitude >= SEISMIC_THRESHOLDS["magnitude_warning"]:
            alerts.append(f"WARNING: Magnitude {event.magnitude} earthquake")

        if event.depth_km < SEISMIC_THRESHOLDS["depth_km_shallow_threshold"] and event.magnitude >= 5.0:
            alerts.append(f"SHALLOW: Depth {event.depth_km}km, increased damage risk")

        if event.tsunami_warning:
            alerts.append("TSUNAMI WARNING: Event has tsunami potential")

        if alerts:
            alert = {
                "event_id": event.event_id,
                "timestamp_utc": datetime.utcnow().isoformat(),
                "severity": "CRITICAL" if event.magnitude >= 6.5 else "ELEVATED",
                "alerts": alerts,
                "lat": event.lat,
                "lon": event.lon,
                "magnitude": event.magnitude,
                "depth_km": event.depth_km,
            }
            await kafka_client.send_event("alerts", alert, key=f"seismic-{event.event_id}")

    @staticmethod
    def _kp_severity(kp: float) -> str:
        if kp >= 9:
            return "EXTREME"
        elif kp >= 7:
            return "SEVERE"
        elif kp >= 5:
            return "WARNING"
        elif kp >= 4:
            return "WATCH"
        return "NORMAL"
