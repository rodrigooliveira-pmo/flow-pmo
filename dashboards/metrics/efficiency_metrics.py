import pandas as pd

from dashboards.core.data_processing import done_time_eligible_mask

# Candidate column names for item creation date (same candidates as dashboard_full.py)
_CREATION_DATE_CANDIDATES = [
    'DataCriacao', 'DataCriacaoID', 'Created', 'CreatedDate', 'IssueCreated',
]


def _resolve_system_lead_time(df: pd.DataFrame) -> pd.Series:
    """
    Calculates system lead time (creation → done) in calendar days.
    Falls back to LeadTime_Dias when creation date is unavailable.
    This captures the full demand queue including pre-sprint waiting time,
    which is typically the dominant source of waste in high-WIP systems.
    """
    data_done = pd.to_datetime(df.get('DataDone'), errors='coerce')

    creation = pd.Series(pd.NaT, index=df.index, dtype='datetime64[ns]')
    for col in _CREATION_DATE_CANDIDATES:
        if col not in df.columns:
            continue
        parsed = pd.to_datetime(df[col], errors='coerce', utc=False)
        # strip tz if present
        if parsed.dt.tz is not None:
            parsed = parsed.dt.tz_localize(None)
        creation = creation.combine_first(parsed)

    has_creation = creation.notna() & data_done.notna()
    system_lt = pd.Series(float('nan'), index=df.index, dtype=float)
    system_lt[has_creation] = (data_done[has_creation] - creation[has_creation]).dt.days.clip(lower=0)

    # Fallback to LeadTime_Dias for rows without creation date
    if 'LeadTime_Dias' in df.columns:
        fallback = pd.to_numeric(df['LeadTime_Dias'], errors='coerce')
        system_lt = system_lt.combine_first(fallback)

    return system_lt


def build_waste_decomposition(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """
    Aggregates mean Cycle Time (value) vs full system waste per group.
    Waste = SystemLeadTime - CycleTime, where SystemLeadTime = DataCriacao → DataDone.
    This captures pre-sprint queue time, which is invisible in LeadTime_Dias
    (DataBacklog → DataDone) and explains high apparent efficiency in the old metric.
    Falls back to LeadTime_Dias when creation date is unavailable.
    Returns sorted by waste descending so worst cases appear first.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[group_col, 'Entregas de Valor', 'Desperdícios do processo', 'Eficiência (%)'])

    required = {'TempoExecucao_Dias', group_col}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=[group_col, 'Entregas de Valor', 'Desperdícios do processo', 'Eficiência (%)'])

    mask = done_time_eligible_mask(df)
    eligible = df[mask].copy()

    eligible['TempoExecucao_Dias'] = pd.to_numeric(eligible['TempoExecucao_Dias'], errors='coerce')
    eligible['_SystemLeadTime'] = _resolve_system_lead_time(eligible)
    eligible = eligible.dropna(subset=['TempoExecucao_Dias', '_SystemLeadTime', group_col])
    eligible = eligible[(eligible['TempoExecucao_Dias'] >= 0) & (eligible['_SystemLeadTime'] >= 0)]

    if eligible.empty:
        return pd.DataFrame(columns=[group_col, 'Entregas de Valor', 'Desperdícios do processo', 'Eficiência (%)'])

    grp = (
        eligible.groupby(group_col, dropna=False)
        .agg(
            valor=('TempoExecucao_Dias', 'mean'),
            lead=('_SystemLeadTime', 'mean'),
            n=('TempoExecucao_Dias', 'count'),
        )
        .reset_index()
    )

    grp['Entregas de Valor'] = grp['valor'].round(1)
    grp['Desperdícios do processo'] = (grp['lead'] - grp['valor']).clip(lower=0).round(1)
    total = grp['Entregas de Valor'] + grp['Desperdícios do processo']
    grp['Eficiência (%)'] = (grp['Entregas de Valor'] / total.replace(0, float('nan')) * 100).round(1)

    return (
        grp[[group_col, 'Entregas de Valor', 'Desperdícios do processo', 'Eficiência (%)', 'n']]
        .sort_values('Desperdícios do processo', ascending=False)
        .reset_index(drop=True)
    )


def build_scenario_simulation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds 4 hypothetical scenarios based on overall system lead time averages.
    Uses system lead time (creation → done) so the baseline reflects real waste levels.
    Scenario multipliers:
      Contratar pessoas: value slightly up but process waste grows faster (more coordination overhead)
      Reduzir times: proportional scale-down (same waste ratio, just smaller)
      Reduzir desperdícios: targeted waste removal, value time unchanged
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['Cenário', 'Entregas de Valor', 'Desperdícios do processo'])

    if 'TempoExecucao_Dias' not in df.columns:
        return pd.DataFrame(columns=['Cenário', 'Entregas de Valor', 'Desperdícios do processo'])

    mask = done_time_eligible_mask(df)
    eligible = df[mask].copy()
    eligible['TempoExecucao_Dias'] = pd.to_numeric(eligible['TempoExecucao_Dias'], errors='coerce')
    eligible['_SystemLeadTime'] = _resolve_system_lead_time(eligible)
    eligible = eligible.dropna(subset=['TempoExecucao_Dias', '_SystemLeadTime'])
    eligible = eligible[(eligible['TempoExecucao_Dias'] >= 0) & (eligible['_SystemLeadTime'] >= 0)]

    if eligible.empty:
        return pd.DataFrame(columns=['Cenário', 'Entregas de Valor', 'Desperdícios do processo'])

    valor_base = eligible['TempoExecucao_Dias'].mean()
    lead_base = eligible['_SystemLeadTime'].mean()
    waste_base = max(lead_base - valor_base, 0)

    cenarios = [
        ('Cenário atual',          round(valor_base, 1),          round(waste_base, 1)),
        ('Contratar pessoas',      round(valor_base * 1.2, 1),    round(waste_base * 1.5, 1)),
        ('Reduzir times',          round(valor_base * 0.6, 1),    round(waste_base * 0.6, 1)),
        ('Reduzir desperdícios',   round(valor_base, 1),          round(waste_base * 0.35, 1)),
    ]

    return pd.DataFrame(cenarios, columns=['Cenário', 'Entregas de Valor', 'Desperdícios do processo'])
