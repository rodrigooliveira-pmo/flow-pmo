import sys as _sys_bootstrap
# When run directly as `python dashboard_full.py`, register this module under its
# real name so that submodules doing `from dashboard_full import X` don't trigger
# a second full execution (which would re-register all callbacks and clientside_callbacks).
if __name__ == '__main__':
    _sys_bootstrap.modules.setdefault('dashboard_full', _sys_bootstrap.modules['__main__'])

import dash
try:
    from dash import dcc, html, Input, Output, State, dash_table
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html
    from dash.dependencies import Input, Output, State
    import dash_table
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import os
import json
import numpy as np
import math
import hashlib
from pathlib import Path
import socket
import urllib.request
import urllib.parse
import posixpath
import re
from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import Any, Dict, List
try:
    from plotly.subplots import make_subplots
except ImportError:
    from plotly.tools import make_subplots
import plotly.graph_objects as go
from datetime import datetime, timedelta
import platform

from shared.env_utils import load_env_file, parse_json_env
from shared.path_utils import candidate_data_folders, _sanitize_os_path
from shared.text_utils import normalize_text

from jira.client import JiraClient
from jira.four_ps_kanban import FourPsKanbanExtractor

# Import from refactored modules
from dashboards.core import (
    _download_model_from_url,
    _download_portfolio_csv_from_url,
    _download_four_ps_kanban_csv_from_url,
    _download_bottleneck_csv_from_url,
    _download_process_mining_report_from_url,
    _download_downstream_items_csv_from_url,
    _download_capex_csv_from_url,
    _download_gmud_csv_from_url,
    _load_bottleneck_url_map,
    _load_bitbucket_csv_url_map,
    _download_bitbucket_csv_from_url,
    _load_downstream_url_map,
    _url_filename_matches_project_suffix,
    _url_filename_matches_project,
    _resolve_model_file,
    DATA_FOLDERS,
    DATA_FOLDER,
    PROCESS_MINING_ARTIFACT_FOLDER,
    MODEL_FILE,
    _iter_local_data_folders,
    _format_last_processed_load,
    LAST_PROCESSED_LOAD_LABEL,
    safe_read_sheet,
    load_model_data,
    resolve_service_class,
    canonicalize_highest_label,
    is_highest_alias,
    portfolio_type_to_demand_type,
    portfolio_project_team_aliases,
    portfolio_has_extra_onepage_tag,
    apply_portfolio_module_filters,
    process_fato_data,
    canonicalize_demand_type,
    normalize_project_filter_value,
    unique_sorted,
    done_time_eligible_mask,
    TYPE_SUPPORT,
    TYPE_ISSUES,
    TYPE_DEV,
    TYPE_OTHER,
    PORTFOLIO_EXTRA_ONEPAGE_TAG,
    PROJECT_FILTER_ALL_VALUE,
    ORIGINAL_JIRA_TYPE_FILTER_ALL_VALUE,
)

from dashboards.metrics.time_metrics import (
    time_metric_series,
    build_lead_time_comparable_scope,
    unique_item_keys,
    build_delivered_items_base,
    exact_empirical_percentile,
    exact_percentile_map,
    fit_weibull_linearized,
    describe_weibull_scale_cadence,
    exact_percentile_band_summary,
    add_statistical_lines,
    compute_process_capability_metrics,
    build_monthly_throughput_percentage_by_type,
    build_monthly_leadtime_sla_percentage_by_type,
)

from dashboards.metrics.efficiency_metrics import (
    build_waste_decomposition,
    build_scenario_simulation,
)
from dashboards.metrics.health_score import compute_health_score, compute_health_score_monthly
from dashboards.components.health_score_modal import render_health_score_panel

from dashboards.components.cards import (
    create_kpi_card,
    _portfolio_metric_card,
)

from dashboards.components.tables import (
    create_table,
    create_generic_datatable,
)

from dashboards.four_ps import build_four_ps_payload, render_four_ps_tab
from dashboards.pages.corporativo import layout_corporativo
from dashboards.components.error_boundary import error_boundary, callback_error_div

from dashboards.people import (
    _load_people_config,
    _load_person_bu_map,
    _load_person_role_map,
    _load_person_alias_index,
    _load_person_seniority_index,
    _person_match_key,
    _person_email_key,
    _person_tokens_for_match,
    _normalize_person_name,
    _person_names_compatible,
    _canonical_person_name,
    _person_bu,
    _person_role,
    _normalize_seniority_bucket,
    _normalize_multiselect_value,
    _normalize_responsavel_filter_values,
    _format_responsavel_filter_label,
    _split_people_field,
    _project_team_bu,
    _project_team_seed_df,
    _ensure_dev_productivity_columns,
)

