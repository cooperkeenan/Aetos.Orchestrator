from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.enums.listing_state import ListingState


@dataclass
class StateHistoryRecord:
    id: UUID
    listing_id: UUID
    from_state: ListingState | None
    to_state: ListingState
    transitioned_at: datetime
    triggered_by: str
    metadata: dict  # type: ignore[type-arg]


class StateHistoryRepository(ABC):
    """Port for persisting and querying state transition history."""

    @abstractmethod
    async def save(
        self,
        *,
        listing_id: UUID,
        from_state: ListingState | None,
        to_state: ListingState,
        triggered_by: str,
        metadata: dict | None = None,  # type: ignore[type-arg]
    ) -> StateHistoryRecord:
        ...

    @abstractmethod
    async def get_history_for_listing(
        self, listing_id: UUID
    ) -> list[StateHistoryRecord]:
        ...
