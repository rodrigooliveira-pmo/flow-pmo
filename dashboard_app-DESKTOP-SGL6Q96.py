import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.express as px
import pandas as pd
import glob
import os

# --- 1. CONFIGURAÇÃO E CARREGAMENTO DE DADOS ---

def find_latest_file(folder, prefix):
    """Encontra o arquivo mais recente em uma pasta com um determinado prefixo."""
    files = glob.glob(os.path.join(folder, f'{prefix}*.xlsx'))
    if not files:
        return None
    return max(files, key=os.path.getctime)

DATA_FOLDER = r'C:\Users\W1 TI\OneDrive - W1\Documentos\Dados'
DASHBOARD_FILE_PATH = find_latest_file(DATA_FOLDER, 'dashboard_output_')

if not DASHBOARD_FILE_PATH:
    print(f"ERRO: Nenhum arquivo 'dashboard_output_*.xlsx' foi encontrado na pasta '{DATA_FOLDER}'.")
    print("Por favor, execute o script 'dash_board_metricas.py' primeiro.")
    exit()

print(f"Carregando dados do arquivo: {DASHBOARD_FILE_PATH}")

# Carrega todas as abas do arquivo Excel para um dicionário de DataFrames
try:
    xls = pd.ExcelFile(DASHBOARD_FILE_PATH)
    sheet_names = xls.sheet_names
    dfs = {}
    for sheet in sheet_names:
        dfs[sheet] = pd.read_excel(xls, sheet_name=sheet)
    print(f"Abas carregadas com sucesso: {list(dfs.keys())}")
except FileNotFoundError:
    print(f"ERRO: O arquivo '{DASHBOARD_FILE_PATH}' não foi encontrado.")
    exit()

# --- 2. FUNÇÕES AUXILIARES PARA GERAR LAYOUTS DAS ABAS ---

def create_generic_datatable(df, table_id, title):
    """Cria um Dash DataTable padrão para uma aba."""
    if df is None or df.empty:
        return html.Div(f"Dados para '{title}' não encontrados ou a aba está vazia.")
    
    # Converte colunas de data para um formato legível
    for col in df.select_dtypes(include=['datetime64[ns]']).columns:
        df[col] = df[col].dt.strftime('%Y-%m-%d')

    return html.Div([
        html.H3(title, style={'marginTop': '20px'}),
        dash_table.DataTable(
            id=table_id,
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            page_size=15,
            filter_action="native",
            sort_action="native",
            style_table={'overflowX': 'auto'},
            style_cell={
                'height': 'auto',
                'minWidth': '90px', 'width': '120px', 'maxWidth': '180px',
                'whiteSpace': 'normal',
                'textAlign': 'left'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            }
        )
    ])

def create_layout_dimensional():
    """Cria o layout para a aba de Análise Dimensional com gráfico."""
    df = dfs.get('Análise Dimensional')
    if df is None or df.empty:
        return html.Div("Dados para 'Análise Dimensional' não encontrados.")

    dimensoes = df['Dimensão'].unique()

    return html.Div([
        html.H3('Análise por Dimensão', style={'marginTop': '20px'}),
        html.Label('Selecione a Dimensão para Análise:'),
        dcc.Dropdown(
            id='dropdown-dimensional',
            options=[{'label': d, 'value': d} for d in dimensoes],
            value=dimensoes[0]
        ),
        html.Div([
            dcc.Graph(id='graph-dimensional-throughput', className='six columns'),
            dcc.Graph(id='graph-dimensional-defeitos', className='six columns'),
        ], className='row')
    ])

def create_layout_throughput_tipo():
    """Cria o layout para a aba Throughput por Tipo."""
    df = dfs.get('Throughput por Tipo')
    if df is None or df.empty:
        return html.Div("Dados para 'Throughput por Tipo' não encontrados.")

    tipos_item = df['Tipo Item'].unique()

    return html.Div([
        html.H3('Throughput Semanal por Tipo de Item', style={'marginTop': '20px'}),
        html.Label('Selecione o Tipo de Item:'),
        dcc.Dropdown(
            id='dropdown-throughput-tipo',
            options=[{'label': t, 'value': t} for t in tipos_item],
            value=tipos_item[0] if len(tipos_item) > 0 else None
        ),
        dcc.Graph(id='graph-throughput-tipo-trend'),
    ])

