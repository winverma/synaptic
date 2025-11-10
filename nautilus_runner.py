"""
# src/nautilus_runner.py

Nautilus Trader integration for the SMA(20/50) crossover backtest.

This module shows the modern import path and a minimal, deterministic runner
configuration to match the baseline runner settings:
- Fees: ~1 bps using a fixed bps fee model
- Slippage: fixed 1 tick
- Position size: 1
- End-of-Day: flatten positions

Notes
- This file intentionally isolates all Nautilus-specific imports inside the
  run function to avoid import errors when the library is not installed.
- The concrete fee/slippage model class names can vary by version; the
  try/except imports demonstrate the intended locations and provide clear
  error messages if your version differs.
- The data-feed wiring uses placeholder comments since API details can differ
  by version. Replace the “load_ohlcv_csv” body with your project’s adapter.
"""

from __future__ import annotations

from typing import Dict


def run_nautilus_backtest(csv_path: str = "ohlcv.csv", seed: int = 123) -> Dict[str, float]:
    """Run a Nautilus Trader backtest with SMA(20/50) crossover.

    Returns a metrics dict, e.g. {"total_pnl": float, "max_drawdown": float}.

    Raises ImportError if Nautilus Trader is not available.
    May raise NotImplementedError if fee/slippage models differ in your version
    and placeholders are not updated.
    """
    try:
        # Core engine and config
        from nautilus_trader.backtest.engine import BacktestEngine
        from nautilus_trader.backtest.config import BacktestEngineConfig
    except Exception as exc:  # pragma: no cover
        raise ImportError(
            "Nautilus Trader is not installed. Please install it to run this backtest."
        ) from exc

    # Fee and slippage models: class names/paths may vary by version. Adjust as needed.
    fee_model = None
    slippage_model = None
    fee_exc = None
    slip_exc = None
    try:
        from nautilus_trader.backtest.fees import FixedBpsFeeModel  # type: ignore

        fee_model = FixedBpsFeeModel(bps=1.0)  # ~1 bps
    except Exception as e:  # pragma: no cover
        fee_exc = e
    try:
        from nautilus_trader.backtest.slippage import FixedTickSlippageModel  # type: ignore

        slippage_model = FixedTickSlippageModel(ticks=1)
    except Exception as e:  # pragma: no cover
        slip_exc = e

    if fee_model is None or slippage_model is None:
        # Provide a helpful message so users can map to their version.
        raise NotImplementedError(
            "Could not import FixedBpsFeeModel and/or FixedTickSlippageModel. "
            "Please update nautilus_runner.py to use the fee/slippage models available in your Nautilus version.\n"
            f"Fee import error: {fee_exc}\nSlippage import error: {slip_exc}"
        )

    # Build engine config (parameters can vary by version)
    config = BacktestEngineConfig(
        starting_balances={"USD": 1_000_000},
        fee_model=fee_model,
        slippage_model=slippage_model,
        seed=seed,
        # Some versions expose eod_flat or similar behavior via config or strategy.
        # If your version differs, implement EOD flatten inside the strategy.
        # eod_flat=True,
    )

    engine = BacktestEngine(config)

    # 1) Register instruments and load OHLCV into the engine’s data store
    # Replace this placeholder with your project’s data adapter.
    load_ohlcv_csv(engine, csv_path)

    # 2) Add SMA crossover strategy (size=1)
    # Strategy API can differ between versions; here we demonstrate the intent.
    try:
        from nautilus_trader.trading.strategy import Strategy  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise NotImplementedError(
            "Strategy base class import failed. Map to your Nautilus version."
        ) from exc

    class SmaCrossStrategy(Strategy):  # type: ignore
        fast: int = 20
        slow: int = 50
        size: float = 1.0

        def on_start(self):  # type: ignore
            # Subscribe to bars / initialize indicators here.
            # self.subscribe_bars(symbol, timeframe)
            pass

        def on_bar(self, bar):  # type: ignore
            # Compute SMA(20/50) on closes and place 1-lot orders on crossover.
            # Pseudocode (replace with your version’s indicator accessors):
            # fast = self.sma_fast.value(symbol)
            # slow = self.sma_slow.value(symbol)
            # if fast > slow and self.position_qty(symbol) <= 0:
            #     self.buy(symbol, qty=self.size)
            # elif fast < slow and self.position_qty(symbol) > 0:
            #     self.sell(symbol, qty=self.position_qty(symbol))
            pass

        def on_end_of_day(self):  # type: ignore
            # Flatten any open position at EOD for determinism.
            # for sym in self.symbols:
            #     qty = self.position_qty(sym)
            #     if qty > 0:
            #         self.sell(sym, qty=qty)
            pass

    # Register and run
    strategy = SmaCrossStrategy()
    engine.add_strategy(strategy)
    engine.run()

    # Collect metrics – adapt the accessors to your version.
    metrics = {
        "total_pnl": float(getattr(engine.performance, "total_pnl", 0.0)),
        "max_drawdown": float(getattr(engine.performance, "max_drawdown", 0.0)),
    }
    return metrics


def load_ohlcv_csv(engine, csv_path: str) -> None:
    """Placeholder CSV loader for Nautilus Trader.

    Replace this with code that:
    - Registers the instrument/security in the engine (symbol, tick size, etc.)
    - Parses CSV rows and inserts bars (timestamp, O/H/L/C/V) into the engine’s
      data store with the correct BarType/BarSpecification per your version.
    """
    # Example sketch (not executable without the concrete API):
    # from nautilus_trader.model.identifiers import Symbol
    # from nautilus_trader.model.data import Bar, BarSpecification, PriceType
    # bar_type = BarSpecification(symbol=Symbol("XYZ"), price_type=PriceType.LAST, interval=60)
    # for row in csv:
    #     bar = Bar.from_ohlcv(...)
    #     engine.add_data(bar)
    return None
