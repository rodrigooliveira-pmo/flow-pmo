"""
generate_empirical_validation.py
--------------------------------
Builds anonymized production aggregates and figures for the FlowPMO paper.

Usage:
    python paper/generate_empirical_validation.py

Outputs:
    paper/data/empirical_team_quarter.csv
    paper/data/empirical_benchmark_attainment.csv
    paper/data/empirical_wip_cohorts.csv
    paper/generated/empirical_summary.tex
    paper/generated/empirical_descriptives.tex
    paper/figures/fig5_empirical_heatmap.{pdf,png}
    paper/figures/fig6_benchmark_attainment.{pdf,png}
    paper/figures/fig7_wip_boxplot.{pdf,png}
    paper/figures/fig8_empirical_scatter.{pdf,png}
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault("MPLCONFIGDIR", os.path.join(PROJECT_ROOT, ".mplconfig"))
os.environ.setdefault("XDG_CACHE_HOME", os.path.join(PROJECT_ROOT, ".cache"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dashboard_full as dashmod


DATA_DIR = os.path.join(SCRIPT_DIR, "data")
FIGURES_DIR = os.path.join(SCRIPT_DIR, "figures")
GENERATED_DIR = os.path.join(SCRIPT_DIR, "generated")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

MIN_GROUP_SIZE = 5
MAX_FULL_QUARTERS = 4
PROJECT_KEYS = ["W1NNER", "S1NC", "BF", "DT"]
DIMENSION_LABELS = [
    "Delivery",
    "Flow",
    "Review/Git",
    "Conformance",
    "Anti-Rework",
]


@dataclass(frozen=True)
class QuarterWindow:
    label: str
    start: pd.Timestamp
    end: pd.Timestamp


def save_figure(fig, name: str) -> None:
    pdf_path = os.path.join(FIGURES_DIR, f"{name}.pdf")
    png_path = os.path.join(FIGURES_DIR, f"{name}.png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=300)
    plt.close(fig)


def quarter_label(ts: pd.Timestamp) -> str:
    dt = pd.Timestamp(ts)
    quarter = ((int(dt.month) - 1) // 3) + 1
    return f"Q{quarter}-{int(dt.year)}"


def quarter_start(year: int, quarter: int) -> pd.Timestamp:
    return pd.Timestamp(year=year, month=((quarter - 1) * 3) + 1, day=1)


def iter_full_quarters(max_quarters: int = MAX_FULL_QUARTERS) -> list[QuarterWindow]:
    done_dates = pd.to_datetime(dashmod.fato.get("DataDone", pd.Series(dtype="datetime64[ns]")), errors="coerce").dropna()
    if done_dates.empty:
        return []
    max_done = done_dates.max()
    today = pd.Timestamp(date.today())
    current_quarter = ((today.month - 1) // 3) + 1
    current_q_start = quarter_start(today.year, current_quarter)
    effective_end = min(max_done, current_q_start - pd.Timedelta(days=1))
    last_quarter = ((effective_end.month - 1) // 3) + 1
    year = int(effective_end.year)

    windows: list[QuarterWindow] = []
    while len(windows) < max_quarters:
        start = quarter_start(year, last_quarter)
        end = start + pd.offsets.QuarterEnd()
        if end <= effective_end:
            windows.append(QuarterWindow(f"Q{last_quarter}-{year}", start, end + pd.Timedelta(days=1)))
        last_quarter -= 1
        if last_quarter == 0:
            last_quarter = 4
            year -= 1
        if year < int(done_dates.min().year) - 1:
            break
    return list(reversed(windows))


def filter_project_scope(project_key: str) -> pd.DataFrame:
    if dashmod.fato.empty or "Projeto" not in dashmod.fato.columns:
        return pd.DataFrame()
    proj_norm = dashmod.normalize_text(project_key)
    scope = dashmod.fato[
        dashmod.fato["Projeto"].astype(str).apply(dashmod.normalize_text) == proj_norm
    ].copy()
    if scope.empty and project_key == "BF":
        scope = dashmod.fato[
            dashmod.fato["Projeto"].astype(str).apply(dashmod.normalize_text) == dashmod.normalize_text("BEFINANCE")
        ].copy()
    if scope.empty and project_key == "DT":
        scope = dashmod.fato[
            dashmod.fato["Projeto"].astype(str).apply(dashmod.normalize_text) == dashmod.normalize_text("DATA&ANALYTICS")
        ].copy()
    return scope


def project_has_complete_sources(project_key: str) -> bool:
    jira_scope = filter_project_scope(project_key)
    bb_logs = dashmod.load_project_bitbucket_logs(project_key)
    pm_cases = dashmod.load_project_pm_case_df(project_key)
    events_df = dashmod.load_project_pm_sheet(project_key, "EventosFiltrados")
    return (
        jira_scope is not None
        and not jira_scope.empty
        and isinstance(bb_logs, dict)
        and any(not df.empty for df in bb_logs.values())
        and (
            (pm_cases is not None and not pm_cases.empty)
            or (events_df is not None and not events_df.empty)
        )
    )


def _series_median(df: pd.DataFrame, col: str) -> float:
    if df.empty or col not in df.columns:
        return float("nan")
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    values = values[values >= 0]
    return float(values.median()) if not values.empty else float("nan")


def _series_quantile(df: pd.DataFrame, col: str, q: float) -> float:
    if df.empty or col not in df.columns:
        return float("nan")
    values = pd.to_numeric(df[col], errors="coerce").dropna()
    values = values[values >= 0]
    return float(values.quantile(q)) if not values.empty else float("nan")


def _fallback_lead_series(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    if "LeadTime_Selected_Dias" in df.columns:
        values = pd.to_numeric(df["LeadTime_Selected_Dias"], errors="coerce")
        values = values[values >= 0]
        if not values.dropna().empty:
            return values.dropna()
    if {"DataBacklog", "DataDone"}.issubset(df.columns):
        start = pd.to_datetime(df["DataBacklog"], errors="coerce")
        done = pd.to_datetime(df["DataDone"], errors="coerce")
        values = ((done - start).dt.total_seconds() / 86400.0).dropna()
        values = values[values >= 0]
        if not values.empty:
            return values
    if {"DataInProgress", "DataDone"}.issubset(df.columns):
        start = pd.to_datetime(df["DataInProgress"], errors="coerce")
        done = pd.to_datetime(df["DataDone"], errors="coerce")
        values = ((done - start).dt.total_seconds() / 86400.0).dropna()
        values = values[values >= 0]
        if not values.empty:
            return values
    return pd.Series(dtype=float)


def _compute_pr_without_approval_pct(bitbucket_logs: dict, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> float:
    pr_df = bitbucket_logs.get("pullrequests", pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    if pr_df is None or pr_df.empty:
        return float("nan")
    merged_prs = pr_df.copy()
    if "updated_on" in merged_prs.columns:
        merged_prs = merged_prs[(merged_prs["updated_on"] >= start_ts) & (merged_prs["updated_on"] < end_ts)]
    elif "created_on" in merged_prs.columns:
        merged_prs = merged_prs[(merged_prs["created_on"] >= start_ts) & (merged_prs["created_on"] < end_ts)]
    if "state_norm" in merged_prs.columns:
        merged_prs = merged_prs[merged_prs["state_norm"] == "merged"]
    if merged_prs.empty:
        return float("nan")
    if "reviewers_approved_count" in merged_prs.columns:
        approved_count = pd.to_numeric(merged_prs["reviewers_approved_count"], errors="coerce").fillna(0)
        no_approval = int((approved_count <= 0).sum())
    elif "approved_by" in merged_prs.columns:
        no_approval = int(merged_prs["approved_by"].fillna("").astype(str).str.strip().eq("").sum())
    else:
        return float("nan")
    return round(no_approval / len(merged_prs) * 100.0, 1) if len(merged_prs) > 0 else float("nan")


def _compute_bottleneck_hours(scope: pd.DataFrame) -> float:
    bdf = dashmod.compute_flow_bottlenecks(scope)
    if bdf.empty:
        return float("nan")
    hours = (
        pd.to_numeric(bdf["Tempo Médio (dias)"], errors="coerce").fillna(0)
        * pd.to_numeric(bdf["Qtde Itens"], errors="coerce").fillna(0)
        * 8.0
    )
    return round(float(hours.sum()), 1)


def _build_team_alias_map(project_keys: list[str]) -> dict[str, str]:
    aliases = {}
    for idx, key in enumerate(sorted(project_keys), start=1):
        aliases[key] = f"Team {chr(64 + idx)}"
    return aliases


def collect_team_quarter_metrics() -> pd.DataFrame:
    windows = iter_full_quarters()
    complete_projects = [key for key in PROJECT_KEYS if project_has_complete_sources(key)]
    alias_map = _build_team_alias_map(complete_projects)
    rows: list[dict] = []

    for project_key in complete_projects:
        project_scope = filter_project_scope(project_key)
        if project_scope.empty:
            continue
        bitbucket_logs = dashmod.load_project_bitbucket_logs(project_key)
        pm_cases = dashmod.load_project_pm_case_df(project_key)
        pm_events = dashmod.load_project_pm_sheet(project_key, "EventosFiltrados")

        for window in windows:
            start_ts = pd.Timestamp(window.start)
            end_ts = pd.Timestamp(window.end)
            per_dev, _, _ = dashmod.build_dev_productivity_metrics(project_scope, start_ts, end_ts)
            if per_dev.empty:
                continue

            active_dev_mask = (
                pd.to_numeric(per_dev.get("Itens Entregues", 0), errors="coerce").fillna(0)
                + pd.to_numeric(per_dev.get("Itens Puxados", 0), errors="coerce").fillna(0)
            ) > 0
            active_dev_count = int(active_dev_mask.sum())
            if active_dev_count <= 0:
                continue

            quarter_scope = project_scope.copy()
            item_person_map = dashmod._build_dev_item_person_map(quarter_scope)
            pm_dev = dashmod.compute_pm_dev_metrics(pm_cases, start_ts, end_ts, item_person_map=item_person_map)
            pm_flow = dashmod.compute_pm_dev_flow_metrics(
                pd.DataFrame(),
                pd.DataFrame(),
                start_ts,
                end_ts,
                item_person_map=item_person_map,
                events_df=pm_events,
            )
            cross_people, cross_totals, _ = dashmod.compute_cross_source_capacity_metrics(
                quarter_scope,
                bitbucket_logs,
                start_ts,
                end_ts,
            )

            done_window = quarter_scope[
                quarter_scope.get("DataDone", pd.Series(pd.NaT, index=quarter_scope.index)).between(start_ts, end_ts, inclusive="left")
            ].copy()
            lead_values = _fallback_lead_series(done_window)
            lead_median = float(lead_values.median()) if not lead_values.empty else float("nan")
            lead_p85 = float(lead_values.quantile(0.85)) if not lead_values.empty else float("nan")
            pr_without_approval_pct = _compute_pr_without_approval_pct(bitbucket_logs, start_ts, end_ts)
            bottleneck_hours = _compute_bottleneck_hours(done_window if not done_window.empty else quarter_scope)

            items_delivered = int(pd.to_numeric(per_dev["Itens Entregues"], errors="coerce").fillna(0).sum())
            items_pulled = int(pd.to_numeric(per_dev["Itens Puxados"], errors="coerce").fillna(0).sum())
            sp_delivered = int(pd.to_numeric(per_dev["SP Entregues"], errors="coerce").fillna(0).sum())
            score_complexity = float(pd.to_numeric(per_dev["Score Complexidade"], errors="coerce").fillna(0).sum())
            score_complexity_pulled = float(pd.to_numeric(per_dev["Score Complexidade Puxado"], errors="coerce").fillna(0).sum())
            wip_residual = int(pd.to_numeric(per_dev["WIP Residual"], errors="coerce").fillna(0).sum())
            flow_efficiency_pct = round(min(items_delivered / items_pulled * 100.0, 100.0), 1) if items_pulled > 0 else float("nan")
            commitment_completion_pct = (
                round(min(score_complexity / score_complexity_pulled * 100.0, 100.0), 1)
                if score_complexity_pulled > 0 else float("nan")
            )
            throughput_per_dev = round(items_delivered / active_dev_count, 1) if active_dev_count > 0 else float("nan")
            score_complexity_per_dev = round(score_complexity / active_dev_count, 1) if active_dev_count > 0 else float("nan")
            wip_per_dev = round(wip_residual / active_dev_count, 2) if active_dev_count > 0 else float("nan")
            conformance_pct = _series_median(pm_dev, "Conformance Quality (%)")
            rework_pct = _series_median(pm_dev, "Rework Rate PM (%)")
            qa_return_pct = _series_median(pm_dev, "QA Return Rate (%)")
            qa_return_cards_pct = _series_median(pm_flow, "% Cards com Retorno QA->Dev")
            git_coverage_pct = float(cross_totals.get("Itens com Evidencia Tecnica", 0))
            git_coverage_pct = (
                round(git_coverage_pct / items_delivered * 100.0, 1)
                if items_delivered > 0 else float("nan")
            )

            rows.append({
                "Quarter": window.label,
                "ProjectKey": project_key,
                "TeamAlias": alias_map[project_key],
                "ActiveDevelopers": active_dev_count,
                "ItemsDelivered": items_delivered,
                "ItemsPulled": items_pulled,
                "SPDelivered": sp_delivered,
                "ScoreComplexity": round(score_complexity, 1),
                "ScoreComplexityPulled": round(score_complexity_pulled, 1),
                "CommitmentCompletionPct": commitment_completion_pct,
                "ThroughputPerDev": throughput_per_dev,
                "ScoreComplexityPerDev": score_complexity_per_dev,
                "WIPResidual": wip_residual,
                "WIPPerDev": wip_per_dev,
                "FlowEfficiencyPct": flow_efficiency_pct,
                "LeadTimeMedianDays": round(lead_median, 1) if pd.notna(lead_median) else np.nan,
                "LeadTimeP85Days": round(lead_p85, 1) if pd.notna(lead_p85) else np.nan,
                "ConformancePct": round(conformance_pct, 1) if pd.notna(conformance_pct) else np.nan,
                "ReworkPct": round(rework_pct, 1) if pd.notna(rework_pct) else np.nan,
                "QAReturnPct": round(qa_return_pct, 1) if pd.notna(qa_return_pct) else np.nan,
                "QAReturnCardsPct": round(qa_return_cards_pct, 1) if pd.notna(qa_return_cards_pct) else np.nan,
                "GitCoveragePct": git_coverage_pct,
                "PRWithoutApprovalPct": pr_without_approval_pct,
                "BottleneckHours": bottleneck_hours,
            })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def normalize_metrics(team_df: pd.DataFrame) -> pd.DataFrame:
    if team_df.empty:
        return team_df

    df = team_df.copy()
    delivery_p75 = max(float(df["ScoreComplexityPerDev"].dropna().quantile(0.75)), 0.1)
    nds = (df["ScoreComplexityPerDev"] / delivery_p75 * 100.0).clip(0, 100)
    eee = pd.to_numeric(df["CommitmentCompletionPct"], errors="coerce").clip(0, 100)
    review_components = pd.DataFrame({
        "GitCoveragePct": pd.to_numeric(df["GitCoveragePct"], errors="coerce"),
        "ApprovalCompliancePct": 100.0 - pd.to_numeric(df["PRWithoutApprovalPct"], errors="coerce"),
    })
    review_signal = (review_components.sum(axis=1, min_count=1) / review_components.notna().sum(axis=1).replace(0, np.nan))

    df["NormDelivery"] = (0.70 * nds + 0.30 * eee).clip(0, 100).round(1)
    df["NormFlow"] = (pd.to_numeric(df["FlowEfficiencyPct"], errors="coerce") / 80.0 * 100.0).clip(0, 100).round(1)
    df["NormReview"] = (review_signal / 80.0 * 100.0).clip(0, 100).round(1)
    df["NormConformance"] = (pd.to_numeric(df["ConformancePct"], errors="coerce") / 75.0 * 100.0).clip(0, 100).round(1)
    df["NormAntiRework"] = ((100.0 - pd.to_numeric(df["ReworkPct"], errors="coerce")) / 80.0 * 100.0).clip(0, 100).round(1)

    ideal = np.array([100, 100, 100, 100, 100], dtype=float)
    norm_cols = ["NormDelivery", "NormFlow", "NormReview", "NormConformance", "NormAntiRework"]
    distances = df[norm_cols].fillna(0).apply(lambda row: np.linalg.norm(row.values - ideal), axis=1)
    df["EmpiricalScoreBenchmark"] = (100.0 - (distances / (math.sqrt(5) * 100.0) * 100.0)).clip(0, 100).round(1)
    return df


def apply_disclosure_control(team_df: pd.DataFrame) -> pd.DataFrame:
    if team_df.empty:
        return team_df
    df = team_df.copy()
    df["PublishedTeam"] = np.where(df["ActiveDevelopers"] < MIN_GROUP_SIZE, "Other", df["TeamAlias"])
    agg_rules = {
        "ActiveDevelopers": "sum",
        "ItemsDelivered": "sum",
        "ItemsPulled": "sum",
        "SPDelivered": "sum",
        "ScoreComplexity": "sum",
        "ScoreComplexityPulled": "sum",
        "WIPResidual": "sum",
        "BottleneckHours": "sum",
        "ThroughputPerDev": "mean",
        "ScoreComplexityPerDev": "mean",
        "WIPPerDev": "mean",
        "FlowEfficiencyPct": "mean",
        "LeadTimeMedianDays": "median",
        "LeadTimeP85Days": "median",
        "ConformancePct": "mean",
        "ReworkPct": "mean",
        "QAReturnPct": "mean",
        "QAReturnCardsPct": "mean",
        "GitCoveragePct": "mean",
        "PRWithoutApprovalPct": "mean",
        "CommitmentCompletionPct": "mean",
        "NormDelivery": "mean",
        "NormFlow": "mean",
        "NormReview": "mean",
        "NormConformance": "mean",
        "NormAntiRework": "mean",
        "EmpiricalScoreBenchmark": "mean",
    }
    df = df.groupby(["Quarter", "PublishedTeam"], as_index=False).agg(agg_rules)
    for pct_col in [c for c in df.columns if c.endswith("Pct") or c.startswith("Norm") or c == "EmpiricalScoreBenchmark"]:
        df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce").round(1)
    for day_col in ["LeadTimeMedianDays", "LeadTimeP85Days", "BottleneckHours", "ThroughputPerDev", "ScoreComplexityPerDev", "WIPPerDev"]:
        if day_col in df.columns:
            df[day_col] = pd.to_numeric(df[day_col], errors="coerce").round(1)
    return df


def build_benchmark_attainment(team_df: pd.DataFrame) -> pd.DataFrame:
    attainment = pd.DataFrame({
        "Dimension": ["Flow", "Conformance", "Anti-Rework", "Git Coverage"],
        "Threshold": [80.0, 75.0, 80.0, 80.0],
        "Metric": ["FlowEfficiencyPct", "ConformancePct", "NormAntiRework", "GitCoveragePct"],
    })
    rows = []
    for _, row in attainment.iterrows():
        values = pd.to_numeric(team_df[row["Metric"]], errors="coerce").dropna()
        if values.empty:
            share = np.nan
        else:
            share = round(float((values >= float(row["Threshold"])).mean() * 100.0), 1)
        rows.append({
            "Dimension": row["Dimension"],
            "Threshold": row["Threshold"],
            "ShareMeetingBenchmarkPct": share,
        })
    return pd.DataFrame(rows)


def build_wip_cohorts(team_df: pd.DataFrame) -> pd.DataFrame:
    if team_df.empty:
        return pd.DataFrame()
    df = team_df.copy()
    median_wip = float(df["WIPPerDev"].median())
    df["WIPCohort"] = np.where(df["WIPPerDev"] >= median_wip, "High WIP", "Low WIP")
    rows = []
    for cohort, g in df.groupby("WIPCohort"):
        rows.append({
            "WIPCohort": cohort,
            "Observations": int(len(g)),
            "ThroughputPerDev": round(float(g["ThroughputPerDev"].median()), 1),
            "LeadTimeMedianDays": round(float(g["LeadTimeMedianDays"].median()), 1),
            "ConformancePct": round(float(g["ConformancePct"].median()), 1),
            "ReworkPct": round(float(g["ReworkPct"].median()), 1),
            "QAReturnPct": round(float(g["QAReturnPct"].median()), 1),
        })
    return pd.DataFrame(rows)


def generate_heatmap(team_df: pd.DataFrame) -> None:
    pivot_df = team_df.copy()
    pivot_df["Label"] = pivot_df["PublishedTeam"] + " • " + pivot_df["Quarter"]
    heat = pivot_df.set_index("Label")[["NormDelivery", "NormFlow", "NormReview", "NormConformance", "NormAntiRework"]]
    heat.columns = DIMENSION_LABELS
    fig, ax = plt.subplots(figsize=(10, max(4, 0.45 * len(heat))))
    im = ax.imshow(heat.values, aspect="auto", cmap="YlGnBu", vmin=50, vmax=100)
    ax.set_xticks(np.arange(len(heat.columns)))
    ax.set_xticklabels(heat.columns, rotation=0)
    ax.set_yticks(np.arange(len(heat.index)))
    ax.set_yticklabels(heat.index)
    ax.set_title("Empirical Validation Heatmap: Anonymized Team-Quarter Profiles", fontsize=12, fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.set_label("Normalized score")
    plt.tight_layout()
    save_figure(fig, "fig5_empirical_heatmap")


def generate_benchmark_attainment(attainment_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(
        attainment_df["Dimension"],
        attainment_df["ShareMeetingBenchmarkPct"],
        color=["#1f77b4", "#2ca02c", "#ff7f0e", "#9467bd"],
        edgecolor="white",
        linewidth=0.8,
    )
    ax.axhline(50, linestyle="--", color="grey", linewidth=1.0)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1, f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Team-quarter observations meeting benchmark (%)")
    ax.set_title("Benchmark Attainment in Anonymized Production Cohorts", fontsize=12, fontweight="bold")
    plt.tight_layout()
    save_figure(fig, "fig6_benchmark_attainment")


def generate_wip_boxplot(team_df: pd.DataFrame) -> None:
    df = team_df.copy()
    median_wip = float(df["WIPPerDev"].median())
    df["WIPCohort"] = np.where(df["WIPPerDev"] >= median_wip, "High WIP", "Low WIP")
    metrics = ["LeadTimeMedianDays", "ReworkPct", "QAReturnPct"]
    labels = ["Lead Time", "Rework", "QA Return"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, metric, label in zip(axes, metrics, labels):
        low = pd.to_numeric(df.loc[df["WIPCohort"] == "Low WIP", metric], errors="coerce").dropna()
        high = pd.to_numeric(df.loc[df["WIPCohort"] == "High WIP", metric], errors="coerce").dropna()
        ax.boxplot(
            [low.values, high.values],
            tick_labels=["Low WIP", "High WIP"],
            patch_artist=True,
            boxprops={"facecolor": "#cfe8ff"},
            medianprops={"color": "#d62728"},
        )
        ax.set_title(label)
    fig.suptitle("Flow-Health by WIP Cohort", fontsize=12, fontweight="bold")
    plt.tight_layout()
    save_figure(fig, "fig7_wip_boxplot")


def generate_scatter(team_df: pd.DataFrame) -> None:
    df = team_df.copy()
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    sizes = pd.to_numeric(df["BottleneckHours"], errors="coerce").fillna(0).clip(lower=1) * 0.8 + 40
    colors = pd.to_numeric(df["QAReturnPct"], errors="coerce").fillna(0)
    scatter = ax.scatter(
        df["FlowEfficiencyPct"],
        df["ConformancePct"],
        s=sizes,
        c=colors,
        cmap="YlOrRd",
        edgecolors="white",
        linewidths=0.7,
        alpha=0.9,
    )
    ax.axvline(80, linestyle="--", color="steelblue", linewidth=1.2)
    ax.axhline(75, linestyle="--", color="darkorange", linewidth=1.2)
    ax.set_xlabel("Flow Efficiency (%)")
    ax.set_ylabel("Conformance (%)")
    ax.set_title("Team-Level Flow vs. Conformance\nsize = bottleneck hours, color = QA return (%)", fontsize=12, fontweight="bold")
    cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    cbar.set_label("QA return (%)")
    plt.tight_layout()
    save_figure(fig, "fig8_empirical_scatter")


def write_latex_descriptives(team_df: pd.DataFrame, attainment_df: pd.DataFrame, wip_df: pd.DataFrame) -> None:
    desc_path = os.path.join(GENERATED_DIR, "empirical_descriptives.tex")
    summary_path = os.path.join(GENERATED_DIR, "empirical_summary.tex")

    subset = team_df[
        [
            "Quarter", "PublishedTeam", "ActiveDevelopers", "ItemsDelivered", "ItemsPulled",
            "LeadTimeMedianDays", "FlowEfficiencyPct", "ConformancePct", "ReworkPct",
            "QAReturnPct", "GitCoveragePct", "EmpiricalScoreBenchmark",
        ]
    ].copy()
    subset = subset.sort_values(["Quarter", "PublishedTeam"]).reset_index(drop=True)

    table_lines = [
        "\\begin{table}[htbp]",
        "  \\centering",
        "  \\caption{Anonymized production descriptives by team-quarter. Cells with $n < 5$ were merged into \\texttt{Other}.}",
        "  \\label{tab:empirical-desc}",
        "  \\scriptsize",
        "  \\begin{tabular}{llrrrrrrrrr}",
        "    \\toprule",
        "    Quarter & Team & $n$ & Delivered & Pulled & LT$_{50}$ & FE & Conf & Rework & Git & SB \\\\",
        "    \\midrule",
    ]
    for _, row in subset.iterrows():
        table_lines.append(
            "    {quarter} & {team} & {n:d} & {delivered:d} & {pulled:d} & {lt:.1f} & {fe:.1f} & {conf:.1f} & {rw:.1f} & {git:.1f} & {sb:.1f} \\\\".format(
                quarter=row["Quarter"],
                team=row["PublishedTeam"],
                n=int(row["ActiveDevelopers"]),
                delivered=int(row["ItemsDelivered"]),
                pulled=int(row["ItemsPulled"]),
                lt=float(row["LeadTimeMedianDays"]) if pd.notna(row["LeadTimeMedianDays"]) else 0.0,
                fe=float(row["FlowEfficiencyPct"]) if pd.notna(row["FlowEfficiencyPct"]) else 0.0,
                conf=float(row["ConformancePct"]) if pd.notna(row["ConformancePct"]) else 0.0,
                rw=float(row["ReworkPct"]) if pd.notna(row["ReworkPct"]) else 0.0,
                git=float(row["GitCoveragePct"]) if pd.notna(row["GitCoveragePct"]) else 0.0,
                sb=float(row["EmpiricalScoreBenchmark"]) if pd.notna(row["EmpiricalScoreBenchmark"]) else 0.0,
            )
        )
    table_lines += [
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
    ]
    with open(desc_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(table_lines) + "\n")

    observations = int(len(team_df))
    n_teams = int(team_df["PublishedTeam"].nunique())
    best_benchmark = attainment_df.sort_values("ShareMeetingBenchmarkPct", ascending=False).iloc[0]
    worst_benchmark = attainment_df.sort_values("ShareMeetingBenchmarkPct", ascending=True).iloc[0]
    low_wip = wip_df[wip_df["WIPCohort"] == "Low WIP"]
    high_wip = wip_df[wip_df["WIPCohort"] == "High WIP"]
    lead_gap = np.nan
    rework_gap = np.nan
    if not low_wip.empty and not high_wip.empty:
        lead_gap = float(high_wip["LeadTimeMedianDays"].iloc[0] - low_wip["LeadTimeMedianDays"].iloc[0])
        rework_gap = float(high_wip["ReworkPct"].iloc[0] - low_wip["ReworkPct"].iloc[0])

    summary_lines = [
        "% Auto-generated by paper/generate_empirical_validation.py",
        (
            "Empirical validation used {obs} anonymized team-quarter observations across {teams} published cohorts. "
            "Inclusion required complete Jira, Bitbucket, and process-mining coverage for the analyzed window."
        ).format(obs=observations, teams=n_teams),
        "",
        (
            "Benchmark attainment was strongest for {best_dim} ({best_val:.1f}\\% of team-quarter observations at or above target) "
            "and weakest for {worst_dim} ({worst_val:.1f}\\%)."
        ).format(
            best_dim=str(best_benchmark["Dimension"]),
            best_val=float(best_benchmark["ShareMeetingBenchmarkPct"]),
            worst_dim=str(worst_benchmark["Dimension"]),
            worst_val=float(worst_benchmark["ShareMeetingBenchmarkPct"]),
        ),
        "",
        (
            "High-WIP cohorts showed a median lead-time penalty of {lead_gap:.1f} days and a median rework penalty of {rework_gap:.1f} percentage points "
            "relative to low-WIP cohorts, supporting the flow-health interpretation of WIP residual."
        ).format(
            lead_gap=lead_gap if not math.isnan(lead_gap) else 0.0,
            rework_gap=rework_gap if not math.isnan(rework_gap) else 0.0,
        ),
    ]
    with open(summary_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(summary_lines) + "\n")


def main() -> None:
    raw_team_df = collect_team_quarter_metrics()
    if raw_team_df.empty:
        raise SystemExit("No empirical production data could be aggregated from the current environment.")

    normalized_df = normalize_metrics(raw_team_df)
    published_df = apply_disclosure_control(normalized_df)
    attainment_df = build_benchmark_attainment(published_df)
    wip_df = build_wip_cohorts(published_df)

    published_df.to_csv(os.path.join(DATA_DIR, "empirical_team_quarter.csv"), index=False)
    attainment_df.to_csv(os.path.join(DATA_DIR, "empirical_benchmark_attainment.csv"), index=False)
    wip_df.to_csv(os.path.join(DATA_DIR, "empirical_wip_cohorts.csv"), index=False)

    generate_heatmap(published_df)
    generate_benchmark_attainment(attainment_df)
    generate_wip_boxplot(published_df)
    generate_scatter(published_df)
    write_latex_descriptives(published_df, attainment_df, wip_df)

    print(f"[OK] empirical team-quarter rows: {len(published_df)}")
    print(f"[OK] published cohorts: {published_df['PublishedTeam'].nunique()}")
    print(f"[OK] figures written to: {FIGURES_DIR}")
    print(f"[OK] latex snippets written to: {GENERATED_DIR}")


if __name__ == "__main__":
    main()
