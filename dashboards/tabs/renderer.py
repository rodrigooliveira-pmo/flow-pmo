"""render_tab body extracted from dashboard_full.py — RF-034/RF-036."""
from __future__ import annotations

import sys
import os
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
try:
    from plotly.subplots import make_subplots
except ImportError:
    from plotly.tools import make_subplots

import dash
try:
    from dash import dcc, html, Input, Output, State, dash_table
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html
    from dash.dependencies import Input, Output, State
    import dash_table
from dash.exceptions import PreventUpdate

from dashboards.core import (
    _download_model_from_url,
    _download_portfolio_csv_from_url,
    _download_four_ps_kanban_csv_from_url,
    _download_bottleneck_csv_from_url,
    _download_process_mining_report_from_url,
    _download_downstream_items_csv_from_url,
    _download_capex_csv_from_url,
    _download_gmud_csv_from_url,
    _load_bottleneck_url_map,
    _load_bitbucket_csv_url_map,
    _download_bitbucket_csv_from_url,
    _load_downstream_url_map,
    _url_filename_matches_project_suffix,
    _url_filename_matches_project,
    _resolve_model_file,
    DATA_FOLDERS,
    DATA_FOLDER,
    PROCESS_MINING_ARTIFACT_FOLDER,
    MODEL_FILE,
    _iter_local_data_folders,
    _format_last_processed_load,
    LAST_PROCESSED_LOAD_LABEL,
    safe_read_sheet,
    load_model_data,
    resolve_service_class,
    canonicalize_highest_label,
    is_highest_alias,
    portfolio_type_to_demand_type,
    portfolio_project_team_aliases,
    portfolio_has_extra_onepage_tag,
    apply_portfolio_module_filters,
    process_fato_data,
    canonicalize_demand_type,
    normalize_project_filter_value,
    unique_sorted,
    done_time_eligible_mask,
    TYPE_SUPPORT,
    TYPE_ISSUES,
    TYPE_DEV,
    TYPE_OTHER,
    PORTFOLIO_EXTRA_ONEPAGE_TAG,
    PROJECT_FILTER_ALL_VALUE,
    ORIGINAL_JIRA_TYPE_FILTER_ALL_VALUE,
)

from dashboards.metrics.time_metrics import (
    time_metric_series,
    build_lead_time_comparable_scope,
    unique_item_keys,
    build_delivered_items_base,
    exact_empirical_percentile,
    exact_percentile_map,
    fit_weibull_linearized,
    describe_weibull_scale_cadence,
    exact_percentile_band_summary,
    add_statistical_lines,
    compute_process_capability_metrics,
    build_monthly_throughput_percentage_by_type,
    build_monthly_leadtime_sla_percentage_by_type,
)

from dashboards.metrics.efficiency_metrics import (
    build_waste_decomposition,
    build_scenario_simulation,
)
from dashboards.metrics.health_score import compute_health_score, compute_health_score_monthly
from dashboards.components.health_score_modal import render_health_score_panel

from dashboards.components.cards import (
    create_kpi_card,
    _portfolio_metric_card,
)

from dashboards.components.tables import (
    create_table,
    create_generic_datatable,
)

from dashboards.four_ps import build_four_ps_payload, render_four_ps_tab
from dashboards.pages.corporativo import layout_corporativo
from dashboards.components.error_boundary import error_boundary, callback_error_div

from shared.text_utils import normalize_text

from dashboards.people import (
    _load_people_config,
    _load_person_bu_map,
    _load_person_role_map,
    _load_person_alias_index,
    _load_person_seniority_index,
    _person_match_key,
    _person_email_key,
    _person_tokens_for_match,
    _normalize_person_name,
    _person_names_compatible,
    _canonical_person_name,
    _person_bu,
    _person_role,
    _normalize_seniority_bucket,
    _normalize_multiselect_value,
    _normalize_responsavel_filter_values,
    _format_responsavel_filter_label,
    _split_people_field,
    _project_team_bu,
    _project_team_seed_df,
    _ensure_dev_productivity_columns,
)


def render_tab(main_view, tab, start_date, end_date, projeto, tipo, tipo_original_jira, classe_servico, responsavel, leadtime_stages, etapa_fluxo=None, capacity_top_n=5, capacity_weekly_metric='score', portfolio_team=PROJECT_FILTER_ALL_VALUE, portfolio_quarter='ALL',
               pf_backlog_15=None, pf_backlog_30=None, pf_fresh_15=None, pf_fresh_30=None,
               pf_decision_statuses=None, pf_workflow_statuses=None, pf_sla_aging_json=None, pf_target_mix_json=None,
               criadores=None, date_filter_mode=None,
               estatistica_lsl=None, estatistica_usl=None,
               corp_periodicity='M', corp_groupby_product='False', corp_feature_types=None):
    _df = sys.modules.get('dashboard_full') or sys.modules['__main__']
    FILTER_DATE_CREATED_VALUE = _df.FILTER_DATE_CREATED_VALUE
    INTERNAL_SERVICE_TAB_VALUES = _df.INTERNAL_SERVICE_TAB_VALUES
    PATTERN_ACTIONS = _df.PATTERN_ACTIONS
    PATTERN_RULES = _df.PATTERN_RULES
    PORTFOLIO_COLOR_THRESHOLDS = _df.PORTFOLIO_COLOR_THRESHOLDS
    PORTFOLIO_PENDING_BUCKET_1 = _df.PORTFOLIO_PENDING_BUCKET_1
    PORTFOLIO_PENDING_BUCKET_2 = _df.PORTFOLIO_PENDING_BUCKET_2
    PORTFOLIO_PENDING_BUCKET_3 = _df.PORTFOLIO_PENDING_BUCKET_3
    PORTFOLIO_TAB_VALUE = _df.PORTFOLIO_TAB_VALUE
    PROJECT_BITBUCKET_PREFIX = _df.PROJECT_BITBUCKET_PREFIX
    THROUGHPUT_BREAKDOWN_PRODUCT_LABELS = _df.THROUGHPUT_BREAKDOWN_PRODUCT_LABELS
    THROUGHPUT_BREAKDOWN_PRODUCT_ORDER = _df.THROUGHPUT_BREAKDOWN_PRODUCT_ORDER
    WEEK_DATE_RANGE_FREQ = _df.WEEK_DATE_RANGE_FREQ
    _TYPE_CATEGORY_ORDER = _df._TYPE_CATEGORY_ORDER
    _TYPE_NORM_TO_CATEGORY = _df._TYPE_NORM_TO_CATEGORY
    _TYPE_SLA_DISPLAY_LABELS = _df._TYPE_SLA_DISPLAY_LABELS
    _build_custo_espera_section = _df._build_custo_espera_section
    _build_custo_estimado_vs_real_section = _df._build_custo_estimado_vs_real_section
    _build_custo_pm_calibrado_section = _df._build_custo_pm_calibrado_section
    _build_custo_por_atividade_section = _df._build_custo_por_atividade_section
    _build_custo_por_fase_section = _df._build_custo_por_fase_section
    _build_custo_retrabalho_section = _df._build_custo_retrabalho_section
    _build_dev_item_person_map = _df._build_dev_item_person_map
    _canonical_gmud_service_team = _df._canonical_gmud_service_team
    _cfd_stage_color = _df._cfd_stage_color
    _coerce_story_points_value = _df._coerce_story_points_value
    _compute_dev_aging_rates = _df._compute_dev_aging_rates
    _compute_ied = _df._compute_ied
    _compute_monthly_ecr_series = _df._compute_monthly_ecr_series
    _compute_monthly_ied_series = _df._compute_monthly_ied_series
    _detect_stage_date_columns = _df._detect_stage_date_columns
    _extract_work_item_keys_from_bitbucket_logs = _df._extract_work_item_keys_from_bitbucket_logs
    _format_month_label_pt_br = _df._format_month_label_pt_br
    _gmud_scope_mask = _df._gmud_scope_mask
    _load_bitbucket_prefix_map = _df._load_bitbucket_prefix_map
    _load_four_ps_kanban_data = _df._load_four_ps_kanban_data
    _pm_filter_real_worklog_df = _df._pm_filter_real_worklog_df
    _pm_has_real_worklog_data = _df._pm_has_real_worklog_data
    _pm_product_color = _df._pm_product_color
    _pm_product_label = _df._pm_product_label
    _recompute_itens_entregues_from_dev_flow = _df._recompute_itens_entregues_from_dev_flow
    _resolve_dev_person_series = _df._resolve_dev_person_series
    _resolve_type_sla_config = _df._resolve_type_sla_config
    _story_points_band = _df._story_points_band
    _unified_sp_bucket = _df._unified_sp_bucket
    _work_item_age_bucket = _df._work_item_age_bucket
    _work_item_age_health_label = _df._work_item_age_health_label
    apply_selected_commitment_metric = _df.apply_selected_commitment_metric
    apply_selected_lead_time_metric = _df.apply_selected_lead_time_metric
    build_bitbucket_contributor_section = _df.build_bitbucket_contributor_section
    build_bitbucket_temporal_section = _df.build_bitbucket_temporal_section
    build_cfd_dataframe = _df.build_cfd_dataframe
    build_cfd_summary_payload = _df.build_cfd_summary_payload
    build_date_range_mask = _df.build_date_range_mask
    build_dev_productivity_metrics = _df.build_dev_productivity_metrics
    build_expedite_governance_view = _df.build_expedite_governance_view
    build_generated_portfolio_financial_view = _df.build_generated_portfolio_financial_view
    build_leadtime_stage_selection_summary = _df.build_leadtime_stage_selection_summary
    build_live_wip_snapshot = _df.build_live_wip_snapshot
    build_monthly_product_original_type_breakdown = _df.build_monthly_product_original_type_breakdown
    build_monthly_product_throughput_breakdown = _df.build_monthly_product_throughput_breakdown
    build_period_evolution_sustainability_breakdown = _df.build_period_evolution_sustainability_breakdown
    build_pm_commits_vs_jira_report = _df.build_pm_commits_vs_jira_report
    build_pm_dev_return_report = _df.build_pm_dev_return_report
    build_pm_portfolio_capex_view = _df.build_pm_portfolio_capex_view
    build_portfolio_cross_delivery_integration = _df.build_portfolio_cross_delivery_integration
    build_service_bucket_index = _df.build_service_bucket_index
    build_service_lead_time_breakdown = _df.build_service_lead_time_breakdown
    build_service_wip_breakdown = _df.build_service_wip_breakdown
    build_throughput_avg_cost_series = _df.build_throughput_avg_cost_series
    build_throughput_series = _df.build_throughput_series
    build_variability_alerts_view = _df.build_variability_alerts_view
    build_weekly_flow_checklist_and_diagnosis = _df.build_weekly_flow_checklist_and_diagnosis
    calculate_flow_efficiency = _df.calculate_flow_efficiency
    calculate_mm1_metrics = _df.calculate_mm1_metrics
    classify_urgency_label = _df.classify_urgency_label
    compute_bitbucket_contributor_metrics = _df.compute_bitbucket_contributor_metrics
    compute_current_stage_map = _df.compute_current_stage_map
    compute_flow_bottlenecks = _df.compute_flow_bottlenecks
    compute_pipeline_success_rate = _df.compute_pipeline_success_rate
    compute_pm_bottleneck_contribution = _df.compute_pm_bottleneck_contribution
    compute_pm_dev_flow_metrics = _df.compute_pm_dev_flow_metrics
    compute_pm_dev_metrics = _df.compute_pm_dev_metrics
    compute_portfolio_snapshot = _df.compute_portfolio_snapshot
    compute_weekly_service_metrics = _df.compute_weekly_service_metrics
    create_cfd_figure = _df.create_cfd_figure
    create_cfd_summary_panel = _df.create_cfd_summary_panel
    detect_systemic_patterns = _df.detect_systemic_patterns
    fato = _df.fato
    filter_df = _df.filter_df
    filter_items_by_current_stage = _df.filter_items_by_current_stage
    format_currency_br = _df.format_currency_br
    format_original_jira_type_filter_label = _df.format_original_jira_type_filter_label
    get_downstream_done_stage_column = _df.get_downstream_done_stage_column
    get_gmud_snapshot = _df.get_gmud_snapshot
    get_portfolio_snapshot = _df.get_portfolio_snapshot
    get_type_sla_days = _df.get_type_sla_days
    get_type_sla_display = _df.get_type_sla_display
    infer_service_bucket_config = _df.infer_service_bucket_config
    load_project_bitbucket_logs = _df.load_project_bitbucket_logs
    load_project_bottlenecks_from_csv = _df.load_project_bottlenecks_from_csv
    load_project_bottlenecks_from_model = _df.load_project_bottlenecks_from_model
    load_project_downstream_items_csv = _df.load_project_downstream_items_csv
    load_project_pm_case_df = _df.load_project_pm_case_df
    load_project_pm_sheet = _df.load_project_pm_sheet
    load_w1nner_process_mining_report = _df.load_w1nner_process_mining_report
    portfolio_is_highest_priority = _df.portfolio_is_highest_priority
    portfolio_table_component = _df.portfolio_table_component
    render_portfolio_roadmap_full_epics_view = _df.render_portfolio_roadmap_full_epics_view
    resolve_creation_date_series = _df.resolve_creation_date_series
    resolve_filter_date_series = _df.resolve_filter_date_series
    resolve_project_sla_days = _df.resolve_project_sla_days
    weekly_bucket_start = _df.weekly_bucket_start

    if main_view in (None, 'home'):
        return html.Div(
            'Selecione "Portfólio" ou "Serviços (Value Stream)" na tela principal para continuar.',
            style={
                'textAlign': 'center',
                'color': '#666',
                'padding': '18px',
                'border': '1px dashed #d1d5db',
                'borderRadius': '10px',
                'maxWidth': '720px',
                'margin': '0 auto'
            }
        )

    if main_view == 'portfolio':
        tab = PORTFOLIO_TAB_VALUE
    elif tab is None:
        tab = 'tab-performance'
    elif tab not in INTERNAL_SERVICE_TAB_VALUES:
        return html.Div(
            [
                html.H4('Aba inválida no modo Serviços', style={'textAlign': 'center', 'color': '#b22222'}),
                html.P(
                    f"Valor recebido: {tab!r}. Selecione novamente uma aba no topo.",
                    style={'textAlign': 'center', 'color': '#555'}
                ),
            ],
            style={'padding': '16px', 'border': '1px dashed #d1d5db', 'borderRadius': '10px', 'maxWidth': '780px', 'margin': '12px auto'}
        )

    projeto = normalize_project_filter_value(projeto)
    portfolio_project = normalize_project_filter_value(portfolio_team)
    use_creation_date = FILTER_DATE_CREATED_VALUE in (date_filter_mode or [])
    df = filter_df(
        fato,
        start_date,
        end_date,
        projeto,
        tipo,
        classe_servico,
        responsavel,
        criadores=criadores,
        use_creation_date=use_creation_date,
        tipo_original=tipo_original_jira,
    )
    df, leadtime_meta = apply_selected_lead_time_metric(df, projeto, leadtime_stages)
    leadtime_selection_summary = build_leadtime_stage_selection_summary(projeto, leadtime_stages)

    # Padrão de cores para os tipos de demanda
    color_map = {
        TYPE_DEV: 'green',           # Demanda de Valor
        TYPE_ISSUES: 'red',          # Demanda de Falha
        TYPE_SUPPORT: 'orange',      # Suporte
        TYPE_OTHER: 'lightgray'      # Outros tipos
    }

    if tab == 'tab-performance':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        df_scope = df.copy()
        df_wip_base = filter_df(
            fato,
            None,
            None,
            projeto,
            tipo,
            classe_servico,
            responsavel,
            criadores=criadores,
            use_creation_date=use_creation_date,
            apply_date=False,
            tipo_original=tipo_original_jira,
        )
        if df_scope.empty and df_wip_base.empty:
            return html.Div('Sem dados para os filtros selecionados.')

        weeks = pd.date_range(start=start_ts, end=end_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal.')

        wip_stage_map = compute_current_stage_map(projeto) if projeto and etapa_fluxo else {}
        metric_names, rows = compute_weekly_service_metrics(
            df_scope, weeks,
            lead_time_col='LeadTime_Selected_Dias',
            projeto=projeto,
            wip_stage_map=wip_stage_map if etapa_fluxo else None,
            wip_stage_filter=etapa_fluxo or None,
            wip_base_df=df_wip_base,
        )
        week_labels = [str(weeks[i].date()) for i in range(len(weeks) - 1)]

        table_data = []
        for m in metric_names:
            row = {'Métrica': m}
            for wl in week_labels:
                row[wl] = rows[m].get(wl, '—')
            table_data.append(row)

        columns = [{'name': 'Métrica', 'id': 'Métrica'}] + [{'name': wl, 'id': wl} for wl in week_labels]

        style_data_conditional = [
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
            {'if': {'filter_query': '{Métrica} = "% Demanda de Valor"'}, 'color': 'green', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Métrica} = "% Demanda de Falha"'}, 'color': 'red', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Métrica} contains "—"'}, 'color': '#aaa'},
        ]
        for m in ['Qtd. Itens Descartados', 'DDP']:
            style_data_conditional.append({
                'if': {'filter_query': f'{{Métrica}} = "{m}"'},
                'backgroundColor': 'rgb(245, 245, 245)', 'color': '#bbb', 'fontStyle': 'italic'
            })

        titulo = f"Serviço e SLA: {projeto}" if projeto else "Serviço e SLA"
        period_label = f"{start_ts.strftime('%d/%m')} a {end_ts.strftime('%d/%m')}"
        bucket_freq, bucket_label, bucket_adj = infer_service_bucket_config(start_ts, end_ts)
        sla_days = resolve_project_sla_days(projeto, default=8.0)

        data_in_progress = pd.to_datetime(df_scope['DataInProgress'], errors='coerce') if 'DataInProgress' in df_scope.columns else pd.Series(pd.NaT, index=df_scope.index)
        data_done = pd.to_datetime(df_scope['DataDone'], errors='coerce') if 'DataDone' in df_scope.columns else pd.Series(pd.NaT, index=df_scope.index)

        mask_started_until_end = data_in_progress.isna() | (data_in_progress <= end_ts)
        mask_not_finished_before_start = data_done.isna() | (data_done >= start_ts)
        scope_mask = mask_started_until_end & mask_not_finished_before_start
        df_scope_period = df_scope[scope_mask].copy()

        done_period_mask = (data_done >= start_ts) & (data_done <= end_ts)
        df_done_period = df_scope[done_period_mask].copy()
        df_done_period_eligible = build_delivered_items_base(df_done_period, lead_time_col='LeadTime_Selected_Dias')
        df_done_period_eligible = df_done_period_eligible.copy()
        if not df_done_period_eligible.empty:
            df_done_period_eligible['ClassificacaoUrgencia'] = df_done_period_eligible.apply(classify_urgency_label, axis=1)
            if 'TipoNorm' not in df_done_period_eligible.columns and 'Tipo' in df_done_period_eligible.columns:
                df_done_period_eligible['TipoNorm'] = df_done_period_eligible['Tipo'].apply(normalize_text)
            _tipo_norm_col = df_done_period_eligible['TipoNorm'] if 'TipoNorm' in df_done_period_eligible.columns else pd.Series('', index=df_done_period_eligible.index)
            # WorkItemSubType é mais granular (Feature/História/Tarefa) que Tipo (Desenvolvimento/Defeitos).
            # Prefere WorkItemSubType para o lookup de SLA quando disponível.
            _sla_lookup_col = (
                df_done_period_eligible['WorkItemSubType'].fillna('').astype(str).map(normalize_text)
                if 'WorkItemSubType' in df_done_period_eligible.columns
                else _tipo_norm_col
            )
            df_done_period_eligible['SLARef_Dias'] = _sla_lookup_col.apply(get_type_sla_days)

        active_wip = build_live_wip_snapshot(
            df_wip_base,
            end_ts,
            projeto=projeto,
            selected_stages=etapa_fluxo,
            stage_map=wip_stage_map if etapa_fluxo else None,
        )
        if not active_wip.empty:
            active_wip['ClassificacaoUrgencia'] = active_wip.apply(classify_urgency_label, axis=1)
        elif 'WIPAge' not in active_wip.columns:
            active_wip['WIPAge'] = pd.Series(dtype=float)

        lead_series = time_metric_series(df_done_period_eligible, 'LeadTime_Selected_Dias', non_negative=True)
        lead_avg = float(lead_series.mean()) if not lead_series.empty else np.nan
        lead_p85 = exact_empirical_percentile(lead_series, 0.85) if not lead_series.empty else np.nan
        if not df_done_period_eligible.empty and 'SLARef_Dias' in df_done_period_eligible.columns:
            _elt = pd.to_numeric(df_done_period_eligible.get('LeadTime_Selected_Dias'), errors='coerce')
            _esla = pd.to_numeric(df_done_period_eligible.get('SLARef_Dias'), errors='coerce')
            _vmask = _elt.notna() & (_elt >= 0) & _esla.notna()
            sla_share = float((_elt[_vmask] <= _esla[_vmask]).mean() * 100.0) if _vmask.sum() > 0 else np.nan
        else:
            sla_share = float((lead_series <= sla_days).mean() * 100.0) if not lead_series.empty and sla_days > 0 else np.nan

        # % dentro do SLA por categoria de tipo
        sla_share_by_type = []
        _has_subtype = 'WorkItemSubType' in df_done_period_eligible.columns
        if not df_done_period_eligible.empty and (_has_subtype or 'TipoNorm' in df_done_period_eligible.columns):
            _elt_all = pd.to_numeric(df_done_period_eligible.get('LeadTime_Selected_Dias'), errors='coerce')
            _esla_all = pd.to_numeric(df_done_period_eligible.get('SLARef_Dias', pd.Series(dtype=float)), errors='coerce')
            # WorkItemSubType (ex: Feature, História, Tarefa) é mais granular que TipoNorm (Desenvolvimento, Defeitos).
            if _has_subtype:
                _tnorm = df_done_period_eligible['WorkItemSubType'].fillna('').astype(str).map(normalize_text)
            else:
                _tnorm = df_done_period_eligible['TipoNorm'].fillna('').astype(str).str.strip().str.lower()
            for _cat in _TYPE_CATEGORY_ORDER:
                _label = _TYPE_SLA_DISPLAY_LABELS[_cat]
                _cat_norms = {k for k, v in _TYPE_NORM_TO_CATEGORY.items() if v == _cat}
                _cmask = _tnorm.isin(_cat_norms) & _elt_all.notna() & (_elt_all >= 0) & _esla_all.notna()
                if _cmask.sum() > 0:
                    _pct = float((_elt_all[_cmask] <= _esla_all[_cmask]).mean() * 100.0)
                    sla_share_by_type.append((_label, _pct, int(_cmask.sum())))
                else:
                    sla_share_by_type.append((_label, None, 0))
        else:
            sla_share_by_type = [(_TYPE_SLA_DISPLAY_LABELS[k], None, 0) for k in _TYPE_CATEGORY_ORDER]

        # Due Date Performance: % entregues dentro do DueDate do item (DataDone ≤ DueDate).
        _ddp_due_dt = pd.to_datetime(df_done_period_eligible.get('DueDate'), errors='coerce') if not df_done_period_eligible.empty and 'DueDate' in df_done_period_eligible.columns else pd.Series(pd.NaT, index=df_done_period_eligible.index if not df_done_period_eligible.empty else [])
        _ddp_done_dt = pd.to_datetime(df_done_period_eligible.get('DataDone'), errors='coerce') if not df_done_period_eligible.empty and 'DataDone' in df_done_period_eligible.columns else pd.Series(pd.NaT, index=df_done_period_eligible.index if not df_done_period_eligible.empty else [])
        _ddp_has_due = _ddp_due_dt.notna() if not _ddp_due_dt.empty else pd.Series(dtype=bool)
        _ddp_on_time = (_ddp_has_due & (_ddp_done_dt.dt.normalize() <= _ddp_due_dt.dt.normalize())) if not _ddp_has_due.empty else pd.Series(dtype=bool)
        ddp_with_due = int(_ddp_has_due.sum()) if not _ddp_has_due.empty else 0
        ddp_on_time_count = int(_ddp_on_time.sum()) if not _ddp_on_time.empty else 0
        ddp_late_count = ddp_with_due - ddp_on_time_count
        ddp_no_target_count = int(len(df_done_period_eligible)) - ddp_with_due
        ddp_pct = float(ddp_on_time_count / ddp_with_due * 100) if ddp_with_due > 0 else np.nan

        lt_weibull = fit_weibull_linearized(lead_series) if not lead_series.empty else None
        weibull_shape = float(lt_weibull['shape']) if lt_weibull else np.nan
        weibull_lambda = float(lt_weibull['lambda']) if lt_weibull else np.nan
        weibull_cadence = describe_weibull_scale_cadence(weibull_lambda) if lt_weibull else None
        lead_start_col = 'LeadStart_Selected' if 'LeadStart_Selected' in df_scope.columns else 'DataInProgress'
        selected_start_series = pd.to_datetime(df_scope.get(lead_start_col), errors='coerce')
        arrivals_period = df_scope[
            (selected_start_series >= start_ts) &
            (selected_start_series <= end_ts)
        ].copy()
        pressure_rho, _ = calculate_flow_efficiency(len(arrivals_period), len(df_done_period_eligible))

        throughput_bucket_df = df_done_period_eligible.copy()
        throughput_p15 = np.nan
        throughput_avg = np.nan
        throughput_p85 = np.nan
        if not throughput_bucket_df.empty:
            throughput_bucket_df['DataDone'] = pd.to_datetime(throughput_bucket_df['DataDone'], errors='coerce')
            throughput_bucket_df = throughput_bucket_df.dropna(subset=['DataDone'])
            if not throughput_bucket_df.empty:
                if bucket_freq == 'MS':
                    throughput_bucket_df['Bucket'] = throughput_bucket_df['DataDone'].dt.to_period('M').dt.start_time
                else:
                    throughput_bucket_df['Bucket'] = weekly_bucket_start(throughput_bucket_df['DataDone'])
                bucket_range = build_service_bucket_index(start_ts, end_ts, bucket_freq)
                bucket_counts = throughput_bucket_df.groupby('Bucket').size().reindex(bucket_range, fill_value=0)
                if not bucket_counts.empty:
                    throughput_p15 = float(exact_empirical_percentile(bucket_counts, 0.15))
                    throughput_avg = float(bucket_counts.mean())
                    throughput_p85 = float(exact_empirical_percentile(bucket_counts, 0.85))

        wip_count = int(len(active_wip))
        wip_age_series = pd.to_numeric(active_wip.get('WIPAge', pd.Series(dtype=float)), errors='coerce').dropna()
        wip_age_avg = float(wip_age_series.mean()) if not wip_age_series.empty else np.nan
        wip_age_p85 = float(exact_empirical_percentile(wip_age_series, 0.85)) if not wip_age_series.empty else np.nan
        oldest_wip = float(wip_age_series.max()) if not wip_age_series.empty else np.nan

        lead_by_type = build_service_lead_time_breakdown(df_done_period_eligible, 'TipoDemanda', 'Tipo de Demanda', sla_days=sla_days, sla_col='SLARef_Dias' if 'SLARef_Dias' in df_done_period_eligible.columns else None)
        lead_by_urgency = build_service_lead_time_breakdown(df_done_period_eligible, 'ClassificacaoUrgencia', 'Urgência', sla_days=sla_days)
        tp_by_type = build_throughput_series(df_done_period_eligible, 'TipoDemanda', 'Tipo de Demanda', temporal=True, start_ts=start_ts, end_ts=end_ts, bucket_freq=bucket_freq)
        tp_by_urgency = build_throughput_series(df_done_period_eligible, 'ClassificacaoUrgencia', 'Urgência', temporal=True, start_ts=start_ts, end_ts=end_ts, bucket_freq=bucket_freq)
        wip_by_type = build_service_wip_breakdown(active_wip, end_ts, 'TipoDemanda', 'Tipo de Demanda')
        wip_by_urgency = build_service_wip_breakdown(active_wip, end_ts, 'ClassificacaoUrgencia', 'Urgência')
        
        monthly_tp_pct_by_type = build_monthly_throughput_percentage_by_type(df_done_period_eligible, 'TipoDemanda', 'Tipo de Demanda')
        monthly_lt_sla_pct_by_type = build_monthly_leadtime_sla_percentage_by_type(
            df_done_period_eligible, 
            'TipoDemanda', 
            'Tipo de Demanda', 
            sla_days=sla_days, 
            sla_col='SLARef_Dias' if 'SLARef_Dias' in df_done_period_eligible.columns else None
        )

        def service_table(title, df_table, empty_message, table_id):
            if df_table is None or df_table.empty:
                body = html.P(empty_message, style={'color': '#64748b', 'margin': 0})
            else:
                body = dash_table.DataTable(
                    id=table_id,
                    columns=[{"name": c, "id": c} for c in df_table.columns],
                    data=df_table.to_dict('records'),
                    style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
                    style_header={'backgroundColor': '#e2e8f0', 'fontWeight': 'bold'},
                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8fafc'}],
                    style_table={'overflowX': 'auto'},
                )
            return html.Div([
                html.H4(title, style={'marginTop': '0', 'marginBottom': '10px'}),
                body,
            ], style={'backgroundColor': '#ffffff', 'border': '1px solid #e2e8f0', 'borderRadius': '10px', 'padding': '14px'})

        def service_card(label, value, subtitle=''):
            return html.Div([
                html.Div(label, style={'fontSize': '12px', 'fontWeight': '700', 'textTransform': 'uppercase', 'letterSpacing': '0.4px', 'color': '#475569'}),
                html.Div(value, style={'fontSize': '30px', 'fontWeight': '800', 'lineHeight': '1.1', 'color': '#0f172a', 'marginTop': '6px'}),
                html.Div(subtitle, style={'fontSize': '12px', 'color': '#64748b', 'marginTop': '6px'}),
            ], style={'backgroundColor': '#f8fafc', 'border': '1px solid #dbeafe', 'borderRadius': '10px', 'padding': '14px', 'minHeight': '112px'})

        sla_ref_card = html.Div([
            html.Div('SLA de referência por tipo', style={'fontSize': '12px', 'fontWeight': '700', 'textTransform': 'uppercase', 'letterSpacing': '0.4px', 'color': '#475569', 'marginBottom': '8px'}),
            html.Div([
                html.Div([
                    html.Span(label, style={'fontSize': '11px', 'color': '#64748b'}),
                    html.Span(f'{days}d', style={'fontSize': '13px', 'fontWeight': '800', 'color': '#0f172a', 'marginLeft': '6px'}),
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '3px 0', 'borderBottom': '1px solid #e2e8f0'})
                for label, days in get_type_sla_display()
            ]),
        ], style={'backgroundColor': '#f8fafc', 'border': '1px solid #dbeafe', 'borderRadius': '10px', 'padding': '14px', 'minHeight': '112px'})

        summary_cards = html.Div([
            sla_ref_card,
            service_card('Lead Time', f"{lead_avg:.1f} / {lead_p85:.1f}" if pd.notna(lead_avg) and pd.notna(lead_p85) else '—', 'médio / P85 do período'),
            service_card(
                'Cadência avaliada',
                weibull_cadence['label'] if weibull_cadence else '—',
                f"Weibull k={weibull_shape:.4f} | λ={weibull_lambda:.4f}d" if weibull_cadence else 'Requer amostra suficiente de lead time'
            ),
            service_card(
                f'Vazão {bucket_adj} (P15/Média/P85)',
                f"{throughput_p15:.1f} / {throughput_avg:.1f} / {throughput_p85:.1f}" if pd.notna(throughput_p15) and pd.notna(throughput_avg) and pd.notna(throughput_p85) else '—',
                f'Leitura: P15 / média / P85 por {bucket_label.lower()}'
            ),
            service_card(
                'Pressão (ρ)',
                f"{pressure_rho:.2f}" if pd.notna(pressure_rho) else '—',
                'chegada / vazão no período'
            ),
            service_card('Itens entregues', f"{len(df_done_period_eligible)}", period_label),
            service_card('WIP atual', f'{wip_count}', f"age médio {wip_age_avg:.1f}d" if pd.notna(wip_age_avg) else 'sem aging disponível'),
            html.Div([
                html.Div('% dentro do SLA', style={'fontSize': '12px', 'fontWeight': '700', 'textTransform': 'uppercase', 'letterSpacing': '0.4px', 'color': '#475569', 'marginBottom': '6px'}),
                html.Div(
                    f"{sla_share:.1f}%" if pd.notna(sla_share) else '—',
                    style={'fontSize': '22px', 'fontWeight': '800', 'color': '#0f172a', 'lineHeight': '1.1', 'marginBottom': '6px'}
                ),
                html.Div([
                    html.Div([
                        html.Span(label, style={'fontSize': '10px', 'color': '#64748b'}),
                        html.Span(
                            f"{pct:.0f}%" if pct is not None else '—',
                            style={'fontSize': '11px', 'fontWeight': '700',
                                   'color': '#16a34a' if pct is not None and pct >= 70 else ('#dc2626' if pct is not None and pct < 40 else '#d97706'),
                                   'marginLeft': '4px'}
                        ),
                        html.Span(f" ({n})" if n > 0 else '', style={'fontSize': '10px', 'color': '#94a3b8'}),
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '2px 0', 'borderBottom': '1px solid #e2e8f0'})
                    for label, pct, n in sla_share_by_type
                ]),
            ], style={'backgroundColor': '#f8fafc', 'border': '1px solid #dbeafe', 'borderRadius': '10px', 'padding': '14px', 'minHeight': '112px'}),
            html.Div([
                html.Div('Due Date Performance', style={'fontSize': '12px', 'fontWeight': '700', 'textTransform': 'uppercase', 'letterSpacing': '0.4px', 'color': '#475569', 'marginBottom': '6px'}),
                html.Div(
                    f"{ddp_pct:.1f}%" if pd.notna(ddp_pct) else '—',
                    style={'fontSize': '22px', 'fontWeight': '800',
                           'color': '#16a34a' if pd.notna(ddp_pct) and ddp_pct >= 80 else ('#dc2626' if pd.notna(ddp_pct) and ddp_pct < 50 else '#d97706'),
                           'lineHeight': '1.1', 'marginBottom': '4px'}
                ),
                html.Div(
                    f"{ddp_with_due} com target date" if ddp_with_due > 0 else 'sem DueDate no período',
                    style={'fontSize': '10px', 'color': '#64748b', 'marginBottom': '4px'}
                ),
                html.Div([
                    html.Div([
                        html.Span('No prazo', style={'fontSize': '10px', 'color': '#64748b'}),
                        html.Span(str(ddp_on_time_count), style={'fontSize': '11px', 'fontWeight': '700', 'color': '#16a34a', 'marginLeft': '4px'}),
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'padding': '2px 0', 'borderBottom': '1px solid #e2e8f0'}),
                    html.Div([
                        html.Span('Atrasado', style={'fontSize': '10px', 'color': '#64748b'}),
                        html.Span(str(ddp_late_count), style={'fontSize': '11px', 'fontWeight': '700', 'color': '#dc2626' if ddp_late_count > 0 else '#94a3b8', 'marginLeft': '4px'}),
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'padding': '2px 0', 'borderBottom': '1px solid #e2e8f0'}),
                    html.Div([
                        html.Span('Sem target', style={'fontSize': '10px', 'color': '#64748b'}),
                        html.Span(str(ddp_no_target_count), style={'fontSize': '11px', 'fontWeight': '700', 'color': '#94a3b8', 'marginLeft': '4px'}),
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'padding': '2px 0'}),
                ]),
            ], style={'backgroundColor': '#f8fafc', 'border': '1px solid #dbeafe', 'borderRadius': '10px', 'padding': '14px', 'minHeight': '112px'}),
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(180px, 1fr))', 'gap': '10px', 'marginTop': '12px', 'marginBottom': '14px'})

        executive_findings = []
        if pd.notna(lead_p85):
            _sla_cfg = _resolve_type_sla_config()
            executive_findings.append(
                f"Lead Time P85 em {lead_p85:.1f}d no período "
                f"(SLA: Bug/Suporte {int(_sla_cfg['bug'])}d · Histórias {int(_sla_cfg['historia'])}d · "
                f"Features {int(_sla_cfg['feature'])}d · Épicos {int(_sla_cfg['epico'])}d)."
            )
        else:
            executive_findings.append('Lead Time sem base suficiente para leitura executiva no período.')

        if pd.notna(sla_share):
            executive_findings.append(f"{sla_share:.1f}% das entregas ficaram dentro do SLA do seu tipo no recorte.")
        else:
            executive_findings.append('Sem amostra suficiente para medir aderência ao SLA no recorte.')

        if pd.notna(ddp_pct):
            executive_findings.append(
                f"Due Date Performance: {ddp_pct:.1f}% dos {ddp_with_due} itens com DueDate foram entregues no prazo "
                f"({ddp_on_time_count} no prazo · {ddp_late_count} atrasados · {ddp_no_target_count} sem target)."
            )
        elif ddp_with_due == 0:
            executive_findings.append('Due Date Performance: nenhum item entregue no período possui DueDate preenchido.')

        if lt_weibull and weibull_cadence:
            executive_findings.append(
                f"Weibull do lead time em k={weibull_shape:.4f} e λ={weibull_lambda:.4f}d; "
                f"a cadência avaliada fica {weibull_cadence['label']}."
            )
        else:
            executive_findings.append('Weibull do lead time indisponível por amostra insuficiente no recorte.')

        if pd.notna(pressure_rho):
            if pressure_rho >= 1.0:
                executive_findings.append(f"Chegada acima da capacidade de entrega: pressão em ρ={pressure_rho:.2f}.")
            elif pressure_rho >= 0.85:
                executive_findings.append(f"Serviço operando pressionado: ρ={pressure_rho:.2f}, com pouca folga de vazão.")
            else:
                executive_findings.append(f"Pressão de fluxo sob controle: ρ={pressure_rho:.2f}.")
        else:
            executive_findings.append('Pressão de fluxo indisponível por falta de throughput elegível no período.')

        if pd.notna(wip_age_avg):
            if wip_age_avg > sla_days:
                executive_findings.append(f"WIP envelhecido: age médio em {wip_age_avg:.1f}d, acima do SLA de referência.")
            else:
                executive_findings.append(f"WIP atual em {wip_count} itens, com age médio de {wip_age_avg:.1f}d.")
        else:
            executive_findings.append(f"WIP atual em {wip_count} itens, sem aging suficiente para leitura.")

        highlights = html.Div([
            html.Strong('Resumo executivo do serviço'),
            html.Ul([
                *[html.Li(text) for text in executive_findings],
                html.Li(f"Vazão {bucket_adj}: P15 {throughput_p15:.1f}, média {throughput_avg:.1f} e P85 {throughput_p85:.1f} por {bucket_label.lower()}." if pd.notna(throughput_p15) and pd.notna(throughput_avg) and pd.notna(throughput_p85) else f'Vazão sem base suficiente por {bucket_label.lower()}.'),
                html.Li(f"WIP atual: {wip_count} itens | age médio {wip_age_avg:.1f}d | P85 {wip_age_p85:.1f}d | mais antigo {oldest_wip:.1f}d." if pd.notna(wip_age_avg) and pd.notna(wip_age_p85) and pd.notna(oldest_wip) else f'WIP atual: {wip_count} itens.'),
            ], style={'marginTop': '8px', 'marginBottom': '0', 'paddingLeft': '20px'}),
        ], style={'backgroundColor': '#fff7ed', 'border': '1px solid #fed7aa', 'borderRadius': '10px', 'padding': '12px', 'marginBottom': '14px'})

        fig_lt_type = go.Figure()
        if not lead_by_type.empty:
            fig_lt_type = px.bar(
                lead_by_type,
                x='Tipo de Demanda',
                y='Lead P85',
                hover_data=['Lead Médio', '% SLA', 'Itens'],
                title='Lead Time P85 por Tipo de Demanda',
                labels={'Lead P85': 'Lead Time P85 (dias)'},
                color='Lead P85',
                color_continuous_scale='OrRd',
            )
            fig_lt_type.add_hline(y=sla_days, line_dash='dash', line_color='royalblue')
            fig_lt_type.update_layout(height=360, coloraxis_showscale=False)

        fig_tp_urgency = go.Figure()
        if not tp_by_urgency.empty:
            fig_tp_urgency = px.bar(
                tp_by_urgency,
                x='Urgência',
                y='P85',
                hover_data=['Média/Bucket', 'Itens Entregues', 'Máx Bucket'],
                title=f'Vazão P85 por Urgência ({bucket_label.lower()})',
                labels={'P85': f'P85 de throughput por {bucket_label.lower()}'},
                color='P85',
                color_continuous_scale='Blues',
            )
            fig_tp_urgency.update_layout(height=360, coloraxis_showscale=False)

        return html.Div([
            html.H3(titulo, style={'textAlign': 'center', 'marginBottom': '10px'}),
            leadtime_selection_summary,
            html.Div(
                (
                    "Visão unificada para responder SLA por projeto/período com cortes por tipo, urgência e WIP atual. "
                    f"Buckets de vazão: {bucket_label.lower()}s dentro do recorte selecionado."
                ),
                style={'textAlign': 'center', 'color': '#555', 'marginBottom': '10px', 'fontSize': '13px'}
            ),
            summary_cards,
            highlights,
            html.Div([
                service_table('Lead Time por Tipo de Demanda', lead_by_type, 'Sem dados de lead time por tipo no período.', 'service-lt-type'),
                service_table('Lead Time por Urgência', lead_by_urgency, 'Sem dados de lead time por urgência no período.', 'service-lt-urgency'),
            ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(420px, 1fr))', 'gap': '12px', 'marginBottom': '14px'}),
            html.Div([
                dcc.Graph(figure=fig_lt_type),
                service_table(f'Vazão por Tipo de Demanda ({bucket_label.lower()})', tp_by_type, 'Sem dados de vazão por tipo no período.', 'service-tp-type'),
            ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(420px, 1fr))', 'gap': '12px', 'marginBottom': '14px'}),
            html.Div([
                dcc.Graph(figure=fig_tp_urgency),
                service_table(f'Vazão por Urgência ({bucket_label.lower()})', tp_by_urgency, 'Sem dados de vazão por urgência no período.', 'service-tp-urgency'),
            ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(420px, 1fr))', 'gap': '12px', 'marginBottom': '14px'}),
            html.Div([
                service_table('% Vazão por Tipo de Demanda (Mensal)', monthly_tp_pct_by_type, 'Sem dados de vazão no período.', 'service-monthly-tp-pct-type'),
                service_table('% Lead Time por Tipo de Demanda (Mensal)', monthly_lt_sla_pct_by_type, 'Sem dados de lead time no período.', 'service-monthly-lt-pct-type'),
            ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(420px, 1fr))', 'gap': '12px', 'marginBottom': '14px'}),
            html.Div([
                service_table('WIP Atual por Tipo de Demanda', wip_by_type, 'Sem itens em progresso no recorte atual.', 'service-wip-type'),
                service_table('WIP Atual por Urgência', wip_by_urgency, 'Sem itens em progresso no recorte atual.', 'service-wip-urgency'),
            ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(420px, 1fr))', 'gap': '12px', 'marginBottom': '14px'}),
            html.H4('Série semanal de apoio', style={'marginBottom': '8px'}),
            dash_table.DataTable(
                id='performance-table',
                columns=columns,
                data=table_data,
                style_cell={'textAlign': 'center', 'padding': '8px', 'minWidth': '120px'},
                style_cell_conditional=[{'if': {'column_id': 'Métrica'}, 'textAlign': 'left', 'fontWeight': 'bold', 'minWidth': '250px'}],
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=style_data_conditional + [
                    {'if': {'state': 'active'}, 'backgroundColor': 'rgba(0, 116, 217, 0.1)', 'border': '1px solid rgb(0, 116, 217)'}
                ],
                style_table={'overflowX': 'auto'},
            ),
            html.Div(id='performance-metric-chart'),
        ])

    if tab == 'tab-gmud':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        gmud_index_df, gmud_index_error = get_gmud_snapshot('index')
        gmud_weekly_df, gmud_weekly_error = get_gmud_snapshot('weekly')
        gmud_items_df, gmud_items_error = get_gmud_snapshot('items')

        if gmud_items_df.empty and gmud_weekly_df.empty:
            error_lines = [msg for msg in [gmud_items_error, gmud_weekly_error, gmud_index_error] if msg]
            return html.Div([
                html.H4('Cobertura GMUD indisponível', style={'textAlign': 'center', 'color': '#b45309'}),
                html.P(
                    'Os artefatos `gmud-coverage-*` ainda não estão disponíveis para o dashboard.',
                    style={'textAlign': 'center', 'color': '#475569'}
                ),
                html.Ul([html.Li(line) for line in error_lines], style={'maxWidth': '860px', 'margin': '12px auto', 'color': '#64748b'}) if error_lines else html.Div(),
            ], style={'padding': '18px', 'border': '1px dashed #cbd5e1', 'borderRadius': '12px', 'backgroundColor': '#fff'})

        canonical_project = _canonical_gmud_service_team(projeto) if projeto else ''
        items_scope = gmud_items_df.copy()
        if not items_scope.empty:
            items_scope = items_scope[_gmud_scope_mask(items_scope, projeto)].copy()
            items_scope = items_scope[items_scope['EligibleForGMUD'] == True].copy()
            if 'ReferenceDate' in items_scope.columns:
                items_scope = items_scope[
                    items_scope['ReferenceDate'].notna() &
                    (items_scope['ReferenceDate'] >= start_ts) &
                    (items_scope['ReferenceDate'] <= end_ts)
                ].copy()

            if not df.empty and 'ItemID' in df.columns:
                df_urg = df[['ItemID', 'ClasseServico', 'Prioridade']].drop_duplicates(subset=['ItemID']).fillna('')
                items_scope = items_scope.merge(df_urg, left_on='ItemKey', right_on='ItemID', how='left')
            else:
                items_scope['ClasseServico'] = ''
                items_scope['Prioridade'] = ''
            
            items_scope['ClassificacaoUrgencia'] = items_scope.apply(classify_urgency_label, axis=1)
            items_scope['TipoUrgencia'] = items_scope['ClassificacaoUrgencia'].apply(lambda x: 'Emergencial' if x == 'Highest' else 'Normal')

        weekly_scope = gmud_weekly_df.copy()
        if not weekly_scope.empty:
            if 'Semana' in weekly_scope.columns:
                weekly_scope = weekly_scope[
                    weekly_scope['Semana'].notna() &
                    (weekly_scope['Semana'] >= start_ts) &
                    (weekly_scope['Semana'] <= end_ts + pd.Timedelta(days=7))
                ].copy()
            if canonical_project:
                if {'Escopo', 'Valor'}.issubset(weekly_scope.columns):
                    weekly_scope = weekly_scope[
                        (weekly_scope['Escopo'].astype(str) == 'Time') &
                        (weekly_scope['Valor'].astype(str).apply(_canonical_gmud_service_team) == canonical_project)
                    ].copy()
            elif {'Escopo', 'Valor'}.issubset(weekly_scope.columns):
                weekly_scope = weekly_scope[
                    (weekly_scope['Escopo'].astype(str) == 'Geral') &
                    (weekly_scope['Valor'].astype(str) == 'Total')
                ].copy()

        if weekly_scope.empty and not items_scope.empty:
            derived_weekly_rows = []
            weekly_items = items_scope.copy()
            weekly_items['Semana'] = weekly_bucket_start(weekly_items['ReferenceDate'])
            for week, group in weekly_items.groupby('Semana', dropna=False):
                eligible_total = int(len(group))
                covered_total = int(group['HasGMUD'].sum())
                explicit_total = int((group['PrimaryEvidenceBucket'].astype(str) == 'Explicita').sum())
                comment_total = int(group['UsedCommentEvidence'].sum())
                row = {
                    'Semana': week,
                    'Escopo': 'Time' if canonical_project else 'Geral',
                    'Valor': canonical_project if canonical_project else 'Total',
                    'ItensElegiveis': eligible_total,
                    'ItensComGMUD': covered_total,
                    'ItensSemGMUD': max(eligible_total - covered_total, 0),
                    'IndiceCoberturaGMUDPct': round((covered_total / eligible_total) * 100.0, 1) if eligible_total else 0.0,
                    'ItensComEvidenciaExplicita': explicit_total,
                    'ItensComEvidenciaComentario': comment_total,
                }
                for bucket_name in ['Melhoria', 'Manutencao', 'Bug']:
                    bucket_df = group[group['DeliveryBucket'].astype(str) == bucket_name]
                    bucket_total = int(len(bucket_df))
                    bucket_covered = int(bucket_df['HasGMUD'].sum()) if bucket_total else 0
                    row[f'Itens{bucket_name}'] = bucket_total
                    row[f'{bucket_name}ComGMUD'] = bucket_covered
                    row[f'Pct{bucket_name}'] = round((bucket_covered / bucket_total) * 100.0, 1) if bucket_total else 0.0
                derived_weekly_rows.append(row)
            weekly_scope = pd.DataFrame(derived_weekly_rows)

        baseline_scope = gmud_index_df.copy()
        if not baseline_scope.empty:
            if canonical_project and {'Escopo', 'Valor'}.issubset(baseline_scope.columns):
                baseline_scope = baseline_scope[
                    (baseline_scope['Escopo'].astype(str) == 'Time') &
                    (baseline_scope['Valor'].astype(str).apply(_canonical_gmud_service_team) == canonical_project)
                ].copy()
            elif {'Escopo', 'Valor'}.issubset(baseline_scope.columns):
                baseline_scope = baseline_scope[
                    (baseline_scope['Escopo'].astype(str) == 'Geral') &
                    (baseline_scope['Valor'].astype(str) == 'Total')
                ].copy()

        def gmud_metric_card(label, value, subtitle='', accent='#0f766e'):
            return html.Div([
                html.Div(label, style={'fontSize': '12px', 'fontWeight': '700', 'textTransform': 'uppercase', 'letterSpacing': '0.4px', 'color': '#475569'}),
                html.Div(value, style={'fontSize': '30px', 'fontWeight': '800', 'lineHeight': '1.1', 'color': '#10202f', 'marginTop': '6px'}),
                html.Div(subtitle, style={'fontSize': '12px', 'color': '#64748b', 'marginTop': '6px'}),
            ], style={
                'background': 'linear-gradient(180deg, #ffffff 0%, #f8fbff 100%)',
                'border': f'1px solid {accent}33',
                'borderTop': f'4px solid {accent}',
                'borderRadius': '12px',
                'padding': '14px',
                'minHeight': '118px',
                'boxShadow': '0 8px 18px rgba(15, 23, 42, 0.05)',
            })

        eligible_total = int(len(items_scope))
        covered_total = int(items_scope['HasGMUD'].sum()) if eligible_total else 0
        uncovered_total = max(eligible_total - covered_total, 0)
        coverage_pct = round((covered_total / eligible_total) * 100.0, 1) if eligible_total else 0.0
        explicit_total = int((items_scope['PrimaryEvidenceBucket'].astype(str) == 'Explicita').sum()) if eligible_total else 0
        explicit_pct = round((explicit_total / eligible_total) * 100.0, 1) if eligible_total else 0.0
        text_or_comment_total = int(items_scope['PrimaryEvidenceBucket'].astype(str).isin(['Texto', 'Comentario']).sum()) if eligible_total else 0
        text_or_comment_pct = round((text_or_comment_total / eligible_total) * 100.0, 1) if eligible_total else 0.0
        unique_chgs = 0
        if not items_scope.empty and 'MatchedCHGKeys' in items_scope.columns:
            unique_chgs = len({
                token.strip() for value in items_scope['MatchedCHGKeys'].fillna('').astype(str)
                for token in value.split(',')
                if token.strip()
            })

        baseline_label = 'Sem baseline latest disponível'
        if not baseline_scope.empty and 'IndiceCoberturaGMUDPct' in baseline_scope.columns:
            baseline_value = pd.to_numeric(baseline_scope['IndiceCoberturaGMUDPct'], errors='coerce').dropna()
            if not baseline_value.empty:
                baseline_label = f"baseline latest: {baseline_value.iloc[0]:.1f}%"

        subtitle_scope = canonical_project if canonical_project else 'Todos os times'
        summary_cards = html.Div([
            gmud_metric_card('Cobertura GMUD', f'{coverage_pct:.1f}%', f'{covered_total}/{eligible_total} itens com evidência | {baseline_label}', '#0f766e'),
            gmud_metric_card('Cobertura explícita', f'{explicit_pct:.1f}%', f'{explicit_total} itens por vínculo estruturado', '#176ea4'),
            gmud_metric_card('Texto / comentário', f'{text_or_comment_pct:.1f}%', f'{text_or_comment_total} itens cobertos por menção textual', '#c77d12'),
            gmud_metric_card('Itens sem GMUD', str(uncovered_total), f'gaps do recorte {subtitle_scope}', '#c62828'),
            gmud_metric_card('Itens elegíveis', str(eligible_total), 'itens com data de referência para produção/finalização', '#455a64'),
            gmud_metric_card('GMUDs únicas', str(unique_chgs), 'tickets CHG distintos relacionados ao recorte', '#6d4c41'),
        ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(200px, 1fr))', 'gap': '12px', 'marginTop': '14px', 'marginBottom': '16px'})

        findings = []
        if eligible_total:
            findings.append(f'O recorte atual cobre {eligible_total} itens elegíveis e {coverage_pct:.1f}% deles têm alguma evidência de GMUD.')
            findings.append(f'A cobertura explícita está em {explicit_pct:.1f}%, enquanto {text_or_comment_pct:.1f}% depende de texto/comentário.')
            findings.append(f'Existem {uncovered_total} itens sem evidência de GMUD no período filtrado.')
        else:
            findings.append('Não há itens elegíveis no recorte atual para medir cobertura GMUD.')
        if unique_chgs:
            findings.append(f'O recorte se relaciona a {unique_chgs} tickets CHG distintos.')
        if canonical_project:
            findings.append(f'A leitura está filtrada para o time/value stream {canonical_project}.')
        else:
            findings.append('A visão está consolidada para todos os times/value streams.')

        highlight_panel = html.Div([
            html.Strong('Leitura executiva da cobertura GMUD'),
            html.Ul([html.Li(text) for text in findings], style={'marginTop': '8px', 'marginBottom': '0', 'paddingLeft': '20px'})
        ], style={'backgroundColor': '#f8fafc', 'border': '1px solid #dbeafe', 'borderRadius': '12px', 'padding': '12px', 'marginBottom': '16px'})

        fig_weekly = go.Figure()
        if not weekly_scope.empty and {'Semana', 'IndiceCoberturaGMUDPct', 'ItensSemGMUD', 'ItensComGMUD'}.issubset(weekly_scope.columns):
            weekly_plot = weekly_scope.sort_values('Semana').copy()
            fig_weekly = make_subplots(specs=[[{"secondary_y": True}]])
            fig_weekly.add_trace(
                go.Bar(
                    x=weekly_plot['Semana'],
                    y=weekly_plot['ItensComGMUD'],
                    name='Itens com GMUD',
                    marker_color='#2e7d32',
                    hovertemplate='Semana: %{x|%Y-%m-%d}<br>Itens com GMUD: %{y}<extra></extra>'
                ),
                secondary_y=False,
            )
            fig_weekly.add_trace(
                go.Bar(
                    x=weekly_plot['Semana'],
                    y=weekly_plot['ItensSemGMUD'],
                    name='Itens sem GMUD',
                    marker_color='#c62828',
                    hovertemplate='Semana: %{x|%Y-%m-%d}<br>Itens sem GMUD: %{y}<extra></extra>'
                ),
                secondary_y=False,
            )
            fig_weekly.add_trace(
                go.Scatter(
                    x=weekly_plot['Semana'],
                    y=weekly_plot['IndiceCoberturaGMUDPct'],
                    name='Cobertura (%)',
                    mode='lines+markers',
                    line={'color': '#176ea4', 'width': 3},
                    hovertemplate='Semana: %{x|%Y-%m-%d}<br>Cobertura: %{y:.1f}%<extra></extra>'
                ),
                secondary_y=True,
            )
            fig_weekly.update_layout(
                title='Histórico semanal de cobertura GMUD',
                height=430,
                barmode='stack',
                legend={'orientation': 'h', 'y': 1.12},
                margin=dict(t=70, b=60),
            )
            fig_weekly.update_yaxes(title_text='Itens', secondary_y=False)
            fig_weekly.update_yaxes(title_text='Cobertura (%)', range=[0, 100], secondary_y=True)

        category_summary = pd.DataFrame(columns=['Categoria', 'Itens Elegíveis', 'Itens com GMUD', 'Itens sem GMUD', 'Cobertura (%)'])
        if not items_scope.empty:
            category_rows = []
            for bucket_name in ['Melhoria', 'Manutencao', 'Bug']:
                bucket_df = items_scope[items_scope['DeliveryBucket'].astype(str) == bucket_name].copy()
                total_bucket = int(len(bucket_df))
                covered_bucket = int(bucket_df['HasGMUD'].sum()) if total_bucket else 0
                category_rows.append({
                    'Categoria': bucket_name,
                    'Itens Elegíveis': total_bucket,
                    'Itens com GMUD': covered_bucket,
                    'Itens sem GMUD': max(total_bucket - covered_bucket, 0),
                    'Cobertura (%)': round((covered_bucket / total_bucket) * 100.0, 1) if total_bucket else 0.0,
                })
            category_summary = pd.DataFrame(category_rows)

        fig_category = go.Figure()
        if not category_summary.empty and category_summary['Itens Elegíveis'].sum() > 0:
            fig_category = px.bar(
                category_summary,
                x='Categoria',
                y=['Itens com GMUD', 'Itens sem GMUD'],
                title='Cobertura por categoria de entrega',
                barmode='stack',
                color_discrete_map={'Itens com GMUD': '#2e7d32', 'Itens sem GMUD': '#c62828'},
            )
            fig_category.update_layout(height=360, legend_title_text='')

        evidence_summary = pd.DataFrame(columns=['Tipo de evidência', 'Itens'])
        if not items_scope.empty:
            evidence_summary = (
                items_scope[items_scope['HasGMUD'] == True]
                .assign(**{'Tipo de evidência': items_scope.loc[items_scope['HasGMUD'] == True, 'PrimaryEvidenceBucket'].replace({'Explicita': 'Explícita', 'Comentario': 'Comentário', 'Texto': 'Texto'})})
                .groupby('Tipo de evidência', dropna=False)
                .size()
                .reset_index(name='Itens')
                .sort_values('Itens', ascending=False, ignore_index=True)
            )

        fig_evidence = go.Figure()
        if not evidence_summary.empty:
            fig_evidence = px.pie(
                evidence_summary,
                names='Tipo de evidência',
                values='Itens',
                title='Distribuição da evidência de cobertura',
                color='Tipo de evidência',
                color_discrete_map={'Explícita': '#176ea4', 'Comentário': '#c77d12', 'Texto': '#7b61ff'},
                hole=0.45,
            )
            fig_evidence.update_layout(height=360)

        team_summary = pd.DataFrame(columns=['Time', 'Itens Elegíveis', 'Itens com GMUD', 'Itens sem GMUD', 'Cobertura (%)'])
        if not items_scope.empty and not canonical_project:
            team_summary = (
                items_scope.groupby('ServiceTeam', dropna=False)
                .agg(
                    **{
                        'Itens Elegíveis': ('ItemKey', 'count'),
                        'Itens com GMUD': ('HasGMUD', 'sum'),
                    }
                )
                .reset_index()
                .rename(columns={'ServiceTeam': 'Time'})
            )
            team_summary['Itens sem GMUD'] = team_summary['Itens Elegíveis'] - team_summary['Itens com GMUD']
            team_summary['Cobertura (%)'] = np.where(
                team_summary['Itens Elegíveis'] > 0,
                team_summary['Itens com GMUD'] / team_summary['Itens Elegíveis'] * 100.0,
                0.0,
            ).round(1)
            team_summary = team_summary.sort_values(['Cobertura (%)', 'Itens Elegíveis'], ascending=[False, False], ignore_index=True)

        fig_team = go.Figure()
        if not team_summary.empty:
            fig_team = px.bar(
                team_summary,
                x='Time',
                y='Cobertura (%)',
                color='Itens sem GMUD',
                title='Cobertura GMUD por time no recorte',
                color_continuous_scale='RdYlGn_r',
                hover_data=['Itens Elegíveis', 'Itens com GMUD', 'Itens sem GMUD'],
            )
            fig_team.update_layout(height=360, coloraxis_colorbar_title='Gaps')

        gaps_df = pd.DataFrame(columns=['ItemKey', 'ServiceTeam', 'DeliveryBucket', 'ReferenceDate', 'Titulo', 'Source', 'ReferenceKeys'])
        if not items_scope.empty:
            gaps_df = items_scope[items_scope['HasGMUD'] == False].copy()
            if not gaps_df.empty:
                gaps_df = gaps_df[['ItemKey', 'ServiceTeam', 'DeliveryBucket', 'ReferenceDate', 'Titulo', 'Source', 'ReferenceKeys']].copy()
                gaps_df['ReferenceDate'] = pd.to_datetime(gaps_df['ReferenceDate'], errors='coerce').dt.strftime('%Y-%m-%d')
                gaps_df['ReferenceKeys'] = gaps_df['ReferenceKeys'].fillna('').astype(str)
                gaps_df = gaps_df.sort_values(['ReferenceDate', 'ServiceTeam', 'ItemKey'], ascending=[False, True, True], ignore_index=True)

        chg_summary_df = pd.DataFrame(columns=['CHG', 'Itens Cobertos', 'Times', 'Categorias'])
        if not items_scope.empty and 'MatchedCHGKeys' in items_scope.columns:
            chg_rows = []
            covered_items = items_scope[items_scope['HasGMUD'] == True].copy()
            for _, row in covered_items.iterrows():
                for token in str(row.get('MatchedCHGKeys') or '').split(','):
                    chg_key = token.strip()
                    if not chg_key:
                        continue
                    chg_rows.append({
                        'CHG': chg_key,
                        'ItemKey': str(row.get('ItemKey') or '').strip(),
                        'Time': str(row.get('ServiceTeam') or '').strip(),
                        'Categoria': str(row.get('DeliveryBucket') or '').strip(),
                    })
            if chg_rows:
                chg_expanded = pd.DataFrame(chg_rows)
                chg_summary_df = (
                    chg_expanded.groupby('CHG', dropna=False)
                    .agg(
                        **{
                            'Itens Cobertos': ('ItemKey', 'nunique'),
                            'Times': ('Time', lambda s: ', '.join(sorted({str(v).strip() for v in s if str(v).strip()}))),
                            'Categorias': ('Categoria', lambda s: ', '.join(sorted({str(v).strip() for v in s if str(v).strip()}))),
                        }
                    )
                    .reset_index()
                    .sort_values(['Itens Cobertos', 'CHG'], ascending=[False, True], ignore_index=True)
                )

        fig_urgency_total = go.Figure()
        fig_urgency_weekly = go.Figure()

        if not items_scope.empty:
            gmud_done_scope = items_scope[items_scope['HasGMUD'] == True].copy()
            if not gmud_done_scope.empty:
                gmud_done_scope['ServiceTeam'] = gmud_done_scope['ServiceTeam'].fillna('Indefinido')
                
                urgency_summary = (
                    gmud_done_scope.groupby(['ServiceTeam', 'TipoUrgencia'], dropna=False)
                    .size().reset_index(name='Quantidade')
                )
                fig_urgency_total = px.bar(
                    urgency_summary,
                    x='ServiceTeam',
                    y='Quantidade',
                    color='TipoUrgencia',
                    title='Total de GMUDs por Produto e Urgência',
                    barmode='stack',
                    color_discrete_map={'Emergencial': '#d32f2f', 'Normal': '#1976d2'},
                    labels={'ServiceTeam': 'Produto', 'TipoUrgencia': 'Urgência'}
                )
                fig_urgency_total.update_layout(height=360, margin=dict(t=40, b=40))

                if 'ReferenceDate' in gmud_done_scope.columns:
                    gmud_done_scope['Semana'] = weekly_bucket_start(gmud_done_scope['ReferenceDate'])
                    weekly_urgency_summary = (
                        gmud_done_scope.groupby(['Semana', 'ServiceTeam', 'TipoUrgencia'], dropna=False)
                        .size().reset_index(name='Quantidade')
                    )
                    weekly_urgency_summary['Produto_Tipo'] = weekly_urgency_summary['ServiceTeam'].astype(str) + ' (' + weekly_urgency_summary['TipoUrgencia'] + ')'
                    fig_urgency_weekly = px.bar(
                        weekly_urgency_summary.sort_values('Semana'),
                        x='Semana',
                        y='Quantidade',
                        color='Produto_Tipo',
                        title='Evolução Semanal de GMUDs',
                        barmode='stack',
                        labels={'Semana': 'Semana', 'Produto_Tipo': 'Produto/Urgência'}
                    )
                    fig_urgency_weekly.update_layout(height=400, margin=dict(t=40, b=40))

        title_suffix = f' - {canonical_project}' if canonical_project else ''
        filter_note = 'A aba usa principalmente período e Time. Os filtros de Responsável, Classe e Tipo ainda não restringem diretamente a base GMUD nesta versão.'

        def gmud_table_card(title, description, df_table, table_id, page_size=10):
            body = html.P('Sem dados no recorte atual.', style={'color': '#64748b', 'margin': 0})
            if df_table is not None and not df_table.empty:
                body = dash_table.DataTable(
                    id=table_id,
                    columns=[{'name': c, 'id': c} for c in df_table.columns],
                    data=df_table.to_dict('records'),
                    page_size=page_size,
                    style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px', 'whiteSpace': 'normal', 'height': 'auto'},
                    style_header={'backgroundColor': '#e2e8f0', 'fontWeight': 'bold'},
                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8fafc'}],
                    style_table={'overflowX': 'auto'},
                    filter_action='native' if len(df_table) > 10 else 'none',
                    sort_action='native',
                )
            return html.Div([
                html.H4(title, style={'marginTop': '0', 'marginBottom': '6px', 'color': '#10202f'}),
                html.P(description, style={'marginTop': '0', 'marginBottom': '10px', 'color': '#64748b', 'fontSize': '13px'}),
                body,
            ], style={'backgroundColor': '#ffffff', 'border': '1px solid #e2e8f0', 'borderRadius': '12px', 'padding': '14px'})

        return html.Div([
            html.H3(f'Cobertura GMUD{title_suffix}', style={'textAlign': 'center', 'marginBottom': '8px', 'color': '#10202f'}),
            html.Div(
                'Painel para acompanhar se as entregas do fluxo estão sendo acompanhadas por solicitações de mudança para produção (GMUD/CHG).',
                style={'textAlign': 'center', 'color': '#475569', 'fontSize': '13px', 'marginBottom': '8px'}
            ),
            html.Div(filter_note, style={'textAlign': 'center', 'color': '#8a6d3b', 'fontSize': '12px', 'marginBottom': '10px'}),
            summary_cards,
            highlight_panel,
            html.Div([
                html.Div([dcc.Graph(figure=fig_weekly)], style={'backgroundColor': '#fff', 'border': '1px solid #e2e8f0', 'borderRadius': '12px', 'padding': '10px', 'minWidth': '360px', 'flex': '2 1 560px'}),
                html.Div([dcc.Graph(figure=fig_evidence)], style={'backgroundColor': '#fff', 'border': '1px solid #e2e8f0', 'borderRadius': '12px', 'padding': '10px', 'minWidth': '320px', 'flex': '1 1 320px'}),
            ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap', 'marginBottom': '14px'}),
            html.Div([
                html.Div([dcc.Graph(figure=fig_category)], style={'backgroundColor': '#fff', 'border': '1px solid #e2e8f0', 'borderRadius': '12px', 'padding': '10px', 'minWidth': '360px', 'flex': '1 1 420px'}),
                html.Div([dcc.Graph(figure=fig_team)], style={'backgroundColor': '#fff', 'border': '1px solid #e2e8f0', 'borderRadius': '12px', 'padding': '10px', 'minWidth': '360px', 'flex': '1 1 420px'}) if not team_summary.empty else html.Div(),
            ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap', 'marginBottom': '14px'}),
            html.Div([
                html.Div([dcc.Graph(figure=fig_urgency_total)], style={'backgroundColor': '#fff', 'border': '1px solid #e2e8f0', 'borderRadius': '12px', 'padding': '10px', 'minWidth': '320px', 'flex': '1 1 350px'}),
                html.Div([dcc.Graph(figure=fig_urgency_weekly)], style={'backgroundColor': '#fff', 'border': '1px solid #e2e8f0', 'borderRadius': '12px', 'padding': '10px', 'minWidth': '420px', 'flex': '2 1 500px'}),
            ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap', 'marginBottom': '14px'}),
            html.Div([
                gmud_table_card(
                    'Resumo por categoria',
                    'Cobertura no recorte por categoria de entrega.',
                    category_summary,
                    'gmud-category-summary',
                    page_size=6,
                ),
                gmud_table_card(
                    'GMUDs relacionadas',
                    'Tickets CHG mais reutilizados no recorte atual.',
                    chg_summary_df.head(30),
                    'gmud-chg-summary',
                    page_size=10,
                ),
            ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(420px, 1fr))', 'gap': '12px', 'marginBottom': '14px'}),
            html.Div([
                gmud_table_card(
                    'Itens sem evidência de GMUD',
                    'Gaps prioritários do recorte: entregas sem vínculo explícito nem menção textual/comentário em GMUD.',
                    gaps_df.head(200),
                    'gmud-gap-items',
                    page_size=12,
                ),
                gmud_table_card(
                    'Resumo por time',
                    'Comparativo de cobertura por time/value stream no recorte atual.',
                    team_summary.head(20) if not team_summary.empty else pd.DataFrame(),
                    'gmud-team-summary',
                    page_size=10,
                ),
            ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(420px, 1fr))', 'gap': '12px'}),
        ])

    if tab == 'tab-lead-time':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        delivered_scope = build_delivered_items_base(df)
        delivered_total = int(len(delivered_scope))
        df_lt, lt_series, lt_stats = build_lead_time_comparable_scope(df, lead_col='LeadTime_Selected_Dias')
        if lt_series.empty:
            return html.Div('Sem amostra válida de Lead Time para o período e filtros selecionados.')

        line_defs = [
            ('p50', 'P50', '#27AE60', 'dash'),
            ('p75', 'P75', '#2D9CDB', 'dash'),
            ('p85', 'P85', '#9B51E0', 'dash'),
            ('p95', 'P95', '#EB5757', 'dash'),
            ('mean', 'Média', '#333333', 'dot'),
        ]

        freq = df_lt['LeadTime_Selected_Dias'].round().astype(int).value_counts().sort_index().reset_index()
        freq.columns = ['LeadTimeDia', 'Frequencia']
        freq['CumulativoPct'] = (freq['Frequencia'].cumsum() / freq['Frequencia'].sum()) * 100

        fig_lt_dist = make_subplots(specs=[[{'secondary_y': True}]])
        fig_lt_dist.add_trace(
            go.Bar(x=freq['LeadTimeDia'], y=freq['Frequencia'], name='Frequência', marker_color='#2F80ED'),
            secondary_y=False
        )
        fig_lt_dist.add_trace(
            go.Scatter(
                x=freq['LeadTimeDia'],
                y=freq['CumulativoPct'],
                mode='lines',
                name='Cumulativo %',
                line=dict(color='#F2994A', width=3)
            ),
            secondary_y=True
        )
        for key, label, color, dash_style in line_defs:
            val = lt_stats.get(key)
            if pd.isna(val):
                continue
            fig_lt_dist.add_vline(
                x=float(val),
                line_color=color,
                line_dash=dash_style,
                line_width=1.5,
                annotation_text=f'{label}: {float(val):.1f}',
                annotation_position='top',
                annotation_textangle=90
            )
        fig_lt_dist.update_layout(
            title=dict(
                text='Lead Time Distribution: frequência e curva acumulada',
                x=0.5,
                xanchor='center',
                pad=dict(b=48)
            ),
            template='plotly_white',
            hovermode='x unified',
            legend=dict(orientation='h', y=-0.18, x=0.5, xanchor='center'),
            height=620,
            margin=dict(t=160, b=120, l=60, r=60)
        )
        fig_lt_dist.update_xaxes(title_text='Lead Time (dias)')
        fig_lt_dist.update_yaxes(title_text='Frequência (# itens)', secondary_y=False)
        fig_lt_dist.update_yaxes(title_text='Cumulativo (%)', range=[0, 100], secondary_y=True)

        df_lt_scatter = df_lt.copy().sort_values('DataDone').reset_index(drop=True)
        df_lt_scatter['MM_10'] = df_lt_scatter['LeadTime_Selected_Dias'].rolling(10, min_periods=1).mean()

        fig_lt_scatter = go.Figure()
        fig_lt_scatter.add_trace(go.Scatter(
            x=df_lt_scatter['DataDone'],
            y=df_lt_scatter['LeadTime_Selected_Dias'],
            mode='markers',
            name='Lead Time (item)',
            marker=dict(color='#2F80ED', size=8, opacity=0.75),
            hovertemplate='Done: %{x|%d/%m/%Y}<br>Lead Time: %{y:.1f} dias<extra></extra>'
        ))
        fig_lt_scatter.add_trace(go.Scatter(
            x=df_lt_scatter['DataDone'],
            y=df_lt_scatter['MM_10'],
            mode='lines',
            name='Média móvel (10 itens)',
            line=dict(color='#F2994A', width=3, dash='dash')
        ))
        for key, label, color, dash_style in line_defs:
            val = lt_stats.get(key)
            if pd.isna(val):
                continue
            fig_lt_scatter.add_hline(
                y=float(val),
                line_color=color,
                line_dash=dash_style,
                line_width=1.2,
                annotation_text=f'{label}: {float(val):.1f}',
                annotation_position='top right'
            )

        weekly_lt = (
            df_lt_scatter.assign(Semana=weekly_bucket_start(df_lt_scatter['DataDone']))
            .groupby('Semana', as_index=False)['LeadTime_Selected_Dias'].mean()
            .sort_values('Semana')
        )
        if not weekly_lt.empty:
            fig_lt_scatter.add_trace(go.Scatter(
                x=weekly_lt['Semana'],
                y=weekly_lt['LeadTime_Selected_Dias'],
                mode='lines',
                name='Lead Time médio semanal',
                line=dict(color='#111827', width=2)
            ))

        fig_lt_scatter.update_layout(
            title='Lead Time: itens concluídos ao longo do tempo',
            template='plotly_white',
            hovermode='x unified',
            legend=dict(orientation='h', y=-0.18, x=0.5, xanchor='center'),
            height=620,
            margin=dict(t=80, b=120, l=60, r=40)
        )
        fig_lt_scatter.update_xaxes(title_text='Data de conclusão', tickformat='%d/%m/%Y', tickangle=-45)
        fig_lt_scatter.update_yaxes(title_text='Lead Time (dias)')

        lt_valid_total = int(len(lt_series))
        lt_missing_total = int(max(delivered_total - lt_valid_total, 0))
        lt_fallback_total = int(leadtime_meta.get('fallback_sample', 0))
        lt_mean = lt_stats.get('mean', np.nan)
        lt_p50 = lt_stats.get('p50', np.nan)
        lt_p85 = lt_stats.get('p85', np.nan)
        subtitle = (
            f"Projeto: {projeto or 'Todos'} | Período: {start_ts.strftime('%d/%m/%Y')} a {end_ts.strftime('%d/%m/%Y')} | "
            f"Finalizados: {delivered_total} | LT válido: {lt_valid_total} | Sem base LT: {lt_missing_total} | "
            f"Fallback aplicado: {lt_fallback_total} | "
            f"Média: {lt_mean:.2f} | P50: {lt_p50:.2f} | P85: {lt_p85:.2f} | "
            f"Início: {leadtime_meta.get('label', 'padrão')}"
        )

        # --- Análise Avançada de Fluxo (anteriormente aba 'Fluxo') ---
        df_flow = df.copy()
        flow_lead_meta = leadtime_meta

        if etapa_fluxo and projeto:
            _stage_map_flow = compute_current_stage_map(projeto)
            df_flow = filter_items_by_current_stage(
                df_flow,
                projeto=projeto,
                selected_stages=etapa_fluxo,
                stage_map=_stage_map_flow,
                keep_done=True,
            )

        mask_started_until_end = df_flow['DataInProgress'].isna() | (df_flow['DataInProgress'] <= end_ts)
        mask_not_finished_before_start = df_flow['DataDone'].isna() | (df_flow['DataDone'] >= start_ts)
        df_flow = df_flow[mask_started_until_end & mask_not_finished_before_start].copy()
        df_flow_done_period = df_flow[
            (df_flow['DataDone'] >= start_ts) &
            (df_flow['DataDone'] <= end_ts)
        ].copy()
        df_flow_done_period_eligible = df_flow_done_period[done_time_eligible_mask(df_flow_done_period)].copy()

        flow_metrics = {}
        lead_time_selected = time_metric_series(df_flow_done_period_eligible, 'LeadTime_Selected_Dias', non_negative=True)
        tempo_exec = time_metric_series(df_flow_done_period_eligible, 'TempoExecucao_Dias', non_negative=True)
        tempo_backlog = time_metric_series(df_flow_done_period_eligible, 'TempoBacklog_Dias', non_negative=True)
        tempo_bloqueio = time_metric_series(df_flow_done_period_eligible, 'TempoBloqueioDias', non_negative=True)
        tempo_espera = time_metric_series(df_flow_done_period_eligible, 'TempoEsperaIntermediariaDias', non_negative=True)

        if not lead_time_selected.empty:
            flow_metrics['Lead Time Médio (dias)'] = lead_time_selected.mean()
            flow_metrics['Lead Time P85 (dias)'] = exact_empirical_percentile(lead_time_selected, 0.85)
            flow_metrics['Lead Time Mediano (dias)'] = exact_empirical_percentile(lead_time_selected, 0.50)
        if not tempo_exec.empty:
            flow_metrics['Cycle Time Médio (dias)'] = tempo_exec.mean()
            flow_metrics['Cycle Time Mediano (dias)'] = tempo_exec.median()
        if not tempo_backlog.empty:
            flow_metrics['Tempo em Backlog Médio (dias)'] = tempo_backlog.mean()
            flow_metrics['Tempo até Primeiro Movimento (dias)'] = tempo_backlog.mean()
        arrivals_period = len(df_flow[
            (df_flow['DataInProgress'] >= start_ts) &
            (df_flow['DataInProgress'] <= end_ts)
        ])
        throughput_period = len(df_flow_done_period_eligible)
        pressure_period, efficiency_period = calculate_flow_efficiency(arrivals_period, throughput_period)
        if pd.notna(efficiency_period):
            flow_metrics['Eficiência de Fluxo (1 - ρ)'] = efficiency_period
        if pd.notna(pressure_period):
            flow_metrics['Pressão de Fluxo (ρ = λ/μ)'] = pressure_period
        if not tempo_bloqueio.empty:
            flow_metrics['Tempo de Bloqueio Médio (dias)'] = tempo_bloqueio.mean()
        if not tempo_espera.empty:
            flow_metrics['Tempo de Espera Intermediária Médio (dias)'] = tempo_espera.mean()
        if 'Bloqueado' in df_flow.columns:
            total_items = len(df_flow)
            blocked_items = df_flow['Bloqueado'].sum()
            flow_metrics['Taxa de Bloqueio (%)'] = (blocked_items / total_items * 100) if total_items > 0 else 0

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}"} for k, v in flow_metrics.items()]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        bottlenecks_df = load_project_bottlenecks_from_model(projeto)
        if bottlenecks_df.empty:
            bottlenecks_df = load_project_bottlenecks_from_csv(projeto)
        if bottlenecks_df.empty:
            bottlenecks_df = compute_flow_bottlenecks(df_flow)

        lead_hist_component = html.P('Sem dados válidos de Lead Time (>= 0 dias) para o período e filtros selecionados.')
        lead_band_table_component = html.P('Sem dados suficientes para calcular bandas percentílicas exatas de Lead Time.')
        if 'LeadTime_Selected_Dias' in df_flow.columns:
            lead_series_flow = time_metric_series(df_flow_done_period_eligible, 'LeadTime_Selected_Dias', non_negative=True)
            if not lead_series_flow.empty:
                lead_df = pd.DataFrame({'LeadTime_Selected_Dias': lead_series_flow})
                fig_lead_hist = px.histogram(
                    lead_df,
                    x='LeadTime_Selected_Dias',
                    nbins=30,
                    title='Distribuição do Lead Time (dias)',
                )
                fig_lead_hist.update_layout(
                    height=500,
                    xaxis=dict(title='Lead Time (dias)', rangemode='nonnegative'),
                    yaxis=dict(title='Quantidade de itens'),
                )
                lead_hist_component = dcc.Graph(figure=fig_lead_hist)
                lead_bands_df = exact_percentile_band_summary(lead_series_flow)
                lead_band_table_component = dash_table.DataTable(
                    columns=[{"name": i, "id": i} for i in lead_bands_df.columns],
                    data=lead_bands_df.to_dict('records'),
                    style_cell={'textAlign': 'center', 'padding': '6px'},
                    style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
                )

        lead_time_breakdown_component = html.P('Sem dados suficientes para calcular o breakdown percentual de lead time por etapa.')
        if bottlenecks_df.empty:
            fig_bottlenecks = {}
            bottlenecks_table = html.P('Sem dados suficientes para calcular gargalos por etapa.')
        else:
            fig_bottlenecks = go.Figure(
                go.Bar(
                    x=bottlenecks_df['Tempo Médio (dias)'],
                    y=bottlenecks_df['Etapa'],
                    orientation='h',
                    text=[
                        f"{lt:.2f} d | vazão: {vz}"
                        for lt, vz in zip(
                            bottlenecks_df['Tempo Médio (dias)'],
                            bottlenecks_df['Vazão da Etapa (itens)'],
                        )
                    ],
                    textposition='outside',
                    marker_color='#1f77b4',
                    marker_line=dict(color='#155a8a', width=1),
                    customdata=bottlenecks_df[['Vazão da Etapa (itens)']].values,
                    hovertemplate='Etapa: %{y}<br>Lead time médio: %{x:.2f} dias'
                                  '<br>Vazão: %{customdata[0]} itens<extra></extra>',
                )
            )
            fig_bottlenecks.update_layout(
                title='Ranking de Gargalos do Fluxo (Maior para Menor)'
                      '<br><sup>Ordenação das etapas críticas por tempo médio</sup>',
                xaxis_title='Tempo médio na etapa (dias)',
                yaxis_title='Etapa',
                template='plotly_white',
                yaxis=dict(autorange='reversed'),
                height=480,
                margin=dict(l=140, r=40, t=70, b=50),
            )
            display_df = bottlenecks_df.copy()
            for c in ['Tempo Médio (dias)', 'Tempo Mediano (dias)', 'P90 (dias)']:
                display_df[c] = display_df[c].round(2)
            bottlenecks_table = dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in display_df.columns],
                data=display_df.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            )

            breakdown_df = bottlenecks_df[['Etapa', 'Tempo Médio (dias)']].copy()
            total_lead_time = breakdown_df['Tempo Médio (dias)'].sum()
            if total_lead_time > 0:
                breakdown_df['Percentual'] = (breakdown_df['Tempo Médio (dias)'] / total_lead_time) * 100
                breakdown_df['Barra'] = 'Lead Time'
                color_map = {
                    'Backlog': '#4C78A8',
                    'Execução': '#59A14F',
                    'Bloqueio': '#E45756',
                    'Espera Intermediária': '#F28E2B',
                }
                stage_order = breakdown_df['Etapa'].tolist()
                fig_lead_time_breakdown = px.bar(
                    breakdown_df,
                    x='Percentual',
                    y='Barra',
                    color='Etapa',
                    orientation='h',
                    text=breakdown_df['Percentual'].map(lambda v: f'{v:.1f}%'),
                    title='Lead Time Breakdown por Etapa do Fluxo (%)',
                    labels={'Percentual': '% do Lead Time', 'Barra': ''},
                    color_discrete_map=color_map,
                    category_orders={'Etapa': stage_order},
                    template='plotly_white',
                    height=320,
                )
                fig_lead_time_breakdown.update_layout(
                    barmode='stack',
                    xaxis=dict(range=[0, 100], ticksuffix='%'),
                    yaxis=dict(showticklabels=False),
                    legend_title_text='Etapa do Fluxo',
                    margin=dict(l=60, r=40, t=70, b=50),
                )
                fig_lead_time_breakdown.update_traces(
                    textposition='inside',
                    insidetextanchor='middle',
                    hovertemplate='Etapa: %{fullData.name}<br>% Lead Time: %{x:.1f}%<extra></extra>',
                )
                lead_time_breakdown_component = dcc.Graph(figure=fig_lead_time_breakdown)

        # --- Breakdown Semanal por Etapa ---
        # Uses downstream CSV stage dates (same source as bottlenecks_df) when available,
        # falling back to 4 aggregated columns from df_flow_done_period_eligible.
        weekly_breakdown_component = html.Div()
        _weekly_long = pd.DataFrame()
        _weekly_stage_order = []

        _ds_items = load_project_downstream_items_csv(projeto) if projeto else pd.DataFrame()
        if not _ds_items.empty and 'ID' in _ds_items.columns:
            _ds_stage_cols = _detect_stage_date_columns(_ds_items, bottlenecks_df=bottlenecks_df)
            if len(_ds_stage_cols) >= 2:
                _done_col_ds = get_downstream_done_stage_column(_ds_stage_cols)
                _non_done_cols = [c for c in _ds_stage_cols if c != _done_col_ds]
                _dates_ds = _ds_items[['ID'] + _ds_stage_cols].copy()
                for _c in _ds_stage_cols:
                    _dates_ds[_c] = pd.to_datetime(_dates_ds[_c], dayfirst=True, errors='coerce')
                _frames_ds = []
                for _i, _stage in enumerate(_non_done_cols):
                    _next_col = _ds_stage_cols[_i + 1]
                    _days = (_dates_ds[_next_col] - _dates_ds[_stage]).dt.days.clip(lower=0)
                    _frames_ds.append(pd.DataFrame({
                        'ID': _ds_items['ID'].astype(str).str.strip().values,
                        'Etapa': _stage,
                        'Dias': _days.values,
                        'DataDone': _dates_ds[_done_col_ds].values,
                    }))
                if _frames_ds:
                    _weekly_long = pd.concat(_frames_ds, ignore_index=True)
                    _weekly_long['DataDone'] = pd.to_datetime(_weekly_long['DataDone'], errors='coerce')
                    _weekly_long = _weekly_long.dropna(subset=['DataDone', 'Dias'])
                    if 'ItemID' in df_flow_done_period_eligible.columns:
                        _elig_ids = set(df_flow_done_period_eligible['ItemID'].astype(str).str.strip())
                        _weekly_long = _weekly_long[_weekly_long['ID'].isin(_elig_ids)]
                    elif not df_flow_done_period_eligible.empty and 'DataDone' in df_flow_done_period_eligible.columns:
                        _min_d = df_flow_done_period_eligible['DataDone'].min()
                        _max_d = df_flow_done_period_eligible['DataDone'].max()
                        _weekly_long = _weekly_long[
                            (_weekly_long['DataDone'] >= _min_d) & (_weekly_long['DataDone'] <= _max_d)
                        ]
                    _weekly_stage_order = _non_done_cols

        if _weekly_long.empty and not df_flow_done_period_eligible.empty and 'DataDone' in df_flow_done_period_eligible.columns:
            _static_stages = [
                ('Backlog', 'TempoBacklog_Dias'),
                ('Execução', 'TempoExecucao_Dias'),
                ('Bloqueio', 'TempoBloqueioDias'),
                ('Espera Intermediária', 'TempoEsperaIntermediariaDias'),
            ]
            _avail_static = [(n, c) for n, c in _static_stages if c in df_flow_done_period_eligible.columns]
            if _avail_static:
                _wdf = df_flow_done_period_eligible.copy()
                _wdf['DataDone'] = pd.to_datetime(_wdf['DataDone'], errors='coerce')
                _wdf = _wdf.dropna(subset=['DataDone'])
                _static_frames = []
                for _sname, _scol in _avail_static:
                    _tmp = _wdf[['DataDone', _scol]].copy()
                    _tmp[_scol] = pd.to_numeric(_tmp[_scol], errors='coerce').clip(lower=0)
                    _tmp = _tmp.rename(columns={_scol: 'Dias'})
                    _tmp['Etapa'] = _sname
                    _tmp['ID'] = ''
                    _static_frames.append(_tmp[['ID', 'Etapa', 'Dias', 'DataDone']])
                _weekly_long = pd.concat(_static_frames, ignore_index=True)
                _weekly_stage_order = [n for n, _ in _avail_static]

        if not _weekly_long.empty and _weekly_stage_order:
            _weekly_long['Semana'] = weekly_bucket_start(_weekly_long['DataDone'])
            _wagg = (
                _weekly_long.groupby(['Semana', 'Etapa'])['Dias']
                .median()
                .reset_index()
            )
            if not _wagg.empty:
                _all_weeks = sorted(_wagg['Semana'].unique())
                _fig_weekly = go.Figure()
                for _stage in _weekly_stage_order:
                    _sdf = _wagg[_wagg['Etapa'] == _stage].set_index('Semana')['Dias'].reindex(_all_weeks, fill_value=0)
                    _color = _cfd_stage_color(_stage) or '#888888'
                    _fig_weekly.add_trace(go.Bar(
                        x=pd.DatetimeIndex(_all_weeks).strftime('%d/%m/%Y'),
                        y=_sdf.values,
                        name=_stage,
                        marker_color=_color,
                        hovertemplate='Semana: %{x}<br>' + _stage + ': %{y:.1f}d<extra></extra>',
                    ))
                _fig_weekly.update_layout(
                    title='Lead Time Breakdown Semanal por Etapa (Mediana)',
                    barmode='stack',
                    template='plotly_white',
                    xaxis_title='Semana (início)',
                    yaxis_title='Dias (mediana)',
                    legend_title_text='Etapa do Fluxo',
                    height=max(380, min(520, len(_all_weeks) * 28 + 160)),
                    margin=dict(l=60, r=40, t=70, b=80),
                    xaxis=dict(tickangle=-45),
                )
                weekly_breakdown_component = dcc.Graph(figure=_fig_weekly)

        # --- Breakdown por Produto e Tipo de Item ---
        _df_breakdown = df_flow_done_period_eligible.copy()
        if 'Produto' not in _df_breakdown.columns and 'Projeto' in _df_breakdown.columns:
            _df_breakdown['Produto'] = _df_breakdown['Projeto'].apply(_pm_product_label)
        lead_by_produto = build_service_lead_time_breakdown(
            _df_breakdown, 'Produto', 'Produto'
        )
        lead_by_tipo = build_service_lead_time_breakdown(
            _df_breakdown, 'Tipo', 'Tipo de Item'
        )

        def _lt_breakdown_table(title, df_table, table_id):
            if df_table is None or df_table.empty:
                body = html.P('Sem dados suficientes para o recorte selecionado.',
                              style={'color': '#64748b', 'margin': 0})
            else:
                body = dash_table.DataTable(
                    id=table_id,
                    columns=[{"name": c, "id": c} for c in df_table.columns],
                    data=df_table.to_dict('records'),
                    style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
                    style_header={'backgroundColor': '#e2e8f0', 'fontWeight': 'bold'},
                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8fafc'}],
                    style_table={'overflowX': 'auto'},
                )
            return html.Div([
                html.H5(title, style={'marginTop': '0', 'marginBottom': '8px'}),
                body,
            ], style={
                'backgroundColor': '#ffffff',
                'border': '1px solid #e2e8f0',
                'borderRadius': '10px',
                'padding': '14px',
                'flex': '1',
                'minWidth': '280px',
            })

        def _lt_breakdown_chart(df_table, dimension_col, title):
            if df_table is None or df_table.empty:
                return html.Div()
            chart_df = df_table.copy().sort_values('Lead P85', ascending=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=chart_df[dimension_col],
                x=chart_df['Lead P50'],
                name='P50',
                orientation='h',
                marker_color='#27AE60',
                hovertemplate=f'{dimension_col}: %{{y}}<br>P50: %{{x:.1f}}d<extra></extra>',
            ))
            fig.add_trace(go.Bar(
                y=chart_df[dimension_col],
                x=chart_df['Lead P85'],
                name='P85',
                orientation='h',
                marker_color='#9B51E0',
                hovertemplate=f'{dimension_col}: %{{y}}<br>P85: %{{x:.1f}}d<extra></extra>',
            ))
            n_items = len(chart_df)
            bar_height = max(320, n_items * 36 + 120)
            fig.update_layout(
                title=title,
                template='plotly_white',
                barmode='group',
                xaxis_title='Lead Time (dias)',
                yaxis_title='',
                legend=dict(orientation='h', y=1.08, x=0.5, xanchor='center', yanchor='bottom'),
                height=bar_height,
                margin=dict(l=20, r=20, t=80, b=60),
            )
            return dcc.Graph(figure=fig)

        breakdown_by_produto_section = html.Div([
            html.H4("Lead Time por Produto", style={'textAlign': 'center', 'marginTop': '30px'}),
            html.Div([
                _lt_breakdown_table('Tabela: Lead Time por Produto', lead_by_produto, 'lt-breakdown-produto-table'),
            ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap', 'marginBottom': '8px'}),
            _lt_breakdown_chart(lead_by_produto, 'Produto', 'Lead Time P50 e P85 por Produto'),
        ])

        breakdown_by_tipo_section = html.Div([
            html.H4("Lead Time por Tipo de Item", style={'textAlign': 'center', 'marginTop': '30px'}),
            html.Div([
                _lt_breakdown_table('Tabela: Lead Time por Tipo de Item', lead_by_tipo, 'lt-breakdown-tipo-table'),
            ], style={'display': 'flex', 'gap': '16px', 'flexWrap': 'wrap', 'marginBottom': '8px'}),
            _lt_breakdown_chart(lead_by_tipo, 'Tipo de Item', 'Lead Time P50 e P85 por Tipo de Item'),
        ])

        return html.Div([
            html.H3("Lead Time", style={'textAlign': 'center'}),
            html.P(subtitle, style={'textAlign': 'center', 'color': '#666'}),
            dcc.Graph(figure=fig_lt_dist),
            dcc.Graph(figure=fig_lt_scatter),
            html.Hr(),
            html.H3("Análise Avançada de Fluxo", style={'textAlign': 'center'}),
            leadtime_selection_summary,
            html.P(
                (
                    "Filtro de etapas de Lead Time aplicado aos KPIs de Lead Time desta tela "
                    f"(amostra: {int(len(lead_time_selected))} itens elegíveis). "
                    "O ranking de gargalos por etapa permanece independente dessa seleção."
                ),
                style={'textAlign': 'center', 'color': '#555', 'marginBottom': '10px'}
            ),
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            html.H4("Indicador de Gargalo do Fluxo", style={'textAlign': 'center', 'marginTop': '10px'}),
            html.Div(bottlenecks_table, style={'width': '70%', 'margin': 'auto', 'marginBottom': '20px'}),
            dcc.Graph(figure=fig_bottlenecks),
            html.H4("Lead Time Breakdown", style={'textAlign': 'center', 'marginTop': '20px'}),
            lead_time_breakdown_component,
            html.H4("Lead Time Breakdown Semanal", style={'textAlign': 'center', 'marginTop': '20px'}),
            weekly_breakdown_component,
            lead_hist_component,
            html.H4("Bandas Percentílicas Exatas (Lead Time)", style={'textAlign': 'center', 'marginTop': '20px'}),
            lead_band_table_component,
            html.Hr(),
            html.H3("Lead Time por Produto e Tipo de Item", style={'textAlign': 'center', 'marginTop': '20px'}),
            breakdown_by_produto_section,
            breakdown_by_tipo_section,
        ])

    if tab == PORTFOLIO_TAB_VALUE:
        snapshot, df_portfolio, error = get_portfolio_snapshot()
        if error:
            return html.Div([
                html.H3('Painel de Portfólio', style={'textAlign': 'center'}),
                html.P(
                    f'Não foi possível carregar o CSV de portfólio: {error}',
                    style={'textAlign': 'center', 'color': '#b22222'}
                ),
                html.P(
                    'Gere/atualize o CSV com o script jira_portfolio_to_csv.py e tente novamente.',
                    style={'textAlign': 'center', 'color': '#666'}
                ),
            ], style={'padding': '20px'})

        df_portfolio_filtered, effective_portfolio_project, portfolio_filter_notes = apply_portfolio_module_filters(
            df_portfolio,
            projeto=projeto,
            tipo=tipo,
            classe_servico=classe_servico,
            responsavel=responsavel,
            portfolio_project=portfolio_project,
            portfolio_quarter=portfolio_quarter,
        )

        # Re-compute snapshot with filtered data
        snapshot = compute_portfolio_snapshot(df_portfolio_filtered, snapshot['updated_at'])

        groups = snapshot['groups']

        epicos_status = groups.get('epicos_por_team_status', pd.DataFrame())
        features_status = groups.get('features_por_team_status', pd.DataFrame())
        epicos_complexidade = groups.get('epicos_por_complexidade', pd.DataFrame())
        features_complexidade = groups.get('features_por_complexidade', pd.DataFrame())
        epicos_fluxo_etapas = groups.get('epicos_fluxo_etapas', pd.DataFrame())
        pendencias_q_por_time = groups.get('pendencias_q_por_time', pd.DataFrame())
        pendencias_breakdown = groups.get('pendencias_breakdown', pd.DataFrame())
        pendencias_detalhe = groups.get('pendencias_detalhe', pd.DataFrame())
        aging_us_20 = groups.get('aging_us_20', pd.DataFrame())
        aging_features_40 = groups.get('aging_features_40', pd.DataFrame())
        aging_us_comp_20 = groups.get('aging_us_comp_20', pd.DataFrame())
        aging_features_comp_40 = groups.get('aging_features_comp_40', pd.DataFrame())
        aging_buckets_por_team = groups.get('aging_buckets_por_team', pd.DataFrame())
        aging_por_tipo = groups.get('aging_por_tipo', pd.DataFrame())
        aging_por_projeto = groups.get('aging_por_projeto', pd.DataFrame())
        flow_health_summary = groups.get('flow_health_summary', pd.DataFrame())
        flow_health_por_team = groups.get('flow_health_por_team', pd.DataFrame())
        portfolio_health_scorecard = groups.get('portfolio_health_scorecard', pd.DataFrame())
        portfolio_health_dimension_summary = groups.get('portfolio_health_dimension_summary', pd.DataFrame())
        flow_distribution_by_type = groups.get('flow_distribution_by_type', pd.DataFrame())
        flow_distribution_by_status = groups.get('flow_distribution_by_status', pd.DataFrame())
        flow_distribution_by_team = groups.get('flow_distribution_by_team', pd.DataFrame())
        stage_load_summary = groups.get('stage_load_summary', pd.DataFrame())
        stage_load_detail = groups.get('stage_load_detail', pd.DataFrame())
        stage_limit_alerts = groups.get('stage_limit_alerts', pd.DataFrame())
        decision_queue_aging = groups.get('decision_queue_aging', pd.DataFrame())
        decision_queue_summary = groups.get('decision_queue_summary', pd.DataFrame())
        data_freshness_por_team_statuscat = groups.get('data_freshness_por_team_statuscat', pd.DataFrame())
        status_categoria_por_team = groups.get('status_categoria_por_team', pd.DataFrame())
        status_ranking_por_team = groups.get('status_ranking_por_team', pd.DataFrame())
        status_original_top = groups.get('status_original_top', pd.DataFrame())
        workflow_conformance_por_team = groups.get('workflow_conformance_por_team', pd.DataFrame())
        status_fora_workflow_top = groups.get('status_fora_workflow_top', pd.DataFrame())
        heatmap_team_status = groups.get('heatmap_team_status', pd.DataFrame())
        effort_features_por_team = groups.get('effort_features_por_team', pd.DataFrame())
        features_sem_effort_por_team = groups.get('features_sem_effort_por_team', pd.DataFrame())
        quality_por_team = groups.get('quality_por_team', pd.DataFrame())
        quality_summary = groups.get('quality_summary', pd.DataFrame())
        estrutura_cobertura_por_team = groups.get('estrutura_cobertura_por_team', pd.DataFrame())
        estrutura_cobertura_summary = groups.get('estrutura_cobertura_summary', pd.DataFrame())
        concentracao_team_share = groups.get('concentracao_team_share', pd.DataFrame())
        concentracao_epico_share = groups.get('concentracao_epico_share', pd.DataFrame())
        concentracao_summary = groups.get('concentracao_summary', pd.DataFrame())
        tipo_balanceamento = groups.get('tipo_balanceamento', pd.DataFrame())
        items_base = groups.get('items_base', pd.DataFrame())
        hist_tasks_sem_feature_por_team = groups.get('hist_tasks_sem_feature_por_team', pd.DataFrame())
        executive_tiles = groups.get('executive_tiles', pd.DataFrame())
        epicos_por_team_total = groups.get('epicos_por_team_total', pd.DataFrame())
        features_por_team_total = groups.get('features_por_team_total', pd.DataFrame())
        top_epicos_volume = groups.get('top_epicos_volume', pd.DataFrame())
        top_epicos_aging = groups.get('top_epicos_aging', pd.DataFrame())
        epicos_detalhe = groups.get('epicos_detalhe', pd.DataFrame())
        features_detalhe = groups.get('features_detalhe', pd.DataFrame())
        portfolio_alerts_detail = groups.get('portfolio_alerts_detail', pd.DataFrame())
        portfolio_alerts_indicator_summary = groups.get('portfolio_alerts_indicator_summary', pd.DataFrame())
        portfolio_alerts_severity_summary = groups.get('portfolio_alerts_severity_summary', pd.DataFrame())
        portfolio_alerts_by_team = groups.get('portfolio_alerts_by_team', pd.DataFrame())
        portfolio_alerts_by_project = groups.get('portfolio_alerts_by_project', pd.DataFrame())
        portfolio_alert_kpis = groups.get('portfolio_alert_kpis', pd.DataFrame())
        portfolio_extra_onepage_summary = groups.get('portfolio_extra_onepage_summary', pd.DataFrame())
        portfolio_technical_readiness_notes = groups.get('portfolio_technical_readiness_notes', pd.DataFrame())
        portfolio_technical_epic_summary = groups.get('portfolio_technical_epic_summary', pd.DataFrame())
        portfolio_technical_items_catalog = groups.get('portfolio_technical_items_catalog', pd.DataFrame())
        has_us_items = bool(groups.get('has_us_items', False))
        due_date_performance = groups.get('due_date_performance', pd.DataFrame())

        lead_time_por_tipo = groups.get('lead_time_por_tipo', pd.DataFrame())
        lead_time_por_team = groups.get('lead_time_por_team', pd.DataFrame())
        lead_time_distribution = groups.get('lead_time_distribution', pd.DataFrame())
        throughput_semanal = groups.get('throughput_semanal', pd.DataFrame())
        throughput_mensal = groups.get('throughput_mensal', pd.DataFrame())
        tema_distribuicao = groups.get('tema_distribuicao', pd.DataFrame())
        tema_team_heatmap = groups.get('tema_team_heatmap', pd.DataFrame())
        tema_status_dist = groups.get('tema_status_dist', pd.DataFrame())
        risk_distribuicao = groups.get('risk_distribuicao', pd.DataFrame())
        risk_por_tipo = groups.get('risk_por_tipo', pd.DataFrame())
        risk_por_team = groups.get('risk_por_team', pd.DataFrame())
        risk_aging = groups.get('risk_aging', pd.DataFrame())
        _p3_metrics = snapshot.get('metrics', {})
        lead_time_p50 = _p3_metrics.get('lead_time_p50')
        lead_time_p85 = _p3_metrics.get('lead_time_p85')
        lead_time_count = int(_p3_metrics.get('lead_time_count', 0))
        throughput_weekly_avg = _p3_metrics.get('throughput_weekly_avg', 0.0)
        throughput_monthly_avg = _p3_metrics.get('throughput_monthly_avg', 0.0)
        pct_com_tema = _p3_metrics.get('pct_com_tema_estrategico', 0.0)
        pct_com_risco = _p3_metrics.get('pct_com_risco', 0.0)

        selected_team = '__ALL__'
        df_portfolio_full_scope = df_portfolio_filtered.copy() if df_portfolio_filtered is not None else pd.DataFrame()

        def filter_by_team(df_source, team_col='Team'):
            if df_source is None or df_source.empty or selected_team == '__ALL__':
                return df_source
            if team_col not in df_source.columns:
                return df_source
            return df_source[df_source[team_col] == selected_team].copy()

        epicos_status = filter_by_team(epicos_status)
        features_status = filter_by_team(features_status)
        epicos_complexidade = filter_by_team(epicos_complexidade)
        features_complexidade = filter_by_team(features_complexidade)
        epicos_fluxo_etapas = filter_by_team(epicos_fluxo_etapas)
        pendencias_q_por_time = filter_by_team(pendencias_q_por_time)
        pendencias_breakdown = filter_by_team(pendencias_breakdown)
        pendencias_detalhe = filter_by_team(pendencias_detalhe)
        aging_us_20 = filter_by_team(aging_us_20)
        aging_features_40 = filter_by_team(aging_features_40)
        aging_us_comp_20 = filter_by_team(aging_us_comp_20)
        aging_features_comp_40 = filter_by_team(aging_features_comp_40)
        aging_buckets_por_team = filter_by_team(aging_buckets_por_team)
        status_categoria_por_team = filter_by_team(status_categoria_por_team)
        status_ranking_por_team = filter_by_team(status_ranking_por_team)
        flow_health_por_team = filter_by_team(flow_health_por_team)
        decision_queue_aging = filter_by_team(decision_queue_aging)
        data_freshness_por_team_statuscat = filter_by_team(data_freshness_por_team_statuscat)
        workflow_conformance_por_team = filter_by_team(workflow_conformance_por_team)
        heatmap_team_status = filter_by_team(heatmap_team_status)
        effort_features_por_team = filter_by_team(effort_features_por_team)
        features_sem_effort_por_team = filter_by_team(features_sem_effort_por_team)
        quality_por_team = filter_by_team(quality_por_team)
        estrutura_cobertura_por_team = filter_by_team(estrutura_cobertura_por_team)
        concentracao_team_share = filter_by_team(concentracao_team_share)
        hist_tasks_sem_feature_por_team = filter_by_team(hist_tasks_sem_feature_por_team)
        epicos_por_team_total = filter_by_team(epicos_por_team_total)
        features_por_team_total = filter_by_team(features_por_team_total)
        top_epicos_volume = filter_by_team(top_epicos_volume)
        top_epicos_aging = filter_by_team(top_epicos_aging)
        concentracao_epico_share = filter_by_team(concentracao_epico_share)
        epicos_detalhe = filter_by_team(epicos_detalhe)
        features_detalhe = filter_by_team(features_detalhe)
        portfolio_alerts_detail = filter_by_team(portfolio_alerts_detail)
        portfolio_alerts_by_team = filter_by_team(portfolio_alerts_by_team)
        if selected_team != '__ALL__' and portfolio_alerts_detail is not None and not portfolio_alerts_detail.empty:
            extra_scope = portfolio_alerts_detail[portfolio_alerts_detail['TipoAlerta'] == 'Tag EXTRA-ONEPAGE'].copy()
            if extra_scope.empty:
                portfolio_extra_onepage_summary = pd.DataFrame(columns=['TipoItem', 'TotalItens'])
            else:
                portfolio_extra_onepage_summary = (
                    extra_scope.groupby(['TipoItem'], dropna=False)
                    .agg(TotalItens=('ItemID', 'nunique'))
                    .reset_index()
                    .sort_values(['TotalItens', 'TipoItem'], ascending=[False, True], ignore_index=True)
                )
        portfolio_technical_epic_summary = filter_by_team(portfolio_technical_epic_summary)
        portfolio_technical_items_catalog = filter_by_team(portfolio_technical_items_catalog)
        lead_time_por_team = filter_by_team(lead_time_por_team, team_col='TeamDisplay')
        lead_time_distribution = filter_by_team(lead_time_distribution, team_col='TeamDisplay')
        tema_team_heatmap = filter_by_team(tema_team_heatmap, team_col='TeamDisplay')
        risk_por_team = filter_by_team(risk_por_team, team_col='TeamDisplay')
        if items_base is None or items_base.empty:
            items_base_scope = pd.DataFrame()
        else:
            items_base_scope = items_base.copy()
            if selected_team != '__ALL__' and 'TeamDisplay' in items_base_scope.columns:
                items_base_scope = items_base_scope[items_base_scope['TeamDisplay'] == selected_team].copy()
        if not df_portfolio_full_scope.empty and selected_team != '__ALL__' and 'Team' in df_portfolio_full_scope.columns:
            df_portfolio_full_scope = df_portfolio_full_scope[
                df_portfolio_full_scope['Team'].fillna('').astype(str).str.strip() == selected_team
            ].copy()
        if selected_team != '__ALL__' and portfolio_alerts_by_project is not None and not portfolio_alerts_by_project.empty:
            scoped_projects = set(portfolio_alerts_detail['Projeto'].dropna().astype(str)) if portfolio_alerts_detail is not None and not portfolio_alerts_detail.empty else set()
            if scoped_projects:
                portfolio_alerts_by_project = portfolio_alerts_by_project[
                    portfolio_alerts_by_project['Projeto'].fillna('').astype(str).isin(scoped_projects)
                ].copy()

        def parse_int_threshold(v, default):
            try:
                return max(0, int(float(v)))
            except Exception:
                return int(default)

        def parse_status_list(raw, fallback):
            txt = str(raw or '').strip()
            if not txt:
                return list(fallback)
            vals = [t.strip() for t in re.split(r'[;,\n]+', txt) if str(t).strip()]
            return vals or list(fallback)

        def parse_json_config(raw, fallback):
            txt = str(raw or '').strip()
            if not txt:
                return fallback
            try:
                obj = json.loads(txt)
                return obj if isinstance(obj, dict) else fallback
            except Exception:
                return fallback

        cfg_backlog_15 = parse_int_threshold(pf_backlog_15, 15)
        cfg_backlog_30 = parse_int_threshold(pf_backlog_30, 30)
        cfg_fresh_15 = parse_int_threshold(pf_fresh_15, 15)
        cfg_fresh_30 = parse_int_threshold(pf_fresh_30, 30)
        cfg_decision_statuses = parse_status_list(pf_decision_statuses, ['Triagem', 'Backlog', 'Business Review', 'READY FOR DEVELOPMENT'])
        cfg_workflow_statuses = parse_status_list(pf_workflow_statuses, ['Triagem', 'Backlog', 'To Do', 'Todo', 'Business Review', 'READY FOR DEVELOPMENT', 'In Progress', 'In Progess', 'Ready', 'Homolog', 'Staging', 'Desenvolvimento', 'Concluído', 'Concluída', 'Done', 'Closed', 'Resolved', 'Cancelled'])
        cfg_sla_aging = parse_json_config(pf_sla_aging_json, {'tipo': {'Épico': 30, 'Feature': 20}, 'status': {'Triagem': 7, 'Backlog': 15, 'Business Review': 10}})
        cfg_target_mix = parse_json_config(pf_target_mix_json, {'global': {'Épico': 70, 'Feature': 30}})
        available_teams = []
        for frame in [epicos_por_team_total, features_por_team_total]:
            if frame is None or frame.empty or 'Team' not in frame.columns:
                continue
            for t in frame['Team'].dropna().astype(str):
                team = t.strip()
                if team and team not in available_teams:
                    available_teams.append(team)

        if selected_team != '__ALL__':
            if not executive_tiles.empty:
                sem_team_val = int((selected_team == 'Sem TEAM'))
                executive_tiles = executive_tiles.copy()
                executive_tiles.loc[executive_tiles['Indicador'] == 'Sem TEAM', 'Valor'] = sem_team_val

        def grouped_chart(df_group, x_col, y_col, color_col, title):
            if df_group is None or df_group.empty:
                return html.Div([
                    html.H4(title),
                    html.P('Sem dados para exibição.')
                ])
            fig = px.bar(
                df_group,
                x=x_col,
                y=y_col,
                color=color_col,
                barmode='group',
                template='plotly_white',
                title=title
            )
            fig.update_layout(height=360, margin=dict(t=50, b=80), xaxis_tickangle=-30)
            return dcc.Graph(figure=fig)

        def threshold_color(count, threshold_key, empty_gray=False):
            c = int(count or 0)
            if empty_gray and c == 0:
                return '#d8d8d8'
            limits = PORTFOLIO_COLOR_THRESHOLDS.get(threshold_key) or {'green_max': 0, 'yellow_max': 0}
            if c <= int(limits.get('green_max', 0)):
                return '#2e7d32'
            if c <= int(limits.get('yellow_max', 0)):
                return '#f9a825'
            return '#c62828'

        def render_tile(label, value, threshold_key, subtitle='Work items', empty_gray=False):
            bg = threshold_color(value, threshold_key=threshold_key, empty_gray=empty_gray)
            fg = '#111' if bg in {'#f9a825', '#d8d8d8'} else 'white'
            return html.Div([
                html.Div(str(label), style={'fontSize': '16px', 'fontWeight': 'bold'}),
                html.Div(str(int(value or 0)), style={'fontSize': '54px', 'lineHeight': '1.1'}),
                html.Div(subtitle, style={'fontSize': '13px', 'opacity': 0.9}),
            ], style={
                'backgroundColor': bg,
                'color': fg,
                'padding': '12px',
                'borderRadius': '4px',
                'minHeight': '150px',
                'display': 'flex',
                'flexDirection': 'column',
                'justifyContent': 'space-between',
            })

        def render_tiles_by_team(df_metric, title, threshold_key):
            cards = []
            if df_metric is None or df_metric.empty:
                if not available_teams:
                    return html.Div([html.H4(title), html.P('Sem dados para exibição.')])
                cards = [
                    render_tile(team, 0, threshold_key=threshold_key, empty_gray=True)
                    for team in available_teams
                ]
            else:
                cards = [
                    render_tile(row['Team'], row['WorkItems'], threshold_key=threshold_key)
                    for _, row in df_metric.sort_values('WorkItems', ascending=False).iterrows()
                ]
            return html.Div([
                html.H4(title, style={'textAlign': 'left'}),
                html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fill, minmax(160px, 1fr))',
                    'gap': '10px'
                })
            ], style={'marginTop': '16px'})

        def render_q_pendencias_grid(df_q, df_breakdown, df_detail):
            if df_q is None or df_q.empty:
                return html.Div([html.H4('Pendências por Faixa de Aging e TEAM'), html.P('Sem dados para exibição.')])
            quadrantes = [
                PORTFOLIO_PENDING_BUCKET_1,
                PORTFOLIO_PENDING_BUCKET_2,
                PORTFOLIO_PENDING_BUCKET_3,
            ]
            blocks = []
            for q in quadrantes:
                d = df_q[df_q['Quadrante'] == q].copy()
                cards = []
                if d.empty:
                    cards.append(render_tile('Sem dados', 0, threshold_key=q, empty_gray=True))
                else:
                    for _, row in d.sort_values('WorkItems', ascending=False).iterrows():
                        cards.append(render_tile(row['Team'], row['WorkItems'], threshold_key=q))
                blocks.append(html.Div([
                    html.H4(q, style={'minWidth': '150px'}),
                    html.Div(cards, style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fill, minmax(160px, 1fr))',
                        'gap': '10px',
                        'width': '100%'
                    })
                ], style={'display': 'flex', 'gap': '16px', 'alignItems': 'flex-start', 'marginBottom': '14px'}))
            notes = html.Div([
                html.P('Pendência = item aberto no snapshot de portfólio (status não concluído).', style={'margin': '0 0 6px 0'}),
                html.P('Faixas: 0-15 dias sem alteração | 16-30 dias | acima de 30 dias.', style={'margin': '0'}),
            ], style={
                'backgroundColor': '#f5f5f5',
                'borderLeft': '4px solid #616161',
                'padding': '10px 12px',
                'marginBottom': '14px',
            })
            sections = [
                html.H3('Indicador 1 - Pendências por Faixa de Aging e TEAM', style={'textAlign': 'left'}),
                notes,
                *blocks,
            ]
            if df_breakdown is not None and not df_breakdown.empty:
                sections.append(
                    portfolio_table_component(
                        df_breakdown.copy(),
                        'Composição das pendências por quadrante, tipo e categoria de status',
                        'table-portfolio-pendencias-breakdown'
                    )
                )
            if df_detail is not None and not df_detail.empty:
                sections.append(
                    portfolio_table_component(
                        df_detail.copy(),
                        'Itens que compõem as pendências de portfólio',
                        'table-portfolio-pendencias-detalhe'
                    )
                )
            return html.Div(sections, style={'marginTop': '24px'})

        def render_executive_tiles(df_exec):
            if df_exec is None or df_exec.empty:
                return html.Div([html.H3('Indicador 3 - Resumo Executivo'), html.P('Sem dados para exibição.')])
            _exec_colors = {
                'ok':    {'bg': '#e8f5e9', 'border': '#2e7d32', 'text': '#1b5e20'},
                'alerta':{'bg': '#fff3e0', 'border': '#e65100', 'text': '#bf360c'},
                'risco': {'bg': '#fce4ec', 'border': '#ad1457', 'text': '#880e4f'},
                'info':  {'bg': '#e3f2fd', 'border': '#1565c0', 'text': '#0d47a1'},
            }
            _EXEC_GROUPS = [
                {'label': 'Escopo do Portfólio',     'indicators': ['Épicos', 'Features']},
                {'label': 'Status de Prazo',          'indicators': ['Em dia', 'Atrasadas', 'Sem TEAM']},
                {'label': 'Qualidade Hierárquica',    'indicators': ['Estado divergente', 'Features sem épico', 'Épicos sem features', 'Hist./Tasks sem feature tática', 'Hist./Tasks órfãos']},
            ]
            row_lookup = {str(r['Indicador']): r for _, r in df_exec.iterrows()}
            sections = [html.H3('Indicador 3 - Resumo Executivo', style={'textAlign': 'left'})]
            for group in _EXEC_GROUPS:
                cards = []
                for indicador in group['indicators']:
                    row = row_lookup.get(indicador)
                    if row is None:
                        continue
                    cfg = _exec_colors.get(str(row.get('Tipo', 'info')), _exec_colors['info'])
                    cards.append(html.Div([
                        html.Div(indicador, style={'fontSize': '11px', 'fontWeight': '700', 'color': cfg['text'], 'textTransform': 'uppercase', 'letterSpacing': '0.3px'}),
                        html.Div(str(int(row['Valor'])), style={'fontSize': '28px', 'fontWeight': '800', 'color': cfg['text'], 'lineHeight': '1.1', 'marginTop': '4px'}),
                    ], style={
                        'padding': '10px 14px',
                        'borderRadius': '10px',
                        'backgroundColor': cfg['bg'],
                        'border': f"1px solid {cfg['border']}",
                        'minHeight': '90px',
                    }))
                if not cards:
                    continue
                sections.append(html.Div([
                    html.Div(group['label'], style={'fontSize': '13px', 'fontWeight': '700', 'color': '#334155', 'marginBottom': '8px'}),
                    html.Div(cards, style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(150px, 1fr))', 'gap': '8px'}),
                ], style={'marginBottom': '16px'}))
            sections.append(html.P(
                'Estado divergente = features sem épico + épicos sem features (quebra de relacionamento entre níveis).',
                style={'marginTop': '8px', 'color': '#555'}
            ))
            return html.Div(sections, style={'marginTop': '24px'})

        def render_portfolio_alerts(
            df_kpis,
            df_severity,
            df_indicator,
            df_detail,
            df_team,
            df_project,
            df_extra_onepage,
            df_tech_notes,
            df_tech_epic_summary,
            df_tech_catalog,
        ):
            if df_detail is None or df_detail.empty:
                return html.Div([
                    html.H3('Alertas de Portfólio', style={'textAlign': 'left'}),
                    html.P('Sem alertas no escopo atual.', style={'color': '#666'}),
                    portfolio_table_component(
                        df_extra_onepage.copy() if df_extra_onepage is not None else pd.DataFrame(),
                        'Itens com tag EXTRA-ONEPAGE por tipo',
                        'table-portfolio-extra-onepage-summary-empty'
                    ),
                    portfolio_table_component(
                        df_tech_notes.copy() if df_tech_notes is not None else pd.DataFrame(),
                        'Prontidão técnica (pendências de dados)',
                        'table-portfolio-technical-readiness-notes-empty'
                    ),
                ], style={'paddingTop': '10px'})

            severity_colors = {
                'Critico': '#b71c1c',
                'Alerta': '#ef6c00',
                'Monitorar': '#1565c0',
            }

            _ALERT_GROUPS = [
                {
                    'label': 'Severidade Geral',
                    'indicators': ['Ocorrências críticas', 'Ocorrências alerta', 'Ocorrências monitorar', 'Itens únicos com alerta'],
                    'border': '#b71c1c',
                },
                {
                    'label': 'Hierarquia & Decomposição',
                    'indicators': ['Épicos sem feature', 'Features sem story/task', 'Features sem épico', 'Stories/Tasks órfãos', 'Prazo crítico sem decomposição'],
                    'border': '#ef6c00',
                },
                {
                    'label': 'Prazos & Vencimentos',
                    'indicators': ['Itens vencidos', 'Itens vencendo em até 7d', 'Épicos sem prazo', 'Épicos em risco de prazo', 'Épicos c/ features atrasadas'],
                    'border': '#b71c1c',
                },
                {
                    'label': 'Bloqueios & Paralisações',
                    'indicators': ['Itens bloqueados', 'Stories/Tasks parados', 'Épicos parados', 'Features paradas', 'Épicos em descoberta parados', 'Features em descoberta paradas', 'Gargalos de handoff'],
                    'border': '#ef6c00',
                },
                {
                    'label': 'Risco & Capacidade',
                    'indicators': ['Times c/ WIP excessivo', 'Times c/ concentração de risco', 'Itens sem prioridade'],
                    'border': '#6a1b9a',
                },
                {
                    'label': 'Cobertura Técnica',
                    'indicators': ['Épicos sem arquitetura', 'Épicos sem infra', 'Épicos sem segurança'],
                    'border': '#1565c0',
                },
                {
                    'label': 'Tagging & Processo',
                    'indicators': ['Itens com tag EXTRA-ONEPAGE'],
                    'border': '#455a64',
                },
            ]

            kpi_lookup = {}
            if df_kpis is not None and not df_kpis.empty:
                for _, row in df_kpis.iterrows():
                    label = str(row.get('Indicador', '')).strip()
                    value = int(pd.to_numeric(row.get('Valor'), errors='coerce') or 0)
                    label_lower = label.lower()
                    bg = '#455a64'
                    if any(t in label_lower for t in ('crítica', 'critic', 'vencidos', 'bloqueados', 'features atrasadas', 'risco de prazo', 'prazo crítico')):
                        bg = severity_colors['Critico']
                    elif any(t in label_lower for t in ('alerta', 'sem feature', 'sem story', 'sem épico', 'parad', 'sem prazo', 'em descoberta', 'concentração de risco', 'órfã', 'handoff')):
                        bg = severity_colors['Alerta']
                    elif any(t in label_lower for t in ('monitorar', '7d', 'prioridade')):
                        bg = severity_colors['Monitorar']
                    elif 'wip excessivo' in label_lower:
                        bg = '#6a1b9a'
                    kpi_lookup[label] = (value, bg)

            grouped_kpi_sections = []
            for _grp in _ALERT_GROUPS:
                _cards = []
                for _ind in _grp['indicators']:
                    if _ind in kpi_lookup:
                        _val, _bg = kpi_lookup[_ind]
                        _cards.append(
                            create_kpi_card(_ind, f"{_val}", class_name='', **portfolio_kpi_style(_bg))
                        )
                if not _cards:
                    continue
                _bc = _grp['border']
                grouped_kpi_sections.append(
                    html.Div([
                        html.Div(
                            _grp['label'],
                            style={
                                'fontSize': '11px',
                                'fontWeight': '700',
                                'textTransform': 'uppercase',
                                'letterSpacing': '0.07em',
                                'color': _bc,
                                'borderLeft': f'3px solid {_bc}',
                                'paddingLeft': '8px',
                                'marginBottom': '8px',
                            }
                        ),
                        html.Div(_cards, style={
                            'display': 'grid',
                            'gridTemplateColumns': 'repeat(auto-fill, minmax(160px, 1fr))',
                            'gap': '8px',
                        }),
                    ], style={
                        'background': '#f8f9fa',
                        'border': f'1px solid {_bc}33',
                        'borderRadius': '6px',
                        'padding': '12px 14px',
                    })
                )

            severity_section = html.Div()
            if df_severity is not None and not df_severity.empty:
                sev_plot = df_severity.copy()
                sev_plot['Cor'] = sev_plot['Severidade'].map(severity_colors).fillna('#455a64')
                fig = px.bar(
                    sev_plot,
                    x='Severidade',
                    y='Ocorrencias',
                    color='Severidade',
                    color_discrete_map=severity_colors,
                    text='Ocorrencias',
                    template='plotly_white',
                    title='Distribuição de alertas por severidade'
                )
                fig.update_layout(height=340, showlegend=False, margin=dict(t=60, b=40))
                severity_section = dcc.Graph(figure=fig)

            indicator_table = portfolio_table_component(
                df_indicator.copy() if df_indicator is not None else pd.DataFrame(),
                'Ocorrências por tipo de alerta e severidade',
                'table-portfolio-alert-indicator-summary'
            )
            detail_table = portfolio_table_component(
                df_detail.copy(),
                'Itens que compõem os alertas de portfólio',
                'table-portfolio-alert-detail'
            )
            team_table = portfolio_table_component(
                df_team.copy() if df_team is not None else pd.DataFrame(),
                'Alertas por TEAM',
                'table-portfolio-alert-team'
            )
            project_table = portfolio_table_component(
                df_project.copy() if df_project is not None else pd.DataFrame(),
                'Alertas por Projeto',
                'table-portfolio-alert-project'
            )
            extra_onepage_table = portfolio_table_component(
                df_extra_onepage.copy() if df_extra_onepage is not None else pd.DataFrame(),
                'Itens com tag EXTRA-ONEPAGE por tipo',
                'table-portfolio-extra-onepage-summary'
            )
            tech_epic_summary_table = portfolio_table_component(
                df_tech_epic_summary.copy() if df_tech_epic_summary is not None else pd.DataFrame(),
                'Cobertura técnica proxy por épico',
                'table-portfolio-technical-epic-summary'
            )
            tech_catalog_table = portfolio_table_component(
                df_tech_catalog.copy() if df_tech_catalog is not None else pd.DataFrame(),
                'Catálogo de itens técnicos detectados no snapshot',
                'table-portfolio-technical-items-catalog'
            )
            tech_table = portfolio_table_component(
                df_tech_notes.copy() if df_tech_notes is not None else pd.DataFrame(),
                'Prontidão técnica (pendências de dados)',
                'table-portfolio-technical-readiness-notes'
            )

            return html.Div([
                html.H3('Alertas de Portfólio', style={'textAlign': 'left'}),
                html.P(
                    'Fase 1: alertas implementados apenas com o snapshot atual do portfólio. Custos e prontidão técnica factual ficam para evolução do contrato de dados.',
                    style={'color': '#666', 'marginBottom': '10px'}
                ),
                html.Div(grouped_kpi_sections, style={
                    'display': 'flex',
                    'flexDirection': 'column',
                    'gap': '10px',
                }),
                severity_section,
                indicator_table,
                extra_onepage_table,
                html.Div([
                    html.Div(team_table, className='six columns'),
                    html.Div(project_table, className='six columns'),
                ], className='row', style={'marginTop': '10px'}),
                detail_table,
                tech_epic_summary_table,
                tech_catalog_table,
                tech_table,
            ], style={'paddingTop': '10px'})

        def render_team_total_tiles(df_team, value_col, title, color='#1565c0'):
            if df_team is None or df_team.empty:
                return html.Div([html.H4(title), html.P('Sem dados para exibição.')])
            cards = []
            for _, row in df_team.sort_values(value_col, ascending=False).iterrows():
                cards.append(html.Div([
                    html.Div(str(row['Team']), style={'fontSize': '16px', 'fontWeight': 'bold'}),
                    html.Div(str(int(row[value_col] or 0)), style={'fontSize': '54px', 'lineHeight': '1.1'}),
                    html.Div('Work items', style={'fontSize': '13px', 'opacity': 0.9}),
                ], style={
                    'backgroundColor': color,
                    'color': 'white',
                    'padding': '12px',
                    'borderRadius': '4px',
                    'minHeight': '150px',
                }))
            return html.Div([
                html.H4(title, style={'textAlign': 'left'}),
                html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fill, minmax(160px, 1fr))',
                    'gap': '10px'
                })
            ], style={'marginTop': '12px'})

        def render_effort_distribution(df_effort):
            if df_effort is None or df_effort.empty:
                return html.Div([html.H3('Distribuição de Effort T-shirt'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            fig_effort_team = px.bar(
                df_effort,
                x='Team',
                y='QtdFeatures',
                color='EffortTShirtDisplay',
                barmode='stack',
                template='plotly_white',
                title='Distribuição de Effort T-shirt Size por TEAM (Features)',
            )
            fig_effort_team.update_layout(height=380, margin=dict(t=60, b=80), xaxis_tickangle=-25, legend_title_text='Effort')
            effort_ranking = (
                df_effort.groupby('EffortTShirtDisplay', as_index=False)['QtdFeatures']
                .sum()
                .sort_values('QtdFeatures', ascending=False, ignore_index=True)
                .rename(columns={'EffortTShirtDisplay': 'Effort T-shirt', 'QtdFeatures': 'Features'})
            )
            return html.Div([
                html.H3('Distribuição de Effort T-shirt', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig_effort_team),
                portfolio_table_component(effort_ranking, 'Distribuição de Effort T-shirt por Feature (contagem)', 'table-portfolio-effort-distribuicao'),
            ], style={'marginTop': '24px'})

        def render_aging_buckets(df_aging):
            if df_aging is None or df_aging.empty:
                return html.Div([html.H3('Aging por Buckets'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            bucket_order = ['0-7', '8-15', '16-30', '31-60', '60+', 'Sem data']
            bucket_color_map = {
                '0-7': '#2e7d32',      # verde
                '8-15': '#f9a825',     # amarelo
                '16-30': '#ef6c00',    # laranja
                '31-60': '#c62828',    # vermelho
                '60+': '#8e0000',      # vermelho escuro
                'Sem data': '#90a4ae', # neutro
            }
            df_plot = df_aging.copy()
            df_plot['AgingBucket'] = (
                df_plot['AgingBucket']
                .fillna('Sem data')
                .astype(str)
                .str.strip()
                .replace({'': 'Sem data'})
            )
            present_buckets = [b for b in bucket_order if (df_plot['AgingBucket'] == b).any()]
            if not present_buckets:
                present_buckets = ['Sem data']
            df_plot['AgingBucket'] = pd.Categorical(df_plot['AgingBucket'], categories=present_buckets, ordered=True)
            df_plot = df_plot.sort_values(['Team', 'AgingBucket'])
            fig_aging = px.bar(
                df_plot,
                x='Team',
                y='WorkItems',
                color='AgingBucket',
                barmode='stack',
                template='plotly_white',
                title='Aging por buckets detalhados (itens abertos) por TEAM',
                color_discrete_map=bucket_color_map,
                category_orders={'AgingBucket': present_buckets}
            )
            fig_aging.update_layout(height=380, margin=dict(t=60, b=80), xaxis_tickangle=-25, legend_title_text='Bucket')
            return html.Div([
                html.H3('Aging por Buckets', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig_aging),
                portfolio_table_component(df_plot.rename(columns={'AgingBucket': 'Bucket'}), 'Aging detalhado por TEAM', 'table-portfolio-aging-buckets'),
            ], style={'marginTop': '24px'})

        def render_status_ranking(df_status_cat, df_status_rank):
            if (df_status_cat is None or df_status_cat.empty) and (df_status_rank is None or df_status_rank.empty):
                return html.Div([html.H3('Ranking de Status por TEAM'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            blocks = []
            if df_status_cat is not None and not df_status_cat.empty:
                fig_status = px.bar(
                    df_status_cat,
                    x='Team',
                    y='WorkItems',
                    color='StatusCategoria',
                    barmode='stack',
                    template='plotly_white',
                    title='%/contagem de itens por categoria de status (TEAM)'
                )
                fig_status.update_layout(height=380, margin=dict(t=60, b=80), xaxis_tickangle=-25, legend_title_text='Categoria')
                blocks.append(dcc.Graph(figure=fig_status))
            if df_status_rank is not None and not df_status_rank.empty:
                rank_cols = [c for c in ['Team', 'TotalItems', '% Backlog', '% Em progresso', '% Concluído', '% Não mapeado', 'Backlog', 'Em progresso', 'Concluído', 'Não mapeado'] if c in df_status_rank.columns]
                blocks.append(
                    portfolio_table_component(
                        df_status_rank[rank_cols].copy(),
                        'Ranking de status por TEAM (% backlog / em progresso / concluído / não mapeado)',
                        'table-portfolio-status-ranking'
                    )
                )
            return html.Div([
                html.H3('Ranking de Status por TEAM', style={'textAlign': 'left'}),
                *blocks
            ], style={'marginTop': '24px'})

        def render_heatmap_team_status(df_heatmap):
            if df_heatmap is None or df_heatmap.empty:
                return html.Div([html.H3('Heatmap TEAM x StatusCategoria'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            pivot = (
                df_heatmap.pivot_table(index='Team', columns='StatusCategoria', values='WorkItems', aggfunc='sum', fill_value=0)
            )
            # Ordem estável para leitura.
            ordered_cols = [c for c in ['Backlog', 'Em progresso', 'Concluído', 'Não mapeado'] if c in pivot.columns] + [c for c in pivot.columns if c not in {'Backlog', 'Em progresso', 'Concluído', 'Não mapeado'}]
            pivot = pivot[ordered_cols]
            fig = px.imshow(
                pivot,
                text_auto=True,
                aspect='auto',
                color_continuous_scale='Blues',
                labels=dict(x='StatusCategoria', y='TEAM', color='Itens'),
                title='Heatmap TEAM x StatusCategoria (contagem)'
            )
            fig.update_layout(height=max(320, 34 * max(1, len(pivot.index)) + 140), margin=dict(t=60, b=60))
            table_df = pivot.reset_index()
            return html.Div([
                html.H3('Heatmap TEAM x StatusCategoria', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(table_df, 'Matriz TEAM x StatusCategoria', 'table-portfolio-heatmap-team-status')
            ], style={'marginTop': '24px'})

        def render_features_sem_effort(df_sem_effort):
            if df_sem_effort is None or df_sem_effort.empty:
                return html.Div([html.H3('Features sem Effort por TEAM'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            df_plot = df_sem_effort.sort_values(['% Sem Effort', 'FeaturesSemEffort'], ascending=[False, False]).copy()
            fig = px.bar(
                df_plot,
                x='Team',
                y='FeaturesSemEffort',
                color='% Sem Effort',
                template='plotly_white',
                title='Features sem Effort por TEAM (contagem e severidade em %)',
                color_continuous_scale='OrRd'
            )
            fig.update_layout(height=360, margin=dict(t=60, b=80), xaxis_tickangle=-25)
            fig.update_traces(
                customdata=df_plot[['FeaturesTotal', '% Sem Effort', '% Com Effort']].to_numpy(),
                hovertemplate='TEAM: %{x}<br>Sem Effort: %{y}<br>Total Features: %{customdata[0]}<br>% Sem Effort: %{customdata[1]}%<br>% Com Effort: %{customdata[2]}%<extra></extra>'
            )
            return html.Div([
                html.H3('Features sem Effort por TEAM', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(df_plot, 'Cobertura de Effort por TEAM (features)', 'table-portfolio-features-sem-effort-team')
            ], style={'marginTop': '24px'})

        def render_effort_aging_staleness(df_features_detail):
            if df_features_detail is None or df_features_detail.empty or 'Effort T-shirt' not in df_features_detail.columns:
                return html.Div([html.H3('Effort x Aging'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = df_features_detail.copy()
            base['Effort T-shirt'] = base['Effort T-shirt'].fillna('').astype(str).str.strip()
            base.loc[base['Effort T-shirt'] == '', 'Effort T-shirt'] = 'Sem estimativa'
            base['DiasSemMovimentacao'] = pd.to_numeric(base.get('DiasSemMovimentacao'), errors='coerce')
            if base['DiasSemMovimentacao'].dropna().empty:
                return html.Div([html.H3('Effort x Aging'), html.P('Sem dados de aging nas features.')], style={'marginTop': '20px'})
            summary = (
                base.groupby('Effort T-shirt', dropna=False)['DiasSemMovimentacao']
                .agg(Features='count', Aging_Medio='mean', Aging_Mediano='median', Aging_Max='max')
                .reset_index()
            )
            p90 = base.groupby('Effort T-shirt', dropna=False)['DiasSemMovimentacao'].quantile(0.90).reset_index(name='Aging_P90')
            summary = summary.merge(p90, on='Effort T-shirt', how='left')
            summary = summary.rename(columns={'Aging_Medio': 'Aging Médio', 'Aging_Mediano': 'Aging Mediano', 'Aging_Max': 'Aging Máx', 'Aging_P90': 'Aging P90'})
            for c in ['Aging Médio', 'Aging Mediano', 'Aging Máx', 'Aging P90']:
                summary[c] = pd.to_numeric(summary[c], errors='coerce').round(1)
            summary = summary.sort_values(['Aging P90', 'Features'], ascending=[False, False], ignore_index=True)

            stale = base.groupby('Effort T-shirt', dropna=False).size().reset_index(name='FeaturesTotal')
            stale15 = base[base['DiasSemMovimentacao'] > 15].groupby('Effort T-shirt', dropna=False).size().reset_index(name='SemMov15d')
            stale30 = base[base['DiasSemMovimentacao'] > 30].groupby('Effort T-shirt', dropna=False).size().reset_index(name='SemMov30d')
            stale = stale.merge(stale15, on='Effort T-shirt', how='left').merge(stale30, on='Effort T-shirt', how='left')
            stale[['SemMov15d', 'SemMov30d']] = stale[['SemMov15d', 'SemMov30d']].fillna(0).astype(int)
            stale['% SemMov15d'] = (stale['SemMov15d'] / stale['FeaturesTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
            stale['% SemMov30d'] = (stale['SemMov30d'] / stale['FeaturesTotal'].replace(0, np.nan) * 100).fillna(0).round(1)
            stale = stale.sort_values(['% SemMov30d', '% SemMov15d', 'FeaturesTotal'], ascending=[False, False, False], ignore_index=True)

            fig = px.bar(summary, x='Effort T-shirt', y='Aging P90', color='Features', template='plotly_white',
                         title='Effort x Aging (P90 de dias sem movimentação)')
            fig.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            return html.Div([
                html.H3('Effort x Aging', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(summary, 'Effort x aging (features)', 'table-portfolio-effort-aging'),
                portfolio_table_component(stale, '% sem movimentação 15/30 dias por effort', 'table-portfolio-effort-stale'),
            ], style={'marginTop': '24px'})

        def render_aging_por_tipo_projeto(df_tipo, df_projeto):
            if (df_tipo is None or df_tipo.empty) and (df_projeto is None or df_projeto.empty):
                return html.Div([html.H3('Aging por Tipo/Projeto'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            severity_scale = ['#2e7d32', '#f9a825', '#c62828']
            blocks = []
            if df_tipo is not None and not df_tipo.empty:
                fig_tipo = px.bar(
                    df_tipo.sort_values(['Aging Médio', 'QtdItensAbertos'], ascending=[False, False]),
                    x='Tipo',
                    y='Aging Médio',
                    color='QtdItensAbertos',
                    template='plotly_white',
                    title='Aging médio por Tipo (itens abertos)',
                    color_continuous_scale=severity_scale
                )
                fig_tipo.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-25)
                blocks.append(dcc.Graph(figure=fig_tipo))
                blocks.append(portfolio_table_component(df_tipo.copy(), 'Aging por Tipo (abertos)', 'table-portfolio-aging-por-tipo'))
            if df_projeto is not None and not df_projeto.empty:
                fig_proj = px.bar(
                    df_projeto.sort_values(['Aging Médio', 'QtdItensAbertos'], ascending=[False, False]),
                    x='Projeto',
                    y='Aging Médio',
                    color='QtdItensAbertos',
                    template='plotly_white',
                    title='Aging médio por Projeto (itens abertos)',
                    color_continuous_scale=severity_scale
                )
                fig_proj.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-25)
                blocks.append(dcc.Graph(figure=fig_proj))
                blocks.append(portfolio_table_component(df_projeto.copy(), 'Aging por Projeto (abertos)', 'table-portfolio-aging-por-projeto'))
            return html.Div([
                html.H3('Aging por Tipo/Projeto', style={'textAlign': 'left'}),
                *blocks
            ], style={'marginTop': '24px'})

        def render_concentracao_epicos(df_top_volume, df_top_aging):
            if (df_top_volume is None or df_top_volume.empty) and (df_top_aging is None or df_top_aging.empty):
                return html.Div([html.H3('Concentração de Épicos'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            sections = []
            if df_top_volume is not None and not df_top_volume.empty:
                fig_vol = px.bar(
                    df_top_volume.head(10).copy().sort_values('QtdItensFluxo', ascending=True),
                    x='QtdItensFluxo',
                    y='EpicID',
                    orientation='h',
                    color='Team',
                    template='plotly_white',
                    title='Top Épicos por Volume (itens de fluxo)',
                    hover_data=['Titulo', 'QtdFeatures', 'AgingDiasSemAlteracao', 'Status']
                )
                fig_vol.update_layout(height=420, margin=dict(l=100, r=40, t=60, b=40))
                sections.append(dcc.Graph(figure=fig_vol))
                sections.append(portfolio_table_component(df_top_volume.copy(), 'Top Épicos por volume', 'table-portfolio-top-epicos-volume'))
            if df_top_aging is not None and not df_top_aging.empty:
                fig_age = px.bar(
                    df_top_aging.head(10).copy().sort_values('AgingDiasSemAlteracao', ascending=True),
                    x='AgingDiasSemAlteracao',
                    y='EpicID',
                    orientation='h',
                    color='Team',
                    template='plotly_white',
                    title='Top Épicos por Aging (abertos)',
                    hover_data=['Titulo', 'QtdItensFluxo', 'QtdFeatures', 'Status']
                )
                fig_age.update_layout(height=420, margin=dict(l=100, r=40, t=60, b=40))
                sections.append(dcc.Graph(figure=fig_age))
                sections.append(portfolio_table_component(df_top_aging.copy(), 'Top Épicos por aging', 'table-portfolio-top-epicos-aging'))
            return html.Div([
                html.H3('Concentração (Top Épicos por Volume/Aging)', style={'textAlign': 'left'}),
                *sections
            ], style={'marginTop': '24px'})

        def render_quality_cards(df_quality_scope, df_quality_global):
            def _from_scope_or_global(indicador):
                if df_quality_scope is not None and not df_quality_scope.empty:
                    total_items = int(df_quality_scope['TotalItems'].sum()) if 'TotalItems' in df_quality_scope.columns else 0
                    com_team = int(df_quality_scope['ComTeamOriginal'].sum()) if 'ComTeamOriginal' in df_quality_scope.columns else 0
                    status_nm = int(df_quality_scope['StatusNaoMapeado'].sum()) if 'StatusNaoMapeado' in df_quality_scope.columns else 0
                    feat_total = int(df_quality_scope['FeaturesTotal'].sum()) if 'FeaturesTotal' in df_quality_scope.columns else 0
                    feat_epic = int(df_quality_scope['FeaturesComEpic'].sum()) if 'FeaturesComEpic' in df_quality_scope.columns else 0
                    feat_eff = int(df_quality_scope['FeaturesComEffort'].sum()) if 'FeaturesComEffort' in df_quality_scope.columns else 0
                    mapping = {
                        '% com TEAM': (com_team, total_items),
                        '% features com épico': (feat_epic, feat_total),
                        '% features com effort': (feat_eff, feat_total),
                        '% itens com status não mapeado': (status_nm, total_items),
                    }
                    n, d = mapping.get(indicador, (0, 0))
                    pct = round((n / d * 100), 1) if d else 0.0
                    return pct, n, d
                if df_quality_global is not None and not df_quality_global.empty:
                    row = df_quality_global[df_quality_global['Indicador'] == indicador]
                    if not row.empty:
                        r = row.iloc[0]
                        return float(r.get('Percentual', 0.0) or 0.0), int(r.get('Numerador', 0) or 0), int(r.get('Denominador', 0) or 0)
                return 0.0, 0, 0

            _quality_palette = {
                'verde':    {'bg': '#e8f5e9', 'border': '#2e7d32', 'text': '#1b5e20'},
                'amarelo':  {'bg': '#fff8e1', 'border': '#f9a825', 'text': '#8d6e00'},
                'vermelho': {'bg': '#ffebee', 'border': '#c62828', 'text': '#8e0000'},
            }
            def _quality_cfg(indicador, pct):
                if indicador == '% itens com status não mapeado':
                    key = 'vermelho' if pct > 10 else ('amarelo' if pct > 3 else 'verde')
                else:
                    key = 'verde' if pct >= 90 else ('amarelo' if pct >= 70 else 'vermelho')
                return _quality_palette[key]

            _QUALITY_GROUPS = [
                {'label': 'Cobertura de Equipes',  'indicators': ['% com TEAM']},
                {'label': 'Completude de Dados',   'indicators': ['% features com épico', '% features com effort', '% itens com status não mapeado']},
            ]
            sections = [html.H3('Qualidade de Cadastro', style={'textAlign': 'left'})]
            for group in _QUALITY_GROUPS:
                cards = []
                for indicador in group['indicators']:
                    pct, n, d = _from_scope_or_global(indicador)
                    cfg = _quality_cfg(indicador, pct)
                    cards.append(html.Div([
                        html.Div(indicador, style={'fontSize': '11px', 'fontWeight': '700', 'color': cfg['text'], 'textTransform': 'uppercase', 'letterSpacing': '0.3px'}),
                        html.Div(f'{pct:.1f}%', style={'fontSize': '28px', 'fontWeight': '800', 'color': cfg['text'], 'lineHeight': '1.1', 'marginTop': '4px'}),
                        html.Div(f'{n}/{d}', style={'fontSize': '12px', 'color': cfg['text'], 'marginTop': '2px'}),
                    ], style={
                        'padding': '10px 14px',
                        'borderRadius': '10px',
                        'backgroundColor': cfg['bg'],
                        'border': f"1px solid {cfg['border']}",
                        'minHeight': '90px',
                    }))
                if not cards:
                    continue
                sections.append(html.Div([
                    html.Div(group['label'], style={'fontSize': '13px', 'fontWeight': '700', 'color': '#334155', 'marginBottom': '8px'}),
                    html.Div(cards, style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(150px, 1fr))', 'gap': '8px'}),
                ], style={'marginBottom': '16px'}))
            return html.Div([
                *sections,
                portfolio_table_component(
                    (df_quality_scope if df_quality_scope is not None and not df_quality_scope.empty else df_quality_global),
                    'Qualidade de cadastro por TEAM (ou resumo global)',
                    'table-portfolio-qualidade-cadastro'
                )
            ], style={'marginTop': '24px'})

        def render_portfolio_due_date_performance(ddp_df):
            if ddp_df is None or ddp_df.empty:
                return html.Div()
            _ddp_status_colors = {
                'No prazo':          {'bg': '#e8f5e9', 'border': '#2e7d32', 'text': '#1b5e20'},
                'Atrasado':          {'bg': '#ffebee', 'border': '#c62828', 'text': '#8e0000'},
                'Vencido':           {'bg': '#ffebee', 'border': '#b71c1c', 'text': '#7f0000'},
                'Risco ≤14d':        {'bg': '#fff3e0', 'border': '#e65100', 'text': '#bf360c'},
                'Risco 15-30d':      {'bg': '#fff8e1', 'border': '#f9a825', 'text': '#8d6e00'},
                'Em acompanhamento': {'bg': '#e3f2fd', 'border': '#1565c0', 'text': '#0d47a1'},
                'Sem target':        {'bg': '#f5f5f5', 'border': '#9e9e9e', 'text': '#424242'},
            }
            sections = [html.H3('Due Date Performance — Épicos e Features', style={'textAlign': 'left'})]
            sections.append(html.P(
                'Distribuição por status de prazo para todos os épicos e features do portfólio (abertos e entregues).',
                style={'color': '#555', 'marginBottom': '10px', 'fontSize': '13px'},
            ))
            for tipo_label in ['Épico', 'Feature']:
                tipo_rows = ddp_df[ddp_df['Tipo'] == tipo_label]
                if tipo_rows.empty:
                    continue
                total_tipo = int(tipo_rows['Qtd'].sum())
                cards = []
                for _, row in tipo_rows.iterrows():
                    status = str(row['Status DDP'])
                    n = int(row['Qtd'])
                    pct = float(row['% do Total'])
                    if n == 0:
                        continue
                    cfg = _ddp_status_colors.get(status, _ddp_status_colors['Sem target'])
                    cards.append(html.Div([
                        html.Div(status, style={'fontSize': '11px', 'fontWeight': '700', 'color': cfg['text'], 'textTransform': 'uppercase', 'letterSpacing': '0.3px'}),
                        html.Div(str(n), style={'fontSize': '28px', 'fontWeight': '800', 'color': cfg['text'], 'lineHeight': '1.1', 'marginTop': '4px'}),
                        html.Div(f"{pct:.1f}%", style={'fontSize': '12px', 'color': cfg['text'], 'marginTop': '2px'}),
                    ], style={
                        'padding': '10px 14px',
                        'borderRadius': '10px',
                        'backgroundColor': cfg['bg'],
                        'border': f"1px solid {cfg['border']}",
                        'minHeight': '90px',
                    }))
                if not cards:
                    continue
                sections.append(html.Div([
                    html.Div(
                        f"{tipo_label}s ({total_tipo} no total)",
                        style={'fontSize': '13px', 'fontWeight': '700', 'color': '#334155', 'marginBottom': '8px'},
                    ),
                    html.Div(cards, style={
                        'display': 'grid',
                        'gridTemplateColumns': 'repeat(auto-fill, minmax(150px, 1fr))',
                        'gap': '8px',
                    }),
                ], style={'marginBottom': '16px'}))
            return html.Div(sections, style={'marginTop': '24px'})

        def render_portfolio_health_scorecard(df_scorecard, df_dimensions):
            if df_scorecard is None or df_scorecard.empty:
                return html.Div([html.H3('Scorecard de Saúde do Portfólio'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            severity_palette = {
                'Saudável': {'bg': '#e8f5e9', 'border': '#2e7d32', 'value': '#1b5e20'},
                'Atenção': {'bg': '#fff8e1', 'border': '#f9a825', 'value': '#8d6e00'},
                'Crítico': {'bg': '#ffebee', 'border': '#c62828', 'value': '#8e0000'},
            }
            overall = df_scorecard.iloc[0]
            overall_style = severity_palette.get(str(overall.get('Status', '')), severity_palette['Atenção'])
            hero = html.Div([
                html.Div('Saúde geral do portfólio', style={'fontSize': '15px', 'fontWeight': '700', 'color': '#334155'}),
                html.Div(f"{float(overall.get('Score', 0.0)):.1f}", style={'fontSize': '72px', 'lineHeight': '1.0', 'fontWeight': '800', 'color': overall_style['value']}),
                html.Div(str(overall.get('Status', '')), style={'fontSize': '18px', 'fontWeight': '700', 'color': overall_style['value']}),
                html.Div(str(overall.get('Detalhe', '')), style={'fontSize': '13px', 'marginTop': '8px', 'color': '#475569'}),
            ], style={
                'padding': '18px 20px',
                'borderRadius': '12px',
                'backgroundColor': overall_style['bg'],
                'border': f"2px solid {overall_style['border']}",
                'minHeight': '210px',
                'display': 'flex',
                'flexDirection': 'column',
                'justifyContent': 'space-between',
            })
            cards = []
            for _, row in df_scorecard.iloc[1:].iterrows():
                style_cfg = severity_palette.get(str(row.get('Status', '')), severity_palette['Atenção'])
                cards.append(html.Div([
                    html.Div(str(row.get('Indicador', '')), style={'fontSize': '15px', 'fontWeight': '700', 'color': '#334155'}),
                    html.Div(f"{float(row.get('Score', 0.0)):.1f}", style={'fontSize': '36px', 'lineHeight': '1.0', 'fontWeight': '800', 'color': style_cfg['value'], 'marginTop': '10px'}),
                    html.Div(str(row.get('Status', '')), style={'fontSize': '14px', 'fontWeight': '700', 'color': style_cfg['value'], 'marginTop': '6px'}),
                    html.Div(str(row.get('Detalhe', '')), style={'fontSize': '12px', 'lineHeight': '1.35', 'marginTop': '8px', 'color': '#475569'}),
                ], style={
                    'padding': '14px 16px',
                    'borderRadius': '12px',
                    'backgroundColor': style_cfg['bg'],
                    'border': f"1px solid {style_cfg['border']}",
                    'minHeight': '170px',
                }))
            return html.Div([
                html.H3('Scorecard de Saúde do Portfólio', style={'textAlign': 'left'}),
                html.Div([
                    html.Div(hero, style={'gridColumn': 'span 2'}),
                    *cards,
                ], style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fit, minmax(220px, 1fr))',
                    'gap': '12px',
                    'alignItems': 'stretch',
                }),
                portfolio_table_component(df_dimensions.copy(), 'Dimensões do scorecard de saúde', 'table-portfolio-health-dimensions')
            ], style={'marginTop': '24px'})

        def render_flow_distribution_and_load(df_type, df_status, df_team, df_stage_summary, df_stage_detail, df_stage_alerts):
            empty_distribution = all(frame is None or frame.empty for frame in [df_type, df_status, df_team])
            empty_load = (df_stage_detail is None or df_stage_detail.empty)
            if empty_distribution and empty_load:
                return html.Div([html.H3('Flow Distribution & Load Atual'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            sections = [html.H3('Flow Distribution & Load Atual', style={'textAlign': 'left'})]
            sections.append(html.P(
                'Leitura de snapshot dos itens abertos no portfólio. A distribuição mostra mix atual; o load explicita a carga por etapa e sinaliza excesso sobre limites configurados.',
                style={'color': '#555', 'marginBottom': '10px'}
            ))
            if df_stage_summary is not None and not df_stage_summary.empty:
                cards = []
                for _, row in df_stage_summary.iterrows():
                    value = row.get('Valor', 0)
                    if isinstance(value, float):
                        display_value = f"{value:.2f}"
                    else:
                        display_value = str(value)
                    cards.append(_portfolio_metric_card(str(row.get('Indicador', '')), display_value))
                sections.append(html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fit, minmax(180px, 1fr))',
                    'gap': '12px',
                    'marginBottom': '12px',
                }))
            if not empty_distribution:
                fig = make_subplots(rows=1, cols=3, subplot_titles=('Por tipo', 'Por status', 'Por TEAM'))
                distribution_frames = [
                    (df_type, 'Tipo'),
                    (df_status, 'Status'),
                    (df_team, 'Team'),
                ]
                colors = ['#1565c0', '#2e7d32', '#ef6c00']
                for idx, (frame, label_col) in enumerate(distribution_frames, start=1):
                    if frame is None or frame.empty or label_col not in frame.columns:
                        continue
                    plot_df = frame.head(10).copy().sort_values('WorkItems', ascending=True)
                    fig.add_trace(
                        go.Bar(
                            x=plot_df['WorkItems'],
                            y=plot_df[label_col],
                            orientation='h',
                            marker_color=colors[idx - 1],
                            showlegend=False,
                            text=plot_df['% Share'].map(lambda v: f"{float(v):.1f}%"),
                            textposition='outside',
                        ),
                        row=1,
                        col=idx,
                    )
                fig.update_layout(height=430, template='plotly_white', margin=dict(t=60, b=40, l=40, r=20))
                sections.append(dcc.Graph(figure=fig))
                sections.append(portfolio_table_component(df_type.copy(), 'Flow distribution por tipo (itens abertos)', 'table-portfolio-flow-distribution-type'))
                sections.append(portfolio_table_component(df_status.copy(), 'Flow distribution por status (itens abertos)', 'table-portfolio-flow-distribution-status'))
                sections.append(portfolio_table_component(df_team.copy(), 'Flow distribution por TEAM (itens abertos)', 'table-portfolio-flow-distribution-team'))
            if not empty_load:
                load_plot = df_stage_detail.copy().sort_values(['TotalItems', 'Status'], ascending=[True, True])
                fig_load = px.bar(
                    load_plot,
                    x='TotalItems',
                    y='Status',
                    orientation='h',
                    color='Severidade',
                    template='plotly_white',
                    title='Load atual por etapa',
                    hover_data=['StatusCategoria', 'WIPItems', 'BacklogItems', 'Limite', 'LoadRatio', 'Aging Médio', 'Aging P90'],
                    color_discrete_map={'OK': '#2e7d32', 'Alerta': '#f9a825', 'Critico': '#c62828', 'Sem limite': '#90a4ae'}
                )
                fig_load.update_layout(height=max(340, 38 * max(1, len(load_plot)) + 120), margin=dict(t=60, b=40, l=80, r=20))
                sections.append(dcc.Graph(figure=fig_load))
                if df_stage_alerts is not None and not df_stage_alerts.empty:
                    sections.append(portfolio_table_component(df_stage_alerts.copy(), 'Alertas de limite por etapa', 'table-portfolio-stage-limit-alerts'))
                sections.append(portfolio_table_component(df_stage_detail.copy(), 'Load atual por etapa (snapshot)', 'table-portfolio-stage-load-detail'))
            return html.Div(sections, style={'marginTop': '24px'})

        def render_flow_health(df_summary, df_team):
            if (df_summary is None or df_summary.empty) and (df_team is None or df_team.empty):
                return html.Div([html.H3('Saúde de Fluxo (Snapshot)'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            card_colors = {
                '% WIP no portfólio': '#1565c0',
                '% backlog parado >15d': '#f9a825',
                '% backlog parado >30d': '#c62828',
                '% itens abertos': '#546e7a',
            }
            cards = []
            if df_summary is not None and not df_summary.empty:
                for _, row in df_summary.iterrows():
                    label = str(row.get('Indicador', 'Indicador'))
                    pct = float(row.get('Percentual', 0) or 0)
                    n = int(row.get('Numerador', 0) or 0)
                    d = int(row.get('Denominador', 0) or 0)
                    bg = card_colors.get(label, '#455a64')
                    cards.append(html.Div([
                        html.Div(label, style={'fontSize': '14px', 'fontWeight': 'bold'}),
                        html.Div(f'{pct:.1f}%', style={'fontSize': '42px', 'lineHeight': '1.0'}),
                        html.Div(f'{n}/{d}', style={'fontSize': '12px', 'opacity': 0.9}),
                    ], style={'backgroundColor': bg, 'color': 'white', 'padding': '12px', 'borderRadius': '4px', 'minHeight': '130px'}))
            blocks = [html.Div(cards, style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(210px, 1fr))', 'gap': '10px'})]
            if df_team is not None and not df_team.empty:
                dynamic_backlog_cols = [c for c in df_team.columns if str(c).startswith('BacklogParado') or str(c).startswith('% Backlog parado >')]
                cols = [c for c in ['Team', 'TotalItems', 'WIP', '% WIP', 'BacklogAberto'] if c in df_team.columns] + dynamic_backlog_cols
                blocks.append(portfolio_table_component(df_team[cols].copy(), 'Saúde de fluxo por TEAM', 'table-portfolio-flow-health-team'))
            return html.Div([html.H3('Saúde de Fluxo (Snapshot)', style={'textAlign': 'left'}), *blocks], style={'marginTop': '24px'})

        def render_flow_health_dynamic(items_df):
            if items_df is None or items_df.empty:
                return render_flow_health(flow_health_summary, flow_health_por_team)
            base = items_df.copy()
            for c in ['IsOpen', 'IsBacklog', 'IsInProgress']:
                if c in base.columns:
                    base[c] = base[c].astype(bool)
            base['AgingDiasSemAlteracao'] = pd.to_numeric(base.get('AgingDiasSemAlteracao'), errors='coerce')
            total_items = int(len(base))
            backlog = base[(base.get('IsOpen', False) == True) & (base.get('IsBacklog', False) == True)].copy()
            wip = int((base.get('IsInProgress', False) == True).sum()) if 'IsInProgress' in base.columns else 0
            open_items = int((base.get('IsOpen', False) == True).sum()) if 'IsOpen' in base.columns else 0
            b15 = int((backlog['AgingDiasSemAlteracao'] > cfg_backlog_15).sum()) if not backlog.empty else 0
            b30 = int((backlog['AgingDiasSemAlteracao'] > cfg_backlog_30).sum()) if not backlog.empty else 0
            total_backlog = int(len(backlog))
            summary = pd.DataFrame([
                {'Indicador': '% WIP no portfólio', 'Percentual': round((wip / total_items * 100), 1) if total_items else 0.0, 'Numerador': wip, 'Denominador': total_items},
                {'Indicador': f'% backlog parado >{cfg_backlog_15}d', 'Percentual': round((b15 / total_backlog * 100), 1) if total_backlog else 0.0, 'Numerador': b15, 'Denominador': total_backlog},
                {'Indicador': f'% backlog parado >{cfg_backlog_30}d', 'Percentual': round((b30 / total_backlog * 100), 1) if total_backlog else 0.0, 'Numerador': b30, 'Denominador': total_backlog},
                {'Indicador': '% itens abertos', 'Percentual': round((open_items / total_items * 100), 1) if total_items else 0.0, 'Numerador': open_items, 'Denominador': total_items},
            ])
            if 'TeamDisplay' in base.columns:
                rows = []
                for team, grp in base.groupby('TeamDisplay', dropna=False):
                    gback = grp[(grp.get('IsOpen', False) == True) & (grp.get('IsBacklog', False) == True)].copy()
                    rows.append({
                        'Team': str(team),
                        'TotalItems': int(len(grp)),
                        'WIP': int((grp.get('IsInProgress', False) == True).sum()) if 'IsInProgress' in grp.columns else 0,
                        '% WIP': round(((grp.get('IsInProgress', False) == True).sum() / len(grp) * 100), 1) if len(grp) else 0.0,
                        'BacklogAberto': int(len(gback)),
                        f'BacklogParado{cfg_backlog_15}': int((pd.to_numeric(gback.get('AgingDiasSemAlteracao'), errors='coerce') > cfg_backlog_15).sum()) if not gback.empty else 0,
                        f'BacklogParado{cfg_backlog_30}': int((pd.to_numeric(gback.get('AgingDiasSemAlteracao'), errors='coerce') > cfg_backlog_30).sum()) if not gback.empty else 0,
                    })
                team_df = pd.DataFrame(rows)
                if not team_df.empty:
                    team_df[f'% Backlog parado >{cfg_backlog_15}d'] = (team_df[f'BacklogParado{cfg_backlog_15}'] / team_df['BacklogAberto'].replace(0, np.nan) * 100).fillna(0).round(1)
                    team_df[f'% Backlog parado >{cfg_backlog_30}d'] = (team_df[f'BacklogParado{cfg_backlog_30}'] / team_df['BacklogAberto'].replace(0, np.nan) * 100).fillna(0).round(1)
            else:
                team_df = pd.DataFrame()
            return render_flow_health(summary, team_df)

        def render_decision_queue(df_dq, df_summary):
            if (df_dq is None or df_dq.empty) and (df_summary is None or df_summary.empty):
                return html.Div([html.H3('Fila de Decisão por Aging'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            parts = []
            if df_dq is not None and not df_dq.empty:
                bucket_order = ['0-7', '8-15', '16-30', '31-60', '60+']
                df_plot = df_dq.copy()
                df_plot['AgingBucketDecision'] = (
                    df_plot['AgingBucketDecision']
                    .fillna('0-7')
                    .astype(str)
                    .str.strip()
                )
                present_buckets = [bucket for bucket in bucket_order if (df_plot['AgingBucketDecision'] == bucket).any()]
                if not present_buckets:
                    present_buckets = bucket_order[:1]
                fig = px.bar(
                    df_plot,
                    x='Status',
                    y='WorkItems',
                    color='AgingBucketDecision',
                    barmode='stack',
                    template='plotly_white',
                    title='Fila de decisão por status e aging',
                    category_orders={'AgingBucketDecision': present_buckets},
                )
                fig.update_layout(height=360, margin=dict(t=60, b=80), xaxis_tickangle=-20)
                parts.append(dcc.Graph(figure=fig))
                parts.append(portfolio_table_component(df_dq.copy(), 'Fila de decisão (detalhe por TEAM/status/bucket)', 'table-portfolio-decision-queue-aging'))
            if df_summary is not None and not df_summary.empty:
                parts.append(portfolio_table_component(df_summary.copy(), 'Fila de decisão por status (resumo)', 'table-portfolio-decision-queue-summary'))
            return html.Div([html.H3('Fila de Decisão por Aging', style={'textAlign': 'left'}), *parts], style={'marginTop': '24px'})

        def render_data_freshness(df_fresh):
            if df_fresh is None or df_fresh.empty:
                return html.Div([html.H3('Data Freshness por Etapa'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            pivot = df_fresh.pivot_table(index='Team', columns='StatusCategoria', values='% >30d', aggfunc='mean', fill_value=0)
            fig = px.imshow(pivot, text_auto='.1f', aspect='auto', color_continuous_scale=['#2e7d32', '#f9a825', '#c62828'],
                            labels=dict(x='StatusCategoria', y='TEAM', color='% >30d'),
                            title='Data Freshness por etapa (abertos) - % acima de 30 dias')
            fig.update_layout(height=max(320, 34 * max(1, len(pivot.index)) + 140), margin=dict(t=60, b=60))
            cols = [c for c in ['Team', 'StatusCategoria', 'WorkItems', 'GT15', '% >15d', 'GT30', '% >30d'] if c in df_fresh.columns]
            return html.Div([
                html.H3('Data Freshness por Etapa', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(df_fresh[cols].copy(), 'Freshness por TEAM e etapa', 'table-portfolio-data-freshness')
            ], style={'marginTop': '24px'})

        def render_data_freshness_dynamic(items_df):
            if items_df is None or items_df.empty:
                return render_data_freshness(data_freshness_por_team_statuscat)
            base = items_df.copy()
            if 'IsOpen' in base.columns:
                base = base[base['IsOpen'] == True].copy()
            if base.empty:
                return html.Div([html.H3('Data Freshness por Etapa'), html.P('Sem itens abertos para exibição.')], style={'marginTop': '20px'})
            base['AgingDiasSemAlteracao'] = pd.to_numeric(base.get('AgingDiasSemAlteracao'), errors='coerce')
            team_col = 'TeamDisplay' if 'TeamDisplay' in base.columns else None
            if not team_col:
                return render_data_freshness(data_freshness_por_team_statuscat)
            agg = (
                base.groupby([team_col, 'StatusCategoria'], dropna=False)
                .agg(WorkItems=('ID', 'count'))
                .reset_index()
                .rename(columns={team_col: 'Team'})
            )
            tmp = base.copy()
            tmp['GTa'] = (tmp['AgingDiasSemAlteracao'] > cfg_fresh_15).astype(int)
            tmp['GTb'] = (tmp['AgingDiasSemAlteracao'] > cfg_fresh_30).astype(int)
            add = tmp.groupby([team_col, 'StatusCategoria'], dropna=False).agg(GTa=('GTa', 'sum'), GTb=('GTb', 'sum')).reset_index().rename(columns={team_col: 'Team'})
            agg = agg.merge(add, on=['Team', 'StatusCategoria'], how='left')
            agg[f'% >{cfg_fresh_15}d'] = (agg['GTa'] / agg['WorkItems'].replace(0, np.nan) * 100).fillna(0).round(1)
            agg[f'% >{cfg_fresh_30}d'] = (agg['GTb'] / agg['WorkItems'].replace(0, np.nan) * 100).fillna(0).round(1)
            view = agg.rename(columns={'GTa': f'GT{cfg_fresh_15}', 'GTb': f'GT{cfg_fresh_30}', f'% >{cfg_fresh_15}d': '% >15d', f'% >{cfg_fresh_30}d': '% >30d'})
            return render_data_freshness(view)

        def render_status_conformance(df_workflow, df_status_top, df_fora_top):
            if all(x is None or x.empty for x in [df_workflow, df_status_top, df_fora_top]):
                return html.Div([html.H3('Conformidade de Workflow'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            parts = []
            if df_workflow is not None and not df_workflow.empty:
                cols = [c for c in ['Team', 'TotalItems', 'StatusForaWorkflow', '% Fora workflow'] if c in df_workflow.columns]
                parts.append(portfolio_table_component(df_workflow[cols].copy(), 'Conformidade de workflow por TEAM', 'table-portfolio-workflow-conformance'))
            if df_fora_top is not None and not df_fora_top.empty:
                parts.append(portfolio_table_component(df_fora_top.copy(), 'Top status fora do workflow padrão', 'table-portfolio-status-fora-workflow'))
            if df_status_top is not None and not df_status_top.empty:
                parts.append(portfolio_table_component(df_status_top.copy(), 'Distribuição de status original (Top N)', 'table-portfolio-status-original-top'))
            return html.Div([html.H3('Conformidade de Workflow', style={'textAlign': 'left'}), *parts], style={'marginTop': '24px'})

        def render_estrutura_cobertura(df_summary, df_team):
            if (df_summary is None or df_summary.empty) and (df_team is None or df_team.empty):
                return html.Div([html.H3('Cobertura Estrutural'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            cards = []
            if df_summary is not None and not df_summary.empty:
                for _, row in df_summary.iterrows():
                    pct = float(row.get('Percentual', 0) or 0)
                    n = int(row.get('Numerador', 0) or 0)
                    d = int(row.get('Denominador', 0) or 0)
                    label = str(row.get('Indicador', 'Indicador'))
                    cards.append(html.Div([
                        html.Div(label, style={'fontSize': '14px', 'fontWeight': 'bold'}),
                        html.Div(f'{pct:.1f}%', style={'fontSize': '42px'}),
                        html.Div(f'{n}/{d}', style={'fontSize': '12px', 'opacity': 0.9}),
                    ], style={'backgroundColor': '#5d4037', 'color': 'white', 'padding': '12px', 'borderRadius': '4px', 'minHeight': '130px'}))
            blocks = [html.Div(cards, style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(220px, 1fr))', 'gap': '10px'})]
            if df_team is not None and not df_team.empty:
                cols = [c for c in ['Team', 'EpicosTotal', 'EpicosComItensFluxo', '% Épicos com itens de fluxo', 'FeaturesTotal', 'FeaturesComFilhos', '% Features com filhos', 'StoryTaskTotal', 'StoryTaskSemFeatureTatico', '% Story/Task sem feature tática', 'StoryTaskOrfaos', '% Story/Task órfãos'] if c in df_team.columns]
                blocks.append(portfolio_table_component(df_team[cols].copy(), 'Cobertura estrutural por TEAM', 'table-portfolio-estrutura-cobertura'))
            return html.Div([html.H3('Cobertura Estrutural', style={'textAlign': 'left'}), *blocks], style={'marginTop': '24px'})

        def render_concentracao_relativa(df_summary, df_team_share, df_epic_share):
            if (df_summary is None or df_summary.empty) and (df_team_share is None or df_team_share.empty) and (df_epic_share is None or df_epic_share.empty):
                return html.Div([html.H3('Concentração Relativa'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            parts = []
            if df_summary is not None and not df_summary.empty:
                parts.append(portfolio_table_component(df_summary.copy(), 'Resumo de concentração relativa (Top N)', 'table-portfolio-concentracao-summary'))
            if df_team_share is not None and not df_team_share.empty:
                cols = [c for c in ['Team', 'TotalItems', '% Share', '% Share Acum', 'QtdEpicos', 'QtdFeatures'] if c in df_team_share.columns]
                parts.append(portfolio_table_component(df_team_share[cols].copy(), 'Concentração por TEAM (share acumulado)', 'table-portfolio-concentracao-team-share'))
            if df_epic_share is not None and not df_epic_share.empty:
                cols = [c for c in ['EpicID', 'Team', 'QtdItensFluxo', '% Share Itens Fluxo', '% Share Acum', 'QtdFeatures', 'AgingDiasSemAlteracao'] if c in df_epic_share.columns]
                parts.append(portfolio_table_component(df_epic_share[cols].copy(), 'Concentração por Épico (share de itens de fluxo)', 'table-portfolio-concentracao-epico-share'))
            return html.Div([html.H3('Concentração Relativa', style={'textAlign': 'left'}), *parts], style={'marginTop': '24px'})

        def render_tipo_balanceamento(df_tipo_balance):
            if df_tipo_balance is None or df_tipo_balance.empty:
                return html.Div([html.H3('Índice de Balanceamento por Tipo'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            fig = px.bar(df_tipo_balance.sort_values('Desvio Abs (pp)', ascending=False), x='Tipo', y='Desvio (pp)', color='Desvio (pp)',
                         template='plotly_white', title='Desvio do mix por tipo (atual vs alvo)', color_continuous_scale=['#2e7d32', '#f9a825', '#c62828'])
            fig.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            return html.Div([
                html.H3('Índice de Balanceamento por Tipo', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(df_tipo_balance.copy(), 'Mix por tipo (atual vs alvo)', 'table-portfolio-tipo-balanceamento')
            ], style={'marginTop': '24px'})

        def render_thresholds_config_summary():
            return html.Div([
                html.H4('Parâmetros ativos (UI)', style={'marginBottom': '6px'}),
                html.P(
                    f'Backlog parado: >{cfg_backlog_15}d / >{cfg_backlog_30}d | Freshness: >{cfg_fresh_15}d / >{cfg_fresh_30}d | '
                    f'Fila decisão: {", ".join(cfg_decision_statuses[:6]) + ("..." if len(cfg_decision_statuses) > 6 else "")}',
                    style={'color': '#555', 'marginBottom': '0'}
                )
            ], style={'marginTop': '10px', 'padding': '10px 12px', 'border': '1px solid #e5e7eb', 'borderRadius': '8px', 'backgroundColor': '#fafafa'})

        def render_dynamic_workflow_conformance(items_df):
            if items_df is None or items_df.empty:
                return html.Div([html.H3('Conformidade de Workflow (Parametrizada)'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = items_df.copy()
            official_norm = [normalize_text(s) for s in cfg_workflow_statuses if str(s).strip()]
            series_norm = base.get('StatusNorm', pd.Series('', index=base.index)).fillna('').astype(str)
            mask_official = pd.Series(False, index=base.index)
            for term in official_norm:
                if term:
                    mask_official = mask_official | series_norm.str.contains(term, regex=False, na=False)
            base['ForaWorkflowCfg'] = ~mask_official
            team_col = 'TeamDisplay' if 'TeamDisplay' in base.columns else None
            team_table = pd.DataFrame()
            if team_col:
                team_table = (
                    base.groupby(team_col, dropna=False)
                    .agg(TotalItems=('ID', 'count'), ForaWorkflow=('ForaWorkflowCfg', 'sum'))
                    .reset_index()
                    .rename(columns={team_col: 'Team'})
                )
                team_table['% Fora workflow (cfg)'] = (team_table['ForaWorkflow'] / team_table['TotalItems'].replace(0, np.nan) * 100).fillna(0).round(1)
                team_table = team_table.sort_values(['% Fora workflow (cfg)', 'ForaWorkflow'], ascending=[False, False], ignore_index=True)
            top_status = (
                base[base['ForaWorkflowCfg']]
                .groupby('Status', dropna=False)
                .size().reset_index(name='WorkItems')
                .sort_values('WorkItems', ascending=False, ignore_index=True)
                .head(20)
            )
            return html.Div([
                html.H3('Conformidade de Workflow (Parametrizada)', style={'textAlign': 'left'}),
                portfolio_table_component(team_table, 'Conformidade por TEAM (lista oficial configurada na UI)', 'table-portfolio-workflow-conformance-cfg'),
                portfolio_table_component(top_status, 'Top status fora do workflow (lista oficial configurada na UI)', 'table-portfolio-status-fora-workflow-cfg'),
            ], style={'marginTop': '24px'})

        def render_dynamic_decision_queue(items_df):
            if items_df is None or items_df.empty:
                return html.Div([html.H3('Fila de Decisão (Parametrizada)'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = items_df.copy()
            status_norm = base.get('StatusNorm', pd.Series('', index=base.index)).fillna('').astype(str)
            wanted = [normalize_text(s) for s in cfg_decision_statuses if str(s).strip()]
            mask = pd.Series(False, index=base.index)
            for term in wanted:
                if term:
                    mask = mask | status_norm.str.contains(term, regex=False, na=False)
            base = base[(base.get('IsOpen', False) == True) & mask].copy()
            if base.empty:
                return html.Div([html.H3('Fila de Decisão (Parametrizada)'), html.P('Nenhum item encontrado com os statuses configurados.')], style={'marginTop': '20px'})
            base['AgingDiasSemAlteracao'] = pd.to_numeric(base['AgingDiasSemAlteracao'], errors='coerce')
            base['Bucket'] = '0-7'
            base.loc[base['AgingDiasSemAlteracao'] > 7, 'Bucket'] = '8-15'
            base.loc[base['AgingDiasSemAlteracao'] > 15, 'Bucket'] = '16-30'
            base.loc[base['AgingDiasSemAlteracao'] > 30, 'Bucket'] = '31-60'
            base.loc[base['AgingDiasSemAlteracao'] > 60, 'Bucket'] = '60+'
            summary = base.groupby('Status', dropna=False).agg(WorkItems=('ID', 'count'), AgingMedio=('AgingDiasSemAlteracao', 'mean')).reset_index()
            summary['AgingMedio'] = pd.to_numeric(summary['AgingMedio'], errors='coerce').round(1)
            fig = px.bar(base.groupby(['Status', 'Bucket'], dropna=False).size().reset_index(name='WorkItems'),
                         x='Status', y='WorkItems', color='Bucket', barmode='stack', template='plotly_white',
                         title='Fila de decisão (parametrizada) por status e aging')
            fig.update_layout(height=340, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            return html.Div([
                html.H3('Fila de Decisão (Parametrizada)', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig),
                portfolio_table_component(summary, 'Resumo da fila de decisão (statuses configurados na UI)', 'table-portfolio-decision-queue-cfg')
            ], style={'marginTop': '24px'})

        def render_dynamic_sla_aging(items_df):
            if items_df is None or items_df.empty:
                return html.Div([html.H3('SLA de Aging por Tipo/Status'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = items_df.copy()
            base = base[base.get('IsOpen', False) == True].copy() if 'IsOpen' in base.columns else base
            if base.empty:
                return html.Div([html.H3('SLA de Aging por Tipo/Status'), html.P('Sem itens abertos para avaliar SLA.')], style={'marginTop': '20px'})
            base['AgingDiasSemAlteracao'] = pd.to_numeric(base['AgingDiasSemAlteracao'], errors='coerce')
            tipo_cfg = cfg_sla_aging.get('tipo', {}) if isinstance(cfg_sla_aging, dict) else {}
            status_cfg = cfg_sla_aging.get('status', {}) if isinstance(cfg_sla_aging, dict) else {}
            tipo_map_norm = {normalize_text(k): float(v) for k, v in (tipo_cfg or {}).items() if str(k).strip()}
            status_map_norm = {normalize_text(k): float(v) for k, v in (status_cfg or {}).items() if str(k).strip()}
            base['SLA Tipo (dias)'] = base['TipoNorm'].map(tipo_map_norm)
            base['SLA Status (dias)'] = base['StatusNorm'].map(status_map_norm)
            base['Dentro SLA Tipo'] = np.where(base['SLA Tipo (dias)'].notna(), base['AgingDiasSemAlteracao'] <= base['SLA Tipo (dias)'], np.nan)
            base['Dentro SLA Status'] = np.where(base['SLA Status (dias)'].notna(), base['AgingDiasSemAlteracao'] <= base['SLA Status (dias)'], np.nan)
            tipo_eval = base[base['SLA Tipo (dias)'].notna()].copy()
            status_eval = base[base['SLA Status (dias)'].notna()].copy()
            tipo_table = pd.DataFrame(columns=['Tipo', 'SLA (dias)', 'Itens', '% Dentro SLA', '% Fora SLA'])
            status_table = pd.DataFrame(columns=['Status', 'SLA (dias)', 'Itens', '% Dentro SLA', '% Fora SLA'])
            if not tipo_eval.empty:
                tipo_table = tipo_eval.groupby('Tipo', dropna=False).agg(
                    **{'SLA (dias)': ('SLA Tipo (dias)', 'first'), 'Itens': ('ID', 'count'), 'Dentro': ('Dentro SLA Tipo', 'sum')}
                ).reset_index()
                tipo_table['% Dentro SLA'] = (tipo_table['Dentro'] / tipo_table['Itens'].replace(0, np.nan) * 100).fillna(0).round(1)
                tipo_table['% Fora SLA'] = (100 - tipo_table['% Dentro SLA']).round(1)
                tipo_table = tipo_table.drop(columns=['Dentro']).sort_values('% Fora SLA', ascending=False, ignore_index=True)
            if not status_eval.empty:
                status_table = status_eval.groupby('Status', dropna=False).agg(
                    **{'SLA (dias)': ('SLA Status (dias)', 'first'), 'Itens': ('ID', 'count'), 'Dentro': ('Dentro SLA Status', 'sum')}
                ).reset_index()
                status_table['% Dentro SLA'] = (status_table['Dentro'] / status_table['Itens'].replace(0, np.nan) * 100).fillna(0).round(1)
                status_table['% Fora SLA'] = (100 - status_table['% Dentro SLA']).round(1)
                status_table = status_table.drop(columns=['Dentro']).sort_values('% Fora SLA', ascending=False, ignore_index=True)
            fig = None
            if not tipo_table.empty:
                fig = px.bar(tipo_table, x='Tipo', y='% Fora SLA', color='% Fora SLA', template='plotly_white',
                             title='SLA de aging por tipo (% fora SLA)', color_continuous_scale=['#2e7d32', '#f9a825', '#c62828'])
                fig.update_layout(height=320, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            children = [html.H3('SLA de Aging por Tipo/Status', style={'textAlign': 'left'})]
            if fig is not None:
                children.append(dcc.Graph(figure=fig))
            children.append(portfolio_table_component(tipo_table, 'SLA aging por Tipo (configurado na UI)', 'table-portfolio-sla-aging-tipo'))
            children.append(portfolio_table_component(status_table, 'SLA aging por Status (configurado na UI)', 'table-portfolio-sla-aging-status'))
            return html.Div(children, style={'marginTop': '24px'})

        def render_mix_explicito_multi_contexto(items_df):
            if items_df is None or items_df.empty:
                return html.Div([html.H3('Mix por Projeto / Tipo / TEAM'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            base = items_df.copy()
            # Mix explícito consolidado
            mix_projeto = base.groupby('Projeto', dropna=False).size().reset_index(name='WorkItems')
            mix_projeto['% Share'] = (mix_projeto['WorkItems'] / mix_projeto['WorkItems'].sum() * 100).round(1)
            mix_tipo = base.groupby('Tipo', dropna=False).size().reset_index(name='WorkItems')
            mix_tipo['% Share'] = (mix_tipo['WorkItems'] / mix_tipo['WorkItems'].sum() * 100).round(1)
            team_col = 'TeamDisplay' if 'TeamDisplay' in base.columns else None
            mix_team = base.groupby(team_col, dropna=False).size().reset_index(name='WorkItems').rename(columns={team_col: 'Team'}) if team_col else pd.DataFrame()
            if not mix_team.empty:
                mix_team['% Share'] = (mix_team['WorkItems'] / mix_team['WorkItems'].sum() * 100).round(1)

            # Comparação multi-recorte de mix alvo por tipo.
            target_cfg = cfg_target_mix if isinstance(cfg_target_mix, dict) else {}
            global_target = target_cfg.get('global', {}) if isinstance(target_cfg.get('global', {}), dict) else {}
            target_global_norm = {str(k): float(v) for k, v in global_target.items() if str(k).strip()}
            recs = []
            contexts = [('Global', 'GLOBAL', base)]
            for p in sorted(base['Projeto'].fillna('').astype(str).unique()):
                if p:
                    contexts.append(('Projeto', p, base[base['Projeto'].astype(str) == p]))
            if team_col:
                for t in sorted(base[team_col].fillna('').astype(str).unique()):
                    if t:
                        contexts.append(('TEAM', t, base[base[team_col].astype(str) == t]))
            for ctx_type, ctx_name, df_ctx in contexts:
                if df_ctx is None or df_ctx.empty:
                    continue
                counts = df_ctx.groupby('Tipo', dropna=False).size().reset_index(name='WorkItems')
                counts['% Atual'] = (counts['WorkItems'] / counts['WorkItems'].sum() * 100).round(1)
                ctx_target_obj = target_cfg.get(ctx_name, None)
                if not isinstance(ctx_target_obj, dict):
                    ctx_target_obj = target_global_norm
                counts['% Alvo'] = counts['Tipo'].map(lambda x: float(ctx_target_obj.get(str(x), 0.0)) if isinstance(ctx_target_obj, dict) else 0.0).fillna(0.0)
                total_t = float(counts['% Alvo'].sum())
                if total_t > 0:
                    counts['% Alvo'] = (counts['% Alvo'] / total_t * 100).round(1)
                counts['Desvio (pp)'] = (counts['% Atual'] - counts['% Alvo']).round(1)
                counts['ContextoTipo'] = ctx_type
                counts['Contexto'] = ctx_name
                recs.append(counts[['ContextoTipo', 'Contexto', 'Tipo', 'WorkItems', '% Atual', '% Alvo', 'Desvio (pp)']])
            mix_contexto = pd.concat(recs, ignore_index=True) if recs else pd.DataFrame(columns=['ContextoTipo', 'Contexto', 'Tipo', 'WorkItems', '% Atual', '% Alvo', 'Desvio (pp)'])
            fig_mix = px.bar(mix_tipo.sort_values('WorkItems', ascending=False), x='Tipo', y='WorkItems', color='% Share', template='plotly_white',
                             title='Mix explícito por Tipo (escopo atual)', color_continuous_scale=['#1565c0', '#42a5f5'])
            fig_mix.update_layout(height=320, margin=dict(t=60, b=80), xaxis_tickangle=-20)
            return html.Div([
                html.H3('Mix por Projeto / Tipo / TEAM', style={'textAlign': 'left'}),
                dcc.Graph(figure=fig_mix),
                portfolio_table_component(mix_projeto.sort_values('WorkItems', ascending=False), 'Mix por Projeto', 'table-portfolio-mix-projeto'),
                portfolio_table_component(mix_tipo.sort_values('WorkItems', ascending=False), 'Mix por Tipo', 'table-portfolio-mix-tipo'),
                portfolio_table_component(mix_team.sort_values('WorkItems', ascending=False) if not mix_team.empty else mix_team, 'Mix por TEAM', 'table-portfolio-mix-team'),
                portfolio_table_component(mix_contexto, 'Mix alvo por tipo por contexto (global/projeto/team)', 'table-portfolio-mix-contexto-target')
            ], style={'marginTop': '24px'})

        def render_pareto_hhi(df_team_share, df_epic_share):
            if (df_team_share is None or df_team_share.empty) and (df_epic_share is None or df_epic_share.empty):
                return html.Div([html.H3('Pareto & HHI de Concentração'), html.P('Sem dados para exibição.')], style={'marginTop': '20px'})
            sections = [html.H3('Pareto & HHI de Concentração', style={'textAlign': 'left'})]
            hhi_rows = []
            if df_team_share is not None and not df_team_share.empty and '% Share' in df_team_share.columns:
                dft = df_team_share.copy()
                dft = dft.sort_values('TotalItems', ascending=False).reset_index(drop=True)
                dft['rank'] = np.arange(1, len(dft) + 1)
                fig_t = go.Figure()
                fig_t.add_trace(go.Bar(x=dft['Team'], y=dft['% Share'], name='% Share'))
                fig_t.add_trace(go.Scatter(x=dft['Team'], y=dft['% Share Acum'], mode='lines+markers', name='% Acum', yaxis='y2'))
                fig_t.update_layout(
                    title='Pareto de concentração por TEAM',
                    template='plotly_white',
                    height=360,
                    margin=dict(t=60, b=100),
                    xaxis=dict(tickangle=-25),
                    yaxis=dict(title='% Share'),
                    yaxis2=dict(title='% Acum', overlaying='y', side='right', range=[0, 100]),
                    legend=dict(orientation='h', y=-0.2)
                )
                sections.append(dcc.Graph(figure=fig_t))
                hhi_team = float(((pd.to_numeric(dft['% Share'], errors='coerce').fillna(0) / 100.0) ** 2).sum())
                hhi_rows.append({'Escopo': 'TEAM', 'HHI': round(hhi_team, 4), 'N': int(len(dft))})
            if df_epic_share is not None and not df_epic_share.empty and '% Share Itens Fluxo' in df_epic_share.columns:
                dfe = df_epic_share.copy()
                fig_e = go.Figure()
                fig_e.add_trace(go.Bar(x=dfe['EpicID'], y=dfe['% Share Itens Fluxo'], name='% Share itens fluxo'))
                fig_e.add_trace(go.Scatter(x=dfe['EpicID'], y=dfe['% Share Acum'], mode='lines+markers', name='% Acum', yaxis='y2'))
                fig_e.update_layout(
                    title='Pareto de concentração por Épico (itens de fluxo)',
                    template='plotly_white',
                    height=360,
                    margin=dict(t=60, b=100),
                    xaxis=dict(tickangle=-35),
                    yaxis=dict(title='% Share'),
                    yaxis2=dict(title='% Acum', overlaying='y', side='right', range=[0, 100]),
                    legend=dict(orientation='h', y=-0.2)
                )
                sections.append(dcc.Graph(figure=fig_e))
                hhi_epic = float(((pd.to_numeric(dfe['% Share Itens Fluxo'], errors='coerce').fillna(0) / 100.0) ** 2).sum())
                hhi_rows.append({'Escopo': 'Épico (itens fluxo)', 'HHI': round(hhi_epic, 4), 'N': int(len(dfe))})
            hhi_df = pd.DataFrame(hhi_rows)
            sections.append(portfolio_table_component(hhi_df, 'HHI de concentração (quanto maior, mais concentrado)', 'table-portfolio-hhi'))
            return html.Div(sections, style={'marginTop': '24px'})

        def render_portfolio_cross_delivery(data):
            if not isinstance(data, dict) or not data.get('available'):
                notes = data.get('notes', ['Sem dados suficientes para cruzar portfólio com downstream/process mining.']) if isinstance(data, dict) else ['Sem dados suficientes para cruzar portfólio com downstream/process mining.']
                return html.Div([
                    html.H3('Portfólio x Delivery', style={'textAlign': 'left'}),
                    *[html.P(str(note), style={'color': '#666'}) for note in notes]
                ], style={'paddingTop': '10px'})

            kpis_df = data.get('kpis_df', pd.DataFrame()).copy()
            asset_delivery_df = data.get('asset_delivery_df', pd.DataFrame()).copy()
            product_capacity_df = data.get('product_capacity_df', pd.DataFrame()).copy()
            dependency_df = data.get('dependency_df', pd.DataFrame()).copy()
            notes = data.get('notes', [])

            cards = []
            for _, row in kpis_df.iterrows():
                label = str(row.get('Indicador', '')).strip()
                value = row.get('Valor')
                if isinstance(value, float) and pd.notna(value):
                    if '%' in label:
                        display_value = f"{float(value):.1f}%"
                    else:
                        display_value = f"{float(value):.1f}" if not float(value).is_integer() else f"{int(value)}"
                else:
                    display_value = '—' if pd.isna(value) else str(value)
                cards.append(_portfolio_metric_card(label, display_value))

            children = [
                html.H3('Portfólio x Delivery', style={'textAlign': 'left'}),
                *[
                    html.P(str(note), style={'color': '#555', 'marginBottom': '6px'})
                    for note in notes
                ],
                html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fit, minmax(180px, 1fr))',
                    'gap': '12px',
                    'marginTop': '12px',
                }),
            ]

            if product_capacity_df is not None and not product_capacity_df.empty:
                cap_plot = product_capacity_df.copy()
                fig_capacity = px.bar(
                    cap_plot,
                    x='Produto',
                    y='% Capacidade Consumida',
                    color='% Capacidade Consumida',
                    template='plotly_white',
                    title='Consumo de capacidade por produto',
                    color_continuous_scale=['#2e7d32', '#f9a825', '#c62828'],
                    hover_data=['Capacidade Período (h)', 'Horas Consumidas', 'Assets Portfolio', 'Assets Entregues']
                )
                fig_capacity.update_layout(height=360, margin=dict(t=60, b=60))
                children.extend([
                    dcc.Graph(figure=fig_capacity),
                    portfolio_table_component(
                        product_capacity_df.copy(),
                        'Capacidade, entrega e valor realizado por produto',
                        'table-portfolio-cross-capacity'
                    )
                ])

            if dependency_df is not None and not dependency_df.empty:
                dep_plot = dependency_df.head(15).copy().sort_values('DependenciesAbertasConhecidas', ascending=True)
                fig_dep = px.bar(
                    dep_plot,
                    x='DependenciesAbertasConhecidas',
                    y='AssetID',
                    orientation='h',
                    color='Produto',
                    template='plotly_white',
                    title='Top ativos por dependências abertas conhecidas',
                    hover_data=['Titulo', 'DependenciesTotal', 'DependenciesExternas', 'PrazoRealStatus']
                )
                fig_dep.update_layout(height=max(320, len(dep_plot) * 28 + 120), margin=dict(t=60, b=40, l=110, r=20))
                children.extend([
                    dcc.Graph(figure=fig_dep),
                    portfolio_table_component(
                        dependency_df.copy(),
                        'Dependências explícitas por ativo',
                        'table-portfolio-cross-dependencies'
                    )
                ])

            if asset_delivery_df is not None and not asset_delivery_df.empty:
                status_order = ['Atrasado', 'Vencido sem entrega', 'Risco <=14d', 'No prazo', 'Em acompanhamento', 'Sem target']
                asset_plot = asset_delivery_df.copy()
                status_rank = {status: idx for idx, status in enumerate(status_order)}
                asset_plot['PrazoRealStatusRank'] = asset_plot['PrazoRealStatus'].map(status_rank).fillna(len(status_order))
                asset_plot = asset_plot.sort_values(['PrazoRealStatusRank', 'DependenciesAbertasConhecidas', 'AssetID']).head(20)
                fig_assets = px.scatter(
                    asset_plot,
                    x='Lead Time Fluxo Médio (dias)',
                    y='DependenciesAbertasConhecidas',
                    size='ItensDownstream',
                    color='PrazoRealStatus',
                    category_orders={'PrazoRealStatus': status_order},
                    hover_name='AssetID',
                    hover_data=['Titulo', 'Produto', 'ProxyRealizacaoValor', 'DeltaPrazoDias', 'Horas Reais Apontadas'],
                    template='plotly_white',
                    title='Prazo real x dependências x evidência downstream'
                )
                fig_assets.update_layout(height=420, margin=dict(t=60, b=40, l=60, r=20))
                asset_cols = [
                    c for c in [
                        'AssetID', 'Produto', 'Tipo', 'Team', 'Titulo', 'Status Portfolio', 'DueDate',
                        'DataEntregaReal', 'DeltaPrazoDias', 'PrazoRealStatus', 'ProxyRealizacaoValor',
                        'ItensDownstream', 'ItensDone', 'ItensReadyProd', 'CasosPM',
                        'Lead Time Fluxo Médio (dias)', 'Cycle Time Dev Médio (dias)',
                        'Horas Reais Apontadas', 'Custo Real Apontado (R$)',
                        'DependenciesTotal', 'DependenciesAbertasConhecidas', 'DependenciesExternas', 'Link'
                    ] if c in asset_delivery_df.columns
                ]
                children.extend([
                    dcc.Graph(figure=fig_assets),
                    portfolio_table_component(
                        asset_delivery_df[asset_cols].copy(),
                        'Ativos do portfólio com prazo real, dependências e proxy de realização de valor',
                        'table-portfolio-cross-assets'
                    )
                ])

            return html.Div(children, style={'paddingTop': '10px'})

        total_epicos_visao = int(epicos_por_team_total['QtdEpicos'].sum()) if epicos_por_team_total is not None and not epicos_por_team_total.empty else 0
        total_features_visao = int(features_por_team_total['QtdFeatures'].sum()) if features_por_team_total is not None and not features_por_team_total.empty else 0
        epicos_sem_features_visao = int((epicos_detalhe['QtdFeatures'] == 0).sum()) if epicos_detalhe is not None and not epicos_detalhe.empty else 0
        features_sem_epico_visao = int((features_detalhe['EpicID'].fillna('').astype(str).str.strip() == '').sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        features_sem_filhos_visao = int((features_detalhe['QtdFilhos'] == 0).sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        features_sem_mov_15_visao = int((features_detalhe['DiasSemMovimentacao'] > 15).sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        features_sem_mov_30_visao = int((features_detalhe['DiasSemMovimentacao'] > 30).sum()) if features_detalhe is not None and not features_detalhe.empty else 0
        hist_tasks_sem_feature_visao = int(hist_tasks_sem_feature_por_team['WorkItems'].sum()) if hist_tasks_sem_feature_por_team is not None and not hist_tasks_sem_feature_por_team.empty else 0
        scope_parts = []
        if portfolio_project and portfolio_project != PROJECT_FILTER_ALL_VALUE:
            scope_parts.append(f'TEAM: {portfolio_project}')
        elif effective_portfolio_project:
            scope_parts.append(f'TEAM contém: {effective_portfolio_project}')
        else:
            scope_parts.append('Todos os TEAMs')
        if tipo:
            scope_parts.append(f'Tipo: {tipo}')
        scope_parts.append(f'Tipo original Jira: {format_original_jira_type_filter_label(tipo_original_jira)}')
        if classe_servico:
            scope_parts.append(f'Classe: {classe_servico}')
        if responsavel:
            scope_parts.append(f'Responsáveis: {_format_responsavel_filter_label(responsavel)}')
        if portfolio_quarter and portfolio_quarter != 'ALL':
            scope_parts.append(f'Quarter: {portfolio_quarter}')
        scope_label = ' | '.join(scope_parts)
        portfolio_filter_alert = html.Div()
        if portfolio_filter_notes:
            portfolio_filter_alert = html.Div(
                [html.P(note, style={'margin': '0'}) for note in portfolio_filter_notes],
                style={
                    'margin': '12px auto 0 auto',
                    'maxWidth': '960px',
                    'padding': '10px 12px',
                    'border': '1px solid #f5c2c7',
                    'borderRadius': '8px',
                    'backgroundColor': '#fff5f5',
                    'color': '#842029'
                }
            )
        aging_label_us_20 = (
            'US com mais de 20 dias em processo sem alteração'
            if has_us_items else
            'Épicos com mais de 20 dias em processo sem alteração'
        )
        aging_label_us_comp_20 = (
            'US compromissadas a mais de 20 dias e em processo'
            if has_us_items else
            'Épicos compromissados a mais de 20 dias e em processo'
        )
        kpi_color_epic = '#ef6c00'      # laranja
        kpi_color_feature = '#7b1fa2'   # roxo
        kpi_color_story = '#1565c0'     # azul
        kpi_neutral = '#455a64'

        def portfolio_kpi_style(bg):
            fg = '#111' if bg in {'#ffcc80', '#ffe082'} else 'white'
            return {
                'card_style': {
                    'backgroundColor': bg,
                    'color': fg,
                    'minHeight': '140px',
                },
                'title_style': {'textAlign': 'left', 'fontSize': '15px', 'marginBottom': '6px', 'marginTop': '0', 'fontWeight': 'bold'},
                'value_style': {'textAlign': 'left', 'fontSize': '48px', 'marginTop': '0', 'marginBottom': '0', 'lineHeight': '1.1'},
            }

        high_priority_ids = set()
        high_priority_titles = set()
        manual_high_ids_raw = os.getenv('FLOW_PMO_PORTFOLIO_HIGHEST_IDS', '').strip()
        if manual_high_ids_raw:
            for token in re.split(r'[;,\n]+', manual_high_ids_raw):
                t = str(token).strip()
                if t:
                    high_priority_ids.add(t.upper())
        manual_high_titles_raw = os.getenv('FLOW_PMO_PORTFOLIO_HIGHEST_TITLES', '').strip()
        if manual_high_titles_raw:
            for token in re.split(r'[;,\n]+', manual_high_titles_raw):
                t = str(token).strip()
                if t:
                    high_priority_titles.add(t)
        candidate_projects = []
        if projeto:
            candidate_projects.append(str(projeto).strip().upper())
        if not df_portfolio_full_scope.empty and 'Projeto' in df_portfolio_full_scope.columns:
            for pval in df_portfolio_full_scope['Projeto'].dropna().astype(str).str.strip().unique():
                pkey = str(pval).strip().upper()
                if pkey:
                    candidate_projects.append(pkey)
                    if pkey == 'BT':
                        candidate_projects.extend(['BEFINANCE', 'BF'])

        seen_projects = set()
        for pkey in candidate_projects:
            if not pkey or pkey in seen_projects:
                continue
            seen_projects.add(pkey)
            try:
                down_df = load_project_downstream_items_csv(pkey)
            except Exception:
                down_df = pd.DataFrame()
            if down_df is None or down_df.empty or 'ID' not in down_df.columns:
                continue
            priority_col = None
            for cand in ['Prioridade', 'Priority', 'priority']:
                if cand in down_df.columns:
                    priority_col = cand
                    break
            if not priority_col:
                continue
            mask_high = down_df[priority_col].apply(portfolio_is_highest_priority)
            ids = down_df.loc[mask_high, 'ID'].dropna().astype(str).str.strip()
            if not ids.empty:
                high_priority_ids.update(x.upper() for x in ids if x)

        roadmap_full_section = html.Div([
            html.P(
                'Visão completa por épico (Q1..Q4). A segunda linha dos itens Running mostra o % de avanço no fluxo.',
                style={'color': '#666', 'marginBottom': '10px'}
            ),
            render_portfolio_roadmap_full_epics_view(
                df_portfolio_full_scope,
                selected_quarter='ALL',
                high_priority_ids=high_priority_ids,
                high_priority_titles=high_priority_titles
            )
        ], style={'paddingTop': '10px'})

        resumo_exec_section = html.Div([
            render_thresholds_config_summary(),
            render_portfolio_health_scorecard(portfolio_health_scorecard, portfolio_health_dimension_summary),
            render_portfolio_due_date_performance(due_date_performance),
            html.Div([
                html.Div([
                    html.Div('Escopo', style={'fontSize': '13px', 'fontWeight': '700', 'color': '#334155', 'marginBottom': '8px'}),
                    html.Div([
                        html.Div([
                            html.Div('TOTAL DE ÉPICOS', style={'fontSize': '11px', 'fontWeight': '700', 'color': '#bf360c', 'letterSpacing': '0.3px'}),
                            html.Div(f"{total_epicos_visao}", style={'fontSize': '28px', 'fontWeight': '800', 'color': '#bf360c', 'lineHeight': '1.1', 'marginTop': '4px'}),
                        ], style={'padding': '10px 14px', 'borderRadius': '10px', 'backgroundColor': '#fff3e0', 'border': '1px solid #e65100', 'minHeight': '90px'}),
                        html.Div([
                            html.Div('TOTAL DE FEATURES', style={'fontSize': '11px', 'fontWeight': '700', 'color': '#4a148c', 'letterSpacing': '0.3px'}),
                            html.Div(f"{total_features_visao}", style={'fontSize': '28px', 'fontWeight': '800', 'color': '#4a148c', 'lineHeight': '1.1', 'marginTop': '4px'}),
                        ], style={'padding': '10px 14px', 'borderRadius': '10px', 'backgroundColor': '#f3e5f5', 'border': '1px solid #7b1fa2', 'minHeight': '90px'}),
                    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(150px, 1fr))', 'gap': '8px'}),
                ], style={'marginBottom': '16px'}),
                html.Div([
                    html.Div('Hierarquia', style={'fontSize': '13px', 'fontWeight': '700', 'color': '#334155', 'marginBottom': '8px'}),
                    html.Div([
                        html.Div([
                            html.Div('ÉPICOS SEM FEATURES', style={'fontSize': '11px', 'fontWeight': '700', 'color': '#bf360c', 'letterSpacing': '0.3px'}),
                            html.Div(f"{epicos_sem_features_visao}", style={'fontSize': '28px', 'fontWeight': '800', 'color': '#bf360c', 'lineHeight': '1.1', 'marginTop': '4px'}),
                        ], style={'padding': '10px 14px', 'borderRadius': '10px', 'backgroundColor': '#fff3e0', 'border': '1px solid #e65100', 'minHeight': '90px'}),
                        html.Div([
                            html.Div('FEATURES SEM ÉPICO', style={'fontSize': '11px', 'fontWeight': '700', 'color': '#4a148c', 'letterSpacing': '0.3px'}),
                            html.Div(f"{features_sem_epico_visao}", style={'fontSize': '28px', 'fontWeight': '800', 'color': '#4a148c', 'lineHeight': '1.1', 'marginTop': '4px'}),
                        ], style={'padding': '10px 14px', 'borderRadius': '10px', 'backgroundColor': '#f3e5f5', 'border': '1px solid #7b1fa2', 'minHeight': '90px'}),
                        html.Div([
                            html.Div('FEATURES SEM FILHOS', style={'fontSize': '11px', 'fontWeight': '700', 'color': '#4a148c', 'letterSpacing': '0.3px'}),
                            html.Div(f"{features_sem_filhos_visao}", style={'fontSize': '28px', 'fontWeight': '800', 'color': '#4a148c', 'lineHeight': '1.1', 'marginTop': '4px'}),
                        ], style={'padding': '10px 14px', 'borderRadius': '10px', 'backgroundColor': '#f3e5f5', 'border': '1px solid #7b1fa2', 'minHeight': '90px'}),
                        html.Div([
                            html.Div('HISTÓRIAS/TASKS SEM FEATURE', style={'fontSize': '11px', 'fontWeight': '700', 'color': '#0d47a1', 'letterSpacing': '0.3px'}),
                            html.Div(f"{hist_tasks_sem_feature_visao}", style={'fontSize': '28px', 'fontWeight': '800', 'color': '#0d47a1', 'lineHeight': '1.1', 'marginTop': '4px'}),
                        ], style={'padding': '10px 14px', 'borderRadius': '10px', 'backgroundColor': '#e3f2fd', 'border': '1px solid #1565c0', 'minHeight': '90px'}),
                    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(150px, 1fr))', 'gap': '8px'}),
                ], style={'marginBottom': '16px'}),
                html.Div([
                    html.Div('Inatividade', style={'fontSize': '13px', 'fontWeight': '700', 'color': '#334155', 'marginBottom': '8px'}),
                    html.Div([
                        html.Div([
                            html.Div('SEM MOVIMENTO 15D / 30D', style={'fontSize': '11px', 'fontWeight': '700', 'color': '#263238', 'letterSpacing': '0.3px'}),
                            html.Div(f"{features_sem_mov_15_visao} / {features_sem_mov_30_visao}", style={'fontSize': '28px', 'fontWeight': '800', 'color': '#263238', 'lineHeight': '1.1', 'marginTop': '4px'}),
                        ], style={'padding': '10px 14px', 'borderRadius': '10px', 'backgroundColor': '#eceff1', 'border': '1px solid #455a64', 'minHeight': '90px'}),
                    ], style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fill, minmax(150px, 1fr))', 'gap': '8px'}),
                ], style={'marginBottom': '16px'}),
            ]),
            render_executive_tiles(executive_tiles),
            render_quality_cards(quality_por_team, quality_summary),
        ], style={'paddingTop': '10px'})

        alertas_section = render_portfolio_alerts(
            portfolio_alert_kpis,
            portfolio_alerts_severity_summary,
            portfolio_alerts_indicator_summary,
            portfolio_alerts_detail,
            portfolio_alerts_by_team,
            portfolio_alerts_by_project,
            portfolio_extra_onepage_summary,
            portfolio_technical_readiness_notes,
            portfolio_technical_epic_summary,
            portfolio_technical_items_catalog,
        )

        aging_fluxo_section = html.Div([
            render_flow_distribution_and_load(
                flow_distribution_by_type,
                flow_distribution_by_status,
                flow_distribution_by_team,
                stage_load_summary,
                stage_load_detail,
                stage_limit_alerts,
            ),
            render_flow_health_dynamic(items_base_scope),
            render_q_pendencias_grid(pendencias_q_por_time, pendencias_breakdown, pendencias_detalhe),
            html.Div([
                html.H3('Indicador 2 - Aging WIP por TEAM', style={'textAlign': 'left'}),
                html.Div([
                    html.Div(render_tiles_by_team(aging_us_20, aging_label_us_20, threshold_key='aging_us_20'), className='six columns'),
                    html.Div(render_tiles_by_team(aging_features_40, 'Features com mais de 40 dias em processo sem alteração', threshold_key='aging_features_40'), className='six columns'),
                ], className='row'),
                html.Div([
                    html.Div(render_tiles_by_team(aging_us_comp_20, aging_label_us_comp_20, threshold_key='aging_us_comp_20'), className='six columns'),
                    html.Div(render_tiles_by_team(aging_features_comp_40, 'Features compromissadas a mais de 40 dias e em processo', threshold_key='aging_features_comp_40'), className='six columns'),
                ], className='row'),
            ], style={'marginTop': '20px'}),
            render_aging_por_tipo_projeto(aging_por_tipo, aging_por_projeto),
            render_aging_buckets(aging_buckets_por_team),
            render_decision_queue(decision_queue_aging, decision_queue_summary),
            render_dynamic_decision_queue(items_base_scope),
            render_dynamic_sla_aging(items_base_scope),
            render_data_freshness_dynamic(items_base_scope),
        ], style={'paddingTop': '10px'})

        estrutura_section = html.Div([
            render_estrutura_cobertura(estrutura_cobertura_summary, estrutura_cobertura_por_team),
            html.Div([
                html.Div([
                    html.H4('Visão de Épicos', style={'textAlign': 'center'}),
                    portfolio_table_component(
                        epicos_complexidade,
                        'Épicos por TEAM e complexidade',
                        'table-portfolio-epicos-complexidade'
                    ),
                    portfolio_table_component(
                        epicos_detalhe,
                        'Backlog de Épicos (detalhado)',
                        'table-portfolio-epicos-detalhe'
                    ),
                ], className='six columns'),
                html.Div([
                    html.H4('Visão de Features', style={'textAlign': 'center'}),
                    portfolio_table_component(
                        features_complexidade,
                        'Features por TEAM e complexidade',
                        'table-portfolio-features-complexidade'
                    ),
                    portfolio_table_component(
                        features_detalhe,
                        'Backlog de Features (detalhado)',
                        'table-portfolio-features-detalhe'
                    ),
                ], className='six columns'),
            ], className='row', style={'marginTop': '10px'}),
            portfolio_table_component(
                epicos_fluxo_etapas,
                'Épicos: quantidade de itens por etapa de fluxo',
                'table-portfolio-epicos-fluxo-etapas'
            ),
        ], style={'paddingTop': '10px'})

        workflow_section = html.Div([
            html.Div([
                html.Div([
                    grouped_chart(
                        epicos_status,
                        x_col='Status',
                        y_col='QtdEpicos',
                        color_col='Team',
                        title='Épicos por TEAM e etapa de fluxo'
                    ),
                ], className='six columns'),
                html.Div([
                    grouped_chart(
                        features_status,
                        x_col='Status',
                        y_col='QtdFeatures',
                        color_col='Team',
                        title='Features por TEAM e etapa de fluxo'
                    ),
                ], className='six columns'),
            ], className='row', style={'marginTop': '10px'}),
            render_status_ranking(status_categoria_por_team, status_ranking_por_team),
            render_heatmap_team_status(heatmap_team_status),
            render_status_conformance(workflow_conformance_por_team, status_original_top, status_fora_workflow_top),
            render_dynamic_workflow_conformance(items_base_scope),
        ], style={'paddingTop': '10px'})

        effort_concentracao_section = html.Div([
            render_features_sem_effort(features_sem_effort_por_team),
            render_effort_distribution(effort_features_por_team),
            render_effort_aging_staleness(features_detalhe),
            html.Div([
                html.Div(
                    render_team_total_tiles(epicos_por_team_total, 'QtdEpicos', 'Total de Épicos por TEAM', color='#2e7d32'),
                    className='six columns'
                ),
                html.Div(
                    render_team_total_tiles(features_por_team_total, 'QtdFeatures', 'Total de Features por TEAM', color='#1565c0'),
                    className='six columns'
                ),
            ], className='row', style={'marginTop': '10px'}),
            render_concentracao_epicos(top_epicos_volume, top_epicos_aging),
            render_concentracao_relativa(concentracao_summary, concentracao_team_share, concentracao_epico_share),
            render_pareto_hhi(concentracao_team_share, concentracao_epico_share),
            render_mix_explicito_multi_contexto(items_base_scope),
            render_tipo_balanceamento(tipo_balanceamento),
        ], style={'paddingTop': '10px'})

        not_started_epics = pd.DataFrame()
        if epicos_detalhe is not None and not epicos_detalhe.empty and 'StatusCategoria' in epicos_detalhe.columns:
            not_started_epics = epicos_detalhe[epicos_detalhe['StatusCategoria'] == 'Backlog'].copy()

        not_started_features = pd.DataFrame()
        if features_detalhe is not None and not features_detalhe.empty and 'StatusCategoria' in features_detalhe.columns:
            not_started_features = features_detalhe[features_detalhe['StatusCategoria'] == 'Backlog'].copy()

        not_started_section = html.Div()
        if portfolio_quarter != 'ALL' and (not not_started_epics.empty or not not_started_features.empty):
            children = [html.H4(f"Itens de Portfólio para {portfolio_quarter} Não Iniciados", style={'textAlign': 'left'})]
            if not not_started_epics.empty:
                children.append(portfolio_table_component(
                    not_started_epics[['EpicID', 'Titulo', 'Team', 'Status']],
                    'Épicos não iniciados',
                    'table-portfolio-epics-not-started'
                ))
            if not not_started_features.empty:
                children.append(portfolio_table_component(
                    not_started_features[['FeatureID', 'Titulo', 'Team', 'Status']],
                    'Features não iniciadas',
                    'table-portfolio-features-not-started'
                ))
            not_started_section = html.Div(children, style={'marginTop': '20px'})

        pm_portfolio_data = build_pm_portfolio_capex_view(
            start_date,
            end_date,
            df_portfolio_full_scope,
            project_value=effective_portfolio_project or projeto,
            responsavel=responsavel,
        )
        generated_financials = build_generated_portfolio_financial_view(
            start_date,
            end_date,
            df_portfolio_full_scope,
            pm_portfolio_data,
        )
        cross_delivery_data = build_portfolio_cross_delivery_integration(
            start_date,
            end_date,
            df_portfolio_full_scope,
            pm_portfolio_data,
            generated_financials,
        )
        pm_product_summary = pm_portfolio_data.get('product_summary', pd.DataFrame()).copy()
        pm_top_assets = pm_portfolio_data.get('top_assets', pd.DataFrame()).copy()
        pm_overall = pm_portfolio_data.get('overall', {})

        pm_chart = go.Figure()
        if not pm_product_summary.empty:
            pm_chart_df = pm_product_summary[['Produto', 'Horas PM Mapeadas', 'Horas PM Não Mapeadas']].copy()
            pm_chart_df = pm_chart_df.melt(
                id_vars=['Produto'],
                value_vars=['Horas PM Mapeadas', 'Horas PM Não Mapeadas'],
                var_name='Faixa',
                value_name='Horas',
            )
            pm_chart_df['Faixa'] = pm_chart_df['Faixa'].replace({
                'Horas PM Mapeadas': 'Horas elegíveis mapeadas',
                'Horas PM Não Mapeadas': 'Horas elegíveis não mapeadas',
            })
            pm_chart = px.bar(
                pm_chart_df,
                x='Produto',
                y='Horas',
                color='Faixa',
                barmode='stack',
                title='Horas elegíveis por produto',
                color_discrete_map={
                    'Horas elegíveis mapeadas': '#2e7d32',
                    'Horas elegíveis não mapeadas': '#c62828',
                },
            )
            pm_chart.update_layout(height=420, xaxis_title='Produto', yaxis_title='Horas')

        def _fmt_number_br(value, decimals=1):
            if pd.isna(value):
                return '—'
            try:
                number = float(value)
            except Exception:
                return '—'
            formatted = f"{number:,.{int(decimals)}f}"
            return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')

        def _fmt_percent_br(value, decimals=1):
            if pd.isna(value):
                return '—'
            try:
                number = float(value)
            except Exception:
                return '—'
            return f"{_fmt_number_br(number * 100.0, decimals)}%"

        def _fmt_currency_compact_br(value):
            if pd.isna(value):
                return '—'
            try:
                number = float(value)
            except Exception:
                return '—'
            abs_number = abs(number)
            if abs_number >= 1_000_000:
                return f"R$ {_fmt_number_br(number / 1_000_000.0, 2)} mi"
            if abs_number >= 1_000:
                return f"R$ {_fmt_number_br(number / 1_000.0, 2)} mil"
            return f"R$ {_fmt_number_br(number, 2)}"

        def _fmt_currency_hour_br(value):
            if pd.isna(value):
                return '—'
            try:
                number = float(value)
            except Exception:
                return '—'
            return f"R$ {_fmt_number_br(number, 2)}/h"

        def _clean_exec_label(value):
            text = str(value or '').strip()
            if not text:
                return '—'
            replacements = [
                ('Process mining', 'Fluxo estimado'),
                ('process mining', 'fluxo estimado'),
                ('Process Mining', 'Fluxo estimado'),
                ('PM', 'Fluxo'),
            ]
            for old, new in replacements:
                text = text.replace(old, new)
            return text

        portfolio_metric_grid_style = {
            'display': 'grid',
            'gridTemplateColumns': 'repeat(auto-fit, minmax(180px, 1fr))',
            'gap': '12px',
        }

        pm_overall_cards = html.Div([
            _portfolio_metric_card('Horas de execução elegíveis', _fmt_number_br(pm_overall.get('hours', 0.0), 1)),
            _portfolio_metric_card('% horas mapeadas', _fmt_percent_br(pm_overall.get('mapped_pct'), 1)),
            _portfolio_metric_card('Horas reais apontadas', _fmt_number_br(pm_overall.get('actual_hours', 0.0), 1)),
            _portfolio_metric_card('% custo real mapeado', _fmt_percent_br(pm_overall.get('actual_mapped_pct_cost'), 1)),
            _portfolio_metric_card('Produtos com cobertura de fluxo', str(int(pm_overall.get('products_with_artifacts', 0)))),
            _portfolio_metric_card('Ativos c/ custo real', str(int(pm_overall.get('actual_assets_mapped', 0)))),
            _portfolio_metric_card('Custo real apontado', _fmt_currency_compact_br(pm_overall.get('actual_cost', 0.0)) if pm_overall.get('actual_cost_configured') else '—'),
            _portfolio_metric_card('Custo estimado de execução', _fmt_currency_compact_br(pm_overall.get('cost', 0.0)) if pm_overall.get('cost_configured') else '—'),
        ], style=portfolio_metric_grid_style)

        pm_product_cards = []
        for row in pm_product_summary.to_dict(orient='records'):
            pm_product_cards.append(
                create_kpi_card(
                    f"{row.get('Produto', '')} | horas elegíveis",
                    _fmt_number_br(row.get('Horas PM Elegíveis', 0.0), 1),
                    class_name='',
                    **portfolio_kpi_style(_pm_product_color(row.get('Projeto PM')))
                )
            )

        pm_summary_display = pm_product_summary.copy()
        if not pm_summary_display.empty:
            for col in [
                'Horas PM Elegíveis', 'Horas PM Mapeadas', 'Horas PM Não Mapeadas', '% Horas Mapeadas',
                'Taxa Hora PM', 'Custo PM Estimado', 'Custo PM Mapeado',
                'Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Custo Real Mapeado (R$)', '% Custo Real Mapeado'
            ]:
                if col in pm_summary_display.columns:
                    pm_summary_display[col] = pd.to_numeric(pm_summary_display[col], errors='coerce').round(2)

        pm_top_assets_display = pm_top_assets.head(20).copy()
        if not pm_top_assets_display.empty:
            for col in ['Horas PM Elegíveis', 'Custo PM Estimado', 'Horas Reais Apontadas', 'Custo Real Apontado (R$)']:
                if col in pm_top_assets_display.columns:
                    pm_top_assets_display[col] = pd.to_numeric(pm_top_assets_display[col], errors='coerce').round(2)

        cost_kpi_cards = html.Div()
        cost_notes = []
        cost_portfolio_display = pd.DataFrame()
        cost_product_display = pd.DataFrame()
        cost_rates_display = pd.DataFrame()
        if generated_financials.get('available'):
            cost_kpis = generated_financials.get('kpis', {})

            def _fmt_currency(value):
                if pd.isna(value):
                    return '—'
                try:
                    return f"R$ {float(value):,.2f}"
                except Exception:
                    return '—'

            def _fmt_pct(value):
                if pd.isna(value):
                    return '—'
                try:
                    return f"{float(value) * 100:.1f}%"
                except Exception:
                    return '—'

            cost_kpi_cards = html.Div([
                _portfolio_metric_card('Budget TI anual', _fmt_currency_compact_br(cost_kpis.get('Budget TI Anual'))),
                _portfolio_metric_card('Custo base do portfólio', _fmt_currency_compact_br(cost_kpis.get('Custo Total do Portfólio'))),
                _portfolio_metric_card('Fonte primária', _clean_exec_label(cost_kpis.get('Fonte Primária Custo', '—'))),
                _portfolio_metric_card('Custo real apontado', _fmt_currency_compact_br(cost_kpis.get('Custo Real Apontado'))),
                _portfolio_metric_card('Custo estimado de execução', _fmt_currency_compact_br(cost_kpis.get('Custo Estimado PM'))),
                _portfolio_metric_card('Budget disponível', _fmt_currency_compact_br(cost_kpis.get('Budget Disponível'))),
                _portfolio_metric_card('% budget comprometido', _fmt_percent_br(cost_kpis.get('% Budget Comprometido'), 1)),
                _portfolio_metric_card('Custo hora carregado', _fmt_currency_hour_br(cost_kpis.get('Custo Hora Carregado'))),
                _portfolio_metric_card('% custo real mapeado', _fmt_percent_br(cost_kpis.get('% Custo Real Mapeado'), 1)),
                _portfolio_metric_card('Custo médio projeto TD', _fmt_currency_compact_br(cost_kpis.get('Custo Médio Projeto (Top-Down)'))),
                _portfolio_metric_card('Custo médio projeto BU', _fmt_currency_compact_br(cost_kpis.get('Custo Médio Projeto (Bottom-Up)'))),
            ], style=portfolio_metric_grid_style)
            cost_notes.append(
                html.P(
                    'Régua financeira híbrida: prioriza worklog real do Jira e usa trilha estimada de fluxo apenas como complemento.',
                    style={'color': '#555', 'marginBottom': '8px'}
                )
            )
            cost_model_snapshot = generated_financials.get('cost_model', {})
            model_kpis = cost_model_snapshot.get('kpis', {}) if isinstance(cost_model_snapshot, dict) else {}
            if float(model_kpis.get('Budget TI Anual', 0) or 0) <= 0:
                cost_notes.append(
                    html.P(
                        'O budget anual está zerado. Configure `FLOW_PMO_PORTFOLIO_COST_MODEL.fl_mensal` para ativar a régua top-down.',
                        style={'color': '#8a6d3b', 'marginBottom': '8px'}
                    )
                )
            if float(model_kpis.get('Custo Hora Carregado', 0) or 0) <= 0:
                cost_notes.append(
                    html.P(
                        'O custo hora heurístico está zerado. Configure `FLOW_PMO_PORTFOLIO_COST_MODEL.salario_medio_bruto` ou mapas por papel/BU para monetizar as horas do portfólio.',
                        style={'color': '#8a6d3b', 'marginBottom': '8px'}
                    )
                )
            for note in generated_financials.get('notes', []):
                cost_notes.append(
                    html.P(_clean_exec_label(note), style={'color': '#8a6d3b', 'marginBottom': '8px'})
                )
            cost_portfolio_display = generated_financials.get('project_costs_df', pd.DataFrame()).copy()
            cost_product_display = generated_financials.get('product_cost_summary_df', pd.DataFrame()).copy()
            cost_rates_display = generated_financials.get('product_rates_df', pd.DataFrame()).copy()
            if not cost_portfolio_display.empty:
                for col in ['Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Horas PM Elegíveis', 'Custo PM Estimado', 'Custo Base Período (R$)', 'Custo Base Anualizado (R$)', '% do Budget TI Anual']:
                    if col in cost_portfolio_display.columns:
                        cost_portfolio_display[col] = pd.to_numeric(cost_portfolio_display[col], errors='coerce').round(2)
            if not cost_product_display.empty:
                for col in ['Horas Reais Apontadas', 'Custo Real Apontado (R$)', 'Custo Real Mapeado (R$)', '% Custo Real Mapeado', 'Horas PM Elegíveis', 'Horas PM Mapeadas', 'Horas PM Não Mapeadas', '% Horas Mapeadas', 'Taxa Hora PM', 'Custo PM Estimado', 'Custo Base Período (R$)', 'Custo Base Anualizado (R$)', '% do Budget TI Anual']:
                    if col in cost_product_display.columns:
                        cost_product_display[col] = pd.to_numeric(cost_product_display[col], errors='coerce').round(2)
            if not cost_rates_display.empty:
                for col in ['Headcount', 'Custo Mensal Produto (R$)', 'Capacidade Mensal Produto (h)', 'Custo Hora Produto (R$)']:
                    if col in cost_rates_display.columns:
                        cost_rates_display[col] = pd.to_numeric(cost_rates_display[col], errors='coerce').round(2)
        else:
            cost_notes.append(
                html.P(
                    _clean_exec_label(generated_financials.get('error', 'Régua financeira heurística não disponível.')),
                    style={'color': '#8a6d3b', 'marginBottom': '8px'}
                )
            )

        pm_notes = [
            html.P(
                'As horas elegíveis usam apenas permanência em estados de execução; custo real apontado vem dos worklogs CAPEX quando disponíveis.',
                style={'color': '#555', 'marginBottom': '6px'}
            )
        ]
        if not pm_overall.get('actual_cost', 0):
            pm_notes.append(
                html.P(
                    'Sem worklog real monetizado no período atual; o dashboard continua exibindo a trilha estimada de execução.',
                    style={'color': '#8a6d3b', 'marginBottom': '6px'}
                )
            )
        if not pm_overall.get('cost_configured'):
            pm_notes.append(
                html.P(
                    'O custo monetário usa o custo hora heurístico do modelo financeiro e pode ser refinado por produto com `FLOW_PMO_PM_COST_PER_HOUR_MAP`.',
                    style={'color': '#8a6d3b', 'marginBottom': '6px'}
                )
            )
        pm_has_hours = False
        if not pm_product_summary.empty and 'Horas PM Elegíveis' in pm_product_summary.columns:
            pm_has_hours = pd.to_numeric(pm_product_summary['Horas PM Elegíveis'], errors='coerce').fillna(0).gt(0).any()
        if not pm_has_hours:
            pm_notes.append(
                html.P(
                    'Sem horas elegíveis de execução no período/filtros atuais. Verifique a disponibilidade dos artefatos de fluxo para os produtos em escopo.',
                    style={'color': '#b22222', 'marginBottom': '0'}
                )
            )

        capex_worklog_df = (
            pm_portfolio_data.get('capex_cost_data', {}).get('df', pd.DataFrame())
            if isinstance(pm_portfolio_data, dict) else pd.DataFrame()
        )
        real_capex_worklog_df = _pm_filter_real_worklog_df(capex_worklog_df)
        has_real_capex_worklog = _pm_has_real_worklog_data(capex_worklog_df)
        events_all_df = pm_portfolio_data.get('events_all', pd.DataFrame()) if isinstance(pm_portfolio_data, dict) else pd.DataFrame()
        all_events_df_full = pm_portfolio_data.get('all_events_df', pd.DataFrame()) if isinstance(pm_portfolio_data, dict) else pd.DataFrame()
        custo_hora_val = float((generated_financials.get('kpis', {}) or {}).get('Custo Hora Carregado', 0.0) or 0.0)
        custo_por_atividade_section = _build_custo_por_atividade_section(capex_worklog_df)
        custo_por_fase_section = _build_custo_por_fase_section(events_all_df, capex_worklog_df)
        _touch_time_df = pm_portfolio_data.get('touch_time_triangulation', pd.DataFrame()) if isinstance(pm_portfolio_data, dict) else pd.DataFrame()
        custo_issue_value_section = (
            _build_custo_estimado_vs_real_section(events_all_df, real_capex_worklog_df)
            if has_real_capex_worklog else
            _build_custo_pm_calibrado_section(events_all_df, touch_time_df=_touch_time_df)
        )
        custo_retrabalho_section = _build_custo_retrabalho_section(events_all_df, capex_worklog_df)
        custo_espera_section = _build_custo_espera_section(
            all_events_df_full,
            custo_hora_val,
            strategic_items_df=items_base_scope,
        )

        pm_summary_display = pm_summary_display.rename(columns={
            'Projeto PM': 'Equipe de fluxo',
            'Artefato PM': 'Cobertura de fluxo',
            'Horas PM Elegíveis': 'Horas elegíveis',
            'Horas PM Mapeadas': 'Horas elegíveis mapeadas',
            'Horas PM Não Mapeadas': 'Horas elegíveis não mapeadas',
            'Taxa Hora PM': 'Taxa hora estimada',
            'Custo PM Estimado': 'Custo estimado',
            'Custo PM Mapeado': 'Custo estimado mapeado',
        })
        pm_top_assets_display = pm_top_assets_display.rename(columns={
            'Projeto PM': 'Equipe de fluxo',
            'Responsável PM': 'Responsável',
            'Horas PM Elegíveis': 'Horas elegíveis',
            'Custo PM Estimado': 'Custo estimado',
        })
        cost_product_display = cost_product_display.rename(columns={
            'Horas PM Elegíveis': 'Horas elegíveis',
            'Horas PM Mapeadas': 'Horas elegíveis mapeadas',
            'Horas PM Não Mapeadas': 'Horas elegíveis não mapeadas',
            'Taxa Hora PM': 'Taxa hora estimada',
            'Custo PM Estimado': 'Custo estimado',
        })
        cost_portfolio_display = cost_portfolio_display.rename(columns={
            'Horas PM Elegíveis': 'Horas elegíveis',
            'Custo PM Estimado': 'Custo estimado',
        })

        executive_alerts = []
        mapped_pct = float(pm_overall.get('mapped_pct', 0.0) or 0.0)
        budget_commit_pct = float((generated_financials.get('kpis', {}) or {}).get('% Budget Comprometido', 0.0) or 0.0)
        if not pm_overall.get('actual_cost', 0):
            executive_alerts.append(('Ação imediata', 'Sem custo real apontado no período. Priorize capturar worklogs nas frentes críticas para substituir a estimativa.'))
        if mapped_pct < 0.6:
            executive_alerts.append(('Cobertura fraca', f'Apenas {_fmt_percent_br(mapped_pct, 1)} das horas elegíveis estão mapeadas ao portfólio. Revise vínculos de ativos/produtos.'))
        if budget_commit_pct >= 0.8:
            executive_alerts.append(('Pressão de budget', f'O portfólio já comprometeu {_fmt_percent_br(budget_commit_pct, 1)} do budget anual. Reavalie prioridades e fila de entrada.'))
        if pm_has_hours and mapped_pct >= 0.6 and pm_overall.get('actual_cost', 0):
            executive_alerts.append(('Leitura atual', 'A cobertura de execução e custo já permite leitura comparativa entre produtos. Foque os gargalos e o custo de espera abaixo.'))

        executive_alert_cards = html.Div([
            html.Div([
                html.Div(title, style={'fontSize': '12px', 'fontWeight': '700', 'color': '#102a43', 'marginBottom': '6px'}),
                html.Div(message, style={'fontSize': '13px', 'color': '#334e68', 'lineHeight': '1.45'}),
            ], style={
                'backgroundColor': '#f8fbff',
                'border': '1px solid #d9e6f2',
                'borderRadius': '12px',
                'padding': '14px 16px',
                'boxShadow': '0 1px 2px rgba(16, 42, 67, 0.05)',
            }) for title, message in executive_alerts
        ], style={
            'display': 'grid',
            'gridTemplateColumns': 'repeat(auto-fit, minmax(240px, 1fr))',
            'gap': '12px',
            'marginTop': '12px',
            'marginBottom': '14px',
        }) if executive_alerts else html.Div()

        executive_summary_section = html.Div([
            html.H4('KPIs Prioritários', style={'textAlign': 'left', 'marginTop': '10px', 'marginBottom': '8px'}),
            html.Div(pm_notes, style={'marginBottom': '8px'}),
            pm_overall_cards,
            executive_alert_cards,
        ])

        executive_visual_section = html.Div([
            html.H4('Onde Agir Agora', style={'textAlign': 'left', 'marginTop': '22px', 'marginBottom': '8px'}),
            html.P(
                'Comece pelos gráficos de atraso, custo calibrado e cobertura por produto. Os detalhamentos analíticos ficam abaixo.',
                style={'color': '#555', 'marginBottom': '12px'}
            ),
            custo_espera_section,
            custo_issue_value_section,
            html.H4('Cobertura e Custo por Produto', style={'textAlign': 'left', 'marginTop': '18px'}),
            html.Div(pm_product_cards, style={
                'display': 'grid',
                'gridTemplateColumns': 'repeat(auto-fill, minmax(180px, 1fr))',
                'gap': '10px',
                'marginTop': '12px',
            }) if pm_product_cards else html.Div(),
            html.Div([dcc.Graph(figure=pm_chart)], style={'marginTop': '14px'}),
            custo_por_fase_section,
            custo_por_atividade_section,
            custo_retrabalho_section,
        ])

        analytical_section = html.Div([
            html.H4('Base Analítica', style={'textAlign': 'left', 'marginTop': '22px'}),
            html.P(
                'Detalhamento financeiro e tabelas de apoio para investigação dos números executivos exibidos acima.',
                style={'color': '#555', 'marginBottom': '8px'}
            ),
            html.H4('Régua Financeira do Portfólio', style={'textAlign': 'left', 'marginTop': '8px'}),
            html.Div(cost_notes, style={'marginBottom': '8px'}),
            cost_kpi_cards,
            portfolio_table_component(
                cost_portfolio_display.head(20),
                'Top ativos por custo base do período',
                'table-portfolio-costs-generated-projects'
            ) if not cost_portfolio_display.empty else html.Div(),
            portfolio_table_component(
                cost_product_display,
                'Resumo financeiro por produto',
                'table-portfolio-costs-generated-products'
            ) if not cost_product_display.empty else html.Div(),
            portfolio_table_component(
                cost_rates_display,
                'Parâmetros e taxas heurísticas por produto',
                'table-portfolio-costs-generated-rates'
            ) if not cost_rates_display.empty else html.Div(),
            portfolio_table_component(
                pm_summary_display,
                'Resumo de execução e custo real por produto',
                'table-portfolio-process-mining-produto'
            ),
            portfolio_table_component(
                pm_top_assets_display,
                'Top ativos por custo real/estimado',
                'table-portfolio-process-mining-ativos'
            ),
        ])

        pm_portfolio_section = html.Div([
            executive_summary_section,
            executive_visual_section,
            analytical_section,
        ], style={'paddingTop': '10px'})
        cross_delivery_section = render_portfolio_cross_delivery(cross_delivery_data)

        # 4Ps — Governança TECH
        try:
            from datetime import date as _date_cls, datetime as _dt_cls
            _four_ps_month = _date_cls.today().replace(day=1)
            # Detecta tamanho do período a partir do filtro de quarter OU do intervalo de datas
            if portfolio_quarter and portfolio_quarter not in ('ALL', '', None) and portfolio_quarter.startswith('Q'):
                _four_ps_period = 3
            elif start_date and end_date:
                try:
                    _sd = _dt_cls.fromisoformat(str(start_date)[:10]).date()
                    _ed = _dt_cls.fromisoformat(str(end_date)[:10]).date()
                    _four_ps_period = 3 if (_ed - _sd).days >= 80 else 1
                except Exception:
                    _four_ps_period = 1
            else:
                _four_ps_period = 1
            _four_ps_kanban_data = _load_four_ps_kanban_data(_four_ps_month, period_months=_four_ps_period)
            _four_ps_payload = build_four_ps_payload(
                df_portfolio=df_portfolio_full_scope,
                kanban_data=_four_ps_kanban_data or None,
                month=_four_ps_month,
                period_months=_four_ps_period,
            )
            # Converte start_date/end_date para date para passar ao renderer
            try:
                _four_ps_start = _dt_cls.fromisoformat(str(start_date)[:10]).date() if start_date else None
                _four_ps_end   = _dt_cls.fromisoformat(str(end_date)[:10]).date()   if end_date   else None
            except Exception:
                _four_ps_start = _four_ps_end = None
            four_ps_section = render_four_ps_tab(
                _four_ps_payload,
                month=_four_ps_month,
                df_portfolio=df_portfolio_full_scope,
                period_months=_four_ps_period,
                date_start=_four_ps_start,
                date_end=_four_ps_end,
                kanban_data=_four_ps_kanban_data or None,
            )
        except Exception as _four_ps_err:
            four_ps_section = html.Div(
                html.P(f'Erro ao montar 4Ps: {_four_ps_err}',
                       style={'color': '#b22222', 'padding': '20px'}),
            )

        # ── Fase 3: Métricas Avançadas ─────────────────────────────────────
        def _p3_kpi(title, value, color='#1565C0'):
            return html.Div([
                html.Div(title, style={'fontSize': '11px', 'color': '#555', 'marginBottom': '4px'}),
                html.Div(str(value), style={'fontSize': '22px', 'fontWeight': 'bold', 'color': color}),
            ], style={
                'background': '#f5f8ff', 'border': f'1px solid {color}',
                'borderRadius': '8px', 'padding': '12px 16px', 'minWidth': '140px',
            })

        def _p3_bar(df_src, x, y, title, color=None, orientation='v', height=320):
            if df_src is None or df_src.empty:
                return html.Div(html.P(f'{title}: sem dados.', style={'color': '#888'}))
            kwargs = dict(x=x, y=y, title=title, template='plotly_white',
                          color=color, orientation=orientation)
            fig = px.bar(df_src, **{k: v for k, v in kwargs.items() if v is not None})
            fig.update_layout(height=height, margin=dict(t=45, b=60, l=60, r=20))
            return dcc.Graph(figure=fig, config={'displayModeBar': False})

        def _p3_line(df_src, x, y, title, height=280):
            if df_src is None or df_src.empty:
                return html.Div(html.P(f'{title}: sem dados.', style={'color': '#888'}))
            fig = px.line(df_src, x=x, y=y, title=title, template='plotly_white', markers=True)
            fig.update_layout(height=height, margin=dict(t=45, b=60, l=60, r=20))
            return dcc.Graph(figure=fig, config={'displayModeBar': False})

        def _p3_hist(df_src, x, title, height=300):
            if df_src is None or df_src.empty:
                return html.Div(html.P(f'{title}: sem dados.', style={'color': '#888'}))
            fig = px.histogram(df_src, x=x, title=title, template='plotly_white', nbins=20)
            fig.update_layout(height=height, margin=dict(t=45, b=60, l=60, r=20))
            return dcc.Graph(figure=fig, config={'displayModeBar': False})

        def _make_waste_bar(df_src, x_col, title, sort=True, height=360):
            if df_src is None or df_src.empty:
                return dcc.Graph(figure=go.Figure(), config={'displayModeBar': False})
            plot_df = df_src.copy()
            if sort:
                plot_df = plot_df.sort_values('Desperdícios do processo', ascending=False)
            fig = px.bar(
                plot_df,
                x=x_col,
                y=['Entregas de Valor', 'Desperdícios do processo'],
                title=title,
                barmode='stack',
                color_discrete_map={
                    'Entregas de Valor': '#27ae60',
                    'Desperdícios do processo': '#e74c3c',
                },
                template='plotly_white',
                labels={'value': 'Dias (média)', 'variable': ''},
            )
            fig.update_layout(
                height=height,
                yaxis_title='Dias (média)',
                legend_title_text='',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                margin=dict(t=60, b=60, l=60, r=20),
            )
            return dcc.Graph(figure=fig, config={'displayModeBar': False})

        _kpi_grid_style = {
            'display': 'grid',
            'gridTemplateColumns': 'repeat(auto-fill, minmax(160px, 1fr))',
            'gap': '10px', 'marginBottom': '16px',
        }
        _two_col = {'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '16px', 'marginBottom': '16px'}
        _section_title_style = {'borderLeft': '4px solid #1565C0', 'paddingLeft': '10px', 'marginTop': '24px', 'marginBottom': '10px'}

        # KPIs Fase 3
        _lt_p50_txt = f"{lead_time_p50}d" if lead_time_p50 is not None else '—'
        _lt_p85_txt = f"{lead_time_p85}d" if lead_time_p85 is not None else '—'
        _tp_w_txt = f"{throughput_weekly_avg}/sem" if throughput_weekly_avg else '—'
        _tp_m_txt = f"{throughput_monthly_avg}/mês" if throughput_monthly_avg else '—'

        _avancado_kpis = html.Div([
            _p3_kpi('Lead Time P50', _lt_p50_txt),
            _p3_kpi('Lead Time P85', _lt_p85_txt, '#6A1B9A'),
            _p3_kpi('Itens com lead time', lead_time_count, '#00695C'),
            _p3_kpi('Throughput médio/sem', _tp_w_txt, '#E65100'),
            _p3_kpi('Throughput médio/mês', _tp_m_txt, '#E65100'),
            _p3_kpi('Tema estratégico (%)', f"{pct_com_tema}%", '#1B5E20' if pct_com_tema >= 50 else '#BF360C'),
            _p3_kpi('Risco preenchido (%)', f"{pct_com_risco}%", '#1B5E20' if pct_com_risco >= 50 else '#BF360C'),
        ], style=_kpi_grid_style)

        # Lead Time
        _lt_bloqueio_note = html.Div(
            '⚠ Lead time requer CreatedAt e ResolvedAt preenchidos no CSV. Execute jira_portfolio_to_csv.py atualizado.',
            style={'color': '#7B3F00', 'background': '#FFF8E1', 'border': '1px solid #FFD54F',
                   'padding': '8px 12px', 'borderRadius': '6px', 'marginBottom': '10px',
                   'display': 'block' if lead_time_count == 0 else 'none'}
        )
        _lt_section = html.Div([
            html.H4('Lead Time de Portfólio', style=_section_title_style),
            _lt_bloqueio_note,
            html.Div([
                _p3_hist(lead_time_distribution, 'LeadTimeDias', 'Distribuição de Lead Time (dias)'),
                _p3_bar(lead_time_por_tipo, 'Tipo', 'P50', 'Lead Time P50 por Tipo (dias)', color='Tipo'),
            ], style=_two_col),
            html.Div([
                _p3_bar(lead_time_por_team.sort_values('P50', ascending=True) if not lead_time_por_team.empty else lead_time_por_team,
                        'P50', 'TeamDisplay', 'Lead Time P50 por Team (dias)', orientation='h'),
                _p3_bar(lead_time_por_tipo, 'Tipo', 'P85', 'Lead Time P85 por Tipo (dias)', color='Tipo'),
            ], style=_two_col),
        ])

        # Throughput
        _tp_section = html.Div([
            html.H4('Throughput de Portfólio', style=_section_title_style),
            html.Div([
                _p3_line(throughput_semanal, 'SemanaResolucao', 'Itens', 'Throughput Semanal (itens concluídos)'),
                _p3_line(throughput_mensal, 'MesResolucao', 'Itens', 'Throughput Mensal (itens concluídos)'),
            ], style=_two_col),
        ])

        # Alinhamento Estratégico
        _tema_bloqueio_note = html.Div(
            '⚠ Alinhamento estratégico requer campo StrategicTheme exportado. Configure strategic_theme em JIRA_FIELD_MAP.',
            style={'color': '#7B3F00', 'background': '#FFF8E1', 'border': '1px solid #FFD54F',
                   'padding': '8px 12px', 'borderRadius': '6px', 'marginBottom': '10px',
                   'display': 'block' if tema_distribuicao.empty else 'none'}
        )
        _tema_section = html.Div([
            html.H4('Alinhamento Estratégico', style=_section_title_style),
            _tema_bloqueio_note,
            html.Div([
                _p3_bar(tema_distribuicao, 'StrategicTheme', 'Itens', 'Distribuição por Tema Estratégico', color='StrategicTheme'),
                _p3_bar(tema_status_dist, 'StrategicTheme', 'Itens', 'Tema × Categoria de Status', color='StatusCategoria'),
            ], style=_two_col),
        ] + ([
            portfolio_table_component(
                tema_team_heatmap.pivot_table(index='TeamDisplay', columns='StrategicTheme', values='Itens', aggfunc='sum', fill_value=0).reset_index()
                if not tema_team_heatmap.empty else pd.DataFrame(),
                'Heatmap Team × Tema Estratégico',
                'table-portfolio-tema-heatmap'
            )
        ] if not tema_team_heatmap.empty else []))

        # Riscos
        _risk_bloqueio_note = html.Div(
            '⚠ Análise de riscos requer campo Risk exportado. Configure risk em JIRA_FIELD_MAP.',
            style={'color': '#7B3F00', 'background': '#FFF8E1', 'border': '1px solid #FFD54F',
                   'padding': '8px 12px', 'borderRadius': '6px', 'marginBottom': '10px',
                   'display': 'block' if risk_distribuicao.empty else 'none'}
        )
        _risk_section = html.Div([
            html.H4('Análise de Riscos', style=_section_title_style),
            _risk_bloqueio_note,
            html.Div([
                _p3_bar(risk_distribuicao, 'Risk', 'Itens', 'Distribuição por Nível de Risco', color='Risk'),
                _p3_bar(risk_aging, 'Risk', 'AgingMediano', 'Aging Mediano por Nível de Risco (dias)', color='Risk'),
            ], style=_two_col),
            _p3_bar(risk_por_tipo, 'Tipo', 'Itens', 'Risco × Tipo de Item', color='Risk', height=280),
        ])

        # Desperdício de Fluxo
        _waste_proj_df = build_waste_decomposition(df, 'Projeto')
        _waste_cs_df = build_waste_decomposition(df, 'ClasseServico')
        _waste_sim_df = build_scenario_simulation(df)

        _has_creation_date = any(
            c in df.columns for c in ['DataCriacao', 'DataCriacaoID', 'Created', 'CreatedDate', 'IssueCreated']
        )
        _waste_data_note = html.Div(
            '⚠ Data de criação do item não encontrada (DataCriacao/Created). '
            'O desperdício exibido usa LeadTime_Dias (DataBacklog→Done) como fallback, '
            'subestimando a fila pré-sprint. Para o gráfico completo, exporte DataCriacao do Jira.',
            style={'color': '#7B3F00', 'background': '#FFF8E1', 'border': '1px solid #FFD54F',
                   'padding': '8px 12px', 'borderRadius': '6px', 'marginBottom': '10px',
                   'display': 'none' if _has_creation_date else 'block'}
        )

        _waste_section = html.Div([
            html.H4('Desperdício de Fluxo', style=_section_title_style),
            html.P(
                'Decomposição do Lead Time médio em valor entregue (verde) e desperdício de processo (vermelho). '
                'Referência para priorizar intervenções de melhoria.',
                style={'color': '#555', 'marginBottom': '12px', 'fontSize': '13px'}
            ),
            _waste_data_note,
            html.Div([
                html.Div([
                    html.H5('Por Projeto', style={'fontSize': '13px', 'color': '#444', 'marginBottom': '4px'}),
                    _make_waste_bar(_waste_proj_df, 'Projeto', 'Desperdício por Projeto'),
                ], style={'flex': '1', 'minWidth': '380px'}),
                html.Div([
                    html.H5('Por Value Stream (Classe de Serviço)', style={'fontSize': '13px', 'color': '#444', 'marginBottom': '4px'}),
                    _make_waste_bar(_waste_cs_df, 'ClasseServico', 'Desperdício por Value Stream'),
                ], style={'flex': '1', 'minWidth': '380px'}),
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '20px', 'marginBottom': '20px'}),
            html.Div([
                html.H5('Simulação: Impacto de Diferentes Intervenções', style={'fontSize': '13px', 'color': '#444', 'marginBottom': '4px'}),
                html.P(
                    'Projeção hipotética a partir das médias atuais. '
                    'Contratar pessoas amplifica o desperdício; reduzir desperdícios é a alavanca mais eficiente.',
                    style={'color': '#777', 'fontSize': '12px', 'marginBottom': '6px'}
                ),
                _make_waste_bar(_waste_sim_df, 'Cenário', 'Intervenções: Impacto no Lead Time Médio', sort=False, height=340),
            ]),
        ], style={
            'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '10px',
            'marginBottom': '20px', 'border': '1px solid #e2e8f0',
        })

        avancado_section = html.Div([
            _avancado_kpis,
            _lt_section,
            _tp_section,
            _tema_section,
            _risk_section,
            _waste_section,
        ], style={'paddingTop': '10px'})
        # ── /Fase 3 ────────────────────────────────────────────────────────

        return html.Div([
            html.H3('Painel de Portfólio', style={'textAlign': 'center'}),
            html.P(
                f"Atualizado em: {snapshot['updated_at']} | Escopo: {scope_label} | Fonte: CSV local de portfólio",
                style={'textAlign': 'center', 'color': '#666'}
            ),
            portfolio_filter_alert,
            dcc.Tabs(
                id='tabs-portfolio-tematicas',
                value='portfolio-resumo-executivo',
                children=[
                    dcc.Tab(label='Resumo Executivo', value='portfolio-resumo-executivo', children=[resumo_exec_section]),
                    dcc.Tab(label='Alertas', value='portfolio-alertas', children=[alertas_section]),
                    dcc.Tab(label='One Page Completo', value='portfolio-one-page-completo', children=[roadmap_full_section]),
                    dcc.Tab(label='4Ps - Governança', value='portfolio-four-ps', children=[four_ps_section]),
                    dcc.Tab(label='Aging & Fluxo', value='portfolio-aging-fluxo', children=[aging_fluxo_section]),
                    dcc.Tab(label='Hierarquia & Estrutura', value='portfolio-estrutura', children=[estrutura_section]),
                    dcc.Tab(label='Status & Workflow', value='portfolio-status-workflow', children=[workflow_section]),
                    dcc.Tab(label='Effort & Concentração', value='portfolio-effort-concentracao', children=[effort_concentracao_section]),
                    dcc.Tab(label='Portfólio x Delivery', value='portfolio-cross-delivery', children=[cross_delivery_section]),
                    dcc.Tab(label='Custos & Fluxo', value='portfolio-process-mining-capex', children=[pm_portfolio_section]),
                    dcc.Tab(label='Métricas Avançadas', value='portfolio-avancado', children=[avancado_section]),
                ]
            ),
            not_started_section,
        ], style={'padding': '10px 20px 20px 20px'})

    if tab == 'tab-painel-3x3':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        # Base exibida no painel (respeita todos os filtros ativos).
        df_signal_base = df.copy()
        df_signal_base, _ = apply_selected_commitment_metric(df_signal_base, projeto, leadtime_stages)
        panel_stage_map = compute_current_stage_map(projeto) if projeto and etapa_fluxo else {}

        # Base viva para snapshots de backlog/WIP/estoque, sem recorte global por DataDone/Created.
        df_snapshot_base = filter_df(
            fato,
            None,
            None,
            projeto,
            tipo,
            classe_servico,
            responsavel,
            criadores=criadores,
            use_creation_date=use_creation_date,
            apply_date=False,
            tipo_original=tipo_original_jira,
        )
        df_snapshot_base, _ = apply_selected_lead_time_metric(df_snapshot_base, projeto, leadtime_stages)
        df_snapshot_base, _ = apply_selected_commitment_metric(df_snapshot_base, projeto, leadtime_stages)

        # Base de referência para thresholds (projeto/tipo), independente de período e responsável.
        df_threshold_base = filter_df(
            fato,
            None,
            None,
            projeto,
            tipo,
            classe_servico,
            None,
            criadores=None,
            use_creation_date=use_creation_date,
            apply_date=False,
            tipo_original=tipo_original_jira,
        )
        df_threshold_base, _ = apply_selected_lead_time_metric(df_threshold_base, projeto, leadtime_stages)
        df_threshold_base, _ = apply_selected_commitment_metric(df_threshold_base, projeto, leadtime_stages)

        weeks = pd.date_range(start=start_ts, end=end_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal.')

        strict_stage_start = bool(leadtime_meta.get('enabled', False))

        def datetime_col_or_nat(df_local, column_name):
            if column_name in df_local.columns:
                return pd.to_datetime(df_local[column_name], errors='coerce')
            return pd.Series(pd.NaT, index=df_local.index, dtype='datetime64[ns]')

        def selected_flow_start_series(df_local):
            if df_local is None or getattr(df_local, 'empty', True):
                return pd.Series(dtype='datetime64[ns]')
            s = pd.to_datetime(df_local.get('LeadStart_Selected'), errors='coerce')
            if not strict_stage_start:
                if 'DataBacklog' in df_local.columns:
                    s = s.fillna(df_local['DataBacklog'])
                if 'DataInProgress' in df_local.columns:
                    s = s.fillna(df_local['DataInProgress'])
            return s

        def build_weekly_metrics(df_source, start_ref, end_ref, stage_map=None, stage_filter=None):
            rows = []
            weeks_ref = pd.date_range(start=start_ref, end=end_ref + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
            if len(weeks_ref) < 2:
                return pd.DataFrame()
            backlog_start = datetime_col_or_nat(df_source, 'DataBacklog')
            commitment_start = datetime_col_or_nat(df_source, 'Commitment_Selected')
            for i in range(len(weeks_ref) - 1):
                week_start = weeks_ref[i]
                week_end = weeks_ref[i + 1]
                arrived = df_source[
                    (backlog_start >= week_start) &
                    (backlog_start < week_end)
                ]
                committed = df_source[
                    (commitment_start >= week_start) &
                    (commitment_start < week_end)
                ]
                done = df_source[
                    (df_source['DataDone'] >= week_start) &
                    (df_source['DataDone'] < week_end)
                ]
                backlog_items = df_source[
                    (backlog_start < week_end) &
                    ((commitment_start >= week_end) | commitment_start.isna())
                ]
                wip_items = df_source[
                    (commitment_start < week_end) &
                    ((df_source['DataDone'] >= week_end) | pd.isna(df_source['DataDone']))
                ]
                wip_items = filter_items_by_current_stage(
                    wip_items,
                    projeto=projeto,
                    selected_stages=stage_filter,
                    stage_map=stage_map,
                )
                total_system_items = pd.concat([backlog_items, wip_items], axis=0).drop_duplicates(subset=['ItemID']) if 'ItemID' in df_source.columns else pd.concat([backlog_items, wip_items], axis=0).drop_duplicates()

                lt_p85 = np.nan
                lt_p50 = np.nan
                lt_done = time_metric_series(done, 'LeadTime_Selected_Dias', non_negative=True)
                if not lt_done.empty:
                    lt_p85 = exact_empirical_percentile(lt_done, 0.85)
                    lt_p50 = exact_empirical_percentile(lt_done, 0.50)

                done_eligible = done[done_time_eligible_mask(done)] if not done.empty else done
                tp = len(done_eligible)
                ar = len(arrived)
                cm = len(committed)
                backlog = len(backlog_items)
                wip = len(wip_items)
                total_system = len(total_system_items)
                pressure_w, flow_eff_w = calculate_flow_efficiency(ar, tp)
                rows.append({
                    'Semana': week_start.date(),
                    'EntradasBacklog': ar,
                    'Compromissos': cm,
                    'Throughput': tp,
                    'Backlog': backlog,
                    'WIP': wip,
                    'EstoqueTotal': total_system,
                    'WIP_Age': (week_end - pd.to_datetime(wip_items.get('LeadStart_Selected'), errors='coerce')).dt.days.mean() if wip > 0 else np.nan,
                    'LeadTime_P85': lt_p85,
                    'FlowEfficiency': flow_eff_w,
                    'Pressure': pressure_w,
                    'QueueEfficiency': flow_eff_w,
                    'WIP_TP_Ratio': (wip / tp) if tp > 0 else np.nan,
                    'Predictability': (lt_p85 / lt_p50) if pd.notna(lt_p85) and pd.notna(lt_p50) and lt_p50 > 0 else np.nan,
                })
            return pd.DataFrame(rows)

        weekly_rows = []
        signal_backlog_start = datetime_col_or_nat(df_signal_base, 'DataBacklog')
        signal_commitment_start = datetime_col_or_nat(df_signal_base, 'Commitment_Selected')
        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]
            arrivals = len(df_signal_base[
                (signal_backlog_start >= week_start) &
                (signal_backlog_start < week_end)
            ])
            commitments = len(df_signal_base[
                (signal_commitment_start >= week_start) &
                (signal_commitment_start < week_end)
            ])
            done_week = df_signal_base[
                (df_signal_base['DataDone'] >= week_start) &
                (df_signal_base['DataDone'] < week_end)
            ]
            throughput = len(done_week[done_time_eligible_mask(done_week)]) if not done_week.empty else 0
            backlog = len(df_signal_base[
                (signal_backlog_start < week_end) &
                ((signal_commitment_start >= week_end) | signal_commitment_start.isna())
            ])
            wip_items_week = df_signal_base[
                (signal_commitment_start < week_end) &
                ((df_signal_base['DataDone'] >= week_end) | pd.isna(df_signal_base['DataDone']))
            ].copy()
            wip_items_week = filter_items_by_current_stage(
                wip_items_week,
                projeto=projeto,
                selected_stages=etapa_fluxo,
                stage_map=panel_stage_map,
            )
            wip = len(wip_items_week)
            total_system = backlog + wip
            weekly_rows.append({
                'Semana': week_start.date(),
                'EntradasBacklog': arrivals,
                'Compromissos': commitments,
                'Throughput': throughput,
                'Backlog': backlog,
                'WIP': wip,
                'EstoqueTotal': total_system,
            })
        weekly_df = pd.DataFrame(weekly_rows)

        # Histórico de referência para thresholds dinâmicos por projeto/tipo.
        date_candidates = []
        threshold_flow_start = selected_flow_start_series(df_threshold_base)
        if not threshold_flow_start.dropna().empty:
            date_candidates.append(threshold_flow_start.dropna().min())
        for col in ['DataDone']:
            if col in df_threshold_base.columns and not df_threshold_base[col].dropna().empty:
                date_candidates.append(df_threshold_base[col].dropna().min())
        if not date_candidates:
            date_candidates = [start_ts]
        hist_start = min(date_candidates)
        hist_end = end_ts
        weekly_hist_df = build_weekly_metrics(
            df_threshold_base,
            hist_start,
            hist_end,
            stage_map=panel_stage_map,
            stage_filter=etapa_fluxo,
        )

        df_done_period = df_signal_base[
            (df_signal_base['DataDone'] >= start_ts) &
            (df_signal_base['DataDone'] <= end_ts)
        ].copy()
        df_done_period_eligible = df_done_period[done_time_eligible_mask(df_done_period)].copy()
        demand_date = datetime_col_or_nat(df_signal_base, 'DataBacklog')
        commitment_date = datetime_col_or_nat(df_signal_base, 'Commitment_Selected')
        df_arrived_period = df_signal_base[
            (demand_date >= start_ts) &
            (demand_date <= end_ts)
        ]
        df_demand_period = df_arrived_period
        demand_label = "itens que entraram em backlog no período"

        snapshot_demand_date = datetime_col_or_nat(df_snapshot_base, 'DataBacklog')
        snapshot_commitment_date = datetime_col_or_nat(df_snapshot_base, 'Commitment_Selected')

        df_backlog_start = df_snapshot_base[
            (snapshot_demand_date < start_ts) &
            ((snapshot_commitment_date >= start_ts) | snapshot_commitment_date.isna())
        ].copy()
        df_backlog_end = df_snapshot_base[
            (snapshot_demand_date <= end_ts) &
            ((snapshot_commitment_date > end_ts) | snapshot_commitment_date.isna())
        ].copy()
        df_wip_start = df_snapshot_base[
            (snapshot_commitment_date < start_ts) &
            ((df_snapshot_base['DataDone'] >= start_ts) | pd.isna(df_snapshot_base['DataDone']))
        ].copy()
        df_wip_end = df_snapshot_base[
            (snapshot_commitment_date <= end_ts) &
            ((df_snapshot_base['DataDone'] > end_ts) | pd.isna(df_snapshot_base['DataDone']))
        ].copy()
        df_wip_start = filter_items_by_current_stage(
            df_wip_start,
            projeto=projeto,
            selected_stages=etapa_fluxo,
            stage_map=panel_stage_map,
        )
        df_wip_end = filter_items_by_current_stage(
            df_wip_end,
            projeto=projeto,
            selected_stages=etapa_fluxo,
            stage_map=panel_stage_map,
        )
        if 'ItemID' in df_snapshot_base.columns:
            df_inventory_start = pd.concat([df_backlog_start, df_wip_start], axis=0).drop_duplicates(subset=['ItemID']).copy()
            df_inventory_end = pd.concat([df_backlog_end, df_wip_end], axis=0).drop_duplicates(subset=['ItemID']).copy()
        else:
            df_inventory_start = pd.concat([df_backlog_start, df_wip_start], axis=0).drop_duplicates().copy()
            df_inventory_end = pd.concat([df_backlog_end, df_wip_end], axis=0).drop_duplicates().copy()

        throughput_avg = weekly_df['Throughput'].mean() if not weekly_df.empty else np.nan
        arrivals_avg = weekly_df['EntradasBacklog'].mean() if not weekly_df.empty else np.nan
        commitment_avg = weekly_df['Compromissos'].mean() if not weekly_df.empty else np.nan
        backlog_avg = weekly_df['Backlog'].mean() if not weekly_df.empty else np.nan
        wip_avg = weekly_df['WIP'].mean() if not weekly_df.empty else np.nan
        total_system_avg = weekly_df['EstoqueTotal'].mean() if not weekly_df.empty else np.nan
        wip_age = (
            end_ts - pd.to_datetime(df_wip_end.get('LeadStart_Selected'), errors='coerce')
        ).dt.days.mean() if not df_wip_end.empty else np.nan
        throughput_total = float(len(df_done_period_eligible))
        commitment_total = float(len(df_signal_base[
            (commitment_date >= start_ts) &
            (commitment_date <= end_ts)
        ]))
        inflow_total = commitment_total
        demand_total = float(len(df_demand_period))
        capacity_total = throughput_total
        backlog_start_count = float(len(df_backlog_start))
        backlog_end_count = float(len(df_backlog_end))
        wip_start_count = float(len(df_wip_start))
        wip_end_count = float(len(df_wip_end))
        inventory_start_count = float(len(df_inventory_start)) if isinstance(df_inventory_start, pd.DataFrame) else np.nan
        inventory_end_count = float(len(df_inventory_end)) if isinstance(df_inventory_end, pd.DataFrame) else np.nan
        inventory_growth = inventory_end_count - inventory_start_count if pd.notna(inventory_start_count) and pd.notna(inventory_end_count) else np.nan
        backlog_growth = backlog_end_count - backlog_start_count if pd.notna(backlog_start_count) and pd.notna(backlog_end_count) else np.nan
        wip_growth = wip_end_count - wip_start_count
        weeks_count = max(1, len(weeks) - 1)
        throughput_weekly_avg = throughput_total / weeks_count if weeks_count > 0 else np.nan
        commitment_weekly_avg = commitment_total / weeks_count if weeks_count > 0 else np.nan
        inventory_weeks = (inventory_end_count / throughput_weekly_avg) if throughput_weekly_avg > 0 and pd.notna(inventory_end_count) else np.nan
        capacity_label = "itens concluídos no período (throughput)"

        lead_time_p85 = np.nan
        lead_time_p50 = np.nan
        lead_time_p98 = np.nan
        lead_time_avg_days = np.nan
        full_system_lead_time_avg_days = np.nan
        time_to_commit_avg_days = np.nan
        lt_done_period = time_metric_series(df_done_period, 'LeadTime_Selected_Dias', non_negative=True)
        lt_done_period_eligible = time_metric_series(df_done_period_eligible, 'LeadTime_Selected_Dias', non_negative=True)
        full_system_lt_done_period_eligible = time_metric_series(df_done_period_eligible, 'LeadTime_Dias', non_negative=True)
        if not lt_done_period_eligible.empty:
            lead_time_avg_days = float(lt_done_period_eligible.mean())
        if not full_system_lt_done_period_eligible.empty:
            full_system_lead_time_avg_days = float(full_system_lt_done_period_eligible.mean())
        if not lt_done_period.empty:
            lead_time_p85 = exact_empirical_percentile(lt_done_period, 0.85)
            lead_time_p50 = exact_empirical_percentile(lt_done_period, 0.50)
            lead_time_p98 = exact_empirical_percentile(lt_done_period, 0.98)

        lead_time_avg_weeks = (lead_time_avg_days / 7.0) if pd.notna(lead_time_avg_days) else np.nan
        full_system_lead_time_avg_weeks = (full_system_lead_time_avg_days / 7.0) if pd.notna(full_system_lead_time_avg_days) else np.nan
        backlog_consumption_weeks = (
            backlog_avg / commitment_avg
            if pd.notna(backlog_avg) and pd.notna(commitment_avg) and commitment_avg > 0
            else np.nan
        )
        wip_consumption_weeks = (
            wip_avg / throughput_avg
            if pd.notna(wip_avg) and pd.notna(throughput_avg) and throughput_avg > 0
            else np.nan
        )
        total_system_consumption_weeks = (
            total_system_avg / throughput_avg
            if pd.notna(total_system_avg) and pd.notna(throughput_avg) and throughput_avg > 0
            else np.nan
        )
        throughput_needed_for_wip = (
            wip_avg / lead_time_avg_weeks
            if pd.notna(wip_avg) and pd.notna(lead_time_avg_weeks) and lead_time_avg_weeks > 0
            else np.nan
        )
        throughput_needed_for_total_system = (
            total_system_avg / full_system_lead_time_avg_weeks
            if pd.notna(total_system_avg) and pd.notna(full_system_lead_time_avg_weeks) and full_system_lead_time_avg_weeks > 0
            else np.nan
        )

        pressure_ratio, queue_efficiency = calculate_flow_efficiency(arrivals_avg, throughput_avg)
        wip_tp_ratio = wip_avg / throughput_avg if pd.notna(wip_avg) and pd.notna(throughput_avg) and throughput_avg > 0 else np.nan
        predictability = lead_time_p85 / lead_time_p50 if pd.notna(lead_time_p85) and pd.notna(lead_time_p50) and lead_time_p50 > 0 else np.nan
        risk_forecasting_ratio = lead_time_p98 / lead_time_p50 if pd.notna(lead_time_p98) and pd.notna(lead_time_p50) and lead_time_p50 > 0 else np.nan
        demand_vs_capacity_pct = ((demand_total - capacity_total) / capacity_total * 100.0) if capacity_total > 0 else np.nan
        inflow_vs_outflow_pct = ((inflow_total - throughput_total) / throughput_total * 100.0) if throughput_total > 0 else np.nan
        commitment_rate = (throughput_total / demand_total * 100.0) if demand_total > 0 else np.nan
        # Razões calculadas sobre df_snapshot_base (inclui itens não concluídos),
        # evitando o viés de df_signal_base que filtra apenas itens com DataDone no período.
        snapshot_backlog_date = datetime_col_or_nat(df_snapshot_base, 'DataBacklog')
        snapshot_commit_date_ratio = datetime_col_or_nat(df_snapshot_base, 'Commitment_Selected')
        true_arrivals_period = float(len(df_snapshot_base[
            (snapshot_backlog_date >= start_ts) &
            (snapshot_backlog_date <= end_ts)
        ]))
        true_inflow_period = float(len(df_snapshot_base[
            (snapshot_commit_date_ratio >= start_ts) &
            (snapshot_commit_date_ratio <= end_ts)
        ]))
        true_arrivals_per_week = true_arrivals_period / weeks_count if weeks_count > 0 else np.nan
        true_inflow_per_week = true_inflow_period / weeks_count if weeks_count > 0 else np.nan
        backlog_throughput_ratio = (
            true_arrivals_per_week / throughput_avg
            if pd.notna(true_arrivals_per_week) and pd.notna(throughput_avg) and throughput_avg > 0
            else np.nan
        )
        inflow_throughput_ratio = (
            true_inflow_per_week / throughput_avg
            if pd.notna(true_inflow_per_week) and pd.notna(throughput_avg) and throughput_avg > 0
            else np.nan
        )
        true_demand_vs_capacity_pct = (
            (true_arrivals_period - capacity_total) / capacity_total * 100.0
            if capacity_total > 0 else np.nan
        )
        true_inflow_vs_outflow_pct = (
            (true_inflow_period - throughput_total) / throughput_total * 100.0
            if throughput_total > 0 else np.nan
        )
        commit_times = pd.Series(dtype='float64')
        commit_date = datetime_col_or_nat(df_signal_base, 'Commitment_Selected')
        df_commit_period = df_signal_base[
            (commit_date >= start_ts) &
            (commit_date <= end_ts)
        ].copy()
        if not df_commit_period.empty and 'TimeToCommit_Selected_Dias' in df_commit_period.columns:
            commit_times = pd.to_numeric(df_commit_period['TimeToCommit_Selected_Dias'], errors='coerce').dropna()
            commit_times = commit_times[commit_times >= 0]
            if not commit_times.empty:
                time_to_commit_avg_days = float(commit_times.mean())
        time_to_commit_p85 = exact_empirical_percentile(commit_times, 0.85) if not commit_times.empty else np.nan
        time_to_commit_avg_weeks = (time_to_commit_avg_days / 7.0) if pd.notna(time_to_commit_avg_days) else np.nan
        commitment_needed_for_backlog = (
            backlog_avg / time_to_commit_avg_weeks
            if pd.notna(backlog_avg) and pd.notna(time_to_commit_avg_weeks) and time_to_commit_avg_weeks > 0
            else np.nan
        )

        tipo_demanda = df_done_period_eligible['TipoDemanda'] if 'TipoDemanda' in df_done_period_eligible.columns else pd.Series(dtype='object')
        tp_valor = int((tipo_demanda == TYPE_DEV).sum()) if not tipo_demanda.empty else 0
        tp_falha = int((tipo_demanda == TYPE_ISSUES).sum()) if not tipo_demanda.empty else 0
        tp_base_valor_falha = tp_valor + tp_falha
        tp_valor_pct = (tp_valor / tp_base_valor_falha * 100.0) if tp_base_valor_falha > 0 else np.nan
        tp_falha_pct = (tp_falha / tp_base_valor_falha * 100.0) if tp_base_valor_falha > 0 else np.nan

        def classify_direction(value, good_limit, warn_limit, lower_is_better=True):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            if lower_is_better:
                if value <= good_limit:
                    return ('Saudável', '#2e7d32')
                if value <= warn_limit:
                    return ('Atenção', '#f9a825')
                return ('Crítico', '#c62828')
            if value >= good_limit:
                return ('Saudável', '#2e7d32')
            if value >= warn_limit:
                return ('Atenção', '#f9a825')
            return ('Crítico', '#c62828')

        def fmt_value(value, pattern):
            if pd.isna(value):
                return '—'
            return pattern.format(value)

        def classify_forecasting_risk(value):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            if value < 6:
                return ('RISCO MODERADO', '#2e7d32')
            return ('RISCO ALTO', '#ef7d32')

        def classify_pressure(value):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            if value <= 0.80:
                return ('OK', '#2e7d32')
            if value <= 0.90:
                return ('ATENÇÃO', '#f9a825')
            if value <= 0.95:
                return ('CRÍTICO', '#c62828')
            return ('EXTREMAMENTE CRÍTICO', '#7f0000')

        def classify_efficiency(value):
            if pd.isna(value):
                return ('Sem base', '#9e9e9e')
            # Eficiência (1 - rho) é o inverso da pressão rho.
            if value >= 0.20:
                return ('OK', '#2e7d32')
            if value >= 0.10:
                return ('ATENÇÃO', '#f9a825')
            if value >= 0.05:
                return ('CRÍTICO', '#c62828')
            return ('EXTREMAMENTE CRÍTICO', '#7f0000')

        def classify_throughput_mix(falha_pct):
            if pd.isna(falha_pct):
                return ('Sem base', '#9e9e9e')
            if falha_pct <= 20:
                return ('OK', '#2e7d32')
            if falha_pct <= 35:
                return ('ATENÇÃO', '#f9a825')
            return ('CRÍTICO', '#c62828')

        def cv_percent(series):
            s = pd.Series(series).dropna()
            if len(s) < 2:
                return np.nan
            mean = s.mean()
            if pd.isna(mean) or abs(mean) < 1e-9:
                return np.nan
            return (s.std() / abs(mean)) * 100.0

        def classify_cv(cv_value):
            if pd.isna(cv_value):
                return ('Sem base', '#9e9e9e')
            if cv_value <= 30:
                return ('OK (VERDE)', '#2e7d32')
            if cv_value <= 50:
                return ('RAZOÁVEL', '#f9a825')
            if cv_value <= 65:
                return ('RUIM', '#ef6c00')
            if cv_value <= 80:
                return ('CRÍTICO', '#c62828')
            return ('EXTREMAMENTE CRÍTICO', '#7f0000')

        backlog_cv_status = classify_cv(cv_percent(weekly_hist_df.get('Backlog', pd.Series(dtype=float))))
        wip_cv_status = classify_cv(cv_percent(weekly_hist_df.get('WIP', pd.Series(dtype=float))))
        total_system_cv_status = classify_cv(cv_percent(weekly_hist_df.get('EstoqueTotal', pd.Series(dtype=float))))
        lt_cv_status = classify_cv(cv_percent(weekly_hist_df.get('LeadTime_P85', pd.Series(dtype=float))))
        throughput_cv_status = classify_cv(cv_percent(weekly_hist_df.get('Throughput', pd.Series(dtype=float))))
        arrivals_cv_status = classify_cv(cv_percent(weekly_hist_df.get('EntradasBacklog', pd.Series(dtype=float))))
        commitment_cv_status = classify_cv(cv_percent(weekly_hist_df.get('Compromissos', pd.Series(dtype=float))))
        predictability_status = classify_direction(predictability, 1.8, 2.2, lower_is_better=True)

        tp_relacao_display = (
            f"{tp_valor_pct:.1f}% x {tp_falha_pct:.1f}%" if pd.notna(tp_valor_pct) and pd.notna(tp_falha_pct) else '—'
        )
        tp_relacao_status = classify_throughput_mix(tp_falha_pct)

        # Catálogo único de métricas para todo o painel (id único por indicador).
        metric_catalog = {
            'demand_total': {'value': demand_total},
            'capacity_total': {'value': capacity_total},
            'demand_vs_capacity_pct': {'value': demand_vs_capacity_pct},
            'inflow_total': {'value': inflow_total},
            'outflow_total': {'value': throughput_total},
            'inflow_vs_outflow_pct': {'value': inflow_vs_outflow_pct},
            'inventory_growth': {'value': inventory_growth},
            'wip_growth': {'value': wip_growth},
            'backlog_uncommitted_current': {
                'title': 'Backlog não comprometido',
                'value': backlog_end_count,
                'format': '{:.0f}',
                'unit': 'itens de fluxo',
                'note': (
                    f"(fim do período; média semanal no período: {backlog_avg:.1f} itens)"
                    if pd.notna(backlog_avg)
                    else "(fim do período)"
                ),
            },
            'wip_in_progress_current': {
                'title': 'WIP',
                'value': wip_end_count,
                'format': '{:.0f}',
                'unit': 'itens de fluxo',
                'note': (
                    f"(fim do período; média semanal no período: {wip_avg:.1f} itens)"
                    if pd.notna(wip_avg)
                    else "(fim do período)"
                ),
            },
            'total_system_current': {
                'title': 'Estoque total do sistema',
                'value': inventory_end_count,
                'format': '{:.0f}',
                'unit': 'itens de fluxo',
                'note': (
                    f"(backlog {backlog_end_count:.0f} + WIP {wip_end_count:.0f}; média semanal no período: {total_system_avg:.1f} itens)"
                    if pd.notna(total_system_avg)
                    else f"(backlog {backlog_end_count:.0f} + WIP {wip_end_count:.0f})"
                ),
            },
            'backlog_little_weeks': {
                'title': 'Tempo médio até compromisso',
                'value': backlog_consumption_weeks,
                'format': '{:.1f}',
                'unit': 'semanas',
                'note': (
                    f"Lei de Little: backlog médio {backlog_avg:.1f} / taxa média de compromisso {commitment_avg:.1f}"
                    if pd.notna(backlog_avg) and pd.notna(commitment_avg)
                    else 'Lei de Little: backlog médio / taxa média de compromisso'
                ),
            },
            'wip_little_weeks': {
                'title': 'Tempo médio para concluir WIP',
                'value': wip_consumption_weeks,
                'format': '{:.1f}',
                'unit': 'semanas',
                'note': (
                    f"Lei de Little: WIP médio {wip_avg:.1f} / vazão média {throughput_avg:.1f}"
                    if pd.notna(wip_avg) and pd.notna(throughput_avg)
                    else 'Lei de Little: WIP médio / vazão média'
                ),
            },
            'total_system_little_weeks': {
                'title': 'Tempo médio total no sistema',
                'value': total_system_consumption_weeks,
                'format': '{:.1f}',
                'unit': 'semanas',
                'note': (
                    f"Lei de Little: estoque médio {total_system_avg:.1f} / vazão média {throughput_avg:.1f}"
                    if pd.notna(total_system_avg) and pd.notna(throughput_avg)
                    else 'Lei de Little: estoque médio / vazão média'
                ),
            },
            'backlog_required_rate': {
                'title': 'Taxa necessária para comprometer backlog',
                'value': commitment_needed_for_backlog,
                'format': '{:.1f}',
                'unit': 'itens/semana',
                'note': (
                    f"Lei de Little: {backlog_avg:.1f} / {time_to_commit_avg_weeks:.1f} = {commitment_needed_for_backlog:.1f} itens/sem"
                    if pd.notna(backlog_avg) and pd.notna(time_to_commit_avg_weeks) and pd.notna(commitment_needed_for_backlog)
                    else 'Lei de Little: backlog médio / tempo médio até compromisso'
                ),
            },
            'wip_required_rate': {
                'title': 'Vazão necessária para concluir WIP',
                'value': throughput_needed_for_wip,
                'format': '{:.1f}',
                'unit': 'itens/semana',
                'note': (
                    f"Lei de Little: {wip_avg:.1f} / {lead_time_avg_weeks:.1f} = {throughput_needed_for_wip:.1f} itens/sem"
                    if pd.notna(wip_avg) and pd.notna(lead_time_avg_weeks) and pd.notna(throughput_needed_for_wip)
                    else 'Lei de Little: WIP médio semanal / Lead Time médio (semanas)'
                ),
            },
            'total_system_required_rate': {
                'title': 'Vazão necessária para o estoque total',
                'value': throughput_needed_for_total_system,
                'format': '{:.1f}',
                'unit': 'itens/semana',
                'note': (
                    f"Lei de Little: {total_system_avg:.1f} / {full_system_lead_time_avg_weeks:.1f} = {throughput_needed_for_total_system:.1f} itens/sem"
                    if pd.notna(total_system_avg) and pd.notna(full_system_lead_time_avg_weeks) and pd.notna(throughput_needed_for_total_system)
                    else 'Lei de Little: estoque médio / tempo médio total no sistema'
                ),
            },
            'throughput_total': {
                'title': 'Throughput total (Done s/ cancel.)',
                'value': throughput_total,
                'format': '{:.0f}',
                'unit': 'itens de fluxo',
                'note': (
                    f"(período selecionado, elegíveis para tempo; média semanal: {throughput_avg:.1f} itens/sem)"
                    if pd.notna(throughput_avg)
                    else '(período selecionado, elegíveis para tempo)'
                ),
            },
            'time_to_commit_p85': {
                'title': 'Tempo para Commit (P85)',
                'value': time_to_commit_p85,
                'format': '{:.0f}',
                'unit': 'dias',
                'status': classify_direction(time_to_commit_p85, 7.0, 14.0, lower_is_better=True),
            },
            'wip_age_avg': {
                'title': 'WIP Age (médio)',
                'value': wip_age,
                'format': '{:.0f}',
                'unit': 'dias',
                'status': classify_direction(wip_age, 14.0, 28.0, lower_is_better=True),
            },
            'commitment_rate': {
                'title': 'Taxa de Comprometimento',
                'value': commitment_rate,
                'format': '{:.0f}%',
                'unit': 'throughput / demanda',
                'status': classify_direction(commitment_rate, 100.0, 85.0, lower_is_better=False),
            },
            'backlog_avg_week': {'title': 'Backlog médio (semana)', 'value': backlog_avg, 'format': '{:.1f} itens', 'status': backlog_cv_status},
            'commitment_avg_week': {'title': 'Compromissos médios/semana', 'value': commitment_avg, 'format': '{:.1f} itens/sem', 'status': commitment_cv_status},
            'wip_avg_week': {'title': 'WIP médio (semana)', 'value': wip_avg, 'format': '{:.1f} itens', 'status': wip_cv_status},
            'total_system_avg_week': {'title': 'Estoque médio do sistema', 'value': total_system_avg, 'format': '{:.1f} itens', 'status': total_system_cv_status},
            'lead_time_p85': {'title': 'Lead Time P85', 'value': lead_time_p85, 'format': '{:.1f} dias', 'status': lt_cv_status},
            'throughput_avg_week': {'title': 'Vazão média semanal', 'value': throughput_avg, 'format': '{:.1f} itens/sem', 'status': throughput_cv_status},
            'arrivals_avg_week': {'title': 'Entradas em backlog/semana', 'value': arrivals_avg, 'format': '{:.1f} itens/sem', 'status': arrivals_cv_status},
            'flow_efficiency': {'title': 'Eficiência (1 - ρ)', 'value': queue_efficiency, 'format': '{:.2f}', 'status': classify_efficiency(queue_efficiency)},
            'flow_pressure': {'title': 'Pressão de fluxo (chegada/vazão)', 'value': pressure_ratio, 'format': '{:.2f}', 'status': classify_pressure(pressure_ratio)},
            'predictability': {'title': 'Previsibilidade (P85/P50)', 'value': predictability, 'format': '{:.2f}', 'status': predictability_status},
            'backlog_current': {'title': 'Backlog atual', 'value': backlog_end_count, 'format': '{:.0f} itens', 'status': backlog_cv_status},
            'wip_current': {'title': 'WIP atual (fim do período)', 'value': wip_end_count, 'format': '{:.0f} itens', 'status': wip_cv_status},
            'total_system_current_exec': {'title': 'Estoque total atual', 'value': inventory_end_count, 'format': '{:.0f} itens', 'status': total_system_cv_status},
            'forecast_risk': {'title': 'Risco Forecasting (P98/Mediana)', 'value': risk_forecasting_ratio, 'format': '{:.2f}', 'status': classify_forecasting_risk(risk_forecasting_ratio)},
            'throughput_mix': {'title': 'Throughput valor x falha (%)', 'value': tp_relacao_display, 'format': '{}', 'status': tp_relacao_status},
        }

        reference_metric_ids = [
            'throughput_total',
            'backlog_little_weeks',
            'wip_little_weeks',
            'total_system_little_weeks',
            'backlog_required_rate',
            'wip_required_rate',
            'total_system_required_rate',
        ]
        executive_metric_ids = [
            'backlog_avg_week',
            'commitment_avg_week',
            'wip_avg_week',
            'total_system_avg_week',
            'lead_time_p85',
            'throughput_avg_week',
            'arrivals_avg_week',
            'flow_efficiency',
            'flow_pressure',
            'predictability',
            'backlog_current',
            'wip_current',
            'total_system_current_exec',
            'forecast_risk',
            'throughput_mix',
            'time_to_commit_p85',
            'wip_age_avg',
            'commitment_rate',
        ]
        quick_metric_ids = {
            'throughput_avg_week',
            'lead_time_p85',
            'predictability',
            'wip_current',
            'total_system_current_exec',
        }
        reference_metric_set = set(reference_metric_ids)
        executive_metric_ids = [
            mid for mid in executive_metric_ids
            if mid not in reference_metric_set and mid not in quick_metric_ids
        ]

        cards = []
        for metric_id in executive_metric_ids:
            metric = metric_catalog[metric_id]
            title = metric['title']
            raw_value = metric['value']
            value_pattern = metric['format']
            unit = metric.get('unit')
            status_label, status_color = metric['status']
            card_children = [
                html.Div(status_label, style={'fontSize': '12px', 'fontWeight': 'bold', 'color': status_color, 'textTransform': 'uppercase'}),
                html.H4(title, style={'marginTop': '8px', 'marginBottom': '8px', 'fontSize': '17px'}),
                html.Div(fmt_value(raw_value, value_pattern), style={'fontSize': '30px', 'fontWeight': 'bold', 'lineHeight': '1.1'}),
            ]
            if unit:
                card_children.append(
                    html.Div(unit, style={'fontSize': '13px', 'color': '#5f6e7b', 'marginTop': '6px'})
                )
            cards.append(
                html.Div(card_children, style={
                    'backgroundColor': 'white',
                    'border': '1px solid #e5e5e5',
                    'borderTop': f'6px solid {status_color}',
                    'borderRadius': '10px',
                    'padding': '14px',
                    'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
                    'minHeight': '150px',
                })
            )

        card_rows = []
        for idx in range(0, len(cards), 3):
            card_rows.append(
                html.Div(
                    [html.Div(cards[i], className='four columns') for i in range(idx, min(idx + 3, len(cards)))],
                    className='row',
                    style={'marginTop': '14px'} if idx > 0 else {},
                )
            )

        period_days = max(1, (pd.Timestamp(end_ts).normalize() - pd.Timestamp(start_ts).normalize()).days + 1)
        previous_end_ts = pd.Timestamp(start_ts).normalize() - pd.Timedelta(days=1)
        previous_start_ts = previous_end_ts - pd.Timedelta(days=period_days - 1)

        previous_signal_base = filter_df(
            fato,
            previous_start_ts,
            previous_end_ts,
            projeto,
            tipo,
            classe_servico,
            responsavel,
            criadores=criadores,
            use_creation_date=use_creation_date,
            tipo_original=tipo_original_jira,
        )
        previous_signal_base, _ = apply_selected_lead_time_metric(previous_signal_base, projeto, leadtime_stages)
        previous_signal_base, _ = apply_selected_commitment_metric(previous_signal_base, projeto, leadtime_stages)

        def compute_quick_flow_metrics(df_period_base, df_snapshot_scope, start_ref, end_ref, stage_map=None, stage_filter=None):
            start_ref = pd.Timestamp(start_ref)
            end_ref = pd.Timestamp(end_ref)
            weekly_local = build_weekly_metrics(
                df_period_base,
                start_ref,
                end_ref,
                stage_map=stage_map,
                stage_filter=stage_filter,
            ) if df_period_base is not None and not df_period_base.empty else pd.DataFrame()

            throughput_avg_local = float(weekly_local['Throughput'].mean()) if not weekly_local.empty and weekly_local['Throughput'].notna().any() else np.nan

            done_local = df_period_base[
                (df_period_base['DataDone'] >= start_ref) &
                (df_period_base['DataDone'] <= end_ref)
            ].copy() if df_period_base is not None and not df_period_base.empty else pd.DataFrame()
            done_local_eligible = done_local[done_time_eligible_mask(done_local)].copy() if not done_local.empty else pd.DataFrame()

            throughput_total_local = float(len(done_local_eligible))
            lead_series_local = time_metric_series(done_local, 'LeadTime_Selected_Dias', non_negative=True)
            lead_p85_local = exact_empirical_percentile(lead_series_local, 0.85) if not lead_series_local.empty else np.nan
            lead_p50_local = exact_empirical_percentile(lead_series_local, 0.50) if not lead_series_local.empty else np.nan
            predictability_local = (
                lead_p85_local / lead_p50_local
                if pd.notna(lead_p85_local) and pd.notna(lead_p50_local) and lead_p50_local > 0
                else np.nan
            )

            urgency_local = (
                done_local_eligible.apply(classify_urgency_label, axis=1)
                if not done_local_eligible.empty
                else pd.Series(dtype='object')
            )
            expedite_pct_local = (
                float((urgency_local == 'Highest').sum() / throughput_total_local * 100.0)
                if throughput_total_local > 0
                else np.nan
            )

            tipo_local = done_local_eligible['TipoDemanda'] if 'TipoDemanda' in done_local_eligible.columns else pd.Series(dtype='object')
            failure_pct_local = (
                float((tipo_local == TYPE_ISSUES).sum() / throughput_total_local * 100.0)
                if throughput_total_local > 0
                else np.nan
            )

            creation_local = resolve_creation_date_series(done_local_eligible)
            unplanned_pct_local = (
                float(((creation_local > start_ref) & (creation_local <= end_ref)).sum() / throughput_total_local * 100.0)
                if throughput_total_local > 0
                else np.nan
            )

            snapshot_backlog_local = datetime_col_or_nat(df_snapshot_scope, 'DataBacklog')
            snapshot_commitment_local = datetime_col_or_nat(df_snapshot_scope, 'Commitment_Selected')
            snapshot_done_local = datetime_col_or_nat(df_snapshot_scope, 'DataDone')

            backlog_start_local = df_snapshot_scope[
                (snapshot_backlog_local < start_ref) &
                ((snapshot_commitment_local >= start_ref) | snapshot_commitment_local.isna())
            ].copy() if df_snapshot_scope is not None and not df_snapshot_scope.empty else pd.DataFrame()

            backlog_end_local = df_snapshot_scope[
                (snapshot_backlog_local <= end_ref) &
                ((snapshot_commitment_local > end_ref) | snapshot_commitment_local.isna())
            ].copy() if df_snapshot_scope is not None and not df_snapshot_scope.empty else pd.DataFrame()

            wip_end_local = build_live_wip_snapshot(
                df_snapshot_scope,
                end_ref,
                projeto=projeto,
                selected_stages=stage_filter,
                stage_map=stage_map if stage_filter else None,
            )

            if df_snapshot_scope is not None and not df_snapshot_scope.empty and 'ItemID' in df_snapshot_scope.columns:
                inventory_end_local = pd.concat([backlog_end_local, wip_end_local], axis=0).drop_duplicates(subset=['ItemID']).copy()
            else:
                inventory_end_local = pd.concat([backlog_end_local, wip_end_local], axis=0).drop_duplicates().copy()

            backlog_start_commitment_local = datetime_col_or_nat(backlog_start_local, 'Commitment_Selected')
            backlog_start_done_local = snapshot_done_local.reindex(backlog_start_local.index) if not backlog_start_local.empty else pd.Series(dtype='datetime64[ns]')
            backlog_planned_unexecuted_pct_local = (
                float(
                    (
                        (
                            backlog_start_commitment_local.isna() |
                            (backlog_start_commitment_local > end_ref) |
                            backlog_start_done_local.isna() |
                            (backlog_start_done_local > end_ref)
                        ).sum()
                    ) / len(backlog_start_local) * 100.0
                )
                if not backlog_start_local.empty
                else np.nan
            )

            return {
                'throughput_avg': throughput_avg_local,
                'lead_time_p85': lead_p85_local,
                'predictability': predictability_local,
                'failure_pct': failure_pct_local,
                'expedite_pct': expedite_pct_local,
                'unplanned_pct': unplanned_pct_local,
                'wip_current': float(len(wip_end_local)),
                'inventory_current': float(len(inventory_end_local)),
                'backlog_planned_unexecuted_pct': backlog_planned_unexecuted_pct_local,
            }

        current_quick_metrics = compute_quick_flow_metrics(
            df_signal_base,
            df_snapshot_base,
            start_ts,
            end_ts,
            stage_map=panel_stage_map,
            stage_filter=etapa_fluxo,
        )
        previous_quick_metrics = compute_quick_flow_metrics(
            previous_signal_base,
            df_snapshot_base,
            previous_start_ts,
            previous_end_ts,
            stage_map=panel_stage_map,
            stage_filter=etapa_fluxo,
        )

        def metric_delta(current_value, previous_value):
            if pd.isna(current_value) or pd.isna(previous_value):
                return np.nan
            return float(current_value - previous_value)

        def build_trend_summary(current_value, previous_value, better_when='higher', tolerance=0.5, delta_pattern='{:+.1f}', delta_suffix=''):
            if pd.isna(current_value) or pd.isna(previous_value):
                return ('Sem base anterior', '#7b8694', 'Delta indisponível')
            delta = metric_delta(current_value, previous_value)
            if pd.isna(delta):
                return ('Sem base anterior', '#7b8694', 'Delta indisponível')
            if abs(delta) <= tolerance:
                return ('Estável', '#7b8694', f"Delta {delta_pattern.format(delta)}{delta_suffix} vs período anterior")

            moved_up = delta > 0
            direction_label = 'Subiu' if moved_up else 'Caiu'
            improved = moved_up if better_when == 'higher' else not moved_up
            direction_color = '#2e7d32' if improved else '#c62828'
            return (
                direction_label,
                direction_color,
                f"Delta {delta_pattern.format(delta)}{delta_suffix} vs período anterior"
            )

        def build_flow_dimension_card(title, value, subtitle, explanation, status_tuple, trend_tuple, trend_emphasis=False, featured=False):
            status_label, status_color = status_tuple
            trend_label, trend_color, trend_detail = trend_tuple
            return html.Div([
                html.Div([
                    html.Div(status_label, style={
                        'fontSize': '11px',
                        'fontWeight': '700',
                        'letterSpacing': '0.05em',
                        'textTransform': 'uppercase',
                        'color': status_color,
                    }),
                    html.Div(trend_label, style={
                        'display': 'inline-block',
                        'fontSize': '11px',
                        'fontWeight': '700',
                        'color': trend_color,
                        'backgroundColor': '#f4f8fc' if trend_emphasis else '#f8fafc',
                        'border': f'1px solid {trend_color}',
                        'borderRadius': '999px',
                        'padding': '4px 9px',
                    }),
                ], style={
                    'display': 'flex',
                    'justifyContent': 'space-between',
                    'alignItems': 'flex-start',
                    'gap': '10px',
                    'marginBottom': '14px',
                }),
                html.Div(title, style={
                    'fontSize': '14px',
                    'fontWeight': '700',
                    'color': '#22313f',
                    'marginBottom': '6px',
                }),
                html.Div(value, style={
                    'fontSize': '32px' if featured else '28px',
                    'fontWeight': '700',
                    'lineHeight': '1.0',
                    'color': '#0f1720',
                    'marginBottom': '8px',
                }),
                html.Div(subtitle, style={
                    'fontSize': '12px',
                    'fontWeight': '600',
                    'color': '#5f6e7b',
                    'marginBottom': '8px',
                }),
                html.Div(explanation, style={
                    'fontSize': '12px',
                    'color': '#5f6e7b',
                    'lineHeight': '1.45',
                    'marginBottom': '8px',
                }),
                html.Div(trend_detail, style={
                    'fontSize': '11px',
                    'fontWeight': '600',
                    'color': '#4b5563',
                }),
            ], style={
                'background': 'linear-gradient(180deg, #ffffff 0%, #f9fbfe 100%)' if featured else 'white',
                'border': f'1px solid {status_color}33' if featured else '1px solid #d9e2ec',
                'borderTop': f'5px solid {status_color}',
                'borderRadius': '16px',
                'padding': '16px',
                'boxShadow': '0 10px 24px rgba(15, 23, 32, 0.08)' if featured else '0 2px 8px rgba(15, 23, 32, 0.06)',
                'minHeight': '224px' if featured else '210px',
                'height': '100%',
            })

        def build_context_chip(label, note):
            return html.Div([
                html.Div(label, style={
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'letterSpacing': '0.04em',
                    'textTransform': 'uppercase',
                    'color': '#6b7a88',
                    'marginBottom': '4px',
                }),
                html.Div(note, style={
                    'fontSize': '12px',
                    'fontWeight': '600',
                    'color': '#5f6e7b',
                    'lineHeight': '1.35',
                }),
            ], style={
                'backgroundColor': 'rgba(255,255,255,0.88)',
                'border': '1px solid #d6e0eb',
                'borderRadius': '14px',
                'padding': '12px 14px',
                'minHeight': '82px',
            })

        def build_reading_panel(kicker, title, body_text, bullets, accent_color, background_color):
            return html.Div([
                html.Div(kicker, style={
                    'display': 'inline-block',
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'letterSpacing': '0.05em',
                    'textTransform': 'uppercase',
                    'color': accent_color,
                    'backgroundColor': 'rgba(255,255,255,0.78)',
                    'border': f'1px solid {accent_color}44',
                    'borderRadius': '999px',
                    'padding': '4px 10px',
                    'marginBottom': '14px',
                }),
                html.Div(title, style={
                    'fontSize': '22px',
                    'fontWeight': '700',
                    'lineHeight': '1.15',
                    'color': '#10202f',
                    'marginBottom': '12px',
                }),
                html.Div(body_text, style={
                    'fontSize': '13px',
                    'color': '#4d5c6b',
                    'lineHeight': '1.6',
                    'marginBottom': '14px',
                }),
                html.Ul([
                    html.Li(
                        bullet,
                        style={'marginBottom': '8px'}
                    )
                    for bullet in bullets
                ], style={
                    'paddingLeft': '18px',
                    'marginBottom': '0',
                    'fontSize': '12px',
                    'color': '#4d5c6b',
                    'lineHeight': '1.55',
                }),
            ], style={
                'flex': '1 1 280px',
                'minWidth': '280px',
                'background': background_color,
                'border': f'1px solid {accent_color}33',
                'borderRadius': '18px',
                'padding': '18px',
                'boxShadow': 'inset 0 1px 0 rgba(255,255,255,0.65)',
            })

        throughput_quick_status = metric_catalog['throughput_avg_week']['status']
        lead_time_quick_status = metric_catalog['lead_time_p85']['status']
        wip_quick_status = metric_catalog['wip_current']['status']
        predictability_quick_status = metric_catalog['predictability']['status']
        inventory_quick_status = metric_catalog['total_system_current_exec']['status']
        failure_quick_status = classify_direction(current_quick_metrics['failure_pct'], 20.0, 35.0, lower_is_better=True)
        expedite_quick_status = classify_direction(current_quick_metrics['expedite_pct'], 10.0, 20.0, lower_is_better=True)
        unplanned_quick_status = classify_direction(current_quick_metrics['unplanned_pct'], 15.0, 30.0, lower_is_better=True)
        backlog_unexecuted_status = classify_direction(current_quick_metrics['backlog_planned_unexecuted_pct'], 30.0, 50.0, lower_is_better=True)

        period_dimension_cards = [
            build_flow_dimension_card(
                'Throughput',
                fmt_value(current_quick_metrics['throughput_avg'], '{:.1f}'),
                'média semanal de itens concluídos',
                'Capacidade real de saída no recorte filtrado.',
                throughput_quick_status,
                build_trend_summary(
                    current_quick_metrics['throughput_avg'],
                    previous_quick_metrics['throughput_avg'],
                    better_when='higher',
                    tolerance=0.3,
                    delta_pattern='{:+.1f}',
                    delta_suffix=' itens/sem',
                ),
                trend_emphasis=True,
                featured=True,
            ),
            build_flow_dimension_card(
                'Lead Time P85',
                fmt_value(current_quick_metrics['lead_time_p85'], '{:.1f}'),
                'dias para 85% dos itens concluídos',
                'Mostra o tempo de atravessamento em cenário conservador.',
                lead_time_quick_status,
                build_trend_summary(
                    current_quick_metrics['lead_time_p85'],
                    previous_quick_metrics['lead_time_p85'],
                    better_when='lower',
                    tolerance=0.5,
                    delta_pattern='{:+.1f}',
                    delta_suffix=' dias',
                ),
                trend_emphasis=True,
                featured=True,
            ),
            build_flow_dimension_card(
                'Failure Demand',
                fmt_value(current_quick_metrics['failure_pct'], '{:.1f}%'),
                '% do throughput concluído que foi falha',
                'Usa itens de falha concluídos no período como proxy de retrabalho/recuperação.',
                failure_quick_status,
                build_trend_summary(
                    current_quick_metrics['failure_pct'],
                    previous_quick_metrics['failure_pct'],
                    better_when='lower',
                    tolerance=1.0,
                    delta_pattern='{:+.1f}',
                    delta_suffix=' p.p.',
                ),
                trend_emphasis=True,
            ),
            build_flow_dimension_card(
                'Expedite / Highest',
                fmt_value(current_quick_metrics['expedite_pct'], '{:.1f}%'),
                '% do throughput concluído em expedite',
                'Mede quanto da saída do período foi consumida por demandas de urgência máxima.',
                expedite_quick_status,
                build_trend_summary(
                    current_quick_metrics['expedite_pct'],
                    previous_quick_metrics['expedite_pct'],
                    better_when='lower',
                    tolerance=1.0,
                    delta_pattern='{:+.1f}',
                    delta_suffix=' p.p.',
                ),
            ),
            build_flow_dimension_card(
                'Trabalho Não Planejado',
                fmt_value(current_quick_metrics['unplanned_pct'], '{:.1f}%'),
                '% dos concluídos criados dentro do período',
                'Proxy de trabalho que entrou depois do início do recorte e ainda assim foi entregue.',
                unplanned_quick_status,
                build_trend_summary(
                    current_quick_metrics['unplanned_pct'],
                    previous_quick_metrics['unplanned_pct'],
                    better_when='lower',
                    tolerance=1.0,
                    delta_pattern='{:+.1f}',
                    delta_suffix=' p.p.',
                ),
            ),
            build_flow_dimension_card(
                'Previsibilidade',
                fmt_value(current_quick_metrics['predictability'], '{:.2f}'),
                'razão P85 / P50 do período',
                'Quanto mais perto de 1, menor a dispersão e mais confiável o sistema.',
                predictability_quick_status,
                build_trend_summary(
                    current_quick_metrics['predictability'],
                    previous_quick_metrics['predictability'],
                    better_when='lower',
                    tolerance=0.05,
                    delta_pattern='{:+.2f}',
                ),
            ),
        ]

        snapshot_dimension_cards = [
            build_flow_dimension_card(
                'WIP Atual',
                fmt_value(current_quick_metrics['wip_current'], '{:.0f}'),
                'itens em fluxo no fim do período',
                'Resume a carga ativa que ainda compete por atenção do time.',
                wip_quick_status,
                build_trend_summary(
                    current_quick_metrics['wip_current'],
                    previous_quick_metrics['wip_current'],
                    better_when='lower',
                    tolerance=1.0,
                    delta_pattern='{:+.0f}',
                    delta_suffix=' itens',
                ),
                trend_emphasis=True,
                featured=True,
            ),
            build_flow_dimension_card(
                'CFD / Estoque',
                fmt_value(current_quick_metrics['inventory_current'], '{:.0f}'),
                'backlog + WIP no fim do período',
                'Leitura rápida do tamanho do sistema antes de aprofundar na aba de CFD.',
                inventory_quick_status,
                build_trend_summary(
                    current_quick_metrics['inventory_current'],
                    previous_quick_metrics['inventory_current'],
                    better_when='lower',
                    tolerance=1.0,
                    delta_pattern='{:+.0f}',
                    delta_suffix=' itens',
                ),
                trend_emphasis=True,
                featured=True,
            ),
            build_flow_dimension_card(
                'Backlog Planejado sem Execução',
                fmt_value(current_quick_metrics['backlog_planned_unexecuted_pct'], '{:.1f}%'),
                '% do backlog inicial sem compromisso ou sem entrega',
                'Proxy de itens já planejados no início que terminaram o recorte ainda sem avanço suficiente.',
                backlog_unexecuted_status,
                build_trend_summary(
                    current_quick_metrics['backlog_planned_unexecuted_pct'],
                    previous_quick_metrics['backlog_planned_unexecuted_pct'],
                    better_when='lower',
                    tolerance=1.0,
                    delta_pattern='{:+.1f}',
                    delta_suffix=' p.p.',
                ),
            ),
        ]

        def build_dimension_group(title, subtitle, helper_label, overview_panel, cards, background_color, border_color):
            return html.Div([
                html.Div([
                    html.Div([
                        html.Div(title, style={'fontSize': '18px', 'fontWeight': '700', 'color': '#22313f', 'marginBottom': '4px'}),
                        html.Div(subtitle, style={'fontSize': '12px', 'color': '#5f6e7b'}),
                    ], style={'flex': '1 1 320px'}),
                    html.Div(helper_label, style={
                        'display': 'inline-block',
                        'fontSize': '11px',
                        'fontWeight': '700',
                        'letterSpacing': '0.04em',
                        'textTransform': 'uppercase',
                        'color': '#607080',
                        'backgroundColor': 'rgba(255,255,255,0.72)',
                        'border': '1px solid rgba(148, 163, 184, 0.35)',
                        'borderRadius': '999px',
                        'padding': '6px 10px',
                        'alignSelf': 'flex-start',
                    }),
                ], style={
                    'display': 'flex',
                    'justifyContent': 'space-between',
                    'alignItems': 'flex-start',
                    'gap': '12px',
                    'flexWrap': 'wrap',
                    'marginBottom': '16px',
                }),
                html.Div([
                    overview_panel,
                    html.Div(
                        cards,
                        style={
                            'flex': '2.4 1 680px',
                            'display': 'grid',
                            'gridTemplateColumns': 'repeat(auto-fit, minmax(220px, 1fr))',
                            'gap': '12px',
                            'alignContent': 'start',
                        }
                    ),
                ], style={
                    'display': 'flex',
                    'flexWrap': 'wrap',
                    'gap': '14px',
                    'alignItems': 'stretch',
                }),
            ], style={
                'backgroundColor': background_color,
                'border': f'1px solid {border_color}',
                'borderRadius': '20px',
                'padding': '18px',
                'boxShadow': '0 6px 18px rgba(15, 23, 32, 0.04)',
            })

        period_reading_panel = build_reading_panel(
            'Como ler',
            'Médias do Período',
            'Comece pelos cards âncora e use os demais sinais para entender se a cadência do recorte foi estável ou contaminada por urgência, retrabalho ou entrada fora do plano.',
            [
                'Throughput e Lead Time P85 resumem capacidade real de saída e prazo em cenário conservador.',
                'Failure Demand, Expedite e Trabalho Não Planejado mostram quanto do período foi consumido por ruído operacional.',
                'Previsibilidade ajuda a confirmar se o prazo ficou concentrado ou espalhado demais.',
            ],
            throughput_quick_status[1],
            'linear-gradient(180deg, rgba(235, 244, 255, 0.95) 0%, rgba(248, 251, 255, 0.92) 100%)',
        )

        snapshot_reading_panel = build_reading_panel(
            'Como ler',
            'Snapshot Atual',
            'Aqui a leitura é de fotografia final do sistema: quanta carga ficou ativa, quanto estoque permaneceu aberto e quanto do backlog conhecido não ganhou avanço suficiente até o fim do recorte.',
            [
                'WIP Atual mostra a carga viva competindo por atenção agora.',
                'CFD / Estoque resume o tamanho do sistema somando backlog e trabalho em andamento.',
                'Backlog Planejado sem Execução evidencia quanto do que já era conhecido continuou parado.',
            ],
            wip_quick_status[1],
            'linear-gradient(180deg, rgba(255, 243, 224, 0.95) 0%, rgba(255, 250, 242, 0.92) 100%)',
        )

        flow_dimension_section = html.Div([
            html.Div([
                html.Div([
                    html.Div('Leitura Executiva', style={
                        'display': 'inline-block',
                        'fontSize': '11px',
                        'fontWeight': '700',
                        'letterSpacing': '0.06em',
                        'textTransform': 'uppercase',
                        'color': '#176ea4',
                        'backgroundColor': 'rgba(255,255,255,0.72)',
                        'border': '1px solid rgba(23, 110, 164, 0.18)',
                        'borderRadius': '999px',
                        'padding': '5px 10px',
                        'marginBottom': '12px',
                    }),
                    html.H4('Leitura Rápida do Fluxo', style={'marginBottom': '8px', 'fontSize': '34px', 'lineHeight': '1.05', 'color': '#10202f'}),
                    html.P(
                        'Primeiro lemos as médias do período; depois olhamos a fotografia do fim do recorte. Assim, cadência semanal, carga ativa e referências estruturais ficam separados sem repetir o mesmo KPI em várias camadas.',
                        style={'color': '#4d5c6b', 'marginBottom': '0', 'fontSize': '14px', 'lineHeight': '1.6'}
                    ),
                ], style={'flex': '1.6 1 340px'}),
                html.Div([
                    build_context_chip('1. Médias do Período', 'cadência, prazo, previsibilidade e ruído operacional'),
                    build_context_chip('2. Snapshot Atual', 'carga viva, estoque total e execução do backlog conhecido'),
                    build_context_chip('3. Referências Estruturais', 'demanda x capacidade, entrada x saída e leituras pela Lei de Little'),
                ], style={
                    'flex': '2.2 1 420px',
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fit, minmax(180px, 1fr))',
                    'gap': '10px',
                }),
            ], style={
                'display': 'flex',
                'flexWrap': 'wrap',
                'alignItems': 'stretch',
                'gap': '14px',
                'background': 'linear-gradient(135deg, #eef6ff 0%, #f8fbff 55%, #fffaf2 100%)',
                'border': '1px solid #d8e5f1',
                'borderRadius': '22px',
                'padding': '20px',
                'marginBottom': '16px',
                'boxShadow': '0 12px 30px rgba(15, 23, 32, 0.05)',
            }),
            build_dimension_group(
                'Médias do Período',
                'Leitura de cadência, qualidade e disciplina do fluxo no recorte selecionado.',
                'Cadência, qualidade e previsibilidade',
                period_reading_panel,
                period_dimension_cards,
                '#f8fbff',
                '#cfe0f3',
            ),
            html.Div(style={'height': '12px'}),
            build_dimension_group(
                'Snapshot Atual',
                'Fotografia do fim do período para carga ativa e execução do backlog já planejado.',
                'Estoque, carga ativa e execução',
                snapshot_reading_panel,
                snapshot_dimension_cards,
                '#fffaf2',
                '#f1d7a8',
            ),
        ], style={'maxWidth': '1200px', 'margin': '0 auto 20px auto'})

        demand_capacity_max = max(metric_catalog['demand_total']['value'], metric_catalog['capacity_total']['value'], 1.0)
        demand_bar_h = f"{max(18, int((metric_catalog['demand_total']['value'] / demand_capacity_max) * 92))}px"
        capacity_bar_h = f"{max(18, int((metric_catalog['capacity_total']['value'] / demand_capacity_max) * 92))}px"
        inflow_outflow_max = max(metric_catalog['inflow_total']['value'], metric_catalog['outflow_total']['value'], 1.0)
        inflow_bar_h = f"{max(18, int((metric_catalog['inflow_total']['value'] / inflow_outflow_max) * 92))}px"
        outflow_bar_h = f"{max(18, int((metric_catalog['outflow_total']['value'] / inflow_outflow_max) * 92))}px"

        ref_panel_bg = '#f3f5f7'
        ref_card_bg = '#f3f5f7'
        ref_border = '1px solid #2b9be8'
        ref_radius = '12px'
        muted_txt = '#7b8694'
        title_txt = '#3d4b59'
        bar_primary = '#2cb3ad'
        bar_secondary = '#176ea4'
        dot_gray = '#b8c0c8'
        dot_orange = '#f1b236'
        dot_teal = '#33b7b2'

        def indicator_dots(active_color):
            return html.Div([
                html.Div(style={'width': '7px', 'height': '7px', 'borderRadius': '50%', 'backgroundColor': active_color, 'marginBottom': '6px'}),
                html.Div(style={'width': '7px', 'height': '7px', 'borderRadius': '50%', 'backgroundColor': dot_orange if active_color != dot_orange else dot_gray, 'marginBottom': '6px'}),
                html.Div(style={'width': '7px', 'height': '7px', 'borderRadius': '50%', 'backgroundColor': dot_gray}),
            ], style={'position': 'absolute', 'top': '10px', 'right': '10px'})

        reference_tile_cards = []
        for metric_id in reference_metric_ids:
            metric = metric_catalog[metric_id]
            tile_children = [
                html.H6(metric['title'], style={'marginBottom': '4px'}),
                html.Div(fmt_value(metric['value'], metric['format']), style={'fontSize': '38px', 'fontWeight': 'bold', 'lineHeight': '1.0'}),
            ]
            if metric.get('unit'):
                tile_children.append(html.P(metric['unit'], style={'marginBottom': '0'}))
            if metric.get('note'):
                tile_children.append(html.P(metric['note'], style={'fontSize': '12px', 'marginTop': '6px', 'color': '#555'}))
            reference_tile_cards.append(
                html.Div(tile_children, style={
                    'flex': '1 1 150px',
                    'backgroundColor': ref_card_bg,
                    'border': ref_border,
                    'borderRadius': ref_radius,
                    'padding': '10px',
                    'minHeight': '135px',
                    'position': 'relative',
                })
            )

        flow_reference_cards = html.Div([
            html.H4("Referências Estruturais do Fluxo", style={'textAlign': 'center', 'marginBottom': '8px', 'marginTop': '8px'}),
            html.P(
                "Bloco complementar para ler tensão do sistema e relações estruturais de estoque, compromisso e vazão sem repetir os KPIs âncora da leitura rápida.",
                style={'textAlign': 'center', 'color': '#5f6e7b', 'marginBottom': '14px'}
            ),
            html.Div([
                html.Div([
                    indicator_dots(dot_teal),
                    html.P("Demanda vs Capacidade", style={'fontSize': '28px', 'color': title_txt, 'marginBottom': '10px'}),
                    html.P(
                        f"Demanda = {demand_label}. Capacidade = {capacity_label}.",
                        style={'fontSize': '12px', 'color': '#5f6e7b', 'marginTop': '-6px', 'marginBottom': '8px'}
                    ),
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Div(style={
                                    'width': '38px',
                                    'height': demand_bar_h,
                                    'backgroundColor': bar_primary,
                                    'borderRadius': '0',
                                    'margin': '0 auto',
                                }),
                                html.P('Demanda', style={'fontSize': '16px', 'marginTop': '8px', 'marginBottom': '0', 'textAlign': 'center', 'color': '#4f5965'}),
                            ], style={'display': 'inline-block', 'width': '50%'}),
                            html.Div([
                                html.Div(style={
                                    'width': '38px',
                                    'height': capacity_bar_h,
                                    'backgroundColor': bar_secondary,
                                    'borderRadius': '0',
                                    'margin': '0 auto',
                                }),
                                html.P('Capacidade', style={'fontSize': '16px', 'marginTop': '8px', 'marginBottom': '0', 'textAlign': 'center', 'color': '#4f5965'}),
                            ], style={'display': 'inline-block', 'width': '50%'}),
                        ], style={'width': '160px', 'display': 'flex', 'alignItems': 'flex-end', 'justifyContent': 'center'}),
                        html.Ul([
                            html.Li(
                                f"Demanda {abs(true_demand_vs_capacity_pct):.1f}% acima da capacidade."
                                if pd.notna(true_demand_vs_capacity_pct) and true_demand_vs_capacity_pct >= 0
                                else (
                                    f"Demanda {abs(true_demand_vs_capacity_pct):.1f}% abaixo da capacidade."
                                    if pd.notna(true_demand_vs_capacity_pct)
                                    else "Sem base para comparação."
                                )
                            ),
                            html.Li(
                                f"Inventário cresceu em {int(abs(metric_catalog['inventory_growth']['value']))} itens de fluxo."
                                if pd.notna(metric_catalog['inventory_growth']['value']) and metric_catalog['inventory_growth']['value'] >= 0
                                else (
                                    f"Inventário reduziu em {int(abs(metric_catalog['inventory_growth']['value']))} itens de fluxo."
                                    if pd.notna(metric_catalog['inventory_growth']['value'])
                                    else "Sem base para variação de inventário."
                                )
                            ),
                            html.Li(html.Span([
                                f"Razão Demanda/Throughput: {backlog_throughput_ratio:.1f}×" if pd.notna(backlog_throughput_ratio) else "Razão Demanda/Throughput: —",
                                html.Span(
                                    " ⚠ ≥ 3×",
                                    style={
                                        'display': 'inline-block',
                                        'marginLeft': '8px',
                                        'fontSize': '11px',
                                        'fontWeight': '700',
                                        'color': '#fff',
                                        'backgroundColor': '#c62828',
                                        'borderRadius': '999px',
                                        'padding': '1px 8px',
                                        'verticalAlign': 'middle',
                                    }
                                ) if pd.notna(backlog_throughput_ratio) and backlog_throughput_ratio >= 3.0 else None,
                            ])),
                        ], style={'marginBottom': '0', 'fontSize': '16px', 'color': muted_txt, 'lineHeight': '1.7'}),
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '18px'}),
                ], className='six columns', style={
                    'position': 'relative',
                    'backgroundColor': ref_card_bg,
                    'border': ref_border,
                    'borderRadius': ref_radius,
                    'padding': '12px 12px 22px 12px',
                    'minHeight': '260px',
                }),
                html.Div([
                    indicator_dots(dot_orange),
                    html.P("Entrada vs Saída", style={'fontSize': '28px', 'color': title_txt, 'marginBottom': '10px'}),
                    html.P(
                        "Entrada = itens comprometidos no período. Saída = itens concluídos no período.",
                        style={'fontSize': '12px', 'color': '#5f6e7b', 'marginTop': '-6px', 'marginBottom': '8px'}
                    ),
                    html.Div([
                        html.Div([
                            html.Div([
                                html.Div(style={
                                    'width': '38px',
                                    'height': inflow_bar_h,
                                    'backgroundColor': bar_primary,
                                    'borderRadius': '0',
                                    'margin': '0 auto',
                                }),
                                html.P('Compromisso', style={'fontSize': '16px', 'marginTop': '8px', 'marginBottom': '0', 'textAlign': 'center', 'color': '#4f5965'}),
                            ], style={'display': 'inline-block', 'width': '50%'}),
                            html.Div([
                                html.Div(style={
                                    'width': '38px',
                                    'height': outflow_bar_h,
                                    'backgroundColor': bar_secondary,
                                    'borderRadius': '0',
                                    'margin': '0 auto',
                                }),
                                html.P('Saída', style={'fontSize': '16px', 'marginTop': '8px', 'marginBottom': '0', 'textAlign': 'center', 'color': '#4f5965'}),
                            ], style={'display': 'inline-block', 'width': '50%'}),
                        ], style={'width': '160px', 'display': 'flex', 'alignItems': 'flex-end', 'justifyContent': 'center'}),
                        html.Ul([
                            html.Li(
                                f"Entrada {abs(true_inflow_vs_outflow_pct):.1f}% acima da saída."
                                if pd.notna(true_inflow_vs_outflow_pct) and true_inflow_vs_outflow_pct >= 0
                                else (
                                    f"Entrada {abs(true_inflow_vs_outflow_pct):.1f}% abaixo da saída."
                                    if pd.notna(true_inflow_vs_outflow_pct)
                                    else "Sem base para comparação."
                                )
                            ),
                            html.Li(
                                f"WIP cresceu em {int(abs(metric_catalog['wip_growth']['value']))} itens de fluxo."
                                if metric_catalog['wip_growth']['value'] >= 0
                                else f"WIP reduziu em {int(abs(metric_catalog['wip_growth']['value']))} itens de fluxo."
                            ),
                            html.Li(html.Span([
                                f"Razão Entrada/Throughput: {inflow_throughput_ratio:.1f}×" if pd.notna(inflow_throughput_ratio) else "Razão Entrada/Throughput: —",
                                html.Span(
                                    " ⚠ ≥ 3×",
                                    style={
                                        'display': 'inline-block',
                                        'marginLeft': '8px',
                                        'fontSize': '11px',
                                        'fontWeight': '700',
                                        'color': '#fff',
                                        'backgroundColor': '#c62828',
                                        'borderRadius': '999px',
                                        'padding': '1px 8px',
                                        'verticalAlign': 'middle',
                                    }
                                ) if pd.notna(inflow_throughput_ratio) and inflow_throughput_ratio >= 3.0 else None,
                            ])),
                        ], style={'marginBottom': '0', 'fontSize': '16px', 'color': muted_txt, 'lineHeight': '1.7'}),
                    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '18px'}),
                ], className='six columns', style={
                    'position': 'relative',
                    'backgroundColor': ref_card_bg,
                    'border': ref_border,
                    'borderRadius': ref_radius,
                    'padding': '12px 12px 22px 12px',
                    'minHeight': '260px',
                }),
            ], className='row', style={'marginBottom': '12px'}),
            html.Div(reference_tile_cards, style={
                'display': 'flex',
                'flexWrap': 'wrap',
                'gap': '10px',
                'marginTop': '8px',
            }),
        ], style={'maxWidth': '1200px', 'margin': '0 auto 20px auto', 'padding': '0 6px', 'backgroundColor': ref_panel_bg})

        complementary_metric_section = html.Div([
            html.Div([
                html.Div('Leitura complementar', style={
                    'display': 'inline-block',
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'letterSpacing': '0.05em',
                    'textTransform': 'uppercase',
                    'color': '#5f6e7b',
                    'backgroundColor': '#f5f7fa',
                    'border': '1px solid #d6dee6',
                    'borderRadius': '999px',
                    'padding': '5px 10px',
                    'marginBottom': '10px',
                }),
                html.H4("Indicadores Complementares", style={'marginBottom': '8px', 'color': '#10202f'}),
                html.P(
                    "Esta grade fica só com sinais adicionais de média, compromisso, pressão e risco que aprofundam a análise sem repetir os indicadores já destacados acima.",
                    style={'color': '#5f6e7b', 'marginBottom': '0', 'fontSize': '13px', 'lineHeight': '1.6'}
                ),
            ], style={'padding': '0 6px'}),
            html.Div(card_rows, style={'maxWidth': '1200px', 'margin': '0 auto'}),
        ], style={'maxWidth': '1200px', 'margin': '0 auto'})

        return html.Div([
            html.H3("Painel Principal de Gestão de Fluxo", style={'textAlign': 'center'}),
            leadtime_selection_summary,
            html.P(
                "Sinais executivos de fluxo para o filtro ativo de projeto e período. "
                "Semáforo por CV: OK (<=30%), Razoável (>30% e <=50%), Ruim (>50% e <=65%), Crítico (>65% e <=80%) e Extremamente Crítico (>80%). "
                "Limites fixos: Pressão de fluxo (rho=chegada/vazão) OK <=0.80, Atenção >0.80 e <=0.90, Crítico >0.90 e <=0.95, Extremamente Crítico >0.95. "
                "Eficiência (1-rho) inversa: OK >=0.20, Atenção >=0.10 e <0.20, Crítico >=0.05 e <0.10, Extremamente Crítico <0.05.",
                style={'textAlign': 'center', 'color': '#666', 'marginBottom': '20px'}
            ),
            flow_dimension_section,
            flow_reference_cards,
            complementary_metric_section,
        ])


    if tab == 'tab-cfd':
        start_ts = pd.to_datetime(start_date) if start_date else fato['DataDone'].min()
        end_ts = pd.to_datetime(end_date) if end_date else pd.to_datetime('today')

        df_flow = df.copy()

        mask_started_until_end = df_flow['DataInProgress'].isna() | (df_flow['DataInProgress'] <= end_ts)
        mask_not_finished_before_start = df_flow['DataDone'].isna() | (df_flow['DataDone'] >= start_ts)
        df_flow = df_flow[mask_started_until_end & mask_not_finished_before_start].copy()
        if df_flow.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        bottlenecks_df = load_project_bottlenecks_from_model(projeto)
        if bottlenecks_df.empty:
            bottlenecks_df = load_project_bottlenecks_from_csv(projeto)
        if bottlenecks_df.empty:
            bottlenecks_df = compute_flow_bottlenecks(df_flow)

        arrivals_period = len(df_flow[
            (df_flow['DataInProgress'] >= start_ts) &
            (df_flow['DataInProgress'] <= end_ts)
        ])
        throughput_period = int(len(df[done_time_eligible_mask(df)])) if not df.empty else 0
        filtered_done_ids = df.get('ItemID', pd.Series(dtype=str)).tolist()

        cfd_graph_component = html.P('Sem dados suficientes para montar o Cumulative Flow Diagram (CFD).')
        cfd_summary_store = {}
        cfd_summary_default = html.Div(
            'Clique ou passe o mouse sobre um ponto do CFD para ver o quadro de estatísticas sumárias.',
            style={'color': '#666', 'padding': '12px', 'border': '1px dashed #d1d5db', 'borderRadius': '8px'}
        )

        df_cfd, _ = build_cfd_dataframe(df_flow, start_ts=start_ts, end_ts=end_ts)
        if not df_cfd.empty:
            fig_cfd = create_cfd_figure(
                df_cfd,
                bottlenecks_df=bottlenecks_df,
                projeto=projeto,
                filtered_item_ids=filtered_done_ids,
            )
            if isinstance(fig_cfd, go.Figure):
                cfd_graph_component = dcc.Graph(
                    id='cfd-graph',
                    figure=fig_cfd,
                    clear_on_unhover=False,
                    config={'displaylogo': False},
                )
                cfd_summary_store = build_cfd_summary_payload(
                    df_cfd,
                    projeto=projeto,
                    bottlenecks_df=bottlenecks_df,
                    filtered_item_ids=filtered_done_ids,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    arrivals_period=arrivals_period,
                    throughput_period=throughput_period,
                )
                cfd_summary_default = create_cfd_summary_panel(cfd_summary_store)

        return html.Div([
            html.H3("Cumulative Flow Diagram (CFD)", style={'textAlign': 'center'}),
            html.P(
                "Aba dedicada do CFD com modos Macro e Detalhado por Etapas (exato). "
                "O quadro de estatísticas sumárias lê o ponto selecionado no gráfico.",
                style={'textAlign': 'center', 'color': '#666', 'marginBottom': '14px'}
            ),
            dcc.Store(id='cfd-summary-store', data=cfd_summary_store),
            cfd_graph_component,
            html.Div(id='cfd-summary-panel', children=cfd_summary_default, style={'marginTop': '14px'}),
        ])

    if tab == 'tab-estabilidade':
        if df.empty or 'LeadTime_Dias' not in df.columns or df['LeadTime_Dias'].dropna().empty:
            return html.Div('Sem dados de Lead Time para exibir para o período e filtros selecionados.')

        # --- 1. Calcular Métricas de Estabilidade ---
        metrics = {}
        # Throughput
        tp_weekly = df.copy()
        tp_weekly['_FilterDate'] = resolve_filter_date_series(tp_weekly, use_creation_date=use_creation_date)
        tp_weekly = tp_weekly.dropna(subset=['_FilterDate'])
        tp_weekly['Semana'] = weekly_bucket_start(tp_weekly['_FilterDate'])
        tp_weekly = tp_weekly.groupby('Semana').size().reset_index(name='Throughput')
        if not tp_weekly.empty and tp_weekly['Throughput'].mean() > 0:
            metrics['Desvio Padrão do Throughput'] = tp_weekly['Throughput'].std()
            metrics['Coeficiente de Variação (%)'] = (tp_weekly['Throughput'].std() / tp_weekly['Throughput'].mean()) * 100

        # Lead Time
        lead_times = time_metric_series(df, 'LeadTime_Dias')
        metrics['Lead Time P50 (dias)'] = exact_empirical_percentile(lead_times, 0.50)
        metrics['Lead Time P75 (dias)'] = exact_empirical_percentile(lead_times, 0.75)
        metrics['Lead Time P95 (dias)'] = exact_empirical_percentile(lead_times, 0.95)

        # Intervalo de Confiança 95% para o Lead Time
        lt_mean = lead_times.mean()
        lt_std = lead_times.std()
        n = len(lead_times)
        if n > 1:
            ci_margin = 1.96 * (lt_std / np.sqrt(n))
            metrics['Intervalo de Confiança 95%'] = f"{lt_mean - ci_margin:.1f} - {lt_mean + ci_margin:.1f} dias"

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}" if isinstance(v, (int, float)) else v} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        # --- 2. Criar Gráficos ---
        fig_throughput_trend = px.line(tp_weekly, x='Semana', y='Throughput', title='Throughput Semanal', markers=True)
        add_statistical_lines(fig_throughput_trend, tp_weekly['Semana'], tp_weekly['Throughput'])
        fig_throughput_trend.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))
        df_lt_plot = df[done_time_eligible_mask(df)].copy()
        fig_lead_time_dist = px.box(df_lt_plot, y='LeadTime_Dias', title='Distribuição de Lead Time e Percentis', points="all")
        fig_lead_time_dist.update_layout(height=500)

        return html.Div([
            html.H3("Análise de Estabilidade", style={'textAlign': 'center'}),
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            dcc.Graph(figure=fig_throughput_trend),
            dcc.Graph(figure=fig_lead_time_dist),
        ])

    if tab == 'tab-saude':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        df_health_base = df.copy()
        health_filter_dates = resolve_filter_date_series(df_health_base, use_creation_date=use_creation_date)
        # --- 1. Calcular Métricas de Saúde ---
        arrivals_df = df_health_base[(df_health_base['DataInProgress'] >= start_date_ts) & (df_health_base['DataInProgress'] <= end_date_ts)]
        throughput_df = df_health_base[build_date_range_mask(health_filter_dates, start_date_ts, end_date_ts)].copy()
        wip_start_count = len(df_health_base[(df_health_base['DataInProgress'] < start_date_ts) & ((df_health_base['DataDone'] >= start_date_ts) | pd.isna(df_health_base['DataDone']))])
        wip_end_count = len(df_health_base[(df_health_base['DataInProgress'] <= end_date_ts) & ((df_health_base['DataDone'] > end_date_ts) | pd.isna(df_health_base['DataDone']))])

        arrivals_count = len(arrivals_df)
        throughput_count = len(throughput_df)

        metrics = {}
        work_to_be_done = wip_start_count + arrivals_count
        metrics['Taxa Conclusão (%)'] = (throughput_count / work_to_be_done * 100) if work_to_be_done > 0 else 0
        metrics['Ratio Chegada/Throughput'] = arrivals_count / throughput_count if throughput_count > 0 else 0
        metrics['Crescimento WIP (%)'] = ((wip_end_count - wip_start_count) / wip_start_count * 100) if wip_start_count > 0 else (wip_end_count * 100 if wip_end_count > 0 else 0)
        
        lt_throughput = time_metric_series(throughput_df, 'LeadTime_Dias')
        p85_lt = exact_empirical_percentile(lt_throughput, 0.85) if not lt_throughput.empty else 0
        metrics['Itens Vencidos (>P85)'] = (
            len(throughput_df[done_time_eligible_mask(throughput_df) & (pd.to_numeric(throughput_df['LeadTime_Dias'], errors='coerce') > p85_lt)])
            if p85_lt > 0 else 0
        )

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}"} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']], data=kpi_data, style_cell={'textAlign': 'left', 'padding': '5px'}, style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'})

        # --- 2. Criar Gráficos ---
        # Chegadas vs Throughput
        arrivals_weekly = arrivals_df.dropna(subset=['DataInProgress']).copy()
        arrivals_weekly['Semana'] = weekly_bucket_start(arrivals_weekly['DataInProgress'])
        arrivals_weekly = arrivals_weekly.groupby('Semana').size().reset_index(name='Count')
        arrivals_weekly['Métrica'] = 'Chegadas'
        throughput_weekly = throughput_df.copy()
        throughput_weekly['_FilterDate'] = resolve_filter_date_series(throughput_weekly, use_creation_date=use_creation_date)
        throughput_weekly = throughput_weekly.dropna(subset=['_FilterDate'])
        throughput_weekly['Semana'] = weekly_bucket_start(throughput_weekly['_FilterDate'])
        throughput_weekly = throughput_weekly.groupby('Semana').size().reset_index(name='Count')
        throughput_weekly['Métrica'] = 'Throughput'

        flow_df = pd.concat([arrivals_weekly, throughput_weekly]).sort_values('Semana')
        fig_flow = px.bar(flow_df, x='Semana', y='Count', color='Métrica', barmode='group', title='Chegadas vs. Throughput Semanal', color_discrete_map={'Chegadas': 'blue', 'Throughput': 'green'})
        fig_flow.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        # Tendência do WIP
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        wip_trend_data = []
        for week_end in weeks:
            wip_at_date = len(df_health_base[(df_health_base['DataInProgress'] <= week_end) & ((df_health_base['DataDone'] > week_end) | pd.isna(df_health_base['DataDone']))])
            wip_trend_data.append({'Semana': week_end, 'WIP': wip_at_date})
        
        wip_trend_df = pd.DataFrame(wip_trend_data)
        fig_wip_trend = px.line(wip_trend_df, x='Semana', y='WIP', title='Tendência do WIP Semanal', markers=True) if not wip_trend_df.empty else {}
        if not wip_trend_df.empty:
            add_statistical_lines(fig_wip_trend, wip_trend_df['Semana'], wip_trend_df['WIP'])
            fig_wip_trend.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        _is_multi_month = (
            start_date_ts.year != end_date_ts.year or
            start_date_ts.month != end_date_ts.month
        )
        if _is_multi_month:
            hs_overall, hs_monthly = compute_health_score_monthly(df_health_base, start_date_ts, end_date_ts)
            hs_panel = render_health_score_panel(hs_overall, hs_monthly)
        else:
            hs_overall = compute_health_score(df_health_base, start=start_date_ts, end=end_date_ts)
            hs_panel = render_health_score_panel(hs_overall)

        return html.Div([
            html.H3("Análise de Saúde do Fluxo", style={'textAlign': 'center', 'marginBottom': '20px'}),
            hs_panel,
            html.Div(kpi_table, style={'width': '50%', 'margin': 'auto', 'marginBottom': '30px'}),
            dcc.Graph(figure=fig_flow),
            dcc.Graph(figure=fig_wip_trend),
            html.Hr(style={'margin': '30px 0'}),
            render_tab(
                main_view=main_view,
                tab='tab-estabilidade',
                start_date=start_date,
                end_date=end_date,
                projeto=projeto,
                tipo=tipo,
                tipo_original_jira=tipo_original_jira,
                classe_servico=classe_servico,
                responsavel=responsavel,
                leadtime_stages=leadtime_stages,
                etapa_fluxo=etapa_fluxo,
                capacity_top_n=capacity_top_n,
                capacity_weekly_metric=capacity_weekly_metric,
                portfolio_team=portfolio_team,
                portfolio_quarter=portfolio_quarter,
                pf_backlog_15=pf_backlog_15,
                pf_backlog_30=pf_backlog_30,
                pf_fresh_15=pf_fresh_15,
                pf_fresh_30=pf_fresh_30,
                pf_decision_statuses=pf_decision_statuses,
                pf_workflow_statuses=pf_workflow_statuses,
                pf_sla_aging_json=pf_sla_aging_json,
                pf_target_mix_json=pf_target_mix_json,
                criadores=criadores,
                date_filter_mode=date_filter_mode,
            ),
            html.Hr(style={'margin': '30px 0'}),
            render_tab(
                main_view=main_view,
                tab='tab-qualidade',
                start_date=start_date,
                end_date=end_date,
                projeto=projeto,
                tipo=tipo,
                tipo_original_jira=tipo_original_jira,
                classe_servico=classe_servico,
                responsavel=responsavel,
                leadtime_stages=leadtime_stages,
                etapa_fluxo=etapa_fluxo,
                capacity_top_n=capacity_top_n,
                capacity_weekly_metric=capacity_weekly_metric,
                portfolio_team=portfolio_team,
                portfolio_quarter=portfolio_quarter,
                pf_backlog_15=pf_backlog_15,
                pf_backlog_30=pf_backlog_30,
                pf_fresh_15=pf_fresh_15,
                pf_fresh_30=pf_fresh_30,
                pf_decision_statuses=pf_decision_statuses,
                pf_workflow_statuses=pf_workflow_statuses,
                pf_sla_aging_json=pf_sla_aging_json,
                pf_target_mix_json=pf_target_mix_json,
                criadores=criadores,
                date_filter_mode=date_filter_mode,
            ),
        ])

    if tab == 'tab-qualidade':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        # --- 1. Calcular Métricas de Qualidade ---
        defects_count = len(df[df['TipoDemanda'] == TYPE_ISSUES])
        development_count = len(df[df['TipoDemanda'] == TYPE_DEV])
        total_completed = len(df)

        metrics = {}
        metrics['Debt Ratio (% Defeitos)'] = (defects_count / total_completed * 100) if total_completed > 0 else 0
        
        razao = development_count / defects_count if defects_count > 0 else float('inf')
        metrics['Razão Valor/Custo'] = f"{razao:.2f}:1" if razao != float('inf') else "Infinito (sem defeitos)"

        arrivals_base = df.copy()
        arrivals_count = len(arrivals_base[
            (arrivals_base['DataInProgress'] >= pd.to_datetime(start_date)) &
            (arrivals_base['DataInProgress'] <= pd.to_datetime(end_date))
        ])
        throughput_count = len(df)
        pressure_quality, efficiency_quality = calculate_flow_efficiency(arrivals_count, throughput_count)
        if pd.notna(efficiency_quality):
            metrics['Eficiência de Fluxo (1 - ρ)'] = efficiency_quality
        if pd.notna(pressure_quality):
            metrics['Pressão de Fluxo (ρ = λ/μ)'] = pressure_quality

        kpi_data = [{'Métrica': k, 'Valor': f"{v:.2f}" if isinstance(v, (int, float)) else v} for k, v in metrics.items()]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        )

        # --- 2. Criar Gráfico ---
        by_tipo = df.groupby('TipoDemanda').size().reset_index(name='Count')
        fig_pie = px.pie(by_tipo, names='TipoDemanda', values='Count',
                         title='Distribuição do Throughput por Tipo',
                         color='TipoDemanda', color_discrete_map=color_map)
        fig_pie.update_layout(height=500)

        razao_explicacao = html.Div([
            html.H4("Razão Valor/Custo", style={'marginTop': '30px', 'marginBottom': '10px'}),
            html.P([
                "A ", html.Strong("Razão Valor/Custo"), " indica quantos itens de ",
                html.Span("Desenvolvimento (demanda de valor)", style={'color': 'green', 'fontWeight': 'bold'}),
                " foram entregues para cada item de ",
                html.Span("Defeito (demanda de falha)", style={'color': 'red', 'fontWeight': 'bold'}),
                " no período selecionado."
            ], style={'fontSize': '14px', 'lineHeight': '1.6'}),
            html.Ul([
                html.Li([html.Strong("Exemplo: 3.00:1"), " — para cada defeito corrigido, 3 itens de valor foram entregues."]),
                html.Li([html.Strong("Valor alto (> 4:1)"), " — o time está focado em gerar valor, com baixa incidência de retrabalho."]),
                html.Li([html.Strong("Valor baixo (< 2:1)"), " — grande parte do esforço está sendo consumido por correções de defeitos, sinalizando problemas de qualidade."]),
                html.Li([html.Strong("Infinito"), " — nenhum defeito foi registrado no período."]),
            ], style={'fontSize': '13px', 'lineHeight': '1.8', 'color': '#444'}),
            html.P("Fórmula: Throughput de Desenvolvimento / Throughput de Defeitos",
                   style={'fontSize': '12px', 'color': '#888', 'fontStyle': 'italic', 'marginTop': '10px'}),
        ], style={'padding': '15px', 'backgroundColor': '#f9f9f9', 'borderRadius': '8px', 'border': '1px solid #e0e0e0', 'marginTop': '20px'})

        return html.Div([
            html.H3("Análise de Qualidade", style={'textAlign': 'center'}),
            html.Div([
                html.Div(kpi_table, className='six columns', style={'padding': '20px'}),
                html.Div(dcc.Graph(figure=fig_pie), className='six columns'),
            ], className='row'),
            razao_explicacao,
        ])

    if tab == 'tab-analise-fluxo':
        return html.Div([
            html.H3("Análise Fluxo", style={'textAlign': 'center'}),
            html.P(
                "Consolidação das análises dimensional, por tipos e eficiência de fluxo.",
                style={'textAlign': 'center', 'color': '#666', 'marginTop': '-8px'}
            ),
            html.Hr(),
            render_tab(
                main_view=main_view,
                tab='tab-dim',
                start_date=start_date,
                end_date=end_date,
                projeto=projeto,
                tipo=tipo,
                tipo_original_jira=tipo_original_jira,
                classe_servico=classe_servico,
                responsavel=responsavel,
                leadtime_stages=leadtime_stages,
                etapa_fluxo=etapa_fluxo,
                capacity_top_n=capacity_top_n,
                capacity_weekly_metric=capacity_weekly_metric,
                portfolio_team=portfolio_team,
                portfolio_quarter=portfolio_quarter,
                pf_backlog_15=pf_backlog_15,
                pf_backlog_30=pf_backlog_30,
                pf_fresh_15=pf_fresh_15,
                pf_fresh_30=pf_fresh_30,
                pf_decision_statuses=pf_decision_statuses,
                pf_workflow_statuses=pf_workflow_statuses,
                pf_sla_aging_json=pf_sla_aging_json,
                pf_target_mix_json=pf_target_mix_json,
                criadores=criadores,
                date_filter_mode=date_filter_mode,
            ),
            html.Hr(),
            render_tab(
                main_view=main_view,
                tab='tab-tipos',
                start_date=start_date,
                end_date=end_date,
                projeto=projeto,
                tipo=tipo,
                tipo_original_jira=tipo_original_jira,
                classe_servico=classe_servico,
                responsavel=responsavel,
                leadtime_stages=leadtime_stages,
                etapa_fluxo=etapa_fluxo,
                capacity_top_n=capacity_top_n,
                capacity_weekly_metric=capacity_weekly_metric,
                portfolio_team=portfolio_team,
                portfolio_quarter=portfolio_quarter,
                pf_backlog_15=pf_backlog_15,
                pf_backlog_30=pf_backlog_30,
                pf_fresh_15=pf_fresh_15,
                pf_fresh_30=pf_fresh_30,
                pf_decision_statuses=pf_decision_statuses,
                pf_workflow_statuses=pf_workflow_statuses,
                pf_sla_aging_json=pf_sla_aging_json,
                pf_target_mix_json=pf_target_mix_json,
                criadores=criadores,
                date_filter_mode=date_filter_mode,
            ),
            html.Hr(),
            render_tab(
                main_view=main_view,
                tab='tab-eficiencia',
                start_date=start_date,
                end_date=end_date,
                projeto=projeto,
                tipo=tipo,
                tipo_original_jira=tipo_original_jira,
                classe_servico=classe_servico,
                responsavel=responsavel,
                leadtime_stages=leadtime_stages,
                etapa_fluxo=etapa_fluxo,
                capacity_top_n=capacity_top_n,
                capacity_weekly_metric=capacity_weekly_metric,
                portfolio_team=portfolio_team,
                portfolio_quarter=portfolio_quarter,
                pf_backlog_15=pf_backlog_15,
                pf_backlog_30=pf_backlog_30,
                pf_fresh_15=pf_fresh_15,
                pf_fresh_30=pf_fresh_30,
                pf_decision_statuses=pf_decision_statuses,
                pf_workflow_statuses=pf_workflow_statuses,
                pf_sla_aging_json=pf_sla_aging_json,
                pf_target_mix_json=pf_target_mix_json,
                criadores=criadores,
                date_filter_mode=date_filter_mode,
            ),
        ])

    if tab == 'tab-dim':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        def create_dim_graphs(df_filtered, dim_col, dim_title, top_n=30):
            # Throughput
            by_dim_tp = df_filtered.groupby(dim_col).size().reset_index(name='Throughput').sort_values('Throughput', ascending=False).head(top_n)
            fig_tp = px.bar(by_dim_tp, x=dim_col, y='Throughput', title=f'Throughput por {dim_title}')
            fig_tp.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))

            # Defect Rate
            total_by_dim = df_filtered.groupby(dim_col).size()
            defects_by_dim = df_filtered[df_filtered['TipoDemanda'] == TYPE_ISSUES].groupby(dim_col).size()
            defect_rate_df = (defects_by_dim / total_by_dim * 100).fillna(0).reset_index(name='Taxa de Defeitos (%)')
            defect_rate_df = defect_rate_df[defect_rate_df[dim_col].isin(by_dim_tp[dim_col])]

            fig_defect = px.bar(defect_rate_df, x=dim_col, y='Taxa de Defeitos (%)', title=f'Taxa de Defeitos por {dim_title}')
            fig_defect.update_traces(marker_color='red')
            fig_defect.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))
            
            return html.Div([
                html.H4(f"Análise por {dim_title}", style={'textAlign': 'center', 'marginTop': '40px'}),
                html.Div([
                    html.Div(dcc.Graph(figure=fig_tp), className='six columns'),
                    html.Div(dcc.Graph(figure=fig_defect), className='six columns'),
                ], className='row')
            ])

        graphs = [html.H3("Análise Dimensional", style={'textAlign': 'center'})]
        
        if 'Projeto' in df.columns:
            graphs.append(create_dim_graphs(df, 'Projeto', 'Projeto', top_n=100))
        if 'Responsavel' in df.columns:
            graphs.append(create_dim_graphs(df, 'Responsavel', 'Responsável', top_n=30))
        if 'Componente' in df.columns and not df['Componente'].dropna().empty:
            graphs.append(create_dim_graphs(df, 'Componente', 'Componente', top_n=30))
        if 'Prioridade' in df.columns and not df['Prioridade'].dropna().empty:
            graphs.append(create_dim_graphs(df, 'Prioridade', 'Prioridade', top_n=100))

        return html.Div(graphs)

    if tab == 'tab-tipos':
        by_tipo = df.groupby('TipoDemanda').agg({'ItemID':'count', 'LeadTime_Dias':'median'}).rename(columns={'ItemID':'Throughput','LeadTime_Dias':'LeadTime_Mediano'}).reset_index()
        
        graphs = []
        # % por Tipo de Problema (Bug, Feature, Tarefa, Suporte) -> Usando a coluna 'Tipo'
        fig_pie = px.pie(by_tipo, names='TipoDemanda', values='Throughput', title='Distribuição do Throughput por Tipo', color='TipoDemanda', color_discrete_map=color_map)
        fig_pie.update_layout(height=500)
        graphs.append(dcc.Graph(figure=fig_pie))

        # Lead Time por Tipo
        fig_lt = px.bar(by_tipo, x='TipoDemanda', y='LeadTime_Mediano', title='Lead Time Mediano por Tipo', color='TipoDemanda', color_discrete_map=color_map)
        fig_lt.update_layout(height=500)
        graphs.append(dcc.Graph(figure=fig_lt))

        # Throughput por Subtipo
        if 'WorkItemSubType' in df.columns and not df['WorkItemSubType'].dropna().empty:
            by_subtipo = df.groupby('WorkItemSubType').size().reset_index(name='Throughput').sort_values('Throughput', ascending=False)
            fig_subtipo = px.bar(by_subtipo, x='WorkItemSubType', y='Throughput', title='Throughput por Subtipo')
            fig_subtipo.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=130))
            graphs.append(dcc.Graph(figure=fig_subtipo))

        return html.Div(graphs)

    if tab == 'tab-tendencias':
        tp = df.copy()
        tp['_FilterDate'] = resolve_filter_date_series(tp, use_creation_date=use_creation_date)
        tp = tp.dropna(subset=['_FilterDate'])
        tp['Semana'] = weekly_bucket_start(tp['_FilterDate'])
        tp = tp.groupby('Semana').size().reset_index(name='Throughput')
        fig_tp = go.Figure()
        fig_tp.add_trace(go.Scatter(x=tp['Semana'], y=tp['Throughput'], mode='lines+markers', name='Throughput'))
        add_statistical_lines(fig_tp, tp['Semana'], tp['Throughput'])
        fig_tp.update_layout(title='Throughput Semanal (P15, P85, P95, Média, MM5)', height=600, xaxis_tickangle=-45, margin=dict(b=130))

        # Trend Direction
        ma5_tp = tp['Throughput'].rolling(5, min_periods=1).mean()
        trend_direction = '→'
        if len(ma5_tp) >= 5:
            last_ma = ma5_tp.iloc[-1]
            prev_ma = ma5_tp.iloc[-5]
            if prev_ma > 0:
                if last_ma > prev_ma * 1.1: trend_direction = '↑'
                elif last_ma < prev_ma * 0.9: trend_direction = '↓'

        # WIP e Lead Time média móvel
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)
        df_trend_base = df.copy()
        # Lead Time Trend
        lt_weekly = df.dropna(subset=['LeadTime_Dias']).copy()
        lt_weekly['_FilterDate'] = resolve_filter_date_series(lt_weekly, use_creation_date=use_creation_date)
        lt_weekly = lt_weekly.dropna(subset=['_FilterDate'])
        lt_weekly['Semana'] = weekly_bucket_start(lt_weekly['_FilterDate'])
        lt_weekly = lt_weekly.groupby('Semana', as_index=False).agg(LeadTime_Dias=('LeadTime_Dias', 'mean'))

        # WIP Trend
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        wip_trend_data = []
        for week_end in weeks:
            wip_at_date = len(df_trend_base[(df_trend_base['DataInProgress'] <= week_end) & ((df_trend_base['DataDone'] > week_end) | pd.isna(df_trend_base['DataDone']))])
            wip_trend_data.append({'Semana': week_end, 'WIP': wip_at_date})
        wip_trend_df = pd.DataFrame(wip_trend_data)

        # Create figure with secondary y-axis
        fig_wip_lt = make_subplots(specs=[[{"secondary_y": True}]])
        if not wip_trend_df.empty:
            fig_wip_lt.add_trace(go.Scatter(x=wip_trend_df['Semana'], y=wip_trend_df['WIP'], name="WIP", mode='lines+markers'), secondary_y=False)
            add_statistical_lines(fig_wip_lt, wip_trend_df['Semana'], wip_trend_df['WIP'], name_prefix='WIP ', secondary_y=False)
        if not lt_weekly.empty:
            fig_wip_lt.add_trace(go.Scatter(x=lt_weekly['Semana'], y=lt_weekly['LeadTime_Dias'], name="Lead Time", mode='lines+markers'), secondary_y=True)
            add_statistical_lines(fig_wip_lt, lt_weekly['Semana'], lt_weekly['LeadTime_Dias'], name_prefix='LT ', secondary_y=True)

        fig_wip_lt.update_layout(title_text="Tendência Semanal de WIP e Lead Time", height=600, margin=dict(b=130))
        fig_wip_lt.update_xaxes(title_text="Semana", tickangle=-45)
        fig_wip_lt.update_yaxes(title_text="Contagem de WIP", secondary_y=False)
        fig_wip_lt.update_yaxes(title_text="Lead Time Médio (dias)", secondary_y=True)

        return html.Div([
            create_kpi_card('Direção da Tendência (Throughput)', trend_direction, class_name='twelve columns'),
            dcc.Graph(figure=fig_tp),
            dcc.Graph(figure=fig_wip_lt)
        ])

    if tab == 'tab-throughput-breakdown':
        tp_done = build_delivered_items_base(df)
        if tp_done.empty:
            return html.Div('Sem dados de Throughput para exibir para o período e filtros selecionados.')

        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)
        tp_done['_FilterDate'] = resolve_filter_date_series(tp_done, use_creation_date=use_creation_date)
        tp_done = tp_done.dropna(subset=['_FilterDate'])
        tp_done['Semana'] = weekly_bucket_start(tp_done['_FilterDate'])
        tp_weekly = tp_done.groupby('Semana').size().reset_index(name='Throughput')
        fig_tp_weekly = px.line(
            tp_weekly,
            x='Semana',
            y='Throughput',
            title='Throughput Semanal',
            markers=True,
        )
        add_statistical_lines(fig_tp_weekly, tp_weekly['Semana'], tp_weekly['Throughput'], name_prefix='Total ')
        fig_tp_weekly.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=100))

        throughput_cost_data = build_throughput_avg_cost_series(
            tp_done=tp_done,
            scope_df=df,
            start_ts=start_date_ts,
            end_ts=end_date_ts,
            use_creation_date=use_creation_date,
        )
        fig_tp_cost_avg = go.Figure()
        throughput_cost_summary = html.Div(
            str(throughput_cost_data.get('error', 'Sem base suficiente para monetizar o throughput no período selecionado.')),
            style={'textAlign': 'center', 'color': '#666', 'marginBottom': '12px'}
        )
        if throughput_cost_data.get('available'):
            tp_cost_df = throughput_cost_data.get('series_df', pd.DataFrame()).copy()
            fig_tp_cost_avg = go.Figure()
            fig_tp_cost_avg.add_trace(
                go.Scatter(
                    x=tp_cost_df['Semana'],
                    y=tp_cost_df['Custo Medio Demanda (R$)'],
                    mode='lines+markers',
                    name='Custo médio',
                    line=dict(color='#1f77b4', width=2),
                    customdata=tp_cost_df[['Throughput', 'DiasUteisRateados', 'CustoCapacidadeBucket (R$)', 'HorasProdutivasBucket']].to_numpy(),
                    hovertemplate=(
                        'Semana %{x|%d/%m/%Y}'
                        '<br>Custo médio: R$ %{y:,.2f}'
                        '<br>Throughput: %{customdata[0]}'
                        '<br>Dias úteis rateados: %{customdata[1]}'
                        '<br>Custo do bucket: R$ %{customdata[2]:,.2f}'
                        '<br>Horas produtivas rateadas: %{customdata[3]:,.1f}<extra></extra>'
                    ),
                )
            )
            fig_tp_cost_avg.add_trace(
                go.Scatter(
                    x=tp_cost_df['Semana'],
                    y=tp_cost_df['Media Movel Custo Medio (R$)'],
                    mode='lines',
                    name='MM(5)',
                    line=dict(color='#6a1b9a', width=2.5, dash='solid'),
                    hovertemplate='Semana %{x|%d/%m/%Y}<br>MM(5): R$ %{y:,.2f}<extra></extra>',
                )
            )
            avg_cost_mean = throughput_cost_data.get('avg_cost_mean')
            avg_cost_p85 = throughput_cost_data.get('avg_cost_p85')
            if pd.notna(avg_cost_mean):
                fig_tp_cost_avg.add_trace(
                    go.Scatter(
                        x=tp_cost_df['Semana'],
                        y=[avg_cost_mean] * len(tp_cost_df),
                        mode='lines',
                        name='Média período',
                        line=dict(color='#1565c0', width=1.5, dash='dot'),
                        hovertemplate='Média do período: R$ %{y:,.2f}<extra></extra>',
                    )
                )
            if pd.notna(avg_cost_p85):
                fig_tp_cost_avg.add_trace(
                    go.Scatter(
                        x=tp_cost_df['Semana'],
                        y=[avg_cost_p85] * len(tp_cost_df),
                        mode='lines',
                        name='P85',
                        line=dict(color='#ef6c00', width=1.5, dash='dash'),
                        hovertemplate='P85: R$ %{y:,.2f}<extra></extra>',
                    )
                )
            fig_tp_cost_avg.update_layout(
                title='Custo Médio da Demanda por Semana',
                template='plotly_white',
                height=500,
                xaxis_tickangle=-45,
                margin=dict(b=100),
                hovermode='x unified',
                yaxis_title='Custo médio por demanda (R$)',
            )
            fig_tp_cost_avg.update_yaxes(tickprefix='R$ ')
            throughput_cost_summary = html.Div([
                html.Div([
                    create_kpi_card('Custo médio / demanda', format_currency_br(avg_cost_mean), class_name='three columns'),
                    create_kpi_card('P85 custo / demanda', format_currency_br(avg_cost_p85), class_name='three columns'),
                    create_kpi_card('Custo hora usado', format_currency_br(throughput_cost_data.get('cost_hour'), suffix='/h'), class_name='three columns'),
                    create_kpi_card('Custo mensal rateado', format_currency_br(throughput_cost_data.get('monthly_cost')), class_name='three columns'),
                ], className='row'),
                html.P(
                    (
                        f"Parâmetros reaproveitados da régua financeira nativa: "
                        f"`FLOW_PMO_PORTFOLIO_COST_MODEL` (dias úteis/mês={int(throughput_cost_data.get('dias_uteis_mes', 0) or 0)}), "
                        f"`FLOW_PMO_PORTFOLIO_ROLE_SALARY_MAP`, `FLOW_PMO_PORTFOLIO_BU_SALARY_MAP` e "
                        f"`FLOW_PMO_PM_COST_PER_HOUR_MAP` quando houver override por produto. "
                        f"`Custo médio / demanda` = custo total rateado do período ÷ throughput total do período. "
                        f"Escopo monetizado: {throughput_cost_data.get('scope_label', 'TI total')} ({throughput_cost_data.get('scope_source', 'escopo global')})."
                    ),
                    style={'textAlign': 'center', 'color': '#666', 'marginTop': '6px', 'marginBottom': '14px'}
                ),
            ])

        delivery_breakdown = build_period_evolution_sustainability_breakdown(tp_done, start_date_ts, end_date_ts)
        period_order = [_format_month_label_pt_br(ts) for ts in pd.date_range(
            start=pd.Timestamp(start_date_ts).to_period('M').start_time,
            end=pd.Timestamp(end_date_ts).to_period('M').start_time,
            freq='MS',
        )]
        delivery_color_map = {
            'Evolução': '#2E7D32',
            'Sustentação': '#F9A825',
        }
        fig_type_breakdown = px.bar(
            delivery_breakdown,
            x='Percentual',
            y='Barra',
            color='CategoriaEntrega',
            orientation='h',
            text=delivery_breakdown['Percentual'].map(lambda v: f'{v:.1f}%'),
            title='Throughput Breakdown por Evolução x Sustentação por Período (%)',
            labels={'Percentual': '% do Throughput', 'Barra': ''},
            color_discrete_map=delivery_color_map,
            category_orders={'CategoriaEntrega': ['Evolução', 'Sustentação'], 'Barra': period_order[::-1]},
            template='plotly_white',
            height=max(320, 90 + 55 * max(1, len(period_order))),
        )
        fig_type_breakdown.update_layout(
            barmode='stack',
            xaxis=dict(range=[0, 100], ticksuffix='%'),
            yaxis=dict(showticklabels=True, title=''),
            legend_title_text='Categoria de Entrega',
            margin=dict(l=60, r=40, t=70, b=50),
        )
        fig_type_breakdown.update_traces(
            textposition='inside',
            insidetextanchor='middle',
            hovertemplate='Categoria: %{fullData.name}<br>% Throughput: %{x:.1f}%<extra></extra>',
        )

        tp_done['ClassificacaoUrgencia'] = tp_done.apply(classify_urgency_label, axis=1)
        urgency_breakdown = build_throughput_series(
            tp_done,
            'ClassificacaoUrgencia',
            'Throughput por Classificação de Urgência'
        )
        urgency_order = urgency_breakdown['ClassificacaoUrgencia'].tolist()
        urgency_color_map = {
            'Highest': '#E45756',
            'Alta': '#F58518',
            'Data Fixa': '#F28E2B',
            'Padrão': '#4C78A8',
            'Média': '#72B7B2',
            'Baixa': '#54A24B',
            'Intangível': '#B279A2',
            'Não classificado': '#9D9D9D',
        }
        fig_urgency_breakdown = px.bar(
            urgency_breakdown,
            x='Percentual',
            y='Barra',
            color='ClassificacaoUrgencia',
            orientation='h',
            text=urgency_breakdown['Percentual'].map(lambda v: f'{v:.1f}%'),
            title='Throughput Breakdown por Classificação de Urgência (%)',
            labels={'Percentual': '% do Throughput', 'Barra': ''},
            color_discrete_map=urgency_color_map,
            category_orders={'ClassificacaoUrgencia': urgency_order},
            template='plotly_white',
            height=320,
        )
        fig_urgency_breakdown.update_layout(
            barmode='stack',
            xaxis=dict(range=[0, 100], ticksuffix='%'),
            yaxis=dict(showticklabels=False),
            legend_title_text='Classificação de Urgência',
            margin=dict(l=60, r=40, t=70, b=50),
        )
        fig_urgency_breakdown.update_traces(
            textposition='inside',
            insidetextanchor='middle',
            hovertemplate='Urgência: %{fullData.name}<br>% Throughput: %{x:.1f}%<extra></extra>',
        )

        fig_tp_by_person_type = None
        desired_type_order = [TYPE_ISSUES, TYPE_SUPPORT, TYPE_DEV, TYPE_OTHER]
        if 'Responsavel' in tp_done.columns:
            tp_person = tp_done.copy()
            tp_person['Responsavel'] = tp_person['Responsavel'].fillna('Não atribuído').astype(str).str.strip()
            tp_person.loc[tp_person['Responsavel'].eq(''), 'Responsavel'] = 'Não atribuído'
            tp_person['TipoDemanda'] = tp_person.get('TipoDemanda', pd.Series(TYPE_OTHER, index=tp_person.index)).fillna(TYPE_OTHER)

            tp_person_breakdown = (
                tp_person.groupby(['Responsavel', 'TipoDemanda'])
                .size()
                .reset_index(name='Throughput')
            )
            if not tp_person_breakdown.empty:
                tp_person_totals = (
                    tp_person_breakdown.groupby('Responsavel', as_index=False)['Throughput']
                    .sum()
                    .rename(columns={'Throughput': 'ThroughputTotal'})
                    .sort_values(['ThroughputTotal', 'Responsavel'], ascending=[False, True])
                )
                top_people = tp_person_totals.head(20)['Responsavel'].tolist()
                tp_person_breakdown = tp_person_breakdown[tp_person_breakdown['Responsavel'].isin(top_people)].copy()
                tp_person_breakdown['Responsavel'] = pd.Categorical(
                    tp_person_breakdown['Responsavel'],
                    categories=top_people[::-1],
                    ordered=True,
                )
                fig_tp_by_person_type = px.bar(
                    tp_person_breakdown,
                    x='Throughput',
                    y='Responsavel',
                    color='TipoDemanda',
                    orientation='h',
                    barmode='stack',
                    title='Vazão por Pessoa (Top 20) dividida por Tipo de Demanda',
                    labels={'Throughput': 'Itens concluídos', 'Responsavel': 'Responsável', 'TipoDemanda': 'Tipo de Demanda'},
                    color_discrete_map=color_map,
                    template='plotly_white',
                    category_orders={'TipoDemanda': desired_type_order},
                    height=max(420, min(900, 28 * max(1, len(top_people)) + 180)),
                )
                fig_tp_by_person_type.update_layout(
                    legend_title_text='Tipo de Demanda',
                    margin=dict(l=120, r=40, t=70, b=50),
                )
                fig_tp_by_person_type.update_traces(
                    texttemplate='%{x}',
                    textposition='inside',
                    hovertemplate='Responsável: %{y}<br>Tipo: %{fullData.name}<br>Throughput: %{x}<extra></extra>',
                )

        type_table = delivery_breakdown.copy().rename(columns={'CategoriaEntrega': 'Categoria', 'Periodo': 'Período'})
        type_table['Percentual'] = type_table['Percentual'].map(lambda v: f'{v:.1f}%')
        urgency_table = urgency_breakdown.copy()
        urgency_table['Percentual'] = urgency_table['Percentual'].map(lambda v: f'{v:.1f}%')
        throughput_breakdown_monthly = build_monthly_product_throughput_breakdown(tp_done, end_date_ts.year)
        throughput_breakdown_monthly_columns = [
            {'name': ['PRODUTO', 'TIPO'], 'id': 'TIPO'}
        ]
        for product_key in THROUGHPUT_BREAKDOWN_PRODUCT_ORDER:
            product_label = THROUGHPUT_BREAKDOWN_PRODUCT_LABELS[product_key]
            throughput_breakdown_monthly_columns.extend([
                {'name': [product_label, '% Evolução'], 'id': f'{product_label} % Evolução'},
                {'name': [product_label, '%Sustentação'], 'id': f'{product_label} % Sustentação'},
            ])
        throughput_breakdown_original_type_monthly, jira_original_type_order = build_monthly_product_original_type_breakdown(tp_done, end_date_ts.year)
        throughput_breakdown_original_type_columns = [
            {'name': ['PRODUTO', 'TIPO'], 'id': 'TIPO'}
        ]
        for product_key in THROUGHPUT_BREAKDOWN_PRODUCT_ORDER:
            product_label = THROUGHPUT_BREAKDOWN_PRODUCT_LABELS[product_key]
            for jira_type in jira_original_type_order:
                throughput_breakdown_original_type_columns.append(
                    {'name': [product_label, jira_type], 'id': f'{product_label} | {jira_type}'}
                )

        throughput_avg = tp_weekly['Throughput'].mean() if not tp_weekly.empty else 0.0
        tp_cancelled = pd.DataFrame(columns=df.columns)
        tp_cancelled_weekly = pd.DataFrame(columns=['Semana', 'Cancelados'])
        cancelled_avg = 0.0
        cancelled_total = 0
        cancelled_weeks = 0
        if 'DataCancelled' in df.columns:
            tp_cancelled = df.dropna(subset=['DataCancelled']).copy()
            cancelled_total = len(tp_cancelled)
            if not tp_cancelled.empty:
                tp_cancelled['Semana'] = weekly_bucket_start(tp_cancelled['DataCancelled'])
                tp_cancelled_weekly = (
                    tp_cancelled.groupby('Semana')
                    .size()
                    .reset_index(name='Cancelados')
                    .sort_values('Semana')
                )
                cancelled_avg = tp_cancelled_weekly['Cancelados'].mean() if not tp_cancelled_weekly.empty else 0.0
                cancelled_weeks = tp_cancelled_weekly['Semana'].nunique()
        return html.Div([
            html.H3("Throughput Consolidado", style={'textAlign': 'center'}),
            html.Div([
                create_kpi_card('Throughput Total', f"{len(tp_done)}", class_name='two columns'),
                create_kpi_card('Cancelados (Período)', f"{cancelled_total}", class_name='two columns'),
                create_kpi_card('Média Semanal TP', f"{throughput_avg:.1f}", class_name='two columns'),
                create_kpi_card('Média Semanal Cancel.', f"{cancelled_avg:.1f}", class_name='two columns'),
                create_kpi_card('Semanas com Entrega', f"{tp_weekly['Semana'].nunique()}", class_name='two columns'),
                create_kpi_card('Semanas c/ Cancel.', f"{cancelled_weeks}", class_name='two columns'),
            ], className='row'),
            dcc.Graph(figure=fig_tp_weekly),
            html.H4(
                f"Consolidado Mensal por Produto ({int(end_date_ts.year)})",
                style={'textAlign': 'center', 'marginTop': '18px'}
            ),
            dash_table.DataTable(
                columns=throughput_breakdown_monthly_columns,
                data=throughput_breakdown_monthly.to_dict('records'),
                merge_duplicate_headers=True,
                style_cell={'textAlign': 'center', 'padding': '6px', 'minWidth': '110px', 'width': '110px', 'maxWidth': '110px'},
                style_cell_conditional=[{'if': {'column_id': 'TIPO'}, 'minWidth': '90px', 'width': '90px', 'maxWidth': '90px', 'fontWeight': '600'}],
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            ),
            html.H4(
                f"Consolidado Mensal por Produto e Tipo Original Jira ({int(end_date_ts.year)})",
                style={'textAlign': 'center', 'marginTop': '18px'}
            ),
            dash_table.DataTable(
                columns=throughput_breakdown_original_type_columns,
                data=throughput_breakdown_original_type_monthly.to_dict('records'),
                merge_duplicate_headers=True,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'center', 'padding': '6px', 'minWidth': '120px', 'width': '120px', 'maxWidth': '120px'},
                style_cell_conditional=[{'if': {'column_id': 'TIPO'}, 'minWidth': '90px', 'width': '90px', 'maxWidth': '90px', 'fontWeight': '600'}],
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            ),
            html.H4("Custo Médio da Demanda", style={'textAlign': 'center', 'marginTop': '16px'}),
            throughput_cost_summary,
            (dcc.Graph(figure=fig_tp_cost_avg) if throughput_cost_data.get('available') else html.Div()),
            html.H4("Vazão por Pessoa", style={'textAlign': 'center', 'marginTop': '10px'}),
            (dcc.Graph(figure=fig_tp_by_person_type) if fig_tp_by_person_type is not None else html.Div('Dados de responsável não disponíveis para o gráfico de vazão por pessoa.', style={'textAlign': 'center', 'color': '#666', 'marginBottom': '12px'})),
            html.H4("Breakdown por Evolução x Sustentação por Período", style={'textAlign': 'center', 'marginTop': '10px'}),
            dcc.Graph(figure=fig_type_breakdown),
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in type_table.columns],
                data=type_table.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            ),
            html.H4("Breakdown por Classificação de Urgência", style={'textAlign': 'center', 'marginTop': '20px'}),
            dcc.Graph(figure=fig_urgency_breakdown),
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in urgency_table.columns],
                data=urgency_table.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            ),
        ])

    if tab == 'tab-eficiencia':
        if df.empty:
            return html.Div('Sem dados para exibir para o período e filtros selecionados.')

        # --- 1. Calcular colunas adicionais ---
        df_eff = df.copy()

        # Fallback de execução para itens sem DataInProgress:
        # usa DataBacklog como proxy para manter a análise de eficiência.
        if 'DataBacklog' in df_eff.columns:
            effective_start = df_eff.get('DataInProgress', pd.Series(pd.NaT, index=df_eff.index)).fillna(df_eff['DataBacklog'])
        else:
            effective_start = df_eff.get('DataInProgress', pd.Series(pd.NaT, index=df_eff.index))

        if 'TempoBacklog_Dias' in df_eff.columns:
            missing_backlog = df_eff['TempoBacklog_Dias'].isna()
            backlog_fallback = (effective_start - df_eff.get('DataBacklog', pd.Series(pd.NaT, index=df_eff.index))).dt.days
            df_eff.loc[missing_backlog, 'TempoBacklog_Dias'] = backlog_fallback.loc[missing_backlog]

        if 'TempoExecucao_Dias' in df_eff.columns and 'DataDone' in df_eff.columns:
            missing_exec = df_eff['TempoExecucao_Dias'].isna()
            exec_fallback = (df_eff['DataDone'] - effective_start).dt.days
            df_eff.loc[missing_exec, 'TempoExecucao_Dias'] = exec_fallback.loc[missing_exec]

        flow_base = df.copy()

        start_eff_ts = pd.to_datetime(start_date)
        end_eff_ts = pd.to_datetime(end_date)
        weeks_eff = pd.date_range(start=start_eff_ts, end=end_eff_ts + pd.Timedelta(days=7), freq=WEEK_DATE_RANGE_FREQ)
        weekly_eff_map = {}
        weekly_eff_rows = []
        for i in range(len(weeks_eff) - 1):
            week_start = weeks_eff[i]
            week_end = weeks_eff[i + 1]
            arrivals_w = len(flow_base[
                (flow_base['DataInProgress'] >= week_start) &
                (flow_base['DataInProgress'] < week_end)
            ])
            throughput_w = len(flow_base[
                (flow_base['DataDone'] >= week_start) &
                (flow_base['DataDone'] < week_end)
            ])
            _, efficiency_w = calculate_flow_efficiency(arrivals_w, throughput_w)
            weekly_eff_map[pd.Timestamp(week_start).normalize()] = efficiency_w
            weekly_eff_rows.append({
                'SemanaReferencia': pd.Timestamp(week_start).normalize(),
                'Chegadas': arrivals_w,
                'Throughput': throughput_w,
                'Eficiencia': efficiency_w,
            })

        df_eff_weekly = pd.DataFrame(weekly_eff_rows)
        if not df_eff_weekly.empty:
            df_eff_weekly['SemanaLabel'] = df_eff_weekly['SemanaReferencia'].dt.strftime('%d/%m/%Y')

        if 'DataDone' in df_eff.columns:
            df_eff['SemanaReferencia'] = weekly_bucket_start(df_eff['DataDone'].fillna(effective_start))
        else:
            df_eff['SemanaReferencia'] = weekly_bucket_start(effective_start)
        df_eff['SemanaReferencia'] = pd.to_datetime(df_eff['SemanaReferencia']).dt.normalize()
        df_eff['Eficiencia'] = df_eff['SemanaReferencia'].map(weekly_eff_map)
        df_eff['EficienciaAjustada'] = df_eff['Eficiencia']
        
        time_cols = ['TempoBacklog_Dias', 'TempoExecucao_Dias', 'TempoBloqueioDias', 'TempoEsperaIntermediariaDias']
        for col in time_cols:
            if col not in df_eff.columns: df_eff[col] = 0
            else: df_eff[col] = df_eff[col].fillna(0)

        if 'LeadTime_Dias' in df_eff.columns:
            df_eff['Outros Tempos (dias)'] = df_eff['LeadTime_Dias'] - df_eff[time_cols].sum(axis=1)
            df_eff['Outros Tempos (dias)'] = df_eff['Outros Tempos (dias)'].clip(lower=0)

        eff_cols = ['Eficiencia', 'EficienciaAjustada']
        for col in eff_cols:
            if col not in df_eff.columns:
                df_eff[col] = np.nan

        df_eff['Diferença Eficiência'] = df_eff['EficienciaAjustada'] - df_eff['Eficiencia']

        # --- 2. Criar Gráficos ---
        breakdown_components = {
            'Backlog': df_eff['TempoBacklog_Dias'].mean(),
            'Execução': df_eff['TempoExecucao_Dias'].mean(),
            'Bloqueio': df_eff['TempoBloqueioDias'].mean(),
            'Espera Intermediária': df_eff['TempoEsperaIntermediariaDias'].mean(),
            'Outros': df_eff.get('Outros Tempos (dias)', pd.Series(0)).mean()
        }
        df_breakdown = pd.DataFrame(breakdown_components.items(), columns=['Componente', 'Dias'])
        df_breakdown['Dias'] = pd.to_numeric(df_breakdown['Dias'], errors='coerce').fillna(0)
        df_breakdown = df_breakdown[df_breakdown['Dias'] > 0].sort_values('Dias', ascending=True)
        total_breakdown_days = float(df_breakdown['Dias'].sum())
        df_breakdown['Participacao'] = (
            df_breakdown['Dias'] / total_breakdown_days if total_breakdown_days > 0 else 0.0
        )
        df_breakdown['ParticipacaoLabel'] = df_breakdown['Participacao'].map(lambda x: f'{x:.0%}')
        df_breakdown['DiasLabel'] = df_breakdown['Dias'].map(lambda x: f'{x:.1f} d')
        breakdown_color_map = {
            'Backlog': '#5b6cff',
            'Execução': '#f25535',
            'Bloqueio': '#38c786',
            'Espera Intermediária': '#a14cf0',
            'Outros': '#f3a15d',
        }
        bar_colors = [breakdown_color_map.get(comp, '#9aa5b1') for comp in df_breakdown['Componente']]
        fig_breakdown = make_subplots(
            rows=1,
            cols=2,
            specs=[[{"type": "xy"}, {"type": "domain"}]],
            column_widths=[0.68, 0.32],
            subplot_titles=('Dias médios por componente', 'Participação no lead time'),
        )
        fig_breakdown.add_trace(
            go.Bar(
                x=df_breakdown['Dias'],
                y=df_breakdown['Componente'],
                orientation='h',
                marker_color=bar_colors,
                text=[f'{days} ({share})' for days, share in zip(df_breakdown['DiasLabel'], df_breakdown['ParticipacaoLabel'])],
                textposition='outside',
                customdata=np.stack(
                    [df_breakdown['DiasLabel'].to_numpy(), df_breakdown['ParticipacaoLabel'].to_numpy()],
                    axis=-1,
                ),
                hovertemplate='%{y}<br>Dias médios: %{customdata[0]}<br>Participação: %{customdata[1]}<extra></extra>',
                showlegend=False,
                name='Dias médios',
            ),
            row=1,
            col=1,
        )
        fig_breakdown.add_trace(
            go.Pie(
                labels=df_breakdown['Componente'],
                values=df_breakdown['Dias'],
                hole=0.55,
                marker=dict(colors=bar_colors),
                textinfo='label+percent',
                hovertemplate='%{label}<br>Dias médios: %{value:.1f}<br>Participação: %{percent}<extra></extra>',
                sort=False,
                showlegend=False,
                name='Participação',
            ),
            row=1,
            col=2,
        )
        fig_breakdown.update_xaxes(title_text='Dias médios', row=1, col=1, rangemode='tozero')
        fig_breakdown.update_yaxes(title_text=None, row=1, col=1)
        fig_breakdown.update_layout(
            title='Breakdown do Lead Time Médio por Componente',
            height=470,
            template='plotly_white',
            margin=dict(l=40, r=40, t=80, b=40),
        )
        if total_breakdown_days > 0:
            fig_breakdown.add_annotation(
                x=0.84,
                y=0.5,
                xref='paper',
                yref='paper',
                text=f'Lead time médio<br><b>{total_breakdown_days:.1f} dias</b>',
                showarrow=False,
                font=dict(size=14),
            )

        fig_scatter_eff = make_subplots(specs=[[{"secondary_y": True}]])
        if not df_eff_weekly.empty:
            fig_scatter_eff.add_trace(
                go.Bar(
                    x=df_eff_weekly['SemanaReferencia'],
                    y=df_eff_weekly['Chegadas'],
                    name='Chegadas',
                    marker_color='#9aa5b1',
                    opacity=0.45,
                    hovertemplate='Semana %{x|%d/%m/%Y}<br>Chegadas: %{y}<extra></extra>',
                ),
                secondary_y=False,
            )
            fig_scatter_eff.add_trace(
                go.Bar(
                    x=df_eff_weekly['SemanaReferencia'],
                    y=df_eff_weekly['Throughput'],
                    name='Throughput',
                    marker_color='#2f6bff',
                    opacity=0.7,
                    hovertemplate='Semana %{x|%d/%m/%Y}<br>Throughput: %{y}<extra></extra>',
                ),
                secondary_y=False,
            )
            fig_scatter_eff.add_trace(
                go.Scatter(
                    x=df_eff_weekly['SemanaReferencia'],
                    y=df_eff_weekly['Eficiencia'],
                    name='Eficiência de Fluxo (1-ρ)',
                    mode='lines+markers',
                    line=dict(color='#d94841', width=3),
                    marker=dict(size=8),
                    hovertemplate=(
                        'Semana %{x|%d/%m/%Y}'
                        '<br>Eficiência: %{y:.2f}'
                        '<br>Chegadas: %{customdata[0]}'
                        '<br>Throughput: %{customdata[1]}<extra></extra>'
                    ),
                    customdata=df_eff_weekly[['Chegadas', 'Throughput']].to_numpy(),
                ),
                secondary_y=True,
            )
        fig_scatter_eff.update_layout(
            title='Eficiência de Fluxo (1-ρ) por Semana de Referência',
            height=550,
            template='plotly_white',
            barmode='group',
            hovermode='x unified',
            legend_title_text='Métrica',
        )
        fig_scatter_eff.update_xaxes(title_text='Semana de Referência')
        fig_scatter_eff.update_yaxes(title_text='Itens por semana', secondary_y=False, rangemode='tozero')
        fig_scatter_eff.update_yaxes(
            title_text='Eficiência de Fluxo (1-ρ)',
            secondary_y=True,
            range=[-1, 1],
            tickformat='.0%',
        )
        fig_scatter_eff.add_hline(y=0, line_dash='dash', line_color='grey', secondary_y=True)

        # --- 3. Criar Tabela Detalhada ---
        table_cols = ['ItemID', 'Projeto', 'TipoDemanda', 'SemanaReferencia', 'LeadTime_Dias', 'TempoBacklog_Dias', 'TempoExecucao_Dias', 'TempoBloqueioDias', 'TempoEsperaIntermediariaDias', 'Outros Tempos (dias)', 'Eficiencia']
        available_cols = [c for c in table_cols if c in df_eff.columns]
        detail_table = dash_table.DataTable(id='table-eficiencia-detalhada', columns=[{"name": i, "id": i} for i in available_cols], data=df_eff[available_cols].to_dict('records'), page_size=15, filter_action="native", sort_action="native", style_table={'overflowX': 'auto'}, style_cell={'minWidth': '100px', 'width': '150px', 'maxWidth': '180px', 'textAlign': 'center'})

        return html.Div([
            html.H3("Análise de Eficiência de Fluxo", style={'textAlign': 'center'}),
            dcc.Graph(figure=fig_breakdown),
            dcc.Graph(figure=fig_scatter_eff),
            html.H4("Análise Detalhada por Item", style={'textAlign': 'center', 'marginTop': '40px'}),
            detail_table
        ])

    if tab == 'tab-padroes':
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)

        df_patterns = df.copy()

        if df_patterns.empty:
            return html.Div('Sem dados para detectar padrões no filtro selecionado.')

        checklist_df, diagnosis_df, weekly_review_df = build_weekly_flow_checklist_and_diagnosis(df_patterns, start_ts, end_ts)
        expedite_kpis_data, expedite_table_df, expedite_alerts_df = build_expedite_governance_view(df_patterns, start_ts, end_ts)
        variability_alerts_df, variability_metrics_df = build_variability_alerts_view(df_patterns, start_ts, end_ts)
        details, summary = detect_systemic_patterns(df_patterns, start_ts, end_ts, PATTERN_RULES)
        if details.empty and checklist_df.empty and diagnosis_df.empty:
            return html.Div([
                html.H3('Padrões Sistêmicos', style={'textAlign': 'center'}),
                html.P(
                    'Nenhum padrão ou checklist automatizado disponível com os dados do período/filtros.',
                    style={'textAlign': 'center', 'color': '#555'}
                ),
            ])

        period_days = max(1, (pd.Timestamp(end_ts).normalize() - pd.Timestamp(start_ts).normalize()).days + 1)
        previous_end_ts = pd.Timestamp(start_ts).normalize() - pd.Timedelta(days=1)
        previous_start_ts = previous_end_ts - pd.Timedelta(days=period_days - 1)
        previous_patterns_df = filter_df(
            fato,
            previous_start_ts,
            previous_end_ts,
            projeto,
            tipo,
            classe_servico,
            responsavel,
            criadores=criadores,
            use_creation_date=use_creation_date,
            tipo_original=tipo_original_jira,
        ).copy()
        previous_details, previous_summary = detect_systemic_patterns(
            previous_patterns_df,
            previous_start_ts,
            previous_end_ts,
            PATTERN_RULES,
        )

        criticos = int((details['Severidade'] == 'Crítico').sum()) if 'Severidade' in details.columns else 0
        atencao = int((details['Severidade'] == 'Atenção').sum()) if 'Severidade' in details.columns else 0
        semanas_afetadas = int(details['Semana'].nunique()) if 'Semana' in details.columns else 0
        checklist_criticos = int((checklist_df['Status'] == 'Crítico').sum()) if not checklist_df.empty else 0
        checklist_alertas = int((checklist_df['Status'] == 'Atenção').sum()) if not checklist_df.empty else 0
        diagnosticos = int(len(diagnosis_df)) if not diagnosis_df.empty else 0
        variability_criticos = int((variability_alerts_df['Status'] == 'Crítico').sum()) if not variability_alerts_df.empty else 0
        expedite_status = expedite_kpis_data.get('policy_status', 'Sem base')

        def _safe_nunique(frame, column):
            if frame is None or frame.empty or column not in frame.columns:
                return 0
            return int(frame[column].nunique())

        def _trend_descriptor(current_value, previous_value, lower_is_better=True, tolerance=0.0, fmt='{:+.0f}', suffix=''):
            if pd.isna(current_value) or pd.isna(previous_value):
                return ('Sem base anterior', '#7b8694', 'Sem comparação com o período anterior')
            delta = float(current_value) - float(previous_value)
            if abs(delta) <= tolerance:
                return ('Estável', '#7b8694', f'{fmt.format(delta)}{suffix} vs período anterior')
            moved_up = delta > 0
            improved = (not moved_up) if lower_is_better else moved_up
            label = 'Melhorou' if improved else 'Piorou'
            color = '#2e7d32' if improved else '#c62828'
            return (label, color, f'{fmt.format(delta)}{suffix} vs período anterior')

        def _fmt_int(value):
            return f"{int(value)}" if pd.notna(value) else '—'

        def _build_pattern_kpi_card(title, value, subtitle, trend_tuple, accent_color, featured=False):
            trend_label, trend_color, trend_detail = trend_tuple
            return html.Div([
                html.Div(title, style={
                    'fontSize': '12px',
                    'fontWeight': '700',
                    'letterSpacing': '0.05em',
                    'textTransform': 'uppercase',
                    'color': accent_color,
                    'marginBottom': '10px',
                }),
                html.Div(value, style={
                    'fontSize': '38px' if featured else '32px',
                    'fontWeight': '700',
                    'lineHeight': '1.0',
                    'color': '#10202f',
                    'marginBottom': '8px',
                }),
                html.Div(subtitle, style={
                    'fontSize': '13px',
                    'color': '#52606d',
                    'lineHeight': '1.45',
                    'minHeight': '36px',
                }),
                html.Div([
                    html.Span(trend_label, style={
                        'display': 'inline-block',
                        'fontSize': '11px',
                        'fontWeight': '700',
                        'letterSpacing': '0.04em',
                        'textTransform': 'uppercase',
                        'color': trend_color,
                        'backgroundColor': '#f5f7fa',
                        'border': f'1px solid {trend_color}33',
                        'borderRadius': '999px',
                        'padding': '4px 8px',
                        'marginRight': '8px',
                    }),
                    html.Span(trend_detail, style={'fontSize': '12px', 'color': '#5f6e7b'}),
                ], style={'marginTop': '10px'}),
            ], style={
                'background': 'linear-gradient(180deg, #ffffff 0%, #f8fbff 100%)' if featured else 'white',
                'border': f'1px solid {accent_color}2f' if featured else '1px solid #d9e2ec',
                'borderTop': f'6px solid {accent_color}',
                'borderRadius': '18px',
                'padding': '18px',
                'boxShadow': '0 10px 24px rgba(15, 23, 32, 0.06)' if featured else '0 2px 10px rgba(15, 23, 32, 0.05)',
                'minHeight': '188px' if featured else '172px',
                'height': '100%',
            })

        def _section_shell(kicker, title, subtitle, children, background_color='#ffffff', border_color='#d9e2ec'):
            return html.Div([
                html.Div(kicker, style={
                    'display': 'inline-block',
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'letterSpacing': '0.05em',
                    'textTransform': 'uppercase',
                    'color': '#176ea4',
                    'backgroundColor': 'rgba(255,255,255,0.72)',
                    'border': '1px solid rgba(23, 110, 164, 0.18)',
                    'borderRadius': '999px',
                    'padding': '5px 10px',
                    'marginBottom': '10px',
                }),
                html.Div(title, style={'fontSize': '24px', 'fontWeight': '700', 'lineHeight': '1.1', 'color': '#10202f', 'marginBottom': '6px'}),
                html.Div(subtitle, style={'fontSize': '13px', 'color': '#4d5c6b', 'lineHeight': '1.55', 'marginBottom': '16px'}),
                children,
            ], style={
                'backgroundColor': background_color,
                'border': f'1px solid {border_color}',
                'borderRadius': '20px',
                'padding': '18px',
                'boxShadow': '0 6px 18px rgba(15, 23, 32, 0.04)',
                'marginBottom': '18px',
            })

        def _chart_card(title, subtitle, figure):
            return html.Div([
                html.Div(title, style={'fontSize': '16px', 'fontWeight': '700', 'color': '#17324d', 'marginBottom': '4px'}),
                html.Div(subtitle, style={'fontSize': '12px', 'color': '#5f6e7b', 'lineHeight': '1.45', 'marginBottom': '8px'}),
                dcc.Graph(figure=figure),
            ], style={
                'flex': '1 1 460px',
                'minWidth': '360px',
                'backgroundColor': 'white',
                'border': '1px solid #d9e2ec',
                'borderRadius': '18px',
                'padding': '14px',
                'boxShadow': '0 2px 10px rgba(15, 23, 32, 0.05)',
            })

        def _table_block(title, subtitle, component):
            return html.Div([
                html.Div(title, style={'fontSize': '16px', 'fontWeight': '700', 'color': '#17324d', 'marginBottom': '4px'}),
                html.Div(subtitle, style={'fontSize': '12px', 'color': '#5f6e7b', 'lineHeight': '1.45', 'marginBottom': '10px'}),
                component,
            ], style={
                'backgroundColor': 'white',
                'border': '1px solid #d9e2ec',
                'borderRadius': '18px',
                'padding': '14px',
                'boxShadow': '0 2px 10px rgba(15, 23, 32, 0.05)',
                'marginBottom': '14px',
            })

        affected_teams = _safe_nunique(details, 'Projeto')
        affected_teams_prev = _safe_nunique(previous_details, 'Projeto')
        critical_teams = _safe_nunique(details[details['Severidade'] == 'Crítico'], 'Projeto') if not details.empty else 0
        critical_teams_prev = _safe_nunique(previous_details[previous_details['Severidade'] == 'Crítico'], 'Projeto') if not previous_details.empty else 0
        total_occurrences = int(len(details))
        total_occurrences_prev = int(len(previous_details))
        critical_occurrences_prev = int((previous_details['Severidade'] == 'Crítico').sum()) if not previous_details.empty and 'Severidade' in previous_details.columns else 0
        weeks_with_signal_prev = int(previous_details['Semana'].nunique()) if not previous_details.empty and 'Semana' in previous_details.columns else 0

        pattern_totals = details.groupby('Padrão').size().sort_values(ascending=False) if not details.empty else pd.Series(dtype='int64')
        previous_pattern_totals = previous_details.groupby('Padrão').size().sort_values(ascending=False) if not previous_details.empty else pd.Series(dtype='int64')
        pattern_critical_totals = (
            details[details['Severidade'] == 'Crítico'].groupby('Padrão').size()
            if not details.empty else pd.Series(dtype='int64')
        )
        top_patterns = pattern_totals.head(5).index.tolist()
        top_pattern_name = top_patterns[0] if top_patterns else 'Sem padrão dominante'
        top_pattern_count = int(pattern_totals.iloc[0]) if len(pattern_totals) else 0

        latest_week_label = 'Sem base'
        latest_week_details = pd.DataFrame(columns=details.columns)
        if not details.empty and 'Semana' in details.columns:
            details_for_week = details.copy()
            details_for_week['Semana'] = pd.to_datetime(details_for_week['Semana'], errors='coerce')
            latest_week = details_for_week['Semana'].max()
            if pd.notna(latest_week):
                latest_week_label = pd.Timestamp(latest_week).strftime('%d/%m/%Y')
                latest_week_details = details_for_week[details_for_week['Semana'] == latest_week].copy()

        _sev_order = {'Crítico': 0, 'Atenção': 1}
        team_alert_cards = []
        _atencao_teams = []
        if not details.empty:
            team_list_build = []
            for _proj, _grp in details.groupby('Projeto'):
                _pat_summary = (
                    _grp.groupby(['Padrão', 'Severidade'])
                    .size()
                    .reset_index(name='Semanas')
                    .sort_values('Semanas', ascending=False)
                )
                _top_sev = 'Crítico' if (_grp['Severidade'] == 'Crítico').any() else 'Atenção'
                _total_cur = len(_grp)
                _total_prev = (
                    len(previous_details[previous_details['Projeto'] == _proj])
                    if not previous_details.empty and 'Projeto' in previous_details.columns
                    else 0
                )
                team_list_build.append((_sev_order.get(_top_sev, 1), -_total_cur, _proj, _pat_summary, _top_sev, _total_cur, _total_prev))
            team_list_build.sort()
            _atencao_teams = [t for t in team_list_build if t[4] == 'Atenção']

            for _, _, _proj, _pat_summary, _top_sev, _total_cur, _total_prev in team_list_build:
                if _top_sev != 'Crítico':
                    continue
                _accent = '#c62828' if _top_sev == 'Crítico' else '#c77d12'
                _delta = _total_cur - _total_prev
                if _delta > 0:
                    _trend_txt = f'\u2191 +{_delta} ocorrência(s) vs período anterior'
                    _trend_color = '#c62828'
                elif _delta < 0:
                    _trend_txt = f'\u2193 {_delta} ocorrência(s) vs período anterior'
                    _trend_color = '#2e7d32'
                else:
                    _trend_txt = 'Estável vs período anterior'
                    _trend_color = '#7b8694'

                _pattern_rows = []
                for _, _prow in _pat_summary.iterrows():
                    _sev_color = '#c62828' if _prow['Severidade'] == 'Crítico' else '#c77d12'
                    _sev_bg = '#fdecea' if _prow['Severidade'] == 'Crítico' else '#fff8e1'
                    _pattern_rows.append(
                        html.Div([
                            html.Span(_prow['Severidade'], style={
                                'fontSize': '10px', 'fontWeight': '700', 'color': _sev_color,
                                'backgroundColor': _sev_bg,
                                'border': f'1px solid {_sev_color}44',
                                'borderRadius': '999px', 'padding': '2px 6px', 'marginRight': '6px',
                            }),
                            html.Span(_prow['Padrão'], style={'fontSize': '12px', 'color': '#243b53'}),
                            html.Span(
                                f" \u2014 {int(_prow['Semanas'])} sem.",
                                style={'fontSize': '11px', 'color': '#7b8694'},
                            ),
                        ], style={'marginBottom': '5px'})
                    )

                _top_pattern = _pat_summary.iloc[0]['Padrão'] if not _pat_summary.empty else ''
                _action_text = PATTERN_ACTIONS.get(_top_pattern, 'Investigar detalhes na seção Base Analítica abaixo.')

                team_alert_cards.append(html.Div([
                    html.Div([
                        html.Div(_proj, style={
                            'fontSize': '15px', 'fontWeight': '700', 'color': '#10202f', 'flex': '1',
                        }),
                        html.Span(_top_sev, style={
                            'fontSize': '10px', 'fontWeight': '700', 'color': _accent,
                            'backgroundColor': '#fdecea' if _top_sev == 'Crítico' else '#fff8e1',
                            'border': f'1px solid {_accent}44',
                            'borderRadius': '999px', 'padding': '3px 8px',
                        }),
                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
                    html.Div(_pattern_rows, style={'marginBottom': '10px'}),
                    html.Div(
                        _trend_txt,
                        style={'fontSize': '11px', 'color': _trend_color, 'fontWeight': '600', 'marginBottom': '10px'},
                    ),
                    html.Div([
                        html.Div('Ação sugerida', style={
                            'fontSize': '10px', 'fontWeight': '700', 'letterSpacing': '0.04em',
                            'textTransform': 'uppercase', 'color': '#516170', 'marginBottom': '4px',
                        }),
                        html.Div(_action_text, style={
                            'fontSize': '12px', 'color': '#243b53', 'lineHeight': '1.55',
                        }),
                    ], style={
                        'backgroundColor': '#f8fbff',
                        'borderLeft': f'3px solid {_accent}',
                        'borderRadius': '0 8px 8px 0',
                        'padding': '8px 10px',
                    }),
                ], style={
                    'backgroundColor': 'white',
                    'border': '1px solid #d9e2ec',
                    'borderTop': f'4px solid {_accent}',
                    'borderRadius': '14px',
                    'padding': '14px',
                    'boxShadow': '0 2px 8px rgba(15, 23, 32, 0.05)',
                }))

        if team_alert_cards:
            team_alert_grid = html.Div(
                team_alert_cards,
                style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fit, minmax(300px, 1fr))',
                    'gap': '12px',
                },
            )
        else:
            _atencao_count = len(_atencao_teams) if not details.empty else 0
            _atencao_names = ', '.join(t[2] for t in _atencao_teams) if _atencao_teams else '—'
            team_alert_grid = html.Div([
                html.Div('\u2713 Nenhum time em estado crítico no período.', style={
                    'fontSize': '15px', 'fontWeight': '700', 'color': '#2e7d32', 'marginBottom': '8px',
                }),
                html.Div(
                    (
                        f'{_atencao_count} time(s) com sinais de atenção: {_atencao_names}. '
                        'Avalie os detalhes na seção Base Analítica abaixo — tabelas de detalhamento semanal e diagnóstico prescritivo.'
                    ) if _atencao_count > 0 else 'Nenhum padrão sistêmico detectado no período.',
                    style={'fontSize': '13px', 'color': '#4d5c6b', 'lineHeight': '1.6'},
                ),
            ], style={
                'backgroundColor': '#eef8f1',
                'border': '1px solid #a8d5b5',
                'borderRadius': '14px',
                'padding': '16px 20px',
            })

        def _operational_status_badge(label, tone):
            palette = {
                'danger': ('#fff1f0', '#c62828'),
                'warning': ('#fff7e8', '#c77d12'),
                'success': ('#eef8f1', '#2e7d32'),
                'info': ('#eef6ff', '#176ea4'),
                'neutral': ('#f3f6f9', '#607080'),
            }
            bg, color = palette.get(tone, palette['neutral'])
            return html.Span(label, style={
                'display': 'inline-block',
                'fontSize': '10px',
                'fontWeight': '700',
                'letterSpacing': '0.05em',
                'textTransform': 'uppercase',
                'color': color,
                'backgroundColor': bg,
                'border': f'1px solid {color}22',
                'borderRadius': '999px',
                'padding': '4px 8px',
                'marginBottom': '10px',
            })

        def _operational_stat_card(title, value, subtitle='', tone='neutral'):
            tone_map = {
                'danger': '#c62828',
                'warning': '#c77d12',
                'success': '#2e7d32',
                'info': '#176ea4',
                'neutral': '#7b8694',
            }
            accent = tone_map.get(tone, '#7b8694')
            return html.Div([
                html.Div(title, style={
                    'fontSize': '12px',
                    'fontWeight': '700',
                    'color': '#243b53',
                    'lineHeight': '1.35',
                    'marginBottom': '10px',
                    'minHeight': '34px',
                }),
                html.Div(value, style={
                    'fontSize': '36px',
                    'fontWeight': '700',
                    'lineHeight': '1.0',
                    'color': '#10202f',
                    'marginBottom': '8px',
                }),
                html.Div(subtitle, style={
                    'fontSize': '12px',
                    'color': '#5f6e7b',
                    'lineHeight': '1.45',
                    'minHeight': '34px',
                }),
            ], style={
                'backgroundColor': 'white',
                'border': '1px solid #d9e2ec',
                'borderTop': f'5px solid {accent}',
                'borderRadius': '16px',
                'padding': '14px 16px',
                'boxShadow': '0 2px 8px rgba(15, 23, 32, 0.05)',
                'minHeight': '154px',
                'height': '100%',
            })

        def _operational_metric_group(kicker, title, description, cards, tone='neutral'):
            return html.Div([
                _operational_status_badge(kicker, tone),
                html.Div(title, style={
                    'fontSize': '18px',
                    'fontWeight': '700',
                    'color': '#17324d',
                    'marginBottom': '6px',
                }),
                html.Div(description, style={
                    'fontSize': '12px',
                    'color': '#5f6e7b',
                    'lineHeight': '1.5',
                    'marginBottom': '12px',
                }),
                html.Div(cards, style={
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fit, minmax(180px, 1fr))',
                    'gap': '12px',
                }),
            ], style={
                'flex': '1 1 320px',
                'minWidth': '280px',
                'backgroundColor': '#f8fbff' if tone == 'info' else '#fffaf2' if tone == 'warning' else '#ffffff',
                'border': '1px solid #d9e2ec',
                'borderRadius': '18px',
                'padding': '16px',
                'boxShadow': '0 4px 14px rgba(15, 23, 32, 0.04)',
            })

        lead_time_cv_value = (
            f"{float(variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Lead Time', 'CV'].iloc[0]):.3f}"
            if not variability_metrics_df.empty and
            not variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Lead Time', 'CV'].empty and
            pd.notna(variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Lead Time', 'CV'].iloc[0])
            else '—'
        )
        cycle_time_cv_value = (
            f"{float(variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Cycle Time', 'CV'].iloc[0]):.3f}"
            if not variability_metrics_df.empty and
            not variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Cycle Time', 'CV'].empty and
            pd.notna(variability_metrics_df.loc[variability_metrics_df['Métrica'] == 'Cycle Time', 'CV'].iloc[0])
            else '—'
        )

        operational_kpi_groups = html.Div([
            _operational_metric_group(
                'Checklist',
                'Revisão semanal automatizada',
                'Leitura rápida da última semana para confirmar estabilidade operacional e volume de diagnósticos acionáveis.',
                [
                    _operational_stat_card('Checklist Crítico', str(checklist_criticos), 'itens fora da banda segura', 'danger' if checklist_criticos > 0 else 'success'),
                    _operational_stat_card('Checklist Atenção', str(checklist_alertas), 'itens com desvio moderado', 'warning' if checklist_alertas > 0 else 'success'),
                    _operational_stat_card('Diagnósticos Prescritivos', str(diagnosticos), 'combinações com ação recomendada', 'info'),
                ],
                tone='info',
            ),
            _operational_metric_group(
                'Fast Track',
                'Governança Highest',
                'Mede se o fluxo expedite continua exceção ou se está contaminando entrada, saída e estoque em aberto.',
                [
                    _operational_stat_card('Highest nas Entradas', f"{expedite_kpis_data['arrivals_pct']:.1f}%" if pd.notna(expedite_kpis_data.get('arrivals_pct')) else '—', 'participação na entrada', 'warning'),
                    _operational_stat_card('Highest no Throughput', f"{expedite_kpis_data['throughput_pct']:.1f}%" if pd.notna(expedite_kpis_data.get('throughput_pct')) else '—', 'participação na saída', 'warning'),
                    _operational_stat_card('Highest em Aberto', f"{int(expedite_kpis_data.get('open_items', 0))}", 'itens expedite ainda abertos', 'danger' if int(expedite_kpis_data.get('open_items', 0)) > 0 else 'success'),
                    _operational_stat_card('Política Highest', expedite_status, 'status consolidado da política', 'success' if normalize_text(expedite_status) == 'ok' else 'warning'),
                ],
                tone='warning',
            ),
            _operational_metric_group(
                'Variabilidade',
                'Dispersão operacional',
                'Semáforos de estabilidade da operação com foco em volume de alertas e dispersão de lead time e cycle time.',
                [
                    _operational_stat_card('Alertas Críticos', str(variability_criticos), 'métricas em estado crítico', 'danger' if variability_criticos > 0 else 'success'),
                    _operational_stat_card('CV Lead Time', lead_time_cv_value, 'coeficiente de variação', 'warning'),
                    _operational_stat_card('CV Cycle Time', cycle_time_cv_value, 'coeficiente de variação', 'warning'),
                ],
                tone='neutral',
            ),
        ], style={
            'display': 'flex',
            'flexWrap': 'wrap',
            'gap': '14px',
        })

        fig_summary = go.Figure()
        if not summary.empty:
            fig_summary = px.bar(
                summary,
                x='Padrão',
                y='Ocorrências',
                color='Severidade',
                barmode='group',
                title='Padrões Detectados por Severidade',
                color_discrete_map={'Crítico': '#c62828', 'Atenção': '#f9a825'}
            )
            fig_summary.update_layout(height=500, xaxis_tickangle=-22, margin=dict(b=120))

        fig_expedite = go.Figure()
        if not expedite_table_df.empty:
            plot_df = expedite_table_df.copy().head(10)
            fig_expedite = px.bar(
                plot_df,
                x='Classe de Serviço',
                y='Itens',
                title='Distribuição de throughput por classe de serviço',
                color='Classe de Serviço',
            )
            fig_expedite.update_layout(height=420, xaxis_tickangle=-25, showlegend=False, margin=dict(b=100))

        fig_variability = go.Figure()
        if not variability_metrics_df.empty:
            fig_variability = px.bar(
                variability_metrics_df,
                x='Métrica',
                y='CV',
                color='Status',
                title='Alertas explícitos de variabilidade/dispersão',
                color_discrete_map={'OK': '#2E7D32', 'Atenção': '#EF6C00', 'Crítico': '#C62828', 'Sem base': '#90A4AE'},
            )
            fig_variability.update_layout(height=420, showlegend=True, margin=dict(b=60))

        fig_weekly_review = go.Figure()
        if not weekly_review_df.empty:
            weekly_plot = weekly_review_df.copy()
            weekly_plot['Semana'] = weekly_plot['Semana'].astype(str)
            fig_weekly_review = make_subplots(specs=[[{"secondary_y": True}]])
            fig_weekly_review.add_trace(
                go.Bar(x=weekly_plot['Semana'], y=weekly_plot['Throughput'], name='Throughput', marker_color='#2E7D32'),
                secondary_y=False,
            )
            fig_weekly_review.add_trace(
                go.Scatter(x=weekly_plot['Semana'], y=weekly_plot['WIP'], name='WIP', mode='lines+markers', line=dict(color='#1565C0', width=3)),
                secondary_y=False,
            )
            fig_weekly_review.add_trace(
                go.Scatter(x=weekly_plot['Semana'], y=weekly_plot['CycleTime_P50'], name='Cycle P50', mode='lines+markers', line=dict(color='#EF6C00', width=3)),
                secondary_y=True,
            )
            fig_weekly_review.update_layout(
                title='Resumo Semanal Automatizado: Throughput, WIP e Cycle Time',
                height=520,
                template='plotly_white',
                hovermode='x unified',
                margin=dict(b=90),
            )
            fig_weekly_review.update_xaxes(title_text='Semana', tickangle=-45)
            fig_weekly_review.update_yaxes(title_text='Itens', secondary_y=False)
            fig_weekly_review.update_yaxes(title_text='Cycle Time P50 (dias)', secondary_y=True)

        fig_pattern_timeline = go.Figure()
        fig_pattern_team_timeline = go.Figure()
        if not details.empty and top_patterns:
            details_plot = details.copy()
            details_plot['Semana'] = pd.to_datetime(details_plot['Semana'], errors='coerce')

            _period_weeks = max(1, int((end_ts - start_ts).days / 7))
            _use_monthly = _period_weeks > 10
            if _use_monthly:
                details_plot['Período'] = details_plot['Semana'].dt.to_period('M').dt.to_timestamp()
                _period_label = 'Mês'
                _tick_fmt = '%b/%Y'
                _periods_index = pd.date_range(start=start_ts, end=end_ts, freq='MS')
            else:
                details_plot['Período'] = details_plot['Semana']
                _period_label = 'Semana'
                _tick_fmt = '%d/%m'
                _periods_index = pd.date_range(start=start_ts, end=end_ts, freq=WEEK_DATE_RANGE_FREQ)

            _period_pattern_index = pd.MultiIndex.from_product(
                [_periods_index, top_patterns],
                names=['Período', 'Padrão']
            )

            # Chart 1: stacked bar — volume de ocorrências por período
            weekly_pattern_occurrences = (
                details_plot[details_plot['Padrão'].isin(top_patterns)]
                .groupby(['Período', 'Padrão'])
                .size()
                .rename('Ocorrências')
                .reindex(_period_pattern_index, fill_value=0)
                .reset_index()
            )
            fig_pattern_timeline = px.bar(
                weekly_pattern_occurrences,
                x='Período',
                y='Ocorrências',
                color='Padrão',
                barmode='stack',
            )
            fig_pattern_timeline.update_layout(
                height=400,
                template='plotly_white',
                hovermode='x unified',
                margin=dict(l=36, r=16, t=24, b=48),
                title=None,
                legend=dict(
                    title='Padrão',
                    orientation='h',
                    yanchor='bottom',
                    y=1.06,
                    xanchor='left',
                    x=0,
                    bgcolor='rgba(255,255,255,0.88)',
                    bordercolor='rgba(23, 50, 77, 0.08)',
                    borderwidth=1,
                    font=dict(size=11),
                ),
                font={'family': 'Segoe UI, sans-serif', 'color': '#243b53'},
            )
            fig_pattern_timeline.update_xaxes(
                title_text=_period_label,
                tickformat=_tick_fmt,
                tickangle=-25,
                showgrid=False,
                zeroline=False,
            )
            fig_pattern_timeline.update_yaxes(
                title_text='Ocorrências',
                rangemode='tozero',
                showgrid=True,
                gridcolor='rgba(148,163,184,0.18)',
                zeroline=False,
                dtick=1,
            )

            # Chart 2: heatmap — times únicos afetados por padrão × período
            weekly_pattern_teams = (
                details_plot[details_plot['Padrão'].isin(top_patterns)]
                .groupby(['Período', 'Padrão'])['Projeto']
                .nunique()
                .rename('Times Afetados')
                .reindex(_period_pattern_index, fill_value=0)
                .reset_index()
            )
            _heatmap_pivot = weekly_pattern_teams.pivot(
                index='Padrão', columns='Período', values='Times Afetados'
            ).fillna(0)
            _period_labels_fmt = [pd.Timestamp(c).strftime(_tick_fmt) for c in _heatmap_pivot.columns]
            fig_pattern_team_timeline = go.Figure(go.Heatmap(
                z=_heatmap_pivot.values.tolist(),
                x=_period_labels_fmt,
                y=_heatmap_pivot.index.tolist(),
                colorscale=[[0, '#f0f9ff'], [0.3, '#fbbf24'], [0.7, '#ef4444'], [1.0, '#7f1d1d']],
                hoverongaps=False,
                hovertemplate='%{y}<br>%{x}: %{z} time(s)<extra></extra>',
                showscale=True,
                colorbar=dict(title='Times', thickness=12, len=0.8),
                xgap=2,
                ygap=2,
            ))
            fig_pattern_team_timeline.update_layout(
                height=max(280, 80 + len(top_patterns) * 52),
                template='plotly_white',
                margin=dict(l=36, r=60, t=24, b=48),
                font={'family': 'Segoe UI, sans-serif', 'color': '#243b53'},
            )
            fig_pattern_team_timeline.update_xaxes(
                title_text=_period_label,
                tickangle=-25,
                showgrid=False,
            )
            fig_pattern_team_timeline.update_yaxes(
                title_text='',
                showgrid=False,
                autorange='reversed',
            )

        pattern_priority_cards = []
        for pattern_name in top_patterns[:4]:
            pattern_count = int(pattern_totals.get(pattern_name, 0))
            pattern_prev = int(previous_pattern_totals.get(pattern_name, 0))
            pattern_teams = _safe_nunique(details[details['Padrão'] == pattern_name], 'Projeto')
            latest_week_count = int(len(latest_week_details[latest_week_details['Padrão'] == pattern_name])) if not latest_week_details.empty else 0
            accent_color = '#c62828' if int(pattern_critical_totals.get(pattern_name, 0)) > 0 else '#c77d12'
            pattern_priority_cards.append(
                _build_pattern_kpi_card(
                    pattern_name,
                    _fmt_int(pattern_count),
                    f'{pattern_teams} times afetados no período | última semana: {latest_week_count} ocorrência(s).',
                    _trend_descriptor(pattern_count, pattern_prev, lower_is_better=True),
                    accent_color,
                    featured=False,
                )
            )
        priority_patterns_section = html.Div(pattern_priority_cards, style={
            'display': 'grid',
            'gridTemplateColumns': 'repeat(auto-fit, minmax(260px, 1fr))',
            'gap': '12px',
        }) if pattern_priority_cards else html.P('Sem base suficiente para destacar padrões prioritários.')

        details_view = details.sort_values(['Semana', 'Severidade'], ascending=[False, True]) if not details.empty else pd.DataFrame()
        table_summary = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in summary.columns],
            data=summary.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            page_size=12,
        ) if not summary.empty else html.P('Nenhum padrão sistêmico acionado no período.')
        table_details = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in details_view.columns],
            data=details_view.to_dict('records'),
            style_cell={
                'textAlign': 'left',
                'padding': '6px',
                'minWidth': '120px',
                'maxWidth': '260px',
                'whiteSpace': 'normal'
            },
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Severidade} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Severidade} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
            ],
            page_size=12,
            filter_action='native',
            sort_action='native',
        ) if not details_view.empty else html.P('Nenhum detalhe adicional de padrões no período.')
        checklist_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in checklist_df.columns],
            data=checklist_df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Status} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Status} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                {'if': {'filter_query': '{Status} = "OK"'}, 'backgroundColor': '#edf7ed'},
            ],
            page_size=10,
        ) if not checklist_df.empty else html.P('Sem checklist automatizado disponível para o recorte.')
        diagnosis_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in diagnosis_df.columns],
            data=diagnosis_df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px', 'minWidth': '120px', 'maxWidth': '320px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Severidade} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Severidade} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                {'if': {'filter_query': '{Severidade} = "OK"'}, 'backgroundColor': '#edf7ed'},
            ],
            page_size=10,
            filter_action='native',
            sort_action='native',
        ) if not diagnosis_df.empty else html.P('Nenhum diagnóstico prescritivo foi gerado para o período.')
        expedite_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in expedite_table_df.columns],
            data=expedite_table_df.to_dict('records'),
            style_cell={'textAlign': 'center', 'padding': '6px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            page_size=10,
        ) if not expedite_table_df.empty else html.P('Sem base suficiente para governança de expedite.')
        expedite_alerts_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in expedite_alerts_df.columns],
            data=expedite_alerts_df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Status} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Status} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                {'if': {'filter_query': '{Status} = "OK"'}, 'backgroundColor': '#edf7ed'},
            ],
            page_size=10,
        ) if not expedite_alerts_df.empty else html.P('Sem alertas de expedite para o recorte.')
        variability_alerts_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in variability_alerts_df.columns],
            data=variability_alerts_df.to_dict('records'),
            style_cell={'textAlign': 'left', 'padding': '6px', 'whiteSpace': 'normal'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Status} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                {'if': {'filter_query': '{Status} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                {'if': {'filter_query': '{Status} = "OK"'}, 'backgroundColor': '#edf7ed'},
            ],
            page_size=10,
        ) if not variability_alerts_df.empty else html.P('Sem base suficiente para alertas de variabilidade.')
        weekly_review_table = dash_table.DataTable(
            columns=[{'name': c, 'id': c} for c in weekly_review_df.columns],
            data=weekly_review_df.to_dict('records'),
            style_cell={'textAlign': 'center', 'padding': '6px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
            page_size=12,
        ) if not weekly_review_df.empty else html.P('Sem base semanal suficiente para a revisão automatizada.')

        return html.Div([
            html.Div([
                html.Div([
                    html.Div('Leitura Executiva', style={
                        'display': 'inline-block',
                        'fontSize': '11px',
                        'fontWeight': '700',
                        'letterSpacing': '0.06em',
                        'textTransform': 'uppercase',
                        'color': '#176ea4',
                        'backgroundColor': 'rgba(255,255,255,0.72)',
                        'border': '1px solid rgba(23, 110, 164, 0.18)',
                        'borderRadius': '999px',
                        'padding': '5px 10px',
                        'marginBottom': '12px',
                    }),
                    html.H3('Padrões Sistêmicos Detectados', style={'marginBottom': '8px', 'fontSize': '34px', 'lineHeight': '1.05', 'color': '#10202f'}),
                    html.Div([
                        html.Div(f'Período atual: {pd.Timestamp(start_ts).strftime("%d/%m/%Y")} a {pd.Timestamp(end_ts).strftime("%d/%m/%Y")}', style={'fontSize': '12px', 'fontWeight': '600', 'color': '#516170'}),
                        html.Div(f'Período anterior: {pd.Timestamp(previous_start_ts).strftime("%d/%m/%Y")} a {pd.Timestamp(previous_end_ts).strftime("%d/%m/%Y")}', style={'fontSize': '12px', 'fontWeight': '600', 'color': '#516170'}),
                        html.Div(f'Última semana com sinal: {latest_week_label}', style={'fontSize': '12px', 'fontWeight': '600', 'color': '#516170'}),
                    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px'}),
                ], style={'flex': '1.7 1 360px'}),
                html.Div([
                    html.Div('Padrão líder', style={'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '0.05em', 'textTransform': 'uppercase', 'color': '#607080', 'marginBottom': '4px'}),
                    html.Div(top_pattern_name, style={'fontSize': '24px', 'fontWeight': '700', 'lineHeight': '1.1', 'color': '#10202f', 'marginBottom': '8px'}),
                    html.Div(f'{top_pattern_count} ocorrência(s) no período atual', style={'fontSize': '13px', 'color': '#52606d', 'marginBottom': '8px'}),
                    html.Div(_trend_descriptor(top_pattern_count, int(previous_pattern_totals.get(top_pattern_name, 0)) if top_pattern_name in previous_pattern_totals.index else np.nan, lower_is_better=True)[2], style={'fontSize': '12px', 'color': '#5f6e7b'}),
                ], style={
                    'flex': '1 1 280px',
                    'backgroundColor': 'rgba(255,255,255,0.88)',
                    'border': '1px solid #d6e0eb',
                    'borderRadius': '18px',
                    'padding': '16px',
                    'boxShadow': '0 2px 10px rgba(15, 23, 32, 0.05)',
                }),
            ], style={
                'display': 'flex',
                'flexWrap': 'wrap',
                'alignItems': 'stretch',
                'gap': '14px',
                'background': 'linear-gradient(135deg, #eef6ff 0%, #f8fbff 55%, #fffaf2 100%)',
                'border': '1px solid #d8e5f1',
                'borderRadius': '22px',
                'padding': '20px',
                'marginBottom': '16px',
                'boxShadow': '0 12px 30px rgba(15, 23, 32, 0.05)',
            }),
            _section_shell(
                'Times em Alerta',
                'Quais times, quais problemas e o que fazer',
                (
                    f'{affected_teams} time(s) com sinais detectados no período | '
                    f'{critical_teams} crítico(s) | '
                    f'{int(len(details))} ocorrências totais. '
                    'Cards ordenados por severidade e volume. '
                    'A ação sugerida é baseada no padrão mais recorrente do time.'
                ),
                team_alert_grid,
                '#fff8f6' if critical_teams > 0 else '#f8fbff',
                '#f5c6c6' if critical_teams > 0 else '#cfe0f3',
            ),
            _section_shell(
                'Padrões Prioritários',
                'Indicadores que mais pressionam o time',
                'Aqui ficam os padrões mais incidentes do período, já com sinalização de tendência e leitura da última semana.',
                priority_patterns_section,
                '#ffffff',
                '#d9e2ec',
            ),
            _section_shell(
                'Evolução por Período',
                'Volume de ocorrências e cobertura de times ao longo do tempo',
                'Períodos de até 10 semanas usam granularidade semanal; acima disso, agrupamento mensal. Barras empilhadas mostram volume total e composição por padrão; o mapa de calor revela quais padrões persistiram nos times — cor mais escura = mais times afetados.',
                html.Div([
                    _chart_card(
                        'Ocorrências por padrão',
                        'Barras empilhadas por período — comparação direta entre semanas/meses facilita identificar tendência de melhora ou piora.',
                        fig_pattern_timeline,
                    ) if isinstance(fig_pattern_timeline, go.Figure) and fig_pattern_timeline.data else html.Div(),
                    _chart_card(
                        'Times afetados por padrão',
                        'Mapa de calor: cada linha é um padrão, cada coluna é um período. Cor branca = zero times; vermelho escuro = muitos times impactados.',
                        fig_pattern_team_timeline,
                    ) if isinstance(fig_pattern_team_timeline, go.Figure) and fig_pattern_team_timeline.data else html.Div(),
                ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px'}),
                '#fffaf2',
                '#f1d7a8',
            ),
            _section_shell(
                'Governança Operacional',
                'Checklist, fast track e variabilidade com layout dedicado',
                'As leituras operacionais continuam abaixo do resumo executivo, mas agora organizadas em três blocos próprios para facilitar varredura e comparação.',
                html.Div([
                    operational_kpi_groups,
                    html.Div([
                        _chart_card(
                            'Resumo semanal automatizado',
                            'Throughput, WIP e cycle time da revisão semanal automatizada.',
                            fig_weekly_review,
                        ) if isinstance(fig_weekly_review, go.Figure) and fig_weekly_review.data else html.Div(),
                        _chart_card(
                            'Padrões por severidade',
                            'Leitura agregada das ocorrências já consolidadas por padrão e severidade.',
                            fig_summary,
                        ) if isinstance(fig_summary, go.Figure) and fig_summary.data else html.Div(),
                    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px', 'marginTop': '14px'}),
                    html.Div([
                        _chart_card(
                            'Governança Fast Track / Highest',
                            'Participação de Highest na saída para verificar se fast track está virando regra.',
                            fig_expedite,
                        ) if isinstance(fig_expedite, go.Figure) and fig_expedite.data else html.Div(),
                        _chart_card(
                            'Variabilidade e dispersão',
                            'Semáforos de CV para lead time, cycle time e throughput.',
                            fig_variability,
                        ) if isinstance(fig_variability, go.Figure) and fig_variability.data else html.Div(),
                    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px', 'marginTop': '14px'}),
                ]),
                '#ffffff',
                '#d9e2ec',
            ),
            _section_shell(
                'Base Analítica',
                'Tabelas detalhadas para investigação',
                'As bases detalhadas ficam concentradas aqui no final da página para apoiar análise sem tirar foco dos KPIs e das tendências.',
                html.Div([
                    _table_block(
                        'Resumo de ocorrências',
                        'Tabela agregada por padrão e severidade.',
                        table_summary,
                    ),
                    _table_block(
                        'Detalhamento semanal',
                        'Ocorrências por time, semana, padrão e regras acionadas.',
                        table_details,
                    ),
                    _table_block(
                        'Checklist semanal automatizado',
                        'Leitura operacional da última semana do recorte usando bandas históricas.',
                        checklist_table,
                    ),
                    _table_block(
                        'Diagnóstico prescritivo',
                        'Combinações semanais traduzidas em diagnóstico provável e ação recomendada.',
                        diagnosis_table,
                    ),
                    _table_block(
                        'Alertas Fast Track / Highest',
                        'Sinais textuais da governança de expedite no recorte atual.',
                        expedite_alerts_table,
                    ),
                    _table_block(
                        'Tabela Fast Track / Highest',
                        'Base analítica da distribuição de throughput por classe de serviço.',
                        expedite_table,
                    ),
                    _table_block(
                        'Alertas de variabilidade',
                        'Tabela de dispersão operacional convertida em status acionável.',
                        variability_alerts_table,
                    ),
                    _table_block(
                        'Base semanal da revisão automatizada',
                        'Série base da revisão semanal com throughput, WIP e cycle time.',
                        weekly_review_table,
                    ),
                ]),
                '#f8fbff',
                '#cfe0f3',
            ),
        ], style={'maxWidth': '1320px', 'margin': '0 auto 24px auto', 'padding': '0 12px 24px 12px'})

    if tab == 'tab-process-mining-jira':
        if projeto and normalize_text(projeto) not in {'w1nner', 'w1nnr'}:
            return html.Div([
                html.H3('Process Mining Jira (W1NNER)', style={'textAlign': 'center'}),
                html.P(
                    'Este painel é dedicado ao projeto W1NNER (W1NNR). Limpe o filtro de projeto ou selecione W1NNER.',
                    style={'textAlign': 'center', 'color': '#555'}
                )
            ])

        report_path, pm_report = load_w1nner_process_mining_report()
        if not pm_report:
            return html.Div([
                html.H3('Process Mining Jira (W1NNER)', style={'textAlign': 'center'}),
                html.P('Relatório de process mining não encontrado.', style={'textAlign': 'center', 'color': '#b22222'}),
                html.Pre(
                    'Gere com: python process_mining_jira.py --input <jira_changelog_detalhado.csv>',
                    style={'maxWidth': '900px', 'margin': '0 auto', 'whiteSpace': 'pre-wrap', 'background': '#f7f7f7', 'padding': '12px', 'borderRadius': '8px'}
                )
            ])

        pm_summary = pm_report.get('ResumoConformidade', pd.DataFrame()).copy()
        pm_cases = pm_report.get('ConformidadeCasos', pd.DataFrame()).copy()
        pm_rework = pm_report.get('RetrabalhoItens', pd.DataFrame()).copy()
        pm_status = pm_report.get('TemposPorStatus', pd.DataFrame()).copy()
        pm_weekly = pm_report.get('VazaoPessoaSemanal', pd.DataFrame()).copy()
        pm_people = pm_report.get('VazaoPessoaResumo', pd.DataFrame()).copy()
        pm_hours_people = pm_report.get('HorasPessoaResumo', pd.DataFrame()).copy()
        pm_hours_status = pm_report.get('HorasPessoaStatus', pd.DataFrame()).copy()
        pm_variants = pm_report.get('VariantesTop', pd.DataFrame()).copy()
        pm_events = pm_report.get('EventosFiltrados', pd.DataFrame()).copy()
        pm_dfg_edges = pm_report.get('PM4PyDFGEdges', pd.DataFrame()).copy()
        pm_dfg_perf_edges = pm_report.get('PM4PyDFGPerfEdges', pd.DataFrame()).copy()
        pm_tbr_summary = pm_report.get('PM4PyTBRResumo', pd.DataFrame()).copy()
        pm_tbr_cases = pm_report.get('PM4PyTBRCasos', pd.DataFrame()).copy()
        pm_align_summary = pm_report.get('PM4PyAlignResumo', pd.DataFrame()).copy()
        pm_align_cases = pm_report.get('PM4PyAlignCasos', pd.DataFrame()).copy()
        pm_align_moves = pm_report.get('PM4PyAlignTopMoves', pd.DataFrame()).copy()
        pm_meta = pm_report.get('Metadados', pd.DataFrame()).copy()

        for dcol in ['Done Final Date']:
            if dcol in pm_cases.columns:
                pm_cases[dcol] = pd.to_datetime(pm_cases[dcol], errors='coerce')
            if dcol in pm_rework.columns:
                pm_rework[dcol] = pd.to_datetime(pm_rework[dcol], errors='coerce')
            if dcol in pm_tbr_cases.columns:
                pm_tbr_cases[dcol] = pd.to_datetime(pm_tbr_cases[dcol], errors='coerce')
            if dcol in pm_align_cases.columns:
                pm_align_cases[dcol] = pd.to_datetime(pm_align_cases[dcol], errors='coerce')
        if 'Semana' in pm_weekly.columns:
            pm_weekly['Semana'] = pd.to_datetime(pm_weekly['Semana'], errors='coerce')
        if 'History Created' in pm_events.columns:
            pm_events['History Created'] = pd.to_datetime(pm_events['History Created'], errors='coerce')

        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        if 'Done Final Date' in pm_cases.columns:
            pm_cases = pm_cases[
                pm_cases['Done Final Date'].isna() |
                ((pm_cases['Done Final Date'] >= start_ts) & (pm_cases['Done Final Date'] <= end_ts))
            ]
        if 'Done Final Date' in pm_rework.columns:
            pm_rework = pm_rework[
                pm_rework['Done Final Date'].isna() |
                ((pm_rework['Done Final Date'] >= start_ts) & (pm_rework['Done Final Date'] <= end_ts))
            ]
        if 'Semana' in pm_weekly.columns:
            pm_weekly = pm_weekly[
                (pm_weekly['Semana'] >= start_ts) &
                (pm_weekly['Semana'] <= end_ts + pd.Timedelta(days=7))
            ]
        if 'History Created' in pm_events.columns:
            pm_events = pm_events[
                (pm_events['History Created'] >= start_ts) &
                (pm_events['History Created'] <= end_ts + pd.Timedelta(days=1))
            ]
        if 'Done Final Date' in pm_tbr_cases.columns:
            pm_tbr_cases = pm_tbr_cases[
                pm_tbr_cases['Done Final Date'].isna() |
                ((pm_tbr_cases['Done Final Date'] >= start_ts) & (pm_tbr_cases['Done Final Date'] <= end_ts))
            ]
        if 'Done Final Date' in pm_align_cases.columns:
            pm_align_cases = pm_align_cases[
                pm_align_cases['Done Final Date'].isna() |
                ((pm_align_cases['Done Final Date'] >= start_ts) & (pm_align_cases['Done Final Date'] <= end_ts))
            ]

        if responsavel:
            selected_people = set(_normalize_responsavel_filter_values(responsavel, canonicalize=True))
            if 'Responsavel' in pm_people.columns:
                pm_people = pm_people[pm_people['Responsavel'].apply(_canonical_person_name).isin(selected_people)]
            if 'Responsavel' in pm_weekly.columns:
                pm_weekly = pm_weekly[pm_weekly['Responsavel'].apply(_canonical_person_name).isin(selected_people)]
            if 'Responsavel' in pm_hours_people.columns:
                pm_hours_people = pm_hours_people[pm_hours_people['Responsavel'].apply(_canonical_person_name).isin(selected_people)]
            if 'Responsavel' in pm_hours_status.columns:
                pm_hours_status = pm_hours_status[pm_hours_status['Responsavel'].apply(_canonical_person_name).isin(selected_people)]
            if 'Done Final Author' in pm_rework.columns:
                pm_rework = pm_rework[pm_rework['Done Final Author'].apply(_canonical_person_name).isin(selected_people)]
            if 'Done Final Author' in pm_cases.columns:
                pm_cases = pm_cases[pm_cases['Done Final Author'].apply(_canonical_person_name).isin(selected_people)]
            if 'Author' in pm_events.columns:
                pm_events = pm_events[pm_events['Author'].apply(_canonical_person_name).isin(selected_people)]
            if 'Done Final Author' in pm_tbr_cases.columns:
                pm_tbr_cases = pm_tbr_cases[pm_tbr_cases['Done Final Author'].apply(_canonical_person_name).isin(selected_people)]
            if 'Done Final Author' in pm_align_cases.columns:
                pm_align_cases = pm_align_cases[pm_align_cases['Done Final Author'].apply(_canonical_person_name).isin(selected_people)]

        # Rebuild graph datasets from date-filtered bases to guarantee UI date filter adherence.
        if not pm_cases.empty and {'Issue Key', 'Done Final Author', 'Done Final Date'}.issubset(pm_cases.columns):
            done_cases = pm_cases[pm_cases['Done Final Date'].notna()].copy()
            if not done_cases.empty:
                done_cases['Responsavel'] = done_cases['Done Final Author'].fillna('').astype(str).str.strip().replace('', 'Sem Autor')
                done_cases['Com Retrabalho'] = (
                    pd.to_numeric(done_cases.get('Rework Score', pd.Series(0, index=done_cases.index)), errors='coerce')
                    .fillna(0)
                    .gt(0)
                    .astype(int)
                )
                done_cases['Semana'] = pd.to_datetime(done_cases['Done Final Date'], errors='coerce').dt.to_period('W-SUN').dt.start_time

                pm_weekly = (
                    done_cases.groupby(['Semana', 'Responsavel'], dropna=False)
                    .agg(
                        **{
                            'Itens Concluidos': ('Issue Key', 'nunique'),
                            'Itens Com Retrabalho': ('Com Retrabalho', 'sum'),
                        }
                    )
                    .reset_index()
                )
                pm_weekly['Taxa Retrabalho (%)'] = np.where(
                    pm_weekly['Itens Concluidos'] > 0,
                    pm_weekly['Itens Com Retrabalho'] / pm_weekly['Itens Concluidos'] * 100.0,
                    0.0,
                )

                pm_people = (
                    done_cases.groupby('Responsavel', dropna=False)
                    .agg(
                        **{
                            'Itens Concluidos': ('Issue Key', 'nunique'),
                            'Itens Com Retrabalho': ('Com Retrabalho', 'sum'),
                            'Rework Score Total': ('Rework Score', 'sum'),
                            'Lead Time Mediano (dias)': ('Lead Time Fluxo (dias)', 'median'),
                            'Semanas Com Entrega': ('Semana', lambda s: s.dropna().nunique()),
                        }
                    )
                    .reset_index()
                )
                pm_people['Taxa Retrabalho (%)'] = np.where(
                    pm_people['Itens Concluidos'] > 0,
                    pm_people['Itens Com Retrabalho'] / pm_people['Itens Concluidos'] * 100.0,
                    0.0,
                )
                pm_people['Media Itens/Semana Ativa'] = np.where(
                    pm_people['Semanas Com Entrega'] > 0,
                    pm_people['Itens Concluidos'] / pm_people['Semanas Com Entrega'],
                    0.0,
                )
                pm_people = pm_people.sort_values('Itens Concluidos', ascending=False).reset_index(drop=True)
            else:
                pm_weekly = pd.DataFrame(columns=['Semana', 'Responsavel', 'Itens Concluidos', 'Itens Com Retrabalho', 'Taxa Retrabalho (%)'])
                pm_people = pd.DataFrame(columns=['Responsavel', 'Itens Concluidos', 'Itens Com Retrabalho'])

        if not pm_events.empty:
            evt = pm_events.copy()
            if 'Author' in evt.columns:
                evt['Author'] = evt['Author'].fillna('').astype(str).str.strip().replace('', 'Sem Autor')
            if 'Issue Key' in evt.columns:
                evt['Issue Key'] = evt['Issue Key'].astype(str).str.strip()

            if {'TempoStatusDias', 'To Status', 'Issue Key'}.issubset(evt.columns):
                x_status = evt.dropna(subset=['TempoStatusDias']).copy()
                if not x_status.empty:
                    x_status['TempoStatusDias'] = pd.to_numeric(x_status['TempoStatusDias'], errors='coerce')
                    x_status = x_status.dropna(subset=['TempoStatusDias'])
                    pm_status = (
                        x_status.groupby('To Status', dropna=False)
                        .agg(
                            **{
                                'Qtde Ocorrencias': ('Issue Key', 'count'),
                                'Qtde Itens': ('Issue Key', 'nunique'),
                                'Tempo Medio (dias)': ('TempoStatusDias', 'mean'),
                                'Tempo Mediano (dias)': ('TempoStatusDias', 'median'),
                                'P85 (dias)': ('TempoStatusDias', lambda s: float(s.quantile(0.85)) if len(s) else np.nan),
                                'P95 (dias)': ('TempoStatusDias', lambda s: float(s.quantile(0.95)) if len(s) else np.nan),
                            }
                        )
                        .reset_index()
                        .rename(columns={'To Status': 'Status'})
                    )
                else:
                    pm_status = pd.DataFrame(columns=['Status', 'Qtde Ocorrencias', 'Qtde Itens', 'Tempo Medio (dias)', 'Tempo Mediano (dias)', 'P85 (dias)', 'P95 (dias)'])

            if {'Author', 'TempoStatusDias', 'Issue Key'}.issubset(evt.columns):
                x_hours = evt.dropna(subset=['TempoStatusDias']).copy()
                if not x_hours.empty:
                    x_hours['HorasNoFluxo'] = pd.to_numeric(x_hours['TempoStatusDias'], errors='coerce').fillna(0) * 24.0
                    pm_hours_people = (
                        x_hours.groupby('Author', dropna=False)
                        .agg(
                            **{
                                'HorasNoFluxo': ('HorasNoFluxo', 'sum'),
                                'Eventos': ('Issue Key', 'count'),
                                'CardsUnicos': ('Issue Key', 'nunique'),
                            }
                        )
                        .reset_index()
                        .rename(columns={'Author': 'Responsavel'})
                    )
                    pm_hours_people['HorasMediasPorEvento'] = np.where(
                        pm_hours_people['Eventos'] > 0,
                        pm_hours_people['HorasNoFluxo'] / pm_hours_people['Eventos'],
                        0.0,
                    )

                    if 'To Status' in x_hours.columns:
                        pm_hours_status = (
                            x_hours.groupby(['Author', 'To Status'], dropna=False)
                            .agg(
                                **{
                                    'HorasNoFluxo': ('HorasNoFluxo', 'sum'),
                                    'Eventos': ('Issue Key', 'count'),
                                    'CardsUnicos': ('Issue Key', 'nunique'),
                                }
                            )
                            .reset_index()
                            .rename(columns={'Author': 'Responsavel', 'To Status': 'Status'})
                        )
                    else:
                        pm_hours_status = pd.DataFrame(columns=['Responsavel', 'Status', 'HorasNoFluxo', 'Eventos', 'CardsUnicos'])
                else:
                    pm_hours_people = pd.DataFrame(columns=['Responsavel', 'HorasNoFluxo', 'HorasMediasPorEvento', 'Eventos', 'CardsUnicos'])
                    pm_hours_status = pd.DataFrame(columns=['Responsavel', 'Status', 'HorasNoFluxo', 'Eventos', 'CardsUnicos'])

            if {'From Status', 'To Status'}.issubset(evt.columns):
                edge_base = evt.copy()
                edge_base['From Status'] = edge_base['From Status'].fillna('').astype(str).str.strip()
                edge_base['To Status'] = edge_base['To Status'].fillna('').astype(str).str.strip()
                edge_base = edge_base[(edge_base['From Status'] != '') & (edge_base['To Status'] != '')].copy()
                if not edge_base.empty:
                    pm_dfg_edges = (
                        edge_base.groupby(['From Status', 'To Status'], dropna=False)
                        .size()
                        .reset_index(name='Count')
                        .rename(columns={'From Status': 'From', 'To Status': 'To'})
                    )
                    if 'TempoStatusDias' in edge_base.columns:
                        perf_base = edge_base.dropna(subset=['TempoStatusDias']).copy()
                        perf_base['PerfHours'] = pd.to_numeric(perf_base['TempoStatusDias'], errors='coerce').fillna(0) * 24.0
                        pm_dfg_perf_edges = (
                            perf_base.groupby(['From Status', 'To Status'], dropna=False)['PerfHours']
                            .mean()
                            .reset_index()
                            .rename(columns={'From Status': 'From', 'To Status': 'To'})
                        )
                    else:
                        pm_dfg_perf_edges = pd.DataFrame(columns=['From', 'To', 'PerfHours'])
                else:
                    pm_dfg_edges = pd.DataFrame(columns=['From', 'To', 'Count'])
                    pm_dfg_perf_edges = pd.DataFrame(columns=['From', 'To', 'PerfHours'])

        if not pm_cases.empty and {'Variant', 'Issue Key'}.issubset(pm_cases.columns):
            v = pm_cases.copy()
            v['Variant'] = v['Variant'].fillna('').astype(str).str.strip()
            v = v[v['Variant'] != '']
            if not v.empty:
                pm_variants = (
                    v.groupby('Variant', dropna=False)
                    .agg(**{'Qtde Casos': ('Issue Key', 'nunique')})
                    .reset_index()
                    .sort_values('Qtde Casos', ascending=False)
                )
                total_var = max(1, int(pm_variants['Qtde Casos'].sum()))
                pm_variants['Pct Casos'] = pm_variants['Qtde Casos'] / total_var * 100.0
            else:
                pm_variants = pd.DataFrame(columns=['Variant', 'Qtde Casos', 'Pct Casos'])

        pm_pull_dev = pd.DataFrame()
        pm_pull_dev_by_band = pd.DataFrame()
        pull_dev_total_cards = 0
        pull_dev_total_story_points = 0.0
        if not pm_events.empty and {'Issue Key', 'Author', 'To Status Norm'}.issubset(pm_events.columns):
            dev_status_norms = {'in progress', 'in development', 'development', 'doing', 'desenvolvimento'}
            pull_events = pm_events.copy()
            pull_events['To Status Norm'] = pull_events['To Status Norm'].astype(str).map(normalize_text)
            pull_events = pull_events[pull_events['To Status Norm'].isin(dev_status_norms)].copy()
            if 'From Status Norm' in pull_events.columns:
                pull_events['From Status Norm'] = pull_events['From Status Norm'].astype(str).map(normalize_text)
                pull_events = pull_events[~pull_events['From Status Norm'].isin(dev_status_norms)].copy()
            pull_events['Issue Key'] = pull_events['Issue Key'].astype(str).str.strip().str.upper()
            pull_events = pull_events[pull_events['Issue Key'].ne('')].copy()
            if 'History Created' in pull_events.columns:
                pull_events = pull_events.sort_values(['Issue Key', 'History Created'])
            else:
                pull_events = pull_events.sort_values(['Issue Key'])
            pull_events = pull_events.drop_duplicates(subset=['Issue Key'], keep='first')

            alias_index = _load_person_alias_index()
            pull_events['Responsavel'] = pull_events['Author'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index))
            pull_events['Responsavel'] = pull_events['Responsavel'].replace('', 'Sem Autor')

            ds_items = load_project_downstream_items_csv('W1NNER')
            if not ds_items.empty and 'ID' in ds_items.columns:
                ds_points = ds_items.copy()
                ds_points['Issue Key'] = ds_points['ID'].astype(str).str.strip().str.upper()
                if 'Story Points' not in ds_points.columns:
                    ds_points['Story Points'] = np.nan
                if 'Story point estimate' not in ds_points.columns:
                    ds_points['Story point estimate'] = np.nan
                def _resolve_story_points(row):
                    primary = _coerce_story_points_value(row.get('Story Points'))
                    if pd.notna(primary):
                        return primary
                    return _coerce_story_points_value(row.get('Story point estimate'))

                ds_points['StoryPoints_Value'] = ds_points.apply(_resolve_story_points, axis=1)
                ds_points = ds_points[['Issue Key', 'StoryPoints_Value']].drop_duplicates(subset=['Issue Key'], keep='first')
                pull_events = pull_events.merge(ds_points, how='left', on='Issue Key')
            else:
                pull_events['StoryPoints_Value'] = np.nan

            seniority_index = _load_person_seniority_index(alias_index=alias_index)
            pull_events['Senioridade'] = pull_events['Responsavel'].map(seniority_index).fillna('Nao classificado')
            pull_events['Faixa Story Points'] = pull_events['StoryPoints_Value'].apply(_story_points_band)
            faixa_order = ['Sem estimativa', '0', '1', '2-3', '5', '8', '13+']
            pull_events['Faixa Story Points'] = pd.Categorical(pull_events['Faixa Story Points'], categories=faixa_order, ordered=True)
            pm_pull_dev = pull_events.copy()
            pull_dev_total_cards = int(pm_pull_dev['Issue Key'].nunique())
            pull_dev_total_story_points = float(pd.to_numeric(pm_pull_dev['StoryPoints_Value'], errors='coerce').fillna(0).sum())
            pm_pull_dev_by_band = (
                pm_pull_dev
                .groupby(['Responsavel', 'Faixa Story Points'], dropna=False)
                .agg(
                    **{
                        'Cards Puxados': ('Issue Key', 'nunique'),
                        'Story Points Total': ('StoryPoints_Value', lambda s: pd.to_numeric(s, errors='coerce').fillna(0).sum()),
                    }
                )
                .reset_index()
            )
            pm_pull_dev_by_band['Faixa Story Points'] = pm_pull_dev_by_band['Faixa Story Points'].astype(str)
            person_totals = (
                pm_pull_dev_by_band
                .groupby('Responsavel', dropna=False)['Cards Puxados']
                .sum()
                .sort_values(ascending=True)
            )
            person_order = person_totals.index.tolist()
            pm_pull_dev_by_band['Responsavel'] = pd.Categorical(
                pm_pull_dev_by_band['Responsavel'],
                categories=person_order,
                ordered=True,
            )
            pm_pull_dev_by_band = pm_pull_dev_by_band.sort_values(['Responsavel', 'Faixa Story Points'])

        if pm_people.empty and pm_cases.empty:
            return html.Div('Sem dados de process mining para o período/filtros selecionados.')

        finalized_issue_keys = set()
        if 'Issue Key' in pm_cases.columns:
            cases_for_throughput = pm_cases.copy()
            if 'Done Final Date' in cases_for_throughput.columns:
                cases_for_throughput = cases_for_throughput[cases_for_throughput['Done Final Date'].notna()]
            issue_keys = (
                cases_for_throughput['Issue Key']
                .astype(str)
                .str.strip()
                .str.upper()
            )
            finalized_issue_keys = set(issue_keys[issue_keys.ne('')].tolist())
        if finalized_issue_keys:
            total_concluidos = len(finalized_issue_keys)
        elif 'Itens Concluidos' in pm_people.columns and not pm_people.empty:
            total_concluidos = int(pd.to_numeric(pm_people['Itens Concluidos'], errors='coerce').fillna(0).sum())
        else:
            total_concluidos = 0

        if 'Itens Com Retrabalho' in pm_people.columns and not pm_people.empty:
            itens_retrabalho = int(pd.to_numeric(pm_people['Itens Com Retrabalho'], errors='coerce').fillna(0).sum())
        elif not pm_cases.empty and 'Rework Score' in pm_cases.columns:
            itens_retrabalho = int((pd.to_numeric(pm_cases['Rework Score'], errors='coerce').fillna(0) > 0).sum())
        else:
            itens_retrabalho = 0
        taxa_retrabalho = (itens_retrabalho / total_concluidos * 100.0) if total_concluidos > 0 else 0.0

        conf_media = np.nan
        if not pm_cases.empty and 'Conformance Score' in pm_cases.columns:
            conf_series = pd.to_numeric(pm_cases['Conformance Score'], errors='coerce').dropna()
            if not conf_series.empty:
                conf_media = float(conf_series.mean())

        horas_fluxo_total = 0.0
        horas_fluxo_media_evento = np.nan
        if not pm_hours_people.empty and 'HorasNoFluxo' in pm_hours_people.columns:
            horas_fluxo_total = float(pd.to_numeric(pm_hours_people['HorasNoFluxo'], errors='coerce').fillna(0).sum())
        if not pm_hours_people.empty and {'HorasNoFluxo', 'Eventos'}.issubset(pm_hours_people.columns):
            eventos_total = float(pd.to_numeric(pm_hours_people['Eventos'], errors='coerce').fillna(0).sum())
            horas_fluxo_media_evento = (horas_fluxo_total / eventos_total) if eventos_total > 0 else np.nan

        horas_execucao_periodo = 0.0
        if not pm_events.empty and 'TempoStatusDias' in pm_events.columns:
            horas_execucao_periodo = float(
                pd.to_numeric(pm_events['TempoStatusDias'], errors='coerce').fillna(0).sum() * 24.0
            )

        bitbucket_logs = load_project_bitbucket_logs('W1NNER')
        bitbucket_end_ts = end_ts + pd.Timedelta(days=1)
        bb_people, bb_totals = compute_bitbucket_contributor_metrics(
            bitbucket_logs, start_ts, bitbucket_end_ts, alias_index=_load_person_alias_index()
        )
        if responsavel and not bb_people.empty and 'Pessoa' in bb_people.columns:
            selected_people = set(_normalize_responsavel_filter_values(responsavel, canonicalize=True))
            bb_people = bb_people[bb_people['Pessoa'].isin(selected_people)].copy()
            bb_totals = {
                'Commits': int(pd.to_numeric(bb_people.get('Commits', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
                'PRs Abertos': int(pd.to_numeric(bb_people.get('PRs Abertos', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
                'Aprovacoes': int(pd.to_numeric(bb_people.get('Aprovacoes', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
                'Reprovacoes': int(pd.to_numeric(bb_people.get('Reprovacoes', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
                'PRs Declinados (Autor)': int(pd.to_numeric(bb_people.get('PRs Declinados (Autor)', pd.Series(dtype=float)), errors='coerce').fillna(0).sum()),
            }
        bb_totals = bb_totals if isinstance(bb_totals, dict) else {}

        cobertura_tecnica_pct = np.nan
        itens_com_evidencia = 0
        if finalized_issue_keys:
            keys_done = set(finalized_issue_keys)
            if keys_done:
                tech_keys = _extract_work_item_keys_from_bitbucket_logs(bitbucket_logs, start_ts, bitbucket_end_ts)
                if responsavel and 'Done Final Author' in pm_cases.columns:
                    selected_people = set(_normalize_responsavel_filter_values(responsavel, canonicalize=True))
                    done_authors = pm_cases['Done Final Author'].apply(_canonical_person_name)
                    keys_done = set(
                        pm_cases[done_authors.isin(selected_people)]['Issue Key']
                        .astype(str).str.strip().str.upper().tolist()
                    )
                itens_com_evidencia = len(keys_done.intersection(tech_keys))
                cobertura_tecnica_pct = (itens_com_evidencia / len(keys_done) * 100.0) if len(keys_done) > 0 else np.nan

        def _pm_metric_card(title, value, subtitle, accent_color, featured=False):
            return html.Div([
                html.Div(title, style={
                    'fontSize': '12px',
                    'fontWeight': '700',
                    'letterSpacing': '0.04em',
                    'textTransform': 'uppercase',
                    'color': accent_color,
                    'marginBottom': '10px',
                }),
                html.Div(value, style={
                    'fontSize': '34px' if featured else '28px',
                    'fontWeight': '700',
                    'lineHeight': '1.0',
                    'color': '#0f1720',
                    'marginBottom': '8px',
                }),
                html.Div(subtitle, style={
                    'fontSize': '12px',
                    'color': '#556575',
                    'lineHeight': '1.45',
                }),
            ], style={
                'background': 'linear-gradient(180deg, #ffffff 0%, #f9fbfe 100%)' if featured else 'white',
                'border': f'1px solid {accent_color}33' if featured else '1px solid #d9e2ec',
                'borderTop': f'5px solid {accent_color}',
                'borderRadius': '16px',
                'padding': '16px',
                'boxShadow': '0 10px 24px rgba(15, 23, 32, 0.08)' if featured else '0 2px 8px rgba(15, 23, 32, 0.06)',
                'minHeight': '160px' if featured else '142px',
                'height': '100%',
            })

        kpis = html.Div([
            _pm_metric_card('Itens Finalizados', str(total_concluidos), 'itens únicos concluídos no período selecionado', '#176ea4', featured=True),
            _pm_metric_card('Taxa de Retrabalho', f"{taxa_retrabalho:.1f}%", 'percentual de itens concluídos com retrabalho', '#c62828', featured=True),
            _pm_metric_card('Cobertura Técnica', f"{cobertura_tecnica_pct:.1f}%" if pd.notna(cobertura_tecnica_pct) else '—', 'itens concluídos com evidência técnica em Bitbucket', '#2e7d32', featured=True),
            _pm_metric_card('Conformidade Média', f"{conf_media:.2f}" if pd.notna(conf_media) else '—', 'média do score de conformidade dos casos analisados', '#c77d12', featured=True),
            _pm_metric_card('Itens com Retrabalho', str(itens_retrabalho), 'volume absoluto de retrabalho no período', '#c77d12'),
            _pm_metric_card('Cards Puxados p/ Dev', str(pull_dev_total_cards), 'quantidade de itens puxados para desenvolvimento', '#176ea4'),
            _pm_metric_card('SP Puxados p/ Dev', f"{pull_dev_total_story_points:,.1f}", 'story points puxados no recorte', '#176ea4'),
            _pm_metric_card('Horas Execução', f"{horas_execucao_periodo:,.1f}", 'horas inferidas pelas permanências por status', '#2cb3ad'),
            _pm_metric_card('Horas no Fluxo', f"{horas_fluxo_total:,.1f}", 'proxy agregado das transições observadas', '#2cb3ad'),
            _pm_metric_card('Média h/Evento', f"{horas_fluxo_media_evento:.2f}" if pd.notna(horas_fluxo_media_evento) else '—', 'tempo médio associado a cada evento do fluxo', '#2cb3ad'),
            _pm_metric_card('Itens c/ Evidência Técnica', str(int(itens_com_evidencia)), 'interseção entre itens concluídos e chaves vistas no Bitbucket', '#176ea4'),
        ], style={
            'display': 'grid',
            'gridTemplateColumns': 'repeat(auto-fit, minmax(210px, 1fr))',
            'gap': '12px',
            'marginBottom': '18px',
        })

        fig_vazao_pessoa = go.Figure()
        if not pm_people.empty and {'Responsavel', 'Itens Concluidos'}.issubset(pm_people.columns):
            people_plot = pm_people.copy()
            people_plot['Itens Concluidos'] = pd.to_numeric(people_plot['Itens Concluidos'], errors='coerce').fillna(0)
            if 'Taxa Retrabalho (%)' in people_plot.columns:
                people_plot['Taxa Retrabalho (%)'] = pd.to_numeric(people_plot['Taxa Retrabalho (%)'], errors='coerce')
            people_plot = people_plot.sort_values('Itens Concluidos', ascending=False).head(20)
            fig_vazao_pessoa = px.bar(
                people_plot,
                x='Itens Concluidos',
                y='Responsavel',
                orientation='h',
                color='Taxa Retrabalho (%)' if 'Taxa Retrabalho (%)' in people_plot.columns else None,
                title='Vazão por Pessoa (itens concluídos)',
                color_continuous_scale='RdYlGn_r'
            )
            fig_vazao_pessoa.update_layout(height=560, yaxis={'categoryorder': 'total ascending'})

        fig_pull_dev_overlay = go.Figure()
        if not pm_pull_dev_by_band.empty and {'Responsavel', 'Faixa Story Points', 'Cards Puxados'}.issubset(pm_pull_dev_by_band.columns):
            faixa_order = ['Sem estimativa', '0', '1', '2-3', '5', '8', '13+']
            fig_pull_dev_overlay = px.bar(
                pm_pull_dev_by_band,
                x='Cards Puxados',
                y='Responsavel',
                color='Faixa Story Points',
                orientation='h',
                barmode='stack',
                title='Cards puxados para In Development por pessoa (quebrado por faixa de story points)',
                hover_data=['Story Points Total'],
                category_orders={'Faixa Story Points': faixa_order},
            )
            fig_pull_dev_overlay.update_layout(
                height=max(520, 24 * max(1, len(pm_pull_dev_by_band['Responsavel'].cat.categories))),
                xaxis_title='Cards puxados',
                yaxis_title='Pessoa',
                legend_title_text='Faixa de Story Points',
            )

        fig_vazao_semanal = go.Figure()
        if not pm_weekly.empty and {'Semana', 'Responsavel', 'Itens Concluidos'}.issubset(pm_weekly.columns):
            pm_weekly['Itens Concluidos'] = pd.to_numeric(pm_weekly['Itens Concluidos'], errors='coerce').fillna(0)
            if responsavel:
                weekly_plot = pm_weekly.copy()
            else:
                top_people = []
                if not pm_people.empty and {'Responsavel', 'Itens Concluidos'}.issubset(pm_people.columns):
                    tmp = pm_people.copy()
                    tmp['Itens Concluidos'] = pd.to_numeric(tmp['Itens Concluidos'], errors='coerce').fillna(0)
                    top_people = tmp.sort_values('Itens Concluidos', ascending=False).head(5)['Responsavel'].tolist()
                weekly_plot = pm_weekly[pm_weekly['Responsavel'].isin(top_people)] if top_people else pm_weekly.copy()
            fig_vazao_semanal = px.line(
                weekly_plot,
                x='Semana',
                y='Itens Concluidos',
                color='Responsavel',
                markers=True,
                title='Vazão Semanal por Pessoa (Top 5)'
            )
            fig_vazao_semanal.update_layout(height=500, xaxis_tickangle=-45, margin=dict(b=120))

        fig_retrabalho_pessoa = go.Figure()
        if not pm_people.empty and {'Responsavel', 'Itens Com Retrabalho'}.issubset(pm_people.columns):
            retr_people = pm_people.copy()
            retr_people['Itens Com Retrabalho'] = pd.to_numeric(retr_people['Itens Com Retrabalho'], errors='coerce').fillna(0)
            if 'Taxa Retrabalho (%)' in retr_people.columns:
                retr_people['Taxa Retrabalho (%)'] = pd.to_numeric(retr_people['Taxa Retrabalho (%)'], errors='coerce')
            retr_people = retr_people.sort_values('Itens Com Retrabalho', ascending=False).head(20)
            fig_retrabalho_pessoa = px.bar(
                retr_people,
                x='Itens Com Retrabalho',
                y='Responsavel',
                orientation='h',
                color='Taxa Retrabalho (%)' if 'Taxa Retrabalho (%)' in retr_people.columns else None,
                title='Retrabalho por Pessoa (itens concluídos com retrabalho)',
                color_continuous_scale='OrRd'
            )
            fig_retrabalho_pessoa.update_layout(height=560, yaxis={'categoryorder': 'total ascending'})

        fig_tempo_status = go.Figure()
        if not pm_status.empty and {'Status', 'Tempo Mediano (dias)'}.issubset(pm_status.columns):
            status_plot = pm_status.copy()
            status_plot['Tempo Mediano (dias)'] = pd.to_numeric(status_plot['Tempo Mediano (dias)'], errors='coerce').fillna(0)
            status_plot = status_plot.sort_values('Tempo Mediano (dias)', ascending=False).head(15)
            fig_tempo_status = px.bar(
                status_plot,
                x='Tempo Mediano (dias)',
                y='Status',
                orientation='h',
                title='Tempos por Status (Mediana)'
            )
            fig_tempo_status.update_layout(height=520, yaxis={'categoryorder': 'total ascending'})

        fig_variantes = go.Figure()
        if not pm_variants.empty and {'Variant', 'Qtde Casos'}.issubset(pm_variants.columns):
            variants_plot = pm_variants.copy()
            variants_plot['Qtde Casos'] = pd.to_numeric(variants_plot['Qtde Casos'], errors='coerce').fillna(0)
            if 'Pct Casos' in variants_plot.columns:
                variants_plot['Pct Casos'] = pd.to_numeric(variants_plot['Pct Casos'], errors='coerce')
            variants_plot = variants_plot.sort_values('Qtde Casos', ascending=False).head(20)
            fig_variantes = px.bar(
                variants_plot,
                x='Qtde Casos',
                y='Variant',
                orientation='h',
                color='Pct Casos' if 'Pct Casos' in variants_plot.columns else None,
                title='Variantes Mais Frequentes (Top 20)',
                color_continuous_scale='Viridis'
            )
            fig_variantes.update_layout(height=620, yaxis={'categoryorder': 'total ascending'})

        fig_dfg_edges = go.Figure()
        if not pm_dfg_edges.empty and {'From', 'To', 'Count'}.issubset(pm_dfg_edges.columns):
            dfg_plot = pm_dfg_edges.copy()
            dfg_plot['Count'] = pd.to_numeric(dfg_plot['Count'], errors='coerce').fillna(0)
            dfg_plot['Aresta'] = dfg_plot['From'].astype(str) + ' -> ' + dfg_plot['To'].astype(str)
            dfg_plot = dfg_plot.sort_values('Count', ascending=False).head(25)
            fig_dfg_edges = px.bar(
                dfg_plot,
                x='Count',
                y='Aresta',
                orientation='h',
                title='DFG PM4Py - Top Arestas por Frequência'
            )
            fig_dfg_edges.update_layout(height=720, yaxis={'categoryorder': 'total ascending'})

        fig_dfg_perf = go.Figure()
        if not pm_dfg_perf_edges.empty and {'From', 'To', 'PerfHours'}.issubset(pm_dfg_perf_edges.columns):
            dfg_perf_plot = pm_dfg_perf_edges.copy()
            dfg_perf_plot['PerfHours'] = pd.to_numeric(dfg_perf_plot['PerfHours'], errors='coerce').fillna(0)
            dfg_perf_plot['Aresta'] = dfg_perf_plot['From'].astype(str) + ' -> ' + dfg_perf_plot['To'].astype(str)
            dfg_perf_plot = dfg_perf_plot.sort_values('PerfHours', ascending=False).head(25)
            fig_dfg_perf = px.bar(
                dfg_perf_plot,
                x='PerfHours',
                y='Aresta',
                orientation='h',
                title='DFG PM4Py Performance - Top Arestas por Tempo (horas)'
            )
            fig_dfg_perf.update_layout(height=720, yaxis={'categoryorder': 'total ascending'})

        fig_tbr_fitness = go.Figure()
        if not pm_tbr_cases.empty and 'TraceFitness' in pm_tbr_cases.columns:
            tbr_hist = pm_tbr_cases.copy()
            tbr_hist['TraceFitness'] = pd.to_numeric(tbr_hist['TraceFitness'], errors='coerce')
            tbr_hist = tbr_hist.dropna(subset=['TraceFitness'])
            if not tbr_hist.empty:
                fig_tbr_fitness = px.histogram(
                    tbr_hist,
                    x='TraceFitness',
                    nbins=20,
                    title='Token-Based Replay (PM4Py) - Distribuição de Trace Fitness'
                )
                fig_tbr_fitness.update_layout(height=420)

        jira_bitbucket_traceability_section = build_pm_commits_vs_jira_report(
            pm_people=pm_people,
            pm_cases=pm_cases,
            start_ts=start_ts,
            end_ts=end_ts,
            responsavel=responsavel,
        )

        if not pm_rework.empty:
            sort_cols = [c for c in ['Rework Score', 'Reopen Count', 'Backward Moves'] if c in pm_rework.columns]
            if sort_cols:
                pm_rework = pm_rework.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        rework_cols = [c for c in [
            'Issue Key', 'Tipo de Problema', 'Rework Score', 'Reopen Count', 'Backward Moves', 'QA Returns',
            'Revisitas Status', 'Conformance Score', 'Done Final Author', 'Done Final Date'
        ] if c in pm_rework.columns]
        people_table_cols = [c for c in [
            'Responsavel', 'Itens Concluidos', 'Itens Com Retrabalho', 'Taxa Retrabalho (%)',
            'Rework Score Total', 'Lead Time Mediano (dias)', 'Media Itens/Semana Ativa'
        ] if c in pm_people.columns]
        horas_people_cols = [c for c in ['Responsavel', 'HorasNoFluxo', 'HorasMediasPorEvento', 'Eventos', 'CardsUnicos'] if c in pm_hours_people.columns]
        horas_status_cols = [c for c in ['Responsavel', 'Status', 'HorasNoFluxo', 'Eventos', 'CardsUnicos'] if c in pm_hours_status.columns]
        pull_dev_cols = [c for c in ['Issue Key', 'Responsavel', 'Senioridade', 'Faixa Story Points', 'StoryPoints_Value', 'History Created', 'From Status', 'To Status'] if c in pm_pull_dev.columns]
        tbr_summary_cols = [c for c in ['Metric', 'Value'] if c in pm_tbr_summary.columns]
        tbr_case_cols = [c for c in ['Issue Key', 'TraceIsFit', 'TraceFitness', 'MissingTokens', 'RemainingTokens', 'ConsumedTokens', 'ProducedTokens'] if c in pm_tbr_cases.columns]
        align_summary_cols = [c for c in ['Metric', 'Value'] if c in pm_align_summary.columns]
        align_case_cols = [c for c in ['Issue Key', 'AlignmentFitness', 'AlignmentCost', 'SyncMoves', 'LogMoves', 'ModelMoves', 'DesviosTotal'] if c in pm_align_cases.columns]
        align_move_cols = [c for c in ['Move', 'Count', 'CasesAffected'] if c in pm_align_moves.columns]
        conf_table_cols = [c for c in ['Metrica', 'Valor'] if c in pm_summary.columns]
        meta_table_cols = [c for c in ['Metrica', 'Valor'] if c in pm_meta.columns]

        def _pm_section_shell(kicker, title, subtitle, children, background_color, border_color):
            return html.Div([
                html.Div(kicker, style={
                    'display': 'inline-block',
                    'fontSize': '11px',
                    'fontWeight': '700',
                    'letterSpacing': '0.05em',
                    'textTransform': 'uppercase',
                    'color': '#176ea4',
                    'backgroundColor': 'rgba(255,255,255,0.72)',
                    'border': '1px solid rgba(23, 110, 164, 0.18)',
                    'borderRadius': '999px',
                    'padding': '5px 10px',
                    'marginBottom': '10px',
                }),
                html.Div(title, style={'fontSize': '24px', 'fontWeight': '700', 'lineHeight': '1.1', 'color': '#10202f', 'marginBottom': '6px'}),
                html.Div(subtitle, style={'fontSize': '13px', 'color': '#4d5c6b', 'lineHeight': '1.55', 'marginBottom': '16px'}),
                children,
            ], style={
                'backgroundColor': background_color,
                'border': f'1px solid {border_color}',
                'borderRadius': '20px',
                'padding': '18px',
                'boxShadow': '0 6px 18px rgba(15, 23, 32, 0.04)',
                'marginBottom': '18px',
            })

        def _pm_graph_card(title, subtitle, figure, min_width='360px', flex='1 1 420px'):
            return html.Div([
                html.Div(title, style={'fontSize': '16px', 'fontWeight': '700', 'color': '#17324d', 'marginBottom': '4px'}),
                html.Div(subtitle, style={'fontSize': '12px', 'color': '#5f6e7b', 'lineHeight': '1.45', 'marginBottom': '8px'}),
                dcc.Graph(figure=figure),
            ], style={
                'flex': flex,
                'minWidth': min_width,
                'backgroundColor': 'white',
                'border': '1px solid #d9e2ec',
                'borderRadius': '18px',
                'padding': '14px',
                'boxShadow': '0 2px 10px rgba(15, 23, 32, 0.05)',
            })

        def _pm_table_card(title, subtitle, columns, data, page_size=12, sort_action='native', filter_action='none', min_width='360px', flex='1 1 420px'):
            return html.Div([
                html.Div(title, style={'fontSize': '16px', 'fontWeight': '700', 'color': '#17324d', 'marginBottom': '4px'}),
                html.Div(subtitle, style={'fontSize': '12px', 'color': '#5f6e7b', 'lineHeight': '1.45', 'marginBottom': '10px'}),
                dash_table.DataTable(
                    columns=[{'name': c, 'id': c} for c in columns],
                    data=data,
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '9px 10px',
                        'minWidth': '100px',
                        'maxWidth': '260px',
                        'whiteSpace': 'normal',
                        'border': 'none',
                        'fontSize': '13px',
                        'fontFamily': 'Segoe UI, sans-serif',
                    },
                    style_header={'backgroundColor': '#eef4fb', 'color': '#17324d', 'fontWeight': '700', 'border': 'none'},
                    style_data={'backgroundColor': 'white', 'borderBottom': '1px solid #edf2f7'},
                    style_as_list_view=True,
                    sort_action=sort_action,
                    filter_action=filter_action,
                    page_size=page_size,
                ),
            ], style={
                'flex': flex,
                'minWidth': min_width,
                'backgroundColor': 'white',
                'border': '1px solid #d9e2ec',
                'borderRadius': '18px',
                'padding': '14px',
                'boxShadow': '0 2px 10px rgba(15, 23, 32, 0.05)',
            })

        for _figure in [fig_vazao_pessoa, fig_pull_dev_overlay, fig_vazao_semanal, fig_retrabalho_pessoa, fig_tempo_status, fig_variantes, fig_dfg_edges, fig_dfg_perf, fig_tbr_fitness]:
            _figure.update_layout(
                paper_bgcolor='white',
                plot_bgcolor='white',
                font={'family': 'Segoe UI, sans-serif', 'color': '#22313f'},
                margin=dict(l=48, r=24, t=78, b=56),
                title=dict(x=0.02, xanchor='left', font=dict(size=18, color='#10202f')),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0, bgcolor='rgba(255,255,255,0.65)'),
            )
            _figure.update_xaxes(showgrid=True, gridcolor='rgba(148,163,184,0.16)', zeroline=False)
            _figure.update_yaxes(showgrid=True, gridcolor='rgba(148,163,184,0.16)', zeroline=False)

        report_label = os.path.basename(report_path) if report_path else 'n/d'
        period_label = f"{pd.Timestamp(start_ts).strftime('%d/%m/%Y')} a {pd.Timestamp(end_ts).strftime('%d/%m/%Y')}"
        responsavel_label = _format_responsavel_filter_label(responsavel)

        def _pm_highlight_chip(label, value, note):
            return html.Div([
                html.Div(label, style={'fontSize': '11px', 'fontWeight': '700', 'letterSpacing': '0.05em', 'textTransform': 'uppercase', 'color': '#607080', 'marginBottom': '4px'}),
                html.Div(value, style={'fontSize': '24px', 'fontWeight': '700', 'lineHeight': '1.0', 'color': '#10202f', 'marginBottom': '4px'}),
                html.Div(note, style={'fontSize': '12px', 'color': '#5f6e7b', 'lineHeight': '1.4'}),
            ], style={
                'backgroundColor': 'rgba(255,255,255,0.9)',
                'border': '1px solid #d6e0eb',
                'borderRadius': '14px',
                'padding': '12px 14px',
                'minHeight': '94px',
            })
        top_executor_label = 'Sem base'
        if not pm_people.empty and {'Responsavel', 'Itens Concluidos'}.issubset(pm_people.columns):
            _top_people = pm_people.copy()
            _top_people['Itens Concluidos'] = pd.to_numeric(_top_people['Itens Concluidos'], errors='coerce').fillna(0)
            _top_people = _top_people.sort_values('Itens Concluidos', ascending=False)
            if not _top_people.empty:
                top_executor_label = f"{_top_people.iloc[0]['Responsavel']} ({int(_top_people.iloc[0]['Itens Concluidos'])})"

        status_bottleneck_label = 'Sem base'
        if not pm_status.empty and {'Status', 'Tempo Mediano (dias)'}.issubset(pm_status.columns):
            _top_status = pm_status.copy()
            _top_status['Tempo Mediano (dias)'] = pd.to_numeric(_top_status['Tempo Mediano (dias)'], errors='coerce').fillna(0)
            _top_status = _top_status.sort_values('Tempo Mediano (dias)', ascending=False)
            if not _top_status.empty:
                status_bottleneck_label = f"{_top_status.iloc[0]['Status']} ({_top_status.iloc[0]['Tempo Mediano (dias)']:.1f}d)"

        variant_label = 'Sem base'
        if not pm_variants.empty and {'Variant', 'Qtde Casos'}.issubset(pm_variants.columns):
            _top_variant = pm_variants.copy()
            _top_variant['Qtde Casos'] = pd.to_numeric(_top_variant['Qtde Casos'], errors='coerce').fillna(0)
            _top_variant = _top_variant.sort_values('Qtde Casos', ascending=False)
            if not _top_variant.empty:
                variant_label = f"{_top_variant.iloc[0]['Variant']} ({int(_top_variant.iloc[0]['Qtde Casos'])} casos)"

        return html.Div([
            html.Div([
                html.Div([
                    html.Div('Leitura Executiva', style={
                        'display': 'inline-block',
                        'fontSize': '11px',
                        'fontWeight': '700',
                        'letterSpacing': '0.06em',
                        'textTransform': 'uppercase',
                        'color': '#176ea4',
                        'backgroundColor': 'rgba(255,255,255,0.72)',
                        'border': '1px solid rgba(23, 110, 164, 0.18)',
                        'borderRadius': '999px',
                        'padding': '5px 10px',
                        'marginBottom': '12px',
                    }),
                    html.H3('Process Mining Jira - W1NNER (História, Task, Bug)', style={'marginBottom': '8px', 'fontSize': '34px', 'lineHeight': '1.05', 'color': '#10202f'}),
                    html.P(
                        'Aba reorganizada para seguir o padrão do Painel Fluxo, priorizando resumo executivo, leitura por pessoa e estrutura do fluxo.',
                        style={'color': '#4d5c6b', 'marginBottom': '14px', 'fontSize': '14px', 'lineHeight': '1.6'}
                    ),
                    html.Div([
                        html.Div(f'Período: {period_label}', style={'fontSize': '12px', 'fontWeight': '600', 'color': '#516170'}),
                        html.Div(f'Responsável: {responsavel_label}', style={'fontSize': '12px', 'fontWeight': '600', 'color': '#516170'}),
                        html.Div(f'Fonte: {report_label}', style={'fontSize': '12px', 'fontWeight': '600', 'color': '#516170'}),
                    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px'}),
                ], style={'flex': '1.5 1 340px'}),
                html.Div([
                    _pm_highlight_chip('Líder de vazão', top_executor_label, 'responsável com mais itens concluídos'),
                    _pm_highlight_chip('Maior permanência', status_bottleneck_label, 'status com maior tempo mediano'),
                    _pm_highlight_chip('Variante líder', variant_label, 'caminho mais recorrente entre os casos'),
                    _pm_highlight_chip('Evidência técnica', str(int(itens_com_evidencia)), 'itens concluídos que apareceram em logs técnicos'),
                ], style={
                    'flex': '2.1 1 420px',
                    'display': 'grid',
                    'gridTemplateColumns': 'repeat(auto-fit, minmax(170px, 1fr))',
                    'gap': '10px',
                }),
            ], style={
                'display': 'flex',
                'flexWrap': 'wrap',
                'alignItems': 'stretch',
                'gap': '14px',
                'background': 'linear-gradient(135deg, #eef6ff 0%, #f8fbff 55%, #fffaf2 100%)',
                'border': '1px solid #d8e5f1',
                'borderRadius': '22px',
                'padding': '20px',
                'marginBottom': '16px',
                'boxShadow': '0 12px 30px rgba(15, 23, 32, 0.05)',
            }),
            _pm_section_shell('Resumo Executivo', 'Indicadores âncora do process mining', 'Primeiro lemos o resumo executivo do período; depois aprofundamos em pessoa, descoberta do fluxo e conformidade.', kpis, '#f8fbff', '#cfe0f3'),
            _pm_section_shell(
                'Operação por Pessoa',
                'Vazão, entrada em desenvolvimento e concentração de retrabalho',
                'Este bloco aproxima a leitura operacional do time: quem conclui mais, quem recebe mais entrada e onde o retrabalho está concentrado.',
                html.Div([
                    html.Details([
                        html.Summary('Vazão por Pessoa (detalhamento)', style={
                            'cursor': 'pointer', 'fontWeight': '600', 'fontSize': '13px',
                            'color': '#2980b9', 'marginBottom': '8px',
                        }),
                        html.Div([
                            _pm_graph_card('Vazão por Pessoa', 'Top responsáveis por itens concluídos no recorte, com cor refletindo taxa de retrabalho.', fig_vazao_pessoa),
                            _pm_graph_card('Retrabalho por Pessoa', 'Volume de itens concluídos com retrabalho por responsável.', fig_retrabalho_pessoa),
                        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px'}),
                    ], style={'marginBottom': '14px'}),
                    html.Div([
                        _pm_graph_card('Vazão Semanal', 'Evolução semanal da conclusão por pessoa, priorizando os principais nomes do período.', fig_vazao_semanal),
                        _pm_graph_card('Tempo por Status', 'Mediana de permanência por status para localizar pontos de espera mais caros.', fig_tempo_status),
                    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px'}),
                ]),
                '#ffffff',
                '#d9e2ec',
            ),
            _pm_section_shell(
                'Descoberta do Fluxo',
                'Variantes, DFG e leitura estrutural do processo',
                'A mesma base analítica é reorganizada aqui para facilitar a leitura da topologia do fluxo e dos caminhos mais frequentes.',
                html.Div([
                    _pm_graph_card('Variantes Mais Frequentes', 'Top caminhos observados nos casos analisados, com peso relativo por participação.', fig_variantes, min_width='100%', flex='1 1 100%'),
                    html.Div([
                        _pm_graph_card('DFG por Frequência', 'Arestas mais percorridas no modelo descoberto pelo PM4Py.', fig_dfg_edges),
                        _pm_graph_card('DFG por Tempo', 'Arestas com maior acúmulo de horas no fluxo.', fig_dfg_perf),
                    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px', 'marginTop': '14px'}),
                ]),
                '#f8fbff',
                '#cfe0f3',
            ),
            _pm_section_shell(
                'Conformidade PM4Py',
                'Token-based replay, alignments e visão de aderência',
                'O objetivo aqui é separar claramente a leitura de fitness, sumários de conformidade e os principais desvios observados.',
                html.Div([
                    _pm_graph_card('Distribuição de Trace Fitness', 'Histograma dos scores de trace fitness calculados pelo token-based replay.', fig_tbr_fitness, min_width='100%', flex='1 1 100%'),
                    html.Div([
                        _pm_table_card('Resumo TBR', 'Métricas consolidadas do token-based replay.', tbr_summary_cols, pm_tbr_summary[tbr_summary_cols].to_dict('records') if tbr_summary_cols else [], page_size=10, sort_action='none'),
                        _pm_table_card('Casos TBR', 'Amostra dos casos com indicadores de fitness e tokens.', tbr_case_cols, pm_tbr_cases[tbr_case_cols].head(50).to_dict('records') if tbr_case_cols else [], page_size=10, filter_action='native'),
                        _pm_table_card('Resumo Alignments', 'Síntese dos alinhamentos e custo agregado.', align_summary_cols, pm_align_summary[align_summary_cols].to_dict('records') if align_summary_cols else [], page_size=10, sort_action='none'),
                        _pm_table_card('Movimentos', 'Principais movimentos e casos afetados pelos desvios mapeados.', align_move_cols, pm_align_moves[align_move_cols].head(50).to_dict('records') if align_move_cols else [], page_size=10, filter_action='native'),
                        _pm_table_card('Casos com Alignment', 'Casos com fitness, custo e tipos de movimento observados.', align_case_cols, pm_align_cases[align_case_cols].head(50).to_dict('records') if align_case_cols else [], page_size=10, filter_action='native', min_width='100%', flex='1 1 100%'),
                    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px', 'marginTop': '14px'}),
                ]),
                '#fffaf2',
                '#f1d7a8',
            ),
            _pm_section_shell(
                'Bases Analíticas',
                'Tabelas de apoio para exploração detalhada',
                'As tabelas atuais foram mantidas, mas agora agrupadas em painéis com contexto para facilitar leitura e navegação.',
                html.Div([
                    _pm_table_card('Resumo por Pessoa', 'Consolidação de throughput, retrabalho e lead time por responsável.', people_table_cols, pm_people[people_table_cols].head(50).to_dict('records') if people_table_cols else [], page_size=12),
                    _pm_table_card('Itens Puxados para Desenvolvimento', 'Amostra dos itens puxados para In Development com faixa de story points.', pull_dev_cols, pm_pull_dev[pull_dev_cols].head(200).to_dict('records') if pull_dev_cols else [], page_size=12, filter_action='native'),
                    _pm_table_card('Horas no Fluxo por Pessoa', 'Proxy consolidado de horas e eventos por responsável.', horas_people_cols, pm_hours_people[horas_people_cols].head(50).to_dict('records') if horas_people_cols else [], page_size=12),
                    _pm_table_card('Horas no Fluxo por Pessoa e Status', 'Quebra da permanência por responsável e status visitado.', horas_status_cols, pm_hours_status[horas_status_cols].head(60).to_dict('records') if horas_status_cols else [], page_size=12, filter_action='native'),
                    _pm_table_card('Top Itens com Retrabalho', 'Itens mais críticos por score de retrabalho, reaberturas e movimentos para trás.', rework_cols, pm_rework[rework_cols].head(50).to_dict('records') if rework_cols else [], page_size=12, filter_action='native'),
                    _pm_table_card('Resumo de Conformidade Básica', 'Leitura rápida das métricas de conformidade já calculadas.', conf_table_cols, pm_summary[conf_table_cols].to_dict('records') if conf_table_cols else [], page_size=12, sort_action='none'),
                    _pm_table_card('Metadados PM4Py / Execução', 'Metadados do artefato, parâmetros de processamento e trilha da execução.', meta_table_cols, pm_meta[meta_table_cols].to_dict('records') if meta_table_cols else [], page_size=10, sort_action='none', min_width='100%', flex='1 1 100%'),
                ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '14px'}),
                '#f8fbff',
                '#cfe0f3',
            ),
        ], style={'maxWidth': '1320px', 'margin': '0 auto 24px auto', 'padding': '0 12px 24px 12px'})

    if tab == 'tab-work-item-age':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)
        today_ts = pd.Timestamp.today().normalize()
        snapshot_ts = min(end_date_ts.normalize(), today_ts)

        df_age_base = filter_df(
            fato,
            None,
            None,
            projeto,
            tipo,
            classe_servico,
            responsavel,
            criadores=criadores,
            use_creation_date=use_creation_date,
            apply_date=False,
            tipo_original=tipo_original_jira,
        )
        _stage_map_age = compute_current_stage_map(projeto) if etapa_fluxo and projeto else None
        df_age = build_live_wip_snapshot(
            df_age_base,
            snapshot_ts,
            projeto=projeto,
            selected_stages=etapa_fluxo,
            stage_map=_stage_map_age,
        )

        if df_age.empty:
            return html.Div(
                'Sem itens ativos com DataInProgress válida para calcular Work Item Age no recorte selecionado.'
            )

        df_age['DataInProgress'] = pd.to_datetime(df_age.get('DataInProgress'), errors='coerce')
        df_age['WIPStartRef'] = pd.to_datetime(df_age.get('WIPStartRef'), errors='coerce')
        df_age['DataInicioRef'] = df_age['DataInProgress'].combine_first(df_age['WIPStartRef'])
        df_age['WorkItemAge_Dias'] = pd.to_numeric(df_age.get('WIPAge'), errors='coerce')
        if df_age['WorkItemAge_Dias'].isna().any():
            df_age.loc[df_age['WorkItemAge_Dias'].isna(), 'WorkItemAge_Dias'] = (
                snapshot_ts - pd.to_datetime(df_age.loc[df_age['WorkItemAge_Dias'].isna(), 'DataInicioRef'], errors='coerce')
            ).dt.total_seconds() / 86400.0
        df_age['WorkItemAge_Dias'] = pd.to_numeric(df_age['WorkItemAge_Dias'], errors='coerce')
        df_age = df_age[df_age['WorkItemAge_Dias'].notna()].copy()
        if df_age.empty:
            return html.Div('Sem itens ativos com idade calculável para o recorte selecionado.')

        age_filter_dates = resolve_filter_date_series(df_age_base, use_creation_date=use_creation_date)
        done_period_mask = build_date_range_mask(age_filter_dates, start_date_ts, end_date_ts)
        df_cycle_done = df_age_base[done_period_mask].copy()
        df_cycle_done = df_cycle_done[done_time_eligible_mask(df_cycle_done)].copy()
        cycle_series = time_metric_series(df_cycle_done, 'TempoExecucao_Dias', non_negative=True)
        if cycle_series.empty:
            cycle_series = time_metric_series(df_cycle_done, 'CycleTime_Dias', non_negative=True)

        cycle_p50 = exact_empirical_percentile(cycle_series, 0.50) if not cycle_series.empty else np.nan
        cycle_p85 = exact_empirical_percentile(cycle_series, 0.85) if not cycle_series.empty else np.nan
        cycle_mean = float(cycle_series.mean()) if not cycle_series.empty else np.nan

        df_age['SaudeAge'] = df_age['WorkItemAge_Dias'].apply(lambda v: _work_item_age_health_label(v, cycle_p50, cycle_p85))
        df_age['AgeBucket'] = df_age['WorkItemAge_Dias'].apply(_work_item_age_bucket)
        df_age['RazaoVsCycleP50'] = np.where(
            pd.notna(cycle_p50) and cycle_p50 > 0,
            df_age['WorkItemAge_Dias'] / cycle_p50,
            np.nan,
        )
        df_age['BloqueadoFlag'] = df_age.get('Bloqueado', False).fillna(False).astype(bool) if 'Bloqueado' in df_age.columns else False
        df_age['BloqueadoLabel'] = np.where(df_age['BloqueadoFlag'], 'Bloqueado', 'Sem bloqueio')

        item_key_col = next((c for c in ['ItemID', 'Issue Key', 'ID'] if c in df_age.columns), None)
        title_col = next((c for c in ['Titulo', 'Title', 'Summary'] if c in df_age.columns), None)
        type_col = next((c for c in ['TipoDemanda', 'Tipo', 'Tipo de Problema'] if c in df_age.columns), None)
        if 'Status' not in df_age.columns:
            df_age['Status'] = 'Sem status'
        else:
            df_age['Status'] = df_age['Status'].fillna('').astype(str).replace('', 'Sem status')
        if 'Responsavel' not in df_age.columns:
            df_age['Responsavel'] = 'Sem responsável'
        else:
            df_age['Responsavel'] = df_age['Responsavel'].fillna('').astype(str).replace('', 'Sem responsável')
        if 'ClasseServico' not in df_age.columns:
            df_age['ClasseServico'] = 'Sem classe'
        else:
            df_age['ClasseServico'] = df_age['ClasseServico'].fillna('').astype(str).replace('', 'Sem classe')
        if 'Projeto' not in df_age.columns:
            df_age['Projeto'] = 'Sem projeto'
        else:
            df_age['Projeto'] = df_age['Projeto'].fillna('').astype(str).replace('', 'Sem projeto')

        if item_key_col is None:
            df_age['ItemKey'] = df_age.index.astype(str)
        else:
            df_age['ItemKey'] = df_age[item_key_col].astype(str)
        if title_col is None:
            df_age['TituloDisplay'] = ''
        else:
            df_age['TituloDisplay'] = df_age[title_col].fillna('').astype(str)
        df_age['ItemLabel'] = df_age['ItemKey'] + np.where(
            df_age['TituloDisplay'].str.strip() != '',
            ' - ' + df_age['TituloDisplay'].str.slice(0, 60),
            ''
        )

        severity_order = {'Crítico': 0, 'Atenção': 1, 'Saudável': 2, 'Sem referência': 3, 'Sem idade': 4}
        severity_colors = {
            'Crítico': '#C62828',
            'Atenção': '#EF6C00',
            'Saudável': '#2E7D32',
            'Sem referência': '#546E7A',
            'Sem idade': '#90A4AE',
        }
        age_bucket_order = ['0-7d', '8-15d', '16-30d', '31-60d', '60d+', 'Sem idade']
        df_age['_severity_rank'] = df_age['SaudeAge'].map(lambda value: severity_order.get(value, 99))

        risk_summary = (
            df_age.groupby('SaudeAge', dropna=False)
            .agg(
                Itens=('ItemKey', 'count'),
                IdadeMedia=('WorkItemAge_Dias', 'mean'),
                IdadeMediana=('WorkItemAge_Dias', 'median'),
                IdadeMax=('WorkItemAge_Dias', 'max'),
                Bloqueados=('BloqueadoFlag', 'sum'),
            )
            .reset_index()
            .rename(columns={'SaudeAge': 'Saúde'})
        )
        if not risk_summary.empty:
            for col in ['IdadeMedia', 'IdadeMediana', 'IdadeMax']:
                risk_summary[col] = pd.to_numeric(risk_summary[col], errors='coerce').round(1)
            risk_summary['_severity_rank'] = risk_summary['Saúde'].map(lambda value: severity_order.get(value, 99))
            risk_summary = risk_summary.sort_values('_severity_rank', ignore_index=True).drop(columns=['_severity_rank'])

        status_summary = (
            df_age.groupby(['Status', 'SaudeAge'], dropna=False)
            .agg(
                Itens=('ItemKey', 'count'),
                IdadeMedia=('WorkItemAge_Dias', 'mean'),
                IdadeMax=('WorkItemAge_Dias', 'max'),
            )
            .reset_index()
            .rename(columns={'SaudeAge': 'Saúde'})
        )
        if not status_summary.empty:
            status_summary['IdadeMedia'] = pd.to_numeric(status_summary['IdadeMedia'], errors='coerce').round(1)
            status_summary['IdadeMax'] = pd.to_numeric(status_summary['IdadeMax'], errors='coerce').round(1)

        owner_summary = pd.DataFrame()
        if 'Responsavel' in df_age.columns:
            owner_summary = (
                df_age.groupby('Responsavel', dropna=False)
                .agg(
                    Itens=('ItemKey', 'count'),
                    IdadeMedia=('WorkItemAge_Dias', 'mean'),
                    IdadeMax=('WorkItemAge_Dias', 'max'),
                    Bloqueados=('BloqueadoFlag', 'sum'),
                )
                .reset_index()
                .rename(columns={'Responsavel': 'Responsável'})
            )
            owner_summary['Responsável'] = owner_summary['Responsável'].fillna('').replace('', 'Sem responsável')
            owner_summary['IdadeMedia'] = pd.to_numeric(owner_summary['IdadeMedia'], errors='coerce').round(1)
            owner_summary['IdadeMax'] = pd.to_numeric(owner_summary['IdadeMax'], errors='coerce').round(1)
            owner_summary = owner_summary.sort_values(['IdadeMedia', 'Itens'], ascending=[False, False], ignore_index=True)

        df_age['AgeBucket'] = pd.Categorical(df_age['AgeBucket'], categories=age_bucket_order, ordered=True)
        age_bucket_summary = (
            df_age.groupby(['AgeBucket', 'SaudeAge'], dropna=False)
            .size()
            .reset_index(name='Itens')
        )
        age_bucket_summary['AgeBucket'] = age_bucket_summary['AgeBucket'].astype(str)
        age_bucket_summary = age_bucket_summary[age_bucket_summary['AgeBucket'] != 'nan']

        top_oldest = (
            df_age.sort_values(['_severity_rank', 'WorkItemAge_Dias'], ascending=[True, False], ignore_index=True)
            .head(15)
            .copy()
        )
        top_oldest = top_oldest.sort_values('WorkItemAge_Dias', ascending=True)

        fig_age_hist = px.histogram(
            df_age,
            x='WorkItemAge_Dias',
            color='SaudeAge',
            nbins=min(24, max(8, int(np.ceil(np.sqrt(len(df_age)))))),
            title='Distribuição do Work Item Age',
            labels={'WorkItemAge_Dias': 'Work Item Age (dias)', 'count': 'Itens', 'SaudeAge': 'Saúde'},
            color_discrete_map=severity_colors,
        )
        if pd.notna(cycle_p50):
            fig_age_hist.add_vline(x=float(cycle_p50), line_dash='dash', line_color='#1F77B4', annotation_text=f'Cycle P50: {cycle_p50:.1f}d')
        if pd.notna(cycle_p85):
            fig_age_hist.add_vline(x=float(cycle_p85), line_dash='dot', line_color='#8E24AA', annotation_text=f'Cycle P85: {cycle_p85:.1f}d')
        fig_age_hist.update_layout(height=480, barmode='overlay', margin=dict(b=60))

        fig_top_oldest = px.bar(
            top_oldest,
            x='WorkItemAge_Dias',
            y='ItemLabel',
            color='SaudeAge',
            orientation='h',
            title='Itens ativos mais envelhecidos',
            labels={'WorkItemAge_Dias': 'Work Item Age (dias)', 'ItemLabel': 'Item', 'SaudeAge': 'Saúde'},
            color_discrete_map=severity_colors,
            hover_data=['Status', 'Responsavel', 'ClasseServico'] if 'Responsavel' in top_oldest.columns and 'ClasseServico' in top_oldest.columns else None,
        )
        fig_top_oldest.update_layout(height=520, margin=dict(l=120, r=30, t=60, b=40), yaxis_title='')

        scatter_hover = [c for c in ['ItemKey', 'TituloDisplay', 'Status', 'Responsavel', 'ClasseServico', 'Projeto'] if c in df_age.columns]
        fig_age_scatter = px.scatter(
            df_age.sort_values('DataInicioRef'),
            x='DataInicioRef',
            y='WorkItemAge_Dias',
            color='SaudeAge',
            symbol='BloqueadoLabel',
            hover_data=scatter_hover,
            title='Work Item Age por data de início',
            labels={'DataInicioRef': 'Data de início', 'WorkItemAge_Dias': 'Work Item Age (dias)', 'SaudeAge': 'Saúde'},
            color_discrete_map=severity_colors,
        )
        if pd.notna(cycle_p50):
            fig_age_scatter.add_hline(y=float(cycle_p50), line_dash='dash', line_color='#1F77B4', annotation_text=f'Cycle P50: {cycle_p50:.1f}d')
        if pd.notna(cycle_p85):
            fig_age_scatter.add_hline(y=float(cycle_p85), line_dash='dot', line_color='#8E24AA', annotation_text=f'Cycle P85: {cycle_p85:.1f}d')
        fig_age_scatter.update_layout(height=500, margin=dict(b=90), xaxis_tickangle=-45)

        fig_age_bucket = px.bar(
            age_bucket_summary,
            x='AgeBucket',
            y='Itens',
            color='SaudeAge',
            barmode='stack',
            title='Faixas de Work Item Age por severidade',
            labels={'AgeBucket': 'Faixa de idade', 'Itens': 'Itens', 'SaudeAge': 'Saúde'},
            color_discrete_map=severity_colors,
            category_orders={'AgeBucket': age_bucket_order},
        )
        fig_age_bucket.update_layout(height=420, margin=dict(b=40))

        critical_items = int((df_age['SaudeAge'] == 'Crítico').sum())
        attention_items = int((df_age['SaudeAge'] == 'Atenção').sum())
        blocked_items = int(df_age['BloqueadoFlag'].sum())
        total_items = int(len(df_age))
        avg_age = float(df_age['WorkItemAge_Dias'].mean()) if total_items else np.nan
        median_age = float(df_age['WorkItemAge_Dias'].median()) if total_items else np.nan
        max_age = float(df_age['WorkItemAge_Dias'].max()) if total_items else np.nan
        critical_pct = (critical_items / total_items * 100.0) if total_items else 0.0

        subtitle_parts = [
            f"Snapshot considerado: {snapshot_ts.strftime('%d/%m/%Y')}",
            f"Itens ativos: {total_items}",
            f"Amostra de Cycle Time concluído: {int(len(cycle_series))}",
        ]
        if pd.notna(cycle_mean):
            subtitle_parts.append(f"Cycle médio: {cycle_mean:.1f}d")
        if pd.notna(cycle_p50):
            subtitle_parts.append(f"Cycle P50: {cycle_p50:.1f}d")
        if pd.notna(cycle_p85):
            subtitle_parts.append(f"Cycle P85: {cycle_p85:.1f}d")
        if pd.notna(cycle_p50):
            interpretation = (
                "Saudável = idade <= Cycle P50; Atenção = entre Cycle P50 e P85; "
                "Crítico = acima do Cycle P85 do mesmo recorte."
            )
        else:
            interpretation = (
                "Sem referência factual de Cycle Time concluído no recorte; a aba mantém a idade dos itens "
                "e sinaliza a limitação."
            )

        detail_cols = [
            ('ItemKey', 'Item'),
            ('TituloDisplay', 'Título'),
            ('Projeto', 'Projeto'),
            ('Status', 'Status'),
            ('Responsavel', 'Responsável'),
            ('ClasseServico', 'Classe Serviço'),
            ('BloqueadoLabel', 'Bloqueio'),
            ('DataInicioRef', 'Data Início'),
            ('WorkItemAge_Dias', 'Work Item Age (dias)'),
            ('RazaoVsCycleP50', 'Razão vs Cycle P50'),
            ('SaudeAge', 'Saúde'),
            ('Link', 'Link'),
        ]
        if type_col and type_col not in {'TipoDemanda', 'Tipo'}:
            detail_cols.insert(3, (type_col, 'Tipo'))
        elif type_col:
            detail_cols.insert(3, (type_col, type_col))
        available_detail_cols = [src for src, _ in detail_cols if src in df_age.columns]
        detail_rename = {src: dst for src, dst in detail_cols if src in available_detail_cols}
        detail_df = df_age[available_detail_cols].copy().rename(columns=detail_rename)
        if 'Data Início' in detail_df.columns:
            detail_df['Data Início'] = pd.to_datetime(detail_df['Data Início'], errors='coerce').dt.strftime('%d/%m/%Y')
        for col in ['Work Item Age (dias)', 'Razão vs Cycle P50']:
            if col in detail_df.columns:
                detail_df[col] = pd.to_numeric(detail_df[col], errors='coerce').round(1)
        detail_df = detail_df.sort_values(
            ['Saúde', 'Work Item Age (dias)'] if 'Work Item Age (dias)' in detail_df.columns else ['Saúde'],
            ascending=[True, False],
            key=lambda s: s.map(severity_order) if s.name == 'Saúde' else s,
            ignore_index=True,
        )

        return html.Div([
            html.Div([
                html.H2("Work Item Age", className='wia-title'),
                html.Div(
                    [html.Span(part, className='wia-meta-chip') for part in subtitle_parts],
                    className='wia-meta-row',
                ),
                html.P(interpretation, className='wia-interpretation'),
            ], className='wia-header'),
            html.Div([
                html.Div([
                    html.P('Itens Ativos', className='wia-hero-eyebrow'),
                    html.H2(f"{total_items}", className='wia-hero-value'),
                    html.P('Snapshot operacional do trabalho em progresso no recorte atual.', className='wia-hero-caption'),
                    html.Div([
                        html.Div([
                            html.Span('Críticos', className='wia-mini-label'),
                            html.Strong(f"{critical_items}", className='wia-mini-value'),
                        ], className='wia-mini-stat'),
                        html.Div([
                            html.Span('Bloqueados', className='wia-mini-label'),
                            html.Strong(f"{blocked_items}", className='wia-mini-value'),
                        ], className='wia-mini-stat'),
                    ], className='wia-mini-stats'),
                ], className='wia-hero-card'),
                html.Div([
                    html.Div('Envelhecimento', className='wia-panel-title'),
                    html.Div([
                        create_kpi_card(
                            'Age Médio',
                            f"{avg_age:.1f}d" if pd.notna(avg_age) else '—',
                            class_name='wia-kpi-card',
                        ),
                        create_kpi_card(
                            'Age Mediano',
                            f"{median_age:.1f}d" if pd.notna(median_age) else '—',
                            class_name='wia-kpi-card',
                        ),
                        create_kpi_card(
                            'Age Máximo',
                            f"{max_age:.1f}d" if pd.notna(max_age) else '—',
                            class_name='wia-kpi-card wia-kpi-card--emphasis',
                        ),
                    ], className='wia-metric-grid'),
                ], className='wia-panel'),
                html.Div([
                    html.Div('Saúde do WIP', className='wia-panel-title'),
                    html.Div([
                        create_kpi_card('Críticos', critical_items, class_name='wia-kpi-card wia-kpi-card--critical'),
                        create_kpi_card('Em Atenção', attention_items, class_name='wia-kpi-card wia-kpi-card--warning'),
                        create_kpi_card('Bloqueados', blocked_items, class_name='wia-kpi-card'),
                        create_kpi_card('% Críticos', f"{critical_pct:.1f}%", class_name='wia-kpi-card'),
                    ], className='wia-risk-grid'),
                ], className='wia-panel'),
            ], className='wia-kpi-layout'),
            dcc.Graph(figure=fig_age_hist),
            dcc.Graph(figure=fig_age_bucket),
            dcc.Graph(figure=fig_top_oldest),
            dcc.Graph(figure=fig_age_scatter),
            html.H4("Resumo por Severidade", style={'textAlign': 'center', 'marginTop': '24px'}),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in risk_summary.columns],
                data=risk_summary.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248,248,248)'}],
            ),
            html.H4("Resumo por Status", style={'textAlign': 'center', 'marginTop': '24px'}),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in status_summary.columns],
                data=status_summary.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248,248,248)'}],
                page_size=12,
            ),
            html.H4("Resumo por Responsável", style={'textAlign': 'center', 'marginTop': '24px'}),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in owner_summary.columns],
                data=owner_summary.to_dict('records'),
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248,248,248)'}],
                page_size=12,
            ) if not owner_summary.empty else html.P('Sem dados suficientes por responsável no recorte.'),
            html.H4("Detalhe dos Itens Ativos", style={'textAlign': 'center', 'marginTop': '24px'}),
            dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in detail_df.columns],
                data=detail_df.to_dict('records'),
                page_size=15,
                filter_action='native',
                sort_action='native',
                style_table={'overflowX': 'auto'},
                style_cell={'minWidth': '100px', 'width': '140px', 'maxWidth': '220px', 'textAlign': 'left'},
                style_header={'backgroundColor': 'rgb(230,230,230)', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {'if': {'filter_query': '{Saúde} = "Crítico"'}, 'backgroundColor': '#fdecea'},
                    {'if': {'filter_query': '{Saúde} = "Atenção"'}, 'backgroundColor': '#fff8e1'},
                    {'if': {'filter_query': '{Saúde} = "Saudável"'}, 'backgroundColor': '#edf7ed'},
                ],
            ),
        ], className='work-item-age-view')

    if tab == 'tab-wip':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        df_wip_base = filter_df(
            fato,
            None,
            None,
            projeto,
            tipo,
            classe_servico,
            responsavel,
            criadores=criadores,
            use_creation_date=use_creation_date,
            apply_date=False,
            tipo_original=tipo_original_jira,
        )
        _stage_map_wip = compute_current_stage_map(projeto) if etapa_fluxo and projeto else None

        if 'Responsavel' not in df_wip_base.columns or df_wip_base['Responsavel'].dropna().empty:
            return html.Div('Dados de Responsável não disponíveis para calcular WIP.')

        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        if weeks.empty:
            return html.Div("Período selecionado é muito curto para análise semanal.")

        wip_weekly_data = []
        for week_end in weeks:
            wip_at_date_df = build_live_wip_snapshot(
                df_wip_base,
                week_end,
                projeto=projeto,
                selected_stages=etapa_fluxo,
                stage_map=_stage_map_wip,
            )
            wip_counts = wip_at_date_df.groupby('Responsavel').size().reset_index(name='WIP')
            wip_counts['Semana'] = week_end
            wip_weekly_data.append(wip_counts)

        if not wip_weekly_data:
            return html.Div('Sem dados de WIP para o período e filtros selecionados.')

        wip_df = pd.concat(wip_weekly_data, ignore_index=True)
        if wip_df.empty:
            return html.Div('Sem dados de WIP para o período e filtros selecionados.')

        summary_data = []
        for person in wip_df['Responsavel'].unique():
            person_wip = wip_df[wip_df['Responsavel'] == person]
            wip_medio = person_wip['WIP'].mean()
            wip_max = person_wip['WIP'].max()
            last_week_data = person_wip[person_wip['Semana'] == person_wip['Semana'].max()]
            items_ativos_fim = last_week_data['WIP'].iloc[0] if not last_week_data.empty else 0
            
            summary_data.append({'Responsável': person, 'WIP Médio Semanal': wip_medio, 'WIP Máximo na Semana': wip_max, 'Items Ativos no Fim': items_ativos_fim})

        summary_df = pd.DataFrame(
            summary_data,
            columns=['Responsável', 'WIP Médio Semanal', 'WIP Máximo na Semana', 'Items Ativos no Fim']
        )
        if summary_df.empty:
            return html.Div('Sem dados consolidados de WIP por responsável para o período e filtros selecionados.')
        summary_df = summary_df.sort_values('WIP Médio Semanal', ascending=False)

        kpi_table = dash_table.DataTable(
            columns=[
                {"name": "Responsável", "id": "Responsável"},
                {"name": "WIP Médio Semanal", "id": "WIP Médio Semanal", "type": "numeric", "format": dash_table.Format.Format(precision=1, scheme=dash_table.Format.Scheme.fixed)},
                {"name": "WIP Máximo na Semana", "id": "WIP Máximo na Semana", "type": "numeric"},
                {"name": "Items Ativos no Fim", "id": "Items Ativos no Fim", "type": "numeric"},
            ],
            data=summary_df.to_dict('records'),
            style_cell={'textAlign': 'left'}, style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}, sort_action="native"
        )

        fig_wip_avg = px.bar(summary_df.head(30), x='Responsável', y='WIP Médio Semanal', title='WIP Médio Semanal por Pessoa (Top 30)')
        fig_wip_avg.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        if responsavel:
            df_trend = wip_df
        else:
            top_responsaveis = summary_df.head(5)['Responsável'].tolist()
            df_trend = wip_df[wip_df['Responsavel'].isin(top_responsaveis)]
            
        fig_wip_trend = px.line(df_trend, x='Semana', y='WIP', color='Responsavel', title='Tendência do WIP Semanal (Top 5 Responsáveis)', markers=True)
        # Adiciona linhas estatísticas para o WIP total por semana
        wip_total_weekly = df_trend.groupby('Semana')['WIP'].sum().reset_index()
        if not wip_total_weekly.empty:
            add_statistical_lines(fig_wip_trend, wip_total_weekly['Semana'], wip_total_weekly['WIP'], name_prefix='Total ')
        fig_wip_trend.update_layout(height=550, xaxis_tickangle=-45, margin=dict(b=130))

        return html.Div([
            html.H3("Análise de WIP por Pessoa", style={'textAlign': 'center'}),
            html.H4("Resumo do Período", style={'textAlign': 'center', 'marginTop': '30px'}),
            kpi_table,
            dcc.Graph(figure=fig_wip_avg),
            dcc.Graph(figure=fig_wip_trend),
        ])

    if tab == 'tab-estatistica':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        # Base única da aba (mesmos filtros ativos), sem recorte de DataDone.
        # O recorte temporal é aplicado por métrica para manter consistência entre
        # "Todos os projetos" e filtros por projeto.
        df_base = filter_df(
            fato,
            None,
            None,
            projeto,
            tipo,
            classe_servico,
            responsavel,
            criadores=criadores,
            use_creation_date=use_creation_date,
            apply_date=False,
            tipo_original=tipo_original_jira,
        )
        df_base, _ = apply_selected_lead_time_metric(df_base, projeto, leadtime_stages)

        # Itens concluídos no período (para Lead Time e Throughput)
        stats_filter_dates = resolve_filter_date_series(df_base, use_creation_date=use_creation_date)
        done_period_mask = build_date_range_mask(stats_filter_dates, start_date_ts, end_date_ts)
        df_done = df_base[done_period_mask].copy()
        df_done = df_done[done_time_eligible_mask(df_done)].copy()

        # --- 1. Estatísticas de Lead Time (base compartilhada com aba Lead Time) ---
        lead_time_stats = {}
        lead_col = 'LeadTime_Selected_Dias' if 'LeadTime_Selected_Dias' in df_done.columns else 'LeadTime_Dias'
        df_done_lt, lt, lt_comparable_stats = build_lead_time_comparable_scope(df_done, lead_col=lead_col)
        if not lt.empty:
            lt_exact = exact_percentile_map(lt, [0.25, 0.50, 0.75, 0.85, 0.95])
            lt_weibull = fit_weibull_linearized(lt)
            lead_time_stats = {
                'Contagem': int(len(lt)),
                'Média': f"{lt.mean():.2f}",
                'Mediana (P50)': f"{lt_exact.get(0.50, np.nan):.2f}",
                'Desvio Padrão': f"{lt.std():.2f}",
                'Mínimo': f"{lt.min():.2f}",
                'Máximo': f"{lt.max():.2f}",
                'P25': f"{lt_exact.get(0.25, np.nan):.2f}",
                'P75': f"{lt_exact.get(0.75, np.nan):.2f}",
                'P85': f"{lt_exact.get(0.85, np.nan):.2f}",
                'P95': f"{lt_exact.get(0.95, np.nan):.2f}",
                'Weibull Shape (k)': f"{lt_weibull['shape']:.4f}" if lt_weibull else '—',
                'Weibull Lambda (λ)': f"{lt_weibull['lambda']:.4f}" if lt_weibull else '—',
                'Coef. Variação (%)': f"{(lt.std() / lt.mean() * 100):.2f}" if lt.mean() > 0 else '—',
                'Amplitude': f"{lt.max() - lt.min():.2f}",
                'IQR (P75-P25)': f"{lt_exact.get(0.75, np.nan) - lt_exact.get(0.25, np.nan):.2f}",
                'Assimetria (Skewness)': f"{lt.skew():.2f}",
                'Curtose': f"{lt.kurtosis():.2f}",
            }

        def parse_optional_number(value):
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                return np.nan
            return parsed if np.isfinite(parsed) else np.nan

        lsl_value = parse_optional_number(estatistica_lsl)
        usl_value = parse_optional_number(estatistica_usl)
        lsl_input_value = float(lsl_value) if np.isfinite(lsl_value) else None
        usl_input_value = float(usl_value) if np.isfinite(usl_value) else None
        capability_metrics = compute_process_capability_metrics(lt, lsl=lsl_value, usl=usl_value)

        capability_table_data = []
        capability_msg = None
        if capability_metrics.get('error'):
            capability_msg = capability_metrics['error']
        else:
            capability_table_data = [
                {'Métrica': 'Amostra (n)', 'Valor': f"{capability_metrics['count']}"},
                {'Métrica': 'LSL', 'Valor': f"{capability_metrics['lsl']:.2f}"},
                {'Métrica': 'USL', 'Valor': f"{capability_metrics['usl']:.2f}"},
                {'Métrica': 'Média (x̄)', 'Valor': f"{capability_metrics['mean']:.2f}"},
                {'Métrica': 'Desvio padrão amostral (s)', 'Valor': f"{capability_metrics['std']:.4f}"},
                {'Métrica': 'CPU', 'Valor': f"{capability_metrics['cpu']:.4f}" if np.isfinite(capability_metrics['cpu']) else 'N/A'},
                {'Métrica': 'CPL', 'Valor': f"{capability_metrics['cpl']:.4f}" if np.isfinite(capability_metrics['cpl']) else 'N/A'},
                {'Métrica': 'Cpk', 'Valor': f"{capability_metrics['cpk']:.4f}"},
                {'Métrica': 'Nível Sigma (curto prazo = Cpk x 3)', 'Valor': f"{capability_metrics['sigma_short']:.3f}"},
                {'Métrica': 'Nível Sigma (longo prazo = Cpk x 3 - 1.5)', 'Valor': f"{capability_metrics['sigma_long']:.3f}"},
                {'Métrica': 'Interpretação', 'Valor': capability_metrics['quality']},
            ]

        capability_component = dash_table.DataTable(
            columns=[{"name": "Métrica", "id": "Métrica"}, {"name": "Valor", "id": "Valor"}],
            data=capability_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if capability_table_data else html.P(capability_msg or 'Sem dados para calcular Cpk e Nível Sigma.', style={'color': '#666'})

        lt_table_data = [{'Estatística': k, 'Valor': v} for k, v in lead_time_stats.items()]
        lt_table = dash_table.DataTable(
            columns=[{"name": "Estatística", "id": "Estatística"}, {"name": "Valor", "id": "Valor"}],
            data=lt_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if lt_table_data else html.P('Sem dados de Lead Time para o período selecionado.')

        # Gráficos de Lead Time
        fig_lt_hist = {}
        fig_lt_box = {}
        if not df_done_lt.empty:
            fig_lt_hist = px.histogram(df_done_lt, x=lead_col, nbins=30,
                                       title='Distribuição do Lead Time (dias)',
                                       labels={lead_col: 'Lead Time (dias)', 'count': 'Frequência'},
                                       height=500)
            lt_mean_val = lt_comparable_stats.get('mean', np.nan)
            lt_median_val = lt_comparable_stats.get('p50', np.nan)
            lt_p85_val = lt_comparable_stats.get('p85', np.nan)
            fig_lt_hist.add_vline(x=lt_mean_val, line_dash="dash", line_color="red", annotation_text=f"Média: {lt_mean_val:.1f}")
            fig_lt_hist.add_vline(x=lt_median_val, line_dash="dash", line_color="blue", annotation_text=f"Mediana: {lt_median_val:.1f}")
            fig_lt_hist.add_vline(x=lt_p85_val, line_dash="dash", line_color="orange", annotation_text=f"P85: {lt_p85_val:.1f}")

            fig_lt_box = px.box(df_done_lt, y=lead_col, title='Box Plot do Lead Time (dias)',
                                labels={lead_col: 'Lead Time (dias)'}, points='all', height=500)

        # --- 2. Estatísticas de Throughput (semanal) ---
        tp_weekly = df_done.copy()
        tp_weekly['_FilterDate'] = resolve_filter_date_series(tp_weekly, use_creation_date=use_creation_date)
        tp_weekly = tp_weekly.dropna(subset=['_FilterDate'])
        tp_weekly['Semana'] = weekly_bucket_start(tp_weekly['_FilterDate'])
        tp_weekly = tp_weekly.groupby('Semana').size().reset_index(name='Throughput')

        tp_stats = {}
        if not tp_weekly.empty:
            tp = tp_weekly['Throughput']
            tp_stats = {
                'Semanas Analisadas': int(len(tp)),
                'Total de Itens': int(tp.sum()),
                'Média / Semana': f"{tp.mean():.2f}",
                'Mediana / Semana': f"{tp.median():.2f}",
                'Desvio Padrão': f"{tp.std():.2f}",
                'Mínimo / Semana': int(tp.min()),
                'Máximo / Semana': int(tp.max()),
                'P25': f"{exact_empirical_percentile(tp, 0.25):.2f}",
                'P75': f"{exact_empirical_percentile(tp, 0.75):.2f}",
                'P85': f"{exact_empirical_percentile(tp, 0.85):.2f}",
                'P95': f"{exact_empirical_percentile(tp, 0.95):.2f}",
                'Coef. Variação (%)': f"{(tp.std() / tp.mean() * 100):.2f}" if tp.mean() > 0 else '—',
            }

        tp_table_data = [{'Estatística': k, 'Valor': str(v)} for k, v in tp_stats.items()]
        tp_table = dash_table.DataTable(
            columns=[{"name": "Estatística", "id": "Estatística"}, {"name": "Valor", "id": "Valor"}],
            data=tp_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if tp_table_data else html.P('Sem dados de Throughput para o período selecionado.')

        # Gráficos de Throughput
        fig_tp_hist = {}
        fig_tp_line = {}
        if not tp_weekly.empty:
            fig_tp_hist = px.histogram(tp_weekly, x='Throughput', nbins=15,
                                       title='Distribuição do Throughput Semanal',
                                       labels={'Throughput': 'Throughput (itens/semana)', 'count': 'Frequência'},
                                       height=500)
            tp_mean_val = tp_weekly['Throughput'].mean()
            fig_tp_hist.add_vline(x=tp_mean_val, line_dash="dash", line_color="red", annotation_text=f"Média: {tp_mean_val:.1f}")

            tp_weekly_sorted = tp_weekly.sort_values('Semana')
            fig_tp_line = px.bar(tp_weekly_sorted, x='Semana', y='Throughput',
                                 title='Throughput Semanal ao Longo do Tempo',
                                 labels={'Semana': 'Semana', 'Throughput': 'Itens Concluídos'},
                                 height=500)
            fig_tp_line.update_layout(xaxis_tickangle=-45, margin=dict(b=130))

        # --- 3. Estatísticas de WIP (semanal) ---
        weeks = pd.date_range(start=start_date_ts, end=end_date_ts, freq=WEEK_DATE_RANGE_FREQ)
        wip_weekly_values = []
        for week_end in weeks:
            wip_count = len(df_base[
                (df_base['DataInProgress'] <= week_end) &
                ((df_base['DataDone'] > week_end) | pd.isna(df_base['DataDone']))
            ])
            wip_weekly_values.append({'Semana': week_end, 'WIP': wip_count})
        wip_weekly_df = pd.DataFrame(wip_weekly_values)

        wip_stats = {}
        if not wip_weekly_df.empty and len(wip_weekly_df) > 0:
            w = wip_weekly_df['WIP']
            wip_stats = {
                'Semanas Analisadas': int(len(w)),
                'Média': f"{w.mean():.2f}",
                'Mediana': f"{w.median():.2f}",
                'Desvio Padrão': f"{w.std():.2f}",
                'Mínimo': int(w.min()),
                'Máximo': int(w.max()),
                'P25': f"{exact_empirical_percentile(w, 0.25):.2f}",
                'P75': f"{exact_empirical_percentile(w, 0.75):.2f}",
                'P85': f"{exact_empirical_percentile(w, 0.85):.2f}",
                'P95': f"{exact_empirical_percentile(w, 0.95):.2f}",
                'Coef. Variação (%)': f"{(w.std() / w.mean() * 100):.2f}" if w.mean() > 0 else '—',
                'WIP Atual (última semana)': int(w.iloc[-1]) if len(w) > 0 else '—',
            }

        wip_table_data = [{'Estatística': k, 'Valor': str(v)} for k, v in wip_stats.items()]
        wip_table = dash_table.DataTable(
            columns=[{"name": "Estatística", "id": "Estatística"}, {"name": "Valor", "id": "Valor"}],
            data=wip_table_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
        ) if wip_table_data else html.P('Sem dados de WIP para o período selecionado.')

        # Gráficos de WIP
        fig_wip_line = {}
        fig_wip_hist = {}
        if not wip_weekly_df.empty:
            fig_wip_line = px.line(wip_weekly_df, x='Semana', y='WIP',
                                   title='WIP Semanal ao Longo do Tempo', markers=True, height=500)
            fig_wip_line.update_layout(xaxis_tickangle=-45, margin=dict(b=130))
            fig_wip_hist = px.histogram(wip_weekly_df, x='WIP', nbins=15,
                                        title='Distribuição do WIP Semanal',
                                        labels={'WIP': 'WIP (itens)', 'count': 'Frequência'},
                                        height=500)

        # --- Layout da aba ---
        filtro_info = (
            f"Projeto: {projeto or 'Todos'} | "
            f"Tipo: {tipo or 'Todos'} | "
            f"Tipo original Jira: {format_original_jira_type_filter_label(tipo_original_jira)}"
        )
        comparativo_lead_info = (
            f"Lead Time comparável à aba 'Lead Time' | "
            f"Amostra: {int(lt_comparable_stats.get('count', 0))} | "
            f"Média: {float(lt_comparable_stats.get('mean', np.nan)):.2f} | "
            f"P50: {float(lt_comparable_stats.get('p50', np.nan)):.2f} | "
            f"P85: {float(lt_comparable_stats.get('p85', np.nan)):.2f}"
            if lt_comparable_stats else
            "Lead Time comparável à aba 'Lead Time' | Sem amostra válida no recorte."
        )

        return html.Div([
            html.H3("Estatística Descritiva", style={'textAlign': 'center'}),
            html.P(filtro_info, style={'textAlign': 'center', 'color': '#666', 'marginBottom': '30px'}),
            html.P(comparativo_lead_info, style={'textAlign': 'center', 'color': '#666', 'marginTop': '-20px', 'marginBottom': '20px'}),

            # Cpk / Six Sigma
            html.H4("Capabilidade do Processo (Cpk e Nível Sigma)", style={'textAlign': 'center', 'marginTop': '20px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.P(
                "Informe os limites de especificação do cliente (LSL e USL) para calcular CPU, CPL, Cpk e nível sigma.",
                style={'textAlign': 'center', 'color': '#666', 'marginBottom': '14px'}
            ),
            html.Div([
                html.Div([
                    html.Label("LSL (Limite Inferior):", style={'fontWeight': 'bold'}),
                    dcc.Input(
                        id='estatistica-lsl',
                        type='number',
                        value=lsl_input_value,
                        debounce=True,
                        placeholder='Ex.: 9.7',
                        style={'width': '160px'}
                    ),
                ], style={'display': 'inline-flex', 'alignItems': 'center', 'gap': '8px', 'marginRight': '20px'}),
                html.Div([
                    html.Label("USL (Limite Superior):", style={'fontWeight': 'bold'}),
                    dcc.Input(
                        id='estatistica-usl',
                        type='number',
                        value=usl_input_value,
                        debounce=True,
                        placeholder='Ex.: 10.3',
                        style={'width': '160px'}
                    ),
                ], style={'display': 'inline-flex', 'alignItems': 'center', 'gap': '8px'}),
            ], style={'textAlign': 'center', 'marginBottom': '14px'}),
            html.Div(capability_component, style={'width': '60%', 'margin': '0 auto'}),
            html.P(
                "Premissa: distribuição aproximadamente normal. Para processo não normal ou dados binários, use abordagem específica por yield/PPM.",
                style={'textAlign': 'center', 'color': '#666', 'fontSize': '12px', 'marginTop': '10px'}
            ),

            # Lead Time
            html.H4("Lead Time (dias)", style={'textAlign': 'center', 'marginTop': '30px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.Div([
                html.Div(lt_table, className='five columns', style={'padding': '10px'}),
                html.Div([
                    dcc.Graph(figure=fig_lt_hist),
                    dcc.Graph(figure=fig_lt_box),
                ], className='seven columns'),
            ], className='row'),

            # Throughput
            html.H4("Throughput (semanal)", style={'textAlign': 'center', 'marginTop': '40px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.Div([
                html.Div(tp_table, className='five columns', style={'padding': '10px'}),
                html.Div([
                    dcc.Graph(figure=fig_tp_hist),
                    dcc.Graph(figure=fig_tp_line),
                ], className='seven columns'),
            ], className='row'),

            # WIP
            html.H4("WIP - Work in Progress (semanal)", style={'textAlign': 'center', 'marginTop': '40px', 'borderBottom': '2px solid #ddd', 'paddingBottom': '10px'}),
            html.Div([
                html.Div(wip_table, className='five columns', style={'padding': '10px'}),
                html.Div([
                    dcc.Graph(figure=fig_wip_line),
                    dcc.Graph(figure=fig_wip_hist),
                ], className='seven columns'),
            ], className='row'),
        ])

    if tab == 'tab-fila-capacidade':
        start_date_ts = pd.to_datetime(start_date)
        end_date_ts = pd.to_datetime(end_date)

        # Base para cálculo de capacidade com as mesmas regras do One Page:
        # chegada por LeadStart_Selected e vazão por itens concluídos elegíveis.
        df_capacity_base = df.copy()

        lead_start_col = 'LeadStart_Selected' if 'LeadStart_Selected' in df_capacity_base.columns else 'DataInProgress'
        lead_start_series = pd.to_datetime(df_capacity_base.get(lead_start_col), errors='coerce')
        done_series = pd.to_datetime(df_capacity_base.get('DataDone'), errors='coerce')
        done_eligible_mask = done_time_eligible_mask(df_capacity_base)

        weeks = pd.date_range(start=start_date_ts, end=end_date_ts + pd.Timedelta(days=7), freq='W-MON')
        if len(weeks) < 2:
            return html.Div('Período muito curto para análise semanal de capacidade de fila.')

        weekly_rows = []
        for i in range(len(weeks) - 1):
            week_start = weeks[i]
            week_end = weeks[i + 1]
            arrivals = int(((lead_start_series >= week_start) & (lead_start_series < week_end)).sum())
            throughput = int(((done_series >= week_start) & (done_series < week_end) & done_eligible_mask).sum())
            weekly_rows.append({
                'Semana': str(week_start.date()),
                'Chegadas': arrivals,
                'Throughput': throughput,
            })

        weekly_df = pd.DataFrame(weekly_rows)
        n_weeks = len(weekly_df)
        lambda_base = weekly_df['Chegadas'].mean() if n_weeks > 0 else 0.0
        mu = weekly_df['Throughput'].mean() if n_weeks > 0 else 0.0
        lambda_stress = lambda_base * 1.18

        if mu <= 0:
            return html.Div('Não há throughput suficiente no período para calcular capacidade de fila (μ = 0).')

        base = calculate_mm1_metrics(lambda_base, mu)
        stress = calculate_mm1_metrics(lambda_stress, mu)
        if base is None or stress is None:
            return html.Div('Não foi possível calcular métricas de fila com os dados selecionados.')

        lq_growth_pct = ((stress['Lq'] - base['Lq']) / base['Lq']) * 100 if np.isfinite(base['Lq']) and base['Lq'] > 0 else np.nan
        w_growth_pct = ((stress['W'] - base['W']) / base['W']) * 100 if np.isfinite(base['W']) and base['W'] > 0 else np.nan
        arrival_growth_pct = ((lambda_stress - lambda_base) / lambda_base) * 100 if lambda_base > 0 else np.nan

        def fmt_metric_value(value, unit=''):
            if value is None or (isinstance(value, float) and not np.isfinite(value)):
                return 'Sistema instável (ρ >= 1)'
            return f"{value:.2f}{unit}"

        period_label = f"{start_date_ts.date()} a {end_date_ts.date()}"
        _, efficiency = calculate_flow_efficiency(base['lambda'], base['mu'])
        kpi_data = [
            {'Métrica': 'Período analisado', 'Valor': period_label},
            {'Métrica': 'Semanas analisadas', 'Valor': f"{n_weeks}"},
            {'Métrica': 'Taxa de chegada média (λ)', 'Valor': f"{base['lambda']:.2f} tarefas/semana"},
            {'Métrica': 'Taxa de vazão média (μ)', 'Valor': f"{base['mu']:.2f} tarefas/semana"},
            {'Métrica': 'Utilização (ρ)', 'Valor': fmt_metric_value(base['rho'])},
            {'Métrica': 'Eficiência (1 - ρ)', 'Valor': fmt_metric_value(efficiency)},
            {'Métrica': 'Lq - fila média', 'Valor': fmt_metric_value(base['Lq'], ' tarefas')},
            {'Métrica': 'Wq - espera média na fila', 'Valor': fmt_metric_value(base['Wq'], ' semanas')},
            {'Métrica': 'W - tempo total no sistema', 'Valor': fmt_metric_value(base['W'], ' semanas')},
            {'Métrica': 'Cenário de estresse (+18% em λ)', 'Valor': f"{arrival_growth_pct:.1f}%"},
            {'Métrica': 'Lq no estresse', 'Valor': fmt_metric_value(stress['Lq'], ' tarefas')},
            {'Métrica': 'W no estresse', 'Valor': fmt_metric_value(stress['W'], ' semanas')},
            {'Métrica': 'Aumento de fila (Lq)', 'Valor': f"{lq_growth_pct:.0f}%" if np.isfinite(lq_growth_pct) else 'N/A'},
            {'Métrica': 'Aumento de tempo total (W)', 'Valor': f"{w_growth_pct:.0f}%" if np.isfinite(w_growth_pct) else 'N/A'},
        ]
        kpi_table = dash_table.DataTable(
            columns=[{"name": i, "id": i} for i in ['Métrica', 'Valor']],
            data=kpi_data,
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        scenario_df = pd.DataFrame([
            {
                'Cenário': 'Base',
                'λ': base['lambda'],
                'μ': base['mu'],
                'ρ': round(base['rho'], 2),
                'Lq (tarefas)': round(base['Lq'], 2) if np.isfinite(base['Lq']) else 'Instável',
                'Wq (semanas)': round(base['Wq'], 2) if np.isfinite(base['Wq']) else 'Instável',
                'W (semanas)': round(base['W'], 2) if np.isfinite(base['W']) else 'Instável',
            },
            {
                'Cenário': 'Aumento de demanda (+18%)',
                'λ': stress['lambda'],
                'μ': stress['mu'],
                'ρ': round(stress['rho'], 2),
                'Lq (tarefas)': round(stress['Lq'], 2) if np.isfinite(stress['Lq']) else 'Instável',
                'Wq (semanas)': round(stress['Wq'], 2) if np.isfinite(stress['Wq']) else 'Instável',
                'W (semanas)': round(stress['W'], 2) if np.isfinite(stress['W']) else 'Instável',
            },
        ])
        scenario_table = dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in scenario_df.columns],
            data=scenario_df.to_dict('records'),
            style_cell={'textAlign': 'center', 'padding': '8px'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        )

        rho_series = np.linspace(0.50, 0.98, 49)
        lambda_series = rho_series * mu
        lq_series = (rho_series ** 2) / (1 - rho_series)
        w_series = (lq_series / lambda_series) + (1 / mu)

        fig_queue = make_subplots(specs=[[{"secondary_y": True}]])
        fig_queue.add_trace(
            go.Scatter(x=rho_series, y=w_series, mode='lines', name='W - Tempo total (semanas)', line=dict(color='royalblue', width=3)),
            secondary_y=False
        )
        fig_queue.add_trace(
            go.Scatter(x=rho_series, y=lq_series, mode='lines', name='Lq - Fila média (tarefas)', line=dict(color='firebrick', width=3)),
            secondary_y=True
        )
        fig_queue.add_vline(x=0.8, line_dash='dash', line_color='orange')
        fig_queue.add_vline(x=0.9, line_dash='dash', line_color='red')
        fig_queue.add_annotation(x=0.72, y=max(w_series) * 0.15, text='Baixa utilização (ρ < 0.8)', showarrow=False)
        fig_queue.add_annotation(x=0.84, y=max(w_series) * 0.35, text='Intermediária (ρ = 0.8)', showarrow=False)
        fig_queue.add_annotation(x=0.93, y=max(w_series) * 0.70, text='Alta utilização (ρ > 0.9)', showarrow=False)
        fig_queue.update_layout(
            title='Sensibilidade do Sistema à Utilização (Modelo M/M/1)',
            height=580,
            template='plotly_white',
            xaxis_title='Taxa de Utilização (ρ)',
            margin=dict(t=60, b=50),
        )
        fig_queue.update_yaxes(title_text='W - Tempo total no sistema (semanas)', secondary_y=False)
        fig_queue.update_yaxes(title_text='Lq - Comprimento médio da fila (tarefas)', secondary_y=True)

        insight_block = html.Div([
            html.H4("Mensagem de Gestão", style={'marginBottom': '10px'}),
            html.P('"Ah, é só mais uma demanda..." parece pequeno, mas o impacto é exponencial quando ρ se aproxima de 1.'),
            html.P('Associe custo financeiro às demandas na fila para evidenciar o custo de atraso no sistema.'),
        ], style={'padding': '14px', 'backgroundColor': '#f9f9f9', 'border': '1px solid #e0e0e0', 'borderRadius': '8px'})

        return html.Div([
            html.H3("Capacidade de Fila e Impacto de Utilização", style={'textAlign': 'center'}),
            html.P("Modelo M/M/1 com taxas calculadas a partir dos dados importados e filtros ativos.",
                   style={'textAlign': 'center', 'color': '#666'}),
            html.Div(kpi_table, style={'width': '62%', 'margin': '20px auto'}),
            html.H4("Comparação de Cenários", style={'textAlign': 'center', 'marginTop': '24px'}),
            scenario_table,
            dcc.Graph(figure=fig_queue),
            insight_block,
        ])

    # ─── Produtividade Dev ─────────────────────────────────────────────────────
    if tab == 'tab-produtividade-dev':
        start_ts_prod = pd.to_datetime(start_date)
        end_ts_prod = pd.to_datetime(end_date)

        df_prod_base = df.copy()
        df_prod_monthly_base = filter_df(
            fato,
            None,
            None,
            projeto,
            tipo,
            classe_servico,
            responsavel,
            criadores=criadores,
            use_creation_date=use_creation_date,
            apply_date=False,
            tipo_original=tipo_original_jira,
        )

        contributor_section = build_bitbucket_contributor_section(
            projeto,
            start_ts_prod,
            end_ts_prod,
            jira_df=df_prod_base if not df_prod_base.empty else None,
            top_n_people=capacity_top_n,
            weekly_metric=capacity_weekly_metric,
        )

        team_seed_df = _project_team_seed_df(projeto)
        complexity_df = pd.DataFrame()
        category_df = pd.DataFrame()
        if df_prod_base.empty or 'Responsavel' not in df_prod_base.columns:
            per_dev = team_seed_df.copy()
            if per_dev.empty:
                return html.Div([
                    html.Div('Sem dados de responsável disponíveis para o período e filtros selecionados.',
                             style={'padding': '30px', 'textAlign': 'center', 'color': '#888'}),
                    html.Div([
                        html.H4('Contribuições Bitbucket e Capacidade Cruzada', style={'marginBottom': '10px'}),
                        contributor_section,
                    ], style={'padding': '0 20px 20px 20px'}),
                ])
        else:
            per_dev, complexity_df, category_df = build_dev_productivity_metrics(df_prod_base, start_ts_prod, end_ts_prod)
            if not team_seed_df.empty:
                existing_people = per_dev['Pessoa'].tolist() if 'Pessoa' in per_dev.columns else []
                _missing_mask = team_seed_df['Pessoa'].apply(
                    lambda seed_person: not any(_person_names_compatible(seed_person, existing_person) for existing_person in existing_people)
                )
                _missing_team = team_seed_df[_missing_mask]
                if not _missing_team.empty:
                    per_dev = pd.concat([per_dev, _missing_team], ignore_index=True, sort=False)
            if per_dev.empty:
                return html.Div([
                    html.Div('Sem dados de produtividade individual para o período selecionado.',
                             style={'padding': '30px', 'textAlign': 'center', 'color': '#888'}),
                    html.Div([
                        html.H4('Contribuições Bitbucket e Capacidade Cruzada', style={'marginBottom': '10px'}),
                        contributor_section,
                    ], style={'padding': '0 20px 20px 20px'}),
                ])
        per_dev = _ensure_dev_productivity_columns(per_dev)

        # Enriquecer com métricas do Bitbucket
        # W1NNER e S1NC compartilham o mesmo repositório; a BU (people_config.json) separa os times
        alias_index_prod = _load_person_alias_index()
        bu_index_prod = _load_person_bu_map()
        pm_item_person_map = _build_dev_item_person_map(df_prod_base, alias_index=alias_index_prod)

        def _load_bb_for_projects(projects: list[str]) -> tuple[pd.DataFrame, dict]:
            """Carrega Bitbucket de um ou mais projetos e consolida sobre logs crus."""
            env_map = _load_bitbucket_prefix_map()
            loaded_prefixes = set()
            combined_logs = {'commits': [], 'pullrequests': [], 'pipelines': []}
            for proj in projects:
                project_key = str(proj or '').strip().upper()
                prefix = env_map.get(project_key) or PROJECT_BITBUCKET_PREFIX.get(project_key)
                if prefix and prefix in loaded_prefixes:
                    continue
                if prefix:
                    loaded_prefixes.add(prefix)
                logs = load_project_bitbucket_logs(proj)
                if not isinstance(logs, dict):
                    continue
                for log_name in ['commits', 'pullrequests', 'pipelines']:
                    df_log = logs.get(log_name, pd.DataFrame())
                    if df_log is not None and not df_log.empty:
                        combined_logs[log_name].append(df_log.copy())
            if not any(combined_logs.values()):
                return pd.DataFrame(), {}
            merged_logs = {
                log_name: pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                for log_name, frames in combined_logs.items()
            }
            return compute_bitbucket_contributor_metrics(
                merged_logs, start_ts_prod, end_ts_prod, alias_index=alias_index_prod
            )

        # Decide quais projetos carregar para Bitbucket
        # W1NNER e S1NC estão no mesmo repo (w1nner), então basta um dos dois
        if projeto:
            bb_projects = [projeto]
            # Se o projeto selecionado cobre W1NNER ou S1NC, inclui ambos para não perder nenhum
            if str(projeto).upper() in {'W1NNR', 'W1NNER', 'S1NC', 'W1SFT'}:
                bb_projects = ['W1NNER', 'S1NC']
        else:
            bb_projects = ['W1NNER', 'S1NC', 'BEFINANCE', 'DATA&ANALYTICS']

        bb_df_prod, _ = _load_bb_for_projects(bb_projects)

        if not bb_df_prod.empty and 'Pessoa' in bb_df_prod.columns:
            bb_cols_available = [c for c in ['Pessoa', 'Commits', 'PRs Abertos', 'PRs Merged', 'PRs Declinados (Autor)', 'Aprovacoes', 'Reprovacoes', 'Devs Revisados'] if c in bb_df_prod.columns]
            # Enriquece BU nos dados Bitbucket para herdar da config de pessoas
            bb_df_prod['BU'] = bb_df_prod['Pessoa'].apply(lambda p: _person_bu(p, bu_index=bu_index_prod))
            per_dev = pd.merge(per_dev, bb_df_prod[bb_cols_available], on='Pessoa', how='left')

        for col in ['Commits', 'PRs Abertos', 'PRs Merged', 'PRs Declinados (Autor)', 'Aprovacoes', 'Reprovacoes', 'Devs Revisados']:
            if col not in per_dev.columns:
                per_dev[col] = 0
            per_dev[col] = pd.to_numeric(per_dev[col], errors='coerce').fillna(0).astype(int)

        # ── Métricas de Process Mining (qualidade + retorno para desenvolvimento) ──
        pm_case_frames = []
        pm_event_frames = []
        pm_dev_item_frames = []
        pm_dev_return_frames = []
        for _pm_proj in bb_projects:
            _case_df = load_project_pm_case_df(_pm_proj)
            if not _case_df.empty:
                pm_case_frames.append(_case_df)
            _dev_item_df = load_project_pm_sheet(_pm_proj, 'DevFlowItens')
            if not _dev_item_df.empty:
                pm_dev_item_frames.append(_dev_item_df)
            _dev_return_df = load_project_pm_sheet(_pm_proj, 'DevFlowRetornos')
            if not _dev_return_df.empty:
                pm_dev_return_frames.append(_dev_return_df)
            _events_df = load_project_pm_sheet(_pm_proj, 'EventosFiltrados')
            if not _events_df.empty:
                pm_event_frames.append(_events_df)

        pm_event_combined = pd.concat(pm_event_frames, ignore_index=True) if pm_event_frames else pd.DataFrame()
        pm_flow_item_combined = pd.concat(pm_dev_item_frames, ignore_index=True) if pm_dev_item_frames else pd.DataFrame()
        pm_flow_return_combined = pd.concat(pm_dev_return_frames, ignore_index=True) if pm_dev_return_frames else pd.DataFrame()
        pm_dev_return_report = pd.DataFrame()

        if pm_case_frames:
            pm_case_combined = pd.concat(pm_case_frames, ignore_index=True)
            pm_combined = compute_pm_dev_metrics(
                pm_case_combined,
                start_ts_prod,
                end_ts_prod,
                alias_index=alias_index_prod,
                item_person_map=pm_item_person_map,
            )
            if not pm_combined.empty and 'Pessoa' in pm_combined.columns:
                _pm_num_cols = [c for c in ['Conformance Quality (%)', 'Rework Rate PM (%)', 'QA Return Rate (%)', 'Complexidade Variante'] if c in pm_combined.columns]
                for c in _pm_num_cols:
                    pm_combined[c] = pd.to_numeric(pm_combined[c], errors='coerce').round(1)
                per_dev = pd.merge(per_dev, pm_combined, on='Pessoa', how='left')

        pm_flow_metrics = compute_pm_dev_flow_metrics(
            pm_flow_item_combined,
            pm_flow_return_combined,
            start_ts_prod,
            end_ts_prod,
            alias_index=alias_index_prod,
            item_person_map=pm_item_person_map,
            events_df=pm_event_combined if not pm_event_combined.empty else None,
        )
        if not pm_flow_metrics.empty and 'Pessoa' in pm_flow_metrics.columns:
            per_dev = pd.merge(per_dev, pm_flow_metrics, on='Pessoa', how='left')

        # ── Recomputa Itens Entregues usando saída de In Progress como fonte ──
        # Substitui a contagem baseada em Done Final Author pela contagem de quando
        # o dev moveu o card de In Progress → Code Review / QA, refletindo a entrega
        # real do desenvolvedor independente de quem faz o deploy/done final.
        # Fallback automático para done_window quando DevFlowItens não cobre o dev.
        if not pm_flow_item_combined.empty or not pm_event_combined.empty:
            per_dev = _recompute_itens_entregues_from_dev_flow(
                per_dev,
                pm_flow_item_combined,
                df_prod_base,
                alias_index_prod,
                start_ts_prod,
                end_ts_prod,
                events_df=pm_event_combined if not pm_event_combined.empty else None,
            )

        pm_dev_return_report = build_pm_dev_return_report(
            pm_flow_item_combined,
            pm_flow_return_combined,
            item_person_map=pm_item_person_map,
            events_df=pm_event_combined if not pm_event_combined.empty else None,
        )

        for col in ['Conformance Quality (%)', 'Rework Rate PM (%)', 'Rework Score Total', 'Rework Score Médio',
                    'QA Return Rate (%)', 'Complexidade Variante',
                    'Cycle Time Dev Mediano (dias)', 'Cycle Time Dev Médio (dias)',
                    'Tempo Retorno QA->Dev Mediano (dias)', 'Tempo Retorno QA->Dev Total (dias)',
                    '% Cards com Retorno QA->Dev']:
            if col not in per_dev.columns:
                per_dev[col] = np.nan
            per_dev[col] = pd.to_numeric(per_dev[col], errors='coerce')
        for col in ['Retornos QA->Dev', 'Cards com Retorno QA->Dev']:
            if col not in per_dev.columns:
                per_dev[col] = 0
            per_dev[col] = pd.to_numeric(per_dev[col], errors='coerce').fillna(0).astype(int)

        # ── Pipeline Success Rate (Bitbucket pipelines × commits) ──────────────
        pip_df = compute_pipeline_success_rate(bb_projects, start_ts_prod, end_ts_prod, alias_index=alias_index_prod)
        if not pip_df.empty and 'Pessoa' in pip_df.columns:
            per_dev = pd.merge(per_dev, pip_df[['Pessoa', 'Pipeline Success Rate (%)', 'Pipelines Total']], on='Pessoa', how='left')
        for col in ['Pipeline Success Rate (%)', 'Pipelines Total']:
            if col not in per_dev.columns:
                per_dev[col] = np.nan
            per_dev[col] = pd.to_numeric(per_dev[col], errors='coerce')

        # ── Bottleneck Contribution (horas em status de gargalo por dev) ────────
        _bnk_df = compute_pm_bottleneck_contribution(bb_projects, alias_index=alias_index_prod)
        _gargalo_label = _bnk_df.attrs.get('gargalo_label', '') if not _bnk_df.empty else ''
        if not _bnk_df.empty and 'Pessoa' in _bnk_df.columns:
            _bnk_merge_cols = ['Pessoa'] + [c for c in ['HorasNoFluxo Total', 'Média H/Evento', 'Horas em Gargalo', '% Horas em Gargalo'] if c in _bnk_df.columns]
            per_dev = pd.merge(per_dev, _bnk_df[_bnk_merge_cols], on='Pessoa', how='left')
        for col in ['HorasNoFluxo Total', 'Média H/Evento', 'Horas em Gargalo', '% Horas em Gargalo']:
            if col not in per_dev.columns:
                per_dev[col] = np.nan
            per_dev[col] = pd.to_numeric(per_dev[col], errors='coerce')

        # Indicador de colaboração real: qualidade de revisão = aprovações / total revisões
        per_dev['Total Revisoes'] = per_dev['Aprovacoes'] + per_dev['Reprovacoes']
        per_dev['Qualidade Revisao'] = np.where(
            per_dev['Total Revisoes'] > 0,
            (per_dev['Aprovacoes'] / per_dev['Total Revisoes'] * 100).round(1),
            0.0,
        )

        per_dev = per_dev.sort_values(
            ['Itens Entregues', 'Score Complexidade', 'Pessoa'],
            ascending=[False, False, True],
        ).reset_index(drop=True)

        # ── Índice de Entrega do Desenvolvedor (IED) ──────────────────────────
        # Computa após todos os enriquecimentos; usa Score Complexidade Puxado
        # para a taxa de conclusão (EEE) e Lead Time para velocidade (VEL).
        per_dev = _compute_ied(per_dev)

        # ── Índice de Entrega Focado (IEF = 0.70×NDS + 0.30×EEE) ─────────────
        # Foco exclusivo em volume de entrega ajustado por complexidade e taxa de
        # conclusão do trabalho comprometido — sem penalização de velocidade ou qualidade.
        # EEE é capped em 100: entrega acima do comprometido não infla o índice.
        if '_ied_nds' in per_dev.columns and '_ied_eee' in per_dev.columns:
            per_dev['IEF'] = (
                per_dev['_ied_nds'] * 0.70 +
                per_dev['_ied_eee'].clip(0, 100) * 0.30
            ).round(1)
            per_dev.loc[per_dev['Itens Entregues'] == 0, 'IEF'] = 0.0
        else:
            per_dev['IEF'] = 0.0

        def _ief_classe(v):
            if v >= 85: return 'Excelente'
            if v >= 70: return 'Bom'
            if v >= 50: return 'Regular'
            if v >= 30: return 'Abaixo do Esperado'
            return 'Crítico'
        per_dev['IEF Classe'] = per_dev['IEF'].apply(_ief_classe)

        # ── IEF Ajustado — fator de confiança via ECR ─────────────────────────
        # Quando estimativas são majoritariamente inferidas (ECR baixo), o IEF é baseado
        # em pesos de complexidade não confiáveis. O fator (0.5 + 0.5×ECR) aplica um
        # desconto suave: ECR=100% → sem desconto; ECR=50% → IEF×0.75; ECR=0% → IEF×0.50.
        # Fonte: Kitchenham & Mendes (TSE 2004) — estimativa como pré-requisito de comparabilidade.
        if 'ECR' in per_dev.columns:
            _ecr_norm = pd.to_numeric(per_dev['ECR'], errors='coerce').fillna(100.0).clip(0, 100) / 100.0
            _ief_conf_factor = (0.5 + 0.5 * _ecr_norm)
            per_dev['IEF Ajustado'] = (per_dev['IEF'] * _ief_conf_factor).round(1)
            per_dev['IEF Confiança (%)'] = (_ief_conf_factor * 100).round(0).astype(int)
        else:
            per_dev['IEF Ajustado'] = per_dev['IEF']
            per_dev['IEF Confiança (%)'] = 100

        per_dev['IEF Ajustado Classe'] = per_dev['IEF Ajustado'].apply(_ief_classe)

        # ── Divergência IEF–IED: sinal diagnóstico ────────────────────────────
        # IEF captura só volume+conclusão; IED penaliza também VEL e QUA.
        # Δ alto (>15) sinaliza que velocidade ou qualidade estão puxando o IED para baixo.
        # Fonte: separação analítica inspirada em Forsgren et al. (SPACE, ACM Queue 2021).
        if 'IEF' in per_dev.columns and 'IED' in per_dev.columns:
            per_dev['Δ IEF–IED'] = (per_dev['IEF'] - per_dev['IED']).abs().round(1)
        else:
            per_dev['Δ IEF–IED'] = 0.0

        # ── Novos Indicadores ────────────────────────────────────────────────────
        # DD/FP — Defect Density por Function Point (Capers Jones / Namcook Analytics, IFPUG 2017)
        # Benchmarks: Excelente <0.10 | Bom 0.10–0.30 | Médio 0.30–0.60 | Crítico >0.60
        per_dev['DD_FP'] = (
            pd.to_numeric(per_dev['Defeitos Entregues'], errors='coerce').fillna(0) /
            pd.to_numeric(per_dev['Score Complexidade'], errors='coerce').fillna(1).clip(lower=0.1)
        ).round(3)

        # KCR — Knowledge Concentration Risk (Ricca et al., ICSE 2019 — Truck Factor)
        # KCR > 40% = dev concentra >40% da produção técnica → risco de bus factor
        _total_commits_kpi = max(int(per_dev['Commits'].sum()), 1)
        per_dev['KCR'] = (per_dev['Commits'] / _total_commits_kpi * 100).round(1)

        # Estabilidade de Throughput — (1 − CV_semanal) × 100
        # CV = desvio_padrão / média do throughput semanal (itens concluídos/semana)
        # Benchmark: Estabilidade ≥70 → previsível (CV ≤ 0.5) (Anderson 2010; Magennis 2016)
        _done_cv = df_prod_base.copy()
        _done_cv['_Pessoa'] = _resolve_dev_person_series(_done_cv, alias_index=alias_index_prod)
        if 'DataDone' in _done_cv.columns:
            _done_cv['DataDone'] = pd.to_datetime(_done_cv['DataDone'], errors='coerce')
            _done_cv = _done_cv[
                (_done_cv['DataDone'] >= start_ts_prod) &
                (_done_cv['DataDone'] < end_ts_prod) &
                _done_cv['_Pessoa'].astype(str).str.strip().ne('')
            ]
            if not _done_cv.empty:
                _done_cv['_week'] = _done_cv['DataDone'].dt.to_period('W')
                _weekly_tp = _done_cv.groupby(['_Pessoa', '_week']).size().reset_index(name='_cnt')
                def _stability(dev):
                    s = _weekly_tp[_weekly_tp['_Pessoa'] == dev]['_cnt']
                    if len(s) < 2:
                        return 100.0
                    return float(np.clip((1.0 - float(s.std()) / max(float(s.mean()), 0.01)) * 100.0, 0.0, 100.0))
                per_dev['Estabilidade_Throughput'] = per_dev['Pessoa'].apply(_stability).round(1)
            else:
                per_dev['Estabilidade_Throughput'] = 100.0
        else:
            per_dev['Estabilidade_Throughput'] = 100.0

        # ── P85/P50 Lead Time ratio — previsibilidade de entrega ─────────────────
        # Razão P85/P50: ≤2.0 = Previsível | ≤3.0 = Moderado | >3.0 = Imprevisível
        # Referência: Reinertsen (2009) — "The Principles of Product Development Flow"
        if 'Lead Time P50 (dias)' in per_dev.columns and 'Lead Time P85 (dias)' in per_dev.columns:
            _p50_safe = per_dev['Lead Time P50 (dias)'].clip(lower=0.1)
            per_dev['Razão P85/P50'] = (per_dev['Lead Time P85 (dias)'] / _p50_safe).round(2)
            per_dev['Previsibilidade LT'] = per_dev['Razão P85/P50'].apply(
                lambda r: 'Previsível'   if pd.notna(r) and r <= 2.0 else
                          'Moderado'     if pd.notna(r) and r <= 3.0 else
                          'Imprevisível'
            )
            # Devs sem Lead Time (zero entregas) ficam com NaN
            _no_lt_mask = per_dev['Lead Time P50 (dias)'] == 0
            per_dev.loc[_no_lt_mask, 'Razão P85/P50'] = np.nan
            per_dev.loc[_no_lt_mask, 'Previsibilidade LT'] = '—'
        else:
            per_dev['Razão P85/P50'] = np.nan
            per_dev['Previsibilidade LT'] = '—'

        # ── WIP Médio por dev (Little's Law: WIP_avg = Throughput × CT_médio) ──
        # Usa apenas itens com DataInProgress dentro do período (cycle time puro).
        # Referência: Little (1961); Anderson (2010) Kanban — WIP e LT são co-dependentes.
        if 'DataDone' in df_prod_base.columns and 'DataInProgress' in df_prod_base.columns:
            _wm_df = df_prod_base.copy()
            _wm_df['_Pessoa'] = _resolve_dev_person_series(_wm_df, alias_index=alias_index_prod)
            _wm_df['DataDone'] = pd.to_datetime(_wm_df['DataDone'], errors='coerce')
            _wm_df['DataInProgress'] = pd.to_datetime(_wm_df['DataInProgress'], errors='coerce')
            _wm_done = _wm_df[
                (_wm_df['DataDone'] >= start_ts_prod) &
                (_wm_df['DataDone'] < end_ts_prod) &
                (_wm_df['DataInProgress'] >= start_ts_prod) &
                _wm_df['_Pessoa'].astype(str).str.strip().ne('')
            ].copy()
            _n_days_prod = max((end_ts_prod - start_ts_prod).days, 1)
            if not _wm_done.empty and 'LeadTime_Selected_Dias' in _wm_done.columns:
                _wm_done['_lt'] = pd.to_numeric(_wm_done['LeadTime_Selected_Dias'], errors='coerce')
                _wm_done = _wm_done[_wm_done['_lt'] > 0]
                _lt_mean_by_dev = _wm_done.groupby('_Pessoa')['_lt'].mean().rename('_lt_mean')
                _tp_by_dev = (_wm_done.groupby('_Pessoa').size() / _n_days_prod).rename('_tp_day')
                _wip_frame = pd.concat([_lt_mean_by_dev, _tp_by_dev], axis=1).reset_index()
                _wip_frame = _wip_frame.rename(columns={'_Pessoa': 'Pessoa'})
                _wip_frame['WIP Medio'] = (_wip_frame['_tp_day'] * _wip_frame['_lt_mean']).round(2)
                per_dev = per_dev.merge(_wip_frame[['Pessoa', 'WIP Medio']], on='Pessoa', how='left')
            else:
                per_dev['WIP Medio'] = np.nan
        else:
            per_dev['WIP Medio'] = np.nan
        per_dev['WIP Medio'] = pd.to_numeric(per_dev['WIP Medio'], errors='coerce')

        # ── IED Temporal — sparklines mensais por dev ─────────────────────────
        # Só computa se o período tiver ao menos 2 meses (caso contrário sem tendência).
        _n_meses_period = (end_ts_prod - start_ts_prod).days / 30.44

        def _has_monthly_trend_points(monthly_data):
            return any(len(points) >= 2 for points in monthly_data.values())

        _monthly_ied_data = {}
        if _n_meses_period >= 1.8:
            try:
                _monthly_ied_data = _compute_monthly_ied_series(
                    df_prod_monthly_base, start_ts_prod, end_ts_prod,
                    alias_index=alias_index_prod,
                )
                # Mantém a régua stricter de 2 itens/mês como padrão, mas evita
                # "falso vazio" quando o usuário foca em um dev/time de baixo volume.
                if not _has_monthly_trend_points(_monthly_ied_data):
                    _monthly_ied_data = _compute_monthly_ied_series(
                        df_prod_monthly_base, start_ts_prod, end_ts_prod,
                        alias_index=alias_index_prod,
                        min_items_per_month=1,
                    )
            except Exception:
                _monthly_ied_data = {}

        # ── Δ IED Trend — variação IED (primeiro → último mês com dados) ──────
        # Positivo = dev melhorando; Negativo = dev em queda; NaN = dados insuficientes
        def _ied_trend_delta(pessoa):
            pts = _monthly_ied_data.get(str(pessoa), [])
            if len(pts) >= 2:
                return round(pts[-1][1] - pts[0][1], 1)
            return np.nan
        per_dev['Δ IED Trend'] = per_dev['Pessoa'].apply(_ied_trend_delta)

        # ── IED Seta — tendência visual ↑↓→ ──────────────────────────────────
        # Δ > 5 = melhora significativa ↑ | Δ < -5 = queda significativa ↓ | |Δ| ≤ 5 = estável →
        def _ied_seta(delta):
            if pd.isna(delta):
                return '—'
            if delta > 5:
                return '↑'
            if delta < -5:
                return '↓'
            return '→'
        per_dev['IED Seta'] = per_dev['Δ IED Trend'].apply(_ied_seta)

        # ── Tendência mensal do ECR — confiabilidade de estimativa ───────────
        # ECR = % de itens puxados com estimativa real (não inferida).
        # Meta gerencial: ECR ≥ 80% em 3 meses consecutivos => dev maduro em estimativa.
        _ECR_MATURITY_THRESHOLD = 80.0
        _ECR_MATURITY_STREAK = 3
        _monthly_ecr_data = {}
        if _n_meses_period >= 0.8:
            try:
                _monthly_ecr_data = _compute_monthly_ecr_series(
                    df_prod_monthly_base, start_ts_prod, end_ts_prod,
                    alias_index=alias_index_prod,
                )
                if _n_meses_period >= 1.8 and not _has_monthly_trend_points(_monthly_ecr_data):
                    _monthly_ecr_data = _compute_monthly_ecr_series(
                        df_prod_monthly_base, start_ts_prod, end_ts_prod,
                        alias_index=alias_index_prod,
                        min_items_per_month=1,
                    )
            except Exception:
                _monthly_ecr_data = {}

        def _ecr_trend_delta(pessoa):
            pts = _monthly_ecr_data.get(str(pessoa), [])
            if len(pts) >= 2:
                return round(float(pts[-1][1]) - float(pts[0][1]), 1)
            return np.nan

        def _ecr_tail_streak(pessoa):
            streak = 0
            for _, ecr_value, _ in reversed(_monthly_ecr_data.get(str(pessoa), [])):
                if pd.notna(ecr_value) and float(ecr_value) >= _ECR_MATURITY_THRESHOLD:
                    streak += 1
                else:
                    break
            return streak

        def _ecr_maturity_label(pessoa):
            pts = _monthly_ecr_data.get(str(pessoa), [])
            streak = _ecr_tail_streak(pessoa)
            if streak >= _ECR_MATURITY_STREAK:
                return 'Maduro em Estimativa'
            if len(pts) >= 2:
                return 'Em evolução'
            return 'Sem base'

        per_dev['Δ ECR (p.p.)'] = per_dev['Pessoa'].apply(_ecr_trend_delta)
        per_dev['Meses ECR>=80 Consecutivos'] = per_dev['Pessoa'].apply(_ecr_tail_streak)
        per_dev['Maturidade Estimativa'] = per_dev['Pessoa'].apply(_ecr_maturity_label)

        # ── Aging Rates — backlog antigo ao ser puxado ────────────────────────
        # Item "antigo" = data_criacao→DataInProgress > 30 dias antes de ser puxado.
        # Separa:
        # - Aging Rescue Rate: % dos cards ENTREGUES que já estavam envelhecidos ao serem puxados
        # - Aging Pull Rate: % dos cards PUXADOS que já estavam envelhecidos ao serem puxados
        # Referência: Jørgensen (IST 2023) — itens com high aging têm menor chance de entrega.
        _AGING_THRESHOLD_DAYS = 30
        _aging_rates_df = _compute_dev_aging_rates(
            df_prod_base,
            start_ts_prod,
            end_ts_prod,
            alias_index=alias_index_prod,
            threshold_days=_AGING_THRESHOLD_DAYS,
        )
        if not _aging_rates_df.empty:
            per_dev = per_dev.merge(_aging_rates_df, on='Pessoa', how='left')
            per_dev['Aging Rescue Rate (%)'] = pd.to_numeric(
                per_dev['Aging Rescue Rate (%)'], errors='coerce'
            )
            per_dev['Aging Pull Rate (%)'] = pd.to_numeric(
                per_dev['Aging Pull Rate (%)'], errors='coerce'
            )
            per_dev.loc[per_dev['Itens Entregues'].gt(0), 'Aging Rescue Rate (%)'] = (
                per_dev.loc[per_dev['Itens Entregues'].gt(0), 'Aging Rescue Rate (%)'].fillna(0.0)
            )
            per_dev.loc[per_dev['Itens Puxados'].gt(0), 'Aging Pull Rate (%)'] = (
                per_dev.loc[per_dev['Itens Puxados'].gt(0), 'Aging Pull Rate (%)'].fillna(0.0)
            )
        else:
            per_dev['Aging Rescue Rate (%)'] = np.nan
            per_dev['Aging Pull Rate (%)'] = np.nan

        # Filtro por BU (inline, sem necessidade de novo callback)
        bus_disponiveis = sorted(per_dev['BU'].dropna().unique().tolist())
        bus_disponiveis = [b for b in bus_disponiveis if b]  # remove vazios

        # ── KPIs de resumo do período ─────────────────────────────────────────
        total_entregues = int(per_dev['Itens Entregues'].sum())
        total_puxados = int(per_dev['Itens Puxados'].sum())
        total_sp = int(per_dev['SP Entregues'].sum())
        total_defeitos = int(per_dev['Defeitos Entregues'].sum())
        total_commits = int(per_dev['Commits'].sum())
        total_prs = int(per_dev['PRs Merged'].sum())
        total_qa_dev_returns = int(per_dev['Retornos QA->Dev'].sum()) if 'Retornos QA->Dev' in per_dev.columns else 0
        cards_with_qa_dev_return = int(per_dev['Cards com Retorno QA->Dev'].sum()) if 'Cards com Retorno QA->Dev' in per_dev.columns else 0
        pct_falha_geral = round(total_defeitos / total_entregues * 100, 1) if total_entregues > 0 else 0.0
        devs_ativos = int((per_dev['Itens Entregues'] > 0).sum())
        dev_cycle_median_series = pd.to_numeric(per_dev.get('Cycle Time Dev Mediano (dias)'), errors='coerce').dropna()
        dev_cycle_median = round(float(dev_cycle_median_series.median()), 1) if not dev_cycle_median_series.empty else 0.0

        # ── Métricas QSM-derivadas ────────────────────────────────────────────
        # Referência: QSM Benchmark Tables — Business Systems FP/PM
        # (https://www.qsm.com/resources/qsm-benchmark-tables, n≈330 projetos)
        # SP/mês ≈ FP/PM como proxy de produtividade (1 SP ≈ 1 FP, calibração equipe)
        _n_meses = max((end_ts_prod - start_ts_prod).days / 30.44, 0.1)
        sp_por_dev_por_mes = round(total_sp / devs_ativos / _n_meses, 1) if devs_ativos > 0 else 0.0
        per_dev['SP_por_Mes'] = (
            pd.to_numeric(per_dev['SP Entregues'], errors='coerce').fillna(0) / _n_meses
        ).round(1)

        # Posicionamento do time vs QSM Avg Staff quartis (Business Systems FP)
        # Q1=1.49 | Mediana=4.38 | Q3=9.17  (Fonte: QSM Benchmark Tables)
        _qsm_staff_band = (
            'abaixo Q1 QSM (<2)'   if devs_ativos < 2  else
            'Q1–Mediana QSM (2–4)' if devs_ativos < 5  else
            'Mediana–Q3 QSM (5–9)' if devs_ativos < 10 else
            'acima Q3 QSM (≥10)'
        )

        # IED — mediana dos devs com entregas (IED=0 excluídos da mediana)
        _ied_ativos = per_dev.loc[per_dev['IED'] > 0, 'IED']
        ied_mediano = round(float(_ied_ativos.median()), 0) if not _ied_ativos.empty else 0.0
        ied_color = '#27ae60' if ied_mediano >= 70 else '#e67e22' if ied_mediano >= 50 else '#e74c3c'

        def _mini_kpi(label, value, color='#2c3e50', bg='#f8f9fa', border_color='#dee2e6'):
            falha_bg = '#fff5f5' if '% Demanda' in label and isinstance(value, str) and float(value.replace('%','') or 0) >= 30 else bg
            falha_border = '#e74c3c' if '% Demanda' in label and isinstance(value, str) and float(value.replace('%','') or 0) >= 30 else border_color
            return html.Div([
                html.Div(str(value), style={
                    'fontSize': '26px', 'fontWeight': '700', 'color': color,
                    'lineHeight': '1.1', 'marginBottom': '4px',
                }),
                html.Div(label, style={
                    'fontSize': '11px', 'color': '#6c757d', 'textTransform': 'uppercase',
                    'letterSpacing': '0.5px', 'fontWeight': '500',
                }),
            ], style={
                'background': falha_bg, 'border': f'1px solid {falha_border}',
                'borderRadius': '8px', 'padding': '12px 16px',
                'minWidth': '110px', 'flex': '1',
                'textAlign': 'center', 'boxShadow': '0 1px 3px rgba(0,0,0,.06)',
            })

        # SP/Dev/Mês vs QSM benchmark: ≥7.47 = mediana indústria (Business Systems FP/PM)
        _sppm_color = '#27ae60' if sp_por_dev_por_mes >= 7.47 else '#e67e22' if sp_por_dev_por_mes >= 5.0 else '#e74c3c'
        falha_color = '#e74c3c' if pct_falha_geral >= 30 else '#e67e22' if pct_falha_geral >= 15 else '#27ae60'

        # KPIs dos novos indicadores
        _kcr_max_row = per_dev.nlargest(1, 'KCR').iloc[0] if not per_dev.empty and 'KCR' in per_dev.columns else None
        if _kcr_max_row is not None and _kcr_max_row['KCR'] > 0:
            _kcr_first = str(_kcr_max_row['Pessoa']).split()[0]
            _kcr_max_label = f"{_kcr_first} ({_kcr_max_row['KCR']:.0f}%)"
            _kcr_color = '#e74c3c' if _kcr_max_row['KCR'] > 40 else '#e67e22' if _kcr_max_row['KCR'] > 25 else '#27ae60'
        else:
            _kcr_max_label = '—'
            _kcr_color = '#6c757d'
        _ecr_series = per_dev.loc[per_dev.get('ECR', pd.Series(dtype=float)) > 0, 'ECR'] if 'ECR' in per_dev.columns else pd.Series(dtype=float)
        _ecr_med = round(float(_ecr_series.median()), 0) if not _ecr_series.empty else 100.0
        _ecr_color = '#27ae60' if _ecr_med >= 85 else '#e67e22' if _ecr_med >= 60 else '#e74c3c'
        _estab_series = per_dev['Estabilidade_Throughput'] if 'Estabilidade_Throughput' in per_dev.columns else pd.Series(dtype=float)
        _estab_med = round(float(_estab_series.median()), 0) if not _estab_series.empty else 0.0
        _estab_color = '#27ae60' if _estab_med >= 70 else '#e67e22' if _estab_med >= 50 else '#e74c3c'

        kpi_row = html.Div([
            _mini_kpi('Devs Ativos', f'{devs_ativos} ({_qsm_staff_band})', color='#2980b9'),
            _mini_kpi('IED Mediano', f'{ied_mediano:.0f}/100', color=ied_color,
                      bg='#f0fff4' if ied_mediano >= 70 else '#fffbf0' if ied_mediano >= 50 else '#fff5f5',
                      border_color='#b2dfdb' if ied_mediano >= 70 else '#ffe082' if ied_mediano >= 50 else '#ffcdd2'),
            _mini_kpi('Itens Entregues', total_entregues, color='#27ae60'),
            _mini_kpi('Itens Puxados', total_puxados, color='#2980b9'),
            _mini_kpi('SP Entregues', total_sp, color='#8e44ad'),
            _mini_kpi('SP/Dev/Mês', f'{sp_por_dev_por_mes:.1f}', color=_sppm_color,
                      bg='#f0fff4' if sp_por_dev_por_mes >= 7.47 else '#fffbf0' if sp_por_dev_por_mes >= 5.0 else '#fff5f5',
                      border_color='#b2dfdb' if sp_por_dev_por_mes >= 7.47 else '#ffe082' if sp_por_dev_por_mes >= 5.0 else '#ffcdd2'),
            _mini_kpi('Defeitos Entregues', total_defeitos, color='#c0392b'),
            _mini_kpi('% Demanda Falha', f'{pct_falha_geral:.1f}%', color=falha_color),
            _mini_kpi('Retornos QA->Dev', total_qa_dev_returns, color='#d35400'),
            _mini_kpi('Cards com Retorno', cards_with_qa_dev_return, color='#8e44ad'),
            _mini_kpi('CT Dev Mediano', f'{dev_cycle_median:.1f} d', color='#16a085'),
            _mini_kpi('Commits', total_commits, color='#16a085'),
            _mini_kpi('PRs Merged', total_prs, color='#2980b9'),
            _mini_kpi('Concentração Commits', _kcr_max_label, color=_kcr_color),
            _mini_kpi('ECR Mediano', f'{_ecr_med:.0f}%', color=_ecr_color,
                      bg='#f0fff4' if _ecr_med >= 85 else '#fffbf0' if _ecr_med >= 60 else '#fff5f5',
                      border_color='#b2dfdb' if _ecr_med >= 85 else '#ffe082' if _ecr_med >= 60 else '#ffcdd2'),
            _mini_kpi('Estabilidade TP', f'{_estab_med:.0f}/100', color=_estab_color,
                      bg='#f0fff4' if _estab_med >= 70 else '#fffbf0' if _estab_med >= 50 else '#fff5f5',
                      border_color='#b2dfdb' if _estab_med >= 70 else '#ffe082' if _estab_med >= 50 else '#ffcdd2'),
        ], style={
            'display': 'flex', 'flexWrap': 'wrap', 'gap': '10px',
            'marginBottom': '20px', 'marginTop': '10px',
        })

        no_delivery_notice = None
        if total_entregues == 0 and total_puxados > 0:
            no_delivery_notice = html.Div([
                html.Strong('Período com trabalho puxado, mas sem entregas elegíveis para IEF/IED.'),
                html.Span(
                    f' Foram identificados {total_puxados} itens puxados no recorte, porém 0 itens entregues '
                    'sem cancelamento. Por isso os gráficos de IEF e IED ficam sem base válida neste período.',
                    style={'marginLeft': '6px'},
                ),
            ], style={
                'padding': '12px 16px',
                'marginBottom': '16px',
                'backgroundColor': '#fff8e1',
                'border': '1px solid #ffe082',
                'borderLeft': '4px solid #f39c12',
                'borderRadius': '8px',
                'color': '#6d4c41',
            })

        team_visibility_enabled = bool(projeto and not team_seed_df.empty)
        zero_delivery_count = int((pd.to_numeric(per_dev['Itens Entregues'], errors='coerce').fillna(0) == 0).sum()) if 'Itens Entregues' in per_dev.columns else 0
        team_visibility_disclaimer = (
            f' Observação: {zero_delivery_count} pessoa(s) do time oficial aparecem com IEF/IED = 0 '
            'por não terem entregas elegíveis no recorte atual.'
            if team_visibility_enabled and zero_delivery_count > 0 else
            ' Observação: membros do time oficial são mantidos no gráfico mesmo sem entregas elegíveis no recorte.'
            if team_visibility_enabled else
            ''
        )

        # ── Banner de BU ──────────────────────────────────────────────────────
        _bu_chips = [
            html.Span(bu, style={
                'display': 'inline-block', 'background': '#e9ecef', 'color': '#495057',
                'borderRadius': '12px', 'padding': '2px 10px', 'fontSize': '12px',
                'marginLeft': '6px', 'fontWeight': '500',
            })
            for bu in bus_disponiveis
        ] if bus_disponiveis else [
            html.Span('(nenhuma BU mapeada — verifique people_config.json)',
                      style={'color': '#aaa', 'fontSize': '12px', 'marginLeft': '6px'})
        ]
        bu_selector = html.Div(
            [html.Span('Times mapeados: ', style={'fontWeight': '600', 'fontSize': '12px', 'color': '#555'})]
            + _bu_chips
            + [html.Span(
                ' | Use a coluna BU na tabela para filtrar por time. W1NNER e S1NC compartilham repositório Bitbucket.',
                style={'fontSize': '11px', 'color': '#999', 'marginLeft': '8px'},
            )],
            style={
                'padding': '8px 14px', 'backgroundColor': '#f8f9fa',
                'border': '1px solid #dee2e6', 'borderRadius': '6px',
                'marginBottom': '14px', 'display': 'flex', 'flexWrap': 'wrap',
                'alignItems': 'center', 'gap': '2px',
            },
        )

        # ── IEF — Índice de Entrega Focado (0.70×NDS + 0.30×EEE) ─────────────
        # Foco exclusivo em: volume/complexidade entregue + taxa de conclusão do estimado.
        # Exclui velocidade (VEL) e qualidade (QUA) para isolar a dimensão de entrega pura.
        _ief_df = per_dev.copy()
        _ief_df = _ief_df.sort_values('IEF', ascending=True).head(40)

        fig_ief = go.Figure()

        if not _ief_df.empty:
            def _ief_bar_color(v):
                if v >= 85: return '#27ae60'
                if v >= 70: return '#2ecc71'
                if v >= 50: return '#f39c12'
                if v >= 30: return '#e67e22'
                return '#e74c3c'

            _ief_colors = [_ief_bar_color(v) for v in _ief_df['IEF']]

            # Faixas de fundo
            for x0, x1, label, fill in [
                (0,  30,  'Crítico',           'rgba(231,76,60,0.07)'),
                (30, 50,  'Abaixo do Esperado','rgba(230,126,34,0.07)'),
                (50, 70,  'Regular',            'rgba(243,156,18,0.07)'),
                (70, 85,  'Bom',                'rgba(46,204,113,0.07)'),
                (85, 105, 'Excelente',          'rgba(39,174,96,0.12)'),
            ]:
                fig_ief.add_vrect(
                    x0=x0, x1=x1, fillcolor=fill, line_width=0,
                    annotation_text=label, annotation_position='top',
                    annotation_font_size=9, annotation_font_color='#666',
                )

            _ief_hover_cols = ['_ied_nds', '_ied_eee', 'IEF Classe',
                               'Score Complexidade', 'Score Complexidade Puxado', 'Flow Efficiency (%)']
            _ief_hover_avail = [c for c in _ief_hover_cols if c in _ief_df.columns]
            _ief_custom = _ief_df[_ief_hover_avail].values if _ief_hover_avail else None

            _nds_i = _ief_hover_avail.index('_ied_nds')              if '_ied_nds'               in _ief_hover_avail else None
            _eee_i = _ief_hover_avail.index('_ied_eee')              if '_ied_eee'               in _ief_hover_avail else None
            _cls_i = _ief_hover_avail.index('IEF Classe')            if 'IEF Classe'             in _ief_hover_avail else None
            _cx_i  = _ief_hover_avail.index('Score Complexidade')    if 'Score Complexidade'     in _ief_hover_avail else None
            _pux_i = _ief_hover_avail.index('Score Complexidade Puxado') if 'Score Complexidade Puxado' in _ief_hover_avail else None
            _fe_i  = _ief_hover_avail.index('Flow Efficiency (%)')   if 'Flow Efficiency (%)'    in _ief_hover_avail else None

            _ht = ['<b>%{y}</b><br>', 'IEF: <b>%{x:.1f}/100</b>']
            if _cls_i is not None: _ht.append(f' (%{{customdata[{_cls_i}]}})')
            _ht.append('<br>')
            if _nds_i is not None: _ht.append(f'NDS — Entrega/Complexidade (70%): %{{customdata[{_nds_i}]:.1f}}/100<br>')
            if _eee_i is not None: _ht.append(f'EEE — Taxa Conclusão Estimado (30%): %{{customdata[{_eee_i}]:.1f}}/100<br>')
            if _cx_i  is not None: _ht.append(f'Score Complexidade Entregue: %{{customdata[{_cx_i}]:.1f}}<br>')
            if _pux_i is not None: _ht.append(f'Score Complexidade Puxado: %{{customdata[{_pux_i}]:.1f}}<br>')
            if _fe_i  is not None: _ht.append(f'Flow Efficiency: %{{customdata[{_fe_i}]:.1f}}%')
            _ht.append('<extra></extra>')

            fig_ief.add_trace(go.Bar(
                y=_ief_df['Pessoa'],
                x=_ief_df['IEF'],
                orientation='h',
                marker_color=_ief_colors,
                marker_line_width=0,
                text=[f"{v:.0f}" for v in _ief_df['IEF']],
                textposition='outside',
                textfont=dict(size=11, color='#444'),
                customdata=_ief_custom,
                hovertemplate=''.join(_ht),
            ))

            for y_val, dash, color, label in [
                (85, 'dot',  '#1abc9c', 'Excelente (85)'),
                (70, 'dash', '#27ae60', 'Bom (70)'),
                (50, 'dot',  '#f39c12', 'Regular (50)'),
            ]:
                fig_ief.add_vline(
                    x=y_val, line_dash=dash, line_color=color, line_width=1.5,
                    annotation_text=label, annotation_position='bottom right',
                    annotation_font_size=10, annotation_font_color=color,
                )

        fig_ief.update_layout(
            title=(
                'Índice de Entrega Focado (IEF) — 0.70×NDS + 0.30×EEE<br>'
                '<sup>'
                'NDS (70%): volume de entregas ponderado por complexidade vs P75 do grupo. '
                'EEE (30%): taxa de conclusão do trabalho comprometido (entregue / puxado por complexidade). '
                'SP e T-shirt equalizados (Kitchenham &amp; Mendes, TSE 2004). '
                'Faixas: Excelente ≥85 | Bom ≥70 | Regular ≥50 | Abaixo ≥30 | Crítico &lt;30.'
                f'{team_visibility_disclaimer}'
                '</sup>'
            ),
            xaxis=dict(range=[0, 110], title='IEF (0–100)', showgrid=True, gridcolor='#eee'),
            yaxis=dict(title='', automargin=True),
            template='plotly_white',
            height=max(400, 30 * max(len(_ief_df), 1) + 140),
            margin=dict(t=90, b=50, l=180, r=80),
            bargap=0.25,
            plot_bgcolor='#fafafa',
        )

        # ── Régua IED — gráfico de barras horizontais com faixas de classificação ──
        # Mostra o IED de cada dev com cor por faixa e linhas de referência.
        _ied_df = per_dev.copy()
        _ied_df = _ied_df.sort_values('IED', ascending=True).head(40)

        def _ied_bar_color(v):
            if v >= 85:
                return '#27ae60'
            if v >= 70:
                return '#2ecc71'
            if v >= 50:
                return '#f39c12'
            if v >= 30:
                return '#e67e22'
            return '#e74c3c'

        fig_ied = go.Figure()

        if not _ied_df.empty:
            # Faixas de fundo por classificação
            for x0, x1, label, fill in [
                (0,  30,  'Crítico',           'rgba(231,76,60,0.07)'),
                (30, 50,  'Abaixo do Esperado','rgba(230,126,34,0.07)'),
                (50, 70,  'Regular',            'rgba(243,156,18,0.07)'),
                (70, 85,  'Bom',                'rgba(46,204,113,0.07)'),
                (85, 105, 'Excelente',          'rgba(39,174,96,0.12)'),
            ]:
                fig_ied.add_vrect(
                    x0=x0, x1=x1, fillcolor=fill, line_width=0,
                    annotation_text=label, annotation_position='top',
                    annotation_font_size=9, annotation_font_color='#666',
                )

            _bar_colors = [_ied_bar_color(v) for v in _ied_df['IED']]
            _hover_cols = ['_ied_nds', '_ied_eee', '_ied_vel', '_ied_qua', 'IED Classe',
                           'Score Complexidade', 'Score Complexidade Puxado',
                           'Flow Efficiency (%)', 'Lead Time Mediano (dias)']
            _hover_cols_avail = [c for c in _hover_cols if c in _ied_df.columns]
            _custom = _ied_df[_hover_cols_avail].values if _hover_cols_avail else None

            _nds_idx  = _hover_cols_avail.index('_ied_nds')  if '_ied_nds'  in _hover_cols_avail else None
            _eee_idx  = _hover_cols_avail.index('_ied_eee')  if '_ied_eee'  in _hover_cols_avail else None
            _vel_idx  = _hover_cols_avail.index('_ied_vel')  if '_ied_vel'  in _hover_cols_avail else None
            _qua_idx  = _hover_cols_avail.index('_ied_qua')  if '_ied_qua'  in _hover_cols_avail else None
            _cls_idx  = _hover_cols_avail.index('IED Classe') if 'IED Classe' in _hover_cols_avail else None

            _ht_parts = ['<b>%{y}</b><br>', 'IED: <b>%{x:.1f}/100</b>']
            if _cls_idx is not None:
                _ht_parts.append(f' (%{{customdata[{_cls_idx}]}})')
            _ht_parts.append('<br>')
            if _nds_idx is not None:
                _ht_parts.append(f'Entrega (NDS 40%): %{{customdata[{_nds_idx}]:.1f}}/100<br>')
            if _eee_idx is not None:
                _ht_parts.append(f'Taxa Conclusão Estimado (EEE 30%): %{{customdata[{_eee_idx}]:.1f}}/100<br>')
            if _vel_idx is not None:
                _ht_parts.append(f'Velocidade (VEL 20%): %{{customdata[{_vel_idx}]:.1f}}/100<br>')
            if _qua_idx is not None:
                _ht_parts.append(f'Qualidade (QUA 10%): %{{customdata[{_qua_idx}]:.1f}}/100')
            _ht_parts.append('<extra></extra>')

            fig_ied.add_trace(go.Bar(
                y=_ied_df['Pessoa'],
                x=_ied_df['IED'],
                orientation='h',
                marker_color=_bar_colors,
                marker_line_width=0,
                text=[f"{v:.0f}" for v in _ied_df['IED']],
                textposition='outside',
                textfont=dict(size=11, color='#444'),
                customdata=_custom,
                hovertemplate=''.join(_ht_parts),
            ))

            # Linhas de referência
            fig_ied.add_vline(
                x=70, line_dash='dash', line_color='#27ae60', line_width=1.5,
                annotation_text='Bom (70)', annotation_position='bottom right',
                annotation_font_size=10, annotation_font_color='#27ae60',
            )
            fig_ied.add_vline(
                x=50, line_dash='dot', line_color='#f39c12', line_width=1.5,
                annotation_text='Regular (50)', annotation_position='bottom right',
                annotation_font_size=10, annotation_font_color='#f39c12',
            )
            fig_ied.add_vline(
                x=85, line_dash='dot', line_color='#1abc9c', line_width=1.5,
                annotation_text='Excelente (85)', annotation_position='top right',
                annotation_font_size=10, annotation_font_color='#1abc9c',
            )

        fig_ied.update_layout(
            title=(
                'Índice de Entrega do Desenvolvedor (IED) — Régua de Produtividade<br>'
                '<sup>'
                'IED = 0.40×NDS (volume/complexidade) + 0.30×EEE (taxa conclusão estimado) '
                '+ 0.20×VEL (velocidade) + 0.10×QUA (qualidade) | '
                'SP e T-shirt equalizados (Kitchenham & Mendes, TSE 2004) | '
                'Referências: Jørgensen (IST 2023), Flournoy et al. (EMSE 2025), Forsgren et al. (SPACE 2021).'
                f'{team_visibility_disclaimer}'
                '</sup>'
            ),
            xaxis=dict(range=[0, 110], title='IED (0–100)', showgrid=True, gridcolor='#eee'),
            yaxis=dict(title='', automargin=True),
            template='plotly_white',
            height=max(400, 30 * max(len(_ied_df), 1) + 140),
            margin=dict(t=90, b=50, l=180, r=80),
            bargap=0.25,
            plot_bgcolor='#fafafa',
        )

        # ── Radar IED — comparação multidimensional dos componentes por dev ──
        _radar_cols_map = [
            ('_ied_nds', 'NDS (Entrega 40%)'),
            ('_ied_eee', 'EEE (Conclusão 30%)'),
            ('_ied_vel', 'VEL (Velocidade 20%)'),
            ('_ied_qua', 'QUA (Qualidade 10%)'),
        ]
        _radar_col_keys  = [c   for c, _ in _radar_cols_map if c in per_dev.columns]
        _radar_col_lbls  = [lbl for c, lbl in _radar_cols_map if c in per_dev.columns]

        _radar_src = per_dev[['Pessoa', 'IED'] + _radar_col_keys].copy()
        _radar_src = _radar_src[_radar_src['IED'] > 0].sort_values('IED', ascending=False).head(15)

        _radar_palette = [
            '#27ae60', '#2ecc71', '#3498db', '#9b59b6', '#e74c3c',
            '#e67e22', '#f39c12', '#1abc9c', '#e91e63', '#00bcd4',
            '#8bc34a', '#ff5722', '#607d8b', '#795548', '#ff9800',
        ]

        fig_ied_radar = go.Figure()
        if not _radar_src.empty and _radar_col_keys:
            for _ri, (_, _rrow) in enumerate(_radar_src.iterrows()):
                _rvals = [float(_rrow.get(c, 0) or 0) for c in _radar_col_keys]
                _rcol  = _radar_palette[_ri % len(_radar_palette)]
                _rh    = _rcol.lstrip('#')
                _rfill = 'rgba({},{},{},0.13)'.format(
                    int(_rh[0:2], 16), int(_rh[2:4], 16), int(_rh[4:6], 16)
                )
                fig_ied_radar.add_trace(go.Scatterpolar(
                    r=_rvals + [_rvals[0]],
                    theta=_radar_col_lbls + [_radar_col_lbls[0]],
                    fill='toself',
                    fillcolor=_rfill,
                    line=dict(color=_rcol, width=2),
                    name=str(_rrow['Pessoa']),
                    hovertemplate=(
                        '<b>' + str(_rrow['Pessoa']) + '</b><br>'
                        '%{theta}: <b>%{r:.1f}/100</b><extra></extra>'
                    ),
                ))
        fig_ied_radar.update_layout(
            title=(
                'IED — Radar de Componentes por Desenvolvedor<br>'
                '<sup>Comparação multidimensional dos 4 eixos do IED (top 15 por score). '
                'Quanto maior a área, melhor o desempenho agregado.</sup>'
            ),
            polar=dict(
                radialaxis=dict(
                    range=[0, 100], showticklabels=True,
                    tickfont=dict(size=9), gridcolor='#ddd',
                    tickvals=[0, 25, 50, 75, 100],
                ),
                angularaxis=dict(tickfont=dict(size=12, color='#2c3e50')),
                bgcolor='#fafafa',
            ),
            template='plotly_white',
            height=560,
            margin=dict(t=100, b=60, l=60, r=220),
            legend=dict(
                orientation='v', x=1.02, y=0.5,
                font=dict(size=10),
                bgcolor='rgba(255,255,255,0.92)',
                bordercolor='#ddd', borderwidth=1,
            ),
            showlegend=True,
        )

        # ── Scatter IEF × IED — diagnóstico de divergência ────────────────────
        # IEF captura volume+conclusão; IED penaliza também VEL e QUA.
        # Devs acima da diagonal: IEF > IED → velocidade ou qualidade reduz o IED.
        # Devs com Δ > 15 ficam destacados — sinaliza onde intervir em VEL ou QUA.
        fig_ief_ied_scatter = go.Figure()
        if 'IEF' in per_dev.columns and 'IED' in per_dev.columns:
            _scatter_df = per_dev[per_dev['IED'] > 0][['Pessoa', 'IEF', 'IED', 'Δ IEF–IED', 'Papel']].copy() \
                if 'Δ IEF–IED' in per_dev.columns else \
                per_dev[per_dev['IED'] > 0][['Pessoa', 'IEF', 'IED', 'Papel']].copy()
            if 'Δ IEF–IED' not in _scatter_df.columns:
                _scatter_df['Δ IEF–IED'] = (_scatter_df['IEF'] - _scatter_df['IED']).abs()
            _scatter_df['Alerta'] = _scatter_df['Δ IEF–IED'] > 15
            if not _scatter_df.empty:
                _normal = _scatter_df[~_scatter_df['Alerta']]
                _alerta = _scatter_df[_scatter_df['Alerta']]
                fig_ief_ied_scatter.add_trace(go.Scatter(
                    x=_normal['IED'], y=_normal['IEF'],
                    mode='markers+text', name='Normal (Δ ≤ 15)',
                    marker=dict(color='#2980b9', size=10, opacity=0.75),
                    text=_normal['Pessoa'], textposition='top center', textfont=dict(size=9),
                    hovertemplate='<b>%{text}</b><br>IED: %{x:.1f}<br>IEF: %{y:.1f}<br>Δ: %{customdata:.1f}',
                    customdata=_normal['Δ IEF–IED'],
                ))
                if not _alerta.empty:
                    fig_ief_ied_scatter.add_trace(go.Scatter(
                        x=_alerta['IED'], y=_alerta['IEF'],
                        mode='markers+text', name='Δ > 15 (atenção)',
                        marker=dict(color='#e74c3c', size=12, opacity=0.9, symbol='diamond'),
                        text=_alerta['Pessoa'], textposition='top center', textfont=dict(size=9, color='#c0392b'),
                        hovertemplate='<b>%{text}</b><br>IED: %{x:.1f}<br>IEF: %{y:.1f}<br>Δ: %{customdata:.1f}',
                        customdata=_alerta['Δ IEF–IED'],
                    ))
                # Linha diagonal de referência (IEF = IED)
                fig_ief_ied_scatter.add_trace(go.Scatter(
                    x=[0, 100], y=[0, 100], mode='lines',
                    name='IEF = IED', line=dict(color='#aaa', dash='dash', width=1),
                    hoverinfo='skip',
                ))
                fig_ief_ied_scatter.update_layout(
                    title=(
                        'Divergência IEF × IED<br>'
                        '<sup>Devs acima da diagonal: VEL ou QUA reduzem o IED. '
                        'Marcadores vermelhos: Δ > 15 — intervenção sugerida.</sup>'
                    ),
                    xaxis=dict(title='IED (régua completa)', range=[0, 110], showgrid=True, gridcolor='#eee'),
                    yaxis=dict(title='IEF (volume + conclusão)', range=[0, 110], showgrid=True, gridcolor='#eee'),
                    template='plotly_white', height=480,
                    margin=dict(t=80, b=60, l=60, r=40),
                    legend=dict(orientation='h', y=-0.15),
                )

        # ── Radar Produtividade 360° — combina IED + Estabilidade + ECR ────────
        # Extensão do IED radar com 6 eixos: os 4 componentes do IED + 2 novos indicadores.
        # Top 15 por IED. Referências: Anderson (2010), Kitchenham & Mendes (TSE 2004).
        _p360_axes = [
            ('_ied_nds',              'Entrega (NDS)'),
            ('_ied_eee',              'Conclusão (EEE)'),
            ('_ied_vel',              'Velocidade (VEL)'),
            ('_ied_qua',              'Qualidade (QUA)'),
            ('Estabilidade_Throughput', 'Estabilidade'),
            ('ECR',                   'Cobertura Estimativa (ECR)'),
        ]
        _p360_keys = [k for k, _ in _p360_axes if k in per_dev.columns]
        _p360_lbls = [l for k, l in _p360_axes if k in per_dev.columns]

        _p360_src = per_dev[['Pessoa', 'IED'] + _p360_keys].copy()
        _p360_src = _p360_src[_p360_src['IED'] > 0].sort_values('IED', ascending=False).head(15)

        fig_prod_360 = go.Figure()
        if not _p360_src.empty and len(_p360_keys) >= 3:
            for _ri, (_, _row) in enumerate(_p360_src.iterrows()):
                _vals = [float(_row.get(k, 0) or 0) for k in _p360_keys]
                _col = _radar_palette[_ri % len(_radar_palette)]
                _rh = _col.lstrip('#')
                _rfill = 'rgba({},{},{},0.10)'.format(
                    int(_rh[0:2], 16), int(_rh[2:4], 16), int(_rh[4:6], 16)
                )
                fig_prod_360.add_trace(go.Scatterpolar(
                    r=_vals + [_vals[0]],
                    theta=_p360_lbls + [_p360_lbls[0]],
                    fill='toself',
                    fillcolor=_rfill,
                    line=dict(color=_col, width=2),
                    name=str(_row['Pessoa']),
                    hovertemplate=(
                        '<b>' + str(_row['Pessoa']) + '</b><br>'
                        '%{theta}: <b>%{r:.1f}/100</b><extra></extra>'
                    ),
                ))
            # Referência: mínimo esperado = 70 em todos os eixos
            fig_prod_360.add_trace(go.Scatterpolar(
                r=[70] * len(_p360_lbls) + [70],
                theta=_p360_lbls + [_p360_lbls[0]],
                fill=None,
                name='Mínimo Esperado (70)',
                line=dict(color='#f39c12', width=2.5, dash='dash'),
                opacity=1.0,
            ))
            # Referência: excelência = 100
            fig_prod_360.add_trace(go.Scatterpolar(
                r=[100] * len(_p360_lbls) + [100],
                theta=_p360_lbls + [_p360_lbls[0]],
                fill=None,
                name='Excelência (100)',
                line=dict(color='#27ae60', width=2.5, dash='dot'),
                opacity=1.0,
            ))
        fig_prod_360.update_layout(
            title=(
                'Produtividade 360° — Resumo Geral por Desenvolvedor<br>'
                '<sup>'
                'Combina os 4 eixos do IED (NDS, EEE, VEL, QUA) + Estabilidade de Throughput (1−CV semanal) + '
                'ECR (% itens puxados com estimativa real). Top 15 por IED. '
                'Maior área = perfil mais completo. | '
                'Estabilidade: Anderson (2010); Magennis (2016) | '
                'ECR: Kitchenham & Mendes (TSE 2004)'
                '</sup>'
            ),
            polar=dict(
                radialaxis=dict(
                    range=[0, 100], showticklabels=True,
                    tickfont=dict(size=9), gridcolor='#ddd',
                    tickvals=[0, 25, 50, 75, 100],
                ),
                angularaxis=dict(tickfont=dict(size=12, color='#2c3e50')),
                bgcolor='#fafafa',
            ),
            template='plotly_white',
            height=600,
            margin=dict(t=120, b=60, l=60, r=240),
            legend=dict(
                orientation='v', x=1.02, y=0.5,
                font=dict(size=10),
                bgcolor='rgba(255,255,255,0.92)',
                bordercolor='#ddd', borderwidth=1,
            ),
            showlegend=True,
        )

        # ── Tabela de componentes do IED (breakdown por dev) ──────────────────
        _ied_comp_cols = ['Pessoa', 'IED', 'IED Classe', '_ied_nds', '_ied_eee', '_ied_vel', '_ied_qua']
        _ied_comp_avail = [c for c in _ied_comp_cols if c in per_dev.columns]
        _ied_comp_display = per_dev[_ied_comp_avail].head(30).copy()
        _ied_col_rename = {
            '_ied_nds': 'NDS (Entrega, 40%)',
            '_ied_eee': 'EEE (Conclusão Estimado, 30%)',
            '_ied_vel': 'VEL (Velocidade, 20%)',
            '_ied_qua': 'QUA (Qualidade, 10%)',
        }
        _ied_comp_display = _ied_comp_display.rename(columns=_ied_col_rename)
        for _rc in list(_ied_col_rename.values()) + ['IED']:
            if _rc in _ied_comp_display.columns:
                _ied_comp_display[_rc] = _ied_comp_display[_rc].apply(
                    lambda v: f'{float(v):.1f}' if pd.notna(v) else '—'
                )

        _ied_comp_table_cols = [c for c in _ied_comp_display.columns]
        ied_breakdown_table = dash_table.DataTable(
            columns=[{"name": c, "id": c} for c in _ied_comp_table_cols],
            data=_ied_comp_display.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'center', 'padding': '7px 12px',
                'fontSize': '13px', 'whiteSpace': 'nowrap',
            },
            style_cell_conditional=[
                {'if': {'column_id': 'Pessoa'}, 'textAlign': 'left', 'minWidth': '140px'},
                {'if': {'column_id': 'IED Classe'}, 'fontWeight': '600'},
            ],
            style_header={
                'backgroundColor': '#2c3e50', 'color': 'white',
                'fontWeight': '600', 'fontSize': '12px',
                'textTransform': 'uppercase', 'letterSpacing': '0.3px',
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                {'if': {'filter_query': '{IED Classe} = "Excelente"'},
                 'backgroundColor': '#f0fff4', 'color': '#155724'},
                {'if': {'filter_query': '{IED Classe} = "Bom"'},
                 'backgroundColor': '#f0faf8', 'color': '#0c5460'},
                {'if': {'filter_query': '{IED Classe} = "Crítico"'},
                 'backgroundColor': '#fff5f5', 'color': '#721c24'},
                {'if': {'filter_query': '{IED Classe} = "Abaixo do Esperado"'},
                 'backgroundColor': '#fffbf0', 'color': '#856404'},
            ],
            sort_action='native',
            page_size=15,
        )

        # ── Tabela resumo por dev ─────────────────────────────────────────────
        table_col_order = [
            'BU', 'Papel', 'Pessoa',
            # Entrega e flow
            'Itens Puxados', 'Itens Entregues', 'WIP Residual', 'WIP Inicio Periodo',
            'Flow Efficiency (%)', 'FE Ajustada (%)',
            'SP Entregues', 'Score Complexidade',
            # Qualidade Jira
            'Defeitos Puxados', 'Defeitos Entregues', '% Demanda Falha',
            'Lead Time Mediano (dias)',
            # Código / CI
            'Commits', 'PRs Abertos', 'PRs Merged',
            'PR Cycle Time Mediano (h)', 'PR Size Mediana (LOC)',
            'Pipelines Total', 'Pipeline Success Rate (%)',
            # Revisão
            'Aprovacoes', 'Total Revisoes', 'Qualidade Revisao', 'Devs Revisados',
            # Process Mining — qualidade de processo
            'Conformance Quality (%)', 'Rework Rate PM (%)', 'QA Return Rate (%)',
            'Complexidade Variante',
            'Cycle Time Dev Mediano (dias)', 'Cycle Time Dev Médio (dias)',
            'Retornos QA->Dev', 'Cards com Retorno QA->Dev',
            '% Cards com Retorno QA->Dev', 'Tempo Retorno QA->Dev Mediano (dias)',
            # Process Mining — bottleneck
            'Horas em Gargalo', '% Horas em Gargalo',
            # Benchmark multidimensional
            'Score Benchmark', 'Distancia ao Ideal',
            # Índice de Entrega do Desenvolvedor
            'IED', 'IED Classe', 'Confiança IED',
            # Índice de Entrega Focado (volume + conclusão, sem VEL/QUA)
            'IEF', 'IEF Ajustado', 'IEF Confiança (%)', 'IEF Classe',
            # Divergência IEF–IED: sinal diagnóstico (alto Δ indica penalização por VEL ou QUA)
            'Δ IEF–IED',
            # Componentes do IED (detalhamento)
            'Score Complexidade Puxado',
            # Novos indicadores
            'DD_FP', 'KCR', 'ECR', 'Estabilidade_Throughput',
            'Δ ECR (p.p.)', 'Maturidade Estimativa',
            # Previsibilidade de Lead Time (P85/P50)
            'Lead Time P50 (dias)', 'Lead Time P85 (dias)', 'Razão P85/P50', 'Previsibilidade LT',
            # WIP médio (Little's Law)
            'WIP Medio',
            # IED trend mensal
            'Δ IED Trend', 'IED Seta',
            # Aging rates
            'Aging Rescue Rate (%)',
            'Aging Pull Rate (%)',
        ]
        table_cols_prod = [c for c in table_col_order if c in per_dev.columns]

        # Formata colunas percentuais para exibição
        prod_display = per_dev[table_cols_prod].head(80).copy()
        for _pct_col in ['% Demanda Falha', 'Qualidade Revisao', 'Pipeline Success Rate (%)',
                         'Conformance Quality (%)', 'Rework Rate PM (%)', 'QA Return Rate (%)',
                         '% Horas em Gargalo', 'Flow Efficiency (%)', '% Cards com Retorno QA->Dev']:
            if _pct_col in prod_display.columns:
                prod_display[_pct_col] = prod_display[_pct_col].apply(
                    lambda v: f'{float(v):.1f}%' if pd.notna(v) else '—'
                )
        # Formata novos indicadores
        if 'DD_FP' in prod_display.columns:
            prod_display['DD_FP'] = prod_display['DD_FP'].apply(
                lambda v: f'{float(v):.3f}' if pd.notna(v) else '—'
            )
        if 'KCR' in prod_display.columns:
            prod_display['KCR'] = prod_display['KCR'].apply(
                lambda v: f'{float(v):.1f}%' if pd.notna(v) else '—'
            )
        if 'ECR' in prod_display.columns:
            prod_display['ECR'] = prod_display['ECR'].apply(
                lambda v: f'{float(v):.1f}%' if pd.notna(v) else '—'
            )
        if 'Estabilidade_Throughput' in prod_display.columns:
            prod_display['Estabilidade_Throughput'] = prod_display['Estabilidade_Throughput'].apply(
                lambda v: f'{float(v):.1f}' if pd.notna(v) else '—'
            )
        if 'Δ IEF–IED' in prod_display.columns:
            prod_display['Δ IEF–IED'] = prod_display['Δ IEF–IED'].apply(
                lambda v: f'{float(v):.1f}' if pd.notna(v) else '—'
            )
        if 'Δ ECR (p.p.)' in prod_display.columns:
            prod_display['Δ ECR (p.p.)'] = prod_display['Δ ECR (p.p.)'].apply(
                lambda v: f'{float(v):+.1f}' if pd.notna(v) else '—'
            )
        for _lt_num_col in ['Lead Time P50 (dias)', 'Lead Time P85 (dias)', 'Razão P85/P50', 'WIP Medio']:
            if _lt_num_col in prod_display.columns:
                prod_display[_lt_num_col] = prod_display[_lt_num_col].apply(
                    lambda v: f'{float(v):.1f}' if pd.notna(v) else '—'
                )
        if 'Δ IED Trend' in prod_display.columns:
            prod_display['Δ IED Trend'] = prod_display['Δ IED Trend'].apply(
                lambda v: f'{float(v):+.1f}' if pd.notna(v) else '—'
            )
        if 'Aging Rescue Rate (%)' in prod_display.columns:
            prod_display['Aging Rescue Rate (%)'] = prod_display['Aging Rescue Rate (%)'].apply(
                lambda v: f'{float(v):.1f}%' if pd.notna(v) else '—'
            )
        if 'Aging Pull Rate (%)' in prod_display.columns:
            prod_display['Aging Pull Rate (%)'] = prod_display['Aging Pull Rate (%)'].apply(
                lambda v: f'{float(v):.1f}%' if pd.notna(v) else '—'
            )
        for _pr_num_col in ['PR Cycle Time Mediano (h)', 'PR Size Mediana (LOC)',
                             'IEF Ajustado', 'IEF Confiança (%)']:
            if _pr_num_col in prod_display.columns:
                prod_display[_pr_num_col] = prod_display[_pr_num_col].apply(
                    lambda v: f'{float(v):.1f}' if pd.notna(v) else '—'
                )
        # IED: marca com * quando ECR < 50% para sinalizar baixa confiabilidade
        if 'IED' in prod_display.columns and 'Confiança IED' in prod_display.columns:
            _ied_raw = per_dev.set_index('Pessoa')['IED'] if 'Pessoa' in per_dev.columns else pd.Series(dtype=float)
            _conf_raw = per_dev.set_index('Pessoa')['Confiança IED'] if 'Confiança IED' in per_dev.columns else pd.Series(dtype=str)
            prod_display['IED'] = prod_display.apply(
                lambda row: f"{row['IED']}*" if str(row.get('Confiança IED', '')).startswith('⚠') else str(row['IED']),
                axis=1,
            )

        # ── Tabela com tabs internas por grupo de indicadores ────────────────
        # Colunas de identificação presentes em todas as abas
        _ID_COLS = [c for c in ['BU', 'Papel', 'Pessoa'] if c in prod_display.columns]

        def _make_tab_table(extra_cols, conditional_styles=None):
            _cols = [c for c in _ID_COLS + extra_cols if c in prod_display.columns]
            return dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in _cols],
                data=prod_display[_cols].to_dict('records'),
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left', 'padding': '8px 12px',
                    'fontSize': '13px', 'whiteSpace': 'nowrap',
                    'overflow': 'hidden', 'textOverflow': 'ellipsis',
                    'maxWidth': '180px',
                },
                style_cell_conditional=[
                    {'if': {'column_id': 'Pessoa'}, 'minWidth': '150px', 'maxWidth': '200px'},
                    {'if': {'column_id': 'BU'}, 'minWidth': '120px'},
                ],
                style_header={
                    'backgroundColor': '#343a40', 'color': 'white',
                    'fontWeight': '600', 'fontSize': '12px',
                    'textTransform': 'uppercase', 'letterSpacing': '0.4px',
                    'padding': '10px 12px',
                },
                sort_action='native',
                filter_action='native',
                page_size=20,
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                    {'if': {'filter_query': '{BU} = "Sistemas - W1NNER"'}, 'borderLeft': '3px solid #3498db'},
                    {'if': {'filter_query': '{BU} = "Sistemas - S1NC"'}, 'borderLeft': '3px solid #9b59b6'},
                    {'if': {'filter_query': '{BU} = "BeFinance"'}, 'borderLeft': '3px solid #e67e22'},
                    {'if': {'filter_query': '{BU} = "Dados"'}, 'borderLeft': '3px solid #1abc9c'},
                ] + (conditional_styles or []),
            )

        _tab_style = {'padding': '4px 12px', 'fontSize': '13px', 'fontWeight': '600'}
        _tab_sel_style = {**_tab_style, 'borderTop': '3px solid #2980b9', 'color': '#2980b9'}

        prod_table = dcc.Tabs(
            value='tab-flow',
            style={'marginBottom': '0'},
            children=[
                dcc.Tab(
                    label='Flow',
                    value='tab-flow',
                    style=_tab_style,
                    selected_style=_tab_sel_style,
                    children=[_make_tab_table([
                        'Itens Puxados', 'Itens Entregues', 'WIP Residual', 'WIP Inicio Periodo',
                        'FE Ajustada (%)', 'SP Entregues', 'Score Complexidade', 'Score Complexidade Puxado',
                        'Lead Time Mediano (dias)', 'Lead Time P50 (dias)', 'Lead Time P85 (dias)',
                        'Razão P85/P50', 'Previsibilidade LT', 'WIP Medio',
                        'Defeitos Puxados', 'Defeitos Entregues', '% Demanda Falha',
                    ], [
                        {'if': {'filter_query': '{Itens Entregues} >= 10'}, 'borderLeft': '3px solid #27ae60'},
                        {'if': {'filter_query': '{Previsibilidade LT} = "Previsível"', 'column_id': 'Razão P85/P50'},
                         'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': '700'},
                        {'if': {'filter_query': '{Previsibilidade LT} = "Moderado"', 'column_id': 'Razão P85/P50'},
                         'backgroundColor': '#fff3cd', 'color': '#856404', 'fontWeight': '700'},
                        {'if': {'filter_query': '{Previsibilidade LT} = "Imprevisível"', 'column_id': 'Razão P85/P50'},
                         'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': '700'},
                    ])],
                ),
                dcc.Tab(
                    label='Código / CI',
                    value='tab-codigo',
                    style=_tab_style,
                    selected_style=_tab_sel_style,
                    children=[_make_tab_table([
                        'Commits', 'PRs Abertos', 'PRs Merged',
                        'PR Cycle Time Mediano (h)', 'PR Size Mediana (LOC)',
                        'Pipelines Total', 'Pipeline Success Rate (%)',
                        'KCR', 'DD_FP', 'Estabilidade_Throughput',
                    ])],
                ),
                dcc.Tab(
                    label='Revisão',
                    value='tab-revisao',
                    style=_tab_style,
                    selected_style=_tab_sel_style,
                    children=[_make_tab_table([
                        'Aprovacoes', 'Reprovacoes', 'Total Revisoes',
                        'Qualidade Revisao', 'Devs Revisados',
                        'PRs Declinados (Autor)',
                    ])],
                ),
                dcc.Tab(
                    label='Processo',
                    value='tab-processo',
                    style=_tab_style,
                    selected_style=_tab_sel_style,
                    children=[_make_tab_table([
                        'HorasNoFluxo Total', 'Média H/Evento',
                        'Horas em Gargalo', '% Horas em Gargalo',
                        'Conformance Quality (%)', 'Rework Rate PM (%)',
                        'Rework Score Total', 'Rework Score Médio',
                        'QA Return Rate (%)', 'Complexidade Variante',
                        'Cycle Time Dev Mediano (dias)', 'Cycle Time Dev Médio (dias)',
                        'Retornos QA->Dev', 'Cards com Retorno QA->Dev',
                        '% Cards com Retorno QA->Dev', 'Tempo Retorno QA->Dev Mediano (dias)',
                    ])],
                ),
                dcc.Tab(
                    label='Índices',
                    value='tab-indices',
                    style=_tab_style,
                    selected_style=_tab_sel_style,
                    children=[_make_tab_table([
                        'IED', 'IED Classe', 'Confiança IED',
                        'IEF', 'IEF Ajustado', 'IEF Confiança (%)', 'IEF Classe',
                        'Δ IEF–IED',
                        'ECR', 'Δ ECR (p.p.)', 'Maturidade Estimativa',
                        'Δ IED Trend', 'IED Seta',
                        'Aging Rescue Rate (%)', 'Aging Pull Rate (%)',
                        'Score Benchmark', 'Distancia ao Ideal',
                    ], [
                        {'if': {'filter_query': '{IED Classe} = "Excelente"', 'column_id': 'IED'},
                         'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': '700'},
                        {'if': {'filter_query': '{IED Classe} = "Bom"', 'column_id': 'IED'},
                         'backgroundColor': '#d1ecf1', 'color': '#0c5460', 'fontWeight': '700'},
                        {'if': {'filter_query': '{IED Classe} = "Regular"', 'column_id': 'IED'},
                         'backgroundColor': '#fff3cd', 'color': '#856404', 'fontWeight': '700'},
                        {'if': {'filter_query': '{IED Classe} = "Abaixo do Esperado"', 'column_id': 'IED'},
                         'backgroundColor': '#ffe5b4', 'color': '#7d4500', 'fontWeight': '700'},
                        {'if': {'filter_query': '{IED Classe} = "Crítico"', 'column_id': 'IED'},
                         'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': '700'},
                        {'if': {'filter_query': '{Δ IED Trend} contains "+"', 'column_id': 'Δ IED Trend'},
                         'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': '700'},
                        {'if': {'filter_query': '{Δ IED Trend} contains "-"', 'column_id': 'Δ IED Trend'},
                         'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': '700'},
                        {'if': {'filter_query': '{IED Seta} = "↑"', 'column_id': 'IED Seta'},
                         'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': '700', 'fontSize': '16px'},
                        {'if': {'filter_query': '{IED Seta} = "↓"', 'column_id': 'IED Seta'},
                         'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': '700', 'fontSize': '16px'},
                        {'if': {'filter_query': '{Δ ECR (p.p.)} contains "+"', 'column_id': 'Δ ECR (p.p.)'},
                         'backgroundColor': '#d1ecf1', 'color': '#0c5460', 'fontWeight': '700'},
                        {'if': {'filter_query': '{Δ ECR (p.p.)} contains "-"', 'column_id': 'Δ ECR (p.p.)'},
                         'backgroundColor': '#f8d7da', 'color': '#721c24', 'fontWeight': '700'},
                        {'if': {'filter_query': '{Maturidade Estimativa} = "Maduro em Estimativa"', 'column_id': 'Maturidade Estimativa'},
                         'backgroundColor': '#d4edda', 'color': '#155724', 'fontWeight': '700'},
                        {'if': {'filter_query': '{Maturidade Estimativa} = "Em evolução"', 'column_id': 'Maturidade Estimativa'},
                         'backgroundColor': '#fff3cd', 'color': '#856404', 'fontWeight': '700'},
                    ])],
                ),
            ],
        )

        pm_dev_return_table = html.P(
            'Sem ocorrências QA->Dev no período ou sem artefato de process mining compatível.',
            style={'color': '#aaa', 'fontStyle': 'italic'},
        )
        if not pm_dev_return_report.empty:
            pm_dev_return_display = pm_dev_return_report.head(80).copy()
            for _dt_col in ['Entrada QA/Teste Em', 'Retorno Dev Em']:
                if _dt_col in pm_dev_return_display.columns:
                    pm_dev_return_display[_dt_col] = pd.to_datetime(pm_dev_return_display[_dt_col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
                    pm_dev_return_display[_dt_col] = pm_dev_return_display[_dt_col].fillna('—')
            for _num_col in ['Tempo Retorno QA->Dev (dias)', 'Cycle Time Dev (dias)']:
                if _num_col in pm_dev_return_display.columns:
                    pm_dev_return_display[_num_col] = pm_dev_return_display[_num_col].apply(
                        lambda v: f'{float(v):.1f}' if pd.notna(v) else '—'
                    )
            pm_dev_return_cols = [c for c in [
                'Pessoa', 'Issue Key', 'Projeto', 'Tipo de Problema', 'Retorno Seq',
                'Entrada QA/Teste Em', 'Retorno Dev Em',
                'Status Entrada QA/Teste', 'Status Retorno Dev',
                'Tempo Retorno QA->Dev (dias)', 'Cycle Time Dev (dias)', 'Retornos QA->Dev',
            ] if c in pm_dev_return_display.columns]
            pm_dev_return_table = dash_table.DataTable(
                columns=[{"name": c, "id": c} for c in pm_dev_return_cols],
                data=pm_dev_return_display[pm_dev_return_cols].to_dict('records'),
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left', 'padding': '8px 12px',
                    'fontSize': '13px', 'whiteSpace': 'nowrap',
                    'overflow': 'hidden', 'textOverflow': 'ellipsis',
                    'maxWidth': '220px',
                },
                style_header={
                    'backgroundColor': '#6c4f3d', 'color': 'white',
                    'fontWeight': '600', 'fontSize': '12px',
                    'textTransform': 'uppercase', 'letterSpacing': '0.4px',
                    'padding': '10px 12px',
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                    {'if': {'column_id': 'Tempo Retorno QA->Dev (dias)'}, 'fontWeight': '700', 'color': '#d35400'},
                ],
                sort_action='native',
                page_size=12,
            )

        # ── Gráfico: Velocidade de Entrega (SP/Dev/Mês) com benchmarks QSM ───
        # Referência externa: QSM Benchmark Tables — Business Systems Function Points
        # (https://www.qsm.com/resources/qsm-benchmark-tables, n≈330 projetos IT)
        # Proxy: 1 SP ≈ 1 FP (calibração interna necessária para precisão)
        # Benchmarks QSM Business Systems FP/PM:
        #   Q1 median: 5.00 | Global median: 7.47 | Q4 median: 11.55
        _QSM_Q1_FP_PM     = 5.00   # Q1 (projetos pequenos, ~30 FP) — mínimo esperado
        _QSM_MEDIAN_FP_PM = 7.47   # Mediana global Business Systems
        _QSM_Q4_FP_PM     = 11.55  # Q4 (projetos grandes, ~686 FP) — alta performance

        _vel_df = per_dev[per_dev['SP_por_Mes'] > 0].copy().sort_values('SP_por_Mes', ascending=False).head(30)
        fig_velocity = go.Figure()

        if not _vel_df.empty:
            # Cor por faixa QSM
            def _vel_color(v):
                if v >= _QSM_Q4_FP_PM:  return '#1abc9c'
                if v >= _QSM_MEDIAN_FP_PM: return '#27ae60'
                if v >= _QSM_Q1_FP_PM:  return '#f39c12'
                return '#e74c3c'

            _vel_colors = [_vel_color(v) for v in _vel_df['SP_por_Mes']]
            _p75_interno = float(per_dev['SP_por_Mes'].quantile(0.75))

            fig_velocity.add_trace(go.Bar(
                x=_vel_df['Pessoa'],
                y=_vel_df['SP_por_Mes'],
                marker_color=_vel_colors,
                marker_line_width=0,
                text=[f'{v:.1f}' for v in _vel_df['SP_por_Mes']],
                textposition='outside',
                textfont=dict(size=11, color='#444'),
                customdata=_vel_df[['BU', 'Papel', 'Itens Entregues', 'SP Entregues']].values
                    if all(c in _vel_df.columns for c in ['BU', 'Papel', 'Itens Entregues', 'SP Entregues'])
                    else None,
                hovertemplate=(
                    '<b>%{x}</b><br>'
                    'SP/Mês: <b>%{y:.1f}</b><br>'
                    'BU: %{customdata[0]}<br>'
                    'Papel: %{customdata[1]}<br>'
                    'Itens Entregues: %{customdata[2]}<br>'
                    'SP Entregues: %{customdata[3]}<extra></extra>'
                ) if _vel_df.shape[0] > 0 and all(c in _vel_df.columns for c in ['BU', 'Papel', 'Itens Entregues', 'SP Entregues']) else None,
                name='SP/Mês por dev',
            ))

            # Linha: P75 interno do grupo
            fig_velocity.add_hline(
                y=_p75_interno, line_dash='dash', line_color='#2980b9', line_width=1.5,
                annotation_text=f'P75 grupo ({_p75_interno:.1f} SP/mês)',
                annotation_position='right', annotation_font_size=10, annotation_font_color='#2980b9',
            )
            # Linha QSM Q1 — floor de referência
            fig_velocity.add_hline(
                y=_QSM_Q1_FP_PM, line_dash='dot', line_color='#e67e22', line_width=1.5,
                annotation_text=f'QSM Q1 — 5.0 FP/PM (proj. pequenos)',
                annotation_position='right', annotation_font_size=10, annotation_font_color='#e67e22',
            )
            # Linha QSM Mediana global
            fig_velocity.add_hline(
                y=_QSM_MEDIAN_FP_PM, line_dash='dash', line_color='#27ae60', line_width=2,
                annotation_text=f'QSM Mediana — 7.47 FP/PM (Business Systems)',
                annotation_position='right', annotation_font_size=10, annotation_font_color='#27ae60',
            )
            # Linha QSM Q4 — alta performance
            fig_velocity.add_hline(
                y=_QSM_Q4_FP_PM, line_dash='dot', line_color='#1abc9c', line_width=1.5,
                annotation_text=f'QSM Q4 — 11.55 FP/PM (proj. grandes)',
                annotation_position='right', annotation_font_size=10, annotation_font_color='#1abc9c',
            )

        fig_velocity.update_layout(
            title=(
                f'Velocidade de Entrega por Dev — SP/Mês (proxy FP/PM)<br>'
                f'<sup>'
                f'Período: {_n_meses:.1f} meses. '
                f'Referência: QSM Benchmark Tables — Business Systems Function Points '
                f'(https://www.qsm.com/resources/qsm-benchmark-tables, n≈330 projetos IT). '
                f'Proxy: 1 SP ≈ 1 FP — calibração interna necessária para comparação precisa.'
                f'</sup>'
            ),
            xaxis=dict(title='', tickangle=-40),
            yaxis=dict(title='SP por mês (proxy FP/PM)', showgrid=True, gridcolor='#eee'),
            template='plotly_white',
            height=max(420, 22 * len(_vel_df) + 200) if not _vel_df.empty else 300,
            margin=dict(t=100, b=120, r=280),
            showlegend=False,
            plot_bgcolor='#fafafa',
        )

        # ── Gráfico: Entregues vs Puxados por BU (barras agrupadas) ──────────
        top_n_prod = min(30, len(per_dev))
        df_top = per_dev.head(top_n_prod).copy()
        color_col = 'BU' if 'BU' in df_top.columns and df_top['BU'].astype(str).str.strip().ne('').any() else None
        fig_pulled_vs_done = px.bar(
            df_top,
            x='Pessoa',
            y=['Itens Puxados', 'Itens Entregues'],
            title='Cartões Puxados vs Entregues por Dev (top 30 por Score)',
            barmode='group',
            color_discrete_map={'Itens Puxados': '#5b9bd5', 'Itens Entregues': '#2ca02c'},
            height=560,
            facet_col=color_col,
            facet_col_wrap=3 if color_col else None,
        ) if color_col else px.bar(
            df_top,
            x='Pessoa',
            y=['Itens Puxados', 'Itens Entregues'],
            title='Cartões Puxados vs Entregues por Dev (top 30 por Score)',
            barmode='group',
            color_discrete_map={'Itens Puxados': '#5b9bd5', 'Itens Entregues': '#2ca02c'},
            height=520,
        )
        fig_pulled_vs_done.update_layout(
            xaxis_tickangle=-45,
            margin=dict(b=140),
            legend_title='Métrica',
            yaxis_title='Quantidade de itens',
        )

        # Gráfico agregado por BU
        fig_bu_summary = go.Figure()
        _has_bu_data = 'BU' in per_dev.columns and per_dev['BU'].astype(str).str.strip().ne('').any()
        if _has_bu_data:
            bu_agg = per_dev.groupby('BU', dropna=False).agg(
                Devs=('Pessoa', 'count'),
                Itens_Entregues=('Itens Entregues', 'sum'),
                Itens_Puxados=('Itens Puxados', 'sum'),
                SP_Entregues=('SP Entregues', 'sum'),
                Defeitos_Entregues=('Defeitos Entregues', 'sum'),
                Commits=('Commits', 'sum'),
                PRs_Merged=('PRs Merged', 'sum'),
            ).reset_index()
            bu_agg.columns = ['BU', 'Devs', 'Itens Entregues', 'Itens Puxados', 'SP Entregues',
                               'Defeitos Entregues', 'Commits', 'PRs Merged']
            bu_agg['% Demanda Falha'] = np.where(
                bu_agg['Itens Entregues'] > 0,
                (bu_agg['Defeitos Entregues'] / bu_agg['Itens Entregues'] * 100).round(1),
                0.0,
            )
            bu_agg = bu_agg.sort_values('Itens Entregues', ascending=False)
            fig_bu_summary = px.bar(
                bu_agg,
                x='BU',
                y=['Itens Entregues', 'Commits', 'PRs Merged'],
                title='Resumo por BU/Time — Entregas, Commits e PRs Merged',
                barmode='group',
                height=460,
            )
            fig_bu_summary.update_layout(xaxis_tickangle=-30, margin=dict(b=100), legend_title='Métrica')

        # ── ICC — Índice de Concentração de Contribuição por BU ────────────────
        # HHI de commits por BU: mede se entregas estão concentradas em poucos devs.
        # HHI = Σ(commits_i/commits_BU)² — 1/N = perfeita distribuição, 1.0 = concentrado em 1.
        # HHI Norm. = (HHI - 1/N) / (1 - 1/N) — facilita comparação entre BUs de tamanhos diferentes.
        # Benchmarks: HHI < 0.10 (distribuído) | 0.10–0.25 (moderado) | >0.25 (concentrado — risco KCR).
        # Fonte: Ricca et al. (ICSE 2019) — Truck Factor; U.S. DOJ HHI standard.
        icc_table = html.Div()
        if _has_bu_data and 'Commits' in per_dev.columns:
            _icc_rows = []
            for _bu, _grp in per_dev.groupby('BU', dropna=False):
                _commits = pd.to_numeric(_grp['Commits'], errors='coerce').fillna(0)
                _total_commits = _commits.sum()
                _n_devs = len(_grp)
                if _total_commits > 0:
                    _hhi = float((_commits / _total_commits).pow(2).sum())
                else:
                    _hhi = 1.0
                _hhi_norm = max((_hhi - 1 / _n_devs) / (1 - 1 / _n_devs), 0.0) if _n_devs > 1 else 0.0
                _icc_classe = (
                    'Concentrado ⚠' if _hhi > 0.25 else
                    'Moderado' if _hhi > 0.10 else
                    'Distribuído ✓'
                )
                _icc_rows.append({
                    'BU': _bu,
                    'N Devs': _n_devs,
                    'Commits Total': int(_total_commits),
                    'ICC (HHI)': round(_hhi, 4),
                    'ICC Norm.': round(_hhi_norm, 4),
                    'Concentração': _icc_classe,
                })
            if _icc_rows:
                _icc_df = pd.DataFrame(_icc_rows).sort_values('ICC (HHI)', ascending=False)
                icc_table = html.Div([
                    html.P(
                        'ICC (Índice de Concentração de Contribuição) — HHI de commits por BU. '
                        'Valores acima de 0.25 indicam risco de concentração de conhecimento.',
                        style={'fontSize': '12px', 'color': '#555', 'marginBottom': '8px'}
                    ),
                    dash_table.DataTable(
                        columns=[{"name": c, "id": c} for c in _icc_df.columns],
                        data=_icc_df.to_dict('records'),
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'center', 'padding': '7px 10px', 'fontSize': '13px'},
                        style_cell_conditional=[{'if': {'column_id': 'BU'}, 'textAlign': 'left', 'fontWeight': 'bold'}],
                        style_header={
                            'backgroundColor': '#2c3e50', 'color': 'white',
                            'fontWeight': '600', 'fontSize': '12px',
                        },
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                            {'if': {'filter_query': '{Concentração} contains "⚠"'},
                             'backgroundColor': '#fff5f5', 'color': '#721c24'},
                            {'if': {'filter_query': '{Concentração} contains "✓"'},
                             'backgroundColor': '#f0fff4', 'color': '#155724'},
                        ],
                        sort_action='native',
                    ),
                ], style={'marginTop': '16px'})

        # ── Gráfico: Cartões puxados por complexidade (estimativa unificada) ──
        # Usa _unified_sp_bucket(): SP numérico ou T-shirt equalizado (P=2SP, M=5SP, G=8SP).
        # "Sem estimativa" só aparece para itens sem nenhum dos dois formatos.
        fig_complexity = go.Figure()
        if not complexity_df.empty:
            bucket_order = ['1-3 SP (pequeno)', '5-8 SP (médio)', '13+ SP (grande)']
            bucket_colors = {
                '1-3 SP (pequeno)': '#98df8a',
                '5-8 SP (médio)': '#ffbb78',
                '13+ SP (grande)': '#ff9896',
            }
            top_people_complexity = per_dev['Pessoa'].head(top_n_prod).tolist()
            cdf = complexity_df[complexity_df['Pessoa'].isin(top_people_complexity)].copy()
            # garante todas as faixas para todos os devs (pivot + melt)
            cdf_pivot = cdf.pivot_table(index='Pessoa', columns='SP_Bucket', values='Qtd', aggfunc='sum', fill_value=0).reset_index()
            cdf_melted = cdf_pivot.melt(id_vars='Pessoa', var_name='SP_Bucket', value_name='Qtd')
            # remove linhas com Qtd=0 para não inflar a legenda
            cdf_melted = cdf_melted[cdf_melted['Qtd'] > 0]
            # Conta "Sem estimativa" ANTES de remover — reporta no subtítulo
            _sem_est_total = int(cdf_melted.loc[cdf_melted['SP_Bucket'] == 'Sem estimativa', 'Qtd'].sum())
            _total_cx = int(cdf_melted['Qtd'].sum())
            _sem_est_pct = round(_sem_est_total / _total_cx * 100, 1) if _total_cx > 0 else 0.0

            # Remove "Sem estimativa" do gráfico — itens sem SP nem T-shirt
            # não contribuem para análise de complexidade (preencha SP ou T-shirt no Jira)
            cdf_melted = cdf_melted[cdf_melted['SP_Bucket'] != 'Sem estimativa']

            # Remove devs que ficaram sem nenhum item estimado após o filtro
            _devs_com_estimativa = cdf_melted.groupby('Pessoa')['Qtd'].sum()
            _devs_com_estimativa = _devs_com_estimativa[_devs_com_estimativa > 0].index.tolist()
            cdf_melted = cdf_melted[cdf_melted['Pessoa'].isin(_devs_com_estimativa)]

            # ordena devs pelo total estimado
            person_totals_cx = cdf_melted.groupby('Pessoa')['Qtd'].sum().sort_values(ascending=False)
            people_ordered_cx = person_totals_cx.index.tolist()

            _n_inf_cx = complexity_df.attrs.get('n_inferred', 0)
            _inf_note = (
                f' | {_n_inf_cx} itens com estimativa inferida por mediana condicional.' if _n_inf_cx > 0 else ''
            )
            _cx_subtitle = (
                f'Estimativa unificada: SP numérico > T-shirt equalizado > inferência por mediana condicional '
                f'(Kitchenham & Mendes, TSE 2004).{_inf_note}'
                + (f' Excluídos: {_sem_est_total} sem estimativa ({_sem_est_pct:.1f}%).' if _sem_est_total > 0 else '')
            )
            fig_complexity = px.bar(
                cdf_melted,
                x='Pessoa',
                y='Qtd',
                color='SP_Bucket',
                title=f'Cartões Puxados por Complexidade (Estimativa Unificada)<br><sup>{_cx_subtitle}</sup>',
                category_orders={'SP_Bucket': bucket_order, 'Pessoa': people_ordered_cx},
                color_discrete_map=bucket_colors,
                height=520,
                labels={'Qtd': 'Qtd. itens iniciados', 'SP_Bucket': 'Faixa de Complexidade'},
            )
            fig_complexity.update_layout(
                xaxis_tickangle=-45,
                margin=dict(b=140, t=90),
                legend_title='Complexidade',
                template='plotly_white',
            )

        # ── Gráfico: Demanda de Falha por Dev ─────────────────────────────────
        fig_failure_demand = go.Figure()
        has_defect_data = False
        if 'Defeitos Entregues' in per_dev.columns:
            df_defects = per_dev[per_dev['Defeitos Entregues'] > 0].head(20).copy()
            if not df_defects.empty:
                has_defect_data = True
                fig_failure_demand = px.bar(
                    df_defects,
                    x='Pessoa',
                    y='Defeitos Entregues',
                    color='% Demanda Falha',
                    color_continuous_scale='RdYlGn_r',
                    range_color=[0, 100],
                    title='Demandas de Falha Entregues por Dev (colorido por % falha)',
                    labels={'Defeitos Entregues': 'Defeitos', '% Demanda Falha': '% Falha'},
                    height=480,
                )
                fig_failure_demand.update_layout(xaxis_tickangle=-45, margin=dict(b=140))

        # ── Gráfico: Scatter Commits x Itens Entregues ────────────────────────
        df_scatter = per_dev[(per_dev['Itens Entregues'] > 0) | (per_dev['Commits'] > 0)].copy()
        fig_scatter = go.Figure()
        if not df_scatter.empty:
            fig_scatter = px.scatter(
                df_scatter,
                x='Commits',
                y='Itens Entregues',
                size=df_scatter['PRs Merged'].clip(lower=1),
                color='% Demanda Falha',
                color_continuous_scale='RdYlGn_r',
                range_color=[0, 100],
                hover_name='Pessoa',
                hover_data={
                    'Commits': ':.0f',
                    'Itens Entregues': ':.0f',
                    'SP Entregues': ':.0f',
                    'Defeitos Entregues': ':.0f',
                    '% Demanda Falha': ':.1f',
                    'PRs Merged': ':.0f',
                    'IED': ':.1f',
                },
                title='Commits (Bitbucket) × Itens Entregues (Jira) por Dev',
                labels={
                    'Commits': 'Commits no período',
                    'Itens Entregues': 'Itens concluídos no Jira',
                    '% Demanda Falha': '% Falha',
                },
                size_max=45,
                height=580,
            )
            fig_scatter.update_traces(marker=dict(line=dict(width=1, color='white'), opacity=0.88))
            fig_scatter.add_hline(y=0, line_dash='dash', line_color='#aaa', opacity=0.5)
            fig_scatter.add_vline(x=0, line_dash='dash', line_color='#aaa', opacity=0.5)
            fig_scatter.update_layout(template='plotly_white', margin=dict(t=60, b=50))

        period_label = f"{start_ts_prod.date()} → {end_ts_prod.date()}"

        # ── Gráfico: Breakdown de tipos de demanda por dev ────────────────────
        fig_category_breakdown = go.Figure()
        _cat_colors = {
            'Defeitos':        '#e74c3c',
            'Desenvolvimento': '#2980b9',
            'Melhorias':       '#27ae60',
            'Melhoria':        '#27ae60',
            'Feature':         '#1abc9c',
            'Técnico':         '#8e44ad',
            'Tecnico':         '#8e44ad',
            'Suporte':         '#f39c12',
            'Operacional':     '#e67e22',
            'Outro':           '#34495e',
        }
        if not category_df.empty and 'WorkItemCategory' in category_df.columns:
            # Top 20 devs por Itens Entregues
            _top_devs_cat = per_dev.head(20)['Pessoa'].tolist()
            _cat_filtered = category_df[category_df['Pessoa'].isin(_top_devs_cat)].copy()
            # Ordenar devs pelo ranking de IED (mesma ordem do per_dev)
            _pessoa_order = per_dev[per_dev['Pessoa'].isin(_top_devs_cat)]['Pessoa'].tolist()
            _all_cats = sorted(_cat_filtered['WorkItemCategory'].dropna().unique())
            for _cat in _all_cats:
                _cat_data = _cat_filtered[_cat_filtered['WorkItemCategory'] == _cat]
                _cat_map = _cat_data.set_index('Pessoa')['Pct']
                _y_vals = [float(_cat_map.get(p, 0)) for p in _pessoa_order]
                fig_category_breakdown.add_trace(go.Bar(
                    name=_cat,
                    x=_pessoa_order,
                    y=_y_vals,
                    marker_color=_cat_colors.get(_cat, '#16a085'),
                    hovertemplate=f'<b>%{{x}}</b><br>{_cat}: %{{y:.1f}}%<extra></extra>',
                ))
            fig_category_breakdown.update_layout(
                barmode='stack',
                title='Composição de Demanda por Dev — Top 20 (% por tipo de WorkItem entregue)',
                xaxis_tickangle=-40,
                yaxis=dict(title='% dos itens entregues', range=[0, 100]),
                height=480,
                legend=dict(orientation='h', yanchor='bottom', y=-0.45, x=0.5, xanchor='center'),
                margin=dict(t=60, b=160),
                template='plotly_white',
            )

        def _make_bottleneck_fig(df: pd.DataFrame, label: str) -> go.Figure:
            """Gráfico de barras horizontais: Horas em Gargalo por dev (top 25)."""
            _df = df[df['Horas em Gargalo'].notna() & (df['Horas em Gargalo'] > 0)].copy()
            if _df.empty:
                return go.Figure()
            _df = _df.nlargest(25, 'Horas em Gargalo').sort_values('Horas em Gargalo')
            _fig = px.bar(
                _df,
                x='Horas em Gargalo',
                y='Pessoa',
                orientation='h',
                color='% Horas em Gargalo',
                color_continuous_scale='YlOrRd',
                range_color=[0, 100],
                title=f'Horas em Status de Gargalo por Dev (top 25) — Gargalos: {label or "—"}',
                labels={
                    'Horas em Gargalo': 'Horas acumuladas em gargalo',
                    '% Horas em Gargalo': '% do total de horas',
                },
                height=max(340, 34 * len(_df) + 120),
                hover_data={'% Horas em Gargalo': ':.1f'},
            )
            _fig.update_layout(template='plotly_white', margin=dict(t=60, b=40, l=160))
            _fig.update_coloraxes(colorbar_title='% do total')
            return _fig

        # ── Radar com benchmarks absolutos + Perfil Alvo + Distância ao Ideal ──
        #
        # Benchmarks por dimensão (baseados na literatura):
        #   Entrega        → P75 do grupo no período     (Jørgensen 2023: top 50% = 2.44× bottom)
        #   Flow Efficiency→ ≥ 80% completion rate       (Anderson 2010 — Kanban / Little's Law)
        #   Revisão        → Qualidade Revisão ≥ 70%     (Forsgren et al. 2021 — SPACE framework)
        #   Conformance    → Conformance Quality ≥ 75%   (Caldeira et al., ICPM 2019)
        #   Anti-Retrab.   → Rework Rate ≤ 20% → ≥ 80   (Caldeira et al. 2021; Shah et al. 2023)
        #
        # Normalização: valor / benchmark × 100, cap 100.
        # 100 = atingiu o benchmark; > 100 truncado; < 100 = abaixo do esperado.
        # Distância ao Ideal = distância euclidiana normalizada ao vetor [100,100,100,100,100].
        # Score Benchmark = 100 − Distância ao Ideal (0-100; maior = mais próximo do ideal).

        _radar_categories = ['Entrega', 'Flow Efficiency', 'Revisão', 'Conformance', 'Anti-Retrabalho']
        _radar_cols_bench = ['_rb_entrega', '_rb_flow', '_rb_revisao', '_rb_processo', '_rb_qualidade']

        def _abs_norm(series, benchmark):
            """Normaliza para benchmark absoluto (100 = atingiu). Cap em 100."""
            s = pd.to_numeric(series, errors='coerce').fillna(0)
            return (s / max(benchmark, 0.01) * 100).clip(0, 100)

        # Calcula benchmarks sobre TODOS os devs do período
        _score_cx_col = 'Score Complexidade' if 'Score Complexidade' in per_dev.columns else 'Itens Entregues'
        _bench_entrega = max(float(per_dev[_score_cx_col].quantile(0.75)), 0.1)
        _bench_commits  = max(float(per_dev['Commits'].quantile(0.75)), 1.0)

        # Eixo 1: Entrega — P75 do grupo (Jørgensen 2023)
        per_dev['_rb_entrega'] = _abs_norm(per_dev[_score_cx_col], _bench_entrega)

        # Eixo 2: Flow Efficiency — ≥80% dos itens puxados entregues no período
        # Usa FE Ajustada (corrigida para WIP cross-period) para evitar saturação artificial
        # em devs que entregam itens de períodos anteriores (Anderson 2010, Kanban / Little's Law)
        _fe_rb_col = 'FE Ajustada (%)' if 'FE Ajustada (%)' in per_dev.columns else 'Flow Efficiency (%)'
        if _fe_rb_col in per_dev.columns:
            per_dev['_rb_flow'] = _abs_norm(per_dev[_fe_rb_col], 80.0)
        else:
            per_dev['_rb_flow'] = pd.Series(0.0, index=per_dev.index)

        # Eixo 3: Revisão — Qualidade Revisão ≥70% (Forsgren et al. 2021 — SPACE)
        if 'Qualidade Revisao' in per_dev.columns:
            per_dev['_rb_revisao'] = _abs_norm(per_dev['Qualidade Revisao'], 70.0)
        else:
            per_dev['_rb_revisao'] = _abs_norm(per_dev['Aprovacoes'], _bench_commits)

        # Eixo 4: Conformance — Conformance Quality ≥75% (Caldeira et al. 2019)
        if 'Conformance Quality (%)' in per_dev.columns and per_dev['Conformance Quality (%)'].notna().any():
            per_dev['_rb_processo'] = _abs_norm(per_dev['Conformance Quality (%)'], 75.0)
        else:
            per_dev['_rb_processo'] = pd.Series(0.0, index=per_dev.index)

        # Eixo 5: Anti-Retrabalho — Rework ≤20% → Anti ≥80 (Caldeira 2021; Shah et al. 2023)
        if 'Rework Rate PM (%)' in per_dev.columns and per_dev['Rework Rate PM (%)'].notna().any():
            per_dev['_rb_qualidade'] = _abs_norm(
                100 - per_dev['Rework Rate PM (%)'].fillna(50), 80.0
            )
        else:
            per_dev['_rb_qualidade'] = _abs_norm(
                100 - per_dev['% Demanda Falha'].clip(0, 100), 80.0
            )

        # Distância ao Ideal e Score Benchmark (todos os devs)
        _ideal_vec = np.array([100.0] * 5)
        _max_dist = float(np.sqrt(5 * 100 ** 2))
        for _idx in per_dev.index:
            _vec = np.array([float(per_dev.loc[_idx, c]) for c in _radar_cols_bench])
            _dist = float(np.sqrt(np.sum((_ideal_vec - _vec) ** 2))) / _max_dist * 100
            per_dev.loc[_idx, 'Distancia ao Ideal'] = round(_dist, 1)
            per_dev.loc[_idx, 'Score Benchmark']    = round(100 - _dist, 1)

        # Constrói o radar com os top 10 por IED
        fig_radar = go.Figure()
        _radar_top = per_dev.head(10).copy()
        if not _radar_top.empty:
            _radar_colors = [
                '#2980b9', '#27ae60', '#8e44ad', '#e67e22', '#c0392b',
                '#16a085', '#d35400', '#2c3e50', '#1abc9c', '#e74c3c',
            ]
            _cats_closed = _radar_categories + [_radar_categories[0]]

            for _ri, (_ridx, _rrow) in enumerate(_radar_top.iterrows()):
                _vals = [float(_rrow[c]) for c in _radar_cols_bench]
                _nome_parts = str(_rrow['Pessoa']).split()
                _short_name = (
                    f"{_nome_parts[0]} {_nome_parts[-1]}"
                    if len(_nome_parts) > 1 else str(_rrow['Pessoa'])
                )
                _sb = _rrow.get('Score Benchmark', 0)
                fig_radar.add_trace(go.Scatterpolar(
                    r=_vals + [_vals[0]],
                    theta=_cats_closed,
                    fill='toself',
                    name=f"{_short_name} (SB={_sb:.0f})",
                    opacity=0.55,
                    line=dict(color=_radar_colors[_ri % len(_radar_colors)], width=2),
                    hovertemplate=(
                        f"<b>{_short_name}</b><br>"
                        "Dimensão: %{theta}<br>Valor: %{r:.1f}/100<extra></extra>"
                    ),
                ))

            # Traço de referência: Mínimo Esperado = 75 em todos os eixos
            fig_radar.add_trace(go.Scatterpolar(
                r=[75] * 5 + [75],
                theta=_cats_closed,
                fill=None,
                name='Mínimo Esperado (75)',
                line=dict(color='#f39c12', width=2.5, dash='dash'),
                opacity=1.0,
            ))
            # Traço de referência: Excelência = 100 em todos os eixos
            fig_radar.add_trace(go.Scatterpolar(
                r=[100] * 5 + [100],
                theta=_cats_closed,
                fill=None,
                name='Excelência (100)',
                line=dict(color='#27ae60', width=2.5, dash='dot'),
                opacity=1.0,
            ))

            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True, range=[0, 100],
                        tickvals=[25, 50, 75, 100],
                        tickfont=dict(size=9), gridcolor='#e0e0e0',
                    ),
                    angularaxis=dict(tickfont=dict(size=12)),
                ),
                showlegend=True,
                height=640,
                title=(
                    'Perfil Multidimensional com Benchmarks Absolutos — Top 10 por IED<br>'
                    '<sup>'
                    'SB = Score Benchmark (0-100; maior = mais próximo do ideal) | '
                    'Entrega: P75 grupo (Jørgensen, IST 2023) | '
                    'Flow Efficiency: ≥80% itens puxados entregues (Anderson 2010 — Kanban/Little\'s Law) | '
                    'Revisão: ≥70% (Forsgren et al., ACM Queue 2021 — SPACE) | '
                    'Conformance: ≥75% (Caldeira et al., ICPM 2019) | '
                    'Anti-Retrabalho: Rework≤20% (Caldeira 2021; Shah et al., ICSME 2023)'
                    '</sup>'
                ),
                template='plotly_white',
                legend=dict(
                    orientation='h', yanchor='bottom', y=-0.45,
                    x=0.5, xanchor='center', font=dict(size=10),
                ),
                margin=dict(t=110, b=170),
            )

        # ── Comparativo por Papel (Tech Lead vs Dev) ──────────────────────────
        fig_papel = go.Figure()
        _has_papel = 'Papel' in per_dev.columns and per_dev['Papel'].astype(str).str.strip().ne('').any()
        papel_kpi_section = html.Span()
        if _has_papel:
            _score_cx_col_p = 'Score Complexidade' if 'Score Complexidade' in per_dev.columns else 'Itens Entregues'
            papel_agg = per_dev.groupby('Papel', dropna=False).agg(
                Devs=('Pessoa', 'count'),
                Itens_Entregues_Med=('Itens Entregues', 'median'),
                Score_Cx_Med=(_score_cx_col_p, 'median'),
                Commits_Med=('Commits', 'median'),
                PRs_Merged_Med=('PRs Merged', 'median'),
                Aprovacoes_Med=('Aprovacoes', 'median'),
                Falha_Med=('% Demanda Falha', 'median'),
                LT_Med=('Lead Time Mediano (dias)', 'median'),
                QualRev_Med=('Qualidade Revisao', 'median'),
            ).reset_index()
            papel_agg.columns = [
                'Papel', 'Devs', 'Itens Entregues (med)', 'Score Complexidade (med)',
                'Commits (med)', 'PRs Merged (med)', 'Aprovações (med)',
                '% Demanda Falha (med)', 'Lead Time (med, dias)', 'Qualidade Revisão (med %)',
            ]
            _metricas_papel = [
                'Itens Entregues (med)', 'Score Complexidade (med)', 'Commits (med)',
                'PRs Merged (med)', 'Aprovações (med)',
            ]
            _papel_melted = papel_agg.melt(
                id_vars='Papel', value_vars=_metricas_papel,
                var_name='Métrica', value_name='Mediana',
            )
            fig_papel = px.bar(
                _papel_melted,
                x='Métrica',
                y='Mediana',
                color='Papel',
                barmode='group',
                title='Benchmark por Papel — Medianas (Tech Lead vs Dev)',
                color_discrete_map={'Tech Lead': '#e67e22', 'Dev': '#2980b9'},
                height=420,
                labels={'Mediana': 'Valor mediano'},
            )
            fig_papel.update_layout(xaxis_tickangle=-20, margin=dict(b=100), legend_title='Papel')

            # Mini KPIs de comparação
            _papel_rows = papel_agg.set_index('Papel').to_dict('index')
            _kpi_papel_cards = []
            for _p, _pdata in _papel_rows.items():
                _bg = '#fff8f0' if _p == 'Tech Lead' else '#f0f6ff'
                _border = '#e67e22' if _p == 'Tech Lead' else '#2980b9'
                _kpi_papel_cards.append(html.Div([
                    html.Div(_p, style={
                        'fontWeight': '700', 'fontSize': '13px',
                        'color': _border, 'marginBottom': '6px',
                        'borderBottom': f'2px solid {_border}', 'paddingBottom': '4px',
                    }),
                    html.Div(f"Devs: {int(_pdata.get('Devs', 0))}", style={'fontSize': '12px', 'marginBottom': '2px'}),
                    html.Div(f"Itens med.: {_pdata.get('Itens Entregues (med)', 0):.1f}", style={'fontSize': '12px', 'marginBottom': '2px'}),
                    html.Div(f"Score Cx med.: {_pdata.get('Score Complexidade (med)', 0):.1f}", style={'fontSize': '12px', 'marginBottom': '2px'}),
                    html.Div(f"Commits med.: {_pdata.get('Commits (med)', 0):.1f}", style={'fontSize': '12px', 'marginBottom': '2px'}),
                    html.Div(f"Qual. Revisão: {_pdata.get('Qualidade Revisão (med %)', 0):.1f}%", style={'fontSize': '12px', 'marginBottom': '2px'}),
                    html.Div(f"% Falha med.: {_pdata.get('% Demanda Falha (med)', 0):.1f}%", style={'fontSize': '12px'}),
                ], style={
                    'background': _bg, 'border': f'1px solid {_border}',
                    'borderRadius': '8px', 'padding': '10px 14px',
                    'minWidth': '180px', 'flex': '1',
                }))
            papel_kpi_section = html.Div(_kpi_papel_cards, style={
                'display': 'flex', 'flexWrap': 'wrap', 'gap': '12px', 'marginBottom': '16px',
            })

        # ── Fig: IED Sparklines — evolução temporal mensal ───────────────────────
        from plotly.subplots import make_subplots as _make_subplots
        _spark_devs = sorted(
            _monthly_ied_data.keys(),
            key=lambda p: next((per_dev.loc[per_dev['Pessoa'] == p, 'IED'].values[0]
                                 for _ in [None] if p in per_dev['Pessoa'].values), 0),
            reverse=True,
        )[:20]
        fig_ied_sparklines = go.Figure()
        _spark_palette = [
            '#27ae60','#2980b9','#8e44ad','#e67e22','#e74c3c',
            '#1abc9c','#f39c12','#3498db','#9b59b6','#c0392b',
            '#16a085','#d35400','#2c3e50','#7f8c8d','#e91e63',
            '#00bcd4','#8bc34a','#ff5722','#607d8b','#795548',
        ]
        if _spark_devs:
            _n_cols_spark = min(4, len(_spark_devs))
            _n_rows_spark = -(-len(_spark_devs) // _n_cols_spark)  # ceiling div
            fig_ied_sparklines = _make_subplots(
                rows=_n_rows_spark, cols=_n_cols_spark,
                subplot_titles=[p.split()[0] for p in _spark_devs],
                shared_yaxes=False,
            )
            for _si, _sdev in enumerate(_spark_devs):
                _spts = _monthly_ied_data[_sdev]
                _sx = [p[0] for p in _spts]
                _sy = [p[1] for p in _spts]
                _srow = _si // _n_cols_spark + 1
                _scol = _si % _n_cols_spark + 1
                _scol_hex = _spark_palette[_si % len(_spark_palette)]
                fig_ied_sparklines.add_trace(
                    go.Scatter(
                        x=_sx, y=_sy,
                        mode='lines+markers',
                        line=dict(color=_scol_hex, width=2),
                        marker=dict(size=5, color=_scol_hex),
                        name=_sdev,
                        showlegend=False,
                        hovertemplate='%{x}: <b>%{y:.1f}</b><extra></extra>',
                    ),
                    row=_srow, col=_scol,
                )
                # Faixa de referência: 70 = mínimo esperado
                fig_ied_sparklines.add_hline(
                    y=70, line_dash='dot', line_color='#e67e22', line_width=1,
                    row=_srow, col=_scol,
                )
            fig_ied_sparklines.update_yaxes(range=[0, 105], showgrid=True, gridcolor='#f0f0f0')
            fig_ied_sparklines.update_layout(
                title=dict(
                    text='Evolução Mensal do IED por Desenvolvedor<br>'
                         '<sup>Linha laranja pontilhada = mínimo esperado (IED 70). '
                         'Top 20 por IED. Devs com < 2 entregas/mês excluídos do mês.</sup>',
                    font=dict(size=13),
                ),
                height=max(240, 200 * _n_rows_spark),
                margin=dict(t=80, b=30, l=40, r=20),
                template='plotly_white',
                plot_bgcolor='#fafafa',
            )

        # ── Fig: WIP Médio × Lead Time — Little's Law scatter ─────────────────
        _ied_class_colors = {
            'Excelente': '#27ae60', 'Bom': '#2ecc71',
            'Regular': '#f39c12', 'Abaixo do Esperado': '#e67e22', 'Crítico': '#e74c3c',
        }
        _wip_lt_df = per_dev[
            per_dev['WIP Medio'].notna() &
            per_dev['Lead Time Mediano (dias)'].gt(0) &
            per_dev['IED'].gt(0)
        ].copy() if 'WIP Medio' in per_dev.columns else pd.DataFrame()

        fig_wip_lt = go.Figure()
        if not _wip_lt_df.empty:
            _wlt_colors = _wip_lt_df['IED Classe'].map(_ied_class_colors).fillna('#aaa')
            _wlt_sizes = (_wip_lt_df['IED'] / 100 * 36 + 10).clip(10, 48)
            fig_wip_lt.add_trace(go.Scatter(
                x=_wip_lt_df['WIP Medio'],
                y=_wip_lt_df['Lead Time Mediano (dias)'],
                mode='markers+text',
                marker=dict(
                    size=_wlt_sizes,
                    color=_wlt_colors,
                    opacity=0.82,
                    line=dict(width=1.5, color='white'),
                ),
                text=_wip_lt_df['Pessoa'].apply(lambda n: n.split()[0]),
                textposition='top center',
                textfont=dict(size=9),
                customdata=_wip_lt_df[['IED', 'IED Classe', 'Itens Entregues', 'WIP Medio']].values,
                hovertemplate=(
                    '<b>%{text}</b><br>'
                    'WIP Médio: %{customdata[3]:.2f} itens<br>'
                    'LT Mediano: %{y:.1f} dias<br>'
                    'IED: %{customdata[0]:.1f} (%{customdata[1]})<br>'
                    'Itens Entregues: %{customdata[2]}<extra></extra>'
                ),
            ))
            # Linha diagonal: LT = WIP / (TP_equipe/dev) — referência Little's Law
            _wlt_x_max = float(_wip_lt_df['WIP Medio'].max()) * 1.1
            fig_wip_lt.add_trace(go.Scatter(
                x=[0, _wlt_x_max], y=[0, _wlt_x_max * float(_wip_lt_df['Lead Time Mediano (dias)'].median())
                                       / max(float(_wip_lt_df['WIP Medio'].median()), 0.01)],
                mode='lines',
                line=dict(color='#aaa', dash='dash', width=1),
                name='Tendência mediana',
                showlegend=False,
                hoverinfo='skip',
            ))
        fig_wip_lt.update_layout(
            title=dict(
                text='WIP Médio × Lead Time Mediano (Little\'s Law)<br>'
                     '<sup>WIP_avg = Throughput × CT (Little 1961). '
                     'Bolha ∝ IED. Alto WIP crônico → LT alto → queda de previsibilidade.</sup>',
                font=dict(size=13),
            ),
            xaxis=dict(title='WIP Médio (itens simultâneos estimados)', gridcolor='#f0f0f0'),
            yaxis=dict(title='Lead Time Mediano (dias)', gridcolor='#f0f0f0'),
            template='plotly_white',
            height=460,
            margin=dict(t=80, b=50, l=60, r=30),
            plot_bgcolor='#fafafa',
        )

        # ── Fig: Previsibilidade de Lead Time — P85/P50 por dev ───────────────
        _prev_df = per_dev[
            per_dev['Razão P85/P50'].notna() &
            per_dev['IED'].gt(0)
        ].copy() if 'Razão P85/P50' in per_dev.columns else pd.DataFrame()
        _prev_df = _prev_df.sort_values('Razão P85/P50', ascending=True)

        _prev_colors_map = {'Previsível': '#27ae60', 'Moderado': '#f39c12', 'Imprevisível': '#e74c3c', '—': '#aaa'}
        fig_lt_predictability = go.Figure()
        if not _prev_df.empty:
            _pc_list = _prev_df['Previsibilidade LT'].map(_prev_colors_map).fillna('#aaa').tolist()
            fig_lt_predictability.add_trace(go.Bar(
                y=_prev_df['Pessoa'],
                x=_prev_df['Razão P85/P50'],
                orientation='h',
                marker_color=_pc_list,
                marker_line_width=0,
                text=[f'{v:.2f}' for v in _prev_df['Razão P85/P50']],
                textposition='outside',
                customdata=_prev_df[['Lead Time P50 (dias)', 'Lead Time P85 (dias)', 'Previsibilidade LT']].values,
                hovertemplate=(
                    '<b>%{y}</b><br>'
                    'Razão P85/P50: <b>%{x:.2f}</b><br>'
                    'P50: %{customdata[0]:.1f} dias | P85: %{customdata[1]:.1f} dias<br>'
                    'Classificação: <b>%{customdata[2]}</b><extra></extra>'
                ),
            ))
            # Linhas de referência
            fig_lt_predictability.add_vline(x=2.0, line_dash='dot', line_color='#27ae60', line_width=1.5,
                                             annotation_text='≤2 Previsível', annotation_position='top right',
                                             annotation_font_size=10)
            fig_lt_predictability.add_vline(x=3.0, line_dash='dot', line_color='#e67e22', line_width=1.5,
                                             annotation_text='≤3 Moderado', annotation_position='top right',
                                             annotation_font_size=10)
        fig_lt_predictability.update_layout(
            title=dict(
                text='Previsibilidade de Lead Time — Razão P85/P50<br>'
                     '<sup>Verde ≤2 (Previsível) | Laranja ≤3 (Moderado) | Vermelho >3 (Imprevisível). '
                     'Reinertsen (2009) — Product Development Flow.</sup>',
                font=dict(size=13),
            ),
            xaxis=dict(title='Razão P85/P50', gridcolor='#f0f0f0'),
            yaxis=dict(title='', automargin=True),
            template='plotly_white',
            height=max(340, 28 * max(len(_prev_df), 1) + 120),
            margin=dict(t=80, b=50, l=180, r=80),
            plot_bgcolor='#fafafa',
        )

        # ── Fig: Δ IED Trend — variação mensal primeiro → último mês ──────────
        _trend_df = per_dev[per_dev['Δ IED Trend'].notna()].copy() if 'Δ IED Trend' in per_dev.columns else pd.DataFrame()
        _trend_df = _trend_df.sort_values('Δ IED Trend', ascending=True)
        fig_delta_ied = go.Figure()
        if not _trend_df.empty:
            _trend_colors = ['#27ae60' if v >= 0 else '#e74c3c' for v in _trend_df['Δ IED Trend']]
            fig_delta_ied.add_trace(go.Bar(
                y=_trend_df['Pessoa'],
                x=_trend_df['Δ IED Trend'],
                orientation='h',
                marker_color=_trend_colors,
                marker_line_width=0,
                text=[f'{v:+.1f}' for v in _trend_df['Δ IED Trend']],
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Δ IED: <b>%{x:+.1f}</b><extra></extra>',
            ))
            fig_delta_ied.add_vline(x=0, line_color='#495057', line_width=1.5)
        fig_delta_ied.update_layout(
            title=dict(
                text='Δ IED Trend — Variação Mensal (Primeiro → Último Mês com Dados)<br>'
                     '<sup>Verde = dev melhorando | Vermelho = dev em queda. '
                     'Disponível apenas para períodos com ≥ 2 meses de dados.</sup>',
                font=dict(size=13),
            ),
            xaxis=dict(title='Variação do IED (pontos)', gridcolor='#f0f0f0'),
            yaxis=dict(title='', automargin=True),
            template='plotly_white',
            height=max(300, 28 * max(len(_trend_df), 1) + 100),
            margin=dict(t=80, b=50, l=180, r=80),
            plot_bgcolor='#fafafa',
        )

        # ── Fig: Δ ECR — variação mensal da confiabilidade de estimativa ─────
        _ecr_trend_df = per_dev[per_dev['Δ ECR (p.p.)'].notna()].copy() if 'Δ ECR (p.p.)' in per_dev.columns else pd.DataFrame()
        _ecr_trend_df = _ecr_trend_df.sort_values('Δ ECR (p.p.)', ascending=True)
        fig_delta_ecr = go.Figure()
        if not _ecr_trend_df.empty:
            _ecr_streak_hover_label = f'Streak ECR≥{_ECR_MATURITY_THRESHOLD:.0f}%: '
            def _ecr_color(row):
                if row.get('Maturidade Estimativa') == 'Maduro em Estimativa':
                    return '#27ae60'
                return '#2980b9' if float(row.get('Δ ECR (p.p.)', 0) or 0) >= 0 else '#e74c3c'
            _ecr_colors = [_ecr_color(row) for _, row in _ecr_trend_df.iterrows()]
            fig_delta_ecr.add_trace(go.Bar(
                y=_ecr_trend_df['Pessoa'],
                x=_ecr_trend_df['Δ ECR (p.p.)'],
                orientation='h',
                marker_color=_ecr_colors,
                marker_line_width=0,
                text=[f'{v:+.1f}' for v in _ecr_trend_df['Δ ECR (p.p.)']],
                textposition='outside',
                customdata=_ecr_trend_df[['ECR', 'Meses ECR>=80 Consecutivos', 'Maturidade Estimativa']].values,
                hovertemplate=(
                    '<b>%{y}</b><br>'
                    'Δ ECR: <b>%{x:+.1f} p.p.</b><br>'
                    'ECR atual: %{customdata[0]:.1f}%<br>'
                    + _ecr_streak_hover_label + '%{customdata[1]} mês(es)<br>'
                    'Status: <b>%{customdata[2]}</b><extra></extra>'
                ),
            ))
            fig_delta_ecr.add_vline(x=0, line_color='#495057', line_width=1.5)
        fig_delta_ecr.update_layout(
            title=dict(
                text='Δ ECR — Tendência Mensal da Confiabilidade de Estimativa<br>'
                     f'<sup>Meta: ECR ≥ {_ECR_MATURITY_THRESHOLD:.0f}% por {_ECR_MATURITY_STREAK} meses consecutivos = maduro em estimativa.</sup>',
                font=dict(size=13),
            ),
            xaxis=dict(title='Variação do ECR (pontos percentuais)', gridcolor='#f0f0f0'),
            yaxis=dict(title='', automargin=True),
            template='plotly_white',
            height=max(300, 28 * max(len(_ecr_trend_df), 1) + 110),
            margin=dict(t=80, b=50, l=180, r=90),
            plot_bgcolor='#fafafa',
        )

        # ── Fig: Heatmap Mensal IED ────────────────────────────────────────────
        # Visualização matricial: devs como linhas, meses como colunas, cor = classe IED.
        # Permite identificar padrões de melhora/queda consistentes ao longo do tempo.
        _ied_class_color = {
            'Excelente': '#27ae60', 'Bom': '#2980b9',
            'Regular': '#f39c12', 'Abaixo do Esperado': '#e67e22', 'Crítico': '#e74c3c',
        }
        fig_ied_heatmap = go.Figure()
        if _monthly_ied_data:
            _all_months_ordered = []
            _seen_months = set()
            for _pts in _monthly_ied_data.values():
                for _ml, _ in _pts:
                    if _ml not in _seen_months:
                        _all_months_ordered.append(_ml)
                        _seen_months.add(_ml)

            _heatmap_devs = sorted(
                _monthly_ied_data.keys(),
                key=lambda p: -max((v for _, v in _monthly_ied_data[p]), default=0),
            )[:30]

            _heatmap_z = []
            _heatmap_text = []
            for _dev in _heatmap_devs:
                _pts_map = dict(_monthly_ied_data[_dev])
                _row_z = [_pts_map.get(_m, None) for _m in _all_months_ordered]
                _row_text = [
                    f'{v:.0f}' if v is not None else '' for v in _row_z
                ]
                _heatmap_z.append(_row_z)
                _heatmap_text.append(_row_text)

            fig_ied_heatmap.add_trace(go.Heatmap(
                z=_heatmap_z,
                x=_all_months_ordered,
                y=_heatmap_devs,
                text=_heatmap_text,
                texttemplate='%{text}',
                colorscale=[
                    [0.0,  '#e74c3c'],   # Crítico (<30)
                    [0.30, '#e67e22'],   # Abaixo do Esperado (30-49)
                    [0.50, '#f39c12'],   # Regular (50-69)
                    [0.70, '#2980b9'],   # Bom (70-84)
                    [0.85, '#27ae60'],   # Excelente (≥85)
                    [1.0,  '#1a7a45'],
                ],
                zmin=0, zmax=100,
                colorbar=dict(
                    title='IED', tickvals=[0, 30, 50, 70, 85, 100],
                    ticktext=['0', '30 Crítico', '50 Regular', '70 Bom', '85 Excel.', '100'],
                    len=0.7,
                ),
                hovertemplate='<b>%{y}</b><br>%{x}<br>IED: <b>%{z:.1f}</b><extra></extra>',
            ))
            fig_ied_heatmap.update_layout(
                title=dict(
                    text='Heatmap Mensal IED — Top 30 Devs<br>'
                         '<sup>Verde = Excelente | Azul = Bom | Laranja = Regular | Vermelho = Crítico. Branco = sem dados.</sup>',
                    font=dict(size=13),
                ),
                xaxis=dict(title='', side='top', tickangle=-30),
                yaxis=dict(title='', automargin=True, autorange='reversed'),
                template='plotly_white',
                height=max(350, 28 * len(_heatmap_devs) + 120),
                margin=dict(t=100, b=30, l=180, r=60),
            )

        # ── Fig: Vazão Semanal por Pessoa (Produtividade Dev) ─────────────────
        fig_vazao_semanal_dev = go.Figure()
        _vzs_top_n = 10
        if not df_prod_base.empty and 'Responsavel' in df_prod_base.columns and 'DataDone' in df_prod_base.columns:
            _vzs_df = df_prod_base.copy()
            _vzs_df['DataDone'] = pd.to_datetime(_vzs_df['DataDone'], errors='coerce')
            _vzs_df = _vzs_df[
                _vzs_df['DataDone'].notna() &
                (_vzs_df['DataDone'] >= start_ts_prod) &
                (_vzs_df['DataDone'] < end_ts_prod)
            ].copy()
            _vzs_df['Pessoa'] = _vzs_df['Responsavel'].apply(lambda x: _canonical_person_name(x, alias_index=alias_index_prod))
            _vzs_df = _vzs_df[_vzs_df['Pessoa'].astype(str).str.strip().ne('')]
            _vzs_df['Semana'] = _vzs_df['DataDone'].dt.to_period('W').apply(lambda p: p.start_time)
            _vzs_weekly = _vzs_df.groupby(['Pessoa', 'Semana']).size().reset_index(name='Itens')

            # Top N devs por total de itens no período
            _vzs_top_devs = (
                _vzs_weekly.groupby('Pessoa')['Itens'].sum()
                .nlargest(_vzs_top_n).index.tolist()
            )
            _vzs_palette = [
                '#2980b9', '#27ae60', '#e74c3c', '#f39c12', '#8e44ad',
                '#16a085', '#d35400', '#2c3e50', '#c0392b', '#1abc9c',
            ]
            for _vzs_i, _vzs_dev in enumerate(_vzs_top_devs):
                _vzs_sub = _vzs_weekly[_vzs_weekly['Pessoa'] == _vzs_dev].sort_values('Semana')
                fig_vazao_semanal_dev.add_trace(go.Scatter(
                    x=_vzs_sub['Semana'],
                    y=_vzs_sub['Itens'],
                    mode='lines+markers',
                    name=_vzs_dev,
                    line=dict(color=_vzs_palette[_vzs_i % len(_vzs_palette)], width=2),
                    marker=dict(size=5),
                    hovertemplate='<b>%{fullData.name}</b><br>Semana: %{x|%d/%m/%Y}<br>Itens: <b>%{y}</b><extra></extra>',
                ))
            if fig_vazao_semanal_dev.data:
                fig_vazao_semanal_dev.update_layout(
                    title=dict(
                        text=f'Vazão Semanal por Pessoa — Top {_vzs_top_n} Devs<br>'
                             '<sup>Itens entregues (DataDone) por semana. Cada linha = um desenvolvedor.</sup>',
                        font=dict(size=13),
                    ),
                    xaxis=dict(title='Semana', tickformat='%d/%m/%Y', tickangle=-30),
                    yaxis=dict(title='Itens Entregues'),
                    legend=dict(orientation='v', x=1.01, y=1),
                    template='plotly_white',
                    height=420,
                    margin=dict(t=90, b=60, l=60, r=200),
                )

        # ── Fig: Review Reciprocity Matrix ────────────────────────────────────
        # Matriz de calor: linhas = revisor, colunas = autor revisado.
        # Detecta silos de revisão (TL revisa tudo, devs não revisam entre si).
        fig_review_reciprocity = go.Figure()
        _reciprocity_df = pd.DataFrame()
        for _bb_proj_key in bb_projects:
            _bb_logs = load_project_bitbucket_logs(_bb_proj_key)
            if not isinstance(_bb_logs, dict):
                continue
            _prs_raw = _bb_logs.get('pullrequests', pd.DataFrame())
            if _prs_raw.empty or 'author' not in _prs_raw.columns:
                continue
            if 'created_on' in _prs_raw.columns:
                _prs_win = _prs_raw[
                    (_prs_raw['created_on'] >= start_ts_prod) & (_prs_raw['created_on'] < end_ts_prod)
                ].copy()
            else:
                _prs_win = _prs_raw.copy()

            _recip_rows = []
            for _, _pr_row in _prs_win.iterrows():
                _pr_author = _canonical_person_name(_pr_row.get('author'), alias_index=alias_index_prod)
                if not _pr_author:
                    continue
                for _rev_name in _split_people_field(_pr_row.get('approved_by', '')):
                    _rev = _canonical_person_name(_rev_name, alias_index=alias_index_prod)
                    if _rev and _rev != _pr_author:
                        _recip_rows.append({'Revisor': _rev, 'Autor': _pr_author})
                for _rev_name in _split_people_field(_pr_row.get('changes_requested_by', '')):
                    _rev = _canonical_person_name(_rev_name, alias_index=alias_index_prod)
                    if _rev and _rev != _pr_author:
                        _recip_rows.append({'Revisor': _rev, 'Autor': _pr_author})

            if _recip_rows:
                _reciprocity_df = pd.concat(
                    [_reciprocity_df, pd.DataFrame(_recip_rows)], ignore_index=True
                ) if not _reciprocity_df.empty else pd.DataFrame(_recip_rows)

        if not _reciprocity_df.empty:
            _recip_pivot = _reciprocity_df.groupby(['Revisor', 'Autor']).size().reset_index(name='Revisões')
            _pivot_matrix = _recip_pivot.pivot(index='Revisor', columns='Autor', values='Revisões').fillna(0)
            # Ordena por total de revisões dadas (revisor mais ativo no topo)
            _pivot_matrix = _pivot_matrix.loc[
                _pivot_matrix.sum(axis=1).sort_values(ascending=False).index
            ]
            _rev_z = _pivot_matrix.values.tolist()
            _rev_text = [[str(int(v)) if v > 0 else '' for v in row] for row in _rev_z]
            fig_review_reciprocity.add_trace(go.Heatmap(
                z=_rev_z,
                x=list(_pivot_matrix.columns),
                y=list(_pivot_matrix.index),
                text=_rev_text,
                texttemplate='%{text}',
                colorscale='Blues',
                hovertemplate='<b>%{y}</b> revisou <b>%{x}</b><br>Revisões: <b>%{z:.0f}</b><extra></extra>',
                colorbar=dict(title='Revisões'),
            ))
            fig_review_reciprocity.update_layout(
                title=dict(
                    text='Review Reciprocity — Matriz de Revisões (Revisor × Autor)<br>'
                         '<sup>Linhas = quem revisa | Colunas = quem tem seu código revisado | Valor = nº de revisões no período.</sup>',
                    font=dict(size=13),
                ),
                xaxis=dict(title='Autor do PR', side='top', tickangle=-30),
                yaxis=dict(title='Revisor', automargin=True, autorange='reversed'),
                template='plotly_white',
                height=max(350, 28 * len(_pivot_matrix) + 120),
                margin=dict(t=110, b=30, l=180, r=60),
            )

        # ── Fig: Aging Rescue Rate — % de entregues envelhecidos resgatados ──
        _arr_df = per_dev[
            per_dev['Aging Rescue Rate (%)'].notna() &
            per_dev['Itens Entregues'].gt(0)
        ].copy() if 'Aging Rescue Rate (%)' in per_dev.columns else pd.DataFrame()
        _arr_df = _arr_df.sort_values('Aging Rescue Rate (%)', ascending=False).head(30)
        fig_aging_rescue = go.Figure()
        if not _arr_df.empty:
            _arr_colors = ['#27ae60' if v >= 30 else '#f39c12' if v >= 10 else '#95a5a6'
                           for v in _arr_df['Aging Rescue Rate (%)']]
            fig_aging_rescue.add_trace(go.Bar(
                x=_arr_df['Pessoa'],
                y=_arr_df['Aging Rescue Rate (%)'],
                marker_color=_arr_colors,
                marker_line_width=0,
                text=[f'{v:.1f}%' for v in _arr_df['Aging Rescue Rate (%)']],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Aging Rescue Rate: <b>%{y:.1f}%</b><extra></extra>',
            ))
        fig_aging_rescue.update_layout(
            title=dict(
                text=f'Aging Rescue Rate — % dos Cards Entregues que já tinham > {_AGING_THRESHOLD_DAYS} dias de Backlog ao ser Puxados<br>'
                     '<sup>Produtividade sobre itens envelhecidos: sinaliza quem pega card antigo e efetivamente entrega.</sup>',
                font=dict(size=13),
            ),
            xaxis=dict(title='', automargin=True, tickangle=-30),
            yaxis=dict(title='% Entregues com Aging Alto', gridcolor='#f0f0f0'),
            template='plotly_white',
            height=420,
            margin=dict(t=80, b=90, l=60, r=30),
            plot_bgcolor='#fafafa',
        )

        # ── Fig: Aging Pull Rate — % de puxados envelhecidos ─────────────────
        _apr_df = per_dev[
            per_dev['Aging Pull Rate (%)'].notna() &
            per_dev['Itens Puxados'].gt(0)
        ].copy() if 'Aging Pull Rate (%)' in per_dev.columns else pd.DataFrame()
        _apr_df = _apr_df.sort_values('Aging Pull Rate (%)', ascending=False).head(30)
        fig_aging_pull = go.Figure()
        if not _apr_df.empty:
            _apr_colors = ['#2980b9' if v >= 30 else '#5dade2' if v >= 10 else '#95a5a6'
                           for v in _apr_df['Aging Pull Rate (%)']]
            fig_aging_pull.add_trace(go.Bar(
                x=_apr_df['Pessoa'],
                y=_apr_df['Aging Pull Rate (%)'],
                marker_color=_apr_colors,
                marker_line_width=0,
                text=[f'{v:.1f}%' for v in _apr_df['Aging Pull Rate (%)']],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Aging Pull Rate: <b>%{y:.1f}%</b><extra></extra>',
            ))
        fig_aging_pull.update_layout(
            title=dict(
                text=f'Aging Pull Rate — % dos Cards Puxados com > {_AGING_THRESHOLD_DAYS} dias de Backlog<br>'
                     '<sup>Iniciativa operacional: sinaliza quem se dispõe a puxar itens antigos do backlog.</sup>',
                font=dict(size=13),
            ),
            xaxis=dict(title='', automargin=True, tickangle=-30),
            yaxis=dict(title='% Puxados com Aging Alto', gridcolor='#f0f0f0'),
            template='plotly_white',
            height=420,
            margin=dict(t=80, b=90, l=60, r=30),
            plot_bgcolor='#fafafa',
        )

        def _section(title, subtitle=None, children=None):
            """Helper: cria bloco de seção com título, linha divisória e conteúdo."""
            return html.Div([
                html.Div([
                    html.H4(title, style={
                        'margin': '0 0 2px 0', 'fontSize': '15px',
                        'fontWeight': '600', 'color': '#343a40',
                    }),
                    html.P(subtitle, style={
                        'margin': '0', 'fontSize': '12px', 'color': '#6c757d',
                    }) if subtitle else html.Span(),
                ], style={'borderBottom': '2px solid #dee2e6', 'paddingBottom': '8px', 'marginBottom': '12px'}),
                *(children or []),
            ], style={
                'backgroundColor': '#ffffff', 'border': '1px solid #e9ecef',
                'borderRadius': '8px', 'padding': '16px 20px', 'marginBottom': '16px',
                'boxShadow': '0 1px 4px rgba(0,0,0,.05)',
            })

        return html.Div([
            # ── Cabeçalho ─────────────────────────────────────────────────────
            html.Div([
                html.H3('Produtividade Individual por Desenvolvedor', style={
                    'margin': '0 0 4px 0', 'fontSize': '20px', 'fontWeight': '700', 'color': '#212529',
                }),
                html.P(
                    f'Período: {period_label}  •  Jira (cartões, Story Points, demanda de falha) + Bitbucket (commits, PRs)',
                    style={'margin': 0, 'fontSize': '12px', 'color': '#6c757d'},
                ),
            ], style={
                'padding': '14px 20px', 'marginBottom': '16px',
                'background': 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                'borderRadius': '8px', 'borderLeft': '4px solid #2980b9',
            }),

            # ── KPIs ──────────────────────────────────────────────────────────
            kpi_row,

            no_delivery_notice if no_delivery_notice is not None else html.Div(),

            # ── BU Banner ─────────────────────────────────────────────────────
            bu_selector,

            # ── IEF — Índice de Entrega Focado (0.70×NDS + 0.30×EEE) ────────
            _section(
                'Índice de Entrega Focado (IEF) — Volume × Conclusão',
                [
                    html.Span('Régua simplificada de entrega pura: '),
                    html.Span('IEF = 0.70×NDS + 0.30×EEE', style={'fontWeight': '700', 'fontFamily': 'monospace'}),
                    html.Span(' · '),
                    html.Span('IEF Ajustado = IEF × (0.5 + 0.5×ECR)', style={'fontFamily': 'monospace', 'color': '#8e44ad'}),
                    html.Br(),
                    html.Span('NDS (70%)', style={'color': '#2980b9', 'fontWeight': '600'}),
                    html.Span(' — volume de entregas ponderado por complexidade vs P75 rolling do grupo. '),
                    html.Span('EEE (30%)', style={'color': '#8e44ad', 'fontWeight': '600'}),
                    html.Span(' — taxa de conclusão do trabalho comprometido, capped em 100%. '),
                    html.Span('Exclui velocidade e qualidade — foco em volume × conclusão (Kitchenham & Mendes, TSE 2004). ', style={'color': '#6c757d'}),
                    html.Span(
                        'IEF Ajustado aplica fator de confiança via ECR: ECR=100% → sem desconto | ECR=50% → ×0.75 | ECR=0% → ×0.50.',
                        style={'color': '#e67e22'},
                    ),
                ],
                [
                    dcc.Graph(figure=fig_ief, config={'displayModeBar': False})
                    if fig_ief.data else
                    html.P(
                        'Sem dados para calcular o IEF no período selecionado.'
                        if total_puxados == 0 else
                        f'Sem base para IEF: houve {total_puxados} itens puxados, mas 0 entregas elegíveis no período.',
                        style={'color': '#aaa'},
                    ),
                ],
            ),

            # ── IED — Índice de Entrega do Desenvolvedor (régua principal) ────
            _section(
                'Índice de Entrega do Desenvolvedor (IED)',
                [
                    html.Span('Régua unificada de produtividade: '),
                    html.Span('IED = 0.35×NDS + 0.30×EEE + 0.15×VEL + 0.20×QUA', style={'fontWeight': '700', 'fontFamily': 'monospace'}),
                    html.Br(),
                    html.Span('NDS (35%)', style={'color': '#2980b9', 'fontWeight': '600'}),
                    html.Span(' — Volume de entregas ajustado por complexidade vs P75 rolling (3 meses) do grupo por papel. '),
                    html.Span('EEE (30%)', style={'color': '#8e44ad', 'fontWeight': '600'}),
                    html.Span(' — Taxa de conclusão do trabalho comprometido, capped em 100% (entregas / puxados ponderados). '),
                    html.Span('VEL (15%)', style={'color': '#16a085', 'fontWeight': '600'}),
                    html.Span(' — Velocidade relativa ao grupo. Peso reduzido para não penalizar itens intrinsecamente complexos. '),
                    html.Span('QUA (20%)', style={'color': '#e74c3c', 'fontWeight': '600'}),
                    html.Span(' — Qualidade com suavização Bayesiana (100 − % Demanda Falha). Peso aumentado: defeitos têm custo real. '),
                    html.Span(
                        'IED* = score de baixa confiança (ECR < 50%). '
                        'Faixas: Excelente ≥85 | Bom ≥70 | Regular ≥50 | Abaixo ≥30 | Crítico <30.',
                        style={'color': '#6c757d'},
                    ),
                ],
                [
                    dcc.Graph(figure=fig_ied, config={'displayModeBar': False})
                    if fig_ied.data else html.P(
                        'Sem dados para calcular o IED no período selecionado.'
                        if total_puxados == 0 else
                        f'Sem base para IED: houve {total_puxados} itens puxados, mas 0 entregas elegíveis no período.',
                        style={'color': '#aaa'},
                    ),
                    dcc.Graph(figure=fig_ied_radar, config={'displayModeBar': False})
                    if fig_ied_radar.data else html.P('Sem dados suficientes para o radar de componentes.', style={'color': '#aaa'}),
                    dcc.Graph(figure=fig_ief_ied_scatter, config={'displayModeBar': False})
                    if fig_ief_ied_scatter.data else html.Div(),
                    html.Details([
                        html.Summary('Detalhamento dos Componentes do IED por Desenvolvedor',
                                     style={'fontWeight': '600', 'cursor': 'pointer',
                                            'fontSize': '13px', 'marginTop': '12px', 'color': '#2c3e50'}),
                        html.Div(ied_breakdown_table, style={'marginTop': '10px'}),
                    ]),
                ],
            ),

            # ── Evolução Temporal do IED — sparklines mensais ─────────────────
            _section(
                'Evolução Temporal do IED por Desenvolvedor',
                [
                    html.Span('IED calculado por mês para os top 20 devs. '),
                    html.Span('Linha laranja pontilhada = mínimo esperado (IED 70). ', style={'color': '#e67e22'}),
                    html.Span('Devs com < 2 entregas no mês são excluídos daquele mês. '),
                    html.Span('Disponível apenas quando o período selecionado abrange ≥ 2 meses.',
                              style={'color': '#6c757d'}),
                ],
                [
                    dcc.Graph(figure=fig_ied_sparklines, config={'displayModeBar': False})
                    if _monthly_ied_data else html.P(
                        'Período selecionado menor que 2 meses — selecione um intervalo mais amplo para ver a evolução temporal.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── WIP Médio × Lead Time (Little's Law) ──────────────────────────
            _section(
                'WIP Médio × Lead Time (Little\'s Law)',
                [
                    html.Span('WIP médio estimado por Little\'s Law: '),
                    html.Span('WIP = Throughput × CT', style={'fontFamily': 'monospace', 'fontWeight': '600'}),
                    html.Span('. Bolha ∝ IED. '),
                    html.Span('Referência: Little (1961); Anderson (2010) — WIP e Lead Time são co-dependentes. ',
                              style={'color': '#2980b9'}),
                    html.Span('Devs com WIP alto e LT alto são candidatos prioritários a coaching de fluxo.',
                              style={'color': '#e67e22'}),
                ],
                [
                    dcc.Graph(figure=fig_wip_lt, config={'displayModeBar': False})
                    if not _wip_lt_df.empty else html.P(
                        'Dados insuficientes para calcular WIP médio (necessário DataInProgress e LeadTime no período).',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Previsibilidade de Lead Time (P85/P50) ────────────────────────
            _section(
                'Previsibilidade de Lead Time — Razão P85/P50',
                [
                    html.Span('Razão P85/P50 mede dispersão da distribuição de Lead Time. '),
                    html.Span('≤ 2.0 = Previsível', style={'color': '#27ae60', 'fontWeight': '600'}),
                    html.Span(' | '),
                    html.Span('≤ 3.0 = Moderado', style={'color': '#f39c12', 'fontWeight': '600'}),
                    html.Span(' | '),
                    html.Span('> 3.0 = Imprevisível', style={'color': '#e74c3c', 'fontWeight': '600'}),
                    html.Span('. Referência: Reinertsen (2009) — Product Development Flow.',
                              style={'color': '#6c757d'}),
                ],
                [
                    dcc.Graph(figure=fig_lt_predictability, config={'displayModeBar': False})
                    if not _prev_df.empty else html.P(
                        'Dados insuficientes para calcular P85/P50 (mínimo de 2 entregas por dev).',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Δ IED Trend ───────────────────────────────────────────────────
            _section(
                'Δ IED Trend — Variação Mensal de Produtividade',
                [
                    html.Span('Diferença entre o IED do último mês com dados e o primeiro mês do período. '),
                    html.Span('Verde = dev melhorando', style={'color': '#27ae60', 'fontWeight': '600'}),
                    html.Span(' | '),
                    html.Span('Vermelho = dev em queda', style={'color': '#e74c3c', 'fontWeight': '600'}),
                    html.Span('. Disponível apenas para períodos com ≥ 2 meses de dados suficientes.',
                              style={'color': '#6c757d'}),
                ],
                [
                    dcc.Graph(figure=fig_delta_ied, config={'displayModeBar': False})
                    if not _trend_df.empty else html.P(
                        'Período sem dados mensais suficientes para calcular Δ IED Trend.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Heatmap Mensal IED ────────────────────────────────────────────
            _section(
                'Heatmap Mensal IED — Evolução Matricial por Desenvolvedor',
                [
                    html.Span('Cada célula = IED do dev no mês. '),
                    html.Span('Verde = Excelente | Azul = Bom | Laranja = Regular | Vermelho = Crítico. ', style={'fontWeight': '600'}),
                    html.Span('Branco = dev sem dados suficientes naquele mês (< 2 entregas). ', style={'color': '#6c757d'}),
                    html.Span('Identifica padrões de queda ou melhora consistentes ao longo do período.',
                              style={'color': '#2980b9'}),
                ],
                [
                    dcc.Graph(figure=fig_ied_heatmap, config={'displayModeBar': False})
                    if fig_ied_heatmap.data else html.P(
                        'Período selecionado menor que 2 meses — selecione um intervalo mais amplo para ver o heatmap mensal.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Vazão Semanal por Pessoa ──────────────────────────────────────
            _section(
                'Vazão Semanal por Pessoa — Evolução Temporal',
                [
                    html.Span('Itens entregues (DataDone) por semana para os '),
                    html.Span(f'top {_vzs_top_n} devs', style={'fontWeight': '600'}),
                    html.Span(' do período. Complementa o heatmap mensal com granularidade semanal — '),
                    html.Span('identifica semanas de pico, queda de produção e variabilidade intra-mês.',
                              style={'color': '#2980b9'}),
                ],
                [
                    dcc.Graph(figure=fig_vazao_semanal_dev, config={'displayModeBar': False})
                    if fig_vazao_semanal_dev.data else html.P(
                        'Sem dados suficientes para construir a série semanal no período selecionado.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Δ ECR / maturidade de estimativa ─────────────────────────────
            _section(
                'Confiabilidade de Estimativa — Δ ECR e Maturidade',
                [
                    html.Span('Diferença entre o ECR do último mês válido e o primeiro mês do período. '),
                    html.Span('ECR', style={'color': '#8e44ad', 'fontWeight': '600'}),
                    html.Span(' mede a cobertura de estimativas reais nos itens puxados. '),
                    html.Span(
                        f'Maduro em estimativa = ECR ≥ {_ECR_MATURITY_THRESHOLD:.0f}% por {_ECR_MATURITY_STREAK} meses consecutivos.',
                        style={'color': '#27ae60', 'fontWeight': '600'},
                    ),
                    html.Span(' `Devs Revisados` aparece na tabela como breadth de revisão/capacidade cruzada.', style={'color': '#6c757d'}),
                ],
                [
                    dcc.Graph(figure=fig_delta_ecr, config={'displayModeBar': False})
                    if not _ecr_trend_df.empty else html.P(
                        'Período sem base mensal suficiente para calcular a tendência de ECR.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Aging Rescue Rate ─────────────────────────────────────────────
            _section(
                f'Aging Rescue Rate — Entregues com > {_AGING_THRESHOLD_DAYS} dias de Backlog ao ser Puxados',
                [
                    html.Span('% dos cards entregues pelo dev que já estavam em backlog há mais de '),
                    html.Span(f'{_AGING_THRESHOLD_DAYS} dias', style={'fontWeight': '600'}),
                    html.Span(' quando foram puxados (DataCriacao → DataInProgress). '),
                    html.Span('Esse é o indicador de produtividade sobre backlog antigo: puxou item envelhecido e entregou. ',
                              style={'color': '#27ae60'}),
                    html.Span('Requer data de criação no Jira (DataCriacao, Created ou CreatedDate).', style={'color': '#6c757d'}),
                ],
                [
                    dcc.Graph(figure=fig_aging_rescue, config={'displayModeBar': False})
                    if not _arr_df.empty else html.P(
                        'Data de criação não disponível ou sem itens entregues elegíveis no período para calcular Aging Rescue Rate.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Aging Pull Rate ───────────────────────────────────────────────
            _section(
                f'Aging Pull Rate — Puxados com > {_AGING_THRESHOLD_DAYS} dias de Backlog',
                [
                    html.Span('% dos cards puxados pelo dev que já estavam em backlog há mais de '),
                    html.Span(f'{_AGING_THRESHOLD_DAYS} dias', style={'fontWeight': '600'}),
                    html.Span(' quando foram puxados (DataCriacao → DataInProgress). '),
                    html.Span('Esse é o indicador de iniciativa operacional: quem não pega só o topo da fila. ',
                              style={'color': '#2980b9'}),
                    html.Span('Complementa o Aging Rescue Rate, mas não substitui o sinal de entrega.', style={'color': '#6c757d'}),
                ],
                [
                    dcc.Graph(figure=fig_aging_pull, config={'displayModeBar': False})
                    if not _apr_df.empty else html.P(
                        'Data de criação não disponível ou sem itens puxados no período para calcular Aging Pull Rate.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Produtividade 360° — radar resumo geral ───────────────────────
            _section(
                'Produtividade 360° — Resumo Geral',
                [
                    html.Span('Combina os 4 eixos do IED '),
                    html.Span('(NDS, EEE, VEL, QUA)', style={'fontWeight': '600', 'fontFamily': 'monospace'}),
                    html.Span(' + '),
                    html.Span('Estabilidade de Throughput', style={'color': '#2980b9', 'fontWeight': '600'}),
                    html.Span(' (1 − CV semanal: previsibilidade de entrega semana a semana) + '),
                    html.Span('ECR', style={'color': '#8e44ad', 'fontWeight': '600'}),
                    html.Span(' (% de itens puxados com estimativa real, não inferida por modelo). '),
                    html.Span('Top 15 por IED. Maior área = perfil mais completo. ', style={'color': '#6c757d'}),
                    html.Span('Referências: ', style={'fontWeight': '600'}),
                    html.Span('Estabilidade — Anderson (2010); Magennis (2016) | ', style={'color': '#2980b9'}),
                    html.Span('ECR — Kitchenham & Mendes (TSE 2004)', style={'color': '#8e44ad'}),
                ],
                [
                    dcc.Graph(figure=fig_prod_360, config={'displayModeBar': False})
                    if fig_prod_360.data else html.P(
                        'Dados insuficientes para o radar 360° (mínimo 3 eixos com dados).',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Bitbucket + capacidade cruzada ───────────────────────────────
            _section(
                'Contribuições Bitbucket e Capacidade Cruzada',
                'Relatórios movidos da aba Performance do Serviço para centralizar a leitura técnica por pessoa.',
                [contributor_section],
            ),

            # ── Resumo por BU ─────────────────────────────────────────────────
            _section(
                'Visão por BU / Time',
                'Entregas, commits e PRs Merged consolidados por time no período. '
                'ICC (HHI) mede concentração de commits — valores altos indicam risco de concentração de conhecimento.',
                ([dcc.Graph(figure=fig_bu_summary, config={'displayModeBar': False})]
                 if fig_bu_summary.data else [html.P('Dados de BU não disponíveis.', style={'color': '#aaa'})])
                + [icc_table],
            ),

            # ── Tabela de devs ─────────────────────────────────────────────────
            _section(
                'Ranking de Desenvolvedores',
                'Ordenado por Itens Entregues e Score Complexidade. Use as abas (Flow | Código | Revisão | Processo | Índices) '
                'para navegar entre grupos de indicadores. Filtre por BU ou Papel.',
                [prod_table],
            ),

            _section(
                'Relatório QA->Dev por Card',
                'Cada linha representa uma ida para QA/Teste/Homologação seguida de retorno para desenvolvimento. '
                'Quando o artefato novo de process mining ainda não existir, a tela recalcula o relatório a partir de EventosFiltrados.',
                [pm_dev_return_table],
            ),

            # ── Radar chart multidimensional ───────────────────────────────────
            _section(
                'Perfil Multidimensional com Benchmarks Absolutos',
                [
                    html.Span('Top 10 por IED.'),
                    html.Span('100 = atingiu o benchmark da dimensão. ', style={'fontWeight': '600'}),
                    html.Span('Score Benchmark (SB) = 100 − distância euclidiana ao perfil ideal [100,100,100,100,100]. '),
                    html.Span('Referências: '),
                    html.Span('Entrega P75 (Jørgensen, IST 2023)', style={'color': '#2980b9'}),
                    html.Span(' | '),
                    html.Span('Flow Efficiency ≥80% (Anderson 2010 — Kanban/Little\'s Law)', style={'color': '#27ae60'}),
                    html.Span(' | '),
                    html.Span('Revisão ≥70% (Forsgren et al., SPACE — ACM Queue 2021)', style={'color': '#8e44ad'}),
                    html.Span(' | '),
                    html.Span('Conformance ≥75% (Caldeira et al., ICPM 2019)', style={'color': '#e67e22'}),
                    html.Span(' | '),
                    html.Span('Anti-Retrabalho Rework≤20% (Caldeira 2021; Shah et al., ICSME 2023)', style={'color': '#c0392b'}),
                ],
                [dcc.Graph(figure=fig_radar, config={'displayModeBar': False})]
                if fig_radar.data else [html.P('Dados insuficientes para gerar radar.', style={'color': '#aaa'})],
            ),

            # ── Segmentação por Papel (Tech Lead vs Dev) ───────────────────────
            _section(
                'Benchmark por Papel — Tech Lead vs Dev',
                'Medianas por papel. Ajuste os papéis em people_config.json → role_map.',
                [
                    papel_kpi_section,
                    dcc.Graph(figure=fig_papel, config={'displayModeBar': False})
                    if fig_papel.data else html.P('Papel não configurado ou sem dados.', style={'color': '#aaa'}),
                ],
            ),

            # ── Velocidade de Entrega (SP/Mês) com benchmarks QSM ────────────
            _section(
                'Velocidade de Entrega por Dev (SP/Mês)',
                [
                    html.Span('Story Points entregues por desenvolvedor por mês no período. '),
                    html.Span('Usado como proxy de FP/PM ', style={'fontWeight': '600'}),
                    html.Span('(1 SP ≈ 1 FP — calibração interna necessária). '),
                    html.Span('Linhas de referência: ', style={'fontWeight': '600'}),
                    html.Span('QSM Business Systems — Q1: 5.0 | Mediana: 7.47 | Q4: 11.55 FP/PM ', style={'color': '#27ae60'}),
                    html.Span('(QSM Benchmark Tables, '),
                    html.A('qsm.com/resources/qsm-benchmark-tables',
                           href='https://www.qsm.com/resources/qsm-benchmark-tables',
                           target='_blank', style={'color': '#2980b9', 'fontSize': '12px'}),
                    html.Span(f', n≈330 projetos IT). '),
                    html.Span(
                        'Benchmarks refletem produtividade de equipe, não individual — use como referência de ordem de grandeza.',
                        style={'color': '#e67e22', 'fontSize': '12px'},
                    ),
                ],
                [
                    dcc.Graph(figure=fig_velocity, config={'displayModeBar': False})
                    if fig_velocity.data else
                    html.P('Sem dados de Story Points no período para calcular SP/mês.', style={'color': '#aaa'}),
                ],
            ),

            # ── Gráfico puxados vs entregues ───────────────────────────────────
            _section(
                'Cartões Puxados vs Entregues',
                'Top 30 por Itens Entregues. Puxados = itens movidos para WIP; Entregues = itens concluídos.',
                [dcc.Graph(figure=fig_pulled_vs_done, config={'displayModeBar': False})],
            ),

            # ── Complexidade ──────────────────────────────────────────────────
            _section(
                'Cartões Puxados por Complexidade (Estimativa Unificada)',
                [
                    html.Span('Itens iniciados no período classificados por complexidade. '),
                    html.Span('SP numérico tem prioridade; ', style={'fontWeight': '600'}),
                    html.Span('itens sem SP usam T-shirt size equalizado: '),
                    html.Span('P = 2SP | M = 5SP | G = 8SP | GG/XL = 13SP', style={'fontFamily': 'monospace', 'color': '#2980b9'}),
                    html.Span(' (Kitchenham & Mendes, TSE 2004). '),
                    html.Span('"Sem estimativa" só aparece se o item não tem nem SP nem T-shirt.', style={'color': '#e67e22'}),
                ],
                [dcc.Graph(figure=fig_complexity, config={'displayModeBar': False})]
                if not complexity_df.empty else [
                    html.P('Sem dados de estimativa (SP ou T-shirt) para o período com os filtros ativos.',
                           style={'color': '#aaa', 'fontStyle': 'italic'})
                ],
            ),

            # ── Demanda de falha ──────────────────────────────────────────────
            _section(
                'Demanda de Falha por Desenvolvedor',
                'Defeitos concluídos atribuídos ao dev. Cor indica % de falha em relação ao total entregue.',
                [dcc.Graph(figure=fig_failure_demand, config={'displayModeBar': False})]
                if has_defect_data else [
                    html.P('Nenhum item do tipo Defeito concluído no período com os filtros ativos.',
                           style={'color': '#aaa', 'fontStyle': 'italic'})
                ],
            ),

            # ── Scatter commits x entregas ────────────────────────────────────
            _section(
                'Commits × Itens Entregues (Bitbucket + Jira)',
                'Cada bolha = um dev. Tamanho ∝ PRs Merged. Cor = % Demanda Falha (verde → saudável, vermelho → alto).',
                [dcc.Graph(figure=fig_scatter, config={'displayModeBar': False})],
            ),

            # ── Bottleneck Contribution ───────────────────────────────────────
            _section(
                'Contribuição em Status de Gargalo (Process Mining)',
                (
                    f'Horas acumuladas por dev nos status de gargalo identificados pelo process mining '
                    f'({_gargalo_label or "—"}). '
                    f'Gargalo = statuses com Tempo Mediano ≥ P75 (excluindo terminais). '
                    f'Alto % = dev concentra trabalho em filas lentas.'
                ),
                [
                    dcc.Graph(
                        figure=_make_bottleneck_fig(per_dev, _gargalo_label),
                        config={'displayModeBar': False},
                    ) if not per_dev[['Horas em Gargalo']].dropna().empty else
                    html.P(
                        'Dados de bottleneck não disponíveis — gere *-process-mining-latest.xlsx com process_mining_jira.py.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    )
                ],
            ),

            # ── Composição de Demanda por tipo ───────────────────────────────
            _section(
                'Composição de Demanda por Dev (WorkItemCategory)',
                [
                    html.Span('Top 20 devs por IED.'),
                    html.Span('Cada barra = 100% dos itens entregues, particionados por tipo. '),
                    html.Span(
                        'Idealmente devs de produto concentram em Melhorias/Features; '
                        'alto % Defeitos pode indicar débito de qualidade. ',
                        style={'color': '#6c757d'},
                    ),
                    html.Span(
                        'WIP Residual (tabela) = itens puxados ainda não concluídos ao fim do período — '
                        'alto WIP reduz Flow Efficiency (Anderson 2010).',
                        style={'color': '#e67e22', 'fontWeight': '600'},
                    ),
                ],
                [
                    dcc.Graph(figure=fig_category_breakdown, config={'displayModeBar': False})
                    if fig_category_breakdown.data else
                    html.P(
                        'WorkItemCategory não disponível nos dados — campo necessário nos cards do Jira.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    )
                ],
            ),

            # ── Review Reciprocity Matrix ─────────────────────────────────────
            _section(
                'Review Reciprocity — Quem Revisa Quem',
                [
                    html.Span('Matriz de revisões: '),
                    html.Span('linhas = revisor', style={'fontWeight': '600', 'color': '#2980b9'}),
                    html.Span(' | '),
                    html.Span('colunas = autor do PR revisado', style={'fontWeight': '600', 'color': '#8e44ad'}),
                    html.Span('. Valor = nº de revisões (aprovações + change requests) no período. '),
                    html.Span(
                        'Silos de revisão: TL concentra toda coluna → devs não revisam entre si → risco de bus factor.',
                        style={'color': '#e74c3c'},
                    ),
                ],
                [
                    dcc.Graph(figure=fig_review_reciprocity, config={'displayModeBar': False})
                    if fig_review_reciprocity.data else html.P(
                        'Sem dados de revisão no período ou sem dados Bitbucket disponíveis.',
                        style={'color': '#aaa', 'fontStyle': 'italic'},
                    ),
                ],
            ),

            # ── Breakdown Temporal Bitbucket ──────────────────────────────────
            _section(
                'Breakdown Temporal Bitbucket — Mensal e Semanal',
                'Visão analítica de commits, PRs e aprovações por desenvolvedor, quebrada por mês e por semana. '
                'Heatmaps e tabelas pivô permitem identificar ritmo de contribuição e variações ao longo do período.',
                [build_bitbucket_temporal_section(bb_projects, start_ts_prod, end_ts_prod, alias_index_prod)],
            ),

        ], style={'padding': '20px', 'backgroundColor': '#f4f6f8', 'minHeight': '100vh'})

    if tab == 'tab-corporativo':
        try:
            _, df_portfolio, _pf_err = get_portfolio_snapshot()
        except Exception:
            df_portfolio = pd.DataFrame()
            
        return layout_corporativo(
            df=df,
            df_portfolio=df_portfolio,
            start_ts=start_date,
            end_ts=end_date,
            projeto=projeto,
            periodicity=corp_periodicity or 'M',
            group_by_product=corp_groupby_product,
            feature_types=corp_feature_types
        )

    return html.Div('Aba não encontrada')

