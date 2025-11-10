# tests/template_test.py
# Pytest-style template tests. Extend with your own indicator and equity checks.

from pathlib import Path
import csv

BASE = Path(__file__).resolve().parents[1]

def test_csv_has_expected_columns():
    csv_path = BASE / "ohlcv.csv"
    assert csv_path.exists(), "ohlcv.csv is missing"
    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        headers = next(reader)
    for col in ["timestamp","open","high","low","close","volume"]:
        assert col in headers, f"Missing column: {col}"

def test_placeholder_equity_curve_reproducible():
    # TODO: Replace with a real check once your runner is implemented.
    # Example:
    #   ec1 = run_strategy(seed=123)
    #   ec2 = run_strategy(seed=123)
    #   assert list(ec1) == list(ec2)
    assert True
