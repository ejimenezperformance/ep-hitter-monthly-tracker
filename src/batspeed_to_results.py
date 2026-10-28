"""Does a monthly bat-speed change come with a change in NEXT month's production,
beyond what this month's production already shows?

Same pairs, baseline and filters as persistence_test.py. For every hitter-month t (May-Aug):
    bs_change   = bat speed in month t - season-to-date bat speed through t (mph)
    own_change  = outcome in month t   - season-to-date outcome through t
    next_change = outcome in month t+1 - season-to-date outcome through t
Model: next_change = a + b_bs * bs_change + b_own * own_change
b_bs = outcome points per 1 mph of bat-speed change, holding this month's outcome fixed.

Pre-registered rules (set before the real run):
    outcomes: xwOBA (primary), Barrel% and Avg EV (secondary); Benjamini-Hochberg across the 3
    CONFIRMED: q < 0.05 AND b_bs >= practical bar (positive: slower bat -> worse next month)
        xwOBA .010 per mph | Barrel% 0.5 points per mph | Avg EV 0.5 mph per mph
    forecast: leave-one-player-out MAE, season-to-date + drift vs. + bat-speed model
    flag view (descriptive): bs_change <= -0.75 mph vs. everyone else
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import persistence_test as pt  # noqa: E402

OUTCOMES = {"xwOBA": 0.010, "Barrel%": 0.005, "Avg EV": 0.5}
FLAG_MPH = -0.75
N_BOOT, SEED = 2000, 2026


def make_pairs(counts, outcome, excluded=frozenset()):
    bs = pt.build_pairs(counts, "Bat Speed", excluded)[["batter", "month_num", "dev"]]
    oc = pt.build_pairs(counts, outcome, excluded)
    df = oc.merge(bs.rename(columns={"dev": "bs_change"}), on=["batter", "month_num"])
    return df.rename(columns={"dev": "own_change", "next_dev": "next_change"})


def fit(df):
    X = np.column_stack([np.ones(len(df)), df.bs_change, df.own_change])
    return np.linalg.lstsq(X, df.next_change.values, rcond=None)[0]


def lopo_mae(df):
    players = df.batter.unique()
    pa, pc = np.empty(len(df)), np.empty(len(df))
    for pl in players:
        test = (df.batter == pl).values
        tr = df[~test]
        coef = fit(tr)
        te = df[test]
        pa[test] = te.base + tr.next_change.mean()
        pc[test] = te.base + coef[0] + coef[1] * te.bs_change + coef[2] * te.own_change
    return np.abs(df.nxt.values - pa), np.abs(df.nxt.values - pc)


def analyse(df, bar, seed=SEED):
    rng = np.random.default_rng(seed)
    a, b_bs, b_own = fit(df)
    ea, ec = lopo_mae(df)
    flag = (df.bs_change <= FLAG_MPH).values
    players = df.batter.unique()
    idx = {pl: np.flatnonzero(df.batter.values == pl) for pl in players}
    bb, gain, gap = [], [], []
    for _ in range(N_BOOT):
        take = np.concatenate([idx[pl] for pl in rng.choice(players, len(players))])
        q = df.iloc[take]
        bb.append(fit(q)[1])
        gain.append(ea[take].mean() - ec[take].mean())
        f = flag[take]
        gap.append(q.next_change.values[f].mean() - q.next_change.values[~f].mean() if f.any() else np.nan)
    bb, gain, gap = map(np.array, (bb, gain, gap))
    se = bb.std(ddof=1)
    return {
        "pairs": len(df), "hitters": len(players), "b_bs_per_mph": b_bs,
        "b_ci_low": np.percentile(bb, 2.5), "b_ci_high": np.percentile(bb, 97.5),
        "p_value": 2 * stats.norm.sf(abs(b_bs) / se), "b_own": b_own, "practical_bar": bar,
        "mae_season_line": ea.mean(), "mae_with_bat_speed": ec.mean(),
        "gain_pct": (ea.mean() - ec.mean()) / ea.mean(),
        "gain_ci_low": np.percentile(gain, 2.5), "gain_ci_high": np.percentile(gain, 97.5),
        "flagged_pairs": int(flag.sum()),
        "flagged_next_change": df.next_change[flag].mean(), "others_next_change": df.next_change[~flag].mean(),
        "flag_gap": df.next_change[flag].mean() - df.next_change[~flag].mean(),
        "flag_gap_ci_low": np.nanpercentile(gap, 2.5), "flag_gap_ci_high": np.nanpercentile(gap, 97.5),
    }


def label(res):
    res["q_value"] = pt.bh(res.p_value)
    res["label"] = np.where((res.q_value < 0.05) & (res.b_bs_per_mph >= res.practical_bar),
                            "CONFIRMED", "NOT CONFIRMED")
    res["note"] = np.select(
        [res.label == "CONFIRMED", (res.q_value < 0.05) & (res.b_bs_per_mph > 0)],
        ["slower bat came with a worse next month", "real but below the practical bar"],
        "no evidence of a link")
    res["forecast_gain"] = np.where((res.gain_ci_low > 0) & (res.gain_pct >= 0.02), "CONFIRMED", "NOT CONFIRMED")
    return res


def main(root):
    root = Path(root)
    counts = pd.read_csv(root / "data/processed/league_hitter_month_counts.csv")
    excluded = pt.excluded_months(root, counts)
    rows, pairs = [], {}
    for oc, bar in OUTCOMES.items():
        df = make_pairs(counts, oc, excluded)
        pairs[oc] = df
        rows.append({"outcome": oc, **analyse(df, bar)})
    res = label(pd.DataFrame(rows))
    res.to_csv(root / "results/batspeed_to_results.csv", index=False, encoding="utf-8")
    # binned view for the chart: bat-speed change quintiles vs next-month xwOBA change
    x = pairs["xwOBA"].copy()
    x["bin"] = pd.qcut(x.bs_change, 5, labels=False)
    bins = x.groupby("bin").agg(bs_change=("bs_change", "mean"), next_change=("next_change", "mean"),
                                own_change=("own_change", "mean"), n=("next_change", "size"),
                                sd=("next_change", "std")).reset_index()
    bins["se"] = bins.sd / np.sqrt(bins.n)
    bins.to_csv(root / "results/batspeed_to_xwoba_bins.csv", index=False, encoding="utf-8")
    cols = ["outcome", "pairs", "hitters", "b_bs_per_mph", "b_ci_low", "b_ci_high", "q_value", "label",
            "gain_pct", "forecast_gain", "flagged_pairs", "flag_gap", "flag_gap_ci_low", "flag_gap_ci_high"]
    print(res[cols].round(4).to_string(index=False))
    print(bins.round(4).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
