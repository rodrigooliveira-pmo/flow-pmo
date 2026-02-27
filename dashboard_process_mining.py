import base64
import json
import os
import platform
import re
import unicodedata
from datetime import datetime, time, timedelta

import dash
try:
    from dash import dcc, html, dash_table, Input, Output
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html
    from dash.dependencies import Input, Output
    import dash_table
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


if platform.system() == "Windows":
    LEGACY_DATA_FOLDER = r"C:\Users\W1 TI\OneDrive - W1\Documentos\Dados"
else:
    LEGACY_DATA_FOLDER = os.path.join(
        os.path.expanduser("~"),
        "Library",
        "CloudStorage",
        "OneDrive-W1",
        "Documentos",
        "Dados",
    )


def _existing_dirs(paths):
    out = []
    seen = set()
    for raw in paths:
        if not raw:
            continue
        p = os.path.abspath(str(raw).strip())
        if p in seen:
            continue
        seen.add(p)
        if os.path.isdir(p):
            out.append(p)
    return out


def candidate_data_folders():
    base_dir = os.path.dirname(__file__)
    home_dir = os.path.expanduser("~")
    env_dirs = os.getenv("FLOW_PMO_DATA_DIRS", "").strip()
    split_env_dirs = [p for p in env_dirs.split(os.pathsep) if p.strip()]
    return _existing_dirs(
        [
            os.getenv("FLOW_PMO_DATA_DIR", "").strip(),
            os.getenv("DATA_FOLDER", "").strip(),
            *split_env_dirs,
            os.path.join(home_dir, "Documents", "dados"),
            os.path.join(home_dir, "Documents", "Dados"),
            os.path.join(base_dir, "data"),
            base_dir,
            LEGACY_DATA_FOLDER,
        ]
    )


DATA_FOLDERS = candidate_data_folders()
EXECUTION_STATUS_HINTS = (
    "in progress",
    "desenvol",
    "development",
    "code review",
    "testing",
    "qa",
    "homolog",
    "staging",
)
ACTIVE_EXECUTION_STATUS_HINTS = (
    "in progress",
    "desenvol",
    "development",
    "code review",
)
VALIDATION_QA_STATUS_HINTS = (
    "testing",
    "qa",
    "homolog",
)
WAIT_EXECUTION_STATUS_HINTS = (
    "ready",
    "staging",
)
STATUS_EXECUTION_WEIGHTS = {
    "in progress": 1.0,
    "desenvolvimento": 1.0,
    "development": 1.0,
    "code review": 0.7,
    "testing/qa": 0.8,
    "testing": 0.8,
    "qa": 0.8,
    "homologation": 0.8,
    "homolog": 0.8,
    "in staging": 0.7,
    "staging": 0.5,
    "ready to homologation": 0.15,
    "qa approved hml": 0.1,
    "ready to staging": 0.1,
    "qa approved staging": 0.05,
    "ready for production": 0.05,
}
WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 18
WORKDAY_DAILY_CAP_HOURS = 8.0
PROJECT_BITBUCKET_PREFIX = {"W1NNER": "w1nner"}


def find_latest_process_mining_report():
    candidates = []
    for folder in DATA_FOLDERS:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low = name.lower()
            if low.startswith("w1nner-process-mining-") and low.endswith(".xlsx"):
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=os.path.getctime)


def load_report(path):
    sheet_names = [
        "ResumoConformidade",
        "ConformidadeCasos",
        "RetrabalhoItens",
        "TemposPorStatus",
        "VazaoPessoaSemanal",
        "VazaoPessoaResumo",
        "HorasPessoaResumo",
        "HorasPessoaStatus",
        "VariantesTop",
        "EventosFiltrados",
        "PM4PyDFGEdges",
        "PM4PyDFGPerfEdges",
        "PM4PyTBRResumo",
        "PM4PyTBRCasos",
        "PM4PyAlignResumo",
        "PM4PyAlignCasos",
        "PM4PyAlignTopMoves",
        "Metadados",
    ]
    xls = pd.ExcelFile(path)
    out = {}
    for sheet in sheet_names:
        out[sheet] = pd.read_excel(xls, sheet_name=sheet) if sheet in xls.sheet_names else pd.DataFrame()
    return out


def create_kpi_card(title, value):
    return html.Div(
        [
            html.Div(title, style={"fontSize": "14px", "color": "#555", "marginBottom": "6px"}),
            html.Div(str(value), style={"fontSize": "28px", "fontWeight": "600"}),
        ],
        style={
            "border": "1px solid #e5e7eb",
            "borderRadius": "10px",
            "padding": "12px",
            "background": "white",
            "boxShadow": "0 1px 4px rgba(0,0,0,0.04)",
        },
    )


def _load_artifact_images_from_base(base_no_ext):
    img_suffixes = {
        "dfg": "-pm4py-dfg.png",
        "dfg_performance": "-pm4py-dfg-performance.png",
        "heuristics": "-pm4py-heuristics.png",
        "inductive_tree": "-pm4py-inductive-tree.png",
        "petri": "-pm4py-petri.png",
    }
    out = {}
    for key, suffix in img_suffixes.items():
        path = f"{base_no_ext}{suffix}"
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                out[key] = {"path": path, "b64": base64.b64encode(f.read()).decode("ascii")}
        except Exception:
            continue
    return out


def _safe_num(series):
    return pd.to_numeric(series, errors="coerce")


def _normalize_person_name(raw_name):
    if raw_name is None or (isinstance(raw_name, float) and pd.isna(raw_name)):
        return ""
    name = str(raw_name).strip()
    if not name or name.lower() in {"nan", "none"}:
        return ""
    if "<" in name:
        name = name.split("<", 1)[0].strip()
    return re.sub(r"\s+", " ", name).strip()


