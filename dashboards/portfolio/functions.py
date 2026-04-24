import dash
from infra.env_config import get_settings

# ============================================================================
# PORTFOLIO MODULE - Extracted from dashboard_full.py
# ============================================================================

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


def _pm_portfolio_selected_specs(project_value=None):
    selected = _canonical_pm_product_key(project_value)
    specs = []
    for spec in _PM_PORTFOLIO_PRODUCT_SPECS:
        if selected and spec['project_key'] != selected:
            continue
        specs.append(dict(spec))
    return specs


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

    asset_delivery_df = asset_scope[[
        'AssetID', 'Projeto PM', 'Produto', 'Tipo', 'TeamPortfolio', 'Titulo', 'Status Portfolio', 'DueDate', 'Link'
    ]].copy().rename(columns={'TeamPortfolio': 'Team'})
    merge_frames = [ds_agg.copy(), pm_agg.copy(), cost_assets.copy()]
    if merge_frames[0] is not None and not merge_frames[0].empty:
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


TYPE_SUPPORT = 'Suporte'
TYPE_ISSUES = 'Issues/Defeitos/Problemas'
TYPE_DEV = 'Desenvolvimento'
TYPE_OTHER = 'Outro'
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
            {'Indicador': 'Itens com tag EXTRA-ONEPAGE', 'Valor': int(extra_onepage_items['ID'].nunique())},
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
    target_mix_raw = get_settings().FLOW_PMO_PORTFOLIO_TYPE_TARGET_MIX.strip()
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
        },
    }


def find_latest_portfolio_csv():
    explicit_csv = get_settings().FLOW_PMO_PORTFOLIO_CSV_FILE.strip()
    if explicit_csv:
        candidate = explicit_csv if os.path.isabs(explicit_csv) else os.path.join(os.path.dirname(__file__), explicit_csv)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        raise RuntimeError(f'FLOW_PMO_PORTFOLIO_CSV_FILE aponta para arquivo inexistente: {candidate}')

    csv_url = get_settings().FLOW_PMO_PORTFOLIO_CSV_URL.strip()
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


def portfolio_is_cancelled_item(status_value, status_category_value=''):
    status_norm = normalize_text(status_value)
    status_category_norm = normalize_text(status_category_value)
    cancel_terms = ('cancel', 'cancelad', 'cancelled', 'canceled', 'descart', 'abort')
    return any(term in status_norm for term in cancel_terms) or any(term in status_category_norm for term in cancel_terms)


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
