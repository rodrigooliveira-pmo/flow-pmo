#!/usr/bin/env python3
"""
Exporta dados do Jira Cloud para o formato CSV consumido pelo pipeline local.

Uso (PowerShell):
  $env:JIRA_BASE_URL='https://suaempresa.atlassian.net'
  $env:JIRA_EMAIL='seu.email@empresa.com'
  $env:JIRA_API_TOKEN='***'
  python jira_to_pipeline_csv.py --projects W1NNR --out "C:\\Users\\W1 TI\\OneDrive - W1\\Documentos\\Dados\\w1nner-downstream-$(Get-Date -Format yyyyMMdd)-data.csv"

Opcional:
  $env:JIRA_FIELD_MAP='{"blocked_days":"customfield_12345","flagged":"customfield_10021","team":"customfield_10001","organizations":"customfield_10002","sprints":"customfield_10020","epic_name":"customfield_10014","principal":"customfield_10067"}'
  $env:JIRA_STATUS_MAP='{"Sprint Backlog":["Backlog","To Do","Sprint Backlog","Triagem"],"In Progress":["In Progress","Em Progresso","Desenvolvimento"],"Ready to Homologation":["Ready to Homologation"],"Homologation":["Homologation"],"QA Approved Hml":["QA Approved Hml"],"Ready To Staging":["Ready To Staging"],"In Staging":["In Staging"],"QA Approved Staging":["QA Approved Staging"],"Ready for production":["Ready for production"],"Done":["Done","Concluído","Concluido"]}'
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from statistics import median
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import requests

from jira.client import JiraClient
from shared.env_utils import load_env_file, parse_json_env
from shared.text_utils import normalize_text


DEFAULT_STATUS_MAP: Dict[str, List[str]] = {
    "Sprint Backlog": ["Backlog", "To Do", "Sprint Backlog", "Triagem"],
    "In Progress": ["In Progress", "Em Progresso", "Desenvolvimento"],
    "Ready to Homologation": ["Ready to Homologation"],
    "Homologation": ["Homologation"],
    "QA Approved Hml": ["QA Approved Hml"],
    "Ready To Staging": ["Ready To Staging"],
    "In Staging": ["In Staging"],
    "QA Approved Staging": ["QA Approved Staging"],
    "Ready for production": ["Ready for production"],
    "Done": ["Done", "Concluído", "Concluido"],
}

LEGACY_PRODUCTS_STATUS_MAP: Dict[str, List[str]] = {
    "Triagem": ["Triagem"],
    "Backlog": ["Backlog", "To Do", "Sprint Backlog"],
    "Ready to Start": ["Ready to Start", "Ready to start", "Ready for development", "Ready For Development"],
    "In progress": [
        "In Progress",
        "In progress",
        "Em Progresso",
        "Desenvolvimento",
        "Development",
        "In Development",
        "Doing",
    ],
    "ready code review": ["ready code review", "Ready code review", "Ready for code review", "Ready For Code Review"],
    "Code review": ["Code review", "Code Review"],
    "ready testing/Qa": ["ready testing/qa", "Ready testing/qa", "Ready for testing/qa", "Ready for Testing/QA", "Ready for test/qa"],
    "Testing/QA": ["Testing/QA", "Testing / QA", "Testing /Qa", "QA", "Testing"],
    "ready homolog": ["ready homolog", "Ready homolog", "Ready to homologation", "Ready to Homologation", "Ready to staging", "Ready To Staging"],
    "Homolog": ["Homolog", "Homologation", "Staging", "In Staging"],
    "ready for production": ["ready for production", "Ready for production", "Ready For Production"],
    "Itens concluídos": [
        "Itens concluídos",
        "Itens Concluídos",
        "Done",
        "Concluído",
        "Concluido",
    ],
}

DT_IMPROVEMENT_STATUS_MAP: Dict[str, List[str]] = {
    "To Do": ["To Do", "A fazer", "A Fazer"],
    "Discovery": ["Discovery"],
    "Development": ["Development", "Desenvolvimento"],
    "Tech Review": ["Tech Review"],
    "In Validation": ["In Validation", "Em validacao", "Em validação"],
    "Improvement": ["Improvement", "Melhoria"],
    "Done": ["Done", "Concluído", "Concluido"],
}

DT_ADHOC_STAGE_ORDER = ["To Do", "Development", "In Validation", "Done"]
DT_IMPROVEMENT_STAGE_ORDER = ["To Do", "Discovery", "Development", "Tech Review", "In Validation", "Improvement", "Done"]
DT_ADHOC_TYPE_HINTS = {"adhoc", "ad hoc", "bug", "incidente", "incident"}

METADATA_COLUMNS = [
    "ID",
    "Link",
    "Title",
    "Tipo de Problema",
    "Prioridade",
    "Versões de correção",
    "Componentes",
    "Responsável",
    "Criador",
    "Created",
    "Start date",
    "Space",
    "Resolução",
    "Data Cancelled",
    "Etiquetas",
    "Blocked Days",
    "Blocked",
    "Flagged",
    "Story Points",
    "Story point estimate",
    "EffortTShirtSize",
    "Epic Name",
    "Team",
    "Organizations",
    "Sprints",
    "Principal",
    "ParentID",
    "ParentTipo",
    "ParentTitle",
    "HierarchyLinkSource",
    "FeatureLinkID",
    "FeatureLinkTipo",
    "EpicLinkID",
    "EpicLinkTipo",
    "EpicLinkName",
]

DEFAULT_EXCLUDED_ISSUE_TYPES = ["Épico", "Epic", "Iniciativa", "Initiative"]
ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$")
DETAILED_CHANGELOG_COLUMNS = [
    "Projeto",
    "Issue Key",
    "Issue Link",
    "Title",
    "Tipo de Problema",
    "Status Atual",
    "History Id",
    "History Created",
    "History Date",
    "Author",
    "From Status",
    "To Status",
]


def build_csv_columns(stage_order: List[str]) -> List[str]:
    return ["ID", "Link", "Title", *stage_order, *METADATA_COLUMNS[3:]]


def normalize_project_key(project: str) -> str:
    key = str(project or "").strip().upper()
    aliases = {
        "W1NNRI": "W1NNR",
        "W1SFT": "S1NC",
        "DA": "DT",
    }
    return aliases.get(key, key)




FEATURE_TYPE_HINTS = {"feature", "funcionalidade"}
EPIC_TYPE_HINTS = {"epic", "epico"}
STORY_TASK_TYPE_HINTS = {
    "story",
    "user story",
    "historia",
    "historia de usuario",
    "us",
    "task",
    "tarefa",
    "subtarefa",
    "sub task",
    "tech task",
    "task de produto",
}


def issue_type_is_feature(value: str) -> bool:
    return normalize_text(value) in FEATURE_TYPE_HINTS


def issue_type_is_epic(value: str) -> bool:
    return normalize_text(value) in EPIC_TYPE_HINTS


def issue_type_is_storytask(value: str) -> bool:
    norm = normalize_text(value)
    if norm in STORY_TASK_TYPE_HINTS:
        return True
    return ("historia" in norm) or ("task" in norm)


def issue_key_or_blank(value: str) -> str:
    txt = str(value or "").strip()
    return txt if ISSUE_KEY_PATTERN.match(txt) else ""


def compute_storytask_orphan_indicator(rows: List[Dict[str, str]]) -> Dict[str, float | int]:
    total = 0
    orphan = 0
    for row in rows:
        issue_type = str(row.get("Tipo de Problema") or "")
        if not issue_type_is_storytask(issue_type):
            continue
        total += 1
        parent_tipo = str(row.get("ParentTipo") or "")
        has_parent_feature = issue_type_is_feature(parent_tipo)
        has_feature_link = bool(str(row.get("FeatureLinkID") or "").strip())
        has_epic_link = bool(str(row.get("EpicLinkID") or "").strip())
        # Considera órfão apenas quando não há vínculo explícito nem com feature nem com épico.
        if not (has_parent_feature or has_feature_link or has_epic_link):
            orphan += 1
    pct = round(orphan / total * 100, 1) if total else 0.0
    return {"storytask_total": total, "storytask_orfaos": orphan, "pct_storytask_orfaos": pct}


def env_flag_enabled(name: str) -> bool:
    return normalize_text(os.getenv(name, "")) in {"1", "true", "yes", "sim", "on"}


def resolve_excluded_issue_types() -> List[str]:
    if env_flag_enabled("JIRA_INCLUDE_PORTFOLIO_ISSUES"):
        return []

    raw = os.getenv("JIRA_EXCLUDE_ISSUE_TYPES", "").strip()
    if not raw:
        return list(DEFAULT_EXCLUDED_ISSUE_TYPES)

    parsed = [part.strip() for part in raw.split(",")]
    return [name for name in parsed if name]


def quote_jql_string(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def resolve_status_map(projects: List[str]) -> Dict[str, List[str]]:
    env_map = {} if env_flag_enabled("JIRA_IGNORE_STATUS_MAP") else parse_json_env("JIRA_STATUS_MAP", default={})
    if env_map:
        normalized_env: Dict[str, List[str]] = {}
        for k, v in env_map.items():
            if isinstance(v, list):
                normalized_env[str(k)] = [str(item) for item in v]
            else:
                normalized_env[str(k)] = [str(v)]
        return normalized_env

    normalized_projects = {normalize_project_key(p) for p in projects if p}
    if not normalized_projects:
        return DEFAULT_STATUS_MAP

    if normalized_projects.issubset({"W1NNR", "S1NC", "BF"}):
        return LEGACY_PRODUCTS_STATUS_MAP

    if normalized_projects.issubset({"DT"}):
        return DT_IMPROVEMENT_STATUS_MAP

    # Mixed flows in one export should use explicit env override to avoid ambiguous stage order.
    return DEFAULT_STATUS_MAP


def should_use_dt_dual_flow(projects: List[str]) -> bool:
    if (not env_flag_enabled("JIRA_IGNORE_STATUS_MAP")) and os.getenv("JIRA_STATUS_MAP", "").strip():
        return False
    normalized_projects = {normalize_project_key(p) for p in projects if p}
    return bool(normalized_projects) and normalized_projects.issubset({"DT"})


def resolve_dt_stage_order_for_row(row: Dict[str, str]) -> List[str]:
    issue_type = normalize_text(row.get("Tipo de Problema", ""))
    for hint in DT_ADHOC_TYPE_HINTS:
        if hint in issue_type:
            return DT_ADHOC_STAGE_ORDER
    return DT_IMPROVEMENT_STAGE_ORDER


def format_jira_datetime(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return dt.strftime("%d/%m/%Y")


def format_list(values: Iterable[str], as_label_array: bool = False) -> str:
    items = [v for v in values if v]
    if not items:
        return ""
    if as_label_array:
        return "[" + ",".join(items) + "]"
    return ", ".join(items)


def safe_get(d: Dict[str, Any], *path: str) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def extract_first_status_dates(
    issue_fields: Dict[str, Any],
    changelog: List[Dict[str, Any]],
    status_map: Dict[str, List[str]],
    normalized_status_map: Optional[Dict[str, set[str]]] = None,
    date_mode: str = "first",
) -> Dict[str, str]:
    mode = str(date_mode or "first").strip().lower()
    if mode not in {"first", "latest"}:
        mode = "first"
    normalized = normalized_status_map or {
        col: {name.strip().lower() for name in names}
        for col, names in status_map.items()
    }
    status_dates: Dict[str, Optional[str]] = {col: None for col in status_map.keys()}
    done_col_names = {"done", "concluido", "concluído", "itens concluídos", "itens concluidos"}
    done_status_names = {
        "done",
        "concluido",
        "concluído",
        "closed",
        "resolved",
        "completed",
    }
    done_columns: set[str] = set()
    for col, allowed in normalized.items():
        col_norm = str(col).strip().lower()
        if col_norm in done_col_names or any(status in done_status_names for status in allowed):
            done_columns.add(col)

    created = issue_fields.get("created")
    current_status = safe_get(issue_fields, "status", "name")
    if created and current_status:
        current_status_norm = str(current_status).strip().lower()
        for col, allowed in normalized.items():
            if current_status_norm in allowed:
                # Do not set terminal "Done" date from issue creation;
                # prefer changelog transition date (or resolution date fallback).
                if col in done_columns:
                    continue
                status_dates[col] = created

    sorted_changes = sorted(changelog, key=lambda h: h.get("created") or "")
    for history in sorted_changes:
        when = history.get("created")
        for item in history.get("items", []):
            if item.get("field") != "status":
                continue
            to_status = str(item.get("toString") or "").strip().lower()
            if not to_status:
                continue
            for col, allowed in normalized.items():
                if to_status not in allowed:
                    continue
                if mode == "first":
                    if status_dates[col] is None:
                        status_dates[col] = when
                else:
                    status_dates[col] = when

    # Fallback for terminal status when changelog transition is unavailable.
    resolution_date = issue_fields.get("resolutiondate")
    if resolution_date and current_status:
        current_status_norm = str(current_status).strip().lower()
        for col in done_columns:
            allowed = normalized.get(col, set())
            if current_status_norm not in allowed:
                continue
            if mode == "first":
                if status_dates.get(col) is None:
                    status_dates[col] = resolution_date
            else:
                status_dates[col] = resolution_date

    return {k: format_jira_datetime(v) for k, v in status_dates.items()}


def extract_first_transition_date(
    issue_fields: Dict[str, Any],
    changelog: List[Dict[str, Any]],
    target_statuses: List[str],
) -> str:
    targets = {str(s).strip().lower() for s in target_statuses if str(s).strip()}
    if not targets:
        return ""
    sorted_changes = sorted(changelog, key=lambda h: h.get("created") or "")
    for history in sorted_changes:
        when = history.get("created")
        for item in history.get("items", []):
            if item.get("field") != "status":
                continue
            to_status = str(item.get("toString") or "").strip().lower()
            if to_status in targets:
                return format_jira_datetime(when)
    # Fallback: if currently cancelled and resolution date exists, use it
    current_status = str(safe_get(issue_fields, "status", "name") or "").strip().lower()
    if current_status in targets:
        return format_jira_datetime(issue_fields.get("resolutiondate"))
    return ""


def get_embedded_changelog(issue: Dict[str, Any]) -> tuple[List[Dict[str, Any]], int]:
    changelog = issue.get("changelog")
    if not isinstance(changelog, dict):
        return [], 0

    histories = changelog.get("histories")
    if not isinstance(histories, list):
        histories = changelog.get("values")
    if not isinstance(histories, list):
        histories = []

    total_raw = changelog.get("total")
    try:
        total = int(total_raw) if total_raw is not None else len(histories)
    except (TypeError, ValueError):
        total = len(histories)
    return histories, max(total, len(histories))


def _discover_tshirt_field_id(base_url: str, email: str, token: str) -> str:
    """Descobre o ID do campo T-shirt size na instância Jira via /rest/api/3/field.

    Usa a mesma lógica de descoberta de jira_portfolio_to_csv.py:
    1. Match exato no nome normalizado (ex.: "t shirt size", "effort tshirt size")
    2. Match parcial por palavras-chave (size + shirt + effort)
    3. Fallback por schema custom (contém "tshirt" ou "t-shirt")

    Retorna o field ID (ex.: "customfield_10042") ou "" se não encontrado.
    Suporte a override via JIRA_FIELD_MAP: effort_tshirt_size=customfield_XXXXX
    """
    try:
        resp = requests.get(
            f"{base_url}/rest/api/3/field",
            auth=(email, token),
            headers={"Accept": "application/json"},
            timeout=60,
        )
        resp.raise_for_status()
        field_defs = resp.json()
    except Exception:
        return ""

    if not isinstance(field_defs, list):
        return ""

    def _norm(txt: str) -> str:
        return " ".join(str(txt or "").strip().lower().replace("-", " ").split())

    exact_targets = {"effort t shirt size", "effort tshirt size", "t shirt size", "tshirt size"}

    # 1) Match exato no nome normalizado
    for f in field_defs:
        name = _norm((f or {}).get("name") or "")
        fid = str((f or {}).get("id") or "").strip()
        if name in exact_targets and fid:
            return fid

    # 2) Match parcial: size + shirt + effort
    for f in field_defs:
        name = _norm((f or {}).get("name") or "")
        fid = str((f or {}).get("id") or "").strip()
        if not fid:
            continue
        if "size" in name and ("shirt" in name or "tshirt" in name) and "effort" in name:
            return fid

    # 3) Fallback por schema custom
    for f in field_defs:
        schema_custom = str(((f or {}).get("schema") or {}).get("custom") or "").strip().lower()
        fid = str((f or {}).get("id") or "").strip()
        if fid and ("tshirt" in schema_custom or "t-shirt" in schema_custom):
            return fid

    return ""


def build_issue_row(
    base_url: str,
    issue: Dict[str, Any],
    status_dates: Dict[str, str],
    field_map: Dict[str, str],
    stage_order: List[str],
    csv_columns: List[str],
    cancelled_date: str = "",
) -> Dict[str, str]:
    fields = issue.get("fields", {})

    key = issue.get("key", "")
    fix_versions = [v.get("name", "") for v in fields.get("fixVersions", [])]
    components = [c.get("name", "") for c in fields.get("components", [])]
    labels = fields.get("labels", []) or []
    assignee = safe_get(fields, "assignee", "displayName") or ""
    creator = safe_get(fields, "creator", "displayName") or ""
    project_key = safe_get(fields, "project", "key") or ""

    blocked_days_val = ""
    blocked_custom = field_map.get("blocked_days")
    if blocked_custom:
        raw = fields.get(blocked_custom)
        blocked_days_val = "" if raw is None else str(raw)

    flagged_custom = field_map.get("flagged")
    flagged_value = fields.get(flagged_custom) if flagged_custom else None
    if isinstance(flagged_value, list):
        flagged_str = format_list([str(v) for v in flagged_value], as_label_array=True)
    else:
        flagged_str = str(flagged_value or "")

    blocked_value = "yes" if flagged_str else "no"

    parent_id = str(safe_get(fields, "parent", "key") or "")
    parent_tipo = str(safe_get(fields, "parent", "fields", "issuetype", "name") or "")
    parent_summary = str(safe_get(fields, "parent", "fields", "summary") or "")
    epic_name = ""
    if field_map.get("epic_name"):
        epic_raw = fields.get(field_map["epic_name"])
        epic_name = str(epic_raw or "")
    if not epic_name:
        epic_name = parent_summary

    def custom_as_text(key_name: str, as_label_array: bool = False) -> str:
        cf = field_map.get(key_name)
        if not cf:
            return ""
        val = fields.get(cf)
        if isinstance(val, list):
            names: List[str] = []
            for item in val:
                if isinstance(item, dict):
                    names.append(str(item.get("name") or item.get("value") or item.get("displayName") or ""))
                else:
                    names.append(str(item))
            return format_list(names, as_label_array=as_label_array)
        if isinstance(val, dict):
            return str(val.get("name") or val.get("value") or val.get("displayName") or "")
        return str(val or "")

    def custom_as_number_text(key_name: str, fallback_field_ids: List[str]) -> str:
        value = custom_as_text(key_name)
        if value:
            return value
        for field_id in fallback_field_ids:
            raw = fields.get(field_id)
            if raw is None or raw == "":
                continue
            if isinstance(raw, float) and raw.is_integer():
                return str(int(raw))
            return str(raw)
        return ""

    def custom_as_date_text(key_name: str, fallback_field_ids: List[str]) -> str:
        value = custom_as_text(key_name)
        if value:
            formatted = format_jira_datetime(value)
            return formatted or value
        for field_id in fallback_field_ids:
            raw = fields.get(field_id)
            if raw is None or raw == "":
                continue
            formatted = format_jira_datetime(str(raw))
            return formatted or str(raw)
        return ""

    principal_value = custom_as_text("principal")
    story_points_value = custom_as_number_text("story_points", ["customfield_10026", "customfield_10028"])
    story_point_estimate_value = custom_as_number_text("story_point_estimate", ["customfield_10016"])
    effort_tshirt_size_value = custom_as_text("effort_tshirt_size")
    start_date_value = custom_as_date_text("start_date", ["startdate"])

    # Defensive fix for field-map semantic inversion:
    # some environments configure "epic_name" as a custom field that actually stores a key (ex.: W1NNER-1771),
    # while "principal" remains empty. In this case preserve the key in "Principal" and keep Epic Name as summary/blank.
    if epic_name and not principal_value and ISSUE_KEY_PATTERN.match(epic_name):
        principal_value = epic_name
        epic_name = ""

    parent_id_key = issue_key_or_blank(parent_id)
    principal_key = issue_key_or_blank(principal_value)
    epic_name_key = issue_key_or_blank(epic_name)

    feature_link_id = ""
    feature_link_tipo = ""
    epic_link_id = ""
    epic_link_tipo = ""
    epic_link_name = ""
    link_sources: List[str] = []

    if parent_id_key:
        if issue_type_is_feature(parent_tipo):
            feature_link_id = parent_id_key
            feature_link_tipo = parent_tipo
            link_sources.append("parent_feature")
        elif issue_type_is_epic(parent_tipo):
            epic_link_id = parent_id_key
            epic_link_tipo = parent_tipo
            epic_link_name = parent_summary
            link_sources.append("parent_epic")
        else:
            link_sources.append("parent_other")

    if principal_key and not epic_link_id:
        epic_link_id = principal_key
        epic_link_tipo = "Epic/Principal"
        link_sources.append("principal_key")

    if epic_name_key and not epic_link_id:
        epic_link_id = epic_name_key
        epic_link_tipo = "EpicLinkCustomField"
        link_sources.append("epic_name_key")

    if not epic_link_name and epic_name and not ISSUE_KEY_PATTERN.match(epic_name):
        epic_link_name = epic_name
    if epic_link_name and ("epic_name_text" not in link_sources):
        link_sources.append("epic_name_text")

    row = {
        "ID": key,
        "Link": f"{base_url}/browse/{key}" if key else "",
        "Title": str(fields.get("summary") or ""),
        "Tipo de Problema": str(safe_get(fields, "issuetype", "name") or ""),
        "Prioridade": str(safe_get(fields, "priority", "name") or ""),
        "Versões de correção": format_list(fix_versions),
        "Componentes": format_list(components),
        "Responsável": assignee,
        "Criador": creator,
        "Created": format_jira_datetime(fields.get("created")),
        "Start date": start_date_value,
        "Space": project_key,
        "Resolução": str(safe_get(fields, "resolution", "name") or ""),
        "Data Cancelled": cancelled_date,
        "Etiquetas": format_list([str(x) for x in labels], as_label_array=True),
        "Blocked Days": blocked_days_val,
        "Blocked": blocked_value,
        "Flagged": flagged_str,
        "Story Points": story_points_value,
        "Story point estimate": story_point_estimate_value,
        "EffortTShirtSize": effort_tshirt_size_value,
        "Epic Name": epic_name,
        "Team": custom_as_text("team"),
        "Organizations": custom_as_text("organizations"),
        "Sprints": custom_as_text("sprints", as_label_array=True),
        "Principal": principal_value,
        "ParentID": parent_id,
        "ParentTipo": parent_tipo,
        "ParentTitle": parent_summary,
        "HierarchyLinkSource": "|".join(link_sources),
        "FeatureLinkID": feature_link_id,
        "FeatureLinkTipo": feature_link_tipo,
        "EpicLinkID": epic_link_id,
        "EpicLinkTipo": epic_link_tipo,
        "EpicLinkName": epic_link_name,
    }

    for stage in stage_order:
        row[stage] = status_dates.get(stage, "")

    for c in csv_columns:
        row.setdefault(c, "")
    return row


def build_jql(projects: List[str], jql_extra: str, exclude_issue_types: Optional[List[str]] = None) -> str:
    proj_clause = ", ".join(projects)
    clauses = [f"project in ({proj_clause})"]

    if exclude_issue_types:
        issue_types = [quote_jql_string(name) for name in exclude_issue_types if str(name).strip()]
        if issue_types:
            clauses.append(f"issuetype not in ({', '.join(issue_types)})")

    if jql_extra.strip():
        clauses.append(f"({jql_extra.strip()})")

    return " AND ".join(clauses)





def parse_pipeline_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y")
    except ValueError:
        return None


def percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * q
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    if high == low:
        return float(ordered[low])
    fraction = pos - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * fraction)


def compute_bottleneck_summary(
    rows: List[Dict[str, str]],
    stage_order: List[str],
    row_stage_order_resolver: Optional[Callable[[Dict[str, str]], List[str]]] = None,
) -> List[Dict[str, float | int | str]]:
    stage_durations: Dict[str, List[float]] = {}
    for i in range(len(stage_order) - 1):
        stage_durations.setdefault(stage_order[i], [])

    for row in rows:
        current_order = stage_order
        if row_stage_order_resolver is not None:
            try:
                resolved = row_stage_order_resolver(row)
                if isinstance(resolved, list) and len(resolved) >= 2:
                    current_order = resolved
            except Exception:
                current_order = stage_order

        for i in range(len(current_order) - 1):
            current_stage = current_order[i]
            next_stage = current_order[i + 1]
            stage_durations.setdefault(current_stage, [])
            start_dt = parse_pipeline_date(row.get(current_stage, ""))
            end_dt = parse_pipeline_date(row.get(next_stage, ""))
            if not start_dt or not end_dt:
                continue
            duration_days = (end_dt - start_dt).days
            if duration_days < 0:
                continue
            stage_durations[current_stage].append(float(duration_days))

    summary: List[Dict[str, float | int | str]] = []
    for stage, durations in stage_durations.items():
        if not durations:
            continue
        summary.append(
            {
                "Etapa": stage,
                "Qtde Issues": len(durations),
                "Media Dias": round(sum(durations) / len(durations), 2),
                "Mediana Dias": round(float(median(durations)), 2),
                "P90 Dias": round(percentile(durations, 0.90), 2),
                "Max Dias": round(max(durations), 2),
            }
        )

    summary.sort(key=lambda item: float(item["Media Dias"]), reverse=True)
    return summary


def write_bottleneck_csv(path: str, summary: List[Dict[str, float | int | str]]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Etapa", "Qtde Issues", "Media Dias", "Mediana Dias", "P90 Dias", "Max Dias"],
        )
        writer.writeheader()
        writer.writerows(summary)


def build_default_artifact_path(csv_out: str, suffix: str) -> str:
    out_path = Path(csv_out)
    stem = out_path.stem
    return str(out_path.with_name(f"{stem}{suffix}"))


def extract_detailed_status_changelog_rows(
    base_url: str,
    issue: Dict[str, Any],
    changelog: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    fields = issue.get("fields", {}) or {}
    key = str(issue.get("key") or "")
    project_key = str(safe_get(fields, "project", "key") or "")
    title = str(fields.get("summary") or "")
    issue_type = str(safe_get(fields, "issuetype", "name") or "")
    current_status = str(safe_get(fields, "status", "name") or "")
    issue_link = f"{base_url}/browse/{key}" if key else ""

    rows: List[Dict[str, str]] = []
    for history in sorted(changelog, key=lambda h: h.get("created") or ""):
        history_created = str(history.get("created") or "")
        history_id = str(history.get("id") or "")
        author = (
            str(safe_get(history, "author", "displayName") or "")
            or str(safe_get(history, "author", "emailAddress") or "")
            or str(safe_get(history, "author", "accountId") or "")
        )
        for item in history.get("items", []) or []:
            if item.get("field") != "status":
                continue
            from_status = str(item.get("fromString") or "")
            to_status = str(item.get("toString") or "")
            rows.append(
                {
                    "Projeto": project_key,
                    "Issue Key": key,
                    "Issue Link": issue_link,
                    "Title": title,
                    "Tipo de Problema": issue_type,
                    "Status Atual": current_status,
                    "History Id": history_id,
                    "History Created": history_created,
                    "History Date": format_jira_datetime(history_created),
                    "Author": author,
                    "From Status": from_status,
                    "To Status": to_status,
                }
            )
    return rows


def write_detailed_changelog_csv(path: str, rows: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DETAILED_CHANGELOG_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_bottleneck_bar_chart(path: str, summary: List[Dict[str, float | int | str]]) -> bool:
    if not summary:
        return False

    try:
        import plotly.graph_objects as go
    except ImportError:
        print("Aviso: plotly não está instalado; gráfico de gargalo não foi gerado.")
        return False

    stages = [str(item["Etapa"]) for item in summary]
    avg_days = [float(item["Media Dias"]) for item in summary]
    sample_sizes = [int(item["Qtde Issues"]) for item in summary]

    fig = go.Figure(
        go.Bar(
            x=avg_days,
            y=stages,
            orientation="h",
            text=[f"{value:.2f} d" for value in avg_days],
            textposition="outside",
            hovertemplate="Etapa: %{y}<br>Média: %{x:.2f} dias<br>Issues: %{customdata}<extra></extra>",
            customdata=sample_sizes,
            marker_color="#1f77b4",
        )
    )
    fig.update_layout(
        title="Ranking de Gargalos do Fluxo (Maior para Menor)",
        xaxis_title="Tempo médio na etapa (dias)",
        yaxis_title="Etapa",
        yaxis=dict(autorange="reversed"),
        template="plotly_white",
        height=max(420, 90 + len(stages) * 45),
        margin=dict(l=180, r=40, t=80, b=60),
    )

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.write_html(path, include_plotlyjs="cdn")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta Jira para CSV no formato do pipeline.")
    parser.add_argument("--projects", nargs="+", required=True, help="Chaves dos projetos Jira (ex: W1NNR BF DT)")
    parser.add_argument("--out", required=True, help="Caminho do CSV de saída")
    parser.add_argument("--jql-extra", default="", help="Filtro JQL adicional")
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Número de workers para buscar changelog em paralelo (default: 8).",
    )
    parser.add_argument(
        "--env-file",
        default=str(Path(__file__).with_name("jira_env.txt")),
        help="Arquivo .txt com variáveis no formato KEY=VALUE (default: jira_env.txt ao lado do script)",
    )
    parser.add_argument(
        "--bottleneck-out",
        default="",
        help="CSV opcional com ranking de gargalos por etapa (default: <out>_bottlenecks.csv)",
    )
    parser.add_argument(
        "--bottleneck-chart",
        default="",
        help="HTML opcional com gráfico de barras de gargalos (somente se informado).",
    )
    parser.add_argument(
        "--detailed-changelog-out",
        default="",
        help=(
            "CSV opcional com transições reais de status do changelog Jira "
            "(default: desabilitado; quando informado, gera um arquivo detalhado por execução/projeto)."
        ),
    )
    parser.add_argument(
        "--search-expand-changelog",
        action="store_true",
        help=(
            "Inclui expand=changelog na busca inicial de issues. "
            "Desligado por padrão para evitar payloads grandes/travamentos em projetos maiores."
        ),
    )
    args = parser.parse_args()

    load_env_file(args.env_file, overwrite=True)

    base_url = os.getenv("JIRA_BASE_URL", "").strip()
    email = os.getenv("JIRA_EMAIL", "").strip()
    token = os.getenv("JIRA_API_TOKEN", "").strip()

    if not base_url or not email or not token:
        print("Erro: defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN.", file=sys.stderr)
        return 2

    field_map = parse_json_env("JIRA_FIELD_MAP", default={})

    # ── Descoberta automática do campo T-shirt size ────────────────────────────
    # Tenta via JIRA_FIELD_MAP (override manual) antes de chamar a API de campos.
    if not field_map.get("effort_tshirt_size"):
        _tshirt_fid = _discover_tshirt_field_id(base_url, email, token)
        if _tshirt_fid:
            field_map["effort_tshirt_size"] = _tshirt_fid
            print(f"T-shirt size field descoberto automaticamente: {_tshirt_fid}")
        else:
            print("T-shirt size field não encontrado na instância Jira (EffortTShirtSize ficará vazio).")
    else:
        print(f"T-shirt size field configurado via JIRA_FIELD_MAP: {field_map['effort_tshirt_size']}")

    status_map = resolve_status_map(args.projects)
    stage_order = list(status_map.keys())
    csv_columns = build_csv_columns(stage_order)
    print(f"Fluxo de status aplicado ({len(stage_order)} etapas): {', '.join(stage_order)}")
    dt_dual_flow_enabled = should_use_dt_dual_flow(args.projects)
    if dt_dual_flow_enabled:
        print(
            "Fluxo DT por tipo habilitado: melhorias (To Do -> Discovery -> Development -> Tech Review -> "
            "In Validation -> Improvement -> Done) e ad-hoc/bug/incidente (To Do -> Development -> In Validation -> Done)."
        )

    fields_to_fetch = [
        "summary",
        "issuetype",
        "priority",
        "fixVersions",
        "components",
        "assignee",
        "creator",
        "project",
        "resolution",
        "labels",
        "versions",
        "parent",
        "status",
        "created",
        "startdate",
        "resolutiondate",
        "customfield_10016",
        "customfield_10026",
        "customfield_10028",
    ]

    for logical_name, jira_field in field_map.items():
        if jira_field and jira_field not in fields_to_fetch:
            fields_to_fetch.append(jira_field)
            if logical_name == "effort_tshirt_size":
                print(f"Adicionado {jira_field} (EffortTShirtSize) ao fetch de campos.")

    excluded_issue_types = resolve_excluded_issue_types()
    if excluded_issue_types:
        print(f"Excluindo issue types no downstream: {', '.join(excluded_issue_types)}")
    jql = build_jql(args.projects, args.jql_extra, exclude_issue_types=excluded_issue_types)
    print(f"Consultando Jira com JQL: {jql}")

    client = JiraClient(base_url=base_url, email=email, api_token=token)
    search_expand = ["changelog"] if bool(args.search_expand_changelog) else None
    if search_expand:
        print("Busca inicial com expand=changelog habilitada (payload maior).")
    else:
        print("Busca inicial sem expand=changelog (modo recomendado para projetos grandes).")
    issues = client.search_issues(jql=jql, fields=fields_to_fetch, expand=search_expand)
    print(f"Issues encontradas: {len(issues)}")
    if not issues:
        print("Nenhuma issue retornada para o JQL informado.")
        try:
            visible_projects = client.list_visible_projects(page_size=100)
            if visible_projects:
                keys = [str(p.get("key", "")) for p in visible_projects if p.get("key")]
                print(f"Projetos visíveis para este usuário/token: {', '.join(keys)}")
            else:
                print("Não foi possível listar projetos visíveis (lista vazia).")
        except Exception as exc:
            print(f"Não foi possível listar projetos visíveis: {exc}")

    workers = max(1, int(args.workers))
    rows: List[Dict[str, str]] = []
    detailed_changelog_enabled = bool(str(args.detailed_changelog_out).strip())
    detailed_changelog_rows: List[Dict[str, str]] = []
    processing_errors: List[str] = []
    normalized_status_map = {
        col: {name.strip().lower() for name in names}
        for col, names in status_map.items()
    }
    status_date_mode = str(os.getenv("JIRA_STATUS_DATE_MODE", "latest") or "latest").strip().lower()
    if status_date_mode not in {"first", "latest"}:
        print(f"Valor inválido em JIRA_STATUS_DATE_MODE={status_date_mode!r}; usando 'latest'.")
        status_date_mode = "latest"
    print(f"Modo de datas por etapa (status): {status_date_mode}")
    worker_local = threading.local()

    def get_worker_client() -> JiraClient:
        local_client = getattr(worker_local, "client", None)
        if local_client is None:
            # Keep one client/session per worker thread for persistent connections.
            local_client = JiraClient(base_url=base_url, email=email, api_token=token)
            worker_local.client = local_client
        return local_client

    def process_one(
        index: int,
        issue_data: Dict[str, Any],
    ) -> tuple[int, Optional[Dict[str, str]], List[Dict[str, str]], Optional[str]]:
        key = issue_data.get("key", "")
        if not key:
            return index, None, [], None
        try:
            local_client = get_worker_client()
            embedded_histories, embedded_total = get_embedded_changelog(issue_data)
            if embedded_histories and len(embedded_histories) >= embedded_total:
                changelog = embedded_histories
            elif embedded_histories:
                changelog = local_client.get_issue_changelog(
                    key,
                    start_at=len(embedded_histories),
                    initial_histories=embedded_histories,
                    total_hint=embedded_total,
                )
            else:
                changelog = local_client.get_issue_changelog(key)

            status_dates = extract_first_status_dates(
                issue_data.get("fields", {}),
                changelog,
                status_map,
                normalized_status_map=normalized_status_map,
                date_mode=status_date_mode,
            )
            cancelled_date = extract_first_transition_date(
                issue_data.get("fields", {}),
                changelog,
                ["Cancelled", "Canceled", "Cancelado", "Cancelada"],
            )
            row = build_issue_row(
                base_url=base_url,
                issue=issue_data,
                status_dates=status_dates,
                field_map=field_map,
                stage_order=stage_order,
                csv_columns=csv_columns,
                cancelled_date=cancelled_date,
            )
            changelog_rows = []
            if detailed_changelog_enabled:
                changelog_rows = extract_detailed_status_changelog_rows(
                    base_url=base_url,
                    issue=issue_data,
                    changelog=changelog,
                )
            return index, row, changelog_rows, None
        except Exception as exc:
            return index, None, [], f"{key}: {exc}"

    if workers == 1 or len(issues) <= 1:
        for idx0, issue in enumerate(issues):
            _, row, changelog_rows, err = process_one(idx0, issue)
            if row is not None:
                rows.append(row)
            if changelog_rows:
                detailed_changelog_rows.extend(changelog_rows)
            if err:
                processing_errors.append(err)
            done = idx0 + 1
            if done % 100 == 0:
                print(f"Processadas {done}/{len(issues)} issues...")
    else:
        ordered_rows: List[Optional[Dict[str, str]]] = [None] * len(issues)
        ordered_changelog_rows: List[Optional[List[Dict[str, str]]]] = [None] * len(issues)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(process_one, idx0, issue) for idx0, issue in enumerate(issues)]
            done = 0
            for fut in as_completed(futures):
                idx0, row, changelog_rows, err = fut.result()
                if row is not None:
                    ordered_rows[idx0] = row
                if detailed_changelog_enabled:
                    ordered_changelog_rows[idx0] = changelog_rows
                if err:
                    processing_errors.append(err)
                done += 1
                if done % 100 == 0:
                    print(f"Processadas {done}/{len(issues)} issues...")
        rows = [r for r in ordered_rows if r is not None]
        if detailed_changelog_enabled:
            for chunk in ordered_changelog_rows:
                if chunk:
                    detailed_changelog_rows.extend(chunk)

    if processing_errors:
        print(f"Aviso: {len(processing_errors)} issues com falha no processamento.")
        for msg in processing_errors[:5]:
            print(f" - {msg}")
        if len(processing_errors) > 5:
            print(" - ...")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV gerado: {args.out}")

    orphan_metrics = compute_storytask_orphan_indicator(rows)
    print(
        "Indicador fluxo operacional - % histórias/tasks órfãos "
        f"(exato via hierarquia exportada): {orphan_metrics['pct_storytask_orfaos']}% "
        f"({orphan_metrics['storytask_orfaos']}/{orphan_metrics['storytask_total']})"
    )

    if detailed_changelog_enabled:
        detailed_changelog_out = str(args.detailed_changelog_out).strip()
        write_detailed_changelog_csv(detailed_changelog_out, detailed_changelog_rows)
        print(
            f"Changelog detalhado real (transições de status) salvo em: {detailed_changelog_out} "
            f"(linhas={len(detailed_changelog_rows)})"
        )

    summary = compute_bottleneck_summary(
        rows=rows,
        stage_order=stage_order,
        row_stage_order_resolver=resolve_dt_stage_order_for_row if dt_dual_flow_enabled else None,
    )

    if not summary:
        print("Aviso: sem dados suficientes para calcular gargalo por etapa.")
        return 0

    bottleneck_out = args.bottleneck_out or build_default_artifact_path(args.out, "_bottlenecks.csv")
    bottleneck_chart = args.bottleneck_chart.strip()

    write_bottleneck_csv(bottleneck_out, summary)
    print(f"Ranking de gargalos salvo em: {bottleneck_out}")

    if bottleneck_chart:
        chart_written = write_bottleneck_bar_chart(bottleneck_chart, summary)
        if chart_written:
            print(f"Gráfico de gargalos salvo em: {bottleneck_chart}")

    print("Top 5 gargalos (maior para menor):")
    for item in summary[:5]:
        print(
            f" - {item['Etapa']}: média {item['Media Dias']:.2f} dias "
            f"(issues={item['Qtde Issues']}, p90={item['P90 Dias']:.2f})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
