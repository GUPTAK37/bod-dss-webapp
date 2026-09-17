"""Local dev entrypoint.

Run with:  fastapi dev backend/dev_main.py
or:        uvicorn backend.dev_main:app --reload

DSS does NOT use this file — `backend/backend.py` reuses the pre-injected
`app` there.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()  # fastapi dev doesn't load .env on its own

# Force dev mode BEFORE configure() runs so setup.py picks the frontend()
# helper path over the explicit StaticFiles mount.
os.environ.setdefault("FASTAPI_ENV", "development")

from fastapi import FastAPI  # noqa: E402

from .service.setup import configure  # noqa: E402

app = FastAPI(
    title="COVID-19 QCIT — Burden of Disease",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
configure(app)
