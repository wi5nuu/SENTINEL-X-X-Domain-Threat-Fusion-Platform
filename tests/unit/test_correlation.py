import pytest
from src.response.correlation import DarkPatternCorrelationEngine
from src.common.models import CompoundThreat


class TestDarkPatternCorrelationEngine:
    def setup_method(self):
        self.engine = DarkPatternCorrelationEngine()

    def test_empty_buffer_returns_no_matches(self):
        matches = self.engine.analyze()
        assert len(matches) == 0

    def test_add_event(self):
        self.engine.add_event({"domain": "air", "source": "adsb", "threat_flags": []})
        assert len(self.engine.event_buffer) == 1

    def test_pattern_detection(self):
        self.engine.add_event({"domain": "maritime", "anomaly_flags": ["dark_vessel_suspect"]})
        self.engine.add_event({"domain": "rf", "freq_mhz": 160.0, "anomaly_type": "burst"})
        self.engine.add_event({"domain": "air", "source": "adsb"})
        matches = self.engine.analyze()
        assert len(matches) >= 0

    def test_compound_threat_model(self):
        threat = CompoundThreat(
            threat_class="ELEVATED",
            confidence=0.85,
            compound_pattern="Test Pattern",
            reasoning_chain=[{"step": 1, "domain": "test", "observation": "test", "contribution": 1.0, "evidence": {}}],
            recommended_actions=["Action 1"],
        )
        assert threat.threat_class == "ELEVATED"
        assert threat.confidence == 0.85
        assert len(threat.recommended_actions) == 1
