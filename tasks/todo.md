# Task Plan

## Current Task (Weibull shape/lambda na estatística descritiva)
- [x] Inspecionar referência da planilha `LT_STATS_WEIBULL.xlsx` e alinhar fórmula de ajuste Weibull
- [x] Implementar cálculo de `shape (k)` e `lambda` do Lead Time na aba `Estatística Descritiva`
- [x] Validar sintaxe/diff e registrar review/evidências

## Specification (Weibull shape/lambda na estatística descritiva)
- Objetivo: incluir na tabela de estatísticas de Lead Time da aba `Estatística Descritiva` os parâmetros da distribuição Weibull (`shape` e `lambda`) calculados pelo mesmo método da planilha de referência.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Cálculo usa transformação Weibull linearizada (ranking + regressão em escala log/log), compatível com a planilha `LT_STATS_WEIBULL.xlsx`.
  - A tabela de Lead Time exibe `shape` e `lambda` quando houver amostra válida (> 0).
  - Não quebra a aba quando a amostra for insuficiente; exibir fallback seguro.

## Review (Weibull shape/lambda na estatística descritiva)
- What was validated:
  - A planilha `LT_STATS_WEIBULL.xlsx` foi inspecionada e o método confirmado: ordenação dos LT, posição de plotagem `F(i)=(2i-1)/(2n)`, regressão linear em `ln(t)` vs `ln(-ln(1-F))`.
  - `dashboard_full.py` recebeu helper `fit_weibull_linearized(...)` para calcular `shape (k)` e `lambda` (2 parâmetros) com fallback seguro quando a amostra positiva é insuficiente.
  - A tabela de Lead Time da aba `Estatística Descritiva` agora exibe `Weibull Shape (k)` e `Weibull Lambda (λ)`.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- dashboard_full.py tasks/todo.md`
  - verificação da planilha via `openpyxl` (resultado compatível: `k≈1.4258`, `lambda≈23.9604`)
- Suggested commit message:
  - `feat(stats): add Weibull shape and lambda to descriptive lead time stats`


## Current Task (Gráfico de vazão por pessoa na aba Throughput)
- [x] Localizar a aba/callback de throughput no dashboard ativo (`dashboard_full.py`)
- [x] Adicionar gráfico de barras de vazão por pessoa segmentado por tipo de demanda
- [x] Validar sintaxe e revisar diff da alteração

## Specification (Gráfico de vazão por pessoa na aba Throughput)
- Objetivo: exibir na aba de throughput um gráfico de barras de vazão por responsável, com divisão por tipo de demanda.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Gráfico aparece na aba `Throughput Breakdown` usando os filtros já aplicados.
  - Barras segmentadas por `TipoDemanda`.
  - Ordenação por maior volume de throughput por pessoa.

## Review (Gráfico de vazão por pessoa na aba Throughput)
- What was validated:
  - Inserido gráfico `Vazão por Pessoa` na aba `tab-throughput-breakdown` usando `tp_done` (itens concluídos no período filtrado).
  - Visualização em barras horizontais empilhadas por `TipoDemanda`, com ordenação por throughput total e limite Top 20 para legibilidade.
  - Tratamento de responsável ausente com fallback `Não atribuído`.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; p=pathlib.Path('dashboard_full.py'); ast.parse(p.read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- dashboard_full.py`
- Suggested commit message:
  - `feat(throughput): add stacked throughput by person chart`

## Current Task (Redesenho dos botões da Tela Principal)
- [x] Diagnosticar causa visual dos botões pequenos/desalinhados no menu inicial
- [x] Ajustar estilos dos botões `Porfólio` e `Serviços (Value Stream)` para centralização e tamanho maior
- [x] Validar sintaxe e registrar evidências/review

## Specification (Redesenho dos botões da Tela Principal)
- Objetivo: melhorar a usabilidade visual da tela principal, deixando os botões maiores e com texto centralizado vertical/horizontalmente.
- Escopo:
  - `dashboard_full.py`
- Critério de aceite:
  - Botões com área clicável maior.
  - Texto visualmente centralizado dentro dos botões.
  - Layout continua responsivo e centralizado no painel inicial.

## Review (Redesenho dos botões da Tela Principal)
- What was validated:
  - `dashboard_full.py` teve ajuste apenas no bloco da tela principal (`Tela Principal`), sem mexer na lógica de navegação.
  - Botões `Porfólio` e `Serviços (Value Stream)` ficaram maiores (`height`, `minWidth`, `fontSize`) e com centralização explícita via `display:flex`, `alignItems:center`, `justifyContent:center`.
  - Container dos botões ganhou largura máxima maior para evitar compressão e melhorar alinhamento em telas médias.
- Evidence (tests/logs/diff):
  - `git diff -- dashboard_full.py`
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('syntax ok')"`
- Suggested commit message:
  - `style(dashboard): enlarge and center main menu buttons`

## Current Task (Versão executiva 1 página - últimos 30 dias)
- [x] Definir estrutura executiva em bullet points para apresentação
- [x] Gerar documento markdown de 1 página com números-chave, entregas e impacto
- [x] Revisar clareza e consistência com o resumo consolidado anterior

## Specification (Versão executiva 1 página - últimos 30 dias)
- Objetivo: produzir uma síntese executiva de leitura rápida (1 página) para apresentação de status/entregas recentes.
- Escopo:
  - `RESUMO_EXECUTIVO_ULTIMOS_30_DIAS.md`
  - `tasks/todo.md`
- Critério de aceite:
  - Documento em bullets, com foco em comunicação executiva.
  - Deve conter janela analisada, números-chave, entregas, impacto e próximos passos.
  - Deve estar consistente com o resumo já registrado em `ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md`.

## Review (Versão executiva 1 página - últimos 30 dias)
- What was validated:
  - Criado `RESUMO_EXECUTIVO_ULTIMOS_30_DIAS.md` com estrutura de apresentação (1 página) em bullets.
  - O conteúdo consolida as frentes principais: dashboard, métricas, CFD, pipeline Jira, portfólio e deploy.
  - Datas e números mantidos consistentes com o resumo anterior: janela `25/01/2026` a `24/02/2026`, `51` commits, histórico disponível desde `19/02/2026`.
- Evidence (tests/logs/diff):
  - `git diff -- RESUMO_EXECUTIVO_ULTIMOS_30_DIAS.md tasks/todo.md`
  - conferência manual com `ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md` (seção 13)
- Suggested commit message:
  - `docs: add one-page executive summary for last 30 days`

## Current Task (Inventário de funcionalidades + resumo dos últimos 30 dias)
- [x] Levantar funcionalidades atuais a partir do código e da documentação central
- [x] Consolidar entregas dos últimos 30 dias com base em `git log` e `tasks/todo.md`
- [x] Atualizar documentação com inventário funcional e resumo executivo do período
- [x] Revisar diff e registrar evidências/review

## Specification (Inventário de funcionalidades + resumo dos últimos 30 dias)
- Objetivo: produzir um inventário atualizado das funcionalidades do projeto e registrar um resumo das entregas recentes para facilitar onboarding, auditoria e comunicação de progresso.
- Escopo:
  - `ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md`
  - `tasks/todo.md`
- Critério de aceite:
  - Documentação contém inventário funcional atualizado por componente.
  - Documentação contém resumo das entregas dos últimos 30 dias com datas explícitas.
  - Resumo cita evidências de origem (`git log` + histórico interno em `tasks/todo.md`).

## Review (Inventário de funcionalidades + resumo dos últimos 30 dias)
- What was validated:
  - `ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md` recebeu duas novas seções:
    - inventário atual de funcionalidades (extração, pipeline, orquestração, dashboards e deploy)
    - resumo de entregas dos últimos 30 dias (25/01/2026 a 24/02/2026), com recorte de commits e consolidação por tema
  - O inventário reflete o estado atual visível no código, incluindo abas atuais do `dashboard_full.py` e capacidades dos scripts `run_all_projects`.
  - O resumo de entregas cruza o histórico detalhado já registrado em `tasks/todo.md` com o `git log` da janela solicitada.
- Evidence (tests/logs/diff):
  - `git log --since='2026-01-25' --date=short --pretty=format:'%h|%ad|%s'`
  - `git rev-list --count --since='2026-01-25' HEAD` => `51`
  - `git log --since='2026-01-25' --date=short --pretty=format:'%ad'` (distribuição por dia)
  - inspeção de `dashboard_full.py`, `dash_board_metricas.py`, `jira_to_pipeline_csv.py`, `jira_portfolio_to_csv.py`, `run_all_projects.ps1`, `run_all_projects_macos.sh`, `api/index.py`
- Suggested commit message:
  - `docs: add functional inventory and 30-day delivery summary`

## Current Task (Arquivos latest por produto para downstream)
- [x] Implementar geração de `*-latest-data.csv` por produto no fluxo de exportação
- [x] Priorizar `*-latest-data.csv` no loader do dashboard quando existir
- [x] Validar sintaxe e registrar evidências/review

## Specification (Arquivos latest por produto para downstream)
- Objetivo: padronizar o consumo do CSV downstream detalhado por produto usando aliases `latest`, reduzindo necessidade de atualizar referências a arquivos datados.
- Escopo:
  - `run_all_projects_macos.sh`
  - `dashboard_full.py`
- Critério de aceite:
  - O script de exportação copia `<prefix>-<DATE_TAG>-data.csv` para `<prefix>-latest-data.csv`.
  - O dashboard prefere explicitamente `<prefix>-latest-data.csv` ao procurar downstream local do projeto.
  - Fallback para arquivos datados e URL permanece funcionando.

## Review (Arquivos latest por produto para downstream)
- What was validated:
  - `run_all_projects_macos.sh` agora atualiza `<prefix>-latest-data.csv` logo após cada exportação downstream por projeto, no mesmo padrão já usado para `*-latest-data_bottlenecks.csv`.
  - `dashboard_full.py` passou a priorizar explicitamente o alias local `<prefix>-latest-data.csv` ao carregar o downstream detalhado; se não existir, continua escolhendo o arquivo mais recente por `ctime`.
  - O suporte previamente adicionado a URL (`FLOW_PMO_DOWNSTREAM_CSV_URL_MAP` / `FLOW_PMO_DOWNSTREAM_CSV_URL`) permanece ativo como fallback complementar.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `bash -n run_all_projects_macos.sh`
  - `git diff -- dashboard_full.py run_all_projects_macos.sh tasks/todo.md`
- Suggested commit message:
  - `feat(pipeline): publish and prefer latest downstream csv aliases per product`

## Current Task (CFD detalhado e amostra Lead Time em produção)
- [x] Diagnosticar indisponibilidade do CFD detalhado e amostra baixa de Lead Time em produção
- [x] Implementar suporte a CSV downstream `*-data.csv` via URL (env) no `dashboard_full.py`
- [x] Validar sintaxe e registrar evidências/review

