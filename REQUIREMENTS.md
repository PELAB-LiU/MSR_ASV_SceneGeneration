Hardware
========
- CPU: 4+ cores recommended for scene generation; paper measurements used Intel Haswell-class CPU
- RAM: 8 GB minimum; 32 GB recommended for full reproduction runs
- Disk: 10 GB free space (Docker image, bundled sample, optional full dataset download)
- Display: not required (headless Docker + web browser)

Software
========
- Docker Engine 24+ and Docker Compose v2
- Web browser for the Streamlit UI at http://localhost:8501
- Optional (non-Docker): Python 3.12, see package.json for pinned dependencies
- Browser uploads: max 300 MB per file (Streamlit `server.maxUploadSize`)

Python dependencies are pinned in package.json (pythonDependencies.common).
Install locally with: python scripts/install_dependencies.py

Environment variables (Docker)
==============================
- PYTHONPATH=/app/src
- ARTIFACT_DATA_DIR=/data
- ARTIFACT_OUTPUT_DIR=/output
- ENABLE_RRT_ANIMATION=false (headless RRT in artifact mode)
- MPLBACKEND=Agg

Dataset (separate Zenodo publication)
=====================================
- Full evaluation data is published separately under CC-BY 4.0
- Dataset DOI: `10.5281/zenodo.20792734` (hardcoded in `src/utils/artifact_config.py`)
