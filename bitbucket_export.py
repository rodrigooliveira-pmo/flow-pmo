#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests


def load_env_file(env_file: str, overwrite: bool = False) -> None:
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


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Variável obrigatória ausente: {name}")
    return value


def iter_paginated(
    session: requests.Session,
    url: str,
    *,
    auth: tuple[str, str],
    pagelen: int,
    max_pages: Optional[int],
) -> Iterable[Dict[str, Any]]:
    page_count = 0
    next_url = url
    params = {"pagelen": pagelen}

    while next_url:
        page_count += 1
        if max_pages and page_count > max_pages:
            break

        response = session.get(next_url, auth=auth, params=params if page_count == 1 else None, timeout=60)
        response.raise_for_status()
        payload = response.json()

        for row in payload.get("values", []):
            if isinstance(row, dict):
                yield row

        next_url = payload.get("next")


def export_commits(rows: Iterable[Dict[str, Any]], output_path: Path) -> int:
    fields = ["hash", "date", "author", "message"]
    count = 0
    with output_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            author = ((row.get("author") or {}).get("raw")) if isinstance(row.get("author"), dict) else ""
            message = (row.get("message") or "").splitlines()[0] if row.get("message") else ""
            writer.writerow(
                {
                    "hash": str(row.get("hash") or ""),
                    "date": str(row.get("date") or ""),
                    "author": str(author or ""),
                    "message": message,
                }
            )
            count += 1
    return count


def export_pullrequests(rows: Iterable[Dict[str, Any]], output_path: Path) -> int:
    fields = ["id", "state", "title", "author", "created_on", "updated_on", "source_branch", "destination_branch"]
    count = 0
    with output_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            source_branch = (
                ((row.get("source") or {}).get("branch") or {}).get("name")
                if isinstance(row.get("source"), dict)
                else ""
            )
            destination_branch = (
                ((row.get("destination") or {}).get("branch") or {}).get("name")
                if isinstance(row.get("destination"), dict)
                else ""
            )
            author_name = (
                ((row.get("author") or {}).get("display_name")) if isinstance(row.get("author"), dict) else ""
            )
            writer.writerow(
                {
                    "id": row.get("id") or "",
                    "state": row.get("state") or "",
                    "title": row.get("title") or "",
                    "author": author_name or "",
                    "created_on": row.get("created_on") or "",
                    "updated_on": row.get("updated_on") or "",
                    "source_branch": source_branch or "",
                    "destination_branch": destination_branch or "",
                }
            )
            count += 1
    return count


def export_pipelines(rows: Iterable[Dict[str, Any]], output_path: Path) -> int:
    fields = [
        "uuid",
        "build_number",
        "state",
        "state_type",
        "state_result",
        "created_on",
        "completed_on",
        "ref_name",
        "commit_hash",
    ]
    count = 0
    with output_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            target = row.get("target") if isinstance(row.get("target"), dict) else {}
            state = row.get("state") if isinstance(row.get("state"), dict) else {}
            result = state.get("result") if isinstance(state.get("result"), dict) else {}
            commit_hash = ((target.get("commit") or {}).get("hash")) if isinstance(target, dict) else ""
            writer.writerow(
                {
                    "uuid": row.get("uuid") or "",
                    "build_number": row.get("build_number") or "",
                    "state": state.get("name") or "",
                    "state_type": state.get("type") or "",
                    "state_result": result.get("name") or "",
                    "created_on": row.get("created_on") or "",
                    "completed_on": row.get("completed_on") or "",
                    "ref_name": target.get("ref_name") if isinstance(target, dict) else "",
                    "commit_hash": commit_hash or "",
                }
            )
            count += 1
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta commits, pull requests e pipelines do Bitbucket para CSV lendo credenciais do .env."
    )
    parser.add_argument("--env-file", default=".env", help="Arquivo .env com BB_EMAIL/BB_TOKEN/BB_WORKSPACE/BB_REPO.")
    parser.add_argument("--workspace", default="", help="Workspace slug (override de BB_WORKSPACE).")
    parser.add_argument("--repo", default="", help="Repository slug (override de BB_REPO).")
    parser.add_argument("--email", default="", help="Email da conta Atlassian (override de BB_EMAIL).")
    parser.add_argument("--token", default="", help="Token da API Atlassian (override de BB_TOKEN).")
    parser.add_argument("--out-dir", default=".", help="Diretório de saída dos CSVs.")
    parser.add_argument("--prefix", default="bitbucket", help="Prefixo dos arquivos CSV de saída.")
    parser.add_argument("--pagelen", type=int, default=50, help="Pagelen da API Bitbucket (recomendado até 50).")
    parser.add_argument("--max-pages", type=int, default=0, help="Limite de páginas por endpoint (0 = sem limite).")
    parser.add_argument("--dry-run", action="store_true", help="Valida configuração sem chamar a API.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(args.env_file, overwrite=False)

    if args.email:
        os.environ["BB_EMAIL"] = args.email
    if args.token:
        os.environ["BB_TOKEN"] = args.token
    if args.workspace:
        os.environ["BB_WORKSPACE"] = args.workspace
    if args.repo:
        os.environ["BB_REPO"] = args.repo

    try:
        email = require_env("BB_EMAIL")
        token = require_env("BB_TOKEN")
        workspace = require_env("BB_WORKSPACE")
        repo = require_env("BB_REPO")
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print("Dry run OK: configuração carregada.")
        print(f"workspace={workspace}")
        print(f"repo={repo}")
        print(f"email={email}")
        return 0

    pagelen = min(max(args.pagelen, 1), 50)
    max_pages = args.max_pages if args.max_pages > 0 else None

    base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    auth = (email, token)

    commits_csv = out_dir / f"{args.prefix}_commits.csv"
    prs_csv = out_dir / f"{args.prefix}_pullrequests.csv"
    pipelines_csv = out_dir / f"{args.prefix}_pipelines.csv"

    try:
        commit_rows = iter_paginated(
            session,
            f"{base_url}/commits",
            auth=auth,
            pagelen=pagelen,
            max_pages=max_pages,
        )
        commit_count = export_commits(commit_rows, commits_csv)

        pr_rows = iter_paginated(
            session,
            f"{base_url}/pullrequests",
            auth=auth,
            pagelen=pagelen,
            max_pages=max_pages,
        )
        pr_count = export_pullrequests(pr_rows, prs_csv)

        pipeline_rows = iter_paginated(
            session,
            f"{base_url}/pipelines/",
            auth=auth,
            pagelen=pagelen,
            max_pages=max_pages,
        )
        pipeline_count = export_pipelines(pipeline_rows, pipelines_csv)
    except requests.HTTPError as exc:
        body = ""
        if exc.response is not None:
            try:
                body = exc.response.text
            except Exception:
                body = ""
        print(f"Erro HTTP ao consultar Bitbucket: {exc}", file=sys.stderr)
        if body:
            print(body, file=sys.stderr)
        return 1

    print(f"Commits exportados: {commit_count} -> {commits_csv}")
    print(f"Pull requests exportados: {pr_count} -> {prs_csv}")
    print(f"Pipelines exportados: {pipeline_count} -> {pipelines_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
