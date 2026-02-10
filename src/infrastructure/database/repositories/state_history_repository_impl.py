import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.state_history_repository import (
    StateHistoryRecord,
    StateHistoryRepository,
)
from src.domain.enums.listing_state import ListingState
from src.infrastructure.database.models import ProductStateHistoryModel


class SqlAlchemyStateHistoryRepository(StateHistoryRepository):
    """SQLAlchemy-backed implementation of StateHistoryRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        *,
        listing_id: UUID,
        from_state: ListingState | None,
        to_state: ListingState,
        triggered_by: str,
        metadata: dict | None = None,  # type: ignore[type-arg]
    ) -> StateHistoryRecord:
        record_id = uuid.uuid4()
        model = ProductStateHistoryModel(
            id=record_id,
            listing_id=listing_id,
            from_state=from_state.value if from_state else None,
            to_state=to_state.value,
            triggered_by=triggered_by,
            metadata_=metadata or {},
        )
        self._session.add(model)
        await self._session.flush()

        return StateHistoryRecord(
            id=record_id,
            listing_id=listing_id,
            from_state=from_state,
            to_state=to_state,
            transitioned_at=model.transitioned_at,
            triggered_by=triggered_by,
            metadata=metadata or {},
        )

    async def get_history_for_listing(self, listing_id: UUID) -> list[StateHistoryRecord]:
        result = await self._session.execute(
            select(ProductStateHistoryModel)
            .where(ProductStateHistoryModel.listing_id == listing_id)
            .order_by(ProductStateHistoryModel.transitioned_at.asc())
        )
        models = result.scalars().all()

        return [
            StateHistoryRecord(
                id=m.id,
                listing_id=m.listing_id,
                from_state=ListingState(m.from_state) if m.from_state else None,
                to_state=ListingState(m.to_state),
                transitioned_at=m.transitioned_at,
                triggered_by=m.triggered_by,
                metadata=m.metadata_,
            )
            for m in models
        ]
