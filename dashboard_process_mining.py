import base64
import os
import platform
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
WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 18
WORKDAY_DAILY_CAP_HOURS = 8.0


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


def is_execution_status(status_name: str) -> bool:
    s = str(status_name or "").strip().lower()
    return any(h in s for h in EXECUTION_STATUS_HINTS)


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
    return x


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
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "220px 1fr 1fr",
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
)
def render_pm(data, start_date, end_date, person):
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
        if "Responsavel" in pm_hours_people.columns:
            pm_hours_people = pm_hours_people[pm_hours_people["Responsavel"] == person]
        if "Responsavel" in pm_hours_status.columns:
            pm_hours_status = pm_hours_status[pm_hours_status["Responsavel"] == person]

    event_hours = add_business_hours_overlap(pm_events, start_ts=start_ts, end_ts=end_ts)
    exec_event_hours = pd.DataFrame()
    exec_by_person = pd.DataFrame()
    exec_by_status = pd.DataFrame()
    if not event_hours.empty and "To Status" in event_hours.columns:
        exec_event_hours = event_hours[event_hours["To Status"].map(is_execution_status)].copy()
    if not exec_event_hours.empty and "Author" in exec_event_hours.columns:
        exec_by_person = (
            exec_event_hours.assign(Responsavel=exec_event_hours["Author"].fillna("").replace("", "Sem Autor"))
            .groupby("Responsavel", dropna=False)
            .agg(
                HorasExecucaoPeriodo=("HorasNoPeriodo", "sum"),
                HorasExecucaoUteisPeriodo=("HorasUteisPeriodo", "sum"),
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
        exec_by_person["MediaHorasPorEvento"] = _safe_num(exec_by_person["MediaHorasPorEvento"]).fillna(0).round(2)
        exec_by_person["MediaHorasUteisPorEvento"] = _safe_num(exec_by_person["MediaHorasUteisPorEvento"]).fillna(0).round(2)
        exec_by_status = (
            exec_event_hours.assign(Responsavel=exec_event_hours["Author"].fillna("").replace("", "Sem Autor"))
            .groupby(["Responsavel", "To Status"], dropna=False)
            .agg(
                HorasExecucaoPeriodo=("HorasNoPeriodo", "sum"),
                HorasExecucaoUteisPeriodo=("HorasUteisPeriodo", "sum"),
                Eventos=("Issue Key", "count"),
                CardsUnicos=("Issue Key", "nunique"),
            )
            .reset_index()
            .rename(columns={"To Status": "Status"})
            .sort_values("HorasExecucaoPeriodo", ascending=False)
        )
        exec_by_status["HorasExecucaoPeriodo"] = _safe_num(exec_by_status["HorasExecucaoPeriodo"]).fillna(0).round(2)
        exec_by_status["HorasExecucaoUteisPeriodo"] = _safe_num(exec_by_status["HorasExecucaoUteisPeriodo"]).fillna(0).round(2)
    exec_total_h = float(_safe_num(exec_event_hours.get("HorasNoPeriodo", pd.Series(dtype=float))).fillna(0).sum()) if not exec_event_hours.empty else 0.0
    exec_mean_h_event = float(_safe_num(exec_event_hours.get("HorasNoPeriodo", pd.Series(dtype=float))).replace(0, np.nan).dropna().mean()) if not exec_event_hours.empty else float("nan")
    exec_useful_total_h = float(_safe_num(exec_event_hours.get("HorasUteisPeriodo", pd.Series(dtype=float))).fillna(0).sum()) if not exec_event_hours.empty else 0.0
    exec_useful_mean_h_event = float(_safe_num(exec_event_hours.get("HorasUteisPeriodo", pd.Series(dtype=float))).replace(0, np.nan).dropna().mean()) if not exec_event_hours.empty else float("nan")

    total_concluidos = int(pd.to_numeric(pm_people.get("Itens Concluidos", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not pm_people.empty else int(pm_cases["Issue Key"].nunique()) if "Issue Key" in pm_cases.columns else 0
    itens_retrabalho = int(pd.to_numeric(pm_people.get("Itens Com Retrabalho", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not pm_people.empty else int((pd.to_numeric(pm_cases.get("Rework Score", pd.Series(dtype=float)), errors="coerce").fillna(0) > 0).sum())
    taxa_retrabalho = (itens_retrabalho / total_concluidos * 100.0) if total_concluidos > 0 else 0.0
    conf_media = pd.to_numeric(pm_cases.get("Conformance Score", pd.Series(dtype=float)), errors="coerce").dropna()
    conf_media_val = float(conf_media.mean()) if not conf_media.empty else np.nan

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
        ],
        style={"display": "grid", "gridTemplateColumns": "repeat(8, minmax(180px, 1fr))", "gap": "10px", "marginBottom": "16px"},
    )

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
    horas_people_cols = [c for c in ["Responsavel", "HorasNoFluxo", "HorasMediasPorEvento", "Eventos", "CardsUnicos"] if c in pm_hours_people.columns]
    horas_status_cols = [c for c in ["Responsavel", "Status", "HorasNoFluxo", "Eventos", "CardsUnicos"] if c in pm_hours_status.columns]
    exec_people_cols = [c for c in ["Responsavel", "HorasExecucaoUteisPeriodo", "HorasExecucaoPeriodo", "MediaHorasUteisPorEvento", "MediaHorasPorEvento", "Eventos", "CardsUnicos"] if c in exec_by_person.columns]
    exec_status_cols = [c for c in ["Responsavel", "Status", "HorasExecucaoUteisPeriodo", "HorasExecucaoPeriodo", "Eventos", "CardsUnicos"] if c in exec_by_status.columns]

    model_cards = []
    model_titles = {
        "dfg": "DFG (pm4py)",
        "heuristics": "Heuristics Miner (pm4py)",
        "inductive_tree": "Inductive Miner - Process Tree (pm4py)",
        "petri": "Inductive Miner - Rede de Petri (pm4py)",
    }
    for key in ["dfg", "heuristics", "inductive_tree", "petri"]:
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

    return html.Div(
        [
            pm4py_banner if pm4py_banner else html.Div(),
            kpi_grid,
            html.H3("Visualizações de Process Mining", style={"marginTop": "6px"}),
            html.Div(
                model_cards if model_cards else [html.Div("Artefatos visuais pm4py (DFG / Heuristics / Inductive / Petri) ainda não encontrados neste relatório.")],
                style={"display": "flex", "gap": "12px", "flexWrap": "wrap", "marginBottom": "8px"},
            ),
            dcc.Graph(figure=fig_dfg_edges),
            dcc.Graph(figure=fig_transition_map),
            dcc.Graph(figure=fig_variants),
            html.Div(
                [
                    html.Div(dcc.Graph(figure=fig_conf_hist), style={"flex": "1 1 420px"}),
                    html.Div(dcc.Graph(figure=fig_lt_rework), style={"flex": "1 1 420px"}),
                ],
                style={"display": "flex", "gap": "10px", "flexWrap": "wrap"},
            ),
            dcc.Graph(figure=fig_event_vol),
            html.H3("Análises Operacionais", style={"marginTop": "6px"}),
            html.Div(
                "Filtro de data aplicado aos eventos do changelog por `History Created`. "
                "Horas de execução no período usam a interseção do intervalo do evento (`History Created` até `Next Timestamp`) com o período selecionado.",
                style={"color": "#555", "fontSize": "13px", "marginBottom": "8px"},
            ),
            html.Div(
                "Heurística de horas úteis: considera somente dias úteis, janela comercial e teto diário (aproximação de horas trabalhadas, não timesheet).",
                style={"color": "#555", "fontSize": "13px", "marginBottom": "8px"},
            ),
            dcc.Graph(figure=fig_exec_by_person),
            dcc.Graph(figure=fig_exec_by_status),
            dcc.Graph(figure=fig_horas_pessoa),
            dcc.Graph(figure=fig_horas_status),
            dcc.Graph(figure=fig_vazao),
            dcc.Graph(figure=fig_vazao_sem),
            dcc.Graph(figure=fig_retrabalho),
            dcc.Graph(figure=fig_tempo_status),
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
            html.H4("Metadados"),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in meta_cols],
                data=pm_meta[meta_cols].to_dict("records") if meta_cols else [],
                style_cell={"textAlign": "left", "padding": "6px", "whiteSpace": "normal"},
                style_header={"backgroundColor": "rgb(230,230,230)", "fontWeight": "bold"},
                page_size=10,
            ),
        ]
    )


if __name__ == "__main__":
    app.run(debug=True, port=8051)
