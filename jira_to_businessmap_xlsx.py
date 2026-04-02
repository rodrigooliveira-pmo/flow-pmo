#!/usr/bin/env python3
"""
MÓDULO DE MIGRAÇÃO DE DADOS: Jira Cloud → BusinessMap

Propósito
---------
Ferramenta de migração one-time (ou periódica) para exportar issues do Jira Cloud
para planilha XLSX no formato de importação nativo do BusinessMap (Kanbanize).

Este módulo NÃO faz parte do pipeline de métricas/dashboards do Flow-PMO.
É um utilitário standalone de migração/integração entre ferramentas.

Fluxo de uso típico
-------------------
1. Executar este script apontando para o(s) projeto(s) Jira desejados.
2. Gerar o arquivo businessmap-import-<projeto>-<data>.xlsx.
3. Importar o XLSX diretamente no BusinessMap via: Settings → Import Cards.

Por que existe separado
-----------------------
- O BusinessMap usa uma estrutura de colunas própria (Board/Workflow/Lane/Column)
  incompatível com o modelo de dados do pipeline Flow-PMO (stages de fluxo).
- Os mapeamentos de status Jira → coluna BusinessMap (ex: BF_BUSINESSMAP_STATUS_TO_COLUMN_MAP)
  são específicos para cada quadro do BusinessMap e não se aplicam ao restante do sistema.
- Não deve ser integrado ao pipeline de métricas para evitar acoplamento desnecessário.

Uso (PowerShell):
  $env:JIRA_BASE_URL='https://suaempresa.atlassian.net'
  $env:JIRA_EMAIL='seu.email@empresa.com'
  $env:JIRA_API_TOKEN='***'
  python jira_to_businessmap_xlsx.py --projects W1NNR --board-name "Meu Board" --workflow-name "Workflow Padrão"

Mapeamentos opcionais via JSON (CLI ou env):
  $env:BUSINESSMAP_STATUS_TO_COLUMN_MAP='{"Backlog":"Requested","In Progress":"In Progress","Done":"Done"}'
  $env:BUSINESSMAP_STATUS_TO_LANE_MAP='{"Backlog":"Discovery","In Progress":"Execution","Done":"Delivery"}'
  $env:BUSINESSMAP_PRIORITY_MAP='{"Highest":"critical","High":"high","Medium":"average","Low":"low","Lowest":"low"}'

Observações:
  - A coluna "Title" é sempre gerada (obrigatória no BusinessMap).
  - "Custom Card ID" recebe o issue key do Jira para rastreabilidade.
  - "Column name"/"Lane name" podem ser derivados do status Jira via mapeamento.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests


BUSINESSMAP_COLUMNS = [
    "Title",
    "Description",
    "Custom Card ID",
    "Links",
    "Priority",
    "Owner",
    "Co-Owners",
    "Color",
    "Size",
    "Tags",
    "Deadline",
    "Type name",
    "Column name",
    "Lane name",
    "Board name",
    "Board ID",
    "Workflow name",
    "Created at",
    "Start Date",
    "End Date",
]

BUSINESSMAP_DATE_COLUMNS = ["Deadline", "Created at", "Start Date", "End Date"]
ISSUE_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*-\d+$")


DEFAULT_PRIORITY_MAP = {
    "highest": "critical",
    "critical": "critical",
    "blocker": "critical",
    "high": "high",
    "medium": "average",
    "average": "average",
    "normal": "average",
    "low": "low",
    "lowest": "low",
}

TSHIRT_TO_BM_SIZE = {
    "s": 1,
    "m": 2,
    "l": 3,
    "xl": 4,
    "xxl": 5,
    "xxxl": 6,
}

BF_BUSINESSMAP_STATUS_TO_COLUMN_MAP: Dict[str, str] = {
    "Triagem": "TRIAGEM",
    "Backlog": "BACKLOG",
    "To Do": "BACKLOG",
    "Sprint Backlog": "BACKLOG",
    "Ready to Start": "READY TO START",
    "Ready to start": "READY TO START",
    "READY FOR DEVELOPMENT": "READY TO START",
    "Ready for development": "READY TO START",
    "Ready for development": "READY TO START",
    "Ready For Development": "READY TO START",
    "In Progress": "IN PROGRESS",
    "In Progess": "IN PROGRESS",
    "In progress": "IN PROGRESS",
    "Em Progresso": "IN PROGRESS",
    "Desenvolvimento": "IN PROGRESS",
    "Development": "IN PROGRESS",
    "In Development": "IN PROGRESS",
    "Doing": "IN PROGRESS",
    "ready code review": "READY CODE REVIEW",
    "Ready code review": "READY CODE REVIEW",
    "Ready for code review": "READY CODE REVIEW",
    "Ready For Code Review": "READY CODE REVIEW",
    "Code review": "CODE REVIEW",
    "Code Review": "CODE REVIEW",
    "ready testing/qa": "READY TESTING/QA",
    "Ready testing/qa": "READY TESTING/QA",
    "Ready for testing/qa": "READY TESTING/QA",
    "Ready for Testing/QA": "READY TESTING/QA",
    "Ready for test/qa": "READY TESTING/QA",
    "Testing/QA": "TESTING/QA",
    "Testing / QA": "TESTING/QA",
    "Testing /Qa": "TESTING/QA",
    "QA": "TESTING/QA",
    "Testing": "TESTING/QA",
    "ready homolog": "READY STAGING",
    "Ready homolog": "READY STAGING",
    "Ready to Homologation": "READY STAGING",
    "Ready to homologation": "READY STAGING",
    "Ready To Staging": "READY STAGING",
    "Ready to staging": "READY STAGING",
    "Homolog": "STAGING",
    "Homologation": "STAGING",
    "Staging": "STAGING",
    "In Staging": "STAGING",
    "QA / Staging": "STAGING",
    "QA/Staging": "STAGING",
    "ready for production": "READY FOR PRODUCTION",
    "Ready for production": "READY FOR PRODUCTION",
    "Ready For Production": "READY FOR PRODUCTION",
    "Itens concluídos": "DONE",
    "Itens Concluídos": "DONE",
    "Done": "DONE",
    "Concluído": "DONE",
    "Concluido": "DONE",
    "Cancelled": "DONE",
    "Cancelada": "DONE",
    # Statuses de discovery/portfolio/design observados no BF
    "Discovery & Definition": "TRIAGEM",
    "Discovery and Definition": "TRIAGEM",
    "Discovery": "TRIAGEM",
    "Ideação": "TRIAGEM",
    "Ideacao": "TRIAGEM",
    "Idea": "TRIAGEM",
    "Wishlist": "BACKLOG",
    "Doing Design": "IN PROGRESS",
    "Design": "IN PROGRESS",
}

BF_BUSINESSMAP_STATUS_TO_LANE_MAP: Dict[str, str] = {}

BF_BUSINESSMAP_TYPE_NAME_MAP: Dict[str, str] = {
    "Task": "História",
    "Tarefa": "História",
    "Story": "História",
    "User Story": "História",
}


def parse_json_dict(value: str, *, label: str) -> Dict[str, Any]:
    raw = str(value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} não é JSON válido: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} precisa ser um objeto JSON")
    return parsed


def parse_json_env(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return default
    return parsed if isinstance(parsed, dict) else default


def parse_json_list_env(name: str, default: List[Any]) -> List[Any]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return default
    return parsed if isinstance(parsed, list) else default


def load_env_file(env_file: str, overwrite: bool = True) -> None:
    path = Path(env_file)
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and (overwrite or key not in os.environ):
            os.environ[key] = value


def issue_key_or_blank(value: Any) -> str:
    txt = str(value or "").strip()
    return txt if ISSUE_KEY_PATTERN.match(txt) else ""


def search_issues(
    base_url: str,
    email: str,
    token: str,
    jql: str,
    fields: List[str],
    page_size: int = 100,
) -> List[Dict[str, Any]]:
    session = requests.Session()
    session.auth = (email, token)
    session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    def enhanced_post() -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None
        seen = set()
        while True:
            payload: Dict[str, Any] = {"jql": jql, "maxResults": page_size, "fields": fields}
            if next_page_token:
                payload["nextPageToken"] = next_page_token
            resp = session.post(f"{base_url}/rest/api/3/search/jql", json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            page = data.get("issues", [])
            issues.extend(page)
            if data.get("isLast") is True:
                break
            next_page_token = data.get("nextPageToken")
            if not next_page_token or next_page_token in seen:
                break
            seen.add(next_page_token)
        return issues

    def enhanced_get() -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None
        seen = set()
        while True:
            params: Dict[str, Any] = {"jql": jql, "maxResults": page_size, "fields": ",".join(fields)}
            if next_page_token:
                params["nextPageToken"] = next_page_token
            resp = session.get(f"{base_url}/rest/api/3/search/jql", params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            page = data.get("issues", [])
            issues.extend(page)
            if data.get("isLast") is True:
                break
            next_page_token = data.get("nextPageToken")
            if not next_page_token or next_page_token in seen:
                break
            seen.add(next_page_token)
        return issues

    def legacy_search() -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        start_at = 0
        while True:
            params: Dict[str, Any] = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": page_size,
                "fields": ",".join(fields),
            }
            resp = session.get(f"{base_url}/rest/api/3/search", params=params, timeout=60)
            if resp.status_code in {400, 404, 405, 410}:
                resp = session.get(f"{base_url}/rest/api/2/search", params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            page = data.get("issues", [])
            issues.extend(page)
            total = int(data.get("total", 0))
            start_at += len(page)
            if not page or start_at >= total:
                break
        return issues

    errors: List[str] = []
    for name, fn in [("enhanced_post", enhanced_post), ("enhanced_get", enhanced_get), ("legacy", legacy_search)]:
        try:
            return fn()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "n/a"
            errors.append(f"{name}:{status}")
    raise RuntimeError(f"Falha ao consultar Jira ({', '.join(errors)}).")


def safe_get(d: Dict[str, Any], *path: str) -> Any:
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def extract_custom_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("name") or item.get("value") or item.get("displayName") or ""))
            else:
                parts.append(str(item))
        return ", ".join([p for p in parts if p])
    if isinstance(value, dict):
        return str(value.get("name") or value.get("value") or value.get("displayName") or "")
    return str(value)


def custom_field_as_text(fields: Dict[str, Any], field_id: str) -> str:
    fid = str(field_id or "").strip()
    if not fid:
        return ""
    return extract_custom_text(fields.get(fid)).strip()


def adf_to_text(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(item) for item in node)
    if not isinstance(node, dict):
        return str(node)

    node_type = str(node.get("type") or "")
    content = node.get("content") or []

    if node_type == "text":
        return str(node.get("text") or "")
    if node_type == "hardBreak":
        return "\n"
    if node_type in {"doc", "paragraph"}:
        txt = "".join(adf_to_text(item) for item in content)
        return txt + ("\n" if node_type == "paragraph" and txt else "")
    if node_type in {"bulletList", "orderedList"}:
        parts: List[str] = []
        for item in content:
            item_txt = adf_to_text(item).strip()
            if item_txt:
                parts.append(f"- {item_txt}")
        return "\n".join(parts) + ("\n" if parts else "")
    if node_type == "listItem":
        return "".join(adf_to_text(item) for item in content)
    if node_type == "mention":
        attrs = node.get("attrs") or {}
        return str(attrs.get("text") or attrs.get("id") or "")

    return "".join(adf_to_text(item) for item in content)


def normalize_multiline_text(text: str) -> str:
    lines = [line.rstrip() for line in str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    cleaned: List[str] = []
    blank_pending = False
    for line in lines:
        if line.strip():
            if blank_pending and cleaned:
                cleaned.append("")
            cleaned.append(line.strip())
            blank_pending = False
        else:
            blank_pending = True
    return "\n".join(cleaned).strip()


def parse_jira_date_to_businessmap(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return dt.date().isoformat()


def normalize_priority(priority_name: str, priority_map: Dict[str, str]) -> str:
    p = str(priority_name or "").strip()
    if not p:
        return ""
    direct = priority_map.get(p)
    if direct:
        return str(direct).strip().lower()
    low = priority_map.get(p.lower())
    if low:
        return str(low).strip().lower()
    mapped = DEFAULT_PRIORITY_MAP.get(p.lower(), "")
    return mapped


def normalize_size_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)) and not pd.isna(value):
        # BusinessMap aceita valores numéricos; preserva inteiro quando possível.
        if float(value).is_integer():
            return str(int(value))
        return str(value)
    text = extract_custom_text(value).strip()
    if not text:
        return ""
    lower = text.lower().replace(" ", "")
    if lower in TSHIRT_TO_BM_SIZE:
        return str(TSHIRT_TO_BM_SIZE[lower])
    try:
        numeric = float(text.replace(",", "."))
    except ValueError:
        return ""
    if numeric.is_integer():
        return str(int(numeric))
    return str(numeric)


def extract_user_value(user_obj: Any, owner_format: str) -> str:
    if not isinstance(user_obj, dict):
        return ""
    owner_format = str(owner_format or "display_name").strip().lower()
    if owner_format == "display_name":
        return str(user_obj.get("displayName") or "")
    if owner_format == "email":
        return str(user_obj.get("emailAddress") or "")
    if owner_format == "email_local":
        email = str(user_obj.get("emailAddress") or "")
        return email.split("@", 1)[0] if "@" in email else email
    if owner_format == "account_id":
        return str(user_obj.get("accountId") or "")
    if owner_format == "name":
        return str(user_obj.get("name") or "")
    return str(user_obj.get("displayName") or "")


def map_status_value(status_name: str, mapping: Dict[str, Any], default_value: str = "") -> str:
    s = str(status_name or "").strip()
    if not s:
        return default_value
    if s in mapping:
        return str(mapping[s] or "")
    lower_mapping = {str(k).strip().lower(): v for k, v in mapping.items()}
    if s.lower() in lower_mapping:
        return str(lower_mapping[s.lower()] or "")
    return default_value


def resolve_lane_from_title_prefix(
    title: str,
    lane_title_prefix_map: List[Dict[str, Any]],
    fallback_lane_name: str,
) -> str:
    txt = str(title or "").strip().lower()
    for rule in lane_title_prefix_map:
        if not isinstance(rule, dict):
            continue
        prefix = str(rule.get("prefix") or "").strip().lower()
        lane = str(rule.get("lane") or "").strip()
        if prefix and lane and txt.startswith(prefix):
            return lane
    return str(fallback_lane_name or "")


def build_tags(
    fields: Dict[str, Any],
    tag_sources: List[str],
    *,
    mapped_type_name: str,
    workflow_name: str,
    column_name: str,
) -> str:
    tags: List[str] = []
    seen = set()

    def add_many(values: Iterable[str]) -> None:
        for raw in values:
            tag = str(raw or "").strip()
            if not tag:
                continue
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            tags.append(tag)

    for source in tag_sources:
        src = source.strip().lower()
        if src == "labels":
            add_many([str(x) for x in (fields.get("labels") or [])])
        elif src == "components":
            add_many([str((c or {}).get("name") or "") for c in (fields.get("components") or [])])
        elif src == "fixversions":
            add_many([str((v or {}).get("name") or "") for v in (fields.get("fixVersions") or [])])
        elif src == "project":
            add_many([str(safe_get(fields, "project", "key") or "")])
        elif src == "issuetype":
            add_many([str(safe_get(fields, "issuetype", "name") or "")])
        elif src == "priority":
            add_many([str(safe_get(fields, "priority", "name") or "")])
        elif src == "type_name":
            add_many([mapped_type_name])
        elif src == "workflow_name":
            add_many([workflow_name])
        elif src == "column_name":
            add_many([column_name])

    return ", ".join(tags)


def resolve_parent_link_id(fields: Dict[str, Any], field_map: Dict[str, Any]) -> str:
    parent_id = issue_key_or_blank(safe_get(fields, "parent", "key"))
    if parent_id:
        return parent_id

    principal_key = issue_key_or_blank(custom_field_as_text(fields, str(field_map.get("principal") or "")))
    if principal_key:
        return principal_key

    epic_name_raw = custom_field_as_text(fields, str(field_map.get("epic_name") or ""))
    epic_name_key = issue_key_or_blank(epic_name_raw)
    if epic_name_key:
        return epic_name_key

    return ""


def build_businessmap_links(parent_custom_id: str) -> str:
    parent_id = issue_key_or_blank(parent_custom_id)
    if not parent_id:
        return ""
    return f"Parent: {parent_id};"


def default_out_path(projects: List[str]) -> str:
    configured_out_dir = str(os.getenv("BUSINESSMAP_OUT_DIR", "")).strip()
    if configured_out_dir:
        data_folder = configured_out_dir
    elif os.name == "nt":
        data_folder = r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados"
    else:
        data_folder = os.path.join(os.path.expanduser("~"), "Library", "CloudStorage", "OneDrive-W1", "Documentos", "Dados")
    date_tag = datetime.now().strftime("%Y%m%d")
    project_tag = "-".join([p.strip().lower() for p in projects if p.strip()]) or "jira"
    return os.path.join(data_folder, f"businessmap-import-{project_tag}-{date_tag}.xlsx")


def add_batch_suffix(out_path: str, batch_index_1based: int) -> str:
    p = Path(out_path)
    return str(p.with_name(f"{p.stem}-lote-{batch_index_1based}{p.suffix or '.xlsx'}"))


def write_output_xlsx(df: pd.DataFrame, out_path: str, split_size: int) -> List[str]:
    def prepare_dataframe_for_excel(input_df: pd.DataFrame) -> pd.DataFrame:
        prepared = input_df.copy()
        for col in BUSINESSMAP_DATE_COLUMNS:
            if col not in prepared.columns:
                continue
            values = prepared[col].astype(str).str.strip()
            prepared[col] = pd.to_datetime(values.where(values.ne(""), None), errors="coerce")
        return prepared

    def write_single_xlsx(input_df: pd.DataFrame, path: str) -> None:
        export_df = prepare_dataframe_for_excel(input_df)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Sheet1")
            ws = writer.book["Sheet1"]
            header_index = {cell.value: idx for idx, cell in enumerate(ws[1], start=1)}
            for col in BUSINESSMAP_DATE_COLUMNS:
                col_idx = header_index.get(col)
                if not col_idx:
                    continue
                for row in range(2, ws.max_row + 1):
                    cell = ws.cell(row=row, column=col_idx)
                    if cell.value is not None:
                        cell.number_format = "yyyy-mm-dd"

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if split_size <= 0 or len(df) <= split_size:
        write_single_xlsx(df, out_path)
        return [out_path]

    written_paths: List[str] = []
    for i, start in enumerate(range(0, len(df), split_size), start=1):
        batch_df = df.iloc[start : start + split_size].copy()
        batch_path = add_batch_suffix(out_path, i)
        write_single_xlsx(batch_df, batch_path)
        written_paths.append(batch_path)
    return written_paths


def resolve_builtin_mapping_preset(name: str) -> tuple[Dict[str, str], Dict[str, str]]:
    preset = str(name or "").strip().lower()
    if preset in {"", "none"}:
        return {}, {}
    if preset in {"bf", "bf_businessmap", "businessmap_bf"}:
        return dict(BF_BUSINESSMAP_STATUS_TO_COLUMN_MAP), dict(BF_BUSINESSMAP_STATUS_TO_LANE_MAP)
    raise ValueError(f"Preset de mapeamento desconhecido: {name}")


def resolve_builtin_type_preset(name: str) -> Dict[str, str]:
    preset = str(name or "").strip().lower()
    if preset in {"", "none"}:
        return {}
    if preset in {"bf", "bf_businessmap", "businessmap_bf"}:
        return dict(BF_BUSINESSMAP_TYPE_NAME_MAP)
    raise ValueError(f"Preset de tipo desconhecido: {name}")


def map_issue_type_name(issue_type_name: str, type_name_map: Dict[str, Any]) -> str:
    raw = str(issue_type_name or "").strip()
    if not raw:
        return ""
    if raw in type_name_map:
        return str(type_name_map[raw] or "")
    lowered = {str(k).strip().lower(): v for k, v in type_name_map.items()}
    if raw.lower() in lowered:
        return str(lowered[raw.lower()] or "")
    return raw


def build_output_row(
    base_url: str,
    issue: Dict[str, Any],
    *,
    field_map: Dict[str, Any],
    board_name: str,
    board_id: str,
    workflow_name: str,
    default_column_name: str,
    default_lane_name: str,
    status_to_column_map: Dict[str, Any],
    status_to_lane_map: Dict[str, Any],
    priority_map: Dict[str, Any],
    owner_source: str,
    owner_format: str,
    tag_sources: List[str],
    type_name_map: Dict[str, Any],
    lane_title_prefix_map: List[Dict[str, Any]],
    lane_title_prefix_fallback: str,
    size_field: str,
    start_date_field: str,
    end_date_field: str,
    omit_historical_dates: bool,
) -> Dict[str, str]:
    fields = issue.get("fields", {}) or {}
    key = str(issue.get("key") or "")
    status_name = str(safe_get(fields, "status", "name") or "")
    column_name = map_status_value(status_name, status_to_column_map, default_value="")
    if not column_name:
        column_name = default_column_name or status_name
    owner_user: Any = None
    owner_source_norm = str(owner_source or "assignee").strip().lower()
    if owner_source_norm == "assignee":
        owner_user = fields.get("assignee")
    elif owner_source_norm == "reporter":
        owner_user = fields.get("reporter")
    elif owner_source_norm == "creator":
        owner_user = fields.get("creator")
    elif owner_source_norm == "none":
        owner_user = None

    description_text = normalize_multiline_text(adf_to_text(fields.get("description")))
    summary = str(fields.get("summary") or "")
    if not summary:
        summary = key or "(sem título)"

    lane_name = map_status_value(status_name, status_to_lane_map, default_value="")
    if not lane_name and lane_title_prefix_map:
        lane_name = resolve_lane_from_title_prefix(
            summary,
            lane_title_prefix_map=lane_title_prefix_map,
            fallback_lane_name=lane_title_prefix_fallback,
        )
    if not lane_name:
        lane_name = default_lane_name

    start_date_value = ""
    end_date_value = ""
    if start_date_field:
        start_date_value = parse_jira_date_to_businessmap(fields.get(start_date_field))
    if end_date_field:
        end_date_value = parse_jira_date_to_businessmap(fields.get(end_date_field))

    if not end_date_value:
        end_date_value = parse_jira_date_to_businessmap(fields.get("resolutiondate"))
    if not start_date_value:
        # Fallback conservador: statuscategorychangedate pode representar entrada no status atual.
        # Para status DONE, essa data costuma ser a conclusão; nesse caso usar como Start Date gera contradição.
        status_low = status_name.lower()
        if any(token in status_low for token in ("progress", "desenvol", "doing", "review", "testing", "qa")):
            start_date_value = parse_jira_date_to_businessmap(fields.get("statuscategorychangedate"))
    if not end_date_value:
        status_low = status_name.lower()
        if any(token in status_low for token in ("done", "conclu", "cancel")):
            end_date_value = parse_jira_date_to_businessmap(fields.get("statuscategorychangedate"))
    if not start_date_value and end_date_value:
        status_low = status_name.lower()
        if any(token in status_low for token in ("done", "conclu", "cancel")):
            # Para histórico do BusinessMap, itens concluídos com End Date tendem a exigir Start Date.
            # Fallback seguro: usar a data de criação quando não houver início melhor disponível.
            start_date_value = parse_jira_date_to_businessmap(fields.get("created"))

    created_at_value = parse_jira_date_to_businessmap(fields.get("created"))
    if omit_historical_dates:
        created_at_value = ""
        start_date_value = ""
        end_date_value = ""

    size_value = ""
    if size_field:
        size_value = normalize_size_value(fields.get(size_field))

    mapped_type_name = map_issue_type_name(str(safe_get(fields, "issuetype", "name") or ""), type_name_map)
    parent_link_id = resolve_parent_link_id(fields, field_map)

    row = {
        "Title": summary,
        "Description": description_text,
        "Custom Card ID": key,
        "Links": build_businessmap_links(parent_link_id),
        "Priority": normalize_priority(str(safe_get(fields, "priority", "name") or ""), priority_map),
        "Owner": extract_user_value(owner_user, owner_format=owner_format),
        "Co-Owners": "",
        "Color": "",
        "Size": size_value,
        "Tags": build_tags(
            fields,
            tag_sources,
            mapped_type_name=mapped_type_name,
            workflow_name=workflow_name,
            column_name=column_name,
        ),
        "Deadline": parse_jira_date_to_businessmap(fields.get("duedate")),
        "Type name": mapped_type_name,
        "Column name": column_name,
        "Lane name": lane_name,
        "Board name": board_name,
        "Board ID": str(board_id or ""),
        "Workflow name": workflow_name,
        "Created at": created_at_value,
        "Start Date": start_date_value,
        "End Date": end_date_value,
    }

    # Garantia de headers válidos/ordem estável.
    return {col: str(row.get(col) or "") for col in BUSINESSMAP_COLUMNS}


def choose_size_field(field_map: Dict[str, Any], size_source: str) -> str:
    source = str(size_source or "none").strip().lower()
    if source == "none":
        return ""
    if source == "story_points":
        for key in ("story_points", "storypoint", "story_point_estimate"):
            fid = str(field_map.get(key) or "").strip()
            if fid:
                return fid
        return ""
    if source == "tshirt":
        for key in ("effort_tshirt_size", "tshirt_size", "effort_tshirt"):
            fid = str(field_map.get(key) or "").strip()
            if fid:
                return fid
        return ""
    return ""


def main() -> int:
    env_parser = argparse.ArgumentParser(add_help=False)
    env_parser.add_argument(
        "--env-file",
        default=str(Path(__file__).with_name("jira_env.txt")),
        help=argparse.SUPPRESS,
    )
    env_args, _ = env_parser.parse_known_args()
    load_env_file(env_args.env_file, overwrite=True)

    parser = argparse.ArgumentParser(description="Exporta Jira para XLSX compatível com import do BusinessMap.")
    parser.add_argument(
        "--projects",
        nargs="+",
        default=[],
        help="Projetos Jira para exportar (ex.: W1NNR DT). Opcional quando --jql completo for informado.",
    )
    parser.add_argument("--out", default="", help="Caminho do XLSX de saída")
    parser.add_argument("--jql", default="", help="JQL completa; quando informada, tem precedência sobre --projects/--jql-extra")
    parser.add_argument("--jql-extra", default="", help="Filtro JQL adicional opcional")
    parser.add_argument(
        "--split-size",
        type=int,
        default=int(os.getenv("BUSINESSMAP_SPLIT_SIZE", "0") or "0"),
        help="Se > 0, divide a saída em múltiplos XLSX com no máximo N cartões por arquivo (ex.: 100)",
    )
    parser.add_argument(
        "--mapping-preset",
        choices=["auto", "none", "bf"],
        default=os.getenv("BUSINESSMAP_MAPPING_PRESET", "auto"),
        help="Preset embutido de mapeamento status->coluna/lane (default: auto; aplica 'bf' quando projeto = BF e não há JSON/env)",
    )
    parser.add_argument("--board-name", default=os.getenv("BUSINESSMAP_BOARD_NAME", "").strip(), help="Preenche coluna 'Board name'")
    parser.add_argument("--board-id", default=os.getenv("BUSINESSMAP_BOARD_ID", "").strip(), help="Preenche coluna 'Board ID'")
    parser.add_argument(
        "--workflow-name",
        default=os.getenv("BUSINESSMAP_WORKFLOW_NAME", "").strip(),
        help="Preenche coluna 'Workflow name'",
    )
    parser.add_argument(
        "--default-column-name",
        default=os.getenv("BUSINESSMAP_DEFAULT_COLUMN_NAME", "").strip(),
        help="Valor padrão para 'Column name' quando não houver mapeamento por status (fallback final = status Jira)",
    )
    parser.add_argument(
        "--default-lane-name",
        default=os.getenv("BUSINESSMAP_DEFAULT_LANE_NAME", "").strip(),
        help="Valor padrão para 'Lane name' quando não houver mapeamento por status",
    )
    parser.add_argument(
        "--status-to-column-map",
        default="",
        help="JSON com mapeamento de status Jira para 'Column name' (sobrescreve env BUSINESSMAP_STATUS_TO_COLUMN_MAP)",
    )
    parser.add_argument(
        "--status-to-lane-map",
        default="",
        help="JSON com mapeamento de status Jira para 'Lane name' (sobrescreve env BUSINESSMAP_STATUS_TO_LANE_MAP)",
    )
    parser.add_argument(
        "--lane-by-title-prefix-map",
        default="",
        help=(
            "JSON list para mapear `Lane name` por prefixo do título "
            "(ex.: [{\"prefix\":\"S1NC -\",\"lane\":\"S1NC\"}])"
        ),
    )
    parser.add_argument(
        "--lane-by-title-prefix-fallback",
        default=os.getenv("BUSINESSMAP_LANE_BY_TITLE_PREFIX_FALLBACK", "").strip(),
        help="Raia fallback usada com --lane-by-title-prefix-map quando nenhum prefixo combinar",
    )
    parser.add_argument(
        "--priority-map",
        default="",
        help="JSON com mapeamento de prioridade Jira -> BusinessMap (low/average/high/critical)",
    )
    parser.add_argument(
        "--type-name-map",
        default="",
        help="JSON com mapeamento de tipo Jira -> 'Type name' no BusinessMap (ex.: {\"Task\":\"História\"})",
    )
    parser.add_argument(
        "--owner-source",
        choices=["assignee", "reporter", "creator", "none"],
        default=os.getenv("BUSINESSMAP_OWNER_SOURCE", "assignee"),
        help="Origem do Owner no Jira (default: assignee)",
    )
    parser.add_argument(
        "--owner-format",
        choices=["display_name", "email", "email_local", "account_id", "name"],
        default=os.getenv("BUSINESSMAP_OWNER_FORMAT", "display_name"),
        help="Formato do valor de Owner (default: display_name)",
    )
    parser.add_argument(
        "--tag-sources",
        default=os.getenv("BUSINESSMAP_TAG_SOURCES", "labels,components,project,issuetype"),
        help=(
            "Fontes para compor 'Tags' (csv: labels,components,fixversions,project,issuetype,priority,"
            "type_name,workflow_name,column_name)"
        ),
    )
    parser.add_argument(
        "--size-source",
        choices=["none", "story_points", "tshirt"],
        default=os.getenv("BUSINESSMAP_SIZE_SOURCE", "none"),
        help="Origem para coluna 'Size' (default: none)",
    )
    parser.add_argument(
        "--start-date-field",
        default=os.getenv("BUSINESSMAP_START_DATE_FIELD", "").strip(),
        help="Custom field Jira para usar em 'Start Date' (ex.: customfield_12345)",
    )
    parser.add_argument(
        "--end-date-field",
        default=os.getenv("BUSINESSMAP_END_DATE_FIELD", "").strip(),
        help="Custom field Jira para usar em 'End Date' (ex.: customfield_67890)",
    )
    parser.add_argument(
        "--omit-historical-dates",
        action="store_true",
        help="Não preenche Created at / Start Date / End Date; útil para atualizar cards existentes no BusinessMap",
    )
    parser.add_argument(
        "--env-file",
        default=env_args.env_file,
        help="Arquivo com variáveis no formato KEY=VALUE (default: jira_env.txt ao lado do script)",
    )
    args = parser.parse_args()
    base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
    email = os.getenv("JIRA_EMAIL", "").strip()
    token = os.getenv("JIRA_API_TOKEN", "").strip()

    if not base_url or not email or not token:
        print("Erro: defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN.", file=sys.stderr)
        return 2

    raw_jql = str(args.jql or "").strip()
    projects = [p.strip().upper() for p in args.projects if p and p.strip()]
    if not projects and not raw_jql:
        print("Erro: informe ao menos um projeto em --projects ou uma consulta completa em --jql.", file=sys.stderr)
        return 2

    if args.board_name and args.board_id:
        print("Info: preenchendo 'Board name' e 'Board ID'. Se ambos existirem, o import do BusinessMap pode usar qualquer um válido.")

    try:
        preset_column_map: Dict[str, Any] = {}
        preset_lane_map: Dict[str, Any] = {}
        preset_type_map: Dict[str, Any] = {}
        env_column_map = parse_json_env("BUSINESSMAP_STATUS_TO_COLUMN_MAP", default={})
        env_lane_map = parse_json_env("BUSINESSMAP_STATUS_TO_LANE_MAP", default={})
        env_type_map = parse_json_env("BUSINESSMAP_TYPE_NAME_MAP", default={})
        env_lane_title_prefix_map = parse_json_list_env("BUSINESSMAP_LANE_BY_TITLE_PREFIX_MAP", default=[])
        explicit_cli_column = bool(args.status_to_column_map.strip())
        explicit_cli_lane = bool(args.status_to_lane_map.strip())
        explicit_cli_type = bool(args.type_name_map.strip())

        should_apply_bf_preset = False
        if args.mapping_preset == "bf":
            should_apply_bf_preset = True
        elif args.mapping_preset == "auto":
            normalized_projects = {p.strip().upper() for p in projects}
            no_external_maps = not (explicit_cli_column or explicit_cli_lane or env_column_map or env_lane_map)
            should_apply_bf_preset = normalized_projects == {"BF"} and no_external_maps

        if should_apply_bf_preset:
            preset_column_map, preset_lane_map = resolve_builtin_mapping_preset("bf")
            preset_type_map = resolve_builtin_type_preset("bf")
            print("Preset de mapeamento aplicado: BF (BusinessMap columns/lanes).")

        status_to_column_map = (
            parse_json_dict(args.status_to_column_map, label="--status-to-column-map")
            if args.status_to_column_map.strip()
            else (env_column_map or preset_column_map)
        )
        status_to_lane_map = (
            parse_json_dict(args.status_to_lane_map, label="--status-to-lane-map")
            if args.status_to_lane_map.strip()
            else (env_lane_map or preset_lane_map)
        )
        if args.lane_by_title_prefix_map.strip():
            try:
                lane_title_prefix_map = json.loads(args.lane_by_title_prefix_map)
            except json.JSONDecodeError as exc:
                raise ValueError(f"--lane-by-title-prefix-map não é JSON válido: {exc}") from exc
        else:
            lane_title_prefix_map = env_lane_title_prefix_map
        if not isinstance(lane_title_prefix_map, list):
            raise ValueError("--lane-by-title-prefix-map precisa ser uma lista JSON")
        priority_map = DEFAULT_PRIORITY_MAP | (
            parse_json_dict(args.priority_map, label="--priority-map")
            if args.priority_map.strip()
            else parse_json_env("BUSINESSMAP_PRIORITY_MAP", default={})
        )
        type_name_map = (
            parse_json_dict(args.type_name_map, label="--type-name-map")
            if args.type_name_map.strip()
            else (env_type_map or preset_type_map)
        )
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    field_map = parse_json_env("JIRA_FIELD_MAP", default={})
    size_field = choose_size_field(field_map, args.size_source)

    requested_fields = [
        "summary",
        "description",
        "parent",
        "status",
        "priority",
        "assignee",
        "reporter",
        "creator",
        "labels",
        "components",
        "fixVersions",
        "duedate",
        "issuetype",
        "project",
        "created",
        "resolutiondate",
        "statuscategorychangedate",
    ]
    for custom_field in [
        size_field,
        args.start_date_field.strip(),
        args.end_date_field.strip(),
        str(field_map.get("principal") or "").strip(),
        str(field_map.get("epic_name") or "").strip(),
    ]:
        if custom_field and custom_field not in requested_fields:
            requested_fields.append(custom_field)

    if raw_jql:
        jql = raw_jql
    else:
        proj_clause = ", ".join(projects)
        jql = f"project in ({proj_clause}) ORDER BY created ASC"
        if args.jql_extra.strip():
            jql = f"project in ({proj_clause}) AND ({args.jql_extra.strip()}) ORDER BY created ASC"

    out_path = args.out.strip() or default_out_path(projects)
    tag_sources = [part.strip() for part in str(args.tag_sources or "").split(",") if part.strip()]

    print(f"Consultando Jira com JQL: {jql}")
    issues = search_issues(
        base_url=base_url,
        email=email,
        token=token,
        jql=jql,
        fields=requested_fields,
        page_size=100,
    )
    print(f"Issues encontradas: {len(issues)}")

    rows = [
        build_output_row(
            base_url=base_url,
            issue=issue,
            field_map=field_map,
            board_name=args.board_name.strip(),
            board_id=args.board_id.strip(),
            workflow_name=args.workflow_name.strip(),
            default_column_name=args.default_column_name.strip(),
            default_lane_name=args.default_lane_name.strip(),
            status_to_column_map=status_to_column_map,
            status_to_lane_map=status_to_lane_map,
            priority_map=priority_map,
            owner_source=args.owner_source,
            owner_format=args.owner_format,
            tag_sources=tag_sources,
            type_name_map=type_name_map,
            lane_title_prefix_map=lane_title_prefix_map,
            lane_title_prefix_fallback=args.lane_by_title_prefix_fallback.strip(),
            size_field=size_field,
            start_date_field=args.start_date_field.strip(),
            end_date_field=args.end_date_field.strip(),
            omit_historical_dates=bool(args.omit_historical_dates),
        )
        for issue in issues
    ]

    df = pd.DataFrame(rows, columns=BUSINESSMAP_COLUMNS)
    written_paths = write_output_xlsx(df, out_path=out_path, split_size=max(0, int(args.split_size or 0)))

    populated_owner = int(df["Owner"].astype(str).str.strip().ne("").sum()) if not df.empty else 0
    populated_deadline = int(df["Deadline"].astype(str).str.strip().ne("").sum()) if not df.empty else 0
    if len(written_paths) == 1:
        print(f"Planilha gerada: {written_paths[0]}")
    else:
        print(f"Planilhas geradas em lotes ({len(written_paths)}):")
        for p in written_paths:
            print(f" - {p}")
    print(
        "Resumo colunas preenchidas: "
        f"Title={len(df)}, Owner={populated_owner}, Deadline={populated_deadline}, "
        f"Column name preenchida={int(df['Column name'].astype(str).str.strip().ne('').sum()) if not df.empty else 0}"
    )
    print(
        "Dica: valide no import do BusinessMap se 'Owner' corresponde ao username esperado no board; "
        "ajuste com --owner-format/--owner-source se necessário."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
