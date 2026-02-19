# 📊 Guia de Importação do Modelo Power BI

## 📁 Arquivos Gerados

### 1. **PowerBI_Model_20260211_135700.xlsx** ⭐ USAR ESTE ARQUIVO
Este é o arquivo otimizado para importação no Power BI com tabelas relacionadas (Fato + Dimensões).

**Estrutura:**
- **Dim_Projeto** - Lista de projetos (ProjetoID, NomeProjeto)
- **Dim_Data** - Dimensão temporal (DataID, Data, Ano, Mes, MesNome, Semana, DiaSemana, AnoMes)
- **Dim_Tipo** - Tipos de trabalho (TipoID, Tipo)
- **Dim_Responsavel** - Membros do time (ResponsavelID, Responsavel)
- **Dim_Componente** - Componentes técnicos (ComponenteID, Componente)
- **Dim_Prioridade** - Níveis de prioridade (PrioridadeID, Prioridade)
- **Fato_Items** - Tabela de fatos com todos os work items e métricas

### 2. **dashboard_output_20260211_135652.xlsx** - Análises Já Prontas
Este arquivo contém 8 abas com análises já calculadas (pode ser usado como complemento).

---

## 🚀 Como Importar no Power BI

### Passo 1: Abrir Power BI Desktop
1. Abra o **Power BI Desktop**
2. Clique em **"Obter Dados"** (Get Data)
3. Selecione **"Excel"**
4. Navegue até: `C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\`
5. Selecione **PowerBI_Model_20260211_135700.xlsx**

### Passo 2: Carregar as Tabelas
Na janela do Navigator:
- ✓ Dim_Projeto
- ✓ Dim_Data
- ✓ Dim_Tipo
- ✓ Dim_Responsavel
- ✓ Dim_Componente
- ✓ Dim_Prioridade
- ✓ Fato_Items

Clique em **Load** (ou Transform data para fazer ajustes)

### Passo 3: Criar Relacionamentos
No Power BI, vá para **Model** view:

**Relacionamentos a criar:**
```
Fato_Items[ProjetoID] ──→ Dim_Projeto[ProjetoID]
Fato_Items[TipoID] ──→ Dim_Tipo[TipoID]
Fato_Items[ResponsavelID] ──→ Dim_Responsavel[ResponsavelID]
Fato_Items[ComponenteID] ──→ Dim_Componente[ComponenteID]
Fato_Items[PrioridadeID] ──→ Dim_Prioridade[PrioridadeID]
Fato_Items[DataDone] ──→ Dim_Data[Data] (para análises por data de conclusão)
```

---

## 📊 Painéis Recomendados (Passo a Passo)

> **Total de 7 Painéis (Páginas):**
> 1. **Pulse Executivo** - KPIs executivos principais
> 2. **Saúde do Fluxo** - Monitoramento operacional  
> 3. **Previsibilidade** - Análise estatística e percentis
> 4. **Performance por Dimensão** - Rankings e comparativos
> 5. **Qualidade** - Análise de Debt Ratio e Defeitos
> 6. **WIP por Pessoa** ✨ **NOVO** - Capacidade por responsável
> 7. **Tendências** - Histórico e forecasting

### **PAINEL 1: Pulse Executivo**
**Página 1 - KPIs Principais**

**Cards (4 colunas):**
```
1. Throughput Total
   Medida: COUNT(Fato_Items[ItemID]) WHERE Fato_Items[Concluido] = 1
   
2. Lead Time Médio (dias)
   Medida: AVERAGE(Fato_Items[LeadTime_Dias])
   
3. Taxa de Conclusão (%)
   Medida: (COUNT Concluidos / COUNT Total) * 100
   
4. Debt Ratio (%)
   Medida: (COUNT Defeitos / COUNT Total) * 100
```

**Visualizações:**
```
- Gráfico de Linha: Throughput por semana (do Dim_Data)
  X: Dim_Data[Semana]
  Y: COUNTA(Fato_Items[ItemID]) BY Dim_Projeto[NomeProjeto]
  
- Pie Chart: Distribuição por Tipo
  Legend: Dim_Tipo[Tipo]
  Values: COUNTA(Fato_Items[ItemID])
  
- Table/Ranking: Top 5 Responsáveis por Throughput
  Dim_Responsavel[Responsavel]
  COUNTA(Fato_Items WHERE Concluido=1)
```

---

### **PAINEL 2: Saúde do Fluxo**
**Página 2 - Monitoring Operacional**

**Visualizações:**
```
- Sankey/Waterfall: Fluxo (Backlog → In Progress → Done)
  FROM: Dim_Projeto[NomeProjeto]
  TO: Dim_Tipo[Tipo]
  VALUE: COUNT(Fato_Items)
  
