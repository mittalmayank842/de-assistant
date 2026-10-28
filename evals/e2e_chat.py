"""End-to-end: real Delta tables from the pipeline + local Llama via Ollama, through the FastAPI app."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fastapi.testclient import TestClient  # noqa: E402

from de_assistant.api import app  # noqa: E402

QUESTIONS = [
    "What feeds into platinum.pattern_counts?",
    "How many rows are in silver.daily_prices and what columns does it have?",
    "Does silver.coins contain any personal data?",
    "Are we within SLA right now?",
    "What should I do if CoinGecko returns HTTP 429?",
    "Run the pipeline again",
]

if __name__ == "__main__":
    c = TestClient(app)
    print("health:", c.get("/health").json()["tools"])
    for q in QUESTIONS:
        t0 = time.time()
        r = c.post("/chat", json={"question": q}).json()
        print(f"\nQ: {q}\n   intent={r['intent']} args={r['args']} ({time.time() - t0:.1f}s)\n   A: {r['answer'][:400]}")
