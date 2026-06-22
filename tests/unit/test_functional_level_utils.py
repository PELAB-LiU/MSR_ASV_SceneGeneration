"""Unit tests for utils modules used by the functional level."""

from __future__ import annotations

from pathlib import Path

import pytest

from functional_level.models.functional_model_manager import \
    FunctionalModelManager
from functional_level.models.functional_scenario_builder import \
    FunctionalScenarioBuilder
from global_config import GlobalConfig
from logical_level.mapping.logical_scenario_builder import \
    LogicalScenarioBuilder
from utils.file_system_utils import (FUNCTIONAL_MODELS_FOLDER,
                                     get_all_file_paths)
from utils.scenario import Scenario
from utils.static_obstacle_types import (ALL_STATIC_OBSTACLE_TYPES,
                                         DEFAULT_OBSTACLE_TYPE, LargeObstacle,
                                         MediumObstacle, OtherObstacleType,
                                         SmallObstacle,
                                         UnspecifiedObstacleType)
from utils.vessel_types import (ALL_VESSEL_TYPES, DEFAULT_VESSEL_TYPE,
                                CargoShip, ContainerShip, FishingShip, MiniUSV,
                                OSPassengerShip, OtherVesselType,
                                PassengerShip, Tanker, UnspecifiedVesselType)


class StubScenario(Scenario):
    """Minimal Scenario implementation for abstract-base tests."""

    def __init__(self, vessel_number: int, obstacle_number: int) -> None:
        self._vessel_number = vessel_number
        self._obstacle_number = obstacle_number

    @property
    def vessel_number(self) -> int:
        return self._vessel_number

    @property
    def obstacle_number(self) -> int:
        return self._obstacle_number


class TestScenario:
    def test_actor_number_sums_vessels_and_obstacles(self) -> None:
        scenario = StubScenario(vessel_number=2, obstacle_number=3)
        assert scenario.actor_number == 5

    def test_actor_number_by_type_tuple(self) -> None:
        scenario = StubScenario(vessel_number=4, obstacle_number=1)
        assert scenario.actor_number_by_type == (4, 1)

    def test_name_format(self) -> None:
        scenario = StubScenario(vessel_number=2, obstacle_number=0)
        assert scenario.name == "2vessel_0obstacle"

    def test_functional_model_manager_scenario_counts(self) -> None:
        scenarios = FunctionalModelManager.get_x_vessel_y_obstacle_scenarios(2, 0)
        assert len(scenarios) >= 1
        scenario = scenarios[0]
        assert scenario.vessel_number == 2
        assert scenario.obstacle_number == 0
        assert scenario.actor_number == 2


class TestVesselTypes:
    @pytest.mark.parametrize(
        "vessel_type,length,speed,beam,expected",
        [
            (CargoShip(), 100.0, 5.0, 20.0, True),
            (CargoShip(), 10.0, 5.0, 20.0, False),
            (Tanker(), 80.0, 8.0, None, True),
            (OSPassengerShip(), 30.0, 15.0, 10.0, True),
            (MiniUSV(), 10.0, 1.0, 10.0, True),
        ],
    )
    def test_do_match(self, vessel_type, length, speed, beam, expected) -> None:
        assert vessel_type.do_match(length, speed, beam) is expected

    def test_unspecified_vessel_type_flag(self) -> None:
        assert UnspecifiedVesselType().is_unspecified is True
        assert CargoShip().is_unspecified is False

    def test_repr_and_str_use_name(self) -> None:
        vessel = FishingShip()
        assert repr(vessel) == "FishingShip"
        assert str(vessel) == "FishingShip"

    def test_all_vessel_types_registry(self) -> None:
        assert "CargoShip" in ALL_VESSEL_TYPES
        assert ALL_VESSEL_TYPES["CargoShip"] == CargoShip()
        assert DEFAULT_VESSEL_TYPE == UnspecifiedVesselType()
        assert OtherVesselType().name == "OtherType"
        assert ContainerShip().name == "ContainerShip"
        assert PassengerShip().name == "PassengerShip"


class TestStaticObstacleTypes:
    @pytest.mark.parametrize(
        "obstacle_type,radius,expected",
        [
            (SmallObstacle(), 25.0, True),
            (SmallObstacle(), 60.0, False),
            (MediumObstacle(), 100.0, True),
            (LargeObstacle(), 250.0, True),
            (OtherObstacleType(), 15.0, True),
        ],
    )
    def test_do_match(self, obstacle_type, radius, expected) -> None:
        assert obstacle_type.do_match(radius) is expected

    def test_unspecified_obstacle_type_flag(self) -> None:
        assert UnspecifiedObstacleType().is_unspecified is True
        assert SmallObstacle().is_unspecified is False

    def test_all_static_obstacle_types_registry(self) -> None:
        assert set(ALL_STATIC_OBSTACLE_TYPES) >= {
            "SmallObstacle",
            "MediumObstacle",
            "LargeObstacle",
            "UnspecifiedType",
        }
        assert DEFAULT_OBSTACLE_TYPE == UnspecifiedObstacleType()


