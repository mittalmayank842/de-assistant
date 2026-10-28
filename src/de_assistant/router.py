"""Intent detection: decide which tool answers a question, and pull out the table name.

Embedding similarity against a few example questions per intent, with a table-name
regex for arguments. Cheap, deterministic, and easy to test without an LLM.
"""
from __future__ import annotations

import re

import numpy as np

from . import catalog, rag

EXAMPLES = {
    "search_docs": ["what does the silver layer do", "how is volatility calculated",
                    "what should I do on a 429 error", "explain the data quality rules"],
    "get_table_metadata": ["what columns does gold.daily_metrics have", "schema of silver.coins",
                           "how many rows are in platinum.movers", "describe the table"],
    "classify_pii": ["does this table contain personal data", "check silver.coins for PII",
                     "is there any sensitive or personal information"],
    "trace_lineage": ["where does platinum.movers come from", "what depends on silver.candles",
                      "show lineage for this table", "upstream and downstream of gold.daily_metrics"],
    "pipeline_status": ["did the pipeline run today", "is the SLA breached", "pipeline health",
                        "show the last run and errors"],
    "trigger_pipeline": ["run the pipeline", "trigger a rerun", "start the pipeline now", "reprocess the data"],
}
TABLE_RX = re.compile(r"\b(bronze|silver|gold|platinum)\.(_?[a-z_]+)\b")

# Strong keyword cues win over embedding similarity. Embeddings alone confuse questions
# that share a table name (metadata vs lineage vs PII), so explicit words decide first.
KEYWORDS = [
    ("trigger_pipeline", r"\b(run|rerun|re-run|kick off|start|trigger|reprocess)\b.*\b(pipeline|run|batch|everything|data)\b"),
    ("classify_pii", r"\b(pii|personal|sensitive|email|phone|privacy|gdpr)\b"),
    ("trace_lineage", r"\b(lineage|upstream|downstream|feeds?|depends?|comes? from|affected|impact|back to)\b"),
    ("get_table_metadata", r"\b(schema|columns?|fields?|rows?|row count|version|partition(ed)?|describe)\b"),
    ("pipeline_status", r"\b(sla|last run|latest run|fresh|stale|health|errors? in|today|status)\b"),
]


def _centroids():
    if not hasattr(_centroids, "cache"):
        _centroids.cache = {k: np.mean(rag.embed(v), axis=0) for k, v in EXAMPLES.items()}
    return _centroids.cache


def detect(question: str) -> tuple[str, dict, float]:
    q = np.array(rag.embed([question])[0])
    scores = {k: float(q @ c / np.linalg.norm(c)) for k, c in _centroids().items()}
    intent = max(scores, key=scores.get)
    low = question.lower()
    m = TABLE_RX.search(low)
    table = m.group(0) if m else None
    # a "how/why/what is the policy" question without a table is a docs question even if it says SLA or PII
    is_docs_question = not table and re.match(r"^(why|how|what('s| is) the|explain|which .* do we)", low)
    for name, rx in KEYWORDS:
        if not is_docs_question and re.search(rx, low):
            intent = name
            break
    args: dict = {}
    if intent in ("get_table_metadata", "classify_pii", "trace_lineage"):
        if not table:                      # no table named: fall back to docs
            intent = "search_docs"
        else:
            args["table"] = table
    if intent == "search_docs":
        args["query"] = question
    if intent == "trigger_pipeline":
        args = {"reuse": "fresh" not in question.lower(), "confirm": False}
    return intent, args, round(scores[intent], 3)


def known_tables() -> list[str]:
    return catalog.list_tables()
