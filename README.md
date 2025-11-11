🚀 Quick Start (One Command Execution)

The entire project (setup, dependency installation, service launch, and full test suite execution) is managed by a single command.

Prerequisites: You must have Python 3.10+ and Make or Bash installed.

# This command will:

 1. Install dependencies (FastAPI, Nautilus Trader, pytest, etc.)
 2. Run the full test suite (T1 indicators, T1 service, T2 deterministic backtest).
 3. Launch the T1 FastAPI "Signal" Service in the background (using Uvicorn).

make run
 OR
 bash run.sh

 
## 🚀 Quick Start: Single Command Execution

The entire project (install, test, and run the service) is executed via a single command from a clean clone.

**Prerequisites:** You must have **Python 3.10+** and **Bash** (or WSL/Git Bash on Windows).

```bash
# This command performs:
# 1. Dependency Installation (FastAPI, Nautilus Trader, pytest, etc.)
# 2. Runs the full test suite (T1/T2).
# 3. Launches the T1 FastAPI "Signal" Service (runs in the background).

bash run.sh
```

**Service Access:** The T1 Signal Service will be running at `http://localhost:8000`.


## Windows (PowerShell)
```powershell
./run.ps1
```

This will:
1. Create a virtual environment in `.venv/` if missing.
2. Install `requirements.txt` once (cached by `installed.flag`).
3. Run the test suite (`pytest -q`).
4. (Unless FAST=1) Generate a deterministic backtest (`backtest_runner.py`) producing `equity_curve.csv`.
5. (Unless FAST=1) Run a quick in‑process performance check (`perf_asgi_load_test.py`).
6. Start the FastAPI service at `http://127.0.0.1:8000/signal`.

## Optional Modes
Skip perf & backtest for faster startup:
```bash
FAST=1 ./run.sh
```
```powershell
$env:FAST=1; ./run.ps1
```

Run tests only (no server):
```bash
TEST=1 ./run.sh
```
```powershell
$env:TEST=1; ./run.ps1
```

## Verification & Traceability
See `docs/Verification.md` for full artifact mapping (indicators, service, performance, backtest, SQL schema, Nautilus scaffold) and reproduction steps.

## Manual Service Launch (alternative)
If you just want the API:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```
PowerShell:
```powershell
uvicorn main:app --host 127.0.0.1 --port 8000
```

## Endpoints
- GET `/signal` — returns latest cached trend, decision, RSI.
- WS `/ws/signal/{symbol}` — real‑time stream with initial snapshot.

## Determinism
`backtest_runner.py` produces a repeatable equity curve from `ohlcv.csv`. Tests ensure indicator logic and service contract stability.

## Next Steps (Suggested)
- Migrate startup to FastAPI lifespan context for deprecation warnings.
- Flesh out `nautilus_runner.py` with concrete adapters and assert final equity in tests.
- Add linting (ruff or flake8) & type checking (mypy) for stricter CI.

```bash
#!/bin/bash

echo "--- 1/3: Installing Dependencies ---"
# Create a virtual environment if needed, or simply install globally/locally
pip install -r requirements.txt || { echo "Installation failed. Check requirements.txt"; exit 1; }

echo "--- 2/3: Running All Tests (T1 Indicators, T1 Service, T2 Deterministic Backtest) ---"
# Run pytest and exit immediately if tests fail
pytest || { echo "Tests failed. Fix errors before proceeding."; exit 1; }

echo "--- 3/3: Starting T1 FastAPI Signal Service ---"
echo "Service running at http://localhost:8000"
# Use a single worker for simplicity in a dev environment
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## 📁 Repository Structure and Deliverables

| Directory | Content & Key Deliverables | Tasks Covered |
| :--- | :--- | :--- |
| **`src/`** | Service (`main.py`), Indicators (`indicators.py`), Nautilus Runner (`nautilus_runner.py`). | T1, T2 |
| **`tests/`** | Unit tests for T1 (indicators/endpoints) and the T2 **deterministic test**. | T1, T2 |
| **`docs/`** | **Mandatory Documentation:** `README.md`, `DESIGN.md`, `VERIFICATION.md`. | T1, T3, T4 |
| **`docs/ai-logs.txt`** | Raw prompt logs used with AI assistants. | All |

## 🔎 Key Verification Files

The evaluation requires specific files to audit AI usage and verification:

  * **`VERIFICATION.md`**: Contains the audit log for AI outputs, including the verification of the RSI formula and the successful detection/correction of the T2 **outdated Nautilus import trap**.
  * **`t1_perf_note.txt`**: Benchmarking evidence proving $\mathbf{P95 < 100\text{ms}}$ for the `GET /signal` endpoint.
  * **`prompts/`**: Required submission of all input prompts used during the evaluation.
