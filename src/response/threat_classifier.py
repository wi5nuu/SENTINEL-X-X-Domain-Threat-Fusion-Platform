from datetime import datetime, timedelta
from typing import Optional, List, Dict
from src.common.models import ThreatLevel

import yaml
from pathlib import Path
from src.common.logging import setup_logging

logger = setup_logging("threat-classifier")

_rules_path = Path(__file__).parent.parent.parent / "data" / "threat_intel" / "correlation_rules.yaml"
try:
    with open(_rules_path, "r", encoding="utf-8") as _f:
        _rules = yaml.safe_load(_f)
        _raw_matrix = _rules.get("threat_matrix", {})
        THREAT_MATRIX = {}
        for k, v in _raw_matrix.items():
            THREAT_MATRIX[ThreatLevel(k)] = v
        
        _raw_squawk = _rules.get("squawk_severity", {})
        SQUAWK_SEVERITY = {}
        for k, v in _raw_squawk.items():
            SQUAWK_SEVERITY[str(k)] = ThreatLevel(v)
except Exception as e:
    logger.error(f"Failed to load correlation_rules.yaml in classifier: {e}")
    THREAT_MATRIX = {}
    SQUAWK_SEVERITY = {}


class ThreatClassifier:
    def __init__(self):
        self.recent_alerts: Dict[str, List[datetime]] = {}

    def classify(self, event: dict) -> ThreatLevel:
        severity = event.get("severity", "").upper()
        if severity == "CATASTROPHIC":
            return ThreatLevel.catastrophic
        elif severity == "CRITICAL":
            return ThreatLevel.critical
        elif severity == "ELEVATED":
            return ThreatLevel.elevated
        elif severity == "SUSPICIOUS":
            return ThreatLevel.suspicious

        domain = event.get("domain", "")
        threat_flags = event.get("threat_flags", [])
        for flag in threat_flags:
            if flag.startswith("SQUAWK:"):
                squawk = flag.split(":")[1].split("-")[0]
                if squawk in SQUAWK_SEVERITY:
                    return SQUAWK_SEVERITY[squawk]

        anomaly_flags = event.get("anomaly_flags", [])
        if anomaly_flags:
            if any("loitering" in f for f in anomaly_flags):
                return ThreatLevel.suspicious
            if any("course_change" in f for f in anomaly_flags):
                return ThreatLevel.suspicious

        magnitude = event.get("magnitude", 0)
        if magnitude >= 7.5:
            return ThreatLevel.critical
        elif magnitude >= 6.5:
            return ThreatLevel.elevated
        elif magnitude >= 5.0:
            return ThreatLevel.suspicious

        return ThreatLevel.informational

    def should_escalate(self, threat: ThreatLevel, alert_id: str, event_type: str) -> bool:
        now = datetime.utcnow()
        key = f"{event_type}"
        if key not in self.recent_alerts:
            self.recent_alerts[key] = []
        self.recent_alerts[key].append(now)
        self.recent_alerts[key] = [t for t in self.recent_alerts[key] if now - t < timedelta(hours=1)]
        if len(self.recent_alerts[key]) >= 5 and threat == ThreatLevel.informational:
            return True
        return False


class EscalationEngine:
    def __init__(self):
        self.classifier = ThreatClassifier()

    def process_event(self, event: dict) -> dict:
        threat_class = self.classifier.classify(event)
        matrix = THREAT_MATRIX.get(threat_class, THREAT_MATRIX[ThreatLevel.informational])
        return {
            "threat_class": threat_class.value,
            "auto_actions": matrix["auto_action"],
            "operator_notify": matrix.get("operator_notify", False),
            "sla_response_minutes": matrix.get("sla_response_minutes"),
            "requires_confirmation": matrix.get("requires_two_operator_confirm", False),
        }
