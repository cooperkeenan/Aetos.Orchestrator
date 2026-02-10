"""Unit tests for application use cases — all dependencies are mocked."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.use_cases.create_listings_from_scraper import (
    CreateListingsFromScraper,
    CreateListingsFromScraperInput,
    ScraperMatch,
)
from src.application.use_cases.transition_listing_state import (
    ListingNotFoundError,
    TransitionListingState,
    TransitionListingStateInput,
)
from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState
from src.domain.state_machine.lifecycle_state_machine import InvalidStateTransitionError


def _make_repo(listing: ProductListing | None = None) -> MagicMock:
    repo = MagicMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=listing)
    return repo


def _make_history_repo() -> MagicMock:
    repo = MagicMock()
    repo.save = AsyncMock()
    return repo


def _make_publisher() -> MagicMock:
    pub = MagicMock()
    pub.publish_many = AsyncMock()
    return pub


def _make_listing() -> ProductListing:
    return ProductListing.create_from_scraper_match(
        product_id=230,
        marketplace_url="https://fb.com/item/1",
        title="Sony A6400",
        asking_price=Decimal("400"),
        scraper_job_id=uuid4(),
        brand="Sony",
        model="a6400",
        confidence_score=Decimal("95"),
        estimated_profit=Decimal("100"),
    )


class TestCreateListingsFromScraper:
    @pytest.mark.asyncio
    async def test_creates_listings_for_all_matches(self) -> None:
        job_id = uuid4()
        listing_repo = _make_repo()
        history_repo = _make_history_repo()
        publisher = _make_publisher()
        use_case = CreateListingsFromScraper(listing_repo, history_repo, publisher)

        result = await use_case.execute(
            CreateListingsFromScraperInput(
                job_id=job_id,
                brand="Sony",
                matches=[
                    ScraperMatch(
                        url="https://fb.com/1",
                        title="Sony A6400",
                        price=400.0,
                        product_id=230,
                        brand="Sony",
                        model="a6400",
                        confidence=95.0,
                        potential_profit=100.0,
                    ),
                    ScraperMatch(
                        url="https://fb.com/2",
                        title="Sony A7III",
                        price=800.0,
                        product_id=231,
                        brand="Sony",
                        model="a7iii",
                        confidence=90.0,
                        potential_profit=150.0,
                    ),
                ],
            )
        )

        assert len(result.created_listing_ids) == 2
        assert result.skipped_count == 0
        assert listing_repo.save.call_count == 2
        assert history_repo.save.call_count == 2
        assert publisher.publish_many.call_count == 2

    @pytest.mark.asyncio
    async def test_skips_and_counts_failed_matches(self) -> None:
        job_id = uuid4()
        listing_repo = _make_repo()
        listing_repo.save = AsyncMock(side_effect=Exception("DB error"))
        history_repo = _make_history_repo()
        publisher = _make_publisher()
        use_case = CreateListingsFromScraper(listing_repo, history_repo, publisher)

        result = await use_case.execute(
            CreateListingsFromScraperInput(
                job_id=job_id,
                brand="Sony",
                matches=[
                    ScraperMatch(
                        url="https://fb.com/1",
                        title="Sony A6400",
                        price=400.0,
                        product_id=230,
                        brand="Sony",
                        model="a6400",
                        confidence=95.0,
                        potential_profit=100.0,
                    )
                ],
            )
        )

        assert len(result.created_listing_ids) == 0
        assert result.skipped_count == 1

    @pytest.mark.asyncio
    async def test_handles_empty_matches(self) -> None:
        use_case = CreateListingsFromScraper(
            _make_repo(), _make_history_repo(), _make_publisher()
        )
        result = await use_case.execute(
            CreateListingsFromScraperInput(job_id=uuid4(), brand="Sony", matches=[])
        )
        assert result.created_listing_ids == []
        assert result.skipped_count == 0


class TestTransitionListingState:
    @pytest.mark.asyncio
    async def test_transitions_listing_successfully(self) -> None:
        listing = _make_listing()
        listing.collect_events()  # clear initial events
        repo = _make_repo(listing)
        history_repo = _make_history_repo()
        publisher = _make_publisher()
        use_case = TransitionListingState(repo, history_repo, publisher)

        result = await use_case.execute(
            TransitionListingStateInput(
                listing_id=listing.id,
                to_state=ListingState.MESSAGING,
                triggered_by="test",
            )
        )

        assert result.from_state == ListingState.FOUND
        assert result.to_state == ListingState.MESSAGING
        repo.save.assert_awaited_once()
        history_repo.save.assert_awaited_once()
        publisher.publish_many.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_raises_listing_not_found(self) -> None:
        repo = _make_repo(None)
        use_case = TransitionListingState(repo, _make_history_repo(), _make_publisher())

        with pytest.raises(ListingNotFoundError):
            await use_case.execute(
                TransitionListingStateInput(
                    listing_id=uuid4(),
                    to_state=ListingState.MESSAGING,
                    triggered_by="test",
                )
            )

    @pytest.mark.asyncio
    async def test_raises_invalid_transition(self) -> None:
        listing = _make_listing()
        repo = _make_repo(listing)
        use_case = TransitionListingState(repo, _make_history_repo(), _make_publisher())

        with pytest.raises(InvalidStateTransitionError):
            await use_case.execute(
                TransitionListingStateInput(
                    listing_id=listing.id,
                    to_state=ListingState.SOLD,
                    triggered_by="test",
                )
            )
