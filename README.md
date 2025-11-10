🚀 Quick Start (One Command Execution)The entire project (setup, dependency installation, service launch, and full test suite execution) is managed by a single command.Prerequisites: You must have Python 3.10+ and Make or Bash installed.Bash# This command will:

 1. Install dependencies (FastAPI, Nautilus Trader, pytest, etc.)
 2. Run the full test suite (T1 indicators, T1 service, T2 deterministic backtest).
 3. Launch the T1 FastAPI "Signal" Service in the background (using Uvicorn).

make run
 OR
 bash run.sh
 
Note: The service will be running at http://localhost:8000. Use Ctrl+C in the terminal running the service to shut it down after running the tests.🔬 Individual Execution CommandsTargetCommandPurposeInstallpip install -r requirements.txtInstalls all project dependencies.Run TestspytestExecutes all tests in the tests/ directory.Run Backtestpython src/nautilus_runner.pyExecutes the T2 Nautilus Trader backtest.Start Serviceuvicorn src.main:app --host 0.0.0.0 --port 8000Starts the T1 Signal Service.📄 Submission and DocumentationFilePurposeLocationGoogle DocFull narrative, metrics, and analysis for all tasks.[Insert Google Doc View Link Here]VERIFICATION.mdAuditing log for AI outputs and correction of the T2 deliberate trap.docs/DESIGN.mdDesign rationale for low-latency T1 architecture and T3 data model.docs/t1_perf_note.txtEvidence of $\text{P95} < 100\text{ms}$ benchmark.docs/
