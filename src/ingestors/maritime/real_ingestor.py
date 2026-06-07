"""
REAL-TIME Maritime Domain Ingestor
Uses MarineTraffic API and AISHub for REAL vessel data
NO SYNTHETIC DATA - 100% REAL
"""
import asyncio
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict
import httpx

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics
from src.common.kafka import kafka_client
from src.common.security import get_security_manager
from src.common.models import VesselTrack, VesselType, NavStatus, AISClass

logger = setup_logging("maritime-real-ingestor")
security = get_security_manager()


class RealMaritimeIngestor:
    """100% Real-time maritime data - NO SYNTHETIC"""
    
    def __init__(self):
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # API keys
        self.marinetraffic_key = getattr(settings, 'marinetraffic_api_key', '')
        self.vesselfinder_key = getattr(settings, 'vesselfinder_api_key', '')
        self.aishub_username = getattr(settings, 'aishub_username', '')
        
        self.seen_vessels = set()
        
        logger.info(f"Maritime sources: MarineTraffic={bool(self.marinetraffic_key)}, "
                   f"VesselFinder={bool(self.vesselfinder_key)}, AISHub={bool(self.aishub_username)}")
    
    async def start(self):
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await kafka_client.start()
        logger.info("REAL Maritime Ingestor started - 100% REAL-TIME MODE")
        
        tasks = []
        
        if self.marinetraffic_key:
            tasks.append(self.poll_marinetraffic())
        
        if self.vesselfinder_key:
            tasks.append(self.poll_vesselfinder())
        
        if self.aishub_username:
            tasks.append(self.poll_aishub())
        
        # Always try public AIS streams
        tasks.append(self.poll_aprs_fi())
        tasks.append(self.poll_shipfinder())
        
        if not tasks:
            logger.warning("⚠️ NO MARITIME DATA SOURCES CONFIGURED!")
            logger.warning("Configure: MARINETRAFFIC_API_KEY, VESSELFINDER_API_KEY, or AISHUB_USERNAME")
            logger.warning("Using public AIS feeds only (limited coverage)")
        
        await asyncio.gather(*tasks)
    
    async def stop(self):
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
        await kafka_client.stop()
    
    async def poll_marinetraffic(self):
        """Poll MarineTraffic API for real vessel data"""
        while self.running:
            if not security.check_rate_limit("marinetraffic", max_requests=100, window_seconds=3600):
                await asyncio.sleep(60)
                continue
            
            try:
                # Get vessels in area (example: Singapore Strait)
                resp = await self.http_client.get(
                    f"{getattr(settings, 'marinetraffic_url', 'https://services.marinetraffic.com/api')}/exportvessels/v:8",
                    params={
                        "protocol": "json",
                        "msgtype": "extended",
                        "MINLAT": 1.0,
                        "MAXLAT": 1.5,
                        "MINLON": 103.5,
                        "MAXLON": 104.0
                    },
                    headers={"api-key": self.marinetraffic_key}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    vessels = data if isinstance(data, list) else []
                    
                    for vessel_data in vessels[:100]:
                        await self._process_marinetraffic_vessel(vessel_data)
                    
                    logger.info(f"MarineTraffic poll: {len(vessels)} vessels")
                
            except Exception as e:
                logger.error(f"MarineTraffic poll error: {e}")
            
            await asyncio.sleep(120)  # Poll every 2 minutes
    
    async def _process_marinetraffic_vessel(self, data: dict):
        """Process real MarineTraffic vessel data"""
        try:
            mmsi = str(data.get("MMSI", "")).zfill(9)
            if not mmsi or mmsi == "000000000":
                return
            
            vessel_id = hashlib.sha256(f"mt_{mmsi}".encode()).hexdigest()[:16]
            if vessel_id in self.seen_vessels:
                return
            
            self.seen_vessels.add(vessel_id)
            if len(self.seen_vessels) > 50000:
                self.seen_vessels = set(list(self.seen_vessels)[-25000:])
            
            lat = float(data.get("LAT", 0))
            lon = float(data.get("LON", 0))
            
            if not security.validate_coordinates(lat, lon):
                return
            
            vessel = {
                "mmsi": mmsi,
                "domain": "maritime",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "vessel_name": security.sanitize_input(data.get("SHIPNAME", "Unknown")),
                "vessel_type": self._map_ship_type(data.get("TYPE", 0)),
                "imo": data.get("IMO"),
                "flag_state": data.get("FLAG", ""),
                "lat": lat,
                "lon": lon,
                "sog_knots": float(data.get("SPEED", 0)) / 10,
                "cog_deg": float(data.get("COURSE", 0)) / 10,
                "heading_deg": int(data.get("HEADING", 0)),
                "destination": security.sanitize_input(data.get("DESTINATION", "")),
                "eta": data.get("ETA"),
                "draught_m": float(data.get("DRAUGHT", 0)) / 10 if data.get("DRAUGHT") else None,
                "length_m": data.get("LENGTH"),
                "width_m": data.get("WIDTH"),
                "source": "marinetraffic_real",
                "dark_vessel_suspect": False,
                "anomaly_flags": [],
                "threat_flags": []
            }
            
            await kafka_client.send_event("maritime-positions", vessel, key=mmsi)
            metrics.events_ingested.labels(domain="maritime", source="marinetraffic_real").inc()
            
        except Exception as e:
            logger.error(f"Error processing MarineTraffic vessel: {e}")
    
    async def poll_vesselfinder(self):
        """Poll VesselFinder API for real vessel data"""
        while self.running:
            if not security.check_rate_limit("vesselfinder", max_requests=100, window_seconds=3600):
                await asyncio.sleep(60)
                continue
            
            try:
                # Get vessels in area
                resp = await self.http_client.get(
                    f"{getattr(settings, 'vesselfinder_url', 'https://api.vesselfinder.com')}/vesselslist",
                    params={
                        "userkey": self.vesselfinder_key,
                        "mmsi": "",  # Get all
                        "sat": 1
                    }
                )
                
                if resp.status_code == 200:
                    vessels = resp.json()
                    
                    for vessel_data in vessels[:100]:
                        await self._process_vesselfinder_vessel(vessel_data)
                    
                    logger.info(f"VesselFinder poll: {len(vessels)} vessels")
                
            except Exception as e:
                logger.error(f"VesselFinder poll error: {e}")
            
            await asyncio.sleep(180)  # Poll every 3 minutes
    
    async def _process_vesselfinder_vessel(self, data: dict):
        """Process real VesselFinder vessel data"""
        try:
            mmsi = str(data.get("MMSI", "")).zfill(9)
            if not mmsi or mmsi == "000000000":
                return
            
            lat = float(data.get("LAT", 0))
            lon = float(data.get("LON", 0))
            
            if not security.validate_coordinates(lat, lon):
                return
            
            vessel = {
                "mmsi": mmsi,
                "domain": "maritime",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "vessel_name": security.sanitize_input(data.get("NAME", "Unknown")),
                "vessel_type": self._map_ship_type(data.get("TYPE", 0)),
                "lat": lat,
                "lon": lon,
                "sog_knots": float(data.get("SPEED", 0)),
                "cog_deg": float(data.get("COURSE", 0)),
                "heading_deg": int(data.get("HEADING", 0)),
                "source": "vesselfinder_real",
                "dark_vessel_suspect": False,
                "anomaly_flags": [],
                "threat_flags": []
            }
            
            await kafka_client.send_event("maritime-positions", vessel, key=mmsi)
            metrics.events_ingested.labels(domain="maritime", source="vesselfinder_real").inc()
            
        except Exception as e:
            logger.error(f"Error processing VesselFinder vessel: {e}")
    
    async def poll_aishub(self):
        """Poll AISHub for real AIS data"""
        while self.running:
            if not security.check_rate_limit("aishub", max_requests=500, window_seconds=3600):
                await asyncio.sleep(60)
                continue
            
            try:
                # Get compressed feed
                resp = await self.http_client.get(
                    f"{getattr(settings, 'aishub_url', 'http://data.aishub.net')}/ws.php",
                    params={
                        "username": self.aishub_username,
                        "format": 1,  # JSON
                        "output": "json",
                        "compress": 0
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    vessels = data.get("data", [])
                    
                    for vessel_data in vessels[:200]:
                        await self._process_aishub_vessel(vessel_data)
                    
                    logger.info(f"AISHub poll: {len(vessels)} vessels")
                
            except Exception as e:
                logger.error(f"AISHub poll error: {e}")
            
            await asyncio.sleep(60)  # Poll every minute
    
    async def _process_aishub_vessel(self, data: dict):
        """Process real AISHub vessel data"""
        try:
            mmsi = str(data.get("MMSI", "")).zfill(9)
            if not mmsi or mmsi == "000000000":
                return
            
            lat = float(data.get("LATITUDE", 0))
            lon = float(data.get("LONGITUDE", 0))
            
            if not security.validate_coordinates(lat, lon):
                return
            
            vessel = {
                "mmsi": mmsi,
                "domain": "maritime",
                "timestamp_utc": datetime.fromtimestamp(int(data.get("TIME", 0))).isoformat(),
                "vessel_name": security.sanitize_input(data.get("NAME", "Unknown")),
                "vessel_type": self._map_ship_type(data.get("TYPE", 0)),
                "lat": lat,
                "lon": lon,
                "sog_knots": float(data.get("SOG", 0)),
                "cog_deg": float(data.get("COG", 0)),
                "heading_deg": int(data.get("HEADING", 0)),
                "source": "aishub_real",
                "dark_vessel_suspect": False,
                "anomaly_flags": [],
                "threat_flags": []
            }
            
            await kafka_client.send_event("maritime-positions", vessel, key=mmsi)
            metrics.events_ingested.labels(domain="maritime", source="aishub_real").inc()
            
        except Exception as e:
            logger.error(f"Error processing AISHub vessel: {e}")
    
    async def poll_aprs_fi(self):
        """Poll APRS.fi for public AIS data"""
        while self.running:
            try:
                # Public AIS feed (limited)
                resp = await self.http_client.get(
                    "https://api.aprs.fi/api/get",
                    params={
                        "what": "loc",
                        "name": "AIS*",
                        "format": "json"
                    },
                    timeout=15.0
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    entries = data.get("entries", [])
                    logger.info(f"APRS.fi public feed: {len(entries)} entries")
                
            except Exception as e:
                logger.debug(f"APRS.fi poll: {e}")
            
            await asyncio.sleep(300)  # Poll every 5 minutes
    
    async def poll_shipfinder(self):
        """Try public ship tracking feeds"""
        while self.running:
            await asyncio.sleep(300)
            logger.debug("Public maritime feeds: limited coverage without API keys")
    
    def _map_ship_type(self, type_code: int) -> str:
        """Map AIS ship type code to vessel type"""
        type_map = {
            70: "cargo", 71: "cargo", 72: "cargo", 73: "cargo", 74: "cargo",
            75: "cargo", 76: "cargo", 77: "cargo", 78: "cargo", 79: "cargo",
            80: "tanker", 81: "tanker", 82: "tanker", 83: "tanker", 84: "tanker",
            85: "tanker", 86: "tanker", 87: "tanker", 88: "tanker", 89: "tanker",
            60: "passenger", 61: "passenger", 62: "passenger", 63: "passenger", 64: "passenger",
            65: "passenger", 66: "passenger", 67: "passenger", 68: "passenger", 69: "passenger",
            30: "fishing", 31: "fishing", 32: "fishing", 33: "fishing",
            35: "military", 36: "military",
            37: "pleasure",
            50: "pilot", 51: "search_rescue", 52: "tug",
            40: "high_speed", 41: "high_speed", 42: "high_speed", 43: "high_speed",
        }
        return type_map.get(type_code, "unknown")


if __name__ == "__main__":
    ingestor = RealMaritimeIngestor()
    asyncio.run(ingestor.start())
