from __future__ import annotations

from pathlib import Path
from typing import List

from concrete_level.data_parser import EvalDataParser
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from utils.file_folder_opener import get_artifact_file_opener


def unzip_eval_data(pkl_path: str, output_dir: str) -> Path:
    opener = get_artifact_file_opener(
        open_files=[pkl_path],
        open_dirs=[output_dir],
    )
    parser = EvalDataParser(opener)
    eval_datas: List[EvaluationData] = parser.load_pkl_gzip_compressed_eval_data(
        pkl_path
    )
    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    for eval_data in eval_datas:
        asset_folder = (
            folder
            / eval_data.measurement_name
            / eval_data.config_group.upper()
            / f"{eval_data.algorithm_desc}_{eval_data.aggregate_strat}"
            / str(eval_data.random_seed)
        )
        asset_folder.mkdir(parents=True, exist_ok=True)
        timestamp = eval_data.timestamp.replace(":", "-")
        eval_data.path = str(
            asset_folder / f"{eval_data.scenario_name}_{timestamp}.json"
        )
        eval_data.save_to_json()
    return folder


def main() -> None:
    import tkfilebrowser

    from utils.file_system_utils import GEN_DATA_FOLDER

    dp = EvalDataParser()
    files = dp._opener.ask_open_files(
        initialdir=GEN_DATA_FOLDER,
        filetypes=[("pkl.gz files", "*.pkl.gz")],
    )
    if not files:
        print("No file selected")
        return
    folders = tkfilebrowser.askopendirnames(initialdir=GEN_DATA_FOLDER)
    if not folders:
        print("No folder selected")
        return
    unzip_eval_data(files[0], folders[0])


if __name__ == "__main__":
    main()
