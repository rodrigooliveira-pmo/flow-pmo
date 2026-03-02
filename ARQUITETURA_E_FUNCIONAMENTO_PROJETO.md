# Arquitetura e Funcionamento do Projeto

## 1) Visão Geral

Este projeto implementa um pipeline completo de métricas de fluxo e portfólio:

1. Exporta dados Jira para CSV (projetos de fluxo e portfólio BT/NS).
2. Consolida e padroniza os dados de fluxo.
3. Calcula métricas semanais, métricas avançadas e eficiência baseada em capacidade de fila.
4. Gera artefatos para Excel e modelo dimensional para Power BI.
5. Publica dashboards interativos em Dash (`dashboard_full.py`, `dashboard_process_mining.py` e `dashboard_app.py`).

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

### 2.5 `process_mining_jira.py` (Pipeline de Process Mining)

Responsável por:

- Gerar artefatos de process mining a partir de changelog downstream do Jira.
- Produzir workbook de process mining (`w1nner-process-mining-<timestamp>.xlsx`) com conformidade, variantes, tempos e vazão.
- Gerar artefatos visuais de apoio (`pm4py-dfg`, rede heurística, árvore indutiva, rede de Petri), quando disponíveis.

### 2.6 `run_all_projects.ps1` (Orquestração)

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
8. Gerar artefatos de process mining (`process_mining_jira.py`) quando necessário.
9. Consumir modelo + snapshot de portfólio no `dashboard_full.py`.

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

## 6) Dashboards Interativos

### 6.1 Dashboard Principal (`dashboard_full.py`)

Abas de serviços atualmente expostas:

1. Performance do Serviço
2. One Page Report
3. Painel Fluxo
4. Lead Time
5. Fluxo
6. CFD
7. Saúde do Fluxo
8. Análise Fluxo
9. Tendências
10. Throughput Breakdown
11. Padrões Sistêmicos
12. WIP por Pessoa
13. Estatística Descritiva
14. Capacidade de Fila

Características:

- Menu inicial com navegação entre visões de Portfólio e Serviços.
- Filtros globais por período/projeto/tipo/classe de serviço/responsável.
- KPIs, gráficos de tendência e tabelas interativas.
- Ranking de gargalos por etapa, CFD macro/detalhado e visões executivas dinâmicas.
- Integração com indicadores de process mining no One Page (conformidade e sinais de retrabalho), quando artefatos estiverem disponíveis.

### 6.2 Dashboard Dedicado de Process Mining (`dashboard_process_mining.py`)

- Aplicação Dash focada em process mining Jira (W1NNER), com exploração de conformidade e fluxo real.
- Visões de mapa de transições, variantes, fitness/conformance, dotted chart, gargalos por transição e análises de capacidade por pessoa.
- Consumo do workbook `w1nner-process-mining-*.xlsx` mais recente e artefatos derivados do `process_mining_jira.py`.

### 6.3 Dashboard Secundário (`dashboard_app.py`)

- Aplicação Dash simplificada para leitura direta do `dashboard_output_*.xlsx`.
- Útil para validações rápidas, smoke tests e consumo leve das análises.

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

## 12) Inventário Atual de Funcionalidades (Atualizado em 02/03/2026)

### 12.1 Extração Jira (Fluxo)

- Exportação por projeto para CSV downstream (`*-data.csv`) via `jira_to_pipeline_csv.py`.
- Fallback de endpoints Jira (`search/jql` e `search`) com retry/backoff para `429`/`5xx`.
- Resolução de fluxo por projeto (legado vs Data&Analytics) e por tipo de item no DT (melhoria vs bug/incidente/ad-hoc).
- Exportação de gargalos por projeto (`*-data_bottlenecks.csv`).
- Suporte opcional a changelog detalhado por projeto (`--detailed-changelog-out` no script macOS).
- Datas por etapa configuráveis no exportador (modo com última entrada por etapa, usado para alinhar WIP/WIP Age com referência operacional).

### 12.2 Extração Jira (Portfólio)