def create_layout_wip_pessoa(df_filtered):
    """Cria o layout para a aba WIP por Pessoa."""
    if df_filtered is None or df_filtered.empty:
        return html.Div("Dados para 'WIP por Pessoa' não encontrados para este projeto.")

    return html.Div([
        html.H3('Work In Progress (WIP) por Pessoa', style={'marginTop': '20px'}),
        dcc.Graph(id='graph-wip-pessoa-ranking'),
        create_generic_datatable(df_filtered, 'table-wip-pessoa', 'Dados Detalhados de WIP por Pessoa')
    ])

def create_layout_analise_tipos(df_filtered):
    """Cria o layout para a aba Análise Tipos."""
    if df_filtered is None or df_filtered.empty:
        return html.Div("Dados para 'Análise Tipos' não encontrados para este projeto.")

    return html.Div([
        html.H3('Análise por Tipo de Item', style={'marginTop': '20px'}),
        html.Div([
            dcc.Graph(id='graph-tipos-distribuicao', className='six columns'),
            dcc.Graph(id='graph-tipos-leadtime', className='six columns'),
        ], className='row'),
        create_generic_datatable(df_filtered, 'table-analise-tipos', 'Dados Detalhados por Tipo')
    ])

def create_layout_tendencias():
    """Cria o layout para a aba de Tendências."""
    return html.Div([
        html.H3('Análise de Tendências', style={'marginTop': '20px'}),
        dcc.Graph(id='graph-tendencias-throughput'),
        dcc.Graph(id='graph-tendencias-wip-leadtime')
    ])

# --- 3. INICIALIZAÇÃO DA APLICAÇÃO ---
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'], suppress_callback_exceptions=True)
app.title = "Dashboard de Métricas de Fluxo"

# --- 4. LAYOUT PRINCIPAL DA APLICAÇÃO ---
app.layout = html.Div(children=[
    html.H1(children='Dashboard de Métricas de Fluxo', style={'textAlign': 'center', 'marginBottom': '20px'}),

    # Filtro Global de Projeto
    html.Div([
        html.Label('Selecione o Projeto:'),
        dcc.Dropdown(
            id='filtro-projeto',
            options=[{'label': proj, 'value': proj} for proj in sorted(dfs.get('Dashboard', pd.DataFrame(columns=['Projeto'])).get('Projeto', pd.Series(dtype=str)).unique())],
            value=sorted(dfs.get('Dashboard', pd.DataFrame(columns=['Projeto'])).get('Projeto', pd.Series(dtype=str)).unique())[0] if not dfs.get('Dashboard', pd.DataFrame()).empty else None,
            clearable=False
        ),
    ], style={'width': '50%', 'margin': 'auto', 'marginBottom': '20px'}),

    # Estrutura de Abas
    dcc.Tabs(id="tabs-main", value='tab-1-dashboard', children=[
        dcc.Tab(label='Dashboard', value='tab-1-dashboard'),
        dcc.Tab(label='Adv - Fluxo', value='tab-2-fluxo'),
        dcc.Tab(label='Adv - Estabilidade', value='tab-3-estabilidade'),
        dcc.Tab(label='Adv - Saúde Fluxo', value='tab-4-saude'),
        dcc.Tab(label='Adv - Qualidade', value='tab-5-qualidade'),
        dcc.Tab(label='Análise Dimensional', value='tab-6-dimensional'),
        dcc.Tab(label='Análise Tipos', value='tab-7-tipos'),
        dcc.Tab(label='Tendências', value='tab-8-tendencias'),
        dcc.Tab(label='Tendências Completas', value='tab-9-tendencias-comp'),
        dcc.Tab(label='Throughput por Tipo', value='tab-10-throughput-tipo'),
        dcc.Tab(label='Análise Eficiência', value='tab-11-eficiencia'),
        dcc.Tab(label='WIP por Pessoa', value='tab-12-wip-pessoa'),
    ]),
    
    # Container para o conteúdo da aba selecionada
    html.Div(id='tabs-content', style={'padding': '20px'})
])

# --- 5. CALLBACKS PARA INTERATIVIDADE ---

