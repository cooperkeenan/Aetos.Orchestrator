from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass
class ScraperJobResult:
    job_id: UUID
    status: str  # "pending" | "running" | "complete" | "error"


class ScraperCoordinatorInterface(ABC):
    """Port for triggering ScraperV2 jobs."""

    @abstractmethod
    async def trigger_scrape(self, brand: str, search: str | None = None) -> ScraperJobResult:
        ...


class ChatterbotCoordinatorInterface(ABC):
    """Port for sending listings to Chatterbot (Phase 2)."""

    @abstractmethod
    async def send_listing_for_messaging(self, listing_id: UUID, marketplace_url: str) -> None:
        ...


class EbayCoordinatorInterface(ABC):
    """Port for triggering eBay listing creation (Phase 3)."""

    @abstractmethod
    async def create_listing(self, listing_id: UUID, photos: list[str]) -> str:
        """Returns the eBay listing ID."""
        ...
