from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState


class ListingRepository(ABC):
    """Port for persisting and querying ProductListing aggregates."""

    @abstractmethod
    async def save(self, listing: ProductListing) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, listing_id: UUID) -> ProductListing | None:
        ...

    @abstractmethod
    async def list_all(
        self,
        *,
        state: ListingState | None = None,
        brand: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProductListing], int]:
        """Return (listings, total_count)."""
        ...
