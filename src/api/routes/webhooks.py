import structlog
from decimal import Decimal
from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_listing_repo, get_history_repo
from src.api.schemas.listing_responses import WebhookAcceptedResponse
from src.api.schemas.scraper_webhook import ScraperJobCompleteWebhookPayload
from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState
from src.infrastructure.database.repositories.listing_repository import (
    SqlAlchemyListingRepository,
)
from src.infrastructure.database.repositories.state_history_repository import (
    SqlAlchemyStateHistoryRepository,
)
from src.infrastructure.messaging.rabbitmq_publisher import RabbitMQPublisher

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/scraper/job-complete",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WebhookAcceptedResponse,
)
async def scraper_job_complete(
    payload: ScraperJobCompleteWebhookPayload,
    listing_repo: SqlAlchemyListingRepository = Depends(get_listing_repo),
    history_repo: SqlAlchemyStateHistoryRepository = Depends(get_history_repo),
) -> WebhookAcceptedResponse:
    """Called by ScraperV2 when a scrape job finishes.
    Creates a ProductListing in FOUND state for each matched camera.
    """
    created_ids = []
    skipped = 0
    publisher = RabbitMQPublisher()

    for match in payload.matches:
        try:
            listing = ProductListing.create_from_scraper_match(
                product_id=match.product.id,
                marketplace_url=match.listing.url,
                title=match.listing.title,
                asking_price=Decimal(str(match.listing.price)),
                scraper_job_id=payload.job_id,
                brand=match.product.brand,
                model=match.product.model,
                confidence_score=Decimal(str(match.confidence)),
                estimated_profit=Decimal(str(match.potential_profit)),
            )

            await listing_repo.save(listing)

            await history_repo.save(
                listing_id=listing.id,
                from_state=None,
                to_state=ListingState.FOUND,
                triggered_by="scraper_webhook",
                metadata={"job_id": str(payload.job_id), "brand": payload.brand},
            )

            await publisher.publish_many(listing.collect_events())
            created_ids.append(listing.id)
            logger.info(
                "listing_created",
                listing_id=str(listing.id),
                brand=match.product.brand,
                model=match.product.model,
            )
        except Exception:
            logger.exception("failed_to_create_listing", url=match.listing.url)
            skipped += 1

    return WebhookAcceptedResponse(
        created_listings=len(created_ids),
        skipped=skipped,
    )
