from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, JSON, Text, Enum as SAEnum, event, text, PrimaryKeyConstraint
import enum
from datetime import datetime
import uuid

from src.common.config import settings


engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ThreatLevelDB(enum.Enum):
    INFORMATIONAL = "INFORMATIONAL"
    SUSPICIOUS = "SUSPICIOUS"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"
    CATASTROPHIC = "CATASTROPHIC"


class AirTrackDB(Base):
    __tablename__ = "air_tracks"

    id = Column(String, default=lambda: str(uuid.uuid4()))
    icao24 = Column(String(6), nullable=False, index=True)
    callsign = Column(String, nullable=True)
    origin_country = Column(String, default="")
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    __table_args__ = (PrimaryKeyConstraint("id", "timestamp_utc"),)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    baro_altitude_m = Column(Float, nullable=True)
    geo_altitude_m = Column(Float, nullable=True)
    velocity_ms = Column(Float, nullable=True)
    true_track_deg = Column(Float, nullable=True)
    vertical_rate_ms = Column(Float, nullable=True)
    squawk = Column(String, nullable=True)
    on_ground = Column(Boolean, default=False)
    source = Column(String, default="adsb")
    classification = Column(String, default="unidentified")
    classification_confidence = Column(Float, default=0.0)
    sensors_contributing = Column(JSON, default=list)
    deviation_score = Column(Float, nullable=True)
    threat_flags = Column(JSON, default=list)

class VesselTrackDB(Base):
    __tablename__ = "vessel_tracks"

    id = Column(String, default=lambda: str(uuid.uuid4()))
    mmsi = Column(String(9), nullable=False, index=True)
    imo = Column(String, nullable=True)
    vessel_name = Column(String, default="")
    vessel_type = Column(String, default="unknown")
    flag_state = Column(String, default="")
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    __table_args__ = (PrimaryKeyConstraint("id", "timestamp_utc"),)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    sog_knots = Column(Float, default=0.0)
    cog_deg = Column(Float, default=0.0)
    heading_deg = Column(Float, nullable=True)
    nav_status = Column(String, default="unknown")
    destination = Column(String, nullable=True)
    eta_utc = Column(DateTime(timezone=True), nullable=True)
    draught_m = Column(Float, nullable=True)
    cargo_hazmat_class = Column(String, nullable=True)
    ais_class = Column(String, default="A")
    last_seen_utc = Column(DateTime(timezone=True), nullable=False)
    ais_gap_minutes = Column(Float, default=0.0)
    dark_vessel_suspect = Column(Boolean, default=False)
    anomaly_flags = Column(JSON, default=list)

class SeismicEventDB(Base):
    __tablename__ = "seismic_events"

    id = Column(String, default=lambda: str(uuid.uuid4()))
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    __table_args__ = (PrimaryKeyConstraint("id", "timestamp_utc"),)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    depth_km = Column(Float, nullable=False)
    magnitude = Column(Float, nullable=False)
    magnitude_type = Column(String, default="ml")
    location_description = Column(String, default="")
    felt_reports = Column(Integer, default=0)
    tsunami_warning = Column(Boolean, default=False)
    source = Column(String, default="usgs")

class AlertDB(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp_utc = Column(DateTime(timezone=True), nullable=False, index=True)
    threat_class = Column(String, nullable=False)
    confidence = Column(Float, default=0.0)
    domain = Column(String, default="")
    description = Column(Text, default="")
    source_event_ids = Column(JSON, default=list)
    compound_pattern = Column(String, nullable=True)
    reasoning_chain = Column(JSON, default=list)
    recommended_actions = Column(JSON, default=list)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String, nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)


class ResponseActionDB(Base):
    __tablename__ = "response_actions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action_type = Column(String, nullable=False)
    target_id = Column(String, nullable=True)
    requested_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    requested_by = Column(String, nullable=False)
    approvals = Column(JSON, default=list) # List of operator_ids
    required_approvals = Column(Integer, default=2)
    status = Column(String, default="PENDING") # PENDING, APPROVED, EXECUTED, CANCELLED
    metadata_json = Column(JSON, default=dict)


