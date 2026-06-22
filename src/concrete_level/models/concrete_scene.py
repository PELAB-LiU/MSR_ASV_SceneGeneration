from dataclasses import dataclass
from itertools import combinations, product
from typing import Any, Dict, List, Optional, Set, Type

from concrete_level.models.actor_state import ActorState
from concrete_level.models.concrete_actors import (ConcreteActor,
                                                   ConcreteStaticObstacle,
                                                   ConcreteVessel)
from logical_level.constraint_satisfaction.assignments import Assignments
from logical_level.models.actor_variable import ActorVariable
from logical_level.models.relation_constraints_concept.literals import (
    DoCollide, MayCollide)
from utils.serializable import Serializable


@dataclass(frozen=True)
class ConcreteScene(Serializable):
    _data: Dict[ConcreteActor, ActorState]
    dcpa: Optional[float] = None
    tcpa: Optional[float] = None
    danger_sector: Optional[float] = None
    proximity_index: Optional[float] = None

    first_level_hash: Optional[int] = None
    second_level_hash: Optional[int] = None
    is_relevant_by_fec: Optional[bool] = None
    is_relevant_by_fsm: Optional[bool] = None
    is_ambiguous_by_fec: Optional[bool] = None
    is_ambiguous_by_fsm: Optional[bool] = None

    @property
    def has_risk_metrics(self):
        return all(
            value is not None
            for value in [
                self.dcpa,
                self.tcpa,
                self.danger_sector,
                self.proximity_index,
            ]
        )

    @property
    def has_functional_hash(self):
        return all(
            value is not None
            for value in [
                self.first_level_hash,
                self.second_level_hash,
                self.is_relevant_by_fec,
                self.is_relevant_by_fsm,
                self.is_ambiguous_by_fec,
                self.is_ambiguous_by_fsm,
            ]
        )

    def __post_init__(self):
        object.__setattr__(self, "_data", dict(self._data))

    def __getitem__(self, key):
        return self._data[key]

    @property
    def actors(self) -> List[ConcreteActor]:
        return [actor for actor, _ in self.sorted_actor_states]

    @property
    def vessels(self) -> List[ConcreteVessel]:
        return [actor for actor, _ in self.sorted_actor_states if actor.is_vessel]

    @property
    def obstacles(self) -> List[ConcreteStaticObstacle]:
        return [actor for actor, _ in self.sorted_actor_states if not actor.is_vessel]

    @property
    def all_actor_pair_combinations(self):
        return {(ai, aj) for ai, aj in combinations(self.actors, 2)}

    @property
    def all_vessel_pair_combinations_with_obstacles(self):
        return self.all_vessel_pair_combinations.union(
            set(product(self.obstacles, self.vessels))
        )

    @property
    def all_vessel_pair_combinations(self):
        return {(ai, aj) for ai, aj in combinations(self.vessels, 2)}

    @property
    def actor_states(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    @property
    def sorted_actor_states(self):
        return sorted(self.items(), key=lambda item: item[0].id)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._data})"

    def as_dict(self) -> Dict[ConcreteActor, ActorState]:
        return self._data

    @property
    def individual(self) -> List[float]:
        individual: List[float] = []
        for actor, state in self.sorted_actor_states:
            if isinstance(actor, ConcreteVessel):
                individual += [
                    state.x,
                    state.y,
                    state.heading,
                    actor.length,
                    state.speed,
                ]
            elif isinstance(actor, ConcreteStaticObstacle):
                individual += [state.x, state.y, actor.radius]
            else:
                raise ValueError("Unsupported actor type.")
        return individual

    @property
    def actor_number(self) -> int:
        return len(self)

    @property
    def vessel_number(self) -> int:
        return len(self.vessels)

    @property
    def obstacle_number(self) -> int:
        return len(self.obstacles)

    @property
    def os(self) -> ConcreteVessel:
        vessel = next((vessel for vessel in self.vessels if vessel.is_os), None)
        if vessel is None:
            raise ValueError("No OS in the scene.")
        return vessel

    @property
    def ts_vessels(self) -> Set[ConcreteVessel]:
        return {vessel for vessel in self.vessels if not vessel.is_os}

    def assignments(self, variables: List[ActorVariable]) -> Assignments:
        if len(self) != len(variables):
            raise ValueError("Variable and actor numbers do not match.")
        for actor, var in zip(self.actors, variables):
            if actor.id != var.id:
                raise ValueError("Insufficient order of actors and variables.")
        return Assignments(variables).update_from_individual(self.individual)

    def may_collide(self, actor1: ConcreteActor, actor2: ConcreteVessel) -> bool:
        vars = {a: a.logical_variable for a in self.actors}
        return (
            MayCollide(vars[actor1], vars[actor2])
            .evaluate_penalty(self.assignments(list(vars.values())))
            .is_zero
        )

    def do_collide(self, actor1: ConcreteActor, actor2: ConcreteVessel) -> bool:
        vars = {a: a.logical_variable for a in self.actors}
        return (
            DoCollide(vars[actor1], vars[actor2])
            .evaluate_penalty(self.assignments(list(vars.values())))
            .is_zero
        )

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if key == "_data":
                result[key] = [
                    (actor.to_dict(), state.to_dict())
                    for actor, state in self._data.items()
                ]
            else:  # Handle primitive types
                result[key] = value
        return result

    @classmethod
    def from_dict(cls: Type["ConcreteScene"], data: Dict[str, Any]) -> "ConcreteScene":
        copy_data = data.copy()
        for attr, value in data.items():
            if attr == "_data":
                copy_data[attr] = {
                    ConcreteActor.from_dict(actor): ActorState.from_dict(state)
                    for actor, state in value
                }
                copy_data.pop("is_relevant", None)
                copy_data.pop("is_ambiguous", None)

        return ConcreteScene(**copy_data)
