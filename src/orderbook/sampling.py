
from dataclasses import dataclass
from typing import Iterable, Optional

from .reconstruction import OrderBook


@dataclass
class BookSample:
    """One timestamped observation of the reconstructed order book."""

    sample_timestamp_ms: int
    last_update_timestamp_ms: Optional[int]
    last_update_id: int

    best_bid: float
    best_ask: float
    mid_price: float
    spread: float

    bid_levels: int
    ask_levels: int

    top_bids: list
    top_asks: list


def sample_order_book(
    book: OrderBook,
    batches: Iterable,
    start_timestamp_ms: int,
    end_timestamp_ms: int,
    interval_ms: int = 1000,
    depth: int = 1000,
):
    """
    Replay ordered update batches and sample the book at fixed intervals.

    Each batch is an iterable of update-row dictionaries.

    Sampling is performed only after all batches with timestamps
    <= the sample timestamp have been applied.

    The function yields BookSample objects.

    The input book is modified in place.
    """

    if interval_ms <= 0:
        raise ValueError("interval_ms must be positive.")

    if depth <= 0:
        raise ValueError("depth must be positive.")

    if end_timestamp_ms < start_timestamp_ms:
        raise ValueError("End timestamp precedes start timestamp.")

    batch_iterator = iter(batches)
    next_batch = next(batch_iterator, None)

    previous_batch_timestamp = None

    for sample_time in range(
        start_timestamp_ms,
        end_timestamp_ms + 1,
        interval_ms,
    ):

        while next_batch is not None:

            rows = list(next_batch)

            if not rows:
                next_batch = next(batch_iterator, None)
                continue

            batch_timestamp = int(rows[0]["timestamp_ms"])

            if (
                previous_batch_timestamp is not None
                and batch_timestamp < previous_batch_timestamp
            ):
                raise ValueError(
                    "Update batches are not ordered by timestamp."
                )

            if batch_timestamp > sample_time:
                break

            book.apply_batch(rows)

            previous_batch_timestamp = batch_timestamp
            next_batch = next(batch_iterator, None)

        if not book.is_valid:
            raise RuntimeError(
                "Cannot sample an invalid order book."
            )

        book.validate()

        state = book.state()
        top_bids, top_asks = state.top_levels(depth)

        yield BookSample(
            sample_timestamp_ms=sample_time,
            last_update_timestamp_ms=state.last_update_timestamp,
            last_update_id=state.last_update_id,
            best_bid=state.best_bid,
            best_ask=state.best_ask,
            mid_price=state.mid_price,
            spread=state.spread,
            bid_levels=len(state.bids),
            ask_levels=len(state.asks),
            top_bids=top_bids,
            top_asks=top_asks,
        )


def finish_replay(book: OrderBook, batches: Iterable):
    """
    Apply all remaining update batches after sampling.

    This is for reconstruction validation only.
    It does not create or modify historical samples.

    Returns the number of batches successfully applied.
    """

    applied = 0

    for batch in batches:
        rows = list(batch)

        if not rows:
            continue

        if book.apply_batch(rows):
            applied += 1

    book.validate()

    return applied

