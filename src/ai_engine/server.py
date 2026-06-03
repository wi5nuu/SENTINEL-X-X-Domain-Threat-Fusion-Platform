import asyncio
import json
import os
import time
from datetime import datetime
from typing import Optional, List

import numpy as np
import torch

from src.common.config import settings
from src.common.logging import setup_logging
from src.common.kafka import kafka_client
from src.common.metrics import _metrics as metrics
from src.common.websocket_broadcast import ws_manager
from src.response.correlation import DarkPatternCorrelationEngine
from src.response.threat_classifier import ThreatClassifier, EscalationEngine
from src.ai_engine.model import ThreatFusionModel

logger = setup_logging("ai-engine")

DOMAIN_FEATURE_DIMS = {
    "air": (14, ["lat", "lon", "baro_alt", "geo_alt", "velocity", "track_deg", "vert_rate", "squawk", "icao24", "on_ground", "classification", "threat_flag0", "threat_flag1", "anomaly_flag"]),
    "maritime": (12, ["lat", "lon", "sog", "cog", "heading", "nav_status", "vessel_type", "dark_suspect", "ais_gap", "anomaly0", "threat_flag0", "flag_state"]),
    "seismic": (5, ["lat", "lon", "depth_km", "magnitude", "tsunami_flag"]),
    "rf": (8, ["freq_mhz", "bandwidth", "signal_strength", "est_lat", "est_lon", "confidence", "anomaly_type", "protocol_flag"]),
    "cyber": (10, ["src_ip_enc", "src_port", "dst_port", "protocol", "technique", "target_sector", "severity", "confidence", "payload_flag0", "payload_flag1"]),
}

THREAT_LABELS = ["INFORMATIONAL", "SUSPICIOUS", "ELEVATED", "CRITICAL", "CATASTROPHIC"]


def event_to_tensor(event: dict, domain: str) -> Optional[np.ndarray]:
    if domain not in DOMAIN_FEATURE_DIMS:
        return None
    dim, feature_names = DOMAIN_FEATURE_DIMS[domain]
    vec = np.zeros(dim, dtype=np.float32)
    for i, name in enumerate(feature_names):
        val = event.get(name)
        if val is not None:
            try:
                vec[i] = float(val)
            except (ValueError, TypeError):
                vec[i] = 0.0
    return vec


