import os
import re
import unicodedata
import warnings
from datetime import timedelta

import numpy as np
import pandas as pd

from shared.path_utils import candidate_data_folders


warnings.filterwarnings("ignore", message="Mean of empty slice", category=RuntimeWarning)


PROJECT_FILE_PREFIX = {
    "W1NNER": "w1nner",
    "W1NNR": "w1nner",
    "S1NC": "s1nc",
    "BF": "befinance",
    "BEFINANCE": "befinance",
    "DT": "dataanalytics",
    "DATA&ANALYTICS": "dataanalytics",
    "DATA ANALYTICS": "dataanalytics",
}

SPAF_DIMENSIONS = [
    "Temporal",
    "Intensity",
    "Parallelism",
    "Quality vs Load",
    "Human Sustainability",
    "Efficiency",
    "Collab under Load",
    "Predictive",
]

WORKDAY_START_HOUR = 8
WORKDAY_END_HOUR = 19


def normalize_text(value):
    text = str(value or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


def normalize_person(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return ""
    if "<" in text:
        text = text.split("<", 1)[0].strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _safe_series(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def _score_higher_better(value, good, bad):
    if pd.isna(value):
        return np.nan
    value = float(value)
    good = float(good)
    bad = float(bad)
    if good == bad:
        return 100.0 if value >= good else 0.0
    if value >= good:
        return 100.0
    if value <= bad:
        return 0.0
    return round((value - bad) / (good - bad) * 100.0, 1)


def _score_lower_better(value, good, bad):
    if pd.isna(value):
        return np.nan
    value = float(value)
    good = float(good)
    bad = float(bad)
    if good == bad:
        return 100.0 if value <= good else 0.0
    if value <= good:
        return 100.0
    if value >= bad:
        return 0.0
    return round((bad - value) / (bad - good) * 100.0, 1)


def _safe_ratio(num, den):
    try:
        num = float(num)
        den = float(den)
    except Exception:
        return np.nan
    if den <= 0:
        return np.nan
    return num / den


def _nanmean(values):
    valid = [float(v) for v in values if pd.notna(v)]
    if not valid:
        return np.nan
    return float(sum(valid) / len(valid))


def _to_naive_datetime(series):
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    try:
        return parsed.dt.tz_localize(None)
    except Exception:
        return pd.to_datetime(series, errors="coerce")


def _project_aliases(project_name):
    raw = str(project_name or "").strip()
    norm = normalize_text(raw)
    aliases = {norm}
    mapping = {
        "w1nner": {"w1nner", "w1nnr"},
        "s1nc": {"s1nc"},
        "befinance": {"befinance", "bf"},
        "data analytics": {"dt", "data analytics", "data analytics", "data analytics", "data&analytics"},
    }
    for values in mapping.values():
        if norm in values:
            aliases |= values
    return {alias for alias in aliases if alias}


def _resolve_model_file(data_folders):
    explicit_model = os.getenv("FLOW_PMO_MODEL_FILE", "").strip()
    if explicit_model:
        candidate = explicit_model if os.path.isabs(explicit_model) else os.path.join(os.path.dirname(__file__), explicit_model)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        raise FileNotFoundError(f"FLOW_PMO_MODEL_FILE aponta para arquivo inexistente: {candidate}")

    model_files = []
    for folder in data_folders:
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if name.startswith("PowerBI_Model_") and name.endswith(".xlsx"):
                model_files.append(os.path.join(folder, name))
    if model_files:
        return max(model_files, key=os.path.getctime)
    raise FileNotFoundError("PowerBI_Model_*.xlsx não encontrado nas pastas de dados resolvidas.")


def _find_latest_prefixed_file(data_folders, prefix, suffix):
    candidates = []
    for folder in data_folders:
        if not os.path.isdir(folder):
            continue
        try:
            entries = os.listdir(folder)
        except Exception:
            continue
        for name in entries:
            low = name.lower()
            if low.startswith(prefix.lower()) and low.endswith(suffix.lower()):
                path = os.path.join(folder, name)
                if os.path.isfile(path):
                    candidates.append(path)
    return max(candidates, key=os.path.getctime) if candidates else None


def _read_csv_maybe(path):
    if not path or not os.path.isfile(path):
        return pd.DataFrame()
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception:
            continue
    return pd.DataFrame()


def _load_bitbucket_logs(data_folders, project_name):
    project_key = str(project_name or "").strip().upper()
    prefix = PROJECT_FILE_PREFIX.get(project_key, "")
    if not prefix:
        return {"commits": pd.DataFrame(), "pullrequests": pd.DataFrame(), "pipelines": pd.DataFrame()}

    commits = _read_csv_maybe(_find_latest_prefixed_file(data_folders, f"{prefix}_commits", ".csv"))
    prs = _read_csv_maybe(_find_latest_prefixed_file(data_folders, f"{prefix}_pullrequests", ".csv"))
    pipes = _read_csv_maybe(_find_latest_prefixed_file(data_folders, f"{prefix}_pipelines", ".csv"))

    for df, date_cols in (
        (commits, ["date"]),
        (prs, ["created_on", "updated_on"]),
        (pipes, ["created_on", "completed_on"]),
    ):
        for col in date_cols:
            if col in df.columns:
                df[col] = _to_naive_datetime(df[col])

    if "author" in commits.columns:
        commits["person_norm"] = commits["author"].apply(normalize_person).map(normalize_text)
    if "author" in prs.columns:
        prs["person_norm"] = prs["author"].apply(normalize_person).map(normalize_text)
    if "state_result" in pipes.columns:
        pipes["state_norm"] = pipes["state_result"].fillna("").astype(str).str.strip().str.lower()

    return {"commits": commits, "pullrequests": prs, "pipelines": pipes}


def _load_pm_cases(data_folders, project_name):
    project_key = str(project_name or "").strip().upper()
    prefix = PROJECT_FILE_PREFIX.get(project_key, "")
    if not prefix:
        return {"cases": pd.DataFrame(), "events": pd.DataFrame()}

    workbook = _find_latest_prefixed_file(data_folders, f"{prefix}-process-mining-", ".xlsx")
    if not workbook:
        return {"cases": pd.DataFrame(), "events": pd.DataFrame()}

    try:
        xls = pd.ExcelFile(workbook)
    except Exception:
        return {"cases": pd.DataFrame(), "events": pd.DataFrame()}

    out = {}
    for sheet, key in (("ConformidadeCasos", "cases"), ("EventosFiltrados", "events")):
        if sheet not in xls.sheet_names:
            out[key] = pd.DataFrame()
            continue
        try:
            out[key] = pd.read_excel(xls, sheet_name=sheet)
        except Exception:
            out[key] = pd.DataFrame()

    if "Done Final Date" in out["cases"].columns:
        out["cases"]["Done Final Date"] = _to_naive_datetime(out["cases"]["Done Final Date"])
    if "History Date" in out["events"].columns:
        out["events"]["History Date"] = _to_naive_datetime(out["events"]["History Date"])
    if "Done Final Author" in out["cases"].columns:
        out["cases"]["person_norm"] = out["cases"]["Done Final Author"].apply(normalize_person).map(normalize_text)
    if "Author" in out["events"].columns:
        out["events"]["person_norm"] = out["events"]["Author"].apply(normalize_person).map(normalize_text)
    return out


def load_spaf_context():
    data_folders = candidate_data_folders()
    model_file = _resolve_model_file(data_folders)
    xls = pd.ExcelFile(model_file)
    dim_projeto = pd.read_excel(xls, sheet_name="Dim_Projeto")
    dim_tipo = pd.read_excel(xls, sheet_name="Dim_Tipo")
    dim_resp = pd.read_excel(xls, sheet_name="Dim_Responsavel") if "Dim_Responsavel" in xls.sheet_names else pd.DataFrame()
    fact = pd.read_excel(xls, sheet_name="Fato_Items")

    for col in ["DataBacklog", "DataInProgress", "DataDone", "DataCancelled"]:
        if col in fact.columns:
            fact[col] = pd.to_datetime(fact[col], errors="coerce")

    fact = fact.merge(dim_projeto, on="ProjetoID", how="left")
    fact = fact.merge(dim_tipo, on="TipoID", how="left")
    if not dim_resp.empty:
        fact = fact.merge(dim_resp, on="ResponsavelID", how="left")

    fact.rename(
        columns={
            "NomeProjeto": "Projeto",
            "Responsavel": "Responsavel",
        },
        inplace=True,
    )

    if "Projeto" not in fact.columns:
        fact["Projeto"] = ""
    if "Responsavel" not in fact.columns:
        fact["Responsavel"] = fact.get("ResponsavelNome", "")
    elif "ResponsavelNome" in fact.columns:
        responsavel_base = fact["Responsavel"].fillna("").astype(str).str.strip()
        responsavel_nome = fact["ResponsavelNome"].fillna("").astype(str).str.strip()
        fact["Responsavel"] = responsavel_base.where(responsavel_base.ne(""), responsavel_nome)

    fact["Projeto"] = fact["Projeto"].fillna("").astype(str).str.strip()
    fact["Responsavel"] = fact["Responsavel"].fillna("").astype(str).str.strip()
    fact["person_norm"] = fact["Responsavel"].apply(normalize_person).map(normalize_text)
    fact["project_norm"] = fact["Projeto"].map(normalize_text)

    available_projects = [p for p in sorted(fact["Projeto"].dropna().astype(str).str.strip().unique()) if p]
    bitbucket = {project: _load_bitbucket_logs(data_folders, project) for project in available_projects}
    process_mining = {project: _load_pm_cases(data_folders, project) for project in available_projects}

    date_candidates = []
    for col in ["DataBacklog", "DataInProgress", "DataDone"]:
        if col in fact.columns:
            ser = pd.to_datetime(fact[col], errors="coerce").dropna()
            if not ser.empty:
                date_candidates.append((ser.min(), ser.max()))

    if date_candidates:
        min_date = min(pair[0] for pair in date_candidates).normalize()
        max_date = max(pair[1] for pair in date_candidates).normalize()
    else:
        now = pd.Timestamp.utcnow().tz_localize(None).normalize()
        min_date = now - pd.Timedelta(days=90)
        max_date = now

    return {
        "data_folders": data_folders,
        "model_file": model_file,
        "fact": fact,
        "projects": available_projects,
        "bitbucket": bitbucket,
        "process_mining": process_mining,
        "min_date": min_date,
        "max_date": max_date,
    }


def _period_overlap_mask(df, start_ts, end_ts):
    started = pd.to_datetime(df.get("DataInProgress"), errors="coerce")
    backlog = pd.to_datetime(df.get("DataBacklog"), errors="coerce")
    done = pd.to_datetime(df.get("DataDone"), errors="coerce")
    effective_start = started.fillna(backlog)
    effective_end = done.fillna(end_ts + pd.Timedelta(days=1))
    return effective_start.notna() & (effective_start <= end_ts) & (effective_end >= start_ts)


def _filter_fact_scope(fact_df, start_ts, end_ts, selected_projects):
    df = fact_df.copy()
    if selected_projects:
        allowed_norms = set()
        for project in selected_projects:
            allowed_norms |= _project_aliases(project)
        df = df[df["project_norm"].isin(allowed_norms)].copy()
    if df.empty:
        return df
    df = df[_period_overlap_mask(df, start_ts, end_ts)].copy()
    return df


def _filter_bitbucket_scope(bitbucket_map, selected_projects, start_ts, end_ts):
    projects = selected_projects or list(bitbucket_map.keys())
    commits, prs, pipes = [], [], []
    for project in projects:
        logs = bitbucket_map.get(project, {})
        cdf = logs.get("commits", pd.DataFrame()).copy()
        pdf = logs.get("pullrequests", pd.DataFrame()).copy()
        ldf = logs.get("pipelines", pd.DataFrame()).copy()
        if not cdf.empty and "date" in cdf.columns:
            cdf = cdf[(cdf["date"] >= start_ts) & (cdf["date"] <= end_ts)].copy()
            cdf["Projeto"] = project
            commits.append(cdf)
        if not pdf.empty and "updated_on" in pdf.columns:
            pdf = pdf[(pdf["updated_on"] >= start_ts) & (pdf["updated_on"] <= end_ts)].copy()
            pdf["Projeto"] = project
            prs.append(pdf)
        if not ldf.empty and "completed_on" in ldf.columns:
            ldf = ldf[(ldf["completed_on"] >= start_ts) & (ldf["completed_on"] <= end_ts)].copy()
            ldf["Projeto"] = project
            pipes.append(ldf)
    return {
        "commits": pd.concat(commits, ignore_index=True) if commits else pd.DataFrame(),
        "pullrequests": pd.concat(prs, ignore_index=True) if prs else pd.DataFrame(),
        "pipelines": pd.concat(pipes, ignore_index=True) if pipes else pd.DataFrame(),
    }


def _filter_pm_scope(pm_map, selected_projects, start_ts, end_ts):
    projects = selected_projects or list(pm_map.keys())
    cases, events = [], []
    for project in projects:
        data = pm_map.get(project, {})
        cdf = data.get("cases", pd.DataFrame()).copy()
        edf = data.get("events", pd.DataFrame()).copy()
        if not cdf.empty and "Done Final Date" in cdf.columns:
            cdf = cdf[(cdf["Done Final Date"] >= start_ts) & (cdf["Done Final Date"] <= end_ts)].copy()
            cdf["Projeto"] = project
            cases.append(cdf)
        if not edf.empty and "History Date" in edf.columns:
            edf = edf[(edf["History Date"] >= start_ts) & (edf["History Date"] <= end_ts)].copy()
            edf["Projeto"] = project
            events.append(edf)
    return {
        "cases": pd.concat(cases, ignore_index=True) if cases else pd.DataFrame(),
        "events": pd.concat(events, ignore_index=True) if events else pd.DataFrame(),
    }


def _business_days_between(start_ts, end_ts):
    days = pd.bdate_range(start_ts.normalize(), end_ts.normalize())
    return max(len(days), 1)


def _calendar_days_between(start_ts, end_ts):
    return max((end_ts.normalize() - start_ts.normalize()).days + 1, 1)


def _build_daily_concurrency(scope_df, start_ts, end_ts):
    if scope_df.empty:
        return pd.DataFrame(columns=["Date", "ConcurrentItems"])

    start_candidates = pd.to_datetime(scope_df.get("DataInProgress"), errors="coerce").fillna(
        pd.to_datetime(scope_df.get("DataBacklog"), errors="coerce")
    )
    end_candidates = pd.to_datetime(scope_df.get("DataDone"), errors="coerce").fillna(end_ts + pd.Timedelta(days=1))

    rows = []
    for day in pd.date_range(start_ts.normalize(), end_ts.normalize(), freq="D"):
        active_mask = (start_candidates.notna()) & (start_candidates <= day + pd.Timedelta(hours=23, minutes=59)) & (end_candidates >= day)
        rows.append({"Date": day, "ConcurrentItems": int(active_mask.sum())})
    return pd.DataFrame(rows)


def _build_person_day_concurrency(scope_df, start_ts, end_ts):
    if scope_df.empty or "person_norm" not in scope_df.columns:
        return pd.DataFrame(columns=["person_norm", "Date", "ConcurrentItems"])

    start_candidates = pd.to_datetime(scope_df.get("DataInProgress"), errors="coerce").fillna(
        pd.to_datetime(scope_df.get("DataBacklog"), errors="coerce")
    )
    end_candidates = pd.to_datetime(scope_df.get("DataDone"), errors="coerce").fillna(end_ts + pd.Timedelta(days=1))
    people = scope_df["person_norm"].fillna("")

    rows = []
    for day in pd.date_range(start_ts.normalize(), end_ts.normalize(), freq="D"):
        active_mask = (start_candidates.notna()) & (start_candidates <= day + pd.Timedelta(hours=23, minutes=59)) & (end_candidates >= day)
        if not active_mask.any():
            continue
        grouped = people[active_mask & people.ne("")].value_counts()
        for person_norm, concurrent in grouped.items():
            rows.append({"person_norm": person_norm, "Date": day, "ConcurrentItems": int(concurrent)})
    return pd.DataFrame(rows)


def _compute_productivity_aligned_flow_efficiency(scope_df, start_ts, end_ts):
    if scope_df.empty:
        return {
            "itens_entregues": 0,
            "itens_puxados": 0,
            "wip_inicio_periodo": 0,
            "fe_bruta_pct": np.nan,
            "fe_ajustada_pct": np.nan,
        }

    base = scope_df.copy()
    if "person_norm" in base.columns:
        base = base[base["person_norm"].astype(str).str.strip().ne("")].copy()
    if base.empty:
        return {
            "itens_entregues": 0,
            "itens_puxados": 0,
            "wip_inicio_periodo": 0,
            "fe_bruta_pct": np.nan,
            "fe_ajustada_pct": np.nan,
        }

    base = base[
        pd.to_datetime(base.get("DataDone"), errors="coerce").between(start_ts, end_ts, inclusive="both")
    ].copy()
    if base.empty:
        return {
            "itens_entregues": 0,
            "itens_puxados": 0,
            "wip_inicio_periodo": 0,
            "fe_bruta_pct": np.nan,
            "fe_ajustada_pct": np.nan,
        }

    if "ElegivelTempoConcluido" in base.columns:
        done_eligible = base[
            pd.to_numeric(base["ElegivelTempoConcluido"], errors="coerce").fillna(0).eq(1)
        ].copy()
    else:
        done_eligible = base.copy()

    done_window = done_eligible[
        pd.to_datetime(done_eligible.get("DataDone"), errors="coerce").between(start_ts, end_ts, inclusive="both")
    ].copy()
    started_window = base[
        pd.to_datetime(base.get("DataInProgress"), errors="coerce").between(start_ts, end_ts, inclusive="both")
    ].copy()
    wip_inicio = base[
        pd.to_datetime(base.get("DataInProgress"), errors="coerce").notna()
        & (pd.to_datetime(base.get("DataInProgress"), errors="coerce") < start_ts)
        & (
            pd.to_datetime(base.get("DataDone"), errors="coerce").isna()
            | (pd.to_datetime(base.get("DataDone"), errors="coerce") >= start_ts)
        )
    ].copy()

    itens_entregues = int(len(done_window))
    itens_puxados = int(len(started_window))
    wip_inicio_periodo = int(len(wip_inicio))
    fe_bruta_pct = (itens_entregues / itens_puxados * 100.0) if itens_puxados > 0 else (100.0 if itens_entregues > 0 else np.nan)
    fe_ajustada_denom = itens_puxados + wip_inicio_periodo
    fe_ajustada_pct = (
        min(itens_entregues / fe_ajustada_denom * 100.0, 100.0)
        if fe_ajustada_denom > 0
        else (100.0 if itens_entregues > 0 else np.nan)
    )

    return {
        "itens_entregues": itens_entregues,
        "itens_puxados": itens_puxados,
        "wip_inicio_periodo": wip_inicio_periodo,
        "fe_bruta_pct": fe_bruta_pct,
        "fe_ajustada_pct": fe_ajustada_pct,
    }


def _compute_commit_patterns(commits_df):
    if commits_df.empty or "date" not in commits_df.columns:
        return {
            "after_hours_pct": np.nan,
            "weekend_pct": np.nan,
            "median_recovery_days": np.nan,
            "commits_per_active_day": np.nan,
            "commit_hhi": np.nan,
            "active_authors": 0,
        }

    commits_df = commits_df.dropna(subset=["date"]).copy()
    if commits_df.empty:
        return {
            "after_hours_pct": np.nan,
            "weekend_pct": np.nan,
            "median_recovery_days": np.nan,
            "commits_per_active_day": np.nan,
            "commit_hhi": np.nan,
            "active_authors": 0,
        }

    commits_df["hour"] = commits_df["date"].dt.hour
    commits_df["weekday"] = commits_df["date"].dt.weekday
    commits_df["after_hours"] = (commits_df["hour"] < WORKDAY_START_HOUR) | (commits_df["hour"] >= WORKDAY_END_HOUR)
    commits_df["weekend"] = commits_df["weekday"] >= 5
    commits_df["active_day"] = commits_df["date"].dt.normalize()

    active_days = commits_df["active_day"].nunique()
    commits_per_active_day = _safe_ratio(len(commits_df), active_days)

    recovery_gaps = []
    for _, group in commits_df.sort_values("date").groupby("person_norm"):
        days = group["active_day"].dropna().drop_duplicates().sort_values()
        if len(days) < 2:
            continue
        deltas = days.diff().dropna().dt.total_seconds() / 86400.0
        if not deltas.empty:
            recovery_gaps.append(float(deltas.median()))

    shares = commits_df["person_norm"].value_counts(normalize=True)
    commit_hhi = float((shares.pow(2)).sum()) if not shares.empty else np.nan
    return {
        "after_hours_pct": float(commits_df["after_hours"].mean() * 100.0),
        "weekend_pct": float(commits_df["weekend"].mean() * 100.0),
        "median_recovery_days": float(np.median(recovery_gaps)) if recovery_gaps else np.nan,
        "commits_per_active_day": commits_per_active_day,
        "commit_hhi": commit_hhi,
        "active_authors": int(commits_df["person_norm"].replace("", np.nan).dropna().nunique()),
    }


def _compute_pr_patterns(pr_df):
    if pr_df.empty:
        return {
            "avg_reviewers": np.nan,
            "approval_rate": np.nan,
            "median_pr_size": np.nan,
        }
    reviewers = _safe_series(pr_df, "reviewers_total")
    approvals = _safe_series(pr_df, "reviewers_approved_count")
    pr_size = _safe_series(pr_df, "lines_changed_total")
    review_total = reviewers.sum()
    approval_total = approvals.sum()
    return {
        "avg_reviewers": float(reviewers.mean()) if not reviewers.dropna().empty else np.nan,
        "approval_rate": float((approval_total / review_total) * 100.0) if review_total > 0 else np.nan,
        "median_pr_size": float(pr_size.median()) if not pr_size.dropna().empty else np.nan,
    }


def _compute_pipeline_patterns(pipelines_df):
    if pipelines_df.empty:
        return {
            "success_rate": np.nan,
            "change_failure_rate": np.nan,
            "deploys": 0,
        }
    state = pipelines_df.get("state_norm", pd.Series("", index=pipelines_df.index)).astype(str).str.lower()
    success_mask = state.isin({"successful", "success", "passed"})
    fail_mask = state.isin({"failed", "error"})
    total = int((success_mask | fail_mask).sum())
    deploys = int(success_mask.sum())
    return {
        "success_rate": float(success_mask.sum() / total * 100.0) if total > 0 else np.nan,
        "change_failure_rate": float(fail_mask.sum() / total * 100.0) if total > 0 else np.nan,
        "deploys": deploys,
    }


def _compute_pm_patterns(pm_cases_df):
    if pm_cases_df.empty:
        return {
            "rework_rate": np.nan,
            "qa_return_rate": np.nan,
            "conformance_score": np.nan,
        }
    rework_flag = pd.to_numeric(pm_cases_df.get("Rework Score"), errors="coerce").fillna(0) > 0
    qa_flag = pd.to_numeric(pm_cases_df.get("QA Returns"), errors="coerce").fillna(0) > 0
    conformance = pd.to_numeric(pm_cases_df.get("Conformance Score"), errors="coerce").dropna()
    return {
        "rework_rate": float(rework_flag.mean() * 100.0) if len(rework_flag) else np.nan,
        "qa_return_rate": float(qa_flag.mean() * 100.0) if len(qa_flag) else np.nan,
        "conformance_score": float(conformance.mean() * 100.0) if not conformance.empty else np.nan,
    }


def _compute_dimension_scores(scope_df, bitbucket_scope, pm_scope, start_ts, end_ts):
    done_df = scope_df[pd.to_datetime(scope_df.get("DataDone"), errors="coerce").between(start_ts, end_ts, inclusive="both")].copy()
    started_df = scope_df[pd.to_datetime(scope_df.get("DataInProgress"), errors="coerce").between(start_ts, end_ts, inclusive="both")].copy()
    active_df = scope_df[_period_overlap_mask(scope_df, start_ts, end_ts)].copy()

    business_days = _business_days_between(start_ts, end_ts)
    calendar_days = _calendar_days_between(start_ts, end_ts)
    weeks = max(calendar_days / 7.0, 1.0)

    lead_time = _safe_series(done_df, "LeadTime_Dias").dropna()
    wip_days = _safe_series(active_df, "WIP_Dias").dropna()

    productivity_flow = _compute_productivity_aligned_flow_efficiency(scope_df, start_ts, end_ts)
    itens_entregues = productivity_flow["itens_entregues"]
    itens_puxados = productivity_flow["itens_puxados"]
    wip_inicio_periodo = productivity_flow["wip_inicio_periodo"]
    fe_bruta_pct = productivity_flow["fe_bruta_pct"]
    fe_ajustada_pct = productivity_flow["fe_ajustada_pct"]

    defects_done = done_df[done_df.get("Tipo", pd.Series("", index=done_df.index)).astype(str).str.contains("def", case=False, na=False)].copy()
    failure_pct = float(len(defects_done) / len(done_df) * 100.0) if len(done_df) > 0 else np.nan

    daily_concurrency = _build_daily_concurrency(scope_df, start_ts, end_ts)
    person_day_concurrency = _build_person_day_concurrency(scope_df, start_ts, end_ts)
    concurrency_mean = float(daily_concurrency["ConcurrentItems"].mean()) if not daily_concurrency.empty else np.nan
    if not person_day_concurrency.empty:
        high_multiplex_share = float((person_day_concurrency["ConcurrentItems"] > 2).mean() * 100.0)
        concurrent_per_person_mean = float(person_day_concurrency["ConcurrentItems"].mean())
    else:
        high_multiplex_share = np.nan
        concurrent_per_person_mean = np.nan

    wip_tp_ratio = _safe_ratio(len(active_df), max(len(done_df), 1))
    throughput_per_week = _safe_ratio(len(done_df), weeks)
    active_people = int(active_df["person_norm"].replace("", np.nan).dropna().nunique())
    throughput_per_person_week = _safe_ratio(len(done_df), max(active_people * weeks, 1))
    completion_rate = float(len(done_df) / len(started_df) * 100.0) if len(started_df) > 0 else np.nan

    predictability_ratio = np.nan
    if not lead_time.empty and float(lead_time.median()) > 0:
        predictability_ratio = float(lead_time.quantile(0.85) / max(lead_time.median(), 0.01))

    commit_patterns = _compute_commit_patterns(bitbucket_scope.get("commits", pd.DataFrame()))
    pr_patterns = _compute_pr_patterns(bitbucket_scope.get("pullrequests", pd.DataFrame()))
    pipeline_patterns = _compute_pipeline_patterns(bitbucket_scope.get("pipelines", pd.DataFrame()))
    pm_patterns = _compute_pm_patterns(pm_scope.get("cases", pd.DataFrame()))

    temporal_score = _nanmean(
        [
            _score_lower_better(float(lead_time.median()) if not lead_time.empty else np.nan, 5.0, 20.0),
            _score_lower_better(predictability_ratio, 1.8, 3.5),
            _score_lower_better(float(wip_days.median()) if not wip_days.empty else np.nan, 4.0, 18.0),
        ]
    )
    intensity_score = _nanmean(
        [
            _score_lower_better(commit_patterns["commits_per_active_day"], 3.0, 10.0),
            _score_lower_better(commit_patterns["after_hours_pct"], 10.0, 35.0),
            _score_lower_better(_safe_ratio(len(started_df), max(active_people * weeks, 1)), 2.0, 6.0),
        ]
    )
    parallelism_score = _nanmean(
        [
            _score_lower_better(concurrent_per_person_mean, 1.5, 4.5),
            _score_lower_better(high_multiplex_share, 10.0, 45.0),
            _score_lower_better(wip_tp_ratio, 1.5, 4.0),
        ]
    )
    quality_load_score = _nanmean(
        [
            _score_lower_better(failure_pct, 12.0, 35.0),
            _score_lower_better(pm_patterns["rework_rate"], 15.0, 35.0),
            _score_higher_better(pipeline_patterns["success_rate"], 85.0, 60.0),
        ]
    )
    human_score = _nanmean(
        [
            _score_lower_better(commit_patterns["weekend_pct"], 5.0, 20.0),
            _score_lower_better(commit_patterns["after_hours_pct"], 10.0, 35.0),
            _score_higher_better(commit_patterns["median_recovery_days"], 1.0, 0.25),
        ]
    )
    efficiency_score = _nanmean(
        [
            _score_higher_better(fe_ajustada_pct, 75.0, 35.0),
            _score_higher_better(completion_rate, 80.0, 40.0),
            _score_higher_better(throughput_per_person_week, 1.2, 0.25),
        ]
    )
    collab_score = _nanmean(
        [
            _score_higher_better(pr_patterns["avg_reviewers"], 2.0, 0.5),
            _score_higher_better(pr_patterns["approval_rate"], 70.0, 30.0),
            _score_lower_better(commit_patterns["commit_hhi"], 0.18, 0.45),
            _score_lower_better(pr_patterns["median_pr_size"], 250.0, 1500.0),
        ]
    )
    predictive_score = _nanmean(
        [
            _score_lower_better(predictability_ratio, 1.8, 3.5),
            _score_lower_better(pipeline_patterns["change_failure_rate"], 10.0, 35.0),
            _score_lower_better(pm_patterns["rework_rate"], 15.0, 35.0),
            _score_lower_better(wip_tp_ratio, 1.5, 4.0),
        ]
    )

    dimension_scores = {
        "Temporal": temporal_score,
        "Intensity": intensity_score,
        "Parallelism": parallelism_score,
        "Quality vs Load": quality_load_score,
        "Human Sustainability": human_score,
        "Efficiency": efficiency_score,
        "Collab under Load": collab_score,
        "Predictive": predictive_score,
    }
    overall_score = _nanmean(list(dimension_scores.values())) if dimension_scores else np.nan
    evidence = {
        "Lead Time Mediano (dias)": round(float(lead_time.median()), 2) if not lead_time.empty else np.nan,
        "Predictability P85/P50": round(float(predictability_ratio), 2) if pd.notna(predictability_ratio) else np.nan,
        "WIP Age Mediano (dias)": round(float(wip_days.median()), 2) if not wip_days.empty else np.nan,
        "Commits por Dia Ativo": round(float(commit_patterns["commits_per_active_day"]), 2) if pd.notna(commit_patterns["commits_per_active_day"]) else np.nan,
        "% After Hours Commit": round(float(commit_patterns["after_hours_pct"]), 1) if pd.notna(commit_patterns["after_hours_pct"]) else np.nan,
        "% Weekend Commit": round(float(commit_patterns["weekend_pct"]), 1) if pd.notna(commit_patterns["weekend_pct"]) else np.nan,
        "Recovery Gap Mediano (dias)": round(float(commit_patterns["median_recovery_days"]), 2) if pd.notna(commit_patterns["median_recovery_days"]) else np.nan,
        "Concurrency Média": round(float(concurrent_per_person_mean), 2) if pd.notna(concurrent_per_person_mean) else np.nan,
        "% Multiplex >2": round(float(high_multiplex_share), 1) if pd.notna(high_multiplex_share) else np.nan,
        "WIP/TP Ratio": round(float(wip_tp_ratio), 2) if pd.notna(wip_tp_ratio) else np.nan,
        "% Failure Demand": round(float(failure_pct), 1) if pd.notna(failure_pct) else np.nan,
        "% Rework PM": round(float(pm_patterns["rework_rate"]), 1) if pd.notna(pm_patterns["rework_rate"]) else np.nan,
        "Conformance Score (%)": round(float(pm_patterns["conformance_score"]), 1) if pd.notna(pm_patterns["conformance_score"]) else np.nan,
        "Pipeline Success (%)": round(float(pipeline_patterns["success_rate"]), 1) if pd.notna(pipeline_patterns["success_rate"]) else np.nan,
        "Change Failure (%)": round(float(pipeline_patterns["change_failure_rate"]), 1) if pd.notna(pipeline_patterns["change_failure_rate"]) else np.nan,
        "Flow Efficiency Média (%)": round(float(fe_ajustada_pct), 1) if pd.notna(fe_ajustada_pct) else np.nan,
        "Flow Efficiency Bruta (%)": round(float(fe_bruta_pct), 1) if pd.notna(fe_bruta_pct) else np.nan,
        "Completion Rate (%)": round(float(completion_rate), 1) if pd.notna(completion_rate) else np.nan,
        "Itens Puxados": itens_puxados,
        "WIP Início Período": wip_inicio_periodo,
        "Throughput por Pessoa/Semana": round(float(throughput_per_person_week), 2) if pd.notna(throughput_per_person_week) else np.nan,
        "Reviewers por PR": round(float(pr_patterns["avg_reviewers"]), 2) if pd.notna(pr_patterns["avg_reviewers"]) else np.nan,
        "Review Approval (%)": round(float(pr_patterns["approval_rate"]), 1) if pd.notna(pr_patterns["approval_rate"]) else np.nan,
        "Commit HHI": round(float(commit_patterns["commit_hhi"]), 3) if pd.notna(commit_patterns["commit_hhi"]) else np.nan,
        "PR Size Mediano": round(float(pr_patterns["median_pr_size"]), 1) if pd.notna(pr_patterns["median_pr_size"]) else np.nan,
        "Itens Concluídos": int(len(done_df)),
        "Itens Ativos": int(len(active_df)),
        "Pessoas Ativas": active_people,
        "Deploys": int(pipeline_patterns["deploys"]),
    }
    return dimension_scores, overall_score, evidence


def _build_person_risk_table(scope_df, bitbucket_scope, pm_scope, start_ts, end_ts):
    if scope_df.empty:
        return pd.DataFrame()

    active_df = scope_df[_period_overlap_mask(scope_df, start_ts, end_ts)].copy()
    done_df = scope_df[pd.to_datetime(scope_df.get("DataDone"), errors="coerce").between(start_ts, end_ts, inclusive="both")].copy()
    started_df = scope_df[pd.to_datetime(scope_df.get("DataInProgress"), errors="coerce").between(start_ts, end_ts, inclusive="both")].copy()
    person_day = _build_person_day_concurrency(scope_df, start_ts, end_ts)

    commits = bitbucket_scope.get("commits", pd.DataFrame()).copy()
    if not commits.empty and "date" in commits.columns:
        commits["after_hours"] = (commits["date"].dt.hour < WORKDAY_START_HOUR) | (commits["date"].dt.hour >= WORKDAY_END_HOUR)
        commits["weekend"] = commits["date"].dt.weekday >= 5

    pm_cases = pm_scope.get("cases", pd.DataFrame()).copy()
    if not pm_cases.empty:
        pm_cases["rework_flag"] = pd.to_numeric(pm_cases.get("Rework Score"), errors="coerce").fillna(0) > 0

    rows = []
    people = sorted({p for p in scope_df["person_norm"].dropna().unique() if p})
    for person_norm in people:
        label = (
            active_df.loc[active_df["person_norm"] == person_norm, "Responsavel"].dropna().astype(str).head(1).tolist()
            or done_df.loc[done_df["person_norm"] == person_norm, "Responsavel"].dropna().astype(str).head(1).tolist()
        )
        person_name = label[0] if label else person_norm
        person_active = active_df[active_df["person_norm"] == person_norm]
        person_done = done_df[done_df["person_norm"] == person_norm]
        person_started = started_df[started_df["person_norm"] == person_norm]
        person_commits = commits[commits.get("person_norm", pd.Series("", index=commits.index)) == person_norm] if not commits.empty else pd.DataFrame()
        person_pm = pm_cases[pm_cases.get("person_norm", pd.Series("", index=pm_cases.index)) == person_norm] if not pm_cases.empty else pd.DataFrame()
        person_concurrency = person_day[person_day["person_norm"] == person_norm] if not person_day.empty else pd.DataFrame()

        after_hours_pct = float(person_commits["after_hours"].mean() * 100.0) if not person_commits.empty else np.nan
        weekend_pct = float(person_commits["weekend"].mean() * 100.0) if not person_commits.empty else np.nan
        concurrency_mean = float(person_concurrency["ConcurrentItems"].mean()) if not person_concurrency.empty else np.nan
        rework_pct = float(person_pm["rework_flag"].mean() * 100.0) if not person_pm.empty else np.nan
        lt_median = float(_safe_series(person_done, "LeadTime_Dias").median()) if not person_done.empty else np.nan
        failure_pct = float(
            person_done[person_done.get("Tipo", pd.Series("", index=person_done.index)).astype(str).str.contains("def", case=False, na=False)].shape[0]
            / person_done.shape[0] * 100.0
        ) if not person_done.empty else np.nan

        risk_score = _nanmean(
            [
                100.0 - _score_lower_better(after_hours_pct, 10.0, 35.0),
                100.0 - _score_lower_better(weekend_pct, 5.0, 20.0),
                100.0 - _score_lower_better(concurrency_mean, 1.5, 4.5),
                100.0 - _score_lower_better(rework_pct, 15.0, 35.0),
                100.0 - _score_lower_better(lt_median, 5.0, 20.0),
            ]
        )

        rows.append(
            {
                "Pessoa": person_name,
                "Itens Concluídos": int(len(person_done)),
                "Itens Iniciados": int(len(person_started)),
                "WIP Ativo": int(len(person_active)),
                "Lead Time Mediano": round(lt_median, 2) if pd.notna(lt_median) else np.nan,
                "Concorrência Média": round(concurrency_mean, 2) if pd.notna(concurrency_mean) else np.nan,
                "% After Hours": round(after_hours_pct, 1) if pd.notna(after_hours_pct) else np.nan,
                "% Weekend": round(weekend_pct, 1) if pd.notna(weekend_pct) else np.nan,
                "% Failure": round(failure_pct, 1) if pd.notna(failure_pct) else np.nan,
                "% Rework PM": round(rework_pct, 1) if pd.notna(rework_pct) else np.nan,
                "Commits": int(len(person_commits)),
                "SPAF Risk": round(float(risk_score), 1) if pd.notna(risk_score) else np.nan,
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(["SPAF Risk", "WIP Ativo", "Itens Concluídos"], ascending=[False, False, False], ignore_index=True)


def compute_spaf_dashboard_payload(context, start_date=None, end_date=None, selected_projects=None):
    fact = context["fact"]
    start_ts = pd.to_datetime(start_date or context["min_date"]).normalize()
    end_ts = pd.to_datetime(end_date or context["max_date"]).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)

    selected_projects = [p for p in (selected_projects or []) if str(p).strip()]
    scope_df = _filter_fact_scope(fact, start_ts, end_ts, selected_projects)
    bitbucket_scope = _filter_bitbucket_scope(context["bitbucket"], selected_projects, start_ts, end_ts)
    pm_scope = _filter_pm_scope(context["process_mining"], selected_projects, start_ts, end_ts)

    overall_dimensions, overall_score, overall_evidence = _compute_dimension_scores(scope_df, bitbucket_scope, pm_scope, start_ts, end_ts)

    project_rows = []
    scoped_projects = selected_projects or context["projects"]
    for project in scoped_projects:
        project_scope = _filter_fact_scope(fact, start_ts, end_ts, [project])
        if project_scope.empty:
            continue
        project_bitbucket = _filter_bitbucket_scope(context["bitbucket"], [project], start_ts, end_ts)
        project_pm = _filter_pm_scope(context["process_mining"], [project], start_ts, end_ts)
        dims, score, evidence = _compute_dimension_scores(project_scope, project_bitbucket, project_pm, start_ts, end_ts)
        row = {"Projeto": project, "SPAF Overall": round(score, 1) if pd.notna(score) else np.nan}
        for dim in SPAF_DIMENSIONS:
            row[dim] = round(float(dims.get(dim)), 1) if pd.notna(dims.get(dim)) else np.nan
        row.update(
            {
                "Itens Concluídos": evidence.get("Itens Concluídos"),
                "Pessoas Ativas": evidence.get("Pessoas Ativas"),
                "Lead Time Mediano (dias)": evidence.get("Lead Time Mediano (dias)"),
                "Pipeline Success (%)": evidence.get("Pipeline Success (%)"),
                "% Rework PM": evidence.get("% Rework PM"),
            }
        )
        project_rows.append(row)

    project_df = pd.DataFrame(project_rows).sort_values("SPAF Overall", ascending=False, na_position="last") if project_rows else pd.DataFrame()
    person_df = _build_person_risk_table(scope_df, bitbucket_scope, pm_scope, start_ts, end_ts)

    methodology_rows = []
    for dim in SPAF_DIMENSIONS:
        methodology_rows.append(
            {
                "Dimensão": dim,
                "Score": round(float(overall_dimensions.get(dim)), 1) if pd.notna(overall_dimensions.get(dim)) else np.nan,
                "Natureza": "proxy operacional" if dim in {"Intensity", "Human Sustainability", "Predictive"} else "métrica operacional",
            }
        )
    methodology_df = pd.DataFrame(methodology_rows)

    return {
        "start_date": start_ts.date().isoformat(),
        "end_date": end_ts.date().isoformat(),
        "overall_score": round(float(overall_score), 1) if pd.notna(overall_score) else np.nan,
        "overall_dimensions": overall_dimensions,
        "overall_evidence": overall_evidence,
        "project_df": project_df,
        "person_df": person_df,
        "methodology_df": methodology_df,
        "scope_counts": {
            "items": int(len(scope_df)),
            "projects": int(project_df["Projeto"].nunique()) if not project_df.empty else 0,
            "people": int(scope_df["person_norm"].replace("", np.nan).dropna().nunique()),
        },
    }
