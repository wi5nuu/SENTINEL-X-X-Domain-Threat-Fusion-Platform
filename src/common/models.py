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


# ─── Missile Intelligence Models ───────────────────────────────────────────

class MissilePhase(str, Enum):
    boost = "boost"
    midcourse = "midcourse"
    terminal = "terminal"
    impact = "impact"
    intercepted = "intercepted"


class MissileStatus(str, Enum):
    launched = "launched"
    in_flight = "in_flight"
    impacted = "impacted"
    intercepted = "intercepted"
    failed = "failed"
    test = "test"
    unknown = "unknown"


class ValidationStatus(str, Enum):
    verified = "verified"
    corroborated = "corroborated"   # multiple sources agree
    unverified = "unverified"       # single source, not yet cross-checked
    disputed = "disputed"           # conflicting reports
    retracted = "retracted"


class SimulationMode(str, Enum):
    historical = "historical"   # replay of a real event
    live = "live"               # extrapolation of an active event
    what_if = "what_if"         # hypothetical scenario


class MissileSpec(BaseModel):
    """Verified missile capability record — sourced from OSINT / public references."""
    spec_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                                       # e.g. "Hwasong-17"
    nato_designation: Optional[str] = None          # e.g. "KN-22"
    operator_country: str                           # ISO 3166-1 alpha-3 e.g. "PRK"
    missile_type: str                               # ICBM / IRBM / MRBM / SRBM / cruise / HGV / SLBM
    max_range_km: float
    min_range_km: float = 0.0
    speed_mach: float                               # approximate average speed
    apogee_km: Optional[float] = None              # max altitude in flight
    cep_m: Optional[float] = None                  # circular error probable
    payload_kg: Optional[float] = None
    warhead_types: List[str] = Field(default_factory=list)  # ["HE", "nuclear_capable", "cluster"]
    launch_method: str = "unknown"                 # road_mobile_TEL, silo, submarine, air_launched
    guidance_type: str = "inertial"               # inertial, GPS, terrain_contour, stellar, electro_optical
    boost_phase_s: Optional[float] = None          # seconds
    midcourse_phase_s: Optional[float] = None
    terminal_phase_s: Optional[float] = None
    operational_status: str = "unknown"           # operational, developmental, retired, test_only
    first_test_date: Optional[str] = None
    ioc_date: Optional[str] = None                # initial operating capability
    sources: List[str] = Field(default_factory=list)  # e.g. ["CSIS Missile Defense Project"]
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MissileEvent(BaseModel):
    """Real-world missile launch/attack event from OSINT sources."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    # Temporal
    launch_time: Optional[datetime] = None
    detection_time: Optional[datetime] = None
    impact_time: Optional[datetime] = None
    # Origin
    origin_country: str = ""
    origin_actor: Optional[str] = None            # e.g. "Iran IRGC" or "Houthi (Ansar Allah)"
    launch_lat: Optional[float] = None
    launch_lon: Optional[float] = None
    launch_location_name: Optional[str] = None
    # Target
    target_country: str = ""
    target_lat: Optional[float] = None
    target_lon: Optional[float] = None
    target_name: Optional[str] = None             # e.g. "Tel Aviv", "Patriot Battery Alpha"
    # Missile
    missile_type: Optional[str] = None            # FK to MissileSpec.name
    missile_count: int = 1
    # Outcome
    status: MissileStatus = MissileStatus.unknown
    intercepted_count: int = 0
    interception_system: Optional[str] = None     # e.g. "Iron Dome", "Arrow-3"
    damage_assessment: Optional[str] = None
    casualties_reported: Optional[str] = None
    # Distance & flight
    estimated_range_km: Optional[float] = None
    flight_duration_s: Optional[float] = None
    # Provenance
    headline: str = ""
    source_url: str = ""
    source_name: str = ""
    validation_status: ValidationStatus = ValidationStatus.unverified
    corroborating_sources: List[str] = Field(default_factory=list)
    # Event context
    conflict_context: Optional[str] = None       # e.g. "Iran-Israel escalation cycle"
    notes: Optional[str] = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)


class DefenseSystem(BaseModel):
    """Missile defense / early warning system record."""
    system_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str                                     # e.g. "THAAD Battery Alpha"
    system_type: str                              # SAM / ABM / SHORAD / EarlyWarning / Radar
    platform_name: str                            # e.g. "THAAD", "S-400", "Iron Dome"
    operator_country: str
    lat: float
    lon: float
    location_name: Optional[str] = None
    radar_range_km: Optional[float] = None
    intercept_range_km: Optional[float] = None
    intercept_altitude_max_km: Optional[float] = None
    interceptor_type: Optional[str] = None       # e.g. "PAC-3 MSE", "SM-3 Block IIA"
    engagement_envelope: Optional[dict] = None   # {"min_alt_km": x, "max_alt_km": y, "azimuth": [0,360]}
    operational_status: str = "operational"
    sources: List[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TrajectoryPoint(BaseModel):
    """Single computed waypoint along a missile trajectory."""
    time_s: float                   # seconds from launch
    lat: float
    lon: float
    altitude_km: float
    speed_ms: float
    phase: MissilePhase
    downrange_km: float             # distance from launch point


class MissileTrajectory(BaseModel):
    """Computed full trajectory for a missile event or simulation."""
    trajectory_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: Optional[str] = None
    mode: SimulationMode
    missile_spec_name: str
    launch_lat: float
    launch_lon: float
    target_lat: float
    target_lon: float
    total_range_km: float
    total_flight_s: float
    points: List[TrajectoryPoint] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    # Interception analysis
    threatened_defense_systems: List[str] = Field(default_factory=list)
    estimated_intercept_probability: float = 0.0
    intercept_point: Optional[TrajectoryPoint] = None
