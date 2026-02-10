"""Unit tests for the ProductListing domain entity."""
from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.entities.product_listing import ProductListing
from src.domain.enums.listing_state import ListingState
from src.domain.events.domain_events import ListingCreatedEvent, ListingStateChangedEvent
from src.domain.state_machine.lifecycle_state_machine import InvalidStateTransitionError


def _make_listing(**overrides) -> ProductListing:  # type: ignore[no-untyped-def]
    defaults = dict(
        product_id=230,
        marketplace_url="https://facebook.com/marketplace/item/123",
        title="Sony A6400 mirrorless camera",
        asking_price=Decimal("400.00"),
        scraper_job_id=uuid4(),
        brand="Sony",
        model="a6400",
        confidence_score=Decimal("95.00"),
        estimated_profit=Decimal("100.00"),
    )
    defaults.update(overrides)
    return ProductListing.create_from_scraper_match(**defaults)


class TestCreateFromScraperMatch:
    def test_creates_in_found_state(self) -> None:
        listing = _make_listing()
        assert listing.state == ListingState.FOUND

    def test_emits_listing_created_event(self) -> None:
        listing = _make_listing()
        events = listing.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ListingCreatedEvent)

    def test_events_cleared_after_collect(self) -> None:
        listing = _make_listing()
        listing.collect_events()
        assert listing.collect_events() == []

    def test_listing_fields_set_correctly(self) -> None:
        job_id = uuid4()
        listing = _make_listing(product_id=230, brand="Sony", model="a6400", scraper_job_id=job_id)
        assert listing.product_id == 230
        assert listing.brand == "Sony"
        assert listing.model == "a6400"
        assert listing.scraper_job_id == job_id


class TestStateTransitions:
    def test_valid_transition_changes_state(self) -> None:
        listing = _make_listing()
        listing.collect_events()  # clear creation event
        listing.transition_to(ListingState.MESSAGING, triggered_by="test")
        assert listing.state == ListingState.MESSAGING

    def test_transition_emits_state_changed_event(self) -> None:
        listing = _make_listing()
        listing.collect_events()
        listing.transition_to(ListingState.MESSAGING, triggered_by="test")
        events = listing.collect_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ListingStateChangedEvent)
        assert event.from_state == ListingState.FOUND
        assert event.to_state == ListingState.MESSAGING
        assert event.triggered_by == "test"

    def test_transition_sets_lifecycle_timestamp(self) -> None:
        listing = _make_listing()
        assert listing.messaged_at is None
        listing.transition_to(ListingState.MESSAGING, triggered_by="test")
        assert listing.messaged_at is not None

    def test_invalid_transition_raises(self) -> None:
        listing = _make_listing()
        with pytest.raises(InvalidStateTransitionError):
            listing.transition_to(ListingState.SOLD, triggered_by="test")

    def test_cannot_transition_from_cancelled(self) -> None:
        listing = _make_listing()
        listing.transition_to(ListingState.CANCELLED, triggered_by="test")
        with pytest.raises(InvalidStateTransitionError):
            listing.transition_to(ListingState.MESSAGING, triggered_by="test")

    def test_full_happy_path(self) -> None:
        listing = _make_listing()
        listing.transition_to(ListingState.MESSAGING, "test")
        listing.transition_to(ListingState.NEGOTIATING, "test")
        listing.transition_to(ListingState.PURCHASED, "test")
        listing.transition_to(ListingState.RECEIVED, "test")
        listing.transition_to(ListingState.LISTED, "test")
        listing.transition_to(ListingState.SOLD, "test")
        assert listing.state == ListingState.SOLD
        assert listing.sold_at is not None


class TestRecordError:
    def test_stores_error_message(self) -> None:
        listing = _make_listing()
        listing.record_error("Something went wrong")
        assert listing.error_message == "Something went wrong"
        assert listing.error_occurred_at is not None
