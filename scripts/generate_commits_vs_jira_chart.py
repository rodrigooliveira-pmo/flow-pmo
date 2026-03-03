#!/usr/bin/env python3
"""Gera gráfico de commits x cartões concluídos (Jira vs Bitbucket) por pessoa."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import dashboard_process_mining as dpm


FOCUS_PEOPLE = [
    "Igor Rezende",
    "Christopher Alves",
    "Gabriel de Oliveira Koehler",
    "Lorraine Caribe",
    "Lara Junqueira Alvarenga",
    "Thaís Cabral",
    "Lucas Pizol",
    "Peterson Bem",
]


def classify_pattern(row: pd.Series) -> str:
    commits = float(row.get("Commits", 0) or 0)
    done = float(row.get("Itens Concluidos", 0) or 0)
    if commits <= 0 and done > 0:
        return "Alta vazão sem evidência técnica"
    if commits > 0 and done <= 0:
        return "Atividade técnica sem fechamento Jira"
    if commits > 0 and done > 0:
        return "Vazão + atividade técnica"
    return "Sem atividade no recorte"


def build_cross_dataframe(days: int, project: str) -> tuple[pd.DataFrame, dict, pd.Timestamp, pd.Timestamp]:
    report_path = dpm.find_latest_process_mining_report()
    if not report_path:
        raise RuntimeError("Nenhum relatório process mining encontrado (w1nner-process-mining-*.xlsx).")

    report = dpm.load_report(report_path)
    pm_people = report.get("VazaoPessoaResumo", pd.DataFrame())
    pm_cases = report.get("ConformidadeCasos", pd.DataFrame())
    if "Done Final Date" in pm_cases.columns:
        pm_cases["Done Final Date"] = pd.to_datetime(pm_cases["Done Final Date"], errors="coerce")

    end_ts = pd.Timestamp.today().normalize()
    start_ts = end_ts - pd.Timedelta(days=max(days, 1))

    bitbucket_logs = dpm.load_project_bitbucket_logs(project)
    cross_people, cross_totals, _ = dpm.compute_pm_bitbucket_cross_metrics(
        pm_people, pm_cases, bitbucket_logs, start_ts, end_ts
    )

    if cross_people.empty:
        raise RuntimeError("Sem dados cruzados Jira + Bitbucket para o período informado.")

    cross_people = cross_people.copy()
    cross_people["Commits"] = pd.to_numeric(cross_people.get("Commits", 0), errors="coerce").fillna(0)
    cross_people["Itens Concluidos"] = pd.to_numeric(
        cross_people.get("Itens Concluidos", 0), errors="coerce"
    ).fillna(0)
    cross_people["PRs Abertos"] = pd.to_numeric(cross_people.get("PRs Abertos", 0), errors="coerce").fillna(0)
    cross_people["PRs Merged"] = pd.to_numeric(cross_people.get("PRs Merged", 0), errors="coerce").fillna(0)
    cross_people["Classificacao"] = cross_people.apply(classify_pattern, axis=1)
    cross_people["PRs (abertos+merged)"] = cross_people["PRs Abertos"] + cross_people["PRs Merged"]

    return cross_people, cross_totals, start_ts, end_ts


def build_figure(df: pd.DataFrame, totals: dict, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> go.Figure:
    active = df[(df["Commits"] > 0) | (df["Itens Concluidos"] > 0)].copy()
    active["is_focus"] = active["Pessoa"].isin(FOCUS_PEOPLE)

    color_map = {
        "Alta vazão sem evidência técnica": "#f39c12",
        "Atividade técnica sem fechamento Jira": "#d62728",
        "Vazão + atividade técnica": "#2ca02c",
        "Sem atividade no recorte": "#7f8c8d",
    }

    fig = px.scatter(
        active,
        x="Commits",
        y="Itens Concluidos",
        color="Classificacao",
        size="PRs (abertos+merged)",
        hover_name="Pessoa",
        hover_data={
            "Commits": ":.0f",
            "Itens Concluidos": ":.0f",
            "PRs Abertos": ":.0f",
            "PRs Merged": ":.0f",
            "PRs (abertos+merged)": ":.0f",
            "Classificacao": True,
        },
        color_discrete_map=color_map,
        size_max=42,
        title="Commits (Bitbucket) x Cartões Concluídos (Jira) por Pessoa",
    )

    fig.update_traces(marker=dict(line=dict(width=1, color="white"), opacity=0.88))
    fig.update_layout(
        template="plotly_white",
        height=820,
        legend_title="Padrão",
        xaxis_title="Commits no período",
        yaxis_title="Cartões concluídos no Jira",
    )

    # Linha de referência para zero concluídos, onde aparece a desconexão técnica->Jira.
    fig.add_hline(y=0, line_dash="dash", line_color="#555", opacity=0.6)

    for _, row in active[active["is_focus"]].iterrows():
        fig.add_annotation(
            x=row["Commits"],
            y=row["Itens Concluidos"],
            text=row["Pessoa"],
            showarrow=True,
            arrowhead=1,
            ax=16,
            ay=-18,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#d0d7de",
            borderwidth=1,
            font=dict(size=11),
        )

    coverage_pct = float(totals.get("Cobertura Tecnica (%)", 0.0) or 0.0)
    total_done = int(totals.get("Itens Concluidos", 0) or 0)
    total_with_evidence = int(totals.get("Itens c/ Evidencia Tecnica", 0) or 0)
    window_text = f"Período: {start_ts.date()} a {end_ts.date()}"
    coverage_text = (
        f"Cobertura técnica no recorte: {coverage_pct:.1f}% "
        f"({total_with_evidence} de {total_done} itens concluídos com evidência técnica)"
    )
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0,
        y=1.08,
        text=f"{window_text}<br>{coverage_text}",
        showarrow=False,
        align="left",
        font=dict(size=12, color="#333"),
    )

    return fig


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera gráfico commits x cartões concluídos (Jira vs Bitbucket).")
    parser.add_argument("--days", type=int, default=30, help="Janela em dias para cruzamento (default: 30).")
    parser.add_argument("--project", default="W1NNER", help="Projeto para logs Bitbucket (default: W1NNER).")
    parser.add_argument(
        "--out",
        default="artifacts/commits_vs_jira_done.html",
        help="Arquivo HTML de saída (default: artifacts/commits_vs_jira_done.html).",
    )
    args = parser.parse_args()

    df, totals, start_ts, end_ts = build_cross_dataframe(days=args.days, project=args.project)
    fig = build_figure(df=df, totals=totals, start_ts=start_ts, end_ts=end_ts)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path), include_plotlyjs="cdn")

    focus_df = df[df["Pessoa"].isin(FOCUS_PEOPLE)][
        ["Pessoa", "Itens Concluidos", "Commits", "PRs Abertos", "PRs Merged", "Classificacao"]
    ].sort_values(["Itens Concluidos", "Commits"], ascending=[False, False])

    print(f"Arquivo gerado: {out_path.resolve()}")
    print(f"Período: {start_ts.date()} -> {end_ts.date()}")
    print("\nPessoas-chave no gráfico:")
    print(focus_df.to_string(index=False))


if __name__ == "__main__":
    main()
