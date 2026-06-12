import asyncio
import json
import uuid
import os
from datetime import datetime, timedelta
from typing import Optional, List
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response, FileResponse
from sqlalchemy import select, func

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.kafka import kafka_client
from src.common.database import init_db, async_session, AlertDB, ResponseActionDB, MissileEventDB, MissileSpecDB, DefenseSystemDB
from src.common.models import Alert, ThreatLevel, CompoundThreat
from src.missile.trajectory import calculator as traj_calc, intercept_analyzer
from src.missile.range_calculator import compute_coverage_zones, countries_in_range, flight_time_estimate
from prometheus_client import CONTENT_TYPE_LATEST
from src.common.metrics import get_metrics
from src.common.websocket_broadcast import ws_manager
from src.ai_engine.analyst import analyst
from src.intelligence.manager import intelligence_manager
from src.intelligence.modules import CBRNWatch, DarkFleetTracker
from src.common.telemetry import setup_telemetry
from src.common.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestIDMiddleware,
    InputValidationMiddleware,
    AuditLogMiddleware,
    AuthenticationMiddleware,
)

intelligence_manager.register_module(CBRNWatch())
intelligence_manager.register_module(DarkFleetTracker())

logger = setup_logging("sentinel-api")

alert_buffer: deque = deque(maxlen=500)
track_buffer: deque = deque(maxlen=200)
event_counts: dict = {"air": 0, "maritime": 0, "seismic": 0, "rf": 0, "cyber": 0}
event_count_lock = asyncio.Lock()
_background_consumers: list = []


def _is_relevant_track(msg: dict) -> bool:
    return (msg.get("lat") is not None or msg.get("estimated_lat") is not None) and \
           (msg.get("lon") is not None or msg.get("estimated_lon") is not None)


async def _alert_handler(topic: str, msg: dict):
    msg["timestamp_utc"] = msg.get("timestamp_utc", datetime.utcnow().isoformat())
    alert_buffer.appendleft(msg)
    try:
        from src.common.models import Alert
        # Fix timestamp format for Pydantic if needed
        data = dict(msg)
        if isinstance(data.get("timestamp_utc"), str):
            data["timestamp_utc"] = datetime.fromisoformat(data["timestamp_utc"].replace("Z", "+00:00"))
        alert_obj = Alert(**data)
        analyst.add_alert(alert_obj)
    except Exception as e:
        logger.debug(f"Analyst alert feed error: {e}")
    await ws_manager.broadcast({"type": "new_alert", "payload": msg})


async def _track_handler(topic: str, msg: dict):
    domain_map = {"air-tracks": "air", "maritime-positions": "maritime", "seismic-events": "seismic", "rf-signals": "rf", "cyber-events": "cyber"}
    domain = domain_map.get(topic, "unknown")
    async with event_count_lock:
        event_counts[domain] = event_counts.get(domain, 0) + 1
    
    if domain in ("air", "maritime"):
        analyst.add_track(domain, msg)

    if _is_relevant_track(msg):
        lat = msg.get("lat") or msg.get("estimated_lat")
        lon = msg.get("lon") or msg.get("estimated_lon")
        color_map = {"air": "#00D4FF", "maritime": "#22C55E", "seismic": "#F59E0B", "rf": "#EF4444", "cyber": "#A855F7"}
        classification = msg.get("classification", "")
        velocity = msg.get("velocity_ms", msg.get("sog_knots", 0))
        is_threat = bool(msg.get("threat_flags")) or bool(msg.get("anomaly_flags")) or classification in ("military", "uav", "unidentified")
        track_color = color_map.get(domain, "#00D4FF")
        if classification == "uav":
            track_color = "#FF6B00"
        elif classification == "military":
            track_color = "#FF0000"
        elif classification == "unidentified":
            track_color = "#FFD700"
        elif is_threat:
            track_color = "#FF4444"
        is_missile = bool(msg.get("is_missile")) or (classification == "military" and (float(velocity) if velocity else 0) > 400)
        track_buffer.append({
            "lat": lat, "lon": lon,
            "label": msg.get("callsign") or msg.get("vessel_name") or msg.get("source", domain),
            "color": track_color,
            "domain": domain,
            "classification": classification,
            "velocity": float(velocity) if velocity else 0,
            "is_threat": is_threat,
            "squawk": msg.get("squawk"),
            "altitude": msg.get("baro_altitude_m") or msg.get("geo_altitude_m") or 0,
            "heading": msg.get("true_track_deg") or msg.get("cog_deg") or 0,
            "is_missile": is_missile,
            "threat_status": msg.get("threat_status"),
            "missile_type": msg.get("missile_type"),
            "missile_id": msg.get("missile_id"),
            "origin_lat": msg.get("origin_lat"),
            "origin_lon": msg.get("origin_lon"),
            "origin_name": msg.get("origin_name"),
            "target_lat": msg.get("target_lat"),
            "target_lon": msg.get("target_lon"),
            "target_name": msg.get("target_name"),
            "speed_mach": msg.get("speed_mach"),
            "accuracy_cep_m": msg.get("accuracy_cep_m"),
            "launch_time": msg.get("launch_time"),
            "eta_seconds": msg.get("eta_seconds"),
            "distance_km": msg.get("distance_km"),
            "flight_progress_pct": msg.get("flight_progress_pct"),
        })
        await ws_manager.broadcast({
            "type": "new_track",
            "payload": {
                "lat": lat,
                "lon": lon,
                "label": msg.get("callsign") or msg.get("vessel_name") or msg.get("source", domain),
                "color": track_color,
                "domain": domain,
                "classification": classification,
                "velocity": float(velocity) if velocity else 0,
                "is_threat": is_threat,
                "squawk": msg.get("squawk"),
                "altitude": msg.get("baro_altitude_m") or msg.get("geo_altitude_m") or 0,
                "heading": msg.get("true_track_deg") or msg.get("cog_deg") or 0,
                "is_missile": is_missile,
                "threat_status": msg.get("threat_status"),
                "missile_type": msg.get("missile_type"),
                "missile_id": msg.get("missile_id"),
                "origin_lat": msg.get("origin_lat"),
                "origin_lon": msg.get("origin_lon"),
                "origin_name": msg.get("origin_name"),
                "target_lat": msg.get("target_lat"),
                "target_lon": msg.get("target_lon"),
                "target_name": msg.get("target_name"),
                "speed_mach": msg.get("speed_mach"),
                "accuracy_cep_m": msg.get("accuracy_cep_m"),
                "launch_time": msg.get("launch_time"),
                "eta_seconds": msg.get("eta_seconds"),
                "distance_km": msg.get("distance_km"),
                "flight_progress_pct": msg.get("flight_progress_pct"),
            },
        })


