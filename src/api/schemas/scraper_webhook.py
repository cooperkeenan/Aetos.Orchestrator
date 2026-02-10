from uuid import UUID

from pydantic import BaseModel, Field


class ScraperListingSchema(BaseModel):
    url: str
    title: str
    price: float


class ScraperProductSchema(BaseModel):
    id: int
    brand: str
    model: str


class ScraperMatchSchema(BaseModel):
    listing: ScraperListingSchema
    product: ScraperProductSchema
    confidence: float = Field(ge=0.0, le=100.0)
    potential_profit: float


class ScraperJobCompleteWebhookPayload(BaseModel):
    job_id: UUID
    brand: str
    matches: list[ScraperMatchSchema]
