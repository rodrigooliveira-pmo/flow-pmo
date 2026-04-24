"""Regression tests for dashboards/tabs/renderer.py import completeness.

These tests guard against NameErrors caused by missing module-level imports
in renderer.py — a file extracted from dashboard_full.py whose 13k-line
render_tab function needs all of dashboard_full's original imports available
in renderer.py's own namespace.
"""
from __future__ import annotations

import sys
import types
import unittest.mock as mock

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# 1. renderer.py importa sem erros (todos os pacotes disponíveis)
# ---------------------------------------------------------------------------

def test_renderer_module_imports_cleanly():
    """renderer.py deve importar sem NameError/ImportError."""
    import importlib
    # Force reload to catch any import-time errors
    if 'dashboards.tabs.renderer' in sys.modules:
        mod = sys.modules['dashboards.tabs.renderer']
    else:
        mod = importlib.import_module('dashboards.tabs.renderer')
    assert hasattr(mod, 'render_tab'), "render_tab deve estar definida em renderer.py"


def test_renderer_has_required_names():
    """renderer.py deve expor todas as dependências que o render_tab usa."""
    import importlib
    mod = importlib.import_module('dashboards.tabs.renderer')

    required = [
        'html', 'dcc', 'pd', 'np', 'go', 'px', 'PreventUpdate',
        'normalize_text',
        'TYPE_DEV', 'TYPE_ISSUES', 'TYPE_SUPPORT', 'TYPE_OTHER',
        'normalize_project_filter_value',
        'apply_portfolio_module_filters',
        'done_time_eligible_mask',
        'time_metric_series',
        'exact_empirical_percentile',
        'add_statistical_lines',
        'compute_health_score',
        'render_health_score_panel',
        'create_kpi_card',
        'build_waste_decomposition',
        'math', 'os', 'json', 're',
    ]
    missing = [name for name in required if not hasattr(mod, name)]
    assert missing == [], f"Nomes ausentes em renderer.py: {missing}"


# ---------------------------------------------------------------------------
# 2. render_tab retorna div para main_view='home' sem NameError
# ---------------------------------------------------------------------------

