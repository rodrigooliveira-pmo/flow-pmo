from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from dashboards.core.data_processing import TYPE_ISSUES, done_time_eligible_mask

CANCELLED_STATUSES = frozenset([
    'canceled', 'cancelled', 'cancelado', 'cancelada', 'cancelados', 'canceladas',
])

PERIOD_DAYS = 28


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


def compute_health_score(df: pd.DataFrame, period_days: int = PERIOD_DAYS) -> HealthScoreResult:
    today = pd.Timestamp.today().normalize()
    end = today
    start = end - pd.Timedelta(days=period_days - 1)

    start_date = start.date()
    end_date = end.date()

    def fmt_date(d):
        months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        return f"{d.day:02d}/{months[d.month - 1]}/{d.year}"

    period_label = f"{fmt_date(start_date)} – {fmt_date(end_date)}"

    ratio, pts_balance = score_flow_balance(df, start, end)
    pct_fail, pts_fail = score_failure_demand(df, start, end)
    pct_eff, pts_eff = score_delivery_effectiveness(df, start, end)
    cov, pts_pred = score_predictability(df, start, end)

    all_pts = [pts_balance, pts_fail, pts_eff, pts_pred]
    score = int(round(np.mean(all_pts)))

    dimensions = [
        DimensionResult(
            name='Equilíbrio do Fluxo',
            icon='📊',
            value_display=f"{ratio:.2f}×" if ratio is not None else '—',
            points=pts_balance,
            thresholds=['≤1.2×', '≤1.5×', '>1.5×'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=ratio is not None,
        ),
        DimensionResult(
            name='Demanda de Falha',
            icon='🐞',
            value_display=f"{pct_fail:.0f}%" if pct_fail is not None else '—',
            points=pts_fail,
            thresholds=['≤15%', '≤25%', '>25%'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=pct_fail is not None,
        ),
        DimensionResult(
            name='Efetividade de Entrega',
            icon='🚪',
            value_display=f"{pct_eff:.0f}%" if pct_eff is not None else '—',
            points=pts_eff,
            thresholds=['≥85%', '≥70%', '<70%'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=pct_eff is not None,
        ),
        DimensionResult(
            name='Previsibilidade',
            icon='🗓️',
            value_display=f"{cov:.2f}" if cov is not None else '—',
            points=pts_pred,
            thresholds=['≤0.7', '≤1.2', '>1.2'],
            colors=['#16a34a', '#ea580c', '#dc2626'],
            has_data=cov is not None,
        ),
    ]

    has_data = any(d.has_data for d in dimensions)
    return HealthScoreResult(
        score=score,
        dimensions=dimensions,
        period_label=period_label,
        start_date=start_date,
        end_date=end_date,
        has_data=has_data,
    )
