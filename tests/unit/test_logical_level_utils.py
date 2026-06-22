"""Unit tests for utils modules used by the logical level."""

import random
from typing import Optional

import numpy as np
import pytest

from global_config import GlobalConfig
from logical_level.constraint_satisfaction.aggregates import (ActorAggregate,
                                                              AggregateAll)
from logical_level.constraint_satisfaction.assignments import Assignments
from logical_level.constraint_satisfaction.evaluation_cache import (
    EvaluationCache, GeometricProperties, VesselToVesselProperties)
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from logical_level.constraint_satisfaction.evolutionary_computation.pymoo_nsga2_algorithm import \
    PyMooNSGA2Algorithm
from logical_level.constraint_satisfaction.evolutionary_computation.pymoo_nsga3_algorithm import \
    PyMooNSGA3Algorithm
from logical_level.constraint_satisfaction.rejection_sampling.rejection_sampling_pipeline import (
    BaseRejectionSampling, CDRejectionSampling, TwoStepCDRejectionSampling,
    TwoStepRejectionSampling)
from logical_level.constraint_satisfaction.rejection_sampling.scenic_utils import (
    generate_scenario_code, object_to_individual, vessel_object_to_individual)
from logical_level.models.actor_variable import (OSVariable,
                                                 StaticObstacleVariable,
                                                 TSVariable)
from logical_level.models.logical_model_manager import LogicalModelManager
from logical_level.models.values import ObstacleValues, VesselValues
from utils.evaluation_config import (APPROACH_COMPARED_IN,
                                     APPROACH_DESCRIPTIONS, APPROACH_LABELS,
                                     APPROACH_OPTIONS, DC_RS, DC_RS_PS,
                                     DC_SB_II, DC_SB_III, MSR_CDRS,
                                     MSR_CDRS_PS, MSR_SB_II, MSR_SB_III,
                                     PAPER_APPROACH_OPTIONS,
                                     BaseSBMeasurementConfig,
                                     DummyMeasurementConfig,
                                     MSRMeasurementConfig, RSMeasurementConfig,
                                     create_config,
                                     get_measurement_config_for_approach,
                                     get_scenarios)
from utils.general_utils import set_seed
from utils.hyperparam_combinations import (build_nsga_combinations,
                                           format_nsga_combination)
from utils.math_utils import calculate_heading, compute_angle
from utils.serializable import Serializable, get_inner_type, is_optional_type
from utils.static_obstacle_types import SmallObstacle
from utils.vessel_types import ALL_VESSEL_TYPES, CargoShip


@pytest.fixture
def head_on_vessel_assignments() -> Assignments:
    os_var = OSVariable(1)
    ts_var = TSVariable(2, CargoShip())
    assignments = Assignments([os_var, ts_var])
    assignments[os_var] = VesselValues(x=0.0, y=0.0, h=0.0, l=50.0, sp=10.0)
    assignments[ts_var] = VesselValues(x=400.0, y=0.0, h=np.pi, l=50.0, sp=10.0)
    return assignments


@pytest.fixture
def obstacle_collision_assignments() -> Assignments:
    obst_var = StaticObstacleVariable(1, SmallObstacle())
    vessel_var = TSVariable(2, CargoShip())
    assignments = Assignments([obst_var, vessel_var])
    assignments[obst_var] = ObstacleValues(x=0.0, y=0.0, r=20.0)
    assignments[vessel_var] = VesselValues(x=500.0, y=0.0, h=np.pi, l=40.0, sp=8.0)
    return assignments


class NestedSerializable(Serializable):
    value: int

    def __init__(self, value: int) -> None:
        self.value = value


class ParentSerializable(Serializable):
    name: str
    child: NestedSerializable
    note: Optional[str]

    def __init__(
        self, name: str, child: NestedSerializable, note: Optional[str]
    ) -> None:
        self.name = name
        self.child = child
        self.note = note


