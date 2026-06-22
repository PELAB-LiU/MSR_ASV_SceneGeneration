from typing import Dict, List, Tuple

import numpy as np

from concrete_level.models.concrete_actors import ConcreteVessel
from concrete_level.models.multi_level_scenario import MultiLevelScenario
from concrete_level.models.trajectory_manager import TrajectoryManager
from concrete_level.trajectory_generation.scene_builder import SceneBuilder
from global_config import GlobalConfig
from logical_level.models.actor_variable import VesselVariable


class RiskVector:
    def __init__(self, scenario: MultiLevelScenario) -> None:
        os_ts = {
            (a1, a2): ProximityVector(scenario, a1, a2)
            for a1, a2 in scenario.os_ts_pairs
        }
        ts_ts = {
            (a1, a2): ProximityVector(scenario, a1, a2)
            for a1, a2 in scenario.ts_ts_pairs
        }
        self.proximity_vectors: Dict[
            Tuple[ConcreteVessel, ConcreteVessel], ProximityVector
        ] = {**os_ts, **ts_ts}
        self.danger_sectors: Dict[ConcreteVessel, float] = {
            vessel: NavigationRiskIndex(scenario, vessel).find_danger_sector()
            for vessel in [scenario.concrete_scene.os]
        }

        self.max_proximity_index = min(
            self.proximity_vectors.values(), key=lambda obj: obj.tcpa
        )
        # self.safe_navigation_area_index = self.nav_risk_vector.find_safe_navigation_area_index()
        self.danger_sector = self.danger_sectors[scenario.concrete_scene.os]

        self.min_dcpa = self.max_proximity_index.dcpa
        self.min_tcpa = self.max_proximity_index.tcpa
        self.max_proximity_index = self.max_proximity_index.proximity_index

        # self.distance = (pow(np.e, np.linalg.norm(self.risk_vector) / np.sqrt(3)) - 1) / (np.e - 1)


class ProximityVector:
    def __init__(
        self,
        scenario: MultiLevelScenario,
        actor1: ConcreteVessel,
        actor2: ConcreteVessel,
    ) -> None:
        self.props = scenario.get_geo_props(actor1, actor2)
        self.dist = self.props.o_distance
        self.tcpa = self.props.tcpa
        self.dcpa = self.props.dcpa

        dr = 1 * GlobalConfig.N_MILE_TO_M_CONVERSION
        ts = 10 * 60

        if self.tcpa < 0 or self.tcpa > ts:
            self.dcpa_norm = 0
            self.tcpa_norm = 0
        else:
            if self.dcpa < self.props.safety_dist:
                self.dcpa_norm = 1
            else:
                # self.dcpa_norm = (pow(np.e, (dr - self.dcpa) / (dr - relation.safety_dist)) - 1) / (np.e - 1)
                self.dcpa_norm = (
                    pow(np.e, (dr - self.dcpa) / (dr - self.props.safety_dist)) - 1
                ) / (np.e - 1)
            # self.tcpa_norm = (pow(np.e, (ts - self.tcpa) / ts) - 1) / (np.e - 1)
            self.tcpa_norm = (pow(np.e, (ts - self.tcpa) / ts) - 1) / (np.e - 1)
        if self.dcpa_norm * self.tcpa_norm > 0:
            self.proximity_index = np.sqrt(self.dcpa_norm * self.tcpa_norm)
        else:
            self.proximity_index = 0


class NavigationRiskIndex:
    def __init__(self, scenario: MultiLevelScenario, vessel: ConcreteVessel) -> None:
        self.scenario = scenario
        self.scene = scenario.concrete_scene
        self.initial_state = self.scene[vessel]
        self.vessel = vessel
        self.variable: VesselVariable = scenario.to_variable(self.vessel)

    def find_danger_sector(self) -> float:
        for i in range(91):
            new_scenario = self.scenario.modify_state_get_new_scene(
                self.vessel, heading=self.initial_state.heading + np.radians(i)
            )
            if not new_scenario.may_collide_anyone(self.vessel):
                break
        for j in range(91):
            new_scenario = self.scenario.modify_state_get_new_scene(
                self.vessel, heading=self.initial_state.heading - np.radians(i)
            )
            if not new_scenario.may_collide_anyone(self.vessel):
                break
        return pow((i + j) / 180, 0.33)

    def find_safe_navigation_area_index(self) -> float:
        collides = 0
        no_collides = 0
        partitions = 50

        speeds = [
            i * (self.variable.max_speed / partitions) for i in range(1, partitions + 1)
        ]
        for speed in speeds:
            for i in range(0, 180):
                for direction in [-1, 1]:  # -1 for counterclockwise, 1 for clockwise
                    new_state = self.initial_state.modify_copy(
                        heading=self.initial_state.heading + direction * np.radians(i),
                        speed=speed,
                    )
                    new_scene = SceneBuilder(self.scene).set_state(
                        self.vessel, new_state
                    )
                    scenario = MultiLevelScenario(
                        new_scene,
                        self.scenario.logical_scenario,
                        self.scenario.functional_scenario,
                    )
                    if scenario.may_collide_anyone(self.vessel):
                        collides += 1
                    else:
                        no_collides += 1
        return (pow(np.e, collides / (collides + no_collides)) - 1) / (np.e - 1)


class TrajectoryRiskEvaluator:
    def __init__(self, trajectory_manager: TrajectoryManager) -> None:
        self.trajectory_manager = trajectory_manager
        self.risk_vectors: List[RiskVector] = []
        last_vector = RiskVector(trajectory_manager.scenario)
        for t in range(self.trajectory_manager.timespan):
            if t % 15 == 0:
                scenario = self.trajectory_manager.get_scenario(t)
                last_vector = RiskVector(scenario)
            self.risk_vectors.append(last_vector)