class MissileSpecDB(Base):
    __tablename__ = "missile_specs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True, index=True)
    nato_designation = Column(String, nullable=True)
    operator_country = Column(String, nullable=False, index=True)
    missile_type = Column(String, nullable=False, index=True)
    max_range_km = Column(Float, nullable=False)
    min_range_km = Column(Float, default=0.0)
    speed_mach = Column(Float, nullable=False)
    apogee_km = Column(Float, nullable=True)
    cep_m = Column(Float, nullable=True)
    payload_kg = Column(Float, nullable=True)
    warhead_types = Column(JSON, default=list)
    launch_method = Column(String, default="unknown")
    guidance_type = Column(String, default="inertial")
    boost_phase_s = Column(Float, nullable=True)
    midcourse_phase_s = Column(Float, nullable=True)
    terminal_phase_s = Column(Float, nullable=True)
    operational_status = Column(String, default="unknown")
    first_test_date = Column(String, nullable=True)
    ioc_date = Column(String, nullable=True)
    sources = Column(JSON, default=list)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class MissileEventDB(Base):
    __tablename__ = "missile_events"

    id = Column(String, default=lambda: str(uuid.uuid4()))
    launch_time = Column(DateTime(timezone=True), nullable=True, index=True)
    detection_time = Column(DateTime(timezone=True), nullable=True)
    impact_time = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (PrimaryKeyConstraint("id", "launch_time"),)
    origin_country = Column(String, default="")
    origin_actor = Column(String, nullable=True)
    launch_lat = Column(Float, nullable=True)
    launch_lon = Column(Float, nullable=True)
    launch_location_name = Column(String, nullable=True)
    target_country = Column(String, default="")
    target_lat = Column(Float, nullable=True)
    target_lon = Column(Float, nullable=True)
    target_name = Column(String, nullable=True)
    missile_type = Column(String, nullable=True, index=True)
    missile_count = Column(Integer, default=1)
    status = Column(String, default="unknown")
    intercepted_count = Column(Integer, default=0)
    interception_system = Column(String, nullable=True)
    damage_assessment = Column(Text, nullable=True)
    casualties_reported = Column(String, nullable=True)
    estimated_range_km = Column(Float, nullable=True)
    flight_duration_s = Column(Float, nullable=True)
    headline = Column(Text, default="")
    source_url = Column(Text, default="")
    source_name = Column(String, default="")
    validation_status = Column(String, default="unverified")
    corroborating_sources = Column(JSON, default=list)
    conflict_context = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    ingested_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    # Trajectory cache (JSON array of TrajectoryPoint dicts)
    trajectory_cache = Column(JSON, nullable=True)


class DefenseSystemDB(Base):
    __tablename__ = "defense_systems"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    system_type = Column(String, nullable=False)
    platform_name = Column(String, nullable=False)
    operator_country = Column(String, nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    location_name = Column(String, nullable=True)
    radar_range_km = Column(Float, nullable=True)
    intercept_range_km = Column(Float, nullable=True)
    intercept_altitude_max_km = Column(Float, nullable=True)
    interceptor_type = Column(String, nullable=True)
    engagement_envelope = Column(JSON, nullable=True)
    operational_status = Column(String, default="operational")
    sources = Column(JSON, default=list)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


def _create_hypertable(target, connection, **kw):
    connection.execute(text(f"SELECT create_hypertable('{target.name}', 'timestamp_utc', if_not_exists => TRUE)"))


_models_with_hypertables = []


def register_hypertable(model):
    _models_with_hypertables.append(model)
    event.listen(model.__table__, "after_create", _create_hypertable)


register_hypertable(AirTrackDB)
register_hypertable(VesselTrackDB)
register_hypertable(SeismicEventDB)
register_hypertable(MissileEventDB)


async def init_db():
    async with engine.begin() as conn:
        for tbl in ("air_tracks", "vessel_tracks", "seismic_events", "missile_events"):
            await conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
