"""F1 Lap Race Flow Streamlit app."""

import streamlit as st
import pandas as pd

from src.fetcher import fetch_seasons, fetch_race_schedule, fetch_lap_times, fetch_race_result
from src.processor import parse_lap_times, compute_cumulative_times, compute_positions, get_driver_colors
from src.visualizer import build_animated_chart, export_html

st.set_page_config(page_title="F1 Lap Race Flow", layout="wide")

# Apply custom F1-style font (Titillium Web) globally
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@300;400;600;700&display=swap');
        
        * {
            font-family: 'Titillium Web', sans-serif !important;
        }
        h1, h2, h3, h4, h5, h6 {
            font-weight: 700 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.title("F1 Race Flow")

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
        st.session_state.pop("export_path", None)

# --- Main Area ---
if st.session_state.get("load_race"):
    sel_season = st.session_state["selected_season"]
    sel_round = st.session_state["selected_round"]
    # We deliberately DO NOT set load_race = False here so the app 
    # stays on the loaded race when other buttons are clicked!

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
    df = compute_positions(df)

    driver_teams = {d: id_to_team.get(d, "") for d in df["driver_code"].unique()}
    colors = get_driver_colors(df["driver_code"].unique().tolist(), driver_teams)

    st.markdown(f"## {race_name} {sel_season}")
    if schedule:
        circuit_info = next((r for r in schedule if r["round"] == sel_round), None)
        if circuit_info:
            st.markdown(f"*{circuit_info['circuit']}*")

    fig = build_animated_chart(df, race_name, results, colors, sel_season)
    st.plotly_chart(fig, use_container_width=True)

    # Export button
    st.markdown("---")
    st.markdown("### Export Visualization")
    st.markdown("Save this interactive chart as a standalone webpage file that you can send to anyone.")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if st.button("Generate HTML Export", type="primary"):
            with st.spinner("Generating HTML file (this might take a few seconds)..."):
                filename = f"exports/{sel_season}_{sel_round}_{race_name.replace(' ', '_')}.html"
                saved_path = export_html(fig, filename)
                st.session_state["export_path"] = saved_path
                
    with col2:
        if "export_path" in st.session_state:
            try:
                with open(st.session_state["export_path"], "r", encoding="utf-8") as file:
                    html_data = file.read()
                    
                st.download_button(
                    label="⬇️ Download HTML File",
                    data=html_data,
                    file_name=f"{sel_season}_{race_name.replace(' ', '_')}_grid_trace.html",
                    mime="text/html"
                )
            except FileNotFoundError:
                pass

    # Results table
    st.markdown("### Race Results")
    if results:
        results_df = pd.DataFrame(results)
        results_df = results_df[["position", "driver_name", "team", "gap"]]
        results_df.columns = ["Pos", "Driver", "Team", "Gap"]
        st.dataframe(results_df, use_container_width=True, hide_index=True)
else:
    st.markdown("## Welcome to F1 Race Flow")
    st.markdown(
        "Select a season and race from the sidebar to get started.\n\n"
        "This tool visualizes the position of every driver across the entire grid, lap by lap, "
        "as an animated interactive chart resembling authentic F1 broadcast telemetry."
    )