async def _metric_reset_loop():
    while True:
        await asyncio.sleep(3600)
        async with event_count_lock:
            for k in event_counts:
                event_counts[k] = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SENTINEL API starting")
    try:
        await kafka_client.start()
    except Exception as e:
        logger.warning("Kafka deferred — will retry on demand", extra={"error": str(e)})
    try:
        await init_db()
    except Exception as e:
        logger.warning("Database init deferred", extra={"error": str(e)})
    # Background consumers for live data
    topics = [
        ("alerts", "api-alerts"),
        ("air-tracks", "api-air"),
        ("maritime-positions", "api-maritime"),
        ("seismic-events", "api-seismic"),
        ("rf-signals", "api-rf"),
        ("cyber-events", "api-cyber"),
        ("missile-events", "api-missile"),
    ]
    for topic, group in topics:
        handler = _alert_handler if topic == "alerts" else _track_handler
        task = await kafka_client.create_consumer_task(topic, group, handler)
        _background_consumers.append(task)
    task3 = asyncio.create_task(_metric_reset_loop())
    yield
    for t in _background_consumers:
        t.cancel()
    task3.cancel()
    await kafka_client.stop()
    logger.info("SENTINEL API shutdown")


app = FastAPI(
    title="SENTINEL API",
    description="Global Multi-Domain Threat Detection & Response Platform",
    version="2.0.0",
    lifespan=lifespan,
)

cors_origins = settings.cors_origins.split(",") if settings.cors_origins else ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, max_requests=settings.max_api_rate_limit, window_seconds=60)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(InputValidationMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(AuthenticationMiddleware)

setup_telemetry(app, "sentinel-api")


@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "version": "2.0.0", "ws_connections": ws_manager.active_count}


