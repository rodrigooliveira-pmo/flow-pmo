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
        return default
    return parsed if isinstance(parsed, dict) else default
