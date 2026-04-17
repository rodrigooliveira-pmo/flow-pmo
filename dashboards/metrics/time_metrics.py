import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
import plotly.graph_objects as go

from dashboards.core.data_processing import done_time_eligible_mask


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
    finite_mask = np.isfinite(x) & np.isfinite(y)
    x = x[finite_mask]
    y = y[finite_mask]
    if x.size < 2 or len(np.unique(x)) < 2:
        return None

    try:
        slope, intercept = np.polyfit(x, y, 1)
    except (np.linalg.LinAlgError, ValueError, FloatingPointError):
        return None
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


def describe_weibull_scale_cadence(scale_days):
    """
    Translate Weibull scale (lambda) into explicit day bands for delivery cadence.
    """
    try:
        scale = float(scale_days)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(scale) or scale <= 0:
        return None

    if scale <= 1.0:
        band_label = 'até 1 dia'
        detail = f"Cadência avaliada: λ={scale:.4f}d, equivalente a 1 dia ou menos."
    elif scale <= 5.0:
        band_label = 'entre 1 e 5 dias'
        detail = f"Cadência avaliada: λ={scale:.4f}d, no intervalo entre 1 e 5 dias."
    elif scale <= 10.0:
        band_label = 'entre 5 e 10 dias'
        detail = f"Cadência avaliada: λ={scale:.4f}d, no intervalo entre 5 e 10 dias."
    elif scale <= 15.0:
        band_label = 'entre 10 e 15 dias'
        detail = f"Cadência avaliada: λ={scale:.4f}d, no intervalo entre 10 e 15 dias."
    elif scale <= 20.0:
        band_label = 'entre 15 e 20 dias'
        detail = f"Cadência avaliada: λ={scale:.4f}d, no intervalo entre 15 e 20 dias."
    elif scale <= 25.0:
        band_label = 'entre 20 e 25 dias'
        detail = f"Cadência avaliada: λ={scale:.4f}d, no intervalo entre 20 e 25 dias."
    elif scale <= 30.0:
        band_label = 'entre 25 e 30 dias'
        detail = f"Cadência avaliada: λ={scale:.4f}d, no intervalo entre 25 e 30 dias."
    else:
        band_label = 'acima de 30 dias'
        detail = f"Cadência avaliada: λ={scale:.4f}d, acima de 30 dias."

    return {
        'label': band_label,
        'subtitle': f"λ={scale:.4f}d no lead time",
        'detail': detail,
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


def build_monthly_throughput_percentage_by_type(done_df, dimension_col, dimension_label):
    """
    Calcula a vazão mensal por dimensão (ex: Tipo de Demanda) e a representa 
    como um percentual do total de itens entregues naquele mês.
    """
    if done_df is None or done_df.empty or dimension_col not in done_df.columns:
        return pd.DataFrame()

    base = done_df.copy()
    base['DataDone'] = pd.to_datetime(base.get('DataDone'), errors='coerce')
    base = base.dropna(subset=['DataDone'])
    if base.empty:
        return pd.DataFrame()

    base[dimension_label] = base[dimension_col].fillna('').astype(str).str.strip().replace('', 'Sem classificação')
    # Guarda o Period para ordenação posterior
    base['MonthPeriod'] = base['DataDone'].dt.to_period('M')

    # Agrupa por Mês e Dimensão
    counts = base.groupby(['MonthPeriod', dimension_label]).size().reset_index(name='Count')

    # Calcula os totais mensais
    monthly_totals = counts.groupby('MonthPeriod')['Count'].transform('sum')
    counts['% Vazão'] = (counts['Count'] / monthly_totals * 100).round(1)

    # Pivota mantendo o Period como coluna (para ordenação)
    pivot_df = counts.pivot(index=dimension_label, columns='MonthPeriod', values='% Vazão').fillna(0)

    # Ordena colunas cronologicamente e converte para string (ex: Jan-26)
    pivot_df = pivot_df.sort_index(axis=1)
    pivot_df.columns = [p.strftime('%b-%y').capitalize() for p in pivot_df.columns]
    pivot_df.columns.name = None

    # Adiciona símbolo %
    for col in pivot_df.columns:
        pivot_df[col] = pivot_df[col].astype(str) + '%'
        pivot_df[col] = pivot_df[col].replace('0.0%', '-')

    return pivot_df.reset_index()


def build_monthly_leadtime_sla_percentage_by_type(done_df, dimension_col, dimension_label, lead_col='LeadTime_Selected_Dias', sla_days=None, sla_col=None):
    """
    Calcula a participação percentual mensal de cada tipo de item
    no total de itens com lead time elegível. As colunas de cada mês somam 100%.
    """
    if done_df is None or done_df.empty or dimension_col not in done_df.columns:
        return pd.DataFrame()

    base = done_df.copy()
    base['DataDone'] = pd.to_datetime(base.get('DataDone'), errors='coerce')
    base['LeadMetric'] = pd.to_numeric(base.get(lead_col), errors='coerce')
    base = base.dropna(subset=['DataDone', 'LeadMetric'])
    base = base[base['LeadMetric'] >= 0]
    if base.empty:
        return pd.DataFrame()

    base[dimension_label] = base[dimension_col].fillna('').astype(str).str.strip().replace('', 'Sem classificação')
    # Guarda o Period para ordenação posterior
    base['MonthPeriod'] = base['DataDone'].dt.to_period('M')

    # Agrupa por Mês e Dimensão
    counts = base.groupby(['MonthPeriod', dimension_label]).size().reset_index(name='Count')

    # Calcula os totais mensais e a participação percentual (colunas somam 100%)
    monthly_totals = counts.groupby('MonthPeriod')['Count'].transform('sum')
    counts['% Lead Time'] = (counts['Count'] / monthly_totals * 100).round(1)

    # Pivota mantendo o Period como coluna (para ordenação)
    pivot_df = counts.pivot(index=dimension_label, columns='MonthPeriod', values='% Lead Time').fillna(0)

    # Ordena colunas cronologicamente e converte para string (ex: Jan-26)
    pivot_df = pivot_df.sort_index(axis=1)
    pivot_df.columns = [p.strftime('%b-%y').capitalize() for p in pivot_df.columns]
    pivot_df.columns.name = None

    # Adiciona símbolo %
    for col in pivot_df.columns:
        pivot_df[col] = pivot_df[col].astype(str) + '%'
        pivot_df[col] = pivot_df[col].replace('0.0%', '-')

    return pivot_df.reset_index()