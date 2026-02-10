from dataclasses import dataclass
from uuid import UUID

import structlog

from src.application.interfaces.listing_repository import ListingRepository
from src.application.interfaces.state_history_repository import (
    StateHistoryRecord,
    StateHistoryRepository,
)
from src.application.use_cases.transition_listing_state import ListingNotFoundError

logger = structlog.get_logger(__name__)


@dataclass
class GetListingHistoryInput:
    listing_id: UUID


@dataclass
class GetListingHistoryOutput:
    listing_id: UUID
    history: list[StateHistoryRecord]


class GetListingHistory:
    """Use case: Retrieve the full state transition history for a listing."""

    def __init__(
        self,
        listing_repo: ListingRepository,
        history_repo: StateHistoryRepository,
    ) -> None:
        self._listing_repo = listing_repo
        self._history_repo = history_repo

    async def execute(self, input_data: GetListingHistoryInput) -> GetListingHistoryOutput:
        listing = await self._listing_repo.get_by_id(input_data.listing_id)
        if listing is None:
            raise ListingNotFoundError(input_data.listing_id)

        history = await self._history_repo.get_history_for_listing(input_data.listing_id)

        return GetListingHistoryOutput(listing_id=input_data.listing_id, history=history)
