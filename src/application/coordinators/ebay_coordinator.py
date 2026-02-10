"""
eBay coordinator stub — Phase 3 implementation.

This interface is defined now so the rest of the architecture is wired up
correctly, but all methods raise NotImplementedError until Phase 3.
"""
from uuid import UUID

from src.application.interfaces.service_coordinator import EbayCoordinatorInterface


class EbayCoordinator(EbayCoordinatorInterface):
    """Stub coordinator for eBayLister service (Phase 3)."""

    async def create_listing(self, listing_id: UUID, photos: list[str]) -> str:
        raise NotImplementedError("eBay listing integration is a Phase 3 feature.")
