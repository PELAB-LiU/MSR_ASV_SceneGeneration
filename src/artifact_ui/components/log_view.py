"""Scrollable log display helpers for the artifact UI."""

from __future__ import annotations

import streamlit as st


def render_scrollable_log(
    log_text: str,
    *,
    height: int = 280,
    label: str = "Log",
    placeholder: str = "(no log output yet)",
    key: str,
) -> None:
    st.text_area(
        label,
        value=log_text or placeholder,
        height=height,
        disabled=True,
        label_visibility="collapsed",
        key=key,
    )
