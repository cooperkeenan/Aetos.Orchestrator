"""
RabbitMQ event publisher.

Uses pika in a thread-pool executor so blocking I/O doesn't stall the
asyncio event loop. A new connection is opened per publish call for
simplicity; swap for a persistent connection pool in production.
"""
import asyncio
import json
from functools import partial

import pika
import structlog

from src.config import settings
from src.domain.events.domain_events import (
    DomainEvent,
    ListingCreatedEvent,
    ListingStateChangedEvent,
    ScraperJobCreatedEvent,
)

logger = structlog.get_logger(__name__)

EXCHANGE_NAME = "orchestrator.events"


def _event_to_routing_key(event: DomainEvent) -> str:
    if isinstance(event, ScraperJobCreatedEvent):
        return "scraper.job.created"
    if isinstance(event, ListingStateChangedEvent):
        return f"listing.state.{event.to_state.value.lower()}"
    if isinstance(event, ListingCreatedEvent):
        return "listing.created"
    return "event.unknown"


def _serialise_event(event: DomainEvent) -> str:
    payload: dict = {  # type: ignore[type-arg]
        "event_type": _event_to_routing_key(event),
        "event_id": str(event.event_id),
        "occurred_at": event.occurred_at.isoformat(),
    }

    if isinstance(event, ScraperJobCreatedEvent):
        payload.update({"job_id": str(event.job_id), "brand": event.brand, "search": event.search})
    elif isinstance(event, ListingStateChangedEvent):
        payload.update(
            {
                "listing_id": str(event.listing_id),
                "from_state": event.from_state.value if event.from_state else None,
                "to_state": event.to_state.value,
                "triggered_by": event.triggered_by,
            }
        )
    elif isinstance(event, ListingCreatedEvent):
        payload.update(
            {
                "listing_id": str(event.listing_id),
                "product_id": event.product_id,
                "scraper_job_id": str(event.scraper_job_id),
                "brand": event.brand,
                "model": event.model,
            }
        )

    return json.dumps(payload, default=str)


def _blocking_publish(rabbitmq_url: str, routing_key: str, body: str) -> None:
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    try:
        channel = connection.channel()
        channel.exchange_declare(
            exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
        )
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=body.encode(),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                content_type="application/json",
            ),
        )
    finally:
        connection.close()


class RabbitMQPublisher:
    """Publishes domain events to a RabbitMQ topic exchange."""

    def __init__(self, rabbitmq_url: str = settings.rabbitmq_url) -> None:
        self._url = rabbitmq_url

    async def publish(self, event: DomainEvent) -> None:
        routing_key = _event_to_routing_key(event)
        body = _serialise_event(event)
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                partial(_blocking_publish, self._url, routing_key, body),
            )
            logger.debug("event_published", routing_key=routing_key, event_id=str(event.event_id))
        except Exception as exc:
            logger.error(
                "failed_to_publish_event",
                routing_key=routing_key,
                error=str(exc),
            )
            # Don't re-raise — event publishing failure should not crash the request.

    async def publish_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)
