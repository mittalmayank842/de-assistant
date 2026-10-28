import sys
from pathlib import Path

import pyarrow as pa
from deltalake import write_deltalake

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from de_assistant import catalog, config, lineage, rag  # noqa: E402


def test_chunks_follow_headings():
    md = "# Doc\nintro\n## Rule A\nbody a\n## Rule B\nbody b\n"
    chunks = rag.chunk_markdown(md, "x.md")
    assert [c["section"] for c in chunks] == ["Doc", "Rule A", "Rule B"]
    assert chunks[1]["text"].startswith("Doc > Rule A")


def test_lineage_walks_both_directions():
    t = lineage.trace("gold.daily_metrics")
    assert "silver.daily_prices" in t["upstream"] and "bronze.price_history" in t["upstream"]
    assert "platinum.coin_scorecard" in t["downstream"] and "platinum.movers" in t["downstream"]
    assert "error" in lineage.trace("nope.table")


def test_pii_classifier(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LAKE", tmp_path)
    data = pa.table({"customer_email": ["a@b.com"], "contact": ["+91 98765 43210"],
                     "symbol": ["btc"], "price": [1.0]})
    write_deltalake(str(tmp_path / "silver" / "people"), data)
    out = catalog.classify_pii("silver.people")
    assert set(out["pii_columns"]) == {"customer_email", "contact"}
    assert out["columns"]["contact"]["reason"] == "values look like phone"
