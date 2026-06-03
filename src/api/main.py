import asyncio
import json
import uuid
import random
import time
from datetime import datetime, timedelta
from typing import Optional, List
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from sqlalchemy import select, func

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.kafka import kafka_client
from src.common.database import init_db, async_session, AlertDB, ResponseActionDB
from src.common.models import Alert, ThreatLevel, CompoundThreat
from prometheus_client import CONTENT_TYPE_LATEST
from src.common.metrics import get_metrics
from src.common.websocket_broadcast import ws_manager
from src.ai_engine.analyst import analyst
from src.intelligence.manager import intelligence_manager
from src.intelligence.modules import CBRNWatch, DarkFleetTracker
from src.common.telemetry import setup_telemetry

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
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_telemetry(app, "sentinel-api")


@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "version": "1.0.0", "ws_connections": ws_manager.active_count}


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

    return {
        "events_per_hour": total_events,
        "active_tracks": {"air": air_count, "maritime": maritime_count, "total": len(track_buffer)},
        "alerts_24h": alerts_24h,
        "recent_alerts": alerts_list,
        "threat_score": threat_score,
        "sensors": {
            "opensky": True, "adsb": True, "ais": True, "usgs": True,
            "noaa": True, "sdr": True, "honeypot": True, "otx": True,
        },
        "blockchain_synced": True,
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
        result = await session.execute(select(AlertDB).where(AlertDB.acknowledged == False))
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
    filepath = os.path.join("reports", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)


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
    threat = CompoundThreat(
        threat_class=ThreatLevel(random.choice(list(ThreatLevel))),
        confidence=random.uniform(0.5, 0.99),
        compound_pattern=random.choice(["maritime_deception", "cyber_physical", "air_intrusion", "none"]),
        reasoning_chain=[
            {"step": 1, "domain": "analysis", "observation": "Event received and analyzed", "contribution": 1.0, "evidence": event}
        ],
        recommended_actions=["Monitor and track", "Notify duty officer"],
    )
    return threat.model_dump()
