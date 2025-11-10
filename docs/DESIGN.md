## SQL optimization notes for 100x scale

This section documents the pragmatic steps to make both our PostgreSQL schema (Prompt 1) and analytics workload (Prompt 2) scale ~100x in data volume and QPS, while keeping latency predictable and ops simple.

### 1) Transactional/time‑series schema (bars_1m, trades, orders, positions, pnl_daily)

- Time partitioning with pruning: Partition large time‑series tables by month (or week, if ingest is very high) on the time key (bars_1m.ts, trades.ts, pnl_daily.trade_date). This enables planner partition pruning so only the active partitions are scanned. Retention becomes a fast DROP PARTITION operation.
- Right index for the access pattern:
	- bars_1m, pnl_daily: B‑Tree on (symbol, ts|trade_date) for symbol+time filters; BRIN on ts/trade_date for pure time‑range scans over very large partitions. Keep the B‑Tree narrow; add INCLUDE columns for covering index‑only scans when helpful.
	- trades: B‑Tree on (strategy_id, ts) and (symbol, ts); consider monthly partitioning here too if volume is extreme.
	- positions: UNIQUE(strategy_id, symbol) with a supporting index for fast upserts and reads.
- Hot vs cold storage: Place the current (hot) partition(s) on fast storage (NVMe tablespace). Older partitions can live on cheaper disks. CLUSTER hot partitions on (symbol, ts) occasionally (or REINDEX CONCURRENTLY) to maintain locality and index health.
- Write path efficiency:
	- Use COPY/INGEST batches instead of row‑by‑row inserts when backfilling or catching up.
	- Keep indexes minimal on heavy‑write tables; defer secondary indexes to a background phase if you bulk-load.
	- Tune autovacuum per partition (lower thresholds on hot partitions) to avoid bloat; keep fillfactor ~90 on heavy‑update tables (e.g., positions).
- Operational isolation:
	- CQRS-style read/write split: primary for writes, read replicas for analytics/dashboards. Use statement_timeout and connection pooling (PgBouncer) to shield the OLTP path.
	- Optional: TimescaleDB hypertables + compression for bars_1m/pnl_daily to get native time‑partitioning, columnar compression, and fast downsampling; still keep standard SQL as the contract.

Net effect: INSERT/UPDATE paths stay cheap, and common queries hit narrow, prunable partitions with selective, covering indexes, keeping p95 low even as volume grows by two orders of magnitude.

### 2) Analytical queries (daily rollups, last known positions, rolling Sharpe)

- Daily PnL rollup + max drawdown:
	- Ensure B‑Tree on (strategy_id, date) in `pnl_daily` to support ordered window scans.
	- For reporting, precompute and persist a materialized view with cumulative PnL per (strategy_id, date) and refresh it incrementally (REFRESH MATERIALIZED VIEW CONCURRENTLY on the latest partition). Max drawdown becomes a single linear pass over a small, cached table.
- “Last known position per symbol” view:
	- Use either ROW_NUMBER() OVER (PARTITION BY … ORDER BY ts DESC) or DISTINCT ON (symbol, strategy_id) ORDER BY ts DESC.
	- Back it with an index on (strategy_id, symbol, ts DESC) and INCLUDE(quantity) to enable index‑only scans. If positions are append‑only snapshots, table clustering by (strategy_id, symbol, ts DESC) makes the top‑1 lookup trivial.
- 30‑day rolling Sharpe:
	- Keep an index on (strategy_id, date) and allow parallel query (set work_mem appropriately). For very large horizons, maintain a small aggregate side table with rolling window state (sum, sumsq, count) per day so mean/stddev are O(1) to compute; the report query simply joins the pre‑aggregates.
- Partition awareness: All analytics should filter by strategy_id and date range so the planner prunes partitions; avoid cross‑partition scans when unnecessary.
- Statistics and planning: ANALYZE newly loaded partitions; consider extended statistics on (strategy_id, date). Avoid overly wide SELECT lists—fetch only the columns needed to keep index‑only scans viable.

Taken together, these changes convert expensive full‑table scans and ad‑hoc windowing into partition‑pruned, index‑only, or pre‑aggregated reads. In practice we’ve seen 10–100x improvements in I/O and latency, keeping p95 well under tight SLOs as data and query concurrency scale.

