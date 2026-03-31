"""Plotly chart builder for F1 gap delta visualization."""

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go


def _detect_pit_stops(df: pd.DataFrame) -> pd.DataFrame:
    """Detect likely pit stops where lap time exceeds 120% of driver's median."""
    medians = df.groupby("driver_code")["lap_time_seconds"].median().rename("median_time")
    merged = df.merge(medians, on="driver_code")
    pit_stops = merged[merged["lap_time_seconds"] > merged["median_time"] * 1.2].copy()
    return pit_stops[["driver_code", "lap", "gap_to_leader"]]


def build_animated_chart(
    gap_df: pd.DataFrame,
    race_name: str,
    driver_info: list[dict[str, Any]],
    driver_colors: dict[str, str],
    season: int,
) -> go.Figure:
    """Build an animated Plotly gap chart with lap-by-lap reveal.

    Each frame adds one more lap, showing lines growing across the chart.
    """
    drivers = gap_df["driver_code"].unique().tolist()
    max_lap = int(gap_df["lap"].max())

    # Build driver lookup
    info_map = {}
    for d in driver_info:
        info_map[d["driver_code"]] = d

    # Map driverId to 3-letter code from results
    driver_id_to_code = {}
    for d in driver_info:
        driver_id_to_code[d.get("driver_code", "")] = d.get("driver_code", "")

    pit_stops = _detect_pit_stops(gap_df)

    # Create frames
    frames = []
    for lap in range(1, max_lap + 1):
        frame_data = []
        subset = gap_df[gap_df["lap"] <= lap]
        for driver in drivers:
            d_data = subset[subset["driver_code"] == driver]
            info = info_map.get(driver, {})
            name = info.get("driver_name", driver)
            team = info.get("team", "")
            color = driver_colors.get(driver, "#FFFFFF")

            hover_texts = []
            for _, row in d_data.iterrows():
                lap_time_row = gap_df[
                    (gap_df["driver_code"] == driver) & (gap_df["lap"] == row["lap"])
                ]
                lt = lap_time_row["lap_time_seconds"].values[0] if len(lap_time_row) > 0 else 0
                mins = int(lt // 60)
                secs = lt % 60
                hover_texts.append(
                    f"{name}<br>Team: {team}<br>Gap: +{row['gap_to_leader']:.3f}s<br>"
                    f"Lap time: {mins}:{secs:06.3f}"
                )

            frame_data.append(go.Scatter(
                x=d_data["lap"].tolist(),
                y=d_data["gap_to_leader"].tolist(),
                mode="lines",
                name=driver[:3].upper() if len(driver) > 3 else driver.upper(),
                line=dict(color=color, width=2),
                hovertext=hover_texts,
                hoverinfo="text",
            ))

        # Add pit stop markers for laps up to current
        pit_subset = pit_stops[pit_stops["lap"] <= lap]
        if not pit_subset.empty:
            frame_data.append(go.Scatter(
                x=pit_subset["lap"].tolist(),
                y=pit_subset["gap_to_leader"].tolist(),
                mode="markers",
                name="Pit Stop",
                marker=dict(symbol="triangle-down", size=8, color="#FFD700"),
                hovertext=[f"Pit stop: {r['driver_code']} Lap {r['lap']}" for _, r in pit_subset.iterrows()],
                hoverinfo="text",
                showlegend=False,
            ))

        frames.append(go.Frame(data=frame_data, name=str(lap)))

    # Initial data (lap 1)
    initial_data = frames[0].data if frames else []

    fig = go.Figure(
        data=initial_data,
        frames=frames,
        layout=go.Layout(
            title=dict(
                text=f"{race_name} {season} — Gap to Leader",
                font=dict(color="white", size=20),
            ),
            xaxis=dict(
                title="Lap",
                range=[0, max_lap + 1],
                color="white",
                gridcolor="#333333",
            ),
            yaxis=dict(
                title="Gap to Leader (seconds)",
                autorange="reversed",
                color="white",
                gridcolor="#333333",
            ),
            plot_bgcolor="#1a1a2e",
            paper_bgcolor="#16213e",
            font=dict(color="white"),
            legend=dict(
                bgcolor="rgba(0,0,0,0.5)",
                font=dict(color="white", size=10),
            ),
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                y=1.15,
                x=0.5,
                xanchor="center",
                buttons=[
                    dict(
                        label="▶ Play",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 150, "redraw": True},
                            "fromcurrent": True,
                            "transition": {"duration": 80},
                        }],
                    ),
                    dict(
                        label="⏸ Pause",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "transition": {"duration": 0},
                        }],
                    ),
                ],
            )],
            sliders=[dict(
                active=0,
                steps=[
                    dict(
                        args=[[str(lap)], {"frame": {"duration": 150, "redraw": True},
                                           "mode": "immediate",
                                           "transition": {"duration": 80}}],
                        label=str(lap),
                        method="animate",
                    )
                    for lap in range(1, max_lap + 1)
                ],
                x=0.05,
                len=0.9,
                currentvalue=dict(prefix="Lap: ", font=dict(color="white")),
                font=dict(color="white"),
            )],
        ),
    )

    return fig


def export_html(fig: go.Figure, path: str) -> str:
    """Save the Plotly figure as a standalone HTML file.

    Returns the absolute path of the saved file.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(p), include_plotlyjs=True, full_html=True)
    return str(p.resolve())
