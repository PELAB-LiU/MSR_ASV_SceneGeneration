from typing import List

import numpy as np

from functional_level.models.functional_model_manager import FunctionalModelManager
from global_config import GlobalConfig
from logical_level.constraint_satisfaction.aggregates import (
    ActorAggregate,
    AggregateAll,
)
from logical_level.constraint_satisfaction.evaluation_data import EvaluationData
from logical_level.constraint_satisfaction.evolutionary_computation.pymoo_nsga2_algorithm import (
    PyMooNSGA2Algorithm,
)
from logical_level.constraint_satisfaction.evolutionary_computation.pymoo_nsga3_algorithm import (
    PyMooNSGA3Algorithm,
)
from logical_level.constraint_satisfaction.rejection_sampling.rejection_sampling_pipeline import (
    BaseRejectionSampling,
    CDRejectionSampling,
    TwoStepCDRejectionSampling,
    TwoStepRejectionSampling,
)
from logical_level.mapping.instance_initializer import RandomInstanceInitializer
from logical_level.models.logical_model_manager import LogicalModelManager
from utils.scenario import Scenario

MSR_SB_II = "sb-msr2"
MSR_SB_III = "sb-msr3"
DC_SB_II = "sb-base"
DC_SB_III = "sb-base3"
MSR_CDRS_PS = "rs-msr"
DC_RS = "rs"
MSR_CDRS = "cd-rs"
DC_RS_PS = "ts-rs"

# All config groups implemented in code (includes experimental configs not in the paper).
APPROACH_OPTIONS = [
    MSR_SB_II,
    MSR_SB_III,
    DC_SB_II,
    DC_SB_III,
    MSR_CDRS_PS,
    DC_RS,
    MSR_CDRS,
    DC_RS_PS,
]

# Configurations compared in the paper (Table: compared approaches). MSR_SB_II is excluded.
PAPER_APPROACH_OPTIONS = [
    DC_RS,
    DC_SB_II,
    DC_SB_III,
    DC_RS_PS,
    MSR_CDRS,
    MSR_CDRS_PS,
    MSR_SB_III,
]

APPROACH_LABELS = {
    DC_RS: "BaseRS: Base · rejection sampling (RS)",
    DC_SB_II: "BaseSBII: Base · search-based (SB) with NSGA-II",
    DC_SB_III: "BaseSBIII: Base · search-based (SB) with NSGA-III",
    DC_RS_PS: "BaseRSP: Base · two-step rejection sampling (RS+PS)",
    MSR_CDRS: "MSRRS: MSR · CD rejection sampling (CDRS)",
    MSR_CDRS_PS: "MSRRSP: MSR · CD rejection sampling + PS (CDRS+PS)",
    MSR_SB_III: "MSRSBIII: MSR · search-based (SB) with NSGA-III",
    MSR_SB_II: "MSRSBII: MSR · search-based (SB) with NSGA-II (not in paper)",
}

APPROACH_DESCRIPTIONS = {
    DC_RS: (
        "**Base** workflow with **rejection sampling (RS)** as the constraint-satisfaction "
        "engine. Baseline from prior work (Frey et al.). Compared in RQ1, RQ2, and AB."
    ),
    DC_SB_II: (
        "**Base** workflow with **search-based (SB)** optimization using **NSGA-II**. "
        "Compared in RQ1 and RQ2."
    ),
    DC_SB_III: (
        "**Base** workflow with **search-based (SB)** optimization using **NSGA-III**. "
        "Compared in RQ1 and RQ2."
    ),
    DC_RS_PS: (
        "**Base** workflow with **two-step rejection sampling (RS+PS)**. "
        "Compared in AB (assurance benchmark)."
    ),
    MSR_CDRS: (
        "**MSR** workflow with **CD rejection sampling (CDRS)**. Only compatible with MSR "
        "because it depends on functional state machines (FSMs). Compared in AB."
    ),
    MSR_CDRS_PS: (
        "**MSR** workflow with **CD rejection sampling plus post-processing (CDRS+PS)**. "
        "Requires FSMs from MSR. Compared in RQ1, RQ2, and AB."
    ),
    MSR_SB_III: (
        "**MSR** workflow with **search-based (SB)** optimization using **NSGA-III**. "
        "Compared in RQ1 and RQ2."
    ),
}

APPROACH_COMPARED_IN = {
    DC_RS: "RQ1, RQ2, AB",
    DC_SB_II: "RQ1, RQ2",
    DC_SB_III: "RQ1, RQ2",
    DC_RS_PS: "AB",
    MSR_CDRS: "AB",
    MSR_CDRS_PS: "RQ1, RQ2, AB",
    MSR_SB_III: "RQ1, RQ2",
}

