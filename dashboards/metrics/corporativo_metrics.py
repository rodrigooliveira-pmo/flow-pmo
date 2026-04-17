import pandas as pd
import numpy as np

TYPE_ISSUES = 'Issues/Defeitos/Problemas'

def get_period_grouper(periodicity):
    if periodicity == 'W':
        return pd.Grouper(key='DataDone', freq='W-MON')
    elif periodicity == 'Q':
        return pd.Grouper(key='DataDone', freq='QE')
    else: # M
        return pd.Grouper(key='DataDone', freq='MS')

def exact_empirical_percentile(series, quantile):
    """Calculates exact percentile consistent with previous dashboard code."""
    if series.empty:
        return np.nan
    return series.quantile(quantile, interpolation='midpoint')

def calc_lead_time_features(df, df_portfolio, start_ts, end_ts, periodicity='M', group_by_product=False, feature_types=None):
    """
    Calculates Lead Time for selected feature types (Epics, Features, Stories).
    """
    if feature_types is None:
        feature_types = ['Feature']
    
    feature_types_lower = [t.lower() for t in feature_types]

    df_feat = pd.DataFrame()
    lt_col = 'LeadTime_Portfolio_Dias'
    
    # Tentativa primária: usar portfólio para Epics/Features (CreatedAt -> ResolvedAt)
    if df_portfolio is not None and not df_portfolio.empty:
        _tipo_col = next((c for c in ['Tipo', 'tipo'] if c in df_portfolio.columns), None)
        if _tipo_col:
            # Filtra os tipos desejados
            mask_type = df_portfolio[_tipo_col].fillna('').str.lower().isin(feature_types_lower)
            # Para histórias ou caso falte no portfolio, talvez não encontremos tudo aqui, mas vamos usar o que der.
            # Mapeamento adicional para 'funcionalidade' caso 'feature' esteja selecionado
            if 'feature' in feature_types_lower:
                mask_type = mask_type | df_portfolio[_tipo_col].fillna('').str.lower().isin(['funcionalidade'])
                
            _pf_feat = df_portfolio[mask_type].copy()
            
            if not _pf_feat.empty and 'CreatedAt' in _pf_feat.columns and 'ResolvedAt' in _pf_feat.columns:
                _pf_feat['CreatedAt'] = pd.to_datetime(_pf_feat['CreatedAt'], errors='coerce', utc=True).dt.tz_localize(None)
                _pf_feat['ResolvedAt'] = pd.to_datetime(_pf_feat['ResolvedAt'], errors='coerce', utc=True).dt.tz_localize(None)
                _pf_feat = _pf_feat.dropna(subset=['CreatedAt', 'ResolvedAt'])
                _pf_feat[lt_col] = (_pf_feat['ResolvedAt'] - _pf_feat['CreatedAt']).dt.days
                _pf_feat = _pf_feat[_pf_feat[lt_col] >= 0]
                
                _pf_feat['DataDone'] = _pf_feat['ResolvedAt']
                _in_period = (_pf_feat['DataDone'] >= start_ts) & (_pf_feat['DataDone'] <= end_ts)
                df_feat = _pf_feat[_in_period].copy()

    # Fallback ou complemento: Fato_Items
    # Se não temos dados ou queremos complementar com histórias que não vêm no portfolio:
    if df_feat.empty:
        if 'WorkItemSubType' in df.columns:
            mask_type = df['WorkItemSubType'].fillna('').str.lower().isin(feature_types_lower)
            if 'feature' in feature_types_lower:
                mask_type = mask_type | df['WorkItemSubType'].fillna('').str.lower().isin(['funcionalidade'])
        elif 'IsFeature' in df.columns and 'feature' in feature_types_lower:
            mask_type = df['IsFeature'].fillna(False)
        else:
            mask_type = pd.Series(False, index=df.index)

        # Usar os mesmos critérios de eligibilidade de done_time_eligible_mask do dashboard_full
        # Mas vamos simplificar checando Concluido == 1 e DataDone dentro do periodo
        df_fb = df.copy()
        df_fb['DataDone'] = pd.to_datetime(df_fb['DataDone'], errors='coerce')
        _in_period = (df_fb['DataDone'] >= start_ts) & (df_fb['DataDone'] <= end_ts)
        _done = df_fb['Concluido'].fillna(0) == 1
        
        _df_fb = df_fb[_done & _in_period & mask_type].copy()
        
        _fallback_candidates = ['LeadTime_Selected_Dias', 'LeadTime_Dias', 'TempoExecucao_Dias']
        _fb_col = next((c for c in _fallback_candidates if c in _df_fb.columns and pd.to_numeric(_df_fb[c], errors='coerce').dropna().shape[0] > 0), None)
        
        if _fb_col:
            _df_fb[lt_col] = pd.to_numeric(_df_fb[_fb_col], errors='coerce')
            _df_fb = _df_fb.dropna(subset=[lt_col])
            _df_fb = _df_fb[_df_fb[lt_col] >= 0]
            df_feat = _df_fb

    if df_feat.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_feat['DataDone'] = pd.to_datetime(df_feat['DataDone'])
    grouper = get_period_grouper(periodicity)

    # Identificar coluna de projeto
    proj_col = next((c for c in ['Projeto', 'projeto', 'NomeProjeto'] if c in df_feat.columns), None)
    
    # Agregação Global
    global_agg = df_feat.groupby(grouper)[lt_col].agg(
        Media='mean',
        N='count'
    ).reset_index()
    global_agg['Produto'] = 'Todos'
    
    # Agregação por Produto
    prod_agg = pd.DataFrame()
    if group_by_product and proj_col:
        df_feat[proj_col] = df_feat[proj_col].fillna('Sem Produto')
        prod_agg = df_feat.groupby([proj_col, grouper])[lt_col].agg(
            Media='mean',
            N='count'
        ).reset_index()
        prod_agg.rename(columns={proj_col: 'Produto'}, inplace=True)
    
    return global_agg, prod_agg

