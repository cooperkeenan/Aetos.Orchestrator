"""
Integration tests for the API layer.

These tests use FastAPI's TestClient with mocked use cases and repositories
so they test HTTP contract + wiring without requiring a real database.
"""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.dependencies import (
    get_create_listings_use_case,
    get_listing_repo,
    get_history_repo,
    get_transition_state_use_case,
    get_listing_history_use_case,
    get_event_publisher,
)
from src.application.use_cases.create_listings_from_scraper import (
    CreateListingsFromScraperOutput,
)
from src.application.use_cases.transition_listing_state import (
    TransitionListingStateOutput,
    ListingNotFoundError,
)
from src.application.use_cases.get_listing_history import GetListingHistoryOutput
from src.application.interfaces.state_history_repository import StateHistoryRecord
from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState
from src.domain.state_machine.lifecycle_state_machine import InvalidStateTransitionError
from src.infrastructure.messaging.noop_publisher import NoOpEventPublisher

from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_listing(state: ListingState = ListingState.FOUND) -> ProductListing:
    listing = ProductListing.create_from_scraper_match(
        product_id=230,
        marketplace_url="https://fb.com/item/1",
        title="Sony A6400",
        asking_price=Decimal("400.00"),
        scraper_job_id=uuid4(),
        brand="Sony",
        model="a6400",
        confidence_score=Decimal("95.00"),
        estimated_profit=Decimal("100.00"),
    )
    listing.collect_events()  # clear
    return listing


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides[get_event_publisher] = lambda: NoOpEventPublisher()
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestWebhookScraperJobComplete:
    def test_accepts_valid_payload(self, client: TestClient) -> None:
        listing_id = uuid4()
        mock_use_case = MagicMock()
        mock_use_case.execute = AsyncMock(
            return_value=CreateListingsFromScraperOutput(
                created_listing_ids=[listing_id],
                skipped_count=0,
            )
        )
        app.dependency_overrides[get_create_listings_use_case] = lambda: mock_use_case

        response = client.post(
            "/webhooks/scraper/job-complete",
            json={
                "job_id": str(uuid4()),
                "brand": "Sony",
                "matches": [
                    {
                        "listing": {
                            "url": "https://fb.com/item/1",
                            "title": "Sony A6400",
                            "price": 400.0,
                        },
                        "product": {"id": 230, "brand": "Sony", "model": "a6400"},
                        "confidence": 95.0,
                        "potential_profit": 100.0,
                    }
                ],
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["accepted"] is True
        assert data["created_listings"] == 1
        assert data["skipped"] == 0

    def test_rejects_invalid_payload(self, client: TestClient) -> None:
        response = client.post("/webhooks/scraper/job-complete", json={"bad": "data"})
        assert response.status_code == 422


class TestAdminListings:
    def test_list_listings_returns_paginated_response(self, client: TestClient) -> None:
        listing = _make_listing()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=listing)
        mock_repo.list_all = AsyncMock(return_value=([listing], 1))
        app.dependency_overrides[get_listing_repo] = lambda: mock_repo

        response = client.get("/admin/listings")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["listings"]) == 1
        assert data["listings"][0]["state"] == "FOUND"

    def test_get_listing_returns_404_if_not_found(self, client: TestClient) -> None:
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        app.dependency_overrides[get_listing_repo] = lambda: mock_repo

        response = client.get(f"/admin/listings/{uuid4()}")
        assert response.status_code == 404

    def test_get_listing_returns_200_if_found(self, client: TestClient) -> None:
        listing = _make_listing()
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=listing)
        app.dependency_overrides[get_listing_repo] = lambda: mock_repo

        response = client.get(f"/admin/listings/{listing.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(listing.id)

    def test_transition_returns_422_for_invalid_transition(self, client: TestClient) -> None:
        mock_use_case = MagicMock()
        mock_use_case.execute = AsyncMock(
            side_effect=InvalidStateTransitionError(ListingState.SOLD, ListingState.FOUND)
        )
        app.dependency_overrides[get_transition_state_use_case] = lambda: mock_use_case

        response = client.post(
            f"/admin/listings/{uuid4()}/transition",
            json={"to_state": "FOUND"},
        )
        assert response.status_code == 422

    def test_transition_returns_404_if_listing_not_found(self, client: TestClient) -> None:
        listing_id = uuid4()
        mock_use_case = MagicMock()
        mock_use_case.execute = AsyncMock(side_effect=ListingNotFoundError(listing_id))
        app.dependency_overrides[get_transition_state_use_case] = lambda: mock_use_case

        response = client.post(
            f"/admin/listings/{listing_id}/transition",
            json={"to_state": "CANCELLED"},
        )
        assert response.status_code == 404

    def test_get_history_returns_history(self, client: TestClient) -> None:
        listing_id = uuid4()
        record = StateHistoryRecord(
            id=uuid4(),
            listing_id=listing_id,
            from_state=None,
            to_state=ListingState.FOUND,
            transitioned_at=_utcnow(),
            triggered_by="scraper_webhook",
            metadata={},
        )
        mock_use_case = MagicMock()
        mock_use_case.execute = AsyncMock(
            return_value=GetListingHistoryOutput(listing_id=listing_id, history=[record])
        )
        app.dependency_overrides[get_listing_history_use_case] = lambda: mock_use_case

        response = client.get(f"/admin/listings/{listing_id}/history")
        assert response.status_code == 200
        data = response.json()
        assert data["listing_id"] == str(listing_id)
        assert len(data["history"]) == 1
        assert data["history"][0]["to_state"] == "FOUND"
        assert data["history"][0]["from_state"] is None
