import streamlit as st

from artifact_ui.components.browser_upload import (JSON_EXTENSIONS,
                                                   PKL_GZ_EXTENSIONS,
                                                   output_filename_input,
                                                   upload_file_picker,
                                                   upload_files_to_dir_picker)
from artifact_ui.components.dataset_state import (active_dataset_name,
                                                  require_active_dataset,
                                                  set_active_dataset)
from artifact_ui.components.eval_data_loader import load_eval_datas_cached
from artifact_ui.components.running_state import (disable_if_job_running,
                                                  launch_job)
from artifact_ui.components.time_estimator import (estimate_data_utility,
                                                   format_duration)
from utils.artifact_config import ArtifactConfig, resolve_zenodo_pkl

st.title("Data Manager")

config = ArtifactConfig.from_env()
config.ensure_dirs()

tab_compress, tab_load, tab_annotate, tab_unzip = st.tabs(
    ["Compress", "Load", "Annotate Hash", "Unzip"]
)

with tab_compress:
    st.caption(
        "Upload measurement files from your computer (.json, .pkl.gz, or .zip archive)."
    )
    uploaded_dir = upload_files_to_dir_picker(
        "Upload input files",
        session_dir_key="compress_upload_dir",
        uploader_key="compress_upload",
        type=JSON_EXTENSIONS + PKL_GZ_EXTENSIONS + ["zip"],
    )
    input_dirs = [uploaded_dir] if uploaded_dir else None

    output_filename_input(
        "Download file name (informational)",
        key="compress_output_name",
        default="compressed.pkl.gz",
    )
    record_count = 0
    if active_dataset_name():
        with st.expander("Estimate from active dataset (loads with progress)"):
            pkl_path = require_active_dataset()
            eval_datas = load_eval_datas_cached(pkl_path=pkl_path)
            record_count = len(eval_datas)
    estimate = estimate_data_utility(record_count or 100)
    st.caption(
        f"Estimated time: worst: {format_duration(estimate.worst_case_seconds)}, "
        f"typical: {format_duration(estimate.typical_seconds)}"
    )
    if st.button(
        "Compress eval data", key="compress", disabled=disable_if_job_running()
    ):
        if not input_dirs:
            st.error("Upload input files from your computer.")
        else:
            launch_job("compress_eval_data", {"input_dirs": input_dirs})

with tab_load:
    st.subheader("Upload dataset from your computer")
    upload_file_picker(
        "Upload .pkl.gz measurement file",
        session_path_key="loaded_pkl_path",
        uploader_key="data_manager_pkl_upload",
        type=PKL_GZ_EXTENSIONS,
        help_text=(
            "Choose a file on your computer. It is stored on the artifact server "
            "for browsing and plots (only the file name is shown here)."
        ),
    )
    st.caption(
        "After loading or uploading a dataset, open **Scenario Browser**, "
        "**Evaluation Plots**, or **Trajectories**."
    )

    st.subheader("Download full dataset from Zenodo")
    st.caption(f"Zenodo record DOI: {config.zenodo_record_doi}")
    if st.button("Download from Zenodo", disabled=disable_if_job_running()):
        launch_job("zenodo_download", {})

    zenodo_pkl = resolve_zenodo_pkl(config)
    if zenodo_pkl is not None:
        if st.button("Load Zenodo dataset", disabled=disable_if_job_running()):
            set_active_dataset(str(zenodo_pkl))
            st.success(f"Loaded {zenodo_pkl.name} for browsing and plotting.")

    st.subheader("Active dataset")
    current_name = active_dataset_name()
    if current_name:
        st.info(f"Current dataset: **{current_name}**")
    else:
        st.info("No dataset loaded yet.")

with tab_annotate:
    annotate_in = upload_file_picker(
        "Upload input .pkl.gz",
        session_path_key="annotate_input_path",
        uploader_key="annotate_input_upload",
        type=PKL_GZ_EXTENSIONS,
    )
    if not annotate_in and active_dataset_name():
        annotate_in = require_active_dataset()
        st.caption(f"Using active dataset: **{active_dataset_name()}**")

    output_filename_input(
        "Download file name (informational)",
        key="annotate_output_name",
        default="annotated.pkl.gz",
    )

    if st.button("Annotate hash", key="annotate", disabled=disable_if_job_running()):
        if not annotate_in:
            st.error("Upload a .pkl.gz file or load a dataset in the Load tab.")
        else:
            launch_job("annotate_hash", {"input_pkl": annotate_in})

with tab_unzip:
    st.caption("Upload a .pkl.gz from your computer, or use the active loaded dataset.")
    pkl_input = upload_file_picker(
        "Upload .pkl.gz to unzip",
        session_path_key="unzip_pkl_path",
        uploader_key="unzip_pkl_upload",
        type=PKL_GZ_EXTENSIONS,
    )
    if not pkl_input and active_dataset_name():
        pkl_input = require_active_dataset()
        st.caption(f"Using active dataset: **{active_dataset_name()}**")

    if st.button("Unzip eval data", key="unzip", disabled=disable_if_job_running()):
        if not pkl_input:
            st.error("Upload a .pkl.gz file or load a dataset in the Load tab.")
        else:
            launch_job("unzip_eval_data", {"pkl_path": pkl_input})
