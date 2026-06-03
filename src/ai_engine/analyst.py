import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict

import numpy as np
from src.common.models import Alert, AirTrack, VesselTrack, ThreatLevel

logger = logging.getLogger("sentinel-analyst")

class SentinelAnalyst:
    """
    Tactical AI Analyst for Sentinel-X.
    Uses RAG (Retrieval-Augmented Generation) to provide situational awareness
    and answer operator queries based on real-time sensor data and alerts.
    """

    def __init__(self, model_name: str = "gpt2", use_mock: bool = True):
        self.model_name = model_name
        self.use_mock = use_mock
        self.alert_history: List[Alert] = []
        self.track_history: Dict[str, List] = {"air": [], "maritime": []}
        self.max_history = 100
        
        if not self.use_mock:
            try:
                from transformers import pipeline
                self.generator = pipeline("text-generation", model=model_name)
                logger.info(f"Sentinel Analyst initialized with model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load transformers model: {e}. Falling back to mock mode.")
                self.use_mock = True

    def add_alert(self, alert: Alert):
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)

    def add_track(self, domain: str, track):
        if domain in self.track_history:
            self.track_history[domain].append(track)
            if len(self.track_history[domain]) > self.max_history:
                self.track_history[domain].pop(0)

    def _get_context(self) -> str:
        """Constructs a text-based context from recent data."""
        context = "TACTICAL CONTEXT:\n"
        
        # Recent Critical/Catastrophic Alerts
        critical_alerts = [a for a in self.alert_history if a.threat_class in [ThreatLevel.critical, ThreatLevel.catastrophic]][-5:]
        if critical_alerts:
            context += "CRITICAL ALERTS:\n"
            for a in critical_alerts:
                context += f"- [{a.timestamp_utc.isoformat()}] {a.domain}: {a.description} (Conf: {a.confidence})\n"
        
        # Threat Counts
        threat_counts = {}
        for a in self.alert_history:
            threat_counts[a.threat_class.value] = threat_counts.get(a.threat_class.value, 0) + 1
        
        context += f"CURRENT THREAT PROFILE: {json.dumps(threat_counts)}\n"
        
        # Recent Tracks
        air_count = len(self.track_history["air"])
        maritime_count = len(self.track_history["maritime"])
        context += f"ACTIVE TRACKS: {air_count} Air, {maritime_count} Maritime\n"
        
        return context

    async def query(self, user_query: str) -> str:
        """Answers a user query using tactical context."""
        context = self._get_context()
        prompt = f"{context}\nOPERATOR QUERY: {user_query}\nANALYST RESPONSE:"
        
        if self.use_mock:
            await asyncio.sleep(0.5) # Simulate thinking
            return self._generate_mock_response(user_query)
        
        try:
            result = self.generator(prompt, max_new_tokens=100, num_return_sequences=1)
            response = result[0]['generated_text'].replace(prompt, "").strip()
            return response
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return "ERROR: Tactical inference engine failed. Reverting to manual protocol."

    def _generate_mock_response(self, query: str) -> str:
        """Generates realistic mock responses for tactical scenarios."""
        q = query.lower()
        if "status" in q or "situation" in q:
            crit_count = len([a for a in self.alert_history if a.threat_class in [ThreatLevel.critical, ThreatLevel.catastrophic]])
            return f"Currently monitoring {len(self.alert_history)} active alerts. There are {crit_count} critical threats requiring immediate attention. Airspace and maritime sectors are active with {len(self.track_history['air'])} and {len(self.track_history['maritime'])} tracks respectively."
        if "missile" in q or "threat" in q:
            return "Analyzing threat trajectories. Several high-velocity tracks detected in Sector-7. Recommend activating layered ABM defense and notifying regional command."
        if "cyber" in q:
            return "Cyber domain showing increased probing activity on ICS ports. Lateral movement not yet confirmed, but recommend air-gapping critical infrastructure."
        
        return "Tactical Analyst at your service. Context received. Please specify coordinates or domain for deeper analysis."

    async def get_situational_awareness(self) -> str:
        """Generates a high-level situational awareness summary."""
        return await self.query("Provide a situational awareness summary of the last 15 minutes.")

analyst = SentinelAnalyst()
