# Arquitetura e Funcionamento do Projeto

## 1) Visão Geral

Este projeto implementa um pipeline completo de métricas de fluxo e portfólio:

1. Exporta dados Jira para CSV (projetos de fluxo e portfólio BT/NS).
2. Consolida e padroniza os dados de fluxo.
3. Calcula métricas semanais, métricas avançadas e eficiência baseada em capacidade de fila.
4. Gera artefatos para Excel e modelo dimensional para Power BI.
5. Publica dashboard interativo em Dash (`dashboard_full.py`) com abas operacionais e executivas.

Objetivo: acompanhar desempenho de entrega, gargalos, previsibilidade, qualidade e saúde do fluxo por projeto, tipo e responsável.

## 2) Componentes Principais

### 2.1 `jira_to_pipeline_csv.py` (Extração Jira de Fluxo)

Responsável por:

- Consultar Jira com fallback robusto de endpoint:
  - `POST /rest/api/3/search/jql`
  - `GET /rest/api/3/search/jql`
  - `POST /rest/api/3/search` (legado)
- Repetição automática para falhas transitórias (`429`, `5xx`) com backoff e `Retry-After`.
- Busca paralela do changelog (parâmetro `--workers`).
- Exportar CSV no formato esperado pelo pipeline (`w1nner-downstream-<data>-data.csv`, etc.).

### 2.2 `jira_portfolio_to_csv.py` (Extração Jira de Portfólio)

Responsável por:

- Exportar snapshot de portfólio dos projetos BT/NS.
- Incluir campos de relação e governança (`ParentID`, `Team`, `Status`, `StatusChangedAt`, `UpdatedAt`).
- Gerar arquivo `portfolio-bt-ns-<data>-data.csv` consumido pela aba de portfólio no Dash.

### 2.3 `dash_board_metricas.py` (Pipeline de Dados)

Responsável por:

- Descoberta e leitura robusta de CSVs.
- Detecção automática de colunas de fluxo/datas.
- Classificação de tipo de item (`Defeitos`, `Desenvolvimento`, `Outro`).
- Cálculo de métricas semanais e análises avançadas.
- Cálculo de eficiência de fluxo por regra de capacidade de fila (`1 - λ/μ`), com proteção para limites.
- Geração de:
  - `dashboard_output_<timestamp>.xlsx`,
  - `PowerBI_Model_<timestamp>.xlsx`.

### 2.4 `dashboard_full.py` (Aplicação Dash)

Responsável por:

- Localizar o `PowerBI_Model_*.xlsx` mais recente.
- Carregar tabelas dimensionais/fato e aplicar filtros globais.
- Consumir o CSV de portfólio mais recente (`portfolio-bt-ns-*-data.csv`) com cache.
- Renderizar painéis de fluxo, gargalos, eficiência e portfólio.

### 2.5 `run_all_projects.ps1` (Orquestração)

Responsável por:

- Carregar variáveis do `jira_env.txt`.
- Executar exportação dos 4 projetos de fluxo.
- Executar exportação de portfólio (opcional).
- Executar pipeline de métricas (opcional).
- Subir dashboard automaticamente (opcional).

## 3) Arquitetura de Dados

### 3.1 Origem

- Pasta padrão de entrada/saída:
  - Windows: `C:\Users\W1 TI\OneDrive - W1\Documentos\Dados`
  - macOS: `~/Library/CloudStorage/OneDrive-W1/Documentos/Dados`
- Entradas:
  - CSVs de fluxo por projeto (`*-downstream-*-data.csv`)
  - CSV de portfólio (`portfolio-bt-ns-*-data.csv`)

### 3.2 Padronização

Durante a ingestão:

- Colunas de fluxo são mapeadas para estágios principais (`Sprint Backlog`, `In Progress`, `Done`).
- Datas são convertidas para `datetime`.
- `Blocked Days` é convertido para numérico.
- São adicionadas colunas derivadas de negócio e análise.

### 3.3 Modelo Analítico (Power BI)

Modelo estrela com:

- **Fato**: `Fato_Items`
- **Dimensões**:
  - `Dim_Projeto`
  - `Dim_Data`
  - `Dim_Tipo`
  - `Dim_Responsavel` (se disponível)
  - `Dim_Componente` (se disponível)
  - `Dim_Prioridade` (se disponível)

Métricas por item na fato incluem:

