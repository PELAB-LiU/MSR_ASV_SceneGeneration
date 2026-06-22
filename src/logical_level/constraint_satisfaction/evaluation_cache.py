from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

import numpy as np

from global_config import GlobalConfig, o2VisibilityByo1, vis_distance
from logical_level.constraint_satisfaction.assignments import Assignments
from logical_level.models.actor_variable import (ActorVariable,
                                                 StaticObstacleVariable,
                                                 VesselVariable)
from logical_level.models.values import ActorValues, VesselValues
from utils.math_utils import compute_angle


class GeometricProperties(ABC):

    def __init__(
        self, var1: ActorVariable, var2: VesselVariable, assignments: Assignments
    ):
        self.val1: ActorValues = assignments[var1]
        self.val2: VesselValues = assignments[var2]

        self.safety_dist = max(self.val1.r, self.val2.r)

        self.p12 = self.val2.p - self.val1.p
        self.p21 = -self.p12  # Avoid redundant calculations

        # Compute norm of relative position vector (distance)
        self.o_distance = float(max(np.linalg.norm(self.p12), GlobalConfig.EPSILON))

        # Compute visibility angles
        self.angle_p21_v2 = compute_angle(
            self.p21, self.val2.v, self.o_distance, self.val2.sp
        )

        self.sin_half_col_cone_theta = np.clip(
            max(self.val1.r, self.val2.r) / self.o_distance, -1, 1
        )
        self.angle_half_col_cone = abs(np.arcsin(self.sin_half_col_cone_theta))

        self.dcpa = 0.0
        self.tcpa = 0.0
        self.vis_distance = 0.0

    @abstractmethod
    def get_collision_points(self, time_limit=np.inf) -> List[np.ndarray]:
        pass

    @staticmethod
    def factory(
        var1: ActorVariable, var2: ActorVariable, assignments: Assignments
    ) -> "GeometricProperties":
        if isinstance(var1, VesselVariable) and isinstance(var2, VesselVariable):
            return VesselToVesselProperties(var1, var2, assignments)
        elif isinstance(var1, StaticObstacleVariable) and isinstance(
            var2, VesselVariable
        ):
            return ObstacleToVesselProperties(var1, var2, assignments)
        else:
            raise NotImplementedError(
                "The variable types are not supported or they might be in the wrong order (Obstacle variable has to come first)."
            )


class ObstacleToVesselProperties(GeometricProperties):
    def __init__(
        self,
        var1: StaticObstacleVariable,
        var2: VesselVariable,
        assignments: Assignments,
    ):
        super().__init__(var1, var2, assignments)
        self.tcpa = np.dot(self.p21, self.val2.v_norm)
        self.dcpa = np.linalg.norm(self.p21 - self.tcpa * self.val2.v_norm)
        self.vis_distance = o2VisibilityByo1(True, self.val1.r)

    def get_collision_points(self, time_limit=np.inf) -> List[np.ndarray]:
        # Coefficients for the quadratic equation
        a = np.dot(self.val2.v, self.val2.v)
        b = 2 * np.dot(self.p12, self.val2.v)
        c = np.dot(self.p12, self.p12) - self.safety_dist**2

        # Calculate discriminant
        discriminant = b**2 - 4 * a * c

        # Check for real solutions (collision possible)
        if discriminant < 0:
            return []

        sqrt_discriminant = np.sqrt(discriminant)
        collision_points = []

        # Find times of collision
        t1 = (-b + sqrt_discriminant) / (2 * a)
        t2 = (-b - sqrt_discriminant) / (2 * a)

        # Check if times are within the time limit and positive
        for t in [t1, t2]:
            if 0 <= t <= time_limit:
                # Compute the collision points
                collision_point_vessel2 = self.val2.p + self.val2.v * t
                collision_points.append(collision_point_vessel2)

        # Return the list of collision points as standard list of np.ndarray
        return collision_points


class VesselToVesselProperties(GeometricProperties):

    def __init__(self, var1, var2, assignments):
        super().__init__(var1, var2, assignments)
        self.val1: VesselValues
        self.v12 = self.val1.v - self.val2.v
        self.v12_norm_stable = max(np.linalg.norm(self.v12), GlobalConfig.EPSILON)

        # Compute angles
        self.angle_p12_v1 = compute_angle(
            self.p12, self.val1.v, self.o_distance, self.val1.sp
        )

        # Compute visibility distance
        self.vis_distance = vis_distance(
            self.angle_p21_v2 >= GlobalConfig.SIDE_ANGLE,
            self.val2.l,
            self.angle_p12_v1 >= GlobalConfig.SIDE_ANGLE,
            self.val1.l,
        )

        # Compute time and distance to closest approach
        self.tcpa = np.dot(self.p12, self.v12) / self.v12_norm_stable**2
        self.dcpa = float(np.linalg.norm(self.p21 + self.v12 * max(0, self.tcpa)))

    def get_collision_points(self, time_limit=np.inf) -> List[np.ndarray]:
        # Relative position and velocity
        v_21 = self.val2.v - self.val1.v

        # Coefficients for the quadratic equation
        a = np.dot(v_21, v_21)
        b = 2 * np.dot(self.p12, v_21)
        c = np.dot(self.p12, self.p12) - self.safety_dist**2

        # Calculate discriminant
        discriminant = b**2 - 4 * a * c

        # Check for real solutions (collision possible)
        if discriminant < 0:
            return []

        sqrt_discriminant = np.sqrt(discriminant)
        collision_points = []

        # Find times of collision
        t1 = (-b + sqrt_discriminant) / (2 * a)
        t2 = (-b - sqrt_discriminant) / (2 * a)

        # Check if times are within the time limit and positive
        for t in [t1, t2]:
            if 0 <= t <= time_limit:
                # Compute the collision points
                collision_point_vessel1 = self.val1.p + self.val1.v * t
                collision_points.append(collision_point_vessel1)

        # Return the list of collision points as standard list of np.ndarray
        return collision_points


class EvaluationCache(Dict[Tuple[ActorVariable, ActorVariable], GeometricProperties]):
    def __init__(self, assignments: Assignments, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assignments = assignments

    def get_props(
        self, var1: ActorVariable, var2: ActorVariable
    ) -> GeometricProperties:
        props = self.get((var1, var2), None)
        if props is None:
            props = GeometricProperties.factory(var1, var2, self.assignments)
            self[(var1, var2)] = props
        return props

    def get_collision_points(
        self, var1: ActorVariable, var2: ActorVariable, time_limit=np.inf
    ) -> List[np.ndarray]:
        return self.get_props(var1, var2).get_collision_points(time_limit)
