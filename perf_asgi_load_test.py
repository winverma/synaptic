import asyncio
import statistics
import time

from httpx import AsyncClient, ASGITransport
from main import app


async def run_asgi_load(qps: int = 100, duration_s: int = 10):
    total = qps * duration_s
    latencies = []
    errors = 0

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.perf_counter()
            next_deadline = start
            for _ in range(total):
                next_deadline += 1.0 / qps
                now = time.perf_counter()
                sleep_s = next_deadline - now
                if sleep_s > 0:
                    await asyncio.sleep(sleep_s)
                t0 = time.perf_counter()
                try:
                    r = await client.get("/signal", params={"symbol": "XYZ"})
                    r.raise_for_status()
                    latencies.append((time.perf_counter() - t0) * 1000.0)
                except Exception:
                    errors += 1
            end = time.perf_counter()

    latencies.sort()
    p95 = latencies[max(int(0.95 * len(latencies)) - 1, 0)] if latencies else None
    return {
        "requests": len(latencies) + errors,
        "success": len(latencies),
        "errors": errors,
        "duration_s": end - start,
        "achieved_qps": (len(latencies) + errors) / (end - start) if end > start else 0.0,
        "min_ms": latencies[0] if latencies else None,
        "mean_ms": statistics.fmean(latencies) if latencies else None,
        "p95_ms": p95,
        "max_ms": latencies[-1] if latencies else None,
    }


async def main():
    res = await run_asgi_load()
    lines = [
        "==== T1 Perf Note ====",
        "Tool: httpx ASGITransport (in-process) paced 100 QPS for 10s",
        "Endpoint: GET /signal?symbol=XYZ",
    ]
    for k, v in res.items():
        lines.append(f"{k}: {v}")
    note = "\n".join(lines)
    print(note)
    with open("docs/t1_perf_note.txt", "w") as f:
        f.write(note + "\n")


if __name__ == "__main__":
    asyncio.run(main())
