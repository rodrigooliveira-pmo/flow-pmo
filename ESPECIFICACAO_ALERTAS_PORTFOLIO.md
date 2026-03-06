# Especificacao de Indicadores e Alertas de Portfolio

Atualizado em: 2026-03-06

## Objetivo

Definir, de forma implementavel, os indicadores e as regras de alerta prioritarias para a observabilidade do modulo de Portfolio no dashboard.

Escopo desta especificacao:

- integridade estrutural do portfolio
- estagnacao por falta de movimentacao
- risco de prazo por target date
- prontidao tecnica por vinculos obrigatorios

Fora do escopo imediato:

- custos planejados vs realizados
- qualquer indicador que dependa de metodo financeiro ainda nao definido

## Premissas

### Fonte primaria atual

O portfolio usa hoje o snapshot exportado por `jira_portfolio_to_csv.py`.

Campos confirmados no snapshot atual:

- `ID`
- `Titulo`
- `Projeto`
- `Team`
- `Prioridade`
- `EffortTShirtSize`
- `Tipo`
- `Status`
- `ParentID`
- `ParentTipo`
- `Link`
- `UpdatedAt`
- `StatusChangedAt`
- `DueDate`

### Derivacoes operacionais

- `UltimaMovimentacao = StatusChangedAt`, com fallback para `UpdatedAt`
- `DiasSemMovimentacao = hoje - UltimaMovimentacao`
- `TargetDate = DueDate`
- `ItemAberto = status diferente de concluido/finalizado/cancelado`

### Observacao importante

Os indicadores abaixo devem separar explicitamente:

- o que e calculado apenas com snapshot atual
- o que exige ampliacao do contrato de dados
- o que exige cruzamento portfolio x downstream

## Taxonomia de severidade

### Critico

Condicao com alto risco de descumprimento, omissao estrutural ou governanca quebrada.

### Alerta

Condicao que exige atuacao do time de gestao/portfolio no curto prazo.

### Monitorar

Condicao ainda aceitavel, mas que merece acompanhamento.

## Bloco 1 - Integridade Estrutural

Objetivo: identificar itens sem decomposicao, sem encadeamento pai-filho ou sem preparacao minima para execucao.

### Indicador 1.1 - Epicos sem feature

Pergunta respondida:

- quais epicos nao foram decompostos em features

Definicao:

- numerador: quantidade de epicos sem nenhuma feature vinculada
- denominador: total de epicos abertos no escopo

Regra de deteccao:

- `Tipo` do item = `Epic` ou `Epico`
- nao existe feature cujo `ParentID` seja o `ID` do epico

Visualizacoes:

- KPI total
- tabela detalhada
- ranking por `Projeto`
- ranking por `Team`

Severidade por item:

- `Critico`: epico aberto com `DiasSemMovimentacao > 20`
- `Alerta`: epico aberto com `DiasSemMovimentacao` entre `11` e `20`
- `Monitorar`: epico aberto com `DiasSemMovimentacao <= 10`

### Indicador 1.2 - Features sem story/task

Pergunta respondida:

- quais features nao foram decompostas em itens de fluxo

Definicao:

- numerador: quantidade de features sem filhos taticos
- denominador: total de features abertas no escopo

Regra de deteccao:

- `Tipo` do item = `Feature`
- nao existe item tatico cujo `ParentID` seja o `ID` da feature

Itens taticos considerados:

- `Story`
- `User Story`
- `Historia`
- `Task`
- `Tarefa`
- `Subtask` quando existir

Visualizacoes:

- KPI total
- tabela detalhada
- aging dos casos
- ranking por `Team`

Severidade por item:

- `Critico`: feature aberta com `DiasSemMovimentacao > 20`
- `Alerta`: feature aberta com `DiasSemMovimentacao` entre `11` e `20`
- `Monitorar`: feature aberta com `DiasSemMovimentacao <= 10`

### Indicador 1.3 - Stories/Tasks orfaos

Pergunta respondida:

- quais itens taticos nao possuem feature ou epic vinculados

Definicao:

