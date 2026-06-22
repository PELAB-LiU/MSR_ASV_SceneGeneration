from typing import Dict, List, Tuple

import numpy as np
from matplotlib import pyplot as plt

from concrete_level.models.concrete_actors import ConcreteActor
from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.models.multi_level_scenario import MultiLevelScenario
from logical_level.constraint_satisfaction.evaluation_cache import \
    EvaluationCache
from visualization.colreg_scenarios.plot_components.plot_component import \
    PlotComponent


class AdditionalVOConeComponent(PlotComponent):
    def __init__(self, ax: plt.Axes, scenario: MultiLevelScenario) -> None:
        super().__init__(ax, scenario)
        self.circle_graphs: Dict[Tuple[ConcreteActor, ConcreteActor], plt.Circle] = {}
        self.line1_graphs: Dict[Tuple[ConcreteActor, ConcreteActor], plt.Line2D] = {}
        self.line2_graphs: Dict[Tuple[ConcreteActor, ConcreteActor], plt.Line2D] = {}
        self.graphs_by_rels = [self.circle_graphs, self.line1_graphs, self.line2_graphs]
        self.zorder = -2

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
            vo_circle = plt.Circle(
                props.val2.p,
                props.safety_dist,
                color="black",
                fill=False,
                linestyle="--",
                linewidth=0.7,
                zorder=self.zorder,
            )
            self.ax.add_artist(vo_circle)
            self.circle_graphs[key] = vo_circle
            # Calculate the angles of the cone
            angle_rel = np.arctan2(props.p12[1], props.p12[0])
            sin_half_cone_theta = np.clip(props.safety_dist / props.o_distance, -1, 1)
            angle_half_cone = abs(np.arcsin(sin_half_cone_theta))  # [0, pi/2]
            angle1 = angle_rel + angle_half_cone
            angle2 = angle_rel - angle_half_cone

            # Plot the velocity obstacle cone
            cone1 = (
                props.val1.p
                + np.array([np.cos(angle1), np.sin(angle1)]) * props.o_distance
            )
            cone2 = (
                props.val1.p
                + np.array([np.cos(angle2), np.sin(angle2)]) * props.o_distance
            )

            (line1,) = self.ax.plot(
                [props.val1.x, cone1[0]],
                [props.val1.y, cone1[1]],
                "k--",
                linewidth=0.7,
                zorder=self.zorder,
            )
            self.line1_graphs[key] = line1

            (line2,) = self.ax.plot(
                [props.val1.x, cone2[0]],
                [props.val1.y, cone2[1]],
                "k--",
                linewidth=0.7,
                zorder=self.zorder,
            )
            self.line2_graphs[key] = line2
            self.graphs += [vo_circle, line1, line2]

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
            self.circle_graphs[key].set_center(props.val2.p)
            self.circle_graphs[key].set_radius(props.safety_dist)
            # Calculate the angles of the cone
            # Calculate the angles of the cone
            angle_rel = np.arctan2(props.p12[1], props.p12[0])

            # Calculate the angles of the cone
            angle_rel = np.arctan2(props.p12[1], props.p12[0])
            sin_half_cone_theta = np.clip(props.safety_dist / props.o_distance, -1, 1)
            angle_half_cone = abs(np.arcsin(sin_half_cone_theta))  # [0, pi/2]
            angle1 = angle_rel + angle_half_cone
            angle2 = angle_rel - angle_half_cone

            # Plot the velocity obstacle cone
            cone1 = (
                props.val1.p
                + np.array([np.cos(angle1), np.sin(angle1)]) * props.o_distance
            )
            cone2 = (
                props.val1.p
                + np.array([np.cos(angle2), np.sin(angle2)]) * props.o_distance
            )

            self.line1_graphs[key].set_data(
                [props.val1.x, cone1[0]], [props.val1.y, cone1[1]]
            )
            self.line2_graphs[key].set_data(
                [props.val1.x, cone2[0]], [props.val1.y, cone2[1]]
            )
        return self.graphs
