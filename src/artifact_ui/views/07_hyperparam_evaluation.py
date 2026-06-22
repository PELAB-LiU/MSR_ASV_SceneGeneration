import io
import sys
import zipfile
from pathlib import Path

import streamlit as st

from artifact_ui.components.browser_upload import (JSON_EXTENSIONS,
                                                   offer_bytes_download,
                                                   upload_files_to_dir_picker)
from artifact_ui.components.eval_data_loader import \
    load_eval_datas_from_dirs_cached

_scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))
from evaluate_hyperparameters import \
    evaluate_hyperparameters_from_models  # noqa: E402

st.title("Hyperparameter Evaluation")

uploaded_dir = upload_files_to_dir_picker(
    "Upload JSON files or a .zip of a measurement tree",
    session_dir_key="hyperparam_eval_upload_dir",
    uploader_key="hyperparam_eval_upload",
    type=JSON_EXTENSIONS + ["zip"],
    help_text="Pick files with your browser. Zip a folder if you have many JSON files.",
)
input_dirs = [uploaded_dir] if uploaded_dir else None

if st.button("Evaluate hyperparameters"):
    if not input_dirs:
        st.error("Upload JSON measurement files from your computer.")
    else:
        try:
            eval_datas = load_eval_datas_from_dirs_cached(input_dirs)
            result = evaluate_hyperparameters_from_models(eval_datas)
            st.session_state.hyperparam_eval_result = result
            st.dataframe(result, use_container_width=True)
        except Exception as exc:
            st.error(str(exc))

result = st.session_state.get("hyperparam_eval_result")
if result is not None:
    csv_bytes = result.to_csv(index=False).encode("utf-8")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("hyperparam_evaluation.csv", csv_bytes)
    offer_bytes_download(
        zip_buffer.getvalue(),
        label="Download results (zip)",
        file_name="hyperparam_evaluation.zip",
        download_key="dl_hyperparam_eval_result",
    )
