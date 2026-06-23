import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parent.parent
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

import streamlit as st

from artifact_ui.components.job_runner import get_active_job_state  # noqa: E402
from artifact_ui.components.running_state import (  # noqa: E402
    init_session_state,
    render_global_status_bar,
    render_job_panel,
)

st.set_page_config(
    page_title="Automated Generation of Functionally Complete Assurance Suites for COLREGS-Compliance of Autonomous Surface Vehicles: MODELS26 Artifact",
    page_icon="🚢",
    layout="wide",
)

init_session_state()
render_global_status_bar()

home = st.Page("views/01_home.py", title="Home", icon="🏠")
data_manager = st.Page("views/02_data_manager.py", title="Data Manager", icon="💾")
scenario_browser = st.Page(
    "views/03_data_browser.py", title="Scenario Browser", icon="📋"
)
eval_plots = st.Page(
    "views/04_evaluation_plots.py", title="Evaluation Plots", icon="📈"
)
scene_gen = st.Page("views/05_scene_generation.py", title="Scene Generation", icon="⚙️")
hyperparam = st.Page(
    "views/06_hyperparam_tuning.py", title="Hyperparam Tuning", icon="🔬"
)
hyper_eval = st.Page(
    "views/07_hyperparam_evaluation.py", title="Hyperparam Evaluation", icon="📊"
)
trajectories = st.Page("views/09_trajectories.py", title="Trajectories", icon="🛤️")

pg = st.navigation(
    [
        home,
        data_manager,
        scenario_browser,
        eval_plots,
        scene_gen,
        hyperparam,
        hyper_eval,
        trajectories,
    ]
)
pg.run()
render_job_panel(get_active_job_state(st.session_state.get("active_job_id")))