class TestGeneralUtils:
    def test_set_seed_makes_random_and_numpy_deterministic(self) -> None:
        set_seed(42)
        py_value = random.random()
        np_value = np.random.rand()
        set_seed(42)
        assert random.random() == py_value
        assert np.random.rand() == np_value


class TestMathUtils:
    def test_calculate_heading_east(self) -> None:
        assert calculate_heading(1.0, 0.0) == pytest.approx(0.0)

    def test_calculate_heading_north(self) -> None:
        assert calculate_heading(0.0, 1.0) == pytest.approx(np.pi / 2)

    def test_compute_angle_between_parallel_vectors(self) -> None:
        vec = np.array([1.0, 0.0])
        angle = compute_angle(vec, vec, 1.0, 1.0)
        assert angle == pytest.approx(0.0)

    def test_compute_angle_between_orthogonal_vectors(self) -> None:
        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([0.0, 1.0])
        angle = compute_angle(vec1, vec2, 1.0, 1.0)
        assert angle == pytest.approx(np.pi / 2)


class TestSerializable:
    def test_is_optional_type(self) -> None:
        assert is_optional_type(Optional[str]) is True
        assert is_optional_type(str) is False

    def test_get_inner_type_extracts_non_none_type(self) -> None:
        assert get_inner_type(Optional[int]) is int

    def test_get_inner_type_raises_for_non_optional(self) -> None:
        with pytest.raises(ValueError, match="not Optional"):
            get_inner_type(str)

    def test_to_dict_handles_nested_serializable(self) -> None:
        parent = ParentSerializable("root", NestedSerializable(7), None)
        data = parent.to_dict()
        assert data == {"name": "root", "child": {"value": 7}, "note": None}

    def test_from_dict_reconstructs_nested_serializable(self) -> None:
        payload = {"name": "root", "child": {"value": 3}, "note": "ok"}
        restored = ParentSerializable.from_dict(payload)
        assert restored.name == "root"
        assert restored.child.value == 3
        assert restored.note == "ok"

    def test_get_type_by_annotation_missing_raises(self) -> None:
        with pytest.raises(ValueError, match="not annotated"):
            ParentSerializable.get_type_by_annotation("missing")


class TestHyperparamCombinations:
    def test_build_nsga_combinations_respects_limit(self) -> None:
        combos = build_nsga_combinations(3)
        assert len(combos) == 3
        assert combos[0][0] == 2
        assert combos[2][0] == 8

    def test_build_nsga_combinations_minimum_one(self) -> None:
        combos = build_nsga_combinations(0)
        assert combos == []

    def test_format_nsga_combination(self) -> None:
        combo = (15, 0.8, 1.0, 15, 5)
        text = format_nsga_combination(combo, index=2, total=5)
        assert "combination 2/5" in text
        assert "population_size=15" in text


