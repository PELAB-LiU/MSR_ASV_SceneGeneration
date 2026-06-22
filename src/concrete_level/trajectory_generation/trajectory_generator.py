import random
from datetime import datetime
from itertools import chain
from typing import Callable, Dict, List, Optional

import numpy as np

from concrete_level.models.multi_level_scenario import MultiLevelScenario
from concrete_level.models.rrt_models import (CircularObstacle, LineObstacle,
                                              Obstacle)
from concrete_level.models.vessel_order_graph import (VesselNode,
                                                      VesselOrderGraph)
from concrete_level.trajectory_generation.bidirectional_rrt_star_fnd import (
    DIM, BidirectionalRRTStarFND)
from concrete_level.trajectory_generation.path_interpolator import \
    PathInterpolator
from concrete_level.trajectory_generation.trajectory_builder import \
    TrajectoryBuilder
from concrete_level.trajectory_generation.trajectory_data import TrajectoryData
from global_config import GlobalConfig
from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from utils.math_utils import find_center_and_radius

SCALER = 1 / GlobalConfig.MAX_COORD / 1.5 * DIM

DIRECTION_THRESHOLD = 1  # meter
GOAL_SAMPLE_RATE = 5.0  # %


class TrajectoryGenerator:
    def __init__(
        self,
        eval_data: EvaluationData,
        scenario: MultiLevelScenario,
        *,
        verbose: bool = False,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        self.verbose = verbose
        self.log_callback = log_callback
        seed = 1234
        random.seed(seed)
        np.random.seed(seed)
        self.scenario = scenario
        interpolator = PathInterpolator(self.scenario)
        ordered_vessels = VesselOrderGraph(self.scenario).sort()
        self.default_trajectory_builder = TrajectoryBuilder(
            interpolator.trajectory_builder
        )
        self.default_trajectory_builder.add_scene(self.scenario.concrete_scene)
        self.default_trajectory_builder.extend(GlobalConfig.TWO_HOURS_IN_SEC)

        start_time = datetime.now()
        iter_numbers: Dict[int, int] = {}
        eval_times: Dict[int, float] = {}
        expand_distances: Dict[int, float] = {}

        for v_node in ordered_vessels:
            o_start_time = datetime.now()

            path, iter_number, expand_distance = self.run_trajectory_generation(
                v_node, interpolator
            )
            interpolator.add_path(v_node.vessel, path)

            o_eval_time = (datetime.now() - o_start_time).total_seconds()
            eval_times[v_node.vessel.id] = o_eval_time
            iter_numbers[v_node.vessel.id] = iter_number
            expand_distances[v_node.vessel.id] = expand_distance

        overall_eval_time = (datetime.now() - start_time).total_seconds()
        timestamp = datetime.now().isoformat()

        self.trajectories = interpolator.trajectories
        traj_data = TrajectoryData(
            measurement_name="test",
            iter_numbers=iter_numbers,
            algorithm_desc="RRTStar_algo",
            config_name=eval_data.scenario_name,
            scene_path=eval_data.path,
            random_seed=seed,
            expand_distances=expand_distances,
            goal_sample_rate=GOAL_SAMPLE_RATE,
            timestamp=timestamp,
            trajectories=self.trajectories,
            overall_eval_time=overall_eval_time,
            rrt_evaluation_times=eval_times,
        )

        traj_data.save_as_measurement()

    def _log(self, message: str) -> None:
        if self.log_callback is not None:
            self.log_callback(message)
        elif self.verbose:
            print(message)

    def run_trajectory_generation(
        self, v_node: VesselNode, interpolator: PathInterpolator
    ):
        vessel = v_node.vessel
        vessel_state = self.scenario.concrete_scene[vessel]
        self._log(f"Calculation {vessel}:")
        expand_distance = vessel_state.speed * 20  # half minute precision

        if v_node.out_degree == 0:
            return [], 0, expand_distance

        # collision_points : List[np.ndarray] = []

        # for v1, v2 in v_node.relations:
        #     print(f'Collision points for static colreg ({v1}, {v2})')
        #     var1 = scenario.to_variable(v1)
        #     var2 = scenario.to_variable(v2)
        #     collision_points += scenario.evaluation_cache.get_collision_points(var1, var2)

        trajectory_collision_points = (
            self.default_trajectory_builder.build().collision_points(vessel)
        )
        collision_points = list(
            chain.from_iterable(list(trajectory_collision_points.values()))
        )

        # furthest_collision_point = max(collision_points, key=lambda p: np.linalg.norm(p - vessel_state.p))

        if len(collision_points) != 0:
            collision_center, collision_center_radius = find_center_and_radius(
                collision_points
            )
            collision_center_radius = collision_center_radius + vessel.radius
        else:
            collision_center = (
                vessel_state.p + vessel_state.v * interpolator.path_length / 2
            )
            collision_center_radius = 0

        start_coll_center_dist = np.linalg.norm(vessel_state.p - collision_center)
        # start_furthest_point_dist = np.linalg.norm(vessel_state.p - furthest_collision_point)
        start_goal_dist = start_coll_center_dist * 2
        goal_pos = vessel_state.v_norm * start_goal_dist + vessel_state.p
        goal_state = vessel_state.modify_copy(x=goal_pos[0], y=goal_pos[1])
        collision_center_radius = min(
            collision_center_radius, (start_goal_dist / 2) * 0.75
        )

        # poly_p1 = vessel_state.p + vessel_state.v_norm * start_coll_center_dist / 3
        # poly_p2 = vessel_state.p + vessel_state.v_norm * start_furthest_point_dist
        # poly_p3 = poly_p2 + vessel_state.v_norm_perp * collision_center_radius
        # poly_p4 = poly_p1 + vessel_state.v_norm_perp * collision_center_radius

        obstacle_list: List[Obstacle] = []
        # obstacle_list += [PolygonalObstacle(p1=poly_p1, p2=poly_p2, p3=poly_p3, p4=poly_p4)]
        # obstacle_list += [CircularObstacle(p, max(v.radius, vessel.radius)) for v, points in trajectory_collision_points.items() for p in points]
        obstacle_list.append(
            CircularObstacle(collision_center, collision_center_radius)
        )

        # Define the bounding lines
        min_go_around_line = LineObstacle(
            vessel_state.x,
            vessel_state.y,
            vessel_state.v_norm,
            False,
            collision_center_radius,
        )
        go_around_split_line = LineObstacle(
            collision_center[0], collision_center[1], vessel_state.v_norm_perp, False, 0
        )

        bounding_lines = [
            LineObstacle(
                vessel_state.x,
                vessel_state.y,
                vessel_state.v_norm,
                True,
                DIRECTION_THRESHOLD,
            ),  # Left bounding line
            LineObstacle(
                goal_state.x,
                goal_state.y,
                vessel_state.v_norm,
                False,
                collision_center_radius + GlobalConfig.TWO_N_MILE,
            ),  # Right bounding line
            LineObstacle(
                vessel_state.x,
                vessel_state.y,
                vessel_state.v_norm,
                False,
                collision_center_radius + GlobalConfig.TWO_N_MILE,
            ),  # Right bounding line
            LineObstacle(
                vessel_state.x,
                vessel_state.y,
                vessel_state.v_norm_perp,
                False,
                DIRECTION_THRESHOLD,
            ),  # Behind bounding line
            LineObstacle(
                goal_state.x,
                goal_state.y,
                vessel_state.v_norm_perp,
                True,
                DIRECTION_THRESHOLD,
            ),  # Front bounding line
        ]

        # Add circular obstacle and bounding lines to obstacle list
        # obstacle_list += [CircularObstacle(collision_center[0], collision_center[1], collision_radius)] + bounding_lines
        obstacle_list += bounding_lines

        # Calculate X and Y distances
        shifted_points_x = [line.shifted_point[0] for line in bounding_lines]
        shifted_points_y = [line.shifted_point[1] for line in bounding_lines]

        X_DIST = (min(shifted_points_x), max(shifted_points_x))
        Y_DIST = (min(shifted_points_y), max(shifted_points_y))
        # ====Search Path with RRT====
        self._log(f"start RRT path planning for {vessel}")
        # Set Initial parameters
        rrt = BidirectionalRRTStarFND(
            v_node=v_node,
            start_state=vessel_state,
            goal_state=goal_state,
            min_go_around_line=min_go_around_line,
            go_around_split_line=go_around_split_line,
            sample_area=[X_DIST, Y_DIST],
            obstacle_list=obstacle_list,
            expand_dist=expand_distance,
            goal_sample_rate=GOAL_SAMPLE_RATE,
            collision_points=collision_points,
            interpolator=interpolator,
            scaler=SCALER * GlobalConfig.MAX_COORD / start_goal_dist / 1.5,
            verbose=self.verbose,
            log_callback=self.log_callback,
        )

        # Add the original position to start the path
        path = rrt.plan_trajectory()

        return path, rrt.current_i, expand_distance
