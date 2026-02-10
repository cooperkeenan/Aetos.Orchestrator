"""HTTP client for ScraperV2 service."""
import structlog
import httpx

from src.config import settings

logger = structlog.get_logger(__name__)


class ScraperClientError(Exception):
    pass


class ScraperClient:
    """Thin HTTP wrapper around the ScraperV2 REST API."""

    def __init__(self, base_url: str = settings.scraper_api_url) -> None:
        self._base_url = base_url.rstrip("/")

    async def start_scrape(self, brand: str, search: str | None = None) -> dict:  # type: ignore[type-arg]
        """
        POST /scrape → {"job_id": "...", "status": "pending"}
        """
        payload: dict = {"brand": brand}  # type: ignore[type-arg]
        if search:
            payload["search"] = search

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(f"{self._base_url}/scrape", json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "scraper_job_started",
                    job_id=data.get("job_id"),
                    brand=brand,
                )
                return data
            except httpx.HTTPStatusError as exc:
                raise ScraperClientError(
                    f"ScraperV2 returned {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                raise ScraperClientError(f"Failed to reach ScraperV2: {exc}") from exc