- Gauge/Meter: WIP vs Meta
  Value: SUM(Fato_Items[WIP_count])
  Target: 50 (exemplo)
  
- Bar Chart: Itens Bloqueados por Projeto
  X: Dim_Projeto[NomeProjeto]
  Y: COUNTA(Fato_Items WHERE Bloqueado=1)
  
- Histogram: Distribuição de Lead Time
  Bin: LeadTime_Dias (binning: 5 days)
  Y: COUNTA(Fato_Items)
```

---

### **PAINEL 3: Previsibilidade**
**Página 3 - Predictability & Variance**

**Visualizações:**
```
- Scatter Plot: Cycle Time vs Lead Time
  X: Fato_Items[TempoExecucao_Dias]
  Y: Fato_Items[LeadTime_Dias]
  Legend: Dim_Tipo[Tipo]
  Size: StoryPoints
  
- Box Plot / Distribution: Lead Time por Projeto
  (Mostrar P25, P50, P75, P95)
  
- Trend Line: Coeficiente de Variação ao longo do tempo
  X: Dim_Data[Semana/AnoMes]
  Y: Medida calculada de CV
  
- Table: Percentis de Lead Time
  P50, P75, P85, P95
  POR: Dim_Tipo, Dim_Projeto, Dim_Responsavel
```

---

### **PAINEL 4: Performance por Dimensão**
**Página 4 - Dimensional Analysis**

**Visualizações:**
```
- Horizontal Bar Chart: Throughput por Responsável
  X: COUNTA(Fato_Items WHERE Concluido=1)
  Y: Dim_Responsavel[Responsavel]
  Sort: Descending
  
- Matrix/Table: Throughput x Defect Rate
  Rows: Dim_Componente[Componente]
  Columns: Dim_Projeto[NomeProjeto]
  Values: COUNT(Items), % Defects
  
- Heatmap: Defect Density
  X: Dim_Componente
  Y: Dim_Projeto
  Color intensity: Taxa de Defeitos
  
- Multi-row Card: KPIs por Responsável
  Selecionável com filtro
```

---

### **PAINEL 6: WIP por Pessoa** ✨ NOVO
**Página 6 - Work In Progress por Responsável**

**Objetivo:** Monitorar carga de trabalho (WIP) por pessoa e analisar capacidade de cada membro do time.

**Visualizações:**
```
1. Horizontal Bar Chart: Ranking de WIP por Responsável
   X: [WIP Pessoa]
   Y: Dim_Responsavel[Responsavel]
   Ordenação: Decrescente (maiores WIP no topo)
   
2. Horizontal Bar Chart: Utilização da Capacidade (%)
   X: [Utilizacao Pessoa (%)]
   Y: Dim_Responsavel[Responsavel]
   Cores: Verde (<60%), Laranja (60-80%), Vermelho (>80%)
   
3. Table/Matriz: Detalhamento de WIP
   Colunas:
   - Dim_Responsavel[Responsavel] |  Responsável
   - [WIP Pessoa] | Items em WIP
   - [WIP Media Pessoa] | Dias Médio
   - [WIP Maximo Pessoa] | Dias Máximo
   - [Throughput Pessoa] | Items Completados
   - [Ratio Throughput WIP Pessoa] | Ratio T/WIP
   
4. Scatter Plot: WIP vs Throughput (Análise de Eficiência)
   X: [WIP Pessoa] (carga)
   Y: [Throughput Pessoa] (produtividade)
   Series: Dim_Projeto[NomeProjeto]
   Insight: Pessoas no canto direito superior têm alta carga E alta produção (ideal)
   
5. Card: Headroom (Capacidade Disponível)
   Medida: [Headroom Pessoa]
   Descrição: "Capacidade média disponível (meta max 10 items/pessoa)"
   
6. Line Chart: Trend de WIP por Responsável (últimas 4 semanas)
   X: Dim_Data[Semana]
   Y: [WIP Pessoa]
   Series: Dim_Responsavel[Responsavel]
   Insight: Identificar tendências de crescimento ou redução de WIP
```

**Métricas Chave:**
```
- WIP Pessoa: Número de items em progresso por responsável
- Utlização (%): Percentual de capacidade usada (WIP / 10)
- Headroom: Capacidade disponível para novos items
- Ratio T/WIP: Throughput divido por WIP (quanto maior, melhor)
- Status WIP: Codificado em cores
  🟢 Saudável (<60% utilização)
  🟡 Aviso (60-80% utilização)
  🔴 Crítico (>80% utilização)
