#!/usr/bin/env python3
"""
Exporta uma base mensal de CAPEX a partir de worklogs do Jira, enriquecendo cada
apontamento com a hierarquia de portfolio/fluxo (Epic -> Feature -> Item) e com
uma classificacao auditavel de "Atividade Desenvolvida".

Saidas:
  - CSV detalhado (1 linha = 1 apontamento Jira)
  - CSV resumo mensal consolidado
  - XLSX opcional com abas RawWorklogs / ResumoMensal, quando pandas estiver disponivel
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

try:
    import pandas as pd
except Exception:  # pragma: no cover - fallback operacional
    pd = None

from jira.client import JiraClient
from shared.env_utils import load_env_file, parse_json_env
from shared.text_utils import normalize_text


RAW_COLUMNS = [
    "MesCompetencia",
    "ID do Projeto",
    "Descrição do Ativo",
    "Tipo do Ativo",
    "Colaborador",
    "Data do Apontamento das Horas",
    "Horas",
    "Atividade Desenvolvida",
    "Atividade Desenvolvida Raw",
    "Atividade Desenvolvida Normalizada",
    "Origem Horas",
    "Fonte Atividade",
    "Regra Atividade",
    "ConfidenceScore",
    "Issue Key",
    "Issue Link",
    "Issue Summary",
    "Issue Type",
    "Projeto Jira",
    "Status Atual",
    "Epic ID",
    "Epic Title",
    "Feature ID",
    "Feature Title",
    "Parent ID",
    "Parent Title",
    "Hierarchy Source",
    "Worklog ID",
    "Worklog Author AccountId",
    "Worklog Updated At",
]

SUMMARY_COLUMNS = [
    "MesCompetencia",
    "ID do Projeto",
    "Descrição do Ativo",
    "Tipo do Ativo",
    "Colaborador",
    "Atividade Desenvolvida",
    "Horas",
    "Qtd Apontamentos",
    "Qtd Issues",
    "Origem Horas",
    "Fonte Atividade",
    "Projeto Jira",
    "Epic ID",
    "Feature ID",
]

ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$")

FEATURE_TYPE_HINTS = {"feature", "funcionalidade"}
EPIC_TYPE_HINTS = {"epic", "epico", "epico de portfolio", "epico portfolio"}

DISCOVERY_HINTS = {
    "discovery",
    "refinamento",
    "refinement",
    "triagem",
    "backlog grooming",
    "alinhamento de requisito",
    "levantamento",
    "analise funcional",
}
REVIEW_HINTS = {
    "review",
    "revisao",
    "code review",
    "pull request",
    "pr ",
    "aprovar pr",
    "aprovacao pr",
}
QA_HINTS = {
    "teste",
    "teste funcional",
    "testes",
    "qa",
    "validacao",
    "validacao funcional",
}
HOMOLOG_HINTS = {"homolog", "homologacao", "uat"}
DEPLOY_HINTS = {"deploy", "release", "publicacao", "producao", "go live"}
SUPPORT_HINTS = {"suporte", "sustentacao", "support", "incidente", "incident", "chamado"}
DATA_HINTS = {"etl", "pipeline", "integracao", "integracoes", "dados", "data lake", "sql", "api", "conector"}
ARCH_HINTS = {"arquitetura", "refatoracao", "refactor", "tech debt", "debito tecnico", "observabilidade", "performance"}
MANAGEMENT_HINTS = {"alinhamento", "reuniao tecnica", "planejamento tecnico", "sync tecnico", "cerimonia tecnica"}
PROJECT_ALIASES = {
    "W1NNR": ["W1NNR", "W1NNRI"],
    "S1NC": ["S1NC", "W1SFT"],
    "DT": ["DT", "DA"],
}


def iter_chunks(values: Sequence[str], size: int) -> Iterator[List[str]]:
    for idx in range(0, len(values), size):
        yield list(values[idx : idx + size])


def quote_jql_string(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def parse_month_range(month_str: str) -> tuple[date, date]:
    try:
        month_start = datetime.strptime(month_str, "%Y-%m").date().replace(day=1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Mes invalido: {month_str!r}. Use YYYY-MM.") from exc

    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1, day=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1, day=1)
    month_end = next_month - timedelta(days=1)
    return month_start, month_end


def parse_iso_date(value: str, field_name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{field_name} invalido: {value!r}. Use YYYY-MM-DD.") from exc


def resolve_default_date_range(args: argparse.Namespace) -> tuple[date, date]:
    if args.date_from or args.date_to:
        if not (args.date_from and args.date_to):
            raise argparse.ArgumentTypeError("Use --date-from e --date-to juntos, ou apenas --month.")
        start = parse_iso_date(args.date_from, "date-from")
        end = parse_iso_date(args.date_to, "date-to")
        if end < start:
            raise argparse.ArgumentTypeError("--date-to nao pode ser menor que --date-from.")
        return start, end

    month_value = args.month or datetime.now().strftime("%Y-%m")
    return parse_month_range(month_value)


def resolve_default_output_paths(projects: List[str], start_date: date, end_date: date) -> tuple[str, str, str]:
    if os.name == "nt":
        data_folder = r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados"
    else:
        data_folder = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "CloudStorage",
            "OneDrive-W1",
            "Documentos",
            "Dados",
        )

    os.makedirs(data_folder, exist_ok=True)
    project_tag = "-".join(sorted({p.strip().lower() for p in projects if p.strip()}))
    period_tag = f"{start_date:%Y%m%d}-{end_date:%Y%m%d}"
    raw_out = os.path.join(data_folder, f"capex-{project_tag}-{period_tag}-raw.csv")
    summary_out = os.path.join(data_folder, f"capex-{project_tag}-{period_tag}-mensal.csv")
    xlsx_out = os.path.join(data_folder, f"capex-{project_tag}-{period_tag}.xlsx")
    return raw_out, summary_out, xlsx_out


def expand_project_keys(projects: Sequence[str]) -> List[str]:
    expanded: List[str] = []
    seen: set[str] = set()
    for project in projects:
        key = str(project or "").strip().upper()
        variants = PROJECT_ALIASES.get(key, [key])
        for variant in variants:
            if variant and variant not in seen:
                seen.add(variant)
                expanded.append(variant)
    return expanded


def build_jql(projects: List[str], jql_extra: str, start_date: date, end_date: date, date_field: str = "worklogDate") -> str:
    clauses = [f"project in ({', '.join(projects)})"]
    clauses.append(
        f"{date_field} >= {quote_jql_string(start_date.strftime('%Y-%m-%d'))} "
        f"AND {date_field} <= {quote_jql_string(end_date.strftime('%Y-%m-%d'))}"
    )
    if jql_extra.strip():
        clauses.append(f"({jql_extra.strip()})")
    return " AND ".join(clauses)


def issue_key_or_blank(value: Any) -> str:
    txt = str(value or "").strip()
    return txt if ISSUE_KEY_PATTERN.match(txt) else ""


def extract_custom_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("name") or item.get("value") or item.get("displayName") or item.get("text") or ""))
            else:
                parts.append(str(item))
        return ", ".join([part for part in parts if part.strip()])
    if isinstance(value, dict):
        return str(
            value.get("name")
            or value.get("value")
            or value.get("displayName")
            or value.get("text")
            or value.get("id")
            or ""
        )
    return str(value)


def custom_field_as_text(fields: Dict[str, Any], field_id: str) -> str:
    if not field_id:
        return ""
    return extract_custom_text(fields.get(field_id)).strip()


def is_feature_issue(issue_type_name: str) -> bool:
    return normalize_text(issue_type_name) in FEATURE_TYPE_HINTS


def is_epic_issue(issue_type_name: str) -> bool:
    return normalize_text(issue_type_name) in EPIC_TYPE_HINTS


def resolve_hierarchy_links(
    *,
    fields: Dict[str, Any],
    field_map: Dict[str, Any],
    parent_id: str,
    parent_tipo: str,
    parent_summary: str,
) -> Dict[str, str]:
    epic_name = custom_field_as_text(fields, str(field_map.get("epic_name") or "").strip())
    principal_value = custom_field_as_text(fields, str(field_map.get("principal") or "").strip())

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
        if is_feature_issue(parent_tipo):
            feature_link_id = parent_id_key
            feature_link_tipo = parent_tipo
            link_sources.append("parent_feature")
        elif is_epic_issue(parent_tipo):
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
    if epic_link_name and "epic_name_text" not in link_sources:
        link_sources.append("epic_name_text")

    return {
        "HierarchyLinkSource": "|".join(link_sources),
        "FeatureLinkID": feature_link_id,
        "FeatureLinkTipo": feature_link_tipo,
        "EpicLinkID": epic_link_id,
        "EpicLinkTipo": epic_link_tipo,
        "EpicLinkName": epic_link_name,
    }


def parse_jira_datetime(value: Any) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def extract_display_name(user_obj: Any) -> str:
    if isinstance(user_obj, dict):
        for key in ("displayName", "emailAddress", "name", "accountId"):
            val = str(user_obj.get(key) or "").strip()
            if val:
                return val
    return str(user_obj or "").strip()


def extract_account_id(user_obj: Any) -> str:
    if isinstance(user_obj, dict):
        return str(user_obj.get("accountId") or "").strip()
    return ""


def adf_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [adf_to_text(item) for item in value]
        return "\n".join([part for part in parts if part.strip()]).strip()
    if not isinstance(value, dict):
        return str(value).strip()

    node_type = str(value.get("type") or "").strip()
    if node_type == "text":
        return str(value.get("text") or "")
    if node_type in {"mention", "emoji"}:
        attrs = value.get("attrs") or {}
        return str(attrs.get("text") or attrs.get("shortName") or attrs.get("id") or "").strip()
    if node_type == "hardBreak":
        return "\n"

    content = value.get("content")
    if isinstance(content, list):
        parts = [adf_to_text(item) for item in content]
        if node_type in {"paragraph", "heading", "blockquote", "listItem"}:
            return " ".join([part for part in parts if part.strip()]).strip()
        return "\n".join([part for part in parts if part.strip()]).strip()

    return str(value.get("text") or "").strip()


def extract_worklog_comment_text(worklog: Dict[str, Any]) -> str:
    return adf_to_text(worklog.get("comment")).strip()


def build_issue_context(
    *,
    issue: Dict[str, Any],
    base_url: str,
    field_map: Dict[str, Any],
) -> Dict[str, str]:
    fields = issue.get("fields", {}) or {}
    parent = fields.get("parent") or {}
    parent_fields = parent.get("fields") or {}
    issue_key = str(issue.get("key") or "").strip()
    issue_summary = str(fields.get("summary") or "").strip()
    issue_type = str((fields.get("issuetype") or {}).get("name") or "").strip()
    issue_project = str((fields.get("project") or {}).get("key") or "").strip()
    parent_id = str(parent.get("key") or "").strip()
    parent_tipo = str((parent_fields.get("issuetype") or {}).get("name") or "").strip()
    parent_title = str(parent_fields.get("summary") or "").strip()
    hierarchy = resolve_hierarchy_links(
        fields=fields,
        field_map=field_map,
        parent_id=parent_id,
        parent_tipo=parent_tipo,
        parent_summary=parent_title,
    )

    epic_id = hierarchy.get("EpicLinkID", "")
    epic_title = hierarchy.get("EpicLinkName", "")
    feature_id = hierarchy.get("FeatureLinkID", "")
    feature_title = ""

    if is_epic_issue(issue_type):
        epic_id = issue_key
        epic_title = issue_summary
    elif is_feature_issue(issue_type):
        feature_id = issue_key
        feature_title = issue_summary
        if not epic_id and issue_key_or_blank(parent_id) and is_epic_issue(parent_tipo):
            epic_id = parent_id
            epic_title = parent_title

    return {
        "Issue Key": issue_key,
        "Issue Link": f"{base_url}/browse/{issue_key}" if issue_key else "",
        "Issue Summary": issue_summary,
        "Issue Type": issue_type,
        "Projeto Jira": issue_project,
        "Status Atual": str((fields.get("status") or {}).get("name") or "").strip(),
        "Parent ID": parent_id,
        "Parent Title": parent_title,
        "Parent Tipo": parent_tipo,
        "Epic ID": epic_id,
        "Epic Title": epic_title,
        "Feature ID": feature_id,
        "Feature Title": feature_title,
        "Hierarchy Source": hierarchy.get("HierarchyLinkSource", ""),
        "Labels": ", ".join([str(item) for item in (fields.get("labels") or []) if str(item).strip()]),
        "Components": ", ".join(
            [str((item or {}).get("name") or "") for item in (fields.get("components") or []) if str((item or {}).get("name") or "").strip()]
        ),
    }


def fetch_reference_issue_lookup(
    client: JiraClient,
    keys: Sequence[str],
) -> Dict[str, Dict[str, str]]:
    valid_keys = sorted({issue_key_or_blank(key) for key in keys if issue_key_or_blank(key)})
    if not valid_keys:
        return {}

    lookup: Dict[str, Dict[str, str]] = {}
    for chunk in iter_chunks(valid_keys, 100):
        jql = "key in (" + ", ".join(quote_jql_string(key) for key in chunk) + ")"
        issues = client.search_issues(jql=jql, fields=["summary", "issuetype", "project"], page_size=100)
        for issue in issues:
            key = str(issue.get("key") or "").strip()
            fields = issue.get("fields", {}) or {}
            lookup[key] = {
                "summary": str(fields.get("summary") or "").strip(),
                "issuetype": str((fields.get("issuetype") or {}).get("name") or "").strip(),
                "project": str((fields.get("project") or {}).get("key") or "").strip(),
            }
    return lookup


def enrich_issue_context_titles(
    issue_context: Dict[str, str],
    lookup: Dict[str, Dict[str, str]],
) -> Dict[str, str]:
    enriched = dict(issue_context)

    feature_id = enriched.get("Feature ID", "")
    epic_id = enriched.get("Epic ID", "")
    parent_id = enriched.get("Parent ID", "")

    if feature_id and not enriched.get("Feature Title"):
        enriched["Feature Title"] = lookup.get(feature_id, {}).get("summary", "")
    if epic_id and not enriched.get("Epic Title"):
        enriched["Epic Title"] = lookup.get(epic_id, {}).get("summary", "")
    if parent_id and not enriched.get("Parent Title"):
        enriched["Parent Title"] = lookup.get(parent_id, {}).get("summary", "")

    issue_type = enriched.get("Issue Type", "")
    issue_key = enriched.get("Issue Key", "")
    issue_summary = enriched.get("Issue Summary", "")

    if is_feature_issue(issue_type):
        enriched["Feature ID"] = issue_key
        enriched["Feature Title"] = issue_summary
    if is_epic_issue(issue_type):
        enriched["Epic ID"] = issue_key
        enriched["Epic Title"] = issue_summary

    asset_id = ""
    asset_title = ""
    asset_type = ""

    if enriched.get("Feature ID"):
        asset_id = enriched["Feature ID"]
        asset_title = enriched.get("Feature Title") or issue_summary
        asset_type = "Feature"
    elif enriched.get("Epic ID"):
        asset_id = enriched["Epic ID"]
        asset_title = enriched.get("Epic Title") or issue_summary
        asset_type = "Epic"
    elif enriched.get("Parent ID"):
        asset_id = enriched["Parent ID"]
        asset_title = enriched.get("Parent Title") or issue_summary
        asset_type = enriched.get("Parent Tipo") or "Parent"
    else:
        asset_id = issue_key
        asset_title = issue_summary
        asset_type = issue_type or "Item"

    enriched["ID do Projeto"] = asset_id
    enriched["Descrição do Ativo"] = asset_title
    enriched["Tipo do Ativo"] = asset_type
    return enriched


def get_embedded_worklogs(issue: Dict[str, Any]) -> tuple[List[Dict[str, Any]], int]:
    fields = issue.get("fields", {}) or {}
    worklog = fields.get("worklog")
    if not isinstance(worklog, dict):
        return [], 0
    rows = worklog.get("worklogs")
    if not isinstance(rows, list):
        rows = []
    total_raw = worklog.get("total")
    try:
        total = int(total_raw) if total_raw is not None else len(rows)
    except (TypeError, ValueError):
        total = len(rows)
    return rows, max(total, len(rows))


def has_embedded_worklog_field(issue: Dict[str, Any]) -> bool:
    fields = issue.get("fields", {}) or {}
    return isinstance(fields.get("worklog"), dict)


def contains_any(text_norm: str, terms: Iterable[str]) -> bool:
    return any(term in text_norm for term in terms)


def classify_activity(
    *,
    raw_text: str,
    issue_type: str,
    issue_summary: str,
    current_status: str,
    labels: str,
    components: str,
    parent_title: str,
    feature_title: str,
    epic_title: str,
) -> tuple[str, str, str, float]:
    raw_norm = normalize_text(raw_text)
    status_norm = normalize_text(current_status)
    issue_type_norm = normalize_text(issue_type)
    ctx_norm = normalize_text(" ".join([issue_summary, labels, components, parent_title, feature_title, epic_title]))

    source = "heuristica"
    evidence = ""
    confidence = 0.55

    if raw_norm:
        source = "worklog"
        evidence = raw_norm
        confidence = 1.0
    elif ctx_norm:
        source = "issue_summary"
        evidence = ctx_norm
        confidence = 0.85
    elif status_norm:
        source = "process_mining"
        evidence = status_norm
        confidence = 0.7

    if contains_any(evidence, REVIEW_HINTS):
        return "Code Review", source, "keyword_review", confidence
    if contains_any(evidence, DEPLOY_HINTS) or contains_any(status_norm, {"ready for production", "deploy", "release"}):
        return "Deploy / Release", source, "keyword_deploy", confidence
    if contains_any(evidence, HOMOLOG_HINTS) or contains_any(status_norm, {"homolog", "homologation"}):
        return "Homologacao", source, "keyword_homolog", confidence
    if contains_any(evidence, QA_HINTS) or contains_any(status_norm, {"qa", "testing", "teste"}):
        return "Teste / QA", source, "keyword_qa", confidence
    if contains_any(evidence, DISCOVERY_HINTS) or contains_any(status_norm, {"triagem", "backlog", "discovery"}):
        return "Discovery / Refinamento", source, "keyword_discovery", confidence
    if contains_any(evidence, MANAGEMENT_HINTS):
        return "Gestao / Alinhamento Tecnico", source, "keyword_management", confidence
    if contains_any(evidence, ARCH_HINTS):
        return "Arquitetura / Tech Debt", source, "keyword_architecture", confidence
    if contains_any(evidence, DATA_HINTS):
        return "Dados / Integracao", source, "keyword_data", confidence
    if contains_any(evidence, SUPPORT_HINTS) or issue_type_norm in {"support", "suporte", "incident", "incidente"}:
        return "Suporte / Sustentacao", source, "keyword_support", confidence
    if issue_type_norm in {"bug", "defeito"}:
        return "Correcao de Defeito", source, "issue_type_bug", confidence
    if evidence:
        return "Desenvolvimento", source, "fallback_development", confidence
    return "Nao Classificada", "heuristica", "fallback_unclassified", 0.3


def build_activity_display(raw_text: str, normalized_category: str, issue_summary: str, current_status: str) -> str:
    if raw_text.strip():
        return raw_text.strip()
    if normalized_category and normalized_category != "Nao Classificada":
        return normalized_category
    fallback = issue_summary.strip() or current_status.strip()
    return fallback or "Nao Classificada"


def worklog_in_period(worklog: Dict[str, Any], start_date: date, end_date: date) -> bool:
    started = parse_jira_datetime(worklog.get("started"))
    if started is None:
        return False
    started_date = started.date()
    return start_date <= started_date <= end_date


def build_capex_rows_for_issue(
    *,
    issue_context: Dict[str, str],
    worklogs: List[Dict[str, Any]],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for worklog in worklogs:
        if not worklog_in_period(worklog, start_date, end_date):
            continue

        started_dt = parse_jira_datetime(worklog.get("started"))
        updated_dt = parse_jira_datetime(worklog.get("updated"))
        if started_dt is None:
            continue

        raw_text = extract_worklog_comment_text(worklog)
        normalized_activity, source_activity, rule_activity, activity_conf = classify_activity(
            raw_text=raw_text,
            issue_type=issue_context.get("Issue Type", ""),
            issue_summary=issue_context.get("Issue Summary", ""),
            current_status=issue_context.get("Status Atual", ""),
            labels=issue_context.get("Labels", ""),
            components=issue_context.get("Components", ""),
            parent_title=issue_context.get("Parent Title", ""),
            feature_title=issue_context.get("Feature Title", ""),
            epic_title=issue_context.get("Epic Title", ""),
        )
        final_activity = build_activity_display(
            raw_text=raw_text,
            normalized_category=normalized_activity,
            issue_summary=issue_context.get("Issue Summary", ""),
            current_status=issue_context.get("Status Atual", ""),
        )

        row = {
            "MesCompetencia": started_dt.strftime("%Y-%m"),
            "ID do Projeto": issue_context.get("ID do Projeto", ""),
            "Descrição do Ativo": issue_context.get("Descrição do Ativo", ""),
            "Tipo do Ativo": issue_context.get("Tipo do Ativo", ""),
            "Colaborador": extract_display_name(worklog.get("author")),
            "Data do Apontamento das Horas": started_dt.strftime("%Y-%m-%d"),
            "Horas": round(float((worklog.get("timeSpentSeconds") or 0) / 3600.0), 2),
            "Atividade Desenvolvida": final_activity,
            "Atividade Desenvolvida Raw": raw_text,
            "Atividade Desenvolvida Normalizada": normalized_activity,
            "Origem Horas": "worklog_real",
            "Fonte Atividade": source_activity,
            "Regra Atividade": rule_activity,
            "ConfidenceScore": round(float(activity_conf), 2),
            "Issue Key": issue_context.get("Issue Key", ""),
            "Issue Link": issue_context.get("Issue Link", ""),
            "Issue Summary": issue_context.get("Issue Summary", ""),
            "Issue Type": issue_context.get("Issue Type", ""),
            "Projeto Jira": issue_context.get("Projeto Jira", ""),
            "Status Atual": issue_context.get("Status Atual", ""),
            "Epic ID": issue_context.get("Epic ID", ""),
            "Epic Title": issue_context.get("Epic Title", ""),
            "Feature ID": issue_context.get("Feature ID", ""),
            "Feature Title": issue_context.get("Feature Title", ""),
            "Parent ID": issue_context.get("Parent ID", ""),
            "Parent Title": issue_context.get("Parent Title", ""),
            "Hierarchy Source": issue_context.get("Hierarchy Source", ""),
            "Worklog ID": str(worklog.get("id") or "").strip(),
            "Worklog Author AccountId": extract_account_id(worklog.get("author")),
            "Worklog Updated At": updated_dt.strftime("%Y-%m-%d %H:%M:%S") if updated_dt else "",
        }
        rows.append(row)
    return rows


def diagnose_worklogs(
    worklogs: List[Dict[str, Any]],
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    total = len(worklogs)
    parsed_started = 0
    matched_period = 0
    sample_started: List[str] = []

    for worklog in worklogs[:5]:
        sample_started.append(str(worklog.get("started") or ""))

    for worklog in worklogs:
        started_dt = parse_jira_datetime(worklog.get("started"))
        if started_dt is None:
            continue
        parsed_started += 1
        if start_date <= started_dt.date() <= end_date:
            matched_period += 1

    return {
        "total_worklogs": total,
        "parsed_started": parsed_started,
        "matched_period": matched_period,
        "sample_started": sample_started,
    }


def build_monthly_summary(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    issue_tracker: Dict[Tuple[str, ...], set[str]] = {}

    for row in raw_rows:
        group_key = (
            str(row.get("MesCompetencia") or ""),
            str(row.get("ID do Projeto") or ""),
            str(row.get("Descrição do Ativo") or ""),
            str(row.get("Tipo do Ativo") or ""),
            str(row.get("Colaborador") or ""),
            str(row.get("Atividade Desenvolvida Normalizada") or ""),
            str(row.get("Origem Horas") or ""),
            str(row.get("Fonte Atividade") or ""),
            str(row.get("Projeto Jira") or ""),
            str(row.get("Epic ID") or ""),
            str(row.get("Feature ID") or ""),
        )
        if group_key not in grouped:
            grouped[group_key] = {
                "MesCompetencia": group_key[0],
                "ID do Projeto": group_key[1],
                "Descrição do Ativo": group_key[2],
                "Tipo do Ativo": group_key[3],
                "Colaborador": group_key[4],
                "Atividade Desenvolvida": group_key[5],
                "Horas": 0.0,
                "Qtd Apontamentos": 0,
                "Qtd Issues": 0,
                "Origem Horas": group_key[6],
                "Fonte Atividade": group_key[7],
                "Projeto Jira": group_key[8],
                "Epic ID": group_key[9],
                "Feature ID": group_key[10],
            }
            issue_tracker[group_key] = set()

        grouped[group_key]["Horas"] += float(row.get("Horas") or 0.0)
        grouped[group_key]["Qtd Apontamentos"] += 1
        issue_key = str(row.get("Issue Key") or "").strip()
        if issue_key:
            issue_tracker[group_key].add(issue_key)

    out_rows: List[Dict[str, Any]] = []
    for group_key, data in grouped.items():
        data["Horas"] = round(float(data["Horas"]), 2)
        data["Qtd Issues"] = len(issue_tracker.get(group_key, set()))
        out_rows.append(data)

    return sorted(
        out_rows,
        key=lambda row: (
            str(row.get("MesCompetencia") or ""),
            str(row.get("ID do Projeto") or ""),
            str(row.get("Colaborador") or ""),
            str(row.get("Atividade Desenvolvida") or ""),
        ),
    )


def write_csv(path: str, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx_if_possible(path: str, raw_rows: List[Dict[str, Any]], summary_rows: List[Dict[str, Any]]) -> bool:
    if pd is None:
        return False
    raw_df = pd.DataFrame(raw_rows, columns=RAW_COLUMNS)
    summary_df = pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with pd.ExcelWriter(path) as writer:
        raw_df.to_excel(writer, sheet_name="RawWorklogs", index=False)
        summary_df.to_excel(writer, sheet_name="ResumoMensal", index=False)
    return True


def start_of_day_epoch_ms(day: date) -> int:
    dt = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_issue_contexts_by_ids(
    client: JiraClient,
    issue_ids: Sequence[str],
    *,
    base_url: str,
    field_map: Dict[str, Any],
    fields_to_fetch: List[str],
) -> Dict[str, Dict[str, str]]:
    valid_ids = sorted({str(issue_id).strip() for issue_id in issue_ids if str(issue_id).strip()})
    if not valid_ids:
        return {}

    issue_context_by_id: Dict[str, Dict[str, str]] = {}
    reference_keys: List[str] = []
    raw_contexts: List[tuple[str, Dict[str, str]]] = []

    for chunk in iter_chunks(valid_ids, 100):
        jql = "id in (" + ", ".join(chunk) + ")"
        issues = client.search_issues(jql=jql, fields=fields_to_fetch, page_size=100)
        for issue in issues:
            issue_id = str(issue.get("id") or "").strip()
            if not issue_id:
                continue
            ctx = build_issue_context(issue=issue, base_url=base_url, field_map=field_map)
            raw_contexts.append((issue_id, ctx))
            for key_name in ("Parent ID", "Epic ID", "Feature ID"):
                key_val = ctx.get(key_name, "")
                if issue_key_or_blank(key_val):
                    reference_keys.append(key_val)

    reference_lookup = fetch_reference_issue_lookup(client, reference_keys)
    for issue_id, ctx in raw_contexts:
        enriched = enrich_issue_context_titles(ctx, reference_lookup)
        issue_context_by_id[issue_id] = enriched
    return issue_context_by_id


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exporta uma base mensal de CAPEX a partir de worklogs do Jira."
    )
    parser.add_argument("--projects", nargs="+", required=True, help="Projetos Jira de origem dos apontamentos.")
    parser.add_argument("--jql-extra", default="", help="Filtro JQL adicional opcional.")
    parser.add_argument("--month", default=datetime.now().strftime("%Y-%m"), help="Mes de competencia (default: mes atual). Formato YYYY-MM.")
    parser.add_argument("--date-from", default="", help="Inicio explicito do intervalo (YYYY-MM-DD).")
    parser.add_argument("--date-to", default="", help="Fim explicito do intervalo (YYYY-MM-DD).")
    parser.add_argument("--out", default="", help="CSV detalhado de saida.")
    parser.add_argument("--summary-out", default="", help="CSV resumo mensal de saida.")
    parser.add_argument("--xlsx-out", default="", help="Workbook XLSX de saida (opcional).")
    parser.add_argument("--workers", type=int, default=8, help="Workers paralelos para buscar worklogs (default: 8).")
    parser.add_argument(
        "--env-file",
        default=str(Path(__file__).with_name("jira_env.txt")),
        help="Arquivo com variaveis KEY=VALUE (default: jira_env.txt ao lado do script).",
    )
    args = parser.parse_args()

    try:
        start_date, end_date = resolve_default_date_range(args)
    except argparse.ArgumentTypeError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    load_env_file(args.env_file, overwrite=True)
    base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
    email = os.getenv("JIRA_EMAIL", "").strip()
    token = os.getenv("JIRA_API_TOKEN", "").strip()
    if not base_url or not email or not token:
        print("Erro: defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN.", file=sys.stderr)
        return 2

    projects = [str(project).strip().upper() for project in args.projects if str(project).strip()]
    if not projects:
        print("Erro: informe ao menos um projeto em --projects.", file=sys.stderr)
        return 2

    search_projects = expand_project_keys(projects)
    raw_out_default, summary_out_default, xlsx_out_default = resolve_default_output_paths(projects, start_date, end_date)
    raw_out = args.out.strip() or raw_out_default
    summary_out = args.summary_out.strip() or summary_out_default
    xlsx_out = args.xlsx_out.strip() or xlsx_out_default

    field_map = parse_json_env("JIRA_FIELD_MAP", default={})
    fields_to_fetch = [
        "summary",
        "issuetype",
        "project",
        "parent",
        "status",
        "labels",
        "components",
        "worklog",
    ]
    for logical_name in ("principal", "epic_name"):
        jira_field = str(field_map.get(logical_name) or "").strip()
        if jira_field and jira_field not in fields_to_fetch:
            fields_to_fetch.append(jira_field)

    if search_projects != projects:
        print(f"Projetos expandidos para busca Jira: {', '.join(search_projects)}")

    jql = build_jql(search_projects, args.jql_extra, start_date, end_date, date_field='worklogDate')
    print(f"Consultando Jira com JQL: {jql}")
    print(f"Janela CAPEX: {start_date:%Y-%m-%d} ate {end_date:%Y-%m-%d}")

    client = JiraClient(base_url=base_url, email=email, api_token=token)
    issues = client.search_issues(jql=jql, fields=fields_to_fetch, page_size=100)
    search_mode_used = "worklogDate"
    if not issues:
        fallback_jql = build_jql(search_projects, args.jql_extra, start_date, end_date, date_field='updated')
        print(
            "Nenhuma issue retornada com worklogDate; tentando fallback por updated "
            "e filtrando os worklogs reais no cliente."
        )
        print(f"JQL fallback: {fallback_jql}")
        issues = client.search_issues(jql=fallback_jql, fields=fields_to_fetch, page_size=100)
        if issues:
            search_mode_used = "updated"

    print(f"Issues com worklog no periodo: {len(issues)}")
    if not issues:
        write_csv(raw_out, [], RAW_COLUMNS)
        write_csv(summary_out, [], SUMMARY_COLUMNS)
        print(f"Sem issues com worklog no periodo. CSVs vazios gerados em:\n - {raw_out}\n - {summary_out}")
        return 0

    issue_contexts = [
        build_issue_context(issue=issue, base_url=base_url, field_map=field_map)
        for issue in issues
    ]

    reference_keys: List[str] = []
    for ctx in issue_contexts:
        for key_name in ("Parent ID", "Epic ID", "Feature ID"):
            key_val = ctx.get(key_name, "")
            if issue_key_or_blank(key_val):
                reference_keys.append(key_val)

    reference_lookup = fetch_reference_issue_lookup(client, reference_keys)
    issue_lookup = {
        ctx["Issue Key"]: {
            "summary": ctx["Issue Summary"],
            "issuetype": ctx["Issue Type"],
            "project": ctx["Projeto Jira"],
        }
        for ctx in issue_contexts
    }
    reference_lookup.update(issue_lookup)

    enriched_context_by_key = {
        ctx["Issue Key"]: enrich_issue_context_titles(ctx, reference_lookup)
        for ctx in issue_contexts
    }

    workers = max(1, int(args.workers))
    worker_local = threading.local()

    def get_worker_client() -> JiraClient:
        local_client = getattr(worker_local, "client", None)
        if local_client is None:
            local_client = JiraClient(base_url=base_url, email=email, api_token=token)
            worker_local.client = local_client
        return local_client

    def process_one(issue_data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any], Optional[str]]:
        issue_key = str(issue_data.get("key") or "").strip()
        if not issue_key:
            return [], {"issue_key": "", "total_worklogs": 0, "parsed_started": 0, "matched_period": 0, "sample_started": []}, None
        try:
            local_client = get_worker_client()
            initial_worklogs, total_worklogs = get_embedded_worklogs(issue_data)
            embedded_field_present = has_embedded_worklog_field(issue_data)
            force_endpoint_fetch = (
                search_mode_used == "updated"
                or not embedded_field_present
            )

            if force_endpoint_fetch:
                worklogs = local_client.get_issue_worklogs(issue_key)
            elif total_worklogs == 0:
                worklogs = []
            elif initial_worklogs and len(initial_worklogs) >= total_worklogs:
                worklogs = initial_worklogs
            else:
                worklogs = local_client.get_issue_worklogs(
                    issue_key,
                    start_at=len(initial_worklogs),
                    initial_worklogs=initial_worklogs,
                    total_hint=total_worklogs,
                )
            diag = diagnose_worklogs(worklogs, start_date=start_date, end_date=end_date)
            diag["issue_key"] = issue_key
            rows = build_capex_rows_for_issue(
                issue_context=enriched_context_by_key.get(issue_key, {}),
                worklogs=worklogs,
                start_date=start_date,
                end_date=end_date,
            )
            return rows, diag, None
        except Exception as exc:  # pragma: no cover - falha externa/HTTP
            return [], {"issue_key": issue_key, "total_worklogs": 0, "parsed_started": 0, "matched_period": 0, "sample_started": []}, f"{issue_key}: {exc}"

    all_rows: List[Dict[str, Any]] = []
    processing_errors: List[str] = []
    worklog_diagnostics: List[Dict[str, Any]] = []

    if workers == 1 or len(issues) <= 1:
        for idx, issue in enumerate(issues, start=1):
            rows, diag, err = process_one(issue)
            all_rows.extend(rows)
            worklog_diagnostics.append(diag)
            if err:
                processing_errors.append(err)
            if idx % 100 == 0:
                print(f"Processadas {idx}/{len(issues)} issues...")
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(process_one, issue) for issue in issues]
            done = 0
            for future in as_completed(futures):
                rows, diag, err = future.result()
                all_rows.extend(rows)
                worklog_diagnostics.append(diag)
                if err:
                    processing_errors.append(err)
                done += 1
                if done % 100 == 0:
                    print(f"Processadas {done}/{len(issues)} issues...")

    all_rows = sorted(
        all_rows,
        key=lambda row: (
            str(row.get("MesCompetencia") or ""),
            str(row.get("ID do Projeto") or ""),
            str(row.get("Colaborador") or ""),
            str(row.get("Data do Apontamento das Horas") or ""),
            str(row.get("Issue Key") or ""),
        ),
    )

    global_worklog_diag: Dict[str, Any] = {}
    if issues and not all_rows:
        print(
            "Nenhum apontamento foi materializado pela rota por issue; "
            "tentando fallback global via /worklog/updated + /worklog/list."
        )
        since_ms = max(0, start_of_day_epoch_ms(start_date) - 1)
        updated_refs = client.get_updated_worklog_ids(since_ms)
        global_worklog_ids = [item.get("worklogId") for item in updated_refs if item.get("worklogId") is not None]
        global_worklogs = client.get_worklogs_by_ids(global_worklog_ids)
        global_worklog_diag = diagnose_worklogs(global_worklogs, start_date=start_date, end_date=end_date)

        matching_worklogs = []
        issue_ids_from_worklogs: List[str] = []
        for worklog in global_worklogs:
            if not worklog_in_period(worklog, start_date, end_date):
                continue
            issue_id = str(worklog.get("issueId") or "").strip()
            if not issue_id:
                continue
            matching_worklogs.append(worklog)
            issue_ids_from_worklogs.append(issue_id)

        issue_context_by_id = fetch_issue_contexts_by_ids(
            client,
            issue_ids_from_worklogs,
            base_url=base_url,
            field_map=field_map,
            fields_to_fetch=fields_to_fetch,
        )
        rebuilt_rows: List[Dict[str, Any]] = []
        for worklog in matching_worklogs:
            issue_id = str(worklog.get("issueId") or "").strip()
            issue_context = issue_context_by_id.get(issue_id)
            if not issue_context:
                continue
            rebuilt_rows.extend(
                build_capex_rows_for_issue(
                    issue_context=issue_context,
                    worklogs=[worklog],
                    start_date=start_date,
                    end_date=end_date,
                )
            )
        all_rows = sorted(
            rebuilt_rows,
            key=lambda row: (
                str(row.get("MesCompetencia") or ""),
                str(row.get("ID do Projeto") or ""),
                str(row.get("Colaborador") or ""),
                str(row.get("Data do Apontamento das Horas") or ""),
                str(row.get("Issue Key") or ""),
            ),
        )

    summary_rows = build_monthly_summary(all_rows)

    write_csv(raw_out, all_rows, RAW_COLUMNS)
    write_csv(summary_out, summary_rows, SUMMARY_COLUMNS)
    print(f"CSV detalhado gerado: {raw_out}")
    print(f"CSV resumo mensal gerado: {summary_out}")

    workbook_written = write_xlsx_if_possible(xlsx_out, all_rows, summary_rows)
    if workbook_written:
        print(f"Workbook XLSX gerado: {xlsx_out}")
    else:
        print("Workbook XLSX nao gerado: pandas indisponivel no ambiente.")

    total_hours = round(sum(float(row.get("Horas") or 0.0) for row in all_rows), 2)
    unique_assets = len({str(row.get("ID do Projeto") or "") for row in all_rows if str(row.get("ID do Projeto") or "").strip()})
    unique_people = len({str(row.get("Colaborador") or "") for row in all_rows if str(row.get("Colaborador") or "").strip()})
    print(
        f"Resumo CAPEX: {len(all_rows)} apontamento(s), {total_hours:.2f} hora(s), "
        f"{unique_assets} ativo(s), {unique_people} colaborador(es)."
    )
    print(f"Modo de busca efetivo: {search_mode_used}")
    if issues and not all_rows:
        issues_with_any_worklogs = sum(1 for item in worklog_diagnostics if int(item.get("total_worklogs") or 0) > 0)
        issues_with_parsed_worklogs = sum(1 for item in worklog_diagnostics if int(item.get("parsed_started") or 0) > 0)
        issues_with_period_match = sum(1 for item in worklog_diagnostics if int(item.get("matched_period") or 0) > 0)
        sample_issue = next(
            (
                item for item in worklog_diagnostics
                if item.get("sample_started")
            ),
            None,
        )
        print(
            "Aviso: houve issues candidatas no periodo, mas nenhum worklog passou pelo filtro final. "
            "Verifique permissao de leitura de worklogs ou formato do tenant se esse resultado parecer incorreto."
        )
        print(
            "Diagnostico worklogs: "
            f"{issues_with_any_worklogs} issue(s) com worklogs retornados, "
            f"{issues_with_parsed_worklogs} com data parseada, "
            f"{issues_with_period_match} com worklog(s) dentro do periodo."
        )
        if sample_issue:
            print(
                "Amostra de started bruto: "
                f"{sample_issue.get('issue_key')}: {sample_issue.get('sample_started')}"
            )
        if global_worklog_diag:
            print(
                "Diagnostico fallback global: "
                f"{global_worklog_diag.get('total_worklogs', 0)} worklog(s) retornado(s), "
                f"{global_worklog_diag.get('parsed_started', 0)} com data parseada, "
                f"{global_worklog_diag.get('matched_period', 0)} dentro do periodo."
            )
            if global_worklog_diag.get("sample_started"):
                print(
                    "Amostra global de started bruto: "
                    f"{global_worklog_diag.get('sample_started')}"
                )

    if processing_errors:
        print(f"Aviso: {len(processing_errors)} issue(s) com falha ao buscar worklogs.")
        for msg in processing_errors[:10]:
            print(f" - {msg}")
        if len(processing_errors) > 10:
            print(" - ...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
