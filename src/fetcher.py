"""Ergast API data fetching with local JSON caching."""

import json
import os
from pathlib import Path
from typing import Any

import requests

BASE_URL = "http://ergast.com/api/f1"
CACHE_DIR = Path(".cache")
TIMEOUT = 10


def _get_cache_path(season: int, round_num: int, suffix: str) -> Path:
    """Return the cache file path for a given request."""
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / f"{season}_{round_num}_{suffix}.json"


def _load_cache(path: Path) -> Any | None:
    """Load cached JSON if it exists."""
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return None


def _save_cache(path: Path, data: Any) -> None:
    """Save data to a JSON cache file."""
    with open(path, "w") as f:
        json.dump(data, f)


def fetch_seasons() -> list[int]:
    """Return list of available seasons (1996-2024)."""
    return list(range(1996, 2025))


def fetch_race_schedule(season: int) -> list[dict[str, Any]]:
    """Fetch the race schedule for a given season.

    Returns a list of dicts with keys: round, raceName, circuit.
    """
    url = f"{BASE_URL}/{season}.json"
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    races = resp.json()["MRData"]["RaceTable"]["Races"]
    return [
        {
            "round": int(r["round"]),
            "raceName": r["raceName"],
            "circuit": r["Circuit"]["circuitName"],
        }
        for r in races
    ]


def fetch_lap_times(season: int, round_num: int) -> dict[str, Any]:
    """Fetch all lap times for a race, with pagination and caching.

    Returns the raw JSON response with all laps combined.
    """
    cache_path = _get_cache_path(season, round_num, "laps")
    cached = _load_cache(cache_path)
    if cached is not None:
        return cached

    all_laps: list[dict] = []
    offset = 0
    limit = 2000

    while True:
        url = f"{BASE_URL}/{season}/{round_num}/laps.json?limit={limit}&offset={offset}"
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        race_table = data["MRData"]["RaceTable"]
        races = race_table.get("Races", [])
        if not races:
            break
        laps = races[0].get("Laps", [])
        if not laps:
            break
        all_laps.extend(laps)
        total = int(data["MRData"]["total"])
        offset += limit
        if offset >= total:
            break

    result = {"Laps": all_laps}
    if all_laps:
        result["raceName"] = races[0].get("raceName", "")
        result["season"] = races[0].get("season", str(season))
    _save_cache(cache_path, result)
    return result


def fetch_race_result(season: int, round_num: int) -> list[dict[str, Any]]:
    """Fetch finishing order and driver info for a race.

    Returns list of dicts with: position, driver_code, driver_name, team, nationality, gap.
    """
    cache_path = _get_cache_path(season, round_num, "results")
    cached = _load_cache(cache_path)
    if cached is not None:
        return cached

    url = f"{BASE_URL}/{season}/{round_num}/results.json"
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    races = resp.json()["MRData"]["RaceTable"]["Races"]
    if not races:
        return []

    results = []
    for r in races[0]["Results"]:
        driver = r["Driver"]
        constructor = r["Constructor"]
        results.append({
            "position": int(r["position"]),
            "driver_code": driver.get("code", driver["familyName"][:3].upper()),
            "driver_name": f"{driver['givenName']} {driver['familyName']}",
            "team": constructor["name"],
            "nationality": driver["nationality"],
            "gap": r.get("Time", {}).get("time", r.get("status", "DNF")),
        })

    _save_cache(cache_path, results)
    return results
