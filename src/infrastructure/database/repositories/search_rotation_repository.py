"""Repository for managing search rotation in Aetos-Products DB."""
import structlog
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.config import settings

logger = structlog.get_logger(__name__)


class SearchRotationRepository:
    """Manages search rotation logic for products."""

    def __init__(self, products_db_url: str):
        # Separate connection to Aetos-Products DB
        engine = create_async_engine(products_db_url, echo=False)
        self._session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def get_next_search(self) -> tuple[str, str | None] | None:
     
        async with self._session_maker() as session:
            # Find current search (last_searched=TRUE)
            current = await session.execute(
                text("""
                    SELECT id, brand, search_term 
                    FROM search_rotation 
                    WHERE last_searched = TRUE AND enabled = TRUE
                    LIMIT 1
                """)
            )
            current_row = current.fetchone()

            if current_row:
                # Mark current as false
                await session.execute(
                    text("UPDATE search_rotation SET last_searched = FALSE WHERE id = :id"),
                    {"id": current_row[0]},
                )

            # Find next search (wrap around if needed)
            next_search = await session.execute(
                text("""
                    SELECT id, brand, search_term 
                    FROM search_rotation 
                    WHERE enabled = TRUE 
                    AND (
                        (last_searched = FALSE AND id > :current_id)
                        OR :current_id IS NULL
                    )
                    ORDER BY id ASC 
                    LIMIT 1
                """),
                {"current_id": current_row[0] if current_row else None},
            )
            next_row = next_search.fetchone()

            # If no next found, wrap to first
            if not next_row:
                next_search = await session.execute(
                    text("""
                        SELECT id, brand, search_term 
                        FROM search_rotation 
                        WHERE enabled = TRUE 
                        ORDER BY id ASC 
                        LIMIT 1
                    """)
                )
                next_row = next_search.fetchone()

            if next_row:
                # Mark as current and update timestamp
                await session.execute(
                    text("""
                        UPDATE search_rotation 
                        SET last_searched = TRUE, 
                            last_searched_at = :now,
                            updated_at = :now
                        WHERE id = :id
                    """),
                    {"id": next_row[0], "now": datetime.now(timezone.utc)},
                )
                await session.commit()

                brand = next_row[1]
                search_term = next_row[2]  # Can be None

                logger.info("rotated_search", brand=brand, search_term=search_term)
                return (brand, search_term or brand)  # Default to brand if search_term is NULL

            return None