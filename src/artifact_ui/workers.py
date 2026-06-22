"""Subprocess worker entry points for long-running artifact jobs."""

from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.archive_utils import create_zip_archive
from utils.file_system_utils import GEN_DATA_FOLDER

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _package_download_zip(
    job_dir: Path,
    sources: List[Path],
    zip_name: str,
) -> List[str]:
    existing = [path for path in sources if path.exists()]
    if not existing:
        return []
    zip_path = job_dir / zip_name
    create_zip_archive(existing, zip_path)
    return [str(zip_path)]


def _evaluation_output_dirs(config_dict: Dict[str, Any]) -> List[Path]:
    from utils.evaluation_config import get_measurement_config_for_approach

    obstacle_count = config_dict.get("obstacle_count", 0)
    folders: List[Path] = []
    for approach in config_dict["approaches"]:
        measurement_config = get_measurement_config_for_approach(approach)
        for vessel_count in config_dict["vessel_counts"]:
            measurement_name = (
                f"{measurement_config.BASE_NAME}_{vessel_count}_vessel_"
                f"{obstacle_count}_obstacle_scenarios"
            )
            folder = Path(GEN_DATA_FOLDER) / measurement_name
            if folder.is_dir():
                folders.append(folder)
    return folders


def _log(log_path: Path, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _write_result(
    job_dir: Path,
    status: str,
    exit_code: int = 0,
    error: str = "",
    output_files: Optional[List[str]] = None,
) -> None:
    result = {
        "status": status,
        "exit_code": exit_code,
        "error": error,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "output_files": output_files or [],
    }
    (job_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


def worker_evaluation(job_dir: str, config_dict: Dict[str, Any]) -> None:
    job_path = Path(job_dir)
    log_path = job_path / "run.log"
    _log(log_path, "Worker process alive; importing evaluation_main…")
    try:
        from evaluation_main import EvaluationRunConfig, run_evaluation

        _log(log_path, "Modules loaded; starting scene generation.")

        config = EvaluationRunConfig(
            approaches=config_dict["approaches"],
            vessel_counts=config_dict["vessel_counts"],
            obstacle_count=config_dict.get("obstacle_count", 0),
            num_seeds=config_dict["num_seeds"],
            base_random_seed=config_dict.get("base_random_seed", 1234),
            max_cores=config_dict["max_cores"],
            output_dir=Path(config_dict.get("output_dir", job_dir)),
            verbose=config_dict.get("verbose", False),
        )
        run_evaluation(config, log_callback=lambda msg: _log(log_path, msg))
        output_files = _package_download_zip(
            job_path,
            _evaluation_output_dirs(config_dict),
            "scene_generation_results.zip",
        )
        if output_files:
            _log(log_path, f"Packaged download archive: {Path(output_files[0]).name}")
        _write_result(job_path, "completed", 0, output_files=output_files)
    except Exception as exc:
        _log(log_path, traceback.format_exc())
        ensure_partial_result_packaged(job_path, "failed", 1, str(exc))


def worker_hyperparam(job_dir: str, config_dict: Dict[str, Any]) -> None:
    job_path = Path(job_dir)
    log_path = job_path / "run.log"
    try:
        from hyperparam_test import HyperparamRunConfig, run_hyperparam_test

        config = HyperparamRunConfig(**config_dict)
        run_hyperparam_test(config, log_callback=lambda msg: _log(log_path, msg))
        output_files = _package_download_zip(
            job_path,
            [Path(GEN_DATA_FOLDER) / "parameter_test_base"],
            "hyperparam_results.zip",
        )
        if output_files:
            _log(log_path, f"Packaged download archive: {Path(output_files[0]).name}")
        _write_result(job_path, "completed", 0, output_files=output_files)
    except Exception as exc:
        _log(log_path, traceback.format_exc())
        ensure_partial_result_packaged(job_path, "failed", 1, str(exc))


def worker_compress(job_dir: str, config_dict: Dict[str, Any]) -> None:
    job_path = Path(job_dir)
    log_path = job_path / "run.log"
    try:
        from compress_eval_data import compress_eval_data

        output_path = job_path / "compressed.pkl.gz"
        output = compress_eval_data(config_dict["input_dirs"], str(output_path))
        output_files = [str(output)]
        _log(log_path, f"Compressed data ready for download: {output}")
        _write_result(job_path, "completed", 0, output_files=output_files)
    except Exception as exc:
        _log(log_path, traceback.format_exc())
        ensure_partial_result_packaged(job_path, "failed", 1, str(exc))


def worker_unzip(job_dir: str, config_dict: Dict[str, Any]) -> None:
    job_path = Path(job_dir)
    log_path = job_path / "run.log"
    try:
        from unzip_eval_data import unzip_eval_data

        output = unzip_eval_data(config_dict["pkl_path"], str(job_path / "unzipped"))
        output_files = _package_download_zip(
            job_path,
            [output],
            "unzipped_eval_data.zip",
        )
        _log(log_path, f"Unzipped data packaged for download: {output}")
        _write_result(job_path, "completed", 0, output_files=output_files)
    except Exception as exc:
        _log(log_path, traceback.format_exc())
        ensure_partial_result_packaged(job_path, "failed", 1, str(exc))


def worker_annotate(job_dir: str, config_dict: Dict[str, Any]) -> None:
    job_path = Path(job_dir)
    log_path = job_path / "run.log"
    try:
        from annotate_hash import annotate_hash_file

        output_path = job_path / "annotated.pkl.gz"
        output = annotate_hash_file(
            config_dict["input_pkl"],
            str(output_path),
            log_callback=lambda msg: _log(log_path, msg),
        )
        output_files = [str(output)]
        _log(log_path, f"Annotated data ready for download: {output}")
        _write_result(job_path, "completed", 0, output_files=output_files)
    except Exception as exc:
        _log(log_path, traceback.format_exc())
        ensure_partial_result_packaged(job_path, "failed", 1, str(exc))


def worker_trajectories(job_dir: str, config_dict: Dict[str, Any]) -> None:
    job_path = Path(job_dir)
    log_path = job_path / "run.log"
    try:
        from generate_trajectories import generate_trajectories_from_pkl

        result = generate_trajectories_from_pkl(
            config_dict["pkl_path"],
            config_dict.get("record_index", 0),
            log_callback=lambda msg: _log(log_path, msg),
            verbose=config_dict.get("verbose", False),
        )
        _log(log_path, f"Trajectories generated for {result.num_vessels} vessels.")
        output_files = _package_download_zip(
            job_path,
            [Path(GEN_DATA_FOLDER) / "RRTStar_algo"],
            "trajectory_results.zip",
        )
        if output_files:
            _log(log_path, f"Packaged download archive: {Path(output_files[0]).name}")
        _write_result(job_path, "completed", 0, output_files=output_files)
    except Exception as exc:
        _log(log_path, traceback.format_exc())
        ensure_partial_result_packaged(job_path, "failed", 1, str(exc))


def worker_zenodo_download(job_dir: str, config_dict: Dict[str, Any]) -> None:
    job_path = Path(job_dir)
    log_path = job_path / "run.log"
    try:
        from utils.artifact_config import (ArtifactConfig,
                                           download_zenodo_dataset)

        artifact_config = ArtifactConfig.from_env()
        target = Path(config_dict.get("target_dir", artifact_config.data_dir / "full"))
        download_zenodo_dataset(
            artifact_config,
            target_dir=target,
            log_callback=lambda msg: _log(log_path, msg),
        )
        output_files = _package_download_zip(
            job_path,
            [target],
            "zenodo_dataset.zip",
        )
        if output_files:
            _log(log_path, f"Packaged download archive: {Path(output_files[0]).name}")
        _write_result(job_path, "completed", 0, output_files=output_files)
    except Exception as exc:
        _log(log_path, traceback.format_exc())
        ensure_partial_result_packaged(job_path, "failed", 1, str(exc))


WORKERS = {
    "evaluation_main": worker_evaluation,
    "hyperparam_test": worker_hyperparam,
    "compress_eval_data": worker_compress,
    "unzip_eval_data": worker_unzip,
    "annotate_hash": worker_annotate,
    "generate_trajectories": worker_trajectories,
    "zenodo_download": worker_zenodo_download,
}

GENERATION_JOB_SPECS = {
    "evaluation_main": (
        _evaluation_output_dirs,
        "scene_generation_results.zip",
    ),
    "hyperparam_test": (
        lambda config_dict: [Path(GEN_DATA_FOLDER) / "parameter_test_base"],
        "hyperparam_results.zip",
    ),
    "generate_trajectories": (
        lambda config_dict: [Path(GEN_DATA_FOLDER) / "RRTStar_algo"],
        "trajectory_results.zip",
    ),
}


def package_generation_outputs(job_dir: Path) -> List[str]:
    state_file = job_dir / "state.json"
    config_file = job_dir / "config.json"
    if not state_file.is_file() or not config_file.is_file():
        return []
    state = json.loads(state_file.read_text(encoding="utf-8"))
    script_name = state.get("script_name")
    if script_name not in GENERATION_JOB_SPECS:
        return []
    config_dict = json.loads(config_file.read_text(encoding="utf-8"))
    sources_fn, zip_name = GENERATION_JOB_SPECS[script_name]
    return _package_download_zip(job_dir, sources_fn(config_dict), zip_name)


def ensure_partial_result_packaged(
    job_dir: Path,
    status: str,
    exit_code: int = 0,
    error: str = "",
) -> List[str]:
    job_path = Path(job_dir)
    result_path = job_path / "result.json"
    if result_path.is_file():
        existing = json.loads(result_path.read_text(encoding="utf-8"))
        if existing.get("output_files"):
            return existing["output_files"]
    output_files = package_generation_outputs(job_path)
    log_path = job_path / "run.log"
    if output_files:
        _log(
            log_path,
            f"Packaged partial download archive: {Path(output_files[0]).name}",
        )
    _write_result(job_path, status, exit_code, error, output_files=output_files)
    return output_files
