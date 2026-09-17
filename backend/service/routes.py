"""FastAPI API routes.

Single `APIRouter` mounted at `/api` by `setup.py`. Combines what were
three separate blueprints in the flat `bod_webapp` layout:

    /api/health
    /api/me
    /api/refresh-date
    /api/date-extents
    /api/filter-options
    /api/filter-cascade
    /api/hr-top7
    /api/section/{sid}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from bod_app.data import queries as Q
from bod_app.data.params import (
    CHILD_ACCOUNT_EXPR, GENDER_EXPR, PARENT_ACCOUNT_EXPR,
    PROVIDER_PRIMARY_SPECIALTY_EXPR, PROVIDER_SPECIALTY_GROUP_EXPR,
    granularity_value_expr,
)

from .db import run_query
from .domains import date_extents, domain, run_group_cascade
from .filters import from_payload
from .identity import get_current_user
from .renderers import render_section

router = APIRouter()


# ---------- Meta -----------------------------------------------------------

@router.get("/health")
def health():
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    """Return the signed-in DSS user (resolved from browser headers)."""
    return get_current_user(request.headers)


@router.get("/refresh-date")
def refresh_date():
    try:
        df = run_query(*Q.q_data_refresh_date())
        d = str(df.iloc[0, 0])[:10]
    except Exception as exc:  # noqa: BLE001
        return {"date": None, "error": str(exc)}
    return {"date": d}


@router.get("/date-extents")
def date_extents_route():
    min_d, max_d, years = date_extents()
    return {
        "min_date": min_d.isoformat(),
        "max_date": max_d.isoformat(),
        "years": years,
    }


# ---------- Filter option domains + cascade --------------------------------

_DATA_GROUP = [
    ("p-year",            "YEAR",
     "DATE_PART('year', EPISODE_START_DATE::date)::VARCHAR",           None),
    ("f-age-group",       "AGE_GROUP",             None,               None),
    ("f-gender",          "PATIENT_GENDER",        GENDER_EXPR,        None),
    ("f-payer",           "PAYER_TYPE",            None,               None),
    ("f-hr-condition",    "HIGH_RISK_CONDITION",   None,               None),
    ("f-grouped-account", "GROUPED_ACCOUNT",       None,               None),
    ("f-parent-id",       "PARENT_NAME",           PARENT_ACCOUNT_EXPR, None),
    ("f-child-id",        "CHILD_NAME",            CHILD_ACCOUNT_EXPR,  500),
    ("f-specialty-group", "SPECIALTY_GROUP",       PROVIDER_SPECIALTY_GROUP_EXPR, None),
    ("f-specialty",       "HCP_PRIMARY_SPECIALTY", PROVIDER_PRIMARY_SPECIALTY_EXPR, None),
    ("f-area",            "AREA_TYPE",             None,               None),
]


class CascadeRequest(BaseModel):
    granularity: Optional[str] = "3"
    selections: Dict[str, List[str]] = {}
    currents: Dict[str, List[str]] = {}


@router.get("/filter-options")
def filter_options():
    min_d, max_d, years = date_extents()
    return {
        "min_date": min_d.isoformat(),
        "max_date": max_d.isoformat(),
        "years": [str(y) for y in years],
        "filters": {
            "f-age-group":        domain("AGE_GROUP"),
            "f-gender":           domain("PATIENT_GENDER", expr=GENDER_EXPR),
            "f-payer":            domain("PAYER_TYPE"),
            "f-hr-condition":     [v for v in domain("HIGH_RISK_CONDITION")
                                   if v != "ALL HR CONDITIONS"],
            "f-grouped-account":  domain("GROUPED_ACCOUNT"),
            "f-parent-id":        domain("PARENT_NAME", expr=PARENT_ACCOUNT_EXPR),
            "f-child-id":         domain("CHILD_NAME", expr=CHILD_ACCOUNT_EXPR, top_n=500),
            "f-specialty-group":  domain("SPECIALTY_GROUP", expr=PROVIDER_SPECIALTY_GROUP_EXPR),
            "f-specialty":        domain("HCP_PRIMARY_SPECIALTY", expr=PROVIDER_PRIMARY_SPECIALTY_EXPR),
            "f-area":             domain("AREA_TYPE"),
            "s8-visit-filter":    [v for v in domain("NO_VISIT_30") if v != "NO VISIT"],
            "s10-visit-filter":   [v for v in domain("VISIT_FILTER_COVID") if v and v != "Redundant"],
            "s8-hr-domain":       [v for v in domain("HIGH_RISK_CONDITION")
                                   if v not in ("ALL HR CONDITIONS", "NO HIGH RISK CONDITION")],
        },
    }


@router.post("/filter-cascade")
def filter_cascade(body: CascadeRequest):
    gran = body.granularity or "3"
    gv_expr = granularity_value_expr(gran) if gran and gran != "1" else None
    gv_entry = ("p-granularity-value", f"gv_{gran}", gv_expr, None)
    full_group = _DATA_GROUP + [gv_entry]

    out = run_group_cascade(full_group, body.selections, body.currents)
    if gv_expr is None:
        out["p-granularity-value"] = {"options": [], "value": ["__ALL__"]}
    return out


@router.post("/hr-top7")
def hr_top7(body: Dict[str, Any]):
    f = from_payload(body)
    try:
        df = run_query(*Q.q_s8_top7_list(f))
        top7 = df["HIGH_RISK_CONDITION"].tolist() if not df.empty else []
    except Exception:  # noqa: BLE001
        top7 = []
    hr_all = [v for v in domain("HIGH_RISK_CONDITION")
              if v not in ("ALL HR CONDITIONS", "NO HIGH RISK CONDITION")
              and v not in top7]
    return {
        "top7": top7,
        "top7_options": top7 + ["Other Conditions"],
        "hr_grouping_options": hr_all + ["Top 7 HR Conditions"],
    }


# ---------- Per-section chart + table --------------------------------------

@router.post("/section/{sid}")
def section(sid: str, body: Dict[str, Any]):
    f = from_payload(body)
    return render_section(sid, f)
