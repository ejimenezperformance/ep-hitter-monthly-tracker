"""Charts for the README (figures/)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ep_chart_style as ep  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    ep.apply()
    res = pd.read_csv(ROOT / "results/persistence_and_projection.csv")
    figs = ROOT / "figures"
    figs.mkdir(exist_ok=True)

    # 1. Persistence with 95% CI
    r = res.iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    for i, row in r.iterrows():
        ok = row.persistence_label == "CONFIRMED"
        col = ep.NAVY if ok else ep.GRAY
        ax.plot([row.b_ci_low, row.b_ci_high], [i, i], color=col, lw=2.5, solid_capstyle="round")
        ax.plot(row.persistence_b, i, "o", ms=10, color=col if ok else "white", mec=col, mew=2)
        ax.text(max(row.b_ci_high, 0.2) + 0.03, i,
                f"{row.persistence_b:.2f}  {'CONFIRMED' if ok else 'not confirmed'}",
                va="center", fontsize=9.5, fontweight="bold" if ok else "normal", color=col)
    ax.axvline(0, color=ep.NAVY, lw=1)
    ax.axvline(0.20, color=ep.GOLD, lw=1.5, ls="--")
    ax.text(0.205, len(r) - 0.45, "practical bar (0.20)", color=ep.GOLD, fontsize=8.5)
    ax.set_yticks(range(len(r)), r.metric)
    ax.set_xlim(min(-0.1, r.b_ci_low.min() - 0.05), max(0.85, r.b_ci_high.max() + 0.45))
    ax.set_ylim(-0.6, len(r) - 0.2)
    ax.set_xlabel("Share of a monthly change that carries into the next month (beyond sample size)")
    ax.set_title("Which monthly flags are real? All MLB hitters, 2026", loc="left")
    ep.footer(fig)
    fig.savefig(figs / "persistence_by_metric.png")
    plt.close(fig)

    # 2. Error of reacting fully vs calibrated, relative to "no extra reaction"
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    y = range(len(r))
    full = (r.mae_full_reaction / r.mae_no_reaction - 1) * 100
    cal = (r.mae_calibrated / r.mae_no_reaction - 1) * 100
    ax.barh([i + 0.2 for i in y], full, height=0.38, color=ep.GOLD)
    ax.barh([i - 0.2 for i in y], cal, height=0.38, color=ep.NAVY)
    for i in y:
        ax.text(max(full.iloc[i], 0) + 0.8, i + 0.2, f"{full.iloc[i]:+.0f}% react fully", va="center", fontsize=8.5)
        cv = cal.iloc[i] if abs(cal.iloc[i]) >= 0.05 else 0
        ax.text(max(cal.iloc[i], 0) + 0.8, i - 0.2, f"{cv:+.1f}% calibrated", va="center", fontsize=8.5)
    ax.axvline(0, color=ep.NAVY, lw=1)
    ax.set_yticks(list(y), r.metric)
    ax.set_xlim(min(-5, cal.min() - 3), full.max() * 1.45)
    ax.set_xlabel("Next-month prediction error vs. 'treat the month as more data' (%, lower is better)")
    ax.set_title("Chasing last month makes forecasts worse. Bat speed is the exception", loc="left")
    ep.footer(fig)
    fig.savefig(figs / "reaction_error.png")
    plt.close(fig)

    # 3. Bat-speed change vs next-month xwOBA change (quintiles, 95% CI)
    b = pd.read_csv(ROOT / "results/batspeed_to_xwoba_bins.csv")
    lk = pd.read_csv(ROOT / "results/batspeed_to_results.csv").set_index("outcome").loc["xwOBA"]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    ax.axhline(0, color=ep.GRAY, lw=1)
    drift = res.set_index("metric").loc["xwOBA", "drift"] * 1000
    ax.axhline(drift, color=ep.GOLD, lw=1.5, ls="--")
    ax.errorbar(b.bs_change, b.next_change * 1000, yerr=1.96 * b.se * 1000, fmt="o", ms=9,
                color=ep.NAVY, ecolor=ep.NAVY, elinewidth=2, capsize=4)
    for _, row in b.iterrows():
        ax.text(row.bs_change, row.next_change * 1000 + 1.96 * row.se * 1000 + 1.2,
                f"{row.next_change * 1000:+.0f}", ha="center", fontsize=9)
    lo = (b.next_change - 1.96 * b.se).min() * 1000
    hi = (b.next_change + 1.96 * b.se).max() * 1000
    ax.set_ylim(min(-28, lo - 8), max(18, hi + 6))
    ax.set_xlabel("Bat-speed change this month vs. season line (mph), quintiles")
    ax.set_ylabel("Next-month xwOBA change (points)")
    linked = lk.label == "CONFIRMED"
    ax.set_title("A slower-bat month " + ("came with" if linked else "did not come with") + " a worse next month",
                 loc="left")
    ax.text(0.02, 0.04, f"Slope {lk.b_bs_per_mph * 1000:+.1f} xwOBA points per mph "
            f"(95% CI {lk.b_ci_low * 1000:+.1f} to {lk.b_ci_high * 1000:+.1f}), {int(lk.pairs)} hitter-months: {lk.label}",
            transform=ax.transAxes, fontsize=8.5, color=ep.NAVY)
    ax.text(0.02, 0.11, f"Gold dashed line = league-wide drift for every hitter ({drift:+.0f} points)",
            transform=ax.transAxes, fontsize=8.5, color=ep.GOLD)
    ep.footer(fig)
    fig.savefig(figs / "batspeed_to_next_xwoba.png")
    plt.close(fig)
    print("charts saved to", figs)


if __name__ == "__main__":
    main()
