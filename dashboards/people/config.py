"""People configuration — identity, aliases, BU and role resolution.

This module owns all person-identity utilities extracted from dashboard_full.py.
It has NO dependency on dashboard_full; only on the shared layer and stdlib.

Exported:
    _load_people_config
    _load_person_bu_map
    _load_person_role_map
    _load_person_alias_index
    _load_person_seniority_index
    _person_match_key
    _person_email_key
    _person_tokens_for_match
    _normalize_person_name
    _person_names_compatible
    _canonical_person_name
    _person_bu
    _person_role
    _normalize_seniority_bucket
    _normalize_multiselect_value
    _normalize_responsavel_filter_values
    _format_responsavel_filter_label
    _split_people_field
    _project_team_bu
    _project_team_seed_df
    _ensure_dev_productivity_columns
"""

import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from shared.text_utils import normalize_text
from infra.env_config import get_settings

# ---------------------------------------------------------------------------
# Internal cache
# ---------------------------------------------------------------------------

_PEOPLE_CONFIG_CACHE: dict | None = None


# ---------------------------------------------------------------------------
# Core config loader
# ---------------------------------------------------------------------------

def _load_people_config() -> dict:
    """Carrega people_config.json da raiz do projeto (com cache em memória)."""
    global _PEOPLE_CONFIG_CACHE
    if _PEOPLE_CONFIG_CACHE is not None:
        return _PEOPLE_CONFIG_CACHE
    # Look for the config file two levels up from this module (project root)
    config_path = Path(__file__).resolve().parent.parent.parent / "people_config.json"
    if config_path.exists():
        try:
            with config_path.open(encoding="utf-8") as fp:
                _PEOPLE_CONFIG_CACHE = json.load(fp)
            return _PEOPLE_CONFIG_CACHE
        except Exception:
            pass
    _PEOPLE_CONFIG_CACHE = {}
    return _PEOPLE_CONFIG_CACHE


# ---------------------------------------------------------------------------
# Name normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_person_name(raw_name) -> str:
    if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
        return ""
    name = str(raw_name).strip()
    if not name or name.lower() in {"nan", "none"}:
        return ""
    if "<" in name:
        name = name.split("<", 1)[0].strip()
    return re.sub(r"\s+", " ", name).strip()


def _person_email_key(raw_name) -> str:
    if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
        return ""
    text = str(raw_name).strip().lower()
    if not text:
        return ""
    match = re.search(r"([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})", text)
    if match:
        return match.group(1).strip()
    return ""


def _person_match_key(raw_name) -> str:
    normalized = normalize_text(_normalize_person_name(raw_name))
    if not normalized:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return re.sub(r"\s+", " ", normalized)


def _person_tokens_for_match(raw_name) -> set:
    text = normalize_text(_normalize_person_name(raw_name))
    if not text:
        return set()
    ignored = {"de", "da", "do", "dos", "das", "junior", "jr"}
    return {tok for tok in re.split(r"\s+", text) if tok and tok not in ignored}


def _person_names_compatible(left_name, right_name) -> bool:
    """Heurística leve para evitar duplicar a mesma pessoa em variantes próximas de nome."""
    left_key = _person_match_key(left_name)
    right_key = _person_match_key(right_name)
    if left_key and right_key and left_key == right_key:
        return True
    left_tokens = _person_tokens_for_match(left_name)
    right_tokens = _person_tokens_for_match(right_name)
    if len(left_tokens) < 2 or len(right_tokens) < 2:
        return False
    shorter, longer = (
        (left_tokens, right_tokens)
        if len(left_tokens) <= len(right_tokens)
        else (right_tokens, left_tokens)
    )
    return shorter.issubset(longer)


def _split_people_field(raw_value) -> list:
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return []
    text = str(raw_value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return []
    out = []
    for part in text.split("|"):
        person = _normalize_person_name(part)
        if person:
            out.append(person)
    return out


# ---------------------------------------------------------------------------
# Alias index
# ---------------------------------------------------------------------------

def _load_person_alias_index(alias_index=None) -> dict:
    """Builds alias → canonical_name index from FLOW_PMO_PERSON_ALIAS_MAP env var."""
    if isinstance(alias_index, dict):
        return alias_index
    raw = get_settings().FLOW_PMO_PERSON_ALIAS_MAP.strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}

    result: dict = {}

    def _iter_aliases(value):
        if isinstance(value, list):
            yield from value
        elif isinstance(value, str):
            yield from re.split(r"[|,;]", value)

    for canonical_name, aliases in parsed.items():
        canonical = _normalize_person_name(canonical_name)
        if not canonical:
            continue
        for candidate in [canonical_name, canonical, *_iter_aliases(aliases)]:
            person_key = _person_match_key(candidate)
            if person_key:
                result[person_key] = canonical
            email_key = _person_email_key(candidate)
            if email_key:
                result[email_key] = canonical
    return result


