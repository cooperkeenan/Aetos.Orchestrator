"""
Chatterbot coordinator stub — Phase 2 implementation.

This interface is defined now so the rest of the architecture is wired up
correctly, but all methods raise NotImplementedError until Phase 2.
"""
from uuid import UUID

from src.application.interfaces.service_coordinator import ChatterbotCoordinatorInterface


class ChatterbotCoordinator(ChatterbotCoordinatorInterface):
    """Stub coordinator for Chatterbot service (Phase 2)."""

    async def send_listing_for_messaging(self, listing_id: UUID, marketplace_url: str) -> None:
        raise NotImplementedError("Chatterbot integration is a Phase 2 feature.")
