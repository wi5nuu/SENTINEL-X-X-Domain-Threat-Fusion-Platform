import json
import asyncio
from typing import Optional, Callable, Awaitable
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer, errors as kafka_errors
from src.common.config import settings
from src.common.logging import setup_logging
from src.common.metrics import _metrics as metrics

logger = setup_logging("kafka")


class KafkaClient:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self, retries: int = 5, delay: float = 3.0):
        for attempt in range(1, retries + 1):
            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=settings.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, default=str).encode(),
                    acks="all",
                    retries=3,
                    max_in_flight_requests_per_connection=5,
                    compression_type="gzip",
                    request_timeout_ms=10000,
                )
                await self.producer.start()
                logger.info("Kafka producer started")
                return
            except (kafka_errors.KafkaConnectionError, OSError) as e:
                if attempt < retries:
                    logger.warning(f"Kafka connection attempt {attempt}/{retries} failed, retrying in {delay}s", extra={"error": str(e)})
                    await asyncio.sleep(delay)
                else:
                    logger.error("Kafka producer failed to start after all retries")
                    raise

    async def stop(self):
        if self.producer:
            try:
                await self.producer.stop()
            except Exception:
                pass

    async def send_event(self, topic: str, event: dict, key: Optional[str] = None):
        if not self.producer:
            raise RuntimeError("Kafka producer not started")
        try:
            await self.producer.send(
                topic,
                value=event,
                key=key.encode() if key else None,
            )
            metrics.events_produced.labels(domain=topic).inc()
        except Exception as e:
            metrics.errors_total.labels(service="kafka", error_type="produce").inc()
            logger.error("Failed to send event to Kafka", extra={"topic": topic, "error": str(e)})
            raise

    async def create_consumer_task(self, topic: str, group_id: str, handler: Callable[[dict], Awaitable[None]]) -> asyncio.Task:
        async def _run():
            consumer = AIOKafkaConsumer(
                topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda v: json.loads(v.decode()),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                max_poll_records=500,
                request_timeout_ms=15000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
            )
            try:
                await consumer.start()
                logger.info("Kafka consumer started", extra={"topic": topic, "group": group_id})
                async for msg in consumer:
                    try:
                        await handler(msg.value)
                    except Exception as e:
                        metrics.errors_total.labels(service="kafka", error_type="consume").inc()
                        logger.error("Handler error", extra={"topic": topic, "error": str(e)})
            except asyncio.CancelledError:
                logger.info("Kafka consumer cancelled", extra={"topic": topic})
            except Exception as e:
                logger.error("Kafka consumer error", extra={"topic": topic, "error": str(e)})
            finally:
                await consumer.stop()

        return asyncio.create_task(_run(), name=f"kafka-consumer-{topic}")


kafka_client = KafkaClient()
