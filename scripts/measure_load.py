#!/usr/bin/env python3
"""Measure local request latency and report an explicit zero API-cost baseline."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen


def request(url: str, payload: bytes) -> tuple[float, int]:
    started = time.perf_counter()
    with urlopen(Request(url, data=payload, headers={"content-type": "application/json"}), timeout=10) as response:
        response.read()
        return (time.perf_counter() - started) * 1000, response.status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/triage")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--cost-per-request-usd", type=float, default=0.0)
    args = parser.parse_args()
    payload = json.dumps(
        {"id": "load-test", "context": [{"speaker": "customer", "text": "My card is not working"}]}
    ).encode()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(lambda _: request(args.url, payload), range(args.requests)))
    latencies = sorted(value for value, status in results if status == 200)
    index = min(len(latencies) - 1, max(0, round(0.95 * len(latencies)) - 1))
    print(
        json.dumps(
            {
                "requests": len(results),
                "concurrency": args.concurrency,
                "successful": len(latencies),
                "p50_ms": round(statistics.median(latencies), 3) if latencies else None,
                "p95_ms": round(latencies[index], 3) if latencies else None,
                "cost_per_message_usd": args.cost_per_request_usd,
                "cost_per_1000_messages_usd": round(args.cost_per_request_usd * 1000, 6),
                "note": "Local CPU/API cost only; host electricity and depreciation are excluded.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()