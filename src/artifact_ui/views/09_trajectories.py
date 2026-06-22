import streamlit as st

from artifact_ui.components.dataset_state import require_active_dataset
from artifact_ui.components.eval_data_loader import load_eval_datas_cached
from artifact_ui.components.running_state import (disable_if_job_running,
                                                  launch_job)
from artifact_ui.components.time_estimator import (estimate_trajectory,
                                                   format_duration)

st.title("Trajectory Generation")

pkl_path = require_active_dataset()

eval_datas = load_eval_datas_cached(pkl_path=str(pkl_path))
record_index = st.number_input(
    "Record index",
    min_value=0,
    max_value=max(len(eval_datas) - 1, 0),
    value=0,
)
vessels = len(eval_datas[int(record_index)].best_scene or {})
estimate = estimate_trajectory(vessels)
st.info(
    f"Worst case: **{format_duration(estimate.worst_case_seconds)}** | "
    f"Typical: **{format_duration(estimate.typical_seconds)}**"
)
verbose = st.checkbox(
    "Verbose logging",
    value=False,
    help=(
        "Log each RRT iteration with the tree node closest to the goal "
        "(position and distance)."
    ),
)
st.caption(
    "RRT runs headless (ENABLE_RRT_ANIMATION=false). Stops at first feasible path. "
    "When the job finishes, download the zip archive in the job panel below."
)

if st.button("Generate trajectories", disabled=disable_if_job_running()):
    launch_job(
        "generate_trajectories",
        {
            "pkl_path": str(pkl_path),
            "record_index": int(record_index),
            "verbose": verbose,
        },
    )
