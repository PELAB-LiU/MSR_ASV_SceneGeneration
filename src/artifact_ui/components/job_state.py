"""Persistent job state for subprocess-backed artifact operations."""

from __future__ import annotations

import json
import os
import signal
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]

GENERATION_SCRIPTS = frozenset(
    {"evaluation_main", "hyperparam_test", "generate_trajectories"}
)


@dataclass
class JobState:
    job_id: str
    script_name: str
    status: JobStatus
    started_at: str
    pid: Optional[int]
    log_path: str
    job_dir: str
    progress: Optional[float] = None

    @classmethod
    def from_file(cls, path: Path) -> "JobState":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def is_pid_alive(pid: Optional[int]) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def create_job(jobs_root: Path, script_name: str) -> JobState:
    job_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "_"
        + uuid.uuid4().hex[:8]
    )
    job_dir = jobs_root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / "run.log"
    state = JobState(
        job_id=job_id,
        script_name=script_name,
        status="queued",
        started_at=datetime.now(timezone.utc).isoformat(),
        pid=None,
        log_path=str(log_path),
        job_dir=str(job_dir),
    )
    state.save(job_dir / "state.json")
    return state


def load_job_state(job_dir: Path) -> JobState:
    return JobState.from_file(job_dir / "state.json")


def update_job_status(
    job_dir: Path, status: JobStatus, pid: Optional[int] = None
) -> JobState:
    state = load_job_state(job_dir)
    state.status = status
    if pid is not None:
        state.pid = pid
    state.save(job_dir / "state.json")
    return state


def _ensure_generation_downloads(job_dir: Path, state: JobState) -> None:
    if state.script_name not in GENERATION_SCRIPTS:
        return
    result_path = job_dir / "result.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if result.get("output_files"):
            return
    from artifact_ui.workers import ensure_partial_result_packaged

    ensure_partial_result_packaged(
        job_dir,
        state.status,
        exit_code=1 if state.status != "completed" else 0,
        error="Cancelled by user" if state.status == "cancelled" else "",
    )


def refresh_job_state(job_dir: Path) -> JobState:
    state = load_job_state(job_dir)
    result_path = job_dir / "result.json"
    if state.status in {"completed", "failed", "cancelled"}:
        _ensure_generation_downloads(job_dir, state)
        return state
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding="utf-8"))
        state.status = result.get("status", "failed")
        state.save(job_dir / "state.json")
        _ensure_generation_downloads(job_dir, state)
        return state
    if state.status == "running" and not is_pid_alive(state.pid):
        if result_path.is_file():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            state.status = result.get("status", "failed")
        else:
            state.status = "failed"
        state.save(job_dir / "state.json")
        _ensure_generation_downloads(job_dir, state)
    return state


def cancel_job(job_dir: Path) -> JobState:
    state = load_job_state(job_dir)
    if state.pid and is_pid_alive(state.pid):
        try:
            os.kill(state.pid, signal.SIGTERM)
        except OSError:
            pass
        for _ in range(15):
            if not is_pid_alive(state.pid):
                break
            time.sleep(0.2)
    state.status = "cancelled"
    state.save(job_dir / "state.json")
    from artifact_ui.workers import ensure_partial_result_packaged

    ensure_partial_result_packaged(
        job_dir,
        "cancelled",
        exit_code=1,
        error="Cancelled by user",
    )
    return load_job_state(job_dir)


def tail_log(log_path: Path, max_lines: int = 80) -> str:
    if not log_path.is_file():
        return ""
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-max_lines:])
