from dataclasses import dataclass, field

import numpy as np

from global_config import vessel_radius


@dataclass(frozen=True)
class ActorValues:
    x: float
    y: float
    p: np.ndarray = field(init=False)
    r: float = field(init=False)
    l: float = field(default=1, init=False)

    def __post_init__(self):
        object.__setattr__(self, "p", np.array([self.x, self.y]))


@dataclass(frozen=True)
class VesselValues(ActorValues):
    h: float
    l: float = field(init=True)
    sp: float

    v: np.ndarray = field(init=False)
    v_norm: np.ndarray = field(init=False)
    v_norm_perp: np.ndarray = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(
            self, "v", np.array([np.cos(self.h), np.sin(self.h)]) * self.sp
        )
        object.__setattr__(self, "v_norm", self.v / self.sp)
        object.__setattr__(
            self, "v_norm_perp", np.array([self.v_norm[1], -self.v_norm[0]])
        )
        object.__setattr__(self, "r", vessel_radius(self.l))


@dataclass(frozen=True)
class ObstacleValues(ActorValues):
    r: float = field(init=True)

    def __post_init__(self):
        super().__post_init__()
