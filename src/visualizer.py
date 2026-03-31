"""Plotly chart builder for F1 gap delta visualization."""

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go


def _detect_pit_stops(df: pd.DataFrame) -> pd.DataFrame:
    """Detect likely pit stops where lap time exceeds 120% of driver's median.

    Only marks the first lap of consecutive slow sequences per driver,
    filtering out safety car periods where most drivers are slow together.
    """
    medians = df.groupby("driver_code")["lap_time_seconds"].median().rename("median_time")
    merged = df.merge(medians, on="driver_code")
    slow = merged[merged["lap_time_seconds"] > merged["median_time"] * 1.2].copy()

    # Filter out laps where most of the grid is slow (safety car)
    drivers_per_lap = df.groupby("lap")["driver_code"].nunique()
    slow_per_lap = slow.groupby("lap")["driver_code"].nunique()
    sc_laps = set()
    for lap, count in slow_per_lap.items():
        total = drivers_per_lap.get(lap, 1)
        if count / total > 0.5:
            sc_laps.add(lap)
    slow = slow[~slow["lap"].isin(sc_laps)]

    # Keep only the first lap of consecutive slow sequences per driver
    rows = []
    for driver, group in slow.sort_values("lap").groupby("driver_code"):
        laps = group["lap"].tolist()
        for i, lap in enumerate(laps):
            if i == 0 or lap > laps[i - 1] + 1:
                rows.append(group[group["lap"] == lap].iloc[0])

    if not rows:
        return pd.DataFrame(columns=["driver_code", "lap", "position"])
    return pd.DataFrame(rows)[["driver_code", "lap", "position"]]


