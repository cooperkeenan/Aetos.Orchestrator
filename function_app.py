"""Azure Functions entry point for Aetos Orchestrator."""
import asyncio
import json
import logging
from typing import Any
from uuid import UUID

import azure.functions as func
from sqlalchemy import text
from decimal import Decimal

from src.api.schemas.scraper_webhook import ScraperJobCompleteWebhookPayload
from src.config import settings
from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState
from src.infrastructure.azure.container_manager import AzureContainerManager
from src.infrastructure.database.connection import AsyncSessionLocal
from src.infrastructure.database.repositories.listing_repository import (
    SqlAlchemyListingRepository,
)
from src.infrastructure.database.repositories.state_history_repository import (
    SqlAlchemyStateHistoryRepository,
)
from src.infrastructure.database.repositories.search_rotation_repository import (
    SearchRotationRepository,
)
from src.infrastructure.external_services.scraper_client import ScraperClient
from src.infrastructure.external_services.scraper_coordinator import ScraperCoordinator
from src.infrastructure.messaging.rabbitmq_publisher import RabbitMQPublisher

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Initialize container manager
container_manager = AzureContainerManager()


async def poll_scraper_and_process(job_id: str, brand: str, search_term: str) -> None:
    """
    Poll scraper job status every 3 minutes until complete.
    When done, process results and stop container.
    """
    coordinator = ScraperCoordinator(ScraperClient())
    max_polls = 40  # 40 * 3 min = 2 hours max
    poll_count = 0
    
    logging.info(f"Starting polling for job {job_id}")
    
    while poll_count < max_polls:
        try:
            # Wait 3 minutes before checking (first check after 3 min)
            await asyncio.sleep(180)  # 3 minutes
            poll_count += 1
            
            logging.info(f"Polling job {job_id} (attempt {poll_count}/{max_polls})")
            status_data = await coordinator.get_job_status(job_id)
            
            status = status_data.get("status")
            logging.info(f"Job {job_id} status: {status}")
            
            if status == "completed":
                logging.info(f"Job {job_id} completed! Processing results...")
                
                # Extract matches from result
                result = status_data.get("result", {})
                matches = result.get("matches", [])
                
                logging.info(f"Found {len(matches)} matches for {brand}")
                
                if matches:
                    # Process matches - create lifecycle records
                    created_ids = await process_scraper_matches(job_id, brand, matches)
                    
                    # TODO: Send to Chatterbot (Phase 2)
                    # For now, just log the matches
                    logging.info(f"=== MATCHES TO SEND TO CHATTERBOT ===")
                    for match in matches:
                        listing_info = match.get("listing", {})
                        product_info = match.get("product", {})
                        logging.info(
                            f"  - {product_info.get('brand')} {product_info.get('model')}: "
                            f"£{listing_info.get('price')} at {listing_info.get('url')}"
                        )
                    logging.info(f"=== END MATCHES (created {len(created_ids)} lifecycle records) ===")
                else:
                    logging.info(f"No matches found for {brand}")
                
                # Stop the scraper container to save costs
                try:
                    logging.info(f"Stopping scraper container: {settings.azure_scraper_container}")
                    await container_manager.stop_container(settings.azure_scraper_container)
                    logging.info("Scraper container stopped successfully")
                except Exception as exc:
                    logging.error(f"Failed to stop scraper container: {exc}")
                
                return  # Job complete, exit polling
                
            elif status == "failed" or status == "error":
                logging.error(f"Job {job_id} failed: {status_data.get('error', 'Unknown error')}")
                
                # Stop container even on failure
                try:
                    await container_manager.stop_container(settings.azure_scraper_container)
                except Exception:
                    pass
                
                return  # Exit polling
                
            elif status == "pending" or status == "running":
                logging.info(f"Job {job_id} still {status}, will check again in 3 minutes...")
                continue
            else:
                logging.warning(f"Unknown status '{status}' for job {job_id}")
                continue
                
        except Exception as exc:
            logging.error(f"Error polling job {job_id}: {exc}")
            poll_count += 1
            continue
    
    # Max polls reached
    logging.warning(f"Job {job_id} polling timed out after {max_polls * 3} minutes")
    try:
        await container_manager.stop_container(settings.azure_scraper_container)
    except Exception:
        pass


async def process_scraper_matches(job_id: str, brand: str, matches: list) -> list[UUID]:
    """
    Process scraper matches and create lifecycle records.
    Returns list of created listing IDs.
    """
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
                    triggered_by="scraper_polling",
                    metadata={"job_id": job_id, "brand": brand},
                )
                
                await publisher.publish_many(listing.collect_events())
                created_ids.append(listing.id)
                
                logging.info(f"Created lifecycle record {listing.id} for {product_data.get('model')}")
                
            except Exception as exc:
                logging.exception(f"Failed to process match: {exc}")
                continue
        
        await session.commit()
    
    return created_ids


# ============================================================================
# Health Check
# ============================================================================

@app.route(route="health", methods=["GET"])
async def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
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

    overall = "healthy" if db_status == "connected" and rabbitmq_status == "connected" else "degraded"

    return func.HttpResponse(
        json.dumps({
            "status": overall,
            "database": db_status,
            "rabbitmq": rabbitmq_status,
        }),
        mimetype="application/json",
    )


# ============================================================================
# Admin API - Trigger scrape
# ============================================================================

