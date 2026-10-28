"""How often does intent detection pick the right tool? Questions here are NOT the router's examples."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from de_assistant import router  # noqa: E402

CASES = [
    ("Why do we keep rows in quarantine instead of dropping them?", "search_docs"),
    ("How do I avoid CoinGecko rate limits?", "search_docs"),
    ("What is the freshness SLA for the dashboards?", "search_docs"),
    ("Which candlestick patterns do we detect?", "search_docs"),
    ("What's the policy on personal data in shared tables?", "search_docs"),
    ("List the fields in silver.daily_prices", "get_table_metadata"),
    ("What is the current Delta version of gold.candle_signals?", "get_table_metadata"),
    ("Row count for platinum.coin_scorecard please", "get_table_metadata"),
    ("Is gold.daily_metrics partitioned?", "get_table_metadata"),
    ("Could silver.coins expose anyone's personal details?", "classify_pii"),
    ("Run a PII scan on bronze.markets", "classify_pii"),
    ("Are there emails or phone numbers in platinum.movers?", "classify_pii"),
    ("What feeds into platinum.pattern_counts?", "trace_lineage"),
    ("If bronze.ohlc breaks, which tables are affected?", "trace_lineage"),
    ("Trace silver.daily_prices back to its source", "trace_lineage"),
    ("Which downstream tables read gold.candle_signals?", "trace_lineage"),
    ("When did the last run finish?", "pipeline_status"),
    ("Are we within SLA right now?", "pipeline_status"),
    ("Any errors in the latest pipeline run?", "pipeline_status"),
    ("Is the data fresh today?", "pipeline_status"),
    ("Kick off the pipeline again", "trigger_pipeline"),
    ("Please rerun everything with fresh API data", "trigger_pipeline"),
    ("Reprocess the last landed batch", "trigger_pipeline"),
    ("Can you start a new pipeline run?", "trigger_pipeline"),
]

if __name__ == "__main__":
    wrong = []
    for q, want in CASES:
        got, _, conf = router.detect(q)
        if got != want:
            wrong.append((q, want, got, conf))
    acc = (len(CASES) - len(wrong)) / len(CASES)
    print(f"routing accuracy: {len(CASES) - len(wrong)}/{len(CASES)} = {acc:.0%}")
    for w in wrong:
        print("  MISS", w)
