"""Constantes de domínio do Flow-PMO — única fonte da verdade para configurações de negócio."""
from __future__ import annotations

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Times / Squads
# ---------------------------------------------------------------------------

TEAMS: Tuple[str, ...] = ("W1NNER", "S1NC", "BEFINANCE", "DATA&ANALYTICS")

TEAM_DISPLAY_NAMES: Dict[str, str] = {
    "W1NNER": "W1nner",
    "S1NC": "S1NC",
    "BEFINANCE": "BeFinance",
    "DATA&ANALYTICS": "Dados",
}

# ---------------------------------------------------------------------------
# Story Points
# ---------------------------------------------------------------------------

STORY_POINT_BANDS: Tuple[str, ...] = ("0", "1", "2-3", "5", "8", "13+")

STORY_POINT_BAND_MAP: Dict[int, str] = {
    0: "0",
    1: "1",
    2: "2-3",
    3: "2-3",
    5: "5",
    8: "8",
}

STORY_POINT_BAND_THRESHOLD_LARGE = 13  # valores >= 13 → "13+"

# ---------------------------------------------------------------------------
# Quarters (datas canônicas de início e fim)
# ---------------------------------------------------------------------------

QUARTER_DATES: Dict[str, Tuple[str, str]] = {
    "Q1-2025": ("2025-01-01", "2025-03-31"),
    "Q2-2025": ("2025-04-01", "2025-06-30"),
    "Q3-2025": ("2025-07-01", "2025-09-30"),
    "Q4-2025": ("2025-10-01", "2025-12-31"),
    "Q1-2026": ("2026-01-01", "2026-03-31"),
    "Q2-2026": ("2026-04-01", "2026-06-30"),
    "Q3-2026": ("2026-07-01", "2026-09-30"),
    "Q4-2026": ("2026-10-01", "2026-12-31"),
}

# ---------------------------------------------------------------------------
# Tokens de normalização de prioridade alta (corrigidos de HIGHEST_ALIAS_TOKENS)
# ---------------------------------------------------------------------------

HIGHEST_ALIAS_TOKENS: Tuple[str, ...] = (
    "highest",
    "highest",   # corrige typo "higest" do módulo legado
    "expedite",
    "urgent",
    "urgente",
    "critical",
    "critico",
    "blocker",
    "fast track",
    "fasttrack",
)

# Typos históricos aceitos como aliases (para retrocompatibilidade de normalização)
HIGHEST_ALIAS_TYPOS: Tuple[str, ...] = (
    "higest",    # typo histórico em HIGHEST_ALIAS_TOKENS original
    "critico",   # sem acento (normalize_text já remove acentos)
)

# ---------------------------------------------------------------------------
# Filtros de status
# ---------------------------------------------------------------------------

DONE_STATUS_TERMS: Tuple[str, ...] = (
    "done",
    "conclu",
    "closed",
    "resolved",
    "cancel",
)

WAITING_STATUS_TERMS: Tuple[str, ...] = (
    "waiting",
    "aguardando",
    "blocked",
    "bloqueado",
    "on hold",
)

BACKLOG_STATUS_TERMS: Tuple[str, ...] = (
    "backlog",
    "triagem",
    "triage",
    "to do",
    "todo",
    "ready",
)
