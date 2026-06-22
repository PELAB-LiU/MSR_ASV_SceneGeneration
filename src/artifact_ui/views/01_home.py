from pathlib import Path

import streamlit as st

from global_config import GlobalConfig
from utils.file_system_utils import IMAGES_FOLDER

st.title("MODELS26 Artifact Evaluation")
st.markdown("""
This artifact supports **Automated Generation of Functionally Complete Assurance Suites
for COLREGS-Compliance of Autonomous Surface Vehicles**.

### Badges targeted
- **Artifact Evaluated (Reusable)**: Dockerized Streamlit UI, configurable reproduction
- **Artifact Available**: MIT-licensed software on Zenodo (dataset separately on Zenodo, CC-BY 4.0)
""")

st.subheader("Usage workflow")
st.markdown("""
Scene generation writes many separate JSON measurement files on the server. For analysis
in this UI, datasets are usually handled as a single compressed `.pkl.gz` archive.
**Compress** merges many files into one archive so loading is practical (millions of
separate files would be very slow). **Annotate hash** adds graph-shape hash fields used
to distinguish functional equivalence classes; hashing must run in one unified pass over the full
dataset, so it is applied after compression. Reload the processed archive, then use the
visualization and analysis pages below.
""")

usage_diagram = Path(IMAGES_FOLDER) / "usage.png"
if not usage_diagram.is_file():
    usage_diagram = Path(IMAGES_FOLDER) / "usage.svg"
if usage_diagram.is_file():
    st.image(str(usage_diagram), use_container_width=True)
else:
    st.warning("Usage diagram not found (`assets/images/usage.png`).")

st.subheader("Kick-the-tires checklist (~30 minutes)")
st.markdown("""
1. **Data Manager → Load**: upload a dataset or download from Zenodo
2. **Scenario Browser**: inspect records and COLREG scene plots
3. **Evaluation Plots**: render paper-style figures from the loaded dataset
4. **Scene Generation**: run a minimal configuration (1 seed, 1 approach, 2 vessels, 1 core)
5. Optional: **Trajectories**, **Data Manager** utility tabs, hyperparameter tools
""")

st.subheader("Global time budgets")
st.table(
    {
        "Operation": [
            "Scene generation (per scheduler job)",
            "Full configured batch",
            "Hyperparameter tuning (per combination)",
            "Trajectory generation (per vessel chain)",
            "Data compress / annotate",
        ],
        "Worst-case formula": [
            f"{GlobalConfig.FOUR_MINUTES_IN_SEC}s × number of scenarios",
            "Σ job budgets × seeds / cores",
            "180s × combinations / cores",
            f"{GlobalConfig.TWO_HOURS_IN_SEC}s × vessels",
            "~1s × record count",
        ],
    }
)
