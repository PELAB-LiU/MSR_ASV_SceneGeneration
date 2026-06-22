from typing import Dict, List, Union

import numpy as np

from logical_level.models.actor_variable import (ActorVariable,
                                                 StaticObstacleVariable,
                                                 VesselVariable)
from logical_level.models.values import (ActorValues, ObstacleValues,
                                         VesselValues)


class Assignments(Dict[ActorVariable, ActorValues]):
    def __init__(self, actor_variables: List[ActorVariable] = [], *args, **kwargs):
        super().__init__({var: None for var in actor_variables}, *args, **kwargs)

    def update_from_individual(
        self, states: Union[np.ndarray, List[float]]
    ) -> "Assignments":
        if len(states) != sum(len(var) for var in self.keys()):
            raise Exception("the variable number is insufficient.")

        index = 0
        for var in self.keys():
            if isinstance(var, VesselVariable):
                self[var] = VesselValues(
                    x=states[index + 0],
                    y=states[index + 1],
                    h=states[index + 2],
                    l=states[index + 3],
                    sp=states[index + 4],
                )
            elif isinstance(var, StaticObstacleVariable):
                self[var] = ObstacleValues(
                    x=states[index + 0], y=states[index + 1], r=states[index + 2]
                )
            else:
                raise Exception("The variable type is not supported.")
            index += len(var)
        return self
