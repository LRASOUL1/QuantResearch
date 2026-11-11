
from dataclasses import dataclass
from typing import Dict, Iterable, Optional


@dataclass
class BookState:
    """A reconstructed order-book state."""

    bids: Dict[float, float]
    asks: Dict[float, float]
    last_update_id: int
    last_update_timestamp: Optional[int] = None

    @property
    def best_bid(self) -> float:
        return max(self.bids)

    @property
    def best_ask(self) -> float:
        return min(self.asks)

    @property
    def mid_price(self) -> float:
        return (self.best_bid + self.best_ask) / 2

    @property
    def spread(self) -> float:
        return self.best_ask - self.best_bid

    def top_levels(self, n: int = 10):
        """Return the top N bid and ask levels, best price first."""

        top_bids = sorted(
            self.bids.items(), key=lambda x: x[0], reverse=True
        )[:n]

        top_asks = sorted(
            self.asks.items(), key=lambda x: x[0]
        )[:n]

        return top_bids, top_asks


class OrderBook:
    """Reconstruct an order book from a snapshot and ordered updates."""

    def __init__(self, snapshot_update_id: int):
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        self.last_update_id = snapshot_update_id
        self.last_update_timestamp = None
        self.is_valid = True
        self.invalid_reason = None

    @classmethod
    def from_snapshot(cls, snapshot_rows):
        """
        Initialize the book from snapshot rows.

        Each row must contain:
            side, price, quantity, last_update_id
        """

        rows = list(snapshot_rows)

        if not rows:
            raise ValueError("Snapshot contains no rows.")

        snapshot_ids = {int(row["last_update_id"]) for row in rows}

        if len(snapshot_ids) != 1:
            raise ValueError("Snapshot rows contain inconsistent update IDs.")

        snapshot_id = snapshot_ids.pop()
        book = cls(snapshot_id)

        for row in rows:
            side = row["side"].lower()
            price = float(row["price"])
            quantity = float(row["quantity"])

            if quantity <= 0:
                continue

            if side == "bid":
                book.bids[price] = quantity
            elif side == "ask":
                book.asks[price] = quantity
            else:
                raise ValueError(f"Unknown book side: {side}")

        if not book.bids or not book.asks:
            raise ValueError("Snapshot must contain both bids and asks.")

        return book

    def apply_batch(self, batch_rows):
        """
        Apply one complete update batch atomically.

        Each row must contain:
            first_update_id, last_update_id, timestamp_ms,
            side, price, quantity

        Returns True if applied, False if stale.
        Raises RuntimeError if a sequence gap invalidates the book.
        """

        if not self.is_valid:
            raise RuntimeError(
                f"Cannot update invalid book: {self.invalid_reason}"
            )

        rows = list(batch_rows)

        if not rows:
            return False

        first_ids = {int(row["first_update_id"]) for row in rows}
        last_ids = {int(row["last_update_id"]) for row in rows}
        timestamps = {int(row["timestamp_ms"]) for row in rows}

        if len(first_ids) != 1 or len(last_ids) != 1:
            raise ValueError("Rows do not belong to one update batch.")

        if len(timestamps) != 1:
            raise ValueError("Batch contains inconsistent timestamps.")

        first_id = first_ids.pop()
        last_id = last_ids.pop()
        timestamp = timestamps.pop()

        if last_id < self.last_update_id + 1:
            return False

        expected_id = self.last_update_id + 1

        if first_id > expected_id:
            self.is_valid = False
            self.invalid_reason = (
                f"Sequence gap: expected update ID {expected_id}, "
                f"but next batch starts at {first_id}."
            )
            raise RuntimeError(self.invalid_reason)

        # Apply the complete batch.
        for row in rows:
            side = row["side"].lower()
            price = float(row["price"])
            quantity = float(row["quantity"])

            if side == "bid":
                book_side = self.bids
            elif side == "ask":
                book_side = self.asks
            else:
                raise ValueError(f"Unknown book side: {side}")

            if quantity == 0:
                book_side.pop(price, None)
            elif quantity > 0:
                book_side[price] = quantity
            else:
                raise ValueError(f"Negative quantity encountered: {quantity}")

        self.last_update_id = last_id
        self.last_update_timestamp = timestamp

        return True

    def state(self) -> BookState:
        """Return a convenient view of the current book."""

        if not self.is_valid:
            raise RuntimeError(
                f"Book is invalid: {self.invalid_reason}"
            )

        return BookState(
            bids=self.bids,
            asks=self.asks,
            last_update_id=self.last_update_id,
            last_update_timestamp=self.last_update_timestamp,
        )

    def validate(self):
        """Check basic order-book integrity."""

        if not self.bids or not self.asks:
            raise ValueError("Book has an empty bid or ask side.")

        if self.best_bid >= self.best_ask:
            raise ValueError(
                f"Invalid or crossed book: "
                f"best bid={self.best_bid}, best ask={self.best_ask}"
            )

        return True

    @property
    def best_bid(self):
        return max(self.bids)

    @property
    def best_ask(self):
        return min(self.asks)
