"""Builder do módulo 4Ps — monta o payload estruturado para renderização.

Responsabilidades:
  - Recebe df_portfolio_full_scope (épicos + features + stories do portfólio BT/NS)
    já carregado pelo callback do portfólio — sem nova chamada Jira.
  - Recebe operational_data e kanban_data vindos de FourPsKanbanExtractor.
  - Classifica épicos em Running/Planning/Paused reutilizando as funções existentes.
  - Monta hierarquia épico → feature → story por área de produto.
  - Detecta itens BAU (sem vínculo a épico) e sugere épico por token overlap.
  - Retorna payload final tipado para o renderer.

Sem dependências circulares: não importa nada de dashboard_full.py diretamente.
As funções de portfólio são importadas via dashboards.portfolio (que faz re-export).
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore


# ---------------------------------------------------------------------------
# Tipos de saída
# ---------------------------------------------------------------------------

# Um item normalizado (épico, feature, story ou kanban task)
ItemDict = Dict[str, Any]

# Estrutura por área dentro de uma seção (progresso / próximos passos)
AreaData = Dict[str, Any]
# {
#   "epics":    [ItemDict],          # épicos e seu % de progresso
#   "features": [ItemDict],          # features vinculadas a épicos
#   "stories":  [ItemDict],          # stories vinculadas
#   "bau":      [ItemDict],          # itens sem vínculo com sugestão opcional
#   "blocked":  [ItemDict],          # candidatos a Pontos de Atenção
# }

# Payload completo
FourPsPayload = Dict[str, Dict[str, AreaData]]
# {
#   "progresso":       {area_name: AreaData},
#   "proximos_passos": {area_name: AreaData},
#   "pontos_atencao":  {area_name: [ItemDict]},  # lista plana de candidatos
# }


# ---------------------------------------------------------------------------
# Funções de portfólio e normalização — sem dependências circulares
# ---------------------------------------------------------------------------

from shared.text_utils import normalize_text as _normalize_text
from dashboards.domain.portfolio.status import (
    portfolio_roadmap_status_label as _roadmap_status_label,
    portfolio_roadmap_progress_pct as _roadmap_progress_pct,
    portfolio_team_to_project_key as _team_to_project_key,
)

_KEY_TO_LABEL: dict[str, str] = {
    "W1NNER": "W1nner",
    "S1NC": "S1NC",
    "BF": "BeFinance",
    "DT": "Dados",
}


def _portfolio_status_label(status: str, cat: str = "") -> Optional[str]:
    return _roadmap_status_label(status, cat)


def _portfolio_progress_pct(status: str, cat: str = "") -> Optional[int]:
    return _roadmap_progress_pct(status, cat)


def _team_to_area(team_value: str) -> str:
    """Mapeia valor de Team do portfólio para o nome canônico de área."""
    key = _team_to_project_key(team_value)
    if key and key in _KEY_TO_LABEL:
        return _KEY_TO_LABEL[key]

    norm = _normalize_text(team_value)
    if "w1nner" in norm or "w1nnr" in norm:
        return "W1nner"
    if "s1nc" in norm or "sinc" in norm:
        return "S1NC"
    if "befinance" in norm or " bf " in f" {norm} ":
        return "BeFinance"
    if "dados" in norm or " dt " in f" {norm} " or "data" in norm or "analytics" in norm:
        return "Dados"
    return team_value


# ---------------------------------------------------------------------------
# Sugestão de épico para itens BAU
# ---------------------------------------------------------------------------

def _tokenize(text: str, stop_words: Set[str]) -> Set[str]:
    tokens = set(_normalize_text(text).split())
    return tokens - stop_words - {""}


_DEFAULT_STOP_WORDS: Set[str] = {
    "de", "da", "do", "das", "dos", "e", "em", "o", "a", "os", "as",
    "para", "com", "por", "no", "na", "nos", "nas", "um", "uma",
}


def suggest_epic_for_bau(
    bau_title: str,
    active_epics: List[ItemDict],
    min_tokens: int = 2,
    stop_words: Optional[Set[str]] = None,
) -> Optional[str]:
    """Retorna a chave do épico com maior sobreposição de tokens com bau_title.

    Retorna None se nenhum épico atingir min_tokens tokens em comum.
    """
    stops = stop_words if stop_words is not None else _DEFAULT_STOP_WORDS
    bau_tokens = _tokenize(bau_title, stops)
    if not bau_tokens:
        return None

    best_key: Optional[str] = None
    best_count = 0

    for epic in active_epics:
        epic_title = str(epic.get("title") or epic.get("Titulo") or "")
        epic_tokens = _tokenize(epic_title, stops)
        overlap = len(bau_tokens & epic_tokens)
        if overlap >= min_tokens and overlap > best_count:
            best_count = overlap
            best_key = str(epic.get("key") or epic.get("ID") or "")

    return best_key if best_key else None


# ---------------------------------------------------------------------------
# Processamento do portfólio (épicos + features + stories)
# ---------------------------------------------------------------------------

_EPIC_TYPES = {"epico", "epic"}
_FEATURE_TYPES = {"feature", "funcionalidade"}
_STORY_TYPES = {"story", "user story", "historia", "historias", "us", "task", "bug", "support", "tech", "sub-task"}
_PRODUCT_AREAS = {"W1nner", "S1NC", "BeFinance", "Dados"}

# Tipos permitidos nas Entregas Realizadas (resumo mensal)
# Apenas entregas de valor: épicos, features e histórias/user stories.
# AD HOC é equivalente a história no board DAN.
# Tarefa, Support, Tech, Bug, Sub-task etc. são excluídos.
_DELIVERY_TYPES: set = {"epic", "epico", "feature", "funcionalidade",
                        "story", "user story", "historia", "historias", "us",
                        "ad hoc", "ad-hoc"}


def _norm_type(tipo: str) -> str:
    return _normalize_text(str(tipo or ""))


def _is_in_progress_status(status: str) -> bool:
    """Para épicos: usa semântica do portfólio (status como '40%', 'Running').
    Para features/stories: usar _is_op_in_progress."""
    label = _portfolio_status_label(status) or ""
    return label == "Running"


def _is_planning_status(status: str) -> bool:
    label = _portfolio_status_label(status) or ""
    return label == "Planning"


def _is_paused_status(status: str) -> bool:
    label = _portfolio_status_label(status) or ""
    return label == "Paused"


# Statuses operacionais (features e stories) — comparação direta normalizada
_IN_PROGRESS_NORMS: set = set()
_NEXT_STEPS_NORMS: set = set()
_DONE_NORMS: set = set()


def _ensure_op_status_sets() -> None:
    """Carrega statuses do YAML na primeira chamada."""
    global _IN_PROGRESS_NORMS, _NEXT_STEPS_NORMS, _DONE_NORMS
    if _IN_PROGRESS_NORMS:
        return
    try:
        from jira.four_ps_kanban import load_four_ps_config
        cfg = load_four_ps_config()
        _IN_PROGRESS_NORMS = {
            _normalize_text(s) for s in (cfg.get("in_progress_statuses") or [])
        }
        _NEXT_STEPS_NORMS = {
            _normalize_text(s) for s in (cfg.get("next_steps_statuses") or [])
        }
        _DONE_NORMS = {
            _normalize_text(s) for s in (cfg.get("done_statuses") or [])
        }
    except Exception:
        # fallback com os termos mais comuns
        _IN_PROGRESS_NORMS = {
            "in progress", "em andamento", "desenvolvimento", "code review",
            "ready to code review", "ready for code review", "in review",
            "ready for testing", "testing", "qa", "homologacao", "homologação",
        }
        _NEXT_STEPS_NORMS = {
            "to do", "a fazer", "backlog", "selected for development",
            "refinamento", "ready to start", "pronto para iniciar",
        }
        _DONE_NORMS = {
            "done", "closed", "concluido", "concluído", "resolved", "released",
        }


def _is_op_in_progress(status: str) -> bool:
    """Verifica se um status operacional (feature/story) indica trabalho em andamento."""
    _ensure_op_status_sets()
    return _normalize_text(status) in _IN_PROGRESS_NORMS


def _is_op_next_steps(status: str) -> bool:
    """Verifica se um status operacional indica item planejado/fila."""
    _ensure_op_status_sets()
    return _normalize_text(status) in _NEXT_STEPS_NORMS


def _is_op_done(status: str) -> bool:
    """Verifica se um status operacional indica item concluído."""
    _ensure_op_status_sets()
    return _normalize_text(status) in _DONE_NORMS


def _is_done_this_month(status: str, status_changed_at: str, ref_month: date) -> bool:
    """Retorna True se o item está concluído E a mudança de status ocorreu no mês de referência."""
    if not _is_op_done(status):
        return False
    if not status_changed_at:
        return False
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(status_changed_at)[:10]).date()
        return dt.year == ref_month.year and dt.month == ref_month.month
    except Exception:
        return False


def _is_epic_done_this_month(roadmap_status: str, status_changed_at: str, ref_month: date) -> bool:
    """Versão para épicos: usa o rótulo canônico (Done) em vez dos statuses operacionais."""
    if roadmap_status != "Done":
        return False
    if not status_changed_at:
        return False
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(status_changed_at)[:10]).date()
        return dt.year == ref_month.year and dt.month == ref_month.month
    except Exception:
        return False


def _epic_row_to_item(row: Any) -> ItemDict:
    """Converte uma linha do DataFrame de portfólio num ItemDict de épico."""
    status = str(row.get("Status") or "")
    status_cat = str(row.get("StatusCategoria") or "")
    pct = _portfolio_progress_pct(status, status_cat)
    return {
        "key":              str(row.get("ID") or ""),
        "title":            str(row.get("Titulo") or "Sem título"),
        "status":           status,
        "roadmap_status":   _portfolio_status_label(status, status_cat) or "Planning",
        "progress_pct":     pct,
        "due_date":         str(row.get("DueDate") or ""),
        "priority":         str(row.get("Prioridade") or ""),
        "team":             str(row.get("TeamDisplay") or row.get("Team") or ""),
        "link":             str(row.get("Link") or ""),
        "issue_type":       "Epic",
        "is_bau":           False,
        "status_changed_at": str(row.get("StatusChangedAt") or ""),
        "done_this_month":  False,  # preenchido no builder
    }


def _feature_row_to_item(row: Any, epic_key: str = "") -> ItemDict:
    status = str(row.get("Status") or "")
    return {
        "key":              str(row.get("ID") or ""),
        "title":            str(row.get("Titulo") or "Sem título"),
        "status":           status,
        "due_date":         str(row.get("DueDate") or ""),
        "priority":         str(row.get("Prioridade") or ""),
        "epic_key":         epic_key,
        "is_bau":           not bool(epic_key),
        "issue_type":       "Feature",
        "link":             str(row.get("Link") or ""),
        "team":             str(row.get("TeamDisplay") or row.get("Team") or ""),
        "status_changed_at": str(row.get("StatusChangedAt") or ""),
        "done_this_month":  False,
    }


def _story_row_to_item(row: Any, epic_key: str = "", feature_key: str = "") -> ItemDict:
    status = str(row.get("Status") or "")
    return {
        "key":              str(row.get("ID") or ""),
        "title":            str(row.get("Titulo") or "Sem título"),
        "status":           status,
        "due_date":         str(row.get("DueDate") or ""),
        "priority":         str(row.get("Prioridade") or ""),
        "epic_key":         epic_key,
        "feature_key":      feature_key,
        "is_bau":           not bool(epic_key),
        "issue_type":       str(row.get("Tipo") or "Story"),
        "link":             str(row.get("Link") or ""),
        "team":             str(row.get("TeamDisplay") or row.get("Team") or ""),
        "status_changed_at": str(row.get("StatusChangedAt") or ""),
        "done_this_month":  False,
    }


def _next_period_bounds(ref_month: date, period_months: int) -> Tuple[date, date]:
    """Retorna (primeiro_dia, último_dia) do próximo período de period_months meses."""
    # Avança period_months meses a partir do ref_month
    start_month = ref_month.month + period_months
    start_year = ref_month.year + (start_month - 1) // 12
    start_month = (start_month - 1) % 12 + 1
    first = date(start_year, start_month, 1)
    # Avança mais period_months meses para achar o fim
    end_month = first.month + period_months
    end_year = first.year + (end_month - 1) // 12
    end_month = (end_month - 1) % 12 + 1
    last = date(end_year, end_month, 1) - timedelta(days=1)
    return first, last


def _has_due_in_next_period(due_date_str: str, ref_month: date, period_months: int = 1) -> bool:
    """Verifica se o DueDate cai no próximo período (1 mês, trimestre etc.)."""
    if not due_date_str:
        return False
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(due_date_str)[:10]).date()
        first, last = _next_period_bounds(ref_month, period_months)
        return first <= dt <= last
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Builder principal
# ---------------------------------------------------------------------------

def build_portfolio_4ps(
    df_portfolio: Any,   # pd.DataFrame — df_portfolio_full_scope
    month: Optional[date] = None,
    min_bau_tokens: int = 2,
    period_months: int = 1,
) -> FourPsPayload:
    """Monta o payload 4Ps a partir do DataFrame de portfólio.

    Args:
        df_portfolio: df_portfolio_full_scope já carregado pelo callback.
        month: mês de referência (para filtrar próximos passos). Default = hoje.
        min_bau_tokens: mínimo de tokens em comum para sugerir épico a item BAU.

    Returns:
        FourPsPayload estruturado por área e seção.
    """
    ref_month = month or date.today().replace(day=1)

    if pd is None or df_portfolio is None or df_portfolio.empty:
        return {"progresso": {}, "proximos_passos": {}, "pontos_atencao": {}}

    df = df_portfolio.copy()

    # Garante colunas obrigatórias
    for col in ["Tipo", "Status", "ParentID", "EpicLinkID", "FeatureLinkID", "ID", "Titulo"]:
        if col not in df.columns:
            df[col] = ""

    df["_tipo_norm"] = df["Tipo"].fillna("").astype(str).map(_norm_type)
    df["ParentID"] = df["ParentID"].fillna("").astype(str)
    df["EpicLinkID"] = df["EpicLinkID"].fillna("").astype(str)
    df["FeatureLinkID"] = df["FeatureLinkID"].fillna("").astype(str)

    # Resolve área por Team
    team_col = "TeamDisplay" if "TeamDisplay" in df.columns else ("Team" if "Team" in df.columns else None)
    if team_col:
        df["_area"] = df[team_col].fillna("").astype(str).apply(_team_to_area)
    else:
        df["_area"] = ""

    # --- Separação por tipo ---
    epics_df    = df[df["_tipo_norm"].isin(_EPIC_TYPES)].copy()
    features_df = df[df["_tipo_norm"].isin(_FEATURE_TYPES)].copy()
    stories_df  = df[~df["_tipo_norm"].isin(_EPIC_TYPES | _FEATURE_TYPES)].copy()

    epic_ids    = set(epics_df["ID"].astype(str))
    feature_ids = set(features_df["ID"].astype(str))

    # Features com e sem épico pai
    features_df["_epic_key"] = features_df["ParentID"].where(
        features_df["ParentID"].isin(epic_ids), ""
    )
    # Fallback via EpicLinkID
    mask = features_df["_epic_key"] == ""
    features_df.loc[mask, "_epic_key"] = features_df.loc[mask, "EpicLinkID"].where(
        features_df.loc[mask, "EpicLinkID"].isin(epic_ids), ""
    )

    feature_to_epic: Dict[str, str] = dict(
        zip(features_df["ID"].astype(str), features_df["_epic_key"].astype(str))
    )

    # Stories: resolve epic_key via feature pai ou via EpicLinkID
    stories_df["_feature_key"] = stories_df["ParentID"].where(
        stories_df["ParentID"].isin(feature_ids), ""
    )
    stories_df["_epic_key"] = stories_df["_feature_key"].map(feature_to_epic).fillna("")
    # Fallback direto
    mask_s = stories_df["_epic_key"] == ""
    stories_df.loc[mask_s, "_epic_key"] = stories_df.loc[mask_s, "EpicLinkID"].where(
        stories_df.loc[mask_s, "EpicLinkID"].isin(epic_ids), ""
    )

    # --- Pré-computa épicos ativos por área (para sugestão BAU) ---
    active_epics_by_area: Dict[str, List[ItemDict]] = {}
    for _, row in epics_df.iterrows():
        area = str(row.get("_area") or "")
        if area not in _PRODUCT_AREAS:
            continue
        item = _epic_row_to_item(row)
        active_epics_by_area.setdefault(area, []).append(item)

    # --- Monta payload por área e seção ---
    progresso: Dict[str, AreaData] = {}
    proximos_passos: Dict[str, AreaData] = {}
    pontos_atencao: Dict[str, List[ItemDict]] = {}

    def _get_area_bucket(container: Dict, area: str) -> AreaData:
        return container.setdefault(area, {
            "epics": [], "features": [], "stories": [], "bau": [], "blocked": []
        })

    blocked_days = 5  # default; config é lida no kanban extractor

    # Épicos
    for _, row in epics_df.iterrows():
        area = str(row.get("_area") or "")
        if area not in _PRODUCT_AREAS:
            continue
        status = str(row.get("Status") or "")
        item = _epic_row_to_item(row)
        roadmap_status = item["roadmap_status"]
        changed_at = item["status_changed_at"]

        if _is_epic_done_this_month(roadmap_status, changed_at, ref_month):
            item["done_this_month"] = True
            _get_area_bucket(progresso, area)["epics"].append(item)
        elif _is_in_progress_status(status):
            _get_area_bucket(progresso, area)["epics"].append(item)
        elif _is_planning_status(status):
            # Próximos Passos: Planning SEM DueDate ou com DueDate no próximo período
            if not item["due_date"] or _has_due_in_next_period(item["due_date"], ref_month, period_months):
                _get_area_bucket(proximos_passos, area)["epics"].append(item)
        elif _is_paused_status(status):
            pontos_atencao.setdefault(area, []).append(item)

    # Features (usam statuses operacionais — "In Progress", "Code Review", etc.)
    for _, row in features_df.iterrows():
        area = str(row.get("_area") or "")
        if area not in _PRODUCT_AREAS:
            continue
        status = str(row.get("Status") or "")
        epic_key = str(row.get("_epic_key") or "")
        item = _feature_row_to_item(row, epic_key=epic_key)
        changed_at = item["status_changed_at"]

        if item["is_bau"]:
            item["suggested_epic"] = suggest_epic_for_bau(
                item["title"],
                active_epics_by_area.get(area, []),
                min_tokens=min_bau_tokens,
            )

        if _is_done_this_month(status, changed_at, ref_month):
            item["done_this_month"] = True
            target = _get_area_bucket(progresso, area)
            target["bau"].append(item) if item["is_bau"] else target["features"].append(item)
        elif _is_op_in_progress(status):
            target = _get_area_bucket(progresso, area)
            target["bau"].append(item) if item["is_bau"] else target["features"].append(item)
        elif _is_op_next_steps(status):
            # Próximos Passos: status de fila é suficiente (DueDate não obrigatório)
            target = _get_area_bucket(proximos_passos, area)
            target["bau"].append(item) if item["is_bau"] else target["features"].append(item)

    # Stories / tasks (usam statuses operacionais)
    for _, row in stories_df.iterrows():
        area = str(row.get("_area") or "")
        if area not in _PRODUCT_AREAS:
            continue
        status = str(row.get("Status") or "")
        epic_key = str(row.get("_epic_key") or "")
        feature_key = str(row.get("_feature_key") or "")
        item = _story_row_to_item(row, epic_key=epic_key, feature_key=feature_key)
        changed_at = item["status_changed_at"]

        if item["is_bau"]:
            item["suggested_epic"] = suggest_epic_for_bau(
                item["title"],
                active_epics_by_area.get(area, []),
                min_tokens=min_bau_tokens,
            )

        if _is_done_this_month(status, changed_at, ref_month):
            item["done_this_month"] = True
            target = _get_area_bucket(progresso, area)
            target["bau"].append(item) if item["is_bau"] else target["stories"].append(item)
        elif _is_op_in_progress(status):
            target = _get_area_bucket(progresso, area)
            target["bau"].append(item) if item["is_bau"] else target["stories"].append(item)
        elif _is_op_next_steps(status):
            # Próximos Passos: status de fila é suficiente (DueDate não obrigatório)
            target = _get_area_bucket(proximos_passos, area)
            target["bau"].append(item) if item["is_bau"] else target["stories"].append(item)

    return {
        "progresso":       progresso,
        "proximos_passos": proximos_passos,
        "pontos_atencao":  pontos_atencao,
    }


def merge_kanban_into_payload(
    payload: FourPsPayload,
    kanban_data: Dict[str, Dict[str, List[ItemDict]]],
) -> FourPsPayload:
    """Incorpora os dados Kanban (boards Geral) ao payload do portfólio.

    Os boards Kanban adicionam novas áreas (Infra Tech, Cibersegurança, etc.)
    às seções existentes. Não sobrescreve áreas de produto já presentes.
    """
    blocked_days = 5

    for area_name, area_kanban in kanban_data.items():
        in_progress = area_kanban.get("in_progress") or []
        next_steps  = area_kanban.get("next_steps") or []
        blocked     = area_kanban.get("blocked") or []

        if in_progress:
            bucket = payload["progresso"].setdefault(
                area_name, {"epics": [], "features": [], "stories": [], "bau": [], "blocked": []}
            )
            linked = [i for i in in_progress if not i.get("is_bau")]
            bau    = [i for i in in_progress if i.get("is_bau")]
            bucket["stories"].extend(linked)
            bucket["bau"].extend(bau)
            bucket["blocked"].extend(blocked)

        if next_steps:
            bucket = payload["proximos_passos"].setdefault(
                area_name, {"epics": [], "features": [], "stories": [], "bau": [], "blocked": []}
            )
            linked = [i for i in next_steps if not i.get("is_bau")]
            bau    = [i for i in next_steps if i.get("is_bau")]
            bucket["stories"].extend(linked)
            bucket["bau"].extend(bau)

        if blocked:
            payload["pontos_atencao"].setdefault(area_name, []).extend(blocked)

    return payload


def merge_operational_into_payload(
    payload: FourPsPayload,
    operational_data: Dict[str, Dict[str, List[ItemDict]]],
) -> FourPsPayload:
    """Incorpora dados operacionais (itens de produto) ao payload.

    Os itens operacionais enriquecem as áreas de produto já montadas
    pelo build_portfolio_4ps (que opera sobre épicos). Features e stories
    que não foram capturadas pelo portfólio BT/NS são adicionadas aqui.
    """
    known_keys: Set[str] = set()
    for section in ("progresso", "proximos_passos"):
        for area_data in payload[section].values():
            for bucket_items in area_data.values():
                if isinstance(bucket_items, list):
                    known_keys.update(
                        i.get("key", "") for i in bucket_items if i.get("key")
                    )

    for area_name, area_op in operational_data.items():
        in_progress = [i for i in (area_op.get("in_progress") or []) if i.get("key") not in known_keys]
        next_steps  = [i for i in (area_op.get("next_steps")  or []) if i.get("key") not in known_keys]
        blocked     = [i for i in (area_op.get("blocked")     or []) if i.get("key") not in known_keys]

        if in_progress:
            bucket = payload["progresso"].setdefault(
                area_name, {"epics": [], "features": [], "stories": [], "bau": [], "blocked": []}
            )
            for item in in_progress:
                (bucket["bau"] if item.get("is_bau") else bucket["stories"]).append(item)
            bucket["blocked"].extend(blocked)
            known_keys.update(i.get("key", "") for i in in_progress)

        if next_steps:
            bucket = payload["proximos_passos"].setdefault(
                area_name, {"epics": [], "features": [], "stories": [], "bau": [], "blocked": []}
            )
            for item in next_steps:
                (bucket["bau"] if item.get("is_bau") else bucket["stories"]).append(item)
            known_keys.update(i.get("key", "") for i in next_steps)

        if blocked:
            payload["pontos_atencao"].setdefault(area_name, []).extend(blocked)

    return payload


def build_monthly_summary(
    df_portfolio: Any,
    n_months: int = 6,
    date_start: Optional[date] = None,
    date_end: Optional[date] = None,
    payload: Optional["FourPsPayload"] = None,
    kanban_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Monta resumo mensal do avanço do portfólio usando StatusChangedAt.

    Combina três fontes:
      1. df_portfolio — épicos e features do portfólio estratégico (BT/NS)
      2. payload["progresso"] — itens com done_this_month=True (mês atual apenas)
      3. kanban_data — bucket "done" do CSV exportado (todos os boards + operacional,
         cobrindo histórias/AD HOC concluídos em qualquer mês do período)

    Quando date_start/date_end são fornecidos, restringe os meses ao período.

    Returns:
        {
          "months": ["2025-11", "2025-12", ...],
          "areas":  ["W1nner", "S1NC", ...],
          "done_items": {month: {area: [{key, title, type, link}]}},
          "done":       {month: {area: {epics, features, stories}}},
        }
    """
    empty: Dict[str, Any] = {"months": [], "areas": [], "done_items": {}, "done": {}}
    has_df = pd is not None and df_portfolio is not None and not (
        hasattr(df_portfolio, "empty") and df_portfolio.empty
    )
    has_payload = bool(payload and payload.get("progresso"))
    has_kanban = bool(kanban_data)
    if not has_df and not has_payload and not has_kanban:
        return empty

    _ensure_op_status_sets()

    # --- Gera lista de meses ---
    if date_start and date_end:
        all_months: List[str] = []
        cur = date_start.replace(day=1)
        end_month = date_end.replace(day=1)
        while cur <= end_month:
            all_months.append(cur.strftime("%Y-%m"))
            _nm = cur.month + 1
            cur = cur.replace(year=cur.year + (_nm - 1) // 12, month=(_nm - 1) % 12 + 1)
    else:
        today = date.today()
        all_months = []
        for i in range(n_months - 1, -1, -1):
            m = today.replace(day=1)
            total_months = m.month - i
            year_offset, month_num = divmod(total_months - 1, 12)
            m = m.replace(year=m.year + year_offset, month=month_num + 1)
            all_months.append(m.strftime("%Y-%m"))

    done_items_by_month: Dict[str, Dict[str, List[Dict[str, str]]]] = {m: {} for m in all_months}
    done_counts: Dict[str, Dict[str, Dict[str, int]]] = {m: {} for m in all_months}
    seen_keys: set = set()

    # --- Fonte 1: payload["progresso"] — itens com done_this_month=True ---
    # Inclui stories operacionais (W1NNR/S1NC/BF/DAN) que não estão no df_portfolio.
    if has_payload:
        today_month = date.today().strftime("%Y-%m")
        for area, area_data in (payload.get("progresso") or {}).items():  # type: ignore[union-attr]
            for bucket_key in ("epics", "features", "stories", "bau"):
                for item in (area_data.get(bucket_key) or []):
                    if not item.get("done_this_month"):
                        continue
                    key = str(item.get("key") or "")
                    if not key or key in seen_keys:
                        continue
                    # Determina o mês a partir de status_changed_at ou usa o mês atual
                    changed = str(item.get("status_changed_at") or "")
                    try:
                        from datetime import datetime as _dt
                        month_str = _dt.fromisoformat(changed[:10]).strftime("%Y-%m") if changed else today_month
                    except Exception:
                        month_str = today_month
                    if month_str not in done_items_by_month:
                        continue
                    itype = str(item.get("issue_type") or "Story")
                    # Filtra: apenas épicos, features e histórias/user stories
                    if _norm_type(itype) not in _DELIVERY_TYPES:
                        continue
                    tipo_key = "epics" if _norm_type(itype) in _EPIC_TYPES else "features" if _norm_type(itype) in _FEATURE_TYPES else "stories"
                    done_items_by_month[month_str].setdefault(area, []).append({
                        "key": key,
                        "title": str(item.get("title") or ""),
                        "type": itype,
                        "link": str(item.get("link") or ""),
                    })
                    done_counts[month_str].setdefault(area, {"epics": 0, "features": 0, "stories": 0})[tipo_key] += 1
                    seen_keys.add(key)

    # --- Fonte 2: df_portfolio — épicos e features estratégicos (BT/NS) ---
    if has_df:
        df = df_portfolio.copy()
        for col in ["Tipo", "Status", "StatusChangedAt", "ID", "Titulo"]:
            if col not in df.columns:
                df[col] = ""

        team_col = "TeamDisplay" if "TeamDisplay" in df.columns else ("Team" if "Team" in df.columns else None)
        if team_col:
            df["_area"] = df[team_col].fillna("").astype(str).apply(_team_to_area)
        else:
            df["_area"] = ""

        df["_tipo_norm"] = df["Tipo"].fillna("").astype(str).map(_norm_type)

        try:
            df["_changed_dt"] = pd.to_datetime(df["StatusChangedAt"], errors="coerce", utc=True)
        except Exception:
            df["_changed_dt"] = pd.NaT

        df["_month_str"] = df["_changed_dt"].dt.strftime("%Y-%m")

        for _, row in df.iterrows():
            area = str(row.get("_area") or "")
            if area not in _PRODUCT_AREAS:
                continue
            key = str(row.get("ID") or "")
            if not key or key in seen_keys:
                continue
            month_str = str(row.get("_month_str") or "")
            if month_str not in done_items_by_month:
                continue

            tipo = str(row.get("_tipo_norm") or "")
            status = str(row.get("Status") or "")
            status_cat = str(row.get("StatusCategoria") or "")
            title = str(row.get("Titulo") or "")
            link = str(row.get("Link") or "")

            if tipo in _EPIC_TYPES:
                tipo_label = "Epic"
                tipo_key = "epics"
                is_done = (_portfolio_status_label(status, status_cat) or "") == "Done"
            elif tipo in _FEATURE_TYPES:
                tipo_label = "Feature"
                tipo_key = "features"
                is_done = _is_op_done(status)
            elif tipo in _DELIVERY_TYPES:
                # Apenas Story / User Story — exclui Tarefa, Support, Tech, Bug, etc.
                tipo_label = str(row.get("Tipo") or "Story")
                tipo_key = "stories"
                is_done = _is_op_done(status)
            else:
                # Tipo não listável (Tarefa, Support, Tech, Bug, Sub-task …)
                continue

            if is_done:
                done_items_by_month[month_str].setdefault(area, []).append({
                    "key": key,
                    "title": title,
                    "type": tipo_label,
                    "link": link,
                })
                done_counts[month_str].setdefault(area, {"epics": 0, "features": 0, "stories": 0})[tipo_key] += 1
                seen_keys.add(key)

    # --- Fonte 3: kanban_data["done"] — boards Kanban + operacional (CSV exportado) ---
    # Cobre histórias/AD HOC de todos os quadros para qualquer mês do período,
    # incluindo boards Infra, DevOps, Cross, DAN (AD HOC), etc.
    if kanban_data:
        for raw_area, area_buckets in kanban_data.items():
            # Normaliza nomes de times operacionais (ex: "TECH W1NNER" → "W1nner")
            area = _team_to_area(str(raw_area or ""))
            done_list = area_buckets.get("done") if isinstance(area_buckets, dict) else []
            for item in (done_list or []):
                key = str(item.get("key") or "")
                if not key or key in seen_keys:
                    continue
                # Prefere status_changed_at, fallback para updated
                changed = str(item.get("status_changed_at") or item.get("updated") or "")
                try:
                    from datetime import datetime as _dt
                    month_str = _dt.fromisoformat(changed[:10]).strftime("%Y-%m") if changed else ""
                except Exception:
                    month_str = ""
                if not month_str or month_str not in done_items_by_month:
                    continue
                itype = str(item.get("issue_type") or "Story")
                # Filtra: apenas épicos, features e histórias/user stories (não Tarefa, Support, Tech, etc.)
                if _norm_type(itype) not in _DELIVERY_TYPES:
                    continue
                tipo_key = "epics" if _norm_type(itype) in _EPIC_TYPES else "features" if _norm_type(itype) in _FEATURE_TYPES else "stories"
                done_items_by_month[month_str].setdefault(area, []).append({
                    "key": key,
                    "title": str(item.get("title") or ""),
                    "type": itype,
                    "link": str(item.get("link") or ""),
                })
                done_counts[month_str].setdefault(area, {"epics": 0, "features": 0, "stories": 0})[tipo_key] += 1
                seen_keys.add(key)

    # Coleta áreas presentes nos resultados
    areas_present: List[str] = sorted({
        area
        for month_data in done_items_by_month.values()
        for area in month_data
    })

    return {
        "months": all_months,
        "areas": areas_present,
        "done_items": done_items_by_month,
        "done": done_counts,
    }


def _safe_date_str(val: Any) -> str:
    """Converte valor de data (str, datetime, NaT) para YYYY-MM-DD ou ''."""
    if val is None:
        return ""
    s = str(val)
    if s in ("NaT", "nat", "nan", "None", ""):
        return ""
    return s[:10]


def compute_four_ps_kpis(
    payload: FourPsPayload,
    summary: Dict[str, Any],
    df_portfolio: Any = None,
    kanban_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Computa os 8 KPIs para a faixa de resumo da página 4Ps.

    Returns dict com chaves:
        wip_total, pipeline_total, blocked_total, deliveries_period,
        bau_count, bau_pct, epics_no_date, epics_avg_pct,
        on_time_pct, on_time_count, on_time_denominator
    """
    # --- WIP, BAU, épicos running ---
    wip_total = 0
    bau_count = 0
    epics_running: List[ItemDict] = []

    for area_data in (payload.get("progresso") or {}).values():
        for bucket_key in ("epics", "features", "stories", "bau"):
            items = area_data.get(bucket_key) or []
            wip_total += len(items)
            if bucket_key == "bau":
                bau_count += len(items)
            if bucket_key == "epics":
                epics_running.extend(items)

    bau_pct = round(bau_count / wip_total * 100) if wip_total > 0 else 0

    # --- Pipeline ---
    pipeline_total = 0
    for area_data in (payload.get("proximos_passos") or {}).values():
        for bucket_key in ("epics", "features", "stories", "bau"):
            pipeline_total += len(area_data.get(bucket_key) or [])

    # --- Bloqueados ---
    blocked_total = sum(
        len(items)
        for items in (payload.get("pontos_atencao") or {}).values()
    )

    # --- Entregas no período (via summary já calculado) ---
    deliveries_period = sum(
        len(items)
        for month_data in (summary.get("done_items") or {}).values()
        for items in month_data.values()
    )

    # --- Épicos sem data de entrega (Running com due_date vazio) ---
    epics_no_date = sum(1 for e in epics_running if not e.get("due_date"))

    # --- Progresso médio dos épicos Running ---
    pcts = [
        e["progress_pct"]
        for e in epics_running
        if e.get("progress_pct") is not None
    ]
    epics_avg_pct: Optional[int] = round(sum(pcts) / len(pcts)) if pcts else None

    # --- Taxa de entrega no prazo ---
    # Denominador: itens done com due_date preenchido no período selecionado.
    # Fontes: df_portfolio (épicos/features BT/NS) + kanban_data["done"].
    period_months: set = set(summary.get("months") or [])

    def _in_period(date_str: str) -> bool:
        if not period_months:
            return True
        return date_str[:7] in period_months if len(date_str) >= 7 else False

    def _check_on_time(due: str, changed: str) -> Optional[bool]:
        """None = sem dados. True = no prazo. False = atrasado."""
        if not due or not changed:
            return None
        try:
            from datetime import datetime as _dt
            return _dt.fromisoformat(changed).date() <= _dt.fromisoformat(due).date()
        except Exception:
            return None

    on_time_ok = 0
    on_time_total = 0

    # Fonte 1: df_portfolio
    if pd is not None and df_portfolio is not None and not getattr(df_portfolio, "empty", True):
        _ensure_op_status_sets()
        df = df_portfolio.copy()
        for col in ["Tipo", "Status", "StatusCategoria", "StatusChangedAt", "DueDate"]:
            if col not in df.columns:
                df[col] = ""
        df["_tipo_norm"] = df["Tipo"].fillna("").astype(str).map(_norm_type)

        for _, row in df.iterrows():
            tipo = str(row.get("_tipo_norm") or "")
            status = str(row.get("Status") or "")
            status_cat = str(row.get("StatusCategoria") or "")
            changed = _safe_date_str(row.get("StatusChangedAt"))
            due = _safe_date_str(row.get("DueDate"))

            if not changed or not _in_period(changed):
                continue

            if tipo in _EPIC_TYPES:
                is_done = (_portfolio_status_label(status, status_cat) or "") == "Done"
            elif tipo in (_FEATURE_TYPES | _STORY_TYPES | _DELIVERY_TYPES):
                is_done = _is_op_done(status)
            else:
                continue

            if not is_done:
                continue

            result = _check_on_time(due, changed)
            if result is None:
                continue

            on_time_total += 1
            if result:
                on_time_ok += 1

    # Fonte 2: kanban_data["done"]
    if kanban_data:
        for area_buckets in kanban_data.values():
            if not isinstance(area_buckets, dict):
                continue
            for item in (area_buckets.get("done") or []):
                changed = _safe_date_str(item.get("status_changed_at"))
                due = _safe_date_str(item.get("due_date"))

                if not changed or not _in_period(changed):
                    continue

                result = _check_on_time(due, changed)
                if result is None:
                    continue

                on_time_total += 1
                if result:
                    on_time_ok += 1

    on_time_pct: Optional[int] = (
        round(on_time_ok / on_time_total * 100) if on_time_total > 0 else None
    )

    return {
        "wip_total":          wip_total,
        "pipeline_total":     pipeline_total,
        "blocked_total":      blocked_total,
        "deliveries_period":  deliveries_period,
        "bau_count":          bau_count,
        "bau_pct":            bau_pct,
        "epics_no_date":      epics_no_date,
        "epics_avg_pct":      epics_avg_pct,
        "on_time_pct":        on_time_pct,
        "on_time_count":      on_time_ok,
        "on_time_denominator": on_time_total,
    }


def build_four_ps_payload(
    df_portfolio: Any,
    kanban_data: Optional[Dict[str, Dict[str, List[ItemDict]]]] = None,
    operational_data: Optional[Dict[str, Dict[str, List[ItemDict]]]] = None,
    month: Optional[date] = None,
    period_months: int = 1,
) -> FourPsPayload:
    """Ponto de entrada principal do builder.

    Orquestra:
      1. build_portfolio_4ps — portfólio estratégico (épicos/features/stories BT/NS)
      2. merge_operational_into_payload — itens operacionais de produto
      3. merge_kanban_into_payload — boards Kanban (Geral)
    """
    payload = build_portfolio_4ps(df_portfolio, month=month, period_months=period_months)

    if operational_data:
        payload = merge_operational_into_payload(payload, operational_data)

    if kanban_data:
        payload = merge_kanban_into_payload(payload, kanban_data)

    return payload
