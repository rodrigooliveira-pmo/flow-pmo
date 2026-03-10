#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import time
import urllib.parse
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import chain
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

import requests

WORK_ITEM_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")
GLOBAL_RATE_LIMIT_UNTIL = 0.0
LAST_REQUEST_AT = 0.0
MIN_REQUEST_INTERVAL_SECONDS = 0.35
MAX_REQUEST_INTERVAL_SECONDS = 3.0
CURRENT_REQUEST_INTERVAL_SECONDS = 0.35

PROJECT_BITBUCKET_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "W1NNER": {
        "aliases": {"W1NNR", "W1NNER"},
        "issue_key_prefixes": {"W1NNR", "W1NNER"},
        "repo": "w1nner",
        "prefix": "w1nner",
    },
    "S1NC": {
        "aliases": {"S1NC", "W1SFT"},
        "issue_key_prefixes": {"S1NC", "W1SFT"},
        "repo": "w1nner",
        "prefix": "s1nc",
    },
    "BEFINANCE": {
        "aliases": {"BF", "BEFINANCE"},
        "issue_key_prefixes": {"BF", "BEFINANCE"},
        "repos": ["be-finance-api", "be-finance-web", "be-finance-lambda", "be-finance-diagnostic-api", "be-finance-diagnostic-web", "be-finance-dev"],
        "repo": "be-finance-api",
        "prefix": "befinance",
    },
    "DATA&ANALYTICS": {
        "aliases": {"DT", "DA", "DATA&ANALYTICS", "DATA&ANALITICS"},
        "issue_key_prefixes": {"DT", "DA"},
        "repos": ["d-a-analysis", "w1-data-toolbox", "automacao-rfv", "apuracao-indicadores-mensais", "api-resumo-e-insights", "c3po-automation"],
        "repo": "d-a-analysis",
        "prefix": "dataanalytics",
    },
}


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


