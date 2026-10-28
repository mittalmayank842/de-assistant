# Layers and Tables

## Bronze
Raw API data stored as Delta tables with lineage columns `_run_id`, `_source` and `_ingested_at`.
Tables: `bronze.markets`, `bronze.price_history`, `bronze.ohlc`, `bronze.global`, `bronze.trending`.
Bronze is append-only, so every run is kept for audit and replay.

## Silver
Typed, deduplicated and quality-checked data.
- `silver.daily_prices` — one row per coin per day (deduplicated on coin_id + date).
- `silver.candles` — 4-hour OHLC candles (deduplicated on coin_id + timestamp).
- `silver.coins` — one row per coin with name, symbol, rank and current price.
- `silver._quarantine` — rows that failed a data-quality rule, with the rule name.

## Gold
Analytics computed with Spark window functions.
- `gold.daily_metrics` — daily return, log return, 7-day and 30-day moving averages,
  30-day annualised volatility (stddev of log returns x sqrt(365)), and whether price is above its 30-day average.
  Partitioned by coin_id.
- `gold.candle_signals` — candlestick patterns: doji, hammer, bullish engulfing, bearish engulfing.

## Platinum
Small, business-ready tables for dashboards.
- `platinum.coin_scorecard` — latest price, 7-day and 30-day return, volatility, risk band (low/medium/high) and rank.
- `platinum.movers` — top 5 gainers and top 5 losers over 7 days.
- `platinum.pattern_counts` — how often each candlestick pattern fired per coin.