def _canonical_person_name(raw_name, alias_index=None) -> str:
    fallback = _normalize_person_name(raw_name)
    if not fallback:
        return ""
    alias_index = alias_index if isinstance(alias_index, dict) else _load_person_alias_index()
    for key in (_person_match_key(raw_name), _person_email_key(raw_name)):
        if key and key in alias_index:
            return alias_index[key]
    return fallback


# ---------------------------------------------------------------------------
# BU map
# ---------------------------------------------------------------------------

def _load_person_bu_map() -> dict:
    """Retorna índice {chave_normalizada → BU} a partir de people_config.json."""
    config = _load_people_config()
    raw_bu_map: dict = config.get("bu_map", {})
    raw_aliases: dict = config.get("aliases", {})

    bu_index: dict = {}

    def _register(raw_name: str, bu: str) -> None:
        key = _person_match_key(raw_name)
        if key:
            bu_index[key] = bu

    for canonical, bu in raw_bu_map.items():
        _register(canonical, bu)
        for alias_entry in raw_aliases.get(canonical, []):
            _register(alias_entry, bu)
    return bu_index


def _person_bu(canonical_name: str, bu_index: dict | None = None) -> str:
    """Retorna a BU de uma pessoa pelo nome canônico. Retorna '' se não encontrado."""
    if bu_index is None:
        bu_index = _load_person_bu_map()
    key = _person_match_key(canonical_name)
    if key and key in bu_index:
        return bu_index.get(key, "")

    config = _load_people_config()
    raw_bu_map: dict = config.get("bu_map", {}) if isinstance(config, dict) else {}
    raw_aliases: dict = config.get("aliases", {}) if isinstance(config, dict) else {}
    for raw_name, bu in raw_bu_map.items():
        if _person_names_compatible(canonical_name, raw_name):
            return str(bu).strip()
        for alias_entry in raw_aliases.get(raw_name, []):
            if _person_names_compatible(canonical_name, alias_entry):
                return str(bu).strip()
    return ""


# ---------------------------------------------------------------------------
# Role map
# ---------------------------------------------------------------------------

def _load_person_role_map() -> dict:
    """Retorna índice {chave_normalizada → papel} a partir de people_config.json."""
    config = _load_people_config()
    raw_role_map: dict = config.get("role_map", {})
    raw_aliases: dict = config.get("aliases", {})
    role_index: dict = {}

    def _register(raw_name: str, role: str) -> None:
        key = _person_match_key(raw_name)
        if key:
            role_index[key] = role

    for canonical, role in raw_role_map.items():
        _register(canonical, role)
        for alias_entry in raw_aliases.get(canonical, []):
            _register(alias_entry, role)
    return role_index


def _person_role(canonical_name: str, role_index: dict | None = None) -> str:
    """Retorna o papel de uma pessoa ('Tech Lead' ou 'Dev'). Padrão = 'Dev'."""
    if role_index is None:
        role_index = _load_person_role_map()
    key = _person_match_key(canonical_name)
    if key and key in role_index:
        return role_index.get(key, "Dev")

    config = _load_people_config()
    raw_role_map: dict = config.get("role_map", {}) if isinstance(config, dict) else {}
    raw_aliases: dict = config.get("aliases", {}) if isinstance(config, dict) else {}
    for raw_name, role in raw_role_map.items():
        if _person_names_compatible(canonical_name, raw_name):
            return str(role).strip() or "Dev"
        for alias_entry in raw_aliases.get(raw_name, []):
            if _person_names_compatible(canonical_name, alias_entry):
                return str(role).strip() or "Dev"
    return "Dev"


# ---------------------------------------------------------------------------
# Seniority map
# ---------------------------------------------------------------------------

def _normalize_seniority_bucket(raw_value) -> str:
    text = normalize_text(raw_value)
    if not text:
        return "Nao classificado"
    if ("senior" in text) or ("sr" == text) or (" s r " in f" {text} "):
        return "Senior"
    if ("junior" in text) or ("jr" == text) or (" j r " in f" {text} "):
        return "Junior"
    return "Outros"


def _load_person_seniority_index(alias_index=None) -> dict:
    raw = get_settings().FLOW_PMO_PERSON_SENIORITY_MAP.strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}

    alias_index = alias_index if isinstance(alias_index, dict) else _load_person_alias_index()
    out: dict = {}
    for person_name, seniority in parsed.items():
        person = _canonical_person_name(person_name, alias_index=alias_index)
        if not person:
            continue
        out[person] = _normalize_seniority_bucket(seniority)
    return out


# ---------------------------------------------------------------------------
# Filter-value helpers
# ---------------------------------------------------------------------------

