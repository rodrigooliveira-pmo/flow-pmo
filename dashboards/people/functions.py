import dash

# ============================================================================
# PEOPLE MODULE - Extracted from dashboard_full.py
# ============================================================================

def _canonical_person_name(raw_name, alias_index=None):
    fallback = _normalize_person_name(raw_name)
    if not fallback:
        return ''
    alias_index = alias_index if isinstance(alias_index, dict) else _load_person_alias_index()
    for key in (_person_match_key(raw_name), _person_email_key(raw_name)):
        if key and key in alias_index:
            return alias_index[key]
    return fallback


def _load_person_bu_map() -> dict:
    """
    Retorna índice {chave_normalizada → BU} a partir de people_config.json.
    Inclui aliases definidos em people_config['aliases'].
    """
    config = _load_people_config()
    raw_bu_map: dict = config.get('bu_map', {})
    raw_aliases: dict = config.get('aliases', {})

    bu_index: dict = {}

    def _register(raw_name: str, bu: str) -> None:
        key = _person_match_key(raw_name)
        if key:
            bu_index[key] = bu

    for canonical, bu in raw_bu_map.items():
        _register(canonical, bu)
        for alias_entry in raw_aliases.get(canonical, []):
            _register(alias_entry, bu)

    return bu_index


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


