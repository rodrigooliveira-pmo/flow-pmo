import dash
try:
    from dash import dcc, html, Input, Output, State, dash_table
except ImportError:
    import dash_core_components as dcc
    import dash_html_components as html
    from dash.dependencies import Input, Output, State
    import dash_table


def create_table(df, table_id='table-main', title='Tabela'):
    if df is None or getattr(df, 'empty', True):
        return html.Div('Sem dados para exibir')
    return html.Div([html.H3(title), dash_table.DataTable(id=table_id, columns=[{'name':c,'id':c} for c in df.columns], data=df.head(200).to_dict('records'), page_size=20, style_table={'overflowX':'auto'})])


def create_generic_datatable(df, table_id, title):
    return create_table(df, table_id=table_id, title=title)