MSR_APPROACHES = {MSR_SB_II, MSR_SB_III, MSR_CDRS_PS, MSR_CDRS}
DC_SB_APPROACHES = {DC_SB_II, DC_SB_III}
RS_APPROACHES = {DC_RS, DC_RS_PS, MSR_CDRS_PS, MSR_CDRS}
BOUNDED_APPROACHES = {MSR_SB_II, MSR_SB_III, DC_SB_II, DC_SB_III, MSR_CDRS_PS}
UNBOUNDED_APPROACHES = {DC_RS, DC_RS_PS, MSR_CDRS}


class MeasurementConfig:
    WARMUPS = 2
    RANDOM_SEED = 1234
    TIMEOUT = 600
    INIT_METHOD = RandomInstanceInitializer.name
    AVERAGE_TIME_PER_SCENE = GlobalConfig.FOUR_MINUTES_IN_SEC
    VERBOSE = True
    BASE_NAME = "test"


class MSRMeasurementConfig(MeasurementConfig):
    WARMUPS = 2
    RANDOM_SEED = 1234
    TIMEOUT = GlobalConfig.FOUR_MINUTES_IN_SEC
    AVERAGE_TIME_PER_SCENE = GlobalConfig.FOUR_MINUTES_IN_SEC
    # AVERAGE_TIME_PER_SCENE = 295818.70775175095
    INIT_METHOD = RandomInstanceInitializer.name
    VERBOSE = False
    BASE_NAME = "MSR_evaluation"


class BaseSBMeasurementConfig(MeasurementConfig):
    WARMUPS = 2
    RANDOM_SEED = 1234
    TIMEOUT = GlobalConfig.FOUR_MINUTES_IN_SEC
    AVERAGE_TIME_PER_SCENE = GlobalConfig.FOUR_MINUTES_IN_SEC
    # AVERAGE_TIME_PER_SCENE = 295818.70775175095
    INIT_METHOD = RandomInstanceInitializer.name
    VERBOSE = False
    BASE_NAME = "DC_evaluation"


class RSMeasurementConfig(MeasurementConfig):
    WARMUPS = 2
    RANDOM_SEED = 1234
    TIMEOUT = np.inf  # No timeout for RS
    AVERAGE_TIME_PER_SCENE = GlobalConfig.FOUR_MINUTES_IN_SEC
    # AVERAGE_TIME_PER_SCENE = 295818.70775175095
    INIT_METHOD = RandomInstanceInitializer.name
    VERBOSE = False
    BASE_NAME = "DC_evaluation"


class DummyMeasurementConfig(MeasurementConfig):
    WARMUPS = 2
    RANDOM_SEED = 1234
    TIMEOUT = 10
    INIT_METHOD = RandomInstanceInitializer.name
    AVERAGE_TIME_PER_SCENE = 10
    VERBOSE = False
    BASE_NAME = "dummy_test"


class MiniUSVMeasurementConfig(MeasurementConfig):
    WARMUPS = 0
    RANDOM_SEED = 1234
    TIMEOUT = 30
    INIT_METHOD = RandomInstanceInitializer.name
    VERBOSE = True
    BASE_NAME = "mini_usv_test"


def get_measurement_config_for_approach(approach: str) -> MeasurementConfig:
    if approach in MSR_APPROACHES:
        return MSRMeasurementConfig()
    if approach in DC_SB_APPROACHES:
        return BaseSBMeasurementConfig()
    if approach in {DC_RS, DC_RS_PS}:
        return RSMeasurementConfig()
    raise ValueError(f"Unknown approach: {approach}")


def get_scenarios(
    vessel_number: int, obstacle_number: int, config_group: str
) -> List[Scenario]:
    if config_group in {MSR_SB_II, MSR_SB_III, MSR_CDRS_PS, MSR_CDRS}:
        return FunctionalModelManager.get_x_vessel_y_obstacle_scenarios(
            vessel_number, obstacle_number
        )
    elif config_group in {DC_SB_II, DC_SB_III, DC_RS, DC_RS_PS}:
        return LogicalModelManager.get_x_vessel_y_obstacle_scenarios(
            vessel_number, obstacle_number
        )
    else:
        raise ValueError(f"Unknown config group: {config_group}")


