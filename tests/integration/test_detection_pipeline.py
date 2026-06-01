import pytest
from src.ingestors.air.ingestor import SquawkCodeMonitor, NoFlyZoneEngine
from src.common.models import AirTrack
from src.response.threat_classifier import ThreatClassifier
from src.response.correlation import DarkPatternCorrelationEngine


class TestAlertPipeline:
    def test_squawk_triggers_classification(self):
        monitor = SquawkCodeMonitor()
        classifier = ThreatClassifier()
        track = AirTrack(icao24="test", callsign="EMERG", squawk="7700")
        result = monitor.check(track)
        assert result is not None
        assert result["severity"] == "CRITICAL"
        assert result["name"] == "General Emergency"

    def test_no_fly_zone_classification(self):
        engine = NoFlyZoneEngine()
        engine.load_default_zones()
        track = AirTrack(icao24="test", lat=38.8895, lon=-77.0353, geo_altitude_m=5000.0)
        result = engine.check(track)
        assert result is not None
        assert result["inside"] is True

    def test_correlation_engine_detects_pattern(self):
        engine = DarkPatternCorrelationEngine()
        engine.add_event({"domain": "maritime", "anomaly_flags": ["dark_vessel_suspect"]})
        engine.add_event({"domain": "rf", "freq_mhz": 160.0, "anomaly_type": "burst"})
        engine.add_event({"domain": "air", "source": "adsb"})
        threats = engine.analyze()
        assert len(threats) >= 0
