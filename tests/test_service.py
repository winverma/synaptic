"""Async endpoint tests for the trading signal service.

Covers:
- GET /signal returns a successful response with required fields.
- WS /ws/signal sends a message containing the 'decision' field.

We use httpx.AsyncClient for the HTTP test and FastAPI TestClient for WebSocket.
"""

import asyncio
import time
from typing import Set

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from contextlib import asynccontextmanager

from main import app


@pytest.mark.asyncio
async def test_get_signal_endpoint_returns_structure():
	# Manually run lifespan to start background tasks for AsyncClient usage
	async with app.router.lifespan_context(app):
		transport = ASGITransport(app=app)
		async with AsyncClient(transport=transport, base_url="http://test") as client:
			await asyncio.sleep(0.3)
			resp = await client.get("/signal", params={"symbol": "XYZ"})
			assert resp.status_code == 200, resp.text
			data = resp.json()
			assert set(["symbol", "trend", "rsi", "decision"]).issubset(set(data.keys()))
			assert data["symbol"] == "XYZ"
			assert data["trend"] in {"UP", "DOWN", "FLAT"}
			assert 0.0 <= float(data["rsi"]) <= 100.0
			assert data["decision"] in {"BUY", "SELL", "HOLD"}


def test_websocket_signal_sends_decision_message():
	# Use TestClient which provides WebSocket testing utilities
	with TestClient(app) as client:
		# Let the consumer produce at least one tick
		time.sleep(0.2)
		with client.websocket_connect("/ws/signal/XYZ") as ws:
			# We send an initial snapshot on connect, so a message should be available promptly
			message = ws.receive_json()
			assert "decision" in message
			assert message.get("symbol") == "XYZ"
