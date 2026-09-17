# db_adapter.py
"""
Adapter to build provider-specific config dicts from Dataiku project variables (Config.project_variables)
and return a DatabaseClient instance via DatabaseClientFactory.
"""

try:
    from db_client import DatabaseClientFactory
except ImportError:
    from .db_client import DatabaseClientFactory


def get_provider_config_from_project_variables(provider_name: str, project_variables: dict) -> dict:
    provider_name = provider_name.lower()
    if provider_name == "dataiku":
        return {
            "PROJECT_KEY": project_variables.get("PROJECT_KEY"),
            "CONNECTION_NAME": project_variables.get("SNOWFLAKE_CONNECTION_NAME"),
            "DATABASE_NAME": project_variables.get("database"),
            "SCHEMA_NAME": project_variables.get("schema"),
        }
    elif provider_name == "snowflake":
        # common names used in your Config/project variables

        return {
            "USER": project_variables.get("service_account_username") or project_variables.get("USER"),
            "SNOWFLAKE_PRIVATE_KEY": project_variables.get("snowflake_private_key") or project_variables.get("SNOWFLAKE_PRIVATE_KEY"),
            "ACCOUNT": project_variables.get("account_link") or project_variables.get("ACCOUNT"),
            "WAREHOUSE": project_variables.get("warehouse") or project_variables.get("WAREHOUSE"),
            "DATABASE": project_variables.get("database") or project_variables.get("DATABASE"),
            "SCHEMA": project_variables.get("schema") or project_variables.get("SCHEMA"),
            "ROLE": project_variables.get("role") or project_variables.get("ROLE"),
            "AUTHENTICATOR": project_variables.get("authenticator") or project_variables.get("AUTHENTICATOR"),
        }
    else:
        raise ValueError(f"Unknown provider: {provider_name}")


def create_db_client(provider: str, project_variables: dict):
    cfg = get_provider_config_from_project_variables(provider, project_variables)
    # print(cfg, "Creds")
    # print(provider, "provider")
    return DatabaseClientFactory.get_client(provider=provider, config=cfg)