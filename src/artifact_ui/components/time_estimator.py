"""Worst-case runtime estimates for artifact operations."""

from __future__ import annotations

from dataclasses import dataclass
from multiprocessing import cpu_count
from typing import List

from functional_level.models.functional_model_manager import \
    FunctionalModelManager
from global_config import GlobalConfig
from logical_level.models.logical_model_manager import LogicalModelManager
from utils.evaluation_config import (MSR_APPROACHES, UNBOUNDED_APPROACHES,
                                     get_measurement_config_for_approach)


@dataclass
class TimeEstimate:
    worst_case_seconds: float
    typical_seconds: float
    warning: str = ""


def _scenario_count(approach: str, vessel_count: int, obstacle_count: int = 0) -> int:
    if approach in MSR_APPROACHES:
        return len(
            FunctionalModelManager.get_x_vessel_y_obstacle_scenarios(
                vessel_count,
                obstacle_count,
            )
        )
    return len(
        LogicalModelManager.get_x_vessel_y_obstacle_scenarios(
            vessel_count,
            obstacle_count,
        )
    )


def estimate_scene_generation(
    approaches: List[str],
    vessel_counts: List[int],
    num_seeds: int,
    max_cores: int,
    obstacle_count: int = 0,
) -> TimeEstimate:
    if not approaches or not vessel_counts:
        return TimeEstimate(0, 0)
    unbounded = [
        approach for approach in approaches if approach in UNBOUNDED_APPROACHES
    ]
    warning = ""
    if unbounded:
        warning = (
            "Selected rejection-sampling approaches (rs, cd-rs, ts-rs) have "
            "unbounded runtime (TIMEOUT = infinity)."
        )
    total_worst = 0.0
    for approach in approaches:
        measurement = get_measurement_config_for_approach(approach)
        per_scene = measurement.AVERAGE_TIME_PER_SCENE
        for vessel_count in vessel_counts:
            scenarios = _scenario_count(approach, vessel_count, obstacle_count)
            job_budget = per_scene * max(scenarios, 1)
            total_worst += job_budget * num_seeds
    cores = max(1, min(max_cores, cpu_count()))
    parallel_worst = total_worst / cores
    typical = parallel_worst * 0.3 if not unbounded else parallel_worst
    return TimeEstimate(parallel_worst, typical, warning)


def estimate_hyperparam(
    max_combinations: int, timeout: int, max_cores: int
) -> TimeEstimate:
    cores = max(1, min(max_cores, cpu_count()))
    worst = (timeout * max_combinations) / cores
    return TimeEstimate(worst, worst * 0.5)


def estimate_trajectory(num_vessels: int) -> TimeEstimate:
    worst = GlobalConfig.TWO_HOURS_IN_SEC * max(num_vessels, 1)
    return TimeEstimate(worst, min(worst * 0.05, 600))


def estimate_data_utility(record_count: int) -> TimeEstimate:
    worst = max(record_count, 1)
    return TimeEstimate(worst, worst * 0.5)


def format_duration(seconds: float) -> str:
    if seconds == float("inf"):
        return "unbounded"
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
