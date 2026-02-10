from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.dependencies import (
    get_history_repo,
    get_listing_repo,
    get_scraper_coordinator,
)
from src.api.schemas.listing_responses import (
    ListingHistoryResponse,
    ListingResponse,
    PaginatedListingsResponse,
    StateHistoryEntryResponse,
    TransitionRequest,
    TriggerScrapeRequest,
    TriggerScrapeResponse,
)
from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState
from src.domain.state_machine.lifecycle_state_machine import InvalidStateTransitionError
from src.infrastructure.database.repositories.listing_repository import (
    SqlAlchemyListingRepository,
)
from src.infrastructure.database.repositories.state_history_repository import (
    SqlAlchemyStateHistoryRepository,
)
from src.infrastructure.external_services.scraper_coordinator import ScraperCoordinator
from src.infrastructure.messaging.rabbitmq_publisher import RabbitMQPublisher

router = APIRouter(prefix="/admin", tags=["admin"])


def _listing_to_response(listing: ProductListing) -> ListingResponse:
    return ListingResponse(
        id=listing.id,
        product_id=listing.product_id,
        marketplace_url=listing.marketplace_url,
        title=listing.title,
        asking_price=listing.asking_price,
        state=listing.state,
        brand=listing.brand,
        model=listing.model,
        confidence_score=listing.confidence_score,
        estimated_profit=listing.estimated_profit,
        scraper_job_id=listing.scraper_job_id,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        state_changed_at=listing.state_changed_at,
        found_at=listing.found_at,
        messaged_at=listing.messaged_at,
        negotiating_at=listing.negotiating_at,
        purchased_at=listing.purchased_at,
        received_at=listing.received_at,
        listed_at=listing.listed_at,
        sold_at=listing.sold_at,
        cancelled_at=listing.cancelled_at,
        negotiated_price=listing.negotiated_price,
        purchase_price=listing.purchase_price,
        final_profit=listing.final_profit,
        ebay_listing_id=listing.ebay_listing_id,
        ebay_sold_price=listing.ebay_sold_price,
        error_message=listing.error_message,
    )


@router.get("/listings", response_model=PaginatedListingsResponse)
async def list_listings(
    state: ListingState | None = Query(default=None),
    brand: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repo: SqlAlchemyListingRepository = Depends(get_listing_repo),
) -> PaginatedListingsResponse:
    """List product listings with optional filtering."""
    listings, total = await repo.list_all(state=state, brand=brand, limit=limit, offset=offset)
    return PaginatedListingsResponse(
        listings=[_listing_to_response(l) for l in listings],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(
    listing_id: UUID,
    repo: SqlAlchemyListingRepository = Depends(get_listing_repo),
) -> ListingResponse:
    listing = await repo.get_by_id(listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")
    return _listing_to_response(listing)


@router.get("/listings/{listing_id}/history", response_model=ListingHistoryResponse)
async def get_listing_history(
    listing_id: UUID,
    listing_repo: SqlAlchemyListingRepository = Depends(get_listing_repo),
    history_repo: SqlAlchemyStateHistoryRepository = Depends(get_history_repo),
) -> ListingHistoryResponse:
    listing = await listing_repo.get_by_id(listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")

    history = await history_repo.get_history_for_listing(listing_id)
    return ListingHistoryResponse(
        listing_id=listing_id,
        history=[
            StateHistoryEntryResponse(
                id=entry.id,
                from_state=entry.from_state,
                to_state=entry.to_state,
                transitioned_at=entry.transitioned_at,
                triggered_by=entry.triggered_by,
                metadata=entry.metadata,
            )
            for entry in history
        ],
    )


@router.post("/listings/{listing_id}/transition", response_model=ListingResponse)
async def transition_listing(
    listing_id: UUID,
    body: TransitionRequest,
    listing_repo: SqlAlchemyListingRepository = Depends(get_listing_repo),
    history_repo: SqlAlchemyStateHistoryRepository = Depends(get_history_repo),
) -> ListingResponse:
    listing = await listing_repo.get_by_id(listing_id)
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found.")

    from_state = listing.state
    try:
        listing.transition_to(body.to_state, triggered_by="admin_api")
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await listing_repo.save(listing)

    metadata = {"reason": body.reason} if body.reason else {}
    await history_repo.save(
        listing_id=listing.id,
        from_state=from_state,
        to_state=body.to_state,
        triggered_by="admin_api",
        metadata=metadata,
    )

    await RabbitMQPublisher().publish_many(listing.collect_events())

    return _listing_to_response(listing)


@router.post("/scrape/trigger", response_model=TriggerScrapeResponse)
async def trigger_scrape(
    body: TriggerScrapeRequest,
    coordinator: ScraperCoordinator = Depends(get_scraper_coordinator),
) -> TriggerScrapeResponse:
    """Manually trigger a ScraperV2 job for a given brand."""
    result = await coordinator.trigger_scrape(brand=body.brand, search=body.search)
    return TriggerScrapeResponse(job_id=result.job_id, status=result.status)
