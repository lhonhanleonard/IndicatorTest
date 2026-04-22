"""Technical indicators computed with pandas/numpy (no TA-Lib dependency)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def bollinger(close: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    mid = close.rolling(length).mean()
    sd = close.rolling(length).std()
    return pd.DataFrame({"mid": mid, "upper": mid + std * sd, "lower": mid - std * sd})


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift()
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def vwap(df: pd.DataFrame) -> pd.Series:
    """Rolling session VWAP reset at each UTC day boundary."""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    pv = tp * df["volume"]
    day = df.index.floor("D")
    cum_pv = pv.groupby(day).cumsum()
    cum_v = df["volume"].groupby(day).cumsum()
    return cum_pv / cum_v.replace(0, np.nan)


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema9"] = ema(df["close"], 9)
    out["ema21"] = ema(df["close"], 21)
    out["ema50"] = ema(df["close"], 50)
    out["rsi"] = rsi(df["close"], 14)
    m = macd(df["close"])
    out["macd"] = m["macd"]
    out["macd_signal"] = m["signal"]
    out["macd_hist"] = m["hist"]
    b = bollinger(df["close"])
    out["bb_mid"] = b["mid"]
    out["bb_upper"] = b["upper"]
    out["bb_lower"] = b["lower"]
    out["atr"] = atr(df)
    out["vwap"] = vwap(df)
    return out
