"""Section renderers.

For each section id (`s1`..`s10`), run the SQL query builder from
`bod_app.data.queries`, feed the returned DataFrame to the existing Plotly
figure factory in `bod_app.charts.theme`, and produce a table spec JSON that
the React `MatrixTable` / `GroupedMatrixTable` components render.

The chart is returned as `figure.to_plotly_json()` so React can hand it
straight to `react-plotly.js`.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd
import plotly.io as pio

from bod_app.charts import theme as th
from bod_app.data import queries as Q
from bod_app.data.params import BoDFilters, ENCOUNTER_WINDOWS

from .db import run_query

log = logging.getLogger(__name__)


# ---- Cell formatters (ported from bod_app/layouts/bod.py) -------------------

def _i(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "\u2014"
    try:
        return f"{int(v):,}"
    except Exception:
        return str(v)


def _pct(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "\u2014"
    return f"{v:.0%}"


def _bucket_labels(df: pd.DataFrame, level: str) -> list[str]:
    def fmt(d):
        d = pd.to_datetime(d)
        if level == "month":
            return d.strftime("%b %Y")
        if level == "year":
            return d.strftime("%Y")
        return f"Q{(d.month - 1) // 3 + 1} {d.year}"
    return [fmt(x) for x in df["TIME_BUCKET"]]


def _pretty_visit(v: str) -> str:
    mapping = {
        "ED VISIT": "ED",
        "OFFICE VISIT": "Office",
        "TELEHEALTH VISIT": "Telehealth",
        "UC VISIT": "UC",
        "LTAC/SNF VISIT": "LTAC/SNF",
        "HOSPITALIZATION": "Hospitalization",
    }
    return mapping.get(v, v.title())


# ---- Table spec builders ----------------------------------------------------

def _matrix(columns, rows, first_col_highlight: bool = False) -> dict:
    return {
        "type": "matrix",
        "columns": list(columns),
        "rows": [{"label": lbl, "values": list(vals)} for lbl, vals in rows],
        "first_col_highlight": bool(first_col_highlight),
    }


def _grouped(groups, subcols, rows, first_group_highlight: bool = False) -> dict:
    return {
        "type": "grouped_matrix",
        "groups": list(groups),
        "subcols": list(subcols),
        "rows": [{"label": lbl, "values": list(vals)} for lbl, vals in rows],
        "first_group_highlight": bool(first_group_highlight),
    }


def _empty_table() -> dict:
    return {"type": "empty"}


def _fig_json(fig) -> dict:
    """Convert a Plotly Figure to a JSON-serialisable dict.

    Uses `plotly.io.to_json` (which handles numpy arrays, datetime64, etc.)
    then re-parses back into a dict so FastAPI's default JSON serializer never
    encounters raw numpy types.

    Also normalises the layout so bar centres line up EXACTLY with the
    value-column centres of the HTML table underneath:
       * `margin.l` = 300px  (matches `.bod-table td.row-label { width: 300px }`)
       * `margin.r` = 0px    (matches the table's last-column right edge)
       * yaxis `automargin` disabled so wide tick labels don't push the plot
         area right.
       * xaxis range pinned to `[-0.5, N-0.5]` so category centres are at
         integer positions with no extra padding.
    Top/bottom margins are preserved from the source figure.
    """
    if fig is None:
        fig = th._empty_figure()
    d = json.loads(pio.to_json(fig, validate=False))
    layout = d.setdefault("layout", {})
    margin = layout.get("margin") or {}
    layout["margin"] = {
        "l": 300,
        "r": 0,
        "t": margin.get("t", 8),
        "b": margin.get("b", 8),
    }
    layout.setdefault("yaxis", {})
    layout["yaxis"]["automargin"] = False

    # Pin xaxis range so category centres never drift due to axis padding.
    # Uses the first trace's `x` array length to determine N.
    traces = d.get("data") or []
    n = 0
    for tr in traces:
        xs = tr.get("x") or []
        if len(xs) > n:
            n = len(xs)
    if n > 0:
        layout.setdefault("xaxis", {})
        layout["xaxis"]["range"] = [-0.5, n - 0.5]
        layout["xaxis"]["automargin"] = False
    return d


# ---- Per-section renderers --------------------------------------------------

def _render_s1(df, f):
    if df is None or df.empty:
        return _fig_json(th._empty_figure()), _empty_table()
    labels = _bucket_labels(df, f.time_level)
    fig = th.followup_stacked(df, x_col="TIME_BUCKET", x_labels=labels)
    rows = [
        ("# Total Episodes", [_i(v) for v in df["TOTAL_EPISODES"]]),
        ("# Episodes with No Follow-Up Visit of Interest",
         [_i(v) for v in df["EPISODES_NO_FOLLOWUP"]]),
        ("% Episodes with No Follow-Up Visit of Interest",
         [_pct(v) for v in (df["EPISODES_NO_FOLLOWUP"] / df["TOTAL_EPISODES"])]),
        ("# Episodes with Follow-Up Visits",
         [_i(v) for v in df["EPISODES_WITH_FOLLOWUP"]]),
        ("% Episodes with Follow-Up Visits",
         [_pct(v) for v in df["PCT_FOLLOWUP"]]),
        ("# Follow-Up Visits", [_i(v) for v in df["TOTAL_FOLLOWUP_VISITS"]]),
    ]
    return _fig_json(fig), _matrix(labels, rows)


def _render_s2(df, f):
    if df is None or df.empty:
        return _fig_json(th._empty_figure()), _empty_table()
    fig = th.followup_stacked(df, x_col="COHORT")
    labels = df["COHORT"].tolist()
    grand_total = int(df["TOTAL_EPISODES"].sum()) or 1
    rows = [
        ("# Total Episodes (% treated or untreated)",
         [f"{_i(v)} ({int(v)/grand_total:.0%})" for v in df["TOTAL_EPISODES"]]),
        ("# Episodes with No Follow-Up Visit of Interest",
         [_i(v) for v in df["EPISODES_NO_FOLLOWUP"]]),
        ("% Episodes with No Follow-Up Visit of Interest",
         [_pct(v) for v in (df["EPISODES_NO_FOLLOWUP"] / df["TOTAL_EPISODES"])]),
        ("# Episodes with Follow-Up Visits",
         [_i(v) for v in df["EPISODES_WITH_FOLLOWUP"]]),
        ("% Episodes with Follow-Up Visits",
         [_pct(v) for v in df["PCT_FOLLOWUP"]]),
        ("# Follow-Up Visits", [_i(v) for v in df["TOTAL_FOLLOWUP_VISITS"]]),
    ]
    return _fig_json(fig), _matrix(labels, rows)


def _render_s3(df, f):
    if df is None or df.empty:
        return _fig_json(th._empty_figure()), _empty_table()
    df = df.copy()
    df["LABEL"] = _bucket_labels(df, f.time_level)
    quarters = list(dict.fromkeys(df["LABEL"].tolist()))
    fig = th.followup_stacked_grouped_by_cohort(df, bucket_col="LABEL", bucket_labels=quarters)
    cohorts = ["Treated", "Untreated"]
    df_i = df.set_index(["LABEL", "COHORT"])

    def col_vals(col):
        return [df_i.loc[(q, c), col] if (q, c) in df_i.index else 0
                for q in quarters for c in cohorts]

    per_q = df.groupby("LABEL")["TOTAL_EPISODES"].sum().to_dict()
    total_cells = []
    for q in quarters:
        qt = per_q[q] or 1
        for c in cohorts:
            v = df_i.loc[(q, c), "TOTAL_EPISODES"] if (q, c) in df_i.index else 0
            total_cells.append(f"{_i(v)} ({int(v)/qt:.0%})")

    rows = [
        ("# Total Episodes (% treated or untreated)", total_cells),
        ("# Episodes with No Follow-Up Visit of Interest",
         [_i(v) for v in col_vals("EPISODES_NO_FOLLOWUP")]),
        ("% Episodes with No Follow-Up Visit of Interest",
         [_pct(a / b) if b else "\u2014"
          for a, b in zip(col_vals("EPISODES_NO_FOLLOWUP"), col_vals("TOTAL_EPISODES"))]),
        ("# Episodes with Follow-Up Visits",
         [_i(v) for v in col_vals("EPISODES_WITH_FOLLOWUP")]),
        ("% Episodes with Follow-Up Visits",
         [_pct(v) for v in col_vals("PCT_FOLLOWUP")]),
        ("# Follow-Up Visits",
         [_i(v) for v in col_vals("TOTAL_FOLLOWUP_VISITS")]),
    ]
    return _fig_json(fig), _grouped(quarters, cohorts, rows)


def _render_s4(df, f):
    if df is None or df.empty:
        return _fig_json(th._empty_figure()), _empty_table()
    df = df.copy()
    df["LABEL"] = _bucket_labels(df, f.time_level)
    quarters = list(dict.fromkeys(df["LABEL"].tolist()))
    cohorts = ["Treated", "Untreated"]
    fig = th.avg_visits_grouped(df, bucket_labels=quarters)

    df_i = df.set_index(["LABEL", "COHORT"])

    def col_vals(col):
        return [df_i.loc[(q, c), col] if (q, c) in df_i.index else 0
                for q in quarters for c in cohorts]

    per_q = df.groupby("LABEL")["TOTAL_EPISODES"].sum().to_dict()
    total_cells = []
    for q in quarters:
        qt = per_q[q] or 1
        for c in cohorts:
            v = df_i.loc[(q, c), "TOTAL_EPISODES"] if (q, c) in df_i.index else 0
            total_cells.append(f"{_i(v)} ({int(v)/qt:.0%})")

    rows = [
        ("# Total Episodes (% treated or untreated)", total_cells),
        ("# Episodes with Follow-Up Visits",
         [_i(v) for v in col_vals("EPISODES_WITH_FOLLOWUP")]),
        ("# Follow-Up Visits",
         [_i(v) for v in col_vals("TOTAL_FOLLOWUP_VISITS")]),
        ("Average # Follow-Up Visits per Total Episodes",
         [f"{v:.1f}" if v else "\u2014" for v in col_vals("AVG_VISITS_PER_EPISODE")]),
    ]
    return _fig_json(fig), _grouped(quarters, cohorts, rows)


def _render_visit_mix(df, f, *, group_by_cohort, group_by_bucket):
    if df is None or df.empty:
        return _fig_json(th._empty_figure()), _empty_table()
    df = df.copy()
    if "VISIT_TYPE" in df.columns and "VISIT" not in df.columns:
        df = df.rename(columns={"VISIT_TYPE": "VISIT"})

    if group_by_bucket:
        df["LABEL"] = _bucket_labels(df, f.time_level)
        quarters = list(dict.fromkeys(df["LABEL"].tolist()))
    else:
        quarters = None

    if group_by_bucket and group_by_cohort:
        cohorts = ["Treated", "Untreated"]
        x_labels = [f"{q}|{c}" for q in quarters for c in cohorts]
        key_cols = ["LABEL", "COHORT"]
        df["_XKEY"] = df["LABEL"].astype(str) + "|" + df["COHORT"].astype(str)
    elif group_by_bucket:
        cohorts = None
        x_labels = quarters
        key_cols = ["LABEL"]
        df["_XKEY"] = df["LABEL"].astype(str)
    else:
        cohorts = ["Treated", "Untreated"]
        x_labels = cohorts
        key_cols = ["COHORT"]
        df["_XKEY"] = df["COHORT"].astype(str)

    fig = th.visit_mix_stacked(df, x_labels=x_labels, key_cols=key_cols)

    TABLE_ORDER = ["HOSPITALIZATION", "ED VISIT", "UC VISIT",
                   "LTAC/SNF VISIT", "OFFICE VISIT", "TELEHEALTH VISIT",
                   "PHARMACY", "OTHERS"]
    DISPLAY_NAMES = {
        "HOSPITALIZATION": "# Hospitalizations", "ED VISIT": "# ED Visits",
        "UC VISIT": "# UC Visits", "LTAC/SNF VISIT": "# LTAC/SNF Visits",
        "OFFICE VISIT": "# Office Visits", "TELEHEALTH VISIT": "# Telehealth Visits",
        "PHARMACY": "# Pharmacy", "OTHERS": "# Others",
    }
    visit_types = [v for v in TABLE_ORDER if v in df["VISIT"].unique()]
    visit_types += [v for v in df["VISIT"].unique() if v not in visit_types]

    pivot = df.pivot_table(index="VISIT", columns="_XKEY", values="N_VISITS",
                           aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(index=visit_types, columns=x_labels, fill_value=0)

    totals_df = (df.groupby("_XKEY")[["TOTAL_EPISODES", "TOTAL_FOLLOWUP_VISITS"]]
                   .first().reindex(x_labels, fill_value=0))
    total_ep = totals_df["TOTAL_EPISODES"].tolist()
    total_fu = totals_df["TOTAL_FOLLOWUP_VISITS"].tolist()

    if group_by_cohort:
        if group_by_bucket:
            def denom_for(x):
                q = x.split("|", 1)[0]
                return sum(v for lbl, v in zip(x_labels, total_ep)
                           if lbl.split("|", 1)[0] == q) or 1
            total_ep_cells = [f"{_i(v)} ({int(v)/denom_for(lbl):.0%})"
                              for lbl, v in zip(x_labels, total_ep)]
        else:
            denom = sum(total_ep) or 1
            total_ep_cells = [f"{_i(v)} ({int(v)/denom:.0%})" for v in total_ep]
        total_label = "# Total Episodes (% treated or untreated)"
    else:
        total_ep_cells = [_i(v) for v in total_ep]
        total_label = "# Total Episodes"

    rows = [(total_label, total_ep_cells),
            ("# Follow-up Visits", [_i(v) for v in total_fu])]
    for v in visit_types:
        rows.append((DISPLAY_NAMES.get(v, f"# {v.title()}"),
                     [_i(x) for x in pivot.loc[v].tolist()]))

    if group_by_bucket and group_by_cohort:
        return _fig_json(fig), _grouped(quarters, cohorts, rows)
    if group_by_bucket:
        return _fig_json(fig), _matrix(quarters, rows)
    return _fig_json(fig), _matrix(cohorts, rows)


def _render_s5(df, f): return _render_visit_mix(df, f, group_by_cohort=False, group_by_bucket=True)
def _render_s6(df, f): return _render_visit_mix(df, f, group_by_cohort=True,  group_by_bucket=False)
def _render_s7(df, f): return _render_visit_mix(df, f, group_by_cohort=True,  group_by_bucket=True)


def _render_s8(df, f):
    if df is None or df.empty:
        return _fig_json(th._empty_figure()), _empty_table()
    df = df.copy().reset_index(drop=True)
    fig = th.hr_condition_bar(df)

    if f.s8_visit_types:
        visit_lbl = _pretty_visit(f.s8_visit_types[0]) if len(f.s8_visit_types) == 1 else "Selected"
    else:
        visit_lbl = ""
    row1 = ("# Episodes with " + (visit_lbl + " " if visit_lbl else "") + "Follow-Up Visits").replace("  ", " ")

    hr_names = df["HIGH_RISK_CONDITION"].tolist()
    ref_header = (f.s8_visit_types[0] if len(f.s8_visit_types) == 1
                  else ("All Visits" if not f.s8_visit_types else "Selected"))
    columns = [ref_header] + hr_names[1:]

    ref_ep = float(df["N_EPISODES_WITH_FU"].iloc[0] or 0)
    ref_fu = float(df["N_FOLLOWUP_VISITS"].iloc[0] or 0)

    def cell(v, ref, is_ref):
        if is_ref:
            return _i(v)
        return f"{_i(v)} ({(v/ref if ref else 0):.0%})"

    row_ep = [cell(v, ref_ep, i == 0) for i, v in enumerate(df["N_EPISODES_WITH_FU"])]
    row_fu = [cell(v, ref_fu, i == 0) for i, v in enumerate(df["N_FOLLOWUP_VISITS"])]

    return _fig_json(fig), _matrix(columns, [
        (row1, row_ep), ("# Follow-Up Visits", row_fu),
    ], first_col_highlight=True)


def _render_s9(df, f):
    if df is None or df.empty:
        return _fig_json(th._empty_figure()), _empty_table()
    df = df.copy().reset_index(drop=True)

    hr_order = []
    for h in df["HIGH_RISK_CONDITION"]:
        if h not in hr_order:
            hr_order.append(h)

    fig = th.hr_condition_by_cohort_bar(df, hr_order=hr_order)

    ref_header = (f.s8_visit_types[0] if len(f.s8_visit_types) == 1
                  else ("All Visits" if not f.s8_visit_types else "Selected"))
    top_headers = [ref_header] + [h for h in hr_order[1:]]
    cohorts = ["Treated", "Untreated"]

    if f.s8_visit_types:
        visit_lbl = _pretty_visit(f.s8_visit_types[0]) if len(f.s8_visit_types) == 1 else "Selected"
    else:
        visit_lbl = ""
    row1 = ("# Episodes with " + (visit_lbl + " " if visit_lbl else "") + "Follow-Up Visits").replace("  ", " ")

    idx = df.set_index(["HIGH_RISK_CONDITION", "COHORT"])

    def col_vals(col):
        out = []
        for h in hr_order:
            for c in cohorts:
                out.append(float(idx.loc[(h, c), col]) if (h, c) in idx.index else 0.0)
        return out

    ep_vals = col_vals("N_EPISODES_WITH_FU")
    fu_vals = col_vals("N_FOLLOWUP_VISITS")

    def with_pct(vals):
        cells = []
        for i in range(0, len(vals), 2):
            t, u = vals[i], vals[i + 1]
            total = t + u
            cells.append(f"{_i(t)} ({(t/total if total else 0):.0%})")
            cells.append(f"{_i(u)} ({(u/total if total else 0):.0%})")
        return cells

    return _fig_json(fig), _grouped(top_headers, cohorts, [
        (row1, with_pct(ep_vals)),
        ("# Follow-Up Visits", with_pct(fu_vals)),
    ], first_group_highlight=True)


def _render_s10(df, f):
    if df is None or df.empty:
        return _fig_json(th._empty_figure()), _empty_table()
    df = df.copy()
    df["LABEL"] = _bucket_labels(df, f.time_level)
    quarters = list(dict.fromkeys(df["LABEL"].tolist()))

    fig = th.visit_mix_stacked(
        df, x_labels=quarters, key_cols=["LABEL"], value_col="N_EPISODES",
        yaxis_title="% COVID-19 Initial Diagnosis/Treatment Location",
    )

    pivot = df.pivot_table(index="VISIT", columns="LABEL", values="N_EPISODES",
                           aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(columns=quarters, fill_value=0)
    totals = pivot.sum(axis=0)

    ordered = [v for v in reversed(th.VISIT_STACK_ORDER) if v in pivot.index]
    ordered += [v for v in pivot.index if v not in ordered]

    rows = [("Total # Episodes with Covid-19 Initial Diagnosis/Treatment Location",
             [_i(v) for v in totals.tolist()])]
    for visit in ordered:
        rows.append((f"# {visit}", [_i(x) for x in pivot.loc[visit].tolist()]))
    return _fig_json(fig), _matrix(quarters, rows)


_SECTION_REGISTRY = {
    "s1":  (Q.q_s1_episodes_by_bucket,        _render_s1),
    "s2":  (Q.q_s2_episodes_by_cohort,        _render_s2),
    "s3":  (Q.q_s3_episodes_by_bucket_cohort, _render_s3),
    "s4":  (Q.q_s4_avg_visits_per_episode,    _render_s4),
    "s5":  (Q.q_s5_visit_mix_by_bucket,       _render_s5),
    "s6":  (Q.q_s6_visit_mix_by_cohort,       _render_s6),
    "s7":  (Q.q_s7_visit_mix_by_bucket_cohort,_render_s7),
    "s8":  (Q.q_s8_hr_conditions,             _render_s8),
    "s9":  (Q.q_s9_hr_conditions_by_cohort,   _render_s9),
    "s10": (Q.q_s10_covid_dx_location,        _render_s10),
}


def render_section(section_id: str, f: BoDFilters) -> dict:
    if section_id not in _SECTION_REGISTRY:
        return {"error": f"Unknown section '{section_id}'"}
    query_fn, render_fn = _SECTION_REGISTRY[section_id]

    try:
        sql, binds = query_fn(f)
    except Exception as exc:
        log.exception("SQL build failed for %s", section_id)
        return {"error": f"SQL build error: {exc}",
                "figure": _fig_json(th._empty_figure(f"SQL build error: {exc}")),
                "table": _empty_table()}
    try:
        df = run_query(sql, binds)
    except Exception as exc:
        log.exception("Query failed for %s", section_id)
        return {"error": str(exc), "sql": sql[:400],
                "figure": _fig_json(th._empty_figure(f"Query error: {exc}")),
                "table": _empty_table()}

    fig_json, table = render_fn(df, f)

    # Sub-header pills.
    tp = f"Time Period: {f.start_month:%B %Y} - {f.end_month:%B %Y}"
    win = f"Follow-up Visit Window: {ENCOUNTER_WINDOWS[f.encounter_window]}"
    eps_lines = []
    try:
        hc = run_query(*Q.q_headline_counts(f))
        eps_val = int(hc.iloc[0, 0])
        eps_lines.append(f"#Episodes: {eps_val:,}")
    except Exception:
        pass
    if "TOTAL_FOLLOWUP_VISITS" in getattr(df, "columns", []):
        group_cols = [c for c in ("TIME_BUCKET", "COHORT") if c in df.columns]
        if group_cols and ("VISIT" in df.columns or "VISIT_TYPE" in df.columns):
            fu_total = int(df.drop_duplicates(group_cols)["TOTAL_FOLLOWUP_VISITS"].sum())
        else:
            fu_total = int(df["TOTAL_FOLLOWUP_VISITS"].sum())
        eps_lines.append(f"#Follow-up Visits: {fu_total:,}")

    return {
        "figure": fig_json,
        "table": table,
        "subheader": {"timeperiod": tp, "window": win, "episodes": eps_lines},
    }
