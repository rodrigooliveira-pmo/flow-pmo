# Arquitetura e Funcionamento do Projeto

## 1) Visão Geral

Este projeto implementa um pipeline completo de métricas de fluxo de trabalho:

1. Lê múltiplos arquivos CSV de itens de trabalho (origem operacional).
2. Consolida e padroniza os dados.
3. Calcula métricas semanais e métricas avançadas.
4. Gera artefatos para análise em Excel e para consumo em Power BI.
5. Publica um dashboard interativo em Dash (`dashboard_full.py`) usando o modelo mais recente.

O objetivo principal é acompanhar desempenho de entrega, qualidade e saúde de fluxo por projeto, tipo de demanda e responsável.

## 2) Componentes Principais

### 2.1 `dash_board_metricas.py` (Pipeline de Dados)

Responsável por:

- Descoberta e leitura robusta de CSVs (múltiplos encodings e delimitadores).
- Detecção automática de colunas de fluxo/datas.
- Classificação de tipo de item (`Defeitos`, `Desenvolvimento`, `Outro`).
- Cálculo de métricas semanais e análises avançadas.
- Geração de:
  - `dashboard_output_<timestamp>.xlsx` (abas analíticas),
  - `PowerBI_Model_<timestamp>.xlsx` (modelo dimensional).

### 2.2 `dashboard_full.py` (Aplicação Dash)

Responsável por:

- Localizar o `PowerBI_Model_*.xlsx` mais recente na pasta de dados.
- Carregar tabelas dimensionais e fato.
- Aplicar filtros globais (período, projeto, tipo, responsável).
- Renderizar abas analíticas com KPIs, tabelas e gráficos interativos.

### 2.3 Arquivos de Apoio

- `dashboard_app.py`: alternativa de aplicação Dash (escopo menor em relação ao `dashboard_full.py`).
- Documentação complementar no repositório (`INDICE_CENTRAL.md`, `RESUMO_EXECUTIVO.md`, `ARQUITETURA_MODELO.md`, etc.).

## 3) Arquitetura de Dados

## 3.1 Origem

- Pasta padrão de entrada/saída:
  - Windows: `C:\Users\W1 TI\OneDrive - W1\Documentos\Dados`
  - macOS: `~/Library/CloudStorage/OneDrive-W1/Documentos/Dados`
- Entradas: arquivos `*.csv` exportados de gestão de trabalho.

## 3.2 Padronização

Durante a ingestão:

- Colunas de data do fluxo são mapeadas para:
  - `Sprint Backlog`
  - `In Progress`
  - `Done`
- Datas são convertidas para `datetime`.
- `Blocked Days` é convertido para numérico.
- São adicionadas colunas derivadas:
  - `Projeto`
  - `WorkItemCategory`
  - `WorkItemSubType`

## 3.3 Modelo Analítico (Power BI)

Modelo estrela com:

- **Fato**: `Fato_Items`
- **Dimensões**:
  - `Dim_Projeto`
  - `Dim_Data`
  - `Dim_Tipo`
  - `Dim_Responsavel` (se aplicável)
  - `Dim_Componente` (se aplicável)
  - `Dim_Prioridade` (se aplicável)

Métricas por item na fato incluem, entre outras:

- `TempoBacklog_Dias`
- `TempoExecucao_Dias`
- `LeadTime_Dias`
- `Eficiencia`
- `EficienciaAjustada`
- `TempoBloqueioDias`
- `TempoEsperaIntermediariaDias`
- `Concluido`, `Bloqueado`, `EmWIP`, `WIP_Dias`

## 4) Fluxo de Processamento

1. Coleta de CSVs da pasta de dados.
2. Leitura robusta com fallback de encoding/delimitador.
3. Identificação de projeto por `ID` e/ou nome de arquivo.
4. Eliminação de duplicados por `ID` dentro de cada projeto.
5. Cálculo de métricas em janelas semanais (terça a terça no pipeline principal).
6. Geração de abas analíticas no Excel consolidado.
7. Geração do modelo dimensional para Power BI.
8. Consumo do modelo pelo `dashboard_full.py`.

