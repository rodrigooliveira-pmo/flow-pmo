# 📊 Indicadores de Eficiência de Fluxo - Documentação Completa

**Data de Atualização:** 12 de fevereiro de 2026  
**Versão:** 2.0 - Com Eficiência Ajustada  
**Status:** ✅ IMPLEMENTADO

---

## 🎯 Introdução

Este documento descreve em detalhes o novo indicador de **Eficiência de Fluxo Ajustada** e como ele aprimora a análise de produtividade do time, considerando tempos de bloqueio e espera intermediária.

---

## 📈 INDICADORES PRINCIPAIS DE FLUXO

### 1️⃣ **Throughput (Taxa de Entrega)**

**Definição:**
Número total de itens completados em um período (semana/mês/sprint).

**Fórmula:**
$$\text{Throughput} = \text{COUNT(Items WHERE Done ≠ NULL)}$$

**Unidade:** Items/Semana ou Items/Mês

**Meta:** ≥ 15 items/semana (ajustar conforme baseline do projeto)

**Interpretação:**
- ↑ Crescimento = Mais produtividade
- ↓ Queda = Preocupação (investigar causas)
- Variância alta = Falta de previsibilidade

**Exemplo:**
```
Semana 1: 12 items
Semana 2: 18 items
Semana 3: 14 items
Semana 4: 16 items
Throughput Médio = 15 items/semana
```

---

### 2️⃣ **Lead Time (Tempo Total)**

**Definição:**
Tempo total desde a criação/comprometimento até a conclusão de um item.

**Fórmula:**
$$\text{Lead Time} = \text{(Done - Sprint Backlog)} \text{ em dias}$$

**Componentes de Lead Time:**
```
Lead Time Total
    = Tempo em Backlog 
    + Tempo em Execução (Cycle Time)
    + Tempo em Bloqueio
    + Tempo em Espera Intermediária
    + Outros Tempos Não Contabilizados
```

**Unidade:** Dias

**Meta:** Média < 15 dias, P85 < 21 dias

**Interpretação:**
- Quanto menor, melhor (mais rápido)
- Lead Time alto = Há gargalos (investigar componentes)
- Variância alta = Falta de previsibilidade

---

### 3️⃣ **Cycle Time (Tempo de Execução)**

**Definição:**
Tempo que o item permanece "In Progress" (durante a execução real).

**Fórmula:**
$$\text{Cycle Time} = \text{(Done - In Progress)} \text{ em dias}$$

**Unidade:** Dias

**Meta:** Média < 7 dias

**Interpretação:**
- Diferença entre Cycle Time e Lead Time = tempo de espera anterior
- Um item com Lead Time 15 dias e Cycle Time 3 dias teve 12 dias de espera

**Fórmula Relativa:**
$$\text{Tempo de Espera Anterior} = \text{Lead Time - Cycle Time}$$

---

### 4️⃣ **Eficiência de Fluxo Simples** ⭐ TRADICIONAL

**Definição:**
Razão entre o tempo realmente gasto em execução e o tempo total da jornada.

**Fórmula:**
$$\text{Eficiência Simples} = \frac{\text{Cycle Time}}{\text{Lead Time}}$$

**Intervalo:** 0 a 1 (ou 0% a 100%)

**Meta:** ≥ 0.7 (70% ou mais do tempo em execução)

**Interpretação:**
- 0.8 = 80% do tempo em execução, 20% em espera
- 0.4 = 40% em execução, 60% em espera (gargaloado)
- 1.0 = Teórico perfeito (sem espera)

**Exemplo:**
```
Item A:
  Lead Time = 10 dias
  Cycle Time = 7 dias
  Eficiência Simples = 7/10 = 0.70 (70%) ✓ Bom

Item B:
  Lead Time = 14 dias
  Cycle Time = 3 dias
  Eficiência Simples = 3/14 = 0.21 (21%) ✗ Problema
```

**Limitação:**
Não distingue entre:
- Tempo em espera "normal" (antes de iniciar)
- Tempo em bloqueio (parado por dependência)
- Tempo em espera intermediária (fila em estágios "Ready to...")

