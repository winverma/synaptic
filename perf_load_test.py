import statistics
import time
from typing import List
import httpx


def run_load_test(host: str = "http://127.0.0.1:8001", endpoint: str = "/signal", symbol: str = "XYZ", qps: int = 100, duration_s: int = 10) -> dict:
    """Run a paced synchronous load test approximating qps for duration.

    Shortened duration (default 10s) to keep evaluation quick; adjust as needed.
    """
    total_requests = qps * duration_s
    latencies_ms: List[float] = []
    errors = 0
    start = time.perf_counter()
    next_deadline = start
    with httpx.Client(base_url=host, timeout=2.0) as client:
        for i in range(total_requests):
            # Pace requests to target QPS
            next_deadline += 1.0 / qps
            now = time.perf_counter()
            sleep_s = next_deadline - now
            if sleep_s > 0:
                time.sleep(sleep_s)
            t0 = time.perf_counter()
            try:
                r = client.get(endpoint, params={"symbol": symbol})
                r.raise_for_status()
                lat_ms = (time.perf_counter() - t0) * 1000.0
                latencies_ms.append(lat_ms)
            except Exception:
                errors += 1
    end = time.perf_counter()

    if latencies_ms:
        latencies_ms.sort()
        p95_index = max(int(0.95 * len(latencies_ms)) - 1, 0)
        p95 = latencies_ms[p95_index]
        metrics = {
            "requests": len(latencies_ms) + errors,
            "success": len(latencies_ms),
            "errors": errors,
            "duration_s": end - start,
            "achieved_qps": (len(latencies_ms) + errors) / (end - start),
            "min_ms": latencies_ms[0],
            "mean_ms": statistics.fmean(latencies_ms),
            "p95_ms": p95,
            "max_ms": latencies_ms[-1],
        }
    else:
        metrics = {
            "requests": 0,
            "success": 0,
            "errors": errors,
            "duration_s": 0.0,
            "achieved_qps": 0.0,
            "min_ms": None,
            "mean_ms": None,
            "p95_ms": None,
            "max_ms": None,
        }
    return metrics


def main():
    metrics = run_load_test()
    lines = ["==== T1 Perf Note ====",
             "Tool: custom paced httpx client (approx 100 QPS for 10s)",
             "Endpoint: GET /signal?symbol=XYZ"]
    for k, v in metrics.items():
        lines.append(f"{k}: {v}")
    note = "\n".join(lines)
    print(note)
    try:
        with open("docs/t1_perf_note.txt", "w") as f:
            f.write(note + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
