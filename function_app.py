"""Azure Functions entry point for Aetos Orchestrator."""

import asyncio
import json
import logging
import os
from decimal import Decimal
from uuid import UUID

import azure.functions as func
from sqlalchemy import text

from src.api.schemas.scraper_webhook import ScraperJobCompleteWebhookPayload
from src.config import settings
from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState
from src.infrastructure.azure.container_manager import AzureContainerManager
from src.infrastructure.database.connection import AsyncSessionLocal
from src.infrastructure.database.repositories.listing_repository import (
    SqlAlchemyListingRepository,
)
from src.infrastructure.database.repositories.search_rotation_repository import (
    SearchRotationRepository,
)
from src.infrastructure.database.repositories.state_history_repository import (
    SqlAlchemyStateHistoryRepository,
)
from src.infrastructure.external_services.scraper_client import ScraperClient
from src.infrastructure.external_services.scraper_coordinator import ScraperCoordinator
from src.infrastructure.messaging.rabbitmq_publisher import RabbitMQPublisher
from src.infrastructure.messaging.telegram_service import TelegramService

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

_UNAUTHORIZED = func.HttpResponse(
    json.dumps({"error": "Unauthorized"}),
    mimetype="application/json",
    status_code=401,
)


def _authorized(req: func.HttpRequest) -> bool:
    return req.headers.get("x-api-key") == settings.scraper_api_key


def _get_container_manager() -> AzureContainerManager:
    return AzureContainerManager()


async def _process_scraper_matches(
    job_id: str, brand: str, matches: list
) -> list[UUID]:
    created_ids = []
    publisher = RabbitMQPublisher()

    async with AsyncSessionLocal() as session:
        listing_repo = SqlAlchemyListingRepository(session)
        history_repo = SqlAlchemyStateHistoryRepository(session)

        for match in matches:
            try:
                listing_data = match.get("listing", {})
                product_data = match.get("product", {})

                listing = ProductListing.create_from_scraper_match(
                    product_id=product_data.get("id"),
                    marketplace_url=listing_data.get("url"),
                    title=listing_data.get("title"),
                    asking_price=Decimal(str(listing_data.get("price", 0))),
                    scraper_job_id=UUID(job_id),
                    brand=product_data.get("brand"),
                    model=product_data.get("model"),
                    confidence_score=Decimal(str(match.get("confidence", 0))),
                    estimated_profit=Decimal(str(match.get("potential_profit", 0))),
                )

                await listing_repo.save(listing)
                await history_repo.save(
                    listing_id=listing.id,
                    from_state=None,
                    to_state=ListingState.FOUND,
                    triggered_by="scraper_webhook",
                    metadata={"job_id": job_id, "brand": brand},
                )
                await publisher.publish_many(listing.collect_events())
                created_ids.append(listing.id)
                logging.info(
                    f"Created lifecycle record {listing.id} for {product_data.get('model')}"
                )

            except Exception as exc:
                logging.exception(f"Failed to process match: {exc}")

        await session.commit()

    return created_ids


async def _stop_scraper_container() -> None:
    try:
        await _get_container_manager().stop_container(settings.azure_scraper_container)
        logging.info("Scraper container stopped")
    except Exception as exc:
        logging.error(f"Failed to stop scraper container: {exc}")


# ============================================================================
# Health Check
# ============================================================================


@app.route(route="health", methods=["GET"])
async def health(req: func.HttpRequest) -> func.HttpResponse:
    if not _authorized(req):
        return _UNAUTHORIZED
    db_status = "connected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    rabbitmq_status = "connected"
    try:
        import pika

        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        connection.close()
    except Exception as exc:
        rabbitmq_status = f"error: {exc}"

    overall = (
        "healthy"
        if db_status == "connected" and rabbitmq_status == "connected"
        else "degraded"
    )

    return func.HttpResponse(
        json.dumps(
            {"status": overall, "database": db_status, "rabbitmq": rabbitmq_status}
        ),
        mimetype="application/json",
    )


# ============================================================================
# Scraper Webhook — scraper pushes results here when a job completes
# ============================================================================


@app.route(route="webhooks/scraper/job-complete", methods=["POST"])
async def scraper_job_complete(req: func.HttpRequest) -> func.HttpResponse:
    if not _authorized(req):
        return _UNAUTHORIZED
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            mimetype="application/json",
            status_code=400,
        )

    job_id = body.get("job_id")
    brands = body.get("brands", [])
    matches = body.get("matches", [])
    brand = brands[0] if brands else "unknown"

    if not job_id:
        return func.HttpResponse(
            json.dumps({"error": "job_id is required"}),
            mimetype="application/json",
            status_code=400,
        )

    logging.info(
        f"Received scraper webhook: job={job_id}, matches={len(matches)}, brands={brands}"
    )

    created_ids = await _process_scraper_matches(job_id, brand, matches)

    telegram = TelegramService()
    await telegram.send_scrape_results(brands, matches)
    asyncio.create_task(_stop_scraper_container())

    return func.HttpResponse(
        json.dumps(
            {
                "accepted": True,
                "created_listings": len(created_ids),
                "skipped": len(matches) - len(created_ids),
            }
        ),
        mimetype="application/json",
        status_code=202,
    )


# ============================================================================
# Admin API - Trigger scrape
# ============================================================================


