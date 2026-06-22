from __future__ import annotations

from collections import Counter
from typing import List, Optional

import pandas as pd

from concrete_level.data_parser import EvalDataParser, ProgressCallback
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from utils.file_folder_opener import get_artifact_file_opener


def get_config_key(obj: EvaluationData) -> tuple:
    return (
        obj.population_size,
        obj.mutate_eta,
        obj.mutate_prob,
        obj.crossover_eta,
        obj.crossover_prob,
    )


def main() -> None:
    dp = EvalDataParser()
    eval_datas = dp.load_dirs_merged_as_models()
    result = evaluate_hyperparameters_from_models(eval_datas)
    print(result)


def evaluate_hyperparameters_from_models(
    eval_datas: List[EvaluationData],
) -> pd.DataFrame:
    config_counter = Counter(get_config_key(obj) for obj in eval_datas if obj.is_valid)
    rows = []
    for most_common_config, count in config_counter.most_common():
        grouped_objects = [
            obj
            for obj in eval_datas
            if get_config_key(obj) == most_common_config and obj.is_valid
        ]
        total_eval_time = sum(obj.evaluation_time for obj in grouped_objects)
        rows.append(
            {
                "population_size": most_common_config[0],
                "mutate_eta": most_common_config[1],
                "mutate_prob": most_common_config[2],
                "crossover_eta": most_common_config[3],
                "crossover_prob": most_common_config[4],
                "count": count,
                "total_eval_time": total_eval_time,
            }
        )
    return pd.DataFrame(rows)


def evaluate_hyperparameters(
    input_dirs: List[str],
    progress_callback: Optional[ProgressCallback] = None,
) -> pd.DataFrame:
    opener = get_artifact_file_opener(open_dirs=input_dirs)
    parser = EvalDataParser(opener)
    eval_datas = parser.load_eval_data_complex(
        dirs=input_dirs,
        progress_callback=progress_callback,
    )
    return evaluate_hyperparameters_from_models(eval_datas)


if __name__ == "__main__":
    main()
