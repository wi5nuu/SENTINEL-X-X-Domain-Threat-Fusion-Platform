import pytest
import asyncio
from datetime import datetime
from src.ingestors.maritime.ingestor import MaritimeDomainIngestor, AISParser
from src.common.models import AirTrack, VesselTrack, SeismicEvent, ThreatLevel


@pytest.mark.asyncio
async def test_air_track_creation():
    track = AirTrack(
        icao24="abc123",
        callsign="TEST123",
        lat=40.7128,
        lon=-74.0060,
        geo_altitude_m=10000.0,
        velocity_ms=250.0,
    )
    assert track.track_id is not None
    assert track.icao24 == "abc123"
    assert track.source.value == "adsb"


@pytest.mark.asyncio
async def test_vessel_track_creation():
    vessel = VesselTrack(
        mmsi="123456789",
        vessel_name="MV TEST",
        lat=1.2789,
        lon=103.8390,
        sog_knots=15.5,
    )
    assert vessel.mmsi == "123456789"
    assert vessel.nav_status.value == "unknown"


@pytest.mark.asyncio
async def test_seismic_event_thresholds():
    event = SeismicEvent(
        lat=-20.0,
        lon=-175.0,
        depth_km=10.0,
        magnitude=7.8,
        location_description="Tonga Trench",
        tsunami_warning=True,
    )
    assert event.magnitude >= 7.5
    assert event.tsunami_warning is True
    assert event.depth_km < 70


@pytest.mark.asyncio
async def test_threat_level_enum():
    levels = [
        ThreatLevel.informational,
        ThreatLevel.suspicious,
        ThreatLevel.elevated,
        ThreatLevel.critical,
        ThreatLevel.catastrophic,
    ]
    names = [l.value for l in levels]
    assert "INFORMATIONAL" in names
    assert "CATASTROPHIC" in names
    assert len(names) == 5


@pytest.mark.asyncio
async def test_air_track_default_values():
    track = AirTrack(icao24="test01", lat=0.0, lon=0.0)
    assert track.on_ground is False
    assert track.classification.value == "unidentified"
    assert track.threat_flags == []
