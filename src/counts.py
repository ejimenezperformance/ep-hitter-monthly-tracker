"""Aggregate pitch-level Statcast rows into hitter-month counting stats.

Every rate in the project (and in the Excel tracker) is built from these counts,
so the definitions live in one place.
"""
import numpy as np
import pandas as pd

MONTH_NAMES = {4: "Mar-Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep"}
HITS = {"single", "double", "triple", "home_run"}
WALKS = {"walk", "intent_walk"}
STRIKEOUTS = {"strikeout", "strikeout_double_play"}
NOT_AB = WALKS | {"hit_by_pitch", "sac_fly", "sac_bunt", "sac_fly_double_play",
                  "sac_bunt_double_play", "catcher_interf"}
SAC_FLY = {"sac_fly", "sac_fly_double_play"}
# Savant credits ROE / FC with a wOBA value in the pitch CSV; leaderboards treat them as outs.
WOBA_AS_OUT = {"field_error", "fielders_choice"}
SWINGS = {"swinging_strike", "swinging_strike_blocked", "foul", "foul_tip", "hit_into_play",
          "foul_bunt", "missed_bunt", "bunt_foul_tip"}
WHIFFS = {"swinging_strike", "swinging_strike_blocked", "missed_bunt"}
SUM_COLS = ["Pitches", "Swings", "Whiffs", "Z_Pitches", "Z_Swings", "Z_Whiffs", "O_Pitches",
            "O_Swings", "RunValue", "PA", "AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF", "SO",
            "wOBA_num", "wOBA_den", "xwOBA_num", "BBE", "Barrels", "HardHit", "EV_n", "EV_sum",
            "SweetSpot", "CompSwings", "BatSpeed_sum", "FastSwings"]
KEYS = ["hitter", "batter", "month_num", "month"]


def load_raw(path):
    df = pd.read_csv(path, low_memory=False)
    if "game_type" in df:
        df = df[df.game_type.isin(["R", np.nan])]
    df = df.drop_duplicates(["game_pk", "at_bat_number", "pitch_number"]).copy()
    df["game_date"] = pd.to_datetime(df.game_date)
    df["month_num"] = df.game_date.dt.month.clip(lower=4, upper=9)
    df["month"] = df.month_num.map(MONTH_NAMES)
    df["hitter"] = df.player_name.str.split(", ").str[::-1].str.join(" ")
    # batting team: away team bats in the top of the inning
    df["team"] = np.where(df.inning_topbot == "Top", df.away_team, df.home_team)
    # one display name per hitter id (Savant can vary accents between windows)
    df["hitter"] = df.batter.map(df.groupby("batter").hitter.agg(lambda s: s.mode().iloc[0]))
    return df


def competitive_p10(df):
    """10th percentile of each hitter's full-season swing speeds (Savant: top 90% = competitive)."""
    s = df[df.bat_speed.notna() & ~df.description.str.contains("bunt", na=False)]
    return s.groupby("batter").bat_speed.quantile(0.10)


