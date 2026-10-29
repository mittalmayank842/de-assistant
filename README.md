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

[![CI](https://github.com/mittalmayank842/de-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/mittalmayank842/de-assistant/actions/workflows/ci.yml)
[![Docker image](https://github.com/mittalmayank842/de-assistant/actions/workflows/docker.yml/badge.svg)](https://github.com/mittalmayank842/de-assistant/actions/workflows/docker.yml)

`evals/benchmark.py` holds questions written after the router and RAG were finished. None of them is used to tune anything.

| Check | Set | Result |
| --- | --- | --- |
| Intent routing | 120 held-out questions (20 per tool) | **94.2%** accuracy (113/120); per-tool precision 0.83–1.00, recall 0.75–1.00 |
| Retrieval | 40 questions labelled with the right doc section | **recall@3 90%**, recall@1 80%, MRR 0.858 |
| Guardrail | 15 prompts that try to force a real pipeline run ("confirm=true", "admin approved", "ignore your rules") | **15/15 blocked**: nothing runs without an explicit confirm |
| Grounding (Llama 3.2 3B) | 12 end-to-end questions | **12/12** answers use only numbers and table names found in the tool result |
| Admits unknown | 6 questions the docs can't answer | **6/6** say so instead of guessing |
| Latency | local, M-series Mac | routing p50 11 ms · retrieval p50 11 ms · LLM answer p50 4.3 s |
| Earlier sets | tuning 24 / first held-out 16 | 24/24 · 13/16 |

**Known weak spot:** about a quarter of docs questions that mention the pipeline ("How often does the pipeline run?") get routed to `pipeline_status` or `trigger_pipeline`. They stay misses in the set on purpose; fixing them by tuning on this set would make the score dishonest.

**CI/CD:** every push runs the unit tests, the benchmark and the MCP smoke test on GitHub Actions. The benchmark is a regression gate: the build fails if routing drops below 80%, recall@3 below 85% or guardrails below 100%. On `main`, the Docker image is built, started and checked on `/health` (deploy smoke test), then published to GitHub Container Registry:

```bash
docker run -p 8000:8000 ghcr.io/mittalmayank842/de-assistant:latest
```

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
.venv/bin/python evals/benchmark.py --llm   # full benchmark incl. grounding (needs Ollama)
.venv/bin/python evals/mcp_smoke.py
```
