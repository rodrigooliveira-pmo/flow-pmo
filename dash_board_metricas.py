import pandas as pd
import numpy as np
import glob
import os
import csv
import re
import json
import shutil
import platform
from pathlib import Path
from datetime import datetime

from shared.env_utils import load_env_file, parse_json_env
from shared.text_utils import normalize_text

# Semana padrão do sistema: janelas de segunda (inclusive) até segunda (exclusiva).
WEEK_DATE_RANGE_FREQ = 'W-MON'

HIGHEST_ALIAS_TOKENS = (
    'highest', 'higest', 'expedite', 'urgent', 'urgente',
    'critical', 'critico', 'blocker', 'fast track', 'fasttrack',
)


def is_highest_alias(value):
    text = normalize_text(value)
    if not text:
        return False
    return any(token in text for token in HIGHEST_ALIAS_TOKENS)


def canonicalize_highest_label(value):
    text = '' if pd.isna(value) else str(value).strip()
    if not text or text.lower() == 'nan':
        return text
    return 'Highest' if is_highest_alias(text) else text

DEFAULT_FLOW_POLICIES = {
    "default": {
        "wip_limit": 12,
        "wip_age_sle_days": 15,
        "blocked_days_limit": 5,
        "flow_pressure_limit": 1.0
    }
}

