from typing import Dict, List, Tuple

from matplotlib import pyplot as plt

from concrete_level.models.concrete_actors import ConcreteActor
from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.models.multi_level_scenario import MultiLevelScenario
from logical_level.constraint_satisfaction.evaluation_cache import \
    EvaluationCache
from visualization.colreg_scenarios.plot_components.plot_component import \
    PlotComponent


class PrimeComponent(PlotComponent):
    def __init__(self, ax: plt.Axes, scenario: MultiLevelScenario) -> None:
        super().__init__(ax, scenario)
        self.p12_vec_graphs: Dict[Tuple[ConcreteActor, ConcreteActor], plt.Quiver] = {}
        self.p21_vec_graphs: Dict[Tuple[ConcreteActor, ConcreteActor], plt.Quiver] = {}
        self.zorder = -15

    def do_draw(self):
        eval_cache = EvaluationCache(
            self.scenario.concrete_scene.assignments(
                self.scenario.logical_scenario.actor_variables
            )
        )
        for (
            actor1,
            actor2,
        ) in self.scenario.concrete_scene.all_vessel_pair_combinations_with_obstacles:
            var1, var2 = self.scenario.to_variable(actor1), self.scenario.to_variable(
                actor2
            )
            key = (actor1, actor2)
            props = eval_cache.get_props(var1, var2)

            p12_scaled = props.p12 * 0.95
            p12_vec = self.ax.quiver(
                props.val1.x,
                props.val1.y,
                p12_scaled[0],
                p12_scaled[1],
                angles="xy",
                scale_units="xy",
                scale=1,
                color="black",
                zorder=self.zorder,
                width=0.006,
            )
            self.p12_vec_graphs[key] = p12_vec

            p21_scaled = props.p21 * 0.95
            p21_vec = self.ax.quiver(
                props.val2.x,
                props.val2.y,
                p21_scaled[0],
                p21_scaled[1],
                angles="xy",
                scale_units="xy",
                scale=1,
                color="black",
                zorder=self.zorder,
                width=0.006,
            )
            self.p21_vec_graphs[key] = p21_vec

            self.graphs += [p12_vec, p21_vec]

    def do_update(self, scene: ConcreteScene) -> List[plt.Artist]:
        eval_cache = EvaluationCache(
            scene.assignments(self.scenario.logical_scenario.actor_variables)
        )
        for (
            actor1,
            actor2,
        ) in self.scenario.concrete_scene.all_vessel_pair_combinations_with_obstacles:
            var1, var2 = self.scenario.to_variable(actor1), self.scenario.to_variable(
                actor2
            )
            key = (actor1, actor2)
            props = eval_cache.get_props(var1, var2)

            p12_scaled = props.p12 * 0.95
            self.p12_vec_graphs[key].set_offsets(props.val1.p)
            self.p12_vec_graphs[key].set_UVC(p12_scaled[0], p12_scaled[1])
            p21_scaled = props.p21 * 0.95
            self.p21_vec_graphs[key].set_offsets(props.val2.p)
            self.p21_vec_graphs[key].set_UVC(p21_scaled[0], p21_scaled[1])
        return self.graphs
