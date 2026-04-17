"""Finance module — CAPEX, cost models and portfolio financial functions.

Phase 2A: Re-exports functions from dashboard_full.py (wrapper layer).
Phase 2B: Actual extraction to finance/functions.py (planned — requires
          moving _pm_* helpers first).

All finance functions are currently defined in dashboard_full.py.
"""

try:
    from dashboard_full import (
        _load_portfolio_cost_model,
        _load_portfolio_role_salary_map,
        _load_portfolio_bu_salary_map,
        _build_portfolio_cost_team_df,
        build_portfolio_cost_model_snapshot,
        build_capex_worklog_cost_fact,
        build_pm_portfolio_capex_view,
        build_generated_portfolio_financial_view,
        build_portfolio_cross_delivery_integration,
    )
except ImportError:
    def __getattr__(name):
        import dashboard_full as _df
        if hasattr(_df, name):
            return getattr(_df, name)
        raise AttributeError(f"finance: no attribute {name!r}")

__all__ = [
    "_load_portfolio_cost_model",
    "_load_portfolio_role_salary_map",
    "_load_portfolio_bu_salary_map",
    "_build_portfolio_cost_team_df",
    "build_portfolio_cost_model_snapshot",
    "build_capex_worklog_cost_fact",
    "build_pm_portfolio_capex_view",
    "build_generated_portfolio_financial_view",
    "build_portfolio_cross_delivery_integration",
]
