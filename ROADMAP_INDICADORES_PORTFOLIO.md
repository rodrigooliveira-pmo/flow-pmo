# Roadmap de Indicadores de Portfólio

Atualizado em: 2026-02-24 14:48:56

## Objetivo

Documentar:

- indicadores de portfólio já implementados no `dashboard_full.py`
- matriz de implementação (valor de negócio, dados necessários, complexidade técnica)
- o que falta fazer (priorizado)
- lacunas de dados / evolução do exportador `jira_portfolio_to_csv.py`
- um roadmap pragmático de implantação

## Escopo atual do módulo de Portfólio

O módulo de Portfólio consome um snapshot CSV (`portfolio-bt-ns-YYYYMMDD-data.csv`) gerado por `jira_portfolio_to_csv.py` e renderiza a aba `Portfólio` no `dashboard_full.py`.

### Contrato de dados atual (CSV)

Colunas atuais:

- `ID`
- `Titulo`
- `Projeto`
- `Team`
- `EffortTShirtSize`
- `Tipo`
- `Status`
- `ParentID`
- `ParentTipo`
- `Link`
- `UpdatedAt`
- `StatusChangedAt`

### Implicação do modelo atual (snapshot)

O CSV atual é um **snapshot** (estado atual) e não um histórico temporal. Isso permite:

- aging
- qualidade de cadastro
- distribuição por status/tipo/team
- hierarquia/órfãos
- concentração

Mas não permite, sem ampliar o exportador:

- throughput por período
- lead time real
- CFD
- tempo por etapa histórico
- previsibilidade temporal

## O que já foi implementado (Portfólio)

### Base existente (antes das últimas melhorias)

- `Indicador 1 - Q Pendências por TEAM`
- `Indicador 2 - Aging WIP por TEAM`
- `Indicador 3 - Resumo Executivo`
- KPIs de topo:
  - total de épicos/features
  - épicos sem features
  - features sem épico
  - features sem filhos
  - sem movimento 15d/30d
- Visões auxiliares:
  - épicos/features por team e status
  - épicos/features por team e complexidade
  - totais por team
  - backlog detalhado de épicos/features
  - itens por etapa de fluxo por épico

### Implementado nesta frente de trabalho

#### Qualidade de vínculo / cadastro

- `Histórias/Tasks sem feature` (KPI + resumo executivo)
- `% com TEAM` (qualidade de cadastro; usando TEAM original)
- `% features com épico`
- `% features com effort`
- `% itens com status não mapeado`
- tabela de qualidade por TEAM (e cards de qualidade)

#### Effort

- distribuição de `Effort T-shirt Size` por TEAM (Features)
- distribuição por effort (contagem)
- coluna `Effort T-shirt` no backlog detalhado de features
- `Features sem effort por TEAM (% e contagem)`

#### Aging

- aging por buckets detalhados: `0-7`, `8-15`, `16-30`, `31-60`, `60+`, `Sem data`
- `Aging por tipo`
- `Aging por projeto`

#### Status / workflow

- ranking de status por TEAM (categorias mapeadas)
- `% backlog / em progresso / concluído / não mapeado`
- `Heatmap TEAM x StatusCategoria`

#### Concentração

- `Top épicos por volume (QtdItensFluxo)`
- `Top épicos por aging (abertos)`

## Matriz de Implementação (Indicadores Recomendados)

Escala:

- Valor de negócio: `Alto`, `Médio`, `Baixo`
- Complexidade técnica: `Baixa`, `Média`, `Alta`

### Implementáveis com o CSV atual (snapshot)

