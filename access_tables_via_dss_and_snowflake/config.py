from dotenv import load_dotenv
import os
import json
import logging
import time as _time
from datetime import timedelta
import requests

try:
    from db_adapter import create_db_client
except ImportError:
    from .db_adapter import create_db_client

# Load .env file
load_dotenv()

_logger = logging.getLogger("app.timing")

# ============================================================================
# LOCAL_DEV bypass: set LOCAL_DEV=1 in your .env or environment to run the
# backend without the dataiku SDK installed. All config values come from
# hardcoded defaults below. DO NOT commit with LOCAL_DEV=1 in production.
# ============================================================================
LOCAL_DEV = os.getenv("LOCAL_DEV", "0") == "1"


def _load_json_variable(value):
    """
    Dataiku project variables that hold a JSON array/object (e.g.
    NEO_TRIGGERED_RULES_THRESHOLDS_CONFIG) come back from
    project.get_variables() ALREADY PARSED into a native list/dict when the
    variable was entered as JSON in the Dataiku UI - not as a JSON string.
    json.loads() on that already-parsed value throws
    "TypeError: ... must be str, bytes or bytearray, not list". Handle both
    shapes rather than assuming one, since it depends on how the variable
    was entered.
    """
    if isinstance(value, (list, dict)):
        return value
    return json.loads(value)

if LOCAL_DEV:
    # --- LOCAL DEV MODE: see config_local.py ---
    try:
        from config_local import Config
    except ImportError:
        from .config_local import Config

