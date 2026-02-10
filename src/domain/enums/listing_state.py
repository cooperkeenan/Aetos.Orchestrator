from enum import Enum


class ListingState(str, Enum):
    """All possible states in the product lifecycle."""

    FOUND = "FOUND"
    MESSAGING = "MESSAGING"
    NEGOTIATING = "NEGOTIATING"
    PURCHASED = "PURCHASED"
    RECEIVED = "RECEIVED"
    LISTED = "LISTED"
    SOLD = "SOLD"
    CANCELLED = "CANCELLED"

    @property
    def is_terminal(self) -> bool:
        """Terminal states cannot be transitioned out of."""
        return self in (ListingState.SOLD, ListingState.CANCELLED)
