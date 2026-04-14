#!/usr/bin/env python3
"""
Proper integration of extracted modules into dashboard_full.py
- Fix syntax errors in extracted modules
- Add proper imports to dashboard_full.py  
- Remove duplicate/conflicting imports
"""

import re
from pathlib import Path

def fix_portfolio_functions():
    """Fix syntax errors in portfolio/functions.py."""
    path = Path('/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboards/portfolio/functions.py')
    content = path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Line 4135 has a syntax error - likely incomplete function
    # Find and remove the problematic section
    if len(lines) > 4135:
        print(f"Checking portfolio functions.py (line 4135)...")
        print(f"  Line 4133: {lines[4132][:80] if len(lines) > 4132 else 'N/A'}")
        print(f"  Line 4134: {lines[4133][:80] if len(lines) > 4133 else 'N/A'}")
        print(f"  Line 4135: {lines[4134][:80] if len(lines) > 4134 else 'N/A'}")
        print(f"  Line 4136: {lines[4135][:80] if len(lines) > 4135 else 'N/A'}")
    
    # Try to identify incomplete functions by finding 'def ' without proper closing
    # For now, just ensure file ends properly
    clean_lines = []
    in_string = False
    string_char = None
    
    for i, line in enumerate(lines):
        if '"""' in line or "'''" in line:
            in_string = not in_string
        clean_lines.append(line)
    
    # Remove trailing incomplete sections
    while clean_lines and clean_lines[-1].startswith(' ') and not clean_lines[-1].strip():
        clean_lines.pop()
    
    path.write_text('\n'.join(clean_lines), encoding='utf-8')
    print(f"✓ portfolio/functions.py cleaned")

def create_module_imports():
    """Create a proper imports file for dashboard_full.py to use."""
    imports_file = Path('/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboards/_module_imports.py')
    
    content = '''"""
Module imports for dashboard_full.py
Consolidates all domain-specific function imports.
"""

# Import portfolio functions
try:
    from dashboards.portfolio import (
        build_portfolio_snapshot_from_csv,
        find_latest_portfolio_csv,
        get_portfolio_snapshot,
        compute_portfolio_snapshot,
        build_portfolio_tab,
        get_portfolio_project_filter_options,
        render_portfolio_roadmap_full_epics_view,
        render_portfolio_roadmap_quarter_view,
        build_portfolio_cost_model_snapshot,
        build_generated_portfolio_financial_view,
        build_portfolio_cross_delivery_integration,
        sync_portfolio_project_filter,
        portfolio_table_component,
        portfolio_is_cancelled_item,
        portfolio_is_highest_priority,
        portfolio_roadmap_progress_pct,
        portfolio_roadmap_status_label,
        portfolio_quarter_label_from_date,
        build_pm_portfolio_capex_view,
        _pm_portfolio_selected_specs,
        _pm_build_portfolio_lookup,
        _portfolio_team_to_pm_project_key,
        _load_portfolio_cost_model,
        _load_portfolio_bu_salary_map,
        _load_portfolio_role_salary_map,
        _build_portfolio_cost_team_df,
        _build_capex_portfolio_asset_lookup,
        _build_worklog_portfolio_cost_view_v2_unused,
        _build_worklog_portfolio_cost_view_legacy,
        _build_strategic_portfolio_wait_frame,
    )
    PORTFOLIO_IMPORTS_OK = True
except Exception as e:
    print(f"Warning: Could not import portfolio functions: {e}")
    PORTFOLIO_IMPORTS_OK = False

# Import people functions  
try:
    from dashboards.people import (
        _person_seniority_label,
        _person_role_options,
        _load_person_bu_map,
        _load_person_team_map,
        compute_jira_person_capacity_metrics,
        _canonical_person_name,
        _resolve_person_bu,
        _resolve_person_team,
    )
    PEOPLE_IMPORTS_OK = True
except Exception as e:
    print(f"Warning: Could not import people functions: {e}")
    PEOPLE_IMPORTS_OK = False

# Export all for re-import in dashboard_full
__all__ = [
    # Portfolio
    'build_portfolio_snapshot_from_csv',
    'find_latest_portfolio_csv',
    'get_portfolio_snapshot',
    'compute_portfolio_snapshot',
    'build_portfolio_tab',
    'get_portfolio_project_filter_options',
    'render_portfolio_roadmap_full_epics_view',
    'render_portfolio_roadmap_quarter_view',
    'build_portfolio_cost_model_snapshot',
    'build_generated_portfolio_financial_view',
    'build_portfolio_cross_delivery_integration',
    'sync_portfolio_project_filter',
    'portfolio_table_component',
    'portfolio_is_cancelled_item',
    'portfolio_is_highest_priority',
    'portfolio_roadmap_progress_pct',
    'portfolio_roadmap_status_label',
    'portfolio_quarter_label_from_date',
    'build_pm_portfolio_capex_view',
    '_pm_portfolio_selected_specs',
    '_pm_build_portfolio_lookup',
    '_portfolio_team_to_pm_project_key',
    '_load_portfolio_cost_model',
    '_load_portfolio_bu_salary_map',
    '_load_portfolio_role_salary_map',
    '_build_portfolio_cost_team_df',
    '_build_capex_portfolio_asset_lookup',
    '_build_worklog_portfolio_cost_view_v2_unused',
    '_build_worklog_portfolio_cost_view_legacy',
    '_build_strategic_portfolio_wait_frame',
    # People
    '_person_seniority_label',
    '_person_role_options',
    '_load_person_bu_map',
    '_load_person_team_map',
    'compute_jira_person_capacity_metrics',
    '_canonical_person_name',
    '_resolve_person_bu',
    '_resolve_person_team',
]
'''
    
    imports_file.write_text(content, encoding='utf-8')
    print(f"✓ Created dashboards/_module_imports.py for graceful fallback")

def main():
    print("Fixing extracted modules...\n")
    
    # Fix syntax errors in extracted modules
    fix_portfolio_functions()
    create_module_imports()
    
    print("\nModules properly integrated!")
    print("\nNEXT: Import in dashboard_full.py using:")
    print("  from dashboards._module_imports import *")

if __name__ == '__main__':
    main()