from dashboards.callbacks import navigation as _nav_callbacks, metrics as _metrics_callbacks
from dashboards.domain.all_functions import (
    canonicalize_original_jira_type,
    classify_original_jira_demand_bucket,
    is_failure_demand_type,
    _load_bitbucket_prefix_map,
    _coerce_story_points_value,
    _story_points_band,
    _load_project_bitbucket_csv,
    load_project_bitbucket_logs,
    compute_bitbucket_contributor_metrics,
    compute_bitbucket_temporal_metrics,
    build_bitbucket_temporal_section,
    compute_jira_person_capacity_metrics,
    compute_cross_source_capacity_metrics,
    compute_cross_source_capacity_weekly_metrics,
    _sp_bucket,
    _sp_weight,
    _tshirt_to_weight,
    _unified_complexity_weight,
    _build_sp_inference_model,
    _infer_sp,
    _unified_sp_bucket,
    _resolve_dev_person_series,
    _build_dev_item_person_map,
    _recompute_itens_entregues_from_dev_flow,
    build_dev_productivity_metrics,
    _compute_ied,
    _compute_monthly_ied_series,
    _compute_monthly_ecr_series,
    _compute_dev_aging_rates,
    build_bitbucket_contributor_section,
    _extract_work_item_keys_from_bitbucket_logs,
    build_pm_commits_vs_jira_report,
    load_pattern_rules,
    _parse_env_date,
    _bool_env,
    _load_four_ps_kanban_csv,
    _load_four_ps_kanban_online,
    _resolve_four_ps_kanban_csv_source,
    _load_four_ps_kanban_data,
    _safe_ratio,
    _safe_pct,
    _get_weekly_wip_items_per_person_limit,
    _get_expedite_target_pct,
    _get_expedite_critical_pct,
    _get_variability_cv_warn,
    _get_variability_cv_critical,
    _is_expedite_service_class,
    _variability_status,
    detect_systemic_patterns,
    build_weekly_flow_checklist_and_diagnosis,
    build_expedite_governance_view,
    build_variability_alerts_view,
    compute_portfolio_snapshot,
    find_latest_portfolio_csv,
    build_portfolio_snapshot_from_csv,
    get_portfolio_snapshot,
    _canonical_gmud_service_team,
    _gmud_kind_spec,
    _replace_url_filename,
    _iter_gmud_companion_urls,
    find_latest_gmud_csv,
    _gmud_bool_series,
    _gmud_link_evidence_series,
    _prepare_gmud_snapshot_df,
    get_gmud_snapshot,
    _gmud_scope_mask,
    _capex_local_file_matches,
    _capex_required_columns,
    _find_latest_capex_csv,
    _load_capex_csv,
    get_capex_snapshot,
    _capex_project_key_from_team,
    _build_capex_portfolio_asset_lookup,
    _build_capex_person_rate_map,
    _build_custo_por_atividade_section,
    build_cost_per_phase_data,
    _build_custo_por_fase_section,
    _pm_filter_real_worklog_df,
    _pm_has_real_worklog_data,
    build_custo_estimado_vs_real_data,
    _build_custo_estimado_vs_real_section,
    build_custo_pm_calibrado_data,
    _build_custo_pm_calibrado_section,
    _pm_is_waiting_status,
    _pm_waiting_direction,
    _portfolio_team_to_pm_project_key,
    _bt_strategic_board_phase,
    _build_strategic_portfolio_wait_frame,
    build_custo_espera_data,
    _build_custo_espera_section,
    _coerce_bool_flag,
    build_custo_retrabalho_data,
    _build_custo_retrabalho_section,
    _build_capex_worklog_fact,
    _capex_project_key,
    _capex_asset_key,
    _capex_prepare_worklog_df,
    build_worklog_cost_fact,
    _build_worklog_portfolio_cost_view_legacy,
    get_portfolio_project_filter_options,
    _capex_kind_spec,
    _capex_find_latest_csv_v2_unused,
    _prepare_capex_snapshot_df,
    _get_capex_snapshot_v2_unused,
    portfolio_table_component,
    portfolio_roadmap_status_label,
    portfolio_quarter_label_from_date,
    portfolio_roadmap_progress_pct,
    portfolio_is_highest_priority,
    portfolio_is_cancelled_item,
    render_portfolio_roadmap_quarter_view,
    render_portfolio_roadmap_full_epics_view,
    normalize_original_jira_type_filter_values,
    format_original_jira_type_filter_label,
    weekly_bucket_start,
    format_currency_br,
    build_cfd_dataframe,
    _detect_stage_date_columns,
    build_detailed_cfd_exact_dataframe,
    _hex_to_rgba,
    _cfd_stage_color,
    _compute_cfd_trend_line,
    _select_cfd_rate_stages,
    create_cfd_figure,
    _get_cfd_detailed_unavailable_reason,
    build_cfd_summary_payload,
    create_cfd_summary_panel,
    _cfd_stat_chip_style,
    classify_urgency_label,
    resolve_project_sla_days,
    _resolve_type_sla_config,
    get_type_sla_display,
    get_type_sla_days,
    infer_service_bucket_config,
    build_service_bucket_index,
    _service_dimension_label,
    build_service_lead_time_breakdown,
    build_throughput_series,
    build_live_wip_snapshot,
    build_service_wip_breakdown,
    _format_pct_br,
    _format_month_label_pt_br,
    _throughput_breakdown_product_key,
    build_monthly_product_throughput_breakdown,
    build_evolution_sustainability_breakdown,
    filter_done_to_month,
    build_period_evolution_sustainability_breakdown,
    build_monthly_product_original_type_breakdown,
    calculate_mm1_metrics,
    calculate_flow_efficiency,
    compute_flow_bottlenecks,
    load_project_bottlenecks_from_model,
    load_project_bottlenecks_from_csv,
    load_project_downstream_items_csv,
    load_project_downstream_metadata,
    enrich_items_with_downstream_metadata,
    get_downstream_workflow_stage_columns,
    get_default_lead_time_start_stages,
    _compute_storytask_orphan_from_downstream,
    get_explicit_done_stage_column,
    get_downstream_done_stage_column,
    compute_current_stage_map,
    filter_items_by_current_stage,
    _find_latest_w1nner_process_mining_excel,
    load_w1nner_process_mining_report,
    _load_pm_excel_url_map,
    load_project_pm_sheet,
    load_project_pm_case_df,
    _load_portfolio_cost_model,
    _load_portfolio_role_salary_map,
    _load_portfolio_bu_salary_map,
    _build_portfolio_cost_team_df,
    _product_bu_for_cost,
    build_portfolio_cost_model_snapshot,
    _pm_pick_first_column,
    _canonical_pm_product_key,
    _pm_product_label,
    _pm_product_color,
    _pm_portfolio_selected_specs,
    _pm_load_cost_rate_map,
    _pm_status_phase_category,
    _pm_load_capacity_map,
    _pm_derive_sync_calibration,
    build_touch_time_triangulation,
    build_capex_worklog_cost_fact,
    build_throughput_avg_cost_series,
    _pm_is_execution_status,
    _pm_is_asset_type,
    _pm_clean_issue_key,
    _pm_build_portfolio_lookup,
    _pm_build_downstream_asset_map,
    _infer_project_key_from_issue,
    _build_worklog_portfolio_cost_view_v2_unused,
    _build_synthetic_capex_worklog_from_pm,
    build_pm_portfolio_capex_view,
    build_generated_portfolio_financial_view,
    build_portfolio_cross_delivery_integration,
    _pm_is_dev_status,
    _pm_is_qa_status,
    _pm_summarize_dev_flow_from_events,
    _pm_extract_dev_flow_datasets,
    compute_pm_dev_metrics,
    compute_pm_dev_flow_metrics,
    build_pm_dev_return_report,
    compute_pipeline_success_rate,
    compute_pm_bottleneck_contribution,
    get_leadtime_stage_filter_columns,
    build_custom_lead_time_by_selected_stages,
    build_time_to_commit_by_selected_stages,
    _coerce_datetime_flexible,
    _resolve_lead_start_series,
    apply_selected_lead_time_metric,
    apply_selected_commitment_metric,
    build_leadtime_stage_selection_summary,
    _compute_bitbucket_weekly_dora,
    _format_change_lead_time,
    compute_weekly_service_metrics,
    resolve_creator_filter_column,
    build_dropdown_options_from_column,
    build_creator_filter_dataset,
    get_creator_filter_options_for_project,
    resolve_creation_date_series,
    resolve_filter_date_series,
    build_date_range_mask,
    filter_df,
    _work_item_age_health_label,
    _work_item_age_bucket,
)


# Load model
try:
    _model_file_to_load = MODEL_FILE or _resolve_model_file(DATA_FOLDERS)
    xls = pd.ExcelFile(_model_file_to_load)
    dim_projeto = pd.read_excel(xls, sheet_name='Dim_Projeto')
    dim_tipo = pd.read_excel(xls, sheet_name='Dim_Tipo')
    dim_responsavel = safe_read_sheet(xls, 'Dim_Responsavel', ['ResponsavelID', 'Responsavel'])
    dim_prioridade = safe_read_sheet(xls, 'Dim_Prioridade', ['PrioridadeID', 'Prioridade'])
    dim_classe_servico = safe_read_sheet(xls, 'Dim_ClasseServico', ['ClasseServicoID', 'ClasseServico'])
    fato = pd.read_excel(xls, sheet_name='Fato_Items')
    fato_gargalos = safe_read_sheet(
        xls,
        'Fato_Gargalos',
        ['Projeto', 'Etapa', 'Tempo Médio (dias)', 'Tempo Mediano (dias)', 'P90 (dias)', 'Qtde Itens', 'Vazão da Etapa (itens)'],
    )
except Exception as _model_load_exc:
    import traceback as _tb
    print(f"[dashboard_full] ERRO ao carregar modelo: {_model_load_exc}", flush=True)
    print(_tb.format_exc(), flush=True)
    xls = None
    dim_projeto = pd.DataFrame()
    dim_tipo = pd.DataFrame()
    dim_responsavel = pd.DataFrame()
    dim_prioridade = pd.DataFrame()
    dim_classe_servico = pd.DataFrame()
    fato = pd.DataFrame()
    fato_gargalos = pd.DataFrame()

