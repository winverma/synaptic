"""Lightweight trading indicators optimized for deque inputs.

This module provides Simple Moving Average (SMA) and Relative Strength Index (RSI)
calculations that accept a ``collections.deque[float]`` of prices. Implementations
are designed to be simple and fast enough for low-latency environments where the
current value is computed on demand.

Notes on efficiency:
- With only a price deque (and no persistent state passed between calls), we compute
  the current values in a single linear pass over the necessary portion of the deque.
- For even lower latency, consider maintaining rolling sums (for SMA) and previous
  average gain/loss (for RSI) in your service and pass them in to avoid recomputation.
"""

from collections import deque
from typing import Tuple


def calculate_sma(prices: deque[float], period: int) -> float:
    """Compute the Simple Moving Average (SMA) of the last ``period`` prices.

    Contract:
    - Input: prices as ``deque[float]``, ``period`` > 0
    - Output: float SMA for the trailing window
    - Edge cases: If there aren't enough prices, return a neutral value: the last
      observed price if available, else 0.0. This avoids biasing signals toward 0.

    Rationale for neutral choice: returning the last price preserves the most recent
    market information without fabricating momentum.
    """
    if period <= 0:
        raise ValueError("period must be > 0")

    n = len(prices)
    if n == 0:
        return 0.0
    if n < period:
        # Not enough data: return the most recent price as a neutral proxy.
        return float(prices[-1])

    # Sum the last `period` prices in a single pass without copying the full deque.
    start_index = n - period
    total = 0.0
    for i, p in enumerate(prices):
        if i >= start_index:
            total += float(p)
    return total / period


def calculate_rsi(prices: deque[float], period: int = 14) -> float:
    """Compute the Relative Strength Index (RSI) using Wilder's smoothing.

    - Uses standard RSI definition:
      1) Compute average gain and loss over the first ``period`` deltas (SMA).
      2) For each subsequent delta, update the averages via Wilder's smoothing:
         avg_gain = (prev_avg_gain*(period-1) + gain) / period
         avg_loss = (prev_avg_loss*(period-1) + loss) / period
    - Returns 50.0 if insufficient data (fewer than ``period+1`` prices).
    - Result is clipped to [0, 100].

    Note: Without carrying state between calls, we walk the deque once. For very
    high-frequency usage, store and reuse the previous averages externally.
    """
    if period <= 0:
        raise ValueError("period must be > 0")

    if len(prices) < period + 1:
        return 50.0  # Neutral when data is insufficient

    closes = list(float(x) for x in prices)

    # Compute deltas between consecutive closes
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Initial averages from the first `period` deltas using simple mean
    gains = [max(d, 0.0) for d in deltas[:period]]
    losses = [max(-d, 0.0) for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder smoothing for remaining deltas (if any)
    for d in deltas[period:]:
        gain = max(d, 0.0)
        loss = max(-d, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    # Convert averages to RSI
    if avg_loss == 0.0:
        if avg_gain == 0.0:
            rsi = 50.0  # flat market
        else:
            rsi = 100.0
    elif avg_gain == 0.0:
        rsi = 0.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - 100.0 / (1.0 + rs)

    # Bound the value strictly to [0, 100]
    if rsi < 0.0:
        rsi = 0.0
    elif rsi > 100.0:
        rsi = 100.0
    return rsi


def determine_trend_and_decision(prices: deque[float]) -> Tuple[str, str, float]:
    """Apply a simple MA(20/50) + RSI(14) rule to generate a decision.

    Returns (trend, decision, rsi):
    - trend: "UP" | "DOWN" | "FLAT"
    - decision: "BUY" | "SELL" | "HOLD"
    - rsi: current RSI(14)
    """
    rsi_val = calculate_rsi(prices, period=14)
    ma_short = calculate_sma(prices, period=20)
    ma_long = calculate_sma(prices, period=50)

    trend = "FLAT"
    decision = "HOLD"

    if ma_short > ma_long:
        trend = "UP"
        if rsi_val < 30.0:  # Potential oversold in uptrend
            decision = "BUY"
    elif ma_short < ma_long:
        trend = "DOWN"
        if rsi_val > 70.0:  # Potential overbought in downtrend
                decision = "SELL"

    return trend, decision, rsi_val