| Indicador | Valor de negócio | Dados necessários | Complexidade técnica | Status |
|---|---|---|---|---|
| Aging por tipo (Épico/Feature/etc.) | Alto | `Tipo`, `Status`, `UpdatedAt`/`StatusChangedAt` | Baixa | Implementado |
| Aging por projeto (BT/NS) | Alto | `Projeto`, `Status`, `UpdatedAt`/`StatusChangedAt` | Baixa | Implementado |
| % WIP no portfólio | Médio | `Status` (mapeamento backlog/em progresso/concluído) | Baixa | Pendente |
| % backlog parado (>X dias) | Alto | `Status`, `UpdatedAt`/`StatusChangedAt` | Baixa | Pendente |
| Features sem effort por TEAM (% e contagem) | Alto | `Tipo`, `Team`, `EffortTShirtSize` | Baixa | Implementado |
| Distribuição de effort por TEAM | Médio | `Tipo=Feature`, `Team`, `EffortTShirtSize` | Baixa | Implementado |
| Distribuição de effort x aging | Alto | `Tipo=Feature`, `EffortTShirtSize`, `UpdatedAt`/`StatusChangedAt`, `Status` | Média | Pendente |
| % sem movimentação 15/30 dias por effort | Alto | `EffortTShirtSize`, `UpdatedAt`/`StatusChangedAt`, `Status`, `Tipo` | Média | Pendente |
| Ranking de status por TEAM (% backlog/em progresso/concluído) | Alto | `Team`, `Status` | Baixa | Implementado |
| Heatmap TEAM x StatusCategoria | Alto | `Team`, `Status` | Baixa | Implementado |
| Distribuição de status original (Top N) | Médio | `Status` | Baixa | Pendente |
| % itens com status não mapeado | Alto | `Status` + dicionário de mapeamento | Baixa | Implementado |
| % com TEAM (qualidade de cadastro) | Alto | `Team` (original) | Baixa | Implementado |
| % features com épico | Alto | `Tipo`, `ParentID`, `ParentTipo`/validação por IDs | Baixa | Implementado |
| % features com filhos | Médio | `Tipo`, `ParentID` | Média | Pendente |
| % épicos com itens de fluxo | Alto | `Tipo`, `ParentID` | Média | Pendente |
| % itens órfãos (story/task sem feature) | Alto | `Tipo`, `ParentID`, IDs de features | Média | Implementado (como contagem; % pendente) |
| Concentração por team (% top 3/top 5) | Alto | `Team`, contagem de itens | Baixa | Pendente |
| Concentração por épico (% portfólio nos top 5 épicos) | Alto | `Tipo`, `ParentID`, hierarquia Épico-Feature-Itens | Média | Parcial (tops absolutos implementados) |
| Top épicos por volume (itens de fluxo) | Alto | `Tipo`, `ParentID`, status/hierarquia | Média | Implementado |
| Top épicos por aging | Alto | `Tipo=Épico`, `Status`, `UpdatedAt`/`StatusChangedAt` | Baixa | Implementado |
| Fila de decisão por aging (Triagem/Backlog/Business Review) | Alto | `Status`, `UpdatedAt`/`StatusChangedAt` | Média (depende da taxonomia) | Pendente |
| Status fora do workflow padrão | Alto | `Status` + lista oficial de status permitidos | Baixa | Pendente |
| Índice de balanceamento por tipo (mix atual vs alvo) | Alto | `Tipo` + mix alvo parametrizado | Média | Pendente |
| Mix por projeto / tipo / team | Médio | `Projeto`, `Tipo`, `Team` | Baixa | Parcial (há visões por dimensão; faltam indicadores/mix explícitos) |
| Data freshness por etapa (% sem update >X) | Alto | `Status`, `UpdatedAt`/`StatusChangedAt` | Baixa | Pendente |

### Recomendados, mas exigem ampliar o exportador (`jira_portfolio_to_csv.py`)

| Indicador | Valor de negócio | Dados necessários | Complexidade técnica | Status |
|---|---|---|---|---|
| Lead time de portfólio (Feature/Épico) | Alto | `CreatedAt`, `ResolvedAt` (ou conclusão), `Tipo` | Média | Bloqueado por dados |
| Throughput semanal/mensal de portfólio | Alto | `ResolvedAt` + snapshots históricos (ou eventos) | Média | Bloqueado por dados |
| Flow Predictability (planejado vs entregue) | Alto | baseline/planejado + entregas reais por período | Alta | Bloqueado por dados |
| CFD de portfólio | Alto | histórico de status por data (snapshots diários ou changelog) | Alta | Bloqueado por dados |
| Queue time por etapa de portfólio | Alto | changelog de transições/status | Alta | Bloqueado por dados |
| Tempo de decisão (entrada -> aprovado/rejeitado) | Alto | timestamps de etapas/gates de decisão | Alta | Bloqueado por dados |
| Taxa de repriorização | Alto | histórico de rank/priority e mudanças | Alta | Bloqueado por dados |
| % cancelados antes/depois de iniciar | Alto | `Status`, timestamps de transição, cancelamento | Média/Alta | Parcial (cancelados atuais visíveis; faltam timestamps de decisão/início) |
| % capacidade consumida por baixa prioridade | Alto | `Prioridade` + capacidade por team | Alta | Bloqueado por dados |
| Demanda vs capacidade por TEAM | Alto | volume demandado + capacidade nominal/real | Alta | Bloqueado por dados |
| Funding allocation por fluxo/tema | Alto | budget/funding (custom fields ou sistema financeiro) | Alta | Bloqueado por dados |
| Run/Grow/Transform mix | Alto | classificação de investimento por item | Média | Bloqueado por dados |
| % budget guardrails breach (SAFe) | Médio/Alto | guardrails + budget/funding + alocação | Alta | Bloqueado por dados |
| % itens com objetivo estratégico vinculado | Alto | campo de objetivo/tema estratégico | Média | Bloqueado por dados |
| % itens fora do foco estratégico ativo | Alto | objetivo/tema + catálogo de metas ativas | Média/Alta | Bloqueado por dados |
| Distribuição por tema estratégico | Alto | campo tema estratégico | Média | Bloqueado por dados |
| Top temas por volume/aging/risco | Alto | tema + aging/status + (risco opcional) | Média | Bloqueado por dados |
| % épicos com benefício esperado definido | Alto | campos de benefício esperado | Média | Bloqueado por dados |
| % épicos com owner de benefício | Alto | owner/sponsor + tipo épico | Baixa/Média | Bloqueado por dados |
| Baseline vs target de benefício (planejado vs realizado) | Alto | baseline, target, realizado, datas | Alta | Bloqueado por dados |
| Taxa de realização de benefícios (30/60/90d) | Alto | benefícios realizados + conclusão + janela temporal | Alta | Bloqueado por dados |
| % épicos com risco alto sem plano | Alto | risco, plano de mitigação | Média | Bloqueado por dados |
| Dependências críticas / vencidas | Alto | issue links/dependências + status/target | Alta | Bloqueado por dados |
| Aging de dependência | Alto | dependências + timestamps | Alta | Bloqueado por dados |
| % marcos no prazo / desvio de marcos | Alto | milestones/target dates + datas reais | Média/Alta | Bloqueado por dados |