# Normalize date columns
for dcol in ['DataBacklog', 'DataInProgress', 'DataDone']:
    if dcol in fato.columns:
        fato[dcol] = pd.to_datetime(fato[dcol], errors='coerce')

# Fallback: when DataInProgress is missing, use DataBacklog as start proxy.
if 'DataInProgress' in fato.columns and 'DataBacklog' in fato.columns:
    missing_in_progress = fato['DataInProgress'].isna() & fato['DataBacklog'].notna()
    if missing_in_progress.any():
        fato.loc[missing_in_progress, 'DataInProgress'] = fato.loc[missing_in_progress, 'DataBacklog']

# Merge readable names
print(f"[dashboard_full] dim_projeto empty={dim_projeto.empty} cols={list(dim_projeto.columns) if not dim_projeto.empty else []}", flush=True)
if not dim_projeto.empty and 'ProjetoID' in dim_projeto.columns:
    fato = fato.merge(dim_projeto, how='left', left_on='ProjetoID', right_on='ProjetoID')
if not dim_tipo.empty and 'TipoID' in dim_tipo.columns:
    fato = fato.merge(dim_tipo, how='left', left_on='TipoID', right_on='TipoID')
if not dim_responsavel.empty:
    fato = fato.merge(dim_responsavel, how='left', left_on='ResponsavelID', right_on='ResponsavelID')
if not dim_prioridade.empty:
    fato = fato.merge(dim_prioridade, how='left', left_on='PrioridadeID', right_on='PrioridadeID')
if not dim_classe_servico.empty and 'ClasseServicoID' in fato.columns:
    fato = fato.merge(dim_classe_servico, how='left', left_on='ClasseServicoID', right_on='ClasseServicoID')
if 'Responsavel' not in fato.columns:
    fato['Responsavel'] = ''
print(f"[dashboard_full] fato cols after merge: {list(fato.columns)}", flush=True)


# Friendly column names
rename_map = {
    'NomeProjeto': 'Projeto',
    'Tipo': 'Tipo',
    'Responsavel': 'Responsavel',
    'Prioridade': 'Prioridade',
    'ClasseServico': 'ClasseServico',
}
fato.rename(columns={k: v for k, v in rename_map.items() if k in fato.columns}, inplace=True)
if 'Projeto' not in fato.columns:
    print(f"[dashboard_full] AVISO: coluna 'Projeto' ausente em fato. Colunas disponíveis: {list(fato.columns)}", flush=True)
    fato['Projeto'] = ''
if 'ClasseServico' not in fato.columns:
    fato['ClasseServico'] = np.nan
if 'Prioridade' not in fato.columns:
    fato['Prioridade'] = np.nan
fato['Prioridade'] = fato['Prioridade'].apply(canonicalize_highest_label)
fato['ClasseServico'] = fato.apply(lambda row: resolve_service_class(row.get('ClasseServico'), row.get('Prioridade')), axis=1)

# Semana padrão do sistema: semana ISO (segunda a domingo).
WEEK_DATE_RANGE_FREQ = 'W-MON'
WEEK_PERIOD = 'W-SUN'
CFD_SNAPSHOT_FREQ = 'D'

# App
app = dash.Dash(
    __name__,
    external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'],
    suppress_callback_exceptions=True,
    serve_locally=True,
)
app.title = 'Dashboard de Métricas (Full)'

PROJECT_BOTTLENECK_PREFIX = {
    'W1NNER': 'w1nner-downstream',
    'S1NC': 's1nc-downstream',
    'BF': 'befinance-downstream',
    'BEFINANCE': 'befinance-downstream',
    'DT': 'dataanalytics-downstream',
    'DATA&ANALYTICS': 'dataanalytics-downstream',
    'DATA&ANALITICS': 'dataanalytics-downstream',
}

PROJECT_BITBUCKET_PREFIX = {
    'W1NNER': 'w1nner',
    'S1NC': 's1nc',
    'BF': 'befinance',
    'BEFINANCE': 'befinance',
    'DT': 'dataanalytics',
    'DATA&ANALYTICS': 'dataanalytics',
    'DATA&ANALITICS': 'dataanalytics',
}

DOWNSTREAM_METADATA_COLUMNS = {
    'ID', 'Link', 'Title', 'Tipo de Problema', 'Prioridade', 'Versões de correção',
    'Versões afetadas', 'Componentes', 'Responsável', 'Criador', 'Space', 'Resolução',
    'Data Cancelled', 'Etiquetas', 'Blocked Days', 'Blocked', 'Flagged', 'Story Points',
    'Story point estimate', 'Organizations', 'Sprints', 'Principal', 'Epic Name',
    'Team', 'Expected deliverables', 'B.U.', 'Checklist Completed', 'Ready', 'Build',
    'Afeta as versões', 'Change type'
}

CREATOR_FILTER_COLUMN_CANDIDATES = [
    'Criador', 'Creator', 'Created By', 'CreatedBy', 'Reporter', 'Autor'
]
CREATION_DATE_COLUMN_CANDIDATES = [
    'DataCriacao', 'DataCriacaoID', 'Created', 'CreatedDate', 'IssueCreated'
]
FILTER_DATE_CREATED_VALUE = 'created'
DOWNSTREAM_METADATA_CACHE = {}

LEAD_TIME_END_STAGE_CANDIDATES = [
    'Itens concluídos', 'Itens concluidos', 'Done', 'Concluído', 'Concluido', 'ready for production'
]

LEAD_TIME_START_STAGE_PREFERENCES = [
    'Ready to Start', 'In progress', 'Development', 'Ready', 'To Do', 'Discovery'
]

LEAD_TIME_BACKLOG_LIKE_STAGE_NAMES = {
    'backlog',
    'triagem',
    'to do',
    'todo',
    'discovery',
}

# Default stages considered "active WIP" for the Etapa de Fluxo filter.
WIP_FLOW_STAGE_DEFAULTS = [
    'ready to start', 'in progress', 'ready to code review', 'code review',
]

