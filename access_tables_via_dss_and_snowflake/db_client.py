# db_clients.py
"""
Database Client Abstractions
Supports: Dataiku, Snowflake
Factory accepts explicit provider and config dict (no required YAML).
"""
from abc import ABC, abstractmethod
import pandas as pd
import logging
import time

logger = logging.getLogger(__name__)
timing_logger = logging.getLogger("app.timing")


class DatabaseClient(ABC):
    @abstractmethod
    def get_dataframe(self, dataset_name: str) -> pd.DataFrame:
        raise NotImplementedError()

    @abstractmethod
    def write_dataframe(self, df: pd.DataFrame, table_name: str):
        raise NotImplementedError()

    @abstractmethod
    def get_schema(self, table_name: str):
        raise NotImplementedError()

    @abstractmethod
    def update_dataframe(self, df: pd.DataFrame, table_name: str, key_columns: list):
        raise NotImplementedError()

    @abstractmethod
    def execute_query_to_df(self, query: str) -> pd.DataFrame:
        raise NotImplementedError()

    def execute_sql_query(self, query: str):
        """
        Optional: execute CREATE/UPDATE/DELETE etc.
        Concrete clients should override if they support.
        """
        raise NotImplementedError()

    def make_dataset_instance(self, new_table_name: str) -> str:
        raise NotImplementedError()


class DataikuDatabaseClient(DatabaseClient):
    def __init__(self, config: dict):
        # config keys: PROJECT_KEY, CONNECTION_NAME, DATABASE_NAME, SCHEMA_NAME
        import dataiku
        from dataiku.core.sql import SQLExecutor2

        _t0 = time.perf_counter()
        self.client = dataiku.api_client()
        _t_api = time.perf_counter()
        self.project = self.client.get_project(config["PROJECT_KEY"])
        _t_proj = time.perf_counter()
        self.connection_name = config.get("CONNECTION_NAME")
        self.project_key = config.get("PROJECT_KEY")
        self.SQLExecutor2 = SQLExecutor2
        self.database = config.get("DATABASE_NAME")
        self.schema = config.get("SCHEMA_NAME")
        timing_logger.info(
            "DATAIKU INIT connection='%s' api_client=%.1fms get_project=%.1fms total=%.1fms",
            self.connection_name,
            (_t_api - _t0) * 1000,
            (_t_proj - _t_api) * 1000,
            (_t_proj - _t0) * 1000,
        )

    def get_dataframe(self, dataset_name: str) -> pd.DataFrame:
        dataset = self.project.get_dataset(dataset_name)
        return dataset.get_dataframe()

    def write_dataframe(self, df: pd.DataFrame, dataset_name: str):
        dataset = self.project.get_dataset(dataset_name)
        dataset.write_with_schema(df)

    def get_schema(self, dataset_name: str):
        dataset = self.project.get_dataset(dataset_name)
        schema = dataset.get_schema()
        schema_info = []
        for col in schema.get("columns", []):
            entry = {
                "name": col.get("name"),
                "description": col.get("comment"),
                "data type": col.get("type"),
            }
            schema_info.append(entry)
        return schema_info

    def update_dataframe(self, df: pd.DataFrame, dataset_name: str, key_columns: list):
        # Dataiku normally uses rewrite; preserve existing behavior
        self.write_dataframe(df, dataset_name)

    def execute_query_to_df(self, query: str) -> pd.DataFrame:
        # Phase-split timing so deployed logs reveal whether time goes into
        # SQLExecutor2 construction (connection acquisition), the actual
        # Snowflake round-trip, or app-side NaN->None post-processing.
        _t0 = time.perf_counter()
        executor = self.SQLExecutor2(connection=self.connection_name)
        _t_exec = time.perf_counter()
        df = executor.query_to_df(query)
        _t_query = time.perf_counter()

        row_count = 0 if df is None else len(df)
        if df is not None and not df.empty:
            df = df.astype(object)                # allow None in all columns
            df = df.where(pd.notna(df), None)    # replace NaN/NaT with None
        _t_post = time.perf_counter()

        timing_logger.info(
            "DATAIKU QUERY connection='%s' executor_init=%.1fms query_to_df=%.1fms "
            "postprocess=%.1fms total=%.1fms rows=%d",
            self.connection_name,
            (_t_exec - _t0) * 1000,
            (_t_query - _t_exec) * 1000,
            (_t_post - _t_query) * 1000,
            (_t_post - _t0) * 1000,
            row_count,
        )
        return df

    def execute_sql_query(self, query: str):
        response = self.client.sql_query(
            query=query, connection=self.connection_name, post_queries=["COMMIT"], project_key=self.project_key
        )
        return response

    def make_dataset_instance(self, new_table_name: str) -> str:
        # Keep your existing Dataiku mapping routine if desired.
        try:
            full_table_path = f"{self.database}.{self.schema}.{new_table_name}"
            try:
                from dataikuapi.utils import DataikuException
            except Exception:
                DataikuException = Exception

            try:
                self.project.create_dataset(
                    new_table_name,
                    type="Snowflake",
                    params={
                        "connection": self.connection_name,
                        "table": full_table_path,
                        "mode": "table",
                        "tableMode": "table",
                    },
                )
            except DataikuException:
                # dataset likely exists — continue
                pass

            dss_dataset = self.project.get_dataset(new_table_name)

            definition = dss_dataset.get_definition()
            if definition.get("managed") is not True:
                definition["managed"] = True
                dss_dataset.set_definition(definition)

            # Optionally sync schema from an external util (left as in original)
            try:
                from agent_middleware.utils.database_utility.fetch_schema_utils import (
                    get_table_schema_with_descriptions,
                )

                fetched_schema = get_table_schema_with_descriptions(f"{self.schema}.{new_table_name}")
                for c in fetched_schema.get("columns", []):
                    txt = str(c.get("comment", "")).strip()
                    if txt.lower().startswith("no description"):
                        c["comment"] = None
                dss_dataset.set_schema(fetched_schema)
            except Exception:
                # If schema sync not available, ignore
                logger.debug("Schema sync skipped or failed", exc_info=True)

            settings = dss_dataset.get_settings()
            settings.set_table(self.connection_name, self.schema, new_table_name)
            settings.save()
            return f"{new_table_name} has been created/updated in Dataiku successfully"
        except Exception as e:
            return f"Failed to create/update dataset {new_table_name}: {e}"


