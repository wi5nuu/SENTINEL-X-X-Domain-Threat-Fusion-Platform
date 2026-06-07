"""
FlightAware AeroAPI Integration for Enhanced Aviation Data
Provides more accurate and detailed flight information
"""
import asyncio
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, List
import httpx

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics
from src.common.kafka import kafka_client
from src.common.security import get_security_manager

logger = setup_logging("flightaware-ingestor")
security = get_security_manager()


class FlightAwareIngestor:
    """Enhanced aviation data from FlightAware AeroAPI"""
    
    def __init__(self):
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        self.api_key = getattr(settings, 'aeroapi_key', '')
        self.base_url = getattr(settings, 'aeroapi_url', 'https://aeroapi.flightaware.com/aeroapi')
        self.seen_flights = set()
        
        logger.info(f"FlightAware configured: {bool(self.api_key)}")
    
    async def start(self):
        if not self.api_key:
            logger.warning("FlightAware API key not configured - skipping")
            return
        
        self.running = True
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "x-apikey": self.api_key,
                "Accept": "application/json"
            }
        )
        await kafka_client.start()
        logger.info("FlightAware Ingestor started - ENHANCED AVIATION DATA")
        
        tasks = [
            self.poll_flights_in_area(),
            self.poll_airport_delays(),
            self.poll_flight_routes(),
        ]
        await asyncio.gather(*tasks)
    
    async def stop(self):
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
    
    async def poll_flights_in_area(self):
        """Get flights in specific geographic areas"""
        while self.running:
            if not security.check_rate_limit("flightaware", max_requests=100, window_seconds=3600):
                await asyncio.sleep(60)
                continue
            
            try:
                # Query flights in box (example: major international area)
                resp = await self.http_client.get(
                    f"{self.base_url}/flights/search",
                    params={
                        "query": "-latlong \"30 -130 50 -70\"",  # North America
                        "max_pages": 1
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    flights = data.get("flights", [])
                    
                    for flight in flights[:50]:
                        await self._process_flight(flight)
                    
                    logger.info(f"FlightAware: Processed {len(flights)} enhanced flights")
                else:
                    logger.warning(f"FlightAware API error: {resp.status_code}")
                
            except Exception as e:
                logger.error(f"FlightAware poll error: {e}")
                metrics.errors_total.labels(service="flightaware", error_type="poll").inc()
            
            await asyncio.sleep(180)  # Poll every 3 minutes
    
    async def _process_flight(self, flight: dict):
        """Process enhanced flight data"""
        try:
            fa_flight_id = flight.get("fa_flight_id", "")
            ident = flight.get("ident", flight.get("registration", "UNKNOWN"))
            
            flight_hash = hashlib.sha256(f"fa_{fa_flight_id}".encode()).hexdigest()[:16]
            if flight_hash in self.seen_flights:
                return
            
            self.seen_flights.add(flight_hash)
            if len(self.seen_flights) > 10000:
                self.seen_flights = set(list(self.seen_flights)[-5000:])
            
            # Extract position
            last_position = flight.get("last_position", {})
            lat = last_position.get("latitude")
            lon = last_position.get("longitude")
            altitude = last_position.get("altitude")
            
            if not lat or not lon or not security.validate_coordinates(lat, lon):
                return
            
            # Enhanced flight data
            enhanced_flight = {
                "flight_id": fa_flight_id,
                "domain": "air",
                "timestamp_utc": datetime.utcnow().isoformat(),
                "ident": security.sanitize_input(ident),
                "registration": flight.get("registration"),
                "aircraft_type": flight.get("aircraft_type"),
                "origin": flight.get("origin", {}).get("code"),
                "destination": flight.get("destination", {}).get("code"),
                "lat": lat,
                "lon": lon,
                "altitude_ft": altitude,
                "groundspeed_kts": last_position.get("groundspeed"),
                "heading": last_position.get("heading"),
                "status": flight.get("status"),
                "route": flight.get("route"),
                "filed_altitude": flight.get("filed_altitude"),
                "filed_speed": flight.get("filed_speed"),
                "departure_delay": flight.get("departure_delay"),
                "arrival_delay": flight.get("arrival_delay"),
                "estimated_arrival": flight.get("estimated_arrival_time"),
                "actual_arrival": flight.get("actual_arrival_time"),
                "waypoints": flight.get("waypoints", [])[:10],  # First 10 waypoints
                "source": "flightaware_aeroapi",
                "accuracy_level": "high",
                "data_quality_score": 0.95,
                "threat_flags": []
            }
            
            # Check for anomalies
            if flight.get("departure_delay", 0) > 3600:  # > 1 hour delay
                enhanced_flight["threat_flags"].append("significant_departure_delay")
            
            if flight.get("status") == "diverted":
                enhanced_flight["threat_flags"].append("flight_diverted")
            
            await kafka_client.send_event("enhanced-air-tracks", enhanced_flight, key=fa_flight_id)
            metrics.events_ingested.labels(domain="air", source="flightaware").inc()
            
        except Exception as e:
            logger.error(f"Error processing FlightAware flight: {e}")
    
    async def poll_airport_delays(self):
        """Monitor airport delays and conditions"""
        while self.running:
            try:
                # Major international airports
                airports = ["KJFK", "KLAX", "EGLL", "LFPG", "EDDF", "RJTT", "WSSS", "VHHH"]
                
                for airport in airports:
                    resp = await self.http_client.get(
                        f"{self.base_url}/airports/{airport}/delays"
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        await self._process_airport_delays(airport, data)
                
            except Exception as e:
                logger.error(f"Airport delays poll error: {e}")
            
            await asyncio.sleep(600)  # Poll every 10 minutes
    
    async def _process_airport_delays(self, airport: str, data: dict):
        """Process airport delay information"""
        try:
            delays = data.get("delays", {})
            
            if any(delays.values()):
                delay_event = {
                    "event_id": str(uuid.uuid4()),
                    "domain": "air",
                    "type": "airport_delays",
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "airport_code": airport,
                    "departure_delays": delays.get("departure", {}),
                    "arrival_delays": delays.get("arrival", {}),
                    "ground_delays": delays.get("ground", {}),
                    "weather_impact": data.get("weather", {}),
                    "source": "flightaware_aeroapi",
                    "severity": self._calculate_delay_severity(delays)
                }
                
                await kafka_client.send_event("airport-conditions", delay_event, key=airport)
                metrics.events_ingested.labels(domain="air", source="flightaware_delays").inc()
                
        except Exception as e:
            logger.error(f"Error processing airport delays: {e}")
    
    async def poll_flight_routes(self):
        """Get detailed flight routes and waypoints"""
        while self.running:
            await asyncio.sleep(300)
            # Implementation for route tracking
    
    def _calculate_delay_severity(self, delays: dict) -> str:
        """Calculate delay severity based on delay times"""
        max_delay = 0
        for category in delays.values():
            if isinstance(category, dict):
                delay_val = category.get("average", 0)
                max_delay = max(max_delay, delay_val)
        
        if max_delay > 3600:  # > 1 hour
            return "CRITICAL"
        elif max_delay > 1800:  # > 30 min
            return "ELEVATED"
        elif max_delay > 900:  # > 15 min
            return "SUSPICIOUS"
        else:
            return "INFORMATIONAL"


if __name__ == "__main__":
    ingestor = FlightAwareIngestor()
    asyncio.run(ingestor.start())