PORTFOLIO_CACHE_TTL = timedelta(minutes=10)
PORTFOLIO_CACHE = {
    'fetched_at': None,
    'data': None,
    'df': None,
    'error': None,
    'source_file': None,
    'source_mtime': None,
}
CAPEX_CACHE_TTL = timedelta(minutes=10)
CAPEX_CACHE = {
    'fetched_at': None,
    'data': None,
    'raw_df': None,
    'summary_df': None,
    'error': None,
    'raw_file': None,
    'raw_mtime': None,
    'summary_file': None,
    'summary_mtime': None,
}
GMUD_CACHE_TTL = timedelta(minutes=10)
GMUD_CACHE = {
    'index': {'fetched_at': None, 'df': None, 'error': None, 'source_file': None, 'source_mtime': None},
    'weekly': {'fetched_at': None, 'df': None, 'error': None, 'source_file': None, 'source_mtime': None},
    'items': {'fetched_at': None, 'df': None, 'error': None, 'source_file': None, 'source_mtime': None},
}
PORTFOLIO_CSV_PREFIX = 'portfolio-bt-ns-'
PORTFOLIO_TAB_VALUE = 'tab-portfolio'
PORTFOLIO_EXTRA_ONEPAGE_TAG = 'extra onepage'
PROJECT_FILTER_ALL_VALUE = '__ALL_PROJECTS__'
PROJECT_FILTER_ALL_LABEL = 'Todos os times'
ORIGINAL_JIRA_TYPE_FILTER_ALL_VALUE = '__ALL_ORIGINAL_JIRA_TYPES__'
ORIGINAL_JIRA_TYPE_FILTER_ALL_LABEL = 'Todos os tipos'
SERVICE_TABS = [
    ('Serviço e SLA', 'tab-performance'),
    ('Cobertura GMUD', 'tab-gmud'),
    ('Process Mining Jira', 'tab-process-mining-jira'),
    ('Painel Fluxo', 'tab-painel-3x3'),
    ('Lead Time', 'tab-lead-time'),
    ('CFD', 'tab-cfd'),
    ('Saúde do Fluxo', 'tab-saude'),
    ('Análise Fluxo', 'tab-analise-fluxo'),
    ('Tendências', 'tab-tendencias'),
    ('Throughput Breakdown', 'tab-throughput-breakdown'),
    ('Padrões Sistêmicos', 'tab-padroes'),
    ('Work Item Age', 'tab-work-item-age'),
    ('WIP por Pessoa', 'tab-wip'),
    ('Produtividade Dev', 'tab-produtividade-dev'),
    ('Estatística Descritiva', 'tab-estatistica'),
    ('Capacidade de Fila', 'tab-fila-capacidade'),
    ('Indicadores Corporativos', 'tab-corporativo'),
]
SERVICE_TAB_VALUES = {value for _, value in SERVICE_TABS}
INTERNAL_SERVICE_TAB_VALUES = SERVICE_TAB_VALUES | {
    'tab-estabilidade',
    'tab-qualidade',
    'tab-dim',
    'tab-tipos',
    'tab-eficiencia',
}


def build_service_tabs():
    return [
        dcc.Tab(
            label=label,
            value=value,
            className='service-tab',
            selected_className='service-tab service-tab--selected',
        )
        for label, value in SERVICE_TABS
    ]


def build_portfolio_tab():
    return [dcc.Tab(label='Portfólio', value=PORTFOLIO_TAB_VALUE)]
PORTFOLIO_CSV_SUFFIX = '-data.csv'
PORTFOLIO_PENDING_BUCKET_1 = 'Pendências 0-15d'
PORTFOLIO_PENDING_BUCKET_2 = 'Pendências 16-30d'
PORTFOLIO_PENDING_BUCKET_3 = 'Pendências +30d'
PORTFOLIO_COLOR_THRESHOLDS = {
    PORTFOLIO_PENDING_BUCKET_1: {'green_max': 2, 'yellow_max': 8},
    PORTFOLIO_PENDING_BUCKET_2: {'green_max': 1, 'yellow_max': 5},
    PORTFOLIO_PENDING_BUCKET_3: {'green_max': 0, 'yellow_max': 3},
    'aging_us_20': {'green_max': 0, 'yellow_max': 5},
    'aging_features_40': {'green_max': 0, 'yellow_max': 8},
    'aging_us_comp_20': {'green_max': 0, 'yellow_max': 5},
    'aging_features_comp_40': {'green_max': 0, 'yellow_max': 8},
}
PORTFOLIO_ROADMAP_QUARTERS_2026 = ['Q1-2026', 'Q2-2026', 'Q3-2026', 'Q4-2026']
PORTFOLIO_ROADMAP_STATUS_ORDER = ['Running', 'Planning', 'Done', 'Paused']
PORTFOLIO_ROADMAP_STATUS_COLORS = {
    'Running': '#8ec7cf',
    'Planning': '#d5c6dc',
    'Done': '#97c95c',
    'Paused': '#e4d8ad',
}

DEFAULT_PATTERN_RULES = {
    "urgencia_cronica": {"expedite_pct_min": 25.0, "flow_pressure_min": 1.0, "failure_demand_pct_min": 30.0},
    "burnout": {"expedite_pct_min": 30.0, "flow_pressure_min": 1.15, "failure_demand_pct_min": 35.0},
    "confianca_comprometida": {"predictability_ratio_min": 2.2, "lead_time_p85_min": 15.0, "failure_demand_pct_min": 30.0},
    "problema_sistemico_fluxo": {"wip_tp_ratio_min": 2.0, "blocked_rate_min": 12.0, "flow_pressure_min": 1.0},
    "atrasos_desperdicios": {"discard_rate_min": 8.0, "blocked_rate_min": 10.0, "wip_age_over_p85_min": 1.1},
    "estagnacao": {"wip_tp_ratio_min": 3.0, "wip_age_over_p85_min": 1.3, "flow_pressure_min": 1.05},
    "compromisso_prematuro": {"flow_pressure_min": 1.1, "wip_tp_ratio_min": 2.2, "predictability_ratio_min": 2.0},
}

PATTERN_ACTIONS = {
    "Times operando em estado de urgência": (
        "Revisar política de Highest: limitar a 1 item ativo por vez. "
        "Investigar a causa raiz dos expedites — são falhas de processo upstream ou comprometimentos comerciais sem base? "
        "Separar demanda failure da fila principal e tratar com fluxo dedicado."
    ),
    "Times em processo de burnout": (
        "Congelar novas entradas imediatamente. "
        "Redistribuir carga ou adicionar capacidade temporária nos gargalos identificados. "
        "Priorizar conclusão sobre início de trabalho novo até WIP cair abaixo do limite seguro."
    ),
    "Times comprometendo a confiança do cliente": (
        "Revisar e comunicar o lead time de referência realista com o cliente. "
        "Aumentar frequência de atualização proativa em itens com prazo em risco. "
        "Identificar e atacar a principal fonte de variabilidade no lead time (dependências, retrabalho ou tamanho de itens)."
    ),
    "Times com problemas sistêmicos de fluxo": (
        "Limitar WIP imediatamente — nenhum item novo começa enquanto a fila não reduzir. "
        "Fazer swarming nos itens bloqueados: designar responsável e dar prazo de desbloqueio. "
        "Revisar o critério de entrada no fluxo para cortar demanda inadequada."
    ),
    "Times com atrasos e desperdícios": (
        "Auditar a fila de descarte: por que trabalho foi iniciado e não entregue? "
        "Tornar bloqueios visíveis no quadro e resolver um por um antes de puxar novo trabalho. "
        "Revisar Definition of Ready para evitar que itens imaturos entrem no fluxo."
    ),
    "Times estagnados": (
        "Fazer retrospectiva de fluxo focada em: o que está preso e por quê? "
        "Reduzir tamanho médio dos itens para aumentar cadência e visibilidade de progresso. "
        "Investigar se há dependências externas não mapeadas que travam a entrega."
    ),
    "Times com compromisso prematuro": (
        "Revisar o processo de aceite de demanda — não comprometer prazo sem capacidade confirmada. "
        "Implementar política pull explícita: demanda só entra quando há slot disponível. "
        "Usar dados históricos de lead time para fazer promessas com base em probabilidade, não em estimativas."
    ),
}


# TYPE_SUPPORT, TYPE_ISSUES, TYPE_DEV, TYPE_OTHER — imported from dashboards.core above
THROUGHPUT_BREAKDOWN_PRODUCT_ORDER = ['S1NC', 'W1NNER', 'BF', 'DT']
THROUGHPUT_BREAKDOWN_PRODUCT_LABELS = {
    'S1NC': 'S1NC',
    'W1NNER': 'W1NNER',
    'BF': 'BEFINANCE',
    'DT': 'DATA&ANALYTICS',
}
THROUGHPUT_BREAKDOWN_MONTH_ABBR = {
    1: 'jan.',
    2: 'fev.',
    3: 'mar.',
    4: 'abr.',
    5: 'mai.',
    6: 'jun.',
    7: 'jul.',
    8: 'ago.',
    9: 'set.',
    10: 'out.',
    11: 'nov.',
    12: 'dez.',
}










