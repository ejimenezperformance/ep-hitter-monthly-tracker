"""Build the processed tables from data/raw/pitches_2026.csv.

Outputs (data/processed/):
  league_hitter_month_counts.csv  every MLB hitter, every month (all teams pooled)
  team_hitter_month_counts.csv    same, split by the team each PA was taken for (feeds the Excel tracker)
  absence_months.csv              hitter-months touched by a 14+ day absence
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from counts import absence_months, competitive_p10, hitter_month_counts, load_raw  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    league = load_raw(ROOT / "data/raw/pitches_2026.csv")
    p10 = competitive_p10(league)  # competitive-swing cutoff uses each hitter's full season
    out = ROOT / "data/processed"
    out.mkdir(parents=True, exist_ok=True)
    lc = hitter_month_counts(league, p10)
    lc.to_csv(out / "league_hitter_month_counts.csv", index=False, encoding="utf-8")
    tc = hitter_month_counts(league, p10, by_team=True)
    tc.to_csv(out / "team_hitter_month_counts.csv", index=False, encoding="utf-8")
    absence_months(league).to_csv(out / "absence_months.csv", index=False, encoding="utf-8")
    print(f"league: {len(league):,} pitches, {lc.batter.nunique()} hitters, {int(lc.PA.sum()):,} PA, "
          f"dates {league.game_date.min().date()} to {league.game_date.max().date()}")
    print(f"by team: {len(tc):,} team-hitter-months, {tc.team.nunique()} teams, PA check {int(tc.PA.sum()):,}")


if __name__ == "__main__":
    main()
