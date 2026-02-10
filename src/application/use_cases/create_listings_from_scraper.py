from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import structlog

from src.application.interfaces.event_publisher import EventPublisher
from src.application.interfaces.listing_repository import ListingRepository
from src.application.interfaces.state_history_repository import StateHistoryRepository
from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState

logger = structlog.get_logger(__name__)


@dataclass
class ScraperMatch:
    url: str
    title: str
    price: float
    product_id: int
    brand: str
    model: str
    confidence: float
    potential_profit: float


@dataclass
class CreateListingsFromScraperInput:
    job_id: UUID
    brand: str
    matches: list[ScraperMatch]


@dataclass
class CreateListingsFromScraperOutput:
    created_listing_ids: list[UUID]
    skipped_count: int


class CreateListingsFromScraper:
    """
    Use case: Process a completed ScraperV2 job and persist a ProductListing
    for each matched camera in the FOUND state.
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
        self, input_data: CreateListingsFromScraperInput
    ) -> CreateListingsFromScraperOutput:
        created_ids: list[UUID] = []
        skipped = 0

        for match in input_data.matches:
            try:
                listing = ProductListing.create_from_scraper_match(
                    product_id=match.product_id,
                    marketplace_url=match.url,
                    title=match.title,
                    asking_price=Decimal(str(match.price)),
                    scraper_job_id=input_data.job_id,
                    brand=match.brand,
                    model=match.model,
                    confidence_score=Decimal(str(match.confidence)),
                    estimated_profit=Decimal(str(match.potential_profit)),
                )

                await self._listing_repo.save(listing)

                await self._history_repo.save(
                    listing_id=listing.id,
                    from_state=None,
                    to_state=ListingState.FOUND,
                    triggered_by="scraper_webhook",
                    metadata={"job_id": str(input_data.job_id), "brand": input_data.brand},
                )

                events = listing.collect_events()
                await self._event_publisher.publish_many(events)

                created_ids.append(listing.id)
                logger.info(
                    "listing_created",
                    listing_id=str(listing.id),
                    product_id=match.product_id,
                    brand=match.brand,
                    model=match.model,
                )

            except Exception:
                logger.exception(
                    "failed_to_create_listing",
                    url=match.url,
                    product_id=match.product_id,
                )
                skipped += 1

        return CreateListingsFromScraperOutput(
            created_listing_ids=created_ids,
            skipped_count=skipped,
        )
