"""Browser-native upload/download helpers (works in Docker; no Tkinter/Zenity)."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional, Union

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from utils.artifact_config import ArtifactConfig

PKL_GZ_EXTENSIONS = ["gz"]
JSON_EXTENSIONS = ["json"]
ARCHIVE_EXTENSIONS = ["zip"]
MAX_STREAMLIT_MB = 300
MAX_UPLOAD_MB = MAX_STREAMLIT_MB
UPLOAD_SIZE_HELP = (
    f"Maximum upload size: {MAX_UPLOAD_MB} MB per file. "
    f"Browser message limit: {MAX_STREAMLIT_MB} MB (tables/plots)."
)


def upload_root() -> Path:
    config = ArtifactConfig.from_env()
    root = config.data_dir / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_filename(name: str) -> str:
    return Path(name).name


def _extract_zip_safe(data: bytes, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for member in archive.namelist():
            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise ValueError(f"Unsafe path in archive: {member}")
        archive.extractall(dest)


def persist_uploaded_file(uploaded: UploadedFile, namespace: str) -> Path:
    dest_dir = upload_root() / namespace
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / _safe_filename(uploaded.name)
    dest.write_bytes(uploaded.getbuffer())
    return dest


def materialize_uploads_to_dir(
    uploads: List[UploadedFile],
    namespace: str,
) -> Path:
    work_dir = upload_root() / namespace / uuid.uuid4().hex[:12]
    work_dir.mkdir(parents=True, exist_ok=True)
    for uploaded in uploads:
        name = _safe_filename(uploaded.name)
        data = bytes(uploaded.getbuffer())
        if name.endswith(".zip"):
            _extract_zip_safe(data, work_dir)
        else:
            (work_dir / name).write_bytes(data)
    return work_dir


def server_output_path(filename: str) -> Path:
    config = ArtifactConfig.from_env()
    config.ensure_dirs()
    return config.output_dir / _safe_filename(filename)


def create_zip_from_directory(source_dir: Path, zip_path: Path) -> Path:
    from utils.archive_utils import create_zip_from_directory as _create_zip

    return _create_zip(source_dir, zip_path)


def create_zip_archive(
    sources: List[Union[str, Path]], zip_path: Union[str, Path]
) -> Path:
    from utils.archive_utils import create_zip_archive as _create_zip_archive

    return _create_zip_archive(sources, zip_path)


def upload_file_picker(
    label: str,
    session_path_key: str,
    uploader_key: str,
    *,
    type: Optional[List[str]] = None,
    help_text: Optional[str] = None,
) -> Optional[str]:
    uploaded = st.file_uploader(
        label,
        type=type,
        key=uploader_key,
        help=help_text or f"Choose a file on your computer. {UPLOAD_SIZE_HELP}",
    )
    if uploaded is not None:
        path = persist_uploaded_file(uploaded, uploader_key)
        if session_path_key == "loaded_pkl_path":
            from artifact_ui.components.eval_data_loader import \
                invalidate_eval_data_cache

            invalidate_eval_data_cache()
        st.session_state[session_path_key] = str(path)
    path = st.session_state.get(session_path_key)
    if path:
        st.caption(f"Ready: **{Path(path).name}**")
    return path


def upload_files_to_dir_picker(
    label: str,
    session_dir_key: str,
    uploader_key: str,
    *,
    type: Optional[List[str]] = None,
    help_text: Optional[str] = None,
) -> Optional[str]:
    uploads = st.file_uploader(
        label,
        type=type,
        accept_multiple_files=True,
        key=uploader_key,
        help=help_text
        or f"Select one or more files, or a .zip archive. {UPLOAD_SIZE_HELP}",
    )
    if uploads:
        work_dir = materialize_uploads_to_dir(list(uploads), uploader_key)
        st.session_state[session_dir_key] = str(work_dir)
    path = st.session_state.get(session_dir_key)
    if path:
        st.caption("Upload prepared.")
    return path


def output_filename_input(label: str, key: str, default: str) -> str:
    return st.text_input(
        label,
        value=default,
        key=key,
        help="Used only to describe the expected download file name.",
    )


def offer_file_download(
    file_path: Union[str, Path],
    label: str,
    download_key: str,
) -> None:
    path = Path(file_path)
    if not path.is_file():
        return
    if path.name.endswith(".gz"):
        mime = "application/gzip"
    elif path.name.endswith(".zip"):
        mime = "application/zip"
    elif path.suffix == ".png":
        mime = "image/png"
    elif path.suffix == ".csv":
        mime = "text/csv"
    else:
        mime = "application/octet-stream"
    st.download_button(
        label=label,
        data=path.read_bytes(),
        file_name=path.name,
        key=download_key,
        mime=mime,
    )


def offer_bytes_download(
    data: bytes,
    label: str,
    file_name: str,
    download_key: str,
    *,
    mime: str = "application/zip",
) -> None:
    st.download_button(
        label=label,
        data=data,
        file_name=file_name,
        key=download_key,
        mime=mime,
    )


def render_job_output_downloads(job_dir: Union[str, Path]) -> None:
    result_file = Path(job_dir) / "result.json"
    if not result_file.is_file():
        return
    result = json.loads(result_file.read_text(encoding="utf-8"))
    status = result.get("status")
    if status not in {"completed", "cancelled", "failed"}:
        return
    output_files = result.get("output_files", [])
    if not output_files:
        if status == "completed":
            st.info("No downloadable archive was produced for this job.")
        elif status in {"cancelled", "failed"}:
            st.info("No partial results were saved before the job stopped.")
        return
    if status == "completed":
        st.markdown("**Download results to your computer:**")
    else:
        st.markdown("**Download partial results to your computer:**")
        st.caption("Archive contains outputs produced before the job stopped.")
    for index, file_path in enumerate(output_files):
        offer_file_download(
            file_path,
            label=f"Download {Path(file_path).name}",
            download_key=f"dl_{Path(job_dir).name}_{index}",
        )
