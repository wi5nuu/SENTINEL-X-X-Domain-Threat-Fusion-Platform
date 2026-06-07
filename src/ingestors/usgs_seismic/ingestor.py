"""
USGS Real-time Earthquake Data Ingestor
Fetches real earthquake data from USGS and EMSC APIs
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional
import httpx

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics
from src.common.kafka import kafka_client
from src.common.security import get_security_manager

logger = setup_logging("usgs-seismic-ingestor")
security = get_security_manager()


class USGSSeismicIngestor:
    """Real-time earthquake data from USGS and EMSC"""
    
    def __init__(self):
        self.usgs_url = getattr(settings, 'usgs_api_url', 'https://earthquake.usgs.gov/earthquakes/feed/v1.0')
        self.emsc_url = getattr(settings, 'emsc_api_url', 'https://www.seismicportal.eu/fdsnws/event/1')
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        self.seen_events = set()
        
    async def start(self):
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await kafka_client.start()
        logger.info("USGS Seismic Ingestor started - REAL-TIME MODE")
        
        tasks = [
            self.poll_usgs_all(),
            self.poll_usgs_significant(),
            self.poll_emsc(),
        ]
        await asyncio.gather(*tasks)
    
    async def stop(self):
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
        await kafka_client.stop()
    
    async def poll_usgs_all(self):
        """Poll USGS for all earthquakes in last hour"""
        while self.running:
            try:
                resp = await self.http_client.get(
                    f"{self.usgs_url}/summary/all_hour.geojson",
                    headers={"User-Agent": "SENTINEL-Platform/1.0"}
                )
                
                if resp.status_code != 200:
                    logger.warning(f"USGS API error: {resp.status_code}")
                    await asyncio.sleep(60)
                    continue
                
                data = resp.json()
                features = data.get("features", [])
                
                for feature in features:
                    event_id = feature.get("id")
                    if event_id in self.seen_events:
                        continue
                    
                    self.seen_events.add(event_id)
                    if len(self.seen_events) > 10000:
                        self.seen_events = set(list(self.seen_events)[-5000:])
                    
                    await self._process_usgs_event(feature)
                
                logger.info(f"USGS poll complete: {len(features)} events")
                
            except Exception as e:
                logger.error(f"USGS poll error: {e}")
                metrics.errors_total.labels(service="usgs_ingestor", error_type="usgs_poll").inc()
            
            await asyncio.sleep(120)  # Poll every 2 minutes
    
    async def poll_usgs_significant(self):
        """Poll USGS for significant earthquakes in last week"""
        while self.running:
            try:
                resp = await self.http_client.get(
                    f"{self.usgs_url}/summary/significant_week.geojson",
                    headers={"User-Agent": "SENTINEL-Platform/1.0"}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    for feature in data.get("features", []):
                        event_id = feature.get("id")
                        if event_id not in self.seen_events:
                            self.seen_events.add(event_id)
                            await self._process_usgs_event(feature, is_significant=True)
                
            except Exception as e:
                logger.error(f"USGS significant poll error: {e}")
            
            await asyncio.sleep(300)  # Poll every 5 minutes
    
    async def poll_emsc(self):
        """Poll EMSC for European earthquakes"""
        while self.running:
            try:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=6)
                
                params = {
                    "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "minmagnitude": 2.5,
                    "format": "json",
                    "limit": 100
                }
                
                resp = await self.http_client.get(
                    f"{self.emsc_url}/query",
                    params=params,
                    headers={"User-Agent": "SENTINEL-Platform/1.0"}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    events = data.get("features", [])
                    
                    for event in events:
                        event_id = f"emsc_{event.get('id', str(uuid.uuid4()))}"
                        if event_id not in self.seen_events:
                            self.seen_events.add(event_id)
                            await self._process_emsc_event(event)
                    
                    logger.info(f"EMSC poll complete: {len(events)} events")
                
            except Exception as e:
                logger.error(f"EMSC poll error: {e}")
            
            await asyncio.sleep(300)  # Poll every 5 minutes
    
    async def _process_usgs_event(self, feature: dict, is_significant: bool = False):
        """Process USGS earthquake event"""
        try:
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [0, 0, 0])
            
            magnitude = props.get("mag", 0)
            if magnitude is None:
                magnitude = 0
            
            # Validate coordinates
            lon, lat, depth = coords[0], coords[1], coords[2] if len(coords) > 2 else 0
            if not security.validate_coordinates(lat, lon):
                logger.warning(f"Invalid coordinates: lat={lat}, lon={lon}")
                return
            
            event_data = {
                "event_id": f"usgs_{feature.get('id', str(uuid.uuid4()))}",
                "domain": "seismic",
                "timestamp_utc": datetime.fromtimestamp(props.get("time", 0) / 1000).isoformat(),
                "lat": lat,
                "lon": lon,
                "depth_km": abs(depth),
                "magnitude": magnitude,
                "magnitude_type": props.get("magType", "ml"),
                "location_description": security.sanitize_input(props.get("place", "Unknown")),
                "tsunami_warning": props.get("tsunami", 0) == 1,
                "source": "usgs_real",
                "felt_reports": props.get("felt", 0),
                "cdi": props.get("cdi"),
                "mmi": props.get("mmi"),
                "alert_level": props.get("alert"),
                "significance": props.get("sig", 0),
                "url": props.get("url", ""),
                "is_significant": is_significant,
                "threat_flags": []
            }
            
            # Add threat flags based on magnitude and depth
            if magnitude >= 7.0:
                event_data["threat_flags"].append("major_earthquake")
            if magnitude >= 6.0 and depth < 70:
                event_data["threat_flags"].append("shallow_strong_quake")
            if props.get("tsunami") == 1:
                event_data["threat_flags"].append("tsunami_warning_issued")
            
            await kafka_client.send_event("seismic-events", event_data, key=event_data["event_id"])
            metrics.events_ingested.labels(domain="seismic", source="usgs_real").inc()
            
            # Emit alert for significant events
            if magnitude >= 6.0 or is_significant:
                await self._emit_alert(event_data)
            
        except Exception as e:
            logger.error(f"Error processing USGS event: {e}")
    
    async def _process_emsc_event(self, feature: dict):
        """Process EMSC earthquake event"""
        try:
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [0, 0, 0])
            
            magnitude = props.get("mag", 0)
            lon, lat, depth = coords[0], coords[1], coords[2] if len(coords) > 2 else 0
            
            if not security.validate_coordinates(lat, lon):
                return
            
            event_data = {
                "event_id": f"emsc_{feature.get('id', str(uuid.uuid4()))}",
                "domain": "seismic",
                "timestamp_utc": props.get("time", datetime.utcnow().isoformat()),
                "lat": lat,
                "lon": lon,
                "depth_km": abs(depth),
                "magnitude": magnitude,
                "magnitude_type": props.get("magType", "ml"),
                "location_description": security.sanitize_input(props.get("flynn_region", "Unknown")),
                "tsunami_warning": False,
                "source": "emsc_real",
                "threat_flags": []
            }
            
            if magnitude >= 6.0:
                event_data["threat_flags"].append("significant_european_quake")
            
            await kafka_client.send_event("seismic-events", event_data, key=event_data["event_id"])
            metrics.events_ingested.labels(domain="seismic", source="emsc_real").inc()
            
        except Exception as e:
            logger.error(f"Error processing EMSC event: {e}")
    
    async def _emit_alert(self, event_data: dict):
        """Emit alert for significant earthquake"""
        severity = "INFORMATIONAL"
        if event_data["magnitude"] >= 8.0:
            severity = "CATASTROPHIC"
        elif event_data["magnitude"] >= 7.0:
            severity = "CRITICAL"
        elif event_data["magnitude"] >= 6.0:
            severity = "ELEVATED"
        
        alert = {
            "alert_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.utcnow().isoformat(),
            "threat_class": severity,
            "confidence": 0.99,
            "domain": "seismic",
            "description": f"Earthquake M{event_data['magnitude']} - {event_data['location_description']} (depth: {event_data['depth_km']}km)" + 
                          (" - TSUNAMI WARNING" if event_data.get("tsunami_warning") else ""),
            "source": "usgs_real_time",
            "ipfs_hash": f"Qm{abs(hash(event_data['event_id']))}{uuid.uuid4().hex[:16]}",
        }
        
        await kafka_client.send_event("alerts", alert, key=alert["alert_id"])
        metrics.events_ingested.labels(domain="alerts", source="usgs_real").inc()


if __name__ == "__main__":
    ingestor = USGSSeismicIngestor()
    asyncio.run(ingestor.start())
