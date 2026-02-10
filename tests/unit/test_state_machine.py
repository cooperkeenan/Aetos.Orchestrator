"""Unit tests for the lifecycle state machine."""
import pytest

from src.domain.enums.listing_state import ListingState
from src.domain.state_machine.lifecycle_state_machine import (
    InvalidStateTransitionError,
    LifecycleStateMachine,
)


@pytest.fixture()
def sm() -> LifecycleStateMachine:
    return LifecycleStateMachine()


class TestValidTransitions:
    def test_found_to_messaging(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.FOUND, ListingState.MESSAGING) is True

    def test_found_to_cancelled(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.FOUND, ListingState.CANCELLED) is True

    def test_messaging_to_negotiating(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.MESSAGING, ListingState.NEGOTIATING) is True

    def test_messaging_to_cancelled(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.MESSAGING, ListingState.CANCELLED) is True

    def test_negotiating_to_purchased(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.NEGOTIATING, ListingState.PURCHASED) is True

    def test_negotiating_to_cancelled(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.NEGOTIATING, ListingState.CANCELLED) is True

    def test_purchased_to_received(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.PURCHASED, ListingState.RECEIVED) is True

    def test_purchased_to_cancelled(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.PURCHASED, ListingState.CANCELLED) is True

    def test_received_to_listed(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.RECEIVED, ListingState.LISTED) is True

    def test_listed_to_sold(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.LISTED, ListingState.SOLD) is True


class TestInvalidTransitions:
    def test_cannot_skip_states(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.FOUND, ListingState.PURCHASED) is False

    def test_cannot_go_backwards(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.MESSAGING, ListingState.FOUND) is False

    def test_sold_is_terminal(self, sm: LifecycleStateMachine) -> None:
        for state in ListingState:
            assert sm.can_transition(ListingState.SOLD, state) is False

    def test_cancelled_is_terminal(self, sm: LifecycleStateMachine) -> None:
        for state in ListingState:
            assert sm.can_transition(ListingState.CANCELLED, state) is False

    def test_found_to_sold_invalid(self, sm: LifecycleStateMachine) -> None:
        assert sm.can_transition(ListingState.FOUND, ListingState.SOLD) is False

    def test_listed_to_cancelled_invalid(self, sm: LifecycleStateMachine) -> None:
        # Once listed, can only go to SOLD — no longer can cancel
        assert sm.can_transition(ListingState.LISTED, ListingState.CANCELLED) is False


class TestValidateTransition:
    def test_valid_transition_does_not_raise(self, sm: LifecycleStateMachine) -> None:
        sm.validate_transition(ListingState.FOUND, ListingState.MESSAGING)  # no exception

    def test_invalid_transition_raises(self, sm: LifecycleStateMachine) -> None:
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            sm.validate_transition(ListingState.FOUND, ListingState.SOLD)
        assert "FOUND" in str(exc_info.value)
        assert "SOLD" in str(exc_info.value)

    def test_terminal_state_raises(self, sm: LifecycleStateMachine) -> None:
        with pytest.raises(InvalidStateTransitionError):
            sm.validate_transition(ListingState.SOLD, ListingState.FOUND)


class TestGetAllowedTransitions:
    def test_found_allowed(self, sm: LifecycleStateMachine) -> None:
        allowed = sm.get_allowed_transitions(ListingState.FOUND)
        assert ListingState.MESSAGING in allowed
        assert ListingState.CANCELLED in allowed
        assert ListingState.SOLD not in allowed

    def test_sold_has_no_transitions(self, sm: LifecycleStateMachine) -> None:
        assert sm.get_allowed_transitions(ListingState.SOLD) == frozenset()

    def test_cancelled_has_no_transitions(self, sm: LifecycleStateMachine) -> None:
        assert sm.get_allowed_transitions(ListingState.CANCELLED) == frozenset()
