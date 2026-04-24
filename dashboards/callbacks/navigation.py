"""Navigation and filter callbacks — RF-034/RF-035."""
from __future__ import annotations

import dash
from dash import Input, Output, State
from dash.exceptions import PreventUpdate

from dashboards.components.error_boundary import error_boundary
from dashboards.core.data_processing import PROJECT_FILTER_ALL_VALUE, normalize_project_filter_value


def register_callbacks(app):
    from dashboard_full import (  # lazy: avoids circular import at module load time
        WIP_FLOW_STAGE_DEFAULTS,
        PORTFOLIO_TAB_VALUE,
        SERVICE_TAB_VALUES,
        get_leadtime_stage_filter_columns,
        get_downstream_done_stage_column,
        get_explicit_done_stage_column,
        get_default_lead_time_start_stages,
        get_creator_filter_options_for_project,
        get_portfolio_project_filter_options,
        build_portfolio_tab,
        build_service_tabs,
    )

    @app.callback(
        Output('main-view', 'data'),
        Output('tabs', 'value'),
        Input('btn-menu-portfolio', 'n_clicks'),
        Input('btn-menu-services', 'n_clicks'),
        Input('btn-menu-home', 'n_clicks'),
        State('tabs', 'value'),
        prevent_initial_call=True
    )
    @error_boundary(fallback=(dash.no_update, dash.no_update))
    def handle_main_menu_navigation(_portfolio_clicks, _services_clicks, _home_clicks, current_tab):
        triggered_id = dash.ctx.triggered_id
        if not triggered_id:
            raise PreventUpdate

        if triggered_id == 'btn-menu-portfolio':
            return 'portfolio', PORTFOLIO_TAB_VALUE

        if triggered_id == 'btn-menu-services':
            next_tab = current_tab if current_tab in SERVICE_TAB_VALUES else 'tab-performance'
            return 'services', next_tab

        if triggered_id == 'btn-menu-home':
            next_tab = current_tab if current_tab in SERVICE_TAB_VALUES else 'tab-performance'
            return 'home', next_tab

        raise PreventUpdate

    @app.callback(
        Output('filter-leadtime-stages', 'options'),
        Output('filter-leadtime-stages', 'value'),
        Input('filter-projeto', 'value'),
        State('filter-leadtime-stages', 'value'),
    )
    @error_boundary(fallback=([], []))
    def update_leadtime_stage_filter_options(projeto, current_value):
        projeto = normalize_project_filter_value(projeto)
        stage_cols, stage_source = get_leadtime_stage_filter_columns(projeto)
        if not stage_cols:
            return [], []
        done_col = get_downstream_done_stage_column(stage_cols) if stage_source == 'downstream' else get_explicit_done_stage_column(stage_cols)
        start_candidates = [c for c in stage_cols if c != done_col]
        options = [{'label': c, 'value': c} for c in start_candidates]
        current = [v for v in (current_value or []) if v in start_candidates]
        if current:
            return options, current
        return options, get_default_lead_time_start_stages(start_candidates)

    @app.callback(
        Output('filter-etapa-fluxo', 'options'),
        Output('filter-etapa-fluxo', 'value'),
        Input('filter-projeto', 'value'),
        State('filter-etapa-fluxo', 'value'),
    )
    @error_boundary(fallback=([], []))
    def update_etapa_fluxo_filter_options(projeto, current_value):
        projeto = normalize_project_filter_value(projeto)
        stage_cols, source = get_leadtime_stage_filter_columns(projeto)
        if not stage_cols:
            return [], []
        done_col = get_downstream_done_stage_column(stage_cols) if source == 'downstream' else get_explicit_done_stage_column(stage_cols)
        candidates = [c for c in stage_cols if c != done_col]
        options = [{'label': c, 'value': c} for c in candidates]
        preserved = [v for v in (current_value or []) if v in candidates]
        if preserved:
            return options, preserved
        available_lower = {str(c).strip().lower(): c for c in candidates}
        defaults = []
        for pref in WIP_FLOW_STAGE_DEFAULTS:
            hit = available_lower.get(pref.strip().lower())
            if hit and hit not in defaults:
                defaults.append(hit)
        return options, defaults

    @app.callback(
        Output('filter-criador', 'options'),
        Output('filter-criador', 'disabled'),
        Output('filter-criador', 'value'),
        Input('filter-projeto', 'value'),
        State('filter-criador', 'value'),
    )
    @error_boundary(fallback=([], True, []))
    def update_creator_filter_options(projeto, current_value):
        projeto = normalize_project_filter_value(projeto)
        options = get_creator_filter_options_for_project(projeto)
        allowed_values = {opt.get('value') for opt in options}
        preserved = [value for value in (current_value or []) if value in allowed_values]
        return options, not bool(options), preserved

    @app.callback(
        Output('filter-portfolio-team', 'options'),
        Output('filter-portfolio-team', 'value'),
        Input('filter-projeto', 'value'),
        State('filter-portfolio-team', 'value'),
    )
    @error_boundary(fallback=([], dash.no_update))
    def sync_portfolio_project_filter(projeto, current_portfolio_project):
        options = get_portfolio_project_filter_options()
        allowed_values = {opt.get('value') for opt in options}
        if current_portfolio_project in allowed_values:
            return options, current_portfolio_project
        return options, PROJECT_FILTER_ALL_VALUE

    @app.callback(
        Output('main-menu-panel', 'style'),
        Output('main-nav-panel', 'style'),
        Output('main-nav-context', 'children'),
        Output('filters-panel', 'style'),
        Output('tabs-wrapper', 'style'),
        Output('tabs', 'children'),
        Input('main-view', 'data')
    )
    @error_boundary(fallback=(dash.no_update,) * 6)
    def update_main_navigation_layout(main_view):
        menu_style = {
            'maxWidth': '720px',
            'margin': '0 auto 16px auto',
            'padding': '20px',
            'border': '1px solid #e5e7eb',
            'borderRadius': '14px',
            'backgroundColor': '#fafafa',
            'textAlign': 'center',
            'boxShadow': '0 4px 14px rgba(0,0,0,0.04)',
        }
        nav_style = {
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'center',
            'gap': '12px',
            'marginBottom': '12px',
            'flexWrap': 'wrap'
        }
        filters_style = {'display': 'flex', 'justifyContent': 'center', 'gap': '10px', 'marginBottom': '20px', 'flexWrap': 'wrap', 'alignItems': 'flex-start'}
        hidden_style = {'display': 'none'}

        if main_view == 'portfolio':
            return hidden_style, nav_style, 'Módulo: Portfólio', filters_style, hidden_style, build_portfolio_tab()

        if main_view == 'services':
            return hidden_style, nav_style, 'Módulo: Serviços (Value Stream)', filters_style, {}, build_service_tabs()

        return menu_style, hidden_style, '', hidden_style, hidden_style, build_service_tabs()
