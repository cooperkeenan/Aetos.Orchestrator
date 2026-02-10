from abc import ABC, abstractmethod

from src.domain.events.domain_events import DomainEvent


class EventPublisher(ABC):
    """Port for publishing domain events to the message bus."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        ...

    async def publish_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)
