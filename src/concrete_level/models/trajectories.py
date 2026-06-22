import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Type, Union

import numpy as np

from concrete_level.models.actor_state import ActorState
from concrete_level.models.concrete_actors import ConcreteActor, ConcreteVessel
from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.trajectory_generation.scene_builder import SceneBuilder
from utils.serializable import Serializable


@dataclass(frozen=True)
class Trajectories(Serializable):
    _data: Dict[ConcreteVessel, List[ActorState]]

    def __post_init__(self):
        object.__setattr__(self, "_data", dict(self._data).copy())

    def __getitem__(self, index) -> Union["Trajectories", List[ActorState]]:
        if isinstance(index, slice):  # Handle slicing
            return Trajectories({key: value[index] for key, value in self.items()})
        return self._data[index]

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._data})"

    def get_scene(self, t: int) -> ConcreteScene:
        if t >= self.timespan:
            raise ValueError("Timespan out of range.")
        sb = SceneBuilder()
        for vessel, states in self.items():
            sb.set_state(vessel, states[t])
        return sb.build()

    @property
    def timespan(self) -> int:
        return (
            0
            if len(self._data) == 0
            else min(len(states) for states in self._data.values())
        )

    @property
    def initial_scene(self) -> ConcreteScene:
        return self.get_scene(0)

    def collision_points(
        self, vessel: ConcreteVessel
    ) -> Dict[ConcreteVessel, List[np.ndarray]]:
        other_vessels = [v for v in self.keys() if v is not vessel]
        collision_points: Dict[ConcreteVessel, List[np.ndarray]] = defaultdict(list)
        for vessel2 in other_vessels:
            for t in range(self.timespan):
                scene = self.get_scene(t)
                if scene.do_collide(vessel, vessel2):
                    collision_points[vessel2] += [scene[vessel].p, scene[vessel2].p]
        return collision_points

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if key == "_data":
                result[key] = [
                    (vessel.to_dict(), [state.to_dict() for state in states])
                    for vessel, states in self._data.items()
                ]
            else:  # Handle primitive types
                result[key] = value
        return result

    @classmethod
    def from_dict(cls: Type["Trajectories"], data: Dict[str, Any]) -> "Trajectories":
        copy_data = data.copy()
        for attr, value in data.items():
            if attr == "_data":
                copy_data[attr] = {
                    ConcreteActor.from_dict(vessel): [
                        ActorState.from_dict(state) for state in states
                    ]
                    for vessel, states in value
                }
        return Trajectories(**copy_data)