## Specification (CFD detalhado e amostra Lead Time em produção)
- Objetivo: permitir que a aplicação em produção carregue o CSV downstream detalhado de itens (`*-data.csv`) via URL, assim como já faz para gargalos, restaurando o CFD detalhado e o cálculo de Lead Time por etapas.
- Escopo:
  - `dashboard_full.py`
- Critério de aceite:
  - `load_project_downstream_items_csv(...)` tenta URL por projeto e URL global (quando o filename bate com o prefixo do projeto) antes de cair apenas em arquivos locais.
  - CFD detalhado deixa de depender exclusivamente de arquivos locais quando a URL estiver configurada.
  - A tela de Lead Time pode usar `LeadTime_Selected_Dias` com base no downstream em produção quando a URL estiver configurada.

## Review (CFD detalhado e amostra Lead Time em produção)
- What was validated:
  - A indisponibilidade do CFD detalhado e a amostra baixa na tela de Lead Time tinham a mesma causa provável: `load_project_downstream_items_csv(...)` buscava apenas arquivos locais (`*-data.csv`), sem suporte a URL em produção.
  - `dashboard_full.py` agora suporta download/cache de downstream via URL, no mesmo padrão já usado para gargalos.
  - O loader tenta:
    - `FLOW_PMO_DOWNSTREAM_CSV_URL_MAP` (JSON por projeto, ex. `{\"S1NC\":\"https://.../s1nc-...-data.csv\"}`)
    - `FLOW_PMO_DOWNSTREAM_CSV_URL` (URL global, se o filename bater com o prefixo do projeto)
    - pastas locais (`DATA_FOLDERS`)
  - Isso desbloqueia:
    - CFD detalhado por etapas (exato)
    - cálculo de `LeadTime_Selected_Dias` por etapas, aumentando a amostra além do fallback do modelo quando aplicável
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(dashboard): support downstream items csv via URL for CFD and lead-time stage metrics`

## Current Task (Filtro de etapas vazio em produção)
- [x] Diagnosticar por que o dropdown `Etapas Lead Time (Comprometimento)` fica sem opções em produção
- [x] Implementar fallback de opções usando etapas de gargalo/modelo quando CSV downstream não existir
- [x] Validar sintaxe e registrar evidências/review

## Specification (Filtro de etapas vazio em produção)
- Objetivo: evitar dropdown vazio no filtro de etapas de Lead Time em produção quando o CSV downstream detalhado do projeto não estiver disponível.
- Escopo:
  - `dashboard_full.py`
- Critério de aceite:
  - O dropdown `filter-leadtime-stages` exibe opções de etapas para o projeto selecionado mesmo sem `*-data.csv`, usando fallback disponível (`Fato_Gargalos`/CSV de gargalos).
  - O comportamento atual de cálculo permanece: sem downstream detalhado, o dashboard continua usando a coluna do modelo (`LeadTime_Dias`/`DataBacklog`) como fallback.
  - A UI não quebra quando não houver nenhuma fonte de etapas.

## Review (Filtro de etapas vazio em produção)
- What was validated:
  - `dashboard_full.py` agora resolve as etapas do filtro via helper único com fallback em ordem: downstream detalhado -> `Fato_Gargalos` (modelo) -> CSV de gargalos.
  - O callback `update_leadtime_stage_filter_options(...)` deixou de retornar vazio quando o downstream não existe, desde que haja etapas em gargalos/modelo.
  - Ajuste de robustez: no fallback por gargalos, a UI só remove a etapa final do conjunto selecionável quando encontra uma etapa terminal explícita (evita excluir uma etapa arbitrária).
  - O resumo do Lead Time (`build_leadtime_stage_selection_summary`) passou a refletir a origem das etapas e avisar quando está em modo fallback do modelo.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(dashboard): fallback lead-time stage filter options when downstream csv is unavailable`


## Current Task (Unificar abas de análise em Análise Fluxo)
- [x] Consolidar as abas `Análise Dimensional`, `Análise Tipos` e `Análise Eficiência` em uma única aba `Análise Fluxo`
- [x] Garantir que os gráficos/tabela das três análises sejam renderizados na aba unificada
- [x] Validar sintaxe do dashboard e registrar evidências/review

## Specification (Unificar abas de análise em Análise Fluxo)
- Objetivo: simplificar a navegação do dashboard consolidando três abas de análise em uma única aba chamada `Análise Fluxo`.
- Escopo:
  - `dashboard_full.py`
- Critério de aceite:
  - As abas separadas `Análise Dimensional`, `Análise Tipos` e `Análise Eficiência` deixam de aparecer na navegação.
  - Existe uma aba `Análise Fluxo`.
  - A aba `Análise Fluxo` exibe os gráficos de dimensional, os gráficos/detalhes de tipos e a tabela de eficiência.

## Review (Unificar abas de análise em Análise Fluxo)
- What was validated:
  - `dashboard_full.py` removeu as três tabs separadas (`Análise Dimensional`, `Análise Tipos`, `Análise Eficiência`) da lista `SERVICE_TABS` e adicionou a tab única `Análise Fluxo`.
  - A nova tab `Análise Fluxo` renderiza, em sequência, os conteúdos existentes de `tab-dim`, `tab-tipos` e `tab-eficiencia` via reutilização de `render_tab(...)`.
  - Correção complementar: `INTERNAL_SERVICE_TAB_VALUES` passou a aceitar `tab-dim`, `tab-tipos` e `tab-eficiencia` para evitar erro de "Aba inválida" na renderização interna da aba consolidada.
  - Correção de escopo aplicada após feedback: a mudança visível foi feita no dashboard ativo (`dashboard_full.py`).
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `refactor(dashboard): merge dimensional type and efficiency analysis tabs into analise fluxo`

## Current Task (Unificar abas Estabilidade/Saúde/Qualidade)
- [x] Consolidar as abas `Estabilidade`, `Saúde Fluxo` e `Qualidade` em uma única aba `Saúde do Fluxo`
- [x] Garantir que os gráficos/conteúdos das três abas sejam renderizados na aba unificada
- [x] Validar sintaxe do dashboard e registrar evidências/review

## Specification (Unificar abas Estabilidade/Saúde/Qualidade)
- Objetivo: simplificar a navegação consolidando as visualizações de estabilidade, saúde de fluxo e qualidade em uma única aba chamada `Saúde do Fluxo`.
- Escopo:
  - `dashboard_full.py`
- Critério de aceite:
  - A navegação não exibe abas separadas `Estabilidade` e `Qualidade`.
  - Existe uma aba `Saúde do Fluxo`.
  - A aba `Saúde do Fluxo` mostra os gráficos/tabelas das três análises.

## Review (Unificar abas Estabilidade/Saúde/Qualidade)
- What was validated:
  - A lista `SERVICE_TABS` deixou de exibir abas separadas `Estabilidade` e `Qualidade`.
  - A aba única foi renomeada para `Saúde do Fluxo`.
  - A renderização de `tab-saude` passou a incluir os conteúdos de `tab-estabilidade` e `tab-qualidade` via reutilização da função `render_tab(...)`, preservando os gráficos e tabelas existentes.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `refactor(dashboard): merge stability flow-health and quality tabs into one`

## Current Task (Aba CFD + Quadro Sumário por Ponto)
- [x] Criar aba dedicada `CFD`
- [x] Mover gráfico CFD para a nova aba (remover da aba `Fluxo`)
- [x] Implementar `dcc.Store` com dados sumários do CFD
- [x] Implementar quadro de estatísticas sumárias reativo a clique/hover no gráfico
- [x] Validar sintaxe e smoke test

## Specification (Aba CFD + Quadro Sumário por Ponto)
- Objetivo: separar o CFD em uma aba própria e exibir um quadro de estatísticas sumárias baseado no ponto selecionado no gráfico.
- Escopo:
  - `dashboard_full.py`
- Critério de aceite:
  - Existe uma aba `CFD` no conjunto de abas de serviços.
  - O gráfico CFD renderiza nessa aba com modos Macro/Detalhado.
  - O quadro sumário atualiza ao clicar/hover em um ponto do gráfico.

## Review (Aba CFD + Quadro Sumário por Ponto)
- What was validated:
  - Nova aba `CFD` criada e gráfico removido da aba `Fluxo`.
  - Quadro `Summary Statistics` é alimentado por `clickData`/`hoverData` + `dcc.Store` do CFD.
  - Painel mostra snapshot, métricas do período e tabela por etapa (WIP/Acumulado/Cycle Time*).
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - Smoke test local de `build_cfd_summary_payload(...)` e `create_cfd_summary_panel(...)`
- Suggested commit message:
  - `feat(dashboard): move CFD to dedicated tab and add point-driven summary panel`

## Current Task (Percentil Exato + Elegibilidade Done)
- [x] Implementar helper único de percentil empírico exato no `dashboard_full.py`
- [x] Aplicar helper a P50/P70/P85/P95 e bandas percentílicas no dashboard
- [x] Adicionar colunas de elegibilidade (Done sem cancelamento) no `dash_board_metricas.py`
- [x] Garantir que cálculos de tempo usem filtro elegível
- [x] Validar sintaxe e registrar evidências

## Specification (Percentil Exato + Elegibilidade Done)
- Objetivo: tornar os cálculos estatísticos de tempo mais precisos, sem interpolação, e excluir itens cancelados das métricas de conclusão.
- Decisões:
  - Percentis no dashboard: método empírico exato (nearest-rank), sem `quantile(linear)`.
  - População de tempo (lead/cycle): apenas itens com `Done` no período e sem `DataCancelled`.
  - Pipeline deve expor elegibilidade explícita para evitar ambiguidades (`Done sem cancelamento`).
- Escopo:
  - `dashboard_full.py`
  - `dash_board_metricas.py`
- Critério de aceite:
  - Helper único implementado e reutilizado.
  - Bandas percentílicas usam contagem/rank exatos.
  - Itens cancelados ficam fora dos cálculos de tempo de concluídos.

