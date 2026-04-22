# IndicatorTest

BTC 5-minute scalping **signal aggregator** — decision support, not a trading bot.
It pulls free public data, computes a bundle of signals, combines them into a
weighted score, and prints `LONG / SHORT / FLAT` with confidence to the terminal
and a log file. No exchange keys required, no orders sent.

> Disclaimer: nothing here is financial advice. 5m BTC scalping is high-risk.
> Paper-trade and tune weights before risking real money.

## What it looks at

| Bucket         | Inputs                                                                 |
| -------------- | ---------------------------------------------------------------------- |
| Trend          | EMA9 / EMA21 / EMA50 stack, EMA9/21 cross                              |
| Momentum       | RSI(14), MACD(12,26,9) histogram flip                                  |
| Mean reversion | Bollinger band tags, session VWAP reclaim/rejection                    |
| Candles        | Bull / bear engulfing                                                  |
| Order flow     | Top-of-book bid/ask imbalance, recent aggressive buy vs sell tape      |
| Positioning    | Perp funding rate (extremes used as contrarian bias)                   |
| News           | CryptoPanic RSS headlines (last N min) scored with VADER sentiment     |

Each signal emits a score in `[-1, +1]`. The combiner multiplies by the per-signal
weight from `config.yaml`, sums, and compares the absolute value to the enter /
strong thresholds.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Continuous loop (evaluates every `loop_seconds`, default 60s):

```bash
python -m scalper.main
```

One-shot evaluation (useful for cron / quick check):

```bash
python -m scalper.main --once
```

Alternate config:

```bash
python -m scalper.main --config path/to/config.yaml
```

Output goes to the terminal **and** to:

- `logs/signals.log`   — human-readable lines
- `logs/signals.jsonl` — one JSON object per evaluation (easy to replay / backtest)

Example line:

```
[2026-04-22 14:05]  LONG score=+2.14 conf=medium px=64210.50 stop=64020.15 tp=64552.80 | ema_trend=+1.00 ema_cross=+0.00 rsi=+0.40 macd=+0.80 bollinger=+0.00 vwap=+0.80 engulfing=+0.00 book_imbalance=+0.35 trade_tape=+0.50 funding=-0.20 news=+0.30 | news(4): "Spot BTC ETFs see $420m net inflow" (+0.55) ; funding=+0.0300%
```

## Tuning

Edit `config.yaml`:

- **Weights** — raise what you trust, zero out what you don't.
- **Thresholds** — raise `enter` to get fewer, higher-conviction calls.
- **News keywords** — filters the RSS feed to BTC-relevant headlines.
- **Risk** — `atr_stop_mult` / `atr_target_mult` set the stop/target distances
  printed beside each signal (in units of ATR). Adjust to your R:R appetite.

## Suggested workflow

1. Run with `--once` a few times and sanity-check the component breakdown.
2. Let it loop for a day, then open `logs/signals.jsonl` and eyeball how the
   calls align with actual 5m moves.
3. Tweak weights / thresholds. Keep a changelog.
4. Only after the paper record looks reasonable, consider acting on signals.

## Layout

```
scalper/
  data.py         ccxt market data (Binance spot + USDM perps, public)
  indicators.py   EMA / RSI / MACD / Bollinger / ATR / VWAP
  patterns.py     chart pattern scores
  orderflow.py    book imbalance, trade tape, funding
  news.py         CryptoPanic RSS + VADER sentiment
  signals.py      weighted combiner -> Decision
  main.py         loop + logging
```

## Limitations (read me)

- Public data only — no tick-level flow, no aggregated liquidations, no on-chain.
- CryptoPanic RSS is coarse; upgrade to their API or a paid news feed for real
  low-latency headlines.
- Signals are evaluated at wall-clock intervals, not exactly on candle close;
  set `loop_seconds` low (30-60s) if timing matters.
- No backtester yet. The `.jsonl` log is structured so one can be added later.
