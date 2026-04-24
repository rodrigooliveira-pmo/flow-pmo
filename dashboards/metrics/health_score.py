from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from dashboards.core.data_processing import TYPE_ISSUES, TYPE_SUPPORT, done_time_eligible_mask

CANCELLED_STATUSES = frozenset([
    'canceled', 'cancelled', 'cancelado', 'cancelada', 'cancelados', 'canceladas',
])

PERIOD_DAYS = 28

_MONTH_NAMES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


@dataclass
class DimensionResult:
    name: str
    icon: str
    value_display: str
    points: int
    thresholds: list
    colors: list
    has_data: bool = True


@dataclass
class HealthScoreResult:
    score: int
    dimensions: list
    period_label: str
    start_date: date
    end_date: date
    has_data: bool = True


def _fmt_date(d) -> str:
    return f"{d.day:02d}/{_MONTH_NAMES[d.month - 1]}/{d.year}"


def _month_label(d) -> str:
    return f"{_MONTH_NAMES[d.month - 1]}/{str(d.year)[2:]}"


def _is_cancelled(status_norm_series: pd.Series) -> pd.Series:
    return status_norm_series.str.lower().str.strip().isin(CANCELLED_STATUSES)


def score_flow_balance(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple:
    if df.empty or 'DataInProgress' not in df.columns or 'DataDone' not in df.columns:
        return None, 0

    dip = pd.to_datetime(df['DataInProgress'], errors='coerce')
    ddone = pd.to_datetime(df['DataDone'], errors='coerce')

    entradas = int(((dip >= start) & (dip <= end)).sum())
    saidas = int(((ddone >= start) & (ddone <= end)).sum())

    if saidas == 0:
        return None, 0

    ratio = entradas / saidas
    pts = 100 if ratio <= 1.2 else (50 if ratio <= 1.5 else 0)
    return ratio, pts


def score_failure_demand(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple:
    if df.empty or 'DataDone' not in df.columns:
        return None, 0

    ddone = pd.to_datetime(df['DataDone'], errors='coerce')
    done_mask = (ddone >= start) & (ddone <= end)
    done_df = df[done_mask]

    total = len(done_df)
    if total == 0:
        return None, 0

    if 'TipoDemanda' in done_df.columns:
        failure_count = int((done_df['TipoDemanda'] == TYPE_ISSUES).sum())
    else:
        failure_count = 0

    pct = failure_count / total * 100
    pts = 100 if pct <= 15 else (50 if pct <= 25 else 0)
    return pct, pts


def score_delivery_effectiveness(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple:
    if df.empty or 'DataInProgress' not in df.columns:
        return None, 0

    dip = pd.to_datetime(df['DataInProgress'], errors='coerce')
    committed_mask = (dip >= start) & (dip <= end)
    committed_df = df[committed_mask].copy()

    if committed_df.empty:
        return None, 0

    ddone = pd.to_datetime(committed_df.get('DataDone', pd.Series(dtype='datetime64[ns]')), errors='coerce')
    delivered_mask = ddone.notna()

    status_col = 'StatusNorm' if 'StatusNorm' in committed_df.columns else 'Status'
    if status_col in committed_df.columns:
        aborted_mask = _is_cancelled(committed_df[status_col].fillna('')) & ~delivered_mask
    else:
        aborted_mask = pd.Series(False, index=committed_df.index)

    finalized = int(delivered_mask.sum()) + int(aborted_mask.sum())
    delivered = int(delivered_mask.sum())

    if finalized == 0:
        return None, 0

    pct = delivered / finalized * 100
    pts = 100 if pct >= 85 else (50 if pct >= 70 else 0)
    return pct, pts


def score_predictability(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple:
    if df.empty or 'DataDone' not in df.columns or 'TempoExecucao_Dias' not in df.columns:
        return None, 0

    ddone = pd.to_datetime(df['DataDone'], errors='coerce')
    done_mask = (ddone >= start) & (ddone <= end)
    eligible = done_time_eligible_mask(df)
    base = df[done_mask & eligible]

    cycle_times = pd.to_numeric(base['TempoExecucao_Dias'], errors='coerce').dropna()
    cycle_times = cycle_times[cycle_times > 0]

    if len(cycle_times) < 2:
        return None, 0

    mean_ct = cycle_times.mean()
    if mean_ct == 0:
        return None, 0

    cov = cycle_times.std() / mean_ct
    pts = 100 if cov <= 0.7 else (50 if cov <= 1.2 else 0)
    return cov, pts


def score_lead_time(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple:
    """D2 — Do it Fast. Returns (p50, p85, pts). Scores tail control: P85 vs 2×P50."""
    if df.empty or 'DataDone' not in df.columns or 'TempoExecucao_Dias' not in df.columns:
        return None, None, 0

    ddone = pd.to_datetime(df['DataDone'], errors='coerce')
    done_mask = (ddone >= start) & (ddone <= end)
    eligible = done_time_eligible_mask(df)
    base = df[done_mask & eligible]

    cycle_times = pd.to_numeric(base['TempoExecucao_Dias'], errors='coerce').dropna()
    cycle_times = cycle_times[cycle_times > 0]

    if len(cycle_times) < 5:
        return None, None, 0

    p50 = float(cycle_times.quantile(0.50))
    p85 = float(cycle_times.quantile(0.85))

    if p50 == 0:
        return p50, p85, 0

    ratio = p85 / p50
    pts = 100 if ratio <= 2.0 else (50 if ratio <= 3.0 else 0)
    return p50, p85, pts


def score_value_demand(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple:
    """D5 — Do Valuable Stuff. Returns (pct_value, pts). Proxy: % itens não-Issues e não-Suporte."""
    if df.empty or 'DataDone' not in df.columns or 'TipoDemanda' not in df.columns:
        return None, 0

    ddone = pd.to_datetime(df['DataDone'], errors='coerce')
    done_mask = (ddone >= start) & (ddone <= end)
    done_df = df[done_mask]

    total = len(done_df)
    if total == 0:
        return None, 0

    non_value = done_df['TipoDemanda'].isin([TYPE_ISSUES, TYPE_SUPPORT])
    value_count = int((~non_value).sum())

    pct = value_count / total * 100
    pts = 100 if pct >= 60 else (50 if pct >= 40 else 0)
    return pct, pts


def _compute_for_period(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, label: str, prev_d1_to_d5_pts: list = None) -> HealthScoreResult:
    ratio, pts_balance = score_flow_balance(df, start, end)
    pct_fail, pts_fail = score_failure_demand(df, start, end)
    pct_eff, pts_eff = score_delivery_effectiveness(df, start, end)
    cov, pts_pred = score_predictability(df, start, end)
    p50, p85, pts_speed = score_lead_time(df, start, end)
    pct_value, pts_value = score_value_demand(df, start, end)

    # D6 — Sustentabilidade: delta do agregado D1–D5 vs. período anterior
    d1_to_d5_pts = [pts_eff, pts_speed, pts_balance, pts_pred, pts_fail, pts_value]
    if prev_d1_to_d5_pts is not None:
        delta = float(np.mean(d1_to_d5_pts)) - float(np.mean(prev_d1_to_d5_pts))
        pts_sust = 100 if delta >= 0 else (50 if delta >= -10 else 0)
        sust_display = f"{delta:+.0f}pts"
        sust_has_data = True
    else:
        pts_sust = 0
        sust_display = '—'
        sust_has_data = False

    scored_pts = d1_to_d5_pts + ([pts_sust] if sust_has_data else [])
    score = int(round(np.mean(scored_pts)))

    dimensions = [
        DimensionResult(
            name='Volume de Entrega', icon='📦',
            value_display=f"{pct_eff:.0f}%" if pct_eff is not None else '—',
            points=pts_eff,
            thresholds=['≥85%', '≥70%', '<70%'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=pct_eff is not None,
        ),
        DimensionResult(
            name='Velocidade', icon='⚡',
            value_display=f"P85:{p85:.0f}d / P50:{p50:.0f}d" if p85 is not None else '—',
            points=pts_speed,
            thresholds=['P85≤2×P50', 'P85≤3×P50', 'P85>3×P50'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=p85 is not None,
        ),
        DimensionResult(
            name='Equilíbrio do Fluxo', icon='📊',
            value_display=f"{ratio:.2f}×" if ratio is not None else '—',
            points=pts_balance,
            thresholds=['≤1.2×', '≤1.5×', '>1.5×'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=ratio is not None,
        ),
        DimensionResult(
            name='Previsibilidade', icon='🗓️',
            value_display=f"{cov:.2f}" if cov is not None else '—',
            points=pts_pred,
            thresholds=['≤0.7', '≤1.2', '>1.2'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=cov is not None,
        ),
        DimensionResult(
            name='Qualidade', icon='🐞',
            value_display=f"{pct_fail:.0f}%" if pct_fail is not None else '—',
            points=pts_fail,
            thresholds=['≤15%', '≤25%', '>25%'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=pct_fail is not None,
        ),
        DimensionResult(
            name='Valor Entregue', icon='💎',
            value_display=f"{pct_value:.0f}%" if pct_value is not None else '—',
            points=pts_value,
            thresholds=['≥60%', '≥40%', '<40%'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=pct_value is not None,
        ),
        DimensionResult(
            name='Sustentabilidade', icon='🔋',
            value_display=sust_display,
            points=pts_sust,
            thresholds=['↑ estável', '↓ leve', '↓↓ forte'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=sust_has_data,
        ),
    ]

    return HealthScoreResult(
        score=score,
        dimensions=dimensions,
        period_label=label,
        start_date=start.date(),
        end_date=end.date(),
        has_data=any(d.has_data for d in dimensions),
    )


def compute_health_score(df: pd.DataFrame, start=None, end=None, period_days: int = PERIOD_DAYS) -> HealthScoreResult:
    if start is None or end is None:
        _end = pd.Timestamp.today().normalize()
        _start = _end - pd.Timedelta(days=period_days - 1)
    else:
        _start = pd.Timestamp(start).normalize()
        _end = pd.Timestamp(end).normalize()

    label = f"{_fmt_date(_start.date())} – {_fmt_date(_end.date())}"
    return _compute_for_period(df, _start, _end, label)


def compute_health_score_monthly(df: pd.DataFrame, start, end) -> tuple:
    """Returns (overall: HealthScoreResult, monthly: list[HealthScoreResult]).

    Splits the date range into calendar months and computes a HealthScoreResult
    for each month plus one for the full period.
    """
    _start = pd.Timestamp(start).normalize()
    _end = pd.Timestamp(end).normalize()

    overall_label = f"{_fmt_date(_start.date())} – {_fmt_date(_end.date())}"
    overall = _compute_for_period(df, _start, _end, overall_label)

    monthly = []
    prev_d1_to_d5_pts = None
    cursor = _start.replace(day=1)
    while cursor <= _end:
        m_start = max(_start, cursor)
        # last day of cursor's month
        if cursor.month == 12:
            next_month = cursor.replace(year=cursor.year + 1, month=1, day=1)
        else:
            next_month = cursor.replace(month=cursor.month + 1, day=1)
        m_end = min(_end, next_month - pd.Timedelta(days=1))

        label = _month_label(cursor.date())
        result = _compute_for_period(df, m_start, m_end, label, prev_d1_to_d5_pts)
        prev_d1_to_d5_pts = [d.points for d in result.dimensions[:6]]  # D1–D5 excluindo D6
        monthly.append(result)

        cursor = next_month

    return overall, monthly