def build_animated_chart(
    gap_df: pd.DataFrame,
    race_name: str,
    driver_info: list[dict[str, Any]],
    driver_colors: dict[str, str],
    season: int,
) -> go.Figure:
    """Build an animated Plotly position chart with lap-by-lap reveal.

    Each frame adds one more lap, showing lines growing across the chart.
    """
    drivers = gap_df["driver_code"].unique().tolist()
    max_lap = int(gap_df["lap"].max())
    num_drivers = len(drivers)

    # Build driver lookup
    info_map = {}
    for d in driver_info:
        info_map[d["driver_code"]] = d

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
                    f"{name}<br>Team: {team}<br>Position: P{int(row['position'])}<br>"
                    f"Lap time: {mins}:{secs:06.3f}"
                )

            driver_label = driver[:3].upper() if len(driver) > 3 else driver.upper()
            
            # 1) The main line trace
            frame_data.append(go.Scatter(
                x=d_data["lap"].tolist(),
                y=d_data["position"].tolist(),
                mode="lines",
                name=driver_label,
                line=dict(color=color, width=3),
                hovertext=hover_texts,
                hoverinfo="text",
                legendgroup=driver,
                showlegend=True,
            ))

            # 2) A separate 1-point trace just for the label to avoid flicker
            x_last = [d_data["lap"].iloc[-1]] if not d_data.empty else []
            y_last = [d_data["position"].iloc[-1]] if not d_data.empty else []
            frame_data.append(go.Scatter(
                x=x_last,
                y=y_last,
                mode="text",
                name=f"{driver_label}_label",
                text=[driver_label] if not d_data.empty else [],
                textposition="middle right",
                textfont=dict(color=color, size=14, family="Titillium Web, Arial, sans-serif", weight="bold"),
                hoverinfo="skip",
                legendgroup=driver,
                showlegend=False,
            ))

            # 3) Pit stop markers assigned to the specific driver's legend group
            pit_driver_subset = pit_stops[(pit_stops["lap"] <= lap) & (pit_stops["driver_code"] == driver)]
            
            # Add explicit IDs so Plotly tracks the markers instead of interpolating them
            pit_ids = [f"{r['driver_code']}_{r['lap']}" for _, r in pit_driver_subset.iterrows()] if not pit_driver_subset.empty else []
            
            frame_data.append(go.Scatter(
                x=pit_driver_subset["lap"].tolist() if not pit_driver_subset.empty else [],
                y=pit_driver_subset["position"].tolist() if not pit_driver_subset.empty else [],
                ids=pit_ids,
                mode="markers",
                name=f"{driver_label}_pit",
                marker=dict(symbol="triangle-down", size=8, color="#FFD700", line=dict(color="black", width=1)),
                hovertext=[f"Pit stop: {r['driver_code']} Lap {r['lap']}" for _, r in pit_driver_subset.iterrows()] if not pit_driver_subset.empty else [],
                hoverinfo="text",
                legendgroup=driver,
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
                text=f"<b>{race_name} {season} <span style='color:#E10600'>|</span> Lap Position</b>",
                font=dict(color="white", size=24, family="Titillium Web, Arial, sans-serif"),
                x=0.02,
                y=0.98,
            ),
            xaxis=dict(
                title="<b>LAP NUMBER</b>",
                range=[0, max_lap + 2],  # Extra space for text labels
                color="white",
                gridcolor="#2b2b36",
                showgrid=True,
                zeroline=False,
                tickfont=dict(family="Titillium Web, Arial, sans-serif"),
                titlefont=dict(family="Titillium Web, Arial, sans-serif", size=14),
            ),
            yaxis=dict(
                title="<b>POSITION</b>",
                autorange="reversed",
                range=[0.5, num_drivers + 0.5],
                dtick=1,
                color="white",
                gridcolor="#2b2b36",
                showgrid=True,
                zeroline=False,
                tickfont=dict(family="Titillium Web, Arial, sans-serif"),
                titlefont=dict(family="Titillium Web, Arial, sans-serif", size=14),
            ),
            plot_bgcolor="#15151E", # F1 TV Telemetry Dark
            paper_bgcolor="#15151E",
            font=dict(color="white", family="Titillium Web, Arial, sans-serif"),
            height=900,
            hoverlabel=dict(
                bgcolor="#15151E",
                font_size=14,
                font_family="Titillium Web, Arial, sans-serif",
                bordercolor="#E10600",
            ),
            legend=dict(
                title=dict(
                    text="<b>DRIVERS</b><br><span style='font-size:13px; color:#A0A0A0;'>(Click to toggle)</span>", 
                    font=dict(color="white", size=18)
                ),
                bgcolor="rgba(21, 21, 30, 0.8)",
                bordercolor="#E10600",
                borderwidth=2,
                font=dict(color="white", size=15, family="Titillium Web, Arial, sans-serif"),
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02,
                itemclick="toggle",
                itemdoubleclick="toggleothers",
                traceorder="normal",
            ),
            margin=dict(l=60, r=160, t=100, b=120),
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                direction="right",
                y=-0.12,
                x=0.08,
                xanchor="right",
                yanchor="top",
                pad={"r": 10, "t": 0, "l": 0, "b": 0},
                buttons=[
                    dict(
                        label="<b>▶  PLAY</b>",
                        method="animate",
                        args=[None, {
                            "frame": {"duration": 150, "redraw": True},
                            "fromcurrent": True,
                            "transition": {"duration": 80},
                        }],
                    ),
                    dict(
                        label="<b>⏸  PAUSE</b>",
                        method="animate",
                        args=[[None], {
                            "frame": {"duration": 0, "redraw": False},
                            "mode": "immediate",
                            "transition": {"duration": 0},
                        }],
                    ),
                ],
                bgcolor="rgba(21, 21, 30, 0.8)",
                font=dict(color="#E10600", family="Titillium Web, Arial, sans-serif", size=14),
                bordercolor="#E10600",
                borderwidth=2,
            )],
            sliders=[dict(
                active=0,
                y=-0.12,
                yanchor="top",
                xanchor="left",
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
                x=0.1,
                len=0.9,
                currentvalue=dict(prefix="LAP: ", font=dict(color="#E10600", family="Titillium Web, Arial, sans-serif", size=16)),
                font=dict(color="white", family="Titillium Web, Arial, sans-serif"),
                bgcolor="#2b2b36",
                bordercolor="#E10600",
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
    
    # Write the figure to HTML. We disable auto_play so it doesn't run infinitely automatically
    # We also embed plotly.js to make it entirely standalone
    fig.write_html(
        str(p), 
        include_plotlyjs="cdn", # Use CDN to make file size much smaller (around 3MB instead of 10MB+)
        full_html=True,
        auto_play=False
    )
    return str(p.resolve())
