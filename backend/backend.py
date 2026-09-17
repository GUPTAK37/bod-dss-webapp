"""DSS entrypoint.

Dataiku DSS pre-injects a `FastAPI` instance as the global `app` when the
web app is configured with `backendFramework: FASTAPI`. We MUST reuse that
instance — never redefine it — and simply attach our routes + static mount.
"""

from .service.setup import configure

configure(app)  # noqa: F821 - `app` is injected by DSS at runtime
