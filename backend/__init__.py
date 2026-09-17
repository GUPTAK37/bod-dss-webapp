# backend package.
#
# Monkey-patches `bod_app.data.snowflake_client.run_query` to route through our
# `backend.service.db.run_query`, so the SQL builders in
# `bod_app.data.queries` use the adapter-driven client
# (access_tables_via_dss_and_snowflake/db_client.py) transparently.

from bod_app.data import snowflake_client as _sc  # noqa: E402
from .service import db as _db  # noqa: E402

_sc.run_query = _db.run_query  # type: ignore[assignment]
