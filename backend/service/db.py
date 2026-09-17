"""Snowflake access shim.

Uses the reusable **DatabaseClientFactory** from
`access_tables_via_dss_and_snowflake/db_client.py` (via the
`db_adapter.create_db_client()` factory) so this project uses the same
pattern as your other Pfizer webapps for easy DSS integration.

Config lookup (in order):

  1. **Dataiku DSS** — if the `dataiku` module is importable, read Snowflake
     connection settings from the current project's variables via
     `dataiku.api_client()`. Uses provider = "dataiku" (`SQLExecutor2` path).
  2. **Local dev** — fall back to `~/.snowflake/connections.toml` + env vars,
     using provider = "snowflake" with `authenticator=externalbrowser` (SSO).

Both paths surface `run_query(sql, binds)` returning a pandas DataFrame,
matching the signature used by `bod_app`.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Mapping

import pandas as pd

# NB: the folder name has no dashes/dots, so it imports cleanly.
from access_tables_via_dss_and_snowflake.db_adapter import create_db_client
from bod_app.data.snowflake_client import FACT_TABLE  # noqa: F401  — re-export

log = logging.getLogger(__name__)


_client_lock = threading.Lock()
_client = None
_provider_used: str | None = None


def _build_project_variables_from_dss() -> dict[str, Any] | None:
    """Return a project-variables dict when running inside Dataiku DSS.

    Reads only the keys `db_adapter.get_provider_config_from_project_variables()`
    consumes for provider == "dataiku". We intentionally do NOT load the full
    `access_tables_via_dss_and_snowflake/config.py`, because that module also
    requires app-specific variables (JWT_SECRET, COGS_YEAR, etc.) that don't
    belong to this webapp.
    """
    try:
        import dataiku  # type: ignore
    except Exception:
        return None
    try:
        project = dataiku.api_client().get_project(dataiku.default_project_key())
        pv = project.get_variables().get("standard", {}) or {}
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not read DSS project variables (%s); using local fallback", exc)
        return None
    return {
        "PROJECT_KEY": pv.get("PROJECT_KEY")
                       or os.getenv("DKU_CURRENT_PROJECT_KEY"),
        "SNOWFLAKE_CONNECTION_NAME": pv.get("SNOWFLAKE_CONNECTION_NAME")
                                     or os.getenv("DSS_SNOWFLAKE_CONNECTION")
                                     or "VAW_SF_COMMERCIAL_AMER_DESIGN_RW",
        "database": pv.get("database"),
        "schema":   pv.get("schema"),
    }


def _read_snowflake_toml(name: str | None = None) -> dict[str, Any]:
    """Read `~/.snowflake/connections.toml` and return the named entry (or
    the file's default). Returns {} on any error. Lets us reuse the
    developer's existing SSO setup without duplicating creds into .env."""
    name = name or os.getenv("SNOWFLAKE_CONNECTION_NAME") or "AMERPROD01"
    try:
        # Prefer snowflake-connector's own config manager (handles the standard
        # locations + `default_connection_name` file).
        from snowflake.connector.config_manager import CONFIG_MANAGER  # type: ignore
        try:
            conns = CONFIG_MANAGER["connections"]
        except Exception:
            conns = None
        if conns and name in conns:
            entry = dict(conns[name])
            return entry
    except Exception:
        pass
    # Manual fallback: parse TOML directly.
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {}
    path = os.path.expanduser("~/.snowflake/connections.toml")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return data.get(name) or {}
    except Exception:
        return {}


def _build_local_snowflake_variables() -> dict[str, Any]:
    """Env-var-driven Snowflake config for local dev (SSO / externalbrowser).

    If env vars are missing, fall back to `~/.snowflake/connections.toml`
    so the developer's existing SSO setup 'just works'.
    """
    toml_entry = _read_snowflake_toml()

    def pick(env_key: str, toml_key: str, default: str | None = None):
        return os.getenv(env_key) or toml_entry.get(toml_key) or default

    return {
        "USER":                  pick("SNOWFLAKE_USER",           "user"),
        "ACCOUNT":               pick("SNOWFLAKE_ACCOUNT",        "account"),
        "WAREHOUSE":             pick("SNOWFLAKE_WAREHOUSE",      "warehouse"),
        "DATABASE":              pick("SNOWFLAKE_DATABASE",       "database"),
        "SCHEMA":                pick("SNOWFLAKE_SCHEMA",         "schema"),
        "ROLE":                  pick("SNOWFLAKE_ROLE",           "role"),
        "AUTHENTICATOR":         pick("SNOWFLAKE_AUTHENTICATOR",  "authenticator",
                                       "externalbrowser"),
        "SNOWFLAKE_PRIVATE_KEY": os.getenv("SNOWFLAKE_PRIVATE_KEY"),
    }


def _pick_provider_and_vars() -> tuple[str, dict[str, Any]]:
    """Return `(provider_name, project_variables_dict)` for `create_db_client`."""
    dss_vars = _build_project_variables_from_dss()
    if dss_vars is not None:
        log.info("bod_webapp DB: using Dataiku DSS provider")
        return "dataiku", dss_vars
    log.info("bod_webapp DB: using local Snowflake provider (%s)",
             os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser"))
    return "snowflake", _build_local_snowflake_variables()


def _get_client():
    global _client, _provider_used
    with _client_lock:
        if _client is None:
            provider = os.getenv("DB_PROVIDER")   # override, if user pins it
            if provider:
                if provider.lower() == "dataiku":
                    project_vars = _build_project_variables_from_dss() or {}
                else:
                    project_vars = _build_local_snowflake_variables()
            else:
                provider, project_vars = _pick_provider_and_vars()
            _provider_used = provider
            _client = create_db_client(provider, project_vars)
        return _client


def _materialise_binds(sql: str, binds: Mapping[str, Any] | None) -> str:
    """The DSS `SQLExecutor2.query_to_df()` and the SnowflakeClient's
    `execute_query_to_df()` both take a plain SQL string (no bind params), so
    inline the values here. Escaping mirrors the logic used by
    `bod_app/data/snowflake_client.py::_run_via_dss`."""
    if not binds:
        return sql
    out = sql
    for k, v in binds.items():
        placeholder = "%(" + k + ")s"
        if isinstance(v, str):
            lit = "'" + v.replace("'", "''") + "'"
        elif hasattr(v, "isoformat"):
            lit = "'" + v.isoformat() + "'"
        elif v is None:
            lit = "NULL"
        else:
            lit = str(v)
        out = out.replace(placeholder, lit)
    return out


# ---------- LRU-cached run_query (matches bod_app's public API) --------------

import hashlib
import json as _json
from functools import lru_cache


def _key(sql: str, binds: Mapping[str, Any] | None) -> str:
    payload = _json.dumps({"sql": sql, "binds": binds or {}},
                          sort_keys=True, default=str)
    return hashlib.sha1(payload.encode()).hexdigest()


@lru_cache(maxsize=256)
def _cached(key: str, sql: str, binds_json: str) -> pd.DataFrame:  # noqa: ARG001
    binds = _json.loads(binds_json)
    materialised = _materialise_binds(sql, binds)
    return _get_client().execute_query_to_df(materialised)


def run_query(sql: str, binds: Mapping[str, Any] | None = None) -> pd.DataFrame:
    binds_json = _json.dumps(binds or {}, sort_keys=True, default=str)
    try:
        return _cached(_key(sql, binds), sql, binds_json).copy()
    except Exception:
        _cached.cache_clear()
        raise


def clear_cache() -> None:
    _cached.cache_clear()


def provider() -> str | None:
    """Introspection helper — which provider was picked at first call."""
    return _provider_used