else:
    # --- NORMAL MODE: requires dataiku SDK ---
    import dataiku

    class Config:
        # get the stored variable from dss.
        project = dataiku.api_client().get_project(dataiku.default_project_key())
        project_variables = project.get_variables()["standard"]
        

        JWT_SECRET = project_variables["JWT_SECRET_KEY"]
        JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
        # JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
        JWT_TOKEN_LOCATION = ["headers"]
        JWT_ALGORITHM = "HS256"
        JWT_HEADER_NAME = "Authorization"
        JWT_HEADER_TYPE = "Bearer"
        JWT_EXPIRY_HOURS = 8
        CHARGEBACK_START_DATE  = project_variables["CHARGEBACK_START_DATE"]
        CHARGEBACK_END_DATE =  project_variables["CHARGEBACK_END_DATE"]
        COGS_YEAR  = project_variables["COGS_YEAR"]
        COST_FILE_NEXT_YEAR = project_variables["COST_FILE_NEXT_YEAR"]
        COST_FILE_CURRENT_YEAR = project_variables['COST_FILE_CURRENT_YEAR']
        # JWT_IDENTITY_CLAIM = "sub"
        # JWT_PAYLOAD_HANDLER = None
        # JWT_BLACKLIST_ENABLED = True
        # JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]

        #DATAIKU_CONNECTION_NAME = project_variables["SNOWFLAKE_CONNECTION_NAME"]
        DATAIKU_PROJECT_KEY = project_variables["PROJECT_KEY"]
        APP_NAME = project_variables["PROJECT_NAME"] or "PVSimulator"
        APP_VERSION = project_variables["PROJECT_VERSION"] or "1"
        ALLOWED_ORIGINS = project_variables["ALLOWED_ORIGINS"] or "*"
        DATASETS = {
        "ndc_dataset": project_variables["CONTRACT_DATASET"],
        "user_dataset": project_variables["USER_ACCESS_DATASET"],
        "neo_pricing_dataset": project_variables["NEO_PRICING_DATASET"],
        "access_logs_dataset" : project_variables["ACCESS_LOGS_DATASET"],
        "ims_color_dataset" : project_variables['IMS_COLOR_DATASET'],
        # Market Dynamics (Task 31.9+) shared dataset. Read with .get() and
        # fall back to the NEO pricing dataset so import doesn't break before
        # the dedicated MARKET_DYNAMICS_DATASET project variable is added.
        "market_dynamics_dataset": project_variables.get(
            "MARKET_DYNAMICS_DATASET"
        ) or project_variables["NEO_PRICING_DATASET"],
        # Task 31.22 / 31.22a — Market Dynamics NDC snooze writeback table.
        # Single fully-qualified `<DB>.<SCHEMA>.<TABLE>` value sourced from
        # the Dataiku project variable `NEO_MD_SNOOZES_TABLE`.
        "neo_md_snoozes_dataset": project_variables["NEO_MD_SNOOZES_TABLE"],
        # PP (Task pp-01) — placeholder dataset keys until data team provides real ones
        "pp_violations_dataset": project_variables.get("PP_VIOLATIONS_DATASET", ""),
        "pp_exclusions_dataset": project_variables.get("PP_EXCLUSIONS_DATASET", ""),
        }

        # Task 32 - pluggable server-side cache. Kept on env vars (not Dataiku
        # project variables) so the default "memory" backend needs no new DSS
        # variable; flip CACHE_BACKEND=redis once a Redis backend ships.
        CACHE_BACKEND = os.getenv("CACHE_BACKEND", "memory")
        CACHE_DEFAULT_TTL_SECONDS = int(os.getenv("CACHE_DEFAULT_TTL_SECONDS", "3600"))
        CACHE_MAX_ENTRIES = int(os.getenv("CACHE_MAX_ENTRIES", "1024"))

        # NEO Triggered Rules threshold config (Task 4.1) - a JSON array of
        # {key, label, default_value, display_type, unit} objects, one per
        # threshold control, in on-screen order. Lives in a Dataiku project
        # variable (not a hardcoded Python literal) so changing a default value
        # or label doesn't require an app redeploy - only a variable update.
        #
        # NEW REQUIRED DATAIKU VARIABLE - does not exist yet, same treatment as
        # NEO_PRICING_DATASET (Task 14.0): add it under Settings -> Variables,
        # `standard` group, with this exact JSON as the value (17 items, source:
        # project-context/tableau-context/02-parameters.md lines 10-49):
        #
        # [
        #   {"key": "competitor_count_threshold", "label": "1. Competitor Count Threshold", "default_value": 4, "display_type": "integer", "unit": null},
        #   {"key": "gpo_concentration_threshold", "label": "2. GPO Concentration Threshold", "default_value": 50, "display_type": "percentage", "unit": "%"},
        #   {"key": "competitor_market_share_threshold", "label": "(3.1, 10.1) Competitor Market Share Threshold", "default_value": 55, "display_type": "percentage", "unit": "%"},
        #   {"key": "wac_pfizer_market_share_threshold", "label": "(3.2, 10.2) WAC Pfizer Market Share Threshold", "default_value": 20, "display_type": "percentage", "unit": "%"},
        #   {"key": "wac_gap_threshold", "label": "(3.3, 10.3) WAC Gap Threshold", "default_value": 10, "display_type": "percentage", "unit": "%"},
        #   {"key": "inter_segment_price_gap_threshold", "label": "4. Inter-Segment Price Gap Threshold", "default_value": 200, "display_type": "percentage", "unit": "%"},
        #   {"key": "intra_segment_price_gap_threshold", "label": "5. Intra-Segment Price Gap Threshold", "default_value": 50, "display_type": "percentage", "unit": "%"},
        #   {"key": "number_of_price_points_threshold", "label": "6. Number of Price Points Threshold", "default_value": 20, "display_type": "integer", "unit": null},
        #   {"key": "contract_volume_concentration_threshold", "label": "7.1 Contract Volume Concentration Threshold", "default_value": 5, "display_type": "percentage", "unit": "%"},
        #   {"key": "closeness_to_list_price_threshold", "label": "7.2 Closeness to List Price Threshold", "default_value": 5, "display_type": "percentage", "unit": "%"},
        #   {"key": "high_wac_gap_to_list_price_threshold", "label": "8. High WAC Gap to List Price Threshold", "default_value": 200, "display_type": "percentage", "unit": "%"},
        #   {"key": "pfizer_market_share_ndc_threshold", "label": "9.1 Pfizer Market Share NDC Threshold", "default_value": 30, "display_type": "percentage", "unit": "%"},
        #   {"key": "price_difference_threshold", "label": "9.2 Price Difference Threshold", "default_value": 20, "display_type": "percentage", "unit": "%"},
        #   {"key": "wac_market_volume_threshold_pct", "label": "10.4 WAC Market Volume Threshold (%)", "default_value": 20, "display_type": "percentage", "unit": "%"},
        #   {"key": "non_acute_concentration_threshold", "label": "11. Non-Acute Concentration Threshold", "default_value": 20, "display_type": "percentage", "unit": "%"},
        #   {"key": "wac_compare_threshold", "label": "12. WAC Compare Threshold", "default_value": 20, "display_type": "percentage", "unit": "%"},
        #   {"key": "market_340b_concentration_threshold", "label": "13. 340 Market Concentration Threshold", "default_value": 20, "display_type": "percentage", "unit": "%"}
        # ]
        NEO_TRIGGERED_RULES_THRESHOLDS_CONFIG = _load_json_variable(
            project_variables["NEO_TRIGGERED_RULES_THRESHOLDS_CONFIG"]
        )

        # NEO Market Dynamics threshold config (Task 31.21) - JSON list of
        # {key, label, default_value, display_type, unit, signals[]} entries.
        # `signals` names the per-signal `type` keys each threshold applies to.
        # Starts empty; each signal task (31.4-31.18) appends its own entries.
        # Falls back to [] when the Dataiku variable is not yet defined, so
        # this shell task can ship before the variable is provisioned.
        NEO_MARKET_DYNAMICS_THRESHOLDS_CONFIG = (
            _load_json_variable(project_variables["NEO_MARKET_DYNAMICS_THRESHOLDS_CONFIG"])
            if "NEO_MARKET_DYNAMICS_THRESHOLDS_CONFIG" in project_variables
            and project_variables["NEO_MARKET_DYNAMICS_THRESHOLDS_CONFIG"]
            else []
        )

        # PP_RULE_DESCRIPTIONS_CONFIG (Task pp-12) - JSON array of
        # {rule, direction, title, description, thresholds[]} entries used by
        # the "Rule descriptions & help" panel. Owned end-to-end by Task pp-12;
        # Task pp-01's config surface deliberately excludes this key.
        #
        # NEW REQUIRED DATAIKU VARIABLE (same treatment as
        # NEO_TRIGGERED_RULES_THRESHOLDS_CONFIG): add under Settings ->
        # Variables, `standard` group. Missing variable falls back to [] so
        # the app boots even before it is provisioned.
        PP_RULE_DESCRIPTIONS_CONFIG = (
            _load_json_variable(project_variables["PP_RULE_DESCRIPTIONS_CONFIG"])
            if "PP_RULE_DESCRIPTIONS_CONFIG" in project_variables
            and project_variables["PP_RULE_DESCRIPTIONS_CONFIG"]
            else []
        )

        # PP config variables (Task pp-01) — filter buckets and exclusion reasons.
        PP_L12M_SALES_BUCKETS_CONFIG = (
            _load_json_variable(project_variables["PP_L12M_SALES_BUCKETS_CONFIG"])
            if "PP_L12M_SALES_BUCKETS_CONFIG" in project_variables
            and project_variables["PP_L12M_SALES_BUCKETS_CONFIG"]
            else []
        )
        PP_IMPACT_BUCKETS_CONFIG = (
            _load_json_variable(project_variables["PP_IMPACT_BUCKETS_CONFIG"])
            if "PP_IMPACT_BUCKETS_CONFIG" in project_variables
            and project_variables["PP_IMPACT_BUCKETS_CONFIG"]
            else []
        )
        PP_EXCLUSION_REASONS_CONFIG = (
            _load_json_variable(project_variables["PP_EXCLUSION_REASONS_CONFIG"])
            if "PP_EXCLUSION_REASONS_CONFIG" in project_variables
            and project_variables["PP_EXCLUSION_REASONS_CONFIG"]
            else []
        )

        AUTHENTICATION = {
            "SSO_AUTH_URL": project_variables["SSO_AUTH_URL"],
            "SSO_CLIENT_ID": project_variables["SSO_CLIENT_ID"],
            "SSO_CLIENT_SECRET": project_variables["SSO_CLIENT_SECRET"],
            "SSO_REDIRECT_URI": project_variables["SSO_REDIRECT_URI"],
            "SSO_SCOPE": project_variables["SSO_SCOPE"],
            # "SSO_REDIRECT_URI": "https://dss-amer-design.pfizer.com/code-studios/PRICE_VOLUME_SIMULATOR_APP/2rhXvTq/8080/proxy/8000/",
            "SSO_TOKEN_URL": project_variables["SSO_TOKEN_URL"],
        #     "SSO_USERINFO_URL": project_variables["SSO_USERINFO_URL"],
        #     "ENCRYPTION_KEY": project_variables["ENCRYPTION_KEY"],
        #     "SSO_ENCRYPTION_SALT": project_variables["SSO_ENCRYPTION_SALT"],
        #     "EXCLUDED_PATHS_ENCRYPTIONS": project_variables["EXCLUDED_PATHS_ENCRYPTIONS"],
        #     "SSO_TOKEN_PREFIX": project_variables["SSO_TOKEN_PREFIX"],
        #     "SSO_TOKEN_HEADER": project_variables["SSO_TOKEN_HEADER"],
        #     "COOKIE_DOMAIN": project_variables["COOKIE_DOMAIN"]
        }

        # EMAIL = {
        #     "smtp_email": project_variables["smtp_email"],
        #     "sender_email": project_variables["sender_email"],
        # }


        # Column name mappings
        COLUMN_MAPPING = {
            "ndc"               : "NDC11_CD_TRANSITION_DASH",
            "stackkey"          : "STACKKEY",
            "customer"          : "CUSTOMER_OWNER",
            "net_sales"         : "LST12MTH_NET_SALES",
            "volume"            : "LST12MTH_SLS_QTY_EACHES",
            "volume_6mts"       : "LST6MTH_SLS_QTY_EACHES",
            "net_sales_6mts"    : "LST6MTH_NET_SALES",

            "current_year_std_cogs"          : "CY_SKU_STD_COST_PRICE_USD_PER_EACH",
            "next_year_std_cogs"              : "NY_SKU_STD_COST_PRICE_USD_PER_EACH",
            "next_year_fixed_cogs"        : "NY_FIXED_COST_PRICE_USD_PER_EACH",
            "current_year_fixed_cogs"        :  "CY_FIXED_COST_PRICE_USD_PER_EACH",

        "manufacturer"      : "MANUFACTURER",
        "exact_market"      : "EXACT_LEVEL",
        "similar_market"    : "SIMILAR_LEVEL",
        "ims_sales_6m"      : "LAST6MTH_DOLLARS_IMS",
        "ims_volume_6m"     : "LAST6MTH_EACHES_IMS",
        "ndc_desc" : "DESCRIPTION",
        "molecule" : "MOLECULE_IMS",
        "portfolio_manager": "PORTFOLIO_MANAGER",
        "wac_price" : "LIST_PRICE",
        "current_year_budget_volume" : "CY_BUDGET_VOLUME_EACHES",
        "next_year_budget_volume"     : "NY_BUDGET_VOLUME_EACHES",
        "item_cd"       : "ITEM_CD",
        "contract_price" : "CONTRACT_PRICE",
        "contract_price_eaches" : "CONTRACT_PRICE_EACHES",
        "customer_type" : "CONTRACT_TYPE",
        "volume_last_month" : "LATEST_MTH_SLS_QTY_EACHES",
       # ── IMS Market Data — Exact Market ───────────────────────────────────
    "pfizer_dollars_12m_exact"  : "PFIZER_DOLLARS_IMS_LAST_12M_EXACT_MKT",
    "comp_dollars_12m_exact"    : "COMP_DOLLARS_IMS_LAST_12M_EXACT_MKT",
    "total_dollars_12m_exact"   : "DOLLARS_IMS_LAST_12M_EXACT_MKT",
    "pfizer_eaches_12m_exact"   : "PFIZER_EACHES_IMS_LAST_12M_EXACT_MKT",
    "comp_eaches_12m_exact"     : "COMP_EACHES_IMS_LAST_12M_EXACT_MKT",
    "total_eaches_12m_exact"    : "EACHES_IMS_LAST_12M_EXACT_MKT",
    "comp_dollars_6m_exact"     : "COMP_DOLLARS_IMS_LAST_6M_EXACT_MKT",
    "comp_eaches_6m_exact"      : "COMP_EACHES_IMS_LAST_6M_EXACT_MKT",

        # ── IMS Market Data — Similar Market ─────────────────────────────────
        "pfizer_dollars_12m_similar": "PFIZER_DOLLARS_IMS_LAST_12M_SIMILAR_MKT",
        "comp_dollars_12m_similar"  : "COMP_DOLLARS_IMS_LAST_12M_SIMILAR_MKT",
        "total_dollars_12m_similar" : "DOLLARS_IMS_LAST_12M_SIMILAR_MKT",
        "pfizer_eaches_12m_similar" : "PFIZER_EACHES_IMS_LAST_12M_SIMILAR_MKT",
        "comp_eaches_12m_similar"   : "COMP_EACHES_IMS_LAST_12M_SIMILAR_MKT",
        "total_eaches_12m_similar"  : "EACHES_IMS_LAST_12M_SIMILAR_MKT",
        "comp_dollars_6m_similar"   : "COMP_DOLLARS_IMS_LAST_6M_SIMILAR_MKT",
        "comp_eaches_6m_similar"    : "COMP_EACHES_IMS_LAST_6M_SIMILAR_MKT",

            # ── IMS Monthly columns ───────────────────────────────────────────
            "date_identifier"  : "DATE_IDENTIFIER",
            "date_parsed"      : "DATE_PARSED",
            "eaches_ims"       : "EACHES_IMS",
            "dollar_ims"       : "DOLLARS_IMS",

            "latest_complete_month" : "LATEST_COMPLETE_MONTH",

        # FCODE Volume Breakdown columns - STACKKEY = FCODE VOLUME BREAKDOWN
        "packs_to_eaches" : "PACKS_TO_EACHES",
        "source_price_group_id" : "SOURCE_PRICE_GROUP_ID",
       "source_price_group_description" : "SOURCE_PRICE_GROUP_DESCRIPTION",
        "sales_packs_12m" : "LST12MTH_SLS_QTY_PACKS",
        "sales_eaches_12m" : "LST12MTH_SLS_QTY_EACHES",

        # Missing NDC columns - STACKKEY = MISSING NDC
        "status" : "ACTIVATION_STATUS",
        "site_cmo" : "NDC_AGGREGATED_SITE_CMO",
        "missing_reason" : "MISSING_REASON",
        "is_cy_available" : "IS_CY_AVAILABLE",
        "is_ny_available" : "IS_NY_AVAILABLE",

        # Fcode deep-dive table - STACKKEY = COST DEEPDIVE

        "next_year_unit_absorp" : "NY_SKU_UNIT_ABSORP_PRICE_USD",
        "next_year_est_price" : "NY_SKU_EST_COST_PRICE_USD",
        "next_year_std_usd": "NY_SKU_STD_COST_PRICE_USD",
        "year" : "YEAR",
        "expense_ratio" : "SITE_FIXED_EXPENSE_RATIO",
        "budget_rate" : "BUDGET_RATE",
        
         # NET Calculation columns 
        "net_sales_12m" :"LST12MTH_NET_SALES",
        "net_sales_6m":"LST6MTH_NET_SALES",
       "net_sales_latest" : "LATEST_MTH_NET_SALES",
        "net_revenue" : "NET_REVENUE_SRC",
 "net_revenue_6m" : "NET_REVENUE_6M_SRC",
 "net_revenue_latest" : "NET_REVENUE_LATEST_MTH_SRC",
"net_revenue_pt": "NET_REVENUE_PT",
   "net_revenue_6m_pt" : "NET_REVENUE_6M_PT",
   "net_revenue_latest_pt" :  "NET_REVENUE_LATEST_MTH_PT",
   "flex_rebate" : "FLEX_REBATE",
   "flex_admin_fee" : "FLEX_ADMIN_FEE",
   "group_id" : "SOURCE_PRICE_GROUP_ID",
   "rate_type" : "DEDCTN_RATE_TYPE",

   "admin_fee_revenue" : "ADMIN_FEE_DOLLAR_SRC",
   "admin_fee_revenue_pt" : "ADMIN_FEE_DOLLAR_PT",
   "rebate_revenue" : "REBATE_DOLLAR_SRC",
   "rebate_revenue_pt" : "REBATE_DOLLAR_PT",   

    "zero_deduction_cnt" :  "ZERO_DEDUCTN_CNT",
    "null_deduction_cnt" : "NULL_DEDUCTN_CNT",
    "zero_deduction_cnt_pt" : "PT_ZERO_DEDUCTN_CNT",

    "rebate_type" : "REBATE_TYPE",
    "private_label" : "PRIVATE_LABEL",
   

        }

        _db_client_instance = None

        @classmethod
        def get_db_client(cls, provider: str = None):
            if cls._db_client_instance is None:
                chosen = provider or cls.project_variables.get("DEFAULT_PROVIDER") or "dataiku"
                _t0 = _time.perf_counter()
                _logger.info("DB CONNECT >>> creating '%s' client", chosen)
                cls._db_client_instance = create_db_client(chosen, cls.project_variables)
                _elapsed_ms = (_time.perf_counter() - _t0) * 1000
                _logger.info(
                    "DB CONNECT <<< '%s' client ready in %.1f ms", chosen, _elapsed_ms
                )
            return cls._db_client_instance


    
