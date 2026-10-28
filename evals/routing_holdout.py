"""Held-out routing questions, written after the keyword rules and never used to tune them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from de_assistant import router  # noqa: E402

CASES = [
    ("How does the pipeline compute annualised volatility?", "search_docs"),
    ("What happens to a candle whose high is below its open?", "search_docs"),
    ("Explain what the platinum layer is for", "search_docs"),
    ("Why is bronze append-only?", "search_docs"),
    ("Give me the column types of platinum.movers", "get_table_metadata"),
    ("How big is silver.candles?", "get_table_metadata"),
    ("Show me the schema for bronze.trending", "get_table_metadata"),
    ("Does gold.candle_signals hold any sensitive customer info?", "classify_pii"),
    ("Scan silver.daily_prices for privacy issues", "classify_pii"),
    ("Which tables would break if silver.coins changed?", "trace_lineage"),
    ("Where does silver.candles get its data?", "trace_lineage"),
    ("Has the pipeline been healthy since yesterday?", "pipeline_status"),
    ("Is anything stale on the dashboard?", "pipeline_status"),
    ("Show errors from the latest run", "pipeline_status"),
    ("Trigger a fresh run of the pipeline", "trigger_pipeline"),
    ("Re-run the batch from the existing landed data", "trigger_pipeline"),
]

if __name__ == "__main__":
    wrong = [(q, w, router.detect(q)[0]) for q, w in CASES if router.detect(q)[0] != w]
    print(f"held-out routing accuracy: {len(CASES) - len(wrong)}/{len(CASES)} = {(len(CASES) - len(wrong)) / len(CASES):.0%}")
    for w in wrong:
        print("  MISS", w)
