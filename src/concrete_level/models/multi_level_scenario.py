from typing import Dict, Optional, Set, Tuple, Union

from concrete_level.models.concrete_actors import (ConcreteActor,
                                                   ConcreteStaticObstacle,
                                                   ConcreteVessel)
from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.trajectory_generation.scene_builder import SceneBuilder
from functional_level.metamodels.functional_scenario import (
    FuncObject, FunctionalScenario)
from logical_level.constraint_satisfaction.evaluation_cache import (
    EvaluationCache, VesselToVesselProperties)
from logical_level.models.actor_variable import ActorVariable
from logical_level.models.logical_scenario import LogicalScenario
from logical_level.models.penalty import Penalty
from logical_level.models.relation_constraints_concept.literals import (
    DoCollide, MayCollide)


class MultiLevelScenario:
    def __init__(
        self,
        concrete_scene: ConcreteScene,
        logical_scenario: LogicalScenario,
        functional_scenario: FunctionalScenario,
    ):
        self.concrete_scene = concrete_scene
        self.logical_scenario = logical_scenario
        self.functional_scenario = functional_scenario

        self.concrete_actor_map: Dict[int, ConcreteActor] = {
            actor.id: actor for actor in self.concrete_scene.actors
        }
        self.logical_actor_map: Dict[int, ActorVariable] = {
            actor.id: actor for actor in self.logical_scenario.actor_variables
        }
        self.functional_object_map: Dict[int, FuncObject] = {
            obj.id: obj for obj in self.functional_scenario.sorted_sea_objects
        }
        self.assignments = self.concrete_scene.assignments(
            self.logical_scenario.actor_variables
        )
        self.evaluation_cache = EvaluationCache(self.assignments)

    @property
    def penalty(self) -> Penalty:
        return self.logical_scenario.relation_constraint.evaluate_penalty(
            self.assignments
        )

    def to_concrete_vessel(
        self, actor_or_obj: Union[ConcreteActor, FuncObject]
    ) -> ConcreteScene:
        return self.concrete_actor_map[actor_or_obj.id]

    def to_variable(
        self, actor_or_obj: Union[ConcreteActor, FuncObject]
    ) -> ActorVariable:
        return self.logical_actor_map[actor_or_obj.id]

    def to_object(
        self, actor_or_var: Union[ActorVariable, ConcreteActor]
    ) -> FuncObject:
        return self.functional_object_map[actor_or_var.id]

    def get_geo_props(
        self, actor1: ConcreteActor, actor2: ConcreteVessel
    ) -> VesselToVesselProperties:
        var1, var2 = self.to_variable(actor1), self.to_variable(actor2)
        return self.evaluation_cache.get_props(var1, var2)

    def may_collide(self, actor1: ConcreteActor, actor2: ConcreteVessel) -> bool:
        var1, var2 = self.to_variable(actor1), self.to_variable(actor2)
        may_collide = MayCollide(var1, var2)
        return may_collide._evaluate_penalty(self.evaluation_cache).is_zero

    def do_collide(self, actor1: ConcreteActor, actor2: ConcreteVessel) -> bool:
        var1, var2 = self.to_variable(actor1), self.to_variable(actor2)
        do_collide = DoCollide(var1, var2)
        return do_collide._evaluate_penalty(self.evaluation_cache).is_zero

    def may_collide_anyone(self, vessel: ConcreteVessel) -> bool:
        for actor2 in self.concrete_actor_map.values():
            if vessel == actor2:
                continue
            if self.may_collide(actor2, vessel):
                return True
        return False

    @property
    def os_ts_pairs(self) -> Set[Tuple[ConcreteVessel, ConcreteVessel]]:
        os = self.concrete_scene.os
        return {(os, vessel) for vessel in self.concrete_scene.ts_vessels}

    @property
    def ts_ts_pairs(self) -> Set[Tuple[ConcreteVessel, ConcreteVessel]]:
        ts = list(self.concrete_scene.ts_vessels)
        return {(ts[i], ts[j]) for i in range(len(ts)) for j in range(i + 1, len(ts))}

    @property
    def os_obstacle_pairs(self) -> Set[Tuple[ConcreteVessel, ConcreteStaticObstacle]]:
        os = self.concrete_scene.os
        return {(os, obst) for obst in self.concrete_scene.obstacles}

    def get_actor_name(self, actor: ConcreteActor) -> str:
        return self.to_variable(actor).name

    def modify_state_get_new_scene(
        self,
        actor: ConcreteActor,
        x: Optional[float] = None,
        y: Optional[float] = None,
        speed: Optional[float] = None,
        heading: Optional[float] = None,
    ) -> "MultiLevelScenario":
        new_state = self.concrete_scene[actor].modify_copy(
            x=x, y=y, speed=speed, heading=heading
        )
        new_scene = (
            SceneBuilder(self.concrete_scene).set_state(actor, new_state).build()
        )
        return MultiLevelScenario(
            new_scene, self.logical_scenario, self.functional_scenario
        )
