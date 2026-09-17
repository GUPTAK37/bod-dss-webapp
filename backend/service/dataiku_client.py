"""DSSClient factory.

Returns a `dataikuapi.DSSClient` instance that works in two environments:

- **In DSS** — `dataiku.api_client()` (uses the injected internal ticket).
- **Locally** — `DSSClient(DSS_HOST, DSS_API_KEY)` from env vars in `.env`.

Nothing in the current webapp needs project-level DSSClient calls at
request time (all data goes through `db.run_query`), but this helper is
here for future features that inspect DSS project state — e.g. reading a
managed dataset, resolving a scenario status, etc.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

log = logging.getLogger("backend.service.dataiku_client")

_client_lock = threading.Lock()
_client: Any = None


def get_client() -> Any:
    """Return a cached `DSSClient` instance. Raises RuntimeError if neither
    the in-DSS injected client nor local env-var creds are available."""
    global _client
    with _client_lock:
        if _client is not None:
            return _client
        # In DSS: use the injected API client.
        try:
            import dataiku  # type: ignore
            _client = dataiku.api_client()
            log.info("DSSClient: using injected api_client() (in-DSS)")
            return _client
        except Exception:
            pass
        # Local: build a DSSClient from env vars.
        host = os.getenv("DSS_HOST")
        api_key = os.getenv("DSS_API_KEY")
        if not host or not api_key:
            raise RuntimeError(
                "DSSClient unavailable: neither dataiku.api_client() (in DSS) "
                "nor DSS_HOST + DSS_API_KEY (local dev) are set."
            )
        from dataikuapi import DSSClient  # type: ignore
        no_cert_check = os.getenv("DSS_NO_CERT_CHECK", "false").lower() == "true"
        _client = DSSClient(host, api_key, no_check_certificate=no_cert_check)
        log.info("DSSClient: using DSSClient(%s) (local dev)", host)
        return _client


def get_project(project_key: str | None = None) -> Any:
    """Return the current or named DSS project handle."""
    client = get_client()
    if project_key is None:
        try:
            import dataiku  # type: ignore
            project_key = dataiku.default_project_key()
        except Exception:
            project_key = os.getenv("DSS_PROJECT_KEY")
    if not project_key:
        raise RuntimeError("No DSS project_key given and default_project_key() not resolvable.")
    return client.get_project(project_key)
