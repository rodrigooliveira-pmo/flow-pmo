"""Utilitários de variáveis de ambiente compartilhados entre os módulos Flow-PMO."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def load_env_file(env_file: str, overwrite: bool = True) -> None:
    """Carrega pares CHAVE=VALOR de um arquivo .env para os.environ.

    Args:
        env_file: Caminho para o arquivo .env.
        overwrite: Se True (padrão), sobrescreve variáveis já definidas.
    """
    path = Path(env_file)
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            quote = value[0]
            value = value[1:-1]
            if quote == '"':
                value = (
                    value
                    .replace(r'\"', '"')
                    .replace(r'\n', '\n')
                    .replace(r'\r', '\r')
                    .replace(r'\t', '\t')
                )
            else:
                value = value.replace(r"\'", "'")
        if key and value and (overwrite or key not in os.environ):
            os.environ[key] = value


def parse_json_env(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    """Lê uma variável de ambiente como JSON e retorna um dict.

    Retorna `default` se a variável não existir, estiver vazia ou for JSON inválido.
    """
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = _parse_relaxed_object_env(raw)
    return parsed if isinstance(parsed, dict) else default


def _parse_relaxed_object_env(raw: str) -> Dict[str, Any] | None:
    """Aceita mapas simples de env no formato `{A:1,B:texto}`.

    Esse fallback cobre valores históricos do projeto em `.env.local`, que às vezes
    aparecem com chaves sem aspas e barras invertidas escapando `:` e nomes.
    """
    text = (raw or "").strip()
    if not text.startswith("{") or not text.endswith("}"):
        return None

    body = text[1:-1].strip()
    if not body:
        return {}

    result: Dict[str, Any] = {}
    for entry in _split_relaxed_env_entries(body):
        if not entry:
            continue
        key, value = _split_relaxed_env_key_value(entry)
        if key is None:
            return None
        normalized_key = _normalize_relaxed_env_token(key)
        if not normalized_key:
            continue
        result[normalized_key] = _coerce_relaxed_env_value(value)
    return result


def _split_relaxed_env_entries(body: str) -> list[str]:
    entries: list[str] = []
    current: list[str] = []
    in_quotes = False
    quote_char = ""
    depth = 0

    for char in body:
        if in_quotes:
            current.append(char)
            if char == quote_char:
                in_quotes = False
            continue
        if char in {'"', "'"}:
            in_quotes = True
            quote_char = char
            current.append(char)
            continue
        if char in "{[":
            depth += 1
            current.append(char)
            continue
        if char in "}]":
            depth = max(0, depth - 1)
            current.append(char)
            continue
        if char == "," and depth == 0:
            item = "".join(current).strip()
            if item:
                entries.append(item)
            current = []
            continue
        current.append(char)

    tail = "".join(current).strip()
    if tail:
        entries.append(tail)
    return entries


def _split_relaxed_env_key_value(entry: str) -> tuple[str | None, str]:
    in_quotes = False
    quote_char = ""
    depth = 0

    for idx, char in enumerate(entry):
        if in_quotes:
            if char == quote_char:
                in_quotes = False
            continue
        if char in {'"', "'"}:
            in_quotes = True
            quote_char = char
            continue
        if char in "{[":
            depth += 1
            continue
        if char in "}]":
            depth = max(0, depth - 1)
            continue
        if char == ":" and depth == 0:
            return entry[:idx], entry[idx + 1 :]
    return None, ""


def _normalize_relaxed_env_token(token: str) -> str:
    text = (token or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1]
    text = text.replace("\\:", ":").replace('\\"', '"').replace("\\'", "'").strip()
    while text.startswith("\\"):
        text = text[1:].strip()
    while text.endswith("\\"):
        text = text[:-1].strip()
    return text


def _coerce_relaxed_env_value(value: str) -> Any:
    normalized = _normalize_relaxed_env_token(value)
    if not normalized:
        return ""

    lowered = normalized.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None

    try:
        if any(ch in normalized for ch in (".", "e", "E")):
            return float(normalized)
        return int(normalized)
    except ValueError:
        return normalized
