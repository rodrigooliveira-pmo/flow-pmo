"""People module — identity, aliases, BU, roles and capacity metrics.

All person-identity functions live in people/config.py.
Capacity metrics live in people/functions.py (Jira-based).
Dev productivity metrics live in people/dev_metrics.py (Bitbucket-based).
"""

from .config import (
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

__all__ = [
    "_load_people_config",
    "_load_person_bu_map",
    "_load_person_role_map",
    "_load_person_alias_index",
    "_load_person_seniority_index",
    "_person_match_key",
    "_person_email_key",
    "_person_tokens_for_match",
    "_normalize_person_name",
    "_person_names_compatible",
    "_canonical_person_name",
    "_person_bu",
    "_person_role",
    "_normalize_seniority_bucket",
    "_normalize_multiselect_value",
    "_normalize_responsavel_filter_values",
    "_format_responsavel_filter_label",
    "_split_people_field",
    "_project_team_bu",
    "_project_team_seed_df",
    "_ensure_dev_productivity_columns",
]
