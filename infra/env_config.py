"""Configuração centralizada e validada do Flow-PMO via variáveis de ambiente.

Uso:
    from infra.env_config import get_settings
    settings = get_settings()
    ttl = settings.FLOW_PMO_REMOTE_CACHE_TTL_SECONDS

Todas as leituras de env vars de negócio devem passar por este módulo.
Leituras diretas via os.getenv() fora daqui são dívida técnica (RF-007).
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FlowPMOSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file_encoding="utf-8",
    )

    # --- Módulo Dash ---
    FLOW_PMO_DASH_MODULE: str = "dashboard_full"
    FLOW_PMO_DASH_ATTR: str = "app"

    # --- URLs dos modelos de dados ---
    FLOW_PMO_MODEL_URL: str = ""
    FLOW_PMO_MODEL_FILE: str = ""
    FLOW_PMO_PORTFOLIO_CSV_URL: str = ""
    FLOW_PMO_BOTTLENECK_CSV_URL_MAP: str = ""
    FLOW_PMO_FOUR_PS_KANBAN_CSV_URL: str = ""
    FLOW_PMO_DOWNSTREAM_CSV_URL_MAP: str = ""
    FLOW_PMO_PROCESS_MINING_REPORT_URL: str = ""
    FLOW_PMO_BITBUCKET_CSV_URL_MAP: str = ""

    # --- Cache ---
    FLOW_PMO_CACHE_DIR: str = "/tmp/flow-pmo-models"
    FLOW_PMO_REMOTE_CACHE_TTL_SECONDS: int = 300

    # --- SLA ---
    FLOW_PMO_ONE_PAGE_SLA_DAYS: int = 5
    FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP: str = ""

    # --- Controle de acesso ---
    FLOW_PMO_ALLOWED_DOMAIN: str = ""
    FLOW_PMO_ALLOWED_GROUP: str = ""
    FLOW_PMO_ALLOWED_EMAILS: str = ""

    # --- Configuração financeira (sensível — nunca commitar valores reais) ---
    FLOW_PMO_PM_COST_PER_HOUR_MAP: str = ""
    FLOW_PMO_PORTFOLIO_BU_SALARY_MAP: str = ""
    FLOW_PMO_PORTFOLIO_COST_MODEL: str = ""
    FLOW_PMO_PORTFOLIO_ROLE_SALARY_MAP: str = ""

    # --- Auth Google ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    FLASK_SECRET_KEY: str = ""

    # --- Portfólio ---
    FLOW_PMO_PORTFOLIO_CSV_FILE: str = ""
    FLOW_PMO_PORTFOLIO_TYPE_TARGET_MIX: str = ""

    # --- People ---
    FLOW_PMO_PERSON_ALIAS_MAP: str = ""
    FLOW_PMO_PERSON_SENIORITY_MAP: str = ""

    # --- AWS ---
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_DEFAULT_REGION: str = "us-east-1"

    def get_downstream_url_map(self) -> Dict[str, str]:
        return _parse_json_map(self.FLOW_PMO_DOWNSTREAM_CSV_URL_MAP)

    def get_bottleneck_url_map(self) -> Dict[str, str]:
        return _parse_json_map(self.FLOW_PMO_BOTTLENECK_CSV_URL_MAP)

    def get_bitbucket_csv_url_map(self) -> Dict[str, str]:
        return _parse_json_map(self.FLOW_PMO_BITBUCKET_CSV_URL_MAP)

    def get_process_mining_report_url_map(self) -> Dict[str, str]:
        return _parse_json_map(self.FLOW_PMO_PROCESS_MINING_REPORT_URL)

    def get_one_page_sla_days_map(self) -> Dict[str, int]:
        return _parse_json_map(self.FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP)

    def get_pm_cost_per_hour_map(self) -> Dict[str, float]:
        return _parse_json_map(self.FLOW_PMO_PM_COST_PER_HOUR_MAP)

    def get_portfolio_bu_salary_map(self) -> Dict[str, float]:
        return _parse_json_map(self.FLOW_PMO_PORTFOLIO_BU_SALARY_MAP)

    def get_portfolio_cost_model(self) -> Dict[str, Any]:
        return _parse_json_map(self.FLOW_PMO_PORTFOLIO_COST_MODEL)

    def get_portfolio_role_salary_map(self) -> Dict[str, float]:
        return _parse_json_map(self.FLOW_PMO_PORTFOLIO_ROLE_SALARY_MAP)


def _parse_json_map(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        return {}


_cached_settings: FlowPMOSettings | None = None


def get_settings() -> FlowPMOSettings:
    """Returns the validated settings instance (cached after first call)."""
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = FlowPMOSettings()
    return _cached_settings
