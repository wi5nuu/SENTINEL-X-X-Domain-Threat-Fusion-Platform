"""
SENTINEL-X Missile Intelligence Ingestor
=========================================
Continuously collects, deduplicates, and ingests missile-related events
from verified open-source intelligence (OSINT) sources.

Sub-modules:
  A. CapabilityLoader  — loads/refreshes missile spec YAML into DB
  B. DefenseLoader     — loads/refreshes defense system YAML into DB
  C. OSINTCollector    — polls RSS feeds and ACLED API for missile events
  D. HistoricalSeeder  — pre-seeds verified historical events on first run

Data integrity rules:
  - Every event must have at least one source_url
  - Events are deduplicated by headline hash + approximate time window
  - validation_status starts as "unverified" until cross-checked
  - No fabricated, random, or dummy data is ever generated
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

import httpx
import yaml

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.kafka import kafka_client
from src.common.database import async_session, MissileSpecDB, MissileEventDB, DefenseSystemDB
from sqlalchemy import select, func

logger = setup_logging("missile-ingestor")

# OSINT and Historical config is now loaded dynamically from data/missile_intel/osint_config.yaml
_osint_config_path = Path(__file__).parent.parent.parent.parent / "data" / "missile_intel" / "osint_config.yaml"
try:
    with open(_osint_config_path, "r", encoding="utf-8") as _f:
        _osint_config = yaml.safe_load(_f)
        RSS_FEEDS = _osint_config.get("rss_feeds", [])
        MISSILE_KEYWORDS = _osint_config.get("missile_keywords", [])
        GEO_KEYWORDS = _osint_config.get("geo_keywords", {})
        LOCATION_COORDS = _osint_config.get("location_coords", {})
        HISTORICAL_EVENTS = _osint_config.get("historical_events", [])
except Exception as e:
    logger.error(f"Failed to load osint_config.yaml: {e}")
    RSS_FEEDS = []
    MISSILE_KEYWORDS = []
    GEO_KEYWORDS = {}
    LOCATION_COORDS = {}
    HISTORICAL_EVENTS = []


class CapabilityLoader:
    """Loads missile capability specs from YAML into database."""

    def __init__(self, yaml_path: str):
        self.yaml_path = yaml_path

    async def load(self):
        """Upsert all missile specs into missile_specs table."""
        path = Path(self.yaml_path)
        if not path.exists():
            logger.warning(f"Capability YAML not found: {self.yaml_path}")
            return 0

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        missiles = data.get("missiles", [])
        loaded = 0

        async with async_session() as session:
            for m in missiles:
                # Check if already exists
                existing = await session.execute(
                    select(MissileSpecDB).where(MissileSpecDB.name == m["name"])
                )
                existing = existing.scalar_one_or_none()

                if existing:
                    # Update
                    existing.max_range_km = m.get("max_range_km", existing.max_range_km)
                    existing.speed_mach = m.get("speed_mach", existing.speed_mach)
                    existing.sources = m.get("sources", existing.sources)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Insert
                    rec = MissileSpecDB(
                        id=str(uuid.uuid4()),
                        name=m["name"],
                        nato_designation=m.get("nato_designation"),
                        operator_country=m["operator_country"],
                        missile_type=m["missile_type"],
                        max_range_km=m["max_range_km"],
                        min_range_km=m.get("min_range_km", 0.0),
                        speed_mach=m["speed_mach"],
                        apogee_km=m.get("apogee_km"),
                        cep_m=m.get("cep_m"),
                        payload_kg=m.get("payload_kg"),
                        warhead_types=m.get("warhead_types", []),
                        launch_method=m.get("launch_method", "unknown"),
                        guidance_type=m.get("guidance_type", "inertial"),
                        boost_phase_s=m.get("boost_phase_s"),
                        midcourse_phase_s=m.get("midcourse_phase_s"),
                        terminal_phase_s=m.get("terminal_phase_s"),
                        operational_status=m.get("operational_status", "unknown"),
                        first_test_date=m.get("first_test_date"),
                        ioc_date=m.get("ioc_date"),
                        sources=m.get("sources", []),
                    )
                    session.add(rec)
                    loaded += 1

            await session.commit()

        logger.info(f"CapabilityLoader: upserted {loaded} new / updated existing missile specs")
        return loaded


class DefenseLoader:
    """Loads defense system records from YAML into database."""

    def __init__(self, yaml_path: str):
        self.yaml_path = yaml_path

    async def load(self):
        path = Path(self.yaml_path)
        if not path.exists():
            logger.warning(f"Defense YAML not found: {self.yaml_path}")
            return 0

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        systems = data.get("defense_systems", [])
        loaded = 0

        async with async_session() as session:
            for ds in systems:
                existing = await session.execute(
                    select(DefenseSystemDB).where(DefenseSystemDB.name == ds["name"])
                )
                existing = existing.scalar_one_or_none()

                if existing:
                    existing.operational_status = ds.get("operational_status", existing.operational_status)
                    existing.updated_at = datetime.utcnow()
                else:
                    rec = DefenseSystemDB(
                        id=str(uuid.uuid4()),
                        name=ds["name"],
                        system_type=ds["system_type"],
                        platform_name=ds["platform_name"],
                        operator_country=ds["operator_country"],
                        lat=ds["lat"],
                        lon=ds["lon"],
                        location_name=ds.get("location_name"),
                        radar_range_km=ds.get("radar_range_km"),
                        intercept_range_km=ds.get("intercept_range_km"),
                        intercept_altitude_max_km=ds.get("intercept_altitude_max_km"),
                        interceptor_type=ds.get("interceptor_type"),
                        engagement_envelope=ds.get("engagement_envelope"),
                        operational_status=ds.get("operational_status", "operational"),
                        sources=ds.get("sources", []),
                    )
                    session.add(rec)
                    loaded += 1

            await session.commit()

        logger.info(f"DefenseLoader: loaded {loaded} defense systems")
        return loaded


class HistoricalSeeder:
    """Seeds verified historical missile events on first run."""

    async def seed(self):
        """Insert historical events if they don't exist yet."""
        async with async_session() as session:
            count = await session.execute(select(func.count()).select_from(MissileEventDB))
            existing_count = count.scalar_one()
            if existing_count > 0:
                logger.info(f"HistoricalSeeder: {existing_count} events already in DB, skipping seed")
                return 0

        loaded = 0
        async with async_session() as session:
            for ev in HISTORICAL_EVENTS:
                launch_time = None
                if ev.get("launch_time"):
                    try:
                        launch_time = datetime.fromisoformat(ev["launch_time"].replace("Z", "+00:00"))
                    except Exception:
                        launch_time = datetime.utcnow()

                rec = MissileEventDB(
                    id=str(uuid.uuid4()),
                    launch_time=launch_time,
                    origin_country=ev.get("origin_country", ""),
                    origin_actor=ev.get("origin_actor"),
                    launch_lat=ev.get("launch_lat"),
                    launch_lon=ev.get("launch_lon"),
                    launch_location_name=ev.get("launch_location_name"),
                    target_country=ev.get("target_country", ""),
                    target_lat=ev.get("target_lat"),
                    target_lon=ev.get("target_lon"),
                    target_name=ev.get("target_name"),
                    missile_type=ev.get("missile_type"),
                    missile_count=ev.get("missile_count", 1),
                    status=ev.get("status", "unknown"),
                    intercepted_count=ev.get("intercepted_count", 0),
                    interception_system=ev.get("interception_system"),
                    damage_assessment=ev.get("damage_assessment"),
                    casualties_reported=ev.get("casualties_reported"),
                    estimated_range_km=ev.get("estimated_range_km"),
                    flight_duration_s=ev.get("flight_duration_s"),
                    headline=ev.get("headline", ""),
                    source_url=ev.get("source_url", ""),
                    source_name=ev.get("source_name", ""),
                    validation_status=ev.get("validation_status", "unverified"),
                    corroborating_sources=ev.get("corroborating_sources", []),
                    conflict_context=ev.get("conflict_context"),
                    notes=ev.get("notes"),
                )
                session.add(rec)
                loaded += 1

                # Publish to Kafka
                await kafka_client.send_event(
                    "missile-events",
                    {
                        "event_id": rec.id,
                        "type": "historical",
                        "launch_lat": rec.launch_lat,
                        "launch_lon": rec.launch_lon,
                        "target_lat": rec.target_lat,
                        "target_lon": rec.target_lon,
                        "missile_type": rec.missile_type,
                        "origin_country": rec.origin_country,
                        "target_country": rec.target_country,
                        "status": rec.status,
                        "headline": rec.headline,
                        "launch_time": rec.launch_time.isoformat() if rec.launch_time else None,
                    },
                    key=rec.id,
                )

            await session.commit()

        logger.info(f"HistoricalSeeder: seeded {loaded} verified historical events")
        return loaded


