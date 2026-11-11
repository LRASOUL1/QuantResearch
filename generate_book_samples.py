
from pathlib import Path
from itertools import groupby

import duckdb
import pandas as pd

from src.orderbook.reconstruction import OrderBook
from src.orderbook.sampling import sample_order_book, finish_replay


# ============================================================
# CONFIGURATION
# ============================================================

SNAPSHOT_ID = 98351551490
SEGMENT_END_ID = 98351655098

DATA_DIR = Path("C:/QuantResearch/data/raw/binance_btcusdt")
OUTPUT_DIR = Path("C:/QuantResearch/data/processed")

SNAPSHOT_FILE = (
    DATA_DIR / "snapshots/binance/BTCUSDT/2026-08.parquet"
)
DEPTH_FILE = (
    DATA_DIR / "depth/binance/BTCUSDT/2026-08.parquet"
)

INTERVAL_MS = 1000
DEPTH = 1000

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. LOAD SNAPSHOT
# ============================================================

con = duckdb.connect()

print("Loading initial snapshot...")

snapshot_rows = con.execute(
    """
    SELECT side, price, quantity, last_update_id
    FROM read_parquet(?)
    WHERE last_update_id = ?
    """,
    [str(SNAPSHOT_FILE), SNAPSHOT_ID],
).fetchdf().to_dict("records")

book = OrderBook.from_snapshot(snapshot_rows)
book.validate()

print(f"Snapshot initialized: {SNAPSHOT_ID}")


# ============================================================
# 2. LOAD VERIFIED CONTINUOUS SEGMENT
# ============================================================

print("Loading continuous depth updates...")

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
    ORDER BY first_update_id, last_update_id, timestamp_ms
    """,
    [str(DEPTH_FILE), SNAPSHOT_ID, SEGMENT_END_ID],
).fetchdf()

print(f"Loaded {len(updates):,} price-level updates.")

assert not updates.empty

# The segment boundaries were verified in the earlier test.
# Check them again before replaying.
assert int(updates.iloc[0]["first_update_id"]) == SNAPSHOT_ID + 1
assert int(updates.iloc[-1]["last_update_id"]) == SEGMENT_END_ID


# ============================================================
# 3. GROUP UPDATES INTO ATOMIC BATCHES
# ============================================================

records = updates.to_dict("records")

def batch_generator():
    for _, group in groupby(
        records,
        key=lambda row: (
            row["first_update_id"],
            row["last_update_id"],
        ),
    ):
        yield list(group)


# ============================================================
# 4. DETERMINE SAMPLING WINDOW
# ============================================================

first_timestamp = int(updates["timestamp_ms"].min())
last_timestamp = int(updates["timestamp_ms"].max())

# Use whole-second boundaries.
# Start at the first second at or after the first update.
start_timestamp = (
    (first_timestamp + INTERVAL_MS - 1) // INTERVAL_MS
) * INTERVAL_MS

end_timestamp = (
    last_timestamp // INTERVAL_MS
) * INTERVAL_MS

print(f"First update timestamp: {first_timestamp}")
print(f"Last update timestamp:  {last_timestamp}")
print(f"Sampling start:         {start_timestamp}")
print(f"Sampling end:           {end_timestamp}")


# ============================================================
# 5. RECONSTRUCT AND SAMPLE
# ============================================================

print("Reconstructing and sampling...")

samples = list(
    sample_order_book(
        book=book,
        batches=batch_generator(),
        start_timestamp_ms=start_timestamp,
        end_timestamp_ms=end_timestamp,
        interval_ms=INTERVAL_MS,
        depth=DEPTH,
    )
)

print(f"Generated {len(samples):,} samples.")

# Finish replaying any updates after the final sampling timestamp.
# Recreate the batch iterator; already-applied batches are ignored
# by the reconstruction engine as stale.
remaining_applied = finish_replay(book, batch_generator())

print(f"Additional batches applied: {remaining_applied:,}")
print(f"Final update ID: {book.last_update_id}")

assert book.last_update_id == SEGMENT_END_ID

# Check that the book remains valid.
book.validate()

# ============================================================
# 6. BUILD SUMMARY DATASET
# ============================================================

summary_rows = []

for sample in samples:
    summary_rows.append(
        {
            "sample_timestamp_ms": sample.sample_timestamp_ms,
            "last_update_timestamp_ms": sample.last_update_timestamp_ms,
            "last_update_id": sample.last_update_id,
            "best_bid": sample.best_bid,
            "best_ask": sample.best_ask,
            "mid_price": sample.mid_price,
            "spread": sample.spread,
            "bid_levels": sample.bid_levels,
            "ask_levels": sample.ask_levels,
        }
    )

summary_df = pd.DataFrame(summary_rows)


# ============================================================
# 7. BUILD FULL DEPTH DATASET
# ============================================================

depth_rows = []

for sample in samples:

    for level, (price, quantity) in enumerate(
        sample.top_bids, start=1
    ):
        depth_rows.append(
            {
                "sample_timestamp_ms": sample.sample_timestamp_ms,
                "side": "bid",
                "level": level,
                "price": price,
                "quantity": quantity,
            }
        )

    for level, (price, quantity) in enumerate(
        sample.top_asks, start=1
    ):
        depth_rows.append(
            {
                "sample_timestamp_ms": sample.sample_timestamp_ms,
                "side": "ask",
                "level": level,
                "price": price,
                "quantity": quantity,
            }
        )

depth_df = pd.DataFrame(depth_rows)


# ============================================================
# 8. SAVE PARQUET FILES
# ============================================================

summary_path = OUTPUT_DIR / "btc_book_summary_1s.parquet"
depth_path = OUTPUT_DIR / "btc_book_depth_1s.parquet"

summary_df.to_parquet(summary_path, index=False)
depth_df.to_parquet(depth_path, index=False)

print("\nFILES SAVED")
print("------------------------------")
print(summary_path)
print(depth_path)


# ============================================================
# 9. VALIDATE OUTPUT
# ============================================================

assert summary_df["sample_timestamp_ms"].is_unique
assert summary_df["sample_timestamp_ms"].is_monotonic_increasing
assert (summary_df["best_bid"] < summary_df["best_ask"]).all()

assert (
    summary_df["last_update_timestamp_ms"]
    <= summary_df["sample_timestamp_ms"]
).all()

assert (
    summary_df["last_update_id"].diff().dropna() >= 0
).all()

print("\nSUMMARY PREVIEW")
print(summary_df.head(10).to_string(index=False))

print("\nFINAL RECONSTRUCTION STATE")
print("------------------------------")
print(f"Last applied update ID: {book.last_update_id}")
print(f"Final best bid: {book.best_bid:.2f}")
print(f"Final best ask: {book.best_ask:.2f}")

print("\nSAMPLING PIPELINE COMPLETED")

con.close()
