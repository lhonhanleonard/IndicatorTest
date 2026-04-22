"""BTC 5m scalping signal aggregator. Signals only — no order execution."""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict
from pathlib import Path

import yaml

from . import patterns, orderflow
from .data import MarketData
from .indicators import enrich
from .news import NewsFeed, aggregate_sentiment
from .signals import build_decision


ROOT = Path(__file__).resolve().parent.parent


def setup_logging(log_dir: Path) -> tuple[logging.Logger, Path]:
    log_dir.mkdir(parents=True, exist_ok=True)
    text_path = log_dir / "signals.log"
    jsonl_path = log_dir / "signals.jsonl"

    logger = logging.getLogger("scalper")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(text_path)
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger, jsonl_path


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def evaluate_once(cfg: dict, market: MarketData, news: NewsFeed):
    symbol = cfg["symbol"]

    df = enrich(market.ohlcv(symbol, cfg["timeframe"], cfg["ohlcv_limit"]))
    book = market.order_book(symbol, cfg["orderbook_depth"])
    trades = market.recent_trades(symbol, cfg["trades_limit"])
    funding = market.funding_rate(symbol)
    headlines = news.fetch(cfg["news"]["lookback_minutes"])
    news_score = aggregate_sentiment(headlines)

    components = {
        "ema_trend": patterns.ema_trend(df),
        "ema_cross": patterns.ema_cross(df),
        "rsi": patterns.rsi_signal(df),
        "macd": patterns.macd_signal(df),
        "bollinger": patterns.bollinger_signal(df),
        "vwap": patterns.vwap_signal(df),
        "engulfing": patterns.engulfing(df),
        "book_imbalance": orderflow.book_imbalance(book),
        "trade_tape": orderflow.trade_tape(trades),
        "funding": orderflow.funding_signal(funding),
        "news": news_score,
    }

    notes = []
    if headlines:
        top = max(headlines, key=lambda h: abs(h.sentiment))
        notes.append(f"news({len(headlines)}): \"{top.title[:90]}\" ({top.sentiment:+.2f})")
    if funding is not None:
        notes.append(f"funding={funding:+.4%}")

    last = df.iloc[-1]
    decision = build_decision(
        components=components,
        weights=cfg["weights"],
        price=float(last["close"]),
        atr_value=float(last["atr"]),
        enter=cfg["thresholds"]["enter"],
        strong=cfg["thresholds"]["strong"],
        stop_mult=cfg["risk"]["atr_stop_mult"],
        target_mult=cfg["risk"]["atr_target_mult"],
        notes=notes,
    )
    return decision, df.index[-1]


def format_line(decision, candle_ts) -> str:
    parts = [
        f"[{candle_ts:%Y-%m-%d %H:%M}]",
        f"{decision.action:>5}",
        f"score={decision.score:+.2f}",
        f"conf={decision.confidence}",
        f"px={decision.price:.2f}",
    ]
    if decision.action != "FLAT":
        parts.append(f"stop={decision.stop:.2f}")
        parts.append(f"tp={decision.target:.2f}")
    comp_str = " ".join(f"{k}={v:+.2f}" for k, v in decision.components.items())
    parts.append(f"| {comp_str}")
    if decision.notes:
        parts.append("| " + " ; ".join(decision.notes))
    return " ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="BTC 5m scalping signal aggregator")
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    parser.add_argument("--once", action="store_true", help="Run one evaluation and exit")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    logger, jsonl_path = setup_logging(ROOT / "logs")

    market = MarketData(cfg["exchange"], cfg["futures_exchange"])
    news = NewsFeed(cfg["news"]["rss_url"], cfg["news"]["keywords"])

    logger.info("starting | symbol=%s tf=%s loop=%ss",
                cfg["symbol"], cfg["timeframe"], cfg["loop_seconds"])

    while True:
        try:
            decision, ts = evaluate_once(cfg, market, news)
            logger.info(format_line(decision, ts))
            with open(jsonl_path, "a") as jf:
                jf.write(json.dumps({"ts": ts.isoformat(), **asdict(decision)}) + "\n")
        except KeyboardInterrupt:
            logger.info("stopped by user")
            break
        except Exception as exc:
            logger.exception("evaluate failed: %s", exc)

        if args.once:
            break
        time.sleep(cfg["loop_seconds"])


if __name__ == "__main__":
    main()
