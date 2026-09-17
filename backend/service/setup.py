"""FastAPI wiring — routes + static mount + CORS.

Called from BOTH entrypoints:
  - `backend/backend.py` (DSS)   — reuses the pre-injected FastAPI `app`
  - `backend/dev_main.py`         — creates its own `app` for `fastapi dev`
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import Config
from .routes import router

# The built React bundle sits at `<repo>/backend/dist/`. DSS runs the webapp
# from an unrelated cwd so we resolve the path relative to THIS file, not cwd.
DIST_DIR = Path(__file__).resolve().parent.parent / "dist"

log = logging.getLogger("backend.service.setup")


def configure(app: FastAPI, config_cls=Config) -> None:
    # ---- CORS ---------------------------------------------------------------
    origins = config_cls.ALLOWED_ORIGINS
    allow_list = ["*"] if origins == "*" else [o.strip() for o in origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- API routes ---------------------------------------------------------
    app.include_router(router, prefix="/api")

    # ---- Static frontend ----------------------------------------------------
    # In dev, prefer FastAPI's `app.frontend()` helper (adds live-reload etc.).
    # In DSS (prod), the platform installs a low-priority catch-all route
    # that shadows `app.frontend()`, so mount StaticFiles explicitly.
    if os.getenv("FASTAPI_ENV") == "development" and hasattr(app, "frontend"):
        # FastAPI 0.115+ ships `app.frontend()`; use it when available.
        app.frontend(  # type: ignore[attr-defined]
            "/app", directory=str(DIST_DIR),
            fallback="index.html", check_dir=False,
        )
    else:
        app.mount(
            "/app",
            StaticFiles(directory=str(DIST_DIR), html=True, check_dir=False),
            name="frontend",
        )

    log.info("bod_dss_webapp configured (dist=%s)", DIST_DIR)