- numerador: stories/tasks sem vinculo estrutural valido
- denominador: total de stories/tasks no escopo

Regra de deteccao:

- `Tipo` em conjunto tatico
- sem `ParentID` valido apontando para feature
- quando houver enriquecimento downstream, considerar tambem `FeatureLinkID` e `EpicLinkID`

Visualizacoes:

- KPI percentual
- tabela detalhada
- top teams com maior taxa de orfandade

Severidade por item:

- `Critico`: item em progresso sem vinculo tatico valido
- `Alerta`: item em backlog sem vinculo
- `Monitorar`: item concluido sem vinculo historico

## Bloco 2 - Estagnacao

Objetivo: sinalizar itens parados por tempo excessivo.

### Indicador 2.1 - Epicos sem movimentacao >10d, >20d, >30d

Pergunta respondida:

- quais epicos estao estagnados

Definicao:

- contar epicos abertos em tres buckets:
  - `>10 dias`
  - `>20 dias`
  - `>30 dias`

Regra de deteccao:

- `Tipo` = `Epic` ou `Epico`
- item aberto
- `DiasSemMovimentacao > threshold`

Visualizacoes:

- tres KPIs
- tabela unica com coluna `FaixaAlerta`
- distribuicao por `Projeto`, `Team`, `Quarter`

Severidade:

- `Critico`: `>30 dias`
- `Alerta`: `>20 dias`
- `Monitorar`: `>10 dias`

### Indicador 2.2 - Features sem movimentacao >10d, >20d, >30d

Mesmo desenho do indicador anterior, trocando o universo para `Feature`.

### Indicador 2.3 - Backlog parado proximo do vencimento

Pergunta respondida:

- quais itens estao simultaneamente sem evolucao e com risco de prazo

Definicao:

- itens abertos com `DiasSemMovimentacao > 10`
- e `TargetDate` dentro da janela de vencimento critica

Severidade:

- `Critico`: `DiasSemMovimentacao > 20` e `TargetDate <= hoje + 7 dias`
- `Alerta`: `DiasSemMovimentacao > 10` e `TargetDate <= hoje + 14 dias`
- `Monitorar`: `DiasSemMovimentacao > 10` e `TargetDate <= hoje + 30 dias`

## Bloco 3 - Risco de Prazo

Objetivo: dar visibilidade a itens de portfolio proximos ou alem do target date.

### Indicador 3.1 - Itens vencidos

Pergunta respondida:

- quais itens de portfolio ja estao alem do target date

Definicao:

- itens abertos com `DueDate < hoje`

Visualizacoes:

- KPI total
- ranking por `Projeto`
- ranking por `Team`
- tabela detalhada ordenada por dias de atraso

Severidade:

- `Critico`: vencido

### Indicador 3.2 - Itens vencendo em 7, 14 e 30 dias

Pergunta respondida:

- quais itens exigem acao antes de vencer

Definicao:

- itens abertos com `DueDate` preenchido
- buckets:
  - `vence em 0-7 dias`
  - `vence em 8-14 dias`
  - `vence em 15-30 dias`

Severidade:

- `Critico`: `0-7 dias`
- `Alerta`: `8-14 dias`
- `Monitorar`: `15-30 dias`

### Indicador 3.3 - Itens proximos do vencimento sem decomposicao

Pergunta respondida:

- quais itens correm risco de prazo sem preparacao estrutural minima

Regra de deteccao:

- epico vencido ou vencendo em ate `14 dias` sem feature
- feature vencida ou vencendo em ate `14 dias` sem story/task

Severidade:

- `Critico`: vencido ou vence em `<=7 dias`
- `Alerta`: vence em `8-14 dias`

## Bloco 4 - Prontidao Tecnica

Objetivo: alertar quando um epico nao possui trilha tecnica obrigatoria criada e concluida.

## Status de implementacao esperado

Este bloco deve ser dividido em duas fases.

### Fase 4A - Alerta proxy com o que existir hoje

Implementar somente se houver no dataset algum sinal confiavel por:

- label
- componente
- tipo
- titulo padronizado
- issue link

