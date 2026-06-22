from __future__ import annotations

from dataclasses import dataclass
from multiprocessing import Process, cpu_count
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from logical_level.constraint_satisfaction.csp_evaluation.csp_evaluator import (
    CSPEvaluatorImpl,
)
from logical_level.constraint_satisfaction.csp_evaluation.csp_scheduler import (
    CSPScheduler,
    CSPSchedulerFactory,
)
from logical_level.constraint_satisfaction.csp_evaluation.csp_solver_factory import (
    CPSSolverFactory,
)
from utils.evaluation_config import (
    create_config,
    get_measurement_config_for_approach,
    get_scenarios,
)
from utils.console_utils import configure_utf8_stdio
from utils.multiprocessing_config import configure_spawn_start_method


class SceneGenerationProcess(Process):
    def __init__(self, test: CSPScheduler, core_id: int, measurement_name) -> None:
        super().__init__(
            target=test.run,
            args=(core_id,),
            name=f"process on {core_id} - {measurement_name}",
            daemon=True,
        )


@dataclass
class EvaluationRunConfig:
    approaches: List[str]
    vessel_counts: List[int]
    obstacle_count: int = 0
    num_seeds: int = 1
    base_random_seed: int = 1234
    max_cores: int = 1
    output_dir: Optional[Path] = None
    verbose: Optional[bool] = None


@dataclass
class EvaluationRunResult:
    num_jobs: int
    num_seeds: int
    output_dir: Optional[Path]


def build_evaluation_jobs(
    config: EvaluationRunConfig,
) -> List[Tuple[CSPScheduler, str, int]]:
    tests: List[Tuple[CSPScheduler, str, int]] = []
    for seed_index in range(config.num_seeds):
        for approach in config.approaches:
            for vessel_count in config.vessel_counts:
                measurement_config = get_measurement_config_for_approach(approach)
                random_seed = measurement_config.RANDOM_SEED + seed_index
                actor_number = (vessel_count, config.obstacle_count)
                measurement_name = (
                    f"{measurement_config.BASE_NAME}_{actor_number[0]}_vessel_"
                    f"{actor_number[1]}_obstacle_scenarios"
                )
                eval_config = create_config(measurement_config, approach, random_seed)
                verbose = (
                    config.verbose
                    if config.verbose is not None
                    else measurement_config.VERBOSE
                )
                solver = CPSSolverFactory.factory(
                    eval_config.algorithm_desc,
                    verbose,
                )
                evaluator = CSPEvaluatorImpl(
                    solver,
                    measurement_name,
                    eval_config,
                    verbose,
                )
                scenarios = get_scenarios(
                    actor_number[0],
                    actor_number[1],
                    approach,
                )
                scheduler = CSPSchedulerFactory.factory(
                    evaluator,
                    scenarios,
                    random_seed,
                    measurement_config.WARMUPS,
                    measurement_config.AVERAGE_TIME_PER_SCENE,
                    eval_config.init_method,
                )
                tests.append((scheduler, measurement_name, actor_number[0]))
    tests.sort(key=lambda item: item[2])
    return tests


def run_evaluation(
    config: EvaluationRunConfig,
    log_callback: Optional[Callable[[str], None]] = None,
) -> EvaluationRunResult:
    configure_utf8_stdio()
    configure_spawn_start_method()
    tests = build_evaluation_jobs(config)
    core_count = min(config.max_cores, cpu_count(), max(len(tests), 1))
    if log_callback:
        log_callback(f"Starting {len(tests)} jobs on {core_count} core(s).")

    processes: List[Process] = []
    index = 0
    while index < len(tests):
        processes = [process for process in processes if process.is_alive()]
        if len(processes) < core_count:
            scheduler, measurement_name, _ = tests[index]
            process = SceneGenerationProcess(
                scheduler, index % core_count, measurement_name
            )
            process.start()
            processes.append(process)
            if log_callback:
                log_callback(
                    f"Started job {index + 1}/{len(tests)}: {measurement_name}"
                )
            index += 1
        else:
            for process in processes:
                process.join(timeout=0.1)

    for process in processes:
        process.join()

    if log_callback:
        log_callback("All evaluation jobs completed.")
    return EvaluationRunResult(
        num_jobs=len(tests),
        num_seeds=config.num_seeds,
        output_dir=config.output_dir,
    )


def main() -> None:
    configure_spawn_start_method()
    default_config = EvaluationRunConfig(
        approaches=["rs-msr"],
        vessel_counts=[3],
        num_seeds=1,
        max_cores=cpu_count(),
    )
    run_evaluation(default_config, log_callback=print)


if __name__ == "__main__":
    main()
