import dash
from dash import dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
import os
import json
import numpy as np
import math
import hashlib
import urllib.request
import urllib.parse
import re
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Config ---
import platform
if platform.system() == 'Windows':
    LEGACY_DATA_FOLDER = r'C:\Users\W1 TI\OneDrive - W1\Documentos\Dados'
else:
    LEGACY_DATA_FOLDER = os.path.join(os.path.expanduser('~'), 'Library', 'CloudStorage', 'OneDrive-W1', 'Documentos', 'Dados')


def _existing_dirs(paths):
    out = []
    seen = set()
    for raw in paths:
        if not raw:
            continue
        p = os.path.abspath(raw.strip())
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
    home_dir = os.path.expanduser('~')
    return _existing_dirs([
        explicit_dir,
        legacy_override,
        *split_env_dirs,
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
    if not os.path.exists(out_file):
        urllib.request.urlretrieve(url, out_file)
    return out_file


def _download_portfolio_csv_from_url(url):
    cache_dir = '/tmp/flow-pmo-models'
    os.makedirs(cache_dir, exist_ok=True)
    file_key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    out_file = os.path.join(cache_dir, f'portfolio-bt-ns-{file_key}-data.csv')
    if not os.path.exists(out_file):
        urllib.request.urlretrieve(url, out_file)
    return out_file


def _download_bottleneck_csv_from_url(url, project_key):
    cache_dir = '/tmp/flow-pmo-models'
    os.makedirs(cache_dir, exist_ok=True)
    safe_project = ''.join(ch for ch in str(project_key or '').lower() if ch.isalnum()) or 'project'
    file_key = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    out_file = os.path.join(cache_dir, f'{safe_project}-{file_key}-data_bottlenecks.csv')
    if not os.path.exists(out_file):
        urllib.request.urlretrieve(url, out_file)
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


def _url_filename_matches_project(url, expected_prefix):
    """Validate if URL filename seems to belong to the expected project prefix."""
    if not url or not expected_prefix:
        return False
    parsed = urllib.parse.urlparse(str(url).strip())
    filename = os.path.basename(parsed.path or '').lower()
    prefix = str(expected_prefix).strip().lower()
    return filename.startswith(prefix) and filename.endswith('-data_bottlenecks.csv')


def _resolve_model_file(data_folders):
    explicit_model = os.getenv('FLOW_PMO_MODEL_FILE', '').strip()
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
            return prioridade_text

    if classe_text and classe_text.lower() != 'nan':
        return classe_text
    return 'Standard'
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

# App
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'], suppress_callback_exceptions=True)
app.title = 'Dashboard de Métricas (Full)'

PROJECT_BOTTLENECK_PREFIX = {
    'W1NNER': 'w1nner-downstream',
    'S1NC': 's1nc-downstream',
    'BEFINANCE': 'befinance-downstream',
    'DATA&ANALYTICS': 'dataanalytics-downstream',
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
PORTFOLIO_CACHE = {'fetched_at': None, 'data': None, 'error': None}
PORTFOLIO_CSV_PREFIX = 'portfolio-bt-ns-'
PORTFOLIO_TAB_VALUE = 'tab-portfolio'
SERVICE_TABS = [
    ('Performance do Serviço', 'tab-performance'),
    ('Painel Fluxo', 'tab-painel-3x3'),
    ('Lead Time', 'tab-lead-time'),
    ('Fluxo', 'tab-fluxo'),
    ('CFD', 'tab-cfd'),
    ('Saúde do Fluxo', 'tab-saude'),
    ('Análise Fluxo', 'tab-analise-fluxo'),
    ('Tendências', 'tab-tendencias'),
    ('Throughput Breakdown', 'tab-throughput-breakdown'),
    ('Padrões Sistêmicos', 'tab-padroes'),
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
PORTFOLIO_COLOR_THRESHOLDS = {
    'Q1 Pendências': {'green_max': 2, 'yellow_max': 8},
    'Q2 Pendências': {'green_max': 1, 'yellow_max': 5},
    'Q3 Pendências': {'green_max': 0, 'yellow_max': 3},
    'aging_us_20': {'green_max': 0, 'yellow_max': 5},
    'aging_features_40': {'green_max': 0, 'yellow_max': 8},
    'aging_us_comp_20': {'green_max': 0, 'yellow_max': 5},
    'aging_features_comp_40': {'green_max': 0, 'yellow_max': 8},
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


def _safe_ratio(num, den):
    if den is None or den == 0:
        return np.nan
    return float(num) / float(den)


def _safe_pct(num, den):
    if den is None or den == 0:
        return 0.0
    return float(num) / float(den) * 100.0


def detect_systemic_patterns(df_source, start_ts, end_ts, rules):
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
        return pd.DataFrame(), pd.DataFrame()

    for i in range(len(weeks) - 1):
        week_start = weeks[i]
        week_end = weeks[i + 1]
        arrivals = df_source[(df_source['DataInProgress'] >= week_start) & (df_source['DataInProgress'] < week_end)]
        done = df_source[(df_source['DataDone'] >= week_start) & (df_source['DataDone'] < week_end)]
        wip = df_source[(df_source['DataInProgress'] < week_end) & ((df_source['DataDone'] >= week_end) | pd.isna(df_source['DataDone']))]

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
        return pd.DataFrame(), pd.DataFrame()
    summary = (
        details.groupby(['Padrão', 'Severidade'], as_index=False)
        .size()
        .rename(columns={'size': 'Ocorrências'})
        .sort_values('Ocorrências', ascending=False)
    )
    return details, summary


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
            'metrics': {'epics_sem_features': 0, 'features_sem_epico': 0, 'features_sem_filhos': 0, 'features_sem_mov_15': 0, 'features_sem_mov_30': 0},
            'groups': {
                'epicos_por_team_status': pd.DataFrame(),
                'features_por_team_status': pd.DataFrame(),
                'epicos_por_complexidade': pd.DataFrame(),
                'features_por_complexidade': pd.DataFrame(),
                'epicos_fluxo_etapas': pd.DataFrame(),
                'epicos_por_team_total': pd.DataFrame(),
                'features_por_team_total': pd.DataFrame(),
                'pendencias_q_por_time': pd.DataFrame(),
                'aging_us_20': pd.DataFrame(),
                'aging_features_40': pd.DataFrame(),
                'aging_us_comp_20': pd.DataFrame(),
                'aging_features_comp_40': pd.DataFrame(),
                'executive_tiles': pd.DataFrame(),
                'epicos_detalhe': pd.DataFrame(),
                'features_detalhe': pd.DataFrame(),
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
    if 'Team' not in df.columns:
        df['Team'] = ''

    df['Projeto'] = df['Projeto'].fillna('').astype(str)
    df['Team'] = df['Team'].fillna('').astype(str).str.strip()
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
    # Fallback: se a taxonomia de status vier fora do dicionário, considera "aberto e não backlog" como em processo.
    if not bool(is_in_progress.any()):
        is_in_progress = (~is_done) & (~is_backlog)
    is_open = (~is_done)

    df['IsOpen'] = is_open
    df['IsInProgress'] = is_in_progress
    df['IsBacklog'] = is_backlog

    user_story_types = {'story', 'user story', 'historia', 'historia de usuario', 'us'}
    df['IsUS'] = df['TipoNorm'].isin(user_story_types)
    df['IsFeature'] = df['TipoNorm'].isin(feature_types)

    # Q1/Q2/Q3 Pendências (faixas de aging em aberto, por TEAM/projeto agrupado).
    pendencias = df[df['IsOpen']].copy()
    pendencias['Quadrante'] = 'Q1 Pendências'
    pendencias.loc[pendencias['AgingDiasSemAlteracao'] > 15, 'Quadrante'] = 'Q2 Pendências'
    pendencias.loc[pendencias['AgingDiasSemAlteracao'] > 30, 'Quadrante'] = 'Q3 Pendências'
    pendencias_q_por_time = (
        group_count(pendencias, ['Quadrante', 'TeamDisplay'], 'WorkItems')
        .rename(columns={'TeamDisplay': 'Team'})
    )

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
    epics_sem_features = epics[epics['QtdFeatures'] == 0].copy()

    epicos_por_team_status = group_count(epics, ['TeamDisplay', 'Status'], 'QtdEpicos').rename(columns={'TeamDisplay': 'Team'})
    features_por_team_status = group_count(features, ['TeamDisplay', 'Status'], 'QtdFeatures').rename(columns={'TeamDisplay': 'Team'})
    epicos_por_complexidade = group_count(epics, ['TeamDisplay', 'Complexidade'], 'QtdEpicos').rename(columns={'TeamDisplay': 'Team'})
    features_por_complexidade = group_count(features, ['TeamDisplay', 'Complexidade'], 'QtdFeatures').rename(columns={'TeamDisplay': 'Team'})
    epicos_por_team_total = group_count(epics, ['TeamDisplay'], 'QtdEpicos').rename(columns={'TeamDisplay': 'Team'})
    features_por_team_total = group_count(features, ['TeamDisplay'], 'QtdFeatures').rename(columns={'TeamDisplay': 'Team'})

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
    epic_title_map = epics.set_index('ID')['Titulo'] if not epics.empty else pd.Series(dtype='object')
    features['EpicTitulo'] = features['EpicID'].map(epic_title_map).fillna('')
    features['DiasSemMovimentacao'] = (
        (now_utc - features['UltimaMovimentacao']).dt.days
        if 'UltimaMovimentacao' in features.columns else np.nan
    )
    epicos_detalhe = (
        epics[['TeamDisplay', 'ID', 'Titulo', 'Status', 'Complexidade', 'QtdFeatures', 'QtdItensFluxo', 'Link']]
        .rename(columns={'TeamDisplay': 'Team', 'ID': 'EpicID'})
        .sort_values(['Team', 'QtdItensFluxo', 'QtdFeatures'], ascending=[True, False, False], ignore_index=True)
    )
    features_detalhe = (
        features[['TeamDisplay', 'ID', 'Titulo', 'Status', 'Complexidade', 'EpicID', 'EpicTitulo', 'QtdFilhos', 'DiasSemMovimentacao', 'Link']]
        .rename(columns={'TeamDisplay': 'Team', 'ID': 'FeatureID'})
        .sort_values(['Team', 'QtdFilhos', 'DiasSemMovimentacao'], ascending=[True, False, False], ignore_index=True)
    )

    # Cards executivos no estilo "mosaico".
    sem_team = int((df['Team'].str.strip() == '').sum())
    em_dia = int(((df['IsOpen']) & (df['AgingDiasSemAlteracao'] <= 15)).sum())
    atrasadas = int(((df['IsOpen']) & (df['AgingDiasSemAlteracao'] > 30)).sum())
    divergente = int(len(features_sem_epico) + len(epics_sem_features))
    executive_tiles = pd.DataFrame([
        {'Indicador': 'Épicos', 'Valor': int(len(epics)), 'Tipo': 'ok'},
        {'Indicador': 'Features', 'Valor': int(len(features)), 'Tipo': 'ok'},
        {'Indicador': 'Sem TEAM', 'Valor': sem_team, 'Tipo': 'risco'},
        {'Indicador': 'Em dia', 'Valor': em_dia, 'Tipo': 'ok'},
        {'Indicador': 'Atrasadas', 'Valor': atrasadas, 'Tipo': 'risco'},
        {'Indicador': 'Estado divergente', 'Valor': divergente, 'Tipo': 'alerta'},
        {'Indicador': 'Features sem épico', 'Valor': int(len(features_sem_epico)), 'Tipo': 'alerta'},
        {'Indicador': 'Épicos sem features', 'Valor': int(len(epics_sem_features)), 'Tipo': 'alerta'},
    ])

    return {
        'updated_at': updated_at_label,
        'metrics': {
            'epics_sem_features': int(len(epics_sem_features)),
            'features_sem_epico': int(len(features_sem_epico)),
            'features_sem_filhos': int(len(features_sem_filhos)),
            'features_sem_mov_15': int(len(features_sem_mov_15)),
            'features_sem_mov_30': int(len(features_sem_mov_30)),
            'total_epicos': int(len(epics)),
            'total_features': int(len(features)),
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
            'aging_us_20': aging_us_20,
            'aging_features_40': aging_features_40,
            'aging_us_comp_20': aging_us_comp_20,
            'aging_features_comp_40': aging_features_comp_40,
            'executive_tiles': executive_tiles,
            'epicos_detalhe': epicos_detalhe,
            'features_detalhe': features_detalhe,
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
    if cached_at and (now - cached_at) <= PORTFOLIO_CACHE_TTL and PORTFOLIO_CACHE.get('data') is not None:
        return PORTFOLIO_CACHE.get('data'), PORTFOLIO_CACHE.get('error')
    try:
        payload = build_portfolio_snapshot_from_csv()
        PORTFOLIO_CACHE['fetched_at'] = now
        PORTFOLIO_CACHE['data'] = payload
        PORTFOLIO_CACHE['error'] = None
        return payload, None
    except Exception as exc:
        PORTFOLIO_CACHE['fetched_at'] = now
        PORTFOLIO_CACHE['data'] = None
        PORTFOLIO_CACHE['error'] = str(exc)
        return None, str(exc)

def get_portfolio_team_filter_options():
    default_options = [{'label': 'Todos os Teams', 'value': '__ALL__'}]
    snapshot, error = get_portfolio_snapshot()
    if error or not snapshot:
        return default_options

    groups = snapshot.get('groups', {})
    frames = [
        groups.get('epicos_por_team_total', pd.DataFrame()),
        groups.get('features_por_team_total', pd.DataFrame()),
    ]
    teams = set()
    for frame in frames:
        if frame is None or frame.empty or 'Team' not in frame.columns:
            continue
        for team in frame['Team'].dropna().astype(str):
            t = team.strip()
            if t:
                teams.add(t)

    for team in sorted(teams):
        default_options.append({'label': team, 'value': team})
    return default_options


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

def create_kpi_card(title, value, class_name='six columns'):
    return html.Div([
        html.H4(title, style={'textAlign': 'center'}),
        html.H2(value, style={'textAlign': 'center'})
    ], className=class_name)

def unique_sorted(col):
    return sorted([x for x in col.dropna().unique()])

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

    weekly_points = pd.date_range(start=start_point, end=end_point, freq=WEEK_DATE_RANGE_FREQ)
    snapshots = pd.DatetimeIndex(sorted(set([start_point, end_point, *list(weekly_points)])))
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
    for stage in ['Pronto', 'Em Progresso', 'Backlog']:
        stage_color = macro_colors[stage]
        raw_col = macro_raw_map[stage]
        trace = go.Scatter(
            x=df_cfd['Data'],
            y=df_cfd[raw_col],
            mode='lines',
            name=stage,
            line=dict(width=1.8, color=stage_color),
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
                line=dict(width=1.35, color=line_color),
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
                            {'annotations': [{
                                'text': 'Macro (exato): usa datas reais de Backlog / Em Progresso / Pronto.',
                                'xref': 'paper', 'yref': 'paper', 'x': 0, 'y': 1.15,
                                'showarrow': False, 'align': 'left', 'font': {'size': 11, 'color': '#555'}
                            }]}
                        ]
                    },
                    {
                        'label': 'Detalhado por Etapas (exato)',
                        'method': 'update',
                        'args': [
                            {'visible': detailed_visible},
                            {'annotations': [{
                                'text': 'Detalhado (exato): usa datas por etapa do CSV downstream do projeto.',
                                'xref': 'paper', 'yref': 'paper', 'x': 0, 'y': 1.15,
                                'showarrow': False, 'align': 'left', 'font': {'size': 11, 'color': '#555'}
                            }]}
                        ]
                    },
                ],
            }],
            annotations=[{
                'text': 'Macro (exato): usa datas reais de Backlog / Em Progresso / Pronto.',
                'xref': 'paper', 'yref': 'paper', 'x': 0, 'y': 1.15,
                'showarrow': False, 'align': 'left', 'font': {'size': 11, 'color': '#555'}
            }],
        )
    else:
        fig.update_layout(
            annotations=[{
                'text': 'Modo detalhado indisponível: selecione um projeto com CSV downstream (`*-data.csv`) contendo datas por etapa.',
                'xref': 'paper', 'yref': 'paper', 'x': 0, 'y': 1.15,
                'showarrow': False, 'align': 'left', 'font': {'size': 11, 'color': '#777'}
            }]
        )
    return fig


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
    prefix = PROJECT_BOTTLENECK_PREFIX.get(project_key)
    if not prefix:
        return pd.DataFrame()

    files = []
    for folder in DATA_FOLDERS:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            if not (name.startswith(prefix) and name.endswith('-data.csv')):
                continue
            if name.endswith('-data_bottlenecks.csv'):
                continue
            files.append(os.path.join(folder, name))

    files = [path for path in files if os.path.isfile(path)]
    if not files:
        return pd.DataFrame()

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


def apply_selected_lead_time_metric(df, projeto, selected_start_stages):
    """Attach lead time metric based on selected downstream stages to the filtered dataframe."""
    if df is None or getattr(df, 'empty', True):
        return df, {'enabled': False, 'sample': 0, 'stage_count': 0}
    if not projeto or 'ItemID' not in df.columns:
        out = df.copy()
        out['LeadTime_Selected_Dias'] = pd.to_numeric(out.get('LeadTime_Dias'), errors='coerce')
        out['LeadStart_Selected'] = pd.to_datetime(out.get('DataBacklog'), errors='coerce')
        return out, {'enabled': False, 'sample': int(out['LeadTime_Selected_Dias'].notna().sum()), 'stage_count': 0}

    lead_map = build_custom_lead_time_by_selected_stages(projeto, selected_start_stages)
    out = df.copy()
    if lead_map.empty:
        out['LeadTime_Selected_Dias'] = pd.to_numeric(out.get('LeadTime_Dias'), errors='coerce')
        out['LeadStart_Selected'] = pd.to_datetime(out.get('DataBacklog'), errors='coerce')
        return out, {'enabled': False, 'sample': int(out['LeadTime_Selected_Dias'].notna().sum()), 'stage_count': 0}

    out['ItemID'] = out['ItemID'].astype(str)
    out = out.merge(lead_map, how='left', on='ItemID')
    out['LeadTime_Selected_Dias'] = pd.to_numeric(out['LeadTime_Custom_Dias'], errors='coerce')
    out['LeadStart_Selected'] = pd.to_datetime(out['LeadStart_Custom'], errors='coerce')
    out.drop(columns=['LeadTime_Custom_Dias'], inplace=True, errors='ignore')
    out.drop(columns=['LeadStart_Custom'], inplace=True, errors='ignore')
    return out, {
        'enabled': True,
        'sample': int(out['LeadTime_Selected_Dias'].notna().sum()),
        'stage_count': len(selected_start_stages or []),
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
        footer_note = "Etapas carregadas de gargalos/modelo; cálculo usa fallback do modelo sem CSV downstream"
    elif not stage_cols:
        footer_note = "CSV downstream do projeto não encontrado; usando coluna do modelo"

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

def compute_weekly_service_metrics(df_projeto, weeks, lead_time_col='LeadTime_Dias'):
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
        'Taxa de demanda de falha',
        'MTTR',
    ]
    rows = {m: {} for m in metric_names}

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
        mttr_series = time_metric_series(
            finished_eligible[finished_eligible['TipoDemanda'] == TYPE_ISSUES] if tp_def > 0 else finished_eligible.iloc[0:0],
            lead_time_col,
            non_negative=True
        )
        mttr = mttr_series.mean() if not mttr_series.empty else np.nan
        if pd.isna(mttr):
            mttr = 0

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
        rows['Frequência de Deploy'][week_label] = str(tp_dev)
        rows['Lead time para mudanças'][week_label] = f"{avg_lt:.0f}" if pd.notna(avg_lt) else '—'
        rows['Taxa de demanda de falha'][week_label] = f"{tp_def / tp_total * 100:.1f}%" if tp_total > 0 else '—'
        rows['MTTR'][week_label] = f"{mttr:.0f}" if pd.notna(mttr) else '—'

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
                    'Porfólio',
                    id='btn-menu-portfolio',
                    n_clicks=0,
                    style={
                        'padding': '14px 20px',
                        'fontWeight': 'bold',
                        'borderRadius': '10px',
                        'border': '1px solid #0b5cab',
                        'backgroundColor': '#e9f2ff',
                        'color': '#0b3d75',
                        'cursor': 'pointer',
                        'minWidth': '240px',
                        'textAlign': 'center',
                    }
                ),
                html.Button(
                    'Serviços (Value Stream)',
                    id='btn-menu-services',
                    n_clicks=0,
                    style={
                        'padding': '14px 20px',
                        'fontWeight': 'bold',
                        'borderRadius': '10px',
                        'border': '1px solid #0f766e',
                        'backgroundColor': '#ecfdf5',
                        'color': '#115e59',
                        'cursor': 'pointer',
                        'minWidth': '240px',
                        'textAlign': 'center',
                    }
                ),
            ], style={
                'display': 'flex',
                'gap': '12px',
                'flexWrap': 'wrap',
                'justifyContent': 'center',
                'alignItems': 'center',
                'width': '100%',
                'maxWidth': '560px',
                'margin': '8px auto 0 auto',
            }),
        ],
        style={
            'maxWidth': '720px',
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
        html.Div([html.Label('Projeto:'), dcc.Dropdown(id='filter-projeto', options=[{'label':p,'value':p} for p in unique_sorted(fato['Projeto'])], value=unique_sorted(fato['Projeto'])[0] if len(unique_sorted(fato['Projeto']))>0 else None, clearable=False)], style={'width':'20%', 'display':'inline-block'}),
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
            html.Label('Team (Portfólio):'),
            dcc.Dropdown(
                id='filter-portfolio-team',
                options=get_portfolio_team_filter_options(),
                value='__ALL__',
                clearable=False
            )
        ], style={'width':'20%', 'display':'inline-block', 'marginLeft':'20px'}),
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
        return hidden_style, nav_style, 'Módulo: Porfólio', filters_style, hidden_style, build_portfolio_tab()

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
    Input('filter-portfolio-team', 'value')
)
def render_tab(main_view, tab, start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, portfolio_team):
    if main_view in (None, 'home'):
        return html.Div(
            'Selecione "Porfólio" ou "Serviços (Value Stream)" na tela principal para continuar.',
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

        metric_names, rows = compute_weekly_service_metrics(df_proj, weeks, lead_time_col='LeadTime_Selected_Dias')
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
        for m in ['Qtd. Itens Descartados', 'DDP', 'Frequência de Deploy', 'Lead time para mudanças', 'Taxa de demanda de falha', 'MTTR']:
            style_data_conditional.append({
                'if': {'filter_query': f'{{Métrica}} = "{m}"'},
                'backgroundColor': 'rgb(245, 245, 245)', 'color': '#bbb', 'fontStyle': 'italic'
            })

        titulo = f"Performance da Entrega do Serviço: {projeto}" if projeto else "Performance da Entrega do Serviço"

        return html.Div([
            html.H3(titulo, style={'textAlign': 'center', 'marginBottom': '10px'}),
            leadtime_selection_summary,
            html.Div(
                f"Lead Time = primeira etapa selecionada (compromisso) até finalização | "
                f"Amostra no período filtrado: {int(time_metric_series(df, 'LeadTime_Selected_Dias', non_negative=True).shape[0])}",
                style={'textAlign': 'center', 'color': '#555', 'marginBottom': '10px', 'fontSize': '13px'}
            ),
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
            html.Div(id='performance-metric-chart')
        ])

    if tab == 'tab-lead-time':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        df_lt = df.copy()
        if not df_lt.empty:
            df_lt = df_lt[done_time_eligible_mask(df_lt)].copy()
        if df_lt.empty or 'LeadTime_Selected_Dias' not in df_lt.columns:
            return html.Div('Sem dados de Lead Time para o período e filtros selecionados.')

        df_lt['LeadTime_Selected_Dias'] = pd.to_numeric(df_lt['LeadTime_Selected_Dias'], errors='coerce')
        df_lt['DataDone'] = pd.to_datetime(df_lt['DataDone'], errors='coerce')
        df_lt = df_lt.dropna(subset=['LeadTime_Selected_Dias', 'DataDone']).copy()
        df_lt = df_lt[df_lt['LeadTime_Selected_Dias'] >= 0].sort_values('DataDone')
        if df_lt.empty:
            return html.Div('Sem dados válidos de Lead Time para o período e filtros selecionados.')

        lt_series = time_metric_series(df_lt, 'LeadTime_Selected_Dias', non_negative=True)
        if lt_series.empty:
            return html.Div('Sem amostra válida de Lead Time para o período e filtros selecionados.')

        lt_stats = {
            'p50': exact_empirical_percentile(lt_series, 0.50),
            'p75': exact_empirical_percentile(lt_series, 0.75),
            'p85': exact_empirical_percentile(lt_series, 0.85),
            'p95': exact_empirical_percentile(lt_series, 0.95),
            'mean': float(lt_series.mean()),
        }
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

        subtitle = (
            f"Projeto: {projeto or 'Todos'} | Período: {start_ts.date()} a {end_ts.date()} | "
            f"Amostra: {int(len(lt_series))} itens | Início: {leadtime_meta.get('label', 'padrão')}"
        )
        return html.Div([
            html.H3("Lead Time", style={'textAlign': 'center'}),
            html.P(subtitle, style={'textAlign': 'center', 'color': '#666'}),
            dcc.Graph(figure=fig_lt_dist),
            dcc.Graph(figure=fig_lt_scatter),
        ])

    if tab == PORTFOLIO_TAB_VALUE:
        snapshot, error = get_portfolio_snapshot()
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

        groups = snapshot['groups']

        epicos_status = groups.get('epicos_por_team_status', pd.DataFrame())
        features_status = groups.get('features_por_team_status', pd.DataFrame())
        epicos_complexidade = groups.get('epicos_por_complexidade', pd.DataFrame())
        features_complexidade = groups.get('features_por_complexidade', pd.DataFrame())
        epicos_fluxo_etapas = groups.get('epicos_fluxo_etapas', pd.DataFrame())
        pendencias_q_por_time = groups.get('pendencias_q_por_time', pd.DataFrame())
        aging_us_20 = groups.get('aging_us_20', pd.DataFrame())
        aging_features_40 = groups.get('aging_features_40', pd.DataFrame())
        aging_us_comp_20 = groups.get('aging_us_comp_20', pd.DataFrame())
        aging_features_comp_40 = groups.get('aging_features_comp_40', pd.DataFrame())
        executive_tiles = groups.get('executive_tiles', pd.DataFrame())
        epicos_por_team_total = groups.get('epicos_por_team_total', pd.DataFrame())
        features_por_team_total = groups.get('features_por_team_total', pd.DataFrame())
        epicos_detalhe = groups.get('epicos_detalhe', pd.DataFrame())
        features_detalhe = groups.get('features_detalhe', pd.DataFrame())
        has_us_items = bool(groups.get('has_us_items', False))

        selected_team = str(portfolio_team or '__ALL__')

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
        aging_us_20 = filter_by_team(aging_us_20)
        aging_features_40 = filter_by_team(aging_features_40)
        aging_us_comp_20 = filter_by_team(aging_us_comp_20)
        aging_features_comp_40 = filter_by_team(aging_features_comp_40)
        epicos_por_team_total = filter_by_team(epicos_por_team_total)
        features_por_team_total = filter_by_team(features_por_team_total)
        epicos_detalhe = filter_by_team(epicos_detalhe)
        features_detalhe = filter_by_team(features_detalhe)
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

        def render_q_pendencias_grid(df_q):
            if df_q is None or df_q.empty:
                return html.Div([html.H4('Q Pendências por TEAM'), html.P('Sem dados para exibição.')])
            quadrantes = ['Q1 Pendências', 'Q2 Pendências', 'Q3 Pendências']
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
            return html.Div([
                html.H3('Indicador 1 - Q Pendências por TEAM', style={'textAlign': 'left'}),
                *blocks
            ], style={'marginTop': '24px'})

        def render_executive_tiles(df_exec):
            if df_exec is None or df_exec.empty:
                return html.Div([html.H3('Indicador 3 - Resumo Executivo'), html.P('Sem dados para exibição.')])
            colors = {'ok': '#2e7d32', 'alerta': '#ef6c00', 'risco': '#ad1457', 'info': '#1976d2'}
            cards = []
            for _, row in df_exec.iterrows():
                bg = colors.get(str(row.get('Tipo', 'info')), '#1976d2')
                cards.append(html.Div([
                    html.Div(str(row['Indicador']), style={'fontSize': '16px', 'fontWeight': 'bold'}),
                    html.Div(str(int(row['Valor'])), style={'fontSize': '56px', 'lineHeight': '1.1'}),
                ], style={
                    'backgroundColor': bg,
                    'color': 'white',
                    'padding': '12px',
                    'borderRadius': '4px',
                    'minHeight': '135px',
                }))
            return html.Div([
                html.H3('Indicador 3 - Resumo Executivo', style={'textAlign': 'left'}),
                html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fill, minmax(170px, 1fr))',
                    'gap': '10px'
                }),
                html.P(
                    'Estado divergente = features sem épico + épicos sem features (quebra de relacionamento entre níveis).',
                    style={'marginTop': '8px', 'color': '#555'}
                )
            ], style={'marginTop': '24px'})

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

        total_epicos_visao = int(epicos_por_team_total['QtdEpicos'].sum()) if epicos_por_team_total is not None and not epicos_por_team_total.empty else 0
        total_features_visao = int(features_por_team_total['QtdFeatures'].sum()) if features_por_team_total is not None and not features_por_team_total.empty else 0
        epicos_sem_features_visao = int((epicos_detalhe['QtdFeatures'] == 0).sum()) if epicos_detalhe is not None and not epicos_detalhe.empty else 0
        features_sem_epico_visao = int((features_detalhe['EpicID'].fillna('').astype(str).str.strip() == '').sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        features_sem_filhos_visao = int((features_detalhe['QtdFilhos'] == 0).sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        features_sem_mov_15_visao = int((features_detalhe['DiasSemMovimentacao'] > 15).sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        features_sem_mov_30_visao = int((features_detalhe['DiasSemMovimentacao'] > 30).sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        scope_label = 'Todos os teams' if selected_team == '__ALL__' else selected_team
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

        return html.Div([
            html.H3('Painel de Portfólio', style={'textAlign': 'center'}),
            html.P(
                f"Atualizado em: {snapshot['updated_at']} | Escopo: {scope_label} | Fonte: CSV local de portfólio",
                style={'textAlign': 'center', 'color': '#666'}
            ),
            html.Div([
                create_kpi_card('Total de épicos', f"{total_epicos_visao}", class_name='two columns'),
                create_kpi_card('Total de features', f"{total_features_visao}", class_name='two columns'),
                create_kpi_card('Épicos sem features', f"{epicos_sem_features_visao}", class_name='two columns'),
                create_kpi_card('Features sem épico', f"{features_sem_epico_visao}", class_name='two columns'),
                create_kpi_card('Features sem filhos', f"{features_sem_filhos_visao}", class_name='two columns'),
                create_kpi_card('Sem movimento 15d / 30d', f"{features_sem_mov_15_visao} / {features_sem_mov_30_visao}", class_name='two columns'),
            ], className='row'),

            render_q_pendencias_grid(pendencias_q_por_time),

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

            render_executive_tiles(executive_tiles),
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

            html.Div([
                html.Div([
                    html.H4('Visão de Épicos', style={'textAlign': 'center'}),
                    grouped_chart(
                        epicos_status,
                        x_col='Status',
                        y_col='QtdEpicos',
                        color_col='Team',
                        title='Épicos por TEAM e etapa de fluxo'
                    ),
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
                    grouped_chart(
                        features_status,
                        x_col='Status',
                        y_col='QtdFeatures',
                        color_col='Team',
                        title='Features por TEAM e etapa de fluxo'
                    ),
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
            ], className='row', style={'marginTop': '20px'}),

            portfolio_table_component(
                epicos_fluxo_etapas,
                'Épicos: quantidade de itens por etapa de fluxo',
                'table-portfolio-epicos-fluxo-etapas'
            ),
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
            render_tab(main_view, 'tab-estabilidade', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, portfolio_team),
            html.Hr(style={'margin': '30px 0'}),
            render_tab(main_view, 'tab-qualidade', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, portfolio_team),
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
            render_tab(main_view, 'tab-dim', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, portfolio_team),
            html.Hr(),
            render_tab(main_view, 'tab-tipos', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, portfolio_team),
            html.Hr(),
            render_tab(main_view, 'tab-eficiencia', start_date, end_date, projeto, tipo, classe_servico, responsavel, leadtime_stages, portfolio_team),
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
        tp_done = df.dropna(subset=['DataDone']).copy()
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
        df_breakdown['dummy'] = 'Lead Time Médio'
        fig_breakdown = px.bar(df_breakdown, x='Dias', y='dummy', orientation='h', color='Componente',
                               title='Breakdown do Lead Time Médio por Componente', labels={'Dias': 'Dias Médios', 'dummy': ''},
                               height=400, template='plotly_white')
        fig_breakdown.update_layout(barmode='stack', yaxis_title=None, yaxis_showticklabels=False, legend_title_text='Componente')

        fig_scatter_eff = px.scatter(df_eff, x='Eficiencia', y='EficienciaAjustada',
                                     color='TipoDemanda', hover_data=['ItemID'], title='Eficiência de Fluxo (1-ρ) por Semana de Referência',
                                     labels={'Eficiencia': 'Eficiência de Fluxo (1-ρ)', 'EficienciaAjustada': 'Eficiência de Fluxo (1-ρ)'}, color_discrete_map=color_map)
        fig_scatter_eff.update_layout(height=550)
        fig_scatter_eff.add_shape(type='line', x0=0, y0=0, x1=1, y1=1, line=dict(color='grey', width=2, dash='dash'))

        # --- 3. Criar Tabela Detalhada ---
        table_cols = ['ItemID', 'Projeto', 'TipoDemanda', 'LeadTime_Dias', 'TempoBacklog_Dias', 'TempoExecucao_Dias', 'TempoBloqueioDias', 'TempoEsperaIntermediariaDias', 'Outros Tempos (dias)', 'Eficiencia', 'EficienciaAjustada', 'Diferença Eficiência']
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

        details, summary = detect_systemic_patterns(df_patterns, start_ts, end_ts, PATTERN_RULES)
        if details.empty:
            return html.Div([
                html.H3('Padrões Sistêmicos', style={'textAlign': 'center'}),
                html.P(
                    'Nenhum padrão detectado com as regras configuradas para o período/filtros.',
                    style={'textAlign': 'center', 'color': '#555'}
                ),
            ])

        criticos = int((details['Severidade'] == 'Crítico').sum())
        atencao = int((details['Severidade'] == 'Atenção').sum())
        semanas_afetadas = int(details['Semana'].nunique())

        kpis = html.Div([
            create_kpi_card('Ocorrências Críticas', criticos, class_name='four columns'),
            create_kpi_card('Ocorrências Atenção', atencao, class_name='four columns'),
            create_kpi_card('Semanas com Sinal', semanas_afetadas, class_name='four columns'),
        ], className='row')

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

        details_view = details.sort_values(['Semana', 'Severidade'], ascending=[False, True])
        table_summary = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in summary.columns],
            data=summary.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            page_size=12,
        )
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
        )

        return html.Div([
            html.H3('Padrões Sistêmicos Detectados', style={'textAlign': 'center'}),
            html.P(
                'Detecção automática por regras configuráveis (PATTERN_RULES/JIRA_PATTERN_RULES). '
                'Inclui urgência crônica, burnout, confiança comprometida, problema sistêmico de fluxo, '
                'atrasos/desperdícios, estagnação e compromisso prematuro.',
                style={'textAlign': 'center', 'color': '#555'}
            ),
            kpis,
            dcc.Graph(figure=fig_summary),
            html.H4('Resumo de Ocorrências', style={'marginTop': '16px'}),
            table_summary,
            html.H4('Detalhamento Semanal', style={'marginTop': '16px'}),
            table_details,
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

        # Base sem filtro de DataDone para calcular WIP
        df_base = fato.copy()
        if projeto:
            df_base = df_base[df_base['Projeto'] == projeto]
        if tipo:
            df_base = df_base[df_base['TipoDemanda'] == tipo]
        if responsavel:
            df_base = df_base[df_base['Responsavel'] == responsavel]
        # Itens concluídos no período (para Lead Time)
        df_done = df_base[
            (df_base['DataDone'] >= start_date_ts) &
            (df_base['DataDone'] <= end_date_ts)
        ].copy()
        df_done = df_done[done_time_eligible_mask(df_done)]

        # --- 1. Estatísticas de Lead Time ---
        lead_time_stats = {}
        if not df_done.empty and 'LeadTime_Dias' in df_done.columns and not df_done['LeadTime_Dias'].dropna().empty:
            lt = time_metric_series(df_done, 'LeadTime_Dias')
            lt_exact = exact_percentile_map(lt, [0.25, 0.50, 0.75, 0.85, 0.95]) if not lt.empty else {}
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
                'Coef. Variação (%)': f"{(lt.std() / lt.mean() * 100):.2f}" if lt.mean() > 0 else '—',
                'Amplitude': f"{lt.max() - lt.min():.2f}",
                'IQR (P75-P25)': f"{lt_exact.get(0.75, np.nan) - lt_exact.get(0.25, np.nan):.2f}",
                'Assimetria (Skewness)': f"{lt.skew():.2f}",
                'Curtose': f"{lt.kurtosis():.2f}",
            }

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
        if not df_done.empty and 'LeadTime_Dias' in df_done.columns and not df_done['LeadTime_Dias'].dropna().empty:
            fig_lt_hist = px.histogram(df_done, x='LeadTime_Dias', nbins=30,
                                       title='Distribuição do Lead Time (dias)',
                                       labels={'LeadTime_Dias': 'Lead Time (dias)', 'count': 'Frequência'},
                                       height=500)
            lt_hist_series = time_metric_series(df_done, 'LeadTime_Dias')
            lt_mean_val = lt_hist_series.mean()
            lt_median_val = exact_empirical_percentile(lt_hist_series, 0.50)
            lt_p85_val = exact_empirical_percentile(lt_hist_series, 0.85)
            fig_lt_hist.add_vline(x=lt_mean_val, line_dash="dash", line_color="red", annotation_text=f"Média: {lt_mean_val:.1f}")
            fig_lt_hist.add_vline(x=lt_median_val, line_dash="dash", line_color="blue", annotation_text=f"Mediana: {lt_median_val:.1f}")
            fig_lt_hist.add_vline(x=lt_p85_val, line_dash="dash", line_color="orange", annotation_text=f"P85: {lt_p85_val:.1f}")

            fig_lt_box = px.box(df_done, y='LeadTime_Dias', title='Box Plot do Lead Time (dias)',
                                labels={'LeadTime_Dias': 'Lead Time (dias)'}, points='all', height=500)

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

        return html.Div([
            html.H3("Estatística Descritiva", style={'textAlign': 'center'}),
            html.P(filtro_info, style={'textAlign': 'center', 'color': '#666', 'marginBottom': '30px'}),

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

        # Base para cálculo de capacidade: usa dados importados e filtros ativos.
        df_capacity_base = fato.copy()
        if projeto:
            df_capacity_base = df_capacity_base[df_capacity_base['Projeto'] == projeto]
        if tipo:
            df_capacity_base = df_capacity_base[df_capacity_base['TipoDemanda'] == tipo]
        if responsavel:
            df_capacity_base = df_capacity_base[df_capacity_base['Responsavel'] == responsavel]

        weeks = pd.date_range(start=start_date_ts, end=end_date_ts + pd.Timedelta(days=7), freq='W-MON')
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal de capacidade de fila.')

        weekly_rows = []
        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]
            arrivals = len(df_capacity_base[
                (df_capacity_base['DataInProgress'] >= week_start) &
                (df_capacity_base['DataInProgress'] < week_end)
            ])
            throughput = len(df_capacity_base[
                (df_capacity_base['DataDone'] >= week_start) &
                (df_capacity_base['DataDone'] < week_end)
            ])
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

    values = []
    for wl in week_labels:
        val_str = str(row[wl]).replace('%', '').replace(',', '.').strip()
        try:
            values.append(float(val_str))
        except (ValueError, TypeError):
            values.append(None)

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

    fig.update_layout(
        title=f'{metric_name} — Tendência Semanal',
        xaxis_title='Semana',
        yaxis_title=metric_name,
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


@app.callback(
    Output('cfd-summary-panel', 'children'),
    Input('cfd-graph', 'clickData'),
    Input('cfd-graph', 'hoverData'),
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
    app.run(debug=True)
