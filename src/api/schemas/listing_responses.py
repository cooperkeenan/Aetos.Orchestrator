from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from src.domain.enums.listing_state import ListingState


class ListingResponse(BaseModel):
    id: UUID
    product_id: int
    marketplace_url: str
    title: str
    asking_price: Decimal
    state: ListingState
    brand: str
    model: str
    confidence_score: Decimal
    estimated_profit: Decimal
    scraper_job_id: UUID
    created_at: datetime
    updated_at: datetime
    state_changed_at: datetime
    found_at: datetime
    messaged_at: datetime | None = None
    negotiating_at: datetime | None = None
    purchased_at: datetime | None = None
    received_at: datetime | None = None
    listed_at: datetime | None = None
    sold_at: datetime | None = None
    cancelled_at: datetime | None = None
    negotiated_price: Decimal | None = None
    purchase_price: Decimal | None = None
    final_profit: Decimal | None = None
    ebay_listing_id: str | None = None
    ebay_sold_price: Decimal | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class PaginatedListingsResponse(BaseModel):
    listings: list[ListingResponse]
    total: int
    limit: int
    offset: int


class StateHistoryEntryResponse(BaseModel):
    id: UUID
    from_state: ListingState | None
    to_state: ListingState
    transitioned_at: datetime
    triggered_by: str
    metadata: dict  # type: ignore[type-arg]


class ListingHistoryResponse(BaseModel):
    listing_id: UUID
    history: list[StateHistoryEntryResponse]


class TransitionRequest(BaseModel):
    to_state: ListingState
    reason: str | None = None


class TriggerScrapeRequest(BaseModel):
    brand: str
    search: str | None = None


class TriggerScrapeResponse(BaseModel):
    job_id: UUID
    status: str


class WebhookAcceptedResponse(BaseModel):
    accepted: bool = True
    created_listings: int
    skipped: int
