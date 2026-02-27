#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

import requests

WORK_ITEM_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fp:
        return sum(1 for _ in fp)


def _safe_export(output_path: Path, exporter_fn, rows: Iterable[Dict[str, Any]]) -> int:
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    count = exporter_fn(rows, tmp_path)
    existing_lines = _line_count(output_path)
    tmp_lines = _line_count(tmp_path)
    # Evita perder histórico válido se uma execução falhar/parcial e gerar só cabeçalho.
    if tmp_lines <= 1 and existing_lines > 1:
        tmp_path.unlink(missing_ok=True)
        return existing_lines - 1
    tmp_path.replace(output_path)
    return count


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


def extract_work_item_keys(*texts: str) -> list[str]:
    keys: list[str] = []
    seen = set()
    for raw in texts:
        txt = str(raw or "").upper()
        for match in WORK_ITEM_KEY_RE.findall(txt):
            key = str(match).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            keys.append(key)
    return keys


def iter_paginated(
    session: requests.Session,
    url: str,
    *,
    auth: tuple[str, str],
    pagelen: int,
    max_pages: Optional[int],
    extra_params: Optional[Dict[str, Any]] = None,
    stop_on_row: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> Iterable[Dict[str, Any]]:
    page_count = 0
    next_url = url
    params = {"pagelen": pagelen}
    if extra_params:
        params.update(extra_params)

    should_stop = False
    while next_url and not should_stop:
        page_count += 1
        if max_pages and page_count > max_pages:
            break

        response = session.get(next_url, auth=auth, params=params if page_count == 1 else None, timeout=60)
        response.raise_for_status()
        payload = response.json()

        for row in payload.get("values", []):
            if isinstance(row, dict):
                if stop_on_row is not None and stop_on_row(row):
                    should_stop = True
                    break
                yield row

        next_url = payload.get("next")


def export_commits(rows: Iterable[Dict[str, Any]], output_path: Path) -> int:
    fields = ["hash", "date", "author", "message", "work_item_keys", "primary_work_item_key"]
    count = 0
    with output_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            author = ((row.get("author") or {}).get("raw")) if isinstance(row.get("author"), dict) else ""
            message = (row.get("message") or "").splitlines()[0] if row.get("message") else ""
            work_item_keys = extract_work_item_keys(message)
            writer.writerow(
                {
                    "hash": str(row.get("hash") or ""),
                    "date": str(row.get("date") or ""),
                    "author": str(author or ""),
                    "message": message,
                    "work_item_keys": "|".join(work_item_keys),
                    "primary_work_item_key": work_item_keys[0] if work_item_keys else "",
                }
            )
            count += 1
    return count


def export_pullrequests(rows: Iterable[Dict[str, Any]], output_path: Path) -> int:
    fields = [
        "id",
        "state",
        "title",
        "author",
        "created_on",
        "updated_on",
        "source_branch",
        "destination_branch",
        "reviewers_total",
        "reviewers_approved_count",
        "reviewers_changes_requested_count",
        "approved_by",
        "changes_requested_by",
        "additions",
        "deletions",
        "files_changed",
        "lines_changed_total",
        "work_item_keys",
        "primary_work_item_key",
    ]
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
            participants = row.get("participants") if isinstance(row.get("participants"), list) else []
            work_item_keys = extract_work_item_keys(
                row.get("title") or "",
                source_branch or "",
                destination_branch or "",
            )
            approved_by = []
            changes_requested_by = []
            reviewers_total = 0
            for participant in participants:
                if not isinstance(participant, dict):
                    continue
                role = str(participant.get("role") or "").strip().lower()
                if role and role != "reviewer":
                    continue
                reviewers_total += 1
                user = participant.get("user") if isinstance(participant.get("user"), dict) else {}
                display_name = (
                    str(user.get("display_name") or participant.get("display_name") or "").strip()
                )
                approved = participant.get("approved")
                state = str(participant.get("state") or "").strip().lower()
                if approved is True and display_name:
                    approved_by.append(display_name)
                if state in {"changes_requested", "needs_work", "request_changes", "requested_changes"} and display_name:
                    changes_requested_by.append(display_name)

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
                    "reviewers_total": reviewers_total,
                    "reviewers_approved_count": len(approved_by),
                    "reviewers_changes_requested_count": len(changes_requested_by),
                    "approved_by": "|".join(sorted(set(approved_by))),
                    "changes_requested_by": "|".join(sorted(set(changes_requested_by))),
                    "additions": row.get("additions", ""),
                    "deletions": row.get("deletions", ""),
                    "files_changed": row.get("files_changed", ""),
                    "lines_changed_total": row.get("lines_changed_total", ""),
                    "work_item_keys": "|".join(work_item_keys),
                    "primary_work_item_key": work_item_keys[0] if work_item_keys else "",
                }
            )
            count += 1
    return count


