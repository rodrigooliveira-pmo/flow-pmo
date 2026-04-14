"""
People module - Re-exports functions from dashboard_full.py

Phase 2A: Modular boundary/wrapper layer
Phase 2B: Actual function extraction (pending)

This module provides clean imports for people/team management functions.
Currently re-exports the 7 people-related functions that were successfully
extracted from dashboard_full.py during Phase 2A.
"""

try:
    from dashboard_full import (
        _canonical_person_name,
        _load_person_bu_map,
        _load_person_team_map,
        _person_role_options,
        _person_seniority_label,
        _resolve_person_bu,
        _resolve_person_team,
        compute_jira_person_capacity_metrics,
    )
except ImportError:
    def __getattr__(name):
        from dashboard_full import __dict__ as dashboard
        if name in dashboard:
            return dashboard[name]
        raise AttributeError(f"people: no attribute {name}")

__all__ = [
    '_canonical_person_name',
    '_load_person_bu_map',
    '_load_person_team_map',
    '_person_role_options',
    '_person_seniority_label',
    '_resolve_person_bu',
    '_resolve_person_team',
    'compute_jira_person_capacity_metrics',
]


__all__ = [
    "_canonical_person_name",
    "_load_person_aliases_map",
    "_load_person_bu_map",
    "_load_person_team_map",
    "_load_seniority_map",
    "_person_aliases",
    "_person_display_name",
    "_person_full_name",
    "_person_role_options",
    "_person_seniority_label",
    "_person_team_label",
    "_resolve_person_bu",
    "_resolve_person_team",
    "build_people_capacity_view",
    "build_people_tab",
    "build_people_team_capacity",
    "compute_jira_person_capacity_metrics",
]
