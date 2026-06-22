from __future__ import annotations

import os
from multiprocessing import cpu_count
from pathlib import Path
from typing import Callable, Optional

from tqdm import tqdm

from concrete_level.concrete_scene_abstractor import ConcreteSceneAbstractor
from concrete_level.data_parser import EvalDataParser
from concrete_level.trajectory_generation.scene_builder import SceneBuilder
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from utils.file_folder_opener import get_artifact_file_opener
from utils.multiprocessing_config import get_spawn_context

os.environ.setdefault("PYTHONHASHSEED", "0")


def annotate_hash(eval_data: EvaluationData) -> EvaluationData | None:
    eval_data.path = None
    if not eval_data.is_valid:
        return eval_data
    scenario = ConcreteSceneAbstractor.get_abstractions_from_eval(eval_data)
    fec_level_hash = scenario.functional_scenario.fec_shape_hash()
    is_relevant_by_fec = scenario.functional_scenario.is_relevant_by_fec
    is_ambiguous_by_fec = scenario.functional_scenario.is_ambiguous_by_fec
    eval_data.best_scene = SceneBuilder(eval_data.best_scene).build(
        second_level_hash=fec_level_hash,
        is_relevant_by_fec=is_relevant_by_fec,
        is_ambiguous_by_fec=is_ambiguous_by_fec,
    )
    return eval_data


def annotate_hash_file(
    input_pkl: str,
    output_pkl: str,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Path:
    opener = get_artifact_file_opener(
        open_files=[input_pkl],
        save_file=output_pkl,
    )
    parser = EvalDataParser(opener)
    eval_datas = parser.load_pkl_gzip_compressed_eval_data(input_pkl)
    if log_callback:
        log_callback(f"Annotating {len(eval_datas)} records...")
    with get_spawn_context().Pool(cpu_count() or 1) as pool:
        processed = list(
            tqdm(
                pool.imap_unordered(annotate_hash, eval_datas),
                total=len(eval_datas),
                desc="Hashing eval datas",
            )
        )
    processed_eval_datas = [entry for entry in processed if entry is not None]
    parser.dump_eval_datas_to_gz(processed_eval_datas, output_pkl)
    if log_callback:
        log_callback(f"Saved annotated data to {output_pkl}")
    return Path(output_pkl)


def main() -> None:
    from utils.file_folder_opener import get_default_file_opener
    from utils.file_system_utils import GEN_DATA_FOLDER

    opener = get_default_file_opener()
    save_path = opener.ask_save_file(
        initialdir=GEN_DATA_FOLDER,
        filetypes=[("gz files", "*.gz")],
    )
    if save_path is None:
        print("No file selected")
        return
    input_files = opener.ask_open_files(
        initialdir=GEN_DATA_FOLDER,
        filetypes=[("pkl.gz files", "*.pkl.gz")],
    )
    if not input_files:
        print("No input file selected")
        return
    annotate_hash_file(input_files[0], save_path)


if __name__ == "__main__":
    main()
