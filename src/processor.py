"""Gap delta computation logic for F1 lap time data."""

from typing import Any

import pandas as pd

# Real F1 team colors (2023/2024 season)
TEAM_COLORS: dict[str, str] = {
    "Red Bull": "#3671C6",
    "Mercedes": "#6CD3BF",
    "Ferrari": "#F91536",
    "McLaren": "#FF8000",
    "Aston Martin": "#358C75",
    "Alpine F1 Team": "#2293D1",
    "Williams": "#64C4FF",
    "AlphaTauri": "#5E8FAA",
    "RB F1 Team": "#6692FF",
    "Alfa Romeo": "#C92D4B",
    "Haas F1 Team": "#B6BABD",
    "Racing Point": "#F596C8",
    "Renault": "#FFF500",
    "Toro Rosso": "#469BFF",
    "Force India": "#F596C8",
    "Sauber": "#52E252",
    "Kick Sauber": "#52E252",
}

FALLBACK_PALETTE = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
    "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9",
    "#F8C471", "#82E0AA", "#F1948A", "#AED6F1", "#D7BDE2",
    "#A3E4D7", "#FAD7A0", "#A9CCE3", "#D5F5E3", "#FADBD8",
]


def parse_lap_times(raw_json: dict[str, Any]) -> pd.DataFrame:
    """Parse raw Ergast lap JSON into a DataFrame.

    Returns DataFrame with columns: driver_code, lap, lap_time_seconds.
    """
    rows = []
    for lap_data in raw_json.get("Laps", []):
        lap_num = int(lap_data["number"])
        for timing in lap_data["Timings"]:
            time_str = timing["time"]
            parts = time_str.split(":")
            if len(parts) == 2:
                seconds = float(parts[0]) * 60 + float(parts[1])
            else:
                seconds = float(parts[0])
            rows.append({
                "driver_code": timing["driverId"],
                "lap": lap_num,
                "lap_time_seconds": seconds,
            })
    return pd.DataFrame(rows)


def compute_cumulative_times(df: pd.DataFrame) -> pd.DataFrame:
    """Add cumulative race time per driver per lap.

    Returns DataFrame with added cumulative_time column.
    """
    df = df.sort_values(["driver_code", "lap"]).copy()
    df["cumulative_time"] = df.groupby("driver_code")["lap_time_seconds"].cumsum()
    return df


def compute_positions(df: pd.DataFrame) -> pd.DataFrame:
    """Compute each driver's race position at each lap.

    Position is determined by ranking cumulative time (lowest = P1).
    Returns DataFrame with added position column.
    """
    df["position"] = df.groupby("lap")["cumulative_time"].rank(method="min").astype(int)
    return df


def get_driver_colors(drivers: list[str], driver_teams: dict[str, str] | None = None) -> dict[str, str]:
    """Map driver codes to hex colors using real F1 team colors.

    Falls back to a preset palette for unknown teams.
    """
    colors: dict[str, str] = {}
    fallback_idx = 0

    for driver in drivers:
        team = (driver_teams or {}).get(driver, "")
        color = None
        for team_name, team_color in TEAM_COLORS.items():
            if team_name.lower() in team.lower() or team.lower() in team_name.lower():
                color = team_color
                break
        if color is None:
            color = FALLBACK_PALETTE[fallback_idx % len(FALLBACK_PALETTE)]
            fallback_idx += 1
        colors[driver] = color

    return colors
