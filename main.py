# src/main.py
import asyncio
from typing import List
from fastapi import FastAPI, WebSocket, HTTPException, status
from starlette.websockets import WebSocketDisconnect

# Import the provided price stream stub and your logic
from stream_stub import price_stream, Tick
from models import GLOBAL_STATE, SymbolState, SignalResponse
from indicators import determine_trend_and_decision

# --- INITIAL SETUP ---
# List of symbols the service should track
SYMBOLS_TO_TRACK = ("XYZ", "ABC", "DEF") 
# Initialize the global state for tracked symbols
for sym in SYMBOLS_TO_TRACK:
    GLOBAL_STATE[sym] = SymbolState()

app = FastAPI(title="Synaptic Trading Signal Service")

# --- 1) ASYNC CONSUMER TASK (Runs in the background) ---

async def price_consumer_task(symbols: List[str]):
    """
    Async consumer updating the rolling state[cite: 18].
    This task runs continuously in the background.
    """
    print(f"Starting price consumer for symbols: {symbols}")
    try:
        # Use the provided stream_stub to ingest simulated prices [cite: 17]
        async for tick in price_stream(symbols=symbols, interval_ms=50):
            state = GLOBAL_STATE.get(tick.symbol)
            if state:
                state.add_price(tick.price)
                
                # Re-calculate and update latest signal on every tick
                trend, decision, rsi = determine_trend_and_decision(state.prices)
                state.latest_trend = trend
                state.latest_decision = decision
                state.latest_rsi = rsi
                # print(f"Update: {tick.symbol} - {decision} ({rsi:.2f})") # Debug
                
    except asyncio.CancelledError:
        print("Price consumer task cancelled.")

@app.on_event("startup")
async def startup_event():
    # Start the background consumer task when the server starts
    app.state.consumer_task = asyncio.create_task(price_consumer_task(list(SYMBOLS_TO_TRACK)))

@app.on_event("shutdown")
async def shutdown_event():
    # Cancel the background consumer task when the server shuts down
    app.state.consumer_task.cancel()
    await app.state.consumer_task

# --- 2) GET /signal Endpoint ---

@app.get("/signal", response_model=SignalResponse, tags=["Signal"])
async def get_signal(symbol: str):
    """
    Expose a simple trading signal with low latency[cite: 17].
    Returns trend, RSI, and decision via MA(20/50)+RSI(14) rule[cite: 19].
    """
    state = GLOBAL_STATE.get(symbol.upper())
    
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {symbol} not tracked.")
    # Low-latency return: use precomputed values from state
    return SignalResponse(
        symbol=symbol.upper(),
        trend=state.latest_trend,
        rsi=state.latest_rsi,
        decision=state.latest_decision,
    )

# --- 3) WS /ws/signal Endpoint ---

@app.websocket("/ws/signal/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    """
    Streaming the latest decision via WebSocket[cite: 20].
    """
    await websocket.accept()
    state = GLOBAL_STATE.get(symbol.upper())
    if not state:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=f"Symbol {symbol} not tracked.")
        return

    # In a real system, you'd use a pub/sub pattern (like Redis/Kafka) 
    # to fan out updates. For this evaluation, we can poll the state 
    # or implement a simpler notifier (better for performance).

    # For the boilerplate, we'll use a simple polling loop.
    try:
        # Send an initial snapshot immediately so clients receive something on connect
        last_decision = state.latest_decision
        await websocket.send_json({
            "symbol": symbol.upper(),
            "decision": last_decision,
        })
        while True:
            # Check for a change in decision
            current_decision = state.latest_decision
            if current_decision != last_decision:
                # Send the latest decision when it changes
                await websocket.send_json({"symbol": symbol.upper(), "decision": current_decision})
                last_decision = current_decision
                
            # Sleep briefly to avoid high CPU usage from constant polling
            await asyncio.sleep(0.1) 
            
    except WebSocketDisconnect:
        print(f"Client disconnected from {symbol} WebSocket.")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Attempt graceful close if still connected
        try:
            await websocket.close()
        except Exception:
            pass