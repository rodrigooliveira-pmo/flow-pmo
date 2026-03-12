"""Utilitários de resolução de caminhos compartilhados entre os módulos Flow-PMO.

Hierarquia de resolução de DATA_FOLDER (por prioridade decrescente):
  1. FLOW_PMO_DATA_DIR  — diretório único explícito
  2. DATA_FOLDER        — override legado
  3. FLOW_PMO_DATA_DIRS — lista separada por pathsep
  4. <project_root>/dados/latest/
  5. <project_root>/dados/
  6. <home>/Documents/dados
  7. <home>/Documents/Dados
  8. <project_root>/data/
  9. <project_root>/
 10. LEGACY_DATA_FOLDER — OneDrive Windows/macOS
"""
from __future__ import annotations

import glob
import os
import platform
import re


# Pasta legado OneDrive — fallback quando nenhuma outra existe
if platform.system() == "Windows":
    LEGACY_DATA_FOLDER = r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados"
else:
    LEGACY_DATA_FOLDER = os.path.join(
        os.path.expanduser("~"),
        "Library",
        "CloudStorage",
        "OneDrive-W1",
        "Documentos",
        "Dados",
    )

# Raiz do projeto = pasta pai de shared/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_windows_absolute_path(path_value: str) -> bool:
    raw = str(path_value or "").strip()
    return bool(re.match(r"^[A-Za-z]:[\\/]", raw))


def _is_posix_absolute_path(path_value: str) -> bool:
    raw = str(path_value or "").strip()
    return raw.startswith("/")


def _is_path_compatible_with_current_os(path_value: str) -> bool:
    """Retorna False para caminhos absolutos de SO incompatível (ex: C:\\ no macOS)."""
    raw = str(path_value or "").strip()
    if not raw:
        return False
    if platform.system() == "Windows":
        return _is_windows_absolute_path(raw) or not _is_posix_absolute_path(raw)
    return _is_posix_absolute_path(raw) or not _is_windows_absolute_path(raw)


def _sanitize_os_path(path_value: str) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return ""
    return raw if _is_path_compatible_with_current_os(raw) else ""


def existing_dirs(paths: list[str]) -> list[str]:
    """Filtra e deduplica caminhos, retornando apenas diretórios existentes e compatíveis com o SO."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        cleaned = _sanitize_os_path(raw)
        if not cleaned:
            continue
        p = os.path.abspath(cleaned)
        if p in seen:
            continue
        seen.add(p)
        if os.path.isdir(p):
            out.append(p)
    return out


def candidate_data_folders() -> list[str]:
    """Retorna lista de pastas de dados existentes, em ordem de prioridade."""
    home_dir = os.path.expanduser("~")
    env_dirs = os.getenv("FLOW_PMO_DATA_DIRS", "").strip()
    split_env_dirs = [p for p in env_dirs.split(os.pathsep) if p.strip()]
    return existing_dirs([
        os.getenv("FLOW_PMO_DATA_DIR", "").strip(),
        os.getenv("DATA_FOLDER", "").strip(),
        *split_env_dirs,
        os.path.join(_PROJECT_ROOT, "dados", "latest"),
        os.path.join(_PROJECT_ROOT, "dados"),
        os.path.join(home_dir, "Documents", "dados"),
        os.path.join(home_dir, "Documents", "Dados"),
        os.path.join(_PROJECT_ROOT, "data"),
        _PROJECT_ROOT,
        LEGACY_DATA_FOLDER,
    ])


def find_latest_file(folder: str, prefix: str, extension: str = "*.xlsx") -> str | None:
    """Retorna o arquivo mais recente em `folder` cujo nome começa com `prefix`.

    Args:
        folder: Diretório onde buscar.
        prefix: Prefixo do nome do arquivo.
        extension: Padrão glob de extensão (padrão: "*.xlsx").

    Returns:
        Caminho absoluto do arquivo mais recente, ou None se não encontrado.
    """
    pattern = os.path.join(folder, f"{prefix}{extension}")
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)
