from typing import Dict, List

from concrete_level.models.actor_state import ActorState
from concrete_level.models.concrete_actors import ConcreteVessel
from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.models.trajectories import Trajectories
from global_config import GlobalConfig


class TrajectoryBuilder(Dict[ConcreteVessel, List[ActorState]]):
    def __init__(
        self,
        existing_dict: Dict[ConcreteVessel, List[ActorState]] = {},
        *args,
        **kwargs
    ):
        super().__init__(existing_dict.copy(), *args, **kwargs)

    def add_state(self, vessel: ConcreteVessel, state: ActorState):
        if vessel not in self:
            self[vessel] = [state]
        else:
            self[vessel].append(state)

    def add_scene(self, scene: ConcreteScene):
        for vessel, state in scene.items():
            self.add_state(vessel, state)

    def build(self):
        return Trajectories(self.even_lengths())

    @staticmethod
    def default_trajectory_from_scene(
        scene: ConcreteScene, length: int = GlobalConfig.ONE_HOUR_IN_SEC
    ) -> Trajectories:
        builder = TrajectoryBuilder()
        builder.add_scene(scene)
        builder.extend(length)
        return builder.build()

    def extend(self, length: int = GlobalConfig.ONE_HOUR_IN_SEC) -> "TrajectoryBuilder":
        for vessel in self.keys():
            self[vessel] = self.extend_trajectory(self[vessel], length)
        return self

    def even_lengths(self) -> "TrajectoryBuilder":
        if not self:
            return self
        return self.extend(max(len(states) for states in self.values()))

    def extend_trajectory(
        self, trajectory: List[ActorState], length: int = GlobalConfig.ONE_HOUR_IN_SEC
    ) -> List[ActorState]:
        new_trajectory = trajectory.copy()
        while len(new_trajectory) < length:
            turned_state = new_trajectory[-1].modify_copy(
                heading=new_trajectory[0].heading
            )
            new_p = turned_state.p + turned_state.v
            new_trajectory.append(turned_state.modify_copy(x=new_p[0], y=new_p[1]))
        return new_trajectory

    def shift_states_to_zero(self) -> "TrajectoryBuilder":
        for vessel in self.keys():
            self[vessel] = [
                state.modify_copy(
                    x=state.x - GlobalConfig.OS_COORD, y=state.y - GlobalConfig.OS_COORD
                )
                for state in self[vessel]
            ]
        return self