class ThreatFusionEngine:
    def __init__(self):
        self.correlation = DarkPatternCorrelationEngine()
        self.classifier = ThreatClassifier()
        self.escalation = EscalationEngine()
        self.running = False
        self.batch_size = 64
        self.event_buffer: List[dict] = []
        self._consumer_tasks: List[asyncio.Task] = []
        self._model: Optional[ThreatFusionModel] = None

    def _load_model(self):
        model_path = os.environ.get("MODEL_PATH", "models/threat_fusion_v1.pt")
        if os.path.exists(model_path):
            try:
                self._model = ThreatFusionModel(embedding_dim=128, num_classes=5)
                self._model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
                self._model.eval()
                logger.info(f"Loaded trained model from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}. Using rule-based classification only.")
                self._model = None
        else:
            logger.info(f"No model found at {model_path}. Using rule-based classification only.")

    async def start(self):
        self.running = True
        await kafka_client.start()
        self._load_model()
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

    async def handle_event(self, topic: str, event: dict):
        domain_map = {
            "air-tracks": "air", "maritime-positions": "maritime",
            "seismic-events": "seismic", "rf-signals": "rf", "cyber-events": "cyber",
        }
        if "domain" not in event:
            event["domain"] = domain_map.get(topic, event.get("source", "unknown"))
        self.event_buffer.append(event)
        self.correlation.add_event(event)
        if len(self.event_buffer) >= self.batch_size:
            await self.process_batch()

    async def _send_alert(self, alert: dict):
        await kafka_client.send_event("alerts", alert, key=alert.get("alert_id", str(time.time())))
        await ws_manager.broadcast({
            "type": "new_alert",
            "payload": alert,
            "timestamp_utc": datetime.utcnow().isoformat(),
            "sequence_number": int(time.time() * 1000),
        })

    async def process_batches(self):
        last_heartbeat = 0
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
                await self._send_alert(alert)

            if time.time() - last_heartbeat >= 15:
                last_heartbeat = time.time()
                domain_counts = {}
                for e in self.event_buffer[-500:]:
                    d = e.get("domain", "unknown")
                    domain_counts[d] = domain_counts.get(d, 0) + 1
                await self._send_alert({
                    "alert_id": f"HB-{datetime.utcnow().timestamp()}",
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "threat_class": "INFORMATIONAL",
                    "confidence": 1.0,
                    "domain": "fusion",
                    "description": f"AI engine heartbeat — buffer: {len(self.event_buffer)}, domains: {domain_counts}",
                    "event_counts": domain_counts,
                })

    async def _run_model_inference(self, batch: List[dict]) -> dict:
        if self._model is None:
            return {}
        domain_tensors = {d: [] for d in DOMAIN_FEATURE_DIMS}
        for event in batch:
            domain = event.get("domain", event.get("source", "unknown"))
            vec = event_to_tensor(event, domain)
            if vec is not None:
                domain_tensors[domain].append(vec)
            else:
                for d in DOMAIN_FEATURE_DIMS:
                    domain_tensors[d].append(np.zeros(DOMAIN_FEATURE_DIMS[d][0], dtype=np.float32))

        try:
            model_inputs = {}
            for domain, tensors in domain_tensors.items():
                if tensors:
                    arr = np.stack(tensors, axis=0)
                    model_inputs[f"{domain}_x"] = torch.from_numpy(arr).unsqueeze(1).repeat(1, 64, 1).float()
            if not model_inputs:
                return {}
            with torch.no_grad():
                outputs = self._model(**model_inputs)
            return {
                "threat_classes": outputs["threat_class"].argmax(dim=1).tolist(),
                "compound_threats": (torch.sigmoid(outputs["compound_threat"]) > 0.5).int().tolist(),
                "eta_minutes": outputs["eta_minutes"].squeeze(-1).tolist(),
                "confidences": outputs["confidence"].squeeze(-1).tolist(),
            }
        except Exception as e:
            logger.warning(f"Model inference error: {e}")
            return {}

    async def process_batch(self):
        if not self.event_buffer:
            return
        batch = self.event_buffer[:self.batch_size]
        self.event_buffer = self.event_buffer[self.batch_size:]
        start = time.time()
        try:
            model_results = await self._run_model_inference(batch)
            model_confidences = model_results.get("confidences", [])
            model_threats = model_results.get("threat_classes", [])

            for idx, event in enumerate(batch):
                classification = self.escalation.process_event(event)
                rule_threat = classification["threat_class"]
                combined_threat = rule_threat

                if model_confidences and idx < len(model_confidences):
                    model_conf = model_confidences[idx]
                    if model_conf > 0.7 and idx < len(model_threats):
                        model_label = THREAT_LABELS[min(model_threats[idx], 4)]
                        severity_order = ["INFORMATIONAL", "SUSPICIOUS", "ELEVATED", "CRITICAL", "CATASTROPHIC"]
                        rule_idx = severity_order.index(rule_threat) if rule_threat in severity_order else 0
                        model_idx = severity_order.index(model_label) if model_label in severity_order else 0
                        if model_idx > rule_idx:
                            combined_threat = model_label
                            classification["threat_class"] = model_label
                            classification["model_confidence"] = model_conf

                if combined_threat in ("CRITICAL", "CATASTROPHIC", "ELEVATED"):
                    alert = {
                        "alert_id": f"AI-{datetime.utcnow().timestamp()}-{hash(json.dumps(event, default=str)) % 10000}",
                        "timestamp_utc": datetime.utcnow().isoformat(),
                        "threat_class": combined_threat,
                        "domain": event.get("domain", event.get("source", "unknown")),
                        "description": f"Event classified as {combined_threat}",
                        "auto_actions": classification["auto_actions"],
                        "model_confidence": classification.get("model_confidence", 0.0),
                    }
                    await self._send_alert(alert)
        except Exception as e:
            metrics.errors_total.labels(service="ai_engine", error_type="batch_process").inc()
            logger.error("Batch processing error", extra={"error": str(e)})
        finally:
            elapsed = time.time() - start
            metrics.ai_inference_latency.observe(elapsed)


if __name__ == "__main__":
    engine = ThreatFusionEngine()
    asyncio.run(engine.start())
