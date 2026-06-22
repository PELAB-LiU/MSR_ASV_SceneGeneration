from typing import List, Set, Tuple

import numpy as np

from concrete_level.models.actor_state import ActorState
from concrete_level.models.concrete_actors import ConcreteVessel
from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.models.multi_level_scenario import MultiLevelScenario
from concrete_level.models.rrt_models import RRTNode
from concrete_level.models.trajectories import Trajectories
from concrete_level.trajectory_generation.trajectory_builder import \
    TrajectoryBuilder


class PathInterpolator:
    def __init__(self, scenario: MultiLevelScenario) -> None:
        self.trajectory_builder = TrajectoryBuilder()
        self.vessels: Set[ConcreteVessel] = set()
        self.scenario: MultiLevelScenario = scenario
        self.path_length = 45 * 60

    def add_path(self, vessel: ConcreteVessel, path: List[RRTNode]):
        vessel_state = self.scenario.concrete_scene[vessel]
        if vessel in self.trajectory_builder:
            raise Exception("Cannot add two path for one vessel")
        if len(path) == 0:
            self.trajectory_builder[vessel] = [vessel_state]
        else:
            self.trajectory_builder[vessel] = self.interpolate_path(vessel_state, path)
        self.vessels.add(vessel)
        self.trajectory_builder.extend(self.path_length)

    def get_scene_by_second(self, second: int) -> ConcreteScene:
        # If there are no trajectories yet (e.g., planning the first vessel),
        # there is nothing to collide with, so return an empty scene.
        if len(self.trajectory_builder) == 0:
            from concrete_level.trajectory_generation.scene_builder import \
                SceneBuilder

            return SceneBuilder().build()
        if second >= self.path_length:
            self.path_length = self.path_length + (second - self.path_length) + 60
            self.trajectory_builder.extend(self.path_length)
        return self.trajectory_builder.build().get_scene(second)

    def interpolate_path(
        self, vessel_state: ActorState, path: List[RRTNode]
    ) -> List[ActorState]:
        """
        Interpolates the given path to have positions at one-second intervals
        and calculates the heading based on the direction of movement.

        :param positions: List of (x, y) tuples representing the positions.
        :param speed: Speed of the vessel (units per second).
        :return: List of interpolated (position, heading) tuples.
        """
        interpolated_positions = []
        interpolated_headings = []
        interpolated_speeds = []

        for i in range(len(path) - 1):
            # Start and end points
            node_start = path[i]
            node_end = path[i + 1]

            # Calculate the distance and heading between the points
            delta_pos = node_end.p - node_start.p
            heading = np.arctan2(delta_pos[1], delta_pos[0])
            time_cost = node_end.time_cost - node_start.time_cost

            # Interpolate positions for each second
            for s in range(time_cost):
                fraction = s / time_cost
                new_p = node_start.p + delta_pos * fraction
                interpolated_positions.append(new_p)
                interpolated_headings.append(heading)
                interpolated_speeds.append(vessel_state.speed)
            if node_end.s_fraction > 0.0001:  # Bigger than some small value
                speed = vessel_state.speed * node_end.s_fraction
                interpolated_speeds[-1] = speed

        # Append the final position and heading
        interpolated_positions.append(path[-1].p)
        interpolated_headings.append(vessel_state.heading)
        interpolated_speeds.append(vessel_state.speed)

        return [
            ActorState(
                interpolated_positions[i][0],
                interpolated_positions[i][1],
                interpolated_speeds[i],
                heading,
            )
            for i, heading in enumerate(interpolated_headings)
        ]

    @property
    def trajectories(self) -> Trajectories:
        return self.trajectory_builder.build()

    @staticmethod
    def interpolate_headings(
        trajectory: List[Tuple[float, float, float, float, float]],
    ) -> List[Tuple[float, float, float, float, float]]:
        headings = [t[2] for t in trajectory]

        def interpolate_chunk(start, end, num_steps):
            """Linearly interpolate between start and end in num_steps steps."""
            step_values = []
            for i in range(num_steps):
                ratio = i / (num_steps - 1) if num_steps > 1 else 0
                interpolated_value = start * (1 - ratio) + end * ratio
                step_values.append(interpolated_value)
            return step_values

        # Find blocks of same heading
        blocks = []
        current_block = [0]
        for i in range(1, len(headings)):
            if headings[i] == headings[current_block[0]]:
                current_block.append(i)
            else:
                blocks.append(current_block)
                current_block = [i]
        blocks.append(current_block)

        # Interpolate between the end of one block to the start of the next
        for i in range(len(blocks) - 1):
            start_block = blocks[i]
            end_block = blocks[i + 1]

            start_value = headings[start_block[-1]]
            end_value = headings[end_block[0]]

            # Interpolate from the last index of the current block to the first index of the next block
            num_steps = len(start_block) + len(end_block)
            interpolated_values = interpolate_chunk(start_value, end_value, num_steps)

            # Replace values in the original list
            for j in range(len(start_block)):
                headings[start_block[j]] = interpolated_values[j]
            for j in range(len(end_block)):
                headings[end_block[j]] = interpolated_values[len(start_block) + j]

        return [
            (
                trajectory[i][0],
                trajectory[i][1],
                headings[i],
                trajectory[i][3],
                trajectory[i][4],
            )
            for i in range(len(headings))
        ]
