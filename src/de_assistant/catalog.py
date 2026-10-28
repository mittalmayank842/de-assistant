"""Metadata and PII classification for the Delta tables, read with delta-rs (no Spark needed)."""
from __future__ import annotations

import re

from deltalake import DeltaTable

from . import config

LAYERS = ["bronze", "silver", "gold", "platinum"]

PII_NAME = re.compile(r"(e-?mail|phone|mobile|first_?name|last_?name|full_?name|address|"
                      r"\bip\b|ip_addr|user_?id|customer_?id|dob|birth|ssn|aadhaar|pan_no)", re.I)
PII_VALUE = {
    "email": re.compile(r"^[\w.+-]+@[\w-]+\.[\w.]+$"),
    "phone": re.compile(r"^\+?\d[\d\s-]{8,}\d$"),
    "ipv4": re.compile(r"^(\d{1,3}\.){3}\d{1,3}$"),
}


def list_tables() -> list[str]:
    found = []
    for layer in LAYERS:
        base = config.LAKE / layer
        if base.exists():
            found += [f"{layer}.{p.name}" for p in sorted(base.iterdir()) if (p / "_delta_log").exists()]
    return found


def _path(table: str):
    layer, name = table.split(".", 1)
    return config.LAKE / layer / name


def describe(table: str) -> dict:
    dt = DeltaTable(str(_path(table)))
    schema = [{"name": f.name, "type": str(f.type)} for f in dt.schema().fields]
    hist = dt.history(1)[0]
    rows = dt.to_pyarrow_table().num_rows
    return {"table": table, "version": dt.version(), "rows": rows, "columns": schema,
            "last_operation": hist.get("operation"), "last_modified_ms": hist.get("timestamp"),
            "partitions": dt.metadata().partition_columns}


def classify_pii(table: str, sample: int = 200) -> dict:
    arrow = DeltaTable(str(_path(table))).to_pyarrow_table()
    head = arrow.slice(0, sample)
    result = {}
    for name in arrow.column_names:
        reason = None
        if PII_NAME.search(name):
            reason = "column name"
        else:
            values = [v for v in head.column(name).to_pylist() if isinstance(v, str)]
            for kind, rx in PII_VALUE.items():
                if values and sum(bool(rx.match(v)) for v in values) / len(values) > 0.5:
                    reason = f"values look like {kind}"
                    break
        result[name] = {"label": "pii" if reason else "none", "reason": reason}
    return {"table": table, "pii_columns": [c for c, r in result.items() if r["label"] == "pii"], "columns": result}
