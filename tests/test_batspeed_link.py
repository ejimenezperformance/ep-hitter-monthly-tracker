"""Known-answer tests for src/batspeed_to_results.py (run BEFORE the real data).

Synthetic pairs shaped like the real ones (650 pairs, 250 hitters, bat-speed change SD 0.45 mph,
xwOBA change SD .032, next-month noise SD .045):
  LINK     : next xwOBA change = +0.020 x bat-speed change  -> CONFIRMED
  NO LINK  : next xwOBA change unrelated to bat speed       -> NOT CONFIRMED
  REVERSED : next xwOBA change = -0.020 x bat-speed change  -> NOT CONFIRMED (wrong direction)
Run:  python tests/test_batspeed_link.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import batspeed_to_results as bl  # noqa: E402


def pairs(slope, n=650, hitters=250, seed=11):
    rng = np.random.default_rng(seed)
    bs = rng.normal(0, 0.45, n)
    own = rng.normal(0, 0.032, n)
    base = rng.normal(0.315, 0.03, n)
    nxt_change = slope * bs + rng.normal(0, 0.045, n)
    return pd.DataFrame({"batter": rng.integers(0, hitters, n), "base": base, "bs_change": bs,
                         "own_change": own, "next_change": nxt_change, "nxt": base + nxt_change})


def check():
    rows = []
    for name, slope in [("LINK", 0.02), ("NO LINK", 0.0), ("REVERSED", -0.02)]:
        rows.append({"outcome": name, **bl.analyse(pairs(slope), 0.010)})
    res = bl.label(pd.DataFrame(rows))
    print(res[["outcome", "b_bs_per_mph", "b_ci_low", "b_ci_high", "q_value", "label"]].round(4).to_string(index=False))
    lab = dict(zip(res.outcome, res.label))
    assert lab["LINK"] == "CONFIRMED"
    assert lab["NO LINK"] == "NOT CONFIRMED"
    assert lab["REVERSED"] == "NOT CONFIRMED"
    print("ALL BAT-SPEED LINK CHECKS PASS")


if __name__ == "__main__":
    check()