```

**Filtros Aplicáveis:**
- Projeto (para ver WIP por pessoa em cada projeto)
- Período (semana/mês para análise temporal)
- Responsável (drill-down em uma pessoa específica)

---

### **PAINEL 7: Tendências**
**Página 7 - Histórico e Forecasting**

**Visualizações:**
```
- Combo Chart: Throughput com Trend (4 semanas)
  Coluna: Throughput semanal
  Linha: Média móvel de 4 semanas
  X: Dim_Data[Semana]
  
- Area Chart: WIP e Lead Time Trend
  Series 1: WIP Count
  Series 2: Lead Time Médio
  X: Dim_Data[Semana]
  
- Trend Analysis: Crescimento/Redução de WIP
  Comparação: Esta semana vs Semana passada
```

## 📐 Medidas DAX Importantes

Adicione essas medidas ao seu modelo Power BI:

```dax
-- Métricas Básicas
TotalItems = COUNTA(Fato_Items[ItemID])

ItemsConcluidos = CALCULATE([TotalItems], Fato_Items[Concluido] = 1)

TaxaConclusao = DIVIDE([ItemsConcluidos], [TotalItems]) * 100

-- Lead Time Percentis
LeadTime_P50 = PERCENTILE.INC(Fato_Items[LeadTime_Dias], 0.5)
LeadTime_P75 = PERCENTILE.INC(Fato_Items[LeadTime_Dias], 0.75)
LeadTime_P85 = PERCENTILE.INC(Fato_Items[LeadTime_Dias], 0.85)
LeadTime_P95 = PERCENTILE.INC(Fato_Items[LeadTime_Dias], 0.95)

-- Defeitos
ItemsDefeitos = CALCULATE([TotalItems], Dim_Tipo[Tipo] = "Defeitos")

DebtRatio = DIVIDE([ItemsDefeitos], [ItemsConcluidos]) * 100

-- Throughput
Throughput = [ItemsConcluidos]

RazaoValorCusto = CALCULATE([TotalItems], Dim_Tipo[Tipo] = "Desenvolvimento") 
                  / CALCULATE([TotalItems], Dim_Tipo[Tipo] = "Defeitos")

-- Bloqueados
ItemsBloqueados = CALCULATE([TotalItems], Fato_Items[Bloqueado] = 1)

TaxaBloqueio = DIVIDE([ItemsBloqueados], [TotalItems]) * 100

-- ✨ NOVO: WIP por Pessoa
WIPPessoa = CALCULATE([TotalItems], Fato_Items[EmWIP] = 1)

WIPMediaPessoa = AVERAGEX(FILTER(Fato_Items, Fato_Items[EmWIP] = 1), Fato_Items[WIP_Dias])

WIPMaximoPessoa = MAXX(FILTER(Fato_Items, Fato_Items[EmWIP] = 1), Fato_Items[WIP_Dias])

ThroughputPessoa = CALCULATE([ItemsConcluidos], SELECTEDVALUE(Dim_Responsavel[ResponsavelID]))

UtilizacaoPessoa = DIVIDE([WIPPessoa], 10) * 100

HeadroomPessoa = MAX(0, 10 - [WIPPessoa])

RatioThroughputWIP = DIVIDE([ThroughputPessoa], [WIPPessoa])

-- ✨ NOVO: Métricas de Tendência e Chegada
Taxa Chegada = 
CALCULATE(
    [TotalItems],
    USERELATIONSHIP(Fato_Items[DataBacklog], Dim_Data[Data])
)

Crescimento WIP (%) = 
VAR CurrentWIP = [WIP Count]
VAR PreviousWIP = 
    CALCULATE(
        [WIP Count],
        DATEADD(Dim_Data[Data], -7, DAY)
    )
RETURN
    DIVIDE(CurrentWIP - PreviousWIP, PreviousWIP)