class SnowflakeClient(DatabaseClient):

    def __init__(self, config = {}):
        import snowflake.connector
        self.snowflake_connector = snowflake.connector

        authenticator = config.get('AUTHENTICATOR')
        private_key_str = config.get('SNOWFLAKE_PRIVATE_KEY')

        if authenticator and authenticator.lower() == 'externalbrowser':
            self.connection_params = {
                'user': config.get('USER'),
                'account': config.get('ACCOUNT'),
                'authenticator': 'externalbrowser',
                'warehouse': config.get('WAREHOUSE'),
                'database': config.get('DATABASE'),
                'schema': config.get('SCHEMA'),
                'role': config.get('ROLE'),
                'client_session_keep_alive': True
            }
        else:
            from cryptography.hazmat.primitives import serialization
            private_key_str = private_key_str.replace("  ", "\n").strip()

            key_data = private_key_str.encode("utf-8")
            try:
                p_key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                )
            except TypeError:
                p_key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                )

            private_key_bytes = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            self.connection_params = {
                'user': config.get('USER'),
                'private_key': private_key_bytes,
                'account': config.get('ACCOUNT'),
                'warehouse': config.get('WAREHOUSE'),
                'database': config.get('DATABASE'),
                'role': config.get('ROLE'),
                'client_session_keep_alive': True
            }

        _t0 = time.perf_counter()
        self.conn = snowflake.connector.connect(**self.connection_params)
        timing_logger.info(
            "SNOWFLAKE CONNECT account='%s' warehouse='%s' connect=%.1fms",
            self.connection_params.get("account"),
            self.connection_params.get("warehouse"),
            (time.perf_counter() - _t0) * 1000,
        )


    def _get_cursor(self):
        return self.conn.cursor()

    def get_dataframe(self, dataset_name: str) -> pd.DataFrame:
        cur = self._get_cursor()
        try:
            query = f'SELECT * FROM {dataset_name}'
            cur.execute(query)
            df = cur.fetch_pandas_all()
            return df
        finally:
            cur.close()

    def write_dataframe(self, df: pd.DataFrame, table_name: str):
        """
        Fast path: use write_pandas (if available).
        Fallback: row-by-row insert (with escaping).
        """
        try:
            # try using Snowflake helper if installed
            from snowflake.connector.pandas_tools import write_pandas

            # write_pandas returns (success, nchunks, nrows, output)
            success, nchunks, nrows, _ = write_pandas(self.conn, df, table_name)
            if not success:
                raise RuntimeError("write_pandas failed")
            return {"rows_written": nrows, "chunks": nchunks}
        except Exception:
            # fallback: naive row-by-row insert (escape single quotes)
            cur = self._get_cursor()
            try:
                cols = ",".join([f'"{c}"' for c in df.columns])
                for _, row in df.iterrows():
                    vals = []
                    for x in row:
                        if x is None:
                            vals.append("NULL")
                        else:
                            s = str(x).replace("'", "''")
                            vals.append(f"'{s}'")
                    values = ",".join(vals)
                    sql = f"INSERT INTO {table_name} ({cols}) VALUES ({values})"
                    cur.execute(sql)
                try:
                    self.conn.commit()
                except Exception:
                    pass
            finally:
                cur.close()
            return {"rows_written": len(df)}

    def get_schema(self, table_name: str):
        cur = self._get_cursor()
        try:
            cur.execute(f"DESC TABLE {table_name}")
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            # indices heuristics
            name_idx = cols.index("name") if "name" in cols else 0
            type_idx = cols.index("type") if "type" in cols else 1
            comment_idx = None
            if "comment" in cols:
                comment_idx = cols.index("comment")
            elif "description" in cols:
                comment_idx = cols.index("description")
            schema = []
            for r in rows:
                col_name = r[name_idx]
                col_type = r[type_idx] if len(r) > type_idx else ""
                col_desc = r[comment_idx] if (comment_idx is not None and len(r) > comment_idx) else ""
                schema.append({"name": col_name, "description": col_desc or "", "data type": col_type})
            return schema
        finally:
            cur.close()

    def update_dataframe(self, df: pd.DataFrame, table_name: str, key_columns: list):
        """
        Naive implementation: generates UPDATE statements row-by-row.
        For large updates, prefer loading into a staging table and running a set-based MERGE.
        """
        cur = self._get_cursor()
        try:
            for _, row in df.iterrows():
                set_clause = ', '.join([f"{col}='{str(row[col])}'" for col in df.columns if col not in key_columns])
                where_clause = ' AND '.join([f"{col}='{str(row[col])}'" for col in key_columns])
                sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
                cur.execute(sql)
        finally:
            cur.close()

    def execute_query_to_df(self, query: str) -> pd.DataFrame:
        cur = self._get_cursor()
        try:
            _t0 = time.perf_counter()
            cur.execute(query)
            _t_exec = time.perf_counter()
            df = cur.fetch_pandas_all()
            _t_fetch = time.perf_counter()
            row_count = 0 if df is None else len(df)
            if df is not None and not df.empty:
                df = df.astype(object)                # allow None in all columns
                df = df.where(pd.notna(df), None)    # replace NaN/NaT with None
            _t_post = time.perf_counter()

            timing_logger.info(
                "SNOWFLAKE QUERY execute=%.1fms fetch=%.1fms postprocess=%.1fms "
                "total=%.1fms rows=%d",
                (_t_exec - _t0) * 1000,
                (_t_fetch - _t_exec) * 1000,
                (_t_post - _t_fetch) * 1000,
                (_t_post - _t0) * 1000,
                row_count,
            )
            # for col in df.select_dtypes(include=[object]).columns:
            #     df[col] = df[col].apply(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)
            return df
        finally:
            cur.close()

    def execute_sql_query(self, query: str):
        cur = self._get_cursor()
        try:
            cur.execute(query)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cur.close()

    def make_dataset_instance(self, new_table_name: str) -> str:
        # Snowflake has no Dataiku mapping — simple placeholder/validation
        cur = None
        try:
            cur = self._get_cursor()
            try:
                cur.execute(f"SELECT 1 FROM {new_table_name} LIMIT 1")
                return f"Snowflake table {new_table_name} appears to exist."
            except Exception:   
                return f"Snowflake table {new_table_name} does not exist or not accessible."
        finally:
            if cur is not None:
                try:
                    cur.close()
                except Exception:
                    pass


