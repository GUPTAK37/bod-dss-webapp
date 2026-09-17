"""DSS SSO user resolution.

DSS authenticates every browser request through its own SSO layer before the
request reaches the webapp backend. The signed-in user's identity travels in
a handful of headers, which the Dataiku Python SDK exposes through
`dataiku.get_auth_info_from_browser_headers(headers)`.

Outside DSS (local `fastapi dev`) there is no SSO layer, so we synthesize a
predictable dev identity to keep API contracts stable.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping

log = logging.getLogger("backend.service.identity")


def get_current_user(headers: Mapping[str, str]) -> dict[str, Any]:
    """Return `{login, groups, source}` for the current request.

    - `login`  — DSS username (e.g. `KRITARTH.GUPTA@PFIZER.COM`)
    - `groups` — list of DSS group names the user belongs to
    - `source` — `"dss"` in prod, `"local-dev"` outside DSS
    """
    try:
        import dataiku  # type: ignore
        info = dataiku.get_auth_info_from_browser_headers(dict(headers))
        return {
            "login": info.get("authIdentifier") or info.get("login"),
            "groups": info.get("groups") or [],
            "source": "dss",
        }
    except Exception as exc:  # noqa: BLE001
        # Local dev / not in DSS — return a stable synthetic identity so the
        # frontend can render user-scoped views without special-casing.
        if os.getenv("DKU_BACKEND_HOST"):
            # We ARE in DSS but the headers lookup failed — surface it.
            log.warning("DSS identity lookup failed: %s", exc)
        return {
            "login": os.getenv("DEV_USER_LOGIN", "local.dev@example.com"),
            "groups": [g.strip() for g in os.getenv("DEV_USER_GROUPS", "developers").split(",") if g.strip()],
            "source": "local-dev",
        }
