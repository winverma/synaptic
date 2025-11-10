## Verification report (end-to-end)

This document captures how each deliverable was implemented, validated, and audited from first edit to final checks. It is designed to be reproducible on a Windows host using PowerShell.

### 1) Artifacts and where to find them

- Indicators
	- `indicators.py` — SMA and RSI (Wilder) with `determine_trend_and_decision` (MA20/50 + RSI14)
	- Tests: `tests/test_indicators.py`
- Service
	- App: `main.py` (GET /signal, WS /ws/signal with background consumer)
	- Tests: `tests/test_service.py`
- Performance note
	- In‑process load: `perf_asgi_load_test.py`
	- Network client (optional): `perf_load_test.py`
	- Result: `docs/t1_perf_note.txt`
- Backtest (baseline, deterministic)
	- Runner: `backtest_runner.py`
	- Output file: `equity_curve.csv`
- Nautilus integration (scaffold)
	- Runner: `nautilus_runner.py`
	- Tests: `tests/test_nautilus.py` (skips if Nautilus not installed)
- SQL deliverables
	- Schema DDL: `t3_schema.sql` (or copy from prior message)
	- Analytics queries: delivered in prior step (kept in conversation for brevity)
- Design / docs
	- Optimization: `docs/DESIGN.md`
	- This report: `docs/Verification.md`

### 2) Methodology and quality gates

- Coding workflow: Implement small, testable changes; immediately add/adjust tests; run test suite; iterate until green.
- Quality gates executed after substantive edits:
	- Build/import check: PASS (Python files importable in repo context)
	- Tests: PASS (9 tests) — see section 3
	- Lint/type hints: Not enforced in repo; basic static import checks were observed (warnings for missing third‑party packages such as Nautilus in optional code paths)
	- Environment note: Verified on Windows (PowerShell) with Python 3.14; if multiple Python installs exist, prefer an activated venv (`python -m venv .venv; .\.venv\Scripts\Activate.ps1`).

### 3) Unit and integration tests

- Indicators
	- Cases: flat RSI=50, insufficient data RSI=50, monotonic up RSI=100, manual RSI window match, SMA correctness and insufficient data behavior.
	- Result: PASS.
- Service
	- GET /signal: httpx AsyncClient with lifespan; asserts structure and value bounds.
	- WS /ws/signal: FastAPI TestClient; receives initial snapshot with `decision`.
	- Result: PASS.
- Nautilus runner
	- Test uses `pytest.importorskip('nautilus_trader')` and asserts determinism with fixed seed; skipped if library not present or placeholders need mapping.
	- Result: SKIPPED (library not installed in this environment).

Repro (PowerShell):
```powershell
python -m pytest -q
```

Observed summary during verification: `9 passed, 0 failed` (skips may appear if Nautilus not present).

Tip: To avoid optional Nautilus test entirely, run:
```powershell
python -m pytest -q -k "not nautilus"
```

If your shell maps Python as `py`, you can use:
```powershell
py -3 -m pytest -q
```

### 4) API contract: GET /signal

Request
- Method/Path: GET `/signal`
- Query: none (current implementation serves the default symbol tracked by the background consumer)

Response 200
```json
{
	"symbol": "BTCUSDT",
	"decision": "BUY" | "SELL" | "HOLD",
	"trend": "UP" | "DOWN" | "FLAT",
	"rsi": 0.0,
	"ts": "2025-11-10T12:34:56.789Z"
}
```

Notes
- RSI is Wilder RSI(14). When data is insufficient, RSI defaults to 50.0 (neutral).
- Trend is derived from SMA(20) vs SMA(50). If insufficient data, trend is `FLAT`.
- The service computes and caches values in the background task and serves cached values for low latency.
- Error modes: 500 on internal error; 200 with neutral fields for initial warm-up. Unknown symbol handling can be added if multi-symbol support is introduced.

### 5) Functional checks (manual)

- Backtest runner
	- Ran `python backtest_runner.py` against `ohlcv.csv`.
	- Verified trade list printed and `equity_curve.csv` written; summary PnL/MaxDD displayed.