# ---------------------------------------------------------------------------
# People/identity functions — imported from dashboards.people.config
# (see dashboards/people/config.py)
# ---------------------------------------------------------------------------


























# ── T-shirt size → Story Points equivalência ──────────────────────────────────
# Equaliza estimativas em SP e T-shirt para um peso único de complexidade.
# Mapeamento baseado em convenções comuns de times ágeis:
#   XS/XP = 1 SP | P/S = 2 SP | M = 5 SP | G/L = 8 SP | GG/XL = 13 SP | XGG/XXL = 21 SP
# Fonte: Kitchenham & Mendes (TSE 2004) — AdjustedSize combinando múltiplas medidas.
_TSHIRT_TO_SP_EQUIV: dict = {
    'xs': 1.0, 'xp': 1.0,
    'p': 2.0, 's': 2.0, 'small': 2.0, 'pequeno': 2.0,
    'm': 5.0, 'medium': 5.0, 'médio': 5.0, 'medio': 5.0,
    'g': 8.0, 'l': 8.0, 'large': 8.0, 'grande': 8.0,
    'gg': 13.0, 'xl': 13.0, 'xg': 13.0, 'x-large': 13.0, 'muito grande': 13.0,
    'xgg': 21.0, 'xxl': 21.0, 'xxg': 21.0,
}




































load_env_file('.env', overwrite=False)
load_env_file('.env.local', overwrite=False)
load_env_file('jira_env.txt', overwrite=False)
load_env_file('jira-env.txt', overwrite=False)














PATTERN_RULES = load_pattern_rules()
DEFAULT_WEEKLY_WIP_ITEMS_PER_PERSON_LIMIT = float(os.getenv('FLOW_WEEKLY_WIP_ITEMS_PER_PERSON_LIMIT', '2').strip() or '2')
DEFAULT_EXPEDITE_TARGET_PCT = float(os.getenv('FLOW_EXPEDITE_TARGET_PCT', '20').strip() or '20')
DEFAULT_EXPEDITE_CRITICAL_PCT = float(os.getenv('FLOW_EXPEDITE_CRITICAL_PCT', '30').strip() or '30')
DEFAULT_VARIABILITY_CV_WARN = float(os.getenv('FLOW_VARIABILITY_CV_WARN', '0.30').strip() or '0.30')
DEFAULT_VARIABILITY_CV_CRITICAL = float(os.getenv('FLOW_VARIABILITY_CV_CRITICAL', '0.50').strip() or '0.50')






















































































































































































# SLA de referência por tipo de item
# Chaves canônicas das 4 categorias — configuráveis via FLOW_PMO_TYPE_SLA_DAYS no .env
_TYPE_SLA_DEFAULTS = {'bug': 5, 'historia': 15, 'feature': 30, 'epico': 90}
_TYPE_CATEGORY_ORDER = ['bug', 'historia', 'feature', 'epico']
_TYPE_SLA_DISPLAY_LABELS = {
    'bug': 'Bug / Suporte',
    'historia': 'Histórias',
    'feature': 'Features',
    'epico': 'Épicos',
}
# Mapa de TipoNorm (Jira) → chave canônica de categoria
_TYPE_NORM_TO_CATEGORY = {
    'bug': 'bug', 'bugs': 'bug', 'defeito': 'bug', 'defeitos': 'bug',
    'issue': 'bug', 'issues': 'bug', 'problema': 'bug', 'problemas': 'bug',
    'suporte': 'bug', 'support': 'bug',
    # WorkItemSubType composto gerado pelo pipeline (Issues/Defeitos/Problemas)
    'issues/defeitos/problemas': 'bug',
    'historia': 'historia', 'historias': 'historia', 'story': 'historia',
    'us': 'historia', 'user story': 'historia', 'userstory': 'historia',
    'user_story': 'historia', 'tarefa': 'historia', 'task': 'historia',
    'feature': 'feature', 'features': 'feature',
    'funcionalidade': 'feature', 'funcionalidades': 'feature',
    'epic': 'epico', 'epico': 'epico', 'epicos': 'epico',
}


















build_service_throughput_breakdown = lambda done_df, dimension_col, dimension_label, start_ts, end_ts, bucket_freq='W-MON': build_throughput_series(done_df, dimension_col, dimension_label, temporal=True, start_ts=start_ts, end_ts=end_ts, bucket_freq=bucket_freq)






build_throughput_breakdown = lambda df, dimension_col, dimension_label: build_throughput_series(df, dimension_col, dimension_label)



















































# Prefixo de arquivo de process mining por projeto
_PM_FILE_PREFIX_MAP = {
    'W1NNER': 'w1nner',
    'W1NNR':  'w1nner',
    'S1NC':   's1nc',
    'W1SFT':  's1nc',
    'BEFINANCE': 'befinance',
    'BF':        'befinance',
    'DATA&ANALYTICS': 'dataanalytics',
    'DATA ANALYTICS': 'dataanalytics',
    'DT': 'dataanalytics',
    'DA': 'dataanalytics',
}

_PM_SHEET_CSV_SLUG_MAP = {
    'ResumoConformidade': 'conformidade_resumo',
    'ConformidadeCasos': 'conformidade_casos',
    'RetrabalhoItens': 'retrabalho_itens',
    'RetornoDevLoops': 'retorno_dev_loops',
    'TemposPorStatus': 'tempos_status',
    'VazaoPessoaSemanal': 'vazao_pessoa_semanal',
    'VazaoPessoaResumo': 'vazao_pessoa_resumo',
    'HorasPessoaResumo': 'horas_pessoa_resumo',
    'HorasPessoaStatus': 'horas_pessoa_status',
    'DevFlowResumo': 'dev_flow_summary',
    'DevFlowItens': 'dev_flow_items',
    'DevFlowRetornos': 'dev_flow_returns',
    'VariantesTop': 'variantes_top',
    'EventosFiltrados': 'eventos_filtrados',
    'PM4PyDFGEdges': 'pm4py_dfg_edges',
    'PM4PyDFGPerfEdges': 'pm4py_dfg_perf_edges',
    'PM4PyTBRResumo': 'pm4py_tbr_summary',
    'PM4PyTBRCasos': 'pm4py_tbr_cases',
    'Metadados': 'metadados',
}




















_PM_PORTFOLIO_PRODUCT_SPECS = (
    {'project_key': 'BF', 'product': 'BeFinance', 'color': '#e67e22'},
    {'project_key': 'DT', 'product': 'Data&Analytics', 'color': '#1abc9c'},
    {'project_key': 'S1NC', 'product': 'Sync', 'color': '#9b59b6'},
    {'project_key': 'W1NNER', 'product': 'W1nner', 'color': '#3498db'},
)

_PM_PORTFOLIO_CANONICAL_PROJECT_MAP = {
    'BF': 'BF',
    'BEFINANCE': 'BF',
    'BE FINANCE': 'BF',
    'DT': 'DT',
    'DA': 'DT',
    'DADOS': 'DT',
    'DATA ANALYTICS': 'DT',
    'DATA&ANALYTICS': 'DT',
    'S1NC': 'S1NC',
    'W1SFT': 'S1NC',
    'SYNC': 'S1NC',
    'W1NNR': 'W1NNER',
    'W1NNER': 'W1NNER',
    'WINNER': 'W1NNER',
}

