#!/usr/bin/env python3
"""
Exporta dados de portfólio do Jira (projetos BT e NS) para CSV local.

Uso:
  python jira_portfolio_to_csv.py
  python jira_portfolio_to_csv.py --projects BT NS --out "C:\\Users\\W1 TI\\OneDrive - W1\\Documentos\\Dados\\portfolio-bt-ns-20260219-data.csv"
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

CSV_COLUMNS = [
    "ID",
    "Titulo",
    "Projeto",
    "Team",
    "EffortTShirtSize",
    "Tipo",
    "Status",
    "ParentID",
    "ParentTipo",
    "Link",
    "UpdatedAt",
    "StatusChangedAt",
]


def parse_json_env(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return default
    return parsed if isinstance(parsed, dict) else default


def load_env_file(env_file: str) -> None:
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
        if key and value and key not in os.environ:
            os.environ[key] = value


def search_issues(base_url: str, email: str, token: str, jql: str, fields: List[str], page_size: int = 100) -> List[Dict[str, Any]]:
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


def discover_field_id(base_url: str, email: str, token: str, target_name: str) -> str:
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

    target = str(target_name or "").strip().lower()
    if not isinstance(field_defs, list):
        return ""

    # 1) Match exato por nome visível.
    for f in field_defs:
        name = str((f or {}).get("name") or "").strip().lower()
        fid = str((f or {}).get("id") or "").strip()
        if name == target and fid:
            return fid

    # 2) Fallback por schema de Team (varia entre plugins/instâncias).
    for f in field_defs:
        schema = (f or {}).get("schema") or {}
        schema_type = str(schema.get("type") or "").strip().lower()
        schema_custom = str(schema.get("custom") or "").strip().lower()
        fid = str((f or {}).get("id") or "").strip()
        if not fid:
            continue
        if "team" in schema_type or "team" in schema_custom:
            return fid

    return ""


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


def extract_team_from_fields(fields: Dict[str, Any], team_field: str) -> str:
    candidates: List[Any] = []
    if team_field:
        candidates.append(fields.get(team_field))
    for k in ("teams", "team", "Teams", "Team"):
        if k in fields:
            candidates.append(fields.get(k))
    for val in candidates:
        text = extract_custom_text(val).strip()
        if text:
            return text
    return ""


def is_feature_issue(issue_type_name: str) -> bool:
    tipo = str(issue_type_name or "").strip().lower()
    return tipo in {"feature", "funcionalidade"}


def build_output_row(
    base_url: str,
    issue: Dict[str, Any],
    team_field: str,
    effort_tshirt_field: str,
    issue_team_map: Dict[str, str],
) -> Dict[str, str]:
    fields = issue.get("fields", {}) or {}
    parent = fields.get("parent") or {}
    parent_fields = parent.get("fields") or {}
    key = str(issue.get("key") or "")
    parent_id = str(parent.get("key") or "")
    own_team = extract_team_from_fields(fields, team_field=team_field)
    parent_team = extract_team_from_fields(parent_fields, team_field=team_field)
    if not parent_team and parent_id:
        parent_team = str(issue_team_map.get(parent_id) or "")
    team_text = own_team or parent_team
    issue_type_name = str((fields.get("issuetype") or {}).get("name") or "")
    effort_tshirt_size = ""
    if effort_tshirt_field and is_feature_issue(issue_type_name):
        effort_tshirt_size = extract_custom_text(fields.get(effort_tshirt_field)).strip()
    return {
        "ID": key,
        "Titulo": str(fields.get("summary") or ""),
        "Projeto": str((fields.get("project") or {}).get("key") or ""),
        "Team": team_text,
        "EffortTShirtSize": effort_tshirt_size,
        "Tipo": issue_type_name,
        "Status": str((fields.get("status") or {}).get("name") or ""),
        "ParentID": parent_id,
        "ParentTipo": str((parent_fields.get("issuetype") or {}).get("name") or ""),
        "Link": f"{base_url}/browse/{key}" if key else "",
        "UpdatedAt": str(fields.get("updated") or ""),
        "StatusChangedAt": str(fields.get("statuscategorychangedate") or ""),
    }


def default_out_path(projects: List[str]) -> str:
    if os.name == "nt":
        data_folder = r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados"
    else:
        data_folder = os.path.join(os.path.expanduser("~"), "Library", "CloudStorage", "OneDrive-W1", "Documentos", "Dados")
    date_tag = datetime.now().strftime("%Y%m%d")
    project_tag = "-".join([p.strip().lower() for p in projects if p.strip()])
    filename = f"portfolio-{project_tag}-{date_tag}-data.csv"
    return os.path.join(data_folder, filename)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta portfólio Jira para CSV local.")
    parser.add_argument("--projects", nargs="+", default=["BT", "NS"], help="Projetos Jira para exportar (default: BT NS)")
    parser.add_argument("--out", default="", help="Caminho do CSV de saída")
    parser.add_argument("--jql-extra", default="", help="Filtro JQL adicional opcional")
    parser.add_argument(
        "--env-file",
        default=str(Path(__file__).with_name("jira_env.txt")),
        help="Arquivo com variáveis no formato KEY=VALUE (default: jira_env.txt ao lado do script)",
    )
    args = parser.parse_args()

    load_env_file(args.env_file)
    base_url = os.getenv("JIRA_BASE_URL", "").strip().rstrip("/")
    email = os.getenv("JIRA_EMAIL", "").strip()
    token = os.getenv("JIRA_API_TOKEN", "").strip()

    if not base_url or not email or not token:
        print("Erro: defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN.", file=sys.stderr)
        return 2

    projects = [p.strip().upper() for p in args.projects if p and p.strip()]
    if not projects:
        print("Erro: informe ao menos um projeto.", file=sys.stderr)
        return 2

    out_path = args.out.strip() or default_out_path(projects)
    proj_clause = ", ".join(projects)
    jql = f"project in ({proj_clause})"
    if args.jql_extra.strip():
        jql = f"{jql} AND ({args.jql_extra.strip()})"

    field_map = parse_json_env("JIRA_FIELD_MAP", default={})
    team_field = str(field_map.get("team") or "").strip()
    effort_tshirt_field = str(field_map.get("effort_tshirt_size") or "").strip()
    if not team_field:
        team_field = discover_field_id(base_url=base_url, email=email, token=token, target_name="Team")
        if team_field:
            print(f"Campo Team autodetectado: {team_field}")

    fields = ["summary", "issuetype", "project", "parent", "status", "updated", "statuscategorychangedate"]
    if team_field and team_field not in fields:
        fields.append(team_field)
    if effort_tshirt_field and effort_tshirt_field not in fields:
        fields.append(effort_tshirt_field)

    print(f"Consultando Jira com JQL: {jql}")
    issues = search_issues(base_url=base_url, email=email, token=token, jql=jql, fields=fields, page_size=100)
    print(f"Issues encontradas: {len(issues)}")

    # Se o customfield configurado para TEAM estiver incorreto, tenta autodetectar e consulta novamente.
    if issues and team_field:
        has_team_field = False
        sample_size = min(25, len(issues))
        for issue in issues[:sample_size]:
            issue_fields = issue.get("fields", {}) or {}
            if team_field in issue_fields:
                has_team_field = True
                break
        if not has_team_field:
            discovered_team_field = discover_field_id(base_url=base_url, email=email, token=token, target_name="Team")
            if discovered_team_field and discovered_team_field != team_field:
                print(
                    f"Campo Team configurado ({team_field}) não retornou dados. "
                    f"Usando autodetectado ({discovered_team_field}) e repetindo consulta."
                )
                team_field = discovered_team_field
                fields = [f for f in fields if f != team_field]
                if team_field not in fields:
                    fields.append(team_field)
                issues = search_issues(base_url=base_url, email=email, token=token, jql=jql, fields=fields, page_size=100)
                print(f"Issues reconsultadas: {len(issues)}")

    issue_team_map: Dict[str, str] = {}
    for issue in issues:
        key = str(issue.get("key") or "")
        if not key:
            continue
        issue_fields = issue.get("fields", {}) or {}
        issue_team_map[key] = extract_team_from_fields(issue_fields, team_field=team_field)

    rows = [
        build_output_row(
            base_url=base_url,
            issue=issue,
            team_field=team_field,
            effort_tshirt_field=effort_tshirt_field,
            issue_team_map=issue_team_map,
        )
        for issue in issues
    ]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV gerado: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