---

### 5️⃣ **Eficiência de Fluxo Ajustada** ⭐ NOVO

**Definição:**
Razão entre tempo de execução e o tempo "produtivo disponível", desconsiderando tempos que não são culpa do time (bloqueios e filas intermediárias).

**Fórmula:**
$$\text{Eficiência Ajustada} = \frac{\text{Cycle Time}}{\text{Lead Time - Tempo Bloqueio - Tempo Espera Intermediária}}$$

**Componentes:**

**a) Tempo de Bloqueio**
- Origem: Campo `Blocked Days` do rastreamento
- Representa: Item parado por dependência externa (aguardando outro time, cliente, infra)
- Não é responsabilidade direta do time executante

**b) Tempo em Espera Intermediária**
- Origem: Colunas como `Ready to...`, `Staging`, `Waiting`, `Pending`, `Queue`
- Representa: Item em fila entre estágios conhecidos
- Exemplo: "Ready to QA" → "In QA" = dias em fila

**c) Intervalo de Confiança**
- O denominador é sempre ≥ 1 (protegido contra divisão por zero)
- Valores são clamped entre 0.0 e 2.0

**Unidade:** 0 a 2.0 (ou 0% a 200%)

**Meta:** ≥ 0.7 (70%)

**Interpretação:**
- 0.8 = 80% da janela "produtiva" foi gasta em execução
- Valor > 1.0 = Mais tempo em execução que a janela disponível (anomalia - investigar)
- Valor < 0.5 = Há muito tempo perdido dentro da janela produtiva

**Exemplo Comparativo:**
```
Item C - Bloqueado por dependência:
  Lead Time = 20 dias
  Cycle Time = 5 dias
  Blocked Days = 10 dias
  Wait Stages = 0 dias
  
  Eficiência Simples = 5/20 = 0.25 (25%) ✗
  Eficiência Ajustada = 5/(20-10-0) = 5/10 = 0.50 (50%) ⚠️
  
  Interpretação: O time teve 10 dias úteis e usou 5 (50%).
  Os 10 dias de bloqueio não são responsabilidade do time.

Item D - Em fila intermediária:
  Lead Time = 18 dias
  Cycle Time = 4 dias
  Blocked Days = 0 dias
  Wait Stages = 8 dias (esperando em "Ready to Test")
  
  Eficiência Simples = 4/18 = 0.22 (22%) ✗
  Eficiência Ajustada = 4/(18-0-8) = 4/10 = 0.40 (40%) ⚠️
  
  Interpretação: O time teve 10 dias produtivos, usou 4 (40%).
  Os 8 dias em fila são gargalo de processo (revisar fluxo).
```

---

## 📊 Breakdown de Lead Time

Para cada item completado, o sistema agora calcula:

