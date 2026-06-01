import asyncio
import json
import time
from datetime import datetime
from typing import Optional, List

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.kafka import kafka_client
from src.common.metrics import _metrics as metrics
from src.common.websocket_broadcast import ws_manager
from src.response.correlation import DarkPatternCorrelationEngine
from src.response.threat_classifier import ThreatClassifier, EscalationEngine

logger = setup_logging("ai-engine")


class ThreatFusionEngine:
    def __init__(self):
        self.correlation = DarkPatternCorrelationEngine()
        self.classifier = ThreatClassifier()
        self.escalation = EscalationEngine()
        self.running = False
        self.batch_size = 64
        self.event_buffer: List[dict] = []
        self._consumer_tasks: List[asyncio.Task] = []

    async def start(self):
        self.running = True
        await kafka_client.start()
        logger.info("AI Threat Fusion Engine started")

        topics = [
            ("air-tracks", "ai-engine-air"),
            ("maritime-positions", "ai-engine-maritime"),
            ("seismic-events", "ai-engine-seismic"),
            ("rf-signals", "ai-engine-rf"),
            ("cyber-events", "ai-engine-cyber"),
        ]

        for topic, group in topics:
            task = await kafka_client.create_consumer_task(topic, group, self.handle_event)
            self._consumer_tasks.append(task)

        await asyncio.gather(self.process_batches(), *self._consumer_tasks)

    async def stop(self):
        self.running = False
        for task in self._consumer_tasks:
            task.cancel()
        await kafka_client.stop()

    async def handle_event(self, event: dict):
        self.event_buffer.append(event)
        self.correlation.add_event(event)
        if len(self.event_buffer) >= self.batch_size:
            await self.process_batch()

    async def process_batches(self):
        while self.running:
            await asyncio.sleep(1)
            if len(self.event_buffer) >= self.batch_size:
                await self.process_batch()

            compound_threats = self.correlation.analyze()
            for threat in compound_threats:
                tc = threat.threat_class
                alert = {
                    "alert_id": f"AI-{datetime.utcnow().timestamp()}",
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "threat_class": tc.value if hasattr(tc, 'value') else tc,
                    "confidence": threat.confidence,
                    "domain": "fusion",
                    "description": f"Compound threat detected: {threat.compound_pattern}",
                    "compound_pattern": threat.compound_pattern,
                    "reasoning_chain": threat.reasoning_chain,
                    "recommended_actions": threat.recommended_actions,
                }
                await kafka_client.send_event("alerts", alert, key=alert["alert_id"])
                await ws_manager.broadcast({
                    "type": "new_alert",
                    "payload": alert,
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "sequence_number": int(time.time() * 1000),
                })

    async def process_batch(self):
        if not self.event_buffer:
            return
        batch = self.event_buffer[:self.batch_size]
        self.event_buffer = self.event_buffer[self.batch_size:]
        start = time.time()
        try:
            for event in batch:
                classification = self.escalation.process_event(event)
                if classification["threat_class"] in ("CRITICAL", "CATASTROPHIC"):
                    alert = {
                        "alert_id": f"AI-{datetime.utcnow().timestamp()}-{hash(json.dumps(event, default=str)) % 10000}",
                        "timestamp_utc": datetime.utcnow().isoformat(),
                        "threat_class": classification["threat_class"],
                        "domain": event.get("domain", event.get("source", "unknown")),
                        "description": f"Event classified as {classification['threat_class']}",
                        "auto_actions": classification["auto_actions"],
                    }
                    await kafka_client.send_event("alerts", alert, key=alert["alert_id"])
                    await ws_manager.broadcast({
                        "type": "new_alert",
                        "payload": alert,
                        "timestamp_utc": datetime.utcnow().isoformat(),
                        "sequence_number": int(time.time() * 1000),
                    })
        except Exception as e:
            metrics.errors_total.labels(service="ai_engine", error_type="batch_process").inc()
            logger.error("Batch processing error", extra={"error": str(e)})
        finally:
            elapsed = time.time() - start
            metrics.ai_inference_latency.observe(elapsed)


if __name__ == "__main__":
    engine = ThreatFusionEngine()
    asyncio.run(engine.start())
