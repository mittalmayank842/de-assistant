"""FastAPI backend: POST /chat routes a question to a tool, then asks the LLM to answer."""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import config, llm, rag, router
from .tools import TOOLS

app = FastAPI(title="Data Engineering Assistant")


NO_DATA = ("No pipeline data on this host: the Delta tables and run report live with the pipeline, "
           "so this tool needs PIPELINE_HOME pointing at a crypto-market-pipeline checkout. "
           "Docs search and lineage still work.")


def run_tool(name: str, args: dict):
    """Run a tool; on a host without the pipeline's data, say so instead of failing with a 500."""
    try:
        return TOOLS[name](**args)
    except Exception:
        if not config.LAKE.exists():
            return {"error": NO_DATA}
        raise


class Ask(BaseModel):
    question: str


class Call(BaseModel):
    args: dict = {}


@app.get("/health")
def health():
    return {"ok": True, "version": os.getenv("GIT_SHA", "dev"), "tables": router.known_tables(), "tools": list(TOOLS)}


@app.post("/index")
def index():
    return {"chunks_indexed": rag.build_index()}


@app.post("/chat")
def chat(body: Ask):
    intent, args, confidence = router.detect(body.question)
    result = run_tool(intent, args)
    return {"intent": intent, "confidence": confidence, "args": args, "tool_result": result,
            "answer": llm.answer(body.question, intent, result)}


@app.post("/tools/{name}")
def call_tool(name: str, body: Call):
    if name not in TOOLS:
        raise HTTPException(404, f"unknown tool {name}")
    return run_tool(name, body.args)
