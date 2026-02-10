from fastapi import APIRouter, Depends, status

from src.api.dependencies import get_create_listings_use_case
from src.api.schemas.listing_responses import WebhookAcceptedResponse
from src.api.schemas.scraper_webhook import ScraperJobCompleteWebhookPayload
from src.application.use_cases.create_listings_from_scraper import (
    CreateListingsFromScraper,
    CreateListingsFromScraperInput,
    ScraperMatch,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post(
    "/scraper/job-complete",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WebhookAcceptedResponse,
)
async def scraper_job_complete(
    payload: ScraperJobCompleteWebhookPayload,
    use_case: CreateListingsFromScraper = Depends(get_create_listings_use_case),
) -> WebhookAcceptedResponse:
    """
    Called by ScraperV2 when a scrape job finishes.
    Creates a ProductListing in FOUND state for each matched camera.
    """
    matches = [
        ScraperMatch(
            url=m.listing.url,
            title=m.listing.title,
            price=m.listing.price,
            product_id=m.product.id,
            brand=m.product.brand,
            model=m.product.model,
            confidence=m.confidence,
            potential_profit=m.potential_profit,
        )
        for m in payload.matches
    ]

    result = await use_case.execute(
        CreateListingsFromScraperInput(
            job_id=payload.job_id,
            brand=payload.brand,
            matches=matches,
        )
    )

    return WebhookAcceptedResponse(
        created_listings=len(result.created_listing_ids),
        skipped=result.skipped_count,
    )
