"""Answer generation with a local Llama model served by Ollama."""
from __future__ import annotations

import json

import httpx

from . import config

SYSTEM = ("You are a data engineering assistant for a crypto market data pipeline. "
          "Answer only from the tool result you are given. If it does not contain the answer, say so. "
          "Be brief and concrete; quote table names and numbers exactly.")


def answer(question: str, tool: str, result: object) -> str:
    prompt = f"Question: {question}\n\nTool used: {tool}\nTool result (JSON):\n{json.dumps(result, default=str)[:6000]}"
    try:
        r = httpx.post(f"{config.OLLAMA_URL}/api/chat", timeout=120, json={
            "model": config.OLLAMA_MODEL, "stream": False, "options": {"temperature": 0.1},
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]})
        r.raise_for_status()
        return r.json()["message"]["content"].strip()
    except httpx.HTTPError as e:
        return f"(LLM unavailable: {e.__class__.__name__}) Raw tool result: {json.dumps(result, default=str)[:800]}"