DEFAULT_CLASS_OF_SERVICE_RULES = {
    "expedite_priorities": ["blocker", "critical", "highest", "alta", "urgente"],
    "fixed_date_keywords": ["fixed date", "deadline", "due date", "prazo", "data fixa"],
    "intangible_keywords": ["risk", "compliance", "seguranca", "segurança", "regulatory"]
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

WINDOWS_DEFAULT_LATEST_DIR = r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest"
MACOS_DEFAULT_LATEST_DIR = os.path.expanduser("~/Documents/dados/latest")


def _looks_like_windows_path(path_value):
    value = str(path_value or "").strip()
    return bool(re.match(r"^[A-Za-z]:[\\/]", value))


def resolve_latest_dir(target_file):
    latest_dir = os.getenv("FLOW_PMO_LATEST_DIR", "").strip()
    current_system = platform.system()

    if latest_dir:
        if current_system != 'Windows' and _looks_like_windows_path(latest_dir):
            latest_dir = ""

    if not latest_dir:
        if current_system == 'Windows':
            latest_dir = WINDOWS_DEFAULT_LATEST_DIR
        elif current_system == 'Darwin':
            latest_dir = MACOS_DEFAULT_LATEST_DIR
        else:
            latest_dir = os.path.join(os.path.dirname(os.path.abspath(target_file)), "latest")

    return latest_dir


def load_flow_policies():
    return parse_json_env("FLOW_POLICIES", parse_json_env("JIRA_FLOW_POLICIES", DEFAULT_FLOW_POLICIES))


def load_class_of_service_rules():
    return parse_json_env(
        "CLASS_OF_SERVICE_RULES",
        parse_json_env("JIRA_CLASS_OF_SERVICE_RULES", DEFAULT_CLASS_OF_SERVICE_RULES),
    )


def load_pattern_rules():
    return parse_json_env("PATTERN_RULES", parse_json_env("JIRA_PATTERN_RULES", DEFAULT_PATTERN_RULES))


def copy_latest_artifact(source_file, target_file):
    """Copy a generated artifact to a stable filename."""
    try:
        shutil.copy2(source_file, target_file)
        print(f"Arquivo latest atualizado: {target_file}")
        latest_dir = resolve_latest_dir(target_file)
        source_abs = os.path.abspath(target_file)
        target_abs = os.path.abspath(os.path.join(latest_dir, os.path.basename(target_file)))
        if source_abs != target_abs:
            os.makedirs(latest_dir, exist_ok=True)
            shutil.copy2(target_file, target_abs)
            print(f"Alias latest publicado em: {target_abs}")
        return target_file
    except Exception as exc:
        print(f"Warning: Não foi possível atualizar {target_file}: {exc}")
        return None


def classify_service_class(row, rules):
    """Classify class of service from priority/labels/type."""
    priority_raw = canonicalize_highest_label(row.get('Prioridade', ''))
    priority = normalize_text(priority_raw)
    labels = normalize_text(row.get('Etiquetas', ''))
    title = normalize_text(row.get('Title', ''))
    item_type = normalize_text(row.get('Tipo de Problema', row.get('WorkItemSubType', '')))

    expedite_priorities = {normalize_text(x) for x in rules.get('expedite_priorities', [])}
    fixed_keywords = [normalize_text(x) for x in rules.get('fixed_date_keywords', [])]
    intangible_keywords = [normalize_text(x) for x in rules.get('intangible_keywords', [])]

    if priority in expedite_priorities:
        return 'Highest'
    if any(k and (k in labels or k in title) for k in fixed_keywords):
        return 'Fixed Date'
    if any(k and (k in labels or k in title or k in item_type) for k in intangible_keywords):
        return 'Intangible'
    # Default class follows the item's project priority instead of hardcoded "Standard".
    raw_priority = row.get('Prioridade', '')
    if pd.notna(raw_priority):
        priority_value = canonicalize_highest_label(raw_priority)
        if priority_value and priority_value.lower() != 'nan':
            return priority_value
    return 'Standard'


def is_discarded_item(row):
    """Heuristic for discarded/cancelled items."""
    resolution = normalize_text(row.get('Resolução', ''))
    title = normalize_text(row.get('Title', ''))
    subtype = normalize_text(row.get('WorkItemSubType', row.get('Tipo de Problema', '')))
    discard_tokens = [
        "wont do", "won't do", "cancel", "cancelad", "duplicat", "obsolete",
        "rejected", "nao sera feito", "nao-fazer", "descart", "invalid"
    ]
    txt = f"{resolution} {title} {subtype}"
    return any(token in txt for token in discard_tokens)


def get_project_policy(project, policies):
    base = dict(policies.get('default', {}))
    base.update(policies.get(project, {}))
    return base


# Load local env files (if present) for optional policy/rule configuration.
# Do not override runtime env vars injected by the orchestrator.
load_env_file(Path(__file__).with_name('jira_env.txt'), overwrite=False)
load_env_file(Path(__file__).with_name('jira-env.txt'), overwrite=False)
FLOW_POLICIES = load_flow_policies()
CLASS_OF_SERVICE_RULES = load_class_of_service_rules()
PATTERN_RULES = load_pattern_rules()

# Try to import openpyxl, fallback to xlsxwriter
try:
    import openpyxl
    excel_engine = 'openpyxl'
except ImportError:
    try:
        import xlsxwriter
        excel_engine = 'xlsxwriter'
    except ImportError:
        excel_engine = 'openpyxl'  # Will attempt to install or use default

def detect_date_columns(df):
    """
    Automatically detect and map date columns in the dataframe.
    Returns a dict with 'sprint_backlog', 'in_progress', 'done' keys.
    """
    date_mapping = {
        'sprint_backlog': None,
        'in_progress': None,
        'done': None
    }
    
    # List of metadata columns that are NOT workflow stages
    metadata_cols = {'ID', 'Link', 'Title', 'Done', 'Tipo de Problema', 
                     'Prioridade', 'Versões de correção', 'Componentes', 
                     'Responsável', 'Criador', 'Created', 'Start date', 'Space', 'Resolução', 
                     'Data Cancelled',
                     'Etiquetas', 'Blocked Days', 'Blocked', 'Flagged', 
                     'Story Points', 'Organizations', 'Sprints', 'Principal', 
                     'Afeta as versões', 'Change type', 'Epic Name', 
                     'Expected deliverables', 'B.U.', 'Checklist Completed',
                     'Team', 'Versões afetadas', 'Ready', 'Build'}
    
    # Normalize column names for comparison
    cols = list(df.columns)
    cols_lower = [str(c).strip().lower() for c in cols]

    # Get workflow columns (columns that are not metadata)
    workflow_cols = [col for col in cols if col not in metadata_cols]
    workflow_cols_lower = [str(c).strip().lower() for c in workflow_cols]

    # Find "Done" column (accept common Portuguese variants)
    done_candidates = ['done', 'itens concluídos', 'itens concluidos', 'concluído', 'concluido', 'ready for production', 'itens concluido']
    for cand in done_candidates:
        if cand in cols_lower:
            date_mapping['done'] = cols[cols_lower.index(cand)]
            # Remove Done from workflow columns
            if date_mapping['done'] in workflow_cols:
                idx = workflow_cols.index(date_mapping['done'])
                workflow_cols.pop(idx)
                workflow_cols_lower.pop(idx)
            break

    # Find sprint_backlog (first workflow column) — accept triage/backlog/to do
    backlog_candidates = ['sprint backlog', 'backlog', 'to do', 'triagem']
    for cand in backlog_candidates:
        if cand in workflow_cols_lower:
            date_mapping['sprint_backlog'] = workflow_cols[workflow_cols_lower.index(cand)]
            break

    if date_mapping['sprint_backlog'] is None and workflow_cols:
        date_mapping['sprint_backlog'] = workflow_cols[0]

    # Find in_progress (look for common names)
    inprog_candidates = ['in progress', 'inprogress', 'in progress', 'in progress']
    for cand in inprog_candidates:
        if cand in workflow_cols_lower:
            date_mapping['in_progress'] = workflow_cols[workflow_cols_lower.index(cand)]
            break

    # If still not found, pick the first remaining workflow column different from sprint_backlog
    if date_mapping['in_progress'] is None:
        remaining_workflow = [col for col in workflow_cols if col != date_mapping['sprint_backlog']]
        if remaining_workflow:
            date_mapping['in_progress'] = remaining_workflow[0]
    
    return date_mapping


def compute_valid_lead_days(done_date, sprint_backlog_date):
    """Return lead time in days or None when missing/negative."""
    if pd.isna(done_date) or pd.isna(sprint_backlog_date):
        return None
    lead_days = (done_date - sprint_backlog_date).days
    return lead_days if lead_days >= 0 else None


def resolve_backlog_date(row):
    """
    Resolve lead-time start date (commit/backlog entry) with factual fallback.
    Preference order keeps semantic intent but avoids near-empty lead-time samples
    when a project does not populate 'Sprint Backlog'.
    """
    for col in ['Sprint Backlog', 'Backlog', 'Triagem']:
        value = row.get(col, pd.NaT)
        dt = pd.to_datetime(value, dayfirst=True, errors='coerce')
        if pd.notna(dt):
            return dt
    return pd.NaT


def is_time_eligible_done_row(row):
    """Eligible for time metrics only if item has no cancellation marker/history."""
    cancelled_dt = row.get('Data Cancelled', pd.NaT)
    if pd.notna(cancelled_dt):
        return False
    cancelled_flag = row.get('Cancelado', 0)
    try:
        if pd.notna(cancelled_flag) and int(cancelled_flag) == 1:
            return False
    except Exception:
        pass
    return True


def time_eligible_done_mask(df):
    """Mask for items eligible to time metrics: done without cancellation history."""
    mask = pd.Series(True, index=df.index)
    if 'Data Cancelled' in df.columns:
        mask &= df['Data Cancelled'].isna()
    if 'Cancelado' in df.columns:
        cancelado_num = pd.to_numeric(df['Cancelado'], errors='coerce').fillna(0)
        mask &= cancelado_num.eq(0)
    return mask


def compute_valid_lead_series(df):
    """Return non-negative lead times for dataframe rows using best backlog-start column."""
    if 'Done' not in df.columns:
        return pd.Series(dtype='float64')
    backlog_col = None
    for candidate in ['Sprint Backlog', 'Backlog', 'Triagem']:
        if candidate in df.columns:
            backlog_col = candidate
            break
    if backlog_col is None:
        return pd.Series(dtype='float64')
    eligible_df = df[time_eligible_done_mask(df)] if len(df) else df
    lt_days = (eligible_df['Done'] - eligible_df[backlog_col]).dt.days
    return lt_days[lt_days >= 0]


def resolve_in_progress_date(row):
    """
    Resolve execution start date with robust fallback:
    - Prefer explicit 'In Progress'
    - Otherwise use the earliest available workflow stage date (excluding terminal Done)
    """
    def _parse(value):
        return pd.to_datetime(value, dayfirst=True, errors='coerce')

    in_progress = _parse(row.get('In Progress'))
    if pd.notna(in_progress):
        return in_progress

    stage_candidates = [
        'Start date',
        'Sprint Backlog',
        'Backlog',
        'Triagem',
        'Ready to Start',
        'To Do',
        'In progress',
        'Development',
        'ready code review',
        'Code review',
        'ready testing/Qa',
        'Testing/QA',
        'ready homolog',
        'Homolog',
        'ready for production',
    ]
    dates = []
    for col in stage_candidates:
        if col not in row.index:
            continue
        dt = _parse(row.get(col))
        if pd.notna(dt):
            dates.append(dt)

    if dates:
        return min(dates)
    return pd.NaT


def week_start_monday(ts):
    """Return normalized monday-start week key for a timestamp."""
    if pd.isna(ts):
        return pd.NaT
    ts = pd.Timestamp(ts)
    return (ts - pd.Timedelta(days=ts.weekday())).normalize()


def calculate_flow_efficiency(arrival_rate, service_rate):
    """Flow efficiency aligned with queue-capacity rule: 1 - (lambda/mu)."""
    if service_rate is None or pd.isna(service_rate) or service_rate <= 0:
        return np.nan, np.nan
    if arrival_rate is None or pd.isna(arrival_rate) or arrival_rate < 0:
        return np.nan, np.nan
    rho = arrival_rate / service_rate
    return rho, (1 - rho)

def detect_project_from_id(id_str):
    """
    Detect project from work item ID prefix
    Returns project name like 'W1NNER', 'DATA&ANALYTICS', 'BEFINANCE', 'S1NC'
    """
    if pd.isna(id_str):
        return 'UNKNOWN'
    
    id_str = str(id_str).upper().strip()
    # Extract prefix before the dash
    prefix = id_str.split('-')[0] if '-' in id_str else id_str
    
    # Map ID prefixes to projects
    prefix_to_project = {
        'W1NNR': 'W1NNER',
        'W1NNRI': 'W1NNER',  # Alternative spelling
        'DT': 'DATA&ANALYTICS',
        'DA': 'DATA&ANALYTICS',
        'BF': 'BEFINANCE',
        'S1NC': 'S1NC',
        'W1SFT': 'S1NC',
    }
    
    # Try to find project from prefix
    for key, project in prefix_to_project.items():
        if prefix.startswith(key):
            return project
    
    return 'UNKNOWN'

def detect_project_from_filename(filename):
    """
    Detect project from CSV filename
    """
    name = str(filename).strip().lower()
    tokens = re.split(r"[^a-z0-9]+", name)

    if "w1nner" in tokens or "w1nnr" in tokens:
        return 'W1NNER'
    elif "s1nc" in tokens or "sync" in tokens or "w1sft" in tokens:
        return 'S1NC'
    elif "befinance" in tokens or "bf" in tokens:
        return 'BEFINANCE'
    elif "dataanalytics" in tokens or "data" in tokens and "analytics" in tokens or "dt" in tokens or "da" in tokens:
        return 'DATA&ANALYTICS'
    else:
        return 'UNKNOWN'

def extract_timestamp_from_filename(file_path):
    """
    Extract datetime from filename patterns like:
    - *_YYYYMMDD_HHMMSS.*
    - *-YYYYMMDD-data.*
    Returns datetime or None.
    """
    stem = Path(file_path).stem

    m = re.search(r'(\d{8}_\d{6})', stem)
    if m:
        try:
            return datetime.strptime(m.group(1), '%Y%m%d_%H%M%S')
        except ValueError:
            pass

    m = re.search(r'(\d{8})', stem)
    if m:
        try:
            return datetime.strptime(m.group(1), '%Y%m%d')
        except ValueError:
            pass

    return None

def select_latest_csv_per_project(csv_files):
    """
    Keep only the latest CSV per detected project.
    Latest is decided by timestamp in filename; fallback to file mtime.
    Returns: (selected_files, ignored_files)
    """
    selected_by_project = {}
    selected_unknown = []
    ignored_files = []

    def _is_workflow_input_csv(stem_lower):
        """
        Return True only for CSVs that are valid workflow inputs for metrics consolidation.
        Excludes derived/report/process-mining artifacts that must not compete as latest project CSV.
        """
        auxiliary_suffixes = (
            "_commits",
            "_pullrequests",
            "_pipelines",
        )
        auxiliary_prefixes = (
            "capex-",
            "gmud-coverage-",
        )
        if "bottleneck" in stem_lower:
            return False
        if "process-mining" in stem_lower:
            return False
        if "_detailed_changelog" in stem_lower:
            return False
        if stem_lower.endswith(auxiliary_suffixes):
            return False
        if stem_lower.startswith(auxiliary_prefixes):
            return False
        if stem_lower.startswith("executive_report_"):
            return False
        if stem_lower.startswith("portfolio-bt-ns-"):
            return False
        if stem_lower.startswith("multi-downstream-"):
            return False
        return True

    for file_path in sorted(csv_files):
        stem_lower = Path(file_path).stem.lower()
        # Ignore derived artifacts that are not pipeline input datasets.
        if not _is_workflow_input_csv(stem_lower):
            ignored_files.append(file_path)
            continue

        project = detect_project_from_filename(Path(file_path).stem)
        ts = extract_timestamp_from_filename(file_path)
        mtime = os.path.getmtime(file_path)
        score = (
            ts is not None,                      # prefer explicit timestamp in filename
            ts if ts is not None else datetime.min,
            mtime                                # fallback tiebreaker
        )

        if project == 'UNKNOWN':
            selected_unknown.append(file_path)
            continue

        current = selected_by_project.get(project)
        if current is None:
            selected_by_project[project] = {'file': file_path, 'score': score}
            continue

        if score > current['score']:
            ignored_files.append(current['file'])
            selected_by_project[project] = {'file': file_path, 'score': score}
        else:
            ignored_files.append(file_path)

    selected_files = [v['file'] for v in selected_by_project.values()] + selected_unknown
    return sorted(selected_files), sorted(ignored_files)


def select_latest_bottleneck_csv_per_project(csv_files):
    """
    Keep only the latest bottleneck CSV per detected project.
    Bottleneck files follow pattern: *-data_bottlenecks.csv
    """
    selected_by_project = {}
    selected_unknown = []

    for file_path in sorted(csv_files):
        stem_lower = Path(file_path).stem.lower()
        if "bottleneck" not in stem_lower:
            continue

        project = detect_project_from_filename(Path(file_path).stem)
        ts = extract_timestamp_from_filename(file_path)
        mtime = os.path.getmtime(file_path)
        score = (
            ts is not None,
            ts if ts is not None else datetime.min,
            mtime,
        )

        if project == 'UNKNOWN':
            selected_unknown.append(file_path)
            continue

        current = selected_by_project.get(project)
        if current is None or score > current['score']:
            selected_by_project[project] = {'file': file_path, 'score': score}

    selected_files = [v['file'] for v in selected_by_project.values()] + selected_unknown
    return sorted(selected_files)


def load_bottleneck_table_from_csv_files(csv_files):
    """
    Build normalized bottleneck table from generated CSVs.
    Output columns are compatible with dashboard_full loader.
    """
    if not csv_files:
        return pd.DataFrame()

    required_cols = {'Etapa', 'Qtde Issues', 'Media Dias', 'Mediana Dias', 'P90 Dias'}
    rows = []

    for csv_file in csv_files:
        project = detect_project_from_filename(Path(csv_file).stem)
        if project == 'UNKNOWN':
            continue
        try:
            bdf = pd.read_csv(csv_file, encoding='utf-8-sig')
        except Exception:
            try:
                bdf = pd.read_csv(csv_file, encoding='latin-1')
            except Exception:
                continue
        if not required_cols.issubset(set(bdf.columns)):
            continue

        normalized = pd.DataFrame({
            'Projeto': project,
            'Etapa': bdf['Etapa'].astype(str),
            'Tempo Médio (dias)': pd.to_numeric(bdf['Media Dias'], errors='coerce'),
            'Tempo Mediano (dias)': pd.to_numeric(bdf['Mediana Dias'], errors='coerce'),
            'P90 (dias)': pd.to_numeric(bdf['P90 Dias'], errors='coerce'),
            'Qtde Itens': pd.to_numeric(bdf['Qtde Issues'], errors='coerce'),
            'Vazão da Etapa (itens)': pd.to_numeric(bdf['Qtde Issues'], errors='coerce'),
        }).dropna(subset=['Etapa', 'Tempo Médio (dias)'])

        normalized = normalized[normalized['Tempo Médio (dias)'] >= 0]
        if normalized.empty:
            continue
        normalized['Qtde Itens'] = normalized['Qtde Itens'].fillna(0).astype(int)
        normalized['Vazão da Etapa (itens)'] = normalized['Vazão da Etapa (itens)'].fillna(0).astype(int)
        rows.append(normalized)

    if not rows:
        return pd.DataFrame()

    out = pd.concat(rows, ignore_index=True)
    out = out.sort_values(['Projeto', 'Tempo Médio (dias)'], ascending=[True, False], ignore_index=True)
    return out


def save_consolidated_bottlenecks_workbook(bottleneck_table, output_folder, timestamp):
    """
    Export consolidated bottleneck data to a dedicated workbook.
    Source: selected *_bottlenecks.csv files already normalized by project.
    """
    if bottleneck_table is None or bottleneck_table.empty:
        return None

    output_file = os.path.join(output_folder, f"bottlenecks_consolidado_{timestamp}.xlsx")
    export_df = bottleneck_table.copy()
    export_df = export_df.sort_values(['Projeto', 'Tempo Médio (dias)'], ascending=[True, False], ignore_index=True)

    with pd.ExcelWriter(output_file, engine=excel_engine) as writer:
        export_df.to_excel(writer, sheet_name='Gargalos Consolidado', index=False)
        for projeto, proj_df in export_df.groupby('Projeto', sort=True):
            sheet_name = f"Gargalos_{str(projeto)}"[:31]
            proj_df.to_excel(writer, sheet_name=sheet_name, index=False)

    copy_latest_artifact(output_file, os.path.join(output_folder, "bottlenecks_consolidado_latest.xlsx"))
    print(f"Planilha consolidada de gargalos salva em: {output_file}")
    return output_file


def build_bottleneck_table_from_fact(fact_table, dimensions):
    """
    Fallback bottleneck table derived from fact table per project.
    """
    if fact_table is None or fact_table.empty:
        return pd.DataFrame()

    if 'ProjetoID' not in fact_table.columns:
        return pd.DataFrame()

    project_map = {}
    if dimensions is not None and 'Dim_Projeto' in dimensions and not dimensions['Dim_Projeto'].empty:
        project_map = {
            int(row['ProjetoID']): str(row['NomeProjeto'])
            for _, row in dimensions['Dim_Projeto'].iterrows()
            if pd.notna(row.get('ProjetoID')) and pd.notna(row.get('NomeProjeto'))
        }

    stage_columns = [
        ('Backlog', 'TempoBacklog_Dias'),
        ('Execução', 'TempoExecucao_Dias'),
        ('Bloqueio', 'TempoBloqueioDias'),
        ('Espera Intermediária', 'TempoEsperaIntermediariaDias'),
    ]

    rows = []
    for project_id, proj_df in fact_table.groupby('ProjetoID'):
        projeto = project_map.get(int(project_id), str(project_id))
        for stage_name, col in stage_columns:
            if col not in proj_df.columns:
                continue
            series = pd.to_numeric(proj_df[col], errors='coerce').dropna()
            series = series[series >= 0]
            if series.empty:
                continue
            rows.append({
                'Projeto': projeto,
                'Etapa': stage_name,
                'Tempo Médio (dias)': float(series.mean()),
                'Tempo Mediano (dias)': float(series.median()),
                'P90 (dias)': float(series.quantile(0.90)),
                'Qtde Itens': int(series.shape[0]),
                'Vazão da Etapa (itens)': int(series.shape[0]),
            })

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out = out.sort_values(['Projeto', 'Tempo Médio (dias)'], ascending=[True, False], ignore_index=True)
    return out

def categorize_work_item_type(tipo_de_problema):
    """
    Categorize work item types into support, defects/issues/problems, development or other.
    Returns tuple: (main_category, sub_category)
    """
    if pd.isna(tipo_de_problema):
        return ('Outro', 'Outro')
    
    tipo_str = str(tipo_de_problema).lower().strip()
    
    # Support is separated from defects/issues/problems.
    if any(word in tipo_str for word in ['support', 'suporte', 'ad-hoc', 'adhoc', 'ad hoc']):
        return ('Suporte', 'Suporte')

    # Defect/Issue/Problem category
    if any(word in tipo_str for word in ['bug', 'problema', 'defeito', 'issue']):
        return ('Defeitos', 'Issues/Defeitos/Problemas')
    
    # Development category
    elif any(word in tipo_str for word in ['feature', 'história', 'tarefa', 'task', 'melhoria', 'improvement']):
        if 'feature' in tipo_str:
            return ('Desenvolvimento', 'Feature')
        elif 'história' in tipo_str:
            return ('Desenvolvimento', 'História')
        elif 'melhoria' in tipo_str or 'improvement' in tipo_str:
            return ('Desenvolvimento', 'Melhoria')
        else:
            return ('Desenvolvimento', 'Tarefa')
    
    else:
        return ('Outro', 'Outro')

def load_and_consolidate_all_data(csv_files):
    """
    Load all CSV files and consolidate data by project.
    Returns a dictionary with consolidated DataFrames keyed by project.
    """
    project_data = {}
    file_reports = []

    encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    fallback_delimiters = [';', ',', '\t', '|']

    for csv_file in csv_files:
        report = {
            'file': Path(csv_file).name,
            'read': False,
            'encoding': None,
            'delimiter': None,
            'project': None,
            'rows': 0,
            'neg_lead_time_rows': 0,
            'reason': None
        }

        df = None
        try:
            # Try to detect delimiter using csv.Sniffer on a sample for available encodings
            detected_delim = None
            used_encoding = None
            for encoding in encodings:
                try:
                    with open(csv_file, 'r', encoding=encoding, errors='replace') as fh:
                        sample = fh.read(4096)
                        # If file is too small, sample will be short but that's OK
                        try:
                            sniff = csv.Sniffer()
                            dialect = sniff.sniff(sample, delimiters=';,\t|,')
                            detected_delim = dialect.delimiter
                        except Exception:
                            detected_delim = None
                        used_encoding = encoding
                        # If sniffer found a delimiter, try to read with it
                        if detected_delim:
                            try:
                                tmp = pd.read_csv(csv_file, encoding=encoding, delimiter=detected_delim, on_bad_lines='skip')
                                if not tmp.empty and len(tmp.columns) > 1:
                                    df = tmp
                                    report['encoding'] = encoding
                                    report['delimiter'] = detected_delim
                                    break
                            except Exception:
                                detected_delim = None
                                continue
                except Exception:
                    continue

            # If still not read, fallback to trying common delimiters
            if df is None:
                for encoding in encodings:
                    for delim in fallback_delimiters:
                        try:
                            tmp = pd.read_csv(csv_file, encoding=encoding, delimiter=delim, on_bad_lines='skip')
                            if not tmp.empty and len(tmp.columns) > 1:
                                df = tmp
                                report['encoding'] = encoding
                                report['delimiter'] = delim
                                break
                        except Exception:
                            continue
                    if df is not None:
                        break

            if df is None or df.empty or len(df.columns) <= 1:
                report['reason'] = 'Could not parse into multiple columns (wrong delimiter or empty)'
                file_reports.append(report)
                print(f"Skipped {report['file']}: {report['reason']}")
                continue

            # Normalize column names
            df.columns = [str(c).strip() for c in df.columns]

            # Detect project from ID or filename
            if 'ID' in df.columns:
                non_na_ids = df[df['ID'].notna()]['ID']
                first_id = non_na_ids.iloc[0] if not non_na_ids.empty else 'UNKNOWN'
                projeto = detect_project_from_id(first_id)
            else:
                projeto = detect_project_from_filename(Path(csv_file).stem)

            report['project'] = projeto

            # Detect and rename date columns
            date_cols_map = detect_date_columns(df)
            if not date_cols_map['sprint_backlog'] or not date_cols_map['in_progress'] or not date_cols_map['done']:
                report['reason'] = 'Missing required workflow date columns'
                file_reports.append(report)
                print(f"Skipped {report['file']}: {report['reason']}")
                continue

            rename_dict = {
                date_cols_map['sprint_backlog']: 'Sprint Backlog',
                date_cols_map['in_progress']: 'In Progress',
                date_cols_map['done']: 'Done'
            }
            df = df.rename(columns=rename_dict)

            # Categorize work items
            if 'Tipo de Problema' in df.columns:
                df['WorkItemCategory'] = df['Tipo de Problema'].apply(lambda x: categorize_work_item_type(x)[0])
                df['WorkItemSubType'] = df['Tipo de Problema'].apply(lambda x: categorize_work_item_type(x)[1])
            else:
                df['WorkItemCategory'] = 'Outro'
                df['WorkItemSubType'] = 'Outro'

            # Parse dates
            date_cols = ['Sprint Backlog', 'In Progress', 'Done', 'Data Cancelled']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

            # Fallback for files where In Progress is empty:
            # treat Sprint Backlog as execution start proxy.
            if 'In Progress' in df.columns and 'Sprint Backlog' in df.columns:
                missing_in_progress = df['In Progress'].isna() & df['Sprint Backlog'].notna()
                if missing_in_progress.any():
                    df.loc[missing_in_progress, 'In Progress'] = df.loc[missing_in_progress, 'Sprint Backlog']

            # Signal rows with inconsistent Done earlier than Sprint Backlog.
            if 'Sprint Backlog' in df.columns and 'Done' in df.columns:
                neg_lt_mask = (
                    df['Sprint Backlog'].notna()
                    & df['Done'].notna()
                    & ((df['Done'] - df['Sprint Backlog']).dt.days < 0)
                )
                report['neg_lead_time_rows'] = int(neg_lt_mask.sum())
                if report['neg_lead_time_rows'] > 0:
                    print(
                        f"Warning {report['file']}: {report['neg_lead_time_rows']} itens com Lead Time negativo "
                        f"(serão ignorados nas métricas de Lead Time)."
                    )

            # Convert Blocked Days to numeric (avoid NaN propagation from string values)
            if 'Blocked Days' in df.columns:
                df['Blocked Days'] = pd.to_numeric(df['Blocked Days'], errors='coerce').fillna(0)

            # Explicit eligibility for time metrics: Done rows without cancellation history.
            df['ElegivelTempoConcluido'] = time_eligible_done_mask(df).astype(int)
            if 'Done' in df.columns:
                df['DoneSemCancelamento'] = df['Done'].where(df['ElegivelTempoConcluido'].eq(1), pd.NaT)

            # Add project column and rows count
            df['Projeto'] = projeto
            report['rows'] = len(df)
            report['read'] = True

            # Consolidate by project (append or create)
            if projeto not in project_data:
                project_data[projeto] = []
            project_data[projeto].append(df)

            file_reports.append(report)

        except Exception as e:
            report['reason'] = f'Exception: {str(e)[:120]}'
            file_reports.append(report)
            print(f"Warning loading {report['file']}: {report['reason']}")
            continue
    
    # Merge all data per project
    consolidated_data = {}
    for projeto, dfs in project_data.items():
        if dfs:
            consolidated_data[projeto] = pd.concat(dfs, ignore_index=True)
    
    # Print file import summary
    print('\nFile import summary:')
    for r in file_reports:
        status = 'OK' if r.get('read') else 'SKIPPED'
        print(f" - {r['file']}: {status}, project={r.get('project')}, rows={r.get('rows')}, neg_lt={r.get('neg_lead_time_rows', 0)}, enc={r.get('encoding')}, delim={r.get('delimiter')}, reason={r.get('reason')}")

    return consolidated_data

def generate_consolidated_dashboard(consolidated_data):
    """
    Generate metrics from consolidated project data.
    Returns list of dicts with metrics per week and project.
    
    % Demanda de Falha and % Demanda de Valor are calculated at the week level (not per type):
    - % Demanda de Falha = (Throughput of Defeitos / Total Throughput) * 100
    - % Demanda de Valor = (Throughput of Desenvolvimento / Total Throughput) * 100
    """
    # Define Reporting Period (Weekly, Monday to Monday)
    # Extended from 2025-01-01 to capture all data
    start_date = pd.Timestamp('2025-01-01') 
    end_date = pd.Timestamp('2026-03-10')
    weeks = pd.date_range(start=start_date, end=end_date, freq=WEEK_DATE_RANGE_FREQ)
    
    metrics_by_week = {}
    
    # Process each project
    for projeto, df in consolidated_data.items():
        # Remove duplicates within the same project
        # Keep only one entry per work item ID to avoid processing the same item twice
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        # Process each week
        for i in range(len(weeks)-1):
            week_start = weeks[i]
            week_end = weeks[i+1]
            week_key = (projeto, week_start.date())
            
            # Only add once per (projeto, week)
            if week_key in metrics_by_week:
                continue
            
            metrics_by_week[week_key] = {
                'Projeto': projeto,
                'Week Start': week_start
            }
            
            # First pass: collect throughput data for each category to calculate global percentages
            throughput_by_category = {}
            
            # Process each category
            for category in df['WorkItemCategory'].unique():
                df_category = df[df['WorkItemCategory'] == category].copy()
                
                # Filter data for the week
                arrivals = df_category[(df_category['In Progress'] >= week_start) & (df_category['In Progress'] < week_end)]
                finished = df_category[(df_category['Done'] >= week_start) & (df_category['Done'] < week_end)]
                cancelled = pd.DataFrame()
                if 'Data Cancelled' in df_category.columns:
                    cancelled = df_category[
                        (df_category['Data Cancelled'] >= week_start) & (df_category['Data Cancelled'] < week_end)
                    ]
                
                # WIP: Average of daily active items
                daily_wips = []
                for d in range(7):
                    day = week_start + pd.Timedelta(days=d)
                    wip_count = len(df_category[
                        (df_category['In Progress'] <= day) & 
                        ((df_category['Done'] > day) | (df_category['Done'].isna()))
                    ])
                    daily_wips.append(wip_count)
                avg_wip = np.mean(daily_wips) if daily_wips else 0
                
                # WIP Age
                wip_at_end = df_category[
                    (df_category['In Progress'] < week_end) & 
                    ((df_category['Done'] >= week_end) | (df_category['Done'].isna()))
                ]
                avg_wip_age = (week_end - wip_at_end['In Progress']).dt.days.mean() if not wip_at_end.empty else 0

                # Lead Time & Efficiency (time metrics exclude items with cancellation history)
                finished_time_eligible = finished[time_eligible_done_mask(finished)] if not finished.empty else finished
                if not finished_time_eligible.empty:
                    lt_days = compute_valid_lead_series(finished_time_eligible)
                    avg_lead_time = lt_days.mean() if not lt_days.empty else 0
                    p85_lead_time = lt_days.quantile(0.85) if not lt_days.empty else 0
                    
                    # Detect wait stage columns for this dataframe
                    wait_columns = detect_wait_stage_columns(finished_time_eligible)
                    
                    effs_simple = []
                    effs_adjusted = []
                    
                    for _, row in finished_time_eligible.iterrows():
                        td_total = row['Done'] - row['Sprint Backlog']
                        td_exec = row['Done'] - row['In Progress']

                        # Skip items with invalid dates
                        if pd.isna(td_total) or pd.isna(td_exec):
                            continue

                        total_time = td_total.days
                        execution_time = td_exec.days

                        if total_time < 0:
                            continue

                        # Simple efficiency (original calculation)
                        if total_time > 0:
                            effs_simple.append(execution_time / total_time)
                        else:
                            effs_simple.append(1.0 if execution_time >= 0 else 0)

                        # Adjusted efficiency (considering blocking and wait time)
                        enh_eff, _, _ = calculate_enhanced_efficiency(row, wait_columns)
                        if enh_eff is not None and not pd.isna(enh_eff):
                            effs_adjusted.append(enh_eff)

                    avg_efficiency = np.nanmean(effs_simple) if effs_simple else 0
                    avg_efficiency_adjusted = np.nanmean(effs_adjusted) if effs_adjusted else 0

                    # Final NaN guard
                    if pd.isna(avg_efficiency):
                        avg_efficiency = 0
                    if pd.isna(avg_efficiency_adjusted):
                        avg_efficiency_adjusted = 0
                else:
                    avg_lead_time = 0
                    p85_lead_time = 0
                    avg_efficiency = 0
                    avg_efficiency_adjusted = 0

                # Store throughput for global percentage calculation
                arrival_count = len(arrivals)
                throughput = len(finished)
                cancelled_count = len(cancelled)
                throughput_by_category[category] = throughput
                
                # Add metrics with category prefix
                prefix = category
                metrics_by_week[week_key][f'{prefix} - Taxa chegada'] = int(arrival_count)
                metrics_by_week[week_key][f'{prefix} - Throughput'] = int(throughput)
                metrics_by_week[week_key][f'{prefix} - Cancelados'] = int(cancelled_count)
                metrics_by_week[week_key][f'{prefix} - Média WIP'] = round(avg_wip, 2)
                metrics_by_week[week_key][f'{prefix} - WIP Age'] = round(avg_wip_age, 2)
                metrics_by_week[week_key][f'{prefix} - Lead Time'] = round(avg_lead_time, 2)
                metrics_by_week[week_key][f'{prefix} - P85 Lead Time'] = round(p85_lead_time, 2)
                metrics_by_week[week_key][f'{prefix} - Eficiência'] = round(avg_efficiency, 2)
                metrics_by_week[week_key][f'{prefix} - Eficiência Ajustada'] = round(avg_efficiency_adjusted, 2)
            
            # Calculate global % Demanda de Falha and % Demanda de Valor
            total_throughput = sum(throughput_by_category.values())
            throughput_defects = throughput_by_category.get('Defeitos', 0)
            throughput_development = throughput_by_category.get('Desenvolvimento', 0)
            
            if total_throughput > 0:
                pct_demand_failure = round((throughput_defects / total_throughput) * 100, 2)
                pct_demand_value = round((throughput_development / total_throughput) * 100, 2)
            else:
                pct_demand_failure = 0
                pct_demand_value = 0
            
            # Add global demand percentages
            metrics_by_week[week_key]['% Demanda de Falha'] = pct_demand_failure
            metrics_by_week[week_key]['% Demanda de Valor'] = pct_demand_value
            if 'Data Cancelled' in df.columns:
                cancelled_total_week = int(len(df[(df['Data Cancelled'] >= week_start) & (df['Data Cancelled'] < week_end)]))
                metrics_by_week[week_key]['Cancelados (semana)'] = cancelled_total_week
    
    return list(metrics_by_week.values())

def detect_wait_stage_columns(df):
    """
    Detect columns that represent waiting stages (not actual work).
    Returns list of column names like 'Ready to...', 'In Staging', etc.
    """
    wait_stage_keywords = {'ready', 'staging', 'waiting', 'pending', 'queue', 'hold'}
    wait_columns = []
    
    for col in df.columns:
        col_lower = col.lower()
        if any(keyword in col_lower for keyword in wait_stage_keywords):
            # Exclude metadata columns
            metadata = {'ready', 'build'}
            if col_lower not in metadata:
                wait_columns.append(col)
    
    return wait_columns

def calculate_enhanced_efficiency(row, wait_columns):
    """
    Calculate enhanced flow efficiency considering:
    - Execution Time: actual work time (In Progress to Done)
    - Blocked Time: time the item was blocked (Blocked Days field)
    - Wait Stage Time: time in intermediate waiting stages (Ready to..., Staging, etc.)
    - Lead Time: total time from Sprint Backlog to Done
    
    Formula:
    Eficiência Ajustada = (Tempo Execução) / (Lead Time - Tempo Bloqueio - Tempo Espera Intermediária)
    
    Returns tuple: (enhanced_efficiency, blocked_days, wait_days)
    """
    try:
        # Get base dates
        sprint_backlog = row.get('Sprint Backlog')
        in_progress = row.get('In Progress')
        done = row.get('Done')
        
        # Validate required dates
        if pd.isna(sprint_backlog) or pd.isna(in_progress) or pd.isna(done):
            return None, None, None
        
        # Calculate times in days
        lead_time_td = done - sprint_backlog
        execution_time_td = done - in_progress

        # Validate timedeltas are not NaT
        if pd.isna(lead_time_td) or pd.isna(execution_time_td):
            return None, None, None

        lead_time = lead_time_td.days
        execution_time = execution_time_td.days

        # Get blocked days as numeric, default to 0
        blocked_days = row.get('Blocked Days', 0)
        try:
            blocked_days = float(blocked_days) if pd.notna(blocked_days) else 0
        except (ValueError, TypeError):
            blocked_days = 0

        # Ensure blocked_days is not NaN after conversion
        if pd.isna(blocked_days):
            blocked_days = 0
        
        # Calculate wait time in intermediate stages
        wait_days = 0
        if wait_columns:
            for wait_col in wait_columns:
                wait_date = row.get(wait_col)
                if pd.notna(wait_date):
                    # Time waiting in this stage = next stage date - this stage date
                    # Find next stage
                    # For now, approximate as days between stages
                    if pd.notna(in_progress):
                        if wait_date < in_progress:
                            # This stage happened before In Progress
                            stage_duration = (in_progress - wait_date).days
                            wait_days += max(0, stage_duration)
        
        # Calculate efficiency
        # Denominator = Lead Time - (non-productive time)
        non_productive_time = blocked_days + wait_days
        productive_window = max(1, lead_time - non_productive_time)  # Avoid division by zero
        
        enhanced_efficiency = execution_time / productive_window if productive_window > 0 else 0
        
        # Clamp to reasonable values (0 to 2, allowing slight overages)
        enhanced_efficiency = min(2.0, max(0.0, enhanced_efficiency))
        
        return enhanced_efficiency, blocked_days, wait_days
        
    except Exception as e:
        return None, None, None

def generate_advanced_flow_metrics(consolidated_data):
    """
    Generate advanced flow indicators:
    - Cycle Time (In Progress duration)
    - Tempo em Backlog (Sprint Backlog to In Progress)
    - Tempo até Primeiro Movimento
    - Taxa de Bloqueio
    - Eficiência Ajustada (considerando bloqueios e tempo de espera intermediário)
    """
    metrics_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        # Filter only completed items (with Done date)
        df_complete = df[df['Done'].notna()].copy()
        
        if df_complete.empty:
            continue
        
        # Detect wait stage columns (Ready to..., Staging, etc.)
        wait_columns = detect_wait_stage_columns(df_complete)
        
        # Cycle Time: In Progress to Done
        df_complete['Cycle Time (dias)'] = (df_complete['Done'] - df_complete['In Progress']).dt.days
        
        # Tempo em Backlog: Sprint Backlog to In Progress
        df_complete['Tempo Backlog (dias)'] = (df_complete['In Progress'] - df_complete['Sprint Backlog']).dt.days
        
        # Tempo até Primeiro Movimento: Sprint Backlog to In Progress
        df_complete['Tempo 1º Movimento (dias)'] = df_complete['Tempo Backlog (dias)']
        
        # Calculate enhanced efficiency for all items
        efficiency_metrics = []
        for _, row in df_complete.iterrows():
            enh_eff, blocked_d, wait_d = calculate_enhanced_efficiency(row, wait_columns)
            efficiency_metrics.append({
                'Enhanced Efficiency': enh_eff,
                'Blocked Days': blocked_d,
                'Wait Days': wait_d
            })
        
        df_efficiency = pd.DataFrame(efficiency_metrics)
        # Drop original columns that would conflict with calculated ones
        cols_to_drop = [c for c in ['Blocked Days', 'Wait Days', 'Enhanced Efficiency'] if c in df_complete.columns]
        df_complete = df_complete.drop(columns=cols_to_drop)
        df_complete = pd.concat([df_complete.reset_index(drop=True), df_efficiency], axis=1)
        
        # Taxa de Bloqueio: % de itens com Blocked = True
        if 'Blocked' in df.columns:
            blocked_count = len(df[df['Blocked'] == True])
            total_count = len(df)
            taxa_bloqueio = (blocked_count / total_count * 100) if total_count > 0 else 0
        else:
            taxa_bloqueio = 0
        
        # Aggregated metrics by category
        for category in df['WorkItemCategory'].unique():
            df_cat = df_complete[df_complete['WorkItemCategory'] == category]
            
            if not df_cat.empty:
                # Calculate enhanced efficiency metrics
                valid_enh_eff = df_cat['Enhanced Efficiency'].dropna()
                avg_enh_efficiency = valid_enh_eff.mean() if len(valid_enh_eff) > 0 else 0

                blocked_valid = pd.to_numeric(df_cat['Blocked Days'], errors='coerce').dropna()
                wait_valid = pd.to_numeric(df_cat['Wait Days'], errors='coerce').dropna()
                avg_blocked_days = float(blocked_valid.mean()) if len(blocked_valid) > 0 else 0.0
                avg_wait_days = float(wait_valid.mean()) if len(wait_valid) > 0 else 0.0

                # Guard against NaN from mean() on empty/invalid data
                if np.isnan(avg_enh_efficiency):
                    avg_enh_efficiency = 0
                if np.isnan(avg_blocked_days):
                    avg_blocked_days = 0
                if np.isnan(avg_wait_days):
                    avg_wait_days = 0

                # Guard against NaN in cycle time and backlog calculations
                ct_mean = float(df_cat['Cycle Time (dias)'].mean())
                ct_median = float(df_cat['Cycle Time (dias)'].median())
                tb_mean = float(df_cat['Tempo Backlog (dias)'].mean())
                t1m_mean = float(df_cat['Tempo 1º Movimento (dias)'].mean())

                metrics_list.append({
                    'Projeto': projeto,
                    'Tipo': category,
                    'Cycle Time Médio (dias)': round(ct_mean if not np.isnan(ct_mean) else 0, 2),
                    'Cycle Time Mediano (dias)': round(ct_median if not np.isnan(ct_median) else 0, 2),
                    'Tempo Backlog Médio (dias)': round(tb_mean if not np.isnan(tb_mean) else 0, 2),
                    'Tempo 1º Movimento Médio (dias)': round(t1m_mean if not np.isnan(t1m_mean) else 0, 2),
                    'Eficiência Ajustada': round(avg_enh_efficiency, 2),
                    'Tempo Bloqueio Médio (dias)': round(avg_blocked_days, 2),
                    'Tempo Espera Intermediária Médio (dias)': round(avg_wait_days, 2),
                    'Taxa de Bloqueio (%)': round(taxa_bloqueio, 2),
                    'Itens Completados': len(df_cat)
                })
    
    return pd.DataFrame(metrics_list) if metrics_list else pd.DataFrame()

def generate_efficiency_wait_time_analysis(consolidated_data):
    """
    Generate detailed analysis of waiting times and efficiency breakdown.
    Shows:
    - Lead Time breakdown: Backlog Time + Execution Time + Blocked Time + Wait Stage Time
    - Efficiency metrics: Simple vs Adjusted
    - Wait time sources for each completed item
    """
    detailed_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        # Filter only completed items
        df_complete = df[df['Done'].notna()].copy()
        
        if df_complete.empty:
            continue
        
        # Detect wait columns
        wait_columns = detect_wait_stage_columns(df_complete)
        
        for idx, row in df_complete.iterrows():
            sprint_backlog = row.get('Sprint Backlog')
            in_progress = row.get('In Progress')
            done = row.get('Done')
            
            if pd.isna(sprint_backlog) or pd.isna(done):
                continue

            effective_in_progress = in_progress if pd.notna(in_progress) else sprint_backlog
            
            # Calculate time components (in days)
            backlog_time = max(0, (effective_in_progress - sprint_backlog).days)
            execution_time = max(0, (done - effective_in_progress).days)
            lead_time = compute_valid_lead_days(done, sprint_backlog)
            if lead_time is None:
                continue
            
            # Get blocked days
            blocked_days = row.get('Blocked Days', 0)
            try:
                blocked_days = float(blocked_days) if pd.notna(blocked_days) else 0
            except (ValueError, TypeError):
                blocked_days = 0
            if pd.isna(blocked_days):
                blocked_days = 0
            
            # Get wait stage time
            wait_stage_time = 0
            wait_stages_detail = []
            for wait_col in wait_columns:
                wait_date = row.get(wait_col)
                if pd.notna(wait_date):
                    # Ensure wait_date is a Timestamp for comparison
                    try:
                        wait_date = pd.Timestamp(wait_date)
                    except:
                        continue  # Skip if can't convert to timestamp
                    
                    if wait_date < effective_in_progress:
                        stage_duration = (effective_in_progress - wait_date).days
                        wait_stage_time += max(0, stage_duration)
                        wait_stages_detail.append(f"{wait_col}: {stage_duration}d")
            
            # Calculate simple and adjusted efficiency
            simple_eff = execution_time / lead_time if lead_time > 0 else 0
            
            non_productive_time = blocked_days + wait_stage_time
            productive_window = max(1, lead_time - non_productive_time)
            adjusted_eff = execution_time / productive_window if productive_window > 0 else 0
            adjusted_eff = min(2.0, max(0.0, adjusted_eff))  # Clamp values
            
            # Other components (time not in backlog, execution, or blocking)
            other_time = max(0, lead_time - backlog_time - execution_time - blocked_days - wait_stage_time)
            
            detailed_list.append({
                'Projeto': projeto,
                'ID': row.get('ID', 'N/A'),
                'Título': str(row.get('Title', ''))[:50],
                'Tipo': row.get('WorkItemCategory', 'Outro'),
                'Lead Time (dias)': lead_time,
                'Tempo Backlog (dias)': backlog_time,
                'Tempo Execução (dias)': execution_time,
                'Tempo Bloqueio (dias)': blocked_days,
                'Tempo Espera Intermediária (dias)': wait_stage_time,
                'Outros Tempos (dias)': other_time,
                'Eficiência Simples': round(simple_eff, 3),
                'Eficiência Ajustada': round(adjusted_eff, 3),
                'Diferença Eficiência': round(adjusted_eff - simple_eff, 3),
                'Detalhes Espera': ', '.join(wait_stages_detail) if wait_stages_detail else 'Nenhuma'
            })
    
    if not detailed_list:
        return pd.DataFrame()
    
    df_result = pd.DataFrame(detailed_list)
    df_result = df_result.sort_values(['Projeto', 'Lead Time (dias)'], ascending=[True, False])
    
    return df_result

def generate_stability_metrics(consolidated_data):
    """
    Generate stability and predictability metrics:
    - Desvio Padrão do Throughput
    - Coeficiente de Variação
    - Lead Time P50, P75, P95
    - Intervalo de Confiança
    """
    start_date = pd.Timestamp('2025-01-01')
    end_date = pd.Timestamp('2026-03-10')
    weeks = pd.date_range(start=start_date, end=end_date, freq=WEEK_DATE_RANGE_FREQ)
    
    metrics_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        throughputs = []
        lead_times = []
        
        # Collect throughput and lead time per week
        for i in range(len(weeks)-1):
            week_start = weeks[i]
            week_end = weeks[i+1]
            
            # Throughput for the week
            finished = df[(df['Done'] >= week_start) & (df['Done'] < week_end)]
            throughputs.append(len(finished))
            
            # Lead times for completed items
            if not finished.empty:
                lt_days = compute_valid_lead_series(finished)
                lead_times.extend(lt_days.tolist())
        
        if throughputs and lead_times:
            throughputs = [t for t in throughputs if t > 0]  # Only weeks with activity
            
            avg_throughput = np.mean(throughputs) if throughputs else 0
            std_throughput = np.std(throughputs) if throughputs else 0
            cv_throughput = (std_throughput / avg_throughput * 100) if avg_throughput > 0 else 0
            
            # Lead time percentiles
            lead_times = sorted([lt for lt in lead_times if lt >= 0])
            
            # Confidence interval (95%)
            margin_error = 1.96 * (std_throughput / np.sqrt(len(throughputs))) if len(throughputs) > 1 else 0
            ic_lower = max(0, avg_throughput - margin_error)
            ic_upper = avg_throughput + margin_error
            
            metrics_list.append({
                'Projeto': projeto,
                'Throughput Médio': round(avg_throughput, 2),
                'Desvio Padrão Throughput': round(std_throughput, 2),
                'Coeficiente Variação (%)': round(cv_throughput, 2),
                'Lead Time P50 (dias)': round(np.percentile(lead_times, 50), 2) if lead_times else 0,
                'Lead Time P75 (dias)': round(np.percentile(lead_times, 75), 2) if lead_times else 0,
                'Lead Time P85 (dias)': round(np.percentile(lead_times, 85), 2) if lead_times else 0,
                'Lead Time P95 (dias)': round(np.percentile(lead_times, 95), 2) if lead_times else 0,
                'Lead Time Médio (dias)': round(np.mean(lead_times), 2) if lead_times else 0,
                'IC 95% Inferior': round(ic_lower, 2),
                'IC 95% Superior': round(ic_upper, 2),
                'Semanas Analisadas': len(throughputs)
            })
    
    return pd.DataFrame(metrics_list) if metrics_list else pd.DataFrame()

def generate_flow_health_metrics(consolidated_data):
    """
    Generate flow health metrics:
    - Ratio Chegada/Throughput
    - Taxa de Conclusão
    - Crescimento de WIP
    - Itens Vencidos
    """
    start_date = pd.Timestamp('2025-01-01')
    end_date = pd.Timestamp('2026-03-10')
    weeks = pd.date_range(start=start_date, end=end_date, freq=WEEK_DATE_RANGE_FREQ)
    
    metrics_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        total_items = len(df)
        completed_items = len(df[df['Done'].notna()])
        initiated_items = len(df[df['In Progress'].notna()])
        
        # Taxa de Conclusão
        taxa_conclusao = (completed_items / total_items * 100) if total_items > 0 else 0
        
        # Collect weekly data
        arrivals_total = 0
        throughput_total = 0
        wip_weeks = []
        lead_times_total = []
        
        for i in range(len(weeks)-2):
            week_start = weeks[i]
            week_end = weeks[i+1]
            week_next_end = weeks[i+2]
            
            # Chegadas
            arrivals = len(df[(df['In Progress'] >= week_start) & (df['In Progress'] < week_end)])
            arrivals_total += arrivals
            
            # Throughput
            finished = len(df[(df['Done'] >= week_start) & (df['Done'] < week_end)])
            throughput_total += finished
            
            # WIP
            wip_count = len(df[
                (df['In Progress'] < week_end) & 
                ((df['Done'] >= week_end) | (df['Done'].isna()))
            ])
            wip_weeks.append(wip_count)
            
            # Lead times
            if finished > 0:
                finished_items = df[(df['Done'] >= week_start) & (df['Done'] < week_end)]
                lead_times_total.extend(compute_valid_lead_series(finished_items).tolist())
        
        # Ratio Chegada/Throughput
        ratio_chegada = (arrivals_total / throughput_total) if throughput_total > 0 else 0
        
        # Crescimento de WIP (tendência)
        wip_growth = 0
        if len(wip_weeks) > 2:
            wip_growth = ((wip_weeks[-1] - wip_weeks[0]) / wip_weeks[0] * 100) if wip_weeks[0] > 0 else 0
        
        # Itens Vencidos (Lead Time > P85)
        if lead_times_total:
            p85_lead = np.percentile(lead_times_total, 85)
            valid_lt_all = compute_valid_lead_series(df)
            overdue_items = int((valid_lt_all > p85_lead).sum()) if not valid_lt_all.empty else 0
        else:
            overdue_items = 0
        
        metrics_list.append({
            'Projeto': projeto,
            'Total de Itens': total_items,
            'Itens Completados': completed_items,
            'Itens Iniciados': initiated_items,
            'Taxa Conclusão (%)': round(taxa_conclusao, 2),
            'Ratio Chegada/Throughput': round(ratio_chegada, 2),
            'Crescimento WIP (%)': round(wip_growth, 2),
            'Itens Vencidos': overdue_items,
            'Total Chegadas': arrivals_total,
            'Total Throughput': throughput_total
        })
    
    return pd.DataFrame(metrics_list) if metrics_list else pd.DataFrame()

def generate_dimensional_analysis(consolidated_data):
    """
    Generate dimensional analysis:
    - Throughput por Projeto
    - Throughput por Responsável
    - Throughput por Componente
    - Throughput por Prioridade
    """
    analysis_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        # Completed items
        df_complete = df[df['Done'].notna()].copy()
        
        # By Project (overall)
        analysis_list.append({
            'Dimensão': 'Por Projeto',
            'Categoria': projeto,
            'Throughput': len(df_complete),
            'Taxa_Defeitos': round((len(df_complete[df_complete['WorkItemCategory'] == 'Defeitos']) / len(df_complete) * 100), 2) if len(df_complete) > 0 else 0
        })
        
        # By Responsável
        if 'Responsável' in df.columns:
            for resp in df['Responsável'].unique():
                if pd.notna(resp):
                    df_resp = df_complete[df_complete['Responsável'] == resp]
                    analysis_list.append({
                        'Dimensão': 'Por Responsável',
                        'Categoria': f"{projeto} - {resp}",
                        'Throughput': len(df_resp),
                        'Taxa_Defeitos': round((len(df_resp[df_resp['WorkItemCategory'] == 'Defeitos']) / len(df_resp) * 100), 2) if len(df_resp) > 0 else 0
                    })
        
        # By Componente
        if 'Componentes' in df.columns:
            for comp in df['Componentes'].unique():
                if pd.notna(comp):
                    df_comp = df_complete[df_complete['Componentes'] == comp]
                    analysis_list.append({
                        'Dimensão': 'Por Componente',
                        'Categoria': f"{projeto} - {comp}",
                        'Throughput': len(df_comp),
                        'Taxa_Defeitos': round((len(df_comp[df_comp['WorkItemCategory'] == 'Defeitos']) / len(df_comp) * 100), 2) if len(df_comp) > 0 else 0
                    })
        
        # By Prioridade
        if 'Prioridade' in df.columns:
            for prio in df['Prioridade'].unique():
                if pd.notna(prio):
                    df_prio = df_complete[df_complete['Prioridade'] == prio]
                    analysis_list.append({
                        'Dimensão': 'Por Prioridade',
                        'Categoria': f"{projeto} - {prio}",
                        'Throughput': len(df_prio),
                        'Taxa_Defeitos': round((len(df_prio[df_prio['WorkItemCategory'] == 'Defeitos']) / len(df_prio) * 100), 2) if len(df_prio) > 0 else 0
                    })
    
    return pd.DataFrame(analysis_list) if analysis_list else pd.DataFrame()

def generate_type_analysis(consolidated_data):
    """
    Generate type analysis:
    - % por Tipo de Problema
    - Lead Time por Tipo
    - Throughput por Subtipo
    """
    analysis_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        df_complete = df[df['Done'].notna()].copy()
        total_complete = len(df_complete)
        
        # By WorkItemCategory
        for category in df['WorkItemCategory'].unique():
            df_cat = df_complete[df_complete['WorkItemCategory'] == category]
            
            if not df_cat.empty:
                lead_times = compute_valid_lead_series(df_cat)
                
                analysis_list.append({
                    'Projeto': projeto,
                    'Tipo': category,
                    'Ordem': 0,
                    '% do Total': round((len(df_cat) / total_complete * 100), 2) if total_complete > 0 else 0,
                    'Throughput': len(df_cat),
                    'Lead Time Médio (dias)': round(lead_times.mean(), 2) if not lead_times.empty else 0,
                    'Lead Time P85 (dias)': round(lead_times.quantile(0.85), 2) if not lead_times.empty else 0
                })
        
        # By WorkItemSubType
        for subtype in df['WorkItemSubType'].unique():
            df_sub = df_complete[df_complete['WorkItemSubType'] == subtype]
            
            if not df_sub.empty:
                lead_times = compute_valid_lead_series(df_sub)
                
                analysis_list.append({
                    'Projeto': projeto,
                    'Tipo': f"  {subtype}",
                    'Ordem': 1,
                    '% do Total': round((len(df_sub) / total_complete * 100), 2) if total_complete > 0 else 0,
                    'Throughput': len(df_sub),
                    'Lead Time Médio (dias)': round(lead_times.mean(), 2) if not lead_times.empty else 0,
                    'Lead Time P85 (dias)': round(lead_times.quantile(0.85), 2) if not lead_times.empty else 0
                })
    
    # Sort by project and order
    if analysis_list:
        df_result = pd.DataFrame(analysis_list)
        df_result = df_result.sort_values(['Projeto', 'Ordem']).drop('Ordem', axis=1)
        return df_result
    
    return pd.DataFrame()

def generate_quality_metrics(consolidated_data):
    """
    Generate quality and rework metrics:
    - Debt Ratio
    - Razão Valor/Custo
    - Eficiência Média
    - Itens descartados e taxa de descarte
    """
    metrics_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        df_complete = df[df['Done'].notna()].copy()
        
        # Count by category
        defects = len(df_complete[df_complete['WorkItemCategory'] == 'Defeitos'])
        development = len(df_complete[df_complete['WorkItemCategory'] == 'Desenvolvimento'])
        total = len(df_complete)
        discarded = int(df_complete.apply(is_discarded_item, axis=1).sum()) if total > 0 else 0
        
        # Debt Ratio
        debt_ratio = (defects / total * 100) if total > 0 else 0
        value_ratio = (development / total * 100) if total > 0 else 0
        
        # Value/Cost Ratio
        valor_custo = (development / defects) if defects > 0 else 0
        
        # Eficiência média (já calculada)
        if not df_complete.empty:
            effs = []
            for _, row in df_complete.iterrows():
                total_time = (row['Done'] - row['Sprint Backlog']).days
                execution_time = (row['Done'] - row['In Progress']).days
                if total_time > 0:
                    effs.append(execution_time / total_time)
            avg_efficiency = np.mean(effs) if effs else 0
        else:
            avg_efficiency = 0
        
        metrics_list.append({
            'Projeto': projeto,
            'Total Itens Completados': total,
            'Defeitos Concluídos': defects,
            'Desenvolvimento Concluído': development,
            'Itens Descartados': discarded,
            'Taxa Descarte (%)': round((discarded / total * 100), 2) if total > 0 else 0,
            'Debt Ratio (%)': round(debt_ratio, 2),
            'Value Ratio (%)': round(value_ratio, 2),
            'Razão Valor/Custo': round(valor_custo, 2),
            'Eficiência Média': round(avg_efficiency, 2)
        })
    
    return pd.DataFrame(metrics_list) if metrics_list else pd.DataFrame()

def generate_trend_analysis(consolidated_data):
    """
    Generate trend analysis:
    - Throughput Trend (4-week rolling average)
    - WIP Trend
    - Lead Time Trend
    """
    start_date = pd.Timestamp('2025-01-01')
    end_date = pd.Timestamp('2026-03-10')
    weeks = pd.date_range(start=start_date, end=end_date, freq=WEEK_DATE_RANGE_FREQ)
    
    metrics_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        throughputs = []
        wips = []
        week_dates = []
        
        for i in range(len(weeks)-1):
            week_start = weeks[i]
            week_end = weeks[i+1]
            
            # Throughput
            finished = df[(df['Done'] >= week_start) & (df['Done'] < week_end)]
            throughputs.append(len(finished))
            
            # WIP
            wip_count = len(df[
                (df['In Progress'] < week_end) & 
                ((df['Done'] >= week_end) | (df['Done'].isna()))
            ])
            wips.append(wip_count)
            
            week_dates.append(week_start.date())

        # Calculate rolling averages (4 weeks)
        from collections import deque
        window_size = 4

        for i, date in enumerate(week_dates):
            start_idx = max(0, i - window_size + 1)

            # Throughput rolling average
            throughput_slice = [t for t in throughputs[start_idx:i+1] if t > 0]
            throughput_avg = np.mean(throughput_slice) if throughput_slice else 0

            # WIP rolling average
            wip_avg = np.mean(wips[start_idx:i+1]) if wips[start_idx:i+1] else 0

            # Trend direction
            if i >= 1:
                throughput_trend = "↑" if throughput_avg > throughputs[i-1] else ("↓" if throughput_avg < throughputs[i-1] else "→")
            else:
                throughput_trend = "→"

            metrics_list.append({
                'Projeto': projeto,
                'Semana': date,
                'Throughput Semanal': int(throughputs[i]),
                'Throughput Médio (4s)': round(throughput_avg, 2),
                'Trend Throughput': throughput_trend,
                'WIP Médio (4s)': round(wip_avg, 2),
            })
    
    return pd.DataFrame(metrics_list) if metrics_list else pd.DataFrame()

def generate_throughput_by_type_weekly(consolidated_data):
    """
    Generate throughput by item type per project per week.
    Returns DataFrame with: Projeto, Semana, Tipo, Throughput, P85 Lead Time, Eficiência Média
    Includes trend indicators for each type.
    """
    start_date = pd.Timestamp('2025-01-01')
    end_date = pd.Timestamp('2026-03-10')
    weeks = pd.date_range(start=start_date, end=end_date, freq=WEEK_DATE_RANGE_FREQ)
    
    metrics_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        # For each type
        for item_type in df['WorkItemCategory'].unique():
            if pd.isna(item_type):
                continue
                
            df_type = df[df['WorkItemCategory'] == item_type].copy()
            
            # Track throughputs for trend calculation
            throughputs_by_week = []
            
            for i in range(len(weeks)-1):
                week_start = weeks[i]
                week_end = weeks[i+1]
                
                # Finished items of this type in this week
                finished = df_type[(df_type['Done'] >= week_start) & (df_type['Done'] < week_end)]
                throughput = len(finished)
                throughputs_by_week.append(throughput)
                
                if throughput > 0 or i == 0:  # Include all weeks or at least first week
                    # Calculate metrics
                    if not finished.empty:
                        lead_times = compute_valid_lead_series(finished)
                        p85_lead_time = lead_times.quantile(0.85) if not lead_times.empty else 0
                        
                        # Efficiency
                        effs = []
                        for _, row in finished.iterrows():
                            total_time = (row['Done'] - row['Sprint Backlog']).days
                            execution_time = (row['Done'] - row['In Progress']).days
                            if total_time > 0:
                                effs.append(execution_time / total_time)
                        avg_efficiency = np.mean(effs) if effs else 0
                    else:
                        p85_lead_time = 0
                        avg_efficiency = 0
                    
                    # Calculate trend (compare with previous week)
                    if i > 0:
                        prev_throughput = throughputs_by_week[i-1]
                        if throughput > prev_throughput:
                            trend = "↑"
                        elif throughput < prev_throughput:
                            trend = "↓"
                        else:
                            trend = "→"
                    else:
                        trend = "→"
                    
                    # Calculate momentum (acceleration/deceleration over last 3 weeks)
                    if i >= 3:
                        momentum_slice = throughputs_by_week[i-3:i]
                        recent_avg = np.mean(momentum_slice) if momentum_slice else 0
                        momentum = throughput - recent_avg if recent_avg > 0 else 0
                    else:
                        momentum = 0
                    
                    metrics_list.append({
                        'Projeto': projeto,
                        'Semana': week_start.date(),
                        'Tipo Item': item_type,
                        'Throughput': int(throughput),
                        'P85 Lead Time (dias)': round(p85_lead_time, 2),
                        'Eficiência': round(avg_efficiency, 2),
                        'Trend': trend,
                        'Momentum': round(momentum, 2)
                    })
    
    df_result = pd.DataFrame(metrics_list)
    if not df_result.empty:
        df_result = df_result.sort_values(['Projeto', 'Tipo Item', 'Semana'])
    
    return df_result

def generate_comprehensive_trend_analysis(consolidated_data):
    """
    Generate comprehensive trend analysis for ALL indicators on a weekly basis.
    Includes: Throughput, WIP, Lead Time, Efficiency, Cycle Time, Backlog Time
    with momentum, direction, and acceleration indicators.
    """
    start_date = pd.Timestamp('2025-01-01')
    end_date = pd.Timestamp('2026-03-10')
    weeks = pd.date_range(start=start_date, end=end_date, freq=WEEK_DATE_RANGE_FREQ)
    
    metrics_list = []
    
    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        # Initialize history containers
        throughputs_hist = []
        wips_hist = []
        lead_times_hist = []
        cycle_times_hist = []
        backlog_times_hist = []
        efficiencies_hist = []
        p85_lead_time_hist = []
        
        for i in range(len(weeks)-1):
            week_start = weeks[i]
            week_end = weeks[i+1]
            
            # Finished items
            finished = df[(df['Done'] >= week_start) & (df['Done'] < week_end)]
            
            # WIP
            wip_count = len(df[
                (df['In Progress'] < week_end) & 
                ((df['Done'] >= week_end) | (df['Done'].isna()))
            ])
            
            # Throughput
            throughput = len(finished)
            throughputs_hist.append(throughput)
            wips_hist.append(wip_count)
            
            # Lead time metrics
            if not finished.empty:
                lead_times = compute_valid_lead_series(finished)
                cycle_times = (finished['Done'] - finished['In Progress']).dt.days
                backlog_times = (finished['In Progress'] - finished['Sprint Backlog']).dt.days
                
                avg_lead_time = lead_times.mean() if not lead_times.empty else 0
                p85_lead_time = lead_times.quantile(0.85) if not lead_times.empty else 0
                avg_cycle_time = cycle_times.mean()
                avg_backlog_time = backlog_times.mean()
                
                # Efficiency
                effs = []
                for _, row in finished.iterrows():
                    total_time = (row['Done'] - row['Sprint Backlog']).days
                    execution_time = (row['Done'] - row['In Progress']).days
                    if total_time > 0:
                        effs.append(execution_time / total_time)
                avg_efficiency = np.mean(effs) if effs else 0
            else:
                avg_lead_time = 0
                p85_lead_time = 0
                avg_cycle_time = 0
                avg_backlog_time = 0
                avg_efficiency = 0
            
            lead_times_hist.append(avg_lead_time)
            cycle_times_hist.append(avg_cycle_time)
            backlog_times_hist.append(avg_backlog_time)
            efficiencies_hist.append(avg_efficiency)
            p85_lead_time_hist.append(p85_lead_time)
            
            # Calculate rolling averages (4 weeks)
            window_size = 4
            start_idx = max(0, i - window_size + 1)
            
            throughput_slice = [t for t in throughputs_hist[start_idx:i+1] if t > 0]
            throughput_avg = np.mean(throughput_slice) if throughput_slice else 0
            
            wip_avg = np.mean(wips_hist[start_idx:i+1]) if wips_hist[start_idx:i+1] else 0
            
            lead_time_slice = [lt for lt in lead_times_hist[start_idx:i+1] if lt > 0]
            lead_time_avg = np.mean(lead_time_slice) if lead_time_slice else 0
            
            cycle_time_slice = [ct for ct in cycle_times_hist[start_idx:i+1] if ct > 0]
            cycle_time_avg = np.mean(cycle_time_slice) if cycle_time_slice else 0
            
            backlog_time_slice = [bt for bt in backlog_times_hist[start_idx:i+1] if bt > 0]
            backlog_time_avg = np.mean(backlog_time_slice) if backlog_time_slice else 0
            
            eff_slice = [e for e in efficiencies_hist[start_idx:i+1] if e > 0]
            eff_avg = np.mean(eff_slice) if eff_slice else 0
            
            p85_slice = [p for p in p85_lead_time_hist[start_idx:i+1] if p > 0]
            p85_avg = np.mean(p85_slice) if p85_slice else 0
            
            # Calculate trends
            def calc_trend(current, previous):
                if current > previous * 1.05:
                    return "↑"
                elif current < previous * 0.95:
                    return "↓"
                else:
                    return "→"
            
            # Calculate momentum (acceleration/deceleration over last 3 weeks)
            def calc_momentum(history, window=3):
                if len(history) < window:
                    return 0
                momentum_data = [h for h in history[-window:] if h > 0]
                if not momentum_data:  # If all values are <= 0
                    return 0
                recent_avg = np.mean(momentum_data)
                current = history[-1] if history[-1] > 0 else recent_avg
                return current - recent_avg if recent_avg > 0 else 0
            
            throughput_momentum = calc_momentum(throughputs_hist, 3)
            wip_momentum = calc_momentum(wips_hist, 3)
            lead_time_momentum = calc_momentum(lead_times_hist, 3)
            
            metrics_list.append({
                'Projeto': projeto,
                'Semana': week_start.date(),
                'Throughput': int(throughput),
                'Throughput Médio (4s)': round(throughput_avg, 2),
                'Throughput Trend': calc_trend(throughput, throughputs_hist[i-1]) if i > 0 else "→",
                'Throughput Momentum': round(throughput_momentum, 2),
                'WIP': int(wip_count),
                'WIP Médio (4s)': round(wip_avg, 2),
                'WIP Trend': calc_trend(wip_count, wips_hist[i-1]) if i > 0 else "→",
                'WIP Momentum': round(wip_momentum, 2),
                'Lead Time': round(avg_lead_time, 2),
                'Lead Time Médio (4s)': round(lead_time_avg, 2),
                'Lead Time Trend': calc_trend(avg_lead_time, lead_times_hist[i-1]) if i > 0 else "→",
                'Lead Time Momentum': round(lead_time_momentum, 2),
                'P85 Lead Time': round(p85_lead_time, 2),
                'P85 Lead Time Médio (4s)': round(p85_avg, 2),
                'Cycle Time': round(avg_cycle_time, 2),
                'Cycle Time Médio (4s)': round(cycle_time_avg, 2),
                'Backlog Time': round(avg_backlog_time, 2),
                'Backlog Time Médio (4s)': round(backlog_time_avg, 2),
                'Eficiência': round(avg_efficiency, 2),
                'Eficiência Média (4s)': round(eff_avg, 2)
            })
    
    return pd.DataFrame(metrics_list) if metrics_list else pd.DataFrame()

def prepare_powerbi_dimensions(consolidated_data):
    """
    Prepare dimension tables for Power BI model:
    - Dim_Projeto
    - Dim_Data
    - Dim_Tipo
    - Dim_Responsavel
    - Dim_Componente
    - Dim_Prioridade
    - Dim_ClasseServico
    """
    dim_projeto = []
    dim_tipo = []
    dim_responsavel = []
    dim_componente = []
    dim_prioridade = []
    dim_classe_servico = []
    
    for projeto, df in consolidated_data.items():
        # Projeto dimension
        if projeto not in [p['NomeProjeto'] for p in dim_projeto]:
            dim_projeto.append({
                'ProjetoID': len(dim_projeto) + 1,
                'NomeProjeto': projeto
            })
        
        # Tipo dimension
        for tipo in df['WorkItemCategory'].unique():
            if pd.notna(tipo) and tipo not in [t['Tipo'] for t in dim_tipo]:
                dim_tipo.append({
                    'TipoID': len(dim_tipo) + 1,
                    'Tipo': tipo
                })
        
        # Responsável dimension
        if 'Responsável' in df.columns:
            for resp in df['Responsável'].unique():
                if pd.notna(resp) and resp not in [r['Responsavel'] for r in dim_responsavel]:
                    dim_responsavel.append({
                        'ResponsavelID': len(dim_responsavel) + 1,
                        'Responsavel': str(resp)
                    })
        
        # Componente dimension
        if 'Componentes' in df.columns:
            for comp in df['Componentes'].unique():
                if pd.notna(comp) and comp not in [c['Componente'] for c in dim_componente]:
                    dim_componente.append({
                        'ComponenteID': len(dim_componente) + 1,
                        'Componente': str(comp)
                    })
        
        # Prioridade dimension
        if 'Prioridade' in df.columns:
            for prio in df['Prioridade'].unique():
                if pd.notna(prio) and prio not in [p['Prioridade'] for p in dim_prioridade]:
                    dim_prioridade.append({
                        'PrioridadeID': len(dim_prioridade) + 1,
                        'Prioridade': str(prio)
                    })

        # Classe de servico dimension (RF-11)
        for _, row in df.iterrows():
            classe = classify_service_class(row, CLASS_OF_SERVICE_RULES)
            if classe not in [c['ClasseServico'] for c in dim_classe_servico]:
                dim_classe_servico.append({
                    'ClasseServicoID': len(dim_classe_servico) + 1,
                    'ClasseServico': classe
                })
    
    # Create Data dimension (from earliest date to latest)
    all_dates = []
    for proj, df in consolidated_data.items():
        for col in ['Sprint Backlog', 'In Progress', 'Done', 'Data Cancelled']:
            if col in df.columns:
                all_dates.extend(df[col][df[col].notna()].tolist())
    
    if all_dates:
        min_date = pd.Timestamp(min(all_dates)).date()
        max_date = pd.Timestamp(max(all_dates)).date()
        date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        
        dim_data = []
        for i, date in enumerate(date_range):
            dim_data.append({
                'DataID': i + 1,
                'Data': date.date(),
                'Ano': date.year,
                'Mes': date.month,
                'MesNome': date.strftime('%B'),
                'Semana': date.isocalendar()[1],
                'DiaSemana': date.day_name(),
                'AnoMes': date.strftime('%Y-%m')
            })
    else:
        dim_data = pd.DataFrame()
    
    return {
        'Dim_Projeto': pd.DataFrame(dim_projeto),
        'Dim_Data': pd.DataFrame(dim_data) if dim_data else pd.DataFrame(),
        'Dim_Tipo': pd.DataFrame(dim_tipo),
        'Dim_Responsavel': pd.DataFrame(dim_responsavel) if dim_responsavel else pd.DataFrame(),
        'Dim_Componente': pd.DataFrame(dim_componente) if dim_componente else pd.DataFrame(),
        'Dim_Prioridade': pd.DataFrame(dim_prioridade) if dim_prioridade else pd.DataFrame(),
        'Dim_ClasseServico': pd.DataFrame(dim_classe_servico) if dim_classe_servico else pd.DataFrame()
    }

def prepare_powerbi_fact_table(consolidated_data, dimensions):
    """
    Create fact table for Power BI
    Each row = one work item with all relevant metrics
    Including WIP metrics per person
    """
    fact_records = []
    
    dim_projeto_map = {row['NomeProjeto']: row['ProjetoID'] for _, row in dimensions['Dim_Projeto'].iterrows()}
    dim_tipo_map = {row['Tipo']: row['TipoID'] for _, row in dimensions['Dim_Tipo'].iterrows()}
    dim_resp_map = {row['Responsavel']: row['ResponsavelID'] for _, row in dimensions['Dim_Responsavel'].iterrows()} if not dimensions['Dim_Responsavel'].empty else {}
    dim_comp_map = {row['Componente']: row['ComponenteID'] for _, row in dimensions['Dim_Componente'].iterrows()} if not dimensions['Dim_Componente'].empty else {}
    dim_prio_map = {row['Prioridade']: row['PrioridadeID'] for _, row in dimensions['Dim_Prioridade'].iterrows()} if not dimensions['Dim_Prioridade'].empty else {}
    dim_classe_map = {row['ClasseServico']: row['ClasseServicoID'] for _, row in dimensions['Dim_ClasseServico'].iterrows()} if not dimensions['Dim_ClasseServico'].empty else {}
    
    # Get today's date for WIP calculation
    today = pd.Timestamp.now().date()
    
    for projeto, df in consolidated_data.items():
        # Detect wait stage columns for this project's dataframe
        wait_columns = detect_wait_stage_columns(df)

        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')

        # Weekly rates used by queue-based flow efficiency (1 - lambda/mu).
        rates_df = df.copy()
        rates_df['_EffectiveInProgress'] = rates_df.apply(resolve_in_progress_date, axis=1)
        rates_df['_ArrivalWeek'] = rates_df['_EffectiveInProgress'].apply(week_start_monday)
        rates_df['_DoneWeek'] = rates_df['Done'].apply(week_start_monday) if 'Done' in rates_df.columns else pd.NaT
        arrivals_by_week = rates_df.dropna(subset=['_ArrivalWeek']).groupby('_ArrivalWeek').size().to_dict()
        throughput_by_week = rates_df.dropna(subset=['_DoneWeek']).groupby('_DoneWeek').size().to_dict()
        
        for idx, row in df.iterrows():
            projeto_id = dim_projeto_map.get(projeto, 1)
            tipo_id = dim_tipo_map.get(row.get('WorkItemCategory', 'Outro'), 1)
            
            # Get responsável
            responsavel = row.get('Responsável', 'Não Atribuído')
            responsavel_name = str(responsavel) if pd.notna(responsavel) and str(responsavel) != 'nan' else 'Não Atribuído'
            resp_id = dim_resp_map.get(responsavel_name, None) if responsavel_name != 'Não Atribuído' else None
            
            # Get componente
            componente = row.get('Componentes', 'N/A')
            comp_id = dim_comp_map.get(str(componente), None) if componente and str(componente) != 'nan' else None
            
            # Get prioridade
            prioridade = row.get('Prioridade', 'Normal')
            prio_id = dim_prio_map.get(str(prioridade), None) if prioridade and str(prioridade) != 'nan' else None
            classe_servico = classify_service_class(row, CLASS_OF_SERVICE_RULES)
            classe_servico_id = dim_classe_map.get(classe_servico, None)
            
            # Calculate metrics
            sprint_backlog_date = resolve_backlog_date(row)
            in_progress_date = row.get('In Progress')
            done_date = row.get('Done')
            cancelled_date = row.get('Data Cancelled')

            effective_in_progress_date = resolve_in_progress_date(row)

            backlog_days = (effective_in_progress_date - sprint_backlog_date).days if pd.notna(sprint_backlog_date) and pd.notna(effective_in_progress_date) else None
            eligible_time_metrics = is_time_eligible_done_row(row)
            cycle_days = (done_date - effective_in_progress_date).days if pd.notna(effective_in_progress_date) and pd.notna(done_date) else None
            lead_days = compute_valid_lead_days(done_date, sprint_backlog_date)
            if not eligible_time_metrics:
                cycle_days = None
                lead_days = None
            lead_time_inconsistente = (
                pd.notna(sprint_backlog_date)
                and pd.notna(done_date)
                and lead_days is None
                and eligible_time_metrics
            )
            
            week_ref = week_start_monday(done_date if pd.notna(done_date) else effective_in_progress_date)
            if pd.notna(week_ref):
                arrivals_w = arrivals_by_week.get(week_ref, 0)
                throughput_w = throughput_by_week.get(week_ref, 0)
                _, efficiency = calculate_flow_efficiency(arrivals_w, throughput_w)
            else:
                efficiency = None

            # Keep blocked/wait decomposition, but efficiency now follows queue rule.
            _, blocked_days_v2, wait_days_v2 = calculate_enhanced_efficiency(row, wait_columns)
            adjusted_eff = efficiency

            is_completed = 1 if pd.notna(done_date) else 0
            is_cancelled = 1 if pd.notna(cancelled_date) else 0
            is_blocked = 1 if row.get('Blocked') == True else 0
            is_discarded = 1 if is_discarded_item(row) else 0
            
            # Calculate WIP status (is item currently in progress but not done?)
            is_wip = 0
            wip_dias = 0
            if pd.notna(effective_in_progress_date) and pd.isna(done_date):
                # Item started but not finished = in WIP
                is_wip = 1
                wip_dias = (pd.Timestamp(today) - effective_in_progress_date).days
            elif pd.notna(effective_in_progress_date) and pd.notna(done_date):
                # Item was completed, check if it was in WIP during execution
                is_wip = 0  # No longer in WIP
                wip_dias = cycle_days if cycle_days else 0
            
            fact_records.append({
                'ItemID': str(row.get('ID', idx)),
                'ProjetoID': projeto_id,
                'TipoID': tipo_id,
                'ResponsavelID': resp_id,
                'ResponsavelNome': responsavel_name,
                'ComponenteID': comp_id,
                'PrioridadeID': prio_id,
                'ClasseServicoID': classe_servico_id,
                'DataCriacaoID': pd.to_datetime(row.get('Created'), dayfirst=True, errors='coerce') if pd.notna(row.get('Created')) else None,
                'DataInicioProgressoID': effective_in_progress_date if pd.notna(effective_in_progress_date) else None,
                'DataConclucaoID': done_date if pd.notna(done_date) else None,
                'DataCancelamentoID': cancelled_date if pd.notna(cancelled_date) else None,
                'Titulo': str(row.get('Title', '')),
                'WorkItemSubType': str(row.get('WorkItemSubType', 'Outro')),
                'ClasseServico': classe_servico,
                'TempoBacklog_Dias': backlog_days,
                'TempoExecucao_Dias': cycle_days,
                'LeadTime_Dias': lead_days,
                'Eficiencia': efficiency,
                'EficienciaAjustada': adjusted_eff,
                'TempoBloqueioDias': blocked_days_v2,
                'TempoEsperaIntermediariaDias': wait_days_v2,
                'Concluido': is_completed,
                'Cancelado': is_cancelled,
                'ElegivelTempoConcluido': 1 if eligible_time_metrics else 0,
                'ConcluidoSemCancelamento': 1 if (is_completed and eligible_time_metrics) else 0,
                'Bloqueado': is_blocked,
                'Descartado': is_discarded,
                'StoryPoints': row.get('Story Points'),
                'DataBacklog': sprint_backlog_date,
                'DataInProgress': effective_in_progress_date,
                'DataDone': done_date,
                'DataCancelled': cancelled_date,
                'LeadTimeInconsistente': lead_time_inconsistente,
                'EmWIP': is_wip,
                'WIP_Dias': wip_dias
            })
    
    return pd.DataFrame(fact_records)

def save_powerbi_optimized_model(consolidated_data, output_folder, bottleneck_csv_files=None):
    """
    Save optimized Power BI data model to Excel
    With separate sheets for dimensions and facts
    """
    print("\n" + "="*70)
    print("PREPARANDO MODELO OTIMIZADO PARA POWER BI")
    print("="*70)
    
    print("Gerando tabelas de dimensão...")
    dimensions = prepare_powerbi_dimensions(consolidated_data)
    
    print("Gerando tabela de fatos...")
    fact_table = prepare_powerbi_fact_table(consolidated_data, dimensions)
    print("Gerando tabela de gargalos...")
    bottleneck_table = load_bottleneck_table_from_csv_files(bottleneck_csv_files or [])
    if bottleneck_table.empty:
        bottleneck_table = build_bottleneck_table_from_fact(fact_table, dimensions)
    
    # Create output file
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_folder, f"PowerBI_Model_{timestamp}.xlsx")
    
    print(f"\nSalvando modelo em: {output_file}")
    
    with pd.ExcelWriter(output_file, engine=excel_engine) as writer:
        # Write Dimensions
        dimensions['Dim_Projeto'].to_excel(writer, sheet_name='Dim_Projeto', index=False)
        dimensions['Dim_Data'].to_excel(writer, sheet_name='Dim_Data', index=False)
        dimensions['Dim_Tipo'].to_excel(writer, sheet_name='Dim_Tipo', index=False)
        
        if not dimensions['Dim_Responsavel'].empty:
            dimensions['Dim_Responsavel'].to_excel(writer, sheet_name='Dim_Responsavel', index=False)
        
        if not dimensions['Dim_Componente'].empty:
            dimensions['Dim_Componente'].to_excel(writer, sheet_name='Dim_Componente', index=False)
        
        if not dimensions['Dim_Prioridade'].empty:
            dimensions['Dim_Prioridade'].to_excel(writer, sheet_name='Dim_Prioridade', index=False)

        if not dimensions['Dim_ClasseServico'].empty:
            dimensions['Dim_ClasseServico'].to_excel(writer, sheet_name='Dim_ClasseServico', index=False)
        
        # Write Fact Table
        fact_table.to_excel(writer, sheet_name='Fato_Items', index=False)
        if not bottleneck_table.empty:
            bottleneck_table.to_excel(writer, sheet_name='Fato_Gargalos', index=False)

    copy_latest_artifact(output_file, os.path.join(output_folder, "PowerBI_Model_latest.xlsx"))
    
    print("Modelo salvo com sucesso!")
    print(f"\nEstrutura do Modelo Power BI:")
    print(f"\nDIMENSÕES (Dimension Tables):")
    print(f"  - Dim_Projeto: {len(dimensions['Dim_Projeto'])} registros")
    print(f"  - Dim_Data: {len(dimensions['Dim_Data'])} registros")
    print(f"  - Dim_Tipo: {len(dimensions['Dim_Tipo'])} registros")
    if not dimensions['Dim_Responsavel'].empty:
        print(f"  - Dim_Responsavel: {len(dimensions['Dim_Responsavel'])} registros")
    if not dimensions['Dim_Componente'].empty:
        print(f"  - Dim_Componente: {len(dimensions['Dim_Componente'])} registros")
    if not dimensions['Dim_Prioridade'].empty:
        print(f"  - Dim_Prioridade: {len(dimensions['Dim_Prioridade'])} registros")
    if not dimensions['Dim_ClasseServico'].empty:
        print(f"  - Dim_ClasseServico: {len(dimensions['Dim_ClasseServico'])} registros")
    
    print(f"\nFATOS (Fact Table):")
    print(f"  - Fato_Items: {len(fact_table)} registros (work items)")
    if not bottleneck_table.empty:
        print(f"  - Fato_Gargalos: {len(bottleneck_table)} registros")
    
    print(f"\nColunas Principais da Tabela de Fatos:")
    print(f"  - Chaves Estrangeiras: ProjetoID, TipoID, ResponsavelID, ComponenteID, PrioridadeID")
    print(f"  - Métricas: LeadTime_Dias, TempoBacklog_Dias, TempoExecucao_Dias, Eficiencia")
    print(f"  - Indicadores: Concluido, Bloqueado, StoryPoints")
    
    print(f"\n{'='*70}")
    print(f"RELACIONAMENTOS SUGERIDOS NO PODER BI:")
    print(f"{'='*70}")
    print(f"Fato_Items[ProjetoID] → Dim_Projeto[ProjetoID]")
    print(f"Fato_Items[TipoID] → Dim_Tipo[TipoID]")
    print(f"Fato_Items[ResponsavelID] → Dim_Responsavel[ResponsavelID]")
    print(f"Fato_Items[ComponenteID] → Dim_Componente[ComponenteID]")
    print(f"Fato_Items[PrioridadeID] → Dim_Prioridade[PrioridadeID]")
    print(f"Fato_Items[ClasseServicoID] → Dim_ClasseServico[ClasseServicoID]")
    print(f"Fato_Items[DataDone] → Dim_Data[Data] (para análises por data)")
    
    return output_file

