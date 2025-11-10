# src/models.py
from pydantic import BaseModel
from collections import deque
from typing import List, Literal, Dict
from dataclasses import dataclass

# Data class for incoming stream ticks (matches stream_stub.py output)
@dataclass
class Tick:
    symbol: str
    ts: float        # epoch seconds
    price: float

# The rolling state for one symbol
class SymbolState:
    def __init__(self, max_size: int = 200):
        # A deque to hold a rolling window of prices (for indicators)
        self.prices: deque[float] = deque(maxlen=max_size)
        self.latest_trend: str = "FLAT"
        self.latest_decision: str = "HOLD"
        self.latest_rsi: float = 50.0

    def add_price(self, price: float):
        self.prices.append(price)

# The response model for the GET /signal endpoint
class SignalResponse(BaseModel):
    symbol: str
    trend: Literal["UP", "DOWN", "FLAT"]
    rsi: float  # [0, 100]
    decision: Literal["BUY", "SELL", "HOLD"]

# Global state store, shared across the application (TBD: better concurrency)
# Key: Symbol (str), Value: SymbolState
GLOBAL_STATE: Dict[str, SymbolState] = {}