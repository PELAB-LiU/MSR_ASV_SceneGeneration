"""Streamlit helpers for interactive Plotly figures."""

from __future__ import annotations

import io
import warnings
from typing import Optional, Union

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st
from matplotlib.figure import Figure


def matplotlib_to_plotly(fig: Figure) -> go.Figure:
    import plotly.tools as tls

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        plotly_fig = tls.mpl_to_plotly(fig)
    plotly_fig.update_layout(
        hovermode="x unified",
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return plotly_fig


def figure_to_png_bytes(fig: Figure, *, dpi: int = 150) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=dpi)
    return buffer.getvalue()


def plotly_to_html_bytes(fig: go.Figure) -> bytes:
    return fig.to_html(include_plotlyjs="cdn", full_html=True).encode("utf-8")


def render_evaluation_plot(
    png_bytes: bytes,
    plotly_fig: go.Figure,
    *,
    plot_name: str,
    download_key: Optional[str] = None,
    show_download: bool = True,
) -> None:
    """Show the original matplotlib PNG above an interactive Plotly version."""
    safe_name = plot_name.lower().replace(" ", "_")
    st.caption(f"Original figure: **{plot_name}** (matplotlib)")
    st.image(png_bytes, use_container_width=True)
    st.caption(
        f"Interactive version: **{plot_name}** "
        "(zoom, pan, hover; toggle traces in the legend)."
    )
    st.plotly_chart(plotly_fig, use_container_width=True)

    if show_download:
        key_base = download_key or f"dl_eval_{safe_name}"
        col_png, col_html = st.columns(2)
        with col_png:
            st.download_button(
                "Download PNG",
                data=png_bytes,
                file_name=f"{safe_name}.png",
                mime="image/png",
                key=f"{key_base}_png",
            )
        with col_html:
            st.download_button(
                "Download HTML",
                data=plotly_to_html_bytes(plotly_fig),
                file_name=f"{safe_name}.html",
                mime="text/html",
                key=f"{key_base}_html",
            )


def render_figure(
    fig: Union[Figure, go.Figure],
    *,
    caption: Optional[str] = None,
    download_name: str = "plot",
    download_key: Optional[str] = None,
    show_download: bool = True,
    close_matplotlib: bool = True,
) -> None:
    """Render an interactive Plotly chart (from Plotly or converted matplotlib)."""
    if caption:
        st.caption(caption)

    source_figure: Optional[Figure] = None
    if isinstance(fig, go.Figure):
        plotly_fig = fig
    else:
        source_figure = fig
        plotly_fig = matplotlib_to_plotly(fig)

    st.plotly_chart(plotly_fig, use_container_width=True)

    if show_download:
        key_base = download_key or f"dl_plot_{download_name}"
        col_png, col_html = st.columns(2)
        with col_png:
            if source_figure is not None:
                st.download_button(
                    "Download PNG",
                    data=figure_to_png_bytes(source_figure),
                    file_name=f"{download_name}.png",
                    mime="image/png",
                    key=f"{key_base}_png",
                )
        with col_html:
            st.download_button(
                "Download HTML",
                data=plotly_to_html_bytes(plotly_fig),
                file_name=f"{download_name}.html",
                mime="text/html",
                key=f"{key_base}_html",
            )

    if close_matplotlib and source_figure is not None:
        plt.close(source_figure)