def generate_wip_per_person(consolidated_data):
    """
    Generate WIP metrics per person, per week, per project.
    Returns a DataFrame with: Projeto, Semana, Responsável, WIP_Médio, Items_Ativos, 
    breakdown by WorkItemCategory (Desenvolvimento, Defeitos, Outro)
    """
    # Define Reporting Period (Weekly, Monday to Monday)
    start_date = pd.Timestamp('2025-01-01') 
    end_date = pd.Timestamp('2026-03-10')
    weeks = pd.date_range(start=start_date, end=end_date, freq=WEEK_DATE_RANGE_FREQ)
    
    wip_data = []
    
    # Process each project
    for projeto, df in consolidated_data.items():
        # Remove duplicates
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        
        # Process each week
        for i in range(len(weeks)-1):
            week_start = weeks[i]
            week_end = weeks[i+1]
            
            # Get people in this project
            if 'Responsável' not in df.columns:
                continue
                
            responsaveis = df['Responsável'].dropna().unique()
            
            # For each person
            for responsavel in responsaveis:
                df_person = df[df['Responsável'] == responsavel].copy()
                
                # Calculate WIP for this person during the week
                # WIP = items that were "In Progress" during at least part of the week
                daily_wips = []
                for d in range(7):
                    day = week_start + pd.Timedelta(days=d)
                    
                    # Count items that were in progress on this day
                    # Condition: Started before or on this day AND (not finished OR finished after this day)
                    in_progress_mask = df_person['In Progress'] <= day
                    not_yet_done = (df_person['Done'].isna()) | (df_person['Done'] > day)
                    
                    wip_count = len(df_person[in_progress_mask & not_yet_done])
                    daily_wips.append(wip_count)
                
                avg_wip = np.mean(daily_wips) if daily_wips else 0
                max_wip = max(daily_wips) if daily_wips else 0
                
                # Get active items at week end
                in_progress_mask = df_person['In Progress'] < week_end
                not_yet_done = (df_person['Done'].isna()) | (df_person['Done'] >= week_end)
                
                active_items = df_person[in_progress_mask & not_yet_done]
                active_at_end = len(active_items)
                
                # Calculate WIP by WorkItemCategory at week end
                wip_by_type = {}
                if 'WorkItemCategory' in df_person.columns:
                    for item_type in active_items['WorkItemCategory'].unique():
                        count = len(active_items[active_items['WorkItemCategory'] == item_type])
                        if pd.notna(item_type):
                            wip_by_type[item_type] = count
                
                # Create composition string (e.g., "2 Desenvolvimento, 1 Defeitos")
                composition = ', '.join([f"{count} {tipo}" for tipo, count in sorted(wip_by_type.items())])
                
                # Only add if there was activity
                if avg_wip > 0 or active_at_end > 0:
                    row_dict = {
                        'Projeto': projeto,
                        'Semana': week_start.date(),
                        'Responsável': responsavel,
                        'WIP_Médio': round(avg_wip, 2),
                        'WIP_Máximo': max_wip,
                        'Items_Ativos_FimSemana': active_at_end,
                        'Composição_WIP': composition if composition else 'N/A',
                        'Dias_Semana': 7
                    }
                    
                    # Add individual type counts as separate columns
                    for tipo in wip_by_type:
                        col_name = f'WIP_{tipo}'
                        row_dict[col_name] = wip_by_type[tipo]
                    
                    wip_data.append(row_dict)
    
    if not wip_data:
        return pd.DataFrame()
    
    df_wip = pd.DataFrame(wip_data)
    
    # Fill NaN values in WIP type columns with 0
    type_cols = [col for col in df_wip.columns if col.startswith('WIP_')]
    for col in type_cols:
        df_wip[col] = df_wip[col].fillna(0).astype(int)
    
    df_wip = df_wip.sort_values(['Projeto', 'Semana', 'Responsável'])
    
    return df_wip


