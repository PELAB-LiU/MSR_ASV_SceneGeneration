import random
from typing import Dict, Optional

from concrete_level.models.actor_state import ActorState
from concrete_level.models.concrete_actors import (ConcreteActor,
                                                   ConcreteStaticObstacle,
                                                   ConcreteVessel)
from concrete_level.models.concrete_scene import ConcreteScene
from global_config import GlobalConfig
from logical_level.constraint_satisfaction.assignments import Assignments
from logical_level.models.actor_variable import (StaticObstacleVariable,
                                                 VesselVariable)
from logical_level.models.values import ObstacleValues, VesselValues
from utils.static_obstacle_types import ALL_STATIC_OBSTACLE_TYPES
from utils.vessel_types import ALL_VESSEL_TYPES


class SceneBuilder(Dict[ConcreteActor, ActorState]):
    def __init__(self, base_scene: Optional[ConcreteScene] = None, *args, **kwargs):
        # Initialize with an empty dict if no existing_dict is provided
        if base_scene is not None:
            existing_dict = base_scene._data
        else:
            existing_dict = {}
        self.base_scene = base_scene
        # Call the parent constructor with the provided data
        super().__init__(existing_dict, *args, **kwargs)

    def set_state(self, actor: ConcreteActor, state: ActorState) -> "SceneBuilder":
        self[actor] = state
        return self

    def build(
        self,
        dcpa=None,
        tcpa=None,
        danger_sector=None,
        proximity_index=None,
        first_level_hash=None,
        second_level_hash=None,
        is_relevant_by_fec=None,
        is_relevant_by_fsm=None,
        is_ambiguous_by_fec=None,
        is_ambiguous_by_fsm=None,
    ) -> ConcreteScene:
        return ConcreteScene(
            self,
            **{
                key: value if value is not None else getattr(self.base_scene, key, None)
                for key, value in {
                    "dcpa": dcpa,
                    "tcpa": tcpa,
                    "danger_sector": danger_sector,
                    "proximity_index": proximity_index,
                    "first_level_hash": first_level_hash,
                    "second_level_hash": second_level_hash,
                    "is_relevant_by_fec": is_relevant_by_fec,
                    "is_relevant_by_fsm": is_relevant_by_fsm,
                    "is_ambiguous_by_fec": is_ambiguous_by_fec,
                    "is_ambiguous_by_fsm": is_ambiguous_by_fsm,
                }.items()
            }
        )

    @staticmethod
    def build_from_assignments(assignments: Assignments) -> ConcreteScene:
        builder = SceneBuilder()
        for actor_var, values in assignments.items():
            if isinstance(actor_var, VesselVariable) and isinstance(
                values, VesselValues
            ):
                vessel_type = actor_var.vessel_type
                if vessel_type.is_unspecified:
                    valid_types = [
                        ALL_VESSEL_TYPES[t]
                        for t in GlobalConfig.VALID_VESSEL_TYPES
                        if ALL_VESSEL_TYPES[t].do_match(values.l, values.sp)
                    ]
                    vessel_type = random.choice(valid_types)
                builder.set_state(
                    ConcreteVessel(
                        id=actor_var.id,
                        radius=values.r,
                        type=vessel_type.name,
                        is_os=actor_var.is_os,
                        length=values.l,
                        max_speed=vessel_type.max_speed,
                    ),
                    ActorState(
                        x=values.x, y=values.y, speed=values.sp, heading=values.h
                    ),
                )
            elif isinstance(actor_var, StaticObstacleVariable) and isinstance(
                values, ObstacleValues
            ):
                obstacle_type = actor_var.obstacle_type
                if obstacle_type.is_unspecified:
                    valid_types = [
                        ALL_STATIC_OBSTACLE_TYPES[t]
                        for t in GlobalConfig.VALID_STATIC_OBSTACLE_TYPES
                        if ALL_STATIC_OBSTACLE_TYPES[t].do_match(values.r)
                    ]
                    obstacle_type = random.choice(valid_types)
                builder.set_state(
                    ConcreteStaticObstacle(
                        id=actor_var.id, radius=values.r, type=obstacle_type.name
                    ),
                    ActorState(x=values.x, y=values.y, speed=0, heading=0),
                )
            else:
                raise TypeError("Unsupported Actor")
        return builder.build()