## Review (Percentil Exato + Elegibilidade Done)
- What was validated:
  - `dashboard_full.py` ganhou helper único de percentil empírico exato (nearest-rank, sem interpolação) e helper de bandas percentílicas exatas.
  - KPIs/estatísticas de tempo no dashboard passaram a usar percentis exatos (P50/P75/P85/P95/P98 e linhas estatísticas P15/P85/P95 onde aplicável).
  - Aba de Fluxo agora exibe tabela `Bandas Percentílicas Exatas (Cycle Time)` com:
    - `Percentile band`
    - `Items in range`
    - `Cumulative items`
    - `Cycle Time (Days)`
  - `dashboard_full.py` aplica filtro de elegibilidade temporal (`done_time_eligible_mask`) para excluir itens com cancelamento de séries de tempo (`LeadTime_Dias`, `TempoExecucao_Dias`, etc.).
  - `dash_board_metricas.py` agora expõe colunas explícitas de elegibilidade:
    - `ElegivelTempoConcluido`
    - `DoneSemCancelamento`
    - `ConcluidoSemCancelamento` (na `Fato_Items`)
  - `dash_board_metricas.py` zera (`None`) `LeadTime_Dias` e `TempoExecucao_Dias` para itens com histórico de cancelamento ao montar a `Fato_Items`.
  - Métricas semanais em `generate_consolidated_dashboard(...)` continuam contando throughput normalmente, mas calculam Lead Time/Eficiência usando apenas itens elegíveis (sem cancelamento).
  - Correção adicional de inconsistência no `dashboard_full.py`:
    - KPI `Throughput` no painel executivo agora conta `Done sem cancelamento` (antes contava todos `DataDone`, incluindo cancelados).
    - Aba de Fluxo (métricas + histograma + bandas de Cycle Time) passou a usar **concluídos elegíveis no período**, e não toda a base em fluxo no intervalo.
    - Bandas de Cycle Time passaram a incluir `Cycle Time = 0` (`>= 0`) em vez de excluir (`> 0`), evitando perda de itens válidos.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py dash_board_metricas.py`
  - Smoke test local dos helpers em `dashboard_full.py`:
    - `exact_empirical_percentile([1,2,3,4,100], 0.50/0.70/0.95)` => `3 / 4 / 100`
    - `exact_percentile_band_summary(...)` retornou tabela de faixas com contagem cumulativa e threshold por banda
  - Diff em `dashboard_full.py`:
    - helpers `done_time_eligible_mask`, `time_metric_series`, `exact_empirical_percentile`, `exact_percentile_band_summary`
    - uso dos helpers em KPIs/abas de estatística/saúde/fluxo
    - ajuste de base no painel (`throughput_total`) e na aba de fluxo (`df_flow_done_period_eligible`)
    - inclusão de ciclos `0 dias` nas bandas de Cycle Time
  - Diff em `dash_board_metricas.py`:
    - helpers `is_time_eligible_done_row`, `time_eligible_done_mask`
    - colunas de elegibilidade e exclusão de cancelados das métricas de tempo
  - Suggested commit message:
  - `feat(metrics): use exact empirical percentiles and exclude cancelled items from done-time stats`

## Current Task (Validação Lead Time / Cycle Time W1NNER)
- [x] Verificar fórmulas de lead time/cycle time no código
- [x] Calcular distribuição para W1NNER no período 2026-01-01 a 2026-02-23
- [x] Comparar com dados de produção informados (190 itens e bandas percentílicas)
- [x] Documentar conclusão e possíveis diferenças de critério

## Specification (Validação Lead Time / Cycle Time W1NNER)
- Objetivo: confirmar se os cálculos do sistema estão corretos frente aos dados de produção fornecidos para W1NNER.
- Referência de produção (fornecida pelo usuário):
  - 190 work items completed
  - Período: 01/01/2026 a 23/02/2026 (54 dias)
  - Bandas percentílicas e cycle time (dias): 50%=7, 70%=11, 85%=22, 95%=38, 95%+=274
- Escopo:
  - `dash_board_metricas.py`
  - `dashboard_full.py`
  - Modelo local (`PowerBI_Model_latest.xlsx`) se disponível
- Critério de aceite:
  - Resposta esclarece se o cálculo do sistema bate com a referência e, se não bater, explica a diferença de critério (lead vs cycle, janela, filtro, cancelados, etc.).

## Review (Validação Lead Time / Cycle Time W1NNER)
- What was validated:
  - O código calcula **Lead Time** e **Cycle Time** com fórmulas coerentes:
    - `LeadTime_Dias = DataDone - DataBacklog`
    - `TempoExecucao_Dias (Cycle Time) = DataDone - DataInProgress`
  - A tabela enviada pelo usuário é de **Cycle Time**, não de Lead Time (apesar da pergunta mencionar lead time).
  - A comparação direta com o modelo local de produção (`/Users/rodrigoalmeidadeoliveira/Documents/dados/PowerBI_Model_20260223_105715.xlsx`) não bate, principalmente por diferença de critério/filtro (itens com histórico de cancelamento e dataset ainda contaminado por `DataDone` em itens cancelados).
  - Extração factual atualizada do W1NNER (`/tmp/w1nner-downstream-factual-20260223-legacyflow.csv`, com `JIRA_IGNORE_STATUS_MAP=1`) mostrou:
    - 297 itens com `Itens concluídos` no período
    - 119 com histórico de cancelamento (`Data Cancelled`)
    - 182 com cycle time factual não nulo (`Itens concluídos - In progress`)
  - Quando exclui itens com histórico de cancelamento, os percentis ficam bem mais próximos da referência em cauda:
    - `P95 ≈ 41` e `max = 273` (referência: `38` e `274`)
    - ainda não fecha em `190` itens nem nos percentis menores (`P50/P70/P85`) por diferença de critério de inclusão/início.
- Evidence (tests/logs/diff):
  - Fórmulas no código:
    - `dash_board_metricas.py:2093` (`TempoExecucao_Dias`)
    - `dash_board_metricas.py:2094` (`LeadTime_Dias`)
  - Percentis no dashboard/modelo usam `quantile(...)` em séries (ex.: `dashboard_full.py:3166`-`3168` para lead time).
  - Inspeção do modelo local (`PowerBI_Model_20260223_105715.xlsx`) para W1NNER em `2026-01-01` a `2026-02-23`:
    - `W1NNER_DONE_COUNT = 297`
    - `Cancelado = 119` (soma no período)
  - Extração Jira factual W1NNER com fluxo correto:
    - `/tmp/w1nner-downstream-factual-20260223-legacyflow.csv`
    - `Issues encontradas: 2026`
    - `COMPLETED_ROWS_BY_DONE = 297`
    - `CYCLE_NON_NULL = 182`
  - Comparação factual (W1NNER, ciclo `Itens concluídos - In progress`):
    - Todos os concluídos com cycle válido: `P50=10`, `P70=20`, `P85≈36.85`, `P95≈236.95`, `max=686`
    - Excluindo histórico de cancelamento: `P50=9`, `P70=17`, `P85=25`, `P95≈41.4`, `max=273`
- Suggested commit message:
  - `chore: validate w1nner lead-time and cycle-time calculations against production`

## Current Task (Refino Visual do CFD)
- [x] Definir ajustes de legibilidade e paleta do CFD
- [x] Implementar layout/cores mais legíveis no `dashboard_full.py`
- [x] Validar sintaxe e smoke test
- [x] Atualizar review e sugestão de commit

## Specification (Refino Visual do CFD)
- Objetivo: melhorar legibilidade do `Cumulative Flow Diagram (CFD)` com paleta de cores mais viva e layout mais compreensível.
- Escopo:
  - `dashboard_full.py` (apenas visualização do gráfico CFD; sem alterar regras de cálculo).
- Critério de aceite:
  - Cores do CFD ficam mais contrastantes/vivas.
  - Leitura do gráfico melhora (grade, legenda, hover, botões/título).
  - Modos `Macro` e `Detalhado` continuam funcionando.

## Review (Refino Visual do CFD)
- What was validated:
  - CFD passou a usar áreas empilhadas (`stackgroup`) por faixa, melhorando leitura visual das bandas em macro e detalhado.
  - Paleta foi trocada por cores mais vivas/contrastantes, com mapeamento por etapa (ex.: `Done` vermelho, `Backlog` laranja).
  - Layout melhorado com `hovermode='x unified'`, legenda horizontal inferior, grid mais suave e botões posicionados acima do gráfico.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - Smoke test local: `create_cfd_figure(...)` retornou figura com botões dos dois modos e `stackgroup` ativo
  - Diff em `dashboard_full.py` (helpers `_hex_to_rgba`/`_cfd_stage_color` + refino visual de `create_cfd_figure`)
- Suggested commit message:
  - `style(dashboard): improve CFD readability with vivid colors and stacked areas`

## Current Task (Batch Changelog Detalhado por Projeto)
- [x] Definir formato/nomes dos artefatos de changelog detalhado em modo batch
- [x] Implementar exportação opcional de changelog real no `jira_to_pipeline_csv.py`
- [x] Expor flag no `run_all_projects_macos.sh` para gerar changelog detalhado por projeto
- [x] Validar sintaxe/ajuda e registrar evidências

## Specification (Batch Changelog Detalhado por Projeto)
- Objetivo: criar uma opção no fluxo batch para extrair o changelog detalhado e real (baseado no histórico do Jira) em arquivos separados por projeto.
- Escopo:
  - `jira_to_pipeline_csv.py`
  - `run_all_projects_macos.sh`
- Critério de aceite:
  - Exportador aceita opção opcional para gravar CSV de changelog detalhado.
  - Script batch expõe flag para ativar/desativar a geração do changelog detalhado por projeto.
  - Arquivos gerados seguem padrão por projeto (um arquivo por projeto).
  - Sintaxe dos scripts validada.

## Review (Batch Changelog Detalhado por Projeto)
- What was validated:
  - `jira_to_pipeline_csv.py` agora aceita `--detailed-changelog-out` para exportar transições reais de status do Jira (changelog) em CSV opcional por execução.
  - O CSV detalhado contém linhas por transição de status com contexto da issue (`Projeto`, `Issue Key`, `Title`, `Tipo de Problema`) e dados do histórico (`History Created`, `Author`, `From Status`, `To Status`).
  - `run_all_projects_macos.sh` ganhou flag batch `--run-detailed-changelog-export` (default desabilitado) para gerar um arquivo de changelog detalhado por projeto e atualizar o respectivo `latest`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile jira_to_pipeline_csv.py`
  - `bash -n run_all_projects_macos.sh`
  - `./run_all_projects_macos.sh --help` mostra `--run-detailed-changelog-export` / `--no-run-detailed-changelog-export`
  - `python3 jira_to_pipeline_csv.py --help` mostra `--detailed-changelog-out`
- Suggested commit message:
  - `feat(batch): add optional per-project detailed Jira changelog export`

## Current Task (Validação Factual + KPI Cancelados)
- [x] Gerar extração S1NC factual atualizada
- [x] Inspecionar volume e exemplos de itens cancelados no CSV
- [x] Adicionar KPI explícito de cancelados no `dashboard_full.py` (período e semanal)
- [x] Validar sintaxe e registrar evidências

## Specification (Validação Factual + KPI Cancelados)
- Objetivo: validar a extração factual recém-ajustada e refletir cancelados explicitamente no dashboard novo.
- Escopo:
  - `jira_to_pipeline_csv.py` (execução da extração)
  - `dashboard_full.py` (KPI visual de cancelados)
