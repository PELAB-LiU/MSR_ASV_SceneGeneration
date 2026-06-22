from __future__ import annotations

from pathlib import Path
from typing import List

from concrete_level.data_parser import EvalDataParser
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from utils.file_folder_opener import get_artifact_file_opener


def compress_eval_data(
    input_dirs: List[str],
    output_path: str,
) -> Path:
    opener = get_artifact_file_opener(open_dirs=input_dirs, save_file=output_path)
    parser = EvalDataParser(opener)
    eval_datas: List[EvaluationData] = parser.load_eval_data_complex(dirs=input_dirs)
    for eval_data in eval_datas:
        eval_data.path = None
    parser.dump_eval_datas_to_gz(eval_datas, output_path)
    return Path(output_path)


def main() -> None:
    from utils.file_folder_opener import get_default_file_opener

    opener = get_default_file_opener()
    save_path = opener.ask_save_file(filetypes=[("gz files", "*.gz")])
    if save_path is None:
        print("No file selected")
        return
    dirs = opener.ask_open_dirs()
    if not dirs:
        print("No directories selected")
        return
    compress_eval_data(dirs, save_path)


if __name__ == "__main__":
    main()
