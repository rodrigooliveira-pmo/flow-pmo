import dash

# ============================================================================
# FINANCE MODULE - Extracted from dashboard_full.py
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