- Critério de aceite:
  - CSV factual S1NC gerado com `Data Cancelled`.
  - Evidência de quantidade de cancelados e amostra no CSV.
  - Dashboard expõe métrica de cancelados no período e visão semanal (média/total).

## Review (Validação Factual + KPI Cancelados)
- What was validated:
  - Extração factual S1NC gerada com sucesso em `/tmp/s1nc-downstream-factual-20260223.csv` contendo coluna `Data Cancelled`.
  - Inspeção de cancelados no CSV factual:
    - `179` itens com `Data Cancelled`
    - `178` com `Done` também preenchido (cards posteriormente fechados em `Done`)
    - `1` sem `Done`
  - `dashboard_full.py` passou a exibir KPIs explícitos de cancelados no bloco "Throughput Consolidado":
    - `Cancelados (Período)`
    - `Média Semanal Cancel.`
    - `Semanas c/ Cancel.`
  - Implementação é resiliente: se `DataCancelled` não existir no modelo carregado, KPIs ficam em `0` sem quebrar a tela.
- Evidence (tests/logs/diff):
  - Extração Jira real (S1NC): `Issues encontradas: 1758`, `CSV gerado: /tmp/s1nc-downstream-factual-20260223.csv`
  - Inspeção CSV via `python3`:
    - `CANCELLED_TOTAL=179`
    - `TOP_TYPES=[('Support', 101), ('Problema', 34), ('Tarefa', 22), ('Tech', 21), ...]`
    - Semanas com mais cancelamentos: `2024-07-29 (24)`, `2025-02-17 (11)`, `2025-03-10 (11)`
  - `python3 -m py_compile dashboard_full.py jira_to_pipeline_csv.py dash_board_metricas.py`
- Suggested commit message:
  - `feat(dashboard): add cancelled-item KPIs and validate factual S1NC export`

## Current Task (Diretriz Factual para Dashboard Novo)
- [x] Definir CSV factual (changelog) como fonte principal do dashboard novo
- [x] Remover heurísticas de compatibilidade legada que distorcem datas por etapa
- [x] Separar cancelados de concluídos no pipeline (exportação + métricas)
- [x] Manter comparação com legado apenas como validação auxiliar (volume/schema)
- [x] Validar sintaxe e registrar decisão

## Specification (Diretriz Factual para Dashboard Novo)
- Objetivo: priorizar precisão da movimentação real dos cards no dashboard novo, usando changelog Jira como fonte de verdade.
- Decisões:
  - Datas por etapa: primeira entrada real por etapa (sem backfill/compressão legada no modo padrão).
  - `Cancelled` não deve ser tratado automaticamente como `Done`.
  - Throughput de concluídos: somente `Done`.
  - Itens cancelados: medir separadamente.
  - Lead Time: medir somente itens `Done` (cancelados excluídos).
  - Legado: usar apenas para reconciliação auxiliar de volume/schema, não como verdade para datas de fluxo.
- Escopo:
  - `jira_to_pipeline_csv.py`
  - `dash_board_metricas.py`

## Review (Diretriz Factual para Dashboard Novo)
- What was validated:
  - Exportador voltou ao comportamento factual para datas por etapa (removido backfill/compressão legada no fluxo padrão).
  - `Cancelled` deixou de preencher a coluna terminal (`Itens concluídos`) automaticamente.
  - Exportador passou a registrar `Data Cancelled` separadamente (derivada do changelog, com fallback em `resolutiondate` quando status atual é cancelado).
  - `dash_board_metricas.py` reconhece `Data Cancelled`, parseia a data e inclui contagem semanal de cancelados separada (`Cancelados (semana)` e `Categoria - Cancelados`).
  - `Fato_Items` agora expõe `DataCancelled` e indicador `Cancelado` (sem contaminar `Concluido`/`DataDone`).
  - Lead Time/Throughput de concluídos continuam baseados em `Done`, o que automaticamente exclui cancelados quando o CSV factual é usado.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile jira_to_pipeline_csv.py dash_board_metricas.py`
  - Smoke test local de `extract_first_status_dates(...)` + `extract_first_transition_date(...)`:
    - item cancelado gera `Data Cancelled`
    - colunas de etapa permanecem vazias (cancelado não vira `Itens concluídos`)
- Suggested commit message:
  - `feat(flow): use factual stage dates and track cancelled items separately`

## Current Task (Correção Fina Downstream S1NC)
- [x] Investigar divergência das datas por etapa (changelog/status aliases/critério)
- [x] Ajustar schema de metadados para compatibilidade 1:1 com CSV correto
- [x] Verificar `S1NC-1939` no Jira (tipo/status/permissão) e causa da ausência
- [x] Regerar CSV e comparar novamente com o arquivo correto
- [x] Documentar evidências e conclusão

## Specification (Correção Fina Downstream S1NC)
- Objetivo: aproximar a extração downstream do CSV correto em conteúdo e schema, após correções iniciais.
- Escopo:
  - `jira_to_pipeline_csv.py`
- Itens de diagnóstico/correção:
  - Datas por etapa: entender por que o arquivo correto contém datas preenchidas/replicadas onde o exportador atual deixa vazio ou datas diferentes.
  - Schema: alinhar colunas de metadados (`Story Points`, `Story point estimate`, remoção/renomeação de colunas divergentes como `Afeta as versões`).
  - `S1NC-1939`: confirmar presença/ausência no Jira e motivo (tipo excluído, permissão, status, timing).
- Critério de aceite:
  - Evidência objetiva da causa das datas divergentes.
  - Schema do exportador alinhado ao arquivo correto.
  - Diagnóstico de `S1NC-1939` concluído.

## Review (Correção Fina Downstream S1NC)
- What was validated:
  - Causa principal das datas por etapa divergentes identificada: o CSV correto usa um critério de compatibilidade/normalização diferente da extração “primeira passagem por status”.
  - Evidência (`S1NC-1`): o CSV correto considera `Triagem=created`, ignora aliases antigos como `To Do`/`Sprint Backlog` para `Backlog`, trata `Cancelled` como terminal e preenche etapas puladas com a data terminal (30/07/2024).
  - Evidência (`S1NC-1000`): o CSV correto concentra várias etapas intermediárias na data de marco posterior (18/09/2025), enquanto a extração atual usa datas reais anteriores (11/09 e 12/09), indicando regra histórica de compressão/propagação de datas.
  - Schema de metadados do exportador foi alinhado 1:1 ao arquivo correto (headers iguais), incluindo `Story Points` / `Story point estimate` e remoção de `Afeta as versões`.
  - `S1NC-1939` foi consultado diretamente no Jira e retornou `404` / `search_count=0`, indicando ausência atual para o usuário/token (issue removida/sem permissão/indisponível no momento); por isso aparece no CSV correto mas não na extração atual.
- Evidence (tests/logs/diff):
  - Query Jira `S1NC-1` (changelog real) + `extract_first_status_dates(...)` após ajuste:
    - retorno reproduziu exatamente as datas do CSV correto para o item (`Triagem=28/11/2023`, `Backlog=24/07/2024`, etapas seguintes em `30/07/2024`).
  - Query Jira `S1NC-1000`:
    - transições reais incluem `In Development` (11/09), `Staging` (12/09), `QA Approved Staging` / `Ready for Production` (18/09), `Done` (19/09)
    - CSV correto usa `18/09/2025` em várias etapas intermediárias, evidenciando compressão/backfill diferente de “first hit”.
  - Query Jira `S1NC-1939`:
    - `SEARCH_COUNT 0`
    - `GET_ISSUE_ERR HTTPError 404 ... /issue/S1NC-1939`
  - Comparação automática (`/tmp/s1nc-downstream-20260223-data-fixed-legacy-v3.csv` vs CSV correto):
    - `HEADERS_EQUAL=True`
    - `ROWS=1758 vs 1757`
    - `ONLY_REF_IDS=['S1NC-1939']`
    - `MISMATCH_IDS=1535` (restante majoritariamente em datas por etapa, por diferença de critério histórico)
  - `python3 -m py_compile jira_to_pipeline_csv.py`
- Suggested commit message:
  - `fix(export): align downstream stage dates and schema with canonical S1NC csv`

## Current Task (Correção Divergência Extração S1NC)
- [x] Aplicar filtro JQL padrão para excluir Épico/Iniciativa no downstream
- [x] Alinhar status map legado ao formato do CSV correto
- [x] Proteger preenchimento de `Epic Name`/`Principal` contra inversão por field map
- [x] Validar sintaxe e comportamento básico (JQL/headers/heurística)
- [x] Documentar resultado e sugestão de commit

## Specification (Correção Divergência Extração S1NC)
- Objetivo: corrigir a geração de `*-downstream-*-data.csv` para ficar alinhada ao CSV correto informado pelo usuário.
- Escopo:
  - `jira_to_pipeline_csv.py`
- Correções:
  - Excluir `Épico`/`Iniciativa` (e aliases em inglês) por padrão no JQL downstream.
  - Usar nomes de etapas/colunas legadas iguais ao arquivo correto (`Ready to Start`, `In progress`, `Homolog`, `Itens concluídos`, etc.).
  - Reatribuir automaticamente valor de `Epic Name` para `Principal` quando `epic_name` vier como issue key e `principal` estiver vazio (sinal de field map semântico invertido).
- Critério de aceite:
  - `build_jql` inclui filtro de tipo por padrão.
  - Exportador legado produz headers compatíveis com o arquivo correto.
  - Caso típico de inversão (`Epic Name` issue key / `Principal` vazio) é corrigido no row builder.

## Review (Correção Divergência Extração S1NC)
- What was validated:
  - `jira_to_pipeline_csv.py` agora exclui por padrão `Épico`/`Epic`/`Iniciativa`/`Initiative` no JQL downstream (com override por env `JIRA_INCLUDE_PORTFOLIO_ISSUES=1`).
  - Fluxo legado (`W1NNER/S1NC/BEFINANCE`) passou a usar nomes de etapas alinhados ao CSV correto: `Ready to Start`, `In progress`, `ready code review`, `Code review`, `ready testing/Qa`, `Testing/QA`, `ready homolog`, `Homolog`, `ready for production`, `Itens concluídos`.
  - Heurística defensiva corrige caso de inversão semântica de `JIRA_FIELD_MAP`: se `Epic Name` vier como issue key e `Principal` vier vazio, o valor é movido para `Principal`.
  - Mantido escape hatch de configuração para incluir itens de portfólio via variável de ambiente.
  - Extração real no Jira (S1NC) executada após correção; removeu os 46 extras de `Épico/Iniciativa`, mas o CSV ainda não ficou idêntico ao arquivo de referência.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile jira_to_pipeline_csv.py`
  - Smoke test local (import do módulo):
    - `build_jql(['S1NC'], '', DEFAULT_EXCLUDED_ISSUE_TYPES)` => `project in (S1NC) AND issuetype not in ("Épico", "Epic", "Iniciativa", "Initiative")`
    - `LEGACY_PRODUCTS_STATUS_MAP.keys()` retorna headers alinhados ao CSV correto
    - `build_issue_row(...)` com `epic_name='W1NNER-1771'` e `principal=''` passou a gerar `Principal='W1NNER-1771'` e `Epic Name='Epic summary'`
  - Extração Jira real (com elevação) gerou:
    - `/tmp/s1nc-downstream-20260223-data-fixed.csv` (ainda usando `JIRA_STATUS_MAP` do env)
    - `/tmp/s1nc-downstream-20260223-data-fixed-legacy.csv` (com `JIRA_IGNORE_STATUS_MAP=1`, formato legado alinhado)
  - Log da extração legada: `Issues encontradas: 1757` e `CSV gerado: /tmp/s1nc-downstream-20260223-data-fixed-legacy.csv`
  - Comparação final vs arquivo correto (`20260223-data (1).csv`):
    - `HEADERS_EQUAL=False` (persistem diferenças de schema de metadados)
    - `ROWS=1758 vs 1757`
    - `ONLY_REF_IDS=1` (`S1NC-1939`)
    - `MISMATCH_IDS=1745` (datas por etapa ainda divergentes em larga escala)
