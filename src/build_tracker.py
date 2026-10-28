"""Build the league-wide Excel tracker: pick any team and hitter.

Every rate is a live Excel formula on the Counts / Season Counts tabs (hardcoded
counting inputs aggregated from Statcast by src/build_counts.py).
Usage: python src/build_tracker.py
"""
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.formatting.rule import ColorScaleRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "MLB_Hitter_Monthly_Tracker_2026.xlsx"
MONTHS = ["Mar-Apr", "May", "Jun", "Jul", "Aug", "Sep"]
GRID_MIN_SEASON_PA = 50

NAVY, GOLD, OFF, GRAY = "0B1B33", "D4A53A", "F5F3EC", "8A8F98"
F = "Arial"
hdr_font = Font(name=F, bold=True, color="FFFFFF", size=10)
hdr_fill = PatternFill("solid", fgColor=NAVY)
body, bold = Font(name=F, size=10), Font(name=F, size=10, bold=True)
blue = Font(name=F, size=10, color="0000FF")
title_f = Font(name=F, size=16, bold=True, color=NAVY)
h2 = Font(name=F, size=12, bold=True, color=NAVY)
sub_f = Font(name=F, size=10, italic=True, color="555555")
yellow = PatternFill("solid", fgColor="FFFF00")
band = PatternFill("solid", fgColor=OFF)
box = Border(bottom=Side(style="thin", color="D0D5DD"))
center = Alignment(horizontal="center", vertical="center", wrap_text=True)
mid = Alignment(horizontal="center")

# ---------------------------------------------------------------- data
c = pd.read_csv(ROOT / "data/processed/team_hitter_month_counts.csv")
res = pd.read_csv(ROOT / "results/persistence_and_projection.csv")
link = pd.read_csv(ROOT / "results/batspeed_to_results.csv").set_index("outcome")
c["key"] = c.team + "|" + c.hitter
season = c.groupby(["team", "hitter", "key"], as_index=False).sum(numeric_only=True)
season = season.drop(columns=["batter", "month_num"]).sort_values(["team", "PA"], ascending=[True, False])
order = season.key.tolist()
c["_o"] = c.key.map({k: i for i, k in enumerate(order)})
c = c.sort_values(["_o", "month_num"]).drop(columns="_o").reset_index(drop=True)
teams = sorted(c.team.unique())
grid = season[season.PA >= GRID_MIN_SEASON_PA]
GRID_ROWS = int(grid.groupby("team").size().max())

SUMS = ["Pitches", "Swings", "Whiffs", "Z_Pitches", "Z_Swings", "Z_Whiffs", "O_Pitches", "O_Swings",
        "RunValue", "PA", "AB", "H", "2B", "3B", "HR", "BB", "HBP", "SF", "SO", "wOBA_num", "wOBA_den",
        "xwOBA_num", "BBE", "Barrels", "HardHit", "EV_n", "EV_sum", "SweetSpot", "CompSwings",
        "BatSpeed_sum", "FastSwings"]
CCOLS = ["key", "team", "hitter", "batter", "month_num", "month"] + SUMS
SCOLS = ["key", "team", "hitter"] + SUMS
CC = {k: L(i + 1) for i, k in enumerate(CCOLS)}
SC = {k: L(i + 1) for i, k in enumerate(SCOLS)}
NC, NS = len(c) + 1, len(season) + 1


def rng(k):
    return f"Counts!${CC[k]}$2:${CC[k]}${NC}"


