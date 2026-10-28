"""Table-level lineage of the crypto pipeline, as a directed graph (source -> target)."""
from __future__ import annotations

EDGES = [
    ("api./coins/markets", "bronze.markets"),
    ("api./coins/{id}/market_chart", "bronze.price_history"),
    ("api./coins/{id}/ohlc", "bronze.ohlc"),
    ("api./global", "bronze.global"),
    ("api./search/trending", "bronze.trending"),
    ("bronze.price_history", "silver.daily_prices"),
    ("bronze.ohlc", "silver.candles"),
    ("bronze.markets", "silver.coins"),
    ("bronze.price_history", "silver._quarantine"),
    ("bronze.ohlc", "silver._quarantine"),
    ("silver.daily_prices", "gold.daily_metrics"),
    ("silver.candles", "gold.candle_signals"),
    ("gold.daily_metrics", "platinum.coin_scorecard"),
    ("silver.coins", "platinum.coin_scorecard"),
    ("platinum.coin_scorecard", "platinum.movers"),
    ("gold.candle_signals", "platinum.pattern_counts"),
]


def _walk(start: str, forward: bool) -> list[str]:
    nxt = {}
    for a, b in EDGES:
        src, dst = (a, b) if forward else (b, a)
        nxt.setdefault(src, []).append(dst)
    seen, stack, order = set(), [start], []
    while stack:
        node = stack.pop()
        for n in nxt.get(node, []):
            if n not in seen:
                seen.add(n)
                order.append(n)
                stack.append(n)
    return order


def trace(table: str) -> dict:
    known = {n for e in EDGES for n in e}
    if table not in known:
        return {"table": table, "error": f"unknown table; known: {sorted(known)}"}
    return {"table": table, "upstream": _walk(table, forward=False), "downstream": _walk(table, forward=True)}
