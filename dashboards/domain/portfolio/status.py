"""Funções de status e classificação de portfólio — sem dependências circulares.

Este módulo é a fonte canônica das funções de status/progresso do portfólio.
Ele não importa nada de dashboard_full, apenas de shared/.
"""
from __future__ import annotations

import re
from typing import Optional

from shared.text_utils import normalize_text


# Mapeamento canônico de chaves de portfólio (team → project key)
PORTFOLIO_CANONICAL_PROJECT_MAP: dict[str, str] = {
    "BF": "BF",
    "BEFINANCE": "BF",
    "BE FINANCE": "BF",
    "DT": "DT",
    "DA": "DT",
    "DADOS": "DT",
    "DATA ANALYTICS": "DT",
    "DATA&ANALYTICS": "DT",
    "S1NC": "S1NC",
    "W1SFT": "S1NC",
    "SYNC": "S1NC",
    "W1NNR": "W1NNER",
    "W1NNER": "W1NNER",
    "WINNER": "W1NNER",
}

# Alias map para resolução de team display → project key
_TEAM_ALIAS_MAP: dict[str, str] = {
    "TECH DATA": "DT",
    "DATA ANALYTICS": "DT",
    "DATA&ANALYTICS": "DT",
    "TECH BEFINANCE": "BF",
    "BEFINANCE": "BF",
    "BF": "BF",
    "TECH S1NC": "S1NC",
    "S1NC": "S1NC",
    "SQUAD | S1NC": "S1NC",
    "TECH W1NNER": "W1NNER",
    "W1NNER": "W1NNER",
    "W1NNR": "W1NNER",
    "SQUAD | W1NNER": "W1NNER",
}


def portfolio_roadmap_status_label(status_value: str, status_categoria_value: str = "") -> Optional[str]:
    """Converte status bruto do roadmap em label canônico (Running/Planning/Paused/Done)."""
    status_raw = str(status_value or "").strip()
    status_norm = normalize_text(status_raw)
    status_categoria_norm = normalize_text(status_categoria_value)

    if any(term in status_norm for term in ("blocked", "bloque", "suspend", "suspens", "paused", "pause")):
        return "Paused"

    if any(term in status_norm for term in ("done", "concluido", "concluida", "closed", "resolved")):
        return "Done"

    if "ready to delivery" in status_norm:
        return "Running"

    pct_match = re.search(r"(\d{1,3})\s*%", status_raw)
    if pct_match:
        try:
            pct = float(pct_match.group(1))
            if pct <= 80.0:
                return "Running"
        except Exception:
            pass

    if ("planning" in status_norm) or ("pllaning" in status_norm):
        return "Planning"

    planning_terms = (
        "triagem",
        "backlog",
        "to do",
        "todo",
        "business review",
        "ready for development",
        "ready to start",
    )
    if any(term in status_norm for term in planning_terms):
        return "Planning"

    if status_categoria_norm == "backlog":
        return "Planning"

    return None


def portfolio_roadmap_progress_pct(status_value: str, status_categoria_value: str = "") -> Optional[int]:
    """Converte status bruto em percentual de progresso (0–100)."""
    status_raw = str(status_value or "").strip()
    status_norm = normalize_text(status_raw)
    status_categoria_norm = normalize_text(status_categoria_value)

    pct_match = re.search(r"(\d{1,3})\s*%", status_raw)
    if pct_match:
        try:
            return max(0, min(100, int(float(pct_match.group(1)))))
        except Exception:
            pass

    if any(term in status_norm for term in ("blocked", "bloque", "suspend", "suspens", "paused", "pause")):
        return None

    if any(term in status_norm for term in ("done", "concluido", "concluida", "closed", "resolved")):
        return 100

    flow_pct_map = [
        (("triagem", "backlog", "to do", "todo", "planning", "pllaning", "business review"), 0),
        (("ready for development", "ready to start"), 15),
        (("in progress", "in progess", "desenvolvimento", "development", "doing"), 40),
        (("ready for code review", "code review"), 55),
        (("ready for testing", "testing", "qa", "homolog"), 70),
        (("ready for staging", "staging"), 80),
        (("ready to delivery", "ready for production", "ready for release"), 80),
    ]
    for terms, pct in flow_pct_map:
        if any(term in status_norm for term in terms):
            return int(pct)

    if status_categoria_norm == "concluido":
        return 100
    if status_categoria_norm == "backlog":
        return 0
    if status_categoria_norm == "em progresso":
        return 40

    return None


def _canonical_project_key(value: str) -> str:
    """Resolve valor de team/projeto para chave canônica (BF/DT/S1NC/W1NNER)."""
    norm = normalize_text(value).upper()
    if not norm:
        return ""
    return PORTFOLIO_CANONICAL_PROJECT_MAP.get(norm, "")


def portfolio_team_to_project_key(team_value: str) -> str:
    """Resolve valor de Team do portfólio (ex: 'Sistemas - W1NNER') para chave canônica."""
    team_text = str(team_value or "").strip()
    if not team_text:
        return ""
    norm = normalize_text(team_text).upper()
    candidate = _TEAM_ALIAS_MAP.get(norm, norm)
    return _canonical_project_key(candidate)
