from datetime import datetime, timedelta
from typing import Optional, List, Dict
from src.common.models import ThreatLevel

THREAT_MATRIX = {
    ThreatLevel.informational: {
        "color": "#6B7280",
        "auto_action": ["log_to_database"],
        "operator_notify": False,
        "sla_response_minutes": None,
        "escalation_trigger": "5_same_type_in_1h",
    },
    ThreatLevel.suspicious: {
        "color": "#F59E0B",
        "auto_action": ["log", "notify_operator_websocket"],
        "operator_notify": True,
        "sla_response_minutes": 30,
        "escalation_trigger": "unacknowledged_15min OR compound_with_other_domain",
    },
    ThreatLevel.elevated: {
        "color": "#EF4444",
        "auto_action": ["log", "notify_all_operators", "begin_recording_all_feeds"],
        "operator_notify": True,
        "mandatory_review": True,
        "sla_response_minutes": 10,
        "escalation_trigger": "unacknowledged_5min OR threat_score_increases",
    },
    ThreatLevel.critical: {
        "color": "#DC2626",
        "auto_action": ["log_blockchain", "broadcast_all_channels", "activate_playbook"],
        "external_notification": ["command_center_api", "sms_duty_officer"],
        "sla_response_minutes": 3,
        "requires_two_operator_confirm": True,
    },
    ThreatLevel.catastrophic: {
        "color": "#7F1D1D",
        "auto_action": ["log_blockchain_immediate", "full_emergency_protocol",
                        "activate_all_playbooks", "external_api_push", "siren_stub"],
        "external_notification": ["ALL_CHANNELS"],
        "sla_response_minutes": 1,
        "cannot_be_suppressed": True,
        "auto_escalate_external": True,
    },
}

SQUAWK_SEVERITY = {
    "7500": ThreatLevel.catastrophic,
    "7600": ThreatLevel.elevated,
    "7700": ThreatLevel.critical,
    "7777": ThreatLevel.critical,
}


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
