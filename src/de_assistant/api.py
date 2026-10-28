"""FastAPI backend: POST /chat routes a question to a tool, then asks the LLM to answer."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import llm, rag, router
from .tools import TOOLS

app = FastAPI(title="Data Engineering Assistant")


class Ask(BaseModel):
    question: str


class Call(BaseModel):
    args: dict = {}


@app.get("/health")
def health():
    return {"ok": True, "tables": router.known_tables(), "tools": list(TOOLS)}


@app.post("/index")
def index():
    return {"chunks_indexed": rag.build_index()}


@app.post("/chat")
def chat(body: Ask):
    intent, args, confidence = router.detect(body.question)
    result = TOOLS[intent](**args)
    return {"intent": intent, "confidence": confidence, "args": args, "tool_result": result,
            "answer": llm.answer(body.question, intent, result)}


@app.post("/tools/{name}")
def call_tool(name: str, body: Call):
    if name not in TOOLS:
        raise HTTPException(404, f"unknown tool {name}")
    return TOOLS[name](**body.args)
