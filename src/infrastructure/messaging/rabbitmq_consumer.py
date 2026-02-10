"""
RabbitMQ consumer — background worker that processes inbound messages.

Declares the queues that feed into the orchestrator so they exist before
any service tries to publish to them.
"""
import asyncio
import json
import threading
from collections.abc import Callable

import pika
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)

EXCHANGE_NAME = "orchestrator.events"

# Queues consumed by this orchestrator
QUEUE_BINDINGS: list[tuple[str, str]] = [
    ("scraper.jobs", "scraper.job.created"),
]


class RabbitMQConsumer:
    """Long-running consumer that dispatches messages to registered handlers."""

    def __init__(self, rabbitmq_url: str = settings.rabbitmq_url) -> None:
        self._url = rabbitmq_url
        self._handlers: dict[str, Callable[[dict], None]] = {}  # type: ignore[type-arg]
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def register_handler(
        self, routing_key: str, handler: Callable[[dict], None]  # type: ignore[type-arg]
    ) -> None:
        self._handlers[routing_key] = handler

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("rabbitmq_consumer_started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("rabbitmq_consumer_stopped")

    def _run(self) -> None:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(self._url))
            channel = connection.channel()
            channel.exchange_declare(
                exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
            )
            for queue_name, routing_key in QUEUE_BINDINGS:
                channel.queue_declare(queue=queue_name, durable=True)
                channel.queue_bind(
                    exchange=EXCHANGE_NAME,
                    queue=queue_name,
                    routing_key=routing_key,
                )

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue="scraper.jobs", on_message_callback=self._on_message, auto_ack=False
            )
            while not self._stop_event.is_set():
                connection.process_data_events(time_limit=1)
            connection.close()
        except Exception as exc:
            logger.error("rabbitmq_consumer_error", error=str(exc))

    def _on_message(
        self,
        channel: pika.channel.Channel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ) -> None:
        routing_key = method.routing_key
        try:
            payload = json.loads(body)
            handler = self._handlers.get(routing_key)
            if handler:
                handler(payload)
            else:
                logger.warning("no_handler_for_routing_key", routing_key=routing_key)
            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.error("message_processing_error", routing_key=routing_key, error=str(exc))
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
