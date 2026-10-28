# Data Quality Rules

Silver applies rules to every row. A row that fails is never silently dropped: it is written to
`silver._quarantine` with the name of the rule it broke, so it can be investigated.

## Price rules (silver.daily_prices)
- `price_not_null` — price must be present.
- `price_positive` — price must be greater than zero.
- `volume_non_negative` — volume must be zero or more (missing volume is allowed).

## Candle rules (silver.candles)
- `ohlc_not_null` — open and close must be present.
- `high_is_highest` — high must be at least open, close and low.
- `low_is_lowest` — low must be at most open, close and high.

## What to do when quarantine grows
A handful of quarantined rows per run is normal (the API occasionally returns a zero volume or a
partial candle). If more than 1% of a run is quarantined, check whether CoinGecko changed its
response format before re-running.
