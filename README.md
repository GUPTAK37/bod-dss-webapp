# COVID-19 QCIT — FastAPI + React on Dataiku DSS (STANDARD web app)

Reproduces the Tableau *Burden of Disease* dashboard as a **STANDARD Dataiku
DSS web app** with a FastAPI backend and a Vite/React frontend. Follows the
DSS pattern described in *"React Frontend on a FastAPI (STANDARD) Web App"*:

- **`backend/backend.py`** reuses the FastAPI `app` DSS injects — never
  redefines it.
- **`backend/dev_main.py`** creates its own `app` for local `fastapi dev`.
- **`backend/dist/`** holds the built React bundle and is **committed to
  git**. FastAPI's own `StaticFiles` (or `app.frontend()` in dev) serves it.
- **`dss/app.js`** is a tiny iframe that embeds
  `dataiku.getWebAppBackendUrl('app/')`.
- **Git-linked project library** — you deploy by `git push` + `Reset from
  remote head` inside DSS, not by `dss-sync push`.

## Repo layout

```
bod_dss_webapp/                                  ← this folder = the git repo
├── README.md
├── Makefile                                      make dev / make build
├── pyproject.toml                                uv-managed Python deps
├── .env.example
│
├── backend/
│   ├── backend.py                                DSS entrypoint (reuses injected `app`)
│   ├── dev_main.py                               `fastapi dev` entrypoint
│   ├── dist/                                     built React bundle (committed!)
│   └── service/
│       ├── setup.py                              configure(app): routes + static mount
│       ├── routes.py                             /api/* APIRouter
│       ├── identity.py                           DSS SSO user via browser headers
│       ├── dataiku_client.py                     DSSClient factory (in-DSS or local)
│       ├── config.py, db.py, filters.py, domains.py, renderers.py
│
├── frontend/
│   ├── package.json                              tsc && vite build
│   ├── tsconfig.json                             permissive TS (allows JSX/JS too)
│   ├── vite.config.ts                            base:'./', outDir:'../backend/dist'
│   ├── index.html
│   └── src/                                      App, components, styles
│
├── bod_app/                                      library: SQL builders + Plotly theme
├── access_tables_via_dss_and_snowflake/          library: DB adapter (Snowflake/Dataiku)
│
└── dss/                                          copy-paste into the DSS web app editor
    ├── body.html                                 (empty)
    ├── style.css                                 (empty)
    └── app.js                                    iframe embed of `getWebAppBackendUrl('app/')`
```

## Local development

Prerequisites: Python 3.11+, `uv`, Node 20+.

```powershell
# from repo root
uv sync --group dev
npm ci --prefix frontend
copy .env.example .env

# runs FastAPI (:8000) and Vite (:5173) in parallel
make dev
```

Then open **http://localhost:5173** — Vite proxies `/api/*` → FastAPI on 8000.
Setting `FASTAPI_ENV=development` in `.env` makes `setup.py` use FastAPI's
`app.frontend()` helper (nicer error pages) instead of the explicit
`StaticFiles` mount that DSS needs.

No Makefile? Do it by hand in two terminals:

```powershell
# terminal 1
uv run fastapi dev backend/dev_main.py --port 8000

# terminal 2
npm run dev --prefix frontend
```

## Building the SPA (do this before every `git push`)

```powershell
make build
# or
npm run build --prefix frontend
```

This runs `tsc && vite build`, which type-checks and emits into `backend/dist/`.
That folder **is committed to git** — DSS never runs `npm`.

A pre-commit hook (`make pre-commit`) refuses commits where source changed
but `backend/dist/` was not rebuilt.

## Deploying to DSS

### One-time setup

1. In DSS: **Project Settings → Libraries → Git** — link this repo.
2. Create a **STANDARD web app** in the project:
   - Params → **Backend framework: FASTAPI**
   - Params → **Code environment**: one that has `fastapi[standard]`,
     `pydantic`, `pandas`, `plotly`, `snowflake-connector-python[pandas]`,
     `dataikuapi` installed.
   - Paste the contents of `dss/body.html`, `dss/style.css`, `dss/app.js`
     into the corresponding editor slots.
