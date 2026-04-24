"""Static analysis: garante que funções em all_functions.py não acessam
variáveis de estado do módulo dashboard_full diretamente.

As funções em all_functions.py devem acessar estado mutável do dashboard_full
(DataFrames carregados em runtime como `fato`, `fato_gargalos`, etc.) APENAS
via `_df().<var>`, nunca como global free-variable. Acessar diretamente resulta
em NameError em runtime porque essas variáveis não existem no escopo de
all_functions.py.
"""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

ALL_FUNCTIONS_PATH = (
    Path(__file__).parent.parent.parent
    / "dashboards" / "domain" / "all_functions.py"
)

# Variáveis que são MODULE-LEVEL state de dashboard_full.py e NÃO devem ser
# acessadas como free variables em all_functions.py.
DASHBOARD_FULL_MODULE_STATE = {
    'fato',
    'fato_gargalos',
    'dim_projeto',
    'dim_tipo',
    'dim_responsavel',
    'dim_prioridade',
    'dim_classe_servico',
    'xls',
    'creator_filter_options',
    'done_date_defaults',
    'creation_date_defaults',
    'date_min_candidates',
    'date_max_candidates',
    'min_date',
    'max_date',
    'rename_map',
}

# Constantes que são DUPLICADAS em all_functions.py (definidas como {} ou similar)
# e portanto é ACEITÁVEL acessar como local — não são free variables perigosas.
SAFE_DUPLICATES = {
    'PORTFOLIO_CACHE',
    'CAPEX_CACHE',
    'PROCESS_MINING_CACHE',
    'BITBUCKET_CACHE',
    'DEFAULT_PATTERN_RULES',
}


def _collect_free_names_in_function(func_node: ast.FunctionDef) -> set[str]:
    """Retorna nomes referenciados dentro da função que não são parâmetros,
    não são atribuídos localmente e não são built-ins."""
    assigned = set()
    referenced = set()

    for node in ast.walk(func_node):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Store):
                assigned.add(node.id)
            elif isinstance(node.ctx, ast.Load):
                referenced.add(node.id)
        elif isinstance(node, (ast.arg,)):
            assigned.add(node.arg)

    # Parameters are assigned implicitly
    for arg in func_node.args.args + func_node.args.posonlyargs + func_node.args.kwonlyargs:
        assigned.add(arg.arg)
    if func_node.args.vararg:
        assigned.add(func_node.args.vararg.arg)
    if func_node.args.kwarg:
        assigned.add(func_node.args.kwarg.arg)

    return referenced - assigned


def _get_violations() -> list[tuple[str, str, int]]:
    """Retorna lista de (func_name, var_name, line) para violações encontradas."""
    source = ALL_FUNCTIONS_PATH.read_text(encoding='utf-8')
    tree = ast.parse(source)

    # Collect module-level assigned names (safe to reference)
    module_assigned = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    module_assigned.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                module_assigned.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module_assigned.add(node.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                module_assigned.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module_assigned.add(alias.asname or alias.name.split('.')[0])

    violations = []
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        func_name = node.name
        free = _collect_free_names_in_function(node)
        for var in DASHBOARD_FULL_MODULE_STATE - SAFE_DUPLICATES:
            if var in free and var not in module_assigned:
                violations.append((func_name, var, node.lineno))

    return violations


@pytest.fixture(scope='module')
def violations():
    return _get_violations()


def test_no_naked_dashboard_full_state_access(violations):
    """Nenhuma função em all_functions.py deve acessar estado de dashboard_full
    como free variable. Use _df().<var> em vez disso."""
    if not violations:
        return

    details = '\n'.join(
        f"  Line {line}: {func}() acessa '{var}' diretamente — use _df().{var}"
        for func, var, line in sorted(violations, key=lambda x: x[2])
    )
    pytest.fail(
        f"{len(violations)} violação(ões) encontrada(s) em all_functions.py:\n{details}\n\n"
        "Correção: adicione `{var} = _df().{var}` no início de cada função acima."
    )


def test_all_functions_file_exists():
    assert ALL_FUNCTIONS_PATH.exists(), f"Arquivo não encontrado: {ALL_FUNCTIONS_PATH}"


def test_all_functions_parses_without_syntax_error():
    source = ALL_FUNCTIONS_PATH.read_text(encoding='utf-8')
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"SyntaxError em all_functions.py: {e}")
