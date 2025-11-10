# Nautilus Trader Mini Runner Primer (Synaptic Evaluation)

Use this outline if you choose **Track A (preferred)**. Keep it minimal and reproducible.

## Imports (current)
Make sure you import the backtest engine from the current package path:

```python
from nautilus_trader.backtest.engine import BacktestEngine
```

(Older snippets on the web often show a different path; avoid them.)

## Minimal runner outline
- Load `ohlcv.csv` into a data adapter or in-memory bars.
- Implement the toy rule: MA(20/50) + RSI(14), careful with warm-up (no look-ahead).
- Configure: fees (~1 bps), fixed slippage (1 tick), size=1, EOD flat.
- Output: trades, PnL, max drawdown, daily Sharpe (state convention), equity curve CSV.
- Add a seeded test to reproduce identical equity on a known slice.

## Verification notes to include
- How you verified the import path/API; version info if possible.
- How you ensured no leakage (previous bar values only).
