from __future__ import annotations

from typing import List

from concrete_level.data_parser import EvalDataParser
from visualization.evaluation_plots.eval_plot_registry import (
    build_eval_plot_figure, list_eval_plot_names)


def load_eval_plot_names(pkl_path: str) -> List[str]:
    parser = EvalDataParser()
    eval_datas = parser.load_pkl_gzip_compressed_eval_data(pkl_path)
    return list_eval_plot_names(eval_datas)


def load_eval_plot_figure(pkl_path: str, plot_name: str):
    parser = EvalDataParser()
    eval_datas = parser.load_pkl_gzip_compressed_eval_data(pkl_path)
    return build_eval_plot_figure(eval_datas, plot_name)


def main() -> None:
    from visualization.evaluation_plots.eval_plot_manager import \
        EvalPlotManager

    parser = EvalDataParser()
    eval_datas = parser.load_pkl_gzip_compressed_eval_data()
    EvalPlotManager(eval_datas)


if __name__ == "__main__":
    main()