def _to_non_negative_int(value: Any) -> int:
    try:
        out = int(value)
    except (TypeError, ValueError):
        return 0
    return out if out >= 0 else 0


def fetch_pullrequest_volume(
    session: requests.Session,
    diffstat_url: str,
    *,
    auth: tuple[str, str],
    pagelen: int,
    max_pages: Optional[int],
) -> Dict[str, Any]:
    additions = 0
    deletions = 0
    files_changed = 0
    try:
        rows = iter_paginated(
            session,
            diffstat_url,
            auth=auth,
            pagelen=pagelen,
            max_pages=max_pages,
            extra_params={
                "fields": "values.lines_added,values.lines_removed,next",
            },
        )
        for row in rows:
            files_changed += 1
            additions += _to_non_negative_int(row.get("lines_added"))
            deletions += _to_non_negative_int(row.get("lines_removed"))
    except requests.RequestException as exc:
        print(
            f"Aviso: falha ao coletar diffstat do PR ({diffstat_url}): {exc}",
            file=sys.stderr,
        )
        return {
            "additions": "",
            "deletions": "",
            "files_changed": "",
            "lines_changed_total": "",
        }

    return {
        "additions": additions,
        "deletions": deletions,
        "files_changed": files_changed,
        "lines_changed_total": additions + deletions,
    }


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
        "work_item_keys",
        "primary_work_item_key",
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
            ref_name = target.get("ref_name") if isinstance(target, dict) else ""
            work_item_keys = extract_work_item_keys(ref_name)
            writer.writerow(
                {
                    "uuid": row.get("uuid") or "",
                    "build_number": row.get("build_number") or "",
                    "state": state.get("name") or "",
                    "state_type": state.get("type") or "",
                    "state_result": result.get("name") or "",
                    "created_on": row.get("created_on") or "",
                    "completed_on": row.get("completed_on") or "",
                    "ref_name": ref_name,
                    "commit_hash": commit_hash or "",
                    "work_item_keys": "|".join(work_item_keys),
                    "primary_work_item_key": work_item_keys[0] if work_item_keys else "",
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
    parser.add_argument("--workers", type=int, default=3, help="Workers paralelos por endpoint (1 = sequencial).")
    parser.add_argument("--since-days", type=int, default=0, help="Exporta apenas itens dos últimos N dias (0 = histórico completo).")
    parser.add_argument(
        "--skip-pr-volume",
        action="store_true",
        help="Não consulta diffstat por PR (mais rápido, porém sem colunas de volume).",
    )
    parser.add_argument("--skip-commits", action="store_true", help="Não exporta commits.")
    parser.add_argument("--skip-pullrequests", action="store_true", help="Não exporta pull requests.")
    parser.add_argument("--skip-pipelines", action="store_true", help="Não exporta pipelines.")
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
    since_cutoff = None
    if args.since_days and args.since_days > 0:
        since_cutoff = datetime.now(timezone.utc) - timedelta(days=args.since_days)

    def row_older_than_cutoff(row: Dict[str, Any], date_keys: tuple[str, ...]) -> bool:
        if since_cutoff is None:
            return False
        raw_value = ""
        for key in date_keys:
            value = row.get(key)
            if value:
                raw_value = str(value)
                break
        if not raw_value:
            return False
        normalized = raw_value.replace("Z", "+00:00")
        try:
            ts = datetime.fromisoformat(normalized)
        except ValueError:
            return False
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts < since_cutoff

    base_url = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo}"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    auth = (email, token)

    commits_csv = out_dir / f"{args.prefix}_commits.csv"
    prs_csv = out_dir / f"{args.prefix}_pullrequests.csv"
    pipelines_csv = out_dir / f"{args.prefix}_pipelines.csv"

    def run_commits() -> int:
        if args.skip_commits:
            return 0
        with requests.Session() as session:
            rows = iter_paginated(
                session,
                f"{base_url}/commits",
                auth=auth,
                pagelen=pagelen,
                max_pages=max_pages,
                extra_params={
                    "fields": "values.hash,values.date,values.author.raw,values.message,next",
                },
                stop_on_row=lambda row: row_older_than_cutoff(row, ("date",)),
            )
            return _safe_export(commits_csv, export_commits, rows)

    def run_pullrequests() -> int:
        if args.skip_pullrequests:
            return 0
        with requests.Session() as session:
            rows = iter_paginated(
                session,
                f"{base_url}/pullrequests",
                auth=auth,
                pagelen=pagelen,
                max_pages=max_pages,
                extra_params={
                    "state": "ALL",
                    "fields": (
                        "values.id,values.state,values.title,values.author.display_name,"
                        "values.created_on,values.updated_on,values.source.branch.name,"
                        "values.destination.branch.name,values.participants.role,"
                        "values.participants.approved,values.participants.state,"
                        "values.participants.display_name,values.participants.user.display_name,"
                        "values.links.diffstat.href,next"
                    ),
                },
                stop_on_row=lambda row: row_older_than_cutoff(row, ("updated_on", "created_on")),
            )
            if args.skip_pr_volume:
                return _safe_export(prs_csv, export_pullrequests, rows)

            def iter_enriched_pullrequests() -> Iterable[Dict[str, Any]]:
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    diffstat_url = (
                        ((row.get("links") or {}).get("diffstat") or {}).get("href")
                        if isinstance(row.get("links"), dict)
                        else ""
                    )
                    if not diffstat_url:
                        pr_id = row.get("id")
                        if pr_id:
                            diffstat_url = f"{base_url}/pullrequests/{pr_id}/diffstat"
                    if diffstat_url:
                        row.update(
                            fetch_pullrequest_volume(
                                session,
                                str(diffstat_url),
                                auth=auth,
                                pagelen=pagelen,
                                max_pages=max_pages,
                            )
                        )
                    else:
                        row.update(
                            {
                                "additions": "",
                                "deletions": "",
                                "files_changed": "",
                                "lines_changed_total": "",
                            }
                        )
                    yield row

            return _safe_export(prs_csv, export_pullrequests, iter_enriched_pullrequests())

    def run_pipelines() -> int:
        if args.skip_pipelines:
            return 0
        with requests.Session() as session:
            rows = iter_paginated(
                session,
                f"{base_url}/pipelines/",
                auth=auth,
                pagelen=pagelen,
                max_pages=max_pages,
                extra_params={
                    "fields": (
                        "values.uuid,values.build_number,values.state.name,values.state.type,"
                        "values.state.result.name,values.created_on,values.completed_on,"
                        "values.target.ref_name,values.target.commit.hash,next"
                    ),
                },
                stop_on_row=lambda row: row_older_than_cutoff(row, ("completed_on", "created_on")),
            )
            return _safe_export(pipelines_csv, export_pipelines, rows)

    try:
        workers = min(max(args.workers, 1), 3)
        commit_count = pr_count = pipeline_count = 0
        jobs = {
            "commits": run_commits,
            "pullrequests": run_pullrequests,
            "pipelines": run_pipelines,
        }

        if workers == 1:
            commit_count = run_commits()
            pr_count = run_pullrequests()
            pipeline_count = run_pipelines()
        else:
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {executor.submit(fn): name for name, fn in jobs.items()}
                for future in as_completed(future_map):
                    name = future_map[future]
                    count = future.result()
                    if name == "commits":
                        commit_count = count
                    elif name == "pullrequests":
                        pr_count = count
                    elif name == "pipelines":
                        pipeline_count = count
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
    except Exception as exc:
        print(f"Erro ao exportar dados do Bitbucket: {exc}", file=sys.stderr)
        return 1

    print(f"Commits exportados: {commit_count} -> {commits_csv}")
    print(f"Pull requests exportados: {pr_count} -> {prs_csv}")
    print(f"Pipelines exportados: {pipeline_count} -> {pipelines_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
