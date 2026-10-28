"""Check the hitter season totals built from pitch-level data against Baseball Savant's
own leaderboards (expected stats: PA, wOBA, xwOBA; bat tracking: average bat speed).

Output: results/validation_vs_savant.json
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    c = pd.read_csv(ROOT / "data/processed/league_hitter_month_counts.csv")
    s = c.groupby("batter").sum(numeric_only=True)
    s["woba"] = s.wOBA_num / s.wOBA_den
    s["xwoba"] = s.xwOBA_num / s.wOBA_den
    s["bat_speed"] = s.BatSpeed_sum / s.CompSwings
    e = pd.read_csv(ROOT / "data/raw/savant_expected_2026.csv").set_index("player_id")
    j = s.join(e[["pa", "woba", "est_woba"]].add_prefix("sv_"), how="inner")
    b = pd.read_csv(ROOT / "data/raw/savant_bat_tracking_2026.csv").set_index("id")
    k = s.join(b[["avg_bat_speed"]], how="inner")
    dw, dx, db = (j.woba - j.sv_woba).abs(), (j.xwoba - j.sv_est_woba).abs(), (k.bat_speed - k.avg_bat_speed).abs()
    out = {
        "expected_stats_hitters": int(len(j)),
        "pa_exact_match_pct": round(float((j.PA == j.sv_pa).mean() * 100), 1),
        "woba_abs_diff_median": round(float(dw.median()), 4), "woba_abs_diff_p95": round(float(dw.quantile(.95)), 4),
        "xwoba_abs_diff_median": round(float(dx.median()), 4), "xwoba_abs_diff_p95": round(float(dx.quantile(.95)), 4),
        "bat_tracking_hitters": int(len(k)),
        "bat_speed_abs_diff_median_mph": round(float(db.median()), 3),
        "bat_speed_abs_diff_p95_mph": round(float(db.quantile(.95)), 3),
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/validation_vs_savant.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
