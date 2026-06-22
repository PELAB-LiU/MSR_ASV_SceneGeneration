from abc import ABC, abstractmethod
from typing import List

from matplotlib import pyplot as plt

from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.models.multi_level_scenario import MultiLevelScenario


class PlotComponent(ABC):
    def __init__(self, ax: plt.Axes, scenario: MultiLevelScenario) -> None:
        self.ax = ax
        self.scenario = scenario
        self.graphs: List[plt.Artist] = []
        self.zorder = 0

    def draw(self):
        self.do_draw()

    @abstractmethod
    def do_draw(self):
        pass

    def update(self, scene: ConcreteScene) -> List[plt.Artist]:
        return self.do_update(scene)

    @abstractmethod
    def do_update(self, scene: ConcreteScene) -> List[plt.Artist]:
        pass

    def reset(self) -> List[plt.Artist]:
        return self.update(self.scenario.concrete_scene)
