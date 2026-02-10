from dataclasses import dataclass

from src.domain.enums.listing_state import ListingState


# Mapping of valid transitions: from_state -> set of allowed to_states
VALID_TRANSITIONS: dict[ListingState, frozenset[ListingState]] = {
    ListingState.FOUND: frozenset({ListingState.MESSAGING, ListingState.CANCELLED}),
    ListingState.MESSAGING: frozenset({ListingState.NEGOTIATING, ListingState.CANCELLED}),
    ListingState.NEGOTIATING: frozenset({ListingState.PURCHASED, ListingState.CANCELLED}),
    ListingState.PURCHASED: frozenset({ListingState.RECEIVED, ListingState.CANCELLED}),
    ListingState.RECEIVED: frozenset({ListingState.LISTED}),
    ListingState.LISTED: frozenset({ListingState.SOLD}),
    # Terminal states — no valid outgoing transitions
    ListingState.SOLD: frozenset(),
    ListingState.CANCELLED: frozenset(),
}


@dataclass(frozen=True)
class TransitionResult:
    success: bool
    from_state: ListingState
    to_state: ListingState
    error_message: str | None = None


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: ListingState, to_state: ListingState) -> None:
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition from {from_state.value} to {to_state.value}. "
            f"Allowed transitions: {[s.value for s in VALID_TRANSITIONS.get(from_state, frozenset())]}"
        )


class LifecycleStateMachine:
    """
    Validates and enforces state transitions for product listing lifecycle.

    Stateless by design — call validate() or transition() with explicit states.
    """

    def can_transition(self, from_state: ListingState, to_state: ListingState) -> bool:
        """Return True if transitioning from_state → to_state is permitted."""
        if from_state.is_terminal:
            return False
        return to_state in VALID_TRANSITIONS.get(from_state, frozenset())

    def validate_transition(self, from_state: ListingState, to_state: ListingState) -> None:
        """Raise InvalidStateTransitionError if the transition is not permitted."""
        if not self.can_transition(from_state, to_state):
            raise InvalidStateTransitionError(from_state, to_state)

    def get_allowed_transitions(self, from_state: ListingState) -> frozenset[ListingState]:
        """Return the set of states reachable from from_state."""
        return VALID_TRANSITIONS.get(from_state, frozenset())
