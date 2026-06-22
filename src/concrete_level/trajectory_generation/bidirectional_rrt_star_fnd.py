import os
import random
from typing import Callable, List, Optional, Tuple

import numpy as np

from concrete_level.models.actor_state import ActorState
from concrete_level.models.rrt_models import (LineObstacle, Obstacle,
                                              RandomPoint, RRTNode)
from concrete_level.models.vessel_order_graph import VesselNode
from concrete_level.trajectory_generation.path_interpolator import \
    PathInterpolator

DIM = 1000


def is_rrt_animation_enabled() -> bool:
    return os.environ.get("ENABLE_RRT_ANIMATION", "false").lower() in {
        "1",
        "true",
        "yes",
    }


show_animation = is_rrt_animation_enabled()


class BidirectionalRRTStarFND:
    """
    Class for RRT Planning
    """

    def __init__(
        self,
        v_node: VesselNode,
        start_state: ActorState,
        goal_state: ActorState,
        min_go_around_line: LineObstacle,
        go_around_split_line: LineObstacle,
        obstacle_list: List[Obstacle],
        sample_area: List[Tuple[float, float]],
        collision_points: List[np.ndarray],
        interpolator: PathInterpolator,
        expand_dist=10.0,
        goal_sample_rate=15,
        scaler=1.0,
        max_nodes=500,
        verbose: bool = False,
        log_callback: Optional[Callable[[str], None]] = None,
    ):
        self.vessel = v_node.vessel
        self.collision_points = collision_points
        self.interpolator = interpolator
        self.start = RRTNode(start_state.p)
        self.goal = RRTNode(goal_state.p)
        self.min_go_around_line = min_go_around_line
        self.go_around_split_line = go_around_split_line
        self.delta_pos_start_end = self.goal.p - self.start.p
        self.start_end_distance = np.linalg.norm(self.delta_pos_start_end)
        self.sample_area = sample_area
        self.expand_dist = expand_dist
        self.goal_sample_rate = goal_sample_rate
        self.obstacle_list: List[Obstacle] = obstacle_list
        self.current_i = 0
        self.stop = False
        self.scaler = scaler
        self.max_nodes = max_nodes
        self.start_state = start_state
        self.verbose = verbose
        self.log_callback = log_callback

        if show_animation:
            from visualization.trajectory_visualizer import \
                TrajectoryVisualizer

            self.trajectory_visualizer = TrajectoryVisualizer(DIM, scaler, sample_area)
            self.trajectory_visualizer.set_caption(v_node, interpolator)

    def _log(self, message: str) -> None:
        if self.log_callback is not None:
            self.log_callback(message)
        else:
            print(message)

    def _log_verbose_progress(self) -> None:
        if not self.verbose or not self.node_list:
            return
        closest_key = min(
            self.node_list.keys(),
            key=lambda key: np.linalg.norm(self.goal.p - self.node_list[key].p),
        )
        closest_node = self.node_list[closest_key]
        closest_dist = float(np.linalg.norm(self.goal.p - closest_node.p))
        self._log(
            f"iteration {self.current_i}: closest node {closest_key} "
            f"at ({closest_node.p[0]:.1f}, {closest_node.p[1]:.1f}), "
            f"distance to goal {closest_dist:.2f} m"
        )

    def do_plan(self) -> Optional[List[RRTNode]]:
        while not self.stop:
            if self.verbose:
                self._log_verbose_progress()
            elif self.current_i % 100 == 0:
                print(
                    f"iteration: {self.current_i}, number of nodes: {len(self.node_list)}"
                )

            rnd = self.get_random_point()
            nearest_index = self.get_nearest_list_index(
                rnd
            )  # get nearest node index to random point
            new_node = self.steer(
                rnd, nearest_index
            )  # generate new node from that nearest node in direction of random point

            if self.check_no_collision(
                new_node, self.obstacle_list
            ):  # if it does not collide
                nearest_indexes = self.find_near_nodes(
                    new_node, 5
                )  # find nearest nodes to newNode
                found = self.choose_parent(
                    new_node, nearest_indexes
                )  # from that nearest nodes find the best parent to newNode
                if not found:
                    continue
                self.node_list[self.current_i + 100] = (
                    new_node  # add newNode to nodeList
                )
                self.rewire(
                    self.current_i + 100, new_node, nearest_indexes
                )  # make newNode a parent of another node if necessary
                self.node_list[new_node.parent].children.add(self.current_i + 100)

                if len(self.node_list) > self.max_nodes:
                    self.prune_branches()

            self.update_anim()

            self.current_i += 1

        # generate course
        lastIndex = self.get_best_last_index()
        if lastIndex is None:
            return None
        path = self.gen_final_course(lastIndex)
        return path

    def update_anim(self):
        if show_animation:
            if self.current_i % 25 == 0:
                self.trajectory_visualizer.update(
                    self.obstacle_list,
                    self.collision_points,
                    self.min_go_around_line,
                    self.go_around_split_line,
                    self.start,
                    self.goal,
                    self.node_list,
                    self.get_best_last_index(),
                    self.gen_final_course,
                )
            if self.trajectory_visualizer.handle_user_input(
                self.goal, self.obstacle_list, self.path_validation
            ):
                self.stop = True
        else:
            self.path_validation()
            if self.get_best_last_index() is not None:
                self.stop = True

    def prune_branches(self):
        leaves = [
            key
            for key, node in self.node_list.items()
            if len(node.children) == 0 and len(self.node_list[node.parent].children) > 1
        ]
        if len(leaves) > 0:
            ind = leaves[random.randint(0, len(leaves) - 1)]
            self.node_list[self.node_list[ind].parent].children.discard(ind)
            self.node_list.pop(ind)
        else:
            leaves = [
                key for key, node in self.node_list.items() if len(node.children) == 0
            ]
            for i in range(300):
                ind = leaves[random.randint(0, len(leaves) - 1)]
                self.node_list[self.node_list[ind].parent].children.discard(ind)
                self.node_list.pop(ind)

    def plan_trajectory(self) -> List[RRTNode]:
        """
        plan_trajectory
        animation: flag for animation on or off
        """
        self.node_list = {0: self.start}
        path = None
        path = self.do_plan()
        if path is None:
            raise Exception("No path is found")
        path.reverse()
        return path

    def path_validation(self):
        lastIndex = self.get_best_last_index()
        if lastIndex is not None:
            while self.node_list[lastIndex].parent is not None:
                nodeInd = lastIndex
                lastIndex = self.node_list[lastIndex].parent
                if not self.check_no_collision_extend(
                    self.node_list[lastIndex], self.node_list[nodeInd]
                )[0]:
                    self.node_list[lastIndex].children.discard(nodeInd)
                    self.remove_branch(nodeInd)

    def remove_branch(self, nodeInd):
        for ix in self.node_list[nodeInd].children:
            self.remove_branch(ix)
        self.node_list.pop(nodeInd)

    def choose_parent(self, new_node: RRTNode, nearest_indexes):
        if len(nearest_indexes) == 0:
            return False

        min_cost = np.inf
        min_cost_index = None
        for i in nearest_indexes:
            no_coll, dist = self.check_no_collision_extend(self.node_list[i], new_node)
            if no_coll:
                cost = self.node_list[i].distance_cost + dist
                if cost < min_cost:
                    min_cost = cost
                    min_cost_index = i

        if min_cost_index == None:
            print("min_cost is inf")
            return False

        new_node.distance_cost = min_cost
        new_node.parent = min_cost_index
        return True

    def steer(self, rnd: RandomPoint, nearest_index: int):
        # expand tree
        nearest_node = self.node_list[nearest_index]
        delta_pos = rnd.p - nearest_node.p
        theta = np.arctan2(delta_pos[1], delta_pos[0])
        new_point = (
            nearest_node.p + np.array([np.cos(theta), np.sin(theta)]) * self.expand_dist
        )
        new_node = RRTNode(new_point)

        # # Apply the condition for adjusting theta
        # abs_theta = abs(theta)  # Work with absolute value of theta for comparison

        # if abs_theta < np.radians(30):
        #     theta = 0  # Set to 0 if below 30 degrees
        # elif abs_theta > np.radians(60):
        #     theta = np.sign(theta) * np.radians(60)  # Cap at 60 degrees with the same sign

        s_dist, s_fraction = RRTNode.calc_cost(self.start_state, self.expand_dist)
        new_node.set_cost(
            nearest_node.distance_cost + self.expand_dist,
            nearest_node.time_cost + s_dist,
            s_fraction,
        )
        new_node.parent = nearest_index
        return new_node

    def get_random_point(self) -> RandomPoint:
        if random.randint(0, 100) > self.goal_sample_rate:
            return RandomPoint.get(self.sample_area)
        return RandomPoint(self.goal.p.copy(), True)

    def get_best_last_index(self):
        dist_to_goal_list = [
            (key, np.linalg.norm(self.goal.p - node.p))
            for key, node in self.node_list.items()
        ]
        near_goal_indexes = [
            key for key, distance in dist_to_goal_list if distance <= self.expand_dist
        ]

        if len(near_goal_indexes) == 0:
            return None

        min_cost_index = min(
            near_goal_indexes, key=lambda i: self.node_list[i].distance_cost
        )
        return min_cost_index

    def gen_final_course(self, goal_index: int) -> List[RRTNode]:
        path = [self.goal]
        while self.node_list[goal_index].parent is not None:
            node = self.node_list[goal_index]
            path.append(node)
            goal_index = node.parent
        path.append(self.start)
        return path

    def find_near_nodes(self, newNode: RRTNode, value):
        r_squared = (
            self.expand_dist * value
        ) ** 2  # Compute the squared distance threshold once

        new_p = newNode.p
        node_positions = np.array(
            [node.p for node in self.node_list.values()]
        )  # Extract positions
        node_keys = np.array(list(self.node_list.keys()))  # Extract node keys

        # Compute squared distances between nodes and newNode
        dist_squared = np.sum((node_positions - new_p) ** 2, axis=1)

        # Find nodes with distances less than or equal to r_squared
        nearest_indexes = node_keys[dist_squared <= r_squared]

        return nearest_indexes

    def rewire(self, new_node_index: int, new_node: RRTNode, near_indexes: List[int]):
        for i in near_indexes:
            near_node = self.node_list[i]

            d = np.linalg.norm(new_node.p - near_node.p)
            new_cost = new_node.distance_cost + d

            if near_node.distance_cost > new_cost:
                no_coll, dist = self.check_no_collision_extend(new_node, near_node)
                if no_coll:
                    self.node_list[near_node.parent].children.discard(i)
                    near_node.parent = new_node_index
                    s_d, s_fraction = RRTNode.calc_cost(self.start_state, d)
                    near_node.set_cost(new_cost, s_d + new_node.time_cost, s_fraction)
                    new_node.children.add(i)

    def get_nearest_list_index(self, rnd: RandomPoint):
        rnd_p = rnd.p
        node_keys = list(self.node_list.keys())
        node_positions = np.array([node.p for node in self.node_list.values()])

        # Compute squared distances directly and lazily find the min
        dist_squared = np.sum((node_positions - rnd_p) ** 2, axis=1)

        # Get the index with the minimum distance
        min_index = node_keys[np.argmin(dist_squared)]

        return min_index

    def check_no_collision_extend(
        self, parent_node: RRTNode, node: RRTNode
    ) -> Tuple[bool, float]:
        delta_pos = node.p - parent_node.p
        dist = float(np.linalg.norm(delta_pos))
        if parent_node.parent is not None:
            pass
            #  delta_pos_parent = parent_node.p - self.node_list[parent_node.parent].p
            #  angle_parent = self.angle_between_vectors(delta_pos_parent, delta_pos, dist)
            #  if not (np.radians(0) <= angle_parent <= np.radians(3) or
            #          np.radians(30) <= angle_parent <= np.radians(60)):
            #      return False, dist
        else:
            angle_start_end = self.angle_between_vectors(
                self.delta_pos_start_end, delta_pos, dist
            )
            if not (np.radians(0) <= angle_start_end <= np.radians(0.1)):
                return False, dist

        tmpNode = RRTNode(np.array([parent_node.p[0], parent_node.p[1]]))
        s_d, s_fraction = RRTNode.calc_cost(self.start_state, dist)
        s_d = s_d - np.ceil(s_fraction)

        for s in range(int(s_d)):
            fraction = s / s_d
            tmpNode.p = parent_node.p + delta_pos * fraction
            tmpNode.set_cost(0, parent_node.time_cost + s, 0.0)
            if not self.check_no_collision(tmpNode, self.obstacle_list):
                return False, dist
        return True, dist

    def check_no_collision(self, node: RRTNode, obstacleList: List[Obstacle]):
        for obs in obstacleList:
            if not obs.check_no_collision(node):
                # print(f'Hit obstacle {obs} at {node.p}')
                return False

        # The two trajectories will collide at the specific second
        scene = self.interpolator.get_scene_by_second(node.time_cost)
        for vessel2, vessel2_state in scene.items():
            if np.linalg.norm(node.p - vessel2_state.p) <= max(
                self.vessel.radius, vessel2.radius
            ):
                print(f"Hit trajectory of {vessel2} at {vessel2_state.p}.")
                return False
        return True  # safe

    def angle_between_vectors(self, vec1, vec2, dist2):
        # Calculate the dot product
        dot_product = np.dot(vec1, vec2)
        # Calculate the magnitudes of the vectors
        magnitude1 = np.linalg.norm(vec1)
        # Calculate the cosine of the angle
        cos_theta = dot_product / (magnitude1 * dist2)
        # Clip the cosine value to be within the valid range for arccos
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        # Calculate the angle in radians and then in degrees
        return np.arccos(cos_theta)
