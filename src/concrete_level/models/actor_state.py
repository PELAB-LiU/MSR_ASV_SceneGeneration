from dataclasses import dataclass
from typing import Any, Dict, Optional, Type

import numpy as np

from utils.serializable import Serializable


@dataclass(frozen=True)
class ActorState(Serializable):
    x: float
    y: float
    speed: float
    heading: float

    @property
    def p(self) -> np.ndarray:
        return np.array([self.x, self.y])

    @property
    def v(self) -> np.ndarray:
        return np.array([np.cos(self.heading), np.sin(self.heading)]) * self.speed

    @property
    def v_norm(self) -> np.ndarray:
        return self.v / self.speed

    @property
    def v_norm_perp(self) -> np.ndarray:
        return np.array([self.v_norm[1], -self.v_norm[0]])

    @property
    def heading_deg(self):
        return np.rad2deg(self.heading)

    def modify_copy(
        self,
        x: Optional[float] = None,
        y: Optional[float] = None,
        speed: Optional[float] = None,
        heading: Optional[float] = None,
    ) -> "ActorState":
        return ActorState(
            x if x is not None else self.x,
            y if y is not None else self.y,
            speed if speed is not None else self.speed,
            heading if heading is not None else self.heading,
        )

    @classmethod
    def from_dict(cls: Type["ActorState"], data: Dict[str, Any]) -> "ActorState":
        return ActorState(**data)
