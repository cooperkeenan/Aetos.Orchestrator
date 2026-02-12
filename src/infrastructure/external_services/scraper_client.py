"""HTTP client for ScraperV2 service."""

import httpx
import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


class ScraperClientError(Exception):
    pass


class ScraperClient:
    """Thin HTTP wrapper around the ScraperV2 REST API."""

    def __init__(
        self,
        base_url: str = settings.scraper_api_url,
        api_key: str = settings.scraper_api_key,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }

    async def start_scrape(self, brand: str, search: str | None = None) -> dict:  # type: ignore[type-arg]
        """
        POST /scrape → {"job_id": "...", "status": "pending", "message": "..."}
        """
        payload = {
            "brand": brand,
            "search": search or brand,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/scrape",
                    json=payload,
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "scraper_job_started",
                    job_id=data.get("job_id"),
                    brand=brand,
                    status=data.get("status"),
                )
                return data
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "scraper_request_failed",
                    status_code=exc.response.status_code,
                    response=exc.response.text,
                )
                raise ScraperClientError(
                    f"ScraperV2 returned {exc.response.status_code}: {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:
                logger.error("scraper_connection_failed", error=str(exc))
                raise ScraperClientError(f"Failed to reach ScraperV2: {exc}") from exc

    async def get_job_status(self, job_id: str) -> dict:  # type: ignore[type-arg]
        """
        GET /scrape/{job_id} → {"job_id": "...", "status": "...", "result": {...}}
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self._base_url}/scrape/{job_id}",
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "scraper_job_status",
                    job_id=job_id,
                    status=data.get("status"),
                )
                return data
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "scraper_status_failed",
                    job_id=job_id,
                    status_code=exc.response.status_code,
                )
                raise ScraperClientError(
                    f"Failed to get job status: {exc.response.status_code}"
                ) from exc
            except httpx.RequestError as exc:
                raise ScraperClientError(f"Failed to reach ScraperV2: {exc}") from exc