def create_config(
    meas_config: MeasurementConfig, config_group: str, random_seed: int
) -> EvaluationData:
    config = EvaluationData(
        timeout=meas_config.TIMEOUT,
        init_method=meas_config.INIT_METHOD,
        random_seed=random_seed,
        aggregate_strat=ActorAggregate.name,
        config_group=config_group,
    )
    if config_group == MSR_SB_II:
        config.population_size = 15
        config.mutate_eta = 20
        config.mutate_prob = 0.8
        config.crossover_eta = 15
        config.crossover_prob = 1.0
        config.algorithm_desc = PyMooNSGA2Algorithm.algorithm_desc()
        config.aggregate_strat = ActorAggregate.name
    elif config_group == MSR_SB_III:
        config.population_size = 30
        config.mutate_eta = 15
        config.mutate_prob = 1
        config.crossover_eta = 5
        config.crossover_prob = 1
        config.algorithm_desc = PyMooNSGA3Algorithm.algorithm_desc()
    elif config_group == DC_SB_II:
        config.population_size = 10
        config.mutate_eta = 15
        config.mutate_prob = 0.8
        config.crossover_eta = 20
        config.crossover_prob = 1
        config.algorithm_desc = PyMooNSGA2Algorithm.algorithm_desc()
    elif config_group == DC_SB_III:
        config.population_size = 8
        config.mutate_eta = 5
        config.mutate_prob = 1
        config.crossover_eta = 20
        config.crossover_prob = 0.8
        config.algorithm_desc = PyMooNSGA3Algorithm.algorithm_desc()
        config.aggregate_strat = ActorAggregate.name
    elif config_group == MSR_CDRS_PS:
        config.population_size = 1
        config.aggregate_strat = AggregateAll.name
        config.algorithm_desc = TwoStepCDRejectionSampling.algorithm_desc()
    elif config_group == DC_RS:
        config.population_size = 1
        config.aggregate_strat = AggregateAll.name
        config.algorithm_desc = BaseRejectionSampling.algorithm_desc()
    elif config_group == MSR_CDRS:
        config.population_size = 1
        config.aggregate_strat = AggregateAll.name
        config.algorithm_desc = CDRejectionSampling.algorithm_desc()
    elif config_group == DC_RS_PS:
        config.population_size = 1
        config.aggregate_strat = AggregateAll.name
        config.algorithm_desc = TwoStepRejectionSampling.algorithm_desc()
    else:
        raise ValueError(f"Unknown config group: {config_group}")
    return config


# nsga3_vessel_sb_msr_config = EvaluationData(population_size=6, mutate_eta=15, mutate_prob=0.8,
#                             crossover_eta=20, crossover_prob=1, timeout=MEAS_GlobalConfig.TIMEOUT,
#                             init_method=MEAS_GlobalConfig.INIT_METHOD, random_seed=MEAS_GlobalConfig.RANDOM_SEED, aggregate_strat=ActorAggregate.name,
#                             config_group='SB-MSR', algorithm_desc=PyMooNSGA3Algorithm.algorithm_desc)


# ga_config = EvaluationData(population_size=4, num_parents_mating = 4,
#                         mutate_eta=20, mutate_prob=0.2, crossover_eta=10,
#                         crossover_prob=0.2, timeout=MEAS_GlobalConfig.TIMEOUT, init_method=MEAS_GlobalConfig.INIT_METHOD,
#                         random_seed=MEAS_GlobalConfig.RANDOM_SEED, aggregate_strat=AggregateAll.name)

# nsga2_all_config = EvaluationData(population_size=50, mutate_eta=10, mutate_prob=1.0,
#                             crossover_eta=20, crossover_prob=0.8, timeout=MEAS_GlobalConfig.TIMEOUT,
#                             init_method=MEAS_GlobalConfig.INIT_METHOD, random_seed=MEAS_GlobalConfig.RANDOM_SEED, aggregate_strat=AggregateAll.name)
# nsga2_category_config = EvaluationData(population_size=4, mutate_eta=5, mutate_prob=0.8,
#                             crossover_eta=15, crossover_prob=1.0, timeout=MEAS_GlobalConfig.TIMEOUT,
#                             init_method=MEAS_GlobalConfig.INIT_METHOD, random_seed=MEAS_GlobalConfig.RANDOM_SEED, aggregate_strat=CategoryAggregate.name)


# nsga3_all_config = EvaluationData(population_size=20, mutate_eta=1, mutate_prob=0.8,
#                             crossover_eta=1, crossover_prob=1.0, timeout=MEAS_GlobalConfig.TIMEOUT,
#                             init_method=MEAS_GlobalConfig.INIT_METHOD, random_seed=MEAS_GlobalConfig.RANDOM_SEED, aggregate_strat=AggregateAll.name)
# nsga3_category_config = EvaluationData(population_size=4, mutate_eta=5, mutate_prob=0.8,
#                             crossover_eta=15, crossover_prob=1.0, timeout=TIMEOUT,
#                             init_method=MEAS_GlobalConfig.INIT_METHOD, random_seed=MEAS_GlobalConfig.RANDOM_SEED, aggregate_strat=CategoryAggregate.name)


# pso_config = EvaluationData(population_size=30, c_1=2.5, c_2=1.0, w=0.4, timeout=MEAS_GlobalConfig.TIMEOUT,
#                           init_method=MEAS_GlobalConfig.INIT_METHOD, random_seed=MEAS_GlobalConfig.RANDOM_SEED, aggregate_strat=AggregateAllSwarm.name)

# de_config = EvaluationData(population_size=15, mutate_prob=0.5, crossover_prob=0.5,
#                           timeout=MEAS_GlobalConfig.TIMEOUT, init_method=MEAS_GlobalConfig.INIT_METHOD, random_seed=MEAS_GlobalConfig.RANDOM_SEED, aggregate_strat=AggregateAll.name)
