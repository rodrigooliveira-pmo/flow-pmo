"""
4Ps module — Relatório de Governança TECH

Exports públicos do módulo:

  build_four_ps_payload   — builder principal (portfólio + kanban + operacional)
  render_four_ps_tab      — renderer Dash da aba 4Ps
  FourPsKanbanExtractor   — extrator Jira (boards Kanban + nível operacional)
  load_four_ps_config     — acesso à configuração YAML

Fluxo típico no callback do dashboard:
    from dashboards.four_ps import build_four_ps_payload, render_four_ps_tab

    payload = build_four_ps_payload(
        df_portfolio=df_portfolio_full_scope,
        kanban_data=kanban_data,        # opcional
        operational_data=operational_data,  # opcional
        month=date(2026, 4, 1),
    )
    return render_four_ps_tab(payload, month=date(2026, 4, 1))
"""

from dashboards.four_ps.builder import (
    build_four_ps_payload,
    build_portfolio_4ps,
    merge_kanban_into_payload,
    merge_operational_into_payload,
    suggest_epic_for_bau,
    build_monthly_summary,
    compute_four_ps_kpis,
    FourPsPayload,
    AreaData,
    ItemDict,
)

from dashboards.four_ps.renderer import render_four_ps_tab

from jira.four_ps_kanban import (
    FourPsKanbanExtractor,
    load_four_ps_config,
    discover_team_uuid_map,
)

__all__ = [
    # Builder
    "build_four_ps_payload",
    "build_portfolio_4ps",
    "merge_kanban_into_payload",
    "merge_operational_into_payload",
    "suggest_epic_for_bau",
    "build_monthly_summary",
    "compute_four_ps_kpis",
    "FourPsPayload",
    "AreaData",
    "ItemDict",
    # Renderer
    "render_four_ps_tab",
    # Extrator Jira
    "FourPsKanbanExtractor",
    "load_four_ps_config",
    "discover_team_uuid_map",
]
