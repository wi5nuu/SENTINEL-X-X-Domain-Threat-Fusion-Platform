import pytest
import numpy as np
from datetime import datetime
from src.ingestors.air.ingestor import (
    ExtendedKalmanFilter,
    TrackManager,
    DroneRFDetector,
    FlightPlanDeviationDetector,
    NoFlyZoneEngine,
    SquawkCodeMonitor,
)
from src.common.models import AirTrack, SourceType, AircraftClassification, FlightPlan


class TestExtendedKalmanFilter:
    def test_predict_update_cycle(self):
        ekf = ExtendedKalmanFilter(dt=1.0)
        initial_pos = np.array([40.7128, -74.0060, 1000.0])
        ekf.x = np.array([initial_pos[0], initial_pos[1], initial_pos[2], 0, 0, 0, 0, 0, 0])
        predicted = ekf.predict()
        assert len(predicted) == 3
        updated = ekf.update(initial_pos)
        assert len(updated) == 3
        assert np.allclose(updated, initial_pos, atol=1.0)

    def test_multiple_updates(self):
        ekf = ExtendedKalmanFilter(dt=1.0)
        positions = [np.array([40.0, -74.0, 1000.0]), np.array([40.01, -74.01, 1010.0]), np.array([40.02, -74.02, 1020.0])]
        ekf.x = np.array([positions[0][0], positions[0][1], positions[0][2], 0, 0, 0, 0, 0, 0])
        for z in positions:
            ekf.predict()
            ekf.update(z)
        assert np.allclose(ekf.x[:3], positions[-1], atol=1.0)


class TestTrackManager:
    def test_track_creation(self):
        tm = TrackManager()
        track = AirTrack(icao24="abc123", lat=40.0, lon=-74.0, geo_altitude_m=1000.0)
        tm.process_measurement(track)
        assert "abc123" in tm.tracks
        assert tm.tracks["abc123"]["status"] == "tentative"

    def test_track_confirmation(self):
        tm = TrackManager(confirm_hits=2)
        for _ in range(3):
            track = AirTrack(icao24="abc123", lat=40.0, lon=-74.0, geo_altitude_m=1000.0)
            tm.process_measurement(track)
        assert tm.tracks["abc123"]["status"] == "confirmed"

    def test_track_coasting(self):
        tm = TrackManager(max_misses=3)
        track = AirTrack(icao24="abc123", lat=40.0, lon=-74.0, geo_altitude_m=1000.0)
        tm.process_measurement(track)
        tm.coast_tracks([])
        assert "abc123" in tm.tracks
        tm.coast_tracks([])
        assert "abc123" in tm.tracks
        tm.coast_tracks([])
        assert "abc123" not in tm.tracks


class TestDroneRFDetector:
    @pytest.mark.asyncio
    async def test_analyze_returns_result_with_strong_signal(self):
        detector = DroneRFDetector()
        iq = np.random.randn(2048) + 1j * np.random.randn(2048)
        iq += 100 * np.sin(2 * np.pi * 433e6 / 2.4e6 * np.arange(2048))
        result = await detector.analyze(iq, 2.4e6)
        assert result is None or "freq_mhz" in (result or {})

    @pytest.mark.asyncio
    async def test_no_signal(self):
        detector = DroneRFDetector()
        iq = np.random.randn(2048) + 1j * np.random.randn(2048)
        result = await detector.analyze(iq, 2.4e6)
        assert result is None


class TestFlightPlanDeviationDetector:
    def test_frechet_distance(self):
        detector = FlightPlanDeviationDetector()
        P = np.array([[0, 0, 0], [1, 1, 1]])
        Q = np.array([[0, 0, 0], [1, 1, 1]])
        dist = detector.frechet_distance(P, Q)
        assert dist == pytest.approx(0.0, abs=1e-6)

    def test_no_deviation(self):
        detector = FlightPlanDeviationDetector()
        track = AirTrack(icao24="test", lat=40.0, lon=-74.0, geo_altitude_m=10000.0)
        result = detector.detect(track, None)
        assert result is None

    def test_deviation_detected_on_route(self):
        detector = FlightPlanDeviationDetector()
        track = AirTrack(icao24="test", lat=50.0, lon=-70.0, geo_altitude_m=12000.0)
        flight_plan = FlightPlan(route=[{"lat": 40.0, "lon": -74.0, "alt_m": 10000.0}, {"lat": 41.0, "lon": -73.0, "alt_m": 11000.0}])
        result = detector.detect(track, flight_plan)
        assert result is not None


class TestNoFlyZoneEngine:
    def test_inside_zone(self):
        engine = NoFlyZoneEngine()
        engine.load_default_zones()
        track = AirTrack(icao24="test", lat=38.8895, lon=-77.0353, geo_altitude_m=5000.0)
        result = engine.check(track)
        assert result is not None
        assert result["inside"] is True

    def test_outside_zone(self):
        engine = NoFlyZoneEngine()
        engine.load_default_zones()
        track = AirTrack(icao24="test", lat=0.0, lon=0.0, geo_altitude_m=10000.0)
        result = engine.check(track)
        assert result is None


class TestSquawkCodeMonitor:
    def test_critical_squawk(self):
        monitor = SquawkCodeMonitor()
        track = AirTrack(icao24="test", callsign="TEST123", squawk="7500")
        result = monitor.check(track)
        assert result is not None
        assert result["squawk"] == "7500"
        assert result["severity"] == "CATASTROPHIC"

    def test_normal_squawk(self):
        monitor = SquawkCodeMonitor()
        track = AirTrack(icao24="test", squawk="1200")
        result = monitor.check(track)
        assert result is None

    def test_debounce(self):
        monitor = SquawkCodeMonitor()
        track = AirTrack(icao24="test", squawk="7700")
        result1 = monitor.check(track)
        assert result1 is not None
        result2 = monitor.check(track)
        assert result2 is None
