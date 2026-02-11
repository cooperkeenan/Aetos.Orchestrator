"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create listing_state enum
    listing_state = sa.Enum(
        "FOUND",
        "MESSAGING",
        "NEGOTIATING",
        "PURCHASED",
        "RECEIVED",
        "LISTED",
        "SOLD",
        "CANCELLED",
        name="listing_state",
    )
    listing_state.create(op.get_bind(), checkfirst=True)

    # Product lifecycle tracking table
    op.create_table(
        "product_lifecycle",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("marketplace_url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("asking_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("state", listing_state, nullable=False),
        sa.Column(
            "state_changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Lifecycle timestamps
        sa.Column("found_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("messaged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("negotiating_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("listed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        # ScraperV2 metadata
        sa.Column("scraper_job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("brand", sa.String(128), nullable=False),
        sa.Column("model", sa.String(256), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("estimated_profit", sa.Numeric(10, 2), nullable=False),
        # Deal details
        sa.Column("negotiated_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("seller_messenger_id", sa.String(256), nullable=True),
        sa.Column("conversation_thread_id", sa.String(256), nullable=True),
        # eBay details
        sa.Column("ebay_listing_id", sa.String(256), nullable=True),
        sa.Column("ebay_asking_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("ebay_sold_price", sa.Numeric(10, 2), nullable=True),
        # Profit tracking
        sa.Column("purchase_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("shipping_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("ebay_fees", sa.Numeric(10, 2), nullable=True),
        sa.Column("final_profit", sa.Numeric(10, 2), nullable=True),
        # Error tracking
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_index("ix_product_lifecycle_product_id", "product_lifecycle", ["product_id"])
    op.create_index("ix_product_lifecycle_state", "product_lifecycle", ["state"])
    op.create_index("ix_product_lifecycle_scraper_job_id", "product_lifecycle", ["scraper_job_id"])
    op.create_index("ix_product_lifecycle_brand", "product_lifecycle", ["brand"])
    op.create_index("ix_product_lifecycle_brand_state", "product_lifecycle", ["brand", "state"])

    # State history table for audit trail
    op.create_table(
        "product_state_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lifecycle_id",
            UUID(as_uuid=True),
            sa.ForeignKey("product_lifecycle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_state", listing_state, nullable=True),
        sa.Column("to_state", listing_state, nullable=False),
        sa.Column(
            "transitioned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("triggered_by", sa.String(256), nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_product_state_history_lifecycle_id", "product_state_history", ["lifecycle_id"])


def downgrade() -> None:
    op.drop_table("product_state_history")
    op.drop_table("product_lifecycle")
    sa.Enum(name="listing_state").drop(op.get_bind(), checkfirst=True)