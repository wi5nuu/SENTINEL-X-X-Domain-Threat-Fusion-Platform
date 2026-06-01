from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from functools import wraps
import time


class SentinelMetrics:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self):
        self.events_ingested = Counter("sentinel_events_ingested_total", "Total events ingested", ["domain", "source"], registry=REGISTRY)
        self.events_produced = Counter("sentinel_events_produced_total", "Total events produced to Kafka", ["domain"], registry=REGISTRY)
        self.alerts_generated = Counter("sentinel_alerts_generated_total", "Total alerts generated", ["severity"], registry=REGISTRY)
        self.errors_total = Counter("sentinel_errors_total", "Total errors", ["service", "error_type"], registry=REGISTRY)
        self.ingestion_latency = Histogram("sentinel_ingestion_latency_seconds", "Ingestion latency", ["domain"], buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0), registry=REGISTRY)
        self.ai_inference_latency = Histogram("sentinel_ai_inference_latency_seconds", "AI inference latency", buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0), registry=REGISTRY)
        self.kafka_consumer_lag = Gauge("sentinel_kafka_consumer_lag", "Kafka consumer lag per partition", ["topic", "partition"], registry=REGISTRY)
        self.sensor_status = Gauge("sentinel_sensor_status", "Sensor online status", ["sensor_id"], registry=REGISTRY)


_metrics = SentinelMetrics()


def track_latency(domain: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                _metrics.ingestion_latency.labels(domain=domain).observe(time.time() - start)
        return wrapper
    return decorator


def get_metrics():
    return generate_latest()
