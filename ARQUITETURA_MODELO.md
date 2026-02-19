# 📐 Arquitetura do Modelo de Dados Power BI

## DIAGRAMA DE RELACIONAMENTOS

```
┌─────────────────────────────────────────────────────────────────┐
│                         TABELAS DE DIMENSÃO                      │
└─────────────────────────────────────────────────────────────────┘

      ◇ DIM_PROJETO              ◇ DIM_TIPO                ◇ DIM_DATA
      ──────────────────         ──────────────────        ──────────────────
      ProjetoID [PK]            TipoID [PK]               DataID [PK]
      NomeProjeto               Tipo                      Data
                                                          Ano
      Exemplos:                 Exemplos:                 Mes
      - W1NNER                  - Desenvolvimento         MesNome
      - DATA&ANALYTICS          - Defeitos                 Semana
      - BEFINANCE               - Suporte                 DiaSemana
      - S1NC                    - Outro                   AnoMes


        ◇ DIM_RESPONSAVEL         ◇ DIM_COMPONENTE       ◇ DIM_PRIORIDADE
        ──────────────────────     ──────────────────     ──────────────────
        ResponsavelID [PK]         ComponenteID [PK]      PrioridadeID [PK]
        Responsavel                Componente             Prioridade

        Exemplos:                  Exemplos:              Exemplos:
        - João Silva               - Backend              - Crítico
        - Maria Santos             - Frontend             - Alto
        - Pedro Oliveira           - Database             - Normal
        - Ana Costa                - DevOps               - Baixo


┌─────────────────────────────────────────────────────────────────┐
│                    🔴 TABELA DE FATOS (CENTRAL)                  │
│                        FATO_ITEMS                                │
└─────────────────────────────────────────────────────────────────┘

    ItemID [PK]
    ├── Chaves Estrangeiras (FKs):
    │   ├── ProjetoID [FK] → Dim_Projeto[ProjetoID]
    │   ├── TipoID [FK] → Dim_Tipo[TipoID]
    │   ├── ResponsavelID [FK] → Dim_Responsavel[ResponsavelID]
    │   ├── ComponenteID [FK] → Dim_Componente[ComponenteID]
    │   └── PrioridadeID [FK] → Dim_Prioridade[PrioridadeID]
    │
    ├── Métricas de Tempo (dias):
    │   ├── TempoBacklog_Dias (Sprint Backlog → In Progress)
    │   ├── TempoExecucao_Dias (In Progress → Done) = Cycle Time
    │   ├── LeadTime_Dias (Sprint Backlog → Done)
    │   ├── WIP_Dias (Dias que item está em "In Progress")
    │   ├── TempoBlockeio_Dias ✨ NOVO - Tempo em Blocked Days
    │   └── TempoEsperaIntermediaria_Dias ✨ NOVO - Tempo em estágios "Ready to..."
    │
    ├── Indicadores:
    │   ├── Eficiencia (TempoExecucao / LeadTime) - TRADICIONAL
    │   ├── EficienciaAjustada ✨ NOVO (Execution / (LeadTime - Blocked - WaitStages))
    │   ├── Concluido (0/1)
    │   ├── Bloqueado (0/1)
    │   └── EmWIP (0/1)
    │
    ├── Atributos:
    │   ├── Titulo
    │   ├── ResponsavelNome
    │   ├── WorkItemSubType
    │   └── StoryPoints
    │
    └── Datas:
        ├── DataBacklog
        ├── DataInProgress
        └── DataDone


┌────────────────────────────────────────────────────────┐
│              RELACIONAMENTOS (Recomendados)            │
└────────────────────────────────────────────────────────┘

    Fato_Items[ProjetoID] ──M:1──→ Dim_Projeto[ProjetoID]
    (Ativo, One-way)
    
    Fato_Items[TipoID] ──M:1──→ Dim_Tipo[TipoID]
    (Ativo, One-way)
    
    Fato_Items[ResponsavelID] ──M:1──→ Dim_Responsavel[ResponsavelID]
    (Ativo, One-way)
    
    Fato_Items[ComponenteID] ──M:1──→ Dim_Componente[ComponenteID]
    (Ativo, One-way)
    
    Fato_Items[PrioridadeID] ──M:1──→ Dim_Prioridade[PrioridadeID]
    (Ativo, One-way)
    
    Fato_Items[DataDone] ──M:1──→ Dim_Data[Data]
    (Ativo, One-way | Opcional - para análise por data de conclusão)
```

