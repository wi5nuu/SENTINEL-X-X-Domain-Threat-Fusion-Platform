"""
Enhanced Correlation Engine
Correlates data across multiple domains for better accuracy
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import numpy as np

from src.common.logging import setup_logging
from src.common.kafka import kafka_client
from src.common.database import get_db

logger = setup_logging("enhanced-correlation")


class EnhancedCorrelationEngine:
    """Advanced multi-domain correlation with ML-based scoring"""
    
    def __init__(self):
        self.running = False
        self.event_buffer = defaultdict(list)
        self.correlation_window = 300  # 5 minutes
        
        # Correlation rules
        self.rules = {
            "weather_aviation_impact": {
                "domains": ["weather", "air"],
                "conditions": ["low_visibility", "high_winds", "severe_weather"],
                "score_multiplier": 1.5
            },
            "cyber_physical_convergence": {
                "domains": ["cyber", "air", "maritime"],
                "conditions": ["cyber_attack", "gps_disruption", "navigation_anomaly"],
                "score_multiplier": 2.0
            },
            "space_weather_rf_impact": {
                "domains": ["space", "rf", "air"],
                "conditions": ["solar_flare", "gps_disruption", "comms_loss"],
                "score_multiplier": 1.8
            },
            "seismic_infrastructure_risk": {
                "domains": ["seismic", "cyber"],
                "conditions": ["earthquake", "power_outage", "network_disruption"],
                "score_multiplier": 1.7
            },
            "maritime_cyber_hijack": {
                "domains": ["maritime", "cyber"],
                "conditions": ["dark_vessel", "navigation_anomaly", "cyber_attack"],
                "score_multiplier": 2.5
            },
            "aviation_gps_spoofing": {
                "domains": ["air", "rf"],
                "conditions": ["gps_anomaly", "signal_interference", "position_jump"],
                "score_multiplier": 2.2
            }
        }
    
    async def start(self):
        self.running = True
        await kafka_client.start()
        logger.info("Enhanced Correlation Engine started")
        
        tasks = [
            self.consume_events(),
            self.correlate_events(),
            self.emit_correlated_alerts(),
        ]
        await asyncio.gather(*tasks)
    
    async def stop(self):
        self.running = False
    
    async def consume_events(self):
        """Consume events from all domains"""
        topics = [
            "air-tracks", "enhanced-air-tracks", "maritime-positions",
            "cyber-events", "seismic-events", "rf-signals",
            "weather-data", "weather-alerts", "airport-conditions"
        ]
        
        # Implementation would consume from Kafka topics
        while self.running:
            await asyncio.sleep(1)
    
    async def correlate_events(self):
        """Correlate events across domains"""
        while self.running:
            try:
                # Clean old events
                cutoff_time = datetime.utcnow() - timedelta(seconds=self.correlation_window)
                for domain in list(self.event_buffer.keys()):
                    self.event_buffer[domain] = [
                        e for e in self.event_buffer[domain]
                        if e["timestamp"] > cutoff_time
                    ]
                
                # Check correlation rules
                for rule_name, rule in self.rules.items():
                    correlations = await self._check_rule(rule_name, rule)
                    
                    if correlations:
                        await self._emit_correlation(rule_name, rule, correlations)
                
            except Exception as e:
                logger.error(f"Correlation error: {e}")
            
            await asyncio.sleep(10)  # Run every 10 seconds
    
    async def _check_rule(self, rule_name: str, rule: dict) -> List[Dict]:
        """Check if correlation rule is triggered"""
        required_domains = rule["domains"]
        conditions = rule["conditions"]
        
        correlations = []
        
        # Check if we have events from all required domains
        domain_events = {}
        for domain in required_domains:
            events = self.event_buffer.get(domain, [])
            if not events:
                return []  # Missing domain, no correlation
            domain_events[domain] = events
        
        # Check spatial-temporal proximity
        for i, primary_event in enumerate(domain_events[required_domains[0]]):
            related_events = [primary_event]
            
            for other_domain in required_domains[1:]:
                # Find events within time window and geographic proximity
                matching = self._find_matching_events(
                    primary_event,
                    domain_events[other_domain]
                )
                
                if matching:
                    related_events.extend(matching)
            
            # If we found events from all domains, we have a correlation
            if len(related_events) >= len(required_domains):
                correlations.append({
                    "events": related_events,
                    "confidence": self._calculate_confidence(related_events),
                    "severity": self._calculate_severity(related_events, rule)
                })
        
        return correlations
    
    def _find_matching_events(self, primary: dict, candidates: List[dict]) -> List[dict]:
        """Find events that match spatially and temporally"""
        matches = []
        
        primary_lat = primary.get("lat", 0)
        primary_lon = primary.get("lon", 0)
        primary_time = primary.get("timestamp")
        
        for candidate in candidates:
            # Time proximity (within correlation window)
            time_diff = abs((candidate["timestamp"] - primary_time).total_seconds())
            if time_diff > self.correlation_window:
                continue
            
            # Spatial proximity (within 500km)
            cand_lat = candidate.get("lat", 0)
            cand_lon = candidate.get("lon", 0)
            
            if primary_lat and primary_lon and cand_lat and cand_lon:
                distance = self._haversine_distance(
                    primary_lat, primary_lon,
                    cand_lat, cand_lon
                )
                
                if distance <= 500:  # Within 500km
                    matches.append(candidate)
        
        return matches
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km using Haversine formula"""
        R = 6371  # Earth radius in km
        
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        
        return R * c
    
    def _calculate_confidence(self, events: List[dict]) -> float:
        """Calculate correlation confidence score"""
        # More events = higher confidence
        event_score = min(len(events) / 5.0, 1.0) * 0.4
        
        # Temporal clustering
        timestamps = [e["timestamp"] for e in events]
        time_span = (max(timestamps) - min(timestamps)).total_seconds()
        temporal_score = max(1.0 - (time_span / self.correlation_window), 0) * 0.3
        
        # Spatial clustering
        lats = [e.get("lat", 0) for e in events if e.get("lat")]
        lons = [e.get("lon", 0) for e in events if e.get("lon")]
        
        if lats and lons:
            lat_spread = max(lats) - min(lats)
            lon_spread = max(lons) - min(lons)
            spatial_score = max(1.0 - ((lat_spread + lon_spread) / 10), 0) * 0.3
        else:
            spatial_score = 0.2
        
        return min(event_score + temporal_score + spatial_score, 1.0)
    
    def _calculate_severity(self, events: List[dict], rule: dict) -> str:
        """Calculate overall severity"""
        severity_map = {
            "INFORMATIONAL": 1,
            "SUSPICIOUS": 2,
            "ELEVATED": 3,
            "CRITICAL": 4,
            "CATASTROPHIC": 5
        }
        
        max_severity = 1
        for event in events:
            severity = event.get("severity", "INFORMATIONAL")
            max_severity = max(max_severity, severity_map.get(severity, 1))
        
        # Apply rule multiplier
        score = max_severity * rule.get("score_multiplier", 1.0)
        
        if score >= 8:
            return "CATASTROPHIC"
        elif score >= 6:
            return "CRITICAL"
        elif score >= 4:
            return "ELEVATED"
        elif score >= 2:
            return "SUSPICIOUS"
        else:
            return "INFORMATIONAL"
    
    async def _emit_correlation(self, rule_name: str, rule: dict, correlations: List[Dict]):
        """Emit correlated alert"""
        for correlation in correlations:
            alert = {
                "alert_id": str(uuid.uuid4()),
                "alert_type": "correlation",
                "rule_name": rule_name,
                "timestamp_utc": datetime.utcnow().isoformat(),
                "domains_involved": rule["domains"],
                "num_events": len(correlation["events"]),
                "confidence": correlation["confidence"],
                "severity": correlation["severity"],
                "description": f"Multi-domain correlation detected: {rule_name}",
                "events": correlation["events"],
                "recommended_actions": self._get_recommendations(rule_name, correlation["severity"])
            }
            
            await kafka_client.send_event("correlated-alerts", alert, key=alert["alert_id"])
            logger.info(f"Correlated alert: {rule_name} - Severity: {correlation['severity']}")
    
    def _get_recommendations(self, rule_name: str, severity: str) -> List[str]:
        """Get recommended actions based on correlation"""
        recommendations = {
            "weather_aviation_impact": [
                "Review flight diversions and delays",
                "Check weather forecasts for affected areas",
                "Monitor airport operational status"
            ],
            "cyber_physical_convergence": [
                "Escalate to security operations center",
                "Investigate potential coordinated attack",
                "Check for additional IOCs across networks"
            ],
            "space_weather_rf_impact": [
                "Monitor GPS accuracy degradation",
                "Check satellite communication systems",
                "Prepare for potential RF interference"
            ],
            "seismic_infrastructure_risk": [
                "Check critical infrastructure status",
                "Monitor for secondary effects",
                "Activate disaster response procedures"
            ],
            "maritime_cyber_hijack": [
                "Alert coast guard of potential vessel hijack",
                "Monitor for unexpected course changes",
                "Initiate cyber forensics on vessel communications"
            ],
            "aviation_gps_spoofing": [
                "Notify air traffic control of GPS anomalies",
                "Advise pilots to use alternative navigation",
                "Deploy SIGINT assets to locate interference source"
            ]
        }
        
        return recommendations.get(rule_name, ["Investigate correlated events"])
    
    async def emit_correlated_alerts(self):
        """Emit high-confidence correlated alerts"""
        while self.running:
            await asyncio.sleep(30)


if __name__ == "__main__":
    engine = EnhancedCorrelationEngine()
    asyncio.run(engine.start())