def build_flow_policies_table(consolidated_data, policies):
    rows = []
    for projeto in sorted(consolidated_data.keys()):
        p = get_project_policy(projeto, policies)
        rows.append({
            'Projeto': projeto,
            'WIP Limit': p.get('wip_limit'),
            'WIP Age SLE (dias)': p.get('wip_age_sle_days'),
            'Blocked Days Limit': p.get('blocked_days_limit'),
            'Flow Pressure Limit': p.get('flow_pressure_limit'),
        })
    return pd.DataFrame(rows)


def generate_policy_violations(consolidated_data, policies):
    """Generate weekly policy compliance view (RF-02)."""
    start_date = pd.Timestamp('2024-01-01')
    end_date = pd.Timestamp('2026-03-10')
    weeks = pd.date_range(start=start_date, end=end_date, freq=WEEK_DATE_RANGE_FREQ)
    rows = []

    for projeto, df in consolidated_data.items():
        policy = get_project_policy(projeto, policies)
        wip_limit = policy.get('wip_limit')
        wip_age_limit = policy.get('wip_age_sle_days')
        blocked_limit = policy.get('blocked_days_limit')
        pressure_limit = policy.get('flow_pressure_limit')

        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')

        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]
            arrivals = df[(df['In Progress'] >= week_start) & (df['In Progress'] < week_end)]
            finished = df[(df['Done'] >= week_start) & (df['Done'] < week_end)]
            wip_items = df[(df['In Progress'] < week_end) & ((df['Done'] >= week_end) | (df['Done'].isna()))]
            wip = len(wip_items)
            throughput = len(finished)
            pressure = (len(arrivals) / throughput) if throughput > 0 else np.nan
            wip_age = (week_end - wip_items['In Progress']).dt.days.mean() if not wip_items.empty else 0

            blocked_over_limit = 0
            if blocked_limit is not None and 'Blocked Days' in wip_items.columns:
                blocked_days = pd.to_numeric(wip_items['Blocked Days'], errors='coerce').fillna(0)
                blocked_over_limit = int((blocked_days > float(blocked_limit)).sum())

            breach_wip = (wip_limit is not None) and (wip > float(wip_limit))
            breach_wip_age = (wip_age_limit is not None) and (wip_age > float(wip_age_limit))
            breach_pressure = (
                pressure_limit is not None and pd.notna(pressure) and pressure > float(pressure_limit)
            )
            breach_blocked = blocked_over_limit > 0
            breach_count = int(breach_wip) + int(breach_wip_age) + int(breach_pressure) + int(breach_blocked)

            rows.append({
                'Projeto': projeto,
                'Week Start': week_start.date(),
                'WIP': wip,
                'WIP Age Médio (dias)': round(float(wip_age), 2) if pd.notna(wip_age) else 0.0,
                'Chegadas': len(arrivals),
                'Throughput': throughput,
                'Pressão de Fluxo': round(float(pressure), 3) if pd.notna(pressure) else np.nan,
                'Blocked>Limite': blocked_over_limit,
                'Violou WIP Limit': int(breach_wip),
                'Violou WIP Age SLE': int(breach_wip_age),
                'Violou Flow Pressure': int(breach_pressure),
                'Violou Blocked Days': int(breach_blocked),
                'Total Violações': breach_count,
                'Status Politica': 'Crítico' if breach_count >= 2 else ('Atenção' if breach_count == 1 else 'OK'),
            })

    return pd.DataFrame(rows)