def calc_execucao_onepage(df, df_portfolio, start_ts, end_ts, periodicity='M', group_by_product=False, feature_types=None):
    """
    Calculates Conclusão Projetos OnePage: Features Delivered vs Epics Planned.
    Using ONLY df_portfolio.
    Cumulative delivered in the Quarter vs Total planned in the Quarter.
    """
    if feature_types is None:
        feature_types = ['Feature']
    feature_types_lower = [t.lower() for t in feature_types]
    
    df_base = pd.DataFrame()
    
    if df_portfolio is not None and not df_portfolio.empty:
        df_pf = df_portfolio.copy()
        
        # Build mask based on selected feature types
        mask_type = pd.Series(False, index=df_pf.index)
        tipo_col = df_pf.get('Tipo', pd.Series(dtype=str)).fillna('').str.lower()
        
        if 'epic' in feature_types_lower or 'épico' in feature_types_lower:
            mask_type = mask_type | tipo_col.str.contains('pico|epic')
        if 'feature' in feature_types_lower or 'funcionalidade' in feature_types_lower:
            mask_type = mask_type | tipo_col.str.contains('feature|funcionalidade')
        if 'story' in feature_types_lower or 'história' in feature_types_lower:
            mask_type = mask_type | tipo_col.str.contains('stor|hist|ad-hoc')
            
        df_base = df_pf[mask_type].copy()
        
    if df_base.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    if 'ResolvedAt' in df_base.columns:
        df_base['ResolvedAt'] = pd.to_datetime(df_base['ResolvedAt'], errors='coerce', utc=True).dt.tz_localize(None)
    else:
        df_base['ResolvedAt'] = pd.NaT
        
    if 'DueDate' in df_base.columns:
        df_base['DueDate'] = pd.to_datetime(df_base['DueDate'], errors='coerce')
    else:
        df_base['DueDate'] = pd.NaT

    proj_col = next((c for c in ['Projeto', 'projeto', 'NomeProjeto'] if c in df_base.columns), None)
    if proj_col:
        df_base['ProjetoCol'] = df_base[proj_col].fillna('Sem Produto')
    else:
        df_base['ProjetoCol'] = 'Sem Produto'

    start_ts = pd.to_datetime(start_ts)
    end_ts = pd.to_datetime(end_ts)

    if periodicity == 'W':
        # Align to Mondays for consistency with rest of app
        periods = pd.date_range(start_ts, end_ts, freq='W-MON')
        get_end = lambda p: p + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59)
    elif periodicity == 'Q':
        periods = pd.date_range(start_ts, end_ts, freq='QE')
        get_end = lambda p: p + pd.offsets.QuarterEnd(0) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    else:
        periods = pd.date_range(start_ts, end_ts, freq='MS')
        get_end = lambda p: p + pd.offsets.MonthEnd(0) + pd.Timedelta(hours=23, minutes=59, seconds=59)

    # Ensure periods exist
    if len(periods) == 0:
        return pd.DataFrame(), pd.DataFrame()

    results_global = []
    results_prod = []

    for p in periods:
        p_end = get_end(p)
        q = p.to_period('Q')
        
        plan_mask = df_base['DueDate'].dt.to_period('Q') == q
        del_mask = (df_base['ResolvedAt'].dt.to_period('Q') == q) & (df_base['ResolvedAt'] <= p_end)
        
        plan_count = plan_mask.sum()
        del_count = del_mask.sum()
        
        results_global.append({
            'DataRef': p,
            'Planejados': plan_count,
            'Entregues': del_count,
            'Percentual': (del_count / plan_count * 100) if plan_count > 0 else 0,
            'Produto': 'Todos'
        })
        
        if group_by_product:
            df_plan_sub = df_base[plan_mask]
            df_del_sub = df_base[del_mask]
            
            plan_prod = df_plan_sub.groupby('ProjetoCol').size()
            del_prod = df_del_sub.groupby('ProjetoCol').size()
            
            projs = set(plan_prod.index).union(set(del_prod.index))
            for proj in projs:
                p_count = plan_prod.get(proj, 0)
                d_count = del_prod.get(proj, 0)
                results_prod.append({
                    'DataRef': p,
                    'Produto': proj,
                    'Planejados': p_count,
                    'Entregues': d_count,
                    'Percentual': (d_count / p_count * 100) if p_count > 0 else 0
                })

    global_agg = pd.DataFrame(results_global)
    prod_agg = pd.DataFrame(results_prod) if group_by_product else pd.DataFrame()

    return global_agg, prod_agg

