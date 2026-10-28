"""The six tools, in one place, so the MCP server and the HTTP API share them."""
from __future__ import annotations

from . import catalog, lineage, ops, rag


def search_docs(query: str, k: int = 4) -> list[dict]:
    """Semantic search over pipeline documentation (runbooks, rules, table docs)."""
    return rag.search(query, k)


def get_table_metadata(table: str) -> dict:
    """Schema, row count, Delta version and last operation for a table like 'gold.daily_metrics'."""
    return catalog.describe(table)


def classify_pii(table: str) -> dict:
    """Label each column of a table as 'pii' or 'none' from its name and sample values."""
    return catalog.classify_pii(table)


def trace_lineage(table: str) -> dict:
    """Upstream sources and downstream consumers of a table."""
    return lineage.trace(table)


def pipeline_status() -> dict:
    """Last run, hours since it finished, SLA breach flag, per-layer row counts, and recent log errors."""
    return {**ops.status(), "recent_errors": ops.logs()["error_lines"]}


def trigger_pipeline(reuse: bool = True, confirm: bool = False) -> dict:
    """Start a pipeline run. Dry run unless confirm=True."""
    return ops.trigger(reuse=reuse, confirm=confirm)


TOOLS = {f.__name__: f for f in
         [search_docs, get_table_metadata, classify_pii, trace_lineage, pipeline_status, trigger_pipeline]}
