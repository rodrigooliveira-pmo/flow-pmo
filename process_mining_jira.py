#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

try:
    import pm4py  # type: ignore
    PM4PY_AVAILABLE = True
except Exception:
    pm4py = None  # type: ignore
    PM4PY_AVAILABLE = False

W1NNER_PROJECT_ALIASES = {"w1nner", "w1nnr"}
DEFAULT_EXPECTED_FLOW = [
    "Triagem",
    "Backlog",
    "Ready to Start",
    "In progress",
    "ready code review",
    "Code review",
    "ready testing/Qa",
    "Testing/QA",
    "ready homolog",
    "Homolog",
    "ready for production",
    "Itens concluídos",
]
DEFAULT_DONE_STATUSES = {"itens concluidos", "itens concluídos", "done", "concluido", "concluído"}
QA_HINTS = ("qa", "test", "homolog", "valid")
DEV_HINTS = ("progress", "develop", "desenvol", "code review")

REQUIRED_COLS = {
    "Projeto",
    "Issue Key",
    "History Created",
    "Author",
    "From Status",
    "To Status",
    "Tipo de Problema",
}

ISSUE_TYPE_ALIASES = {
    "historia": {"historia", "história", "story"},
    "story": {"historia", "história", "story"},
    "task": {"task", "tarefa"},
    "tarefa": {"task", "tarefa"},
    "bug": {"bug", "problema", "problem", "incident", "incidente"},
    "problema": {"bug", "problema", "problem", "incident", "incidente"},
}