## O que foi feito recentemente (mudanças no código)

### `dashboard_full.py` (aba Portfólio)

Foram adicionados cálculos e visualizações para:

- histórias/tasks sem feature
- qualidade de cadastro (global e por TEAM)
- distribuição de effort e cobertura de estimativa
- aging por buckets / tipo / projeto
- ranking de status e heatmap TEAM x status
- concentração de épicos (volume e aging)

### Estratégias de implementação adotadas

- Cálculo no `compute_portfolio_snapshot(...)` para manter a UI simples
- Reuso do filtro `TEAM` existente (aplicado nas novas tabelas e gráficos)
- Uso de `TEAM` herdado para escopo visual, mas `TEAM` original para métrica de qualidade de cadastro
- Categorização de status com fallback (`Não mapeado`) para governança de taxonomia

## O que falta fazer (prioridade prática)

### Próxima onda (sem mexer no exportador) - alta relação valor/esforço

1. `Fila de decisão por aging`
2. `Status fora do workflow padrão`
3. `Concentração por team (% top 3/top 5)` e `top épicos % do total`
4. `Distribuição de effort x aging`
5. `% sem movimentação 15/30 dias por effort`
6. `Índice de balanceamento por tipo (mix atual vs alvo)`
7. `% WIP no portfólio` e `% backlog parado`
8. `Data freshness por etapa`

### Próxima onda (exige ampliar exportador)

1. Adicionar `CreatedAt` e `ResolvedAt`
2. Definir estratégia de histórico:
   - snapshots diários
   - ou changelog de transições
3. Adicionar campos estratégicos:
   - tema/objetivo estratégico
   - prioridade
   - target date / milestone
   - risco
   - sponsor / owner
4. (Opcional) funding/capacidade vindo de fonte complementar

## Roadmap técnico sugerido

### Fase 1 - Consolidar observabilidade do snapshot (rápido)

Objetivo: fechar governança e aging com dados já disponíveis.

- [ ] Fila de decisão por aging
- [ ] Status fora do workflow padrão (lista oficial parametrizável)
- [ ] Concentração relativa (% top N)
- [ ] Effort x aging
- [ ] WIP/Backlog parado e data freshness

Critério de aceite:

- todos os indicadores respeitam filtro `TEAM`
- tabela + visual para cada indicador crítico
- dicionário de status mapeado/permitido centralizado

### Fase 2 - Evolução do contrato de dados de portfólio

Objetivo: habilitar métricas de fluxo temporal e previsibilidade.

- [ ] Exportar `CreatedAt`
- [ ] Exportar `ResolvedAt`
- [ ] Exportar `Priority`
- [ ] Exportar `DueDate` / target date (se existir)
- [ ] Exportar tema/objetivo estratégico (custom field)
- [ ] Exportar risco / owner / sponsor (se existirem)

Critério de aceite:

- CSV mantém retrocompatibilidade
- dashboard continua funcionando sem os novos campos (fallback)
- validação de cobertura dos novos campos documentada

### Fase 3 - Métricas avançadas (PMI / SAFe / Gartner)

Objetivo: suportar decisão executiva com valor e previsibilidade.

- [ ] Lead time de portfólio
- [ ] Throughput por período
- [ ] CFD
- [ ] Flow Predictability
- [ ] Alinhamento estratégico
- [ ] Benefícios (planejado vs realizado)
- [ ] Riscos e dependências

Critério de aceite:

- definição operacional de cada métrica documentada
- janela temporal e regras de cálculo explícitas
- visualizações orientadas a decisão (não só volume)

## Riscos / Observações relevantes

- O snapshot atual de BT/NS costuma ter predominância de `Épico` e `Feature`; `US/Story/Task` pode ser escasso.
- Métricas que dependem de histórico de transições devem ser evitadas no snapshot para não gerar falsa precisão.
- Taxonomia de `Status` precisa governança contínua; novos status podem degradar indicadores se não forem mapeados.
- Qualidade de `TEAM` influencia quase todos os cortes executivos; manter medição por `TEAM` original é essencial.

## Referências conceituais usadas no roadmap (alto nível)

- PMI (Portfolio Management / Benefits Realization)
- SAFe (Lean Portfolio Management / Measure and Grow / Flow)
- Gartner (portfolio dashboards, prioritização e reporting executivo; abstracts públicos)

## Próximo passo recomendado

Implementar o pacote de Fase 1 sem mudar o exportador:

1. `Fila de decisão por aging`
2. `Status fora do workflow padrão`
3. `Concentração relativa (% top N)`
4. `Effort x aging`

