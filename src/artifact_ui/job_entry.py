"""Isolated process entry for long-running artifact UI jobs (Windows-safe)."""

from __future__ import annotations

import json
import signal
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parent.parent
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from utils.console_utils import configure_utf8_stdio  # noqa: E402
from utils.multiprocessing_config import \
    configure_spawn_start_method  # noqa: E402

configure_utf8_stdio()
configure_spawn_start_method()

from artifact_ui.workers import WORKERS  # noqa: E402

_ACTIVE_JOB_DIR: Path | None = None


def _log(job_dir: Path, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with (job_dir / "run.log").open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _handle_termination(signum: int, _frame) -> None:
    if _ACTIVE_JOB_DIR is None:
        raise SystemExit(128 + signum)
    from artifact_ui.workers import ensure_partial_result_packaged

    _log(
        _ACTIVE_JOB_DIR,
        f"Received termination signal ({signum}); packaging partial results.",
    )
    ensure_partial_result_packaged(
        _ACTIVE_JOB_DIR,
        "cancelled",
        exit_code=1,
        error="Job terminated",
    )
    raise SystemExit(128 + signum)


def main() -> int:
    global _ACTIVE_JOB_DIR
    if len(sys.argv) != 3:
        print(
            "Usage: python -m artifact_ui.job_entry <script_name> <job_dir>",
            file=sys.stderr,
        )
        return 2
    script_name = sys.argv[1]
    job_dir = Path(sys.argv[2])
    if script_name not in WORKERS:
        print(f"Unknown job: {script_name}", file=sys.stderr)
        return 2
    _ACTIVE_JOB_DIR = job_dir
    signal.signal(signal.SIGTERM, _handle_termination)
    signal.signal(signal.SIGINT, _handle_termination)
    _log(job_dir, f"job_entry started for {script_name}.")
    try:
        config = json.loads((job_dir / "config.json").read_text(encoding="utf-8"))
        WORKERS[script_name](str(job_dir), config)
    except Exception:
        _log(job_dir, traceback.format_exc())
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