- Service behavior
	- Background consumer precomputes `latest_trend`, `latest_decision`, `latest_rsi` on each tick.
	- GET returns cached values (no recalculation) to ensure low latency.
	- WS sends an initial snapshot on connect, then updates on change.

### 6) Performance measurement (T1)

- Tooling
	- In‑process ASGI load driver: `perf_asgi_load_test.py` (stable, no OS socket).
	- Optional network client: `perf_load_test.py` (requires running Uvicorn separately).
- Run performed (ASGI in‑process): ~100 QPS for 10s
	- Example result written to `docs/t1_perf_note.txt`:
		- requests: 1000, success: 1000, errors: 0
		- achieved_qps: ~99.98
		- min/mean/p95/max ms ≈ 0.27 / 0.63 / 0.94 / 6.11
	- Interpretation: P95 ≪ 100 ms → meets requirement.

Repro (PowerShell):
```powershell
python perf_asgi_load_test.py
# For network mode:
# python -m uvicorn main:app --host 127.0.0.1 --port 8001
# python perf_load_test.py
```

### 7) SQL deliverables verification

- Schema DDL
	- Checked for appropriate types: prices NUMERIC(18,8), size/volume NUMERIC(28,12), times TIMESTAMPTZ/DATE.
	- Partitioning guidance provided on time columns; pragmatic indexes on (symbol, ts) and (strategy_id, date).
- Analytics queries
	- CTE + window functions for cumulative PnL and max drawdown; DISTINCT ON/ROW_NUMBER view for last positions; rolling 30‑day Sharpe with `STDDEV_SAMP` and `sqrt(252)`.
	- Verified syntax is modern PostgreSQL and partition-pruning friendly with time filters.

### 8) Determinism and seeds

- Baseline backtest (`backtest_runner.py`) is deterministic over the provided CSV (no randomness).
- Nautilus integration test fixes the engine seed to ensure reproducibility once concrete fee/slippage/data adapters are mapped.

### 9) Risks, gaps, and mitigations

- External deps
	- Nautilus library not installed → tests skip; placeholders in `nautilus_runner.py` require mapping to your installed version’s fee/slippage/strategy/data APIs.
- Microstructure realism
	- Baseline runner uses fixed 1‑tick slippage; `DESIGN.md` outlines a volatility/participation model and next‑bar fills for higher fidelity.
- FastAPI lifespan
	- `on_event` is deprecated; migrate to lifespan handlers to remove warnings (functionality unaffected).

### 10) How to reproduce end‑to‑end

```powershell
# 1) Run tests
python -m pytest -q

# 2) Generate equity curve
python backtest_runner.py

# 3) Performance note (in‑process ASGI)
python perf_asgi_load_test.py

# 4) Optional: serve API and hit it
# python -m uvicorn main:app --host 127.0.0.1 --port 8001
# python perf_load_test.py
```

All the above steps were executed during verification; test and perf outputs are saved in the repository (`equity_curve.csv`, `docs/t1_perf_note.txt`).

### 11) Traceability (quick map)

- Efficient indicators → `indicators.py`, validated by `tests/test_indicators.py`.
- Low-latency service → `main.py`, validated by `tests/test_service.py` and `perf_asgi_load_test.py`.
- Performance requirement (p95 < 100 ms @ ~100 QPS) → `docs/t1_perf_note.txt` produced by `perf_asgi_load_test.py`.
- Deterministic backtest baseline → `backtest_runner.py` producing `equity_curve.csv` from `ohlcv.csv`.
- SQL schema and analytics → `t3_schema.sql` and provided queries (conversation artifacts), rationale in `docs/DESIGN.md`.
- Nautilus scaffold and determinism approach → `nautilus_runner.py`, `tests/test_nautilus.py` (skipped if package absent).

### 12) Edge cases considered

- Insufficient bars for RSI/SMA → RSI returns 50.0 (neutral), trend becomes `FLAT`.
- Flat series → RSI ≈ 50.0; no division-by-zero due to guarded logic.
- Service cold start → cached fields initialize to neutral values before first ticks.
- WebSocket initial state → sends a snapshot immediately upon connect, then deltas.