def _make_stub_module():
    """Cria stub mínimo do módulo dashboard_full para render_tab não quebrar."""
    stub = types.ModuleType('dashboard_full')
    # Module-level state accessed via _df()
    stub.fato = pd.DataFrame()
    stub.fato_gargalos = pd.DataFrame()
    stub.FILTER_DATE_CREATED_VALUE = 'created'
    stub.INTERNAL_SERVICE_TAB_VALUES = {'tab-performance'}
    stub.PATTERN_ACTIONS = {}
    stub.PATTERN_RULES = []
    stub.PORTFOLIO_COLOR_THRESHOLDS = {}
    stub.PORTFOLIO_PENDING_BUCKET_1 = 'Pendências 0-15d'
    stub.PORTFOLIO_PENDING_BUCKET_2 = 'Pendências 16-30d'
    stub.PORTFOLIO_PENDING_BUCKET_3 = 'Pendências +30d'
    stub.PORTFOLIO_TAB_VALUE = 'tab-portfolio'
    stub.PROJECT_BITBUCKET_PREFIX = {}
    stub.THROUGHPUT_BREAKDOWN_PRODUCT_LABELS = {}
    stub.THROUGHPUT_BREAKDOWN_PRODUCT_ORDER = []
    stub.WEEK_DATE_RANGE_FREQ = 'W-MON'
    stub._TYPE_CATEGORY_ORDER = []
    stub._TYPE_NORM_TO_CATEGORY = {}
    stub._TYPE_SLA_DISPLAY_LABELS = {}
    # Functions accessed via _df() — return no-ops
    _noop = lambda *a, **kw: None
    for name in [
        '_build_custo_espera_section', '_build_custo_estimado_vs_real_section',
        '_build_custo_pm_calibrado_section', '_build_custo_por_atividade_section',
        '_build_custo_por_fase_section', '_build_custo_retrabalho_section',
        '_build_dev_item_person_map', '_canonical_gmud_service_team',
        '_cfd_stage_color', '_coerce_story_points_value',
        '_compute_dev_aging_rates', '_compute_ied',
        '_compute_monthly_ecr_series', '_compute_monthly_ied_series',
        '_detect_stage_date_columns', '_extract_work_item_keys_from_bitbucket_logs',
        '_format_month_label_pt_br', '_gmud_scope_mask',
        '_load_bitbucket_prefix_map', '_load_four_ps_kanban_data',
        '_pm_filter_real_worklog_df', '_pm_has_real_worklog_data',
        '_pm_product_color', '_pm_product_label',
        '_recompute_itens_entregues_from_dev_flow', '_resolve_dev_person_series',
        '_resolve_type_sla_config', '_story_points_band', '_unified_sp_bucket',
        '_work_item_age_bucket', '_work_item_age_health_label',
        'apply_selected_commitment_metric', 'apply_selected_lead_time_metric',
        'build_bitbucket_contributor_section', 'build_bitbucket_temporal_section',
        'build_cfd_dataframe', 'build_cfd_summary_payload',
        'build_date_range_mask', 'build_dev_productivity_metrics',
        'build_expedite_governance_view', 'build_generated_portfolio_financial_view',
        'build_leadtime_stage_selection_summary', 'build_live_wip_snapshot',
        'build_monthly_product_original_type_breakdown',
        'build_monthly_product_throughput_breakdown',
        'build_period_evolution_sustainability_breakdown',
        'build_pm_commits_vs_jira_report', 'build_pm_dev_return_report',
        'build_pm_portfolio_capex_view', 'build_portfolio_cross_delivery_integration',
        'build_service_bucket_index', 'build_service_lead_time_breakdown',
        'build_service_wip_breakdown', 'build_throughput_avg_cost_series',
        'build_throughput_series', 'build_variability_alerts_view',
        'build_weekly_flow_checklist_and_diagnosis', 'calculate_flow_efficiency',
        'calculate_mm1_metrics', 'classify_urgency_label',
        'compute_bitbucket_contributor_metrics', 'compute_current_stage_map',
        'compute_flow_bottlenecks', 'compute_pipeline_success_rate',
        'compute_pm_bottleneck_contribution', 'compute_pm_dev_flow_metrics',
        'compute_pm_dev_metrics', 'compute_portfolio_snapshot',
        'compute_weekly_service_metrics', 'create_cfd_figure',
        'create_cfd_summary_panel', 'detect_systemic_patterns',
        'filter_df', 'filter_items_by_current_stage', 'format_currency_br',
        'format_original_jira_type_filter_label', 'get_downstream_done_stage_column',
        'get_gmud_snapshot', 'get_portfolio_snapshot', 'get_type_sla_days',
        'get_type_sla_display', 'infer_service_bucket_config',
        'load_project_bitbucket_logs', 'load_project_bottlenecks_from_csv',
        'load_project_bottlenecks_from_model', 'load_project_downstream_items_csv',
        'load_project_pm_case_df', 'load_project_pm_sheet',
        'load_w1nner_process_mining_report', 'portfolio_is_highest_priority',
        'portfolio_table_component', 'render_portfolio_roadmap_full_epics_view',
        'resolve_creation_date_series', 'resolve_filter_date_series',
        'resolve_project_sla_days', 'weekly_bucket_start',
    ]:
        setattr(stub, name, _noop)
    return stub


def test_render_tab_home_returns_div():
    """render_tab com main_view='home' deve retornar html.Div sem NameError."""
    from dashboards.tabs import renderer
    from dash import html

    stub = _make_stub_module()
    with mock.patch.dict(sys.modules, {'dashboard_full': stub}):
        result = renderer.render_tab(
            main_view='home',
            tab=None,
            start_date='2026-01-01',
            end_date='2026-04-01',
            projeto=None,
            tipo=None,
            tipo_original_jira=None,
            classe_servico=None,
            responsavel=None,
            leadtime_stages=None,
        )
    assert isinstance(result, html.Div), (
        f"render_tab('home') deve retornar html.Div, obteve {type(result)}"
    )
