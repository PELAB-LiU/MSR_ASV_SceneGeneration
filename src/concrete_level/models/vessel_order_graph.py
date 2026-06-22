from typing import Dict, List, Tuple

from concrete_level.models.concrete_actors import ConcreteVessel
from concrete_level.models.multi_level_scenario import MultiLevelScenario
from functional_level.metamodels.functional_object import FuncObject
from functional_level.metamodels.functional_scenario import FunctionalScenario


class VesselNode:
    def __init__(self, vessel: ConcreteVessel) -> None:
        self.vessel = vessel
        self.relations: List[Tuple[ConcreteVessel, ConcreteVessel]] = []
        self.in_degree = 0
        self.out_degree = 0

    def __eq__(self, value: object) -> bool:
        return isinstance(value, VesselNode) and self.vessel == value.vessel

    def __repr__(self) -> str:
        return self.vessel.__repr__()


class VesselOrderGraph:
    def __init__(self, scenario: MultiLevelScenario):
        self.nodes: Dict[ConcreteVessel, VesselNode] = {}
        self.in_degree: Dict[VesselNode, int] = {}
        self.out_degree: Dict[VesselNode, int] = {}
        relations = [
            (scenario.to_concrete_vessel(obj1), scenario.to_concrete_vessel(obj2))
            for obj1, obj2 in scenario.functional_scenario.all_colregs_relation_pairs
        ]

        for rel in relations:
            self.add_nodes(rel)
        for rel in relations:
            self.add_edge(rel)

    def add_nodes(self, rel: Tuple[ConcreteVessel, ConcreteVessel]):
        node1 = VesselNode(rel[0])
        if rel[0] not in self.nodes:
            self.nodes[rel[0]] = node1
        node2 = VesselNode(rel[1])
        if rel[1] not in self.nodes:
            self.nodes[rel[1]] = node2

    def add_edge(self, rel: Tuple[ConcreteVessel, ConcreteVessel]):
        node1 = self.nodes[rel[0]]
        node2 = self.nodes[rel[1]]
        node1.relations.append(rel)
        node1.out_degree += 1
        node2.in_degree += 1

    def sort(self) -> list[VesselNode]:
        return sorted(
            self.nodes.values(), key=lambda node: node.out_degree - node.in_degree
        )
