"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-06-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table(
        "air_tracks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("icao24", sa.String(6), nullable=False, index=True),
        sa.Column("callsign", sa.String, nullable=True),
        sa.Column("origin_country", sa.String, server_default=""),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lon", sa.Float, nullable=False),
        sa.Column("baro_altitude_m", sa.Float, nullable=True),
        sa.Column("geo_altitude_m", sa.Float, nullable=True),
        sa.Column("velocity_ms", sa.Float, nullable=True),
        sa.Column("true_track_deg", sa.Float, nullable=True),
        sa.Column("vertical_rate_ms", sa.Float, nullable=True),
        sa.Column("squawk", sa.String, nullable=True),
        sa.Column("on_ground", sa.Boolean, server_default="false"),
        sa.Column("source", sa.String, server_default="adsb"),
        sa.Column("classification", sa.String, server_default="unidentified"),
        sa.Column("classification_confidence", sa.Float, server_default="0"),
        sa.Column("sensors_contributing", JSON, nullable=True),
        sa.Column("deviation_score", sa.Float, nullable=True),
        sa.Column("threat_flags", JSON, nullable=True),
    )
    op.execute("SELECT create_hypertable('air_tracks', 'timestamp_utc', if_not_exists => TRUE)")

    op.create_table(
        "vessel_tracks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("mmsi", sa.String(9), nullable=False, index=True),
        sa.Column("imo", sa.String, nullable=True),
        sa.Column("vessel_name", sa.String, server_default=""),
        sa.Column("vessel_type", sa.String, server_default="unknown"),
        sa.Column("flag_state", sa.String, server_default=""),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lon", sa.Float, nullable=False),
        sa.Column("sog_knots", sa.Float, server_default="0"),
        sa.Column("cog_deg", sa.Float, server_default="0"),
        sa.Column("heading_deg", sa.Float, nullable=True),
        sa.Column("nav_status", sa.String, server_default="unknown"),
        sa.Column("destination", sa.String, nullable=True),
        sa.Column("eta_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("draught_m", sa.Float, nullable=True),
        sa.Column("cargo_hazmat_class", sa.String, nullable=True),
        sa.Column("ais_class", sa.String, server_default="A"),
        sa.Column("last_seen_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ais_gap_minutes", sa.Float, server_default="0"),
        sa.Column("dark_vessel_suspect", sa.Boolean, server_default="false"),
        sa.Column("anomaly_flags", JSON, nullable=True),
    )
    op.execute("SELECT create_hypertable('vessel_tracks', 'timestamp_utc', if_not_exists => TRUE)")

    op.create_table(
        "seismic_events",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lon", sa.Float, nullable=False),
        sa.Column("depth_km", sa.Float, nullable=False),
        sa.Column("magnitude", sa.Float, nullable=False),
        sa.Column("magnitude_type", sa.String, server_default="ml"),
        sa.Column("location_description", sa.String, server_default=""),
        sa.Column("felt_reports", sa.Integer, server_default="0"),
        sa.Column("tsunami_warning", sa.Boolean, server_default="false"),
        sa.Column("source", sa.String, server_default="usgs"),
    )
    op.execute("SELECT create_hypertable('seismic_events', 'timestamp_utc', if_not_exists => TRUE)")

    op.create_table(
        "alerts",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("threat_class", sa.String, nullable=False),
        sa.Column("confidence", sa.Float, server_default="0"),
        sa.Column("domain", sa.String, server_default=""),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("source_event_ids", JSON, nullable=True),
        sa.Column("compound_pattern", sa.String, nullable=True),
        sa.Column("reasoning_chain", JSON, nullable=True),
        sa.Column("recommended_actions", JSON, nullable=True),
        sa.Column("acknowledged", sa.Boolean, server_default="false"),
        sa.Column("acknowledged_by", sa.String, nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table("alerts")
    op.drop_table("seismic_events")
    op.drop_table("vessel_tracks")
    op.drop_table("air_tracks")