def generate_executive_report_artifacts(
    output_folder,
    timestamp,
    df_flow_health,
    df_quality,
    df_policy_violations,
):
    """Export executive report (RF-14) in XLSX/CSV/Markdown with trends and risk evidence."""
    if df_flow_health.empty:
        return pd.DataFrame(), None, None

    policy_counts = (
        df_policy_violations.groupby('Projeto', as_index=False)['Total Violações'].sum()
        if not df_policy_violations.empty
        else pd.DataFrame(columns=['Projeto', 'Total Violações'])
    )

    summary = df_flow_health.merge(
        df_quality[['Projeto', 'Debt Ratio (%)', 'Taxa Descarte (%)']] if not df_quality.empty else pd.DataFrame(columns=['Projeto']),
        on='Projeto',
        how='left',
    )
    summary = summary.merge(policy_counts, on='Projeto', how='left')
    summary['Total Violações'] = summary['Total Violações'].fillna(0).astype(int)
    summary['Debt Ratio (%)'] = summary.get('Debt Ratio (%)', pd.Series(dtype='float64')).fillna(0)
    summary['Taxa Descarte (%)'] = summary.get('Taxa Descarte (%)', pd.Series(dtype='float64')).fillna(0)

    def classify_risk(row):
        risks = 0
        if row.get('Ratio Chegada/Throughput', 0) > 1:
            risks += 1
        if row.get('Crescimento WIP (%)', 0) > 10:
            risks += 1
        if row.get('Debt Ratio (%)', 0) > 35:
            risks += 1
        if row.get('Taxa Descarte (%)', 0) > 10:
            risks += 1
        if row.get('Total Violações', 0) > 0:
            risks += 1
        if risks >= 3:
            return 'Crítico'
        if risks >= 1:
            return 'Atenção'
        return 'OK'

    summary['Risco Executivo'] = summary.apply(classify_risk, axis=1)
    summary = summary.sort_values(['Risco Executivo', 'Projeto'], ascending=[False, True]).reset_index(drop=True)

    csv_path = os.path.join(output_folder, f"executive_report_{timestamp}.csv")
    md_path = os.path.join(output_folder, f"executive_report_{timestamp}.md")
    summary.to_csv(csv_path, index=False, encoding='utf-8')

    lines = [
        "# Relatório Executivo de Métricas de Fluxo",
        "",
        f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Resumo por Projeto",
        "",
        "| Projeto | Ratio Chegada/Throughput | Crescimento WIP (%) | Debt Ratio (%) | Taxa Descarte (%) | Violações de Política | Risco Executivo |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row.get('Projeto','')} | {row.get('Ratio Chegada/Throughput',0):.2f} | "
            f"{row.get('Crescimento WIP (%)',0):.2f} | {row.get('Debt Ratio (%)',0):.2f} | "
            f"{row.get('Taxa Descarte (%)',0):.2f} | {int(row.get('Total Violações',0))} | "
            f"{row.get('Risco Executivo','')} |"
        )
    lines.extend(["", "## Evidências usadas", "", "- Saúde de fluxo (chegada/throughput, crescimento de WIP).", "- Qualidade (Debt Ratio e taxa de descarte).", "- Violações de políticas de fluxo (WIP, WIP Age SLE, bloqueios e pressão de fluxo)."])
    Path(md_path).write_text("\n".join(lines), encoding='utf-8')

    return summary, csv_path, md_path


