from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, List, Optional

from concrete_level.data_parser import EvalDataParser
from concrete_level.models.trajectory_manager import TrajectoryManager
from concrete_level.trajectory_generation.trajectory_generator import \
    TrajectoryGenerator
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from utils.file_folder_opener import get_artifact_file_opener


@dataclass
class TrajectoryResult:
    eval_data_path: str
    num_vessels: int
    overall_eval_time: float


def generate_trajectories(
    eval_data_path: str,
    log_callback: Optional[Callable[[str], None]] = None,
) -> TrajectoryResult:
    os.environ.setdefault("ENABLE_RRT_ANIMATION", "false")
    opener = get_artifact_file_opener(open_files=[eval_data_path])
    parser = EvalDataParser(opener)
    data_models = parser.load_data_models_from_files([eval_data_path])
    if not data_models:
        raise ValueError(f"No evaluation data found at {eval_data_path}")
    eval_data = data_models[0]
    if log_callback:
        log_callback(f"Generating trajectories for {eval_data.scenario_name}...")
    trajectory_manager = TrajectoryManager(eval_data.best_scene)
    traj_gen = TrajectoryGenerator(eval_data, trajectory_manager.scenario)
    if log_callback:
        log_callback(
            f"Trajectory generation completed in {traj_gen.trajectories is not None}."
        )
    return TrajectoryResult(
        eval_data_path=eval_data_path,
        num_vessels=len(eval_data.best_scene),
        overall_eval_time=0.0,
    )


def generate_trajectories_from_pkl(
    pkl_path: str,
    record_index: int = 0,
    log_callback: Optional[Callable[[str], None]] = None,
    verbose: bool = False,
) -> TrajectoryResult:
    opener = get_artifact_file_opener(open_files=[pkl_path])
    parser = EvalDataParser(opener)
    eval_datas: List[EvaluationData] = parser.load_pkl_gzip_compressed_eval_data(
        pkl_path
    )
    if record_index >= len(eval_datas):
        raise IndexError(
            f"Record index {record_index} out of range ({len(eval_datas)} records)"
        )
    eval_data = eval_datas[record_index]
    if log_callback:
        log_callback(f"Generating trajectories for record {record_index}...")
    trajectory_manager = TrajectoryManager(eval_data.best_scene)
    TrajectoryGenerator(
        eval_data,
        trajectory_manager.scenario,
        verbose=verbose,
        log_callback=log_callback,
    )
    return TrajectoryResult(
        eval_data_path=pkl_path,
        num_vessels=len(eval_data.best_scene),
        overall_eval_time=0.0,
    )


def main() -> None:
    parser = EvalDataParser()
    data_models = parser.load_data_models()
    if not data_models:
        return
    eval_data = data_models[0]
    trajectory_manager = TrajectoryManager(eval_data.best_scene)
    from visualization.colreg_scenarios.scenario_plot_manager import \
        ScenarioPlotManager

    ScenarioPlotManager(trajectory_manager)
    traj_gen = TrajectoryGenerator(eval_data, trajectory_manager.scenario)
    ScenarioPlotManager(TrajectoryManager(traj_gen.trajectories))


if __name__ == "__main__":
    main()
