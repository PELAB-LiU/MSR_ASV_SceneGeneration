"""Build evaluation plot figures without Tkinter."""

from __future__ import annotations

from typing import Dict, List

import matplotlib.pyplot as plt

from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from visualization.evaluation_plots.coverage_evolution_plot import \
    RelevantCoverageEvolutionPlot
from visualization.evaluation_plots.coverage_plot import RelevantCoveragePlot
from visualization.evaluation_plots.rare_scenario_plot import RareScenarioPlot
from visualization.evaluation_plots.time_per_eq_class_plot import (
    TimePerEqvClassForValidPlot, TimePerEqvClassPlot, TimePerScenePlot)
from visualization.evaluation_plots.time_to_full_coverage_plot import \
    RelevantTimeToFullCoveragePlot
from visualization.plotting_utils import EvalPlot


def get_eval_plot_registry(
    eval_datas: List[EvaluationData],
) -> Dict[str, type]:
    return {
        "Relevant Coverage Evolution": RelevantCoverageEvolutionPlot,
        "Relevant Coverage": RelevantCoveragePlot,
        "Time to 100% Coverage": RelevantTimeToFullCoveragePlot,
        "Time Per Eqv Class": TimePerEqvClassPlot,
        "Time Per Eqv Class For Valid Scenes": TimePerEqvClassForValidPlot,
        "Time Per Scene": TimePerScenePlot,
        "Rare Scenario Plot": RareScenarioPlot,
    }


def build_eval_plot_figure(
    eval_datas: List[EvaluationData],
    plot_name: str,
) -> plt.Figure:
    registry = get_eval_plot_registry(eval_datas)
    if plot_name not in registry:
        raise ValueError(f"Unknown plot: {plot_name}")
    plot_class = registry[plot_name]
    kwargs = {"eval_datas": eval_datas, "is_all": True, "is_algo": False}
    if plot_class in {
        TimePerEqvClassPlot,
        TimePerEqvClassForValidPlot,
        TimePerScenePlot,
    }:
        plot: EvalPlot = plot_class(**kwargs)
    else:
        plot = plot_class(eval_datas=eval_datas)
    return plot.fig


def list_eval_plot_names(eval_datas: List[EvaluationData]) -> List[str]:
    return list(get_eval_plot_registry(eval_datas).keys())
