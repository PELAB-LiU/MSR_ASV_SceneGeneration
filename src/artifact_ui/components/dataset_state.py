"""Session helpers for the active evaluation dataset (no internal paths in UI)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import streamlit as st

from artifact_ui.components.eval_data_loader import invalidate_eval_data_cache


def active_dataset_path() -> Optional[str]:
    return st.session_state.get("loaded_pkl_path")


def active_dataset_name() -> Optional[str]:
    path = active_dataset_path()
    if not path:
        return None
    return Path(path).name


def set_active_dataset(path: str) -> None:
    invalidate_eval_data_cache()
    st.session_state.loaded_pkl_path = str(path)


def require_active_dataset() -> str:
    path = active_dataset_path()
    if not path:
        st.warning(
            "Load a dataset from **Data Manager → Load** first "
            "(upload from your computer or download from Zenodo)."
        )
        st.stop()
    return path
