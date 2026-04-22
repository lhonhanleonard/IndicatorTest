"""Order flow signals: what other participants are doing right now."""
from __future__ import annotations

import time


def book_imbalance(book: dict, depth: int = 20) -> float:
    """Top-N bid size vs ask size. +1 = aggressive bids, -1 = aggressive asks."""
    bids = sum(q for _, q in book.get("bids", [])[:depth])
    asks = sum(q for _, q in book.get("asks", [])[:depth])
    total = bids + asks
    if total <= 0:
        return 0.0
    return max(-1.0, min(1.0, (bids - asks) / total))


def trade_tape(trades: list[dict], window_seconds: int = 300) -> float:
    """Aggressive buy vs sell volume over the recent window."""
    cutoff_ms = (time.time() - window_seconds) * 1000
    buy_vol = sell_vol = 0.0
    for t in trades:
        ts = t.get("timestamp") or 0
        if ts < cutoff_ms:
            continue
        amount = float(t.get("amount") or 0)
        if t.get("side") == "buy":
            buy_vol += amount
        elif t.get("side") == "sell":
            sell_vol += amount
    total = buy_vol + sell_vol
    if total <= 0:
        return 0.0
    return max(-1.0, min(1.0, (buy_vol - sell_vol) / total))


def funding_signal(rate: float | None) -> float:
    """Extreme funding -> contrarian bias (crowded longs often flush)."""
    if rate is None:
        return 0.0
    # Typical 8h funding on majors sits near 0.0001 (0.01%).
    # Treat >0.05% as crowded long (short bias), <-0.05% as crowded short (long bias).
    if rate > 0.0005:
        return -min(1.0, rate / 0.001)
    if rate < -0.0005:
        return min(1.0, -rate / 0.001)
    return 0.0
