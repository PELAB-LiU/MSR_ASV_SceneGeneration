"""Build evaluation plot figures without Tkinter."""

from __future__ import annotations

from typing import Dict, List

import matplotlib.pyplot as plt

from logical_level.constraint_satisfaction.evaluation_data import \
    EvaluationData
from visualization.evaluation_plots.coverage_evolution_plot import \
    RelevantCoverageEvolutionPlot
from visualization.evaluation_plots.coverage_plot import RelevantCoveragePlot
from visualization.evaluation_plots.time_per_eq_class_plot import \
    TimePerEqvClassPlot
from visualization.evaluation_plots.time_to_full_coverage_plot import \
    RelevantTimeToFullCoveragePlot
from visualization.plotting_utils import EvalPlot

EVAL_PLOT_DESCRIPTIONS: Dict[str, str] = {
    "Relevant Coverage Evolution": (
        "Cumulative **relevant FEC coverage** (%) over wall-clock evaluation time for "
        "each paper approach, vessel count, and random seed. Shows how quickly each "
        "configuration discovers new functionally relevant equivalence classes."
    ),
    "Relevant Coverage": (
        "Final **relevant FEC coverage** (%) per approach and vessel count after all "
        "scheduled scenarios finish. Bars aggregate seeds; asterisks mark statistically "
        "significant pairwise differences (Mann–Whitney U with effect size)."
    ),
    "Time to 100% Coverage": (
        "Wall-clock time until **100% of relevant FECs** are covered for each approach "
        "and vessel count. Only runs that reach full coverage contribute; compares how "
        "long complete assurance-suite generation takes across configurations."
    ),
    "Time Per Eqv Class": (
        "Mean evaluation time per **newly covered relevant equivalence class** "
        "(graph-shape hash), averaged over seeds. Lower values indicate faster discovery "
        "of distinct functional scenarios; includes statistical comparison markers."
    ),
}


def get_eval_plot_registry(
    eval_datas: List[EvaluationData],
) -> Dict[str, type]:
    return {
        "Relevant Coverage Evolution": RelevantCoverageEvolutionPlot,
        "Relevant Coverage": RelevantCoveragePlot,
        "Time to 100% Coverage": RelevantTimeToFullCoveragePlot,
        "Time Per Eqv Class": TimePerEqvClassPlot,
    }


def get_eval_plot_description(plot_name: str) -> str:
    return EVAL_PLOT_DESCRIPTIONS.get(
        plot_name,
        "Paper-style figure generated from the loaded evaluation measurements.",
    )


def build_eval_plot_figure(
    eval_datas: List[EvaluationData],
    plot_name: str,
) -> plt.Figure:
    registry = get_eval_plot_registry(eval_datas)
    if plot_name not in registry:
        raise ValueError(f"Unknown plot: {plot_name}")
    plot_class = registry[plot_name]
    kwargs = {"eval_datas": eval_datas, "is_all": True, "is_algo": False}
    if plot_class is TimePerEqvClassPlot:
        plot: EvalPlot = plot_class(**kwargs)
    else:
        plot = plot_class(eval_datas=eval_datas)
    return plot.fig


def list_eval_plot_names(eval_datas: List[EvaluationData]) -> List[str]:
    return list(get_eval_plot_registry(eval_datas).keys())
