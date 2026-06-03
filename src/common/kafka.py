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
                    compression_type="gzip",
                    request_timeout_ms=10000,
                )
                await self.producer.start()
                logger.info("Kafka producer started")
                return
            except (kafka_errors.KafkaConnectionError, OSError, Exception) as e:
                if attempt < retries:
                    logger.warning(f"Kafka connection attempt {attempt}/{retries} failed, retrying in {delay}s", extra={"error": str(e)})
                    await asyncio.sleep(delay)
                else:
                    logger.warning("Kafka unavailable — running in degraded mode (events will be logged but not published)", extra={"error": str(e)})
                    self.producer = None

    async def stop(self):
        if self.producer:
            try:
                await self.producer.stop()
            except Exception:
                pass

    async def send_event(self, topic: str, event: dict, key: Optional[str] = None):
        if not self.producer:
            return
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

    async def create_consumer_task(self, topic: str, group_id: str, handler: Callable[[str, dict], Awaitable[None]]) -> asyncio.Task:
        queue: asyncio.Queue = asyncio.Queue(maxsize=10000)

        async def _worker():
            while True:
                msg_topic, msg_value = await queue.get()
                try:
                    await handler(msg_topic, msg_value)
                except Exception as e:
                    metrics.errors_total.labels(service="kafka", error_type="consume").inc()
                    logger.error("Handler error", extra={"topic": msg_topic, "error": str(e)})

        async def _run():
            retry_delay = 5
            worker_task = asyncio.create_task(_worker())
            consumer = None
            while True:
                try:
                    consumer = AIOKafkaConsumer(
                        topic,
                        bootstrap_servers=settings.kafka_bootstrap_servers,
                        value_deserializer=lambda v: json.loads(v.decode()),
                        auto_offset_reset="latest",
                        max_poll_records=500,
                        request_timeout_ms=30000,
                    )
                    await asyncio.wait_for(consumer.start(), timeout=15)
                    logger.info("Kafka consumer started", extra={"topic": topic, "group": group_id})
                    async for msg in consumer:
                        await queue.put((topic, msg.value))
                except asyncio.CancelledError:
                    logger.info("Kafka consumer cancelled", extra={"topic": topic})
                    break
                except asyncio.TimeoutError:
                    logger.warning("Kafka consumer start timed out — retrying", extra={"topic": topic, "retry_delay": retry_delay})
                except Exception as e:
                    logger.warning("Kafka consumer error — retrying", extra={"topic": topic, "error": str(e)[:80], "retry_delay": retry_delay})
                finally:
                    if consumer:
                        try:
                            await consumer.stop()
                        except Exception:
                            pass
                        consumer = None
                await asyncio.sleep(retry_delay)
            worker_task.cancel()

        return asyncio.create_task(_run(), name=f"kafka-consumer-{topic}")


kafka_client = KafkaClient()
