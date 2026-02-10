from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.connection import get_db_session
from src.infrastructure.database.repositories.listing_repository import (
    SqlAlchemyListingRepository,
)
from src.infrastructure.database.repositories.state_history_repository import (
    SqlAlchemyStateHistoryRepository,
)
from src.infrastructure.external_services.scraper_client import ScraperClient
from src.infrastructure.external_services.scraper_coordinator import ScraperCoordinator


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_listing_repo(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyListingRepository:
    return SqlAlchemyListingRepository(session)


def get_history_repo(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyStateHistoryRepository:
    return SqlAlchemyStateHistoryRepository(session)


def get_scraper_coordinator() -> ScraperCoordinator:
    return ScraperCoordinator(ScraperClient())