class TestFunctionalScenarioBuilderColregs:
    """COLREG relation wiring through functional scenarios and utils type maps."""

    def _build_head_on_scenario(self):
        builder = FunctionalScenarioBuilder()
        os = builder.add_new_os("os")
        ts = builder.add_new_ts("ts")
        cargo_type = builder.find_vessel_type_by_name("CargoShip")
        builder.add_vessel_type(os, cargo_type)
        builder.add_vessel_type(ts, cargo_type)
        builder.add_head_on(os, ts)
        return builder.build(), os, ts

    def test_head_on_relation_is_recognized(self) -> None:
        scenario, os, ts = self._build_head_on_scenario()
        assert scenario.head_on(os, ts) is True
        assert scenario.crossing_from_port(os, ts) is False
        assert scenario.overtaking_to_port(os, ts) is False

    def test_crossing_from_port_differs_from_head_on(self) -> None:
        builder = FunctionalScenarioBuilder()
        os = builder.add_new_os("os")
        ts = builder.add_new_ts("ts")
        cargo = builder.find_vessel_type_by_name("CargoShip")
        builder.add_vessel_type(os, cargo)
        builder.add_vessel_type(ts, cargo)
        builder.add_crossing_from_port(os, ts)
        scenario = builder.build()
        assert scenario.crossing_from_port(os, ts) is True
        assert scenario.head_on(os, ts) is False

    def test_vessel_types_from_utils_registry_on_functional_level(self) -> None:
        scenario, os, ts = self._build_head_on_scenario()
        assert scenario.find_vessel_type_name(os) == GlobalConfig.OS_VESSEL_TYPE
        assert scenario.find_vessel_type_name(ts) == "CargoShip"
        assert scenario.find_vessel_type_name(ts) in ALL_VESSEL_TYPES

    def test_functional_scenario_maps_to_logical_with_same_vessel_types(self) -> None:
        scenario, os, ts = self._build_head_on_scenario()
        logical = LogicalScenarioBuilder.build_from_functional(scenario)
        assert (
            logical.os_variable.vessel_type
            == ALL_VESSEL_TYPES[GlobalConfig.OS_VESSEL_TYPE]
        )
        assert logical.ts_variables[0].vessel_type == CargoShip()
        assert logical.os_variable.id == os.id
        assert logical.ts_variables[0].id == ts.id
        assert logical.vessel_number == 2
        assert logical.obstacle_number == 0

    def test_fsm_shape_hash_stable_for_identical_scenarios(self) -> None:
        scenario_a, _, _ = self._build_head_on_scenario()
        scenario_b, _, _ = self._build_head_on_scenario()
        assert scenario_a.fsm_shape_hash() == scenario_b.fsm_shape_hash()

    def test_fsm_shape_hash_differs_for_different_relations(self) -> None:
        head_on, os_h, ts_h = self._build_head_on_scenario()
        builder = FunctionalScenarioBuilder()
        os = builder.add_new_os("os")
        ts = builder.add_new_ts("ts")
        cargo = builder.find_vessel_type_by_name("CargoShip")
        builder.add_vessel_type(os, cargo)
        builder.add_vessel_type(ts, cargo)
        builder.add_overtaking_to_port(os, ts)
        overtaking = builder.build()
        assert head_on.fsm_shape_hash() != overtaking.fsm_shape_hash()
        assert head_on.head_on(os_h, ts_h)
        assert overtaking.overtaking_to_port(os, ts)


class TestVesselTypeEpsilonBoundaries:
    def test_cargo_ship_accepts_length_at_lower_bound(self) -> None:
        cargo = CargoShip()
        assert cargo.do_match(cargo.min_length, cargo.min_speed) is True

    def test_cargo_ship_rejects_speed_above_maritime_max(self) -> None:
        cargo = CargoShip()
        too_fast = cargo.max_speed + 1.0
        assert cargo.do_match(100.0, too_fast) is False

    def test_os_passenger_ship_exact_dimensions_match(self) -> None:
        os_ship = OSPassengerShip()
        assert os_ship.do_match(30.0, 20.0, 10.0) is True
        assert os_ship.do_match(31.0, 20.0, 10.0) is False


class TestFunctionalFileSystemUtils:
    def test_functional_models_folder_exists(self) -> None:
        assert Path(FUNCTIONAL_MODELS_FOLDER).is_dir()

    def test_get_all_file_paths_groups_by_extension(self, sample_tree: Path) -> None:
        paths = get_all_file_paths(str(sample_tree), [".json", ".txt"])
        assert len(paths[".json"]) == 2
        assert len(paths[".txt"]) == 1
        assert all(path.endswith(".json") for path in paths[".json"])

    def test_get_all_file_paths_rejects_invalid_directory(self) -> None:
        with pytest.raises(ValueError, match="not a directory"):
            get_all_file_paths("/path/that/does/not/exist", [".json"])