METRICS = [
    ("PA", "0", lambda g: g("PA")),
    ("AVG", ".000", lambda g: f"{g('H')}/{g('AB')}"),
    ("OBP", ".000", lambda g: f"({g('H')}+{g('BB')}+{g('HBP')})/({g('AB')}+{g('BB')}+{g('HBP')}+{g('SF')})"),
    ("SLG", ".000", lambda g: f"({g('H')}+{g('2B')}+2*{g('3B')}+3*{g('HR')})/{g('AB')}"),
    ("HR", "0", lambda g: g("HR")),
    ("wOBA", ".000", lambda g: f"{g('wOBA_num')}/{g('wOBA_den')}"),
    ("xwOBA", ".000", lambda g: f"{g('xwOBA_num')}/{g('wOBA_den')}"),
    ("xwOBA - wOBA", "+.000;-.000;.000", lambda g: f"({g('xwOBA_num')}-{g('wOBA_num')})/{g('wOBA_den')}"),
    ("K%", "0.0%", lambda g: f"{g('SO')}/{g('PA')}"),
    ("BB%", "0.0%", lambda g: f"{g('BB')}/{g('PA')}"),
    ("Barrel%", "0.0%", lambda g: f"{g('Barrels')}/{g('BBE')}"),
    ("HardHit%", "0.0%", lambda g: f"{g('HardHit')}/{g('BBE')}"),
    ("Avg EV", "0.0", lambda g: f"{g('EV_sum')}/{g('EV_n')}"),
    ("SweetSpot%", "0.0%", lambda g: f"{g('SweetSpot')}/{g('BBE')}"),
    ("Chase%", "0.0%", lambda g: f"{g('O_Swings')}/{g('O_Pitches')}"),
    ("Z-Swing%", "0.0%", lambda g: f"{g('Z_Swings')}/{g('Z_Pitches')}"),
    ("Whiff%", "0.0%", lambda g: f"{g('Whiffs')}/{g('Swings')}"),
    ("Z-Contact%", "0.0%", lambda g: f"1-{g('Z_Whiffs')}/{g('Z_Swings')}"),
    ("Bat Speed", "0.0", lambda g: f"{g('BatSpeed_sum')}/{g('CompSwings')}"),
    ("Fast-Swing%", "0.0%", lambda g: f"{g('FastSwings')}/{g('CompSwings')}"),
    ("Run Value", "+0.0;-0.0;0.0", lambda g: g("RunValue")),
]
MI = {m[0]: i for i, m in enumerate(METRICS)}


def fm(name, g):
    return f'=IFERROR({METRICS[MI[name]][2](g)},"")'


def hdr(ws, row, col, text, width=None):
    cl = ws.cell(row=row, column=col, value=text)
    cl.font, cl.fill, cl.alignment = hdr_font, hdr_fill, center
    if width:
        ws.column_dimensions[L(col)].width = width


def put(ws, row, col, value, fmt=None, font=body, align=mid, border=box):
    cl = ws.cell(row=row, column=col, value=value)
    cl.font, cl.alignment = font, align
    if fmt:
        cl.number_format = fmt
    if border:
        cl.border = border
    return cl


def line_chart(ws, rows, first_col, last_col, cat_row, title, anchor, yfmt, ymin=None):
    ch = LineChart()
    ch.title, ch.height, ch.width = title, 7, 14
    ch.y_axis.number_format, ch.y_axis.majorGridlines = yfmt, None
    if ymin is not None:
        ch.y_axis.scaling.min = ymin
    for rr in rows:
        ch.add_data(Reference(ws, min_col=first_col - 1, max_col=last_col, min_row=rr, max_row=rr),
                    from_rows=True, titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=first_col, max_col=last_col, min_row=cat_row))
    for s, col in zip(ch.series, [NAVY, GOLD, GRAY]):
        s.smooth = False
        s.graphicalProperties.line.solidFill = col
        s.graphicalProperties.line.width = 28000
        s.marker.symbol, s.marker.size = "circle", 6
        s.marker.graphicalProperties.solidFill = col
        s.marker.graphicalProperties.line.solidFill = col
    ch.x_axis.delete = ch.y_axis.delete = False
    ws.add_chart(ch, anchor)


wb = Workbook()

# ---------------------------------------------------------------- Lists (hidden)
ls = wb.active
ls.title = "Lists"
for i, t in enumerate(teams, start=1):
    ls.cell(row=i, column=1, value=t)
for i, (t, h) in enumerate(zip(season.team, season.hitter), start=1):
    ls.cell(row=i, column=3, value=t)
    ls.cell(row=i, column=4, value=h)
for i, (t, h) in enumerate(zip(grid.team, grid.hitter), start=1):
    ls.cell(row=i, column=6, value=t)
    ls.cell(row=i, column=7, value=h)
