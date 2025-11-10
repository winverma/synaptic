# src/backtest_runner.py
"""
Deterministic backtest runner over OHLCV CSV data.

Requirements implemented:
- Strategy: Simple moving-average (SMA) crossover (fast=20, slow=50 by default)
- Fees: ~1 bps (0.0001) per notional traded
- Slippage: Fixed 1 tick per order (fill price adjusted by +/- one tick)
- Size: Fixed position size of 1 unit per signal
- EOD Action: Flatten all positions at end of each trading day
- Outputs:
  * Trades list (stdout)
  * Total PnL (stdout)
  * Max Drawdown (stdout)
  * Daily Sharpe Ratio (stdout)
  * Equity Curve CSV written to equity_curve.csv

Note about Nautilus Trader usage:
- This runner is self-contained and deterministic.
- If you have Nautilus Trader installed, see the commented example below showing how
  to configure the BacktestEngine with fees, slippage, and EOD flat. You can wire the
  same SMA signals into Nautilus for execution and still reuse the metrics computation
  in this file against generated fills.

Example Nautilus Trader setup (pseudo-code, modern imports):
----------------------------------------------------------------
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.core.datetime import to_unix_nanos
# Fee model and slippage models vary by version; an example configuration:
config = BacktestEngineConfig(
    starting_balances={"USD": 1_000_000},
    # Configure slippage and fee models in your version of Nautilus Trader, e.g.:
    # fee_model=FixedBpsFeeModel(bps=1.0),  # 1 bps
    # slippage_model=FixedTickSlippageModel(ticks=1),
    # eod_flat=True,
)
engine = BacktestEngine(config)
# Load your OHLCV into engine's data store, register instruments, etc.
# Add your strategy instance to the engine and run.
----------------------------------------------------------------

Because Nautilus Trader evolves, consult its current docs for exact fee/slippage config API.
This file ensures you have a working, deterministic alternative today.
"""

from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import List, Optional, Tuple


@dataclass
class Trade:
    timestamp: datetime
    side: str  # "BUY" or "SELL"
    qty: float
    price: float  # execution price incl. slippage
    fee: float    # positive cost


class SMACrossoverBacktester:
    def __init__(
        self,
        fast: int = 20,
        slow: int = 50,
        fee_bps: float = 1.0,  # 1 bps
        tick_size: float = 0.01,
        size: float = 1.0,
        tz: timezone = timezone.utc,
    ) -> None:
        if fast <= 0 or slow <= 0 or fast >= slow:
            raise ValueError("Expect 0 < fast < slow for SMA crossover")
        self.fast = fast
        self.slow = slow
        self.fee_rate = fee_bps / 10_000.0
        self.tick_size = tick_size
        self.size = size
        self.tz = tz

        self.position: float = 0.0
        self.cash: float = 0.0
        self.equity_curve: List[Tuple[datetime, float]] = []  # (ts, equity)
        self.trades: List[Trade] = []
        self._last_close: Optional[float] = None

        # SMA rolling buffers
        self._fast_buf: List[float] = []
        self._slow_buf: List[float] = []

        # For EOD flattening
        self._current_day: Optional[date] = None

    def _sma(self, buf: List[float], period: int) -> Optional[float]:
        if len(buf) < period:
            return None
        return sum(buf[-period:]) / period

    def _apply_fee(self, notional: float) -> float:
        # Return positive fee cost
        return abs(notional) * self.fee_rate

    def _exec(self, ts: datetime, side: str, price: float, qty: float) -> None:
        # Apply 1-tick slippage in direction of trade
        if side == "BUY":
            fill_price = price + self.tick_size
            self.position += qty
            cash_change = -(fill_price * qty)
        else:  # SELL
            fill_price = price - self.tick_size
            self.position -= qty
            cash_change = +(fill_price * qty)

        fee = self._apply_fee(fill_price * qty)
        self.cash += cash_change - fee
        self.trades.append(Trade(ts, side, qty, fill_price, fee))
        self._last_close = price

    def _mark_to_market(self, price: float) -> float:
        return self.cash + self.position * price

    def _maybe_eod_flat(self, ts: datetime, close_price: float) -> None:
        day = ts.date()
        if self._current_day is None:
            self._current_day = day
            return
        if day != self._current_day:
            # EOD flat at the previous bar's close
            if self.position != 0.0 and self._last_close is not None:
                side = "SELL" if self.position > 0 else "BUY"
                self._exec(ts.replace(hour=0, minute=0, second=0, microsecond=0), side, close_price, abs(self.position))
            self._current_day = day

    def on_bar(self, ts: datetime, close: float) -> None:
        # Update rolling windows for SMA
        self._fast_buf.append(close)
        self._slow_buf.append(close)

        # EOD flattening check (based on calendar day change)
        self._maybe_eod_flat(ts, close)

        fast_sma = self._sma(self._fast_buf, self.fast)
        slow_sma = self._sma(self._slow_buf, self.slow)

        if fast_sma is not None and slow_sma is not None:
            # Generate crossover signals
            if self.position <= 0 and fast_sma > slow_sma:
                # Go long 1
                self._exec(ts, "BUY", close, self.size)
            elif self.position >= 0 and fast_sma < slow_sma:
                # Go flat if long, or short if desired (here: flat only)
                if self.position > 0:
                    self._exec(ts, "SELL", close, self.position)
                # If you want to allow going short, uncomment:
                # else:
                #     self._exec(ts, "SELL", close, self.size)

        # Mark-to-market equity at bar close
        equity = self._mark_to_market(close)
        self.equity_curve.append((ts, equity))
        self._last_close = close

    def finalize(self) -> None:
        # Final EOD flat at the last observed close
        if self.position != 0.0 and self._last_close is not None:
            ts = self.equity_curve[-1][0] if self.equity_curve else datetime.now(self.tz)
            side = "SELL" if self.position > 0 else "BUY"
            self._exec(ts, side, self._last_close, abs(self.position))
            # Update final equity snapshot
            self.equity_curve.append((ts, self._mark_to_market(self._last_close)))

    # --- Metrics ---
    def total_pnl(self) -> float:
        if not self.equity_curve:
            return 0.0
        start_equity = 0.0
        end_equity = self.equity_curve[-1][1]
        return end_equity - start_equity

    def max_drawdown(self) -> float:
        max_eq = -float("inf")
        max_dd = 0.0
        for _, eq in self.equity_curve:
            if eq > max_eq:
                max_eq = eq
            dd = max_eq - eq
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def daily_sharpe(self) -> float:
        # Aggregate equity by day, then compute daily returns
        if len(self.equity_curve) < 2:
            return 0.0
        by_day = {}
        for ts, eq in self.equity_curve:
            d = ts.date()
            by_day[d] = eq  # last equity per day
        days = sorted(by_day.keys())
        if len(days) < 2:
            return 0.0
        daily_vals = [by_day[d] for d in days]
        rets = []
        for i in range(1, len(daily_vals)):
            prev, cur = daily_vals[i - 1], daily_vals[i]
            if prev != 0:
                rets.append((cur - prev) / abs(prev))
        if not rets:
            return 0.0
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1) if len(rets) > 1 else 0.0
        std = math.sqrt(var)
        if std == 0:
            return 0.0
        # Annualize with sqrt(252)
        return (mean / std) * math.sqrt(252)

    def save_equity_curve(self, path: str = "equity_curve.csv") -> None:
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "equity"])
            for ts, eq in self.equity_curve:
                w.writerow([ts.isoformat(), f"{eq:.8f}"])