def normalize_text(value: Any) -> str:
    raw = str(value or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", raw)
    no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return " ".join(no_accents.replace("_", " ").replace("-", " ").split())


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Process mining Jira (W1NNER) com saída CSV/Excel.")
    p.add_argument("--input", required=True, help="CSV de changelog detalhado do Jira")
    p.add_argument("--out-dir", default="", help="Diretório de saída (default: pasta do input)")
    p.add_argument("--project", default="W1NNR", help="Projeto alvo (W1NNR/W1NNER)")
    p.add_argument("--issue-types", nargs="*", default=["História", "Task", "Bug"])
    p.add_argument("--expected-flow", nargs="*", default=DEFAULT_EXPECTED_FLOW)
    p.add_argument("--done-status", nargs="*", default=["Done", "Itens concluídos", "Concluído"])
    p.add_argument("--prefix", default="w1nner-process-mining")
    p.add_argument("--max-top", type=int, default=25)
    return p.parse_args()


def require_cols(df: pd.DataFrame, cols: Iterable[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"CSV sem colunas obrigatórias: {missing}")


def expand_issue_type_filters(issue_types: Sequence[str]) -> set[str]:
    expanded: set[str] = set()
    for raw in issue_types:
        norm = normalize_text(raw)
        if not norm:
            continue
        expanded.add(norm)
        expanded |= ISSUE_TYPE_ALIASES.get(norm, set())
    return expanded


def load_events(path: str, project: str, issue_types: Sequence[str]) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    require_cols(df, REQUIRED_COLS)
    for c in ["Projeto", "Issue Key", "Author", "From Status", "To Status", "Tipo de Problema", "History Id"]:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].fillna("").astype(str)
    df["History Created"] = pd.to_datetime(df["History Created"], utc=True, errors="coerce")
    df = df.dropna(subset=["History Created"]).copy()
    allowed_projects = set(W1NNER_PROJECT_ALIASES)
    allowed_projects.add(normalize_text(project))
    df = df[df["Projeto"].map(normalize_text).isin(allowed_projects)].copy()
    allowed_types = expand_issue_type_filters(issue_types) or {"historia", "story", "task", "tarefa", "bug", "problema"}
    df = df[df["Tipo de Problema"].map(normalize_text).isin(allowed_types)].copy()
    if df.empty:
        return df
    df["Author"] = df["Author"].str.strip().replace("", "Sem Autor")
    for c in ["Issue Key", "From Status", "To Status", "Tipo de Problema", "Projeto"]:
        df[c] = df[c].str.strip()
    dedup_cols = [c for c in ["Issue Key", "History Id", "History Created", "From Status", "To Status", "Author"] if c in df.columns]
    df = df.drop_duplicates(subset=dedup_cols).sort_values(["Issue Key", "History Created", "To Status", "From Status"]).reset_index(drop=True)
    df["To Status Norm"] = df["To Status"].map(normalize_text)
    df["From Status Norm"] = df["From Status"].map(normalize_text)
    return df


def enrich_events(df: pd.DataFrame, expected_flow: Sequence[str], done_statuses: Sequence[str]) -> tuple[pd.DataFrame, dict[str, int], set[str]]:
    out = df.copy()
    flow_norm = [normalize_text(s) for s in expected_flow if str(s).strip()]
    idx_map = {s: i for i, s in enumerate(flow_norm)}
    done_norm = {normalize_text(s) for s in done_statuses if str(s).strip()} | DEFAULT_DONE_STATUSES
    g = out.groupby("Issue Key", sort=False)
    out["Event Seq"] = g.cumcount() + 1
    out["Prev Status Norm"] = g["To Status Norm"].shift(1)
    out["Prev Timestamp"] = g["History Created"].shift(1)
    out["Next Timestamp"] = g["History Created"].shift(-1)
    out["Stage Index"] = out["To Status Norm"].map(idx_map)
    out["Prev Stage Index"] = out["Prev Status Norm"].map(idx_map)
    out["Unknown Status"] = out["Stage Index"].isna()
    out["Self Loop"] = out["Prev Status Norm"].notna() & (out["Prev Status Norm"] == out["To Status Norm"])
    out["Backward Move"] = out["Stage Index"].notna() & out["Prev Stage Index"].notna() & (out["Stage Index"] < out["Prev Stage Index"])
    out["Forward Skip"] = out["Stage Index"].notna() & out["Prev Stage Index"].notna() & ((out["Stage Index"] - out["Prev Stage Index"]) > 1)
    out["Is Done Event"] = out["To Status Norm"].isin(done_norm)
    out["Reopen Transition"] = out["From Status Norm"].isin(done_norm) & (~out["To Status Norm"].isin(done_norm))
    out["QA Return"] = out["From Status Norm"].fillna("").map(lambda s: any(h in s for h in QA_HINTS)) & out["To Status Norm"].fillna("").map(lambda s: any(h in s for h in DEV_HINTS))
    dur = (out["Next Timestamp"] - out["History Created"]).dt.total_seconds() / 86400.0
    out["TempoStatusDias"] = dur.where(dur.notna() & (dur >= 0))
    return out, idx_map, done_norm


def summarize_cases(events: pd.DataFrame, done_norm: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for issue_key, g in events.groupby("Issue Key", sort=False):
        g = g.sort_values("History Created")
        statuses_norm = g["To Status Norm"].fillna("").tolist()
        first_ts = g["History Created"].iloc[0]
        last_ts = g["History Created"].iloc[-1]
        done_events = g[g["Is Done Event"]]
        final_done = done_events.iloc[-1] if not done_events.empty else None
        final_done_author = str(final_done["Author"]) if final_done is not None else "Sem Autor"
        final_done_date = pd.to_datetime(final_done["History Created"], utc=True) if final_done is not None else pd.NaT
        unknown = int(g["Unknown Status"].sum())
        self_loops = int(g["Self Loop"].sum())
        backward = int(g["Backward Move"].sum())
        skips = int(g["Forward Skip"].sum())
        reopen = int(g["Reopen Transition"].sum())
        qa_returns = int(g["QA Return"].sum())
        revisitas = int(len(statuses_norm) - len(set([s for s in statuses_norm if s])))
        ends_done = bool(g["To Status Norm"].iloc[-1] in done_norm)
        conform = (unknown == 0) and (self_loops == 0) and (backward == 0) and ends_done
        penalties = unknown + self_loops + (1.5 * backward) + (0.5 * skips) + (1.5 * reopen) + qa_returns
        score = max(0.0, 1.0 - penalties / max(1, len(g)))
        variant = " > ".join(g["To Status"].astype(str).tolist())
        lead_days = (last_ts - first_ts).total_seconds() / 86400.0
        rework_score = revisitas + self_loops + backward + reopen + qa_returns
        rows.append({
            "Issue Key": issue_key,
            "Projeto": str(g["Projeto"].iloc[0]),
            "Tipo de Problema": str(g["Tipo de Problema"].iloc[0]),
            "Eventos": int(len(g)),
            "Statuses Unicos": int(len(set([s for s in statuses_norm if s]))),
            "Revisitas Status": revisitas,
            "Self Loops": self_loops,
            "Backward Moves": backward,
            "Forward Skips": skips,
            "Reopen Count": reopen,
            "QA Returns": qa_returns,
            "Unknown Status Events": unknown,
            "Conforme Basico": "Sim" if conform else "Nao",
            "Conformance Score": round(float(score), 4),
            "Termina Em Done": "Sim" if ends_done else "Nao",
            "Primeiro Evento": first_ts.tz_convert(None) if getattr(first_ts, "tzinfo", None) else first_ts,
            "Ultimo Evento": last_ts.tz_convert(None) if getattr(last_ts, "tzinfo", None) else last_ts,
            "Lead Time Fluxo (dias)": round(float(lead_days), 4),
            "Done Final Author": final_done_author,
            "Done Final Date": final_done_date.tz_convert(None) if pd.notna(final_done_date) else pd.NaT,
            "Variant": variant,
            "Rework Score": int(rework_score),
        })
    case_df = pd.DataFrame(rows)
    if case_df.empty:
        return case_df, pd.DataFrame(columns=["Metrica", "Valor"])
    case_df = case_df.sort_values(["Rework Score", "Conformance Score"], ascending=[False, True], na_position="last").reset_index(drop=True)
    total = len(case_df)
    summary = pd.DataFrame([
        {"Metrica": "Casos analisados", "Valor": int(total)},
        {"Metrica": "Casos finalizados (Done)", "Valor": int((case_df["Termina Em Done"] == "Sim").sum())},
        {"Metrica": "Casos conformes (basico)", "Valor": int((case_df["Conforme Basico"] == "Sim").sum())},
        {"Metrica": "Taxa conformidade basica (%)", "Valor": round(float(((case_df["Conforme Basico"] == "Sim").mean()) * 100.0), 2)},
        {"Metrica": "Casos com retrabalho", "Valor": int((pd.to_numeric(case_df["Rework Score"], errors="coerce").fillna(0) > 0).sum())},
        {"Metrica": "Taxa retrabalho (%)", "Valor": round(float(((pd.to_numeric(case_df["Rework Score"], errors="coerce").fillna(0) > 0).mean()) * 100.0), 2)},
        {"Metrica": "Rework score medio", "Valor": round(float(pd.to_numeric(case_df["Rework Score"], errors="coerce").mean()), 3)},
        {"Metrica": "Conformance score medio", "Valor": round(float(pd.to_numeric(case_df["Conformance Score"], errors="coerce").mean()), 4)},
    ])
    return case_df, summary


def summarize_status_times(events: pd.DataFrame) -> pd.DataFrame:
    df = events.dropna(subset=["TempoStatusDias"]).copy()
    if df.empty:
        return pd.DataFrame(columns=["Status", "Qtde Ocorrencias", "Qtde Itens", "Tempo Medio (dias)", "Tempo Mediano (dias)", "P85 (dias)", "P95 (dias)"])
    rows = []
    for status, g in df.groupby("To Status", sort=False):
        s = pd.to_numeric(g["TempoStatusDias"], errors="coerce").dropna()
        if s.empty:
            continue
        rows.append({
            "Status": str(status),
            "Qtde Ocorrencias": int(len(g)),
            "Qtde Itens": int(g["Issue Key"].nunique()),
            "Tempo Medio (dias)": round(float(s.mean()), 4),
            "Tempo Mediano (dias)": round(float(s.median()), 4),
            "P85 (dias)": round(float(s.quantile(0.85)), 4),
            "P95 (dias)": round(float(s.quantile(0.95)), 4),
        })
    return pd.DataFrame(rows).sort_values("Tempo Medio (dias)", ascending=False, ignore_index=True) if rows else pd.DataFrame()


def summarize_people(case_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if case_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    done = case_df.dropna(subset=["Done Final Date"]).copy()
    if done.empty:
        return pd.DataFrame(), pd.DataFrame()
    done["Responsavel"] = done["Done Final Author"].fillna("").replace("", "Sem Autor")
    done["Semana"] = pd.to_datetime(done["Done Final Date"], errors="coerce").dt.to_period("W-SUN").dt.start_time
    done["Com Retrabalho"] = (pd.to_numeric(done["Rework Score"], errors="coerce").fillna(0) > 0).astype(int)
    weekly = (
        done.groupby(["Semana", "Responsavel"], dropna=False)
        .agg(**{"Itens Concluidos": ("Issue Key", "nunique"), "Itens Com Retrabalho": ("Com Retrabalho", "sum")})
        .reset_index()
    )
    weekly["Taxa Retrabalho (%)"] = np.where(weekly["Itens Concluidos"] > 0, weekly["Itens Com Retrabalho"] / weekly["Itens Concluidos"] * 100.0, 0.0)
    weekly = weekly.sort_values(["Semana", "Itens Concluidos"], ascending=[True, False]).reset_index(drop=True)
    summary = (
        done.groupby("Responsavel", dropna=False)
        .agg(
            **{
                "Itens Concluidos": ("Issue Key", "nunique"),
                "Itens Com Retrabalho": ("Com Retrabalho", "sum"),
                "Rework Score Total": ("Rework Score", "sum"),
                "Lead Time Mediano (dias)": ("Lead Time Fluxo (dias)", "median"),
                "Semanas Com Entrega": ("Semana", lambda x: x.dropna().nunique()),
            }
        )
        .reset_index()
    )
    summary["Taxa Retrabalho (%)"] = np.where(summary["Itens Concluidos"] > 0, summary["Itens Com Retrabalho"] / summary["Itens Concluidos"] * 100.0, 0.0)
    summary["Media Itens/Semana Ativa"] = np.where(summary["Semanas Com Entrega"] > 0, summary["Itens Concluidos"] / summary["Semanas Com Entrega"], 0.0)
    summary = summary.sort_values(["Itens Concluidos", "Taxa Retrabalho (%)", "Rework Score Total"], ascending=[False, False, False]).reset_index(drop=True)
    return weekly, summary


def summarize_variants(case_df: pd.DataFrame, max_top: int) -> pd.DataFrame:
    if case_df.empty or "Variant" not in case_df.columns:
        return pd.DataFrame()
    total = len(case_df)
    out = (
        case_df.groupby("Variant", dropna=False)
        .agg(**{"Qtde Casos": ("Issue Key", "count"), "Conformance Score Medio": ("Conformance Score", "mean"), "Rework Score Medio": ("Rework Score", "mean")})
        .reset_index()
    )
    out["Pct Casos"] = np.where(total > 0, out["Qtde Casos"] / total * 100.0, 0.0)
    out = out.sort_values(["Qtde Casos", "Pct Casos"], ascending=[False, False]).reset_index(drop=True)
    return out.head(max_top)


def build_pm4py_meta(events: pd.DataFrame) -> pd.DataFrame:
    rows = [{"Metrica": "pm4py_available", "Valor": str(PM4PY_AVAILABLE)}]
    if events.empty:
        return pd.DataFrame(rows)
    if not PM4PY_AVAILABLE:
        rows.append({"Metrica": "pm4py_note", "Valor": "pm4py não instalado; relatório gerado com pandas/heursticas."})
        return pd.DataFrame(rows)
    try:
        pm_df = events.rename(columns={"Issue Key": "case:concept:name", "To Status": "concept:name", "History Created": "time:timestamp", "Author": "org:resource"}).copy()
        pm_df = pm4py.format_dataframe(pm_df, case_id="case:concept:name", activity_key="concept:name", timestamp_key="time:timestamp")
        dfg, sa, ea = pm4py.discover_dfg(pm_df)
        rows.extend([
            {"Metrica": "pm4py_events", "Valor": int(len(pm_df))},
            {"Metrica": "pm4py_cases", "Valor": int(pm_df["case:concept:name"].nunique())},
            {"Metrica": "pm4py_activities", "Valor": int(pm_df["concept:name"].nunique())},
            {"Metrica": "pm4py_dfg_edges", "Valor": int(len(dfg))},
            {"Metrica": "pm4py_start_activities", "Valor": int(len(sa))},
            {"Metrica": "pm4py_end_activities", "Valor": int(len(ea))},
        ])
    except Exception as exc:
        rows.append({"Metrica": "pm4py_error", "Valor": str(exc)})
    return pd.DataFrame(rows)


def _csv_ready(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M:%S")
    return out


def write_outputs(out_dir: Path, prefix: str, datasets: dict[str, pd.DataFrame]) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{prefix}-{stamp}"
    excel = out_dir / f"{base}.xlsx"
    sheet_map = {
        "Metadados": datasets["metadados"],
        "ResumoConformidade": datasets["conformidade_resumo"],
        "ConformidadeCasos": datasets["conformidade_casos"],
        "RetrabalhoItens": datasets["retrabalho_itens"],
        "TemposPorStatus": datasets["tempos_status"],
        "VazaoPessoaSemanal": datasets["vazao_pessoa_semanal"],
        "VazaoPessoaResumo": datasets["vazao_pessoa_resumo"],
        "VariantesTop": datasets["variantes_top"],
        "EventosFiltrados": datasets["eventos_filtrados"],
    }
    excel_written = False
    excel_engine_used = None
    last_excel_error = None
    for engine in ("xlsxwriter", "openpyxl"):
        try:
            with pd.ExcelWriter(excel, engine=engine) as writer:
                for name, df in sheet_map.items():
                    _csv_ready(df).to_excel(writer, sheet_name=name[:31], index=False)
            excel_written = True
            excel_engine_used = engine
            break
        except ModuleNotFoundError as exc:
            last_excel_error = exc
            continue
    paths = {}
    if excel_written:
        paths["excel"] = str(excel)
        paths["excel_engine"] = str(excel_engine_used)
    elif last_excel_error is not None:
        print(f"Aviso: Excel não gerado ({last_excel_error}). Seguindo com saída CSV.")
    for key, df in datasets.items():
        csv_path = out_dir / f"{base}-{key}.csv"
        _csv_ready(df).to_csv(csv_path, index=False, encoding="utf-8-sig")
        paths[key] = str(csv_path)
    return paths


def main() -> int:
    args = parse_args()
    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {in_path}")
    out_dir = Path(args.out_dir) if str(args.out_dir).strip() else in_path.parent

    events = load_events(str(in_path), args.project, args.issue_types)
    if events.empty:
        print("Nenhum evento após filtros (W1NNER/W1NNR + História/Task/Bug).")
        return 1
    events_feat, _, done_norm = enrich_events(events, args.expected_flow, args.done_status)
    case_df, conf_sum = summarize_cases(events_feat, done_norm)
    rework_df = case_df[[
        c for c in [
            "Issue Key", "Tipo de Problema", "Rework Score", "Reopen Count", "Backward Moves",
            "QA Returns", "Revisitas Status", "Conformance Score", "Conforme Basico",
            "Lead Time Fluxo (dias)", "Done Final Author", "Done Final Date", "Variant"
        ] if c in case_df.columns
    ]].copy()
    rework_df = rework_df.sort_values(["Rework Score", "Reopen Count", "Backward Moves"], ascending=False).reset_index(drop=True) if not rework_df.empty else rework_df
    tempos_status = summarize_status_times(events_feat)
    vazao_sem, vazao_res = summarize_people(case_df)
    variantes = summarize_variants(case_df, max_top=max(5, int(args.max_top)))
    metadados = build_pm4py_meta(events_feat)

    export_events = events_feat.copy()
    for c in ["History Created", "Prev Timestamp", "Next Timestamp"]:
        if c in export_events.columns:
            export_events[c] = pd.to_datetime(export_events[c], errors="coerce").dt.tz_convert(None)

    datasets = {
        "metadados": metadados,
        "conformidade_resumo": conf_sum,
        "conformidade_casos": case_df,
        "retrabalho_itens": rework_df,
        "tempos_status": tempos_status,
        "vazao_pessoa_semanal": vazao_sem,
        "vazao_pessoa_resumo": vazao_res,
        "variantes_top": variantes,
        "eventos_filtrados": export_events,
    }
    paths = write_outputs(out_dir, args.prefix, datasets)
    print("Relatórios gerados:")
    for k, v in paths.items():
        print(f"- {k}: {v}")
    print(f"- eventos: {len(events_feat)}")
    print(f"- casos: {events_feat['Issue Key'].nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
