import matplotlib.pyplot as plt
import streamlit as st

from artifact_ui.components.dataset_state import require_active_dataset
from artifact_ui.components.eval_data_loader import (
    load_eval_datas_cached, with_plot_generation_progress)
from artifact_ui.components.plot_renderer import (figure_to_png_bytes,
                                                  matplotlib_to_plotly,
                                                  render_evaluation_plot)
from visualization.evaluation_plots.eval_plot_registry import (
    build_eval_plot_figure, list_eval_plot_names)

st.title("Evaluation Plots")

pkl_path = require_active_dataset()

eval_datas = load_eval_datas_cached(pkl_path=str(pkl_path))
plot_names = list_eval_plot_names(eval_datas)
plot_name = st.selectbox("Plot type", plot_names)

if st.button("Generate plot"):
    mpl_fig = with_plot_generation_progress(
        plot_name,
        lambda: build_eval_plot_figure(eval_datas, plot_name),
    )
    st.session_state.eval_plot_png = figure_to_png_bytes(mpl_fig)
    st.session_state.eval_plot_figure = matplotlib_to_plotly(mpl_fig)
    st.session_state.eval_plot_name = plot_name
    plt.close(mpl_fig)

cached_name = st.session_state.get("eval_plot_name")
cached_png = st.session_state.get("eval_plot_png")
cached_fig = st.session_state.get("eval_plot_figure")
if cached_fig is not None and cached_png is not None and cached_name is not None:
    if cached_name != plot_name:
        st.caption(
            f"Showing **{cached_name}**. Select another plot type and click "
            "**Generate plot** to replace it."
        )
    safe_name = cached_name.lower().replace(" ", "_")
    render_evaluation_plot(
        cached_png,
        cached_fig,
        plot_name=cached_name,
        download_key=f"dl_{safe_name}",
    )
