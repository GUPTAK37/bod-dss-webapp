"""Runtime config for the FastAPI backend.

Reads env-vars only (no Dataiku dependency). The upstream Snowflake connection
is handled by the existing `bod_app.data.snowflake_client` module which already
auto-detects DSS vs direct connector.
"""

from __future__ import annotations

import os


class Config:
    # Allowed CORS origins. Comma-separated. '*' for dev.
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")

    # Where the built React SPA lives — FastAPI serves it as static assets
    # under the same origin so the DSS Code Studio proxy works without CORS.
    FRONTEND_DIST = os.getenv(
        "FRONTEND_DIST",
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
        ),
    )

    # DSS Code Studio strips the /code-studios/... prefix before the request
    # reaches the backend, so routes are mounted at "/". Frontend uses
    # relative URLs (Vite `base: './'`) so this is only needed if the frontend
    # has to know its own public base — normally not required.
    URL_PREFIX = os.getenv("URL_PREFIX", "")

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
