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
import socket
import urllib.request
import urllib.parse
import re
try:
    from plotly.subplots import make_subplots
except ImportError:
    from plotly.tools import make_subplots
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Config ---
import platform
if platform.system() == 'Windows':
    LEGACY_DATA_FOLDER = r'C:\Users\W1 TI\OneDrive - W1\Documentos\Dados'
else:
    LEGACY_DATA_FOLDER = os.path.join(os.path.expanduser('~'), 'Library', 'CloudStorage', 'OneDrive-W1', 'Documentos', 'Dados')


def _is_windows_absolute_path(path_value):
    raw = str(path_value or '').strip()
    return bool(re.match(r'^[A-Za-z]:[\\/]', raw))


def _is_posix_absolute_path(path_value):
    raw = str(path_value or '').strip()
    return raw.startswith('/')


def _is_path_compatible_with_current_os(path_value):
    raw = str(path_value or '').strip()
    if not raw:
        return False
    if platform.system() == 'Windows':
        return _is_windows_absolute_path(raw) or not _is_posix_absolute_path(raw)
    return _is_posix_absolute_path(raw) or not _is_windows_absolute_path(raw)


def _sanitize_os_path(path_value):
    raw = str(path_value or '').strip()
    if not raw:
        return ''
    return raw if _is_path_compatible_with_current_os(raw) else ''


def _existing_dirs(paths):
    out = []
    seen = set()
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


def _candidate_data_folders():
    env_dirs = os.getenv('FLOW_PMO_DATA_DIRS', '').strip()
    split_env_dirs = [p for p in env_dirs.split(os.pathsep) if p.strip()]
    explicit_dir = os.getenv('FLOW_PMO_DATA_DIR', '').strip()
    legacy_override = os.getenv('DATA_FOLDER', '').strip()
    base_dir = os.path.dirname(__file__)
    project_root_dir = os.path.abspath(os.path.join(base_dir, os.pardir))
    home_dir = os.path.expanduser('~')
    return _existing_dirs([
        explicit_dir,
        legacy_override,
        *split_env_dirs,
        os.path.join(project_root_dir, 'dados', 'latest'),
        os.path.join(project_root_dir, 'dados'),
        os.path.join(base_dir, 'artifacts', 'process_mining'),
        os.path.join(home_dir, 'Documents', 'dados'),
        os.path.join(home_dir, 'Documents', 'Dados'),
        os.path.join(base_dir, 'data'),
        base_dir,
        LEGACY_DATA_FOLDER,
    ])


def _download_model_from_url(url):
    cache_dir = '/tmp/flow-pmo-models'
    os.makedirs(cache_dir, exist_ok=True)
    file_key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    out_file = os.path.join(cache_dir, f'PowerBI_Model_{file_key}.xlsx')
    _refresh_remote_cache_file(url, out_file)
    return out_file


def _download_portfolio_csv_from_url(url):
    cache_dir = '/tmp/flow-pmo-models'
    os.makedirs(cache_dir, exist_ok=True)
    file_key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    out_file = os.path.join(cache_dir, f'portfolio-bt-ns-{file_key}-data.csv')
    _refresh_remote_cache_file(url, out_file)
    return out_file


def _download_bottleneck_csv_from_url(url, project_key):
    cache_dir = '/tmp/flow-pmo-models'
    os.makedirs(cache_dir, exist_ok=True)
    safe_project = ''.join(ch for ch in str(project_key or '').lower() if ch.isalnum()) or 'project'
    file_key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    out_file = os.path.join(cache_dir, f'{safe_project}-{file_key}-data_bottlenecks.csv')
    _refresh_remote_cache_file(url, out_file)
    return out_file


def _download_process_mining_report_from_url(url):
    cache_dir = '/tmp/flow-pmo-models'
    os.makedirs(cache_dir, exist_ok=True)
    file_key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    out_file = os.path.join(cache_dir, f'w1nner-process-mining-{file_key}.xlsx')
    _refresh_remote_cache_file(url, out_file)
    return out_file


def _download_downstream_items_csv_from_url(url, project_key):
    cache_dir = '/tmp/flow-pmo-models'
    os.makedirs(cache_dir, exist_ok=True)
    safe_project = ''.join(ch for ch in str(project_key or '').lower() if ch.isalnum()) or 'project'
    file_key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    out_file = os.path.join(cache_dir, f'{safe_project}-{file_key}-data.csv')
    _refresh_remote_cache_file(url, out_file)
    return out_file


def _remote_cache_ttl_seconds():
    raw = os.getenv('FLOW_PMO_REMOTE_CACHE_TTL_SECONDS', '').strip()
    if not raw:
        return 300
    try:
        return max(0, int(raw))
    except Exception:
        return 300


def _refresh_remote_cache_file(url, out_file):
    """Download URL into cache file with TTL-based refresh for stable *latest* URLs."""
    ttl = _remote_cache_ttl_seconds()
    if os.path.exists(out_file):
        age_seconds = max(0.0, (datetime.now() - datetime.fromtimestamp(os.path.getmtime(out_file))).total_seconds())
        if age_seconds <= float(ttl):
            return out_file
    tmp_file = f"{out_file}.tmp"
    urllib.request.urlretrieve(url, tmp_file)
    os.replace(tmp_file, out_file)
    return out_file


def _load_bottleneck_url_map():
    raw = os.getenv('FLOW_PMO_BOTTLENECK_CSV_URL_MAP', '').strip()
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
        url = str(value).strip()
        if project_key and url:
            out[project_key] = url
    return out


def _load_downstream_url_map():
    raw = os.getenv('FLOW_PMO_DOWNSTREAM_CSV_URL_MAP', '').strip()
    if not raw:
        return {}
    parsed = None
    for candidate in (
        raw,
        raw.strip('"').strip("'"),
        raw.replace('\\"', '"'),
    ):
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            break
        except Exception:
            continue
    if parsed is None:
        # Fallback tolerante para env malformada:
        # ex.: FLOW_PMO_DOWNSTREAM_CSV_URL_MAP="{"W1NNER":"https://..."}"
        matches = re.findall(r'"?([A-Za-z0-9& _-]+)"?\s*:\s*"([^"]+)"', raw)
        if matches:
            parsed = {k: v for k, v in matches}
        else:
            return {}
    if not isinstance(parsed, dict):
        return {}
    out = {}
    for key, value in parsed.items():
        project_key = str(key).strip().upper()
        url = str(value).strip()
        if project_key and url:
            out[project_key] = url
    return out


def _url_filename_matches_project_suffix(url, expected_prefix, suffix):
    """Validate if URL filename seems to belong to the expected project prefix/suffix."""
    if not url or not expected_prefix:
        return False
    parsed = urllib.parse.urlparse(str(url).strip())
    filename = os.path.basename(parsed.path or '').lower()
    prefix = str(expected_prefix).strip().lower()
    return filename.startswith(prefix) and filename.endswith(str(suffix or '').lower())


def _url_filename_matches_project(url, expected_prefix):
    """Backward-compatible helper for bottleneck URLs."""
    return _url_filename_matches_project_suffix(url, expected_prefix, '-data_bottlenecks.csv')


def _resolve_model_file(data_folders):
    explicit_model = _sanitize_os_path(os.getenv('FLOW_PMO_MODEL_FILE', ''))
    if explicit_model:
        candidate = explicit_model if os.path.isabs(explicit_model) else os.path.join(os.path.dirname(__file__), explicit_model)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        raise FileNotFoundError(f'FLOW_PMO_MODEL_FILE aponta para arquivo inexistente: {candidate}')

    model_url = os.getenv('FLOW_PMO_MODEL_URL', '').strip()
    if model_url:
        return _download_model_from_url(model_url)

    model_files = []
    for folder in data_folders:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            if name.startswith('PowerBI_Model_') and name.endswith('.xlsx'):
                model_files.append(os.path.join(folder, name))
    if model_files:
        return max(model_files, key=os.path.getctime)

    raise FileNotFoundError(
        'Arquivo de modelo não encontrado. Configure FLOW_PMO_MODEL_FILE ou FLOW_PMO_MODEL_URL, '
        'ou adicione PowerBI_Model_*.xlsx em uma destas pastas: '
        + ', '.join(data_folders or ['(nenhuma pasta encontrada)'])
    )


DATA_FOLDERS = _candidate_data_folders()
DATA_FOLDER = DATA_FOLDERS[0] if DATA_FOLDERS else os.path.dirname(__file__)
MODEL_FILE = _resolve_model_file(DATA_FOLDERS)


def _format_last_processed_load(model_file):
    """Best-effort label for the processed data load timestamp."""
    try:
        filename = os.path.basename(model_file or '')
        match = re.match(r'^PowerBI_Model_(\d{8})_(\d{6})\.xlsx$', filename)
        if match:
            return datetime.strptime(''.join(match.groups()), '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M')
        return datetime.fromtimestamp(os.path.getmtime(model_file)).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return 'indisponível'


LAST_PROCESSED_LOAD_LABEL = _format_last_processed_load(MODEL_FILE)

# Load model
xls = pd.ExcelFile(MODEL_FILE)
dim_projeto = pd.read_excel(xls, sheet_name='Dim_Projeto')
dim_tipo = pd.read_excel(xls, sheet_name='Dim_Tipo')

def safe_read_sheet(excel_file, sheet_name, default_cols):
    if sheet_name in excel_file.sheet_names:
        return pd.read_excel(excel_file, sheet_name=sheet_name)
    return pd.DataFrame(columns=default_cols)

dim_responsavel = safe_read_sheet(xls, 'Dim_Responsavel', ['ResponsavelID', 'Responsavel'])
dim_prioridade = safe_read_sheet(xls, 'Dim_Prioridade', ['PrioridadeID', 'Prioridade'])
dim_classe_servico = safe_read_sheet(xls, 'Dim_ClasseServico', ['ClasseServicoID', 'ClasseServico'])
fato = pd.read_excel(xls, sheet_name='Fato_Items')
fato_gargalos = safe_read_sheet(
    xls,
    'Fato_Gargalos',
    ['Projeto', 'Etapa', 'Tempo Médio (dias)', 'Tempo Mediano (dias)', 'P90 (dias)', 'Qtde Itens', 'Vazão da Etapa (itens)'],
)

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
fato = fato.merge(dim_projeto, how='left', left_on='ProjetoID', right_on='ProjetoID')
fato = fato.merge(dim_tipo, how='left', left_on='TipoID', right_on='TipoID')
if not dim_responsavel.empty:
    fato = fato.merge(dim_responsavel, how='left', left_on='ResponsavelID', right_on='ResponsavelID')
if not dim_prioridade.empty:
    fato = fato.merge(dim_prioridade, how='left', left_on='PrioridadeID', right_on='PrioridadeID')
if not dim_classe_servico.empty and 'ClasseServicoID' in fato.columns:
    fato = fato.merge(dim_classe_servico, how='left', left_on='ClasseServicoID', right_on='ClasseServicoID')


def resolve_service_class(classe_servico, prioridade):
    """Use explicit service classes first; fallback to priority instead of generic Standard."""
    classe_text = ''
    if pd.notna(classe_servico):
        classe_text = str(classe_servico).strip()

    classe_norm = ''.join(ch for ch in classe_text.lower() if ch.isalnum() or ch.isspace()).strip()
    if classe_text and classe_norm and classe_norm not in {'standard', 'padrao', 'normal', 'default'}:
        return classe_text

    if pd.notna(prioridade):
        prioridade_text = str(prioridade).strip()
        if prioridade_text and prioridade_text.lower() != 'nan':
            prioridade_norm = ''.join(ch for ch in prioridade_text.lower() if ch.isalnum() or ch.isspace()).strip()
            if any(token in prioridade_norm for token in ['highest', 'higest']):
                return 'Expedite'
            return prioridade_text

    if classe_text and classe_text.lower() != 'nan':
        return classe_text
    return 'Standard'


def portfolio_type_to_demand_type(tipo):
    tipo_norm = normalize_text(tipo)
    if tipo_norm in {'epico', 'epic', 'feature', 'funcionalidade', 'historia', 'story', 'task', 'tarefa', 'spike'}:
        return TYPE_DEV
    if tipo_norm in {'support', 'suporte'}:
        return TYPE_SUPPORT
    if tipo_norm in {'bug', 'defeito', 'defeitos', 'issue', 'issues', 'problema', 'problemas'}:
        return TYPE_ISSUES
    return canonicalize_demand_type(tipo)


def portfolio_project_team_aliases(project_value):
    project_text = str(project_value or '').strip()
    if not project_text:
        return []

    aliases = [project_text]
    alias_map = {
        'DATA&ANALYTICS': ['TECH DATA', 'DATA ANALYTICS', 'DATA&ANALYTICS'],
        'BEFINANCE': ['TECH BEFINANCE', 'BEFINANCE', 'BF'],
        'S1NC': ['TECH S1NC', 'SQUAD | S1NC', 'S1NC'],
        'W1NNER': ['TECH W1NNER', 'SQUAD | W1NNER', 'W1NNER', 'W1NNR'],
    }
    aliases.extend(alias_map.get(project_text.upper(), []))

    out = []
    seen = set()
    for alias in aliases:
        norm = normalize_text(alias)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(alias)
    return out


def apply_portfolio_module_filters(df_portfolio, projeto=None, tipo=None, classe_servico=None, responsavel=None,
                                   portfolio_project=None, portfolio_quarter='ALL'):
    df_filtered = df_portfolio.copy() if df_portfolio is not None else pd.DataFrame()
    notes = []

    if df_filtered.empty:
        return df_filtered, None, notes

    if 'Prioridade' not in df_filtered.columns:
        df_filtered['Prioridade'] = ''
    if 'ClasseServico' not in df_filtered.columns:
        df_filtered['ClasseServico'] = ''
    df_filtered['ClasseServico'] = [
        resolve_service_class(classe, prioridade)
        for classe, prioridade in zip(df_filtered['ClasseServico'], df_filtered['Prioridade'])
    ]

    if 'Tipo' not in df_filtered.columns:
        df_filtered['Tipo'] = ''
    df_filtered['PortfolioTipoDemanda'] = df_filtered['Tipo'].apply(portfolio_type_to_demand_type)

    if portfolio_quarter != 'ALL':
        quarter_dates = {
            'Q1-2026': ('2026-01-01', '2026-03-31'),
            'Q2-2026': ('2026-04-01', '2026-06-30'),
            'Q3-2026': ('2026-07-01', '2026-09-30'),
            'Q4-2026': ('2026-10-01', '2026-12-31'),
        }
        if portfolio_quarter in quarter_dates and 'DueDate' in df_filtered.columns:
            q_start, q_end = quarter_dates[portfolio_quarter]
            q_start_ts = pd.to_datetime(q_start)
            q_end_ts = pd.to_datetime(q_end)
            df_filtered = df_filtered[
                (df_filtered['DueDate'] >= q_start_ts) &
                (df_filtered['DueDate'] <= q_end_ts)
            ].copy()

    effective_portfolio_project = None
    team_col = 'Team' if 'Team' in df_filtered.columns else None
    explicit_team = normalize_project_filter_value(portfolio_project)
    project_team_hint = normalize_project_filter_value(projeto)
    if explicit_team:
        effective_portfolio_project = explicit_team
        if team_col:
            explicit_team_norm = normalize_text(explicit_team)
            df_filtered = df_filtered[
                df_filtered[team_col].fillna('').astype(str).map(normalize_text) == explicit_team_norm
            ].copy()
            if df_filtered.empty:
                notes.append(f'TEAM "{explicit_team}" não possui itens no CSV atual de portfólio.')
        else:
            notes.append('O CSV atual de portfólio não possui a coluna Team.')
            df_filtered = df_filtered.iloc[0:0].copy()
    elif project_team_hint:
        effective_portfolio_project = project_team_hint
        if team_col:
            team_series = df_filtered[team_col].fillna('').astype(str)
            team_norm = team_series.map(normalize_text)
            aliases = portfolio_project_team_aliases(project_team_hint)
            alias_norms = [normalize_text(alias) for alias in aliases if normalize_text(alias)]
            mask = pd.Series(False, index=df_filtered.index)
            for alias_norm in alias_norms:
                mask = mask | team_norm.str.contains(alias_norm, regex=False, na=False)
            df_filtered = df_filtered[mask].copy()
            if df_filtered.empty:
                notes.append(f'Nenhum TEAM do portfólio corresponde ao filtro de projeto "{project_team_hint}".')
        else:
            notes.append('O CSV atual de portfólio não possui a coluna Team.')
            df_filtered = df_filtered.iloc[0:0].copy()

    if tipo:
        df_filtered = df_filtered[df_filtered['PortfolioTipoDemanda'] == tipo].copy()
        if df_filtered.empty:
            notes.append(f'Tipo "{tipo}" sem itens no escopo atual do portfólio.')

    if classe_servico:
        df_filtered = df_filtered[df_filtered['ClasseServico'] == classe_servico].copy()
        if df_filtered.empty:
            notes.append(f'Classe de serviço "{classe_servico}" sem itens no escopo atual do portfólio.')

    if responsavel:
        responsavel_col = next((col for col in ['Responsavel', 'Responsável'] if col in df_filtered.columns), None)
        if responsavel_col:
            df_filtered = df_filtered[df_filtered[responsavel_col].fillna('').astype(str) == str(responsavel)].copy()
            if df_filtered.empty:
                notes.append(f'Responsável "{responsavel}" sem itens no escopo atual do portfólio.')
        else:
            notes.append('O CSV atual de portfólio não possui informação de responsável.')
            df_filtered = df_filtered.iloc[0:0].copy()

    return df_filtered, effective_portfolio_project, notes


# Friendly column names
rename_map = {
    'NomeProjeto': 'Projeto',
    'Tipo': 'Tipo',
    'Responsavel': 'Responsavel',
    'Prioridade': 'Prioridade',
    'ClasseServico': 'ClasseServico',
}
fato.rename(columns={k: v for k, v in rename_map.items() if k in fato.columns}, inplace=True)
if 'ClasseServico' not in fato.columns:
    fato['ClasseServico'] = np.nan
if 'Prioridade' not in fato.columns:
    fato['Prioridade'] = np.nan
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

LEAD_TIME_END_STAGE_CANDIDATES = [
    'Itens concluídos', 'Itens concluidos', 'Done', 'Concluído', 'Concluido', 'ready for production'
]

LEAD_TIME_START_STAGE_PREFERENCES = [
    'Backlog', 'Triagem', 'Ready to Start', 'In progress'
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
PORTFOLIO_CSV_PREFIX = 'portfolio-bt-ns-'
PORTFOLIO_TAB_VALUE = 'tab-portfolio'
PROJECT_FILTER_ALL_VALUE = '__ALL_PROJECTS__'
PROJECT_FILTER_ALL_LABEL = 'Todos os projetos'
SERVICE_TABS = [
    ('Performance do Serviço', 'tab-performance'),
    ('One Page Report', 'tab-one-page'),
    ('Process Mining Jira', 'tab-process-mining-jira'),
    ('Painel Fluxo', 'tab-painel-3x3'),
    ('Lead Time', 'tab-lead-time'),
    ('Fluxo', 'tab-fluxo'),
    ('CFD', 'tab-cfd'),
    ('Saúde do Fluxo', 'tab-saude'),
    ('Análise Fluxo', 'tab-analise-fluxo'),
    ('Tendências', 'tab-tendencias'),
    ('Throughput Breakdown', 'tab-throughput-breakdown'),
    ('Padrões Sistêmicos', 'tab-padroes'),
    ('Work Item Age', 'tab-work-item-age'),
    ('WIP por Pessoa', 'tab-wip'),
    ('Estatística Descritiva', 'tab-estatistica'),
    ('Capacidade de Fila', 'tab-fila-capacidade'),
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
    return [dcc.Tab(label=label, value=value) for label, value in SERVICE_TABS]


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


def normalize_text(value):
    txt = str(value or '').strip().lower()
    translate_map = str.maketrans('áàâãäéèêëíìîïóòôõöúùûüç', 'aaaaaeeeeiiiiooooouuuuc')
    return txt.translate(translate_map)

TYPE_SUPPORT = 'Suporte'
TYPE_ISSUES = 'Issues/Defeitos/Problemas'
TYPE_DEV = 'Desenvolvimento'
TYPE_OTHER = 'Outro'


def canonicalize_demand_type(tipo, subtype=None):
    tipo_norm = normalize_text(tipo)
    subtype_norm = normalize_text(subtype)

    if tipo_norm in {'suporte', 'support'} or subtype_norm in {'suporte', 'support'}:
        return TYPE_SUPPORT
    if tipo_norm in {'defeitos', 'defeito', 'bug', 'issue', 'issues', 'problema', 'problemas'}:
        return TYPE_ISSUES
    if tipo_norm == normalize_text(TYPE_ISSUES):
        return TYPE_ISSUES
    if tipo_norm in {'desenvolvimento', 'development'}:
        return TYPE_DEV
    if tipo_norm in {'outro', 'other'}:
        return TYPE_OTHER
    return str(tipo) if str(tipo or '').strip() else TYPE_OTHER


def is_failure_demand_type(tipo):
    return canonicalize_demand_type(tipo) == TYPE_ISSUES


def parse_json_env(name, default):
    raw = os.getenv(name, '').strip()
    if not raw:
        return default
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else default
    except json.JSONDecodeError:
        return default


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


def _load_person_alias_index():
    raw = os.getenv('FLOW_PMO_PERSON_ALIAS_MAP', '').strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}

    alias_index = {}

    def _iter_aliases(value):
        if isinstance(value, list):
            for item in value:
                yield item
            return
        if isinstance(value, str):
            for part in re.split(r'[|,;]', value):
                yield part

    for canonical_name, aliases in parsed.items():
        canonical = _normalize_person_name(canonical_name)
        if not canonical:
            continue
        for candidate in [canonical_name, canonical, *_iter_aliases(aliases)]:
            person_key = _person_match_key(candidate)
            if person_key:
                alias_index[person_key] = canonical
            email_key = _person_email_key(candidate)
            if email_key:
                alias_index[email_key] = canonical
    return alias_index


def _person_email_key(raw_name):
    if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
        return ''
    text = str(raw_name).strip().lower()
    if not text:
        return ''
    match = re.search(r'([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})', text)
    if match:
        return match.group(1).strip()
    return ''


def _person_match_key(raw_name):
    normalized = normalize_text(_normalize_person_name(raw_name))
    if not normalized:
        return ''
    normalized = re.sub(r'[^a-z0-9]+', ' ', normalized).strip()
    return re.sub(r'\s+', ' ', normalized)


def _canonical_person_name(raw_name, alias_index=None):
    fallback = _normalize_person_name(raw_name)
    if not fallback:
        return ''
    alias_index = alias_index if isinstance(alias_index, dict) else _load_person_alias_index()
    for key in (_person_match_key(raw_name), _person_email_key(raw_name)):
        if key and key in alias_index:
            return alias_index[key]
    return fallback


def _normalize_seniority_bucket(raw_value):
    text = normalize_text(raw_value)
    if not text:
        return 'Nao classificado'
    if ('senior' in text) or ('sr' == text) or (' s r ' in f" {text} "):
        return 'Senior'
    if ('junior' in text) or ('jr' == text) or (' j r ' in f" {text} "):
        return 'Junior'
    return 'Outros'


def _load_person_seniority_index(alias_index=None):
    raw = os.getenv('FLOW_PMO_PERSON_SENIORITY_MAP', '').strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}

    alias_index = alias_index if isinstance(alias_index, dict) else _load_person_alias_index()
    out = {}
    for person_name, seniority in parsed.items():
        person = _canonical_person_name(person_name, alias_index=alias_index)
        if not person:
            continue
        out[person] = _normalize_seniority_bucket(seniority)
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
    candidates = []
    for folder in DATA_FOLDERS:
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


def _normalize_person_name(raw_name):
    if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
        return ''
    name = str(raw_name).strip()
    if not name or name.lower() in {'nan', 'none'}:
        return ''
    if '<' in name:
        name = name.split('<', 1)[0].strip()
    return re.sub(r'\s+', ' ', name).strip()


def _split_people_field(raw_value):
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return []
    text = str(raw_value).strip()
    if not text or text.lower() in {'nan', 'none'}:
        return []
    out = []
    for part in text.split('|'):
        person = _normalize_person_name(part)
        if person:
            out.append(person)
    return out


def compute_bitbucket_contributor_metrics(bitbucket_logs, start_ts, end_ts, alias_index=None):
    commits = bitbucket_logs.get('commits', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    pullrequests = bitbucket_logs.get('pullrequests', pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    stats = {}

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
            }
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
            for approver in _split_people_field(row.get('approved_by')):
                person_key = _ensure_person(approver)
                if person_key:
                    stats[person_key]['Aprovacoes'] += 1
            for rejector in _split_people_field(row.get('changes_requested_by')):
                person_key = _ensure_person(rejector)
                if person_key:
                    stats[person_key]['Reprovacoes'] += 1

    if not stats:
        return pd.DataFrame(), {}

    df_metrics = pd.DataFrame(stats.values())
    df_metrics['Total Contribuicoes'] = (
        df_metrics['PRs Abertos'] +
        df_metrics['Aprovacoes'] +
        df_metrics['Reprovacoes'] +
        df_metrics['PRs Declinados (Autor)'] +
        df_metrics['Commits']
    )
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
    }


def compute_jira_person_capacity_metrics(jira_df, start_ts, end_ts, alias_index=None):
    if jira_df is None or jira_df.empty:
        return pd.DataFrame(), {}
    required = {'Responsavel', 'DataInProgress', 'DataDone'}
    if not required.issubset(jira_df.columns):
        return pd.DataFrame(), {}

    df = jira_df.copy()
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
            done_window['Pessoa'] = done_window['Responsavel'].apply(
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
        jira_done['Pessoa'] = jira_done['Responsavel'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
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
        focus_people.add(str(responsavel))
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
            done_cases = done_cases[done_cases['Done Final Author'].astype(str) == str(responsavel)]
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


def load_env_file(env_file):
    p = os.path.join(os.path.dirname(__file__), env_file)
    if not os.path.exists(p):
        return
    try:
        with open(p, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()
    except Exception:
        return


def load_pattern_rules():
    return parse_json_env("PATTERN_RULES", parse_json_env("JIRA_PATTERN_RULES", DEFAULT_PATTERN_RULES))


load_env_file('jira_env.txt')
load_env_file('jira-env.txt')
PATTERN_RULES = load_pattern_rules()
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
    text = normalize_text(value)
    return any(token in text for token in ['expedite', 'urgent', 'urgente', 'critical', 'critico', 'fast track', 'fasttrack', 'highest', 'higest'])


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
        'Projeto', 'Semana', 'Padrão', 'Severidade', 'Regras Acionadas', 'Expedite (%)',
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
        project_groups = [('Todos os projetos', df_source.copy())]

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
            expedite_arrivals = len(arrivals[arrivals['ClasseServico'] == 'Expedite']) if 'ClasseServico' in arrivals.columns else 0
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
                    'Expedite (%)': round(signals['expedite_pct'], 2),
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
            'Indicador': '% de entradas em Expedite',
            'Observado': f"{arrivals_pct:.1f}%" if pd.notna(arrivals_pct) else 'Sem base',
            'Regra': f"OK <= {expedite_target:.1f}% | Crítico > {expedite_critical:.1f}%",
            'Status': policy_status,
            'Leitura': (
                'Uso de expedite dentro da política.'
                if policy_status == 'OK' else
                'Expedite acima da meta; revisar critérios de fast track.'
                if policy_status == 'Atenção' else
                'Expedite dominando a entrada; risco de canibalizar fluxo normal.'
                if policy_status == 'Crítico' else
                'Sem base suficiente para política de expedite.'
            ),
        },
        {
            'Indicador': '% de throughput em Expedite',
            'Observado': f"{throughput_pct:.1f}%" if pd.notna(throughput_pct) else 'Sem base',
            'Regra': 'Monitorar desbalanceamento entre urgente e fluxo normal',
            'Status': 'OK' if pd.notna(throughput_pct) and throughput_pct <= expedite_target else ('Atenção' if pd.notna(throughput_pct) and throughput_pct <= expedite_critical else 'Crítico' if pd.notna(throughput_pct) else 'Sem base'),
            'Leitura': 'Usar como proxy de quanto da capacidade está sendo consumida por urgências.',
        },
        {
            'Indicador': 'Itens Expedite em aberto',
            'Observado': f"{int(len(expedite_open))} itens",
            'Regra': 'Preferir fila urgente curta e envelhecimento baixo',
            'Status': 'OK' if len(expedite_open) <= 2 else 'Atenção' if len(expedite_open) <= 5 else 'Crítico',
            'Leitura': 'Itens urgentes abertos demais indicam fast track virando estoque em vez de exceção.',
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
                'portfolio_technical_readiness_notes': pd.DataFrame(),
                'portfolio_technical_epic_summary': pd.DataFrame(),
                'portfolio_technical_items_catalog': pd.DataFrame(),
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
    if 'Team' not in df.columns:
        df['Team'] = ''
    for col in ['ParentTitle', 'HierarchyLinkSource', 'FeatureLinkID', 'FeatureLinkTipo', 'EpicLinkID', 'EpicLinkTipo', 'EpicLinkName', 'Componentes', 'Etiquetas', 'IssueLinkKeys', 'IssueLinkTypes', 'IssueLinkDetails']:
        if col not in df.columns:
            df[col] = ''

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
        portfolio_alert_kpis = pd.DataFrame([
            {'Indicador': 'Ocorrências críticas', 'Valor': int(severity_counts.get('Critico', 0))},
            {'Indicador': 'Ocorrências alerta', 'Valor': int(severity_counts.get('Alerta', 0))},
            {'Indicador': 'Ocorrências monitorar', 'Valor': int(severity_counts.get('Monitorar', 0))},
            {'Indicador': 'Itens únicos com alerta', 'Valor': int(portfolio_alerts_detail['ItemID'].nunique())},
            {'Indicador': 'Épicos sem feature', 'Valor': int(type_counts.get('Épico sem feature', 0))},
            {'Indicador': 'Features sem story/task', 'Valor': int(type_counts.get('Feature sem story/task', 0))},
            {'Indicador': 'Itens vencidos', 'Valor': int(type_counts.get('Item vencido', 0))},
            {'Indicador': 'Itens vencendo em até 7d', 'Valor': int(len(upcoming_items[upcoming_items['DiasParaVencimento'] <= 7])) if not upcoming_items.empty else 0},
            {'Indicador': 'Épicos sem arquitetura', 'Valor': int(type_counts.get('Épico sem item técnico de arquitetura', 0))},
            {'Indicador': 'Épicos sem infra', 'Valor': int(type_counts.get('Épico sem item técnico de infra', 0))},
            {'Indicador': 'Épicos sem segurança', 'Valor': int(type_counts.get('Épico sem item técnico de seguranca', 0)) + int(type_counts.get('Épico sem item técnico de segurança', 0))},
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
            'portfolio_technical_readiness_notes': portfolio_technical_readiness_notes,
            'portfolio_technical_epic_summary': portfolio_technical_epic_summary,
            'portfolio_technical_items_catalog': technical_items_catalog,
            'has_us_items': has_us_items,
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
        return _download_portfolio_csv_from_url(csv_url)

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


def render_portfolio_roadmap_quarter_view(df_source, selected_quarter='ALL'):
    if df_source is None or df_source.empty:
        return html.Div([
            html.H4('One Page - Roadmap 2026', style={'margin': '0 0 6px 0'}),
            html.P('Sem itens de portfólio para montar o roadmap por quarter.', style={'margin': 0, 'color': '#666'})
        ], style={'marginBottom': '18px'})

    df = df_source.copy()
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
    if 'TipoNorm' not in df.columns and 'Tipo' in df.columns:
        df['TipoNorm'] = df['Tipo'].map(normalize_text)
    if 'TipoNorm' in df.columns:
        df = df[df['TipoNorm'].isin({'epico', 'epic'})].copy()
    if df.empty:
        return html.Div([
            html.H4('One Page Completo - Roadmap 2026', style={'margin': '0 0 6px 0'}),
            html.P('Nenhum épico encontrado no recorte atual.', style={'margin': 0, 'color': '#666'})
        ], style={'marginBottom': '18px'})

    df['RoadmapQuarter'] = df['DueDate'].apply(portfolio_quarter_label_from_date) if 'DueDate' in df.columns else None
    df = df[df['RoadmapQuarter'].isin(PORTFOLIO_ROADMAP_QUARTERS_2026)].copy()
    if selected_quarter in PORTFOLIO_ROADMAP_QUARTERS_2026:
        df = df[df['RoadmapQuarter'] == selected_quarter].copy()
    if df.empty:
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
    if 'DueDate' in df.columns:
        df['DueDate'] = pd.to_datetime(df['DueDate'], errors='coerce')

    legend_counts = (
        df['RoadmapStatus']
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

    quarter_columns = []
    for quarter in PORTFOLIO_ROADMAP_QUARTERS_2026:
        q_df = df[df['RoadmapQuarter'] == quarter].copy()
        if not q_df.empty:
            q_df = q_df.sort_values(['DueDate', 'Titulo'], ascending=[True, True], ignore_index=True)
        if q_df.empty:
            quarter_columns.append(
                html.Div([
                    html.Div(quarter, style={'fontWeight': 'bold', 'fontSize': '22px', 'color': '#3e6166', 'marginBottom': '10px'}),
                    html.Div('Sem épicos', style={'fontSize': '13px', 'color': '#666', 'fontStyle': 'italic'})
                ], style={'padding': '12px', 'border': '1px solid #d8e1e3', 'borderRadius': '6px', 'minHeight': '540px'})
            )
            continue

        def _render_epic_row(row):
            status = str(row.get('RoadmapStatus', 'Planning'))
            color = PORTFOLIO_ROADMAP_STATUS_COLORS.get(status, '#d9d9d9')
            pct = row.get('RoadmapProgressPct')
            pct_valid = pd.notna(pct)
            pct_label = f"{int(pct)}%" if pct_valid else 'N/D'
            is_high = bool(row.get('IsHighestPriority', False))
            return html.Div([
                html.Div(
                    [
                        html.Span(str(row.get('Titulo', 'Sem título')), style={'flex': '1', 'minWidth': 0}),
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
                    title=f"{row.get('Titulo', '')} | Status: {row.get('Status', '')}" + (' | Highest' if is_high else ''),
                    style={
                        'backgroundColor': color,
                        'padding': '4px 10px',
                        'borderRadius': '0',
                        'fontSize': '15px',
                        'fontWeight': '700',
                        'lineHeight': '1.2',
                        'display': 'flex',
                        'alignItems': 'center',
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

        running_df = q_df[q_df['RoadmapStatus'] == 'Running'].copy()
        if not running_df.empty:
            running_df['_pct_sort'] = pd.to_numeric(running_df['RoadmapProgressPct'], errors='coerce').fillna(-1)
            running_df = running_df.sort_values(['_pct_sort', 'DueDate', 'Titulo'], ascending=[True, True, True], ignore_index=True)
        planning_df = q_df[q_df['RoadmapStatus'] == 'Planning'].copy().sort_values(['DueDate', 'Titulo'], ascending=[True, True], ignore_index=True)
        done_df = q_df[q_df['RoadmapStatus'] == 'Done'].copy().sort_values(['DueDate', 'Titulo'], ascending=[True, True], ignore_index=True)
        paused_df = q_df[q_df['RoadmapStatus'] == 'Paused'].copy().sort_values(['DueDate', 'Titulo'], ascending=[True, True], ignore_index=True)

        epic_rows = []
        if not running_df.empty:
            epic_rows.append(html.Div(f"Running ({int(len(running_df))})", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#1f3e46', 'margin': '4px 0'}))
            for _, row in running_df.iterrows():
                epic_rows.append(_render_epic_row(row))
        if not planning_df.empty:
            epic_rows.append(html.Div(f"Planning ({int(len(planning_df))})", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#4a3e57', 'margin': '8px 0 4px 0'}))
            for _, row in planning_df.iterrows():
                epic_rows.append(_render_epic_row(row))
        if not done_df.empty:
            epic_rows.append(html.Div(f"Done ({int(len(done_df))})", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#355427', 'margin': '8px 0 4px 0'}))
            for _, row in done_df.iterrows():
                epic_rows.append(_render_epic_row(row))
        if not paused_df.empty:
            epic_rows.append(html.Div(f"Paused ({int(len(paused_df))})", style={'fontSize': '12px', 'fontWeight': 'bold', 'color': '#6d5a29', 'margin': '8px 0 4px 0'}))
            for _, row in paused_df.iterrows():
                epic_rows.append(_render_epic_row(row))

        quarter_columns.append(
            html.Div([
                html.Div(quarter, style={'fontWeight': 'bold', 'fontSize': '22px', 'color': '#3e6166', 'marginBottom': '8px'}),
                html.Div(
                    f"Épicos: {int(len(q_df))}",
                    style={'fontSize': '12px', 'color': '#3d3d3d', 'marginBottom': '8px'}
                ),
                html.Div(
                    epic_rows,
                    style={'maxHeight': '500px', 'overflowY': 'auto'}
                ),
            ], style={'padding': '12px', 'border': '1px solid #d8e1e3', 'borderRadius': '6px', 'minHeight': '540px'})
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
                'gridTemplateColumns': 'repeat(auto-fit, minmax(300px, 1fr))',
                'gap': '10px'
            }
        )
    ], style={'marginBottom': '20px'})

def create_kpi_card(title, value, class_name='six columns', card_style=None, title_style=None, value_style=None):
    base_card_style = {'padding': '10px', 'borderRadius': '6px'}
    if isinstance(card_style, dict):
        base_card_style.update(card_style)
    base_title_style = {'textAlign': 'center'}
    if isinstance(title_style, dict):
        base_title_style.update(title_style)
    base_value_style = {'textAlign': 'center'}
    if isinstance(value_style, dict):
        base_value_style.update(value_style)
    return html.Div([
        html.H4(title, style=base_title_style),
        html.H2(value, style=base_value_style)
    ], className=class_name, style=base_card_style)

def unique_sorted(col):
    return sorted([x for x in col.dropna().unique()])


def normalize_project_filter_value(projeto):
    """Convert explicit 'all projects' selection into global scope (None)."""
    if projeto in (None, '', PROJECT_FILTER_ALL_VALUE):
        return None
    return projeto


def weekly_bucket_start(date_series):
    return date_series.dt.to_period(WEEK_PERIOD).dt.start_time


def done_time_eligible_mask(df):
    """Rows eligible for time metrics: done/completed rows without cancellation history."""
    if df is None or getattr(df, 'empty', True):
        return pd.Series(dtype=bool)
    mask = pd.Series(True, index=df.index)
    if 'ElegivelTempoConcluido' in df.columns:
        elig = pd.to_numeric(df['ElegivelTempoConcluido'], errors='coerce').fillna(0)
        mask &= elig.eq(1)
    else:
        if 'Cancelado' in df.columns:
            cancelado = pd.to_numeric(df['Cancelado'], errors='coerce').fillna(0)
            mask &= cancelado.eq(0)
        if 'DataCancelled' in df.columns:
            mask &= pd.to_datetime(df['DataCancelled'], errors='coerce').isna()
    return mask


def time_metric_series(df, column, positive_only=False, non_negative=False):
    """Numeric series for time metrics with exact eligibility filter (done without cancellation)."""
    if df is None or getattr(df, 'empty', True) or column not in df.columns:
        return pd.Series(dtype='float64')
    base = df
    if column in {'LeadTime_Dias', 'LeadTime_Selected_Dias', 'TempoExecucao_Dias', 'TempoBacklog_Dias', 'TempoBloqueioDias', 'TempoEsperaIntermediariaDias'}:
        base = df[done_time_eligible_mask(df)]
    s = pd.to_numeric(base[column], errors='coerce').dropna()
    if positive_only:
        s = s[s > 0]
    elif non_negative:
        s = s[s >= 0]
    return s


def build_lead_time_comparable_scope(df_source, lead_col='LeadTime_Selected_Dias'):
    """
    Build a canonical Lead Time scope used by both Lead Time and Estatística tabs.
    Returns: (clean_df, lt_series, lt_stats)
    """
    if df_source is None or getattr(df_source, 'empty', True):
        return pd.DataFrame(), pd.Series(dtype='float64'), {}
    if lead_col not in df_source.columns or 'DataDone' not in df_source.columns:
        return pd.DataFrame(), pd.Series(dtype='float64'), {}

    df_lt = df_source.copy()
    df_lt = df_lt[done_time_eligible_mask(df_lt)].copy()
    if df_lt.empty:
        return pd.DataFrame(), pd.Series(dtype='float64'), {}

    df_lt[lead_col] = pd.to_numeric(df_lt[lead_col], errors='coerce')
    df_lt['DataDone'] = pd.to_datetime(df_lt['DataDone'], errors='coerce')
    df_lt = df_lt.dropna(subset=[lead_col, 'DataDone']).copy()
    df_lt = df_lt[df_lt[lead_col] >= 0].sort_values('DataDone')
    if df_lt.empty:
        return pd.DataFrame(), pd.Series(dtype='float64'), {}

    lt_series = time_metric_series(df_lt, lead_col, non_negative=True)
    if lt_series.empty:
        return pd.DataFrame(), pd.Series(dtype='float64'), {}

    lt_stats = {
        'count': int(len(lt_series)),
        'mean': float(lt_series.mean()),
        'p50': float(exact_empirical_percentile(lt_series, 0.50)),
        'p75': float(exact_empirical_percentile(lt_series, 0.75)),
        'p85': float(exact_empirical_percentile(lt_series, 0.85)),
        'p95': float(exact_empirical_percentile(lt_series, 0.95)),
    }
    return df_lt, lt_series, lt_stats


def unique_item_keys(df):
    """Return deduplication keys preserving project context when available."""
    keys = []
    if df is not None and 'Projeto' in df.columns:
        keys.append('Projeto')
    if df is not None and 'ItemID' in df.columns:
        keys.append('ItemID')
    return keys


def build_delivered_items_base(df_source, lead_time_col=None):
    """
    Standard delivered-items base used across tabs:
    - done in current filtered scope (DataDone not null)
    - eligible done items (no cancellation history)
    - deduplicated by Projeto+ItemID (or ItemID)
    - optional valid lead-time filter when lead_time_col is provided
    """
    if df_source is None or getattr(df_source, 'empty', True):
        return pd.DataFrame(columns=getattr(df_source, 'columns', []))

    out = df_source.dropna(subset=['DataDone']).copy() if 'DataDone' in df_source.columns else df_source.copy()
    if out.empty:
        return out

    out = out[done_time_eligible_mask(out)].copy()
    if out.empty:
        return out

    if lead_time_col and lead_time_col in out.columns:
        out[lead_time_col] = pd.to_numeric(out[lead_time_col], errors='coerce')
        out = out.dropna(subset=[lead_time_col])
        out = out[out[lead_time_col] >= 0]
        if out.empty:
            return out

    dedup_keys = unique_item_keys(out)
    if dedup_keys:
        out = out.drop_duplicates(subset=dedup_keys, keep='first')
    return out


def exact_empirical_percentile(values, q):
    """Nearest-rank empirical percentile (no interpolation)."""
    s = pd.Series(values).dropna()
    if s.empty:
        return np.nan
    q = float(q)
    if q <= 0:
        return float(s.min())
    if q >= 1:
        return float(s.max())
    ordered = s.sort_values().reset_index(drop=True)
    rank = max(1, min(len(ordered), math.ceil(q * len(ordered))))
    return float(ordered.iloc[rank - 1])


def exact_percentile_map(values, quantiles):
    return {q: exact_empirical_percentile(values, q) for q in quantiles}


def fit_weibull_linearized(values):
    """
    2-parameter Weibull fit via linearized Weibull plot (same method as LT_STATS_WEIBULL.xlsx):
    F(i) = (2i - 1) / (2n), y = ln(-ln(1-F)), x = ln(t), then linear regression y = k*x + b.
    lambda = exp(-b/k)
    """
    s = pd.to_numeric(pd.Series(values), errors='coerce').dropna()
    s = s[s > 0].sort_values().reset_index(drop=True)
    n = int(len(s))
    if n < 2:
        return None

    i = np.arange(1, n + 1, dtype=float)
    f = (2.0 * i - 1.0) / (2.0 * n)
    x = np.log(s.to_numpy(dtype=float))
    y = np.log(-np.log(1.0 - f))

    slope, intercept = np.polyfit(x, y, 1)
    if not np.isfinite(slope) or abs(float(slope)) < 1e-12:
        return None
    weibull_lambda = math.exp(-float(intercept) / float(slope))
    if not np.isfinite(weibull_lambda):
        return None

    return {
        'shape': float(slope),
        'lambda': float(weibull_lambda),
        'n': n,
    }


def exact_percentile_band_summary(values, cutoffs=(0.50, 0.70, 0.85, 0.95)):
    """Build exact percentile-band summary using nearest-rank cumulative positions."""
    s = pd.Series(values).dropna().sort_values().reset_index(drop=True)
    if s.empty:
        return pd.DataFrame(columns=['Percentile band', 'Items in range', 'Cumulative items', 'Cycle Time (Days)'])
    n = len(s)
    cutoffs = [float(c) for c in cutoffs]
    cum_counts = [max(0, min(n, math.ceil(c * n))) for c in cutoffs] + [n]
    # enforce monotonicity
    for i in range(1, len(cum_counts)):
        cum_counts[i] = max(cum_counts[i], cum_counts[i - 1])
    labels = ['0-50%', '51-70%', '71-85%', '86-95%', '95%+']
    thresholds = [exact_empirical_percentile(s, c) for c in cutoffs] + [float(s.max())]
    ranges = []
    prev = 0
    for c in cum_counts:
        ranges.append(c - prev)
        prev = c
    return pd.DataFrame({
        'Percentile band': labels,
        'Items in range': ranges,
        'Cumulative items': cum_counts,
        'Cycle Time (Days)': [int(round(x)) if pd.notna(x) else None for x in thresholds],
    })

def add_statistical_lines(fig, x_values, y_values, name_prefix='', secondary_y=None):
    """Adiciona linhas de percentil 15, 85, 95, média e média móvel (5 períodos) a um gráfico de tendência."""
    y_series = pd.Series(y_values.values if hasattr(y_values, 'values') else y_values).dropna()
    if y_series.empty:
        return fig
    p15 = exact_empirical_percentile(y_series, 0.15)
    p85 = exact_empirical_percentile(y_series, 0.85)
    p95 = exact_empirical_percentile(y_series, 0.95)
    mean_val = y_series.mean()
    ma5 = y_series.rolling(5, min_periods=1).mean()
    kwargs = {}
    if secondary_y is not None:
        kwargs['secondary_y'] = secondary_y
    x_list = list(x_values)
    fig.add_trace(go.Scatter(x=x_list, y=[p15]*len(x_list), mode='lines', name=f'{name_prefix}P15',
                             line=dict(dash='dot', width=1, color='gray')), **kwargs)
    fig.add_trace(go.Scatter(x=x_list, y=[p85]*len(x_list), mode='lines', name=f'{name_prefix}P85',
                             line=dict(dash='dash', width=1.5, color='orange')), **kwargs)
    fig.add_trace(go.Scatter(x=x_list, y=[p95]*len(x_list), mode='lines', name=f'{name_prefix}P95',
                             line=dict(dash='dash', width=1.5, color='red')), **kwargs)
    fig.add_trace(go.Scatter(x=x_list, y=[mean_val]*len(x_list), mode='lines', name=f'{name_prefix}Média',
                             line=dict(dash='solid', width=1.5, color='blue')), **kwargs)
    fig.add_trace(go.Scatter(x=x_list, y=list(ma5), mode='lines', name=f'{name_prefix}MM(5)',
                             line=dict(dash='solid', width=2, color='purple')), **kwargs)
    return fig


def compute_process_capability_metrics(values, lsl=None, usl=None):
    series = pd.to_numeric(pd.Series(values), errors='coerce').dropna()
    result = {
        'count': int(len(series)),
        'lsl': float(lsl) if pd.notna(lsl) else np.nan,
        'usl': float(usl) if pd.notna(usl) else np.nan,
        'mean': np.nan,
        'std': np.nan,
        'cpu': np.nan,
        'cpl': np.nan,
        'cpk': np.nan,
        'sigma_short': np.nan,
        'sigma_long': np.nan,
        'quality': 'Sem classificação',
        'error': None,
    }

    if series.empty:
        result['error'] = 'Sem dados suficientes para calcular Cpk e Nível Sigma.'
        return result
    if result['count'] < 2:
        result['error'] = 'São necessários pelo menos 2 pontos para calcular desvio padrão amostral.'
        return result
    if not np.isfinite(result['lsl']) and not np.isfinite(result['usl']):
        result['error'] = 'Informe ao menos um limite de especificação (LSL ou USL).'
        return result
    if np.isfinite(result['lsl']) and np.isfinite(result['usl']) and result['lsl'] >= result['usl']:
        result['error'] = 'LSL deve ser menor que USL.'
        return result

    mean = float(series.mean())
    std = float(series.std(ddof=1))
    result['mean'] = mean
    result['std'] = std
    if not np.isfinite(std) or std <= 0:
        result['error'] = 'Desvio padrão inválido (zero ou não finito) para cálculo de capabilidade.'
        return result

    if np.isfinite(result['usl']):
        result['cpu'] = (result['usl'] - mean) / (3.0 * std)
    if np.isfinite(result['lsl']):
        result['cpl'] = (mean - result['lsl']) / (3.0 * std)

    candidates = [v for v in [result['cpu'], result['cpl']] if np.isfinite(v)]
    if not candidates:
        result['error'] = 'Não foi possível calcular CPU/CPL com os limites informados.'
        return result

    cpk = float(min(candidates))
    result['cpk'] = cpk
    result['sigma_short'] = cpk * 3.0
    result['sigma_long'] = (cpk * 3.0) - 1.5

    if cpk < 1.0:
        result['quality'] = 'Incapaz (Cpk < 1.00)'
    elif cpk < 1.33:
        result['quality'] = 'Apenas capaz (1.00 ≤ Cpk < 1.33)'
    elif cpk < 2.0:
        result['quality'] = 'Bom (1.33 ≤ Cpk < 2.00)'
    else:
        result['quality'] = 'Classe Seis Sigma (Cpk ≥ 2.00)'

    return result


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
        if any(k in classe_servico for k in ['expedite', 'urgente', 'urgent', 'critical', 'critico']):
            return 'Urgente'
        if any(k in classe_servico for k in ['fixed date', 'fixed_date', 'deadline', 'prazo', 'data fixa']):
            return 'Data Fixa'
        if any(k in classe_servico for k in ['intang', 'risco', 'risk', 'compliance', 'regulatorio', 'regulatory']):
            return 'Intangível'
        if any(k in classe_servico for k in ['standard', 'padrao', 'normal', 'default']):
            return 'Padrão'
        return str(row.get('ClasseServico'))

    if prioridade:
        if any(k in prioridade for k in ['blocker', 'critical', 'highest', 'high', 'alta', 'urgente', 'critica']):
            return 'Urgente'
        if any(k in prioridade for k in ['medium', 'media', 'normal']):
            return 'Média'
        if any(k in prioridade for k in ['low', 'lowest', 'baixa']):
            return 'Baixa'
        return str(row.get('Prioridade'))

    return 'Não classificado'


def build_throughput_breakdown(df, dimension_col, dimension_label):
    """Monta DataFrame com contagem e percentual para breakdown de throughput."""
    if df.empty or dimension_col not in df.columns:
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
    if total > 0:
        breakdown['Percentual'] = (breakdown['Throughput'] / total) * 100
    else:
        breakdown['Percentual'] = 0.0
    breakdown['Barra'] = dimension_label
    return breakdown

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
        if t in {'story', 'user story', 'historia', 'historia de usuario', 'us', 'task', 'tarefa', 'subtarefa', 'sub task', 'tech task', 'task de produto'}:
            return True
        return ('historia' in t) or ('task' in t)

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


def _find_latest_w1nner_process_mining_excel():
    report_url = os.getenv('FLOW_PMO_PROCESS_MINING_REPORT_URL', '').strip()
    if report_url:
        try:
            return _download_process_mining_report_from_url(report_url)
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
        dt.loc[dt_ddmmyyyy.index] = dt_ddmmyyyy

    num = pd.to_numeric(raw, errors='coerce')
    if num.notna().any():
        num_int = num.dropna().astype('Int64').astype(str).str.strip()
        looks_yyyymmdd = num_int.str.fullmatch(r'\d{8}')
        if looks_yyyymmdd.any():
            parsed = pd.to_datetime(num_int.where(looks_yyyymmdd), format='%Y%m%d', errors='coerce')
            dt.loc[parsed.index] = parsed
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


ONE_PAGE_THEME = {
    'bg': '#0f1117',
    'surface': '#1a1d27',
    'surface_2': '#232734',
    'border': '#2e3345',
    'text': '#e2e8f0',
    'muted': '#8892a8',
    'green': '#22c55e',
    'amber': '#f59e0b',
    'red': '#ef4444',
    'teal': '#14b8a6',
    'accent': '#3b82f6',
}


def _one_page_status_color(status):
    return {
        'good': ONE_PAGE_THEME['green'],
        'warn': ONE_PAGE_THEME['amber'],
        'bad': ONE_PAGE_THEME['red'],
        'info': ONE_PAGE_THEME['accent'],
    }.get(status, ONE_PAGE_THEME['accent'])


def _one_page_fmt(value, pattern='{:.1f}', empty='—'):
    try:
        if value is None or pd.isna(value):
            return empty
        return pattern.format(value)
    except Exception:
        return empty


def _one_page_health_card(value, label, sublabel, status):
    color = _one_page_status_color(status)
    return html.Div(
        [
            html.Div(
                str(value),
                style={'fontFamily': 'JetBrains Mono, monospace', 'fontSize': '24px', 'fontWeight': '600', 'color': color, 'lineHeight': '1.1'}
            ),
            html.Div(label.upper(), style={'fontSize': '10px', 'letterSpacing': '0.8px', 'marginTop': '4px', 'color': ONE_PAGE_THEME['muted']}),
            html.Div(sublabel, style={'fontSize': '9px', 'marginTop': '3px', 'color': '#5a6478'}),
        ],
        style={
            'backgroundColor': ONE_PAGE_THEME['surface'],
            'border': f"1px solid {ONE_PAGE_THEME['border']}",
            'borderTop': f"3px solid {color}",
            'borderRadius': '8px',
            'padding': '12px 12px',
            'minHeight': '92px',
            'textAlign': 'center',
        }
    )


def _one_page_dimension_row(label, value_text, width_pct, status):
    color = _one_page_status_color(status)
    width = max(0, min(100, float(width_pct)))
    return html.Div(
        [
            html.Div(label, style={'color': ONE_PAGE_THEME['muted'], 'fontSize': '11px', 'fontWeight': '500'}),
            html.Div(
                html.Div(style={'height': '100%', 'width': f'{width:.1f}%', 'backgroundColor': color, 'borderRadius': '999px'}),
                style={'height': '8px', 'backgroundColor': ONE_PAGE_THEME['surface_2'], 'borderRadius': '999px'}
            ),
            html.Div(value_text, style={'fontFamily': 'JetBrains Mono, monospace', 'fontSize': '11px', 'fontWeight': '600', 'color': color, 'textAlign': 'right'}),
        ],
        style={'display': 'grid', 'gridTemplateColumns': '160px 1fr 72px', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '7px'}
    )


def _one_page_status_by_threshold(metric_key, value, context=None):
    if value is None or pd.isna(value):
        return 'info'
    ctx = context or {}
    v = float(value)
    if metric_key == 'throughput':
        prev = ctx.get('prev')
        if prev is None or pd.isna(prev) or float(prev) <= 0:
            return 'info'
        drop = (float(prev) - v) / float(prev)
        if drop <= 0:
            return 'good'
        if drop <= 0.20:
            return 'warn'
        return 'bad'
    if metric_key == 'pressure':
        if v < 0.85:
            return 'good'
        if v < 1.0:
            return 'warn'
        return 'bad'
    if metric_key == 'lead_ratio':
        if v <= 1.0:
            return 'good'
        if v <= 1.5:
            return 'warn'
        return 'bad'
    if metric_key == 'conformance':
        if v > 50:
            return 'good'
        if v >= 20:
            return 'warn'
        return 'bad'
    if metric_key == 'coverage':
        if v > 60:
            return 'good'
        if v >= 30:
            return 'warn'
        return 'bad'
    if metric_key == 'rework':
        if v < 5:
            return 'good'
        if v <= 15:
            return 'warn'
        return 'bad'
    if metric_key == 'utilization':
        if v < 6.5:
            return 'good'
        if v <= 7.5:
            return 'warn'
        return 'bad'
    if metric_key == 'pr_no_approval':
        if v < 20:
            return 'good'
        if v <= 50:
            return 'warn'
        return 'bad'
    if metric_key == 'tp_inflation':
        if v < 3:
            return 'good'
        if v <= 7:
            return 'warn'
        return 'bad'
    return 'info'


def build_dynamic_one_page_report(projeto, tipo, classe_servico, responsavel, start_ts, end_ts, leadtime_stages):
    scope = fato.copy()
    if projeto:
        scope = scope[scope['Projeto'] == projeto]
    if tipo:
        scope = scope[scope['TipoDemanda'] == tipo]
    if classe_servico:
        scope = scope[scope['ClasseServico'] == classe_servico]
    if responsavel:
        scope = scope[scope['Responsavel'] == responsavel]
    scope, _ = apply_selected_lead_time_metric(scope, projeto, leadtime_stages)

    if scope.empty:
        return html.Div(
            'Sem dados para gerar One Page com os filtros atuais.',
            style={'padding': '16px', 'border': '1px dashed #d1d5db', 'borderRadius': '10px'}
        )

    done_period = scope[(scope['DataDone'] >= start_ts) & (scope['DataDone'] <= end_ts)].copy()
    done_eligible = done_period[done_time_eligible_mask(done_period)].copy() if not done_period.empty else done_period

    lead_start_col = 'LeadStart_Selected' if 'LeadStart_Selected' in scope.columns else 'DataInProgress'
    start_series = pd.to_datetime(scope.get(lead_start_col), errors='coerce')
    arrivals_period = scope[(start_series >= start_ts) & (start_series <= end_ts)].copy()

    days_span = max(1, int((end_ts.normalize() - start_ts.normalize()).days + 1))
    prev_start = start_ts - pd.Timedelta(days=days_span)
    prev_end = start_ts - pd.Timedelta(days=1)
    prev_done = scope[(scope['DataDone'] >= prev_start) & (scope['DataDone'] <= prev_end)].copy()
    prev_done_eligible = prev_done[done_time_eligible_mask(prev_done)].copy() if not prev_done.empty else prev_done

    throughput = int(len(done_eligible))
    throughput_prev = int(len(prev_done_eligible)) if prev_done_eligible is not None else 0
    rho = (len(arrivals_period) / throughput) if throughput > 0 else np.nan
    lead_series = time_metric_series(done_eligible, 'LeadTime_Selected_Dias', non_negative=True)
    lead_median = exact_empirical_percentile(lead_series, 0.50) if not lead_series.empty else np.nan
    lead_p85 = exact_empirical_percentile(lead_series, 0.85) if not lead_series.empty else np.nan

    sla_default = 8.0
    try:
        sla_default = float(os.getenv('FLOW_PMO_ONE_PAGE_SLA_DAYS', '8'))
    except Exception:
        sla_default = 8.0
    sla_map = parse_json_env('FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP', {})
    sla_days = sla_default
    if projeto:
        try:
            sla_days = float(sla_map.get(str(projeto).upper(), sla_default))
        except Exception:
            sla_days = sla_default
    lead_ratio = (lead_median / sla_days) if pd.notna(lead_median) and sla_days > 0 else np.nan

    bitbucket_logs = load_project_bitbucket_logs(projeto) if projeto else {'commits': pd.DataFrame(), 'pullrequests': pd.DataFrame(), 'pipelines': pd.DataFrame()}
    _, cross_totals, _ = compute_cross_source_capacity_metrics(scope, bitbucket_logs, start_ts, end_ts)
    completed_items = int(cross_totals.get('Itens Concluidos', 0))
    with_tech = int(cross_totals.get('Itens com Evidencia Tecnica', 0))
    coverage_pct = (with_tech / completed_items * 100.0) if completed_items > 0 else np.nan

    pr_df = bitbucket_logs.get('pullrequests', pd.DataFrame())
    pr_no_approval_pct = np.nan
    merged_prs = pd.DataFrame()
    if pr_df is not None and not pr_df.empty:
        if 'updated_on' in pr_df.columns:
            merged_prs = pr_df[(pr_df['updated_on'] >= start_ts) & (pr_df['updated_on'] <= end_ts)].copy()
        elif 'created_on' in pr_df.columns:
            merged_prs = pr_df[(pr_df['created_on'] >= start_ts) & (pr_df['created_on'] <= end_ts)].copy()
        else:
            merged_prs = pr_df.copy()
        if 'state_norm' in merged_prs.columns:
            merged_prs = merged_prs[merged_prs['state_norm'] == 'merged']
        if not merged_prs.empty:
            if 'reviewers_approved_count' in merged_prs.columns:
                approved_count = pd.to_numeric(merged_prs['reviewers_approved_count'], errors='coerce').fillna(0)
                no_approval = int((approved_count <= 0).sum())
            elif 'approved_by' in merged_prs.columns:
                no_approval = int(merged_prs['approved_by'].fillna('').astype(str).str.strip().eq('').sum())
            else:
                no_approval = 0
            pr_no_approval_pct = (no_approval / len(merged_prs) * 100.0) if len(merged_prs) > 0 else np.nan

    utilization_h_day = np.nan
    active_people = int(done_eligible['Responsavel'].dropna().nunique()) if 'Responsavel' in done_eligible.columns else 0
    if active_people > 0:
        exec_days = float(time_metric_series(done_eligible, 'TempoExecucao_Dias', non_negative=True).sum())
        workdays = max(int(np.busday_count(start_ts.date(), (end_ts + pd.Timedelta(days=1)).date())), 1)
        utilization_h_day = (exec_days * 8.0) / float(active_people * workdays)

    conformance_pct = np.nan
    rework_pct = np.nan
    tp_inflation = np.nan
    pm_people = pd.DataFrame()
    pm_cases = pd.DataFrame()
    is_w1nner = normalize_text(projeto) in {'w1nner', 'w1nnr'} if projeto else False
    if is_w1nner:
        _, pm_report = load_w1nner_process_mining_report()
        pm_cases = pm_report.get('ConformidadeCasos', pd.DataFrame()).copy()
        pm_people = pm_report.get('VazaoPessoaResumo', pd.DataFrame()).copy()
        if not pm_cases.empty:
            if 'Done Final Date' in pm_cases.columns:
                pm_cases['Done Final Date'] = pd.to_datetime(pm_cases['Done Final Date'], errors='coerce')
                pm_cases = pm_cases[
                    pm_cases['Done Final Date'].isna() |
                    ((pm_cases['Done Final Date'] >= start_ts) & (pm_cases['Done Final Date'] <= end_ts))
                ]
            if responsavel and 'Done Final Author' in pm_cases.columns:
                pm_cases = pm_cases[pm_cases['Done Final Author'].astype(str) == str(responsavel)]
            if tipo and 'Tipo de Problema' in pm_cases.columns:
                pm_cases = pm_cases[pm_cases['Tipo de Problema'].astype(str).map(normalize_text) == normalize_text(tipo)]

            if 'Conforme Basico' in pm_cases.columns:
                conf_bool = pd.to_numeric(pm_cases['Conforme Basico'], errors='coerce').fillna(0)
                conformance_pct = float(conf_bool.mean() * 100.0) if not conf_bool.empty else np.nan
            elif 'Conformance Score' in pm_cases.columns:
                conf_score = pd.to_numeric(pm_cases['Conformance Score'], errors='coerce').dropna()
                conformance_pct = float(conf_score.mean() * 100.0) if not conf_score.empty else np.nan

            if 'Rework Score' in pm_cases.columns and len(pm_cases) > 0:
                rw = pd.to_numeric(pm_cases['Rework Score'], errors='coerce').fillna(0)
                rework_pct = float((rw > 0).sum() / len(pm_cases) * 100.0)

            if 'Eventos' in pm_cases.columns and len(pm_cases) > 0:
                eventos_total = pd.to_numeric(pm_cases['Eventos'], errors='coerce').fillna(0).sum()
                tp_inflation = float(eventos_total / max(len(pm_cases), 1))

    value_count = int(done_eligible['TipoDemanda'].map(lambda x: canonicalize_demand_type(x) == TYPE_DEV).sum()) if 'TipoDemanda' in done_eligible.columns else 0
    execution_count = int(done_eligible['TipoDemanda'].map(lambda x: canonicalize_demand_type(x) in {TYPE_ISSUES, TYPE_SUPPORT}).sum()) if 'TipoDemanda' in done_eligible.columns else 0
    val_exec_ratio = (value_count / execution_count) if execution_count > 0 else np.nan

    health_cards = [
        _one_page_health_card(
            throughput,
            'Throughput',
            f"{throughput_prev} no período anterior",
            _one_page_status_by_threshold('throughput', throughput, {'prev': throughput_prev}),
        ),
        _one_page_health_card(_one_page_fmt(rho, '{:.2f}'), 'Pressão (ρ)', 'λ/μ (chegada/vazão)', _one_page_status_by_threshold('pressure', rho)),
        _one_page_health_card(
            f"{_one_page_fmt(lead_median, '{:.1f}')}/{_one_page_fmt(lead_p85, '{:.1f}')}",
            'Lead Time',
            f"mediana/p85 | SLA {sla_days:.0f}d",
            _one_page_status_by_threshold('lead_ratio', lead_ratio),
        ),
        _one_page_health_card(_one_page_fmt(conformance_pct, '{:.1f}%'), 'Conformidade', 'process mining', _one_page_status_by_threshold('conformance', conformance_pct)),
        _one_page_health_card(_one_page_fmt(coverage_pct, '{:.1f}%'), 'Cobertura Git', 'itens com evidência técnica', _one_page_status_by_threshold('coverage', coverage_pct)),
        _one_page_health_card(_one_page_fmt(rework_pct, '{:.1f}%'), 'Retrabalho', 'itens com reversão', _one_page_status_by_threshold('rework', rework_pct)),
    ]

    bottlenecks = compute_flow_bottlenecks(done_eligible if not done_eligible.empty else done_period)
    if bottlenecks.empty and projeto:
        bottlenecks = load_project_bottlenecks_from_model(projeto)
    if bottlenecks.empty and projeto:
        bottlenecks = load_project_bottlenecks_from_csv(projeto)
    if not bottlenecks.empty:
        bottlenecks = bottlenecks.copy().head(5)
        bottlenecks['Horas Uteis (proxy)'] = (
            pd.to_numeric(bottlenecks['Tempo Médio (dias)'], errors='coerce').fillna(0) *
            8.0 *
            pd.to_numeric(bottlenecks['Qtde Itens'], errors='coerce').fillna(0)
        ).round(1)
        max_h = max(float(bottlenecks['Horas Uteis (proxy)'].max()), 1.0)
    else:
        max_h = 1.0

    bottleneck_rows = []
    if bottlenecks.empty:
        bottleneck_rows.append(html.Div('Sem dados de gargalos para o filtro.', style={'color': ONE_PAGE_THEME['muted'], 'fontSize': '12px'}))
    else:
        for _, row in bottlenecks.iterrows():
            hours = float(row.get('Horas Uteis (proxy)', 0.0))
            med_h = float(row.get('Tempo Mediano (dias)', 0.0) * 8.0)
            sev = 'good'
            if hours >= (0.60 * max_h):
                sev = 'bad'
            elif hours >= (0.30 * max_h):
                sev = 'warn'
            sev_color = _one_page_status_color(sev)
            bottleneck_rows.append(
                html.Div(
                    [
                        html.Div(str(row.get('Etapa', '—')), style={'fontSize': '12px', 'fontWeight': '600', 'color': ONE_PAGE_THEME['text']}),
                        html.Div(
                            html.Div(style={'height': '100%', 'width': f"{(hours / max_h * 100.0):.1f}%", 'backgroundColor': sev_color, 'opacity': 0.25, 'borderRadius': '3px'}),
                            style={'height': '16px', 'backgroundColor': ONE_PAGE_THEME['surface_2'], 'borderRadius': '3px'}
                        ),
                        html.Div(_one_page_fmt(hours, '{:.1f}h'), style={'fontFamily': 'JetBrains Mono, monospace', 'fontSize': '11px'}),
                        html.Div(_one_page_fmt(med_h, '{:.1f}h'), style={'fontFamily': 'JetBrains Mono, monospace', 'fontSize': '11px'}),
                    ],
                    style={'display': 'grid', 'gridTemplateColumns': '160px 1fr 72px 72px', 'gap': '8px', 'alignItems': 'center', 'marginBottom': '8px'}
                )
            )

    dimensions_rows = [
        _one_page_dimension_row('Inflação TP', _one_page_fmt(tp_inflation, '{:.1f}x'), 0 if pd.isna(tp_inflation) else min(100, tp_inflation / 10.0 * 100.0), _one_page_status_by_threshold('tp_inflation', tp_inflation)),
        _one_page_dimension_row('Pressão de Fluxo', _one_page_fmt(rho, '{:.2f}'), 0 if pd.isna(rho) else min(100, rho / 1.5 * 100.0), _one_page_status_by_threshold('pressure', rho)),
        _one_page_dimension_row('Razão Valor/Exec', _one_page_fmt(val_exec_ratio, '{:.2f}x'), 0 if pd.isna(val_exec_ratio) else min(100, val_exec_ratio / 3.0 * 100.0), 'warn' if pd.notna(val_exec_ratio) and val_exec_ratio < 1.0 else 'good'),
        _one_page_dimension_row('Conformidade', _one_page_fmt(conformance_pct, '{:.1f}%'), 0 if pd.isna(conformance_pct) else conformance_pct, _one_page_status_by_threshold('conformance', conformance_pct)),
        _one_page_dimension_row('Cobertura Técnica', _one_page_fmt(coverage_pct, '{:.1f}%'), 0 if pd.isna(coverage_pct) else coverage_pct, _one_page_status_by_threshold('coverage', coverage_pct)),
        _one_page_dimension_row('Utilização Equipe', _one_page_fmt(utilization_h_day, '{:.1f}h/d'), 0 if pd.isna(utilization_h_day) else min(100, utilization_h_day / 10.0 * 100.0), _one_page_status_by_threshold('utilization', utilization_h_day)),
        _one_page_dimension_row('Retrabalho', _one_page_fmt(rework_pct, '{:.1f}%'), 0 if pd.isna(rework_pct) else rework_pct, _one_page_status_by_threshold('rework', rework_pct)),
        _one_page_dimension_row('PR sem Aprovação', _one_page_fmt(pr_no_approval_pct, '{:.1f}%'), 0 if pd.isna(pr_no_approval_pct) else pr_no_approval_pct, _one_page_status_by_threshold('pr_no_approval', pr_no_approval_pct)),
    ]

    findings = []
    if pd.notna(rho) and rho >= 1.0:
        findings.append(('bad', f"Sobrecarga sistêmica: rho = {rho:.2f} indica chegada acima da capacidade de entrega."))
    if pd.notna(pr_no_approval_pct) and pr_no_approval_pct > 50:
        findings.append(('bad', f"Gate fragilizado: {pr_no_approval_pct:.1f}% dos PRs merged sem aprovação formal."))
    if pd.notna(conformance_pct) and conformance_pct < 20:
        findings.append(('bad', f"Baixa conformidade processual: apenas {conformance_pct:.1f}% dos casos seguem o fluxo esperado."))
    if pd.notna(coverage_pct) and coverage_pct < 30:
        findings.append(('warn', f"Rastreabilidade técnica baixa: cobertura Git em {coverage_pct:.1f}% dos itens concluídos."))
    if pd.notna(rework_pct) and rework_pct > 15:
        findings.append(('warn', f"Retrabalho elevado: {rework_pct:.1f}% dos itens concluídos tiveram reversão."))
    if not bottlenecks.empty:
        top_stage = str(bottlenecks.iloc[0].get('Etapa', 'Etapa crítica'))
        top_hours = float(bottlenecks.iloc[0].get('Horas Uteis (proxy)', 0.0))
        findings.append(('info', f"Gargalo dominante: {top_stage} concentra {_one_page_fmt(top_hours, '{:.1f}h')} de carga útil estimada no período."))
    if not findings:
        findings.append(('info', 'Sem sinais críticos no recorte atual; manter monitoramento quinzenal.'))
    findings = findings[:5]

    finding_nodes = []
    for sev, text in findings:
        finding_nodes.append(
            html.Div(
                text,
                style={'backgroundColor': ONE_PAGE_THEME['surface_2'], 'borderLeft': f"3px solid {_one_page_status_color(sev)}", 'padding': '8px 10px', 'borderRadius': '4px', 'fontSize': '11px', 'marginBottom': '6px'}
            )
        )

    people_table = pd.DataFrame()
    if not pm_people.empty and {'Responsavel', 'Itens Concluidos'}.issubset(pm_people.columns):
        people_table = pm_people.copy()
        if responsavel:
            people_table = people_table[people_table['Responsavel'].astype(str) == str(responsavel)]
        people_table['Itens Concluidos'] = pd.to_numeric(people_table['Itens Concluidos'], errors='coerce').fillna(0)
        people_table['Itens Com Retrabalho'] = pd.to_numeric(people_table.get('Itens Com Retrabalho', 0), errors='coerce').fillna(0)
        people_table['Lead Time Mediano (dias)'] = pd.to_numeric(people_table.get('Lead Time Mediano (dias)', np.nan), errors='coerce').round(1)
        people_table['Media Itens/Semana Ativa'] = pd.to_numeric(people_table.get('Media Itens/Semana Ativa', np.nan), errors='coerce').round(2)
        people_table = people_table.sort_values('Itens Concluidos', ascending=False).head(6)
        people_table = people_table[['Responsavel', 'Itens Concluidos', 'Itens Com Retrabalho', 'Lead Time Mediano (dias)', 'Media Itens/Semana Ativa']]
    elif not done_eligible.empty and 'Responsavel' in done_eligible.columns:
        tmp = done_eligible.copy()
        tmp['Lead Time Mediano (dias)'] = pd.to_numeric(tmp.get('LeadTime_Selected_Dias'), errors='coerce')
        people_table = tmp.groupby('Responsavel', dropna=False).agg(
            **{
                'Itens Concluidos': ('ItemID', 'count'),
                'Lead Time Mediano (dias)': ('Lead Time Mediano (dias)', 'median'),
            }
        ).reset_index().sort_values('Itens Concluidos', ascending=False).head(6)
        people_table['Itens Com Retrabalho'] = np.nan
        people_table['Media Itens/Semana Ativa'] = np.nan
        people_table = people_table[['Responsavel', 'Itens Concluidos', 'Itens Com Retrabalho', 'Lead Time Mediano (dias)', 'Media Itens/Semana Ativa']]

    commits_period = 0
    prs_merged_period = 0
    approvals_period = 0
    commits_df = bitbucket_logs.get('commits', pd.DataFrame())
    if commits_df is not None and not commits_df.empty and 'date' in commits_df.columns:
        commits_period = int(len(commits_df[(commits_df['date'] >= start_ts) & (commits_df['date'] <= end_ts)]))
    if not merged_prs.empty:
        prs_merged_period = int(len(merged_prs))
        if 'reviewers_approved_count' in merged_prs.columns:
            approvals_period = int(pd.to_numeric(merged_prs['reviewers_approved_count'], errors='coerce').fillna(0).sum())
        elif 'approved_by' in merged_prs.columns:
            approvals_period = int(merged_prs['approved_by'].fillna('').astype(str).apply(lambda x: len([p for p in x.split('|') if p.strip()])).sum())

    reco_immediate = "Implementar WIP limit de entrada e rebalancear capacidade para reduzir rho abaixo de 1.0."
    if pd.notna(pr_no_approval_pct) and pr_no_approval_pct > 50:
        reco_immediate = "Configurar branch protection exigindo ao menos 1 aprovação antes de merge."
    if pd.notna(conformance_pct) and conformance_pct < 20:
        reco_immediate = "Padronizar fluxo mínimo e revisar regras de passagem para elevar conformidade acima de 20%."

    reco_short = "Tornar obrigatória a vinculação de work item em commits/PRs para elevar cobertura técnica."
    if pd.notna(coverage_pct) and coverage_pct >= 30:
        reco_short = "Reduzir variação entre etapas críticas com política pull e limites por estágio."
    reco_medium = "Formalizar classes de serviço com metas de lead time e revisão mensal dos thresholds de semáforo."

    filter_tags = []
    if tipo:
        filter_tags.append(f"Tipo: {tipo}")
    if classe_servico:
        filter_tags.append(f"Classe: {classe_servico}")
    if responsavel:
        filter_tags.append(f"Responsável: {responsavel}")

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H2(f"One Page Report - {projeto or 'Todos os Projetos'}", style={'margin': 0, 'fontSize': '24px', 'color': ONE_PAGE_THEME['text']}),
                            html.Div(
                                f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')} | Filtros: " + ('; '.join(filter_tags) if filter_tags else 'sem filtros adicionais'),
                                style={'fontSize': '11px', 'color': ONE_PAGE_THEME['muted'], 'marginTop': '3px'}
                            ),
                        ]
                    ),
                    html.Div(start_ts.strftime('%b %Y').upper(), style={'fontFamily': 'JetBrains Mono, monospace', 'fontWeight': '600', 'fontSize': '12px', 'padding': '6px 12px', 'border': f"1px solid {ONE_PAGE_THEME['border']}", 'borderRadius': '6px', 'color': ONE_PAGE_THEME['accent'], 'backgroundColor': ONE_PAGE_THEME['surface']}),
                ],
                style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'borderBottom': f"1px solid {ONE_PAGE_THEME['border']}", 'paddingBottom': '14px', 'marginBottom': '14px'}
            ),
            html.Div(health_cards, style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(150px, 1fr))', 'gap': '10px', 'marginBottom': '14px'}),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div('Ranking de Gargalos', style={'fontSize': '14px', 'fontWeight': '700', 'color': ONE_PAGE_THEME['muted'], 'textTransform': 'uppercase', 'marginBottom': '10px'}),
                            html.Div(
                                [
                                    html.Div('Etapa', style={'fontSize': '10px', 'color': '#5a6478'}),
                                    html.Div('Carga', style={'fontSize': '10px', 'color': '#5a6478'}),
                                    html.Div('Horas', style={'fontSize': '10px', 'color': '#5a6478'}),
                                    html.Div('Mediana', style={'fontSize': '10px', 'color': '#5a6478'}),
                                ],
                                style={'display': 'grid', 'gridTemplateColumns': '160px 1fr 72px 72px', 'gap': '8px', 'marginBottom': '8px'}
                            ),
                            *bottleneck_rows,
                        ],
                        style={'backgroundColor': ONE_PAGE_THEME['surface'], 'border': f"1px solid {ONE_PAGE_THEME['border']}", 'borderRadius': '8px', 'padding': '14px'}
                    ),
                    html.Div(
                        [
                            html.Div('Indicadores por Dimensão', style={'fontSize': '14px', 'fontWeight': '700', 'color': ONE_PAGE_THEME['muted'], 'textTransform': 'uppercase', 'marginBottom': '10px'}),
                            *dimensions_rows,
                        ],
                        style={'backgroundColor': ONE_PAGE_THEME['surface'], 'border': f"1px solid {ONE_PAGE_THEME['border']}", 'borderRadius': '8px', 'padding': '14px'}
                    ),
                ],
                style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(420px, 1fr))', 'gap': '14px', 'marginBottom': '14px'}
            ),
            html.Div(
                [
                    html.Div(
                        [html.Div('Achados Principais', style={'fontSize': '14px', 'fontWeight': '700', 'color': ONE_PAGE_THEME['muted'], 'textTransform': 'uppercase', 'marginBottom': '10px'}), *finding_nodes],
                        style={'backgroundColor': ONE_PAGE_THEME['surface'], 'border': f"1px solid {ONE_PAGE_THEME['border']}", 'borderRadius': '8px', 'padding': '14px'}
                    ),
                    html.Div(
                        [
                            html.Div('Composição da Equipe', style={'fontSize': '14px', 'fontWeight': '700', 'color': ONE_PAGE_THEME['muted'], 'textTransform': 'uppercase', 'marginBottom': '10px'}),
                            dash_table.DataTable(
                                columns=[{'name': c, 'id': c} for c in people_table.columns] if not people_table.empty else [{'name': 'Info', 'id': 'Info'}],
                                data=people_table.to_dict('records') if not people_table.empty else [{'Info': 'Sem dados de equipe para o recorte atual.'}],
                                style_header={'backgroundColor': ONE_PAGE_THEME['surface_2'], 'color': ONE_PAGE_THEME['muted'], 'fontWeight': 'bold', 'border': f"1px solid {ONE_PAGE_THEME['border']}", 'fontSize': '10px'},
                                style_cell={'backgroundColor': ONE_PAGE_THEME['surface'], 'color': ONE_PAGE_THEME['text'], 'border': f"1px solid {ONE_PAGE_THEME['border']}", 'fontSize': '11px', 'padding': '6px', 'textAlign': 'left'},
                                style_table={'overflowX': 'auto'}
                            ),
                            html.Div(
                                [
                                    html.Div([html.Div(str(commits_period), style={'fontFamily': 'JetBrains Mono, monospace', 'fontSize': '18px', 'fontWeight': '600', 'color': ONE_PAGE_THEME['teal']}), html.Div('Commits', style={'fontSize': '9px', 'color': '#5a6478', 'textTransform': 'uppercase'})], style={'textAlign': 'center'}),
                                    html.Div([html.Div(str(prs_merged_period), style={'fontFamily': 'JetBrains Mono, monospace', 'fontSize': '18px', 'fontWeight': '600', 'color': ONE_PAGE_THEME['teal']}), html.Div('PRs Merged', style={'fontSize': '9px', 'color': '#5a6478', 'textTransform': 'uppercase'})], style={'textAlign': 'center'}),
                                    html.Div([html.Div(str(approvals_period), style={'fontFamily': 'JetBrains Mono, monospace', 'fontSize': '18px', 'fontWeight': '600', 'color': ONE_PAGE_THEME['red']}), html.Div('Aprovações', style={'fontSize': '9px', 'color': '#5a6478', 'textTransform': 'uppercase'})], style={'textAlign': 'center'}),
                                ],
                                style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr 1fr', 'gap': '8px', 'marginTop': '10px', 'paddingTop': '10px', 'borderTop': f"1px solid {ONE_PAGE_THEME['border']}"}
                            ),
                        ],
                        style={'backgroundColor': ONE_PAGE_THEME['surface'], 'border': f"1px solid {ONE_PAGE_THEME['border']}", 'borderRadius': '8px', 'padding': '14px'}
                    ),
                ],
                style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(420px, 1fr))', 'gap': '14px', 'marginBottom': '14px'}
            ),
            html.Div(
                [
                    html.Div([html.Div('Imediato (2 semanas)', style={'color': ONE_PAGE_THEME['red'], 'fontSize': '10px', 'fontWeight': '700', 'textTransform': 'uppercase', 'marginBottom': '6px'}), html.Div(reco_immediate, style={'fontSize': '11px', 'color': ONE_PAGE_THEME['text']})], style={'backgroundColor': ONE_PAGE_THEME['surface_2'], 'borderTop': f"2px solid {ONE_PAGE_THEME['red']}", 'borderRadius': '6px', 'padding': '10px'}),
                    html.Div([html.Div('Curto prazo (30 dias)', style={'color': ONE_PAGE_THEME['amber'], 'fontSize': '10px', 'fontWeight': '700', 'textTransform': 'uppercase', 'marginBottom': '6px'}), html.Div(reco_short, style={'fontSize': '11px', 'color': ONE_PAGE_THEME['text']})], style={'backgroundColor': ONE_PAGE_THEME['surface_2'], 'borderTop': f"2px solid {ONE_PAGE_THEME['amber']}", 'borderRadius': '6px', 'padding': '10px'}),
                    html.Div([html.Div('Médio prazo (60 dias)', style={'color': ONE_PAGE_THEME['teal'], 'fontSize': '10px', 'fontWeight': '700', 'textTransform': 'uppercase', 'marginBottom': '6px'}), html.Div(reco_medium, style={'fontSize': '11px', 'color': ONE_PAGE_THEME['text']})], style={'backgroundColor': ONE_PAGE_THEME['surface_2'], 'borderTop': f"2px solid {ONE_PAGE_THEME['teal']}", 'borderRadius': '6px', 'padding': '10px'}),
                ],
                style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(220px, 1fr))', 'gap': '10px', 'marginBottom': '14px'}
            ),
            html.Div(
                [
                    html.Div('Flow Forensics | Fontes: Jira + Bitbucket + Flow-PMO', style={'fontSize': '10px', 'color': '#5a6478'}),
                    html.Div(f"Período: {start_ts.strftime('%Y-%m-%d')} a {end_ts.strftime('%Y-%m-%d')}", style={'fontFamily': 'JetBrains Mono, monospace', 'fontSize': '10px', 'color': '#5a6478'}),
                ],
                style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'borderTop': f"1px solid {ONE_PAGE_THEME['border']}", 'paddingTop': '10px'}
            ),
        ],
        style={'backgroundColor': ONE_PAGE_THEME['bg'], 'color': ONE_PAGE_THEME['text'], 'padding': '18px', 'borderRadius': '10px', 'fontFamily': 'DM Sans, sans-serif', 'overflowX': 'auto'}
    )


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


def compute_weekly_service_metrics(df_projeto, weeks, lead_time_col='LeadTime_Dias', projeto=None):
    """Calcula métricas de performance do serviço por semana (layout transposto)."""
    metric_names = [
        'Taxa de chegada / semana',
        'Throughput / semana',
        'Média WIP / semana',
        'WIP Age (dias)',
        'Média Lead Time',
        'Média Eficiência de Fluxo',
        '% Demanda de Valor',
        '% Demanda de Falha',
        'Qtd. Itens Descartados',
        'P85% DO LEAD TIME',
        'DDP',
        'Frequência de Deploy',
        'Lead time para mudanças',
    ]
    rows = {m: {} for m in metric_names}
    bitbucket_logs = load_project_bitbucket_logs(projeto)

    for i in range(len(weeks) - 1):
        week_start = weeks[i]
        week_end = weeks[i + 1]
        week_label = str(week_start.date())

        arrived = df_projeto[
            (df_projeto['DataInProgress'] >= week_start) & (df_projeto['DataInProgress'] < week_end)
        ]
        finished = df_projeto[
            (df_projeto['DataDone'] >= week_start) & (df_projeto['DataDone'] < week_end)
        ]
        wip = df_projeto[
            (df_projeto['DataInProgress'] < week_end) &
            ((df_projeto['DataDone'] >= week_end) | pd.isna(df_projeto['DataDone']))
        ]

        finished_eligible = finished[done_time_eligible_mask(finished)] if not finished.empty else finished
        tp_total = len(finished_eligible)
        tp_dev = len(finished_eligible[finished_eligible['TipoDemanda'] == TYPE_DEV]) if tp_total > 0 else 0
        tp_def = len(finished_eligible[finished_eligible['TipoDemanda'] == TYPE_ISSUES]) if tp_total > 0 else 0
        tp_discard = int(finished_eligible['Descartado'].sum()) if 'Descartado' in finished_eligible.columns else 0

        wip_age = (week_end - wip['DataInProgress']).dt.days.mean() if len(wip) > 0 else 0
        lt_finished = time_metric_series(finished, lead_time_col, non_negative=True)
        avg_lt = lt_finished.mean() if not lt_finished.empty else np.nan
        _, avg_eff = calculate_flow_efficiency(len(arrived), tp_total)
        if pd.isna(avg_eff):
            avg_eff = 0
        median_lt = exact_empirical_percentile(lt_finished, 0.50) if tp_total > 0 and not lt_finished.empty else np.nan
        p85_lt = exact_empirical_percentile(lt_finished, 0.85) if tp_total > 0 and not lt_finished.empty else np.nan
        dora = _compute_bitbucket_weekly_dora(bitbucket_logs, week_start, week_end)
        dora_deploy_frequency = dora.get('deploy_frequency')
        dora_lead_time = dora.get('lead_time_changes')

        rows['Taxa de chegada / semana'][week_label] = str(len(arrived))
        rows['Throughput / semana'][week_label] = str(tp_total)
        rows['Média WIP / semana'][week_label] = str(len(wip))
        rows['WIP Age (dias)'][week_label] = f"{wip_age:.0f}" if wip_age else '0'
        rows['Média Lead Time'][week_label] = f"{avg_lt:.0f}" if pd.notna(avg_lt) else '—'
        rows['Média Eficiência de Fluxo'][week_label] = f"{avg_eff:.3f}" if pd.notna(avg_eff) else '0.000'
        rows['% Demanda de Valor'][week_label] = f"{tp_dev / tp_total * 100:.1f}%" if tp_total > 0 else '—'
        rows['% Demanda de Falha'][week_label] = f"{tp_def / tp_total * 100:.1f}%" if tp_total > 0 else '—'
        rows['Qtd. Itens Descartados'][week_label] = str(tp_discard)
        rows['P85% DO LEAD TIME'][week_label] = f"{p85_lt:.0f}" if pd.notna(p85_lt) else '—'
        rows['DDP'][week_label] = f"{max(0, p85_lt - median_lt):.1f}" if pd.notna(p85_lt) and pd.notna(median_lt) else '—'
        rows['Frequência de Deploy'][week_label] = f"{dora_deploy_frequency:.0f}" if pd.notna(dora_deploy_frequency) else str(tp_dev)
        rows['Lead time para mudanças'][week_label] = _format_change_lead_time(dora_lead_time) if pd.notna(dora_lead_time) else _format_change_lead_time(avg_lt)

    return metric_names, rows

fato['TipoDemanda'] = fato.apply(
    lambda row: canonicalize_demand_type(row.get('Tipo'), row.get('WorkItemSubType')),
    axis=1
)

min_date = fato['DataDone'].min() if 'DataDone' in fato.columns else pd.to_datetime('2023-01-01')
max_date = fato['DataDone'].max() if 'DataDone' in fato.columns else pd.to_datetime('today')

app.layout = html.Div([
    dcc.Store(id='main-view', data='home'),
    html.Div([
        html.H1('Dashboard de Métricas - Full', style={'margin': '0'}),
        html.Span(
            f'Última carga processada: {LAST_PROCESSED_LOAD_LABEL}',
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
            html.Label('Projeto:'),
            dcc.Dropdown(
                id='filter-projeto',
                options=[{'label': PROJECT_FILTER_ALL_LABEL, 'value': PROJECT_FILTER_ALL_VALUE}] + [{'label': p, 'value': p} for p in unique_sorted(fato['Projeto'])],
                value=PROJECT_FILTER_ALL_VALUE,
                clearable=False
            )
        ], style={'width':'20%', 'display':'inline-block'}),
        html.Div([html.Label('Tipo:'), dcc.Dropdown(id='filter-tipo', options=[{'label':t,'value':t} for t in unique_sorted(fato['TipoDemanda'])], value=None, clearable=True)], style={'width':'15%', 'display':'inline-block', 'marginLeft':'20px'}),
        html.Div([html.Label('Classe Serviço (Prioridade):'), dcc.Dropdown(id='filter-classe-servico', options=[{'label':c,'value':c} for c in unique_sorted(fato['ClasseServico'])], value=None, clearable=True)], style={'width':'16%', 'display':'inline-block', 'marginLeft':'20px'}),
        html.Div([html.Label('Responsável:'), dcc.Dropdown(id='filter-responsavel', options=[{'label':r,'value':r} for r in unique_sorted(fato['Responsavel'])], value=None, clearable=True)], style={'width':'20%', 'display':'inline-block', 'marginLeft':'20px'}),
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
            parent_style={'overflowX': 'auto'}
        ),
        id='tabs-wrapper',
        style={'display': 'none'}
    ),

    html.Div(id='tab-content')
])

def filter_df(df, start_date, end_date, projeto, tipo, classe_servico, responsavel):
    d = df.copy()
    if start_date:
        d = d[d['DataDone'] >= pd.to_datetime(start_date)]
    if end_date:
        d = d[d['DataDone'] <= pd.to_datetime(end_date)]
    if projeto:
        d = d[d['Projeto'] == projeto]
    if tipo:
        d = d[d['TipoDemanda'] == tipo]
    if classe_servico:
        d = d[d['ClasseServico'] == classe_servico]
    if responsavel:
        d = d[d['Responsavel'] == responsavel]
    return d


def optional_input(component_id, component_property):
    """Dash compatibility shim for versions without Input(..., allow_optional=...)."""
    try:
        return Input(component_id, component_property, allow_optional=True)
    except TypeError:
        return Input(component_id, component_property)


@app.callback(
    Output('main-view', 'data'),
    Output('tabs', 'value'),
    Input('btn-menu-portfolio', 'n_clicks'),
    Input('btn-menu-services', 'n_clicks'),
    Input('btn-menu-home', 'n_clicks'),
    State('tabs', 'value'),
    prevent_initial_call=True
)
def handle_main_menu_navigation(_portfolio_clicks, _services_clicks, _home_clicks, current_tab):
    triggered_id = dash.ctx.triggered_id
    if not triggered_id:
        raise PreventUpdate

    if triggered_id == 'btn-menu-portfolio':
        return 'portfolio', PORTFOLIO_TAB_VALUE

    if triggered_id == 'btn-menu-services':
        next_tab = current_tab if current_tab in SERVICE_TAB_VALUES else 'tab-performance'
        return 'services', next_tab

    if triggered_id == 'btn-menu-home':
        next_tab = current_tab if current_tab in SERVICE_TAB_VALUES else 'tab-performance'
        return 'home', next_tab

    raise PreventUpdate


@app.callback(
    Output('filter-leadtime-stages', 'options'),
    Output('filter-leadtime-stages', 'value'),
    Input('filter-projeto', 'value'),
    State('filter-leadtime-stages', 'value'),
)
def update_leadtime_stage_filter_options(projeto, current_value):
    projeto = normalize_project_filter_value(projeto)
    stage_cols, stage_source = get_leadtime_stage_filter_columns(projeto)
    if not stage_cols:
        return [], []
    done_col = get_downstream_done_stage_column(stage_cols) if stage_source == 'downstream' else get_explicit_done_stage_column(stage_cols)
    start_candidates = [c for c in stage_cols if c != done_col]
    options = [{'label': c, 'value': c} for c in start_candidates]
    current = [v for v in (current_value or []) if v in start_candidates]
    if current:
        return options, current
    return options, get_default_lead_time_start_stages(start_candidates)


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


@app.callback(
    Output('filter-portfolio-team', 'options'),
    Output('filter-portfolio-team', 'value'),
    Input('filter-projeto', 'value'),
    State('filter-portfolio-team', 'value'),
)
def sync_portfolio_project_filter(projeto, current_portfolio_project):
    options = get_portfolio_project_filter_options()
    allowed_values = {opt.get('value') for opt in options}
    if current_portfolio_project in allowed_values:
        return options, current_portfolio_project

    return options, PROJECT_FILTER_ALL_VALUE


@app.callback(
    Output('main-menu-panel', 'style'),
    Output('main-nav-panel', 'style'),
    Output('main-nav-context', 'children'),
    Output('filters-panel', 'style'),
    Output('tabs-wrapper', 'style'),
    Output('tabs', 'children'),
    Input('main-view', 'data')
)
def update_main_navigation_layout(main_view):
    menu_style = {
        'maxWidth': '720px',
        'margin': '0 auto 16px auto',
        'padding': '20px',
        'border': '1px solid #e5e7eb',
        'borderRadius': '14px',
        'backgroundColor': '#fafafa',
        'textAlign': 'center',
        'boxShadow': '0 4px 14px rgba(0,0,0,0.04)',
    }
    nav_style = {
        'display': 'flex',
        'justifyContent': 'center',
        'alignItems': 'center',
        'gap': '12px',
        'marginBottom': '12px',
        'flexWrap': 'wrap'
    }
    filters_style = {'display': 'flex', 'justifyContent': 'center', 'gap': '10px', 'marginBottom': '20px', 'flexWrap': 'wrap', 'alignItems': 'flex-start'}
    hidden_style = {'display': 'none'}

    if main_view == 'portfolio':
        return hidden_style, nav_style, 'Módulo: Portfólio', filters_style, hidden_style, build_portfolio_tab()

    if main_view == 'services':
        return hidden_style, nav_style, 'Módulo: Serviços (Value Stream)', filters_style, {}, build_service_tabs()

    return menu_style, hidden_style, '', hidden_style, hidden_style, build_service_tabs()

@app.callback(
    Output('tab-content', 'children'),
    Input('main-view', 'data'),
    Input('tabs', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    Input('filter-projeto', 'value'),
    Input('filter-tipo', 'value'),
    Input('filter-classe-servico', 'value'),
    Input('filter-responsavel', 'value'),
    Input('filter-leadtime-stages', 'value'),
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
    optional_input('estatistica-lsl', 'value'),
    optional_input('estatistica-usl', 'value'),
)
def render_tab(main_view, tab, start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, capacity_top_n=5, capacity_weekly_metric='score', portfolio_team=PROJECT_FILTER_ALL_VALUE, portfolio_quarter='ALL',
               pf_backlog_15=None, pf_backlog_30=None, pf_fresh_15=None, pf_fresh_30=None,
               pf_decision_statuses=None, pf_workflow_statuses=None, pf_sla_aging_json=None, pf_target_mix_json=None,
               estatistica_lsl=None, estatistica_usl=None):
    if main_view in (None, 'home'):
        return html.Div(
            'Selecione "Portfólio" ou "Serviços (Value Stream)" na tela principal para continuar.',
            style={
                'textAlign': 'center',
                'color': '#666',
                'padding': '18px',
                'border': '1px dashed #d1d5db',
                'borderRadius': '10px',
                'maxWidth': '720px',
                'margin': '0 auto'
            }
        )

    if main_view == 'portfolio':
        tab = PORTFOLIO_TAB_VALUE
    elif tab is None:
        tab = 'tab-performance'
    elif tab not in INTERNAL_SERVICE_TAB_VALUES:
        return html.Div(
            [
                html.H4('Aba inválida no modo Serviços', style={'textAlign': 'center', 'color': '#b22222'}),
                html.P(
                    f"Valor recebido: {tab!r}. Selecione novamente uma aba no topo.",
                    style={'textAlign': 'center', 'color': '#555'}
                ),
            ],
            style={'padding': '16px', 'border': '1px dashed #d1d5db', 'borderRadius': '10px', 'maxWidth': '780px', 'margin': '12px auto'}
        )

    projeto = normalize_project_filter_value(projeto)
    portfolio_project = normalize_project_filter_value(portfolio_team)
    df = filter_df(fato, start_date, end_date, projeto, tipo, classe_servico, responsavel)
    df, leadtime_meta = apply_selected_lead_time_metric(df, projeto, leadtime_stages)
    leadtime_selection_summary = build_leadtime_stage_selection_summary(projeto, leadtime_stages)

    # Padrão de cores para os tipos de demanda
    color_map = {
        TYPE_DEV: 'green',           # Demanda de Valor
        TYPE_ISSUES: 'red',          # Demanda de Falha
        TYPE_SUPPORT: 'orange',      # Suporte
        TYPE_OTHER: 'lightgray'      # Outros tipos
    }

    if tab == 'tab-one-page':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        one_page = build_dynamic_one_page_report(
            projeto=projeto,
            tipo=tipo,
            classe_servico=classe_servico,
            responsavel=responsavel,
            start_ts=start_ts,
            end_ts=end_ts,
            leadtime_stages=leadtime_stages,
        )
        return html.Div([one_page], style={'paddingBottom': '12px'})

    if tab == 'tab-performance':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        df_proj = fato.copy()
        if projeto:
            df_proj = df_proj[df_proj['Projeto'] == projeto]
        if responsavel:
            df_proj = df_proj[df_proj['Responsavel'] == responsavel]
        if tipo:
            df_proj = df_proj[df_proj['TipoDemanda'] == tipo]
        if classe_servico:
            df_proj = df_proj[df_proj['ClasseServico'] == classe_servico]
        df_proj, _ = apply_selected_lead_time_metric(df_proj, projeto, leadtime_stages)
        weeks = pd.date_range(start=start_ts, end=end_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal.')

        metric_names, rows = compute_weekly_service_metrics(df_proj, weeks, lead_time_col='LeadTime_Selected_Dias', projeto=projeto)
        week_labels = [str(weeks[i].date()) for i in range(len(weeks) - 1)]

        table_data = []
        for m in metric_names:
            row = {'Métrica': m}
            for wl in week_labels:
                row[wl] = rows[m].get(wl, '—')
            table_data.append(row)

        columns = [{'name': 'Métrica', 'id': 'Métrica'}] + [{'name': wl, 'id': wl} for wl in week_labels]

        style_data_conditional = [
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
            {'if': {'filter_query': '{Métrica} = "% Demanda de Valor"'}, 'color': 'green', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Métrica} = "% Demanda de Falha"'}, 'color': 'red', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Métrica} contains "—"'}, 'color': '#aaa'},
        ]
        for m in ['Qtd. Itens Descartados', 'DDP']:
            style_data_conditional.append({
                'if': {'filter_query': f'{{Métrica}} = "{m}"'},
                'backgroundColor': 'rgb(245, 245, 245)', 'color': '#bbb', 'fontStyle': 'italic'
            })

        titulo = f"Performance da Entrega do Serviço: {projeto}" if projeto else "Performance da Entrega do Serviço"
        contributor_section = build_bitbucket_contributor_section(
            projeto,
            start_ts,
            end_ts,
            jira_df=df_proj,
            top_n_people=capacity_top_n,
            weekly_metric=capacity_weekly_metric,
        )
        df_scope = fato.copy()
        if projeto:
            df_scope = df_scope[df_scope['Projeto'] == projeto]
        if responsavel:
            df_scope = df_scope[df_scope['Responsavel'] == responsavel]
        if tipo:
            df_scope = df_scope[df_scope['TipoDemanda'] == tipo]
        if classe_servico:
            df_scope = df_scope[df_scope['ClasseServico'] == classe_servico]
        df_scope, _ = apply_selected_lead_time_metric(df_scope, projeto, leadtime_stages)

        period_label = f"{start_ts.strftime('%d/%m')} a {end_ts.strftime('%d/%m')}"

        data_in_progress = pd.to_datetime(df_scope['DataInProgress'], errors='coerce') if 'DataInProgress' in df_scope.columns else pd.Series(pd.NaT, index=df_scope.index)
        data_done = pd.to_datetime(df_scope['DataDone'], errors='coerce') if 'DataDone' in df_scope.columns else pd.Series(pd.NaT, index=df_scope.index)

        mask_started_until_end = data_in_progress.isna() | (data_in_progress <= end_ts)
        mask_not_finished_before_start = data_done.isna() | (data_done >= start_ts)
        scope_mask = mask_started_until_end & mask_not_finished_before_start
        df_scope_period = df_scope[scope_mask].copy()

        done_period_mask = (data_done >= start_ts) & (data_done <= end_ts)
        df_done_period = df_scope[done_period_mask].copy()
        df_done_period_eligible = build_delivered_items_base(df_done_period)

        planned_items = int(len(df_scope_period))
        delivered_items = int(len(df_done_period_eligible))

        in_progress_mask = (
            (pd.to_datetime(df_scope_period['DataInProgress'], errors='coerce') <= end_ts) &
            (
                pd.to_datetime(df_scope_period['DataDone'], errors='coerce').isna() |
                (pd.to_datetime(df_scope_period['DataDone'], errors='coerce') > end_ts)
            )
        ) if not df_scope_period.empty else pd.Series(dtype=bool)
        in_progress_items = int(in_progress_mask.sum()) if not df_scope_period.empty else 0

        exec_days = time_metric_series(df_done_period_eligible, 'TempoExecucao_Dias', non_negative=True)
        executed_hours = float(exec_days.sum() * 8.0) if not exec_days.empty else 0.0

        sp_scope = pd.to_numeric(df_scope_period.get('StoryPoints', pd.Series(dtype=float)), errors='coerce')
        sp_done = pd.to_numeric(df_done_period_eligible.get('StoryPoints', pd.Series(dtype=float)), errors='coerce')
        sp_scope_sum = float(sp_scope.dropna().sum()) if not sp_scope.empty else 0.0
        sp_done_sum = float(sp_done.dropna().sum()) if not sp_done.empty else 0.0
        if sp_scope_sum > 0 and sp_done_sum > 0 and executed_hours > 0:
            quarter_estimated_hours = sp_scope_sum * (executed_hours / sp_done_sum)
        elif planned_items > 0 and delivered_items > 0 and executed_hours > 0:
            quarter_estimated_hours = (executed_hours / delivered_items) * planned_items
        else:
            quarter_estimated_hours = executed_hours

        tempo_bloqueio = pd.to_numeric(df_scope_period.get('TempoBloqueioDias', pd.Series(0, index=df_scope_period.index)), errors='coerce').fillna(0)
        blocked_raw = df_scope_period.get('Bloqueado', pd.Series(0, index=df_scope_period.index))
        blocked_num = pd.to_numeric(blocked_raw, errors='coerce').fillna(0)
        blocked_str = blocked_raw.fillna('').astype(str).str.strip().str.lower()
        blocked_flag = blocked_num.gt(0) | blocked_str.isin({'true', 'sim', 'yes', 'y', '1'})
        blocked_items = int((tempo_bloqueio.gt(0) | blocked_flag).sum()) if not df_scope_period.empty else 0

        dev_count = int(df_scope_period['Responsavel'].fillna('').astype(str).str.strip().replace('', np.nan).dropna().nunique()) if ('Responsavel' in df_scope_period.columns and not df_scope_period.empty) else 0
        business_days = int(np.busday_count(start_ts.date(), (end_ts + pd.Timedelta(days=1)).date())) if end_ts >= start_ts else 0
        avg_hours_dev_day = (executed_hours / (dev_count * business_days)) if dev_count > 0 and business_days > 0 else 0.0

        delivery_rate_pct = (delivered_items / planned_items * 100.0) if planned_items > 0 else 0.0
        quarter_consumed_pct = (executed_hours / quarter_estimated_hours * 100.0) if quarter_estimated_hours > 0 else 0.0
        delivery_gap = max(planned_items - delivered_items, 0)
        avg_hours_dev_day_label = f"{float(avg_hours_dev_day):.2f}".replace('.', ',')
        consolidated_cards = [
            ('Itens planejados', f"{planned_items}"),
            ('Entregues', f"{delivered_items} ({delivery_rate_pct:.0f}%)"),
            ('Em andamento', f"{in_progress_items}"),
            ('Horas executadas', f"{executed_hours:,.0f}".replace(',', '.')),
            ('Estimado do quarter', f"{quarter_estimated_hours:,.0f}".replace(',', '.')),
            ('Consumo do estimado', f"{quarter_consumed_pct:.0f}%"),
        ]
        consolidated_cards_section = html.Div([
            html.Div([
                html.Div(label, style={'fontSize': '13px', 'fontWeight': 'bold', 'color': '#334155', 'marginBottom': '4px'}),
                html.Div(value, style={'fontSize': '30px', 'fontWeight': 'bold', 'lineHeight': '1.1', 'color': '#0f172a'}),
            ], style={
                'backgroundColor': '#f8fafc',
                'border': '1px solid #dbeafe',
                'borderRadius': '10px',
                'padding': '12px',
                'minHeight': '106px',
            }) for label, value in consolidated_cards
        ], style={
            'display': 'grid',
            'gridTemplateColumns': 'repeat(auto-fit, minmax(200px, 1fr))',
            'gap': '10px',
            'marginTop': '12px',
            'marginBottom': '10px',
        })
        consolidated_section = html.Div([
            html.H4('Visão consolidada: planejamento do quarter x execução real', style={'marginBottom': '4px'}),
            html.P(
                f"Período analisado: {period_label} | "
                "Referência de horas = volume estimado no planejamento do quarter (não capacidade do time).",
                style={'color': '#475569', 'marginTop': '0', 'marginBottom': '8px'}
            ),
            consolidated_cards_section,
            html.Ul([
                html.Li(f"Aderência de entrega no período: {delivered_items}/{planned_items} ({delivery_rate_pct:.0f}%)."),
                html.Li(
                    f"Backlog imediato para decisão: {delivery_gap} itens ainda não entregues "
                    f"(dos quais {in_progress_items} em andamento)."
                ),
                html.Li(
                    f"Consumo de esforço do quarter: {executed_hours:,.0f}h de {quarter_estimated_hours:,.0f}h "
                    f"({quarter_consumed_pct:.0f}% do estimado).".replace(',', '.')
                ),
                html.Li(
                    f"Média de {avg_hours_dev_day_label}h por dev/dia: "
                    + ("sinal de possível sobrecarga pontual." if avg_hours_dev_day > 8.0 else "faixa operacional compatível com o período.")
                ),
                html.Li(
                    f"{blocked_items} bloqueios registrados: "
                    + ("tratar causa raiz e SLA de remoção." if blocked_items > 0 else "nenhum bloqueio sinalizado no recorte filtrado.")
                ),
                html.Li(
                    "Corte de escopo e priorização precisam acontecer mais cedo na sprint."
                    if delivery_gap > 0 else
                    "Manter priorização e cadência para sustentar o ritmo de entrega."
                ),
            ], style={'marginTop': '6px', 'marginBottom': '10px', 'paddingLeft': '20px'}),
            html.Div([
                html.Strong('Perguntas críticas para decisão imediata'),
                html.Ul([
                    html.Li('Estamos dentro do previsto?'),
                    html.Li('Onde está o risco?'),
                    html.Li('O que precisa ser ajustado agora?'),
                ], style={'marginTop': '6px', 'marginBottom': '0', 'paddingLeft': '20px'})
            ], style={'backgroundColor': '#fff7ed', 'border': '1px solid #fed7aa', 'borderRadius': '10px', 'padding': '10px'})
        ], style={'marginTop': '14px', 'marginBottom': '14px'})

        return html.Div([
            html.H3(titulo, style={'textAlign': 'center', 'marginBottom': '10px'}),
            leadtime_selection_summary,
            html.Div(
                (
                    "Lead Time = primeira etapa selecionada (compromisso) até finalização | "
                    f"Entregues no período: {int(len(build_delivered_items_base(df)))} itens"
                ),
                style={'textAlign': 'center', 'color': '#555', 'marginBottom': '10px', 'fontSize': '13px'}
            ),
            consolidated_section,
            dash_table.DataTable(
                id='performance-table',
                columns=columns,
                data=table_data,
                style_cell={'textAlign': 'center', 'padding': '8px', 'minWidth': '120px'},
                style_cell_conditional=[{'if': {'column_id': 'Métrica'}, 'textAlign': 'left', 'fontWeight': 'bold', 'minWidth': '250px'}],
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=style_data_conditional + [
                    {'if': {'state': 'active'}, 'backgroundColor': 'rgba(0, 116, 217, 0.1)', 'border': '1px solid rgb(0, 116, 217)'}
                ],
                style_table={'overflowX': 'auto'},
            ),
            html.Div(id='performance-metric-chart'),
            contributor_section,
        ])

    if tab == 'tab-lead-time':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        delivered_scope = build_delivered_items_base(df)
        delivered_total = int(len(delivered_scope))
        df_lt, lt_series, lt_stats = build_lead_time_comparable_scope(df, lead_col='LeadTime_Selected_Dias')
        if lt_series.empty:
            return html.Div('Sem amostra válida de Lead Time para o período e filtros selecionados.')

        line_defs = [
            ('p50', 'P50', '#27AE60', 'dash'),
            ('p75', 'P75', '#2D9CDB', 'dash'),
            ('p85', 'P85', '#9B51E0', 'dash'),
            ('p95', 'P95', '#EB5757', 'dash'),
            ('mean', 'Média', '#333333', 'dot'),
        ]

        freq = df_lt['LeadTime_Selected_Dias'].round().astype(int).value_counts().sort_index().reset_index()
        freq.columns = ['LeadTimeDia', 'Frequencia']
        freq['CumulativoPct'] = (freq['Frequencia'].cumsum() / freq['Frequencia'].sum()) * 100

        fig_lt_dist = make_subplots(specs=[[{'secondary_y': True}]])
        fig_lt_dist.add_trace(
            go.Bar(x=freq['LeadTimeDia'], y=freq['Frequencia'], name='Frequência', marker_color='#2F80ED'),
            secondary_y=False
        )
        fig_lt_dist.add_trace(
            go.Scatter(
                x=freq['LeadTimeDia'],
                y=freq['CumulativoPct'],
                mode='lines',
                name='Cumulativo %',
                line=dict(color='#F2994A', width=3)
            ),
            secondary_y=True
        )
        for key, label, color, dash_style in line_defs:
            val = lt_stats.get(key)
            if pd.isna(val):
                continue
            fig_lt_dist.add_vline(
                x=float(val),
                line_color=color,
                line_dash=dash_style,
                line_width=1.5,
                annotation_text=f'{label}: {float(val):.1f}',
                annotation_position='top'
            )
        fig_lt_dist.update_layout(
            title='Lead Time Distribution: frequência e curva acumulada',
            template='plotly_white',
            hovermode='x unified',
            legend=dict(orientation='h', y=-0.18, x=0.5, xanchor='center'),
            height=620,
            margin=dict(t=80, b=120, l=60, r=60)
        )
        fig_lt_dist.update_xaxes(title_text='Lead Time (dias)')
        fig_lt_dist.update_yaxes(title_text='Frequência (# itens)', secondary_y=False)
        fig_lt_dist.update_yaxes(title_text='Cumulativo (%)', range=[0, 100], secondary_y=True)

        df_lt_scatter = df_lt.copy().sort_values('DataDone').reset_index(drop=True)
        df_lt_scatter['MM_10'] = df_lt_scatter['LeadTime_Selected_Dias'].rolling(10, min_periods=1).mean()

        fig_lt_scatter = go.Figure()
        fig_lt_scatter.add_trace(go.Scatter(
            x=df_lt_scatter['DataDone'],
            y=df_lt_scatter['LeadTime_Selected_Dias'],
            mode='markers',
            name='Lead Time (item)',
            marker=dict(color='#2F80ED', size=8, opacity=0.75),
            hovertemplate='Done: %{x|%d/%m/%Y}<br>Lead Time: %{y:.1f} dias<extra></extra>'
        ))
        fig_lt_scatter.add_trace(go.Scatter(
            x=df_lt_scatter['DataDone'],
            y=df_lt_scatter['MM_10'],
            mode='lines',
            name='Média móvel (10 itens)',
            line=dict(color='#F2994A', width=3, dash='dash')
        ))
        for key, label, color, dash_style in line_defs:
            val = lt_stats.get(key)
            if pd.isna(val):
                continue
            fig_lt_scatter.add_hline(
                y=float(val),
                line_color=color,
                line_dash=dash_style,
                line_width=1.2,
                annotation_text=f'{label}: {float(val):.1f}',
                annotation_position='top right'
            )

        weekly_lt = (
            df_lt_scatter.assign(Semana=weekly_bucket_start(df_lt_scatter['DataDone']))
            .groupby('Semana', as_index=False)['LeadTime_Selected_Dias'].mean()
            .sort_values('Semana')
        )
        if not weekly_lt.empty:
            fig_lt_scatter.add_trace(go.Scatter(
                x=weekly_lt['Semana'],
                y=weekly_lt['LeadTime_Selected_Dias'],
                mode='lines',
                name='Lead Time médio semanal',
                line=dict(color='#111827', width=2)
            ))

        fig_lt_scatter.update_layout(
            title='Lead Time: itens concluídos ao longo do tempo',
            template='plotly_white',
            hovermode='x unified',
            legend=dict(orientation='h', y=-0.18, x=0.5, xanchor='center'),
            height=620,
            margin=dict(t=80, b=120, l=60, r=40)
        )
        fig_lt_scatter.update_xaxes(title_text='Data de conclusão', tickformat='%d/%m/%Y', tickangle=-45)
        fig_lt_scatter.update_yaxes(title_text='Lead Time (dias)')

        lt_valid_total = int(len(lt_series))
        lt_missing_total = int(max(delivered_total - lt_valid_total, 0))
        lt_fallback_total = int(leadtime_meta.get('fallback_sample', 0))
        lt_mean = lt_stats.get('mean', np.nan)
        lt_p50 = lt_stats.get('p50', np.nan)
        lt_p85 = lt_stats.get('p85', np.nan)
        subtitle = (
            f"Projeto: {projeto or 'Todos'} | Período: {start_ts.strftime('%d/%m/%Y')} a {end_ts.strftime('%d/%m/%Y')} | "
            f"Finalizados: {delivered_total} | LT válido: {lt_valid_total} | Sem base LT: {lt_missing_total} | "
            f"Fallback aplicado: {lt_fallback_total} | "
            f"Média: {lt_mean:.2f} | P50: {lt_p50:.2f} | P85: {lt_p85:.2f} | "
            f"Início: {leadtime_meta.get('label', 'padrão')}"
        )
        return html.Div([
            html.H3("Lead Time", style={'textAlign': 'center'}),
            html.P(subtitle, style={'textAlign': 'center', 'color': '#666'}),
            dcc.Graph(figure=fig_lt_dist),
            dcc.Graph(figure=fig_lt_scatter),
        ])

    if tab == PORTFOLIO_TAB_VALUE:
        snapshot, df_portfolio, error = get_portfolio_snapshot()
        if error:
            return html.Div([
                html.H3('Painel de Portfólio', style={'textAlign': 'center'}),
                html.P(
                    f'Não foi possível carregar o CSV de portfólio: {error}',
                    style={'textAlign': 'center', 'color': '#b22222'}
                ),
                html.P(
                    'Gere/atualize o CSV com o script jira_portfolio_to_csv.py e tente novamente.',
                    style={'textAlign': 'center', 'color': '#666'}
                ),
            ], style={'padding': '20px'})

        df_portfolio_filtered, effective_portfolio_project, portfolio_filter_notes = apply_portfolio_module_filters(
            df_portfolio,
            projeto=projeto,
            tipo=tipo,
            classe_servico=classe_servico,
            responsavel=responsavel,
            portfolio_project=portfolio_project,
            portfolio_quarter=portfolio_quarter,
        )

        # Re-compute snapshot with filtered data
        snapshot = compute_portfolio_snapshot(df_portfolio_filtered, snapshot['updated_at'])

        groups = snapshot['groups']

        epicos_status = groups.get('epicos_por_team_status', pd.DataFrame())
        features_status = groups.get('features_por_team_status', pd.DataFrame())
        epicos_complexidade = groups.get('epicos_por_complexidade', pd.DataFrame())
        features_complexidade = groups.get('features_por_complexidade', pd.DataFrame())
        epicos_fluxo_etapas = groups.get('epicos_fluxo_etapas', pd.DataFrame())
        pendencias_q_por_time = groups.get('pendencias_q_por_time', pd.DataFrame())
        pendencias_breakdown = groups.get('pendencias_breakdown', pd.DataFrame())
        pendencias_detalhe = groups.get('pendencias_detalhe', pd.DataFrame())
        aging_us_20 = groups.get('aging_us_20', pd.DataFrame())
        aging_features_40 = groups.get('aging_features_40', pd.DataFrame())
        aging_us_comp_20 = groups.get('aging_us_comp_20', pd.DataFrame())
        aging_features_comp_40 = groups.get('aging_features_comp_40', pd.DataFrame())
        aging_buckets_por_team = groups.get('aging_buckets_por_team', pd.DataFrame())
        aging_por_tipo = groups.get('aging_por_tipo', pd.DataFrame())
        aging_por_projeto = groups.get('aging_por_projeto', pd.DataFrame())
        flow_health_summary = groups.get('flow_health_summary', pd.DataFrame())
        flow_health_por_team = groups.get('flow_health_por_team', pd.DataFrame())
        decision_queue_aging = groups.get('decision_queue_aging', pd.DataFrame())
        decision_queue_summary = groups.get('decision_queue_summary', pd.DataFrame())
        data_freshness_por_team_statuscat = groups.get('data_freshness_por_team_statuscat', pd.DataFrame())
        status_categoria_por_team = groups.get('status_categoria_por_team', pd.DataFrame())
        status_ranking_por_team = groups.get('status_ranking_por_team', pd.DataFrame())
        status_original_top = groups.get('status_original_top', pd.DataFrame())
        workflow_conformance_por_team = groups.get('workflow_conformance_por_team', pd.DataFrame())
        status_fora_workflow_top = groups.get('status_fora_workflow_top', pd.DataFrame())
        heatmap_team_status = groups.get('heatmap_team_status', pd.DataFrame())
        effort_features_por_team = groups.get('effort_features_por_team', pd.DataFrame())
        features_sem_effort_por_team = groups.get('features_sem_effort_por_team', pd.DataFrame())
        quality_por_team = groups.get('quality_por_team', pd.DataFrame())
        quality_summary = groups.get('quality_summary', pd.DataFrame())
        estrutura_cobertura_por_team = groups.get('estrutura_cobertura_por_team', pd.DataFrame())
        estrutura_cobertura_summary = groups.get('estrutura_cobertura_summary', pd.DataFrame())
        concentracao_team_share = groups.get('concentracao_team_share', pd.DataFrame())
        concentracao_epico_share = groups.get('concentracao_epico_share', pd.DataFrame())
        concentracao_summary = groups.get('concentracao_summary', pd.DataFrame())
        tipo_balanceamento = groups.get('tipo_balanceamento', pd.DataFrame())
        items_base = groups.get('items_base', pd.DataFrame())
        hist_tasks_sem_feature_por_team = groups.get('hist_tasks_sem_feature_por_team', pd.DataFrame())
        executive_tiles = groups.get('executive_tiles', pd.DataFrame())
        epicos_por_team_total = groups.get('epicos_por_team_total', pd.DataFrame())
        features_por_team_total = groups.get('features_por_team_total', pd.DataFrame())
        top_epicos_volume = groups.get('top_epicos_volume', pd.DataFrame())
        top_epicos_aging = groups.get('top_epicos_aging', pd.DataFrame())
        epicos_detalhe = groups.get('epicos_detalhe', pd.DataFrame())
        features_detalhe = groups.get('features_detalhe', pd.DataFrame())
        portfolio_alerts_detail = groups.get('portfolio_alerts_detail', pd.DataFrame())
        portfolio_alerts_indicator_summary = groups.get('portfolio_alerts_indicator_summary', pd.DataFrame())
        portfolio_alerts_severity_summary = groups.get('portfolio_alerts_severity_summary', pd.DataFrame())
        portfolio_alerts_by_team = groups.get('portfolio_alerts_by_team', pd.DataFrame())
        portfolio_alerts_by_project = groups.get('portfolio_alerts_by_project', pd.DataFrame())
        portfolio_alert_kpis = groups.get('portfolio_alert_kpis', pd.DataFrame())
        portfolio_technical_readiness_notes = groups.get('portfolio_technical_readiness_notes', pd.DataFrame())
        portfolio_technical_epic_summary = groups.get('portfolio_technical_epic_summary', pd.DataFrame())
        portfolio_technical_items_catalog = groups.get('portfolio_technical_items_catalog', pd.DataFrame())
        has_us_items = bool(groups.get('has_us_items', False))

        selected_team = '__ALL__'
        df_portfolio_full_scope = df_portfolio_filtered.copy() if df_portfolio_filtered is not None else pd.DataFrame()

        def filter_by_team(df_source, team_col='Team'):
            if df_source is None or df_source.empty or selected_team == '__ALL__':
                return df_source
            if team_col not in df_source.columns:
                return df_source
            return df_source[df_source[team_col] == selected_team].copy()

        epicos_status = filter_by_team(epicos_status)
        features_status = filter_by_team(features_status)
        epicos_complexidade = filter_by_team(epicos_complexidade)
        features_complexidade = filter_by_team(features_complexidade)
        epicos_fluxo_etapas = filter_by_team(epicos_fluxo_etapas)
        pendencias_q_por_time = filter_by_team(pendencias_q_por_time)
        pendencias_breakdown = filter_by_team(pendencias_breakdown)
        pendencias_detalhe = filter_by_team(pendencias_detalhe)
        aging_us_20 = filter_by_team(aging_us_20)
        aging_features_40 = filter_by_team(aging_features_40)
        aging_us_comp_20 = filter_by_team(aging_us_comp_20)
        aging_features_comp_40 = filter_by_team(aging_features_comp_40)
        aging_buckets_por_team = filter_by_team(aging_buckets_por_team)
        status_categoria_por_team = filter_by_team(status_categoria_por_team)
        status_ranking_por_team = filter_by_team(status_ranking_por_team)
        flow_health_por_team = filter_by_team(flow_health_por_team)
        decision_queue_aging = filter_by_team(decision_queue_aging)
        data_freshness_por_team_statuscat = filter_by_team(data_freshness_por_team_statuscat)
        workflow_conformance_por_team = filter_by_team(workflow_conformance_por_team)
        heatmap_team_status = filter_by_team(heatmap_team_status)
        effort_features_por_team = filter_by_team(effort_features_por_team)
        features_sem_effort_por_team = filter_by_team(features_sem_effort_por_team)
        quality_por_team = filter_by_team(quality_por_team)
        estrutura_cobertura_por_team = filter_by_team(estrutura_cobertura_por_team)
        concentracao_team_share = filter_by_team(concentracao_team_share)
        hist_tasks_sem_feature_por_team = filter_by_team(hist_tasks_sem_feature_por_team)
        epicos_por_team_total = filter_by_team(epicos_por_team_total)
        features_por_team_total = filter_by_team(features_por_team_total)
        top_epicos_volume = filter_by_team(top_epicos_volume)
        top_epicos_aging = filter_by_team(top_epicos_aging)
        concentracao_epico_share = filter_by_team(concentracao_epico_share)
        epicos_detalhe = filter_by_team(epicos_detalhe)
        features_detalhe = filter_by_team(features_detalhe)
        portfolio_alerts_detail = filter_by_team(portfolio_alerts_detail)
        portfolio_alerts_by_team = filter_by_team(portfolio_alerts_by_team)
        portfolio_technical_epic_summary = filter_by_team(portfolio_technical_epic_summary)
        portfolio_technical_items_catalog = filter_by_team(portfolio_technical_items_catalog)
        if items_base is None or items_base.empty:
            items_base_scope = pd.DataFrame()
        else:
            items_base_scope = items_base.copy()
            if selected_team != '__ALL__' and 'TeamDisplay' in items_base_scope.columns:
                items_base_scope = items_base_scope[items_base_scope['TeamDisplay'] == selected_team].copy()
        if not df_portfolio_full_scope.empty and selected_team != '__ALL__' and 'Team' in df_portfolio_full_scope.columns:
            df_portfolio_full_scope = df_portfolio_full_scope[
                df_portfolio_full_scope['Team'].fillna('').astype(str).str.strip() == selected_team
            ].copy()
        if selected_team != '__ALL__' and portfolio_alerts_by_project is not None and not portfolio_alerts_by_project.empty:
            scoped_projects = set(portfolio_alerts_detail['Projeto'].dropna().astype(str)) if portfolio_alerts_detail is not None and not portfolio_alerts_detail.empty else set()
            if scoped_projects:
                portfolio_alerts_by_project = portfolio_alerts_by_project[
                    portfolio_alerts_by_project['Projeto'].fillna('').astype(str).isin(scoped_projects)
                ].copy()

        def parse_int_threshold(v, default):
            try:
                return max(0, int(float(v)))
            except Exception:
                return int(default)

        def parse_status_list(raw, fallback):
            txt = str(raw or '').strip()
            if not txt:
                return list(fallback)
            vals = [t.strip() for t in re.split(r'[;,\n]+', txt) if str(t).strip()]
            return vals or list(fallback)

        def parse_json_config(raw, fallback):
            txt = str(raw or '').strip()
            if not txt:
                return fallback
            try:
                obj = json.loads(txt)
                return obj if isinstance(obj, dict) else fallback
            except Exception:
                return fallback

        cfg_backlog_15 = parse_int_threshold(pf_backlog_15, 15)
        cfg_backlog_30 = parse_int_threshold(pf_backlog_30, 30)
        cfg_fresh_15 = parse_int_threshold(pf_fresh_15, 15)
        cfg_fresh_30 = parse_int_threshold(pf_fresh_30, 30)
        cfg_decision_statuses = parse_status_list(pf_decision_statuses, ['Triagem', 'Backlog', 'Business Review', 'READY FOR DEVELOPMENT'])
        cfg_workflow_statuses = parse_status_list(pf_workflow_statuses, ['Triagem', 'Backlog', 'To Do', 'Todo', 'Business Review', 'READY FOR DEVELOPMENT', 'In Progress', 'In Progess', 'Ready', 'Homolog', 'Staging', 'Desenvolvimento', 'Concluído', 'Concluída', 'Done', 'Closed', 'Resolved', 'Cancelled'])
        cfg_sla_aging = parse_json_config(pf_sla_aging_json, {'tipo': {'Épico': 30, 'Feature': 20}, 'status': {'Triagem': 7, 'Backlog': 15, 'Business Review': 10}})
        cfg_target_mix = parse_json_config(pf_target_mix_json, {'global': {'Épico': 70, 'Feature': 30}})
        available_teams = []
        for frame in [epicos_por_team_total, features_por_team_total]:
            if frame is None or frame.empty or 'Team' not in frame.columns:
                continue
            for t in frame['Team'].dropna().astype(str):
                team = t.strip()
                if team and team not in available_teams:
                    available_teams.append(team)

        if selected_team != '__ALL__':
            if not executive_tiles.empty:
                sem_team_val = int((selected_team == 'Sem TEAM'))
                executive_tiles = executive_tiles.copy()
                executive_tiles.loc[executive_tiles['Indicador'] == 'Sem TEAM', 'Valor'] = sem_team_val

        def grouped_chart(df_group, x_col, y_col, color_col, title):
            if df_group is None or df_group.empty:
                return html.Div([
                    html.H4(title),
                    html.P('Sem dados para exibição.')
                ])
            fig = px.bar(
                df_group,
                x=x_col,
                y=y_col,
                color=color_col,
                barmode='group',
                template='plotly_white',
                title=title
            )
            fig.update_layout(height=360, margin=dict(t=50, b=80), xaxis_tickangle=-30)
            return dcc.Graph(figure=fig)

        def threshold_color(count, threshold_key, empty_gray=False):
            c = int(count or 0)
            if empty_gray and c == 0:
                return '#d8d8d8'
            limits = PORTFOLIO_COLOR_THRESHOLDS.get(threshold_key) or {'green_max': 0, 'yellow_max': 0}
            if c <= int(limits.get('green_max', 0)):
                return '#2e7d32'
            if c <= int(limits.get('yellow_max', 0)):
                return '#f9a825'
            return '#c62828'

        def render_tile(label, value, threshold_key, subtitle='Work items', empty_gray=False):
            bg = threshold_color(value, threshold_key=threshold_key, empty_gray=empty_gray)
            fg = '#111' if bg in {'#f9a825', '#d8d8d8'} else 'white'
            return html.Div([
                html.Div(str(label), style={'fontSize': '16px', 'fontWeight': 'bold'}),
                html.Div(str(int(value or 0)), style={'fontSize': '54px', 'lineHeight': '1.1'}),
                html.Div(subtitle, style={'fontSize': '13px', 'opacity': 0.9}),
            ], style={
                'backgroundColor': bg,
                'color': fg,
                'padding': '12px',
                'borderRadius': '4px',
                'minHeight': '150px',
                'display': 'flex',
                'flexDirection': 'column',
                'justifyContent': 'space-between',
            })

        def render_tiles_by_team(df_metric, title, threshold_key):
            cards = []
            if df_metric is None or df_metric.empty:
                if not available_teams:
                    return html.Div([html.H4(title), html.P('Sem dados para exibição.')])
                cards = [
                    render_tile(team, 0, threshold_key=threshold_key, empty_gray=True)
                    for team in available_teams
                ]
            else:
                cards = [
                    render_tile(row['Team'], row['WorkItems'], threshold_key=threshold_key)
                    for _, row in df_metric.sort_values('WorkItems', ascending=False).iterrows()
                ]
            return html.Div([
                html.H4(title, style={'textAlign': 'left'}),
                html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fill, minmax(160px, 1fr))',
                    'gap': '10px'
                })
            ], style={'marginTop': '16px'})

        def render_q_pendencias_grid(df_q, df_breakdown, df_detail):
            if df_q is None or df_q.empty:
                return html.Div([html.H4('Pendências por Faixa de Aging e TEAM'), html.P('Sem dados para exibição.')])
            quadrantes = [
                PORTFOLIO_PENDING_BUCKET_1,
                PORTFOLIO_PENDING_BUCKET_2,
                PORTFOLIO_PENDING_BUCKET_3,
            ]
            blocks = []
            for q in quadrantes:
                d = df_q[df_q['Quadrante'] == q].copy()
                cards = []
                if d.empty:
                    cards.append(render_tile('Sem dados', 0, threshold_key=q, empty_gray=True))
                else:
                    for _, row in d.sort_values('WorkItems', ascending=False).iterrows():
                        cards.append(render_tile(row['Team'], row['WorkItems'], threshold_key=q))
                blocks.append(html.Div([
                    html.H4(q, style={'minWidth': '150px'}),
                    html.Div(cards, style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fill, minmax(160px, 1fr))',
                        'gap': '10px',
                        'width': '100%'
                    })
                ], style={'display': 'flex', 'gap': '16px', 'alignItems': 'flex-start', 'marginBottom': '14px'}))
            notes = html.Div([
                html.P('Pendência = item aberto no snapshot de portfólio (status não concluído).', style={'margin': '0 0 6px 0'}),
                html.P('Faixas: 0-15 dias sem alteração | 16-30 dias | acima de 30 dias.', style={'margin': '0'}),
            ], style={
                'backgroundColor': '#f5f5f5',
                'borderLeft': '4px solid #616161',
                'padding': '10px 12px',
                'marginBottom': '14px',
            })
            sections = [
                html.H3('Indicador 1 - Pendências por Faixa de Aging e TEAM', style={'textAlign': 'left'}),
                notes,
                *blocks,
            ]
            if df_breakdown is not None and not df_breakdown.empty:
                sections.append(
                    portfolio_table_component(
                        df_breakdown.copy(),
                        'Composição das pendências por quadrante, tipo e categoria de status',
                        'table-portfolio-pendencias-breakdown'
                    )
                )
            if df_detail is not None and not df_detail.empty:
                sections.append(
                    portfolio_table_component(
                        df_detail.copy(),
                        'Itens que compõem as pendências de portfólio',
                        'table-portfolio-pendencias-detalhe'
                    )
                )
            return html.Div(sections, style={'marginTop': '24px'})

        def render_executive_tiles(df_exec):
            if df_exec is None or df_exec.empty:
                return html.Div([html.H3('Indicador 3 - Resumo Executivo'), html.P('Sem dados para exibição.')])
            colors = {'ok': '#2e7d32', 'alerta': '#ef6c00', 'risco': '#ad1457', 'info': '#1976d2'}
            cards = []
            for _, row in df_exec.iterrows():
                bg = colors.get(str(row.get('Tipo', 'info')), '#1976d2')
                fg = 'white'
                cards.append(html.Div([
                    html.Div(str(row['Indicador']), style={'fontSize': '15px', 'fontWeight': 'bold'}),
                    html.Div(str(int(row['Valor'])), style={'fontSize': '48px', 'lineHeight': '1.1'}),
                ], style={
                    'backgroundColor': bg,
                    'color': fg,
                    'padding': '12px',
                    'borderRadius': '4px',
                    'minHeight': '140px',
                }))
            return html.Div([
                html.H3('Indicador 3 - Resumo Executivo', style={'textAlign': 'left'}),
                html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fill, minmax(190px, 1fr))',
                    'gap': '10px',
                }),
                html.P(
                    'Estado divergente = features sem épico + épicos sem features (quebra de relacionamento entre níveis).',
                    style={'marginTop': '8px', 'color': '#555'}
                )
            ], style={'marginTop': '24px'})

        def render_portfolio_alerts(
            df_kpis,
            df_severity,
            df_indicator,
            df_detail,
            df_team,
            df_project,
            df_tech_notes,
            df_tech_epic_summary,
            df_tech_catalog,
        ):
            if df_detail is None or df_detail.empty:
                return html.Div([
                    html.H3('Alertas de Portfólio', style={'textAlign': 'left'}),
                    html.P('Sem alertas no escopo atual.', style={'color': '#666'}),
                    portfolio_table_component(
                        df_tech_notes.copy() if df_tech_notes is not None else pd.DataFrame(),
                        'Prontidão técnica (pendências de dados)',
                        'table-portfolio-technical-readiness-notes-empty'
                    ),
                ], style={'paddingTop': '10px'})

            severity_colors = {
                'Critico': '#b71c1c',
                'Alerta': '#ef6c00',
                'Monitorar': '#1565c0',
            }

            kpi_cards = []
            if df_kpis is not None and not df_kpis.empty:
                for _, row in df_kpis.iterrows():
                    label = str(row.get('Indicador', '')).strip()
                    value = int(pd.to_numeric(row.get('Valor'), errors='coerce') or 0)
                    bg = '#455a64'
                    if 'crítica' in label.lower() or 'critic' in label.lower() or 'vencidos' in label.lower():
                        bg = severity_colors['Critico']
                    elif 'alerta' in label.lower() or 'sem feature' in label.lower() or 'sem story' in label.lower():
                        bg = severity_colors['Alerta']
                    elif 'monitorar' in label.lower() or '7d' in label.lower():
                        bg = severity_colors['Monitorar']
                    kpi_cards.append(
                        create_kpi_card(
                            label,
                            f"{value}",
                            class_name='',
                            **portfolio_kpi_style(bg)
                        )
                    )

            severity_section = html.Div()
            if df_severity is not None and not df_severity.empty:
                sev_plot = df_severity.copy()
                sev_plot['Cor'] = sev_plot['Severidade'].map(severity_colors).fillna('#455a64')
                fig = px.bar(
                    sev_plot,
                    x='Severidade',
                    y='Ocorrencias',
                    color='Severidade',
                    color_discrete_map=severity_colors,
                    text='Ocorrencias',
                    template='plotly_white',
                    title='Distribuição de alertas por severidade'
                )
                fig.update_layout(height=340, showlegend=False, margin=dict(t=60, b=40))
                severity_section = dcc.Graph(figure=fig)

            indicator_table = portfolio_table_component(
                df_indicator.copy() if df_indicator is not None else pd.DataFrame(),
                'Ocorrências por tipo de alerta e severidade',
                'table-portfolio-alert-indicator-summary'
            )
            detail_table = portfolio_table_component(
                df_detail.copy(),
                'Itens que compõem os alertas de portfólio',
                'table-portfolio-alert-detail'
            )
            team_table = portfolio_table_component(
                df_team.copy() if df_team is not None else pd.DataFrame(),
                'Alertas por TEAM',
                'table-portfolio-alert-team'
            )
            project_table = portfolio_table_component(
                df_project.copy() if df_project is not None else pd.DataFrame(),
                'Alertas por Projeto',
                'table-portfolio-alert-project'
            )
            tech_epic_summary_table = portfolio_table_component(
                df_tech_epic_summary.copy() if df_tech_epic_summary is not None else pd.DataFrame(),
                'Cobertura técnica proxy por épico',
                'table-portfolio-technical-epic-summary'
            )
            tech_catalog_table = portfolio_table_component(
                df_tech_catalog.copy() if df_tech_catalog is not None else pd.DataFrame(),
                'Catálogo de itens técnicos detectados no snapshot',
                'table-portfolio-technical-items-catalog'
            )
            tech_table = portfolio_table_component(
                df_tech_notes.copy() if df_tech_notes is not None else pd.DataFrame(),
                'Prontidão técnica (pendências de dados)',
                'table-portfolio-technical-readiness-notes'
            )

            return html.Div([
                html.H3('Alertas de Portfólio', style={'textAlign': 'left'}),
                html.P(
                    'Fase 1: alertas implementados apenas com o snapshot atual do portfólio. Custos e prontidão técnica factual ficam para evolução do contrato de dados.',
                    style={'color': '#666', 'marginBottom': '10px'}
                ),
                html.Div(kpi_cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fill, minmax(190px, 1fr))',
                    'gap': '10px',
                }),
                severity_section,
                indicator_table,
                html.Div([
                    html.Div(team_table, className='six columns'),
                    html.Div(project_table, className='six columns'),
                ], className='row', style={'marginTop': '10px'}),
                detail_table,
                tech_epic_summary_table,
                tech_catalog_table,
                tech_table,
            ], style={'paddingTop': '10px'})

        def render_team_total_tiles(df_team, value_col, title, color='#1565c0'):
            if df_team is None or df_team.empty:
                return html.Div([html.H4(title), html.P('Sem dados para exibição.')])
            cards = []
            for _, row in df_team.sort_values(value_col, ascending=False).iterrows():
                cards.append(html.Div([
                    html.Div(str(row['Team']), style={'fontSize': '16px', 'fontWeight': 'bold'}),
                    html.Div(str(int(row[value_col] or 0)), style={'fontSize': '54px', 'lineHeight': '1.1'}),
                    html.Div('Work items', style={'fontSize': '13px', 'opacity': 0.9}),
                ], style={
                    'backgroundColor': color,
                    'color': 'white',
                    'padding': '12px',
                    'borderRadius': '4px',
                    'minHeight': '150px',
                }))
            return html.Div([
                html.H4(title, style={'textAlign': 'left'}),
                html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fill, minmax(160px, 1fr))',
                    'gap': '10px'
                })
            ], style={'marginTop': '12px'})

        def render_effort_distribution(df_effort):
            if df_effort is None or df_effort.empty:
                return html.Div([html.H3('Distribuição de Effort T-shirt'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            fig_effort_team = px.bar(
                df_effort,
                x='Team',
                y='QtdFeatures',
                color='EffortTShirtDisplay',
                barmode='stack',
                template='plotly_white',
                title='Distribuição de Effort T-shirt Size por TEAM (Features)',
            )
            fig_effort_team.update_layout(height=380, margin=dict(t=60, b=80), xaxis_tickangle=-25, legend_title_text='Effort')
            effort_ranking = (
                df_effort.groupby('EffortTShirtDisplay', as_index=False)['QtdFeatures']
                .sum()
                .sort_values('QtdFeatures', ascending=False, ignore_index=True)
                .rename(columns={'EffortTShirtDisplay': 'Effort T-shirt', 'QtdFeatures': 'Features'})
            )
            return html.Div([
                html.H3('Distribuição de Effort T-shirt', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig_effort_team),
                portfolio_table_component(effort_ranking, 'Distribuição de Effort T-shirt por Feature (contagem)', 'table-portfolio-effort-distribuicao'),
            ], style={'marginTop': '24px'})

        def render_aging_buckets(df_aging):
            if df_aging is None or df_aging.empty:
                return html.Div([html.H3('Aging por Buckets'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            bucket_order = ['0-7', '8-15', '16-30', '31-60', '60+', 'Sem data']
            bucket_color_map = {
                '0-7': '#2e7d32',      # verde
                '8-15': '#f9a825',     # amarelo
                '16-30': '#ef6c00',    # laranja
                '31-60': '#c62828',    # vermelho
                '60+': '#8e0000',      # vermelho escuro
                'Sem data': '#90a4ae', # neutro
            }
            df_plot = df_aging.copy()
            df_plot['AgingBucket'] = (
                df_plot['AgingBucket']
                .fillna('Sem data')
                .astype(str)
                .str.strip()
                .replace({'': 'Sem data'})
            )
            present_buckets = [b for b in bucket_order if (df_plot['AgingBucket'] == b).any()]
            if not present_buckets:
                present_buckets = ['Sem data']
            df_plot['AgingBucket'] = pd.Categorical(df_plot['AgingBucket'], categories=present_buckets, ordered=True)
            df_plot = df_plot.sort_values(['Team', 'AgingBucket'])
            fig_aging = px.bar(
                df_plot,
                x='Team',
                y='WorkItems',
                color='AgingBucket',
                barmode='stack',
                template='plotly_white',
                title='Aging por buckets detalhados (itens abertos) por TEAM',
                color_discrete_map=bucket_color_map,
                category_orders={'AgingBucket': present_buckets}
            )
            fig_aging.update_layout(height=380, margin=dict(t=60, b=80), xaxis_tickangle=-25, legend_title_text='Bucket')
            return html.Div([
                html.H3('Aging por Buckets', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig_aging),
                portfolio_table_component(df_plot.rename(columns={'AgingBucket': 'Bucket'}), 'Aging detalhado por TEAM', 'table-portfolio-aging-buckets'),
            ], style={'marginTop': '24px'})

        def render_status_ranking(df_status_cat, df_status_rank):
            if (df_status_cat is None or df_status_cat.empty) and (df_status_rank is None or df_status_rank.empty):
                return html.Div([html.H3('Ranking de Status por TEAM'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            blocks = []
            if df_status_cat is not None and not df_status_cat.empty:
                fig_status = px.bar(
                    df_status_cat,
                    x='Team',
                    y='WorkItems',
                    color='StatusCategoria',
                    barmode='stack',
                    template='plotly_white',
                    title='%/contagem de itens por categoria de status (TEAM)'
                )
                fig_status.update_layout(height=380, margin=dict(t=60, b=80), xaxis_tickangle=-25, legend_title_text='Categoria')
                blocks.append(dcc.Graph(figure=fig_status))
            if df_status_rank is not None and not df_status_rank.empty:
                rank_cols = [c for c in ['Team', 'TotalItems', '% Backlog', '% Em progresso', '% Concluído', '% Não mapeado', 'Backlog', 'Em progresso', 'Concluído', 'Não mapeado'] if c in df_status_rank.columns]
                blocks.append(
                    portfolio_table_component(
                        df_status_rank[rank_cols].copy(),
                        'Ranking de status por TEAM (% backlog / em progresso / concluído / não mapeado)',
                        'table-portfolio-status-ranking'
                    )
                )
            return html.Div([
                html.H3('Ranking de Status por TEAM', style={'textAlign': 'left'}),
                *blocks
            ], style={'marginTop': '24px'})

        def render_heatmap_team_status(df_heatmap):
            if df_heatmap is None or df_heatmap.empty:
                return html.Div([html.H3('Heatmap TEAM x StatusCategoria'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            pivot = (
                df_heatmap.pivot_table(index='Team', columns='StatusCategoria', values='WorkItems', aggfunc='sum', fill_value=0)
            )
            # Ordem estável para leitura.
            ordered_cols = [c for c in ['Backlog', 'Em progresso', 'Concluído', 'Não mapeado'] if c in pivot.columns] + [c for c in pivot.columns if c not in {'Backlog', 'Em progresso', 'Concluído', 'Não mapeado'}]
            pivot = pivot[ordered_cols]
            fig = px.imshow(
                pivot,
                text_auto=True,
                aspect='auto',
                color_continuous_scale='Blues',
                labels=dict(x='StatusCategoria', y='TEAM', color='Itens'),
                title='Heatmap TEAM x StatusCategoria (contagem)'
            )
            fig.update_layout(height=max(320, 34 * max(1, len(pivot.index)) + 140), margin=dict(t=60, b=60))
            table_df = pivot.reset_index()
            return html.Div([
                html.H3('Heatmap TEAM x StatusCategoria', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(table_df, 'Matriz TEAM x StatusCategoria', 'table-portfolio-heatmap-team-status')
            ], style={'marginTop': '24px'})

        def render_features_sem_effort(df_sem_effort):
            if df_sem_effort is None or df_sem_effort.empty:
                return html.Div([html.H3('Features sem Effort por TEAM'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            df_plot = df_sem_effort.sort_values(['% Sem Effort', 'FeaturesSemEffort'], ascending=[False, False]).copy()
            fig = px.bar(
                df_plot,
                x='Team',
                y='FeaturesSemEffort',
                color='% Sem Effort',
                template='plotly_white',
                title='Features sem Effort por TEAM (contagem e severidade em %)',
                color_continuous_scale='OrRd'
            )
            fig.update_layout(height=360, margin=dict(t=60, b=80), xaxis_tickangle=-25)
            fig.update_traces(
                customdata=df_plot[['FeaturesTotal', '% Sem Effort', '% Com Effort']].to_numpy(),
                hovertemplate='TEAM: %{x}<br>Sem Effort: %{y}<br>Total Features: %{customdata[0]}<br>% Sem Effort: %{customdata[1]}%<br>% Com Effort: %{customdata[2]}%<extra></extra>'
            )
            return html.Div([
                html.H3('Features sem Effort por TEAM', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(df_plot, 'Cobertura de Effort por TEAM (features)', 'table-portfolio-features-sem-effort-team')
            ], style={'marginTop': '24px'})

        def render_effort_aging_staleness(df_features_detail):
            if df_features_detail is None or df_features_detail.empty or 'Effort T-shirt' not in df_features_detail.columns:
                return html.Div([html.H3('Effort x Aging'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = df_features_detail.copy()
            base['Effort T-shirt'] = base['Effort T-shirt'].fillna('').astype(str).str.strip()
            base.loc[base['Effort T-shirt'] == '', 'Effort T-shirt'] = 'Sem estimativa'
            base['DiasSemMovimentacao'] = pd.to_numeric(base.get('DiasSemMovimentacao'), errors='coerce')
            if base['DiasSemMovimentacao'].dropna().empty:
                return html.Div([html.H3('Effort x Aging'), html.P('Sem dados de aging nas features.')], style={'marginTop': '20px'})
            summary = (
                base.groupby('Effort T-shirt', dropna=False)['DiasSemMovimentacao']
                .agg(Features='count', Aging_Medio='mean', Aging_Mediano='median', Aging_Max='max')
                .reset_index()
            )
            p90 = base.groupby('Effort T-shirt', dropna=False)['DiasSemMovimentacao'].quantile(0.90).reset_index(name='Aging_P90')
            summary = summary.merge(p90, on='Effort T-shirt', how='left')
            summary = summary.rename(columns={'Aging_Medio': 'Aging Médio', 'Aging_Mediano': 'Aging Mediano', 'Aging_Max': 'Aging Máx', 'Aging_P90': 'Aging P90'})
            for c in ['Aging Médio', 'Aging Mediano', 'Aging Máx', 'Aging P90']:
                summary[c] = pd.to_numeric(summary[c], errors='coerce').round(1)
            summary = summary.sort_values(['Aging P90', 'Features'], ascending=[False, False], ignore_index=True)

            stale = base.groupby('Effort T-shirt', dropna=False).size().reset_index(name='FeaturesTotal')
            stale15 = base[base['DiasSemMovimentacao'] > 15].groupby('Effort T-shirt', dropna=False).size().reset_index(name='SemMov15d')
            stale30 = base[base['DiasSemMovimentacao'] > 30].groupby('Effort T-shirt', dropna=False).size().reset_index(name='SemMov30d')
            stale = stale.merge(stale15, on='Effort T-shirt', how='left').merge(stale30, on='Effort T-shirt', how='left')
            stale[['SemMov15d', 'SemMov30d']] = stale[['SemMov15d', 'SemMov30d']].fillna(0).astype(int)
            stale['% SemMov15d'] = (stale['SemMov15d'] / stale['FeaturesTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
            stale['% SemMov30d'] = (stale['SemMov30d'] / stale['FeaturesTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
            stale = stale.sort_values(['% SemMov30d', '% SemMov15d', 'FeaturesTotal'], ascending=[False, False, False], ignore_index=True)

            fig = px.bar(summary, x='Effort T-shirt', y='Aging P90', color='Features', template='plotly_white',
                         title='Effort x Aging (P90 de dias sem movimentação)')
            fig.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            return html.Div([
                html.H3('Effort x Aging', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(summary, 'Effort x aging (features)', 'table-portfolio-effort-aging'),
                portfolio_table_component(stale, '% sem movimentação 15/30 dias por effort', 'table-portfolio-effort-stale'),
            ], style={'marginTop': '24px'})

        def render_aging_por_tipo_projeto(df_tipo, df_projeto):
            if (df_tipo is None or df_tipo.empty) and (df_projeto is None or df_projeto.empty):
                return html.Div([html.H3('Aging por Tipo/Projeto'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            severity_scale = ['#2e7d32', '#f9a825', '#c62828']
            blocks = []
            if df_tipo is not None and not df_tipo.empty:
                fig_tipo = px.bar(
                    df_tipo.sort_values(['Aging Médio', 'QtdItensAbertos'], ascending=[False, False]),
                    x='Tipo',
                    y='Aging Médio',
                    color='QtdItensAbertos',
                    template='plotly_white',
                    title='Aging médio por Tipo (itens abertos)',
                    color_continuous_scale=severity_scale
                )
                fig_tipo.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-25)
                blocks.append(dcc.Graph(figure=fig_tipo))
                blocks.append(portfolio_table_component(df_tipo.copy(), 'Aging por Tipo (abertos)', 'table-portfolio-aging-por-tipo'))
            if df_projeto is not None and not df_projeto.empty:
                fig_proj = px.bar(
                    df_projeto.sort_values(['Aging Médio', 'QtdItensAbertos'], ascending=[False, False]),
                    x='Projeto',
                    y='Aging Médio',
                    color='QtdItensAbertos',
                    template='plotly_white',
                    title='Aging médio por Projeto (itens abertos)',
                    color_continuous_scale=severity_scale
                )
                fig_proj.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-25)
                blocks.append(dcc.Graph(figure=fig_proj))
                blocks.append(portfolio_table_component(df_projeto.copy(), 'Aging por Projeto (abertos)', 'table-portfolio-aging-por-projeto'))
            return html.Div([
                html.H3('Aging por Tipo/Projeto', style={'textAlign': 'left'}),
                *blocks
            ], style={'marginTop': '24px'})

        def render_concentracao_epicos(df_top_volume, df_top_aging):
            if (df_top_volume is None or df_top_volume.empty) and (df_top_aging is None or df_top_aging.empty):
                return html.Div([html.H3('Concentração de Épicos'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            sections = []
            if df_top_volume is not None and not df_top_volume.empty:
                fig_vol = px.bar(
                    df_top_volume.head(10).copy().sort_values('QtdItensFluxo', ascending=True),
                    x='QtdItensFluxo',
                    y='EpicID',
                    orientation='h',
                    color='Team',
                    template='plotly_white',
                    title='Top Épicos por Volume (itens de fluxo)',
                    hover_data=['Titulo', 'QtdFeatures', 'AgingDiasSemAlteracao', 'Status']
                )
                fig_vol.update_layout(height=420, margin=dict(l=100, r=40, t=60, b=40))
                sections.append(dcc.Graph(figure=fig_vol))
                sections.append(portfolio_table_component(df_top_volume.copy(), 'Top Épicos por volume', 'table-portfolio-top-epicos-volume'))
            if df_top_aging is not None and not df_top_aging.empty:
                fig_age = px.bar(
                    df_top_aging.head(10).copy().sort_values('AgingDiasSemAlteracao', ascending=True),
                    x='AgingDiasSemAlteracao',
                    y='EpicID',
                    orientation='h',
                    color='Team',
                    template='plotly_white',
                    title='Top Épicos por Aging (abertos)',
                    hover_data=['Titulo', 'QtdItensFluxo', 'QtdFeatures', 'Status']
                )
                fig_age.update_layout(height=420, margin=dict(l=100, r=40, t=60, b=40))
                sections.append(dcc.Graph(figure=fig_age))
                sections.append(portfolio_table_component(df_top_aging.copy(), 'Top Épicos por aging', 'table-portfolio-top-epicos-aging'))
            return html.Div([
                html.H3('Concentração (Top Épicos por Volume/Aging)', style={'textAlign': 'left'}),
                *sections
            ], style={'marginTop': '24px'})

        def render_quality_cards(df_quality_scope, df_quality_global):
            def _from_scope_or_global(indicador):
                if df_quality_scope is not None and not df_quality_scope.empty:
                    total_items = int(df_quality_scope['TotalItems'].sum()) if 'TotalItems' in df_quality_scope.columns else 0
                    com_team = int(df_quality_scope['ComTeamOriginal'].sum()) if 'ComTeamOriginal' in df_quality_scope.columns else 0
                    status_nm = int(df_quality_scope['StatusNaoMapeado'].sum()) if 'StatusNaoMapeado' in df_quality_scope.columns else 0
                    feat_total = int(df_quality_scope['FeaturesTotal'].sum()) if 'FeaturesTotal' in df_quality_scope.columns else 0
                    feat_epic = int(df_quality_scope['FeaturesComEpic'].sum()) if 'FeaturesComEpic' in df_quality_scope.columns else 0
                    feat_eff = int(df_quality_scope['FeaturesComEffort'].sum()) if 'FeaturesComEffort' in df_quality_scope.columns else 0
                    mapping = {
                        '% com TEAM': (com_team, total_items),
                        '% features com épico': (feat_epic, feat_total),
                        '% features com effort': (feat_eff, feat_total),
                        '% itens com status não mapeado': (status_nm, total_items),
                    }
                    n, d = mapping.get(indicador, (0, 0))
                    pct = round((n / d * 100), 1) if d else 0.0
                    return pct, n, d
                if df_quality_global is not None and not df_quality_global.empty:
                    row = df_quality_global[df_quality_global['Indicador'] == indicador]
                    if not row.empty:
                        r = row.iloc[0]
                        return float(r.get('Percentual', 0.0) or 0.0), int(r.get('Numerador', 0) or 0), int(r.get('Denominador', 0) or 0)
                return 0.0, 0, 0

            specs = [
                '% com TEAM',
                '% features com épico',
                '% features com effort',
                '% itens com status não mapeado',
            ]
            cards = []
            for indicador in specs:
                pct, n, d = _from_scope_or_global(indicador)
                if indicador == '% itens com status não mapeado':
                    color = '#c62828' if pct > 10 else ('#f9a825' if pct > 3 else '#2e7d32')
                else:
                    color = '#2e7d32' if pct >= 90 else ('#f9a825' if pct >= 70 else '#c62828')
                fg = '#111' if color == '#f9a825' else 'white'
                cards.append(html.Div([
                    html.Div(indicador, style={'fontSize': '15px', 'fontWeight': 'bold'}),
                    html.Div(f'{pct:.1f}%', style={'fontSize': '48px', 'lineHeight': '1.1'}),
                    html.Div(f'{n}/{d}', style={'fontSize': '13px', 'opacity': 0.9}),
                ], style={
                    'backgroundColor': color,
                    'color': fg,
                    'padding': '12px',
                    'borderRadius': '4px',
                    'minHeight': '140px',
                }))
            return html.Div([
                html.H3('Qualidade de Cadastro', style={'textAlign': 'left'}),
                html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fill, minmax(190px, 1fr))',
                    'gap': '10px',
                }),
                portfolio_table_component(
                    (df_quality_scope if df_quality_scope is not None and not df_quality_scope.empty else df_quality_global),
                    'Qualidade de cadastro por TEAM (ou resumo global)',
                    'table-portfolio-qualidade-cadastro'
                )
            ], style={'marginTop': '24px'})

        def render_flow_health(df_summary, df_team):
            if (df_summary is None or df_summary.empty) and (df_team is None or df_team.empty):
                return html.Div([html.H3('Saúde de Fluxo (Snapshot)'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            card_colors = {
                '% WIP no portfólio': '#1565c0',
                '% backlog parado >15d': '#f9a825',
                '% backlog parado >30d': '#c62828',
                '% itens abertos': '#546e7a',
            }
            cards = []
            if df_summary is not None and not df_summary.empty:
                for _, row in df_summary.iterrows():
                    label = str(row.get('Indicador', 'Indicador'))
                    pct = float(row.get('Percentual', 0) or 0)
                    n = int(row.get('Numerador', 0) or 0)
                    d = int(row.get('Denominador', 0) or 0)
                    bg = card_colors.get(label, '#455a64')
                    cards.append(html.Div([
                        html.Div(label, style={'fontSize': '14px', 'fontWeight': 'bold'}),
                        html.Div(f'{pct:.1f}%', style={'fontSize': '42px', 'lineHeight': '1.0'}),
                        html.Div(f'{n}/{d}', style={'fontSize': '12px', 'opacity': 0.9}),
                    ], style={'backgroundColor': bg, 'color': 'white', 'padding': '12px', 'borderRadius': '4px', 'minHeight': '130px'}))
            blocks = [html.Div(cards, style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(210px, 1fr))', 'gap': '10px'})]
            if df_team is not None and not df_team.empty:
                dynamic_backlog_cols = [c for c in df_team.columns if str(c).startswith('BacklogParado') or str(c).startswith('% Backlog parado >')]
                cols = [c for c in ['Team', 'TotalItems', 'WIP', '% WIP', 'BacklogAberto'] if c in df_team.columns] + dynamic_backlog_cols
                blocks.append(portfolio_table_component(df_team[cols].copy(), 'Saúde de fluxo por TEAM', 'table-portfolio-flow-health-team'))
            return html.Div([html.H3('Saúde de Fluxo (Snapshot)', style={'textAlign': 'left'}), *blocks], style={'marginTop': '24px'})

        def render_flow_health_dynamic(items_df):
            if items_df is None or items_df.empty:
                return render_flow_health(flow_health_summary, flow_health_por_team)
            base = items_df.copy()
            for c in ['IsOpen', 'IsBacklog', 'IsInProgress']:
                if c in base.columns:
                    base[c] = base[c].astype(bool)
            base['AgingDiasSemAlteracao'] = pd.to_numeric(base.get('AgingDiasSemAlteracao'), errors='coerce')
            total_items = int(len(base))
            backlog = base[(base.get('IsOpen', False) == True) & (base.get('IsBacklog', False) == True)].copy()
            wip = int((base.get('IsInProgress', False) == True).sum()) if 'IsInProgress' in base.columns else 0
            open_items = int((base.get('IsOpen', False) == True).sum()) if 'IsOpen' in base.columns else 0
            b15 = int((backlog['AgingDiasSemAlteracao'] > cfg_backlog_15).sum()) if not backlog.empty else 0
            b30 = int((backlog['AgingDiasSemAlteracao'] > cfg_backlog_30).sum()) if not backlog.empty else 0
            total_backlog = int(len(backlog))
            summary = pd.DataFrame([
                {'Indicador': '% WIP no portfólio', 'Percentual': round((wip / total_items * 100), 1) if total_items else 0.0, 'Numerador': wip, 'Denominador': total_items},
                {'Indicador': f'% backlog parado >{cfg_backlog_15}d', 'Percentual': round((b15 / total_backlog * 100), 1) if total_backlog else 0.0, 'Numerador': b15, 'Denominador': total_backlog},
                {'Indicador': f'% backlog parado >{cfg_backlog_30}d', 'Percentual': round((b30 / total_backlog * 100), 1) if total_backlog else 0.0, 'Numerador': b30, 'Denominador': total_backlog},
                {'Indicador': '% itens abertos', 'Percentual': round((open_items / total_items * 100), 1) if total_items else 0.0, 'Numerador': open_items, 'Denominador': total_items},
            ])
            if 'TeamDisplay' in base.columns:
                rows = []
                for team, grp in base.groupby('TeamDisplay', dropna=False):
                    gback = grp[(grp.get('IsOpen', False) == True) & (grp.get('IsBacklog', False) == True)].copy()
                    rows.append({
                        'Team': str(team),
                        'TotalItems': int(len(grp)),
                        'WIP': int((grp.get('IsInProgress', False) == True).sum()) if 'IsInProgress' in grp.columns else 0,
                        '% WIP': round(((grp.get('IsInProgress', False) == True).sum() / len(grp) * 100), 1) if len(grp) else 0.0,
                        'BacklogAberto': int(len(gback)),
                        f'BacklogParado{cfg_backlog_15}': int((pd.to_numeric(gback.get('AgingDiasSemAlteracao'), errors='coerce') > cfg_backlog_15).sum()) if not gback.empty else 0,
                        f'BacklogParado{cfg_backlog_30}': int((pd.to_numeric(gback.get('AgingDiasSemAlteracao'), errors='coerce') > cfg_backlog_30).sum()) if not gback.empty else 0,
                    })
                team_df = pd.DataFrame(rows)
                if not team_df.empty:
                    team_df[f'% Backlog parado >{cfg_backlog_15}d'] = (team_df[f'BacklogParado{cfg_backlog_15}'] / team_df['BacklogAberto'].replace(0, np.nan) * 100).fillna(0).round(1)
                    team_df[f'% Backlog parado >{cfg_backlog_30}d'] = (team_df[f'BacklogParado{cfg_backlog_30}'] / team_df['BacklogAberto'].replace(0, np.nan) * 100).fillna(0).round(1)
            else:
                team_df = pd.DataFrame()
            return render_flow_health(summary, team_df)

        def render_decision_queue(df_dq, df_summary):
            if (df_dq is None or df_dq.empty) and (df_summary is None or df_summary.empty):
                return html.Div([html.H3('Fila de Decisão por Aging'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            parts = []
            if df_dq is not None and not df_dq.empty:
                bucket_order = ['0-7', '8-15', '16-30', '31-60', '60+']
                df_plot = df_dq.copy()
                df_plot['AgingBucketDecision'] = (
                    df_plot['AgingBucketDecision']
                    .fillna('0-7')
                    .astype(str)
                    .str.strip()
                )
                present_buckets = [bucket for bucket in bucket_order if (df_plot['AgingBucketDecision'] == bucket).any()]
                if not present_buckets:
                    present_buckets = bucket_order[:1]
                fig = px.bar(
                    df_plot,
                    x='Status',
                    y='WorkItems',
                    color='AgingBucketDecision',
                    barmode='stack',
                    template='plotly_white',
                    title='Fila de decisão por status e aging',
                    category_orders={'AgingBucketDecision': present_buckets},
                )
                fig.update_layout(height=360, margin=dict(t=60, b=80), xaxis_tickangle=-20)
                parts.append(dcc.Graph(figure=fig))
                parts.append(portfolio_table_component(df_dq.copy(), 'Fila de decisão (detalhe por TEAM/status/bucket)', 'table-portfolio-decision-queue-aging'))
            if df_summary is not None and not df_summary.empty:
                parts.append(portfolio_table_component(df_summary.copy(), 'Fila de decisão por status (resumo)', 'table-portfolio-decision-queue-summary'))
            return html.Div([html.H3('Fila de Decisão por Aging', style={'textAlign': 'left'}), *parts], style={'marginTop': '24px'})

        def render_data_freshness(df_fresh):
            if df_fresh is None or df_fresh.empty:
                return html.Div([html.H3('Data Freshness por Etapa'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            pivot = df_fresh.pivot_table(index='Team', columns='StatusCategoria', values='% >30d', aggfunc='mean', fill_value=0)
            fig = px.imshow(pivot, text_auto='.1f', aspect='auto', color_continuous_scale=['#2e7d32', '#f9a825', '#c62828'],
                            labels=dict(x='StatusCategoria', y='TEAM', color='% >30d'),
                            title='Data Freshness por etapa (abertos) - % acima de 30 dias')
            fig.update_layout(height=max(320, 34 * max(1, len(pivot.index)) + 140), margin=dict(t=60, b=60))
            cols = [c for c in ['Team', 'StatusCategoria', 'WorkItems', 'GT15', '% >15d', 'GT30', '% >30d'] if c in df_fresh.columns]
            return html.Div([
                html.H3('Data Freshness por Etapa', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(df_fresh[cols].copy(), 'Freshness por TEAM e etapa', 'table-portfolio-data-freshness')
            ], style={'marginTop': '24px'})

        def render_data_freshness_dynamic(items_df):
            if items_df is None or items_df.empty:
                return render_data_freshness(data_freshness_por_team_statuscat)
            base = items_df.copy()
            if 'IsOpen' in base.columns:
                base = base[base['IsOpen'] == True].copy()
            if base.empty:
                return html.Div([html.H3('Data Freshness por Etapa'), html.P('Sem itens abertos para exibição.')], style={'marginTop': '20px'})
            base['AgingDiasSemAlteracao'] = pd.to_numeric(base.get('AgingDiasSemAlteracao'), errors='coerce')
            team_col = 'TeamDisplay' if 'TeamDisplay' in base.columns else None
            if not team_col:
                return render_data_freshness(data_freshness_por_team_statuscat)
            agg = (
                base.groupby([team_col, 'StatusCategoria'], dropna=False)
                .agg(WorkItems=('ID', 'count'))
                .reset_index()
                .rename(columns={team_col: 'Team'})
            )
            tmp = base.copy()
            tmp['GTa'] = (tmp['AgingDiasSemAlteracao'] > cfg_fresh_15).astype(int)
            tmp['GTb'] = (tmp['AgingDiasSemAlteracao'] > cfg_fresh_30).astype(int)
            add = tmp.groupby([team_col, 'StatusCategoria'], dropna=False).agg(GTa=('GTa', 'sum'), GTb=('GTb', 'sum')).reset_index().rename(columns={team_col: 'Team'})
            agg = agg.merge(add, on=['Team', 'StatusCategoria'], how='left')
            agg[f'% >{cfg_fresh_15}d'] = (agg['GTa'] / agg['WorkItems'].replace(0, np.nan) * 100).fillna(0).round(1)
            agg[f'% >{cfg_fresh_30}d'] = (agg['GTb'] / agg['WorkItems'].replace(0, np.nan) * 100).fillna(0).round(1)
            view = agg.rename(columns={'GTa': f'GT{cfg_fresh_15}', 'GTb': f'GT{cfg_fresh_30}', f'% >{cfg_fresh_15}d': '% >15d', f'% >{cfg_fresh_30}d': '% >30d'})
            return render_data_freshness(view)

        def render_status_conformance(df_workflow, df_status_top, df_fora_top):
            if all(x is None or x.empty for x in [df_workflow, df_status_top, df_fora_top]):
                return html.Div([html.H3('Conformidade de Workflow'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            parts = []
            if df_workflow is not None and not df_workflow.empty:
                cols = [c for c in ['Team', 'TotalItems', 'StatusForaWorkflow', '% Fora workflow'] if c in df_workflow.columns]
                parts.append(portfolio_table_component(df_workflow[cols].copy(), 'Conformidade de workflow por TEAM', 'table-portfolio-workflow-conformance'))
            if df_fora_top is not None and not df_fora_top.empty:
                parts.append(portfolio_table_component(df_fora_top.copy(), 'Top status fora do workflow padrão', 'table-portfolio-status-fora-workflow'))
            if df_status_top is not None and not df_status_top.empty:
                parts.append(portfolio_table_component(df_status_top.copy(), 'Distribuição de status original (Top N)', 'table-portfolio-status-original-top'))
            return html.Div([html.H3('Conformidade de Workflow', style={'textAlign': 'left'}), *parts], style={'marginTop': '24px'})

        def render_estrutura_cobertura(df_summary, df_team):
            if (df_summary is None or df_summary.empty) and (df_team is None or df_team.empty):
                return html.Div([html.H3('Cobertura Estrutural'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            cards = []
            if df_summary is not None and not df_summary.empty:
                for _, row in df_summary.iterrows():
                    pct = float(row.get('Percentual', 0) or 0)
                    n = int(row.get('Numerador', 0) or 0)
                    d = int(row.get('Denominador', 0) or 0)
                    label = str(row.get('Indicador', 'Indicador'))
                    cards.append(html.Div([
                        html.Div(label, style={'fontSize': '14px', 'fontWeight': 'bold'}),
                        html.Div(f'{pct:.1f}%', style={'fontSize': '42px'}),
                        html.Div(f'{n}/{d}', style={'fontSize': '12px', 'opacity': 0.9}),
                    ], style={'backgroundColor': '#5d4037', 'color': 'white', 'padding': '12px', 'borderRadius': '4px', 'minHeight': '130px'}))
            blocks = [html.Div(cards, style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(220px, 1fr))', 'gap': '10px'})]
            if df_team is not None and not df_team.empty:
                cols = [c for c in ['Team', 'EpicosTotal', 'EpicosComItensFluxo', '% Épicos com itens de fluxo', 'FeaturesTotal', 'FeaturesComFilhos', '% Features com filhos', 'StoryTaskTotal', 'StoryTaskSemFeatureTatico', '% Story/Task sem feature tática', 'StoryTaskOrfaos', '% Story/Task órfãos'] if c in df_team.columns]
                blocks.append(portfolio_table_component(df_team[cols].copy(), 'Cobertura estrutural por TEAM', 'table-portfolio-estrutura-cobertura'))
            return html.Div([html.H3('Cobertura Estrutural', style={'textAlign': 'left'}), *blocks], style={'marginTop': '24px'})

        def render_concentracao_relativa(df_summary, df_team_share, df_epic_share):
            if (df_summary is None or df_summary.empty) and (df_team_share is None or df_team_share.empty) and (df_epic_share is None or df_epic_share.empty):
                return html.Div([html.H3('Concentração Relativa'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            parts = []
            if df_summary is not None and not df_summary.empty:
                parts.append(portfolio_table_component(df_summary.copy(), 'Resumo de concentração relativa (Top N)', 'table-portfolio-concentracao-summary'))
            if df_team_share is not None and not df_team_share.empty:
                cols = [c for c in ['Team', 'TotalItems', '% Share', '% Share Acum', 'QtdEpicos', 'QtdFeatures'] if c in df_team_share.columns]
                parts.append(portfolio_table_component(df_team_share[cols].copy(), 'Concentração por TEAM (share acumulado)', 'table-portfolio-concentracao-team-share'))
            if df_epic_share is not None and not df_epic_share.empty:
                cols = [c for c in ['EpicID', 'Team', 'QtdItensFluxo', '% Share Itens Fluxo', '% Share Acum', 'QtdFeatures', 'AgingDiasSemAlteracao'] if c in df_epic_share.columns]
                parts.append(portfolio_table_component(df_epic_share[cols].copy(), 'Concentração por Épico (share de itens de fluxo)', 'table-portfolio-concentracao-epico-share'))
            return html.Div([html.H3('Concentração Relativa', style={'textAlign': 'left'}), *parts], style={'marginTop': '24px'})

        def render_tipo_balanceamento(df_tipo_balance):
            if df_tipo_balance is None or df_tipo_balance.empty:
                return html.Div([html.H3('Índice de Balanceamento por Tipo'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            fig = px.bar(df_tipo_balance.sort_values('Desvio Abs (pp)', ascending=False), x='Tipo', y='Desvio (pp)', color='Desvio (pp)',
                         template='plotly_white', title='Desvio do mix por tipo (atual vs alvo)', color_continuous_scale=['#2e7d32', '#f9a825', '#c62828'])
            fig.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            return html.Div([
                html.H3('Índice de Balanceamento por Tipo', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(df_tipo_balance.copy(), 'Mix por tipo (atual vs alvo)', 'table-portfolio-tipo-balanceamento')
            ], style={'marginTop': '24px'})

        def render_thresholds_config_summary():
            return html.Div([
                html.H4('Parâmetros ativos (UI)', style={'marginBottom': '6px'}),
                html.P(
                    f'Backlog parado: >{cfg_backlog_15}d / >{cfg_backlog_30}d | Freshness: >{cfg_fresh_15}d / >{cfg_fresh_30}d | '
                    f'Fila decisão: {", ".join(cfg_decision_statuses[:6]) + ("..." if len(cfg_decision_statuses) > 6 else "")}',
                    style={'color': '#555', 'marginBottom': '0'}
                )
            ], style={'marginTop': '10px', 'padding': '10px 12px', 'border': '1px solid #e5e7eb', 'borderRadius': '8px', 'backgroundColor': '#fafafa'})

        def render_dynamic_workflow_conformance(items_df):
            if items_df is None or items_df.empty:
                return html.Div([html.H3('Conformidade de Workflow (Parametrizada)'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = items_df.copy()
            official_norm = [normalize_text(s) for s in cfg_workflow_statuses if str(s).strip()]
            series_norm = base.get('StatusNorm', pd.Series('', index=base.index)).fillna('').astype(str)
            mask_official = pd.Series(False, index=base.index)
            for term in official_norm:
                if term:
                    mask_official = mask_official | series_norm.str.contains(term, regex=False, na=False)
            base['ForaWorkflowCfg'] = ~mask_official
            team_col = 'TeamDisplay' if 'TeamDisplay' in base.columns else None
            team_table = pd.DataFrame()
            if team_col:
                team_table = (
                    base.groupby(team_col, dropna=False)
                    .agg(TotalItems=('ID', 'count'), ForaWorkflow=('ForaWorkflowCfg', 'sum'))
                    .reset_index()
                    .rename(columns={team_col: 'Team'})
                )
                team_table['% Fora workflow (cfg)'] = (team_table['ForaWorkflow'] / team_table['TotalItems'].replace(0, np.nan) * 100).fillna(0).round(1)
                team_table = team_table.sort_values(['% Fora workflow (cfg)', 'ForaWorkflow'], ascending=[False, False], ignore_index=True)
            top_status = (
                base[base['ForaWorkflowCfg']]
                .groupby('Status', dropna=False)
                .size().reset_index(name='WorkItems')
                .sort_values('WorkItems', ascending=False, ignore_index=True)
                .head(20)
            )
            return html.Div([
                html.H3('Conformidade de Workflow (Parametrizada)', style={'textAlign': 'left'}),
                portfolio_table_component(team_table, 'Conformidade por TEAM (lista oficial configurada na UI)', 'table-portfolio-workflow-conformance-cfg'),
                portfolio_table_component(top_status, 'Top status fora do workflow (lista oficial configurada na UI)', 'table-portfolio-status-fora-workflow-cfg'),
            ], style={'marginTop': '24px'})

        def render_dynamic_decision_queue(items_df):
            if items_df is None or items_df.empty:
                return html.Div([html.H3('Fila de Decisão (Parametrizada)'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = items_df.copy()
            status_norm = base.get('StatusNorm', pd.Series('', index=base.index)).fillna('').astype(str)
            wanted = [normalize_text(s) for s in cfg_decision_statuses if str(s).strip()]
            mask = pd.Series(False, index=base.index)
            for term in wanted:
                if term:
                    mask = mask | status_norm.str.contains(term, regex=False, na=False)
            base = base[(base.get('IsOpen', False) == True) & mask].copy()
            if base.empty:
                return html.Div([html.H3('Fila de Decisão (Parametrizada)'), html.P('Nenhum item encontrado com os statuses configurados.')], style={'marginTop': '20px'})
            base['AgingDiasSemAlteracao'] = pd.to_numeric(base['AgingDiasSemAlteracao'], errors='coerce')
            base['Bucket'] = '0-7'
            base.loc[base['AgingDiasSemAlteracao'] > 7, 'Bucket'] = '8-15'
            base.loc[base['AgingDiasSemAlteracao'] > 15, 'Bucket'] = '16-30'
            base.loc[base['AgingDiasSemAlteracao'] > 30, 'Bucket'] = '31-60'
            base.loc[base['AgingDiasSemAlteracao'] > 60, 'Bucket'] = '60+'
            summary = base.groupby('Status', dropna=False).agg(WorkItems=('ID', 'count'), AgingMedio=('AgingDiasSemAlteracao', 'mean')).reset_index()
            summary['AgingMedio'] = pd.to_numeric(summary['AgingMedio'], errors='coerce').round(1)
            fig = px.bar(base.groupby(['Status', 'Bucket'], dropna=False).size().reset_index(name='WorkItems'),
                         x='Status', y='WorkItems', color='Bucket', barmode='stack', template='plotly_white',
                         title='Fila de decisão (parametrizada) por status e aging')
            fig.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            return html.Div([
                html.H3('Fila de Decisão (Parametrizada)', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(summary, 'Resumo da fila de decisão (statuses configurados na UI)', 'table-portfolio-decision-queue-cfg')
            ], style={'marginTop': '24px'})

        def render_dynamic_sla_aging(items_df):
            if items_df is None or items_df.empty:
                return html.Div([html.H3('SLA de Aging por Tipo/Status'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = items_df.copy()
            base = base[base.get('IsOpen', False) == True].copy() if 'IsOpen' in base.columns else base
            if base.empty:
                return html.Div([html.H3('SLA de Aging por Tipo/Status'), html.P('Sem itens abertos para avaliar SLA.')], style={'marginTop': '20px'})
            base['AgingDiasSemAlteracao'] = pd.to_numeric(base['AgingDiasSemAlteracao'], errors='coerce')
            tipo_cfg = cfg_sla_aging.get('tipo', {}) if isinstance(cfg_sla_aging, dict) else {}
            status_cfg = cfg_sla_aging.get('status', {}) if isinstance(cfg_sla_aging, dict) else {}
            tipo_map_norm = {normalize_text(k): float(v) for k, v in (tipo_cfg or {}).items() if str(k).strip()}
            status_map_norm = {normalize_text(k): float(v) for k, v in (status_cfg or {}).items() if str(k).strip()}
            base['SLA Tipo (dias)'] = base['TipoNorm'].map(tipo_map_norm)
            base['SLA Status (dias)'] = base['StatusNorm'].map(status_map_norm)
            base['Dentro SLA Tipo'] = np.where(base['SLA Tipo (dias)'].notna(), base['AgingDiasSemAlteracao'] <= base['SLA Tipo (dias)'], np.nan)
            base['Dentro SLA Status'] = np.where(base['SLA Status (dias)'].notna(), base['AgingDiasSemAlteracao'] <= base['SLA Status (dias)'], np.nan)
            tipo_eval = base[base['SLA Tipo (dias)'].notna()].copy()
            status_eval = base[base['SLA Status (dias)'].notna()].copy()
            tipo_table = pd.DataFrame(columns=['Tipo', 'SLA (dias)', 'Itens', '% Dentro SLA', '% Fora SLA'])
            status_table = pd.DataFrame(columns=['Status', 'SLA (dias)', 'Itens', '% Dentro SLA', '% Fora SLA'])
            if not tipo_eval.empty:
                tipo_table = tipo_eval.groupby('Tipo', dropna=False).agg(
                    **{'SLA (dias)': ('SLA Tipo (dias)', 'first'), 'Itens': ('ID', 'count'), 'Dentro': ('Dentro SLA Tipo', 'sum')}
                ).reset_index()
                tipo_table['% Dentro SLA'] = (tipo_table['Dentro'] / tipo_table['Itens'].replace(0, np.nan) * 100).fillna(0).round(1)
                tipo_table['% Fora SLA'] = (100 - tipo_table['% Dentro SLA']).round(1)
                tipo_table = tipo_table.drop(columns=['Dentro']).sort_values('% Fora SLA', ascending=False, ignore_index=True)
            if not status_eval.empty:
                status_table = status_eval.groupby('Status', dropna=False).agg(
                    **{'SLA (dias)': ('SLA Status (dias)', 'first'), 'Itens': ('ID', 'count'), 'Dentro': ('Dentro SLA Status', 'sum')}
                ).reset_index()
                status_table['% Dentro SLA'] = (status_table['Dentro'] / status_table['Itens'].replace(0, np.nan) * 100).fillna(0).round(1)
                status_table['% Fora SLA'] = (100 - status_table['% Dentro SLA']).round(1)
                status_table = status_table.drop(columns=['Dentro']).sort_values('% Fora SLA', ascending=False, ignore_index=True)
            fig = None
            if not tipo_table.empty:
                fig = px.bar(tipo_table, x='Tipo', y='% Fora SLA', color='% Fora SLA', template='plotly_white',
                             title='SLA de aging por tipo (% fora SLA)', color_continuous_scale=['#2e7d32', '#f9a825', '#c62828'])
                fig.update_layout(height=320, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            children = [html.H3('SLA de Aging por Tipo/Status', style={'textAlign': 'left'})]
            if fig is not None:
                children.append(dcc.Graph(figure=fig))
            children.append(portfolio_table_component(tipo_table, 'SLA aging por Tipo (configurado na UI)', 'table-portfolio-sla-aging-tipo'))
            children.append(portfolio_table_component(status_table, 'SLA aging por Status (configurado na UI)', 'table-portfolio-sla-aging-status'))
            return html.Div(children, style={'marginTop': '24px'})

        def render_mix_explicito_multi_contexto(items_df):
            if items_df is None or items_df.empty:
                return html.Div([html.H3('Mix por Projeto / Tipo / TEAM'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = items_df.copy()
            # Mix explícito consolidado
            mix_projeto = base.groupby('Projeto', dropna=False).size().reset_index(name='WorkItems')
            mix_projeto['% Share'] = (mix_projeto['WorkItems'] / mix_projeto['WorkItems'].sum() * 100).round(1)
            mix_tipo = base.groupby('Tipo', dropna=False).size().reset_index(name='WorkItems')
            mix_tipo['% Share'] = (mix_tipo['WorkItems'] / mix_tipo['WorkItems'].sum() * 100).round(1)
            team_col = 'TeamDisplay' if 'TeamDisplay' in base.columns else None
            mix_team = base.groupby(team_col, dropna=False).size().reset_index(name='WorkItems').rename(columns={team_col: 'Team'}) if team_col else pd.DataFrame()
            if not mix_team.empty:
                mix_team['% Share'] = (mix_team['WorkItems'] / mix_team['WorkItems'].sum() * 100).round(1)

            # Comparação multi-recorte de mix alvo por tipo.
            target_cfg = cfg_target_mix if isinstance(cfg_target_mix, dict) else {}
            global_target = target_cfg.get('global', {}) if isinstance(target_cfg.get('global', {}), dict) else {}
            target_global_norm = {str(k): float(v) for k, v in global_target.items() if str(k).strip()}
            recs = []
            contexts = [('Global', 'GLOBAL', base)]
            for p in sorted(base['Projeto'].fillna('').astype(str).unique()):
                if p:
                    contexts.append(('Projeto', p, base[base['Projeto'].astype(str) == p]))
            if team_col:
                for t in sorted(base[team_col].fillna('').astype(str).unique()):
                    if t:
                        contexts.append(('TEAM', t, base[base[team_col].astype(str) == t]))
            for ctx_type, ctx_name, df_ctx in contexts:
                if df_ctx is None or df_ctx.empty:
                    continue
                counts = df_ctx.groupby('Tipo', dropna=False).size().reset_index(name='WorkItems')
                counts['% Atual'] = (counts['WorkItems'] / counts['WorkItems'].sum() * 100).round(1)
                ctx_target_obj = target_cfg.get(ctx_name, None)
                if not isinstance(ctx_target_obj, dict):
                    ctx_target_obj = target_global_norm
                counts['% Alvo'] = counts['Tipo'].map(lambda x: float(ctx_target_obj.get(str(x), 0.0)) if isinstance(ctx_target_obj, dict) else 0.0).fillna(0.0)
                total_t = float(counts['% Alvo'].sum())
                if total_t > 0:
                    counts['% Alvo'] = (counts['% Alvo'] / total_t * 100).round(1)
                counts['Desvio (pp)'] = (counts['% Atual'] - counts['% Alvo']).round(1)
                counts['ContextoTipo'] = ctx_type
                counts['Contexto'] = ctx_name
                recs.append(counts[['ContextoTipo', 'Contexto', 'Tipo', 'WorkItems', '% Atual', '% Alvo', 'Desvio (pp)']])
            mix_contexto = pd.concat(recs, ignore_index=True) if recs else pd.DataFrame(columns=['ContextoTipo', 'Contexto', 'Tipo', 'WorkItems', '% Atual', '% Alvo', 'Desvio (pp)'])
            fig_mix = px.bar(mix_tipo.sort_values('WorkItems', ascending=False), x='Tipo', y='WorkItems', color='% Share', template='plotly_white',
                             title='Mix explícito por Tipo (escopo atual)', color_continuous_scale=['#1565c0', '#42a5f5'])
            fig_mix.update_layout(height=320, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            return html.Div([
                html.H3('Mix por Projeto / Tipo / TEAM', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig_mix),
                portfolio_table_component(mix_projeto.sort_values('WorkItems', ascending=False), 'Mix por Projeto', 'table-portfolio-mix-projeto'),
                portfolio_table_component(mix_tipo.sort_values('WorkItems', ascending=False), 'Mix por Tipo', 'table-portfolio-mix-tipo'),
                portfolio_table_component(mix_team.sort_values('WorkItems', ascending=False) if not mix_team.empty else mix_team, 'Mix por TEAM', 'table-portfolio-mix-team'),
                portfolio_table_component(mix_contexto, 'Mix alvo por tipo por contexto (global/projeto/team)', 'table-portfolio-mix-contexto-target')
            ], style={'marginTop': '24px'})

        def render_pareto_hhi(df_team_share, df_epic_share):
            if (df_team_share is None or df_team_share.empty) and (df_epic_share is None or df_epic_share.empty):
                return html.Div([html.H3('Pareto & HHI de Concentração'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            sections = [html.H3('Pareto & HHI de Concentração', style={'textAlign': 'left'})]
            hhi_rows = []
            if df_team_share is not None and not df_team_share.empty and '% Share' in df_team_share.columns:
                dft = df_team_share.copy()
                dft = dft.sort_values('TotalItems', ascending=False).reset_index(drop=True)
                dft['rank'] = np.arange(1, len(dft) + 1)
                fig_t = go.Figure()
                fig_t.add_trace(go.Bar(x=dft['Team'], y=dft['% Share'], name='% Share'))
                fig_t.add_trace(go.Scatter(x=dft['Team'], y=dft['% Share Acum'], mode='lines+markers', name='% Acum', yaxis='y2'))
                fig_t.update_layout(
                    title='Pareto de concentração por TEAM',
                    template='plotly_white',
                    height=360,
                    margin=dict(t=60, b=100),
                    xaxis=dict(tickangle=-25),
                    yaxis=dict(title='% Share'),
                    yaxis2=dict(title='% Acum', overlaying='y', side='right', range=[0, 100]),
                    legend=dict(orientation='h', y=-0.2)
                )
                sections.append(dcc.Graph(figure=fig_t))
                hhi_team = float(((pd.to_numeric(dft['% Share'], errors='coerce').fillna(0) / 100.0) ** 2).sum())
                hhi_rows.append({'Escopo': 'TEAM', 'HHI': round(hhi_team, 4), 'N': int(len(dft))})
            if df_epic_share is not None and not df_epic_share.empty and '% Share Itens Fluxo' in df_epic_share.columns:
                dfe = df_epic_share.copy()
                fig_e = go.Figure()
                fig_e.add_trace(go.Bar(x=dfe['EpicID'], y=dfe['% Share Itens Fluxo'], name='% Share itens fluxo'))
                fig_e.add_trace(go.Scatter(x=dfe['EpicID'], y=dfe['% Share Acum'], mode='lines+markers', name='% Acum', yaxis='y2'))
                fig_e.update_layout(
                    title='Pareto de concentração por Épico (itens de fluxo)',
                    template='plotly_white',
                    height=360,
                    margin=dict(t=60, b=100),
                    xaxis=dict(tickangle=-35),
                    yaxis=dict(title='% Share'),
                    yaxis2=dict(title='% Acum', overlaying='y', side='right', range=[0, 100]),
                    legend=dict(orientation='h', y=-0.2)
                )
                sections.append(dcc.Graph(figure=fig_e))
                hhi_epic = float(((pd.to_numeric(dfe['% Share Itens Fluxo'], errors='coerce').fillna(0) / 100.0) ** 2).sum())
                hhi_rows.append({'Escopo': 'Épico (itens fluxo)', 'HHI': round(hhi_epic, 4), 'N': int(len(dfe))})
            hhi_df = pd.DataFrame(hhi_rows)
            sections.append(portfolio_table_component(hhi_df, 'HHI de concentração (quanto maior, mais concentrado)', 'table-portfolio-hhi'))
            return html.Div(sections, style={'marginTop': '24px'})

        total_epicos_visao = int(epicos_por_team_total['QtdEpicos'].sum()) if epicos_por_team_total is not None and not epicos_por_team_total.empty else 0
        total_features_visao = int(features_por_team_total['QtdFeatures'].sum()) if features_por_team_total is not None and not features_por_team_total.empty else 0
        epicos_sem_features_visao = int((epicos_detalhe['QtdFeatures'] == 0).sum()) if epicos_detalhe is not None and not epicos_detalhe.empty else 0
        features_sem_epico_visao = int((features_detalhe['EpicID'].fillna('').astype(str).str.strip() == '').sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        features_sem_filhos_visao = int((features_detalhe['QtdFilhos'] == 0).sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        features_sem_mov_15_visao = int((features_detalhe['DiasSemMovimentacao'] > 15).sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        features_sem_mov_30_visao = int((features_detalhe['DiasSemMovimentacao'] > 30).sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        hist_tasks_sem_feature_visao = int(hist_tasks_sem_feature_por_team['WorkItems'].sum()) if hist_tasks_sem_feature_por_team is not None and not hist_tasks_sem_feature_por_team.empty else 0
        scope_parts = []
        if portfolio_project and portfolio_project != PROJECT_FILTER_ALL_VALUE:
            scope_parts.append(f'TEAM: {portfolio_project}')
        elif effective_portfolio_project:
            scope_parts.append(f'TEAM contém: {effective_portfolio_project}')
        else:
            scope_parts.append('Todos os TEAMs')
        if tipo:
            scope_parts.append(f'Tipo: {tipo}')
        if classe_servico:
            scope_parts.append(f'Classe: {classe_servico}')
        if responsavel:
            scope_parts.append(f'Responsável: {responsavel}')
        if portfolio_quarter and portfolio_quarter != 'ALL':
            scope_parts.append(f'Quarter: {portfolio_quarter}')
        scope_label = ' | '.join(scope_parts)
        portfolio_filter_alert = html.Div()
        if portfolio_filter_notes:
            portfolio_filter_alert = html.Div(
                [html.P(note, style={'margin': '0'}) for note in portfolio_filter_notes],
                style={
                    'margin': '12px auto 0 auto',
                    'maxWidth': '960px',
                    'padding': '10px 12px',
                    'border': '1px solid #f5c2c7',
                    'borderRadius': '8px',
                    'backgroundColor': '#fff5f5',
                    'color': '#842029'
                }
            )
        aging_label_us_20 = (
            'US com mais de 20 dias em processo sem alteração'
            if has_us_items else
            'Épicos com mais de 20 dias em processo sem alteração'
        )
        aging_label_us_comp_20 = (
            'US compromissadas a mais de 20 dias e em processo'
            if has_us_items else
            'Épicos compromissados a mais de 20 dias e em processo'
        )
        kpi_color_epic = '#ef6c00'      # laranja
        kpi_color_feature = '#7b1fa2'   # roxo
        kpi_color_story = '#1565c0'     # azul
        kpi_neutral = '#455a64'

        def portfolio_kpi_style(bg):
            fg = '#111' if bg in {'#ffcc80', '#ffe082'} else 'white'
            return {
                'card_style': {
                    'backgroundColor': bg,
                    'color': fg,
                    'minHeight': '140px',
                },
                'title_style': {'textAlign': 'left', 'fontSize': '15px', 'marginBottom': '6px', 'marginTop': '0', 'fontWeight': 'bold'},
                'value_style': {'textAlign': 'left', 'fontSize': '48px', 'marginTop': '0', 'marginBottom': '0', 'lineHeight': '1.1'},
            }

        high_priority_ids = set()
        high_priority_titles = set()
        manual_high_ids_raw = os.getenv('FLOW_PMO_PORTFOLIO_HIGHEST_IDS', '').strip()
        if manual_high_ids_raw:
            for token in re.split(r'[;,\n]+', manual_high_ids_raw):
                t = str(token).strip()
                if t:
                    high_priority_ids.add(t.upper())
        manual_high_titles_raw = os.getenv('FLOW_PMO_PORTFOLIO_HIGHEST_TITLES', '').strip()
        if manual_high_titles_raw:
            for token in re.split(r'[;,\n]+', manual_high_titles_raw):
                t = str(token).strip()
                if t:
                    high_priority_titles.add(t)
        candidate_projects = []
        if projeto:
            candidate_projects.append(str(projeto).strip().upper())
        if not df_portfolio_full_scope.empty and 'Projeto' in df_portfolio_full_scope.columns:
            for pval in df_portfolio_full_scope['Projeto'].dropna().astype(str).str.strip().unique():
                pkey = str(pval).strip().upper()
                if pkey:
                    candidate_projects.append(pkey)
                    if pkey == 'BT':
                        candidate_projects.extend(['BEFINANCE', 'BF'])

        seen_projects = set()
        for pkey in candidate_projects:
            if not pkey or pkey in seen_projects:
                continue
            seen_projects.add(pkey)
            try:
                down_df = load_project_downstream_items_csv(pkey)
            except Exception:
                down_df = pd.DataFrame()
            if down_df is None or down_df.empty or 'ID' not in down_df.columns:
                continue
            priority_col = None
            for cand in ['Prioridade', 'Priority', 'priority']:
                if cand in down_df.columns:
                    priority_col = cand
                    break
            if not priority_col:
                continue
            mask_high = down_df[priority_col].apply(portfolio_is_highest_priority)
            ids = down_df.loc[mask_high, 'ID'].dropna().astype(str).str.strip()
            if not ids.empty:
                high_priority_ids.update(x.upper() for x in ids if x)

        roadmap_full_section = html.Div([
            html.P(
                'Visão completa por épico (Q1..Q4). A segunda linha dos itens Running mostra o % de avanço no fluxo.',
                style={'color': '#666', 'marginBottom': '10px'}
            ),
            render_portfolio_roadmap_full_epics_view(
                df_portfolio_full_scope,
                selected_quarter='ALL',
                high_priority_ids=high_priority_ids,
                high_priority_titles=high_priority_titles
            )
        ], style={'paddingTop': '10px'})

        resumo_exec_section = html.Div([
            render_thresholds_config_summary(),
            html.Div([
                create_kpi_card('Total de épicos', f"{total_epicos_visao}", class_name='', **portfolio_kpi_style(kpi_color_epic)),
                create_kpi_card('Total de features', f"{total_features_visao}", class_name='', **portfolio_kpi_style(kpi_color_feature)),
                create_kpi_card('Épicos sem features', f"{epicos_sem_features_visao}", class_name='', **portfolio_kpi_style(kpi_color_epic)),
                create_kpi_card('Features sem épico', f"{features_sem_epico_visao}", class_name='', **portfolio_kpi_style(kpi_color_feature)),
                create_kpi_card('Features sem filhos', f"{features_sem_filhos_visao}", class_name='', **portfolio_kpi_style(kpi_color_feature)),
                create_kpi_card('Histórias/Tasks sem feature', f"{hist_tasks_sem_feature_visao}", class_name='', **portfolio_kpi_style(kpi_color_story)),
                create_kpi_card('Sem movimento 15d / 30d', f"{features_sem_mov_15_visao} / {features_sem_mov_30_visao}", class_name='', **portfolio_kpi_style(kpi_neutral)),
            ], style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fill, minmax(190px, 1fr))',
                'gap': '10px',
            }),
            render_executive_tiles(executive_tiles),
            render_quality_cards(quality_por_team, quality_summary),
        ], style={'paddingTop': '10px'})

        alertas_section = render_portfolio_alerts(
            portfolio_alert_kpis,
            portfolio_alerts_severity_summary,
            portfolio_alerts_indicator_summary,
            portfolio_alerts_detail,
            portfolio_alerts_by_team,
            portfolio_alerts_by_project,
            portfolio_technical_readiness_notes,
            portfolio_technical_epic_summary,
            portfolio_technical_items_catalog,
        )

        aging_fluxo_section = html.Div([
            render_flow_health_dynamic(items_base_scope),
            render_q_pendencias_grid(pendencias_q_por_time, pendencias_breakdown, pendencias_detalhe),
            html.Div([
                html.H3('Indicador 2 - Aging WIP por TEAM', style={'textAlign': 'left'}),
                html.Div([
                    html.Div(render_tiles_by_team(aging_us_20, aging_label_us_20, threshold_key='aging_us_20'), className='six columns'),
                    html.Div(render_tiles_by_team(aging_features_40, 'Features com mais de 40 dias em processo sem alteração', threshold_key='aging_features_40'), className='six columns'),
                ], className='row'),
                html.Div([
                    html.Div(render_tiles_by_team(aging_us_comp_20, aging_label_us_comp_20, threshold_key='aging_us_comp_20'), className='six columns'),
                    html.Div(render_tiles_by_team(aging_features_comp_40, 'Features compromissadas a mais de 40 dias e em processo', threshold_key='aging_features_comp_40'), className='six columns'),
                ], className='row'),
            ], style={'marginTop': '20px'}),
            render_aging_por_tipo_projeto(aging_por_tipo, aging_por_projeto),
            render_aging_buckets(aging_buckets_por_team),
            render_decision_queue(decision_queue_aging, decision_queue_summary),
            render_dynamic_decision_queue(items_base_scope),
            render_dynamic_sla_aging(items_base_scope),
            render_data_freshness_dynamic(items_base_scope),
        ], style={'paddingTop': '10px'})

        estrutura_section = html.Div([
            render_estrutura_cobertura(estrutura_cobertura_summary, estrutura_cobertura_por_team),
            html.Div([
                html.Div([
                    html.H4('Visão de Épicos', style={'textAlign': 'center'}),
                    portfolio_table_component(
                        epicos_complexidade,
                        'Épicos por TEAM e complexidade',
                        'table-portfolio-epicos-complexidade'
                    ),
                    portfolio_table_component(
                        epicos_detalhe,
                        'Backlog de Épicos (detalhado)',
                        'table-portfolio-epicos-detalhe'
                    ),
                ], className='six columns'),
                html.Div([
                    html.H4('Visão de Features', style={'textAlign': 'center'}),
                    portfolio_table_component(
                        features_complexidade,
                        'Features por TEAM e complexidade',
                        'table-portfolio-features-complexidade'
                    ),
                    portfolio_table_component(
                        features_detalhe,
                        'Backlog de Features (detalhado)',
                        'table-portfolio-features-detalhe'
                    ),
                ], className='six columns'),
            ], className='row', style={'marginTop': '10px'}),
            portfolio_table_component(
                epicos_fluxo_etapas,
                'Épicos: quantidade de itens por etapa de fluxo',
                'table-portfolio-epicos-fluxo-etapas'
            ),
        ], style={'paddingTop': '10px'})

        workflow_section = html.Div([
            html.Div([
                html.Div([
                    grouped_chart(
                        epicos_status,
                        x_col='Status',
                        y_col='QtdEpicos',
                        color_col='Team',
                        title='Épicos por TEAM e etapa de fluxo'
                    ),
                ], className='six columns'),
                html.Div([
                    grouped_chart(
                        features_status,
                        x_col='Status',
                        y_col='QtdFeatures',
                        color_col='Team',
                        title='Features por TEAM e etapa de fluxo'
                    ),
                ], className='six columns'),
            ], className='row', style={'marginTop': '10px'}),
            render_status_ranking(status_categoria_por_team, status_ranking_por_team),
            render_heatmap_team_status(heatmap_team_status),
            render_status_conformance(workflow_conformance_por_team, status_original_top, status_fora_workflow_top),
            render_dynamic_workflow_conformance(items_base_scope),
        ], style={'paddingTop': '10px'})

        effort_concentracao_section = html.Div([
            render_features_sem_effort(features_sem_effort_por_team),
            render_effort_distribution(effort_features_por_team),
            render_effort_aging_staleness(features_detalhe),
            html.Div([
                html.Div(
                    render_team_total_tiles(epicos_por_team_total, 'QtdEpicos', 'Total de Épicos por TEAM', color='#2e7d32'),
                    className='six columns'
                ),
                html.Div(
                    render_team_total_tiles(features_por_team_total, 'QtdFeatures', 'Total de Features por TEAM', color='#1565c0'),
                    className='six columns'
                ),
            ], className='row', style={'marginTop': '10px'}),
            render_concentracao_epicos(top_epicos_volume, top_epicos_aging),
            render_concentracao_relativa(concentracao_summary, concentracao_team_share, concentracao_epico_share),
            render_pareto_hhi(concentracao_team_share, concentracao_epico_share),
            render_mix_explicito_multi_contexto(items_base_scope),
            render_tipo_balanceamento(tipo_balanceamento),
        ], style={'paddingTop': '10px'})

        not_started_epics = pd.DataFrame()
        if epicos_detalhe is not None and not epicos_detalhe.empty and 'StatusCategoria' in epicos_detalhe.columns:
            not_started_epics = epicos_detalhe[epicos_detalhe['StatusCategoria'] == 'Backlog'].copy()

        not_started_features = pd.DataFrame()
        if features_detalhe is not None and not features_detalhe.empty and 'StatusCategoria' in features_detalhe.columns:
            not_started_features = features_detalhe[features_detalhe['StatusCategoria'] == 'Backlog'].copy()

        not_started_section = html.Div()
        if portfolio_quarter != 'ALL' and (not not_started_epics.empty or not not_started_features.empty):
            children = [html.H4(f"Itens de Portfólio para {portfolio_quarter} Não Iniciados", style={'textAlign': 'left'})]
            if not not_started_epics.empty:
                children.append(portfolio_table_component(
                    not_started_epics[['EpicID', 'Titulo', 'Team', 'Status']],
                    'Épicos não iniciados',
                    'table-portfolio-epics-not-started'
                ))
            if not not_started_features.empty:
                children.append(portfolio_table_component(
                    not_started_features[['FeatureID', 'Titulo', 'Team', 'Status']],
                    'Features não iniciadas',
                    'table-portfolio-features-not-started'
                ))
            not_started_section = html.Div(children, style={'marginTop': '20px'})

        return html.Div([
            html.H3('Painel de Portfólio', style={'textAlign': 'center'}),
            html.P(
                f"Atualizado em: {snapshot['updated_at']} | Escopo: {scope_label} | Fonte: CSV local de portfólio",
                style={'textAlign': 'center', 'color': '#666'}
            ),
            portfolio_filter_alert,
            dcc.Tabs(
                id='tabs-portfolio-tematicas',
                value='portfolio-resumo-executivo',
                children=[
                    dcc.Tab(label='Resumo Executivo', value='portfolio-resumo-executivo', children=[resumo_exec_section]),
                    dcc.Tab(label='Alertas', value='portfolio-alertas', children=[alertas_section]),
                    dcc.Tab(label='One Page Completo', value='portfolio-one-page-completo', children=[roadmap_full_section]),
                    dcc.Tab(label='Aging & Fluxo', value='portfolio-aging-fluxo', children=[aging_fluxo_section]),
                    dcc.Tab(label='Hierarquia & Estrutura', value='portfolio-estrutura', children=[estrutura_section]),
                    dcc.Tab(label='Status & Workflow', value='portfolio-status-workflow', children=[workflow_section]),
                    dcc.Tab(label='Effort & Concentração', value='portfolio-effort-concentracao', children=[effort_concentracao_section]),
                ]
            ),
            not_started_section,
        ], style={'padding': '10px 20px 20px 20px'})

    if tab == 'tab-painel-3x3':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        # Base exibida no painel (respeita todos os filtros ativos).
        df_signal_base = fato.copy()
        if projeto:
            df_signal_base = df_signal_base[df_signal_base['Projeto'] == projeto]
        if tipo:
            df_signal_base = df_signal_base[df_signal_base['TipoDemanda'] == tipo]
        if responsavel:
            df_signal_base = df_signal_base[df_signal_base['Responsavel'] == responsavel]
        if classe_servico:
            df_signal_base = df_signal_base[df_signal_base['ClasseServico'] == classe_servico]
        df_signal_base, _ = apply_selected_lead_time_metric(df_signal_base, projeto, leadtime_stages)

        # Base de referência para thresholds (projeto/tipo), independente de período e responsável.
        df_threshold_base = fato.copy()
        if projeto:
            df_threshold_base = df_threshold_base[df_threshold_base['Projeto'] == projeto]
        if tipo:
            df_threshold_base = df_threshold_base[df_threshold_base['TipoDemanda'] == tipo]
        if classe_servico:
            df_threshold_base = df_threshold_base[df_threshold_base['ClasseServico'] == classe_servico]
        df_threshold_base, _ = apply_selected_lead_time_metric(df_threshold_base, projeto, leadtime_stages)

        weeks = pd.date_range(start=start_ts, end=end_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal.')

        strict_stage_start = bool(leadtime_meta.get('enabled', False))

        def selected_flow_start_series(df_local):
            if df_local is None or getattr(df_local, 'empty', True):
                return pd.Series(dtype='datetime64[ns]')
            s = pd.to_datetime(df_local.get('LeadStart_Selected'), errors='coerce')
            if not strict_stage_start:
                if 'DataBacklog' in df_local.columns:
                    s = s.fillna(df_local['DataBacklog'])
                if 'DataInProgress' in df_local.columns:
                    s = s.fillna(df_local['DataInProgress'])
            return s

        def build_weekly_metrics(df_source, start_ref, end_ref):
            rows = []
            weeks_ref = pd.date_range(start=start_ref, end=end_ref + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
            if len(weeks_ref) < 2:
                return pd.DataFrame()
            flow_start = selected_flow_start_series(df_source)
            for i in range(len(weeks_ref) - 1):
                week_start = weeks_ref[i]
                week_end = weeks_ref[i + 1]
                arrived = df_source[
                    (flow_start >= week_start) &
                    (flow_start < week_end)
                ]
                done = df_source[
                    (df_source['DataDone'] >= week_start) &
                    (df_source['DataDone'] < week_end)
                ]
                wip_items = df_source[
                    (flow_start < week_end) &
                    ((df_source['DataDone'] >= week_end) | pd.isna(df_source['DataDone']))
                ]

                lt_p85 = np.nan
                lt_p50 = np.nan
                lt_done = time_metric_series(done, 'LeadTime_Selected_Dias', non_negative=True)
                if not lt_done.empty:
                    lt_p85 = exact_empirical_percentile(lt_done, 0.85)
                    lt_p50 = exact_empirical_percentile(lt_done, 0.50)

                done_eligible = done[done_time_eligible_mask(done)] if not done.empty else done
                tp = len(done_eligible)
                ar = len(arrived)
                wip = len(wip_items)
                pressure_w, flow_eff_w = calculate_flow_efficiency(ar, tp)
                rows.append({
                    'Semana': week_start.date(),
                    'Chegadas': ar,
                    'Throughput': tp,
                    'WIP': wip,
                    'WIP_Age': (week_end - pd.to_datetime(wip_items.get('LeadStart_Selected'), errors='coerce')).dt.days.mean() if wip > 0 else np.nan,
                    'LeadTime_P85': lt_p85,
                    'FlowEfficiency': flow_eff_w,
                    'Pressure': pressure_w,
                    'QueueEfficiency': flow_eff_w,
                    'WIP_TP_Ratio': (wip / tp) if tp > 0 else np.nan,
                    'Predictability': (lt_p85 / lt_p50) if pd.notna(lt_p85) and pd.notna(lt_p50) and lt_p50 > 0 else np.nan,
                })
            return pd.DataFrame(rows)

        weekly_rows = []
        signal_flow_start = selected_flow_start_series(df_signal_base)
        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]
            arrivals = len(df_signal_base[
                (signal_flow_start >= week_start) &
                (signal_flow_start < week_end)
            ])
            done_week = df_signal_base[
                (df_signal_base['DataDone'] >= week_start) &
                (df_signal_base['DataDone'] < week_end)
            ]
            throughput = len(done_week[done_time_eligible_mask(done_week)]) if not done_week.empty else 0
            wip = len(df_signal_base[
                (signal_flow_start < week_end) &
                ((df_signal_base['DataDone'] >= week_end) | pd.isna(df_signal_base['DataDone']))
            ])
            weekly_rows.append({
                'Semana': week_start.date(),
                'Chegadas': arrivals,
                'Throughput': throughput,
                'WIP': wip,
            })
        weekly_df = pd.DataFrame(weekly_rows)

        # Histórico de referência para thresholds dinâmicos por projeto/tipo.
        date_candidates = []
        threshold_flow_start = selected_flow_start_series(df_threshold_base)
        if not threshold_flow_start.dropna().empty:
            date_candidates.append(threshold_flow_start.dropna().min())
        for col in ['DataDone']:
            if col in df_threshold_base.columns and not df_threshold_base[col].dropna().empty:
                date_candidates.append(df_threshold_base[col].dropna().min())
        if not date_candidates:
            date_candidates = [start_ts]
        hist_start = min(date_candidates)
        hist_end = end_ts
        weekly_hist_df = build_weekly_metrics(df_threshold_base, hist_start, hist_end)

        df_done_period = df_signal_base[
            (df_signal_base['DataDone'] >= start_ts) &
            (df_signal_base['DataDone'] <= end_ts)
        ].copy()
        df_done_period_eligible = df_done_period[done_time_eligible_mask(df_done_period)].copy()
        demand_date = selected_flow_start_series(df_signal_base)
        df_arrived_period = df_signal_base[
            (demand_date >= start_ts) &
            (demand_date <= end_ts)
        ]
        if not demand_date.dropna().empty:
            df_demand_period = df_signal_base[
                (demand_date >= start_ts) &
                (demand_date <= end_ts)
            ]
            df_inventory_start = df_signal_base[
                (demand_date < start_ts) &
                ((df_signal_base['DataDone'] >= start_ts) | pd.isna(df_signal_base['DataDone']))
            ]
            df_inventory_end = df_signal_base[
                (demand_date <= end_ts) &
                ((df_signal_base['DataDone'] > end_ts) | pd.isna(df_signal_base['DataDone']))
            ]
            use_backlog_for_inventory = True
            demand_label = "itens comprometidos no período (etapas selecionadas/início)"
        else:
            df_demand_period = df_arrived_period
            use_backlog_for_inventory = False
            demand_label = "itens que iniciaram o fluxo no período"

        df_wip_start = df_signal_base[
            (demand_date < start_ts) &
            ((df_signal_base['DataDone'] >= start_ts) | pd.isna(df_signal_base['DataDone']))
        ]
        df_wip_end = df_signal_base[
            (demand_date <= end_ts) &
            ((df_signal_base['DataDone'] > end_ts) | pd.isna(df_signal_base['DataDone']))
        ]
        if not use_backlog_for_inventory:
            df_inventory_start = df_wip_start.copy()
            df_inventory_end = df_wip_end.copy()

        throughput_avg = weekly_df['Throughput'].mean() if not weekly_df.empty else np.nan
        arrivals_avg = weekly_df['Chegadas'].mean() if not weekly_df.empty else np.nan
        wip_avg = weekly_df['WIP'].mean() if not weekly_df.empty else np.nan
        wip_current = float(weekly_df['WIP'].iloc[-1]) if not weekly_df.empty else np.nan
        wip_age = (
            end_ts - pd.to_datetime(df_wip_end.get('LeadStart_Selected'), errors='coerce')
        ).dt.days.mean() if not df_wip_end.empty else np.nan
        throughput_total = float(len(df_done_period_eligible))
        inflow_total = float(len(df_arrived_period))
        demand_total = float(len(df_demand_period))
        capacity_total = throughput_total
        wip_start_count = float(len(df_wip_start))
        wip_end_count = float(len(df_wip_end))
        inventory_start_count = float(len(df_inventory_start)) if isinstance(df_inventory_start, pd.DataFrame) else np.nan
        inventory_end_count = float(len(df_inventory_end)) if isinstance(df_inventory_end, pd.DataFrame) else np.nan
        inventory_growth = inventory_end_count - inventory_start_count if pd.notna(inventory_start_count) and pd.notna(inventory_end_count) else np.nan
        wip_growth = wip_end_count - wip_start_count
        weeks_count = max(1, len(weeks) - 1)
        throughput_weekly_avg = throughput_total / weeks_count if weeks_count > 0 else np.nan
        inventory_weeks = (inventory_end_count / throughput_weekly_avg) if throughput_weekly_avg > 0 and pd.notna(inventory_end_count) else np.nan
        capacity_label = "itens concluídos no período (throughput)"

        lead_time_p85 = np.nan
        lead_time_p50 = np.nan
        lead_time_p98 = np.nan
        lt_done_period = time_metric_series(df_done_period, 'LeadTime_Selected_Dias', non_negative=True)
        if not lt_done_period.empty:
            lead_time_p85 = exact_empirical_percentile(lt_done_period, 0.85)
            lead_time_p50 = exact_empirical_percentile(lt_done_period, 0.50)
            lead_time_p98 = exact_empirical_percentile(lt_done_period, 0.98)

        pressure_ratio, queue_efficiency = calculate_flow_efficiency(arrivals_avg, throughput_avg)
        wip_tp_ratio = wip_avg / throughput_avg if pd.notna(wip_avg) and pd.notna(throughput_avg) and throughput_avg > 0 else np.nan
        predictability = lead_time_p85 / lead_time_p50 if pd.notna(lead_time_p85) and pd.notna(lead_time_p50) and lead_time_p50 > 0 else np.nan
        risk_forecasting_ratio = lead_time_p98 / lead_time_p50 if pd.notna(lead_time_p98) and pd.notna(lead_time_p50) and lead_time_p50 > 0 else np.nan
        demand_vs_capacity_pct = ((demand_total - capacity_total) / capacity_total * 100.0) if capacity_total > 0 else np.nan
        inflow_vs_outflow_pct = ((inflow_total - throughput_total) / throughput_total * 100.0) if throughput_total > 0 else np.nan
        commitment_rate = (throughput_total / demand_total * 100.0) if demand_total > 0 else np.nan
        commit_times = pd.Series(dtype='float64')
        if not df_arrived_period.empty:
            # Tempo para Commit = da entrada base (backlog) até a etapa de compromisso selecionada.
            if {'DataBacklog', 'LeadStart_Selected'}.issubset(df_arrived_period.columns):
                commit_times = (
                    pd.to_datetime(df_arrived_period['LeadStart_Selected'], errors='coerce') -
                    pd.to_datetime(df_arrived_period['DataBacklog'], errors='coerce')
                ).dt.days
            commit_times = pd.to_numeric(commit_times, errors='coerce').dropna()
            commit_times = commit_times[commit_times >= 0]
        time_to_commit_p85 = exact_empirical_percentile(commit_times, 0.85) if not commit_times.empty else np.nan

        tipo_demanda = df_done_period_eligible['TipoDemanda'] if 'TipoDemanda' in df_done_period_eligible.columns else pd.Series(dtype='object')
        tp_valor = int((tipo_demanda == TYPE_DEV).sum()) if not tipo_demanda.empty else 0
        tp_falha = int((tipo_demanda == TYPE_ISSUES).sum()) if not tipo_demanda.empty else 0
        tp_base_valor_falha = tp_valor + tp_falha
        tp_valor_pct = (tp_valor / tp_base_valor_falha * 100.0) if tp_base_valor_falha > 0 else np.nan
        tp_falha_pct = (tp_falha / tp_base_valor_falha * 100.0) if tp_base_valor_falha > 0 else np.nan

        def classify_direction(value, good_limit, warn_limit, lower_is_better=True):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            if lower_is_better:
                if value <= good_limit:
                    return ('Saudável', '#2e7d32')
                if value <= warn_limit:
                    return ('Atenção', '#f9a825')
                return ('Crítico', '#c62828')
            if value >= good_limit:
                return ('Saudável', '#2e7d32')
            if value >= warn_limit:
                return ('Atenção', '#f9a825')
            return ('Crítico', '#c62828')

        def fmt_value(value, pattern):
            if pd.isna(value):
                return '—'
            return pattern.format(value)

        def classify_forecasting_risk(value):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            if value < 6:
                return ('RISCO MODERADO', '#2e7d32')
            return ('RISCO ALTO', '#ef7d32')

        def classify_pressure(value):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            if value <= 0.80:
                return ('OK', '#2e7d32')
            if value <= 0.90:
                return ('ATENÇÃO', '#f9a825')
            if value <= 0.95:
                return ('CRÍTICO', '#c62828')
            return ('EXTREMAMENTE CRÍTICO', '#7f0000')

        def classify_efficiency(value):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            # Eficiência (1 - rho) é o inverso da pressão rho.
            if value >= 0.20:
                return ('OK', '#2e7d32')
            if value >= 0.10:
                return ('ATENÇÃO', '#f9a825')
            if value >= 0.05:
                return ('CRÍTICO', '#c62828')
            return ('EXTREMAMENTE CRÍTICO', '#7f0000')

        def classify_throughput_mix(falha_pct):
            if pd.isna(falha_pct):
                return ('Sem base', '#9e9e9e')
            if falha_pct <= 20:
                return ('OK', '#2e7d32')
            if falha_pct <= 35:
                return ('ATENÇÃO', '#f9a825')
            return ('CRÍTICO', '#c62828')

        def cv_percent(series):
            s = pd.Series(series).dropna()
            if len(s) < 2:
                return np.nan
            mean = s.mean()
            if pd.isna(mean) or abs(mean) < 1e-9:
                return np.nan
            return (s.std() / abs(mean)) * 100.0

        def classify_cv(cv_value):
            if pd.isna(cv_value):
                return ('Sem base', '#9e9e9e')
            if cv_value <= 30:
                return ('OK (VERDE)', '#2e7d32')
            if cv_value <= 50:
                return ('RAZOÁVEL', '#f9a825')
            if cv_value <= 65:
                return ('RUIM', '#ef6c00')
            if cv_value <= 80:
                return ('CRÍTICO', '#c62828')
            return ('EXTREMAMENTE CRÍTICO', '#7f0000')

        wip_cv_status = classify_cv(cv_percent(weekly_hist_df.get('WIP', pd.Series(dtype=float))))
        lt_cv_status = classify_cv(cv_percent(weekly_hist_df.get('LeadTime_P85', pd.Series(dtype=float))))
        throughput_cv_status = classify_cv(cv_percent(weekly_hist_df.get('Throughput', pd.Series(dtype=float))))
        arrivals_cv_status = classify_cv(cv_percent(weekly_hist_df.get('Chegadas', pd.Series(dtype=float))))
        predictability_status = classify_direction(predictability, 1.8, 2.2, lower_is_better=True)

        tp_relacao_display = (
            f"{tp_valor_pct:.1f}% x {tp_falha_pct:.1f}%" if pd.notna(tp_valor_pct) and pd.notna(tp_falha_pct) else '—'
        )
        tp_relacao_status = classify_throughput_mix(tp_falha_pct)

        # Catálogo único de métricas para todo o painel (id único por indicador).
        metric_catalog = {
            'demand_total': {'value': demand_total},
            'capacity_total': {'value': capacity_total},
            'demand_vs_capacity_pct': {'value': demand_vs_capacity_pct},
            'inflow_total': {'value': inflow_total},
            'outflow_total': {'value': throughput_total},
            'inflow_vs_outflow_pct': {'value': inflow_vs_outflow_pct},
            'inventory_growth': {'value': inventory_growth},
            'wip_growth': {'value': wip_growth},
            'inventory_size': {
                'title': 'Tamanho do Inventário',
                'value': inventory_end_count,
                'format': '{:.0f}',
                'unit': 'itens de fluxo',
                'note': f"({inventory_weeks:.1f} semanas de inventário)" if pd.notna(inventory_weeks) else "(sem base de semanas de inventário)",
            },
            'commitment_rate': {
                'title': 'Taxa de Comprometimento',
                'value': commitment_rate,
                'format': '{:.0f}%',
                'unit': 'throughput / demanda',
            },
            'time_to_commit_p85': {
                'title': 'Tempo para Commit (P85)',
                'value': time_to_commit_p85,
                'format': '{:.0f}',
                'unit': 'dias',
            },
            'wip_age_avg': {
                'title': 'WIP Age (médio)',
                'value': wip_age,
                'format': '{:.0f}',
                'unit': 'dias',
            },
            'throughput_total': {
                'title': 'Throughput (Done s/ cancel.)',
                'value': throughput_total,
                'format': '{:.0f}',
                'unit': 'itens de fluxo',
                'note': '(período selecionado, elegíveis para tempo)',
            },
            'wip_avg_week': {'title': 'WIP médio (semana)', 'value': wip_avg, 'format': '{:.1f} itens', 'status': wip_cv_status},
            'lead_time_p85': {'title': 'Lead Time P85', 'value': lead_time_p85, 'format': '{:.1f} dias', 'status': lt_cv_status},
            'throughput_avg_week': {'title': 'Vazão média semanal', 'value': throughput_avg, 'format': '{:.1f} itens/sem', 'status': throughput_cv_status},
            'arrivals_avg_week': {'title': 'Taxa de chegada média', 'value': arrivals_avg, 'format': '{:.1f} itens/sem', 'status': arrivals_cv_status},
            'flow_efficiency': {'title': 'Eficiência (1 - ρ)', 'value': queue_efficiency, 'format': '{:.2f}', 'status': classify_efficiency(queue_efficiency)},
            'flow_pressure': {'title': 'Pressão de fluxo (chegada/vazão)', 'value': pressure_ratio, 'format': '{:.2f}', 'status': classify_pressure(pressure_ratio)},
            'predictability': {'title': 'Previsibilidade (P85/P50)', 'value': predictability, 'format': '{:.2f}', 'status': predictability_status},
            'wip_current': {'title': 'WIP atual (fim do período)', 'value': wip_current, 'format': '{:.0f} itens', 'status': wip_cv_status},
            'forecast_risk': {'title': 'Risco Forecasting (P98/Mediana)', 'value': risk_forecasting_ratio, 'format': '{:.2f}', 'status': classify_forecasting_risk(risk_forecasting_ratio)},
            'throughput_mix': {'title': 'Throughput valor x falha (%)', 'value': tp_relacao_display, 'format': '{}', 'status': tp_relacao_status},
        }

        reference_metric_ids = [
            'inventory_size',
            'commitment_rate',
            'time_to_commit_p85',
            'wip_age_avg',
            'throughput_total',
        ]
        executive_metric_ids = [
            'wip_avg_week',
            'lead_time_p85',
            'throughput_avg_week',
            'arrivals_avg_week',
            'flow_efficiency',
            'flow_pressure',
            'predictability',
            'wip_current',
            'forecast_risk',
            'throughput_mix',
        ]
        reference_metric_set = set(reference_metric_ids)
        executive_metric_ids = [mid for mid in executive_metric_ids if mid not in reference_metric_set]

        cards = []
        for metric_id in executive_metric_ids:
            metric = metric_catalog[metric_id]
            title = metric['title']
            raw_value = metric['value']
            value_pattern = metric['format']
            status_label, status_color = metric['status']
            cards.append(
                html.Div([
                    html.Div(status_label, style={'fontSize': '12px', 'fontWeight': 'bold', 'color': status_color, 'textTransform': 'uppercase'}),
                    html.H4(title, style={'marginTop': '8px', 'marginBottom': '8px', 'fontSize': '17px'}),
                    html.Div(fmt_value(raw_value, value_pattern), style={'fontSize': '30px', 'fontWeight': 'bold', 'lineHeight': '1.1'}),
                ], style={
                    'backgroundColor': 'white',
                    'border': '1px solid #e5e5e5',
                    'borderTop': f'6px solid {status_color}',
                    'borderRadius': '10px',
                    'padding': '14px',
                    'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
                    'minHeight': '150px',
                })
            )

        card_rows = []
        for idx in range(0, len(cards), 3):
            card_rows.append(
                html.Div(
                    [html.Div(cards[i], className='four columns') for i in range(idx, min(idx + 3, len(cards)))],
                    className='row',
                    style={'marginTop': '14px'} if idx > 0 else {},
                )
            )

        demand_capacity_max = max(metric_catalog['demand_total']['value'], metric_catalog['capacity_total']['value'], 1.0)
        demand_bar_h = f"{max(18, int((metric_catalog['demand_total']['value'] / demand_capacity_max) * 92))}px"
        capacity_bar_h = f"{max(18, int((metric_catalog['capacity_total']['value'] / demand_capacity_max) * 92))}px"
        inflow_outflow_max = max(metric_catalog['inflow_total']['value'], metric_catalog['outflow_total']['value'], 1.0)
        inflow_bar_h = f"{max(18, int((metric_catalog['inflow_total']['value'] / inflow_outflow_max) * 92))}px"
        outflow_bar_h = f"{max(18, int((metric_catalog['outflow_total']['value'] / inflow_outflow_max) * 92))}px"

        ref_panel_bg = '#f3f5f7'
        ref_card_bg = '#f3f5f7'
        ref_border = '1px solid #2b9be8'
        ref_radius = '12px'
        muted_txt = '#7b8694'
        title_txt = '#3d4b59'
        bar_primary = '#2cb3ad'
        bar_secondary = '#176ea4'
        dot_gray = '#b8c0c8'
        dot_orange = '#f1b236'
        dot_teal = '#33b7b2'

        def indicator_dots(active_color):
            return html.Div([
                html.Div(style={'width': '7px', 'height': '7px', 'borderRadius': '50%', 'backgroundColor': active_color, 'marginBottom': '6px'}),
                html.Div(style={'width': '7px', 'height': '7px', 'borderRadius': '50%', 'backgroundColor': dot_orange if active_color != dot_orange else dot_gray, 'marginBottom': '6px'}),
                html.Div(style={'width': '7px', 'height': '7px', 'borderRadius': '50%', 'backgroundColor': dot_gray}),
            ], style={'position': 'absolute', 'top': '10px', 'right': '10px'})

        reference_tile_cards = []
        for metric_id in reference_metric_ids:
            metric = metric_catalog[metric_id]
            tile_children = [
                html.H6(metric['title'], style={'marginBottom': '4px'}),
                html.Div(fmt_value(metric['value'], metric['format']), style={'fontSize': '38px', 'fontWeight': 'bold', 'lineHeight': '1.0'}),
            ]
            if metric.get('unit'):
                tile_children.append(html.P(metric['unit'], style={'marginBottom': '0'}))
            if metric.get('note'):
                tile_children.append(html.P(metric['note'], style={'fontSize': '12px', 'marginTop': '6px', 'color': '#555'}))
            reference_tile_cards.append(
                html.Div(tile_children, style={
                    'flex': '1 1 150px',
                    'backgroundColor': ref_card_bg,
                    'border': ref_border,
                    'borderRadius': ref_radius,
                    'padding': '10px',
                    'minHeight': '135px',
                    'position': 'relative',
                })
            )

        flow_reference_cards = html.Div([
            html.H4("Indicadores de Referência do Fluxo", style={'textAlign': 'center', 'marginBottom': '12px', 'marginTop': '8px'}),
            html.Div([
                html.Div([
                    indicator_dots(dot_teal),
                    html.P("Demanda vs Capacidade", style={'fontSize': '28px', 'color': title_txt, 'marginBottom': '10px'}),
                    html.P(
                        f"Demanda = {demand_label}. Capacidade = {capacity_label}.",
                        style={'fontSize': '12px', 'color': '#5f6e7b', 'marginTop': '-6px', 'marginBottom': '8px'}
                    ),
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Div(style={
                                    'width': '38px',
                                    'height': demand_bar_h,
                                    'backgroundColor': bar_primary,
                                    'borderRadius': '0',
                                    'margin': '0 auto',
                                }),
                                html.P('Demanda', style={'fontSize': '16px', 'marginTop': '8px', 'marginBottom': '0', 'textAlign': 'center', 'color': '#4f5965'}),
                            ], style={'display': 'inline-block', 'width': '50%'}),
                            html.Div([
                                html.Div(style={
                                    'width': '38px',
                                    'height': capacity_bar_h,
                                    'backgroundColor': bar_secondary,
                                    'borderRadius': '0',
                                    'margin': '0 auto',
                                }),
                                html.P('Capacidade', style={'fontSize': '16px', 'marginTop': '8px', 'marginBottom': '0', 'textAlign': 'center', 'color': '#4f5965'}),
                            ], style={'display': 'inline-block', 'width': '50%'}),
                        ], style={'width': '160px', 'display': 'flex', 'alignItems': 'flex-end', 'justifyContent': 'center'}),
                        html.Ul([
                            html.Li(
                                f"Demanda {abs(metric_catalog['demand_vs_capacity_pct']['value']):.1f}% acima da capacidade."
                                if pd.notna(metric_catalog['demand_vs_capacity_pct']['value']) and metric_catalog['demand_vs_capacity_pct']['value'] >= 0
                                else (
                                    f"Demanda {abs(metric_catalog['demand_vs_capacity_pct']['value']):.1f}% abaixo da capacidade."
                                    if pd.notna(metric_catalog['demand_vs_capacity_pct']['value'])
                                    else "Sem base para comparação."
                                )
                            ),
                            html.Li(
                                f"Inventário cresceu em {int(abs(metric_catalog['inventory_growth']['value']))} itens de fluxo."
                                if pd.notna(metric_catalog['inventory_growth']['value']) and metric_catalog['inventory_growth']['value'] >= 0
                                else (
                                    f"Inventário reduziu em {int(abs(metric_catalog['inventory_growth']['value']))} itens de fluxo."
                                    if pd.notna(metric_catalog['inventory_growth']['value'])
                                    else "Sem base para variação de inventário."
                                )
                            ),
                        ], style={'marginBottom': '0', 'fontSize': '16px', 'color': muted_txt, 'lineHeight': '1.7'}),
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '18px'}),
                ], className='six columns', style={
                    'position': 'relative',
                    'backgroundColor': ref_card_bg,
                    'border': ref_border,
                    'borderRadius': ref_radius,
                    'padding': '12px 12px 22px 12px',
                    'minHeight': '260px',
                }),
                html.Div([
                    indicator_dots(dot_orange),
                    html.P("Entrada vs Saída", style={'fontSize': '28px', 'color': title_txt, 'marginBottom': '10px'}),
                    html.P(
                        "Entrada = itens comprometidos no período (etapas selecionadas). Saída = itens concluídos no período.",
                        style={'fontSize': '12px', 'color': '#5f6e7b', 'marginTop': '-6px', 'marginBottom': '8px'}
                    ),
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Div(style={
                                    'width': '38px',
                                    'height': inflow_bar_h,
                                    'backgroundColor': bar_primary,
                                    'borderRadius': '0',
                                    'margin': '0 auto',
                                }),
                                html.P('Compromisso', style={'fontSize': '16px', 'marginTop': '8px', 'marginBottom': '0', 'textAlign': 'center', 'color': '#4f5965'}),
                            ], style={'display': 'inline-block', 'width': '50%'}),
                            html.Div([
                                html.Div(style={
                                    'width': '38px',
                                    'height': outflow_bar_h,
                                    'backgroundColor': bar_secondary,
                                    'borderRadius': '0',
                                    'margin': '0 auto',
                                }),
                                html.P('Saída', style={'fontSize': '16px', 'marginTop': '8px', 'marginBottom': '0', 'textAlign': 'center', 'color': '#4f5965'}),
                            ], style={'display': 'inline-block', 'width': '50%'}),
                        ], style={'width': '160px', 'display': 'flex', 'alignItems': 'flex-end', 'justifyContent': 'center'}),
                        html.Ul([
                            html.Li(
                                f"Entrada {abs(metric_catalog['inflow_vs_outflow_pct']['value']):.1f}% acima da saída."
                                if pd.notna(metric_catalog['inflow_vs_outflow_pct']['value']) and metric_catalog['inflow_vs_outflow_pct']['value'] >= 0
                                else (
                                    f"Entrada {abs(metric_catalog['inflow_vs_outflow_pct']['value']):.1f}% abaixo da saída."
                                    if pd.notna(metric_catalog['inflow_vs_outflow_pct']['value'])
                                    else "Sem base para comparação."
                                )
                            ),
                            html.Li(
                                f"WIP cresceu em {int(abs(metric_catalog['wip_growth']['value']))} itens de fluxo."
                                if metric_catalog['wip_growth']['value'] >= 0
                                else f"WIP reduziu em {int(abs(metric_catalog['wip_growth']['value']))} itens de fluxo."
                            ),
                        ], style={'marginBottom': '0', 'fontSize': '16px', 'color': muted_txt, 'lineHeight': '1.7'}),
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '18px'}),
                ], className='six columns', style={
                    'position': 'relative',
                    'backgroundColor': ref_card_bg,
                    'border': ref_border,
                    'borderRadius': ref_radius,
                    'padding': '12px 12px 22px 12px',
                    'minHeight': '260px',
                }),
            ], className='row', style={'marginBottom': '12px'}),
            html.Div(reference_tile_cards, style={
                'display': 'flex',
                'flexWrap': 'wrap',
                'gap': '10px',
                'marginTop': '8px',
            }),
        ], style={'maxWidth': '1200px', 'margin': '0 auto 20px auto', 'padding': '0 6px', 'backgroundColor': ref_panel_bg})

        return html.Div([
            html.H3("Painel Principal de Gestão de Fluxo", style={'textAlign': 'center'}),
            leadtime_selection_summary,
            html.P(
                "Sinais executivos de fluxo para o filtro ativo de projeto e período. "
                "Semáforo por CV: OK (<=30%), Razoável (>30% e <=50%), Ruim (>50% e <=65%), Crítico (>65% e <=80%) e Extremamente Crítico (>80%). "
                "Limites fixos: Pressão de fluxo (rho=chegada/vazão) OK <=0.80, Atenção >0.80 e <=0.90, Crítico >0.90 e <=0.95, Extremamente Crítico >0.95. "
                "Eficiência (1-rho) inversa: OK >=0.20, Atenção >=0.10 e <0.20, Crítico >=0.05 e <0.10, Extremamente Crítico <0.05.",
                style={'textAlign': 'center', 'color': '#666', 'marginBottom': '20px'}
            ),
            flow_reference_cards,
            html.Div(card_rows, style={'maxWidth': '1200px', 'margin': '0 auto'}),
        ])

    if tab == 'tab-fluxo':
        start_ts = pd.to_datetime(start_date) if start_date else fato['DataDone'].min()
        end_ts = pd.to_datetime(end_date) if end_date else pd.to_datetime('today')

        df_flow = fato.copy()
        if projeto:
            df_flow = df_flow[df_flow['Projeto'] == projeto]
        if tipo:
            df_flow = df_flow[df_flow['TipoDemanda'] == tipo]
        if responsavel:
            df_flow = df_flow[df_flow['Responsavel'] == responsavel]
        if classe_servico:
            df_flow = df_flow[df_flow['ClasseServico'] == classe_servico]
        df_flow, flow_lead_meta = apply_selected_lead_time_metric(df_flow, projeto, leadtime_stages)

        mask_started_until_end = df_flow['DataInProgress'].isna() | (df_flow['DataInProgress'] <= end_ts)
        mask_not_finished_before_start = df_flow['DataDone'].isna() | (df_flow['DataDone'] >= start_ts)
        df_flow = df_flow[mask_started_until_end & mask_not_finished_before_start].copy()
        df_flow_done_period = df_flow[
            (df_flow['DataDone'] >= start_ts) &
            (df_flow['DataDone'] <= end_ts)
        ].copy()
        df_flow_done_period_eligible = df_flow_done_period[done_time_eligible_mask(df_flow_done_period)].copy()

        if df_flow.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        # --- 1. Calcular Métricas ---
        metrics = {}
        lead_time_selected = time_metric_series(df_flow_done_period_eligible, 'LeadTime_Selected_Dias', non_negative=True)
        tempo_exec = time_metric_series(df_flow_done_period_eligible, 'TempoExecucao_Dias', non_negative=True)
        tempo_backlog = time_metric_series(df_flow_done_period_eligible, 'TempoBacklog_Dias', non_negative=True)
        tempo_bloqueio = time_metric_series(df_flow_done_period_eligible, 'TempoBloqueioDias', non_negative=True)
        tempo_espera = time_metric_series(df_flow_done_period_eligible, 'TempoEsperaIntermediariaDias', non_negative=True)

        if not lead_time_selected.empty:
            metrics['Lead Time Médio (dias)'] = lead_time_selected.mean()
            metrics['Lead Time P85 (dias)'] = exact_empirical_percentile(lead_time_selected, 0.85)
            metrics['Lead Time Mediano (dias)'] = exact_empirical_percentile(lead_time_selected, 0.50)
        if not tempo_exec.empty:
            metrics['Cycle Time Médio (dias)'] = tempo_exec.mean()
            metrics['Cycle Time Mediano (dias)'] = tempo_exec.median()
        if not tempo_backlog.empty:
            # Assumindo que "Tempo até Primeiro Movimento" é equivalente ao tempo em backlog.
            metrics['Tempo em Backlog Médio (dias)'] = tempo_backlog.mean()
            metrics['Tempo até Primeiro Movimento (dias)'] = tempo_backlog.mean()
        arrivals_period = len(df_flow[
            (df_flow['DataInProgress'] >= start_ts) &
            (df_flow['DataInProgress'] <= end_ts)
        ])
        throughput_period = len(df_flow_done_period_eligible)
        pressure_period, efficiency_period = calculate_flow_efficiency(arrivals_period, throughput_period)
        if pd.notna(efficiency_period):
            metrics['Eficiência de Fluxo (1 - ρ)'] = efficiency_period
        if pd.notna(pressure_period):
            metrics['Pressão de Fluxo (ρ = λ/μ)'] = pressure_period
        if not tempo_bloqueio.empty:
            metrics['Tempo de Bloqueio Médio (dias)'] = tempo_bloqueio.mean()
        if not tempo_espera.empty:
            metrics['Tempo de Espera Intermediária Médio (dias)'] = tempo_espera.mean()
        if 'Bloqueado' in df_flow.columns:
            total_items = len(df_flow)
            blocked_items = df_flow['Bloqueado'].sum()
            metrics['Taxa de Bloqueio (%)'] = (blocked_items / total_items * 100) if total_items > 0 else 0

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}"} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        # --- 2. Criar Gráficos ---
        bottlenecks_df = load_project_bottlenecks_from_model(projeto)
        if bottlenecks_df.empty:
            bottlenecks_df = load_project_bottlenecks_from_csv(projeto)
        if bottlenecks_df.empty:
            bottlenecks_df = compute_flow_bottlenecks(df_flow)

        fig_lead_hist = {}
        lead_hist_component = html.P(
            'Sem dados válidos de Lead Time (>= 0 dias) para o período e filtros selecionados.'
        )
        lead_band_table_component = html.P(
            'Sem dados suficientes para calcular bandas percentílicas exatas de Lead Time.'
        )
        if 'LeadTime_Selected_Dias' in df_flow.columns:
            lead_series = time_metric_series(df_flow_done_period_eligible, 'LeadTime_Selected_Dias', non_negative=True)
            if not lead_series.empty:
                lead_df = pd.DataFrame({'LeadTime_Selected_Dias': lead_series})
                fig_lead_hist = px.histogram(
                    lead_df,
                    x='LeadTime_Selected_Dias',
                    nbins=30,
                    title='Distribuição do Lead Time (dias)',
                )
                fig_lead_hist.update_layout(
                    height=500,
                    xaxis=dict(title='Lead Time (dias)', rangemode='nonnegative'),
                    yaxis=dict(title='Quantidade de itens'),
                )
                lead_hist_component = dcc.Graph(figure=fig_lead_hist)
                lead_bands_df = exact_percentile_band_summary(lead_series)
                lead_band_table_component = dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in lead_bands_df.columns],
                    data=lead_bands_df.to_dict('records'),
                    style_cell={'textAlign': 'center', 'padding': '6px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
                )

        # --- 3. Ranking de Gargalos por Etapa ---
        fig_lead_time_breakdown = {}
        lead_time_breakdown_component = html.P(
            'Sem dados suficientes para calcular o breakdown percentual de lead time por etapa.'
        )
        if bottlenecks_df.empty:
            fig_bottlenecks = {}
            bottlenecks_table = html.P('Sem dados suficientes para calcular gargalos por etapa.')
        else:
            fig_bottlenecks = go.Figure(
                go.Bar(
                    x=bottlenecks_df['Tempo Médio (dias)'],
                    y=bottlenecks_df['Etapa'],
                    orientation='h',
                    text=[
                        f"{lt:.2f} d | vazão: {vz}"
                        for lt, vz in zip(
                            bottlenecks_df['Tempo Médio (dias)'],
                            bottlenecks_df['Vazão da Etapa (itens)'],
                        )
                    ],
                    textposition='outside',
                    marker_color='#1f77b4',
                    marker_line=dict(color='#155a8a', width=1),
                    customdata=bottlenecks_df[['Vazão da Etapa (itens)']].values,
                    hovertemplate='Etapa: %{y}<br>Lead time médio: %{x:.2f} dias'
                                  '<br>Vazão: %{customdata[0]} itens<extra></extra>',
                )
            )
            fig_bottlenecks.update_layout(
                title='Ranking de Gargalos do Fluxo (Maior para Menor)'
                      '<br><sup>Ordenação das etapas críticas por tempo médio</sup>',
                xaxis_title='Tempo médio na etapa (dias)',
                yaxis_title='Etapa',
                template='plotly_white',
                yaxis=dict(autorange='reversed'),
                height=480,
                margin=dict(l=140, r=40, t=70, b=50),
            )

            display_df = bottlenecks_df.copy()
            for c in ['Tempo Médio (dias)', 'Tempo Mediano (dias)', 'P90 (dias)']:
                display_df[c] = display_df[c].round(2)
            bottlenecks_table = dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in display_df.columns],
                data=display_df.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            )

            breakdown_df = bottlenecks_df[['Etapa', 'Tempo Médio (dias)']].copy()
            total_lead_time = breakdown_df['Tempo Médio (dias)'].sum()
            if total_lead_time > 0:
                breakdown_df['Percentual'] = (breakdown_df['Tempo Médio (dias)'] / total_lead_time) * 100
                breakdown_df['Barra'] = 'Lead Time'

                color_map = {
                    'Backlog': '#4C78A8',
                    'Execução': '#59A14F',
                    'Bloqueio': '#E45756',
                    'Espera Intermediária': '#F28E2B',
                }
                stage_order = breakdown_df['Etapa'].tolist()
                fig_lead_time_breakdown = px.bar(
                    breakdown_df,
                    x='Percentual',
                    y='Barra',
                    color='Etapa',
                    orientation='h',
                    text=breakdown_df['Percentual'].map(lambda v: f'{v:.1f}%'),
                    title='Lead Time Breakdown por Etapa do Fluxo (%)',
                    labels={'Percentual': '% do Lead Time', 'Barra': ''},
                    color_discrete_map=color_map,
                    category_orders={'Etapa': stage_order},
                    template='plotly_white',
                    height=320,
                )
                fig_lead_time_breakdown.update_layout(
                    barmode='stack',
                    xaxis=dict(range=[0, 100], ticksuffix='%'),
                    yaxis=dict(showticklabels=False),
                    legend_title_text='Etapa do Fluxo',
                    margin=dict(l=60, r=40, t=70, b=50),
                )
                fig_lead_time_breakdown.update_traces(
                    textposition='inside',
                    insidetextanchor='middle',
                    hovertemplate='Etapa: %{fullData.name}<br>% Lead Time: %{x:.1f}%<extra></extra>',
                )
                lead_time_breakdown_component = dcc.Graph(figure=fig_lead_time_breakdown)

        return html.Div([
            html.H3("Análise Avançada de Fluxo", style={'textAlign': 'center'}),
            leadtime_selection_summary,
            html.P(
                (
                    "Filtro de etapas de Lead Time aplicado aos KPIs de Lead Time desta tela "
                    f"(amostra: {int(len(lead_time_selected))} itens elegíveis). "
                    "O ranking de gargalos por etapa permanece independente dessa seleção."
                ),
                style={'textAlign': 'center', 'color': '#555', 'marginBottom': '10px'}
            ),
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            html.H4("Indicador de Gargalo do Fluxo", style={'textAlign': 'center', 'marginTop': '10px'}),
            html.Div(bottlenecks_table, style={'width': '70%', 'margin': 'auto', 'marginBottom': '20px'}),
            dcc.Graph(figure=fig_bottlenecks),
            html.H4("Lead Time Breakdown", style={'textAlign': 'center', 'marginTop': '20px'}),
            lead_time_breakdown_component,
            lead_hist_component,
            html.H4("Bandas Percentílicas Exatas (Lead Time)", style={'textAlign': 'center', 'marginTop': '20px'}),
            lead_band_table_component,
        ])

    if tab == 'tab-cfd':
        start_ts = pd.to_datetime(start_date) if start_date else fato['DataDone'].min()
        end_ts = pd.to_datetime(end_date) if end_date else pd.to_datetime('today')

        df_flow = fato.copy()
        if projeto:
            df_flow = df_flow[df_flow['Projeto'] == projeto]
        if tipo:
            df_flow = df_flow[df_flow['TipoDemanda'] == tipo]
        if responsavel:
            df_flow = df_flow[df_flow['Responsavel'] == responsavel]

        mask_started_until_end = df_flow['DataInProgress'].isna() | (df_flow['DataInProgress'] <= end_ts)
        mask_not_finished_before_start = df_flow['DataDone'].isna() | (df_flow['DataDone'] >= start_ts)
        df_flow = df_flow[mask_started_until_end & mask_not_finished_before_start].copy()
        if df_flow.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        bottlenecks_df = load_project_bottlenecks_from_model(projeto)
        if bottlenecks_df.empty:
            bottlenecks_df = load_project_bottlenecks_from_csv(projeto)
        if bottlenecks_df.empty:
            bottlenecks_df = compute_flow_bottlenecks(df_flow)

        arrivals_period = len(df_flow[
            (df_flow['DataInProgress'] >= start_ts) &
            (df_flow['DataInProgress'] <= end_ts)
        ])
        throughput_period = int(len(df[done_time_eligible_mask(df)])) if not df.empty else 0
        filtered_done_ids = df.get('ItemID', pd.Series(dtype=str)).tolist()

        cfd_graph_component = html.P('Sem dados suficientes para montar o Cumulative Flow Diagram (CFD).')
        cfd_summary_store = {}
        cfd_summary_default = html.Div(
            'Clique ou passe o mouse sobre um ponto do CFD para ver o quadro de estatísticas sumárias.',
            style={'color': '#666', 'padding': '12px', 'border': '1px dashed #d1d5db', 'borderRadius': '8px'}
        )

        df_cfd, _ = build_cfd_dataframe(df_flow, start_ts=start_ts, end_ts=end_ts)
        if not df_cfd.empty:
            fig_cfd = create_cfd_figure(
                df_cfd,
                bottlenecks_df=bottlenecks_df,
                projeto=projeto,
                filtered_item_ids=filtered_done_ids,
            )
            if isinstance(fig_cfd, go.Figure):
                cfd_graph_component = dcc.Graph(
                    id='cfd-graph',
                    figure=fig_cfd,
                    clear_on_unhover=False,
                    config={'displaylogo': False},
                )
                cfd_summary_store = build_cfd_summary_payload(
                    df_cfd,
                    projeto=projeto,
                    bottlenecks_df=bottlenecks_df,
                    filtered_item_ids=filtered_done_ids,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    arrivals_period=arrivals_period,
                    throughput_period=throughput_period,
                )
                cfd_summary_default = create_cfd_summary_panel(cfd_summary_store)

        return html.Div([
            html.H3("Cumulative Flow Diagram (CFD)", style={'textAlign': 'center'}),
            html.P(
                "Aba dedicada do CFD com modos Macro e Detalhado por Etapas (exato). "
                "O quadro de estatísticas sumárias lê o ponto selecionado no gráfico.",
                style={'textAlign': 'center', 'color': '#666', 'marginBottom': '14px'}
            ),
            dcc.Store(id='cfd-summary-store', data=cfd_summary_store),
            cfd_graph_component,
            html.Div(id='cfd-summary-panel', children=cfd_summary_default, style={'marginTop': '14px'}),
        ])

    if tab == 'tab-estabilidade':
        if df.empty or 'LeadTime_Dias' not in df.columns or df['LeadTime_Dias'].dropna().empty:
            return html.Div('Sem dados de Lead Time para exibir para o período e filtros selecionados.')

        # --- 1. Calcular Métricas de Estabilidade ---
        metrics = {}
        # Throughput
        tp_weekly = df.dropna(subset=['DataDone']).copy()
        tp_weekly['Semana'] = weekly_bucket_start(tp_weekly['DataDone'])
        tp_weekly = tp_weekly.groupby('Semana').size().reset_index(name='Throughput')
        if not tp_weekly.empty and tp_weekly['Throughput'].mean() > 0:
            metrics['Desvio Padrão do Throughput'] = tp_weekly['Throughput'].std()
            metrics['Coeficiente de Variação (%)'] = (tp_weekly['Throughput'].std() / tp_weekly['Throughput'].mean()) * 100

        # Lead Time
        lead_times = time_metric_series(df, 'LeadTime_Dias')
        metrics['Lead Time P50 (dias)'] = exact_empirical_percentile(lead_times, 0.50)
        metrics['Lead Time P75 (dias)'] = exact_empirical_percentile(lead_times, 0.75)
        metrics['Lead Time P95 (dias)'] = exact_empirical_percentile(lead_times, 0.95)

        # Intervalo de Confiança 95% para o Lead Time
        lt_mean = lead_times.mean()
        lt_std = lead_times.std()
        n = len(lead_times)
        if n > 1:
            ci_margin = 1.96 * (lt_std / np.sqrt(n))
            metrics['Intervalo de Confiança 95%'] = f"{lt_mean - ci_margin:.1f} - {lt_mean + ci_margin:.1f} dias"

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}" if isinstance(v, (int, float)) else v} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        # --- 2. Criar Gráficos ---
        fig_throughput_trend = px.line(tp_weekly, x='Semana', y='Throughput', title='Throughput Semanal', markers=True)
        add_statistical_lines(fig_throughput_trend, tp_weekly['Semana'], tp_weekly['Throughput'])
        fig_throughput_trend.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))
        df_lt_plot = df[done_time_eligible_mask(df)].copy()
        fig_lead_time_dist = px.box(df_lt_plot, y='LeadTime_Dias', title='Distribuição de Lead Time e Percentis', points="all")
        fig_lead_time_dist.update_layout(height=500)

        return html.Div([
            html.H3("Análise de Estabilidade", style={'textAlign': 'center'}),
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            dcc.Graph(figure=fig_throughput_trend),
            dcc.Graph(figure=fig_lead_time_dist),
        ])

    if tab == 'tab-saude':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        df_health_base = fato.copy()
        if projeto: df_health_base = df_health_base[df_health_base['Projeto'] == projeto]
        if responsavel: df_health_base = df_health_base[df_health_base['Responsavel'] == responsavel]
        # --- 1. Calcular Métricas de Saúde ---
        arrivals_df = df_health_base[(df_health_base['DataInProgress'] >= start_date_ts) & (df_health_base['DataInProgress'] <= end_date_ts)]
        throughput_df = df_health_base[(df_health_base['DataDone'] >= start_date_ts) & (df_health_base['DataDone'] <= end_date_ts)]
        wip_start_count = len(df_health_base[(df_health_base['DataInProgress'] < start_date_ts) & ((df_health_base['DataDone'] >= start_date_ts) | pd.isna(df_health_base['DataDone']))])
        wip_end_count = len(df_health_base[(df_health_base['DataInProgress'] <= end_date_ts) & ((df_health_base['DataDone'] > end_date_ts) | pd.isna(df_health_base['DataDone']))])

        arrivals_count = len(arrivals_df)
        throughput_count = len(throughput_df)

        metrics = {}
        work_to_be_done = wip_start_count + arrivals_count
        metrics['Taxa Conclusão (%)'] = (throughput_count / work_to_be_done * 100) if work_to_be_done > 0 else 0
        metrics['Ratio Chegada/Throughput'] = arrivals_count / throughput_count if throughput_count > 0 else 0
        metrics['Crescimento WIP (%)'] = ((wip_end_count - wip_start_count) / wip_start_count * 100) if wip_start_count > 0 else (wip_end_count * 100 if wip_end_count > 0 else 0)
        
        lt_throughput = time_metric_series(throughput_df, 'LeadTime_Dias')
        p85_lt = exact_empirical_percentile(lt_throughput, 0.85) if not lt_throughput.empty else 0
        metrics['Itens Vencidos (>P85)'] = (
            len(throughput_df[done_time_eligible_mask(throughput_df) & (pd.to_numeric(throughput_df['LeadTime_Dias'], errors='coerce') > p85_lt)])
            if p85_lt > 0 else 0
        )

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}"} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']], data=kpi_data, style_cell={'textAlign': 'left', 'padding': '5px'}, style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'})

        # --- 2. Criar Gráficos ---
        # Chegadas vs Throughput
        arrivals_weekly = arrivals_df.dropna(subset=['DataInProgress']).copy()
        arrivals_weekly['Semana'] = weekly_bucket_start(arrivals_weekly['DataInProgress'])
        arrivals_weekly = arrivals_weekly.groupby('Semana').size().reset_index(name='Count')
        arrivals_weekly['Métrica'] = 'Chegadas'
        throughput_weekly = throughput_df.dropna(subset=['DataDone']).copy()
        throughput_weekly['Semana'] = weekly_bucket_start(throughput_weekly['DataDone'])
        throughput_weekly = throughput_weekly.groupby('Semana').size().reset_index(name='Count')
        throughput_weekly['Métrica'] = 'Throughput'

        flow_df = pd.concat([arrivals_weekly, throughput_weekly]).sort_values('Semana')
        fig_flow = px.bar(flow_df, x='Semana', y='Count', color='Métrica', barmode='group', title='Chegadas vs. Throughput Semanal', color_discrete_map={'Chegadas': 'blue', 'Throughput': 'green'})
        fig_flow.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        # Tendência do WIP
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        wip_trend_data = []
        for week_end in weeks:
            wip_at_date = len(df_health_base[(df_health_base['DataInProgress'] <= week_end) & ((df_health_base['DataDone'] > week_end) | pd.isna(df_health_base['DataDone']))])
            wip_trend_data.append({'Semana': week_end, 'WIP': wip_at_date})
        
        wip_trend_df = pd.DataFrame(wip_trend_data)
        fig_wip_trend = px.line(wip_trend_df, x='Semana', y='WIP', title='Tendência do WIP Semanal', markers=True) if not wip_trend_df.empty else {}
        if not wip_trend_df.empty:
            add_statistical_lines(fig_wip_trend, wip_trend_df['Semana'], wip_trend_df['WIP'])
            fig_wip_trend.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        return html.Div([
            html.H3("Análise de Saúde do Fluxo", style={'textAlign': 'center'}),
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            dcc.Graph(figure=fig_flow),
            dcc.Graph(figure=fig_wip_trend),
            html.Hr(style={'margin': '30px 0'}),
            render_tab(main_view, 'tab-estabilidade', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, capacity_top_n, capacity_weekly_metric, portfolio_team,
                       pf_backlog_15, pf_backlog_30, pf_fresh_15, pf_fresh_30, pf_decision_statuses, pf_workflow_statuses, pf_sla_aging_json, pf_target_mix_json),
            html.Hr(style={'margin': '30px 0'}),
            render_tab(main_view, 'tab-qualidade', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, capacity_top_n, capacity_weekly_metric, portfolio_team,
                       pf_backlog_15, pf_backlog_30, pf_fresh_15, pf_fresh_30, pf_decision_statuses, pf_workflow_statuses, pf_sla_aging_json, pf_target_mix_json),
        ])

    if tab == 'tab-qualidade':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        # --- 1. Calcular Métricas de Qualidade ---
        defects_count = len(df[df['TipoDemanda'] == TYPE_ISSUES])
        development_count = len(df[df['TipoDemanda'] == TYPE_DEV])
        total_completed = len(df)

        metrics = {}
        metrics['Debt Ratio (% Defeitos)'] = (defects_count / total_completed * 100) if total_completed > 0 else 0
        
        razao = development_count / defects_count if defects_count > 0 else float('inf')
        metrics['Razão Valor/Custo'] = f"{razao:.2f}:1" if razao != float('inf') else "Infinito (sem defeitos)"

        arrivals_base = fato.copy()
        if projeto:
            arrivals_base = arrivals_base[arrivals_base['Projeto'] == projeto]
        if tipo:
            arrivals_base = arrivals_base[arrivals_base['TipoDemanda'] == tipo]
        if responsavel:
            arrivals_base = arrivals_base[arrivals_base['Responsavel'] == responsavel]
        arrivals_count = len(arrivals_base[
            (arrivals_base['DataInProgress'] >= pd.to_datetime(start_date)) &
            (arrivals_base['DataInProgress'] <= pd.to_datetime(end_date))
        ])
        throughput_count = len(df)
        pressure_quality, efficiency_quality = calculate_flow_efficiency(arrivals_count, throughput_count)
        if pd.notna(efficiency_quality):
            metrics['Eficiência de Fluxo (1 - ρ)'] = efficiency_quality
        if pd.notna(pressure_quality):
            metrics['Pressão de Fluxo (ρ = λ/μ)'] = pressure_quality

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}" if isinstance(v, (int, float)) else v} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        )

        # --- 2. Criar Gráfico ---
        by_tipo = df.groupby('TipoDemanda').size().reset_index(name='Count')
        fig_pie = px.pie(by_tipo, names='TipoDemanda', values='Count',
                         title='Distribuição do Throughput por Tipo',
                         color='TipoDemanda', color_discrete_map=color_map)
        fig_pie.update_layout(height=500)

        razao_explicacao = html.Div([
            html.H4("Razão Valor/Custo", style={'marginTop': '30px', 'marginBottom': '10px'}),
            html.P([
                "A ", html.Strong("Razão Valor/Custo"), " indica quantos itens de ",
                html.Span("Desenvolvimento (demanda de valor)", style={'color': 'green', 'fontWeight': 'bold'}),
                " foram entregues para cada item de ",
                html.Span("Defeito (demanda de falha)", style={'color': 'red', 'fontWeight': 'bold'}),
                " no período selecionado."
            ], style={'fontSize': '14px', 'lineHeight': '1.6'}),
            html.Ul([
                html.Li([html.Strong("Exemplo: 3.00:1"), " — para cada defeito corrigido, 3 itens de valor foram entregues."]),
                html.Li([html.Strong("Valor alto (> 4:1)"), " — o time está focado em gerar valor, com baixa incidência de retrabalho."]),
                html.Li([html.Strong("Valor baixo (< 2:1)"), " — grande parte do esforço está sendo consumido por correções de defeitos, sinalizando problemas de qualidade."]),
                html.Li([html.Strong("Infinito"), " — nenhum defeito foi registrado no período."]),
            ], style={'fontSize': '13px', 'lineHeight': '1.8', 'color': '#444'}),
            html.P("Fórmula: Throughput de Desenvolvimento / Throughput de Defeitos",
                   style={'fontSize': '12px', 'color': '#888', 'fontStyle': 'italic', 'marginTop': '10px'}),
        ], style={'padding': '15px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px', 'border': '1px solid #e0e0e0', 'marginTop': '20px'})

        return html.Div([
            html.H3("Análise de Qualidade", style={'textAlign': 'center'}),
            html.Div([
                html.Div(kpi_table, className='six columns', style={'padding': '20px'}),
                html.Div(dcc.Graph(figure=fig_pie), className='six columns'),
            ], className='row'),
            razao_explicacao,
        ])

    if tab == 'tab-analise-fluxo':
        return html.Div([
            html.H3("Análise Fluxo", style={'textAlign': 'center'}),
            html.P(
                "Consolidação das análises dimensional, por tipos e eficiência de fluxo.",
                style={'textAlign': 'center', 'color': '#666', 'marginTop': '-8px'}
            ),
            html.Hr(),
            render_tab(main_view, 'tab-dim', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, capacity_top_n, capacity_weekly_metric, portfolio_team,
                       pf_backlog_15, pf_backlog_30, pf_fresh_15, pf_fresh_30, pf_decision_statuses, pf_workflow_statuses, pf_sla_aging_json, pf_target_mix_json),
            html.Hr(),
            render_tab(main_view, 'tab-tipos', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, capacity_top_n, capacity_weekly_metric, portfolio_team,
                       pf_backlog_15, pf_backlog_30, pf_fresh_15, pf_fresh_30, pf_decision_statuses, pf_workflow_statuses, pf_sla_aging_json, pf_target_mix_json),
            html.Hr(),
            render_tab(main_view, 'tab-eficiencia', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, capacity_top_n, capacity_weekly_metric, portfolio_team,
                       pf_backlog_15, pf_backlog_30, pf_fresh_15, pf_fresh_30, pf_decision_statuses, pf_workflow_statuses, pf_sla_aging_json, pf_target_mix_json),
        ])

    if tab == 'tab-dim':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        def create_dim_graphs(df_filtered, dim_col, dim_title, top_n=30):
            # Throughput
            by_dim_tp = df_filtered.groupby(dim_col).size().reset_index(name='Throughput').sort_values('Throughput', ascending=False).head(top_n)
            fig_tp = px.bar(by_dim_tp, x=dim_col, y='Throughput', title=f'Throughput por {dim_title}')
            fig_tp.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))

            # Defect Rate
            total_by_dim = df_filtered.groupby(dim_col).size()
            defects_by_dim = df_filtered[df_filtered['TipoDemanda'] == TYPE_ISSUES].groupby(dim_col).size()
            defect_rate_df = (defects_by_dim / total_by_dim * 100).fillna(0).reset_index(name='Taxa de Defeitos (%)')
            defect_rate_df = defect_rate_df[defect_rate_df[dim_col].isin(by_dim_tp[dim_col])]

            fig_defect = px.bar(defect_rate_df, x=dim_col, y='Taxa de Defeitos (%)', title=f'Taxa de Defeitos por {dim_title}')
            fig_defect.update_traces(marker_color='red')
            fig_defect.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))
            
            return html.Div([
                html.H4(f"Análise por {dim_title}", style={'textAlign': 'center', 'marginTop': '40px'}),
                html.Div([
                    html.Div(dcc.Graph(figure=fig_tp), className='six columns'),
                    html.Div(dcc.Graph(figure=fig_defect), className='six columns'),
                ], className='row')
            ])

        graphs = [html.H3("Análise Dimensional", style={'textAlign': 'center'})]
        
        if 'Projeto' in df.columns:
            graphs.append(create_dim_graphs(df, 'Projeto', 'Projeto', top_n=100))
        if 'Responsavel' in df.columns:
            graphs.append(create_dim_graphs(df, 'Responsavel', 'Responsável', top_n=30))
        if 'Componente' in df.columns and not df['Componente'].dropna().empty:
            graphs.append(create_dim_graphs(df, 'Componente', 'Componente', top_n=30))
        if 'Prioridade' in df.columns and not df['Prioridade'].dropna().empty:
            graphs.append(create_dim_graphs(df, 'Prioridade', 'Prioridade', top_n=100))

        return html.Div(graphs)

    if tab == 'tab-tipos':
        by_tipo = df.groupby('TipoDemanda').agg({'ItemID':'count', 'LeadTime_Dias':'median'}).rename(columns={'ItemID':'Throughput','LeadTime_Dias':'LeadTime_Mediano'}).reset_index()
        
        graphs = []
        # % por Tipo de Problema (Bug, Feature, Tarefa, Suporte) -> Usando a coluna 'Tipo'
        fig_pie = px.pie(by_tipo, names='TipoDemanda', values='Throughput', title='Distribuição do Throughput por Tipo', color='TipoDemanda', color_discrete_map=color_map)
        fig_pie.update_layout(height=500)
        graphs.append(dcc.Graph(figure=fig_pie))

        # Lead Time por Tipo
        fig_lt = px.bar(by_tipo, x='TipoDemanda', y='LeadTime_Mediano', title='Lead Time Mediano por Tipo', color='TipoDemanda', color_discrete_map=color_map)
        fig_lt.update_layout(height=500)
        graphs.append(dcc.Graph(figure=fig_lt))

        # Throughput por Subtipo
        if 'WorkItemSubType' in df.columns and not df['WorkItemSubType'].dropna().empty:
            by_subtipo = df.groupby('WorkItemSubType').size().reset_index(name='Throughput').sort_values('Throughput', ascending=False)
            fig_subtipo = px.bar(by_subtipo, x='WorkItemSubType', y='Throughput', title='Throughput por Subtipo')
            fig_subtipo.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))
            graphs.append(dcc.Graph(figure=fig_subtipo))

        return html.Div(graphs)

    if tab == 'tab-tendencias':
        tp = df.dropna(subset=['DataDone']).copy()
        tp['Semana'] = weekly_bucket_start(tp['DataDone'])
        tp = tp.groupby('Semana').size().reset_index(name='Throughput')
        fig_tp = go.Figure()
        fig_tp.add_trace(go.Scatter(x=tp['Semana'], y=tp['Throughput'], mode='lines+markers', name='Throughput'))
        add_statistical_lines(fig_tp, tp['Semana'], tp['Throughput'])
        fig_tp.update_layout(title='Throughput Semanal (P15, P85, P95, Média, MM5)', height=600, xaxis_tickangle=-45, margin=dict(b=130))

        # Trend Direction
        ma5_tp = tp['Throughput'].rolling(5, min_periods=1).mean()
        trend_direction = '→'
        if len(ma5_tp) >= 5:
            last_ma = ma5_tp.iloc[-1]
            prev_ma = ma5_tp.iloc[-5]
            if prev_ma > 0:
                if last_ma > prev_ma * 1.1: trend_direction = '↑'
                elif last_ma < prev_ma * 0.9: trend_direction = '↓'

        # WIP e Lead Time média móvel
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)
        df_trend_base = fato.copy()
        if projeto: df_trend_base = df_trend_base[df_trend_base['Projeto'] == projeto]
        if responsavel: df_trend_base = df_trend_base[df_trend_base['Responsavel'] == responsavel]
        # Lead Time Trend
        lt_weekly = df.dropna(subset=['DataDone', 'LeadTime_Dias']).copy()
        lt_weekly['Semana'] = weekly_bucket_start(lt_weekly['DataDone'])
        lt_weekly = lt_weekly.groupby('Semana', as_index=False).agg(LeadTime_Dias=('LeadTime_Dias', 'mean'))

        # WIP Trend
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        wip_trend_data = []
        for week_end in weeks:
            wip_at_date = len(df_trend_base[(df_trend_base['DataInProgress'] <= week_end) & ((df_trend_base['DataDone'] > week_end) | pd.isna(df_trend_base['DataDone']))])
            wip_trend_data.append({'Semana': week_end, 'WIP': wip_at_date})
        wip_trend_df = pd.DataFrame(wip_trend_data)

        # Create figure with secondary y-axis
        fig_wip_lt = make_subplots(specs=[[{"secondary_y": True}]])
        if not wip_trend_df.empty:
            fig_wip_lt.add_trace(go.Scatter(x=wip_trend_df['Semana'], y=wip_trend_df['WIP'], name="WIP", mode='lines+markers'), secondary_y=False)
            add_statistical_lines(fig_wip_lt, wip_trend_df['Semana'], wip_trend_df['WIP'], name_prefix='WIP ', secondary_y=False)
        if not lt_weekly.empty:
            fig_wip_lt.add_trace(go.Scatter(x=lt_weekly['Semana'], y=lt_weekly['LeadTime_Dias'], name="Lead Time", mode='lines+markers'), secondary_y=True)
            add_statistical_lines(fig_wip_lt, lt_weekly['Semana'], lt_weekly['LeadTime_Dias'], name_prefix='LT ', secondary_y=True)

        fig_wip_lt.update_layout(title_text="Tendência Semanal de WIP e Lead Time", height=600, margin=dict(b=130))
        fig_wip_lt.update_xaxes(title_text="Semana", tickangle=-45)
        fig_wip_lt.update_yaxes(title_text="Contagem de WIP", secondary_y=False)
        fig_wip_lt.update_yaxes(title_text="Lead Time Médio (dias)", secondary_y=True)

        return html.Div([
            create_kpi_card('Direção da Tendência (Throughput)', trend_direction, class_name='twelve columns'),
            dcc.Graph(figure=fig_tp),
            dcc.Graph(figure=fig_wip_lt)
        ])

    if tab == 'tab-throughput-breakdown':
        tp_done = build_delivered_items_base(df)
        if tp_done.empty:
            return html.Div('Sem dados de Throughput para exibir para o período e filtros selecionados.')

        tp_done['Semana'] = weekly_bucket_start(tp_done['DataDone'])
        tp_weekly = tp_done.groupby('Semana').size().reset_index(name='Throughput')
        fig_tp_weekly = px.line(
            tp_weekly,
            x='Semana',
            y='Throughput',
            title='Throughput Semanal',
            markers=True,
        )
        add_statistical_lines(fig_tp_weekly, tp_weekly['Semana'], tp_weekly['Throughput'], name_prefix='Total ')
        fig_tp_weekly.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=100))

        type_breakdown = build_throughput_breakdown(tp_done, 'TipoDemanda', 'Throughput por Tipo de Demanda')
        desired_type_order = [TYPE_ISSUES, TYPE_SUPPORT, TYPE_DEV, TYPE_OTHER]
        if not type_breakdown.empty:
            type_breakdown['_ord'] = type_breakdown['TipoDemanda'].apply(
                lambda t: desired_type_order.index(t) if t in desired_type_order else len(desired_type_order)
            )
            type_breakdown = type_breakdown.sort_values(['_ord', 'Throughput'], ascending=[True, False]).drop(columns=['_ord'])
        type_order = type_breakdown['TipoDemanda'].tolist()
        fig_type_breakdown = px.bar(
            type_breakdown,
            x='Percentual',
            y='Barra',
            color='TipoDemanda',
            orientation='h',
            text=type_breakdown['Percentual'].map(lambda v: f'{v:.1f}%'),
            title='Throughput Breakdown por Tipo de Demanda (%)',
            labels={'Percentual': '% do Throughput', 'Barra': ''},
            color_discrete_map=color_map,
            category_orders={'TipoDemanda': type_order},
            template='plotly_white',
            height=320,
        )
        fig_type_breakdown.update_layout(
            barmode='stack',
            xaxis=dict(range=[0, 100], ticksuffix='%'),
            yaxis=dict(showticklabels=False),
            legend_title_text='Tipo de Demanda',
            margin=dict(l=60, r=40, t=70, b=50),
        )
        fig_type_breakdown.update_traces(
            textposition='inside',
            insidetextanchor='middle',
            hovertemplate='Tipo: %{fullData.name}<br>% Throughput: %{x:.1f}%<extra></extra>',
        )

        tp_done['ClassificacaoUrgencia'] = tp_done.apply(classify_urgency_label, axis=1)
        urgency_breakdown = build_throughput_breakdown(
            tp_done,
            'ClassificacaoUrgencia',
            'Throughput por Classificação de Urgência'
        )
        urgency_order = urgency_breakdown['ClassificacaoUrgencia'].tolist()
        urgency_color_map = {
            'Urgente': '#E45756',
            'Data Fixa': '#F28E2B',
            'Padrão': '#4C78A8',
            'Média': '#72B7B2',
            'Baixa': '#54A24B',
            'Intangível': '#B279A2',
            'Não classificado': '#9D9D9D',
        }
        fig_urgency_breakdown = px.bar(
            urgency_breakdown,
            x='Percentual',
            y='Barra',
            color='ClassificacaoUrgencia',
            orientation='h',
            text=urgency_breakdown['Percentual'].map(lambda v: f'{v:.1f}%'),
            title='Throughput Breakdown por Classificação de Urgência (%)',
            labels={'Percentual': '% do Throughput', 'Barra': ''},
            color_discrete_map=urgency_color_map,
            category_orders={'ClassificacaoUrgencia': urgency_order},
            template='plotly_white',
            height=320,
        )
        fig_urgency_breakdown.update_layout(
            barmode='stack',
            xaxis=dict(range=[0, 100], ticksuffix='%'),
            yaxis=dict(showticklabels=False),
            legend_title_text='Classificação de Urgência',
            margin=dict(l=60, r=40, t=70, b=50),
        )
        fig_urgency_breakdown.update_traces(
            textposition='inside',
            insidetextanchor='middle',
            hovertemplate='Urgência: %{fullData.name}<br>% Throughput: %{x:.1f}%<extra></extra>',
        )

        fig_tp_by_person_type = None
        if 'Responsavel' in tp_done.columns:
            tp_person = tp_done.copy()
            tp_person['Responsavel'] = tp_person['Responsavel'].fillna('Não atribuído').astype(str).str.strip()
            tp_person.loc[tp_person['Responsavel'].eq(''), 'Responsavel'] = 'Não atribuído'
            tp_person['TipoDemanda'] = tp_person.get('TipoDemanda', pd.Series(TYPE_OTHER, index=tp_person.index)).fillna(TYPE_OTHER)

            tp_person_breakdown = (
                tp_person.groupby(['Responsavel', 'TipoDemanda'])
                .size()
                .reset_index(name='Throughput')
            )
            if not tp_person_breakdown.empty:
                tp_person_totals = (
                    tp_person_breakdown.groupby('Responsavel', as_index=False)['Throughput']
                    .sum()
                    .rename(columns={'Throughput': 'ThroughputTotal'})
                    .sort_values(['ThroughputTotal', 'Responsavel'], ascending=[False, True])
                )
                top_people = tp_person_totals.head(20)['Responsavel'].tolist()
                tp_person_breakdown = tp_person_breakdown[tp_person_breakdown['Responsavel'].isin(top_people)].copy()
                tp_person_breakdown['Responsavel'] = pd.Categorical(
                    tp_person_breakdown['Responsavel'],
                    categories=top_people[::-1],
                    ordered=True,
                )
                fig_tp_by_person_type = px.bar(
                    tp_person_breakdown,
                    x='Throughput',
                    y='Responsavel',
                    color='TipoDemanda',
                    orientation='h',
                    barmode='stack',
                    title='Vazão por Pessoa (Top 20) dividida por Tipo de Demanda',
                    labels={'Throughput': 'Itens concluídos', 'Responsavel': 'Responsável', 'TipoDemanda': 'Tipo de Demanda'},
                    color_discrete_map=color_map,
                    template='plotly_white',
                    category_orders={'TipoDemanda': desired_type_order},
                    height=max(420, min(900, 28 * max(1, len(top_people)) + 180)),
                )
                fig_tp_by_person_type.update_layout(
                    legend_title_text='Tipo de Demanda',
                    margin=dict(l=120, r=40, t=70, b=50),
                )
                fig_tp_by_person_type.update_traces(
                    texttemplate='%{x}',
                    textposition='inside',
                    hovertemplate='Responsável: %{y}<br>Tipo: %{fullData.name}<br>Throughput: %{x}<extra></extra>',
                )

        type_table = type_breakdown.copy().rename(columns={'TipoDemanda': 'Tipo'})
        type_table['Percentual'] = type_table['Percentual'].map(lambda v: f'{v:.1f}%')
        urgency_table = urgency_breakdown.copy()
        urgency_table['Percentual'] = urgency_table['Percentual'].map(lambda v: f'{v:.1f}%')

        throughput_avg = tp_weekly['Throughput'].mean() if not tp_weekly.empty else 0.0
        tp_cancelled = pd.DataFrame(columns=df.columns)
        tp_cancelled_weekly = pd.DataFrame(columns=['Semana', 'Cancelados'])
        cancelled_avg = 0.0
        cancelled_total = 0
        cancelled_weeks = 0
        if 'DataCancelled' in df.columns:
            tp_cancelled = df.dropna(subset=['DataCancelled']).copy()
            cancelled_total = len(tp_cancelled)
            if not tp_cancelled.empty:
                tp_cancelled['Semana'] = weekly_bucket_start(tp_cancelled['DataCancelled'])
                tp_cancelled_weekly = (
                    tp_cancelled.groupby('Semana')
                    .size()
                    .reset_index(name='Cancelados')
                    .sort_values('Semana')
                )
                cancelled_avg = tp_cancelled_weekly['Cancelados'].mean() if not tp_cancelled_weekly.empty else 0.0
                cancelled_weeks = tp_cancelled_weekly['Semana'].nunique()
        return html.Div([
            html.H3("Throughput Consolidado", style={'textAlign': 'center'}),
            html.Div([
                create_kpi_card('Throughput Total', f"{len(tp_done)}", class_name='two columns'),
                create_kpi_card('Cancelados (Período)', f"{cancelled_total}", class_name='two columns'),
                create_kpi_card('Média Semanal TP', f"{throughput_avg:.1f}", class_name='two columns'),
                create_kpi_card('Média Semanal Cancel.', f"{cancelled_avg:.1f}", class_name='two columns'),
                create_kpi_card('Semanas com Entrega', f"{tp_weekly['Semana'].nunique()}", class_name='two columns'),
                create_kpi_card('Semanas c/ Cancel.', f"{cancelled_weeks}", class_name='two columns'),
            ], className='row'),
            dcc.Graph(figure=fig_tp_weekly),
            html.H4("Vazão por Pessoa", style={'textAlign': 'center', 'marginTop': '10px'}),
            (dcc.Graph(figure=fig_tp_by_person_type) if fig_tp_by_person_type is not None else html.Div('Dados de responsável não disponíveis para o gráfico de vazão por pessoa.', style={'textAlign': 'center', 'color': '#666', 'marginBottom': '12px'})),
            html.H4("Breakdown por Tipo de Demanda", style={'textAlign': 'center', 'marginTop': '10px'}),
            dcc.Graph(figure=fig_type_breakdown),
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in type_table.columns],
                data=type_table.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            ),
            html.H4("Breakdown por Classificação de Urgência", style={'textAlign': 'center', 'marginTop': '20px'}),
            dcc.Graph(figure=fig_urgency_breakdown),
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in urgency_table.columns],
                data=urgency_table.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            ),
        ])

    if tab == 'tab-eficiencia':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        # --- 1. Calcular colunas adicionais ---
        df_eff = df.copy()

        # Fallback de execução para itens sem DataInProgress:
        # usa DataBacklog como proxy para manter a análise de eficiência.
        if 'DataBacklog' in df_eff.columns:
            effective_start = df_eff.get('DataInProgress', pd.Series(pd.NaT, index=df_eff.index)).fillna(df_eff['DataBacklog'])
        else:
            effective_start = df_eff.get('DataInProgress', pd.Series(pd.NaT, index=df_eff.index))

        if 'TempoBacklog_Dias' in df_eff.columns:
            missing_backlog = df_eff['TempoBacklog_Dias'].isna()
            backlog_fallback = (effective_start - df_eff.get('DataBacklog', pd.Series(pd.NaT, index=df_eff.index))).dt.days
            df_eff.loc[missing_backlog, 'TempoBacklog_Dias'] = backlog_fallback.loc[missing_backlog]

        if 'TempoExecucao_Dias' in df_eff.columns and 'DataDone' in df_eff.columns:
            missing_exec = df_eff['TempoExecucao_Dias'].isna()
            exec_fallback = (df_eff['DataDone'] - effective_start).dt.days
            df_eff.loc[missing_exec, 'TempoExecucao_Dias'] = exec_fallback.loc[missing_exec]

        flow_base = fato.copy()
        if projeto:
            flow_base = flow_base[flow_base['Projeto'] == projeto]
        if tipo:
            flow_base = flow_base[flow_base['TipoDemanda'] == tipo]
        if responsavel:
            flow_base = flow_base[flow_base['Responsavel'] == responsavel]

        start_eff_ts = pd.to_datetime(start_date)
        end_eff_ts = pd.to_datetime(end_date)
        weeks_eff = pd.date_range(start=start_eff_ts, end=end_eff_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
        weekly_eff_map = {}
        weekly_eff_rows = []
        for i in range(len(weeks_eff) - 1):
            week_start = weeks_eff[i]
            week_end = weeks_eff[i + 1]
            arrivals_w = len(flow_base[
                (flow_base['DataInProgress'] >= week_start) &
                (flow_base['DataInProgress'] < week_end)
            ])
            throughput_w = len(flow_base[
                (flow_base['DataDone'] >= week_start) &
                (flow_base['DataDone'] < week_end)
            ])
            _, efficiency_w = calculate_flow_efficiency(arrivals_w, throughput_w)
            weekly_eff_map[pd.Timestamp(week_start).normalize()] = efficiency_w
            weekly_eff_rows.append({
                'SemanaReferencia': pd.Timestamp(week_start).normalize(),
                'Chegadas': arrivals_w,
                'Throughput': throughput_w,
                'Eficiencia': efficiency_w,
            })

        df_eff_weekly = pd.DataFrame(weekly_eff_rows)
        if not df_eff_weekly.empty:
            df_eff_weekly['SemanaLabel'] = df_eff_weekly['SemanaReferencia'].dt.strftime('%d/%m/%Y')

        if 'DataDone' in df_eff.columns:
            df_eff['SemanaReferencia'] = weekly_bucket_start(df_eff['DataDone'].fillna(effective_start))
        else:
            df_eff['SemanaReferencia'] = weekly_bucket_start(effective_start)
        df_eff['SemanaReferencia'] = pd.to_datetime(df_eff['SemanaReferencia']).dt.normalize()
        df_eff['Eficiencia'] = df_eff['SemanaReferencia'].map(weekly_eff_map)
        df_eff['EficienciaAjustada'] = df_eff['Eficiencia']
        
        time_cols = ['TempoBacklog_Dias', 'TempoExecucao_Dias', 'TempoBloqueioDias', 'TempoEsperaIntermediariaDias']
        for col in time_cols:
            if col not in df_eff.columns: df_eff[col] = 0
            else: df_eff[col] = df_eff[col].fillna(0)

        if 'LeadTime_Dias' in df_eff.columns:
            df_eff['Outros Tempos (dias)'] = df_eff['LeadTime_Dias'] - df_eff[time_cols].sum(axis=1)
            df_eff['Outros Tempos (dias)'] = df_eff['Outros Tempos (dias)'].clip(lower=0)

        eff_cols = ['Eficiencia', 'EficienciaAjustada']
        for col in eff_cols:
            if col not in df_eff.columns:
                df_eff[col] = np.nan

        df_eff['Diferença Eficiência'] = df_eff['EficienciaAjustada'] - df_eff['Eficiencia']

        # --- 2. Criar Gráficos ---
        breakdown_components = {
            'Backlog': df_eff['TempoBacklog_Dias'].mean(),
            'Execução': df_eff['TempoExecucao_Dias'].mean(),
            'Bloqueio': df_eff['TempoBloqueioDias'].mean(),
            'Espera Intermediária': df_eff['TempoEsperaIntermediariaDias'].mean(),
            'Outros': df_eff.get('Outros Tempos (dias)', pd.Series(0)).mean()
        }
        df_breakdown = pd.DataFrame(breakdown_components.items(), columns=['Componente', 'Dias'])
        df_breakdown['Dias'] = pd.to_numeric(df_breakdown['Dias'], errors='coerce').fillna(0)
        df_breakdown = df_breakdown[df_breakdown['Dias'] > 0].sort_values('Dias', ascending=True)
        total_breakdown_days = float(df_breakdown['Dias'].sum())
        df_breakdown['Participacao'] = (
            df_breakdown['Dias'] / total_breakdown_days if total_breakdown_days > 0 else 0.0
        )
        df_breakdown['ParticipacaoLabel'] = df_breakdown['Participacao'].map(lambda x: f'{x:.0%}')
        df_breakdown['DiasLabel'] = df_breakdown['Dias'].map(lambda x: f'{x:.1f} d')
        breakdown_color_map = {
            'Backlog': '#5b6cff',
            'Execução': '#f25535',
            'Bloqueio': '#38c786',
            'Espera Intermediária': '#a14cf0',
            'Outros': '#f3a15d',
        }
        bar_colors = [breakdown_color_map.get(comp, '#9aa5b1') for comp in df_breakdown['Componente']]
        fig_breakdown = make_subplots(
            rows=1,
            cols=2,
            specs=[[{"type": "xy"}, {"type": "domain"}]],
            column_widths=[0.68, 0.32],
            subplot_titles=('Dias médios por componente', 'Participação no lead time'),
        )
        fig_breakdown.add_trace(
            go.Bar(
                x=df_breakdown['Dias'],
                y=df_breakdown['Componente'],
                orientation='h',
                marker_color=bar_colors,
                text=[f'{days} ({share})' for days, share in zip(df_breakdown['DiasLabel'], df_breakdown['ParticipacaoLabel'])],
                textposition='outside',
                customdata=np.stack(
                    [df_breakdown['DiasLabel'].to_numpy(), df_breakdown['ParticipacaoLabel'].to_numpy()],
                    axis=-1,
                ),
                hovertemplate='%{y}<br>Dias médios: %{customdata[0]}<br>Participação: %{customdata[1]}<extra></extra>',
                showlegend=False,
                name='Dias médios',
            ),
            row=1,
            col=1,
        )
        fig_breakdown.add_trace(
            go.Pie(
                labels=df_breakdown['Componente'],
                values=df_breakdown['Dias'],
                hole=0.55,
                marker=dict(colors=bar_colors),
                textinfo='label+percent',
                hovertemplate='%{label}<br>Dias médios: %{value:.1f}<br>Participação: %{percent}<extra></extra>',
                sort=False,
                showlegend=False,
                name='Participação',
            ),
            row=1,
            col=2,
        )
        fig_breakdown.update_xaxes(title_text='Dias médios', row=1, col=1, rangemode='tozero')
        fig_breakdown.update_yaxes(title_text=None, row=1, col=1)
        fig_breakdown.update_layout(
            title='Breakdown do Lead Time Médio por Componente',
            height=470,
            template='plotly_white',
            margin=dict(l=40, r=40, t=80, b=40),
        )
        if total_breakdown_days > 0:
            fig_breakdown.add_annotation(
                x=0.84,
                y=0.5,
                xref='paper',
                yref='paper',
                text=f'Lead time médio<br><b>{total_breakdown_days:.1f} dias</b>',
                showarrow=False,
                font=dict(size=14),
            )

        fig_scatter_eff = make_subplots(specs=[[{"secondary_y": True}]])
        if not df_eff_weekly.empty:
            fig_scatter_eff.add_trace(
                go.Bar(
                    x=df_eff_weekly['SemanaReferencia'],
                    y=df_eff_weekly['Chegadas'],
                    name='Chegadas',
                    marker_color='#9aa5b1',
                    opacity=0.45,
                    hovertemplate='Semana %{x|%d/%m/%Y}<br>Chegadas: %{y}<extra></extra>',
                ),
                secondary_y=False,
            )
            fig_scatter_eff.add_trace(
                go.Bar(
                    x=df_eff_weekly['SemanaReferencia'],
                    y=df_eff_weekly['Throughput'],
                    name='Throughput',
                    marker_color='#2f6bff',
                    opacity=0.7,
                    hovertemplate='Semana %{x|%d/%m/%Y}<br>Throughput: %{y}<extra></extra>',
                ),
                secondary_y=False,
            )
            fig_scatter_eff.add_trace(
                go.Scatter(
                    x=df_eff_weekly['SemanaReferencia'],
                    y=df_eff_weekly['Eficiencia'],
                    name='Eficiência de Fluxo (1-ρ)',
                    mode='lines+markers',
                    line=dict(color='#d94841', width=3),
                    marker=dict(size=8),
                    hovertemplate=(
                        'Semana %{x|%d/%m/%Y}'
                        '<br>Eficiência: %{y:.2f}'
                        '<br>Chegadas: %{customdata[0]}'
                        '<br>Throughput: %{customdata[1]}<extra></extra>'
                    ),
                    customdata=df_eff_weekly[['Chegadas', 'Throughput']].to_numpy(),
                ),
                secondary_y=True,
            )
        fig_scatter_eff.update_layout(
            title='Eficiência de Fluxo (1-ρ) por Semana de Referência',
            height=550,
            template='plotly_white',
            barmode='group',
            hovermode='x unified',
            legend_title_text='Métrica',
        )
        fig_scatter_eff.update_xaxes(title_text='Semana de Referência')
        fig_scatter_eff.update_yaxes(title_text='Itens por semana', secondary_y=False, rangemode='tozero')
        fig_scatter_eff.update_yaxes(
            title_text='Eficiência de Fluxo (1-ρ)',
            secondary_y=True,
            range=[-1, 1],
            tickformat='.0%',
        )
        fig_scatter_eff.add_hline(y=0, line_dash='dash', line_color='grey', secondary_y=True)

        # --- 3. Criar Tabela Detalhada ---
        table_cols = ['ItemID', 'Projeto', 'TipoDemanda', 'SemanaReferencia', 'LeadTime_Dias', 'TempoBacklog_Dias', 'TempoExecucao_Dias', 'TempoBloqueioDias', 'TempoEsperaIntermediariaDias', 'Outros Tempos (dias)', 'Eficiencia']
        available_cols = [c for c in table_cols if c in df_eff.columns]
        detail_table = dash_table.DataTable(id='table-eficiencia-detalhada', columns=[{"name": i, "id": i} for i in available_cols], data=df_eff[available_cols].to_dict('records'), page_size=15, filter_action="native", sort_action="native", style_table={'overflowX': 'auto'}, style_cell={'minWidth': '100px', 'width': '150px', 'maxWidth': '180px', 'textAlign': 'center'})

        return html.Div([
            html.H3("Análise de Eficiência de Fluxo", style={'textAlign': 'center'}),
            dcc.Graph(figure=fig_breakdown),
            dcc.Graph(figure=fig_scatter_eff),
            html.H4("Análise Detalhada por Item", style={'textAlign': 'center', 'marginTop': '40px'}),
            detail_table
        ])

    if tab == 'tab-padroes':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        df_patterns = fato.copy()
        if projeto:
            df_patterns = df_patterns[df_patterns['Projeto'] == projeto]
        if tipo:
            df_patterns = df_patterns[df_patterns['TipoDemanda'] == tipo]
        if classe_servico:
            df_patterns = df_patterns[df_patterns['ClasseServico'] == classe_servico]
        if responsavel:
            df_patterns = df_patterns[df_patterns['Responsavel'] == responsavel]

        if df_patterns.empty:
            return html.Div('Sem dados para detectar padrões no filtro selecionado.')

        checklist_df, diagnosis_df, weekly_review_df = build_weekly_flow_checklist_and_diagnosis(df_patterns, start_ts, end_ts)
        expedite_kpis_data, expedite_table_df, expedite_alerts_df = build_expedite_governance_view(df_patterns, start_ts, end_ts)
        variability_alerts_df, variability_metrics_df = build_variability_alerts_view(df_patterns, start_ts, end_ts)
        details, summary = detect_systemic_patterns(df_patterns, start_ts, end_ts, PATTERN_RULES)
        if details.empty and checklist_df.empty and diagnosis_df.empty:
            return html.Div([
                html.H3('Padrões Sistêmicos', style={'textAlign': 'center'}),
                html.P(
                    'Nenhum padrão ou checklist automatizado disponível com os dados do período/filtros.',
                    style={'textAlign': 'center', 'color': '#555'}
                ),
            ])

        criticos = int((details['Severidade'] == 'Crítico').sum()) if 'Severidade' in details.columns else 0
        atencao = int((details['Severidade'] == 'Atenção').sum()) if 'Severidade' in details.columns else 0
        semanas_afetadas = int(details['Semana'].nunique()) if 'Semana' in details.columns else 0
        checklist_criticos = int((checklist_df['Status'] == 'Crítico').sum()) if not checklist_df.empty else 0
        checklist_alertas = int((checklist_df['Status'] == 'Atenção').sum()) if not checklist_df.empty else 0
        diagnosticos = int(len(diagnosis_df)) if not diagnosis_df.empty else 0
        variability_criticos = int((variability_alerts_df['Status'] == 'Crítico').sum()) if not variability_alerts_df.empty else 0
        expedite_status = expedite_kpis_data.get('policy_status', 'Sem base')

        kpis = html.Div([
            create_kpi_card('Ocorrências Críticas', criticos, class_name='four columns'),
            create_kpi_card('Ocorrências Atenção', atencao, class_name='four columns'),
            create_kpi_card('Semanas com Sinal', semanas_afetadas, class_name='four columns'),
        ], className='row')
        checklist_kpis = html.Div([
            create_kpi_card('Checklist Crítico', checklist_criticos, class_name='four columns'),
            create_kpi_card('Checklist Atenção', checklist_alertas, class_name='four columns'),
            create_kpi_card('Diagnósticos Prescritivos', diagnosticos, class_name='four columns'),
        ], className='row')
        expedite_kpis = html.Div([
            create_kpi_card('Expedite nas Entradas', f"{expedite_kpis_data['arrivals_pct']:.1f}%" if pd.notna(expedite_kpis_data.get('arrivals_pct')) else '—', class_name='three columns'),
            create_kpi_card('Expedite no Throughput', f"{expedite_kpis_data['throughput_pct']:.1f}%" if pd.notna(expedite_kpis_data.get('throughput_pct')) else '—', class_name='three columns'),
            create_kpi_card('Expedite em Aberto', f"{int(expedite_kpis_data.get('open_items', 0))}", class_name='three columns'),
            create_kpi_card('Política Expedite', expedite_status, class_name='three columns'),
        ], className='row')
        variability_kpis = html.Div([
            create_kpi_card('Alertas de Variabilidade Críticos', variability_criticos, class_name='four columns'),
            create_kpi_card('CV Lead Time', f"{float(variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Lead Time', 'CV'].iloc[0]):.3f}" if not variability_metrics_df.empty and not variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Lead Time', 'CV'].empty and pd.notna(variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Lead Time', 'CV'].iloc[0]) else '—', class_name='four columns'),
            create_kpi_card('CV Cycle Time', f"{float(variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Cycle Time', 'CV'].iloc[0]):.3f}" if not variability_metrics_df.empty and not variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Cycle Time', 'CV'].empty and pd.notna(variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Cycle Time', 'CV'].iloc[0]) else '—', class_name='four columns'),
        ], className='row')

        fig_summary = go.Figure()
        if not summary.empty:
            fig_summary = px.bar(
                summary,
                x='Padrão',
                y='Ocorrências',
                color='Severidade',
                barmode='group',
                title='Padrões Detectados por Severidade',
                color_discrete_map={'Crítico': '#c62828', 'Atenção': '#f9a825'}
            )
            fig_summary.update_layout(height=520, xaxis_tickangle=-25, margin=dict(b=140))

        fig_expedite = go.Figure()
        if not expedite_table_df.empty:
            plot_df = expedite_table_df.copy().head(10)
            fig_expedite = px.bar(
                plot_df,
                x='Classe de Serviço',
                y='Itens',
                title='Distribuição de throughput por classe de serviço',
                color='Classe de Serviço',
            )
            fig_expedite.update_layout(height=420, xaxis_tickangle=-25, showlegend=False, margin=dict(b=100))

        fig_variability = go.Figure()
        if not variability_metrics_df.empty:
            fig_variability = px.bar(
                variability_metrics_df,
                x='Métrica',
                y='CV',
                color='Status',
                title='Alertas explícitos de variabilidade/dispersão',
                color_discrete_map={'OK': '#2E7D32', 'Atenção': '#EF6C00', 'Crítico': '#C62828', 'Sem base': '#90A4AE'},
            )
            fig_variability.update_layout(height=420, showlegend=True, margin=dict(b=60))

        fig_weekly_review = go.Figure()
        if not weekly_review_df.empty:
            weekly_plot = weekly_review_df.copy()
            weekly_plot['Semana'] = weekly_plot['Semana'].astype(str)
            fig_weekly_review = make_subplots(specs=[[{"secondary_y": True}]])
            fig_weekly_review.add_trace(
                go.Bar(x=weekly_plot['Semana'], y=weekly_plot['Throughput'], name='Throughput', marker_color='#2E7D32'),
                secondary_y=False,
            )
            fig_weekly_review.add_trace(
                go.Scatter(x=weekly_plot['Semana'], y=weekly_plot['WIP'], name='WIP', mode='lines+markers', line=dict(color='#1565C0', width=3)),
                secondary_y=False,
            )
            fig_weekly_review.add_trace(
                go.Scatter(x=weekly_plot['Semana'], y=weekly_plot['CycleTime_P50'], name='Cycle P50', mode='lines+markers', line=dict(color='#EF6C00', width=3)),
                secondary_y=True,
            )
            fig_weekly_review.update_layout(
                title='Resumo Semanal Automatizado: Throughput, WIP e Cycle Time',
                height=520,
                template='plotly_white',
                hovermode='x unified',
                margin=dict(b=90),
            )
            fig_weekly_review.update_xaxes(title_text='Semana', tickangle=-45)
            fig_weekly_review.update_yaxes(title_text='Itens', secondary_y=False)
            fig_weekly_review.update_yaxes(title_text='Cycle Time P50 (dias)', secondary_y=True)

        details_view = details.sort_values(['Semana', 'Severidade'], ascending=[False, True]) if not details.empty else pd.DataFrame()
        table_summary = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in summary.columns],
            data=summary.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            page_size=12,
        ) if not summary.empty else html.P('Nenhum padrão sistêmico acionado no período.')
        table_details = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in details_view.columns],
            data=details_view.to_dict('records'),
            style_cell={
                'textAlign': 'left',
                'padding': '6px',
                'minWidth': '120px',
                'maxWidth': '260px',
                'whiteSpace': 'normal'
            },
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Severidade} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Severidade} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
            ],
            page_size=12,
            filter_action='native',
            sort_action='native',
        ) if not details_view.empty else html.P('Nenhum detalhe adicional de padrões no período.')
        checklist_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in checklist_df.columns],
            data=checklist_df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Status} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Status} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                {'if': {'filter_query': '{Status} = "OK"'}, 'backgroundColor': '#edf7ed'},
            ],
            page_size=10,
        ) if not checklist_df.empty else html.P('Sem checklist automatizado disponível para o recorte.')
        diagnosis_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in diagnosis_df.columns],
            data=diagnosis_df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px', 'minWidth': '120px', 'maxWidth': '320px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Severidade} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Severidade} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                {'if': {'filter_query': '{Severidade} = "OK"'}, 'backgroundColor': '#edf7ed'},
            ],
            page_size=10,
            filter_action='native',
            sort_action='native',
        ) if not diagnosis_df.empty else html.P('Nenhum diagnóstico prescritivo foi gerado para o período.')
        expedite_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in expedite_table_df.columns],
            data=expedite_table_df.to_dict('records'),
            style_cell={'textAlign': 'center', 'padding': '6px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            page_size=10,
        ) if not expedite_table_df.empty else html.P('Sem base suficiente para governança de expedite.')
        expedite_alerts_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in expedite_alerts_df.columns],
            data=expedite_alerts_df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Status} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Status} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                {'if': {'filter_query': '{Status} = "OK"'}, 'backgroundColor': '#edf7ed'},
            ],
            page_size=10,
        ) if not expedite_alerts_df.empty else html.P('Sem alertas de expedite para o recorte.')
        variability_alerts_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in variability_alerts_df.columns],
            data=variability_alerts_df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Status} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Status} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                {'if': {'filter_query': '{Status} = "OK"'}, 'backgroundColor': '#edf7ed'},
            ],
            page_size=10,
        ) if not variability_alerts_df.empty else html.P('Sem base suficiente para alertas de variabilidade.')
        weekly_review_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in weekly_review_df.columns],
            data=weekly_review_df.to_dict('records'),
            style_cell={'textAlign': 'center', 'padding': '6px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            page_size=12,
        ) if not weekly_review_df.empty else html.P('Sem base semanal suficiente para a revisão automatizada.')

        return html.Div([
            html.H3('Padrões Sistêmicos Detectados', style={'textAlign': 'center'}),
            html.P(
                'Detecção automática por regras configuráveis (PATTERN_RULES/JIRA_PATTERN_RULES). '
                'Inclui urgência crônica, burnout, confiança comprometida, problema sistêmico de fluxo, '
                'atrasos/desperdícios, estagnação e compromisso prematuro.',
                style={'textAlign': 'center', 'color': '#555'}
            ),
            html.H4('Checklist Semanal Automatizado', style={'marginTop': '16px'}),
            html.P(
                'Leitura operacional automática da última semana do recorte, usando banda histórica de throughput, referência factual de cycle time e banda histórica de WIP.',
                style={'color': '#555'}
            ),
            checklist_kpis,
            checklist_table,
            html.H4('Tabela Diagnóstica Prescritiva', style={'marginTop': '16px'}),
            html.P(
                'Combinações semanais de métricas transformadas em diagnóstico provável e ação recomendada.',
                style={'color': '#555'}
            ),
            diagnosis_table,
            html.H4('Governança Fast Track / Expedite', style={'marginTop': '16px'}),
            html.P(
                'Expõe participação de urgências na entrada, na saída e no estoque em aberto para evitar que fast track vire regra em vez de exceção.',
                style={'color': '#555'}
            ),
            expedite_kpis,
            expedite_alerts_table,
            dcc.Graph(figure=fig_expedite) if isinstance(fig_expedite, go.Figure) and fig_expedite.data else html.Div(),
            expedite_table,
            html.H4('Alertas Explícitos de Variabilidade / Dispersão', style={'marginTop': '16px'}),
            html.P(
                'Semáforos operacionais de dispersão para `Lead Time`, `Cycle Time` e `Throughput`, convertendo CV em alerta acionável.',
                style={'color': '#555'}
            ),
            variability_kpis,
            dcc.Graph(figure=fig_variability) if isinstance(fig_variability, go.Figure) and fig_variability.data else html.Div(),
            variability_alerts_table,
            dcc.Graph(figure=fig_weekly_review) if isinstance(fig_weekly_review, go.Figure) and fig_weekly_review.data else html.Div(),
            html.H4('Base Semanal da Revisão Automatizada', style={'marginTop': '16px'}),
            weekly_review_table,
            html.Hr(style={'margin': '28px 0'}),
            kpis,
            dcc.Graph(figure=fig_summary) if isinstance(fig_summary, go.Figure) and fig_summary.data else html.Div(),
            html.H4('Resumo de Ocorrências', style={'marginTop': '16px'}),
            table_summary,
            html.H4('Detalhamento Semanal', style={'marginTop': '16px'}),
            table_details,
        ])

    if tab == 'tab-process-mining-jira':
        if projeto and normalize_text(projeto) not in {'w1nner', 'w1nnr'}:
            return html.Div([
                html.H3('Process Mining Jira (W1NNER)', style={'textAlign': 'center'}),
                html.P(
                    'Este painel é dedicado ao projeto W1NNER (W1NNR). Limpe o filtro de projeto ou selecione W1NNER.',
                    style={'textAlign': 'center', 'color': '#555'}
                )
            ])

        report_path, pm_report = load_w1nner_process_mining_report()
        if not pm_report:
            return html.Div([
                html.H3('Process Mining Jira (W1NNER)', style={'textAlign': 'center'}),
                html.P('Relatório de process mining não encontrado.', style={'textAlign': 'center', 'color': '#b22222'}),
                html.Pre(
                    'Gere com: python process_mining_jira.py --input <jira_changelog_detalhado.csv>',
                    style={'maxWidth': '900px', 'margin': '0 auto', 'whiteSpace': 'pre-wrap', 'background': '#f7f7f7', 'padding': '12px', 'borderRadius': '8px'}
                )
            ])

        pm_summary = pm_report.get('ResumoConformidade', pd.DataFrame()).copy()
        pm_cases = pm_report.get('ConformidadeCasos', pd.DataFrame()).copy()
        pm_rework = pm_report.get('RetrabalhoItens', pd.DataFrame()).copy()
        pm_status = pm_report.get('TemposPorStatus', pd.DataFrame()).copy()
        pm_weekly = pm_report.get('VazaoPessoaSemanal', pd.DataFrame()).copy()
        pm_people = pm_report.get('VazaoPessoaResumo', pd.DataFrame()).copy()
        pm_hours_people = pm_report.get('HorasPessoaResumo', pd.DataFrame()).copy()
        pm_hours_status = pm_report.get('HorasPessoaStatus', pd.DataFrame()).copy()
        pm_variants = pm_report.get('VariantesTop', pd.DataFrame()).copy()
        pm_events = pm_report.get('EventosFiltrados', pd.DataFrame()).copy()
        pm_dfg_edges = pm_report.get('PM4PyDFGEdges', pd.DataFrame()).copy()
        pm_dfg_perf_edges = pm_report.get('PM4PyDFGPerfEdges', pd.DataFrame()).copy()
        pm_tbr_summary = pm_report.get('PM4PyTBRResumo', pd.DataFrame()).copy()
        pm_tbr_cases = pm_report.get('PM4PyTBRCasos', pd.DataFrame()).copy()
        pm_align_summary = pm_report.get('PM4PyAlignResumo', pd.DataFrame()).copy()
        pm_align_cases = pm_report.get('PM4PyAlignCasos', pd.DataFrame()).copy()
        pm_align_moves = pm_report.get('PM4PyAlignTopMoves', pd.DataFrame()).copy()
        pm_meta = pm_report.get('Metadados', pd.DataFrame()).copy()

        for dcol in ['Done Final Date']:
            if dcol in pm_cases.columns:
                pm_cases[dcol] = pd.to_datetime(pm_cases[dcol], errors='coerce')
            if dcol in pm_rework.columns:
                pm_rework[dcol] = pd.to_datetime(pm_rework[dcol], errors='coerce')
            if dcol in pm_tbr_cases.columns:
                pm_tbr_cases[dcol] = pd.to_datetime(pm_tbr_cases[dcol], errors='coerce')
            if dcol in pm_align_cases.columns:
                pm_align_cases[dcol] = pd.to_datetime(pm_align_cases[dcol], errors='coerce')
        if 'Semana' in pm_weekly.columns:
            pm_weekly['Semana'] = pd.to_datetime(pm_weekly['Semana'], errors='coerce')
        if 'History Created' in pm_events.columns:
            pm_events['History Created'] = pd.to_datetime(pm_events['History Created'], errors='coerce')

        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        if 'Done Final Date' in pm_cases.columns:
            pm_cases = pm_cases[
                pm_cases['Done Final Date'].isna() |
                ((pm_cases['Done Final Date'] >= start_ts) & (pm_cases['Done Final Date'] <= end_ts))
            ]
        if 'Done Final Date' in pm_rework.columns:
            pm_rework = pm_rework[
                pm_rework['Done Final Date'].isna() |
                ((pm_rework['Done Final Date'] >= start_ts) & (pm_rework['Done Final Date'] <= end_ts))
            ]
        if 'Semana' in pm_weekly.columns:
            pm_weekly = pm_weekly[
                (pm_weekly['Semana'] >= start_ts) &
                (pm_weekly['Semana'] <= end_ts + pd.Timedelta(days=7))
            ]
        if 'History Created' in pm_events.columns:
            pm_events = pm_events[
                (pm_events['History Created'] >= start_ts) &
                (pm_events['History Created'] <= end_ts + pd.Timedelta(days=1))
            ]
        if 'Done Final Date' in pm_tbr_cases.columns:
            pm_tbr_cases = pm_tbr_cases[
                pm_tbr_cases['Done Final Date'].isna() |
                ((pm_tbr_cases['Done Final Date'] >= start_ts) & (pm_tbr_cases['Done Final Date'] <= end_ts))
            ]
        if 'Done Final Date' in pm_align_cases.columns:
            pm_align_cases = pm_align_cases[
                pm_align_cases['Done Final Date'].isna() |
                ((pm_align_cases['Done Final Date'] >= start_ts) & (pm_align_cases['Done Final Date'] <= end_ts))
            ]

        if responsavel:
            if 'Responsavel' in pm_people.columns:
                pm_people = pm_people[pm_people['Responsavel'] == responsavel]
            if 'Responsavel' in pm_weekly.columns:
                pm_weekly = pm_weekly[pm_weekly['Responsavel'] == responsavel]
            if 'Responsavel' in pm_hours_people.columns:
                pm_hours_people = pm_hours_people[pm_hours_people['Responsavel'] == responsavel]
            if 'Responsavel' in pm_hours_status.columns:
                pm_hours_status = pm_hours_status[pm_hours_status['Responsavel'] == responsavel]
            if 'Done Final Author' in pm_rework.columns:
                pm_rework = pm_rework[pm_rework['Done Final Author'] == responsavel]
            if 'Done Final Author' in pm_cases.columns:
                pm_cases = pm_cases[pm_cases['Done Final Author'] == responsavel]
            if 'Author' in pm_events.columns:
                pm_events = pm_events[pm_events['Author'] == responsavel]
            if 'Done Final Author' in pm_tbr_cases.columns:
                pm_tbr_cases = pm_tbr_cases[pm_tbr_cases['Done Final Author'] == responsavel]
            if 'Done Final Author' in pm_align_cases.columns:
                pm_align_cases = pm_align_cases[pm_align_cases['Done Final Author'] == responsavel]

        # Rebuild graph datasets from date-filtered bases to guarantee UI date filter adherence.
        if not pm_cases.empty and {'Issue Key', 'Done Final Author', 'Done Final Date'}.issubset(pm_cases.columns):
            done_cases = pm_cases[pm_cases['Done Final Date'].notna()].copy()
            if not done_cases.empty:
                done_cases['Responsavel'] = done_cases['Done Final Author'].fillna('').astype(str).str.strip().replace('', 'Sem Autor')
                done_cases['Com Retrabalho'] = (
                    pd.to_numeric(done_cases.get('Rework Score', pd.Series(0, index=done_cases.index)), errors='coerce')
                    .fillna(0)
                    .gt(0)
                    .astype(int)
                )
                done_cases['Semana'] = pd.to_datetime(done_cases['Done Final Date'], errors='coerce').dt.to_period('W-SUN').dt.start_time

                pm_weekly = (
                    done_cases.groupby(['Semana', 'Responsavel'], dropna=False)
                    .agg(
                        **{
                            'Itens Concluidos': ('Issue Key', 'nunique'),
                            'Itens Com Retrabalho': ('Com Retrabalho', 'sum'),
                        }
                    )
                    .reset_index()
                )
                pm_weekly['Taxa Retrabalho (%)'] = np.where(
                    pm_weekly['Itens Concluidos'] > 0,
                    pm_weekly['Itens Com Retrabalho'] / pm_weekly['Itens Concluidos'] * 100.0,
                    0.0,
                )

                pm_people = (
                    done_cases.groupby('Responsavel', dropna=False)
                    .agg(
                        **{
                            'Itens Concluidos': ('Issue Key', 'nunique'),
                            'Itens Com Retrabalho': ('Com Retrabalho', 'sum'),
                            'Rework Score Total': ('Rework Score', 'sum'),
                            'Lead Time Mediano (dias)': ('Lead Time Fluxo (dias)', 'median'),
                            'Semanas Com Entrega': ('Semana', lambda s: s.dropna().nunique()),
                        }
                    )
                    .reset_index()
                )
                pm_people['Taxa Retrabalho (%)'] = np.where(
                    pm_people['Itens Concluidos'] > 0,
                    pm_people['Itens Com Retrabalho'] / pm_people['Itens Concluidos'] * 100.0,
                    0.0,
                )
                pm_people['Media Itens/Semana Ativa'] = np.where(
                    pm_people['Semanas Com Entrega'] > 0,
                    pm_people['Itens Concluidos'] / pm_people['Semanas Com Entrega'],
                    0.0,
                )
                pm_people = pm_people.sort_values('Itens Concluidos', ascending=False).reset_index(drop=True)
            else:
                pm_weekly = pd.DataFrame(columns=['Semana', 'Responsavel', 'Itens Concluidos', 'Itens Com Retrabalho', 'Taxa Retrabalho (%)'])
                pm_people = pd.DataFrame(columns=['Responsavel', 'Itens Concluidos', 'Itens Com Retrabalho'])

        if not pm_events.empty:
            evt = pm_events.copy()
            if 'Author' in evt.columns:
                evt['Author'] = evt['Author'].fillna('').astype(str).str.strip().replace('', 'Sem Autor')
            if 'Issue Key' in evt.columns:
                evt['Issue Key'] = evt['Issue Key'].astype(str).str.strip()

            if {'TempoStatusDias', 'To Status', 'Issue Key'}.issubset(evt.columns):
                x_status = evt.dropna(subset=['TempoStatusDias']).copy()
                if not x_status.empty:
                    x_status['TempoStatusDias'] = pd.to_numeric(x_status['TempoStatusDias'], errors='coerce')
                    x_status = x_status.dropna(subset=['TempoStatusDias'])
                    pm_status = (
                        x_status.groupby('To Status', dropna=False)
                        .agg(
                            **{
                                'Qtde Ocorrencias': ('Issue Key', 'count'),
                                'Qtde Itens': ('Issue Key', 'nunique'),
                                'Tempo Medio (dias)': ('TempoStatusDias', 'mean'),
                                'Tempo Mediano (dias)': ('TempoStatusDias', 'median'),
                                'P85 (dias)': ('TempoStatusDias', lambda s: float(s.quantile(0.85)) if len(s) else np.nan),
                                'P95 (dias)': ('TempoStatusDias', lambda s: float(s.quantile(0.95)) if len(s) else np.nan),
                            }
                        )
                        .reset_index()
                        .rename(columns={'To Status': 'Status'})
                    )
                else:
                    pm_status = pd.DataFrame(columns=['Status', 'Qtde Ocorrencias', 'Qtde Itens', 'Tempo Medio (dias)', 'Tempo Mediano (dias)', 'P85 (dias)', 'P95 (dias)'])

            if {'Author', 'TempoStatusDias', 'Issue Key'}.issubset(evt.columns):
                x_hours = evt.dropna(subset=['TempoStatusDias']).copy()
                if not x_hours.empty:
                    x_hours['HorasNoFluxo'] = pd.to_numeric(x_hours['TempoStatusDias'], errors='coerce').fillna(0) * 24.0
                    pm_hours_people = (
                        x_hours.groupby('Author', dropna=False)
                        .agg(
                            **{
                                'HorasNoFluxo': ('HorasNoFluxo', 'sum'),
                                'Eventos': ('Issue Key', 'count'),
                                'CardsUnicos': ('Issue Key', 'nunique'),
                            }
                        )
                        .reset_index()
                        .rename(columns={'Author': 'Responsavel'})
                    )
                    pm_hours_people['HorasMediasPorEvento'] = np.where(
                        pm_hours_people['Eventos'] > 0,
                        pm_hours_people['HorasNoFluxo'] / pm_hours_people['Eventos'],
                        0.0,
                    )

                    if 'To Status' in x_hours.columns:
                        pm_hours_status = (
                            x_hours.groupby(['Author', 'To Status'], dropna=False)
                            .agg(
                                **{
                                    'HorasNoFluxo': ('HorasNoFluxo', 'sum'),
                                    'Eventos': ('Issue Key', 'count'),
                                    'CardsUnicos': ('Issue Key', 'nunique'),
                                }
                            )
                            .reset_index()
                            .rename(columns={'Author': 'Responsavel', 'To Status': 'Status'})
                        )
                    else:
                        pm_hours_status = pd.DataFrame(columns=['Responsavel', 'Status', 'HorasNoFluxo', 'Eventos', 'CardsUnicos'])
                else:
                    pm_hours_people = pd.DataFrame(columns=['Responsavel', 'HorasNoFluxo', 'HorasMediasPorEvento', 'Eventos', 'CardsUnicos'])
                    pm_hours_status = pd.DataFrame(columns=['Responsavel', 'Status', 'HorasNoFluxo', 'Eventos', 'CardsUnicos'])

            if {'From Status', 'To Status'}.issubset(evt.columns):
                edge_base = evt.copy()
                edge_base['From Status'] = edge_base['From Status'].fillna('').astype(str).str.strip()
                edge_base['To Status'] = edge_base['To Status'].fillna('').astype(str).str.strip()
                edge_base = edge_base[(edge_base['From Status'] != '') & (edge_base['To Status'] != '')].copy()
                if not edge_base.empty:
                    pm_dfg_edges = (
                        edge_base.groupby(['From Status', 'To Status'], dropna=False)
                        .size()
                        .reset_index(name='Count')
                        .rename(columns={'From Status': 'From', 'To Status': 'To'})
                    )
                    if 'TempoStatusDias' in edge_base.columns:
                        perf_base = edge_base.dropna(subset=['TempoStatusDias']).copy()
                        perf_base['PerfHours'] = pd.to_numeric(perf_base['TempoStatusDias'], errors='coerce').fillna(0) * 24.0
                        pm_dfg_perf_edges = (
                            perf_base.groupby(['From Status', 'To Status'], dropna=False)['PerfHours']
                            .mean()
                            .reset_index()
                            .rename(columns={'From Status': 'From', 'To Status': 'To'})
                        )
                    else:
                        pm_dfg_perf_edges = pd.DataFrame(columns=['From', 'To', 'PerfHours'])
                else:
                    pm_dfg_edges = pd.DataFrame(columns=['From', 'To', 'Count'])
                    pm_dfg_perf_edges = pd.DataFrame(columns=['From', 'To', 'PerfHours'])

        if not pm_cases.empty and {'Variant', 'Issue Key'}.issubset(pm_cases.columns):
            v = pm_cases.copy()
            v['Variant'] = v['Variant'].fillna('').astype(str).str.strip()
            v = v[v['Variant'] != '']
            if not v.empty:
                pm_variants = (
                    v.groupby('Variant', dropna=False)
                    .agg(**{'Qtde Casos': ('Issue Key', 'nunique')})
                    .reset_index()
                    .sort_values('Qtde Casos', ascending=False)
                )
                total_var = max(1, int(pm_variants['Qtde Casos'].sum()))
                pm_variants['Pct Casos'] = pm_variants['Qtde Casos'] / total_var * 100.0
            else:
                pm_variants = pd.DataFrame(columns=['Variant', 'Qtde Casos', 'Pct Casos'])

        pm_pull_dev = pd.DataFrame()
        pm_pull_dev_by_band = pd.DataFrame()
        pull_dev_total_cards = 0
        pull_dev_total_story_points = 0.0
        if not pm_events.empty and {'Issue Key', 'Author', 'To Status Norm'}.issubset(pm_events.columns):
            dev_status_norms = {'in progress', 'in development', 'development', 'doing', 'desenvolvimento'}
            pull_events = pm_events.copy()
            pull_events['To Status Norm'] = pull_events['To Status Norm'].astype(str).map(normalize_text)
            pull_events = pull_events[pull_events['To Status Norm'].isin(dev_status_norms)].copy()
            if 'From Status Norm' in pull_events.columns:
                pull_events['From Status Norm'] = pull_events['From Status Norm'].astype(str).map(normalize_text)
                pull_events = pull_events[~pull_events['From Status Norm'].isin(dev_status_norms)].copy()
            pull_events['Issue Key'] = pull_events['Issue Key'].astype(str).str.strip().str.upper()
            pull_events = pull_events[pull_events['Issue Key'].ne('')].copy()
            if 'History Created' in pull_events.columns:
                pull_events = pull_events.sort_values(['Issue Key', 'History Created'])
            else:
                pull_events = pull_events.sort_values(['Issue Key'])
            pull_events = pull_events.drop_duplicates(subset=['Issue Key'], keep='first')

            alias_index = _load_person_alias_index()
            pull_events['Responsavel'] = pull_events['Author'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
            pull_events['Responsavel'] = pull_events['Responsavel'].replace('', 'Sem Autor')

            ds_items = load_project_downstream_items_csv('W1NNER')
            if not ds_items.empty and 'ID' in ds_items.columns:
                ds_points = ds_items.copy()
                ds_points['Issue Key'] = ds_points['ID'].astype(str).str.strip().str.upper()
                if 'Story Points' not in ds_points.columns:
                    ds_points['Story Points'] = np.nan
                if 'Story point estimate' not in ds_points.columns:
                    ds_points['Story point estimate'] = np.nan
                def _resolve_story_points(row):
                    primary = _coerce_story_points_value(row.get('Story Points'))
                    if pd.notna(primary):
                        return primary
                    return _coerce_story_points_value(row.get('Story point estimate'))

                ds_points['StoryPoints_Value'] = ds_points.apply(_resolve_story_points, axis=1)
                ds_points = ds_points[['Issue Key', 'StoryPoints_Value']].drop_duplicates(subset=['Issue Key'], keep='first')
                pull_events = pull_events.merge(ds_points, how='left', on='Issue Key')
            else:
                pull_events['StoryPoints_Value'] = np.nan

            seniority_index = _load_person_seniority_index(alias_index=alias_index)
            pull_events['Senioridade'] = pull_events['Responsavel'].map(seniority_index).fillna('Nao classificado')
            pull_events['Faixa Story Points'] = pull_events['StoryPoints_Value'].apply(_story_points_band)
            faixa_order = ['Sem estimativa', '0', '1', '2-3', '5', '8', '13+']
            pull_events['Faixa Story Points'] = pd.Categorical(pull_events['Faixa Story Points'], categories=faixa_order, ordered=True)
            pm_pull_dev = pull_events.copy()
            pull_dev_total_cards = int(pm_pull_dev['Issue Key'].nunique())
            pull_dev_total_story_points = float(pd.to_numeric(pm_pull_dev['StoryPoints_Value'], errors='coerce').fillna(0).sum())
            pm_pull_dev_by_band = (
                pm_pull_dev
                .groupby(['Responsavel', 'Faixa Story Points'], dropna=False)
                .agg(
                    **{
                        'Cards Puxados': ('Issue Key', 'nunique'),
                        'Story Points Total': ('StoryPoints_Value', lambda s: pd.to_numeric(s, errors='coerce').fillna(0).sum()),
                    }
                )
                .reset_index()
            )
            pm_pull_dev_by_band['Faixa Story Points'] = pm_pull_dev_by_band['Faixa Story Points'].astype(str)
            person_totals = (
                pm_pull_dev_by_band
                .groupby('Responsavel', dropna=False)['Cards Puxados']
                .sum()
                .sort_values(ascending=True)
            )
            person_order = person_totals.index.tolist()
            pm_pull_dev_by_band['Responsavel'] = pd.Categorical(
                pm_pull_dev_by_band['Responsavel'],
                categories=person_order,
                ordered=True,
            )
            pm_pull_dev_by_band = pm_pull_dev_by_band.sort_values(['Responsavel', 'Faixa Story Points'])

        if pm_people.empty and pm_cases.empty:
            return html.Div('Sem dados de process mining para o período/filtros selecionados.')

        finalized_issue_keys = set()
        if 'Issue Key' in pm_cases.columns:
            cases_for_throughput = pm_cases.copy()
            if 'Done Final Date' in cases_for_throughput.columns:
                cases_for_throughput = cases_for_throughput[cases_for_throughput['Done Final Date'].notna()]
            issue_keys = (
                cases_for_throughput['Issue Key']
                .astype(str)
                .str.strip()
                .str.upper()
            )
            finalized_issue_keys = set(issue_keys[issue_keys.ne('')].tolist())
        if finalized_issue_keys:
            total_concluidos = len(finalized_issue_keys)
        elif 'Itens Concluidos' in pm_people.columns and not pm_people.empty:
            total_concluidos = int(pd.to_numeric(pm_people['Itens Concluidos'], errors='coerce').fillna(0).sum())
        else:
            total_concluidos = 0

        if 'Itens Com Retrabalho' in pm_people.columns and not pm_people.empty:
            itens_retrabalho = int(pd.to_numeric(pm_people['Itens Com Retrabalho'], errors='coerce').fillna(0).sum())
        elif not pm_cases.empty and 'Rework Score' in pm_cases.columns:
            itens_retrabalho = int((pd.to_numeric(pm_cases['Rework Score'], errors='coerce').fillna(0) > 0).sum())
        else:
            itens_retrabalho = 0
        taxa_retrabalho = (itens_retrabalho / total_concluidos * 100.0) if total_concluidos > 0 else 0.0

        conf_media = np.nan
        if not pm_cases.empty and 'Conformance Score' in pm_cases.columns:
            conf_series = pd.to_numeric(pm_cases['Conformance Score'], errors='coerce').dropna()
            if not conf_series.empty:
                conf_media = float(conf_series.mean())

        horas_fluxo_total = 0.0
        horas_fluxo_media_evento = np.nan
        if not pm_hours_people.empty and 'HorasNoFluxo' in pm_hours_people.columns:
            horas_fluxo_total = float(pd.to_numeric(pm_hours_people['HorasNoFluxo'], errors='coerce').fillna(0).sum())
        if not pm_hours_people.empty and {'HorasNoFluxo', 'Eventos'}.issubset(pm_hours_people.columns):
            eventos_total = float(pd.to_numeric(pm_hours_people['Eventos'], errors='coerce').fillna(0).sum())
            horas_fluxo_media_evento = (horas_fluxo_total / eventos_total) if eventos_total > 0 else np.nan

        horas_execucao_periodo = 0.0
        if not pm_events.empty and 'TempoStatusDias' in pm_events.columns:
            horas_execucao_periodo = float(
                pd.to_numeric(pm_events['TempoStatusDias'], errors='coerce').fillna(0).sum() * 24.0
            )

        bitbucket_logs = load_project_bitbucket_logs('W1NNER')
        bitbucket_end_ts = end_ts + pd.Timedelta(days=1)
        bb_people, bb_totals = compute_bitbucket_contributor_metrics(
            bitbucket_logs, start_ts, bitbucket_end_ts, alias_index=_load_person_alias_index()
        )
        if responsavel and not bb_people.empty and 'Pessoa' in bb_people.columns:
            target_person = _canonical_person_name(responsavel)
            bb_people = bb_people[bb_people['Pessoa'] == target_person].copy()
            bb_totals = {
                'Commits': int(pd.to_numeric(bb_people.get('Commits', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
                'PRs Abertos': int(pd.to_numeric(bb_people.get('PRs Abertos', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
                'Aprovacoes': int(pd.to_numeric(bb_people.get('Aprovacoes', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
                'Reprovacoes': int(pd.to_numeric(bb_people.get('Reprovacoes', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
                'PRs Declinados (Autor)': int(pd.to_numeric(bb_people.get('PRs Declinados (Autor)', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
            }
        bb_totals = bb_totals if isinstance(bb_totals, dict) else {}

        cobertura_tecnica_pct = np.nan
        itens_com_evidencia = 0
        if finalized_issue_keys:
            keys_done = set(finalized_issue_keys)
            if keys_done:
                tech_keys = _extract_work_item_keys_from_bitbucket_logs(bitbucket_logs, start_ts, bitbucket_end_ts)
                if responsavel and 'Done Final Author' in pm_cases.columns:
                    keys_done = set(
                        pm_cases[pm_cases['Done Final Author'].astype(str) == str(responsavel)]['Issue Key']
                        .astype(str).str.strip().str.upper().tolist()
                    )
                itens_com_evidencia = len(keys_done.intersection(tech_keys))
                cobertura_tecnica_pct = (itens_com_evidencia / len(keys_done) * 100.0) if len(keys_done) > 0 else np.nan

        kpis = html.Div([
            create_kpi_card('Itens Únicos Finalizados (período)', total_concluidos, class_name='three columns'),
            create_kpi_card('Itens com Retrabalho', itens_retrabalho, class_name='three columns'),
            create_kpi_card('Taxa de Retrabalho', f"{taxa_retrabalho:.1f}%", class_name='three columns'),
            create_kpi_card('Conformidade Média', f"{conf_media:.2f}" if pd.notna(conf_media) else '—', class_name='three columns'),
            create_kpi_card('Cards Puxados p/ Dev', pull_dev_total_cards, class_name='three columns'),
            create_kpi_card('SP Puxados p/ Dev', f"{pull_dev_total_story_points:,.1f}", class_name='three columns'),
            create_kpi_card('Horas Execução (período)', f"{horas_execucao_periodo:,.1f}", class_name='three columns'),
            create_kpi_card('Horas no Fluxo (proxy)', f"{horas_fluxo_total:,.1f}", class_name='three columns'),
            create_kpi_card('Média h/Evento (proxy)', f"{horas_fluxo_media_evento:.2f}" if pd.notna(horas_fluxo_media_evento) else '—', class_name='three columns'),
            create_kpi_card('Cobertura Técnica', f"{cobertura_tecnica_pct:.1f}%" if pd.notna(cobertura_tecnica_pct) else '—', class_name='three columns'),
            create_kpi_card('Commits (Bitbucket)', int(bb_totals.get('Commits', 0)), class_name='three columns'),
            create_kpi_card('PRs Abertos (Bitbucket)', int(bb_totals.get('PRs Abertos', 0)), class_name='three columns'),
            create_kpi_card('PRs Declinados (Bitbucket)', int(bb_totals.get('PRs Declinados (Autor)', 0)), class_name='three columns'),
            create_kpi_card('Itens c/ Evidência Técnica', int(itens_com_evidencia), class_name='three columns'),
        ], className='row', style={'rowGap': '8px'})

        fig_vazao_pessoa = go.Figure()
        if not pm_people.empty and {'Responsavel', 'Itens Concluidos'}.issubset(pm_people.columns):
            people_plot = pm_people.copy()
            people_plot['Itens Concluidos'] = pd.to_numeric(people_plot['Itens Concluidos'], errors='coerce').fillna(0)
            if 'Taxa Retrabalho (%)' in people_plot.columns:
                people_plot['Taxa Retrabalho (%)'] = pd.to_numeric(people_plot['Taxa Retrabalho (%)'], errors='coerce')
            people_plot = people_plot.sort_values('Itens Concluidos', ascending=False).head(20)
            fig_vazao_pessoa = px.bar(
                people_plot,
                x='Itens Concluidos',
                y='Responsavel',
                orientation='h',
                color='Taxa Retrabalho (%)' if 'Taxa Retrabalho (%)' in people_plot.columns else None,
                title='Vazão por Pessoa (itens concluídos)',
                color_continuous_scale='RdYlGn_r'
            )
            fig_vazao_pessoa.update_layout(height=560, yaxis={'categoryorder': 'total ascending'})

        fig_pull_dev_overlay = go.Figure()
        if not pm_pull_dev_by_band.empty and {'Responsavel', 'Faixa Story Points', 'Cards Puxados'}.issubset(pm_pull_dev_by_band.columns):
            faixa_order = ['Sem estimativa', '0', '1', '2-3', '5', '8', '13+']
            fig_pull_dev_overlay = px.bar(
                pm_pull_dev_by_band,
                x='Cards Puxados',
                y='Responsavel',
                color='Faixa Story Points',
                orientation='h',
                barmode='stack',
                title='Cards puxados para In Development por pessoa (quebrado por faixa de story points)',
                hover_data=['Story Points Total'],
                category_orders={'Faixa Story Points': faixa_order},
            )
            fig_pull_dev_overlay.update_layout(
                height=max(520, 24 * max(1, len(pm_pull_dev_by_band['Responsavel'].cat.categories))),
                xaxis_title='Cards puxados',
                yaxis_title='Pessoa',
                legend_title_text='Faixa de Story Points',
            )

        fig_vazao_semanal = go.Figure()
        if not pm_weekly.empty and {'Semana', 'Responsavel', 'Itens Concluidos'}.issubset(pm_weekly.columns):
            pm_weekly['Itens Concluidos'] = pd.to_numeric(pm_weekly['Itens Concluidos'], errors='coerce').fillna(0)
            if responsavel:
                weekly_plot = pm_weekly.copy()
            else:
                top_people = []
                if not pm_people.empty and {'Responsavel', 'Itens Concluidos'}.issubset(pm_people.columns):
                    tmp = pm_people.copy()
                    tmp['Itens Concluidos'] = pd.to_numeric(tmp['Itens Concluidos'], errors='coerce').fillna(0)
                    top_people = tmp.sort_values('Itens Concluidos', ascending=False).head(5)['Responsavel'].tolist()
                weekly_plot = pm_weekly[pm_weekly['Responsavel'].isin(top_people)] if top_people else pm_weekly.copy()
            fig_vazao_semanal = px.line(
                weekly_plot,
                x='Semana',
                y='Itens Concluidos',
                color='Responsavel',
                markers=True,
                title='Vazão Semanal por Pessoa (Top 5)'
            )
            fig_vazao_semanal.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=120))

        fig_retrabalho_pessoa = go.Figure()
        if not pm_people.empty and {'Responsavel', 'Itens Com Retrabalho'}.issubset(pm_people.columns):
            retr_people = pm_people.copy()
            retr_people['Itens Com Retrabalho'] = pd.to_numeric(retr_people['Itens Com Retrabalho'], errors='coerce').fillna(0)
            if 'Taxa Retrabalho (%)' in retr_people.columns:
                retr_people['Taxa Retrabalho (%)'] = pd.to_numeric(retr_people['Taxa Retrabalho (%)'], errors='coerce')
            retr_people = retr_people.sort_values('Itens Com Retrabalho', ascending=False).head(20)
            fig_retrabalho_pessoa = px.bar(
                retr_people,
                x='Itens Com Retrabalho',
                y='Responsavel',
                orientation='h',
                color='Taxa Retrabalho (%)' if 'Taxa Retrabalho (%)' in retr_people.columns else None,
                title='Retrabalho por Pessoa (itens concluídos com retrabalho)',
                color_continuous_scale='OrRd'
            )
            fig_retrabalho_pessoa.update_layout(height=560, yaxis={'categoryorder': 'total ascending'})

        fig_tempo_status = go.Figure()
        if not pm_status.empty and {'Status', 'Tempo Mediano (dias)'}.issubset(pm_status.columns):
            status_plot = pm_status.copy()
            status_plot['Tempo Mediano (dias)'] = pd.to_numeric(status_plot['Tempo Mediano (dias)'], errors='coerce').fillna(0)
            status_plot = status_plot.sort_values('Tempo Mediano (dias)', ascending=False).head(15)
            fig_tempo_status = px.bar(
                status_plot,
                x='Tempo Mediano (dias)',
                y='Status',
                orientation='h',
                title='Tempos por Status (Mediana)'
            )
            fig_tempo_status.update_layout(height=520, yaxis={'categoryorder': 'total ascending'})

        fig_variantes = go.Figure()
        if not pm_variants.empty and {'Variant', 'Qtde Casos'}.issubset(pm_variants.columns):
            variants_plot = pm_variants.copy()
            variants_plot['Qtde Casos'] = pd.to_numeric(variants_plot['Qtde Casos'], errors='coerce').fillna(0)
            if 'Pct Casos' in variants_plot.columns:
                variants_plot['Pct Casos'] = pd.to_numeric(variants_plot['Pct Casos'], errors='coerce')
            variants_plot = variants_plot.sort_values('Qtde Casos', ascending=False).head(20)
            fig_variantes = px.bar(
                variants_plot,
                x='Qtde Casos',
                y='Variant',
                orientation='h',
                color='Pct Casos' if 'Pct Casos' in variants_plot.columns else None,
                title='Variantes Mais Frequentes (Top 20)',
                color_continuous_scale='Viridis'
            )
            fig_variantes.update_layout(height=620, yaxis={'categoryorder': 'total ascending'})

        fig_dfg_edges = go.Figure()
        if not pm_dfg_edges.empty and {'From', 'To', 'Count'}.issubset(pm_dfg_edges.columns):
            dfg_plot = pm_dfg_edges.copy()
            dfg_plot['Count'] = pd.to_numeric(dfg_plot['Count'], errors='coerce').fillna(0)
            dfg_plot['Aresta'] = dfg_plot['From'].astype(str) + ' -> ' + dfg_plot['To'].astype(str)
            dfg_plot = dfg_plot.sort_values('Count', ascending=False).head(25)
            fig_dfg_edges = px.bar(
                dfg_plot,
                x='Count',
                y='Aresta',
                orientation='h',
                title='DFG PM4Py - Top Arestas por Frequência'
            )
            fig_dfg_edges.update_layout(height=720, yaxis={'categoryorder': 'total ascending'})

        fig_dfg_perf = go.Figure()
        if not pm_dfg_perf_edges.empty and {'From', 'To', 'PerfHours'}.issubset(pm_dfg_perf_edges.columns):
            dfg_perf_plot = pm_dfg_perf_edges.copy()
            dfg_perf_plot['PerfHours'] = pd.to_numeric(dfg_perf_plot['PerfHours'], errors='coerce').fillna(0)
            dfg_perf_plot['Aresta'] = dfg_perf_plot['From'].astype(str) + ' -> ' + dfg_perf_plot['To'].astype(str)
            dfg_perf_plot = dfg_perf_plot.sort_values('PerfHours', ascending=False).head(25)
            fig_dfg_perf = px.bar(
                dfg_perf_plot,
                x='PerfHours',
                y='Aresta',
                orientation='h',
                title='DFG PM4Py Performance - Top Arestas por Tempo (horas)'
            )
            fig_dfg_perf.update_layout(height=720, yaxis={'categoryorder': 'total ascending'})

        fig_tbr_fitness = go.Figure()
        if not pm_tbr_cases.empty and 'TraceFitness' in pm_tbr_cases.columns:
            tbr_hist = pm_tbr_cases.copy()
            tbr_hist['TraceFitness'] = pd.to_numeric(tbr_hist['TraceFitness'], errors='coerce')
            tbr_hist = tbr_hist.dropna(subset=['TraceFitness'])
            if not tbr_hist.empty:
                fig_tbr_fitness = px.histogram(
                    tbr_hist,
                    x='TraceFitness',
                    nbins=20,
                    title='Token-Based Replay (PM4Py) - Distribuição de Trace Fitness'
                )
                fig_tbr_fitness.update_layout(height=420)

        jira_bitbucket_traceability_section = build_pm_commits_vs_jira_report(
            pm_people=pm_people,
            pm_cases=pm_cases,
            start_ts=start_ts,
            end_ts=end_ts,
            responsavel=responsavel,
        )

        if not pm_rework.empty:
            sort_cols = [c for c in ['Rework Score', 'Reopen Count', 'Backward Moves'] if c in pm_rework.columns]
            if sort_cols:
                pm_rework = pm_rework.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        rework_cols = [c for c in [
            'Issue Key', 'Tipo de Problema', 'Rework Score', 'Reopen Count', 'Backward Moves', 'QA Returns',
            'Revisitas Status', 'Conformance Score', 'Done Final Author', 'Done Final Date'
        ] if c in pm_rework.columns]
        people_table_cols = [c for c in [
            'Responsavel', 'Itens Concluidos', 'Itens Com Retrabalho', 'Taxa Retrabalho (%)',
            'Rework Score Total', 'Lead Time Mediano (dias)', 'Media Itens/Semana Ativa'
        ] if c in pm_people.columns]
        horas_people_cols = [c for c in ['Responsavel', 'HorasNoFluxo', 'HorasMediasPorEvento', 'Eventos', 'CardsUnicos'] if c in pm_hours_people.columns]
        horas_status_cols = [c for c in ['Responsavel', 'Status', 'HorasNoFluxo', 'Eventos', 'CardsUnicos'] if c in pm_hours_status.columns]
        pull_dev_cols = [c for c in ['Issue Key', 'Responsavel', 'Senioridade', 'Faixa Story Points', 'StoryPoints_Value', 'History Created', 'From Status', 'To Status'] if c in pm_pull_dev.columns]
        tbr_summary_cols = [c for c in ['Metric', 'Value'] if c in pm_tbr_summary.columns]
        tbr_case_cols = [c for c in ['Issue Key', 'TraceIsFit', 'TraceFitness', 'MissingTokens', 'RemainingTokens', 'ConsumedTokens', 'ProducedTokens'] if c in pm_tbr_cases.columns]
        align_summary_cols = [c for c in ['Metric', 'Value'] if c in pm_align_summary.columns]
        align_case_cols = [c for c in ['Issue Key', 'AlignmentFitness', 'AlignmentCost', 'SyncMoves', 'LogMoves', 'ModelMoves', 'DesviosTotal'] if c in pm_align_cases.columns]
        align_move_cols = [c for c in ['Move', 'Count', 'CasesAffected'] if c in pm_align_moves.columns]
        conf_table_cols = [c for c in ['Metrica', 'Valor'] if c in pm_summary.columns]
        meta_table_cols = [c for c in ['Metrica', 'Valor'] if c in pm_meta.columns]

        return html.Div([
            html.H3('Process Mining Jira - W1NNER (História, Task, Bug)', style={'textAlign': 'center'}),
            html.P(
                f"Relatório fonte: {os.path.basename(report_path) if report_path else 'n/d'} | Foco em vazão por pessoa e retrabalho.",
                style={'textAlign': 'center', 'color': '#555'}
            ),
            kpis,
            dcc.Graph(figure=fig_vazao_pessoa),
            dcc.Graph(figure=fig_pull_dev_overlay),
            dcc.Graph(figure=fig_vazao_semanal),
            dcc.Graph(figure=fig_retrabalho_pessoa),
            dcc.Graph(figure=fig_tempo_status),
            html.H4('Descoberta e Estrutura do Fluxo (PM4Py)', style={'marginTop': '18px'}),
            dcc.Graph(figure=fig_variantes),
            dcc.Graph(figure=fig_dfg_edges),
            dcc.Graph(figure=fig_dfg_perf),
            html.H4('Conformidade PM4Py (Token-Based Replay / Alignments)', style={'marginTop': '16px'}),
            dcc.Graph(figure=fig_tbr_fitness),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in tbr_summary_cols],
                data=pm_tbr_summary[tbr_summary_cols].to_dict('records') if tbr_summary_cols else [],
                style_cell={'textAlign': 'left', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                page_size=10,
            ),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in tbr_case_cols],
                data=pm_tbr_cases[tbr_case_cols].head(50).to_dict('records') if tbr_case_cols else [],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '6px', 'minWidth': '100px', 'maxWidth': '220px', 'whiteSpace': 'normal'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                sort_action='native',
                filter_action='native',
                page_size=10,
            ),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in align_summary_cols],
                data=pm_align_summary[align_summary_cols].to_dict('records') if align_summary_cols else [],
                style_cell={'textAlign': 'left', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                page_size=10,
            ),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in align_move_cols],
                data=pm_align_moves[align_move_cols].head(50).to_dict('records') if align_move_cols else [],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '6px', 'minWidth': '100px', 'maxWidth': '220px', 'whiteSpace': 'normal'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                sort_action='native',
                filter_action='native',
                page_size=10,
            ),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in align_case_cols],
                data=pm_align_cases[align_case_cols].head(50).to_dict('records') if align_case_cols else [],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '6px', 'minWidth': '100px', 'maxWidth': '220px', 'whiteSpace': 'normal'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                sort_action='native',
                filter_action='native',
                page_size=10,
            ),
            jira_bitbucket_traceability_section,
            html.H4('Resumo por Pessoa', style={'marginTop': '10px'}),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in people_table_cols],
                data=pm_people[people_table_cols].head(50).to_dict('records') if people_table_cols else [],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                sort_action='native',
                page_size=12,
            ),
            html.H4('Itens puxados para In Development por pessoa e faixa de story points', style={'marginTop': '16px'}),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in pull_dev_cols],
                data=pm_pull_dev[pull_dev_cols].head(200).to_dict('records') if pull_dev_cols else [],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '6px', 'minWidth': '100px', 'maxWidth': '240px', 'whiteSpace': 'normal'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                sort_action='native',
                filter_action='native',
                page_size=12,
            ),
            html.H4('Horas no Fluxo por Pessoa (proxy por transição/status)', style={'marginTop': '16px'}),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in horas_people_cols],
                data=pm_hours_people[horas_people_cols].head(50).to_dict('records') if horas_people_cols else [],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                sort_action='native',
                page_size=12,
            ),
            html.H4('Horas no Fluxo por Pessoa e Status', style={'marginTop': '16px'}),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in horas_status_cols],
                data=pm_hours_status[horas_status_cols].head(60).to_dict('records') if horas_status_cols else [],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '6px', 'minWidth': '100px', 'maxWidth': '240px', 'whiteSpace': 'normal'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                sort_action='native',
                filter_action='native',
                page_size=12,
            ),
            html.H4('Top Itens com Retrabalho', style={'marginTop': '16px'}),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in rework_cols],
                data=pm_rework[rework_cols].head(50).to_dict('records') if rework_cols else [],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '6px', 'minWidth': '100px', 'maxWidth': '240px', 'whiteSpace': 'normal'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                sort_action='native',
                filter_action='native',
                page_size=12,
            ),
            html.H4('Resumo de Conformidade Básica', style={'marginTop': '16px'}),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in conf_table_cols],
                data=pm_summary[conf_table_cols].to_dict('records') if conf_table_cols else [],
                style_cell={'textAlign': 'left', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                page_size=12,
            ),
            html.H4('Metadados PM4Py / Execução', style={'marginTop': '16px'}),
            dash_table.DataTable(
                columns=[{'name': c, 'id': c} for c in meta_table_cols],
                data=pm_meta[meta_table_cols].to_dict('records') if meta_table_cols else [],
                style_cell={'textAlign': 'left', 'padding': '6px', 'whiteSpace': 'normal'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                page_size=10,
            ),
        ])

    if tab == 'tab-work-item-age':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)
        today_ts = pd.Timestamp.today().normalize()
        snapshot_ts = min(end_date_ts.normalize(), today_ts)

        df_age_base = fato.copy()
        if projeto:
            df_age_base = df_age_base[df_age_base['Projeto'] == projeto]
        if tipo:
            df_age_base = df_age_base[df_age_base['TipoDemanda'] == tipo]
        if classe_servico:
            df_age_base = df_age_base[df_age_base['ClasseServico'] == classe_servico]
        if responsavel:
            df_age_base = df_age_base[df_age_base['Responsavel'] == responsavel]
        df_age_base, _ = apply_selected_lead_time_metric(df_age_base, projeto, leadtime_stages)

        in_progress_series = pd.to_datetime(df_age_base.get('DataInProgress'), errors='coerce')
        done_series = pd.to_datetime(df_age_base.get('DataDone'), errors='coerce')
        active_mask = (
            in_progress_series.notna() &
            (in_progress_series <= snapshot_ts) &
            (done_series.isna() | (done_series > snapshot_ts))
        )
        df_age = df_age_base[active_mask].copy()
        if df_age.empty:
            return html.Div(
                'Sem itens ativos com DataInProgress válida para calcular Work Item Age no recorte selecionado.'
            )

        df_age['DataInProgress'] = pd.to_datetime(df_age.get('DataInProgress'), errors='coerce')
        df_age['WorkItemAge_Dias'] = (snapshot_ts - df_age['DataInProgress']).dt.total_seconds() / 86400.0
        df_age['WorkItemAge_Dias'] = pd.to_numeric(df_age['WorkItemAge_Dias'], errors='coerce')
        df_age = df_age[df_age['WorkItemAge_Dias'].notna()].copy()
        if df_age.empty:
            return html.Div('Sem itens ativos com idade calculável para o recorte selecionado.')

        done_period_mask = (
            (pd.to_datetime(df_age_base.get('DataDone'), errors='coerce') >= start_date_ts) &
            (pd.to_datetime(df_age_base.get('DataDone'), errors='coerce') <= end_date_ts)
        )
        df_cycle_done = df_age_base[done_period_mask].copy()
        df_cycle_done = df_cycle_done[done_time_eligible_mask(df_cycle_done)].copy()
        cycle_series = time_metric_series(df_cycle_done, 'TempoExecucao_Dias', non_negative=True)
        if cycle_series.empty:
            cycle_series = time_metric_series(df_cycle_done, 'CycleTime_Dias', non_negative=True)

        cycle_p50 = exact_empirical_percentile(cycle_series, 0.50) if not cycle_series.empty else np.nan
        cycle_p85 = exact_empirical_percentile(cycle_series, 0.85) if not cycle_series.empty else np.nan
        cycle_mean = float(cycle_series.mean()) if not cycle_series.empty else np.nan

        df_age['SaudeAge'] = df_age['WorkItemAge_Dias'].apply(lambda v: _work_item_age_health_label(v, cycle_p50, cycle_p85))
        df_age['AgeBucket'] = df_age['WorkItemAge_Dias'].apply(_work_item_age_bucket)
        df_age['RazaoVsCycleP50'] = np.where(
            pd.notna(cycle_p50) and cycle_p50 > 0,
            df_age['WorkItemAge_Dias'] / cycle_p50,
            np.nan,
        )
        df_age['BloqueadoFlag'] = df_age.get('Bloqueado', False).fillna(False).astype(bool) if 'Bloqueado' in df_age.columns else False
        df_age['BloqueadoLabel'] = np.where(df_age['BloqueadoFlag'], 'Bloqueado', 'Sem bloqueio')

        item_key_col = next((c for c in ['ItemID', 'Issue Key', 'ID'] if c in df_age.columns), None)
        title_col = next((c for c in ['Titulo', 'Title', 'Summary'] if c in df_age.columns), None)
        type_col = next((c for c in ['TipoDemanda', 'Tipo', 'Tipo de Problema'] if c in df_age.columns), None)
        if 'Status' not in df_age.columns:
            df_age['Status'] = 'Sem status'
        else:
            df_age['Status'] = df_age['Status'].fillna('').astype(str).replace('', 'Sem status')
        if 'Responsavel' not in df_age.columns:
            df_age['Responsavel'] = 'Sem responsável'
        else:
            df_age['Responsavel'] = df_age['Responsavel'].fillna('').astype(str).replace('', 'Sem responsável')
        if 'ClasseServico' not in df_age.columns:
            df_age['ClasseServico'] = 'Sem classe'
        else:
            df_age['ClasseServico'] = df_age['ClasseServico'].fillna('').astype(str).replace('', 'Sem classe')
        if 'Projeto' not in df_age.columns:
            df_age['Projeto'] = 'Sem projeto'
        else:
            df_age['Projeto'] = df_age['Projeto'].fillna('').astype(str).replace('', 'Sem projeto')

        if item_key_col is None:
            df_age['ItemKey'] = df_age.index.astype(str)
        else:
            df_age['ItemKey'] = df_age[item_key_col].astype(str)
        if title_col is None:
            df_age['TituloDisplay'] = ''
        else:
            df_age['TituloDisplay'] = df_age[title_col].fillna('').astype(str)
        df_age['ItemLabel'] = df_age['ItemKey'] + np.where(
            df_age['TituloDisplay'].str.strip() != '',
            ' - ' + df_age['TituloDisplay'].str.slice(0, 60),
            ''
        )

        severity_order = {'Crítico': 0, 'Atenção': 1, 'Saudável': 2, 'Sem referência': 3, 'Sem idade': 4}
        severity_colors = {
            'Crítico': '#C62828',
            'Atenção': '#EF6C00',
            'Saudável': '#2E7D32',
            'Sem referência': '#546E7A',
            'Sem idade': '#90A4AE',
        }
        age_bucket_order = ['0-7d', '8-15d', '16-30d', '31-60d', '60d+', 'Sem idade']
        df_age['_severity_rank'] = df_age['SaudeAge'].map(lambda value: severity_order.get(value, 99))

        risk_summary = (
            df_age.groupby('SaudeAge', dropna=False)
            .agg(
                Itens=('ItemKey', 'count'),
                IdadeMedia=('WorkItemAge_Dias', 'mean'),
                IdadeMediana=('WorkItemAge_Dias', 'median'),
                IdadeMax=('WorkItemAge_Dias', 'max'),
                Bloqueados=('BloqueadoFlag', 'sum'),
            )
            .reset_index()
            .rename(columns={'SaudeAge': 'Saúde'})
        )
        if not risk_summary.empty:
            for col in ['IdadeMedia', 'IdadeMediana', 'IdadeMax']:
                risk_summary[col] = pd.to_numeric(risk_summary[col], errors='coerce').round(1)
            risk_summary['_severity_rank'] = risk_summary['Saúde'].map(lambda value: severity_order.get(value, 99))
            risk_summary = risk_summary.sort_values('_severity_rank', ignore_index=True).drop(columns=['_severity_rank'])

        status_summary = (
            df_age.groupby(['Status', 'SaudeAge'], dropna=False)
            .agg(
                Itens=('ItemKey', 'count'),
                IdadeMedia=('WorkItemAge_Dias', 'mean'),
                IdadeMax=('WorkItemAge_Dias', 'max'),
            )
            .reset_index()
            .rename(columns={'SaudeAge': 'Saúde'})
        )
        if not status_summary.empty:
            status_summary['IdadeMedia'] = pd.to_numeric(status_summary['IdadeMedia'], errors='coerce').round(1)
            status_summary['IdadeMax'] = pd.to_numeric(status_summary['IdadeMax'], errors='coerce').round(1)

        owner_summary = pd.DataFrame()
        if 'Responsavel' in df_age.columns:
            owner_summary = (
                df_age.groupby('Responsavel', dropna=False)
                .agg(
                    Itens=('ItemKey', 'count'),
                    IdadeMedia=('WorkItemAge_Dias', 'mean'),
                    IdadeMax=('WorkItemAge_Dias', 'max'),
                    Bloqueados=('BloqueadoFlag', 'sum'),
                )
                .reset_index()
                .rename(columns={'Responsavel': 'Responsável'})
            )
            owner_summary['Responsável'] = owner_summary['Responsável'].fillna('').replace('', 'Sem responsável')
            owner_summary['IdadeMedia'] = pd.to_numeric(owner_summary['IdadeMedia'], errors='coerce').round(1)
            owner_summary['IdadeMax'] = pd.to_numeric(owner_summary['IdadeMax'], errors='coerce').round(1)
            owner_summary = owner_summary.sort_values(['IdadeMedia', 'Itens'], ascending=[False, False], ignore_index=True)

        df_age['AgeBucket'] = pd.Categorical(df_age['AgeBucket'], categories=age_bucket_order, ordered=True)
        age_bucket_summary = (
            df_age.groupby(['AgeBucket', 'SaudeAge'], dropna=False)
            .size()
            .reset_index(name='Itens')
        )
        age_bucket_summary['AgeBucket'] = age_bucket_summary['AgeBucket'].astype(str)
        age_bucket_summary = age_bucket_summary[age_bucket_summary['AgeBucket'] != 'nan']

        top_oldest = (
            df_age.sort_values(['_severity_rank', 'WorkItemAge_Dias'], ascending=[True, False], ignore_index=True)
            .head(15)
            .copy()
        )
        top_oldest = top_oldest.sort_values('WorkItemAge_Dias', ascending=True)

        fig_age_hist = px.histogram(
            df_age,
            x='WorkItemAge_Dias',
            color='SaudeAge',
            nbins=min(24, max(8, int(np.ceil(np.sqrt(len(df_age)))))),
            title='Distribuição do Work Item Age',
            labels={'WorkItemAge_Dias': 'Work Item Age (dias)', 'count': 'Itens', 'SaudeAge': 'Saúde'},
            color_discrete_map=severity_colors,
        )
        if pd.notna(cycle_p50):
            fig_age_hist.add_vline(x=float(cycle_p50), line_dash='dash', line_color='#1F77B4', annotation_text=f'Cycle P50: {cycle_p50:.1f}d')
        if pd.notna(cycle_p85):
            fig_age_hist.add_vline(x=float(cycle_p85), line_dash='dot', line_color='#8E24AA', annotation_text=f'Cycle P85: {cycle_p85:.1f}d')
        fig_age_hist.update_layout(height=480, barmode='overlay', margin=dict(b=60))

        fig_top_oldest = px.bar(
            top_oldest,
            x='WorkItemAge_Dias',
            y='ItemLabel',
            color='SaudeAge',
            orientation='h',
            title='Itens ativos mais envelhecidos',
            labels={'WorkItemAge_Dias': 'Work Item Age (dias)', 'ItemLabel': 'Item', 'SaudeAge': 'Saúde'},
            color_discrete_map=severity_colors,
            hover_data=['Status', 'Responsavel', 'ClasseServico'] if 'Responsavel' in top_oldest.columns and 'ClasseServico' in top_oldest.columns else None,
        )
        fig_top_oldest.update_layout(height=520, margin=dict(l=120, r=30, t=60, b=40), yaxis_title='')

        scatter_hover = [c for c in ['ItemKey', 'TituloDisplay', 'Status', 'Responsavel', 'ClasseServico', 'Projeto'] if c in df_age.columns]
        fig_age_scatter = px.scatter(
            df_age.sort_values('DataInProgress'),
            x='DataInProgress',
            y='WorkItemAge_Dias',
            color='SaudeAge',
            symbol='BloqueadoLabel',
            hover_data=scatter_hover,
            title='Work Item Age por data de início',
            labels={'DataInProgress': 'Data de início', 'WorkItemAge_Dias': 'Work Item Age (dias)', 'SaudeAge': 'Saúde'},
            color_discrete_map=severity_colors,
        )
        if pd.notna(cycle_p50):
            fig_age_scatter.add_hline(y=float(cycle_p50), line_dash='dash', line_color='#1F77B4', annotation_text=f'Cycle P50: {cycle_p50:.1f}d')
        if pd.notna(cycle_p85):
            fig_age_scatter.add_hline(y=float(cycle_p85), line_dash='dot', line_color='#8E24AA', annotation_text=f'Cycle P85: {cycle_p85:.1f}d')
        fig_age_scatter.update_layout(height=500, margin=dict(b=90), xaxis_tickangle=-45)

        fig_age_bucket = px.bar(
            age_bucket_summary,
            x='AgeBucket',
            y='Itens',
            color='SaudeAge',
            barmode='stack',
            title='Faixas de Work Item Age por severidade',
            labels={'AgeBucket': 'Faixa de idade', 'Itens': 'Itens', 'SaudeAge': 'Saúde'},
            color_discrete_map=severity_colors,
            category_orders={'AgeBucket': age_bucket_order},
        )
        fig_age_bucket.update_layout(height=420, margin=dict(b=40))

        critical_items = int((df_age['SaudeAge'] == 'Crítico').sum())
        attention_items = int((df_age['SaudeAge'] == 'Atenção').sum())
        blocked_items = int(df_age['BloqueadoFlag'].sum())
        total_items = int(len(df_age))
        avg_age = float(df_age['WorkItemAge_Dias'].mean()) if total_items else np.nan
        median_age = float(df_age['WorkItemAge_Dias'].median()) if total_items else np.nan
        max_age = float(df_age['WorkItemAge_Dias'].max()) if total_items else np.nan
        critical_pct = (critical_items / total_items * 100.0) if total_items else 0.0

        subtitle_parts = [
            f"Snapshot considerado: {snapshot_ts.strftime('%d/%m/%Y')}",
            f"Itens ativos: {total_items}",
            f"Amostra de Cycle Time concluído: {int(len(cycle_series))}",
        ]
        if pd.notna(cycle_mean):
            subtitle_parts.append(f"Cycle médio: {cycle_mean:.1f}d")
        if pd.notna(cycle_p50):
            subtitle_parts.append(f"Cycle P50: {cycle_p50:.1f}d")
        if pd.notna(cycle_p85):
            subtitle_parts.append(f"Cycle P85: {cycle_p85:.1f}d")
        subtitle = " | ".join(subtitle_parts)

        if pd.notna(cycle_p50):
            interpretation = (
                "Saudável = idade <= Cycle P50; Atenção = entre Cycle P50 e P85; "
                "Crítico = acima do Cycle P85 do mesmo recorte."
            )
        else:
            interpretation = (
                "Sem referência factual de Cycle Time concluído no recorte; a aba mantém a idade dos itens "
                "e sinaliza a limitação."
            )

        detail_cols = [
            ('ItemKey', 'Item'),
            ('TituloDisplay', 'Título'),
            ('Projeto', 'Projeto'),
            ('Status', 'Status'),
            ('Responsavel', 'Responsável'),
            ('ClasseServico', 'Classe Serviço'),
            ('BloqueadoLabel', 'Bloqueio'),
            ('DataInProgress', 'Data Início'),
            ('WorkItemAge_Dias', 'Work Item Age (dias)'),
            ('RazaoVsCycleP50', 'Razão vs Cycle P50'),
            ('SaudeAge', 'Saúde'),
            ('Link', 'Link'),
        ]
        if type_col and type_col not in {'TipoDemanda', 'Tipo'}:
            detail_cols.insert(3, (type_col, 'Tipo'))
        elif type_col:
            detail_cols.insert(3, (type_col, type_col))
        available_detail_cols = [src for src, _ in detail_cols if src in df_age.columns]
        detail_rename = {src: dst for src, dst in detail_cols if src in available_detail_cols}
        detail_df = df_age[available_detail_cols].copy().rename(columns=detail_rename)
        if 'Data Início' in detail_df.columns:
            detail_df['Data Início'] = pd.to_datetime(detail_df['Data Início'], errors='coerce').dt.strftime('%d/%m/%Y')
        for col in ['Work Item Age (dias)', 'Razão vs Cycle P50']:
            if col in detail_df.columns:
                detail_df[col] = pd.to_numeric(detail_df[col], errors='coerce').round(1)
        detail_df = detail_df.sort_values(
            ['Saúde', 'Work Item Age (dias)'] if 'Work Item Age (dias)' in detail_df.columns else ['Saúde'],
            ascending=[True, False],
            key=lambda s: s.map(severity_order) if s.name == 'Saúde' else s,
            ignore_index=True,
        )

        return html.Div([
            html.H3("Work Item Age", style={'textAlign': 'center'}),
            html.P(subtitle, style={'textAlign': 'center', 'color': '#666', 'marginBottom': '8px'}),
            html.P(interpretation, style={'textAlign': 'center', 'color': '#666', 'marginBottom': '18px'}),
            html.Div([
                create_kpi_card('Itens Ativos', total_items, class_name='three columns'),
                create_kpi_card('Age Médio', f"{avg_age:.1f}d" if pd.notna(avg_age) else '—', class_name='three columns'),
                create_kpi_card('Age Mediano', f"{median_age:.1f}d" if pd.notna(median_age) else '—', class_name='three columns'),
                create_kpi_card('Age Máximo', f"{max_age:.1f}d" if pd.notna(max_age) else '—', class_name='three columns'),
                create_kpi_card('Críticos', critical_items, class_name='three columns'),
                create_kpi_card('Em Atenção', attention_items, class_name='three columns'),
                create_kpi_card('Bloqueados', blocked_items, class_name='three columns'),
                create_kpi_card('% Críticos', f"{critical_pct:.1f}%", class_name='three columns'),
            ], className='row'),
            dcc.Graph(figure=fig_age_hist),
            dcc.Graph(figure=fig_age_bucket),
            dcc.Graph(figure=fig_top_oldest),
            dcc.Graph(figure=fig_age_scatter),
            html.H4("Resumo por Severidade", style={'textAlign': 'center', 'marginTop': '24px'}),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in risk_summary.columns],
                data=risk_summary.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248,248,248)'}],
            ),
            html.H4("Resumo por Status", style={'textAlign': 'center', 'marginTop': '24px'}),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in status_summary.columns],
                data=status_summary.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248,248,248)'}],
                page_size=12,
            ),
            html.H4("Resumo por Responsável", style={'textAlign': 'center', 'marginTop': '24px'}),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in owner_summary.columns],
                data=owner_summary.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248,248,248)'}],
                page_size=12,
            ) if not owner_summary.empty else html.P('Sem dados suficientes por responsável no recorte.'),
            html.H4("Detalhe dos Itens Ativos", style={'textAlign': 'center', 'marginTop': '24px'}),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in detail_df.columns],
                data=detail_df.to_dict('records'),
                page_size=15,
                filter_action='native',
                sort_action='native',
                style_table={'overflowX': 'auto'},
                style_cell={'minWidth': '100px', 'width': '140px', 'maxWidth': '220px', 'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {'if': {'filter_query': '{Saúde} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                    {'if': {'filter_query': '{Saúde} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                    {'if': {'filter_query': '{Saúde} = "Saudável"'}, 'backgroundColor': '#edf7ed'},
                ],
            ),
        ])

    if tab == 'tab-wip':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        df_wip_base = fato.copy()
        if projeto: df_wip_base = df_wip_base[df_wip_base['Projeto'] == projeto]
        if responsavel: df_wip_base = df_wip_base[df_wip_base['Responsavel'] == responsavel]

        if 'Responsavel' not in df_wip_base.columns or df_wip_base['Responsavel'].dropna().empty:
            return html.Div('Dados de Responsável não disponíveis para calcular WIP.')

        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        if weeks.empty:
            return html.Div("Período selecionado é muito curto para análise semanal.")

        wip_weekly_data = []
        for week_end in weeks:
            wip_at_date_df = df_wip_base[(df_wip_base['DataInProgress'] <= week_end) & ((df_wip_base['DataDone'] > week_end) | pd.isna(df_wip_base['DataDone']))]
            wip_counts = wip_at_date_df.groupby('Responsavel').size().reset_index(name='WIP')
            wip_counts['Semana'] = week_end
            wip_weekly_data.append(wip_counts)

        if not wip_weekly_data:
            return html.Div('Sem dados de WIP para o período e filtros selecionados.')

        wip_df = pd.concat(wip_weekly_data, ignore_index=True)
        if wip_df.empty:
            return html.Div('Sem dados de WIP para o período e filtros selecionados.')

        summary_data = []
        for person in wip_df['Responsavel'].unique():
            person_wip = wip_df[wip_df['Responsavel'] == person]
            wip_medio = person_wip['WIP'].mean()
            wip_max = person_wip['WIP'].max()
            last_week_data = person_wip[person_wip['Semana'] == person_wip['Semana'].max()]
            items_ativos_fim = last_week_data['WIP'].iloc[0] if not last_week_data.empty else 0
            
            summary_data.append({'Responsável': person, 'WIP Médio Semanal': wip_medio, 'WIP Máximo na Semana': wip_max, 'Items Ativos no Fim': items_ativos_fim})

        summary_df = pd.DataFrame(
            summary_data,
            columns=['Responsável', 'WIP Médio Semanal', 'WIP Máximo na Semana', 'Items Ativos no Fim']
        )
        if summary_df.empty:
            return html.Div('Sem dados consolidados de WIP por responsável para o período e filtros selecionados.')
        summary_df = summary_df.sort_values('WIP Médio Semanal', ascending=False)

        kpi_table = dash_table.DataTable(
            columns=[
                {"name": "Responsável", "id": "Responsável"},
                {"name": "WIP Médio Semanal", "id": "WIP Médio Semanal", "type": "numeric", "format": dash_table.Format.Format(precision=1, scheme=dash_table.Format.Scheme.fixed)},
                {"name": "WIP Máximo na Semana", "id": "WIP Máximo na Semana", "type": "numeric"},
                {"name": "Items Ativos no Fim", "id": "Items Ativos no Fim", "type": "numeric"},
            ],
            data=summary_df.to_dict('records'),
            style_cell={'textAlign': 'left'}, style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}, sort_action="native"
        )

        fig_wip_avg = px.bar(summary_df.head(30), x='Responsável', y='WIP Médio Semanal', title='WIP Médio Semanal por Pessoa (Top 30)')
        fig_wip_avg.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        if responsavel:
            df_trend = wip_df
        else:
            top_responsaveis = summary_df.head(5)['Responsável'].tolist()
            df_trend = wip_df[wip_df['Responsavel'].isin(top_responsaveis)]
            
        fig_wip_trend = px.line(df_trend, x='Semana', y='WIP', color='Responsavel', title='Tendência do WIP Semanal (Top 5 Responsáveis)', markers=True)
        # Adiciona linhas estatísticas para o WIP total por semana
        wip_total_weekly = df_trend.groupby('Semana')['WIP'].sum().reset_index()
        if not wip_total_weekly.empty:
            add_statistical_lines(fig_wip_trend, wip_total_weekly['Semana'], wip_total_weekly['WIP'], name_prefix='Total ')
        fig_wip_trend.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        return html.Div([
            html.H3("Análise de WIP por Pessoa", style={'textAlign': 'center'}),
            html.H4("Resumo do Período", style={'textAlign': 'center', 'marginTop': '30px'}),
            kpi_table,
            dcc.Graph(figure=fig_wip_avg),
            dcc.Graph(figure=fig_wip_trend),
        ])

    if tab == 'tab-estatistica':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        # Base única da aba (mesmos filtros ativos), sem recorte de DataDone.
        # O recorte temporal é aplicado por métrica para manter consistência entre
        # "Todos os projetos" e filtros por projeto.
        df_base = fato.copy()
        if projeto:
            df_base = df_base[df_base['Projeto'] == projeto]
        if tipo:
            df_base = df_base[df_base['TipoDemanda'] == tipo]
        if classe_servico:
            df_base = df_base[df_base['ClasseServico'] == classe_servico]
        if responsavel:
            df_base = df_base[df_base['Responsavel'] == responsavel]
        df_base, _ = apply_selected_lead_time_metric(df_base, projeto, leadtime_stages)

        # Itens concluídos no período (para Lead Time e Throughput)
        done_period_mask = (
            (pd.to_datetime(df_base['DataDone'], errors='coerce') >= start_date_ts) &
            (pd.to_datetime(df_base['DataDone'], errors='coerce') <= end_date_ts)
        )
        df_done = df_base[done_period_mask].copy()
        df_done = df_done[done_time_eligible_mask(df_done)].copy()

        # --- 1. Estatísticas de Lead Time (base compartilhada com aba Lead Time) ---
        lead_time_stats = {}
        lead_col = 'LeadTime_Selected_Dias' if 'LeadTime_Selected_Dias' in df_done.columns else 'LeadTime_Dias'
        df_done_lt, lt, lt_comparable_stats = build_lead_time_comparable_scope(df_done, lead_col=lead_col)
        if not lt.empty:
            lt_exact = exact_percentile_map(lt, [0.25, 0.50, 0.75, 0.85, 0.95])
            lt_weibull = fit_weibull_linearized(lt)
            lead_time_stats = {
                'Contagem': int(len(lt)),
                'Média': f"{lt.mean():.2f}",
                'Mediana (P50)': f"{lt_exact.get(0.50, np.nan):.2f}",
                'Desvio Padrão': f"{lt.std():.2f}",
                'Mínimo': f"{lt.min():.2f}",
                'Máximo': f"{lt.max():.2f}",
                'P25': f"{lt_exact.get(0.25, np.nan):.2f}",
                'P75': f"{lt_exact.get(0.75, np.nan):.2f}",
                'P85': f"{lt_exact.get(0.85, np.nan):.2f}",
                'P95': f"{lt_exact.get(0.95, np.nan):.2f}",
                'Weibull Shape (k)': f"{lt_weibull['shape']:.4f}" if lt_weibull else '—',
                'Weibull Lambda (λ)': f"{lt_weibull['lambda']:.4f}" if lt_weibull else '—',
                'Coef. Variação (%)': f"{(lt.std() / lt.mean() * 100):.2f}" if lt.mean() > 0 else '—',
                'Amplitude': f"{lt.max() - lt.min():.2f}",
                'IQR (P75-P25)': f"{lt_exact.get(0.75, np.nan) - lt_exact.get(0.25, np.nan):.2f}",
                'Assimetria (Skewness)': f"{lt.skew():.2f}",
                'Curtose': f"{lt.kurtosis():.2f}",
            }

        def parse_optional_number(value):
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                return np.nan
            return parsed if np.isfinite(parsed) else np.nan

        lsl_value = parse_optional_number(estatistica_lsl)
        usl_value = parse_optional_number(estatistica_usl)
        lsl_input_value = float(lsl_value) if np.isfinite(lsl_value) else None
        usl_input_value = float(usl_value) if np.isfinite(usl_value) else None
        capability_metrics = compute_process_capability_metrics(lt, lsl=lsl_value, usl=usl_value)

        capability_table_data = []
        capability_msg = None
        if capability_metrics.get('error'):
            capability_msg = capability_metrics['error']
        else:
            capability_table_data = [
                {'Métrica': 'Amostra (n)', 'Valor': f"{capability_metrics['count']}"},
                {'Métrica': 'LSL', 'Valor': f"{capability_metrics['lsl']:.2f}"},
                {'Métrica': 'USL', 'Valor': f"{capability_metrics['usl']:.2f}"},
                {'Métrica': 'Média (x̄)', 'Valor': f"{capability_metrics['mean']:.2f}"},
                {'Métrica': 'Desvio padrão amostral (s)', 'Valor': f"{capability_metrics['std']:.4f}"},
                {'Métrica': 'CPU', 'Valor': f"{capability_metrics['cpu']:.4f}" if np.isfinite(capability_metrics['cpu']) else 'N/A'},
                {'Métrica': 'CPL', 'Valor': f"{capability_metrics['cpl']:.4f}" if np.isfinite(capability_metrics['cpl']) else 'N/A'},
                {'Métrica': 'Cpk', 'Valor': f"{capability_metrics['cpk']:.4f}"},
                {'Métrica': 'Nível Sigma (curto prazo = Cpk x 3)', 'Valor': f"{capability_metrics['sigma_short']:.3f}"},
                {'Métrica': 'Nível Sigma (longo prazo = Cpk x 3 - 1.5)', 'Valor': f"{capability_metrics['sigma_long']:.3f}"},
                {'Métrica': 'Interpretação', 'Valor': capability_metrics['quality']},
            ]

        capability_component = dash_table.DataTable(
            columns=[{"name": "Métrica", "id": "Métrica"}, {"name": "Valor", "id": "Valor"}],
            data=capability_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if capability_table_data else html.P(capability_msg or 'Sem dados para calcular Cpk e Nível Sigma.', style={'color': '#666'})

        lt_table_data = [{'Estatística': k, 'Valor': v} for k, v in lead_time_stats.items()]
        lt_table = dash_table.DataTable(
            columns=[{"name": "Estatística", "id": "Estatística"}, {"name": "Valor", "id": "Valor"}],
            data=lt_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if lt_table_data else html.P('Sem dados de Lead Time para o período selecionado.')

        # Gráficos de Lead Time
        fig_lt_hist = {}
        fig_lt_box = {}
        if not df_done_lt.empty:
            fig_lt_hist = px.histogram(df_done_lt, x=lead_col, nbins=30,
                                       title='Distribuição do Lead Time (dias)',
                                       labels={lead_col: 'Lead Time (dias)', 'count': 'Frequência'},
                                       height=500)
            lt_mean_val = lt_comparable_stats.get('mean', np.nan)
            lt_median_val = lt_comparable_stats.get('p50', np.nan)
            lt_p85_val = lt_comparable_stats.get('p85', np.nan)
            fig_lt_hist.add_vline(x=lt_mean_val, line_dash="dash", line_color="red", annotation_text=f"Média: {lt_mean_val:.1f}")
            fig_lt_hist.add_vline(x=lt_median_val, line_dash="dash", line_color="blue", annotation_text=f"Mediana: {lt_median_val:.1f}")
            fig_lt_hist.add_vline(x=lt_p85_val, line_dash="dash", line_color="orange", annotation_text=f"P85: {lt_p85_val:.1f}")

            fig_lt_box = px.box(df_done_lt, y=lead_col, title='Box Plot do Lead Time (dias)',
                                labels={lead_col: 'Lead Time (dias)'}, points='all', height=500)

        # --- 2. Estatísticas de Throughput (semanal) ---
        tp_weekly = df_done.dropna(subset=['DataDone']).copy()
        tp_weekly['Semana'] = weekly_bucket_start(tp_weekly['DataDone'])
        tp_weekly = tp_weekly.groupby('Semana').size().reset_index(name='Throughput')

        tp_stats = {}
        if not tp_weekly.empty:
            tp = tp_weekly['Throughput']
            tp_stats = {
                'Semanas Analisadas': int(len(tp)),
                'Total de Itens': int(tp.sum()),
                'Média / Semana': f"{tp.mean():.2f}",
                'Mediana / Semana': f"{tp.median():.2f}",
                'Desvio Padrão': f"{tp.std():.2f}",
                'Mínimo / Semana': int(tp.min()),
                'Máximo / Semana': int(tp.max()),
                'P25': f"{exact_empirical_percentile(tp, 0.25):.2f}",
                'P75': f"{exact_empirical_percentile(tp, 0.75):.2f}",
                'P85': f"{exact_empirical_percentile(tp, 0.85):.2f}",
                'P95': f"{exact_empirical_percentile(tp, 0.95):.2f}",
                'Coef. Variação (%)': f"{(tp.std() / tp.mean() * 100):.2f}" if tp.mean() > 0 else '—',
            }

        tp_table_data = [{'Estatística': k, 'Valor': str(v)} for k, v in tp_stats.items()]
        tp_table = dash_table.DataTable(
            columns=[{"name": "Estatística", "id": "Estatística"}, {"name": "Valor", "id": "Valor"}],
            data=tp_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if tp_table_data else html.P('Sem dados de Throughput para o período selecionado.')

        # Gráficos de Throughput
        fig_tp_hist = {}
        fig_tp_line = {}
        if not tp_weekly.empty:
            fig_tp_hist = px.histogram(tp_weekly, x='Throughput', nbins=15,
                                       title='Distribuição do Throughput Semanal',
                                       labels={'Throughput': 'Throughput (itens/semana)', 'count': 'Frequência'},
                                       height=500)
            tp_mean_val = tp_weekly['Throughput'].mean()
            fig_tp_hist.add_vline(x=tp_mean_val, line_dash="dash", line_color="red", annotation_text=f"Média: {tp_mean_val:.1f}")

            tp_weekly_sorted = tp_weekly.sort_values('Semana')
            fig_tp_line = px.bar(tp_weekly_sorted, x='Semana', y='Throughput',
                                 title='Throughput Semanal ao Longo do Tempo',
                                 labels={'Semana': 'Semana', 'Throughput': 'Itens Concluídos'},
                                 height=500)
            fig_tp_line.update_layout(xaxis_tickangle=-45, margin=dict(b=130))

        # --- 3. Estatísticas de WIP (semanal) ---
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        wip_weekly_values = []
        for week_end in weeks:
            wip_count = len(df_base[
                (df_base['DataInProgress'] <= week_end) &
                ((df_base['DataDone'] > week_end) | pd.isna(df_base['DataDone']))
            ])
            wip_weekly_values.append({'Semana': week_end, 'WIP': wip_count})
        wip_weekly_df = pd.DataFrame(wip_weekly_values)

        wip_stats = {}
        if not wip_weekly_df.empty and len(wip_weekly_df) > 0:
            w = wip_weekly_df['WIP']
            wip_stats = {
                'Semanas Analisadas': int(len(w)),
                'Média': f"{w.mean():.2f}",
                'Mediana': f"{w.median():.2f}",
                'Desvio Padrão': f"{w.std():.2f}",
                'Mínimo': int(w.min()),
                'Máximo': int(w.max()),
                'P25': f"{exact_empirical_percentile(w, 0.25):.2f}",
                'P75': f"{exact_empirical_percentile(w, 0.75):.2f}",
                'P85': f"{exact_empirical_percentile(w, 0.85):.2f}",
                'P95': f"{exact_empirical_percentile(w, 0.95):.2f}",
                'Coef. Variação (%)': f"{(w.std() / w.mean() * 100):.2f}" if w.mean() > 0 else '—',
                'WIP Atual (última semana)': int(w.iloc[-1]) if len(w) > 0 else '—',
            }

        wip_table_data = [{'Estatística': k, 'Valor': str(v)} for k, v in wip_stats.items()]
        wip_table = dash_table.DataTable(
            columns=[{"name": "Estatística", "id": "Estatística"}, {"name": "Valor", "id": "Valor"}],
            data=wip_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if wip_table_data else html.P('Sem dados de WIP para o período selecionado.')

        # Gráficos de WIP
        fig_wip_line = {}
        fig_wip_hist = {}
        if not wip_weekly_df.empty:
            fig_wip_line = px.line(wip_weekly_df, x='Semana', y='WIP',
                                   title='WIP Semanal ao Longo do Tempo', markers=True, height=500)
            fig_wip_line.update_layout(xaxis_tickangle=-45, margin=dict(b=130))
            fig_wip_hist = px.histogram(wip_weekly_df, x='WIP', nbins=15,
                                        title='Distribuição do WIP Semanal',
                                        labels={'WIP': 'WIP (itens)', 'count': 'Frequência'},
                                        height=500)

        # --- Layout da aba ---
        filtro_info = f"Projeto: {projeto or 'Todos'} | Tipo: {tipo or 'Todos'}"
        comparativo_lead_info = (
            f"Lead Time comparável à aba 'Lead Time' | "
            f"Amostra: {int(lt_comparable_stats.get('count', 0))} | "
            f"Média: {float(lt_comparable_stats.get('mean', np.nan)):.2f} | "
            f"P50: {float(lt_comparable_stats.get('p50', np.nan)):.2f} | "
            f"P85: {float(lt_comparable_stats.get('p85', np.nan)):.2f}"
            if lt_comparable_stats else
            "Lead Time comparável à aba 'Lead Time' | Sem amostra válida no recorte."
        )

        return html.Div([
            html.H3("Estatística Descritiva", style={'textAlign': 'center'}),
            html.P(filtro_info, style={'textAlign': 'center', 'color': '#666', 'marginBottom': '30px'}),
            html.P(comparativo_lead_info, style={'textAlign': 'center', 'color': '#666', 'marginTop': '-20px', 'marginBottom': '20px'}),

            # Cpk / Six Sigma
            html.H4("Capabilidade do Processo (Cpk e Nível Sigma)", style={'textAlign': 'center', 'marginTop': '20px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.P(
                "Informe os limites de especificação do cliente (LSL e USL) para calcular CPU, CPL, Cpk e nível sigma.",
                style={'textAlign': 'center', 'color': '#666', 'marginBottom': '14px'}
            ),
            html.Div([
                html.Div([
                    html.Label("LSL (Limite Inferior):", style={'fontWeight': 'bold'}),
                    dcc.Input(
                        id='estatistica-lsl',
                        type='number',
                        value=lsl_input_value,
                        debounce=True,
                        placeholder='Ex.: 9.7',
                        style={'width': '160px'}
                    ),
                ], style={'display': 'inline-flex', 'alignItems': 'center', 'gap': '8px', 'marginRight': '20px'}),
                html.Div([
                    html.Label("USL (Limite Superior):", style={'fontWeight': 'bold'}),
                    dcc.Input(
                        id='estatistica-usl',
                        type='number',
                        value=usl_input_value,
                        debounce=True,
                        placeholder='Ex.: 10.3',
                        style={'width': '160px'}
                    ),
                ], style={'display': 'inline-flex', 'alignItems': 'center', 'gap': '8px'}),
            ], style={'textAlign': 'center', 'marginBottom': '14px'}),
            html.Div(capability_component, style={'width': '60%', 'margin': '0 auto'}),
            html.P(
                "Premissa: distribuição aproximadamente normal. Para processo não normal ou dados binários, use abordagem específica por yield/PPM.",
                style={'textAlign': 'center', 'color': '#666', 'fontSize': '12px', 'marginTop': '10px'}
            ),

            # Lead Time
            html.H4("Lead Time (dias)", style={'textAlign': 'center', 'marginTop': '30px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.Div([
                html.Div(lt_table, className='five columns', style={'padding': '10px'}),
                html.Div([
                    dcc.Graph(figure=fig_lt_hist),
                    dcc.Graph(figure=fig_lt_box),
                ], className='seven columns'),
            ], className='row'),

            # Throughput
            html.H4("Throughput (semanal)", style={'textAlign': 'center', 'marginTop': '40px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.Div([
                html.Div(tp_table, className='five columns', style={'padding': '10px'}),
                html.Div([
                    dcc.Graph(figure=fig_tp_hist),
                    dcc.Graph(figure=fig_tp_line),
                ], className='seven columns'),
            ], className='row'),

            # WIP
            html.H4("WIP - Work in Progress (semanal)", style={'textAlign': 'center', 'marginTop': '40px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.Div([
                html.Div(wip_table, className='five columns', style={'padding': '10px'}),
                html.Div([
                    dcc.Graph(figure=fig_wip_line),
                    dcc.Graph(figure=fig_wip_hist),
                ], className='seven columns'),
            ], className='row'),
        ])

    if tab == 'tab-fila-capacidade':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        # Base para cálculo de capacidade com as mesmas regras do One Page:
        # chegada por LeadStart_Selected e vazão por itens concluídos elegíveis.
        df_capacity_base = fato.copy()
        if projeto:
            df_capacity_base = df_capacity_base[df_capacity_base['Projeto'] == projeto]
        if tipo:
            df_capacity_base = df_capacity_base[df_capacity_base['TipoDemanda'] == tipo]
        if responsavel:
            df_capacity_base = df_capacity_base[df_capacity_base['Responsavel'] == responsavel]
        if classe_servico:
            df_capacity_base = df_capacity_base[df_capacity_base['ClasseServico'] == classe_servico]
        df_capacity_base, _ = apply_selected_lead_time_metric(df_capacity_base, projeto, leadtime_stages)

        lead_start_col = 'LeadStart_Selected' if 'LeadStart_Selected' in df_capacity_base.columns else 'DataInProgress'
        lead_start_series = pd.to_datetime(df_capacity_base.get(lead_start_col), errors='coerce')
        done_series = pd.to_datetime(df_capacity_base.get('DataDone'), errors='coerce')
        done_eligible_mask = done_time_eligible_mask(df_capacity_base)

        weeks = pd.date_range(start=start_date_ts, end=end_date_ts + pd.Timedelta(days=7), freq='W-MON')
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal de capacidade de fila.')

        weekly_rows = []
        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]
            arrivals = int(((lead_start_series >= week_start) & (lead_start_series < week_end)).sum())
            throughput = int(((done_series >= week_start) & (done_series < week_end) & done_eligible_mask).sum())
            weekly_rows.append({
                'Semana': str(week_start.date()),
                'Chegadas': arrivals,
                'Throughput': throughput,
            })

        weekly_df = pd.DataFrame(weekly_rows)
        n_weeks = len(weekly_df)
        lambda_base = weekly_df['Chegadas'].mean() if n_weeks > 0 else 0.0
        mu = weekly_df['Throughput'].mean() if n_weeks > 0 else 0.0
        lambda_stress = lambda_base * 1.18

        if mu <= 0:
            return html.Div('Não há throughput suficiente no período para calcular capacidade de fila (μ = 0).')

        base = calculate_mm1_metrics(lambda_base, mu)
        stress = calculate_mm1_metrics(lambda_stress, mu)
        if base is None or stress is None:
            return html.Div('Não foi possível calcular métricas de fila com os dados selecionados.')

        lq_growth_pct = ((stress['Lq'] - base['Lq']) / base['Lq']) * 100 if np.isfinite(base['Lq']) and base['Lq'] > 0 else np.nan
        w_growth_pct = ((stress['W'] - base['W']) / base['W']) * 100 if np.isfinite(base['W']) and base['W'] > 0 else np.nan
        arrival_growth_pct = ((lambda_stress - lambda_base) / lambda_base) * 100 if lambda_base > 0 else np.nan

        def fmt_metric_value(value, unit=''):
            if value is None or (isinstance(value, float) and not np.isfinite(value)):
                return 'Sistema instável (ρ >= 1)'
            return f"{value:.2f}{unit}"

        period_label = f"{start_date_ts.date()} a {end_date_ts.date()}"
        _, efficiency = calculate_flow_efficiency(base['lambda'], base['mu'])
        kpi_data = [
            {'Métrica': 'Período analisado', 'Valor': period_label},
            {'Métrica': 'Semanas analisadas', 'Valor': f"{n_weeks}"},
            {'Métrica': 'Taxa de chegada média (λ)', 'Valor': f"{base['lambda']:.2f} tarefas/semana"},
            {'Métrica': 'Taxa de vazão média (μ)', 'Valor': f"{base['mu']:.2f} tarefas/semana"},
            {'Métrica': 'Utilização (ρ)', 'Valor': fmt_metric_value(base['rho'])},
            {'Métrica': 'Eficiência (1 - ρ)', 'Valor': fmt_metric_value(efficiency)},
            {'Métrica': 'Lq - fila média', 'Valor': fmt_metric_value(base['Lq'], ' tarefas')},
            {'Métrica': 'Wq - espera média na fila', 'Valor': fmt_metric_value(base['Wq'], ' semanas')},
            {'Métrica': 'W - tempo total no sistema', 'Valor': fmt_metric_value(base['W'], ' semanas')},
            {'Métrica': 'Cenário de estresse (+18% em λ)', 'Valor': f"{arrival_growth_pct:.1f}%"},
            {'Métrica': 'Lq no estresse', 'Valor': fmt_metric_value(stress['Lq'], ' tarefas')},
            {'Métrica': 'W no estresse', 'Valor': fmt_metric_value(stress['W'], ' semanas')},
            {'Métrica': 'Aumento de fila (Lq)', 'Valor': f"{lq_growth_pct:.0f}%" if np.isfinite(lq_growth_pct) else 'N/A'},
            {'Métrica': 'Aumento de tempo total (W)', 'Valor': f"{w_growth_pct:.0f}%" if np.isfinite(w_growth_pct) else 'N/A'},
        ]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        scenario_df = pd.DataFrame([
            {
                'Cenário': 'Base',
                'λ': base['lambda'],
                'μ': base['mu'],
                'ρ': round(base['rho'], 2),
                'Lq (tarefas)': round(base['Lq'], 2) if np.isfinite(base['Lq']) else 'Instável',
                'Wq (semanas)': round(base['Wq'], 2) if np.isfinite(base['Wq']) else 'Instável',
                'W (semanas)': round(base['W'], 2) if np.isfinite(base['W']) else 'Instável',
            },
            {
                'Cenário': 'Aumento de demanda (+18%)',
                'λ': stress['lambda'],
                'μ': stress['mu'],
                'ρ': round(stress['rho'], 2),
                'Lq (tarefas)': round(stress['Lq'], 2) if np.isfinite(stress['Lq']) else 'Instável',
                'Wq (semanas)': round(stress['Wq'], 2) if np.isfinite(stress['Wq']) else 'Instável',
                'W (semanas)': round(stress['W'], 2) if np.isfinite(stress['W']) else 'Instável',
            },
        ])
        scenario_table = dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in scenario_df.columns],
            data=scenario_df.to_dict('records'),
            style_cell={'textAlign': 'center', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        )

        rho_series = np.linspace(0.50, 0.98, 49)
        lambda_series = rho_series * mu
        lq_series = (rho_series ** 2) / (1 - rho_series)
        w_series = (lq_series / lambda_series) + (1 / mu)

        fig_queue = make_subplots(specs=[[{"secondary_y": True}]])
        fig_queue.add_trace(
            go.Scatter(x=rho_series, y=w_series, mode='lines', name='W - Tempo total (semanas)', line=dict(color='royalblue', width=3)),
            secondary_y=False
        )
        fig_queue.add_trace(
            go.Scatter(x=rho_series, y=lq_series, mode='lines', name='Lq - Fila média (tarefas)', line=dict(color='firebrick', width=3)),
            secondary_y=True
        )
        fig_queue.add_vline(x=0.8, line_dash='dash', line_color='orange')
        fig_queue.add_vline(x=0.9, line_dash='dash', line_color='red')
        fig_queue.add_annotation(x=0.72, y=max(w_series) * 0.15, text='Baixa utilização (ρ < 0.8)', showarrow=False)
        fig_queue.add_annotation(x=0.84, y=max(w_series) * 0.35, text='Intermediária (ρ = 0.8)', showarrow=False)
        fig_queue.add_annotation(x=0.93, y=max(w_series) * 0.70, text='Alta utilização (ρ > 0.9)', showarrow=False)
        fig_queue.update_layout(
            title='Sensibilidade do Sistema à Utilização (Modelo M/M/1)',
            height=580,
            template='plotly_white',
            xaxis_title='Taxa de Utilização (ρ)',
            margin=dict(t=60, b=50),
        )
        fig_queue.update_yaxes(title_text='W - Tempo total no sistema (semanas)', secondary_y=False)
        fig_queue.update_yaxes(title_text='Lq - Comprimento médio da fila (tarefas)', secondary_y=True)

        insight_block = html.Div([
            html.H4("Mensagem de Gestão", style={'marginBottom': '10px'}),
            html.P('"Ah, é só mais uma demanda..." parece pequeno, mas o impacto é exponencial quando ρ se aproxima de 1.'),
            html.P('Associe custo financeiro às demandas na fila para evidenciar o custo de atraso no sistema.'),
        ], style={'padding': '14px', 'backgroundColor': '#f9f9f9', 'border': '1px solid #e0e0e0', 'borderRadius': '8px'})

        return html.Div([
            html.H3("Capacidade de Fila e Impacto de Utilização", style={'textAlign': 'center'}),
            html.P("Modelo M/M/1 com taxas calculadas a partir dos dados importados e filtros ativos.",
                   style={'textAlign': 'center', 'color': '#666'}),
            html.Div(kpi_table, style={'width': '62%', 'margin': '20px auto'}),
            html.H4("Comparação de Cenários", style={'textAlign': 'center', 'marginTop': '24px'}),
            scenario_table,
            dcc.Graph(figure=fig_queue),
            insight_block,
        ])

    return html.Div('Aba não encontrada')


@app.callback(
    Output('performance-metric-chart', 'children'),
    Input('performance-table', 'active_cell'),
    Input('performance-table', 'data'),
    prevent_initial_call=True
)
def render_metric_chart(active_cell, table_data):
    if not active_cell or not table_data:
        return html.Div()

    row_idx = active_cell['row']
    row = table_data[row_idx]
    metric_name = row['Métrica']

    # Extrair semanas (colunas exceto 'Métrica') e valores numéricos
    week_labels = [col for col in row.keys() if col != 'Métrica']

    # Para Demanda de Valor/Falha, exibe comparativo em colunas sobrepostas.
    if metric_name in ['% Demanda de Valor', '% Demanda de Falha']:
        row_valor = next((r for r in table_data if r.get('Métrica') == '% Demanda de Valor'), None)
        row_falha = next((r for r in table_data if r.get('Métrica') == '% Demanda de Falha'), None)

        if row_valor and row_falha:
            weeks_cmp = []
            vals_valor = []
            vals_falha = []

            for wl in week_labels:
                raw_valor = str(row_valor.get(wl, '')).replace('%', '').replace(',', '.').strip()
                raw_falha = str(row_falha.get(wl, '')).replace('%', '').replace(',', '.').strip()
                try:
                    num_valor = float(raw_valor)
                    num_falha = float(raw_falha)
                    weeks_cmp.append(wl)
                    vals_valor.append(num_valor)
                    vals_falha.append(num_falha)
                except (ValueError, TypeError):
                    continue

            if weeks_cmp:
                fig_cmp = go.Figure()
                fig_cmp.add_trace(go.Bar(
                    x=weeks_cmp,
                    y=vals_valor,
                    name='Demanda de Valor',
                    marker_color='green',
                    opacity=0.85
                ))
                fig_cmp.add_trace(go.Bar(
                    x=weeks_cmp,
                    y=vals_falha,
                    name='Demanda de Falha',
                    marker_color='red',
                    opacity=0.85
                ))
                fig_cmp.update_layout(
                    title='Demanda de Falha x Demanda de Valor',
                    xaxis_title='Semana',
                    yaxis_title='Percentual (%)',
                    template='plotly_white',
                    height=550,
                    margin=dict(t=60, b=130),
                    xaxis_tickangle=-45,
                    barmode='overlay',
                    legend_title_text='Valores'
                )

                return html.Div([
                    dcc.Graph(figure=fig_cmp)
                ], style={'marginTop': '20px'})

    def _parse_metric_numeric_value(raw_value, metric):
        txt = str(raw_value or '').strip().lower().replace(',', '.')
        if not txt or txt in {'—', '-', 'nan', 'none'}:
            return None
        if metric == 'Lead time para mudanças':
            if txt.endswith('h'):
                try:
                    return float(txt[:-1].strip()) / 24.0
                except (ValueError, TypeError):
                    return None
            if txt.endswith('d'):
                try:
                    return float(txt[:-1].strip())
                except (ValueError, TypeError):
                    return None
        txt = txt.replace('%', '').strip()
        try:
            return float(txt)
        except (ValueError, TypeError):
            return None

    values = []
    for wl in week_labels:
        values.append(_parse_metric_numeric_value(row.get(wl), metric_name))

    # Filtrar semanas com valores válidos
    valid = [(w, v) for w, v in zip(week_labels, values) if v is not None]
    if not valid:
        return html.Div(
            f'A métrica "{metric_name}" não possui dados numéricos para exibir.',
            style={'textAlign': 'center', 'padding': '20px', 'color': '#999'}
        )

    weeks_valid, vals_valid = zip(*valid)
    weeks_valid = list(weeks_valid)
    vals_valid = list(vals_valid)

    # Criar gráfico de linha
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weeks_valid, y=vals_valid,
        mode='lines+markers', name=metric_name,
        line=dict(width=2.5, color='#0074D9'),
        marker=dict(size=8)
    ))

    # Adicionar linhas de percentis
    s = pd.Series(vals_valid)
    if len(s) >= 2:
        add_statistical_lines(fig, weeks_valid, s)

    yaxis_title = metric_name
    if metric_name == 'Lead time para mudanças':
        yaxis_title = 'Lead time para mudanças (dias)'

    fig.update_layout(
        title=f'{metric_name} — Tendência Semanal',
        xaxis_title='Semana',
        yaxis_title=yaxis_title,
        template='plotly_white',
        height=550,
        margin=dict(t=60, b=130),
        xaxis_tickangle=-45,
    )

    return html.Div([
        dcc.Graph(figure=fig)
    ], style={'marginTop': '20px'})


def create_table(df, table_id='table-main', title='Tabela'):
    if df is None or getattr(df, 'empty', True):
        return html.Div('Sem dados para exibir')
    return html.Div([html.H3(title), dash_table.DataTable(id=table_id, columns=[{'name':c,'id':c} for c in df.columns], data=df.head(200).to_dict('records'), page_size=20, style_table={'overflowX':'auto'})])

def create_generic_datatable(df, table_id, title):
    return create_table(df, table_id=table_id, title=title)


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


@app.callback(
    Output('cfd-summary-panel', 'children'),
    optional_input('cfd-graph', 'clickData'),
    optional_input('cfd-graph', 'hoverData'),
    Input('cfd-summary-store', 'data'),
)
def update_cfd_summary_panel(click_data, hover_data, summary_payload):
    if not summary_payload:
        raise PreventUpdate

    selected_date = None
    source = click_data or hover_data
    try:
        points = (source or {}).get('points') or []
        if points:
            selected_date = points[0].get('x')
    except Exception:
        selected_date = None

    return create_cfd_summary_panel(summary_payload, selected_date=selected_date)

if __name__ == '__main__':
    app.run(**_resolve_dash_runtime_options())