def hitter_month_counts(df, p10=None, by_team=False):
    keys = (["team"] if by_team else []) + KEYS
    p10 = competitive_p10(df) if p10 is None else p10
    ev = df.events
    pa = df[ev.notna() & (ev != "truncated_pa")].copy()
    pa["PA"] = 1
    pa["AB"] = (~pa.events.isin(NOT_AB)).astype(int)
    pa["H"] = pa.events.isin(HITS).astype(int)
    for e, c in [("double", "2B"), ("triple", "3B"), ("home_run", "HR")]:
        pa[c] = (pa.events == e).astype(int)
    pa["BB"] = pa.events.isin(WALKS).astype(int)
    pa["HBP"] = (pa.events == "hit_by_pitch").astype(int)
    pa["SF"] = pa.events.isin(SAC_FLY).astype(int)
    pa["SO"] = pa.events.isin(STRIKEOUTS).astype(int)
    den = pa.woba_denom.fillna(0)
    pa["wOBA_den"] = den
    pa["wOBA_num"] = pa.woba_value.fillna(0) * (den > 0) * (~pa.events.isin(WOBA_AS_OUT))
    xw = np.where(pa.estimated_woba_using_speedangle.notna(),
                  pa.estimated_woba_using_speedangle, pa.woba_value.fillna(0))
    pa["xwOBA_num"] = xw * (den > 0)

    bbe = df[df.type == "X"].copy()
    bbe["BBE"] = 1
    bbe["Barrels"] = (bbe.launch_speed_angle == 6).astype(int)
    bbe["HardHit"] = (bbe.launch_speed >= 95).astype(int)
    bbe["EV_n"] = bbe.launch_speed.notna().astype(int)
    bbe["EV_sum"] = bbe.launch_speed.fillna(0)
    bbe["SweetSpot"] = bbe.launch_angle.between(8, 32).astype(int)

    p = df.copy()
    p["Pitches"] = 1
    p["Swings"] = p.description.isin(SWINGS).astype(int)
    p["Whiffs"] = p.description.isin(WHIFFS).astype(int)
    inz, outz = p.zone.between(1, 9), p.zone.between(11, 14)
    p["Z_Pitches"] = inz.astype(int)
    p["Z_Swings"] = (inz & (p.Swings == 1)).astype(int)
    p["Z_Whiffs"] = (inz & (p.Whiffs == 1)).astype(int)
    p["O_Pitches"] = outz.astype(int)
    p["O_Swings"] = (outz & (p.Swings == 1)).astype(int)
    p["RunValue"] = p.delta_run_exp.fillna(0)

    bs = p[p.bat_speed.notna() & ~p.description.str.contains("bunt", na=False)].copy()
    bs = bs[bs.bat_speed >= bs.batter.map(p10)]
    bs["CompSwings"] = 1
    bs["BatSpeed_sum"] = bs.bat_speed
    bs["FastSwings"] = (bs.bat_speed >= 75).astype(int)

    def agg(d, cols):
        return d.groupby(keys)[cols].sum()

    out = pd.concat([
        agg(p, ["Pitches", "Swings", "Whiffs", "Z_Pitches", "Z_Swings", "Z_Whiffs",
                "O_Pitches", "O_Swings", "RunValue"]),
        agg(pa, ["PA", "AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF", "SO",
                 "wOBA_num", "wOBA_den", "xwOBA_num"]),
        agg(bbe, ["BBE", "Barrels", "HardHit", "EV_n", "EV_sum", "SweetSpot"]),
        agg(bs, ["CompSwings", "BatSpeed_sum", "FastSwings"]),
    ], axis=1).fillna(0).reset_index()
    out = out[out.PA > 0].copy()
    for c in ["RunValue", "wOBA_num", "xwOBA_num", "EV_sum", "BatSpeed_sum"]:
        out[c] = out[c].round(3)
    return out[keys + SUM_COLS].sort_values(keys[:-1]).reset_index(drop=True)


def absence_months(df, min_gap_days=14):
    """Hitter-months touched by a stretch of min_gap_days+ between consecutive games
    (IL stint, demotion or other absence), or by a season that ended min_gap_days+ early.
    Every month from the last game before the gap to the first game after it is flagged."""
    g = df[["batter", "game_date"]].drop_duplicates().sort_values(["batter", "game_date"])
    g["prev"] = g.groupby("batter").game_date.shift()
    g = g[(g.game_date - g.prev).dt.days >= min_gap_days]
    rows = []
    for b, prev, cur in g[["batter", "prev", "game_date"]].itertuples(index=False):
        m0 = min(max(prev.month, 4), 9)
        m1 = min(max(cur.month, 4), 9)
        rows += [(b, m, (cur - prev).days) for m in range(m0, m1 + 1)]
    # season ended early for the hitter (injury, release, demotion)
    end = df.game_date.max()
    last = df.groupby("batter").game_date.max()
    for b, d in last[(end - last).dt.days >= min_gap_days].items():
        rows += [(b, m, (end - d).days) for m in range(min(max(d.month, 4), 9), 10)]
    out = pd.DataFrame(rows, columns=["batter", "month_num", "gap_days"])
    return out.groupby(["batter", "month_num"]).gap_days.max().reset_index()