- Suggested commit message:
  - `fix(export): align downstream jira extraction with canonical csv format`

## Current Task (Diagnóstico Divergência CSV S1NC)
- [x] Verificar se a divergência nasce na extração ou na consolidação
- [x] Mapear evidências no código (JQL, status map, field map, escrita de arquivos)
- [x] Documentar causa provável e próximos ajustes

## Specification (Diagnóstico Divergência CSV S1NC)
- Objetivo: identificar em qual etapa do sistema surge a divergência entre o CSV correto e o `s1nc-downstream-20260223-data.csv`.
- Escopo:
  - `jira_to_pipeline_csv.py` (extração e geração do downstream)
  - `run_all_projects_macos.sh` (orquestração e parâmetros usados)
  - `dash_board_metricas.py` (consolidação)
- Critério de aceite:
  - Classificação clara: erro de extração, de consolidação, ou ambos.
  - Evidências com referências de código e diferenças observadas nos CSVs.

## Review (Diagnóstico Divergência CSV S1NC)
- What was validated:
  - A divergência está na **extração/exportação downstream**, não na consolidação.
  - `run_all_projects_macos.sh` gera diretamente `s1nc-downstream-<data>-data.csv` chamando `jira_to_pipeline_csv.py`.
  - `dash_board_metricas.py` lê CSVs downstream para consolidar, mas grava saídas em `PowerBI_Model_*.xlsx` (não reescreve o downstream).
  - Os **46 IDs extras** no arquivo do sistema são majoritariamente `Épico` (41) e `Iniciativa` (5), compatível com ausência de filtro JQL por tipo.
  - As diferenças massivas em datas/colunas decorrem de mapeamento de fluxo/campos na exportação (status map/header e field map), não de transformação do consolidado.
- Evidence (tests/logs/diff):
  - Comparação dos CSVs: `ONLY_OTHER_IDS=46`, `EXTRA_TYPES=[('Épico', 41), ('Iniciativa', 5)]`.
  - `jira_to_pipeline_csv.py:664` constrói JQL base como `project in (...)` e só aplica filtro extra se `--jql-extra` for passado.
  - `run_all_projects_macos.sh:159` chama exportador sem `--jql-extra`.
  - `run_all_projects_macos.sh:147`-`148` remove `JIRA_STATUS_MAP` e força `JIRA_IGNORE_STATUS_MAP=1`, alterando o fluxo usado na exportação.
  - `jira_to_pipeline_csv.py:48`-`68` define `LEGACY_PRODUCTS_STATUS_MAP` (headers iguais ao arquivo do sistema: `Ready for development`, `Staging`, `Done`).
  - `jira_to_pipeline_csv.py:607`-`653` popula `Epic Name`/`Principal` a partir de `JIRA_FIELD_MAP`; divergência observada indica mismatch de configuração de campo versus arquivo de referência.
  - `dash_board_metricas.py:2121`-`2148` grava modelo consolidado em `PowerBI_Model_*.xlsx`, sem sobrescrever `s1nc-downstream-*.csv`.
- Suggested commit message:
  - `docs: document root cause of S1NC downstream csv divergence`

## Current Task (Comparação de CSVs Downstream)
- [x] Registrar e executar comparação entre os dois CSVs informados
- [x] Validar colunas, contagem de linhas e conteúdo (arquivo correto como referência)
- [x] Documentar evidências e conclusão
- [x] Atualizar sugestão de commit

## Specification (Comparação de CSVs Downstream)
- Objetivo: verificar se `20260223-data (1).csv` e `s1nc-downstream-20260223-data.csv` trazem os mesmos dados.
- Referência correta: `20260223-data (1).csv` (Downloads).
- Escopo:
  - Comparação estrutural (headers/ordem de colunas).
  - Comparação de volume (linhas).
  - Comparação de conteúdo (registros iguais/diferentes).
- Critério de aceite:
  - Resposta conclui claramente se os arquivos são idênticos em dados.
  - Se houver divergência, listar diferenças objetivas (estrutura e/ou linhas).

## Review (Comparação de CSVs Downstream)
- What was validated:
  - Os arquivos **não** trazem os mesmos dados.
  - O arquivo correto (`20260223-data (1).csv`) tem 1758 linhas de dados; o arquivo `s1nc-downstream-20260223-data.csv` tem 1804 (46 IDs extras no segundo).
  - Estrutura divergente: headers e nomes de colunas de etapas diferem (ex.: `Ready to Start` vs `Ready for development`, `Homolog` vs `Staging`), além de colunas exclusivas em cada arquivo.
  - Mesmo nos 1758 IDs em comum, 1745 IDs possuem diferenças em campos compartilhados (ex.: `Triagem`, `Backlog`, `Epic Name`, `Sprints`, `Principal`).
- Evidence (tests/logs/diff):
  - Comparação via `python3` (`csv.DictReader` + `Counter`) entre:
    - `/Users/rodrigoalmeidadeoliveira/Downloads/20260223-data (1).csv`
    - `/Users/rodrigoalmeidadeoliveira/Documents/dados/s1nc-downstream-20260223-data.csv`
  - Resultado: `HEADERS_EQUAL=False`, `ROWS=1758 vs 1804`, `ONLY_OTHER_IDS=46`, `OVERLAP_IDS_WITH_FIELD_DIFFS=1745`.
  - Exemplo (`S1NC-1`): `Triagem` vazio no segundo arquivo vs `28/11/2023` no correto; `Backlog` `22/04/2024` vs `24/07/2024`; `Epic Name`/`Principal` invertidos; `Sprints` com formatação diferente.
- Suggested commit message:
  - `chore: compare downstream csv files and document differences`

## Current Task (CFD Detalhado por Etapas)
- [x] Definir abordagem do modo detalhado exato via CSV downstream e registrar limitações
- [x] Implementar opção `Macro` x `Detalhado por Etapas` no gráfico CFD
- [x] Reutilizar etapas do fluxo e datas por etapa a partir do CSV downstream (`*_data.csv`)
- [x] Validar sintaxe e revisar diff
- [x] Atualizar review e sugestão de commit

## Specification (CFD Detalhado por Etapas)
- Objetivo: adicionar no CFD uma opção de visualização detalhada por etapas do fluxo usando datas reais por etapa do CSV downstream do projeto.
- Escopo:
  - `dashboard_full.py` (cálculo estimado das bandas por etapa e toggle no gráfico).
- Premissas:
  - O modelo consolidado não possui timestamps por etapa por item, então o modo detalhado lê o CSV downstream `*_data.csv` do projeto.
  - O modo macro permanece como visão exata e padrão.
- Critério de aceite:
  - Usuário consegue alternar entre `Macro` e `Detalhado por Etapas` no mesmo CFD.
  - Legenda do modo detalhado usa nomes de etapas de `bottlenecks_df`.
  - Quando não houver gargalos suficientes, o gráfico permanece em modo macro sem quebrar.

## Review (CFD Detalhado por Etapas)
- What was validated:
  - CFD passou a expor botões `Macro (exato)` e `Detalhado por Etapas (exato)` no próprio gráfico.
  - Modo detalhado usa datas reais por etapa do CSV downstream `*_data.csv` (ex.: `s1nc-downstream-*-data.csv`) e plota bandas por etapa em ordem de fluxo.
  - Quando não há projeto/CSV com colunas de etapa, o gráfico mantém macro e mostra aviso de indisponibilidade do modo detalhado.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - Smoke test local: `create_cfd_figure(...)` retornou `Figure` com botões `Macro (exato)` / `Detalhado por Etapas (exato)`
  - Diff em `dashboard_full.py` (helper `load_project_downstream_items_csv`, parser de colunas de etapa e upgrade de `create_cfd_figure`)
- Suggested commit message:
  - `feat(dashboard): add exact stage-level CFD from downstream project csv`

## Current Task (Cumulative Flow Diagram)
- [x] Definir especificação e plano detalhado do CFD na aba de Fluxo
- [x] Implementar cálculo das séries cumulativas por etapa (Backlog / Em Progresso / Pronto)
- [x] Adicionar gráfico `Cumulative Flow Diagram (CFD)` no `dashboard_full.py`
- [x] Validar sintaxe e revisar diff
- [x] Registrar review com evidências e sugestão de commit

## Specification (Cumulative Flow Diagram)
- Objetivo: adicionar um gráfico `Cumulative Flow Diagram (CFD)` na aba `Fluxo` para visualizar a evolução acumulada das etapas ao longo do tempo.
- Escopo:
  - `dashboard_full.py` (cálculo das séries do CFD e renderização do gráfico na UI).
- Premissas:
  - Usar os timestamps já disponíveis no modelo (`DataBacklog`, `DataInProgress`, `DataDone`) e filtros globais aplicados.
  - Se não houver histórico detalhado por status, representar macrofases de fluxo (`Backlog`, `Em Progresso`, `Pronto`).
- Critério de aceite:
  - O gráfico aparece na aba `Fluxo` sem quebrar os gráficos existentes.
  - O CFD respeita filtros (projeto, tipo, responsável, período).
  - Há fallback seguro com mensagem quando faltarem datas suficientes.

