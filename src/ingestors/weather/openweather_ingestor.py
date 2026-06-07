"""
OpenWeatherMap Integration for Weather-Based Correlation
Weather data can correlate with aircraft diversions, maritime delays, etc.
"""
import asyncio
import hashlib
import uuid
from datetime import datetime
from typing import Optional, List, Dict
import httpx

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics
from src.common.kafka import kafka_client
from src.common.security import get_security_manager

logger = setup_logging("weather-ingestor")
security = get_security_manager()


class WeatherIngestor:
    """Real-time weather data for correlation analysis"""
    
    # Major cities and strategic locations for monitoring
    MONITORING_LOCATIONS = [
        {"name": "New York", "lat": 40.7128, "lon": -74.0060},
        {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
        {"name": "London", "lat": 51.5074, "lon": -0.1278},
        {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
        {"name": "Singapore", "lat": 1.3521, "lon": 103.8198},
        {"name": "Dubai", "lat": 25.2048, "lon": 55.2708},
        {"name": "Hong Kong", "lat": 22.3193, "lon": 114.1694},
        {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
        {"name": "Frankfurt", "lat": 50.1109, "lon": 8.6821},
        {"name": "Amsterdam", "lat": 52.3676, "lon": 4.9041},
    ]
    
    def __init__(self):
        self.running = False
        self.http_client: Optional[httpx.AsyncClient] = None
        self.api_key = getattr(settings, 'openweather_api_key', '')
        self.base_url = getattr(settings, 'openweather_url', 'https://api.openweathermap.org/data/2.5')
        
        logger.info(f"OpenWeather configured: {bool(self.api_key)}")
    
    async def start(self):
        if not self.api_key:
            logger.warning("OpenWeather API key not configured - skipping")
            return
        
        self.running = True
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await kafka_client.start()
        logger.info("Weather Ingestor started - WEATHER CORRELATION DATA")
        
        tasks = [
            self.poll_current_weather(),
            self.poll_weather_alerts(),
        ]
        await asyncio.gather(*tasks)
    
    async def stop(self):
        self.running = False
        if self.http_client:
            await self.http_client.aclose()
    
    async def poll_current_weather(self):
        """Poll current weather for monitored locations"""
        while self.running:
            if not security.check_rate_limit("openweather", max_requests=1000, window_seconds=3600):
                await asyncio.sleep(60)
                continue
            
            try:
                for location in self.MONITORING_LOCATIONS:
                    resp = await self.http_client.get(
                        f"{self.base_url}/weather",
                        params={
                            "lat": location["lat"],
                            "lon": location["lon"],
                            "appid": self.api_key,
                            "units": "metric"
                        }
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        await self._process_weather(location, data)
                    
                    await asyncio.sleep(1)  # Rate limit between requests
                
                logger.info(f"Weather poll complete: {len(self.MONITORING_LOCATIONS)} locations")
                
            except Exception as e:
                logger.error(f"Weather poll error: {e}")
                metrics.errors_total.labels(service="weather", error_type="poll").inc()
            
            await asyncio.sleep(600)  # Poll every 10 minutes
    
    async def _process_weather(self, location: dict, data: dict):
        """Process weather data"""
        try:
            main = data.get("main", {})
            weather = data.get("weather", [{}])[0]
            wind = data.get("wind", {})
            visibility = data.get("visibility", 10000)
            
            weather_data = {
                "event_id": str(uuid.uuid4()),
                "domain": "weather",
                "timestamp_utc": datetime.fromtimestamp(data.get("dt", 0)).isoformat(),
                "location_name": location["name"],
                "lat": location["lat"],
                "lon": location["lon"],
                "temperature_c": main.get("temp"),
                "feels_like_c": main.get("feels_like"),
                "pressure_hpa": main.get("pressure"),
                "humidity_percent": main.get("humidity"),
                "visibility_m": visibility,
                "wind_speed_ms": wind.get("speed"),
                "wind_direction_deg": wind.get("deg"),
                "wind_gust_ms": wind.get("gust"),
                "clouds_percent": data.get("clouds", {}).get("all"),
                "weather_condition": weather.get("main"),
                "weather_description": weather.get("description"),
                "rain_1h_mm": data.get("rain", {}).get("1h", 0),
                "snow_1h_mm": data.get("snow", {}).get("1h", 0),
                "source": "openweather_api",
                "threat_flags": []
            }
            
            # Identify conditions that affect aviation/maritime
            if visibility < 1000:  # Low visibility
                weather_data["threat_flags"].append("low_visibility_aviation_impact")
            
            if wind.get("speed", 0) > 15:  # High winds (>15 m/s = ~30 knots)
                weather_data["threat_flags"].append("high_winds_operations_impact")
            
            if weather.get("main") in ["Thunderstorm", "Squall", "Tornado"]:
                weather_data["threat_flags"].append("severe_weather_alert")
            
            if main.get("temp", 0) < -10 or main.get("temp", 0) > 40:
                weather_data["threat_flags"].append("extreme_temperature")
            
            await kafka_client.send_event("weather-data", weather_data, key=location["name"])
            metrics.events_ingested.labels(domain="weather", source="openweather").inc()
            
        except Exception as e:
            logger.error(f"Error processing weather data: {e}")
    
    async def poll_weather_alerts(self):
        """Poll for severe weather alerts"""
        while self.running:
            try:
                for location in self.MONITORING_LOCATIONS:
                    resp = await self.http_client.get(
                        f"{self.base_url}/onecall",
                        params={
                            "lat": location["lat"],
                            "lon": location["lon"],
                            "appid": self.api_key,
                            "exclude": "minutely,hourly,daily"
                        }
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        alerts = data.get("alerts", [])
                        
                        for alert in alerts:
                            await self._process_weather_alert(location, alert)
                    
                    await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Weather alerts poll error: {e}")
            
            await asyncio.sleep(900)  # Poll every 15 minutes
    
    async def _process_weather_alert(self, location: dict, alert: dict):
        """Process weather alert"""
        try:
            alert_data = {
                "alert_id": str(uuid.uuid4()),
                "domain": "weather",
                "type": "weather_alert",
                "timestamp_utc": datetime.fromtimestamp(alert.get("start", 0)).isoformat(),
                "location_name": location["name"],
                "lat": location["lat"],
                "lon": location["lon"],
                "event": security.sanitize_input(alert.get("event", "")),
                "sender": security.sanitize_input(alert.get("sender_name", "")),
                "description": security.sanitize_input(alert.get("description", ""))[:500],
                "start_time": datetime.fromtimestamp(alert.get("start", 0)).isoformat(),
                "end_time": datetime.fromtimestamp(alert.get("end", 0)).isoformat(),
                "severity": "ELEVATED",
                "source": "openweather_alerts",
                "threat_flags": ["severe_weather_alert", "operations_disruption_risk"]
            }
            
            await kafka_client.send_event("weather-alerts", alert_data, key=alert_data["alert_id"])
            metrics.events_ingested.labels(domain="weather", source="openweather_alerts").inc()
            
            logger.warning(f"Weather alert: {alert.get('event')} in {location['name']}")
            
        except Exception as e:
            logger.error(f"Error processing weather alert: {e}")


if __name__ == "__main__":
    ingestor = WeatherIngestor()
    asyncio.run(ingestor.start())
