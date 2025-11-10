("""Tests for indicators module: SMA and RSI.

We focus on correctness for several key RSI scenarios and basic SMA sanity.
Using pytest function tests for simplicity.
""")

from collections import deque
import math

from indicators import calculate_sma, calculate_rsi


def test_rsi_flat_data_returns_50():
	prices = deque([10.0] * 30)
	assert calculate_rsi(prices, period=14) == 50.0


def test_rsi_insufficient_data_returns_50():
	prices = deque([10.0 + i for i in range(10)])  # fewer than period+1
	assert calculate_rsi(prices, period=14) == 50.0


def test_rsi_rising_trend_near_100():
	# Strictly rising so losses = 0, RSI should be 100.
	prices = deque([float(i) for i in range(1, 40)])
	rsi_val = calculate_rsi(prices, period=14)
	assert rsi_val == 100.0


def test_rsi_mixed_sequence_matches_manual_calc():
	# Provide exactly period+1 prices for an initial RSI computation.
	period = 14
	prices = deque([
		44.0, 44.0, 45.0, 43.0, 44.0, 45.0, 44.0, 46.0, 45.0, 47.0, 46.0, 46.0, 47.0, 46.0, 48.0
	])  # length = 15 -> period+1
	rsi_val = calculate_rsi(prices, period=period)

	# Manual average gain/loss over first period deltas (no smoothing step since only initial window)
	closes = list(prices)
	deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
	gains = [max(d, 0.0) for d in deltas[:period]]
	losses = [max(-d, 0.0) for d in deltas[:period]]
	avg_gain = sum(gains) / period
	avg_loss = sum(losses) / period
	if avg_loss == 0:
		expected = 100.0 if avg_gain > 0 else 50.0
	elif avg_gain == 0:
		expected = 0.0
	else:
		rs = avg_gain / avg_loss
		expected = 100.0 - 100.0 / (1.0 + rs)

	# Allow small floating tolerance
	assert math.isclose(rsi_val, expected, rel_tol=1e-6, abs_tol=1e-6)


def test_sma_basic():
	prices = deque([1, 2, 3, 4, 5])
	assert calculate_sma(prices, period=5) == 3.0
	# Insufficient data returns last price
	assert calculate_sma(prices, period=10) == 5.0
