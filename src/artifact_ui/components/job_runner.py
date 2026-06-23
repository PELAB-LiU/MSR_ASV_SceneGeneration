"""Subprocess job runner for Streamlit artifact UI."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any, Dict, Optional

from artifact_ui.components.job_state import (JobState, create_job,
                                              refresh_job_state,
                                              update_job_status)
from utils.artifact_config import ArtifactConfig

_SRC_ROOT = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _SRC_ROOT.parent


def _worker_env() -> dict[str, str]:
    env = os.environ.copy()
    src_root = str(_SRC_ROOT)
    existing = env.get("PYTHONPATH", "")
    parts = [part for part in existing.split(os.pathsep) if part]
    if src_root not in parts:
        parts.insert(0, src_root)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    for key in (
        "ARTIFACT_DATA_DIR",
        "ARTIFACT_OUTPUT_DIR",
        "MPLBACKEND",
        "ENABLE_RRT_ANIMATION",
    ):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _append_log(log_path: Path, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def start_job(script_name: str, config: Dict[str, Any]) -> JobState:
    from artifact_ui.workers import WORKERS

    if script_name not in WORKERS:
        raise ValueError(f"Unknown script job: {script_name}")
    artifact_config = ArtifactConfig.from_env()
    artifact_config.ensure_dirs()
    state = create_job(artifact_config.jobs_dir, script_name)
    job_dir = Path(state.job_dir)
    log_path = job_dir / "run.log"
    (job_dir / "config.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )
    _append_log(
        log_path,
        f"Launching worker for {script_name} (first import can take 30-60s)...",
    )
    log_handle: IO[str] = log_path.open("a", encoding="utf-8")
    popen_kwargs: dict[str, Any] = {
        "cwd": str(_PROJECT_ROOT),
        "env": _worker_env(),
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(
        [sys.executable, "-m", "artifact_ui.job_entry", script_name, str(job_dir)],
        **popen_kwargs,
    )
    _append_log(log_path, f"Worker subprocess started (pid={process.pid}).")
    update_job_status(job_dir, "running", pid=process.pid)
    return refresh_job_state(job_dir)


def poll_job(job_id: str) -> Optional[JobState]:
    artifact_config = ArtifactConfig.from_env()
    job_dir = artifact_config.jobs_dir / job_id
    if not job_dir.is_dir():
        return None
    return refresh_job_state(job_dir)


def get_active_job_state(active_job_id: Optional[str]) -> Optional[JobState]:
    if not active_job_id:
        return None
    return poll_job(active_job_id)


def job_is_running(state: Optional[JobState]) -> bool:
    if state is None:
        return False
    return state.status in {"queued", "running"}
