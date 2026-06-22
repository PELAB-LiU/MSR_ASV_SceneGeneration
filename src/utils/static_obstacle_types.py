from abc import ABC
from dataclasses import dataclass
from typing import Dict

from global_config import GlobalConfig


@dataclass(frozen=True, repr=False)
class StaticObstacleType(ABC):
    name: str = "StaticObstacleType"
    min_radius: float = GlobalConfig.MIN_OBSTACLE_RADIUS
    max_radius: float = GlobalConfig.MAX_OBSTACLE_RADIUS

    def do_match(self, radius: float) -> bool:
        return (
            self.min_radius - GlobalConfig.EPSILON
            <= radius
            <= self.max_radius + GlobalConfig.EPSILON
        )

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    @property
    def is_unspecified(self) -> bool:
        return False


@dataclass(frozen=True, repr=False)
class UnspecifiedObstacleType(StaticObstacleType):
    name: str = "UnspecifiedType"

    @property
    def is_unspecified(self) -> bool:
        return True


@dataclass(frozen=True, repr=False)
class OtherObstacleType(StaticObstacleType):
    name: str = "OtherType"
    pass


@dataclass(frozen=True, repr=False)
class SmallObstacle(StaticObstacleType):
    name: str = "SmallObstacle"
    max_radius: float = 50


@dataclass(frozen=True, repr=False)
class MediumObstacle(StaticObstacleType):
    name: str = "MediumObstacle"
    min_radius: float = 50
    max_radius: float = 200


@dataclass(frozen=True, repr=False)
class LargeObstacle(StaticObstacleType):
    name: str = "LargeObstacle"
    min_radius: float = 200


# ALL_STATIC_OBSTACLE_TYPES : List[StaticObstacleType] = [OtherObstacleType(), SmallObstacle(), MediumObstacle(), LargeObstacle()]
ALL_STATIC_OBSTACLE_TYPES: Dict[str, StaticObstacleType] = {
    "OtherType": OtherObstacleType(),
    "SmallObstacle": SmallObstacle(),
    "MediumObstacle": MediumObstacle(),
    "LargeObstacle": LargeObstacle(),
    "UnspecifiedType": UnspecifiedObstacleType(),
}

DEFAULT_OBSTACLE_TYPE = UnspecifiedObstacleType()
