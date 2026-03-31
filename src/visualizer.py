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

            frame_data.append(go.Scatter(
                x=d_data["lap"].tolist(),
                y=d_data["position"].tolist(),
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
                y=pit_subset["position"].tolist(),
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
                text=f"{race_name} {season} — Position",
                font=dict(color="white", size=20),
            ),
            xaxis=dict(
                title="Lap",
                range=[0, max_lap + 1],
                color="white",
                gridcolor="#333333",
            ),
            yaxis=dict(
                title="Position",
                autorange="reversed",
                range=[0.5, num_drivers + 0.5],
                dtick=1,
                color="white",
                gridcolor="#333333",
            ),
            plot_bgcolor="#1a1a2e",
            paper_bgcolor="#16213e",
            font=dict(color="white"),
            height=900,
            legend=dict(
                bgcolor="rgba(0,0,0,0.5)",
                font=dict(color="white", size=13),
                orientation="h",
                yanchor="top",
                y=-0.08,
                xanchor="center",
                x=0.5,
                itemclick="toggle",
                itemdoubleclick="toggleothers",
                itemwidth=30,
                traceorder="normal",
            ),
            margin=dict(b=120),
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
