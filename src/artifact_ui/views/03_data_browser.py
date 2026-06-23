import streamlit as st

from artifact_ui.components.dataset_state import require_active_dataset
from artifact_ui.components.eval_data_loader import (load_eval_dataframe_cached,
                                                     render_dataset_loader)
from artifact_ui.components.plot_renderer import (figure_to_png_bytes,
                                                  render_evaluation_plot)

st.title("Scenario Browser")

pkl_path = require_active_dataset()
eval_datas = render_dataset_loader(str(pkl_path), key_prefix="scenario_browser")
if eval_datas is None:
    st.stop()

df = load_eval_dataframe_cached(str(pkl_path))
st.dataframe(df, use_container_width=True)

selected = st.number_input(
    "Row index for scene preview",
    min_value=0,
    max_value=max(len(eval_datas) - 1, 0),
    value=0,
)

if eval_datas and st.button("Render COLREG scene"):
    from visualization.colreg_scenarios.scene_figure_builder import \
        build_scene_figure
    from visualization.colreg_scenarios.scene_plotly_builder import \
        build_scene_plotly_figure

    scene = eval_datas[int(selected)].best_scene
    if scene is None:
        st.error("Selected record has no best_scene.")
    else:
        with st.status("Building COLREG scene visualizations…", expanded=False):
            mpl_fig = build_scene_figure(scene)
            plotly_fig = build_scene_plotly_figure(scene)
        st.session_state.colreg_scene_index = int(selected)
        st.session_state.colreg_scene_png = figure_to_png_bytes(mpl_fig)
        st.session_state.colreg_scene_plotly = plotly_fig

preview_index = st.session_state.get("colreg_scene_index")
cached_png = st.session_state.get("colreg_scene_png")
cached_plotly = st.session_state.get("colreg_scene_plotly")
if (
    eval_datas
    and preview_index is not None
    and cached_png is not None
    and cached_plotly is not None
):
    if preview_index < 0 or preview_index >= len(eval_datas):
        st.session_state.pop("colreg_scene_index", None)
        st.session_state.pop("colreg_scene_png", None)
        st.session_state.pop("colreg_scene_plotly", None)
    else:
        plot_label = f"COLREG scene (row {preview_index})"
        if preview_index != int(selected):
            st.caption(
                f"Showing **{plot_label}**. Change the row index and click "
                "**Render COLREG scene** to update."
            )
        render_evaluation_plot(
            cached_png,
            cached_plotly,
            plot_name=plot_label,
            download_key="dl_colreg_scene",
        )
