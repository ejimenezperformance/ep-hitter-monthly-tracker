"""Download 2026 regular-season pitch-level Statcast data for every MLB hitter,
plus the Savant leaderboards used to validate the counts.

Source: Baseball Savant Statcast Search (CSV export), batter view, so player_name is
the hitter. Pulled in 4-day windows to stay under Savant's 25,000-row cap. Only the
columns used downstream are kept; raw files go to data/raw/ (ignored by git).

  pitches_2026.csv          every regular-season pitch (needed columns only)
  savant_expected_2026.csv  expected-stats leaderboard (PA, wOBA, xwOBA), validation
  savant_bat_tracking_2026.csv  bat-tracking leaderboard (avg bat speed), validation

Usage: python src/pull_data.py
"""
import io
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
SAVANT = "https://baseballsavant.mlb.com"
START, END = date(2026, 3, 25), date(2026, 9, 27)
KEEP = ["game_pk", "game_date", "game_type", "home_team", "away_team", "inning_topbot",
        "at_bat_number", "pitch_number", "batter", "player_name", "stand", "events",
        "description", "type", "zone", "launch_speed", "launch_angle", "launch_speed_angle",
        "woba_value", "woba_denom", "estimated_woba_using_speedangle", "bat_speed",
        "delta_run_exp"]


def get(url, params, tries=6):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=300)
            if r.ok:
                text = r.content.decode("utf-8-sig").strip()
                return pd.read_csv(io.StringIO(text), low_memory=False) if text else pd.DataFrame()
        except requests.RequestException:
            pass
        time.sleep(8 * (i + 1))
    raise RuntimeError(f"failed: {url} {params}")


def pitches():
    out = RAW / "pitches_2026.csv"
    if out.exists():
        print("cached", out.name)
        return
    parts, d = [], START
    while d <= END:
        e = min(d + timedelta(days=3), END)
        df = get(f"{SAVANT}/statcast_search/csv", {
            "all": "true", "hfGT": "R|", "hfSea": "2026|", "player_type": "batter",
            "game_date_gt": d.isoformat(), "game_date_lt": e.isoformat(),
            "min_pitches": 0, "min_results": 0, "type": "details"})
        if len(df) >= 24_999:
            raise RuntimeError(f"row cap hit {d}..{e}: use smaller windows")
        if not df.empty:
            parts.append(df.reindex(columns=KEEP))
        print(d, e, len(df), flush=True)
        d = e + timedelta(days=1)
    pd.concat(parts).to_csv(out, index=False, encoding="utf-8")


def leaderboards():
    jobs = {
        "savant_expected_2026": (f"{SAVANT}/leaderboard/expected_statistics",
                                 {"type": "batter", "year": 2026, "position": "", "team": "",
                                  "min": 100, "csv": "true"}),
        "savant_bat_tracking_2026": (f"{SAVANT}/leaderboard/bat-tracking",
                                     {"type": "batter", "seasonStart": 2026, "seasonEnd": 2026,
                                      "gameType": "Regular", "minSwings": 100, "minGroupSwings": 1,
                                      "csv": "true"}),
    }
    for name, (url, params) in jobs.items():
        out = RAW / f"{name}.csv"
        if not out.exists():
            get(url, params).to_csv(out, index=False, encoding="utf-8")
            print("saved", out.name)


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    leaderboards()
    pitches()