```
┌─────────────────────────────────────────────────────────────┐
│                    LEAD TIME TOTAL (Σ)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Tempo em Backlog                                        │
│     (Sprint Backlog → In Progress)                           │
│     = Dias aguardando para iniciar                           │
│     Causa: Falta de capacidade, priorização                │
│                                                              │
│  2. Tempo em Execução (Cycle Time)                         │
│     (In Progress → Done)                                    │
│     = Dias de trabalho real ✓ TEM VALOR                     │
│                                                              │
│  3. Tempo em Bloqueio ⚠️                                     │
│     (Via campo Blocked Days)                                │
│     = Dias parado por dependência externa                   │
│     Causa: Outro time, cliente, infraestrutura             │
│     Responsabilidade: Externo                               │
│                                                              │
│  4. Tempo em Espera Intermediária ⚠️                        │
│     (Via colunas "Ready to...", "Staging", etc)             │
│     = Dias em fila entre estágios                           │
│     Causa: Gargalo de processo, filas                      │
│     Responsabilidade: Processo                              │
│                                                              │
│  5. Outros Tempos (Residual)                               │
│     = Tempos não contabilizados                             │
│     Causa: Transição entre estágios, overhead              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 COMO INTERPRETAR OS RESULTADOS

### Cenário 1: Eficiência Simples Baixa + Eficiência Ajustada Alta

```
Eficiência Simples = 0.30
Eficiência Ajustada = 0.75
Blocked Days = 12 dias
```

**Análise:**
- O item parecia ineficiente (30%)
- Mas 12 dos 20 dias foi bloqueio externo
- O team realmente executou bem quando tinha capacidade (75%)
- **Ação:** Investigar causa de bloqueios, não criticar time

### Cenário 2: Ambas Eficiências Baixas

```
Eficiência Simples = 0.25
Eficiência Ajustada = 0.30
Blocked Days = 2 dias
Wait Stages = 3 dias
```

**Análise:**
- Mesmo desconsiderando bloqueios e esperas, a eficiência é baixa
- O time não executou bem, há perda de tempo dentro da execução
- Pode ser: contexto switching, reuniões, rework, indecisão
- **Ação:** Revisar procedimentos de trabalho, reduzir interrupções

### Cenário 3: Ambas Eficiências Altas

```
Eficiência Simples = 0.85
Eficiência Ajustada = 0.88
Blocked Days = 0 dias
Wait Stages = 0 dias
```

**Análise:**
- Team está executando muito bem
- Fluxo desimpedido
- Mínimo de bloqueios e esperas
- **Ação:** Documentar boas práticas, escalar este padrão

---

## 📋 Exemplo Prático: 5 Items Reais

```
┌──────────┬──────────┬──────────┬──────────┬─────────┬──────────┬──────────────┐
│ Item ID  │Lead Time │Cycle T  │ Blocked D│ Wait St │Eff Simp │ Eff Ajustada │
├──────────┼──────────┼──────────┼──────────┼─────────┼──────────┼──────────────┤
│W1-001    │ 10 dias  │ 7 dias   │ 0 dias   │ 0 dias  │  70%     │    70%      │
│W1-002    │ 18 dias  │ 5 dias   │ 8 dias   │ 2 dias  │  28%     │    62%      │
│W1-003    │ 25 dias  │ 6 dias   │ 0 dias   │ 12 dias │  24%     │    54%      │
│W1-004    │ 12 dias  │ 4 dias   │ 5 dias   │ 0 dias  │  33%     │    80%      │
│W1-005    │ 8 dias   │ 6 dias   │ 0 dias   │ 0 dias  │  75%     │    75%      │
├──────────┼──────────┼──────────┼──────────┼─────────┼──────────┼──────────────┤
│ MÉDIA    │ 14.6 dias│ 5.6 dias │ 2.6 dias │2.8 dias │  46%     │    68%      │
└──────────┴──────────┴──────────┴──────────┴─────────┴──────────┴──────────────┘

Insights:
- W1-001: Excelente (ideal)
- W1-002: Bloqueado por dependência (8 dias) + fila (2 dias)
  → Investigar dependência e etapa "Ready to..."
- W1-003: Muito tempo em espera intermediária (12 dias)
  → Gargalo no processo de teste/review
- W1-004: Bem executado (80% ajustado) apesar do bloqueio
  → Bom time, problema externo
- W1-005: Perfeito (75% simples e ajustado)
  → Reference item