def calc_change_failure_rate(df, start_ts, end_ts, periodicity='M', group_by_product=False):
    """
    Calculates Change Failure Rate: Defects delivered / Total delivered.
    """
    df_op = df.copy()
    df_op['DataDone'] = pd.to_datetime(df_op['DataDone'], errors='coerce')
    _in_period = (df_op['DataDone'] >= start_ts) & (df_op['DataDone'] <= end_ts)
    _done = df_op['Concluido'].fillna(0) == 1
    
    df_done = df_op[_done & _in_period].copy()
    if df_done.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    is_bug = df_done.get('TipoDemanda', pd.Series(dtype=str)) == TYPE_ISSUES
    
    grouper = get_period_grouper(periodicity)
    proj_col = next((c for c in ['Projeto', 'projeto', 'NomeProjeto'] if c in df_done.columns), None)

    # Agregação Global
    df_done['IsBug'] = np.where(is_bug, 1, 0)
    global_agg = df_done.groupby(grouper).agg(
        Falhas=('IsBug', 'sum'),
        Total=('IsBug', 'count')
    ).reset_index()
    global_agg['CFR'] = np.where(global_agg['Total'] > 0, (global_agg['Falhas'] / global_agg['Total']) * 100, 0)
    global_agg['Produto'] = 'Todos'
    
    prod_agg = pd.DataFrame()
    if group_by_product and proj_col:
        df_done[proj_col] = df_done[proj_col].fillna('Sem Produto')
        prod_agg = df_done.groupby([proj_col, grouper]).agg(
            Falhas=('IsBug', 'sum'),
            Total=('IsBug', 'count')
        ).reset_index()
        prod_agg.rename(columns={proj_col: 'Produto'}, inplace=True)
        prod_agg['CFR'] = np.where(prod_agg['Total'] > 0, (prod_agg['Falhas'] / prod_agg['Total']) * 100, 0)

    return global_agg, prod_agg
