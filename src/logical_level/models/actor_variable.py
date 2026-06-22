from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

import numpy as np

from global_config import GlobalConfig
from utils.static_obstacle_types import (DEFAULT_OBSTACLE_TYPE,
                                         StaticObstacleType)
from utils.vessel_types import (ALL_VESSEL_TYPES, DEFAULT_VESSEL_TYPE,
                                VesselType)


@dataclass(frozen=True)
class ActorVariable(ABC):
    id: int

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.name

    @property
    @abstractmethod
    def upper_bounds(self) -> List[float]:
        pass

    @property
    @abstractmethod
    def lower_bounds(self) -> List[float]:
        pass

    @property
    @abstractmethod
    def is_vessel(self) -> bool:
        pass

    def __len__(self) -> int:
        return len(self.lower_bounds)

    @property
    def min_coord(self) -> float:
        return GlobalConfig.MIN_COORD

    @property
    def max_coord(self) -> float:
        return GlobalConfig.MAX_COORD

    @property
    @abstractmethod
    def type_name(self) -> str:
        pass


@dataclass(frozen=True)
class VesselVariable(ActorVariable, ABC):
    vessel_type: VesselType = DEFAULT_VESSEL_TYPE

    @property
    def type_name(self) -> str:
        return self.vessel_type.name

    @property
    def min_length(self) -> float:
        return self.vessel_type.min_length - GlobalConfig.EPSILON

    @property
    def max_length(self) -> float:
        return self.vessel_type.max_length + GlobalConfig.EPSILON

    @property
    def min_beam(self) -> float:
        return self.vessel_type.min_beam - GlobalConfig.EPSILON

    @property
    def max_beam(self) -> float:
        return self.vessel_type.max_beam + GlobalConfig.EPSILON

    @property
    def min_speed(self) -> float:
        return self.vessel_type.min_speed - GlobalConfig.EPSILON

    @property
    def max_speed(self) -> float:
        return self.vessel_type.max_speed + GlobalConfig.EPSILON

    @property
    def min_heading(self) -> float:
        return GlobalConfig.MIN_HEADING - GlobalConfig.EPSILON

    @property
    def max_heading(self) -> float:
        return GlobalConfig.MAX_HEADING + GlobalConfig.EPSILON

    @property
    def is_vessel(self) -> bool:
        return True

    @property
    @abstractmethod
    def is_os(self) -> bool:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def upper_bounds(self) -> List[float]:
        return [
            self.max_coord,
            self.max_coord,
            self.max_heading,
            self.max_length,
            self.max_speed,
        ]

    @property
    def lower_bounds(self) -> List[float]:
        return [
            self.min_coord,
            self.min_coord,
            self.min_heading,
            self.min_length,
            self.min_speed,
        ]


@dataclass(frozen=True)
class OSVariable(VesselVariable):
    vessel_type: VesselType = ALL_VESSEL_TYPES[GlobalConfig.OS_VESSEL_TYPE]

    @property
    def min_heading(self) -> float:
        return GlobalConfig.MAX_HEADING / 2 - GlobalConfig.EPSILON

    @property
    def max_heading(self) -> float:
        return GlobalConfig.MAX_HEADING / 2 + GlobalConfig.EPSILON

    @property
    def min_coord(self) -> float:
        return GlobalConfig.OS_COORD - GlobalConfig.EPSILON

    @property
    def max_coord(self) -> float:
        return GlobalConfig.OS_COORD + GlobalConfig.EPSILON

    @property
    def name(self) -> str:
        return f"OS_{self.id}"

    @property
    def is_os(self) -> bool:
        return True


@dataclass(frozen=True)
class TSVariable(VesselVariable):
    @property
    def name(self) -> str:
        return f"TS_{self.id}"

    @property
    def is_os(self) -> bool:
        return False


@dataclass(frozen=True)
class StaticObstacleVariable(ActorVariable):
    obstacle_type: StaticObstacleType = DEFAULT_OBSTACLE_TYPE

    @property
    def type_name(self) -> str:
        return self.obstacle_type.name

    @property
    def name(self) -> str:
        return f"SO_{self.id}"

    @property
    def min_radius(self) -> float:
        return self.obstacle_type.min_radius

    @property
    def max_radius(self) -> float:
        return self.obstacle_type.max_radius

    @property
    def upper_bounds(self) -> List[float]:
        return [self.max_coord, self.max_coord, self.max_radius]

    @property
    def lower_bounds(self) -> List[float]:
        return [self.min_coord, self.min_coord, self.min_radius]

    @property
    def is_vessel(self) -> bool:
        return False
