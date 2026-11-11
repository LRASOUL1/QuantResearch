
from src.orderbook.reconstruction import OrderBook


# ------------------------------------------------------------
# TEST 1: Initialize a book from a snapshot
# ------------------------------------------------------------

snapshot = [
    {"side": "bid", "price": 100.0, "quantity": 5.0, "last_update_id": 100},
    {"side": "bid", "price": 99.0, "quantity": 8.0, "last_update_id": 100},
    {"side": "ask", "price": 101.0, "quantity": 4.0, "last_update_id": 100},
    {"side": "ask", "price": 102.0, "quantity": 7.0, "last_update_id": 100},
]

book = OrderBook.from_snapshot(snapshot)

assert book.best_bid == 100.0
assert book.best_ask == 101.0
assert book.state().mid_price == 100.5
assert book.validate()

print("TEST 1 PASSED: Snapshot initialization")


# ------------------------------------------------------------
# TEST 2: Update an existing price level
# ------------------------------------------------------------

batch_1 = [
    {
        "first_update_id": 101,
        "last_update_id": 102,
        "timestamp_ms": 1000,
        "side": "bid",
        "price": 100.0,
        "quantity": 12.0,
    },
    {
        "first_update_id": 101,
        "last_update_id": 102,
        "timestamp_ms": 1000,
        "side": "ask",
        "price": 101.0,
        "quantity": 6.0,
    },
]

book.apply_batch(batch_1)

assert book.bids[100.0] == 12.0
assert book.asks[101.0] == 6.0
assert book.last_update_id == 102

print("TEST 2 PASSED: Existing price-level updates")


# ------------------------------------------------------------
# TEST 3: Delete a price level
# ------------------------------------------------------------

batch_2 = [
    {
        "first_update_id": 103,
        "last_update_id": 103,
        "timestamp_ms": 2000,
        "side": "bid",
        "price": 100.0,
        "quantity": 0.0,
    },
]

book.apply_batch(batch_2)

assert 100.0 not in book.bids
assert book.best_bid == 99.0

print("TEST 3 PASSED: Price-level deletion")


# ------------------------------------------------------------
# TEST 4: Ignore a stale batch
# ------------------------------------------------------------

stale_batch = [
    {
        "first_update_id": 102,
        "last_update_id": 102,
        "timestamp_ms": 1500,
        "side": "ask",
        "price": 101.0,
        "quantity": 99.0,
    },
]

applied = book.apply_batch(stale_batch)

assert applied is False
assert book.asks[101.0] == 6.0
assert book.last_update_id == 103

print("TEST 4 PASSED: Stale batch ignored")


# ------------------------------------------------------------
# TEST 5: Detect a sequence gap
# ------------------------------------------------------------

gap_batch = [
    {
        "first_update_id": 105,
        "last_update_id": 105,
        "timestamp_ms": 3000,
        "side": "bid",
        "price": 99.0,
        "quantity": 10.0,
    },
]

try:
    book.apply_batch(gap_batch)
    raise AssertionError("Expected a sequence-gap error.")
except RuntimeError as error:
    assert "Sequence gap" in str(error)

assert book.is_valid is False

print("TEST 5 PASSED: Sequence gap detected")


print("\nALL TESTS PASSED")