_PM_EXECUTION_INCLUDE_TOKENS = (
    'in progress',
    'development',
    'desenvolvimento',
    'code review',
    'review',
    'testing',
    'qa',
    'homolog',
    'validation',
    'validacao',
)

_PM_EXECUTION_EXCLUDE_TOKENS = (
    'backlog',
    'triagem',
    'triage',
    'discovery',
    'planning',
    'refinement',
    'refinamento',
    'grooming',
    'to do',
    'todo',
    'cancel',
    'done',
    'conclu',
    'closed',
)

_PM_PORTFOLIO_ASSET_TYPES = frozenset({
    'epic',
    'epico',
    'feature',
    'funcionalidade',
    'story',
    'user story',
    'historia',
    'historia de usuario',
})














# ── Touch Time — Triangulação de Estimativas (3 Modelos) ─────────────────────



































_PM_DEV_STATUS_NAMES = frozenset({
    'in progress',
    'in development',
    'em desenvolvimento',
    'em andamento',
    'desenvolvimento',
    'development',
    'doing',
    'wip',
})
_PM_QA_STATUS_HINTS = ('qa', 'test', 'homolog', 'valid')


















# Statuses terminais excluídos da identificação de gargalos
_TERMINAL_STATUS_HINTS = {
    'done', 'concluido', 'concluído', 'cancelled', 'cancelado', 'closed',
    'fechado', 'rejected', 'won\'t do', 'wont do', 'backlog', 'to do',
}

























fato['TipoDemanda'] = fato.apply(
    lambda row: canonicalize_demand_type(row.get('Tipo'), row.get('WorkItemSubType')),
    axis=1
)
fato['TipoOriginalJira'] = fato.apply(
    lambda row: canonicalize_original_jira_type(row.get('WorkItemSubType'), row.get('Tipo')),
    axis=1
)















creator_filter_options = get_creator_filter_options_for_project()
done_date_defaults = pd.to_datetime(fato['DataDone'], errors='coerce') if 'DataDone' in fato.columns else pd.Series(dtype='datetime64[ns]')
creation_date_defaults = resolve_creation_date_series(fato)
date_min_candidates = [series.min() for series in [done_date_defaults, creation_date_defaults] if not series.dropna().empty]
date_max_candidates = [series.max() for series in [done_date_defaults, creation_date_defaults] if not series.dropna().empty]
min_date = min(date_min_candidates) if date_min_candidates else pd.to_datetime('2023-01-01')
max_date = max(date_max_candidates) if date_max_candidates else pd.to_datetime('today')

_deploy_version = os.environ.get('BITBUCKET_COMMIT') or 'Local'
_deploy_version_display = _deploy_version[:7] if len(_deploy_version) > 7 and _deploy_version != 'Local' else _deploy_version

