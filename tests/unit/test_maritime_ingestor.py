import pytest
from src.ingestors.maritime.ingestor import (
    AISParser,
    DarkVesselDetector,
    AnomalousBehaviorDetector,
    PortArrivalPredictor,
)
from src.common.models import VesselTrack, VesselType, NavStatus


class TestAISParser:
    def setup_method(self):
        self.parser = AISParser()

    def test_parse_invalid_nmea(self):
        result = self.parser.parse_nmea("invalid")
        assert result is None

    def test_decode_position_report(self):
        mmsi_val = 123456789
        bits = f"00000100{mmsi_val:030b}0000000000000000000100000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000111100000000111111111"
        bits = bits[:350]
        result = self.parser._decode_position_report(bits)
        assert result is not None
        assert "mmsi" in result
        assert result["mmsi"] == str(mmsi_val).zfill(9)

    def test_decode_static_voyage(self):
        mmsi_val = 123456789
        bits = f"00010100{mmsi_val:030b}" + "0" * 32
        bits = bits.ljust(400, "0")
        result = self.parser._decode_static_voyage(bits)
        assert result is not None
        assert result["mmsi"] == "123456789"

    def test_decode_class_b_position(self):
        mmsi_val = 123456789
        bits = f"01001000{mmsi_val:030b}" + "0" * 100
        bits = bits.ljust(200, "0")
        result = self.parser._decode_class_b_position(bits)
        assert result is not None
        assert result["ais_class"] == "B"


class TestDarkVesselDetector:
    def test_dark_vessel_detection(self):
        detector = DarkVesselDetector()
        from datetime import datetime, timedelta
        vessel = VesselTrack(
            mmsi="123456789",
            vessel_type=VesselType.cargo,
            last_seen_utc=datetime.utcnow() - timedelta(minutes=30),
        )
        result = detector.check(vessel)
        assert result is True

    def test_normal_vessel(self):
        detector = DarkVesselDetector()
        from datetime import datetime
        vessel = VesselTrack(
            mmsi="123456789",
            vessel_type=VesselType.cargo,
            last_seen_utc=datetime.utcnow(),
        )
        result = detector.check(vessel)
        assert result is False


class TestAnomalousBehaviorDetector:
    def setup_method(self):
        self.detector = AnomalousBehaviorDetector()

    def test_speed_anomaly_no_history(self):
        vessel = VesselTrack(mmsi="123456789", vessel_type=VesselType.cargo, sog_knots=25.0)
        result = self.detector.check_speed_anomaly(vessel, "test_area")
        assert result is None

    def test_loitering_not_detected_initially(self):
        vessel = VesselTrack(mmsi="123456789", lat=10.0, lon=20.0)
        result = self.detector.check_loitering(vessel)
        assert result is None

    def test_speed_draught_mismatch(self):
        vessel = VesselTrack(mmsi="123456789", draught_m=15.0, sog_knots=20.0)
        result = self.detector.check_speed_draught(vessel)
        assert result is not None

    def test_course_change_no_history(self):
        vessel = VesselTrack(mmsi="123456789", cog_deg=90.0)
        result = self.detector.check_course_change(vessel)
        assert result is None


class TestPortArrivalPredictor:
    def test_no_destination(self):
        predictor = PortArrivalPredictor()
        vessel = VesselTrack(mmsi="123456789", sog_knots=10.0)
        result = predictor.predict(vessel)
        assert result is None