class DatabaseClientFactory:
    """
    Factory for creating database client instances based on provider name.
    Supports both explicit (provider, config) and YAML-based initialization.
    """

    _client_map = {
        "dataiku": DataikuDatabaseClient,
        "snowflake": SnowflakeClient,
    }

    @staticmethod
    def get_client(provider: str = None, config: dict = None):
        """
        Create and return a database client instance.
        Args:
            provider (str, optional): The provider name (e.g., 'dataiku', 'snowflake').
                If not provided, defaults to the provider found in YAML config.
            config (dict, optional): Configuration dictionary for the client.
                If not provided, the factory will look for provider-specific settings
                in the YAML file read via `read_yaml_to_dict()`.
        Returns:
            DatabaseClient: An instance of the appropriate client implementation.
        Raises:
            ValueError: If the provider is not supported or cannot be determined.
        """
        # --- Case 1: Explicit parameters provided ---
        if provider and config:
            client_cls = DatabaseClientFactory._client_map.get(provider.lower())
            # print(client_cls, "class")
            if not client_cls:
                raise ValueError(f"Unsupported provider: {provider}")
            return client_cls(config)

        # --- Case 2: Fallback to YAML configuration ---
        try:
            from base import read_yaml_to_dict
        except Exception:
            read_yaml_to_dict = None

        if read_yaml_to_dict is None:
            raise ValueError("No provider/config provided and read_yaml_to_dict() not available as fallback.")

        cfg = read_yaml_to_dict()
        provider = cfg.get("DATA_CONFIG", {}).get("DEFAULT_PROVIDER")
        provider_config = cfg.get("DATA_CONFIG", {}).get("PROVIDERS", {}).get(provider)

        if not provider:
            raise ValueError("No provider specified or found in configuration.")
        if not provider_config:
            raise ValueError(f"No configuration found for provider '{provider}'.")

        client_cls = DatabaseClientFactory._client_map.get(provider.lower())
        if not client_cls:
            raise ValueError(f"Unsupported provider: {provider}")

        return client_cls(provider_config)