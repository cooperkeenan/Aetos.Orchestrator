"""
No-op event publisher — used in tests and when RabbitMQ is unavailable.
"""
import structlog

from src.application.interfaces.event_publisher import EventPublisher
from src.domain.events.domain_events import DomainEvent

logger = structlog.get_logger(__name__)


class NoOpEventPublisher(EventPublisher):
    """Discards all events. Useful for testing and local development."""

    async def publish(self, event: DomainEvent) -> None:
        logger.debug("noop_event_discarded", event_type=type(event).__name__)