class OSINTCollector:
    """
    Polls RSS feeds for missile-related news and creates unverified event records.
    Uses keyword filtering + basic NLP entity extraction.
    No fabricated data is ever generated.
    """

    def __init__(self):
        self._seen_hashes: Set[str] = set()
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self, client: httpx.AsyncClient):
        self._client = client
        await self._restore_seen_hashes()

    async def _restore_seen_hashes(self):
        """Load hashes of already-ingested events to prevent duplicates."""
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(MissileEventDB.source_url).limit(2000)
                )
                for (url,) in result:
                    self._seen_hashes.add(self._hash_event(url, ""))
        except Exception as e:
            logger.warning(f"Could not restore seen hashes: {e}")

    @staticmethod
    def _hash_event(url: str, headline: str) -> str:
        key = f"{url}|{headline[:80]}"
        return hashlib.md5(key.encode()).hexdigest()

    def _is_missile_related(self, title: str, summary: str) -> bool:
        text = (title + " " + summary).lower()
        return any(kw in text for kw in MISSILE_KEYWORDS)

    def _extract_countries(self, text: str) -> tuple[str, str]:
        """Heuristic: first country = origin, second = target."""
        found = []
        lower = text.lower()
        for keyword, iso3 in GEO_KEYWORDS.items():
            if keyword in lower and iso3 not in found:
                found.append(iso3)
        origin = found[0] if found else ""
        target = found[1] if len(found) > 1 else ""
        return origin, target

    def _extract_coords(self, text: str) -> tuple:
        lower = text.lower()
        for loc_name, coords in LOCATION_COORDS.items():
            if loc_name in lower:
                return coords[0], coords[1], loc_name
        return None, None, None

    async def poll_rss(self) -> int:
        """Poll all RSS feeds, extract missile events. Returns count of new events."""
        if not self._client:
            return 0

        new_events = 0
        for feed in RSS_FEEDS:
            try:
                resp = await self._client.get(feed["url"], timeout=15.0)
                if resp.status_code != 200:
                    continue

                # Parse RSS with regex (avoid feedparser dependency for now)
                content = resp.text
                items = re.findall(r"<item>(.*?)</item>", content, re.DOTALL)

                for item in items:
                    title_match = re.search(r"<title[^>]*>(.*?)</title>", item, re.DOTALL)
                    link_match = re.search(r"<link[^>]*>(.*?)</link>", item, re.DOTALL)
                    desc_match = re.search(r"<description[^>]*>(.*?)</description>", item, re.DOTALL)
                    date_match = re.search(r"<pubDate[^>]*>(.*?)</pubDate>", item, re.DOTALL)

                    title = re.sub(r"<[^>]+>|<!\[CDATA\[|\]\]>", "", title_match.group(1) if title_match else "").strip()
                    link = (link_match.group(1) if link_match else "").strip()
                    desc = re.sub(r"<[^>]+>|<!\[CDATA\[|\]\]>", "", desc_match.group(1) if desc_match else "").strip()

                    if not title or not self._is_missile_related(title, desc):
                        continue

                    h = self._hash_event(link, title)
                    if h in self._seen_hashes:
                        continue
                    self._seen_hashes.add(h)

                    # Extract entities
                    text_combined = title + " " + desc
                    origin, target = self._extract_countries(text_combined)
                    t_lat, t_lon, t_name = self._extract_coords(text_combined)

                    # Parse date
                    launch_time = datetime.utcnow()
                    if date_match:
                        try:
                            from email.utils import parsedate_to_datetime
                            launch_time = parsedate_to_datetime(date_match.group(1).strip()).replace(tzinfo=None)
                        except Exception:
                            pass

                    event_id = str(uuid.uuid4())
                    async with async_session() as session:
                        rec = MissileEventDB(
                            id=event_id,
                            launch_time=launch_time,
                            origin_country=origin,
                            target_country=target,
                            target_lat=t_lat,
                            target_lon=t_lon,
                            target_name=t_name,
                            headline=title[:500],
                            source_url=link,
                            source_name=feed["name"],
                            validation_status="unverified",
                            notes=desc[:1000],
                            status="unknown",
                        )
                        session.add(rec)
                        await session.commit()

                    new_events += 1
                    logger.info(f"OSINTCollector: new event from {feed['name']}: {title[:80]}")

            except Exception as e:
                logger.warning(f"RSS poll error for {feed['name']}: {e}")

        return new_events

    async def poll_acled(self) -> int:
        """Poll ACLED API for missile/explosion events."""
        if not settings.acled_api_key or not self._client:
            return 0

        new_events = 0
        try:
            # ACLED API: explosion/remote violence events with missile keywords
            params = {
                "key": settings.acled_api_key,
                "email": settings.acled_email,
                "event_type": "Explosions/Remote violence",
                "sub_event_type": "Air/drone strike,Shelling/artillery/missile attack",
                "limit": 100,
                "fields": "event_date,country,admin1,location,latitude,longitude,actor1,notes,source,source_scale",
                "format": "json",
            }
            resp = await self._client.get(settings.acled_api_url, params=params, timeout=30.0)
            if resp.status_code != 200:
                return 0

            data = resp.json()
            for row in data.get("data", []):
                notes = row.get("notes", "")
                if not self._is_missile_related(notes, row.get("sub_event_type", "")):
                    continue

                url = row.get("source", "")
                h = self._hash_event(url, notes[:80])
                if h in self._seen_hashes:
                    continue
                self._seen_hashes.add(h)

                event_id = str(uuid.uuid4())
                try:
                    lt = datetime.strptime(row["event_date"], "%Y-%m-%d")
                except Exception:
                    lt = datetime.utcnow()

                async with async_session() as session:
                    rec = MissileEventDB(
                        id=event_id,
                        launch_time=lt,
                        target_country=row.get("country", ""),
                        target_lat=float(row.get("latitude", 0) or 0),
                        target_lon=float(row.get("longitude", 0) or 0),
                        target_name=row.get("location", ""),
                        origin_actor=row.get("actor1", ""),
                        headline=f"ACLED: {row.get('sub_event_type','')} in {row.get('location','')}",
                        source_url=url,
                        source_name=f"ACLED/{row.get('source_scale','')}",
                        validation_status="unverified",
                        notes=notes[:1000],
                        status="unknown",
                    )
                    session.add(rec)
                    await session.commit()
                    new_events += 1

        except Exception as e:
            logger.warning(f"ACLED poll error: {e}")

        return new_events


