# F1 Race Flow

An interactive web application that fetches Formula 1 data and visualizes the lap-by-lap race position progression using authentic F1 broadcast styling.

![F1 Race Flow Animation](preview.gif)

## Features

- **Lap-by-Lap Animation**: Watch the grid's positions evolve over the course of the race.
- **Interactive Controls**: Play, pause, scrub through laps, and click driver names to isolate specific rivalries.
- **Pit Stop Tracking**: Automatically detects and accurately plots pit stops on the timeline as warning triangles.
- **HTML Export**: Save any generated race visualization as a standalone interactive HTML file.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   streamlit run app.py
   ```
   *Then open `http://localhost:8501` in your browser!*

## Data Source

All race data is provided by the [Ergast Developer API](http://ergast.com/mrd/) (via the [Jolpica mirror](https://api.jolpi.ca/ergast/)).

## License

MIT
