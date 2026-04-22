"""Market data access via ccxt public endpoints (no API key required)."""
from __future__ import annotations

import ccxt
import pandas as pd


class MarketData:
    def __init__(self, spot_id: str = "binance", futures_id: str = "binanceusdm"):
        self.spot = getattr(ccxt, spot_id)({"enableRateLimit": True})
        self.futures = getattr(ccxt, futures_id)({"enableRateLimit": True})

    def ohlcv(self, symbol: str, timeframe: str = "5m", limit: int = 300) -> pd.DataFrame:
        rows = self.spot.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        return df.set_index("ts")

    def order_book(self, symbol: str, depth: int = 50) -> dict:
        return self.spot.fetch_order_book(symbol, limit=depth)

    def recent_trades(self, symbol: str, limit: int = 200) -> list[dict]:
        return self.spot.fetch_trades(symbol, limit=limit)

    def funding_rate(self, symbol: str) -> float | None:
        try:
            fr = self.futures.fetch_funding_rate(symbol)
            return float(fr.get("fundingRate") or 0.0)
        except Exception:
            return None
