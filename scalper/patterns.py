"""Chart-reading signals. Each function returns a float score in [-1, +1]."""
from __future__ import annotations

import pandas as pd


def _clip(x: float) -> float:
    return max(-1.0, min(1.0, x))


def ema_trend(df: pd.DataFrame) -> float:
    """Price above EMA21 > EMA50 is bullish stack; below is bearish."""
    last = df.iloc[-1]
    if last["close"] > last["ema21"] > last["ema50"]:
        return 1.0
    if last["close"] < last["ema21"] < last["ema50"]:
        return -1.0
    if last["close"] > last["ema50"]:
        return 0.3
    return -0.3


def ema_cross(df: pd.DataFrame) -> float:
    """EMA9 crossing EMA21 on the last closed candle."""
    a, b = df.iloc[-2], df.iloc[-1]
    if a["ema9"] <= a["ema21"] and b["ema9"] > b["ema21"]:
        return 1.0
    if a["ema9"] >= a["ema21"] and b["ema9"] < b["ema21"]:
        return -1.0
    return 0.0


def rsi_signal(df: pd.DataFrame) -> float:
    r = df["rsi"].iloc[-1]
    if r < 30:
        return _clip((30 - r) / 15)        # oversold -> long bias
    if r > 70:
        return _clip(-(r - 70) / 15)       # overbought -> short bias
    return 0.0


def macd_signal(df: pd.DataFrame) -> float:
    """Histogram sign flip is a momentum trigger."""
    h0, h1 = df["macd_hist"].iloc[-2], df["macd_hist"].iloc[-1]
    if h0 <= 0 < h1:
        return 1.0
    if h0 >= 0 > h1:
        return -1.0
    return _clip(h1 / (df["close"].iloc[-1] * 0.001))   # scaled residual


def bollinger_signal(df: pd.DataFrame) -> float:
    """Mean-reversion: tag the lower band while in range = long bias."""
    last = df.iloc[-1]
    if last["close"] <= last["bb_lower"]:
        return 0.7
    if last["close"] >= last["bb_upper"]:
        return -0.7
    return 0.0


def vwap_signal(df: pd.DataFrame) -> float:
    """Reclaim / rejection of VWAP on the last closed candle."""
    a, b = df.iloc[-2], df.iloc[-1]
    if a["close"] < a["vwap"] and b["close"] > b["vwap"]:
        return 0.8
    if a["close"] > a["vwap"] and b["close"] < b["vwap"]:
        return -0.8
    if b["close"] > b["vwap"]:
        return 0.2
    return -0.2


def engulfing(df: pd.DataFrame) -> float:
    """Simple bull/bear engulfing pattern on the last two candles."""
    a, b = df.iloc[-2], df.iloc[-1]
    a_body = a["close"] - a["open"]
    b_body = b["close"] - b["open"]
    if a_body < 0 and b_body > 0 and b["close"] > a["open"] and b["open"] < a["close"]:
        return 1.0
    if a_body > 0 and b_body < 0 and b["close"] < a["open"] and b["open"] > a["close"]:
        return -1.0
    return 0.0
