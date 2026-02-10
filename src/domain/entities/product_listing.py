from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from src.domain.enums.listing_state import ListingState
from src.domain.events.domain_events import (
    DomainEvent,
    ListingCreatedEvent,
    ListingStateChangedEvent,
)
from src.domain.state_machine.lifecycle_state_machine import LifecycleStateMachine

_state_machine = LifecycleStateMachine()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProductListing:
    """
    Core domain entity representing a single marketplace listing being tracked
    through the buy/resell lifecycle.

    Emits domain events on state transitions — callers are responsible for
    collecting and publishing them.
    """

    # Identity
    id: UUID = field(default_factory=uuid4)
    product_id: int = 0

    # Marketplace data
    marketplace_url: str = ""
    title: str = ""
    asking_price: Decimal = Decimal("0")

    # State
    state: ListingState = ListingState.FOUND

    # Timestamps
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    state_changed_at: datetime = field(default_factory=_utcnow)

    # Lifecycle timestamps
    found_at: datetime = field(default_factory=_utcnow)
    messaged_at: datetime | None = None
    negotiating_at: datetime | None = None
    purchased_at: datetime | None = None
    received_at: datetime | None = None
    listed_at: datetime | None = None
    sold_at: datetime | None = None
    cancelled_at: datetime | None = None

    # ScraperV2 metadata
    scraper_job_id: UUID = field(default_factory=uuid4)
    brand: str = ""
    model: str = ""
    confidence_score: Decimal = Decimal("0")
    estimated_profit: Decimal = Decimal("0")

    # Deal details (populated during MESSAGING/NEGOTIATING/PURCHASED)
    negotiated_price: Decimal | None = None
    seller_messenger_id: str | None = None
    conversation_thread_id: str | None = None

    # eBay details (populated during LISTED/SOLD)
    ebay_listing_id: str | None = None
    ebay_asking_price: Decimal | None = None
    ebay_sold_price: Decimal | None = None

    # Profit tracking
    purchase_price: Decimal | None = None
    shipping_cost: Decimal | None = None
    ebay_fees: Decimal | None = None
    final_profit: Decimal | None = None

    # Error tracking
    error_message: str | None = None
    error_occurred_at: datetime | None = None

    # Pending domain events (collected and cleared by the application layer)
    _events: list[DomainEvent] = field(default_factory=list, repr=False, compare=False)

    # -------------------------------------------------------------------------
    # Factory
    # -------------------------------------------------------------------------

    @classmethod
    def create_from_scraper_match(
        cls,
        *,
        product_id: int,
        marketplace_url: str,
        title: str,
        asking_price: Decimal,
        scraper_job_id: UUID,
        brand: str,
        model: str,
        confidence_score: Decimal,
        estimated_profit: Decimal,
    ) -> "ProductListing":
        listing = cls(
            product_id=product_id,
            marketplace_url=marketplace_url,
            title=title,
            asking_price=asking_price,
            scraper_job_id=scraper_job_id,
            brand=brand,
            model=model,
            confidence_score=confidence_score,
            estimated_profit=estimated_profit,
        )
        listing._events.append(
            ListingCreatedEvent(
                listing_id=listing.id,
                product_id=product_id,
                scraper_job_id=scraper_job_id,
                brand=brand,
                model=model,
                marketplace_url=marketplace_url,
                asking_price=float(asking_price),
                confidence_score=float(confidence_score),
                estimated_profit=float(estimated_profit),
            )
        )
        return listing

    # -------------------------------------------------------------------------
    # State transitions
    # -------------------------------------------------------------------------

    def transition_to(self, new_state: ListingState, triggered_by: str) -> None:
        """Validate and apply a state transition, recording the domain event."""
        _state_machine.validate_transition(self.state, new_state)

        old_state = self.state
        now = _utcnow()

        self.state = new_state
        self.state_changed_at = now
        self.updated_at = now

        self._apply_lifecycle_timestamp(new_state, now)

        self._events.append(
            ListingStateChangedEvent(
                listing_id=self.id,
                from_state=old_state,
                to_state=new_state,
                triggered_by=triggered_by,
            )
        )

    def _apply_lifecycle_timestamp(self, state: ListingState, now: datetime) -> None:
        mapping: dict[ListingState, str] = {
            ListingState.MESSAGING: "messaged_at",
            ListingState.NEGOTIATING: "negotiating_at",
            ListingState.PURCHASED: "purchased_at",
            ListingState.RECEIVED: "received_at",
            ListingState.LISTED: "listed_at",
            ListingState.SOLD: "sold_at",
            ListingState.CANCELLED: "cancelled_at",
        }
        attr = mapping.get(state)
        if attr:
            setattr(self, attr, now)

    def record_error(self, message: str) -> None:
        self.error_message = message
        self.error_occurred_at = _utcnow()
        self.updated_at = _utcnow()

    # -------------------------------------------------------------------------
    # Event collection
    # -------------------------------------------------------------------------

    def collect_events(self) -> list[DomainEvent]:
        """Return pending events and clear the internal buffer."""
        events = list(self._events)
        self._events.clear()
        return events
