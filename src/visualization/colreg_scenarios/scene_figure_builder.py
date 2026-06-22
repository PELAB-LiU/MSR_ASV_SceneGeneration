"""Build static COLREG scene figures without Tkinter."""

from __future__ import annotations

import matplotlib.pyplot as plt

from concrete_level.models.concrete_scene import ConcreteScene
from concrete_level.models.trajectory_manager import TrajectoryManager


def _stop_scenario_animation(scenario_plot) -> None:
    animation = getattr(scenario_plot, "animation", None)
    if animation is None:
        return
    func_animation = getattr(animation, "anim", None)
    if func_animation is not None and hasattr(func_animation, "event_source"):
        func_animation.event_source.stop()


def build_scene_figure(concrete_scene: ConcreteScene) -> plt.Figure:
    from visualization.colreg_scenarios.scenario_plot import ScenarioPlot

    trajectory_manager = TrajectoryManager(concrete_scene)
    scenario_plot = ScenarioPlot(trajectory_manager)
    _stop_scenario_animation(scenario_plot)
    return scenario_plot.fig


def build_trajectory_figure(trajectory_manager: TrajectoryManager) -> plt.Figure:
    from visualization.colreg_scenarios.scenario_plot import ScenarioPlot

    scenario_plot = ScenarioPlot(trajectory_manager)
    _stop_scenario_animation(scenario_plot)
    return scenario_plot.fig
