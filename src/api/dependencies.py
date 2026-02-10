"""
FastAPI dependency injection wiring.

Each dependency function returns a fully-constructed object with its
collaborators injected — keeping the route handlers thin.
"""
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.coordinators.scraper_coordinator import ScraperCoordinator
from src.application.interfaces.event_publisher import EventPublisher
from src.application.interfaces.listing_repository import ListingRepository
from src.application.interfaces.state_history_repository import StateHistoryRepository
from src.application.use_cases.create_listings_from_scraper import CreateListingsFromScraper
from src.application.use_cases.get_listing_history import GetListingHistory
from src.application.use_cases.transition_listing_state import TransitionListingState
from src.infrastructure.database.connection import get_db_session
from src.infrastructure.database.repositories.listing_repository_impl import (
    SqlAlchemyListingRepository,
)
from src.infrastructure.database.repositories.state_history_repository_impl import (
    SqlAlchemyStateHistoryRepository,
)
from src.infrastructure.external_services.scraper_client import ScraperClient
from src.infrastructure.messaging.rabbitmq_publisher import RabbitMQPublisher


# ---- Low-level dependencies ------------------------------------------------

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_listing_repo(session: AsyncSession = Depends(get_session)) -> ListingRepository:
    return SqlAlchemyListingRepository(session)


def get_history_repo(session: AsyncSession = Depends(get_session)) -> StateHistoryRepository:
    return SqlAlchemyStateHistoryRepository(session)


def get_event_publisher() -> EventPublisher:
    return RabbitMQPublisher()


# ---- Use-case dependencies -------------------------------------------------

def get_create_listings_use_case(
    listing_repo: ListingRepository = Depends(get_listing_repo),
    history_repo: StateHistoryRepository = Depends(get_history_repo),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> CreateListingsFromScraper:
    return CreateListingsFromScraper(listing_repo, history_repo, event_publisher)


def get_transition_state_use_case(
    listing_repo: ListingRepository = Depends(get_listing_repo),
    history_repo: StateHistoryRepository = Depends(get_history_repo),
    event_publisher: EventPublisher = Depends(get_event_publisher),
) -> TransitionListingState:
    return TransitionListingState(listing_repo, history_repo, event_publisher)


def get_listing_history_use_case(
    listing_repo: ListingRepository = Depends(get_listing_repo),
    history_repo: StateHistoryRepository = Depends(get_history_repo),
) -> GetListingHistory:
    return GetListingHistory(listing_repo, history_repo)


# ---- External service coordinators ----------------------------------------

def get_scraper_coordinator() -> ScraperCoordinator:
    return ScraperCoordinator(ScraperClient())
