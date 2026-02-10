"""
SQLAlchemy ORM models.

These are purely infrastructure concerns — domain entities are mapped to/from
these models inside the repository implementations.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums.listing_state import ListingState
from src.infrastructure.database.connection import Base

_listing_state_enum = SAEnum(
    ListingState,
    name="listing_state",
    values_callable=lambda obj: [e.value for e in obj],
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProductListingModel(Base):
    __tablename__ = "product_listings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[int] = mapped_column(nullable=False, index=True)

    # Marketplace data
    marketplace_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    asking_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # State
    state: Mapped[str] = mapped_column(_listing_state_enum, nullable=False, index=True)
    state_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Lifecycle timestamps
    found_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    messaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    negotiating_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purchased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ScraperV2 metadata
    scraper_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(256), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    estimated_profit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Deal details
    negotiated_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    seller_messenger_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    conversation_thread_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # eBay details
    ebay_listing_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ebay_asking_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ebay_sold_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Profit tracking
    purchase_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    shipping_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ebay_fees: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    final_profit: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    state_history: Mapped[list["ProductStateHistoryModel"]] = relationship(
        "ProductStateHistoryModel",
        back_populates="listing",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        Index("ix_product_listings_brand_state", "brand", "state"),
    )


class ProductStateHistoryModel(Base):
    __tablename__ = "product_state_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_state: Mapped[str | None] = mapped_column(_listing_state_enum, nullable=True)
    to_state: Mapped[str] = mapped_column(_listing_state_enum, nullable=False)
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    triggered_by: Mapped[str] = mapped_column(String(256), nullable=False)
    metadata_: Mapped[dict] = mapped_column(  # type: ignore[type-arg]
        "metadata", JSONB, nullable=False, default=dict
    )

    listing: Mapped[ProductListingModel] = relationship(
        "ProductListingModel", back_populates="state_history"
    )
