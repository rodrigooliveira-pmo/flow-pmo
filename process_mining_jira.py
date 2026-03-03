#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import shutil
import glob
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
    "Sprint Backlog",
    "In Progress",
    "Ready to Homologation",
    "Homologation",
    "QA Approved Hml",
    "Ready To Staging",
    "In Staging",
    "QA Approved Staging",
    "Ready for production",
    "Done",
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

WINDOWS_DEFAULT_LATEST_DIR = r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest"


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
    p.add_argument("--pm4py-align-max-cases", type=int, default=0, help="Limite de casos para alignments PM4Py (0=desabilita; default rápido)")
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


def summarize_person_hours(events: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Proxy de horas no fluxo por pessoa: aloca o tempo até a próxima transição ao autor que moveu o card
    para o status atual (`Author` + `To Status`).
    """
    if events.empty or "TempoStatusDias" not in events.columns:
        return pd.DataFrame(), pd.DataFrame()

    x = events.dropna(subset=["TempoStatusDias"]).copy()
    if x.empty:
        return pd.DataFrame(), pd.DataFrame()

    x["Author"] = x.get("Author", pd.Series(dtype=str)).fillna("").replace("", "Sem Autor").astype(str)
    x["To Status"] = x.get("To Status", pd.Series(dtype=str)).fillna("").astype(str)
    x["TempoStatusDias"] = pd.to_numeric(x["TempoStatusDias"], errors="coerce")
    x = x.dropna(subset=["TempoStatusDias"])
    x = x[x["TempoStatusDias"] >= 0].copy()
    if x.empty:
        return pd.DataFrame(), pd.DataFrame()

    x["HorasNoFluxo"] = x["TempoStatusDias"] * 24.0
    if "History Created" in x.columns:
        x["Semana"] = pd.to_datetime(x["History Created"], errors="coerce").dt.to_period("W-SUN").dt.start_time

    resumo = (
        x.groupby("Author", dropna=False)
        .agg(
            **{
                "HorasNoFluxo": ("HorasNoFluxo", "sum"),
                "HorasMediasPorEvento": ("HorasNoFluxo", "mean"),
                "Eventos": ("Issue Key", "count"),
                "CardsUnicos": ("Issue Key", "nunique"),
            }
        )
        .reset_index()
        .rename(columns={"Author": "Responsavel"})
    )
    resumo["HorasNoFluxo"] = pd.to_numeric(resumo["HorasNoFluxo"], errors="coerce").fillna(0).round(2)
    resumo["HorasMediasPorEvento"] = pd.to_numeric(resumo["HorasMediasPorEvento"], errors="coerce").fillna(0).round(2)
    resumo = resumo.sort_values("HorasNoFluxo", ascending=False).reset_index(drop=True)

    por_status = (
        x.groupby(["Author", "To Status"], dropna=False)
        .agg(
            **{
                "HorasNoFluxo": ("HorasNoFluxo", "sum"),
                "Eventos": ("Issue Key", "count"),
                "CardsUnicos": ("Issue Key", "nunique"),
            }
        )
        .reset_index()
        .rename(columns={"Author": "Responsavel", "To Status": "Status"})
    )
    por_status["HorasNoFluxo"] = pd.to_numeric(por_status["HorasNoFluxo"], errors="coerce").fillna(0).round(2)
    por_status = por_status.sort_values("HorasNoFluxo", ascending=False).reset_index(drop=True)
    return resumo, por_status


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


def _ensure_graphviz_dot_on_path() -> tuple[bool, str]:
    """
    Garantir que o executável `dot` (Graphviz) esteja acessível para visualizações do pm4py.
    Retorna (disponivel, detalhe).
    """
    dot_path = shutil.which("dot")
    if dot_path:
        return True, dot_path

    candidates: list[str] = []

    # Conda (Windows): Graphviz costuma instalar em Library/bin
    conda_prefix = os.getenv("CONDA_PREFIX", "").strip()
    if conda_prefix:
        candidates.append(os.path.join(conda_prefix, "Library", "bin"))
        candidates.append(os.path.join(conda_prefix, "bin"))

    # Instalações comuns do Graphviz no Windows
    program_files = os.getenv("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)")
    candidates.extend(
        [
            os.path.join(program_files, "Graphviz", "bin"),
            os.path.join(program_files_x86, "Graphviz", "bin"),
        ]
    )
    candidates.extend(glob.glob(os.path.join(program_files, "Graphviz*", "bin")))
    candidates.extend(glob.glob(os.path.join(program_files_x86, "Graphviz*", "bin")))

    checked = []
    for folder in candidates:
        if not folder or not os.path.isdir(folder):
            continue
        dot_exe = os.path.join(folder, "dot.exe")
        dot_unix = os.path.join(folder, "dot")
        checked.append(folder)
        if os.path.isfile(dot_exe) or os.path.isfile(dot_unix):
            os.environ["PATH"] = folder + os.pathsep + os.environ.get("PATH", "")
            found = shutil.which("dot")
            if found:
                return True, found

    detail = "dot_not_found"
    if checked:
        detail += " | checked: " + "; ".join(checked[:8])
    return False, detail


def build_pm4py_model_artifacts(
    events: pd.DataFrame,
    out_dir: Path,
    base: str,
    pm4py_align_max_cases: int = 500,
) -> tuple[dict[str, pd.DataFrame], dict[str, str], list[dict[str, Any]]]:
    extra_datasets: dict[str, pd.DataFrame] = {}
    extra_files: dict[str, str] = {}
    meta_rows: list[dict[str, Any]] = []
    if events.empty or not PM4PY_AVAILABLE:
        return extra_datasets, extra_files, meta_rows

    dot_ok, dot_detail = _ensure_graphviz_dot_on_path()
    meta_rows.append({"Metrica": "graphviz_dot_available", "Valor": str(dot_ok)})
    meta_rows.append({"Metrica": "graphviz_dot_path", "Valor": str(dot_detail)})

    try:
        pm_df = events.rename(
            columns={
                "Issue Key": "case:concept:name",
                "To Status": "concept:name",
                "History Created": "time:timestamp",
                "Author": "org:resource",
            }
        ).copy()
        pm_df = pm4py.format_dataframe(pm_df, case_id="case:concept:name", activity_key="concept:name", timestamp_key="time:timestamp")
    except Exception as exc:
        meta_rows.append({"Metrica": "pm4py_artifacts_error", "Valor": f"format_dataframe: {exc}"})
        return extra_datasets, extra_files, meta_rows
    case_order = (
        pm_df.sort_values(["case:concept:name", "time:timestamp"])
        ["case:concept:name"]
        .drop_duplicates()
        .astype(str)
        .tolist()
        if {"case:concept:name", "time:timestamp"}.issubset(pm_df.columns)
        else pm_df.get("case:concept:name", pd.Series(dtype=str)).astype(str).drop_duplicates().tolist()
    )

    def _dict_get_any(d: Any, keys: Sequence[str], default: Any = None) -> Any:
        if not isinstance(d, dict):
            return default
        for key in keys:
            if key in d:
                return d.get(key)
        return default

    def _perf_to_seconds(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float, np.integer, np.floating)):
            return float(value)
        if isinstance(value, pd.Timedelta):
            return float(value.total_seconds())
        if isinstance(value, dict):
            for key in ("mean", "median", "value", "performance", "avg"):
                if key in value:
                    return _perf_to_seconds(value.get(key))
        try:
            td = pd.to_timedelta(value)
            if pd.notna(td):
                return float(td.total_seconds())
        except Exception:
            pass
        try:
            return float(value)
        except Exception:
            return None

    # DFG data + image (frequency)
    try:
        dfg, sa, ea = pm4py.discover_dfg(pm_df)
        dfg_rows = []
        for edge, count in (dfg or {}).items():
            if not isinstance(edge, tuple) or len(edge) != 2:
                continue
            dfg_rows.append({"From": edge[0], "To": edge[1], "Count": int(count)})
        extra_datasets["pm4py_dfg_edges"] = pd.DataFrame(dfg_rows).sort_values("Count", ascending=False).reset_index(drop=True) if dfg_rows else pd.DataFrame()
        if dot_ok:
            try:
                dfg_img = out_dir / f"{base}-pm4py-dfg.png"
                pm4py.save_vis_dfg(dfg, sa, ea, str(dfg_img))
                extra_files["pm4py_dfg_png"] = str(dfg_img)
                meta_rows.append({"Metrica": "pm4py_dfg_png", "Valor": str(dfg_img)})
            except Exception as exc:
                meta_rows.append({"Metrica": "pm4py_dfg_vis_error", "Valor": str(exc)})
        else:
            meta_rows.append({"Metrica": "pm4py_dfg_vis_error", "Valor": "Graphviz 'dot' não encontrado no PATH"})
    except Exception as exc:
        meta_rows.append({"Metrica": "pm4py_dfg_error", "Valor": str(exc)})

    # DFG performance data + image
    try:
        dfg_perf, sa_perf, ea_perf = pm4py.discover_performance_dfg(pm_df)
        freq_lookup = {
            (str(r["From"]), str(r["To"])): int(r["Count"])
            for _, r in extra_datasets.get("pm4py_dfg_edges", pd.DataFrame()).iterrows()
            if {"From", "To", "Count"}.issubset(extra_datasets.get("pm4py_dfg_edges", pd.DataFrame()).columns)
        }
        perf_rows = []
        for edge, perf_val in (dfg_perf or {}).items():
            if not isinstance(edge, tuple) or len(edge) != 2:
                continue
            perf_seconds = _perf_to_seconds(perf_val)
            perf_rows.append(
                {
                    "From": edge[0],
                    "To": edge[1],
                    "Count": int(freq_lookup.get((str(edge[0]), str(edge[1])), 0)),
                    "PerfSeconds": perf_seconds,
                    "PerfHours": (perf_seconds / 3600.0) if perf_seconds is not None else None,
                }
            )
        extra_datasets["pm4py_dfg_perf_edges"] = (
            pd.DataFrame(perf_rows)
            .sort_values(["PerfSeconds", "Count"], ascending=[False, False], na_position="last")
            .reset_index(drop=True)
            if perf_rows
            else pd.DataFrame()
        )
        if dot_ok:
            perf_img = out_dir / f"{base}-pm4py-dfg-performance.png"
            perf_saved = False
            try:
                pm4py.save_vis_dfg(dfg_perf, sa_perf, ea_perf, str(perf_img), variant="performance")
                perf_saved = True
            except Exception as exc1:
                try:
                    if hasattr(pm4py, "save_vis_performance_dfg"):
                        pm4py.save_vis_performance_dfg(dfg_perf, sa_perf, ea_perf, str(perf_img))
                        perf_saved = True
                    else:
                        raise exc1
                except Exception as exc2:
                    meta_rows.append({"Metrica": "pm4py_dfg_performance_vis_error", "Valor": str(exc2)})
            if perf_saved:
                extra_files["pm4py_dfg_performance_png"] = str(perf_img)
                meta_rows.append({"Metrica": "pm4py_dfg_performance_png", "Valor": str(perf_img)})
        else:
            meta_rows.append({"Metrica": "pm4py_dfg_performance_vis_error", "Valor": "Graphviz 'dot' não encontrado no PATH"})
    except Exception as exc:
        meta_rows.append({"Metrica": "pm4py_dfg_performance_error", "Valor": str(exc)})

    # Heuristics miner image
    try:
        heu_net = pm4py.discover_heuristics_net(pm_df)
        if dot_ok:
            heu_img = out_dir / f"{base}-pm4py-heuristics.png"
            pm4py.save_vis_heuristics_net(heu_net, str(heu_img))
            extra_files["pm4py_heuristics_png"] = str(heu_img)
            meta_rows.append({"Metrica": "pm4py_heuristics_png", "Valor": str(heu_img)})
        else:
            meta_rows.append({"Metrica": "pm4py_heuristics_error", "Valor": "Graphviz 'dot' não encontrado no PATH"})
    except Exception as exc:
        meta_rows.append({"Metrica": "pm4py_heuristics_error", "Valor": str(exc)})

    # Inductive miner (process tree) image
    try:
        tree = pm4py.discover_process_tree_inductive(pm_df)
        if dot_ok:
            tree_img = out_dir / f"{base}-pm4py-inductive-tree.png"
            pm4py.save_vis_process_tree(tree, str(tree_img))
            extra_files["pm4py_inductive_tree_png"] = str(tree_img)
            meta_rows.append({"Metrica": "pm4py_inductive_tree_png", "Valor": str(tree_img)})
        else:
            meta_rows.append({"Metrica": "pm4py_inductive_tree_error", "Valor": "Graphviz 'dot' não encontrado no PATH"})
    except Exception as exc:
        meta_rows.append({"Metrica": "pm4py_inductive_tree_error", "Valor": str(exc)})

    net = im = fm = None
    # Inductive miner -> Petri net image
    try:
        net, im, fm = pm4py.discover_petri_net_inductive(pm_df)
        if dot_ok:
            petri_img = out_dir / f"{base}-pm4py-petri.png"
            pm4py.save_vis_petri_net(net, im, fm, str(petri_img))
            extra_files["pm4py_petri_png"] = str(petri_img)
            meta_rows.append({"Metrica": "pm4py_petri_png", "Valor": str(petri_img)})
        else:
            meta_rows.append({"Metrica": "pm4py_petri_error", "Valor": "Graphviz 'dot' não encontrado no PATH"})
    except Exception as exc:
        meta_rows.append({"Metrica": "pm4py_petri_error", "Valor": str(exc)})

    tbr_diag = None
    # Token-based replay (conformance)
    if net is not None and im is not None and fm is not None:
        try:
            tbr_summary_rows: list[dict[str, Any]] = []
            tbr_diag = pm4py.conformance_diagnostics_token_based_replay(pm_df, net, im, fm)
            tbr_case_rows = []
            for idx, row in enumerate(tbr_diag or []):
                issue_key = case_order[idx] if idx < len(case_order) else f"trace_{idx+1}"
                entry = row if isinstance(row, dict) else {}
                tbr_case_rows.append(
                    {
                        "Issue Key": issue_key,
                        "TraceIsFit": _dict_get_any(entry, ["trace_is_fit", "is_fit"]),
                        "TraceFitness": _dict_get_any(entry, ["trace_fitness", "fitness"]),
                        "MissingTokens": _dict_get_any(entry, ["missing_tokens", "missing"]),
                        "RemainingTokens": _dict_get_any(entry, ["remaining_tokens", "remaining"]),
                        "ConsumedTokens": _dict_get_any(entry, ["consumed_tokens", "consumed"]),
                        "ProducedTokens": _dict_get_any(entry, ["produced_tokens", "produced"]),
                    }
                )
            if tbr_case_rows:
                tbr_cases_df = pd.DataFrame(tbr_case_rows)
                for c in ["TraceFitness", "MissingTokens", "RemainingTokens", "ConsumedTokens", "ProducedTokens"]:
                    if c in tbr_cases_df.columns:
                        tbr_cases_df[c] = pd.to_numeric(tbr_cases_df[c], errors="coerce")
                extra_datasets["pm4py_tbr_cases"] = tbr_cases_df.sort_values(
                    ["TraceIsFit", "TraceFitness"], ascending=[True, True], na_position="last"
                ).reset_index(drop=True)
                # summary derived from diagnostics (avoids a second TBR replay pass)
                s = tbr_cases_df.copy()
                n_cases = int(len(s))
                fit_vals = pd.to_numeric(s.get("TraceFitness", pd.Series(dtype=float)), errors="coerce").dropna()
                is_fit = s.get("TraceIsFit", pd.Series(dtype=object))
                is_fit_bool = is_fit.map(
                    lambda v: (bool(v) if isinstance(v, (bool, np.bool_)) else str(v).strip().lower() in {"true", "1", "yes"})
                ) if len(is_fit) else pd.Series(dtype=bool)
                tbr_summary_rows.extend(
                    [
                        {"Metric": "num_cases", "Value": n_cases},
                        {"Metric": "perc_fit_traces", "Value": float((is_fit_bool.mean() * 100.0) if n_cases and len(is_fit_bool) else 0.0)},
                        {"Metric": "average_trace_fitness", "Value": float(fit_vals.mean()) if not fit_vals.empty else None},
                        {"Metric": "min_trace_fitness", "Value": float(fit_vals.min()) if not fit_vals.empty else None},
                    ]
                )
            else:
                extra_datasets["pm4py_tbr_cases"] = pd.DataFrame()
            extra_datasets["pm4py_tbr_summary"] = pd.DataFrame(tbr_summary_rows)
        except Exception as exc:
            meta_rows.append({"Metrica": "pm4py_tbr_error", "Valor": str(exc)})

    # Petri net decorated visuals via token replay (frequency/performance)
    if net is not None and im is not None and fm is not None and tbr_diag is not None and dot_ok:
        def _try_save_petri_variant(img_path: Path, variant_name: str, meta_ok_key: str, meta_err_key: str) -> bool:
            try:
                pm4py.save_vis_petri_net(net, im, fm, str(img_path), variant=variant_name, diagnostics=tbr_diag)
                extra_files[meta_ok_key] = str(img_path)
                meta_rows.append({"Metrica": meta_ok_key, "Valor": str(img_path)})
                return True
            except Exception as exc1:
                # Fallbacks for API differences across PM4Py versions
                fallback_attempts = [
                    {"variant": variant_name, "aggregated_statistics": tbr_diag},
                    {"variant": variant_name},
                ]
                for kwargs in fallback_attempts:
                    try:
                        pm4py.save_vis_petri_net(net, im, fm, str(img_path), **kwargs)
                        extra_files[meta_ok_key] = str(img_path)
                        meta_rows.append({"Metrica": meta_ok_key, "Valor": str(img_path)})
                        return True
                    except Exception:
                        continue
                meta_rows.append({"Metrica": meta_err_key, "Valor": str(exc1)})
                return False

        _try_save_petri_variant(
            out_dir / f"{base}-pm4py-petri-token-freq.png",
            "token_decoration_frequency",
            "pm4py_petri_token_freq_png",
            "pm4py_petri_token_freq_error",
        )
        _try_save_petri_variant(
            out_dir / f"{base}-pm4py-petri-token-perf.png",
            "token_decoration_performance",
            "pm4py_petri_token_perf_png",
            "pm4py_petri_token_perf_error",
        )
    elif net is not None and im is not None and fm is not None and not dot_ok:
        meta_rows.append({"Metrica": "pm4py_petri_token_freq_error", "Valor": "Graphviz 'dot' não encontrado no PATH"})
        meta_rows.append({"Metrica": "pm4py_petri_token_perf_error", "Valor": "Graphviz 'dot' não encontrado no PATH"})

    # Alignments (conformance, bounded)
    if net is not None and im is not None and fm is not None:
        try:
            max_cases = max(int(pm4py_align_max_cases or 0), 0)
        except Exception:
            max_cases = 500
        meta_rows.append({"Metrica": "pm4py_alignments_max_cases", "Valor": int(max_cases)})
        if max_cases <= 0:
            meta_rows.append({"Metrica": "pm4py_alignments_skipped", "Valor": "disabled_by_limit"})
        else:
            try:
                limited_cases = set(case_order[:max_cases])
                pm_align_df = pm_df[pm_df["case:concept:name"].astype(str).isin(limited_cases)].copy()
                align_case_order = (
                    pm_align_df.sort_values(["case:concept:name", "time:timestamp"])["case:concept:name"]
                    .drop_duplicates().astype(str).tolist()
                )
                aligned_traces = pm4py.conformance_diagnostics_alignments(pm_align_df, net, im, fm)

                def _normalize_move(raw: Any) -> tuple[str | None, str | None]:
                    if isinstance(raw, tuple):
                        # PM4Py often returns tuples like ((log_act, trans), (model_act, trans)) or variants
                        if len(raw) == 2 and isinstance(raw[0], tuple) and isinstance(raw[1], tuple):
                            log_act = raw[0][0] if raw[0] else None
                            model_act = raw[1][0] if raw[1] else None
                            return (None if log_act in (None, ">>") else str(log_act), None if model_act in (None, ">>") else str(model_act))
                        if len(raw) == 2:
                            a, b = raw
                            return (None if a in (None, ">>") else str(a), None if b in (None, ">>") else str(b))
                    if isinstance(raw, dict):
                        a = _dict_get_any(raw, ["label", "activity", "log_label"])
                        b = _dict_get_any(raw, ["model_label", "model_activity"])
                        return (None if a in (None, ">>") else str(a), None if b in (None, ">>") else str(b))
                    return (None, None)

                align_rows = []
                move_rows = []
                for idx, row in enumerate(aligned_traces or []):
                    issue_key = align_case_order[idx] if idx < len(align_case_order) else f"trace_{idx+1}"
                    entry = row if isinstance(row, dict) else {}
                    fitness = _dict_get_any(entry, ["fitness", "trace_fitness"])
                    cost = _dict_get_any(entry, ["cost", "alignment_cost"])
                    align_seq = _dict_get_any(entry, ["alignment", "moves"], default=[])
                    sync_moves = log_moves = model_moves = 0
                    for mv in (align_seq or []):
                        log_act, model_act = _normalize_move(mv)
                        if log_act and model_act and log_act == model_act:
                            sync_moves += 1
                        elif log_act and not model_act:
                            log_moves += 1
                            move_rows.append({"Issue Key": issue_key, "MoveType": "log_move", "Activity": log_act})
                        elif model_act and not log_act:
                            model_moves += 1
                            move_rows.append({"Issue Key": issue_key, "MoveType": "model_move", "Activity": model_act})
                        elif log_act or model_act:
                            # fallback mixed mismatch counts as both sides deviating
                            if log_act:
                                log_moves += 1
                                move_rows.append({"Issue Key": issue_key, "MoveType": "log_move", "Activity": log_act})
                            if model_act:
                                model_moves += 1
                                move_rows.append({"Issue Key": issue_key, "MoveType": "model_move", "Activity": model_act})
                    align_rows.append(
                        {
                            "Issue Key": issue_key,
                            "AlignmentFitness": fitness,
                            "AlignmentCost": cost,
                            "SyncMoves": sync_moves,
                            "LogMoves": log_moves,
                            "ModelMoves": model_moves,
                            "DesviosTotal": log_moves + model_moves,
                        }
                    )
                align_cases_df = pd.DataFrame(align_rows)
                if not align_cases_df.empty:
                    for c in ["AlignmentFitness", "AlignmentCost", "SyncMoves", "LogMoves", "ModelMoves", "DesviosTotal"]:
                        align_cases_df[c] = pd.to_numeric(align_cases_df[c], errors="coerce")
                    align_cases_df = align_cases_df.sort_values(
                        ["DesviosTotal", "AlignmentCost", "AlignmentFitness"],
                        ascending=[False, False, True],
                        na_position="last",
                    ).reset_index(drop=True)
                extra_datasets["pm4py_align_cases"] = align_cases_df

                align_summary_rows = []
                if not align_cases_df.empty:
                    fit_vals = pd.to_numeric(align_cases_df["AlignmentFitness"], errors="coerce").dropna()
                    cost_vals = pd.to_numeric(align_cases_df["AlignmentCost"], errors="coerce").dropna()
                    perfect = (pd.to_numeric(align_cases_df["DesviosTotal"], errors="coerce").fillna(0) == 0).mean() * 100.0
                    align_summary_rows = [
                        {"Metric": "num_cases_aligned", "Value": int(len(align_cases_df))},
                        {"Metric": "avg_fitness", "Value": float(fit_vals.mean()) if not fit_vals.empty else None},
                        {"Metric": "alignment_cost_total", "Value": float(cost_vals.sum()) if not cost_vals.empty else None},
                        {"Metric": "perc_perfect_alignments", "Value": float(perfect)},
                    ]
                extra_datasets["pm4py_align_summary"] = pd.DataFrame(align_summary_rows)

                move_df = pd.DataFrame(move_rows)
                if not move_df.empty:
                    move_top = (
                        move_df.groupby(["MoveType", "Activity"], dropna=False)
                        .agg(Count=("Issue Key", "size"), CasesAffected=("Issue Key", "nunique"))
                        .reset_index()
                        .sort_values(["Count", "CasesAffected"], ascending=False)
                        .reset_index(drop=True)
                    )
                else:
                    move_top = pd.DataFrame(columns=["MoveType", "Activity", "Count", "CasesAffected"])
                extra_datasets["pm4py_align_top_moves"] = move_top
                meta_rows.append({"Metrica": "pm4py_alignments_cases_processed", "Valor": int(len(align_case_order))})
            except Exception as exc:
                meta_rows.append({"Metrica": "pm4py_alignments_error", "Valor": str(exc)})

    return extra_datasets, extra_files, meta_rows


def _csv_ready(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M:%S")
    return out


def _copy_latest_artifact(source: Path, target: Path) -> bool:
    try:
        shutil.copy2(source, target)
        return True
    except Exception as exc:
        print(f"Aviso: falha ao atualizar latest ({target}): {exc}")
        return False


def _resolve_central_latest_dir(out_dir: Path) -> Path:
    env_latest_dir = str(os.getenv("FLOW_PMO_LATEST_DIR", "")).strip()
    if env_latest_dir:
        return Path(env_latest_dir)
    if os.name == "nt":
        return Path(WINDOWS_DEFAULT_LATEST_DIR)
    return out_dir / "latest"


def _publish_to_central_latest(latest_file: Path, central_latest_dir: Path) -> bool:
    try:
        source_abs = latest_file.resolve(strict=False)
        target = central_latest_dir / latest_file.name
        target_abs = target.resolve(strict=False)
        if source_abs == target_abs:
            return True
        central_latest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(latest_file, target)
        return True
    except Exception as exc:
        print(f"Aviso: falha ao publicar latest central ({latest_file.name}): {exc}")
        return False


def write_outputs(out_dir: Path, prefix: str, datasets: dict[str, pd.DataFrame], pm4py_align_max_cases: int = 500) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    central_latest_dir = _resolve_central_latest_dir(out_dir)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{prefix}-{stamp}"
    latest_base = f"{prefix}-latest"
    excel = out_dir / f"{base}.xlsx"

    pm_extra_datasets, pm_extra_files, pm_meta_rows = build_pm4py_model_artifacts(
        datasets.get("eventos_filtrados", pd.DataFrame()),
        out_dir=out_dir,
        base=base,
        pm4py_align_max_cases=pm4py_align_max_cases,
    )
    if pm_meta_rows:
        meta_df = datasets.get("metadados", pd.DataFrame())
        datasets["metadados"] = pd.concat([meta_df, pd.DataFrame(pm_meta_rows)], ignore_index=True)
    for key, df in pm_extra_datasets.items():
        datasets[key] = df

    sheet_map = {
        "Metadados": datasets["metadados"],
        "ResumoConformidade": datasets["conformidade_resumo"],
        "ConformidadeCasos": datasets["conformidade_casos"],
        "RetrabalhoItens": datasets["retrabalho_itens"],
        "TemposPorStatus": datasets["tempos_status"],
        "VazaoPessoaSemanal": datasets["vazao_pessoa_semanal"],
        "VazaoPessoaResumo": datasets["vazao_pessoa_resumo"],
        "HorasPessoaResumo": datasets.get("horas_pessoa_resumo", pd.DataFrame()),
        "HorasPessoaStatus": datasets.get("horas_pessoa_status", pd.DataFrame()),
        "VariantesTop": datasets["variantes_top"],
        "EventosFiltrados": datasets["eventos_filtrados"],
        "PM4PyDFGEdges": datasets.get("pm4py_dfg_edges", pd.DataFrame()),
        "PM4PyDFGPerfEdges": datasets.get("pm4py_dfg_perf_edges", pd.DataFrame()),
        "PM4PyTBRResumo": datasets.get("pm4py_tbr_summary", pd.DataFrame()),
        "PM4PyTBRCasos": datasets.get("pm4py_tbr_cases", pd.DataFrame()),
        "PM4PyAlignResumo": datasets.get("pm4py_align_summary", pd.DataFrame()),
        "PM4PyAlignCasos": datasets.get("pm4py_align_cases", pd.DataFrame()),
        "PM4PyAlignTopMoves": datasets.get("pm4py_align_top_moves", pd.DataFrame()),
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
        excel_latest = out_dir / f"{latest_base}.xlsx"
        if _copy_latest_artifact(excel, excel_latest):
            paths["excel_latest"] = str(excel_latest)
            _publish_to_central_latest(excel_latest, central_latest_dir)
    elif last_excel_error is not None:
        print(f"Aviso: Excel não gerado ({last_excel_error}). Seguindo com saída CSV.")
    for key, df in datasets.items():
        csv_path = out_dir / f"{base}-{key}.csv"
        _csv_ready(df).to_csv(csv_path, index=False, encoding="utf-8-sig")
        paths[key] = str(csv_path)
        csv_latest = out_dir / f"{latest_base}-{key}.csv"
        if _copy_latest_artifact(csv_path, csv_latest):
            paths[f"{key}_latest"] = str(csv_latest)
            _publish_to_central_latest(csv_latest, central_latest_dir)
    for key, value in pm_extra_files.items():
        paths[key] = value
        src = Path(value)
        if src.exists():
            latest_name = src.name
            if src.name.startswith(base):
                latest_name = latest_base + src.name[len(base):]
            latest_path = src.with_name(latest_name)
            if _copy_latest_artifact(src, latest_path):
                paths[f"{key}_latest"] = str(latest_path)
                _publish_to_central_latest(latest_path, central_latest_dir)
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
    horas_resumo, horas_status = summarize_person_hours(events_feat)
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
        "horas_pessoa_resumo": horas_resumo,
        "horas_pessoa_status": horas_status,
        "variantes_top": variantes,
        "eventos_filtrados": export_events,
    }
    paths = write_outputs(out_dir, args.prefix, datasets, pm4py_align_max_cases=args.pm4py_align_max_cases)
    print("Relatórios gerados:")
    for k, v in paths.items():
        print(f"- {k}: {v}")
    print(f"- eventos: {len(events_feat)}")
    print(f"- casos: {events_feat['Issue Key'].nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
