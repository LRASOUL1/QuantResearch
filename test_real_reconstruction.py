
import duckdb

from src.orderbook.reconstruction import OrderBook


# ============================================================
# CONFIGURATION
# ============================================================

SNAPSHOT_ID = 98351551490

DATA_DIR = (
    "C:/QuantResearch/data/raw/binance_btcusdt"
)

SNAPSHOT_FILE = (
    f"{DATA_DIR}/snapshots/binance/BTCUSDT/2026-08.parquet"
)

DEPTH_FILE = (
    f"{DATA_DIR}/depth/binance/BTCUSDT/2026-08.parquet"
)


# ============================================================
# 1. CONNECT TO DUCKDB
# ============================================================

con = duckdb.connect()

print("Connected to DuckDB.")


# ============================================================
# 2. LOAD SNAPSHOT
# ============================================================

snapshot_rows = con.execute(
    """
    SELECT
        side,
        price,
        quantity,
        last_update_id
    FROM read_parquet(?)
    WHERE last_update_id = ?
    """,
    [SNAPSHOT_FILE, SNAPSHOT_ID],
).fetchdf().to_dict("records")

book = OrderBook.from_snapshot(snapshot_rows)

print("\nSnapshot loaded:")
print(f"  Update ID: {book.last_update_id}")
print(f"  Bid levels: {len(book.bids):,}")
print(f"  Ask levels: {len(book.asks):,}")
print(f"  Best bid: {book.best_bid:.2f}")
print(f"  Best ask: {book.best_ask:.2f}")

assert len(book.bids) == 1000
assert len(book.asks) == 1000
assert book.validate()


# ============================================================
# 3. IDENTIFY THE CONTINUOUS SEGMENT
# ============================================================

print("\nIdentifying continuous update segment...")

batches = con.execute(
    """
    SELECT
        first_update_id,
        last_update_id,
        MIN(timestamp_ms) AS timestamp_ms
    FROM read_parquet(?)
    WHERE last_update_id > ?
    GROUP BY
        first_update_id,
        last_update_id
    ORDER BY first_update_id
    """,
    [DEPTH_FILE, SNAPSHOT_ID],
).fetchall()

expected_id = SNAPSHOT_ID + 1
segment_end_id = SNAPSHOT_ID
batch_count = 0

for first_id, last_id, timestamp in batches:

    if first_id > expected_id:
        break

    if last_id < expected_id:
        continue

    segment_end_id = last_id
    expected_id = last_id + 1
    batch_count += 1

print(f"  Continuous batches: {batch_count:,}")
print(f"  Starting update ID: {SNAPSHOT_ID + 1}")
print(f"  Ending update ID: {segment_end_id}")

assert batch_count > 0, "No continuous batches found."


# ============================================================
# 4. LOAD ALL UPDATES FOR THE SEGMENT
# ============================================================

print("\nLoading segment updates...")

updates = con.execute(
    """
    SELECT
        first_update_id,
        last_update_id,
        timestamp_ms,
        side,
        price,
        quantity
    FROM read_parquet(?)
    WHERE first_update_id > ?
      AND last_update_id <= ?
    ORDER BY
        first_update_id,
        last_update_id,
        timestamp_ms
    """,
    [DEPTH_FILE, SNAPSHOT_ID, segment_end_id],
).fetchdf()

print(f"  Price-level update rows: {len(updates):,}")


# ============================================================
# 5. REPLAY UPDATES
# ============================================================

print("\nReconstructing order book...")

applied_batches = 0

for _, group in updates.groupby(
    ["first_update_id", "last_update_id"],
    sort=True,
):
    rows = group.to_dict("records")
    book.apply_batch(rows)
    applied_batches += 1

assert applied_batches == batch_count
assert book.last_update_id == segment_end_id

book.validate()

state = book.state()

print("\nRECONSTRUCTION COMPLETE")
print("------------------------------")
print(f"Applied batches: {applied_batches:,}")
print(f"Final update ID: {state.last_update_id}")
print(f"Bid levels: {len(state.bids):,}")
print(f"Ask levels: {len(state.asks):,}")
print(f"Best bid: {state.best_bid:.2f}")
print(f"Best ask: {state.best_ask:.2f}")
print(f"Spread: {state.spread:.4f}")
print(f"Mid-price: {state.mid_price:.4f}")

top_bids, top_asks = state.top_levels(5)

print("\nTOP 5 BIDS")
for price, quantity in top_bids:
    print(f"  {price:.2f} | {quantity:.5f}")

print("\nTOP 5 ASKS")
for price, quantity in top_asks:
    print(f"  {price:.2f} | {quantity:.5f}")

print("\nREAL-DATA RECONSTRUCTION TEST PASSED")

con.close()