- `TempoBacklog_Dias`
- `TempoExecucao_Dias`
- `LeadTime_Dias`
- `Eficiencia`
- `EficienciaAjustada`
- `TempoBloqueioDias`
- `TempoEsperaIntermediariaDias`
- `Concluido`, `Bloqueado`, `EmWIP`, `WIP_Dias`

## 4) Fluxo de Processamento

1. Exportar dados Jira de fluxo (`jira_to_pipeline_csv.py`).
2. Exportar snapshot Jira de portfólio (`jira_portfolio_to_csv.py`).
3. Consolidar CSVs de fluxo.
4. Eliminar duplicados por `ID` dentro de cada projeto.
5. Calcular métricas semanais em padrão ISO (segunda a domingo).
6. Gerar abas analíticas no Excel consolidado.
7. Gerar modelo dimensional para Power BI.
8. Consumir modelo + snapshot de portfólio no `dashboard_full.py`.

## 5) Métricas e Análises Entregues

### 5.1 Dashboard Semanal Base

- Taxa de chegada
- Throughput
- WIP e WIP Age
- Lead Time médio e P85
- Eficiência de fluxo (`1 - λ/μ`)
- `% Demanda de Falha` e `% Demanda de Valor`

### 5.2 Blocos Avançados

- Fluxo: cycle time, backlog time, bloqueios e esperas.
- Estabilidade: desvio padrão, coeficiente de variação e percentis.
- Saúde de fluxo: razão chegada/throughput, crescimento de WIP, itens vencidos.
- Qualidade: debt ratio e razão valor/custo.
- Tendências: médias móveis, direção e momentum.
- Throughput por tipo: segmentação semanal.
- Eficiência detalhada por item.
- WIP por pessoa.
- Capacidade de fila.
- Portfólio BT/NS com aging e pendências por quadrante.

## 6) Dashboard Interativo (`dashboard_full.py`)

Abas principais:

1. Performance do Serviço
2. Portfólio
3. Painel Fluxo
4. Fluxo
5. Estabilidade
6. Saúde Fluxo
7. Qualidade
8. Análise Dimensional
9. Análise Tipos
10. Tendências
11. Throughput por Tipo
12. Análise Eficiência
13. WIP por Pessoa
14. Estatística Descritiva
15. Capacidade de Fila

Características:

- Filtros globais por período/projeto/tipo/responsável.
- KPIs, gráficos de tendência e tabelas interativas.
- Ranking de gargalos por etapa e sinalização de criticidade.
- Snapshot executivo de portfólio com agrupamento por time/projeto.

## 7) Operação e Execução

### 7.1 Execução ponta a ponta (recomendado)

```powershell
.\run_all_projects.ps1
```

Parâmetros úteis:

- `-RunPortfolioExport $true|$false`
- `-RunMetrics $true|$false`
- `-OpenDashboard $true|$false`
- `-Workers <n>`

### 7.2 Execução manual

```bash
python jira_to_pipeline_csv.py --projects W1NNR S1NC BF DT --out "<arquivo>"
python jira_portfolio_to_csv.py --projects BT NS --out "<arquivo>"
python dash_board_metricas.py
python dashboard_full.py
```

## 8) Dependências Técnicas

Principais bibliotecas:

- `pandas`
- `numpy`
- `dash`
- `plotly`
- `requests`
- `openpyxl` (preferencial) ou `xlsxwriter` (fallback para escrita Excel)

## 9) Decisões de Arquitetura Relevantes

- Separação clara entre extração Jira, processamento de métricas e visualização.
- Fallback de endpoint Jira para compatibilidade com tenants diferentes.
- Retentativa automática para estabilidade de coleta.
- Modelo dimensional para facilitar consumo no Power BI e Dash.
- Dashboard sempre acoplado ao arquivo `PowerBI_Model_*.xlsx` mais recente.

## 10) Limitações e Pontos de Atenção

- `dash_board_metricas.py` ainda executa processamento ao importar (efeito colateral).
- Parte das métricas DORA na aba de performance está como placeholder (`—`).
- A seleção de arquivos mais recentes depende de timestamps; validar em ambientes compartilhados.
- A qualidade da aba Portfólio depende do preenchimento de `Team`/parentesco no Jira.

## 11) Recomendações de Evolução

1. Adicionar entrada explícita (`if __name__ == '__main__':`) no pipeline.
2. Consolidar contrato de dados para os dois tipos de CSV (fluxo e portfólio).
3. Externalizar configurações em `.env`/`config.yaml`.
4. Incluir testes automáticos para regras de eficiência e gargalo.
5. Versionar semanticamente as mudanças de documentação e scripts de coleta.
