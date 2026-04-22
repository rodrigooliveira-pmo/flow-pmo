import pandas as pd
import numpy as np
from datetime import datetime

from shared.text_utils import normalize_text


def safe_read_sheet(excel_file, sheet_name, default_cols):
    if sheet_name in excel_file.sheet_names:
        return pd.read_excel(excel_file, sheet_name=sheet_name)
    return pd.DataFrame(columns=default_cols)


def load_model_data(model_file):
    """Load and process the main model data."""
    xls = pd.ExcelFile(model_file)
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
    if 'Responsavel' not in fato.columns:
        fato['Responsavel'] = ''

    return {
        'dim_projeto': dim_projeto,
        'dim_tipo': dim_tipo,
        'dim_responsavel': dim_responsavel,
        'dim_prioridade': dim_prioridade,
        'dim_classe_servico': dim_classe_servico,
        'fato': fato,
        'fato_gargalos': fato_gargalos,
    }


def resolve_service_class(classe_servico, prioridade):
    """Use explicit service classes first; fallback to priority instead of generic Standard."""
    classe_text = ''
    if pd.notna(classe_servico):
        classe_text = str(classe_servico).strip()

    normalized_class = canonicalize_highest_label(classe_text)
    if normalized_class == 'Highest':
        return normalized_class

    classe_norm = ''.join(ch for ch in classe_text.lower() if ch.isalnum() or ch.isspace()).strip()
    if classe_text and classe_norm and classe_norm not in {'standard', 'padrao', 'normal', 'default'}:
        return canonicalize_highest_label(classe_text)

    if pd.notna(prioridade):
        prioridade_text = canonicalize_highest_label(prioridade)
        if prioridade_text and prioridade_text.lower() != 'nan':
            return prioridade_text

    if classe_text and classe_text.lower() != 'nan':
        return canonicalize_highest_label(classe_text)
    return 'Standard'


def canonicalize_highest_label(value):
    text = '' if pd.isna(value) else str(value).strip()
    if not text or text.lower() == 'nan':
        return text
    return 'Highest' if is_highest_alias(text) else text


def is_highest_alias(value):
    text = normalize_text(value)
    if not text:
        return False
    return any(token in text for token in HIGHEST_ALIAS_TOKENS)


HIGHEST_ALIAS_TOKENS = (
    'highest', 'higest', 'expedite', 'urgent', 'urgente',
    'critical', 'critico', 'blocker', 'fast track', 'fasttrack',
)


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


def portfolio_has_extra_onepage_tag(raw_labels):
    text = normalize_text(str(raw_labels or '')).replace('-', ' ')
    return PORTFOLIO_EXTRA_ONEPAGE_TAG in text


def apply_portfolio_module_filters(df_portfolio, projeto=None, tipo=None, classe_servico=None, responsavel=None,
                                   portfolio_project=None, portfolio_quarter='ALL'):
    df_filtered = df_portfolio.copy() if df_portfolio is not None else pd.DataFrame()
    notes = []

    if df_filtered.empty:
        return df_filtered, None, notes

    if 'Prioridade' not in df_filtered.columns:
        df_filtered['Prioridade'] = ''
    df_filtered['Prioridade'] = df_filtered['Prioridade'].apply(canonicalize_highest_label)
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
            selected_responsaveis = set(_normalize_responsavel_filter_values(responsavel))
            df_filtered = df_filtered[
                df_filtered[responsavel_col].fillna('').astype(str).str.strip().isin(selected_responsaveis)
            ].copy()
            if df_filtered.empty:
                notes.append(f'Responsável "{_format_responsavel_filter_label(responsavel)}" sem itens no escopo atual do portfólio.')
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


def process_fato_data(fato):
    """Process and rename fato data."""
    fato.rename(columns={k: v for k, v in rename_map.items() if k in fato.columns}, inplace=True)
    if 'ClasseServico' not in fato.columns:
        fato['ClasseServico'] = np.nan
    if 'Prioridade' not in fato.columns:
        fato['Prioridade'] = np.nan
    fato['Prioridade'] = fato['Prioridade'].apply(canonicalize_highest_label)
    fato['ClasseServico'] = fato.apply(lambda row: resolve_service_class(row.get('ClasseServico'), row.get('Prioridade')), axis=1)
    return fato


# Constants that might be needed
TYPE_SUPPORT = 'Suporte'
TYPE_ISSUES = 'Issues/Defeitos/Problemas'
TYPE_DEV = 'Desenvolvimento'
TYPE_OTHER = 'Outro'
PORTFOLIO_EXTRA_ONEPAGE_TAG = 'extra onepage'
PROJECT_FILTER_ALL_VALUE = '__ALL_PROJECTS__'
ORIGINAL_JIRA_TYPE_FILTER_ALL_VALUE = '__ALL_ORIGINAL_JIRA_TYPES__'


def canonicalize_demand_type(tipo, subtype=None):
    tipo_norm = normalize_text(tipo)
    subtype_norm = normalize_text(subtype)

    if tipo_norm in {'suporte', 'support'} or subtype_norm in {'suporte', 'support'}:
        return TYPE_SUPPORT
    if tipo_norm in {'ad hoc', 'adhoc', 'ad-hoc'} or subtype_norm in {'ad hoc', 'adhoc', 'ad-hoc'}:
        return TYPE_DEV
    if tipo_norm in {'defeitos', 'defeito', 'bug', 'issue', 'issues', 'problema', 'problemas'}:
        return TYPE_ISSUES
    if tipo_norm == normalize_text(TYPE_ISSUES):
        return TYPE_ISSUES
    if tipo_norm in {'desenvolvimento', 'development'}:
        return TYPE_DEV
    if tipo_norm in {'outro', 'other'}:
        return TYPE_OTHER
    return str(tipo) if str(tipo or '').strip() else TYPE_OTHER


def normalize_project_filter_value(projeto):
    """Convert explicit 'all projects' selection into global scope (None)."""
    if projeto in (None, '', PROJECT_FILTER_ALL_VALUE):
        return None
    return projeto


def unique_sorted(col):
    return sorted([x for x in col.dropna().unique()])


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