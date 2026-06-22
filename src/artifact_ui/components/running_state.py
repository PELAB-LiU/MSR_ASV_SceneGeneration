"""Global running-state banner for all artifact UI pages."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st

from artifact_ui.components.browser_upload import render_job_output_downloads
from artifact_ui.components.job_runner import (get_active_job_state,
                                               job_is_running)
from artifact_ui.components.job_state import JobState, cancel_job, tail_log


def init_session_state() -> None:
    if "active_job_id" not in st.session_state:
        st.session_state.active_job_id = None
    if "loaded_pkl_path" not in st.session_state:
        st.session_state.loaded_pkl_path = None


def render_global_status_bar() -> Optional[JobState]:
    init_session_state()
    running_state = get_active_job_state(st.session_state.active_job_id)
    if running_state and job_is_running(running_state):
        started = datetime.fromisoformat(running_state.started_at)
        elapsed = datetime.now(timezone.utc) - started.replace(tzinfo=timezone.utc)
        st.sidebar.warning(
            f"Running: **{running_state.script_name}** "
            f"({int(elapsed.total_seconds())}s elapsed)"
        )
        if st.sidebar.button("Cancel active job"):
            cancel_job(Path(running_state.job_dir))
            st.rerun()
        return running_state
    st.sidebar.info("No job running")
    return None


def render_job_panel(state: Optional[JobState]) -> None:
    if state is None:
        return
    refreshed = get_active_job_state(state.job_id)
    if refreshed is None:
        return
    with st.status(f"Job {refreshed.script_name}: {refreshed.status}", expanded=True):
        st.write(f"Job ID: `{refreshed.job_id}`")
        if refreshed.status in {"queued", "running"}:
            st.caption(
                "Worker is starting or running. Heavy jobs load Python modules in the "
                "background first: the log below updates automatically."
            )
        st.code(tail_log(Path(refreshed.log_path)), language="text")
    if refreshed.status in {"completed", "failed", "cancelled"}:
        if refreshed.status == "completed":
            st.success("Job completed successfully.")
        elif refreshed.status == "failed":
            st.error("Job failed. See log for details.")
        else:
            st.warning("Job cancelled.")
        render_job_output_downloads(Path(refreshed.job_dir))
        return
    if job_is_running(refreshed):
        import time

        time.sleep(3)
        st.rerun()


def disable_if_job_running() -> bool:
    state = get_active_job_state(st.session_state.get("active_job_id"))
    return job_is_running(state)


def launch_job(script_name: str, config: dict) -> None:
    from artifact_ui.components.job_runner import start_job

    state = start_job(script_name, config)
    st.session_state.active_job_id = state.job_id
    st.rerun()