## Review (Cumulative Flow Diagram)
- What was validated:
  - Aba `Fluxo` passou a renderizar o gráfico `Cumulative Flow Diagram (CFD)` após o breakdown de lead time.
  - Cálculo usa macrofases (`Backlog`, `Em Progresso`, `Pronto`) com acumulação da direita para a esquerda (algoritmo de CFD).
  - Fallback com mensagem é exibido quando faltam dados temporais suficientes.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - Diff em `dashboard_full.py` (helpers `build_cfd_dataframe`/`create_cfd_figure` + integração em `tab-fluxo`)
- Suggested commit message:
  - `feat(dashboard): add cumulative flow diagram (CFD) to fluxo tab`

## Current Task (Data da Última Carga no Cabeçalho)
- [x] Definir fonte da data de carga exibida no dashboard
- [x] Implementar cálculo/formatação no `dashboard_full.py`
- [x] Exibir data ao lado do título principal da tela
- [x] Validar sintaxe e revisar diff

## Specification (Data da Última Carga no Cabeçalho)
- Objetivo: exibir no cabeçalho principal do dashboard a data/hora da última carga de dados processada.
- Escopo:
  - `dashboard_full.py` (layout do cabeçalho e helper de formatação).
- Critério de aceite:
  - Texto visível ao lado do título principal.
  - Sem quebrar o layout em desktop/mobile (com wrap simples).
  - Fallback seguro se a data não puder ser inferida.

## Review (Data da Última Carga no Cabeçalho)
- What was validated:
  - Cabeçalho principal passou a exibir `Última carga processada: ...` ao lado do título.
  - Timestamp usa preferência por data no nome `PowerBI_Model_YYYYMMDD_HHMMSS.xlsx`, com fallback para `mtime`.
  - Layout usa `flexWrap` para não quebrar em telas menores.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - Diff em `dashboard_full.py` (helper `_format_last_processed_load` + bloco de cabeçalho)

## Current Task (Classe de Serviço por Prioridade)
- [x] Definir especificação da mudança (classe de serviço baseada em `Prioridade`)
- [x] Ajustar classificação no pipeline de geração de dados
- [x] Ajustar fallback no dashboard para usar `Prioridade` quando `ClasseServico` ausente/inválida
- [x] Atualizar filtro da tela para refletir o novo critério
- [x] Validar com checagem de sintaxe e revisão de diff
- [x] Revisar elegância e impacto mínimo (sem regressão)

## Specification (Classe de Serviço por Prioridade)
- Objetivo: parar de usar `Standard` como default de classe de serviço e usar `Prioridade (priority)` do projeto/item como fonte de classificação.
- Escopo:
  - `dash_board_metricas.py`: regra de classificação de classe de serviço.
  - `dashboard_full.py`: fallback de `ClasseServico` e filtro da UI.
- Restrições:
  - Manter compatibilidade com dados já exportados.
  - Evitar mudança estrutural ampla fora dos pontos de classificação/filtro.
- Entregáveis:
  - `ClasseServico` preenchida com base em `Prioridade` quando não houver regra explícita (ex.: Expedite/Fixed Date/Intangible).
  - Filtro da tela coerente com o novo comportamento.
  - Verificação de sintaxe e inspeção de diff.

## Current Task
- [x] Define scope and write detailed specification
- [x] Validate plan before implementation
- [x] Add bottleneck data to PowerBI model spreadsheet
- [x] Change dashboard bottleneck source to spreadsheet first
- [x] Keep safe fallback behavior (legacy CSV + computed)
- [x] Verify behavior (syntax/diff) and update docs
- [x] Review for elegance and root-cause quality

## Specification
- Objetivo: consolidar dados de gargalo na mesma planilha Excel dos demais indicadores e fazer o dashboard ler prioritariamente dessa planilha.
- Restrições:
  - Manter impacto mínimo no fluxo atual.
  - Preservar compatibilidade com artefatos legados.
  - Evitar quebra quando a aba nova não existir.
- Entregáveis:
  - Aba `Fato_Gargalos` no `PowerBI_Model_*.xlsx`.
  - Leitura do gargalo no `dashboard_full.py` a partir da aba da planilha.
  - Fallback mantido para CSV legado e cálculo em memória.
- Validação:
  - Checar sintaxe dos arquivos alterados.
  - Revisar diff final para confirmar prioridade da nova fonte.

## Progress Notes
- Date: 2026-02-20
- Summary: Classe de serviço deixou de cair em `Standard` como comportamento principal; agora usa `Prioridade` como fallback no pipeline e também no carregamento do dashboard para compatibilidade com modelos antigos.
- Risks:
  - Itens sem `Prioridade` e sem sinais de classe de serviço explícita continuam em `Standard`.
- Date: 2026-02-20
- Summary: Corrigido desalinhamento de diretório de dados; métricas e modelo agora podem usar `DATA_FOLDER`/`FLOW_PMO_DATA_DIR` (mesma pasta de exportação), e `Fato_Gargalos` voltou a incluir `DATA&ANALYTICS`.
- Risks:
  - Se produção continuar apontando para um `PowerBI_Model_latest.xlsx` antigo, a tela seguirá no fallback legado.
- Date: 2026-02-20
- Summary: Ajustado mapeamento de tipo de demanda para classificar `Ad-hoc` como `Suporte` no processamento de `Tipo de Problema`.
- Risks:
  - Exportações antigas precisam ser reprocessadas para refletir a nova classificação nos dashboards.
- Date: 2026-02-20
- Summary: Corrigida resolução de pasta de dados no `dashboard_full.py` para incluir `~/Documents/dados` e `~/Documents/Dados`, alinhando leitura do modelo com o pipeline de reprocessamento.
- Risks:
  - Se produção usar `FLOW_PMO_MODEL_URL`/`FLOW_PMO_MODEL_FILE` apontando para artefato antigo, o ajuste de pastas locais não terá efeito.

## Review
- What was validated:
  - Reprocessamento completo em `/Users/.../Documents/dados` com sucesso.
  - `PowerBI_Model_latest.xlsx` gerado com `Fato_Gargalos` contendo linhas de `DATA&ANALYTICS`.
  - Sintaxe dos módulos Python e shell alterados.
  - Regra de classificação atualizada para mapear `ad-hoc/adhoc/ad hoc` em `Suporte`.
  - `dashboard_full.py` passou a considerar `~/Documents/dados` e `~/Documents/Dados` na seleção automática do modelo.
- Evidence (tests/logs/diff):
  - Execução: `DATA_FOLDER=/Users/.../Documents/dados FLOW_PMO_DATA_DIR=/Users/.../Documents/dados python3 dash_board_metricas.py`
  - Verificação da aba `Fato_Gargalos` no `PowerBI_Model_latest.xlsx` com 3 linhas para `DATA&ANALYTICS`.
  - `python3 -m py_compile dash_board_metricas.py dashboard_full.py api/index.py`
  - `bash -n run_all_projects_macos.sh`
  - Diferença na regra: `dash_board_metricas.py` agora inclui `ad-hoc`, `adhoc` e `ad hoc` na categoria `Suporte`.
  - Diagnóstico: antes do ajuste, `dashboard_full.MODEL_FILE` resolvia para `/Users/.../OneDrive-W1/Documentos/Dados/PowerBI_Model_20260220_151715.xlsx` (modelo antigo com `Tipo=Outro` para parte do DT).
- Open issues:
- Necessário publicar o `PowerBI_Model_latest.xlsx` atualizado na Vercel para refletir em produção.
  - Para refletir o novo mapeamento no modelo dimensional (`Dim_ClasseServico`), é necessário reprocessar exportação com `dash_board_metricas.py`.

## Current Task (Revisão de Gargalos por Projeto)
- [x] Definir hipótese de impacto cruzado após ajuste de mapeamento do DATA&ANALYTICS
- [x] Inspecionar código de seleção/carregamento de gargalos (`Fato_Gargalos`, CSV fallback, filtro por projeto)
- [x] Validar conteúdo real do modelo carregado pelo dashboard
- [x] Comparar saída de gargalos entre projetos para detectar contaminação
- [x] Documentar conclusão e risco residual

## Specification (Revisão de Gargalos por Projeto)
- Objetivo: confirmar se a mudança de mapeamento do fluxo para DATA&ANALYTICS contaminou gargalos dos demais projetos.
- Escopo:
  - `dashboard_full.py`: leitura de `Fato_Gargalos` e filtro por `Projeto`.
  - Modelo em uso pelo app (`MODEL_FILE`) e aba `Fato_Gargalos`.
- Critério de aceite:
  - Cada projeto deve retornar somente suas próprias linhas de gargalo.
  - Não deve haver reutilização de linhas de DATA&ANALYTICS para outros projetos na fonte principal.

## Progress Notes
- Date: 2026-02-20
- Summary: Revisão concluída no modelo carregado em runtime (`/Users/rodrigoalmeidadeoliveira/Documents/dados/PowerBI_Model_20260220_162032.xlsx`): `Fato_Gargalos` possui 12 linhas, distribuídas em 4 projetos (3 por projeto), e o filtro de `load_project_bottlenecks_from_model` retorna subconjuntos corretos por projeto.
- Risks:
  - Se produção cair no fallback `FLOW_PMO_BOTTLENECK_CSV_URL` (URL única global), o mesmo CSV pode ser usado para mais de um projeto quando não houver `Fato_Gargalos`/URL map por projeto.
- Date: 2026-02-20
- Summary: Harden no fallback legado de gargalos: URL global agora só é utilizada quando o nome do arquivo bate com o prefixo do projeto filtrado, reduzindo risco de contaminação cruzada.
- Risks:
  - Ambientes devem preferir `FLOW_PMO_BOTTLENECK_CSV_URL_MAP` para configuração explícita por projeto.

## Review (Revisão de Gargalos por Projeto)
- What was validated:
  - `dashboard_full.MODEL_FILE` aponta para modelo local atualizado.
  - `fato_gargalos['Projeto'].value_counts()` = BEFINANCE 3, DATA&ANALYTICS 3, S1NC 3, W1NNER 3.
  - `load_project_bottlenecks_from_model('W1NNER'|'DATA&ANALYTICS'|'BEFINANCE'|'S1NC')` retorna linhas distintas por projeto.
- Evidence (tests/logs/diff):
  - Execução de inspeção em runtime via `python3 - <<'PY' ... import dashboard_full ...`.
  - Verificação de código: filtro estrito por projeto em `dashboard_full.py` (`normalize_text` + igualdade em coluna `Projeto`).
  - `python3 -m py_compile dashboard_full.py api/index.py dash_board_metricas.py`.
  - Smoke test helper `_url_filename_matches_project` com URL correta/incorreta de projeto.

## Current Task (Fluxo Diferente por Projeto)
- [x] Confirmar ponto de cálculo do gargalo por ordem de etapas
- [x] Identificar limitação de mapa único de status para todos os projetos
- [x] Implementar resolução de fluxo por projeto (W1NNER/S1NC/BEFINANCE vs DATA&ANALYTICS)
- [x] Tornar colunas de etapa dinâmicas no CSV exportado
- [x] Validar com checagem de sintaxe e teste rápido de seleção de mapa
- [x] Revisar impacto e documentar resultado