## 5) Métricas e Análises Entregues

## 5.1 Dashboard Semanal Base

- Taxa de chegada
- Throughput
- WIP e WIP Age
- Lead Time médio e P85
- Eficiência simples e ajustada
- `% Demanda de Falha` e `% Demanda de Valor`

## 5.2 Blocos Avançados

- Fluxo: cycle time, backlog time, bloqueios e esperas intermediárias.
- Estabilidade: desvio padrão, coeficiente de variação, percentis e IC.
- Saúde de fluxo: razão chegada/throughput, crescimento de WIP, itens vencidos.
- Qualidade: debt ratio e razão valor/custo.
- Tendências: médias móveis, direção e momentum.
- Throughput por tipo: segmentação semanal por categoria.
- Eficiência detalhada por item: breakdown de tempos.
- WIP por pessoa: visão semanal por responsável.

## 6) Dashboard Interativo (`dashboard_full.py`)

Abas principais:

1. Performance do Serviço
2. Dashboard
3. Fluxo
4. Estabilidade
5. Saúde Fluxo
6. Qualidade
7. Análise Dimensional
8. Análise Tipos
9. Tendências
10. Throughput por Tipo
11. Análise Eficiência
12. WIP por Pessoa
13. Estatística Descritiva

Características:

- Filtros globais por período/projeto/tipo/responsável.
- KPIs com detalhamento em gráficos.
- Tabelas interativas com ordenação e filtro.
- Linhas estatísticas (P15/P85/P95/média/MM5) em gráficos de tendência.

## 7) Operação e Execução

## 7.1 Gerar dados (pipeline)

Executar:

```bash
python dash_board_metricas.py
```

Resultado esperado:

- Arquivo consolidado: `dashboard_output_<timestamp>.xlsx`
- Modelo analítico: `PowerBI_Model_<timestamp>.xlsx`

## 7.2 Subir dashboard

Executar:

```bash
python dashboard_full.py
```

Comportamento:

- A aplicação seleciona automaticamente o `PowerBI_Model_*.xlsx` mais recente.
- Caso não exista arquivo de modelo, a aplicação interrompe com `FileNotFoundError`.

## 8) Dependências Técnicas

Principais bibliotecas:

- `pandas`
- `numpy`
- `dash`
- `plotly`
- `openpyxl` (preferencial) ou `xlsxwriter` (fallback para escrita Excel)

## 9) Decisões de Arquitetura Relevantes

- **Separação de responsabilidades**:
  - Pipeline de dados separado da camada de visualização.
- **Robustez de ingestão**:
  - Fallback automático para encoding/delimitador.
- **Modelo dimensional**:
  - Facilita Power BI e simplifica consumo no Dash.
- **Acoplamento temporal por arquivo mais recente**:
  - Dashboard depende do último `PowerBI_Model_*.xlsx`.

## 10) Limitações e Pontos de Atenção

- `dash_board_metricas.py` executa o processamento automaticamente ao ser importado (efeito colateral no fim do arquivo).
- Parte das métricas DORA na aba de performance está como placeholder (`—`).
- O sistema foi padronizado para semana ISO (segunda a domingo), com janelas `W-MON` e bucket semanal `W-SUN` para agrupamentos.
- A seleção do modelo mais recente depende de timestamp de criação de arquivo; em ambientes compartilhados, validar se o arquivo esperado é o correto.

## 11) Recomendações de Evolução

1. Adicionar um ponto de entrada explícito em `dash_board_metricas.py` com `if __name__ == '__main__':` para evitar execução em import.
2. Manter o padrão semanal ISO (segunda a domingo) como regra única em novos cálculos e visualizações.
3. Externalizar configurações (pastas, janela de datas, frequência) em arquivo `.env` ou `config.yaml`.
4. Incluir testes automáticos para regras de classificação e cálculo de métricas críticas.
5. Definir contrato de dados de entrada (campos obrigatórios/opcionais) com validação formal.