-- Nota: Medidas de Momentum e Direção de Tendência são mais complexas
-- e podem exigir variáveis para comparar múltiplos períodos.
-- Veja o arquivo MEDIDAS_DAX.txt para exemplos.
```

---

## 🎯 Filtros Recomendados

Adicione slicers em sus páginas:

1. **Projeto** - Filtrar por Dim_Projeto[NomeProjeto]
2. **Tipo de Trabalho** - Filtrar por Dim_Tipo[Tipo]
3. **Responsável** - Filtrar por Dim_Responsavel[Responsavel]
4. **Período de Data** - Filtrar por Dim_Data[Data] (range)
5. **Prioridade** - Filtrar por Dim_Prioridade[Prioridade]

---

## 🔄 Atualização de Dados

Para atualizar com dados novos:

1. Execute novamente o script Python: `dash_board_metricas.py`
2. Isso gerará um novo arquivo `PowerBI_Model_YYYYMMDD_HHMMSS.xlsx`
3. No Power BI → **Home → Refresh** (Se usar Direct Query)
   Ou **Edit Queries → Source → Browse** para apontar pro novo arquivo

---

## ⚠️ Dicas Importantes

1. **Performance:** Se Fato_Items ficar muito grande (>100k linhas):
   - Adicione agregações no Power BI
   - Use DirectQuery ao invés de Import (se tiver SQL Server)

2. **StoryPoints:** Se a coluna StoryPoints estiver vazia, você pode calcular Lead Time ponderado:
   ```dax
   LeadTimeAdjustadoSP = 
   SUMPRODUCT(Fato_Items[LeadTime_Dias], Fato_Items[StoryPoints]) 
   / SUM(Fato_Items[StoryPoints])
   ```

3. **Drill-Down:** Crie hierarquias para análises profundas:
   - Ano → Mês → Semana → Dia
   - Projeto → Componente → Tipo

4. **Compartilhamento:** 
   - Salve o arquivo `.pbix` no Power BI Service
   - Compartilhe com stakeholders
   - Configure refresh automático (opcional)

---

## 📞 Suporte Rápido

**Problema:** Dados não aparecem
- Solução: Verifique os relacionamentos em Model view

**Problema:** Medidas não funcionam
- Solução: Certifique-se que Fato_Items está selecionada ao criar medida DAX

**Problema:** Performance lenta
- Solução: Reduza o período de data ou agregue por semana/mês

---

## 📊 NOVO PAINEL: Eficiência de Fluxo (Análise Profunda) ✨

**Objetivo:** Diagnosticar onde o tempo está sendo gasto (execução vs bloqueio vs espera).

**Visualizações Recomendadas:**

1. **KPI Cards (4 colunas):**
   - Eficiência Simples Média
   - Eficiência Ajustada Média ← Compare a diferença!
   - Tempo Bloqueio Médio (dias)
   - Tempo Espera Intermediária Médio (dias)

2. **Stacked Bar Chart: Breakdown do Lead Time**
   - Tempo em Backlog
   - Tempo em Execução ✓ (ideal)
   - Tempo em Bloqueio ⚠️
   - Tempo em Espera Intermediária ⚠️
   - Outros Tempos

3. **Scatter Plot: Eficiência Simples vs Ajustada**
   - X: Eficiência Simples
   - Y: Eficiência Ajustada
   - Series: Projeto
   - **Insight:** Se acima da diagonal = bloqueios impactam; Se abaixo = problema no team

4. **Table: Items Mais Afetados por Bloqueios**
   - ID | Título | Blocked Days | Eficiência

5. **Bar Chart: Impacto de Filas por Tipo**
   - Qual tipo fica mais tempo esperando?

---

## 💡 Entendendo Eficiência Simples vs Ajustada

**Eficiência Simples = Execution / Lead Time**
- Inclui tudo (bloqueios, filas, tudo)
- Useful para visão geral

**Eficiência Ajustada = Execution / (Lead Time - Bloqueios - Filas)**
- Remove tempo que não é responsabilidade do team
- Mais justo para avaliar performance

**Exemplo:**
```
Item com 20 dias, bloqueado 10 dias por infra:
- Simples: 5/20 = 25% (parece ruim)
- Ajustada: 5/10 = 50% (team executou bem, problema foi externo)
```

---

## 🎓 Próximas Funcionalidades Opcionais

1. **Forecast:** Adicionar linha de tendência com previsão (R ou Python)
2. **Alertas:** Configura alertas quando Debt Ratio > 40% ou WIP > 80%
3. **Benchmarking:** Compare seus 4 projetos com industry standards
4. **Mobile Layout:** Criar versão mobile-friendly dos dashboards
5. **Deep Dive:** Dashboard específico para rastrear bloqueios por responsável

---

## 📚 Documentação Relacionada

- **INDICADORES_EFICIENCIA_DETALHADO.md** - Guia completo sobre a nova métrica
- **MEDIDAS_DAX.txt** - Todas as 60+ medidas prontas para copiar

---

**Gerado em:** 2026-02-11  
**Atualizado em:** 2026-02-12 (Com Eficiência Ajustada)  
**Versão do Modelo:** 2.0 (Com análise profunda de bloqueios)  
**Total de Painéis:** 8  
**Total de Medidas DAX:** 65+  
**Próxima Atualização:** Automática (execute script 1x/semana)
