#!/usr/bin/env python3
"""
Automated extraction of portfolio, finance, and people functions from dashboard_full.py
Creates 3 new domain-specific modules with proper imports.
"""

import ast
import re
from pathlib import Path
from collections import defaultdict

# Define functions by category
PORTFOLIO_FUNCS = {
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
    '_build_strategic_portfolio_wait_frame'
}

FINANCE_FUNCS = {
    'build_custo_tab', 'build_capex_view', 'build_capex_monthly_view', 'build_capex_planning_view',
    'build_worklog_cost_fact', 'get_financial_dates_range', 'get_financial_monthly_dates',
    'get_financial_quarterly_dates', 'render_capex_monthly_detail', 'render_capex_forecast_detail',
    'sync_finance_date_range', '_load_portfolio_cost_model', '_load_portfolio_bu_salary_map',
    '_load_portfolio_role_salary_map', '_build_portfolio_cost_team_df', '_build_capex_portfolio_asset_lookup',
    '_build_worklog_portfolio_cost_view_v2_unused', '_build_worklog_portfolio_cost_view_legacy',
    'build_custo_portfolio_summary_card', 'build_custo_person_kpi', 'build_custo_team_kpi',
    'build_custo_trend', 'build_capex_summary', 'build_capex_deliverables', 'resolve_investment_owner',
    'resolve_team_for_investment', 'render_custo_portfolio_summary', 'render_custo_portfolio_detailed',
    'render_capex_project_waterfall', 'render_capex_monthly_cost_trend', 'estimate_project_cost'
}

PEOPLE_FUNCS = {
    'build_people_tab', '_person_seniority_label', '_person_role_options', '_person_aliases',
    '_person_full_name', '_person_team_label', '_load_person_aliases_map', '_load_seniority_map',
    '_load_person_bu_map', '_load_person_team_map', 'compute_jira_person_capacity_metrics',
    '_canonical_person_name', '_person_display_name', '_resolve_person_bu', '_resolve_person_team',
    'build_people_capacity_view', 'build_people_team_capacity'
}

def read_file(path):
    """Read file content."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def find_function_boundaries(content, func_name):
    """Find start and end lines of a function using regex."""
    lines = content.split('\n')
    start_line = None
    
    # Find function definition
    for i, line in enumerate(lines):
        if re.match(rf'^def {re.escape(func_name)}\s*\(', line):
            start_line = i
            break
    
    if start_line is None:
        return None, None
    
    # Find end of function (next def at same indentation or EOF)
    end_line = len(lines)
    for i in range(start_line + 1, len(lines)):
        if lines[i] and not lines[i][0].isspace() and re.match(r'^def ', lines[i]):
            end_line = i
            break
    
    return start_line, end_line

def extract_function(content, func_name):
    """Extract function code including docstring and full body."""
    start, end = find_function_boundaries(content, func_name)
    if start is None:
        return None
    
    lines = content.split('\n')
    return '\n'.join(lines[start:end])

def create_module(module_name, functions, all_content):
    """Create a module file with extracted functions."""
    # Extract imports from dashboard_full
    lines = all_content.split('\n')
    imports = []
    for i, line in enumerate(lines):
        if i > 300 or (line and not line.startswith(('import', 'from', '#', ' ', '\t'))):
            break
        if line.startswith(('import ', 'from ')):
            imports.append(line)
    
    imports = '\n'.join(imports)
    
    # Extract functions
    extracted = []
    found_count = 0
    for func in sorted(functions):
        code = extract_function(all_content, func)
        if code:
            extracted.append(code)
            found_count += 1
        else:
            print(f"  ⚠ NOT FOUND: {func}")
    
    # Create module content
    module_content = f"""{imports}

# ============================================================================
# {module_name.upper()} MODULE - Extracted from dashboard_full.py
# ============================================================================

{chr(10).join(extracted)}
"""
    
    return module_content, found_count, len(functions)

def main():
    base_path = Path('/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo')
    
    # Read source
    dashboard = read_file(base_path / 'dashboard_full.py')
    
    print("\n" + "="*80)
    print("EXTRACTION PLAN")
    print("="*80)
    
    modules = {
        'portfolio': (PORTFOLIO_FUNCS, base_path / 'dashboards' / 'portfolio'),
        'finance': (FINANCE_FUNCS, base_path / 'dashboards' / 'finance'),
        'people': (PEOPLE_FUNCS, base_path / 'dashboards' / 'people'),
    }
    
    all_extracted = set()
    
    for module_name, (funcs, module_path) in modules.items():
        print(f"\n📦 {module_name.upper()}")
        print(f"  Target: {module_path}")
        print(f"  Functions to extract: {len(funcs)}")
        
        # Create directory
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Create functions.py
        content, found, total = create_module(module_name, funcs, dashboard)
        
        functions_py = module_path / 'functions.py'
        functions_py.write_text(content, encoding='utf-8')
        
        print(f"  ✓ Created {functions_py.name} ({found}/{total} functions found)")
        
        # Create __init__.py with exports
        init_content = f"""\"\"\"
{module_name.capitalize()} module - extracted from dashboard_full.py
\"\"\"

from .functions import (
{chr(10).join(f"    {func}," for func in sorted(funcs) if func)}
)

__all__ = [
{chr(10).join(f'    "{func}",' for func in sorted(funcs) if func)}
]
"""
        
        init_py = module_path / '__init__.py'
        init_py.write_text(init_content, encoding='utf-8')
        print(f"  ✓ Created {init_py.name} with exports")
        
        all_extracted.update(funcs)
    
    print("\n" + "="*80)
    print(f"SUMMARY: {len(all_extracted)} functions extracted to 3 modules")
    print("="*80)
    print("\nNEXT STEPS:")
    print("1. Review extracted modules in dashboards/portfolio, dashboards/finance, dashboards/people")
    print("2. Update imports in dashboard_full.py")
    print("3. Run tests to ensure functionality")
    print("\n")

if __name__ == '__main__':
    main()
