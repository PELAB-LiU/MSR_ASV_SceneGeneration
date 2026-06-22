"""Configuration for MODELS26 artifact evaluation (Docker / Streamlit UI)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

ZENODO_DATASET_DOI = "10.5281/zenodo.20792734"

ZENODO_MEASUREMENT_FILES = (
    "main_measurements.pkl.gz",
    "msr_measurements_for_full_coverage.pkl.gz",
)


@dataclass(frozen=True)
class ArtifactConfig:
    data_dir: Path
    output_dir: Path
    zenodo_record_doi: str
    jobs_dir: Path

    @classmethod
    def from_env(cls) -> "ArtifactConfig":
        data_dir = Path(os.environ.get("ARTIFACT_DATA_DIR", "data"))
        output_dir = Path(os.environ.get("ARTIFACT_OUTPUT_DIR", "output"))
        jobs = output_dir / "jobs"
        return cls(
            data_dir=data_dir,
            output_dir=output_dir,
            zenodo_record_doi=ZENODO_DATASET_DOI,
            jobs_dir=jobs,
        )

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "full").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "uploads").mkdir(parents=True, exist_ok=True)


def zenodo_record_id_from_doi(doi: str) -> str:
    """Extract numeric Zenodo record id from a DOI, URL, or bare record id."""
    doi = doi.strip()
    if doi.startswith("http"):
        path = urlparse(doi).path.strip("/")
        token = path.split("/")[-1]
    else:
        token = doi.split("/")[-1]
    if token.startswith("zenodo."):
        return token.removeprefix("zenodo.")
    return token


def fetch_zenodo_record(record_id: str) -> dict:
    url = f"https://zenodo.org/api/records/{record_id}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def download_zenodo_dataset(
    config: ArtifactConfig,
    target_dir: Optional[Path] = None,
    log_callback=None,
) -> Path:
    """Download all files from the configured Zenodo dataset record."""
    target = target_dir or (config.data_dir / "full")
    target.mkdir(parents=True, exist_ok=True)
    record_id = zenodo_record_id_from_doi(config.zenodo_record_doi)
    if log_callback:
        log_callback(f"Fetching Zenodo record {record_id}...")
    record = fetch_zenodo_record(record_id)
    files = record.get("files", [])
    if not files:
        raise RuntimeError(f"No files found in Zenodo record {record_id}")
    for file_info in files:
        file_url = file_info["links"]["self"]
        filename = file_info["key"]
        dest = target / filename
        if log_callback:
            log_callback(f"Downloading {filename}...")
        with requests.get(file_url, stream=True, timeout=300) as response:
            response.raise_for_status()
            with dest.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        handle.write(chunk)
        if log_callback:
            log_callback(f"Saved {filename}")
    return target


def list_zenodo_measurement_files(config: ArtifactConfig) -> list[Path]:
    """Return known Zenodo measurement archives present under data_dir/full."""
    full_dir = config.data_dir / "full"
    return [
        full_dir / name
        for name in ZENODO_MEASUREMENT_FILES
        if (full_dir / name).is_file()
    ]


def resolve_zenodo_pkl(
    config: ArtifactConfig, filename: Optional[str] = None
) -> Optional[Path]:
    """Return a compressed dataset downloaded from Zenodo, if present on disk."""
    full_dir = config.data_dir / "full"
    if filename:
        path = full_dir / filename
        return path if path.is_file() else None
    for name in ZENODO_MEASUREMENT_FILES:
        path = full_dir / name
        if path.is_file():
            return path
    if full_dir.is_dir():
        for path in sorted(full_dir.glob("*.pkl.gz")):
            return path
    return None
