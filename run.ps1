<#
PowerShell bootstrap script for Windows users.
Usage:
  ./run.ps1              # full cycle then starts uvicorn
  $env:FAST=1; ./run.ps1 # skip perf/backtest
  $env:TEST=1; ./run.ps1 # run tests only
#>

$ErrorActionPreference = 'Stop'
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV_DIR = Join-Path $PROJECT_ROOT '.venv'
$PYTHON = 'python'

if (-not (Test-Path $VENV_DIR)) {
  Write-Host '[bootstrap] creating virtual environment'
  & $PYTHON -m venv $VENV_DIR
}

$activate = Join-Path $VENV_DIR 'Scripts/Activate.ps1'
. $activate

if (-not (Test-Path (Join-Path $VENV_DIR 'installed.flag'))) {
  Write-Host '[bootstrap] installing requirements'
  pip install -r (Join-Path $PROJECT_ROOT 'requirements.txt')
  New-Item -Path (Join-Path $VENV_DIR 'installed.flag') -ItemType File | Out-Null
}

Write-Host '[step] running pytest'
& pytest -q

if (-not $env:FAST) {
  Write-Host '[step] generating equity curve (deterministic backtest)'
  try { & $PYTHON (Join-Path $PROJECT_ROOT 'backtest_runner.py') } catch { Write-Warning 'Backtest script failed (non-critical)' }

  Write-Host '[step] performance quick check'
  try { & $PYTHON (Join-Path $PROJECT_ROOT 'perf_asgi_load_test.py') } catch { Write-Warning 'Perf script failed (non-critical)' }
}

if ($env:TEST) {
  Write-Host '[mode] TEST only; exiting before serving'
  exit 0
}

Write-Host '[serve] starting uvicorn (http://127.0.0.1:8000/signal)'
& uvicorn main:app --host 127.0.0.1 --port 8000
