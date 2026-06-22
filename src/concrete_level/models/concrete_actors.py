from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Type

import numpy as np

from functional_level.metamodels.functional_object import FuncObject
from functional_level.models.functional_scenario_builder import \
    FunctionalScenarioBuilder
from logical_level.models.actor_variable import (ActorVariable, OSVariable,
                                                 StaticObstacleVariable,
                                                 TSVariable, VesselVariable)
from utils.serializable import Serializable
from utils.static_obstacle_types import ALL_STATIC_OBSTACLE_TYPES
from utils.vessel_types import ALL_VESSEL_TYPES


@dataclass(frozen=True)
class ConcreteActor(Serializable, ABC):
    id: int
    is_vessel: bool
    radius: float
    type: str

    @classmethod
    def from_dict(cls: Type["ConcreteActor"], data: Dict[str, Any]) -> "ConcreteActor":
        new_data = {k: v for k, v in data.items() if k != "is_vessel"}
        if data["is_vessel"]:
            return ConcreteVessel.from_dict(new_data)
        return ConcreteStaticObstacle.from_dict(new_data)

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def logical_variable(self) -> ActorVariable:
        pass

    @abstractmethod
    def create_abstraction(
        self, builder: FunctionalScenarioBuilder
    ) -> Tuple[ActorVariable, FuncObject]:
        pass

    def __repr__(self):
        return self.name


@dataclass(frozen=True)
class ConcreteStaticObstacle(ConcreteActor):
    is_vessel: bool = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "is_vessel", False)

    @property
    def name(self) -> str:
        return f"SO_{self.id}"

    @property
    def p(self) -> np.ndarray:
        return np.array([self.x, self.y])

    @property
    def logical_variable(self) -> "StaticObstacleVariable":
        t = ALL_STATIC_OBSTACLE_TYPES[self.type]
        return StaticObstacleVariable(self.id, t)

    def create_abstraction(
        self, builder: FunctionalScenarioBuilder
    ) -> Tuple[ActorVariable, FuncObject]:
        logical_variable = self.logical_variable
        obj = builder.add_new_obstacle(self.id)
        t_obj = builder.find_obstacle_type_by_name(logical_variable.type_name)
        builder.static_obstacle_type_interpretation.add(obj, t_obj)
        return logical_variable, obj

    @classmethod
    def from_dict(
        cls: Type["ConcreteStaticObstacle"], data: Dict[str, Any]
    ) -> "ConcreteStaticObstacle":
        return ConcreteStaticObstacle(**data)


@dataclass(frozen=True)
class ConcreteVessel(ConcreteActor):
    is_os: bool
    length: float
    max_speed: float
    beam: Optional[float] = None

    is_vessel: bool = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "is_vessel", True)

    @property
    def name(self) -> str:
        return f"OS_{self.id}" if self.is_os else f"TS_{self.id}"

    @property
    def max_turning_angle(self) -> float:
        return self.max_speed / 2.5 * self.length

    @property
    def max_acceleration(self) -> float:
        # return self.max_speed**2 / (2* 15 * self.length)
        return 0.5

    @property
    def logical_variable(self) -> VesselVariable:
        t = ALL_VESSEL_TYPES[self.type]
        return OSVariable(self.id, t) if self.is_os else TSVariable(self.id, t)

    def create_abstraction(
        self, builder: FunctionalScenarioBuilder
    ) -> Tuple[ActorVariable, FuncObject]:
        logical_variable = self.logical_variable
        obj = builder.add_new_os(self.id) if self.is_os else builder.add_new_ts(self.id)
        t_obj = builder.find_vessel_type_by_name(logical_variable.type_name)
        builder.static_obstacle_type_interpretation.add(obj, t_obj)
        return logical_variable, obj

    @classmethod
    def from_dict(
        cls: Type["ConcreteVessel"], data: Dict[str, Any]
    ) -> "ConcreteVessel":
        return ConcreteVessel(**data)
