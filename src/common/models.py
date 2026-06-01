import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class SourceType(str, Enum):
    adsb = "adsb"
    mode_s = "mode_s"
    sdr = "sdr"
    radar_fusion = "radar_fusion"
    simulated = "simulated"


class AircraftClassification(str, Enum):
    commercial = "commercial"
    military = "military"
    private = "private"
    cargo = "cargo"
    uav = "uav"
    helicopter = "helicopter"
    balloon = "balloon"
    unidentified = "unidentified"


class VesselType(str, Enum):
    cargo = "cargo"
    tanker = "tanker"
    passenger = "passenger"
    military = "military"
    fishing = "fishing"
    pleasure = "pleasure"
    unknown = "unknown"


class NavStatus(str, Enum):
    underway = "underway"
    at_anchor = "at_anchor"
    moored = "moored"
    aground = "aground"
    restricted = "restricted"
    unknown = "unknown"


class AISClass(str, Enum):
    A = "A"
    B = "B"


class ThreatLevel(str, Enum):
    informational = "INFORMATIONAL"
    suspicious = "SUSPICIOUS"
    elevated = "ELEVATED"
    critical = "CRITICAL"
    catastrophic = "CATASTROPHIC"


class FlightPlan(BaseModel):
    departure_airport: Optional[str] = None
    arrival_airport: Optional[str] = None
    filed_altitude_m: Optional[float] = None
    filed_speed_ms: Optional[float] = None
    route: Optional[List[dict]] = None
    departure_time: Optional[datetime] = None
    arrival_time: Optional[datetime] = None


class AirTrack(BaseModel):
    track_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    icao24: str
    callsign: Optional[str] = None
    origin_country: str = ""
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    lat: float = 0.0
    lon: float = 0.0
    baro_altitude_m: Optional[float] = None
    geo_altitude_m: Optional[float] = None
    velocity_ms: Optional[float] = None
    true_track_deg: Optional[float] = None
    vertical_rate_ms: Optional[float] = None
    squawk: Optional[str] = None
    on_ground: bool = False
    source: SourceType = SourceType.adsb
    classification: AircraftClassification = AircraftClassification.unidentified
    classification_confidence: float = 0.0
    sensors_contributing: List[str] = Field(default_factory=list)
    filed_flight_plan: Optional[FlightPlan] = None
    deviation_score: Optional[float] = None
    threat_flags: List[str] = Field(default_factory=list)


class VesselTrack(BaseModel):
    mmsi: str
    imo: Optional[str] = None
    vessel_name: str = ""
    vessel_type: VesselType = VesselType.unknown
    flag_state: str = ""
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    lat: float = 0.0
    lon: float = 0.0
    sog_knots: float = 0.0
    cog_deg: float = 0.0
    heading_deg: Optional[float] = None
    nav_status: NavStatus = NavStatus.unknown
    destination: Optional[str] = None
    eta_utc: Optional[datetime] = None
    draught_m: Optional[float] = None
    cargo_hazmat_class: Optional[str] = None
    ais_class: AISClass = AISClass.A
    last_seen_utc: datetime = Field(default_factory=datetime.utcnow)
    ais_gap_minutes: float = 0.0
    dark_vessel_suspect: bool = False
    anomaly_flags: List[str] = Field(default_factory=list)


class SeismicEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    lat: float
    lon: float
    depth_km: float
    magnitude: float
    magnitude_type: str = "ml"
    location_description: str = ""
    felt_reports: int = 0
    tsunami_warning: bool = False
    source: str = "usgs"


class RFAnomaly(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    freq_mhz: float
    bandwidth_hz: float = 0.0
    signal_strength_dbm: float = 0.0
    estimated_lat: Optional[float] = None
    estimated_lon: Optional[float] = None
    confidence: float = 0.0
    anomaly_type: str = "unknown"
    protocol_guess: Optional[str] = None
    burst_interval_ms: Optional[float] = None


class CyberEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    src_ip: str
    src_port: int = 0
    dst_port: int
    protocol: str = ""
    payload_hex: str = ""
    technique: Optional[str] = None
    target_sector: Optional[str] = None
    source_feed: str = "honeypot"
    severity: ThreatLevel = ThreatLevel.suspicious


class Alert(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_utc: datetime = Field(default_factory=datetime.utcnow)
    threat_class: ThreatLevel
    confidence: float = 0.0
    domain: str = ""
    description: str = ""
    source_event_ids: List[str] = Field(default_factory=list)
    compound_pattern: Optional[str] = None
    reasoning_chain: List[dict] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class CompoundThreat(BaseModel):
    threat_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    threat_class: ThreatLevel
    confidence: float
    reasoning_chain: List[dict] = Field(default_factory=list)
    compound_pattern: str = ""
    recommended_actions: List[str] = Field(default_factory=list)
    false_positive_probability: float = 0.0
