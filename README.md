# de-assistant — AI assistant for a data pipeline (RAG + MCP)

Ask questions about the [crypto-market-pipeline](https://github.com/mittalmayank842/crypto-market-pipeline)
in plain English: how a rule works, what a table contains, whether it holds personal data, where its data
comes from, whether today's run met its SLA — or ask it to re-run the pipeline.

```
POST /chat  {"question": "What feeds into platinum.pattern_counts?"}
-> intent: trace_lineage   args: {"table": "platinum.pattern_counts"}
-> answer: platinum.pattern_counts is built from gold.candle_signals, which comes from
           silver.candles, bronze.ohlc and the CoinGecko /coins/{id}/ohlc endpoint.
```

## Six tools, two front doors

| Tool | What it does |
| --- | --- |
| `search_docs` | Semantic search (RAG) over the pipeline runbooks, table docs and data-quality rules |
| `get_table_metadata` | Schema, row count, Delta version, partitions and last operation of any table |
| `classify_pii` | Labels every column `pii` / `none` from its name and sample values |
| `trace_lineage` | Upstream sources and downstream consumers of a table |
| `pipeline_status` | Last run, hours since it ran, 24-hour SLA check, row counts per layer, recent errors |
| `trigger_pipeline` | Starts a run — dry run unless `confirm=true` |

The same functions are served two ways:
- **MCP server** (`de_assistant.mcp_server`) — plug into Claude Desktop / Claude Code / any MCP client.
- **FastAPI** (`de_assistant.api`) — `/chat` detects intent, calls the tool, and asks a local
  **Llama 3.2 (3B) through Ollama** to write the answer from the tool result only.

## How it works

- **RAG:** docs are chunked on their markdown headings (one rule or table per chunk), embedded with
  `all-MiniLM-L6-v2` sentence-transformers and stored in **ChromaDB** with cosine distance.
- **Intent detection:** keyword cues decide first (e.g. "upstream", "PII", "schema"); otherwise the question
  is matched to the closest intent by embedding similarity. Table names are pulled out with a regex.
- **Metadata without Spark:** Delta tables are read with `deltalake` (delta-rs), so the assistant stays light.
- **Guarded actions:** the only write action, `trigger_pipeline`, never runs without an explicit confirm.

## Evaluation

| Check | Result |
| --- | --- |
| Intent routing, tuning set (24 questions) | 24/24 |
| Intent routing, **held-out set (16 questions, never tuned on)** | **13/16 (81%)** |
| Unit tests (chunking, lineage, PII classifier) | 3 passing |
| MCP smoke test (list tools, call 2 tools over stdio) | passing |

The tuning-set score is optimistic by design; the held-out score is the honest one. Remaining misses are
listed by `evals/routing_holdout.py`.

## Run it

```bash
uv venv --python 3.11 .venv && uv pip install -r requirements.txt
ollama pull llama3.2:3b && ollama serve &
PYTHONPATH=src .venv/bin/uvicorn de_assistant.api:app --port 8000
curl -s localhost:8000/chat -H 'content-type: application/json' -d '{"question":"Are we within SLA?"}'
```

Set `PIPELINE_HOME` if the pipeline checkout is not a sibling folder.
`docker-compose.yml` runs the API and Ollama together (`docker compose up`).

## Tests and evals

```bash
.venv/bin/python -m pytest -q
.venv/bin/python evals/routing_eval.py
.venv/bin/python evals/routing_holdout.py
.venv/bin/python evals/mcp_smoke.py
```
