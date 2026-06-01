from datetime import datetime, timedelta
from typing import Optional, List
import networkx as nx

from src.common.logging import setup_logging
from src.common.models import ThreatLevel, CompoundThreat

logger = setup_logging("correlation-engine")

COMPOUND_PATTERNS = {
    "Maritime Deception Stack": {
        "threat_score": 75,
        "threat_class": ThreatLevel.elevated,
        "conditions": [
            {"domain": "maritime", "flag": "dark_vessel_suspect", "time_window_minutes": 30},
            {"domain": "rf", "freq_range_mhz": (156, 174)},
            {"domain": "air", "min_tracks": 1, "max_distance_nm": 50},
        ],
    },
    "Infrastructure Attack Precursor": {
        "threat_score": 85,
        "threat_class": ThreatLevel.critical,
        "conditions": [
            {"domain": "rf", "type": "gps_jamming"},
            {"domain": "cyber", "target_sector": "power_grid", "time_window_hours": 1},
            {"domain": "maritime", "flag": "loitering", "near_infrastructure": True},
        ],
    },
    "Pre-Launch Warning": {
        "threat_score": 95,
        "threat_class": ThreatLevel.catastrophic,
        "conditions": [
            {"domain": "air", "min_unidentified": 2},
            {"domain": "rf", "type": "abnormal_radar"},
            {"domain": "cyber", "type": "comms_blackout"},
        ],
    },
}


class DarkPatternCorrelationEngine:
    def __init__(self):
        self.graph = nx.Graph()
        self.event_buffer: List[dict] = []
        self.buffer_max_size = 10000
        self.time_window = timedelta(hours=2)

    def add_event(self, event: dict):
        self.event_buffer.append(event)
        if len(self.event_buffer) > self.buffer_max_size:
            self.event_buffer = self.event_buffer[-self.buffer_max_size:]
        cutoff = datetime.utcnow() - self.time_window
        self.event_buffer = [e for e in self.event_buffer if self._parse_time(e) > cutoff]

    def _parse_time(self, event: dict) -> datetime:
        ts = event.get("timestamp_utc", "")
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                return datetime.utcnow()
        return ts or datetime.utcnow()

    def analyze(self) -> List[CompoundThreat]:
        matches = []
        for pattern_name, pattern in COMPOUND_PATTERNS.items():
            if self._match_pattern(pattern):
                threat = CompoundThreat(
                    threat_class=pattern["threat_class"],
                    confidence=pattern["threat_score"] / 100.0,
                    compound_pattern=pattern_name,
                    reasoning_chain=self._build_reasoning_chain(pattern_name, pattern),
                    recommended_actions=self._get_recommendations(pattern_name),
                )
                matches.append(threat)
        return matches

    def _match_pattern(self, pattern: dict) -> bool:
        conditions_met = 0
        for condition in pattern["conditions"]:
            if self._check_condition(condition):
                conditions_met += 1
        required = max(1, len(pattern["conditions"]) - 1)
        return conditions_met >= required

    def _check_condition(self, condition: dict) -> bool:
        domain = condition.get("domain", "")
        domain_events = [e for e in self.event_buffer if e.get("domain", e.get("source", "")).startswith(domain)]
        if not domain_events:
            return False
        if "flag" in condition:
            flag = condition["flag"]
            for e in domain_events:
                e_flags = e.get("anomaly_flags", []) + e.get("threat_flags", [])
                if any(flag in f for f in e_flags):
                    return True
            return False
        if "type" in condition:
            event_type = condition["type"]
            for e in domain_events:
                e_type = e.get("type", e.get("anomaly_type", ""))
                if event_type in e_type:
                    return True
            return False
        if "freq_range_mhz" in condition:
            lo, hi = condition["freq_range_mhz"]
            for e in domain_events:
                freq = e.get("freq_mhz", 0)
                if lo <= freq <= hi:
                    return True
            return False
        if "target_sector" in condition:
            for e in domain_events:
                if e.get("target_sector") == condition["target_sector"]:
                    return True
            return False
        return True

    def _build_reasoning_chain(self, pattern_name: str, pattern: dict) -> List[dict]:
        chain = []
        for i, condition in enumerate(pattern["conditions"]):
            chain.append({
                "step": i + 1,
                "domain": condition["domain"],
                "observation": f"Condition matched: {json.dumps(condition)}",
                "contribution": round(1.0 / len(pattern["conditions"]), 2),
                "evidence": condition,
            })
        return chain

    def _get_recommendations(self, pattern_name: str) -> List[str]:
        recommendations = {
            "Maritime Deception Stack": [
                "Task ISR assets to area",
                "Coordinate with regional navy",
                "Notify port authority",
            ],
            "Infrastructure Attack Precursor": [
                "Alert infrastructure security team",
                "Increase cyber monitoring on ICS networks",
                "Dispatch patrol vessel to loitering vessel location",
            ],
            "Pre-Launch Warning": [
                "Raise DEFCON level",
                "Activate all air defense systems",
                "Notify national command authority",
            ],
        }
        return recommendations.get(pattern_name, ["Monitor situation", "Notify duty officer"])


import json
