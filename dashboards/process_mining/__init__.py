"""Process Mining module — re-exports from dashboard_full.py.

Phase 2A: Wrapper layer (functions still defined in dashboard_full.py).
Phase 2B: Extract to process_mining/functions.py (planned).

Public API:
    load_w1nner_process_mining_report
    load_project_pm_sheet
    load_project_pm_case_df
    compute_pm_dev_metrics
    compute_pm_dev_flow_metrics
    build_pm_commits_vs_jira_report
    build_pm_dev_return_report
    compute_pipeline_success_rate
    compute_pm_bottleneck_contribution
    build_touch_time_triangulation
"""

try:
    from dashboard_full import (
        _find_latest_w1nner_process_mining_excel,
        load_w1nner_process_mining_report,
        _load_pm_excel_url_map,
        load_project_pm_sheet,
        load_project_pm_case_df,
        build_touch_time_triangulation,
        _pm_is_execution_status,
        _pm_is_asset_type,
        _pm_is_dev_status,
        _pm_is_qa_status,
        _pm_summarize_dev_flow_from_events,
        _pm_extract_dev_flow_datasets,
        compute_pm_dev_metrics,
        compute_pm_dev_flow_metrics,
        build_pm_dev_return_report,
        compute_pipeline_success_rate,
        compute_pm_bottleneck_contribution,
        build_pm_commits_vs_jira_report,
    )
except ImportError:
    def __getattr__(name):
        import dashboard_full as _df
        if hasattr(_df, name):
            return getattr(_df, name)
        raise AttributeError(f"process_mining: no attribute {name!r}")

__all__ = [
    "_find_latest_w1nner_process_mining_excel",
    "load_w1nner_process_mining_report",
    "_load_pm_excel_url_map",
    "load_project_pm_sheet",
    "load_project_pm_case_df",
    "build_touch_time_triangulation",
    "_pm_is_execution_status",
    "_pm_is_asset_type",
    "_pm_is_dev_status",
    "_pm_is_qa_status",
    "_pm_summarize_dev_flow_from_events",
    "_pm_extract_dev_flow_datasets",
    "compute_pm_dev_metrics",
    "compute_pm_dev_flow_metrics",
    "build_pm_dev_return_report",
    "compute_pipeline_success_rate",
    "compute_pm_bottleneck_contribution",
    "build_pm_commits_vs_jira_report",
]
