import streamlit as st

from artifact_ui.components.dataset_state import require_active_dataset
from artifact_ui.components.eval_data_loader import (render_dataset_loader,
                                                     render_plot_generation_log,
                                                     with_plot_generation_progress)
from artifact_ui.components.plot_renderer import (build_eval_plot_figure,
                                                  figure_to_png_bytes,
                                                  get_eval_plot_description,
                                                  list_eval_plot_names,
                                                  matplotlib_to_plotly,
                                                  render_evaluation_plot)

st.title("Evaluation Plots")

pkl_path = require_active_dataset()
eval_datas = render_dataset_loader(str(pkl_path), key_prefix="eval_plots")
if eval_datas is None:
    st.stop()

plot_names = list_eval_plot_names(eval_datas)
plot_name = st.selectbox("Plot type", plot_names)
st.markdown(get_eval_plot_description(plot_name))

if st.button("Generate plot"):
    mpl_fig = with_plot_generation_progress(
        plot_name,
        lambda: build_eval_plot_figure(eval_datas, plot_name),
    )
    st.session_state.eval_plot_figure = matplotlib_to_plotly(mpl_fig)
    st.session_state.eval_plot_png = figure_to_png_bytes(mpl_fig)
    st.session_state.eval_plot_name = plot_name

cached_name = st.session_state.get("eval_plot_name")
cached_png = st.session_state.get("eval_plot_png")
cached_fig = st.session_state.get("eval_plot_figure")
cached_log = st.session_state.get("eval_plot_generation_log")
log_shown_in_status = st.session_state.pop("eval_plot_log_in_status", False)
if cached_fig is not None and cached_png is not None and cached_name is not None:
    if cached_log and not log_shown_in_status:
        render_plot_generation_log(
            cached_log,
            expanded=False,
            key="plot_generation_log_cached",
        )
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