---

## 📊 ESTRUTURA ANALÍTICA

### Modelo Dimensional (Star Schema)

```
                    Dim_Projeto
                         ▲
                         │
        Dim_Responsavel   │   Dim_Componente   Dim_Prioridade
                 ▲        │        ▲                 ▲
                 │        │        │                 │
                 └────────┼────────┴─────────────────┘
                          │
                      Fato_Items
                          │
                 ┌────────┴─────────┐
                 │                  │
            Dim_Tipo          Dim_Data
                 ▲                  ▲
                 │                  │
```

### Granularidade da Tabela de Fatos

**Um registro = Um Work Item**

- Total de registros: ~1-2k itens (conforme projeto)
- Histórico: Desde 2025-01-01 até hoje
- Atualização: Diária (reexecutar script 1x/dia ou 1x/semana)

---

## 🔄 FLUXO DE DADOS

```
1. Origem: CSV files (Jira/ADO exports)
   ↓
2. Processamento Python:
   - Limpeza e deduplicação
   - Parsing de datas
   - Cálculo de métricas
   - Cálculo de WIP_Dias e EmWIP ✨ NOVO
   ↓
3. Consolidação em Tabelas Dimensionais
   ↓
4. Exportação para Excel (PowerBI_Model_YYYYMMDD.xlsx)
   ├── Dim_Projeto
   ├── Dim_Data
   ├── Dim_Tipo
   ├── Dim_Responsavel
   ├── Dim_Componente
   ├── Dim_Prioridade
   └── Fato_Items (+ colunas EmWIP, WIP_Dias, ResponsavelNome)
   ↓
5. Importação no Power BI Desktop
   ↓
6. Criar Relacionamentos (relação M:1)
   ↓
7. Criar Medidas DAX (incluindo medidas de WIP por Pessoa)
   ↓
8. Construir Painéis Visuais (7 painéis totais, com novo painel "WIP por Pessoa")
```

---

## 📈 CASOS DE USO POR PAINEL

### 1️⃣ **Pulse Executivo**
```
Dimensões usadas: Projeto, Data (semana)
Métricas: Throughput, Lead Time, Taxa Conclusão, Debt Ratio
Filtros: Período, Projeto
Tipo: KPI Executive View
```

### 2️⃣ **Saúde do Fluxo**
```
Dimensões usadas: Projeto, Tipo, Data
Métricas: WIP, Items Bloqueados, Cycle Time, Tempo em Backlog
Filtros: Projeto, Status (Bloqueado/Normal)
Tipo: Operacional Monitoring
```

### 3️⃣ **Previsibilidade**
```
Dimensões usadas: Tipo, Responsável, Componente
Métricas: Lead Time (P50, P75, P85, P95), Coeficiente Variação, IC 95%
Filtros: Período, Tipo
Tipo: Statistical Analysis
```

### 4️⃣ **Performance por Dimensão**
```
Dimensões usadas: Responsável, Componente, Prioridade
Métricas: Throughput, Lead Time Médio, Taxa Defeitos
Filtros: Projeto, Período
Tipo: Dimensional Analysis
```

### 5️⃣ **Qualidade**
```
Dimensões usadas: Tipo (Defeitos/Desenvolvimento), Componente
Métricas: Debt Ratio, Razão Valor/Custo, Eficiência
Filtros: Período, Responsável
Tipo: Quality Dashboard
```

### 6️⃣ **WIP por Pessoa** ✨ NOVO
```
Dimensões usadas: Responsável, Projeto, Data (semanal)
Métricas: WIP Pessoa, WIP Média, WIP Máximo, Utilização, Headroom
Filtros: Projeto, Período, Responsável
Detalhes: 
  - Ranking de WIP por responsável
  - Análise de capacidade por pessoa (max 10 items/pessoa)
  - Histórico semanal de WIP trend
  - Comparativo Throughput vs WIP
  - Status de alerta (capacidade crítica)
Tipo: Capacity Planning por Pessoa
```

