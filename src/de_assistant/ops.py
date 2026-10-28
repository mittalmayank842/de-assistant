"""Pipeline operations: status, logs, SLA check, and a guarded trigger."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone

from . import config


def _run_time(run_id: str) -> datetime:
    return datetime.strptime(run_id, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def status() -> dict:
    if not config.RUN_REPORT.exists():
        return {"status": "never_run"}
    report = json.loads(config.RUN_REPORT.read_text())
    started = _run_time(report["run"])
    age_h = (datetime.now(timezone.utc) - started).total_seconds() / 3600
    breached = age_h > config.SLA_HOURS
    # Spell the verdict out: small local models misread bare booleans next to numbers.
    verdict = (f"SLA BREACHED: last run was {age_h:.1f} hours ago, more than the {config.SLA_HOURS}-hour limit."
               if breached else
               f"SLA MET: last run was {age_h:.1f} hours ago, within the {config.SLA_HOURS}-hour limit.")
    return {"status": "ok", "sla_verdict": verdict, "last_run": report["run"], "hours_since_last_run": round(age_h, 1),
            "sla_hours": config.SLA_HOURS, "sla_breached": breached,
            "layers": {k: v for k, v in report.items() if k != "run"}}


def logs(lines: int = 40) -> dict:
    if not config.RUN_LOG.exists():
        return {"lines": []}
    text = config.RUN_LOG.read_text(errors="ignore").splitlines()
    errors = [l for l in text if any(w in l for w in ("ERROR", "Traceback", "Exception"))]
    return {"lines": text[-lines:], "error_lines": errors[-10:]}


def trigger(reuse: bool = True, confirm: bool = False) -> dict:
    """Start a pipeline run. Without confirm=True it only describes what it would do."""
    cmd = [str(config.PIPELINE_HOME / ".venv" / "bin" / "python"), "-m", "crypto_pipeline.pipeline"]
    if reuse:
        cmd.append("--reuse")
    if not confirm:
        return {"dry_run": True, "would_run": " ".join(cmd),
                "note": "Pass confirm=true to actually start the run."}
    if not (config.PIPELINE_HOME / ".venv").exists():
        cmd[0] = sys.executable
    proc = subprocess.Popen(cmd, cwd=config.PIPELINE_HOME, env={"PYTHONPATH": "src", "PATH": "/usr/bin:/bin"},
                            stdout=open(config.RUN_LOG, "w"), stderr=subprocess.STDOUT)
    return {"started": True, "pid": proc.pid, "command": " ".join(cmd)}