@app.route(route="admin/scrape/trigger", methods=["POST"])
async def trigger_scrape(req: func.HttpRequest) -> func.HttpResponse:
    """
    Manually trigger a scrape job.
    
    Request body (optional):
    {
        "brand": "Sony",
        "search_term": "Sony A7"
    }
    
    If no body provided, uses search rotation logic.
    Starts background polling to check job status every 3 minutes.
    """
    try:
        payload = req.get_json() if req.get_body() else {}
        brand = payload.get("brand")
        search_term = payload.get("search_term")
    except (ValueError, TypeError):
        payload = {}
        brand = None
        search_term = None

    # If no brand specified, use rotation logic
    if not brand:
        logging.info("No brand specified, using search rotation")
        rotation_repo = SearchRotationRepository(settings.products_database_url)
        next_search = await rotation_repo.get_next_search()

        if not next_search:
            return func.HttpResponse(
                json.dumps({"error": "No searches configured in rotation table"}),
                mimetype="application/json",
                status_code=500,
            )

        brand, search_term = next_search
        logging.info(f"Using rotation: {brand} - '{search_term}'")
    else:
        search_term = search_term or brand
        logging.info(f"Using provided: {brand} - '{search_term}'")

    # START ScraperV2 container
    try:
        logging.info(f"Starting scraper container: {settings.azure_scraper_container}")
        await container_manager.start_container(settings.azure_scraper_container)
        
        logging.info("Waiting 30 seconds for scraper to be ready...")
        await asyncio.sleep(30)
        
    except Exception as exc:
        logging.error(f"Failed to start scraper container: {exc}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to start scraper container: {exc}"}),
            mimetype="application/json",
            status_code=500,
        )

    # Trigger scrape
    coordinator = ScraperCoordinator(ScraperClient())
    try:
        result = await coordinator.trigger_scrape(brand=brand, search=search_term)
        job_id = str(result.job_id)
        
        logging.info(f"Scrape job started: {job_id}")
        
        # Start background polling task (fire and forget)
        asyncio.create_task(poll_scraper_and_process(job_id, brand, search_term))
        
        return func.HttpResponse(
            json.dumps({
                "job_id": job_id,
                "status": result.status,
                "brand": brand,
                "search_term": search_term,
                "source": "manual" if payload.get("brand") else "rotation",
                "message": "Scrape started. Results will be processed automatically when complete."
            }),
            mimetype="application/json",
        )
    except Exception as exc:
        logging.error(f"Failed to trigger scrape: {exc}")
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="admin/scrape/{job_id}/status", methods=["GET"])
async def get_scrape_status(req: func.HttpRequest) -> func.HttpResponse:
    """Get the status of a scrape job from ScraperV2."""
    job_id = req.route_params.get("job_id")
    
    if not job_id:
        return func.HttpResponse("Missing job_id", status_code=400)
    
    coordinator = ScraperCoordinator(ScraperClient())
    try:
        status = await coordinator.get_job_status(job_id)
        return func.HttpResponse(
            json.dumps(status),
            mimetype="application/json",
        )
    except Exception as exc:
        logging.error(f"Failed to get job status: {exc}")
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
    """
    Runs 3 times per day: 9am, 2pm, 9pm UTC.
    Uses search rotation to cycle through brands.
    Starts background polling for results.
    """
    logging.info("Starting scheduled scrape with rotation")

    rotation_repo = SearchRotationRepository(settings.products_database_url)
    next_search = await rotation_repo.get_next_search()

    if not next_search:
        logging.warning("No searches configured in rotation table")
        return

    brand, search_term = next_search
    logging.info(f"Scheduled scrape: {brand} - '{search_term}'")

    try:
        # Start ScraperV2 container
        await container_manager.start_container(settings.azure_scraper_container)
        await asyncio.sleep(30)

        # Trigger scrape
        coordinator = ScraperCoordinator(ScraperClient())
        result = await coordinator.trigger_scrape(brand=brand, search=search_term)
        job_id = str(result.job_id)
        
        logging.info(f"Scheduled scrape job started: {job_id}")
        
        # Start background polling (fire and forget)
        asyncio.create_task(poll_scraper_and_process(job_id, brand, search_term))

    except Exception as exc:
        logging.error(f"Failed to start scheduled scrape for {brand}: {exc}")

    logging.info("Scheduled scrape trigger completed (polling continues in background)")


# ============================================================================
# Admin API - List/Get Listings
# ============================================================================

@app.route(route="admin/listings", methods=["GET"])
async def list_listings(req: func.HttpRequest) -> func.HttpResponse:
    """List all product listings with optional filtering."""
    state_param = req.params.get("state")
    brand = req.params.get("brand")
    limit = int(req.params.get("limit", 50))
    offset = int(req.params.get("offset", 0))

    state = ListingState(state_param) if state_param else None

    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyListingRepository(session)
        listings, total = await repo.list_all(state=state, brand=brand, limit=limit, offset=offset)

        return func.HttpResponse(
            json.dumps({
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
            }),
            mimetype="application/json",
        )


@app.route(route="admin/listings/{listing_id}", methods=["GET"])
async def get_listing(req: func.HttpRequest) -> func.HttpResponse:
    """Get a specific listing by ID."""
    listing_id = req.route_params.get("listing_id")

    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyListingRepository(session)
        listing = await repo.get_by_id(UUID(listing_id))

        if not listing:
            return func.HttpResponse("Listing not found", status_code=404)

        return func.HttpResponse(
            json.dumps({
                "id": str(listing.id),
                "product_id": listing.product_id,
                "brand": listing.brand,
                "model": listing.model,
                "state": listing.state.value,
                "marketplace_url": listing.marketplace_url,
                "asking_price": float(listing.asking_price),
                "estimated_profit": float(listing.estimated_profit),
                "created_at": listing.created_at.isoformat(),
            }),
            mimetype="application/json",
        )