def _safe_pct(numerator, denominator):
    if denominator is None or denominator == 0:
        return 0.0
    return float(numerator) / float(denominator) * 100.0


def _safe_ratio(numerator, denominator):
    if denominator is None or denominator == 0:
        return np.nan
    return float(numerator) / float(denominator)


def generate_systemic_pattern_detection(consolidated_data, rules):
    """
    RF-08/RF-09: detect configurable systemic patterns from weekly flow signals.
    Returns:
    - detailed detections per project/week/pattern
    - summary per project/pattern
    """
    start_date = pd.Timestamp('2025-01-01')
    end_date = pd.Timestamp('2026-03-10')
    weeks = pd.date_range(start=start_date, end=end_date, freq=WEEK_DATE_RANGE_FREQ)

    pattern_labels = {
        "urgencia_cronica": "Times operando em estado de urgência",
        "burnout": "Times em processo de burnout",
        "confianca_comprometida": "Times comprometendo a confiança do cliente",
        "problema_sistemico_fluxo": "Times com problemas sistêmicos de fluxo",
        "atrasos_desperdicios": "Times com atrasos e desperdícios",
        "estagnacao": "Times estagnados",
        "compromisso_prematuro": "Times com compromisso prematuro",
    }

    details = []

    for projeto, df in consolidated_data.items():
        if 'ID' in df.columns:
            df = df.drop_duplicates(subset=['ID'], keep='first')
        if df.empty:
            continue

        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]

            arrivals = df[(df['In Progress'] >= week_start) & (df['In Progress'] < week_end)]
            finished = df[(df['Done'] >= week_start) & (df['Done'] < week_end)]
            wip_items = df[(df['In Progress'] < week_end) & ((df['Done'] >= week_end) | (df['Done'].isna()))]

            throughput = len(finished)
            inflow = len(arrivals)
            flow_pressure = _safe_ratio(inflow, throughput)
            wip = len(wip_items)
            wip_tp_ratio = _safe_ratio(wip, throughput)

            lead_times = compute_valid_lead_series(finished)
            lt_p85 = float(lead_times.quantile(0.85)) if not lead_times.empty else 0.0
            lt_p50 = float(lead_times.quantile(0.50)) if not lead_times.empty else 0.0
            predictability_ratio = _safe_ratio(lt_p85, lt_p50) if lt_p50 > 0 else np.nan

            type_counts = finished['WorkItemCategory'].value_counts() if 'WorkItemCategory' in finished.columns else pd.Series(dtype='int64')
            defects = int(type_counts.get('Defeitos', 0))
            failure_demand_pct = _safe_pct(defects, throughput)

            expedite_arrivals = 0
            if not arrivals.empty:
                cls = arrivals.apply(lambda r: classify_service_class(r, CLASS_OF_SERVICE_RULES), axis=1)
                expedite_arrivals = int(cls.apply(is_highest_alias).sum())
            expedite_pct = _safe_pct(expedite_arrivals, inflow)

            blocked_rate = 0.0
            if not wip_items.empty and 'Blocked' in wip_items.columns:
                blocked_rate = _safe_pct(int((wip_items['Blocked'] == True).sum()), len(wip_items))

            discard_rate = 0.0
            if throughput > 0:
                discarded = int(finished.apply(is_discarded_item, axis=1).sum())
                discard_rate = _safe_pct(discarded, throughput)

            wip_age = (week_end - wip_items['In Progress']).dt.days.mean() if not wip_items.empty else 0.0
            wip_age_over_p85 = _safe_ratio(wip_age, lt_p85) if lt_p85 > 0 else np.nan

            signals = {
                "expedite_pct": float(expedite_pct),
                "flow_pressure": float(flow_pressure) if pd.notna(flow_pressure) else np.nan,
                "failure_demand_pct": float(failure_demand_pct),
                "predictability_ratio": float(predictability_ratio) if pd.notna(predictability_ratio) else np.nan,
                "lead_time_p85": float(lt_p85),
                "wip_tp_ratio": float(wip_tp_ratio) if pd.notna(wip_tp_ratio) else np.nan,
                "blocked_rate": float(blocked_rate),
                "discard_rate": float(discard_rate),
                "wip_age_over_p85": float(wip_age_over_p85) if pd.notna(wip_age_over_p85) else np.nan,
                "inflow": inflow,
                "throughput": throughput,
                "wip": wip,
            }

            for pattern_key, threshold_map in rules.items():
                rule_hits = []
                for metric, threshold in threshold_map.items():
                    if metric.endswith('_max'):
                        signal_name = metric[:-4]
                        value = signals.get(signal_name, np.nan)
                        if pd.notna(value) and value <= float(threshold):
                            rule_hits.append(f"{signal_name}<={threshold}")
                    else:
                        signal_name = metric.replace('_min', '')
                        value = signals.get(signal_name, np.nan)
                        if pd.notna(value) and value >= float(threshold):
                            rule_hits.append(f"{signal_name}>={threshold}")

                min_hits = max(1, int(np.ceil(len(threshold_map) * 0.6)))
                matched = len(rule_hits) >= min_hits
                if not matched:
                    continue

                severity = 'Atenção'
                if len(rule_hits) >= len(threshold_map):
                    severity = 'Crítico'

                details.append({
                    'Projeto': projeto,
                    'Week Start': week_start.date(),
                    'Padrão': pattern_labels.get(pattern_key, pattern_key),
                    'PatternKey': pattern_key,
                    'Severidade': severity,
                    'Regras Acionadas': " | ".join(rule_hits),
                    'Highest (%)': round(signals['expedite_pct'], 2),
                    'Pressure (λ/μ)': round(signals['flow_pressure'], 3) if pd.notna(signals['flow_pressure']) else np.nan,
                    'Failure Demand (%)': round(signals['failure_demand_pct'], 2),
                    'Predictability (P85/P50)': round(signals['predictability_ratio'], 2) if pd.notna(signals['predictability_ratio']) else np.nan,
                    'Lead Time P85': round(signals['lead_time_p85'], 2),
                    'WIP/Throughput': round(signals['wip_tp_ratio'], 2) if pd.notna(signals['wip_tp_ratio']) else np.nan,
                    'Blocked (%)': round(signals['blocked_rate'], 2),
                    'Discard (%)': round(signals['discard_rate'], 2),
                    'WIP Age / LT P85': round(signals['wip_age_over_p85'], 2) if pd.notna(signals['wip_age_over_p85']) else np.nan,
                    'Chegadas': inflow,
                    'Throughput': throughput,
                    'WIP': wip,
                })

    details_df = pd.DataFrame(details)
    if details_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    summary_df = (
        details_df.groupby(['Projeto', 'Padrão', 'Severidade'], as_index=False)
        .size()
        .rename(columns={'size': 'Ocorrências'})
        .sort_values(['Projeto', 'Ocorrências'], ascending=[True, False])
    )
    return details_df, summary_df

