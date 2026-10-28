# Runbook: Failures and Fixes

## HTTP 429 Too Many Requests
CoinGecko's free tier allows roughly 5 to 15 calls a minute. The ingest client waits 6.5 seconds
between calls and backs off 30, 60, 90 seconds on a 429. If runs still fail, set the
`COINGECKO_API_KEY` environment variable to use a free demo key with a higher limit.

## Python version mismatch in Spark workers
Error: `PYTHON_VERSION_MISMATCH`. Spark started workers with a different Python than the driver.
The pipeline sets `PYSPARK_PYTHON` to the current interpreter; if you run Spark another way,
export `PYSPARK_PYTHON` to the same virtual environment.

## Stale platinum tables
If the newest successful run is older than 24 hours the SLA is breached. Check the last run report
(`data/last_run_report.json`) and the run log (`data/run.log`), fix the cause, then re-run.
If the API data is already landed, use `--reuse` to reprocess without calling the API again.

## Re-running safely
Bronze is append-only and silver always reads the newest run only, so running the pipeline twice
does not duplicate data in silver, gold or platinum.
