from typing import List, Optional, Tuple

import numpy as np
import pygame

from concrete_level.models.rrt_models import (CircularObstacle, LineObstacle,
                                              Obstacle, PolygonalObstacle,
                                              RRTNode)
from concrete_level.models.vessel_order_graph import VesselNode
from concrete_level.trajectory_generation.path_interpolator import \
    PathInterpolator


class TrajectoryVisualizer:
    def __init__(
        self, dim: int, scaler: float, sample_area: List[Tuple[float, float]]
    ) -> None:
        self.scaler = scaler
        self.sample_area = sample_area
        self.dim = dim
        window_size = [dim, dim]
        pygame.init()
        self.screen = pygame.display.set_mode(window_size)

    def set_caption(self, v_node: VesselNode, interpolator: PathInterpolator):
        conf_rels = ""
        for rel in v_node.relations:
            conf_rels = str(rel) if not conf_rels else f"{conf_rels}, {str(rel)}"

        conf_trajs = ""
        for vessel in interpolator.vessels:
            conf_trajs = (
                vessel.name if not conf_trajs else f"{conf_trajs}, {vessel.name}"
            )

        pygame.display.set_caption(
            f"{conf_rels}, Conflicting trajectories: {conf_trajs}"
        )

    def draw_obstacles(
        self,
        obstacle_list: List[Obstacle],
        collision_points: List[np.ndarray],
        min_go_around_line: LineObstacle,
        go_around_split_line: LineObstacle,
    ):
        for o in obstacle_list:
            if isinstance(o, LineObstacle):
                self.draw_line(o, (0, 0, 0), 5)
            elif isinstance(o, CircularObstacle):
                pygame.draw.circle(
                    self.screen,
                    (255, 0, 0),
                    self.reverse_coord(o.p),
                    o.radius * self.scaler,
                    width=5,
                )
            elif isinstance(o, PolygonalObstacle):
                pygame.draw.polygon(
                    self.screen, (0, 0, 0), [self.reverse_coord(p) for p in o.polygon]
                )

        self.draw_line(min_go_around_line, (255, 165, 0), 5)
        self.draw_line(go_around_split_line, (255, 165, 0), 5)

        for cp in collision_points:
            pygame.draw.circle(self.screen, (255, 0, 0), self.reverse_coord(cp), 3)

    def draw_line(self, line: LineObstacle, color: Tuple[int, int, int], width: int):
        start = self.reverse_coord(
            line.shifted_point + line.dir_vec * 2 * self.dim / self.scaler
        )
        end = self.reverse_coord(
            line.shifted_point - line.dir_vec * 2 * self.dim / self.scaler
        )
        pygame.draw.line(self.screen, color, start, end, width - 1)
        pygame.draw.circle(
            self.screen, (23, 231, 5), self.reverse_coord(line.shifted_point), width
        )

    def draw_branches(
        self,
        start: RRTNode,
        end: RRTNode,
        node_list: dict[int, RRTNode],
        last_index: Optional[int],
        gen_final_course,
    ):
        pygame.draw.circle(self.screen, (0, 0, 255), self.reverse_coord(start.p), 7)
        pygame.draw.circle(self.screen, (0, 255, 255), self.reverse_coord(end.p), 7)
        # Branches
        for node in node_list.values():
            if node.parent is not None:
                pygame.draw.line(
                    self.screen,
                    (0, 255, 0),
                    self.reverse_coord(node_list[node.parent].p),
                    self.reverse_coord(node.p),
                )
        for node in node_list.values():
            if len(node.children) == 0:
                pygame.draw.circle(
                    self.screen, (255, 0, 255), self.reverse_coord(node.p), 2
                )

        # Final path
        if last_index is not None:
            path: List[RRTNode] = gen_final_course(last_index)

            ind = len(path)
            while ind > 1:
                color = (0, 0, 0)
                pygame.draw.line(
                    self.screen,
                    color,
                    self.reverse_coord(path[ind - 2].p),
                    self.reverse_coord(path[ind - 1].p),
                    5,
                )
                ind -= 1

    def update(
        self,
        obstacle_list: List[Obstacle],
        collision_points: List[np.ndarray],
        min_go_around_line: LineObstacle,
        go_around_split_line: LineObstacle,
        start: RRTNode,
        end: RRTNode,
        node_list: dict[int, RRTNode],
        last_index: Optional[int],
        gen_final_course,
    ):
        self.screen.fill((255, 255, 255))
        self.draw_obstacles(
            obstacle_list, collision_points, min_go_around_line, go_around_split_line
        )
        self.draw_branches(start, end, node_list, last_index, gen_final_course)
        pygame.display.update()

    def handle_user_input(
        self, end: RRTNode, obstacle_list: List[Obstacle], path_validation
    ) -> bool:
        for e in pygame.event.get():
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    coords = self.inverse_reverse_coord(np.array(e.pos))
                    obstacle_list.append(CircularObstacle(coords, 3000))
                    path_validation()
                elif e.button == 3:
                    end.p = self.inverse_reverse_coord(np.array(e.pos))
                    path_validation()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    return True
                elif e.key == pygame.K_ESCAPE:
                    exit(0)
        return False

    def reverse_coord(self, coords: np.ndarray):
        return np.array(
            [
                (coords[0] - self.sample_area[0][0]) * self.scaler + 50,
                self.dim - (coords[1] - self.sample_area[1][0]) * self.scaler - 50,
            ]
        )

    def inverse_reverse_coord(self, coords: np.ndarray):
        return np.array(
            [
                (coords[0] - 50) / self.scaler + self.sample_area[0][0],
                (self.dim - coords[1] - 50) / self.scaler + self.sample_area[1][0],
            ]
        )
