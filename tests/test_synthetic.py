"""Known-answer tests for the persistence / projection test.

Three synthetic leagues (400 hitters, ~105 PA per month, binomial K%):
  1. NULL      : every hitter's true K% is fixed all season  -> b ~ 0, NOT CONFIRMED
  2. FORM      : true K% drifts month to month and the change sticks (AR(1), rho=0.85)
                 -> b > 0.20, CONFIRMED, calibrated model beats "no extra reaction"
  3. REVERSAL  : true K% alternates up/down every month -> b < 0, NOT CONFIRMED
Plus a warning test: on the NULL league, the naive design (month vs. PRIOR months only)
must produce fake persistence -- this is why the project uses the pooled baseline.
Run:  python tests/test_synthetic.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import persistence_test as pt  # noqa: E402


def league(kind, n=400, seed=7):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        talent = rng.normal(0.22, 0.05)
        shift = 0.0
        sign = rng.choice([-1, 1])
        for j, m in enumerate(range(4, 10)):
            if kind == "form":
                shift = 0.85 * shift + rng.normal(0, 0.035)
            elif kind == "reversal":
                shift = 0.03 * sign * (-1) ** j
            true = float(np.clip(talent + shift, 0.03, 0.6))
            pa = int(rng.integers(95, 115))
            rows.append({"hitter": f"H{i}", "batter": i, "month_num": m,
                         "PA": pa, "SO": rng.binomial(pa, true)})
    return pd.DataFrame(rows)


def naive_prior_only_baseline(counts):
    """Same test, but the baseline excludes month t (the design this project rejects)."""
    orig = pt.build_pairs

    def prior_only(c, metric, excluded=frozenset()):
        p = orig(c, metric, excluded)
        num, den, _ = pt.METRICS[metric]
        idx = c.set_index(["batter", "month_num"])
        dc = np.array([idx.loc[(b, t), den] for b, t in zip(p.batter, p.month_num)])
        dp = np.array([idx.loc[b].loc[lambda x: x.index < t, den].sum() for b, t in zip(p.batter, p.month_num)])
        p["base"] = (p.base * (dp + dc) - p.cur * dc) / dp
        p["dev"], p["next_dev"] = p.cur - p.base, p.nxt - p.base
        return p

    pt.build_pairs = prior_only
    try:
        return pt.run(counts, metrics=["K%"]).iloc[0]
    finally:
        pt.build_pairs = orig


def check():
    out = {}
    for kind in ("null", "form", "reversal"):
        r = pt.run(league(kind), metrics=["K%"]).iloc[0]
        out[kind] = r
        print(f"{kind:9s} b={r.persistence_b:+.3f} [{r.b_ci_low:+.3f},{r.b_ci_high:+.3f}] "
              f"q={r.q_value:.3g} {r.persistence_label:13s} gain={r.gain_pct:+.1%} "
              f"calibrated={r.calibrated_beats_none} full_worse={r.full_reaction_worse}")
    n, f, v = out["null"], out["form"], out["reversal"]
    assert n.b_ci_low < 0 < n.b_ci_high, "null: CI must contain 0 (no fake persistence)"
    assert n.persistence_label == "NOT CONFIRMED"
    assert n.full_reaction_worse == "CONFIRMED", "null: reacting fully to one month must hurt"
    assert f.persistence_label == "CONFIRMED" and f.persistence_b > 0.2
    assert f.calibrated_beats_none == "CONFIRMED"
    assert v.persistence_b < 0 and v.persistence_label == "NOT CONFIRMED"
    naive = naive_prior_only_baseline(league("null"))
    print(f"naive prior-only baseline on NULL league: b={naive.persistence_b:+.3f} -> {naive.persistence_label} (fake)")
    assert naive.persistence_b > 0.2, "naive design should show the fake persistence it is known for"
    print("ALL SYNTHETIC CHECKS PASS")


if __name__ == "__main__":
    check()
