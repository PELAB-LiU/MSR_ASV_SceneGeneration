from typing import Dict, List, Tuple

from matplotlib import pyplot as plt

from concrete_level.models.concrete_actors import ConcreteActor
from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.models.multi_level_scenario import MultiLevelScenario
from global_config import GlobalConfig
from logical_level.constraint_satisfaction.evaluation_cache import \
    EvaluationCache
from visualization.colreg_scenarios.plot_components.plot_component import \
    PlotComponent


class DistanceComponent(PlotComponent):
    def __init__(self, ax: plt.Axes, scenario: MultiLevelScenario) -> None:
        super().__init__(ax, scenario)
        self.text_graphs: Dict[Tuple[ConcreteActor, ConcreteActor], plt.Text] = {}
        self.line_graphs: Dict[Tuple[ConcreteActor, ConcreteActor], plt.Line2D] = {}
        self.graphs_by_rels = [self.text_graphs, self.line_graphs]
        self.zorder = -3

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

            if props.o_distance < 1000:
                text_str = f"{props.o_distance:.0f} m"
            else:
                text_str = (
                    f"{props.o_distance / GlobalConfig.N_MILE_TO_M_CONVERSION:.1f} NM"
                )
            text = self.ax.text(
                props.val1.p[0] + props.p12[0] / 2,
                props.val1.p[1] + props.p12[1] / 2,
                text_str,
                fontsize=10,
                color="black",
                zorder=self.zorder + 10,
            )
            self.text_graphs[key] = text

            (line,) = self.ax.plot(
                [props.val1.x, props.val2.x],
                [props.val1.y, props.val2.y],
                color="black",
                linewidth=0.8,
                zorder=self.zorder,
            )
            self.line_graphs[key] = line

            self.graphs += [text, line]

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

            self.text_graphs[key].set_position(
                (props.val1.p[0] + props.p12[0] / 2, props.val1.p[1] + props.p12[1] / 2)
            )
            if props.o_distance < 1000:
                text_str = f"{props.o_distance:.0f} m"
            else:
                text_str = (
                    f"{props.o_distance / GlobalConfig.N_MILE_TO_M_CONVERSION:.1f} NM"
                )
            self.text_graphs[key].set_text(text_str)

            self.line_graphs[key].set_data(
                [props.val1.x, props.val2.x], [props.val1.y, props.val2.y]
            )
        return self.graphs
