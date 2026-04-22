"""Market data access via ccxt public endpoints (no API key required).

Supports a fallback list of exchanges so it keeps working from regions where
some exchanges (e.g. Binance from US-routed Colab IPs) return HTTP 451.
"""
from __future__ import annotations

import sys
from typing import Iterable

import ccxt
import pandas as pd


def _as_list(x) -> list[str]:
    if isinstance(x, str):
        return [x]
    return list(x)


class MarketData:
    def __init__(
        self,
        spot_ids: str | Iterable[str] = ("kraken", "coinbase", "bitstamp", "binance"),
        futures_ids: str | Iterable[str] = ("bybit", "binanceusdm"),
        futures_symbol: str | None = None,
    ):
        self._spot_ids = _as_list(spot_ids)
        self._futures_ids = _as_list(futures_ids)
        self._spot: ccxt.Exchange | None = None
        self._futures: ccxt.Exchange | None = None
        self._futures_unavailable = False  # latch off after first full failure
        self.futures_symbol = futures_symbol

    @staticmethod
    def _try_exchange(ex_id: str) -> ccxt.Exchange:
        ex = getattr(ccxt, ex_id)({"enableRateLimit": True})
        ex.load_markets()
        return ex

    def _pick(self, ids: list[str], kind: str) -> ccxt.Exchange:
        last_err: Exception | None = None
        for ex_id in ids:
            try:
                ex = self._try_exchange(ex_id)
                print(f"[data] using {kind} exchange: {ex_id}", file=sys.stderr)
                return ex
            except Exception as exc:
                last_err = exc
                print(f"[data] {kind} exchange {ex_id} unavailable: "
                      f"{exc.__class__.__name__}", file=sys.stderr)
        raise RuntimeError(f"no {kind} exchange available; last error: {last_err}")

    @property
    def spot(self) -> ccxt.Exchange:
        if self._spot is None:
            self._spot = self._pick(self._spot_ids, "spot")
        return self._spot

    @property
    def futures(self) -> ccxt.Exchange:
        if self._futures is None:
            self._futures = self._pick(self._futures_ids, "futures")
        return self._futures

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
        if self._futures_unavailable:
            return None
        sym = self.futures_symbol or symbol
        try:
            fr = self.futures.fetch_funding_rate(sym)
            return float(fr.get("fundingRate") or 0.0)
        except Exception as exc:
            if self._futures is None:
                # All futures exchanges failed at init; latch off.
                self._futures_unavailable = True
                print(f"[data] funding rate disabled: {exc.__class__.__name__}",
                      file=sys.stderr)
            return None
