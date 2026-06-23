"""Load evaluation data in Streamlit with visible progress and session caching."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from typing import Callable, List, Optional

import pandas as pd
import streamlit as st

from artifact_ui.components.log_view import render_scrollable_log
from concrete_level.data_parser import EvalDataParser, ProgressCallback
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from utils.file_folder_opener import get_artifact_file_opener

HIDDEN_DF_COLUMNS = {
    "best_scene",
    "path",
    "risk_vector",
    "error_message",
    "best_fitness",
}


def invalidate_eval_data_cache() -> None:
    st.session_state.pop("eval_datas_cache_key", None)
    st.session_state.pop("eval_datas_cache", None)
    st.session_state.pop("eval_browse_df_cache_key", None)
    st.session_state.pop("eval_browse_df_cache", None)
    st.session_state.pop("eval_plot_figure", None)
    st.session_state.pop("eval_plot_png", None)
    st.session_state.pop("eval_plot_name", None)
    st.session_state.pop("colreg_scene_index", None)
    st.session_state.pop("colreg_scene_png", None)
    st.session_state.pop("colreg_scene_plotly", None)
    st.session_state.pop("compress_estimate_count", None)


def _invalidate_browse_df_cache() -> None:
    st.session_state.pop("eval_browse_df_cache_key", None)
    st.session_state.pop("eval_browse_df_cache", None)


def is_eval_datas_cached(
    *,
    pkl_path: Optional[str] = None,
    input_dirs: Optional[List[str]] = None,
) -> bool:
    if pkl_path:
        cache_key = _cache_key_for_pkl(pkl_path)
    elif input_dirs:
        cache_key = _cache_key_for_dirs(input_dirs)
    else:
        return False
    return (
        st.session_state.get("eval_datas_cache_key") == cache_key
        and st.session_state.get("eval_datas_cache") is not None
    )


def render_dataset_loader(pkl_path: str, *, key_prefix: str) -> Optional[List[EvaluationData]]:
    """Load evaluation data on demand; return None until the user clicks Load."""
    name = Path(pkl_path).name
    if is_eval_datas_cached(pkl_path=pkl_path):
        count = len(st.session_state.eval_datas_cache)
        status_col, action_col = st.columns([4, 1])
        with status_col:
            st.success(f"**{name}** in memory ({count} records).")
        with action_col:
            if st.button("Reload", key=f"{key_prefix}_reload"):
                _invalidate_browse_df_cache()
                load_eval_datas_cached(pkl_path=pkl_path, force_reload=True)
                st.rerun()
        return st.session_state.eval_datas_cache

    st.info(
        f"Active dataset: **{name}**. "
        "Click **Load dataset** to read it into memory (large archives may take minutes)."
    )
    if st.button("Load dataset", key=f"{key_prefix}_load", type="primary"):
        _invalidate_browse_df_cache()
        load_eval_datas_cached(pkl_path=pkl_path)
        st.rerun()
    return None


def _cache_key_for_pkl(pkl_path: str) -> str:
    path = Path(pkl_path)
    mtime = path.stat().st_mtime if path.is_file() else 0
    return f"pkl:{path.resolve()}:{mtime}"


def _cache_key_for_dirs(input_dirs: List[str]) -> str:
    parts = []
    for directory in sorted(input_dirs):
        path = Path(directory)
        if path.is_dir():
            parts.append(f"{path.resolve()}:{path.stat().st_mtime}")
        else:
            parts.append(str(path))
    return "dirs:" + "|".join(parts)


def _make_streamlit_progress(
    progress_bar,
    detail_slot,
) -> ProgressCallback:
    def callback(current: int, total: int, message: str) -> None:
        fraction = 0.0 if total <= 0 else min(float(current) / float(total), 1.0)
        progress_bar.progress(
            fraction,
            text=f"{message} ({current}/{total})" if total > 0 else message,
        )
        detail_slot.caption(message)

    return callback


def load_eval_datas_cached(
    *,
    pkl_path: Optional[str] = None,
    input_dirs: Optional[List[str]] = None,
    force_reload: bool = False,
) -> List[EvaluationData]:
    if pkl_path:
        cache_key = _cache_key_for_pkl(pkl_path)
        source_label = f"compressed dataset **{Path(pkl_path).name}**"
    elif input_dirs:
        cache_key = _cache_key_for_dirs(input_dirs)
        source_label = f"{len(input_dirs)} directory tree(s)"
    else:
        raise ValueError("Provide pkl_path or input_dirs")

    if (
        not force_reload
        and st.session_state.get("eval_datas_cache_key") == cache_key
        and st.session_state.get("eval_datas_cache") is not None
    ):
        return st.session_state.eval_datas_cache

    progress_bar = st.progress(0.0, text="Preparing to load evaluation data…")
    detail_slot = st.empty()
    callback = _make_streamlit_progress(progress_bar, detail_slot)
    parser = EvalDataParser()

    with st.status(
        f"Loading evaluation data from {source_label}", expanded=True
    ) as status:
        st.write(
            "Large archives can take **several minutes**. "
            "Progress below shows each evaluation record file being processed."
        )
        if pkl_path:
            st.write(
                "For **.pkl.gz** archives, decompression and unpickling run as one step; "
                "the bar may pause for several minutes on large datasets."
            )
            eval_datas = parser.load_pkl_gzip_compressed_eval_data(
                pkl_path,
                progress_callback=callback,
            )
        else:
            opener = get_artifact_file_opener(open_dirs=input_dirs)
            parser = EvalDataParser(opener)
            eval_datas = parser.load_eval_data_complex(
                dirs=input_dirs,
                progress_callback=callback,
            )
        st.write(f"**{len(eval_datas)}** evaluation record(s) loaded.")
        status.update(
            label=f"Loaded {len(eval_datas)} evaluation record(s)",
            state="complete",
        )

    progress_bar.progress(1.0, text=f"Ready: {len(eval_datas)} evaluation record(s)")
    st.session_state.eval_datas_cache_key = cache_key
    st.session_state.eval_datas_cache = eval_datas
    return eval_datas


def eval_datas_to_dataframe(
    eval_datas: List[EvaluationData],
    progress_callback: Optional[ProgressCallback] = None,
) -> pd.DataFrame:
    rows = []
    total = len(eval_datas)
    for index, item in enumerate(eval_datas):
        if progress_callback is not None and (
            index == 0 or index % 25 == 0 or index == total - 1
        ):
            progress_callback(
                index,
                total,
                f"Building browse table row {index + 1}/{total}",
            )
        row = {
            key: getattr(item, key, None)
            for key in EvalDataParser.EVAL_DATA_COLUMN_NAMES
        }
        rows.append(row)
    if progress_callback is not None and total > 0:
        progress_callback(total, total, f"Browse table ready ({total} rows)")
    df = pd.DataFrame(rows)
    display_cols = [col for col in df.columns if col not in HIDDEN_DF_COLUMNS]
    return df[display_cols]


def load_eval_dataframe_cached(pkl_path: str) -> pd.DataFrame:
    eval_datas = load_eval_datas_cached(pkl_path=pkl_path)
    df_cache_key = f"df:{st.session_state.get('eval_datas_cache_key', '')}"
    if (
        st.session_state.get("eval_browse_df_cache_key") == df_cache_key
        and st.session_state.get("eval_browse_df_cache") is not None
    ):
        return st.session_state.eval_browse_df_cache

    progress_bar = st.progress(0.0, text="Building table view…")
    detail_slot = st.empty()
    callback = _make_streamlit_progress(progress_bar, detail_slot)
    dataframe = eval_datas_to_dataframe(eval_datas, progress_callback=callback)
    progress_bar.progress(1.0, text=f"Table ready: {len(dataframe)} rows")
    st.session_state.eval_browse_df_cache_key = df_cache_key
    st.session_state.eval_browse_df_cache = dataframe
    return dataframe


def load_eval_datas_from_dirs_cached(input_dirs: List[str]) -> List[EvaluationData]:
    return load_eval_datas_cached(input_dirs=input_dirs)


def render_plot_generation_log(
    log_text: str,
    *,
    use_expander: bool = True,
    expanded: bool = False,
    key: str = "plot_generation_log",
) -> None:
    """Show captured plot-build stdout in a scrollable, read-only text area."""
    if not log_text:
        return

    def _body() -> None:
        render_scrollable_log(
            log_text,
            height=220,
            label="Plot generation log",
            key=key,
        )

    if use_expander:
        with st.expander("Generation log", expanded=expanded):
            _body()
    else:
        st.markdown("**Generation log**")
        _body()


def with_plot_generation_progress(
    plot_name: str,
    build_fn: Callable[[], object],
):
    progress_bar = st.progress(0.0, text=f"Preparing plot: {plot_name}…")
    log_buffer = io.StringIO()
    with st.status(f"Generating plot: {plot_name}", expanded=True) as status:
        st.caption(
            "Aggregating loaded evaluation records into the figure "
            "(statistical test output appears in the log below)."
        )
        with contextlib.redirect_stdout(log_buffer), contextlib.redirect_stderr(
            log_buffer
        ):
            result = build_fn()
        log_text = log_buffer.getvalue().strip()
        if log_text:
            render_plot_generation_log(
                log_text,
                use_expander=False,
                key="plot_generation_log_active",
            )
        else:
            st.write("No log output from plot generation.")
        status.update(label=f"Plot ready: {plot_name}", state="complete")

    progress_bar.progress(1.0, text=f"Plot ready: {plot_name}")
    st.session_state.eval_plot_generation_log = log_text
    st.session_state.eval_plot_log_in_status = bool(log_text)
    return result