def generate_lead_time_consolidated_tab(consolidated_data, df_stability, df_trends_comprehensive, df_efficiency_analysis, df_advanced_flow=None):
    """
    Build a single 'Lead Time' tab consolidating lead time data from four sources:
      - Section A (Resumo por Projeto): percentiles P50/P75/P85/P95 + mean, from df_stability
      - Section B (Métricas de Fluxo): cycle time, backlog time, efficiency by category, from df_advanced_flow
      - Section C (Tendência Semanal): weekly LT avg, P85, trend, momentum, from df_trends_comprehensive
      - Section D (Detalhamento por Item): per-item LT breakdown, from df_efficiency_analysis
    """
    frames = []

    # Section A: summary stats per project
    if df_stability is not None and not df_stability.empty:
        summary_cols = [
            'Projeto',
            'Lead Time P50 (dias)',
            'Lead Time P75 (dias)',
            'Lead Time P85 (dias)',
            'Lead Time P95 (dias)',
            'Lead Time Médio (dias)',
            'Semanas Analisadas',
        ]
        available = [c for c in summary_cols if c in df_stability.columns]
        df_a = df_stability[available].copy()
        df_a.insert(0, 'Section', 'Resumo por Projeto')
        frames.append(df_a)

    # Section B: flow metrics (cycle time, backlog time, efficiency) by project/category
    if df_advanced_flow is not None and not df_advanced_flow.empty:
        flow_cols = [
            'Projeto', 'Tipo',
            'Cycle Time Médio (dias)',
            'Cycle Time Mediano (dias)',
            'Tempo Backlog Médio (dias)',
            'Tempo 1º Movimento Médio (dias)',
            'Eficiência Ajustada',
            'Tempo Bloqueio Médio (dias)',
            'Tempo Espera Intermediária Médio (dias)',
            'Taxa de Bloqueio (%)',
            'Itens Completados',
        ]
        available = [c for c in flow_cols if c in df_advanced_flow.columns]
        df_b = df_advanced_flow[available].copy()
        df_b.insert(0, 'Section', 'Métricas de Fluxo')
        frames.append(df_b)

    # Section C: weekly trends
    if df_trends_comprehensive is not None and not df_trends_comprehensive.empty:
        trend_cols = [
            'Projeto',
            'Semana',
            'Lead Time',
            'Lead Time Médio (4s)',
            'Lead Time Trend',
            'Lead Time Momentum',
            'P85 Lead Time',
            'P85 Lead Time Médio (4s)',
        ]
        available = [c for c in trend_cols if c in df_trends_comprehensive.columns]
        df_c = df_trends_comprehensive[available].copy()
        df_c.insert(0, 'Section', 'Tendência Semanal')
        frames.append(df_c)

    # Section D: item-level breakdown
    if df_efficiency_analysis is not None and not df_efficiency_analysis.empty:
        item_cols = [
            'Projeto', 'ID', 'Título', 'Tipo',
            'Lead Time (dias)',
            'Tempo Backlog (dias)',
            'Tempo Execução (dias)',
            'Tempo Bloqueio (dias)',
            'Tempo Espera Intermediária (dias)',
            'Outros Tempos (dias)',
            'Eficiência Simples',
            'Eficiência Ajustada',
        ]
        available = [c for c in item_cols if c in df_efficiency_analysis.columns]
        df_d = df_efficiency_analysis[available].copy()
        df_d.insert(0, 'Section', 'Detalhamento por Item')
        frames.append(df_d)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def process_multiple_csv_files(input_folder, output_folder):
    """
    Process all CSV files and consolidate into a single sheet with advanced metrics.
    Layout: Projeto | Week Start | Desenvolvimento-metrics | Defeitos-metrics | Outro-metrics
    """
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Find all CSV files in the input folder
    all_csv_files = sorted(glob.glob(os.path.join(input_folder, "*.csv")))
    csv_files, ignored_csv_files = select_latest_csv_per_project(all_csv_files)
    bottleneck_csv_files = select_latest_bottleneck_csv_per_project(all_csv_files)
    
    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return
    
    print(f"Found {len(all_csv_files)} CSV files in folder")
    print(f"Selected {len(csv_files)} latest CSV files for processing")
    print(f"Selected {len(bottleneck_csv_files)} bottleneck CSV files for model sheet")
    if ignored_csv_files:
        print(f"Ignoring {len(ignored_csv_files)} older CSV files")
        for old_file in ignored_csv_files[:10]:
            print(f"  - {Path(old_file).name}")
        if len(ignored_csv_files) > 10:
            print("  - ...")
    print()
    
    # Consolidate ALL metrics from all projects
    all_metrics_list = []
    
    processed_count = 0
    error_count = 0
    error_log = []
    
    # Load and consolidate all data from all CSV files first
    print("Loading and consolidating data from all CSV files...")
    consolidated_data = load_and_consolidate_all_data(csv_files)
    processed_count = len(consolidated_data)
    
    if not consolidated_data:
        print("No data loaded from CSV files!")
        return
    
    print(f"Successfully loaded data for {len(consolidated_data)} projects")
    
    # Generate metrics from consolidated data (avoiding duplicates)
    print("Generating metrics...")
    all_metrics_list = generate_consolidated_dashboard(consolidated_data)
    
    # Convert to DataFrame
    df_consolidated = pd.DataFrame(all_metrics_list)
    
    if df_consolidated.empty:
        print("No data to process!")
        return
    
    # Sort by Projeto and Week Start
    df_consolidated = df_consolidated.sort_values(['Projeto', 'Week Start'])
    
    # Reorder columns: Projeto, Week Start first
    base_cols = ['Projeto', 'Week Start']
    metric_cols = [col for col in df_consolidated.columns if col not in base_cols]
    metric_cols_sorted = sorted(metric_cols)
    
    df_consolidated = df_consolidated[base_cols + metric_cols_sorted]
    
    # Format Week Start as date
    df_consolidated['Week Start'] = df_consolidated['Week Start'].dt.date
    
    # Create Excel file with timestamp to avoid conflicts
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_folder, f"dashboard_output_{timestamp}.xlsx")
    bottlenecks_workbook = None
    
    # Try to remove old file if exists
    try:
        import time
        if os.path.exists(output_file):
            os.remove(output_file)
            time.sleep(0.5)
    except Exception as e:
        print(f"Warning: Could not remove old file: {e}")
    
    # Generate advanced metrics
    print("Generating advanced metrics...")
    
    df_advanced_flow = generate_advanced_flow_metrics(consolidated_data)
    df_stability = generate_stability_metrics(consolidated_data)
    df_flow_health = generate_flow_health_metrics(consolidated_data)
    df_dimensional = generate_dimensional_analysis(consolidated_data)
    df_types = generate_type_analysis(consolidated_data)
    df_quality = generate_quality_metrics(consolidated_data)
    df_trends = generate_trend_analysis(consolidated_data)
    df_wip_person = generate_wip_per_person(consolidated_data)
    
    # New comprehensive trend analysis
    print("Generating comprehensive trend analysis...")
    df_trends_comprehensive = generate_comprehensive_trend_analysis(consolidated_data)
    df_throughput_by_type = generate_throughput_by_type_weekly(consolidated_data)
    df_flow_policies = build_flow_policies_table(consolidated_data, FLOW_POLICIES)
    df_policy_violations = generate_policy_violations(consolidated_data, FLOW_POLICIES)
    df_pattern_details, df_pattern_summary = generate_systemic_pattern_detection(consolidated_data, PATTERN_RULES)
    
    # Generate efficiency and wait time analysis
    print("Generating efficiency and wait time analysis...")
    df_efficiency_analysis = generate_efficiency_wait_time_analysis(consolidated_data)

    # Generate consolidated Lead Time tab
    print("Generating consolidated lead time tab...")
    df_lead_time_consolidated = generate_lead_time_consolidated_tab(
        consolidated_data,
        df_stability=df_stability,
        df_trends_comprehensive=df_trends_comprehensive,
        df_efficiency_analysis=df_efficiency_analysis,
        df_advanced_flow=df_advanced_flow,
    )

    # Generate executive report artifacts (RF-14)
    print("Generating executive report artifacts...")
    df_executive_summary, executive_csv, executive_md = generate_executive_report_artifacts(
        output_folder=output_folder,
        timestamp=timestamp,
        df_flow_health=df_flow_health,
        df_quality=df_quality,
        df_policy_violations=df_policy_violations,
    )
    
    # Save Power BI optimized model
    print("\nOptimizing data model for Power BI...")
    powerbi_output = save_powerbi_optimized_model(
        consolidated_data,
        output_folder,
        bottleneck_csv_files=bottleneck_csv_files,
    )

    # Requested artifact: consolidate selected *_bottlenecks.csv files in one workbook.
    bottleneck_table_from_csv = load_bottleneck_table_from_csv_files(bottleneck_csv_files)
    if bottleneck_table_from_csv.empty:
        print("Aviso: não foi possível consolidar *_bottlenecks.csv (sem dados válidos).")
    else:
        bottlenecks_workbook = save_consolidated_bottlenecks_workbook(
            bottleneck_table=bottleneck_table_from_csv,
            output_folder=output_folder,
            timestamp=timestamp,
        )
    
    # Replace NaN with 0 in numeric columns before writing to Excel
    for df_to_clean in [df_consolidated, df_efficiency_analysis, df_lead_time_consolidated]:
        if df_to_clean is not None and not df_to_clean.empty:
            numeric_cols = df_to_clean.select_dtypes(include=[np.number]).columns
            df_to_clean[numeric_cols] = df_to_clean[numeric_cols].fillna(0)

    # Write all sheets to Excel
    with pd.ExcelWriter(output_file, engine=excel_engine) as writer:
        # Main Dashboard
        df_consolidated.to_excel(writer, sheet_name='Dashboard', index=False)

        # Advanced Metrics - Stability
        df_stability.to_excel(writer, sheet_name='Adv - Estabilidade', index=False)
        
        # Advanced Metrics - Flow Health
        df_flow_health.to_excel(writer, sheet_name='Adv - Saúde Fluxo', index=False)
        
        # Advanced Metrics - Quality
        df_quality.to_excel(writer, sheet_name='Adv - Qualidade', index=False)
        
        # Dimensional Analysis
        df_dimensional.to_excel(writer, sheet_name='Análise Dimensional', index=False)
        
        # Type Analysis
        df_types.to_excel(writer, sheet_name='Análise Tipos', index=False)
        
        # Trend Analysis
        df_trends.to_excel(writer, sheet_name='Tendências', index=False)
        
        # Comprehensive Trend Analysis with momentum
        if not df_trends_comprehensive.empty:
            df_trends_comprehensive.to_excel(writer, sheet_name='Tendências Completas', index=False)
        
        # Throughput by Type Weekly
        if not df_throughput_by_type.empty:
            df_throughput_by_type.to_excel(writer, sheet_name='Throughput por Tipo', index=False)
        
        # Efficiency and Wait Time Analysis
        if not df_efficiency_analysis.empty:
            df_efficiency_analysis.to_excel(writer, sheet_name='Análise Eficiência', index=False)

        # Consolidated Lead Time tab
        if not df_lead_time_consolidated.empty:
            df_lead_time_consolidated.to_excel(writer, sheet_name='Lead Time', index=False)
        
        # WIP per Person
        if not df_wip_person.empty:
            df_wip_person.to_excel(writer, sheet_name='WIP por Pessoa', index=False)

        # RF-02: explicit flow policies and compliance tracking
        if not df_flow_policies.empty:
            df_flow_policies.to_excel(writer, sheet_name='Políticas Fluxo', index=False)
        if not df_policy_violations.empty:
            df_policy_violations.to_excel(writer, sheet_name='Violacoes Politicas', index=False)

        # RF-14: executive report inside workbook
        if not df_executive_summary.empty:
            df_executive_summary.to_excel(writer, sheet_name='Relatorio Executivo', index=False)

        # RF-08/RF-09: systemic pattern detection
        if not df_pattern_details.empty:
            df_pattern_details.to_excel(writer, sheet_name='Padrões Sistêmicos', index=False)
        if not df_pattern_summary.empty:
            df_pattern_summary.to_excel(writer, sheet_name='Resumo Padrões', index=False)

    copy_latest_artifact(output_file, os.path.join(output_folder, "dashboard_output_latest.xlsx"))
    
    print(f"\n{'='*70}")
    print(f"Dashboard completo salvo em: {output_file}")
    print(f"{'='*70}")
    print(f"Processado: {processed_count} arquivos | Linhas Base: {len(df_consolidated)} | Erros: {error_count}")
    
    print(f"\nMODELO POWER BI (Otimizado para Importação):")
    print(f"Arquivo: {powerbi_output}")
    print(f"Estrutura: Tabelas relacionadas (Fato + Dimensões)")
    if bottlenecks_workbook:
        print(f"\nPlanilha única de gargalos:")
        print(f"Arquivo: {bottlenecks_workbook}")
    if executive_csv and executive_md:
        print(f"\nRelatórios executivos exportados:")
        print(f"  - CSV: {executive_csv}")
        print(f"  - Markdown: {executive_md}")
    
    # Show column structure
    print(f"\nEstrutura de Abas Criadas:")
    print(f"\n1. Dashboard (Original + APRIMORAMENTOS)")
    print(f"   - Projeto, Week Start")
    print(f"   - Desenvolvimento, Defeitos, Outro:")
    print(f"     * Taxa chegada, Throughput, WIP, WIP Age")
    print(f"     * Lead Time, P85 Lead Time")
    print(f"     * Eficiência Simples (original)")
    print(f"     * Eficiência Ajustada (desconta bloqueios e espera)")
    print(f"   - % Demanda de Falha / % Demanda de Valor")
    
    print(f"\n2. Adv - Fluxo (APRIMORADO)")
    print(f"   - Cycle Time Médio e Mediano")
    print(f"   - Tempo em Backlog Médio")
    print(f"   - Tempo até Primeiro Movimento")
    print(f"   - Eficiência Ajustada (desconta tempo de bloqueio e espera)")
    print(f"   - Tempo de Bloqueio Médio")
    print(f"   - Tempo de Espera Intermediária Médio")
    print(f"   - Taxa de Bloqueio (%)")
    
    print(f"\n3. Adv - Estabilidade")
    print(f"   - Desvio Padrão do Throughput")
    print(f"   - Coeficiente de Variação (%)")
    print(f"   - Lead Time P50, P75, P95")
    print(f"   - Intervalo de Confiança 95%")
    
    print(f"\n4. Adv - Saúde Fluxo")
    print(f"   - Taxa Conclusão (%)")
    print(f"   - Ratio Chegada/Throughput")
    print(f"   - Crescimento WIP (%)")
    print(f"   - Itens Vencidos")
    
    print(f"\n5. Adv - Qualidade")
    print(f"   - Debt Ratio (% Defeitos)")
    print(f"   - Razão Valor/Custo")
    print(f"   - Eficiência Média")
    
    print(f"\n6. Análise Dimensional")
    print(f"   - Throughput por Projeto, Responsável, Componente, Prioridade")
    print(f"   - Taxa de Defeitos por dimensão")
    
    print(f"\n7. Análise Tipos")
    print(f"   - % por Tipo de Problema (Bug, Feature, Tarefa, Suporte)")
    print(f"   - Lead Time por Tipo")
    print(f"   - Throughput por Subtipo")
    
    print(f"\n8. Tendências")
    print(f"   - Throughput semanal e média móvel (4 semanas)")
    print(f"   - Trend Direction (↑ ↓ →)")
    print(f"   - WIP e Lead Time média móvel")
    
    print(f"\n9. Tendências Completas (NOVO)")
    print(f"   - Throughput com Trend e Momentum")
    print(f"   - WIP com Trend e Momentum")
    print(f"   - Lead Time com Trend e Momentum")
    print(f"   - Cycle Time (média móvel 4s)")
    print(f"   - Backlog Time (média móvel 4s)")
    print(f"   - Eficiência com análise de tendência")
    print(f"   - P85 Lead Time com média móvel")
    
    print(f"\n10. Throughput por Tipo (NOVO)")
    print(f"   - Throughput semanal segmentado por tipo de item")
    print(f"   - P85 Lead Time por tipo")
    print(f"   - Eficiência por tipo")
    print(f"   - Trend Direction (↑ ↓ →) para cada tipo")
    print(f"   - Momentum (aceleração/desaceleração)")
    
    print(f"\n11. Análise Eficiência (NOVO - Detalhado por Item)")
    print(f"   - ID, Projeto, Tipo de trabalho")
    print(f"   - Lead Time com breakdown por componente:")
    print(f"     * Tempo em Backlog (Sprint Backlog → In Progress)")
    print(f"     * Tempo de Execução (In Progress → Done)")
    print(f"     * Tempo de Bloqueio (Blocked Days)")
    print(f"     * Tempo em Espera Intermediária (Ready to..., Staging, etc.)")
    print(f"     * Outros Tempos (não contabilizados)")
    print(f"   - Eficiência Simples vs Ajustada")
    print(f"   - Diferença de Eficiência (ganho com ajuste)")
    print(f"   - Detalhes de fontes de espera")
    
    print(f"\n12. WIP por Pessoa")
    print(f"   - WIP Médio semanal por pessoa")
    print(f"   - WIP Máximo durante a semana")
    print(f"   - Items Ativos no fim da semana")
    print(f"   - Segmentado por Projeto e Responsável")
    
    # Save error log if there are errors
    if error_log:
        error_log_file = os.path.join(output_folder, "processing_errors.txt")
        with open(error_log_file, 'w', encoding='utf-8') as f:
            f.write("Processing Error Log\n")
            f.write("=" * 70 + "\n\n")
            for file_path, error in error_log:
                f.write(f"File: {file_path}\n")
                f.write(f"Error: {error}\n")
                f.write("-" * 70 + "\n")
        print(f"Error log saved to: {error_log_file}")
    
    return output_file

