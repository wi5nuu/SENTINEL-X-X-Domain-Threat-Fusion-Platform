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


def _create_hypertable(target, connection, **kw):
    connection.execute(text(f"SELECT create_hypertable('{target.name}', 'timestamp_utc', if_not_exists => TRUE)"))


_models_with_hypertables = []


def register_hypertable(model):
    _models_with_hypertables.append(model)
    event.listen(model.__table__, "after_create", _create_hypertable)


register_hypertable(AirTrackDB)
register_hypertable(VesselTrackDB)
register_hypertable(SeismicEventDB)


async def init_db():
    async with engine.begin() as conn:
        for tbl in ("air_tracks", "vessel_tracks", "seismic_events"):
            await conn.execute(text(f"DROP TABLE IF EXISTS {tbl} CASCADE"))
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
