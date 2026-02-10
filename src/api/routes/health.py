from fastapi import APIRouter
from sqlalchemy import text

from src.infrastructure.database.connection import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:  # type: ignore[type-arg]
    """Liveness + dependency health check."""
    db_status = "connected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    # RabbitMQ: a lightweight connection attempt
    rabbitmq_status = "connected"
    try:
        import pika
        from src.config import settings

        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        connection.close()
    except Exception as exc:
        rabbitmq_status = f"error: {exc}"

    overall = "healthy" if db_status == "connected" and rabbitmq_status == "connected" else "degraded"

    return {
        "status": overall,
        "database": db_status,
        "rabbitmq": rabbitmq_status,
    }