def _normalize_text(value):
    txt = str(value or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", txt)
    no_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", no_accents)).strip()


def _person_key(raw_name):
    return _normalize_text(_normalize_person_name(raw_name))


def _split_people_field(raw_value):
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return []
    text = str(raw_value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return []
    out = []
    for part in text.split("|"):
        person = _normalize_person_name(part)
        if person:
            out.append(person)
    return out


def _load_bitbucket_prefix_map():
    raw = os.getenv("FLOW_PMO_BITBUCKET_PREFIX_MAP", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    if not isinstance(parsed, dict):
        return {}
    out = {}
    for key, value in parsed.items():
        project_key = str(key).strip().upper()
        prefix = str(value).strip().lower()
        if project_key and prefix:
            out[project_key] = prefix
    return out


def _load_project_bitbucket_csv(project_prefix, suffix):
    if not project_prefix:
        return pd.DataFrame()
    candidates = []
    for folder in DATA_FOLDERS:
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low = name.lower()
            if low.startswith(project_prefix.lower()) and low.endswith(suffix):
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    candidates.append(path)
    if not candidates:
        return pd.DataFrame()
    latest = max(candidates, key=os.path.getctime)
    try:
        return pd.read_csv(latest)
    except Exception:
        return pd.DataFrame()


def load_project_bitbucket_logs(projeto):
    project_key = str(projeto or "").strip().upper()
    if not project_key:
        return {"commits": pd.DataFrame(), "pullrequests": pd.DataFrame(), "pipelines": pd.DataFrame()}
    env_map = _load_bitbucket_prefix_map()
    prefix = env_map.get(project_key) or PROJECT_BITBUCKET_PREFIX.get(project_key)
    if not prefix:
        return {"commits": pd.DataFrame(), "pullrequests": pd.DataFrame(), "pipelines": pd.DataFrame()}

    commits = _load_project_bitbucket_csv(prefix, "_commits.csv")
    pullrequests = _load_project_bitbucket_csv(prefix, "_pullrequests.csv")
    pipelines = _load_project_bitbucket_csv(prefix, "_pipelines.csv")

    if not commits.empty and "date" in commits.columns:
        commits["date"] = pd.to_datetime(commits["date"], errors="coerce", utc=True).dt.tz_localize(None)
    if not pullrequests.empty:
        if "created_on" in pullrequests.columns:
            pullrequests["created_on"] = pd.to_datetime(pullrequests["created_on"], errors="coerce", utc=True).dt.tz_localize(None)
        if "updated_on" in pullrequests.columns:
            pullrequests["updated_on"] = pd.to_datetime(pullrequests["updated_on"], errors="coerce", utc=True).dt.tz_localize(None)
        if "state" in pullrequests.columns:
            pullrequests["state_norm"] = pullrequests["state"].astype(str).str.strip().str.lower()
    if not pipelines.empty:
        if "created_on" in pipelines.columns:
            pipelines["created_on"] = pd.to_datetime(pipelines["created_on"], errors="coerce", utc=True).dt.tz_localize(None)
        if "completed_on" in pipelines.columns:
            pipelines["completed_on"] = pd.to_datetime(pipelines["completed_on"], errors="coerce", utc=True).dt.tz_localize(None)
    return {"commits": commits, "pullrequests": pullrequests, "pipelines": pipelines}


def compute_bitbucket_person_metrics(bitbucket_logs, start_ts, end_ts):
    commits = bitbucket_logs.get("commits", pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    pullrequests = bitbucket_logs.get("pullrequests", pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    stats = {}

    def apply_time_window(df, col):
        if df is None or df.empty or col not in df.columns:
            return df
        out = df.copy()
        if start_ts is not None:
            out = out[out[col] >= pd.to_datetime(start_ts)]
        if end_ts is not None:
            out = out[out[col] < pd.to_datetime(end_ts)]
        return out

    def ensure_person(raw_name):
        person = _normalize_person_name(raw_name)
        if not person:
            return None
        key = _person_key(person) or person.lower()
        if key not in stats:
            stats[key] = {
                "Pessoa": person,
                "Commits": 0,
                "PRs Abertos": 0,
                "PRs Merged": 0,
                "PRs Declinados": 0,
                "Aprovacoes": 0,
                "Reprovacoes": 0,
            }
        return key

    if not commits.empty and {"author", "date"}.issubset(commits.columns):
        c = apply_time_window(commits, "date")
        for author_name, count in c["author"].value_counts(dropna=True).items():
            pkey = ensure_person(author_name)
            if pkey:
                stats[pkey]["Commits"] += int(count)

    if not pullrequests.empty:
        prs = pullrequests.copy()
        opened = apply_time_window(prs, "created_on") if "created_on" in prs.columns else prs
        for author_name, count in opened.get("author", pd.Series(dtype=str)).value_counts(dropna=True).items():
            pkey = ensure_person(author_name)
            if pkey:
                stats[pkey]["PRs Abertos"] += int(count)

        if {"updated_on", "state_norm"}.issubset(prs.columns):
            updated = apply_time_window(prs, "updated_on")
            merged = updated[updated["state_norm"] == "merged"]
            declined = updated[updated["state_norm"] == "declined"]
            for author_name, count in merged.get("author", pd.Series(dtype=str)).value_counts(dropna=True).items():
                pkey = ensure_person(author_name)
                if pkey:
                    stats[pkey]["PRs Merged"] += int(count)
            for author_name, count in declined.get("author", pd.Series(dtype=str)).value_counts(dropna=True).items():
                pkey = ensure_person(author_name)
                if pkey:
                    stats[pkey]["PRs Declinados"] += int(count)
            review = updated
        else:
            review = opened

        for _, row in review.iterrows():
            for approver in _split_people_field(row.get("approved_by")):
                pkey = ensure_person(approver)
                if pkey:
                    stats[pkey]["Aprovacoes"] += 1
            for rejector in _split_people_field(row.get("changes_requested_by")):
                pkey = ensure_person(rejector)
                if pkey:
                    stats[pkey]["Reprovacoes"] += 1

    if not stats:
        return pd.DataFrame(columns=["Pessoa"]), {}
    out = pd.DataFrame(stats.values())
    out["Total Contribuicoes BB"] = (
        out["Commits"]
        + out["PRs Abertos"]
        + out["PRs Merged"]
        + out["Aprovacoes"]
        + out["Reprovacoes"]
    )
    out = out.sort_values(["Total Contribuicoes BB", "Pessoa"], ascending=[False, True]).reset_index(drop=True)
    totals = {
        "Commits": int(out["Commits"].sum()),
        "PRs Abertos": int(out["PRs Abertos"].sum()),
        "PRs Merged": int(out["PRs Merged"].sum()),
        "PRs Declinados": int(out["PRs Declinados"].sum()),
        "Aprovacoes": int(out["Aprovacoes"].sum()),
        "Reprovacoes": int(out["Reprovacoes"].sum()),
    }
    return out, totals


def compute_pm_bitbucket_cross_metrics(pm_people, pm_cases, bitbucket_logs, start_ts, end_ts):
    bb_df, bb_totals = compute_bitbucket_person_metrics(bitbucket_logs, start_ts, end_ts)

    if pm_people is None or pm_people.empty or "Responsavel" not in pm_people.columns:
        jira_df = pd.DataFrame(columns=["Pessoa"])
    else:
        jira_df = pm_people.copy()
        jira_df["Pessoa"] = jira_df["Responsavel"].map(_normalize_person_name)
        jira_df = jira_df[jira_df["Pessoa"].astype(str).str.strip().ne("")]
        rename_map = {}
        if "Itens Concluidos" in jira_df.columns:
            rename_map["Itens Concluidos"] = "Itens Concluidos"
        if "Itens Com Retrabalho" in jira_df.columns:
            rename_map["Itens Com Retrabalho"] = "Itens Com Retrabalho"
        if "Taxa Retrabalho (%)" in jira_df.columns:
            rename_map["Taxa Retrabalho (%)"] = "Taxa Retrabalho (%)"
        keep_cols = ["Pessoa", *rename_map.keys()]
        jira_df = jira_df[keep_cols].rename(columns=rename_map)

    if "Pessoa" not in bb_df.columns:
        bb_df = pd.DataFrame(columns=["Pessoa"])
    if "Pessoa" not in jira_df.columns:
        jira_df = pd.DataFrame(columns=["Pessoa"])
    merged = pd.merge(jira_df, bb_df, on="Pessoa", how="outer")
    if merged.empty:
        return merged, {}, bb_totals

    num_cols = [
        "Itens Concluidos",
        "Itens Com Retrabalho",
        "Taxa Retrabalho (%)",
        "Commits",
        "PRs Abertos",
        "PRs Merged",
        "PRs Declinados",
        "Aprovacoes",
        "Reprovacoes",
        "Total Contribuicoes BB",
    ]
    for col in num_cols:
        if col not in merged.columns:
            merged[col] = 0
        merged[col] = _safe_num(merged[col]).fillna(0)

    tech_keys = set()
    for src_df in [bitbucket_logs.get("commits", pd.DataFrame()), bitbucket_logs.get("pullrequests", pd.DataFrame())]:
        if src_df is None or src_df.empty:
            continue
        date_col = "date" if "date" in src_df.columns else "created_on"
        if date_col in src_df.columns:
            if start_ts is not None:
                src_df = src_df[src_df[date_col] >= pd.to_datetime(start_ts)]
            if end_ts is not None:
                src_df = src_df[src_df[date_col] < pd.to_datetime(end_ts)]
        if "work_item_keys" in src_df.columns:
            for raw in src_df["work_item_keys"].fillna(""):
                for k in str(raw).split("|"):
                    key = str(k).strip().upper()
                    if key:
                        tech_keys.add(key)
        if "primary_work_item_key" in src_df.columns:
            for key in src_df["primary_work_item_key"].fillna("").astype(str):
                key = key.strip().upper()
                if key:
                    tech_keys.add(key)

    merged["Itens c/ Evidencia Tecnica"] = 0
    if pm_cases is not None and not pm_cases.empty and "Issue Key" in pm_cases.columns and "Done Final Author" in pm_cases.columns:
        c = pm_cases.copy()
        c["Pessoa"] = c["Done Final Author"].map(_normalize_person_name)
        c["Issue Key"] = c["Issue Key"].astype(str).str.strip().str.upper()
        c = c[c["Pessoa"].astype(str).str.strip().ne("") & c["Issue Key"].ne("")]
        if not c.empty:
            c["TemEvidenciaTecnica"] = c["Issue Key"].isin(tech_keys)
            by_person = c.groupby("Pessoa", dropna=False)["TemEvidenciaTecnica"].sum()
            merged["Itens c/ Evidencia Tecnica"] = merged["Pessoa"].map(by_person).fillna(0)

    merged["Cobertura Tecnica (%)"] = np.where(
        merged["Itens Concluidos"] > 0,
        merged["Itens c/ Evidencia Tecnica"] / merged["Itens Concluidos"] * 100.0,
        0.0,
    )
    merged["Score Integrado"] = (
        merged["Itens Concluidos"]
        + merged["PRs Merged"]
        + merged["Aprovacoes"]
        + merged["Reprovacoes"]
        + (merged["Commits"] / 5.0)
    )
    merged = merged.sort_values(["Score Integrado", "Itens Concluidos", "Total Contribuicoes BB", "Pessoa"], ascending=[False, False, False, True]).reset_index(drop=True)

    cross_totals = {
        "Itens Concluidos": int(_safe_num(merged["Itens Concluidos"]).fillna(0).sum()),
        "Itens c/ Evidencia Tecnica": int(_safe_num(merged["Itens c/ Evidencia Tecnica"]).fillna(0).sum()),
        "Cobertura Tecnica (%)": float((_safe_num(merged["Itens c/ Evidencia Tecnica"]).sum() / max(_safe_num(merged["Itens Concluidos"]).sum(), 1)) * 100.0),
        "Commits": int(_safe_num(merged["Commits"]).fillna(0).sum()),
        "PRs Merged": int(_safe_num(merged["PRs Merged"]).fillna(0).sum()),
        "Aprovacoes": int(_safe_num(merged["Aprovacoes"]).fillna(0).sum()),
        "Reprovacoes": int(_safe_num(merged["Reprovacoes"]).fillna(0).sum()),
    }
    return merged, cross_totals, bb_totals


def compute_pm_bitbucket_cross_weekly(pm_cases, bitbucket_logs, start_ts, end_ts):
    frames = []

    def apply_time(df, col):
        if df is None or df.empty or col not in df.columns:
            return pd.DataFrame()
        x = df.copy()
        if start_ts is not None:
            x = x[x[col] >= pd.to_datetime(start_ts)]
        if end_ts is not None:
            x = x[x[col] < pd.to_datetime(end_ts)]
        return x

    if pm_cases is not None and not pm_cases.empty and {"Done Final Author", "Done Final Date"}.issubset(pm_cases.columns):
        jira = pm_cases.copy()
        jira["Done Final Date"] = pd.to_datetime(jira["Done Final Date"], errors="coerce")
        jira = jira.dropna(subset=["Done Final Date"])
        jira = apply_time(jira, "Done Final Date")
        jira["Pessoa"] = jira["Done Final Author"].map(_normalize_person_name)
        jira = jira[jira["Pessoa"].astype(str).str.strip().ne("")]
        if not jira.empty:
            jira["Semana"] = jira["Done Final Date"].dt.to_period("W-SUN").dt.start_time
            done_weekly = (
                jira.groupby(["Semana", "Pessoa"], dropna=False)
                .size()
                .reset_index(name="Itens Concluidos")
            )
            frames.append(done_weekly)

    commits = bitbucket_logs.get("commits", pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    if commits is not None and not commits.empty and {"author", "date"}.issubset(commits.columns):
        c = apply_time(commits, "date")
        c["Pessoa"] = c["author"].map(_normalize_person_name)
        c = c[c["Pessoa"].astype(str).str.strip().ne("")]
        if not c.empty:
            c["Semana"] = c["date"].dt.to_period("W-SUN").dt.start_time
            frames.append(c.groupby(["Semana", "Pessoa"], dropna=False).size().reset_index(name="Commits"))

    pullrequests = bitbucket_logs.get("pullrequests", pd.DataFrame()) if isinstance(bitbucket_logs, dict) else pd.DataFrame()
    if pullrequests is not None and not pullrequests.empty:
        if {"author", "created_on"}.issubset(pullrequests.columns):
            prs_open = apply_time(pullrequests, "created_on")
            prs_open["Pessoa"] = prs_open["author"].map(_normalize_person_name)
            prs_open = prs_open[prs_open["Pessoa"].astype(str).str.strip().ne("")]
            if not prs_open.empty:
                prs_open["Semana"] = prs_open["created_on"].dt.to_period("W-SUN").dt.start_time
                frames.append(prs_open.groupby(["Semana", "Pessoa"], dropna=False).size().reset_index(name="PRs Abertos"))
        if {"author", "updated_on", "state_norm"}.issubset(pullrequests.columns):
            prs_upd = apply_time(pullrequests, "updated_on")
            prs_merged = prs_upd[prs_upd["state_norm"] == "merged"].copy()
            prs_merged["Pessoa"] = prs_merged["author"].map(_normalize_person_name)
            prs_merged = prs_merged[prs_merged["Pessoa"].astype(str).str.strip().ne("")]
            if not prs_merged.empty:
                prs_merged["Semana"] = prs_merged["updated_on"].dt.to_period("W-SUN").dt.start_time
                frames.append(prs_merged.groupby(["Semana", "Pessoa"], dropna=False).size().reset_index(name="PRs Merged"))
            prs_review = prs_upd.copy()
            for src_col, metric_col in [("approved_by", "Aprovacoes"), ("changes_requested_by", "Reprovacoes")]:
                if src_col not in prs_review.columns:
                    continue
                rv = prs_review[["updated_on", src_col]].copy()
                rv["Pessoa"] = rv[src_col].apply(_split_people_field)
                rv = rv.explode("Pessoa")
                rv["Pessoa"] = rv["Pessoa"].map(_normalize_person_name)
                rv = rv[rv["Pessoa"].astype(str).str.strip().ne("")]
                if rv.empty:
                    continue
                rv["Semana"] = rv["updated_on"].dt.to_period("W-SUN").dt.start_time
                frames.append(rv.groupby(["Semana", "Pessoa"], dropna=False).size().reset_index(name=metric_col))

    if not frames:
        return pd.DataFrame()

    out = frames[0].copy()
    for f in frames[1:]:
        out = out.merge(f, on=["Semana", "Pessoa"], how="outer")

    for col in ["Itens Concluidos", "Commits", "PRs Abertos", "PRs Merged", "Aprovacoes", "Reprovacoes"]:
        if col not in out.columns:
            out[col] = 0
        out[col] = _safe_num(out[col]).fillna(0)

    out["Score Integrado"] = (
        out["Itens Concluidos"]
        + out["PRs Merged"]
        + out["Aprovacoes"]
        + out["Reprovacoes"]
        + (out["Commits"] / 5.0)
    )
    out = out.sort_values(["Semana", "Score Integrado", "Pessoa"], ascending=[True, False, True]).reset_index(drop=True)
    return out


def is_execution_status(status_name: str) -> bool:
    s = str(status_name or "").strip().lower()
    return any(h in s for h in EXECUTION_STATUS_HINTS)


def execution_status_bucket(status_name: str) -> str:
    s = str(status_name or "").strip().lower()
    if any(h in s for h in ACTIVE_EXECUTION_STATUS_HINTS):
        return "Execucao Ativa"
    if any(h in s for h in VALIDATION_QA_STATUS_HINTS):
        return "Validacao/QA"
    if any(h in s for h in WAIT_EXECUTION_STATUS_HINTS):
        return "Espera"
    return "Nao Execucao"


def execution_status_weight(status_name: str) -> float:
    s = str(status_name or "").strip().lower()
    for key, weight in STATUS_EXECUTION_WEIGHTS.items():
        if key in s:
            return float(weight)
    if execution_status_bucket(s) == "Execucao Ativa":
        return 1.0
    if execution_status_bucket(s) == "Validacao/QA":
        return 0.8
    if execution_status_bucket(s) == "Espera":
        return 0.4
    return 0.0


def compute_overlap_hours(events_df: pd.DataFrame, start_ts=None, end_ts=None) -> pd.DataFrame:
    """
    Calcula horas no período por evento usando interseção do intervalo:
    [History Created, Next Timestamp] com [start_ts, end_ts+1d].
    Fallback para TempoStatusDias*24 se não houver Next Timestamp.
    """
    if events_df is None or events_df.empty:
        return pd.DataFrame()
    x = events_df.copy()
    if "History Created" not in x.columns:
        return pd.DataFrame()
    x["History Created"] = pd.to_datetime(x["History Created"], errors="coerce")
    if "Next Timestamp" in x.columns:
        x["Next Timestamp"] = pd.to_datetime(x["Next Timestamp"], errors="coerce")
    else:
        x["Next Timestamp"] = pd.NaT
    if "TempoStatusDias" in x.columns:
        x["TempoStatusDias"] = _safe_num(x["TempoStatusDias"])
    else:
        x["TempoStatusDias"] = np.nan
    x = x.dropna(subset=["History Created"]).copy()
    if x.empty:
        return x

    if start_ts is None or end_ts is None:
        x["HorasNoPeriodo"] = (x["TempoStatusDias"] * 24.0).fillna(0)
        return x

    window_start = pd.to_datetime(start_ts)
    window_end = pd.to_datetime(end_ts) + pd.Timedelta(days=1)
    starts = x["History Created"].clip(lower=window_start, upper=window_end)
    raw_ends = x["Next Timestamp"].copy()
    # Fallback: se não existe próxima transição, usa duração estimada pela coluna de tempo em status.
    missing_end = raw_ends.isna()
    raw_ends.loc[missing_end] = x.loc[missing_end, "History Created"] + pd.to_timedelta(
        x.loc[missing_end, "TempoStatusDias"].fillna(0), unit="D"
    )
    ends = raw_ends.clip(lower=window_start, upper=window_end)
    overlap_h = (ends - starts).dt.total_seconds() / 3600.0
    x["HorasNoPeriodo"] = overlap_h.where(overlap_h.notna() & (overlap_h > 0), 0.0)
    return x


def business_hours_overlap(start_dt, end_dt, work_start_hour=WORKDAY_START_HOUR, work_end_hour=WORKDAY_END_HOUR, daily_cap_hours=WORKDAY_DAILY_CAP_HOURS) -> float:
    """Horas úteis em dias úteis no intervalo [start_dt, end_dt], com teto diário."""
    if pd.isna(start_dt) or pd.isna(end_dt):
        return 0.0
    start_dt = pd.to_datetime(start_dt)
    end_dt = pd.to_datetime(end_dt)
    if end_dt <= start_dt:
        return 0.0

    total = 0.0
    cur_date = start_dt.date()
    last_date = end_dt.date()
    while cur_date <= last_date:
        if cur_date.weekday() < 5:  # Mon-Fri
            day_start = pd.Timestamp(datetime.combine(cur_date, time(hour=work_start_hour)))
            day_end = pd.Timestamp(datetime.combine(cur_date, time(hour=work_end_hour)))
            seg_start = max(start_dt, day_start)
            seg_end = min(end_dt, day_end)
            if seg_end > seg_start:
                hours = (seg_end - seg_start).total_seconds() / 3600.0
                total += max(0.0, min(float(daily_cap_hours), hours))
        cur_date = cur_date + timedelta(days=1)
    return round(total, 4)


def add_business_hours_overlap(events_df: pd.DataFrame, start_ts=None, end_ts=None) -> pd.DataFrame:
    """Acrescenta `HorasUteisPeriodo` por evento com base em dias úteis/horário comercial/teto diário."""
    x = compute_overlap_hours(events_df, start_ts=start_ts, end_ts=end_ts)
    if x.empty:
        x["HorasUteisPeriodo"] = pd.Series(dtype=float)
        return x
    window_start = pd.to_datetime(start_ts) if start_ts is not None else None
    window_end = (pd.to_datetime(end_ts) + pd.Timedelta(days=1)) if end_ts is not None else None

    starts = pd.to_datetime(x.get("History Created"), errors="coerce")
    ends = pd.to_datetime(x.get("Next Timestamp"), errors="coerce")
    if "TempoStatusDias" in x.columns:
        fallback_ends = starts + pd.to_timedelta(_safe_num(x["TempoStatusDias"]).fillna(0), unit="D")
        ends = ends.fillna(fallback_ends)
    if window_start is not None:
        starts = starts.clip(lower=window_start)
        ends = ends.clip(lower=window_start)
    if window_end is not None:
        starts = starts.clip(upper=window_end)
        ends = ends.clip(upper=window_end)

    x["HorasUteisPeriodo"] = [
        business_hours_overlap(s, e)
        for s, e in zip(starts.tolist(), ends.tolist())
    ]
    x["PeriodoStart"] = starts
    x["PeriodoEnd"] = ends
    return x


def business_hours_daily_slices(start_dt, end_dt, work_start_hour=WORKDAY_START_HOUR, work_end_hour=WORKDAY_END_HOUR, daily_cap_hours=WORKDAY_DAILY_CAP_HOURS):
    """Retorna slices diários úteis (dia, horas) para um intervalo, com teto diário por evento."""
    if pd.isna(start_dt) or pd.isna(end_dt):
        return []
    start_dt = pd.to_datetime(start_dt)
    end_dt = pd.to_datetime(end_dt)
    if end_dt <= start_dt:
        return []
    out = []
    cur_date = start_dt.date()
    last_date = end_dt.date()
    while cur_date <= last_date:
        if cur_date.weekday() < 5:
            day_start = pd.Timestamp(datetime.combine(cur_date, time(hour=work_start_hour)))
            day_end = pd.Timestamp(datetime.combine(cur_date, time(hour=work_end_hour)))
            seg_start = max(start_dt, day_start)
            seg_end = min(end_dt, day_end)
            if seg_end > seg_start:
                hours = (seg_end - seg_start).total_seconds() / 3600.0
                out.append((pd.Timestamp(cur_date), max(0.0, min(float(daily_cap_hours), hours))))
        cur_date = cur_date + timedelta(days=1)
    return out


def explode_event_business_daily_slices(events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Explode eventos em slices diários úteis usando PeriodoStart/PeriodoEnd.
    Útil para normalizar capacidade por pessoa/dia e reduzir superestimação por cards simultâneos.
    """
    if events_df is None or events_df.empty:
        return pd.DataFrame()
    needed = {"PeriodoStart", "PeriodoEnd"}
    if not needed.issubset(events_df.columns):
        return pd.DataFrame()
    rows = []
    for _, r in events_df.iterrows():
        start_dt = r.get("PeriodoStart")
        end_dt = r.get("PeriodoEnd")
        slices = business_hours_daily_slices(start_dt, end_dt)
        if not slices:
            continue
        author = str(r.get("Author", "") or "").strip() or "Sem Autor"
        issue_key = str(r.get("Issue Key", "") or "")
        status = str(r.get("To Status", "") or "")
        bucket = str(r.get("ExecBucket", "") or "")
        weight = float(pd.to_numeric(pd.Series([r.get("ExecWeight", 0.0)]), errors="coerce").fillna(0).iloc[0])
        for day_ts, hours in slices:
            rows.append(
                {
                    "Responsavel": author,
                    "Dia": pd.to_datetime(day_ts),
                    "Issue Key": issue_key,
                    "Status": status,
                    "ExecBucket": bucket,
                    "ExecWeight": weight,
                    "HorasUteisSlice": float(hours),
                    "HorasUteisPonderadasSlice": float(hours) * float(weight),
                }
            )
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out["Dia"] = pd.to_datetime(out["Dia"], errors="coerce")
    return out


def normalize_capacity_by_person_day(daily_slices: pd.DataFrame, daily_cap_hours=WORKDAY_DAILY_CAP_HOURS) -> pd.DataFrame:
    """
    Aplica teto por pessoa/dia (ex.: 8h) normalizando proporcionalmente entre eventos concorrentes do mesmo dia.
    """
    if daily_slices is None or daily_slices.empty:
        return pd.DataFrame()
    x = daily_slices.copy()
    if not {"Responsavel", "Dia", "HorasUteisSlice"}.issubset(x.columns):
        return pd.DataFrame()
    x["HorasUteisSlice"] = _safe_num(x["HorasUteisSlice"]).fillna(0)
    if "HorasUteisPonderadasSlice" not in x.columns:
        x["HorasUteisPonderadasSlice"] = x["HorasUteisSlice"]
    x["HorasUteisPonderadasSlice"] = _safe_num(x["HorasUteisPonderadasSlice"]).fillna(0)
    day_totals = (
        x.groupby(["Responsavel", "Dia"], dropna=False)["HorasUteisSlice"]
        .sum()
        .reset_index(name="HorasUteisPessoaDia")
    )
    day_totals["FatorNormalizacao"] = np.where(
        day_totals["HorasUteisPessoaDia"] > float(daily_cap_hours),
        float(daily_cap_hours) / day_totals["HorasUteisPessoaDia"],
        1.0,
    )
    x = x.merge(day_totals, on=["Responsavel", "Dia"], how="left")
    x["FatorNormalizacao"] = _safe_num(x["FatorNormalizacao"]).fillna(1.0)
    x["HorasUteisNormalizadas"] = x["HorasUteisSlice"] * x["FatorNormalizacao"]
    x["HorasUteisPonderadasNormalizadas"] = x["HorasUteisPonderadasSlice"] * x["FatorNormalizacao"]
    return x


def summarize_bottlenecks(event_hours: pd.DataFrame) -> pd.DataFrame:
    """Resumo de gargalo por status usando tempo útil por evento no período filtrado."""
    if event_hours is None or event_hours.empty:
        return pd.DataFrame()
    needed = {"To Status", "Issue Key", "HorasUteisPeriodo"}
    if not needed.issubset(event_hours.columns):
        return pd.DataFrame()
    x = event_hours.copy()
    x["Status"] = x["To Status"].fillna("").astype(str).str.strip()
    x["HorasUteisPeriodo"] = _safe_num(x["HorasUteisPeriodo"]).fillna(0)
    x = x[(x["Status"] != "") & (x["HorasUteisPeriodo"] > 0)].copy()
    if x.empty:
        return pd.DataFrame()
    if "History Created" in x.columns:
        x["History Created"] = pd.to_datetime(x["History Created"], errors="coerce")
    rows = []
    for status, g in x.groupby("Status", dropna=False):
        vals = _safe_num(g["HorasUteisPeriodo"]).fillna(0)
        vals = vals[vals > 0]
        if vals.empty:
            continue
        rows.append(
            {
                "Status": status,
                "Eventos": int(len(g)),
                "CardsUnicos": int(g["Issue Key"].nunique()),
                "HorasUteisTotalPeriodo": float(vals.sum()),
                "HorasUteisMediaEvento": float(vals.mean()),
                "HorasUteisMedianaEvento": float(vals.median()),
                "HorasUteisP85Evento": float(vals.quantile(0.85)),
                "HorasUteisP95Evento": float(vals.quantile(0.95)),
                "PrimeiroEvento": g["History Created"].min() if "History Created" in g.columns else pd.NaT,
                "UltimoEvento": g["History Created"].max() if "History Created" in g.columns else pd.NaT,
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["HorasUteisMedianaEvento", "HorasUteisTotalPeriodo"], ascending=[False, False]).reset_index(drop=True)


def build_dfg_edges_from_events(events_df):
    if events_df is None or events_df.empty:
        return pd.DataFrame()
    needed = {"From Status", "To Status"}
    if not needed.issubset(events_df.columns):
        return pd.DataFrame()
    x = events_df.copy()
    x["From Status"] = x["From Status"].fillna("").astype(str).str.strip()
    x["To Status"] = x["To Status"].fillna("").astype(str).str.strip()
    x = x[(x["From Status"] != "") & (x["To Status"] != "")]
    if x.empty:
        return pd.DataFrame()
    return (
        x.groupby(["From Status", "To Status"], dropna=False)
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
        .reset_index(drop=True)
    )


def build_transition_sankey(events_df, top_edges=40):
    if events_df is None or events_df.empty:
        return go.Figure()
    needed = {"From Status", "To Status"}
    if not needed.issubset(events_df.columns):
        return go.Figure()
    x = events_df.copy()
    x["From Status"] = x["From Status"].fillna("").astype(str).str.strip()
    x["To Status"] = x["To Status"].fillna("").astype(str).str.strip()
    x = x[(x["From Status"] != "") & (x["To Status"] != "")]
    if x.empty:
        return go.Figure()
    edges = (
        x.groupby(["From Status", "To Status"], dropna=False)
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
        .head(top_edges)
    )
    if edges.empty:
        return go.Figure()
    labels = pd.unique(pd.concat([edges["From Status"], edges["To Status"]], ignore_index=True)).tolist()
    idx = {label: i for i, label in enumerate(labels)}
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(label=labels, pad=15, thickness=16),
                link=dict(
                    source=edges["From Status"].map(idx),
                    target=edges["To Status"].map(idx),
                    value=edges["Count"],
                    customdata=edges["Count"],
                    hovertemplate="%{source.label} → %{target.label}<br>Transições: %{value}<extra></extra>",
                ),
            )
        ]
    )
    fig.update_layout(title="Mapa de Transições (Sankey - Top transições)", height=620)
    return fig


def build_variants_pareto(variants_df):
    if variants_df is None or variants_df.empty or "Qtde Casos" not in variants_df.columns:
        return go.Figure()
    x = variants_df.copy()
    x["Qtde Casos"] = _safe_num(x["Qtde Casos"]).fillna(0)
    x = x[x["Qtde Casos"] > 0].copy()
    if x.empty:
        return go.Figure()
    x = x.sort_values("Qtde Casos", ascending=False).head(15).reset_index(drop=True)
    x["Variant Label"] = [f"V{i+1}" for i in range(len(x))]
    x["Cumulativo (%)"] = x["Qtde Casos"].cumsum() / x["Qtde Casos"].sum() * 100
    fig = go.Figure()
    fig.add_bar(x=x["Variant Label"], y=x["Qtde Casos"], name="Casos", marker_color="#2563eb")
    fig.add_trace(
        go.Scatter(
            x=x["Variant Label"],
            y=x["Cumulativo (%)"],
            name="Cumulativo %",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#ef4444", width=2),
        )
    )
    fig.update_layout(
        title="Pareto de Variantes (Top 15)",
        height=480,
        yaxis=dict(title="Casos"),
        yaxis2=dict(title="% Cumulativo", overlaying="y", side="right", range=[0, 105]),
        xaxis=dict(title="Variantes (V1..V15)"),
        legend=dict(orientation="h"),
    )
    return fig


def build_conformance_rework_figs(case_df):
    fig_hist = go.Figure()
    fig_scatter = go.Figure()
    if case_df is None or case_df.empty:
        return fig_hist, fig_scatter

    x = case_df.copy()
    if "Conformance Score" in x.columns:
        x["Conformance Score"] = _safe_num(x["Conformance Score"])
    if "Rework Score" in x.columns:
        x["Rework Score"] = _safe_num(x["Rework Score"]).fillna(0)
    if "Lead Time Fluxo (dias)" in x.columns:
        x["Lead Time Fluxo (dias)"] = _safe_num(x["Lead Time Fluxo (dias)"])

    if "Conformance Score" in x.columns and x["Conformance Score"].notna().any():
        fig_hist = px.histogram(
            x.dropna(subset=["Conformance Score"]),
            x="Conformance Score",
            nbins=20,
            title="Distribuição do Conformance Score",
        )
        fig_hist.update_layout(height=420)

    scatter_cols = {"Lead Time Fluxo (dias)", "Rework Score"}
    if scatter_cols.issubset(x.columns):
        plot_df = x.dropna(subset=["Lead Time Fluxo (dias)"]).copy()
        if not plot_df.empty:
            color_col = "Conformance Score" if "Conformance Score" in plot_df.columns else None
            fig_scatter = px.scatter(
                plot_df,
                x="Lead Time Fluxo (dias)",
                y="Rework Score",
                color=color_col,
                hover_data=[c for c in ["Issue Key", "Tipo de Problema", "Done Final Author"] if c in plot_df.columns],
                title="Lead Time x Retrabalho por Caso",
                color_continuous_scale="Viridis" if color_col else None,
            )
            fig_scatter.update_layout(height=420)
    return fig_hist, fig_scatter


def build_event_volume_fig(events_df):
    fig = go.Figure()
    if events_df is None or events_df.empty:
        return fig
    ts_col = "History Created" if "History Created" in events_df.columns else None
    if not ts_col:
        return fig
    x = events_df.copy()
    x[ts_col] = pd.to_datetime(x[ts_col], errors="coerce")
    x = x.dropna(subset=[ts_col])
    if x.empty:
        return fig
    x["Semana"] = x[ts_col].dt.to_period("W-SUN").dt.start_time
    vol = x.groupby("Semana").size().reset_index(name="Eventos")
    fig = px.bar(vol, x="Semana", y="Eventos", title="Volume de Eventos do Changelog por Semana")
    fig.update_layout(height=360, xaxis_tickangle=-45, margin=dict(b=90))
    return fig


def build_dotted_chart_fig(events_df: pd.DataFrame):
    fig = go.Figure()
    if events_df is None or events_df.empty:
        return fig
    needed = {"History Created", "Issue Key"}
    if not needed.issubset(events_df.columns):
        return fig
    x = events_df.copy()
    x["History Created"] = pd.to_datetime(x["History Created"], errors="coerce")
    x = x.dropna(subset=["History Created"]).copy()
    if x.empty:
        return fig
    x["Issue Key"] = x["Issue Key"].astype(str)
    x["To Status"] = x.get("To Status", "").astype(str) if "To Status" in x.columns else "Status N/A"
    x["Author"] = x.get("Author", "").fillna("").replace("", "Sem Autor").astype(str) if "Author" in x.columns else "Sem Autor"
    # Limitar cardinalidade visual sem perder percepção temporal.
    top_cases = x["Issue Key"].value_counts().head(80).index.tolist()
    x = x[x["Issue Key"].isin(top_cases)].copy()
    if x.empty:
        return fig
    x = x.sort_values("History Created")
    fig = px.scatter(
        x,
        x="History Created",
        y="Issue Key",
        color="To Status" if "To Status" in x.columns else None,
        hover_data=[c for c in ["Author", "From Status", "To Status", "History Id"] if c in x.columns],
        title="Dotted Chart (Eventos do changelog por caso no tempo)",
    )
    fig.update_traces(marker=dict(size=7, opacity=0.75))
    fig.update_layout(height=620, xaxis_title="Data/Hora do evento", yaxis_title="Issue Key (top 80 por volume)")
    return fig


def build_tbr_figs(tbr_cases_df: pd.DataFrame):
    fig_hist = go.Figure()
    fig_dev = go.Figure()
    if tbr_cases_df is None or tbr_cases_df.empty:
        return fig_hist, fig_dev
    x = tbr_cases_df.copy()
    for c in ["TraceFitness", "MissingTokens", "RemainingTokens"]:
        if c in x.columns:
            x[c] = _safe_num(x[c])
    if "TraceFitness" in x.columns and x["TraceFitness"].notna().any():
        fig_hist = px.histogram(x.dropna(subset=["TraceFitness"]), x="TraceFitness", nbins=20, title="TBR - Distribuição de Trace Fitness")
        fig_hist.update_layout(height=380)
    if {"MissingTokens", "RemainingTokens", "Issue Key"}.issubset(x.columns):
        x["DesvioTokens"] = _safe_num(x["MissingTokens"]).fillna(0) + _safe_num(x["RemainingTokens"]).fillna(0)
        plot_df = x.sort_values(["DesvioTokens", "TraceFitness"], ascending=[False, True], na_position="last").head(20).copy()
        if not plot_df.empty:
            fig_dev = px.bar(
                plot_df,
                x="DesvioTokens",
                y="Issue Key",
                orientation="h",
                color="TraceFitness" if "TraceFitness" in plot_df.columns else None,
                color_continuous_scale="OrRd_r",
                hover_data=[c for c in ["MissingTokens", "RemainingTokens", "ConsumedTokens", "ProducedTokens"] if c in plot_df.columns],
                title="TBR - Casos com maior desvio de tokens",
            )
            fig_dev.update_layout(height=460, yaxis={"categoryorder": "total ascending"})
    return fig_hist, fig_dev


def build_align_figs(align_cases_df: pd.DataFrame, align_moves_df: pd.DataFrame):
    fig_hist = go.Figure()
    fig_moves = go.Figure()
    if align_cases_df is not None and not align_cases_df.empty:
        x = align_cases_df.copy()
        for c in ["AlignmentFitness", "AlignmentCost", "DesviosTotal"]:
            if c in x.columns:
                x[c] = _safe_num(x[c])
        if "AlignmentFitness" in x.columns and x["AlignmentFitness"].notna().any():
            fig_hist = px.histogram(x.dropna(subset=["AlignmentFitness"]), x="AlignmentFitness", nbins=20, title="Alignments - Distribuição de Fitness")
            fig_hist.update_layout(height=380)
    if align_moves_df is not None and not align_moves_df.empty and {"MoveType", "Activity", "Count"}.issubset(align_moves_df.columns):
        m = align_moves_df.copy()
        m["Count"] = _safe_num(m["Count"]).fillna(0)
        m["MoveType"] = m["MoveType"].astype(str)
        m["Label"] = m["MoveType"].astype(str) + " | " + m["Activity"].astype(str)
        m = m.sort_values("Count", ascending=False).head(20)
        fig_moves = px.bar(
            m,
            x="Count",
            y="Label",
            orientation="h",
            color="MoveType",
            title="Alignments - Top movimentos de desvio",
            hover_data=[c for c in ["CasesAffected"] if c in m.columns],
            color_discrete_map={"log_move": "#ef4444", "model_move": "#2563eb"},
        )
        fig_moves.update_layout(height=460, yaxis={"categoryorder": "total ascending"})
    return fig_hist, fig_moves


def _empty_pm_figure(title, message):
    fig = go.Figure()
    fig.update_layout(title=title, height=420)
    fig.add_annotation(text=message, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    return fig


def build_petri_bottleneck_metrics(events_df: pd.DataFrame) -> pd.DataFrame:
    if events_df is None or events_df.empty:
        return pd.DataFrame()
    needed = {"From Status", "To Status"}
    if not needed.issubset(events_df.columns):
        return pd.DataFrame()

    x = events_df.copy()
    x["From Status"] = x["From Status"].fillna("").astype(str).str.strip()
    x["To Status"] = x["To Status"].fillna("").astype(str).str.strip()
    x = x[(x["From Status"] != "") & (x["To Status"] != "")]
    if x.empty:
        return pd.DataFrame()

    if "HorasUteisPeriodo" not in x.columns:
        x["HorasUteisPeriodo"] = _safe_num(x.get("HorasNoPeriodo", 0)).fillna(0)
    else:
        x["HorasUteisPeriodo"] = _safe_num(x["HorasUteisPeriodo"]).fillna(0)
    x["HorasNoPeriodo"] = _safe_num(x.get("HorasNoPeriodo", 0)).fillna(0)
    if "ExecBucket" not in x.columns:
        x["ExecBucket"] = "SemBucket"
    x["ExecBucket"] = x["ExecBucket"].fillna("SemBucket").astype(str)

    grouped = (
        x.groupby(["From Status", "To Status", "ExecBucket"], dropna=False)
        .agg(
            HorasUteisPeriodo=("HorasUteisPeriodo", "sum"),
            HorasNoPeriodo=("HorasNoPeriodo", "sum"),
            Eventos=("Issue Key", "count") if "Issue Key" in x.columns else ("To Status", "count"),
            CardsUnicos=("Issue Key", "nunique") if "Issue Key" in x.columns else ("To Status", "count"),
        )
        .reset_index()
    )
    if grouped.empty:
        return pd.DataFrame()

    pivot_hours = (
        grouped.pivot_table(
            index=["From Status", "To Status"],
            columns="ExecBucket",
            values="HorasUteisPeriodo",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    totals = (
        grouped.groupby(["From Status", "To Status"], dropna=False)
        .agg(
            HorasUteisTotal=("HorasUteisPeriodo", "sum"),
            HorasTotal=("HorasNoPeriodo", "sum"),
            Eventos=("Eventos", "sum"),
            CardsUnicos=("CardsUnicos", "max"),
        )
        .reset_index()
    )
    out = totals.merge(pivot_hours, on=["From Status", "To Status"], how="left")
    for c in ["Execucao Ativa", "Validacao/QA", "Espera"]:
        if c not in out.columns:
            out[c] = 0.0
    out["PctEspera"] = np.where(
        out["HorasUteisTotal"] > 0,
        (out["Espera"] / out["HorasUteisTotal"]) * 100.0,
        0.0,
    )
    out["Aresta"] = out["From Status"].astype(str) + " → " + out["To Status"].astype(str)
    return out.sort_values(["Espera", "HorasUteisTotal", "Eventos"], ascending=False).reset_index(drop=True)


def build_petri_bottleneck_network_fig(events_df: pd.DataFrame, top_edges: int = 16):
    metrics = build_petri_bottleneck_metrics(events_df)
    if metrics.empty:
        return _empty_pm_figure(
            "Rede de Petri (aproximação) - Gargalos",
            "Sem transições suficientes para montar a rede de Petri analítica.",
        )

    m = metrics.head(top_edges).copy()
    if m.empty:
        return _empty_pm_figure(
            "Rede de Petri (aproximação) - Gargalos",
            "Sem transições no recorte selecionado.",
        )

    statuses = pd.unique(pd.concat([m["From Status"], m["To Status"]], ignore_index=True)).tolist()
    n = max(len(statuses), 1)
    radius = 1.0
    place_pos = {}
    for i, status in enumerate(statuses):
        ang = (2 * np.pi * i / n) - (np.pi / 2)
        place_pos[status] = (radius * np.cos(ang), radius * np.sin(ang))

    max_wait = float(m["Espera"].max()) if "Espera" in m.columns and not m["Espera"].empty else 0.0
    max_events = max(float(m["Eventos"].max()), 1.0)

    line_x = []
    line_y = []
    trans_x = []
    trans_y = []
    trans_size = []
    trans_color = []
    trans_text = []
    trans_label = []

    for i, row in m.reset_index(drop=True).iterrows():
        fx, fy = place_pos.get(row["From Status"], (0.0, 0.0))
        tx, ty = place_pos.get(row["To Status"], (0.0, 0.0))
        mx = (fx + tx) / 2.0
        my = (fy + ty) / 2.0
        dx = tx - fx
        dy = ty - fy
        norm = float((dx**2 + dy**2) ** 0.5) or 1.0
        bend = 0.10 + (0.03 * (i % 3))
        px_off = -dy / norm * bend
        py_off = dx / norm * bend
        if i % 2:
            px_off *= -1
            py_off *= -1
        cx = mx + px_off
        cy = my + py_off

        line_x.extend([fx, cx, None, cx, tx, None])
        line_y.extend([fy, cy, None, cy, ty, None])

        trans_x.append(cx)
        trans_y.append(cy)
        trans_size.append(12 + 22 * (float(row.get("Eventos", 0)) / max_events))
        wait_val = float(row.get("Espera", 0.0))
        trans_color.append(wait_val)
        trans_label.append(f"T{i+1}")
        trans_text.append(
            "<br>".join(
                [
                    f"<b>{row['From Status']} → {row['To Status']}</b>",
                    f"Eventos: {int(row.get('Eventos', 0) or 0)}",
                    f"Horas úteis (total): {float(row.get('HorasUteisTotal', 0)):.1f}",
                    f"Horas úteis em espera: {wait_val:.1f}",
                    f"% espera: {float(row.get('PctEspera', 0)):.1f}%",
                ]
            )
        )

    place_x = [place_pos[s][0] for s in statuses]
    place_y = [place_pos[s][1] for s in statuses]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            line=dict(color="rgba(107,114,128,0.45)", width=1.5),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=place_x,
            y=place_y,
            mode="markers+text",
            text=statuses,
            textposition="top center",
            marker=dict(size=26, color="#ffffff", line=dict(color="#111827", width=2)),
            name="Lugares (status)",
            hovertemplate="Status: %{text}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trans_x,
            y=trans_y,
            mode="markers+text",
            text=trans_label,
            textposition="middle center",
            marker=dict(
                symbol="square",
                size=trans_size,
                color=trans_color,
                colorscale="YlOrRd",
                cmin=0,
                cmax=max(max_wait, 1.0),
                colorbar=dict(title="h úteis em espera"),
                line=dict(color="#7c2d12", width=1),
            ),
            customdata=trans_text,
            name="Transições",
            hovertemplate="%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Rede de Petri (aproximação a partir do changelog) - transições com gargalo por espera",
        height=700,
        showlegend=True,
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        plot_bgcolor="white",
    )
    return fig


def build_petri_bottleneck_transition_fig(events_df: pd.DataFrame):
    metrics = build_petri_bottleneck_metrics(events_df)
    if metrics.empty:
        return _empty_pm_figure(
            "Gargalos por Transição (Rede de Petri)",
            "Sem dados de transição para calcular gargalos.",
        )
    x = metrics.head(15).copy()
    fig = go.Figure()
    for col, name, color in [
        ("Execucao Ativa", "Execução Ativa", "#0f766e"),
        ("Validacao/QA", "Validação/QA", "#2563eb"),
        ("Espera", "Espera", "#f59e0b"),
    ]:
        if col in x.columns:
            fig.add_bar(
                x=x[col],
                y=x["Aresta"],
                orientation="h",
                name=name,
                marker_color=color,
                customdata=np.stack([x["Eventos"], x["PctEspera"]], axis=1),
                hovertemplate="%{y}<br>Horas úteis: %{x:.1f}<br>Eventos: %{customdata[0]}<br>% espera total da aresta: %{customdata[1]:.1f}%<extra></extra>",
            )
    fig.update_layout(
        title="Gargalos por Transição (horas úteis por bucket)",
        barmode="stack",
        height=560,
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="Horas úteis no período",
        legend=dict(orientation="h"),
    )
    return fig


def build_petri_bottleneck_status_fig(events_df: pd.DataFrame):
    if events_df is None or events_df.empty or "To Status" not in events_df.columns:
        return _empty_pm_figure(
            "Gargalos por Etapa (lugares da rede)",
            "Sem dados de eventos para calcular gargalos por etapa.",
        )
    x = events_df.copy()
    x["To Status"] = x["To Status"].fillna("").astype(str).str.strip()
    x = x[x["To Status"] != ""]
    if x.empty:
        return _empty_pm_figure(
            "Gargalos por Etapa (lugares da rede)",
            "Sem status de destino válidos no recorte selecionado.",
        )
    x["HorasUteisPeriodo"] = _safe_num(x.get("HorasUteisPeriodo", x.get("HorasNoPeriodo", 0))).fillna(0)
    if "ExecBucket" not in x.columns:
        x["ExecBucket"] = "SemBucket"
    agg = (
        x.groupby(["To Status", "ExecBucket"], dropna=False)["HorasUteisPeriodo"]
        .sum()
        .reset_index()
        .rename(columns={"To Status": "Status"})
    )
    totals = agg.groupby("Status")["HorasUteisPeriodo"].sum().sort_values(ascending=False)
    top_status = totals.head(15).index.tolist()
    agg = agg[agg["Status"].isin(top_status)].copy()
    if agg.empty:
        return _empty_pm_figure(
            "Gargalos por Etapa (lugares da rede)",
            "Sem dados suficientes para ranking por etapa.",
        )
    fig = px.bar(
        agg,
        x="HorasUteisPeriodo",
        y="Status",
        color="ExecBucket",
        orientation="h",
        barmode="stack",
        title="Gargalos por Etapa (lugares da rede de Petri)",
        color_discrete_map={"Execucao Ativa": "#0f766e", "Validacao/QA": "#2563eb", "Espera": "#f59e0b", "SemBucket": "#9ca3af"},
    )
    fig.update_layout(height=560, yaxis={"categoryorder": "total ascending"}, xaxis_title="Horas úteis no período")
    return fig


app = dash.Dash(__name__)
app.title = "Process Mining Jira - W1NNER"

app.layout = html.Div(
    [
        html.H2("Process Mining Jira - W1NNER (Sandbox)", style={"textAlign": "center"}),
        html.P(
            "Página local separada do dashboard de produção. Consome o último arquivo w1nner-process-mining-*.xlsx.",
            style={"textAlign": "center", "color": "#555"},
        ),
        html.Div(
            [
                html.Button("Recarregar Relatório", id="btn-reload", n_clicks=0),
                dcc.DatePickerRange(id="pm-date-range"),
                dcc.Dropdown(id="pm-person-filter", multi=False, placeholder="Filtrar por pessoa"),
                dcc.Dropdown(
                    id="pm-cross-topn",
                    options=[{"label": str(v), "value": v} for v in [3, 5, 8, 10, 15, 20]],
                    value=5,
                    clearable=False,
                    placeholder="Top N",
                ),
                dcc.Dropdown(
                    id="pm-cross-weekly-metric",
                    options=[
                        {"label": "Score Integrado", "value": "score"},
                        {"label": "Itens Concluídos", "value": "itens_concluidos"},
                        {"label": "Commits", "value": "commits"},
                        {"label": "PRs Merged", "value": "prs_merged"},
                        {"label": "PRs Abertos", "value": "prs_abertos"},
                    ],
                    value="score",
                    clearable=False,
                    placeholder="Métrica semanal",
                ),
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "220px 1fr 1fr 140px 260px",
                "gap": "10px",
                "alignItems": "center",
                "marginBottom": "16px",
            },
        ),
        dcc.Store(id="pm-report-store"),
        html.Div(id="pm-header"),
        html.Div(id="pm-body"),
    ],
    style={"maxWidth": "1400px", "margin": "0 auto", "padding": "16px", "background": "#f7f8fa"},
)


@app.callback(
    Output("pm-report-store", "data"),
    Output("pm-header", "children"),
    Output("pm-date-range", "start_date"),
    Output("pm-date-range", "end_date"),
    Output("pm-person-filter", "options"),
    Input("btn-reload", "n_clicks"),
)
def reload_report(_):
    path = find_latest_process_mining_report()
    if not path:
        return None, html.Div("Nenhum arquivo w1nner-process-mining-*.xlsx encontrado."), None, None, []

    report = load_report(path)
    for key in ["ConformidadeCasos", "RetrabalhoItens"]:
        if "Done Final Date" in report.get(key, pd.DataFrame()).columns:
            report[key]["Done Final Date"] = pd.to_datetime(report[key]["Done Final Date"], errors="coerce")
    if "Semana" in report.get("VazaoPessoaSemanal", pd.DataFrame()).columns:
        report["VazaoPessoaSemanal"]["Semana"] = pd.to_datetime(report["VazaoPessoaSemanal"]["Semana"], errors="coerce")

    start_date = None
    end_date = None
    weekly = report.get("VazaoPessoaSemanal", pd.DataFrame())
    if not weekly.empty and "Semana" in weekly.columns:
        s = pd.to_datetime(weekly["Semana"], errors="coerce").dropna()
        if not s.empty:
            start_date = s.min().date().isoformat()
            end_date = s.max().date().isoformat()

    people = report.get("VazaoPessoaResumo", pd.DataFrame())
    options = []
    if not people.empty and "Responsavel" in people.columns:
        vals = sorted([str(v) for v in people["Responsavel"].dropna().astype(str).unique()])
        options = [{"label": v, "value": v} for v in vals]

    header = html.Div(
        [
            html.Div(f"Arquivo: {os.path.basename(path)}"),
            html.Div(f"Atualizado em: {datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')}"),
        ],
        style={"marginBottom": "12px", "color": "#444"},
    )

    serializable = {}
    for k, df in report.items():
        tmp = df.copy()
        for c in tmp.columns:
            if pd.api.types.is_datetime64_any_dtype(tmp[c]):
                tmp[c] = tmp[c].dt.strftime("%Y-%m-%d %H:%M:%S")
        serializable[k] = tmp.to_dict("records")
    serializable["_artifact_images"] = _load_artifact_images_from_base(os.path.splitext(path)[0])
    serializable["_report_file"] = path
    return serializable, header, start_date, end_date, options


@app.callback(
    Output("pm-body", "children"),
    Input("pm-report-store", "data"),
    Input("pm-date-range", "start_date"),
    Input("pm-date-range", "end_date"),
    Input("pm-person-filter", "value"),
    Input("pm-cross-topn", "value"),
    Input("pm-cross-weekly-metric", "value"),
)
def render_pm(data, start_date, end_date, person, cross_topn, cross_weekly_metric):
    if not data:
        return html.Div("Sem dados carregados.")

    pm_summary = pd.DataFrame(data.get("ResumoConformidade", []))
    pm_cases = pd.DataFrame(data.get("ConformidadeCasos", []))
    pm_rework = pd.DataFrame(data.get("RetrabalhoItens", []))
    pm_status = pd.DataFrame(data.get("TemposPorStatus", []))
    pm_weekly = pd.DataFrame(data.get("VazaoPessoaSemanal", []))
    pm_people = pd.DataFrame(data.get("VazaoPessoaResumo", []))
    pm_hours_people = pd.DataFrame(data.get("HorasPessoaResumo", []))
    pm_hours_status = pd.DataFrame(data.get("HorasPessoaStatus", []))
    pm_variants = pd.DataFrame(data.get("VariantesTop", []))
    pm_events = pd.DataFrame(data.get("EventosFiltrados", []))
    pm_dfg_edges = pd.DataFrame(data.get("PM4PyDFGEdges", []))
    pm_dfg_perf_edges = pd.DataFrame(data.get("PM4PyDFGPerfEdges", []))
    pm_tbr_summary = pd.DataFrame(data.get("PM4PyTBRResumo", []))
    pm_tbr_cases = pd.DataFrame(data.get("PM4PyTBRCasos", []))
    pm_align_summary = pd.DataFrame(data.get("PM4PyAlignResumo", []))
    pm_align_cases = pd.DataFrame(data.get("PM4PyAlignCasos", []))
    pm_align_moves = pd.DataFrame(data.get("PM4PyAlignTopMoves", []))
    pm_meta = pd.DataFrame(data.get("Metadados", []))
    artifact_images = data.get("_artifact_images", {}) or {}

    if "Done Final Date" in pm_cases.columns:
        pm_cases["Done Final Date"] = pd.to_datetime(pm_cases["Done Final Date"], errors="coerce")
    if "Done Final Date" in pm_rework.columns:
        pm_rework["Done Final Date"] = pd.to_datetime(pm_rework["Done Final Date"], errors="coerce")
    if "Semana" in pm_weekly.columns:
        pm_weekly["Semana"] = pd.to_datetime(pm_weekly["Semana"], errors="coerce")
    if "History Created" in pm_events.columns:
        pm_events["History Created"] = pd.to_datetime(pm_events["History Created"], errors="coerce")
    if "Next Timestamp" in pm_events.columns:
        pm_events["Next Timestamp"] = pd.to_datetime(pm_events["Next Timestamp"], errors="coerce")
    for _df in [pm_tbr_cases, pm_align_cases]:
        if "Done Final Date" in _df.columns:
            _df["Done Final Date"] = pd.to_datetime(_df["Done Final Date"], errors="coerce")

    start_ts = pd.to_datetime(start_date) if start_date else None
    end_ts = pd.to_datetime(end_date) if end_date else None
    if start_date and end_date:
        if "Semana" in pm_weekly.columns:
            pm_weekly = pm_weekly[(pm_weekly["Semana"] >= start_ts) & (pm_weekly["Semana"] <= end_ts + pd.Timedelta(days=7))]
        if "Done Final Date" in pm_cases.columns:
            pm_cases = pm_cases[pm_cases["Done Final Date"].isna() | ((pm_cases["Done Final Date"] >= start_ts) & (pm_cases["Done Final Date"] <= end_ts))]
        if "Done Final Date" in pm_rework.columns:
            pm_rework = pm_rework[pm_rework["Done Final Date"].isna() | ((pm_rework["Done Final Date"] >= start_ts) & (pm_rework["Done Final Date"] <= end_ts))]
        if "History Created" in pm_events.columns:
            pm_events = pm_events[(pm_events["History Created"] >= start_ts) & (pm_events["History Created"] <= end_ts + pd.Timedelta(days=1))]
        if "Done Final Date" in pm_tbr_cases.columns:
            pm_tbr_cases = pm_tbr_cases[pm_tbr_cases["Done Final Date"].isna() | ((pm_tbr_cases["Done Final Date"] >= start_ts) & (pm_tbr_cases["Done Final Date"] <= end_ts))]
        if "Done Final Date" in pm_align_cases.columns:
            pm_align_cases = pm_align_cases[pm_align_cases["Done Final Date"].isna() | ((pm_align_cases["Done Final Date"] >= start_ts) & (pm_align_cases["Done Final Date"] <= end_ts))]

    if person:
        if "Responsavel" in pm_people.columns:
            pm_people = pm_people[pm_people["Responsavel"] == person]
        if "Responsavel" in pm_weekly.columns:
            pm_weekly = pm_weekly[pm_weekly["Responsavel"] == person]
        if "Done Final Author" in pm_rework.columns:
            pm_rework = pm_rework[pm_rework["Done Final Author"] == person]
        if "Done Final Author" in pm_cases.columns:
            pm_cases = pm_cases[pm_cases["Done Final Author"] == person]
        if "Author" in pm_events.columns:
            pm_events = pm_events[pm_events["Author"] == person]
        if "Done Final Author" in pm_tbr_cases.columns:
            pm_tbr_cases = pm_tbr_cases[pm_tbr_cases["Done Final Author"] == person]
        if "Done Final Author" in pm_align_cases.columns:
            pm_align_cases = pm_align_cases[pm_align_cases["Done Final Author"] == person]
        if "Responsavel" in pm_hours_people.columns:
            pm_hours_people = pm_hours_people[pm_hours_people["Responsavel"] == person]
        if "Responsavel" in pm_hours_status.columns:
            pm_hours_status = pm_hours_status[pm_hours_status["Responsavel"] == person]

    event_hours = add_business_hours_overlap(pm_events, start_ts=start_ts, end_ts=end_ts)
    exec_event_hours = pd.DataFrame()
    exec_by_person = pd.DataFrame()
    exec_by_status = pd.DataFrame()
    exec_daily_slices = pd.DataFrame()
    exec_daily_norm = pd.DataFrame()
    exec_norm_by_person = pd.DataFrame()
    exec_norm_by_status = pd.DataFrame()
    exec_norm_by_bucket = pd.DataFrame()
    bottlenecks = pd.DataFrame()
    if not event_hours.empty and "To Status" in event_hours.columns:
        bottlenecks = summarize_bottlenecks(event_hours)
        exec_event_hours = event_hours[event_hours["To Status"].map(is_execution_status)].copy()
        exec_event_hours["ExecBucket"] = exec_event_hours["To Status"].map(execution_status_bucket)
        exec_event_hours["ExecWeight"] = exec_event_hours["To Status"].map(execution_status_weight)
        exec_event_hours["HorasExecucaoPonderadasPeriodo"] = _safe_num(exec_event_hours.get("HorasNoPeriodo", 0)).fillna(0) * _safe_num(exec_event_hours.get("ExecWeight", 0)).fillna(0)
        exec_event_hours["HorasExecucaoUteisPonderadasPeriodo"] = _safe_num(exec_event_hours.get("HorasUteisPeriodo", 0)).fillna(0) * _safe_num(exec_event_hours.get("ExecWeight", 0)).fillna(0)
        exec_daily_slices = explode_event_business_daily_slices(exec_event_hours)
        exec_daily_norm = normalize_capacity_by_person_day(exec_daily_slices)
        if not exec_daily_norm.empty:
            exec_norm_by_person = (
                exec_daily_norm.groupby("Responsavel", dropna=False)
                .agg(
                    HorasUteisCargaFluxo=("HorasUteisSlice", "sum"),
                    HorasEstimadasTrabalho=("HorasUteisNormalizadas", "sum"),
                    HorasEstimadasTrabalhoPonderadas=("HorasUteisPonderadasNormalizadas", "sum"),
                    HorasUteisPonderadasCarga=("HorasUteisPonderadasSlice", "sum"),
                    DiasAtivos=("Dia", "nunique"),
                    CardsUnicos=("Issue Key", "nunique"),
                    Slices=("Issue Key", "count"),
                )
                .reset_index()
                .sort_values("HorasEstimadasTrabalho", ascending=False)
            )
            exec_norm_by_person["MediaHrsEstimadasPorDiaAtivo"] = np.where(
                _safe_num(exec_norm_by_person["DiasAtivos"]).fillna(0) > 0,
                _safe_num(exec_norm_by_person["HorasEstimadasTrabalho"]).fillna(0) / _safe_num(exec_norm_by_person["DiasAtivos"]).fillna(1),
                0.0,
            )
            exec_norm_by_status = (
                exec_daily_norm.groupby(["Responsavel", "Status", "ExecBucket"], dropna=False)
                .agg(
                    HorasUteisCargaFluxo=("HorasUteisSlice", "sum"),
                    HorasEstimadasTrabalho=("HorasUteisNormalizadas", "sum"),
                    HorasEstimadasTrabalhoPonderadas=("HorasUteisPonderadasNormalizadas", "sum"),
                    DiasComAtividade=("Dia", "nunique"),
                    CardsUnicos=("Issue Key", "nunique"),
                    Slices=("Issue Key", "count"),
                )
                .reset_index()
                .sort_values("HorasEstimadasTrabalho", ascending=False)
            )
            exec_norm_by_bucket = (
                exec_daily_norm.groupby(["Responsavel", "ExecBucket"], dropna=False)
                .agg(
                    HorasUteisCargaFluxo=("HorasUteisSlice", "sum"),
                    HorasEstimadasTrabalho=("HorasUteisNormalizadas", "sum"),
                    HorasEstimadasTrabalhoPonderadas=("HorasUteisPonderadasNormalizadas", "sum"),
                )
                .reset_index()
            )
    if not exec_event_hours.empty and "Author" in exec_event_hours.columns:
        exec_by_person = (
            exec_event_hours.assign(Responsavel=exec_event_hours["Author"].fillna("").replace("", "Sem Autor"))
            .groupby("Responsavel", dropna=False)
            .agg(
                HorasExecucaoPeriodo=("HorasNoPeriodo", "sum"),
                HorasExecucaoUteisPeriodo=("HorasUteisPeriodo", "sum"),
                HorasExecucaoPonderadasPeriodo=("HorasExecucaoPonderadasPeriodo", "sum"),
                HorasExecucaoUteisPonderadasPeriodo=("HorasExecucaoUteisPonderadasPeriodo", "sum"),
                MediaHorasPorEvento=("HorasNoPeriodo", "mean"),
                MediaHorasUteisPorEvento=("HorasUteisPeriodo", "mean"),
                Eventos=("Issue Key", "count"),
                CardsUnicos=("Issue Key", "nunique"),
            )
            .reset_index()
            .sort_values("HorasExecucaoPeriodo", ascending=False)
        )
        exec_by_person["HorasExecucaoPeriodo"] = _safe_num(exec_by_person["HorasExecucaoPeriodo"]).fillna(0).round(2)
        exec_by_person["HorasExecucaoUteisPeriodo"] = _safe_num(exec_by_person["HorasExecucaoUteisPeriodo"]).fillna(0).round(2)
        exec_by_person["HorasExecucaoPonderadasPeriodo"] = _safe_num(exec_by_person["HorasExecucaoPonderadasPeriodo"]).fillna(0).round(2)
        exec_by_person["HorasExecucaoUteisPonderadasPeriodo"] = _safe_num(exec_by_person["HorasExecucaoUteisPonderadasPeriodo"]).fillna(0).round(2)
        exec_by_person["MediaHorasPorEvento"] = _safe_num(exec_by_person["MediaHorasPorEvento"]).fillna(0).round(2)
        exec_by_person["MediaHorasUteisPorEvento"] = _safe_num(exec_by_person["MediaHorasUteisPorEvento"]).fillna(0).round(2)
        exec_by_status = (
            exec_event_hours.assign(Responsavel=exec_event_hours["Author"].fillna("").replace("", "Sem Autor"))
            .groupby(["Responsavel", "To Status", "ExecBucket"], dropna=False)
            .agg(
                HorasExecucaoPeriodo=("HorasNoPeriodo", "sum"),
                HorasExecucaoUteisPeriodo=("HorasUteisPeriodo", "sum"),
                HorasExecucaoPonderadasPeriodo=("HorasExecucaoPonderadasPeriodo", "sum"),
                HorasExecucaoUteisPonderadasPeriodo=("HorasExecucaoUteisPonderadasPeriodo", "sum"),
                Eventos=("Issue Key", "count"),
                CardsUnicos=("Issue Key", "nunique"),
            )
            .reset_index()
            .rename(columns={"To Status": "Status"})
            .sort_values("HorasExecucaoPeriodo", ascending=False)
        )
        exec_by_status["HorasExecucaoPeriodo"] = _safe_num(exec_by_status["HorasExecucaoPeriodo"]).fillna(0).round(2)
        exec_by_status["HorasExecucaoUteisPeriodo"] = _safe_num(exec_by_status["HorasExecucaoUteisPeriodo"]).fillna(0).round(2)
        exec_by_status["HorasExecucaoPonderadasPeriodo"] = _safe_num(exec_by_status["HorasExecucaoPonderadasPeriodo"]).fillna(0).round(2)
        exec_by_status["HorasExecucaoUteisPonderadasPeriodo"] = _safe_num(exec_by_status["HorasExecucaoUteisPonderadasPeriodo"]).fillna(0).round(2)
    exec_total_h = float(_safe_num(exec_event_hours.get("HorasNoPeriodo", pd.Series(dtype=float))).fillna(0).sum()) if not exec_event_hours.empty else 0.0
    exec_mean_h_event = float(_safe_num(exec_event_hours.get("HorasNoPeriodo", pd.Series(dtype=float))).replace(0, np.nan).dropna().mean()) if not exec_event_hours.empty else float("nan")
    exec_useful_total_h = float(_safe_num(exec_event_hours.get("HorasUteisPeriodo", pd.Series(dtype=float))).fillna(0).sum()) if not exec_event_hours.empty else 0.0
    exec_useful_mean_h_event = float(_safe_num(exec_event_hours.get("HorasUteisPeriodo", pd.Series(dtype=float))).replace(0, np.nan).dropna().mean()) if not exec_event_hours.empty else float("nan")
    exec_useful_weighted_total_h = float(_safe_num(exec_event_hours.get("HorasExecucaoUteisPonderadasPeriodo", pd.Series(dtype=float))).fillna(0).sum()) if not exec_event_hours.empty else 0.0
    exec_norm_total_h = float(_safe_num(exec_daily_norm.get("HorasUteisNormalizadas", pd.Series(dtype=float))).fillna(0).sum()) if not exec_daily_norm.empty else 0.0
    exec_norm_weighted_total_h = float(_safe_num(exec_daily_norm.get("HorasUteisPonderadasNormalizadas", pd.Series(dtype=float))).fillna(0).sum()) if not exec_daily_norm.empty else 0.0
    exec_norm_person_days = int(pd.DataFrame(exec_daily_norm)[["Responsavel", "Dia"]].drop_duplicates().shape[0]) if (not exec_daily_norm.empty and {"Responsavel","Dia"}.issubset(exec_daily_norm.columns)) else 0
    exec_norm_mean_person_day = (exec_norm_total_h / exec_norm_person_days) if exec_norm_person_days > 0 else float("nan")
    if not exec_event_hours.empty and "ExecBucket" in exec_event_hours.columns:
        _bucket_sum = exec_event_hours.groupby("ExecBucket")["HorasUteisPeriodo"].sum()
        exec_active_useful_h = float(_bucket_sum.get("Execucao Ativa", 0.0))
        exec_validation_useful_h = float(_bucket_sum.get("Validacao/QA", 0.0))
        exec_wait_useful_h = float(_bucket_sum.get("Espera", 0.0))
    else:
        exec_active_useful_h = 0.0
        exec_validation_useful_h = 0.0
        exec_wait_useful_h = 0.0
    if not exec_daily_norm.empty and "ExecBucket" in exec_daily_norm.columns:
        _bucket_norm_sum = exec_daily_norm.groupby("ExecBucket")["HorasUteisNormalizadas"].sum()
        exec_active_norm_h = float(_bucket_norm_sum.get("Execucao Ativa", 0.0))
        exec_validation_norm_h = float(_bucket_norm_sum.get("Validacao/QA", 0.0))
        exec_wait_norm_h = float(_bucket_norm_sum.get("Espera", 0.0))
    else:
        exec_active_norm_h = 0.0
        exec_validation_norm_h = 0.0
        exec_wait_norm_h = 0.0

    total_concluidos = int(pd.to_numeric(pm_people.get("Itens Concluidos", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not pm_people.empty else int(pm_cases["Issue Key"].nunique()) if "Issue Key" in pm_cases.columns else 0
    itens_retrabalho = int(pd.to_numeric(pm_people.get("Itens Com Retrabalho", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not pm_people.empty else int((pd.to_numeric(pm_cases.get("Rework Score", pd.Series(dtype=float)), errors="coerce").fillna(0) > 0).sum())
    taxa_retrabalho = (itens_retrabalho / total_concluidos * 100.0) if total_concluidos > 0 else 0.0
    conf_media = pd.to_numeric(pm_cases.get("Conformance Score", pd.Series(dtype=float)), errors="coerce").dropna()
    conf_media_val = float(conf_media.mean()) if not conf_media.empty else np.nan
    bitbucket_logs = load_project_bitbucket_logs("W1NNER")
    cross_people, cross_totals, bb_totals = compute_pm_bitbucket_cross_metrics(
        pm_people, pm_cases, bitbucket_logs, start_ts, end_ts
    )
    if person and not cross_people.empty and "Pessoa" in cross_people.columns:
        cross_people = cross_people[cross_people["Pessoa"] == person].copy()
    if not cross_people.empty:
        bb_totals = {
            "Commits": int(_safe_num(cross_people.get("Commits", pd.Series(dtype=float))).fillna(0).sum()),
            "PRs Abertos": int(_safe_num(cross_people.get("PRs Abertos", pd.Series(dtype=float))).fillna(0).sum()),
            "PRs Merged": int(_safe_num(cross_people.get("PRs Merged", pd.Series(dtype=float))).fillna(0).sum()),
            "PRs Declinados": int(_safe_num(cross_people.get("PRs Declinados", pd.Series(dtype=float))).fillna(0).sum()),
            "Aprovacoes": int(_safe_num(cross_people.get("Aprovacoes", pd.Series(dtype=float))).fillna(0).sum()),
            "Reprovacoes": int(_safe_num(cross_people.get("Reprovacoes", pd.Series(dtype=float))).fillna(0).sum()),
        }
        cross_totals = {
            "Itens Concluidos": int(_safe_num(cross_people.get("Itens Concluidos", pd.Series(dtype=float))).fillna(0).sum()),
            "Itens c/ Evidencia Tecnica": int(_safe_num(cross_people.get("Itens c/ Evidencia Tecnica", pd.Series(dtype=float))).fillna(0).sum()),
            "Cobertura Tecnica (%)": float(
                _safe_num(cross_people.get("Itens c/ Evidencia Tecnica", pd.Series(dtype=float))).fillna(0).sum()
                / max(_safe_num(cross_people.get("Itens Concluidos", pd.Series(dtype=float))).fillna(0).sum(), 1)
                * 100.0
            ),
            "Commits": bb_totals["Commits"],
            "PRs Merged": bb_totals["PRs Merged"],
            "Aprovacoes": bb_totals["Aprovacoes"],
            "Reprovacoes": bb_totals["Reprovacoes"],
        }

    kpi_grid = html.Div(
        [
            create_kpi_card("Itens Concluídos", total_concluidos),
            create_kpi_card("Itens com Retrabalho", itens_retrabalho),
            create_kpi_card("Taxa de Retrabalho", f"{taxa_retrabalho:.1f}%"),
            create_kpi_card("Conformidade Média", f"{conf_media_val:.2f}" if pd.notna(conf_media_val) else "—"),
            create_kpi_card("Horas Execução (período)", f"{exec_total_h:,.1f}"),
            create_kpi_card("Média h/Evento Exec", f"{exec_mean_h_event:.1f}" if pd.notna(exec_mean_h_event) else "—"),
            create_kpi_card("Horas Úteis Exec (período)", f"{exec_useful_total_h:,.1f}"),
            create_kpi_card("Média h úteis/Evento", f"{exec_useful_mean_h_event:.1f}" if pd.notna(exec_useful_mean_h_event) else "—"),
            create_kpi_card("Horas Úteis Exec Ativa", f"{exec_active_useful_h:,.1f}"),
            create_kpi_card("Horas Úteis Validação/QA", f"{exec_validation_useful_h:,.1f}"),
            create_kpi_card("Horas Úteis Exec Espera", f"{exec_wait_useful_h:,.1f}"),
            create_kpi_card("Horas Úteis Exec Ponderadas", f"{exec_useful_weighted_total_h:,.1f}"),
            create_kpi_card("Horas Est. Trabalho (normalizadas)", f"{exec_norm_total_h:,.1f}"),
            create_kpi_card("Horas Est. Trab. Ponderadas", f"{exec_norm_weighted_total_h:,.1f}"),
            create_kpi_card("Média h est./pessoa-dia", f"{exec_norm_mean_person_day:.1f}" if pd.notna(exec_norm_mean_person_day) else "—"),
            create_kpi_card("Horas Est. Ativa (norm)", f"{exec_active_norm_h:,.1f}"),
            create_kpi_card("Horas Est. Validação/QA (norm)", f"{exec_validation_norm_h:,.1f}"),
            create_kpi_card("Horas Est. Espera (norm)", f"{exec_wait_norm_h:,.1f}"),
            create_kpi_card("Commits (Bitbucket)", int(bb_totals.get("Commits", 0))),
            create_kpi_card("PRs Merged (Bitbucket)", int(bb_totals.get("PRs Merged", 0))),
            create_kpi_card("Aprovações PR (Bitbucket)", int(bb_totals.get("Aprovacoes", 0))),
            create_kpi_card("Reprovações PR (Bitbucket)", int(bb_totals.get("Reprovacoes", 0))),
            create_kpi_card("Itens c/ Evidência Técnica", int(cross_totals.get("Itens c/ Evidencia Tecnica", 0))),
            create_kpi_card("Cobertura Técnica", f"{float(cross_totals.get('Cobertura Tecnica (%)', 0.0)):.1f}%"),
        ],
        style={"display": "grid", "gridTemplateColumns": "repeat(6, minmax(165px, 1fr))", "gap": "10px", "marginBottom": "16px"},
    )

    fig_cross_integrado = go.Figure()
    if not cross_people.empty:
        x = cross_people.copy()
        for col in ["Score Integrado", "Cobertura Tecnica (%)"]:
            if col in x.columns:
                x[col] = _safe_num(x[col]).fillna(0)
        x = x.sort_values("Score Integrado", ascending=False).head(20)
        fig_cross_integrado = px.bar(
            x,
            x="Score Integrado",
            y="Pessoa",
            orientation="h",
            color="Cobertura Tecnica (%)" if "Cobertura Tecnica (%)" in x.columns else None,
            color_continuous_scale="Tealgrn",
            title="Capacidade Integrada por Pessoa (Jira + Bitbucket)",
            hover_data=[c for c in ["Itens Concluidos", "Commits", "PRs Merged", "Aprovacoes", "Reprovacoes", "Itens c/ Evidencia Tecnica"] if c in x.columns],
        )
        fig_cross_integrado.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

    try:
        cross_topn = int(cross_topn)
    except Exception:
        cross_topn = 5
    cross_topn = min(max(cross_topn, 1), 30)
    weekly_metric_map = {
        "score": ("Score Integrado", "Score Integrado"),
        "itens_concluidos": ("Itens Concluidos", "Itens Concluídos"),
        "commits": ("Commits", "Commits"),
        "prs_merged": ("PRs Merged", "PRs Merged"),
        "prs_abertos": ("PRs Abertos", "PRs Abertos"),
    }
    weekly_metric_col, weekly_metric_label = weekly_metric_map.get(str(cross_weekly_metric), weekly_metric_map["score"])
    cross_weekly = compute_pm_bitbucket_cross_weekly(pm_cases, bitbucket_logs, start_ts, end_ts)
    if person and not cross_weekly.empty and "Pessoa" in cross_weekly.columns:
        cross_weekly = cross_weekly[cross_weekly["Pessoa"] == person].copy()

    fig_cross_weekly = go.Figure()
    if not cross_weekly.empty:
        top_people = (
            cross_people.sort_values("Score Integrado", ascending=False)["Pessoa"].head(cross_topn).tolist()
            if not cross_people.empty and "Pessoa" in cross_people.columns
            else []
        )
        xw = cross_weekly.copy()
        if top_people:
            xw = xw[xw["Pessoa"].isin(top_people)]
        if not xw.empty and weekly_metric_col in xw.columns:
            xw = xw.sort_values(["Semana", weekly_metric_col, "Pessoa"])
            fig_cross_weekly = px.line(
                xw,
                x="Semana",
                y=weekly_metric_col,
                color="Pessoa",
                markers=True,
                title=f"Tendência Semanal Integrada ({weekly_metric_label}, Top {cross_topn})",
            )
            fig_cross_weekly.update_layout(height=500, xaxis_tickangle=-40, margin=dict(b=90))

    fig_vazao = go.Figure()
    if not pm_people.empty and {"Responsavel", "Itens Concluidos"}.issubset(pm_people.columns):
        x = pm_people.copy()
        x["Itens Concluidos"] = pd.to_numeric(x["Itens Concluidos"], errors="coerce").fillna(0)
        if "Taxa Retrabalho (%)" in x.columns:
            x["Taxa Retrabalho (%)"] = pd.to_numeric(x["Taxa Retrabalho (%)"], errors="coerce")
        x = x.sort_values("Itens Concluidos", ascending=False).head(20)
        fig_vazao = px.bar(x, x="Itens Concluidos", y="Responsavel", orientation="h", color="Taxa Retrabalho (%)" if "Taxa Retrabalho (%)" in x.columns else None, color_continuous_scale="RdYlGn_r", title="Vazão por Pessoa")
        fig_vazao.update_layout(height=520, yaxis={"categoryorder": "total ascending"})

    fig_retrabalho = go.Figure()
    if not pm_people.empty and {"Responsavel", "Itens Com Retrabalho"}.issubset(pm_people.columns):
        x = pm_people.copy()
        x["Itens Com Retrabalho"] = pd.to_numeric(x["Itens Com Retrabalho"], errors="coerce").fillna(0)
        if "Taxa Retrabalho (%)" in x.columns:
            x["Taxa Retrabalho (%)"] = pd.to_numeric(x["Taxa Retrabalho (%)"], errors="coerce")
        x = x.sort_values("Itens Com Retrabalho", ascending=False).head(20)
        fig_retrabalho = px.bar(x, x="Itens Com Retrabalho", y="Responsavel", orientation="h", color="Taxa Retrabalho (%)" if "Taxa Retrabalho (%)" in x.columns else None, color_continuous_scale="OrRd", title="Retrabalho por Pessoa")
        fig_retrabalho.update_layout(height=520, yaxis={"categoryorder": "total ascending"})

    fig_vazao_sem = go.Figure()
    if not pm_weekly.empty and {"Semana", "Responsavel", "Itens Concluidos"}.issubset(pm_weekly.columns):
        x = pm_weekly.copy()
        x["Itens Concluidos"] = pd.to_numeric(x["Itens Concluidos"], errors="coerce").fillna(0)
        if not person and not pm_people.empty and {"Responsavel", "Itens Concluidos"}.issubset(pm_people.columns):
            top_people = (
                pm_people.assign(_tp=pd.to_numeric(pm_people["Itens Concluidos"], errors="coerce").fillna(0))
                .sort_values("_tp", ascending=False)
                .head(5)["Responsavel"]
                .tolist()
            )
            x = x[x["Responsavel"].isin(top_people)]
        fig_vazao_sem = px.line(x, x="Semana", y="Itens Concluidos", color="Responsavel", markers=True, title="Vazão Semanal por Pessoa")
        fig_vazao_sem.update_layout(height=480, xaxis_tickangle=-45, margin=dict(b=100))

    fig_tempo_status = go.Figure()
    if not pm_status.empty and {"Status", "Tempo Mediano (dias)"}.issubset(pm_status.columns):
        x = pm_status.copy()
        x["Tempo Mediano (dias)"] = pd.to_numeric(x["Tempo Mediano (dias)"], errors="coerce").fillna(0)
        x = x.sort_values("Tempo Mediano (dias)", ascending=False).head(15)
        fig_tempo_status = px.bar(x, x="Tempo Mediano (dias)", y="Status", orientation="h", title="Tempos por Status (Mediana)")
        fig_tempo_status.update_layout(height=480, yaxis={"categoryorder": "total ascending"})

    fig_horas_pessoa = go.Figure()
    if not pm_hours_people.empty and {"Responsavel", "HorasNoFluxo"}.issubset(pm_hours_people.columns):
        x = pm_hours_people.copy()
        x["HorasNoFluxo"] = _safe_num(x["HorasNoFluxo"]).fillna(0)
        if "HorasMediasPorEvento" in x.columns:
            x["HorasMediasPorEvento"] = _safe_num(x["HorasMediasPorEvento"])
        x = x.sort_values("HorasNoFluxo", ascending=False).head(20)
        fig_horas_pessoa = px.bar(
            x,
            x="HorasNoFluxo",
            y="Responsavel",
            orientation="h",
            color="HorasMediasPorEvento" if "HorasMediasPorEvento" in x.columns else None,
            title="Horas no Fluxo por Pessoa (proxy por transição/status)",
            color_continuous_scale="Blues",
        )
        fig_horas_pessoa.update_layout(height=520, yaxis={"categoryorder": "total ascending"})

    fig_horas_status = go.Figure()
    if not pm_hours_status.empty and {"Responsavel", "Status", "HorasNoFluxo"}.issubset(pm_hours_status.columns):
        x = pm_hours_status.copy()
        x["HorasNoFluxo"] = _safe_num(x["HorasNoFluxo"]).fillna(0)
        x["Pessoa-Status"] = x["Responsavel"].astype(str) + " | " + x["Status"].astype(str)
        x = x.sort_values("HorasNoFluxo", ascending=False).head(20)
        fig_horas_status = px.bar(
            x,
            x="HorasNoFluxo",
            y="Pessoa-Status",
            orientation="h",
            title="Horas no Fluxo por Pessoa e Status (Top 20 combinações)",
        )
        fig_horas_status.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

    fig_transition_map = build_transition_sankey(pm_events)
    fig_variants = build_variants_pareto(pm_variants)
    fig_conf_hist, fig_lt_rework = build_conformance_rework_figs(pm_cases)
    fig_event_vol = build_event_volume_fig(pm_events)
    fig_dotted_chart = build_dotted_chart_fig(pm_events)
    fig_tbr_hist, fig_tbr_dev = build_tbr_figs(pm_tbr_cases)
    fig_align_hist, fig_align_moves = build_align_figs(pm_align_cases, pm_align_moves)
    petri_source_events = exec_event_hours if not exec_event_hours.empty else event_hours
    fig_petri_network = build_petri_bottleneck_network_fig(petri_source_events)
    fig_petri_transitions = build_petri_bottleneck_transition_fig(petri_source_events)
    fig_petri_status = build_petri_bottleneck_status_fig(petri_source_events)

    fig_dfg_edges = go.Figure()
    dfg_source = pm_dfg_edges if (not start_date and not pm_dfg_edges.empty and {"From", "To", "Count"}.issubset(pm_dfg_edges.columns)) else build_dfg_edges_from_events(pm_events)
    if not dfg_source.empty:
        x = dfg_source.copy()
        if "From" not in x.columns and "From Status" in x.columns:
            x = x.rename(columns={"From Status": "From", "To Status": "To"})
        x["Count"] = _safe_num(x["Count"]).fillna(0)
        x["Aresta"] = x["From"].astype(str) + " → " + x["To"].astype(str)
        x = x.sort_values("Count", ascending=False).head(20)
        dfg_title = "DFG (pm4py) - Top Arestas (global)" if (not start_date and not pm_dfg_edges.empty) else "DFG (eventos filtrados) - Top Arestas"
        fig_dfg_edges = px.bar(x, x="Count", y="Aresta", orientation="h", title=dfg_title)
        fig_dfg_edges.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

    fig_dfg_perf_edges = go.Figure()
    if not pm_dfg_perf_edges.empty and {"From", "To"}.issubset(pm_dfg_perf_edges.columns):
        x = pm_dfg_perf_edges.copy()
        if "PerfHours" in x.columns:
            x["PerfHours"] = _safe_num(x["PerfHours"])
        if "PerfSeconds" in x.columns:
            x["PerfSeconds"] = _safe_num(x["PerfSeconds"])
        metric_col = "PerfHours" if "PerfHours" in x.columns else "PerfSeconds" if "PerfSeconds" in x.columns else None
        if metric_col:
            x = x.dropna(subset=[metric_col]).copy()
            if not x.empty:
                x["Count"] = _safe_num(x.get("Count", 0)).fillna(0)
                x["Aresta"] = x["From"].astype(str) + " → " + x["To"].astype(str)
                x = x.sort_values([metric_col, "Count"], ascending=[False, False]).head(20)
                title = "DFG Performance (pm4py) - Top Arestas por Tempo"
                fig_dfg_perf_edges = px.bar(
                    x,
                    x=metric_col,
                    y="Aresta",
                    orientation="h",
                    color="Count" if "Count" in x.columns else None,
                    color_continuous_scale="YlOrRd",
                    hover_data=[c for c in ["Count", "PerfSeconds", "PerfHours"] if c in x.columns],
                    title=title,
                )
                fig_dfg_perf_edges.update_layout(
                    height=560,
                    yaxis={"categoryorder": "total ascending"},
                    xaxis_title="Horas entre atividades" if metric_col == "PerfHours" else "Segundos entre atividades",
                )

    fig_exec_by_person = go.Figure()
    if not exec_by_person.empty:
        x = exec_by_person.head(20).copy()
        fig_exec_by_person = px.bar(
            x,
            x="HorasExecucaoUteisPeriodo" if "HorasExecucaoUteisPeriodo" in x.columns else "HorasExecucaoPeriodo",
            y="Responsavel",
            orientation="h",
            color="MediaHorasUteisPorEvento" if "MediaHorasUteisPorEvento" in x.columns else "MediaHorasPorEvento",
            color_continuous_scale="Teal",
            title="Horas Úteis de Execução no Período por Pessoa (heurística)",
        )
        fig_exec_by_person.update_layout(height=520, yaxis={"categoryorder": "total ascending"})

    fig_exec_by_status = go.Figure()
    if not exec_by_status.empty:
        x = exec_by_status.head(20).copy()
        x["Pessoa-Status"] = x["Responsavel"].astype(str) + " | " + x["Status"].astype(str)
        fig_exec_by_status = px.bar(
            x,
            x="HorasExecucaoUteisPeriodo" if "HorasExecucaoUteisPeriodo" in x.columns else "HorasExecucaoPeriodo",
            y="Pessoa-Status",
            orientation="h",
            title="Horas Úteis de Execução no Período por Pessoa e Status (Top 20)",
        )
        fig_exec_by_status.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

    fig_exec_bucket_person = go.Figure()
    if not exec_event_hours.empty and {"Author", "ExecBucket", "HorasUteisPeriodo"}.issubset(exec_event_hours.columns):
        xb = (
            exec_event_hours.assign(Responsavel=exec_event_hours["Author"].fillna("").replace("", "Sem Autor"))
            .groupby(["Responsavel", "ExecBucket"], dropna=False)["HorasUteisPeriodo"]
            .sum()
            .reset_index()
        )
        if not xb.empty:
            totals = xb.groupby("Responsavel")["HorasUteisPeriodo"].sum().sort_values(ascending=False)
            top_people = totals.head(15).index.tolist()
            xb = xb[xb["Responsavel"].isin(top_people)].copy()
            xb["ExecBucket"] = pd.Categorical(
                xb["ExecBucket"],
                categories=["Execucao Ativa", "Validacao/QA", "Espera"],
                ordered=True,
            )
            fig_exec_bucket_person = px.bar(
                xb,
                x="HorasUteisPeriodo",
                y="Responsavel",
                color="ExecBucket",
                orientation="h",
                barmode="stack",
                title="Horas Úteis por Pessoa (Execução Ativa vs Validação/QA vs Espera)",
                color_discrete_map={"Execucao Ativa": "#0f766e", "Validacao/QA": "#2563eb", "Espera": "#f59e0b"},
            )
            fig_exec_bucket_person.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

    fig_exec_bucket_status = go.Figure()
    if not exec_event_hours.empty and {"To Status", "ExecBucket", "HorasUteisPeriodo"}.issubset(exec_event_hours.columns):
        xs = (
            exec_event_hours.groupby(["To Status", "ExecBucket"], dropna=False)["HorasUteisPeriodo"]
            .sum()
            .reset_index()
            .rename(columns={"To Status": "Status"})
        )
        if not xs.empty:
            totals = xs.groupby("Status")["HorasUteisPeriodo"].sum().sort_values(ascending=False)
            top_status = totals.head(15).index.tolist()
            xs = xs[xs["Status"].isin(top_status)].copy()
            xs["ExecBucket"] = pd.Categorical(
                xs["ExecBucket"],
                categories=["Execucao Ativa", "Validacao/QA", "Espera"],
                ordered=True,
            )
            fig_exec_bucket_status = px.bar(
                xs,
                x="HorasUteisPeriodo",
                y="Status",
                color="ExecBucket",
                orientation="h",
                barmode="stack",
                title="Horas Úteis por Etapa do Fluxo (Ativa vs Validação/QA vs Espera)",
                color_discrete_map={"Execucao Ativa": "#0f766e", "Validacao/QA": "#2563eb", "Espera": "#f59e0b"},
            )
            fig_exec_bucket_status.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

    fig_exec_norm_by_person = go.Figure()
    if not exec_norm_by_person.empty:
        x = exec_norm_by_person.head(20).copy()
        fig_exec_norm_by_person = px.bar(
            x,
            x="HorasEstimadasTrabalho",
            y="Responsavel",
            orientation="h",
            color="MediaHrsEstimadasPorDiaAtivo" if "MediaHrsEstimadasPorDiaAtivo" in x.columns else None,
            color_continuous_scale="Viridis",
            title=f"Horas Estimadas de Trabalho por Pessoa (normalizadas; cap {WORKDAY_DAILY_CAP_HOURS:.0f}h/dia)",
            hover_data=[c for c in ["HorasUteisCargaFluxo", "HorasEstimadasTrabalhoPonderadas", "DiasAtivos", "CardsUnicos"] if c in x.columns],
        )
        fig_exec_norm_by_person.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

    fig_exec_norm_vs_load = go.Figure()
    if not exec_norm_by_person.empty and {"Responsavel", "HorasUteisCargaFluxo", "HorasEstimadasTrabalho"}.issubset(exec_norm_by_person.columns):
        x = exec_norm_by_person.head(20).copy()
        x = x.sort_values("HorasEstimadasTrabalho", ascending=False)
        fig_exec_norm_vs_load = go.Figure()
        fig_exec_norm_vs_load.add_bar(
            x=x["Responsavel"],
            y=x["HorasUteisCargaFluxo"],
            name="Carga de Fluxo (h úteis)",
            marker_color="#93c5fd",
        )
        fig_exec_norm_vs_load.add_bar(
            x=x["Responsavel"],
            y=x["HorasEstimadasTrabalho"],
            name="Horas Estimadas (normalizadas)",
            marker_color="#0f766e",
        )
        fig_exec_norm_vs_load.update_layout(
            barmode="group",
            height=520,
            title="Carga de Fluxo vs Horas Estimadas de Trabalho por Pessoa",
            xaxis_tickangle=-35,
        )

    fig_exec_norm_bucket_person = go.Figure()
    if not exec_norm_by_bucket.empty and {"Responsavel", "ExecBucket", "HorasEstimadasTrabalho"}.issubset(exec_norm_by_bucket.columns):
        xb = exec_norm_by_bucket.copy()
        totals = xb.groupby("Responsavel")["HorasEstimadasTrabalho"].sum().sort_values(ascending=False)
        top_people = totals.head(15).index.tolist()
        xb = xb[xb["Responsavel"].isin(top_people)].copy()
        xb["ExecBucket"] = pd.Categorical(xb["ExecBucket"], categories=["Execucao Ativa", "Validacao/QA", "Espera"], ordered=True)
        fig_exec_norm_bucket_person = px.bar(
            xb,
            x="HorasEstimadasTrabalho",
            y="Responsavel",
            color="ExecBucket",
            orientation="h",
            barmode="stack",
            title=f"Horas Estimadas por Pessoa (Ativa vs Validação/QA vs Espera; cap {WORKDAY_DAILY_CAP_HOURS:.0f}h/dia)",
            color_discrete_map={"Execucao Ativa": "#0f766e", "Validacao/QA": "#2563eb", "Espera": "#f59e0b"},
        )
        fig_exec_norm_bucket_person.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

    fig_exec_norm_bucket_status = go.Figure()
    if not exec_daily_norm.empty and {"Status", "ExecBucket", "HorasEstimadasTrabalho"}.issubset(
        exec_daily_norm.rename(columns={"HorasUteisNormalizadas": "HorasEstimadasTrabalho"}).columns
    ):
        xs = (
            exec_daily_norm.groupby(["Status", "ExecBucket"], dropna=False)["HorasUteisNormalizadas"]
            .sum()
            .reset_index()
            .rename(columns={"HorasUteisNormalizadas": "HorasEstimadasTrabalho"})
        )
        if not xs.empty:
            totals = xs.groupby("Status")["HorasEstimadasTrabalho"].sum().sort_values(ascending=False)
            top_status = totals.head(15).index.tolist()
            xs = xs[xs["Status"].isin(top_status)].copy()
            xs["ExecBucket"] = pd.Categorical(xs["ExecBucket"], categories=["Execucao Ativa", "Validacao/QA", "Espera"], ordered=True)
            fig_exec_norm_bucket_status = px.bar(
                xs,
                x="HorasEstimadasTrabalho",
                y="Status",
                color="ExecBucket",
                orientation="h",
                barmode="stack",
                title=f"Horas Estimadas por Etapa do Fluxo (cap {WORKDAY_DAILY_CAP_HOURS:.0f}h/dia por pessoa)",
                color_discrete_map={"Execucao Ativa": "#0f766e", "Validacao/QA": "#2563eb", "Espera": "#f59e0b"},
            )
            fig_exec_norm_bucket_status.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

    fig_bottleneck_median = go.Figure()
    fig_bottleneck_load = go.Figure()
    fig_bottleneck_scatter = go.Figure()
    if not bottlenecks.empty:
        xb = bottlenecks.copy()
        xb["HorasUteisMedianaEvento"] = _safe_num(xb["HorasUteisMedianaEvento"]).fillna(0)
        xb["HorasUteisP85Evento"] = _safe_num(xb["HorasUteisP85Evento"]).fillna(0)
        xb["HorasUteisTotalPeriodo"] = _safe_num(xb["HorasUteisTotalPeriodo"]).fillna(0)
        xb["Eventos"] = _safe_num(xb["Eventos"]).fillna(0)
        xb["CardsUnicos"] = _safe_num(xb["CardsUnicos"]).fillna(0)
        plot_med = xb.sort_values(["HorasUteisMedianaEvento", "HorasUteisP85Evento"], ascending=False).head(15).sort_values("HorasUteisMedianaEvento")
        fig_bottleneck_median = px.bar(
            plot_med,
            x="HorasUteisMedianaEvento",
            y="Status",
            orientation="h",
            color="HorasUteisP85Evento",
            color_continuous_scale="OrRd",
            title="Gargalo por Status (Tempo Útil Mediano por Evento; p85 na cor)",
            hover_data=["Eventos", "CardsUnicos", "HorasUteisTotalPeriodo"],
        )
        fig_bottleneck_median.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

        plot_load = xb.sort_values("HorasUteisTotalPeriodo", ascending=False).head(15).sort_values("HorasUteisTotalPeriodo")
        fig_bottleneck_load = px.bar(
            plot_load,
            x="HorasUteisTotalPeriodo",
            y="Status",
            orientation="h",
            color="Eventos",
            color_continuous_scale="Blues",
            title="Gargalo por Status (Carga Total de Horas Úteis no Período)",
            hover_data=["HorasUteisMedianaEvento", "HorasUteisP85Evento", "CardsUnicos"],
        )
        fig_bottleneck_load.update_layout(height=560, yaxis={"categoryorder": "total ascending"})

        fig_bottleneck_scatter = px.scatter(
            xb,
            x="HorasUteisMedianaEvento",
            y="HorasUteisTotalPeriodo",
            size="Eventos",
            color="CardsUnicos",
            hover_name="Status",
            hover_data=["HorasUteisP85Evento"],
            title="Mapa de Gargalo: Mediana por Evento x Carga Total (Status)",
            color_continuous_scale="Viridis",
        )
        fig_bottleneck_scatter.update_layout(height=520)

    pm4py_banner = None
    if not pm_meta.empty and {"Metrica", "Valor"}.issubset(pm_meta.columns):
        meta_map = {str(r["Metrica"]): str(r["Valor"]) for _, r in pm_meta.iterrows()}
        if meta_map.get("pm4py_available", "").lower() == "false":
            pm4py_banner = html.Div(
                [
                    html.B("PM4Py não está instalado no ambiente que gerou o relatório. "),
                    html.Span("Os gráficos abaixo usam o workbook exportado (pandas/plotly). "),
                    html.Code("pip install pm4py"),
                    html.Span(" para habilitar métricas extras no script."),
                ],
                style={
                    "background": "#fff8e1",
                    "border": "1px solid #facc15",
                    "padding": "10px 12px",
                    "borderRadius": "8px",
                    "marginBottom": "12px",
                },
            )

    people_cols = [c for c in ["Responsavel", "Itens Concluidos", "Itens Com Retrabalho", "Taxa Retrabalho (%)", "Rework Score Total", "Lead Time Mediano (dias)", "Media Itens/Semana Ativa"] if c in pm_people.columns]
    rework_cols = [c for c in ["Issue Key", "Tipo de Problema", "Rework Score", "Reopen Count", "Backward Moves", "QA Returns", "Revisitas Status", "Conformance Score", "Done Final Author", "Done Final Date"] if c in pm_rework.columns]
    summary_cols = [c for c in ["Metrica", "Valor"] if c in pm_summary.columns]
    meta_cols = [c for c in ["Metrica", "Valor"] if c in pm_meta.columns]
    tbr_summary_cols = [c for c in ["Metric", "Value"] if c in pm_tbr_summary.columns]
    tbr_case_cols = [c for c in ["Issue Key", "TraceIsFit", "TraceFitness", "MissingTokens", "RemainingTokens", "ConsumedTokens", "ProducedTokens", "Done Final Author", "Done Final Date"] if c in pm_tbr_cases.columns]
    align_summary_cols = [c for c in ["Metric", "Value"] if c in pm_align_summary.columns]
    align_case_cols = [c for c in ["Issue Key", "AlignmentFitness", "AlignmentCost", "SyncMoves", "LogMoves", "ModelMoves", "DesviosTotal", "Done Final Author", "Done Final Date"] if c in pm_align_cases.columns]
    align_move_cols = [c for c in ["MoveType", "Activity", "Count", "CasesAffected"] if c in pm_align_moves.columns]
    horas_people_cols = [c for c in ["Responsavel", "HorasNoFluxo", "HorasMediasPorEvento", "Eventos", "CardsUnicos"] if c in pm_hours_people.columns]
    horas_status_cols = [c for c in ["Responsavel", "Status", "HorasNoFluxo", "Eventos", "CardsUnicos"] if c in pm_hours_status.columns]
    exec_people_cols = [c for c in ["Responsavel", "HorasExecucaoUteisPonderadasPeriodo", "HorasExecucaoUteisPeriodo", "HorasExecucaoPonderadasPeriodo", "HorasExecucaoPeriodo", "MediaHorasUteisPorEvento", "MediaHorasPorEvento", "Eventos", "CardsUnicos"] if c in exec_by_person.columns]
    exec_status_cols = [c for c in ["Responsavel", "ExecBucket", "Status", "HorasExecucaoUteisPonderadasPeriodo", "HorasExecucaoUteisPeriodo", "HorasExecucaoPeriodo", "Eventos", "CardsUnicos"] if c in exec_by_status.columns]
    exec_norm_people_cols = [c for c in ["Responsavel", "HorasEstimadasTrabalho", "HorasEstimadasTrabalhoPonderadas", "HorasUteisCargaFluxo", "MediaHrsEstimadasPorDiaAtivo", "DiasAtivos", "CardsUnicos", "Slices"] if c in exec_norm_by_person.columns]
    exec_norm_status_cols = [c for c in ["Responsavel", "ExecBucket", "Status", "HorasEstimadasTrabalho", "HorasEstimadasTrabalhoPonderadas", "HorasUteisCargaFluxo", "DiasComAtividade", "CardsUnicos", "Slices"] if c in exec_norm_by_status.columns]
    cross_people_cols = [c for c in ["Pessoa", "Itens Concluidos", "Itens c/ Evidencia Tecnica", "Cobertura Tecnica (%)", "Commits", "PRs Abertos", "PRs Merged", "Aprovacoes", "Reprovacoes", "Score Integrado"] if c in cross_people.columns]
    bottleneck_cols = [c for c in ["Status", "HorasUteisMedianaEvento", "HorasUteisP85Evento", "HorasUteisP95Evento", "HorasUteisTotalPeriodo", "HorasUteisMediaEvento", "Eventos", "CardsUnicos"] if c in bottlenecks.columns]

    model_cards = []
    model_titles = {
        "dfg": "DFG (pm4py)",
        "dfg_performance": "DFG Performance (pm4py)",
        "heuristics": "Heuristics Miner (pm4py)",
        "inductive_tree": "Inductive Miner - Process Tree (pm4py)",
        "petri": "Inductive Miner - Rede de Petri (pm4py)",
    }
    for key in ["dfg", "dfg_performance", "heuristics", "inductive_tree", "petri"]:
        payload = artifact_images.get(key)
        if not payload:
            continue
        model_cards.append(
            html.Div(
                [
                    html.H4(model_titles.get(key, key), style={"marginBottom": "6px"}),
                    html.Div(html.Code(os.path.basename(payload.get("path", ""))), style={"fontSize": "12px", "color": "#555", "marginBottom": "6px"}),
                    html.Img(
                        src=f"data:image/png;base64,{payload['b64']}",
                        style={"maxWidth": "100%", "border": "1px solid #ddd", "borderRadius": "8px", "background": "white"},
                    ),
                ],
                style={"flex": "1 1 560px", "minWidth": "420px"},
            )
        )

    if not pm_rework.empty:
        sort_cols = [c for c in ["Rework Score", "Reopen Count", "Backward Moves"] if c in pm_rework.columns]
        if sort_cols:
            pm_rework = pm_rework.sort_values(sort_cols, ascending=[False] * len(sort_cols))

    tab_style = {"padding": "12px 10px"}
    tab_content_style = {"padding": "12px 4px"}

    discovery_tab = [
        html.H3("Visualizações de Process Mining", style={"marginTop": "6px"}),
        html.Div(
            model_cards if model_cards else [html.Div("Artefatos visuais pm4py (DFG / Heuristics / Inductive / Petri) ainda não encontrados neste relatório.")],
            style={"display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "8px"},
        ),
        dcc.Graph(figure=fig_dfg_edges),
        dcc.Graph(figure=fig_transition_map),
        dcc.Graph(figure=fig_variants),
        dcc.Graph(figure=fig_event_vol),
    ]

    bottlenecks_tab = [
        html.H3("Rede de Petri e Gargalos do Fluxo", style={"marginTop": "6px"}),
        html.Div(
            [
                html.Span(
                    "A imagem pm4py (quando disponível) mostra a estrutura do processo; os gráficos abaixo ranqueiam gargalos no recorte atual "
                    "usando horas úteis por transição/etapa (com destaque para bucket de espera)."
                )
            ],
            style={"color": "#555", "fontSize": "13px", "marginBottom": "8px"},
        ),
        dcc.Graph(figure=fig_dfg_perf_edges),
        dcc.Graph(figure=fig_dotted_chart),
        dcc.Graph(figure=fig_petri_network),
        html.Div(
            [
                html.Div(dcc.Graph(figure=fig_petri_transitions), style={"flex": "1 1 540px"}),
                html.Div(dcc.Graph(figure=fig_petri_status), style={"flex": "1 1 540px"}),
            ],
            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
        ),
        html.H4("Gargalo no Fluxo (tempo vs carga por status)"),
        html.Div(
            "Segurança da avaliação: compare 3 lentes em conjunto. "
            "1) tempo mediano/p85 por evento (gargalo de espera), "
            "2) carga total de horas úteis (pressão acumulada), "
            "3) mapa mediana x carga (status que combinam tempo alto e volume).",
            style={"color": "#555", "fontSize": "13px", "marginBottom": "8px"},
        ),
        html.Div(
            [
                html.Div(dcc.Graph(figure=fig_bottleneck_median), style={"flex": "1 1 460px"}),
                html.Div(dcc.Graph(figure=fig_bottleneck_load), style={"flex": "1 1 460px"}),
            ],
            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
        ),
        dcc.Graph(figure=fig_bottleneck_scatter),
        dcc.Graph(figure=fig_tempo_status),
        dcc.Graph(figure=fig_exec_bucket_status),
        dcc.Graph(figure=fig_exec_norm_bucket_status),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in bottleneck_cols],
            data=bottlenecks[bottleneck_cols].head(50).to_dict("records") if bottleneck_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_size=12,
        ),
    ]

    conformance_tab = [
        html.H3("Conformidade e Retrabalho", style={"marginTop": "6px"}),
        html.Div(
            [
                html.Div(dcc.Graph(figure=fig_conf_hist), style={"flex": "1 1 420px"}),
                html.Div(dcc.Graph(figure=fig_lt_rework), style={"flex": "1 1 420px"}),
            ],
            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
        ),
        html.H4("Token-Based Replay (PM4Py)"),
        html.Div(
            [
                html.Div(
                    dash_table.DataTable(
                        columns=[{"name": c, "id": c} for c in tbr_summary_cols],
                        data=pm_tbr_summary[tbr_summary_cols].to_dict("records") if tbr_summary_cols else [],
                        style_cell={"textAlign": "left", "padding": "6px"},
                        style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
                        page_size=8,
                    ),
                    style={"flex": "1 1 320px"},
                ),
                html.Div(dcc.Graph(figure=fig_tbr_hist), style={"flex": "1 1 420px"}),
                html.Div(dcc.Graph(figure=fig_tbr_dev), style={"flex": "1 1 480px"}),
            ],
            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
        ),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in tbr_case_cols],
            data=pm_tbr_cases[tbr_case_cols].head(50).to_dict("records") if tbr_case_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px", "minWidth": "100px", "maxWidth": "220px", "whiteSpace": "normal"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_size=12,
        ),
        html.H4("Alignments (PM4Py)"),
        html.Div(
            [
                html.Div(
                    dash_table.DataTable(
                        columns=[{"name": c, "id": c} for c in align_summary_cols],
                        data=pm_align_summary[align_summary_cols].to_dict("records") if align_summary_cols else [],
                        style_cell={"textAlign": "left", "padding": "6px"},
                        style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
                        page_size=8,
                    ),
                    style={"flex": "1 1 320px"},
                ),
                html.Div(dcc.Graph(figure=fig_align_hist), style={"flex": "1 1 420px"}),
                html.Div(dcc.Graph(figure=fig_align_moves), style={"flex": "1 1 480px"}),
            ],
            style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
        ),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in align_move_cols],
            data=pm_align_moves[align_move_cols].head(50).to_dict("records") if align_move_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_size=10,
        ),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in align_case_cols],
            data=pm_align_cases[align_case_cols].head(50).to_dict("records") if align_case_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px", "minWidth": "100px", "maxWidth": "220px", "whiteSpace": "normal"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_size=12,
        ),
        html.H4("Top Itens com Retrabalho"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in rework_cols],
            data=pm_rework[rework_cols].head(50).to_dict("records") if rework_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px", "minWidth": "100px", "maxWidth": "240px", "whiteSpace": "normal"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_size=12,
        ),
        html.H4("Resumo de Conformidade"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in summary_cols],
            data=pm_summary[summary_cols].to_dict("records") if summary_cols else [],
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            page_size=12,
        ),
    ]

    operational_tab = [
        html.H3("Análises Operacionais", style={"marginTop": "6px"}),
        html.Div(
            "Filtro de data aplicado aos eventos do changelog por `History Created`. "
            "Horas de execução no período usam a interseção do intervalo do evento (`History Created` até `Next Timestamp`) com o período selecionado.",
            style={"color": "#555", "fontSize": "13px", "marginBottom": "8px"},
        ),
        html.Div(
            "Heurística de horas úteis: considera somente dias úteis, janela comercial e teto diário. "
            "Buckets: Execução Ativa, Validação/QA e Espera (com pesos por status para estimativa ponderada).",
            style={"color": "#555", "fontSize": "13px", "marginBottom": "8px"},
        ),
        html.Div(
            f"Heurística de capacidade (normalizada): horas úteis são quebradas por dia e normalizadas por pessoa/dia com teto de {WORKDAY_DAILY_CAP_HOURS:.0f}h. "
            "Use esta visão para estimar trabalho humano; use carga de fluxo para detectar pressão/gargalo.",
            style={"color": "#555", "fontSize": "13px", "marginBottom": "8px"},
        ),
        dcc.Graph(figure=fig_exec_by_person),
        dcc.Graph(figure=fig_exec_norm_by_person),
        dcc.Graph(figure=fig_exec_norm_vs_load),
        dcc.Graph(figure=fig_exec_bucket_person),
        dcc.Graph(figure=fig_exec_norm_bucket_person),
        dcc.Graph(figure=fig_exec_by_status),
        dcc.Graph(figure=fig_horas_pessoa),
        dcc.Graph(figure=fig_horas_status),
        dcc.Graph(figure=fig_vazao),
        dcc.Graph(figure=fig_vazao_sem),
        dcc.Graph(figure=fig_retrabalho),
        html.H4("Capacidade Integrada por Pessoa (Jira + Bitbucket)"),
        html.Div(
            "Cruzamento por pessoa usando itens concluídos do Jira, atividade técnica no Bitbucket "
            "(commits/PRs/revisões) e evidência técnica por item (`Issue Key` presente em commit/PR).",
            style={"color": "#555", "fontSize": "13px", "marginBottom": "8px"},
        ),
        dcc.Graph(figure=fig_cross_integrado),
        dcc.Graph(figure=fig_cross_weekly),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in cross_people_cols],
            data=cross_people[cross_people_cols].head(50).to_dict("records") if cross_people_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_size=12,
        ),
        html.H4("Resumo por Pessoa"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in people_cols],
            data=pm_people[people_cols].head(50).to_dict("records") if people_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            page_size=12,
        ),
        html.H4("Horas de Execução no Período por Pessoa (proxy + heurística útil)"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in exec_people_cols],
            data=exec_by_person[exec_people_cols].head(50).to_dict("records") if exec_people_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            page_size=12,
        ),
        html.H4(f"Horas Estimadas de Trabalho por Pessoa (normalizadas; cap {WORKDAY_DAILY_CAP_HOURS:.0f}h/dia)"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in exec_norm_people_cols],
            data=exec_norm_by_person[exec_norm_people_cols].head(50).to_dict("records") if exec_norm_people_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            page_size=12,
        ),
        html.H4("Horas de Execução no Período por Pessoa e Status (proxy + heurística útil)"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in exec_status_cols],
            data=exec_by_status[exec_status_cols].head(50).to_dict("records") if exec_status_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px", "minWidth": "100px", "maxWidth": "240px", "whiteSpace": "normal"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_size=12,
        ),
        html.H4(f"Horas Estimadas de Trabalho por Pessoa e Status (normalizadas; cap {WORKDAY_DAILY_CAP_HOURS:.0f}h/dia)"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in exec_norm_status_cols],
            data=exec_norm_by_status[exec_norm_status_cols].head(80).to_dict("records") if exec_norm_status_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px", "minWidth": "100px", "maxWidth": "260px", "whiteSpace": "normal"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_size=12,
        ),
        html.H4("Horas no Fluxo por Pessoa (proxy)"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in horas_people_cols],
            data=pm_hours_people[horas_people_cols].head(50).to_dict("records") if horas_people_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            page_size=12,
        ),
        html.H4("Horas no Fluxo por Pessoa e Status (proxy)"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in horas_status_cols],
            data=pm_hours_status[horas_status_cols].head(50).to_dict("records") if horas_status_cols else [],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "6px", "minWidth": "100px", "maxWidth": "240px", "whiteSpace": "normal"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            sort_action="native",
            filter_action="native",
            page_size=12,
        ),
    ]

    data_tab = [
        html.H3("Resumo e Metadados", style={"marginTop": "6px"}),
        html.H4("Metadados"),
        dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in meta_cols],
            data=pm_meta[meta_cols].to_dict("records") if meta_cols else [],
            style_cell={"textAlign": "left", "padding": "6px", "whiteSpace": "normal"},
            style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
            page_size=12,
        ),
    ]

    return html.Div(
        [
            pm4py_banner if pm4py_banner else html.Div(),
            kpi_grid,
            dcc.Tabs(
                id="pm-domain-tabs",
                value="tab-discovery",
                children=[
                    dcc.Tab(label="Descoberta", value="tab-discovery", style=tab_style, selected_style=tab_style, children=html.Div(discovery_tab, style=tab_content_style)),
                    dcc.Tab(label="Gargalos", value="tab-bottlenecks", style=tab_style, selected_style=tab_style, children=html.Div(bottlenecks_tab, style=tab_content_style)),
                    dcc.Tab(label="Conformidade", value="tab-conformance", style=tab_style, selected_style=tab_style, children=html.Div(conformance_tab, style=tab_content_style)),
                    dcc.Tab(label="Operacional", value="tab-operational", style=tab_style, selected_style=tab_style, children=html.Div(operational_tab, style=tab_content_style)),
                    dcc.Tab(label="Dados/Meta", value="tab-data", style=tab_style, selected_style=tab_style, children=html.Div(data_tab, style=tab_content_style)),
                ],
            ),
        ]
    )


if __name__ == "__main__":
    app.run(debug=True, port=8051)