@app.route(route="manage/scrape/trigger", methods=["POST"])
async def trigger_scrape(req: func.HttpRequest) -> func.HttpResponse:
    if not _authorized(req):
        return _UNAUTHORIZED
    try:
        payload = req.get_json() if req.get_body() else {}
    except (ValueError, TypeError):
        payload = {}

    brands = payload.get("brands") or (
        [payload["brand"]] if payload.get("brand") else None
    )
    search_term = payload.get("search_term") or payload.get("search")
    source = "manual"

    if not brands:
        rotation_repo = SearchRotationRepository(settings.products_database_url)
        next_search = await rotation_repo.get_next_search()

        if not next_search:
            return func.HttpResponse(
                json.dumps({"error": "No searches configured in rotation table"}),
                mimetype="application/json",
                status_code=500,
            )

        rotation_brand, search_term = next_search
        brands = [rotation_brand]
        source = "rotation"
        logging.info(f"Using rotation: {rotation_brand} - '{search_term}'")
    else:
        search_term = search_term or brands[0]

    try:
        await _get_container_manager().start_container(settings.azure_scraper_container)
        logging.info("Waiting 30s for scraper to be ready...")
        await asyncio.sleep(30)
    except Exception as exc:
        return func.HttpResponse(
            json.dumps({"error": f"Failed to start scraper container: {exc}"}),
            mimetype="application/json",
            status_code=500,
        )

    coordinator = ScraperCoordinator(ScraperClient())
    try:
        result = await coordinator.trigger_scrape(brands=brands, search=search_term)
        return func.HttpResponse(
            json.dumps(
                {
                    "job_id": str(result.job_id),
                    "status": result.status,
                    "brands": brands,
                    "search_term": search_term,
                    "source": source,
                    "message": "Scrape started. Results will be delivered via webhook when complete.",
                }
            ),
            mimetype="application/json",
        )
    except Exception as exc:
        logging.error(f"Failed to trigger scrape: {exc}")
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


# ============================================================================
# Timer Trigger - Scheduled scraping
# ============================================================================


@app.schedule(schedule="0 0 9,14,21 * * *", arg_name="timer", run_on_startup=False)
async def scheduled_scrape(timer: func.TimerRequest) -> None:
    """Triggers a scrape 3x daily at 09:00, 14:00, and 21:00 UTC."""
    brands = ["Nikon", "Canon", "Sony"]
    search = "Camera"
    telegram = TelegramService()

    logging.info(f"Scheduled scrape starting — brands={brands}, search={search!r}")

    try:
        await _get_container_manager().start_container(settings.azure_scraper_container)
        logging.info("Scraper container started — waiting 30s for it to be ready")
        await asyncio.sleep(30)
    except Exception as exc:
        logging.error(f"Scheduled scrape failed to start container: {exc}")
        await telegram.send_error(
            "Scheduled scrape failed to start scraper container", exc
        )
        return

    try:
        coordinator = ScraperCoordinator(ScraperClient())
        result = await coordinator.trigger_scrape(brands=brands, search=search)
        logging.info(
            f"Scheduled scrape job started — "
            f"job_id={result.job_id}, brands={brands}, search={search!r}"
        )
    except Exception as exc:
        logging.error(f"Scheduled scrape failed to trigger job: {exc}")
        await telegram.send_error("Scheduled scrape failed to trigger scraper job", exc)


# ============================================================================
# Admin API - List/Get Listings
# ============================================================================


@app.route(route="manage/listings", methods=["GET"])
async def list_listings(req: func.HttpRequest) -> func.HttpResponse:
    if not _authorized(req):
        return _UNAUTHORIZED
    state_param = req.params.get("state")
    brand = req.params.get("brand")
    limit = int(req.params.get("limit", 50))
    offset = int(req.params.get("offset", 0))
    state = ListingState(state_param) if state_param else None

    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyListingRepository(session)
        listings, total = await repo.list_all(
            state=state, brand=brand, limit=limit, offset=offset
        )

        return func.HttpResponse(
            json.dumps(
                {
                    "listings": [
                        {
                            "id": str(l.id),
                            "product_id": l.product_id,
                            "brand": l.brand,
                            "model": l.model,
                            "state": l.state.value,
                            "asking_price": float(l.asking_price),
                            "estimated_profit": float(l.estimated_profit),
                            "marketplace_url": l.marketplace_url,
                        }
                        for l in listings
                    ],
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                }
            ),
            mimetype="application/json",
        )


@app.route(route="manage/listing/{listing_id}", methods=["GET"])
async def get_listing(req: func.HttpRequest) -> func.HttpResponse:
    if not _authorized(req):
        return _UNAUTHORIZED
    listing_id = req.route_params.get("listing_id")

    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyListingRepository(session)
        listing = await repo.get_by_id(UUID(listing_id))

        if not listing:
            return func.HttpResponse("Listing not found", status_code=404)

        return func.HttpResponse(
            json.dumps(
                {
                    "id": str(listing.id),
                    "product_id": listing.product_id,
                    "brand": listing.brand,
                    "model": listing.model,
                    "state": listing.state.value,
                    "marketplace_url": listing.marketplace_url,
                    "asking_price": float(listing.asking_price),
                    "estimated_profit": float(listing.estimated_profit),
                    "created_at": listing.created_at.isoformat(),
                }
            ),
            mimetype="application/json",
        )