class TestEvaluationConfig:
    def test_approach_metadata_consistency(self) -> None:
        assert DC_RS in APPROACH_OPTIONS
        assert MSR_SB_III in PAPER_APPROACH_OPTIONS
        assert MSR_SB_II not in PAPER_APPROACH_OPTIONS
        assert APPROACH_LABELS[DC_RS].startswith("BaseRS")
        assert "RQ1" in APPROACH_COMPARED_IN[DC_RS]
        assert "rejection sampling" in APPROACH_DESCRIPTIONS[DC_RS]

    @pytest.mark.parametrize(
        "approach,expected_type",
        [
            (MSR_CDRS_PS, MSRMeasurementConfig),
            (DC_SB_III, BaseSBMeasurementConfig),
            (DC_RS, RSMeasurementConfig),
            (DC_RS_PS, RSMeasurementConfig),
        ],
    )
    def test_get_measurement_config_for_approach(self, approach, expected_type) -> None:
        config = get_measurement_config_for_approach(approach)
        assert isinstance(config, expected_type)

    def test_get_measurement_config_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown approach"):
            get_measurement_config_for_approach("invalid")

    @pytest.mark.parametrize(
        "config_group",
        [
            MSR_SB_II,
            MSR_SB_III,
            DC_SB_II,
            DC_SB_III,
            MSR_CDRS_PS,
            DC_RS,
            MSR_CDRS,
            DC_RS_PS,
        ],
    )
    def test_create_config_for_each_group(self, config_group: str) -> None:
        meas = DummyMeasurementConfig()
        config = create_config(meas, config_group, random_seed=99)
        assert isinstance(config, EvaluationData)
        assert config.config_group == config_group
        assert config.random_seed == 99
        assert config.algorithm_desc is not None

    def test_create_config_unknown_group_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown config group"):
            create_config(DummyMeasurementConfig(), "unknown", random_seed=1)

    def test_get_scenarios_msr_and_dc_paths(self) -> None:
        msr = get_scenarios(2, 0, MSR_CDRS)
        dc = get_scenarios(2, 0, DC_RS)
        assert len(msr) >= 1
        assert len(dc) == 1
        assert isinstance(
            dc[0],
            type(LogicalModelManager.get_x_vessel_y_obstacle_scenarios(2, 0)[0]),
        )

    def test_get_scenarios_unknown_group_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown config group"):
            get_scenarios(1, 0, "bad-group")


class TestGeometricProperties:
    """COLREG geometric evaluation using utils.math_utils.compute_angle."""

    def test_head_on_vessels_have_zero_dcpa_at_tcpa(
        self, head_on_vessel_assignments
    ) -> None:
        os_var = next(v for v in head_on_vessel_assignments if v.is_os)
        ts_var = next(v for v in head_on_vessel_assignments if not v.is_os)
        props = VesselToVesselProperties(os_var, ts_var, head_on_vessel_assignments)
        assert props.tcpa == pytest.approx(20.0)
        assert props.dcpa == pytest.approx(0.0, abs=1e-6)

    def test_head_on_vessels_predict_collision_points(
        self, head_on_vessel_assignments
    ) -> None:
        cache = EvaluationCache(head_on_vessel_assignments)
        os_var = next(v for v in head_on_vessel_assignments if v.is_os)
        ts_var = next(v for v in head_on_vessel_assignments if not v.is_os)
        points = cache.get_collision_points(os_var, ts_var, time_limit=20.0)
        assert len(points) >= 1
        assert all(point[0] == pytest.approx(100.0, abs=1.0) for point in points)

    def test_obstacle_vessel_collision_is_detected(
        self, obstacle_collision_assignments
    ) -> None:
        obst_var = next(v for v in obstacle_collision_assignments if not v.is_vessel)
        vessel_var = next(v for v in obstacle_collision_assignments if v.is_vessel)
        props = GeometricProperties.factory(
            obst_var, vessel_var, obstacle_collision_assignments
        )
        assert props.tcpa > 0
        assert props.dcpa < props.safety_dist
        collision_times = props.get_collision_points(time_limit=100.0)
        assert len(collision_times) >= 1

    def test_evaluation_cache_reuses_computed_properties(
        self, head_on_vessel_assignments
    ) -> None:
        cache = EvaluationCache(head_on_vessel_assignments)
        os_var = next(v for v in head_on_vessel_assignments if v.is_os)
        ts_var = next(v for v in head_on_vessel_assignments if not v.is_os)
        first = cache.get_props(os_var, ts_var)
        second = cache.get_props(os_var, ts_var)
        assert first is second


