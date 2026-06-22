from itertools import combinations, product
from typing import List

from functional_level.models.object_generator import IdGenerator
from logical_level.mapping.instance_initializer import \
    RandomInstanceInitializer
from logical_level.mapping.logical_scenario_builder import \
    LogicalScenarioBuilder
from logical_level.models.actor_variable import (OSVariable,
                                                 StaticObstacleVariable,
                                                 TSVariable)
from logical_level.models.logical_scenario import LogicalScenario
from logical_level.models.relation_constraints_concept.composites import \
    RelationConstrTerm
from logical_level.models.relation_constraints_concept.predicates import (
    AtVisAndMayCollide, AtVisAndMayCollideSoon, OutVisOrMayNotCollide)


class LogicalModelManager:
    __scenario_cache_map = {
        (1, 0): None,
        (1, 1): None,
        (2, 0): None,
        (2, 1): None,
        (3, 0): None,
        (3, 1): None,
        (4, 0): None,
        (5, 0): None,
        (6, 0): None,
    }

    @classmethod
    def get_x_vessel_y_obstacle_scenarios(
        cls, vessel_number: int, obstacle_number: int
    ) -> List[LogicalScenario]:
        actor_number_by_type = (vessel_number, obstacle_number)
        if cls.__scenario_cache_map[actor_number_by_type] is not None:
            return [cls.__scenario_cache_map[actor_number_by_type]]

        id_generator = IdGenerator()

        os = OSVariable(id_generator.os_id())
        ts_vessels = [
            TSVariable(id_generator.next_ts()) for _ in range(vessel_number - 1)
        ]
        obstacles = [
            StaticObstacleVariable(id_generator.next_obstacle())
            for _ in range(obstacle_number)
        ]

        actor_variables = [os] + ts_vessels + obstacles
        relation_constr_exprs = set(
            [
                OutVisOrMayNotCollide(ts1, ts2)
                for ts1, ts2 in combinations(ts_vessels, 2)
            ]
            + [OutVisOrMayNotCollide(o, ts) for o, ts in product(obstacles, ts_vessels)]
            + [AtVisAndMayCollide(non_os, os) for non_os in ts_vessels + obstacles]
        )

        cls.__scenario_cache_map[actor_number_by_type] = LogicalScenario(
            LogicalScenarioBuilder.get_initializer(
                RandomInstanceInitializer.name, actor_variables
            ),
            RelationConstrTerm(relation_constr_exprs),
            *LogicalScenarioBuilder.get_bounds(actor_variables)
        )

        return [cls.__scenario_cache_map[actor_number_by_type]]