Pergunta respondida:

- quais epicos nao possuem nenhuma evidencia de item tecnico associado

Indicadores:

- epicos sem item de arquitetura
- epicos sem item de infra
- epicos sem item de seguranca

Severidade:

- `Critico`: epico em execucao sem ao menos um item tecnico obrigatorio
- `Alerta`: epico em planejamento proximo da execucao sem item tecnico

### Fase 4B - Alerta factual com cruzamento portfolio x downstream

Pergunta respondida:

- quais epicos nao possuem item tecnico criado
- quais possuem item tecnico criado mas nao finalizado
- quais possuem todos os itens obrigatorios finalizados

Contrato minimo necessario:

- relacionamento explicito epico -> item tecnico
- classificacao do item tecnico em `arquitetura`, `infra`, `seguranca`
- status factual do item tecnico no fluxo downstream

Indicadores:

- `% epicos sem item tecnico de arquitetura`
- `% epicos sem item tecnico de infra`
- `% epicos sem item tecnico de seguranca`
- `% epicos com trilha tecnica incompleta`
- `% epicos com trilha tecnica concluida`

Regras de alerta por epico:

- `Critico`: nenhum item tecnico obrigatorio criado
- `Alerta`: item tecnico criado, mas pelo menos um obrigatorio ainda aberto
- `Monitorar`: todos criados, porem algum proximo do vencimento do epico

## Bloco 5 - Custos

Prioridade: deixar por ultimo.

Motivo:

- ainda nao existe metodo fechado
- ainda nao existe contrato de dados estavel
- ainda nao existem campos confiaveis no portfolio para calculo

Nao implementar nesta fase:

- epico sem custo
- custo estimado por epico
- custo realizado por epico
- variacao entre estimado e realizado

Quando entrar na fila, abrir uma especificacao separada de metodo financeiro.

## Regras comuns de escopo

Todas as visualizacoes acima devem respeitar:

- filtro de `Projeto`
- filtro de `Team`
- filtro de `Quarter`
- filtro de `Tipo`, quando fizer sentido

E devem ignorar silenciosamente filtros sem suporte apenas quando a semantica do dado for realmente inexistente; caso contrario, devem exibir aviso explicito.

## Estrutura sugerida na UI

### Aba ou secao: Alertas de Portfolio

Subsecoes:

- `Integridade Estrutural`
- `Estagnacao`
- `Prazo`
- `Prontidao Tecnica`

### Padrao visual

Para cada subsecao:

- KPIs de topo
- distribuicao por severidade
- tabela detalhada
- ranking por `Projeto` e `Team`

### Colunas minimas nas tabelas de alerta

- `Severidade`
- `Tipo`
- `Projeto`
- `Team`
- `ItemID`
- `Titulo`
- `Status`
- `DiasSemMovimentacao`
- `DueDate`
- `MotivoAlerta`
- `Link`

## Backlog tecnico derivado

### Fase 1 - Implementavel ja

- adicionar buckets `>10`, `>20`, `>30` para epicos e features parados
- adicionar alertas de vencimento por `DueDate`
- adicionar alertas combinados de prazo + falta de decomposicao
- consolidar tabelas de integridade estrutural em uma secao unica de alertas

### Fase 2 - Enriquecimento do exportador de portfolio

- exportar issue links tipados
- exportar classificadores tecnicos necessarios para arquitetura/infra/seguranca
- validar se existem campos Jira confiaveis para isso

### Fase 3 - Cruzamento portfolio x downstream

- mapear relacionamento epico -> itens tecnicos no fluxo
- verificar conclusao factual desses itens
- publicar indicador de prontidao tecnica concluida

### Fase 4 - Custos

- definir metodo
- definir fonte
- definir contrato de dados
- so depois implementar indicadores financeiros

## Decisoes registradas

- custo fica explicitamente fora da primeira fase
- primeiro entregar alertas acionaveis com o snapshot atual
- prontidao tecnica entra em duas etapas: proxy, depois factual
- severidade deve ser padronizada para evitar KPI sem criterio operacional
