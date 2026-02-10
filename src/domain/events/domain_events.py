from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.domain.enums.listing_state import ListingState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class ListingCreatedEvent(DomainEvent):
    """Published when a new product listing is created from scraper results."""

    listing_id: UUID = field(default_factory=uuid4)
    product_id: int = 0
    scraper_job_id: UUID = field(default_factory=uuid4)
    brand: str = ""
    model: str = ""
    marketplace_url: str = ""
    asking_price: float = 0.0
    confidence_score: float = 0.0
    estimated_profit: float = 0.0


@dataclass(frozen=True)
class ListingStateChangedEvent(DomainEvent):
    """Published whenever a listing transitions between states."""

    listing_id: UUID = field(default_factory=uuid4)
    from_state: ListingState | None = None
    to_state: ListingState = ListingState.FOUND
    triggered_by: str = ""


@dataclass(frozen=True)
class ScraperJobCreatedEvent(DomainEvent):
    """Published when the orchestrator triggers a new scraper job."""

    job_id: UUID = field(default_factory=uuid4)
    brand: str = ""
    search: str = ""
