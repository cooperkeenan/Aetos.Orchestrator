from dataclasses import dataclass
from uuid import UUID

import structlog

from src.application.interfaces.event_publisher import EventPublisher
from src.application.interfaces.listing_repository import ListingRepository
from src.application.interfaces.state_history_repository import StateHistoryRepository
from src.domain.enums.listing_state import ListingState
from src.domain.state_machine.lifecycle_state_machine import InvalidStateTransitionError

logger = structlog.get_logger(__name__)


class ListingNotFoundError(Exception):
    def __init__(self, listing_id: UUID) -> None:
        super().__init__(f"Listing {listing_id} not found.")


@dataclass
class TransitionListingStateInput:
    listing_id: UUID
    to_state: ListingState
    triggered_by: str
    reason: str | None = None


@dataclass
class TransitionListingStateOutput:
    listing_id: UUID
    from_state: ListingState
    to_state: ListingState


class TransitionListingState:
    """
    Use case: Transition a ProductListing from its current state to a new one.

    Validates the transition via the state machine, persists the change,
    records the history entry, and publishes domain events.
    """

    def __init__(
        self,
        listing_repo: ListingRepository,
        history_repo: StateHistoryRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._listing_repo = listing_repo
        self._history_repo = history_repo
        self._event_publisher = event_publisher

    async def execute(
        self, input_data: TransitionListingStateInput
    ) -> TransitionListingStateOutput:
        listing = await self._listing_repo.get_by_id(input_data.listing_id)
        if listing is None:
            raise ListingNotFoundError(input_data.listing_id)

        from_state = listing.state

        # May raise InvalidStateTransitionError — let it propagate to the caller
        listing.transition_to(input_data.to_state, triggered_by=input_data.triggered_by)

        await self._listing_repo.save(listing)

        metadata: dict = {"triggered_by": input_data.triggered_by}  # type: ignore[type-arg]
        if input_data.reason:
            metadata["reason"] = input_data.reason

        await self._history_repo.save(
            listing_id=listing.id,
            from_state=from_state,
            to_state=input_data.to_state,
            triggered_by=input_data.triggered_by,
            metadata=metadata,
        )

        events = listing.collect_events()
        await self._event_publisher.publish_many(events)

        logger.info(
            "listing_state_transitioned",
            listing_id=str(listing.id),
            from_state=from_state.value,
            to_state=input_data.to_state.value,
            triggered_by=input_data.triggered_by,
        )

        return TransitionListingStateOutput(
            listing_id=listing.id,
            from_state=from_state,
            to_state=input_data.to_state,
        )
