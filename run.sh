#!/usr/bin/env bash
set -euo pipefail

# Automated bootstrap: create venv, install deps, run tests, generate artifacts, start API.
# Usage: ./run.sh            # full cycle then starts uvicorn
#        FAST=1 ./run.sh     # skip perf/backtest for quicker start
#        TEST=1 ./run.sh     # run tests only

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="python"
VENV_DIR="$PROJECT_ROOT/.venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "[bootstrap] creating virtual environment";
  $PYTHON -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [ ! -f "$VENV_DIR/installed.flag" ]; then
  echo "[bootstrap] installing requirements";
  pip install -r "$PROJECT_ROOT/requirements.txt" || { echo "Install failed"; exit 1; }
  touch "$VENV_DIR/installed.flag"
fi

echo "[step] running pytest"
pytest -q || { echo "Tests failed"; exit 1; }

echo "[step] generating equity curve (deterministic backtest)"
if [ -z "${FAST:-}" ]; then
  $PYTHON "$PROJECT_ROOT/backtest_runner.py" || echo "Backtest script failed (non-critical)"
fi

echo "[step] performance quick check"
if [ -z "${FAST:-}" ]; then
  $PYTHON "$PROJECT_ROOT/perf_asgi_load_test.py" || echo "Perf script failed (non-critical)"
fi

if [ -n "${TEST:-}" ]; then
  echo "[mode] TEST only; exiting before serving"
  exit 0
fi

echo "[serve] starting uvicorn (http://127.0.0.1:8000/signal)"
exec uvicorn main:app --host 127.0.0.1 --port 8000
