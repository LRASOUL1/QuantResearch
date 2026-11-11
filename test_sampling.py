
from src.orderbook.reconstruction import OrderBook
from src.orderbook.sampling import sample_order_book


# ============================================================
# 1. INITIAL SNAPSHOT
# ============================================================

snapshot = [
    {"side": "bid", "price": 100.0, "quantity": 5.0, "last_update_id": 100},
    {"side": "bid", "price": 99.0, "quantity": 8.0, "last_update_id": 100},
    {"side": "ask", "price": 101.0, "quantity": 4.0, "last_update_id": 100},
    {"side": "ask", "price": 102.0, "quantity": 7.0, "last_update_id": 100},
]

book = OrderBook.from_snapshot(snapshot)


# ============================================================
# 2. SYNTHETIC UPDATE BATCHES
# ============================================================

batches = [
    [
        {
            "first_update_id": 101,
            "last_update_id": 101,
            "timestamp_ms": 500,
            "side": "bid",
            "price": 100.0,
            "quantity": 10.0,
        }
    ],
    [
        {
            "first_update_id": 102,
            "last_update_id": 102,
            "timestamp_ms": 1500,
            "side": "bid",
            "price": 100.5,
            "quantity": 3.0,
        }
    ],
    [
        {
            "first_update_id": 103,
            "last_update_id": 103,
            "timestamp_ms": 2500,
            "side": "ask",
            "price": 101.0,
            "quantity": 0.0,
        }
    ],
]


# ============================================================
# 3. SAMPLE AT 1-SECOND INTERVALS
# ============================================================

samples = list(
    sample_order_book(
        book=book,
        batches=batches,
        start_timestamp_ms=0,
        end_timestamp_ms=3000,
        interval_ms=1000,
        depth=2,
    )
)


# ============================================================
# 4. VERIFY RESULTS
# ============================================================

assert len(samples) == 4

# t = 0: no updates applied yet
assert samples[0].best_bid == 100.0
assert samples[0].best_ask == 101.0
assert samples[0].last_update_id == 100

# t = 1000: update at 500ms included
assert samples[1].top_bids[0] == (100.0, 10.0)
assert samples[1].last_update_id == 101

# t = 2000: update at 1500ms included
assert samples[2].best_bid == 100.5
assert samples[2].last_update_id == 102

# t = 3000: ask deletion at 2500ms included
assert samples[3].best_ask == 102.0
assert samples[3].last_update_id == 103

print("TEST 1 PASSED: Correct sampling timestamps")
print("TEST 2 PASSED: No future updates included")
print("TEST 3 PASSED: Book state carried forward correctly")
print("TEST 4 PASSED: Price-level updates and deletions reflected")

print("\nSAMPLED ORDER BOOK")
print("------------------------------")

for sample in samples:
    print(
        f"t={sample.sample_timestamp_ms:4d} ms | "
        f"bid={sample.best_bid:7.2f} | "
        f"ask={sample.best_ask:7.2f} | "
        f"mid={sample.mid_price:8.3f} | "
        f"last_id={sample.last_update_id}"
    )

print("\nALL SAMPLING TESTS PASSED")