def normalize_text(value: Any) -> str:
    raw = str(value or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", raw)
    no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return " ".join(no_accents.replace("_", " ").replace("-", " ").split())


def normalize_project_key(project: str) -> str:
    norm = normalize_text(project).upper().replace(" ", "")
    aliases = {
        "W1NNRI": "W1NNER",
        "W1NNR": "W1NNER",
        "W1NNER": "W1NNER",
        "W1SFT": "S1NC",
        "S1NC": "S1NC",
        "BF": "BEFINANCE",
        "BEFINANCE": "BEFINANCE",
        "DT": "DATA&ANALYTICS",
        "DA": "DATA&ANALYTICS",
        "DATA&ANALYTICS": "DATA&ANALYTICS",
        "DATA&ANALITICS": "DATA&ANALYTICS",
        "DATAANALYTICS": "DATA&ANALYTICS",
        "DATAANALITICS": "DATA&ANALYTICS",
    }
    return aliases.get(norm, str(project or "").strip().upper())


def parse_json_env(name: str) -> Dict[str, Any]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_issue_key_prefixes(values: Iterable[str]) -> list[str]:
    prefixes = []
    seen = set()
    for value in values:
        prefix = str(value or "").strip().upper()
        if not prefix or prefix in seen:
            continue
        seen.add(prefix)
        prefixes.append(prefix)
    return prefixes


def resolve_project_bitbucket_config(project: str) -> Dict[str, Any]:
    canonical_project = normalize_project_key(project)
    config = dict(PROJECT_BITBUCKET_DEFAULTS.get(canonical_project, {}))
    aliases = {str(alias).strip().upper() for alias in config.get("aliases", set()) if str(alias).strip()}
    if canonical_project:
        aliases.add(canonical_project)

    repo_map = parse_json_env("FLOW_PMO_BITBUCKET_REPO_MAP")
    repo_override = repo_map.get(canonical_project)
    if repo_override is None:
        for alias in aliases:
            if alias in repo_map:
                repo_override = repo_map[alias]
                break
    if isinstance(repo_override, str):
        config["repo"] = repo_override.strip()
    elif isinstance(repo_override, dict):
        for key in ("workspace", "repo", "prefix"):
            value = str(repo_override.get(key) or "").strip()
            if value:
                config[key] = value
        override_prefixes = repo_override.get("issue_key_prefixes")
        if isinstance(override_prefixes, list):
            config["issue_key_prefixes"] = [str(item).strip().upper() for item in override_prefixes if str(item).strip()]

    prefix_map = parse_json_env("FLOW_PMO_BITBUCKET_PREFIX_MAP")
    prefix_override = prefix_map.get(canonical_project)
    if prefix_override is None:
        for alias in aliases:
            if alias in prefix_map:
                prefix_override = prefix_map[alias]
                break
    if str(prefix_override or "").strip():
        config["prefix"] = str(prefix_override).strip()

    issue_key_prefix_map = parse_json_env("FLOW_PMO_BITBUCKET_ISSUE_KEY_PREFIX_MAP")
    issue_prefix_override = issue_key_prefix_map.get(canonical_project)
    if issue_prefix_override is None:
        for alias in aliases:
            if alias in issue_key_prefix_map:
                issue_prefix_override = issue_key_prefix_map[alias]
                break
    if isinstance(issue_prefix_override, list):
        config["issue_key_prefixes"] = [str(item).strip().upper() for item in issue_prefix_override if str(item).strip()]
    elif str(issue_prefix_override or "").strip():
        config["issue_key_prefixes"] = [str(issue_prefix_override).strip().upper()]

    config["canonical_project"] = canonical_project or str(project or "").strip().upper()
    config["issue_key_prefixes"] = _normalize_issue_key_prefixes(config.get("issue_key_prefixes", []))
    return config


def work_item_keys_match_project(work_item_keys: Iterable[str], allowed_prefixes: Iterable[str]) -> bool:
    allowed = {str(prefix or "").strip().upper() for prefix in allowed_prefixes if str(prefix or "").strip()}
    if not allowed:
        return True
    for key in work_item_keys:
        prefix = str(key or "").split("-", 1)[0].strip().upper()
        if prefix in allowed:
            return True
    return False


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

        response = request_with_retry(
            session,
            next_url,
            auth=auth,
            params=params if page_count == 1 else None,
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()

        for row in payload.get("values", []):
            if isinstance(row, dict):
                if stop_on_row is not None and stop_on_row(row):
                    should_stop = True
                    break
                yield row

        next_url = payload.get("next")


def _parse_retry_after_seconds(response: Optional[requests.Response]) -> float:
    if response is None:
        return 0.0
    retry_after = str(response.headers.get("Retry-After") or "").strip()
    if not retry_after:
        return 0.0
    try:
        seconds = float(retry_after)
    except ValueError:
        return 0.0
    return seconds if seconds > 0 else 0.0


def request_with_retry(
    session: requests.Session,
    url: str,
    *,
    auth: tuple[str, str],
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
    allow_redirects: bool = True,
    max_attempts: int = 8,
) -> requests.Response:
    global GLOBAL_RATE_LIMIT_UNTIL, LAST_REQUEST_AT, CURRENT_REQUEST_INTERVAL_SECONDS
    last_error: Optional[requests.RequestException] = None
    for attempt in range(1, max_attempts + 1):
        now = time.monotonic()
        if GLOBAL_RATE_LIMIT_UNTIL > now:
            time.sleep(GLOBAL_RATE_LIMIT_UNTIL - now)
            now = time.monotonic()
        if CURRENT_REQUEST_INTERVAL_SECONDS > 0:
            elapsed = now - LAST_REQUEST_AT
            if elapsed < CURRENT_REQUEST_INTERVAL_SECONDS:
                time.sleep(CURRENT_REQUEST_INTERVAL_SECONDS - elapsed)
        try:
            response = session.get(
                url,
                auth=auth,
                params=params,
                timeout=timeout,
                allow_redirects=allow_redirects,
            )
            LAST_REQUEST_AT = time.monotonic()
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= max_attempts:
                raise
            sleep_seconds = min(30.0, 1.5 ** attempt)
            print(
                f"Aviso: falha de rede ao consultar Bitbucket (tentativa {attempt}/{max_attempts}). "
                f"Nova tentativa em {sleep_seconds:.1f}s...",
                file=sys.stderr,
            )
            time.sleep(sleep_seconds)
            continue

        if response.status_code == 429 or 500 <= response.status_code < 600:
            if attempt >= max_attempts:
                response.raise_for_status()
            header_wait = _parse_retry_after_seconds(response)
            backoff_wait = min(60.0, 1.5 ** attempt)
            floor_wait = 8.0 if response.status_code == 429 else 3.0
            sleep_seconds = max(header_wait, backoff_wait, floor_wait)
            sleep_seconds += random.uniform(0.2, 1.0)
            GLOBAL_RATE_LIMIT_UNTIL = max(GLOBAL_RATE_LIMIT_UNTIL, time.monotonic() + sleep_seconds)
            if response.status_code == 429:
                CURRENT_REQUEST_INTERVAL_SECONDS = min(
                    MAX_REQUEST_INTERVAL_SECONDS,
                    max(MIN_REQUEST_INTERVAL_SECONDS, CURRENT_REQUEST_INTERVAL_SECONDS * 1.25),
                )
            reason = "rate limit (429)" if response.status_code == 429 else f"erro HTTP {response.status_code}"
            print(
                f"Aviso: Bitbucket retornou {reason} em {url} (tentativa {attempt}/{max_attempts}). "
                f"Nova tentativa em {sleep_seconds:.1f}s... interval={CURRENT_REQUEST_INTERVAL_SECONDS:.2f}s",
                file=sys.stderr,
            )
            time.sleep(sleep_seconds)
            continue

        if CURRENT_REQUEST_INTERVAL_SECONDS > MIN_REQUEST_INTERVAL_SECONDS:
            CURRENT_REQUEST_INTERVAL_SECONDS = max(
                MIN_REQUEST_INTERVAL_SECONDS,
                CURRENT_REQUEST_INTERVAL_SECONDS * 0.98,
            )
        return response

    if last_error is not None:
        raise last_error
    raise RuntimeError("Falha inesperada na rotina de retry HTTP.")


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
        page_count = 0
        next_url = normalize_diffstat_url(diffstat_url)
        params: Optional[Dict[str, Any]] = {
            "pagelen": pagelen,
            "fields": "values.lines_added,values.lines_removed,next",
        }

        while next_url:
            page_count += 1
            if max_pages and page_count > max_pages:
                break

            response = request_with_retry(
                session,
                next_url,
                auth=auth,
                params=params,
                timeout=60,
                allow_redirects=False,
            )

            if 300 <= response.status_code < 400:
                redirect_to = response.headers.get("Location", "")
                if not redirect_to:
                    response.raise_for_status()
                next_url = normalize_diffstat_url(urllib.parse.urljoin(response.url, redirect_to))
                params = None
                continue

            response.raise_for_status()
            payload = response.json()
            for row in payload.get("values", []):
                if not isinstance(row, dict):
                    continue
                files_changed += 1
                additions += _to_non_negative_int(row.get("lines_added"))
                deletions += _to_non_negative_int(row.get("lines_removed"))

            next_url = normalize_diffstat_url(payload.get("next") or "")
            params = None
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        # Alguns PRs retornam diffstat indisponível (404) mesmo via endpoint canônico.
        # Nesse caso seguimos sem volume para não poluir o log operacional.
        if status_code == 404:
            return {
                "additions": "",
                "deletions": "",
                "files_changed": "",
                "lines_changed_total": "",
            }
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


def normalize_diffstat_url(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    # Defensive cleanup: some Bitbucket links may include encoded/newline noise in the revspec.
    cleaned = raw.replace("\r", "").replace("\n", "")
    cleaned = cleaned.replace("%0D", "").replace("%0A", "").replace("%0d", "").replace("%0a", "")
    parsed = urllib.parse.urlsplit(cleaned)
    if not parsed.scheme or not parsed.netloc:
        return cleaned
    path = parsed.path.replace("\r", "").replace("\n", "")
    query = parsed.query.replace("\r", "").replace("\n", "")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, query, ""))


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
    parser.add_argument("--project", default="", help="Projeto lógico para resolver repo/prefixo/filtros (ex.: W1NNR, S1NC, BF, DT).")
    parser.add_argument("--workspace", default="", help="Workspace slug (override de BB_WORKSPACE).")
    parser.add_argument("--repo", default="", help="Repository slug (override de BB_REPO).")
    parser.add_argument("--email", default="", help="Email da conta Atlassian (override de BB_EMAIL).")
    parser.add_argument("--token", default="", help="Token da API Atlassian (override de BB_TOKEN).")
    parser.add_argument("--out-dir", default=".", help="Diretório de saída dos CSVs.")
    parser.add_argument("--prefix", default="bitbucket", help="Prefixo dos arquivos CSV de saída.")
    parser.add_argument(
        "--issue-key-prefixes",
        nargs="*",
        default=None,
        help="Prefixos Jira usados para filtrar itens no repositório (ex.: S1NC W1SFT).",
    )
    parser.add_argument("--pagelen", type=int, default=50, help="Pagelen da API Bitbucket (recomendado até 50).")
    parser.add_argument("--max-pages", type=int, default=0, help="Limite de páginas por endpoint (0 = sem limite).")
    parser.add_argument("--workers", type=int, default=3, help="Workers paralelos por endpoint (1 = sequencial).")
    parser.add_argument(
        "--min-request-interval-ms",
        type=int,
        default=350,
        help="Intervalo mínimo entre requisições HTTP em milissegundos (padrão: 350).",
    )
    parser.add_argument(
        "--max-request-interval-ms",
        type=int,
        default=3000,
        help="Teto do intervalo adaptativo entre requisições em milissegundos (padrão: 3000).",
    )
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
    global MIN_REQUEST_INTERVAL_SECONDS, MAX_REQUEST_INTERVAL_SECONDS, CURRENT_REQUEST_INTERVAL_SECONDS
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

    project_config: Dict[str, Any] = {}
    if args.project:
        project_config = resolve_project_bitbucket_config(args.project)
        workspace_override = str(project_config.get("workspace") or "").strip()
        repo_override = str(project_config.get("repo") or "").strip()
        prefix_override = str(project_config.get("prefix") or "").strip()
        if workspace_override and not args.workspace:
            os.environ["BB_WORKSPACE"] = workspace_override
        if repo_override and not args.repo:
            os.environ["BB_REPO"] = repo_override
        if prefix_override and args.prefix == "bitbucket":
            args.prefix = prefix_override

    try:
        email = require_env("BB_EMAIL")
        token = require_env("BB_TOKEN")
        workspace = require_env("BB_WORKSPACE")
        repo = os.getenv("BB_REPO", "").strip() or str(project_config.get("repo") or "").strip()
        if not repo:
            raise ValueError("Variável obrigatória ausente: BB_REPO")
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    # Build list of repos to query (supports multi-repo projects like BF, DT).
    repos_list: list[str] = []
    raw_repos = project_config.get("repos")
    if isinstance(raw_repos, list):
        repos_list = [r.strip() for r in raw_repos if str(r).strip()]
    elif isinstance(raw_repos, str):
        repos_list = [r.strip() for r in raw_repos.split(",") if r.strip()]
    if args.repo:
        repos_list = [args.repo.strip()]
    if not repos_list:
        repos_list = [repo]

    issue_key_prefixes = _normalize_issue_key_prefixes(
        args.issue_key_prefixes
        if args.issue_key_prefixes is not None
        else project_config.get("issue_key_prefixes", [])
    )

    if args.dry_run:
        print("Dry run OK: configuração carregada.")
        if project_config:
            print(f"project={project_config.get('canonical_project')}")
        print(f"workspace={workspace}")
        print(f"repos={','.join(repos_list)}")
        print(f"prefix={args.prefix}")
        print(f"issue_key_prefixes={','.join(issue_key_prefixes)}")
        print(f"email={email}")
        return 0

    pagelen = min(max(args.pagelen, 1), 50)
    max_pages = args.max_pages if args.max_pages > 0 else None
    MIN_REQUEST_INTERVAL_SECONDS = max(args.min_request_interval_ms, 0) / 1000.0
    MAX_REQUEST_INTERVAL_SECONDS = max(args.max_request_interval_ms, args.min_request_interval_ms, 0) / 1000.0
    CURRENT_REQUEST_INTERVAL_SECONDS = MIN_REQUEST_INTERVAL_SECONDS
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

    def row_matches_project(row: Dict[str, Any], *texts: str) -> bool:
        if not issue_key_prefixes:
            return True
        return work_item_keys_match_project(extract_work_item_keys(*texts), issue_key_prefixes)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    auth = (email, token)

    commits_csv = out_dir / f"{args.prefix}_commits.csv"
    prs_csv = out_dir / f"{args.prefix}_pullrequests.csv"
    pipelines_csv = out_dir / f"{args.prefix}_pipelines.csv"

    def _collect_commits_for_repo(current_repo: str) -> list[Dict[str, Any]]:
        repo_base = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{current_repo}"
        try:
            with requests.Session() as session:
                rows = iter_paginated(
                    session,
                    f"{repo_base}/commits",
                    auth=auth,
                    pagelen=pagelen,
                    max_pages=max_pages,
                    extra_params={
                        "fields": "values.hash,values.date,values.author.raw,values.message,next",
                    },
                    stop_on_row=lambda row: row_older_than_cutoff(row, ("date",)),
                )
                return [
                    row for row in rows
                    if row_matches_project(row, str(row.get("message") or ""))
                ]
        except requests.HTTPError as exc:
            print(f"  Aviso: repo '{current_repo}' — {exc}", file=sys.stderr)
            return []

    def run_commits() -> int:
        if args.skip_commits:
            return 0
        all_rows: list[Dict[str, Any]] = []
        for current_repo in repos_list:
            all_rows.extend(_collect_commits_for_repo(current_repo))
        return _safe_export(commits_csv, export_commits, iter(all_rows))

    def _collect_prs_for_repo(current_repo: str) -> list[Dict[str, Any]]:
        repo_base = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{current_repo}"
        try:
            with requests.Session() as session:
                rows = iter_paginated(
                    session,
                    f"{repo_base}/pullrequests",
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
                filtered = [
                    row for row in rows
                    if row_matches_project(
                        row,
                        str(row.get("title") or ""),
                        str((((row.get("source") or {}).get("branch") or {}).get("name")) if isinstance(row.get("source"), dict) else ""),
                        str((((row.get("destination") or {}).get("branch") or {}).get("name")) if isinstance(row.get("destination"), dict) else ""),
                    )
                ]
                if args.skip_pr_volume:
                    return filtered
                enriched = []
                for row in filtered:
                    if not isinstance(row, dict):
                        continue
                    pr_id = row.get("id")
                    diffstat_url = f"{repo_base}/pullrequests/{pr_id}/diffstat" if pr_id else ""
                    if not diffstat_url:
                        diffstat_url = (
                            ((row.get("links") or {}).get("diffstat") or {}).get("href")
                            if isinstance(row.get("links"), dict)
                            else ""
                        )
                    diffstat_url = normalize_diffstat_url(diffstat_url)
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
                        row.update({"additions": "", "deletions": "", "files_changed": "", "lines_changed_total": ""})
                    enriched.append(row)
                return enriched
        except requests.HTTPError as exc:
            print(f"  Aviso: repo '{current_repo}' — {exc}", file=sys.stderr)
            return []

    def run_pullrequests() -> int:
        if args.skip_pullrequests:
            return 0
        all_rows: list[Dict[str, Any]] = []
        for current_repo in repos_list:
            all_rows.extend(_collect_prs_for_repo(current_repo))
        return _safe_export(prs_csv, export_pullrequests, iter(all_rows))

    def _collect_pipelines_for_repo(current_repo: str) -> list[Dict[str, Any]]:
        repo_base = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{current_repo}"
        try:
            with requests.Session() as session:
                rows = iter_paginated(
                    session,
                    f"{repo_base}/pipelines/",
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
                return [
                    row for row in rows
                    if row_matches_project(
                        row,
                        str(((row.get("target") or {}).get("ref_name")) if isinstance(row.get("target"), dict) else ""),
                    )
                ]
        except requests.HTTPError as exc:
            print(f"  Aviso: repo '{current_repo}' — {exc}", file=sys.stderr)
            return []

    def run_pipelines() -> int:
        if args.skip_pipelines:
            return 0
        all_rows: list[Dict[str, Any]] = []
        for current_repo in repos_list:
            all_rows.extend(_collect_pipelines_for_repo(current_repo))
        return _safe_export(pipelines_csv, export_pipelines, iter(all_rows))

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

    repos_label = ", ".join(repos_list)
    print(f"Repos consultados: {repos_label}")
    print(f"Commits exportados: {commit_count} -> {commits_csv}")
    print(f"Pull requests exportados: {pr_count} -> {prs_csv}")
    print(f"Pipelines exportados: {pipeline_count} -> {pipelines_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
