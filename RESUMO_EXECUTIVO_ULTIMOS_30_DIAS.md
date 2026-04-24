# Resumo Executivo (Últimos 30 Dias)

## Janela analisada

- Período: **25/01/2026 a 24/02/2026**
- Base de evidência: `git log` + histórico detalhado em `tasks/todo.md`
- Observação: neste clone, o histórico disponível para a janela começa em **19/02/2026**

## Números-chave

- **51 commits** no período analisado
- **3 dias com maior concentração de entregas**
  - `19/02/2026`: 7 commits
  - `20/02/2026`: 22 commits
  - `23/02/2026`: 22 commits
- Principal foco técnico: **evolução do `dashboard_full.py`** (UI, métricas e robustez operacional)

## Entregas executivas (o que foi entregue)

- **Dashboard mais navegável e mais útil para operação**
  - Menu inicial separando `Portfólio` e `Serviços (Value Stream)`
  - Consolidação de abas em `Análise Fluxo` e `Saúde do Fluxo`
  - Nova aba dedicada de `CFD`
  - Nova visão/aba de `Lead Time`

- **Métricas de fluxo mais confiáveis**
  - Percentis empíricos exatos (sem interpolação)
  - Exclusão de itens cancelados das métricas de tempo de concluídos
  - Correções de semântica em KPIs de Lead Time/Cycle Time
  - Filtro de etapas de comprometimento para Lead Time (maior aderência ao conceito de negócio)

- **CFD mais completo (análise + leitura visual)**
  - Modo macro e detalhado por etapas
  - Painel sumário por ponto (hover/click)
  - Melhorias de visual (contraste, empilhamento, hover unificado)
  - Correções de escopo para respeitar filtros da tela

- **Pipeline Jira e qualidade dos dados fortalecidos**
  - Fluxo por projeto e por tipo (especialmente DT: melhoria vs bug/incidente/ad-hoc)
  - Ajuste de datas de etapa por última entrada (`latest`) para alinhar com referência operacional
  - Geração de aliases `latest` para artefatos downstream/gargalos
  - Consolidação de gargalos em workbook único (`bottlenecks_consolidado_*`)

- **Portfólio e produção mais robustos**
  - Leitura de CSV de portfólio por URL/arquivo via env
  - Fallbacks para CSV downstream detalhado por projeto
  - Cache em memória para leitura de portfólio
  - Melhor diagnóstico de erro de startup no deploy

## Impacto prático esperado

- **Menos retrabalho operacional** com arquivos `latest` e fallbacks de leitura
- **Maior confiança em indicadores de tempo** (percentis, cancelamentos, semântica de Lead Time)
- **Melhor leitura gerencial** com navegação simplificada e consolidação de abas
- **Diagnóstico de fluxo mais acionável** com CFD detalhado e filtros mais consistentes

## Riscos / atenção

- Histórico Git da janela está incompleto neste clone antes de `19/02/2026`
- `tasks/todo.md` é a principal trilha de detalhe técnico (aceite, validação e evidências)
- Parte da confiabilidade do dashboard ainda depende da qualidade/preenchimento dos campos Jira por projeto

## Próximos passos recomendados (executivo)

- Formalizar uma **baseline de KPIs** por projeto (Lead Time, Throughput, WIP, previsibilidade)
- Definir **rotina de publicação** (cadência + checklist) para produção
- Criar **testes automatizados** para regras críticas (percentis, elegibilidade, mapeamento de fluxo)
- Publicar esta síntese junto do índice central para facilitar comunicação com stakeholders