@app.get("/metrics")
async def metrics():
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/dashboard")
async def get_dashboard():
    async with event_count_lock:
        total_events = sum(event_counts.values())
        domain_counts = dict(event_counts)

    alerts_list = list(alert_buffer)[:20]
    alerts_24h = len([a for a in alert_buffer if a.get("threat_class", "INFORMATIONAL") != "INFORMATIONAL"])
    tracks_list = list(track_buffer)[-100:]

    severity_weights = {"INFORMATIONAL": 1, "SUSPICIOUS": 3, "ELEVATED": 6, "CRITICAL": 9, "CATASTROPHIC": 12}
    if alerts_list:
        threat_score = min(99, sum(severity_weights.get(a.get("threat_class", "INFORMATIONAL"), 1) for a in alerts_list) // max(1, len(alerts_list)))
    else:
        threat_score = 0

    air_count = sum(1 for t in track_buffer if t.get("domain") == "air")
    maritime_count = sum(1 for t in track_buffer if t.get("domain") == "maritime")

    # Sensor status derived from real event counts (active if events > 0 in last cycle)
    sensor_status = {
        "opensky": domain_counts.get("air", 0) > 0,
        "adsb": domain_counts.get("air", 0) > 0,
        "ais": domain_counts.get("maritime", 0) > 0,
        "usgs": domain_counts.get("seismic", 0) > 0,
        "noaa": domain_counts.get("rf", 0) > 0,
        "sdr": domain_counts.get("rf", 0) > 0,
        "honeypot": domain_counts.get("cyber", 0) > 0,
        "otx": domain_counts.get("cyber", 0) > 0,
        "nasa_donki": domain_counts.get("space", 0) > 0,
        "nasa_eonet": domain_counts.get("space", 0) > 0,
    }

    # Blockchain real sync status - check Ethereum node connectivity
    blockchain_synced = False
    try:
        from src.blockchain.service import BlockchainService
        bc = BlockchainService()
        await bc.connect()
        blockchain_synced = bc.w3 is not None and bc.w3.is_connected()
    except Exception:
        blockchain_synced = False

    return {
        "events_per_hour": total_events,
        "active_tracks": {"air": air_count, "maritime": maritime_count, "total": len(track_buffer)},
        "alerts_24h": alerts_24h,
        "recent_alerts": alerts_list,
        "threat_score": threat_score,
        "sensors": sensor_status,
        "blockchain_synced": blockchain_synced,
        "tracks": tracks_list,
        "domain_counts": domain_counts,
    }


@app.get("/api/v1/alerts")
async def get_alerts(
    threat_class: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    async with async_session() as session:
        stmt = select(AlertDB).order_by(AlertDB.timestamp_utc.desc()).limit(limit).offset(offset)
        if threat_class:
            stmt = stmt.where(AlertDB.threat_class == threat_class.upper())
        if domain:
            stmt = stmt.where(AlertDB.domain == domain)
        result = await session.execute(stmt)
        return [
            {
                "alert_id": a.id,
                "timestamp_utc": a.timestamp_utc.isoformat() if hasattr(a.timestamp_utc, 'isoformat') else str(a.timestamp_utc),
                "threat_class": a.threat_class,
                "confidence": a.confidence,
                "domain": a.domain,
                "description": a.description,
                "acknowledged": a.acknowledged,
            }
            for a in result.scalars()
        ]


@app.get("/api/v1/alerts/{alert_id}")
async def get_alert(alert_id: str):
    async with async_session() as session:
        result = await session.execute(select(AlertDB).where(AlertDB.id == alert_id))
        a = result.scalar_one_or_none()
        if not a:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {
            "alert_id": a.id,
            "timestamp_utc": a.timestamp_utc.isoformat() if hasattr(a.timestamp_utc, 'isoformat') else str(a.timestamp_utc),
            "threat_class": a.threat_class,
            "confidence": a.confidence,
            "domain": a.domain,
            "description": a.description,
            "acknowledged": a.acknowledged,
        }


@app.post("/api/v1/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, operator_id: str = "operator-1"):
    async with async_session() as session:
        result = await session.execute(select(AlertDB).where(AlertDB.id == alert_id))
        a = result.scalar_one_or_none()
        if not a:
            raise HTTPException(status_code=404, detail="Alert not found")
        a.acknowledged = True
        a.acknowledged_by = operator_id
        a.acknowledged_at = datetime.utcnow()
        await session.commit()
        return {"status": "acknowledged", "alert_id": alert_id}


@app.post("/api/v1/actions/acknowledge_all")
async def acknowledge_all():
    async with async_session() as session:
        result = await session.execute(select(AlertDB).where(not AlertDB.acknowledged))
        count = 0
        for a in result.scalars():
            a.acknowledged = True
            a.acknowledged_by = "operator-bulk"
            a.acknowledged_at = datetime.utcnow()
            count += 1
        await session.commit()
        await ws_manager.broadcast({"type": "alerts_acknowledged", "count": count})
        return {"status": "ok", "acknowledged_count": count}


@app.post("/api/v1/actions/emergency")
async def emergency_mode():
    alert = {
        "alert_id": f"EMRG-{datetime.utcnow().timestamp()}",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "threat_class": "CATASTROPHIC",
        "confidence": 1.0,
        "domain": "fusion",
        "description": "EMERGENCY MODE ACTIVATED by operator",
        "recommended_actions": ["full_emergency_protocol", "activate_all_playbooks", "siren_stub"],
    }
    await kafka_client.send_event("alerts", alert, key=alert["alert_id"])
    await ws_manager.broadcast({"type": "new_alert", "payload": alert})
    return {"status": "emergency_mode_active", "alert_id": alert["alert_id"]}


@app.post("/api/v1/actions/test_alert")
async def test_alert():
    alert = {
        "alert_id": f"TEST-{uuid.uuid4()}",
        "timestamp_utc": datetime.utcnow().isoformat(),
        "threat_class": "CRITICAL",
        "confidence": 0.95,
        "domain": "air",
        "description": "TEST ALERT: Synthetic alert injection working",
    }
    await ws_manager.broadcast({"type": "new_alert", "payload": alert})
    return {"status": "alert_broadcasted"}


@app.get("/api/v1/reports/download/{filename}")
async def download_report(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename or not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    safe_name = os.path.basename(filename)
    filepath = os.path.join("reports", safe_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(filepath, media_type="application/pdf", filename=safe_name)


@app.post("/api/v1/actions/playbook_test")
async def playbook_test():
    playbook_id = str(uuid.uuid4())
    logger.info("Playbook test triggered", extra={"playbook_id": playbook_id})
    await ws_manager.broadcast({"type": "playbook_test", "playbook_id": playbook_id, "status": "running"})
    return {
        "status": "playbook_executing",
        "playbook_id": playbook_id,
        "playbook": "incident_response_v1",
        "steps": [
            {"order": 1, "action": "isolate_affected_systems", "status": "completed"},
            {"order": 2, "action": "collect_forensic_data", "status": "in_progress"},
            {"order": 3, "action": "notify_duty_officer", "status": "pending"},
            {"order": 4, "action": "deploy_countermeasures", "status": "pending"},
        ],
    }


@app.post("/api/v1/actions/request")
async def request_action(request: dict):
    action_type = request.get("action_type")
    operator_id = request.get("operator_id", "operator-1")
    if not action_type:
        raise HTTPException(status_code=400, detail="action_type is required")
    
    async with async_session() as session:
        action = ResponseActionDB(
            action_type=action_type,
            requested_by=operator_id,
            approvals=[operator_id],
            metadata_json=request.get("metadata", {})
        )
        session.add(action)
        await session.commit()
        await ws_manager.broadcast({"type": "action_requested", "action_id": action.id, "action_type": action_type})
        return {"status": "pending_approval", "action_id": action.id}


@app.post("/api/v1/actions/approve/{action_id}")
async def approve_action(action_id: str, operator_id: str = "operator-2"):
    async with async_session() as session:
        result = await session.execute(select(ResponseActionDB).where(ResponseActionDB.id == action_id))
        action = result.scalar_one_or_none()
        if not action:
            raise HTTPException(status_code=404, detail="Action not found")
        
        if operator_id in action.approvals:
            return {"status": "already_approved", "current_approvals": len(action.approvals)}
        
        action.approvals = list(action.approvals) + [operator_id]
        if len(action.approvals) >= action.required_approvals:
            action.status = "APPROVED"
            # Trigger the actual action here
            await ws_manager.broadcast({"type": "action_approved", "action_id": action.id, "action_type": action.action_type})
        
        await session.commit()
        return {"status": action.status, "approvals": len(action.approvals)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "connections": ws_manager.active_count,
                })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error", extra={"error": str(e)})
    finally:
        await ws_manager.disconnect(websocket)


@app.post("/api/v1/ingest/{domain}")
async def ingest_event(domain: str, event: dict):
    topic_map = {
        "air": "air-tracks",
        "maritime": "maritime-positions",
        "seismic": "seismic-events",
        "rf": "rf-signals",
        "cyber": "cyber-events",
    }
    topic = topic_map.get(domain)
    if not topic:
        raise HTTPException(status_code=400, detail=f"Unknown domain: {domain}")
    event["timestamp_utc"] = event.get("timestamp_utc", datetime.utcnow().isoformat())
    await kafka_client.send_event(topic, event, key=str(uuid.uuid4()))
    return {"status": "queued", "domain": domain, "topic": topic}


@app.post("/api/v1/analyst/chat")
async def analyst_chat(query: dict):
    user_query = query.get("query", "")
    if not user_query:
        raise HTTPException(status_code=400, detail="Query is required")
    response = await analyst.query(user_query)
    return {"status": "ok", "response": response}


@app.get("/api/v1/analyst/situational-awareness")
async def situational_awareness():
    summary = await analyst.get_situational_awareness()
    return {"status": "ok", "summary": summary}


@app.post("/api/v1/threat/assess")
async def assess_threat(event: dict):
    """Assess threat level based on actual event data fields."""
    domain = event.get("domain", "unknown")
    threat_flags = event.get("threat_flags", [])
    anomaly_flags = event.get("anomaly_flags", [])
    classification = event.get("classification", "")
    squawk = event.get("squawk", "")
    severity = event.get("severity", event.get("threat_class", "INFORMATIONAL"))

    # Derive threat class from real event attributes
    if squawk in ("7500",) or "hijack" in str(threat_flags):
        threat_class = ThreatLevel.catastrophic
        confidence = 0.95
    elif squawk in ("7700",) or severity == "CRITICAL" or "critical" in str(threat_flags).lower():
        threat_class = ThreatLevel.critical
        confidence = 0.88
    elif squawk in ("7600",) or severity == "ELEVATED" or classification == "military":
        threat_class = ThreatLevel.elevated
        confidence = 0.75
    elif threat_flags or anomaly_flags or severity == "SUSPICIOUS":
        threat_class = ThreatLevel.suspicious
        confidence = 0.60
    else:
        threat_class = ThreatLevel.informational
        confidence = 0.40

    # Build reasoning from actual flags
    reasoning = []
    if squawk:
        reasoning.append({"step": 1, "domain": domain, "observation": f"Squawk code {squawk} detected", "contribution": 0.4})
    if threat_flags:
        reasoning.append({"step": len(reasoning)+1, "domain": domain, "observation": f"Threat flags: {threat_flags}", "contribution": 0.35})
    if anomaly_flags:
        reasoning.append({"step": len(reasoning)+1, "domain": domain, "observation": f"Anomaly flags: {anomaly_flags}", "contribution": 0.25})
    if not reasoning:
        reasoning.append({"step": 1, "domain": domain, "observation": "Event assessed - no threat indicators", "contribution": 0.0})

    compound = CompoundThreat(
        threat_class=threat_class,
        confidence=confidence,
        compound_pattern=f"{domain}_event" if domain != "unknown" else "none",
        reasoning_chain=reasoning,
        recommended_actions=_get_recommended_actions(threat_class),
    )
    return compound.model_dump()


def _get_recommended_actions(threat_class: ThreatLevel) -> list:
    actions = {
        ThreatLevel.catastrophic: ["Activate full emergency protocol", "Notify command authority", "Deploy countermeasures"],
        ThreatLevel.critical: ["Alert duty officer", "Activate playbook", "Increase monitoring"],
        ThreatLevel.elevated: ["Monitor closely", "Prepare response team", "Log incident"],
        ThreatLevel.suspicious: ["Flag for review", "Increase sensor focus", "Log event"],
        ThreatLevel.informational: ["Log and monitor"],
    }
    return actions.get(threat_class, ["Log and monitor"])


# ─────────────────────────────────────────────────────────
# MISSILE INTELLIGENCE API
# ─────────────────────────────────────────────────────────


def _missile_event_to_dict(e: MissileEventDB) -> dict:
    return {
        "event_id": e.id,
        "launch_time": e.launch_time.isoformat() if e.launch_time else None,
        "impact_time": e.impact_time.isoformat() if e.impact_time else None,
        "origin_country": e.origin_country,
        "origin_actor": e.origin_actor,
        "launch_lat": e.launch_lat,
        "launch_lon": e.launch_lon,
        "launch_location_name": e.launch_location_name,
        "target_country": e.target_country,
        "target_lat": e.target_lat,
        "target_lon": e.target_lon,
        "target_name": e.target_name,
        "missile_type": e.missile_type,
        "missile_count": e.missile_count,
        "status": e.status,
        "intercepted_count": e.intercepted_count,
        "interception_system": e.interception_system,
        "damage_assessment": e.damage_assessment,
        "casualties_reported": e.casualties_reported,
        "estimated_range_km": e.estimated_range_km,
        "flight_duration_s": e.flight_duration_s,
        "headline": e.headline,
        "source_url": e.source_url,
        "source_name": e.source_name,
        "validation_status": e.validation_status,
        "corroborating_sources": e.corroborating_sources or [],
        "conflict_context": e.conflict_context,
        "notes": e.notes,
    }


@app.get("/api/v1/missile/events")
async def get_missile_events(
    origin_country: Optional[str] = None,
    target_country: Optional[str] = None,
    status: Optional[str] = None,
    missile_type: Optional[str] = None,
    validation_status: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List missile events with optional filters. Source-attributed OSINT data only."""
    async with async_session() as session:
        stmt = select(MissileEventDB).order_by(MissileEventDB.launch_time.desc()).limit(limit).offset(offset)
        if origin_country:
            stmt = stmt.where(MissileEventDB.origin_country == origin_country.upper())
        if target_country:
            stmt = stmt.where(MissileEventDB.target_country == target_country.upper())
        if status:
            stmt = stmt.where(MissileEventDB.status == status)
        if missile_type:
            stmt = stmt.where(MissileEventDB.missile_type.ilike(f"%{missile_type}%"))
        if validation_status:
            stmt = stmt.where(MissileEventDB.validation_status == validation_status)
        result = await session.execute(stmt)
        return [_missile_event_to_dict(e) for e in result.scalars()]


@app.get("/api/v1/missile/events/{event_id}")
async def get_missile_event(event_id: str):
    """Get a single missile event with full details and trajectory."""
    async with async_session() as session:
        result = await session.execute(select(MissileEventDB).where(MissileEventDB.id == event_id))
        e = result.scalar_one_or_none()
        if not e:
            raise HTTPException(status_code=404, detail="Event not found")
        data = _missile_event_to_dict(e)
        data["trajectory_cached"] = e.trajectory_cache or []
        return data


@app.get("/api/v1/missile/events/{event_id}/trajectory")
async def get_missile_trajectory(event_id: str):
    """
    Get or compute trajectory for a missile event.
    Uses cached trajectory if available; otherwise computes from spec.
    """
    async with async_session() as session:
        result = await session.execute(select(MissileEventDB).where(MissileEventDB.id == event_id))
        e = result.scalar_one_or_none()
        if not e:
            raise HTTPException(status_code=404, detail="Event not found")

        if e.trajectory_cache:
            return {"event_id": event_id, "mode": "historical", "points": e.trajectory_cache}

        if not (e.launch_lat and e.launch_lon and e.target_lat and e.target_lon):
            raise HTTPException(status_code=422, detail="Insufficient coordinates for trajectory computation")

        # Get spec
        spec_dict = {}
        if e.missile_type:
            spec_result = await session.execute(
                select(MissileSpecDB).where(MissileSpecDB.name.ilike(f"%{e.missile_type}%"))
            )
            spec = spec_result.scalar_one_or_none()
            if spec:
                spec_dict = {
                    "speed_mach": spec.speed_mach,
                    "boost_phase_s": spec.boost_phase_s,
                    "midcourse_phase_s": spec.midcourse_phase_s,
                    "terminal_phase_s": spec.terminal_phase_s,
                    "apogee_km": spec.apogee_km,
                    "payload_kg": spec.payload_kg,
                }

        points = traj_calc.compute(
            e.launch_lat, e.launch_lon, e.target_lat, e.target_lon, spec_dict
        )
        pts_dicts = [
            {"time_s": p.time_s, "lat": p.lat, "lon": p.lon,
             "altitude_km": p.altitude_km, "speed_ms": p.speed_ms,
             "phase": p.phase, "downrange_km": p.downrange_km}
            for p in points
        ]

        # Cache computed trajectory
        e.trajectory_cache = pts_dicts
        await session.commit()

        return {"event_id": event_id, "mode": "historical", "points": pts_dicts}


@app.get("/api/v1/missile/capabilities")
async def get_missile_capabilities(
    operator_country: Optional[str] = None,
    missile_type: Optional[str] = None,
    operational_status: Optional[str] = None,
    min_range_km: Optional[float] = None,
    limit: int = Query(default=200, le=500),
):
    """Full missile capability database with optional filters."""
    async with async_session() as session:
        stmt = select(MissileSpecDB).order_by(MissileSpecDB.operator_country, MissileSpecDB.max_range_km.desc()).limit(limit)
        if operator_country:
            stmt = stmt.where(MissileSpecDB.operator_country == operator_country.upper())
        if missile_type:
            stmt = stmt.where(MissileSpecDB.missile_type.ilike(f"%{missile_type}%"))
        if operational_status:
            stmt = stmt.where(MissileSpecDB.operational_status == operational_status)
        if min_range_km:
            stmt = stmt.where(MissileSpecDB.max_range_km >= min_range_km)
        result = await session.execute(stmt)
        return [
            {
                "id": s.id, "name": s.name, "nato_designation": s.nato_designation,
                "operator_country": s.operator_country, "missile_type": s.missile_type,
                "max_range_km": s.max_range_km, "min_range_km": s.min_range_km,
                "speed_mach": s.speed_mach, "apogee_km": s.apogee_km,
                "cep_m": s.cep_m, "payload_kg": s.payload_kg,
                "warhead_types": s.warhead_types, "launch_method": s.launch_method,
                "guidance_type": s.guidance_type,
                "boost_phase_s": s.boost_phase_s, "midcourse_phase_s": s.midcourse_phase_s,
                "terminal_phase_s": s.terminal_phase_s,
                "operational_status": s.operational_status,
                "first_test_date": s.first_test_date, "ioc_date": s.ioc_date,
                "sources": s.sources,
            }
            for s in result.scalars()
        ]


@app.get("/api/v1/missile/capabilities/{name}")
async def get_missile_spec(name: str):
    """Get single missile capability record by name."""
    async with async_session() as session:
        result = await session.execute(
            select(MissileSpecDB).where(MissileSpecDB.name.ilike(f"%{name}%"))
        )
        s = result.scalar_one_or_none()
        if not s:
            raise HTTPException(status_code=404, detail=f"Missile spec not found: {name}")
        return {
            "id": s.id, "name": s.name, "nato_designation": s.nato_designation,
            "operator_country": s.operator_country, "missile_type": s.missile_type,
            "max_range_km": s.max_range_km, "min_range_km": s.min_range_km,
            "speed_mach": s.speed_mach, "apogee_km": s.apogee_km,
            "cep_m": s.cep_m, "payload_kg": s.payload_kg,
            "warhead_types": s.warhead_types, "launch_method": s.launch_method,
            "guidance_type": s.guidance_type,
            "boost_phase_s": s.boost_phase_s, "midcourse_phase_s": s.midcourse_phase_s,
            "terminal_phase_s": s.terminal_phase_s,
            "operational_status": s.operational_status,
            "first_test_date": s.first_test_date, "ioc_date": s.ioc_date,
            "sources": s.sources,
        }


@app.get("/api/v1/missile/defense-systems")
async def get_defense_systems(
    operator_country: Optional[str] = None,
    system_type: Optional[str] = None,
    operational_status: Optional[str] = None,
):
    """Registry of missile defense systems with coverage data."""
    async with async_session() as session:
        stmt = select(DefenseSystemDB).order_by(DefenseSystemDB.operator_country)
        if operator_country:
            stmt = stmt.where(DefenseSystemDB.operator_country == operator_country.upper())
        if system_type:
            stmt = stmt.where(DefenseSystemDB.system_type == system_type)
        if operational_status:
            stmt = stmt.where(DefenseSystemDB.operational_status.ilike(f"%{operational_status}%"))
        result = await session.execute(stmt)
        return [
            {
                "id": d.id, "name": d.name, "system_type": d.system_type,
                "platform_name": d.platform_name, "operator_country": d.operator_country,
                "lat": d.lat, "lon": d.lon, "location_name": d.location_name,
                "radar_range_km": d.radar_range_km,
                "intercept_range_km": d.intercept_range_km,
                "intercept_altitude_max_km": d.intercept_altitude_max_km,
                "interceptor_type": d.interceptor_type,
                "engagement_envelope": d.engagement_envelope,
                "operational_status": d.operational_status,
                "sources": d.sources,
            }
            for d in result.scalars()
        ]


@app.get("/api/v1/missile/live-tracks")
async def get_missile_live_tracks():
    """Return currently active missile events (in_flight or launched status)."""
    async with async_session() as session:
        result = await session.execute(
            select(MissileEventDB)
            .where(MissileEventDB.status.in_(["launched", "in_flight"]))
            .order_by(MissileEventDB.launch_time.desc())
            .limit(50)
        )
        return [_missile_event_to_dict(e) for e in result.scalars()]


@app.get("/api/v1/missile/military-bases")
async def get_military_bases(country: Optional[str] = None, type: Optional[str] = None):
    """
    Return military installation data from the protected backend YAML dataset.
    This data NEVER lives in the frontend — served exclusively from the backend.

    Query params:
      country  : Filter by ISO country code (e.g. IDN, USA, RUS)
      type     : Filter by installation type (nuclear|naval|airforce|army|icbm|missile)
    """
    import yaml as _yaml

    bases_file = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "missile_intel", "military_bases.yaml"
    )
    bases_file = os.path.normpath(bases_file)

    if not os.path.exists(bases_file):
        raise HTTPException(status_code=503, detail="Military bases dataset not found. Ensure data/missile_intel/military_bases.yaml exists.")

    try:
        with open(bases_file, "r", encoding="utf-8") as f:
            raw = _yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load military_bases.yaml: {e}")
        raise HTTPException(status_code=500, detail="Failed to load military bases dataset.")

    bases = raw.get("bases", [])

    # Apply filters
    if country:
        bases = [b for b in bases if b.get("country", "").upper() == country.upper()]
    if type:
        bases = [b for b in bases if b.get("type", "").lower() == type.lower()]

    return {
        "total": len(bases),
        "filters": {"country": country, "type": type},
        "bases": bases,
    }


@app.get("/api/v1/ui-presets")
async def get_ui_presets():
    """
    Return UI presets (global_bases, country_presets, etc.) from the protected backend YAML.
    This prevents sensitive coordinates and configuration from being hardcoded in the frontend.
    """
    import yaml as _yaml
    
    presets_file = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "missile_intel", "ui_presets.yaml"
    )
    presets_file = os.path.normpath(presets_file)

    if not os.path.exists(presets_file):
        raise HTTPException(status_code=503, detail="UI presets dataset not found.")

    try:
        with open(presets_file, "r", encoding="utf-8") as f:
            raw = _yaml.safe_load(f)
            return raw
    except Exception as e:
        logger.error(f"Failed to load ui_presets.yaml: {e}")
        raise HTTPException(status_code=500, detail="Failed to load UI presets.")



@app.post("/api/v1/missile/simulate")
async def simulate_trajectory(request: dict):
    """
    What-If trajectory simulation.
    Computes a physics-based trajectory for any missile + launch/target coords.
    Results are CLEARLY LABELLED as simulation — not real events.
    """
    if not settings.enable_what_if_simulation:
        raise HTTPException(status_code=403, detail="What-if simulation is disabled")

    missile_name = request.get("missile")
    launch_lat = request.get("launch_lat")
    launch_lon = request.get("launch_lon")
    target_lat = request.get("target_lat")
    target_lon = request.get("target_lon")

    if not all([missile_name, launch_lat is not None, launch_lon is not None,
                target_lat is not None, target_lon is not None]):
        raise HTTPException(status_code=400, detail="Required: missile, launch_lat, launch_lon, target_lat, target_lon")

    async with async_session() as session:
        spec_result = await session.execute(
            select(MissileSpecDB).where(MissileSpecDB.name.ilike(f"%{missile_name}%"))
        )
        spec = spec_result.scalar_one_or_none()
        if not spec:
            raise HTTPException(status_code=404, detail=f"Missile not found: {missile_name}")

        spec_dict = {
            "speed_mach": spec.speed_mach, "boost_phase_s": spec.boost_phase_s,
            "midcourse_phase_s": spec.midcourse_phase_s,
            "terminal_phase_s": spec.terminal_phase_s,
            "apogee_km": spec.apogee_km, "payload_kg": spec.payload_kg,
            "max_range_km": spec.max_range_km,
        }

        points = traj_calc.compute(
            float(launch_lat), float(launch_lon),
            float(target_lat), float(target_lon),
            spec_dict
        )

        # Interception analysis
        ds_result = await session.execute(select(DefenseSystemDB))
        defense_systems = [
            {"name": d.name, "lat": d.lat, "lon": d.lon,
             "intercept_range_km": d.intercept_range_km,
             "intercept_altitude_max_km": d.intercept_altitude_max_km,
             "operational_status": d.operational_status}
            for d in ds_result.scalars()
        ]

    intercept_info = intercept_analyzer.analyze(
        [p for p in points],  # pass as list of TrajPoint
        defense_systems
    )

    pts_dicts = [
        {"time_s": p.time_s, "lat": p.lat, "lon": p.lon,
         "altitude_km": p.altitude_km, "speed_ms": p.speed_ms,
         "phase": p.phase, "downrange_km": p.downrange_km}
        for p in points
    ]

    total_flight_s = pts_dicts[-1]["time_s"] if pts_dicts else 0

    return {
        "WARNING": "THIS IS A SIMULATION — NOT A REAL EVENT",
        "mode": "what_if",
        "missile": spec.name,
        "operator_country": spec.operator_country,
        "launch_lat": launch_lat, "launch_lon": launch_lon,
        "target_lat": target_lat, "target_lon": target_lon,
        "total_range_km": round(pts_dicts[-1]["downrange_km"] if pts_dicts else 0, 1),
        "total_flight_s": round(total_flight_s, 0),
        "total_flight_min": round(total_flight_s / 60.0, 1),
        "points": pts_dicts,
        "interception_analysis": {
            "threatened_defense_systems": intercept_info["threatened_defense_systems"],
            "estimated_intercept_probability": intercept_info["estimated_intercept_probability"],
        },
    }


@app.post("/api/v1/missile/range-coverage")
async def missile_range_coverage(request: dict):
    """
    Compute reachable area (range rings) for a missile from a launch point.
    Returns GeoJSON-compatible polygon rings and list of countries in range.
    """
    missile_name = request.get("missile")
    launch_lat = request.get("launch_lat")
    launch_lon = request.get("launch_lon")

    if not all([missile_name, launch_lat is not None, launch_lon is not None]):
        raise HTTPException(status_code=400, detail="Required: missile, launch_lat, launch_lon")

    async with async_session() as session:
        spec_result = await session.execute(
            select(MissileSpecDB).where(MissileSpecDB.name.ilike(f"%{missile_name}%"))
        )
        spec = spec_result.scalar_one_or_none()
        if not spec:
            raise HTTPException(status_code=404, detail=f"Missile not found: {missile_name}")

    zones = compute_coverage_zones(
        float(launch_lat), float(launch_lon),
        spec.max_range_km, spec.min_range_km,
    )
    reachable = countries_in_range(float(launch_lat), float(launch_lon), spec.max_range_km)

    flight_t = flight_time_estimate(
        spec.max_range_km, spec.speed_mach,
        spec.boost_phase_s or 0,
        spec.midcourse_phase_s or 0,
        spec.terminal_phase_s or 0,
    )

    return {
        "WARNING": "THIS IS A SIMULATION — NOT A REAL EVENT",
        "missile": spec.name,
        "operator_country": spec.operator_country,
        "launch_lat": launch_lat, "launch_lon": launch_lon,
        "max_range_km": spec.max_range_km,
        "min_range_km": spec.min_range_km,
        "estimated_max_flight_s": round(flight_t, 0),
        "zones": [
            {"range_km": z["range_km"], "color": z["color"],
             "ring": z["ring"], "is_max_range": z["is_max_range"]}
            for z in zones
        ],
        "countries_in_range": reachable,
    }


@app.get("/api/v1/missile/stats")
async def missile_stats():
    """Aggregate statistics for the missile intelligence database."""
    async with async_session() as session:
        total_events = (await session.execute(select(func.count()).select_from(MissileEventDB))).scalar_one()
        verified = (await session.execute(
            select(func.count()).select_from(MissileEventDB).where(MissileEventDB.validation_status == "verified")
        )).scalar_one()
        total_specs = (await session.execute(select(func.count()).select_from(MissileSpecDB))).scalar_one()
        total_defense = (await session.execute(select(func.count()).select_from(DefenseSystemDB))).scalar_one()

        # Events by status
        status_counts = {}
        for status in ["impacted", "intercepted", "test", "unknown", "launched", "in_flight"]:
            cnt = (await session.execute(
                select(func.count()).select_from(MissileEventDB).where(MissileEventDB.status == status)
            )).scalar_one()
            if cnt > 0:
                status_counts[status] = cnt

    return {
        "total_events": total_events,
        "verified_events": verified,
        "total_missile_specs": total_specs,
        "total_defense_systems": total_defense,
        "events_by_status": status_counts,
    }