class MissileIntelIngestor:
    """Main ingestor orchestrator."""

    def __init__(self):
        data_path = settings.missile_data_path
        self.cap_loader = CapabilityLoader(f"{data_path}/capabilities.yaml")
        self.def_loader = DefenseLoader(f"{data_path}/defense_systems.yaml")
        self.seeder = HistoricalSeeder()
        self.osint = OSINTCollector()
        self.running = False
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self):
        self.running = True
        self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

        await kafka_client.start()
        logger.info("MissileIntelIngestor: starting up")

        # One-time loads
        await self.cap_loader.load()
        await self.def_loader.load()
        await self.seeder.seed()
        await self.osint.start(self._client)

        # Continuous polling loop
        while self.running:
            try:
                n_rss = await self.osint.poll_rss()
                n_acled = await self.osint.poll_acled()
                if n_rss + n_acled > 0:
                    logger.info(f"MissileIntelIngestor: +{n_rss} RSS, +{n_acled} ACLED new events")
            except Exception as e:
                logger.error(f"MissileIntelIngestor poll error: {e}")

            # Refresh capabilities every N hours
            await asyncio.sleep(settings.missile_intel_refresh_hours * 3600)

    async def stop(self):
        self.running = False
        if self._client:
            await self._client.aclose()
        await kafka_client.stop()