## Specification (Fluxo Diferente por Projeto)
- Objetivo: evitar que o fluxo de DATA&ANALYTICS influencie o gargalo de W1NNER/S1NC/BEFINANCE.
- Escopo:
  - `jira_to_pipeline_csv.py` (seleção de `status_map`, ordem das etapas e colunas do CSV).
- Entregáveis:
  - Mapa padrão de status separado para produtos legados (W1NNER/S1NC/BEFINANCE).
  - Mapa padrão de status para DATA&ANALYTICS preservado.
  - Geração de CSV com colunas de etapa conforme o fluxo ativo.

## Review (Fluxo Diferente por Projeto)
- What was validated:
  - `resolve_status_map(['W1NNR'|'S1NC'|'BF'])` retorna fluxo legado com etapas de code review/test/staging.
  - `resolve_status_map(['DT'])` mantém fluxo de homologação/staging do Data&Analytics.
  - `csv_columns` agora é montado dinamicamente via `stage_order`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile jira_to_pipeline_csv.py dash_board_metricas.py dashboard_full.py api/index.py`
  - Smoke test em Python para `resolve_status_map(...)` com projetos legados, DT e caso misto.

## Current Task (DT Fluxo por Tipo)
- [x] Registrar workflows reais de DT (melhorias vs ad-hoc/bug/incidente)
- [x] Ajustar mapeamento padrão de DT para etapas corretas
- [x] Aplicar seleção de fluxo por linha usando `Tipo de Problema`
- [x] Preservar compatibilidade com override via `JIRA_STATUS_MAP`
- [x] Validar com sintaxe e teste de resumo por etapa

## Review (DT Fluxo por Tipo)
- What was validated:
  - DT padrão passou para etapas: `To Do`, `Discovery`, `Development`, `Tech Review`, `In Validation`, `Improvement`, `Done`.
  - Itens com tipo `Bug`/`Incidente`/`Ad-hoc` usam caminho curto: `To Do`, `Development`, `In Validation`, `Done`.
  - Gargalo por etapa agora aceita `stage_order` por item (row-level) no cálculo.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile jira_to_pipeline_csv.py`
  - Smoke test local com linhas simuladas confirmando que `Discovery/Tech Review/Improvement` contam apenas para melhorias.

## Current Task (Consolidar *_bottlenecks.csv)
- [x] Identificar ponto de consolidação no pipeline de métricas
- [x] Implementar geração de planilha única de gargalos
- [x] Gerar arquivo versionado + arquivo `latest`
- [x] Validar sintaxe do pipeline

## Review (Consolidar *_bottlenecks.csv)
- What was validated:
  - Novo artefato `bottlenecks_consolidado_<timestamp>.xlsx` é gerado com os dados normalizados de gargalo.
  - Cópia estável `bottlenecks_consolidado_latest.xlsx` é atualizada automaticamente.
  - Workbook contém aba consolidada e abas por projeto.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dash_board_metricas.py jira_to_pipeline_csv.py dashboard_full.py api/index.py`
  - Trechos alterados em `dash_board_metricas.py` nas funções `save_consolidated_bottlenecks_workbook` e `process_multiple_csv_files`.

## Current Task (Auditoria de Mudanças do Dia)
- [x] Revisar commits e diffs de hoje nos módulos de dashboard e pipeline
- [x] Confirmar resolução de arquivo de modelo ativo no `dashboard_full.py`
- [x] Registrar regra operacional de consulta obrigatória da memória do projeto

## Review (Auditoria de Mudanças do Dia)
- What was validated:
  - O `dashboard_full.py` resolve o modelo via `_resolve_model_file` e hoje está apontando para `PowerBI_Model_latest.xlsx` em `~/Documents/dados`.
  - A leitura de gargalos está priorizando aba `Fato_Gargalos` e usando fallback de CSV por projeto com proteção de prefixo.
  - Decisão de memória persistida em `tasks/lessons.md` com regra de leitura obrigatória antes de alterações.
- Evidence (tests/logs/diff):
  - `git log --since='2026-02-20 00:00' --name-status`
  - `python3 - <<'PY' ... import dashboard_full as d; print(d.MODEL_FILE) ...`

## Current Task (Garantir Fluxos em Fato_Gargalos)
- [x] Executar pipeline completo e confirmar atualização do `PowerBI_Model_latest.xlsx`
- [x] Corrigir bloqueio por `JIRA_STATUS_MAP` global em exportação multi-projeto
- [x] Reprocessar exportações e validar etapas gravadas por projeto na `Fato_Gargalos`

## Review (Garantir Fluxos em Fato_Gargalos)
- What was validated:
  - Novo modelo gerado: `/Users/rodrigoalmeidadeoliveira/Documents/Dados/PowerBI_Model_20260220_171029.xlsx`.
  - `PowerBI_Model_latest.xlsx` atualizado com `Fato_Gargalos` contendo 34 linhas.
  - Etapas de `W1NNER/S1NC/BEFINANCE` refletindo fluxo legado (triagem/backlog/review/testing/staging/prod).
  - Etapas de `DATA&ANALYTICS` refletindo fluxo de melhorias/adhoc do DT (`To Do`, `Discovery`, `Development`, `Tech Review`, `In Validation`, `Improvement`).
- Evidence (tests/logs/diff):
  - Logs de execução do `run_all_projects_macos.sh` exibindo:
    - 12 etapas para `W1NNER/S1NC/BF`
    - 7 etapas para `DT` + mensagem de fluxo por tipo habilitado
  - Leitura direta da aba `Fato_Gargalos` em `PowerBI_Model_latest.xlsx` após reprocessamento.

## Current Task (Tela Principal com Menu Porfólio/Serviços)
- [x] Definir especificação e plano da navegação principal
- [x] Implementar tela principal com 2 botões (`Porfólio` e `Serviços (Value Stream)`)
- [x] Separar acesso ao `Portfólio` das demais abas (Value Stream)
- [x] Validar sintaxe e revisar diff

## Specification (Tela Principal com Menu Porfólio/Serviços)
- Objetivo: criar uma tela principal que funcione como menu de entrada, com dois botões para abrir `Porfólio` ou `Serviços (Value Stream)`.
- Escopo:
  - `dashboard_full.py` (layout e callbacks de navegação).
- Restrições:
  - Manter o conteúdo atual das abas sem refatoração ampla.
  - `Portfólio` deve ficar acessível separado das demais abas de serviço.
- Critério de aceite:
  - Tela inicial aparece com 2 botões.
  - Botão `Porfólio` abre somente a visão de portfólio.
  - Botão `Serviços (Value Stream)` abre o conjunto das abas operacionais.
  - Usuário consegue voltar ao menu principal.

## Review (Tela Principal com Menu Porfólio/Serviços)
- What was validated:
  - Dashboard passa a abrir em uma tela principal com os botões `Porfólio` e `Serviços (Value Stream)`.
  - Navegação por botões controla o contexto (`home`, `portfolio`, `services`) sem refatorar o conteúdo das abas existentes.
  - `Portfólio` ficou separado do conjunto de abas de serviços (em `services`, as abas exibidas excluem `Portfólio`).
  - Botão `Voltar ao menu principal` foi adicionado para retornar à tela inicial.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - Diff em `dashboard_full.py` (novo menu principal, store de navegação e callbacks de layout/roteamento)

## Current Task (Correção KPI P85 no Painel/Performance)
- [x] Diagnosticar por que `Lead Time P85` continuava em `2.0` no W1NNER
- [x] Corrigir base dos cálculos na tela `Performance do Serviço` (throughput/tempos elegíveis)
- [x] Ajustar `Painel Fluxo` para usar `Cycle Time P85` nas métricas operacionais
- [x] Regenerar modelo e validar números no período reportado

## Review (Correção KPI P85 no Painel/Performance)
- What was validated:
  - Causa-raiz identificada: `LeadTime_Dias` no W1NNER tem cobertura muito baixa no período (`n=2`) por falta de `DataBacklog` em grande parte dos itens; o valor `2.0` era matematicamente correto, mas inadequado como KPI operacional.
  - `dashboard_full.py` foi ajustado para usar `Cycle Time` (`TempoExecucao_Dias`) nas métricas percentílicas operacionais do `Painel Fluxo`:
    - card agora exibe `Cycle Time P85` (antes `Lead Time P85`)
    - previsibilidade/risco de forecasting do painel passaram a usar percentis de cycle time
  - `Performance do Serviço`:
    - `Throughput / semana` agora usa concluídos elegíveis (sem cancelamento)
    - linhas operacionais foram renomeadas para `Média Cycle Time` e `P85% DO CYCLE TIME`
    - `Lead time (Backlog→Done)` permanece separado e mostra `—` quando sem amostra suficiente
  - Modelo regenerado em `/Users/rodrigoalmeidadeoliveira/Documents/dados/PowerBI_Model_20260223_132346.xlsx` e `PowerBI_Model_latest.xlsx` atualizado.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py dash_board_metricas.py`
  - Execução completa: `DATA_FOLDER=/Users/rodrigoalmeidadeoliveira/Documents/dados FLOW_PMO_DATA_DIR=/Users/rodrigoalmeidadeoliveira/Documents/dados python3 dash_board_metricas.py`
  - Validação local no `dashboard_full.py` (W1NNER, 2026-01-01 a 2026-02-23):
    - `LeadTime_Dias`: `n=2`, `P85=2`
    - `TempoExecucao_Dias`: `n=167`, `P85=25`
    - `Throughput / semana` corrigido (sem cancelados): semana `2026-02-16` caiu de `146` para `28`

## Current Task (Lead Time com Filtro de Etapas)
- [x] Reverter telas operacionais para Lead Time (não Cycle Time)
- [x] Implementar filtro configurável de etapas de compromisso (colunas downstream)
- [x] Calcular Lead Time factual a partir das etapas selecionadas até finalização
- [x] Validar cobertura amostral e percentis no W1NNER

