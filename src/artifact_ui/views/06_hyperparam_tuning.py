from multiprocessing import cpu_count

import streamlit as st

from artifact_ui.components.running_state import (disable_if_job_running,
                                                  launch_job)
from artifact_ui.components.time_estimator import (estimate_hyperparam,
                                                   format_duration)
from utils.evaluation_config import APPROACH_LABELS, DC_SB_III, MSR_SB_III
from utils.hyperparam_combinations import (build_nsga_combinations,
                                           format_nsga_combination)

HYPERPARAM_CONFIG_GROUPS = [DC_SB_III, MSR_SB_III]

st.title("Hyperparameter Tuning")

vessel_count = st.number_input("Vessel count", min_value=2, max_value=6, value=6)
config_group = st.selectbox(
    "Config group",
    HYPERPARAM_CONFIG_GROUPS,
    index=HYPERPARAM_CONFIG_GROUPS.index(DC_SB_III),
    format_func=lambda key: APPROACH_LABELS.get(key, key),
)
max_combinations = st.number_input(
    "Max combinations",
    min_value=1,
    max_value=20,
    value=3,
    help=(
        "How many NSGA-III hyperparameter tuples to evaluate. Each combination "
        "uses a population size from {2, 4, 8, 15, 30} (in order) together with "
        "fixed mutation/crossover settings, and runs a full measurement batch across "
        "all logical scenarios for the selected vessel count."
    ),
)
st.caption(
    "One **combination** = one hyperparameter setting tested end-to-end on the full "
    "scenario batch. Increasing this value tries larger population sizes and extends "
    "runtime roughly linearly."
)

planned = build_nsga_combinations(int(max_combinations))
with st.expander(f"Planned combinations ({len(planned)})", expanded=False):
    for index, combination in enumerate(planned, start=1):
        st.markdown(f"- {format_nsga_combination(combination, index, len(planned))}")

max_cores = st.slider("Max cores", 1, cpu_count(), 1)
timeout = st.number_input("Timeout per evaluation (s)", min_value=30, value=180)
verbose = st.checkbox(
    "Verbose logging",
    value=False,
    help=(
        "Log each combination as it starts and finishes, including how many remain. "
        "Runs combinations sequentially on one core so progress appears in order."
    ),
)
if verbose and int(max_cores) > 1:
    st.caption("Verbose mode runs sequentially on one core regardless of Max cores.")

estimate = estimate_hyperparam(int(max_combinations), int(timeout), int(max_cores))
st.info(
    f"Worst case: **{format_duration(estimate.worst_case_seconds)}** | "
    f"Typical: **{format_duration(estimate.typical_seconds)}**"
)
st.caption("When the job finishes, download the zip archive in the job panel below.")

if st.button("Run hyperparameter test", disabled=disable_if_job_running()):
    launch_job(
        "hyperparam_test",
        {
            "vessel_count": int(vessel_count),
            "obstacle_count": 0,
            "config_group": config_group,
            "max_cores": int(max_cores),
            "max_combinations": int(max_combinations),
            "timeout": int(timeout),
            "average_time_per_scene": int(timeout),
            "verbose": verbose,
        },
    )
