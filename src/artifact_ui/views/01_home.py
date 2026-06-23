from pathlib import Path

import streamlit as st

from global_config import GlobalConfig
from utils.file_system_utils import IMAGES_FOLDER

st.title("MODELS26 Artifact Evaluation")
st.markdown("""
This artifact supports **Automated Generation of Functionally Complete Assurance Suites
for COLREGS-Compliance of Autonomous Surface Vehicles**.

### Badges targeted
- **Artifact Evaluated (Functional + Reusable)**: Dockerized Streamlit UI, configurable reproduction, technical documentation
- **Artifact Available**: MIT-licensed software on Zenodo (dataset separately on Zenodo, CC-BY 4.0, DOI: [10.5281/zenodo.20792734](https://doi.org/10.5281/zenodo.20792734))
""")

st.subheader("Usage workflow")
st.markdown("""
Scene generation writes many separate JSON measurement files on the server. For analysis in this UI,
datasets are handled as a single compressed, annotated `.pkl.gz` archive (loading millions of
individual JSON files in the browser would be impractical).

The diagram below shows **two ways** to reach the analysis pages:

**Generate your own measurements**

1. **Scene Generation**: run a job and download the result zip.
2. **Data Manager -> Compress**: merge JSON into one `.pkl.gz` and download.
3. **Data Manager -> Annotate hash**: add graph-shape hash fields in one pass over the full archive; download when done.
4. **Data Manager -> Load**: activate the annotated `.pkl.gz` as the active dataset.

**Use the published Zenodo dataset**

1. **Data Manager -> Load**: download from Zenodo and load a pre-annotated `.pkl.gz` (skips compress/annotate).

**Analyze the active dataset**

- **Scenario Browser**, **Evaluation Plots**, **Trajectories**, and **Hyperparam Evaluation**.

**Optional utility**

- **Data Manager -> Unzip**: export human-readable JSON from a loaded archive.
""")

usage_diagram = Path(IMAGES_FOLDER) / "usage.png"
if not usage_diagram.is_file():
    usage_diagram = Path(IMAGES_FOLDER) / "usage.svg"
if usage_diagram.is_file():
    st.image(str(usage_diagram), use_container_width=True)
else:
    st.warning("Usage diagram not found (`assets/images/usage.svg`).")

st.subheader("Kick-the-tires checklist (~30 minutes)")
st.markdown("""
Designed for a commodity laptop without full paper-scale runtime.

**Explore published data (fastest)**

1. **Data Manager -> Load**: download from Zenodo (or upload a small `.pkl.gz`) and activate the dataset.
2. **Scenario Browser**: inspect the table and render one COLREG scene.
3. **Evaluation Plots**: generate one plot type from the loaded dataset.

**Try the generation pipeline (optional)**

4. **Scene Generation**: minimal run: **1 seed**, **1 approach**, **2 vessels**, **1 core**; download the result zip.
5. **Data Manager -> Compress**, then **Annotate hash**, then **Load** the processed archive (see workflow above).

**Optional**

- **Trajectories** on one record; **Hyperparam Evaluation** on uploaded tuning JSON; **Unzip** for human-readable JSON exports.
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
