"""Interactive Plotly COLREG scene preview for the artifact UI."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from concrete_level.models.concrete_scene import ConcreteScene
from global_config import GlobalConfig
from utils.colors import colors


def build_scene_plotly_figure(concrete_scene: ConcreteScene) -> go.Figure:
    fig = go.Figure()

    for actor, state in concrete_scene.items():
        color = colors[actor.id]
        radius = actor.radius
        position = state.p
        heading_deg = float(np.degrees(state.heading))
        speed_kn = float(state.speed / GlobalConfig.KNOT_TO_MS_CONVERSION)

        fig.add_shape(
            type="circle",
            xref="x",
            yref="y",
            x0=position[0] - radius,
            y0=position[1] - radius,
            x1=position[0] + radius,
            y1=position[1] + radius,
            line=dict(color=color, width=1, dash="dash"),
            fillcolor="rgba(0,0,0,0)",
        )
        fig.add_trace(
            go.Scatter(
                x=[position[0], position[0] + state.v[0]],
                y=[position[1], position[1] + state.v[1]],
                mode="lines",
                line=dict(color=color, width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[position[0]],
                y=[position[1]],
                mode="markers",
                name=str(actor),
                marker=dict(color=color, size=11, line=dict(width=1, color="white")),
                hovertemplate=(
                    f"{actor}<br>"
                    f"position: ({position[0]:.1f}, {position[1]:.1f}) m<br>"
                    f"radius: {radius:.1f} m<br>"
                    f"heading: {heading_deg:.1f}°<br>"
                    f"speed: {speed_kn:.1f} kn<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title="COLREG scene preview",
        xaxis_title="X Position (m)",
        yaxis_title="Y Position (m)",
        yaxis_scaleanchor="x",
        yaxis_scaleratio=1,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="closest",
        dragmode="zoom",
    )
    return fig
