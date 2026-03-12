"""Utilitários de normalização de texto compartilhados entre os módulos Flow-PMO."""
from __future__ import annotations

import unicodedata
from typing import Any


def normalize_text(value: Any) -> str:
    """Normaliza texto: minúsculas, remove acentos, colapsa espaços.

    Usa unicodedata.normalize(NFKD) para remoção de acentos, mais robusto que
    str.maketrans para cobrir todos os caracteres Unicode.

    Exemplos:
        "João Silva"  → "joao silva"
        "Em_Progresso" → "em progresso"
        None           → ""
    """
    raw = str(value or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", raw)
    no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return " ".join(no_accents.replace("_", " ").replace("-", " ").split())
