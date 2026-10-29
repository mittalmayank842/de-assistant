"""Azure backend: Azure OpenAI (embeddings + chat) and Azure AI Search (hybrid BM25 + vector retrieval).

Used when AZURE_OPENAI_ENDPOINT / AZURE_SEARCH_ENDPOINT are set; otherwise the local stack
(MiniLM + ChromaDB + Ollama) is used. Plain REST over httpx, so no extra SDKs are needed.
On Azure the keys come from Key Vault references resolved by the app's managed identity.
"""
from __future__ import annotations

import os

import httpx

AOAI = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AOAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")
CHAT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "chat")
CHAT_MODEL = os.getenv("AZURE_OPENAI_CHAT_MODEL", "gpt-5-mini")
EMBED = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-small")
SEARCH = os.getenv("AZURE_SEARCH_ENDPOINT", "").rstrip("/")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "")
INDEX = os.getenv("AZURE_SEARCH_INDEX", "pipeline-docs")
DIMS = 1536
AOAI_VER, SEARCH_VER = "2025-04-01-preview", "2024-07-01"


def openai_enabled() -> bool:
    return bool(AOAI and AOAI_KEY)


def search_enabled() -> bool:
    return bool(SEARCH and SEARCH_KEY and openai_enabled())


def embed(texts: list[str]) -> list[list[float]]:
    r = httpx.post(f"{AOAI}/openai/deployments/{EMBED}/embeddings", params={"api-version": AOAI_VER},
                   headers={"api-key": AOAI_KEY}, json={"input": texts}, timeout=60)
    r.raise_for_status()
    return [d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"])]


def chat(system: str, user: str) -> str:
    r = httpx.post(f"{AOAI}/openai/deployments/{CHAT}/chat/completions", params={"api-version": AOAI_VER},
                   headers={"api-key": AOAI_KEY}, timeout=120, json={
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                       "max_completion_tokens": 1500, "reasoning_effort": "minimal"})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _search(method: str, path: str, body: dict | None = None) -> httpx.Response:
    r = httpx.request(method, f"{SEARCH}{path}", params={"api-version": SEARCH_VER},
                      headers={"api-key": SEARCH_KEY}, json=body, timeout=60)
    if r.status_code >= 400 and not (method == "DELETE" and r.status_code == 404):
        raise httpx.HTTPStatusError(f"{r.status_code}: {r.text[:300]}", request=r.request, response=r)
    return r


def build_index(chunks: list[dict]) -> int:
    """(Re)create the index and upload every chunk with its embedding."""
    _search("DELETE", f"/indexes/{INDEX}")
    _search("PUT", f"/indexes/{INDEX}", {
        "name": INDEX,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True},
            {"name": "text", "type": "Edm.String", "searchable": True},
            {"name": "source", "type": "Edm.String", "filterable": True},
            {"name": "section", "type": "Edm.String", "searchable": True},
            {"name": "vector", "type": "Collection(Edm.Single)", "searchable": True,
             "dimensions": DIMS, "vectorSearchProfile": "hnsw"},
        ],
        "vectorSearch": {"algorithms": [{"name": "hnsw-algo", "kind": "hnsw", "hnswParameters": {"metric": "cosine"}}],
                         "profiles": [{"name": "hnsw", "algorithm": "hnsw-algo"}]},
    })
    vectors = embed([c["text"] for c in chunks])
    docs = [{"@search.action": "upload", "id": c["id"].replace("#", "_").replace(".", "_"), "text": c["text"],
             "source": c["source"], "section": c["section"], "vector": v} for c, v in zip(chunks, vectors)]
    _search("POST", f"/indexes/{INDEX}/docs/index", {"value": docs})
    return len(docs)


def index_count() -> int:
    r = httpx.get(f"{SEARCH}/indexes/{INDEX}/docs/$count", params={"api-version": SEARCH_VER},
                  headers={"api-key": SEARCH_KEY}, timeout=30)
    return int(r.text.strip().lstrip("﻿")) if r.status_code == 200 else 0


def search(query: str, k: int = 4) -> list[dict]:
    """Hybrid retrieval: BM25 keyword search + vector search, fused by Azure AI Search (RRF)."""
    body = {"search": query, "top": k, "select": "text,source,section",
            "vectorQueries": [{"kind": "vector", "vector": embed([query])[0], "fields": "vector", "k": k}]}
    hits = _search("POST", f"/indexes/{INDEX}/docs/search", body).json()["value"]
    return [{"text": h["text"], "source": h["source"], "section": h["section"],
             "score": round(h["@search.score"], 4)} for h in hits]
