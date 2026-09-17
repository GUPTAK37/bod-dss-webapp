"""Filter-domain helpers.

Ports the `_domain`, `_relevant_domain`, `_run_group_cascade`, and
`_date_extents` functions from `bod_app.layouts.bod` with Dash bits stripped
out. Same SQL, same caching semantics.
"""

from __future__ import annotations

import logging
from datetime import date

import pandas as pd

from .db import FACT_TABLE, run_query


log = logging.getLogger(__name__)

ALL_SENTINEL = "__ALL__"

_DOMAIN_CACHE: dict = {}
_RELEVANT_CACHE: dict = {}


def domain(col: str, expr: str | None = None,
           top_n: int | None = None) -> list[str]:
    cache_key = (expr or col, top_n)
    if cache_key in _DOMAIN_CACHE:
        return _DOMAIN_CACHE[cache_key]

    select_expr = expr if expr else col
    where_extra = ""
    if col.upper() != "HIGH_RISK_CONDITION":
        where_extra = "  AND HIGH_RISK_CONDITION = 'ALL HR CONDITIONS' "
    if top_n:
        order_by, limit_clause = "COUNT(*) DESC", f" LIMIT {int(top_n)}"
    else:
        order_by, limit_clause = "1", ""
    try:
        df = run_query(
            f"SELECT {select_expr} AS V, COUNT(*) AS N FROM {FACT_TABLE} "
            f"WHERE MEDICAL_PATIENT_COHORT_FLAG = 1 "
            f"  AND INCOMPLETE_EPISODE_FLAG = 0 "
            f"  AND EPISODE_PER_QUARTER_FLAG = '1' "
            f"{where_extra}"
            f"  AND {select_expr} IS NOT NULL "
            f"GROUP BY 1 ORDER BY {order_by}{limit_clause}"
        )
        vals = [str(v) for v in df["V"].tolist()]
        if top_n:
            vals = sorted(vals)
        _DOMAIN_CACHE[cache_key] = vals
    except Exception:
        log.exception("Domain fetch failed for %s", col)
        _DOMAIN_CACHE[cache_key] = []
    return _DOMAIN_CACHE[cache_key]


def relevant_domain(col: str, expr: str | None = None, *,
                    context: dict[str, list[str]] | None = None,
                    time_range: tuple | None = None,
                    top_n: int | None = None) -> list[str]:
    key = (
        col, expr,
        tuple(sorted((k, tuple(sorted(v))) for k, v in (context or {}).items())),
        time_range, top_n,
    )
    if key in _RELEVANT_CACHE:
        return _RELEVANT_CACHE[key]

    select_expr = expr if expr else col
    parts = [
        "MEDICAL_PATIENT_COHORT_FLAG = 1",
        "INCOMPLETE_EPISODE_FLAG = 0",
        "EPISODE_PER_QUARTER_FLAG = '1'",
        f"{select_expr} IS NOT NULL",
    ]
    if col.upper() != "HIGH_RISK_CONDITION":
        parts.append("HIGH_RISK_CONDITION = 'ALL HR CONDITIONS'")
    binds: dict = {}
    if time_range is not None and time_range[0] is not None and time_range[1] is not None:
        binds["start_month"] = time_range[0]
        binds["end_month"] = time_range[1]
        parts.append(
            "EPISODE_START_DATE >= %(start_month)s "
            "AND EPISODE_START_DATE < DATEADD(month, 1, %(end_month)s)"
        )
    for i, (ctx_col, ctx_vals) in enumerate((context or {}).items()):
        clean = [v for v in (ctx_vals or []) if v not in (ALL_SENTINEL, "(All)")]
        if not clean:
            continue
        ph = []
        for j, v in enumerate(clean):
            k = f"ctx{i}_{j}"
            binds[k] = v
            ph.append(f"%({k})s")
        parts.append(f"{ctx_col} IN ({', '.join(ph)})")
    if top_n:
        order_by, limit_clause = "COUNT(*) DESC", f" LIMIT {int(top_n)}"
        sql = (f"SELECT {select_expr} AS V, COUNT(*) AS N FROM {FACT_TABLE} "
               f"WHERE " + " AND ".join(parts) +
               f" GROUP BY 1 ORDER BY {order_by}{limit_clause}")
    else:
        sql = (f"SELECT DISTINCT {select_expr} AS V FROM {FACT_TABLE} "
               f"WHERE " + " AND ".join(parts) + " ORDER BY 1")
    try:
        df = run_query(sql, binds)
        vals = [str(v) for v in df["V"].tolist() if v is not None]
        if top_n:
            vals = sorted(vals)
    except Exception:
        log.exception("Relevant-domain query failed for %s", col)
        vals = list(domain(col, expr=expr, top_n=top_n))
    _RELEVANT_CACHE[key] = vals
    return vals


