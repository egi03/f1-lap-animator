"""F1 Lap Delta Animator — Streamlit app."""

import streamlit as st
import pandas as pd

from src.fetcher import fetch_seasons, fetch_race_schedule, fetch_lap_times, fetch_race_result
from src.processor import parse_lap_times, compute_cumulative_times, compute_gap_to_leader, get_driver_colors
from src.visualizer import build_animated_chart, export_html

st.set_page_config(page_title="F1 Lap Delta Animator", layout="wide")

FEATURED_RACES = [
    {"season": 2021, "round": 22, "label": "2021 Abu Dhabi — Verstappen vs Hamilton"},
    {"season": 2023, "round": 5, "label": "2023 Miami Grand Prix"},
    {"season": 2019, "round": 11, "label": "2019 German Grand Prix — Chaos in Hockenheim"},
]

# --- Sidebar ---
st.sidebar.title("🏎️ F1 Lap Delta Animator")

st.sidebar.markdown("### Featured Races")
for race in FEATURED_RACES:
    if st.sidebar.button(race["label"], key=f"feat_{race['season']}_{race['round']}"):
        st.session_state["selected_season"] = race["season"]
        st.session_state["selected_round"] = race["round"]
        st.session_state["load_race"] = True

st.sidebar.markdown("---")
st.sidebar.markdown("### Pick a Race")

seasons = fetch_seasons()
season = st.sidebar.selectbox("Season", seasons, index=len(seasons) - 1)

schedule = None
try:
    schedule = fetch_race_schedule(season)
except Exception as e:
    st.sidebar.error(f"Failed to fetch schedule: {e}")

if schedule:
    race_options = {f"Round {r['round']}: {r['raceName']}": r for r in schedule}
    race_label = st.sidebar.selectbox("Race", list(race_options.keys()))
    selected_race = race_options[race_label]

    if st.sidebar.button("Load Race"):
        st.session_state["selected_season"] = season
        st.session_state["selected_round"] = selected_race["round"]
        st.session_state["load_race"] = True

# --- Main Area ---
if st.session_state.get("load_race"):
    sel_season = st.session_state["selected_season"]
    sel_round = st.session_state["selected_round"]
    st.session_state["load_race"] = False

    with st.spinner("Fetching lap data..."):
        try:
            raw_laps = fetch_lap_times(sel_season, sel_round)
            results = fetch_race_result(sel_season, sel_round)
        except Exception as e:
            st.error(f"API error: {e}")
            st.stop()

    if not raw_laps.get("Laps"):
        st.warning(
            "No lap time data available for this race. "
            "Older races (pre-1996) or some events may not have detailed lap data in the Ergast API."
        )
        st.stop()

    race_name = raw_laps.get("raceName", "Race")

    df = parse_lap_times(raw_laps)
    if df.empty:
        st.warning("No lap time data could be parsed for this race.")
        st.stop()

    # Map driverId (used in lap data) → 3-letter code (from results)
    id_to_code = {r["driver_id"]: r["driver_code"] for r in results}
    id_to_team = {r["driver_code"]: r["team"] for r in results}
    df["driver_code"] = df["driver_code"].map(id_to_code).fillna(df["driver_code"])

    df = compute_cumulative_times(df)
    df = compute_gap_to_leader(df)

    driver_teams = {d: id_to_team.get(d, "") for d in df["driver_code"].unique()}
    colors = get_driver_colors(df["driver_code"].unique().tolist(), driver_teams)

    st.markdown(f"## {race_name} — {sel_season}")
    if schedule:
        circuit_info = next((r for r in schedule if r["round"] == sel_round), None)
        if circuit_info:
            st.markdown(f"*{circuit_info['circuit']}*")

    fig = build_animated_chart(df, race_name, results, colors, sel_season)
    st.plotly_chart(fig, use_container_width=True)

    # Export button
    if st.button("Export as HTML"):
        filename = f"exports/{sel_season}_{sel_round}_{race_name.replace(' ', '_')}.html"
        saved_path = export_html(fig, filename)
        st.success(f"Exported to: {saved_path}")

    # Results table
    st.markdown("### Race Results")
    if results:
        results_df = pd.DataFrame(results)
        results_df = results_df[["position", "driver_name", "team", "gap"]]
        results_df.columns = ["Pos", "Driver", "Team", "Gap"]
        st.dataframe(results_df, use_container_width=True, hide_index=True)
else:
    st.markdown("## Welcome to F1 Lap Delta Animator")
    st.markdown(
        "Select a season and race from the sidebar, or click one of the **Featured Races** to get started.\n\n"
        "This tool visualizes the gap between every driver and the race leader, lap by lap, "
        "as an animated interactive chart."
    )
