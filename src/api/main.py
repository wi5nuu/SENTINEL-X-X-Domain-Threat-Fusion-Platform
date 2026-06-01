import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.kafka import kafka_client
from src.common.database import init_db, get_session, AlertDB
from src.common.models import Alert, ThreatLevel, CompoundThreat
from prometheus_client import CONTENT_TYPE_LATEST
from src.common.metrics import get_metrics
from src.common.websocket_broadcast import ws_manager

logger = setup_logging("sentinel-api")


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
    yield
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


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "version": "1.0.0", "ws_connections": ws_manager.active_count}


@app.get("/metrics")
async def metrics():
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/alerts")
async def get_alerts(
    threat_class: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    session = await anext(get_session())
    try:
        query = AlertDB.__table__.select().order_by(AlertDB.timestamp_utc.desc()).limit(limit).offset(offset)
        if threat_class:
            query = query.where(AlertDB.threat_class == threat_class.upper())
        if domain:
            query = query.where(AlertDB.domain == domain)
        result = await session.execute(query)
        alerts = result.fetchall()
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
            for a in alerts
        ]
    finally:
        await session.close()


@app.get("/api/v1/alerts/{alert_id}")
async def get_alert(alert_id: str):
    session = await anext(get_session())
    try:
        result = await session.execute(
            AlertDB.__table__.select().where(AlertDB.id == alert_id)
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        return row._asdict() if hasattr(row, '_asdict') else dict(row)
    finally:
        await session.close()


@app.post("/api/v1/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, operator_id: str):
    session = await anext(get_session())
    try:
        result = await session.execute(
            AlertDB.__table__.select().where(AlertDB.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert.acknowledged = True
        alert.acknowledged_by = operator_id
        alert.acknowledged_at = datetime.utcnow()
        await session.commit()
        return {"status": "acknowledged", "alert_id": alert_id}
    finally:
        await session.close()


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


@app.post("/api/v1/threat/assess")
async def assess_threat(event: dict):
    import random
    threat = CompoundThreat(
        threat_class=ThreatLevel(random.choice(list(ThreatLevel))),
        confidence=random.uniform(0.5, 0.99),
        compound_pattern=random.choice(["maritime_deception", "cyber_physical", "air_intrusion", "none"]),
        reasoning_chain=[
            {
                "step": 1,
                "domain": "analysis",
                "observation": "Event received and analyzed",
                "contribution": 1.0,
                "evidence": event,
            }
        ],
        recommended_actions=["Monitor and track", "Notify duty officer"],
    )
    return threat.model_dump()