- Exportação do snapshot de portfólio BT/NS (`portfolio-bt-ns-<data>-data.csv`) via `jira_portfolio_to_csv.py`.
- Campos de governança e relacionamento (ex.: time, parent, status e datas de atualização/mudança).
- Arquivo estável `portfolio-bt-ns-latest-data.csv` para consumo do dashboard sem depender de nome datado.

### 12.3 Orquestração (Windows/macOS)

- Scripts `run_all_projects.ps1` e `run_all_projects_macos.sh` para execução ponta a ponta.
- Sequenciamento de exportação de 4 projetos de fluxo (`W1NNR`, `S1NC`, `BF`, `DT`), portfólio, métricas e dashboard.
- Carregamento de variáveis do `jira_env.txt`.
- Proteção contra `JIRA_STATUS_MAP` global em execução multi-projeto (usa `JIRA_IGNORE_STATUS_MAP=1`).
- Geração/atualização de aliases `latest` para artefatos de portfólio e gargalos; no macOS também para downstream detalhado e changelog detalhado.

### 12.4 Pipeline de Métricas e Modelo Analítico (`dash_board_metricas.py`)

- Consolidação de CSVs de fluxo multi-projeto e padronização de colunas.
- Cálculo de métricas de lead time, cycle time, backlog time, WIP, throughput, bloqueios e eficiência.
- Regras de elegibilidade para métricas de tempo de concluídos (exclusão de itens cancelados).
- Geração de `dashboard_output_<timestamp>.xlsx` e `PowerBI_Model_<timestamp>.xlsx`.
- Geração de workbook consolidado de gargalos (`bottlenecks_consolidado_<timestamp>.xlsx` + `latest`).
- Modelo dimensional para consumo em Power BI e Dash.

### 12.5 Dashboard Principal (`dashboard_full.py`)

- App Dash principal com menu inicial (`Portfólio` vs `Serviços (Value Stream)`).
- Filtros globais por período, projeto, tipo, classe de serviço, responsável e time de portfólio.
- Abas de serviços atualmente expostas:
  - `One Page Report`
  - `Performance do Serviço`
  - `Painel Fluxo`
  - `Lead Time`
  - `Fluxo`
  - `CFD`
  - `Saúde do Fluxo`
  - `Análise Fluxo`
  - `Tendências`
  - `Throughput Breakdown`
  - `Padrões Sistêmicos`
  - `WIP por Pessoa`
  - `Estatística Descritiva`
  - `Capacidade de Fila`
- Aba de Portfólio com leitura de CSV local/URL por env e cache em memória.
- Filtro configurável de etapas de comprometimento para Lead Time (`LeadTime_Selected_Dias`).
- CFD em aba dedicada, com modos macro/detalhado e painel sumário por ponto (hover/click).
- Consolidação de abas de análise em `Análise Fluxo` e de saúde/qualidade em `Saúde do Fluxo`.
- Fallbacks para carregamento de CSV downstream detalhado por projeto (arquivo local, alias `latest`, URL por projeto/global).

### 12.6 Dashboard Secundário (`dashboard_app.py`)

- Aplicação Dash alternativa/mais simples para consumo do `dashboard_output`.
- Abas analíticas e gráficos auxiliares (dimensional, throughput por tipo, WIP por pessoa, tendências e Lead Time).
- Útil para validação/smoke de visualizações sem toda a complexidade do `dashboard_full.py`.

### 12.7 Process Mining (Pipeline + Dashboard Dedicado)

- Script `process_mining_jira.py` para geração de workbook `w1nner-process-mining-<timestamp>.xlsx`.
- Planilhas com conformidade, variantes, tempos por status, vazão por pessoa, métricas PM4Py (DFG/Alignments/TBR) e metadados.
- Dashboard dedicado `dashboard_process_mining.py` para exploração operacional/tática dos resultados de process mining.
- Suporte a artefatos visuais (DFG, rede heurística, árvore indutiva, rede de Petri) quando presentes no diretório de dados.

### 12.8 Deploy Web (Vercel / `api/index.py`)