NT, NH, NG = len(teams), len(season), len(grid)
TEAM_LIST = f"Lists!$A$1:$A${NT}"
LT, LH = f"Lists!$C$1:$C${NH}", f"Lists!$D$1:$D${NH}"
GT, GH = f"Lists!$F$1:$F${NG}", f"Lists!$G$1:$G${NG}"
ls.sheet_state = "hidden"


def team_picker(ws, cell, default):
    ws[cell] = default
    ws[cell].font, ws[cell].fill = Font(name=F, size=12, bold=True, color="0000FF"), yellow
    dv = DataValidation(type="list", formula1=f"={TEAM_LIST}", allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(cell)


# ---------------------------------------------------------------- Guide
gd = wb.create_sheet("Guide", 0)
gd.sheet_view.showGridLines = False
gd.column_dimensions["A"].width = 3
gd.column_dimensions["B"].width = 26
gd.column_dimensions["C"].width = 100
gd["B2"] = "MLB Hitter Monthly Tracker - 2026"
gd["B2"].font = title_f
gd["B3"] = "Emerson Jimenez | Emerson Performance (EP) | ejimenezperformance.github.io"
gd["B3"].font = sub_f
gd["B4"] = (f"Source: Baseball Savant Statcast Search, pitch-level, 2026 regular season, all 30 teams "
            f"({int(c.PA.sum()):,} PA, {c.batter.nunique()} hitters). A traded hitter appears once per team, "
            "counting only the PAs he took for that team. Late-March games are grouped into \"Mar-Apr\".")
gd["B4"].font = sub_f
r = 6
gd.cell(row=r, column=2, value="Tabs").font = h2
r += 1
for k, v in [
        ("Player Card", "Pick a team, then a hitter (yellow cells): every metric by month + season, with trend charts."),
        ("Team", "Pick a team: team offense by month next to the MLB season line."),
        ("Trend Grid", f"Pick a team: heat maps (hitters x months) for xwOBA, Barrel%, Chase% and Bat Speed. Hitters with {GRID_MIN_SEASON_PA}+ PA for that team."),
        ("Monthly Tracker", "Every team-hitter-month in MLB (use the filters). Each month vs. the hitter's season, with flags."),
        ("Signal Weights", "League-wide test: how much of a monthly change carries into the next month. Read this before acting on a flag."),
        ("Counts / Season Counts", "Hardcoded counting inputs from Statcast. Every other number in the workbook is a formula on these tabs.")]:
    gd.cell(row=r, column=2, value=k).font = bold
    gd.cell(row=r, column=3, value=v).font = body
    r += 1
r += 1
gd.cell(row=r, column=2, value="Key finding (all MLB hitters, 2026)").font = h2
r += 1
R = res.set_index("metric")
bs = R.loc["Bat Speed"]
lx = link.loc["xwOBA"]
conf = [m for m in R.index if R.loc[m, "persistence_label"] == "CONFIRMED"]
small = [m for m in R.index if R.loc[m, "persistence_note"].startswith("real but small")]
none_ = [m for m in R.index if R.loc[m, "persistence_note"].startswith("no evidence")]
lines = [f"Confirmed carry-over: {', '.join(conf) or 'none'}. Bat speed: {bs.persistence_b:.0%} of a month's change vs. the season line "
         f"showed up again the next month (95% CI {bs.b_ci_low:.2f} to {bs.b_ci_high:.2f}), {bs.persistence_label}."]
if none_:
    lines.append(f"{', '.join(none_)}: no evidence a hot or cold month carries over beyond what its sample size already explains. "
                 "The season line is the better guide; reacting fully to one month made next-month forecasts worse.")
if small:
    lines.append(f"{', '.join(small)}: a small real carry-over, below the 0.20 bar set in advance. Watch, don't act alone.")
lines.append(f"Bat speed vs. results: a slower-bat month {'came with' if lx.label == 'CONFIRMED' else 'did NOT come with'} a worse "
             f"next-month xwOBA ({lx.b_bs_per_mph * 1000:+.1f} points per mph, 95% CI {lx.b_ci_low * 1000:+.1f} to "
             f"{lx.b_ci_high * 1000:+.1f}; {lx.label}). Use a ▼ Bat Speed flag for workload and health checks, not as a production forecast.")
for line in lines:
    cl = gd.cell(row=r, column=3, value=line)
    cl.font, cl.alignment = body, Alignment(wrap_text=True, vertical="top")
    gd.row_dimensions[r].height = 28
    r += 1
r += 1
gd.cell(row=r, column=2, value="Flag thresholds (edit the yellow cells)").font = h2
r += 1
TH = {}
for key, label, val, fmt_, note in [
        ("minpa", "Min PA for a flag", 40, "0", 'Below this a month is marked "Low PA" (too noisy to act on).'),
        ("xw", "xwOBA change", 0.040, ".000", "Month xwOBA vs season xwOBA: ▲ Contact / ▼ Contact."),
        ("chase", "Chase% change", 0.040, "0.0%", "Month Chase% vs season: ▲ Chase / ▼ Chase."),
        ("bs", "Bat Speed change (mph)", 1.0, "0.0", "Month bat speed vs season: ▲ / ▼ Bat Speed. About 2 SD of a typical month vs. the season line."),
        ("gridpa", "Min PA per month in Trend Grid", 20, "0", "Hitter-months under this are left blank in the heat maps.")]:
    gd.cell(row=r, column=2, value=label).font = body
    cl = gd.cell(row=r, column=3, value=val)
    cl.font, cl.fill, cl.number_format, cl.alignment = blue, yellow, fmt_, Alignment(horizontal="left")
    cl.comment = Comment(note, "Emerson Jimenez")
    TH[key] = f"Guide!$C${r}"
    r += 1
gd.cell(row=r, column=2, value="Flags compare each month with the hitter's full season for that team (end-of-season view).").font = sub_f
r += 2
gd.cell(row=r, column=2, value="Glossary").font = h2
r += 1
for k, v in [
        ("wOBA / xwOBA", "Run value of outcomes / of contact quality (EV + LA, plus actual K/BB/HBP). Savant pitch-level weights; reached-on-error and fielder's choice count as outs."),
        ("xwOBA - wOBA", "Positive = results trailed the contact (bad luck). Negative = results outran the contact."),
        ("Barrel% / HardHit%", "Barrels (Statcast launch_speed_angle = 6) and 95+ mph batted balls, per batted-ball event."),
        ("SweetSpot%", "Batted balls with launch angle 8-32 degrees, per batted-ball event."),
        ("Chase% / Z-Swing%", "Swing rate on pitches outside the zone (zones 11-14) / inside the zone (zones 1-9)."),
        ("Whiff% / Z-Contact%", "Swinging strikes per swing (foul tips count as contact) / contact rate on in-zone swings."),
        ("Bat Speed", "Average of competitive swings = the fastest 90% of the hitter's 2026 swings (bunts excluded), as on Savant."),
        ("Fast-Swing%", "Competitive swings at 75+ mph."),
        ("Run Value", "Sum of Statcast delta run expectancy over every pitch the hitter saw (runs above average).")]:
    gd.cell(row=r, column=2, value=k).font = bold
    cl = gd.cell(row=r, column=3, value=v)
    cl.font, cl.alignment = body, Alignment(wrap_text=True)
    r += 1

# ---------------------------------------------------------------- Player Card
pc = wb.create_sheet("Player Card", 1)
pc.sheet_view.showGridLines = False
pc.column_dimensions["A"].width = 3
pc.column_dimensions["B"].width = 18
pc["B2"] = "Player Card"
pc["B2"].font = title_f
pc["B3"], pc["B4"] = "Team:", "Hitter:"
pc["B3"].font = pc["B4"].font = bold
team0 = teams[0]
team_picker(pc, "C3", team0)
pc["C4"] = season[season.team == team0].hitter.iloc[0]
pc["C4"].font, pc["C4"].fill = Font(name=F, size=12, bold=True, color="0000FF"), yellow
pc.merge_cells("C4:E4")
dvh = DataValidation(type="list", allow_blank=False,
                     formula1=f"=OFFSET(Lists!$D$1,MATCH($C$3,{LT},0)-1,0,COUNTIF({LT},$C$3),1)")
pc.add_data_validation(dvh)
dvh.add("C4")
pc["F3"] = "<- choose a team, then a hitter from that team"
pc["F3"].font = sub_f
pc["F4"] = f'=IF(COUNTIFS({LT},$C$3,{LH},$C$4)=0,"Hitter not on this team - pick again","")'
pc["F4"].font = Font(name=F, size=10, bold=True, color="C00000")
hdr(pc, 6, 2, "Metric")
for j, m in enumerate(MONTHS + ["Season"]):
    hdr(pc, 6, 3 + j, m, 10)
for i, (name, fmt_, _) in enumerate(METRICS):
    rr = 7 + i
    put(pc, rr, 2, name, font=bold, align=None)
    for j, m in enumerate(MONTHS + ["Season"]):
        if m == "Season":
            g = lambda k: f"SUMIFS({rng(k)},{rng('team')},$C$3,{rng('hitter')},$C$4)"
        else:
            g = (lambda mm: lambda k: f"SUMIFS({rng(k)},{rng('team')},$C$3,{rng('hitter')},$C$4,{rng('month')},\"{mm}\")")(m)
        put(pc, rr, 3 + j, fm(name, g), fmt_, font=bold if m == "Season" else body)
    if i % 2:
        for j in range(8):
            pc.cell(row=rr, column=2 + j).fill = band
pc.cell(row=8 + len(METRICS), column=2,
        value="Blank = no PA that month. Small monthly samples are noisy: read every rate with the PA row.").font = sub_f
line_chart(pc, [7 + MI["wOBA"], 7 + MI["xwOBA"]], 3, 8, 6, "wOBA vs xwOBA by month", "K6", ".000", 0.15)
line_chart(pc, [7 + MI["Chase%"], 7 + MI["Whiff%"], 7 + MI["K%"]], 3, 8, 6, "Swing decisions by month", "K21", "0%")
line_chart(pc, [7 + MI["Bat Speed"]], 3, 8, 6, "Bat speed (mph) by month", "K36", "0.0")

# ---------------------------------------------------------------- Team
tm = wb.create_sheet("Team", 2)
tm.sheet_view.showGridLines = False
tm.column_dimensions["A"].width = 3
tm.column_dimensions["B"].width = 18
tm["B2"] = "Team Offense by Month"
tm["B2"].font = title_f
tm["B3"] = "Team:"
tm["B3"].font = bold
team_picker(tm, "C3", team0)
hdr(tm, 5, 2, "Metric")
for j, m in enumerate(MONTHS + ["Season", "MLB"]):
    hdr(tm, 5, 3 + j, m, 10)
for i, (name, fmt_, _) in enumerate(METRICS):
    rr = 6 + i
    put(tm, rr, 2, name, font=bold, align=None)
    for j, m in enumerate(MONTHS + ["Season", "MLB"]):
        if m == "Season":
            g = lambda k: f"SUMIFS({rng(k)},{rng('team')},$C$3)"
        elif m == "MLB":
            g = lambda k: f"SUM({rng(k)})/30" if k in ("PA", "HR", "RunValue") else f"SUM({rng(k)})"
        else:
            g = (lambda mm: lambda k: f"SUMIFS({rng(k)},{rng('team')},$C$3,{rng('month')},\"{mm}\")")(m)
        put(tm, rr, 3 + j, fm(name, g), fmt_, font=bold if m in ("Season", "MLB") else body)
    if i % 2:
        for j in range(9):
            tm.cell(row=rr, column=2 + j).fill = band
tm.cell(row=7 + len(METRICS), column=2,
        value="MLB column: league season rates; PA, HR and Run Value shown per team (league total / 30).").font = sub_f
line_chart(tm, [6 + MI["wOBA"], 6 + MI["xwOBA"]], 3, 8, 5, "Team wOBA vs xwOBA by month", "M5", ".000", 0.25)

# ---------------------------------------------------------------- Trend Grid
tg = wb.create_sheet("Trend Grid", 3)
tg.sheet_view.showGridLines = False
tg.column_dimensions["A"].width = 3
tg["B2"] = "Trend Grid"
tg["B2"].font = title_f
tg["B3"] = "Team:"
tg["B3"].font = bold
team_picker(tg, "C3", team0)
tg["E3"] = (f"Hitters with {GRID_MIN_SEASON_PA}+ PA for the team, by PA. Gold = better than the group, navy = worse "
            "(Chase%: gold = more disciplined). Blank = under the monthly PA minimum on the Guide tab.")
tg["E3"].font = sub_f
blocks = [("xwOBA", ".000", "high"), ("Barrel%", "0.0%", "high"), ("Chase%", "0.0%", "low"), ("Bat Speed", "0.0", "high")]


def scale(direction):
    lo, hi = (NAVY, GOLD) if direction == "high" else (GOLD, NAVY)
    return ColorScaleRule(start_type="percentile", start_value=5, start_color=lo.replace(NAVY, "7F8DA3"),
                          mid_type="percentile", mid_value=50, mid_color="FFFFFF",
                          end_type="percentile", end_value=95, end_color=hi.replace(NAVY, "7F8DA3"))


r0 = 5
for name, fmt_, direction in blocks:
    tg.cell(row=r0, column=2, value=name).font = h2
    hdr(tg, r0 + 1, 2, "Hitter", 22)
    for j, m in enumerate(MONTHS + ["Season"]):
        hdr(tg, r0 + 1, 3 + j, m, 10)
    for i in range(GRID_ROWS):
        rr = r0 + 2 + i
        put(tg, rr, 2, f'=IF({i + 1}<=COUNTIF({GT},$C$3),INDEX({GH},MATCH($C$3,{GT},0)+{i}),"")',
            font=bold, align=None)
        for j, m in enumerate(MONTHS + ["Season"]):
            if m == "Season":
                g = (lambda R: lambda k: f"SUMIFS({rng(k)},{rng('team')},$C$3,{rng('hitter')},$B{R})")(rr)
                v = f'=IF($B{rr}="","",{fm(name, g)[1:]})'
            else:
                g = (lambda R, mm: lambda k: f"SUMIFS({rng(k)},{rng('team')},$C$3,{rng('hitter')},$B{R},{rng('month')},\"{mm}\")")(rr, m)
                v = (f'=IF($B{rr}="","",IF({g("PA")}<{TH["gridpa"]},"",'
                     f'IFERROR({METRICS[MI[name]][2](g)},"")))')
            put(tg, rr, 3 + j, v, fmt_, font=bold if m == "Season" else body)
    end = r0 + 1 + GRID_ROWS
    tg.conditional_formatting.add(f"C{r0 + 2}:H{end}", scale(direction))
    r0 = end + 3

# ---------------------------------------------------------------- Monthly Tracker
mt = wb.create_sheet("Monthly Tracker", 4)
mt.freeze_panes = "D2"
hdr(mt, 1, 1, "Team", 7)
hdr(mt, 1, 2, "Hitter", 20)
hdr(mt, 1, 3, "Month", 9)
for j, (name, _, _) in enumerate(METRICS):
    hdr(mt, 1, 4 + j, name, 11 if len(name) > 8 else 9)
base = 4 + len(METRICS)
extra = ["Season xwOBA", "Δ xwOBA", "Season Chase%", "Δ Chase%", "Season Bat Speed", "Δ Bat Speed", "Flags", "SC row"]
for j, e in enumerate(extra):
    hdr(mt, 1, base + j, e, 30 if e == "Flags" else 11)
mt.row_dimensions[1].height = 30
colof = {name: L(4 + j) for j, (name, _, _) in enumerate(METRICS)}
S = [L(base + j) for j in range(len(extra))]
ROWC = S[7]
scr = lambda k, R: f"INDEX('Season Counts'!${SC[k]}$2:${SC[k]}${NS},${ROWC}{R})"
for i in range(len(c)):
    rr = i + 2
    put(mt, rr, 1, f"=Counts!{CC['team']}{rr}", border=None)
    put(mt, rr, 2, f"=Counts!{CC['hitter']}{rr}", align=None, border=None)
    put(mt, rr, 3, f"=Counts!{CC['month']}{rr}", border=None)
    g = (lambda R: lambda k: f"Counts!{CC[k]}{R}")(rr)
    for j, (name, fmt_, _) in enumerate(METRICS):
        put(mt, rr, 4 + j, fm(name, g), fmt_, border=None)
    put(mt, rr, base + 7, f"=MATCH(Counts!{CC['key']}{rr},'Season Counts'!$A$2:$A${NS},0)", "0", border=None)
    gs = (lambda R: lambda k: scr(k, R))(rr)
    vals = [fm("xwOBA", gs), f'=IFERROR({colof["xwOBA"]}{rr}-{S[0]}{rr},"")',
            fm("Chase%", gs), f'=IFERROR({colof["Chase%"]}{rr}-{S[2]}{rr},"")',
            fm("Bat Speed", gs), f'=IFERROR({colof["Bat Speed"]}{rr}-{S[4]}{rr},"")']
    fmts = [".000", "+.000;-.000;.000", "0.0%", "+0.0%;-0.0%;0.0%", "0.0", "+0.0;-0.0;0.0"]
    for j, (v, f_) in enumerate(zip(vals, fmts)):
        put(mt, rr, base + j, v, f_, border=None)
    P = f"{colof['PA']}{rr}"
    dx, dc, db = f"N({S[1]}{rr})", f"N({S[3]}{rr})", f"N({S[5]}{rr})"
    inner = (f'TRIM(IF(ISNUMBER({S[5]}{rr}),IF({db}<=-{TH["bs"]},"▼ Bat Speed  ",IF({db}>={TH["bs"]},"▲ Bat Speed  ","")),"")&'
             f'IF({dx}>={TH["xw"]},"▲ Contact  ","")&IF({dx}<=-{TH["xw"]},"▼ Contact  ","")&'
             f'IF({dc}>={TH["chase"]},"▲ Chase  ","")&IF({dc}<=-{TH["chase"]},"▼ Chase  ",""))')
    put(mt, rr, base + 6, f'=IF({P}<{TH["minpa"]},"Low PA",IF({inner}="","Stable",{inner}))', font=bold,
        align=None, border=None)
mt.column_dimensions[ROWC].hidden = True
last = len(c) + 1
mt.auto_filter.ref = f"A1:{S[6]}{last}"
up = lambda: ColorScaleRule(start_type="percentile", start_value=5, start_color="7F8DA3", mid_type="percentile",
                            mid_value=50, mid_color="FFFFFF", end_type="percentile", end_value=95, end_color=GOLD)
down = lambda: ColorScaleRule(start_type="percentile", start_value=5, start_color=GOLD, mid_type="percentile",
                              mid_value=50, mid_color="FFFFFF", end_type="percentile", end_value=95, end_color="7F8DA3")
for name in ["AVG", "OBP", "SLG", "wOBA", "xwOBA", "BB%", "Barrel%", "HardHit%", "Avg EV", "SweetSpot%",
             "Z-Contact%", "Bat Speed", "Fast-Swing%", "Run Value"]:
    mt.conditional_formatting.add(f"{colof[name]}2:{colof[name]}{last}", up())
for name in ["K%", "Chase%", "Whiff%"]:
    mt.conditional_formatting.add(f"{colof[name]}2:{colof[name]}{last}", down())
fl = S[6]
mt.conditional_formatting.add(f"{fl}2:{fl}{last}", FormulaRule(formula=[f'ISNUMBER(SEARCH("Bat Speed",{fl}2))'],
                              font=Font(name=F, bold=True, color="C00000"), fill=PatternFill("solid", fgColor="FCE8C8")))
mt.conditional_formatting.add(f"{fl}2:{fl}{last}", FormulaRule(formula=[f'{fl}2="Low PA"'],
                              font=Font(name=F, italic=True, color="999999")))

# ---------------------------------------------------------------- Signal Weights
sw = wb.create_sheet("Signal Weights", 5)
sw.sheet_view.showGridLines = False
sw.column_dimensions["A"].width = 3
sw["B2"] = "How much should a monthly flag move us? (all MLB hitters, 2026)"
sw["B2"].font = title_f
sw["B3"] = ("Persistence = share of a month's change vs. the season line that showed up again the next month, beyond what "
            "the month's sample size already explains (0 = the month is just more data). Player-clustered bootstrap CIs, "
            "Benjamini-Hochberg q-values; CONFIRMED = q < 0.05 and persistence >= 0.20 (set before the run).")
sw["B3"].font = sub_f
sw.merge_cells("B3:L3")
sw["B3"].alignment = Alignment(wrap_text=True, vertical="top")
sw.row_dimensions[3].height = 42
heads = ["Metric", "Pairs", "Hitters", "Persistence", "CI low", "CI high", "q-value", "Label", "What it means",
         "Forecast gain vs. no extra reaction", "Error of reacting fully vs. none"]
widths = [12, 8, 8, 11, 8, 8, 9, 16, 38, 16, 16]
for j, (h, w) in enumerate(zip(heads, widths)):
    hdr(sw, 5, 2 + j, h, w)
sw.row_dimensions[5].height = 44
for i, x in enumerate(res.itertuples(index=False)):
    vals = [x.metric, int(x.pairs), int(x.hitters), x.persistence_b, x.b_ci_low, x.b_ci_high, x.q_value,
            x.persistence_label, x.persistence_note, x.gain_pct, x.mae_full_reaction / x.mae_no_reaction - 1]
    fmts = ["@", "0", "0", "0.00", "0.00", "0.00", "0.000", "@", "@", "+0.0%;-0.0%;0.0%", "+0%;-0%;0%"]
    for j, (v, f_) in enumerate(zip(vals, fmts)):
        put(sw, 6 + i, 2 + j, v, f_, font=blue, align=Alignment(horizontal="left") if j == 8 else mid)
nb = 7 + len(res)
sw.cell(row=nb, column=2, value=("Reading a flag: expected next-month change = persistence x this month's change. "
        f"Example: a hitter 1.0 mph below his season bat speed -> expect about {bs.persistence_b:.1f} mph below next month "
        "(on top of the league-wide seasonal drift).")).font = body
sw.cell(row=nb + 1, column=2, value=lines[-1]).font = bold
sw.cell(row=nb + 2, column=2, value="Blue = hardcoded from results/persistence_and_projection.csv; rerun the pipeline to refresh.").font = sub_f

# ---------------------------------------------------------------- Counts / Season Counts
for title, frame, cols, ref in [("Counts", c, CCOLS, CC), ("Season Counts", season, SCOLS, SC)]:
    ws = wb.create_sheet(title)
    ws.freeze_panes = "B2"
    for j, k in enumerate(cols):
        hdr(ws, 1, j + 1, k, 22 if k in ("key", "hitter") else 10)
    for i, row in enumerate(frame[cols].itertuples(index=False), start=2):
        for j, v in enumerate(row, start=1):
            if isinstance(v, float):
                v = round(v, 3) if not v.is_integer() else int(v)
            ws.cell(row=i, column=j, value=v).font = blue
    ws["A1"].comment = Comment("Hardcoded counting inputs aggregated from Baseball Savant pitch-level Statcast data "
                               "(2026 regular season) by src/build_counts.py.", "Emerson Jimenez")

tabs = {"Guide": GOLD, "Signal Weights": GOLD}
for ws in wb.worksheets:
    ws.sheet_properties.tabColor = tabs.get(ws.title, NAVY if ws.title not in ("Counts", "Season Counts") else GRAY)
wb.active = 1
wb.calculation.fullCalcOnLoad = True  # Excel computes every formula when the file opens
OUT.parent.mkdir(exist_ok=True)
wb.save(OUT)
print(f"saved {OUT.name}: {len(c)} team-hitter-months, {len(season)} team-hitters, {len(teams)} teams, grid rows {GRID_ROWS}")
