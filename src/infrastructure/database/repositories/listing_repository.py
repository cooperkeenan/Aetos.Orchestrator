from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState
from src.infrastructure.database.models import ProductListingModel


def _to_domain(model: ProductListingModel) -> ProductListing:
    def _dec(value: float | None) -> Decimal | None:
        return Decimal(str(value)) if value is not None else None

    return ProductListing(
        id=model.id,
        product_id=model.product_id,
        marketplace_url=model.marketplace_url,
        title=model.title,
        asking_price=Decimal(str(model.asking_price)),
        state=ListingState(model.state),
        created_at=model.created_at,
        updated_at=model.updated_at,
        state_changed_at=model.state_changed_at,
        found_at=model.found_at,
        messaged_at=model.messaged_at,
        negotiating_at=model.negotiating_at,
        purchased_at=model.purchased_at,
        received_at=model.received_at,
        listed_at=model.listed_at,
        sold_at=model.sold_at,
        cancelled_at=model.cancelled_at,
        scraper_job_id=model.scraper_job_id,
        brand=model.brand,
        model=model.model,
        confidence_score=Decimal(str(model.confidence_score)),
        estimated_profit=Decimal(str(model.estimated_profit)),
        negotiated_price=_dec(model.negotiated_price),
        seller_messenger_id=model.seller_messenger_id,
        conversation_thread_id=model.conversation_thread_id,
        ebay_listing_id=model.ebay_listing_id,
        ebay_asking_price=_dec(model.ebay_asking_price),
        ebay_sold_price=_dec(model.ebay_sold_price),
        purchase_price=_dec(model.purchase_price),
        shipping_cost=_dec(model.shipping_cost),
        ebay_fees=_dec(model.ebay_fees),
        final_profit=_dec(model.final_profit),
        error_message=model.error_message,
        error_occurred_at=model.error_occurred_at,
    )


def _to_model(listing: ProductListing) -> ProductListingModel:
    def _flt(value: Decimal | None) -> float | None:
        return float(value) if value is not None else None

    return ProductListingModel(
        id=listing.id,
        product_id=listing.product_id,
        marketplace_url=listing.marketplace_url,
        title=listing.title,
        asking_price=float(listing.asking_price),
        state=listing.state.value,
        state_changed_at=listing.state_changed_at,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        found_at=listing.found_at,
        messaged_at=listing.messaged_at,
        negotiating_at=listing.negotiating_at,
        purchased_at=listing.purchased_at,
        received_at=listing.received_at,
        listed_at=listing.listed_at,
        sold_at=listing.sold_at,
        cancelled_at=listing.cancelled_at,
        scraper_job_id=listing.scraper_job_id,
        brand=listing.brand,
        model=listing.model,
        confidence_score=float(listing.confidence_score),
        estimated_profit=float(listing.estimated_profit),
        negotiated_price=_flt(listing.negotiated_price),
        seller_messenger_id=listing.seller_messenger_id,
        conversation_thread_id=listing.conversation_thread_id,
        ebay_listing_id=listing.ebay_listing_id,
        ebay_asking_price=_flt(listing.ebay_asking_price),
        ebay_sold_price=_flt(listing.ebay_sold_price),
        purchase_price=_flt(listing.purchase_price),
        shipping_cost=_flt(listing.shipping_cost),
        ebay_fees=_flt(listing.ebay_fees),
        final_profit=_flt(listing.final_profit),
        error_message=listing.error_message,
        error_occurred_at=listing.error_occurred_at,
    )


class SqlAlchemyListingRepository:
    """SQLAlchemy implementation for listing persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, listing: ProductListing) -> None:
        model = await self._session.get(ProductListingModel, listing.id)
        if model is None:
            self._session.add(_to_model(listing))
        else:
            model.state = listing.state.value
            model.state_changed_at = listing.state_changed_at
            model.updated_at = listing.updated_at
            model.messaged_at = listing.messaged_at
            model.negotiating_at = listing.negotiating_at
            model.purchased_at = listing.purchased_at
            model.received_at = listing.received_at
            model.listed_at = listing.listed_at
            model.sold_at = listing.sold_at
            model.cancelled_at = listing.cancelled_at
            model.negotiated_price = float(listing.negotiated_price) if listing.negotiated_price else None
            model.seller_messenger_id = listing.seller_messenger_id
            model.conversation_thread_id = listing.conversation_thread_id
            model.ebay_listing_id = listing.ebay_listing_id
            model.ebay_asking_price = float(listing.ebay_asking_price) if listing.ebay_asking_price else None
            model.ebay_sold_price = float(listing.ebay_sold_price) if listing.ebay_sold_price else None
            model.purchase_price = float(listing.purchase_price) if listing.purchase_price else None
            model.shipping_cost = float(listing.shipping_cost) if listing.shipping_cost else None
            model.ebay_fees = float(listing.ebay_fees) if listing.ebay_fees else None
            model.final_profit = float(listing.final_profit) if listing.final_profit else None
            model.error_message = listing.error_message
            model.error_occurred_at = listing.error_occurred_at
        await self._session.flush()

    async def get_by_id(self, listing_id: UUID) -> ProductListing | None:
        model = await self._session.get(ProductListingModel, listing_id)
        return _to_domain(model) if model is not None else None

    async def list_all(
        self,
        *,
        state: ListingState | None = None,
        brand: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ProductListing], int]:
        query = select(ProductListingModel)
        count_query = select(func.count()).select_from(ProductListingModel)

        if state is not None:
            query = query.where(ProductListingModel.state == state.value)
            count_query = count_query.where(ProductListingModel.state == state.value)
        if brand is not None:
            query = query.where(ProductListingModel.brand.ilike(f"%{brand}%"))
            count_query = count_query.where(ProductListingModel.brand.ilike(f"%{brand}%"))

        query = query.order_by(ProductListingModel.created_at.desc()).limit(limit).offset(offset)

        result = await self._session.execute(query)
        models = result.scalars().all()

        count_result = await self._session.execute(count_query)
        total = count_result.scalar_one()

        return [_to_domain(m) for m in models], total