# Callback principal para renderizar o conteúdo da aba selecionada
@app.callback(
    Output('tabs-content', 'children'),
    Input('tabs-main', 'value'),
    Input('filtro-projeto', 'value')
)
def render_tab_content(tab, selected_project):
    """Renderiza o conteúdo da aba com base na seleção e no filtro de projeto."""
    if not selected_project:
        return html.Div("Por favor, selecione um projeto.")

    # Mapeia o valor da aba para o nome da planilha e o tipo de layout
    tab_map = {
        'tab-1-dashboard': ('Dashboard', 'table'),
        'tab-2-fluxo': ('Adv - Fluxo', 'table'),
        'tab-3-estabilidade': ('Adv - Estabilidade', 'table'),
        'tab-4-saude': ('Adv - Saúde Fluxo', 'table'),
        'tab-5-qualidade': ('Adv - Qualidade', 'table'),
        'tab-6-dimensional': ('Análise Dimensional', 'dimensional'), # Gráfico
        'tab-7-tipos': ('Análise Tipos', 'tipos'), # Gráfico
        'tab-8-tendencias': ('Tendências', 'tendencias'),
        'tab-9-tendencias-comp': ('Tendências Completas', 'table'),
        'tab-10-throughput-tipo': ('Throughput por Tipo', 'throughput_tipo'), # Gráfico
        'tab-11-eficiencia': ('Análise Eficiência', 'table'),
        'tab-12-wip-pessoa': ('WIP por Pessoa', 'wip_pessoa'), # Gráfico
    }

    sheet_name, layout_type = tab_map.get(tab, (None, None))

    if not sheet_name or sheet_name not in dfs:
        return html.Div(f"Aba '{sheet_name}' não encontrada no arquivo de dados.")

    # Filtra o DataFrame pelo projeto selecionado
    df_filtered = dfs[sheet_name]
    if 'Projeto' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['Projeto'] == selected_project]

    # Renderiza o layout apropriado
    if layout_type == 'table':
        return create_generic_datatable(df_filtered, f'table-{sheet_name}', sheet_name)
    elif layout_type == 'dimensional':
        return create_layout_dimensional()
    elif layout_type == 'tendencias':
        return create_layout_tendencias()
    elif layout_type == 'throughput_tipo':
        return create_layout_throughput_tipo()
    elif layout_type == 'wip_pessoa':
        return create_layout_wip_pessoa(df_filtered)
    elif layout_type == 'tipos':
        return create_layout_analise_tipos(df_filtered)

    return html.Div("Tipo de layout não implementado.")

# Callback para a aba 'Análise Dimensional'
@app.callback(
    [Output('graph-dimensional-throughput', 'figure'),
     Output('graph-dimensional-defeitos', 'figure')],
    [Input('dropdown-dimensional', 'value'),
     Input('filtro-projeto', 'value')]
)
def update_dimensional_graphs(selected_dimension, selected_project):
    df_dim = dfs.get('Análise Dimensional')
    if df_dim is None or df_dim.empty:
        return {}, {}

    # Filtra pela dimensão e projeto
    df_filtered = df_dim[df_dim['Dimensão'] == selected_dimension]
    
    # O campo 'Categoria' pode conter o projeto, então filtramos por ele
    # Ex: "W1NNER - João" ou apenas "W1NNER"
    if selected_dimension != 'Por Projeto':
        df_filtered = df_filtered[df_filtered['Categoria'].str.startswith(selected_project)]

    # Gráfico de Throughput
    fig_throughput = px.bar(df_filtered, x='Categoria', y='Throughput',
                            title=f'Throughput por {selected_dimension} em {selected_project}',
                            labels={'Categoria': selected_dimension, 'Throughput': 'Itens Concluídos'})
    
    # Gráfico de Taxa de Defeitos
    fig_defeitos = px.bar(df_filtered, x='Categoria', y='Taxa_Defeitos',
                          title=f'Taxa de Defeitos (%) por {selected_dimension} em {selected_project}',
                          labels={'Categoria': selected_dimension, 'Taxa_Defeitos': 'Taxa de Defeitos (%)'})
    
    return fig_throughput, fig_defeitos

