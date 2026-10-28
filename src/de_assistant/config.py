"""Where things live. Point PIPELINE_HOME at a checkout of crypto-market-pipeline."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ROOT / ".chroma"))

PIPELINE_HOME = Path(os.getenv("PIPELINE_HOME", ROOT.parent / "crypto-market-pipeline"))
LAKE = PIPELINE_HOME / "data" / "lake"
RUN_REPORT = PIPELINE_HOME / "data" / "last_run_report.json"
RUN_LOG = PIPELINE_HOME / "data" / "run.log"

EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

SLA_HOURS = 24
