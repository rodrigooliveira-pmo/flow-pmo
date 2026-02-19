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
    "Tipo",
    "Status",
    "ParentID",
    "ParentTipo",
    "Link",
    "UpdatedAt",
    "StatusChangedAt",
]


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


def build_output_row(base_url: str, issue: Dict[str, Any]) -> Dict[str, str]:
    fields = issue.get("fields", {}) or {}
    parent = fields.get("parent") or {}
    parent_fields = parent.get("fields") or {}
    key = str(issue.get("key") or "")
    return {
        "ID": key,
        "Titulo": str(fields.get("summary") or ""),
        "Projeto": str((fields.get("project") or {}).get("key") or ""),
        "Tipo": str((fields.get("issuetype") or {}).get("name") or ""),
        "Status": str((fields.get("status") or {}).get("name") or ""),
        "ParentID": str(parent.get("key") or ""),
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

    fields = ["summary", "issuetype", "project", "parent", "status", "updated", "statuscategorychangedate"]

    print(f"Consultando Jira com JQL: {jql}")
    issues = search_issues(base_url=base_url, email=email, token=token, jql=jql, fields=fields, page_size=100)
    print(f"Issues encontradas: {len(issues)}")

    rows = [build_output_row(base_url=base_url, issue=issue) for issue in issues]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV gerado: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