### 7️⃣ **Tendências**
```
Dimensões usadas: Data (semanal/mensal)
Métricas: Throughput trend, WIP trend, Lead Time trend
Filtros: Projeto, Tipo
Tipo: Time Series Analysis
```

### 8️⃣ **Capacidade**
```
Dimensões usadas: Projeto, Responsável
Métricas: WIP, Headroom, Utilização, Ratio Chegada/Throughput
Filtros: Data (current week)
Tipo: Capacity Planning
```

### 9️⃣ **Benchmarking**
```
Dimensões usadas: Projeto, Responsável
Métricas: Score (ranking), Performance Index
Filtros: Período
Tipo: Comparative Analysis
```

---

## 🔍 EXEMPLO DE FILTRO CRUZADO

Quando o usuário filtra por um **Projeto**:

```
Projeto = "W1NNER"
    ↓ (filtra)
Fato_Items (apenas items do W1NNER)
    ↓
   Dim_Tipo (apenas tipos usados no W1NNER)
   Dim_Responsavel (apenas pessoas que trabalham em W1NNER)
   Dim_Componente (apenas componentes do W1NNER)
   Dim_Prioridade (apenas prioridades usadas em W1NNER)
   Dim_Data (apenas datas com atividade em W1NNER)
```

---

## 🚦 PERFORMANCE & OTIMIZAÇÕES

### Índices Recomendados (se SQL Server)
```sql
CREATE INDEX idx_FatoItems_ProjetoID 
ON Fato_Items(ProjetoID)

CREATE INDEX idx_FatoItems_TipoID 
ON Fato_Items(TipoID)

CREATE INDEX idx_FatoItems_DataDone 
ON Fato_Items(DataDone)

CREATE INDEX idx_FatoItems_Concluido 
ON Fato_Items(Concluido)
```

### Tamanho Esperado (Excel)
```
Dim_Projeto:      ~4 KB (≈5 registros)
Dim_Data:         ~50 KB (≈400 datas)
Dim_Tipo:         ~3 KB (≈5 tipos)
Dim_Responsavel:  ~15 KB (≈50 pessoas)
Dim_Componente:   ~20 KB (≈60 componentes)
Dim_Prioridade:   ~3 KB (≈5 prioridades)
Fato_Items:       ~200-500 KB (≈1000-2000 itens)
─────────────────────────────────
TOTAL:            ~300-600 KB
```

### Recomendações
- ✓ Import mode adequado para estes tamanhos
- ✓ Aggregation Tables opcional (se > 100k itens)
- ✓ Particionamento por ano (se historical data cresce muito)

---

## 📋 CHECKLIST DE SETUP

- [ ] Importar todas as tabelas do Excel
- [ ] Verificar tipos de dados (datas como DATE, números como DECIMAL)
- [ ] Criar todos os 6 relacionamentos (1:M)
- [ ] Marcar Dim_Data como "Date Table" em Power BI
- [ ] Criar pasta "Medidas" para organizar DAX
- [ ] Importar as 60+ medidas fornecidas (incluindo medidas de WIP por Pessoa)
- [ ] Criar primeiro painel (Pulse Executivo)
- [ ] Criar novo painel "WIP por Pessoa"
- [ ] Testar filtros cruzados
- [ ] Publicar no Power BI Service
- [ ] Configurar refresh automático (daily)

---

## 🔗 RELAÇÕES PRINCIPAIS

| Tabela de Fatos | Campo | Tabela de Dimensão | Campo | Cardinalidade |
|-----------------|-------|-------------------|-------|---------------|
| Fato_Items | ProjetoID | Dim_Projeto | ProjetoID | M:1 |
| Fato_Items | TipoID | Dim_Tipo | TipoID | M:1 |
| Fato_Items | ResponsavelID | Dim_Responsavel | ResponsavelID | M:1 |
| Fato_Items | ComponenteID | Dim_Componente | ComponenteID | M:1 |
| Fato_Items | PrioridadeID | Dim_Prioridade | PrioridadeID | M:1 |
| Fato_Items | DataDone | Dim_Data | Data | M:1 |

---

**Diagrama gerado em:** 2026-02-11
**Compatibilidade:** Power BI Desktop 2.130 ou superior
