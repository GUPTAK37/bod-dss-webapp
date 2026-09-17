# Convenience targets for local dev + build.
# Requires: uv (pip install uv), node/npm.
#
# Windows note: PowerShell users can run `make dev` via GNU make (choco install make)
# or invoke the individual steps by hand from `.PHONY` targets below.

.PHONY: install dev backend frontend build check clean pre-commit

install:
	uv sync --group dev
	npm ci --prefix frontend

# Runs FastAPI (port 8000) and Vite (port 5173) in parallel.
# Open http://localhost:5173 — Vite proxies /api → :8000.
dev:
	@echo "Starting backend (fastapi dev) and frontend (vite) in parallel..."
	@$(MAKE) -j 2 backend frontend

backend:
	uv run fastapi dev backend/dev_main.py --port 8000

frontend:
	npm run dev --prefix frontend

# Build the React bundle into backend/dist/ (committed).
build:
	npm run build --prefix frontend

check:
	uv run python -m compileall backend
	npm run build --prefix frontend

# Pre-commit guard: fail the commit if the source changed but backend/dist
# wasn't rebuilt (very easy to forget since the build output is committed).
pre-commit: check
	@if ! git diff --quiet -- backend/dist; then \
	  echo "backend/dist changed; stage the rebuilt bundle before committing."; \
	  exit 1; \
	fi

clean:
	rm -rf backend/dist/* frontend/node_modules frontend/.vite