# Callback para a aba 'Tendências'
@app.callback(
    [Output('graph-tendencias-throughput', 'figure'),
     Output('graph-tendencias-wip-leadtime', 'figure')],
    [Input('tabs-main', 'value'), # Para garantir que só rode quando a aba estiver ativa
     Input('filtro-projeto', 'value')]
)
def update_tendencias_graphs(active_tab, selected_project):
    if active_tab != 'tab-8-tendencias':
        return {}, {}

    df_trends = dfs.get('Tendências')
    if df_trends is None or df_trends.empty:
        return {}, {}

    df_filtered = df_trends[df_trends['Projeto'] == selected_project]

    # Gráfico de Throughput
    fig_throughput = px.line(df_filtered, x='Semana', y=['Throughput Semanal', 'Throughput Médio (4s)'],
                             title=f'Tendência de Throughput para {selected_project}',
                             labels={'value': 'Quantidade', 'Semana': 'Semana'},
                             markers=True)

    # Gráfico de WIP e Lead Time
    fig_wip_lt = px.line(df_filtered, x='Semana', y=['WIP Médio (4s)', 'Lead Time Médio (4s)'],
                         title=f'Tendência de WIP e Lead Time para {selected_project}',
                         labels={'value': 'Valor', 'Semana': 'Semana'},
                         markers=True)

    return fig_throughput, fig_wip_lt

# Callback para a aba 'Throughput por Tipo'
@app.callback(
    Output('graph-throughput-tipo-trend', 'figure'),
    [Input('dropdown-throughput-tipo', 'value'),
     Input('filtro-projeto', 'value')]
)
def update_throughput_tipo_graphs(selected_type, selected_project):
    df_full = dfs.get('Throughput por Tipo')
    if df_full is None or df_full.empty or not selected_type:
        return {}

    df_filtered = df_full[(df_full['Projeto'] == selected_project) & (df_full['Tipo Item'] == selected_type)]

    fig_trend = px.line(df_filtered, x='Semana', y=['Throughput', 'P85 Lead Time (dias)', 'Eficiência'], 
                        title=f'Tendências para o tipo "{selected_type}" em {selected_project}',
                        labels={'value': 'Valor', 'variable': 'Métrica'},
                        markers=True)
    fig_trend.update_layout(hovermode="x unified")
    
    return fig_trend

# Callback para a aba 'WIP por Pessoa'
@app.callback(
    Output('graph-wip-pessoa-ranking', 'figure'),
    Input('filtro-projeto', 'value')
)
def update_wip_pessoa_graph(selected_project):
    df_wip = dfs.get('WIP por Pessoa')
    if df_wip is None or df_wip.empty:
        return {}
    
    df_filtered = df_wip[df_wip['Projeto'] == selected_project]
    
    # Agrupar por responsável para obter o WIP médio do período completo exibido
    df_agg = df_filtered.groupby('Responsável')['WIP_Médio'].mean().reset_index().sort_values('WIP_Médio', ascending=False).head(20)

    fig = px.bar(df_agg, x='Responsável', y='WIP_Médio', title=f'Ranking de WIP Médio por Pessoa (Top 20) em {selected_project}')
    return fig

# Callback para a aba 'Análise Tipos'
@app.callback(
    [Output('graph-tipos-distribuicao', 'figure'),
     Output('graph-tipos-leadtime', 'figure')],
    Input('filtro-projeto', 'value')
)
def update_analise_tipos_graphs(selected_project):
    df_tipos = dfs.get('Análise Tipos')
    if df_tipos is None or df_tipos.empty:
        return {}, {}

    df_filtered = df_tipos[df_tipos['Projeto'] == selected_project]
    
    # Para o gráfico de pizza, pegar apenas as categorias principais (não subtipos que começam com espaços)
    df_main_types = df_filtered[~df_filtered['Tipo'].str.strip().str.startswith(('  '))]

    fig_pie = px.pie(df_main_types, names='Tipo', values='Throughput', title=f'Distribuição de Throughput por Tipo em {selected_project}')
    fig_bar = px.bar(df_filtered, x='Tipo', y='Lead Time Médio (dias)', color='Tipo', title=f'Lead Time Médio por Tipo/Subtipo em {selected_project}')
    return fig_pie, fig_bar

# --- 6. EXECUÇÃO DA APLICAÇÃO ---
if __name__ == '__main__':
    app.run(debug=True)
