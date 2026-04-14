"""
Portfolio module - Re-exports functions from dashboard_full.py

Phase 2A: Modular boundary/wrapper layer
Phase 2B: Actual function extraction (pending large callback refactoring)

This module provides clean imports for portfolio functions while we
stabilize the refactoring of dashboard_full.py.
"""

# Re-export functions from dashboard_full for now
# These will be properly extracted in Phase 2B
try:
    from dashboard_full import (
        _build_capex_portfolio_asset_lookup,
        _build_portfolio_cost_team_df,
        _build_strategic_portfolio_wait_frame,
        _build_worklog_portfolio_cost_view_legacy,
        _build_worklog_portfolio_cost_view_v2_unused,
        _load_portfolio_bu_salary_map,
        _load_portfolio_cost_model,
        _load_portfolio_role_salary_map,
        _pm_build_portfolio_lookup,
        _pm_portfolio_selected_specs,
        _portfolio_team_to_pm_project_key,
        build_generated_portfolio_financial_view,
        build_pm_portfolio_capex_view,
        build_portfolio_cost_model_snapshot,
        build_portfolio_cross_delivery_integration,
        build_portfolio_snapshot_from_csv,
        build_portfolio_tab,
        compute_portfolio_snapshot,
        find_latest_portfolio_csv,
        get_portfolio_project_filter_options,
        get_portfolio_snapshot,
        portfolio_is_cancelled_item,
        portfolio_is_highest_priority,
        portfolio_quarter_label_from_date,
        portfolio_roadmap_progress_pct,
        portfolio_roadmap_status_label,
        portfolio_table_component,
        render_portfolio_roadmap_full_epics_view,
        render_portfolio_roadmap_quarter_view,
        sync_portfolio_project_filter,
    )
except ImportError as e:
    # Fallback: lazy loading
    def __getattr__(name):
        from dashboard_full import __dict__ as dashboard
        if name in dashboard:
            return dashboard[name]
        raise AttributeError(f"portfolio: no attribute {name}")

__all__ = [
    "_build_capex_portfolio_asset_lookup",
    "_build_portfolio_cost_team_df",
    "_build_strategic_portfolio_wait_frame",
    "_build_worklog_portfolio_cost_view_legacy",
    "_build_worklog_portfolio_cost_view_v2_unused",
    "_load_portfolio_bu_salary_map",
    "_load_portfolio_cost_model",
    "_load_portfolio_role_salary_map",
    "_pm_build_portfolio_lookup",
    "_pm_portfolio_selected_specs",
    "_portfolio_team_to_pm_project_key",
    "build_generated_portfolio_financial_view",
    "build_pm_portfolio_capex_view",
    "build_portfolio_cost_model_snapshot",
    "build_portfolio_cross_delivery_integration",
    "build_portfolio_snapshot_from_csv",
    "build_portfolio_tab",
    "compute_portfolio_snapshot",
    "find_latest_portfolio_csv",
    "get_portfolio_project_filter_options",
    "get_portfolio_snapshot",
    "portfolio_is_cancelled_item",
    "portfolio_is_highest_priority",
    "portfolio_quarter_label_from_date",
    "portfolio_roadmap_progress_pct",
    "portfolio_roadmap_status_label",
    "portfolio_table_component",
    "render_portfolio_roadmap_full_epics_view",
    "render_portfolio_roadmap_quarter_view",
    "sync_portfolio_project_filter",
]
