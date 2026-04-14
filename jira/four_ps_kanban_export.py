"""Exporta os dados dos boards Kanban 4Ps para um CSV.

O CSV gerado serve como fonte de dados estática para carregar os boards
na aba 4Ps sem precisar fazer integração online no dashboard.

Uso:
    python jira/four_ps_kanban_export.py --out four_ps_kanban.csv

O arquivo `jira_env.txt` ou `.env` pode conter:
    JIRA_BASE_URL=https://w1consultoria.atlassian.net
    JIRA_EMAIL=seu.email@w1.com.br
    JIRA_API_TOKEN=seu_token
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

# When this script is run as a file inside the jira package folder,
# Python sets sys.path[0] to the jira directory, which prevents local
# imports from resolving the package root. Ensure project root is first.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from jira.client import JiraClient
from jira.four_ps_kanban import FourPsKanbanExtractor, load_four_ps_config
from shared.env_utils import load_env_file

DEFAULT_OUTPUT = str(ROOT_DIR / "four_ps_kanban.csv")

CSV_COLUMNS = [
    "area_name",
    "bucket",
    "project",
    "board_id",
    "key",
    "title",
    "status",
    "status_category",
    "issue_type",
    "priority",
    "assignee",
    "due_date",
    "updated",
    "status_changed_at",
    "parent_key",
    "parent_type",
    "epic_link",
    "is_bau",
    "days_stale",
    "team",
    "link",
]


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return path
    except PermissionError as exc:
        fallback = Path.cwd() / path.name
        print(f"Erro de permissão ao escrever em {path}: {exc}")
        print(f"Tentando gravar em fallback local: {fallback}")
        with fallback.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        return fallback


def _load_jira_env(env_file: str) -> None:
    path = Path(env_file)
    if not path.is_absolute():
        path = Path.cwd() / path

    script_root = Path(__file__).resolve().parent.parent
    candidates = [path, script_root / env_file]
    candidates.extend(
        script_root / alt
        for alt in ("jira_env.txt", "jira-env.txt", ".env", ".env.local")
        if script_root / alt not in candidates
    )

    loaded = False
    for candidate in candidates:
        if candidate.exists():
            load_env_file(str(candidate), overwrite=True)
            loaded = True

    if not loaded:
        print(f"Aviso: nenhum arquivo de ambiente encontrado em {env_file} ou no diretório do projeto.")


def _build_board_config_map() -> Dict[str, Dict[str, Any]]:
    cfg = load_four_ps_config()
    result: Dict[str, Dict[str, Any]] = {}
    for area_cfg in cfg.get("kanban_areas") or []:
        name = str(area_cfg.get("name") or "").strip()
        if name:
            result[name] = {
                "project": str(area_cfg.get("project") or "").strip(),
                "board_id": str(area_cfg.get("board_id") or "").strip(),
            }
    return result


def _item_row(area_name: str, bucket: str, item: Dict[str, Any], board_config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "area_name": area_name,
        "bucket": bucket,
        "project": item.get("project") or board_config.get("project", ""),
        "board_id": board_config.get("board_id", ""),
        "key": item.get("key", ""),
        "title": item.get("title", ""),
        "status": item.get("status", ""),
        "status_category": item.get("status_category", ""),
        "issue_type": item.get("issue_type", ""),
        "priority": item.get("priority", ""),
        "assignee": item.get("assignee", ""),
        "due_date": item.get("due_date", ""),
        "updated": item.get("updated", ""),
        "status_changed_at": item.get("status_changed_at", ""),
        "parent_key": item.get("parent_key", ""),
        "parent_type": item.get("parent_type", ""),
        "epic_link": item.get("epic_link", ""),
        "is_bau": "true" if item.get("is_bau") else "false",
        "days_stale": item.get("days_stale", 0),
        "team": item.get("team", ""),
        "link": item.get("link", ""),
    }


def _load_jira_credentials() -> Dict[str, str]:
    return {
        "base_url": os.getenv("JIRA_BASE_URL", "").strip(),
        "email": os.getenv("JIRA_EMAIL", "").strip(),
        "api_token": os.getenv("JIRA_API_TOKEN", "").strip(),
    }


def _validate_jira_credentials(creds: Dict[str, str]) -> bool:
    return bool(creds["base_url"] and creds["email"] and creds["api_token"])


def _parse_month(month_text: str | None) -> date:
    if not month_text:
        return date.today().replace(day=1)
    try:
        return date.fromisoformat(month_text)
    except ValueError:
        return date.fromisoformat(f"{month_text}-01")


def _history_date_range(month: date, history_months: int) -> Tuple[date, date]:
    """Retorna (date_start, date_end) para o histórico de concluídos.

    date_end = último dia do mês de referência.
    date_start = primeiro dia de (month - history_months + 1) meses.
    """
    from datetime import date as _date
    # Fim: último dia do mês de referência
    end_m = month.month + 1
    end_y = month.year + (end_m - 1) // 12
    end_m = (end_m - 1) % 12 + 1
    date_end = _date(end_y, end_m, 1) - timedelta(days=1)

    # Início: history_months atrás
    start_total = month.month - history_months + 1
    start_y = month.year + (start_total - 1) // 12 if start_total > 0 else month.year - (-start_total // 12 + 1)
    # Cálculo robusto para subtração de meses
    total_months_abs = month.year * 12 + month.month - history_months
    start_y = total_months_abs // 12
    start_m = total_months_abs % 12 + 1
    date_start = _date(start_y, start_m, 1)

    return date_start, date_end


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta os boards Kanban 4Ps para CSV.")
    parser.add_argument("--out", default=DEFAULT_OUTPUT, help="Caminho do CSV de saída.")
    parser.add_argument("--env-file", default="jira_env.txt", help="Arquivo .env ou jira_env.txt com credenciais Jira.")
    parser.add_argument("--month", default="", help="Mês de referência YYYY-MM ou YYYY-MM-DD para filtros de next steps.")
    parser.add_argument("--history-months", type=int, default=6,
                        help="Quantos meses para trás incluir itens concluídos (padrão: 6).")
    parser.add_argument("--verbose", action="store_true", help="Exibe JQL e contagens por área.")
    args = parser.parse_args()

    _load_jira_env(args.env_file)
    creds = _load_jira_credentials()
    if not _validate_jira_credentials(creds):
        print("Erro: JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN devem ser configurados no ambiente.")
        return 1

    month = _parse_month(args.month)
    client = JiraClient(base_url=creds["base_url"], email=creds["email"], api_token=creds["api_token"])
    try:
        client.get_myself()
    except Exception as exc:
        print(f"Erro de autenticação Jira: {exc}")
        print("Verifique JIRA_EMAIL, JIRA_API_TOKEN e se o token tem acesso ao Jira Cloud.")
        return 1

    extractor = FourPsKanbanExtractor(client, month=month, debug=args.verbose)
    kanban_data = extractor.fetch_all_kanban()
    board_config = _build_board_config_map()

    rows: List[Dict[str, Any]] = []
    board_config = _build_board_config_map()

    for area_name, area_data in kanban_data.items():
        board_info = board_config.get(area_name, {})
        print(
            f"[four_ps_kanban_export] {area_name}: in_progress={len(area_data.get('in_progress', []))}, "
            f"next_steps={len(area_data.get('next_steps', []))}, blocked={len(area_data.get('blocked', []))}"
        )
        for bucket in ["in_progress", "next_steps", "blocked"]:
            for item in area_data.get(bucket, []):
                rows.append(_item_row(area_name, bucket, item, board_info))

    # --- Itens concluídos (Entregas Realizadas) ---
    history_months = max(1, args.history_months)
    date_start, date_end = _history_date_range(month, history_months)
    print(
        f"[four_ps_kanban_export] Buscando itens concluídos de {date_start} a {date_end} "
        f"({history_months} meses) ..."
    )

    done_kanban = extractor.fetch_done_kanban(date_start, date_end)
    for area_name, area_data in done_kanban.items():
        board_info = board_config.get(area_name, {})
        done_items = area_data.get("done", [])
        print(f"[four_ps_kanban_export] {area_name}: done(kanban)={len(done_items)}")
        for item in done_items:
            rows.append(_item_row(area_name, "done", item, board_info))

    done_operational = extractor.fetch_done_operational(date_start, date_end)
    for area_name, area_data in done_operational.items():
        done_items = area_data.get("done", [])
        print(f"[four_ps_kanban_export] {area_name}: done(operational)={len(done_items)}")
        for item in done_items:
            rows.append(_item_row(area_name, "done", item, {}))

    output_path = Path(args.out)
    final_path = _write_csv(output_path, rows)
    print(f"CSV exportado: {final_path} ({len(rows)} linhas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