def _normalize_multiselect_value(raw_value) -> list:
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return []
    if isinstance(raw_value, (list, tuple, set, pd.Series, np.ndarray)):
        candidates = raw_value
    else:
        candidates = [raw_value]
    normalized = []
    seen: set = set()
    for candidate in candidates:
        if candidate is None or (isinstance(candidate, float) and pd.isna(candidate)):
            continue
        text = str(candidate).strip()
        if not text or text.lower() in {"nan", "none"} or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalize_responsavel_filter_values(
    responsavel, alias_index=None, canonicalize: bool = False
) -> list:
    alias_index = alias_index if isinstance(alias_index, dict) else _load_person_alias_index()
    normalized = []
    seen: set = set()
    for raw_name in _normalize_multiselect_value(responsavel):
        person = (
            _canonical_person_name(raw_name, alias_index=alias_index)
            if canonicalize
            else _normalize_person_name(raw_name)
        )
        if not person or person in seen:
            continue
        seen.add(person)
        normalized.append(person)
    return normalized


def _format_responsavel_filter_label(responsavel, max_items: int = 3) -> str:
    selected = _normalize_responsavel_filter_values(responsavel)
    if not selected:
        return "Todos"
    if len(selected) <= max_items:
        return ", ".join(selected)
    return f"{', '.join(selected[:max_items])} +{len(selected) - max_items}"


# ---------------------------------------------------------------------------
# Project → BU / seed-team helpers
# ---------------------------------------------------------------------------

def _project_team_bu(project_value) -> str:
    """Resolve a BU/time oficial a partir do projeto selecionado na aba."""
    project_key = normalize_text(project_value).upper()
    mapping = {
        "W1NNR": "Sistemas - W1NNER",
        "W1NNER": "Sistemas - W1NNER",
        "S1NC": "Sistemas - S1NC",
        "W1SFT": "Sistemas - S1NC",
        "BF": "BeFinance",
        "BEFINANCE": "BeFinance",
        "DT": "Dados",
        "DATA&ANALYTICS": "Dados",
        "DATAANALYTICS": "Dados",
    }
    return mapping.get(project_key, "")


def _project_team_seed_df(project_value) -> pd.DataFrame:
    """Retorna a lista oficial de pessoas do time do projeto com BU e papel."""
    team_bu = _project_team_bu(project_value)
    if not team_bu:
        return pd.DataFrame(columns=["Pessoa", "BU", "Papel"])

    config = _load_people_config()
    bu_map = config.get("bu_map", {}) if isinstance(config, dict) else {}
    alias_index = _load_person_alias_index()
    role_index = _load_person_role_map()
    rows = []
    seen: set = set()
    for raw_name, raw_bu in bu_map.items():
        if str(raw_bu).strip() != team_bu:
            continue
        person = _canonical_person_name(raw_name, alias_index=alias_index)
        if not person or person in seen:
            continue
        seen.add(person)
        rows.append(
            {
                "Pessoa": person,
                "BU": team_bu,
                "Papel": _person_role(person, role_index=role_index),
            }
        )
    if not rows:
        return pd.DataFrame(columns=["Pessoa", "BU", "Papel"])
    return pd.DataFrame(rows).sort_values("Pessoa", ignore_index=True)


# ---------------------------------------------------------------------------
# DataFrame schema enforcement
# ---------------------------------------------------------------------------

def _ensure_dev_productivity_columns(per_dev: pd.DataFrame) -> pd.DataFrame:
    """Garante schema mínimo para exibir membros do time sem entregas no período."""
    if per_dev is None or per_dev.empty:
        return pd.DataFrame(columns=["Pessoa"])

    df = per_dev.copy()
    int_defaults = {
        "Itens Entregues": 0,
        "Itens Puxados": 0,
        "SP Entregues": 0,
        "Defeitos Entregues": 0,
        "Defeitos Puxados": 0,
        "WIP Residual": 0,
        "WIP Inicio Periodo": 0,
    }
    float_defaults = {
        "% Demanda Falha": 0.0,
        "Flow Efficiency (%)": 0.0,
        "FE Ajustada (%)": 0.0,
        "Lead Time Mediano (dias)": 0.0,
        "Score Complexidade": 0.0,
        "Score Complexidade Puxado": 0.0,
        "ECR": 100.0,
    }
    for col, default in int_defaults.items():
        if col not in df.columns:
            df[col] = default
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default).astype(int)
    for col, default in float_defaults.items():
        if col not in df.columns:
            df[col] = default
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)

    bu_index = _load_person_bu_map()
    role_index = _load_person_role_map()
    if "BU" not in df.columns:
        df["BU"] = ""
    if "Papel" not in df.columns:
        df["Papel"] = ""
    df["BU"] = df["BU"].fillna("").astype(str)
    df["Papel"] = df["Papel"].fillna("").astype(str)
    missing_bu = df["BU"].str.strip().eq("")
    if missing_bu.any():
        df.loc[missing_bu, "BU"] = df.loc[missing_bu, "Pessoa"].apply(
            lambda p: _person_bu(p, bu_index=bu_index)
        )
    missing_role = df["Papel"].str.strip().eq("")
    if missing_role.any():
        df.loc[missing_role, "Papel"] = df.loc[missing_role, "Pessoa"].apply(
            lambda p: _person_role(p, role_index=role_index)
        )
    return df
