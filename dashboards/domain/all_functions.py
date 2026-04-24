"""Domain functions extracted from dashboard_full.py — Sprint 4 (RF-037/RF-038/RF-039/RF-040).

All functions are moved verbatim. Module-level state from dashboard_full
(caches, DataFrames) is accessed lazily via sys.modules at call time.
"""
from __future__ import annotations

import sys as _sys
import os
import json
import math
import hashlib
import re
import platform
import socket
import urllib.request
import urllib.parse
import posixpath
from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import Any, Dict, List
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
try:
    from plotly.subplots import make_subplots
except ImportError:
    from plotly.tools import make_subplots

import dash
try:
    from dash import dcc, html, Input, Output, State, dash_table
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html
    from dash.dependencies import Input, Output, State
    import dash_table
from dash.exceptions import PreventUpdate

from shared.env_utils import load_env_file, parse_json_env
from shared.path_utils import candidate_data_folders, _sanitize_os_path
from shared.text_utils import normalize_text

from jira.client import JiraClient
from jira.four_ps_kanban import FourPsKanbanExtractor

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


def _df():
    """Return dashboard_full module — works when imported or run directly as __main__."""
    return _sys.modules.get('dashboard_full') or _sys.modules['__main__']


WEEK_DATE_RANGE_FREQ = 'W-MON'


WEEK_PERIOD = 'W-SUN'


CFD_SNAPSHOT_FREQ = 'D'


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


def canonicalize_original_jira_type(subtype=None, tipo=None):
    subtype_text = str(subtype or '').strip()
    tipo_text = str(tipo or '').strip()
    subtype_norm = normalize_text(subtype_text)
    tipo_norm = normalize_text(tipo_text)

    if subtype_norm in {'epico', 'epic'} or tipo_norm in {'epico', 'epic'}:
        return 'Épico'
    if subtype_norm == 'feature' or tipo_norm == 'feature':
        return 'Feature'
    if subtype_norm in {'historia', 'story', 'user story', 'userstory'} or tipo_norm in {'historia', 'story', 'user story', 'userstory'}:
        return 'História'
    if subtype_norm in {'ad hoc', 'adhoc', 'ad-hoc'} or tipo_norm in {'ad hoc', 'adhoc', 'ad-hoc'}:
        return 'Ad-hoc'
    if subtype_norm in {'task', 'tarefa'} or tipo_norm in {'task', 'tarefa'}:
        return 'Task'
    if subtype_norm in {'bug', 'issue', 'issues', 'defeito', 'defeitos', 'problema', 'problemas'}:
        return 'Bug'
    if tipo_norm in {'bug', 'issue', 'issues', 'defeito', 'defeitos', 'problema', 'problemas'}:
        return 'Bug'
    if subtype_text:
        return subtype_text
    if tipo_text:
        return tipo_text
    return ''


def classify_original_jira_demand_bucket(tipo_original):
    tipo_norm = normalize_text(tipo_original)
    if tipo_norm in {'epico', 'epic', 'feature', 'historia', 'story', 'user story', 'userstory', 'ad hoc', 'adhoc', 'ad-hoc'}:
        return 'value'
    if tipo_norm in {'bug', 'issue', 'issues', 'defeito', 'defeitos', 'problema', 'problemas', 'suporte', 'support', 'outro', 'other'}:
        return 'failure'
    if tipo_norm in {'task', 'tarefa'}:
        return None
    return None


def is_failure_demand_type(tipo):
    return canonicalize_demand_type(tipo) == TYPE_ISSUES


def _load_bitbucket_prefix_map():
    raw = os.getenv('FLOW_PMO_BITBUCKET_PREFIX_MAP', '').strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    out = {}
    for key, value in parsed.items():
        project_key = str(key).strip().upper()
        prefix = str(value).strip().lower()
        if project_key and prefix:
            out[project_key] = prefix
    return out


def _coerce_story_points_value(raw_value):
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return np.nan
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    text = str(raw_value).strip()
    if not text:
        return np.nan
    text = text.replace(',', '.')
    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return np.nan
    try:
        return float(match.group(0))
    except Exception:
        return np.nan


def _story_points_band(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 'Sem estimativa'
    v = float(value)
    if v <= 0:
        return '0'
    if v <= 1:
        return '1'
    if v <= 3:
        return '2-3'
    if v <= 5:
        return '5'
    if v <= 8:
        return '8'
    return '13+'


def _load_project_bitbucket_csv(project_prefix, suffix):
    if not project_prefix:
        return pd.DataFrame()
    # Chave no mapa de URLs: ex. "w1nner_commits", "befinance_pullrequests"
    url_map = _load_bitbucket_csv_url_map()
    type_name = suffix.lstrip('_').replace('.csv', '')  # "_commits.csv" → "commits"
    map_key = f'{project_prefix.lower()}_{type_name}'
    url = url_map.get(map_key)
    if url:
        try:
            local_path = _download_bitbucket_csv_from_url(url, map_key)
            return pd.read_csv(local_path)
        except Exception:
            pass
    candidates = []
    for folder in _iter_local_data_folders(include_process_mining_artifacts=True):
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low = name.lower()
            if low.startswith(project_prefix.lower()) and low.endswith(suffix):
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    candidates.append(path)
    if not candidates:
        return pd.DataFrame()
    latest = max(candidates, key=os.path.getctime)
    try:
        return pd.read_csv(latest)
    except Exception:
        return pd.DataFrame()


def load_project_bitbucket_logs(projeto):
    project_key = str(projeto or '').strip().upper()
    if not project_key:
        return {'commits': pd.DataFrame(), 'pullrequests': pd.DataFrame(), 'pipelines': pd.DataFrame()}

    env_map = _load_bitbucket_prefix_map()
    prefix = env_map.get(project_key) or PROJECT_BITBUCKET_PREFIX.get(project_key)
    if not prefix:
        return {'commits': pd.DataFrame(), 'pullrequests': pd.DataFrame(), 'pipelines': pd.DataFrame()}

    commits = _load_project_bitbucket_csv(prefix, '_commits.csv')
    pullrequests = _load_project_bitbucket_csv(prefix, '_pullrequests.csv')
    pipelines = _load_project_bitbucket_csv(prefix, '_pipelines.csv')

    if not commits.empty and 'date' in commits.columns:
        commits['date'] = pd.to_datetime(commits['date'], errors='coerce', utc=True).dt.tz_localize(None)
    if not pullrequests.empty:
        if 'created_on' in pullrequests.columns:
            pullrequests['created_on'] = pd.to_datetime(pullrequests['created_on'], errors='coerce', utc=True).dt.tz_localize(None)
        if 'updated_on' in pullrequests.columns:
            pullrequests['updated_on'] = pd.to_datetime(pullrequests['updated_on'], errors='coerce', utc=True).dt.tz_localize(None)
        if 'state' in pullrequests.columns:
            pullrequests['state_norm'] = pullrequests['state'].astype(str).str.strip().str.lower()
    if not pipelines.empty:
        if 'created_on' in pipelines.columns:
            pipelines['created_on'] = pd.to_datetime(pipelines['created_on'], errors='coerce', utc=True).dt.tz_localize(None)
        if 'completed_on' in pipelines.columns:
            pipelines['completed_on'] = pd.to_datetime(pipelines['completed_on'], errors='coerce', utc=True).dt.tz_localize(None)
        if 'state_result' in pipelines.columns and pipelines['state_result'].astype(str).str.strip().ne('').any():
            pipelines['state_norm'] = pipelines['state_result'].astype(str).str.strip().str.lower()
        elif 'state' in pipelines.columns:
            pipelines['state_norm'] = pipelines['state'].astype(str).str.strip().str.lower()
        if 'commit_hash' in pipelines.columns:
            pipelines['commit_hash'] = pipelines['commit_hash'].astype(str).str.strip()

    return {'commits': commits, 'pullrequests': pullrequests, 'pipelines': pipelines}


def compute_bitbucket_contributor_metrics(bitbucket_logs, start_ts, end_ts, alias_index=None):
    commits = bitbucket_logs.get('commits', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    pullrequests = bitbucket_logs.get('pullrequests', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    stats = {}
    reviewed_authors_by_person = {}

    def _ensure_person(raw_name):
        person = _canonical_person_name(raw_name, alias_index=alias_index)
        if not person:
            return None
        key = person.lower()
        if key not in stats:
            stats[key] = {
                'Pessoa': person,
                'PRs Abertos': 0,
                'Aprovacoes': 0,
                'Reprovacoes': 0,
                'PRs Declinados (Autor)': 0,
                'Commits': 0,
                'Devs Revisados': 0,
            }
        reviewed_authors_by_person.setdefault(key, set())
        return key

    if not commits.empty and {'author', 'date'}.issubset(commits.columns):
        commit_window = commits[
            (commits['date'] >= start_ts) &
            (commits['date'] < end_ts)
        ]
        for author_name, count in commit_window['author'].value_counts(dropna=True).items():
            person_key = _ensure_person(author_name)
            if person_key:
                stats[person_key]['Commits'] += int(count)

    if not pullrequests.empty:
        prs = pullrequests.copy()
        if 'created_on' in prs.columns:
            prs_opened_window = prs[(prs['created_on'] >= start_ts) & (prs['created_on'] < end_ts)]
        else:
            prs_opened_window = prs

        for author_name, count in prs_opened_window['author'].value_counts(dropna=True).items():
            person_key = _ensure_person(author_name)
            if person_key:
                stats[person_key]['PRs Abertos'] += int(count)

        if 'state_norm' in prs.columns:
            if 'updated_on' in prs.columns:
                decline_window = prs[(prs['updated_on'] >= start_ts) & (prs['updated_on'] < end_ts)]
            else:
                decline_window = prs_opened_window
            decline_window = decline_window[decline_window['state_norm'] == 'declined']
            for author_name, count in decline_window['author'].value_counts(dropna=True).items():
                person_key = _ensure_person(author_name)
                if person_key:
                    stats[person_key]['PRs Declinados (Autor)'] += int(count)

        review_window = prs_opened_window
        if 'updated_on' in prs.columns:
            review_window = prs[(prs['updated_on'] >= start_ts) & (prs['updated_on'] < end_ts)]
        for _, row in review_window.iterrows():
            reviewed_author = _canonical_person_name(row.get('author'), alias_index=alias_index)
            reviewed_author_key = reviewed_author.lower() if reviewed_author else None
            reviewers_in_pr = set()
            for approver in _split_people_field(row.get('approved_by')):
                person_key = _ensure_person(approver)
                if person_key:
                    stats[person_key]['Aprovacoes'] += 1
                    if reviewed_author_key and person_key != reviewed_author_key:
                        reviewers_in_pr.add(person_key)
            for rejector in _split_people_field(row.get('changes_requested_by')):
                person_key = _ensure_person(rejector)
                if person_key:
                    stats[person_key]['Reprovacoes'] += 1
                    if reviewed_author_key and person_key != reviewed_author_key:
                        reviewers_in_pr.add(person_key)
            if reviewed_author:
                for reviewer_key in reviewers_in_pr:
                    reviewed_authors_by_person.setdefault(reviewer_key, set()).add(reviewed_author)

    if not stats:
        return pd.DataFrame(), {}

    for person_key, reviewed_people in reviewed_authors_by_person.items():
        if person_key in stats:
            stats[person_key]['Devs Revisados'] = len(reviewed_people)

    df_metrics = pd.DataFrame(stats.values())
    df_metrics['Total Contribuicoes'] = (
        df_metrics['PRs Abertos'] +
        df_metrics['Aprovacoes'] +
        df_metrics['Reprovacoes'] +
        df_metrics['PRs Declinados (Autor)'] +
        df_metrics['Commits']
    )

    # ── PR Cycle Time e PR Size por autor ─────────────────────────────────────
    # PR Cycle Time: mediana de horas entre created_on → updated_on para PRs merged no período.
    # PR Size Mediana (LOC): mediana de lines_changed_total para PRs merged por autor.
    # Ambos calculados apenas para PRs com state merged para evitar PRs abertos/declined
    # que naturalmente têm duração de ciclo inflada ou tamanho incompleto.
    if not pullrequests.empty and 'created_on' in pullrequests.columns and 'updated_on' in pullrequests.columns:
        _pr_merged = pullrequests.copy()
        if 'state_norm' in _pr_merged.columns:
            _pr_merged = _pr_merged[_pr_merged['state_norm'] == 'merged']
        elif 'state' in _pr_merged.columns:
            _pr_merged = _pr_merged[_pr_merged['state'].astype(str).str.lower() == 'merged']
        # Filtra por janela de tempo (merged_on = updated_on para PRs merged)
        _pr_merged = _pr_merged[
            (_pr_merged['updated_on'] >= start_ts) & (_pr_merged['updated_on'] < end_ts)
        ] if not _pr_merged.empty else _pr_merged

        if not _pr_merged.empty and 'author' in _pr_merged.columns:
            _pr_merged = _pr_merged.copy()
            _pr_merged['_cycle_h'] = (
                pd.to_datetime(_pr_merged['updated_on'], errors='coerce') -
                pd.to_datetime(_pr_merged['created_on'], errors='coerce')
            ).dt.total_seconds() / 3600.0
            _pr_merged['_cycle_h'] = _pr_merged['_cycle_h'].clip(lower=0)

            _pr_merged['_author_norm'] = _pr_merged['author'].apply(
                lambda x: _canonical_person_name(x, alias_index=alias_index)
            )
            _pr_merged = _pr_merged[_pr_merged['_author_norm'].notna() & (_pr_merged['_author_norm'] != '')]

            _cycle_median = _pr_merged.groupby('_author_norm')['_cycle_h'].median().round(1)
            _person_map = df_metrics.set_index('Pessoa')

            def _lookup_cycle(pessoa):
                canonical = _canonical_person_name(pessoa, alias_index=alias_index)
                return float(_cycle_median.get(canonical, np.nan))

            df_metrics['PR Cycle Time Mediano (h)'] = df_metrics['Pessoa'].apply(_lookup_cycle)

            if 'lines_changed_total' in _pr_merged.columns:
                _pr_merged['lines_changed_total'] = pd.to_numeric(
                    _pr_merged['lines_changed_total'], errors='coerce'
                )
                _size_median = _pr_merged.groupby('_author_norm')['lines_changed_total'].median().round(0)
                df_metrics['PR Size Mediana (LOC)'] = df_metrics['Pessoa'].apply(
                    lambda p: float(_size_median.get(_canonical_person_name(p, alias_index=alias_index), np.nan))
                )
            else:
                df_metrics['PR Size Mediana (LOC)'] = np.nan
        else:
            df_metrics['PR Cycle Time Mediano (h)'] = np.nan
            df_metrics['PR Size Mediana (LOC)'] = np.nan
    else:
        df_metrics['PR Cycle Time Mediano (h)'] = np.nan
        df_metrics['PR Size Mediana (LOC)'] = np.nan

    df_metrics = df_metrics.sort_values(
        ['PRs Abertos', 'Aprovacoes', 'Commits', 'Reprovacoes', 'PRs Declinados (Autor)', 'Pessoa'],
        ascending=[False, False, False, False, False, True]
    ).reset_index(drop=True)
    return df_metrics, {
        'PRs Abertos': int(df_metrics['PRs Abertos'].sum()),
        'Aprovacoes': int(df_metrics['Aprovacoes'].sum()),
        'Reprovacoes': int(df_metrics['Reprovacoes'].sum()),
        'PRs Declinados (Autor)': int(df_metrics['PRs Declinados (Autor)'].sum()),
        'Commits': int(df_metrics['Commits'].sum()),
        'Devs Revisados': int(df_metrics['Devs Revisados'].sum()) if 'Devs Revisados' in df_metrics.columns else 0,
    }


def compute_bitbucket_temporal_metrics(bitbucket_logs, start_ts, end_ts, alias_index=None, freq='M'):
    """Computes per-person per-period Bitbucket metrics.

    Returns a DataFrame with columns:
        Pessoa | Período | Commits | PRs Abertos | PRs Merged | PRs Declinados | Aprovações | Reprovações

    freq: 'M' = monthly (first day of month), 'W' = weekly (Monday start)
    """
    commits_raw = bitbucket_logs.get('commits', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    prs_raw = bitbucket_logs.get('pullrequests', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()

    def _period_start(dt):
        if pd.isna(dt):
            return None
        ts = pd.Timestamp(dt)
        if freq == 'M':
            return pd.Timestamp(year=ts.year, month=ts.month, day=1)
        else:
            monday = ts - pd.Timedelta(days=ts.weekday())
            return pd.Timestamp(year=monday.year, month=monday.month, day=monday.day)

    data = {}  # (pessoa_lower, period) -> metric dict

    def _rec(pessoa, period):
        if not pessoa or period is None:
            return None
        key = (pessoa.lower(), period)
        if key not in data:
            data[key] = {
                'Pessoa': pessoa, 'Período': period,
                'Commits': 0, 'PRs Abertos': 0, 'PRs Merged': 0,
                'PRs Declinados': 0, 'Aprovações': 0, 'Reprovações': 0,
            }
        return data[key]

    # ── Commits ──────────────────────────────────────────────────────────────
    if not commits_raw.empty and {'author', 'date'}.issubset(commits_raw.columns):
        c = commits_raw[(commits_raw['date'] >= start_ts) & (commits_raw['date'] < end_ts)].copy()
        c['_pessoa'] = c['author'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
        c['_period'] = c['date'].apply(_period_start)
        for _, row in c[c['_pessoa'].notna() & (c['_pessoa'] != '') & c['_period'].notna()].iterrows():
            rec = _rec(row['_pessoa'], row['_period'])
            if rec is not None:
                rec['Commits'] += 1

    # ── Pull Requests ─────────────────────────────────────────────────────────
    if not prs_raw.empty:
        prs = prs_raw.copy()
        date_col = 'created_on' if 'created_on' in prs.columns else None
        update_col = 'updated_on' if 'updated_on' in prs.columns else None

        # PRs Abertos — by created_on
        if date_col:
            pr_open = prs[(prs[date_col] >= start_ts) & (prs[date_col] < end_ts)].copy()
            pr_open['_pessoa'] = pr_open['author'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
            pr_open['_period'] = pr_open[date_col].apply(_period_start)
            for _, row in pr_open[pr_open['_pessoa'].notna() & (pr_open['_pessoa'] != '')].iterrows():
                rec = _rec(row['_pessoa'], row['_period'])
                if rec is not None:
                    rec['PRs Abertos'] += 1

        # PRs Merged / Declined — by updated_on
        if update_col and 'state_norm' in prs.columns:
            pr_closed = prs[(prs[update_col] >= start_ts) & (prs[update_col] < end_ts)].copy()
            pr_closed['_pessoa'] = pr_closed['author'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
            pr_closed['_period'] = pr_closed[update_col].apply(_period_start)
            for _, row in pr_closed[pr_closed['_pessoa'].notna() & (pr_closed['_pessoa'] != '')].iterrows():
                state = str(row.get('state_norm', '')).lower()
                rec = _rec(row['_pessoa'], row['_period'])
                if rec is None:
                    continue
                if state == 'merged':
                    rec['PRs Merged'] += 1
                elif state == 'declined':
                    rec['PRs Declinados'] += 1

        # Aprovações / Reprovações — iterate reviewer columns
        review_col = update_col or date_col
        if review_col:
            pr_rev = prs[(prs[review_col] >= start_ts) & (prs[review_col] < end_ts)].copy()
            pr_rev['_period'] = pr_rev[review_col].apply(_period_start)
            for _, row in pr_rev.iterrows():
                period = row['_period']
                if period is None:
                    continue
                for approver in _split_people_field(row.get('approved_by')):
                    pessoa = _canonical_person_name(approver, alias_index=alias_index)
                    rec = _rec(pessoa, period)
                    if rec is not None:
                        rec['Aprovações'] += 1
                for rejector in _split_people_field(row.get('changes_requested_by')):
                    pessoa = _canonical_person_name(rejector, alias_index=alias_index)
                    rec = _rec(pessoa, period)
                    if rec is not None:
                        rec['Reprovações'] += 1

    if not data:
        return pd.DataFrame()
    return pd.DataFrame(list(data.values())).sort_values(['Pessoa', 'Período']).reset_index(drop=True)


def build_bitbucket_temporal_section(projects, start_ts, end_ts, alias_index=None):
    """Returns an HTML block with monthly + weekly analytical breakdown of Bitbucket metrics per developer."""
    # Load and merge raw logs (dedup by Bitbucket prefix to avoid double-counting W1NNER/S1NC)
    env_map = _load_bitbucket_prefix_map()
    loaded_prefixes = set()
    raw_logs = {'commits': [], 'pullrequests': []}
    for proj in projects:
        proj_key = str(proj).strip().upper()
        prefix = env_map.get(proj_key) or PROJECT_BITBUCKET_PREFIX.get(proj_key, '')
        if prefix and prefix in loaded_prefixes:
            continue
        if prefix:
            loaded_prefixes.add(prefix)
        logs = load_project_bitbucket_logs(proj)
        if not isinstance(logs, dict):
            continue
        for log_name in ('commits', 'pullrequests'):
            df_log = logs.get(log_name, pd.DataFrame())
            if df_log is not None and not df_log.empty:
                raw_logs[log_name].append(df_log.copy())
    merged = {k: pd.concat(v, ignore_index=True) if v else pd.DataFrame() for k, v in raw_logs.items()}

    monthly_df = compute_bitbucket_temporal_metrics(merged, start_ts, end_ts, alias_index, freq='M')
    weekly_df = compute_bitbucket_temporal_metrics(merged, start_ts, end_ts, alias_index, freq='W')

    if monthly_df.empty and weekly_df.empty:
        return html.Div(
            'Sem dados Bitbucket suficientes para gerar breakdown temporal.',
            style={'color': '#aaa', 'fontStyle': 'italic'},
        )

    METRICS = ['Commits', 'PRs Abertos', 'PRs Merged', 'Aprovações', 'Reprovações']
    COLOR_MAP = {
        'Commits': '#1565c0', 'PRs Abertos': '#0288d1', 'PRs Merged': '#2e7d32',
        'PRs Declinados': '#c62828', 'Aprovações': '#6a1b9a', 'Reprovações': '#e65100',
    }
    children = []

    # ── Monthly ──────────────────────────────────────────────────────────────
    if not monthly_df.empty:
        mdf = monthly_df.copy()
        mdf['Período Label'] = mdf['Período'].apply(lambda d: d.strftime('%b/%y').capitalize())
        periods_sorted = sorted(mdf['Período'].unique())
        period_labels = [p.strftime('%b/%y').capitalize() for p in periods_sorted]

        # Top 20 persons by total commits
        person_order = (
            mdf.groupby('Pessoa')['Commits'].sum()
            .sort_values(ascending=False).head(20).index.tolist()
        )

        # Heatmap — commits
        heat_data = mdf[mdf['Pessoa'].isin(person_order)].copy()
        heat_pivot = heat_data.pivot_table(index='Pessoa', columns='Período Label', values='Commits', fill_value=0)
        cols_ord = [lbl for lbl in period_labels if lbl in heat_pivot.columns]
        heat_pivot = heat_pivot[cols_ord]
        heat_pivot = heat_pivot.loc[[p for p in person_order if p in heat_pivot.index]]
        if not heat_pivot.empty:
            fig_heat = go.Figure(go.Heatmap(
                z=heat_pivot.values.tolist(),
                x=heat_pivot.columns.tolist(),
                y=heat_pivot.index.tolist(),
                colorscale='Blues',
                text=[[str(v) if v > 0 else '' for v in row] for row in heat_pivot.values.tolist()],
                texttemplate='%{text}',
                showscale=True,
                hovertemplate='%{y} | %{x}: %{z} commits<extra></extra>',
            ))
            fig_heat.update_layout(
                title='Commits por Desenvolvedor × Mês',
                height=max(300, 34 * len(heat_pivot) + 80),
                margin={'t': 50, 'b': 30, 'l': 10, 'r': 10},
                xaxis={'side': 'top'},
                yaxis={'autorange': 'reversed'},
                paper_bgcolor='white', plot_bgcolor='white',
            )
            children.append(dcc.Graph(figure=fig_heat, config={'displayModeBar': False}))

        # Stacked bar — PRs (Abertos + Merged) per month, top 10 authors
        pr_plot = mdf[mdf['Pessoa'].isin(person_order[:10])].copy()
        pr_long_rows = []
        for _, row in pr_plot.iterrows():
            for metric in ['PRs Abertos', 'PRs Merged', 'PRs Declinados']:
                if row.get(metric, 0) > 0:
                    pr_long_rows.append({'Pessoa': row['Pessoa'], 'Período Label': row['Período Label'], 'Tipo': metric, 'Qtd': row[metric]})
        if pr_long_rows:
            pr_long = pd.DataFrame(pr_long_rows)
            fig_prs = px.bar(
                pr_long,
                x='Período Label', y='Qtd', color='Pessoa', facet_col='Tipo',
                barmode='stack',
                title='PRs por Mês (top 10 devs)',
                category_orders={'Período Label': period_labels, 'Tipo': ['PRs Abertos', 'PRs Merged', 'PRs Declinados']},
                height=320,
            )
            fig_prs.update_layout(margin={'t': 60, 'b': 40}, paper_bgcolor='white', plot_bgcolor='white')
            fig_prs.for_each_annotation(lambda a: a.update(text=a.text.split('=')[-1]))
            children.append(dcc.Graph(figure=fig_prs, config={'displayModeBar': False}))

        # Monthly pivot DataTable
        table_frames = {}
        for metric in METRICS:
            piv = mdf.pivot_table(index='Pessoa', columns='Período Label', values=metric, fill_value=0)
            for col in piv.columns:
                table_frames[f'{col} — {metric}'] = piv[col]

        if table_frames:
            wide = pd.DataFrame(table_frames).reset_index().fillna(0)
            wide.rename(columns={'index': 'Pessoa'}, inplace=True)
            # Ordered columns: all labels × metrics interleaved by time
            ordered_cols = ['Pessoa']
            for lbl in period_labels:
                for metric in METRICS:
                    col = f'{lbl} — {metric}'
                    if col in wide.columns:
                        ordered_cols.append(col)
            # Totals per metric
            total_cols = []
            for metric in METRICS:
                metric_cols = [c for c in wide.columns if c.endswith(f'— {metric}')]
                if metric_cols:
                    wide[f'TOTAL {metric}'] = wide[metric_cols].sum(axis=1)
                    total_cols.append(f'TOTAL {metric}')
            final_cols = ordered_cols + total_cols
            wide = wide[[c for c in final_cols if c in wide.columns]]
            if 'TOTAL Commits' in wide.columns:
                wide = wide.sort_values('TOTAL Commits', ascending=False)

            tbl_cols = []
            for c in wide.columns:
                if c == 'Pessoa':
                    tbl_cols.append({'name': 'Desenvolvedor', 'id': c})
                elif c.startswith('TOTAL '):
                    tbl_cols.append({'name': c, 'id': c, 'type': 'numeric'})
                else:
                    tbl_cols.append({'name': c, 'id': c, 'type': 'numeric'})

            monthly_table = dash_table.DataTable(
                data=wide.to_dict('records'),
                columns=tbl_cols,
                style_cell={
                    'fontSize': '12px', 'padding': '5px 9px',
                    'fontFamily': 'monospace', 'textAlign': 'center',
                    'whiteSpace': 'nowrap',
                },
                style_cell_conditional=[
                    {'if': {'column_id': 'Pessoa'}, 'textAlign': 'left', 'minWidth': '160px', 'fontFamily': 'sans-serif'},
                ],
                style_header={
                    'fontWeight': '700', 'backgroundColor': '#e8f0fe',
                    'fontSize': '11px', 'whiteSpace': 'normal', 'textAlign': 'center',
                },
                style_data_conditional=[
                    {'if': {'column_id': [c for c in wide.columns if c.startswith('TOTAL')]},
                     'backgroundColor': '#f0f4ff', 'fontWeight': '600'},
                ],
                sort_action='native',
                filter_action='native',
                page_size=25,
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
            )
            children.append(html.Div([
                html.H5('Mensal — Tabela Detalhada por Desenvolvedor',
                        style={'marginTop': '16px', 'marginBottom': '8px', 'color': '#1a237e', 'fontWeight': '600'}),
                html.P(
                    'Cada célula = soma de eventos no mês. Colunas "TOTAL" somam todo o período filtrado.',
                    style={'fontSize': '12px', 'color': '#6c757d', 'marginBottom': '8px'},
                ),
                monthly_table,
            ]))

    # ── Weekly ───────────────────────────────────────────────────────────────
    if not weekly_df.empty:
        wdf = weekly_df.copy()
        wdf['Período Label'] = wdf['Período'].apply(lambda d: d.strftime('%d/%b'))
        periods_sorted_w = sorted(wdf['Período'].unique())
        period_labels_w = [p.strftime('%d/%b') for p in periods_sorted_w]

        # Top 15 by commit count
        person_order_w = (
            wdf.groupby('Pessoa')['Commits'].sum()
            .sort_values(ascending=False).head(15).index.tolist()
        )

        # Line chart — commits per person per week
        weekly_commits = wdf[wdf['Pessoa'].isin(person_order_w) & (wdf['Commits'] > 0)].copy()
        if not weekly_commits.empty:
            fig_wk = px.line(
                weekly_commits,
                x='Período Label', y='Commits', color='Pessoa', markers=True,
                title='Commits por Desenvolvedor × Semana',
                category_orders={'Período Label': period_labels_w},
                height=400,
            )
            fig_wk.update_layout(
                margin={'t': 50, 'b': 50}, paper_bgcolor='white', plot_bgcolor='white',
                xaxis_title='Semana (início segunda-feira)', yaxis_title='Commits',
                legend={'orientation': 'h', 'y': -0.2},
            )
            children.append(html.Div([
                html.H5('Semanal — Commits por Desenvolvedor',
                        style={'marginTop': '24px', 'marginBottom': '8px', 'color': '#1a237e', 'fontWeight': '600'}),
                dcc.Graph(figure=fig_wk, config={'displayModeBar': False}),
            ]))

        # Weekly heatmap — commits
        heat_w_data = wdf[wdf['Pessoa'].isin(person_order_w)].pivot_table(
            index='Pessoa', columns='Período Label', values='Commits', fill_value=0
        )
        cols_w_ord = [lbl for lbl in period_labels_w if lbl in heat_w_data.columns]
        heat_w_data = heat_w_data[cols_w_ord]
        heat_w_data = heat_w_data.loc[[p for p in person_order_w if p in heat_w_data.index]]
        if not heat_w_data.empty:
            fig_heat_w = go.Figure(go.Heatmap(
                z=heat_w_data.values.tolist(),
                x=heat_w_data.columns.tolist(),
                y=heat_w_data.index.tolist(),
                colorscale='Greens',
                text=[[str(v) if v > 0 else '' for v in row] for row in heat_w_data.values.tolist()],
                texttemplate='%{text}',
                showscale=True,
                hovertemplate='%{y} | semana %{x}: %{z} commits<extra></extra>',
            ))
            fig_heat_w.update_layout(
                title='Heatmap de Commits — Semana × Desenvolvedor',
                height=max(300, 34 * len(heat_w_data) + 80),
                margin={'t': 50, 'b': 30, 'l': 10, 'r': 10},
                xaxis={'side': 'top', 'tickangle': -45},
                yaxis={'autorange': 'reversed'},
                paper_bgcolor='white', plot_bgcolor='white',
            )
            children.append(dcc.Graph(figure=fig_heat_w, config={'displayModeBar': False}))

        # Weekly DataTable
        METRICS_W = ['Commits', 'PRs Abertos', 'PRs Merged', 'Aprovações']
        table_frames_w = {}
        for metric in METRICS_W:
            piv_w = wdf.pivot_table(index='Pessoa', columns='Período Label', values=metric, fill_value=0)
            for col in piv_w.columns:
                table_frames_w[f'{col} — {metric}'] = piv_w[col]

        if table_frames_w:
            wide_w = pd.DataFrame(table_frames_w).reset_index().fillna(0)
            wide_w.rename(columns={'index': 'Pessoa'}, inplace=True)
            ordered_cols_w = ['Pessoa']
            for lbl in period_labels_w:
                for metric in METRICS_W:
                    col = f'{lbl} — {metric}'
                    if col in wide_w.columns:
                        ordered_cols_w.append(col)
            total_cols_w = []
            for metric in METRICS_W:
                mc = [c for c in wide_w.columns if c.endswith(f'— {metric}')]
                if mc:
                    wide_w[f'TOTAL {metric}'] = wide_w[mc].sum(axis=1)
                    total_cols_w.append(f'TOTAL {metric}')
            final_cols_w = ordered_cols_w + total_cols_w
            wide_w = wide_w[[c for c in final_cols_w if c in wide_w.columns]]
            if 'TOTAL Commits' in wide_w.columns:
                wide_w = wide_w.sort_values('TOTAL Commits', ascending=False)

            tbl_cols_w = []
            for c in wide_w.columns:
                if c == 'Pessoa':
                    tbl_cols_w.append({'name': 'Desenvolvedor', 'id': c})
                else:
                    tbl_cols_w.append({'name': c, 'id': c, 'type': 'numeric'})

            weekly_table = dash_table.DataTable(
                data=wide_w.to_dict('records'),
                columns=tbl_cols_w,
                style_cell={
                    'fontSize': '11px', 'padding': '4px 8px',
                    'fontFamily': 'monospace', 'textAlign': 'center',
                    'whiteSpace': 'nowrap',
                },
                style_cell_conditional=[
                    {'if': {'column_id': 'Pessoa'}, 'textAlign': 'left', 'minWidth': '160px', 'fontFamily': 'sans-serif'},
                ],
                style_header={
                    'fontWeight': '700', 'backgroundColor': '#e8f5e9',
                    'fontSize': '10px', 'whiteSpace': 'normal', 'textAlign': 'center',
                },
                style_data_conditional=[
                    {'if': {'column_id': [c for c in wide_w.columns if c.startswith('TOTAL')]},
                     'backgroundColor': '#f1f8f2', 'fontWeight': '600'},
                ],
                sort_action='native',
                filter_action='native',
                page_size=20,
                style_table={'overflowX': 'auto', 'minWidth': '100%'},
            )
            children.append(html.Div([
                html.H5('Semanal — Tabela Detalhada por Desenvolvedor',
                        style={'marginTop': '16px', 'marginBottom': '8px', 'color': '#1a237e', 'fontWeight': '600'}),
                html.P(
                    'Cada célula = soma de eventos na semana (início segunda-feira). Colunas "TOTAL" somam todo o período.',
                    style={'fontSize': '12px', 'color': '#6c757d', 'marginBottom': '8px'},
                ),
                weekly_table,
            ]))

    return html.Div(children)


def compute_jira_person_capacity_metrics(jira_df, start_ts, end_ts, alias_index=None):
    if jira_df is None or jira_df.empty:
        return pd.DataFrame(), {}
    required = {'Responsavel', 'DataInProgress', 'DataDone'}
    if not required.issubset(jira_df.columns):
        return pd.DataFrame(), {}

    df = jira_df.copy()
    # DevExecutor (autor do PR/commit no Bitbucket) tem prioridade sobre Responsavel (assignee Jira).
    if 'DevExecutor' in df.columns:
        _exec = df['DevExecutor'].astype(str).str.strip()
        _assi = df['Responsavel'].astype(str).str.strip()
        df['Responsavel'] = _exec.where(_exec.ne('') & _exec.ne('nan'), _assi)
    df['Responsavel'] = df['Responsavel'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
    df = df[df['Responsavel'].astype(str).str.strip().ne('')]
    if df.empty:
        return pd.DataFrame(), {}

    done_window = df[
        (df['DataDone'] >= start_ts) &
        (df['DataDone'] < end_ts)
    ].copy()
    started_window = df[
        (df['DataInProgress'] >= start_ts) &
        (df['DataInProgress'] < end_ts)
    ].copy()
    wip_end = df[
        (df['DataInProgress'] < end_ts) &
        ((df['DataDone'] >= end_ts) | pd.isna(df['DataDone']))
    ].copy()

    by_person = pd.DataFrame({'Pessoa': sorted(df['Responsavel'].unique())})
    if by_person.empty:
        return pd.DataFrame(), {}

    by_person['Itens Concluidos'] = by_person['Pessoa'].map(done_window['Responsavel'].value_counts()).fillna(0).astype(int)
    by_person['Itens Iniciados'] = by_person['Pessoa'].map(started_window['Responsavel'].value_counts()).fillna(0).astype(int)
    by_person['WIP no Fim'] = by_person['Pessoa'].map(wip_end['Responsavel'].value_counts()).fillna(0).astype(int)

    lt_done = done_window.copy()
    if 'LeadTime_Selected_Dias' in lt_done.columns:
        lt_done['LeadTime_Selected_Dias'] = pd.to_numeric(lt_done['LeadTime_Selected_Dias'], errors='coerce')
        lt_done = lt_done[lt_done['LeadTime_Selected_Dias'] >= 0]
        by_person['Lead Time Mediano (dias)'] = by_person['Pessoa'].map(
            lt_done.groupby('Responsavel')['LeadTime_Selected_Dias'].median()
        ).fillna(0.0).round(1)
    else:
        by_person['Lead Time Mediano (dias)'] = 0.0

    by_person['Itens com Evidencia Tecnica'] = 0
    by_person['Cobertura Tecnica (%)'] = 0.0

    by_person = by_person.sort_values(
        ['Itens Concluidos', 'Itens Iniciados', 'WIP no Fim', 'Pessoa'],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)
    totals = {
        'Itens Concluidos': int(by_person['Itens Concluidos'].sum()),
        'Itens Iniciados': int(by_person['Itens Iniciados'].sum()),
        'WIP no Fim': int(by_person['WIP no Fim'].sum()),
    }
    return by_person, totals


def compute_cross_source_capacity_metrics(jira_df, bitbucket_logs, start_ts, end_ts):
    alias_index = _load_person_alias_index()
    jira_people_df, jira_totals = compute_jira_person_capacity_metrics(
        jira_df, start_ts, end_ts, alias_index=alias_index
    )
    bb_people_df, bb_totals = compute_bitbucket_contributor_metrics(
        bitbucket_logs, start_ts, end_ts, alias_index=alias_index
    )

    if 'Pessoa' not in jira_people_df.columns:
        jira_people_df = pd.DataFrame(columns=['Pessoa'])
    if 'Pessoa' not in bb_people_df.columns:
        bb_people_df = pd.DataFrame(columns=['Pessoa'])

    if jira_people_df.empty and bb_people_df.empty:
        return pd.DataFrame(), {}, {}

    merged = pd.merge(jira_people_df, bb_people_df, how='outer', on='Pessoa')
    numeric_fill_zero = [
        'Itens Concluidos',
        'Itens Iniciados',
        'WIP no Fim',
        'PRs Abertos',
        'Aprovacoes',
        'Reprovacoes',
        'PRs Declinados (Autor)',
        'Commits',
    ]
    for col in numeric_fill_zero:
        if col not in merged.columns:
            merged[col] = 0
        merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0).astype(int)

    if 'Lead Time Mediano (dias)' not in merged.columns:
        merged['Lead Time Mediano (dias)'] = 0.0
    merged['Lead Time Mediano (dias)'] = pd.to_numeric(merged['Lead Time Mediano (dias)'], errors='coerce').fillna(0.0).round(1)

    commits = bitbucket_logs.get('commits', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    pullrequests = bitbucket_logs.get('pullrequests', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    tech_keys = set()
    for df_src in (commits, pullrequests):
        if df_src is None or df_src.empty:
            continue
        date_col = 'date' if 'date' in df_src.columns else 'created_on'
        if date_col in df_src.columns:
            df_src = df_src[(df_src[date_col] >= start_ts) & (df_src[date_col] < end_ts)]
        if 'work_item_keys' in df_src.columns:
            for raw in df_src['work_item_keys'].fillna(''):
                for key in str(raw).split('|'):
                    key = key.strip().upper()
                    if key:
                        tech_keys.add(key)
        if 'primary_work_item_key' in df_src.columns:
            for key in df_src['primary_work_item_key'].fillna('').astype(str):
                key = key.strip().upper()
                if key:
                    tech_keys.add(key)

    merged['Itens com Evidencia Tecnica'] = 0
    merged['Cobertura Tecnica (%)'] = 0.0
    if jira_df is not None and not jira_df.empty:
        id_col = 'ItemID' if 'ItemID' in jira_df.columns else ('ID' if 'ID' in jira_df.columns else None)
        if id_col:
            done_window = jira_df[
                (jira_df['DataDone'] >= start_ts) &
                (jira_df['DataDone'] < end_ts)
            ].copy()
            # DevExecutor (autor do PR) tem prioridade sobre Responsavel (assignee Jira).
            if 'DevExecutor' in done_window.columns:
                _exec = done_window['DevExecutor'].astype(str).str.strip()
                _assi = done_window['Responsavel'].astype(str).str.strip()
                _fonte = _exec.where(_exec.ne('') & _exec.ne('nan'), _assi)
            else:
                _fonte = done_window['Responsavel'].astype(str).str.strip()
            done_window['Pessoa'] = _fonte.apply(
                lambda x: _canonical_person_name(x, alias_index=alias_index)
            )
            done_window = done_window[done_window['Pessoa'].astype(str).str.strip().ne('')]
            done_window['ItemKey'] = done_window[id_col].astype(str).str.strip().str.upper()
            done_window = done_window[done_window['ItemKey'].ne('')]
            if not done_window.empty:
                done_window['TemEvidenciaTecnica'] = done_window['ItemKey'].isin(tech_keys)
                by_person_tech = done_window.groupby('Pessoa')['TemEvidenciaTecnica'].sum()
                merged['Itens com Evidencia Tecnica'] = merged['Pessoa'].map(by_person_tech).fillna(0).astype(int)
                with np.errstate(divide='ignore', invalid='ignore'):
                    merged['Cobertura Tecnica (%)'] = np.where(
                        merged['Itens Concluidos'] > 0,
                        (merged['Itens com Evidencia Tecnica'] / merged['Itens Concluidos']) * 100.0,
                        0.0,
                    )
                merged['Cobertura Tecnica (%)'] = merged['Cobertura Tecnica (%)'].round(1)

    merged['Score Capacidade (proxy bruto)'] = (
        merged['Itens Concluidos'] +
        merged['PRs Abertos'] +
        merged['Aprovacoes'] +
        merged['Reprovacoes'] +
        (merged['Commits'] / 5.0)
    ).round(1)
    max_proxy = float(merged['Score Capacidade (proxy bruto)'].max()) if not merged.empty else 0.0
    if max_proxy > 0:
        merged['Score Capacidade (%)'] = ((merged['Score Capacidade (proxy bruto)'] / max_proxy) * 100.0).round(2)
    else:
        merged['Score Capacidade (%)'] = 0.0
    merged['Total Contribuicoes'] = (
        merged['PRs Abertos'] +
        merged['Aprovacoes'] +
        merged['Reprovacoes'] +
        merged['PRs Declinados (Autor)'] +
        merged['Commits']
    )
    merged = merged.sort_values(
        ['Score Capacidade (%)', 'Itens Concluidos', 'Total Contribuicoes', 'Pessoa'],
        ascending=[False, False, False, True]
    ).reset_index(drop=True)

    totals = {
        'Itens Concluidos': int(merged['Itens Concluidos'].sum()),
        'PRs Abertos': int(merged['PRs Abertos'].sum()),
        'Aprovacoes': int(merged['Aprovacoes'].sum()),
        'Reprovacoes': int(merged['Reprovacoes'].sum()),
        'Commits': int(merged['Commits'].sum()),
        'Itens com Evidencia Tecnica': int(merged['Itens com Evidencia Tecnica'].sum()),
    }
    return merged, totals, {'jira': jira_totals, 'bitbucket': bb_totals}


def compute_cross_source_capacity_weekly_metrics(jira_df, bitbucket_logs, start_ts, end_ts):
    alias_index = _load_person_alias_index()
    metric_frames = []

    if jira_df is not None and not jira_df.empty and {'Responsavel', 'DataDone'}.issubset(jira_df.columns):
        jira_done = jira_df.copy()
        jira_done = jira_done[
            (jira_done['DataDone'] >= start_ts) &
            (jira_done['DataDone'] < end_ts)
        ].copy()
        # DevExecutor (autor do PR) tem prioridade sobre Responsavel (assignee Jira).
        if 'DevExecutor' in jira_done.columns:
            _exec = jira_done['DevExecutor'].astype(str).str.strip()
            _assi = jira_done['Responsavel'].astype(str).str.strip()
            _fonte = _exec.where(_exec.ne('') & _exec.ne('nan'), _assi)
        else:
            _fonte = jira_done['Responsavel'].astype(str).str.strip()
        jira_done['Pessoa'] = _fonte.apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
        jira_done = jira_done[jira_done['Pessoa'].astype(str).str.strip().ne('')]
        jira_done['DataDone'] = pd.to_datetime(jira_done['DataDone'], errors='coerce')
        jira_done = jira_done.dropna(subset=['DataDone'])
        if not jira_done.empty:
            jira_done['Semana'] = weekly_bucket_start(jira_done['DataDone'])
            metric_frames.append(
                jira_done.groupby(['Semana', 'Pessoa'], as_index=False).size().rename(columns={'size': 'Itens Concluidos'})
            )

    commits = bitbucket_logs.get('commits', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    if commits is not None and not commits.empty and {'author', 'date'}.issubset(commits.columns):
        c = commits[(commits['date'] >= start_ts) & (commits['date'] < end_ts)].copy()
        c['Pessoa'] = c['author'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
        c = c[c['Pessoa'].astype(str).str.strip().ne('')]
        c['date'] = pd.to_datetime(c['date'], errors='coerce')
        c = c.dropna(subset=['date'])
        if not c.empty:
            c['Semana'] = weekly_bucket_start(c['date'])
            metric_frames.append(c.groupby(['Semana', 'Pessoa'], as_index=False).size().rename(columns={'size': 'Commits'}))

    pullrequests = bitbucket_logs.get('pullrequests', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    if pullrequests is not None and not pullrequests.empty:
        if {'author', 'created_on'}.issubset(pullrequests.columns):
            prs_opened = pullrequests[(pullrequests['created_on'] >= start_ts) & (pullrequests['created_on'] < end_ts)].copy()
            prs_opened['Pessoa'] = prs_opened['author'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
            prs_opened = prs_opened[prs_opened['Pessoa'].astype(str).str.strip().ne('')]
            prs_opened['created_on'] = pd.to_datetime(prs_opened['created_on'], errors='coerce')
            prs_opened = prs_opened.dropna(subset=['created_on'])
            if not prs_opened.empty:
                prs_opened['Semana'] = weekly_bucket_start(prs_opened['created_on'])
                metric_frames.append(
                    prs_opened.groupby(['Semana', 'Pessoa'], as_index=False).size().rename(columns={'size': 'PRs Abertos'})
                )

        if 'updated_on' in pullrequests.columns:
            prs_review = pullrequests[(pullrequests['updated_on'] >= start_ts) & (pullrequests['updated_on'] < end_ts)].copy()
            prs_review['updated_on'] = pd.to_datetime(prs_review['updated_on'], errors='coerce')
            prs_review = prs_review.dropna(subset=['updated_on'])
            if not prs_review.empty:
                for col_name, metric_name in [('approved_by', 'Aprovacoes'), ('changes_requested_by', 'Reprovacoes')]:
                    if col_name not in prs_review.columns:
                        continue
                    exploded = prs_review[['updated_on', col_name]].copy()
                    exploded['Pessoa'] = exploded[col_name].apply(_split_people_field)
                    exploded = exploded.explode('Pessoa')
                    exploded['Pessoa'] = exploded['Pessoa'].apply(
                        lambda x: _canonical_person_name(x, alias_index=alias_index)
                    )
                    exploded = exploded[exploded['Pessoa'].astype(str).str.strip().ne('')]
                    if exploded.empty:
                        continue
                    exploded['Semana'] = weekly_bucket_start(exploded['updated_on'])
                    metric_frames.append(
                        exploded.groupby(['Semana', 'Pessoa'], as_index=False).size().rename(columns={'size': metric_name})
                    )

    if not metric_frames:
        return pd.DataFrame()

    merged = metric_frames[0].copy()
    for frame in metric_frames[1:]:
        merged = pd.merge(merged, frame, how='outer', on=['Semana', 'Pessoa'])

    for col in ['Itens Concluidos', 'PRs Abertos', 'Aprovacoes', 'Reprovacoes', 'Commits']:
        if col not in merged.columns:
            merged[col] = 0
        merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0).astype(int)

    merged['Score Capacidade (proxy bruto)'] = (
        merged['Itens Concluidos'] +
        merged['PRs Abertos'] +
        merged['Aprovacoes'] +
        merged['Reprovacoes'] +
        (merged['Commits'] / 5.0)
    ).round(1)
    weekly_max_proxy = merged.groupby('Semana')['Score Capacidade (proxy bruto)'].transform('max')
    with np.errstate(divide='ignore', invalid='ignore'):
        merged['Score Capacidade (%)'] = np.where(
            weekly_max_proxy > 0,
            (merged['Score Capacidade (proxy bruto)'] / weekly_max_proxy) * 100.0,
            0.0,
        )
    merged['Score Capacidade (%)'] = pd.to_numeric(merged['Score Capacidade (%)'], errors='coerce').fillna(0).round(2)
    merged = merged.sort_values(['Semana', 'Score Capacidade (%)', 'Pessoa'], ascending=[True, False, True]).reset_index(drop=True)
    return merged


def _sp_bucket(sp):
    """Classifica story points em faixas de complexidade."""
    try:
        val = float(sp)
    except (TypeError, ValueError):
        val = 0.0
    if val <= 0:
        return 'Sem estimativa'
    if val <= 3:
        return '1-3 SP (pequeno)'
    if val <= 8:
        return '5-8 SP (médio)'
    return '13+ SP (grande)'


def _sp_weight(sp):
    """Peso de complexidade por faixa de SP (para normalizar score de entrega).
    Sem estimativa = 0.5; pequeno (1-3) = 1.0; médio (5-8) = 2.0; grande (13+) = 3.0
    """
    try:
        val = float(sp)
    except (TypeError, ValueError):
        val = 0.0
    if val <= 0:
        return 0.5
    if val <= 3:
        return 1.0
    if val <= 8:
        return 2.0
    return 3.0


_TSHIRT_TO_SP_EQUIV: dict = {
    'xs': 1.0, 'xp': 1.0,
    'p': 2.0, 's': 2.0, 'small': 2.0, 'pequeno': 2.0,
    'm': 5.0, 'medium': 5.0, 'médio': 5.0, 'medio': 5.0,
    'g': 8.0, 'l': 8.0, 'large': 8.0, 'grande': 8.0,
    'gg': 13.0, 'xl': 13.0, 'xg': 13.0, 'x-large': 13.0, 'muito grande': 13.0,
    'xgg': 21.0, 'xxl': 21.0, 'xxg': 21.0,
}


def _tshirt_to_weight(size_str):
    """Converte T-shirt size (P/M/G/XS/XL) para peso de complexidade equivalente em SP.

    Retorna None se o valor não for reconhecido — o chamador decide o fallback.
    """
    if size_str is None:
        return None
    try:
        import math
        if math.isnan(float(size_str)):
            return None
    except (TypeError, ValueError):
        pass
    key = str(size_str).lower().strip()
    if not key:
        return None
    sp_eq = _TSHIRT_TO_SP_EQUIV.get(key)
    return _sp_weight(sp_eq) if sp_eq is not None else None


def _unified_complexity_weight(sp_val, tshirt_val=None):
    """Peso unificado de complexidade, combinando SP e T-shirt size.

    Prioridade: SP numérico > T-shirt size > sem estimativa (0.5).
    Equaliza os dois formatos de estimativa (Kitchenham & Mendes, TSE 2004).
    """
    try:
        sp = float(sp_val)
    except (TypeError, ValueError):
        sp = 0.0
    if sp > 0:
        return _sp_weight(sp)
    # Fallback para T-shirt size quando SP não disponível
    if tshirt_val is not None:
        w = _tshirt_to_weight(tshirt_val)
        if w is not None:
            return w
    return 0.5  # sem estimativa


def _build_sp_inference_model(base_df: pd.DataFrame) -> dict:
    """Constrói modelo de inferência de SP por mediana condicional em cascata.

    Usado para itens sem SP nem T-shirt registrados.
    Cascata:
      1. Mediana SP por TipoDemanda   (mín. 3 amostras — mais específico)
      2. Mediana SP por WorkItemCategory (mín. 2 amostras — fallback intermediário)
      3. Mediana SP global            (fallback final)

    Retorna dict com chaves:
      'tipo'     → {TipoDemanda: median_sp}
      'category' → {WorkItemCategory: median_sp}
      'global'   → float
      'n_source' → int  (qtd itens com SP usados para construir o modelo)
    """
    model: dict = {'tipo': {}, 'category': {}, 'global': 2.0, 'n_source': 0}
    if base_df is None or base_df.empty or 'StoryPoints' not in base_df.columns:
        return model

    sp_series = pd.to_numeric(base_df['StoryPoints'], errors='coerce').fillna(0)
    has_sp = sp_series > 0
    model['n_source'] = int(has_sp.sum())

    if model['n_source'] == 0:
        return model

    model['global'] = float(sp_series[has_sp].median())

    if 'TipoDemanda' in base_df.columns:
        for tipo, grp in base_df[has_sp].groupby('TipoDemanda', dropna=True):
            if len(grp) >= 3:
                model['tipo'][str(tipo)] = float(
                    pd.to_numeric(grp['StoryPoints'], errors='coerce').median()
                )

    if 'WorkItemCategory' in base_df.columns:
        for cat, grp in base_df[has_sp].groupby('WorkItemCategory', dropna=True):
            if len(grp) >= 2:
                model['category'][str(cat)] = float(
                    pd.to_numeric(grp['StoryPoints'], errors='coerce').median()
                )

    return model


def _infer_sp(sp_val, tshirt_val, tipo: str, category: str, model: dict):
    """Retorna (sp_efetivo, is_inferred) para um item.

    Prioridade:
      1. SP numérico original (> 0)
      2. T-shirt size reconhecido  → SP equivalente (não é inferência, é normalização)
      3. Mediana por TipoDemanda   (model['tipo'])
      4. Mediana por WorkItemCategory (model['category'])
      5. Mediana global            (model['global'])
    """
    try:
        sp = float(sp_val)
    except (TypeError, ValueError):
        sp = 0.0

    if sp > 0:
        return sp, False  # estimativa real — não inferida

    # T-shirt disponível → normalização, não inferência
    if tshirt_val is not None:
        key = str(tshirt_val).lower().strip()
        if key and _TSHIRT_TO_SP_EQUIV.get(key) is not None:
            return float(_TSHIRT_TO_SP_EQUIV[key]), False

    # Sem estimativa — inferir por mediana condicional
    if tipo and tipo in model.get('tipo', {}):
        return model['tipo'][tipo], True
    if category and category in model.get('category', {}):
        return model['category'][category], True
    return model.get('global', 2.0), True


def _unified_sp_bucket(sp_val, tshirt_val=None):
    """Faixa de complexidade usando SP ou T-shirt como fallback.

    Prioridade: SP numérico > T-shirt size equalizado > 'Sem estimativa'.
    Elimina a categoria 'Sem estimativa' para itens que têm T-shirt configurado.
    Equalização: P/S=2SP, M=5SP, G/L=8SP, GG/XL=13SP (Kitchenham & Mendes, TSE 2004).
    """
    try:
        sp = float(sp_val)
    except (TypeError, ValueError):
        sp = 0.0
    if sp > 0:
        return _sp_bucket(sp)
    # Fallback para T-shirt size
    if tshirt_val is not None:
        key = str(tshirt_val).lower().strip()
        sp_eq = _TSHIRT_TO_SP_EQUIV.get(key)
        if sp_eq is not None:
            return _sp_bucket(sp_eq)
    return 'Sem estimativa'


def _resolve_dev_person_series(df: pd.DataFrame, alias_index=None) -> pd.Series:
    """Resolve a pessoa responsável pelo trabalho técnico na mesma semântica da aba dev."""
    if df is None or df.empty or 'Responsavel' not in df.columns:
        return pd.Series(dtype='object')
    if alias_index is None:
        alias_index = _load_person_alias_index()

    if 'DevExecutor' in df.columns:
        executor = df['DevExecutor'].astype(str).str.strip()
        assignee = df['Responsavel'].astype(str).str.strip()
        source = executor.where(executor.ne('') & executor.ne('nan'), assignee)
    else:
        source = df['Responsavel'].astype(str).str.strip()

    return source.apply(lambda x: _canonical_person_name(x, alias_index=alias_index))


def _build_dev_item_person_map(df: pd.DataFrame, alias_index=None) -> dict[str, str]:
    """Mapeia ItemID -> pessoa canônica do dev para alinhar PM e base Jira filtrada."""
    if df is None or df.empty or 'ItemID' not in df.columns or 'Responsavel' not in df.columns:
        return {}
    tmp = df[['ItemID', 'Responsavel'] + (['DevExecutor'] if 'DevExecutor' in df.columns else [])].copy()
    tmp['Pessoa'] = _resolve_dev_person_series(tmp, alias_index=alias_index)
    tmp['ItemID'] = tmp['ItemID'].astype(str).str.strip()
    tmp = tmp[tmp['ItemID'].ne('') & tmp['Pessoa'].astype(str).str.strip().ne('')]
    if tmp.empty:
        return {}
    return tmp.drop_duplicates(subset=['ItemID'], keep='first').set_index('ItemID')['Pessoa'].to_dict()


def _recompute_itens_entregues_from_dev_flow(
    per_dev: pd.DataFrame,
    dev_flow_items_df: pd.DataFrame,
    df_prod_base: pd.DataFrame,
    alias_index: dict,
    start_ts,
    end_ts,
    events_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Atualiza 'Itens Entregues' em per_dev usando a saída do dev stage (In Progress →
    Code Review / QA) como fonte primária, com fallback hierárquico:

      1. EventosFiltrados (fonte primária): conta itens únicos por dev/autor onde
         houve uma transição FROM dev stage TO code review/QA no período.
         Cobre variantes de nome do status (incluindo typos como "In Progess").
      2. DevFlowItens (fonte secundária): para devs não cobertos pelos eventos,
         usa o mapa Issue Key → pessoa via df_prod_base e filtra por data.
      3. Fallback: mantém 'Itens Entregues' original (Done Final Author) para
         devs não encontrados nas fontes 1 e 2.

    A abordagem via EventosFiltrados é mais robusta porque:
    - Não depende do DEV_HINTS do process mining (que pode não cobrir typos de status)
    - Usa o Author da transição (quem efetivamente moveu o card)
    - Filtra pela data da transição diretamente
    """
    # ── Salva Itens Entregues original como fallback final ───────────────────
    original_itens: dict[str, int] = (
        per_dev.set_index('Pessoa')['Itens Entregues'].fillna(0).astype(int).to_dict()
        if 'Itens Entregues' in per_dev.columns else {}
    )

    # Hints de status que indicam saída do estágio de desenvolvimento
    _DEV_STAGE_HINTS = (
        'in progress', 'in progess',  # typo comum no Jira
        'development', 'developing',
        'doing', 'wip',
        'em desenvolvimento', 'em andamento', 'in development',
    )
    _EXIT_TARGET_HINTS = (
        'code review', 'ready for code', 'ready code',
        'testing', 'qa', 'quality',
        'ready for test', 'ready test',
        'homolog', 'staging', 'ready to staging',
        'ready for production', 'ready to homolog',
    )

    def _naive(ts):
        t = pd.to_datetime(ts, errors='coerce')
        return t.tz_convert(None) if getattr(t, 'tzinfo', None) else t

    _start = _naive(start_ts)
    _end   = _naive(end_ts)

    # ── FONTE 1: EventosFiltrados — transições Dev → Code Review/QA ─────────
    dev_count_events: pd.Series = pd.Series(dtype=int)
    if (
        events_df is not None
        and not events_df.empty
        and {'Issue Key', 'Author', 'History Date', 'From Status Norm', 'To Status Norm'}.issubset(events_df.columns)
    ):
        ev = events_df.copy()
        ev['_date'] = pd.to_datetime(ev['History Date'], dayfirst=True, errors='coerce')
        if ev['_date'].dt.tz is not None:
            ev['_date'] = ev['_date'].dt.tz_convert(None)
        ev['From Status Norm'] = ev['From Status Norm'].fillna('').astype(str)
        ev['To Status Norm']   = ev['To Status Norm'].fillna('').astype(str)

        # Transições que saem de um dev stage e entram em review/QA no período
        _from_dev = ev['From Status Norm'].apply(
            lambda s: any(h in s for h in _DEV_STAGE_HINTS)
        )
        _to_review = ev['To Status Norm'].apply(
            lambda s: any(h in s for h in _EXIT_TARGET_HINTS)
        )
        _in_period = ev['_date'].notna() & (ev['_date'] >= _start) & (ev['_date'] < _end)

        transitions = ev[_from_dev & _to_review & _in_period].copy()

        if not transitions.empty:
            transitions['_Author'] = transitions['Author'].astype(str).str.strip()
            # Resolve alias: Author pode ser email ou nome variante
            transitions['_Pessoa'] = transitions['_Author'].apply(
                lambda a: _canonical_person_name(a, alias_index=alias_index)
            )
            transitions = transitions[
                transitions['_Pessoa'].astype(str).str.strip().ne('')
                & transitions['_Pessoa'].str.lower().ne('sem autor')
            ]
            if not transitions.empty:
                # Conta Issue Keys únicas por pessoa (evita double-count por retrabalho)
                dev_count_events = (
                    transitions.groupby('_Pessoa')['Issue Key'].nunique()
                )

    # ── FONTE 2: DevFlowItens — fallback por mapeamento Item → Pessoa ───────
    dev_count_items: pd.Series = pd.Series(dtype=int)
    if (
        dev_flow_items_df is not None
        and not dev_flow_items_df.empty
        and 'Issue Key' in dev_flow_items_df.columns
        and df_prod_base is not None
        and not df_prod_base.empty
        and 'ItemID' in df_prod_base.columns
    ):
        # Mapa ItemID → pessoa canônica
        _tmp = df_prod_base[
            ['ItemID', 'Responsavel']
            + (['DevExecutor'] if 'DevExecutor' in df_prod_base.columns else [])
        ].copy()
        _tmp['_Pessoa'] = _resolve_dev_person_series(_tmp, alias_index=alias_index)
        _tmp['ItemID'] = _tmp['ItemID'].astype(str).str.strip().str.upper()
        _tmp = _tmp[_tmp['ItemID'].ne('') & _tmp['_Pessoa'].astype(str).str.strip().ne('')]
        if not _tmp.empty:
            item_to_person = (
                _tmp.drop_duplicates(subset=['ItemID'], keep='first')
                .set_index('ItemID')['_Pessoa'].to_dict()
            )
            dfi = dev_flow_items_df.copy()
            dfi['Issue Key'] = dfi['Issue Key'].astype(str).str.strip().str.upper()

            for col in ['Primeira Entrada Dev', 'Ultima Entrada Dev']:
                if col in dfi.columns:
                    dfi[col] = pd.to_datetime(dfi[col], errors='coerce')
                    if dfi[col].dt.tz is not None:
                        dfi[col] = dfi[col].dt.tz_convert(None)

            # Filtra itens com segmento de dev sobreposto ao período
            if 'Primeira Entrada Dev' in dfi.columns and 'Ultima Entrada Dev' in dfi.columns:
                _mask = (
                    dfi['Primeira Entrada Dev'].notna()
                    & dfi['Ultima Entrada Dev'].notna()
                    & (dfi['Primeira Entrada Dev'] < _end)
                    & (dfi['Ultima Entrada Dev'] >= _start)
                )
                dfi = dfi[_mask].copy()

            dfi['_Pessoa'] = dfi['Issue Key'].map(item_to_person)
            # Heurística: tenta prefixo alternativo (W1NNR ↔ W1NNER)
            _unmapped = dfi['_Pessoa'].isna()
            if _unmapped.any():
                _alt = {
                    k.replace('W1NNER', 'W1NNR').replace('W1NNR', 'W1NNER'): v
                    for k, v in item_to_person.items()
                }
                dfi.loc[_unmapped, '_Pessoa'] = dfi.loc[_unmapped, 'Issue Key'].map(_alt)

            dfi = dfi[
                dfi['_Pessoa'].notna()
                & dfi['_Pessoa'].astype(str).str.strip().ne('')
                & dfi['_Pessoa'].str.lower().ne('sem autor')
            ]
            if not dfi.empty:
                dev_count_items = dfi.groupby('_Pessoa')['Issue Key'].nunique()

    # ── Mescla fontes e aplica fallback ─────────────────────────────────────
    result = per_dev.copy()

    # Fonte primária: EventosFiltrados
    if not dev_count_events.empty:
        result['Itens Entregues'] = result['Pessoa'].map(dev_count_events).fillna(0).astype(int)
    else:
        result['Itens Entregues'] = 0

    # Fonte secundária: DevFlowItens para quem não apareceu nos eventos
    if not dev_count_items.empty:
        _mask_zero = result['Itens Entregues'] == 0
        result.loc[_mask_zero, 'Itens Entregues'] = (
            result.loc[_mask_zero, 'Pessoa'].map(dev_count_items).fillna(0).astype(int)
        )

    # Fallback final: done_window (comportamento original) para quem ainda tem 0
    if original_itens:
        _mask_zero = result['Itens Entregues'] == 0
        result.loc[_mask_zero, 'Itens Entregues'] = (
            result.loc[_mask_zero, 'Pessoa'].map(original_itens).fillna(0).astype(int)
        )

    # Sincroniza Score Complexidade para devs que ganharam itens via eventos mas não
    # têm DataDone no período (Score Complexidade = 0 da done_window). Usa contagem de
    # itens como proxy — mesmo comportamento do else-branch em build_dev_productivity_metrics.
    if 'Score Complexidade' in result.columns:
        _gain_mask = (result['Itens Entregues'] > 0) & (
            pd.to_numeric(result['Score Complexidade'], errors='coerce').fillna(0) == 0
        )
        result.loc[_gain_mask, 'Score Complexidade'] = (
            result.loc[_gain_mask, 'Itens Entregues'].astype(float)
        )

    return result


def build_dev_productivity_metrics(df, start_ts, end_ts):
    """
    Calcula métricas de produtividade individual por desenvolvedor.

    Retorna:
        per_dev_df  — DataFrame com resumo por pessoa (uma linha por dev).
        complexity_df — DataFrame com cartões puxados por faixa de Story Points e pessoa.
    """
    if df is None or df.empty or 'Responsavel' not in df.columns:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    alias_index = _load_person_alias_index()

    base = df.copy()
    base['_Pessoa'] = _resolve_dev_person_series(base, alias_index=alias_index)
    base = base[base['_Pessoa'].astype(str).str.strip().ne('')]
    if base.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Deriva WorkItemCategory a partir de TipoDemanda se a coluna não existir
    # TipoDemanda usa constantes TYPE_ISSUES, TYPE_DEV, TYPE_SUPPORT, TYPE_OTHER
    if 'WorkItemCategory' not in base.columns and 'TipoDemanda' in base.columns:
        _tipodemanda_to_cat = {
            TYPE_ISSUES:  'Defeitos',
            TYPE_DEV:     'Desenvolvimento',
            TYPE_SUPPORT: 'Suporte',
            TYPE_OTHER:   'Outro',
        }
        base['WorkItemCategory'] = base['TipoDemanda'].map(_tipodemanda_to_cat).fillna('Outro')

    start_ts = pd.to_datetime(start_ts)
    end_ts = pd.to_datetime(end_ts)

    done_eligible = base[done_time_eligible_mask(base)].copy() if callable(done_time_eligible_mask) else base.copy()
    done_window = done_eligible[
        (done_eligible['DataDone'] >= start_ts) & (done_eligible['DataDone'] < end_ts)
    ].copy() if 'DataDone' in done_eligible.columns else pd.DataFrame()

    started_window = base[
        (base['DataInProgress'] >= start_ts) & (base['DataInProgress'] < end_ts)
    ].copy() if 'DataInProgress' in base.columns else pd.DataFrame()

    # ── Modelo de inferência de SP (mediana condicional em cascata) ───────────
    # Construído a partir de TODOS os itens da base com SP preenchido.
    # Cascata: TipoDemanda (≥3 amostras) → WorkItemCategory (≥2) → global.
    # Usado apenas no bucketing e peso de complexidade — SP Entregues não é alterado.
    _sp_model = _build_sp_inference_model(base)

    def _apply_inference_to_window(window_df: pd.DataFrame) -> pd.DataFrame:
        """Aplica inferência de SP ao DataFrame e adiciona colunas _SP_Efetivo e _SP_Inferido."""
        if window_df.empty:
            return window_df
        w = window_df.copy()
        _has_sp  = 'StoryPoints' in w.columns
        _has_ts  = 'EffortTShirtSize' in w.columns
        _has_tpo = 'TipoDemanda' in w.columns
        _has_cat = 'WorkItemCategory' in w.columns
        if _has_sp:
            w['StoryPoints'] = pd.to_numeric(w['StoryPoints'], errors='coerce').fillna(0)
        else:
            w['StoryPoints'] = 0.0
        sp_ef, inf_flag = [], []
        for _, row in w.iterrows():
            sp, is_inf = _infer_sp(
                row['StoryPoints'],
                row.get('EffortTShirtSize') if _has_ts else None,
                str(row.get('TipoDemanda', '') or '') if _has_tpo else '',
                str(row.get('WorkItemCategory', '') or '') if _has_cat else '',
                _sp_model,
            )
            sp_ef.append(sp)
            inf_flag.append(is_inf)
        w['_SP_Efetivo']  = sp_ef
        w['_SP_Inferido'] = inf_flag
        return w

    if not done_window.empty:
        done_window    = _apply_inference_to_window(done_window)
    if not started_window.empty:
        started_window = _apply_inference_to_window(started_window)

    all_people = sorted(base['_Pessoa'].unique())
    per_dev = pd.DataFrame({'Pessoa': all_people})

    # Cartões entregues
    if not done_window.empty:
        per_dev['Itens Entregues'] = per_dev['Pessoa'].map(
            done_window['_Pessoa'].value_counts()
        ).fillna(0).astype(int)
    else:
        per_dev['Itens Entregues'] = 0

    # Cartões puxados (iniciados no período)
    if not started_window.empty:
        per_dev['Itens Puxados'] = per_dev['Pessoa'].map(
            started_window['_Pessoa'].value_counts()
        ).fillna(0).astype(int)
    else:
        per_dev['Itens Puxados'] = 0

    # Story Points entregues
    if not done_window.empty and 'StoryPoints' in done_window.columns:
        sp_done = done_window.copy()
        sp_done['StoryPoints'] = pd.to_numeric(sp_done['StoryPoints'], errors='coerce').fillna(0)
        per_dev['SP Entregues'] = per_dev['Pessoa'].map(
            sp_done.groupby('_Pessoa')['StoryPoints'].sum()
        ).fillna(0).round(0).astype(int)
    else:
        per_dev['SP Entregues'] = 0

    # Demandas de Falha — defeitos concluídos atribuídos ao dev
    if not done_window.empty and 'WorkItemCategory' in done_window.columns:
        defeitos = done_window[done_window['WorkItemCategory'] == 'Defeitos']
        per_dev['Defeitos Entregues'] = per_dev['Pessoa'].map(
            defeitos['_Pessoa'].value_counts()
        ).fillna(0).astype(int)
        per_dev['% Demanda Falha'] = np.where(
            per_dev['Itens Entregues'] > 0,
            (per_dev['Defeitos Entregues'] / per_dev['Itens Entregues'] * 100.0).round(1),
            0.0,
        )
    else:
        per_dev['Defeitos Entregues'] = 0
        per_dev['% Demanda Falha'] = 0.0

    # Defeitos iniciados (falhas puxadas no período)
    if not started_window.empty and 'WorkItemCategory' in started_window.columns:
        def_puxados = started_window[started_window['WorkItemCategory'] == 'Defeitos']
        per_dev['Defeitos Puxados'] = per_dev['Pessoa'].map(
            def_puxados['_Pessoa'].value_counts()
        ).fillna(0).astype(int)
    else:
        per_dev['Defeitos Puxados'] = 0

    # WIP Residual — itens iniciados no período que ainda não foram concluídos
    # (DataDone nula ou >= end_ts)
    if not started_window.empty and 'DataDone' in started_window.columns:
        _dd = pd.to_datetime(started_window['DataDone'], errors='coerce')
        _wip_mask = _dd.isna() | (_dd >= end_ts)
        _wip_items = started_window[_wip_mask.values]
        per_dev['WIP Residual'] = per_dev['Pessoa'].map(
            _wip_items['_Pessoa'].value_counts()
        ).fillna(0).astype(int)
    else:
        per_dev['WIP Residual'] = 0

    # Flow Efficiency — % de itens puxados que foram entregues no período (valor bruto, pode >100%)
    # Proxy de Little's Law: alta efficiency → baixo WIP acumulado (Anderson 2010)
    per_dev['Flow Efficiency (%)'] = np.where(
        per_dev['Itens Puxados'] > 0,
        (per_dev['Itens Entregues'] / per_dev['Itens Puxados'] * 100.0).round(1),
        0.0,
    )

    # WIP Início de Período — itens em progresso antes de start_ts que ainda não estavam done.
    # Representam comprometimento cross-period e devem entrar no denominador da FE Ajustada
    # para evitar saturação artificial em devs que entregam trabalho de períodos anteriores.
    # Fonte: Anderson (2010) — disciplina de WIP inclui carryover de períodos anteriores.
    if 'DataInProgress' in base.columns and 'DataDone' in base.columns:
        _ip = pd.to_datetime(base['DataInProgress'], errors='coerce')
        _dn = pd.to_datetime(base['DataDone'], errors='coerce')
        _wip_start_mask = _ip.notna() & (_ip < start_ts) & (_dn.isna() | (_dn >= start_ts))
        _wip_start_items = base[_wip_start_mask]
        per_dev['WIP Inicio Periodo'] = per_dev['Pessoa'].map(
            _wip_start_items['_Pessoa'].value_counts()
        ).fillna(0).astype(int)
    else:
        per_dev['WIP Inicio Periodo'] = 0

    # FE Ajustada (%) — denominador inclui WIP cross-period: bounded [0, 100].
    # FE_ajustada = Entregues / (Puxados + WIP_inicio) × 100
    # Corrige: FE>100% (entregues > puxados) e FE=0 (puxados=0, entregues>0 de período anterior).
    _fe_denom = per_dev['Itens Puxados'] + per_dev['WIP Inicio Periodo']
    per_dev['FE Ajustada (%)'] = np.where(
        _fe_denom > 0,
        (per_dev['Itens Entregues'] / _fe_denom * 100.0).clip(0, 100).round(1),
        np.where(per_dev['Itens Entregues'] > 0, 100.0, 0.0),
    )

    # Lead Time mediano + P50/P85 por dev
    if not done_window.empty and 'LeadTime_Selected_Dias' in done_window.columns:
        lt = done_window.copy()
        lt['LeadTime_Selected_Dias'] = pd.to_numeric(lt['LeadTime_Selected_Dias'], errors='coerce')
        lt = lt[lt['LeadTime_Selected_Dias'] >= 0]
        _lt_grp = lt.groupby('_Pessoa')['LeadTime_Selected_Dias']
        per_dev['Lead Time Mediano (dias)'] = per_dev['Pessoa'].map(
            _lt_grp.median()
        ).fillna(0.0).round(1)
        per_dev['Lead Time P50 (dias)'] = per_dev['Pessoa'].map(
            _lt_grp.quantile(0.50)
        ).fillna(0.0).round(1)
        per_dev['Lead Time P85 (dias)'] = per_dev['Pessoa'].map(
            _lt_grp.quantile(0.85)
        ).fillna(0.0).round(1)
    else:
        per_dev['Lead Time Mediano (dias)'] = 0.0
        per_dev['Lead Time P50 (dias)'] = 0.0
        per_dev['Lead Time P85 (dias)'] = 0.0

    # Cartões puxados por faixa de complexidade — estimativa unificada (SP ou T-shirt).
    # Usa _unified_sp_bucket() para eliminar "Sem estimativa" em itens com T-shirt size.
    complexity_df = pd.DataFrame()
    if not started_window.empty:
        sw = started_window.copy()
        # _SP_Efetivo já foi calculado por _apply_inference_to_window():
        # SP numérico → T-shirt equalizado → mediana condicional por tipo/categoria/global.
        sw['SP_Bucket'] = sw['_SP_Efetivo'].apply(_unified_sp_bucket)
        _n_inferred_cx = int(sw['_SP_Inferido'].sum()) if '_SP_Inferido' in sw.columns else 0
        complexity_df = (
            sw.groupby(['_Pessoa', 'SP_Bucket']).size()
            .reset_index(name='Qtd')
            .rename(columns={'_Pessoa': 'Pessoa'})
        )
        complexity_df.attrs['n_inferred'] = _n_inferred_cx

    # Breakdown por tipo de demanda (WorkItemCategory) dos itens entregues
    # Retorna category_df com colunas: Pessoa, WorkItemCategory, Qtd, Pct
    category_df = pd.DataFrame()
    if not done_window.empty and 'WorkItemCategory' in done_window.columns:
        _cat_grp = (
            done_window.groupby(['_Pessoa', 'WorkItemCategory']).size()
            .reset_index(name='Qtd')
            .rename(columns={'_Pessoa': 'Pessoa'})
        )
        _cat_totals = _cat_grp.groupby('Pessoa')['Qtd'].transform('sum')
        _cat_grp['Pct'] = (_cat_grp['Qtd'] / _cat_totals * 100).round(1)
        category_df = _cat_grp.copy()

    # BU por pessoa (via people_config.json)
    bu_index = _load_person_bu_map()
    per_dev['BU'] = per_dev['Pessoa'].apply(lambda p: _person_bu(p, bu_index=bu_index))

    # Exclui BUs de gestão/não-dev do dashboard de produtividade individual.
    _NON_DEV_BUS = {'Governanca'}
    per_dev = per_dev[~per_dev['BU'].isin(_NON_DEV_BUS)].reset_index(drop=True)

    # Papel por pessoa: 'Tech Lead' ou 'Dev' (via people_config.json)
    role_index = _load_person_role_map()
    per_dev['Papel'] = per_dev['Pessoa'].apply(lambda p: _person_role(p, role_index=role_index))

    # Score de Complexidade Unificado: itens ENTREGUES ponderados por SP ou T-shirt.
    # Equaliza os dois formatos de estimativa (Kitchenham & Mendes, TSE 2004).
    # Peso: sem estimativa=0.5, P(1-3 SP)=1.0, M(5-8 SP)=2.0, G(13+ SP)=3.0
    if not done_window.empty:
        dw_cx = done_window.copy()
        # _SP_Efetivo: SP original > T-shirt equalizado > inferência por mediana condicional.
        dw_cx['_Unified_Weight'] = dw_cx['_SP_Efetivo'].apply(_sp_weight)
        per_dev['Score Complexidade'] = per_dev['Pessoa'].map(
            dw_cx.groupby('_Pessoa')['_Unified_Weight'].sum()
        ).fillna(0).round(1)
    else:
        per_dev['Score Complexidade'] = per_dev['Itens Entregues'].astype(float)

    # Score de Complexidade dos itens PUXADOS — denominador para a taxa de conclusão (EEE no IED).
    # "De todo o trabalho estimado comprometido (puxado), quanto foi efetivamente entregue?"
    if not started_window.empty:
        sw_cx = started_window.copy()
        # _SP_Efetivo: SP original > T-shirt equalizado > inferência por mediana condicional.
        sw_cx['_Unified_Weight'] = sw_cx['_SP_Efetivo'].apply(_sp_weight)
        per_dev['Score Complexidade Puxado'] = per_dev['Pessoa'].map(
            sw_cx.groupby('_Pessoa')['_Unified_Weight'].sum()
        ).fillna(0).round(1)
    else:
        per_dev['Score Complexidade Puxado'] = 0.0

    # ECR — Estimation Coverage Rate: % de itens puxados com estimativa real (não inferida).
    # Mede confiabilidade do IED/IEF: devs com ECR baixo têm scores baseados em inferência estatística.
    # Referência: Kitchenham & Mendes (TSE 2004) — estimativa como pré-requisito de comparabilidade.
    if not started_window.empty and '_SP_Inferido' in started_window.columns:
        _n_inf = started_window.groupby('_Pessoa')['_SP_Inferido'].sum()
        _n_tot = started_window.groupby('_Pessoa').size()
        per_dev['ECR'] = per_dev['Pessoa'].map(
            (1 - _n_inf / _n_tot.clip(lower=1)) * 100
        ).fillna(100.0).clip(0, 100).round(1)
    else:
        per_dev['ECR'] = 100.0

    per_dev = per_dev[per_dev['Pessoa'].astype(str).str.strip().ne('')]
    per_dev = per_dev.sort_values(
        ['Itens Entregues', 'Itens Puxados', 'Pessoa'],
        ascending=[False, False, True]
    ).reset_index(drop=True)

    # Propaga BU e Papel para complexity_df e category_df
    if not complexity_df.empty:
        complexity_df['BU'] = complexity_df['Pessoa'].apply(lambda p: _person_bu(p, bu_index=bu_index))
        complexity_df['Papel'] = complexity_df['Pessoa'].apply(lambda p: _person_role(p, role_index=role_index))
    if not category_df.empty:
        category_df['BU'] = category_df['Pessoa'].apply(lambda p: _person_bu(p, bu_index=bu_index))

    return per_dev, complexity_df, category_df


def _compute_ied(per_dev: pd.DataFrame, nds_p75_anchor: dict = None) -> pd.DataFrame:
    """Calcula o Índice de Entrega do Desenvolvedor (IED) — 0 a 100.

    Fórmula (baseada em Maspupah et al. 2023 + Kitchenham & Mendes 2004 + SPACE Forsgren 2021):

        IED = 0.35 × NDS + 0.30 × EEE + 0.15 × VEL + 0.20 × QUA

    Componentes
    -----------
    NDS — Normalized Delivery Score (35 %)
        Score_Complexidade_Entregue / P75(grupo) × 100.
        Volume de entregas ponderado por complexidade em relação ao grupo.
        Quando nds_p75_anchor é fornecido, usa esses valores como referência estável
        (ex: P75 rolling 3 meses) em vez do P75 do período atual — evita instabilidade
        em grupos pequenos ou períodos curtos.
        Fonte: Jørgensen (IST 2023) — P75 como referência de entrega.

    EEE — Eficiência Estimativa→Entrega (30 %)
        Score_Complexidade_Entregue / Score_Complexidade_Puxado × 100, capped em 100.
        "De todo o trabalho estimado que o dev comprometeu (puxou), quanto foi entregue?"
        Cap em 100: entrega acima do comprometido é positivo mas não deve compensar NDS baixo.
        Fallback: Flow Efficiency (%) quando Score Complexidade Puxado = 0.
        Fonte: Kitchenham & Mendes (TSE 2004) — AdjustedSize/Esforço.

    VEL — Velocidade relativa (15 %)
        Mediana_LT_grupo / LT_dev × 100 — menor lead time = maior velocidade.
        Peso reduzido para não penalizar devs em itens intrinsecamente complexos.
        Fonte: Flournoy et al. (EMSE 2025) — cycle time como proxy de produtividade.

    QUA — Qualidade (20 %)
        100 − % Demanda Falha (com suavização Bayesiana) — penaliza defeitos no output.
        Peso aumentado para 20%: defeitos têm custo real de retrabalho e confiabilidade.
        Fonte: Forsgren et al. (SPACE, ACM Queue 2021).

    Classificação
    -------------
    85–100 : Excelente
    70–84  : Bom
    50–69  : Regular
    30–49  : Abaixo do Esperado
    0–29   : Crítico

    Parâmetros
    ----------
    nds_p75_anchor : dict, optional
        Mapa {papel: p75_value} com valores de P75 de referência estável (ex: rolling 3 meses).
        Quando fornecido, substitui o cálculo de P75 do período atual para o NDS.
    """
    df = per_dev.copy()

    # ── NDS: Volume ajustado por complexidade vs P75 do grupo por papel ───────
    # P75 calculado separadamente para Dev e Tech Lead evita penalização sistemática
    # de TLs que entregam menos itens que devs de linha (papel estruturalmente distinto).
    # Quando nds_p75_anchor é fornecido (ex: P75 rolling de 3 meses), usa esses valores
    # como referência estável — evita distorção em períodos curtos ou grupos pequenos.
    _cx_col = 'Score Complexidade'
    _cx_vals = pd.to_numeric(df.get(_cx_col, 0), errors='coerce').fillna(0)
    if nds_p75_anchor and isinstance(nds_p75_anchor, dict):
        # Usa P75 anchorado (rolling) fornecido pelo caller
        _cx_p75_arr = df['Papel'].map(nds_p75_anchor).fillna(
            max(nds_p75_anchor.values()) if nds_p75_anchor else 1.0
        ).clip(lower=0.1) if 'Papel' in df.columns else pd.Series(
            max(nds_p75_anchor.values()), index=df.index
        )
        df['_ied_nds'] = (_cx_vals / _cx_p75_arr * 100).clip(0, 100).round(1)
    elif 'Papel' in df.columns and _cx_col in df.columns and df['Papel'].nunique() > 1:
        _cx_p75_map = df.groupby('Papel')[_cx_col].quantile(0.75).clip(lower=0.1)
        _cx_p75_arr = df['Papel'].map(_cx_p75_map).fillna(1.0).clip(lower=0.1)
        df['_ied_nds'] = (_cx_vals / _cx_p75_arr * 100).clip(0, 100).round(1)
    else:
        _cx_p75 = max(float(df[_cx_col].quantile(0.75)) if _cx_col in df.columns else 1.0, 0.1)
        df['_ied_nds'] = (_cx_vals / _cx_p75 * 100).clip(0, 100).round(1)

    # ── EEE: Taxa de conclusão do trabalho estimado comprometido ──────────────
    _cx_pux_col = 'Score Complexidade Puxado'
    if _cx_pux_col in df.columns:
        _cx_pux = pd.to_numeric(df[_cx_pux_col], errors='coerce').fillna(0)
        # Prefere FE Ajustada (corrigida para cross-period); fallback para FE bruta ou neutro 50
        _fe_col_ied = 'FE Ajustada (%)' if 'FE Ajustada (%)' in df.columns else 'Flow Efficiency (%)'
        _flow_eff = pd.to_numeric(df.get(_fe_col_ied, 50.0), errors='coerce').fillna(50.0)
        df['_ied_eee'] = np.where(
            _cx_pux > 0,
            (_cx_vals / _cx_pux * 100).clip(0, 100),
            _flow_eff.clip(0, 100),
        ).round(1)
    elif 'FE Ajustada (%)' in df.columns:
        df['_ied_eee'] = pd.to_numeric(df['FE Ajustada (%)'], errors='coerce').fillna(50.0).clip(0, 100).round(1)
    elif 'Flow Efficiency (%)' in df.columns:
        df['_ied_eee'] = pd.to_numeric(df['Flow Efficiency (%)'], errors='coerce').fillna(50.0).clip(0, 100).round(1)
    else:
        df['_ied_eee'] = 50.0

    # ── VEL: Velocidade relativa (menor LT = mais produtivo) ──────────────────
    if 'Lead Time Mediano (dias)' in df.columns:
        _lt = pd.to_numeric(df['Lead Time Mediano (dias)'], errors='coerce').fillna(0)
        _lt_positivos = _lt[_lt > 0]
        _lt_median_grupo = max(float(_lt_positivos.median()) if not _lt_positivos.empty else 1.0, 0.5)
        # Fallback: mediana de VEL dos devs com LT válido (mais informativo que fixo 50)
        _vel_validos = (_lt_median_grupo / _lt_positivos * 100).clip(0, 100)
        _vel_fallback = float(_vel_validos.median()) if not _vel_validos.empty else 50.0
        df['_ied_vel'] = np.where(
            _lt > 0,
            (_lt_median_grupo / _lt * 100).clip(0, 100),
            _vel_fallback,  # sem lead time → mediana de velocidade do grupo
        ).round(1)
    else:
        df['_ied_vel'] = 50.0

    # ── QUA: Qualidade com suavização Bayesiana ────────────────────────────────
    # Para baixo volume (ex: 1 defeito em 1 entrega), QUA raw = 0 — distorção severa.
    # Prior Beta(α=0.5, β=9.5): taxa de falha a priori = 5%, concentrado próximo de zero.
    # Fonte: Gelman et al. (BDA 3rd ed.) — Laplace/Empirical Bayes para proporções esparsas.
    _QUA_PRIOR_ALPHA = 0.5   # defeitos prior
    _QUA_PRIOR_BETA  = 9.5   # não-defeitos prior
    if 'Defeitos Entregues' in df.columns and 'Itens Entregues' in df.columns:
        _defeitos = pd.to_numeric(df['Defeitos Entregues'], errors='coerce').fillna(0)
        _entregas = pd.to_numeric(df['Itens Entregues'], errors='coerce').fillna(0)
        _p_falha_bayes = (
            (_defeitos + _QUA_PRIOR_ALPHA) /
            (_entregas + _QUA_PRIOR_ALPHA + _QUA_PRIOR_BETA)
        )
        df['_ied_qua'] = (1 - _p_falha_bayes).clip(0, 1).mul(100).round(1)
    elif '% Demanda Falha' in df.columns:
        df['_ied_qua'] = (100 - pd.to_numeric(df['% Demanda Falha'], errors='coerce').fillna(0).clip(0, 100)).round(1)
    else:
        df['_ied_qua'] = 80.0

    # ── IED Final ──────────────────────────────────────────────────────────────
    df['IED'] = (
        df['_ied_nds'] * 0.35 +
        df['_ied_eee'] * 0.30 +
        df['_ied_vel'] * 0.15 +
        df['_ied_qua'] * 0.20
    ).round(1)

    # Devs sem nenhuma entrega ficam com IED = 0 (sem base de cálculo válida)
    _sem_entrega = pd.to_numeric(df.get('Itens Entregues', 0), errors='coerce').fillna(0) == 0
    df.loc[_sem_entrega, 'IED'] = 0.0

    # ── Classificação ──────────────────────────────────────────────────────────
    def _ied_classe(v):
        if v >= 85:
            return 'Excelente'
        if v >= 70:
            return 'Bom'
        if v >= 50:
            return 'Regular'
        if v >= 30:
            return 'Abaixo do Esperado'
        return 'Crítico'

    df['IED Classe'] = df['IED'].apply(_ied_classe)

    # ── Confiança IED — badge de cobertura de estimativa ───────────────────────
    # Scores de devs com ECR < 50% são baseados majoritariamente em inferência estatística.
    # O badge alerta o gestor sem invalidar o IED — apenas contextualiza a confiabilidade.
    # Fonte: Kitchenham & Mendes (TSE 2004) — estimativa como pré-requisito de comparabilidade.
    if 'ECR' in df.columns:
        df['Confiança IED'] = df['ECR'].apply(
            lambda v: '⚠ ECR<50%' if pd.notna(v) and v < 50 else '✓'
        )

    return df


def _compute_monthly_ied_series(df_base, start_ts, end_ts, alias_index=None, min_items_per_month=2):
    """Retorna {pessoa: [(month_label, ied_value), ...]} para sparklines temporais de IED.

    Divide o período em meses completos, chama build_dev_productivity_metrics +
    _compute_ied em cada fatia e agrega os resultados por dev. Por padrão, meses
    com menos de 2 entregas para um dev são omitidos da série (gap no sparkline).
    Guarda no máximo 24 meses para não tornar a renderização pesada.
    """
    result = {}
    if df_base is None or df_base.empty:
        return result
    if 'DataDone' not in df_base.columns:
        return result

    try:
        from dateutil.relativedelta import relativedelta as _rdelta
    except ImportError:
        return result

    # Monta lista de intervalos mensais dentro do período
    months = []
    cur = start_ts.replace(day=1)
    while cur < end_ts and len(months) < 24:
        m_end = cur + _rdelta(months=1)
        months.append((cur, min(m_end, end_ts), cur.strftime('%b/%y')))
        cur = m_end

    if len(months) < 2:
        return result

    # Computa P75 estável do período completo para usar como âncora do NDS em cada mês.
    # Evita distorção quando um mês tem apenas 2-3 devs ativos (P75 ponto a ponto é ruidoso).
    _p75_anchor = None
    try:
        _pd_full, _, _ = build_dev_productivity_metrics(df_base, start_ts, end_ts)
        if not _pd_full.empty and 'Score Complexidade' in _pd_full.columns and 'Papel' in _pd_full.columns:
            _p75_anchor = _pd_full.groupby('Papel')['Score Complexidade'].quantile(0.75).clip(lower=0.1).to_dict()
        elif not _pd_full.empty and 'Score Complexidade' in _pd_full.columns:
            _p75_global = max(float(_pd_full['Score Complexidade'].quantile(0.75)), 0.1)
            _p75_anchor = {'Dev': _p75_global, 'Tech Lead': _p75_global}
    except Exception:
        pass

    for m_start, m_end, m_label in months:
        try:
            _pd_m, _, _ = build_dev_productivity_metrics(df_base, m_start, m_end)
            if _pd_m.empty or 'Pessoa' not in _pd_m.columns:
                continue
            _pd_m = _compute_ied(_pd_m, nds_p75_anchor=_p75_anchor)
            for _, row in _pd_m.iterrows():
                pessoa = str(row.get('Pessoa', ''))
                ied = float(row.get('IED', 0) or 0)
                n_entregues = int(row.get('Itens Entregues', 0) or 0)
                if pessoa and n_entregues >= max(int(min_items_per_month or 0), 1):
                    result.setdefault(pessoa, []).append((m_label, ied))
        except Exception:
            continue

    return result


def _compute_monthly_ecr_series(df_base, start_ts, end_ts, alias_index=None, min_items_per_month=2):
    """Retorna {pessoa: [(month_label, ecr_value, itens_puxados), ...]} para tendência mensal de ECR.

    O ECR é recalculado mês a mês usando a mesma lógica de `build_dev_productivity_metrics`.
    Por padrão, meses com menos de 2 itens puxados por dev são omitidos para reduzir ruído.
    """
    result = {}
    if df_base is None or df_base.empty:
        return result
    if 'DataInProgress' not in df_base.columns:
        return result

    try:
        from dateutil.relativedelta import relativedelta as _rdelta
    except ImportError:
        return result

    start_ts = pd.to_datetime(start_ts)
    end_ts = pd.to_datetime(end_ts)

    months = []
    cur = start_ts.replace(day=1)
    while cur < end_ts and len(months) < 24:
        m_end = cur + _rdelta(months=1)
        months.append((cur, min(m_end, end_ts), cur.strftime('%b/%y')))
        cur = m_end

    for m_start, m_end, m_label in months:
        try:
            _pd_m, _, _ = build_dev_productivity_metrics(df_base, m_start, m_end)
            if _pd_m.empty or 'Pessoa' not in _pd_m.columns or 'ECR' not in _pd_m.columns:
                continue
            for _, row in _pd_m.iterrows():
                pessoa = str(row.get('Pessoa', '') or '').strip()
                ecr = pd.to_numeric(pd.Series([row.get('ECR', np.nan)]), errors='coerce').iloc[0]
                itens_puxados = int(row.get('Itens Puxados', 0) or 0)
                if pessoa and pd.notna(ecr) and itens_puxados >= max(int(min_items_per_month or 0), 1):
                    result.setdefault(pessoa, []).append((m_label, float(ecr), itens_puxados))
        except Exception:
            continue

    return result


def _compute_dev_aging_rates(df_base, start_ts, end_ts, alias_index=None, threshold_days=30):
    """Retorna taxa de aging por dev separando `rescue` (entregues) de `pull` (puxados)."""
    empty = pd.DataFrame(columns=['Pessoa', 'Aging Rescue Rate (%)', 'Aging Pull Rate (%)'])
    if df_base is None or df_base.empty or 'DataInProgress' not in df_base.columns:
        return empty

    aging_df = df_base.copy()
    creation_series = resolve_creation_date_series(aging_df)
    if not creation_series.notna().any():
        return empty

    aging_df['_DataCriacao'] = creation_series
    aging_df['_Pessoa'] = _resolve_dev_person_series(aging_df, alias_index=alias_index)
    aging_df['DataInProgress'] = pd.to_datetime(aging_df['DataInProgress'], errors='coerce')
    if 'DataDone' in aging_df.columns:
        aging_df['DataDone'] = pd.to_datetime(aging_df['DataDone'], errors='coerce')
    else:
        aging_df['DataDone'] = pd.NaT
    aging_df['_aging_days'] = (aging_df['DataInProgress'] - aging_df['_DataCriacao']).dt.days

    aging_base = aging_df[
        (aging_df['DataInProgress'] >= start_ts) &
        (aging_df['DataInProgress'] < end_ts) &
        aging_df['_Pessoa'].astype(str).str.strip().ne('') &
        aging_df['_aging_days'].notna()
    ].copy()
    if aging_base.empty:
        return empty

    total_pulled_g = aging_base.groupby('_Pessoa').size()
    aged_pulled_g = aging_base[
        aging_base['_aging_days'] > threshold_days
    ].groupby('_Pessoa').size()
    result = (
        (aged_pulled_g / total_pulled_g.clip(lower=1) * 100)
        .round(1)
        .rename('Aging Pull Rate (%)')
        .reset_index()
        .rename(columns={'_Pessoa': 'Pessoa'})
    )

    aging_delivered = aging_base[
        (aging_base['DataDone'] >= start_ts) &
        (aging_base['DataDone'] < end_ts)
    ].copy()
    if callable(done_time_eligible_mask):
        try:
            aging_delivered = aging_delivered[done_time_eligible_mask(aging_delivered)]
        except Exception:
            pass
    if not aging_delivered.empty:
        total_delivered_g = aging_delivered.groupby('_Pessoa').size()
        aged_delivered_g = aging_delivered[
            aging_delivered['_aging_days'] > threshold_days
        ].groupby('_Pessoa').size()
        rescue_df = (
            (aged_delivered_g / total_delivered_g.clip(lower=1) * 100)
            .round(1)
            .rename('Aging Rescue Rate (%)')
            .reset_index()
            .rename(columns={'_Pessoa': 'Pessoa'})
        )
        result = result.merge(rescue_df, on='Pessoa', how='outer')

    for col in ['Aging Rescue Rate (%)', 'Aging Pull Rate (%)']:
        if col not in result.columns:
            result[col] = np.nan
    return result


def build_bitbucket_contributor_section(
    projeto,
    start_ts,
    end_ts,
    jira_df=None,
    top_n_people=5,
    weekly_metric='score',
):
    if not projeto:
        return html.Div(
            'Selecione um projeto para visualizar ranking de contribuições no Bitbucket.',
            style={'textAlign': 'center', 'padding': '12px', 'color': '#666'}
        )

    logs = load_project_bitbucket_logs(projeto)
    metrics_df, totals = compute_bitbucket_contributor_metrics(logs, start_ts, end_ts)
    cross_df, cross_totals, _ = compute_cross_source_capacity_metrics(jira_df, logs, start_ts, end_ts)
    if metrics_df.empty and (cross_df is None or cross_df.empty):
        return html.Div(
            f'Sem dados suficientes de contribuições/capacidade para {projeto} no período selecionado.',
            style={'textAlign': 'center', 'padding': '12px', 'color': '#666'}
        )

    def _top_label(col_name):
        max_value = int(metrics_df[col_name].max()) if col_name in metrics_df.columns else 0
        if max_value <= 0:
            return '—'
        leaders = metrics_df[metrics_df[col_name] == max_value]['Pessoa'].head(2).tolist()
        leader_text = ', '.join(leaders)
        return f'{leader_text} ({max_value})'

    bitbucket_panel = html.Div(
        f'Sem dados suficientes de contribuições Bitbucket para {projeto} no período selecionado.',
        style={'textAlign': 'center', 'padding': '12px', 'color': '#666'}
    )
    if not metrics_df.empty:
        kpi_specs = [
            ('Top PRs', _top_label('PRs Abertos')),
            ('Top Aprovações', _top_label('Aprovacoes')),
            ('Top Reprovações', _top_label('Reprovacoes')),
            ('Top PRs Declinados', _top_label('PRs Declinados (Autor)')),
            ('Top Commits', _top_label('Commits')),
        ]
        kpi_cards = [
            html.Div([
                html.Div(label, style={'fontSize': '12px', 'color': '#555', 'marginBottom': '4px'}),
                html.Div(value, style={'fontSize': '14px', 'fontWeight': 'bold'})
            ], style={
                'border': '1px solid #e5e7eb',
                'borderRadius': '8px',
                'padding': '8px 10px',
                'backgroundColor': '#fafafa',
                'minWidth': '180px'
            })
            for label, value in kpi_specs
        ]

        top_rank = metrics_df.head(15).copy()
        table_cols = ['Pessoa', 'PRs Abertos', 'Aprovacoes', 'Reprovacoes', 'PRs Declinados (Autor)', 'Commits']
        fig_rank = px.bar(
            top_rank.sort_values('Total Contribuicoes', ascending=True),
            x='Total Contribuicoes',
            y='Pessoa',
            orientation='h',
            title='Ranking de contribuições (soma das métricas no período)',
            color='Total Contribuicoes',
            color_continuous_scale='Blues'
        )
        fig_rank.update_layout(height=max(320, 38 * len(top_rank) + 120), template='plotly_white', margin=dict(t=60, b=40))
        fig_rank.update_coloraxes(showscale=False)

        bitbucket_panel = html.Div([
            html.Div(
                'Métricas de revisão dependem de colunas de revisores no CSV de PR (approved_by/changes_requested_by).',
                style={'color': '#666', 'fontSize': '12px', 'marginBottom': '8px'}
            ),
            html.Div(kpi_cards, style={'display': 'flex', 'gap': '8px', 'flexWrap': 'wrap', 'marginBottom': '12px'}),
            html.Div([
                html.Span(f"PRs: {totals.get('PRs Abertos', 0)}", style={'marginRight': '14px'}),
                html.Span(f"Aprovações: {totals.get('Aprovacoes', 0)}", style={'marginRight': '14px'}),
                html.Span(f"Reprovações: {totals.get('Reprovacoes', 0)}", style={'marginRight': '14px'}),
                html.Span(f"PRs Declinados: {totals.get('PRs Declinados (Autor)', 0)}", style={'marginRight': '14px'}),
                html.Span(f"Commits: {totals.get('Commits', 0)}"),
            ], style={'fontSize': '12px', 'color': '#555', 'marginBottom': '10px'}),
            dash_table.DataTable(
                columns=[
                    {'name': 'Pessoa', 'id': 'Pessoa'},
                    {'name': 'PRs Abertos', 'id': 'PRs Abertos'},
                    {'name': 'Aprovações', 'id': 'Aprovacoes'},
                    {'name': 'Reprovações', 'id': 'Reprovacoes'},
                    {'name': 'PRs Declinados (Autor)', 'id': 'PRs Declinados (Autor)'},
                    {'name': 'Commits', 'id': 'Commits'},
                ],
                data=top_rank[table_cols].to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '7px'},
                style_cell_conditional=[{'if': {'column_id': 'Pessoa'}, 'textAlign': 'left', 'fontWeight': 'bold'}],
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
                style_table={'overflowX': 'auto'},
            ),
            dcc.Graph(figure=fig_rank),
        ])

    try:
        top_n_people = int(top_n_people)
    except Exception:
        top_n_people = 5
    top_n_people = min(max(top_n_people, 1), 30)

    weekly_metric_map = {
        'score': ('Score Capacidade (%)', 'Score Capacidade (%)'),
        'itens_concluidos': ('Itens Concluidos', 'Itens Concluídos'),
        'commits': ('Commits', 'Commits'),
        'prs_abertos': ('PRs Abertos', 'PRs Abertos'),
    }
    weekly_metric_col, weekly_metric_label = weekly_metric_map.get(str(weekly_metric), weekly_metric_map['score'])

    cross_section = html.Div()
    if cross_df is not None and not cross_df.empty:
        cross_top = cross_df.head(top_n_people).copy()
        cross_cols = [
            'Pessoa',
            'Itens Concluidos',
            'Itens com Evidencia Tecnica',
            'Cobertura Tecnica (%)',
            'PRs Abertos',
            'Aprovacoes',
            'Reprovacoes',
            'Commits',
            'Score Capacidade (%)',
        ]
        fig_cross = px.bar(
            cross_top.sort_values('Score Capacidade (%)', ascending=True),
            x='Score Capacidade (%)',
            y='Pessoa',
            orientation='h',
            title='Capacidade por pessoa (Jira + Bitbucket, índice relativo %)',
            color='Itens Concluidos',
            color_continuous_scale='Tealgrn'
        )
        fig_cross.update_layout(height=max(340, 38 * len(cross_top) + 120), template='plotly_white', margin=dict(t=60, b=40))
        fig_cross.update_coloraxes(showscale=False)

        weekly_df = compute_cross_source_capacity_weekly_metrics(jira_df, logs, start_ts, end_ts)
        weekly_section = html.Div()
        if weekly_df is not None and not weekly_df.empty:
            top_people = cross_top['Pessoa'].head(top_n_people).tolist()
            weekly_top = weekly_df[weekly_df['Pessoa'].isin(top_people)].copy()
            weekly_top = weekly_top.sort_values(['Semana', weekly_metric_col, 'Pessoa'])
            if not weekly_top.empty:
                fig_weekly = px.line(
                    weekly_top,
                    x='Semana',
                    y=weekly_metric_col,
                    color='Pessoa',
                    markers=True,
                    title=f'Tendência semanal de capacidade ({weekly_metric_label}, Top {top_n_people})'
                )
                fig_weekly.update_layout(template='plotly_white', margin=dict(t=60, b=40), legend_title_text='Pessoa')
                if weekly_metric_col == 'Score Capacidade (%)':
                    fig_weekly.update_yaxes(ticksuffix='%')
                weekly_section = html.Div([
                    dcc.Graph(figure=fig_weekly),
                ])

        cross_top_table = cross_top[cross_cols].copy()
        cross_top_table['Score Capacidade (%)'] = pd.to_numeric(
            cross_top_table['Score Capacidade (%)'], errors='coerce'
        ).fillna(0).map(lambda v: f'{v:.2f}%')

        cross_section = html.Div([
            html.H4('Capacidade Cruzada (Jira + Bitbucket)', style={'marginTop': '28px', 'marginBottom': '10px'}),
            html.Div(
                'Score (%) = índice relativo ao maior score bruto do período (100% = maior contribuição relativa no recorte), onde score bruto = itens concluídos + PRs + aprovações + reprovações + commits/5.',
                style={'color': '#666', 'fontSize': '12px', 'marginBottom': '8px'}
            ),
            html.Div([
                html.Span(f"Itens concluídos: {cross_totals.get('Itens Concluidos', 0)}", style={'marginRight': '14px'}),
                html.Span(f"Itens com evidência técnica: {cross_totals.get('Itens com Evidencia Tecnica', 0)}", style={'marginRight': '14px'}),
                html.Span(f"PRs: {cross_totals.get('PRs Abertos', 0)}", style={'marginRight': '14px'}),
                html.Span(f"Aprovações: {cross_totals.get('Aprovacoes', 0)}", style={'marginRight': '14px'}),
                html.Span(f"Reprovações: {cross_totals.get('Reprovacoes', 0)}", style={'marginRight': '14px'}),
                html.Span(f"Commits: {cross_totals.get('Commits', 0)}"),
            ], style={'fontSize': '12px', 'color': '#555', 'marginBottom': '10px'}),
            dash_table.DataTable(
                columns=[
                    {'name': 'Pessoa', 'id': 'Pessoa'},
                    {'name': 'Itens Concluídos', 'id': 'Itens Concluidos'},
                    {'name': 'Itens c/ Evidência Técnica', 'id': 'Itens com Evidencia Tecnica'},
                    {'name': 'Cobertura Técnica (%)', 'id': 'Cobertura Tecnica (%)'},
                    {'name': 'PRs Abertos', 'id': 'PRs Abertos'},
                    {'name': 'Aprovações', 'id': 'Aprovacoes'},
                    {'name': 'Reprovações', 'id': 'Reprovacoes'},
                    {'name': 'Commits', 'id': 'Commits'},
                    {'name': 'Score Capacidade (%)', 'id': 'Score Capacidade (%)'},
                ],
                data=cross_top_table.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '7px'},
                style_cell_conditional=[{'if': {'column_id': 'Pessoa'}, 'textAlign': 'left', 'fontWeight': 'bold'}],
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
                style_table={'overflowX': 'auto'},
            ),
            dcc.Graph(figure=fig_cross),
            weekly_section,
        ], style={'marginTop': '16px'})

    return html.Div([
        html.H4('Contribuições Bitbucket (CSV)', style={'marginTop': '28px', 'marginBottom': '10px'}),
        bitbucket_panel,
        cross_section,
    ], style={'marginTop': '16px'})


def _extract_work_item_keys_from_bitbucket_logs(bitbucket_logs, start_ts, end_ts):
    tech_keys = set()
    if not isinstance(bitbucket_logs, dict):
        return tech_keys
    for source_name, date_col in (('commits', 'date'), ('pullrequests', 'created_on')):
        src = bitbucket_logs.get(source_name, pd.DataFrame())
        if src is None or src.empty:
            continue
        x = src.copy()
        if date_col in x.columns:
            x = x[(x[date_col] >= start_ts) & (x[date_col] < end_ts)]
        for col in ('work_item_keys', 'primary_work_item_key'):
            if col not in x.columns:
                continue
            for raw in x[col].fillna('').astype(str):
                for key in raw.split('|'):
                    cleaned = key.strip().upper()
                    if cleaned:
                        tech_keys.add(cleaned)
    return tech_keys


def build_pm_commits_vs_jira_report(pm_people, pm_cases, start_ts, end_ts, responsavel=None):
    alias_index = _load_person_alias_index()
    jira_people = pd.DataFrame(columns=['Pessoa', 'Itens Concluidos'])
    if pm_people is not None and not pm_people.empty and {'Responsavel', 'Itens Concluidos'}.issubset(pm_people.columns):
        jira_people = pm_people[['Responsavel', 'Itens Concluidos']].copy()
        jira_people['Pessoa'] = jira_people['Responsavel'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
        jira_people['Itens Concluidos'] = pd.to_numeric(jira_people['Itens Concluidos'], errors='coerce').fillna(0)
        jira_people = (
            jira_people[jira_people['Pessoa'].astype(str).str.strip().ne('')]
            .groupby('Pessoa', as_index=False)['Itens Concluidos']
            .sum()
        )

    logs = load_project_bitbucket_logs('W1NNER')
    bb_people, _ = compute_bitbucket_contributor_metrics(logs, start_ts, end_ts, alias_index=alias_index)
    if bb_people is None or bb_people.empty:
        bb_people = pd.DataFrame(columns=['Pessoa', 'Commits', 'PRs Abertos'])
    for col in ('Pessoa', 'Commits', 'PRs Abertos'):
        if col not in bb_people.columns:
            bb_people[col] = 0 if col != 'Pessoa' else ''
    bb_people = bb_people[['Pessoa', 'Commits', 'PRs Abertos']].copy()
    bb_people['Commits'] = pd.to_numeric(bb_people['Commits'], errors='coerce').fillna(0)
    bb_people['PRs Abertos'] = pd.to_numeric(bb_people['PRs Abertos'], errors='coerce').fillna(0)

    merged = pd.merge(jira_people, bb_people, how='outer', on='Pessoa')
    if merged.empty:
        return html.Div('Sem dados suficientes de Jira/Bitbucket para montar a correlação.', style={'color': '#666'})

    merged['Itens Concluidos'] = pd.to_numeric(merged.get('Itens Concluidos', 0), errors='coerce').fillna(0)
    merged['Commits'] = pd.to_numeric(merged.get('Commits', 0), errors='coerce').fillna(0)
    merged['PRs Abertos'] = pd.to_numeric(merged.get('PRs Abertos', 0), errors='coerce').fillna(0)

    def _classify(row):
        done = float(row.get('Itens Concluidos', 0) or 0)
        commits = float(row.get('Commits', 0) or 0)
        if done > 0 and commits <= 0:
            return 'Alta vazão sem commits'
        if done <= 0 and commits > 0:
            return 'Commits sem conclusão Jira'
        if done > 0 and commits > 0:
            return 'Fluxo conectado'
        return 'Sem atividade'

    merged['Classificacao'] = merged.apply(_classify, axis=1)
    merged['PRs+Commits'] = merged['PRs Abertos'] + merged['Commits']
    active = merged[(merged['Itens Concluidos'] > 0) | (merged['Commits'] > 0)].copy()
    active = active.sort_values(['Itens Concluidos', 'Commits'], ascending=[False, False])
    if active.empty:
        return html.Div('Sem atividade no recorte para montar a correlação.', style={'color': '#666'})

    color_map = {
        'Alta vazão sem commits': '#f39c12',
        'Commits sem conclusão Jira': '#d62728',
        'Fluxo conectado': '#2ca02c',
        'Sem atividade': '#7f8c8d',
    }
    fig = px.scatter(
        active,
        x='Commits',
        y='Itens Concluidos',
        color='Classificacao',
        size='PRs+Commits',
        hover_name='Pessoa',
        hover_data={
            'Commits': ':.0f',
            'Itens Concluidos': ':.0f',
            'PRs Abertos': ':.0f',
            'Classificacao': True,
            'PRs+Commits': False,
        },
        color_discrete_map=color_map,
        size_max=38,
        title='Correlação Jira x Bitbucket por Pessoa (Commits x Itens Concluídos)',
    )
    fig.update_traces(marker=dict(opacity=0.88, line=dict(width=1, color='white')))
    fig.add_hline(y=0, line_dash='dash', line_color='#555', opacity=0.6)
    fig.add_vline(x=0, line_dash='dot', line_color='#888', opacity=0.45)
    fig.update_layout(
        template='plotly_white',
        height=760,
        legend_title='Padrão',
        xaxis_title='Commits (Bitbucket)',
        yaxis_title='Itens Concluídos (Jira)',
    )

    focus_people = {
        'Igor Rezende',
        'Christopher Alves',
        'Gabriel de Oliveira Koehler',
        'Lorraine Caribe',
        'Lara Junqueira Alvarenga',
        'Thaís Cabral',
        'Lucas Pizol',
        'Peterson Bem',
    }
    if responsavel:
        focus_people.update(_normalize_responsavel_filter_values(responsavel, alias_index=alias_index, canonicalize=True))
    for _, row in active[active['Pessoa'].isin(focus_people)].iterrows():
        fig.add_annotation(
            x=row['Commits'],
            y=row['Itens Concluidos'],
            text=row['Pessoa'],
            showarrow=True,
            arrowhead=1,
            ax=14,
            ay=-18,
            bgcolor='rgba(255,255,255,0.85)',
            bordercolor='#d0d7de',
            borderwidth=1,
            font=dict(size=11),
        )

    coverage_pct = np.nan
    done_with_evidence = 0
    done_total = 0
    if pm_cases is not None and not pm_cases.empty and 'Issue Key' in pm_cases.columns:
        done_cases = pm_cases.copy()
        if 'Done Final Date' in done_cases.columns:
            done_cases['Done Final Date'] = pd.to_datetime(done_cases['Done Final Date'], errors='coerce')
            done_cases = done_cases[
                done_cases['Done Final Date'].isna() |
                ((done_cases['Done Final Date'] >= start_ts) & (done_cases['Done Final Date'] <= end_ts))
            ]
        if responsavel and 'Done Final Author' in done_cases.columns:
            selected_people = set(_normalize_responsavel_filter_values(responsavel, alias_index=alias_index, canonicalize=True))
            done_authors = done_cases['Done Final Author'].apply(lambda value: _canonical_person_name(value, alias_index=alias_index))
            done_cases = done_cases[done_authors.isin(selected_people)]
        done_cases['Issue Key'] = done_cases['Issue Key'].astype(str).str.strip().str.upper()
        done_cases = done_cases[done_cases['Issue Key'].ne('')]
        tech_keys = _extract_work_item_keys_from_bitbucket_logs(logs, start_ts, end_ts)
        done_total = int(done_cases['Issue Key'].nunique())
        if done_total > 0:
            done_with_evidence = int(done_cases[done_cases['Issue Key'].isin(tech_keys)]['Issue Key'].nunique())
            coverage_pct = (done_with_evidence / done_total) * 100.0

    disconnect_jira = active[(active['Itens Concluidos'] > 0) & (active['Commits'] <= 0)].copy()
    disconnect_jira = disconnect_jira.sort_values('Itens Concluidos', ascending=False).head(8)
    disconnect_bb = active[(active['Commits'] > 0) & (active['Itens Concluidos'] <= 0)].copy()
    disconnect_bb = disconnect_bb.sort_values('Commits', ascending=False).head(8)

    coverage_text = (
        f"Cobertura técnica no recorte: {coverage_pct:.1f}% ({done_with_evidence} de {done_total} itens concluídos com evidência técnica)"
        if pd.notna(coverage_pct) else
        'Cobertura técnica indisponível para o recorte selecionado.'
    )

    return html.Div([
        html.H4('Rastreabilidade Jira x Bitbucket', style={'marginTop': '20px', 'marginBottom': '8px'}),
        html.P(
            'Dispersão por pessoa para evidenciar assimetrias: alta vazão sem commits e atividade técnica sem conclusão no Jira.',
            style={'color': '#555', 'marginBottom': '6px'}
        ),
        html.Div(
            f"Período: {start_ts.date()} a {end_ts.date()} | {coverage_text}",
            style={'fontSize': '12px', 'color': '#444', 'marginBottom': '8px'}
        ),
        dcc.Graph(figure=fig),
        html.Div([
            html.Div([
                html.H5('Alta vazão sem commits', style={'marginBottom': '6px'}),
                dash_table.DataTable(
                    columns=[
                        {'name': 'Pessoa', 'id': 'Pessoa'},
                        {'name': 'Itens Concluídos', 'id': 'Itens Concluidos'},
                        {'name': 'Commits', 'id': 'Commits'},
                        {'name': 'PRs Abertos', 'id': 'PRs Abertos'},
                    ],
                    data=disconnect_jira[['Pessoa', 'Itens Concluidos', 'Commits', 'PRs Abertos']].to_dict('records'),
                    style_cell={'textAlign': 'center', 'padding': '6px'},
                    style_cell_conditional=[{'if': {'column_id': 'Pessoa'}, 'textAlign': 'left', 'fontWeight': 'bold'}],
                    style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                    page_size=8,
                ),
            ], className='six columns'),
            html.Div([
                html.H5('Commits sem conclusão Jira', style={'marginBottom': '6px'}),
                dash_table.DataTable(
                    columns=[
                        {'name': 'Pessoa', 'id': 'Pessoa'},
                        {'name': 'Commits', 'id': 'Commits'},
                        {'name': 'PRs Abertos', 'id': 'PRs Abertos'},
                        {'name': 'Itens Concluídos', 'id': 'Itens Concluidos'},
                    ],
                    data=disconnect_bb[['Pessoa', 'Commits', 'PRs Abertos', 'Itens Concluidos']].to_dict('records'),
                    style_cell={'textAlign': 'center', 'padding': '6px'},
                    style_cell_conditional=[{'if': {'column_id': 'Pessoa'}, 'textAlign': 'left', 'fontWeight': 'bold'}],
                    style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                    page_size=8,
                ),
            ], className='six columns'),
        ], className='row', style={'marginTop': '8px'}),
    ])


def load_pattern_rules():
    return parse_json_env("PATTERN_RULES", parse_json_env("JIRA_PATTERN_RULES", DEFAULT_PATTERN_RULES))


def _parse_env_date(name: str, default_date: date) -> date:
    raw = os.getenv(name, '').strip()
    if not raw:
        return default_date
    try:
        return date.fromisoformat(raw)
    except Exception:
        pass
    try:
        return datetime.strptime(raw, '%Y-%m').date()
    except Exception:
        return default_date


def _bool_env(name: str) -> bool:
    return os.getenv(name, '').strip().lower() in {'1', 'true', 'yes', 'y'}


def _load_four_ps_kanban_csv(csv_source: str) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    if not csv_source:
        return {}
    try:
        df = pd.read_csv(csv_source, dtype=str, keep_default_na=False)
    except Exception as exc:
        print(f"[dashboard_full] Erro ao ler CSV de Kanban 4Ps de {csv_source}: {exc}")
        return {}

    if df.empty:
        return {}

    result: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for _, row in df.iterrows():
        area = str(row.get('area_name', '') or '').strip()
        bucket = str(row.get('bucket', '') or '').strip()
        if not area or bucket not in {'in_progress', 'next_steps', 'blocked', 'done'}:
            continue

        item: Dict[str, Any] = {}
        for column in df.columns:
            if column in {'area_name', 'bucket', 'source'}:
                continue
            value = row.get(column, '')
            if isinstance(value, str):
                item[column] = value.strip()
            else:
                item[column] = value

        item['is_bau'] = str(item.get('is_bau', '')).strip().lower() in {'1', 'true', 'yes', 'y', 'sim'}
        try:
            item['days_stale'] = int(float(str(item.get('days_stale', '')).strip() or 0))
        except Exception:
            item['days_stale'] = 0

        bucket_items = result.setdefault(area, {'in_progress': [], 'next_steps': [], 'blocked': [], 'done': []})
        bucket_items.setdefault(bucket, []).append(item)

    return result


def _load_four_ps_kanban_online(month: date, period_months: int = 1) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    base_url = os.getenv('FLOW_PMO_JIRA_BASE_URL', '').strip() or os.getenv('JIRA_BASE_URL', '').strip()
    email = os.getenv('FLOW_PMO_JIRA_EMAIL', '').strip() or os.getenv('JIRA_EMAIL', '').strip()
    token = os.getenv('FLOW_PMO_JIRA_API_TOKEN', '').strip() or os.getenv('JIRA_API_TOKEN', '').strip()
    if not base_url or not email or not token:
        print('[dashboard_full] Credenciais Jira não configuradas — boards Kanban do 4Ps não serão carregados.')
        return {}
    try:
        client = JiraClient(base_url=base_url, email=email, api_token=token)
        extractor = FourPsKanbanExtractor(client, month=month, period_months=period_months)
        return extractor.fetch_all_kanban()
    except Exception as exc:
        print(f"[dashboard_full] Erro ao extrair Kanban 4Ps online do Jira: {exc}")
        return {}


def _resolve_four_ps_kanban_csv_source() -> str:
    # 1. Caminho local explícito
    csv_source = os.getenv('FLOW_PMO_FOUR_PS_KANBAN_CSV', '').strip()
    if csv_source:
        return csv_source

    # 2. URL remota — baixa para /tmp e retorna path local
    csv_url = os.getenv('FLOW_PMO_FOUR_PS_KANBAN_CSV_URL', '').strip()
    if csv_url:
        try:
            local_path = _download_four_ps_kanban_csv_from_url(csv_url)
            print(f"[dashboard_full] CSV 4Ps baixado do blob: {csv_url}")
            return local_path
        except Exception as exc:
            print(f"[dashboard_full] Aviso: falha ao baixar CSV 4Ps de {csv_url}: {exc}")

    # 3. Fallback: caminhos locais padrão
    root = Path(__file__).resolve().parent
    candidates = [
        root / 'four_ps_kanban.csv',                                  # projeto raiz
        root / 'Dados' / 'latest' / 'latest-upload' / 'four_ps_kanban.csv',
    ]
    for p in candidates:
        if p.exists():
            print(f"[dashboard_full] Usando CSV 4Ps em {p}")
            return str(p)

    return ''


def _load_four_ps_kanban_data(month: date, period_months: int = 1) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    csv_source = _resolve_four_ps_kanban_csv_source()
    if csv_source:
        return _load_four_ps_kanban_csv(csv_source)

    # Tenta online sempre que houver credenciais Jira disponíveis
    base_url = os.getenv('FLOW_PMO_JIRA_BASE_URL', '').strip() or os.getenv('JIRA_BASE_URL', '').strip()
    if base_url:
        return _load_four_ps_kanban_online(month, period_months=period_months)

    return {}


DEFAULT_WEEKLY_WIP_ITEMS_PER_PERSON_LIMIT = float(os.getenv('FLOW_WEEKLY_WIP_ITEMS_PER_PERSON_LIMIT', '2').strip() or '2')


DEFAULT_EXPEDITE_TARGET_PCT = float(os.getenv('FLOW_EXPEDITE_TARGET_PCT', '20').strip() or '20')


DEFAULT_EXPEDITE_CRITICAL_PCT = float(os.getenv('FLOW_EXPEDITE_CRITICAL_PCT', '30').strip() or '30')


DEFAULT_VARIABILITY_CV_WARN = float(os.getenv('FLOW_VARIABILITY_CV_WARN', '0.30').strip() or '0.30')


DEFAULT_VARIABILITY_CV_CRITICAL = float(os.getenv('FLOW_VARIABILITY_CV_CRITICAL', '0.50').strip() or '0.50')


def _safe_ratio(num, den):
    if den is None or den == 0:
        return np.nan
    return float(num) / float(den)


def _safe_pct(num, den):
    if den is None or den == 0:
        return 0.0
    return float(num) / float(den) * 100.0


def _get_weekly_wip_items_per_person_limit():
    raw = os.getenv('FLOW_WEEKLY_WIP_ITEMS_PER_PERSON_LIMIT', '').strip()
    if not raw:
        return DEFAULT_WEEKLY_WIP_ITEMS_PER_PERSON_LIMIT
    try:
        value = float(raw)
        return value if value > 0 else DEFAULT_WEEKLY_WIP_ITEMS_PER_PERSON_LIMIT
    except Exception:
        return DEFAULT_WEEKLY_WIP_ITEMS_PER_PERSON_LIMIT


def _get_expedite_target_pct():
    raw = os.getenv('FLOW_EXPEDITE_TARGET_PCT', '').strip()
    if not raw:
        return DEFAULT_EXPEDITE_TARGET_PCT
    try:
        value = float(raw)
        return value if value >= 0 else DEFAULT_EXPEDITE_TARGET_PCT
    except Exception:
        return DEFAULT_EXPEDITE_TARGET_PCT


def _get_expedite_critical_pct():
    raw = os.getenv('FLOW_EXPEDITE_CRITICAL_PCT', '').strip()
    if not raw:
        return DEFAULT_EXPEDITE_CRITICAL_PCT
    try:
        value = float(raw)
        return value if value >= 0 else DEFAULT_EXPEDITE_CRITICAL_PCT
    except Exception:
        return DEFAULT_EXPEDITE_CRITICAL_PCT


def _get_variability_cv_warn():
    raw = os.getenv('FLOW_VARIABILITY_CV_WARN', '').strip()
    if not raw:
        return DEFAULT_VARIABILITY_CV_WARN
    try:
        value = float(raw)
        return value if value > 0 else DEFAULT_VARIABILITY_CV_WARN
    except Exception:
        return DEFAULT_VARIABILITY_CV_WARN


def _get_variability_cv_critical():
    raw = os.getenv('FLOW_VARIABILITY_CV_CRITICAL', '').strip()
    if not raw:
        return DEFAULT_VARIABILITY_CV_CRITICAL
    try:
        value = float(raw)
        return value if value > 0 else DEFAULT_VARIABILITY_CV_CRITICAL
    except Exception:
        return DEFAULT_VARIABILITY_CV_CRITICAL


def _is_expedite_service_class(value):
    return is_highest_alias(value)


def _variability_status(cv_value, warn=None, critical=None):
    warn = _get_variability_cv_warn() if warn is None else float(warn)
    critical = _get_variability_cv_critical() if critical is None else float(critical)
    if pd.isna(cv_value):
        return 'Sem base'
    if cv_value < warn:
        return 'OK'
    if cv_value < critical:
        return 'Atenção'
    return 'Crítico'


def detect_systemic_patterns(df_source, start_ts, end_ts, rules):
    detail_cols = [
        'Projeto', 'Semana', 'Padrão', 'Severidade', 'Regras Acionadas', 'Highest (%)',
        'Pressure (λ/μ)', 'Failure Demand (%)', 'Predictability (P85/P50)',
        'Lead Time P85', 'WIP/Throughput', 'Blocked (%)', 'Discard (%)', 'WIP Age / LT P85'
    ]
    summary_cols = ['Padrão', 'Severidade', 'Ocorrências']
    pattern_labels = {
        "urgencia_cronica": "Times operando em estado de urgência",
        "burnout": "Times em processo de burnout",
        "confianca_comprometida": "Times comprometendo a confiança do cliente",
        "problema_sistemico_fluxo": "Times com problemas sistêmicos de fluxo",
        "atrasos_desperdicios": "Times com atrasos e desperdícios",
        "estagnacao": "Times estagnados",
        "compromisso_prematuro": "Times com compromisso prematuro",
    }
    weeks = pd.date_range(start=start_ts, end=end_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
    rows = []
    if len(weeks) < 2:
        return pd.DataFrame(columns=detail_cols), pd.DataFrame(columns=summary_cols)

    if 'Projeto' in df_source.columns:
        project_groups = [
            ('Sem Projeto' if pd.isna(project_name) else str(project_name).strip(), group.copy())
            for project_name, group in df_source.groupby('Projeto', dropna=False)
            if not group.empty
        ]
    else:
        project_groups = [(PROJECT_FILTER_ALL_LABEL, df_source.copy())]

    for project_name, project_df in project_groups:
        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]
            arrivals = project_df[(project_df['DataInProgress'] >= week_start) & (project_df['DataInProgress'] < week_end)]
            done = project_df[(project_df['DataDone'] >= week_start) & (project_df['DataDone'] < week_end)]
            wip = project_df[(project_df['DataInProgress'] < week_end) & ((project_df['DataDone'] >= week_end) | pd.isna(project_df['DataDone']))]

            tp = len(done)
            inflow = len(arrivals)
            flow_pressure = _safe_ratio(inflow, tp)
            wip_tp_ratio = _safe_ratio(len(wip), tp)
            lead_times = time_metric_series(done, 'LeadTime_Dias')
            lt_p85 = exact_empirical_percentile(lead_times, 0.85) if not lead_times.empty else 0.0
            lt_p50 = exact_empirical_percentile(lead_times, 0.50) if not lead_times.empty else 0.0
            predictability = _safe_ratio(lt_p85, lt_p50) if lt_p50 > 0 else np.nan

            defects = len(done[done['TipoDemanda'] == TYPE_ISSUES]) if 'TipoDemanda' in done.columns else 0
            failure_pct = _safe_pct(defects, tp)
            expedite_arrivals = int(arrivals['ClasseServico'].apply(_is_expedite_service_class).sum()) if 'ClasseServico' in arrivals.columns else 0
            expedite_pct = _safe_pct(expedite_arrivals, inflow)
            blocked_rate = _safe_pct(wip['Bloqueado'].sum(), len(wip)) if 'Bloqueado' in wip.columns and len(wip) > 0 else 0.0
            discard_rate = _safe_pct(done['Descartado'].sum(), tp) if 'Descartado' in done.columns and tp > 0 else 0.0
            wip_age = (week_end - wip['DataInProgress']).dt.days.mean() if len(wip) > 0 else 0.0
            wip_age_over_p85 = _safe_ratio(wip_age, lt_p85) if lt_p85 > 0 else np.nan

            signals = {
                "expedite_pct": float(expedite_pct),
                "flow_pressure": float(flow_pressure) if pd.notna(flow_pressure) else np.nan,
                "failure_demand_pct": float(failure_pct),
                "predictability_ratio": float(predictability) if pd.notna(predictability) else np.nan,
                "lead_time_p85": float(lt_p85),
                "wip_tp_ratio": float(wip_tp_ratio) if pd.notna(wip_tp_ratio) else np.nan,
                "blocked_rate": float(blocked_rate),
                "discard_rate": float(discard_rate),
                "wip_age_over_p85": float(wip_age_over_p85) if pd.notna(wip_age_over_p85) else np.nan,
                "inflow": inflow,
                "throughput": tp,
                "wip": len(wip),
            }

            for pattern_key, thresholds in rules.items():
                hits = []
                for metric, threshold in thresholds.items():
                    signal_name = metric.replace('_min', '').replace('_max', '')
                    value = signals.get(signal_name, np.nan)
                    if metric.endswith('_max'):
                        if pd.notna(value) and value <= float(threshold):
                            hits.append(f"{signal_name}<={threshold}")
                    else:
                        if pd.notna(value) and value >= float(threshold):
                            hits.append(f"{signal_name}>={threshold}")
                min_hits = max(1, int(np.ceil(len(thresholds) * 0.6)))
                if len(hits) < min_hits:
                    continue
                severity = 'Crítico' if len(hits) >= len(thresholds) else 'Atenção'
                rows.append({
                    'Projeto': project_name,
                    'Semana': week_start.date(),
                    'Padrão': pattern_labels.get(pattern_key, pattern_key),
                    'Severidade': severity,
                    'Regras Acionadas': ' | '.join(hits),
                    'Highest (%)': round(signals['expedite_pct'], 2),
                    'Pressure (λ/μ)': round(signals['flow_pressure'], 3) if pd.notna(signals['flow_pressure']) else np.nan,
                    'Failure Demand (%)': round(signals['failure_demand_pct'], 2),
                    'Predictability (P85/P50)': round(signals['predictability_ratio'], 2) if pd.notna(signals['predictability_ratio']) else np.nan,
                    'Lead Time P85': round(signals['lead_time_p85'], 2),
                    'WIP/Throughput': round(signals['wip_tp_ratio'], 2) if pd.notna(signals['wip_tp_ratio']) else np.nan,
                    'Blocked (%)': round(signals['blocked_rate'], 2),
                    'Discard (%)': round(signals['discard_rate'], 2),
                    'WIP Age / LT P85': round(signals['wip_age_over_p85'], 2) if pd.notna(signals['wip_age_over_p85']) else np.nan,
                })

    details = pd.DataFrame(rows)
    if details.empty:
        return pd.DataFrame(columns=detail_cols), pd.DataFrame(columns=summary_cols)
    summary = (
        details.groupby(['Padrão', 'Severidade'], as_index=False)
        .size()
        .rename(columns={'size': 'Ocorrências'})
        .sort_values('Ocorrências', ascending=False)
    )
    return details, summary


def build_weekly_flow_checklist_and_diagnosis(df_source, start_ts, end_ts):
    weeks = pd.date_range(start=start_ts, end=end_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
    wip_items_per_person_limit = _get_weekly_wip_items_per_person_limit()
    if len(weeks) < 2 or df_source is None or df_source.empty:
        empty_checklist = pd.DataFrame(columns=['Checklist', 'Status', 'Observado', 'Referência', 'Leitura'])
        empty_diag = pd.DataFrame(columns=['Semana', 'Padrão Observado', 'Diagnóstico Provável', 'Ação Recomendada', 'Severidade'])
        empty_weekly = pd.DataFrame()
        return empty_checklist, empty_diag, empty_weekly

    rows = []
    for i in range(len(weeks) - 1):
        week_start = weeks[i]
        week_end = weeks[i + 1]
        arrived = df_source[(df_source['DataInProgress'] >= week_start) & (df_source['DataInProgress'] < week_end)]
        done = df_source[(df_source['DataDone'] >= week_start) & (df_source['DataDone'] < week_end)]
        done = done[done_time_eligible_mask(done)] if not done.empty else done
        wip = df_source[(df_source['DataInProgress'] < week_end) & ((df_source['DataDone'] >= week_end) | pd.isna(df_source['DataDone']))].copy()

        cycle_series = time_metric_series(done, 'TempoExecucao_Dias', non_negative=True)
        if cycle_series.empty:
            cycle_series = time_metric_series(done, 'CycleTime_Dias', non_negative=True)
        cycle_p50 = exact_empirical_percentile(cycle_series, 0.50) if not cycle_series.empty else np.nan
        cycle_p85 = exact_empirical_percentile(cycle_series, 0.85) if not cycle_series.empty else np.nan
        cycle_mean = float(cycle_series.mean()) if not cycle_series.empty else np.nan
        cycle_cv = float(cycle_series.std() / cycle_series.mean()) if len(cycle_series) > 1 and cycle_series.mean() > 0 else np.nan

        wip_age_avg = np.nan
        oldest_open_age = np.nan
        aged_over_p85_count = 0
        if not wip.empty:
            wip['DataInProgress'] = pd.to_datetime(wip['DataInProgress'], errors='coerce')
            wip['WorkItemAge_Dias'] = (week_end - wip['DataInProgress']).dt.total_seconds() / 86400.0
            valid_age = pd.to_numeric(wip['WorkItemAge_Dias'], errors='coerce')
            if not valid_age.dropna().empty:
                wip_age_avg = float(valid_age.mean())
                oldest_open_age = float(valid_age.max())
                if pd.notna(cycle_p85) and cycle_p85 > 0:
                    aged_over_p85_count = int((valid_age > cycle_p85).sum())

        active_people = np.nan
        wip_per_person = np.nan
        wip_limit = np.nan
        if 'Responsavel' in df_source.columns:
            people_series = pd.concat([
                arrived.get('Responsavel', pd.Series(dtype='object')),
                done.get('Responsavel', pd.Series(dtype='object')),
                wip.get('Responsavel', pd.Series(dtype='object')),
            ], ignore_index=True)
            people_series = people_series.fillna('').astype(str).str.strip()
            people_series = people_series[people_series != '']
            if not people_series.empty:
                active_people = int(people_series.nunique())
                wip_limit = float(active_people) * float(wip_items_per_person_limit)
                wip_per_person = float(len(wip)) / float(active_people) if active_people > 0 else np.nan

        tp = int(len(done))
        inflow = int(len(arrived))
        flow_pressure = _safe_ratio(inflow, tp)
        blocked_rate = _safe_pct(wip['Bloqueado'].sum(), len(wip)) if 'Bloqueado' in wip.columns and len(wip) > 0 else 0.0

        rows.append({
            'Semana': week_start.date(),
            'Chegadas': inflow,
            'Throughput': tp,
            'WIP': int(len(wip)),
            'CycleTime_Medio': round(cycle_mean, 2) if pd.notna(cycle_mean) else np.nan,
            'CycleTime_P50': round(cycle_p50, 2) if pd.notna(cycle_p50) else np.nan,
            'CycleTime_P85': round(cycle_p85, 2) if pd.notna(cycle_p85) else np.nan,
            'CycleTime_CV': round(cycle_cv, 3) if pd.notna(cycle_cv) else np.nan,
            'WIP_Age_Medio': round(wip_age_avg, 2) if pd.notna(wip_age_avg) else np.nan,
            'OldestOpenAge': round(oldest_open_age, 2) if pd.notna(oldest_open_age) else np.nan,
            'AgedOverP85Count': aged_over_p85_count,
            'PessoasAtivas': int(active_people) if pd.notna(active_people) else np.nan,
            'WIP_Por_Pessoa': round(wip_per_person, 2) if pd.notna(wip_per_person) else np.nan,
            'WIP_Limite_Config': round(wip_limit, 2) if pd.notna(wip_limit) else np.nan,
            'BlockedRate': round(blocked_rate, 2),
            'FlowPressure': round(flow_pressure, 3) if pd.notna(flow_pressure) else np.nan,
        })

    weekly = pd.DataFrame(rows)
    if weekly.empty:
        empty_checklist = pd.DataFrame(columns=['Checklist', 'Status', 'Observado', 'Referência', 'Leitura'])
        empty_diag = pd.DataFrame(columns=['Semana', 'Padrão Observado', 'Diagnóstico Provável', 'Ação Recomendada', 'Severidade'])
        return empty_checklist, empty_diag, weekly

    throughput_avg = float(weekly['Throughput'].mean()) if weekly['Throughput'].notna().any() else np.nan
    wip_p85_ref = float(weekly['WIP'].quantile(0.85)) if weekly['WIP'].notna().any() else np.nan
    cycle_hist_series = time_metric_series(df_source[done_time_eligible_mask(df_source)].copy(), 'TempoExecucao_Dias', non_negative=True)
    if cycle_hist_series.empty:
        cycle_hist_series = time_metric_series(df_source[done_time_eligible_mask(df_source)].copy(), 'CycleTime_Dias', non_negative=True)
    cycle_hist_median = exact_empirical_percentile(cycle_hist_series, 0.50) if not cycle_hist_series.empty else np.nan

    weekly['ThroughputPrev'] = weekly['Throughput'].shift(1)
    weekly['ThroughputVarVsPrevPct'] = np.where(
        weekly['ThroughputPrev'].fillna(0) > 0,
        ((weekly['Throughput'] - weekly['ThroughputPrev']) / weekly['ThroughputPrev']) * 100.0,
        np.nan,
    )
    weekly['ThroughputStatus'] = 'Estável'
    if pd.notna(throughput_avg) and throughput_avg > 0:
        weekly.loc[weekly['Throughput'] < throughput_avg * 0.8, 'ThroughputStatus'] = 'Baixo'
        weekly.loc[weekly['Throughput'] > throughput_avg * 1.2, 'ThroughputStatus'] = 'Alto'

    weekly['CycleStatus'] = 'Estável'
    if pd.notna(cycle_hist_median) and cycle_hist_median > 0:
        weekly.loc[weekly['CycleTime_P50'] > cycle_hist_median * 1.3, 'CycleStatus'] = 'Alto'
        weekly.loc[weekly['CycleTime_P50'] < cycle_hist_median * 0.7, 'CycleStatus'] = 'Baixo'

    wip_median = float(weekly['WIP'].median()) if weekly['WIP'].notna().any() else np.nan
    weekly['WIPStatus'] = 'Estável'
    if pd.notna(wip_median) and wip_median > 0:
        weekly.loc[weekly['WIP'] > wip_median * 1.2, 'WIPStatus'] = 'Alto'
        weekly.loc[weekly['WIP'] < wip_median * 0.8, 'WIPStatus'] = 'Baixo'

    latest = weekly.iloc[-1]
    checklist_rows = []

    def add_check(item, passed, observed, reference, reading, critical=False):
        status = 'OK' if passed else ('Crítico' if critical else 'Atenção')
        checklist_rows.append({
            'Checklist': item,
            'Status': status,
            'Observado': observed,
            'Referência': reference,
            'Leitura': reading,
        })

    tp_ok = pd.notna(throughput_avg) and latest['Throughput'] >= throughput_avg * 0.8 and latest['Throughput'] <= throughput_avg * 1.2
    add_check(
        'Throughput dentro de ±20% da média histórica?',
        bool(tp_ok),
        f"{int(latest['Throughput'])} itens/semana",
        f"{throughput_avg:.1f} ±20%" if pd.notna(throughput_avg) else 'Sem histórico suficiente',
        'Vazão dentro da banda esperada.' if tp_ok else 'Vazão fora da banda histórica; revisar capacidade ou variabilidade.',
        critical=bool(pd.notna(throughput_avg) and latest['Throughput'] < throughput_avg * 0.8),
    )

    cycle_ok = pd.notna(cycle_hist_median) and pd.notna(latest['CycleTime_P50']) and latest['CycleTime_P50'] <= cycle_hist_median * 1.3
    add_check(
        'Cycle Time dentro de +30% da mediana histórica?',
        bool(cycle_ok),
        f"{latest['CycleTime_P50']:.1f}d" if pd.notna(latest['CycleTime_P50']) else 'Sem amostra',
        f"{cycle_hist_median:.1f}d +30%" if pd.notna(cycle_hist_median) else 'Sem histórico suficiente',
        'Tempo de fluxo segue estável.' if cycle_ok else 'Cycle Time acima da banda; há perda de previsibilidade.',
        critical=bool(pd.notna(cycle_hist_median) and pd.notna(latest['CycleTime_P50']) and latest['CycleTime_P50'] > cycle_hist_median * 1.5),
    )

    wip_rule_available = pd.notna(latest.get('PessoasAtivas')) and pd.notna(latest.get('WIP_Limite_Config')) and latest.get('PessoasAtivas', 0) > 0
    wip_ok = bool(wip_rule_available and latest['WIP'] <= latest['WIP_Limite_Config'])
    add_check(
        'WIP da semana abaixo do limite configurado por pessoa?',
        bool(wip_ok),
        (
            f"{int(latest['WIP'])} itens | "
            f"{latest['WIP_Por_Pessoa']:.2f} por pessoa"
            if wip_rule_available and pd.notna(latest.get('WIP_Por_Pessoa'))
            else f"{int(latest['WIP'])} itens"
        ),
        (
            f"{wip_items_per_person_limit:.1f} por pessoa x {int(latest['PessoasAtivas'])} pessoas = {latest['WIP_Limite_Config']:.1f}"
            if wip_rule_available else
            f"Fallback histórico P85 = {wip_p85_ref:.1f}" if pd.notna(wip_p85_ref) else 'Sem base suficiente'
        ),
        (
            'Carga em progresso compatível com a capacidade observada do time.'
            if wip_ok else
            'WIP por pessoa acima do limite configurado; reduzir frentes abertas e priorizar conclusão.'
        ),
        critical=bool(wip_rule_available and latest['WIP'] > latest['WIP_Limite_Config'] * 1.25),
    )

    tp_var_ok = pd.isna(latest['ThroughputVarVsPrevPct']) or abs(latest['ThroughputVarVsPrevPct']) <= 30.0
    add_check(
        'Variação de throughput <= 30% vs semana anterior?',
        bool(tp_var_ok),
        f"{latest['ThroughputVarVsPrevPct']:.1f}%" if pd.notna(latest['ThroughputVarVsPrevPct']) else 'Sem semana anterior',
        '<= 30%',
        'Cadência estável.' if tp_var_ok else 'Oscilação semanal alta; revisar entrada irregular ou itens muito heterogêneos.',
    )

    dispersion_ok = pd.notna(latest['CycleTime_CV']) and latest['CycleTime_CV'] < 0.30
    add_check(
        'Dispersão do Cycle Time controlada (CV < 0.30)?',
        bool(dispersion_ok),
        f"{latest['CycleTime_CV']:.3f}" if pd.notna(latest['CycleTime_CV']) else 'Sem amostra',
        'CV < 0.30',
        'Dispersão sob controle.' if dispersion_ok else 'Variabilidade alta; revisar tamanho de itens e qualidade de entrada.',
    )

    correlation_bad = latest['WIPStatus'] == 'Alto' and latest['CycleStatus'] == 'Alto'
    add_check(
        'Há correlação adversa entre WIP e Cycle Time?',
        not correlation_bad,
        f"WIP={latest['WIPStatus']} | Cycle={latest['CycleStatus']}",
        'Evitar WIP alto junto com Cycle alto',
        'Sem correlação adversa relevante.' if not correlation_bad else 'WIP e Cycle subiram juntos; fila interna provavelmente está crescendo.',
        critical=bool(correlation_bad),
    )

    aged_ok = int(latest['AgedOverP85Count']) == 0
    add_check(
        'Itens abertos acima do Cycle P85 estão sob controle?',
        aged_ok,
        f"{int(latest['AgedOverP85Count'])} itens",
        '0 itens acima do P85',
        'Nenhum item aberto ultrapassando a banda crítica.' if aged_ok else 'Há itens envelhecendo acima do P85; fazer swarming ou desbloqueio.',
        critical=bool(int(latest['AgedOverP85Count']) >= 3),
    )

    checklist_df = pd.DataFrame(checklist_rows)

    diagnosis_rows = []
    for _, row in weekly.iterrows():
        throughput_status = row.get('ThroughputStatus')
        cycle_status = row.get('CycleStatus')
        wip_status = row.get('WIPStatus')
        high_dispersion = pd.notna(row.get('CycleTime_CV')) and row.get('CycleTime_CV') >= 0.30
        many_aged = int(row.get('AgedOverP85Count') or 0)
        unstable_tp = pd.notna(row.get('ThroughputVarVsPrevPct')) and abs(float(row.get('ThroughputVarVsPrevPct'))) > 30.0
        wip_over_people_limit = pd.notna(row.get('WIP_Limite_Config')) and pd.notna(row.get('WIP')) and float(row.get('WIP')) > float(row.get('WIP_Limite_Config'))

        diagnosis = None
        if throughput_status == 'Baixo' and (wip_status == 'Alto' or wip_over_people_limit) and cycle_status == 'Alto':
            diagnosis = ('Throughput baixo | WIP alto | Cycle alto', 'Sistema sobrecarregado com filas internas.', 'Limitar WIP, priorizar conclusão, fazer swarming nos itens mais antigos e pausar novas entradas.', 'Crítico')
        elif throughput_status == 'Baixo' and wip_status == 'Estável' and cycle_status == 'Alto' and high_dispersion:
            diagnosis = ('Throughput baixo | WIP estável | Cycle alto | alta dispersão', 'Variabilidade elevada por itens complexos ou bloqueios pontuais.', 'Revisar Definition of Ready, quebrar itens grandes e mapear dependências recorrentes.', 'Atenção')
        elif throughput_status == 'Baixo' and wip_status == 'Baixo' and cycle_status == 'Estável':
            diagnosis = ('Throughput baixo | WIP baixo | Cycle estável', 'Redução de capacidade sem degradação do fluxo.', 'Ajustar expectativas e prazos sem acelerar artificialmente o sistema.', 'Atenção')
        elif throughput_status == 'Alto' and wip_status == 'Alto' and cycle_status == 'Alto':
            diagnosis = ('Throughput alto | WIP alto | Cycle alto', 'Aceleração acima do limite sustentável.', 'Congelar novas entradas, reforçar políticas pull e reduzir multitarefa.', 'Crítico')
        elif throughput_status == 'Alto' and wip_status == 'Estável' and cycle_status == 'Estável':
            diagnosis = ('Throughput alto | WIP estável | Cycle estável', 'Fluxo saudável e equilibrado.', 'Manter políticas atuais e usar os dados para planejamento confiável.', 'OK')
        elif throughput_status == 'Estável' and (wip_status == 'Alto' or wip_over_people_limit) and cycle_status == 'Alto':
            diagnosis = ('Throughput estável | WIP alto | Cycle alto', 'Saturação progressiva do sistema.', 'Atuar preventivamente limitando WIP e revisando pontos de espera.', 'Atenção')
        elif unstable_tp and wip_status == 'Estável' and high_dispersion:
            diagnosis = ('Throughput instável | WIP estável | Cycle instável', 'Processo inconsistente ou entrada irregular de trabalho.', 'Padronizar tamanho de itens, revisar critérios de entrada e estabilizar a cadência.', 'Atenção')
        elif cycle_status == 'Alto' and throughput_status == 'Estável' and wip_status == 'Estável':
            diagnosis = ('Cycle alto | Throughput estável | WIP estável', 'Aumento de complexidade interna ou retrabalho.', 'Investigar qualidade, revisar DoD e reduzir dependências.', 'Atenção')
        elif many_aged > 0 and many_aged <= 3:
            diagnosis = ('Work Item Age alto em poucos itens', 'Bloqueios silenciosos ou envelhecimento de itens críticos.', 'Fazer swarming direcionado e tornar bloqueios visíveis.', 'Atenção')
        elif throughput_status == 'Baixo' and wip_status == 'Baixo' and cycle_status == 'Baixo':
            diagnosis = ('WIP baixo | Throughput baixo | Cycle baixo', 'Subutilização de capacidade ou demanda reduzida.', 'Avaliar pipeline de demandas e redistribuir capacidade.', 'Atenção')

        if diagnosis:
            diagnosis_rows.append({
                'Semana': row['Semana'],
                'Padrão Observado': diagnosis[0],
                'Diagnóstico Provável': diagnosis[1],
                'Ação Recomendada': diagnosis[2],
                'Severidade': diagnosis[3],
            })

    diagnosis_df = pd.DataFrame(diagnosis_rows)
    if not diagnosis_df.empty:
        severity_rank = {'Crítico': 0, 'Atenção': 1, 'OK': 2}
        diagnosis_df['_rank'] = diagnosis_df['Severidade'].map(lambda value: severity_rank.get(value, 9))
        diagnosis_df = diagnosis_df.sort_values(['Semana', '_rank'], ascending=[False, True], ignore_index=True).drop(columns=['_rank'])

    return checklist_df, diagnosis_df, weekly


def build_expedite_governance_view(df_source, start_ts, end_ts):
    empty_kpis = {
        'arrivals_pct': np.nan,
        'throughput_pct': np.nan,
        'open_items': 0,
        'policy_status': 'Sem base',
        'open_age_avg': np.nan,
        'lead_p85': np.nan,
    }
    empty_table = pd.DataFrame(columns=['Classe de Serviço', 'Itens', 'Lead P50', 'Lead P85'])
    empty_alerts = pd.DataFrame(columns=['Indicador', 'Observado', 'Regra', 'Status', 'Leitura'])
    if df_source is None or df_source.empty:
        return empty_kpis, empty_table, empty_alerts

    scope = df_source.copy()
    if 'ClasseServico' not in scope.columns:
        scope['ClasseServico'] = ''
    scope['ClasseServicoNorm'] = scope['ClasseServico'].fillna('').astype(str).map(normalize_text)
    scope['IsExpedite'] = scope['ClasseServico'].apply(_is_expedite_service_class)

    done_period = scope[(scope['DataDone'] >= start_ts) & (scope['DataDone'] <= end_ts)].copy()
    done_period = done_period[done_time_eligible_mask(done_period)] if not done_period.empty else done_period
    arrivals_period = scope[(scope['DataInProgress'] >= start_ts) & (scope['DataInProgress'] <= end_ts)].copy()
    active_period = scope[
        (scope['DataInProgress'] <= end_ts) &
        ((scope['DataDone'] > end_ts) | pd.isna(scope['DataDone']))
    ].copy()

    expedite_target = _get_expedite_target_pct()
    expedite_critical = max(expedite_target, _get_expedite_critical_pct())

    expedite_arrivals = arrivals_period[arrivals_period['IsExpedite']].copy() if not arrivals_period.empty else pd.DataFrame(columns=scope.columns)
    expedite_done = done_period[done_period['IsExpedite']].copy() if not done_period.empty else pd.DataFrame(columns=scope.columns)
    expedite_open = active_period[active_period['IsExpedite']].copy() if not active_period.empty else pd.DataFrame(columns=scope.columns)

    arrivals_pct = _safe_pct(len(expedite_arrivals), len(arrivals_period)) if len(arrivals_period) > 0 else np.nan
    throughput_pct = _safe_pct(len(expedite_done), len(done_period)) if len(done_period) > 0 else np.nan
    expedite_lead = time_metric_series(expedite_done, 'LeadTime_Dias', non_negative=True)
    if expedite_lead.empty:
        expedite_lead = time_metric_series(expedite_done, 'LeadTime_Selected_Dias', non_negative=True)
    expedite_lead_p50 = exact_empirical_percentile(expedite_lead, 0.50) if not expedite_lead.empty else np.nan
    expedite_lead_p85 = exact_empirical_percentile(expedite_lead, 0.85) if not expedite_lead.empty else np.nan

    if not expedite_open.empty:
        expedite_open = expedite_open.copy()
        expedite_open['OpenAge'] = (end_ts - expedite_open['DataInProgress']).dt.total_seconds() / 86400.0
        open_age_avg = float(pd.to_numeric(expedite_open['OpenAge'], errors='coerce').mean())
    else:
        open_age_avg = np.nan

    if pd.isna(arrivals_pct):
        policy_status = 'Sem base'
    elif arrivals_pct <= expedite_target:
        policy_status = 'OK'
    elif arrivals_pct <= expedite_critical:
        policy_status = 'Atenção'
    else:
        policy_status = 'Crítico'

    class_summary = pd.DataFrame()
    if 'ClasseServico' in done_period.columns and not done_period.empty:
        base = done_period.copy()
        lead_vals = pd.to_numeric(base.get('LeadTime_Dias'), errors='coerce')
        if lead_vals.isna().all():
            lead_vals = pd.to_numeric(base.get('LeadTime_Selected_Dias'), errors='coerce')
        base['LeadMetric'] = lead_vals
        class_summary = (
            base.groupby('ClasseServico', dropna=False)['LeadMetric']
            .agg(Itens='count', Lead_P50=lambda s: exact_empirical_percentile(s.dropna(), 0.50) if not s.dropna().empty else np.nan, Lead_P85=lambda s: exact_empirical_percentile(s.dropna(), 0.85) if not s.dropna().empty else np.nan)
            .reset_index()
            .rename(columns={'ClasseServico': 'Classe de Serviço', 'Lead_P50': 'Lead P50', 'Lead_P85': 'Lead P85'})
            .sort_values('Itens', ascending=False, ignore_index=True)
        )
        for col in ['Lead P50', 'Lead P85']:
            class_summary[col] = pd.to_numeric(class_summary[col], errors='coerce').round(1)

    alerts = pd.DataFrame([
        {
            'Indicador': '% de entradas em Highest',
            'Observado': f"{arrivals_pct:.1f}%" if pd.notna(arrivals_pct) else 'Sem base',
            'Regra': f"OK <= {expedite_target:.1f}% | Crítico > {expedite_critical:.1f}%",
            'Status': policy_status,
            'Leitura': (
                'Uso de Highest dentro da política.'
                if policy_status == 'OK' else
                'Highest acima da meta; revisar critérios de fast track.'
                if policy_status == 'Atenção' else
                'Highest dominando a entrada; risco de canibalizar fluxo normal.'
                if policy_status == 'Crítico' else
                'Sem base suficiente para política de Highest.'
            ),
        },
        {
            'Indicador': '% de throughput em Highest',
            'Observado': f"{throughput_pct:.1f}%" if pd.notna(throughput_pct) else 'Sem base',
            'Regra': 'Monitorar desbalanceamento entre Highest e fluxo normal',
            'Status': 'OK' if pd.notna(throughput_pct) and throughput_pct <= expedite_target else ('Atenção' if pd.notna(throughput_pct) and throughput_pct <= expedite_critical else 'Crítico' if pd.notna(throughput_pct) else 'Sem base'),
            'Leitura': 'Usar como proxy de quanto da capacidade está sendo consumida por itens Highest.',
        },
        {
            'Indicador': 'Itens Highest em aberto',
            'Observado': f"{int(len(expedite_open))} itens",
            'Regra': 'Preferir fila Highest curta e envelhecimento baixo',
            'Status': 'OK' if len(expedite_open) <= 2 else 'Atenção' if len(expedite_open) <= 5 else 'Crítico',
            'Leitura': 'Itens Highest abertos demais indicam fast track virando estoque em vez de exceção.',
        },
    ])

    return {
        'arrivals_pct': arrivals_pct,
        'throughput_pct': throughput_pct,
        'open_items': int(len(expedite_open)),
        'policy_status': policy_status,
        'open_age_avg': round(open_age_avg, 1) if pd.notna(open_age_avg) else np.nan,
        'lead_p85': round(expedite_lead_p85, 1) if pd.notna(expedite_lead_p85) else np.nan,
    }, class_summary, alerts


def build_variability_alerts_view(df_source, start_ts, end_ts):
    warn = _get_variability_cv_warn()
    critical = _get_variability_cv_critical()
    empty_alerts = pd.DataFrame(columns=['Indicador', 'Observado', 'Regra', 'Status', 'Leitura', 'Ação'])
    empty_metrics = pd.DataFrame(columns=['Métrica', 'CV', 'Status'])
    if df_source is None or df_source.empty:
        return empty_alerts, empty_metrics

    done_period = df_source[(df_source['DataDone'] >= start_ts) & (df_source['DataDone'] <= end_ts)].copy()
    done_period = done_period[done_time_eligible_mask(done_period)] if not done_period.empty else done_period
    lead_series = time_metric_series(done_period, 'LeadTime_Dias', non_negative=True)
    if lead_series.empty:
        lead_series = time_metric_series(done_period, 'LeadTime_Selected_Dias', non_negative=True)
    cycle_series = time_metric_series(done_period, 'TempoExecucao_Dias', non_negative=True)
    if cycle_series.empty:
        cycle_series = time_metric_series(done_period, 'CycleTime_Dias', non_negative=True)

    weeks = pd.date_range(start=start_ts, end=end_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
    throughput_weekly = []
    for i in range(len(weeks) - 1):
        week_start = weeks[i]
        week_end = weeks[i + 1]
        throughput_weekly.append(int(((df_source['DataDone'] >= week_start) & (df_source['DataDone'] < week_end) & done_time_eligible_mask(df_source)).sum()))
    throughput_weekly = pd.Series(throughput_weekly, dtype='float64')

    def series_cv(series):
        s = pd.to_numeric(series, errors='coerce').dropna()
        if len(s) < 2 or s.mean() <= 0:
            return np.nan
        return float(s.std() / s.mean())

    lead_cv = series_cv(lead_series)
    cycle_cv = series_cv(cycle_series)
    throughput_cv = series_cv(throughput_weekly)

    metrics = pd.DataFrame([
        {'Métrica': 'Lead Time', 'CV': round(lead_cv, 3) if pd.notna(lead_cv) else np.nan, 'Status': _variability_status(lead_cv, warn, critical)},
        {'Métrica': 'Cycle Time', 'CV': round(cycle_cv, 3) if pd.notna(cycle_cv) else np.nan, 'Status': _variability_status(cycle_cv, warn, critical)},
        {'Métrica': 'Throughput Semanal', 'CV': round(throughput_cv, 3) if pd.notna(throughput_cv) else np.nan, 'Status': _variability_status(throughput_cv, warn, critical)},
    ])

    alerts = pd.DataFrame([
        {
            'Indicador': 'Dispersão de Lead Time',
            'Observado': f"CV={lead_cv:.3f}" if pd.notna(lead_cv) else 'Sem base',
            'Regra': f"OK < {warn:.2f} | Crítico >= {critical:.2f}",
            'Status': _variability_status(lead_cv, warn, critical),
            'Leitura': 'Dispersão do lead time afeta previsibilidade externa.',
            'Ação': 'Revisar variabilidade de entrada, dependências e mix de tipos de demanda.',
        },
        {
            'Indicador': 'Dispersão de Cycle Time',
            'Observado': f"CV={cycle_cv:.3f}" if pd.notna(cycle_cv) else 'Sem base',
            'Regra': f"OK < {warn:.2f} | Crítico >= {critical:.2f}",
            'Status': _variability_status(cycle_cv, warn, critical),
            'Leitura': 'Dispersão do cycle time evidencia inconsciência operacional dentro do fluxo.',
            'Ação': 'Quebrar itens grandes, reduzir retrabalho e reforçar Definition of Ready.',
        },
        {
            'Indicador': 'Dispersão de Throughput Semanal',
            'Observado': f"CV={throughput_cv:.3f}" if pd.notna(throughput_cv) else 'Sem base',
            'Regra': f"OK < {warn:.2f} | Crítico >= {critical:.2f}",
            'Status': _variability_status(throughput_cv, warn, critical),
            'Leitura': 'Oscilação alta de vazão dificulta compromisso e planejamento.',
            'Ação': 'Estabilizar a cadência, reduzir urgências e padronizar tamanho de trabalho.',
        },
    ])

    return alerts, metrics


def compute_portfolio_snapshot(df, updated_at_label):
    def group_count(df_source, by_cols, count_name):
        if df_source is None or df_source.empty:
            return pd.DataFrame(columns=[*by_cols, count_name])
        return (
            df_source.groupby(by_cols, dropna=False)
            .size()
            .reset_index(name=count_name)
            .sort_values(count_name, ascending=False, ignore_index=True)
        )

    def complexidade_feature(qtd_filhos):
        qtd = int(qtd_filhos or 0)
        if qtd == 0:
            return 'Sem filhos'
        if qtd <= 2:
            return 'Baixa'
        if qtd <= 5:
            return 'Média'
        return 'Alta'

    def complexidade_epico(qtd_itens_fluxo):
        qtd = int(qtd_itens_fluxo or 0)
        if qtd == 0:
            return 'Sem itens'
        if qtd <= 5:
            return 'Baixa'
        if qtd <= 15:
            return 'Média'
        return 'Alta'

    def status_contains(series_norm, terms):
        if series_norm.empty:
            return pd.Series(dtype=bool)
        mask = pd.Series(False, index=series_norm.index)
        for term in terms:
            mask = mask | series_norm.str.contains(term, regex=False, na=False)
        return mask

    if df is None or df.empty:
        return {
            'updated_at': updated_at_label,
            'metrics': {
                'epics_sem_features': 0,
                'features_sem_epico': 0,
                'features_sem_filhos': 0,
                'features_sem_mov_15': 0,
                'features_sem_mov_30': 0,
                'hist_tasks_sem_feature': 0,
                'pct_wip': 0.0,
                'pct_backlog_parado_15': 0.0,
                'pct_backlog_parado_30': 0.0,
                'pct_features_com_filhos': 0.0,
                'pct_epicos_com_itens_fluxo': 0.0,
                'pct_storytask_orfaos': 0.0,
                'lead_time_p50': None,
                'lead_time_p85': None,
                'lead_time_count': 0,
                'throughput_weekly_avg': 0.0,
                'throughput_monthly_avg': 0.0,
                'itens_com_tema_estrategico': 0,
                'pct_com_tema_estrategico': 0.0,
                'itens_com_risco': 0,
                'pct_com_risco': 0.0,
            },
            'groups': {
                'epicos_por_team_status': pd.DataFrame(),
                'features_por_team_status': pd.DataFrame(),
                'epicos_por_complexidade': pd.DataFrame(),
                'features_por_complexidade': pd.DataFrame(),
                'epicos_fluxo_etapas': pd.DataFrame(),
                'epicos_por_team_total': pd.DataFrame(),
                'features_por_team_total': pd.DataFrame(),
                'pendencias_q_por_time': pd.DataFrame(),
                'pendencias_breakdown': pd.DataFrame(),
                'pendencias_detalhe': pd.DataFrame(),
                'aging_us_20': pd.DataFrame(),
                'aging_features_40': pd.DataFrame(),
                'aging_us_comp_20': pd.DataFrame(),
                'aging_features_comp_40': pd.DataFrame(),
                'aging_buckets_por_team': pd.DataFrame(),
                'aging_por_tipo': pd.DataFrame(),
                'aging_por_projeto': pd.DataFrame(),
                'flow_health_summary': pd.DataFrame(),
                'flow_health_por_team': pd.DataFrame(),
                'portfolio_health_scorecard': pd.DataFrame(),
                'portfolio_health_dimension_summary': pd.DataFrame(),
                'flow_distribution_by_type': pd.DataFrame(),
                'flow_distribution_by_status': pd.DataFrame(),
                'flow_distribution_by_team': pd.DataFrame(),
                'stage_load_summary': pd.DataFrame(),
                'stage_load_detail': pd.DataFrame(),
                'stage_limit_alerts': pd.DataFrame(),
                'decision_queue_aging': pd.DataFrame(),
                'decision_queue_summary': pd.DataFrame(),
                'data_freshness_por_team_statuscat': pd.DataFrame(),
                'status_categoria_por_team': pd.DataFrame(),
                'status_ranking_por_team': pd.DataFrame(),
                'status_original_top': pd.DataFrame(),
                'workflow_conformance_por_team': pd.DataFrame(),
                'status_fora_workflow_top': pd.DataFrame(),
                'effort_features_por_team': pd.DataFrame(),
                'features_sem_effort_por_team': pd.DataFrame(),
                'effort_aging_summary': pd.DataFrame(),
                'effort_stale_summary': pd.DataFrame(),
                'heatmap_team_status': pd.DataFrame(),
                'quality_por_team': pd.DataFrame(),
                'estrutura_cobertura_por_team': pd.DataFrame(),
                'estrutura_cobertura_summary': pd.DataFrame(),
                'concentracao_team_share': pd.DataFrame(),
                'concentracao_epico_share': pd.DataFrame(),
                'concentracao_summary': pd.DataFrame(),
                'tipo_balanceamento': pd.DataFrame(),
                'items_base': pd.DataFrame(),
                'hist_tasks_sem_feature_por_team': pd.DataFrame(),
                'executive_tiles': pd.DataFrame(),
                'quality_summary': pd.DataFrame(),
                'top_epicos_volume': pd.DataFrame(),
                'top_epicos_aging': pd.DataFrame(),
                'epicos_detalhe': pd.DataFrame(),
                'features_detalhe': pd.DataFrame(),
                'portfolio_alerts_detail': pd.DataFrame(),
                'portfolio_alerts_indicator_summary': pd.DataFrame(),
                'portfolio_alerts_severity_summary': pd.DataFrame(),
                'portfolio_alerts_by_team': pd.DataFrame(),
                'portfolio_alerts_by_project': pd.DataFrame(),
                'portfolio_alert_kpis': pd.DataFrame(),
                'portfolio_extra_onepage_summary': pd.DataFrame(),
                'portfolio_technical_readiness_notes': pd.DataFrame(),
                'portfolio_technical_epic_summary': pd.DataFrame(),
                'portfolio_technical_items_catalog': pd.DataFrame(),
                'lead_time_por_tipo': pd.DataFrame(),
                'lead_time_por_team': pd.DataFrame(),
                'lead_time_distribution': pd.DataFrame(),
                'throughput_semanal': pd.DataFrame(),
                'throughput_mensal': pd.DataFrame(),
                'tema_distribuicao': pd.DataFrame(),
                'tema_team_heatmap': pd.DataFrame(),
                'tema_status_dist': pd.DataFrame(),
                'risk_distribuicao': pd.DataFrame(),
                'risk_por_tipo': pd.DataFrame(),
                'risk_por_team': pd.DataFrame(),
                'risk_aging': pd.DataFrame(),
                'due_date_performance': pd.DataFrame(),
            },
        }

    df = df.copy()
    if 'UpdatedAt' in df.columns:
        df['UpdatedAt'] = pd.to_datetime(df['UpdatedAt'], errors='coerce', utc=True)
    else:
        df['UpdatedAt'] = pd.NaT
    if 'StatusChangedAt' in df.columns:
        df['StatusChangedAt'] = pd.to_datetime(df['StatusChangedAt'], errors='coerce', utc=True)
    else:
        df['StatusChangedAt'] = pd.NaT
    if 'DueDate' in df.columns:
        df['DueDate'] = pd.to_datetime(df['DueDate'], errors='coerce', utc=True).dt.tz_localize(None)
    else:
        df['DueDate'] = pd.NaT
    if 'CreatedAt' in df.columns:
        df['CreatedAt'] = pd.to_datetime(df['CreatedAt'], errors='coerce', utc=True)
    else:
        df['CreatedAt'] = pd.NaT
    if 'ResolvedAt' in df.columns:
        df['ResolvedAt'] = pd.to_datetime(df['ResolvedAt'], errors='coerce', utc=True)
    else:
        df['ResolvedAt'] = pd.NaT
    for _col_f2 in ['StrategicTheme', 'Owner', 'Sponsor', 'Risk', 'TargetDate']:
        if _col_f2 not in df.columns:
            df[_col_f2] = ''
        else:
            df[_col_f2] = df[_col_f2].fillna('').astype(str).str.strip()
    if 'Team' not in df.columns:
        df['Team'] = ''
    for col in ['ParentTitle', 'HierarchyLinkSource', 'FeatureLinkID', 'FeatureLinkTipo', 'EpicLinkID', 'EpicLinkTipo', 'EpicLinkName', 'Componentes', 'ETIQUETA', 'Etiquetas', 'IssueLinkKeys', 'IssueLinkTypes', 'IssueLinkDetails']:
        if col not in df.columns:
            df[col] = ''
    df['ExtraOnePageLabels'] = df['ETIQUETA'].where(df['ETIQUETA'].astype(str).str.strip() != '', df['Etiquetas'])
    df['IsExtraOnePage'] = df['ExtraOnePageLabels'].apply(portfolio_has_extra_onepage_tag)

    df['Projeto'] = df['Projeto'].fillna('').astype(str)
    df['Team'] = df['Team'].fillna('').astype(str).str.strip()
    df['TeamOriginal'] = df['Team']
    if not df.empty:
        # Herda TEAM pela cadeia de parentesco (item -> feature -> épico) quando o card atual vier sem TEAM.
        team_map = {str(r['ID']): str(r['Team']).strip() for _, r in df[['ID', 'Team']].iterrows()}
        parent_map = {str(r['ID']): str(r['ParentID']).strip() for _, r in df[['ID', 'ParentID']].iterrows()}

        def resolve_team(issue_id):
            iid = str(issue_id or '').strip()
            seen = set()
            while iid and iid not in seen:
                seen.add(iid)
                t = str(team_map.get(iid, '')).strip()
                if t:
                    return t
                iid = str(parent_map.get(iid, '')).strip()
            return ''

        df['Team'] = df['ID'].apply(resolve_team)

    df['TeamDisplay'] = df['Team'].fillna('').astype(str).str.strip()
    df.loc[df['TeamDisplay'] == '', 'TeamDisplay'] = 'Sem TEAM'

    df['TipoNorm'] = df['Tipo'].map(normalize_text)
    df['ProjetoNorm'] = df['Projeto'].map(normalize_text)
    df['StatusNorm'] = df['Status'].map(normalize_text)
    df['ParentID'] = df['ParentID'].fillna('').astype(str)

    # O snapshot de portfólio trabalha apenas com itens não cancelados para que
    # decomposição, KPIs e alertas compartilhem o mesmo universo de análise.
    df['IsCancelled'] = df['Status'].apply(lambda value: portfolio_is_cancelled_item(value, ''))
    df = df[~df['IsCancelled']].copy()

    epic_types = {'epic', 'epico'}
    feature_types = {'feature', 'funcionalidade'}

    epics = df[df['TipoNorm'].isin(epic_types)].copy()
    features = df[df['TipoNorm'].isin(feature_types)].copy()

    epic_ids = set(epics['ID'])
    feature_ids = set(features['ID'])

    features['EpicID'] = features['ParentID'].where(features['ParentID'].isin(epic_ids), '')
    features_with_epic = features[features['EpicID'] != ''].copy()
    features_sem_epico = features[features['EpicID'] == ''].copy()

    children = df[df['ParentID'].isin(feature_ids)].copy()
    children['FeatureID'] = children['ParentID']
    feature_to_epic = features.set_index('ID')['EpicID'] if not features.empty else pd.Series(dtype='object')
    children['EpicID'] = children['FeatureID'].map(feature_to_epic).fillna('')
    children_under_epic = children[children['EpicID'].isin(epic_ids)].copy()

    child_counts = (
        children.groupby('ParentID').size().rename('QtdFilhos')
        if not children.empty
        else pd.Series(name='QtdFilhos', dtype='int64')
    )
    features = features.merge(child_counts, left_on='ID', right_index=True, how='left')
    features['QtdFilhos'] = features['QtdFilhos'].fillna(0).astype(int)
    features_sem_filhos = features[features['QtdFilhos'] == 0].copy()

    children['MovimentadoAt'] = children['StatusChangedAt']
    children.loc[children['MovimentadoAt'].isna(), 'MovimentadoAt'] = children.loc[children['MovimentadoAt'].isna(), 'UpdatedAt']
    last_move = (
        children.groupby('ParentID')['MovimentadoAt'].max().rename('UltimaMovimentacao')
        if not children.empty
        else pd.Series(name='UltimaMovimentacao', dtype='datetime64[ns, UTC]')
    )

    features = features.merge(last_move, left_on='ID', right_index=True, how='left')
    features_com_filhos = features[features['QtdFilhos'] > 0].copy()
    features['Complexidade'] = features['QtdFilhos'].apply(complexidade_feature)
    if 'EffortTShirtSize' in features.columns:
        features['EffortTShirtSize'] = features['EffortTShirtSize'].fillna('').astype(str).str.strip()
    else:
        features['EffortTShirtSize'] = ''
    features['EffortTShirtDisplay'] = features['EffortTShirtSize'].where(features['EffortTShirtSize'].ne(''), 'Sem estimativa')

    now_utc = pd.Timestamp.now(tz='UTC')
    cutoff_15 = now_utc - pd.Timedelta(days=15)
    cutoff_30 = now_utc - pd.Timedelta(days=30)

    features_sem_mov_15 = features_com_filhos[
        features_com_filhos['UltimaMovimentacao'].isna() | (features_com_filhos['UltimaMovimentacao'] < cutoff_15)
    ].copy()
    features_sem_mov_30 = features_com_filhos[
        features_com_filhos['UltimaMovimentacao'].isna() | (features_com_filhos['UltimaMovimentacao'] < cutoff_30)
    ].copy()

    # Aging e classes de fluxo para indicadores em tiles.
    done_terms = {'done', 'concluido', 'concluida', 'closed', 'resolved'}
    backlog_terms = {'backlog', 'to do', 'todo', 'triagem'}
    in_progress_terms = {
        'in progress',
        'in progess',
        'homolog',
        'staging',
        'ready',
        'progress',
        'desenvolvimento',
        'business review',
        '%',
    }

    df['UltimaMovimentacaoItem'] = df['StatusChangedAt']
    df.loc[df['UltimaMovimentacaoItem'].isna(), 'UltimaMovimentacaoItem'] = df.loc[df['UltimaMovimentacaoItem'].isna(), 'UpdatedAt']
    df['AgingDiasSemAlteracao'] = (now_utc - df['UltimaMovimentacaoItem']).dt.days

    is_done = status_contains(df['StatusNorm'], done_terms)
    is_backlog = status_contains(df['StatusNorm'], backlog_terms)
    is_in_progress = status_contains(df['StatusNorm'], in_progress_terms) & (~is_done)
    mapped_status_by_dict = is_done | is_backlog | is_in_progress
    # Fallback: se a taxonomia de status vier fora do dicionário, considera "aberto e não backlog" como em processo.
    if not bool(is_in_progress.any()):
        is_in_progress = (~is_done) & (~is_backlog)
    is_open = (~is_done)

    df['IsOpen'] = is_open
    df['IsInProgress'] = is_in_progress
    df['IsBacklog'] = is_backlog
    df['StatusMapeado'] = mapped_status_by_dict
    df['StatusCategoria'] = 'Não mapeado'
    df.loc[df['IsBacklog'], 'StatusCategoria'] = 'Backlog'
    df.loc[df['IsInProgress'], 'StatusCategoria'] = 'Em progresso'
    df.loc[is_done, 'StatusCategoria'] = 'Concluído'

    user_story_types = {'story', 'user story', 'historia', 'historia de usuario', 'us'}
    task_types = {'task', 'tarefa'}
    df['IsUS'] = df['TipoNorm'].isin(user_story_types)
    df['IsFeature'] = df['TipoNorm'].isin(feature_types)
    df['IsStoryTask'] = df['TipoNorm'].isin(user_story_types | task_types)
    df['HasParentFeature'] = df['ParentID'].isin(feature_ids)

    story_task_sem_feature = df[df['IsStoryTask'] & (~df['HasParentFeature'])].copy()
    hist_tasks_sem_feature_por_team = (
        group_count(story_task_sem_feature, ['TeamDisplay'], 'WorkItems')
        .rename(columns={'TeamDisplay': 'Team'})
    )

    # Aging detalhado por buckets (itens abertos).
    aging_bins = [-np.inf, 7, 15, 30, 60, np.inf]
    aging_labels = ['0-7', '8-15', '16-30', '31-60', '60+']
    aging_open = df[df['IsOpen']].copy()
    if not aging_open.empty:
        aging_vals = pd.to_numeric(aging_open['AgingDiasSemAlteracao'], errors='coerce')
        aging_open['AgingBucket'] = pd.cut(aging_vals, bins=aging_bins, labels=aging_labels, right=True)
        aging_open['AgingBucket'] = aging_open['AgingBucket'].astype('object').where(aging_open['AgingBucket'].notna(), 'Sem data')
        aging_buckets_por_team = (
            group_count(aging_open, ['TeamDisplay', 'AgingBucket'], 'WorkItems')
            .rename(columns={'TeamDisplay': 'Team'})
        )
    else:
        aging_buckets_por_team = pd.DataFrame(columns=['Team', 'AgingBucket', 'WorkItems'])

    # Aging por tipo e por projeto (somente itens abertos).
    def aging_summary(df_source, group_col, rename_col):
        if df_source is None or df_source.empty:
            return pd.DataFrame(columns=[rename_col, 'QtdItensAbertos', 'Aging Médio', 'Aging Mediano', 'Aging P90', 'Aging Máx'])
        base = df_source.copy()
        base['AgingDiasSemAlteracao'] = pd.to_numeric(base['AgingDiasSemAlteracao'], errors='coerce')
        agg = (
            base.groupby(group_col, dropna=False)['AgingDiasSemAlteracao']
            .agg(
                QtdItensAbertos='count',
                Aging_Medio='mean',
                Aging_Mediano='median',
                Aging_Max='max',
            )
            .reset_index()
        )
        p90 = (
            base.groupby(group_col, dropna=False)['AgingDiasSemAlteracao']
            .quantile(0.90)
            .reset_index(name='Aging_P90')
        )
        agg = agg.merge(p90, on=group_col, how='left')
        agg[group_col] = agg[group_col].fillna('').astype(str)
        agg.loc[agg[group_col].str.strip() == '', group_col] = f'Sem {rename_col.upper()}'
        agg['Aging_Medio'] = agg['Aging_Medio'].round(1)
        agg['Aging_Mediano'] = agg['Aging_Mediano'].round(1)
        agg['Aging_P90'] = agg['Aging_P90'].round(1)
        agg['Aging_Max'] = agg['Aging_Max'].round(1)
        agg = agg.sort_values(['Aging_Medio', 'QtdItensAbertos'], ascending=[False, False], ignore_index=True)
        return agg.rename(columns={
            group_col: rename_col,
            'Aging_Medio': 'Aging Médio',
            'Aging_Mediano': 'Aging Mediano',
            'Aging_P90': 'Aging P90',
            'Aging_Max': 'Aging Máx',
        })

    aging_por_tipo = aging_summary(aging_open, 'Tipo', 'Tipo')
    aging_por_projeto = aging_summary(aging_open, 'Projeto', 'Projeto')

    # Ranking de status por TEAM (categorias mapeadas + não mapeado).
    status_categoria_por_team = (
        group_count(df, ['TeamDisplay', 'StatusCategoria'], 'WorkItems')
        .rename(columns={'TeamDisplay': 'Team'})
    )
    if status_categoria_por_team is None or status_categoria_por_team.empty:
        status_ranking_por_team = pd.DataFrame(columns=[
            'Team', 'TotalItems', 'Backlog', 'Em progresso', 'Concluído', 'Não mapeado',
            '% Backlog', '% Em progresso', '% Concluído', '% Não mapeado'
        ])
    else:
        status_ranking_por_team = (
            status_categoria_por_team
            .pivot_table(index='Team', columns='StatusCategoria', values='WorkItems', aggfunc='sum', fill_value=0)
            .reset_index()
        )
        for col in ['Backlog', 'Em progresso', 'Concluído', 'Não mapeado']:
            if col not in status_ranking_por_team.columns:
                status_ranking_por_team[col] = 0
        status_ranking_por_team['TotalItems'] = (
            status_ranking_por_team[['Backlog', 'Em progresso', 'Concluído', 'Não mapeado']]
            .sum(axis=1)
            .astype(int)
        )
        denom = status_ranking_por_team['TotalItems'].replace(0, np.nan)
        status_ranking_por_team['% Backlog'] = (status_ranking_por_team['Backlog'] / denom * 100).fillna(0).round(1)
        status_ranking_por_team['% Em progresso'] = (status_ranking_por_team['Em progresso'] / denom * 100).fillna(0).round(1)
        status_ranking_por_team['% Concluído'] = (status_ranking_por_team['Concluído'] / denom * 100).fillna(0).round(1)
        status_ranking_por_team['% Não mapeado'] = (status_ranking_por_team['Não mapeado'] / denom * 100).fillna(0).round(1)
        status_ranking_por_team = status_ranking_por_team.sort_values(
            ['% Em progresso', 'TotalItems'], ascending=[False, False], ignore_index=True
        )
    heatmap_team_status = status_categoria_por_team.copy() if status_categoria_por_team is not None else pd.DataFrame(columns=['Team', 'StatusCategoria', 'WorkItems'])

    # Distribuição de Effort T-shirt por TEAM (Features).
    if features is not None and not features.empty:
        effort_features_por_team = (
            group_count(features, ['TeamDisplay', 'EffortTShirtDisplay'], 'QtdFeatures')
            .rename(columns={'TeamDisplay': 'Team'})
        )
        features_sem_effort_por_team = (
            group_count(features[features['EffortTShirtSize'].fillna('').astype(str).str.strip() == ''], ['TeamDisplay'], 'FeaturesSemEffort')
            .rename(columns={'TeamDisplay': 'Team'})
        )
        features_total_team = group_count(features, ['TeamDisplay'], 'FeaturesTotal').rename(columns={'TeamDisplay': 'Team'})
        features_sem_effort_por_team = features_total_team.merge(features_sem_effort_por_team, on='Team', how='left')
        features_sem_effort_por_team['FeaturesSemEffort'] = features_sem_effort_por_team['FeaturesSemEffort'].fillna(0).astype(int)
        features_sem_effort_por_team['% Sem Effort'] = (
            (features_sem_effort_por_team['FeaturesSemEffort'] / features_sem_effort_por_team['FeaturesTotal'].replace(0, np.nan)) * 100
        ).fillna(0).round(1)
        features_sem_effort_por_team['% Com Effort'] = (100 - features_sem_effort_por_team['% Sem Effort']).round(1)
        features_sem_effort_por_team = features_sem_effort_por_team.sort_values(
            ['% Sem Effort', 'FeaturesSemEffort'], ascending=[False, False], ignore_index=True
        )
        # Effort x aging (features)
        feat_age = features.copy()
        feat_age['DiasSemMovimentacao'] = pd.to_numeric(feat_age['UltimaMovimentacao'].map(lambda d: (now_utc - d).days if pd.notna(d) else np.nan), errors='coerce')
        effort_aging_summary = (
            feat_age.groupby('EffortTShirtDisplay', dropna=False)['DiasSemMovimentacao']
            .agg(Features='count', Aging_Medio='mean', Aging_Mediano='median', Aging_Max='max')
            .reset_index()
            .rename(columns={'EffortTShirtDisplay': 'Effort T-shirt'})
        )
        effort_p90 = feat_age.groupby('EffortTShirtDisplay', dropna=False)['DiasSemMovimentacao'].quantile(0.90).reset_index(name='Aging_P90')
        effort_aging_summary = effort_aging_summary.merge(effort_p90.rename(columns={'EffortTShirtDisplay': 'Effort T-shirt'}), on='Effort T-shirt', how='left')
        for c in ['Aging_Medio', 'Aging_Mediano', 'Aging_Max', 'Aging_P90']:
            effort_aging_summary[c] = pd.to_numeric(effort_aging_summary[c], errors='coerce').round(1)
        effort_aging_summary = effort_aging_summary.rename(columns={'Aging_Medio': 'Aging Médio', 'Aging_Mediano': 'Aging Mediano', 'Aging_Max': 'Aging Máx', 'Aging_P90': 'Aging P90'})
        effort_stale_summary = feat_age.groupby('EffortTShirtDisplay', dropna=False).size().reset_index(name='FeaturesTotal').rename(columns={'EffortTShirtDisplay': 'Effort T-shirt'})
        stale15 = feat_age[feat_age['DiasSemMovimentacao'] > 15].groupby('EffortTShirtDisplay', dropna=False).size().reset_index(name='SemMov15d').rename(columns={'EffortTShirtDisplay': 'Effort T-shirt'})
        stale30 = feat_age[feat_age['DiasSemMovimentacao'] > 30].groupby('EffortTShirtDisplay', dropna=False).size().reset_index(name='SemMov30d').rename(columns={'EffortTShirtDisplay': 'Effort T-shirt'})
        effort_stale_summary = effort_stale_summary.merge(stale15, on='Effort T-shirt', how='left').merge(stale30, on='Effort T-shirt', how='left')
        for c in ['SemMov15d', 'SemMov30d']:
            effort_stale_summary[c] = effort_stale_summary[c].fillna(0).astype(int)
        effort_stale_summary['% SemMov15d'] = (effort_stale_summary['SemMov15d'] / effort_stale_summary['FeaturesTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
        effort_stale_summary['% SemMov30d'] = (effort_stale_summary['SemMov30d'] / effort_stale_summary['FeaturesTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
        effort_stale_summary = effort_stale_summary.sort_values(['% SemMov30d', '% SemMov15d', 'FeaturesTotal'], ascending=[False, False, False], ignore_index=True)
    else:
        effort_features_por_team = pd.DataFrame(columns=['Team', 'EffortTShirtDisplay', 'QtdFeatures'])
        features_sem_effort_por_team = pd.DataFrame(columns=['Team', 'FeaturesTotal', 'FeaturesSemEffort', '% Sem Effort', '% Com Effort'])
        effort_aging_summary = pd.DataFrame(columns=['Effort T-shirt', 'Features', 'Aging Médio', 'Aging Mediano', 'Aging Máx', 'Aging P90'])
        effort_stale_summary = pd.DataFrame(columns=['Effort T-shirt', 'FeaturesTotal', 'SemMov15d', 'SemMov30d', '% SemMov15d', '% SemMov30d'])

    # Qualidade de cadastro por TEAM (TEAM efetivo para escopo; preenchimento avalia TEAM original).
    total_por_team = group_count(df, ['TeamDisplay'], 'TotalItems').rename(columns={'TeamDisplay': 'Team'})
    com_team_original_por_team = (
        group_count(df[df['TeamOriginal'].fillna('').astype(str).str.strip() != ''], ['TeamDisplay'], 'ComTeamOriginal')
        .rename(columns={'TeamDisplay': 'Team'})
    )
    status_nao_mapeado_por_team = (
        group_count(df[~df['StatusMapeado']], ['TeamDisplay'], 'StatusNaoMapeado')
        .rename(columns={'TeamDisplay': 'Team'})
    )
    if not features.empty:
        features_total_por_team = group_count(features, ['TeamDisplay'], 'FeaturesTotal').rename(columns={'TeamDisplay': 'Team'})
        features_com_epico_por_team = (
            group_count(features[features['EpicID'].fillna('').astype(str).str.strip() != ''], ['TeamDisplay'], 'FeaturesComEpic')
            .rename(columns={'TeamDisplay': 'Team'})
        )
        features_com_effort_por_team = (
            group_count(features[features['EffortTShirtSize'].fillna('').astype(str).str.strip() != ''], ['TeamDisplay'], 'FeaturesComEffort')
            .rename(columns={'TeamDisplay': 'Team'})
        )
    else:
        features_total_por_team = pd.DataFrame(columns=['Team', 'FeaturesTotal'])
        features_com_epico_por_team = pd.DataFrame(columns=['Team', 'FeaturesComEpic'])
        features_com_effort_por_team = pd.DataFrame(columns=['Team', 'FeaturesComEffort'])
    quality_por_team = total_por_team.copy() if total_por_team is not None else pd.DataFrame(columns=['Team', 'TotalItems'])
    for frame in [com_team_original_por_team, status_nao_mapeado_por_team, features_total_por_team, features_com_epico_por_team, features_com_effort_por_team]:
        quality_por_team = quality_por_team.merge(frame, on='Team', how='left')
    for col in ['ComTeamOriginal', 'StatusNaoMapeado', 'FeaturesTotal', 'FeaturesComEpic', 'FeaturesComEffort']:
        if col not in quality_por_team.columns:
            quality_por_team[col] = 0
        quality_por_team[col] = pd.to_numeric(quality_por_team[col], errors='coerce').fillna(0).astype(int)
    denom_items = quality_por_team['TotalItems'].replace(0, np.nan) if 'TotalItems' in quality_por_team.columns else pd.Series(dtype='float64')
    denom_features = quality_por_team['FeaturesTotal'].replace(0, np.nan) if 'FeaturesTotal' in quality_por_team.columns else pd.Series(dtype='float64')
    quality_por_team['% com TEAM'] = (quality_por_team['ComTeamOriginal'] / denom_items * 100).fillna(0).round(1)
    quality_por_team['% itens com status não mapeado'] = (quality_por_team['StatusNaoMapeado'] / denom_items * 100).fillna(0).round(1)
    quality_por_team['% features com épico'] = (quality_por_team['FeaturesComEpic'] / denom_features * 100).fillna(0).round(1)
    quality_por_team['% features com effort'] = (quality_por_team['FeaturesComEffort'] / denom_features * 100).fillna(0).round(1)
    quality_por_team = quality_por_team.sort_values(['TotalItems', 'Team'], ascending=[False, True], ignore_index=True)

    # Saúde de fluxo (snapshot): %WIP e backlog parado.
    backlog_open = df[df['IsBacklog'] & df['IsOpen']].copy()
    backlog_parado_15 = int((backlog_open['AgingDiasSemAlteracao'] > 15).sum()) if not backlog_open.empty else 0
    backlog_parado_30 = int((backlog_open['AgingDiasSemAlteracao'] > 30).sum()) if not backlog_open.empty else 0
    total_items_all = int(len(df))
    total_open_items = int(df['IsOpen'].sum())
    total_backlog_open = int(len(backlog_open))
    total_wip_items = int(df['IsInProgress'].sum())
    flow_health_summary = pd.DataFrame([
        {'Indicador': '% WIP no portfólio', 'Percentual': round((total_wip_items / total_items_all * 100), 1) if total_items_all else 0.0, 'Numerador': total_wip_items, 'Denominador': total_items_all},
        {'Indicador': '% backlog parado >15d', 'Percentual': round((backlog_parado_15 / total_backlog_open * 100), 1) if total_backlog_open else 0.0, 'Numerador': backlog_parado_15, 'Denominador': total_backlog_open},
        {'Indicador': '% backlog parado >30d', 'Percentual': round((backlog_parado_30 / total_backlog_open * 100), 1) if total_backlog_open else 0.0, 'Numerador': backlog_parado_30, 'Denominador': total_backlog_open},
        {'Indicador': '% itens abertos', 'Percentual': round((total_open_items / total_items_all * 100), 1) if total_items_all else 0.0, 'Numerador': total_open_items, 'Denominador': total_items_all},
    ])
    if not quality_por_team.empty:
        flow_health_por_team = quality_por_team[['Team', 'TotalItems']].copy()
        inprog_team = group_count(df[df['IsInProgress']], ['TeamDisplay'], 'WIP').rename(columns={'TeamDisplay': 'Team'})
        backlog_team = group_count(backlog_open, ['TeamDisplay'], 'BacklogAberto').rename(columns={'TeamDisplay': 'Team'})
        backlog15_team = group_count(backlog_open[backlog_open['AgingDiasSemAlteracao'] > 15], ['TeamDisplay'], 'BacklogParado15').rename(columns={'TeamDisplay': 'Team'})
        backlog30_team = group_count(backlog_open[backlog_open['AgingDiasSemAlteracao'] > 30], ['TeamDisplay'], 'BacklogParado30').rename(columns={'TeamDisplay': 'Team'})
        open_team = group_count(df[df['IsOpen']], ['TeamDisplay'], 'ItensAbertos').rename(columns={'TeamDisplay': 'Team'})
        for frame in [inprog_team, backlog_team, backlog15_team, backlog30_team, open_team]:
            flow_health_por_team = flow_health_por_team.merge(frame, on='Team', how='left')
        for col in ['WIP', 'BacklogAberto', 'BacklogParado15', 'BacklogParado30', 'ItensAbertos']:
            flow_health_por_team[col] = flow_health_por_team.get(col, 0)
            flow_health_por_team[col] = pd.to_numeric(flow_health_por_team[col], errors='coerce').fillna(0).astype(int)
        flow_health_por_team['% WIP'] = (flow_health_por_team['WIP'] / flow_health_por_team['TotalItems'].replace(0, np.nan) * 100).fillna(0).round(1)
        flow_health_por_team['% Backlog parado >15d'] = (flow_health_por_team['BacklogParado15'] / flow_health_por_team['BacklogAberto'].replace(0, np.nan) * 100).fillna(0).round(1)
        flow_health_por_team['% Backlog parado >30d'] = (flow_health_por_team['BacklogParado30'] / flow_health_por_team['BacklogAberto'].replace(0, np.nan) * 100).fillna(0).round(1)
        flow_health_por_team = flow_health_por_team.sort_values(['% Backlog parado >30d', '% WIP', 'TotalItems'], ascending=[False, False, False], ignore_index=True)
    else:
        flow_health_por_team = pd.DataFrame()

    # Flow distribution (snapshot atual): leitura de mix do trabalho aberto por tipo, status e team.
    flow_base = df[df['IsOpen']].copy()

    def build_distribution(df_source, group_col, display_col):
        if df_source is None or df_source.empty or group_col not in df_source.columns:
            return pd.DataFrame(columns=[display_col, 'WorkItems', '% Share'])
        out = group_count(df_source, [group_col], 'WorkItems').rename(columns={group_col: display_col})
        total_scope = float(out['WorkItems'].sum())
        out['% Share'] = (out['WorkItems'] / (total_scope if total_scope else np.nan) * 100).fillna(0).round(1)
        out = out.sort_values(['WorkItems', display_col], ascending=[False, True], ignore_index=True)
        return out

    flow_distribution_by_type = build_distribution(flow_base, 'Tipo', 'Tipo')
    flow_distribution_by_status = build_distribution(flow_base, 'Status', 'Status')
    flow_distribution_by_team = build_distribution(flow_base, 'TeamDisplay', 'Team')

    # Load/WIP atual por etapa com alertas de limite.
    stage_limit_cfg = parse_json_env('FLOW_PMO_PORTFOLIO_STAGE_LIMITS', {
        'backlog': 25,
        'em progresso': 15,
        'nao mapeado': 5,
    })
    if flow_base.empty:
        stage_load_detail = pd.DataFrame(columns=[
            'Status', 'StatusCategoria', 'TotalItems', 'WIPItems', 'BacklogItems',
            'Aging Médio', 'Aging P90', 'Limite', 'LoadRatio', 'Severidade'
        ])
        stage_limit_alerts = pd.DataFrame(columns=[
            'Status', 'StatusCategoria', 'TotalItems', 'Limite', 'LoadRatio', 'Severidade', 'Mensagem'
        ])
        stage_load_summary = pd.DataFrame(columns=['Indicador', 'Valor'])
    else:
        stage_load_detail = (
            flow_base.groupby(['Status', 'StatusCategoria'], dropna=False)
            .agg(
                TotalItems=('ID', 'count'),
                WIPItems=('IsInProgress', 'sum'),
                BacklogItems=('IsBacklog', 'sum'),
                Aging_Medio=('AgingDiasSemAlteracao', 'mean'),
                Aging_P90=('AgingDiasSemAlteracao', lambda s: s.quantile(0.90) if len(s) else np.nan),
            )
            .reset_index()
        )
        stage_load_detail['WIPItems'] = pd.to_numeric(stage_load_detail['WIPItems'], errors='coerce').fillna(0).astype(int)
        stage_load_detail['BacklogItems'] = pd.to_numeric(stage_load_detail['BacklogItems'], errors='coerce').fillna(0).astype(int)
        stage_load_detail['Aging_Medio'] = pd.to_numeric(stage_load_detail['Aging_Medio'], errors='coerce').round(1)
        stage_load_detail['Aging_P90'] = pd.to_numeric(stage_load_detail['Aging_P90'], errors='coerce').round(1)

        def resolve_stage_limit(row):
            raw_status = normalize_text(row.get('Status', ''))
            raw_category = normalize_text(row.get('StatusCategoria', ''))
            specific = stage_limit_cfg.get(raw_status)
            if specific is None:
                specific = stage_limit_cfg.get(raw_category)
            try:
                limit = int(float(specific))
            except Exception:
                limit = 0
            return max(0, limit)

        stage_load_detail['Limite'] = stage_load_detail.apply(resolve_stage_limit, axis=1)
        stage_load_detail['LoadRatio'] = np.where(
            stage_load_detail['Limite'] > 0,
            stage_load_detail['TotalItems'] / stage_load_detail['Limite'],
            np.nan,
        )

        def classify_stage_severity(row):
            ratio = pd.to_numeric(row.get('LoadRatio'), errors='coerce')
            if pd.isna(ratio):
                return 'Sem limite'
            if float(ratio) > 1.25:
                return 'Critico'
            if float(ratio) > 1.00:
                return 'Alerta'
            return 'OK'

        stage_load_detail['Severidade'] = stage_load_detail.apply(classify_stage_severity, axis=1)
        stage_load_detail = stage_load_detail.rename(columns={
            'Aging_Medio': 'Aging Médio',
            'Aging_P90': 'Aging P90',
        }).sort_values(
            ['Severidade', 'LoadRatio', 'TotalItems', 'Status'],
            ascending=[True, False, False, True],
            ignore_index=True,
        )
        stage_limit_alerts = stage_load_detail[stage_load_detail['Severidade'].isin(['Critico', 'Alerta'])].copy()
        if not stage_limit_alerts.empty:
            stage_limit_alerts['Mensagem'] = stage_limit_alerts.apply(
                lambda row: (
                    f"Etapa com {int(row.get('TotalItems', 0) or 0)} itens para limite {int(row.get('Limite', 0) or 0)} "
                    f"({float(row.get('LoadRatio', 0.0) or 0.0):.2f}x)."
                ),
                axis=1,
            )
            stage_limit_alerts = stage_limit_alerts[[
                'Status', 'StatusCategoria', 'TotalItems', 'Limite', 'LoadRatio', 'Severidade', 'Mensagem'
            ]].copy()
        stage_load_summary = pd.DataFrame([
            {'Indicador': 'Itens abertos no fluxo', 'Valor': int(len(flow_base))},
            {'Indicador': 'Etapas abertas', 'Valor': int(stage_load_detail['Status'].nunique())},
            {'Indicador': 'Etapas acima do limite', 'Valor': int(len(stage_limit_alerts))},
            {'Indicador': 'Maior carga relativa', 'Valor': round(float(stage_load_detail['LoadRatio'].max()), 2) if stage_load_detail['LoadRatio'].notna().any() else 0.0},
        ])

    # Fila de decisão por aging (status típicos de entrada/decisão inicial).
    decision_terms = {'triagem', 'backlog', 'business review', 'ready for development'}
    is_decision_queue = status_contains(df['StatusNorm'], decision_terms) & df['IsOpen']
    decision_queue = df[is_decision_queue].copy()
    if not decision_queue.empty:
        dq = decision_queue.copy()
        dq['AgingBucketDecision'] = '0-7'
        dq.loc[dq['AgingDiasSemAlteracao'] > 7, 'AgingBucketDecision'] = '8-15'
        dq.loc[dq['AgingDiasSemAlteracao'] > 15, 'AgingBucketDecision'] = '16-30'
        dq.loc[dq['AgingDiasSemAlteracao'] > 30, 'AgingBucketDecision'] = '31-60'
        dq.loc[dq['AgingDiasSemAlteracao'] > 60, 'AgingBucketDecision'] = '60+'
        decision_queue_aging = group_count(dq, ['TeamDisplay', 'Status', 'AgingBucketDecision'], 'WorkItems').rename(columns={'TeamDisplay': 'Team'})
        decision_queue_summary = group_count(dq, ['Status'], 'WorkItems')
        decision_queue_summary['Aging Médio'] = decision_queue_summary['Status'].map(
            dq.groupby('Status')['AgingDiasSemAlteracao'].mean().round(1)
        )
    else:
        decision_queue_aging = pd.DataFrame(columns=['Team', 'Status', 'AgingBucketDecision', 'WorkItems'])
        decision_queue_summary = pd.DataFrame(columns=['Status', 'WorkItems', 'Aging Médio'])

    # Status original (top N) e conformidade com workflow padrão.
    status_original_top = group_count(df, ['Status'], 'WorkItems').head(20) if not df.empty else pd.DataFrame(columns=['Status', 'WorkItems'])
    official_status_terms = {
        'triagem', 'backlog', 'to do', 'todo', 'business review', 'ready for development',
        'in progress', 'in progess', 'ready', 'homolog', 'staging', 'desenvolvimento',
        'concluido', 'concluida', 'done', 'closed', 'resolved', 'cancel'
    }
    status_official_mask = status_contains(df['StatusNorm'], official_status_terms)
    df['StatusForaWorkflow'] = ~status_official_mask
    workflow_conformance_por_team = quality_por_team[['Team', 'TotalItems']].copy() if not quality_por_team.empty else pd.DataFrame(columns=['Team', 'TotalItems'])
    if not workflow_conformance_por_team.empty:
        fora_team = group_count(df[df['StatusForaWorkflow']], ['TeamDisplay'], 'StatusForaWorkflow').rename(columns={'TeamDisplay': 'Team'})
        workflow_conformance_por_team = workflow_conformance_por_team.merge(fora_team, on='Team', how='left')
        workflow_conformance_por_team['StatusForaWorkflow'] = workflow_conformance_por_team['StatusForaWorkflow'].fillna(0).astype(int)
        workflow_conformance_por_team['% Fora workflow'] = (
            workflow_conformance_por_team['StatusForaWorkflow'] / workflow_conformance_por_team['TotalItems'].replace(0, np.nan) * 100
        ).fillna(0).round(1)
        workflow_conformance_por_team = workflow_conformance_por_team.sort_values(['% Fora workflow', 'StatusForaWorkflow'], ascending=[False, False], ignore_index=True)
    status_fora_workflow_top = group_count(df[df['StatusForaWorkflow']], ['Status'], 'WorkItems').head(20) if not df.empty else pd.DataFrame(columns=['Status', 'WorkItems'])

    # Data freshness por etapa (abertos): % >15d e >30d por TEAM x StatusCategoria.
    if not aging_open.empty:
        freshness_base = aging_open[['TeamDisplay', 'StatusCategoria', 'AgingDiasSemAlteracao']].copy()
        freshness_base['GT15'] = (pd.to_numeric(freshness_base['AgingDiasSemAlteracao'], errors='coerce') > 15).astype(int)
        freshness_base['GT30'] = (pd.to_numeric(freshness_base['AgingDiasSemAlteracao'], errors='coerce') > 30).astype(int)
        data_freshness_por_team_statuscat = (
            freshness_base.groupby(['TeamDisplay', 'StatusCategoria'], dropna=False)
            .agg(WorkItems=('AgingDiasSemAlteracao', 'count'), GT15=('GT15', 'sum'), GT30=('GT30', 'sum'))
            .reset_index()
            .rename(columns={'TeamDisplay': 'Team'})
        )
        data_freshness_por_team_statuscat['% >15d'] = (data_freshness_por_team_statuscat['GT15'] / data_freshness_por_team_statuscat['WorkItems'].replace(0, np.nan) * 100).fillna(0).round(1)
        data_freshness_por_team_statuscat['% >30d'] = (data_freshness_por_team_statuscat['GT30'] / data_freshness_por_team_statuscat['WorkItems'].replace(0, np.nan) * 100).fillna(0).round(1)
    else:
        data_freshness_por_team_statuscat = pd.DataFrame(columns=['Team', 'StatusCategoria', 'WorkItems', 'GT15', 'GT30', '% >15d', '% >30d'])

    # Buckets de pendências por aging em aberto, por TEAM/projeto agrupado.
    pendencias = df[df['IsOpen']].copy()
    pendencias['Quadrante'] = PORTFOLIO_PENDING_BUCKET_1
    pendencias.loc[pendencias['AgingDiasSemAlteracao'] > 15, 'Quadrante'] = PORTFOLIO_PENDING_BUCKET_2
    pendencias.loc[pendencias['AgingDiasSemAlteracao'] > 30, 'Quadrante'] = PORTFOLIO_PENDING_BUCKET_3
    pendencias_q_por_time = (
        group_count(pendencias, ['Quadrante', 'TeamDisplay'], 'WorkItems')
        .rename(columns={'TeamDisplay': 'Team'})
    )
    pendencias_breakdown = (
        group_count(pendencias, ['Quadrante', 'Tipo', 'StatusCategoria'], 'WorkItems')
        if not pendencias.empty else
        pd.DataFrame(columns=['Quadrante', 'Tipo', 'StatusCategoria', 'WorkItems'])
    )
    pendencias_detalhe_cols = [
        'Quadrante', 'TeamDisplay', 'Projeto', 'Tipo', 'ID', 'Titulo', 'Status',
        'StatusCategoria', 'AgingDiasSemAlteracao', 'ParentID', 'Link'
    ]
    if not pendencias.empty:
        pendencias_detalhe = (
            pendencias[pendencias_detalhe_cols]
            .rename(columns={
                'TeamDisplay': 'Team',
                'ID': 'ItemID',
                'AgingDiasSemAlteracao': 'DiasSemAlteracao',
                'ParentID': 'ParentID',
            })
            .sort_values(
                ['Quadrante', 'DiasSemAlteracao', 'Team', 'Tipo', 'ItemID'],
                ascending=[True, False, True, True, True],
                ignore_index=True,
            )
        )
    else:
        pendencias_detalhe = pd.DataFrame(columns=[
            'Quadrante', 'Team', 'Projeto', 'Tipo', 'ItemID', 'Titulo', 'Status',
            'StatusCategoria', 'DiasSemAlteracao', 'ParentID', 'Link'
        ])

    # Aging WIP - quatro indicadores no padrão dos exemplos.
    has_us_items = bool(df['IsUS'].any())
    if has_us_items:
        us_in_progress = df[df['IsUS'] & df['IsInProgress']].copy()
        us_compromissadas = df[df['IsUS'] & df['IsInProgress'] & (~df['IsBacklog'])].copy()
    else:
        # No snapshot de portfólio BT/NS costuma não haver US; usa Épicos como proxy operacional.
        us_in_progress = df[df['TipoNorm'].isin(epic_types) & df['IsInProgress']].copy()
        us_compromissadas = df[df['TipoNorm'].isin(epic_types) & df['IsInProgress'] & (~df['IsBacklog'])].copy()
    features_in_progress = df[df['IsFeature'] & df['IsInProgress']].copy()
    features_compromissadas = features_with_epic[features_with_epic['Status'].notna()].copy()
    if not features_compromissadas.empty:
        age_map = df.set_index('ID')['AgingDiasSemAlteracao']
        in_progress_map = df.set_index('ID')['IsInProgress']
        features_compromissadas['AgingDiasSemAlteracao'] = features_compromissadas['ID'].map(age_map)
        features_compromissadas['IsInProgress'] = features_compromissadas['ID'].map(in_progress_map)
        features_compromissadas = features_compromissadas[features_compromissadas['IsInProgress'] == True].copy()

    aging_us_20 = group_count(us_in_progress[us_in_progress['AgingDiasSemAlteracao'] > 20], ['TeamDisplay'], 'WorkItems').rename(columns={'TeamDisplay': 'Team'})
    aging_features_40 = group_count(features_in_progress[features_in_progress['AgingDiasSemAlteracao'] > 40], ['TeamDisplay'], 'WorkItems').rename(columns={'TeamDisplay': 'Team'})
    aging_us_comp_20 = group_count(us_compromissadas[us_compromissadas['AgingDiasSemAlteracao'] > 20], ['TeamDisplay'], 'WorkItems').rename(columns={'TeamDisplay': 'Team'})
    aging_features_comp_40 = (
        group_count(features_compromissadas[features_compromissadas['AgingDiasSemAlteracao'] > 40], ['TeamDisplay'], 'WorkItems').rename(columns={'TeamDisplay': 'Team'})
        if not features_compromissadas.empty
        else pd.DataFrame(columns=['Team', 'WorkItems'])
    )

    epic_feature_counts = (
        features_with_epic.groupby('EpicID').size().rename('QtdFeatures')
        if not features_with_epic.empty
        else pd.Series(name='QtdFeatures', dtype='int64')
    )
    epic_child_counts = (
        children_under_epic.groupby('EpicID').size().rename('QtdItensFilhos')
        if not children_under_epic.empty
        else pd.Series(name='QtdItensFilhos', dtype='int64')
    )
    epics = epics.merge(epic_feature_counts, left_on='ID', right_index=True, how='left')
    epics = epics.merge(epic_child_counts, left_on='ID', right_index=True, how='left')
    epics['QtdFeatures'] = epics['QtdFeatures'].fillna(0).astype(int)
    epics['QtdItensFilhos'] = epics['QtdItensFilhos'].fillna(0).astype(int)
    epics['QtdItensFluxo'] = epics['QtdFeatures'] + epics['QtdItensFilhos']
    epics['Complexidade'] = epics['QtdItensFluxo'].apply(complexidade_epico)
    age_map_all = df.set_index('ID')['AgingDiasSemAlteracao'] if not df.empty else pd.Series(dtype='float64')
    is_open_map = df.set_index('ID')['IsOpen'] if not df.empty else pd.Series(dtype='bool')
    epics['AgingDiasSemAlteracao'] = epics['ID'].map(age_map_all)
    epics['IsOpen'] = epics['ID'].map(is_open_map).fillna(False)
    epics_sem_features = epics[epics['QtdFeatures'] == 0].copy()

    epicos_por_team_status = group_count(epics, ['TeamDisplay', 'Status'], 'QtdEpicos').rename(columns={'TeamDisplay': 'Team'})
    features_por_team_status = group_count(features, ['TeamDisplay', 'Status'], 'QtdFeatures').rename(columns={'TeamDisplay': 'Team'})
    epicos_por_complexidade = group_count(epics, ['TeamDisplay', 'Complexidade'], 'QtdEpicos').rename(columns={'TeamDisplay': 'Team'})
    features_por_complexidade = group_count(features, ['TeamDisplay', 'Complexidade'], 'QtdFeatures').rename(columns={'TeamDisplay': 'Team'})
    epicos_por_team_total = group_count(epics, ['TeamDisplay'], 'QtdEpicos').rename(columns={'TeamDisplay': 'Team'})
    features_por_team_total = group_count(features, ['TeamDisplay'], 'QtdFeatures').rename(columns={'TeamDisplay': 'Team'})

    # Cobertura estrutural (decomposição) por TEAM e resumo global.
    # "Sem feature tática" usa vínculo direto com feature (ParentID em feature do board tático).
    epics_com_itens_fluxo = epics[epics['QtdItensFluxo'] > 0].copy() if not epics.empty else pd.DataFrame(columns=epics.columns)
    features_com_filhos = features[features['QtdFilhos'] > 0].copy() if not features.empty else pd.DataFrame(columns=features.columns)
    storytask_total = df[df['IsStoryTask']].copy()
    storytask_sem_feature_tatico_metric = {
        'Indicador': '% histórias/tasks (melhorias) sem feature tática',
        'Percentual': round((len(story_task_sem_feature) / len(storytask_total) * 100), 1) if len(storytask_total) else 0.0,
        'Numerador': int(len(story_task_sem_feature)),
        'Denominador': int(len(storytask_total)),
    }
    estrutura_cobertura_por_team = pd.DataFrame(columns=['Team'])
    base_teams = sorted(set(df['TeamDisplay'].dropna().astype(str)))
    if base_teams:
        estrutura_cobertura_por_team = pd.DataFrame({'Team': base_teams})
        team_frames = [
            group_count(epics, ['TeamDisplay'], 'EpicosTotal').rename(columns={'TeamDisplay': 'Team'}),
            group_count(epics_com_itens_fluxo, ['TeamDisplay'], 'EpicosComItensFluxo').rename(columns={'TeamDisplay': 'Team'}),
            group_count(features, ['TeamDisplay'], 'FeaturesTotal').rename(columns={'TeamDisplay': 'Team'}),
            group_count(features_com_filhos, ['TeamDisplay'], 'FeaturesComFilhos').rename(columns={'TeamDisplay': 'Team'}),
            group_count(storytask_total, ['TeamDisplay'], 'StoryTaskTotal').rename(columns={'TeamDisplay': 'Team'}),
            group_count(story_task_sem_feature, ['TeamDisplay'], 'StoryTaskSemFeatureTatico').rename(columns={'TeamDisplay': 'Team'}),
            group_count(story_task_sem_feature, ['TeamDisplay'], 'StoryTaskOrfaos').rename(columns={'TeamDisplay': 'Team'}),
        ]
        for frame in team_frames:
            estrutura_cobertura_por_team = estrutura_cobertura_por_team.merge(frame, on='Team', how='left')
        for col in ['EpicosTotal', 'EpicosComItensFluxo', 'FeaturesTotal', 'FeaturesComFilhos', 'StoryTaskTotal', 'StoryTaskSemFeatureTatico', 'StoryTaskOrfaos']:
            col_series = estrutura_cobertura_por_team[col] if col in estrutura_cobertura_por_team.columns else pd.Series(0, index=estrutura_cobertura_por_team.index)
            estrutura_cobertura_por_team[col] = pd.to_numeric(col_series, errors='coerce').fillna(0).astype(int)
        estrutura_cobertura_por_team['% Épicos com itens de fluxo'] = (estrutura_cobertura_por_team['EpicosComItensFluxo'] / estrutura_cobertura_por_team['EpicosTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
        estrutura_cobertura_por_team['% Features com filhos'] = (estrutura_cobertura_por_team['FeaturesComFilhos'] / estrutura_cobertura_por_team['FeaturesTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
        estrutura_cobertura_por_team['% Story/Task sem feature tática'] = (estrutura_cobertura_por_team['StoryTaskSemFeatureTatico'] / estrutura_cobertura_por_team['StoryTaskTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
        estrutura_cobertura_por_team['% Story/Task órfãos'] = (estrutura_cobertura_por_team['StoryTaskOrfaos'] / estrutura_cobertura_por_team['StoryTaskTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
        estrutura_cobertura_por_team = estrutura_cobertura_por_team.sort_values(['% Story/Task órfãos', '% Épicos com itens de fluxo'], ascending=[False, True], ignore_index=True)
    storytask_orfaos_metric = {
        'Indicador': '% histórias/tasks órfãos',
        'Percentual': round((len(story_task_sem_feature) / len(storytask_total) * 100), 1) if len(storytask_total) else 0.0,
        'Numerador': int(len(story_task_sem_feature)),
        'Denominador': int(len(storytask_total)),
    }
    if int(storytask_orfaos_metric['Denominador']) == 0:
        downstream_storytask_metric = _compute_storytask_orphan_from_downstream()
        if downstream_storytask_metric:
            storytask_orfaos_metric.update(downstream_storytask_metric)

    estrutura_cobertura_summary = pd.DataFrame([
        {'Indicador': '% épicos com itens de fluxo', 'Percentual': round((len(epics_com_itens_fluxo) / len(epics) * 100), 1) if len(epics) else 0.0, 'Numerador': int(len(epics_com_itens_fluxo)), 'Denominador': int(len(epics))},
        {'Indicador': '% features com filhos', 'Percentual': round((len(features_com_filhos) / len(features) * 100), 1) if len(features) else 0.0, 'Numerador': int(len(features_com_filhos)), 'Denominador': int(len(features))},
        storytask_sem_feature_tatico_metric,
        storytask_orfaos_metric,
    ])

    epic_flow_items = pd.DataFrame(columns=['EpicID', 'Status'])
    if not features_with_epic.empty:
        epic_flow_items = pd.concat([
            epic_flow_items,
            features_with_epic[['EpicID', 'Status']].copy(),
        ], ignore_index=True)
    if not children_under_epic.empty:
        epic_flow_items = pd.concat([
            epic_flow_items,
            children_under_epic[['EpicID', 'Status']].copy(),
        ], ignore_index=True)

    if epic_flow_items.empty:
        epicos_fluxo_etapas = pd.DataFrame(columns=['EpicID', 'Titulo', 'Team', 'Complexidade', 'TotalItens'])
    else:
        epics_info = epics[['ID', 'Titulo', 'TeamDisplay', 'Complexidade']].copy()
        epics_info.rename(columns={'ID': 'EpicID'}, inplace=True)
        epics_info.rename(columns={'TeamDisplay': 'Team'}, inplace=True)
        epicos_fluxo_etapas = (
            epic_flow_items
            .pivot_table(index='EpicID', columns='Status', values='Status', aggfunc='count', fill_value=0)
            .reset_index()
        )
        epicos_fluxo_etapas = epics_info.merge(epicos_fluxo_etapas, on='EpicID', how='left').fillna(0)
        stage_cols = [c for c in epicos_fluxo_etapas.columns if c not in {'EpicID', 'Titulo', 'Team', 'Complexidade'}]
        if stage_cols:
            epicos_fluxo_etapas['TotalItens'] = epicos_fluxo_etapas[stage_cols].sum(axis=1).astype(int)
        else:
            epicos_fluxo_etapas['TotalItens'] = 0
        epicos_fluxo_etapas = epicos_fluxo_etapas.sort_values('TotalItens', ascending=False, ignore_index=True)

    # Visões detalhadas separadas (épicos x features) para reduzir mistura de contexto.
    status_categoria_by_id = df.set_index('ID')['StatusCategoria'] if ('ID' in df.columns and 'StatusCategoria' in df.columns) else pd.Series(dtype='object')
    if 'StatusCategoria' not in epics.columns:
        epics['StatusCategoria'] = epics['ID'].map(status_categoria_by_id).fillna('Não mapeado')
    if 'StatusCategoria' not in features.columns:
        features['StatusCategoria'] = features['ID'].map(status_categoria_by_id).fillna('Não mapeado')

    epic_title_map = epics.set_index('ID')['Titulo'] if not epics.empty else pd.Series(dtype='object')
    features['EpicTitulo'] = features['EpicID'].map(epic_title_map).fillna('')
    features['DiasSemMovimentacao'] = (
        (now_utc - features['UltimaMovimentacao']).dt.days
        if 'UltimaMovimentacao' in features.columns else np.nan
    )
    epicos_detalhe = (
        epics[['TeamDisplay', 'ID', 'Titulo', 'Status', 'StatusCategoria', 'Complexidade', 'QtdFeatures', 'QtdItensFluxo', 'AgingDiasSemAlteracao', 'Link']]
        .rename(columns={'TeamDisplay': 'Team', 'ID': 'EpicID', 'AgingDiasSemAlteracao': 'AgingDiasSemAlteracao'})
        .sort_values(['Team', 'QtdItensFluxo', 'QtdFeatures'], ascending=[True, False, False], ignore_index=True)
    )
    features_detalhe = (
        features[['TeamDisplay', 'ID', 'Titulo', 'Status', 'StatusCategoria', 'EffortTShirtDisplay', 'Complexidade', 'EpicID', 'EpicTitulo', 'QtdFilhos', 'DiasSemMovimentacao', 'Link']]
        .rename(columns={'TeamDisplay': 'Team', 'ID': 'FeatureID', 'EffortTShirtDisplay': 'Effort T-shirt'})
        .sort_values(['Team', 'QtdFilhos', 'DiasSemMovimentacao'], ascending=[True, False, False], ignore_index=True)
    )

    today = pd.Timestamp.now().normalize()
    alert_columns = [
        'Severidade', 'TipoAlerta', 'TipoItem', 'Projeto', 'Team', 'ItemID', 'Titulo',
        'Status', 'DiasSemMovimentacao', 'DueDate', 'DiasParaVencimento', 'MotivoAlerta', 'Link'
    ]
    severity_order = {'Critico': 0, 'Alerta': 1, 'Monitorar': 2}

    def _empty_alert_df():
        return pd.DataFrame(columns=alert_columns)

    def _due_days(df_source):
        if df_source is None or df_source.empty or 'DueDate' not in df_source.columns:
            return pd.Series(np.nan, index=getattr(df_source, 'index', []), dtype='float64')
        due_dt = pd.to_datetime(df_source['DueDate'], errors='coerce')
        return (due_dt.dt.normalize() - today).dt.days

    def _staleness_severity(days_value):
        days_num = pd.to_numeric(days_value, errors='coerce')
        if pd.isna(days_num):
            return 'Monitorar'
        if float(days_num) > 30:
            return 'Critico'
        if float(days_num) > 20:
            return 'Alerta'
        return 'Monitorar'

    def _build_alert_frame(df_source, item_id_col, item_type_col, alert_type, reason_builder, severity_builder):
        if df_source is None or df_source.empty:
            return _empty_alert_df()
        local = df_source.copy()
        local['ItemID'] = local[item_id_col].astype(str).str.strip()
        if item_type_col in local.columns:
            local['TipoItem'] = local[item_type_col].fillna('').astype(str).str.strip()
        else:
            local['TipoItem'] = ''
        if 'TeamDisplay' in local.columns:
            local['Team'] = local['TeamDisplay'].fillna('').astype(str).str.strip()
        elif 'Team' in local.columns:
            local['Team'] = local['Team'].fillna('').astype(str).str.strip()
        else:
            local['Team'] = ''
        local.loc[local['Team'] == '', 'Team'] = 'Sem TEAM'
        if 'Projeto' in local.columns:
            local['Projeto'] = local['Projeto'].fillna('').astype(str).str.strip()
        else:
            local['Projeto'] = ''
        local['DiasSemMovimentacao'] = pd.to_numeric(
            local.get('AgingDiasSemAlteracao', local.get('DiasSemMovimentacao')),
            errors='coerce'
        )
        local['DueDate'] = pd.to_datetime(local.get('DueDate'), errors='coerce')
        local['DiasParaVencimento'] = _due_days(local)
        local['TipoAlerta'] = alert_type
        local['MotivoAlerta'] = local.apply(reason_builder, axis=1)
        local['Severidade'] = local.apply(severity_builder, axis=1)
        local = local[alert_columns].copy()
        local['_severity_rank'] = local['Severidade'].map(lambda value: severity_order.get(value, 99))
        local = local.sort_values(
            ['_severity_rank', 'DiasParaVencimento', 'DiasSemMovimentacao', 'Projeto', 'Team', 'ItemID'],
            ascending=[True, True, False, True, True, True],
            ignore_index=True,
        )
        return local.drop(columns=['_severity_rank'])

    technical_category_defaults = {
        'arquitetura': ['tech arquitetura', 'arquitetura', 'architecture', 'arq'],
        'infra': ['tech infra', 'infra', 'devops', 'plataforma', 'platform', 'aws', 'lambda', 'deploy', 'terraform', 'kubernetes'],
        'seguranca': ['tech security', 'security', 'seguranca', 'cyber security', 'cybersecurity', 'waf', 'pen test', 'pentest', 'permiss', 'auth', 'autentic', 'lgpd'],
    }
    technical_category_cfg = parse_json_env('FLOW_PMO_PORTFOLIO_TECH_PATTERNS', technical_category_defaults)

    def _detect_technical_category(row):
        text = normalize_text(
            f"{row.get('Team', '')} {row.get('Titulo', '')} "
            f"{row.get('Componentes', '')} {row.get('Etiquetas', '')} {row.get('IssueLinkTypes', '')}"
        )
        if not text:
            return ''
        for category in ['arquitetura', 'infra', 'seguranca']:
            raw_patterns = technical_category_cfg.get(category, technical_category_defaults.get(category, []))
            patterns = raw_patterns if isinstance(raw_patterns, list) else [raw_patterns]
            for pattern in patterns:
                pattern_norm = normalize_text(pattern)
                if pattern_norm and pattern_norm in text:
                    return category
        return ''

    def _technical_alert_severity(row, has_any_created=False):
        status_category = str(row.get('StatusCategoria', '')).strip()
        due_days = pd.to_numeric(row.get('DiasParaVencimento'), errors='coerce')
        if status_category == 'Em progresso':
            return 'Critico'
        if pd.notna(due_days) and float(due_days) <= 14:
            return 'Alerta'
        if has_any_created:
            return 'Alerta'
        return 'Monitorar'

    epics_open = epics[epics['IsOpen'] == True].copy() if not epics.empty else pd.DataFrame(columns=epics.columns)
    features_open = features[features['StatusCategoria'] != 'Concluído'].copy() if not features.empty else pd.DataFrame(columns=features.columns)
    storytask_open = story_task_sem_feature[story_task_sem_feature['IsOpen'] == True].copy() if not story_task_sem_feature.empty else pd.DataFrame(columns=story_task_sem_feature.columns)

    epics_missing_feature = epics_open[epics_open['QtdFeatures'] == 0].copy() if not epics_open.empty else pd.DataFrame(columns=epics.columns)
    features_missing_story = features_open[features_open['QtdFilhos'] == 0].copy() if not features_open.empty else pd.DataFrame(columns=features.columns)

    due_items = df[df['IsOpen'] & df['DueDate'].notna()].copy() if not df.empty else pd.DataFrame(columns=df.columns)
    if not due_items.empty:
        due_items['DiasParaVencimento'] = _due_days(due_items)
    overdue_items = due_items[due_items['DiasParaVencimento'] < 0].copy() if not due_items.empty else pd.DataFrame(columns=due_items.columns)
    upcoming_items = due_items[
        (due_items['DiasParaVencimento'] >= 0) &
        (due_items['DiasParaVencimento'] <= 30)
    ].copy() if not due_items.empty else pd.DataFrame(columns=due_items.columns)

    epics_missing_feature_due = epics_missing_feature.copy()
    if not epics_missing_feature_due.empty:
        epics_missing_feature_due['DiasParaVencimento'] = _due_days(epics_missing_feature_due)
        epics_missing_feature_due = epics_missing_feature_due[
            epics_missing_feature_due['DiasParaVencimento'].notna() &
            (epics_missing_feature_due['DiasParaVencimento'] <= 14)
        ].copy()

    features_missing_story_due = features_missing_story.copy()
    if not features_missing_story_due.empty:
        features_missing_story_due['DiasParaVencimento'] = _due_days(features_missing_story_due)
        features_missing_story_due = features_missing_story_due[
            features_missing_story_due['DiasParaVencimento'].notna() &
            (features_missing_story_due['DiasParaVencimento'] <= 14)
        ].copy()

    extra_onepage_items = df[df['IsExtraOnePage'] == True].copy() if not df.empty else pd.DataFrame(columns=df.columns)
    if not extra_onepage_items.empty:
        portfolio_extra_onepage_summary = (
            extra_onepage_items.groupby(['Tipo'], dropna=False)
            .agg(TotalItens=('ID', 'nunique'))
            .reset_index()
            .rename(columns={'Tipo': 'TipoItem'})
            .sort_values(['TotalItens', 'TipoItem'], ascending=[False, True], ignore_index=True)
        )
        portfolio_extra_onepage_summary.loc[
            portfolio_extra_onepage_summary['TipoItem'].fillna('').astype(str).str.strip() == '',
            'TipoItem'
        ] = 'Sem tipo'
    else:
        portfolio_extra_onepage_summary = pd.DataFrame(columns=['TipoItem', 'TotalItens'])

    # --- Features sem épico (abertas) ---
    features_sem_epico_alerta = (
        features_open[features_open['EpicID'] == ''].copy()
        if not features_open.empty and 'EpicID' in features_open.columns
        else pd.DataFrame(columns=features.columns)
    )

    # --- Épicos com ao menos uma feature atrasada (DueDate < hoje) ---
    epics_com_features_atrasadas = pd.DataFrame(columns=epics.columns)
    if not features_open.empty and 'EpicID' in features_open.columns and 'DueDate' in features_open.columns:
        _feat_due_days = _due_days(features_open)
        _epic_ids_feat_atrasada = set(features_open.loc[_feat_due_days < 0, 'EpicID'].dropna()) - {''}
        if _epic_ids_feat_atrasada and not epics_open.empty:
            epics_com_features_atrasadas = epics_open[epics_open['ID'].isin(_epic_ids_feat_atrasada)].copy()

    # --- Itens bloqueados / impedidos ---
    _blocked_mask = df['StatusNorm'].str.contains('bloqueado|blocked|impedido', na=False, regex=True)
    itens_bloqueados = df[df['IsOpen'] & _blocked_mask].copy() if not df.empty else pd.DataFrame(columns=df.columns)

    # --- Stories/Tasks com parent vinculado mas parados há >30d ---
    _st_com_parent = df[df['IsStoryTask'] & df['HasParentFeature'] & df['IsOpen']].copy() if not df.empty else pd.DataFrame(columns=df.columns)
    stories_tasks_parados = (
        _st_com_parent[pd.to_numeric(_st_com_parent['AgingDiasSemAlteracao'], errors='coerce') > 30].copy()
        if not _st_com_parent.empty else pd.DataFrame(columns=df.columns)
    )

    # --- WIP excessivo por time (KPI sintético — número de times acima do limite) ---
    _wip_limit = int(os.environ.get('FLOW_PMO_PORTFOLIO_WIP_LIMIT', '10'))
    _team_wip = (
        df[df['IsOpen'] & df['IsInProgress']].groupby('TeamDisplay').size()
        if not df.empty else pd.Series(dtype='int64')
    )
    _times_com_wip_excessivo = int((_team_wip > _wip_limit).sum()) if not _team_wip.empty else 0

    # --- FASE 2 ---

    # --- Épicos sem prazo (DueDate ausente) ---
    epics_sem_prazo = (
        epics_open[pd.to_datetime(epics_open.get('DueDate'), errors='coerce').isna()].copy()
        if not epics_open.empty else pd.DataFrame(columns=epics.columns)
    )

    # --- Épicos em descoberta parados (Backlog > 45d sem movimentação) ---
    epics_aging_descoberta = pd.DataFrame(columns=epics.columns)
    if not epics_open.empty and 'StatusCategoria' in epics_open.columns:
        _epics_backlog = epics_open[epics_open['StatusCategoria'] == 'Backlog']
        epics_aging_descoberta = _epics_backlog[
            pd.to_numeric(_epics_backlog['AgingDiasSemAlteracao'], errors='coerce') > 45
        ].copy()

    # --- Épicos em risco de prazo: vence em ≤30d e <50% dos filhos concluídos ---
    epics_milestone_risk = pd.DataFrame(columns=epics.columns)
    if not epics_open.empty and not children_under_epic.empty:
        _done_by_epic = (
            children_under_epic[children_under_epic['ID'].map(status_categoria_by_id) == 'Concluído']
            .groupby('EpicID').size()
            .rename('_QtdConcluidos')
        )
        _epics_due = epics_open[pd.to_datetime(epics_open.get('DueDate'), errors='coerce').notna()].copy()
        if not _epics_due.empty:
            _epics_due['_DPV'] = _due_days(_epics_due)
            _epics_due['_QtdConcluidos'] = _epics_due['ID'].map(_done_by_epic).fillna(0).astype(int)
            _epics_due['_PctConclusao'] = (
                _epics_due['_QtdConcluidos'] /
                _epics_due['QtdItensFilhos'].replace(0, np.nan) * 100
            ).fillna(0).round(1)
            epics_milestone_risk = _epics_due[
                (_epics_due['_DPV'] >= 0) &
                (_epics_due['_DPV'] <= 30) &
                (_epics_due['_PctConclusao'] < 50) &
                (_epics_due['QtdItensFilhos'] > 0)
            ].copy()

    # --- Itens sem prioridade (épicos e features abertos) ---
    itens_sem_prioridade = pd.DataFrame(columns=df.columns)
    if not df.empty and 'Prioridade' in df.columns:
        _prio_vazia = df['Prioridade'].isna() | (df['Prioridade'].astype(str).str.strip().isin(['', 'nan', 'None']))
        itens_sem_prioridade = df[
            df['IsOpen'] & df['TipoNorm'].isin(epic_types | feature_types) & _prio_vazia
        ].copy()

    # --- Features em descoberta paradas (Backlog > 45d) ---
    features_aging_descoberta = pd.DataFrame(columns=features.columns)
    if not features_open.empty and 'StatusCategoria' in features_open.columns:
        _features_backlog = features_open[features_open['StatusCategoria'] == 'Backlog'].copy()
        if not _features_backlog.empty:
            _features_backlog['AgingDiasSemAlteracao'] = _features_backlog['ID'].map(age_map_all)
            features_aging_descoberta = _features_backlog[
                pd.to_numeric(_features_backlog['AgingDiasSemAlteracao'], errors='coerce') > 45
            ].copy()

    # --- Gargalo de handoff (status de espera > 7d) ---
    _handoff_mask = df['StatusNorm'].str.contains(r'aguardando|waiting|em revis|pendente|on hold', na=False, regex=True)
    itens_handoff = (
        df[df['IsOpen'] & _handoff_mask & (pd.to_numeric(df['AgingDiasSemAlteracao'], errors='coerce') > 7)].copy()
        if not df.empty else pd.DataFrame(columns=df.columns)
    )

    technical_items_base = df.copy()
    technical_items_base['TechnicalCategory'] = technical_items_base.apply(_detect_technical_category, axis=1)
    technical_items_catalog = technical_items_base[technical_items_base['TechnicalCategory'].ne('')].copy()
    if not technical_items_catalog.empty:
        technical_items_catalog = technical_items_catalog[[
            'TechnicalCategory', 'Projeto', 'TeamDisplay', 'Tipo', 'ID', 'Titulo', 'Status', 'StatusCategoria', 'ParentID', 'ParentTipo', 'EpicLinkID', 'FeatureLinkID', 'IssueLinkKeys', 'Link'
        ]].rename(columns={
            'TechnicalCategory': 'CategoriaTecnica',
            'TeamDisplay': 'Team',
            'ID': 'ItemID',
            'Tipo': 'TipoItem',
        }).sort_values(['CategoriaTecnica', 'Projeto', 'Team', 'StatusCategoria', 'ItemID'], ignore_index=True)
    else:
        technical_items_catalog = pd.DataFrame(columns=['CategoriaTecnica', 'Projeto', 'Team', 'TipoItem', 'ItemID', 'Titulo', 'Status', 'StatusCategoria', 'ParentID', 'ParentTipo', 'EpicLinkID', 'FeatureLinkID', 'IssueLinkKeys', 'Link'])

    technical_by_parent = {}
    if not technical_items_base.empty:
        for _, row in technical_items_base[technical_items_base['TechnicalCategory'].ne('')].iterrows():
            candidate_refs = []
            for ref_col in ['ParentID', 'EpicLinkID', 'FeatureLinkID']:
                ref_value = str(row.get(ref_col) or '').strip()
                if ref_value:
                    candidate_refs.append(ref_value)
            issue_link_keys = str(row.get('IssueLinkKeys') or '').strip()
            if issue_link_keys:
                for token in issue_link_keys.split(','):
                    ref_value = str(token).strip()
                    if ref_value:
                        candidate_refs.append(ref_value)
            for ref_value in candidate_refs:
                technical_by_parent.setdefault(ref_value, []).append(row)

    technical_alert_rows = []
    technical_epic_summary_rows = []
    if not epics_open.empty:
        epics_open_proxy = epics_open.copy()
        epics_open_proxy['TechnicalCategory'] = epics_open_proxy.apply(_detect_technical_category, axis=1)
        epics_open_proxy['DueDate'] = pd.to_datetime(epics_open_proxy.get('DueDate'), errors='coerce')
        epics_open_proxy['DiasParaVencimento'] = _due_days(epics_open_proxy)
        for _, epic_row in epics_open_proxy.iterrows():
            epic_id = str(epic_row.get('ID') or '').strip()
            if not epic_id:
                continue
            if str(epic_row.get('TechnicalCategory') or '').strip():
                continue
            linked_rows = technical_by_parent.get(epic_id, [])
            coverage = {}
            created_any = False
            validated_any = False
            for category in ['arquitetura', 'infra', 'seguranca']:
                linked_category_rows = [r for r in linked_rows if str(r.get('TechnicalCategory') or '').strip() == category]
                created = len(linked_category_rows) > 0
                validated = any(str(r.get('StatusCategoria', '')).strip() == 'Concluído' for r in linked_category_rows)
                coverage[category] = {'created': created, 'validated': validated}
                created_any = created_any or created
                validated_any = validated_any or validated
                if not created:
                    technical_alert_rows.append({
                        'Severidade': _technical_alert_severity(epic_row, has_any_created=created_any),
                        'TipoAlerta': f'Épico sem item técnico de {category}',
                        'TipoItem': str(epic_row.get('Tipo') or '').strip(),
                        'Projeto': str(epic_row.get('Projeto') or '').strip(),
                        'Team': str(epic_row.get('TeamDisplay') or 'Sem TEAM').strip() or 'Sem TEAM',
                        'ItemID': epic_id,
                        'Titulo': str(epic_row.get('Titulo') or '').strip(),
                        'Status': str(epic_row.get('Status') or '').strip(),
                        'DiasSemMovimentacao': pd.to_numeric(epic_row.get('AgingDiasSemAlteracao'), errors='coerce'),
                        'DueDate': pd.to_datetime(epic_row.get('DueDate'), errors='coerce'),
                        'DiasParaVencimento': pd.to_numeric(epic_row.get('DiasParaVencimento'), errors='coerce'),
                        'MotivoAlerta': f'Nenhum item técnico classificado como {category} foi encontrado via vínculo explícito ParentID no snapshot atual.',
                        'Link': epic_row.get('Link', ''),
                    })
                elif not validated:
                    technical_alert_rows.append({
                        'Severidade': _technical_alert_severity(epic_row, has_any_created=True),
                        'TipoAlerta': f'Épico com {category} não validado',
                        'TipoItem': str(epic_row.get('Tipo') or '').strip(),
                        'Projeto': str(epic_row.get('Projeto') or '').strip(),
                        'Team': str(epic_row.get('TeamDisplay') or 'Sem TEAM').strip() or 'Sem TEAM',
                        'ItemID': epic_id,
                        'Titulo': str(epic_row.get('Titulo') or '').strip(),
                        'Status': str(epic_row.get('Status') or '').strip(),
                        'DiasSemMovimentacao': pd.to_numeric(epic_row.get('AgingDiasSemAlteracao'), errors='coerce'),
                        'DueDate': pd.to_datetime(epic_row.get('DueDate'), errors='coerce'),
                        'DiasParaVencimento': pd.to_numeric(epic_row.get('DiasParaVencimento'), errors='coerce'),
                        'MotivoAlerta': f'Existe item técnico de {category} vinculado ao épico, mas nenhum aparece concluído no snapshot atual.',
                        'Link': epic_row.get('Link', ''),
                    })
            technical_epic_summary_rows.append({
                'Projeto': str(epic_row.get('Projeto') or '').strip(),
                'Team': str(epic_row.get('TeamDisplay') or 'Sem TEAM').strip() or 'Sem TEAM',
                'EpicID': epic_id,
                'Titulo': str(epic_row.get('Titulo') or '').strip(),
                'Status': str(epic_row.get('Status') or '').strip(),
                'Arquitetura Criada': 'Sim' if coverage.get('arquitetura', {}).get('created') else 'Não',
                'Arquitetura Validada': 'Sim' if coverage.get('arquitetura', {}).get('validated') else 'Não',
                'Infra Criada': 'Sim' if coverage.get('infra', {}).get('created') else 'Não',
                'Infra Validada': 'Sim' if coverage.get('infra', {}).get('validated') else 'Não',
                'Segurança Criada': 'Sim' if coverage.get('seguranca', {}).get('created') else 'Não',
                'Segurança Validada': 'Sim' if coverage.get('seguranca', {}).get('validated') else 'Não',
                'Itens Técnicos Vinculados': int(len(linked_rows)),
                'Link': epic_row.get('Link', ''),
            })

    portfolio_technical_epic_summary = pd.DataFrame(technical_epic_summary_rows)
    if not portfolio_technical_epic_summary.empty:
        portfolio_technical_epic_summary = portfolio_technical_epic_summary.sort_values(
            ['Itens Técnicos Vinculados', 'Projeto', 'Team', 'EpicID'],
            ascending=[True, True, True, True],
            ignore_index=True,
        )

    alert_frames = [
        _build_alert_frame(
            epics_missing_feature,
            'ID',
            'Tipo',
            'Épico sem feature',
            lambda row: 'Épico aberto sem feature vinculada.',
            lambda row: _staleness_severity(row.get('AgingDiasSemAlteracao'))
        ),
        _build_alert_frame(
            features_missing_story,
            'ID',
            'Tipo',
            'Feature sem story/task',
            lambda row: 'Feature aberta sem story/task vinculado.',
            lambda row: _staleness_severity(row.get('DiasSemMovimentacao'))
        ),
        _build_alert_frame(
            storytask_open,
            'ID',
            'Tipo',
            'Story/Task órfão',
            lambda row: 'Story/Task sem vínculo estrutural válido com feature ou épico.',
            lambda row: (
                'Critico' if str(row.get('StatusCategoria', '')).strip() == 'Em progresso' else
                ('Alerta' if str(row.get('StatusCategoria', '')).strip() == 'Backlog' else 'Monitorar')
            )
        ),
        _build_alert_frame(
            epics_open[pd.to_numeric(epics_open.get('AgingDiasSemAlteracao'), errors='coerce') > 10].copy() if not epics_open.empty else pd.DataFrame(columns=epics.columns),
            'ID',
            'Tipo',
            'Épico parado',
            lambda row: f"Épico aberto sem movimentação há {int(row.get('AgingDiasSemAlteracao') or 0)} dias.",
            lambda row: _staleness_severity(row.get('AgingDiasSemAlteracao'))
        ),
        _build_alert_frame(
            features_open[pd.to_numeric(features_open.get('DiasSemMovimentacao'), errors='coerce') > 10].copy() if not features_open.empty else pd.DataFrame(columns=features.columns),
            'ID',
            'Tipo',
            'Feature parada',
            lambda row: f"Feature aberta sem movimentação há {int(row.get('DiasSemMovimentacao') or 0)} dias.",
            lambda row: _staleness_severity(row.get('DiasSemMovimentacao'))
        ),
        _build_alert_frame(
            overdue_items,
            'ID',
            'Tipo',
            'Item vencido',
            lambda row: f"Item aberto com target date vencida há {abs(int(row.get('DiasParaVencimento') or 0))} dias.",
            lambda row: 'Critico'
        ),
        _build_alert_frame(
            upcoming_items,
            'ID',
            'Tipo',
            'Item próximo do vencimento',
            lambda row: f"Item aberto com target date em {int(row.get('DiasParaVencimento') or 0)} dias.",
            lambda row: (
                'Critico' if pd.notna(row.get('DiasParaVencimento')) and float(row.get('DiasParaVencimento')) <= 7 else
                ('Alerta' if pd.notna(row.get('DiasParaVencimento')) and float(row.get('DiasParaVencimento')) <= 14 else 'Monitorar')
            )
        ),
        _build_alert_frame(
            epics_missing_feature_due,
            'ID',
            'Tipo',
            'Prazo crítico sem decomposição',
            lambda row: 'Épico vencido ou próximo do vencimento sem feature vinculada.',
            lambda row: 'Critico' if pd.notna(row.get('DiasParaVencimento')) and float(row.get('DiasParaVencimento')) <= 7 else 'Alerta'
        ),
        _build_alert_frame(
            features_missing_story_due,
            'ID',
            'Tipo',
            'Prazo crítico sem decomposição',
            lambda row: 'Feature vencida ou próxima do vencimento sem story/task vinculado.',
            lambda row: 'Critico' if pd.notna(row.get('DiasParaVencimento')) and float(row.get('DiasParaVencimento')) <= 7 else 'Alerta'
        ),
        _build_alert_frame(
            extra_onepage_items,
            'ID',
            'Tipo',
            'Tag EXTRA-ONEPAGE',
            lambda row: 'Item marcado com a tag EXTRA-ONEPAGE para destaque no one page executivo.',
            lambda row: 'Alerta'
        ),
        _build_alert_frame(
            features_sem_epico_alerta,
            'ID',
            'Tipo',
            'Feature sem épico',
            lambda row: 'Feature aberta sem épico pai vinculado.',
            lambda row: _staleness_severity(row.get('DiasSemMovimentacao', row.get('AgingDiasSemAlteracao')))
        ),
        _build_alert_frame(
            epics_com_features_atrasadas,
            'ID',
            'Tipo',
            'Épico c/ feature atrasada',
            lambda row: 'Épico com ao menos uma feature com target date vencida.',
            lambda row: 'Critico'
        ),
        _build_alert_frame(
            itens_bloqueados,
            'ID',
            'Tipo',
            'Item bloqueado',
            lambda row: f"Item em status bloqueado/impedido: {str(row.get('Status', '')).strip()}.",
            lambda row: 'Critico'
        ),
        _build_alert_frame(
            stories_tasks_parados,
            'ID',
            'Tipo',
            'Story/Task parado',
            lambda row: f"Story/Task sem movimentação há {int(pd.to_numeric(row.get('AgingDiasSemAlteracao'), errors='coerce') or 0)} dias.",
            lambda row: _staleness_severity(row.get('AgingDiasSemAlteracao'))
        ),
        _build_alert_frame(
            epics_sem_prazo,
            'ID',
            'Tipo',
            'Épico sem prazo',
            lambda row: 'Épico aberto sem target date definida.',
            lambda row: _staleness_severity(row.get('AgingDiasSemAlteracao'))
        ),
        _build_alert_frame(
            epics_aging_descoberta,
            'ID',
            'Tipo',
            'Épico em descoberta parado',
            lambda row: f"Épico em Backlog sem movimentação há {int(pd.to_numeric(row.get('AgingDiasSemAlteracao'), errors='coerce') or 0)} dias.",
            lambda row: 'Critico' if pd.to_numeric(row.get('AgingDiasSemAlteracao'), errors='coerce') > 90 else 'Alerta'
        ),
        _build_alert_frame(
            epics_milestone_risk,
            'ID',
            'Tipo',
            'Épico em risco de prazo',
            lambda row: f"Vence em {int(pd.to_numeric(row.get('_DPV', 0), errors='coerce') or 0)}d com {int(pd.to_numeric(row.get('_PctConclusao', 0), errors='coerce') or 0)}% de conclusão.",
            lambda row: 'Critico' if pd.to_numeric(row.get('_DPV', 99), errors='coerce') <= 7 else 'Alerta'
        ),
        _build_alert_frame(
            itens_sem_prioridade,
            'ID',
            'Tipo',
            'Item sem prioridade',
            lambda row: 'Épico ou Feature aberto sem prioridade definida.',
            lambda row: 'Monitorar'
        ),
        _build_alert_frame(
            features_aging_descoberta,
            'ID',
            'Tipo',
            'Feature em descoberta parada',
            lambda row: f"Feature em Backlog sem movimentação há {int(pd.to_numeric(row.get('AgingDiasSemAlteracao'), errors='coerce') or 0)} dias.",
            lambda row: 'Critico' if pd.to_numeric(row.get('AgingDiasSemAlteracao'), errors='coerce') > 90 else 'Alerta'
        ),
        _build_alert_frame(
            itens_handoff,
            'ID',
            'Tipo',
            'Gargalo de handoff',
            lambda row: f"Item parado em status de espera há {int(pd.to_numeric(row.get('AgingDiasSemAlteracao'), errors='coerce') or 0)} dias: {str(row.get('Status', '')).strip()}.",
            lambda row: 'Critico' if pd.to_numeric(row.get('AgingDiasSemAlteracao'), errors='coerce') > 14 else 'Alerta'
        ),
    ]

    technical_alerts_df = pd.DataFrame(technical_alert_rows, columns=alert_columns) if technical_alert_rows else _empty_alert_df()
    if technical_alerts_df is not None and not technical_alerts_df.empty:
        alert_frames.append(technical_alerts_df)

    non_empty_alert_frames = [frame for frame in alert_frames if frame is not None and not frame.empty]
    portfolio_alerts_detail = pd.concat(non_empty_alert_frames, ignore_index=True) if non_empty_alert_frames else _empty_alert_df()
    if not portfolio_alerts_detail.empty:
        portfolio_alerts_detail['_severity_rank'] = portfolio_alerts_detail['Severidade'].map(lambda value: severity_order.get(value, 99))
        portfolio_alerts_detail = portfolio_alerts_detail.sort_values(
            ['_severity_rank', 'TipoAlerta', 'DiasParaVencimento', 'DiasSemMovimentacao', 'Projeto', 'Team', 'ItemID'],
            ascending=[True, True, True, False, True, True, True],
            ignore_index=True,
        ).drop(columns=['_severity_rank'])

        portfolio_alerts_indicator_summary = (
            portfolio_alerts_detail.groupby(['TipoAlerta', 'Severidade'], dropna=False)
            .agg(Ocorrencias=('ItemID', 'count'), ItensUnicos=('ItemID', 'nunique'))
            .reset_index()
            .sort_values(['TipoAlerta', 'Ocorrencias'], ascending=[True, False], ignore_index=True)
        )
        portfolio_alerts_severity_summary = (
            portfolio_alerts_detail.groupby(['Severidade'], dropna=False)
            .agg(Ocorrencias=('ItemID', 'count'), ItensUnicos=('ItemID', 'nunique'))
            .reset_index()
        )
        portfolio_alerts_severity_summary['_severity_rank'] = portfolio_alerts_severity_summary['Severidade'].map(lambda value: severity_order.get(value, 99))
        portfolio_alerts_severity_summary = portfolio_alerts_severity_summary.sort_values('_severity_rank').drop(columns=['_severity_rank']).reset_index(drop=True)
        portfolio_alerts_by_team = (
            portfolio_alerts_detail.groupby(['Team', 'Severidade'], dropna=False)
            .agg(Ocorrencias=('ItemID', 'count'), ItensUnicos=('ItemID', 'nunique'))
            .reset_index()
            .sort_values(['Ocorrencias', 'ItensUnicos', 'Team'], ascending=[False, False, True], ignore_index=True)
        )
        portfolio_alerts_by_project = (
            portfolio_alerts_detail.groupby(['Projeto', 'Severidade'], dropna=False)
            .agg(Ocorrencias=('ItemID', 'count'), ItensUnicos=('ItemID', 'nunique'))
            .reset_index()
            .sort_values(['Ocorrencias', 'ItensUnicos', 'Projeto'], ascending=[False, False, True], ignore_index=True)
        )
        severity_counts = portfolio_alerts_detail['Severidade'].value_counts()
        type_counts = portfolio_alerts_detail['TipoAlerta'].value_counts()
        _critico_por_team = (
            portfolio_alerts_by_team[portfolio_alerts_by_team['Severidade'] == 'Critico']['Ocorrencias']
            if not portfolio_alerts_by_team.empty and 'Severidade' in portfolio_alerts_by_team.columns
            else pd.Series(dtype='int64')
        )
        _avg_critico = _critico_por_team.mean() if not _critico_por_team.empty else 0
        _times_concentracao_risco = int((_critico_por_team > max(5, _avg_critico * 1.5)).sum()) if not _critico_por_team.empty else 0
        portfolio_alert_kpis = pd.DataFrame([
            {'Indicador': 'Ocorrências críticas', 'Valor': int(severity_counts.get('Critico', 0))},
            {'Indicador': 'Ocorrências alerta', 'Valor': int(severity_counts.get('Alerta', 0))},
            {'Indicador': 'Ocorrências monitorar', 'Valor': int(severity_counts.get('Monitorar', 0))},
            {'Indicador': 'Itens únicos com alerta', 'Valor': int(portfolio_alerts_detail['ItemID'].nunique())},
            {'Indicador': 'Itens com tag EXTRA-ONEPAGE', 'Valor': int(extra_onepage_items['ID'].nunique())},
            {'Indicador': 'Épicos sem feature', 'Valor': int(type_counts.get('Épico sem feature', 0))},
            {'Indicador': 'Features sem story/task', 'Valor': int(type_counts.get('Feature sem story/task', 0))},
            {'Indicador': 'Itens vencidos', 'Valor': int(type_counts.get('Item vencido', 0))},
            {'Indicador': 'Itens vencendo em até 7d', 'Valor': int(len(upcoming_items[upcoming_items['DiasParaVencimento'] <= 7])) if not upcoming_items.empty else 0},
            {'Indicador': 'Épicos sem arquitetura', 'Valor': int(type_counts.get('Épico sem item técnico de arquitetura', 0))},
            {'Indicador': 'Épicos sem infra', 'Valor': int(type_counts.get('Épico sem item técnico de infra', 0))},
            {'Indicador': 'Épicos sem segurança', 'Valor': int(type_counts.get('Épico sem item técnico de seguranca', 0)) + int(type_counts.get('Épico sem item técnico de segurança', 0))},
            {'Indicador': 'Épicos c/ features atrasadas', 'Valor': int(type_counts.get('Épico c/ feature atrasada', 0))},
            {'Indicador': 'Features sem épico', 'Valor': int(type_counts.get('Feature sem épico', 0))},
            {'Indicador': 'Itens bloqueados', 'Valor': int(type_counts.get('Item bloqueado', 0))},
            {'Indicador': 'Stories/Tasks parados', 'Valor': int(type_counts.get('Story/Task parado', 0))},
            {'Indicador': 'Times c/ WIP excessivo', 'Valor': _times_com_wip_excessivo},
            {'Indicador': 'Épicos sem prazo', 'Valor': int(type_counts.get('Épico sem prazo', 0))},
            {'Indicador': 'Épicos em descoberta parados', 'Valor': int(type_counts.get('Épico em descoberta parado', 0))},
            {'Indicador': 'Épicos em risco de prazo', 'Valor': int(type_counts.get('Épico em risco de prazo', 0))},
            {'Indicador': 'Times c/ concentração de risco', 'Valor': _times_concentracao_risco},
            {'Indicador': 'Épicos parados', 'Valor': int(type_counts.get('Épico parado', 0))},
            {'Indicador': 'Features paradas', 'Valor': int(type_counts.get('Feature parada', 0))},
            {'Indicador': 'Prazo crítico sem decomposição', 'Valor': int(type_counts.get('Prazo crítico sem decomposição', 0))},
            {'Indicador': 'Stories/Tasks órfãos', 'Valor': int(type_counts.get('Story/Task órfão', 0))},
            {'Indicador': 'Itens sem prioridade', 'Valor': int(type_counts.get('Item sem prioridade', 0))},
            {'Indicador': 'Features em descoberta paradas', 'Valor': int(type_counts.get('Feature em descoberta parada', 0))},
            {'Indicador': 'Gargalos de handoff', 'Valor': int(type_counts.get('Gargalo de handoff', 0))},
        ])
    else:
        portfolio_alerts_indicator_summary = pd.DataFrame(columns=['TipoAlerta', 'Severidade', 'Ocorrencias', 'ItensUnicos'])
        portfolio_alerts_severity_summary = pd.DataFrame(columns=['Severidade', 'Ocorrencias', 'ItensUnicos'])
        portfolio_alerts_by_team = pd.DataFrame(columns=['Team', 'Severidade', 'Ocorrencias', 'ItensUnicos'])
        portfolio_alerts_by_project = pd.DataFrame(columns=['Projeto', 'Severidade', 'Ocorrencias', 'ItensUnicos'])
        portfolio_alert_kpis = pd.DataFrame(columns=['Indicador', 'Valor'])

    portfolio_technical_readiness_notes = pd.DataFrame([
        {
            'Status': 'Proxy explícito implementado',
            'Detalhe': 'A cobertura técnica agora usa apenas itens classificados por TEAM/título e vinculados ao épico via ParentID no próprio snapshot de portfólio.',
        },
        {
            'Status': 'Limitação atual',
            'Detalhe': 'Itens técnicos existentes fora da hierarquia explícita do snapshot não entram na cobertura; isso pode gerar falso positivo de ausência de arquitetura/infra/segurança.',
        },
        {
            'Status': 'Pendente de contrato de dados',
            'Detalhe': 'A validação factual no fluxo ainda depende de vínculo explícito entre épico de portfólio e item técnico no downstream, o que hoje não existe de forma confiável por ID.',
        },
    ])

    # Scorecard consolidado de saúde do portfólio.
    def _clamp_score(value):
        try:
            return round(max(0.0, min(100.0, float(value))), 1)
        except Exception:
            return 0.0

    def _score_band(score):
        if score >= 85:
            return 'Saudável'
        if score >= 70:
            return 'Atenção'
        return 'Crítico'

    pct_epicos_fluxo = round((len(epics_com_itens_fluxo) / len(epics) * 100), 1) if len(epics) else 0.0
    pct_features_filhos = round((len(features_com_filhos) / len(features) * 100), 1) if len(features) else 0.0
    pct_story_sem_feature = float(storytask_sem_feature_tatico_metric.get('Percentual', 0.0) or 0.0)
    pct_story_orfaos = float(storytask_orfaos_metric.get('Percentual', 0.0) or 0.0)
    features_com_effort_count = int((features['EffortTShirtSize'].fillna('').astype(str).str.strip() != '').sum()) if not features.empty else 0
    pct_features_effort = round((features_com_effort_count / len(features) * 100), 1) if len(features) else 100.0
    pct_status_nao_mapeado = round((int((~df['StatusMapeado']).sum()) / total_items_all * 100), 1) if total_items_all else 0.0
    structure_score = _clamp_score(np.mean([
        pct_epicos_fluxo,
        pct_features_filhos,
        100.0 - pct_story_sem_feature,
        100.0 - pct_story_orfaos,
    ]))

    aging_p90_open = float(aging_open['AgingDiasSemAlteracao'].quantile(0.90)) if not aging_open.empty else np.nan
    if pd.isna(aging_p90_open):
        aging_p90_score = 100.0
    elif aging_p90_open <= 15:
        aging_p90_score = 100.0
    elif aging_p90_open <= 30:
        aging_p90_score = 75.0
    elif aging_p90_open <= 45:
        aging_p90_score = 50.0
    elif aging_p90_open <= 60:
        aging_p90_score = 25.0
    else:
        aging_p90_score = 0.0
    aging_score = _clamp_score(np.mean([
        100.0 - float(flow_health_summary.loc[flow_health_summary['Indicador'] == '% backlog parado >15d', 'Percentual'].iloc[0]) if not flow_health_summary.empty else 100.0,
        100.0 - float(flow_health_summary.loc[flow_health_summary['Indicador'] == '% backlog parado >30d', 'Percentual'].iloc[0]) if not flow_health_summary.empty else 100.0,
        aging_p90_score,
    ]))

    scope_due_base = df[df['TipoNorm'].isin(epic_types | feature_types)].copy()
    open_due_scope = scope_due_base[scope_due_base['IsOpen'] == True].copy() if not scope_due_base.empty else pd.DataFrame(columns=df.columns)
    due_scope_total = int(len(open_due_scope))
    overdue_scope = int(((pd.to_datetime(open_due_scope.get('DueDate'), errors='coerce').dt.normalize() < today) & pd.to_datetime(open_due_scope.get('DueDate'), errors='coerce').notna()).sum()) if due_scope_total else 0
    upcoming_14_scope = int((((pd.to_datetime(open_due_scope.get('DueDate'), errors='coerce').dt.normalize() - today).dt.days >= 0) & ((pd.to_datetime(open_due_scope.get('DueDate'), errors='coerce').dt.normalize() - today).dt.days <= 14)).sum()) if due_scope_total else 0
    missing_due_scope = int(pd.to_datetime(open_due_scope.get('DueDate'), errors='coerce').isna().sum()) if due_scope_total else 0
    prazo_score = _clamp_score(np.mean([
        100.0 - (overdue_scope / due_scope_total * 100.0 if due_scope_total else 0.0),
        100.0 - (upcoming_14_scope / due_scope_total * 100.0 if due_scope_total else 0.0),
        100.0 - (missing_due_scope / due_scope_total * 100.0 if due_scope_total else 0.0),
    ]))

    # Due Date Performance: breakdown detalhado por tipo (épico e feature) e status de prazo.
    def _ddp_item_status(row):
        due = pd.to_datetime(row.get('DueDate'), errors='coerce')
        done = pd.to_datetime(row.get('DataDone'), errors='coerce')
        if pd.isna(due):
            return 'Sem target'
        if pd.notna(done):
            return 'No prazo' if done.normalize() <= due.normalize() else 'Atrasado'
        days_to_due = (due.normalize() - today).days
        if days_to_due < 0:
            return 'Vencido'
        if days_to_due <= 14:
            return 'Risco ≤14d'
        if days_to_due <= 30:
            return 'Risco 15-30d'
        return 'Em acompanhamento'

    _ddp_status_order = ['No prazo', 'Atrasado', 'Vencido', 'Risco ≤14d', 'Risco 15-30d', 'Em acompanhamento', 'Sem target']
    if not scope_due_base.empty:
        _ddp_df = scope_due_base.copy()
        _ddp_df['_DDPStatus'] = _ddp_df.apply(_ddp_item_status, axis=1)
        _ddp_df['_TipoLabel'] = _ddp_df['TipoNorm'].map(lambda t: 'Épico' if t in epic_types else 'Feature')
        _ddp_rows = []
        for _tipo_label in ['Épico', 'Feature']:
            _tipo_sub = _ddp_df[_ddp_df['_TipoLabel'] == _tipo_label]
            _total = len(_tipo_sub)
            for _status in _ddp_status_order:
                _n = int((_tipo_sub['_DDPStatus'] == _status).sum())
                _ddp_rows.append({
                    'Tipo': _tipo_label,
                    'Status DDP': _status,
                    'Qtd': _n,
                    '% do Total': round(_n / _total * 100, 1) if _total > 0 else 0.0,
                })
        due_date_performance_df = pd.DataFrame(_ddp_rows)
    else:
        due_date_performance_df = pd.DataFrame(columns=['Tipo', 'Status DDP', 'Qtd', '% do Total'])

    pct_status_fora = round((int(df['StatusForaWorkflow'].sum()) / len(df) * 100), 1) if len(df) else 0.0
    workflow_score = _clamp_score(np.mean([
        100.0 - pct_status_fora,
        100.0 - pct_status_nao_mapeado,
    ]))

    sem_mov_30_effort = int(pd.to_numeric(effort_stale_summary.get('SemMov30d'), errors='coerce').fillna(0).sum()) if not effort_stale_summary.empty else 0
    effort_score = _clamp_score(np.mean([
        pct_features_effort,
        100.0 - (sem_mov_30_effort / len(features) * 100.0 if len(features) else 0.0),
    ]))

    overall_health_score = _clamp_score(np.mean([
        structure_score,
        aging_score,
        prazo_score,
        workflow_score,
        effort_score,
    ]))
    portfolio_health_scorecard = pd.DataFrame([
        {'Indicador': 'Saúde geral do portfólio', 'Score': overall_health_score, 'Status': _score_band(overall_health_score), 'Detalhe': 'Consolida estrutura, aging, prazo, workflow e effort.'},
        {'Indicador': 'Estrutura', 'Score': structure_score, 'Status': _score_band(structure_score), 'Detalhe': f'Épicos com itens: {pct_epicos_fluxo:.1f}% | Features com filhos: {pct_features_filhos:.1f}% | Órfãos: {pct_story_orfaos:.1f}%'},
        {'Indicador': 'Aging', 'Score': aging_score, 'Status': _score_band(aging_score), 'Detalhe': f'Backlog >15d: {backlog_parado_15} | >30d: {backlog_parado_30} | P90 aberto: {0 if pd.isna(aging_p90_open) else round(aging_p90_open, 1)}d'},
        {'Indicador': 'Prazo', 'Score': prazo_score, 'Status': _score_band(prazo_score), 'Detalhe': f'Vencidos: {overdue_scope} | Vencendo <=14d: {upcoming_14_scope} | Sem target: {missing_due_scope}'},
        {'Indicador': 'Workflow', 'Score': workflow_score, 'Status': _score_band(workflow_score), 'Detalhe': f'Fora workflow: {pct_status_fora:.1f}% | Não mapeado: {pct_status_nao_mapeado:.1f}%'},
        {'Indicador': 'Effort', 'Score': effort_score, 'Status': _score_band(effort_score), 'Detalhe': f'Features com effort: {pct_features_effort:.1f}% | Sem mov. 30d: {sem_mov_30_effort}'},
    ])
    portfolio_health_dimension_summary = pd.DataFrame([
        {'Dimensão': 'Estrutura', 'Score': structure_score, 'Status': _score_band(structure_score), 'Driver': '% épicos com itens / % features com filhos / órfãos'},
        {'Dimensão': 'Aging', 'Score': aging_score, 'Status': _score_band(aging_score), 'Driver': 'Backlog parado + P90 de aging aberto'},
        {'Dimensão': 'Prazo', 'Score': prazo_score, 'Status': _score_band(prazo_score), 'Driver': 'Vencidos / vencendo / sem target date'},
        {'Dimensão': 'Workflow', 'Score': workflow_score, 'Status': _score_band(workflow_score), 'Driver': 'Status fora do workflow + não mapeados'},
        {'Dimensão': 'Effort', 'Score': effort_score, 'Status': _score_band(effort_score), 'Driver': 'Cobertura de effort + stale 30d'},
    ])

    # Cards executivos no estilo "mosaico".
    sem_team = int((df['Team'].str.strip() == '').sum())
    em_dia = int(((df['IsOpen']) & (df['AgingDiasSemAlteracao'] <= 15)).sum())
    atrasadas = int(((df['IsOpen']) & (df['AgingDiasSemAlteracao'] > 30)).sum())
    divergente = int(len(features_sem_epico) + len(epics_sem_features))
    team_original_preenchido = int((df['TeamOriginal'].fillna('').astype(str).str.strip() != '').sum())
    total_itens = int(len(df))
    features_com_epico = int((features['EpicID'].fillna('').astype(str).str.strip() != '').sum()) if not features.empty else 0
    features_com_effort = int((features['EffortTShirtSize'].fillna('').astype(str).str.strip() != '').sum()) if not features.empty else 0
    itens_status_nao_mapeado = int((~df['StatusMapeado']).sum())
    executive_tiles = pd.DataFrame([
        {'Indicador': 'Épicos', 'Valor': int(len(epics)), 'Tipo': 'ok'},
        {'Indicador': 'Features', 'Valor': int(len(features)), 'Tipo': 'ok'},
        {'Indicador': 'Sem TEAM', 'Valor': sem_team, 'Tipo': 'risco'},
        {'Indicador': 'Em dia', 'Valor': em_dia, 'Tipo': 'ok'},
        {'Indicador': 'Atrasadas', 'Valor': atrasadas, 'Tipo': 'risco'},
        {'Indicador': 'Estado divergente', 'Valor': divergente, 'Tipo': 'alerta'},
        {'Indicador': 'Features sem épico', 'Valor': int(len(features_sem_epico)), 'Tipo': 'alerta'},
        {'Indicador': 'Épicos sem features', 'Valor': int(len(epics_sem_features)), 'Tipo': 'alerta'},
        {'Indicador': 'Hist./Tasks sem feature tática', 'Valor': int(storytask_sem_feature_tatico_metric.get('Numerador', 0)), 'Tipo': 'alerta'},
        {'Indicador': 'Hist./Tasks órfãos', 'Valor': int(storytask_orfaos_metric.get('Numerador', 0)), 'Tipo': 'risco'},
    ])
    quality_summary = pd.DataFrame([
        {
            'Indicador': '% com TEAM',
            'Percentual': round((team_original_preenchido / total_itens * 100), 1) if total_itens else 0.0,
            'Numerador': team_original_preenchido,
            'Denominador': total_itens,
        },
        {
            'Indicador': '% features com épico',
            'Percentual': round((features_com_epico / len(features) * 100), 1) if len(features) else 0.0,
            'Numerador': features_com_epico,
            'Denominador': int(len(features)),
        },
        {
            'Indicador': '% features com effort',
            'Percentual': round((features_com_effort / len(features) * 100), 1) if len(features) else 0.0,
            'Numerador': features_com_effort,
            'Denominador': int(len(features)),
        },
        {
            'Indicador': '% itens com status não mapeado',
            'Percentual': round((itens_status_nao_mapeado / total_itens * 100), 1) if total_itens else 0.0,
            'Numerador': itens_status_nao_mapeado,
            'Denominador': total_itens,
        },
    ])

    # Concentração de portfólio em épicos (volume / aging).
    top_epicos_volume = (
        epics[['TeamDisplay', 'ID', 'Titulo', 'Status', 'QtdFeatures', 'QtdItensFluxo', 'AgingDiasSemAlteracao', 'Link']]
        .rename(columns={'TeamDisplay': 'Team', 'ID': 'EpicID'})
        .sort_values(['QtdItensFluxo', 'QtdFeatures', 'AgingDiasSemAlteracao'], ascending=[False, False, False], ignore_index=True)
        .head(15)
    ) if not epics.empty else pd.DataFrame(columns=['Team', 'EpicID', 'Titulo', 'Status', 'QtdFeatures', 'QtdItensFluxo', 'AgingDiasSemAlteracao', 'Link'])

    top_epicos_aging = (
        epics[epics['IsOpen'] == True][['TeamDisplay', 'ID', 'Titulo', 'Status', 'AgingDiasSemAlteracao', 'QtdItensFluxo', 'QtdFeatures', 'Link']]
        .rename(columns={'TeamDisplay': 'Team', 'ID': 'EpicID'})
        .sort_values(['AgingDiasSemAlteracao', 'QtdItensFluxo'], ascending=[False, False], ignore_index=True)
        .head(15)
    ) if not epics.empty else pd.DataFrame(columns=['Team', 'EpicID', 'Titulo', 'Status', 'AgingDiasSemAlteracao', 'QtdItensFluxo', 'QtdFeatures', 'Link'])

    # Shares de concentração (TEAM e Épicos).
    concentracao_team_share = epicos_por_team_total.copy() if epicos_por_team_total is not None and not epicos_por_team_total.empty else pd.DataFrame(columns=['Team', 'QtdEpicos'])
    if features_por_team_total is not None and not features_por_team_total.empty:
        concentracao_team_share = concentracao_team_share.merge(features_por_team_total, on='Team', how='outer')
    if not concentracao_team_share.empty:
        for col in ['QtdEpicos', 'QtdFeatures']:
            col_series = concentracao_team_share[col] if col in concentracao_team_share.columns else pd.Series(0, index=concentracao_team_share.index)
            concentracao_team_share[col] = pd.to_numeric(col_series, errors='coerce').fillna(0).astype(int)
        total_items_team = group_count(df, ['TeamDisplay'], 'TotalItems').rename(columns={'TeamDisplay': 'Team'})
        concentracao_team_share = concentracao_team_share.merge(total_items_team, on='Team', how='outer')
        concentracao_team_share['TotalItems'] = pd.to_numeric(concentracao_team_share['TotalItems'], errors='coerce').fillna(0).astype(int)
        total_items_scope = int(concentracao_team_share['TotalItems'].sum())
        concentracao_team_share['% Share'] = (concentracao_team_share['TotalItems'] / (total_items_scope if total_items_scope else np.nan) * 100).fillna(0).round(1)
        concentracao_team_share = concentracao_team_share.sort_values(['TotalItems', 'Team'], ascending=[False, True], ignore_index=True)
        concentracao_team_share['% Share Acum'] = concentracao_team_share['% Share'].cumsum().round(1)
    else:
        total_items_scope = 0

    concentracao_epico_share = top_epicos_volume.copy()
    if not concentracao_epico_share.empty:
        total_epic_flow_items = int(epics['QtdItensFluxo'].sum()) if not epics.empty else 0
        concentracao_epico_share['% Share Itens Fluxo'] = (
            concentracao_epico_share['QtdItensFluxo'] / (total_epic_flow_items if total_epic_flow_items else np.nan) * 100
        ).fillna(0).round(1)
        concentracao_epico_share['% Share Acum'] = concentracao_epico_share['% Share Itens Fluxo'].cumsum().round(1)

    def _topn_share(series_values, topn):
        s = pd.to_numeric(pd.Series(series_values), errors='coerce').fillna(0)
        total = float(s.sum())
        if total <= 0:
            return 0.0
        return round(float(s.sort_values(ascending=False).head(int(topn)).sum() / total * 100), 1)

    concentracao_summary = pd.DataFrame([
        {'Indicador': '% concentração top 3 teams', 'Percentual': _topn_share(concentracao_team_share.get('TotalItems', pd.Series(dtype='float64')), 3), 'Escopo': 'TotalItems'},
        {'Indicador': '% concentração top 5 teams', 'Percentual': _topn_share(concentracao_team_share.get('TotalItems', pd.Series(dtype='float64')), 5), 'Escopo': 'TotalItems'},
        {'Indicador': '% concentração top 5 épicos', 'Percentual': _topn_share(epics.get('QtdItensFluxo', pd.Series(dtype='float64')) if not epics.empty else pd.Series(dtype='float64'), 5), 'Escopo': 'ItensFluxo'},
        {'Indicador': '% concentração top 10 épicos', 'Percentual': _topn_share(epics.get('QtdItensFluxo', pd.Series(dtype='float64')) if not epics.empty else pd.Series(dtype='float64'), 10), 'Escopo': 'ItensFluxo'},
    ])

    # Balanceamento por tipo (mix atual vs alvo parametrizável por env JSON; fallback = mix igualitário dos tipos presentes).
    tipo_counts = group_count(df, ['Tipo'], 'WorkItems') if not df.empty else pd.DataFrame(columns=['Tipo', 'WorkItems'])
    target_mix_raw = os.getenv('FLOW_PMO_PORTFOLIO_TYPE_TARGET_MIX', '').strip()
    target_mix_cfg = {}
    if target_mix_raw:
        try:
            parsed_mix = json.loads(target_mix_raw)
            if isinstance(parsed_mix, dict):
                target_mix_cfg = {str(k).strip(): float(v) for k, v in parsed_mix.items() if str(k).strip()}
        except Exception:
            target_mix_cfg = {}
    if not tipo_counts.empty:
        tipo_balanceamento = tipo_counts.copy()
        tipo_balanceamento['% Atual'] = (tipo_balanceamento['WorkItems'] / tipo_balanceamento['WorkItems'].sum() * 100).round(1)
        present_tipos = tipo_balanceamento['Tipo'].astype(str).tolist()
        if target_mix_cfg:
            tipo_balanceamento['% Alvo'] = tipo_balanceamento['Tipo'].map(lambda t: float(target_mix_cfg.get(str(t), 0.0))).fillna(0.0)
            total_target = float(tipo_balanceamento['% Alvo'].sum())
            if total_target > 0:
                tipo_balanceamento['% Alvo'] = (tipo_balanceamento['% Alvo'] / total_target * 100).round(1)
        else:
            eq_target = round(100.0 / max(1, len(present_tipos)), 1)
            tipo_balanceamento['% Alvo'] = eq_target
        tipo_balanceamento['Desvio (pp)'] = (tipo_balanceamento['% Atual'] - tipo_balanceamento['% Alvo']).round(1)
        tipo_balanceamento['Desvio Abs (pp)'] = tipo_balanceamento['Desvio (pp)'].abs().round(1)
        tipo_balanceamento = tipo_balanceamento.sort_values(['Desvio Abs (pp)', 'WorkItems'], ascending=[False, False], ignore_index=True)
    else:
        tipo_balanceamento = pd.DataFrame(columns=['Tipo', 'WorkItems', '% Atual', '% Alvo', 'Desvio (pp)', 'Desvio Abs (pp)'])

    # ── Fase 3: Lead Time ──────────────────────────────────────────────────
    _df_resolved = df[(df['ResolvedAt'].notna()) & (df['CreatedAt'].notna())].copy()
    if not _df_resolved.empty:
        _df_resolved['LeadTimeDias'] = (
            (_df_resolved['ResolvedAt'] - _df_resolved['CreatedAt'])
            .dt.total_seconds() / 86400
        ).round(1)
        _df_resolved = _df_resolved[_df_resolved['LeadTimeDias'] >= 0]
    if not _df_resolved.empty:
        _lt = _df_resolved['LeadTimeDias']
        lead_time_p50 = round(float(_lt.quantile(0.50)), 1)
        lead_time_p85 = round(float(_lt.quantile(0.85)), 1)
        lead_time_count = len(_df_resolved)
        lead_time_por_tipo = (
            _df_resolved.groupby('Tipo', dropna=False)['LeadTimeDias']
            .agg(Count='count',
                 P50=lambda x: round(float(x.quantile(0.50)), 1),
                 P85=lambda x: round(float(x.quantile(0.85)), 1))
            .reset_index()
            .sort_values('P50', ignore_index=True)
        )
        lead_time_por_team = (
            _df_resolved.groupby('TeamDisplay', dropna=False)['LeadTimeDias']
            .agg(Count='count',
                 P50=lambda x: round(float(x.quantile(0.50)), 1),
                 P85=lambda x: round(float(x.quantile(0.85)), 1))
            .reset_index()
            .sort_values('P50', ignore_index=True)
        )
        _lt_cols = ['ID', 'Titulo', 'Tipo', 'TeamDisplay', 'Status', 'LeadTimeDias']
        lead_time_distribution = _df_resolved[[c for c in _lt_cols if c in _df_resolved.columns]].copy()
    else:
        lead_time_p50 = None
        lead_time_p85 = None
        lead_time_count = 0
        lead_time_por_tipo = pd.DataFrame(columns=['Tipo', 'Count', 'P50', 'P85'])
        lead_time_por_team = pd.DataFrame(columns=['TeamDisplay', 'Count', 'P50', 'P85'])
        lead_time_distribution = pd.DataFrame()

    # ── Fase 3: Throughput ─────────────────────────────────────────────────
    if not _df_resolved.empty:
        _df_tp = _df_resolved.copy()
        _df_tp['SemanaResolucao'] = _df_tp['ResolvedAt'].dt.to_period('W').apply(lambda p: p.start_time)
        throughput_semanal = (
            _df_tp.groupby('SemanaResolucao', dropna=True).size().reset_index(name='Itens')
            .sort_values('SemanaResolucao', ignore_index=True)
        )
        throughput_semanal['SemanaResolucao'] = throughput_semanal['SemanaResolucao'].astype(str)
        throughput_weekly_avg = round(float(throughput_semanal['Itens'].mean()), 1) if not throughput_semanal.empty else 0.0
        _df_tp['MesResolucao'] = _df_tp['ResolvedAt'].dt.to_period('M').apply(lambda p: p.start_time)
        throughput_mensal = (
            _df_tp.groupby('MesResolucao', dropna=True).size().reset_index(name='Itens')
            .sort_values('MesResolucao', ignore_index=True)
        )
        throughput_mensal['MesResolucao'] = throughput_mensal['MesResolucao'].astype(str)
        throughput_monthly_avg = round(float(throughput_mensal['Itens'].mean()), 1) if not throughput_mensal.empty else 0.0
    else:
        throughput_semanal = pd.DataFrame(columns=['SemanaResolucao', 'Itens'])
        throughput_mensal = pd.DataFrame(columns=['MesResolucao', 'Itens'])
        throughput_weekly_avg = 0.0
        throughput_monthly_avg = 0.0

    # ── Fase 3: Alinhamento Estratégico ────────────────────────────────────
    _has_tema = df['StrategicTheme'].ne('').any()
    if _has_tema:
        itens_com_tema = int(df['StrategicTheme'].ne('').sum())
        pct_com_tema = round(itens_com_tema / len(df) * 100, 1) if len(df) else 0.0
        _df_tema = df[df['StrategicTheme'].ne('')].copy()
        tema_distribuicao = (
            _df_tema.groupby('StrategicTheme', dropna=False).size().reset_index(name='Itens')
            .sort_values('Itens', ascending=False, ignore_index=True)
        )
        tema_team_heatmap = (
            _df_tema.groupby(['TeamDisplay', 'StrategicTheme'], dropna=False)
            .size().reset_index(name='Itens')
        ) if 'TeamDisplay' in _df_tema.columns else pd.DataFrame(columns=['TeamDisplay', 'StrategicTheme', 'Itens'])
        tema_status_dist = (
            _df_tema.groupby(['StrategicTheme', 'StatusCategoria'], dropna=False)
            .size().reset_index(name='Itens')
        ) if 'StatusCategoria' in _df_tema.columns else pd.DataFrame(columns=['StrategicTheme', 'StatusCategoria', 'Itens'])
    else:
        itens_com_tema = 0
        pct_com_tema = 0.0
        tema_distribuicao = pd.DataFrame(columns=['StrategicTheme', 'Itens'])
        tema_team_heatmap = pd.DataFrame(columns=['TeamDisplay', 'StrategicTheme', 'Itens'])
        tema_status_dist = pd.DataFrame(columns=['StrategicTheme', 'StatusCategoria', 'Itens'])

    # ── Fase 3: Riscos ─────────────────────────────────────────────────────
    _has_risk = df['Risk'].ne('').any()
    if _has_risk:
        itens_com_risco = int(df['Risk'].ne('').sum())
        pct_com_risco = round(itens_com_risco / len(df) * 100, 1) if len(df) else 0.0
        _df_rsk = df[df['Risk'].ne('')].copy()
        risk_distribuicao = (
            _df_rsk.groupby('Risk', dropna=False).size().reset_index(name='Itens')
            .sort_values('Itens', ascending=False, ignore_index=True)
        )
        risk_por_tipo = (
            _df_rsk.groupby(['Risk', 'Tipo'], dropna=False).size().reset_index(name='Itens')
        )
        risk_por_team = (
            _df_rsk.groupby(['TeamDisplay', 'Risk'], dropna=False).size().reset_index(name='Itens')
        ) if 'TeamDisplay' in _df_rsk.columns else pd.DataFrame(columns=['TeamDisplay', 'Risk', 'Itens'])
        risk_aging = (
            _df_rsk.groupby('Risk', dropna=False)['AgingDiasSemAlteracao']
            .agg(Itens='count', AgingMediano=lambda x: int(round(x.median(), 0)))
            .reset_index()
            .sort_values('AgingMediano', ascending=False, ignore_index=True)
        ) if 'AgingDiasSemAlteracao' in _df_rsk.columns else pd.DataFrame(columns=['Risk', 'Itens', 'AgingMediano'])
    else:
        itens_com_risco = 0
        pct_com_risco = 0.0
        risk_distribuicao = pd.DataFrame(columns=['Risk', 'Itens'])
        risk_por_tipo = pd.DataFrame(columns=['Risk', 'Tipo', 'Itens'])
        risk_por_team = pd.DataFrame(columns=['TeamDisplay', 'Risk', 'Itens'])
        risk_aging = pd.DataFrame(columns=['Risk', 'Itens', 'AgingMediano'])

    items_base_cols = [
        'ID', 'Projeto', 'TeamOriginal', 'TeamDisplay', 'Tipo', 'TipoNorm', 'Status', 'StatusNorm',
        'StatusCategoria', 'AgingDiasSemAlteracao', 'IsOpen', 'IsBacklog', 'IsInProgress', 'IsFeature',
        'ParentID', 'EffortTShirtSize'
    ]
    if 'DueDate' in df.columns:
        items_base_cols.append('DueDate')
    items_base = df[items_base_cols].copy()

    return {
        'updated_at': updated_at_label,
        'metrics': {
            'epics_sem_features': int(len(epics_sem_features)),
            'features_sem_epico': int(len(features_sem_epico)),
            'features_sem_filhos': int(len(features_sem_filhos)),
            'features_sem_mov_15': int(len(features_sem_mov_15)),
            'features_sem_mov_30': int(len(features_sem_mov_30)),
            'hist_tasks_sem_feature': int(len(story_task_sem_feature)),
            'total_epicos': int(len(epics)),
            'total_features': int(len(features)),
            'team_original_preenchido': team_original_preenchido,
            'total_itens': total_itens,
            'features_com_epico': features_com_epico,
            'features_com_effort': features_com_effort,
            'itens_status_nao_mapeado': itens_status_nao_mapeado,
            'pct_wip': round((total_wip_items / total_itens * 100), 1) if total_itens else 0.0,
            'pct_backlog_parado_15': round((backlog_parado_15 / total_backlog_open * 100), 1) if total_backlog_open else 0.0,
            'pct_backlog_parado_30': round((backlog_parado_30 / total_backlog_open * 100), 1) if total_backlog_open else 0.0,
            'pct_features_com_filhos': round((len(features_com_filhos) / len(features) * 100), 1) if len(features) else 0.0,
            'pct_epicos_com_itens_fluxo': round((len(epics_com_itens_fluxo) / len(epics) * 100), 1) if len(epics) else 0.0,
            'pct_storytask_sem_feature_tatico': float(storytask_sem_feature_tatico_metric.get('Percentual', 0.0)),
            'pct_storytask_orfaos': float(storytask_orfaos_metric.get('Percentual', 0.0)),
            'lead_time_p50': lead_time_p50,
            'lead_time_p85': lead_time_p85,
            'lead_time_count': lead_time_count,
            'throughput_weekly_avg': throughput_weekly_avg,
            'throughput_monthly_avg': throughput_monthly_avg,
            'itens_com_tema_estrategico': itens_com_tema,
            'pct_com_tema_estrategico': pct_com_tema,
            'itens_com_risco': itens_com_risco,
            'pct_com_risco': pct_com_risco,
        },
        'groups': {
            'epicos_por_team_status': epicos_por_team_status,
            'features_por_team_status': features_por_team_status,
            'epicos_por_complexidade': epicos_por_complexidade,
            'features_por_complexidade': features_por_complexidade,
            'epicos_fluxo_etapas': epicos_fluxo_etapas,
            'epicos_por_team_total': epicos_por_team_total,
            'features_por_team_total': features_por_team_total,
            'pendencias_q_por_time': pendencias_q_por_time,
            'pendencias_breakdown': pendencias_breakdown,
            'pendencias_detalhe': pendencias_detalhe,
            'aging_us_20': aging_us_20,
            'aging_features_40': aging_features_40,
            'aging_us_comp_20': aging_us_comp_20,
            'aging_features_comp_40': aging_features_comp_40,
            'aging_buckets_por_team': aging_buckets_por_team,
            'aging_por_tipo': aging_por_tipo,
            'aging_por_projeto': aging_por_projeto,
            'flow_health_summary': flow_health_summary,
            'flow_health_por_team': flow_health_por_team,
            'portfolio_health_scorecard': portfolio_health_scorecard,
            'portfolio_health_dimension_summary': portfolio_health_dimension_summary,
            'flow_distribution_by_type': flow_distribution_by_type,
            'flow_distribution_by_status': flow_distribution_by_status,
            'flow_distribution_by_team': flow_distribution_by_team,
            'stage_load_summary': stage_load_summary,
            'stage_load_detail': stage_load_detail,
            'stage_limit_alerts': stage_limit_alerts,
            'decision_queue_aging': decision_queue_aging,
            'decision_queue_summary': decision_queue_summary,
            'data_freshness_por_team_statuscat': data_freshness_por_team_statuscat,
            'status_categoria_por_team': status_categoria_por_team,
            'status_ranking_por_team': status_ranking_por_team,
            'status_original_top': status_original_top,
            'workflow_conformance_por_team': workflow_conformance_por_team,
            'status_fora_workflow_top': status_fora_workflow_top,
            'heatmap_team_status': heatmap_team_status,
            'effort_features_por_team': effort_features_por_team,
            'features_sem_effort_por_team': features_sem_effort_por_team,
            'effort_aging_summary': effort_aging_summary,
            'effort_stale_summary': effort_stale_summary,
            'quality_por_team': quality_por_team,
            'estrutura_cobertura_por_team': estrutura_cobertura_por_team,
            'estrutura_cobertura_summary': estrutura_cobertura_summary,
            'concentracao_team_share': concentracao_team_share,
            'concentracao_epico_share': concentracao_epico_share,
            'concentracao_summary': concentracao_summary,
            'tipo_balanceamento': tipo_balanceamento,
            'items_base': items_base,
            'hist_tasks_sem_feature_por_team': hist_tasks_sem_feature_por_team,
            'executive_tiles': executive_tiles,
            'quality_summary': quality_summary,
            'top_epicos_volume': top_epicos_volume,
            'top_epicos_aging': top_epicos_aging,
            'epicos_detalhe': epicos_detalhe,
            'features_detalhe': features_detalhe,
            'portfolio_alerts_detail': portfolio_alerts_detail,
            'portfolio_alerts_indicator_summary': portfolio_alerts_indicator_summary,
            'portfolio_alerts_severity_summary': portfolio_alerts_severity_summary,
            'portfolio_alerts_by_team': portfolio_alerts_by_team,
            'portfolio_alerts_by_project': portfolio_alerts_by_project,
            'portfolio_alert_kpis': portfolio_alert_kpis,
            'portfolio_extra_onepage_summary': portfolio_extra_onepage_summary,
            'portfolio_technical_readiness_notes': portfolio_technical_readiness_notes,
            'portfolio_technical_epic_summary': portfolio_technical_epic_summary,
            'portfolio_technical_items_catalog': technical_items_catalog,
            'has_us_items': has_us_items,
            'lead_time_por_tipo': lead_time_por_tipo,
            'lead_time_por_team': lead_time_por_team,
            'lead_time_distribution': lead_time_distribution,
            'throughput_semanal': throughput_semanal,
            'throughput_mensal': throughput_mensal,
            'tema_distribuicao': tema_distribuicao,
            'tema_team_heatmap': tema_team_heatmap,
            'tema_status_dist': tema_status_dist,
            'risk_distribuicao': risk_distribuicao,
            'risk_por_tipo': risk_por_tipo,
            'risk_por_team': risk_por_team,
            'risk_aging': risk_aging,
            'due_date_performance': due_date_performance_df,
        },
    }


def find_latest_portfolio_csv():
    explicit_csv = os.getenv('FLOW_PMO_PORTFOLIO_CSV_FILE', '').strip()
    if explicit_csv:
        candidate = explicit_csv if os.path.isabs(explicit_csv) else os.path.join(os.path.dirname(__file__), explicit_csv)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        raise RuntimeError(f'FLOW_PMO_PORTFOLIO_CSV_FILE aponta para arquivo inexistente: {candidate}')

    csv_url = os.getenv('FLOW_PMO_PORTFOLIO_CSV_URL', '').strip()
    if csv_url:
        try:
            return _download_portfolio_csv_from_url(csv_url)
        except Exception as _url_exc:
            import warnings
            warnings.warn(
                f"[dashboard_full] Falha ao baixar CSV de portfólio de FLOW_PMO_PORTFOLIO_CSV_URL ({_url_exc}). "
                "Tentando arquivo local como fallback.",
                RuntimeWarning,
                stacklevel=2,
            )

    candidates = []
    preferred_latest_name = f'{PORTFOLIO_CSV_PREFIX}latest{PORTFOLIO_CSV_SUFFIX}'.lower()
    for folder in DATA_FOLDERS:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            if name.startswith(PORTFOLIO_CSV_PREFIX) and name.endswith(PORTFOLIO_CSV_SUFFIX):
                candidates.append(os.path.join(folder, name))
    if not candidates:
        return None
    preferred_matches = [p for p in candidates if os.path.basename(p).lower() == preferred_latest_name]
    if preferred_matches:
        return max(preferred_matches, key=os.path.getctime)
    return max(candidates, key=os.path.getctime)


def build_portfolio_snapshot_from_csv():
    csv_file = find_latest_portfolio_csv()
    if not csv_file:
        raise RuntimeError(
            f'CSV de portfólio não encontrado. Configure FLOW_PMO_PORTFOLIO_CSV_URL ou FLOW_PMO_PORTFOLIO_CSV_FILE, '
            f'ou gere um arquivo {PORTFOLIO_CSV_PREFIX}YYYYMMDD{PORTFOLIO_CSV_SUFFIX} '
            f'em uma destas pastas: {", ".join(DATA_FOLDERS or [DATA_FOLDER])}.'
        )

    df = pd.read_csv(csv_file)
    required_cols = {'ID', 'Titulo', 'Projeto', 'Tipo', 'Status', 'ParentID', 'Link', 'UpdatedAt', 'StatusChangedAt'}
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise RuntimeError(f'CSV de portfólio inválido ({os.path.basename(csv_file)}). Colunas ausentes: {", ".join(missing)}')

    updated_at_label = datetime.fromtimestamp(os.path.getctime(csv_file)).strftime('%Y-%m-%d %H:%M')
    snapshot = compute_portfolio_snapshot(df, updated_at_label)
    snapshot['source_file'] = csv_file
    return snapshot


def get_portfolio_snapshot():
    now = datetime.now()
    cached_at = PORTFOLIO_CACHE.get('fetched_at')
    if cached_at and (now - cached_at) <= PORTFOLIO_CACHE_TTL and PORTFOLIO_CACHE.get('data') is not None and PORTFOLIO_CACHE.get('df') is not None:
        try:
            latest_csv = find_latest_portfolio_csv()
            if latest_csv:
                latest_abs = os.path.abspath(latest_csv)
                cached_abs = os.path.abspath(str(PORTFOLIO_CACHE.get('source_file') or ''))
                latest_mtime = os.path.getmtime(latest_csv)
                cached_mtime = PORTFOLIO_CACHE.get('source_mtime')
                if latest_abs == cached_abs and cached_mtime is not None and float(latest_mtime) == float(cached_mtime):
                    return PORTFOLIO_CACHE.get('data'), PORTFOLIO_CACHE.get('df'), PORTFOLIO_CACHE.get('error')
            else:
                return PORTFOLIO_CACHE.get('data'), PORTFOLIO_CACHE.get('df'), PORTFOLIO_CACHE.get('error')
        except Exception:
            return PORTFOLIO_CACHE.get('data'), PORTFOLIO_CACHE.get('df'), PORTFOLIO_CACHE.get('error')
    try:
        csv_file = find_latest_portfolio_csv()
        if not csv_file:
            raise RuntimeError(
                f'CSV de portfólio não encontrado. Configure FLOW_PMO_PORTFOLIO_CSV_URL ou FLOW_PMO_PORTFOLIO_CSV_FILE, '
                f'ou gere um arquivo {PORTFOLIO_CSV_PREFIX}YYYYMMDD{PORTFOLIO_CSV_SUFFIX} '
                f'em uma destas pastas: {", ".join(DATA_FOLDERS or [DATA_FOLDER])}.'
            )

        df = pd.read_csv(csv_file)
        if 'DueDate' not in df.columns:
            df['DueDate'] = pd.NaT
        df['DueDate'] = pd.to_datetime(df['DueDate'], errors='coerce')
        if 'Prioridade' not in df.columns:
            df['Prioridade'] = ''

        updated_at_label = datetime.fromtimestamp(os.path.getctime(csv_file)).strftime('%Y-%m-%d %H:%M')
        snapshot = compute_portfolio_snapshot(df, updated_at_label)
        snapshot['source_file'] = csv_file

        PORTFOLIO_CACHE['fetched_at'] = now
        PORTFOLIO_CACHE['data'] = snapshot
        PORTFOLIO_CACHE['df'] = df
        PORTFOLIO_CACHE['error'] = None
        PORTFOLIO_CACHE['source_file'] = csv_file
        PORTFOLIO_CACHE['source_mtime'] = os.path.getmtime(csv_file)
        return snapshot, df, None
    except Exception as exc:
        PORTFOLIO_CACHE['fetched_at'] = now
        PORTFOLIO_CACHE['data'] = None
        PORTFOLIO_CACHE['df'] = None
        PORTFOLIO_CACHE['error'] = str(exc)
        PORTFOLIO_CACHE['source_file'] = None
        PORTFOLIO_CACHE['source_mtime'] = None
        return None, None, str(exc)


def _canonical_gmud_service_team(value):
    text = str(value or '').strip()
    if not text:
        return ''
    aliases = {
        'W1NNR': 'W1NNR',
        'W1NNER': 'W1NNR',
        'S1NC': 'S1NC',
        'SYNC': 'S1NC',
        'BF': 'BF',
        'BEFINANCE': 'BF',
        'DT': 'DT',
        'DATA&ANALYTICS': 'DT',
        'DATA ANALYTICS': 'DT',
        'TECH W1NNER': 'W1NNR',
        'SQUAD | W1NNER': 'W1NNR',
        'TECH S1NC': 'S1NC',
        'SQUAD | S1NC': 'S1NC',
        'TECH BEFINANCE': 'BF',
        'TECH DATA': 'DT',
    }
    norm = normalize_text(text).upper()
    return aliases.get(norm, text.upper())


def _gmud_kind_spec(kind: str) -> dict:
    kind_norm = str(kind or '').strip().lower()
    if kind_norm == 'index':
        return {
            'kind': 'index',
            'env_file': 'FLOW_PMO_GMUD_INDEX_FILE',
            'env_url': 'FLOW_PMO_GMUD_INDEX_URL',
            'preferred_latest_names': {'gmud-coverage-index-latest.csv'},
            'prefix': 'gmud-coverage-index-',
            'required_cols': {'Escopo', 'Valor', 'ItensElegiveis', 'ItensComGMUD', 'IndiceCoberturaGMUDPct'},
        }
    if kind_norm == 'weekly':
        return {
            'kind': 'weekly',
            'env_file': 'FLOW_PMO_GMUD_WEEKLY_FILE',
            'env_url': 'FLOW_PMO_GMUD_WEEKLY_URL',
            'preferred_latest_names': {'gmud-coverage-weekly-latest.csv'},
            'prefix': 'gmud-coverage-weekly-',
            'required_cols': {'Semana', 'ItensElegiveis', 'ItensComGMUD', 'IndiceCoberturaGMUDPct'},
        }
    return {
        'kind': 'items',
        'env_file': 'FLOW_PMO_GMUD_ITEMS_FILE',
        'env_url': 'FLOW_PMO_GMUD_ITEMS_URL',
        'preferred_latest_names': {'gmud-coverage-items-latest.csv'},
        'prefix': 'gmud-coverage-items-',
        'required_cols': {'ItemKey', 'Projeto', 'DeliveryBucket', 'HasGMUD', 'EligibleForGMUD'},
    }


def _replace_url_filename(url: str, new_filename: str) -> str:
    parsed = urllib.parse.urlparse(str(url or '').strip())
    if not parsed.scheme or not parsed.netloc or not new_filename:
        return ''
    current_path = parsed.path or ''
    current_dir = posixpath.dirname(current_path)
    if current_dir in {'', '.'}:
        new_path = f'/{new_filename}' if current_path.startswith('/') else new_filename
    else:
        new_path = posixpath.join(current_dir, new_filename)
    return urllib.parse.urlunparse(parsed._replace(path=new_path))


def _iter_gmud_companion_urls(kind: str):
    spec = _gmud_kind_spec(kind)
    latest_name = next(iter(spec['preferred_latest_names']))
    seed_urls = []
    for env_name in (
        'FLOW_PMO_PORTFOLIO_CSV_URL',
        'FLOW_PMO_MODEL_URL',
        'FLOW_PMO_PROCESS_MINING_REPORT_URL',
        'FLOW_PMO_DASHBOARD_OUTPUT_URL',
        'FLOW_PMO_BOTTLENECK_CSV_URL',
    ):
        value = os.getenv(env_name, '').strip()
        if value:
            seed_urls.append(value)
    seed_urls.extend(_load_downstream_url_map().values())
    seed_urls.extend(_load_bottleneck_url_map().values())

    seen = set()
    for seed_url in seed_urls:
        companion_url = _replace_url_filename(seed_url, latest_name)
        if not companion_url:
            continue
        cache_key = companion_url.strip().lower()
        if cache_key in seen:
            continue
        seen.add(cache_key)
        yield companion_url


def find_latest_gmud_csv(kind: str):
    spec = _gmud_kind_spec(kind)
    explicit_file = _sanitize_os_path(os.getenv(spec['env_file'], ''))
    if explicit_file:
        candidate = explicit_file if os.path.isabs(explicit_file) else os.path.join(os.path.dirname(__file__), explicit_file)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        raise RuntimeError(f"{spec['env_file']} aponta para arquivo inexistente: {candidate}")

    csv_url = os.getenv(spec['env_url'], '').strip()
    if csv_url:
        try:
            return _download_gmud_csv_from_url(csv_url, spec['kind'])
        except Exception as _url_exc:
            import warnings
            warnings.warn(
                f"[dashboard_full] Falha ao baixar GMUD CSV de {spec['env_url']} ({_url_exc}). "
                "Tentando arquivo local como fallback.",
                RuntimeWarning,
                stacklevel=2,
            )

    candidates = []
    preferred = {name.lower() for name in spec['preferred_latest_names']}
    for folder in _iter_local_data_folders():
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low = str(name or '').strip().lower()
            if low in preferred or (low.startswith(spec['prefix']) and low.endswith('.csv')):
                candidates.append(os.path.join(folder, name))
    candidates = [path for path in candidates if os.path.isfile(path)]
    if candidates:
        preferred_matches = [path for path in candidates if os.path.basename(path).lower() in preferred]
        if preferred_matches:
            return max(preferred_matches, key=os.path.getctime)
        return max(candidates, key=os.path.getctime)

    for inferred_url in _iter_gmud_companion_urls(spec['kind']):
        try:
            return _download_gmud_csv_from_url(inferred_url, spec['kind'])
        except Exception:
            continue
    return None


def _gmud_bool_series(series):
    if series is None:
        return pd.Series(dtype=bool)
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    normalized = series.fillna('').astype(str).str.strip().str.lower()
    return normalized.isin({'1', 'true', 'yes', 'sim', 'on'})


def _gmud_link_evidence_series(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series(dtype=bool)

    index = df.index
    evidence = pd.Series(False, index=index, dtype=bool)
    url_pattern = re.compile(r'https?://', re.IGNORECASE)
    chg_pattern = re.compile(r'\bchg-\d+\b', re.IGNORECASE)

    for col in ['CHGLink', 'GmudLink', 'GMUDLink', 'ChangeLink']:
        if col not in df.columns:
            continue
        values = df[col].fillna('').astype(str).str.strip()
        evidence |= values.ne('')

    for col in ['link', 'Link']:
        if col not in df.columns:
            continue
        values = df[col].fillna('').astype(str).str.strip()
        evidence |= values.apply(lambda value: bool(value) and (bool(chg_pattern.search(value)) or bool(url_pattern.search(value))))

    return evidence


def _prepare_gmud_snapshot_df(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    kind_norm = str(kind or '').strip().lower()
    if kind_norm == 'index':
        numeric_cols = [
            'ItensElegiveis', 'ItensComGMUD', 'ItensSemGMUD',
            'IndiceCoberturaGMUDPct', 'ItensComEvidenciaExplicita',
            'ItensComEvidenciaTextoOuComentario', 'ItensComEvidenciaComentario',
            'CoberturaExplicitaPct', 'CoberturaTextoOuComentarioPct', 'CoberturaComentarioPct',
        ]
        for col in numeric_cols:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors='coerce')
        for col in ['Escopo', 'Valor']:
            if col not in out.columns:
                out[col] = ''
            out[col] = out[col].fillna('').astype(str)
        return out

    if kind_norm == 'weekly':
        if 'Semana' in out.columns:
            out['Semana'] = pd.to_datetime(out['Semana'], errors='coerce')
        for col in ['Escopo', 'Valor']:
            if col not in out.columns:
                out[col] = ''
            out[col] = out[col].fillna('').astype(str)
        numeric_cols = [col for col in out.columns if col not in {'Semana', 'Escopo', 'Valor'}]
        for col in numeric_cols:
            out[col] = pd.to_numeric(out[col], errors='coerce')
        return out

    for dcol in ['ReferenceDate', 'DoneDate', 'ReadyForProductionDate', 'StatusChangedAt']:
        if dcol in out.columns:
            out[dcol] = pd.to_datetime(out[dcol], errors='coerce')
        else:
            out[dcol] = pd.NaT
    for col in ['ServiceTeam', 'Projeto', 'ItemKey', 'Titulo', 'DeliveryBucket', 'PrimaryEvidence', 'PrimaryEvidenceBucket', 'MatchedCHGKeys', 'Source', 'CHGLink', 'GMUDLink', 'GmudLink', 'ChangeLink', 'Link', 'link']:
        if col not in out.columns:
            out[col] = ''
        out[col] = out[col].fillna('').astype(str)
    if 'ServiceTeam' in out.columns:
        out['ServiceTeam'] = out['ServiceTeam'].apply(_canonical_gmud_service_team)
    if out['ServiceTeam'].astype(str).str.strip().eq('').any():
        fallback_project = out.get('Projeto', pd.Series('', index=out.index)).fillna('').astype(str)
        out.loc[out['ServiceTeam'].astype(str).str.strip().eq(''), 'ServiceTeam'] = fallback_project.apply(_canonical_gmud_service_team)
    for col in ['EligibleForGMUD', 'HasGMUD', 'UsedCommentEvidence']:
        if col not in out.columns:
            out[col] = False
        out[col] = _gmud_bool_series(out[col])
    link_evidence = _gmud_link_evidence_series(out)
    out['HasGMUD'] = out['HasGMUD'] | link_evidence
    missing_bucket_mask = out['PrimaryEvidenceBucket'].astype(str).str.strip().eq('')
    out.loc[link_evidence & missing_bucket_mask, 'PrimaryEvidenceBucket'] = 'Explicita'
    missing_evidence_mask = out['PrimaryEvidence'].astype(str).str.strip().eq('')
    out.loc[link_evidence & missing_evidence_mask, 'PrimaryEvidence'] = 'Link no campo link'
    if 'MatchedCommentSignalCount' in out.columns:
        out['MatchedCommentSignalCount'] = pd.to_numeric(out['MatchedCommentSignalCount'], errors='coerce').fillna(0)
    return out


def get_gmud_snapshot(kind: str = 'items'):
    spec = _gmud_kind_spec(kind)
    cache_entry = GMUD_CACHE.get(spec['kind'], {})
    now = datetime.now()
    cached_at = cache_entry.get('fetched_at')

    if cached_at and (now - cached_at) <= GMUD_CACHE_TTL and cache_entry.get('df') is not None:
        try:
            latest_csv = find_latest_gmud_csv(spec['kind'])
            if latest_csv:
                latest_abs = os.path.abspath(latest_csv)
                cached_abs = os.path.abspath(str(cache_entry.get('source_file') or ''))
                latest_mtime = os.path.getmtime(latest_csv)
                cached_mtime = cache_entry.get('source_mtime')
                if latest_abs == cached_abs and cached_mtime is not None and float(latest_mtime) == float(cached_mtime):
                    return cache_entry.get('df'), cache_entry.get('error')
            else:
                return cache_entry.get('df'), cache_entry.get('error')
        except Exception:
            return cache_entry.get('df'), cache_entry.get('error')

    try:
        csv_file = find_latest_gmud_csv(spec['kind'])
        if not csv_file:
            raise RuntimeError(
                f"CSV GMUD ({spec['kind']}) não encontrado. Configure {spec['env_file']} ou {spec['env_url']}, "
                f"ou publique um alias latest nas pastas: {', '.join(DATA_FOLDERS or [DATA_FOLDER])}. "
                "Se os arquivos GMUD estiverem no mesmo blob/base pública dos demais artefatos latest, "
                "o dashboard tenta descobrir automaticamente os nomes gmud-coverage-*-latest.csv."
            )
        df = pd.read_csv(csv_file)
        missing = [col for col in spec['required_cols'] if col not in df.columns]
        if missing:
            raise RuntimeError(
                f"CSV GMUD inválido ({os.path.basename(csv_file)}). Colunas ausentes: {', '.join(missing)}"
            )
        df = _prepare_gmud_snapshot_df(df, spec['kind'])
        GMUD_CACHE[spec['kind']] = {
            'fetched_at': now,
            'df': df,
            'error': None,
            'source_file': csv_file,
            'source_mtime': os.path.getmtime(csv_file),
        }
        return df, None
    except Exception as exc:
        GMUD_CACHE[spec['kind']] = {
            'fetched_at': now,
            'df': pd.DataFrame(),
            'error': str(exc),
            'source_file': None,
            'source_mtime': None,
        }
        return pd.DataFrame(), str(exc)


def _gmud_scope_mask(df_source: pd.DataFrame, projeto=None) -> pd.Series:
    if df_source is None or df_source.empty:
        return pd.Series(dtype=bool)
    mask = pd.Series(True, index=df_source.index, dtype=bool)
    projeto = normalize_project_filter_value(projeto)
    if not projeto or projeto == PROJECT_FILTER_ALL_VALUE:
        return mask
    target = _canonical_gmud_service_team(projeto)
    service_series = df_source.get('ServiceTeam', df_source.get('Projeto', pd.Series('', index=df_source.index))).fillna('').astype(str)
    mask &= service_series.apply(_canonical_gmud_service_team) == target
    return mask


def _capex_local_file_matches(name: str, kind: str) -> bool:
    low = str(name or '').strip().lower()
    if not (low.startswith('capex') and low.endswith('.csv')):
        return False
    if kind == 'summary':
        return ('mensal' in low) or ('summary' in low)
    return 'raw' in low


def _capex_required_columns(kind: str) -> set[str]:
    if kind == 'summary':
        return {'MesCompetencia', 'ID do Projeto', 'Colaborador', 'Horas', 'Projeto Jira'}
    return {
        'MesCompetencia',
        'ID do Projeto',
        'Colaborador',
        'Data do Apontamento das Horas',
        'Horas',
        'Issue Key',
        'Projeto Jira',
        'Origem Horas',
    }


def _find_latest_capex_csv(kind: str = 'raw'):
    kind = 'summary' if str(kind or '').strip().lower() == 'summary' else 'raw'
    env_suffix = 'SUMMARY' if kind == 'summary' else 'RAW'
    explicit_file = os.getenv(f'FLOW_PMO_CAPEX_{env_suffix}_FILE', '').strip()
    if explicit_file:
        candidate = explicit_file if os.path.isabs(explicit_file) else os.path.join(os.path.dirname(__file__), explicit_file)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        raise RuntimeError(f'FLOW_PMO_CAPEX_{env_suffix}_FILE aponta para arquivo inexistente: {candidate}')

    explicit_url = os.getenv(f'FLOW_PMO_CAPEX_{env_suffix}_URL', '').strip()
    if explicit_url:
        try:
            return _download_capex_csv_from_url(explicit_url, kind)
        except Exception as _url_exc:
            import warnings
            warnings.warn(
                f"[dashboard_full] Falha ao baixar CAPEX CSV de FLOW_PMO_CAPEX_{env_suffix}_URL ({_url_exc}). "
                "Tentando arquivo local como fallback.",
                RuntimeWarning,
                stacklevel=2,
            )

    candidates = []
    latest_candidates = []
    for folder in DATA_FOLDERS:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            if not _capex_local_file_matches(name, kind):
                continue
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            candidates.append(path)
            if 'latest' in str(name).lower():
                latest_candidates.append(path)

    if latest_candidates:
        return max(latest_candidates, key=os.path.getctime)
    if candidates:
        return max(candidates, key=os.path.getctime)
    return None


def _load_capex_csv(kind: str = 'raw') -> tuple[pd.DataFrame, str | None]:
    csv_file = _find_latest_capex_csv(kind)
    if not csv_file:
        return pd.DataFrame(), None

    df = pd.read_csv(csv_file)
    missing = [col for col in _capex_required_columns(kind) if col not in df.columns]
    if missing:
        raise RuntimeError(
            f'CSV CAPEX {kind} inválido ({os.path.basename(csv_file)}). Colunas ausentes: {", ".join(missing)}'
        )
    return df, csv_file


def get_capex_snapshot(kind: str | None = None):
    now = datetime.now()
    cached_at = CAPEX_CACHE.get('fetched_at')
    if cached_at and (now - cached_at) <= CAPEX_CACHE_TTL and CAPEX_CACHE.get('raw_df') is not None:
        try:
            raw_file = _find_latest_capex_csv('raw')
            summary_file = _find_latest_capex_csv('summary')
            raw_matches = bool(
                raw_file
                and CAPEX_CACHE.get('raw_file')
                and os.path.abspath(raw_file) == os.path.abspath(str(CAPEX_CACHE.get('raw_file')))
                and CAPEX_CACHE.get('raw_mtime') is not None
                and float(os.path.getmtime(raw_file)) == float(CAPEX_CACHE.get('raw_mtime'))
            )
            summary_matches = (
                (not summary_file and not CAPEX_CACHE.get('summary_file'))
                or bool(
                    summary_file
                    and CAPEX_CACHE.get('summary_file')
                    and os.path.abspath(summary_file) == os.path.abspath(str(CAPEX_CACHE.get('summary_file')))
                    and CAPEX_CACHE.get('summary_mtime') is not None
                    and float(os.path.getmtime(summary_file)) == float(CAPEX_CACHE.get('summary_mtime'))
                )
            )
            if raw_matches and summary_matches:
                if kind == 'raw':
                    return CAPEX_CACHE.get('raw_df'), CAPEX_CACHE.get('error')
                if kind == 'summary':
                    return CAPEX_CACHE.get('summary_df'), CAPEX_CACHE.get('error')
                return CAPEX_CACHE.get('data'), CAPEX_CACHE.get('raw_df'), CAPEX_CACHE.get('summary_df'), CAPEX_CACHE.get('error')
        except Exception:
            if kind == 'raw':
                return CAPEX_CACHE.get('raw_df'), CAPEX_CACHE.get('error')
            if kind == 'summary':
                return CAPEX_CACHE.get('summary_df'), CAPEX_CACHE.get('error')
            return CAPEX_CACHE.get('data'), CAPEX_CACHE.get('raw_df'), CAPEX_CACHE.get('summary_df'), CAPEX_CACHE.get('error')

    try:
        raw_df, raw_file = _load_capex_csv('raw')
        summary_df, summary_file = _load_capex_csv('summary')
        snapshot = {
            'available': not raw_df.empty,
            'raw_file': raw_file,
            'summary_file': summary_file,
            'updated_at': datetime.fromtimestamp(os.path.getctime(raw_file)).strftime('%Y-%m-%d %H:%M') if raw_file else '',
        }
        CAPEX_CACHE['fetched_at'] = now
        CAPEX_CACHE['data'] = snapshot
        CAPEX_CACHE['raw_df'] = raw_df
        CAPEX_CACHE['summary_df'] = summary_df
        CAPEX_CACHE['error'] = None
        CAPEX_CACHE['raw_file'] = raw_file
        CAPEX_CACHE['raw_mtime'] = os.path.getmtime(raw_file) if raw_file else None
        CAPEX_CACHE['summary_file'] = summary_file
        CAPEX_CACHE['summary_mtime'] = os.path.getmtime(summary_file) if summary_file else None
        if kind == 'raw':
            return raw_df, None
        if kind == 'summary':
            return summary_df, None
        return snapshot, raw_df, summary_df, None
    except Exception as exc:
        CAPEX_CACHE['fetched_at'] = now
        CAPEX_CACHE['data'] = None
        CAPEX_CACHE['raw_df'] = None
        CAPEX_CACHE['summary_df'] = None
        CAPEX_CACHE['error'] = str(exc)
        CAPEX_CACHE['raw_file'] = None
        CAPEX_CACHE['raw_mtime'] = None
        CAPEX_CACHE['summary_file'] = None
        CAPEX_CACHE['summary_mtime'] = None
        if kind == 'raw':
            return pd.DataFrame(), str(exc)
        if kind == 'summary':
            return pd.DataFrame(), str(exc)
        return None, pd.DataFrame(), pd.DataFrame(), str(exc)


def _capex_project_key_from_team(team_value) -> str:
    raw_team = str(team_value or '').strip()
    if not raw_team:
        return ''
    direct = _canonical_pm_product_key(raw_team)
    if direct:
        return direct

    team_norm = normalize_text(raw_team)
    for candidate in ('BF', 'DT', 'S1NC', 'W1NNR'):
        for alias in portfolio_project_team_aliases(candidate):
            alias_norm = normalize_text(alias)
            if not alias_norm:
                continue
            if alias_norm in team_norm or team_norm in alias_norm:
                return _canonical_pm_product_key(candidate)
    return ''


def _build_capex_portfolio_asset_lookup(df_portfolio: pd.DataFrame) -> dict:
    if df_portfolio is None or df_portfolio.empty:
        return {}
    id_col = _pm_pick_first_column(df_portfolio, ['ID', 'ItemID'])
    title_col = _pm_pick_first_column(df_portfolio, ['Titulo', 'Title'])
    type_col = _pm_pick_first_column(df_portfolio, ['Tipo', 'ItemType'])
    team_col = _pm_pick_first_column(df_portfolio, ['Team', 'TEAM'])
    project_col = _pm_pick_first_column(df_portfolio, ['Projeto'])
    if not id_col:
        return {}

    lookup = {}
    for row in df_portfolio.to_dict(orient='records'):
        asset_id = _pm_clean_issue_key(row.get(id_col))
        if not asset_id:
            continue
        team_value = str(row.get(team_col, '') or '').strip() if team_col else ''
        lookup[asset_id] = {
            'AssetID': asset_id,
            'Descrição do Ativo': str(row.get(title_col, '') or '').strip() if title_col else '',
            'Tipo do Ativo': str(row.get(type_col, '') or '').strip() if type_col else '',
            'Portfolio Team': team_value,
            'Projeto Portfólio': str(row.get(project_col, '') or '').strip() if project_col else '',
            'Projeto PM': _capex_project_key_from_team(team_value),
        }
    return lookup


def _build_capex_person_rate_map(cost_model_snapshot: dict) -> dict:
    person_rates = {}
    if not isinstance(cost_model_snapshot, dict):
        return person_rates
    team_df = cost_model_snapshot.get('team_df', pd.DataFrame())
    if team_df is None or team_df.empty:
        return person_rates
    for row in team_df.to_dict(orient='records'):
        person = _canonical_person_name(row.get('Pessoa'))
        if not person:
            continue
        try:
            rate = float(row.get('Custo Hora Pessoa (R$)', 0) or 0)
        except Exception:
            rate = 0.0
        if rate > 0:
            person_rates[person] = rate
    return person_rates


def _build_custo_por_atividade_section(worklog_df: 'pd.DataFrame') -> 'html.Div':
    """
    Renderiza 3 gráficos de custo por categoria de atividade a partir do fact table de worklogs CAPEX.
    Usa 'Custo Real Apontado (R$)' quando disponível; cai para 'Horas' se taxas não estiverem configuradas.
    """
    if worklog_df is None or worklog_df.empty:
        return html.Div()

    df = worklog_df.copy()

    # Resolve rótulo de atividade: preferência para Normalizada → Desenvolvida → fallback
    if 'Atividade Desenvolvida Normalizada' in df.columns:
        ativ = df['Atividade Desenvolvida Normalizada'].fillna('').astype(str).str.strip()
        fallback = df.get('Atividade Desenvolvida', pd.Series([''] * len(df))).fillna('').astype(str).str.strip()
        df['_atividade'] = ativ.where(ativ.ne(''), fallback)
    else:
        df['_atividade'] = df.get('Atividade Desenvolvida', pd.Series([''] * len(df))).fillna('').astype(str).str.strip()
    df['_atividade'] = df['_atividade'].replace('', 'Sem Classificação')

    df['Custo Real Apontado (R$)'] = pd.to_numeric(df.get('Custo Real Apontado (R$)'), errors='coerce').fillna(0.0)
    df['Horas'] = pd.to_numeric(df.get('Horas'), errors='coerce').fillna(0.0)

    has_cost = df['Custo Real Apontado (R$)'].sum() > 0
    value_col = 'Custo Real Apontado (R$)' if has_cost else 'Horas'
    value_label = 'Custo (R$)' if has_cost else 'Horas'

    sem_taxa_note = []
    if not has_cost:
        sem_taxa_note = [html.P(
            'Taxas de custo não configuradas — exibindo horas. Configure FLOW_PMO_PORTFOLIO_ROLE_SALARY_MAP ou FLOW_PMO_PM_COST_PER_HOUR_MAP para habilitar custo monetário.',
            style={'color': '#8a6d3b', 'fontSize': '13px', 'marginBottom': '8px'}
        )]

    # --- Agrupamento por atividade ---
    by_activity = (
        df.groupby('_atividade', dropna=False)
        .agg(**{value_label: (value_col, 'sum'), 'Horas': ('Horas', 'sum')})
        .reset_index()
        .rename(columns={'_atividade': 'Atividade'})
        .sort_values(value_label, ascending=False)
    )

    def _fmt_brl(v):
        try:
            return f'R$ {v:,.0f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        except Exception:
            return str(v)

    # --- Gráfico 1: Barras por atividade ---
    fig_bar = px.bar(
        by_activity,
        x='Atividade',
        y=value_label,
        title='Custo total por categoria de atividade',
        color='Atividade',
        text=value_label,
    )
    text_fmt = '%{text:,.0f}' if not has_cost else '%{text:,.0f}'
    fig_bar.update_traces(texttemplate=text_fmt, textposition='outside')
    fig_bar.update_layout(
        height=380,
        showlegend=False,
        yaxis_title=value_label,
        xaxis_title='',
        margin=dict(t=50, b=80, l=60, r=20),
        xaxis_tickangle=-30,
    )

    # --- Gráfico 2: Pizza distribuição % ---
    fig_pie = px.pie(
        by_activity,
        names='Atividade',
        values=value_label,
        title='Distribuição % por atividade',
        hole=0.4,
    )
    fig_pie.update_traces(textinfo='percent+label')
    fig_pie.update_layout(height=380, margin=dict(t=50, b=30, l=20, r=20))

    # --- Gráfico 3: Tendência mensal (stacked bar) ---
    monthly_graph = html.Div()
    if 'MesCompetencia' in df.columns:
        by_month = (
            df.groupby(['MesCompetencia', '_atividade'], dropna=False)
            .agg(**{value_label: (value_col, 'sum')})
            .reset_index()
            .rename(columns={'_atividade': 'Atividade', 'MesCompetencia': 'Mês'})
            .sort_values('Mês')
        )
        if not by_month.empty:
            fig_trend = px.bar(
                by_month,
                x='Mês',
                y=value_label,
                color='Atividade',
                title='Evolução mensal do custo por atividade',
                barmode='stack',
            )
            fig_trend.update_layout(
                height=380,
                yaxis_title=value_label,
                xaxis_title='',
                margin=dict(t=50, b=100, l=60, r=20),
                legend=dict(orientation='h', yanchor='bottom', y=-0.55, xanchor='center', x=0.5),
            )
            monthly_graph = dcc.Graph(figure=fig_trend)

    return html.Div([
        html.H4('Custo por Categoria de Atividade', style={'textAlign': 'left', 'marginTop': '22px'}),
        html.Div(sem_taxa_note),
        html.Div([
            html.Div([dcc.Graph(figure=fig_bar)], style={'flex': '1', 'minWidth': '320px'}),
            html.Div([dcc.Graph(figure=fig_pie)], style={'flex': '1', 'minWidth': '280px'}),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'}),
        html.Div([monthly_graph], style={'marginTop': '12px'}),
    ])


def build_cost_per_phase_data(events_df: 'pd.DataFrame', worklog_df: 'pd.DataFrame') -> dict:
    """
    Joins PM event intervals with CAPEX worklogs to compute actual vs. estimated cost per
    workflow phase (execution statuses only).

    For each (Issue Key, To Status Norm, phase_start, phase_end) interval in events_df,
    finds all worklogs of the same issue whose 'Data do Apontamento das Horas' falls within
    [phase_start, phase_end) and sums their cost.

    Returns dict with:
      - 'phase_df': DataFrame keyed by 'Fase' with CustoEstimadoPM, HorasEstimadasPM,
                    CustoRealApontado, HorasReaisApontadas, OcorrenciasPM, IssuesPM
      - 'has_real_cost': bool — True when at least one worklog was matched
      - 'coverage_pct': float — % of PM-estimated cost backed by real worklogs
      - 'total_pm_cost', 'total_real_cost': float totals
    """
    _empty = {'phase_df': pd.DataFrame(), 'has_real_cost': False, 'coverage_pct': np.nan,
              'total_pm_cost': 0.0, 'total_real_cost': 0.0}

    if events_df is None or events_df.empty:
        return _empty
    required_ev = {'Issue Key', 'History Created', 'To Status Norm', 'TempoStatusDias'}
    if not required_ev.issubset(events_df.columns):
        return _empty

    ev = events_df[list(required_ev | {'Horas PM Elegíveis', 'Custo PM Estimado'} & set(events_df.columns))].copy()
    ev['History Created'] = pd.to_datetime(ev['History Created'], errors='coerce')
    ev['TempoStatusDias'] = pd.to_numeric(ev['TempoStatusDias'], errors='coerce').fillna(0.0)
    ev = ev[ev['History Created'].notna() & (ev['TempoStatusDias'] > 0)].copy()
    if ev.empty:
        return _empty

    ev['_phase_start'] = ev['History Created']
    ev['_phase_end'] = ev['History Created'] + pd.to_timedelta(ev['TempoStatusDias'], unit='D')
    ev['Horas PM Elegíveis'] = pd.to_numeric(ev.get('Horas PM Elegíveis'), errors='coerce').fillna(0.0)
    ev['Custo PM Estimado'] = pd.to_numeric(ev.get('Custo PM Estimado'), errors='coerce').fillna(0.0)
    ev['_status_label'] = (
        ev['To Status Norm'].fillna('').astype(str).str.strip().str.title().replace('', 'Desconhecido')
    )

    pm_agg = (
        ev.groupby('_status_label', dropna=False)
        .agg(
            CustoEstimadoPM=('Custo PM Estimado', 'sum'),
            HorasEstimadasPM=('Horas PM Elegíveis', 'sum'),
            OcorrenciasPM=('Issue Key', 'size'),
            IssuesPM=('Issue Key', 'nunique'),
        )
        .reset_index()
        .rename(columns={'_status_label': 'Fase'})
    )

    phase_df = pm_agg.copy()
    phase_df['CustoRealApontado'] = 0.0
    phase_df['HorasReaisApontadas'] = 0.0
    has_real_cost = False

    if worklog_df is not None and not worklog_df.empty and 'Data do Apontamento das Horas' in worklog_df.columns:
        wl = worklog_df[['Issue Key', 'Data do Apontamento das Horas', 'Horas', 'Custo Real Apontado (R$)']].copy()
        wl['Data do Apontamento das Horas'] = pd.to_datetime(wl['Data do Apontamento das Horas'], errors='coerce')
        wl['Custo Real Apontado (R$)'] = pd.to_numeric(wl['Custo Real Apontado (R$)'], errors='coerce').fillna(0.0)
        wl['Horas'] = pd.to_numeric(wl['Horas'], errors='coerce').fillna(0.0)
        wl = wl[wl['Data do Apontamento das Horas'].notna() & ((wl['Custo Real Apontado (R$)'] > 0) | (wl['Horas'] > 0))].copy()

        if not wl.empty:
            merged = ev[['Issue Key', '_status_label', '_phase_start', '_phase_end']].merge(
                wl, on='Issue Key', how='inner'
            )
            wl_date = merged['Data do Apontamento das Horas']
            matched = merged[(wl_date >= merged['_phase_start']) & (wl_date < merged['_phase_end'])].copy()

            if not matched.empty:
                has_real_cost = matched['Custo Real Apontado (R$)'].sum() > 0
                real_agg = (
                    matched.groupby('_status_label', dropna=False)
                    .agg(
                        CustoRealApontado=('Custo Real Apontado (R$)', 'sum'),
                        HorasReaisApontadas=('Horas', 'sum'),
                    )
                    .reset_index()
                    .rename(columns={'_status_label': 'Fase'})
                )
                phase_df = pm_agg.merge(real_agg, on='Fase', how='left')
                phase_df['CustoRealApontado'] = pd.to_numeric(phase_df['CustoRealApontado'], errors='coerce').fillna(0.0)
                phase_df['HorasReaisApontadas'] = pd.to_numeric(phase_df['HorasReaisApontadas'], errors='coerce').fillna(0.0)

    total_pm = float(phase_df['CustoEstimadoPM'].sum())
    total_real = float(phase_df['CustoRealApontado'].sum())
    coverage_pct = (total_real / total_pm * 100.0) if total_pm > 0 else np.nan

    phase_df = phase_df.sort_values('CustoEstimadoPM', ascending=False).reset_index(drop=True)
    return {
        'phase_df': phase_df,
        'has_real_cost': has_real_cost,
        'coverage_pct': coverage_pct,
        'total_pm_cost': total_pm,
        'total_real_cost': total_real,
    }


def _build_custo_por_fase_section(events_df: 'pd.DataFrame', worklog_df: 'pd.DataFrame') -> 'html.Div':
    """
    Renders 3 charts comparing PM-estimated vs. actual worklog cost per workflow phase.
    Uses build_cost_per_phase_data() to compute the join.
    """
    data = build_cost_per_phase_data(events_df, worklog_df)
    phase_df = data.get('phase_df', pd.DataFrame())
    if phase_df is None or phase_df.empty:
        return html.Div()

    has_real_cost = data.get('has_real_cost', False)
    coverage_pct = data.get('coverage_pct', np.nan)

    notes = []
    if not has_real_cost:
        notes.append(html.P(
            'Sem sobreposição entre worklogs e janelas de fase no período. '
            'Exibindo estimativa PM (horas elegíveis × taxa). '
            'Para habilitar custo real por fase, certifique-se de que taxas de custo estejam configuradas '
            'e que os worklogs CAPEX estejam no mesmo período que os eventos PM.',
            style={'color': '#8a6d3b', 'fontSize': '13px', 'marginBottom': '8px'}
        ))
    elif not np.isnan(coverage_pct):
        notes.append(html.P(
            f'Cobertura de worklog real nas fases de execução: {coverage_pct:.1f}% do custo PM estimado.',
            style={'color': '#555', 'fontSize': '13px', 'marginBottom': '8px'}
        ))

    # ── Chart 1: Custo por fase — estimado vs. real ──────────────────────────
    if has_real_cost:
        bar_rows = []
        for _, row in phase_df.iterrows():
            bar_rows.append({'Fase': row['Fase'], 'Valor': row['CustoEstimadoPM'], 'Tipo': 'PM Estimado'})
            bar_rows.append({'Fase': row['Fase'], 'Valor': row['CustoRealApontado'], 'Tipo': 'Real Apontado'})
        fig_cost = px.bar(
            pd.DataFrame(bar_rows),
            x='Fase', y='Valor', color='Tipo', barmode='group',
            title='Custo por fase: PM estimado vs. real apontado',
            color_discrete_map={'PM Estimado': '#aec6e8', 'Real Apontado': '#1f77b4'},
        )
        fig_cost.update_layout(showlegend=True)
    else:
        fig_cost = px.bar(
            phase_df, x='Fase', y='CustoEstimadoPM',
            title='Custo estimado PM por fase (horas × taxa)',
            color='Fase', text='CustoEstimadoPM',
        )
        fig_cost.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_cost.update_layout(showlegend=False)
    fig_cost.update_layout(
        height=380, yaxis_title='Custo (R$)', xaxis_title='',
        margin=dict(t=50, b=80, l=60, r=20), xaxis_tickangle=-30,
    )

    # ── Chart 2: Horas por fase — PM elegíveis vs. real ─────────────────────
    if has_real_cost:
        hr_rows = []
        for _, row in phase_df.iterrows():
            hr_rows.append({'Fase': row['Fase'], 'Horas': row['HorasEstimadasPM'], 'Tipo': 'Horas elegíveis'})
            hr_rows.append({'Fase': row['Fase'], 'Horas': row['HorasReaisApontadas'], 'Tipo': 'Real Apontado'})
        fig_hours = px.bar(
            pd.DataFrame(hr_rows),
            x='Fase', y='Horas', color='Tipo', barmode='group',
            title='Horas por fase: elegíveis vs. reais apontadas',
            color_discrete_map={'Horas elegíveis': '#98df8a', 'Real Apontado': '#2ca02c'},
        )
        fig_hours.update_layout(showlegend=True)
    else:
        fig_hours = px.bar(
            phase_df, x='Fase', y='HorasEstimadasPM',
            title='Horas elegíveis por fase',
            color='Fase', text='HorasEstimadasPM',
        )
        fig_hours.update_traces(texttemplate='%{text:,.1f}h', textposition='outside')
        fig_hours.update_layout(showlegend=False)
    fig_hours.update_layout(
        height=380, yaxis_title='Horas', xaxis_title='',
        margin=dict(t=50, b=80, l=60, r=20), xaxis_tickangle=-30,
    )

    # ── Chart 3: Desvio % real vs. estimado (só quando há custo real) ────────
    desvio_graph = html.Div()
    if has_real_cost:
        dev_df = phase_df[phase_df['CustoEstimadoPM'] > 0].copy()
        if not dev_df.empty:
            dev_df['Desvio %'] = (
                (dev_df['CustoRealApontado'] - dev_df['CustoEstimadoPM'])
                / dev_df['CustoEstimadoPM'] * 100.0
            )
            fig_desvio = px.bar(
                dev_df, x='Fase', y='Desvio %',
                title='Desvio custo real vs. estimado por fase (%)',
                color='Desvio %',
                color_continuous_scale='RdYlGn',
                color_continuous_midpoint=0,
                text='Desvio %',
            )
            fig_desvio.update_traces(texttemplate='%{text:+.1f}%', textposition='outside')
            fig_desvio.update_layout(
                height=340, yaxis_title='Desvio %', xaxis_title='',
                margin=dict(t=50, b=80, l=60, r=20), xaxis_tickangle=-30,
                coloraxis_showscale=False,
            )
            desvio_graph = dcc.Graph(figure=fig_desvio)

    return html.Div([
        html.H4('Custo por Fase do Workflow', style={'textAlign': 'left', 'marginTop': '22px'}),
        html.Div(notes),
        html.Div([
            html.Div([dcc.Graph(figure=fig_cost)], style={'flex': '1', 'minWidth': '340px'}),
            html.Div([dcc.Graph(figure=fig_hours)], style={'flex': '1', 'minWidth': '340px'}),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'}),
        html.Div([desvio_graph], style={'marginTop': '12px'}),
    ])


def _pm_filter_real_worklog_df(worklog_df: 'pd.DataFrame') -> 'pd.DataFrame':
    """Keeps only real Jira/CAPEX worklogs, excluding PM synthetic fallback rows."""
    if worklog_df is None or worklog_df.empty:
        return pd.DataFrame()

    wl = worklog_df.copy()
    if 'Origem Horas' not in wl.columns:
        return wl

    origem = wl['Origem Horas'].fillna('').astype(str).str.strip().str.lower()
    synthetic_tokens = {
        'pm - permanência em execução',
        'pm - permanencia em execução',
        'pm - permanência em execucao',
        'pm - permanencia em execucao',
    }
    real_df = wl[~origem.isin(synthetic_tokens)].copy()
    if real_df.empty and origem.eq('').all():
        return wl
    return real_df


def _pm_has_real_worklog_data(worklog_df: 'pd.DataFrame') -> bool:
    real_df = _pm_filter_real_worklog_df(worklog_df)
    if real_df.empty:
        return False
    horas = pd.to_numeric(real_df.get('Horas', pd.Series(0.0, index=real_df.index)), errors='coerce').fillna(0.0)
    custo = pd.to_numeric(real_df.get('Custo Real Apontado (R$)', pd.Series(0.0, index=real_df.index)), errors='coerce').fillna(0.0)
    return bool(horas.gt(0).any() or custo.gt(0).any())


def build_custo_estimado_vs_real_data(events_df: 'pd.DataFrame', worklog_df: 'pd.DataFrame') -> dict:
    """
    Joins PM-estimated cost per issue (from events_all) with real worklog cost per issue
    (from capex_worklog_df) by Issue Key.

    Estimated cost = sum(Custo PM Estimado) across all execution-phase events for the issue.
    Real cost      = sum(Custo Real Apontado) across all worklogs for the issue.

    Returns dict with:
      - 'issue_df': one row per Issue Key with CustoEstimado, CustoReal, HorasEstimadas,
                    HorasReais, Produto, Desvio, DesvioP, Categoria
      - 'has_cost':  bool — True when rates produce monetary values
      - 'n_over':    int — issues over budget (DesvioP > 30%)
      - 'n_under':   int — issues under budget (DesvioP < -20%)
      - 'n_on':      int — issues on target
      - 'median_desvio': float — median DesvioP across matched issues
    """
    _empty = {'issue_df': pd.DataFrame(), 'has_cost': False,
              'n_over': 0, 'n_under': 0, 'n_on': 0, 'median_desvio': np.nan}

    if events_df is None or events_df.empty:
        return _empty
    if 'Issue Key' not in events_df.columns:
        return _empty

    # ── Aggregate PM estimate per issue ──────────────────────────────────────
    ev = events_df.copy()
    ev['Horas PM Elegíveis'] = pd.to_numeric(ev.get('Horas PM Elegíveis'), errors='coerce').fillna(0.0)
    ev['Custo PM Estimado'] = pd.to_numeric(ev.get('Custo PM Estimado'), errors='coerce').fillna(0.0)
    ev['Produto'] = ev.get('Produto', pd.Series([''] * len(ev))).fillna('').astype(str)
    ev_agg = (
        ev.groupby('Issue Key', dropna=False)
        .agg(
            CustoEstimado=('Custo PM Estimado', 'sum'),
            HorasEstimadas=('Horas PM Elegíveis', 'sum'),
            Produto=('Produto', 'first'),
        )
        .reset_index()
    )
    ev_agg = ev_agg[ev_agg['Issue Key'].ne('') & (ev_agg['HorasEstimadas'] > 0)].copy()

    if ev_agg.empty:
        return _empty

    # ── Aggregate real cost per issue ─────────────────────────────────────────
    real_worklog_df = _pm_filter_real_worklog_df(worklog_df)
    if real_worklog_df is None or real_worklog_df.empty or 'Issue Key' not in real_worklog_df.columns:
        return _empty

    wl = real_worklog_df.copy()
    wl['Horas'] = pd.to_numeric(wl.get('Horas'), errors='coerce').fillna(0.0)
    wl['Custo Real Apontado (R$)'] = pd.to_numeric(wl.get('Custo Real Apontado (R$)'), errors='coerce').fillna(0.0)
    wl_agg = (
        wl.groupby('Issue Key', dropna=False)
        .agg(
            CustoReal=('Custo Real Apontado (R$)', 'sum'),
            HorasReais=('Horas', 'sum'),
        )
        .reset_index()
    )

    # ── Join on Issue Key (inner: only issues present in both) ────────────────
    merged = ev_agg.merge(wl_agg, on='Issue Key', how='inner')
    if merged.empty:
        return _empty

    has_cost = (merged['CustoEstimado'].sum() > 0) and (merged['CustoReal'].sum() > 0)
    if not has_cost:
        # Fall back to hours comparison
        merged['CustoEstimado'] = merged['HorasEstimadas']
        merged['CustoReal'] = merged['HorasReais']

    # ── Deviation metrics ─────────────────────────────────────────────────────
    estimado_nonzero = merged['CustoEstimado'].replace(0, np.nan)
    merged['Desvio'] = merged['CustoReal'] - merged['CustoEstimado']
    merged['DesvioP'] = merged['Desvio'] / estimado_nonzero * 100.0

    def _categorize(d):
        if pd.isna(d):
            return 'Sem estimativa'
        if d > 30.0:
            return 'Acima do estimado'
        if d < -20.0:
            return 'Abaixo do estimado'
        return 'Dentro do esperado'

    merged['Categoria'] = merged['DesvioP'].apply(_categorize)
    merged = merged.sort_values('CustoReal', ascending=False).reset_index(drop=True)

    valid = merged['DesvioP'].dropna()
    n_over = int((valid > 30.0).sum())
    n_under = int((valid < -20.0).sum())
    n_on = int(((valid >= -20.0) & (valid <= 30.0)).sum())
    median_dev = float(valid.median()) if not valid.empty else np.nan

    return {
        'issue_df': merged,
        'has_cost': has_cost,
        'n_over': n_over,
        'n_under': n_under,
        'n_on': n_on,
        'median_desvio': median_dev,
    }


def _build_custo_estimado_vs_real_section(events_df: 'pd.DataFrame', worklog_df: 'pd.DataFrame') -> 'html.Div':
    """
    Renders 3 charts comparing PM-estimated vs. actual cost per issue:
      1. Scatter plot: X=Estimado, Y=Real (reference line Y=X, color=Categoria)
      2. Histogram: distribution of DesvioP%
      3. Bar chart: top 15 over-budget issues
    """
    data = build_custo_estimado_vs_real_data(events_df, worklog_df)
    issue_df = data.get('issue_df', pd.DataFrame())
    if issue_df is None or issue_df.empty:
        return html.Div()

    has_cost = data.get('has_cost', False)
    n_over = data.get('n_over', 0)
    n_under = data.get('n_under', 0)
    n_on = data.get('n_on', 0)
    median_dev = data.get('median_desvio', np.nan)

    value_label = 'Custo (R$)' if has_cost else 'Horas'
    est_col = 'CustoEstimado'
    real_col = 'CustoReal'

    notes = []
    if not has_cost:
        notes.append(html.P(
            'Taxas de custo não configuradas — comparação exibida em horas. '
            'Configure FLOW_PMO_PM_COST_PER_HOUR_MAP para ativar comparação monetária.',
            style={'color': '#8a6d3b', 'fontSize': '13px', 'marginBottom': '8px'}
        ))
    med_str = f'{median_dev:+.1f}%' if not np.isnan(median_dev) else '—'
    notes.append(html.P(
        f'{len(issue_df)} issues com estimativa e worklog. '
        f'Acima do estimado: {n_over} | Dentro do esperado: {n_on} | Abaixo: {n_under} | '
        f'Desvio mediano: {med_str}',
        style={'color': '#333', 'fontSize': '13px', 'marginBottom': '8px'}
    ))

    cat_colors = {
        'Acima do estimado': '#d62728',
        'Dentro do esperado': '#2ca02c',
        'Abaixo do estimado': '#1f77b4',
        'Sem estimativa': '#aaa',
    }

    # ── Chart 1: Scatter estimado vs real ────────────────────────────────────
    scatter_df = issue_df.copy()
    scatter_df['_hover_desvio'] = scatter_df['DesvioP'].apply(
        lambda v: f'{v:+.1f}%' if not pd.isna(v) else '—'
    )
    max_val = max(scatter_df[est_col].max(), scatter_df[real_col].max()) * 1.05
    max_val = max_val if max_val > 0 else 1.0

    fig_scatter = px.scatter(
        scatter_df,
        x=est_col,
        y=real_col,
        color='Categoria',
        hover_name='Issue Key',
        hover_data={
            'Produto': True,
            '_hover_desvio': True,
            'HorasEstimadas': ':.1f',
            'HorasReais': ':.1f',
            est_col: False,
            real_col: False,
            'Categoria': False,
        },
        labels={
            est_col: f'{value_label} Estimado (PM)',
            real_col: f'{value_label} Real (Worklog)',
            '_hover_desvio': 'Desvio',
            'HorasEstimadas': 'Horas Estimadas',
            'HorasReais': 'Horas Reais',
        },
        color_discrete_map=cat_colors,
        title='Custo estimado (PM) vs. real (worklog) por issue',
    )
    # Reference line Y = X
    fig_scatter.add_shape(
        type='line',
        x0=0, y0=0, x1=max_val, y1=max_val,
        line=dict(color='#888', width=1.5, dash='dash'),
    )
    fig_scatter.add_annotation(
        x=max_val * 0.85, y=max_val * 0.9,
        text='Estimado = Real',
        showarrow=False,
        font=dict(color='#888', size=11),
    )
    fig_scatter.update_layout(
        height=420,
        xaxis_title=f'{value_label} Estimado (PM)',
        yaxis_title=f'{value_label} Real (Worklog)',
        margin=dict(t=50, b=60, l=60, r=20),
        legend=dict(title='', orientation='h', yanchor='bottom', y=-0.25),
    )

    # ── Chart 2: Histograma de desvio % ──────────────────────────────────────
    dev_df = issue_df[issue_df['DesvioP'].notna()].copy()
    fig_hist = px.histogram(
        dev_df,
        x='DesvioP',
        nbins=30,
        title='Distribuição do desvio % (real vs. estimado)',
        color_discrete_sequence=['#1f77b4'],
        labels={'DesvioP': 'Desvio %'},
    )
    fig_hist.add_vline(x=0, line_dash='dash', line_color='#888', annotation_text='0%')
    if not np.isnan(median_dev):
        fig_hist.add_vline(
            x=median_dev, line_dash='dot', line_color='#d62728',
            annotation_text=f'Mediana {median_dev:+.1f}%',
            annotation_position='top right',
        )
    fig_hist.update_layout(
        height=360,
        xaxis_title='Desvio %',
        yaxis_title='Nº de Issues',
        margin=dict(t=50, b=60, l=60, r=20),
    )

    # ── Chart 3: Top 15 issues com maior desvio positivo (over-budget) ───────
    over_graph = html.Div()
    over_df = issue_df[issue_df['DesvioP'] > 0].nlargest(15, 'DesvioP').copy()
    if not over_df.empty:
        over_df['_label'] = over_df['Issue Key'] + ' (' + over_df['Produto'] + ')'
        fig_over = px.bar(
            over_df,
            x='DesvioP',
            y='_label',
            orientation='h',
            title='Top 15 issues acima do estimado',
            color='DesvioP',
            color_continuous_scale='Reds',
            text='DesvioP',
            labels={'DesvioP': 'Desvio %', '_label': ''},
        )
        fig_over.update_traces(texttemplate='%{text:+.1f}%', textposition='outside')
        fig_over.update_layout(
            height=max(300, len(over_df) * 28 + 80),
            xaxis_title='Desvio %',
            yaxis=dict(autorange='reversed'),
            margin=dict(t=50, b=60, l=220, r=80),
            coloraxis_showscale=False,
        )
        over_graph = dcc.Graph(figure=fig_over)

    return html.Div([
        html.H4('Custo Estimado vs. Real por Issue', style={'textAlign': 'left', 'marginTop': '22px'}),
        html.Div(notes),
        html.Div([
            html.Div([dcc.Graph(figure=fig_scatter)], style={'flex': '2', 'minWidth': '380px'}),
            html.Div([dcc.Graph(figure=fig_hist)], style={'flex': '1', 'minWidth': '280px'}),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'}),
        html.Div([over_graph], style={'marginTop': '12px'}),
    ])


def build_custo_pm_calibrado_data(events_df: 'pd.DataFrame', touch_time_df: 'pd.DataFrame | None' = None) -> dict:
    """Summarises PM-calibrated execution cost by issue/product.

    Uses process mining as the primary source (eligible execution hours × PM cost rate).
    When touch_time_df is provided (from build_touch_time_triangulation), enriches each
    issue with the 3-model triangulation columns: HorasM1, HorasM2, HorasM3,
    HorasEstimadas, ConfiancaEstimativa, ConvergenciaModelos, BandaIncerteza_pct.
    """
    _empty = {
        'issue_df': pd.DataFrame(),
        'product_df': pd.DataFrame(),
        'kpis': {},
        'has_cost': False,
        'triangulation_available': False,
    }

    if events_df is None or events_df.empty or 'Issue Key' not in events_df.columns:
        return _empty

    ev = events_df.copy()
    ev['Horas PM Elegíveis'] = pd.to_numeric(ev.get('Horas PM Elegíveis'), errors='coerce').fillna(0.0)
    ev['Custo PM Estimado'] = pd.to_numeric(ev.get('Custo PM Estimado'), errors='coerce').fillna(0.0)
    ev['TempoStatusDias'] = pd.to_numeric(ev.get('TempoStatusDias'), errors='coerce').fillna(0.0)
    ev['Produto'] = ev.get('Produto', pd.Series('', index=ev.index)).fillna('').astype(str)
    ev['_status_label'] = ev.get('To Status Norm', ev.get('To Status', pd.Series('', index=ev.index))).fillna('').astype(str).str.strip()
    ev['Responsável PM'] = ev.get('Responsável PM', pd.Series('', index=ev.index)).fillna('').astype(str).str.strip()
    ev = ev[ev['Issue Key'].fillna('').astype(str).str.strip().ne('') & (ev['Horas PM Elegíveis'] > 0)].copy()
    if ev.empty:
        return _empty

    issue_df = (
        ev.groupby('Issue Key', dropna=False)
        .agg(
            Produto=('Produto', 'first'),
            CustoPMCalibrado=('Custo PM Estimado', 'sum'),
            HorasPMCalibradas=('Horas PM Elegíveis', 'sum'),
            DiasExecucao=('TempoStatusDias', 'sum'),
            FasesExecucao=('_status_label', lambda x: len({str(v).strip() for v in x if str(v).strip()})),
            ResponsaveisPM=('Responsável PM', lambda x: len({str(v).strip() for v in x if str(v).strip()})),
        )
        .reset_index()
    )
    if issue_df.empty:
        return _empty

    has_cost = issue_df['CustoPMCalibrado'].sum() > 0
    value_col = 'CustoPMCalibrado' if has_cost else 'HorasPMCalibradas'
    issue_df = issue_df.sort_values(value_col, ascending=False).reset_index(drop=True)

    # ── Enriquecer com triangulação se disponível ──────────────────────────────
    triangulation_available = False
    if touch_time_df is not None and not touch_time_df.empty and 'Issue Key' in touch_time_df.columns:
        tri_cols = [c for c in [
            'Issue Key', 'HorasM1', 'HorasM2', 'HorasM3',
            'HorasEstimadas', 'ConfiancaEstimativa', 'ConvergenciaModelos', 'BandaIncerteza_pct',
        ] if c in touch_time_df.columns]
        if len(tri_cols) > 1:
            issue_df = issue_df.merge(touch_time_df[tri_cols], on='Issue Key', how='left')
            triangulation_available = True

    product_df = (
        issue_df.groupby('Produto', dropna=False)
        .agg(
            ValorPM=(value_col, 'sum'),
            HorasPMCalibradas=('HorasPMCalibradas', 'sum'),
            DiasExecucao=('DiasExecucao', 'sum'),
            Issues=('Issue Key', 'nunique'),
        )
        .reset_index()
        .sort_values('ValorPM', ascending=False)
    )

    valor_total = float(issue_df[value_col].sum())
    valor_mediano = float(issue_df[value_col].median()) if not issue_df.empty else np.nan
    horas_total = float(issue_df['HorasPMCalibradas'].sum())
    dias_total = float(issue_df['DiasExecucao'].sum())

    # KPI: % itens com modelos convergentes
    pct_convergentes = np.nan
    if triangulation_available and 'ConvergenciaModelos' in issue_df.columns:
        conv_col = issue_df['ConvergenciaModelos'].dropna()
        if not conv_col.empty:
            pct_convergentes = float(conv_col.sum()) / len(conv_col) * 100.0

    return {
        'issue_df': issue_df,
        'product_df': product_df,
        'has_cost': has_cost,
        'triangulation_available': triangulation_available,
        'kpis': {
            'issues': int(issue_df['Issue Key'].nunique()),
            'valor_total': valor_total,
            'valor_mediano_issue': valor_mediano,
            'horas_total': horas_total,
            'dias_total': dias_total,
            'pct_convergentes': pct_convergentes,
        },
    }


def _build_custo_pm_calibrado_section(events_df: 'pd.DataFrame', touch_time_df: 'pd.DataFrame | None' = None) -> 'html.Div':
    """Renders PM-calibrated issue cost when no independent Jira worklog exists.

    When touch_time_df is provided (from build_touch_time_triangulation), enriches the
    display with 3-model triangulation columns and convergence KPI — audit-ready for CAPEX.
    """
    data = build_custo_pm_calibrado_data(events_df, touch_time_df=touch_time_df)
    issue_df = data.get('issue_df', pd.DataFrame())
    product_df = data.get('product_df', pd.DataFrame())
    kpis = data.get('kpis', {})
    if issue_df is None or issue_df.empty:
        return html.Div()

    has_cost = data.get('has_cost', False)
    value_col = 'CustoPMCalibrado' if has_cost else 'HorasPMCalibradas'
    value_label = 'Custo calibrado (R$)' if has_cost else 'Horas calibradas'

    def _fmt_r(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return '—'
        return f"R$ {float(v):,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def _fmt_h(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return '—'
        return f"{float(v):,.1f}h"

    triangulation_available = data.get('triangulation_available', False)

    notes = [
        html.P(
            'Sem worklog Jira real no período atual. Esta seção usa a trilha de execução observada no fluxo: '
            'horas elegíveis de execução x taxa hora configurada.',
            style={'color': '#333', 'fontSize': '13px', 'marginBottom': '8px'}
        ),
        html.P(
            'Leia estes valores como custo calibrado/observado do processo, útil para gestão operacional e '
            'comparação entre produtos/issues, e não como apontamento contábil formal de horas.',
            style={'color': '#555', 'fontSize': '13px', 'marginBottom': '8px'}
        ),
    ]
    if not has_cost:
        notes.append(html.P(
            'Taxas de custo não configuradas — a visão está exibida em horas calibradas.',
            style={'color': '#8a6d3b', 'fontSize': '13px', 'marginBottom': '8px'}
        ))
    if triangulation_available:
        notes.append(html.Details([
            html.Summary('Metodologia de triangulação (3 modelos — clique para expandir)',
                         style={'cursor': 'pointer', 'color': '#1a5276', 'fontWeight': '600', 'fontSize': '13px'}),
            html.Div([
                html.P('M1 — Fluxo observado: Σ dias em status de execução ativa × 24h (event log Jira). '
                       'Confiança Alta quando o item está mapeado ao portfólio.',
                       style={'marginBottom': '4px', 'fontSize': '12px'}),
                html.P('M2 — Alocação por Capacidade: (CycleTime_item / Σ CycleTimes_produto) × Capacidade_Mensal_Produto_h. '
                       'Distribui a capacidade declarada do time proporcionalmente ao tempo de ciclo de cada item.',
                       style={'marginBottom': '4px', 'fontSize': '12px'}),
                html.P('M3 — Complexidade × Taxa Calibrada: peso_complexidade × horas_por_SP_Sync. '
                       'O Sync (92,87% de horas mapeadas) serve como âncora de calibração da taxa horas/SP.',
                       style={'marginBottom': '4px', 'fontSize': '12px'}),
                html.P('Convergência: quando |(max − min) / média| ≤ 15% entre os modelos disponíveis, '
                       'o número é defensável para CAPEX sem apontamento manual.',
                       style={'marginBottom': '4px', 'fontSize': '12px', 'fontStyle': 'italic'}),
            ], style={'padding': '8px 12px', 'backgroundColor': '#f4f6f7', 'borderRadius': '4px',
                      'marginTop': '6px', 'border': '1px solid #d5d8dc'}),
        ], style={'marginBottom': '8px'}))

    pct_conv = kpis.get('pct_convergentes')
    _fmt_pct = (f"{pct_conv:.0f}%" if pct_conv is not None and not (isinstance(pct_conv, float) and np.isnan(pct_conv)) else '—')

    kpi_cards_items = [
        _portfolio_metric_card('Issues com custo calibrado', str(kpis.get('issues', 0))),
        _portfolio_metric_card(
            'Custo calibrado total' if has_cost else 'Horas calibradas',
            _fmt_r(kpis.get('valor_total')) if has_cost else _fmt_h(kpis.get('horas_total')),
        ),
        _portfolio_metric_card('Horas calibradas', _fmt_h(kpis.get('horas_total'))),
        _portfolio_metric_card('Mediana por issue', _fmt_r(kpis.get('valor_mediano_issue')) if has_cost else _fmt_h(kpis.get('valor_mediano_issue'))),
    ]
    if triangulation_available:
        kpi_cards_items.append(
            _portfolio_metric_card('Itens convergentes (±15%)', _fmt_pct)
        )
    kpi_cards = html.Div(kpi_cards_items, style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap', 'marginBottom': '12px'})

    scatter_df = issue_df.copy()
    scatter_df['_hover_valor'] = scatter_df[value_col].apply(lambda v: _fmt_r(v) if has_cost else _fmt_h(v))
    fig_scatter = px.scatter(
        scatter_df,
        x='HorasPMCalibradas',
        y=value_col,
        color='Produto',
        hover_name='Issue Key',
        hover_data={
            'DiasExecucao': ':.1f',
            'FasesExecucao': True,
            'ResponsaveisPM': True,
            '_hover_valor': True,
            'HorasPMCalibradas': ':.1f',
            value_col: False,
        },
        labels={
            'HorasPMCalibradas': 'Horas calibradas',
            value_col: value_label,
            '_hover_valor': value_label,
            'DiasExecucao': 'Dias em execução',
            'FasesExecucao': 'Fases exec.',
            'ResponsaveisPM': 'Pessoas',
        },
        title='Custo calibrado por issue',
    )
    fig_scatter.update_layout(
        height=420,
        xaxis_title='Horas calibradas',
        yaxis_title=value_label,
        margin=dict(t=50, b=60, l=60, r=20),
        legend=dict(title='', orientation='h', yanchor='bottom', y=-0.25),
    )

    fig_hist = px.histogram(
        issue_df,
        x=value_col,
        nbins=30,
        title='Distribuição do custo PM calibrado por issue',
        color_discrete_sequence=['#1f77b4'],
        labels={value_col: value_label},
    )
    if not np.isnan(kpis.get('valor_mediano_issue', np.nan)):
        fig_hist.add_vline(
            x=kpis.get('valor_mediano_issue'),
            line_dash='dot',
            line_color='#d62728',
            annotation_text='Mediana',
            annotation_position='top right',
        )
    fig_hist.update_layout(
        height=360,
        xaxis_title=value_label,
        yaxis_title='Nº de Issues',
        margin=dict(t=50, b=60, l=60, r=20),
    )

    fig_product = go.Figure()
    if product_df is not None and not product_df.empty:
        fig_product = px.bar(
            product_df,
            x='Produto',
            y='ValorPM',
            color='Produto',
            title='Custo calibrado total por produto',
            text='ValorPM',
            labels={'ValorPM': value_label, 'Produto': ''},
        )
        fig_product.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_product.update_layout(
            height=360,
            showlegend=False,
            yaxis_title=value_label,
            xaxis_title='',
            margin=dict(t=50, b=60, l=60, r=20),
        )

    top_graph = html.Div()
    top_df = issue_df.head(15).copy()
    if not top_df.empty:
        top_df['_label'] = top_df['Issue Key'] + ' (' + top_df['Produto'] + ')'
        fig_top = px.bar(
            top_df,
            x=value_col,
            y='_label',
            orientation='h',
            title='Top 15 issues por custo calibrado',
            color=value_col,
            color_continuous_scale='Blues',
            text=value_col,
            labels={value_col: value_label, '_label': ''},
        )
        fig_top.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_top.update_layout(
            height=max(300, len(top_df) * 28 + 80),
            xaxis_title=value_label,
            yaxis=dict(autorange='reversed'),
            margin=dict(t=50, b=60, l=220, r=80),
            coloraxis_showscale=False,
        )
        top_graph = dcc.Graph(figure=fig_top)

    # ── Tabela de triangulação por issue ──────────────────────────────────────
    triangulation_table = html.Div()
    if triangulation_available:
        _tri_cols_display = ['Issue Key', 'Produto', 'HorasM1', 'HorasM2', 'HorasM3',
                             'HorasEstimadas', 'ConfiancaEstimativa', 'BandaIncerteza_pct', 'ConvergenciaModelos']
        tri_display = issue_df[[c for c in _tri_cols_display if c in issue_df.columns]].head(30).copy()

        def _confidence_badge(val):
            color_map = {'Alta': '#1e8449', 'Média': '#b7950b', 'Baixa': '#922b21'}
            return html.Span(
                str(val),
                style={
                    'backgroundColor': color_map.get(str(val), '#7f8c8d'),
                    'color': 'white',
                    'padding': '2px 8px',
                    'borderRadius': '10px',
                    'fontSize': '11px',
                    'fontWeight': '600',
                },
            )

        def _convergence_badge(val):
            if val is True or val is np.bool_(True):
                return html.Span('Sim', style={'color': '#1e8449', 'fontWeight': '600', 'fontSize': '11px'})
            if val is False or val is np.bool_(False):
                return html.Span('Não', style={'color': '#922b21', 'fontSize': '11px'})
            return html.Span('—', style={'color': '#7f8c8d', 'fontSize': '11px'})

        def _fmt_h_short(v):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return '—'
            return f"{float(v):.1f}h"

        def _fmt_pct_band(v):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return '—'
            return f"±{float(v):.0f}%"

        header = html.Tr([
            html.Th(c, style={'padding': '6px 8px', 'backgroundColor': '#1a5276', 'color': 'white',
                               'fontSize': '11px', 'fontWeight': '600', 'whiteSpace': 'nowrap'})
            for c in ['Issue', 'Produto', 'M1 (h)', 'M2 (h)', 'M3 (h)', 'Estimado (h)', 'Confiança', 'Banda', 'Converge?']
            if True  # alinha com _tri_cols_display
        ])
        rows = []
        for _, row in tri_display.iterrows():
            cells = [
                html.Td(str(row.get('Issue Key', '—')), style={'padding': '4px 8px', 'fontSize': '12px'}),
                html.Td(str(row.get('Produto', '—')), style={'padding': '4px 8px', 'fontSize': '12px'}),
                html.Td(_fmt_h_short(row.get('HorasM1')), style={'padding': '4px 8px', 'fontSize': '12px', 'textAlign': 'right'}),
                html.Td(_fmt_h_short(row.get('HorasM2')), style={'padding': '4px 8px', 'fontSize': '12px', 'textAlign': 'right'}),
                html.Td(_fmt_h_short(row.get('HorasM3')), style={'padding': '4px 8px', 'fontSize': '12px', 'textAlign': 'right'}),
                html.Td(_fmt_h_short(row.get('HorasEstimadas')), style={'padding': '4px 8px', 'fontSize': '12px', 'fontWeight': '600', 'textAlign': 'right'}),
                html.Td(_confidence_badge(row.get('ConfiancaEstimativa', '—')), style={'padding': '4px 8px', 'textAlign': 'center'}),
                html.Td(_fmt_pct_band(row.get('BandaIncerteza_pct')), style={'padding': '4px 8px', 'fontSize': '12px', 'textAlign': 'right'}),
                html.Td(_convergence_badge(row.get('ConvergenciaModelos')), style={'padding': '4px 8px', 'textAlign': 'center'}),
            ]
            bg = '#f9f9f9' if len(rows) % 2 == 0 else 'white'
            rows.append(html.Tr(cells, style={'backgroundColor': bg}))

        triangulation_table = html.Div([
            html.H5('Triangulação de Touch Time por Issue (Top 30)',
                    style={'textAlign': 'left', 'marginTop': '20px', 'marginBottom': '6px', 'color': '#1a5276'}),
            html.P('M1=Fluxo observado | M2=Alocação por Capacidade | M3=Complexidade×Taxa Sync. '
                   'Confiança Alta = item mapeado com eventos diretos de execução.',
                   style={'fontSize': '11px', 'color': '#555', 'marginBottom': '8px'}),
            html.Div(
                html.Table(
                    [html.Thead(header), html.Tbody(rows)],
                    style={'borderCollapse': 'collapse', 'width': '100%', 'fontSize': '12px'},
                ),
                style={'overflowX': 'auto', 'border': '1px solid #d5d8dc', 'borderRadius': '4px'},
            ),
        ])

    return html.Div([
        html.H4('Custo Calibrado por Issue', style={'textAlign': 'left', 'marginTop': '22px'}),
        html.Div(notes),
        kpi_cards,
        html.Div([
            html.Div([dcc.Graph(figure=fig_scatter)], style={'flex': '2', 'minWidth': '380px'}),
            html.Div([dcc.Graph(figure=fig_hist)], style={'flex': '1', 'minWidth': '280px'}),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'}),
        html.Div([
            html.Div([dcc.Graph(figure=fig_product)], style={'flex': '1', 'minWidth': '340px'}),
            html.Div([top_graph], style={'flex': '1', 'minWidth': '340px'}),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap', 'marginTop': '12px'}),
        triangulation_table,
    ])


def _pm_is_waiting_status(status_norm: str) -> bool:
    """True for queue/waiting phases: non-execution AND non-done/cancelled.
    Examples: Sprint Backlog, Ready for QA, Ready for Production, To Do."""
    if not status_norm:
        return False
    s = str(status_norm).lower().strip()
    _done_cancel = ('done', 'conclu', 'closed', 'cancel', 'itens conclu')
    if any(t in s for t in _done_cancel):
        return False
    if _pm_is_execution_status(s):
        return False
    return bool(s)


def _pm_waiting_direction(status_norm: str) -> str:
    """
    Classifies a waiting/queue status as 'Upstream' or 'Downstream'.

    Upstream  = enterprise/product-side queue before delivery to downstream execution,
                including discovery, design, triage, QA/homolog/staging preparation
                and strategic pre-delivery stages such as backlog do produto.
    Downstream = strategic downstream flow, including backlog / in progress on the
                 downstream board and stages from ready-to-delivery onward.
    """
    if not status_norm:
        return 'Upstream'
    s = str(status_norm).lower().strip()
    if s in {'ready to delivery', 'ready for delivery'}:
        return 'Downstream'
    if '%' in s:
        pct = s.replace('%', '').strip()
        if pct.replace('.', '', 1).isdigit():
            return 'Downstream'
    _upstream_tokens = (
        'triage', 'triagem', 'product discov', 'in discovery', 'discovery',
        'planning', 'plan', 'definition', 'design', 'in design',
        'refinement', 'refinamento', 'grooming', 'replenishment',
        'to do', 'todo', 'ready for development', 'ready to development',
        'ready to design', 'prioritized', 'priorit', 'sprint backlog',
        'backlog do produto', 'quebra das hist',
        'staging', 'ready for production', 'ready to staging',
        'ready for testing', 'ready for testing/qa', 'ready for qa',
        'ready for homolog', 'ready to homolog', 'ready for homologation',
        'ready to homologation',
    )
    _downstream_tokens = (
        'backlog', 'in progress', 'in progess', 'em progresso',
        'ready to delivery', 'ready for delivery',
        'ready for release', 'ready for merge', 'ready for uat',
        'in validation', 'homolog', 'validaç', 'approval', 'approved',
        'waiting for qa', 'waiting for review', 'waiting for test',
        'production', 'deploy', 'release', 'uat',
        'post release', 'pós release', 'pos release',
        'aprovação', 'aprovacao', 'ready for acceptance', 'review',
        'qa approved', 'analytics',
    )
    if any(t in s for t in _upstream_tokens):
        return 'Upstream'
    if any(t in s for t in _downstream_tokens):
        return 'Downstream'
    return 'Upstream'


def _portfolio_team_to_pm_project_key(team_value) -> str:
    team_text = str(team_value or '').strip()
    if not team_text:
        return ''
    alias_map = {
        'TECH DATA': 'DT',
        'DATA ANALYTICS': 'DT',
        'DATA&ANALYTICS': 'DT',
        'TECH BEFINANCE': 'BF',
        'BEFINANCE': 'BF',
        'BF': 'BF',
        'TECH S1NC': 'S1NC',
        'S1NC': 'S1NC',
        'SQUAD | S1NC': 'S1NC',
        'TECH W1NNER': 'W1NNER',
        'W1NNER': 'W1NNER',
        'W1NNR': 'W1NNER',
        'SQUAD | W1NNER': 'W1NNER',
    }
    norm = normalize_text(team_text).upper()
    candidate = alias_map.get(norm, norm)
    return _canonical_pm_product_key(candidate)


def _bt_strategic_board_phase(status_value, tipo_norm: str = '') -> str:
    """
    Normalizes raw Jira status values from the BT strategic snapshot to the
    board/business phase expected by executive delay views.

    Today the confirmed board rule is:
      - status 'Triagem' => board column 'Ready to Delivery'
    """
    status_text = str(status_value or '').strip()
    status_norm = normalize_text(status_text)
    tipo_norm = normalize_text(tipo_norm)

    if tipo_norm in {'epic', 'epico', 'feature', 'funcionalidade'}:
        if status_norm == 'triagem':
            return 'ready to delivery'

    return status_text


def _build_strategic_portfolio_wait_frame(portfolio_items_df: 'pd.DataFrame') -> 'pd.DataFrame':
    """
    Builds a strategic waiting-layer frame from the BT portfolio snapshot using
    current status aging (days since status change / last movement).
    """
    _empty = pd.DataFrame(columns=[
        'Issue Key', 'Produto', '_status_norm', 'TempoStatusDias', 'Status PM Elegível',
        'CamadaFluxo', 'NivelHierarquia',
    ])
    if portfolio_items_df is None or portfolio_items_df.empty:
        return _empty

    x = portfolio_items_df.copy()
    if 'Status' not in x.columns:
        return _empty

    for col in ['ID', 'Tipo', 'Status', 'TeamDisplay', 'Projeto']:
        if col not in x.columns:
            x[col] = ''
    if 'IsOpen' not in x.columns:
        status_norm = x['Status'].fillna('').astype(str).map(normalize_text)
        done_terms = ('done', 'conclu', 'closed', 'resolved', 'cancel')
        x['IsOpen'] = ~status_norm.apply(lambda s: any(t in str(s) for t in done_terms))

    x['AgingDiasSemAlteracao'] = pd.to_numeric(
        x.get('AgingDiasSemAlteracao', x.get('DiasSemMovimentacao')),
        errors='coerce'
    ).fillna(0.0)
    x['TipoNorm'] = x['Tipo'].fillna('').astype(str).map(normalize_text)
    allowed_types = {
        'epic', 'epico', 'feature', 'funcionalidade',
        'historia', 'historia de usuario', 'story', 'user story', 'us',
        'task', 'tarefa', 'spike',
    }
    x = x[
        x['ID'].fillna('').astype(str).str.strip().ne('')
        & x['IsOpen'].fillna(False).astype(bool)
        & x['TipoNorm'].isin(allowed_types)
        & (x['AgingDiasSemAlteracao'] > 0)
    ].copy()
    if x.empty:
        return _empty

    def _nivel(tipo_norm: str) -> str:
        if tipo_norm in {'epic', 'epico'}:
            return 'Épico'
        if tipo_norm in {'feature', 'funcionalidade'}:
            return 'Feature'
        return 'História'

    x['Projeto PM'] = x.get('TeamDisplay', '').apply(_portfolio_team_to_pm_project_key)
    x['Produto'] = x['Projeto PM'].apply(_pm_product_label)
    x.loc[x['Produto'].fillna('').astype(str).str.strip().eq(''), 'Produto'] = 'BT Estratégico'
    x['_status_norm'] = x.apply(
        lambda row: _bt_strategic_board_phase(row.get('Status', ''), row.get('TipoNorm', '')),
        axis=1,
    )
    x['Issue Key'] = x['ID'].fillna('').astype(str).str.strip()
    x['TempoStatusDias'] = x['AgingDiasSemAlteracao']
    x['Status PM Elegível'] = False
    x['CamadaFluxo'] = 'Estratégico BT'
    x['NivelHierarquia'] = x['TipoNorm'].apply(_nivel)
    return x[['Issue Key', 'Produto', '_status_norm', 'TempoStatusDias', 'Status PM Elegível', 'CamadaFluxo', 'NivelHierarquia']].copy()


def build_custo_espera_data(
    all_events_df: 'pd.DataFrame',
    custo_hora: float,
    strategic_items_df: 'pd.DataFrame' = None,
    horas_produtivas_dia: float = 8.0,
) -> dict:
    """
    Computes Cost of Delay for queue/waiting phases (Sprint Backlog, Ready for QA, etc.).

    CustoEspera = TempoStatusDias × horas_produtivas_dia × custo_hora

    Uses all_events_df which contains ALL phases (execution + waiting),
    available via pm_portfolio_data['all_events_df'].

    Returns dict with:
      - 'espera_df':    one row per waiting event with CustoEspera, DiasEspera, FaseEspera
      - 'by_phase_df':  aggregate by waiting phase label
      - 'by_product_df': aggregate by product (waiting vs execution days)
      - 'by_issue_df':  top issues by total wait cost
      - 'kpis':         scalar metrics
      - 'has_cost':     bool
    """
    _empty = {
        'espera_df': pd.DataFrame(), 'by_phase_df': pd.DataFrame(),
        'by_product_df': pd.DataFrame(), 'by_issue_df': pd.DataFrame(),
        'by_direction_df': pd.DataFrame(), 'by_direction_product_df': pd.DataFrame(),
        'kpis': {}, 'has_cost': False,
    }

    if (all_events_df is None or all_events_df.empty) and (strategic_items_df is None or strategic_items_df.empty):
        return _empty

    df = all_events_df.copy() if all_events_df is not None else pd.DataFrame()
    _empty_float = pd.Series(index=df.index, dtype='float64')
    _empty_obj = pd.Series(index=df.index, dtype='object')
    df['TempoStatusDias'] = pd.to_numeric(df.get('TempoStatusDias', _empty_float), errors='coerce').fillna(0.0)
    df['Horas PM Elegíveis'] = pd.to_numeric(df.get('Horas PM Elegíveis', _empty_float), errors='coerce').fillna(0.0)
    df['History Created'] = pd.to_datetime(df.get('History Created', _empty_obj), errors='coerce')
    df['Issue Key'] = df.get('Issue Key', pd.Series([''] * len(df), index=df.index)).fillna('').astype(str)
    df['Produto'] = df.get('Produto', pd.Series([''] * len(df), index=df.index)).fillna('').astype(str)
    df['CamadaFluxo'] = 'Operacional PM'
    df['NivelHierarquia'] = 'Issue'

    status_col = 'To Status Norm' if 'To Status Norm' in df.columns else 'To Status'
    df['_status_norm'] = df[status_col].fillna('').astype(str).str.strip() if status_col in df.columns else pd.Series([''] * len(df), index=df.index)
    df['Status PM Elegível'] = df.get('Status PM Elegível', pd.Series([False] * len(df), index=df.index))
    if df['Status PM Elegível'].dtype != bool:
        df['Status PM Elegível'] = _coerce_bool_flag(df['Status PM Elegível'])

    # Waiting = non-execution, non-done, non-cancelled, with time > 0
    df['_is_waiting'] = df['_status_norm'].apply(_pm_is_waiting_status)
    operational_wait_df = df[df['_is_waiting'] & (df['TempoStatusDias'] > 0)].copy()
    strategic_wait_df = _build_strategic_portfolio_wait_frame(strategic_items_df)
    waiting_df = pd.concat([operational_wait_df, strategic_wait_df], ignore_index=True, sort=False)

    if waiting_df.empty:
        return _empty

    taxa_dia = float(custo_hora or 0) * float(horas_produtivas_dia)
    has_cost = taxa_dia > 0

    waiting_df['DiasEspera'] = waiting_df['TempoStatusDias']
    waiting_df['CustoEspera'] = waiting_df['DiasEspera'] * taxa_dia
    waiting_df['FaseEspera'] = waiting_df['_status_norm'].str.title().replace('', 'Desconhecido')
    waiting_df['Direcao'] = waiting_df['_status_norm'].apply(_pm_waiting_direction)

    # ── Execution totals (for efficiency ratio) ───────────────────────────────
    exec_df = df[df['Status PM Elegível'] & (df['TempoStatusDias'] > 0)].copy()
    total_exec_dias = float(exec_df['TempoStatusDias'].sum())
    total_exec_custo = float(exec_df['Horas PM Elegíveis'].sum()) * float(custo_hora or 0)

    total_espera_dias = float(waiting_df['DiasEspera'].sum())
    total_espera_custo = float(waiting_df['CustoEspera'].sum())
    strategic_espera_dias = float(pd.to_numeric(strategic_wait_df.get('TempoStatusDias'), errors='coerce').fillna(0.0).sum()) if not strategic_wait_df.empty else 0.0
    strategic_espera_custo = strategic_espera_dias * taxa_dia
    strategic_itens = int(strategic_wait_df['Issue Key'].nunique()) if not strategic_wait_df.empty else 0
    strategic_wait_enriched = waiting_df[waiting_df.get('CamadaFluxo', '').fillna('').astype(str).eq('Estratégico BT')].copy()
    total_issues_espera = int(waiting_df['Issue Key'].nunique())
    operational_wait_dias = float(pd.to_numeric(operational_wait_df.get('TempoStatusDias'), errors='coerce').fillna(0.0).sum()) if not operational_wait_df.empty else 0.0
    total_dias_operacionais = total_exec_dias + operational_wait_dias
    flow_efficiency = (total_exec_dias / total_dias_operacionais * 100.0) if total_dias_operacionais > 0 else np.nan
    avg_espera_por_issue = (
        waiting_df.groupby('Issue Key')['DiasEspera'].sum().mean()
        if not waiting_df.empty else np.nan
    )

    # ── By waiting phase ──────────────────────────────────────────────────────
    by_phase = (
        waiting_df.groupby('FaseEspera', dropna=False)
        .agg(
            DiasEspera=('DiasEspera', 'sum'),
            CustoEspera=('CustoEspera', 'sum'),
            Ocorrencias=('Issue Key', 'size'),
            Issues=('Issue Key', 'nunique'),
            Camadas=('CamadaFluxo', lambda x: ', '.join(sorted({str(v).strip() for v in x if str(v).strip()}))),
        )
        .reset_index()
        .sort_values('CustoEspera' if has_cost else 'DiasEspera', ascending=False)
    )

    # ── By product: waiting vs execution days ─────────────────────────────────
    wait_by_prod = (
        waiting_df.groupby('Produto', dropna=False)
        .agg(DiasEspera=('DiasEspera', 'sum'), CustoEspera=('CustoEspera', 'sum'))
        .reset_index()
    )
    exec_by_prod = (
        exec_df.groupby('Produto', dropna=False)
        .agg(DiasExecucao=('TempoStatusDias', 'sum'))
        .reset_index()
    ) if not exec_df.empty else pd.DataFrame(columns=['Produto', 'DiasExecucao'])

    by_product = wait_by_prod.merge(exec_by_prod, on='Produto', how='outer').fillna(0)
    by_product['DiasExecucao'] = pd.to_numeric(by_product.get('DiasExecucao'), errors='coerce').fillna(0.0)
    by_product['FlowEfficiency'] = np.where(
        (by_product['DiasExecucao'] + by_product['DiasEspera']) > 0,
        by_product['DiasExecucao'] / (by_product['DiasExecucao'] + by_product['DiasEspera']) * 100.0,
        np.nan,
    )

    # ── By issue ──────────────────────────────────────────────────────────────
    by_issue = (
        waiting_df.groupby(['Issue Key', 'Produto'], dropna=False)
        .agg(
            DiasEspera=('DiasEspera', 'sum'),
            CustoEspera=('CustoEspera', 'sum'),
            FasesEspera=('FaseEspera', lambda x: ', '.join(sorted(set(x)))),
            Ocorrencias=('Issue Key', 'size'),
            Camadas=('CamadaFluxo', lambda x: ', '.join(sorted({str(v).strip() for v in x if str(v).strip()}))),
        )
        .reset_index()
        .sort_values('CustoEspera' if has_cost else 'DiasEspera', ascending=False)
        .reset_index(drop=True)
    )

    # ── By direction (Upstream vs Downstream) ────────────────────────────────
    by_direction = (
        waiting_df.groupby('Direcao', dropna=False)
        .agg(DiasEspera=('DiasEspera', 'sum'), CustoEspera=('CustoEspera', 'sum'),
             Issues=('Issue Key', 'nunique'))
        .reset_index()
    )
    by_direction_product = (
        waiting_df.groupby(['Produto', 'Direcao'], dropna=False)
        .agg(DiasEspera=('DiasEspera', 'sum'), CustoEspera=('CustoEspera', 'sum'))
        .reset_index()
    )

    def _dir_kpi(direction, col):
        row = by_direction[by_direction['Direcao'] == direction]
        return float(row[col].iloc[0]) if not row.empty else 0.0

    upstream_dias = _dir_kpi('Upstream', 'DiasEspera')
    downstream_dias = _dir_kpi('Downstream', 'DiasEspera')
    upstream_custo = _dir_kpi('Upstream', 'CustoEspera')
    downstream_custo = _dir_kpi('Downstream', 'CustoEspera')
    upstream_pct = upstream_dias / total_espera_dias * 100 if total_espera_dias > 0 else np.nan
    downstream_pct = downstream_dias / total_espera_dias * 100 if total_espera_dias > 0 else np.nan

    strategic_by_direction = (
        strategic_wait_enriched.groupby('Direcao', dropna=False)
        .agg(
            DiasEspera=('DiasEspera', 'sum'),
            CustoEspera=('CustoEspera', 'sum'),
            Itens=('Issue Key', 'nunique'),
        )
        .reset_index()
    ) if not strategic_wait_enriched.empty else pd.DataFrame(columns=['Direcao', 'DiasEspera', 'CustoEspera', 'Itens'])

    def _strategic_dir_kpi(direction, col):
        row = strategic_by_direction[strategic_by_direction['Direcao'] == direction]
        if row.empty:
            return 0.0 if col != 'Itens' else 0
        if col == 'Itens':
            return int(row[col].iloc[0])
        return float(row[col].iloc[0])

    strategic_upstream_itens = _strategic_dir_kpi('Upstream', 'Itens')
    strategic_downstream_itens = _strategic_dir_kpi('Downstream', 'Itens')
    strategic_upstream_dias = _strategic_dir_kpi('Upstream', 'DiasEspera')
    strategic_downstream_dias = _strategic_dir_kpi('Downstream', 'DiasEspera')
    strategic_upstream_custo = _strategic_dir_kpi('Upstream', 'CustoEspera')
    strategic_downstream_custo = _strategic_dir_kpi('Downstream', 'CustoEspera')

    return {
        'espera_df': waiting_df,
        'by_phase_df': by_phase,
        'by_product_df': by_product,
        'by_issue_df': by_issue,
        'by_direction_df': by_direction,
        'by_direction_product_df': by_direction_product,
        'kpis': {
            'total_espera_dias': total_espera_dias,
            'total_espera_custo': total_espera_custo,
            'total_exec_dias': total_exec_dias,
            'total_exec_custo': total_exec_custo,
            'flow_efficiency': flow_efficiency,
            'avg_espera_por_issue': avg_espera_por_issue,
            'issues_com_espera': total_issues_espera,
            'strategic_espera_dias': strategic_espera_dias,
            'strategic_espera_custo': strategic_espera_custo,
            'strategic_itens': strategic_itens,
            'strategic_upstream_itens': strategic_upstream_itens,
            'strategic_downstream_itens': strategic_downstream_itens,
            'strategic_upstream_dias': strategic_upstream_dias,
            'strategic_downstream_dias': strategic_downstream_dias,
            'strategic_upstream_custo': strategic_upstream_custo,
            'strategic_downstream_custo': strategic_downstream_custo,
            'taxa_dia': taxa_dia,
            'upstream_dias': upstream_dias,
            'downstream_dias': downstream_dias,
            'upstream_custo': upstream_custo,
            'downstream_custo': downstream_custo,
            'upstream_pct': upstream_pct,
            'downstream_pct': downstream_pct,
        },
        'has_cost': has_cost,
    }


def _build_custo_espera_section(
    all_events_df: 'pd.DataFrame',
    custo_hora: float,
    strategic_items_df: 'pd.DataFrame' = None,
) -> 'html.Div':
    """
    Renders the Cost of Delay section with Upstream vs Downstream analysis:
      - KPI row 1: total dias, custo total, flow efficiency, média/issue
      - KPI row 2: upstream dias/custo/%, downstream dias/custo/%
      - Chart 1: fases de espera coloridas por direção (Upstream / Downstream)
      - Chart 2: Upstream vs Downstream por produto (grouped bars)
      - Chart 3: execução vs espera por produto (stacked)
      - Chart 4: top 15 issues por custo de espera
    """
    data = build_custo_espera_data(all_events_df, custo_hora, strategic_items_df=strategic_items_df)
    kpis = data.get('kpis', {})
    by_phase_df = data.get('by_phase_df', pd.DataFrame())
    by_product_df = data.get('by_product_df', pd.DataFrame())
    by_issue_df = data.get('by_issue_df', pd.DataFrame())
    by_direction_product_df = data.get('by_direction_product_df', pd.DataFrame())

    if not kpis or kpis.get('issues_com_espera', 0) == 0:
        return html.Div()

    has_cost = data.get('has_cost', False)
    fe = kpis.get('flow_efficiency', np.nan)
    fe_str = f'{fe:.1f}%' if not pd.isna(fe) else '—'
    avg_dias = kpis.get('avg_espera_por_issue', np.nan)
    avg_str = f'{avg_dias:.1f}d' if not pd.isna(avg_dias) else '—'

    upstream_pct = kpis.get('upstream_pct', np.nan)
    downstream_pct = kpis.get('downstream_pct', np.nan)
    strategic_itens = int(kpis.get('strategic_itens', 0) or 0)

    def _fmt_r(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return '—'
        return f"R$ {float(v):,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def _fmt_d(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return '—'
        return f"{float(v):,.0f}d"

    def _fmt_pct(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return '—'
        return f"{float(v):.1f}%"

    def _section_heading(title, subtitle='', accent='#0f172a'):
        children = [
            html.H5(title, style={'margin': '0', 'color': accent, 'fontWeight': '700', 'fontSize': '17px'}),
        ]
        if subtitle:
            children.append(html.P(
                subtitle,
                style={'margin': '4px 0 0 0', 'color': '#475569', 'fontSize': '13px', 'lineHeight': '1.4'},
            ))
        return html.Div(children, style={'marginBottom': '10px'})

    def _metric_chip(label, value, accent):
        return html.Div([
            html.Div(label, style={'fontSize': '12px', 'fontWeight': '600', 'color': '#475569', 'marginBottom': '6px'}),
            html.Div(value, style={'fontSize': '24px', 'fontWeight': '800', 'color': '#0f172a', 'lineHeight': '1.15'}),
        ], style={
            'backgroundColor': 'white',
            'border': '1px solid #e2e8f0',
            'borderTop': f'4px solid {accent}',
            'borderRadius': '12px',
            'padding': '14px 16px',
            'minHeight': '106px',
            'display': 'flex',
            'flexDirection': 'column',
            'justifyContent': 'space-between',
            'boxShadow': '0 1px 2px rgba(15, 23, 42, 0.05)',
        })

    def _direction_panel(title, subtitle, accent, bg, metrics):
        metric_blocks = [
            html.Div([
                html.Div(m_label, style={'fontSize': '12px', 'fontWeight': '600', 'color': '#475569', 'marginBottom': '6px'}),
                html.Div(m_value, style={'fontSize': '22px', 'fontWeight': '800', 'color': '#0f172a', 'lineHeight': '1.15'}),
            ], style={
                'backgroundColor': 'rgba(255,255,255,0.82)',
                'border': '1px solid rgba(148,163,184,0.25)',
                'borderRadius': '10px',
                'padding': '12px 14px',
                'minHeight': '92px',
            })
            for m_label, m_value in metrics
        ]
        return html.Div([
            html.Div([
                html.Div(title, style={'fontSize': '18px', 'fontWeight': '800', 'color': accent, 'marginBottom': '4px'}),
                html.Div(subtitle, style={'fontSize': '13px', 'color': '#475569', 'lineHeight': '1.45'}),
            ], style={'marginBottom': '12px'}),
            html.Div(metric_blocks, style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fit, minmax(150px, 1fr))',
                'gap': '10px',
            }),
        ], style={
            'background': bg,
            'border': f'1px solid {accent}',
            'borderLeft': f'8px solid {accent}',
            'borderRadius': '16px',
            'padding': '16px',
            'boxShadow': '0 6px 18px rgba(15, 23, 42, 0.06)',
        })

    overview_cards = html.Div([
        _metric_chip('Dias em espera (total)', _fmt_d(kpis.get('total_espera_dias')), '#1d4ed8'),
        _metric_chip(
            'Custo de espera estimado' if has_cost else 'Dias de espera',
            _fmt_r(kpis.get('total_espera_custo')) if has_cost else _fmt_d(kpis.get('total_espera_dias')),
            '#0f766e',
        ),
        _metric_chip('Flow Efficiency', fe_str, '#7c3aed'),
        _metric_chip('Média dias espera / issue', avg_str, '#ea580c'),
    ], style={
        'display': 'grid',
        'gridTemplateColumns': 'repeat(auto-fit, minmax(200px, 1fr))',
        'gap': '12px',
        'marginBottom': '18px',
    })

    direction_section = html.Div([
        _section_heading(
            'Onde está o atraso',
            'Laranja representa etapas de Upstream. Vermelho representa etapas de Downstream.',
        ),
        html.Div([
            _direction_panel(
                'Upstream',
                'Descoberta, design, definição e preparação antes da entrega para o downstream.',
                '#f59e0b',
                'linear-gradient(180deg, rgba(245,158,11,0.14) 0%, rgba(255,255,255,0.98) 100%)',
                [
                    ('Participação no atraso', _fmt_pct(upstream_pct)),
                    ('Dias em espera', _fmt_d(kpis.get('upstream_dias'))),
                    ('Custo estimado' if has_cost else 'Espera acumulada', _fmt_r(kpis.get('upstream_custo')) if has_cost else _fmt_d(kpis.get('upstream_dias'))),
                ],
            ),
            _direction_panel(
                'Downstream',
                'Backlog downstream, avanço percentual, ready to delivery e etapas posteriores da execução.',
                '#ef4444',
                'linear-gradient(180deg, rgba(239,68,68,0.12) 0%, rgba(255,255,255,0.98) 100%)',
                [
                    ('Participação no atraso', _fmt_pct(downstream_pct)),
                    ('Dias em espera', _fmt_d(kpis.get('downstream_dias'))),
                    ('Custo estimado' if has_cost else 'Espera acumulada', _fmt_r(kpis.get('downstream_custo')) if has_cost else _fmt_d(kpis.get('downstream_dias'))),
                ],
            ),
        ], style={
            'display': 'grid',
            'gridTemplateColumns': 'repeat(auto-fit, minmax(320px, 1fr))',
            'gap': '14px',
            'marginBottom': '18px',
        }),
    ])

    strategic_section = html.Div()
    if strategic_itens > 0:
        strategic_section = html.Div([
            _section_heading(
                'BT Estratégico',
                'Separação da camada estratégica de épicos, features e histórias entre Upstream e Downstream.',
            ),
            html.Div([
                _direction_panel(
                    'BT Estratégico · Upstream',
                    'Itens estratégicos ainda em descoberta, design ou preparação antes do downstream.',
                    '#f59e0b',
                    'linear-gradient(180deg, rgba(245,158,11,0.12) 0%, rgba(255,255,255,0.98) 100%)',
                    [
                        ('Itens em espera', str(int(kpis.get('strategic_upstream_itens', 0) or 0))),
                        ('Dias em espera', _fmt_d(kpis.get('strategic_upstream_dias', 0.0))),
                        ('Custo estimado' if has_cost else 'Espera acumulada', _fmt_r(kpis.get('strategic_upstream_custo', 0.0)) if has_cost else _fmt_d(kpis.get('strategic_upstream_dias', 0.0))),
                    ],
                ),
                _direction_panel(
                    'BT Estratégico · Downstream',
                    'Itens estratégicos já no downstream, incluindo ready to delivery e colunas percentuais de avanço.',
                    '#ef4444',
                    'linear-gradient(180deg, rgba(239,68,68,0.1) 0%, rgba(255,255,255,0.98) 100%)',
                    [
                        ('Itens em espera', str(int(kpis.get('strategic_downstream_itens', 0) or 0))),
                        ('Dias em espera', _fmt_d(kpis.get('strategic_downstream_dias', 0.0))),
                        ('Custo estimado' if has_cost else 'Espera acumulada', _fmt_r(kpis.get('strategic_downstream_custo', 0.0)) if has_cost else _fmt_d(kpis.get('strategic_downstream_dias', 0.0))),
                    ],
                ),
            ], style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fit, minmax(320px, 1fr))',
                'gap': '14px',
                'marginBottom': '18px',
            }),
        ])

    notes = []
    if not has_cost:
        notes.append(html.P(
            'Taxas de custo não configuradas — valores em dias. '
            'Configure FLOW_PMO_PM_COST_PER_HOUR_MAP para custo monetário.',
            style={'color': '#8a6d3b', 'fontSize': '13px', 'marginBottom': '8px'},
        ))
    notes.append(html.P(
        'Flow Efficiency = dias em execução / (dias em execução + dias em espera). '
        'Benchmarks de referência: times de alto desempenho ≥ 40%; típico 15–25%. '
        'A camada operacional usa histórico PM; a camada estratégica BT usa aging do status atual '
        '(dias desde a última mudança de status) para épicos/features/histórias. '
        'Flow Efficiency continua baseada apenas na camada operacional.',
        style={'color': '#555', 'fontSize': '13px', 'marginBottom': '8px'},
    ))

    value_col = 'CustoEspera' if has_cost else 'DiasEspera'
    value_label = 'Custo de Espera (R$)' if has_cost else 'Dias de Espera'

    _dir_colors = {'Upstream': '#f59e0b', 'Downstream': '#ef4444'}

    # ── Chart 1: Por fase — colorida por direção ──────────────────────────────
    fig_phase = go.Figure()
    if not by_phase_df.empty:
        _phase_plot = by_phase_df.copy()
        _phase_plot['Direcao'] = _phase_plot['FaseEspera'].apply(
            lambda f: _pm_waiting_direction(str(f).lower())
        )
        fig_phase = px.bar(
            _phase_plot.sort_values(value_col, ascending=False),
            x='FaseEspera', y=value_col,
            color='Direcao',
            color_discrete_map=_dir_colors,
            title='Custo de espera por fase — Upstream vs Downstream',
            text=value_col,
            hover_data={'Issues': True, 'Ocorrencias': True, 'DiasEspera': ':.1f', 'Direcao': True, 'Camadas': True},
            labels={value_col: value_label, 'FaseEspera': '', 'Direcao': 'Direção',
                    'Issues': 'Issues únicas', 'Ocorrencias': 'Ocorrências', 'Camadas': 'Camada'},
        )
        fig_phase.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_phase.update_layout(
            height=400, yaxis_title=value_label, xaxis_title='',
            margin=dict(t=50, b=80, l=60, r=20), xaxis_tickangle=-30,
            legend=dict(orientation='h', yanchor='bottom', y=-0.35, title=''),
        )

    # ── Chart 2: Upstream vs Downstream por produto (grouped) ────────────────
    fig_dir_prod = go.Figure()
    if not by_direction_product_df.empty:
        fig_dir_prod = px.bar(
            by_direction_product_df,
            x='Produto', y=value_col, color='Direcao',
            barmode='group',
            color_discrete_map=_dir_colors,
            title='Upstream vs Downstream por produto',
            text=value_col,
            labels={value_col: value_label, 'Produto': '', 'Direcao': 'Direção'},
        )
        fig_dir_prod.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_dir_prod.update_layout(
            height=380, yaxis_title=value_label, xaxis_title='',
            margin=dict(t=50, b=60, l=60, r=20),
            legend=dict(orientation='h', yanchor='bottom', y=-0.25, title=''),
        )

    # ── Chart 3: Por produto — execução vs espera total (stacked) ────────────
    fig_product = go.Figure()
    if not by_product_df.empty:
        prod_rows = []
        for _, row in by_product_df.iterrows():
            prod_rows.append({'Produto': row['Produto'], 'Dias': row.get('DiasExecucao', 0), 'Tipo': 'Execução'})
            prod_rows.append({'Produto': row['Produto'], 'Dias': row.get('DiasEspera', 0), 'Tipo': 'Espera (fila)'})
        fig_product = px.bar(
            pd.DataFrame(prod_rows),
            x='Produto', y='Dias', color='Tipo', barmode='stack',
            title='Dias por produto: execução vs. espera total',
            color_discrete_map={'Execução': '#2ca02c', 'Espera (fila)': '#d62728'},
        )
        fig_product.update_layout(
            height=380, yaxis_title='Dias', xaxis_title='',
            margin=dict(t=50, b=60, l=60, r=20),
            legend=dict(orientation='h', yanchor='bottom', y=-0.25),
        )

    # ── Chart 4: Top 15 issues por custo de espera ───────────────────────────
    issues_graph = html.Div()
    if not by_issue_df.empty:
        top15 = by_issue_df.head(15).copy()
        top15['_label'] = top15['Issue Key'] + ' (' + top15['Produto'] + ')'
        fig_issues = px.bar(
            top15,
            x=value_col, y='_label',
            orientation='h',
            title='Top 15 issues por custo de espera',
            color=value_col,
            color_continuous_scale='Oranges',
            text=value_col,
            hover_data={'FasesEspera': True, 'DiasEspera': ':.1f', '_label': False},
            labels={value_col: value_label, '_label': '', 'FasesEspera': 'Fases', 'DiasEspera': 'Dias'},
        )
        fig_issues.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_issues.update_layout(
            height=max(300, len(top15) * 28 + 80),
            xaxis_title=value_label,
            yaxis=dict(autorange='reversed'),
            margin=dict(t=50, b=60, l=220, r=80),
            coloraxis_showscale=False,
        )
        issues_graph = dcc.Graph(figure=fig_issues)

    return html.Div([
        html.H4('Custo de Espera (Cost of Delay)', style={'textAlign': 'left', 'marginTop': '22px', 'marginBottom': '10px'}),
        html.Div([
            html.Span('Upstream', style={
                'display': 'inline-block', 'padding': '6px 10px', 'borderRadius': '999px',
                'backgroundColor': '#fef3c7', 'color': '#92400e', 'fontWeight': '700',
                'fontSize': '12px', 'marginRight': '8px',
            }),
            html.Span(
                'Discovery, design, definição e preparação antes da entrega downstream.',
                style={'fontSize': '13px', 'color': '#475569', 'marginRight': '18px'},
            ),
            html.Span('Downstream', style={
                'display': 'inline-block', 'padding': '6px 10px', 'borderRadius': '999px',
                'backgroundColor': '#fee2e2', 'color': '#991b1b', 'fontWeight': '700',
                'fontSize': '12px', 'marginRight': '8px',
            }),
            html.Span(
                'Ready to delivery, backlog downstream, percentuais de avanço e etapas posteriores.',
                style={'fontSize': '13px', 'color': '#475569'},
            ),
        ], style={
            'display': 'flex',
            'gap': '6px',
            'flexWrap': 'wrap',
            'alignItems': 'center',
            'marginBottom': '10px',
        }),
        html.Div(notes, style={'marginBottom': '10px'}),
        overview_cards,
        direction_section,
        strategic_section,
        html.Div([
            html.Div([dcc.Graph(figure=fig_phase)], style={'flex': '1', 'minWidth': '340px'}),
            html.Div([dcc.Graph(figure=fig_dir_prod)], style={'flex': '1', 'minWidth': '340px'}),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap', 'marginTop': '8px'}),
        html.Div([
            html.Div([dcc.Graph(figure=fig_product)], style={'flex': '1', 'minWidth': '340px'}),
            html.Div([issues_graph], style={'flex': '1', 'minWidth': '340px'}),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap', 'marginTop': '12px'}),
    ])


def _coerce_bool_flag(series: 'pd.Series') -> 'pd.Series':
    """Normalise rework flag columns that may arrive as bool, int 0/1 or string 'True'/'False'."""
    if hasattr(series, 'dtype') and series.dtype == bool:
        return series
    return series.astype(str).str.strip().str.lower().isin({'true', '1', 'yes'})


def build_custo_retrabalho_data(events_df: 'pd.DataFrame', worklog_df: 'pd.DataFrame') -> dict:
    """
    Computes rework cost from PM event log and CAPEX worklogs.

    Rework events are rows in events_df where any of:
      Backward Move, QA Return, Reopen Transition  is True.

    PM-estimated rework cost = sum(Custo PM Estimado) for rework events.

    Real rework cost (worklog-based): for each issue with a rework event, finds the
    EARLIEST rework event timestamp and sums all worklogs for that issue whose
    'Data do Apontamento das Horas' >= that timestamp.

    Returns dict with:
      - 'rework_ev_df':   rework event rows with CustoEstimado, HorasEstimadas, tipo_retrabalho
      - 'kpis':           dict with scalar KPIs
      - 'by_type_df':     cost per rework type (Backward Move / QA Return / Reopen)
      - 'by_issue_df':    cost per issue (top issues by rework cost)
      - 'has_cost':       bool
    """
    _empty = {'rework_ev_df': pd.DataFrame(), 'kpis': {}, 'by_type_df': pd.DataFrame(),
              'by_issue_df': pd.DataFrame(), 'has_cost': False}

    if events_df is None or events_df.empty or 'Issue Key' not in events_df.columns:
        return _empty

    ev = events_df.copy()
    ev['Horas PM Elegíveis'] = pd.to_numeric(ev.get('Horas PM Elegíveis'), errors='coerce').fillna(0.0)
    ev['Custo PM Estimado'] = pd.to_numeric(ev.get('Custo PM Estimado'), errors='coerce').fillna(0.0)
    ev['History Created'] = pd.to_datetime(ev.get('History Created'), errors='coerce')
    ev['Produto'] = ev.get('Produto', pd.Series([''] * len(ev))).fillna('').astype(str)

    # Coerce rework flag columns (may be bool, int, or string)
    rework_flag_cols = {
        'Backward Move': 'Backward Move',
        'QA Return': 'QA Return',
        'Reopen Transition': 'Reopen',
    }
    masks = []
    for col, _label in rework_flag_cols.items():
        if col in ev.columns:
            ev[col] = _coerce_bool_flag(ev[col])
            masks.append(ev[col])
        else:
            ev[col] = False

    if not masks:
        return _empty

    rework_mask = masks[0]
    for m in masks[1:]:
        rework_mask = rework_mask | m

    # Assign rework type label (priority: QA Return > Reopen > Backward Move)
    def _tipo(row):
        if row.get('QA Return', False):
            return 'QA Return'
        if row.get('Reopen Transition', False):
            return 'Reopen'
        if row.get('Backward Move', False):
            return 'Backward Move'
        return 'Outro'

    ev['TipoRetrabalho'] = ev.apply(_tipo, axis=1)

    rework_ev = ev[rework_mask].copy()
    normal_ev = ev[~rework_mask].copy()

    if rework_ev.empty:
        return _empty

    total_pm_cost = float(ev['Custo PM Estimado'].sum())
    rework_pm_cost = float(rework_ev['Custo PM Estimado'].sum())
    normal_pm_cost = float(normal_ev['Custo PM Estimado'].sum())
    rework_pm_hours = float(rework_ev['Horas PM Elegíveis'].sum())
    n_issues_rework = int(rework_ev['Issue Key'].nunique())
    rework_pct = (rework_pm_cost / total_pm_cost * 100.0) if total_pm_cost > 0 else np.nan

    # ── By rework type ────────────────────────────────────────────────────────
    by_type = (
        rework_ev.groupby('TipoRetrabalho', dropna=False)
        .agg(
            CustoEstimado=('Custo PM Estimado', 'sum'),
            HorasEstimadas=('Horas PM Elegíveis', 'sum'),
            Ocorrencias=('Issue Key', 'size'),
            Issues=('Issue Key', 'nunique'),
        )
        .reset_index()
        .sort_values('CustoEstimado', ascending=False)
    )

    # ── Real rework cost via worklog join ─────────────────────────────────────
    real_rework_cost = 0.0
    rework_real_by_issue = pd.DataFrame()
    has_cost = rework_pm_cost > 0

    if worklog_df is not None and not worklog_df.empty and 'Data do Apontamento das Horas' in worklog_df.columns:
        wl = worklog_df[['Issue Key', 'Data do Apontamento das Horas', 'Horas', 'Custo Real Apontado (R$)']].copy()
        wl['Data do Apontamento das Horas'] = pd.to_datetime(wl['Data do Apontamento das Horas'], errors='coerce')
        wl['Custo Real Apontado (R$)'] = pd.to_numeric(wl.get('Custo Real Apontado (R$)'), errors='coerce').fillna(0.0)
        wl['Horas'] = pd.to_numeric(wl.get('Horas'), errors='coerce').fillna(0.0)
        wl = wl[wl['Data do Apontamento das Horas'].notna()].copy()

        if not wl.empty:
            # Earliest rework timestamp per issue
            rework_start = (
                rework_ev[rework_ev['History Created'].notna()]
                .groupby('Issue Key', dropna=False)['History Created']
                .min()
                .reset_index()
                .rename(columns={'History Created': '_rework_start'})
            )
            if not rework_start.empty:
                wl_rw = wl.merge(rework_start, on='Issue Key', how='inner')
                wl_rw = wl_rw[wl_rw['Data do Apontamento das Horas'] >= wl_rw['_rework_start']].copy()
                if not wl_rw.empty:
                    real_rework_cost = float(wl_rw['Custo Real Apontado (R$)'].sum())
                    has_cost = has_cost or (real_rework_cost > 0)
                    rework_real_by_issue = (
                        wl_rw.groupby('Issue Key', dropna=False)
                        .agg(
                            CustoRealRetrabalho=('Custo Real Apontado (R$)', 'sum'),
                            HorasReaisRetrabalho=('Horas', 'sum'),
                        )
                        .reset_index()
                    )

    # ── Per-issue summary ─────────────────────────────────────────────────────
    by_issue = (
        rework_ev.groupby(['Issue Key', 'Produto'], dropna=False)
        .agg(
            CustoEstimado=('Custo PM Estimado', 'sum'),
            HorasEstimadas=('Horas PM Elegíveis', 'sum'),
            Ocorrencias=('Issue Key', 'size'),
            TiposRetrabalho=('TipoRetrabalho', lambda x: ', '.join(sorted(set(x)))),
        )
        .reset_index()
    )
    if not rework_real_by_issue.empty:
        by_issue = by_issue.merge(rework_real_by_issue, on='Issue Key', how='left')
        by_issue['CustoRealRetrabalho'] = pd.to_numeric(by_issue.get('CustoRealRetrabalho'), errors='coerce').fillna(0.0)
        by_issue['HorasReaisRetrabalho'] = pd.to_numeric(by_issue.get('HorasReaisRetrabalho'), errors='coerce').fillna(0.0)
    else:
        by_issue['CustoRealRetrabalho'] = 0.0
        by_issue['HorasReaisRetrabalho'] = 0.0

    by_issue = by_issue.sort_values('CustoEstimado', ascending=False).reset_index(drop=True)

    kpis = {
        'issues_com_retrabalho': n_issues_rework,
        'custo_pm_retrabalho': rework_pm_cost,
        'custo_pm_normal': normal_pm_cost,
        'custo_pm_total': total_pm_cost,
        'horas_pm_retrabalho': rework_pm_hours,
        'pct_retrabalho': rework_pct,
        'custo_real_retrabalho': real_rework_cost,
        'has_real': real_rework_cost > 0,
    }

    return {
        'rework_ev_df': rework_ev,
        'kpis': kpis,
        'by_type_df': by_type,
        'by_issue_df': by_issue,
        'has_cost': has_cost,
    }


def _build_custo_retrabalho_section(events_df: 'pd.DataFrame', worklog_df: 'pd.DataFrame') -> 'html.Div':
    """
    Renders the rework cost section:
      - KPI cards row (issues, custo retrabalho, % do total, custo real)
      - Chart 1: Stacked bar — rework vs. non-rework PM cost
      - Chart 2: Rework cost by type (Backward Move / QA Return / Reopen)
      - Chart 3: Top 15 issues by rework estimated cost
    """
    data = build_custo_retrabalho_data(events_df, worklog_df)
    kpis = data.get('kpis', {})
    by_type_df = data.get('by_type_df', pd.DataFrame())
    by_issue_df = data.get('by_issue_df', pd.DataFrame())

    if not kpis or kpis.get('issues_com_retrabalho', 0) == 0:
        return html.Div()

    has_cost = data.get('has_cost', False)
    has_real = bool(kpis.get('has_real', False))
    value_label = 'Custo (R$)' if has_cost else 'Horas'

    pct = kpis.get('pct_retrabalho', np.nan)
    pct_str = f"{pct:.1f}%" if not pd.isna(pct) else '—'

    def _fmt(v, is_money=True):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return '—'
        if is_money and has_cost:
            return f"R$ {float(v):,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"{float(v):,.1f}h"

    # ── KPI cards ─────────────────────────────────────────────────────────────
    kpi_cards = html.Div([
        _portfolio_metric_card('Issues com retrabalho', str(kpis.get('issues_com_retrabalho', 0))),
        _portfolio_metric_card(
            'Custo estimado retrabalho',
            _fmt(kpis.get('custo_pm_retrabalho'), is_money=True),
        ),
        _portfolio_metric_card('% do custo total', pct_str),
        _portfolio_metric_card(
            'Custo real retrabalho' if has_real else 'Horas de retrabalho',
            _fmt(kpis.get('custo_real_retrabalho') if has_real else kpis.get('horas_pm_retrabalho'), is_money=has_real),
        ),
    ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap', 'marginBottom': '12px'})

    # ── Chart 1: Retrabalho vs. normal (stacked) ──────────────────────────────
    rw_val = kpis.get('custo_pm_retrabalho', 0) if has_cost else kpis.get('horas_pm_retrabalho', 0)
    nm_val = kpis.get('custo_pm_normal', 0) if has_cost else 0.0

    stack_df = pd.DataFrame([
        {'Categoria': 'Retrabalho', value_label: rw_val},
        {'Categoria': 'Execução normal', value_label: nm_val},
    ])
    fig_stack = px.bar(
        stack_df, x='Categoria', y=value_label,
        color='Categoria',
        title='Custo estimado: retrabalho vs. execução normal',
        color_discrete_map={'Retrabalho': '#d62728', 'Execução normal': '#2ca02c'},
        text=value_label,
    )
    fig_stack.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
    fig_stack.update_layout(
        height=340, showlegend=False,
        yaxis_title=value_label, xaxis_title='',
        margin=dict(t=50, b=60, l=60, r=20),
    )

    # ── Chart 2: Custo por tipo de retrabalho ────────────────────────────────
    fig_type = go.Figure()
    if not by_type_df.empty:
        col_y = 'CustoEstimado' if has_cost else 'HorasEstimadas'
        fig_type = px.bar(
            by_type_df, x='TipoRetrabalho', y=col_y,
            color='TipoRetrabalho',
            title='Custo de retrabalho por tipo de evento',
            text=col_y,
            color_discrete_map={
                'QA Return': '#ff7f0e',
                'Backward Move': '#d62728',
                'Reopen': '#9467bd',
                'Outro': '#aaa',
            },
        )
        fig_type.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_type.update_layout(
            height=340, showlegend=False,
            yaxis_title=value_label, xaxis_title='',
            margin=dict(t=50, b=60, l=60, r=20),
        )

    # ── Chart 3: Top 15 issues por custo de retrabalho ───────────────────────
    issues_graph = html.Div()
    if not by_issue_df.empty:
        top15 = by_issue_df.head(15).copy()
        top15['_label'] = top15['Issue Key'] + ' (' + top15['Produto'] + ')'
        col_x = 'CustoEstimado' if has_cost else 'HorasEstimadas'
        fig_issues = px.bar(
            top15, x=col_x, y='_label',
            orientation='h',
            title='Top 15 issues por custo de retrabalho estimado',
            color=col_x,
            color_continuous_scale='Reds',
            text=col_x,
            hover_data={'TiposRetrabalho': True, 'Ocorrencias': True, '_label': False},
            labels={col_x: value_label, '_label': '', 'TiposRetrabalho': 'Tipo', 'Ocorrencias': 'Eventos'},
        )
        fig_issues.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_issues.update_layout(
            height=max(300, len(top15) * 28 + 80),
            xaxis_title=value_label,
            yaxis=dict(autorange='reversed'),
            margin=dict(t=50, b=60, l=220, r=80),
            coloraxis_showscale=False,
        )
        issues_graph = dcc.Graph(figure=fig_issues)

    notes = []
    if not has_cost:
        notes.append(html.P(
            'Taxas de custo não configuradas — valores em horas. Configure FLOW_PMO_PM_COST_PER_HOUR_MAP para custo monetário.',
            style={'color': '#8a6d3b', 'fontSize': '13px', 'marginBottom': '8px'}
        ))
    if has_real:
        notes.append(html.P(
            f"Custo real de retrabalho (worklogs após evento de retrabalho): {_fmt(kpis.get('custo_real_retrabalho'))}",
            style={'color': '#333', 'fontSize': '13px', 'marginBottom': '8px'}
        ))

    return html.Div([
        html.H4('Custo de Retrabalho', style={'textAlign': 'left', 'marginTop': '22px'}),
        html.Div(notes),
        kpi_cards,
        html.Div([
            html.Div([dcc.Graph(figure=fig_stack)], style={'flex': '1', 'minWidth': '280px'}),
            html.Div([dcc.Graph(figure=fig_type)], style={'flex': '1', 'minWidth': '280px'}),
        ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap'}),
        html.Div([issues_graph], style={'marginTop': '12px'}),
    ])


def _build_capex_worklog_fact(start_ts, end_ts, portfolio_scope_df, project_value=None, responsavel=None) -> dict:
    columns = [
        'Data do Apontamento',
        'MesCompetencia',
        'Pessoa',
        'Projeto Jira',
        'Projeto PM',
        'Produto',
        'AssetID',
        'Descrição do Ativo',
        'Tipo do Ativo',
        'Portfolio Team',
        'Issue Key',
        'Horas',
        'Atividade Desenvolvida',
        'Atividade Desenvolvida Normalizada',
        'ConfidenceScore',
        'Origem Horas',
        'Fonte Vínculo',
        'Fonte Taxa',
        'Custo Hora Aplicado (R$)',
        'Custo Real Apontado (R$)',
    ]
    empty_df = pd.DataFrame(columns=columns)

    capex_snapshot, raw_df, _summary_df, capex_error = get_capex_snapshot()
    if capex_error:
        return {
            'available': False,
            'error': capex_error,
            'worklog_df': empty_df,
            'snapshot': capex_snapshot or {},
        }
    if raw_df is None or raw_df.empty:
        return {
            'available': False,
            'error': 'Base CAPEX por worklog indisponível ou vazia.',
            'worklog_df': empty_df,
            'snapshot': capex_snapshot or {},
        }

    cost_model_snapshot = build_portfolio_cost_model_snapshot(portfolio_scope_df, start_ts, end_ts)
    product_rates_df = cost_model_snapshot.get('product_rates_df', pd.DataFrame()) if isinstance(cost_model_snapshot, dict) else pd.DataFrame()
    model_kpis = cost_model_snapshot.get('kpis', {}) if isinstance(cost_model_snapshot, dict) else {}
    person_rate_map = _build_capex_person_rate_map(cost_model_snapshot)
    product_rate_map = {}
    if product_rates_df is not None and not product_rates_df.empty:
        for row in product_rates_df.to_dict(orient='records'):
            project_key = _canonical_pm_product_key(row.get('Projeto PM'))
            if not project_key:
                continue
            try:
                product_rate_map[project_key] = float(row.get('Custo Hora Produto (R$)', 0) or 0)
            except Exception:
                continue
    global_rate = float(model_kpis.get('Custo Hora Carregado', 0) or 0)

    x = raw_df.copy()
    x['Data do Apontamento'] = pd.to_datetime(x.get('Data do Apontamento das Horas'), errors='coerce')
    x['Horas'] = pd.to_numeric(x.get('Horas'), errors='coerce').fillna(0.0)
    x['ConfidenceScore'] = pd.to_numeric(x.get('ConfidenceScore'), errors='coerce').fillna(0.0)
    x['Pessoa'] = x.get('Colaborador', '').apply(_canonical_person_name)
    x['Projeto Jira'] = x.get('Projeto Jira', '').fillna('').astype(str).str.strip().str.upper()
    x['Projeto PM'] = x['Projeto Jira'].apply(_canonical_pm_product_key)
    x['Produto'] = x['Projeto PM'].apply(_pm_product_label)
    x['Issue Key'] = x.get('Issue Key', '').apply(_pm_clean_issue_key)
    x['AssetID'] = x.get('ID do Projeto', '').apply(_pm_clean_issue_key)
    x['Descrição do Ativo'] = x.get('Descrição do Ativo', '').fillna('').astype(str).str.strip()
    x['Tipo do Ativo'] = x.get('Tipo do Ativo', '').fillna('').astype(str).str.strip()
    x['Atividade Desenvolvida'] = x.get('Atividade Desenvolvida', '').fillna('').astype(str).str.strip()
    x['Atividade Desenvolvida Normalizada'] = x.get('Atividade Desenvolvida Normalizada', '').fillna('').astype(str).str.strip()
    x['Origem Horas'] = x.get('Origem Horas', '').fillna('').astype(str).str.strip()
    x['Fonte Vínculo'] = np.where(x['AssetID'].ne(''), 'CAPEX', 'NaoMapeado')
    x['Portfolio Team'] = ''

    period_start = pd.to_datetime(start_ts)
    period_end_exclusive = pd.to_datetime(end_ts) + pd.Timedelta(days=1)
    x = x[
        x['Data do Apontamento'].notna()
        & (x['Data do Apontamento'] >= period_start)
        & (x['Data do Apontamento'] < period_end_exclusive)
        & (x['Horas'] > 0)
    ].copy()
    if x.empty:
        return {
            'available': False,
            'error': 'Sem worklogs CAPEX no período selecionado.',
            'worklog_df': empty_df,
            'snapshot': capex_snapshot or {},
        }

    portfolio_asset_lookup = _build_capex_portfolio_asset_lookup(portfolio_scope_df)
    if portfolio_asset_lookup:
        fallback_rows = []
        for asset_id, meta in portfolio_asset_lookup.items():
            fallback_rows.append({
                'AssetID': asset_id,
                'Descrição do Ativo Fallback': meta.get('Descrição do Ativo', ''),
                'Tipo do Ativo Fallback': meta.get('Tipo do Ativo', ''),
                'Portfolio Team Fallback': meta.get('Portfolio Team', ''),
                'Projeto PM Fallback': meta.get('Projeto PM', ''),
            })
        portfolio_assets_df = pd.DataFrame(fallback_rows)
        if not portfolio_assets_df.empty:
            x = x.merge(portfolio_assets_df, how='left', on='AssetID')
            x['Descrição do Ativo'] = x['Descrição do Ativo'].where(
                x['Descrição do Ativo'].astype(str).str.strip().ne(''),
                x['Descrição do Ativo Fallback']
            )
            x['Tipo do Ativo'] = x['Tipo do Ativo'].where(
                x['Tipo do Ativo'].astype(str).str.strip().ne(''),
                x['Tipo do Ativo Fallback']
            )
            x['Portfolio Team'] = x['Portfolio Team Fallback'].fillna('').astype(str).str.strip()
            missing_project = x['Projeto PM'].astype(str).str.strip().eq('')
            x.loc[missing_project, 'Projeto PM'] = x.loc[missing_project, 'Projeto PM Fallback'].fillna('').astype(str).str.strip()
            x['Produto'] = x['Projeto PM'].apply(_pm_product_label)
            x.drop(
                columns=[
                    'Descrição do Ativo Fallback',
                    'Tipo do Ativo Fallback',
                    'Portfolio Team Fallback',
                    'Projeto PM Fallback',
                ],
                inplace=True,
                errors='ignore',
            )

    specs = _pm_portfolio_selected_specs(project_value)
    selected_projects = {spec['project_key'] for spec in specs}
    if selected_projects:
        x = x[x['Projeto PM'].isin(selected_projects)].copy()

    alias_index = _load_person_alias_index()
    selected_people = set(_normalize_responsavel_filter_values(responsavel, alias_index=alias_index, canonicalize=True))
    if selected_people:
        x = x[x['Pessoa'].isin(selected_people)].copy()

    if x.empty:
        return {
            'available': False,
            'error': 'Sem worklogs CAPEX compatíveis com os filtros atuais.',
            'worklog_df': empty_df,
            'snapshot': capex_snapshot or {},
        }

    person_rates = x['Pessoa'].map(person_rate_map)
    product_rates = x['Projeto PM'].map(product_rate_map)
    x['Custo Hora Aplicado (R$)'] = person_rates.fillna(product_rates).fillna(global_rate).astype(float)
    x['Fonte Taxa'] = np.where(
        person_rates.notna(),
        'Pessoa',
        np.where(product_rates.notna(), 'Produto', np.where(global_rate > 0, 'Global', 'Indisponível'))
    )
    x['Custo Real Apontado (R$)'] = x['Horas'] * x['Custo Hora Aplicado (R$)']

    keep_cols = [col for col in columns if col in x.columns]
    worklog_df = x[keep_cols].copy()
    return {
        'available': not worklog_df.empty,
        'error': '',
        'worklog_df': worklog_df,
        'snapshot': capex_snapshot or {},
        'cost_model': cost_model_snapshot if isinstance(cost_model_snapshot, dict) else {},
    }


def _capex_project_key(project_value, issue_key='') -> str:
    project_key = _canonical_pm_product_key(project_value)
    if project_key:
        return project_key
    issue_text = str(issue_key or '').strip().upper()
    if '-' in issue_text:
        return _canonical_pm_product_key(issue_text.split('-', 1)[0])
    return ''


def _capex_asset_key(row: dict | pd.Series) -> str:
    for candidate in ('ID do Projeto', 'Feature ID', 'Epic ID', 'Parent ID'):
        cleaned = _pm_clean_issue_key(row.get(candidate))
        if cleaned:
            return cleaned
    return ''


def _capex_prepare_worklog_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    df = raw_df.copy()
    df['Data do Apontamento das Horas'] = pd.to_datetime(df.get('Data do Apontamento das Horas'), errors='coerce')
    df['Horas'] = pd.to_numeric(df.get('Horas'), errors='coerce').fillna(0)
    df['ConfidenceScore'] = pd.to_numeric(df.get('ConfidenceScore'), errors='coerce')
    for col in [
        'ID do Projeto', 'Descrição do Ativo', 'Tipo do Ativo', 'Colaborador', 'Atividade Desenvolvida',
        'Origem Horas', 'Issue Key', 'Projeto Jira', 'Epic ID', 'Feature ID', 'Parent ID', 'Worklog ID',
    ]:
        if col not in df.columns:
            df[col] = ''
        df[col] = df[col].fillna('').astype(str).str.strip()

    alias_index = _load_person_alias_index()
    df['Pessoa'] = df['Colaborador'].apply(lambda value: _canonical_person_name(value, alias_index=alias_index))
    df['Projeto PM'] = df.apply(
        lambda row: _capex_project_key(row.get('Projeto Jira'), row.get('Issue Key')),
        axis=1,
    )
    df['Produto'] = df['Projeto PM'].apply(_pm_product_label)
    df['AssetID'] = df.apply(_capex_asset_key, axis=1)
    df['Descrição do Ativo'] = df['Descrição do Ativo'].fillna('').astype(str).str.strip()
    df['Tipo do Ativo'] = df['Tipo do Ativo'].fillna('').astype(str).str.strip()
    df['Issue Key'] = df['Issue Key'].apply(_pm_clean_issue_key)
    df = df[df['Data do Apontamento das Horas'].notna() & (df['Horas'] > 0)].copy()
    return df


def build_worklog_cost_fact(start_ts, end_ts, portfolio_scope_df=None, project_value=None, responsavel=None) -> dict:
    snapshot, raw_df, _summary_df, error = get_capex_snapshot()
    if error:
        return {
            'available': False,
            'error': error,
            'df': pd.DataFrame(),
            'scoped_df': pd.DataFrame(),
            'cost_model': {},
        }
    if raw_df is None or raw_df.empty:
        return {
            'available': False,
            'error': 'Base CAPEX raw indisponível para monetização por worklog.',
            'df': pd.DataFrame(),
            'scoped_df': pd.DataFrame(),
            'cost_model': {},
        }

    df = _capex_prepare_worklog_df(raw_df)
    if df.empty:
        return {
            'available': False,
            'error': 'Base CAPEX raw sem apontamentos válidos.',
            'df': pd.DataFrame(),
            'scoped_df': pd.DataFrame(),
            'cost_model': {},
        }

    period_start = pd.to_datetime(start_ts)
    period_end = pd.to_datetime(end_ts)
    df = df[
        (df['Data do Apontamento das Horas'] >= period_start)
        & (df['Data do Apontamento das Horas'] <= period_end)
    ].copy()

    selected_project = _canonical_pm_product_key(project_value)
    if selected_project:
        df = df[df['Projeto PM'] == selected_project].copy()

    selected_people = set(_normalize_responsavel_filter_values(responsavel, alias_index=_load_person_alias_index(), canonicalize=True))
    if selected_people:
        df = df[df['Pessoa'].isin(selected_people)].copy()

    cost_model = build_portfolio_cost_model_snapshot(
        portfolio_scope_df if isinstance(portfolio_scope_df, pd.DataFrame) else pd.DataFrame(),
        start_ts,
        end_ts,
    )
    team_df = cost_model.get('team_df', pd.DataFrame()).copy() if isinstance(cost_model, dict) else pd.DataFrame()
    product_rates_df = cost_model.get('product_rates_df', pd.DataFrame()).copy() if isinstance(cost_model, dict) else pd.DataFrame()
    model_kpis = cost_model.get('kpis', {}) if isinstance(cost_model, dict) else {}

    person_rate_map = {}
    person_bu_map = {}
    person_role_map = {}
    if team_df is not None and not team_df.empty:
        for row in team_df.to_dict(orient='records'):
            person = str(row.get('Pessoa') or '').strip()
            if not person:
                continue
            person_rate_map[person] = float(row.get('Custo Hora Pessoa (R$)', 0) or 0)
            person_bu_map[person] = str(row.get('BU') or '').strip()
            person_role_map[person] = str(row.get('Papel') or '').strip()

    product_rate_map = {}
    if product_rates_df is not None and not product_rates_df.empty:
        for row in product_rates_df.to_dict(orient='records'):
            canonical_key = _canonical_pm_product_key(row.get('Projeto PM'))
            if not canonical_key:
                continue
            product_rate_map[canonical_key] = float(row.get('Custo Hora Produto (R$)', 0) or 0)

    global_rate = float(model_kpis.get('Custo Hora Carregado', 0) or 0)

    def _resolve_rate(row):
        person = str(row.get('Pessoa') or '').strip()
        product_key = str(row.get('Projeto PM') or '').strip()
        person_rate = float(person_rate_map.get(person, 0) or 0)
        if person_rate > 0:
            return person_rate, 'Pessoa'
        product_rate = float(product_rate_map.get(product_key, 0) or 0)
        if product_rate > 0:
            return product_rate, 'Produto'
        if global_rate > 0:
            return global_rate, 'Global'
        return 0.0, 'Indisponível'

    rate_resolution = df.apply(_resolve_rate, axis=1, result_type='expand')
    df['Taxa Hora Aplicada (R$)'] = pd.to_numeric(rate_resolution[0], errors='coerce').fillna(0)
    df['Fonte Taxa'] = rate_resolution[1].fillna('Indisponível').astype(str)
    df['Custo Real (R$)'] = df['Horas'] * df['Taxa Hora Aplicada (R$)']
    df['BU'] = df['Pessoa'].map(person_bu_map).fillna('')
    df['Papel'] = df['Pessoa'].map(person_role_map).fillna('')
    missing_bu = df['BU'].astype(str).str.strip().eq('')
    if missing_bu.any():
        bu_index = _load_person_bu_map()
        df.loc[missing_bu, 'BU'] = df.loc[missing_bu, 'Pessoa'].apply(lambda value: _person_bu(value, bu_index=bu_index))
    missing_role = df['Papel'].astype(str).str.strip().eq('')
    if missing_role.any():
        role_index = _load_person_role_map()
        df.loc[missing_role, 'Papel'] = df.loc[missing_role, 'Pessoa'].apply(lambda value: _person_role(value, role_index=role_index))

    scope_asset_ids = set()
    if portfolio_scope_df is not None and not portfolio_scope_df.empty:
        scope_id_col = _pm_pick_first_column(portfolio_scope_df, ['ID', 'ItemID'])
        if scope_id_col:
            scope_asset_ids = {
                _pm_clean_issue_key(value)
                for value in portfolio_scope_df[scope_id_col].dropna().astype(str).tolist()
                if _pm_clean_issue_key(value)
            }

    df['Asset em Escopo'] = True
    if scope_asset_ids:
        df['Asset em Escopo'] = df['AssetID'].isin(scope_asset_ids)
    df['Asset Mapeado'] = df['AssetID'].astype(str).str.strip().ne('')

    scoped_df = df[df['Asset em Escopo']].copy() if scope_asset_ids else df.copy()
    return {
        'available': not scoped_df.empty,
        'error': '' if not scoped_df.empty else 'Sem worklogs CAPEX compatíveis com o escopo/filtros atuais.',
        'df': df,
        'scoped_df': scoped_df,
        'snapshot': snapshot or {},
        'cost_model': cost_model,
    }


def _build_worklog_portfolio_cost_view_legacy(start_ts, end_ts, portfolio_scope_df, project_value=None, responsavel=None) -> dict:
    fact_payload = build_worklog_cost_fact(
        start_ts,
        end_ts,
        portfolio_scope_df=portfolio_scope_df,
        project_value=project_value,
        responsavel=responsavel,
    )
    fact_df = fact_payload.get('df', pd.DataFrame()).copy()
    scoped_df = fact_payload.get('scoped_df', pd.DataFrame()).copy()
    if fact_df.empty or scoped_df.empty:
        return {
            'available': False,
            'error': fact_payload.get('error', 'Sem worklogs monetizáveis para o escopo atual.'),
            'worklog_fact_df': fact_df,
            'scoped_worklog_df': scoped_df,
            'product_summary': pd.DataFrame(),
            'top_assets': pd.DataFrame(),
            'overall': {
                'hours': 0.0,
                'cost': 0.0,
                'mapped_pct': np.nan,
                'person_rate_pct': np.nan,
                'items': 0,
                'assets_mapped': 0,
                'cost_model_available': bool((fact_payload.get('cost_model') or {}).get('available')),
            },
            'snapshot': fact_payload.get('snapshot', {}),
            'cost_model': fact_payload.get('cost_model', {}),
        }

    scoped_df['Horas'] = pd.to_numeric(scoped_df['Horas'], errors='coerce').fillna(0)
    scoped_df['Custo Real (R$)'] = pd.to_numeric(scoped_df['Custo Real (R$)'], errors='coerce').fillna(0)
    scoped_df['Asset Mapeado'] = scoped_df['Asset Mapeado'].fillna(False).astype(bool)

    product_summary = (
        scoped_df
        .groupby(['Produto', 'Projeto PM'], dropna=False)
        .agg(
            **{
                'Horas Reais': ('Horas', 'sum'),
                'Custo Real (R$)': ('Custo Real (R$)', 'sum'),
                'Apontamentos': ('Worklog ID', 'nunique'),
                'Issues': ('Issue Key', 'nunique'),
                'Ativos Mapeados': ('AssetID', lambda values: pd.Series(values).astype(str).str.strip().replace('', np.nan).dropna().nunique()),
            }
        )
        .reset_index()
    )
    if not product_summary.empty:
        person_cost = (
            scoped_df[scoped_df['Fonte Taxa'] == 'Pessoa']
            .groupby(['Produto', 'Projeto PM'], dropna=False)['Custo Real (R$)']
            .sum()
            .reset_index(name='Custo com Taxa Pessoa (R$)')
        )
        mapped_cost = (
            scoped_df[scoped_df['Asset Mapeado']]
            .groupby(['Produto', 'Projeto PM'], dropna=False)['Custo Real (R$)']
            .sum()
            .reset_index(name='Custo Mapeado (R$)')
        )
        product_summary = product_summary.merge(person_cost, how='left', on=['Produto', 'Projeto PM'])
        product_summary = product_summary.merge(mapped_cost, how='left', on=['Produto', 'Projeto PM'])
        product_summary['Custo com Taxa Pessoa (R$)'] = pd.to_numeric(product_summary['Custo com Taxa Pessoa (R$)'], errors='coerce').fillna(0)
        product_summary['Custo Mapeado (R$)'] = pd.to_numeric(product_summary['Custo Mapeado (R$)'], errors='coerce').fillna(0)
        product_summary['% Custo com Taxa Pessoa'] = np.where(
            product_summary['Custo Real (R$)'] > 0,
            product_summary['Custo com Taxa Pessoa (R$)'] / product_summary['Custo Real (R$)'],
            np.nan,
        )
        product_summary['% Custo Mapeado'] = np.where(
            product_summary['Custo Real (R$)'] > 0,
            product_summary['Custo Mapeado (R$)'] / product_summary['Custo Real (R$)'],
            np.nan,
        )
        product_summary = product_summary.sort_values(['Custo Real (R$)', 'Horas Reais'], ascending=[False, False], ignore_index=True)

    top_assets = pd.DataFrame(columns=[
        'Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Horas Reais',
        'Custo Real (R$)', 'Issues', 'Apontamentos', '% Custo com Taxa Pessoa'
    ])
    mapped_assets_df = scoped_df[scoped_df['Asset Mapeado']].copy()
    if not mapped_assets_df.empty:
        top_assets = (
            mapped_assets_df
            .groupby(['Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo'], dropna=False)
            .agg(
                **{
                    'Horas Reais': ('Horas', 'sum'),
                    'Custo Real (R$)': ('Custo Real (R$)', 'sum'),
                    'Issues': ('Issue Key', 'nunique'),
                    'Apontamentos': ('Worklog ID', 'nunique'),
                }
            )
            .reset_index()
        )
        person_cost_assets = (
            mapped_assets_df[mapped_assets_df['Fonte Taxa'] == 'Pessoa']
            .groupby(['Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo'], dropna=False)['Custo Real (R$)']
            .sum()
            .reset_index(name='Custo com Taxa Pessoa (R$)')
        )
        top_assets = top_assets.merge(
            person_cost_assets,
            how='left',
            on=['Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo'],
        )
        top_assets['Custo com Taxa Pessoa (R$)'] = pd.to_numeric(top_assets['Custo com Taxa Pessoa (R$)'], errors='coerce').fillna(0)
        top_assets['% Custo com Taxa Pessoa'] = np.where(
            top_assets['Custo Real (R$)'] > 0,
            top_assets['Custo com Taxa Pessoa (R$)'] / top_assets['Custo Real (R$)'],
            np.nan,
        )
        top_assets = top_assets.sort_values(['Custo Real (R$)', 'Horas Reais'], ascending=[False, False], ignore_index=True)

    total_cost = float(scoped_df['Custo Real (R$)'].sum())
    mapped_cost = float(scoped_df.loc[scoped_df['Asset Mapeado'], 'Custo Real (R$)'].sum())
    person_rate_cost = float(scoped_df.loc[scoped_df['Fonte Taxa'] == 'Pessoa', 'Custo Real (R$)'].sum())
    out_of_scope_cost = float(fact_df.loc[~fact_df['Asset em Escopo'], 'Custo Real (R$)'].sum()) if 'Asset em Escopo' in fact_df.columns else 0.0

    return {
        'available': True,
        'worklog_fact_df': fact_df,
        'scoped_worklog_df': scoped_df,
        'product_summary': product_summary,
        'top_assets': top_assets,
        'overall': {
            'hours': float(scoped_df['Horas'].sum()),
            'cost': total_cost,
            'mapped_cost': mapped_cost,
            'mapped_pct': (mapped_cost / total_cost) if total_cost > 0 else np.nan,
            'person_rate_pct': (person_rate_cost / total_cost) if total_cost > 0 else np.nan,
            'items': int(scoped_df['Issue Key'].nunique()),
            'assets_mapped': int(scoped_df.loc[scoped_df['Asset Mapeado'], 'AssetID'].nunique()),
            'out_of_scope_cost': out_of_scope_cost,
            'cost_model_available': bool((fact_payload.get('cost_model') or {}).get('available')),
            'updated_at': str((fact_payload.get('snapshot') or {}).get('updated_at') or ''),
        },
        'snapshot': fact_payload.get('snapshot', {}),
        'cost_model': fact_payload.get('cost_model', {}),
    }


def get_portfolio_project_filter_options():
    options = [{'label': PROJECT_FILTER_ALL_LABEL, 'value': PROJECT_FILTER_ALL_VALUE}]
    teams = set()

    _, df_portfolio, error = get_portfolio_snapshot()
    if not error and df_portfolio is not None and not df_portfolio.empty and 'Team' in df_portfolio.columns:
        for team in df_portfolio['Team'].dropna().astype(str):
            t = team.strip()
            if t:
                teams.add(t)

    for team in sorted(teams):
        options.append({'label': team, 'value': team})
    return options


def _capex_kind_spec(kind: str) -> dict:
    normalized = str(kind or '').strip().lower()
    if normalized == 'summary':
        return {
            'kind': 'summary',
            'env_file': 'FLOW_PMO_CAPEX_SUMMARY_FILE',
            'env_url': 'FLOW_PMO_CAPEX_SUMMARY_URL',
            'preferred_latest_names': {'capex-summary-latest.csv', 'capex-mensal-latest.csv'},
            'suffixes': ('-mensal.csv', '-summary.csv'),
            'required_cols': {'MesCompetencia', 'ID do Projeto', 'Colaborador', 'Horas', 'Projeto Jira'},
        }
    return {
        'kind': 'raw',
        'env_file': 'FLOW_PMO_CAPEX_RAW_FILE',
        'env_url': 'FLOW_PMO_CAPEX_RAW_URL',
        'preferred_latest_names': {'capex-raw-latest.csv'},
        'suffixes': ('-raw.csv',),
        'required_cols': {
            'MesCompetencia', 'ID do Projeto', 'Descrição do Ativo', 'Colaborador',
            'Data do Apontamento das Horas', 'Horas', 'Issue Key', 'Projeto Jira',
        },
    }


def _capex_find_latest_csv_v2_unused(kind: str = 'raw'):
    spec = _capex_kind_spec(kind)
    explicit_file = _sanitize_os_path(os.getenv(spec['env_file'], ''))
    if explicit_file:
        candidate = explicit_file if os.path.isabs(explicit_file) else os.path.join(os.path.dirname(__file__), explicit_file)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        raise RuntimeError(f"{spec['env_file']} aponta para arquivo inexistente: {candidate}")

    csv_url = os.getenv(spec['env_url'], '').strip()
    if csv_url:
        try:
            return _download_capex_csv_from_url(csv_url, spec['kind'])
        except Exception as _url_exc:
            import warnings
            warnings.warn(
                f"[dashboard_full] Falha ao baixar CAPEX CSV de {spec['env_url']} ({_url_exc}). "
                "Tentando arquivo local como fallback.",
                RuntimeWarning,
                stacklevel=2,
            )

    candidates = []
    preferred = {name.lower() for name in spec['preferred_latest_names']}
    for folder in _iter_local_data_folders():
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low_name = str(name).lower()
            if not low_name.startswith('capex-'):
                continue
            if low_name in preferred or any(low_name.endswith(suffix) for suffix in spec['suffixes']):
                candidates.append(os.path.join(folder, name))

    candidates = [path for path in candidates if os.path.isfile(path)]
    if not candidates:
        return None

    preferred_matches = [path for path in candidates if os.path.basename(path).lower() in preferred]
    if preferred_matches:
        return max(preferred_matches, key=os.path.getctime)
    return max(candidates, key=os.path.getctime)


def _prepare_capex_snapshot_df(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if kind == 'raw':
        optional_defaults = {
            'Tipo do Ativo': '',
            'Atividade Desenvolvida': '',
            'Atividade Desenvolvida Normalizada': '',
            'Origem Horas': '',
            'Fonte Atividade': '',
            'Regra Atividade': '',
            'ConfidenceScore': np.nan,
            'Issue Summary': '',
            'Issue Type': '',
            'Status Atual': '',
            'Epic ID': '',
            'Epic Title': '',
            'Feature ID': '',
            'Feature Title': '',
            'Parent ID': '',
            'Parent Title': '',
            'Hierarchy Source': '',
        }
        for col, default in optional_defaults.items():
            if col not in out.columns:
                out[col] = default
        out['Data do Apontamento das Horas'] = pd.to_datetime(out['Data do Apontamento das Horas'], errors='coerce')
        out['Horas'] = pd.to_numeric(out['Horas'], errors='coerce').fillna(0.0)
        out['ConfidenceScore'] = pd.to_numeric(out.get('ConfidenceScore'), errors='coerce')
        out['Issue Key'] = out['Issue Key'].apply(_pm_clean_issue_key)
        out['Projeto Jira'] = out['Projeto Jira'].fillna('').astype(str).str.strip()
        out['MesCompetencia'] = out['MesCompetencia'].fillna('').astype(str).str.strip()
    else:
        if 'Horas' in out.columns:
            out['Horas'] = pd.to_numeric(out['Horas'], errors='coerce').fillna(0.0)
        out['Projeto Jira'] = out.get('Projeto Jira', '').fillna('').astype(str).str.strip() if 'Projeto Jira' in out.columns else ''
        out['MesCompetencia'] = out['MesCompetencia'].fillna('').astype(str).str.strip()
    return out


def _get_capex_snapshot_v2_unused(kind: str = 'raw'):
    spec = _capex_kind_spec(kind)
    cache_entry = CAPEX_CACHE.get(spec['kind'], {})
    now = datetime.now()
    cached_at = cache_entry.get('fetched_at')

    if cached_at and (now - cached_at) <= CAPEX_CACHE_TTL and cache_entry.get('df') is not None:
        try:
            latest_csv = find_latest_capex_csv(spec['kind'])
            if latest_csv:
                latest_abs = os.path.abspath(latest_csv)
                cached_abs = os.path.abspath(str(cache_entry.get('source_file') or ''))
                latest_mtime = os.path.getmtime(latest_csv)
                cached_mtime = cache_entry.get('source_mtime')
                if latest_abs == cached_abs and cached_mtime is not None and float(latest_mtime) == float(cached_mtime):
                    return cache_entry.get('df'), cache_entry.get('error')
            else:
                return cache_entry.get('df'), cache_entry.get('error')
        except Exception:
            return cache_entry.get('df'), cache_entry.get('error')

    try:
        csv_file = find_latest_capex_csv(spec['kind'])
        if not csv_file:
            raise RuntimeError(
                f"CSV CAPEX ({spec['kind']}) não encontrado. Configure {spec['env_file']} ou {spec['env_url']}, "
                f"ou publique um alias estável em uma destas pastas: {', '.join(DATA_FOLDERS or [DATA_FOLDER])}."
            )
        df = pd.read_csv(csv_file)
        missing = [col for col in spec['required_cols'] if col not in df.columns]
        if missing:
            raise RuntimeError(
                f"CSV CAPEX inválido ({os.path.basename(csv_file)}). Colunas ausentes: {', '.join(missing)}"
            )
        df = _prepare_capex_snapshot_df(df, spec['kind'])
        CAPEX_CACHE[spec['kind']] = {
            'fetched_at': now,
            'df': df,
            'error': None,
            'source_file': csv_file,
            'source_mtime': os.path.getmtime(csv_file),
        }
        return df, None
    except Exception as exc:
        CAPEX_CACHE[spec['kind']] = {
            'fetched_at': now,
            'df': pd.DataFrame(),
            'error': str(exc),
            'source_file': None,
            'source_mtime': None,
        }
        return pd.DataFrame(), str(exc)


def portfolio_table_component(df, title, table_id):
    if df is None or df.empty:
        return html.Div([
            html.H4(title),
            html.P('Nenhum item encontrado para este critério.')
        ], style={'marginTop': '20px'})

    columns = []
    for col in df.columns:
        col_def = {'name': col, 'id': col}
        if col == 'Link':
            col_def['presentation'] = 'markdown'
        columns.append(col_def)

    df_display = df.copy()
    if 'Link' in df_display.columns:
        df_display['Link'] = df_display['Link'].apply(lambda x: f"[Abrir]({x})" if str(x).strip() else '')

    return html.Div([
        html.H4(title),
        dash_table.DataTable(
            id=table_id,
            columns=columns,
            data=df_display.to_dict('records'),
            page_size=10,
            sort_action='native',
            filter_action='native',
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '6px', 'minWidth': '120px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        )
    ], style={'marginTop': '20px'})


def portfolio_roadmap_status_label(status_value, status_categoria_value=''):
    status_raw = str(status_value or '').strip()
    status_norm = normalize_text(status_raw)
    status_categoria_norm = normalize_text(status_categoria_value)

    if any(term in status_norm for term in ('blocked', 'bloque', 'suspend', 'suspens', 'paused', 'pause')):
        return 'Paused'

    if any(term in status_norm for term in ('done', 'concluido', 'concluida', 'closed', 'resolved')):
        return 'Done'

    if 'ready to delivery' in status_norm:
        return 'Running'

    pct_match = re.search(r'(\d{1,3})\s*%', status_raw)
    if pct_match:
        try:
            pct = float(pct_match.group(1))
            if pct <= 80.0:
                return 'Running'
        except Exception:
            pass

    if ('planning' in status_norm) or ('pllaning' in status_norm):
        return 'Planning'

    planning_terms = (
        'triagem',
        'backlog',
        'to do',
        'todo',
        'business review',
        'ready for development',
        'ready to start',
    )
    if any(term in status_norm for term in planning_terms):
        return 'Planning'

    if status_categoria_norm == 'backlog':
        return 'Planning'

    return None


def portfolio_quarter_label_from_date(value):
    dt = pd.to_datetime(value, errors='coerce')
    if pd.isna(dt):
        return None
    quarter = int(((int(dt.month) - 1) // 3) + 1)
    year = int(dt.year)
    return f'Q{quarter}-{year}'


def portfolio_roadmap_progress_pct(status_value, status_categoria_value=''):
    status_raw = str(status_value or '').strip()
    status_norm = normalize_text(status_raw)
    status_categoria_norm = normalize_text(status_categoria_value)

    pct_match = re.search(r'(\d{1,3})\s*%', status_raw)
    if pct_match:
        try:
            return max(0, min(100, int(float(pct_match.group(1)))))
        except Exception:
            pass

    if any(term in status_norm for term in ('blocked', 'bloque', 'suspend', 'suspens', 'paused', 'pause')):
        return None

    if any(term in status_norm for term in ('done', 'concluido', 'concluida', 'closed', 'resolved')):
        return 100

    flow_pct_map = [
        (('triagem', 'backlog', 'to do', 'todo', 'planning', 'pllaning', 'business review'), 0),
        (('ready for development', 'ready to start'), 15),
        (('in progress', 'in progess', 'desenvolvimento', 'development', 'doing'), 40),
        (('ready for code review', 'code review'), 55),
        (('ready for testing', 'testing', 'qa', 'homolog'), 70),
        (('ready for staging', 'staging'), 80),
        (('ready to delivery', 'ready for production', 'ready for release'), 80),
    ]
    for terms, pct in flow_pct_map:
        if any(term in status_norm for term in terms):
            return int(pct)

    if status_categoria_norm == 'concluido':
        return 100
    if status_categoria_norm == 'backlog':
        return 0
    if status_categoria_norm == 'em progresso':
        return 40

    return None


def portfolio_is_highest_priority(priority_value):
    priority_norm = normalize_text(priority_value)
    if not priority_norm:
        return False
    return (
        priority_norm == 'highest' or
        priority_norm == 'higest' or
        ('highest' in priority_norm) or
        ('higest' in priority_norm)
    )


def portfolio_is_cancelled_item(status_value, status_category_value=''):
    status_norm = normalize_text(status_value)
    status_category_norm = normalize_text(status_category_value)
    cancel_terms = ('cancel', 'cancelad', 'cancelled', 'canceled', 'descart', 'abort')
    return any(term in status_norm for term in cancel_terms) or any(term in status_category_norm for term in cancel_terms)


def render_portfolio_roadmap_quarter_view(df_source, selected_quarter='ALL'):
    if df_source is None or df_source.empty:
        return html.Div([
            html.H4('One Page - Roadmap 2026', style={'margin': '0 0 6px 0'}),
            html.P('Sem itens de portfólio para montar o roadmap por quarter.', style={'margin': 0, 'color': '#666'})
        ], style={'marginBottom': '18px'})

    df = df_source.copy()
    df = df[
        ~df.apply(
            lambda row: portfolio_is_cancelled_item(row.get('Status', ''), row.get('StatusCategoria', '')),
            axis=1
        )
    ].copy()
    if df.empty:
        return html.Div([
            html.H4('One Page - Roadmap 2026', style={'margin': '0 0 6px 0'}),
            html.P('Sem itens de portfólio ativos para montar o roadmap por quarter.', style={'margin': 0, 'color': '#666'})
        ], style={'marginBottom': '18px'})
    if 'DueDate' in df.columns:
        df['RoadmapQuarter'] = df['DueDate'].apply(portfolio_quarter_label_from_date)
    else:
        df['RoadmapQuarter'] = None

    df['RoadmapStatus'] = df.apply(
        lambda row: portfolio_roadmap_status_label(
            row.get('Status', ''),
            row.get('StatusCategoria', ''),
        ),
        axis=1
    )
    df = df[df['RoadmapStatus'].notna()].copy()

    roadmap_df = df[df['RoadmapQuarter'].isin(PORTFOLIO_ROADMAP_QUARTERS_2026)].copy()
    if roadmap_df.empty:
        return html.Div([
            html.H4('One Page - Roadmap 2026', style={'margin': '0 0 6px 0'}),
            html.P(
                'Nenhum item com status mapeado (Running/Planning/Done/Paused) em quarter de 2026 no recorte atual.',
                style={'margin': 0, 'color': '#666'}
            )
        ], style={'marginBottom': '18px'})

    legend_counts = (
        roadmap_df['RoadmapStatus']
        .value_counts()
        .reindex(PORTFOLIO_ROADMAP_STATUS_ORDER, fill_value=0)
    )

    project_priority = {'Paused': 0, 'Running': 1, 'Planning': 2, 'Done': 3}

    quarter_columns = []
    for quarter in PORTFOLIO_ROADMAP_QUARTERS_2026:
        q_df = roadmap_df[roadmap_df['RoadmapQuarter'] == quarter].copy()
        if q_df.empty:
            quarter_columns.append(
                html.Div([
                    html.Div(quarter, style={'fontWeight': 'bold', 'fontSize': '22px', 'color': '#3e6166', 'marginBottom': '10px'}),
                    html.Div('Sem projetos', style={'fontSize': '13px', 'color': '#666', 'fontStyle': 'italic'})
                ], style={'padding': '12px', 'border': '1px solid #d8e1e3', 'borderRadius': '6px', 'minHeight': '200px'})
            )
            continue

        by_project = (
            q_df.groupby(['Projeto', 'RoadmapStatus'], dropna=False)
            .size()
            .reset_index(name='WorkItems')
        )
        by_project['Projeto'] = by_project['Projeto'].fillna('').astype(str).str.strip().replace('', 'Sem projeto')
        by_project['Priority'] = by_project['RoadmapStatus'].map(project_priority).fillna(99)
        by_project = by_project.sort_values(['Projeto', 'Priority', 'WorkItems'], ascending=[True, True, False], ignore_index=True)
        by_project_primary = by_project.groupby('Projeto', as_index=False).first()

        chips = []
        for _, row in by_project_primary.iterrows():
            status = str(row['RoadmapStatus'])
            color = PORTFOLIO_ROADMAP_STATUS_COLORS.get(status, '#d9d9d9')
            chips.append(
                html.Div(
                    str(row['Projeto']),
                    title=f"{row['Projeto']} | {status}",
                    style={
                        'backgroundColor': color,
                        'padding': '5px 8px',
                        'borderRadius': '12px',
                        'fontSize': '12px',
                        'fontWeight': '600',
                        'whiteSpace': 'nowrap',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                        'maxWidth': '100%',
                    }
                )
            )

        status_counts = (
            q_df['RoadmapStatus']
            .value_counts()
            .reindex(PORTFOLIO_ROADMAP_STATUS_ORDER, fill_value=0)
            .to_dict()
        )
        quarter_columns.append(
            html.Div([
                html.Div(quarter, style={'fontWeight': 'bold', 'fontSize': '22px', 'color': '#3e6166', 'marginBottom': '8px'}),
                html.Div(
                    f"Projetos: {int(by_project_primary['Projeto'].nunique())} | "
                    f"Running {int(status_counts.get('Running', 0))} | "
                    f"Planning {int(status_counts.get('Planning', 0))} | "
                    f"Done {int(status_counts.get('Done', 0))} | "
                    f"Paused {int(status_counts.get('Paused', 0))}",
                    style={'fontSize': '12px', 'color': '#3d3d3d', 'marginBottom': '8px'}
                ),
                html.Div(
                    chips,
                    style={
                        'display': 'grid',
                        'gridTemplateColumns': '1fr',
                        'gap': '6px',
                        'maxHeight': '170px',
                        'overflowY': 'auto'
                    }
                ),
            ], style={'padding': '12px', 'border': '1px solid #d8e1e3', 'borderRadius': '6px', 'minHeight': '200px'})
        )

    legend = []
    for status in PORTFOLIO_ROADMAP_STATUS_ORDER:
        legend.append(
            html.Div([
                html.Span(
                    status,
                    style={
                        'backgroundColor': PORTFOLIO_ROADMAP_STATUS_COLORS.get(status, '#ddd'),
                        'padding': '4px 10px',
                        'borderRadius': '10px',
                        'fontWeight': 'bold',
                        'fontSize': '13px',
                        'display': 'inline-block'
                    }
                )
            ], style={'display': 'inline-block', 'marginRight': '8px', 'marginBottom': '6px'})
        )

    return html.Div([
        html.Div([
            html.H3('One Page - Roadmap 2026', style={'margin': 0, 'color': 'white', 'fontStyle': 'italic'}),
        ], style={'backgroundColor': '#334f52', 'padding': '10px 12px', 'borderRadius': '6px 6px 0 0'}),
        html.Div([
            html.Div(q, style={
                'flex': '1',
                'textAlign': 'center',
                'fontWeight': 'bold',
                'fontSize': '32px',
                'color': '#e6f0f1',
                'backgroundColor': '#4d7378',
                'padding': '8px 0',
                'borderRight': '2px solid #f5f9fa'
            }) for q in ['Q1', 'Q2', 'Q3', 'Q4']
        ], style={'display': 'flex', 'marginTop': '4px', 'borderRadius': '4px', 'overflow': 'hidden'}),
        html.Div([
            html.Span('Legenda:', style={'fontStyle': 'italic', 'fontWeight': 'bold', 'marginRight': '8px'}),
            *legend
        ], style={'marginTop': '14px', 'marginBottom': '12px'}),
        html.Div(
            quarter_columns,
            style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fit, minmax(240px, 1fr))',
                'gap': '10px'
            }
        )
    ], style={'marginBottom': '20px'})


def render_portfolio_roadmap_full_epics_view(df_source, selected_quarter='ALL', high_priority_ids=None, high_priority_titles=None):
    if df_source is None or df_source.empty:
        return html.Div([
            html.H4('One Page Completo - Roadmap 2026', style={'margin': '0 0 6px 0'}),
            html.P('Sem itens de portfólio para montar o roadmap completo.', style={'margin': 0, 'color': '#666'})
        ], style={'marginBottom': '18px'})

    df = df_source.copy()
    df = df[
        ~df.apply(
            lambda row: portfolio_is_cancelled_item(row.get('Status', ''), row.get('StatusCategoria', '')),
            axis=1
        )
    ].copy()
    if df.empty:
        return html.Div([
            html.H4('One Page Completo - Roadmap 2026', style={'margin': '0 0 6px 0'}),
            html.P('Sem itens de portfólio ativos para montar o roadmap completo.', style={'margin': 0, 'color': '#666'})
        ], style={'marginBottom': '18px'})
    if 'ETIQUETA' not in df.columns:
        df['ETIQUETA'] = ''
    if 'Etiquetas' not in df.columns:
        df['Etiquetas'] = ''
    team_col = 'Team' if 'Team' in df.columns else ('team' if 'team' in df.columns else None)
    if team_col is None:
        df['RoadmapTeam'] = 'Sem TEAM'
    else:
        df['RoadmapTeam'] = df[team_col].fillna('').astype(str).str.strip()
        df.loc[df['RoadmapTeam'] == '', 'RoadmapTeam'] = 'Sem TEAM'
    df['ExtraOnePageLabels'] = df['ETIQUETA'].where(df['ETIQUETA'].astype(str).str.strip() != '', df['Etiquetas'])
    df['IsExtraOnePage'] = df['ExtraOnePageLabels'].apply(portfolio_has_extra_onepage_tag)
    if 'TipoNorm' not in df.columns and 'Tipo' in df.columns:
        df['TipoNorm'] = df['Tipo'].map(normalize_text)
    if 'TipoNorm' in df.columns:
        df = df[df['TipoNorm'].isin({'epico', 'epic'})].copy()
    if df.empty:
        return html.Div([
            html.H4('One Page Completo - Roadmap 2026', style={'margin': '0 0 6px 0'}),
            html.P('Nenhum épico encontrado no recorte atual.', style={'margin': 0, 'color': '#666'})
        ], style={'marginBottom': '18px'})

    if 'DueDate' in df.columns:
        df['DueDate'] = pd.to_datetime(df['DueDate'], errors='coerce')
        df['MissingTargetDate'] = df['DueDate'].isna()
        df['RoadmapQuarter'] = df['DueDate'].apply(portfolio_quarter_label_from_date)
    else:
        df['DueDate'] = pd.NaT
        df['MissingTargetDate'] = True
        df['RoadmapQuarter'] = None

    missing_target_df = df[df['MissingTargetDate']].copy()
    roadmap_df = df[df['RoadmapQuarter'].isin(PORTFOLIO_ROADMAP_QUARTERS_2026)].copy()
    if selected_quarter in PORTFOLIO_ROADMAP_QUARTERS_2026:
        roadmap_df = roadmap_df[roadmap_df['RoadmapQuarter'] == selected_quarter].copy()
    if roadmap_df.empty and missing_target_df.empty:
        return html.Div([
            html.H4('One Page Completo - Roadmap 2026', style={'margin': '0 0 6px 0'}),
            html.P('Nenhum épico com DueDate em 2026 no recorte atual.', style={'margin': 0, 'color': '#666'})
        ], style={'marginBottom': '18px'})

    df['RoadmapStatus'] = df.apply(
        lambda row: portfolio_roadmap_status_label(row.get('Status', ''), row.get('StatusCategoria', '')) or 'Planning',
        axis=1
    )
    df['RoadmapProgressPct'] = df.apply(
        lambda row: portfolio_roadmap_progress_pct(row.get('Status', ''), row.get('StatusCategoria', '')),
        axis=1
    )
    high_ids = set(str(x).strip().upper() for x in (high_priority_ids or set()) if str(x).strip())
    high_titles_norm = set(normalize_text(x) for x in (high_priority_titles or set()) if str(x).strip())
    if 'ID' in df.columns:
        df['ID'] = df['ID'].fillna('').astype(str)
    else:
        df['ID'] = ''
    if 'Prioridade' in df.columns:
        df['IsHighestPriority'] = df['Prioridade'].apply(portfolio_is_highest_priority)
    else:
        df['IsHighestPriority'] = False
    if 'Titulo' in df.columns:
        df['Titulo'] = df['Titulo'].fillna('').astype(str).str.strip().replace('', 'Sem título')
    else:
        df['Titulo'] = 'Sem título'
    df['TituloNorm'] = df['Titulo'].map(normalize_text)
    df['IsHighestPriority'] = (
        df['IsHighestPriority'] |
        df['ID'].astype(str).str.strip().str.upper().isin(high_ids) |
        df['TituloNorm'].isin(high_titles_norm) |
        df['TituloNorm'].str.contains('higest|highest', regex=True, na=False)
    )
    roadmap_df = df[df['RoadmapQuarter'].isin(PORTFOLIO_ROADMAP_QUARTERS_2026)].copy()
    if selected_quarter in PORTFOLIO_ROADMAP_QUARTERS_2026:
        roadmap_df = roadmap_df[roadmap_df['RoadmapQuarter'] == selected_quarter].copy()
    missing_target_df = df[df['MissingTargetDate']].copy()

    legend_counts = (
        roadmap_df['RoadmapStatus']
        .value_counts()
        .reindex(PORTFOLIO_ROADMAP_STATUS_ORDER, fill_value=0)
    )

    legend = []
    for status in PORTFOLIO_ROADMAP_STATUS_ORDER:
        legend.append(
            html.Div([
                html.Span(
                    f"{status} ({int(legend_counts.get(status, 0))})",
                    style={
                        'backgroundColor': PORTFOLIO_ROADMAP_STATUS_COLORS.get(status, '#ddd'),
                        'padding': '4px 10px',
                        'borderRadius': '10px',
                        'fontWeight': 'bold',
                        'fontSize': '13px',
                        'display': 'inline-block'
                    }
                )
            ], style={'display': 'inline-block', 'marginRight': '8px', 'marginBottom': '6px'})
        )

    def _render_epic_row(row, highlight_missing_target=False):
        status = str(row.get('RoadmapStatus', 'Planning'))
        is_extra_onepage = bool(row.get('IsExtraOnePage', False))
        color = '#f5b7b1' if highlight_missing_target else PORTFOLIO_ROADMAP_STATUS_COLORS.get(status, '#d9d9d9')
        if is_extra_onepage:
            color = '#f8d7da'
        pct = row.get('RoadmapProgressPct')
        pct_valid = pd.notna(pct)
        pct_label = f"{int(pct)}%" if pct_valid else 'N/D'
        is_high = bool(row.get('IsHighestPriority', False))
        title_extra = ' | Sem target date' if highlight_missing_target else ''
        return html.Div([
            html.Div(
                [
                    html.Span(str(row.get('Titulo', 'Sem título')), style={'flex': '1', 'minWidth': 0}),
                    html.Span(
                        'Sem target date',
                        style={
                            'display': 'inline-block',
                            'marginLeft': '8px',
                            'padding': '2px 6px',
                            'borderRadius': '999px',
                            'backgroundColor': '#b42318',
                            'color': 'white',
                            'fontSize': '10px',
                            'fontWeight': '700',
                            'textTransform': 'uppercase',
                            'letterSpacing': '0.02em',
                        }
                    ) if highlight_missing_target else html.Span(),
                    html.Span(
                        'EXTRA-ONEPAGE',
                        style={
                            'display': 'inline-block',
                            'marginLeft': '8px',
                            'padding': '2px 6px',
                            'borderRadius': '999px',
                            'backgroundColor': '#b42318',
                            'color': 'white',
                            'fontSize': '10px',
                            'fontWeight': '700',
                            'textTransform': 'uppercase',
                            'letterSpacing': '0.02em',
                        }
                    ) if is_extra_onepage else html.Span(),
                    html.Span(
                        '★',
                        title='Priority: Highest',
                        style={
                            'display': 'inline-flex',
                            'alignItems': 'center',
                            'justifyContent': 'center',
                            'width': '26px',
                            'height': '26px',
                            'borderRadius': '50%',
                            'backgroundColor': '#1f4f5e',
                            'color': '#000000',
                            'fontSize': '16px',
                            'fontWeight': '900',
                            'marginLeft': '8px',
                        }
                    ) if is_high else html.Span()
                ],
                title=f"{row.get('Titulo', '')} | Status: {row.get('Status', '')}{title_extra}" + (' | Highest' if is_high else ''),
                style={
                    'backgroundColor': color,
                    'padding': '4px 10px',
                    'borderRadius': '0',
                    'fontSize': '15px',
                    'fontWeight': '700',
                    'lineHeight': '1.2',
                    'display': 'flex',
                    'alignItems': 'center',
                    'borderLeft': '4px solid #b42318' if (highlight_missing_target or is_extra_onepage) else '0',
                    'color': '#7a0610' if is_extra_onepage else '#111',
                }
            ),
            html.Div([
                html.Span('Avanço:', style={'fontSize': '11px', 'fontWeight': 'bold', 'marginRight': '6px', 'color': '#3d3d3d'}),
                html.Span(pct_label, style={'fontSize': '11px', 'fontWeight': 'bold', 'color': '#1f3e46'}),
                html.Div(
                    html.Div(
                        style={
                            'width': f"{int(max(0, min(100, float(pct)))) if pct_valid else 0}%",
                            'height': '6px',
                            'backgroundColor': '#1f3e46',
                            'borderRadius': '4px'
                        }
                    ),
                    style={'marginTop': '4px', 'height': '6px', 'backgroundColor': '#d6e1e4', 'borderRadius': '4px'}
                )
            ], style={'padding': '3px 4px 6px 4px'} if status == 'Running' else {'display': 'none'})
        ], style={'marginBottom': '3px'})

    def _render_column(title, items_df, header_color='#3e6166', border_color='#d8e1e3',
                       empty_label='Sem épicos', counter_label='Épicos', highlight_missing_target=False):
        local_df = items_df.copy()
        if local_df.empty:
            return html.Div([
                html.Div(title, style={'fontWeight': 'bold', 'fontSize': '22px', 'color': header_color, 'marginBottom': '10px'}),
                html.Div(empty_label, style={'fontSize': '13px', 'color': '#666', 'fontStyle': 'italic'})
            ], style={'padding': '12px', 'border': f'1px solid {border_color}', 'borderRadius': '6px', 'minHeight': '540px'})

        local_df = local_df.sort_values(['RoadmapTeam', 'DueDate', 'Titulo'], ascending=[True, True, True], ignore_index=True)

        def _team_sort_key(team_name):
            return (str(team_name or '').strip().lower() == 'sem team', str(team_name or '').strip().lower())

        def _render_status_group(team_df, status_name, label_color, margin_top='8px'):
            status_df = team_df[team_df['RoadmapStatus'] == status_name].copy()
            if status_df.empty:
                return []
            if status_name == 'Running':
                status_df['_pct_sort'] = pd.to_numeric(status_df['RoadmapProgressPct'], errors='coerce').fillna(-1)
                status_df = status_df.sort_values(['_pct_sort', 'DueDate', 'Titulo'], ascending=[True, True, True], ignore_index=True)
            else:
                status_df = status_df.sort_values(['DueDate', 'Titulo'], ascending=[True, True], ignore_index=True)
            rows = [
                html.Div(
                    f"{status_name} ({int(len(status_df))})",
                    style={'fontSize': '12px', 'fontWeight': 'bold', 'color': label_color, 'margin': f'{margin_top} 0 4px 0'}
                )
            ]
            for _, status_row in status_df.iterrows():
                rows.append(_render_epic_row(status_row, highlight_missing_target=highlight_missing_target))
            return rows

        team_lanes = []
        team_names = sorted(local_df['RoadmapTeam'].dropna().astype(str).unique(), key=_team_sort_key)
        for team_name in team_names:
            team_df = local_df[local_df['RoadmapTeam'] == team_name].copy()
            lane_rows = []
            lane_rows.extend(_render_status_group(team_df, 'Running', '#1f3e46', margin_top='4px'))
            lane_rows.extend(_render_status_group(team_df, 'Planning', '#4a3e57'))
            lane_rows.extend(_render_status_group(team_df, 'Done', '#355427'))
            lane_rows.extend(_render_status_group(team_df, 'Paused', '#6d5a29'))
            team_lanes.append(
                html.Div([
                    html.Div(
                        [
                            html.Span(str(team_name), style={'fontSize': '13px', 'fontWeight': '700', 'color': '#17343b'}),
                            html.Span(
                                f"{int(len(team_df))} épico(s)",
                                style={'fontSize': '11px', 'fontWeight': '600', 'color': '#49656b'}
                            )
                        ],
                        style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '6px'}
                    ),
                    html.Div(lane_rows)
                ], style={
                    'padding': '8px',
                    'marginBottom': '10px',
                    'border': '1px solid #d9e3e5',
                    'borderRadius': '6px',
                    'backgroundColor': '#f8fbfb'
                })
            )

        return html.Div([
            html.Div(title, style={'fontWeight': 'bold', 'fontSize': '22px', 'color': header_color, 'marginBottom': '8px'}),
            html.Div(
                f"{counter_label}: {int(len(local_df))}",
                style={'fontSize': '12px', 'color': '#3d3d3d', 'marginBottom': '8px'}
            ),
            html.Div(team_lanes, style={'maxHeight': '500px', 'overflowY': 'auto'}),
        ], style={'padding': '12px', 'border': f'1px solid {border_color}', 'borderRadius': '6px', 'minHeight': '540px'})

    quarter_columns = [
        _render_column(quarter, roadmap_df[roadmap_df['RoadmapQuarter'] == quarter].copy())
        for quarter in PORTFOLIO_ROADMAP_QUARTERS_2026
    ]
    quarter_columns.append(
        _render_column(
            'Sem target date',
            missing_target_df,
            header_color='#b42318',
            border_color='#f5c2c7',
            empty_label='Nenhum épico sem target date',
            counter_label='Sem target date',
            highlight_missing_target=True
        )
    )

    return html.Div([
        html.Div([
            html.H3('One Page Completo - Roadmap 2026', style={'margin': 0, 'color': 'white', 'fontStyle': 'italic'}),
        ], style={'backgroundColor': '#334f52', 'padding': '10px 12px', 'borderRadius': '6px 6px 0 0'}),
        html.Div([
            html.Div(q, style={
                'flex': '1',
                'textAlign': 'center',
                'fontWeight': 'bold',
                'fontSize': '32px',
                'color': '#e6f0f1' if q != 'Sem target date' else '#fff1f2',
                'backgroundColor': '#4d7378' if q != 'Sem target date' else '#b42318',
                'padding': '8px 0',
                'borderRight': '2px solid #f5f9fa'
            }) for q in ['Q1', 'Q2', 'Q3', 'Q4', 'Sem target date']
        ], style={'display': 'flex', 'marginTop': '4px', 'borderRadius': '4px', 'overflow': 'hidden'}),
        html.Div([
            html.Span('Legenda:', style={'fontStyle': 'italic', 'fontWeight': 'bold', 'marginRight': '8px'}),
            *legend
        ], style={'marginTop': '14px', 'marginBottom': '12px'}),
        html.Div(
            quarter_columns,
            style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fit, minmax(300px, 1fr))',
                'gap': '10px'
            }
        )
    ], style={'marginBottom': '20px'})


def normalize_original_jira_type_filter_values(tipo_original):
    if tipo_original in (None, '', []):
        return []
    if isinstance(tipo_original, str):
        values = [tipo_original]
    else:
        values = list(tipo_original)
    cleaned = []
    for value in values:
        text = str(value or '').strip()
        if not text:
            continue
        if text == ORIGINAL_JIRA_TYPE_FILTER_ALL_VALUE:
            return []
        if text not in cleaned:
            cleaned.append(text)
    return cleaned


def format_original_jira_type_filter_label(tipo_original):
    selected = normalize_original_jira_type_filter_values(tipo_original)
    if not selected:
        return ORIGINAL_JIRA_TYPE_FILTER_ALL_LABEL
    return ', '.join(selected)


def weekly_bucket_start(date_series):
    return date_series.dt.to_period(WEEK_PERIOD).dt.start_time


def format_currency_br(value, decimals=2, suffix=''):
    if pd.isna(value):
        return '—'
    try:
        number = float(value)
    except Exception:
        return '—'
    formatted = f"{number:,.{decimals}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"R$ {formatted}{suffix}"


def build_cfd_dataframe(df_source, start_ts=None, end_ts=None):
    """Builds CFD series using macro stages and cumulative stacking (right-to-left sum)."""
    if df_source is None or getattr(df_source, 'empty', True):
        return pd.DataFrame(), ['Backlog', 'Em Progresso', 'Pronto']

    date_cols = [c for c in ['DataBacklog', 'DataInProgress', 'DataDone'] if c in df_source.columns]
    if not date_cols:
        return pd.DataFrame(), ['Backlog', 'Em Progresso', 'Pronto']

    valid_dates = [pd.to_datetime(df_source[c], errors='coerce').dropna() for c in date_cols]
    valid_dates = [s for s in valid_dates if not s.empty]
    if not valid_dates:
        return pd.DataFrame(), ['Backlog', 'Em Progresso', 'Pronto']

    inferred_start = min(s.min() for s in valid_dates)
    inferred_end = max(s.max() for s in valid_dates)
    start_point = pd.to_datetime(start_ts if pd.notna(start_ts) else inferred_start).normalize()
    end_point = pd.to_datetime(end_ts if pd.notna(end_ts) else inferred_end).normalize()
    if pd.isna(start_point) or pd.isna(end_point) or end_point < start_point:
        return pd.DataFrame(), ['Backlog', 'Em Progresso', 'Pronto']

    daily_points = pd.date_range(start=start_point, end=end_point, freq=CFD_SNAPSHOT_FREQ)
    snapshots = pd.DatetimeIndex(sorted(set([start_point, end_point, *list(daily_points)])))
    if snapshots.empty:
        snapshots = pd.DatetimeIndex([start_point, end_point]).unique().sort_values()

    data_backlog = pd.to_datetime(df_source['DataBacklog'], errors='coerce') if 'DataBacklog' in df_source.columns else pd.Series(pd.NaT, index=df_source.index)
    data_in_progress = pd.to_datetime(df_source['DataInProgress'], errors='coerce') if 'DataInProgress' in df_source.columns else pd.Series(pd.NaT, index=df_source.index)
    data_done = pd.to_datetime(df_source['DataDone'], errors='coerce') if 'DataDone' in df_source.columns else pd.Series(pd.NaT, index=df_source.index)

    rows = []
    for snapshot in snapshots:
        backlog_count = int(((data_backlog <= snapshot) & (data_in_progress.isna() | (data_in_progress > snapshot))).sum()) if 'DataBacklog' in df_source.columns else 0
        in_progress_count = int(((data_in_progress <= snapshot) & (data_done.isna() | (data_done > snapshot))).sum()) if 'DataInProgress' in df_source.columns else 0
        done_count = int((data_done <= snapshot).sum()) if 'DataDone' in df_source.columns else 0
        rows.append({
            'Data': snapshot,
            'Backlog_raw': backlog_count,
            'Em Progresso_raw': in_progress_count,
            'Pronto_raw': done_count,
        })

    cfd = pd.DataFrame(rows)
    if cfd.empty:
        return cfd, ['Backlog', 'Em Progresso', 'Pronto']

    # Algoritmo do CFD: acumular da direita para a esquerda (Pronto -> Em Progresso -> Backlog).
    cfd['Pronto'] = cfd['Pronto_raw']
    cfd['Em Progresso'] = cfd['Pronto_raw'] + cfd['Em Progresso_raw']
    cfd['Backlog'] = cfd['Em Progresso'] + cfd['Backlog_raw']

    return cfd, ['Backlog', 'Em Progresso', 'Pronto']


def _detect_stage_date_columns(items_df, bottlenecks_df=None):
    if items_df is None or items_df.empty:
        return []

    cols = list(items_df.columns)
    start_idx = cols.index('Title') + 1 if 'Title' in cols else 0
    end_idx = cols.index('Tipo de Problema') if 'Tipo de Problema' in cols else len(cols)
    candidate_cols = cols[start_idx:end_idx] if start_idx < end_idx else []

    # First preference: the contiguous flow block between Title and Tipo de Problema.
    stage_cols = []
    for col in candidate_cols:
        series = pd.to_datetime(items_df[col], dayfirst=True, errors='coerce')
        if series.notna().any():
            stage_cols.append(col)

    # If all values are blank for the filtered export, fallback to bottleneck stage names / known Done.
    if not stage_cols and bottlenecks_df is not None and not bottlenecks_df.empty and 'Etapa' in bottlenecks_df.columns:
        stage_cols = [c for c in bottlenecks_df['Etapa'].astype(str).tolist() if c in items_df.columns]
        if 'Done' in items_df.columns and 'Done' not in stage_cols:
            stage_cols.append('Done')

    if not stage_cols:
        known_non_stage = {
            'ID', 'Link', 'Title', 'Tipo de Problema', 'Prioridade', 'Versões de correção', 'Componentes',
            'Responsável', 'Criador', 'Space', 'Resolução', 'Etiquetas', 'Blocked Days', 'Blocked', 'Flagged',
            'Epic Name', 'Team', 'Organizations', 'Sprints', 'Principal', 'Afeta as versões'
        }
        for col in cols:
            if col in known_non_stage:
                continue
            series = pd.to_datetime(items_df[col], dayfirst=True, errors='coerce')
            if series.notna().any():
                stage_cols.append(col)

    if 'Done' in items_df.columns and 'Done' not in stage_cols:
        done_series = pd.to_datetime(items_df['Done'], dayfirst=True, errors='coerce')
        if done_series.notna().any():
            stage_cols.append('Done')

    # Keep original CSV order and unique values only.
    seen = set()
    ordered = []
    for col in cols:
        if col in stage_cols and col not in seen:
            ordered.append(col)
            seen.add(col)
    return ordered


def build_detailed_cfd_exact_dataframe(df_cfd_macro, projeto=None, bottlenecks_df=None, filtered_item_ids=None):
    """Build exact stage-level CFD from project downstream CSV timestamps per stage."""
    if df_cfd_macro is None or df_cfd_macro.empty or not projeto:
        return pd.DataFrame(), []
    items_df = load_project_downstream_items_csv(projeto)
    if items_df.empty:
        return pd.DataFrame(), []

    if filtered_item_ids is not None and 'ID' in items_df.columns:
        allowed_ids = {str(x).strip() for x in filtered_item_ids if pd.notna(x) and str(x).strip()}
        if not allowed_ids:
            return pd.DataFrame(), []
        items_df = items_df[items_df['ID'].astype(str).str.strip().isin(allowed_ids)].copy()
        if items_df.empty:
            return pd.DataFrame(), []

    stage_cols = _detect_stage_date_columns(items_df, bottlenecks_df=bottlenecks_df)
    if len(stage_cols) < 2:
        return pd.DataFrame(), []

    stage_dates = items_df[stage_cols].copy()
    for col in stage_cols:
        stage_dates[col] = pd.to_datetime(stage_dates[col], dayfirst=True, errors='coerce')

    snapshots = pd.to_datetime(df_cfd_macro['Data'], errors='coerce').dropna()
    snapshots = pd.DatetimeIndex(sorted(snapshots.unique()))
    if snapshots.empty:
        return pd.DataFrame(), []

    rows = []
    stage_cols_no_done = [c for c in stage_cols if str(c).strip().lower() != 'done']
    for snapshot in snapshots:
        reached = pd.DataFrame(index=stage_dates.index)
        for col in stage_cols:
            reached[col] = stage_dates[col].notna() & (stage_dates[col] <= snapshot)

        row = {'Data': snapshot}
        for i, stage in enumerate(stage_cols):
            is_here = reached[stage].copy()
            if i < len(stage_cols) - 1:
                later_cols = stage_cols[i + 1:]
                if later_cols:
                    progressed_after = reached[later_cols].any(axis=1)
                    is_here = is_here & (~progressed_after)
            row[f'raw::{stage}'] = float(is_here.sum())
        rows.append(row)

    detailed = pd.DataFrame(rows)
    if detailed.empty:
        return pd.DataFrame(), []

    cumulative_next = pd.Series(np.zeros(len(detailed)), index=detailed.index, dtype='float64')
    for stage in reversed(stage_cols):
        cumulative_next = cumulative_next + detailed[f'raw::{stage}']
        detailed[f'cum::{stage}'] = cumulative_next

    stages = stage_cols_no_done + ([s for s in stage_cols if str(s).strip().lower() == 'done'][:1])
    return detailed, stages


def _hex_to_rgba(hex_color, alpha):
    color = str(hex_color or '').strip().lstrip('#')
    if len(color) != 6:
        return f'rgba(120,120,120,{alpha})'
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except ValueError:
        return f'rgba(120,120,120,{alpha})'
    return f'rgba({r},{g},{b},{alpha})'


def _cfd_stage_color(stage_name):
    stage = normalize_text(stage_name)
    vivid_defaults = [
        '#ff9800', '#00bcd4', '#cddc39', '#8bc34a', '#9c27b0', '#03a9f4',
        '#ff5722', '#795548', '#e91e63', '#607d8b', '#3f51b5', '#009688',
    ]
    mapping_rules = [
        (['done', 'pronto', 'concluido', 'concluído'], '#d50000'),
        (['backlog'], '#ff9800'),
        (['triag'], '#4db6ac'),
        (['ready to start', 'ready for dev', 'ready for development', 'ready for de'], '#26c6da'),
        (['in progress', 'inprogress', 'development', 'execucao', 'execução'], '#c0ca33'),
        (['ready for code review'], '#ef5350'),
        (['code review'], '#43a047'),
        (['ready for testing', 'ready for test', 'qa'], '#1e88e5'),
        (['testing / qa', 'testing/qa', 'testing qa'], '#8d6e63'),
        (['ready to staging', 'ready for staging'], '#b8860b'),
        (['staging'], '#00897b'),
        (['ready for production', 'production'], '#7cb342'),
    ]
    for keys, color in mapping_rules:
        if any(k in stage for k in keys):
            return color
    digest = hashlib.sha256(str(stage_name).encode('utf-8')).hexdigest()
    return vivid_defaults[int(digest[:8], 16) % len(vivid_defaults)]


def _compute_cfd_trend_line(dates, values):
    if dates is None or values is None:
        return None
    x_dates = pd.to_datetime(pd.Series(dates), errors='coerce')
    y_values = pd.to_numeric(pd.Series(values), errors='coerce')
    mask = x_dates.notna() & y_values.notna()
    x_dates = x_dates[mask]
    y_values = y_values[mask]
    if x_dates.empty or y_values.empty or len(x_dates) < 2:
        return None

    x_days = (x_dates - x_dates.min()).dt.total_seconds() / 86400.0
    if len(np.unique(x_days.values)) < 2:
        return None

    slope, intercept = np.polyfit(x_days.values, y_values.values, 1)
    if not np.isfinite(slope) or not np.isfinite(intercept):
        return None
    trend_y = intercept + slope * x_days.values
    if not np.isfinite(trend_y).all():
        return None

    return {
        'dates': x_dates.tolist(),
        'trend': trend_y,
        'slope': float(slope),
    }


def _select_cfd_rate_stages(stages):
    if not stages:
        return []

    triagem_stage = None
    done_stage = None
    for stage in stages:
        normalized = normalize_text(stage)
        if triagem_stage is None and 'triag' in normalized:
            triagem_stage = stage
        if done_stage is None and any(token in normalized for token in ['done', 'conclu', 'pronto']):
            done_stage = stage

    if triagem_stage is None:
        triagem_stage = stages[0]

    selected = []
    if triagem_stage:
        selected.append(triagem_stage)
    if done_stage and done_stage not in selected:
        selected.append(done_stage)
    return selected


def create_cfd_figure(df_cfd, bottlenecks_df=None, projeto=None, filtered_item_ids=None):
    """Creates a CFD with macro mode and optional detailed stage mode (exact from downstream CSV)."""
    if df_cfd is None or df_cfd.empty:
        return {}

    fig = go.Figure()
    macro_colors = {
        'Pronto': '#d50000',
        'Em Progresso': '#c0ca33',
        'Backlog': '#ff9800',
    }
    macro_raw_map = {
        'Pronto': 'Pronto_raw',
        'Em Progresso': 'Em Progresso_raw',
        'Backlog': 'Backlog_raw',
    }

    macro_trace_indices = []
    macro_annotations = [{
        'text': 'Macro (exato): usa datas reais de Backlog / Em Progresso / Pronto.',
        'xref': 'paper', 'yref': 'paper', 'x': 0, 'y': 1.15,
        'showarrow': False, 'align': 'left', 'font': {'size': 11, 'color': '#555'}
    }]
    detailed_annotations = [{
        'text': 'Detalhado (exato): usa datas por etapa do CSV downstream do projeto.',
        'xref': 'paper', 'yref': 'paper', 'x': 0, 'y': 1.15,
        'showarrow': False, 'align': 'left', 'font': {'size': 11, 'color': '#555'}
    }]
    for stage in ['Pronto', 'Em Progresso', 'Backlog']:
        stage_color = macro_colors[stage]
        raw_col = macro_raw_map[stage]
        trace = go.Scatter(
            x=df_cfd['Data'],
            y=df_cfd[raw_col],
            mode='lines',
            name=stage,
            line=dict(width=1.8, color=stage_color, shape='hv'),
            stackgroup='macro',
            fillcolor=_hex_to_rgba(stage_color, 0.82),
            customdata=df_cfd[[raw_col, stage]].values,
            hovertemplate=(
                'Modo: Macro (exato)<br>'
                'Data: %{x|%Y-%m-%d}<br>'
                f'Faixa: {stage}<br>'
                'Itens na etapa: %{y:.0f}<br>'
                'Total acumulado: %{customdata[1]:.0f}<extra></extra>'
            ),
            visible=True,
        )
        fig.add_trace(trace)
        macro_trace_indices.append(len(fig.data) - 1)

    detailed_trace_indices = []
    detailed_df, detailed_stages = build_detailed_cfd_exact_dataframe(
        df_cfd,
        projeto=projeto,
        bottlenecks_df=bottlenecks_df,
        filtered_item_ids=filtered_item_ids,
    )
    if not detailed_df.empty and detailed_stages:
        reversed_plot_order = list(reversed(detailed_stages))
        color_by_stage = {
            stage: _cfd_stage_color(stage) for stage in detailed_stages
        }
        if 'Done' in color_by_stage:
            color_by_stage['Done'] = '#d50000'

        for idx, stage in enumerate(reversed_plot_order):
            raw_col = f'raw::{stage}'
            line_color = color_by_stage.get(stage, '#666')
            total_col = f'cum::{stage}'
            fig.add_trace(go.Scatter(
                x=detailed_df['Data'],
                y=detailed_df[raw_col],
                mode='lines',
                name=stage,
                line=dict(width=1.35, color=line_color, shape='hv'),
                stackgroup='detailed',
                fillcolor=_hex_to_rgba(line_color, 0.86),
                customdata=detailed_df[[total_col]].values,
                hovertemplate=(
                    'Modo: Detalhado por Etapas (exato)<br>'
                    'Data: %{x|%Y-%m-%d}<br>'
                    f'Faixa: {stage}<br>'
                    'Itens na etapa: %{y:.0f}<br>'
                    'Total acumulado: %{customdata[0]:.0f}<extra></extra>'
                ),
                visible=False,
            ))
            detailed_trace_indices.append(len(fig.data) - 1)

        for stage in _select_cfd_rate_stages(detailed_stages):
            trend_info = _compute_cfd_trend_line(
                detailed_df['Data'],
                detailed_df.get(f'cum::{stage}')
            )
            if trend_info is None:
                continue

            fig.add_trace(go.Scatter(
                x=trend_info['dates'],
                y=trend_info['trend'],
                mode='lines',
                name=f'{stage} (tendência)',
                line=dict(width=2.4, color='rgba(70,70,70,0.88)'),
                hovertemplate=(
                    f'{stage}: {trend_info["slope"]:.2f} (items/day)'
                    '<extra></extra>'
                ),
                showlegend=False,
                visible=False,
            ))
            detailed_trace_indices.append(len(fig.data) - 1)

            label_idx = int(len(trend_info['dates']) * 0.45)
            label_idx = max(0, min(label_idx, len(trend_info['dates']) - 1))
            detailed_annotations.append({
                'text': f'{stage}: {trend_info["slope"]:.2f} (items/day)',
                'xref': 'x',
                'yref': 'y',
                'x': trend_info['dates'][label_idx],
                'y': float(trend_info['trend'][label_idx]),
                'showarrow': False,
                'font': {'size': 11, 'color': '#ffffff'},
                'bgcolor': 'rgba(0,0,0,0.92)',
                'bordercolor': 'rgba(0,0,0,0.92)',
                'borderpad': 4,
                'align': 'left',
            })

    fig.update_layout(
        title='Cumulative Flow Diagram (CFD)',
        xaxis_title='Data',
        yaxis_title='Itens',
        template='plotly_white',
        height=600,
        margin=dict(t=110, b=150, l=70, r=30),
        legend_title_text='Etapa',
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        hovermode='x unified',
        hoverlabel=dict(bgcolor='white'),
        xaxis=dict(
            tickformat='%d/%m/%Y',
            showgrid=True,
            gridcolor='rgba(15,23,42,0.08)',
            linecolor='rgba(15,23,42,0.15)',
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(15,23,42,0.08)',
            zeroline=False,
            linecolor='rgba(15,23,42,0.15)',
            rangemode='tozero',
        ),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.22,
            xanchor='left',
            x=0,
            bgcolor='rgba(255,255,255,0.92)',
            bordercolor='rgba(15,23,42,0.10)',
            borderwidth=1,
            entrywidth=150,
            entrywidthmode='pixels',
            traceorder='normal',
        ),
    )

    if detailed_trace_indices:
        total_traces = len(fig.data)
        macro_visible = [i in macro_trace_indices for i in range(total_traces)]
        detailed_visible = [i in detailed_trace_indices for i in range(total_traces)]
        fig.update_layout(
            updatemenus=[{
                'type': 'buttons',
                'direction': 'right',
                'x': 0.0,
                'y': 1.28,
                'showactive': True,
                'bgcolor': 'rgba(255,255,255,0.95)',
                'bordercolor': 'rgba(15,23,42,0.15)',
                'borderwidth': 1,
                'buttons': [
                    {
                        'label': 'Macro (exato)',
                        'method': 'update',
                        'args': [
                            {'visible': macro_visible},
                            {'annotations': macro_annotations}
                        ]
                    },
                    {
                        'label': 'Detalhado por Etapas (exato)',
                        'method': 'update',
                        'args': [
                            {'visible': detailed_visible},
                            {'annotations': detailed_annotations}
                        ]
                    },
                ],
            }],
            annotations=macro_annotations,
        )
    else:
        unavailable_reason = _get_cfd_detailed_unavailable_reason(
            projeto=projeto,
            filtered_item_ids=filtered_item_ids,
            bottlenecks_df=bottlenecks_df,
        )
        fig.update_layout(
            annotations=[{
                'text': f'Modo detalhado indisponível: {unavailable_reason}',
                'xref': 'paper', 'yref': 'paper', 'x': 0, 'y': 1.15,
                'showarrow': False, 'align': 'left', 'font': {'size': 11, 'color': '#777'}
            }]
        )
    return fig


def _get_cfd_detailed_unavailable_reason(projeto=None, filtered_item_ids=None, bottlenecks_df=None):
    if not projeto:
        return 'selecione um projeto para carregar o CSV downstream detalhado (`*-data.csv`).'

    items_df = load_project_downstream_items_csv(projeto)
    if items_df is None or items_df.empty:
        return (
            f'CSV downstream (`*-data.csv`) não encontrado para {projeto} '
            'nas pastas de dados/URLs configuradas.'
        )

    if filtered_item_ids is not None:
        allowed_ids = {str(x).strip() for x in filtered_item_ids if pd.notna(x) and str(x).strip()}
        if not allowed_ids:
            return 'o filtro atual não possui itens concluídos (escopo do modo detalhado).'
        if 'ID' in items_df.columns:
            id_set = set(items_df['ID'].astype(str).str.strip())
            if not id_set.intersection(allowed_ids):
                return 'os itens concluídos do filtro não foram encontrados no CSV downstream do projeto.'

    stage_cols = _detect_stage_date_columns(items_df, bottlenecks_df=bottlenecks_df)
    if len(stage_cols) < 2:
        return 'o CSV downstream não tem ao menos 2 etapas com datas válidas para montar o gráfico.'

    return 'dados insuficientes para o recorte atual.'


def build_cfd_summary_payload(
    df_cfd,
    projeto=None,
    bottlenecks_df=None,
    filtered_item_ids=None,
    start_ts=None,
    end_ts=None,
    arrivals_period=None,
    throughput_period=None,
):
    payload = {
        'meta': {},
        'macro': None,
        'detailed': None,
        'stage_cycle_days': {},
    }
    if df_cfd is None or df_cfd.empty:
        return payload

    if start_ts is not None and end_ts is not None and pd.notna(start_ts) and pd.notna(end_ts):
        payload['meta'].update({
            'start_date': pd.to_datetime(start_ts).strftime('%Y-%m-%d'),
            'end_date': pd.to_datetime(end_ts).strftime('%Y-%m-%d'),
            'days': int((pd.to_datetime(end_ts) - pd.to_datetime(start_ts)).days) + 1,
        })
    if projeto:
        payload['meta']['projeto'] = str(projeto)
    if arrivals_period is not None:
        payload['meta']['arrivals_period'] = int(arrivals_period)
    if throughput_period is not None:
        payload['meta']['throughput_period'] = int(throughput_period)
    if filtered_item_ids is not None:
        payload['meta']['filtered_done_items'] = int(sum(1 for x in filtered_item_ids if pd.notna(x) and str(x).strip()))

    payload['macro'] = {
        'dates': pd.to_datetime(df_cfd['Data']).dt.strftime('%Y-%m-%d').tolist(),
        'stages': ['Backlog', 'Em Progresso', 'Pronto'],
        'raw': {
            'Backlog': pd.to_numeric(df_cfd.get('Backlog_raw'), errors='coerce').fillna(0).astype(float).tolist(),
            'Em Progresso': pd.to_numeric(df_cfd.get('Em Progresso_raw'), errors='coerce').fillna(0).astype(float).tolist(),
            'Pronto': pd.to_numeric(df_cfd.get('Pronto_raw'), errors='coerce').fillna(0).astype(float).tolist(),
        },
        'cum': {
            'Backlog': pd.to_numeric(df_cfd.get('Backlog'), errors='coerce').fillna(0).astype(float).tolist(),
            'Em Progresso': pd.to_numeric(df_cfd.get('Em Progresso'), errors='coerce').fillna(0).astype(float).tolist(),
            'Pronto': pd.to_numeric(df_cfd.get('Pronto'), errors='coerce').fillna(0).astype(float).tolist(),
        },
    }

    detailed_df, detailed_stages = build_detailed_cfd_exact_dataframe(
        df_cfd,
        projeto=projeto,
        bottlenecks_df=bottlenecks_df,
        filtered_item_ids=filtered_item_ids,
    )
    if not detailed_df.empty and detailed_stages:
        detailed_dates = pd.to_datetime(detailed_df['Data']).dt.strftime('%Y-%m-%d').tolist()
        payload['detailed'] = {
            'dates': detailed_dates,
            'stages': detailed_stages,
            'raw': {},
            'cum': {},
        }
        for stage in detailed_stages:
            payload['detailed']['raw'][stage] = pd.to_numeric(detailed_df.get(f'raw::{stage}'), errors='coerce').fillna(0).astype(float).tolist()
            payload['detailed']['cum'][stage] = pd.to_numeric(detailed_df.get(f'cum::{stage}'), errors='coerce').fillna(0).astype(float).tolist()

    if bottlenecks_df is not None and not bottlenecks_df.empty and {'Etapa', 'Tempo Médio (dias)'}.issubset(bottlenecks_df.columns):
        tmp = bottlenecks_df[['Etapa', 'Tempo Médio (dias)']].copy()
        tmp['Tempo Médio (dias)'] = pd.to_numeric(tmp['Tempo Médio (dias)'], errors='coerce')
        tmp = tmp.dropna()
        payload['stage_cycle_days'] = {
            str(row['Etapa']): float(row['Tempo Médio (dias)'])
            for _, row in tmp.iterrows()
        }

    return payload


def create_cfd_summary_panel(summary_payload, selected_date=None):
    if not summary_payload or not isinstance(summary_payload, dict):
        return html.Div('Sem dados de sumário do CFD.', style={'color': '#666'})

    meta = summary_payload.get('meta') or {}
    macro = summary_payload.get('macro')
    detailed = summary_payload.get('detailed')
    if not macro:
        return html.Div('Sem dados suficientes para estatísticas sumárias do CFD.', style={'color': '#666'})

    dates = detailed.get('dates') if detailed else macro.get('dates', [])
    if not dates:
        return html.Div('Sem snapshots disponíveis para o CFD.', style={'color': '#666'})

    selected_str = None
    if selected_date:
        try:
            selected_str = pd.to_datetime(selected_date).strftime('%Y-%m-%d')
        except Exception:
            selected_str = None
    if selected_str not in set(dates):
        selected_str = dates[-1]
    idx = dates.index(selected_str)

    stage_cycle_map = summary_payload.get('stage_cycle_days') or {}
    rows = []
    total_wip = 0.0
    total_completed = 0.0
    total_system = 0.0

    if detailed:
        for stage in detailed.get('stages', []):
            stage_raw = float((detailed.get('raw', {}).get(stage, [0]) or [0])[idx])
            stage_cum = float((detailed.get('cum', {}).get(stage, [0]) or [0])[idx])
            total_system = max(total_system, stage_cum)
            if normalize_text(stage) in {'done', 'pronto', 'concluido', 'concluído'}:
                total_completed = stage_raw
            else:
                total_wip += stage_raw
            rows.append({
                'Etapa': stage,
                'Cycle Time* (dias)': f"{stage_cycle_map.get(stage, np.nan):.2f}" if stage in stage_cycle_map else '—',
                'WIP': int(round(stage_raw)),
                'Acumulado': int(round(stage_cum)),
            })
    else:
        for stage in ['Backlog', 'Em Progresso', 'Pronto']:
            stage_raw = float((macro.get('raw', {}).get(stage, [0]) or [0])[idx])
            stage_cum = float((macro.get('cum', {}).get(stage, [0]) or [0])[idx])
            total_system = max(total_system, stage_cum)
            if stage == 'Pronto':
                total_completed = stage_raw
            else:
                total_wip += stage_raw
            rows.append({
                'Etapa': stage,
                'Cycle Time* (dias)': '—',
                'WIP': int(round(stage_raw)),
                'Acumulado': int(round(stage_cum)),
            })

    system_row = {
        'Etapa': 'System',
        'Cycle Time* (dias)': '—',
        'WIP': int(round(total_wip)),
        'Acumulado': int(round(total_system)),
    }
    rows = [system_row] + rows

    period_label = ''
    if meta.get('start_date') and meta.get('end_date'):
        period_label = f"{meta['start_date']} a {meta['end_date']} ({meta.get('days', '—')} dias)"

    stat_chips = html.Div([
        html.Div([html.Div('Chegadas (período)', style={'fontSize': '11px', 'color': '#666'}), html.Strong(str(meta.get('arrivals_period', '—')))], style=_cfd_stat_chip_style()),
        html.Div([html.Div('Throughput (período)', style={'fontSize': '11px', 'color': '#666'}), html.Strong(str(meta.get('throughput_period', '—')))], style=_cfd_stat_chip_style()),
        html.Div([html.Div('Concluídos no filtro', style={'fontSize': '11px', 'color': '#666'}), html.Strong(str(meta.get('filtered_done_items', '—')))], style=_cfd_stat_chip_style()),
        html.Div([html.Div('Snapshot', style={'fontSize': '11px', 'color': '#666'}), html.Strong(selected_str)], style=_cfd_stat_chip_style()),
    ], style={'display': 'flex', 'gap': '10px', 'flexWrap': 'wrap', 'marginBottom': '10px'})

    table = dash_table.DataTable(
        columns=[{"name": c, "id": c} for c in ['Etapa', 'Cycle Time* (dias)', 'WIP', 'Acumulado']],
        data=rows,
        style_cell={'textAlign': 'left', 'padding': '6px'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        style_data_conditional=[
            {'if': {'row_index': 0}, 'backgroundColor': '#f3f4f6', 'fontWeight': 'bold'},
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
        ],
        style_table={'maxHeight': '320px', 'overflowY': 'auto'},
        page_action='none',
    )

    return html.Div([
        html.H4('Summary Statistics', style={'marginTop': '0', 'marginBottom': '4px'}),
        html.Div(period_label, style={'fontSize': '12px', 'color': '#666', 'marginBottom': '8px'}),
        stat_chips,
        table,
        html.Div('*Cycle Time por etapa vem do gráfico de gargalos (tempo médio da etapa).', style={'fontSize': '11px', 'color': '#666', 'marginTop': '8px'})
    ], style={
        'border': '1px solid #e5e7eb',
        'borderRadius': '10px',
        'padding': '12px',
        'backgroundColor': '#fff'
    })


def _cfd_stat_chip_style():
    return {
        'border': '1px solid #e5e7eb',
        'borderRadius': '8px',
        'padding': '8px 10px',
        'backgroundColor': '#fafafa',
        'minWidth': '140px',
    }


def classify_urgency_label(row):
    """Classifica urgência priorizando Classe de Serviço e usando Prioridade como fallback."""
    classe_servico = normalize_text(row.get('ClasseServico', ''))
    prioridade = normalize_text(row.get('Prioridade', ''))

    if classe_servico:
        if is_highest_alias(classe_servico):
            return 'Highest'
        if any(k in classe_servico for k in ['fixed date', 'fixed_date', 'deadline', 'prazo', 'data fixa']):
            return 'Data Fixa'
        if any(k in classe_servico for k in ['intang', 'risco', 'risk', 'compliance', 'regulatorio', 'regulatory']):
            return 'Intangível'
        if any(k in classe_servico for k in ['standard', 'padrao', 'normal', 'default']):
            return 'Padrão'
        return canonicalize_highest_label(row.get('ClasseServico'))

    if prioridade:
        if is_highest_alias(prioridade):
            return 'Highest'
        if any(k in prioridade for k in ['high', 'alta']):
            return 'Alta'
        if any(k in prioridade for k in ['medium', 'media', 'normal']):
            return 'Média'
        if any(k in prioridade for k in ['low', 'lowest', 'baixa']):
            return 'Baixa'
        return canonicalize_highest_label(row.get('Prioridade'))

    return 'Não classificado'


def resolve_project_sla_days(projeto, default=8.0):
    sla_default = float(default)
    try:
        sla_default = float(os.getenv('FLOW_PMO_ONE_PAGE_SLA_DAYS', str(default)))
    except Exception:
        sla_default = float(default)
    sla_map = parse_json_env('FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP', {})
    if not projeto:
        return sla_default
    try:
        return float(sla_map.get(str(projeto).upper(), sla_default))
    except Exception:
        return sla_default


_TYPE_SLA_DEFAULTS = {'bug': 5, 'historia': 15, 'feature': 30, 'epico': 90}


_TYPE_CATEGORY_ORDER = ['bug', 'historia', 'feature', 'epico']


_TYPE_SLA_DISPLAY_LABELS = {
    'bug': 'Bug / Suporte',
    'historia': 'Histórias',
    'feature': 'Features',
    'epico': 'Épicos',
}


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


def _resolve_type_sla_config():
    """Retorna dict categoria → dias, mesclando defaults com FLOW_PMO_TYPE_SLA_DAYS do .env."""
    cfg = dict(_TYPE_SLA_DEFAULTS)
    overrides = parse_json_env('FLOW_PMO_TYPE_SLA_DAYS', {})
    for k, v in overrides.items():
        if k in cfg:
            try:
                cfg[k] = float(v)
            except Exception:
                pass
    return cfg


def get_type_sla_display():
    """Retorna lista de (label, dias) para o card de referência, refletindo env vars."""
    cfg = _resolve_type_sla_config()
    return [(_TYPE_SLA_DISPLAY_LABELS[k], int(cfg[k])) for k in _TYPE_CATEGORY_ORDER]


def get_type_sla_days(tipo_norm, default=15):
    """Retorna o SLA de referência (dias) para um TipoNorm, respeitando env vars."""
    if not tipo_norm or (isinstance(tipo_norm, float) and pd.isna(tipo_norm)):
        return default
    cat = _TYPE_NORM_TO_CATEGORY.get(str(tipo_norm).strip().lower())
    if cat:
        return _resolve_type_sla_config().get(cat, default)
    return default


def infer_service_bucket_config(start_ts, end_ts):
    days_span = max(1, int((pd.Timestamp(end_ts).normalize() - pd.Timestamp(start_ts).normalize()).days + 1))
    if days_span <= 120:
        return 'W-MON', 'Semana', 'semanal'
    return 'MS', 'Mês', 'mensal'


def build_service_bucket_index(start_ts, end_ts, bucket_freq):
    if bucket_freq == 'MS':
        return pd.period_range(start=pd.Timestamp(start_ts), end=pd.Timestamp(end_ts), freq='M').to_timestamp()
    weeks = pd.date_range(start=pd.Timestamp(start_ts), end=pd.Timestamp(end_ts) + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
    if len(weeks) >= 2:
        return pd.DatetimeIndex(weeks[:-1])
    return pd.DatetimeIndex([weekly_bucket_start(pd.Series(pd.to_datetime([start_ts]))).iloc[0]])


def _service_dimension_label(series, empty_label='Não classificado'):
    values = series.fillna('').astype(str).str.strip()
    values = values.replace('', empty_label)
    return values


def build_service_lead_time_breakdown(done_df, dimension_col, dimension_label, lead_col='LeadTime_Selected_Dias', sla_days=None, sla_col=None):
    empty = pd.DataFrame(columns=[dimension_label, 'Itens', 'Lead Médio', 'Lead P50', 'Lead P85', '% SLA', 'SLA Ref (d)'])
    if done_df is None or done_df.empty or dimension_col not in done_df.columns:
        return empty

    base = done_df.copy()
    base[dimension_label] = _service_dimension_label(base[dimension_col])
    base['LeadMetric'] = pd.to_numeric(base.get(lead_col), errors='coerce')
    base = base.dropna(subset=['LeadMetric'])
    base = base[base['LeadMetric'] >= 0]
    if base.empty:
        return empty

    summary = (
        base.groupby(dimension_label, dropna=False)
        .agg(
            Itens=('LeadMetric', 'size'),
            **{
                'Lead Médio': ('LeadMetric', 'mean'),
                'Lead P50': ('LeadMetric', lambda s: exact_empirical_percentile(s.dropna(), 0.50) if not s.dropna().empty else np.nan),
                'Lead P85': ('LeadMetric', lambda s: exact_empirical_percentile(s.dropna(), 0.85) if not s.dropna().empty else np.nan),
            }
        )
        .reset_index()
        .sort_values(['Itens', 'Lead P85', dimension_label], ascending=[False, False, True], ignore_index=True)
    )
    if sla_col and sla_col in base.columns:
        # Per-item SLA: each row compared against its own SLA threshold
        _sla_ref = pd.to_numeric(base[sla_col], errors='coerce')
        base = base.assign(InSLA=(base['LeadMetric'] <= _sla_ref) & _sla_ref.notna())
        sla_share = (
            base.groupby(dimension_label, dropna=False)['InSLA']
            .mean()
            .mul(100.0)
            .reset_index(name='% SLA')
        )
        sla_ref_per_group = (
            base.groupby(dimension_label, dropna=False)[sla_col]
            .median()
            .round(0)
            .astype(int)
            .reset_index()
            .rename(columns={sla_col: 'SLA Ref (d)'})
        )
        summary = summary.merge(sla_share, on=dimension_label, how='left')
        summary = summary.merge(sla_ref_per_group, on=dimension_label, how='left')
    elif sla_days and sla_days > 0:
        sla_share = (
            base.assign(InSLA=base['LeadMetric'] <= float(sla_days))
            .groupby(dimension_label, dropna=False)['InSLA']
            .mean()
            .mul(100.0)
            .reset_index(name='% SLA')
        )
        summary = summary.merge(sla_share, on=dimension_label, how='left')
        summary['SLA Ref (d)'] = int(sla_days)
    else:
        summary['% SLA'] = np.nan
        summary['SLA Ref (d)'] = np.nan

    for col in ['Lead Médio', 'Lead P50', 'Lead P85', '% SLA']:
        summary[col] = pd.to_numeric(summary[col], errors='coerce').round(1)
    return summary


def build_throughput_series(
    df,
    dimension_col,
    dimension_label,
    temporal=False,
    start_ts=None,
    end_ts=None,
    bucket_freq='W-MON',
):
    """Breakdown de throughput por dimensão.

    temporal=False (padrão): contagem simples, retorna
        [dimension_col, 'Throughput', 'Percentual', 'Barra'].
    temporal=True: distribuição por bucket (requer start_ts/end_ts), retorna
        [dimension_label, 'Itens Entregues', 'Média/Bucket', 'P15', 'P50', 'P85', 'Máx Bucket'].
    """
    if not temporal:
        if df is None or getattr(df, 'empty', True) or dimension_col not in df.columns:
            return pd.DataFrame(columns=[dimension_col, 'Throughput', 'Percentual', 'Barra'])
        breakdown = (
            df[dimension_col]
            .fillna('Não classificado')
            .astype(str)
            .value_counts()
            .reset_index()
            .rename(columns={'index': dimension_col, 'count': 'Throughput'})
        )
        total = breakdown['Throughput'].sum()
        breakdown['Percentual'] = (breakdown['Throughput'] / total * 100) if total > 0 else 0.0
        breakdown['Barra'] = dimension_label
        return breakdown

    # temporal=True
    empty = pd.DataFrame(columns=[dimension_label, 'Itens Entregues', 'Média/Bucket', 'P15', 'P50', 'P85', 'Máx Bucket'])
    if df is None or getattr(df, 'empty', True) or dimension_col not in df.columns:
        return empty

    base = df.copy()
    base['DataDone'] = pd.to_datetime(base.get('DataDone'), errors='coerce')
    base = base.dropna(subset=['DataDone'])
    if base.empty:
        return empty
    base[dimension_label] = _service_dimension_label(base[dimension_col])
    if bucket_freq == 'MS':
        base['Bucket'] = base['DataDone'].dt.to_period('M').dt.start_time
    else:
        base['Bucket'] = weekly_bucket_start(base['DataDone'])
    bucket_range = build_service_bucket_index(start_ts, end_ts, bucket_freq)
    bucket_range = pd.DatetimeIndex(bucket_range).unique().sort_values()
    if len(bucket_range) == 0:
        bucket_range = pd.DatetimeIndex([pd.Timestamp(start_ts).normalize()])

    dims = sorted(base[dimension_label].dropna().unique().tolist(), key=lambda x: str(x))
    if not dims:
        return empty

    counts = (
        base.groupby(['Bucket', dimension_label], dropna=False)
        .size()
        .rename('Throughput')
        .reset_index()
    )
    full_index = pd.MultiIndex.from_product([bucket_range, dims], names=['Bucket', dimension_label])
    counts = (
        counts.set_index(['Bucket', dimension_label])
        .reindex(full_index, fill_value=0)
        .reset_index()
    )
    summary = (
        counts.groupby(dimension_label, dropna=False)['Throughput']
        .agg(
            **{
                'Itens Entregues': 'sum',
                'Média/Bucket': 'mean',
                'P15': lambda s: exact_empirical_percentile(s.dropna(), 0.15) if not s.dropna().empty else np.nan,
                'P50': lambda s: exact_empirical_percentile(s.dropna(), 0.50) if not s.dropna().empty else np.nan,
                'P85': lambda s: exact_empirical_percentile(s.dropna(), 0.85) if not s.dropna().empty else np.nan,
                'Máx Bucket': 'max',
            }
        )
        .reset_index()
        .sort_values(['Itens Entregues', 'P85', dimension_label], ascending=[False, False, True], ignore_index=True)
    )
    for col in ['Média/Bucket', 'P15', 'P50', 'P85']:
        summary[col] = pd.to_numeric(summary[col], errors='coerce').round(1)
    summary['Itens Entregues'] = pd.to_numeric(summary['Itens Entregues'], errors='coerce').fillna(0).astype(int)
    summary['Máx Bucket'] = pd.to_numeric(summary['Máx Bucket'], errors='coerce').fillna(0).astype(int)
    return summary


build_service_throughput_breakdown = lambda done_df, dimension_col, dimension_label, start_ts, end_ts, bucket_freq='W-MON': build_throughput_series(done_df, dimension_col, dimension_label, temporal=True, start_ts=start_ts, end_ts=end_ts, bucket_freq=bucket_freq)


def build_live_wip_snapshot(df_source, end_ts, projeto=None, selected_stages=None, stage_map=None):
    if df_source is None or getattr(df_source, 'empty', True):
        return pd.DataFrame()

    active = df_source.copy()
    active['DataInProgress'] = pd.to_datetime(active.get('DataInProgress'), errors='coerce')
    active['DataDone'] = pd.to_datetime(active.get('DataDone'), errors='coerce')
    wip_start_ref = active['DataInProgress'].copy()
    if selected_stages:
        if 'DataBacklog' in active.columns:
            wip_start_ref = wip_start_ref.combine_first(pd.to_datetime(active.get('DataBacklog'), errors='coerce'))
        wip_start_ref = wip_start_ref.combine_first(resolve_creation_date_series(active))
    active['WIPStartRef'] = pd.to_datetime(wip_start_ref, errors='coerce')
    active = active[
        active['WIPStartRef'].notna() &
        (active['WIPStartRef'] <= end_ts) &
        (active['DataDone'].isna() | (active['DataDone'] > end_ts))
    ].copy()
    active = filter_items_by_current_stage(
        active,
        projeto=projeto,
        selected_stages=selected_stages,
        stage_map=stage_map,
    )
    if active.empty:
        return active

    active['WIPAge'] = (pd.Timestamp(end_ts) - active['WIPStartRef']).dt.total_seconds() / 86400.0
    active['WIPAge'] = pd.to_numeric(active['WIPAge'], errors='coerce')
    return active


def build_service_wip_breakdown(df_scope, end_ts, dimension_col, dimension_label):
    empty = pd.DataFrame(columns=[dimension_label, 'Itens em WIP', 'Age Médio', 'Age P85', 'Mais Antigo'])
    if df_scope is None or df_scope.empty or dimension_col not in df_scope.columns:
        return empty

    active = df_scope.copy()
    if 'WIPAge' not in active.columns:
        active['DataInProgress'] = pd.to_datetime(active.get('DataInProgress'), errors='coerce')
        active['WIPAge'] = (pd.Timestamp(end_ts) - active['DataInProgress']).dt.total_seconds() / 86400.0
        active['WIPAge'] = pd.to_numeric(active['WIPAge'], errors='coerce')
    if active.empty:
        return empty

    active[dimension_label] = _service_dimension_label(active[dimension_col])
    summary = (
        active.groupby(dimension_label, dropna=False)
        .agg(
            **{
                'Itens em WIP': ('WIPAge', 'size'),
                'Age Médio': ('WIPAge', 'mean'),
                'Age P85': ('WIPAge', lambda s: exact_empirical_percentile(s.dropna(), 0.85) if not s.dropna().empty else np.nan),
                'Mais Antigo': ('WIPAge', 'max'),
            }
        )
        .reset_index()
        .sort_values(['Itens em WIP', 'Mais Antigo', dimension_label], ascending=[False, False, True], ignore_index=True)
    )
    for col in ['Age Médio', 'Age P85', 'Mais Antigo']:
        summary[col] = pd.to_numeric(summary[col], errors='coerce').round(1)
    summary['Itens em WIP'] = pd.to_numeric(summary['Itens em WIP'], errors='coerce').fillna(0).astype(int)
    return summary


build_throughput_breakdown = lambda df, dimension_col, dimension_label: build_throughput_series(df, dimension_col, dimension_label)


def _format_pct_br(value):
    if pd.isna(value):
        return ''
    return f'{float(value) * 100:.2f}%'.replace('.', ',')


def _format_month_label_pt_br(ts):
    ts = pd.Timestamp(ts)
    return f"{THROUGHPUT_BREAKDOWN_MONTH_ABBR.get(ts.month, ts.strftime('%b').lower())}-{ts.strftime('%y')}"


def _throughput_breakdown_product_key(row):
    for candidate in ('Projeto', 'Projeto Jira', 'Projeto PM'):
        project_key = _canonical_pm_product_key(row.get(candidate))
        if project_key in THROUGHPUT_BREAKDOWN_PRODUCT_ORDER:
            return project_key
    for candidate in ('ItemID', 'ID'):
        item_key = str(row.get(candidate) or '').strip().upper()
        if not item_key:
            continue
        prefix = item_key.split('-', 1)[0]
        project_key = _canonical_pm_product_key(prefix)
        if project_key in THROUGHPUT_BREAKDOWN_PRODUCT_ORDER:
            return project_key
    return ''


def build_monthly_product_throughput_breakdown(tp_done, reference_year):
    """Build monthly matrix for throughput breakdown by product."""
    columns = ['TIPO']
    for product_key in THROUGHPUT_BREAKDOWN_PRODUCT_ORDER:
        product_label = THROUGHPUT_BREAKDOWN_PRODUCT_LABELS[product_key]
        columns.extend([f'{product_label} % Evolução', f'{product_label} % Sustentação'])

    if tp_done is None or getattr(tp_done, 'empty', True) or 'DataDone' not in tp_done.columns:
        rows = []
        for month_start in pd.date_range(start=pd.Timestamp(year=reference_year, month=1, day=1), periods=12, freq='MS'):
            row = {'TIPO': _format_month_label_pt_br(month_start)}
            for product_key in THROUGHPUT_BREAKDOWN_PRODUCT_ORDER:
                product_label = THROUGHPUT_BREAKDOWN_PRODUCT_LABELS[product_key]
                row[f'{product_label} % Evolução'] = ''
                row[f'{product_label} % Sustentação'] = '100,00%'
            rows.append(row)
        return pd.DataFrame(rows, columns=columns)

    base = tp_done.copy()
    base['DataDone'] = pd.to_datetime(base['DataDone'], errors='coerce')
    base = base.dropna(subset=['DataDone']).copy()
    base = base[base['DataDone'].dt.year.eq(int(reference_year))].copy()
    base['ProdutoKey'] = base.apply(_throughput_breakdown_product_key, axis=1)
    base['TipoDemanda'] = base.get('TipoDemanda', pd.Series(TYPE_OTHER, index=base.index)).apply(canonicalize_demand_type)

    rows = []
    for month_start in pd.date_range(start=pd.Timestamp(year=reference_year, month=1, day=1), periods=12, freq='MS'):
        month_end = month_start + pd.offsets.MonthBegin(1)
        month_df = base[(base['DataDone'] >= month_start) & (base['DataDone'] < month_end)].copy()
        row = {'TIPO': _format_month_label_pt_br(month_start)}
        for product_key in THROUGHPUT_BREAKDOWN_PRODUCT_ORDER:
            product_label = THROUGHPUT_BREAKDOWN_PRODUCT_LABELS[product_key]
            product_df = month_df[month_df['ProdutoKey'] == product_key].copy()
            total = len(product_df)
            if total <= 0:
                evolution_pct = np.nan
                sustain_pct = 1.0
            else:
                evolution_count = int(product_df['TipoDemanda'].eq(TYPE_DEV).sum())
                sustain_count = total - evolution_count
                evolution_pct = (evolution_count / total) if evolution_count > 0 else np.nan
                sustain_pct = (sustain_count / total) if total > 0 else 1.0
            row[f'{product_label} % Evolução'] = _format_pct_br(evolution_pct)
            row[f'{product_label} % Sustentação'] = _format_pct_br(sustain_pct)
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def build_evolution_sustainability_breakdown(tp_done):
    """Aggregate delivered items into Evolução x Sustentação using the same rule as the monthly table."""
    if tp_done is None or getattr(tp_done, 'empty', True):
        return pd.DataFrame(columns=['CategoriaEntrega', 'Throughput', 'Percentual', 'Barra'])

    base = tp_done.copy()
    base['CategoriaEntrega'] = base.get('TipoDemanda', pd.Series(TYPE_OTHER, index=base.index)).apply(canonicalize_demand_type)
    base['CategoriaEntrega'] = np.where(base['CategoriaEntrega'].eq(TYPE_DEV), 'Evolução', 'Sustentação')
    breakdown = build_throughput_series(base, 'CategoriaEntrega', 'Throughput por Categoria de Entrega')
    if not breakdown.empty:
        desired_order = ['Evolução', 'Sustentação']
        breakdown['_ord'] = breakdown['CategoriaEntrega'].apply(
            lambda value: desired_order.index(value) if value in desired_order else len(desired_order)
        )
        breakdown = breakdown.sort_values(['_ord', 'Throughput'], ascending=[True, False]).drop(columns=['_ord'])
    return breakdown


def filter_done_to_month(tp_done, reference_ts):
    """Restrict delivered items to the month of the provided reference timestamp."""
    if tp_done is None or getattr(tp_done, 'empty', True) or 'DataDone' not in tp_done.columns:
        return pd.DataFrame(columns=getattr(tp_done, 'columns', []))
    ref_ts = pd.Timestamp(reference_ts)
    month_start = ref_ts.to_period('M').start_time
    month_end = month_start + pd.offsets.MonthBegin(1)
    base = tp_done.copy()
    base['DataDone'] = pd.to_datetime(base['DataDone'], errors='coerce')
    base = base.dropna(subset=['DataDone']).copy()
    return base[(base['DataDone'] >= month_start) & (base['DataDone'] < month_end)].copy()


def build_period_evolution_sustainability_breakdown(tp_done, start_ts, end_ts):
    """Build monthly stacked breakdown with one bar per period."""
    columns = ['Periodo', 'CategoriaEntrega', 'Throughput', 'Percentual', 'Barra']
    if tp_done is None or getattr(tp_done, 'empty', True) or 'DataDone' not in tp_done.columns:
        return pd.DataFrame(columns=columns)

    base = tp_done.copy()
    base['DataDone'] = pd.to_datetime(base['DataDone'], errors='coerce')
    base = base.dropna(subset=['DataDone']).copy()
    if base.empty:
        return pd.DataFrame(columns=columns)

    base['CategoriaEntrega'] = base.get('TipoDemanda', pd.Series(TYPE_OTHER, index=base.index)).apply(canonicalize_demand_type)
    base['CategoriaEntrega'] = np.where(base['CategoriaEntrega'].eq(TYPE_DEV), 'Evolução', 'Sustentação')

    period_starts = pd.date_range(
        start=pd.Timestamp(start_ts).to_period('M').start_time,
        end=pd.Timestamp(end_ts).to_period('M').start_time,
        freq='MS',
    )
    rows = []
    desired_order = ['Evolução', 'Sustentação']

    for month_start in period_starts:
        month_end = month_start + pd.offsets.MonthBegin(1)
        month_df = base[(base['DataDone'] >= month_start) & (base['DataDone'] < month_end)].copy()
        total = len(month_df)
        period_label = _format_month_label_pt_br(month_start)
        for category in desired_order:
            throughput = int(month_df['CategoriaEntrega'].eq(category).sum()) if total > 0 else 0
            percentual = ((throughput / total) * 100.0) if total > 0 else 0.0
            rows.append({
                'Periodo': period_label,
                'CategoriaEntrega': category,
                'Throughput': throughput,
                'Percentual': percentual,
                'Barra': period_label,
            })

    return pd.DataFrame(rows, columns=columns)


def build_monthly_product_original_type_breakdown(tp_done, reference_year):
    """Build monthly matrix by product and original Jira item type."""
    type_candidates = ['Tipo de Problema', 'WorkItemSubType', 'Tipo']
    type_col = next((col for col in type_candidates if tp_done is not None and col in tp_done.columns), None)
    if not type_col:
        return pd.DataFrame(columns=['TIPO']), []

    base = tp_done.copy()
    base['DataDone'] = pd.to_datetime(base['DataDone'], errors='coerce')
    base = base.dropna(subset=['DataDone']).copy()
    base = base[base['DataDone'].dt.year.eq(int(reference_year))].copy()
    base['ProdutoKey'] = base.apply(_throughput_breakdown_product_key, axis=1)
    base['TipoOriginalJira'] = base[type_col].fillna('').astype(str).str.strip()
    base.loc[base['TipoOriginalJira'].eq(''), 'TipoOriginalJira'] = 'Não classificado'

    if base.empty:
        return pd.DataFrame(columns=['TIPO']), []

    original_type_order = (
        base.groupby('TipoOriginalJira')
        .size()
        .reset_index(name='Throughput')
        .sort_values(['Throughput', 'TipoOriginalJira'], ascending=[False, True])['TipoOriginalJira']
        .tolist()
    )

    columns = ['TIPO']
    for product_key in THROUGHPUT_BREAKDOWN_PRODUCT_ORDER:
        product_label = THROUGHPUT_BREAKDOWN_PRODUCT_LABELS[product_key]
        for jira_type in original_type_order:
            columns.append(f'{product_label} | {jira_type}')

    rows = []
    for month_start in pd.date_range(start=pd.Timestamp(year=reference_year, month=1, day=1), periods=12, freq='MS'):
        month_end = month_start + pd.offsets.MonthBegin(1)
        month_df = base[(base['DataDone'] >= month_start) & (base['DataDone'] < month_end)].copy()
        row = {'TIPO': _format_month_label_pt_br(month_start)}
        for product_key in THROUGHPUT_BREAKDOWN_PRODUCT_ORDER:
            product_label = THROUGHPUT_BREAKDOWN_PRODUCT_LABELS[product_key]
            product_df = month_df[month_df['ProdutoKey'] == product_key].copy()
            total = len(product_df)
            for jira_type in original_type_order:
                col_name = f'{product_label} | {jira_type}'
                if total <= 0:
                    row[col_name] = ''
                    continue
                type_count = int(product_df['TipoOriginalJira'].eq(jira_type).sum())
                pct = (type_count / total) if type_count > 0 else np.nan
                row[col_name] = _format_pct_br(pct)
        rows.append(row)
    return pd.DataFrame(rows, columns=columns), original_type_order


def calculate_mm1_metrics(arrival_rate, service_rate):
    """Calcula indicadores de fila M/M/1 para taxa de chegada e vazão."""
    if service_rate <= 0 or arrival_rate < 0:
        return None
    if arrival_rate >= service_rate:
        return {
            'lambda': arrival_rate,
            'mu': service_rate,
            'rho': arrival_rate / service_rate if service_rate else np.nan,
            'Lq': np.inf,
            'Wq': np.inf,
            'W': np.inf,
        }

    rho = arrival_rate / service_rate
    lq = (rho ** 2) / (1 - rho)
    wq = lq / arrival_rate if arrival_rate > 0 else 0
    w = wq + (1 / service_rate)
    return {'lambda': arrival_rate, 'mu': service_rate, 'rho': rho, 'Lq': lq, 'Wq': wq, 'W': w}


def calculate_flow_efficiency(arrival_rate, service_rate):
    """Calcula pressão de fluxo (ρ=λ/μ) e eficiência de fluxo (1-ρ)."""
    if service_rate is None or pd.isna(service_rate) or service_rate <= 0:
        return np.nan, np.nan
    if arrival_rate is None or pd.isna(arrival_rate) or arrival_rate < 0:
        return np.nan, np.nan
    rho = arrival_rate / service_rate
    return rho, (1 - rho)


def compute_flow_bottlenecks(df):
    """Monta ranking de gargalos por etapa do fluxo com base no tempo médio em dias."""
    stage_columns = [
        ('Backlog', 'TempoBacklog_Dias'),
        ('Execução', 'TempoExecucao_Dias'),
        ('Bloqueio', 'TempoBloqueioDias'),
        ('Espera Intermediária', 'TempoEsperaIntermediariaDias'),
    ]

    rows = []
    for stage_name, col in stage_columns:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors='coerce').dropna()
        series = series[series >= 0]
        if series.empty:
            continue
        rows.append({
            'Etapa': stage_name,
            'Tempo Médio (dias)': float(series.mean()),
            'Tempo Mediano (dias)': float(series.median()),
            'P90 (dias)': float(series.quantile(0.90)),
            'Qtde Itens': int(series.shape[0]),
            'Vazão da Etapa (itens)': int(series.shape[0]),
        })

    bottlenecks_df = pd.DataFrame(rows)
    if not bottlenecks_df.empty:
        bottlenecks_df = bottlenecks_df.sort_values(
            by='Tempo Médio (dias)',
            ascending=False,
            ignore_index=True,
        )
    return bottlenecks_df


def load_project_bottlenecks_from_model(projeto):
    """Carrega gargalos da aba Fato_Gargalos do modelo PowerBI."""
    fato_gargalos = _df().fato_gargalos
    if not projeto or fato_gargalos.empty or 'Projeto' not in fato_gargalos.columns:
        return pd.DataFrame()

    local = fato_gargalos.copy()
    required_cols = {'Etapa', 'Tempo Médio (dias)', 'Tempo Mediano (dias)', 'P90 (dias)', 'Qtde Itens', 'Vazão da Etapa (itens)'}
    if not required_cols.issubset(set(local.columns)):
        return pd.DataFrame()

    proj_norm = normalize_text(projeto)
    local = local[local['Projeto'].astype(str).apply(normalize_text) == proj_norm]
    if local.empty:
        return pd.DataFrame()

    for col in ['Tempo Médio (dias)', 'Tempo Mediano (dias)', 'P90 (dias)', 'Qtde Itens', 'Vazão da Etapa (itens)']:
        local[col] = pd.to_numeric(local[col], errors='coerce')
    local = local.dropna(subset=['Etapa', 'Tempo Médio (dias)'])
    local = local[local['Tempo Médio (dias)'] >= 0]
    if local.empty:
        return local

    local['Qtde Itens'] = local['Qtde Itens'].fillna(0).astype(int)
    local['Vazão da Etapa (itens)'] = local['Vazão da Etapa (itens)'].fillna(0).astype(int)
    return local.sort_values('Tempo Médio (dias)', ascending=False, ignore_index=True)


def load_project_bottlenecks_from_csv(projeto):
    """Carrega o CSV de gargalos mais recente do projeto, se existir."""
    if not projeto:
        return pd.DataFrame()
    project_key = str(projeto).strip().upper()
    prefix = PROJECT_BOTTLENECK_PREFIX.get(project_key)
    if not prefix:
        return pd.DataFrame()

    files = []
    url_map = _load_bottleneck_url_map()
    project_csv_url = url_map.get(project_key, '').strip()
    if not project_csv_url:
        global_csv_url = os.getenv('FLOW_PMO_BOTTLENECK_CSV_URL', '').strip()
        if _url_filename_matches_project(global_csv_url, prefix):
            project_csv_url = global_csv_url
    if project_csv_url:
        try:
            files.append(_download_bottleneck_csv_from_url(project_csv_url, project_key))
        except Exception:
            pass

    for folder in DATA_FOLDERS:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            if name.startswith(prefix) and name.endswith('-data_bottlenecks.csv'):
                files.append(os.path.join(folder, name))

    files = [path for path in files if os.path.isfile(path)]
    if not files:
        return pd.DataFrame()

    latest_file = max(files, key=os.path.getctime)
    try:
        bdf = pd.read_csv(latest_file)
    except Exception:
        return pd.DataFrame()

    required_cols = {'Etapa', 'Media Dias', 'Mediana Dias', 'P90 Dias', 'Qtde Issues'}
    if not required_cols.issubset(set(bdf.columns)):
        return pd.DataFrame()

    out = pd.DataFrame({
        'Etapa': bdf['Etapa'].astype(str),
        'Tempo Médio (dias)': pd.to_numeric(bdf['Media Dias'], errors='coerce'),
        'Tempo Mediano (dias)': pd.to_numeric(bdf['Mediana Dias'], errors='coerce'),
        'P90 (dias)': pd.to_numeric(bdf['P90 Dias'], errors='coerce'),
        'Qtde Itens': pd.to_numeric(bdf['Qtde Issues'], errors='coerce'),
        'Vazão da Etapa (itens)': pd.to_numeric(bdf['Qtde Issues'], errors='coerce'),
    }).dropna(subset=['Etapa', 'Tempo Médio (dias)'])

    out = out[out['Tempo Médio (dias)'] >= 0]
    if out.empty:
        return out

    out['Qtde Itens'] = out['Qtde Itens'].fillna(0).astype(int)
    out['Vazão da Etapa (itens)'] = out['Vazão da Etapa (itens)'].fillna(0).astype(int)
    out = out.sort_values('Tempo Médio (dias)', ascending=False, ignore_index=True)
    return out


def load_project_downstream_items_csv(projeto):
    """Carrega o CSV downstream de itens do projeto (com colunas de datas por etapa)."""
    if not projeto:
        return pd.DataFrame()
    project_key = str(projeto).strip().upper()
    prefix = str(PROJECT_BOTTLENECK_PREFIX.get(project_key, '')).strip().lower()
    bitbucket_prefix = str(PROJECT_BITBUCKET_PREFIX.get(project_key, '')).strip().lower()
    if not prefix and not bitbucket_prefix:
        return pd.DataFrame()

    candidate_prefixes = []
    for raw_prefix in (prefix, bitbucket_prefix):
        p = str(raw_prefix or '').strip().lower()
        if not p:
            continue
        if p not in candidate_prefixes:
            candidate_prefixes.append(p)
        if p.endswith('-downstream'):
            short = p[:-11].strip('-_')
            if short and short not in candidate_prefixes:
                candidate_prefixes.append(short)
    preferred_latest_names = {f'{p}-latest-data.csv' for p in candidate_prefixes}

    files = []
    url_map = _load_downstream_url_map()
    project_csv_url = url_map.get(project_key, '').strip()
    if not project_csv_url:
        global_csv_url = os.getenv('FLOW_PMO_DOWNSTREAM_CSV_URL', '').strip()
        matches_any_prefix = any(
            _url_filename_matches_project_suffix(global_csv_url, p, '-data.csv')
            for p in candidate_prefixes
        )
        # Fallback para ambientes single-project com URL global estável sem prefixo padronizado.
        if (matches_any_prefix or (global_csv_url and len(url_map) <= 1)) and not global_csv_url.lower().endswith('-data_bottlenecks.csv'):
            project_csv_url = global_csv_url
    if project_csv_url:
        try:
            files.append(_download_downstream_items_csv_from_url(project_csv_url, project_key))
        except Exception:
            pass

    for folder in DATA_FOLDERS:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low_name = str(name).lower()
            if not (low_name.endswith('-data.csv') and any(low_name.startswith(p) for p in candidate_prefixes)):
                continue
            if low_name.endswith('-data_bottlenecks.csv'):
                continue
            files.append(os.path.join(folder, name))

    files = [path for path in files if os.path.isfile(path)]
    if not files:
        return pd.DataFrame()

    latest_alias_matches = [
        path for path in files
        if os.path.basename(path).lower() in preferred_latest_names
    ]
    if latest_alias_matches:
        latest_file = max(latest_alias_matches, key=os.path.getctime)
    else:
        latest_file = max(files, key=os.path.getctime)
    try:
        return pd.read_csv(latest_file)
    except Exception:
        return pd.DataFrame()


def load_project_downstream_metadata(projeto):
    """Carrega metadados úteis do downstream para filtros e datas quando o modelo principal não traz essas colunas."""
    if not projeto:
        return pd.DataFrame()
    project_key = str(projeto).strip().upper()
    if project_key in DOWNSTREAM_METADATA_CACHE:
        cached = DOWNSTREAM_METADATA_CACHE[project_key]
        return cached.copy() if isinstance(cached, pd.DataFrame) else pd.DataFrame()

    items_df = load_project_downstream_items_csv(project_key)
    if items_df.empty or 'ID' not in items_df.columns:
        DOWNSTREAM_METADATA_CACHE[project_key] = pd.DataFrame()
        return pd.DataFrame()

    meta = pd.DataFrame({
        'Projeto': project_key,
        'ItemID': items_df['ID'].astype(str).str.strip(),
    })

    creator_col = resolve_creator_filter_column(items_df)
    if creator_col and creator_col in items_df.columns:
        meta['Criador'] = items_df[creator_col].fillna('').astype(str).str.strip()
    else:
        meta['Criador'] = ''

    creation_series = resolve_creation_date_series(items_df)
    meta['Created'] = creation_series
    meta = meta.drop_duplicates(subset=['Projeto', 'ItemID'], keep='first')
    DOWNSTREAM_METADATA_CACHE[project_key] = meta
    return meta.copy()


def enrich_items_with_downstream_metadata(df_source, projeto=None):
    if df_source is None or getattr(df_source, 'empty', True) or 'ItemID' not in df_source.columns:
        return df_source

    out = df_source.copy()
    if 'Projeto' in out.columns:
        out['Projeto'] = out['Projeto'].astype(str).str.strip()
    out['ItemID'] = out['ItemID'].astype(str).str.strip()

    project_values = []
    if projeto:
        project_values = [str(projeto).strip()]
    elif 'Projeto' in out.columns:
        project_values = [str(value).strip() for value in out['Projeto'].dropna().astype(str).unique().tolist() if str(value).strip()]

    meta_frames = []
    seen = set()
    for project_name in project_values:
        project_key = str(project_name).strip().upper()
        if not project_key or project_key in seen:
            continue
        seen.add(project_key)
        meta_df = load_project_downstream_metadata(project_key)
        if not meta_df.empty:
            meta_frames.append(meta_df)

    if not meta_frames:
        return out

    meta_all = pd.concat(meta_frames, ignore_index=True)
    merge_keys = ['ItemID']
    if 'Projeto' in out.columns and 'Projeto' in meta_all.columns:
        meta_all['Projeto'] = meta_all['Projeto'].astype(str).str.strip()
        merge_keys = ['Projeto', 'ItemID']
    out = out.merge(meta_all, how='left', on=merge_keys, suffixes=('', '_downstream'))

    creator_col = resolve_creator_filter_column(out)
    downstream_creator_col = 'Criador_downstream' if 'Criador_downstream' in out.columns else ('Criador' if 'Criador' in out.columns else None)
    if downstream_creator_col:
        downstream_creator = out[downstream_creator_col].fillna('').astype(str).str.strip()
        if creator_col and creator_col in out.columns and creator_col != downstream_creator_col:
            current_creator = out[creator_col].fillna('').astype(str).str.strip()
            out[creator_col] = current_creator.where(current_creator.ne(''), downstream_creator)
        else:
            out['Criador'] = downstream_creator

    downstream_created_col = 'Created_downstream' if 'Created_downstream' in out.columns else ('Created' if 'Created' in out.columns else None)
    if downstream_created_col:
        downstream_created = pd.to_datetime(out[downstream_created_col], errors='coerce')
        if 'Created' in out.columns and downstream_created_col != 'Created':
            current_created = pd.to_datetime(out['Created'], errors='coerce')
            out['Created'] = current_created.combine_first(downstream_created)
        else:
            out['Created'] = downstream_created

    out.drop(columns=['Criador_downstream', 'Created_downstream'], inplace=True, errors='ignore')
    return out


def get_downstream_workflow_stage_columns(items_df):
    """Return workflow stage columns from downstream CSV (exclude metadata fields)."""
    if items_df is None or getattr(items_df, 'empty', True):
        return []
    stage_cols = []
    for col in items_df.columns:
        c = str(col).strip()
        if c in DOWNSTREAM_METADATA_COLUMNS:
            continue
        if c in {'ID', 'Link', 'Title'}:
            continue
        stage_cols.append(c)
    return stage_cols


def get_default_lead_time_start_stages(stage_cols):
    """Pick sensible default commitment stages from available workflow columns."""
    if not stage_cols:
        return []
    available_lower = {str(c).strip().lower(): c for c in stage_cols}
    selected = []
    for pref in LEAD_TIME_START_STAGE_PREFERENCES:
        hit = available_lower.get(pref.strip().lower())
        if hit and hit not in selected:
            selected.append(hit)
    if selected:
        return selected

    non_backlog = [
        col for col in stage_cols
        if str(col).strip().lower() not in LEAD_TIME_BACKLOG_LIKE_STAGE_NAMES
    ]
    if non_backlog:
        return [non_backlog[0]]
    return [stage_cols[0]]


def _compute_storytask_orphan_from_downstream():
    """Fallback do indicador de órfãos via downstream (exato quando houver hierarquia)."""
    project_keys = ['W1NNER', 'S1NC', 'BF', 'DT']
    frames = []
    for project_key in project_keys:
        try:
            df_local = load_project_downstream_items_csv(project_key)
        except Exception:
            df_local = pd.DataFrame()
        if df_local is None or df_local.empty or 'Tipo de Problema' not in df_local.columns:
            continue
        frames.append(df_local.copy())

    if not frames:
        return None

    ds = pd.concat(frames, ignore_index=True)
    if ds.empty:
        return None

    def _is_storytask(tipo):
        t = normalize_text(tipo)
        if t in {
            'story', 'user story', 'historia', 'historia de usuario', 'us',
            'task', 'tarefa', 'subtarefa', 'sub task', 'tech task', 'task de produto',
            'ad hoc', 'adhoc', 'ad-hoc'
        }:
            return True
        return ('historia' in t) or ('task' in t) or ('ad hoc' in t) or ('adhoc' in t) or ('ad-hoc' in t)

    tipo_series = ds.get('Tipo de Problema', pd.Series('', index=ds.index)).fillna('').astype(str)
    mask_storytask = tipo_series.apply(_is_storytask)
    total = int(mask_storytask.sum())
    if total <= 0:
        return None

    exact_available = any(c in ds.columns for c in ['ParentTipo', 'FeatureLinkID', 'EpicLinkID'])
    if exact_available:
        parent_tipo = ds.get('ParentTipo', pd.Series('', index=ds.index)).fillna('').astype(str)
        feature_link_id = ds.get('FeatureLinkID', pd.Series('', index=ds.index)).fillna('').astype(str)
        epic_link_id = ds.get('EpicLinkID', pd.Series('', index=ds.index)).fillna('').astype(str)
        has_parent_feature = parent_tipo.map(lambda v: normalize_text(v) in {'feature', 'funcionalidade'})
        has_feature_link = feature_link_id.str.strip().ne('')
        has_epic_link = epic_link_id.str.strip().ne('')
        orphan_mask = mask_storytask & (~(has_parent_feature | has_feature_link | has_epic_link))
        source = 'downstream_exato'
    else:
        epic_name = ds.get('Epic Name', pd.Series('', index=ds.index)).fillna('').astype(str)
        principal = ds.get('Principal', pd.Series('', index=ds.index)).fillna('').astype(str)
        has_link = epic_name.str.strip().ne('') | principal.str.strip().ne('')
        orphan_mask = mask_storytask & (~has_link)
        source = 'downstream_proxy'

    orphan = int(orphan_mask.sum())
    pct = round((orphan / total) * 100, 1) if total else 0.0
    return {'Percentual': pct, 'Numerador': orphan, 'Denominador': total, 'Fonte': source}


def get_explicit_done_stage_column(stage_cols):
    """Detect terminal done/finalization stage column only when explicitly named."""
    available_lower = {str(c).strip().lower(): c for c in stage_cols}
    for cand in LEAD_TIME_END_STAGE_CANDIDATES:
        hit = available_lower.get(cand.strip().lower())
        if hit:
            return hit
    return None


def get_downstream_done_stage_column(stage_cols):
    """Detect terminal done/finalization stage column in downstream CSV."""
    explicit_done = get_explicit_done_stage_column(stage_cols)
    if explicit_done:
        return explicit_done
    return stage_cols[-1] if stage_cols else None


def compute_current_stage_map(projeto):
    """Returns {str(item_id): stage_name} where stage_name is the last stage column
    (in CSV order) with a non-null date for each item in the downstream CSV."""
    items_df = load_project_downstream_items_csv(projeto)
    if items_df is None or items_df.empty or 'ID' not in items_df.columns:
        return {}
    stage_cols = _detect_stage_date_columns(items_df)
    if not stage_cols:
        return {}
    result = {}
    for _, row in items_df.iterrows():
        item_id = str(row['ID']).strip()
        if not item_id:
            continue
        last_stage = None
        for col in stage_cols:
            val = pd.to_datetime(row.get(col), dayfirst=True, errors='coerce')
            if pd.notna(val):
                last_stage = col
        if last_stage is not None:
            result[item_id] = last_stage
    return result


def filter_items_by_current_stage(df_source, projeto=None, selected_stages=None, stage_map=None, keep_done=False):
    """Filter items by current downstream stage.

    When ``keep_done`` is True, concluded items are preserved and only open items
    are constrained by the selected current stages.
    """
    if df_source is None:
        return pd.DataFrame()
    if getattr(df_source, 'empty', True):
        return df_source.copy()
    if not projeto or not selected_stages or 'ItemID' not in df_source.columns:
        return df_source.copy()

    resolved_stage_map = stage_map or compute_current_stage_map(projeto)
    if not resolved_stage_map:
        return df_source.copy()

    selected_lower = {
        str(stage).strip().lower()
        for stage in (selected_stages or [])
        if str(stage).strip()
    }
    if not selected_lower:
        return df_source.copy()

    in_selected_stage = df_source['ItemID'].astype(str).str.strip().map(
        lambda iid: resolved_stage_map.get(iid, '').strip().lower() in selected_lower
    ).fillna(False)

    if keep_done:
        done_mask = pd.to_datetime(df_source.get('DataDone'), errors='coerce').notna()
        return df_source[done_mask | in_selected_stage].copy()

    return df_source[in_selected_stage].copy()


def _find_latest_w1nner_process_mining_excel():
    report_url = os.getenv('FLOW_PMO_PROCESS_MINING_REPORT_URL', '').strip()
    if report_url:
        resolved_url = report_url
        if report_url.startswith('{'):
            try:
                url_map = json.loads(report_url)
                resolved_url = url_map.get('w1nner') or url_map.get('W1NNER') or ''
            except Exception:
                resolved_url = ''
        if resolved_url:
            try:
                return _download_process_mining_report_from_url(resolved_url)
            except Exception:
                pass

    preferred_name = 'w1nner-process-mining-latest.xlsx'
    required_sheets = {'ResumoConformidade', 'ConformidadeCasos', 'EventosFiltrados'}
    candidates = []
    for folder in DATA_FOLDERS:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low = name.lower()
            if not (low.startswith('w1nner-process-mining-') and low.endswith('.xlsx')):
                continue
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                candidates.append(path)
    if not candidates:
        return None
    def _is_valid(path):
        try:
            xls = pd.ExcelFile(path)
        except Exception:
            return False
        return bool(required_sheets.intersection(set(xls.sheet_names)))

    def _sort_key(path):
        name = os.path.basename(path).lower()
        is_preferred = 1 if name == preferred_name else 0
        return (is_preferred, os.path.getctime(path))

    for candidate in sorted(candidates, key=_sort_key, reverse=True):
        if _is_valid(candidate):
            return candidate
    return None


def load_w1nner_process_mining_report():
    """Load latest W1NNER process mining workbook generated by process_mining_jira.py."""
    path = _find_latest_w1nner_process_mining_excel()
    if not path:
        return None, {}
    sheet_names = [
        'ResumoConformidade',
        'ConformidadeCasos',
        'RetrabalhoItens',
        'TemposPorStatus',
        'VazaoPessoaSemanal',
        'VazaoPessoaResumo',
        'HorasPessoaResumo',
        'HorasPessoaStatus',
        'VariantesTop',
        'EventosFiltrados',
        'PM4PyDFGEdges',
        'PM4PyDFGPerfEdges',
        'PM4PyTBRResumo',
        'PM4PyTBRCasos',
        'PM4PyAlignResumo',
        'PM4PyAlignCasos',
        'PM4PyAlignTopMoves',
        'Metadados',
    ]
    loaded = {}
    try:
        xls = pd.ExcelFile(path)
    except Exception:
        return path, {}
    for sheet in sheet_names:
        if sheet not in xls.sheet_names:
            continue
        try:
            loaded[sheet] = pd.read_excel(xls, sheet_name=sheet)
        except Exception:
            loaded[sheet] = pd.DataFrame()
    return path, loaded


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


def _load_pm_excel_url_map() -> dict:
    """Carrega FLOW_PMO_PM_EXCEL_URL_MAP: {"w1nner": "https://...", "s1nc": "https://...", ...}"""
    raw = os.getenv('FLOW_PMO_PM_EXCEL_URL_MAP', '').strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return {str(k).lower().strip(): str(v).strip() for k, v in parsed.items() if v}
    except Exception:
        return {}


def load_project_pm_sheet(projeto: str, sheet_name: str) -> pd.DataFrame:
    """Carrega qualquer aba do Excel de process mining mais recente para qualquer projeto.
    Retorna DataFrame vazio se não encontrado.
    Suporta carregamento remoto via FLOW_PMO_PM_EXCEL_URL_MAP ou FLOW_PMO_PROCESS_MINING_REPORT_URL.
    """
    project_key = str(projeto or '').strip().upper()
    prefix = _PM_FILE_PREFIX_MAP.get(project_key, project_key.lower().replace(' ', '').replace('&', ''))

    # 1) Tenta URL do mapa por projeto
    url_map = _load_pm_excel_url_map()
    url = url_map.get(prefix, '')
    # 2) Fallback: FLOW_PMO_PROCESS_MINING_REPORT_URL para w1nner (retrocompatível)
    if not url and prefix == 'w1nner':
        url = os.getenv('FLOW_PMO_PROCESS_MINING_REPORT_URL', '').strip()
    if url:
        try:
            path = _download_process_mining_report_from_url(url)
            xls = pd.ExcelFile(path)
            if sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                if not df.empty:
                    return df
        except Exception:
            pass

    # 3) Busca local em DATA_FOLDERS
    latest_name = f'{prefix}-process-mining-latest.xlsx'
    candidates = []
    for folder in _iter_local_data_folders(include_process_mining_artifacts=True):
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low = name.lower()
            if low.startswith(f'{prefix}-process-mining-') and low.endswith('.xlsx'):
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    is_latest = 1 if name.lower() == latest_name else 0
                    candidates.append((is_latest, os.path.getctime(path), path))
    if not candidates:
        return pd.DataFrame()
    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
    for _, _, path in candidates:
        try:
            xls = pd.ExcelFile(path)
            if sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                if not df.empty:
                    return df
        except Exception:
            continue

    csv_slug = _PM_SHEET_CSV_SLUG_MAP.get(str(sheet_name).strip())
    if not csv_slug:
        return pd.DataFrame()

    csv_candidates = []
    latest_csv_name = f'{prefix}-process-mining-latest-{csv_slug}.csv'
    for folder in _iter_local_data_folders(include_process_mining_artifacts=True):
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low = name.lower()
            if not (low.startswith(f'{prefix}-process-mining-') and low.endswith(f'-{csv_slug}.csv')):
                continue
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                is_latest = 1 if low == latest_csv_name else 0
                csv_candidates.append((is_latest, os.path.getctime(path), path))
    if not csv_candidates:
        return pd.DataFrame()
    csv_candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
    for _, _, path in csv_candidates:
        try:
            df = pd.read_csv(path)
            if not df.empty:
                return df
        except Exception:
            continue
    return pd.DataFrame()


def load_project_pm_case_df(projeto: str) -> pd.DataFrame:
    """Carrega a aba ConformidadeCasos do Excel de process mining mais recente para qualquer projeto."""
    return load_project_pm_sheet(projeto, 'ConformidadeCasos')


def _load_portfolio_cost_model() -> dict:
    model = parse_json_env('FLOW_PMO_PORTFOLIO_COST_MODEL', {})
    if not isinstance(model, dict):
        model = {}
    return {
        'fl_mensal': float(model.get('fl_mensal', 0) or 0),
        'budget_ti_pct': float(model.get('budget_ti_pct', 0.10) or 0.10),
        'fator_encargos': float(model.get('fator_encargos', 2.0) or 2.0),
        'custo_ferramentas_infra_mensal': float(model.get('custo_ferramentas_infra_mensal', 0) or 0),
        'dias_uteis_mes': float(model.get('dias_uteis_mes', 22) or 22),
        'horas_dia': float(model.get('horas_dia', 8) or 8),
        'fator_produtividade': float(model.get('fator_produtividade', 0.75) or 0.75),
        'salario_medio_bruto': float(model.get('salario_medio_bruto', 0) or 0),
    }


def _load_portfolio_role_salary_map() -> dict:
    raw_map = parse_json_env('FLOW_PMO_PORTFOLIO_ROLE_SALARY_MAP', {})
    if not isinstance(raw_map, dict):
        return {}
    out = {}
    for raw_key, raw_value in raw_map.items():
        key = str(raw_key or '').strip()
        if not key:
            continue
        try:
            out[key] = float(raw_value)
        except Exception:
            continue
    return out


def _load_portfolio_bu_salary_map() -> dict:
    raw_map = parse_json_env('FLOW_PMO_PORTFOLIO_BU_SALARY_MAP', {})
    if not isinstance(raw_map, dict):
        return {}
    out = {}
    for raw_key, raw_value in raw_map.items():
        key = str(raw_key or '').strip()
        if not key:
            continue
        try:
            out[key] = float(raw_value)
        except Exception:
            continue
    return out


def _build_portfolio_cost_team_df() -> pd.DataFrame:
    config = _load_people_config()
    bu_map = config.get('bu_map', {}) if isinstance(config, dict) else {}
    alias_index = _load_person_alias_index()
    role_index = _load_person_role_map()
    rows = []
    seen = set()
    for raw_name, raw_bu in bu_map.items():
        person = _canonical_person_name(raw_name, alias_index=alias_index)
        if not person or person in seen:
            continue
        seen.add(person)
        rows.append({
            'Pessoa': person,
            'BU': str(raw_bu or '').strip(),
            'Papel': _person_role(person, role_index=role_index),
        })
    if not rows:
        return pd.DataFrame(columns=['Pessoa', 'BU', 'Papel'])
    return pd.DataFrame(rows).sort_values(['BU', 'Pessoa'], ignore_index=True)


def _product_bu_for_cost(project_key: str) -> str:
    mapping = {
        'BF': 'BeFinance',
        'DT': 'Dados',
        'S1NC': 'Sistemas - S1NC',
        'W1NNER': 'Sistemas - W1NNER',
    }
    return mapping.get(_canonical_pm_product_key(project_key), '')


def build_portfolio_cost_model_snapshot(portfolio_scope_df: pd.DataFrame, start_ts, end_ts) -> dict:
    model = _load_portfolio_cost_model()
    role_salary_map = _load_portfolio_role_salary_map()
    bu_salary_map = _load_portfolio_bu_salary_map()
    team_df = _build_portfolio_cost_team_df()

    if team_df.empty:
        return {
            'available': False,
            'error': 'people_config.json sem pessoas suficientes para calcular o custo heurístico.',
        }

    team_cost_df = team_df.copy()
    team_cost_df['Salário Base (R$)'] = team_cost_df.apply(
        lambda row: float(
            bu_salary_map.get(str(row.get('BU', '')).strip())
            or role_salary_map.get(str(row.get('Papel', '')).strip())
            or model.get('salario_medio_bruto', 0)
            or 0
        ),
        axis=1,
    )
    team_cost_df['Custo Mensal Pessoa (R$)'] = team_cost_df['Salário Base (R$)'] * float(model.get('fator_encargos', 2.0) or 2.0)

    dias_uteis = max(1.0, float(model.get('dias_uteis_mes', 22) or 22))
    horas_dia = max(1.0, float(model.get('horas_dia', 8) or 8))
    fator_produtividade = max(0.01, float(model.get('fator_produtividade', 0.75) or 0.75))

    team_cost_df['Horas Produtivas Mensais'] = dias_uteis * horas_dia * fator_produtividade
    team_cost_df['Custo Hora Pessoa (R$)'] = np.where(
        pd.to_numeric(team_cost_df['Horas Produtivas Mensais'], errors='coerce').fillna(0) > 0,
        pd.to_numeric(team_cost_df['Custo Mensal Pessoa (R$)'], errors='coerce').fillna(0)
        / pd.to_numeric(team_cost_df['Horas Produtivas Mensais'], errors='coerce').fillna(1),
        0.0,
    )

    custo_equipe_mensal = float(pd.to_numeric(team_cost_df['Custo Mensal Pessoa (R$)'], errors='coerce').fillna(0).sum())
    custo_total_ti_mensal = custo_equipe_mensal + float(model.get('custo_ferramentas_infra_mensal', 0) or 0)
    capacidade_total_mensal = float(pd.to_numeric(team_cost_df['Horas Produtivas Mensais'], errors='coerce').fillna(0).sum())
    custo_hora_global = (custo_total_ti_mensal / capacidade_total_mensal) if capacidade_total_mensal > 0 else 0.0
    budget_ti_mensal = float(model.get('fl_mensal', 0) or 0) * float(model.get('budget_ti_pct', 0.10) or 0.10)
    budget_ti_anual = budget_ti_mensal * 12.0

    product_rate_rows = []
    explicit_rate_overrides = parse_json_env('FLOW_PMO_PM_COST_PER_HOUR_MAP', {})
    explicit_rate_overrides = explicit_rate_overrides if isinstance(explicit_rate_overrides, dict) else {}
    for spec in _PM_PORTFOLIO_PRODUCT_SPECS:
        project_key = spec['project_key']
        bu_name = _product_bu_for_cost(project_key)
        team_slice = team_cost_df[team_cost_df['BU'].astype(str).str.strip() == bu_name].copy()
        custo_mensal_produto = float(pd.to_numeric(team_slice['Custo Mensal Pessoa (R$)'], errors='coerce').fillna(0).sum())
        capacidade_produto = float(pd.to_numeric(team_slice['Horas Produtivas Mensais'], errors='coerce').fillna(0).sum())
        rate = (custo_mensal_produto / capacidade_produto) if capacidade_produto > 0 else custo_hora_global
        explicit = explicit_rate_overrides.get(project_key)
        if explicit is None:
            explicit = explicit_rate_overrides.get(spec['product'])
        try:
            rate = float(explicit) if explicit is not None else float(rate)
        except Exception:
            rate = float(rate or 0)
        product_rate_rows.append({
            'Projeto PM': project_key,
            'Produto': spec['product'],
            'BU': bu_name,
            'Headcount': int(team_slice['Pessoa'].nunique()),
            'Custo Mensal Produto (R$)': custo_mensal_produto,
            'Capacidade Mensal Produto (h)': capacidade_produto,
            'Custo Hora Produto (R$)': rate,
        })

    portfolio_assets = pd.DataFrame()
    if portfolio_scope_df is not None and not portfolio_scope_df.empty:
        assets = portfolio_scope_df.copy()
        type_col = _pm_pick_first_column(assets, ['Tipo', 'ItemType'])
        id_col = _pm_pick_first_column(assets, ['ID', 'ItemID'])
        title_col = _pm_pick_first_column(assets, ['Titulo', 'Title'])
        status_col = _pm_pick_first_column(assets, ['Status'])
        if type_col and id_col and title_col:
            assets['_tipo_norm'] = assets[type_col].apply(normalize_text)
            assets = assets[assets['_tipo_norm'].isin({'epic', 'epico', 'feature', 'funcionalidade'})].copy()
            portfolio_assets = pd.DataFrame({
                'AssetID': assets[id_col].astype(str).str.strip(),
                'Descrição do Ativo': assets[title_col].fillna('').astype(str).str.strip(),
                'Status': assets[status_col].fillna('').astype(str).str.strip() if status_col else '',
            }).drop_duplicates(subset=['AssetID'], keep='first')

    return {
        'available': True,
        'model': model,
        'team_df': team_cost_df,
        'person_rates_df': team_cost_df[['Pessoa', 'BU', 'Papel', 'Custo Hora Pessoa (R$)']].copy(),
        'product_rates_df': pd.DataFrame(product_rate_rows),
        'kpis': {
            'Budget TI Mensal': budget_ti_mensal,
            'Budget TI Anual': budget_ti_anual,
            'Custo Equipe Mensal': custo_equipe_mensal,
            'Custo Total TI Mensal': custo_total_ti_mensal,
            'Capacidade Total Mensal (h)': capacidade_total_mensal,
            'Custo Hora Carregado': custo_hora_global,
            'Headcount TI': int(team_cost_df['Pessoa'].nunique()),
        },
        'portfolio_assets_df': portfolio_assets,
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


def _pm_pick_first_column(df_source: pd.DataFrame, candidates) -> str | None:
    if df_source is None or getattr(df_source, 'empty', True):
        return None
    for candidate in candidates:
        if candidate in df_source.columns:
            return candidate
    return None


def _canonical_pm_product_key(value) -> str:
    norm = normalize_text(value).upper()
    if not norm:
        return ''
    return _PM_PORTFOLIO_CANONICAL_PROJECT_MAP.get(norm, '')


def _pm_product_label(project_key: str) -> str:
    canonical_key = _canonical_pm_product_key(project_key)
    for spec in _PM_PORTFOLIO_PRODUCT_SPECS:
        if spec['project_key'] == canonical_key:
            return spec['product']
    return canonical_key or str(project_key or '').strip()


def _pm_product_color(project_key: str) -> str:
    canonical_key = _canonical_pm_product_key(project_key)
    for spec in _PM_PORTFOLIO_PRODUCT_SPECS:
        if spec['project_key'] == canonical_key:
            return spec['color']
    return '#455a64'


def _pm_portfolio_selected_specs(project_value=None):
    selected = _canonical_pm_product_key(project_value)
    specs = []
    for spec in _PM_PORTFOLIO_PRODUCT_SPECS:
        if selected and spec['project_key'] != selected:
            continue
        specs.append(dict(spec))
    return specs


def _pm_load_cost_rate_map() -> dict:
    out = {}
    cost_model_snapshot = build_portfolio_cost_model_snapshot(pd.DataFrame(), pd.Timestamp(datetime.now().date()), pd.Timestamp(datetime.now().date()))
    product_rates_df = cost_model_snapshot.get('product_rates_df', pd.DataFrame()) if isinstance(cost_model_snapshot, dict) else pd.DataFrame()
    if product_rates_df is not None and not product_rates_df.empty:
        for row in product_rates_df.to_dict(orient='records'):
            canonical_key = _canonical_pm_product_key(row.get('Projeto PM'))
            if not canonical_key:
                continue
            try:
                rate = float(row.get('Custo Hora Produto (R$)', 0) or 0)
            except Exception:
                continue
            if rate >= 0:
                out[canonical_key] = rate
    return out


def _pm_status_phase_category(status_norm: str) -> str:
    """Classifica o status normalizado em 4 categorias de fase.

    Retorna:
      'ativo'              → status de execução ativa (Development, Code Review, etc.)
      'espera_upstream'    → fila antes da execução (Backlog, To Do, Discovery…)
      'espera_downstream'  → fila após execução ou Done (Ready for*, Done, Closed…)
      'nao_contabilizado'  → demais (transições administrativas, cancelamentos)
    """
    norm = normalize_text(status_norm) if status_norm else ''
    if not norm:
        return 'nao_contabilizado'
    # Ativo → tokens de execução (reutiliza lógica existente)
    if _pm_is_execution_status(norm):
        return 'ativo'
    # Espera upstream → antes da execução
    _upstream_tokens = ('backlog', 'triagem', 'triage', 'discovery', 'planning',
                        'refinement', 'refinamento', 'grooming', 'to do', 'todo', 'open')
    if any(t in norm for t in _upstream_tokens):
        return 'espera_upstream'
    # Espera downstream → ready* ou finalizado
    if norm.startswith('ready ') or norm == 'ready':
        return 'espera_downstream'
    _downstream_tokens = ('done', 'conclu', 'closed', 'cancel', 'deployed', 'released',
                          'entregue', 'publicado')
    if any(t in norm for t in _downstream_tokens):
        return 'espera_downstream'
    return 'nao_contabilizado'


def _pm_load_capacity_map() -> dict:
    """Retorna {project_key: capacidade_mensal_horas} para cada produto do portfólio.

    Reutiliza build_portfolio_cost_model_snapshot que já é chamado em _pm_load_cost_rate_map.
    """
    out = {}
    try:
        snapshot = build_portfolio_cost_model_snapshot(
            pd.DataFrame(),
            pd.Timestamp(datetime.now().date()),
            pd.Timestamp(datetime.now().date()),
        )
        rates_df = snapshot.get('product_rates_df', pd.DataFrame()) if isinstance(snapshot, dict) else pd.DataFrame()
        if rates_df is not None and not rates_df.empty:
            for row in rates_df.to_dict(orient='records'):
                key = _canonical_pm_product_key(row.get('Projeto PM'))
                if not key:
                    continue
                try:
                    cap = float(row.get('Capacidade Mensal Produto (h)', 0) or 0)
                    if cap > 0:
                        out[key] = cap
                except Exception:
                    pass
    except Exception:
        pass
    return out


def _pm_derive_sync_calibration(
    events_exec_df: 'pd.DataFrame',
    sp_lookup: dict,
    horas_prod_por_dia_cal: float = 4.336,
) -> dict:
    """Deriva a taxa horas_produtivas/SP calibrada usando o Sync (S1NC) como âncora.

    O Sync tem 92,87% de horas mapeadas — é o único produto com dados suficientes
    para calibrar a taxa de conversão complexidade → horas sem apontamento manual.

    Usa horas produtivas (não horas de calendário) para que M3 fique na mesma
    unidade que M1 e M2 — imprescindível para triangulação sem viés de escala.

    Args:
        events_exec_df: DataFrame de eventos de execução (Horas PM Elegíveis > 0).
                        Deve conter: 'Projeto PM', 'Issue Key', 'TempoStatusDias'.
        sp_lookup: dict {issue_key: sp_float} com SP real > 0 por issue.
        horas_prod_por_dia_cal: conversão horas produtivas / dia calendário (default ≈ 4.34).

    Returns:
        dict com:
          'horas_por_sp': float  — taxa calibrada (horas produtivas por SP no Sync)
          'n_itens': int         — número de itens usados
          'valida': bool         — True se n_itens ≥ 5
    """
    _SYNC_KEY = 'S1NC'
    _MIN_ITENS = 5

    if events_exec_df is None or events_exec_df.empty or not sp_lookup:
        return {'horas_por_sp': None, 'n_itens': 0, 'valida': False}

    sync_ev = events_exec_df[
        events_exec_df.get('Projeto PM', pd.Series(dtype=str)).astype(str) == _SYNC_KEY
    ].copy() if 'Projeto PM' in events_exec_df.columns else pd.DataFrame()

    if sync_ev.empty:
        return {'horas_por_sp': None, 'n_itens': 0, 'valida': False}

    # Horas produtivas por issue: TempoStatusDias × fator produtivo
    sync_hours = (
        sync_ev.groupby('Issue Key')['TempoStatusDias']
        .sum()
        .reset_index()
        .rename(columns={'TempoStatusDias': '_dias_exec'})
    )
    sync_hours['_horas_prod'] = sync_hours['_dias_exec'] * horas_prod_por_dia_cal
    sync_hours['_sp'] = sync_hours['Issue Key'].map(sp_lookup)
    sync_hours = sync_hours[sync_hours['_horas_prod'] > 0].dropna(subset=['_sp'])
    sync_hours = sync_hours[sync_hours['_sp'] > 0]

    n = len(sync_hours)
    if n < _MIN_ITENS:
        return {'horas_por_sp': None, 'n_itens': n, 'valida': False}

    # Taxa = horas produtivas totais / SP totais (razão agregada)
    total_horas = float(sync_hours['_horas_prod'].sum())
    total_sp = float(sync_hours['_sp'].sum())
    rate = total_horas / total_sp if total_sp > 0 else None
    return {'horas_por_sp': rate, 'n_itens': n, 'valida': True}


def build_touch_time_triangulation(
    all_phases_df: 'pd.DataFrame',
    portfolio_scope_df: 'pd.DataFrame',
    period_months: float = 1.0,
) -> 'pd.DataFrame':
    """Triangula estimativas de horas trabalhadas (touch time) por issue usando até 3 modelos.

    Modelo 1 — PM Puro (horas produtivas):
        Σ dias_em_status_ativo × horas_produtivas_por_dia_calendário
        horas_produtivas_por_dia = (horas_produtivas_mensais / dias_calendário_mes)
                                 = (22 × 8 × 0.75) / 30.44 ≈ 4.34 h/dia
        Converte TempoStatusDias de dias de calendário para horas efetivamente trabalhadas,
        usando os mesmos parâmetros do modelo de custo (evita incompatibilidade de unidades
        com M2 que usa horas produtivas como denominador).

    Modelo 2 — Alocação por Capacidade:
        (CycleTime_item / Σ CycleTimes_produto_no_período) × Capacidade_Mensal_Produto_h × period_months
        Âncora: capacidade declarada do time (horas produtivas/mês por produto).

    Modelo 3 — Complexidade × Taxa Calibrada (somente quando SP disponível):
        peso_complexidade × horas_por_SP_calibradas_no_Sync
        Retorna NaN quando SP/T-shirt não encontrado para o item — não produz default.
        O Sync (92,87% mapeado) fornece a taxa âncora via _pm_derive_sync_calibration.

    Confiança por item:
        Alta  → M1 > 0 e item mapeado ao portfólio (Fonte Vínculo ≠ NaoMapeado)
        Média → M1 > 0 mas não mapeado, ou apenas M2 disponível
        Baixa → apenas M3 ou nenhum modelo disponível

    Convergência entre os modelos disponíveis (≥ 2 com valor > 0):
        |(max − min) / média| ≤ 0.30 (30%) — limiar defensável para estimativas sem apontamento.

    Args:
        all_phases_df: todos os eventos PM do período (incluindo fases não-execução).
                       Deve conter: Issue Key, Produto, Projeto PM, Horas PM Elegíveis,
                       TempoStatusDias, Fonte Vínculo (opcional).
        portfolio_scope_df: dados do portfólio com StoryPoints e TShirtSize por issue.
                            Usado apenas para M3 — quando ausente, M3 é NaN.
        period_months: duração do período em meses (padrão 1.0).

    Returns:
        DataFrame por Issue Key com colunas de triangulação.
    """
    _CONVERGENCE_THRESHOLD = 0.30  # 30% — defensável sem apontamento manual
    _DIAS_CALENDARIO_MES = 30.4375
    _empty_cols = [
        'Issue Key', 'Produto', 'Projeto PM',
        'HorasM1', 'HorasM2', 'HorasM3',
        'HorasEstimadas', 'ConfiancaEstimativa',
        'ConvergenciaModelos', 'BandaIncerteza_pct',
    ]

    if all_phases_df is None or all_phases_df.empty:
        return pd.DataFrame(columns=_empty_cols)

    ev = all_phases_df.copy()
    for col in ['Issue Key', 'Produto', 'Projeto PM']:
        if col not in ev.columns:
            ev[col] = ''
    if 'Horas PM Elegíveis' not in ev.columns:
        ev['Horas PM Elegíveis'] = 0.0
    if 'TempoStatusDias' not in ev.columns:
        ev['TempoStatusDias'] = 0.0
    if 'Fonte Vínculo' not in ev.columns:
        ev['Fonte Vínculo'] = 'NaoMapeado'

    ev['Issue Key'] = ev['Issue Key'].astype(str).str.strip()
    ev = ev[ev['Issue Key'].ne('')].copy()
    ev['Horas PM Elegíveis'] = pd.to_numeric(ev['Horas PM Elegíveis'], errors='coerce').fillna(0.0)
    ev['TempoStatusDias'] = pd.to_numeric(ev['TempoStatusDias'], errors='coerce').fillna(0.0)

    # ── Fator de conversão: dias calendário → horas produtivas ───────────────
    # Usa os mesmos parâmetros do modelo de custo para consistência com M2.
    # horas_prod_dia = horas_prod_mensais / dias_calendario_mes
    try:
        _model_params = _load_portfolio_cost_model()
        _dias_uteis = max(1.0, float(_model_params.get('dias_uteis_mes', 22) or 22))
        _horas_dia = max(1.0, float(_model_params.get('horas_dia', 8) or 8))
        _fator_prod = max(0.01, float(_model_params.get('fator_produtividade', 0.75) or 0.75))
    except Exception:
        _dias_uteis, _horas_dia, _fator_prod = 22.0, 8.0, 0.75
    _horas_prod_mensais = _dias_uteis * _horas_dia * _fator_prod  # ex: 132h
    _horas_prod_por_dia_cal = _horas_prod_mensais / _DIAS_CALENDARIO_MES  # ex: 4.34 h/dia

    # ── Modelo 1: PM puro em horas produtivas ─────────────────────────────────
    # Soma apenas as fases ativas (Horas PM Elegíveis > 0) e converte de horas de
    # calendário (TempoStatusDias × 24) para horas produtivas (× horas_prod_por_dia_cal).
    # HorasM1 = Σ TempoStatusDias_ativo × horas_prod_por_dia_cal
    ev_exec = ev[ev['Horas PM Elegíveis'] > 0].copy()
    m1 = (
        ev_exec.groupby('Issue Key', dropna=False)
        .agg(
            Produto=('Produto', 'first'),
            _projeto=('Projeto PM', 'first'),
            _dias_exec=('TempoStatusDias', 'sum'),
            _mapped=('Fonte Vínculo', lambda x: any(str(v) != 'NaoMapeado' for v in x)),
        )
        .reset_index()
    )
    m1['HorasM1'] = m1['_dias_exec'] * _horas_prod_por_dia_cal

    # ── Modelo 2: Alocação por capacidade ────────────────────────────────────
    capacity_map = _pm_load_capacity_map()
    # CycleTime por issue = soma de TODOS os dias em qualquer fase
    cycle_per_issue = (
        ev.groupby(['Issue Key', 'Projeto PM'], dropna=False)['TempoStatusDias']
        .sum()
        .reset_index()
        .rename(columns={'TempoStatusDias': '_cycle_dias'})
    )
    cycle_per_product = (
        cycle_per_issue.groupby('Projeto PM')['_cycle_dias']
        .sum()
        .reset_index()
        .rename(columns={'_cycle_dias': '_total_cycle_produto'})
    )
    cycle_per_issue = cycle_per_issue.merge(cycle_per_product, on='Projeto PM', how='left')
    cycle_per_issue['_cap_produto'] = cycle_per_issue['Projeto PM'].map(capacity_map).fillna(0.0)
    cycle_per_issue['HorasM2'] = np.where(
        (cycle_per_issue['_total_cycle_produto'] > 0) & (cycle_per_issue['_cap_produto'] > 0),
        (cycle_per_issue['_cycle_dias'] / cycle_per_issue['_total_cycle_produto'])
        * cycle_per_issue['_cap_produto'] * period_months,
        np.nan,
    )

    # ── Modelo 3: Complexidade × taxa calibrada (somente com SP real) ─────────
    # NaN quando SP não disponível — nunca usa peso default para não poluir a triangulação.
    sp_lookup: dict = {}
    tshirt_lookup: dict = {}
    if portfolio_scope_df is not None and not portfolio_scope_df.empty:
        scope = portfolio_scope_df.copy()
        key_col = next((c for c in ['Issue Key', 'IssueKey', 'Key'] if c in scope.columns), None)
        sp_col = next((c for c in ['StoryPoints', 'story_points', 'SP'] if c in scope.columns), None)
        tshirt_col = next((c for c in ['TShirtSize', 'tshirt', 'T-shirt', 'TShirt'] if c in scope.columns), None)
        if key_col and sp_col:
            sp_lookup = {
                str(k).strip(): float(v)
                for k, v in zip(scope[key_col], pd.to_numeric(scope[sp_col], errors='coerce'))
                if not (isinstance(v, float) and np.isnan(v)) and float(v) > 0
            }
        if key_col and tshirt_col:
            tshirt_lookup = dict(zip(
                scope[key_col].astype(str).str.strip(),
                scope[tshirt_col].astype(str),
            ))

    # Calibração a partir de dados reais (Sync como âncora): usa horas produtivas (M1)
    calibration = _pm_derive_sync_calibration(ev_exec, sp_lookup, horas_prod_por_dia_cal=_horas_prod_por_dia_cal)
    horas_por_sp = calibration['horas_por_sp'] if calibration['valida'] else None

    def _m3_horas(issue_key: str):
        if horas_por_sp is None:
            return np.nan
        sp = sp_lookup.get(issue_key)
        tshirt = tshirt_lookup.get(issue_key)
        # Só computa M3 quando há SP ou T-shirt real — nunca usa weight default 0.5
        if sp and sp > 0:
            w = _sp_weight(sp)
        elif tshirt and tshirt not in ('', 'None', 'nan'):
            w = _tshirt_to_weight(tshirt)
            if w is None:
                return np.nan
        else:
            return np.nan  # sem estimativa → M3 não disponível para este item
        return w * horas_por_sp

    # ── Combina os 3 modelos ─────────────────────────────────────────────────
    result = m1[['Issue Key', 'Produto', '_projeto', 'HorasM1', '_mapped']].copy().rename(columns={'_projeto': 'Projeto PM'})
    result = result.merge(
        cycle_per_issue[['Issue Key', 'HorasM2']].drop_duplicates('Issue Key'),
        on='Issue Key', how='left',
    )
    result['HorasM3'] = result['Issue Key'].apply(_m3_horas)

    # Confiança — baseada em evidência PM direta, não na presença de M3
    def _confidence(row) -> str:
        if row['HorasM1'] > 0 and row.get('_mapped', False):
            return 'Alta'
        if row['HorasM1'] > 0 or (not pd.isna(row.get('HorasM2')) and row.get('HorasM2', 0) > 0):
            return 'Média'
        return 'Baixa'

    result['ConfiancaEstimativa'] = result.apply(_confidence, axis=1)

    # Média e convergência — considera apenas modelos com valor real (não NaN)
    def _triangulate(row) -> tuple:
        m3_val = row.get('HorasM3')
        vals = [
            v for v in [row['HorasM1'], row.get('HorasM2'), m3_val]
            if v is not None and not (isinstance(v, float) and np.isnan(v)) and v >= 0
        ]
        if len(vals) < 2:
            # Com um único modelo, não há triangulação
            return (float(vals[0]) if vals else np.nan), False, np.nan
        mean_v = float(np.mean(vals))
        if mean_v == 0:
            return 0.0, True, 0.0
        spread = (max(vals) - min(vals)) / mean_v
        return mean_v, spread <= _CONVERGENCE_THRESHOLD, round(spread * 100, 1)

    tris = result.apply(_triangulate, axis=1, result_type='expand')
    result['HorasEstimadas'] = tris[0]
    result['ConvergenciaModelos'] = tris[1]
    result['BandaIncerteza_pct'] = tris[2]

    return result[_empty_cols].copy()


def build_capex_worklog_cost_fact(start_ts, end_ts, portfolio_scope_df, project_value=None, responsavel=None) -> dict:
    empty_df = pd.DataFrame(columns=[
        'MesCompetencia', 'Projeto PM', 'Produto', 'Issue Key', 'AssetID', 'Descrição do Ativo',
        'Tipo do Ativo', 'Colaborador', 'Colaborador Canonico', 'Data do Apontamento das Horas',
        'Horas', 'Atividade Desenvolvida', 'ConfidenceScore', 'Origem Horas', 'RateSource',
        'Custo Hora Aplicado (R$)', 'Custo Real Apontado (R$)', 'AtivoMapeado',
    ])
    snapshot, raw_df, _summary_df, error = get_capex_snapshot()
    if error:
        return {'available': False, 'error': error, 'df': empty_df, 'product_summary': pd.DataFrame(), 'asset_summary': pd.DataFrame(), 'overall': {}}
    if raw_df is None or raw_df.empty:
        return {'available': False, 'error': 'Artefato CAPEX raw não encontrado.', 'df': empty_df, 'product_summary': pd.DataFrame(), 'asset_summary': pd.DataFrame(), 'overall': {}}

    df = raw_df.copy()
    df['Data do Apontamento das Horas'] = pd.to_datetime(df.get('Data do Apontamento das Horas'), errors='coerce')
    df['Horas'] = pd.to_numeric(df.get('Horas'), errors='coerce').fillna(0.0)
    df['Issue Key'] = df.get('Issue Key', '').apply(_pm_clean_issue_key)
    df['Projeto PM'] = df.get('Projeto Jira', '').apply(_canonical_pm_product_key)
    missing_project_mask = df['Projeto PM'].astype(str).str.strip().eq('')
    if missing_project_mask.any():
        df.loc[missing_project_mask, 'Projeto PM'] = df.loc[missing_project_mask, 'Issue Key'].apply(_infer_project_key_from_issue)
    df['Produto'] = df['Projeto PM'].apply(_pm_product_label)
    df['AssetID'] = df.get('ID do Projeto', '').apply(_pm_clean_issue_key)
    df['Descrição do Ativo'] = df.get('Descrição do Ativo', '').fillna('').astype(str).str.strip()
    df['Tipo do Ativo'] = df.get('Tipo do Ativo', '').fillna('').astype(str).str.strip()
    df['ConfidenceScore'] = pd.to_numeric(df.get('ConfidenceScore'), errors='coerce')
    df['Origem Horas'] = df.get('Origem Horas', '').fillna('').astype(str).str.strip()

    alias_index = _load_person_alias_index()
    df['Colaborador'] = df.get('Colaborador', '').fillna('').astype(str).str.strip()
    df['Colaborador Canonico'] = df['Colaborador'].apply(lambda value: _canonical_person_name(value, alias_index=alias_index))

    start_bound = pd.to_datetime(start_ts)
    end_bound = pd.to_datetime(end_ts) + pd.Timedelta(days=1)
    df = df[
        df['Data do Apontamento das Horas'].notna()
        & (df['Data do Apontamento das Horas'] >= start_bound)
        & (df['Data do Apontamento das Horas'] < end_bound)
        & (df['Horas'] > 0)
    ].copy()

    if project_value:
        selected_project = _canonical_pm_product_key(project_value)
        if selected_project:
            df = df[df['Projeto PM'] == selected_project].copy()

    selected_people = set(_normalize_responsavel_filter_values(responsavel, alias_index=alias_index, canonicalize=True))
    if selected_people:
        df = df[df['Colaborador Canonico'].isin(selected_people)].copy()

    if df.empty:
        return {
            'available': False,
            'error': 'Sem worklogs CAPEX no período/filtros atuais.',
            'df': empty_df,
            'product_summary': pd.DataFrame(),
            'asset_summary': pd.DataFrame(),
            'overall': {'worklogs': 0, 'hours': 0.0, 'cost': 0.0, 'mapped_cost': 0.0, 'mapped_pct_cost': np.nan},
            'snapshot': snapshot or {},
        }

    portfolio_lookup = _pm_build_portfolio_lookup(portfolio_scope_df)
    asset_frames = []
    for project_key in sorted(set(df['Projeto PM'].dropna().astype(str).str.strip())):
        if not project_key:
            continue
        asset_map = _pm_build_downstream_asset_map(project_key, portfolio_lookup)
        if asset_map.empty:
            continue
        asset_map = asset_map.rename(columns={
            'AssetID': 'AssetID Fallback',
            'Descrição do Ativo': 'Descrição do Ativo Fallback',
            'Tipo do Ativo': 'Tipo do Ativo Fallback',
        })
        asset_map['Projeto PM'] = project_key
        asset_frames.append(asset_map[['Projeto PM', 'Issue Key', 'AssetID Fallback', 'Descrição do Ativo Fallback', 'Tipo do Ativo Fallback']])

    if asset_frames:
        asset_lookup_df = pd.concat(asset_frames, ignore_index=True)
        df = df.merge(asset_lookup_df, how='left', on=['Projeto PM', 'Issue Key'])
        raw_asset_id = df['AssetID'].fillna('').astype(str).str.strip()
        raw_asset_desc = df['Descrição do Ativo'].fillna('').astype(str).str.strip()
        raw_asset_type = df['Tipo do Ativo'].fillna('').astype(str).str.strip()
        fallback_asset_id = df['AssetID Fallback'].fillna('').astype(str).str.strip()
        fallback_asset_desc = df['Descrição do Ativo Fallback'].fillna('').astype(str).str.strip()
        fallback_asset_type = df['Tipo do Ativo Fallback'].fillna('').astype(str).str.strip()
        df['AssetID'] = np.where(raw_asset_id.ne(''), raw_asset_id, fallback_asset_id)
        df['Descrição do Ativo'] = np.where(raw_asset_desc.ne(''), raw_asset_desc, fallback_asset_desc)
        df['Tipo do Ativo'] = np.where(raw_asset_type.ne(''), raw_asset_type, fallback_asset_type)
        df = df.drop(columns=['AssetID Fallback', 'Descrição do Ativo Fallback', 'Tipo do Ativo Fallback'], errors='ignore')

    df['AtivoMapeado'] = df['AssetID'].astype(str).str.strip().ne('')

    cost_snapshot = build_portfolio_cost_model_snapshot(portfolio_scope_df if portfolio_scope_df is not None else pd.DataFrame(), start_ts, end_ts)
    team_df = cost_snapshot.get('team_df', pd.DataFrame()).copy() if isinstance(cost_snapshot, dict) else pd.DataFrame()
    person_rate_map = {}
    if team_df is not None and not team_df.empty:
        for row in team_df.to_dict(orient='records'):
            person_key = str(row.get('Pessoa', '') or '').strip()
            if not person_key:
                continue
            try:
                rate_value = float(row.get('Custo Hora Pessoa (R$)', 0) or 0)
            except Exception:
                continue
            if rate_value > 0:
                person_rate_map[person_key] = rate_value

    product_rate_map = _pm_load_cost_rate_map()
    global_rate = 0.0
    if isinstance(cost_snapshot, dict):
        global_rate = float(((cost_snapshot.get('kpis', {}) or {}).get('Custo Hora Carregado', 0) or 0))

    def _resolve_rate(row):
        person = str(row.get('Colaborador Canonico', '') or '').strip()
        project_key = str(row.get('Projeto PM', '') or '').strip()
        person_rate = float(person_rate_map.get(person, 0) or 0)
        if person_rate > 0:
            return pd.Series([person_rate, 'Pessoa'])
        product_rate = float(product_rate_map.get(project_key, 0) or 0)
        if product_rate > 0:
            return pd.Series([product_rate, 'Produto'])
        if global_rate > 0:
            return pd.Series([global_rate, 'Global'])
        return pd.Series([0.0, 'SemTaxa'])

    df[['Custo Hora Aplicado (R$)', 'RateSource']] = df.apply(_resolve_rate, axis=1)
    df['Custo Real Apontado (R$)'] = df['Horas'] * pd.to_numeric(df['Custo Hora Aplicado (R$)'], errors='coerce').fillna(0.0)

    keep_cols = [
        'MesCompetencia', 'Projeto PM', 'Produto', 'Issue Key', 'AssetID', 'Descrição do Ativo',
        'Tipo do Ativo', 'Colaborador', 'Colaborador Canonico', 'Data do Apontamento das Horas',
        'Horas', 'Atividade Desenvolvida', 'Atividade Desenvolvida Normalizada', 'ConfidenceScore', 'Origem Horas', 'RateSource',
        'Custo Hora Aplicado (R$)', 'Custo Real Apontado (R$)', 'AtivoMapeado',
    ]
    for col in keep_cols:
        if col not in df.columns:
            df[col] = np.nan
    fact_df = df[keep_cols].copy()

    product_summary = (
        fact_df.groupby(['Produto', 'Projeto PM'], dropna=False)
        .agg(
            **{
                'Horas Reais Apontadas': ('Horas', 'sum'),
                'Custo Real Apontado (R$)': ('Custo Real Apontado (R$)', 'sum'),
                'Qtd Worklogs': ('Issue Key', 'size'),
                'Qtd Issues Custo': ('Issue Key', 'nunique'),
                'Qtd Pessoas Custo': ('Colaborador Canonico', 'nunique'),
                'Horas Reais Mapeadas': ('AtivoMapeado', lambda x: float(fact_df.loc[x.index, 'Horas'][x].sum()) if len(x) else 0.0),
                'Custo Real Mapeado (R$)': ('AtivoMapeado', lambda x: float(fact_df.loc[x.index, 'Custo Real Apontado (R$)'][x].sum()) if len(x) else 0.0),
            }
        )
        .reset_index()
    )
    if not product_summary.empty:
        product_summary['% Custo Real Mapeado'] = np.where(
            pd.to_numeric(product_summary['Custo Real Apontado (R$)'], errors='coerce').fillna(0) > 0,
            pd.to_numeric(product_summary['Custo Real Mapeado (R$)'], errors='coerce').fillna(0)
            / pd.to_numeric(product_summary['Custo Real Apontado (R$)'], errors='coerce').fillna(0),
            np.nan,
        )

    asset_summary = pd.DataFrame(columns=[
        'Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo',
        'Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Worklogs', 'Issues'
    ])
    mapped_df = fact_df[fact_df['AtivoMapeado']].copy()
    if not mapped_df.empty:
        asset_summary = (
            mapped_df.groupby(['Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo'], dropna=False)
            .agg(
                **{
                    'Horas Reais Apontadas': ('Horas', 'sum'),
                    'Custo Real Apontado (R$)': ('Custo Real Apontado (R$)', 'sum'),
                    'Worklogs': ('Issue Key', 'size'),
                    'Issues': ('Issue Key', 'nunique'),
                }
            )
            .reset_index()
            .sort_values(['Custo Real Apontado (R$)', 'Horas Reais Apontadas'], ascending=[False, False], ignore_index=True)
        )

    total_cost = float(pd.to_numeric(fact_df['Custo Real Apontado (R$)'], errors='coerce').fillna(0).sum())
    mapped_cost = float(pd.to_numeric(mapped_df.get('Custo Real Apontado (R$)'), errors='coerce').fillna(0).sum()) if not mapped_df.empty else 0.0
    return {
        'available': True,
        'df': fact_df,
        'product_summary': product_summary,
        'asset_summary': asset_summary,
        'snapshot': snapshot or {},
        'overall': {
            'worklogs': int(len(fact_df)),
            'hours': float(pd.to_numeric(fact_df['Horas'], errors='coerce').fillna(0).sum()),
            'cost': total_cost,
            'mapped_cost': mapped_cost,
            'mapped_pct_cost': (mapped_cost / total_cost) if total_cost > 0 else np.nan,
            'mapped_assets': int(mapped_df['AssetID'].nunique()) if not mapped_df.empty else 0,
            'people_with_cost': int(fact_df.loc[fact_df['Colaborador Canonico'].astype(str).str.strip().ne(''), 'Colaborador Canonico'].nunique()),
            'rate_configured': bool(person_rate_map or product_rate_map or global_rate > 0),
        },
    }


def build_throughput_avg_cost_series(tp_done: pd.DataFrame, scope_df: pd.DataFrame, start_ts, end_ts, use_creation_date=False) -> dict:
    series_columns = [
        'Semana',
        'Throughput',
        'DiasUteisRateados',
        'CustoCapacidadeBucket (R$)',
        'HorasProdutivasBucket',
        'Custo Medio Demanda (R$)',
        'Media Movel Custo Medio (R$)',
    ]
    empty_series = pd.DataFrame(columns=series_columns)

    def _summarize_avg_cost(series_df: pd.DataFrame) -> tuple[float, float]:
        if series_df is None or series_df.empty:
            return np.nan, np.nan
        total_throughput = float(pd.to_numeric(series_df.get('Throughput'), errors='coerce').fillna(0).sum())
        total_bucket_cost = float(pd.to_numeric(series_df.get('CustoCapacidadeBucket (R$)'), errors='coerce').fillna(0).sum())
        avg_cost_series = pd.to_numeric(series_df.get('Custo Medio Demanda (R$)'), errors='coerce').dropna()
        avg_cost_period = (total_bucket_cost / total_throughput) if total_throughput > 0 else np.nan
        avg_cost_p85 = float(exact_empirical_percentile(avg_cost_series, 0.85)) if not avg_cost_series.empty else np.nan
        return avg_cost_period, avg_cost_p85

    if tp_done is None or tp_done.empty:
        return {
            'available': False,
            'error': 'Sem demandas entregues suficientes para monetizar a vazão no período.',
            'series_df': empty_series,
        }

    cost_snapshot = build_portfolio_cost_model_snapshot(pd.DataFrame(), pd.to_datetime(start_ts), pd.to_datetime(end_ts))
    if not isinstance(cost_snapshot, dict) or not cost_snapshot.get('available'):
        return {
            'available': False,
            'error': (cost_snapshot or {}).get('error', 'Modelo de custo heurístico indisponível.'),
            'series_df': empty_series,
        }

    product_rates_df = cost_snapshot.get('product_rates_df', pd.DataFrame()).copy()
    model = cost_snapshot.get('model', {}) if isinstance(cost_snapshot.get('model', {}), dict) else {}
    model_kpis = cost_snapshot.get('kpis', {}) if isinstance(cost_snapshot.get('kpis', {}), dict) else {}

    canonical_projects = []
    if scope_df is not None and not scope_df.empty and 'Projeto' in scope_df.columns:
        raw_projects = scope_df['Projeto'].dropna().astype(str).str.strip().unique().tolist()
        canonical_projects = sorted({
            _canonical_pm_product_key(project)
            for project in raw_projects
            if _canonical_pm_product_key(project)
        })

    scoped_rates_df = pd.DataFrame()
    if canonical_projects and product_rates_df is not None and not product_rates_df.empty and 'Projeto PM' in product_rates_df.columns:
        scoped_rates_df = product_rates_df[product_rates_df['Projeto PM'].isin(canonical_projects)].copy()

    if scoped_rates_df is not None and not scoped_rates_df.empty:
        custo_mensal_escopo = float(pd.to_numeric(scoped_rates_df['Custo Mensal Produto (R$)'], errors='coerce').fillna(0).sum())
        capacidade_mensal_escopo = float(pd.to_numeric(scoped_rates_df['Capacidade Mensal Produto (h)'], errors='coerce').fillna(0).sum())
        scope_label = ', '.join(scoped_rates_df['Produto'].dropna().astype(str).str.strip().unique().tolist())
        scope_source = 'produtos filtrados'
    else:
        custo_mensal_escopo = float(model_kpis.get('Custo Total TI Mensal', 0) or 0)
        capacidade_mensal_escopo = float(model_kpis.get('Capacidade Total Mensal (h)', 0) or 0)
        scope_label = 'TI total'
        scope_source = 'escopo global'

    dias_uteis_mes = max(1.0, float(model.get('dias_uteis_mes', 22) or 22))
    custo_hora_escopo = (
        custo_mensal_escopo / capacidade_mensal_escopo
        if capacidade_mensal_escopo > 0
        else float(model_kpis.get('Custo Hora Carregado', 0) or 0)
    )

    if custo_mensal_escopo <= 0 or capacidade_mensal_escopo <= 0 or custo_hora_escopo <= 0:
        return {
            'available': False,
            'error': 'Parâmetros de custo insuficientes para monetizar a vazão. Revise `FLOW_PMO_PORTFOLIO_COST_MODEL` e os mapas salariais.',
            'series_df': empty_series,
            'scope_label': scope_label,
            'scope_source': scope_source,
        }

    cost_df = tp_done.copy()
    cost_df['_FilterDate'] = resolve_filter_date_series(cost_df, use_creation_date=use_creation_date)
    cost_df = cost_df.dropna(subset=['_FilterDate']).copy()
    if cost_df.empty:
        return {
            'available': False,
            'error': 'Sem datas válidas para distribuir o custo médio da demanda.',
            'series_df': empty_series,
            'scope_label': scope_label,
            'scope_source': scope_source,
        }

    issue_key_col = None
    for candidate in ['Issue Key', 'ID', 'ItemID']:
        if candidate in cost_df.columns:
            issue_key_col = candidate
            break
    if issue_key_col:
        worklog_payload = build_worklog_cost_fact(start_ts, end_ts, portfolio_scope_df=pd.DataFrame())
        worklog_df = worklog_payload.get('df', pd.DataFrame()).copy()
        if not worklog_df.empty:
            if canonical_projects:
                worklog_df = worklog_df[worklog_df['Projeto PM'].isin(canonical_projects)].copy()
            issue_cost_df = (
                worklog_df.groupby('Issue Key', dropna=False)
                .agg(
                    **{
                        'Custo Real Item (R$)': ('Custo Real (R$)', 'sum'),
                        'Horas Reais Item': ('Horas', 'sum'),
                    }
                )
                .reset_index()
            )
            if not issue_cost_df.empty:
                cost_df['_IssueKeyForCost'] = cost_df[issue_key_col].apply(_pm_clean_issue_key)
                real_cost_df = cost_df.merge(
                    issue_cost_df,
                    how='left',
                    left_on='_IssueKeyForCost',
                    right_on='Issue Key',
                )
                real_cost_df['Custo Real Item (R$)'] = pd.to_numeric(real_cost_df['Custo Real Item (R$)'], errors='coerce').fillna(0)
                real_cost_df['Horas Reais Item'] = pd.to_numeric(real_cost_df['Horas Reais Item'], errors='coerce').fillna(0)
                covered_real_cost_df = real_cost_df[real_cost_df['Custo Real Item (R$)'] > 0].copy()
                if not covered_real_cost_df.empty:
                    covered_real_cost_df['Semana'] = weekly_bucket_start(covered_real_cost_df['_FilterDate'])
                    series_df = (
                        covered_real_cost_df.groupby('Semana', dropna=False)
                        .agg(
                            **{
                                'Throughput': ('_IssueKeyForCost', 'nunique'),
                                'DiasUteisRateados': ('_FilterDate', lambda values: int(len(pd.bdate_range(pd.Series(values).min().normalize(), pd.Series(values).max().normalize()))) if len(values) else 0),
                                'CustoCapacidadeBucket (R$)': ('Custo Real Item (R$)', 'sum'),
                                'HorasProdutivasBucket': ('Horas Reais Item', 'sum'),
                            }
                        )
                        .reset_index()
                        .sort_values('Semana')
                        .reset_index(drop=True)
                    )
                    series_df['Custo Medio Demanda (R$)'] = np.where(
                        series_df['Throughput'] > 0,
                        series_df['CustoCapacidadeBucket (R$)'] / series_df['Throughput'],
                        np.nan,
                    )
                    series_df['Media Movel Custo Medio (R$)'] = (
                        pd.to_numeric(series_df['Custo Medio Demanda (R$)'], errors='coerce')
                        .rolling(5, min_periods=1)
                        .mean()
                    )
                    avg_cost_mean, avg_cost_p85 = _summarize_avg_cost(series_df)
                    return {
                        'available': True,
                        'series_df': series_df,
                        'avg_cost_mean': avg_cost_mean,
                        'avg_cost_p85': avg_cost_p85,
                        'cost_hour': custo_hora_escopo,
                        'monthly_cost': custo_mensal_escopo,
                        'monthly_capacity_hours': capacidade_mensal_escopo,
                        'dias_uteis_mes': dias_uteis_mes,
                        'scope_label': scope_label,
                        'scope_source': 'worklog_real_por_issue',
                        'product_rates_df': scoped_rates_df if scoped_rates_df is not None else pd.DataFrame(),
                    }

    cost_df['Semana'] = weekly_bucket_start(cost_df['_FilterDate'])
    series_df = (
        cost_df.groupby('Semana')
        .size()
        .reset_index(name='Throughput')
        .sort_values('Semana')
        .reset_index(drop=True)
    )

    period_start = pd.to_datetime(start_ts)
    period_end_exclusive = pd.to_datetime(end_ts) + pd.Timedelta(days=1)
    custo_dia_util = custo_mensal_escopo / dias_uteis_mes
    horas_produtivas_dia = capacidade_mensal_escopo / dias_uteis_mes

    def _bucket_business_days(bucket_start):
        bucket_start = pd.to_datetime(bucket_start)
        bucket_end = bucket_start + pd.Timedelta(days=7)
        effective_start = max(bucket_start, period_start)
        effective_end = min(bucket_end, period_end_exclusive)
        if effective_end <= effective_start:
            return 0
        last_inclusive = effective_end - pd.Timedelta(days=1)
        return int(len(pd.bdate_range(effective_start.normalize(), last_inclusive.normalize())))

    series_df['DiasUteisRateados'] = series_df['Semana'].apply(_bucket_business_days)
    series_df['CustoCapacidadeBucket (R$)'] = series_df['DiasUteisRateados'] * custo_dia_util
    series_df['HorasProdutivasBucket'] = series_df['DiasUteisRateados'] * horas_produtivas_dia
    series_df['Custo Medio Demanda (R$)'] = np.where(
        series_df['Throughput'] > 0,
        series_df['CustoCapacidadeBucket (R$)'] / series_df['Throughput'],
        np.nan,
    )
    series_df['Media Movel Custo Medio (R$)'] = (
        pd.to_numeric(series_df['Custo Medio Demanda (R$)'], errors='coerce')
        .rolling(5, min_periods=1)
        .mean()
    )

    avg_cost_mean, avg_cost_p85 = _summarize_avg_cost(series_df)

    return {
        'available': True,
        'series_df': series_df,
        'avg_cost_mean': avg_cost_mean,
        'avg_cost_p85': avg_cost_p85,
        'cost_hour': custo_hora_escopo,
        'monthly_cost': custo_mensal_escopo,
        'monthly_capacity_hours': capacidade_mensal_escopo,
        'dias_uteis_mes': dias_uteis_mes,
        'scope_label': scope_label,
        'scope_source': scope_source,
        'product_rates_df': scoped_rates_df if scoped_rates_df is not None else pd.DataFrame(),
    }


def _pm_is_execution_status(value) -> bool:
    norm = normalize_text(value)
    if not norm:
        return False
    if norm.startswith('ready '):
        return False
    if any(token in norm for token in _PM_EXECUTION_EXCLUDE_TOKENS):
        return False
    return any(token in norm for token in _PM_EXECUTION_INCLUDE_TOKENS)


def _pm_is_asset_type(value) -> bool:
    return normalize_text(value) in _PM_PORTFOLIO_ASSET_TYPES


def _pm_clean_issue_key(value) -> str:
    if pd.isna(value):
        return ''
    text = str(value).strip().upper()
    if not text or text in {'NAN', 'NONE'}:
        return ''
    return text


def _pm_build_portfolio_lookup(df_portfolio: pd.DataFrame) -> dict:
    if df_portfolio is None or df_portfolio.empty:
        return {}
    id_col = _pm_pick_first_column(df_portfolio, ['ID', 'ItemID'])
    title_col = _pm_pick_first_column(df_portfolio, ['Titulo', 'Title'])
    type_col = _pm_pick_first_column(df_portfolio, ['Tipo', 'ItemType'])
    project_col = _pm_pick_first_column(df_portfolio, ['Projeto'])
    if not id_col or not title_col:
        return {}

    lookup = {}
    for row in df_portfolio.to_dict(orient='records'):
        item_id = _pm_clean_issue_key(row.get(id_col))
        if not item_id:
            continue
        lookup[item_id] = {
            'AssetID': item_id,
            'Descricao do Ativo': str(row.get(title_col, '') or '').strip(),
            'Tipo do Ativo': str(row.get(type_col, '') or '').strip(),
            'Projeto Portfólio': str(row.get(project_col, '') or '').strip(),
        }
    return lookup


def _pm_build_downstream_asset_map(project_key: str, portfolio_lookup: dict) -> pd.DataFrame:
    canonical_project = _canonical_pm_product_key(project_key) or str(project_key or '').strip().upper()
    items_df = load_project_downstream_items_csv(canonical_project)
    if items_df is None or items_df.empty:
        return pd.DataFrame(columns=[
            'Issue Key', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Fonte Vínculo', 'Produto'
        ])

    id_col = _pm_pick_first_column(items_df, ['ID', 'ItemID'])
    title_col = _pm_pick_first_column(items_df, ['Title', 'Titulo'])
    type_col = _pm_pick_first_column(items_df, ['Tipo de Problema', 'Tipo'])
    if not id_col or not title_col:
        return pd.DataFrame(columns=[
            'Issue Key', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Fonte Vínculo', 'Produto'
        ])

    local_lookup = {}
    for row in items_df.to_dict(orient='records'):
        issue_key = _pm_clean_issue_key(row.get(id_col))
        if not issue_key:
            continue
        local_lookup[issue_key] = {
            'AssetID': issue_key,
            'Descrição do Ativo': str(row.get(title_col, '') or '').strip(),
            'Tipo do Ativo': str(row.get(type_col, '') or '').strip(),
        }

    rows = []
    for row in items_df.to_dict(orient='records'):
        issue_key = _pm_clean_issue_key(row.get(id_col))
        if not issue_key:
            continue

        issue_type = str(row.get(type_col, '') or '').strip()
        issue_title = str(row.get(title_col, '') or '').strip()
        asset = None
        source = 'NaoMapeado'
        candidate_keys = []
        for col in ['FeatureLinkID', 'EpicLinkID', 'ParentID']:
            cleaned = _pm_clean_issue_key(row.get(col))
            if cleaned and cleaned not in candidate_keys:
                candidate_keys.append(cleaned)

        for candidate_key in candidate_keys:
            if candidate_key in portfolio_lookup:
                asset = portfolio_lookup[candidate_key]
                source = 'BT'
                break

        if asset is None:
            for candidate_key in candidate_keys:
                local_asset = local_lookup.get(candidate_key)
                if local_asset and _pm_is_asset_type(local_asset.get('Tipo do Ativo')):
                    asset = local_asset
                    source = 'ProjetoLocal'
                    break

        if asset is None and _pm_is_asset_type(issue_type):
            asset = {
                'AssetID': issue_key,
                'Descrição do Ativo': issue_title,
                'Tipo do Ativo': issue_type,
            }
            source = 'ProjetoLocal'

        if asset is None:
            raw_epic_name = row.get('EpicLinkName', '') or row.get('Epic Name', '') or ''
            epic_name = '' if pd.isna(raw_epic_name) else str(raw_epic_name).strip()
            if epic_name and epic_name.lower() != 'nan':
                asset = {
                    'AssetID': f'{canonical_project}:EPICNAME:{normalize_text(epic_name)[:80].upper()}',
                    'Descrição do Ativo': epic_name,
                    'Tipo do Ativo': 'Epic (proxy)',
                }
                source = 'ProjetoLocalNome'

        if asset is None:
            asset = {
                'AssetID': 'NAO_MAPEADO',
                'Descrição do Ativo': 'Não mapeado ao portfólio',
                'Tipo do Ativo': '',
            }

        rows.append({
            'Issue Key': issue_key,
            'AssetID': str(asset.get('AssetID', '') or '').strip(),
            'Descrição do Ativo': str(asset.get('Descrição do Ativo', '') or '').strip(),
            'Tipo do Ativo': str(asset.get('Tipo do Ativo', '') or '').strip(),
            'Fonte Vínculo': source,
            'Produto': _pm_product_label(canonical_project),
        })

    if not rows:
        return pd.DataFrame(columns=[
            'Issue Key', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Fonte Vínculo', 'Produto'
        ])
    return pd.DataFrame(rows).drop_duplicates(subset=['Issue Key'], keep='first')


def _infer_project_key_from_issue(issue_key: str) -> str:
    cleaned = _pm_clean_issue_key(issue_key)
    if not cleaned or '-' not in cleaned:
        return ''
    return _canonical_pm_product_key(cleaned.split('-', 1)[0])


def _build_worklog_portfolio_cost_view_v2_unused(start_ts, end_ts, portfolio_scope_df, project_value=None, responsavel=None) -> dict:
    empty_product_summary = pd.DataFrame(columns=[
        'Produto', 'Projeto PM', 'Horas Reais Worklog', 'Horas Reais Mapeadas', '% Horas Reais Mapeadas',
        'Custo Real Apontado (R$)', 'Custo Real Mapeado (R$)', 'Issues com Worklog', 'Ativos com Worklog',
        '% Horas com Taxa Pessoa', '% Horas com Taxa Aplicada',
    ])
    empty_top_assets = pd.DataFrame(columns=[
        'Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Fonte Vínculo',
        'Horas Reais Worklog', 'Issues', 'Custo Real Apontado (R$)',
    ])
    empty_fact = pd.DataFrame(columns=[
        'Projeto PM', 'Produto', 'Pessoa', 'Issue Key', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo',
        'Fonte Vínculo', 'Data do Apontamento das Horas', 'Horas', 'Custo Hora Aplicado (R$)',
        'Custo Real Apontado (R$)', 'Fonte Taxa', 'ConfidenceScore',
    ])

    capex_df, capex_error = get_capex_snapshot('raw')
    if capex_error and (capex_df is None or capex_df.empty):
        return {
            'available': False,
            'error': capex_error,
            'product_summary': empty_product_summary,
            'top_assets': empty_top_assets,
            'fact_df': empty_fact,
            'overall': {},
        }

    cost_model = build_portfolio_cost_model_snapshot(portfolio_scope_df, start_ts, end_ts)
    if not cost_model.get('available'):
        return {
            'available': False,
            'error': cost_model.get('error', 'Modelo de custo não disponível.'),
            'product_summary': empty_product_summary,
            'top_assets': empty_top_assets,
            'fact_df': empty_fact,
            'overall': {},
        }

    df = capex_df.copy()
    if df.empty:
        return {
            'available': False,
            'error': 'Base CAPEX de worklog vazia no período disponível.',
            'product_summary': empty_product_summary,
            'top_assets': empty_top_assets,
            'fact_df': empty_fact,
            'overall': {},
        }

    start_ts = pd.to_datetime(start_ts)
    end_ts = pd.to_datetime(end_ts)
    period_end_exclusive = end_ts + pd.Timedelta(days=1)
    alias_index = _load_person_alias_index()
    selected_people = set(_normalize_responsavel_filter_values(responsavel, alias_index=alias_index, canonicalize=True))
    selected_project = _canonical_pm_product_key(project_value)

    df['Data do Apontamento das Horas'] = pd.to_datetime(df['Data do Apontamento das Horas'], errors='coerce')
    df = df[
        df['Data do Apontamento das Horas'].notna()
        & (df['Data do Apontamento das Horas'] >= start_ts)
        & (df['Data do Apontamento das Horas'] < period_end_exclusive)
    ].copy()
    if df.empty:
        return {
            'available': False,
            'error': 'Sem worklogs CAPEX no período/filtros atuais.',
            'product_summary': empty_product_summary,
            'top_assets': empty_top_assets,
            'fact_df': empty_fact,
            'overall': {},
        }

    df['Pessoa'] = df['Colaborador'].apply(lambda value: _canonical_person_name(value, alias_index=alias_index))
    if selected_people:
        df = df[df['Pessoa'].isin(selected_people)].copy()
    if df.empty:
        return {
            'available': False,
            'error': 'Sem worklogs CAPEX após aplicar o filtro de responsável.',
            'product_summary': empty_product_summary,
            'top_assets': empty_top_assets,
            'fact_df': empty_fact,
            'overall': {},
        }

    df['Issue Key'] = df['Issue Key'].apply(_pm_clean_issue_key)
    df['Projeto PM'] = df['Projeto Jira'].apply(_canonical_pm_product_key)
    missing_project = df['Projeto PM'].astype(str).str.strip().eq('')
    if missing_project.any():
        df.loc[missing_project, 'Projeto PM'] = df.loc[missing_project, 'Issue Key'].apply(_infer_project_key_from_issue)
    if selected_project:
        df = df[df['Projeto PM'] == selected_project].copy()
    df = df[df['Projeto PM'].astype(str).str.strip().ne('')].copy()
    if df.empty:
        return {
            'available': False,
            'error': 'Sem worklogs CAPEX mapeáveis ao projeto/produto selecionado.',
            'product_summary': empty_product_summary,
            'top_assets': empty_top_assets,
            'fact_df': empty_fact,
            'overall': {},
        }

    df['Produto'] = df['Projeto PM'].apply(_pm_product_label)
    df['Horas'] = pd.to_numeric(df['Horas'], errors='coerce').fillna(0.0)
    df = df[df['Horas'] > 0].copy()
    if df.empty:
        return {
            'available': False,
            'error': 'Sem horas reais positivas de worklog no período.',
            'product_summary': empty_product_summary,
            'top_assets': empty_top_assets,
            'fact_df': empty_fact,
            'overall': {},
        }

    portfolio_lookup = _pm_build_portfolio_lookup(portfolio_scope_df)
    asset_frames = []
    for project_key in sorted(set(df['Projeto PM'].dropna().astype(str).str.strip())):
        asset_map = _pm_build_downstream_asset_map(project_key, portfolio_lookup)
        if asset_map.empty:
            continue
        asset_map = asset_map.rename(columns={
            'AssetID': 'AssetID Fallback',
            'Descrição do Ativo': 'Descrição do Ativo Fallback',
            'Tipo do Ativo': 'Tipo do Ativo Fallback',
            'Fonte Vínculo': 'Fonte Vínculo Fallback',
        })
        asset_map['Projeto PM'] = project_key
        asset_frames.append(asset_map)
    if asset_frames:
        combined_asset_map = pd.concat(asset_frames, ignore_index=True)
        df = df.merge(combined_asset_map, how='left', on=['Projeto PM', 'Issue Key'])
    else:
        df['AssetID Fallback'] = np.nan
        df['Descrição do Ativo Fallback'] = np.nan
        df['Tipo do Ativo Fallback'] = np.nan
        df['Fonte Vínculo Fallback'] = np.nan

    raw_asset_id = df['ID do Projeto'].fillna('').astype(str).str.strip()
    raw_asset_desc = df['Descrição do Ativo'].fillna('').astype(str).str.strip()
    raw_asset_type = df['Tipo do Ativo'].fillna('').astype(str).str.strip()
    merged_asset_id = df['AssetID Fallback'].fillna('').astype(str).str.strip()
    merged_asset_desc = df['Descrição do Ativo Fallback'].fillna('').astype(str).str.strip()
    merged_asset_type = df['Tipo do Ativo Fallback'].fillna('').astype(str).str.strip()
    merged_source = df['Fonte Vínculo Fallback'].fillna('').astype(str).str.strip()

    df['AssetID'] = np.where(raw_asset_id.ne(''), raw_asset_id, merged_asset_id)
    df['Descrição do Ativo Final'] = np.where(raw_asset_desc.ne(''), raw_asset_desc, merged_asset_desc)
    df['Tipo do Ativo Final'] = np.where(raw_asset_type.ne(''), raw_asset_type, merged_asset_type)
    df['Fonte Vínculo Final'] = np.where(raw_asset_id.ne(''), 'WorklogCAPEX', merged_source)
    df.loc[df['AssetID'].astype(str).str.strip().eq(''), 'AssetID'] = 'NAO_MAPEADO'
    df.loc[df['Descrição do Ativo Final'].astype(str).str.strip().eq(''), 'Descrição do Ativo Final'] = 'Não mapeado ao portfólio'
    df.loc[df['Fonte Vínculo Final'].astype(str).str.strip().eq(''), 'Fonte Vínculo Final'] = 'NaoMapeado'

    team_cost_df = cost_model.get('team_df', pd.DataFrame()).copy()
    if team_cost_df is None or team_cost_df.empty:
        team_cost_df = pd.DataFrame(columns=['Pessoa', 'Custo Hora Pessoa (R$)'])
    if 'Custo Hora Pessoa (R$)' not in team_cost_df.columns:
        team_cost_df['Custo Hora Pessoa (R$)'] = np.nan
    person_rate_df = (
        team_cost_df[['Pessoa', 'Custo Hora Pessoa (R$)']]
        .drop_duplicates(subset=['Pessoa'])
        .copy()
    ) if 'Pessoa' in team_cost_df.columns else pd.DataFrame(columns=['Pessoa', 'Custo Hora Pessoa (R$)'])
    person_rate_df['Pessoa'] = person_rate_df['Pessoa'].fillna('').astype(str).str.strip()
    person_rate_df['Custo Hora Pessoa (R$)'] = pd.to_numeric(person_rate_df['Custo Hora Pessoa (R$)'], errors='coerce')
    df = df.merge(person_rate_df, how='left', on='Pessoa')

    product_rates_df = cost_model.get('product_rates_df', pd.DataFrame()).copy()
    if product_rates_df is None or product_rates_df.empty:
        product_rates_df = pd.DataFrame(columns=['Projeto PM', 'Custo Hora Produto (R$)'])
    if 'Projeto PM' not in product_rates_df.columns:
        product_rates_df['Projeto PM'] = ''
    if 'Custo Hora Produto (R$)' not in product_rates_df.columns:
        product_rates_df['Custo Hora Produto (R$)'] = np.nan
    product_rates_df = product_rates_df[['Projeto PM', 'Custo Hora Produto (R$)']].drop_duplicates(subset=['Projeto PM']).copy()
    product_rates_df['Projeto PM'] = product_rates_df['Projeto PM'].fillna('').astype(str).str.strip()
    product_rates_df['Custo Hora Produto (R$)'] = pd.to_numeric(product_rates_df['Custo Hora Produto (R$)'], errors='coerce')
    df = df.merge(product_rates_df, how='left', on='Projeto PM')

    global_rate = float(cost_model.get('kpis', {}).get('Custo Hora Carregado', 0) or 0)
    person_rate = pd.to_numeric(df['Custo Hora Pessoa (R$)'], errors='coerce')
    product_rate = pd.to_numeric(df['Custo Hora Produto (R$)'], errors='coerce')
    df['Custo Hora Aplicado (R$)'] = person_rate
    df.loc[df['Custo Hora Aplicado (R$)'].isna(), 'Custo Hora Aplicado (R$)'] = product_rate
    if global_rate > 0:
        df['Custo Hora Aplicado (R$)'] = df['Custo Hora Aplicado (R$)'].fillna(global_rate)
    df['Fonte Taxa'] = np.where(
        person_rate.notna() & (person_rate > 0),
        'Pessoa',
        np.where(
            product_rate.notna() & (product_rate > 0),
            'Produto',
            'Global' if global_rate > 0 else 'Indisponivel'
        )
    )
    df['Custo Real Apontado (R$)'] = df['Horas'] * pd.to_numeric(df['Custo Hora Aplicado (R$)'], errors='coerce').fillna(0.0)

    mapped_mask = df['AssetID'].astype(str).str.strip().ne('NAO_MAPEADO')
    person_rate_mask = df['Fonte Taxa'].astype(str).eq('Pessoa')
    applied_rate_mask = df['Fonte Taxa'].astype(str).ne('Indisponivel')

    fact_df = pd.DataFrame({
        'Projeto PM': df['Projeto PM'],
        'Produto': df['Produto'],
        'Pessoa': df['Pessoa'],
        'Issue Key': df['Issue Key'],
        'AssetID': df['AssetID'],
        'Descrição do Ativo': df['Descrição do Ativo Final'],
        'Tipo do Ativo': df['Tipo do Ativo Final'],
        'Fonte Vínculo': df['Fonte Vínculo Final'],
        'Data do Apontamento das Horas': df['Data do Apontamento das Horas'],
        'Horas': df['Horas'],
        'Atividade Desenvolvida': df.get('Atividade Desenvolvida', ''),
        'Atividade Desenvolvida Normalizada': df.get('Atividade Desenvolvida Normalizada', ''),
        'ConfidenceScore': pd.to_numeric(df.get('ConfidenceScore'), errors='coerce'),
        'Custo Hora Aplicado (R$)': pd.to_numeric(df['Custo Hora Aplicado (R$)'], errors='coerce').fillna(0.0),
        'Custo Real Apontado (R$)': pd.to_numeric(df['Custo Real Apontado (R$)'], errors='coerce').fillna(0.0),
        'Fonte Taxa': df['Fonte Taxa'],
        'Origem Horas': df.get('Origem Horas', ''),
    }).copy()

    product_summary_rows = []
    for (produto, projeto_pm), group_df in fact_df.groupby(['Produto', 'Projeto PM'], dropna=False):
        total_hours = float(pd.to_numeric(group_df['Horas'], errors='coerce').fillna(0).sum())
        mapped_hours = float(pd.to_numeric(group_df.loc[group_df['AssetID'].astype(str).ne('NAO_MAPEADO'), 'Horas'], errors='coerce').fillna(0).sum())
        total_cost = float(pd.to_numeric(group_df['Custo Real Apontado (R$)'], errors='coerce').fillna(0).sum())
        mapped_cost = float(pd.to_numeric(group_df.loc[group_df['AssetID'].astype(str).ne('NAO_MAPEADO'), 'Custo Real Apontado (R$)'], errors='coerce').fillna(0).sum())
        person_rate_hours = float(pd.to_numeric(group_df.loc[group_df['Fonte Taxa'].astype(str).eq('Pessoa'), 'Horas'], errors='coerce').fillna(0).sum())
        applied_rate_hours = float(pd.to_numeric(group_df.loc[group_df['Fonte Taxa'].astype(str).ne('Indisponivel'), 'Horas'], errors='coerce').fillna(0).sum())
        product_summary_rows.append({
            'Produto': produto,
            'Projeto PM': projeto_pm,
            'Horas Reais Worklog': total_hours,
            'Horas Reais Mapeadas': mapped_hours,
            '% Horas Reais Mapeadas': (mapped_hours / total_hours * 100.0) if total_hours > 0 else np.nan,
            'Custo Real Apontado (R$)': total_cost,
            'Custo Real Mapeado (R$)': mapped_cost,
            'Issues com Worklog': int(group_df.loc[group_df['Issue Key'].astype(str).str.strip().ne(''), 'Issue Key'].nunique()),
            'Ativos com Worklog': int(group_df.loc[group_df['AssetID'].astype(str).ne('NAO_MAPEADO'), 'AssetID'].nunique()),
            '% Horas com Taxa Pessoa': (person_rate_hours / total_hours * 100.0) if total_hours > 0 else np.nan,
            '% Horas com Taxa Aplicada': (applied_rate_hours / total_hours * 100.0) if total_hours > 0 else np.nan,
        })
    product_summary = pd.DataFrame(product_summary_rows)
    if product_summary.empty:
        product_summary = empty_product_summary.copy()

    top_assets = pd.DataFrame(columns=empty_top_assets.columns)
    mapped_events = fact_df[fact_df['AssetID'].astype(str).ne('NAO_MAPEADO')].copy()
    if not mapped_events.empty:
        top_assets = (
            mapped_events
            .groupby(['Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Fonte Vínculo'], dropna=False)
            .agg(
                **{
                    'Horas Reais Worklog': ('Horas', 'sum'),
                    'Issues': ('Issue Key', 'nunique'),
                    'Custo Real Apontado (R$)': ('Custo Real Apontado (R$)', 'sum'),
                }
            )
            .reset_index()
            .sort_values(['Custo Real Apontado (R$)', 'Horas Reais Worklog'], ascending=[False, False], ignore_index=True)
        )

    total_hours = float(pd.to_numeric(fact_df['Horas'], errors='coerce').fillna(0).sum())
    total_cost = float(pd.to_numeric(fact_df['Custo Real Apontado (R$)'], errors='coerce').fillna(0).sum())
    mapped_hours = float(pd.to_numeric(fact_df.loc[mapped_mask, 'Horas'], errors='coerce').fillna(0).sum())
    person_rate_hours = float(pd.to_numeric(fact_df.loc[person_rate_mask, 'Horas'], errors='coerce').fillna(0).sum())
    applied_rate_hours = float(pd.to_numeric(fact_df.loc[applied_rate_mask, 'Horas'], errors='coerce').fillna(0).sum())

    return {
        'available': True,
        'error': None,
        'cost_model': cost_model,
        'fact_df': fact_df,
        'product_summary': product_summary,
        'top_assets': top_assets,
        'overall': {
            'hours': total_hours,
            'cost': total_cost,
            'mapped_hours': mapped_hours,
            'mapped_pct': (mapped_hours / total_hours * 100.0) if total_hours > 0 else np.nan,
            'person_rate_pct': (person_rate_hours / total_hours * 100.0) if total_hours > 0 else np.nan,
            'rate_applied_pct': (applied_rate_hours / total_hours * 100.0) if total_hours > 0 else np.nan,
            'assets_mapped': int(fact_df.loc[mapped_mask, 'AssetID'].nunique()),
            'products_with_worklogs': int(product_summary['Projeto PM'].nunique()) if not product_summary.empty else 0,
        },
    }


def _build_synthetic_capex_worklog_from_pm(events_all: 'pd.DataFrame') -> 'pd.DataFrame':
    """
    Converts PM execution events into a synthetic CAPEX worklog fact table.
    Used as fallback when no real Jira worklogs exist (no manual time tracking).
    Each execution event (status permanence × hours) becomes one synthetic worklog row.
    Output schema matches build_capex_worklog_cost_fact()['df'].
    """
    _empty = pd.DataFrame(columns=[
        'MesCompetencia', 'Projeto PM', 'Produto', 'Issue Key', 'AssetID', 'Descrição do Ativo',
        'Tipo do Ativo', 'Colaborador', 'Colaborador Canonico', 'Data do Apontamento das Horas',
        'Horas', 'Atividade Desenvolvida', 'Atividade Desenvolvida Normalizada', 'ConfidenceScore',
        'Origem Horas', 'RateSource', 'Custo Hora Aplicado (R$)', 'Custo Real Apontado (R$)', 'AtivoMapeado',
    ])
    if events_all is None or events_all.empty:
        return _empty

    df = events_all.copy()
    df = df[pd.to_numeric(df.get('Horas PM Elegíveis', 0), errors='coerce').fillna(0) > 0].copy()
    if df.empty:
        return _empty

    df['Horas'] = pd.to_numeric(df['Horas PM Elegíveis'], errors='coerce').fillna(0.0)
    df['Colaborador'] = df.get('Responsável PM', pd.Series('', index=df.index)).fillna('').astype(str)
    df['Colaborador Canonico'] = df['Colaborador']
    df['Data do Apontamento das Horas'] = pd.to_datetime(df.get('History Created'), errors='coerce')
    df['MesCompetencia'] = df['Data do Apontamento das Horas'].dt.strftime('%Y-%m').fillna('')

    status_col = (
        df['To Status Norm'] if 'To Status Norm' in df.columns
        else df.get('To Status', pd.Series('', index=df.index))
    )
    df['Atividade Desenvolvida'] = status_col.fillna('').astype(str)
    df['Atividade Desenvolvida Normalizada'] = df['Atividade Desenvolvida']

    df['ConfidenceScore'] = 1.0
    df['Origem Horas'] = 'PM - Permanência em Execução'
    df['RateSource'] = 'PM'

    custo_pm = pd.to_numeric(df.get('Custo PM Estimado', np.nan), errors='coerce')
    horas_nz = df['Horas'].replace(0, np.nan)
    df['Custo Hora Aplicado (R$)'] = (custo_pm / horas_nz).fillna(0.0)
    df['Custo Real Apontado (R$)'] = custo_pm.fillna(0.0)

    for col, default in [('AssetID', 'NAO_MAPEADO'), ('Descrição do Ativo', 'Não mapeado ao portfólio'), ('Tipo do Ativo', '')]:
        if col not in df.columns:
            df[col] = default
        df[col] = df[col].fillna(default).astype(str)

    df['AtivoMapeado'] = ~df['AssetID'].str.strip().isin(['', 'NAO_MAPEADO', 'nan', 'NaN'])

    keep_cols = [
        'MesCompetencia', 'Projeto PM', 'Produto', 'Issue Key', 'AssetID', 'Descrição do Ativo',
        'Tipo do Ativo', 'Colaborador', 'Colaborador Canonico', 'Data do Apontamento das Horas',
        'Horas', 'Atividade Desenvolvida', 'Atividade Desenvolvida Normalizada', 'ConfidenceScore',
        'Origem Horas', 'RateSource', 'Custo Hora Aplicado (R$)', 'Custo Real Apontado (R$)', 'AtivoMapeado',
    ]
    for col in keep_cols:
        if col not in df.columns:
            df[col] = np.nan
    return df[keep_cols].copy()


def build_pm_portfolio_capex_view(start_ts, end_ts, portfolio_scope_df, project_value=None, responsavel=None) -> dict:
    specs = _pm_portfolio_selected_specs(project_value)
    rate_map = _pm_load_cost_rate_map()
    alias_index = _load_person_alias_index()
    selected_people = set(_normalize_responsavel_filter_values(responsavel, alias_index=alias_index, canonicalize=True))
    portfolio_lookup = _pm_build_portfolio_lookup(portfolio_scope_df)
    period_end_exclusive = pd.to_datetime(end_ts) + pd.Timedelta(days=1)
    capex_cost_data = build_capex_worklog_cost_fact(start_ts, end_ts, portfolio_scope_df, project_value=project_value, responsavel=responsavel)
    capex_product_summary = capex_cost_data.get('product_summary', pd.DataFrame()).copy() if isinstance(capex_cost_data, dict) else pd.DataFrame()
    capex_asset_summary = capex_cost_data.get('asset_summary', pd.DataFrame()).copy() if isinstance(capex_cost_data, dict) else pd.DataFrame()
    capex_overall = capex_cost_data.get('overall', {}) if isinstance(capex_cost_data, dict) else {}

    product_summary_rows = []
    event_frames = []
    all_phase_frames = []

    for spec in specs:
        project_key = spec['project_key']
        product_label = spec['product']
        rate = rate_map.get(project_key)
        raw_events = load_project_pm_sheet(project_key, 'EventosFiltrados')
        artifact_available = raw_events is not None and not raw_events.empty
        project_events = pd.DataFrame()

        if artifact_available:
            project_events = raw_events.copy()
            for col in ['Issue Key', 'To Status Norm', 'To Status', 'Author', 'Projeto']:
                if col not in project_events.columns:
                    project_events[col] = ''
            if 'TempoStatusDias' not in project_events.columns:
                project_events['TempoStatusDias'] = np.nan
            project_events['Issue Key'] = project_events['Issue Key'].apply(_pm_clean_issue_key)
            project_events['Projeto'] = project_events['Projeto'].fillna(project_key).astype(str).str.strip()
            project_events['History Created'] = pd.to_datetime(project_events.get('History Created'), errors='coerce')
            project_events = project_events[
                project_events['Issue Key'].ne('')
                & project_events['History Created'].notna()
                & (project_events['History Created'] >= pd.to_datetime(start_ts))
                & (project_events['History Created'] < period_end_exclusive)
            ].copy()
            project_events['Responsável PM'] = project_events['Author'].apply(
                lambda x: _canonical_person_name(x, alias_index=alias_index)
            )
            if selected_people:
                project_events = project_events[project_events['Responsável PM'].isin(selected_people)].copy()
            project_events['Status PM Elegível'] = project_events.get('To Status Norm', project_events.get('To Status', '')).apply(_pm_is_execution_status)
            project_events['Horas PM Elegíveis'] = (
                pd.to_numeric(project_events['TempoStatusDias'], errors='coerce').fillna(0) * 24.0
            )
            project_events.loc[~project_events['Status PM Elegível'], 'Horas PM Elegíveis'] = 0.0

            # Capture all phases (including waiting/queue) before the execution filter
            _all = project_events.copy()
            _all['Produto'] = product_label
            _all['Projeto PM'] = project_key
            _all['Taxa Hora PM'] = rate if rate is not None else np.nan
            all_phase_frames.append(_all)

            project_events = project_events[project_events['Horas PM Elegíveis'] > 0].copy()

        if not project_events.empty:
            asset_map = _pm_build_downstream_asset_map(project_key, portfolio_lookup)
            if not asset_map.empty:
                project_events = project_events.merge(asset_map, how='left', on='Issue Key')
            for col, default in [
                ('AssetID', 'NAO_MAPEADO'),
                ('Descrição do Ativo', 'Não mapeado ao portfólio'),
                ('Tipo do Ativo', ''),
                ('Fonte Vínculo', 'NaoMapeado'),
            ]:
                if col not in project_events.columns:
                    project_events[col] = default
                project_events[col] = project_events[col].fillna(default)
            project_events['Produto'] = product_label
            project_events['Projeto PM'] = project_key
            project_events['Custo PM Estimado'] = (
                project_events['Horas PM Elegíveis'] * rate if rate is not None else np.nan
            )
            event_frames.append(project_events)

        total_hours = float(pd.to_numeric(project_events.get('Horas PM Elegíveis'), errors='coerce').fillna(0).sum()) if not project_events.empty else 0.0
        mapped_mask = project_events['Fonte Vínculo'].astype(str).ne('NaoMapeado') if not project_events.empty else pd.Series(dtype=bool)
        mapped_hours = float(
            pd.to_numeric(project_events.loc[mapped_mask, 'Horas PM Elegíveis'], errors='coerce').fillna(0).sum()
        ) if not project_events.empty else 0.0
        product_summary_rows.append({
            'Produto': product_label,
            'Projeto PM': project_key,
            'Artefato PM': 'Disponível' if artifact_available else 'Indisponível',
            'Horas PM Elegíveis': total_hours,
            'Horas PM Mapeadas': mapped_hours,
            'Horas PM Não Mapeadas': max(0.0, total_hours - mapped_hours),
            '% Horas Mapeadas': (mapped_hours / total_hours * 100.0) if total_hours > 0 else np.nan,
            'Itens com Evidência PM': int(project_events['Issue Key'].nunique()) if not project_events.empty else 0,
            'Ativos Mapeados': int(project_events.loc[mapped_mask, 'AssetID'].nunique()) if not project_events.empty else 0,
            'Taxa Hora PM': rate if rate is not None else np.nan,
            'Custo PM Estimado': (total_hours * rate) if rate is not None else np.nan,
            'Custo PM Mapeado': (mapped_hours * rate) if rate is not None else np.nan,
        })

    product_summary = pd.DataFrame(product_summary_rows)
    if product_summary.empty:
        product_summary = pd.DataFrame(columns=[
            'Produto', 'Projeto PM', 'Artefato PM', 'Horas PM Elegíveis', 'Horas PM Mapeadas',
            'Horas PM Não Mapeadas', '% Horas Mapeadas', 'Itens com Evidência PM', 'Ativos Mapeados',
            'Taxa Hora PM', 'Custo PM Estimado', 'Custo PM Mapeado',
        ])
    if capex_product_summary is not None and not capex_product_summary.empty:
        product_summary = product_summary.merge(
            capex_product_summary,
            on=['Produto', 'Projeto PM'],
            how='outer',
        )
        for col in ['Artefato PM']:
            if col in product_summary.columns:
                product_summary[col] = product_summary[col].fillna('Indisponível')

    events_all = pd.concat(event_frames, ignore_index=True) if event_frames else pd.DataFrame(columns=[
        'Produto', 'Projeto PM', 'Issue Key', 'Horas PM Elegíveis', 'AssetID', 'Descrição do Ativo',
        'Tipo do Ativo', 'Fonte Vínculo', 'Responsável PM', 'Custo PM Estimado',
    ])
    all_events_df = pd.concat(all_phase_frames, ignore_index=True) if all_phase_frames else pd.DataFrame()

    # Fallback: se não há worklogs reais, gera worklog sintético a partir de eventos PM de execução
    _capex_df = capex_cost_data.get('df', pd.DataFrame()) if isinstance(capex_cost_data, dict) else pd.DataFrame()
    if (_capex_df is None or _capex_df.empty) and not events_all.empty:
        _synthetic_df = _build_synthetic_capex_worklog_from_pm(events_all)
        if not _synthetic_df.empty:
            capex_cost_data = dict(capex_cost_data) if isinstance(capex_cost_data, dict) else {}
            capex_cost_data['df'] = _synthetic_df
            capex_cost_data['available'] = True
            capex_cost_data['error'] = None

    top_assets = pd.DataFrame(columns=[
        'Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Fonte Vínculo',
        'Horas PM Elegíveis', 'Issues', 'Custo PM Estimado',
    ])
    if not events_all.empty:
        mapped_events = events_all[events_all['Fonte Vínculo'].astype(str).ne('NaoMapeado')].copy()
        if not mapped_events.empty:
            top_assets = (
                mapped_events
                .groupby(['Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Fonte Vínculo'], dropna=False)
                .agg(
                    **{
                        'Horas PM Elegíveis': ('Horas PM Elegíveis', 'sum'),
                        'Issues': ('Issue Key', 'nunique'),
                        'Custo PM Estimado': ('Custo PM Estimado', 'sum'),
                    }
                )
                .reset_index()
                .sort_values(['Horas PM Elegíveis', 'Issues'], ascending=[False, False], ignore_index=True)
            )
    if capex_asset_summary is not None and not capex_asset_summary.empty:
        top_assets = top_assets.merge(
            capex_asset_summary,
            on=['Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo'],
            how='outer',
        )
        if 'Fonte Vínculo' in top_assets.columns:
            top_assets['Fonte Vínculo'] = top_assets['Fonte Vínculo'].fillna('CAPEX')
        sort_col = 'Custo Real Apontado (R$)' if 'Custo Real Apontado (R$)' in top_assets.columns else 'Custo PM Estimado'
        secondary_col = 'Horas Reais Apontadas' if 'Horas Reais Apontadas' in top_assets.columns else 'Horas PM Elegíveis'
        top_assets = top_assets.sort_values([sort_col, secondary_col], ascending=[False, False], ignore_index=True)

    overall_hours = float(pd.to_numeric(product_summary.get('Horas PM Elegíveis'), errors='coerce').fillna(0).sum()) if not product_summary.empty else 0.0
    overall_mapped = float(pd.to_numeric(product_summary.get('Horas PM Mapeadas'), errors='coerce').fillna(0).sum()) if not product_summary.empty else 0.0
    overall_cost = float(pd.to_numeric(product_summary.get('Custo PM Estimado'), errors='coerce').fillna(0).sum()) if not product_summary.empty else 0.0

    # ── Triangulação de touch time (3 modelos) ────────────────────────────────
    _period_days = max(1, int((period_end_exclusive - pd.to_datetime(start_ts)).days))
    _period_months = max(1.0 / 30.0, _period_days / 30.4375)
    touch_time_triangulation = build_touch_time_triangulation(
        all_events_df,
        portfolio_scope_df,
        period_months=_period_months,
    )

    return {
        'product_summary': product_summary,
        'events_all': events_all,
        'top_assets': top_assets,
        'overall': {
            'hours': overall_hours,
            'mapped_hours': overall_mapped,
            'mapped_pct': (overall_mapped / overall_hours * 100.0) if overall_hours > 0 else np.nan,
            'cost': overall_cost,
            'products_with_artifacts': int((product_summary['Artefato PM'] == 'Disponível').sum()) if not product_summary.empty else 0,
            'assets_mapped': int(pd.to_numeric(product_summary.get('Ativos Mapeados'), errors='coerce').fillna(0).sum()) if not product_summary.empty else 0,
            'cost_configured': bool(rate_map),
            'actual_worklogs': int(capex_overall.get('worklogs', 0) or 0),
            'actual_hours': float(capex_overall.get('hours', 0.0) or 0.0),
            'actual_cost': float(capex_overall.get('cost', 0.0) or 0.0),
            'actual_mapped_cost': float(capex_overall.get('mapped_cost', 0.0) or 0.0),
            'actual_mapped_pct_cost': capex_overall.get('mapped_pct_cost'),
            'actual_assets_mapped': int(capex_overall.get('mapped_assets', 0) or 0),
            'actual_cost_configured': bool(capex_overall.get('rate_configured')),
        },
        'capex_cost_data': capex_cost_data,
        'all_events_df': all_events_df,
        'touch_time_triangulation': touch_time_triangulation,
    }


def build_generated_portfolio_financial_view(start_ts, end_ts, portfolio_scope_df, pm_portfolio_data: dict) -> dict:
    cost_model = build_portfolio_cost_model_snapshot(portfolio_scope_df, start_ts, end_ts)
    if not cost_model.get('available'):
        return {
            'available': False,
            'error': cost_model.get('error', 'Modelo de custo não disponível.'),
        }

    top_assets = pm_portfolio_data.get('top_assets', pd.DataFrame()).copy()
    overall = pm_portfolio_data.get('overall', {}) if isinstance(pm_portfolio_data, dict) else {}
    kpis = dict(cost_model.get('kpis', {}))
    budget_ti_anual = float(kpis.get('Budget TI Anual', 0) or 0)
    custo_hora = float(kpis.get('Custo Hora Carregado', 0) or 0)
    portfolio_assets_df = cost_model.get('portfolio_assets_df', pd.DataFrame()).copy()
    total_assets_portfolio = int(portfolio_assets_df['AssetID'].nunique()) if not portfolio_assets_df.empty and 'AssetID' in portfolio_assets_df.columns else 0

    period_days = max(1, int((pd.to_datetime(end_ts) - pd.to_datetime(start_ts)).days) + 1)
    period_months = max(1.0 / 30.0, float(period_days) / 30.4375)
    annualization_factor = 12.0 / period_months
    custo_real_periodo = float(overall.get('actual_cost', 0.0) or 0.0)
    custo_estimado_pm_periodo = float(overall.get('cost', 0.0) or 0.0)
    custo_periodo_base = custo_real_periodo if custo_real_periodo > 0 else custo_estimado_pm_periodo
    custo_anualizado = custo_periodo_base * annualization_factor
    budget_disponivel = budget_ti_anual - custo_anualizado
    budget_pct = (custo_anualizado / budget_ti_anual) if budget_ti_anual > 0 else np.nan
    custo_medio_topdown = (budget_ti_anual / total_assets_portfolio) if total_assets_portfolio > 0 else np.nan

    project_costs_df = pd.DataFrame(columns=[
        'Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Fonte Vínculo',
        'Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Horas PM Elegíveis',
        'Custo PM Estimado', 'Custo Base Período (R$)', 'Custo Base Anualizado (R$)',
        '% do Budget TI Anual', 'Issues', 'Worklogs'
    ])
    if not top_assets.empty:
        project_costs_df = top_assets.copy()
        if 'Custo PM Estimado' not in project_costs_df.columns:
            project_costs_df['Custo PM Estimado'] = np.nan
        if 'Custo Real Apontado (R$)' not in project_costs_df.columns:
            project_costs_df['Custo Real Apontado (R$)'] = np.nan
        project_costs_df['Custo Base Período (R$)'] = pd.to_numeric(project_costs_df['Custo Real Apontado (R$)'], errors='coerce')
        missing_base = project_costs_df['Custo Base Período (R$)'].isna() | (project_costs_df['Custo Base Período (R$)'] <= 0)
        project_costs_df.loc[missing_base, 'Custo Base Período (R$)'] = pd.to_numeric(
            project_costs_df.loc[missing_base, 'Custo PM Estimado'], errors='coerce'
        ).fillna(0)
        project_costs_df['Custo Base Anualizado (R$)'] = project_costs_df['Custo Base Período (R$)'] * annualization_factor
        project_costs_df['% do Budget TI Anual'] = np.where(
            budget_ti_anual > 0,
            project_costs_df['Custo Base Anualizado (R$)'] / budget_ti_anual,
            np.nan,
        )
        keep_cols = [
            'Produto', 'AssetID', 'Descrição do Ativo', 'Tipo do Ativo', 'Fonte Vínculo',
            'Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Horas PM Elegíveis',
            'Custo PM Estimado', 'Custo Base Período (R$)', 'Custo Base Anualizado (R$)',
            '% do Budget TI Anual', 'Issues', 'Worklogs'
        ]
        existing_keep_cols = [col for col in keep_cols if col in project_costs_df.columns]
        project_costs_df = project_costs_df[existing_keep_cols].copy()
        for col in ['Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Horas PM Elegíveis', 'Custo PM Estimado', 'Custo Base Período (R$)', 'Custo Base Anualizado (R$)', '% do Budget TI Anual']:
            if col in project_costs_df.columns:
                project_costs_df[col] = pd.to_numeric(project_costs_df[col], errors='coerce')

    custo_medio_bottomup = (
        float(project_costs_df['Custo Base Anualizado (R$)'].mean())
        if not project_costs_df.empty and 'Custo Base Anualizado (R$)' in project_costs_df.columns
        else np.nan
    )

    product_cost_summary_df = pd.DataFrame()
    product_summary = pm_portfolio_data.get('product_summary', pd.DataFrame()).copy() if isinstance(pm_portfolio_data, dict) else pd.DataFrame()
    if not product_summary.empty:
        product_cost_summary_df = product_summary.copy()
        if 'Custo PM Estimado' not in product_cost_summary_df.columns:
            product_cost_summary_df['Custo PM Estimado'] = np.nan
        if 'Custo Real Apontado (R$)' not in product_cost_summary_df.columns:
            product_cost_summary_df['Custo Real Apontado (R$)'] = np.nan
        product_cost_summary_df['Custo Base Período (R$)'] = pd.to_numeric(product_cost_summary_df['Custo Real Apontado (R$)'], errors='coerce')
        missing_base = product_cost_summary_df['Custo Base Período (R$)'].isna() | (product_cost_summary_df['Custo Base Período (R$)'] <= 0)
        product_cost_summary_df.loc[missing_base, 'Custo Base Período (R$)'] = pd.to_numeric(
            product_cost_summary_df.loc[missing_base, 'Custo PM Estimado'], errors='coerce'
        ).fillna(0)
        product_cost_summary_df['Custo Base Anualizado (R$)'] = product_cost_summary_df['Custo Base Período (R$)'] * annualization_factor
        product_cost_summary_df['% do Budget TI Anual'] = np.where(
            budget_ti_anual > 0,
            product_cost_summary_df['Custo Base Anualizado (R$)'] / budget_ti_anual,
            np.nan,
        )

    notes = []
    if float(kpis.get('Budget TI Anual', 0) or 0) <= 0:
        notes.append('Configure `FLOW_PMO_PORTFOLIO_COST_MODEL.fl_mensal` para habilitar budget anual heurístico.')
    if float(kpis.get('Custo Hora Carregado', 0) or 0) <= 0:
        notes.append('Configure salário médio ou mapas por papel/BU para o custo hora heurístico.')
    if float(overall.get('actual_cost', 0) or 0) > 0:
        notes.append('Custo base do portfólio prioriza worklog real; custo PM permanece como trilha estimada paralela.')
    elif float(overall.get('cost', 0) or 0) > 0:
        notes.append('Sem custo real apontado no período; custo base do portfólio está usando estimativa por process mining.')
    if float(overall.get('hours', 0) or 0) <= 0:
        notes.append('Sem horas PM elegíveis no período para monetizar os ativos do portfólio.')

    return {
        'available': True,
        'cost_model': cost_model,
        'kpis': {
            'Budget TI Anual': budget_ti_anual,
            'Custo Total do Portfólio': custo_anualizado,
            'Custo Base Período': custo_periodo_base,
            'Custo Real Apontado': custo_real_periodo,
            'Custo Estimado PM': custo_estimado_pm_periodo,
            'Budget Disponível': budget_disponivel,
            '% Budget Comprometido': budget_pct,
            'Custo Hora Carregado': custo_hora,
            'Custo Médio Projeto (Top-Down)': custo_medio_topdown,
            'Custo Médio Projeto (Bottom-Up)': custo_medio_bottomup,
            '% Custo Real Mapeado': overall.get('actual_mapped_pct_cost'),
            'Fonte Primária Custo': 'Worklog real' if custo_real_periodo > 0 else ('Process mining' if custo_estimado_pm_periodo > 0 else 'Indisponível'),
            'Headcount TI': kpis.get('Headcount TI', 0),
            'Capacidade Total Mensal (h)': kpis.get('Capacidade Total Mensal (h)', 0),
            'Custo Total TI Mensal': kpis.get('Custo Total TI Mensal', 0),
        },
        'project_costs_df': project_costs_df,
        'product_cost_summary_df': product_cost_summary_df,
        'product_rates_df': cost_model.get('product_rates_df', pd.DataFrame()).copy(),
        'notes': notes,
        'annualization_factor': annualization_factor,
        'total_assets_portfolio': total_assets_portfolio,
    }


def build_portfolio_cross_delivery_integration(start_ts, end_ts, portfolio_scope_df, pm_portfolio_data: dict = None, generated_financials: dict = None) -> dict:
    empty_asset_df = pd.DataFrame(columns=[
        'AssetID', 'Projeto PM', 'Produto', 'Tipo', 'Team', 'Titulo', 'Status Portfolio', 'DueDate',
        'ItensDownstream', 'ItensDone', 'ItensReadyProd', 'CasosPM', 'Lead Time Fluxo Médio (dias)',
        'Cycle Time Dev Médio (dias)', 'Horas Reais Apontadas', 'Custo Real Apontado (R$)',
        'DependenciesTotal', 'DependenciesAbertasConhecidas', 'PrazoRealStatus', 'ProxyRealizacaoValor', 'Link'
    ])
    empty_product_df = pd.DataFrame(columns=[
        'Projeto PM', 'Produto', 'Capacidade Período (h)', 'Horas Consumidas', '% Capacidade Consumida',
        'Assets Portfolio', 'Assets com Evidência', 'Assets Entregues', '% Valor Realizado (proxy)'
    ])
    empty_dependency_df = pd.DataFrame(columns=[
        'AssetID', 'Produto', 'Titulo', 'DependenciesTotal', 'DependenciesAbertasConhecidas', 'DependenciesExternas', 'PrazoRealStatus', 'Link'
    ])
    empty_kpis = pd.DataFrame(columns=['Indicador', 'Valor', 'Detalhe'])
    empty_notes = [
        'Sem ativos de portfólio elegíveis no escopo atual para cruzar com downstream/process mining.'
    ]

    if portfolio_scope_df is None or portfolio_scope_df.empty:
        return {
            'available': False,
            'asset_delivery_df': empty_asset_df,
            'product_capacity_df': empty_product_df,
            'dependency_df': empty_dependency_df,
            'kpis_df': empty_kpis,
            'notes': empty_notes,
        }

    scope = portfolio_scope_df.copy()
    for col in ['ID', 'Titulo', 'Tipo', 'Status', 'Projeto', 'Team', 'Link']:
        if col not in scope.columns:
            scope[col] = ''
    if 'DueDate' not in scope.columns:
        scope['DueDate'] = pd.NaT
    scope['DueDate'] = pd.to_datetime(scope['DueDate'], errors='coerce')
    if 'IssueLinkKeys' not in scope.columns:
        scope['IssueLinkKeys'] = ''
    scope['TipoNorm'] = scope['Tipo'].apply(normalize_text)
    scope['AssetID'] = scope['ID'].astype(str).str.strip().str.upper()
    scope['TeamPortfolio'] = scope['Team'].fillna('').astype(str).str.strip()
    scope['Projeto PM'] = scope['TeamPortfolio'].apply(_portfolio_team_to_pm_project_key)
    scope['Projeto PM'] = np.where(
        scope['Projeto PM'].astype(str).str.strip().eq(''),
        scope['Projeto'].apply(_canonical_pm_product_key),
        scope['Projeto PM'],
    )
    scope['Produto'] = scope['Projeto PM'].apply(_pm_product_label)
    asset_scope = scope[scope['TipoNorm'].isin({'epic', 'epico', 'feature', 'funcionalidade'})].copy()
    asset_scope = asset_scope[asset_scope['AssetID'].ne('')].copy()
    asset_scope = asset_scope.sort_values(['AssetID', 'DueDate'], ascending=[True, True], na_position='last')
    asset_scope = asset_scope.drop_duplicates(subset=['AssetID'], keep='first').reset_index(drop=True)
    if asset_scope.empty:
        return {
            'available': False,
            'asset_delivery_df': empty_asset_df,
            'product_capacity_df': empty_product_df,
            'dependency_df': empty_dependency_df,
            'kpis_df': empty_kpis,
            'notes': empty_notes,
        }

    asset_scope['Status Portfolio'] = asset_scope['Status'].fillna('').astype(str).str.strip()
    asset_scope['DependenciesPortfolioRaw'] = asset_scope['IssueLinkKeys'].fillna('').astype(str)

    def _split_link_keys(value):
        text = str(value or '').strip()
        if not text:
            return []
        out = []
        for token in re.split(r'[,\n;]+', text):
            cleaned = str(token or '').strip().upper()
            if cleaned and cleaned not in out:
                out.append(cleaned)
        return out

    portfolio_lookup = _pm_build_portfolio_lookup(scope)
    asset_ids = set(asset_scope['AssetID'])
    downstream_frames = []
    pm_case_frames = []
    canonical_projects = sorted({
        _canonical_pm_product_key(project_key)
        for project_key in asset_scope['Projeto PM'].dropna().astype(str).tolist()
        if _canonical_pm_product_key(project_key)
    })

    for project_key in canonical_projects:
        ds = load_project_downstream_items_csv(project_key)
        if ds is None or ds.empty or 'ID' not in ds.columns:
            continue
        ds = ds.copy()
        ds['Issue Key'] = ds['ID'].astype(str).str.strip().str.upper()
        ds = ds[ds['Issue Key'].ne('')].copy()
        asset_map = _pm_build_downstream_asset_map(project_key, portfolio_lookup)
        if asset_map.empty:
            continue
        ds = ds.merge(asset_map[['Issue Key', 'AssetID', 'Fonte Vínculo']], on='Issue Key', how='left')
        ds = ds[ds['AssetID'].astype(str).isin(asset_ids)].copy()
        if ds.empty:
            continue
        stage_cols = _detect_stage_date_columns(ds)
        done_col = get_downstream_done_stage_column(stage_cols)
        ready_prod_col = next((col for col in stage_cols if normalize_text(col) == 'ready for production'), None)
        ds['CreatedDate'] = pd.to_datetime(ds.get('Created'), errors='coerce')
        ds['StartDate'] = pd.to_datetime(ds.get('Start date'), errors='coerce')
        ds['DoneDate'] = pd.to_datetime(ds.get(done_col), dayfirst=True, errors='coerce') if done_col else pd.NaT
        ds['ReadyProdDate'] = pd.to_datetime(ds.get(ready_prod_col), dayfirst=True, errors='coerce') if ready_prod_col else pd.NaT
        ds['BlockedFlag'] = _coerce_bool_flag(ds.get('Blocked', pd.Series(False, index=ds.index)))
        ds['BlockedDaysNum'] = pd.to_numeric(ds.get('Blocked Days'), errors='coerce').fillna(0.0)
        if 'IssueLinkKeys' not in ds.columns:
            ds['IssueLinkKeys'] = ''
        ds['DependencyKeys'] = ds['IssueLinkKeys'].apply(_split_link_keys)
        ds['DependenciesCount'] = ds['DependencyKeys'].apply(len)
        ds['Projeto PM'] = project_key
        ds['Produto'] = _pm_product_label(project_key)
        downstream_frames.append(ds[[
            'Issue Key', 'AssetID', 'Projeto PM', 'Produto', 'CreatedDate', 'StartDate', 'DoneDate',
            'ReadyProdDate', 'BlockedFlag', 'BlockedDaysNum', 'DependencyKeys', 'DependenciesCount'
        ]].copy())

        pm_cases = load_project_pm_case_df(project_key)
        if pm_cases is not None and not pm_cases.empty and 'Issue Key' in pm_cases.columns:
            pm_cases = pm_cases.copy()
            pm_cases['Issue Key'] = pm_cases['Issue Key'].astype(str).str.strip().str.upper()
            pm_cases = pm_cases[pm_cases['Issue Key'].ne('')].copy()
            pm_cases = pm_cases.merge(asset_map[['Issue Key', 'AssetID']], on='Issue Key', how='left')
            pm_cases = pm_cases[pm_cases['AssetID'].astype(str).isin(asset_ids)].copy()
            if not pm_cases.empty:
                pm_cases['Done Final Date'] = pd.to_datetime(pm_cases.get('Done Final Date'), errors='coerce')
                for col in ['Lead Time Fluxo (dias)', 'Cycle Time Dev Medio (dias)', 'Retornos para Desenvolvimento', 'Rework Score']:
                    if col in pm_cases.columns:
                        pm_cases[col] = pd.to_numeric(pm_cases[col], errors='coerce')
                pm_cases['Projeto PM'] = project_key
                pm_cases['Produto'] = _pm_product_label(project_key)
                pm_case_frames.append(pm_cases[[
                    'Issue Key', 'AssetID', 'Projeto PM', 'Produto', 'Done Final Date',
                    'Lead Time Fluxo (dias)', 'Cycle Time Dev Medio (dias)', 'Retornos para Desenvolvimento', 'Rework Score'
                ]].copy())

    downstream_all = pd.concat(downstream_frames, ignore_index=True) if downstream_frames else pd.DataFrame()
    pm_cases_all = pd.concat(pm_case_frames, ignore_index=True) if pm_case_frames else pd.DataFrame()

    known_portfolio_open = {
        str(row['AssetID']).strip().upper(): normalize_text(row.get('Status Portfolio', '')) not in {'done', 'concluido', 'concluida', 'closed', 'resolved', 'cancelado', 'cancelled'}
        for _, row in asset_scope[['AssetID', 'Status Portfolio']].drop_duplicates(subset=['AssetID']).iterrows()
    }
    known_downstream_done = {}
    if not downstream_all.empty:
        done_by_issue = downstream_all.groupby('Issue Key', dropna=False)['DoneDate'].max()
        for issue_key, done_date in done_by_issue.items():
            known_downstream_done[str(issue_key).strip().upper()] = pd.notna(done_date)

    def _count_open_dependencies(key_series):
        keys = []
        for value in key_series:
            for key in value if isinstance(value, list) else []:
                if key and key not in keys:
                    keys.append(key)
        total = len(keys)
        open_known = 0
        external = 0
        for key in keys:
            if key in known_portfolio_open:
                if known_portfolio_open[key]:
                    open_known += 1
            elif key in known_downstream_done:
                if not known_downstream_done[key]:
                    open_known += 1
            else:
                external += 1
        return pd.Series({'DependenciesTotal': total, 'DependenciesAbertasConhecidas': open_known, 'DependenciesExternas': external})

    if not downstream_all.empty:
        ds_dependency_agg = (
            downstream_all.groupby('AssetID', dropna=False)['DependencyKeys']
            .apply(_count_open_dependencies)
            .reset_index()
        )
        if isinstance(ds_dependency_agg.columns, pd.MultiIndex):
            ds_dependency_agg.columns = ['AssetID', 'Metric', 'Value']
            ds_dependency_agg = ds_dependency_agg.pivot(index='AssetID', columns='Metric', values='Value').reset_index()
    else:
        ds_dependency_agg = pd.DataFrame(columns=['AssetID', 'DependenciesTotal', 'DependenciesAbertasConhecidas', 'DependenciesExternas'])

    portfolio_dependency_df = asset_scope[['AssetID', 'DependenciesPortfolioRaw']].copy()
    portfolio_dependency_df['DependencyKeysPortfolio'] = portfolio_dependency_df['DependenciesPortfolioRaw'].apply(_split_link_keys)
    portfolio_dependency_agg = (
        portfolio_dependency_df.groupby('AssetID', dropna=False)['DependencyKeysPortfolio']
        .apply(_count_open_dependencies)
        .reset_index()
    )
    if isinstance(portfolio_dependency_agg.columns, pd.MultiIndex):
        portfolio_dependency_agg.columns = ['AssetID', 'Metric', 'Value']
        portfolio_dependency_agg = portfolio_dependency_agg.pivot(index='AssetID', columns='Metric', values='Value').reset_index()
    for df_dep in [ds_dependency_agg, portfolio_dependency_agg]:
        for col in ['DependenciesTotal', 'DependenciesAbertasConhecidas', 'DependenciesExternas']:
            if col not in df_dep.columns:
                df_dep[col] = 0

    if not downstream_all.empty:
        ds_agg = (
            downstream_all.groupby('AssetID', dropna=False)
            .agg(
                **{
                    'Projeto PM': ('Projeto PM', 'first'),
                    'Produto': ('Produto', 'first'),
                    'ItensDownstream': ('Issue Key', 'nunique'),
                    'ItensDone': ('DoneDate', lambda s: int(s.notna().sum())),
                    'ItensReadyProd': ('ReadyProdDate', lambda s: int(s.notna().sum())),
                    'DownstreamCreatedMin': ('CreatedDate', 'min'),
                    'DownstreamStartMin': ('StartDate', 'min'),
                    'DownstreamDoneMax': ('DoneDate', 'max'),
                    'DownstreamReadyProdMax': ('ReadyProdDate', 'max'),
                    'IssuesBlocked': ('BlockedFlag', 'sum'),
                    'BlockedDaysTotal': ('BlockedDaysNum', 'sum'),
                }
            )
            .reset_index()
        )
        ds_agg['IssuesBlocked'] = pd.to_numeric(ds_agg['IssuesBlocked'], errors='coerce').fillna(0).astype(int)
    else:
        ds_agg = pd.DataFrame(columns=[
            'AssetID', 'Projeto PM', 'Produto', 'ItensDownstream', 'ItensDone', 'ItensReadyProd',
            'DownstreamCreatedMin', 'DownstreamStartMin', 'DownstreamDoneMax', 'DownstreamReadyProdMax',
            'IssuesBlocked', 'BlockedDaysTotal'
        ])

    if not pm_cases_all.empty:
        pm_agg = (
            pm_cases_all.groupby('AssetID', dropna=False)
            .agg(
                **{
                    'CasosPM': ('Issue Key', 'nunique'),
                    'PMDoneMax': ('Done Final Date', 'max'),
                    'Lead Time Fluxo Médio (dias)': ('Lead Time Fluxo (dias)', 'mean'),
                    'Lead Time Fluxo P85 (dias)': ('Lead Time Fluxo (dias)', lambda s: exact_empirical_percentile(pd.Series(s).dropna(), 0.85) if pd.Series(s).dropna().shape[0] else np.nan),
                    'Cycle Time Dev Médio (dias)': ('Cycle Time Dev Medio (dias)', 'mean'),
                    'Retornos QA->Dev': ('Retornos para Desenvolvimento', 'sum'),
                    'Rework Score Médio': ('Rework Score', 'mean'),
                }
            )
            .reset_index()
        )
    else:
        pm_agg = pd.DataFrame(columns=[
            'AssetID', 'CasosPM', 'PMDoneMax', 'Lead Time Fluxo Médio (dias)', 'Lead Time Fluxo P85 (dias)',
            'Cycle Time Dev Médio (dias)', 'Retornos QA->Dev', 'Rework Score Médio'
        ])

    cost_assets = pd.DataFrame()
    if isinstance(generated_financials, dict):
        cost_assets = generated_financials.get('project_costs_df', pd.DataFrame()).copy()
    if cost_assets is not None and not cost_assets.empty and 'AssetID' in cost_assets.columns:
        cost_assets['AssetID'] = cost_assets['AssetID'].astype(str).str.strip().str.upper()
        for col in ['Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Horas PM Elegíveis', 'Custo PM Estimado']:
            if col not in cost_assets.columns:
                cost_assets[col] = np.nan
        cost_assets = cost_assets.groupby('AssetID', dropna=False).agg(
            **{
                'Horas Reais Apontadas': ('Horas Reais Apontadas', 'sum'),
                'Custo Real Apontado (R$)': ('Custo Real Apontado (R$)', 'sum'),
                'Horas PM Elegíveis': ('Horas PM Elegíveis', 'sum'),
                'Custo PM Estimado': ('Custo PM Estimado', 'sum'),
            }
        ).reset_index()
    else:
        cost_assets = pd.DataFrame(columns=['AssetID', 'Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Horas PM Elegíveis', 'Custo PM Estimado'])

    asset_delivery_cols = [
        'AssetID', 'Projeto PM', 'Produto', 'Tipo', 'TeamPortfolio', 'Titulo', 'Status Portfolio', 'DueDate', 'Link'
    ]
    if 'ResolvedAt' in asset_scope.columns:
        asset_delivery_cols.append('ResolvedAt')
    if 'StatusChangedAt' in asset_scope.columns:
        asset_delivery_cols.append('StatusChangedAt')
    asset_delivery_df = asset_scope[asset_delivery_cols].copy().rename(columns={'TeamPortfolio': 'Team'})
    merge_frames = [ds_agg.copy(), pm_agg.copy(), cost_assets.copy()]
    if merge_frames[0] is not None:
        merge_frames[0] = merge_frames[0].drop(columns=[col for col in ['Projeto PM', 'Produto'] if col in merge_frames[0].columns])
    for frame in merge_frames:
        asset_delivery_df = asset_delivery_df.merge(frame, on='AssetID', how='left')
    asset_delivery_df = asset_delivery_df.merge(
        ds_dependency_agg[['AssetID', 'DependenciesTotal', 'DependenciesAbertasConhecidas', 'DependenciesExternas']],
        on='AssetID', how='left'
    )
    if not portfolio_dependency_agg.empty:
        asset_delivery_df = asset_delivery_df.merge(
            portfolio_dependency_agg[['AssetID', 'DependenciesTotal', 'DependenciesAbertasConhecidas', 'DependenciesExternas']].rename(columns={
                'DependenciesTotal': 'DependenciesTotalPortfolio',
                'DependenciesAbertasConhecidas': 'DependenciesAbertasConhecidasPortfolio',
                'DependenciesExternas': 'DependenciesExternasPortfolio',
            }),
            on='AssetID', how='left'
        )
        for target, source in [
            ('DependenciesTotal', 'DependenciesTotalPortfolio'),
            ('DependenciesAbertasConhecidas', 'DependenciesAbertasConhecidasPortfolio'),
            ('DependenciesExternas', 'DependenciesExternasPortfolio'),
        ]:
            asset_delivery_df[target] = (
                pd.to_numeric(asset_delivery_df.get(target), errors='coerce').fillna(0)
                + pd.to_numeric(asset_delivery_df.get(source), errors='coerce').fillna(0)
            )
    asset_delivery_df = asset_delivery_df.drop_duplicates(subset=['AssetID'], keep='first').reset_index(drop=True)
    for col in [
        'ItensDownstream', 'ItensDone', 'ItensReadyProd', 'CasosPM', 'IssuesBlocked',
        'DependenciesTotal', 'DependenciesAbertasConhecidas', 'DependenciesExternas', 'Retornos QA->Dev'
    ]:
        asset_delivery_df[col] = pd.to_numeric(asset_delivery_df.get(col), errors='coerce').fillna(0).astype(int)
    for col in [
        'Lead Time Fluxo Médio (dias)', 'Lead Time Fluxo P85 (dias)', 'Cycle Time Dev Médio (dias)',
        'Rework Score Médio', 'BlockedDaysTotal', 'Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Horas PM Elegíveis', 'Custo PM Estimado'
    ]:
        asset_delivery_df[col] = pd.to_numeric(asset_delivery_df.get(col), errors='coerce')

    asset_delivery_df['DataEntregaReal'] = pd.to_datetime(asset_delivery_df.get('DownstreamReadyProdMax'), errors='coerce')
    asset_delivery_df['DataEntregaReal'] = asset_delivery_df['DataEntregaReal'].combine_first(pd.to_datetime(asset_delivery_df.get('DownstreamDoneMax'), errors='coerce'))
    asset_delivery_df['DataEntregaReal'] = asset_delivery_df['DataEntregaReal'].combine_first(pd.to_datetime(asset_delivery_df.get('PMDoneMax'), errors='coerce'))
    
    portfolio_done_mask = asset_delivery_df['Status Portfolio'].fillna('').astype(str).str.lower().isin({'done', 'concluido', 'concluído', 'closed', 'resolved'})
    if 'ResolvedAt' in asset_delivery_df.columns:
        asset_delivery_df.loc[portfolio_done_mask, 'DataEntregaReal'] = asset_delivery_df.loc[portfolio_done_mask, 'DataEntregaReal'].combine_first(pd.to_datetime(asset_delivery_df.loc[portfolio_done_mask, 'ResolvedAt'], errors='coerce', utc=True).dt.tz_localize(None))
    if 'StatusChangedAt' in asset_delivery_df.columns:
        asset_delivery_df.loc[portfolio_done_mask, 'DataEntregaReal'] = asset_delivery_df.loc[portfolio_done_mask, 'DataEntregaReal'].combine_first(pd.to_datetime(asset_delivery_df.loc[portfolio_done_mask, 'StatusChangedAt'], errors='coerce', utc=True).dt.tz_localize(None))

    today_ts = pd.Timestamp.now().normalize()
    asset_delivery_df['DeltaPrazoDias'] = np.where(
        asset_delivery_df['DueDate'].notna() & asset_delivery_df['DataEntregaReal'].notna(),
        (asset_delivery_df['DataEntregaReal'].dt.normalize() - asset_delivery_df['DueDate'].dt.normalize()).dt.days,
        np.where(
            asset_delivery_df['DueDate'].notna() & asset_delivery_df['DataEntregaReal'].isna(),
            (today_ts - asset_delivery_df['DueDate'].dt.normalize()).dt.days,
            np.nan,
        )
    )

    def _prazo_status(row):
        due = pd.to_datetime(row.get('DueDate'), errors='coerce')
        actual = pd.to_datetime(row.get('DataEntregaReal'), errors='coerce')
        if pd.isna(due):
            return 'Sem target'
        if pd.notna(actual):
            return 'No prazo' if actual.normalize() <= due.normalize() else 'Atrasado'
        if due.normalize() < today_ts:
            return 'Vencido sem entrega'
        if due.normalize() <= (today_ts + pd.Timedelta(days=14)):
            return 'Risco <=14d'
        return 'Em acompanhamento'

    def _value_realization_proxy(row):
        actual = pd.to_datetime(row.get('DataEntregaReal'), errors='coerce')
        real_cost = pd.to_numeric(row.get('Custo Real Apontado (R$)'), errors='coerce')
        real_hours = pd.to_numeric(row.get('Horas Reais Apontadas'), errors='coerce')
        if pd.notna(actual) and ((pd.notna(real_cost) and real_cost > 0) or (pd.notna(real_hours) and real_hours > 0)):
            return 'Valor realizado'
        if pd.notna(actual):
            return 'Entrega com evidência'
        if int(row.get('CasosPM', 0) or 0) > 0 or int(row.get('ItensDownstream', 0) or 0) > 0:
            return 'Execução em andamento'
        return 'Sem evidência'

    asset_delivery_df['PrazoRealStatus'] = asset_delivery_df.apply(_prazo_status, axis=1)
    asset_delivery_df['ProxyRealizacaoValor'] = asset_delivery_df.apply(_value_realization_proxy, axis=1)
    asset_delivery_df = asset_delivery_df.sort_values(
        ['PrazoRealStatus', 'DependenciesAbertasConhecidas', 'ItensDone', 'AssetID'],
        ascending=[True, False, False, True],
        ignore_index=True,
    )

    period_days = max(1, int((pd.to_datetime(end_ts) - pd.to_datetime(start_ts)).days) + 1)
    period_months = max(1.0 / 30.0, float(period_days) / 30.4375)
    product_capacity_df = pd.DataFrame()
    cost_model = generated_financials.get('cost_model', {}) if isinstance(generated_financials, dict) else {}
    product_rates_df = cost_model.get('product_rates_df', pd.DataFrame()).copy() if isinstance(cost_model, dict) else pd.DataFrame()
    pm_product_summary = pm_portfolio_data.get('product_summary', pd.DataFrame()).copy() if isinstance(pm_portfolio_data, dict) else pd.DataFrame()
    if product_rates_df is not None and not product_rates_df.empty:
        product_capacity_df = product_rates_df[['Projeto PM', 'Produto', 'Capacidade Mensal Produto (h)']].copy()
        product_capacity_df['Capacidade Período (h)'] = pd.to_numeric(product_capacity_df['Capacidade Mensal Produto (h)'], errors='coerce').fillna(0.0) * period_months
        if pm_product_summary is not None and not pm_product_summary.empty:
            for col in ['Horas PM Elegíveis', 'Horas Reais Apontadas']:
                if col not in pm_product_summary.columns:
                    pm_product_summary[col] = np.nan
            product_capacity_df = product_capacity_df.merge(
                pm_product_summary[['Projeto PM', 'Produto', 'Horas PM Elegíveis', 'Horas Reais Apontadas']],
                on=['Projeto PM', 'Produto'],
                how='left',
            )
        product_capacity_df['Horas Consumidas'] = pd.to_numeric(product_capacity_df.get('Horas Reais Apontadas'), errors='coerce')
        missing_consumed = product_capacity_df['Horas Consumidas'].isna() | (product_capacity_df['Horas Consumidas'] <= 0)
        product_capacity_df.loc[missing_consumed, 'Horas Consumidas'] = pd.to_numeric(
            product_capacity_df.loc[missing_consumed, 'Horas PM Elegíveis'], errors='coerce'
        ).fillna(0.0)
        asset_product_agg = (
            asset_delivery_df.groupby(['Projeto PM', 'Produto'], dropna=False)
            .agg(
                **{
                    'Assets Portfolio': ('AssetID', 'nunique'),
                    'Assets com Evidência': ('ItensDownstream', lambda s: int((pd.to_numeric(s, errors='coerce').fillna(0) > 0).sum())),
                    'Assets Entregues': ('DataEntregaReal', lambda s: int(pd.to_datetime(s, errors='coerce').notna().sum())),
                    'Assets Valor Realizado': ('ProxyRealizacaoValor', lambda s: int(pd.Series(s).eq('Valor realizado').sum())),
                }
            )
            .reset_index()
        )
        product_capacity_df = product_capacity_df.merge(asset_product_agg, on=['Projeto PM', 'Produto'], how='left')
        for col in ['Assets Portfolio', 'Assets com Evidência', 'Assets Entregues', 'Assets Valor Realizado']:
            product_capacity_df[col] = pd.to_numeric(product_capacity_df.get(col), errors='coerce').fillna(0).astype(int)
        product_capacity_df['% Capacidade Consumida'] = np.where(
            pd.to_numeric(product_capacity_df['Capacidade Período (h)'], errors='coerce').fillna(0) > 0,
            pd.to_numeric(product_capacity_df['Horas Consumidas'], errors='coerce').fillna(0)
            / pd.to_numeric(product_capacity_df['Capacidade Período (h)'], errors='coerce').fillna(0),
            np.nan,
        )
        product_capacity_df['% Valor Realizado (proxy)'] = np.where(
            product_capacity_df['Assets Portfolio'] > 0,
            product_capacity_df['Assets Valor Realizado'] / product_capacity_df['Assets Portfolio'],
            np.nan,
        )
        product_capacity_df = product_capacity_df.sort_values('% Capacidade Consumida', ascending=False, na_position='last', ignore_index=True)

    dependency_df = asset_delivery_df[
        (asset_delivery_df['DependenciesTotal'] > 0) | (asset_delivery_df['DependenciesAbertasConhecidas'] > 0)
    ][['AssetID', 'Produto', 'Titulo', 'DependenciesTotal', 'DependenciesAbertasConhecidas', 'DependenciesExternas', 'PrazoRealStatus', 'Link']].copy()
    dependency_df = dependency_df.sort_values(
        ['DependenciesAbertasConhecidas', 'DependenciesTotal', 'AssetID'],
        ascending=[False, False, True],
        ignore_index=True,
    )

    assets_total = int(asset_delivery_df['AssetID'].nunique())
    assets_with_evidence = int((asset_delivery_df['ItensDownstream'] > 0).sum())
    assets_delivered = int(asset_delivery_df['DataEntregaReal'].notna().sum())
    assets_value_realized = int((asset_delivery_df['ProxyRealizacaoValor'] == 'Valor realizado').sum())
    assets_at_risk = int(asset_delivery_df['PrazoRealStatus'].isin(['Atrasado', 'Vencido sem entrega']).sum())
    open_dependencies = int(pd.to_numeric(asset_delivery_df['DependenciesAbertasConhecidas'], errors='coerce').fillna(0).sum())
    capacity_pct = (
        float(pd.to_numeric(product_capacity_df.get('% Capacidade Consumida'), errors='coerce').dropna().mean())
        if product_capacity_df is not None and not product_capacity_df.empty else np.nan
    )
    kpis_df = pd.DataFrame([
        {'Indicador': 'Ativos no portfólio', 'Valor': assets_total, 'Detalhe': 'Épicos e features no escopo atual.'},
        {'Indicador': 'Ativos com evidência downstream', 'Valor': assets_with_evidence, 'Detalhe': 'Ao menos um item tático mapeado no downstream.'},
        {'Indicador': 'Ativos com entrega factual', 'Valor': assets_delivered, 'Detalhe': 'Ready for production, done downstream ou done final no process mining.'},
        {'Indicador': 'Ativos com valor realizado (proxy)', 'Valor': assets_value_realized, 'Detalhe': 'Entrega factual com horas/custo reais apontados.'},
        {'Indicador': 'Ativos em risco de prazo', 'Valor': assets_at_risk, 'Detalhe': 'Atrasados ou vencidos sem entrega factual.'},
        {'Indicador': 'Dependências abertas conhecidas', 'Valor': open_dependencies, 'Detalhe': 'Links explícitos ainda abertos no portfólio/downstream conhecido.'},
        {'Indicador': '% capacidade consumida', 'Valor': round(capacity_pct * 100.0, 1) if pd.notna(capacity_pct) else np.nan, 'Detalhe': 'Média por produto no período atual.'},
    ])
    notes = [
        'Prazo real usa a melhor evidência disponível entre ready for production, conclusão downstream e done final do process mining.',
        'Capacidade é um proxy factual por produto: horas consumidas no período versus capacidade heurística carregada do modelo financeiro.',
        'Dependências consideram links explícitos do snapshot de portfólio e do downstream; vínculos não materializados nas bases continuam fora da leitura.',
        'Realização de valor é um proxy factual: entrega com evidência operacional e apontamento real de horas/custo.',
    ]
    return {
        'available': True,
        'asset_delivery_df': asset_delivery_df,
        'product_capacity_df': product_capacity_df,
        'dependency_df': dependency_df,
        'kpis_df': kpis_df,
        'notes': notes,
    }


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


def _pm_is_dev_status(value) -> bool:
    return normalize_text(value) in _PM_DEV_STATUS_NAMES


def _pm_is_qa_status(value) -> bool:
    norm = normalize_text(value)
    return any(token in norm for token in _PM_QA_STATUS_HINTS)


def _pm_summarize_dev_flow_from_events(events_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    item_cols = [
        'Issue Key', 'Projeto', 'Tipo de Problema',
        'Primeira Entrada Dev', 'Ultima Entrada Dev', 'Segmentos Dev',
        'Cycle Time Dev (dias)', 'Retornos QA->Dev',
        'Tempo Retorno QA->Dev Total (dias)', 'Tempo Retorno QA->Dev Medio (dias)',
        'Tempo Retorno QA->Dev Mediano (dias)',
    ]
    return_cols = [
        'Issue Key', 'Projeto', 'Tipo de Problema', 'Retorno Seq',
        'Dev Owner Antes QA', 'Entrada QA/Teste Em', 'Retorno Dev Em',
        'Status Entrada QA/Teste', 'Status Retorno Dev', 'Tempo Retorno QA->Dev (dias)',
    ]
    if events_df is None or events_df.empty or 'Issue Key' not in events_df.columns or 'History Created' not in events_df.columns:
        return pd.DataFrame(columns=item_cols), pd.DataFrame(columns=return_cols)

    events = events_df.copy()
    for col in ['Projeto', 'Tipo de Problema', 'Author', 'From Status', 'To Status']:
        if col not in events.columns:
            events[col] = ''
        events[col] = events[col].fillna('').astype(str).str.strip()
    events['Issue Key'] = events['Issue Key'].fillna('').astype(str).str.strip()
    events['History Created'] = pd.to_datetime(events['History Created'], errors='coerce')
    if 'TempoStatusDias' not in events.columns:
        events['TempoStatusDias'] = np.nan
    events['TempoStatusDias'] = pd.to_numeric(events['TempoStatusDias'], errors='coerce')
    events['To Status Norm'] = events.get('To Status Norm', events.get('To Status', '')).apply(normalize_text)
    events['From Status Norm'] = events.get('From Status Norm', events.get('From Status', '')).apply(normalize_text)
    events = events[events['Issue Key'].ne('') & events['History Created'].notna()].copy()
    if events.empty:
        return pd.DataFrame(columns=item_cols), pd.DataFrame(columns=return_cols)

    sort_cols = ['Issue Key', 'History Created']
    if 'Event Seq' in events.columns:
        sort_cols.append('Event Seq')
    events = events.sort_values(sort_cols).reset_index(drop=True)

    item_rows = []
    return_rows = []

    for issue_key, group in events.groupby('Issue Key', sort=False):
        g = group.sort_values(sort_cols[1:]).reset_index(drop=True)
        projeto = str(g['Projeto'].iloc[0]) if 'Projeto' in g.columns else ''
        tipo = str(g['Tipo de Problema'].iloc[0]) if 'Tipo de Problema' in g.columns else ''
        dev_entries = []
        dev_durations = []
        return_durations = []
        last_dev_context = None
        open_qa_cycle = None

        for _, row in g.iterrows():
            ts = row['History Created']
            to_status = str(row.get('To Status') or '')
            to_status_norm = str(row.get('To Status Norm') or '')
            author = str(row.get('Author') or '') or 'Sem Autor'

            if _pm_is_dev_status(to_status_norm):
                dev_entries.append(ts)
                duration = row.get('TempoStatusDias')
                if pd.notna(duration) and float(duration) >= 0:
                    dev_durations.append(float(duration))
                if open_qa_cycle is not None:
                    qa_enter_ts = open_qa_cycle.get('qa_enter_ts')
                    if pd.notna(qa_enter_ts) and ts >= qa_enter_ts:
                        roundtrip_days = max((ts - qa_enter_ts).total_seconds() / 86400.0, 0.0)
                        return_durations.append(roundtrip_days)
                        return_rows.append({
                            'Issue Key': issue_key,
                            'Projeto': projeto,
                            'Tipo de Problema': tipo,
                            'Retorno Seq': len(return_durations),
                            'Dev Owner Antes QA': str(open_qa_cycle.get('dev_owner') or 'Sem Autor'),
                            'Entrada QA/Teste Em': qa_enter_ts,
                            'Retorno Dev Em': ts,
                            'Status Entrada QA/Teste': str(open_qa_cycle.get('qa_status') or ''),
                            'Status Retorno Dev': to_status,
                            'Tempo Retorno QA->Dev (dias)': round(float(roundtrip_days), 4),
                        })
                    open_qa_cycle = None
                last_dev_context = {'author': author, 'timestamp': ts}
                continue

            if _pm_is_qa_status(to_status_norm):
                if open_qa_cycle is None and last_dev_context is not None:
                    last_dev_ts = last_dev_context.get('timestamp')
                    if pd.notna(last_dev_ts) and ts >= last_dev_ts:
                        open_qa_cycle = {
                            'qa_enter_ts': ts,
                            'qa_status': to_status,
                            'dev_owner': str(last_dev_context.get('author') or 'Sem Autor'),
                        }
                continue

        if not dev_entries and not return_durations:
            continue

        total_dev_cycle = float(sum(dev_durations)) if dev_durations else 0.0
        total_return = float(sum(return_durations)) if return_durations else 0.0
        item_rows.append({
            'Issue Key': issue_key,
            'Projeto': projeto,
            'Tipo de Problema': tipo,
            'Primeira Entrada Dev': dev_entries[0] if dev_entries else pd.NaT,
            'Ultima Entrada Dev': dev_entries[-1] if dev_entries else pd.NaT,
            'Segmentos Dev': int(len(dev_entries)),
            'Cycle Time Dev (dias)': round(total_dev_cycle, 4),
            'Retornos QA->Dev': int(len(return_durations)),
            'Tempo Retorno QA->Dev Total (dias)': round(total_return, 4),
            'Tempo Retorno QA->Dev Medio (dias)': round(float(np.mean(return_durations)), 4) if return_durations else 0.0,
            'Tempo Retorno QA->Dev Mediano (dias)': round(float(np.median(return_durations)), 4) if return_durations else 0.0,
        })

    return pd.DataFrame(item_rows, columns=item_cols), pd.DataFrame(return_rows, columns=return_cols)


def _pm_extract_dev_flow_datasets(
    item_df: pd.DataFrame | None,
    return_df: pd.DataFrame | None,
    events_df: pd.DataFrame | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    has_item_summary = item_df is not None and not item_df.empty and 'Cycle Time Dev (dias)' in item_df.columns
    has_return_summary = return_df is not None and not return_df.empty and 'Tempo Retorno QA->Dev (dias)' in return_df.columns
    if has_item_summary:
        return item_df.copy(), return_df.copy() if has_return_summary else pd.DataFrame()
    return _pm_summarize_dev_flow_from_events(events_df if events_df is not None else pd.DataFrame())


def compute_pm_dev_metrics(
    case_df: pd.DataFrame,
    start_ts,
    end_ts,
    alias_index: dict | None = None,
    item_person_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Calcula métricas de process mining por desenvolvedor a partir de ConformidadeCasos.

    Retorna DataFrame com colunas:
        Pessoa, Conformance Quality, Rework Rate PM (%), QA Return Rate (%)
    """
    if case_df is None or case_df.empty:
        return pd.DataFrame()
    if 'Done Final Author' not in case_df.columns or 'Done Final Date' not in case_df.columns:
        return pd.DataFrame()

    df = case_df.copy()
    df['Done Final Date'] = pd.to_datetime(df['Done Final Date'], errors='coerce')
    start_ts = pd.to_datetime(start_ts)
    end_ts = pd.to_datetime(end_ts)

    # Filtra por período (itens concluídos no janela)
    mask = df['Done Final Date'].notna() & (df['Done Final Date'] >= start_ts) & (df['Done Final Date'] < end_ts)
    df = df[mask].copy()
    if item_person_map:
        allowed_keys = {str(k).strip() for k in item_person_map.keys() if str(k).strip()}
        df['Issue Key'] = df.get('Issue Key', pd.Series('', index=df.index)).astype(str).str.strip()
        df = df[df['Issue Key'].isin(allowed_keys)].copy()
    if df.empty:
        return pd.DataFrame()

    # Normaliza autor
    if alias_index is None:
        alias_index = _load_person_alias_index()
    if item_person_map:
        df['Pessoa'] = df['Issue Key'].map(item_person_map).fillna('')
    else:
        df['Pessoa'] = df['Done Final Author'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
    df = df[df['Pessoa'].astype(str).str.strip().ne('') & df['Pessoa'].str.lower().ne('sem autor')]

    for col in ['Conformance Score', 'Rework Score', 'QA Returns']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    rows = []
    for pessoa, g in df.groupby('Pessoa'):
        total = len(g)
        conform_avg = g['Conformance Score'].mean() * 100 if 'Conformance Score' in g.columns else 0.0
        rework_pct = (g['Rework Score'] > 0).sum() / total * 100 if 'Rework Score' in g.columns else 0.0
        rework_total = float(g['Rework Score'].sum()) if 'Rework Score' in g.columns else 0.0
        rework_medio = round(rework_total / total, 2) if total > 0 else 0.0
        qa_pct = (g['QA Returns'] > 0).sum() / total * 100 if 'QA Returns' in g.columns else 0.0
        variant_len_avg = g['Variant'].apply(lambda v: len(str(v).split(' > ')) if pd.notna(v) else 0).mean() if 'Variant' in g.columns else 0.0
        rows.append({
            'Pessoa': pessoa,
            'Conformance Quality (%)': round(float(conform_avg), 1),
            'Rework Rate PM (%)': round(float(rework_pct), 1),
            'Rework Score Total': round(rework_total, 2),
            'Rework Score Médio': rework_medio,
            'QA Return Rate (%)': round(float(qa_pct), 1),
            'Complexidade Variante': round(float(variant_len_avg), 1),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def compute_pm_dev_flow_metrics(
    item_df: pd.DataFrame,
    return_df: pd.DataFrame,
    start_ts,
    end_ts,
    alias_index: dict | None = None,
    item_person_map: dict[str, str] | None = None,
    events_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Calcula retorno QA/teste -> desenvolvimento e cycle time em desenvolvimento por dev."""
    summary_df, returns_df = _pm_extract_dev_flow_datasets(item_df, return_df, events_df)
    if summary_df.empty or 'Issue Key' not in summary_df.columns:
        return pd.DataFrame()

    if alias_index is None:
        alias_index = _load_person_alias_index()

    summary_df = summary_df.copy()
    summary_df['Issue Key'] = summary_df['Issue Key'].astype(str).str.strip()
    if item_person_map:
        allowed_keys = {str(k).strip() for k in item_person_map.keys() if str(k).strip()}
        summary_df = summary_df[summary_df['Issue Key'].isin(allowed_keys)].copy()
        summary_df['Pessoa'] = summary_df['Issue Key'].map(item_person_map).fillna('')
    else:
        summary_df['Pessoa'] = ''
    summary_df = summary_df[
        summary_df['Pessoa'].astype(str).str.strip().ne('') &
        summary_df['Pessoa'].str.lower().ne('sem autor')
    ].copy()
    if summary_df.empty:
        return pd.DataFrame()

    returns_df = returns_df.copy()
    if not returns_df.empty and 'Issue Key' in returns_df.columns:
        returns_df['Issue Key'] = returns_df['Issue Key'].astype(str).str.strip()
        returns_df = returns_df[returns_df['Issue Key'].isin(set(summary_df['Issue Key']))].copy()
        item_people = summary_df[['Issue Key', 'Pessoa']].drop_duplicates(subset=['Issue Key'], keep='first')
        returns_df = returns_df.merge(item_people, on='Issue Key', how='left')
        returns_df = returns_df[returns_df['Pessoa'].astype(str).str.strip().ne('')].copy()

    rows = []
    for pessoa, group in summary_df.groupby('Pessoa', dropna=False):
        dev_cycle_by_item = pd.to_numeric(group.get('Cycle Time Dev (dias)'), errors='coerce').dropna()
        return_counts = pd.to_numeric(group.get('Retornos QA->Dev'), errors='coerce').fillna(0)
        cards_with_return = int((return_counts > 0).sum())
        total_items = int(group['Issue Key'].nunique())
        total_returns = int(return_counts.sum())
        if not returns_df.empty:
            qa_return_times = pd.to_numeric(
                returns_df.loc[returns_df['Pessoa'] == pessoa, 'Tempo Retorno QA->Dev (dias)'],
                errors='coerce',
            ).dropna()
        else:
            qa_return_times = pd.to_numeric(group.get('Tempo Retorno QA->Dev Mediano (dias)'), errors='coerce').dropna()

        rows.append({
            'Pessoa': pessoa,
            'Cycle Time Dev Mediano (dias)': round(float(dev_cycle_by_item.median()), 1) if not dev_cycle_by_item.empty else np.nan,
            'Cycle Time Dev Médio (dias)': round(float(dev_cycle_by_item.mean()), 1) if not dev_cycle_by_item.empty else np.nan,
            'Retornos QA->Dev': total_returns,
            'Cards com Retorno QA->Dev': cards_with_return,
            '% Cards com Retorno QA->Dev': round(cards_with_return / total_items * 100.0, 1) if total_items > 0 else np.nan,
            'Tempo Retorno QA->Dev Mediano (dias)': round(float(qa_return_times.median()), 1) if not qa_return_times.empty else np.nan,
            'Tempo Retorno QA->Dev Total (dias)': round(float(qa_return_times.sum()), 1) if not qa_return_times.empty else 0.0,
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def build_pm_dev_return_report(
    item_df: pd.DataFrame,
    return_df: pd.DataFrame,
    item_person_map: dict[str, str] | None = None,
    events_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    summary_df, returns_df = _pm_extract_dev_flow_datasets(item_df, return_df, events_df)
    if returns_df.empty or 'Issue Key' not in returns_df.columns:
        return pd.DataFrame()

    report = returns_df.copy()
    report['Issue Key'] = report['Issue Key'].astype(str).str.strip()
    if item_person_map:
        allowed_keys = {str(k).strip() for k in item_person_map.keys() if str(k).strip()}
        report = report[report['Issue Key'].isin(allowed_keys)].copy()
        report['Pessoa'] = report['Issue Key'].map(item_person_map).fillna('')
    else:
        report['Pessoa'] = report.get('Dev Owner Antes QA', pd.Series('', index=report.index)).fillna('').astype(str)
    report = report[report['Pessoa'].astype(str).str.strip().ne('')].copy()
    if report.empty:
        return pd.DataFrame()

    if not summary_df.empty and {'Issue Key', 'Cycle Time Dev (dias)', 'Retornos QA->Dev'}.issubset(summary_df.columns):
        summary_cols = summary_df[['Issue Key', 'Cycle Time Dev (dias)', 'Retornos QA->Dev']].drop_duplicates(subset=['Issue Key'], keep='first')
        report = report.merge(summary_cols, on='Issue Key', how='left')

    for col in ['Entrada QA/Teste Em', 'Retorno Dev Em']:
        if col in report.columns:
            report[col] = pd.to_datetime(report[col], errors='coerce')
    if 'Tempo Retorno QA->Dev (dias)' in report.columns:
        report['Tempo Retorno QA->Dev (dias)'] = pd.to_numeric(report['Tempo Retorno QA->Dev (dias)'], errors='coerce')

    preferred_cols = [
        'Pessoa', 'Issue Key', 'Projeto', 'Tipo de Problema', 'Retorno Seq',
        'Entrada QA/Teste Em', 'Retorno Dev Em',
        'Status Entrada QA/Teste', 'Status Retorno Dev',
        'Tempo Retorno QA->Dev (dias)', 'Cycle Time Dev (dias)', 'Retornos QA->Dev',
    ]
    preferred_cols = [c for c in preferred_cols if c in report.columns]
    return report[preferred_cols].sort_values(
        ['Tempo Retorno QA->Dev (dias)', 'Retorno Dev Em'],
        ascending=[False, False],
        na_position='last',
    ).reset_index(drop=True)


def compute_pipeline_success_rate(
    bb_projects: list,
    start_ts,
    end_ts,
    alias_index: dict | None = None,
) -> pd.DataFrame:
    """Calcula taxa de sucesso de pipeline por autor, cruzando pipelines com commits.

    Retorna DataFrame com colunas: Pessoa, Pipelines Total, Pipelines Sucesso, Pipeline Success Rate (%)
    """
    if alias_index is None:
        alias_index = _load_person_alias_index()
    start_ts = pd.to_datetime(start_ts)
    end_ts = pd.to_datetime(end_ts)

    all_pipelines = []
    all_commits = []
    for proj in bb_projects:
        logs = load_project_bitbucket_logs(proj)
        pip = logs.get('pipelines', pd.DataFrame())
        com = logs.get('commits', pd.DataFrame())
        if not pip.empty:
            all_pipelines.append(pip)
        if not com.empty:
            all_commits.append(com)

    if not all_pipelines or not all_commits:
        return pd.DataFrame()

    pipelines = pd.concat(all_pipelines, ignore_index=True).drop_duplicates(subset=['uuid'] if 'uuid' in all_pipelines[0].columns else None)
    commits = pd.concat(all_commits, ignore_index=True).drop_duplicates(subset=['hash'] if 'hash' in all_commits[0].columns else None)

    if 'commit_hash' not in pipelines.columns or 'hash' not in commits.columns or 'author' not in commits.columns:
        return pd.DataFrame()

    # Filtra pipelines pelo período
    if 'created_on' in pipelines.columns:
        pipelines['created_on'] = pd.to_datetime(pipelines['created_on'], errors='coerce')
        pipelines = pipelines[
            pipelines['created_on'].notna() &
            (pipelines['created_on'] >= start_ts) &
            (pipelines['created_on'] < end_ts)
        ]
    if pipelines.empty:
        return pd.DataFrame()

    # Join pipelines → commits para obter autor
    commits_slim = commits[['hash', 'author']].copy()
    commits_slim['hash'] = commits_slim['hash'].astype(str).str.strip()
    pipelines['commit_hash'] = pipelines['commit_hash'].astype(str).str.strip()
    merged = pipelines.merge(commits_slim, left_on='commit_hash', right_on='hash', how='left')
    merged = merged[merged['author'].notna() & (merged['author'].astype(str).str.strip() != '')]
    if merged.empty:
        return pd.DataFrame()

    merged['Pessoa'] = merged['author'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
    merged = merged[merged['Pessoa'].astype(str).str.strip().ne('')]

    state_col = 'state_norm' if 'state_norm' in merged.columns else 'state_result' if 'state_result' in merged.columns else None
    if not state_col:
        return pd.DataFrame()

    merged['_sucesso'] = merged[state_col].astype(str).str.strip().str.lower().isin({'successful', 'success', 'passed'})

    rows = []
    for pessoa, g in merged.groupby('Pessoa'):
        total = len(g)
        sucesso = int(g['_sucesso'].sum())
        rows.append({
            'Pessoa': pessoa,
            'Pipelines Total': total,
            'Pipelines Sucesso': sucesso,
            'Pipeline Success Rate (%)': round(sucesso / total * 100, 1) if total > 0 else 0.0,
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


_TERMINAL_STATUS_HINTS = {
    'done', 'concluido', 'concluído', 'cancelled', 'cancelado', 'closed',
    'fechado', 'rejected', 'won\'t do', 'wont do', 'backlog', 'to do',
}


def compute_pm_bottleneck_contribution(
    bb_projects: list,
    alias_index: dict | None = None,
) -> pd.DataFrame:
    """Calcula contribuição de horas em status de gargalo por desenvolvedor.

    Gargalo = statuses com Tempo Mediano > P75 de todos os statuses (excluindo terminais).
    Fonte: HorasPessoaStatus + TemposPorStatus dos Excels de process mining.

    Retorna DataFrame: Pessoa, HorasNoFluxo Total, Média H/Evento, Horas em Gargalo, % Horas em Gargalo
    """
    if alias_index is None:
        alias_index = _load_person_alias_index()

    all_horas: list[pd.DataFrame] = []
    all_tempos: list[pd.DataFrame] = []
    for proj in bb_projects:
        df_hs = load_project_pm_sheet(proj, 'HorasPessoaStatus')
        df_ts = load_project_pm_sheet(proj, 'TemposPorStatus')
        if not df_hs.empty:
            all_horas.append(df_hs)
        if not df_ts.empty:
            all_tempos.append(df_ts)

    if not all_horas:
        return pd.DataFrame()

    horas_df = pd.concat(all_horas, ignore_index=True)
    if 'Responsavel' not in horas_df.columns or 'HorasNoFluxo' not in horas_df.columns or 'Status' not in horas_df.columns:
        return pd.DataFrame()

    horas_df['HorasNoFluxo'] = pd.to_numeric(horas_df['HorasNoFluxo'], errors='coerce').fillna(0)
    if 'Eventos' in horas_df.columns:
        horas_df['Eventos'] = pd.to_numeric(horas_df['Eventos'], errors='coerce').fillna(0)
    else:
        horas_df['Eventos'] = 0
    horas_df['Pessoa'] = horas_df['Responsavel'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
    horas_df = horas_df[horas_df['Pessoa'].astype(str).str.strip().ne('')]
    if horas_df.empty:
        return pd.DataFrame()

    # Identifica gargalos: statuses com Tempo Mediano > P75 excluindo terminais
    gargalo_statuses: set[str] = set()
    if all_tempos:
        tempos_df = pd.concat(all_tempos, ignore_index=True)
        if 'Status' in tempos_df.columns and 'Tempo Mediano (dias)' in tempos_df.columns:
            tempos_df['Tempo Mediano (dias)'] = pd.to_numeric(tempos_df['Tempo Mediano (dias)'], errors='coerce').fillna(0)
            # Remove statuses terminais
            tempos_df['_status_norm'] = tempos_df['Status'].astype(str).str.lower().str.strip()
            tempos_df = tempos_df[~tempos_df['_status_norm'].apply(
                lambda s: any(hint in s for hint in _TERMINAL_STATUS_HINTS)
            )]
            if not tempos_df.empty:
                p75 = tempos_df['Tempo Mediano (dias)'].quantile(0.75)
                gargalo_statuses = set(tempos_df[tempos_df['Tempo Mediano (dias)'] >= p75]['Status'].astype(str))

    # Fallback: usa top 3 statuses por total de horas se não identificou gargalos
    if not gargalo_statuses:
        top_status = (
            horas_df.groupby('Status')['HorasNoFluxo'].sum()
            .nlargest(3).index.tolist()
        )
        gargalo_statuses = set(top_status)

    gargalo_label = ', '.join(sorted(gargalo_statuses)[:5])  # máx 5 nomes no label

    # Total de horas e eventos por pessoa
    total_horas = horas_df.groupby('Pessoa')['HorasNoFluxo'].sum()
    total_eventos = horas_df.groupby('Pessoa')['Eventos'].sum()
    # Horas em status gargalo por pessoa
    horas_gargalo = (
        horas_df[horas_df['Status'].isin(gargalo_statuses)]
        .groupby('Pessoa')['HorasNoFluxo'].sum()
    )

    rows = []
    for pessoa in total_horas.index:
        total = float(total_horas.get(pessoa, 0))
        eventos = float(total_eventos.get(pessoa, 0))
        gargalo = float(horas_gargalo.get(pessoa, 0))
        pct = round(gargalo / total * 100, 1) if total > 0 else 0.0
        media_h_evento = round(total / eventos, 2) if eventos > 0 else 0.0
        rows.append({
            'Pessoa': pessoa,
            'HorasNoFluxo Total': round(total, 1),
            'Média H/Evento': media_h_evento,
            'Horas em Gargalo': round(gargalo, 1),
            '% Horas em Gargalo': pct,
        })

    result = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not result.empty:
        result.attrs['gargalo_label'] = gargalo_label
    return result


def get_leadtime_stage_filter_columns(projeto):
    """
    Resolve stage columns/options for the Lead Time stage filter.
    Preference order:
    1) downstream item CSV (exact stage date columns)
    2) bottlenecks from model (`Fato_Gargalos`)
    3) bottlenecks CSV
    Returns: (stage_cols, source_tag)
    """
    items_df = load_project_downstream_items_csv(projeto)
    if not items_df.empty:
        bottlenecks_df = load_project_bottlenecks_from_model(projeto)
        if bottlenecks_df.empty:
            bottlenecks_df = load_project_bottlenecks_from_csv(projeto)
        stage_cols = _detect_stage_date_columns(items_df, bottlenecks_df=bottlenecks_df)
        if not stage_cols:
            stage_cols = get_downstream_workflow_stage_columns(items_df)
        if stage_cols:
            return stage_cols, 'downstream'

    for loader in (load_project_bottlenecks_from_model, load_project_bottlenecks_from_csv):
        bdf = loader(projeto)
        if bdf is None or bdf.empty or 'Etapa' not in bdf.columns:
            continue
        seen = set()
        stage_cols = []
        for raw in bdf['Etapa'].astype(str).tolist():
            stage = str(raw).strip()
            if not stage or stage in seen:
                continue
            seen.add(stage)
            stage_cols.append(stage)
        if stage_cols:
            return stage_cols, 'bottlenecks'

    return [], 'none'


def build_custom_lead_time_by_selected_stages(projeto, selected_start_stages):
    """
    Compute factual lead time from selected commitment stages to finalization (Done)
    using the project's downstream CSV.
    Returns dataframe with columns: ItemID, LeadStart_Custom, LeadTime_Custom_Dias.
    """
    items_df = load_project_downstream_items_csv(projeto)
    if items_df.empty or 'ID' not in items_df.columns:
        return pd.DataFrame(columns=['ItemID', 'LeadStart_Custom', 'LeadTime_Custom_Dias'])

    stage_cols = get_downstream_workflow_stage_columns(items_df)
    done_col = get_downstream_done_stage_column(stage_cols)
    if not done_col:
        return pd.DataFrame(columns=['ItemID', 'LeadStart_Custom', 'LeadTime_Custom_Dias'])

    selected = [c for c in (selected_start_stages or []) if c in items_df.columns and c != done_col]
    if not selected:
        selected = get_default_lead_time_start_stages(stage_cols)
        selected = [c for c in selected if c in items_df.columns and c != done_col]
    if not selected:
        return pd.DataFrame(columns=['ItemID', 'LeadStart_Custom', 'LeadTime_Custom_Dias'])

    calc_cols = ['ID', done_col] + selected
    tmp = items_df[calc_cols].copy()
    for col in [done_col] + selected:
        tmp[col] = pd.to_datetime(tmp[col], dayfirst=True, errors='coerce')

    # Commitment date is the earliest date across selected workflow columns.
    tmp['LeadStart_Custom'] = tmp[selected].min(axis=1)
    tmp['LeadEnd_Custom'] = tmp[done_col]
    lead_days = (tmp['LeadEnd_Custom'] - tmp['LeadStart_Custom']).dt.days
    tmp['LeadTime_Custom_Dias'] = pd.to_numeric(lead_days, errors='coerce')
    tmp.loc[tmp['LeadTime_Custom_Dias'] < 0, 'LeadTime_Custom_Dias'] = np.nan

    out = tmp.rename(columns={'ID': 'ItemID', 'LeadStart_Custom': 'LeadStart_Custom'})[['ItemID', 'LeadStart_Custom', 'LeadTime_Custom_Dias']]
    out['ItemID'] = out['ItemID'].astype(str)
    return out.drop_duplicates(subset=['ItemID'], keep='first')


def build_time_to_commit_by_selected_stages(projeto, selected_start_stages):
    """
    Resolve the first selected commitment stage strictly after backlog entry.
    Returns dataframe with columns: ItemID, Commitment_Selected, TimeToCommit_Selected_Dias.
    """
    items_df = load_project_downstream_items_csv(projeto)
    if items_df.empty or 'ID' not in items_df.columns:
        return pd.DataFrame(columns=['ItemID', 'Commitment_Selected', 'TimeToCommit_Selected_Dias'])

    stage_cols = get_downstream_workflow_stage_columns(items_df)
    if not stage_cols:
        return pd.DataFrame(columns=['ItemID', 'Commitment_Selected', 'TimeToCommit_Selected_Dias'])

    selected = [c for c in (selected_start_stages or []) if c in items_df.columns]
    if not selected:
        selected = get_default_lead_time_start_stages(stage_cols)
        selected = [c for c in selected if c in items_df.columns]
    if not selected:
        return pd.DataFrame(columns=['ItemID', 'Commitment_Selected', 'TimeToCommit_Selected_Dias'])

    selected_non_backlog = [
        c for c in selected
        if normalize_text(c) not in LEAD_TIME_BACKLOG_LIKE_STAGE_NAMES
    ]
    if selected_non_backlog:
        selected = selected_non_backlog

    calc_cols = ['ID'] + [c for c in selected if c in items_df.columns]
    if len(calc_cols) <= 1:
        return pd.DataFrame(columns=['ItemID', 'Commitment_Selected', 'TimeToCommit_Selected_Dias'])

    tmp = items_df[calc_cols].copy()
    for col in calc_cols[1:]:
        tmp[col] = pd.to_datetime(tmp[col], dayfirst=True, errors='coerce')

    renamed = {}
    candidate_cols = []
    for idx, col in enumerate(calc_cols[1:]):
        safe_col = f'CommitStage_{idx}'
        renamed[col] = safe_col
        candidate_cols.append(safe_col)
    tmp = tmp.rename(columns=renamed)

    out = tmp.rename(columns={'ID': 'ItemID'})
    out['ItemID'] = out['ItemID'].astype(str)
    out.attrs['candidate_cols'] = candidate_cols
    return out.drop_duplicates(subset=['ItemID'], keep='first')


def _coerce_datetime_flexible(series):
    """Parse datetime from mixed raw values, including YYYYMMDD-like numeric ids."""
    if series is None:
        return pd.Series(dtype='datetime64[ns]')
    raw = pd.Series(series)
    raw_str = raw.astype(str).str.strip()
    ddmmyyyy_mask = raw_str.str.fullmatch(r'\d{2}/\d{2}/\d{4}')
    dt = pd.to_datetime(raw.where(~ddmmyyyy_mask), errors='coerce', utc=True).dt.tz_localize(None)
    if ddmmyyyy_mask.any():
        dt_ddmmyyyy = pd.to_datetime(raw.where(ddmmyyyy_mask), dayfirst=True, errors='coerce', utc=True).dt.tz_localize(None)
        dt = dt.combine_first(dt_ddmmyyyy)

    num = pd.to_numeric(raw, errors='coerce')
    if num.notna().any():
        num_int = num.dropna().astype('Int64').astype(str).str.strip()
        looks_yyyymmdd = num_int.str.fullmatch(r'\d{8}')
        if looks_yyyymmdd.any():
            parsed = pd.to_datetime(num_int.where(looks_yyyymmdd), format='%Y%m%d', errors='coerce')
            dt = dt.combine_first(parsed)
    return dt


def _resolve_lead_start_series(df_source):
    """Resolve best-available lead start datetime per row using fallback chain."""
    idx = df_source.index
    lead_start = pd.Series(pd.NaT, index=idx, dtype='datetime64[ns]')
    lead_source = pd.Series('', index=idx, dtype='object')

    candidates = [
        ('LeadStart_Selected', 'etapas'),
        ('DataInProgress', 'in_progress'),
        ('DataBacklog', 'backlog'),
        ('DataInicioProgresso', 'inicio_progresso'),
        ('DataInicioProgressoID', 'inicio_progresso_id'),
        ('DataCriacao', 'criacao'),
        ('DataCriacaoID', 'criacao_id'),
        ('Created', 'created'),
        ('CreatedDate', 'created_date'),
        ('IssueCreated', 'issue_created'),
        ('FirstMovementDate', 'first_movement'),
        ('FirstTransitionDate', 'first_transition'),
        ('History Created', 'history_created'),
    ]
    for col, source_tag in candidates:
        if col not in df_source.columns:
            continue
        parsed = _coerce_datetime_flexible(df_source[col])
        fill_mask = lead_start.isna() & parsed.notna()
        if fill_mask.any():
            lead_start.loc[fill_mask] = parsed.loc[fill_mask]
            lead_source.loc[fill_mask] = source_tag
    return lead_start, lead_source


def apply_selected_lead_time_metric(df, projeto, selected_start_stages):
    """Attach lead time metric based on selected downstream stages to the filtered dataframe."""
    if df is None or getattr(df, 'empty', True):
        return df, {'enabled': False, 'sample': 0, 'stage_count': 0, 'label': 'padrão'}
    if 'ItemID' not in df.columns:
        out = df.copy()
        out['LeadTime_Selected_Dias'] = pd.to_numeric(out.get('LeadTime_Dias'), errors='coerce')
        out['LeadStart_Selected'] = pd.to_datetime(out.get('DataBacklog'), errors='coerce')
        return out, {'enabled': False, 'sample': int(out['LeadTime_Selected_Dias'].notna().sum()), 'stage_count': 0, 'label': 'padrão', 'fallback_sample': 0}

    out = df.copy()
    out['LeadTime_Selected_Dias'] = pd.to_numeric(out.get('LeadTime_Dias'), errors='coerce')
    out['LeadStart_Selected'] = pd.to_datetime(out.get('DataBacklog'), errors='coerce')

    lead_maps = []
    if projeto:
        lead_map = build_custom_lead_time_by_selected_stages(projeto, selected_start_stages)
        if not lead_map.empty:
            lead_map = lead_map.copy()
            lead_map['Projeto'] = str(projeto)
            lead_maps.append(lead_map)
    else:
        if 'Projeto' in out.columns:
            project_values = (
                out['Projeto']
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )
            for project_name in project_values:
                if not project_name:
                    continue
                lead_map = build_custom_lead_time_by_selected_stages(project_name, selected_start_stages)
                if lead_map.empty:
                    continue
                lead_map = lead_map.copy()
                lead_map['Projeto'] = project_name
                lead_maps.append(lead_map)

    custom_days = pd.Series(np.nan, index=out.index, dtype='float64')
    custom_start = pd.Series(pd.NaT, index=out.index, dtype='datetime64[ns]')
    if lead_maps:
        lead_map = pd.concat(lead_maps, ignore_index=True)
        merge_keys = ['ItemID']
        if 'Projeto' in out.columns and 'Projeto' in lead_map.columns:
            out['Projeto'] = out['Projeto'].astype(str).str.strip()
            lead_map['Projeto'] = lead_map['Projeto'].astype(str).str.strip()
            merge_keys = ['Projeto', 'ItemID']

        out['ItemID'] = out['ItemID'].astype(str)
        out = out.merge(lead_map, how='left', on=merge_keys)
        custom_days = pd.to_numeric(out.get('LeadTime_Custom_Dias'), errors='coerce')
        custom_start = pd.to_datetime(out.get('LeadStart_Custom'), errors='coerce')
    out['LeadTime_Selected_Dias'] = custom_days.combine_first(out['LeadTime_Selected_Dias'])
    out['LeadStart_Selected'] = custom_start.combine_first(out['LeadStart_Selected'])

    out['LeadTime_Selected_Dias'] = pd.to_numeric(out.get('LeadTime_Selected_Dias'), errors='coerce')
    out.loc[out['LeadTime_Selected_Dias'] < 0, 'LeadTime_Selected_Dias'] = np.nan

    lead_start_resolved, lead_start_source = _resolve_lead_start_series(out)
    out['LeadStart_Selected'] = lead_start_resolved
    out['LeadStart_Source'] = lead_start_source

    if 'DataDone' in out.columns:
        done_ts = pd.to_datetime(out['DataDone'], errors='coerce')
        fallback_days = pd.to_numeric((done_ts - out['LeadStart_Selected']).dt.days, errors='coerce')
        fallback_days = fallback_days.where(fallback_days >= 0)
        fill_lt_mask = out['LeadTime_Selected_Dias'].isna() & fallback_days.notna()
        out.loc[fill_lt_mask, 'LeadTime_Selected_Dias'] = fallback_days.loc[fill_lt_mask]
        out.loc[fill_lt_mask & out['LeadStart_Source'].eq(''), 'LeadStart_Source'] = 'fallback'
    else:
        fill_lt_mask = pd.Series(False, index=out.index)
    out.drop(columns=['LeadTime_Custom_Dias'], inplace=True, errors='ignore')
    out.drop(columns=['LeadStart_Custom'], inplace=True, errors='ignore')
    custom_sample = int(custom_days.notna().sum())
    fallback_sample = int(fill_lt_mask.sum()) if 'fill_lt_mask' in locals() else 0
    return out, {
        'enabled': custom_sample > 0,
        'sample': int(out['LeadTime_Selected_Dias'].notna().sum()),
        'stage_count': len(selected_start_stages or []),
        'label': 'etapas selecionadas' if custom_sample > 0 else 'padrão',
        'fallback_sample': fallback_sample,
    }


def apply_selected_commitment_metric(df, projeto, selected_start_stages):
    """Attach commitment milestone and time-to-commit based on selected downstream stages."""
    if df is None or getattr(df, 'empty', True):
        return df, {'enabled': False, 'sample': 0, 'strict_sample': 0, 'fallback_sample': 0}

    out = df.copy()
    backlog_anchor = pd.to_datetime(out.get('DataBacklog'), errors='coerce')
    lead_start_fallback = pd.to_datetime(out.get('LeadStart_Selected'), errors='coerce')
    data_in_progress = pd.to_datetime(out.get('DataInProgress'), errors='coerce')
    # Never treat the backlog entry itself as a valid commitment date.
    fallback_commitment = lead_start_fallback.where(lead_start_fallback > backlog_anchor)
    fallback_commitment = fallback_commitment.combine_first(
        data_in_progress.where(data_in_progress > backlog_anchor)
    )
    fallback_days = pd.to_numeric((fallback_commitment - backlog_anchor).dt.days, errors='coerce')
    fallback_days = fallback_days.where(fallback_days >= 0)

    out['Commitment_Selected'] = fallback_commitment
    out['TimeToCommit_Selected_Dias'] = fallback_days

    if 'ItemID' not in out.columns or 'DataBacklog' not in out.columns:
        return out, {
            'enabled': False,
            'sample': int(out['TimeToCommit_Selected_Dias'].notna().sum()),
            'strict_sample': 0,
            'fallback_sample': int(out['TimeToCommit_Selected_Dias'].notna().sum()),
        }

    commit_maps = []
    if projeto:
        commit_map = build_time_to_commit_by_selected_stages(projeto, selected_start_stages)
        if not commit_map.empty:
            commit_map = commit_map.copy()
            commit_map['Projeto'] = str(projeto)
            commit_maps.append(commit_map)
    elif 'Projeto' in out.columns:
        project_values = out['Projeto'].dropna().astype(str).str.strip().unique().tolist()
        for project_name in project_values:
            if not project_name:
                continue
            commit_map = build_time_to_commit_by_selected_stages(project_name, selected_start_stages)
            if commit_map.empty:
                continue
            commit_map = commit_map.copy()
            commit_map['Projeto'] = project_name
            commit_maps.append(commit_map)

    strict_sample = 0
    if commit_maps:
        commit_map = pd.concat(commit_maps, ignore_index=True)
        candidate_cols = [c for c in commit_map.columns if c.startswith('CommitStage_')]
        merge_keys = ['ItemID']
        if 'Projeto' in out.columns and 'Projeto' in commit_map.columns:
            out['Projeto'] = out['Projeto'].astype(str).str.strip()
            commit_map['Projeto'] = commit_map['Projeto'].astype(str).str.strip()
            merge_keys = ['Projeto', 'ItemID']
        out['ItemID'] = out['ItemID'].astype(str)
        out = out.merge(commit_map, how='left', on=merge_keys)

        if candidate_cols:
            candidate_frames = []
            for col in candidate_cols:
                stage_ts = pd.to_datetime(out.get(col), errors='coerce')
                candidate_frames.append(stage_ts.where(stage_ts > backlog_anchor).rename(col))
            strict_commitment = pd.concat(candidate_frames, axis=1).min(axis=1)
            strict_days = pd.to_numeric((strict_commitment - backlog_anchor).dt.days, errors='coerce')
            strict_days = strict_days.where(strict_days >= 0)
            strict_sample = int(strict_days.notna().sum())
            out['Commitment_Selected'] = strict_commitment.combine_first(out['Commitment_Selected'])
            out['TimeToCommit_Selected_Dias'] = strict_days.combine_first(out['TimeToCommit_Selected_Dias'])
        out.drop(columns=candidate_cols, inplace=True, errors='ignore')

    out['Commitment_Selected'] = pd.to_datetime(out.get('Commitment_Selected'), errors='coerce')
    out['TimeToCommit_Selected_Dias'] = pd.to_numeric(out.get('TimeToCommit_Selected_Dias'), errors='coerce')
    out.loc[out['TimeToCommit_Selected_Dias'] < 0, 'TimeToCommit_Selected_Dias'] = np.nan
    return out, {
        'enabled': strict_sample > 0,
        'sample': int(out['TimeToCommit_Selected_Dias'].notna().sum()),
        'strict_sample': strict_sample,
        'fallback_sample': int(fallback_days.notna().sum()),
    }


def build_leadtime_stage_selection_summary(projeto, selected_start_stages):
    """UI summary of active Lead Time stage selection (commitment -> finalization)."""
    stage_cols, stage_source = get_leadtime_stage_filter_columns(projeto)
    done_col = get_downstream_done_stage_column(stage_cols) if stage_cols else 'Itens concluídos'
    done_col_for_selection = done_col if stage_source == 'downstream' else get_explicit_done_stage_column(stage_cols)
    selected = [s for s in (selected_start_stages or []) if s in stage_cols and s != done_col_for_selection]
    auto_mode = False
    if not selected:
        selectable_stage_cols = [s for s in stage_cols if s != done_col_for_selection]
        selected = get_default_lead_time_start_stages(selectable_stage_cols) if stage_cols else []
        auto_mode = True

    chips = []
    for stage in selected:
        chips.append(html.Span(
            stage,
            style={
                'display': 'inline-block',
                'padding': '4px 10px',
                'borderRadius': '14px',
                'backgroundColor': '#d9edf7',
                'color': '#154360',
                'marginRight': '6px',
                'marginBottom': '6px',
                'fontSize': '12px',
                'fontWeight': 'bold',
            }
        ))

    footer_note = "Seleção padrão automática" if auto_mode else "Seleção definida no filtro"
    if stage_source == 'bottlenecks':
        footer_note = "Etapas carregadas de gargalos/modelo; cálculo usa fallback do modelo sem CSV downstream detalhado"
    elif not stage_cols:
        footer_note = "CSV downstream detalhado do projeto não encontrado (local/URL); usando coluna do modelo"

    return html.Div([
        html.Div("Lead Time (Comprometimento -> Finalização)", style={'fontWeight': 'bold', 'marginBottom': '4px'}),
        html.Div([
            html.Span("Etapas de início: ", style={'color': '#555'}),
            html.Span(chips if chips else ['—'])
        ], style={'marginBottom': '4px'}),
        html.Div([
            html.Span("Etapa final: ", style={'color': '#555'}),
            html.Span(str(done_col), style={'fontWeight': 'bold'})
        ], style={'marginBottom': '2px'}),
        html.Div(footer_note, style={'fontSize': '11px', 'color': '#777'}),
    ], style={
        'maxWidth': '1100px',
        'margin': '0 auto 12px auto',
        'padding': '10px 12px',
        'border': '1px solid #dfe6ee',
        'borderRadius': '10px',
        'backgroundColor': '#f8fafc',
    })


def _compute_bitbucket_weekly_dora(bitbucket_logs, week_start, week_end):
    commits = bitbucket_logs.get('commits', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    pipelines = bitbucket_logs.get('pipelines', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    pullrequests = bitbucket_logs.get('pullrequests', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    out = {
        'deploy_frequency': np.nan,
        'lead_time_changes': np.nan,
        'change_failure_rate': np.nan,
        'mttr': np.nan,
    }

    week_pipes = pd.DataFrame()
    if not pipelines.empty and 'completed_on' in pipelines.columns:
        week_pipes = pipelines[
            (pipelines['completed_on'] >= week_start) &
            (pipelines['completed_on'] < week_end)
        ].copy()

    if not pipelines.empty and {'ref_name', 'state_norm'}.issubset(pipelines.columns):
        refs_raw = os.getenv('FLOW_PMO_DORA_DEPLOY_REFS', 'main,master,production,prod')
        deploy_refs = {str(r).strip().lower() for r in str(refs_raw).split(',') if str(r).strip()}
        if deploy_refs:
            pipelines = pipelines[
                pipelines['ref_name'].astype(str).str.strip().str.lower().isin(deploy_refs)
            ].copy()
            week_pipes = pipelines[
                (pipelines['completed_on'] >= week_start) &
                (pipelines['completed_on'] < week_end)
            ].copy()

    if not week_pipes.empty and 'state_norm' in week_pipes.columns:
        success_mask = week_pipes['state_norm'].isin({'successful', 'success'})
        failure_mask = week_pipes['state_norm'].isin({'failed', 'error'})
        deploy_success = int(success_mask.sum())
        total_deploys = int((success_mask | failure_mask).sum())
        failed_deploys = int(failure_mask.sum())
        out['deploy_frequency'] = float(deploy_success)
        if total_deploys > 0:
            out['change_failure_rate'] = (failed_deploys / total_deploys) * 100.0

        if deploy_success > 0 and not commits.empty and {'commit_hash', 'completed_on'}.issubset(week_pipes.columns) and {'hash', 'date'}.issubset(commits.columns):
            commit_lookup = commits[['hash', 'date']].copy()
            commit_lookup['hash'] = commit_lookup['hash'].astype(str).str.strip()
            deploy_success_df = week_pipes[success_mask].copy()
            deploy_success_df['commit_hash'] = deploy_success_df['commit_hash'].astype(str).str.strip()
            deploy_join = deploy_success_df.merge(commit_lookup, how='left', left_on='commit_hash', right_on='hash')
            lead_days = (
                pd.to_datetime(deploy_join['completed_on'], errors='coerce') -
                pd.to_datetime(deploy_join['date'], errors='coerce')
            ).dt.total_seconds() / 86400.0
            lead_days = pd.to_numeric(lead_days, errors='coerce')
            lead_days = lead_days[(lead_days >= 0) & lead_days.notna()]
            if not lead_days.empty:
                out['lead_time_changes'] = float(lead_days.mean())

        if failed_deploys > 0:
            ordered_week = week_pipes.sort_values('completed_on')
            history = pipelines.sort_values('completed_on')
            recovery_days = []
            week_fail_rows = ordered_week[ordered_week['state_norm'].isin({'failed', 'error'})]
            for _, fail_row in week_fail_rows.iterrows():
                fail_ts = fail_row.get('completed_on')
                fail_ref = str(fail_row.get('ref_name') or '').strip().lower()
                if pd.isna(fail_ts):
                    continue
                ref_success = history[
                    history['state_norm'].isin({'successful', 'success'}) &
                    (history['ref_name'].astype(str).str.strip().str.lower() == fail_ref) &
                    (history['completed_on'] > fail_ts)
                ]
                if ref_success.empty:
                    continue
                next_success = ref_success.iloc[0]['completed_on']
                delta = (next_success - fail_ts).total_seconds() / 86400.0
                if delta >= 0:
                    recovery_days.append(delta)
            if recovery_days:
                out['mttr'] = float(np.mean(recovery_days))

    if pd.isna(out['lead_time_changes']) and not pullrequests.empty and {'created_on', 'updated_on', 'state_norm'}.issubset(pullrequests.columns):
        merged_prs = pullrequests[
            (pullrequests['state_norm'] == 'merged') &
            (pullrequests['updated_on'] >= week_start) &
            (pullrequests['updated_on'] < week_end)
        ]
        if not merged_prs.empty:
            pr_days = (
                pd.to_datetime(merged_prs['updated_on'], errors='coerce') -
                pd.to_datetime(merged_prs['created_on'], errors='coerce')
            ).dt.total_seconds() / 86400.0
            pr_days = pd.to_numeric(pr_days, errors='coerce')
            pr_days = pr_days[(pr_days >= 0) & pr_days.notna()]
            if not pr_days.empty:
                out['lead_time_changes'] = float(pr_days.mean())

    return out


def _format_change_lead_time(days_value):
    if pd.isna(days_value):
        return '—'
    if float(days_value) < 1.0:
        return f"{float(days_value) * 24.0:.1f}h"
    return f"{float(days_value):.1f}d"


def compute_weekly_service_metrics(df_projeto, weeks, lead_time_col='LeadTime_Dias', projeto=None,
                                   wip_stage_map=None, wip_stage_filter=None, wip_base_df=None):
    """Calcula métricas de performance do serviço por semana (layout transposto)."""
    metric_names = [
        'Taxa de chegada / semana',
        'Throughput / semana',
        'Pressão de Fluxo (ρ)',
        'Média WIP / semana',
        'WIP Age (dias)',
        'Média Lead Time',
        'P85% DO LEAD TIME',
        'Cadência sugerida (λ Weibull, dias)',
        'Média Eficiência de Fluxo',
        '% Demanda de Valor',
        '% Demanda de Falha',
        'Qtd. Itens Descartados',
        'DDP',
        'Frequência de Deploy',
        'Lead time para mudanças',
    ]
    rows = {m: {} for m in metric_names}
    bitbucket_logs = load_project_bitbucket_logs(projeto)
    lead_start_col = 'LeadStart_Selected' if 'LeadStart_Selected' in df_projeto.columns else 'DataInProgress'
    lead_start_series = pd.to_datetime(
        df_projeto.get(lead_start_col, pd.Series(pd.NaT, index=df_projeto.index)),
        errors='coerce'
    )
    wip_source = wip_base_df if wip_base_df is not None else df_projeto

    for i in range(len(weeks) - 1):
        week_start = weeks[i]
        week_end = weeks[i + 1]
        week_label = str(week_start.date())

        arrived = df_projeto[
            (lead_start_series >= week_start) & (lead_start_series < week_end)
        ]
        finished = df_projeto[
            (df_projeto['DataDone'] >= week_start) & (df_projeto['DataDone'] < week_end)
        ]
        weekly_wip = build_live_wip_snapshot(
            wip_source,
            week_end,
            projeto=projeto,
            selected_stages=wip_stage_filter,
            stage_map=wip_stage_map,
        )

        finished_eligible = finished[done_time_eligible_mask(finished)] if not finished.empty else finished
        tp_total = len(finished_eligible)
        if tp_total > 0:
            original_type_series = finished_eligible.get('TipoOriginalJira')
            if original_type_series is None:
                original_type_series = finished_eligible.apply(
                    lambda row: canonicalize_original_jira_type(row.get('WorkItemSubType'), row.get('Tipo')),
                    axis=1
                )
            demand_bucket = original_type_series.apply(classify_original_jira_demand_bucket)
            tp_value = int(demand_bucket.eq('value').sum())
            tp_failure = int(demand_bucket.eq('failure').sum())
            tp_value_failure_total = int(demand_bucket.isin(['value', 'failure']).sum())
        else:
            tp_value = 0
            tp_failure = 0
            tp_value_failure_total = 0
        tp_discard = int(finished_eligible['Descartado'].sum()) if 'Descartado' in finished_eligible.columns else 0

        wip_age_series = pd.to_numeric(weekly_wip.get('WIPAge', pd.Series(dtype=float)), errors='coerce').dropna()
        wip_age = float(wip_age_series.mean()) if not wip_age_series.empty else 0
        lt_finished = time_metric_series(finished, lead_time_col, non_negative=True)
        avg_lt = lt_finished.mean() if not lt_finished.empty else np.nan
        pressure_rho, avg_eff = calculate_flow_efficiency(len(arrived), tp_total)
        if pd.isna(avg_eff):
            avg_eff = 0
        median_lt = exact_empirical_percentile(lt_finished, 0.50) if tp_total > 0 and not lt_finished.empty else np.nan
        p85_lt = exact_empirical_percentile(lt_finished, 0.85) if tp_total > 0 and not lt_finished.empty else np.nan
        lt_weibull = fit_weibull_linearized(lt_finished) if not lt_finished.empty else None
        weibull_lambda = float(lt_weibull['lambda']) if lt_weibull else np.nan
        cadence_hint = describe_weibull_scale_cadence(weibull_lambda) if lt_weibull else None
        dora = _compute_bitbucket_weekly_dora(bitbucket_logs, week_start, week_end)
        dora_deploy_frequency = dora.get('deploy_frequency')
        dora_lead_time = dora.get('lead_time_changes')

        rows['Taxa de chegada / semana'][week_label] = str(len(arrived))
        rows['Throughput / semana'][week_label] = str(tp_total)
        rows['Pressão de Fluxo (ρ)'][week_label] = f"{pressure_rho:.2f}" if pd.notna(pressure_rho) else '—'
        rows['Média WIP / semana'][week_label] = str(len(weekly_wip))
        rows['WIP Age (dias)'][week_label] = f"{wip_age:.0f}" if wip_age else '0'
        rows['Média Lead Time'][week_label] = f"{avg_lt:.0f}" if pd.notna(avg_lt) else '—'
        rows['P85% DO LEAD TIME'][week_label] = f"{p85_lt:.0f}" if pd.notna(p85_lt) else '—'
        rows['Cadência sugerida (λ Weibull, dias)'][week_label] = (
            f"{weibull_lambda:.1f} | {cadence_hint['label']}"
            if cadence_hint and pd.notna(weibull_lambda)
            else '—'
        )
        rows['Média Eficiência de Fluxo'][week_label] = f"{avg_eff:.3f}" if pd.notna(avg_eff) else '0.000'
        rows['% Demanda de Valor'][week_label] = f"{tp_value / tp_value_failure_total * 100:.1f}%" if tp_value_failure_total > 0 else '—'
        rows['% Demanda de Falha'][week_label] = f"{tp_failure / tp_value_failure_total * 100:.1f}%" if tp_value_failure_total > 0 else '—'
        rows['Qtd. Itens Descartados'][week_label] = str(tp_discard)
        rows['DDP'][week_label] = f"{max(0, p85_lt - median_lt):.1f}" if pd.notna(p85_lt) and pd.notna(median_lt) else '—'
        rows['Frequência de Deploy'][week_label] = f"{dora_deploy_frequency:.0f}" if pd.notna(dora_deploy_frequency) else str(tp_value)
        rows['Lead time para mudanças'][week_label] = _format_change_lead_time(dora_lead_time) if pd.notna(dora_lead_time) else _format_change_lead_time(avg_lt)

    return metric_names, rows


def resolve_creator_filter_column(df_source):
    if df_source is None:
        return None
    for col in CREATOR_FILTER_COLUMN_CANDIDATES:
        if col in df_source.columns:
            return col
    return None


def build_dropdown_options_from_column(df_source, column_name):
    if df_source is None or getattr(df_source, 'empty', True) or not column_name or column_name not in df_source.columns:
        return []
    values = (
        df_source[column_name]
        .fillna('')
        .astype(str)
        .str.strip()
    )
    unique_values = sorted(v for v in values.unique().tolist() if v)
    return [{'label': value, 'value': value} for value in unique_values]


def build_creator_filter_dataset(projeto=None):
    fato = _df().fato
    projeto = normalize_project_filter_value(projeto)
    base = fato.copy()
    if projeto and 'Projeto' in base.columns:
        base = base[base['Projeto'].astype(str).str.strip() == str(projeto).strip()].copy()
    return enrich_items_with_downstream_metadata(base, projeto=projeto)


def get_creator_filter_options_for_project(projeto=None):
    creator_df = build_creator_filter_dataset(projeto)
    creator_col = resolve_creator_filter_column(creator_df)
    return build_dropdown_options_from_column(creator_df, creator_col)


def resolve_creation_date_series(df_source):
    if df_source is None:
        return pd.Series(dtype='datetime64[ns]')
    idx = df_source.index
    creation_date = pd.Series(pd.NaT, index=idx, dtype='datetime64[ns]')
    for col in CREATION_DATE_COLUMN_CANDIDATES:
        if col not in df_source.columns:
            continue
        parsed = _coerce_datetime_flexible(df_source[col])
        creation_date = creation_date.combine_first(parsed)
    return creation_date


def resolve_filter_date_series(df_source, use_creation_date=False):
    if df_source is None:
        return pd.Series(dtype='datetime64[ns]')
    if use_creation_date:
        return resolve_creation_date_series(df_source)
    if 'DataDone' in df_source.columns:
        return pd.to_datetime(df_source['DataDone'], errors='coerce')
    return pd.Series(pd.NaT, index=df_source.index, dtype='datetime64[ns]')


def build_date_range_mask(date_series, start_date=None, end_date=None):
    if date_series is None:
        return pd.Series(dtype=bool)
    mask = pd.Series(True, index=date_series.index, dtype=bool)
    if start_date:
        mask &= date_series >= pd.to_datetime(start_date)
    if end_date:
        mask &= date_series <= pd.to_datetime(end_date)
    return mask


def filter_df(df, start_date, end_date, projeto, tipo, classe_servico, responsavel, criadores=None, use_creation_date=False, apply_date=True, tipo_original=None):
    d = df.copy()
    if projeto:
        d = d[d['Projeto'] == projeto]
    if tipo:
        d = d[d['TipoDemanda'] == tipo]
    selected_original_types = set(normalize_original_jira_type_filter_values(tipo_original))
    if selected_original_types:
        d = d[d['TipoOriginalJira'].fillna('').astype(str).str.strip().isin(selected_original_types)]
    if classe_servico:
        d = d[d['ClasseServico'] == classe_servico]
    if responsavel:
        selected_responsaveis = set(_normalize_responsavel_filter_values(responsavel))
        d = d[d['Responsavel'].fillna('').astype(str).str.strip().isin(selected_responsaveis)]
    if criadores or use_creation_date:
        d = enrich_items_with_downstream_metadata(d, projeto=projeto)
    if criadores:
        creator_col = resolve_creator_filter_column(d)
        if creator_col and creator_col in d.columns:
            selected_creators = {str(value).strip() for value in criadores if str(value).strip()}
            creator_series = d[creator_col].fillna('').astype(str).str.strip()
            d = d[creator_series.isin(selected_creators)]
        else:
            return d.iloc[0:0].copy()
    if apply_date:
        filter_date_series = resolve_filter_date_series(d, use_creation_date=use_creation_date)
        d = d[build_date_range_mask(filter_date_series, start_date, end_date)]
    return d


def _work_item_age_health_label(age_days, cycle_p50, cycle_p85):
    age = pd.to_numeric(pd.Series([age_days]), errors='coerce').iloc[0]
    p50 = pd.to_numeric(pd.Series([cycle_p50]), errors='coerce').iloc[0]
    p85 = pd.to_numeric(pd.Series([cycle_p85]), errors='coerce').iloc[0]
    if pd.isna(age):
        return 'Sem idade'
    if pd.isna(p50) or p50 <= 0:
        return 'Sem referência'
    if age <= p50:
        return 'Saudável'
    if pd.notna(p85) and p85 > p50:
        if age <= p85:
            return 'Atenção'
        return 'Crítico'
    if age <= (p50 * 1.5):
        return 'Atenção'
    return 'Crítico'


def _work_item_age_bucket(age_days):
    age = pd.to_numeric(pd.Series([age_days]), errors='coerce').iloc[0]
    if pd.isna(age):
        return 'Sem idade'
    if age <= 7:
        return '0-7d'
    if age <= 15:
        return '8-15d'
    if age <= 30:
        return '16-30d'
    if age <= 60:
        return '31-60d'
    return '60d+'