def date_extents() -> tuple[date, date, list[int]]:
    key = "__DATE_EXTENTS__"
    if key in _DOMAIN_CACHE:
        return _DOMAIN_CACHE[key]
    try:
        df = run_query(
            f"SELECT MIN(EPISODE_START_DATE::date) AS MIN_D, "
            f"       MAX(EPISODE_START_DATE::date) AS MAX_D "
            f"FROM {FACT_TABLE} "
            f"WHERE MEDICAL_PATIENT_COHORT_FLAG = 1 "
            f"  AND INCOMPLETE_EPISODE_FLAG = 0 "
            f"  AND EPISODE_PER_QUARTER_FLAG = '1' "
            f"  AND HIGH_RISK_CONDITION = 'ALL HR CONDITIONS'"
        )
        min_d = pd.to_datetime(df.iloc[0, 0]).date()
        max_d = pd.to_datetime(df.iloc[0, 1]).date()
        years = list(range(min_d.year, max_d.year + 1))
        _DOMAIN_CACHE[key] = (min_d, max_d, years)
    except Exception:
        log.exception("date_extents query failed")
        _DOMAIN_CACHE[key] = (date(2024, 1, 1), date(2026, 12, 1), [2024, 2025, 2026])
    return _DOMAIN_CACHE[key]


def run_group_cascade(group: list[tuple], selections: dict, currents: dict) -> dict:
    """Return `{fid: {"options": [...], "value": [...]}}` for each filter.

    `group` = list of `(filter-id, physical-col, calc-expr, top_n_cap)`.
    `selections[fid]` = the SQL-facing value list.
    `currents[fid]`   = the currently-checked value list (with __ALL__ sentinel).
    """
    out: dict = {}
    for fid, phys, expr, cap in group:
        context: dict[str, list[str]] = {}
        for fid2, phys2, expr2, _ in group:
            if fid2 == fid:
                continue
            clean = [v for v in (selections.get(fid2) or []) if v not in (ALL_SENTINEL, "(All)")]
            if clean:
                context[expr2 or phys2] = clean
        try:
            vals = relevant_domain(phys, expr=expr, context=context, top_n=cap)
        except Exception:
            vals = domain(phys, expr=expr, top_n=cap)
        if phys == "HIGH_RISK_CONDITION":
            vals = [v for v in vals if v != "ALL HR CONDITIONS"]

        prev = currents.get(fid) or []
        prev_real = [v for v in prev if v not in (ALL_SENTINEL,)]
        still_valid = [v for v in prev_real if v in vals]
        all_was_checked = ALL_SENTINEL in prev or (prev_real and vals and len(prev_real) >= len(vals))
        if all_was_checked or not still_valid:
            new_value = [ALL_SENTINEL] + vals
        elif len(still_valid) == len(vals):
            new_value = [ALL_SENTINEL] + vals
        else:
            new_value = still_valid
        out[fid] = {"options": vals, "value": new_value}
    return out
