"""Coerce a JSON filter payload from the frontend into a `BoDFilters` object.

The frontend ships the store shape 1:1 with the existing `BoDFilters.to_store()`
JSON, so all we need is to hand it back through `BoDFilters.from_store()`.
Missing/invalid keys fall back to defaults.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from bod_app.data.params import BoDFilters


_DEFAULT_STORE = BoDFilters().to_store()


def from_payload(payload: dict[str, Any] | None) -> BoDFilters:
    d = dict(_DEFAULT_STORE)
    if payload:
        for k, v in payload.items():
            if k in d:
                d[k] = v
    # Dates arrive as ISO strings; from_store handles that.
    try:
        return BoDFilters.from_store(d)
    except Exception:
        return BoDFilters()


def defaults_store() -> dict[str, Any]:
    return dict(_DEFAULT_STORE)
