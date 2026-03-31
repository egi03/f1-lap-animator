# F1 Lap Delta Animator

Visualize the gap between every driver and the race leader across all laps as an animated interactive chart.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Plotly](https://img.shields.io/badge/Plotly-5.18-purple?logo=plotly)
![Streamlit](https://img.shields.io/badge/Streamlit-1.29-red?logo=streamlit)

## Preview

[GIF coming soon — run locally and use screentogif]

## How it works

- **Pick any F1 race** from 1996–2024 using the sidebar dropdown or featured race presets
- **Watch the gap chart animate** lap by lap, showing each driver's time delta to the race leader with pit stop markers
- **Export the chart** as a standalone HTML file to share with anyone

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser. Select a season and race from the sidebar, or click a Featured Race to jump straight in.

## Data source

All race data is provided by the [Ergast Developer API](http://ergast.com/mrd/) via the [Jolpica mirror](https://api.jolpi.ca/ergast/).

## License

MIT