# --- CSV ingestion ---

def read_ohlcv_csv(path: str) -> List[Tuple[datetime, float]]:
    """Read OHLCV CSV and return list of (timestamp, close) in ascending time order.

    Expected columns (header order flexible; autodetected if headers exist):
    - timestamp (or time, datetime): epoch seconds or ISO8601 string
    - open, high, low, close, volume
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    rows: List[Tuple[datetime, float]] = []
    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        # Attempt to detect header names
        lower = [h.strip().lower() for h in header]
        if "close" not in lower:
            # If no header, treat first row as data; reset
            f.seek(0)
            reader = csv.reader(f)
            header = None
        else:
            ts_idx = next((i for i, h in enumerate(lower) if h in ("timestamp", "time", "datetime")), 0)
            close_idx = lower.index("close")

        for i, row in enumerate(reader):
            if not row:
                continue
            if header is None and i == 0:
                # Try parse as no-header line
                # Assume format: timestamp,open,high,low,close,volume
                try:
                    ts_raw = row[0]
                    ts = _parse_timestamp(ts_raw)
                    close = float(row[4])
                except Exception:
                    continue
            else:
                try:
                    ts_raw = row[ts_idx]
                    ts = _parse_timestamp(ts_raw)
                    close = float(row[close_idx])
                except Exception:
                    continue
            rows.append((ts, close))

    rows.sort(key=lambda x: x[0])
    return rows


def _parse_timestamp(val: str) -> datetime:
    val = val.strip()
    # Try epoch seconds
    try:
        if "." in val:
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        return datetime.fromtimestamp(int(val), tz=timezone.utc)
    except Exception:
        pass
    # Try ISO8601
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except Exception:
        raise ValueError(f"Unrecognized timestamp: {val}")


# --- Runner ---

def run_backtest(
    csv_path: str = "ohlcv.csv",
    fast: int = 20,
    slow: int = 50,
    fee_bps: float = 1.0,
    tick_size: float = 0.01,
    size: float = 1.0,
) -> None:
    data = read_ohlcv_csv(csv_path)
    bt = SMACrossoverBacktester(
        fast=fast,
        slow=slow,
        fee_bps=fee_bps,
        tick_size=tick_size,
        size=size,
    )

    for ts, close in data:
        bt.on_bar(ts, close)

    bt.finalize()

    # Save equity curve CSV
    bt.save_equity_curve("equity_curve.csv")

    # Print trades and summary
    print("==== Trades ====")
    for t in bt.trades:
        print(f"{t.timestamp.isoformat()}\t{t.side}\tqty={t.qty}\tprice={t.price:.6f}\tfee={t.fee:.8f}")

    total = bt.total_pnl()
    mdd = bt.max_drawdown()
    sharpe = bt.daily_sharpe()

    print("\n==== Summary ====")
    print(f"Total PnL: {total:.6f}")
    print(f"Max Drawdown: {mdd:.6f}")
    print(f"Daily Sharpe Ratio: {sharpe:.6f}")
    print("Equity curve written to equity_curve.csv")


if __name__ == "__main__":
    run_backtest()
