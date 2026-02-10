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