## Review (Lead Time com Filtro de Etapas)
- What was validated:
  - `dashboard_full.py` voltou a usar `Lead Time` nas telas `Painel Fluxo` e `Performance do Serviço`.
  - Novo filtro `Etapas Lead Time (Comprometimento)` (multi-select) foi adicionado ao topo; opções são carregadas do CSV downstream do projeto selecionado.
  - O cálculo usa o CSV downstream factual por item:
    - início = menor data entre as etapas selecionadas
    - fim = etapa final (`Itens concluídos`/`Done`)
    - `LeadTime_Selected_Dias` é aplicado nas métricas de Lead Time (com exclusão de cancelados via filtro elegível).
  - Com isso, o usuário pode escolher explicitamente quais colunas representam “comprometimento”.
  - W1NNER mostrou a causa real da inconsistência anterior:
    - se usar apenas `Backlog`, a amostra continua `n=2` (`P85=2`)
    - ao incluir `In progress`, a amostra sobe para `n=165+` e o `P85` passa a `25`
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - Validação local (W1NNER, 2026-01-01 a 2026-02-23):
    - `['Backlog'] => n=2, P85=2`
    - `['In progress'] => n=165, P85=25`
    - `['Backlog','Triagem','Ready to Start','In progress'] => n=169, P85=25`

## Current Task (Auditoria do Filtro de Etapas nas Abas)
- [x] Verificar aplicação do filtro em `Performance do Serviço`
- [x] Verificar aplicação do filtro em `Painel Fluxo`
- [x] Verificar aplicação do filtro em `Fluxo`
- [x] Corrigir aba `Fluxo` para aplicar `LeadTime_Selected_Dias` nos KPIs de Lead Time

## Review (Auditoria do Filtro de Etapas nas Abas)
- What was validated:
  - `Performance do Serviço`: aplica o filtro de etapas corretamente via `apply_selected_lead_time_metric(...)` e `compute_weekly_service_metrics(..., lead_time_col='LeadTime_Selected_Dias')`.
  - `Painel Fluxo`: aplica o filtro de etapas corretamente em `df_signal_base` e `df_threshold_base`, usando `LeadTime_Selected_Dias` para `Lead Time P85`, previsibilidade e thresholds semanais.
  - `Fluxo`: **não aplicava** o filtro de etapas nos KPIs de Lead Time antes da correção; foi ajustado para anexar `LeadTime_Selected_Dias` e calcular `Lead Time Médio/P50/P85` com a seleção ativa.
  - Na aba `Fluxo`, gráficos de `Cycle Time` e ranking de gargalos por etapa continuam independentes do filtro de etapas de Lead Time (com aviso explícito na UI).
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - Validação comparativa W1NNER (2026-01-01 a 2026-02-23):
    - `['Backlog']` -> `Performance/Painel P85=2 (n=2)` e `Fluxo KPI P85=2 (n=2)`
    - `['In progress']` -> `Performance/Painel P85=25 (n=165)` e `Fluxo KPI P85=25 (n=165)`

## Current Task (Lead Time na Aba Fluxo + Resumo Visual)
- [x] Substituir histograma/bandas de Cycle Time por Lead Time na aba `Fluxo`
- [x] Reaproveitar `LeadTime_Selected_Dias` (respeitando filtro de etapas)
- [x] Adicionar resumo visual da seleção ativa de etapas nas abas `Performance`, `Painel` e `Fluxo`
- [x] Validar renderização local e sintaxe

## Review (Lead Time na Aba Fluxo + Resumo Visual)
- What was validated:
  - Aba `Fluxo` agora exibe:
    - histograma `Distribuição do Lead Time (dias)`
    - tabela `Bandas Percentílicas Exatas (Lead Time)`
    usando `LeadTime_Selected_Dias` (filtro de etapas aplicado).
  - Resumo visual da seleção ativa de Lead Time foi adicionado no topo das abas:
    - `Performance do Serviço`
    - `Painel Fluxo`
    - `Fluxo`
  - O resumo mostra:
    - etapas de início selecionadas (chips)
    - etapa final detectada (ex.: `Itens concluídos`)
    - indicação de seleção explícita vs padrão automático.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `render_tab('services', tab, ..., 'W1NNER', ..., ['In progress'], ...)` retornando `Div` para `tab-performance`, `tab-painel-3x3` e `tab-fluxo`

## Current Task (Painel 100% sensível ao filtro de etapas)
- [x] Revisar KPIs/gráficos do `Painel` que ainda usavam semântica antiga de entrada
- [x] Aplicar `LeadStart_Selected` às métricas de compromisso/chegada do painel
- [x] Ajustar `Tempo para Commit` para medir `DataBacklog -> LeadStart_Selected` (sem fallback que mascara filtro)
- [x] Validar diferenças entre seleções `Backlog` e `In progress`

## Review (Painel 100% sensível ao filtro de etapas)
- What was validated:
  - No `tab-painel-3x3`, o filtro de etapas agora afeta também:
    - chegadas semanais / média de chegada (usadas em pressão e vazão relativa)
    - card `Entrada vs Saída` (agora `Compromisso vs Saída`)
    - `Demanda vs Capacidade`
    - `Taxa de Comprometimento`
    - `Tempo para Commit (P85)` via `DataBacklog -> LeadStart_Selected`
  - Removido fallback de `TempoBacklog_Dias` no `Tempo para Commit` para não mascarar a seleção de etapas.
  - Métricas que continuam independentes por conceito:
    - `WIP`, `WIP Age`, `Throughput` (baseados em execução/conclusão)
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - W1NNER (2026-01-01 a 2026-02-23):
    - `['Backlog']`: `lead_p85=2`, `arrivals/compromisso=180`, `commit_n=37`
    - `['In progress']`: `lead_p85=25`, `arrivals/compromisso=179`, `commit_n=0` (sem base backlog->compromisso para essa seleção)

## Current Task (WIP/WIP Age sensíveis ao filtro no Painel)
- [x] Aplicar início selecionado (`LeadStart_Selected`) às contagens de WIP semanais e WIP atual
- [x] Aplicar início selecionado ao cálculo de WIP Age no painel
- [x] Validar impacto comparativo por seleção de etapas

## Review (WIP/WIP Age sensíveis ao filtro no Painel)
- What was validated:
  - `tab-painel-3x3` passou a calcular `WIP` e `WIP Age` a partir do início selecionado do fluxo (`LeadStart_Selected`), não mais fixo em `DataInProgress`.
  - `Lead Time P85` do painel continua corretamente dependente do filtro; quando parece estável, normalmente é porque `In progress` ainda está incluído nas etapas selecionadas e domina a primeira data disponível dos itens.
  - Exemplo W1NNER (2026-01-01 a 2026-02-23):
    - `['Backlog']` -> `Lead P85=2`, `WIP Age≈133.9`
    - `['In progress']` -> `Lead P85=25`, `WIP Age≈29.6`
    - `WIP` (contagem no fim) pode permanecer igual no mesmo período se todos os itens vivos já tiverem cruzado ambas as etapas antes da data final.
  - Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - Validação local comparativa (`Backlog` vs `In progress`) confirmando alteração em `Lead Time P85` e `WIP Age`

## Current Task (Corrigir Datas de Etapa no CSV Local W1NNER)
- [x] Diagnosticar divergência de WIP/WIP Age com CSVs do Actionable
- [x] Corrigir exportador para suportar datas de etapa por última entrada (`latest`)
- [x] Validar alinhamento com Actionable em amostra W1NNER
- [x] Regenerar CSV local `w1nner-downstream-20260223-data.csv` e `latest`

## Review (Corrigir Datas de Etapa no CSV Local W1NNER)
- What was validated:
  - Causa raiz das datas antecipadas: exportador usava **primeira entrada histórica por etapa**, enquanto o Actionable (para o cenário analisado) reflete **última entrada** nas etapas do workflow selecionado.
  - `jira_to_pipeline_csv.py` agora suporta modo de datas por etapa (`first|latest`) e passou a usar `latest` por padrão (`JIRA_STATUS_DATE_MODE`, default `latest`).
  - Comparação com `Analytics-filtered_2026-02-23 (1).csv`:
    - `WIP` Actionable = `43`
    - CSV W1NNER regenerado (legado + latest) = `43` (mesma regra)
    - `WIP Age` médio ficou praticamente alinhado (`~8.7` local vs `~8.53` Actionable) no CSV regenerado
  - Divergência residual de 1 item em uma comparação intermediária foi atribuída a diferença de snapshot (`W1NNR-2158` vs `W1NNR-2150`), não à regra de cálculo.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile jira_to_pipeline_csv.py`
  - Teste unitário local da função `extract_first_status_dates(..., date_mode='first|latest')`
  - Extração real:
    - `/tmp/w1nner-downstream-legacy-latestdates.csv`
    - `/Users/rodrigoalmeidadeoliveira/Documents/dados/w1nner-downstream-20260223-data.csv`
    - `/Users/rodrigoalmeidadeoliveira/Documents/dados/w1nner-downstream-latest-data.csv`

## Current Task (Aba Lead Time Dedicada no dashboard_app)
- [x] Criar nova aba `Lead Time` no `dashboard_app.py`
- [x] Implementar gráfico de distribuição de Lead Time com curva acumulada e linhas de percentis/média
- [x] Implementar gráfico temporal de Lead Time com média e média móvel
- [x] Validar sintaxe e registrar review/evidências

## Specification (Aba Lead Time Dedicada no dashboard_app)
- Objetivo: concentrar visualizações de Lead Time em uma aba própria, inspirada no layout do anexo (distribuição + visão temporal).
- Escopo:
  - `dashboard_app.py`
- Decisões:
  - Usar `Análise Eficiência` como base item a item para distribuição de `Lead Time (dias)`.
  - Usar `Tendências Completas` como base temporal semanal para linha de `Lead Time` e `Lead Time Médio (4s)` (média móvel).
  - Exibir linhas horizontais de percentis e média usando `Adv - Estabilidade` quando disponível (fallback para cálculo local quando necessário).
- Critério de aceite:
  - Nova aba aparece na navegação principal.
  - Aba renderiza 2 gráficos de Lead Time para o projeto selecionado.
  - Gráficos exibem percentis/média e média móvel conforme disponibilidade dos dados.

## Review (Aba Lead Time Dedicada no dashboard_app)
- What was validated:
  - Nova aba `Lead Time` adicionada no `dashboard_app.py` e renderizada via `tabs-main`.
  - Aba exibe 2 gráficos:
    - distribuição de Lead Time com barras de frequência + curva acumulada (%)
    - tendência temporal semanal com `Lead Time` e `Lead Time Médio (4s)` (média móvel)
  - Linhas de referência foram adicionadas para `P50`, `P75`, `P85`, `P95` e `Média`.
  - Percentis/média usam `Adv - Estabilidade` quando disponível e fazem fallback para cálculo local na base `Análise Eficiência`.
  - Tratamento de vazio implementado com figuras de mensagem (quando projeto não tem amostra de Lead Time item a item).
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_app.py`
  - Smoke test local do callback `update_lead_time_graphs(...)`:
    - `BEFINANCE`: tendência renderizada e distribuição vazia tratada corretamente
    - `DATA&ANALYTICS`: `dist_traces=2`, `trend_traces=2`
- Suggested commit message:
  - `feat(dashboard-app): add dedicated lead time tab with distribution and trend charts`


