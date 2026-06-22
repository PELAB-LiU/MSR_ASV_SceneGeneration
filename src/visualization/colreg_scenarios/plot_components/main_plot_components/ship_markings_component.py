from typing import Dict, List

import numpy as np
from matplotlib import pyplot as plt

from concrete_level.models.concrete_actors import ConcreteActor
from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.models.multi_level_scenario import MultiLevelScenario
from global_config import GlobalConfig
from utils.colors import colors
from visualization.colreg_scenarios.plot_components.plot_component import \
    PlotComponent


class ShipMarkingsComponent(PlotComponent):
    STATIC_ZOOM = 100
    DYNAMIC_ZOOM = 50

    def __init__(self, ax: plt.Axes, scenario: MultiLevelScenario) -> None:
        super().__init__(ax, scenario)
        self.radius_graphs: Dict[ConcreteActor, plt.Circle] = {}
        self.velocity_graphs: Dict[ConcreteActor, plt.Quiver] = {}
        self.ship_dot_graphs: Dict[ConcreteActor, plt.PathCollection] = {}
        self.zorder = 0

    def do_draw(self):
        for actor, state in self.scenario.concrete_scene.items():
            # Plot the positions and radius as circles
            radius_circle = plt.Circle(
                state.p,
                actor.radius,
                color=colors[actor.id],
                fill=False,
                linestyle="--",
                zorder=self.zorder,
            )
            self.ax.add_artist(radius_circle)
            self.radius_graphs[actor] = radius_circle

            # Plot the positions
            dot_label = f"{actor}\; p: ({state.p[0]:.1f}, {state.p[1]:.1f}), r: {actor.radius:.1f} m"
            ship_dot = self.ax.scatter(
                state.p[0],
                state.p[1],
                color=colors[actor.id],
                s=self.DYNAMIC_ZOOM,
                label=rf"${dot_label}$",
                zorder=self.zorder,
            )
            self.ship_dot_graphs[actor] = ship_dot

            angle = f"h: {np.degrees(state.heading):.1f}^\circ"
            speed = f"sp: {(state.speed / GlobalConfig.KNOT_TO_MS_CONVERSION):.1f} kn"
            velocity_label = f"{actor}\; {angle}, {speed}"
            # Plot the velocity vector with their actual lengths
            ship_vel = self.ax.quiver(
                state.p[0],
                state.p[1],
                state.v[0],
                state.v[1],
                angles="xy",
                scale_units="xy",
                scale=1,
                color=colors[actor.id],
                label=rf"${velocity_label}$",
                zorder=self.zorder - 10,
            )
            self.velocity_graphs[actor] = ship_vel

            self.graphs += [radius_circle, ship_vel, ship_dot]

    def do_update(self, scene: ConcreteScene) -> List[plt.Artist]:
        for actor, state in scene.items():
            self.radius_graphs[actor].set_center(state.p)
            self.radius_graphs[actor].set_radius(actor.radius)
            self.ship_dot_graphs[actor].set_offsets([state.p])
            self.velocity_graphs[actor].set_offsets(state.p)
            self.velocity_graphs[actor].set_UVC(state.v[0], state.v[1])
        return self.graphs
