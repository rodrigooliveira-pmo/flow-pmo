#!/usr/bin/env python3
"""
Update dashboard_full.py to import from new domain modules and remove old definitions.
"""

import re
from pathlib import Path

# Functions that were extracted
EXTRACTED_FUNCS = {
    # Portfolio
    'build_portfolio_snapshot_from_csv', 'find_latest_portfolio_csv', 'get_portfolio_snapshot',
    'compute_portfolio_snapshot', 'build_portfolio_tab', 'get_portfolio_project_filter_options',
    'render_portfolio_roadmap_full_epics_view', 'render_portfolio_roadmap_quarter_view',
    'build_portfolio_cost_model_snapshot', 'build_generated_portfolio_financial_view',
    'build_portfolio_cross_delivery_integration', 'sync_portfolio_project_filter',
    'portfolio_table_component', 'portfolio_is_cancelled_item', 'portfolio_is_highest_priority',
    'portfolio_roadmap_progress_pct', 'portfolio_roadmap_status_label', 'portfolio_quarter_label_from_date',
    'build_pm_portfolio_capex_view', '_pm_portfolio_selected_specs', '_pm_build_portfolio_lookup',
    '_portfolio_team_to_pm_project_key', '_load_portfolio_cost_model', '_load_portfolio_bu_salary_map',
    '_load_portfolio_role_salary_map', '_build_portfolio_cost_team_df', '_build_capex_portfolio_asset_lookup',
    '_build_worklog_portfolio_cost_view_v2_unused', '_build_worklog_portfolio_cost_view_legacy',
    '_build_strategic_portfolio_wait_frame',
    # Finance (only those actually extracted)
    '_load_portfolio_cost_model', '_load_portfolio_bu_salary_map', '_load_portfolio_role_salary_map',
    '_build_portfolio_cost_team_df', '_build_capex_portfolio_asset_lookup',
    '_build_worklog_portfolio_cost_view_v2_unused', '_build_worklog_portfolio_cost_view_legacy',
    'build_worklog_cost_fact',
    # People (only those actually extracted)
    '_person_seniority_label', '_person_role_options', '_load_person_bu_map', '_load_person_team_map',
    'compute_jira_person_capacity_metrics', '_canonical_person_name', '_resolve_person_bu',
    '_resolve_person_team',
}

def find_function_end(lines, start_idx):
    """Find the end line of a function starting at start_idx."""
    if start_idx >= len(lines) or not lines[start_idx].startswith('def '):
        return None
    
    # Get indentation of def line
    def_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    
    # Find next line with same or lesser indentation that's not empty
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if not line.strip():  # Skip empty lines
            continue
        if line.startswith('def ') or (line and len(line) - len(line.lstrip()) <= def_indent and line[0] != ' '):
            return i
    
    return len(lines)

def remove_function_definitions(content, functions):
    """Remove function definitions from content."""
    lines = content.split('\n')
    lines_to_remove = set()
    
    for i, line in enumerate(lines):
        for func in functions:
            if re.match(rf'^def {re.escape(func)}\s*\(', line):
                end = find_function_end(lines, i)
                if end:
                    lines_to_remove.update(range(i, end))
                break
    
    # Remove lines (in reverse to maintain indices)
    result_lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]
    return '\n'.join(result_lines)

def add_imports(content):
    """Add imports for the new modules."""
    # Find the last import statement
    lines = content.split('\n')
    last_import_idx = 0
    
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i
    
    # Create import statements
    new_imports = """
# Domain-specific modules (Phase 2 refactoring)
from dashboards.portfolio import (
    build_portfolio_snapshot_from_csv, find_latest_portfolio_csv, get_portfolio_snapshot,
    compute_portfolio_snapshot, build_portfolio_tab, get_portfolio_project_filter_options,
    render_portfolio_roadmap_full_epics_view, render_portfolio_roadmap_quarter_view,
    build_portfolio_cost_model_snapshot, build_generated_portfolio_financial_view,
    build_portfolio_cross_delivery_integration, sync_portfolio_project_filter,
    portfolio_table_component, portfolio_is_cancelled_item, portfolio_is_highest_priority,
    portfolio_roadmap_progress_pct, portfolio_roadmap_status_label, portfolio_quarter_label_from_date,
    build_pm_portfolio_capex_view, _pm_portfolio_selected_specs, _pm_build_portfolio_lookup,
    _portfolio_team_to_pm_project_key, _load_portfolio_cost_model, _load_portfolio_bu_salary_map,
    _load_portfolio_role_salary_map, _build_portfolio_cost_team_df, _build_capex_portfolio_asset_lookup,
    _build_worklog_portfolio_cost_view_v2_unused, _build_worklog_portfolio_cost_view_legacy,
    _build_strategic_portfolio_wait_frame,
)

from dashboards.finance import (
    _load_portfolio_cost_model, _load_portfolio_bu_salary_map, _load_portfolio_role_salary_map,
    _build_portfolio_cost_team_df, _build_capex_portfolio_asset_lookup,
    _build_worklog_portfolio_cost_view_v2_unused, _build_worklog_portfolio_cost_view_legacy,
    build_worklog_cost_fact,
)

from dashboards.people import (
    _person_seniority_label, _person_role_options, _load_person_bu_map, _load_person_team_map,
    compute_jira_person_capacity_metrics, _canonical_person_name, _resolve_person_bu,
    _resolve_person_team,
)
"""
    
    # Insert imports
    lines.insert(last_import_idx + 1, new_imports)
    
    return '\n'.join(lines)

def main():
    base_path = Path('/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo')
    dashboard_path = base_path / 'dashboard_full.py'
    
    # Read original
    original = dashboard_path.read_text(encoding='utf-8')
    original_lines = len(original.split('\n'))
    
    print(f"Original dashboard_full.py: {original_lines} lines")
    
    # Remove function definitions
    print(f"Removing {len(EXTRACTED_FUNCS)} function definitions...")
    updated = remove_function_definitions(original, EXTRACTED_FUNCS)
    
    # Add imports
    print("Adding import statements for new modules...")
    updated = add_imports(updated)
    
    # Save backup and update
    backup_path = base_path / 'dashboard_full.py.bak'
    backup_path.write_text(original, encoding='utf-8')
    print(f"✓ Backup created: {backup_path.name}")
    
    dashboard_path.write_text(updated, encoding='utf-8')
    updated_lines = len(updated.split('\n'))
    
    reduction = original_lines - updated_lines
    print(f"✓ Updated dashboard_full.py: {updated_lines} lines (reduced by {reduction} lines)")
    print(f"  Reduction: {reduction/original_lines*100:.1f}%")

if __name__ == '__main__':
    main()
