import structlog

from src.application.interfaces.service_coordinator import (
    ScraperCoordinatorInterface,
    ScraperJobResult,
)
from src.infrastructure.external_services.scraper_client import ScraperClient

logger = structlog.get_logger(__name__)


class ScraperCoordinator(ScraperCoordinatorInterface):
    """Drives ScraperV2 via its HTTP API."""

    def __init__(self, client: ScraperClient) -> None:
        self._client = client

    async def trigger_scrape(self, brand: str, search: str | None = None) -> ScraperJobResult:
        logger.info("triggering_scrape", brand=brand, search=search)
        result = await self._client.start_scrape(brand=brand, search=search or brand)
        return ScraperJobResult(job_id=result["job_id"], status=result["status"])
