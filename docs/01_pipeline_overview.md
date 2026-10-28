# Crypto Market Data Pipeline — Overview

## Purpose
The pipeline collects cryptocurrency market data from the CoinGecko public API and turns it into
analytics tables for dashboards. It tracks the top 50 coins by market capitalisation.

## Schedule and SLA
The pipeline runs once a day. The freshness SLA is 24 hours: the newest successful run must have
finished within the last 24 hours, otherwise the platinum tables are considered stale and dashboards
should show a warning.

## Layers
Data moves through a medallion architecture with four layers stored as Delta Lake tables:
landing (raw JSON) -> bronze -> silver -> gold -> platinum.

## Source endpoints
Five CoinGecko endpoints are called on every run:
- `/coins/markets` — current snapshot of the top 50 coins
- `/coins/{id}/market_chart` — 180 days of daily price, market cap and volume
- `/coins/{id}/ohlc` — 30 days of 4-hour candles
- `/global` — total market cap and BTC/ETH dominance
- `/search/trending` — coins currently trending in search

## How to run
`python -m crypto_pipeline.pipeline` fetches fresh data and processes every layer.
`python -m crypto_pipeline.pipeline --reuse` skips the API and reprocesses the newest landed run.
