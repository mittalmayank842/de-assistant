"""RAG over the pipeline documentation.

Docs are split on their markdown headings so each chunk is one self-contained section
(a rule, a table, a runbook entry) instead of an arbitrary character window.
"""
from __future__ import annotations

import re
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from . import config

COLLECTION = "pipeline_docs"


def chunk_markdown(text: str, source: str) -> list[dict]:
    chunks, title, doc_title, buf = [], "", "", []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            heading = f"{doc_title} > {title}" if title and title != doc_title else doc_title
            chunks.append({"id": f"{source}#{len(chunks)}", "text": f"{heading}\n{body}",
                           "source": source, "section": title or doc_title})

    for line in text.splitlines():
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            flush()
            buf = []
            if len(m.group(1)) == 1:
                doc_title = title = m.group(2).strip()
            else:
                title = m.group(2).strip()
        else:
            buf.append(line)
    flush()
    return chunks


@lru_cache(maxsize=1)
def embedder() -> SentenceTransformer:
    return SentenceTransformer(config.EMBED_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    return embedder().encode(texts, normalize_embeddings=True).tolist()


@lru_cache(maxsize=1)
def collection():
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def build_index() -> int:
    chunks = [c for p in sorted(config.DOCS.glob("*.md")) for c in chunk_markdown(p.read_text(), p.name)]
    col = collection()
    existing = col.get()["ids"]
    if existing:
        col.delete(ids=existing)
    col.add(ids=[c["id"] for c in chunks], documents=[c["text"] for c in chunks],
            embeddings=embed([c["text"] for c in chunks]),
            metadatas=[{"source": c["source"], "section": c["section"]} for c in chunks])
    return len(chunks)


def search(query: str, k: int = 4) -> list[dict]:
    col = collection()
    if col.count() == 0:
        build_index()
    res = col.query(query_embeddings=embed([query]), n_results=k)
    return [{"text": d, "source": m["source"], "section": m["section"], "score": round(1 - dist, 3)}
            for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])]