- Entrypoint Python para Vercel que carrega dinamicamente módulo/atributo do Dash (`FLOW_PMO_DASH_MODULE`, `FLOW_PMO_DASH_ATTR`).
- Fallback de erro de inicialização com resposta HTTP 500 e mensagem explícita (facilita diagnóstico em produção).
- Arquivos de suporte de deploy: `vercel.json` e `DEPLOY_VERCEL.md`.

## 13) Resumo das Entregas dos Últimos 30 Dias (25/01/2026 a 24/02/2026)

### 13.1 Recorte e evidência

- Janela analisada: **25/01/2026 a 24/02/2026**.
- Neste clone, o histórico Git disponível para a janela começa em **19/02/2026** (`Initial commit (clean secrets)`).
- Total de commits no período: **51**.
- Distribuição por dia:
  - **19/02/2026:** 7 commits
  - **20/02/2026:** 22 commits
  - **23/02/2026:** 22 commits

### 13.2 Principais entregas (consolidadas)

1. **Evolução forte do `dashboard_full.py` (principal foco do período)**
- Criação/ajuste de menu inicial com separação entre `Portfólio` e `Serviços`.
- Nova aba dedicada de `CFD` com melhorias visuais e opção macro/detalhada.
- Consolidação de abas em `Análise Fluxo` e `Saúde do Fluxo`.
- Nova aba/visões de `Lead Time` e ajustes de KPIs operacionais.
- Melhorias de UX/correções de regressão (ex.: calendário/year dropdown).

2. **Lead Time/Cycle Time: correções de semântica e qualidade estatística**
- Implementação de percentis empíricos exatos (sem interpolação linear).
- Exclusão de itens cancelados nas métricas de tempo de concluídos.
- Filtro de etapas de comprometimento para Lead Time (`LeadTime_Selected_Dias`) aplicado nas abas operacionais.
- Ajustes para tornar Painel/Fluxo sensíveis ao filtro (incluindo WIP/WIP Age quando aplicável).
- Fallbacks para não deixar dropdown de etapas vazio sem CSV downstream local.

3. **CFD: ganho funcional e visual**
- CFD movido para aba própria.
- Painel de estatísticas sumárias por ponto (hover/click).
- Melhorias visuais (stacked areas, paleta mais contrastante, hover unificado).
- Uso de CSV downstream por projeto para modo detalhado e correções de escopo por IDs filtrados.

4. **Pipeline e exportação Jira (fluxo por projeto/tipo)**
- Correções de mapeamento de status e fluxo para projetos legados e DT.
- Suporte a fluxo por tipo no DT (melhoria vs ad-hoc/bug/incidente).
- Correção de datas de etapa por última entrada (`latest`) para alinhar com referência operacional.
- Geração de artefatos `latest` para downstream/gargalos (especialmente no script macOS).
- Consolidação de gargalos em workbook único (`bottlenecks_consolidado_*` + `latest`).

5. **Portfólio e integração em produção**
- Suporte de portfólio por CSV via URL/arquivo em variáveis de ambiente.
- Melhorias em campos e visões de portfólio no dashboard.
- Cache e fallback de leitura para reduzir fragilidade operacional.

6. **Deploy e operação (Vercel)**
- Ajustes de `vercel.json`, rotas/rewrite e entrypoint Python.
- Tratamento melhor de erro de inicialização no `api/index.py`.
- Documentação de deploy (`DEPLOY_VERCEL.md`) atualizada no período.

### 13.3 Arquivos com maior concentração de mudanças no período (sinal de onde houve entrega)

- `dashboard_full.py` (maior volume de alterações)
- `tasks/todo.md` (registro detalhado de especificações/reviews)
- `dash_board_metricas.py`
- `jira_to_pipeline_csv.py`
- `run_all_projects.ps1`
- `run_all_projects_macos.sh`
- `jira_portfolio_to_csv.py`
- `dashboard_app.py`
- `api/index.py` / `vercel.json`

### 13.4 Observação de rastreabilidade

- O arquivo `tasks/todo.md` contém o detalhamento mais granular das entregas (objetivo, critério de aceite, validações e sugestão de commit) e deve ser usado como trilha principal de auditoria funcional.