class TestScenicUtilsEncoding:
    """Scenic rejection-sampling bridge: domain state to optimization vector."""

    def test_vessel_object_to_individual_encodes_state_vector(self) -> None:
        class MockVessel:
            is_vessel = True
            position = (100.0, 50.0)
            velocity = (3.0, 4.0)
            length = 80.0

        encoded = vessel_object_to_individual(MockVessel())
        assert encoded[0:2] == [100.0, 50.0]
        assert encoded[2] == pytest.approx(calculate_heading(3.0, 4.0))
        assert encoded[3] == 80.0
        assert encoded[4] == pytest.approx(5.0)

    def test_object_to_individual_dispatches_on_actor_kind(self) -> None:
        class MockObstacle:
            is_vessel = False
            position = (10.0, -5.0)
            area_radius = 25.0

        assert object_to_individual(MockObstacle()) == [10.0, -5.0, 25.0]

    def test_generate_scenario_code_wires_maps_and_actor_ids(self) -> None:
        code = generate_scenario_code(
            base_code="param param",
            os_id=0,
            ts_ids=[1, 3],
            obst_ids=[2],
            length_map={0: 50, 1: 60},
            radius_map={2: 15},
            possible_distances_map={0: [100, 200]},
            min_distance_map={0: 10},
            vis_distance_map={0: 500},
            bearing_map={0: 0.0},
        )
        assert "class GlobalConfig" in code or "GlobalConfig" in code
        assert "create_scenario(os_id = 0" in code
        assert "ts1 = ts_infos.pop(0)" in code
        assert "ts3 = ts_infos.pop(0)" in code
        assert "obst2 = obst_infos.pop(0)" in code
        assert "length_map={0: 50, 1: 60}" in code


class TestEvaluationConfigSemantics:
    """Verify approach-specific algorithm and aggregation wiring."""

    def test_msr_nsga3_uses_larger_population_than_dc_nsga2(self) -> None:
        msr = create_config(DummyMeasurementConfig(), MSR_SB_III, random_seed=1)
        dc = create_config(DummyMeasurementConfig(), DC_SB_II, random_seed=1)
        assert msr.population_size > dc.population_size
        assert msr.algorithm_desc == PyMooNSGA3Algorithm.algorithm_desc()
        assert dc.algorithm_desc == PyMooNSGA2Algorithm.algorithm_desc()

    def test_rejection_sampling_configs_use_single_individual_and_aggregate_all(
        self,
    ) -> None:
        for group in (DC_RS, MSR_CDRS, DC_RS_PS, MSR_CDRS_PS):
            config = create_config(DummyMeasurementConfig(), group, random_seed=7)
            assert config.population_size == 1
            assert config.aggregate_strat == AggregateAll.name

    def test_search_based_msr_uses_actor_aggregate(self) -> None:
        config = create_config(DummyMeasurementConfig(), MSR_SB_II, random_seed=1)
        assert config.aggregate_strat == ActorAggregate.name

    @pytest.mark.parametrize(
        "group,expected_desc",
        [
            (DC_RS, BaseRejectionSampling.algorithm_desc()),
            (MSR_CDRS, CDRejectionSampling.algorithm_desc()),
            (DC_RS_PS, TwoStepRejectionSampling.algorithm_desc()),
            (MSR_CDRS_PS, TwoStepCDRejectionSampling.algorithm_desc()),
        ],
    )
    def test_rejection_sampling_algorithm_descriptions(
        self, group: str, expected_desc: str
    ) -> None:
        config = create_config(DummyMeasurementConfig(), group, random_seed=1)
        assert config.algorithm_desc == expected_desc

    def test_rs_measurement_config_has_unbounded_timeout(self) -> None:
        rs_config = get_measurement_config_for_approach(DC_RS)
        assert rs_config.TIMEOUT == np.inf

    def test_os_variable_bounds_reflect_configured_os_vessel_type(self) -> None:
        os_var = OSVariable(1)
        configured_type = ALL_VESSEL_TYPES[GlobalConfig.OS_VESSEL_TYPE]
        assert os_var.vessel_type == configured_type
        assert os_var.min_length == pytest.approx(
            configured_type.min_length - GlobalConfig.EPSILON
        )
        assert os_var.max_speed == pytest.approx(
            configured_type.max_speed + GlobalConfig.EPSILON
        )