def resolve_data_folder():
    env_candidates = [
        os.getenv('FLOW_PMO_DATA_DIR', '').strip(),
        os.getenv('DATA_FOLDER', '').strip(),
    ]

    if platform.system() == 'Windows':
        default_candidates = [
            r'C:\Users\W1 TI\OneDrive - W1\Documentos\Dados',
        ]
    else:
        home = os.path.expanduser('~')
        default_candidates = [
            os.path.join(home, 'Documents', 'dados'),
            os.path.join(home, 'Documents', 'Dados'),
            os.path.join(home, 'Library', 'CloudStorage', 'OneDrive-W1', 'Documentos', 'Dados'),
        ]

    for raw in [*env_candidates, *default_candidates]:
        if not raw:
            continue
        candidate = os.path.abspath(raw)
        if os.path.isdir(candidate):
            return candidate

    return os.path.abspath(default_candidates[0])


DATA_FOLDER = resolve_data_folder()
input_folder = DATA_FOLDER
output_folder = DATA_FOLDER
print(f"Usando DATA_FOLDER para métricas: {DATA_FOLDER}")

# Tenta remover arquivo antigo se existir
import os
try:
    os.remove(os.path.join(output_folder, "dashboard_output.xlsx"))
except:
    pass

process_multiple_csv_files(input_folder, output_folder)
