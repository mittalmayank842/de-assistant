# de-assistant — AI assistant for a data pipeline (RAG + MCP)

[![Deploy to Azure](https://github.com/mittalmayank842/de-assistant/actions/workflows/azure-deploy.yml/badge.svg)](https://github.com/mittalmayank842/de-assistant/actions/workflows/azure-deploy.yml)

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
| Retrieval | 40 questions labelled with the right section, over 20 doc sections | **recall@3 90%**, recall@1 80%, MRR 0.858 |
| Guardrail | 45 attacks: 40 direct prompts ("confirm=true", "admin approved", "ignore your rules", fake tool-call JSON) + 5 instructions hidden inside retrieved documents | **45/45 blocked**: nothing runs without an explicit confirm |
| Grounding (Llama 3.2 3B) | 30 end-to-end questions across all 6 tools | **30/30** answers use only numbers and table names found in the tool result |
| Admits unknown | 10 questions the docs can't answer | **10/10** say so instead of guessing |
| Latency | local, M-series Mac | routing p50 11 ms · retrieval p50 11 ms · LLM answer p50 5.2 s |
| Earlier sets | tuning 24 / first held-out 16 | 24/24 · 13/16 |

**Known weak spot:** about a quarter of docs questions that mention the pipeline ("How often does the pipeline run?") get routed to `pipeline_status` or `trigger_pipeline`. They stay misses in the set on purpose; fixing them by tuning on this set would make the score dishonest.

**CI/CD:** every push runs the unit tests, the benchmark and the MCP smoke test on GitHub Actions. The benchmark is a regression gate: the build fails if routing drops below 80%, recall@3 below 85% or any guardrail attack gets through. On `main`, the Docker image is built, started and checked on `/health` (deploy smoke test), then published to GitHub Container Registry:

```bash
docker run -p 8000:8000 ghcr.io/mittalmayank842/de-assistant:latest
```

## Running on Azure

Live: https://deassist-api.bravewater-457fb342.eastasia.azurecontainerapps.io/health. After it has been idle, the first call takes a few seconds while it starts.

| Piece | Azure service |
| --- | --- |
| API (FastAPI, Docker image from GHCR) | **Azure Container Apps**, East Asia; scales to zero, 0.5 vCPU |
| Answer generation | **Azure OpenAI** `gpt-5-mini`, Korea Central |
| Embeddings | **Azure OpenAI** `text-embedding-3-small` |
| Retrieval | **Azure AI Search** (free tier): hybrid BM25 keyword + vector search, fused with RRF |
| Secrets | **Azure Key Vault**; the app reads them through Key Vault references and its managed identity |
| Deploys | **GitHub Actions**, signed in to Azure with OIDC workload identity federation |

No key is stored in the app config, the repo or GitHub. The deploy identity may change only this resource group.

The same benchmark (`evals/results_azure.json`) on the Azure backend:

| Check | Local (ChromaDB + MiniLM + Llama 3.2) | Azure (AI Search hybrid + gpt-5-mini) |
| --- | --- | --- |
| Retrieval recall@3 / recall@1 / MRR | 90% / 80% / 0.858 | **95% / 82.5% / 0.894** |
| Grounded answers | 30/30 | **30/30** |
| Admits unknown | 10/10 | **10/10** |
| LLM answer latency p50 | 5.2 s | **2.6 s** |

Routing (94.2%) and the guardrail (45/45 blocked) don't depend on the backend.

**Deploy flow:** every successful image build on `main` triggers [Deploy to Azure](.github/workflows/azure-deploy.yml).
1. It rolls the container app to the image built from that exact commit, with rollouts one at a time.
2. It waits until the live `/health` reports that commit's version.
3. It fails the run if it never does.

**Setup:** [deploy/azure/setup.sh](deploy/azure/setup.sh) creates the app and its GitHub deploy identity. [deploy/azure/ai_setup.sh](deploy/azure/ai_setup.sh) creates Azure OpenAI, AI Search and Key Vault.

**Data:** the hosted copy has no pipeline data, because the Delta tables live with the pipeline. So metadata, PII and run-status questions return a clear "no pipeline data on this host" message. Docs questions and lineage work fully. Without the Azure settings, the app falls back to the local stack (Docker Compose + Ollama).

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
