"""Extração Jira para o módulo 4Ps — Boards Kanban e nível operacional.

Responsabilidades:
  - Carregar four_ps_config.yaml
  - Descobrir o mapeamento UUID → nome de área via API (com cache em memória)
  - Buscar itens dos boards Kanban (IT/IC/AT/CROS/CT/EA) por status
  - Buscar itens operacionais de produto (W1NNR/S1NC/BF/BT) por status + período
  - Detectar itens BAU nos boards Kanban (sem Epic Link)
  - Identificar candidatos a Pontos de Atenção (bloqueados/sem movimento > N dias)

Uso típico (chamado por dashboards/four_ps/builder.py):
    from jira.four_ps_kanban import FourPsKanbanExtractor
    extractor = FourPsKanbanExtractor(client)
    kanban_data = extractor.fetch_all_kanban(month=date(2026, 4, 1))
    operational_data = extractor.fetch_operational(month=date(2026, 4, 1))
"""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from jira.client import JiraClient

# ---------------------------------------------------------------------------
# Carregamento de configuração
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent.parent / "four_ps_config.yaml"
_config_cache: Optional[Dict[str, Any]] = None


def load_four_ps_config() -> Dict[str, Any]:
    """Carrega four_ps_config.yaml com cache em memória."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if yaml is None:
        raise ImportError(
            "PyYAML não instalado. Execute: pip install pyyaml"
        )
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as fh:
            _config_cache = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        _config_cache = {}
    return _config_cache


# ---------------------------------------------------------------------------
# Descoberta de UUID → nome de área (com cache em memória de processo)
# ---------------------------------------------------------------------------

_uuid_name_cache: Dict[str, str] = {}


def discover_team_uuid_map(client: JiraClient) -> Dict[str, str]:
    """Resolve UUID → nome de área buscando uma amostra de itens operacionais.

    Lê o campo 'team' de até 50 itens da JQL operacional e extrai os
    displayNames dos times. Cacheia o resultado em memória de processo.

    Fallback: se a API não retornar nomes, usa os fallback_names do YAML.
    """
    global _uuid_name_cache
    if _uuid_name_cache:
        return dict(_uuid_name_cache)

    cfg = load_four_ps_config()
    uuid_entries: List[Dict[str, str]] = (
        (cfg.get("operational") or {}).get("team_uuids") or []
    )
    # Mapa de fallback a partir do YAML
    fallback_map: Dict[str, str] = {
        entry["uuid"]: entry["fallback_name"]
        for entry in uuid_entries
        if entry.get("uuid") and entry.get("fallback_name")
    }

    # Descobre o field ID do campo team[team]
    team_field_id = _discover_team_field_id(client)

    if team_field_id:
        uuids = list(fallback_map.keys())
        uuid_list = ", ".join(f'"{u}"' for u in uuids)
        jql = (
            f'project IN ({", ".join(_operational_projects(cfg))}) '
            f'AND "team[team]" IN ({uuid_list}) '
            f'ORDER BY created DESC'
        )
        try:
            issues = client.search_issues(
                jql=jql,
                fields=["summary", team_field_id],
                page_size=50,
            )
            for issue in issues:
                fields = issue.get("fields") or {}
                team_val = fields.get(team_field_id)
                if not isinstance(team_val, dict):
                    continue
                team_id = str(team_val.get("id") or "").strip()
                team_name = str(
                    team_val.get("name") or team_val.get("title") or ""
                ).strip()
                if team_id and team_name and team_id in fallback_map:
                    fallback_map[team_id] = team_name
        except Exception as exc:
            print(f"[four_ps_kanban] Aviso: não foi possível descobrir nomes de times via API: {exc}")

    _uuid_name_cache = fallback_map
    return dict(_uuid_name_cache)


def _discover_team_field_id(client: JiraClient) -> str:
    """Descobre o field ID do campo team[team] usando a API de campos."""
    try:
        fields = client._get("/rest/api/3/field")
        if not isinstance(fields, list):
            return ""
        for f in fields:
            name = str((f or {}).get("name") or "").strip().lower()
            schema = (f or {}).get("schema") or {}
            schema_custom = str(schema.get("custom") or "").strip().lower()
            fid = str((f or {}).get("id") or "").strip()
            if not fid:
                continue
            if "team" in name and "team" in schema_custom:
                return fid
            if schema_custom in {"com.atlassian.teams:rm-teams-custom-field-team", "team"}:
                return fid
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Helpers de configuração
# ---------------------------------------------------------------------------

def _operational_projects(cfg: Dict[str, Any]) -> List[str]:
    return (cfg.get("operational") or {}).get("projects") or ["W1NNR", "S1NC", "BF", "BT"]


def _operational_issue_types(cfg: Dict[str, Any]) -> List[str]:
    return (cfg.get("operational") or {}).get("issue_types") or [
        "Bug", "Story", "Support", "Tech", "Task", "User Story", "Sub-task"
    ]


def _operational_uuids(cfg: Dict[str, Any]) -> List[str]:
    entries = (cfg.get("operational") or {}).get("team_uuids") or []
    return [e["uuid"] for e in entries if e.get("uuid")]


def _status_list(cfg: Dict[str, Any], key: str) -> List[str]:
    return cfg.get(key) or []


def _next_month_range(month: date) -> Tuple[str, str]:
    """Retorna (primeiro_dia, último_dia) do mês seguinte no formato YYYY-MM-DD."""
    first_next = (month.replace(day=1) + timedelta(days=32)).replace(day=1)
    last_next = (first_next + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return first_next.strftime("%Y-%m-%d"), last_next.strftime("%Y-%m-%d")


def _next_period_range(month: date, period_months: int) -> Tuple[str, str]:
    """Retorna (primeiro_dia, último_dia) do próximo período de period_months meses."""
    # Avança period_months meses a partir do ref_month
    start_m = month.month + period_months
    start_y = month.year + (start_m - 1) // 12
    start_m = (start_m - 1) % 12 + 1
    first = date(start_y, start_m, 1)
    # Avança mais period_months para o fim
    end_m = first.month + period_months
    end_y = first.year + (end_m - 1) // 12
    end_m = (end_m - 1) % 12 + 1
    last = date(end_y, end_m, 1) - timedelta(days=1)
    return first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d")


def _current_month_range(month: date) -> Tuple[str, str]:
    first = month.replace(day=1)
    last = (first + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d")


def _jql_status_clause(statuses: List[str]) -> str:
    escaped = [f'"{s}"' for s in statuses]
    return f'status IN ({", ".join(escaped)})'


def _jql_types_clause(types: List[str]) -> str:
    escaped = [f'"{t}"' for t in types]
    return f'issuetype IN ({", ".join(escaped)})'


def _status_category_name_variants(category_name: str) -> List[str]:
    normalized = str(category_name or "").strip().lower()
    if normalized in {"to do", "pendências", "pendencias", "a fazer", "backlog"}:
        return ["To Do", "Pendências"]
    if normalized in {"in progress", "em andamento", "em progresso", "doing", "em desenvolvimentoo"}:
        return ["In Progress", "Em andamento", "Em progresso"]
    if normalized in {"done", "closed", "concluído", "concluido", "resolved", "released"}:
        return ["Done", "Concluído", "Concluido"]
    return [category_name]


def _jql_status_category_clause(category_name: str) -> str:
    variants = _status_category_name_variants(category_name)
    escaped = [f'"{name}"' for name in variants]
    return f'statusCategory IN ({", ".join(escaped)})'


def _split_jql_order_by(jql: str) -> Tuple[str, str]:
    match = re.search(r"(?i)\border\s+by\b", jql)
    if not match:
        return jql.strip(), ""
    return jql[:match.start()].strip(), jql[match.end():].strip()


def _build_jql(base_jql: str, clause: str, default_order_by: str = "priority DESC") -> str:
    base, order_by = _split_jql_order_by(base_jql)
    if base:
        query = f"{base} AND {clause}"
    else:
        query = clause.strip()

    if order_by:
        return f"{query} ORDER BY {order_by}"
    if default_order_by:
        return f"{query} ORDER BY {default_order_by}"
    return query


def _area_base_jql(area_cfg: Dict[str, Any], client: JiraClient) -> str:
    explicit_jql = str(area_cfg.get("jql") or "").strip()
    if explicit_jql:
        return explicit_jql

    board_id = area_cfg.get("board_id")
    if board_id:
        board_jql = _resolve_board_filter_jql(client, board_id)
        if board_jql:
            return board_jql

    project = str(area_cfg.get("project") or "").strip()
    if project:
        return f'project = {project}'

    return ""


def _resolve_board_filter_jql(client: JiraClient, board_id: Any) -> str:
    board_id_str = str(board_id or "").strip()
    if not board_id_str:
        return ""

    filter_id = ""
    try:
        board_meta = client._get(f"/rest/agile/1.0/board/{board_id_str}/filter")
        filter_id = str((board_meta or {}).get("id") or "").strip()
    except Exception as exc:
        try:
            config_meta = client._get(f"/rest/agile/1.0/board/{board_id_str}/configuration")
            filter_info = (config_meta or {}).get("filter") or {}
            filter_id = str(filter_info.get("id") or "").strip()
            if not filter_id:
                raise RuntimeError("board configuration não retornou filter.id")
        except Exception as exc2:
            print(
                f"[four_ps_kanban] Aviso: não foi possível carregar filtro do board {board_id_str}: {exc}; "
                f"fallback configuration falhou: {exc2}"
            )
            return ""

    if not filter_id:
        return ""

    try:
        filter_detail = client._get(f"/rest/api/3/filter/{filter_id}")
        return _split_jql_order_by(str((filter_detail or {}).get("jql") or ""))[0]
    except Exception as exc:
        print(
            f"[four_ps_kanban] Aviso: não foi possível carregar detalhe do filtro {filter_id} para o board {board_id_str}: {exc}"
        )
        return ""


def _board_base_jql(project: str, board_id: Any, client: JiraClient) -> str:
    # Use apenas o projeto como base da busca, pois o endpoint Agile de board
    # pode exigir permissões diferentes do token e não é necessário para JQL.
    return f'project = {project}'


# ---------------------------------------------------------------------------
# Busca genérica com paginação via JiraClient
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Campos comuns extraídos de cada issue
# ---------------------------------------------------------------------------

_KANBAN_FIELDS = [
    "summary",
    "status",
    "issuetype",
    "priority",
    "assignee",
    "duedate",
    "updated",
    "created",
    "statuscategorychangedate",
    "parent",
    "customfield_10014",   # Epic Link (campo legado)
]

_OPERATIONAL_FIELDS = [
    "summary",
    "status",
    "issuetype",
    "priority",
    "assignee",
    "duedate",
    "updated",
    "created",
    "statuscategorychangedate",
    "parent",
    "customfield_10014",   # Epic Link
    "customfield_10008",   # Epic Name (campo legado)
]


def _extract_issue(raw: Dict[str, Any], team_name: str = "") -> Dict[str, Any]:
    """Normaliza um issue Jira bruto para o formato usado pelo builder."""
    fields = raw.get("fields") or {}
    status_obj = fields.get("status") or {}
    status_category = (status_obj.get("statusCategory") or {}).get("key", "")
    issuetype = (fields.get("issuetype") or {}).get("name", "")
    priority = (fields.get("priority") or {}).get("name", "")
    assignee = (fields.get("assignee") or {}).get("displayName", "")
    parent = fields.get("parent") or {}
    parent_key = str(parent.get("key") or "").strip()
    parent_type = str(
        (parent.get("fields") or {}).get("issuetype", {}).get("name") or ""
    ).strip()

    # Epic Link: tenta campo legado customfield_10014, depois parent direto se for épico
    epic_link = str(fields.get("customfield_10014") or "").strip()
    if not epic_link and parent_type.lower() in {"epic", "epico"}:
        epic_link = parent_key

    # Dias sem alteração de status
    status_changed_raw = str(fields.get("statuscategorychangedate") or fields.get("updated") or "")
    days_stale = _days_since(status_changed_raw)
    # Data ISO (apenas YYYY-MM-DD) da última mudança de categoria de status
    status_changed_at = status_changed_raw[:10] if status_changed_raw else ""

    raw_key = str(raw.get("key") or "").strip()
    project_key = raw_key.split("-", 1)[0] if "-" in raw_key else ""
    return {
        "key": raw_key,
        "project": project_key,
        "title": str(fields.get("summary") or "").strip(),
        "status": str(status_obj.get("name") or "").strip(),
        "status_category": status_category,
        "issue_type": issuetype,
        "priority": priority,
        "assignee": assignee,
        "due_date": str(fields.get("duedate") or "").strip(),
        "updated": str(fields.get("updated") or "").strip(),
        "status_changed_at": status_changed_at,
        "parent_key": parent_key,
        "parent_type": parent_type,
        "epic_link": epic_link,
        "is_bau": not bool(epic_link),
        "days_stale": days_stale,
        "team": team_name,
        "link": f"https://w1consultoria.atlassian.net/browse/{raw_key}",
    }


def _days_since(date_str: str) -> int:
    """Retorna quantos dias se passaram desde uma data ISO 8601."""
    if not date_str:
        return 0
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0, (now - dt).days)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Extrator principal
# ---------------------------------------------------------------------------

class FourPsKanbanExtractor:
    """Extrai e classifica itens Jira para o relatório 4Ps.

    Args:
        client: instância de JiraClient já autenticada.
        month: mês de referência (usado para filtrar próximos passos pelo mês seguinte).
        debug: se True, imprime JQL e contagens por área.
    """

    def __init__(
        self,
        client: JiraClient,
        month: Optional[date] = None,
        debug: bool = False,
        period_months: int = 1,
    ) -> None:
        self.client = client
        self.month = month or date.today().replace(day=1)
        self._cfg = load_four_ps_config()
        self._uuid_map: Dict[str, str] = {}
        self._debug = debug
        self.period_months = max(1, period_months)

    def _debug_log(self, msg: str) -> None:
        if self._debug:
            print(f"[four_ps_kanban] {msg}")

    def _ensure_uuid_map(self) -> None:
        if not self._uuid_map:
            self._uuid_map = discover_team_uuid_map(self.client)

    # ------------------------------------------------------------------
    # Kanban boards (Geral)
    # ------------------------------------------------------------------

    def fetch_all_kanban(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Busca itens de todos os boards Kanban configurados.

        Retorna dict keyed por nome de área:
          {area_name: {"in_progress": [...], "next_steps": [...], "blocked": [...]}}
        """
        areas = self._cfg.get("kanban_areas") or []
        result: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for area_cfg in areas:
            area_name = area_cfg.get("name", "?")
            result[area_name] = self._fetch_kanban_area(area_cfg, area_name)
        return result

    def _fetch_kanban_area(
        self,
        area_cfg: Dict[str, Any],
        area_name: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        in_progress_statuses = _status_list(self._cfg, "in_progress_statuses")
        next_steps_statuses = _status_list(self._cfg, "next_steps_statuses")
        blocked_days = int(self._cfg.get("blocked_threshold_days") or 5)

        base_jql = _area_base_jql(area_cfg, self.client)
        if not base_jql:
            return {"in_progress": [], "next_steps": [], "blocked": []}

        in_progress_jql = _build_jql(base_jql, _jql_status_clause(in_progress_statuses), "priority DESC")
        next_steps_jql = self._next_steps_jql_kanban(base_jql, next_steps_statuses)

        explicit_jql = str(area_cfg.get("jql") or "").strip()
        board_jql = ""
        # Só resolve o filtro do board quando não há JQL explícita no YAML
        # (evita chamadas desnecessárias à API Agile que podem retornar 404/401)
        if not explicit_jql:
            if board_id := area_cfg.get("board_id"):
                board_jql = _resolve_board_filter_jql(self.client, board_id)

        self._debug_log(f"{area_name} base JQL: {base_jql}")
        self._debug_log(f"{area_name} in_progress JQL: {in_progress_jql}")
        self._debug_log(f"{area_name} next_steps JQL: {next_steps_jql}")

        in_progress = self._search(
            jql=in_progress_jql,
            fields=_KANBAN_FIELDS,
            area_name=area_name,
        )

        next_steps = self._search(
            jql=next_steps_jql,
            fields=_KANBAN_FIELDS,
            area_name=area_name,
        )

        if not in_progress and board_jql and board_jql != explicit_jql:
            board_in_progress_jql = _build_jql(board_jql, _jql_status_clause(in_progress_statuses), "priority DESC")
            fallback_in_progress = self._search(
                jql=board_in_progress_jql,
                fields=_KANBAN_FIELDS,
                area_name=area_name,
            )
            if fallback_in_progress:
                self._debug_log(
                    f"{area_name} in_progress fallback board filter JQL returned {len(fallback_in_progress)} items"
                )
                in_progress = fallback_in_progress

        if not in_progress:
            category_jql = _build_jql(base_jql, _jql_status_category_clause("In Progress"), "priority DESC")
            fallback_in_progress = self._search(
                jql=category_jql,
                fields=_KANBAN_FIELDS,
                area_name=area_name,
            )
            if fallback_in_progress:
                self._debug_log(
                    f"{area_name} in_progress fallback statusCategory=In Progress returned {len(fallback_in_progress)} items"
                )
                in_progress = fallback_in_progress

        if not next_steps and board_jql and board_jql != explicit_jql:
            board_next_steps_jql = self._next_steps_jql_kanban(board_jql, next_steps_statuses)
            board_next_steps = self._search(
                jql=board_next_steps_jql,
                fields=_KANBAN_FIELDS,
                area_name=area_name,
            )
            if board_next_steps:
                self._debug_log(
                    f"{area_name} next_steps fallback board filter JQL returned {len(board_next_steps)} items"
                )
                next_steps = board_next_steps

        if not next_steps:
            no_date_next_steps_jql = self._next_steps_jql_kanban_no_date(base_jql, next_steps_statuses)
            fallback_next_steps = self._search(
                jql=no_date_next_steps_jql,
                fields=_KANBAN_FIELDS,
                area_name=area_name,
            )
            if fallback_next_steps:
                self._debug_log(
                    f"{area_name} next_steps fallback status list without dates returned {len(fallback_next_steps)} items"
                )
                next_steps = fallback_next_steps

        if not next_steps and board_jql and board_jql != explicit_jql:
            board_no_date_next_steps_jql = self._next_steps_jql_kanban_no_date(board_jql, next_steps_statuses)
            board_next_steps = self._search(
                jql=board_no_date_next_steps_jql,
                fields=_KANBAN_FIELDS,
                area_name=area_name,
            )
            if board_next_steps:
                self._debug_log(
                    f"{area_name} next_steps fallback board filter status list without dates returned {len(board_next_steps)} items"
                )
                next_steps = board_next_steps

        if not next_steps:
            next_steps_category_jql = self._next_steps_category_jql(base_jql, "To Do")
            fallback_next_steps = self._search(
                jql=next_steps_category_jql,
                fields=_KANBAN_FIELDS,
                area_name=area_name,
            )
            if fallback_next_steps:
                self._debug_log(
                    f"{area_name} next_steps fallback statusCategory=To Do returned {len(fallback_next_steps)} items"
                )
                next_steps = fallback_next_steps

        if not next_steps and board_jql and board_jql != explicit_jql:
            board_next_steps_category_jql = self._next_steps_category_jql(board_jql, "To Do")
            board_next_steps = self._search(
                jql=board_next_steps_category_jql,
                fields=_KANBAN_FIELDS,
                area_name=area_name,
            )
            if board_next_steps:
                self._debug_log(
                    f"{area_name} next_steps fallback board filter statusCategory=To Do returned {len(board_next_steps)} items"
                )
                next_steps = board_next_steps

        if not in_progress and not next_steps:
            try:
                raw_issues = self.client.search_issues(
                    jql=base_jql,
                    fields=["status", "statuscategorychangedate"],
                )
                status_counts: Dict[str, int] = {}
                for issue in raw_issues:
                    fields = issue.get("fields") or {}
                    status_name = str((fields.get("status") or {}).get("name") or "").strip()
                    status_counts[status_name] = status_counts.get(status_name, 0) + 1
                if raw_issues:
                    self._debug_log(
                        f"{area_name} raw board issues={len(raw_issues)}; statuses={status_counts}"
                    )
            except Exception as exc:
                self._debug_log(f"{area_name} raw board inspection falhou: {exc}")

        blocked = [
            item for item in in_progress
            if item["days_stale"] >= blocked_days
        ]

        if board_id := area_cfg.get("board_id"):
            if explicit_jql and not in_progress and not next_steps and board_jql and board_jql != explicit_jql:
                self._debug_log(f"{area_name} fallback board filter JQL: {board_jql}")
                in_progress = self._search(
                    jql=_build_jql(board_jql, _jql_status_clause(in_progress_statuses), "priority DESC"),
                    fields=_KANBAN_FIELDS,
                    area_name=area_name,
                )
                next_steps = self._search(
                    jql=self._next_steps_jql_kanban(board_jql, next_steps_statuses),
                    fields=_KANBAN_FIELDS,
                    area_name=area_name,
                )
                blocked = [
                    item for item in in_progress
                    if item["days_stale"] >= blocked_days
                ]

        self._debug_log(
            f"{area_name} counts => in_progress={len(in_progress)}, next_steps={len(next_steps)}, blocked={len(blocked)}"
        )

        return {
            "in_progress": in_progress,
            "next_steps": next_steps,
            "blocked": blocked,
        }

    # ------------------------------------------------------------------
    # Itens concluídos por período (para Entregas Realizadas / resumo mensal)
    # ------------------------------------------------------------------

    def fetch_done_kanban(
        self,
        date_start: date,
        date_end: date,
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Busca itens concluídos nos boards Kanban dentro do intervalo de datas.

        Usa statuscategorychangedate para restringir ao período.
        Retorna {area_name: {"done": [items]}}.
        """
        areas = self._cfg.get("kanban_areas") or []
        result: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        done_statuses = _status_list(self._cfg, "done_statuses")
        start_str = date_start.strftime("%Y-%m-%d")
        end_str = date_end.strftime("%Y-%m-%d")
        # Usa statuses explícitos (não statusCategory) para excluir Cancelled e similares
        status_clause = _jql_status_clause(done_statuses)
        date_clause = (
            f'{status_clause} '
            f'AND statuscategorychangedate >= "{start_str}" '
            f'AND statuscategorychangedate <= "{end_str}"'
        )
        for area_cfg in areas:
            area_name = str(area_cfg.get("name") or "?")
            base_jql = _area_base_jql(area_cfg, self.client)
            if not base_jql:
                continue
            jql = _build_jql(base_jql, date_clause, "statuscategorychangedate DESC")
            items = self._search(jql=jql, fields=_KANBAN_FIELDS, area_name=area_name)
            self._debug_log(
                f"{area_name} done (kanban) => {len(items)} itens entre {start_str} e {end_str}"
            )
            if items:
                result[area_name] = {"done": items}
        return result

    def fetch_done_operational(
        self,
        date_start: date,
        date_end: date,
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Busca itens concluídos dos projetos operacionais de produto dentro do intervalo.

        Agrupa por UUID → nome de área (W1nner / S1NC / BeFinance / Dados).
        Retorna {area_name: {"done": [items]}}.
        """
        self._ensure_uuid_map()
        projects = _operational_projects(self._cfg)
        types = _operational_issue_types(self._cfg)
        uuids = _operational_uuids(self._cfg)
        if not uuids:
            return {}

        project_clause = f'project IN ({", ".join(projects)})'
        type_clause = _jql_types_clause(types)
        uuid_list = ", ".join(f'"{u}"' for u in uuids)
        team_clause = f'"team[team]" IN ({uuid_list})'
        start_str = date_start.strftime("%Y-%m-%d")
        end_str = date_end.strftime("%Y-%m-%d")
        done_statuses = _status_list(self._cfg, "done_statuses")
        # Usa statuses explícitos para excluir Cancelled e similares
        status_clause = _jql_status_clause(done_statuses)
        date_clause = (
            f'{status_clause} '
            f'AND statuscategorychangedate >= "{start_str}" '
            f'AND statuscategorychangedate <= "{end_str}"'
        )
        jql = (
            f'{project_clause} AND {type_clause} AND {team_clause} AND {date_clause} '
            f'ORDER BY statuscategorychangedate DESC'
        )

        # Inclui o campo de time dinamicamente para resolver UUID → área
        team_field_id = _discover_team_field_id(self.client)
        fields = list(_OPERATIONAL_FIELDS)
        if team_field_id and team_field_id not in fields:
            fields.append(team_field_id)

        items = self._search(jql=jql, fields=fields)
        self._debug_log(
            f"operational done => {len(items)} itens entre {start_str} e {end_str}"
        )

        result: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for item in items:
            area = item.get("team") or "Sem área"
            result.setdefault(area, {"done": []})["done"].append(item)
        return result

    def _next_steps_jql_kanban(self, base_jql: str, statuses: List[str]) -> str:
        next_start, next_end = _next_period_range(self.month, self.period_months)
        status_clause = _jql_status_clause(statuses)
        date_clause = (
            f'(duedate >= "{next_start}" AND duedate <= "{next_end}"'
            f' OR "target start[date]" >= "{next_start}")'
        )
        return _build_jql(base_jql, f"{status_clause} AND {date_clause}", "priority DESC")

    def _next_steps_jql_kanban_no_date(self, base_jql: str, statuses: List[str]) -> str:
        status_clause = _jql_status_clause(statuses)
        return _build_jql(base_jql, status_clause, "priority DESC")

    def _next_steps_category_jql(self, base_jql: str, status_category: str) -> str:
        next_start, next_end = _next_period_range(self.month, self.period_months)
        status_clause = _jql_status_category_clause(status_category)
        date_clause = (
            f'(duedate >= "{next_start}" AND duedate <= "{next_end}"'
            f' OR "target start[date]" >= "{next_start}")'
        )
        return _build_jql(base_jql, f"{status_clause} AND {date_clause}", "priority DESC")

    def _next_steps_category_jql_no_date(self, base_jql: str, status_category: str) -> str:
        status_clause = _jql_status_category_clause(status_category)
        return _build_jql(base_jql, status_clause, "priority DESC")

    # ------------------------------------------------------------------
    # Nível operacional (produto: W1nner/S1NC/BeFinance/Dados)
    # ------------------------------------------------------------------

    def fetch_operational(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Busca itens operacionais de produto agrupados por área (time UUID).

        Retorna dict keyed por nome de área:
          {area_name: {"in_progress": [...], "next_steps": [...], "blocked": [...]}}
        """
        self._ensure_uuid_map()
        projects = _operational_projects(self._cfg)
        types = _operational_issue_types(self._cfg)
        uuids = _operational_uuids(self._cfg)
        in_progress_statuses = _status_list(self._cfg, "in_progress_statuses")
        next_steps_statuses = _status_list(self._cfg, "next_steps_statuses")
        blocked_days = int(self._cfg.get("blocked_threshold_days") or 5)

        project_clause = f'project IN ({", ".join(projects)})'
        type_clause = _jql_types_clause(types)
        uuid_list = ", ".join(f'"{u}"' for u in uuids)
        team_clause = f'"team[team]" IN ({uuid_list})'
        base = f'{project_clause} AND {type_clause} AND {team_clause}'

        in_progress_issues = self._search(
            jql=f'{base} AND {_jql_status_clause(in_progress_statuses)} ORDER BY priority DESC, Rank ASC',
            fields=_OPERATIONAL_FIELDS,
        )

        next_steps_issues = self._search(
            jql=self._next_steps_jql_operational(base, next_steps_statuses),
            fields=_OPERATIONAL_FIELDS,
        )

        # Agrupa por UUID → nome de área
        result: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

        def _area_for(item: Dict[str, Any]) -> str:
            return item.get("team") or "Sem área"

        for item in in_progress_issues:
            area = _area_for(item)
            bucket = result.setdefault(area, {"in_progress": [], "next_steps": [], "blocked": []})
            bucket["in_progress"].append(item)
            if item["days_stale"] >= blocked_days:
                bucket["blocked"].append(item)

        for item in next_steps_issues:
            area = _area_for(item)
            bucket = result.setdefault(area, {"in_progress": [], "next_steps": [], "blocked": []})
            bucket["next_steps"].append(item)

        return result

    def _next_steps_jql_operational(self, base_jql: str, statuses: List[str]) -> str:
        next_start, next_end = _next_period_range(self.month, self.period_months)
        status_clause = _jql_status_clause(statuses)
        date_clause = (
            f'(duedate >= "{next_start}" AND duedate <= "{next_end}"'
            f' OR "target start[date]" >= "{next_start}")'
        )
        return f'{base_jql} AND {status_clause} AND {date_clause} ORDER BY priority DESC, Rank ASC'

    # ------------------------------------------------------------------
    # Busca genérica com paginação via JiraClient
    # ------------------------------------------------------------------

    def _search(
        self,
        jql: str,
        fields: List[str],
        area_name: str = "",
        board_id: Any = None,
    ) -> List[Dict[str, Any]]:
        """Executa JQL e normaliza resultados."""
        self._ensure_uuid_map()
        try:
            raw_issues = self.client.search_issues(jql=jql, fields=fields)
        except Exception as exc:
            print(f"[four_ps_kanban] Erro na busca '{jql[:80]}...': {exc}")
            return []

        items: List[Dict[str, Any]] = []
        team_field_id = _discover_team_field_id(self.client) if not area_name else ""

        for raw in raw_issues:
            fields_data = raw.get("fields") or {}

            # Resolve nome de área: se passado explicitamente usa; senão lê campo team
            resolved_area = area_name
            if not resolved_area and team_field_id:
                team_val = fields_data.get(team_field_id) or {}
                team_id = str(team_val.get("id") or "").strip()
                resolved_area = self._uuid_map.get(team_id, "")

            item = _extract_issue(raw, team_name=resolved_area)
            items.append(item)

        return items