```

---

## 📊 NOVAS ABAS EM RELATÓRIO EXCEL

### Aba: **"Análise Eficiência"** (Novo)

Contém **análise item-por-item** com:

| Coluna | Descrição | Tipo |
|--------|-----------|------|
| Projeto | Qual projeto | Texto |
| ID | ID do item | Texto |
| Título | Assunto | Texto |
| Tipo | Desenvolvimento/Defeitos/Outro | Categ. |
| Lead Time (dias) | Total | Número |
| Tempo Backlog (dias) | Sprint Backlog → In Progress | Número |
| Tempo Execução (dias) | In Progress → Done (Cycle Time) | Número |
| Tempo Bloqueio (dias) | Blocked Days | Número |
| Tempo Espera Intermediária (dias) | Dias em "Ready to...", "Staging", etc | Número |
| Outros Tempos (dias) | Residual | Número |
| Eficiência Simples | Execution/LeadTime | % |
| Eficiência Ajustada | Execution/(LeadTime - Blocked - Wait) | % |
| Diferença Eficiência | Ganho com ajuste | % |
| Detalhes Espera | Quais estágios fizeram fila | Texto |

**Uso:**
- Identificar items com problemas
- Classificar por fonte de desperdício
- Trend analysis: Bloqueios crescendo? Filas aumentando?
- Comparação entre times/componentes

---

### Aba: **"Adv - Fluxo"** (Atualizada - Era "Adv - Fluxo", Agora Expandida)

Agora inclui:

| Métrica | Descrição |
|---------|-----------|
| Cycle Time Médio | Tempo de execução |
| Tempo Backlog Médio | Espera antes de iniciar |
| Eficiência Simples Média | Métrica tradicional |
| **Eficiência Ajustada** | **NOVA** |
| **Tempo Bloqueio Médio** | **NOVO** - Dias de bloqueio externo |
| **Tempo Espera Intermediária Médio** | **NOVO** - Dias em filas info |
| Taxa de Bloqueio (%) | % items que foram bloqueados |

---

### Aba: **"Dashboard"** (Atualizada)

Agora com coluna:
- `{Tipo} - Eficiência Ajustada` por semana
- Exemplo: `Desenvolvimento - Eficiência Ajustada`
- Acompanhamento semanal da métrica nova

---

## 📐 Medidas DAX (Usar no Power BI)

```dax
-- Eficiência Média (Simples)
Eficiencia Media = 
AVERAGEX(
    Fato_Items,
    Fato_Items[Eficiencia]
)

-- Eficiência Ajustada Média
Eficiencia Ajustada Media =
AVERAGEX(
    Fato_Items,
    DIVIDE(
        Fato_Items[TempoExecucao_Dias],
        MAX(1, Fato_Items[LeadTime_Dias] - 
            IFERROR(Fato_Items[TempoBlockeio_Dias], 0) - 
            IFERROR(Fato_Items[TempoEsperaIntermediaria_Dias], 0))
    )
)

-- Tempo de Bloqueio Médio (dias)
Tempo Bloqueio Medio = 
AVERAGEX(
    Fato_Items,
    IFERROR(Fato_Items[TempoBlockeio_Dias], 0)
)

-- Tempo Espera Intermediária Médio (dias)
Tempo Espera Intermedia Medio = 
AVERAGEX(
    Fato_Items,
    IFERROR(Fato_Items[TempoEsperaIntermediaria_Dias], 0)
)

-- Taxa de Itens Bloqueados (%)
Taxa Bloqueio (%) =
DIVIDE(
    CALCULATE(
        COUNTA(Fato_Items[ItemID]),
        Fato_Items[Bloqueado] = 1
    ),
    COUNTA(Fato_Items[ItemID])
) * 100
```

---

## 🎯 Quando Usar Cada Métrica

| Situação | Use Eficiência Simples | Use Eficiência Ajustada |
|----------|------------------------|------------------------|
| Análise geral do team | ✓ | ✓ |
| Blame/accountability | ✗ | ✓ |
| Investigar gargalos | ✓ | ✓ |
| Comparar times | ✓ | ✓ |
| Entender blockers | ✓ | ✓ |
| Alinhar expectativas | ✗ | ✓ |

---

## 💡 Próximas Análises Recomendadas

1. **Análise de Filas:** Quais estágios "Ready to..." têm maior acúmulo?
2. **Análise de Bloqueios:** Qual time causa mais bloqueios externos?
3. **Correlação:** Lead Time alto correlaciona melhor com que fonte (bloqueio vs fila)?
4. **Forecast:** Dado os padrões, quanto tempo esperar para delivery?
5. **Diagnóstico:** Para cada componente, qual é o gargalo principal?

---

## 📚 Documentação Relacionada

- `RESUMO_EXECUTIVO.md` - Visão geral da solução
- `ARQUITETURA_MODELO.md` - Estrutura de dados
- `INSTRUCOES_POWERBI.md` - Como criar painéis
- `MEDIDAS_DAX.txt` - Todas medidas DAX disponíveis
