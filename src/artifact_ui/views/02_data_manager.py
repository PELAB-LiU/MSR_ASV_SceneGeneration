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
from utils.artifact_config import (ZENODO_MEASUREMENT_FILES, ArtifactConfig,
                                   list_zenodo_measurement_files,
                                   resolve_zenodo_pkl)

st.title("Data Manager")

config = ArtifactConfig.from_env()
config.ensure_dirs()

tab_compress, tab_annotate, tab_load, tab_unzip = st.tabs(
    ["Compress", "Annotate Hash", "Load", "Unzip"]
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
        with st.expander("Estimate from active dataset"):
            if st.button("Load active dataset for estimate", key="compress_estimate_load"):
                pkl_path = require_active_dataset()
                eval_datas = load_eval_datas_cached(pkl_path=pkl_path)
                st.session_state.compress_estimate_count = len(eval_datas)
            record_count = st.session_state.get("compress_estimate_count", 0)
            if record_count:
                st.caption(f"Loaded record count: **{record_count}**")
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
    st.caption(
        "Downloads every file from the Zenodo record into the artifact data folder "
        "and packages the full record as a zip you can save to your computer."
    )
    if "zenodo_record_doi" not in st.session_state:
        st.session_state.zenodo_record_doi = config.zenodo_record_doi
    zenodo_doi = st.text_input(
        "Zenodo record DOI or URL",
        key="zenodo_record_doi",
        help=(
            "Examples: 10.5281/zenodo.20792733, " "https://zenodo.org/records/20792733"
        ),
    )
    if st.button("Download from Zenodo", disabled=disable_if_job_running()):
        launch_job("zenodo_download", {"zenodo_record_doi": zenodo_doi})

    zenodo_measurements = list_zenodo_measurement_files(config)
    if zenodo_measurements:
        st.caption("Select which measurement archive to use for browsing and plots.")
        measurement_labels = [path.name for path in zenodo_measurements]
        if "zenodo_measurement_choice" not in st.session_state:
            st.session_state.zenodo_measurement_choice = measurement_labels[0]
        if st.session_state.zenodo_measurement_choice not in measurement_labels:
            st.session_state.zenodo_measurement_choice = measurement_labels[0]
        selected_name = st.selectbox(
            "Measurement dataset",
            options=measurement_labels,
            key="zenodo_measurement_choice",
        )
        zenodo_pkl = resolve_zenodo_pkl(config, filename=selected_name)
        if st.button("Load Zenodo dataset", disabled=disable_if_job_running()):
            if zenodo_pkl is not None:
                set_active_dataset(str(zenodo_pkl))
                st.success(f"Loaded {zenodo_pkl.name} for browsing and plotting.")
            else:
                st.error(f"Measurement file not found: {selected_name}")
    elif (config.data_dir / "full").is_dir() and any(
        (config.data_dir / "full").iterdir()
    ):
        st.info(
            "Zenodo files are on disk, but no known measurement archives were found. "
            f"Expected one of: {', '.join(ZENODO_MEASUREMENT_FILES)}"
        )

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
