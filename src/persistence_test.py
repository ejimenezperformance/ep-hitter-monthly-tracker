"""Decision test: when a hitter's month moves away from his season-to-date level,
how much of that move shows up again the next month?

For every hitter-month t (May-Aug) with a following month t+1:
    base     = season-to-date rate THROUGH month t (counts pooled, so month t is
               weighted by its own sample size)
    dev      = month t  - base          (the "flag" a monthly tracker shows)
    next_dev = month t+1 - base         (what actually happened next)

Why the base includes month t: measuring month t against the PRIOR months only lets
the noise in that prior baseline sit on both sides of the regression and creates fake
persistence with no real change in the hitter. With the pooled base, a hitter whose
true level never changes has expected b = 0 (verified in tests/test_synthetic.py).
So b > 0 means the latest month deserves MORE weight than its sample size already
gives it -- a real change in form, not just more data.

Persistence b = slope of next_dev on dev (with an intercept for league-wide seasonal drift).
Projection test (leave-one-player-out, MAE on month t+1):
    A  no extra reaction: base + drift  (the month counts only as more data)
    B  full reaction    : month t
    C  calibrated       : base + drift + b * dev
Paired player-cluster bootstrap gives CIs; Benjamini-Hochberg across metrics.

Pre-registered rules (set before the real run):
    persistence CONFIRMED  : BH q < 0.05 and b >= 0.20
    calibrated beats A     : 95% CI of MAE(A) - MAE(C) above 0 and MAE gain >= 2%
    full reaction worse    : 95% CI of MAE(B) - MAE(A) above 0
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

METRICS = {  # name: (numerator, denominator, min denominator per month)
    "wOBA": ("wOBA_num", "wOBA_den", 60),
    "xwOBA": ("xwOBA_num", "wOBA_den", 60),
    "K%": ("SO", "PA", 60),
    "Chase%": ("O_Swings", "O_Pitches", 100),
    "Barrel%": ("Barrels", "BBE", 40),
    "Bat Speed": ("BatSpeed_sum", "CompSwings", 40),
}
# outcome-only metrics (used by batspeed_to_results.py, not in the persistence table)
EXTRA = {"Avg EV": ("EV_sum", "EV_n", 40)}
MIN_PRIOR_PA = 80
MIN_MONTH_PA = 60
BAR = 0.20
N_BOOT = 2000
SEED = 2026


def build_pairs(counts, metric, excluded=frozenset()):
    num, den, min_den = {**METRICS, **EXTRA}[metric]
    c = counts.sort_values(["batter", "month_num"])
    rows = []
    for b, g in c.groupby("batter"):
        g = g.set_index("month_num")
        for t in (5, 6, 7, 8):
            if t not in g.index or t + 1 not in g.index:
                continue
            if (b, t) in excluded or (b, t + 1) in excluded:
                continue
            prior = g.loc[g.index < t]
            if prior.PA.sum() < MIN_PRIOR_PA or prior[den].sum() < min_den:
                continue
            cur, nxt = g.loc[t], g.loc[t + 1]
            if cur.PA < MIN_MONTH_PA or nxt.PA < MIN_MONTH_PA or cur[den] < min_den or nxt[den] < min_den:
                continue
            base = (prior[num].sum() + cur[num]) / (prior[den].sum() + cur[den])
            rows.append((g.hitter.iloc[0], b, t, base, cur[num] / cur[den], nxt[num] / nxt[den]))
    p = pd.DataFrame(rows, columns=["hitter", "batter", "month_num", "base", "cur", "nxt"])
    p["dev"] = p.cur - p.base
    p["next_dev"] = p.nxt - p.base
    return p


def ols(x, y):
    xm, ym = x.mean(), y.mean()
    b = ((x - xm) * (y - ym)).sum() / ((x - xm) ** 2).sum()
    return ym - b * xm, b


def lopo_predictions(p):
    """Leave-one-player-out drift and slope, from sufficient statistics."""
    x, y = p.dev.values, p.next_dev.values
    gid = p.batter.values
    tot = np.array([len(x), x.sum(), y.sum(), (x * x).sum(), (x * y).sum()])
    s = pd.DataFrame({"g": gid, "n": 1, "x": x, "y": y, "xx": x * x, "xy": x * y}).groupby("g").sum()
    own = s.loc[gid][["n", "x", "y", "xx", "xy"]].values
    n, sx, sy, sxx, sxy = (tot - own).T
    b = (sxy - sx * sy / n) / (sxx - sx * sx / n)
    a = sy / n - b * sx / n
    drift = sy / n
    pred_a = p.base.values + drift
    pred_b = p.cur.values
    pred_c = p.base.values + a + b * x
    return pred_a, pred_b, pred_c


def analyse(p, rng):
    a, b = ols(p.dev, p.next_dev)
    r, _ = stats.pearsonr(p.dev, p.next_dev)
    pa_, pb_, pc_ = lopo_predictions(p)
    y = p.nxt.values
    ea, eb, ec = np.abs(y - pa_), np.abs(y - pb_), np.abs(y - pc_)
    players = p.batter.unique()
    idx = {pl: np.flatnonzero(p.batter.values == pl) for pl in players}
    bs_b, bs_ac, bs_ba = [], [], []
    for _ in range(N_BOOT):
        take = np.concatenate([idx[pl] for pl in rng.choice(players, len(players))])
        q = p.iloc[take]
        bs_b.append(ols(q.dev, q.next_dev)[1])
        bs_ac.append(ea[take].mean() - ec[take].mean())
        bs_ba.append(eb[take].mean() - ea[take].mean())
    bs_b, bs_ac, bs_ba = map(np.array, (bs_b, bs_ac, bs_ba))
    se = bs_b.std(ddof=1)
    pval = 2 * stats.norm.sf(abs(b) / se)
    d = ea - ec
    return {
        "pairs": len(p), "hitters": len(players),
        "sd_monthly_dev": p.dev.std(), "drift": a,
        "persistence_b": b, "b_ci_low": np.percentile(bs_b, 2.5), "b_ci_high": np.percentile(bs_b, 97.5),
        "r": r, "p_value": pval,
        "mae_no_reaction": ea.mean(), "mae_full_reaction": eb.mean(), "mae_calibrated": ec.mean(),
        "gain_calibrated_vs_none": ea.mean() - ec.mean(),
        "gain_ci_low": np.percentile(bs_ac, 2.5), "gain_ci_high": np.percentile(bs_ac, 97.5),
        "gain_pct": (ea.mean() - ec.mean()) / ea.mean(),
        "cohens_d_paired": d.mean() / d.std(ddof=1),
        "full_minus_none": eb.mean() - ea.mean(),
        "full_ci_low": np.percentile(bs_ba, 2.5), "full_ci_high": np.percentile(bs_ba, 97.5),
    }


def bh(pvals):
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    q = p[order] * len(p) / (np.arange(len(p)) + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    out = np.empty_like(q)
    out[order] = np.minimum(q, 1)
    return out


def label(res):
    res["q_value"] = bh(res.p_value)
    ok = (res.q_value < 0.05) & (res.persistence_b >= BAR)
    res["persistence_label"] = np.where(ok, "CONFIRMED", "NOT CONFIRMED")
    res["persistence_note"] = np.select(
        [ok, (res.q_value < 0.05) & (res.persistence_b > 0)],
        ["carries into the next month", "real but small (below the 0.20 bar)"],
        "no evidence it carries over")
    res["calibrated_beats_none"] = np.where((res.gain_ci_low > 0) & (res.gain_pct >= 0.02),
                                            "CONFIRMED", "NOT CONFIRMED")
    res["full_reaction_worse"] = np.where(res.full_ci_low > 0, "CONFIRMED", "NOT CONFIRMED")
    return res


def run(counts, excluded=frozenset(), metrics=None, seed=SEED):
    rng = np.random.default_rng(seed)
    out = []
    for m in metrics or METRICS:
        p = build_pairs(counts, m, excluded)
        out.append({"metric": m, **analyse(p, rng)})
    return label(pd.DataFrame(out))


def excluded_months(root, counts):
    absent = pd.read_csv(root / "data/processed/absence_months.csv")
    excluded = set(zip(absent.batter, absent.month_num))
    manual = pd.read_csv(root / "data/injury_exclusions.csv")
    for name in manual.loc[manual.action == "exclude", "batter_name"]:
        for b in counts.loc[counts.hitter == name, "batter"].unique():
            excluded |= {(b, m) for m in range(4, 10)}
    return frozenset(excluded)


def main(root):
    root = Path(root)
    counts = pd.read_csv(root / "data/processed/league_hitter_month_counts.csv")
    excluded = excluded_months(root, counts)
    res = run(counts, excluded)
    (root / "results").mkdir(exist_ok=True)
    res.to_csv(root / "results/persistence_and_projection.csv", index=False, encoding="utf-8")
    run(counts).to_csv(root / "results/sensitivity_no_absence_filter.csv", index=False, encoding="utf-8")
    meta = {"hitter_months": int(len(counts)), "hitters": int(counts.batter.nunique()),
            "pa": int(counts.PA.sum()), "excluded_hitter_months": len(excluded),
            "n_boot": N_BOOT, "seed": SEED}
    (root / "results/run_info.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    cols = ["metric", "pairs", "hitters", "persistence_b", "b_ci_low", "b_ci_high", "q_value",
            "persistence_label", "gain_pct", "gain_ci_low", "calibrated_beats_none",
            "full_minus_none", "full_reaction_worse"]
    print(json.dumps(meta))
    print(res[cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
