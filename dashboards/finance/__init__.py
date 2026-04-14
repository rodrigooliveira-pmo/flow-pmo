"""
Finance module - Re-exports functions from dashboard_full.py

Phase 2A: Modular boundary/wrapper layer
Phase 2B: Actual function extraction (pending)

This module provides clean imports for finance/cost functions.
Currently re-exports the 8 finance-related functions that were successfully
extracted from dashboard_full.py during Phase 2A.
"""

try:
    from dashboard_full import (
        _build_capex_portfolio_asset_lookup,
        _build_portfolio_cost_team_df,
        _build_worklog_portfolio_cost_view_legacy,
        _build_worklog_portfolio_cost_view_v2_unused,
        _load_portfolio_bu_salary_map,
        _load_portfolio_cost_model,
        _load_portfolio_role_salary_map,
        build_worklog_cost_fact,
    )
except ImportError:
    def __getattr__(name):
        from dashboard_full import __dict__ as dashboard
        if name in dashboard:
            return dashboard[name]
        raise AttributeError(f"finance: no attribute {name}")

__all__ = [
    '_build_capex_portfolio_asset_lookup',
    '_build_portfolio_cost_team_df',
    '_build_worklog_portfolio_cost_view_legacy',
    '_build_worklog_portfolio_cost_view_v2_unused',
    '_load_portfolio_bu_salary_map',
    '_load_portfolio_cost_model',
    '_load_portfolio_role_salary_map',
    'build_worklog_cost_fact',
]