3. Set the DSS project variable `SNOWFLAKE_CONNECTION_NAME` to your DSS
   Snowflake connection (e.g. `VAW_SF_COMMERCIAL_AMER_DESIGN_RW`).

### Ongoing deploys (every code change)

```powershell
make build
git add backend/dist backend frontend/src bod_app access_tables_via_dss_and_snowflake
git commit -m "…"
git push
```

Then in DSS:

1. **Git code library → Reset from remote head**.
2. **Web app → Restart backend** (long-running FastAPI process needs
   to reload code it already imported).

Automate steps 1–2 from CI with `dataikuapi`:

```python
from dataikuapi import DSSClient

client = DSSClient(DSS_HOST, API_KEY, no_check_certificate=True)
project = client.get_project(PROJECT_KEY)

project.get_project_git().reset_library("python/webapps/<lib-path>").wait_for_result()
project.get_webapp(WEBAPP_ID).start_or_restart_backend().wait_for_result()
```

## How the pieces fit together

```
┌─ DSS host page (body.html + app.js) ─────────────────────────────┐
│                                                                    │
│   <iframe src=getWebAppBackendUrl('app/')>                         │
│      ┌───────────────────────────────────────────────────────────┐ │
│      │ FastAPI (backend/backend.py + backend/service/setup.py)   │ │
│      │                                                             │ │
│      │   /api/*     → backend/service/routes.py                    │ │
│      │   /app/*     → StaticFiles(backend/dist)   ← React SPA      │ │
│      │                                                             │ │
│      │   /api/section/s1  → renderers.py → run_query()             │ │
│      │                       │                                     │ │
│      │                       ▼                                     │ │
│      │   access_tables_via_dss_and_snowflake/db_client.py          │ │
│      │        DataikuDatabaseClient (in DSS)  |  SnowflakeClient   │ │
│      └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

- DSS SSO authenticates the browser BEFORE the request reaches FastAPI.
  `backend/service/identity.py::get_current_user()` reads the SSO headers
  via `dataiku.get_auth_info_from_browser_headers()` — the backend never
  sees a password / API key / ticket.
- Snowflake access always flows through the reusable
  `access_tables_via_dss_and_snowflake/` adapter (your other Pfizer webapps
  can drop the same folder in).

## Environment variables

| Var                       | Default              | Notes                                                       |
|---------------------------|----------------------|-------------------------------------------------------------|
| `FASTAPI_ENV`             | *(unset)*            | Set to `development` locally to use `app.frontend()` helper |
| `DB_PROVIDER`             | *(auto)*             | Force `dataiku` or `snowflake`                              |
| `SNOWFLAKE_USER` / …      | *(none)*             | Local SSO overrides; falls back to `~/.snowflake/connections.toml` |
| `SNOWFLAKE_CONNECTION_NAME` | `AMERPROD01`       | Name of the TOML entry to load                              |
| `DSS_HOST` / `DSS_API_KEY`  | *(none)*           | Only needed for the local DSSClient path                    |
| `DEV_USER_LOGIN`          | `local.dev@example.com` | Returned by `/api/me` when not in DSS                     |
| `ALLOWED_ORIGINS`         | `*`                  | Comma-separated CORS origins                                |

## Tech stack

- **Backend:** FastAPI 0.115+ (with `fastapi[standard]`), uvicorn, Pydantic
  v2, Plotly (server-side figure JSON), Snowflake connector, Dataiku SDK
  (auto-detected).
- **Frontend:** React 18, Vite 5, TypeScript (permissive — accepts JSX/JS
  too), react-plotly.js, axios. Plain CSS (Tableau look preserved).
- **Data:** Snowflake; SSO locally, DSS `SQLExecutor2` in DSS.
- **Deploy:** git-linked DSS project library + iframe embed.
