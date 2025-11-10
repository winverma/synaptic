🚀 Quick Start (One Command Execution)The entire project (setup, dependency installation, service launch, and full test suite execution) is managed by a single command.Prerequisites: You must have Python 3.10+ and Make or Bash installed.Bash# This command will:

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

### `run.sh` Content (Must be executable: `chmod +x run.sh`)

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
