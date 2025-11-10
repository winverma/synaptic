import math
import pytest


nautilus = pytest.importorskip("nautilus_trader", reason="Nautilus Trader not installed")


def test_nautilus_runner_is_deterministic():
    # If Nautilus is present, attempt to run with a fixed seed
    from nautilus_runner import run_nautilus_backtest

    try:
        m1 = run_nautilus_backtest(csv_path="ohlcv.csv", seed=123)
        m2 = run_nautilus_backtest(csv_path="ohlcv.csv", seed=123)
    except NotImplementedError:
        pytest.skip("Nautilus integration placeholders need mapping to your installed version")

    # Assert determinism on a key metric with tight tolerance
    assert "total_pnl" in m1 and "total_pnl" in m2
    assert math.isclose(m1["total_pnl"], m2["total_pnl"], rel_tol=1e-9, abs_tol=1e-9)

    # Optionally lock to a specific numeric if your environment is stable
    # expected_total_pnl = 0.0
    # assert math.isclose(m1["total_pnl"], expected_total_pnl, rel_tol=1e-6, abs_tol=1e-6)