app.layout = html.Div([
    dcc.Store(id='main-view', data='home'),
    html.Div([
        html.H1('Dashboard de Métricas - Full', style={'margin': '0'}),
        html.Span(
            f'Última carga processada: {LAST_PROCESSED_LOAD_LABEL} | Versão: {_deploy_version_display}',
            style={
                'fontSize': '14px',
                'color': '#555',
                'backgroundColor': '#f3f4f6',
                'padding': '6px 10px',
                'borderRadius': '999px',
                'whiteSpace': 'nowrap'
            }
        ),
    ], style={
        'display': 'flex',
        'justifyContent': 'center',
        'alignItems': 'center',
        'gap': '12px',
        'flexWrap': 'wrap',
        'marginBottom': '12px'
    }),
    html.Div(
        id='main-menu-panel',
        children=[
            html.H3('Tela Principal', style={'marginTop': '0', 'marginBottom': '8px'}),
            html.P(
                'Escolha o módulo que deseja acessar.',
                style={'marginTop': '0', 'color': '#555'}
            ),
            html.Div([
                html.Button(
                    'Portfólio',
                    id='btn-menu-portfolio',
                    n_clicks=0,
                    style={
                        'padding': '0 24px',
                        'height': '64px',
                        'fontWeight': 'bold',
                        'fontSize': '16px',
                        'lineHeight': '1.2',
                        'borderRadius': '14px',
                        'border': '2px solid #0b5cab',
                        'backgroundColor': '#e9f2ff',
                        'color': '#0b3d75',
                        'cursor': 'pointer',
                        'minWidth': '280px',
                        'flex': '1 1 280px',
                        'maxWidth': '340px',
                        'textAlign': 'center',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'boxShadow': '0 6px 14px rgba(11, 92, 171, 0.10)',
                    }
                ),
                html.Button(
                    'Serviços (Value Stream)',
                    id='btn-menu-services',
                    n_clicks=0,
                    style={
                        'padding': '0 24px',
                        'height': '64px',
                        'fontWeight': 'bold',
                        'fontSize': '16px',
                        'lineHeight': '1.2',
                        'borderRadius': '14px',
                        'border': '2px solid #0f766e',
                        'backgroundColor': '#ecfdf5',
                        'color': '#115e59',
                        'cursor': 'pointer',
                        'minWidth': '280px',
                        'flex': '1 1 280px',
                        'maxWidth': '340px',
                        'textAlign': 'center',
                        'display': 'flex',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'boxShadow': '0 6px 14px rgba(15, 118, 110, 0.10)',
                    }
                ),
            ], style={
                'display': 'flex',
                'gap': '14px',
                'flexWrap': 'wrap',
                'justifyContent': 'center',
                'alignItems': 'center',
                'width': '100%',
                'maxWidth': '720px',
                'margin': '8px auto 0 auto',
            }),
        ],
        style={
            'maxWidth': '760px',
            'margin': '0 auto 16px auto',
            'padding': '20px',
            'border': '1px solid #e5e7eb',
            'borderRadius': '14px',
            'backgroundColor': '#fafafa',
            'textAlign': 'center',
            'boxShadow': '0 4px 14px rgba(0,0,0,0.04)',
            'display': 'flex',
            'flexDirection': 'column',
            'alignItems': 'center',
        }
    ),
    html.Div(
        id='main-nav-panel',
        children=[
            html.Button(
                'Voltar ao menu principal',
                id='btn-menu-home',
                n_clicks=0,
                style={
                    'padding': '8px 12px',
                    'borderRadius': '8px',
                    'border': '1px solid #d1d5db',
                    'backgroundColor': '#fff',
                    'cursor': 'pointer'
                }
            ),
            html.Span(id='main-nav-context', style={'fontWeight': 'bold', 'color': '#374151'}),
        ],
        style={
            'display': 'none',
            'justifyContent': 'center',
            'alignItems': 'center',
            'gap': '12px',
            'marginBottom': '12px',
            'flexWrap': 'wrap'
        }
    ),
    html.Div([
        html.Div([html.Label('Período:'), dcc.DatePickerRange(id='date-range', start_date=min_date, end_date=max_date,
                                                            display_format='YYYY-MM-DD',
                                                            month_format='MMMM YYYY',
                                                            show_outside_days=True)], style={'display':'inline-block', 'marginRight':'20px'}),
        html.Div([
            html.Label('Time:'),
            dcc.Dropdown(
                id='filter-projeto',
                options=[{'label': PROJECT_FILTER_ALL_LABEL, 'value': PROJECT_FILTER_ALL_VALUE}] + [{'label': p, 'value': p} for p in unique_sorted(fato['Projeto'])],
                value=PROJECT_FILTER_ALL_VALUE,
                clearable=False
            )
        ], style={'width':'20%', 'display':'inline-block'}),
        html.Div([html.Label('Tipo:'), dcc.Dropdown(id='filter-tipo', options=[{'label':t,'value':t} for t in unique_sorted(fato['TipoDemanda'])], value=None, clearable=True)], style={'width':'15%', 'display':'inline-block', 'marginLeft':'20px'}),
        html.Div([html.Label('Tipo original Jira:'), dcc.Dropdown(id='filter-tipo-original-jira', options=[{'label': ORIGINAL_JIRA_TYPE_FILTER_ALL_LABEL, 'value': ORIGINAL_JIRA_TYPE_FILTER_ALL_VALUE}] + [{'label':t,'value':t} for t in ['Épico', 'Feature', 'História', 'Task', 'Bug'] + [v for v in unique_sorted(fato['TipoOriginalJira']) if v not in {'Épico', 'Feature', 'História', 'Task', 'Bug'}]], value=[ORIGINAL_JIRA_TYPE_FILTER_ALL_VALUE], multi=True, clearable=True, placeholder='Selecione um ou mais tipos originais')], style={'width':'15%', 'display':'inline-block', 'marginLeft':'20px'}),
        html.Div([html.Label('Classe Serviço (Prioridade):'), dcc.Dropdown(id='filter-classe-servico', options=[{'label':c,'value':c} for c in unique_sorted(fato['ClasseServico'])], value=None, clearable=True)], style={'width':'16%', 'display':'inline-block', 'marginLeft':'20px'}),
        html.Div([
            html.Label('Responsável:'),
            dcc.Dropdown(
                id='filter-responsavel',
                options=[{'label':r,'value':r} for r in unique_sorted(fato['Responsavel'])],
                value=[],
                multi=True,
                clearable=True,
                placeholder='Selecione um ou mais responsáveis'
            )
        ], style={'width':'18%', 'display':'inline-block', 'marginLeft':'20px'}),
        html.Div([
            html.Label('Criador:'),
            dcc.Dropdown(
                id='filter-criador',
                options=creator_filter_options,
                value=[],
                multi=True,
                clearable=True,
                disabled=not bool(creator_filter_options),
                placeholder='Selecione um ou mais criadores'
            )
        ], style={'width':'24%', 'display':'inline-block', 'marginLeft':'20px', 'minWidth':'260px'}),
        html.Div([
            html.Label('Base do período:'),
            dcc.Checklist(
                id='filter-date-mode',
                options=[{'label': 'Usar data de criação do card', 'value': FILTER_DATE_CREATED_VALUE}],
                value=[],
                inputStyle={'marginRight': '6px'},
                labelStyle={'display': 'inline-flex', 'alignItems': 'center', 'marginTop': '8px'}
            ),
            html.Div(
                'Desmarcado = Data done | Marcado = Data de criação',
                style={'fontSize': '12px', 'color': '#666', 'marginTop': '4px'}
            ),
        ], style={'width':'24%', 'display':'inline-block', 'marginLeft':'20px', 'minWidth':'250px'}),
        html.Div([
            html.Label('Etapas Lead Time (Comprometimento):'),
            dcc.Dropdown(
                id='filter-leadtime-stages',
                options=[],
                value=[],
                multi=True,
                placeholder='Selecione etapas que contam como início do compromisso'
            )
        ], style={'width':'30%', 'display':'inline-block', 'marginLeft':'20px', 'minWidth':'340px'}),
        html.Div([
            html.Label('Etapa de Fluxo (WIP):'),
            dcc.Dropdown(
                id='filter-etapa-fluxo',
                options=[],
                value=[],
                multi=True,
                placeholder='Filtra WIP por etapa atual no fluxo'
            )
        ], style={'width':'28%', 'display':'inline-block', 'marginLeft':'20px', 'minWidth':'300px'}),
        html.Div([
            html.Label('Top N Capacidade:'),
            dcc.Dropdown(
                id='filter-capacity-top-n',
                options=[{'label': str(n), 'value': n} for n in [3, 5, 8, 10, 15, 20]],
                value=5,
                clearable=False
            )
        ], style={'width':'12%', 'display':'inline-block', 'marginLeft':'20px', 'minWidth':'140px'}),
        html.Div([
            html.Label('Métrica semanal (capacidade):'),
            dcc.Dropdown(
                id='filter-capacity-weekly-metric',
                options=[
                    {'label': 'Score Capacidade (%)', 'value': 'score'},
                    {'label': 'Itens Concluídos', 'value': 'itens_concluidos'},
                    {'label': 'Commits', 'value': 'commits'},
                    {'label': 'PRs Abertos', 'value': 'prs_abertos'},
                ],
                value='score',
                clearable=False
            )
        ], style={'width':'16%', 'display':'inline-block', 'marginLeft':'20px', 'minWidth':'220px'}),
        html.Div([
            html.Label('TEAM (Portfólio):'),
            dcc.Dropdown(
                id='filter-portfolio-team',
                options=get_portfolio_project_filter_options(),
                value=PROJECT_FILTER_ALL_VALUE,
                clearable=False
            )
        ], style={'display':'none'}),
        html.Div([
            html.Label('Quarter (Portfólio):'),
            dcc.Dropdown(
                id='filter-portfolio-quarter',
                options=[
                    {'label': 'Todos os Quarters', 'value': 'ALL'},
                    {'label': 'Q1-2026', 'value': 'Q1-2026'},
                    {'label': 'Q2-2026', 'value': 'Q2-2026'},
                    {'label': 'Q3-2026', 'value': 'Q3-2026'},
                    {'label': 'Q4-2026', 'value': 'Q4-2026'},
                ],
                value='ALL',
                clearable=False
            )
        ], style={'width':'16%', 'display':'inline-block', 'marginLeft':'20px', 'minWidth':'180px'}),
        html.Div([
            html.Label('Portfólio: thresholds (backlog/freshness 15,30)'),
            html.Div([
                dcc.Input(id='filter-portfolio-threshold-backlog-15', type='number', value=15, min=0, step=1, style={'width': '70px'}),
                dcc.Input(id='filter-portfolio-threshold-backlog-30', type='number', value=30, min=0, step=1, style={'width': '70px', 'marginLeft': '6px'}),
                dcc.Input(id='filter-portfolio-threshold-fresh-15', type='number', value=15, min=0, step=1, style={'width': '70px', 'marginLeft': '10px'}),
                dcc.Input(id='filter-portfolio-threshold-fresh-30', type='number', value=30, min=0, step=1, style={'width': '70px', 'marginLeft': '6px'}),
            ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap'})
        ], style={'display':'inline-block', 'marginLeft':'20px', 'minWidth':'360px'}),
        html.Div([
            html.Label('Portfólio: fila de decisão (status, ; )'),
            dcc.Input(
                id='filter-portfolio-decision-statuses',
                type='text',
                value='Triagem;Backlog;Business Review;READY FOR DEVELOPMENT',
                debounce=True,
                style={'width':'340px'}
            )
        ], style={'display':'none'}),
        html.Div([
            html.Label('Portfólio: workflow oficial (status, ; )'),
            dcc.Input(
                id='filter-portfolio-workflow-statuses',
                type='text',
                value='Triagem;Backlog;To Do;Todo;Business Review;READY FOR DEVELOPMENT;In Progress;In Progess;Ready;Homolog;Staging;Desenvolvimento;Concluído;Concluída;Done;Closed;Resolved;Cancelled',
                debounce=True,
                style={'width':'480px'}
            )
        ], style={'display':'none'}),
        html.Div([
            html.Label('Portfólio: SLA Aging (JSON tipo/status)'),
            dcc.Input(
                id='filter-portfolio-sla-aging-json',
                type='text',
                value='{\"tipo\":{\"Épico\":30,\"Feature\":20},\"status\":{\"Triagem\":7,\"Backlog\":15,\"Business Review\":10}}',
                debounce=True,
                style={'width':'560px'}
            )
        ], style={'display':'none'}),
        html.Div([
            html.Label('Portfólio: mix alvo por tipo (JSON global/projeto/team)'),
            dcc.Input(
                id='filter-portfolio-target-mix-json',
                type='text',
                value='{\"global\":{\"Épico\":70,\"Feature\":30}}',
                debounce=True,
                style={'width':'560px'}
            )
        ], style={'display':'none'}),
    ], id='filters-panel', style={'display':'flex', 'justifyContent':'center', 'gap':'10px', 'marginBottom':'20px', 'flexWrap':'wrap', 'alignItems':'flex-start'}),

    html.Div(
        dcc.Tabs(
            id='tabs',
            value='tab-performance',
            children=build_service_tabs(),
            mobile_breakpoint=0,
            parent_style={'overflowX': 'auto'},
            className='service-tabs',
            parent_className='service-tabs-parent',
        ),
        id='tabs-wrapper',
        style={'display': 'none'}
    ),

    html.Div(id='tab-content')
])



def optional_input(component_id, component_property):
    """Dash compatibility shim for versions without Input(..., allow_optional=...)."""
    try:
        return Input(component_id, component_property, allow_optional=True)
    except TypeError:
        return Input(component_id, component_property)


# Navigation and filter callbacks extracted to dashboards/callbacks/navigation.py






from dashboards.tabs.renderer import render_tab as _render_tab_impl

@app.callback(
    Output('tab-content', 'children'),
    Input('main-view', 'data'),
    Input('tabs', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input('filter-projeto', 'value'),
    Input('filter-tipo', 'value'),
    Input('filter-tipo-original-jira', 'value'),
    Input('filter-classe-servico', 'value'),
    Input('filter-responsavel', 'value'),
    Input('filter-leadtime-stages', 'value'),
    Input('filter-etapa-fluxo', 'value'),
    Input('filter-capacity-top-n', 'value'),
    Input('filter-capacity-weekly-metric', 'value'),
    Input('filter-portfolio-team', 'value'),
    Input('filter-portfolio-quarter', 'value'),
    Input('filter-portfolio-threshold-backlog-15', 'value'),
    Input('filter-portfolio-threshold-backlog-30', 'value'),
    Input('filter-portfolio-threshold-fresh-15', 'value'),
    Input('filter-portfolio-threshold-fresh-30', 'value'),
    Input('filter-portfolio-decision-statuses', 'value'),
    Input('filter-portfolio-workflow-statuses', 'value'),
    Input('filter-portfolio-sla-aging-json', 'value'),
    Input('filter-portfolio-target-mix-json', 'value'),
    Input('filter-criador', 'value'),
    Input('filter-date-mode', 'value'),
    optional_input('estatistica-lsl', 'value'),
    optional_input('estatistica-usl', 'value'),
    optional_input('corp-periodicity', 'value'),
    optional_input('corp-groupby-product', 'value'),
    optional_input('corp-feature-types', 'value'),
)
@error_boundary(fallback=callback_error_div())
def render_tab(main_view, tab, start_date, end_date, projeto, tipo, tipo_original_jira, classe_servico, responsavel, leadtime_stages, etapa_fluxo=None, capacity_top_n=5, capacity_weekly_metric='score', portfolio_team=PROJECT_FILTER_ALL_VALUE, portfolio_quarter='ALL',
               pf_backlog_15=None, pf_backlog_30=None, pf_fresh_15=None, pf_fresh_30=None,
               pf_decision_statuses=None, pf_workflow_statuses=None, pf_sla_aging_json=None, pf_target_mix_json=None,
               criadores=None, date_filter_mode=None,
               estatistica_lsl=None, estatistica_usl=None,
               corp_periodicity='M', corp_groupby_product='False', corp_feature_types=None):
    return _render_tab_impl(
        main_view, tab, start_date, end_date, projeto, tipo, tipo_original_jira,
        classe_servico, responsavel, leadtime_stages, etapa_fluxo, capacity_top_n,
        capacity_weekly_metric, portfolio_team, portfolio_quarter,
        pf_backlog_15, pf_backlog_30, pf_fresh_15, pf_fresh_30,
        pf_decision_statuses, pf_workflow_statuses, pf_sla_aging_json, pf_target_mix_json,
        criadores, date_filter_mode, estatistica_lsl, estatistica_usl,
        corp_periodicity, corp_groupby_product, corp_feature_types,
    )

# Callbacks extracted to dashboards/callbacks/ — registered below via register_callbacks(app)
# - render_metric_chart, update_cfd_summary_panel → dashboards/callbacks/metrics.py
# - navigation callbacks → dashboards/callbacks/navigation.py

_nav_callbacks.register_callbacks(app)
_metrics_callbacks.register_callbacks(app)


def _is_port_available(port, host='127.0.0.1'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _resolve_dash_runtime_options():
    host = os.getenv('FLOW_PMO_DASH_HOST', '127.0.0.1').strip() or '127.0.0.1'
    raw_port = os.getenv('FLOW_PMO_DASH_PORT', os.getenv('PORT', '8050')).strip()
    try:
        preferred_port = int(raw_port)
    except (TypeError, ValueError):
        preferred_port = 8050
    debug_raw = os.getenv('FLOW_PMO_DASH_DEBUG', '1').strip().lower()
    debug = debug_raw not in {'0', 'false', 'no', 'off'}

    port = preferred_port
    while port < preferred_port + 20 and not _is_port_available(port, host=host):
        port += 1
    if port >= preferred_port + 20:
        raise RuntimeError(
            f'Nenhuma porta livre encontrada entre {preferred_port} e {preferred_port + 19} para iniciar o Dash.'
        )
    if port != preferred_port:
        print(f'Porta {preferred_port} ocupada; iniciando Dash em http://{host}:{port}/')
    return {'host': host, 'port': port, 'debug': debug}


# ---------------------------------------------------------------------------
# 4Ps — callback do botão "Copiar como texto"
# ---------------------------------------------------------------------------
from dash import clientside_callback, ClientsideFunction

clientside_callback(
    """
    function(n_clicks, text) {
        if (!n_clicks || !text) return '';
        try {
            navigator.clipboard.writeText(text);
            return 'Copiado!';
        } catch(e) {
            // fallback para browsers sem clipboard API
            var el = document.createElement('textarea');
            el.value = text;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            return 'Copiado!';
        }
    }
    """,
    Output('four-ps-copy-feedback', 'children'),
    Input('btn-four-ps-copy', 'n_clicks'),
    Input('four-ps-copy-text-store', 'data'),
    prevent_initial_call=True,
)


if __name__ == '__main__':
    app.run(**_resolve_dash_runtime_options())
