# Task Plan

## Current Task (Dashboard PM: gráfico backlog restante vs trabalho executado por pessoa)
- [x] Mapear métricas existentes para leitura proxy (`executado` vs `backlog restante estimado`)
- [x] Criar novo gráfico por pessoa com separação visual de executado, restante e excedente
- [x] Validar sintaxe/import e registrar review/evidências

## Specification (Dashboard PM: gráfico backlog restante vs trabalho executado por pessoa)
- Objetivo: adicionar um gráfico na seção de execução por pessoa que traduza a leitura para `trabalho executado` vs `backlog restante`, sem perder a distinção entre estimativa normalizada e horas úteis executadas.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Novo gráfico aparece na aba de análise de execução/pessoas.
  - Gráfico mostra ao menos duas partes por pessoa: executado e backlog restante estimado.
  - Quando executado > estimado, excedente é exibido separadamente (sem mascarar a divergência).
  - Texto da tela deixa explícito que a leitura é um proxy (não saldo real de backlog).

## Review (Dashboard PM: gráfico backlog restante vs trabalho executado por pessoa)
- What was validated:
  - Foi adicionado um gráfico empilhado por pessoa com três componentes: `Trabalho executado`, `Backlog restante (estimado)` e `Executado acima da carga estimada` (quando aplicável).
  - O gráfico usa merge das métricas existentes (`exec_by_person` + `exec_norm_by_person`) para criar uma leitura proxy sem alterar os cálculos-base.
  - A seção do dashboard recebeu texto explicando a semântica de proxy para evitar interpretação como saldo real de backlog do Jira.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_process_mining.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python -c "import dashboard_process_mining; print('import ok')"`
  - `git diff -- dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `feat(dashboard): add backlog restante vs trabalho executado proxy chart by person`

## Current Task (Vercel: Process Mining por URL fixa única)
- [x] Registrar escopo e critérios para consumo do relatório de process mining por env única
- [x] Implementar suporte a `FLOW_PMO_PROCESS_MINING_REPORT_URL` no `dashboard_full.py`
- [x] Implementar suporte a `FLOW_PMO_PROCESS_MINING_REPORT_URL` no `dashboard_process_mining.py`
- [x] Atualizar documentação de deploy e validar sintaxe/import

## Specification (Vercel: Process Mining por URL fixa única)
- Objetivo: permitir que os dashboards consumam o relatório de Process Mining por uma única variável de ambiente (`FLOW_PMO_PROCESS_MINING_REPORT_URL`), evitando configuração por arquivo.
- Escopo:
  - `dashboard_full.py`
  - `dashboard_process_mining.py`
  - `DEPLOY_VERCEL.md`
  - `tasks/todo.md`
- Critério de aceite:
  - Se `FLOW_PMO_PROCESS_MINING_REPORT_URL` estiver definida, os dashboards baixam e usam esse `.xlsx` como fonte de Process Mining.
  - Se a env não estiver definida, o comportamento atual de busca local por arquivos `w1nner-process-mining-*.xlsx` permanece.
  - Documentação de deploy lista explicitamente a nova variável com exemplo de uso.

## Review (Vercel: Process Mining por URL fixa única)
- What was validated:
  - `dashboard_full.py` passou a priorizar `FLOW_PMO_PROCESS_MINING_REPORT_URL` para obter o `.xlsx` de Process Mining, com cache local em `/tmp/flow-pmo-models`.
  - `dashboard_process_mining.py` recebeu o mesmo comportamento, mantendo consistência entre dashboard principal e sandbox de Process Mining.
  - Na ausência da env, ambos preservam o fallback atual por varredura local (`w1nner-process-mining-*.xlsx`).
  - `DEPLOY_VERCEL.md` foi atualizado com a nova variável e exemplo de valor para `w1nner-process-mining-latest.xlsx`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py dashboard_process_mining.py`
  - `python3 - <<'PY' ... import dashboard_full/dashboard_process_mining ... PY`
  - `rg -n "FLOW_PMO_PROCESS_MINING_REPORT_URL|_download_process_mining_report_from_url" dashboard_full.py dashboard_process_mining.py DEPLOY_VERCEL.md`
  - `git diff -- dashboard_full.py dashboard_process_mining.py DEPLOY_VERCEL.md tasks/todo.md`
- Suggested commit message:
  - `feat(vercel): support process mining report from single FLOW_PMO_PROCESS_MINING_REPORT_URL`

## Current Task (Process Mining: gerar artefatos latest com nome fixo)
- [x] Registrar escopo e critérios para geração `latest` no exportador de process mining
- [x] Implementar no `process_mining_jira.py` a atualização automática dos arquivos `-latest` (xlsx/csv/pm4py imagens)
- [x] Validar sintaxe/CLI e registrar review com evidências

## Specification (Process Mining: gerar artefatos latest com nome fixo)
- Objetivo: garantir que o exportador de process mining sempre gere aliases estáveis com nome fixo (`<prefix>-latest...`), facilitando publicação em storage/CDN e consumo pelo dashboard em produção.
- Escopo:
  - `process_mining_jira.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Após execução, além dos arquivos com timestamp, existe `w1nner-process-mining-latest.xlsx`.
  - Para cada dataset CSV exportado, existe também a versão `w1nner-process-mining-latest-<dataset>.csv`.
  - Para cada imagem PM4Py gerada, existe também o alias `w1nner-process-mining-latest-<sufixo>.png`.
  - O comportamento atual (arquivos versionados por timestamp) permanece inalterado.

## Review (Process Mining: gerar artefatos latest com nome fixo)
- What was validated:
  - O `write_outputs(...)` agora mantém arquivos com timestamp e também atualiza aliases fixos `-latest`.
  - Foi adicionado `w1nner-process-mining-latest.xlsx` após a geração do Excel timestampado.
  - Todos os CSVs exportados agora também possuem cópia `w1nner-process-mining-latest-<dataset>.csv`.
  - Imagens PM4Py geradas (`-pm4py-*.png`) também recebem cópias com prefixo `w1nner-process-mining-latest`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile process_mining_jira.py`
  - `python3 process_mining_jira.py --help`
  - Execução funcional com CSV sintético:
    - `python3 process_mining_jira.py --input <tmp>/in.csv --out-dir <tmp> --pm4py-align-max-cases 0`
    - `ls <tmp> | rg "w1nner-process-mining-latest"` (confirmou `latest.xlsx`, CSVs e PNGs)
  - `git diff -- process_mining_jira.py tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): generate stable latest aliases for excel/csv/pm4py artifacts`

## Current Task (Dashboard Full: relatórios Process Mining da extração)
- [x] Registrar escopo e critérios de aceite para ampliar relatórios de Process Mining no `dashboard_full.py`
- [x] Expandir leitura do workbook de Process Mining para abas adicionais produzidas pela extração
- [x] Exibir, na aba `Process Mining Jira`, os relatórios operacionais principais vistos no PDF (KPIs de horas, variantes, DFG/top arestas e conformidade PM4Py)
- [x] Validar sintaxe/smoke test e registrar review com evidências

## Specification (Dashboard Full: relatórios Process Mining da extração)
- Objetivo: exibir na aba `Process Mining Jira` do `dashboard_full.py` os relatórios já produzidos por `process_mining_jira.py`, aproximando a visão do dashboard dedicado (`dashboard_process_mining.py`/PDF) sem depender de arquivos estáticos.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - `load_w1nner_process_mining_report()` passa a carregar abas extras do relatório (`HorasPessoaResumo`, `HorasPessoaStatus`, `VariantesTop`, `EventosFiltrados`, `PM4PyDFGEdges`, `PM4PyDFGPerfEdges`, `PM4PyTBRResumo`, `PM4PyTBRCasos`, `PM4PyAlignResumo`, `PM4PyAlignCasos`, `PM4PyAlignTopMoves`).
  - A aba `tab-process-mining-jira` exibe KPIs de horas e cobertura técnica além dos KPIs atuais.
  - A aba passa a exibir pelo menos gráficos/tabelas de variantes, DFG (top arestas) e conformidade PM4Py (TBR/Align quando disponível).
  - Filtros de período e responsável continuam aplicados sem quebrar a renderização.

## Review (Dashboard Full: relatórios Process Mining da extração)
- What was validated:
  - `load_w1nner_process_mining_report()` foi expandido para carregar todas as abas de relatório produzidas pelo `process_mining_jira.py`, incluindo blocos operacionais e PM4Py.
  - A aba `tab-process-mining-jira` passou a incorporar KPIs adicionais alinhados ao relatório do PDF: horas de execução no período, horas no fluxo (proxy), média de horas por evento, cobertura técnica, commits e PRs Bitbucket.
  - Foram adicionadas visualizações e tabelas para `VariantesTop`, `PM4PyDFGEdges`, `PM4PyDFGPerfEdges`, `PM4PyTBRResumo`/`PM4PyTBRCasos` e `PM4PyAlign*`, além de tabelas de horas por pessoa/status.
  - O filtro de período/responsável foi estendido para os novos datasets (eventos, horas e casos PM4Py) mantendo comportamento consistente.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... d.render_tab('services','tab-process-mining-jira',...) ... print(token in str(node)) ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): expand dashboard_full tab with extraction reports and pm4py views`

## Current Task (Documentação: Process Mining e Dashboards Criados)
- [x] Registrar plano e escopo da atualização de documentação
- [x] Atualizar `ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md` com seção de process mining e inventário de dashboards
- [x] Atualizar `INDICE_CENTRAL.md` com navegação rápida dos dashboards criados
- [x] Validar alterações por busca textual e diff
- [x] Registrar review com evidências e sugestão de commit

## Specification (Documentação: Process Mining e Dashboards Criados)
- Objetivo: atualizar a documentação do projeto para refletir explicitamente os componentes de Process Mining e o conjunto atual de dashboards criados.
- Escopo:
  - `ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md`
  - `INDICE_CENTRAL.md`
  - `tasks/todo.md`
- Critério de aceite:
  - A documentação descreve `process_mining_jira.py` e `dashboard_process_mining.py`.
  - A documentação lista os dashboards existentes e seu propósito.
  - O índice central passa a incluir uma seção de navegação para dashboards do projeto.

## Review (Documentação: Process Mining e Dashboards Criados)
- What was validated:
  - `ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md` passou a documentar explicitamente o pipeline de process mining (`process_mining_jira.py`) e o dashboard dedicado (`dashboard_process_mining.py`).
  - A seção de dashboards foi reorganizada para refletir os dashboards criados atualmente (`dashboard_full.py`, `dashboard_process_mining.py`, `dashboard_app.py`), incluindo o `One Page Report` no dashboard principal.
  - O inventário de funcionalidades foi atualizado para `02/03/2026` e ganhou seção específica de Process Mining.
  - `INDICE_CENTRAL.md` recebeu seção “Dashboards do Projeto” com foco, arquivo e comando de execução para cada dashboard.
- Evidence (tests/logs/diff):
  - `rg -n "process_mining_jira|dashboard_process_mining|Dashboards Interativos|One Page Report|12.7 Process Mining" ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md INDICE_CENTRAL.md`
  - `git diff -- ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md INDICE_CENTRAL.md tasks/todo.md`
- Suggested commit message:
  - `docs: update architecture and index with process mining flow and created dashboards`

## Current Task (Estatística Descritiva: Cpk e Nível Sigma)
- [x] Registrar plano e escopo para incluir Cpk e Nível Sigma na aba de estatística descritiva
- [x] Implementar entrada de limites de especificação (LSL/USL) e cálculo de Cpk/Six Sigma
- [x] Validar sintaxe e smoke test da aba `Estatística Descritiva`
- [x] Registrar review com evidências e sugestão de commit

## Specification (Estatística Descritiva: Cpk e Nível Sigma)
- Objetivo: adicionar na aba `Estatística Descritiva` o cálculo de Cpk e Nível Sigma (curto e longo prazo) com base em dados e limites de especificação informados.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - A aba exibe campos para `LSL` e `USL`.
  - Com limites válidos e dados de Lead Time disponíveis, o dashboard calcula `CPU`, `CPL`, `Cpk`, `Sigma (curto prazo)` e `Sigma (longo prazo, deslocamento 1.5σ)`.
  - A aba exibe interpretação qualitativa do Cpk.
  - Quando dados/limites forem inválidos, a interface mostra mensagem clara sem quebrar o restante da aba.

## Review (Estatística Descritiva: Cpk e Nível Sigma)
- What was validated:
  - A aba `tab-estatistica` recebeu bloco de capabilidade com campos `LSL` e `USL` e cálculo de `CPU`, `CPL`, `Cpk`, `Nível Sigma (curto prazo)` e `Nível Sigma (longo prazo)`.
  - O cálculo foi encapsulado em `compute_process_capability_metrics(...)`, com validações para amostra mínima, limites ausentes/inválidos e desvio padrão zero.
  - A interpretação do Cpk foi adicionada na própria tabela (`Incapaz`, `Apenas capaz`, `Bom`, `Classe Seis Sigma`).
  - Em cenários sem limites ou com dados insuficientes, a aba mostra mensagem clara e preserva os demais blocos de estatística.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... render_tab(... tab='tab-estatistica' ... 9.7, 10.3) ... print('has_cpk_label', ...) ... PY`
  - `python3 - <<'PY' ... render_tab(... tab='tab-estatistica' ... None, None) ... print('msg_limite', ...) ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(estatistica): add Cpk and six sigma calculations with LSL/USL inputs`

## Current Task (Performance do Serviço: visão consolidada dinâmica por filtros)
- [x] Registrar plano e escopo da visão consolidada dinâmica
- [x] Remover valores hardcoded e calcular KPIs com base no período e filtros ativos
- [x] Validar sintaxe e smoke test da aba `Performance do Serviço`
- [x] Registrar review com evidências e sugestão de commit

## Specification (Performance do Serviço: visão consolidada dinâmica por filtros)
- Objetivo: tornar dinâmico o bloco "Visão consolidada: planejamento do quarter x execução real" da aba `Performance do Serviço`, refletindo os filtros ativos e o período selecionado.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O bloco não utiliza mais números estáticos.
  - Cards e bullets mudam conforme filtros (`projeto`, `tipo`, `classe_servico`, `responsavel`) e período (`start_date`, `end_date`).
  - O período exibido no texto do bloco reflete o intervalo selecionado no dashboard.
  - Código permanece válido em sintaxe/import.

## Review (Performance do Serviço: visão consolidada dinâmica por filtros)
- What was validated:
  - O bloco "Visão consolidada: planejamento do quarter x execução real" deixou de usar `consolidated_inputs` fixo e passou a calcular valores do recorte filtrado.
  - Foram calculados dinamicamente: itens planejados no período, entregues no período, em andamento, horas executadas (via `TempoExecucao_Dias`), estimado do quarter (por Story Points/histórico com fallback), consumo do estimado, média h/dev/dia e bloqueios.
  - O texto de período agora usa o intervalo selecionado (`dd/mm a dd/mm`) em vez de string fixa.
  - As bullets de risco foram ajustadas para refletir os valores calculados no recorte.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... d.render_tab(main_view='services', tab='tab-performance', ... ) ... print(type(node).__name__) ... PY`
  - `rg -n "consolidated_inputs|01/01 a 25/02|14947|6263|253|169|84|bloqueios" dashboard_full.py`
- Suggested commit message:
  - `feat(dashboard): make performance consolidated section dynamic by active filters and period`

## Current Task (Dashboard Full: One Page dinâmico por filtros)
- [x] Substituir renderização estática do One Page por geração dinâmica no `tab-one-page`
- [x] Calcular KPIs, gargalos, dimensões, achados, equipe e recomendações com base nos filtros ativos
- [x] Validar sintaxe/import e smoke test de renderização do componente

## Specification (Dashboard Full: One Page dinâmico por filtros)
- Objetivo: fazer o One Page Report refletir dinamicamente os dados coletados e os filtros aplicados no dashboard.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Aba `One Page Report` continua disponível na navegação de serviços.
  - Conteúdo deixa de depender de HTML estático e passa a ser calculado em tempo real pelo callback.
  - Métricas e blocos reagem a `projeto`, `período`, `tipo`, `classe de serviço` e `responsável`.
  - Quando Process Mining não estiver disponível no projeto filtrado, o relatório permanece funcional com fallback para dados Jira/Bitbucket.

## Review (Dashboard Full: One Page dinâmico por filtros)
- What was validated:
  - `tab-one-page` agora usa `build_dynamic_one_page_report(...)` no callback, eliminando leitura de arquivo HTML estático.
  - Foi implementado design system e regras de semáforo para KPIs e dimensões (`ONE_PAGE_THEME`, `_one_page_status_by_threshold`, cards/barras dinâmicos).
  - O relatório monta dinamicamente:
    - Health strip (throughput, pressão, lead time, conformidade, cobertura técnica, retrabalho);
    - Ranking de gargalos (com fallback model/csv quando necessário);
    - Indicadores por dimensão;
    - Achados priorizados;
    - Composição da equipe e atividade técnica;
    - Recomendações por horizonte.
  - Fallback de dados foi mantido para contextos sem Process Mining (projetos além de W1NNER) sem quebrar a renderização.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... import dashboard_full as d; d.build_dynamic_one_page_report('W1NNER', ...); print(type(...).__name__) ... PY`
  - `rg -n "build_dynamic_one_page_report|tab-one-page|ONE_PAGE_THEME" dashboard_full.py`
  - `git diff -- dashboard_full.py`
- Suggested commit message:
  - `feat(dashboard): make one-page report dynamic based on active filters and collected data`

## Current Task (Dashboard Full: incluir aba One Page Report)
- [x] Adicionar aba `One Page Report` na navegação de serviços
- [x] Implementar renderização do HTML do one-page report dentro do dashboard
- [x] Aplicar fallback quando arquivo não existir e validar sintaxe

## Specification (Dashboard Full: incluir aba One Page Report)
- Objetivo: incorporar o one-page report no `dashboard_full.py` como uma aba nativa do dashboard.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Nova aba aparece no menu de serviços com label `One Page Report`.
  - Ao abrir a aba, o dashboard carrega um HTML de report em `artifacts/` (priorizando arquivo do projeto selecionado).
  - Se o arquivo não existir, o usuário vê mensagem clara de indisponibilidade em vez de erro de execução.
  - Código permanece válido em sintaxe.

## Review (Dashboard Full: incluir aba One Page Report)
- What was validated:
  - A aba `One Page Report` foi adicionada em `SERVICE_TABS` e passa a aparecer no menu principal de serviços.
  - Foi criada a função `resolve_one_page_report_file(project_key)` para resolver arquivo por projeto com fallback (`one-page-report-<projeto>.html`, `one-page-report-w1nner.html`, `one-page-report.html`), com suporte a `FLOW_PMO_ONE_PAGE_REPORT_FILE` e `FLOW_PMO_ONE_PAGE_REPORT_DIR`.
  - O `render_tab` ganhou o branch `tab-one-page` que carrega o HTML via `html.Iframe(srcDoc=...)` e trata cenários de arquivo ausente/erro de leitura com mensagens claras.
  - A sintaxe do arquivo permaneceu válida.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `rg -n "tab-one-page|One Page Report|resolve_one_page_report_file|One Page carregado" dashboard_full.py`
  - `git diff -- dashboard_full.py`
- Suggested commit message:
  - `feat(dashboard): add one-page report tab to dashboard_full with project-based html fallback`

## Current Task (One Page Report W1NNER: aderência ao guia executivo)
- [x] Registrar plano e especificação do one-page report
- [x] Ajustar `one-page-report-w1nner.html` para aderência aos blocos e regras visuais do guia
- [x] Validar estrutura final do HTML e registrar evidências

## Specification (One Page Report W1NNER: aderência ao guia executivo)
- Objetivo: produzir um one-page report executivo do projeto W1NNER seguindo as orientações do documento anexo.
- Escopo:
  - `tasks/todo.md`
  - `artifacts/one-page-report-w1nner.html`
- Critério de aceite:
  - Estrutura final contém os 6 blocos definidos (header, health strip, painéis duplos, recomendações e footer).
  - Health strip possui 6 KPIs com semaforização visual consistente.
  - Painéis de gargalos, dimensões, achados, equipe e recomendações refletem o padrão de conteúdo orientado no guia.
  - Arquivo HTML final válido para abertura local e exportação/impressão.

## Review (One Page Report W1NNER: aderência ao guia executivo)
- What was validated:
  - O relatório foi criado em `artifacts/one-page-report-w1nner.html` com os 6 blocos do guia (header, health strip, dois painéis duplos, recomendações e footer).
  - O health strip contém 6 KPIs com semaforização visual por barra superior e valor em destaque.
  - Foram adicionados ajustes de responsividade para manter legibilidade em desktop e mobile.
  - Conteúdo de gargalos, dimensões, achados, equipe e recomendações ficou alinhado ao formato executivo do documento de orientação.
- Evidence (tests/logs/diff):
  - `rg -n "HEADER|HEALTH STRIP|Ranking de Gargalos|Indicadores por Dimensão|Achados Principais|Composição e Carga da Equipe|Recomendações Priorizadas|FOOTER" artifacts/one-page-report-w1nner.html`
  - `python3 - <<'PY' ... HTMLParser ... print('html_parse_ok') ... print('health_items', text.count('class=\"health-item')) ... PY`
  - `git diff -- tasks/todo.md artifacts/one-page-report-w1nner.html`
- Suggested commit message:
  - `feat(report): create w1nner one-page executive report following flow-pmo guidelines`

## Current Task (Dashboard Process Mining: erro de chunk async-graph)
- [x] Diagnosticar erro `Loading chunk 746 failed` no `dcc.Graph` do dashboard process mining
- [x] Ajustar inicialização do app para evitar falha de carregamento assíncrono do `async-graph.js`
- [x] Validar sintaxe/import e registrar evidências

## Specification (Dashboard Process Mining: erro de chunk async-graph)
- Objetivo: eliminar falhas recorrentes de carregamento do chunk JS do `dcc.Graph` no dashboard de process mining (`http://127.0.0.1:8051`).
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - App inicia com carregamento local de componentes e sem dependência de lazy chunk para `dcc.Graph`.
  - Execução local reduz risco de mismatch de assets em hot reload.
  - Script permanece válido em sintaxe/import.

## Review (Dashboard Process Mining: erro de chunk async-graph)
- What was validated:
  - `dashboard_process_mining.py` passou a iniciar o Dash com `serve_locally=True` e `eager_loading=True`, eliminando dependência de chunk assíncrono (`dash/dcc/async-graph.js`) durante renderização inicial.
  - Execução local foi ajustada para `dev_tools_hot_reload=False`, reduzindo risco de inconsistência de assets JS durante recarregamento em desenvolvimento.
  - Import/sintaxe mantidos válidos.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_process_mining.py`
  - `python3 - <<'PY' ... import dashboard_process_mining as d; print(d.app.config.get('eager_loading')); print(d.app.config.get('serve_locally')) ... PY`
  - `git diff -- dashboard_process_mining.py`
- Suggested commit message:
  - `fix(process-mining): prevent dcc graph async chunk load failures in local dash app`


## Current Task (Bitbucket logs: rastreamento de work items)
- [x] Adicionar extração de chaves de work item (`PROJ-123`) no export de commits
- [x] Adicionar extração de chaves de work item (`PROJ-123`) no export de pull requests
- [x] Adicionar extração de chaves de work item (`PROJ-123`) no export de pipelines
- [x] Validar sintaxe/help e registrar evidências

## Specification (Bitbucket logs: rastreamento de work items)
- Objetivo: permitir correlação entre logs do Bitbucket e tarefas/issues/bugs do dashboard via chaves de work item.
- Escopo:
  - `bitbucket_export.py`
  - `tasks/todo.md`
- Critério de aceite:
  - CSVs de commits, PRs e pipelines passam a conter `work_item_keys` e `primary_work_item_key`.
  - Extração usa regex robusta para padrões tipo `W1NNR-2154` em mensagem/título/branch.
  - Script permanece válido em sintaxe e `--help`.

## Review (Bitbucket logs: rastreamento de work items)
- What was validated:
  - `bitbucket_export.py` agora extrai chaves de work item via regex (`[A-Z][A-Z0-9]+-\\d+`) e adiciona `work_item_keys` + `primary_work_item_key` no CSV de commits.
  - O CSV de PR passa a incluir as mesmas colunas de rastreamento usando `title`, `source_branch` e `destination_branch`.
  - O CSV de pipelines passa a incluir as mesmas colunas usando `ref_name`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile bitbucket_export.py`
  - `python3 - <<'PY' ... extract_work_item_keys(...) + export_* com payload mock ... PY`
  - `git diff -- bitbucket_export.py tasks/todo.md`
- Suggested commit message:
  - `feat(integration): add work-item key extraction to bitbucket commit/pr/pipeline exports`

## Current Task (Dashboard Full: métricas de contribuições Bitbucket em CSV)
- [x] Expandir export de PR para incluir revisores e contagens de aprovação/reprovação no CSV
- [x] Calcular métricas por pessoa no `dashboard_full.py` (PRs abertos, aprovações, reprovações, PRs declinados, commits)
- [x] Exibir painel e ranking dessas métricas na aba `Performance do Serviço`
- [x] Validar sintaxe/execução local e registrar review com evidências

## Specification (Dashboard Full: métricas de contribuições Bitbucket em CSV)
- Objetivo: apresentar no `dashboard_full.py` as métricas de contribuição solicitadas usando arquivos CSV do Bitbucket.
- Escopo:
  - `bitbucket_export.py`
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - CSV de PR passa a incluir dados suficientes para contar aprovações/reprovações por revisor.
  - Dashboard mostra ranking por pessoa com as colunas: `PRs abertos`, `Aprovações`, `Reprovações`, `PRs declinados (autor)`, `Commits`.
  - O recorte respeita projeto e período filtrados na aba.
  - Não quebra leitura de CSV legado sem as novas colunas.

## Review (Dashboard Full: métricas de contribuições Bitbucket em CSV)
- What was validated:
  - `bitbucket_export.py` passou a exportar no CSV de PR os campos `approved_by` e `changes_requested_by`, além de contagens de revisores.
  - `dashboard_full.py` agora calcula métricas por pessoa usando CSVs Bitbucket no período filtrado (`PRs Abertos`, `Aprovações`, `Reprovações`, `PRs Declinados (Autor)`, `Commits`).
  - A aba `Performance do Serviço` passou a exibir bloco de contribuição com KPIs, tabela ranking e gráfico de contribuições.
  - Compatibilidade mantida com CSV legado sem colunas novas de revisão (métricas de aprovação/reprovação ficam zeradas).
- Evidence (tests/logs/diff):
  - `python3 -m py_compile bitbucket_export.py dashboard_full.py`
  - `python3 bitbucket_export.py --help`
  - `python3 - <<'PY' ... load_project_bitbucket_logs('W1NNER') + compute_bitbucket_contributor_metrics(...) ... PY`
  - `git diff -- bitbucket_export.py dashboard_full.py tasks/todo.md`
- Operational note:
  - Para preencher aprovações/reprovações por pessoa no dashboard, é necessário reexportar `*_pullrequests.csv` com esta versão do exportador.
- Suggested commit message:
  - `feat(dashboard): add csv-based bitbucket contribution ranking and reviewer metrics`

## Current Task (Bitbucket export: otimização de performance)
- [x] Paralelizar export por endpoint (commits/PRs/pipelines)
- [x] Adicionar flags para pular endpoints não necessários
- [x] Corrigir export de PR para incluir todos os estados (`state=ALL`)
- [x] Reduzir payload da API usando `fields`
- [x] Validar CLI/sintaxe e documentar comandos recomendados

## Specification (Bitbucket export: otimização de performance)
- Objetivo: reduzir tempo do `bitbucket_export.py` em execuções operacionais recorrentes.
- Escopo:
  - `bitbucket_export.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Exportador suporta execução paralela configurável (`--workers`).
  - Exportador permite pular endpoints (`--skip-commits`, `--skip-pullrequests`, `--skip-pipelines`).
  - Pull requests passam a exportar todos os estados do endpoint (`state=ALL`).
  - Requisições usam `fields` para reduzir payload transferido.

## Review (Bitbucket export: otimização de performance)
- What was validated:
  - `bitbucket_export.py` agora executa endpoints em paralelo com `ThreadPoolExecutor` (`--workers`, default `3`).
  - Foram adicionadas flags de skip por endpoint para reduzir tempo quando só parte dos dados é necessária.
  - Pull requests agora usam `state=ALL`, evitando CSV com apenas PRs abertos.
  - Endpoints usam `fields` com seleção mínima de colunas para reduzir transferência e parsing.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile bitbucket_export.py`
  - `python3 bitbucket_export.py --help`
  - `git diff -- bitbucket_export.py tasks/todo.md`
- Notes:
  - Neste ambiente, o teste online do endpoint falhou por DNS/rede (`api.bitbucket.org` indisponível), então a validação foi estrutural/local.
- Suggested commit message:
  - `perf(integration): parallelize and slim bitbucket export with endpoint skip flags`

## Current Task (Validação DORA Bitbucket: MTTR e taxa de falha)
- [x] Auditar consistência entre tabela do dashboard e CSVs extraídos do Bitbucket
- [x] Corrigir export de pipelines para incluir resultado real (sucesso/falha) além do estado de execução
- [x] Ajustar leitura/cálculo no dashboard para priorizar resultado real do pipeline
- [x] Validar sintaxe e registrar evidências + comando de reexport

## Specification (Validação DORA Bitbucket: MTTR e taxa de falha)
- Objetivo: garantir que MTTR e taxa de falha DORA usem o resultado real dos pipelines do Bitbucket.
- Escopo:
  - `bitbucket_export.py`
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Exportador grava coluna explícita com resultado do pipeline (`SUCCESSFUL`, `FAILED`, etc.).
  - Dashboard usa essa coluna para classificar sucesso/falha, mantendo fallback compatível para arquivos legados.
  - Validação local comprova que os números do print atual eram efeito de estado `COMPLETED` e documenta necessidade de reexport.

## Review (Validação DORA Bitbucket: MTTR e taxa de falha)
- Findings (ordered by severity):
  - `bitbucket_export.py` exportava `state` usando `state.name` (ex.: `COMPLETED`), que representa estado de execução e não resultado (`SUCCESSFUL`/`FAILED`). Isso força `Taxa de demanda de falha = 0.0%` e `MTTR = —` por ausência de falhas detectáveis.
  - `w1nner_pullrequests.csv` estava com apenas 10 linhas e todas em `OPEN`, indicando que o endpoint de PR está trazendo somente abertos no export atual; para fallback de lead time por PR merge, isso reduz cobertura histórica.
- What was changed:
  - `bitbucket_export.py` agora exporta também `state_type` e `state_result` em pipelines.
  - `dashboard_full.py` passa a usar `state_result` como fonte primária para `state_norm` (fallback para `state` em CSV legado).
- Evidence (tests/logs/diff):
  - `wc -l w1nner_commits.csv w1nner_pullrequests.csv w1nner_pipelines.csv`
  - `python3 - <<'PY' ... value_counts de state em w1nner_pipelines.csv ... PY`
  - `python3 - <<'PY' ... value_counts de state em w1nner_pullrequests.csv ... PY`
  - `python3 -m py_compile bitbucket_export.py dashboard_full.py`
  - `python3 - <<'PY' ... d._compute_bitbucket_weekly_dora(...) ... PY`
  - `git diff -- bitbucket_export.py dashboard_full.py tasks/todo.md`
- Operational note:
  - É necessário reexecutar `bitbucket_export.py` para gerar `w1nner_pipelines.csv` com a nova coluna `state_result`; sem isso o dashboard continuará em fallback legado.
- Suggested commit message:
  - `fix(dora): export and consume bitbucket pipeline result status for failure rate and mttr`

## Current Task (Dashboard Serviços: indicadores DORA com logs do Bitbucket)
- [x] Mapear e carregar automaticamente CSVs do Bitbucket por projeto (`*_commits.csv`, `*_pullrequests.csv`, `*_pipelines.csv`)
- [x] Calcular métricas DORA semanais no `dashboard_full.py` com prioridade para dados Bitbucket e fallback para cálculo atual
- [x] Integrar os valores DORA na tabela de performance sem marcar como placeholder cinza
- [x] Validar sintaxe/import e registrar review/evidências

## Specification (Dashboard Serviços: indicadores DORA com logs do Bitbucket)
- Objetivo: usar os logs exportados do Bitbucket para popular os indicadores DORA no dashboard de serviços.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O dashboard identifica automaticamente os CSVs mais recentes do Bitbucket no padrão por projeto.
  - A tabela de `Performance do Serviço` exibe `Frequência de Deploy`, `Lead time para mudanças`, `Taxa de demanda de falha` e `MTTR` com dados de Bitbucket quando disponíveis.
  - Quando faltarem dados no Bitbucket, o dashboard mantém fallback com a lógica atual baseada em itens do fluxo.
  - As linhas DORA deixam de ser tratadas como placeholders (não acinzentadas à força).

## Review (Dashboard Serviços: indicadores DORA com logs do Bitbucket)
- What was validated:
  - `dashboard_full.py` agora detecta CSVs do Bitbucket por projeto (`*_commits.csv`, `*_pullrequests.csv`, `*_pipelines.csv`) e também permite override via `FLOW_PMO_BITBUCKET_PREFIX_MAP`.
  - Os indicadores DORA semanais da aba `Performance do Serviço` passaram a usar prioridade de dados Bitbucket:
    - `Frequência de Deploy`: quantidade de pipelines bem-sucedidos na semana.
    - `Lead time para mudanças`: média `commit -> deploy` (fallback para `PR created -> merged`).
    - `Taxa de demanda de falha`: `% pipelines com falha na semana`.
    - `MTTR`: tempo médio de recuperação (`falha -> próximo deploy bem-sucedido`).
  - Quando não há logs suficientes do Bitbucket, os quatro indicadores continuam com fallback para o cálculo já existente no modelo de fluxo.
  - As linhas DORA deixaram de ser estilizadas como placeholder cinza na tabela.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python3 -c "import dashboard_full as d; logs=d.load_project_bitbucket_logs('W1NNER'); print({k: getattr(v,'shape',None) for k,v in logs.items()}); print('ok')"`
  - `python3 - <<'PY' ... d.compute_weekly_service_metrics(..., projeto='W1NNER') ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(dashboard): compute weekly DORA metrics from bitbucket logs with flow fallback`

## Current Task (Portfólio Features NS: raias automáticas por prefixo do título)
- [x] Implementar mapeamento automático de `Lane name` por prefixo do título (S1NC/BeFinance/W1NNR/D&A/CROSS)
- [x] Expor configuração via CLI/env e manter fallback
- [x] Validar help/import/sintaxe e orientar comando atualizado

## Specification (Portfólio Features NS: raias automáticas por prefixo do título)
- Objetivo: distribuir features do portfólio `NS` nas raias corretas do BusinessMap (`S1NC`, `BE FINANCE`, `W1NNER`, `DATA & ANALYTICS`, `CROSS`) usando o prefixo do título como heurística.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Exportador consegue definir `Lane name` a partir de prefixos de título configuráveis.
  - Caso nenhum prefixo combine, usa fallback configurável (ex.: `CROSS`).
  - Script continua validando `--help`, import e sintaxe.

## Review (Portfólio Features NS: raias automáticas por prefixo do título)
- What was validated:
  - O exportador agora suporta `--lane-by-title-prefix-map` (lista JSON) para preencher `Lane name` por prefixo do título.
  - Foi adicionado fallback explícito com `--lane-by-title-prefix-fallback` (ex.: `CROSS`).
  - A resolução da raia por título é aplicada antes do `default-lane-name`, mantendo compatibilidade com fluxos que ainda usam raia fixa.
  - CLI/help/import/sintaxe continuam válidos.
- Evidence (tests/logs/diff):
  - `python jira_to_businessmap_xlsx.py --help`
  - `python -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- jira_to_businessmap_xlsx.py tasks/todo.md`
- Suggested commit message:
  - `feat(integration): support businessmap lane mapping by title prefix`

## Current Task (Portfólio Features NS: status Cancelled/In Progess e histórico)
- [x] Ajustar exportador para tratar status `Cancelled/Cancelado` como terminal ao preencher datas históricas
- [x] Validar help/import/sintaxe
- [x] Orientar mapeamento de colunas de Features com aliases reais (`Cancelled`, `In Progess`)

## Specification (Portfólio Features NS: status Cancelled/In Progess e histórico)
- Objetivo: eliminar erros de validação na importação de Features do portfólio (`NS`) causados por status Jira não mapeados (`Cancelled`, `In Progess`) e por falta de `Start Date` em itens cancelados com histórico.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Exportador trata `Cancelled/Cancelado` como status terminal para fallback de `Start Date`/`End Date`.
  - Validação local (`--help`, import, sintaxe) permanece OK.
  - Resposta inclui `status map` de Features atualizado para colunas `BACKLOG`, `READY FOR DEVELOPMENT`, `IN PROGRESS`, `BUSINESS REVIEW`, `DONE`.

## Review (Portfólio Features NS: status Cancelled/In Progess e histórico)
- What was validated:
  - O fallback de datas históricas agora trata `Cancelled/Cancelado` como status terminal (assim como `Done/Concluído`), preenchendo `End Date` e `Start Date` fallback quando necessário.
  - O erro de `Coluna (nome) inválida` observado em `Cancelled` e `In Progess` depende de ajuste no `status-to-column-map` informado no comando (documentado na resposta).
  - CLI/help/import/sintaxe seguem válidos após a alteração.
- Evidence (tests/logs/diff):
  - `python jira_to_businessmap_xlsx.py --help`
  - `python -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- jira_to_businessmap_xlsx.py tasks/todo.md`
- Suggested commit message:
  - `fix(integration): treat cancelled status as terminal for businessmap history export`

## Current Task (BusinessMap: tags alinhadas ao tipo/fluxo de destino)
- [x] Ajustar exportador para suportar tags derivadas de `Type name` e `Workflow name` do BusinessMap
- [x] Manter compatibilidade com `tag-sources` existentes
- [x] Validar help/import/sintaxe e orientar comandos para BF (histórias + épicos/iniciativas)

## Specification (BusinessMap: tags alinhadas ao tipo/fluxo de destino)
- Objetivo: permitir que as etiquetas no BusinessMap reflitam o tipo/fluxo de destino (ex.: `História`, `Histórias workflow`) em vez de apenas o `issuetype` bruto do Jira.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - `--tag-sources` passa a aceitar fontes derivadas como `type_name`, `workflow_name` e `column_name`.
  - Exportador continua aceitando fontes já existentes (`labels`, `components`, `project`, `issuetype`, etc.).
  - Script continua validando `--help`, import e sintaxe.

## Review (BusinessMap: tags alinhadas ao tipo/fluxo de destino)
- What was validated:
  - `--tag-sources` agora aceita `type_name`, `workflow_name` e `column_name`, permitindo que as etiquetas reflitam o destino no BusinessMap em vez de somente o `issuetype` do Jira.
  - O `Type name` mapeado (ex.: `História`) é reutilizado internamente para compor tags quando `type_name` é solicitado.
  - Compatibilidade mantida com fontes de tag anteriores (`labels`, `components`, `project`, `issuetype`, `priority`, etc.).
  - CLI/help/import/sintaxe continuam válidos.
- Evidence (tests/logs/diff):
  - `python jira_to_businessmap_xlsx.py --help`
  - `python -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- jira_to_businessmap_xlsx.py tasks/todo.md`
- Suggested commit message:
  - `feat(integration): support tags derived from businessmap type and workflow`

## Current Task (BusinessMap: mapear tipo Jira Task -> História)
- [x] Adicionar mapeamento configurável de `issuetype` Jira para `Type name` no BusinessMap
- [x] Incluir preset padrão para `Task/Tarefa -> História` (compatível com BF/SYNC)
- [x] Validar help/import/sintaxe e registrar review/evidências

## Specification (BusinessMap: mapear tipo Jira Task -> História)
- Objetivo: permitir ajustar a classificação exportada em `Type name` para refletir a nomenclatura do BusinessMap (ex.: Jira `Task/Tarefa` -> BusinessMap `História`).
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Exportador aceita mapeamento de tipo via CLI/env (JSON) para sobrescrever `Type name`.
  - Preset padrão aplicado ao fluxo BF/SYNC já converte `Task`/`Tarefa` para `História`.
  - Script continua validando `--help`, import e sintaxe.

## Review (BusinessMap: mapear tipo Jira Task -> História)
- What was validated:
  - O exportador agora suporta `--type-name-map` (JSON) para mapear `issuetype` do Jira no campo `Type name` do BusinessMap.
  - Foi adicionado suporte por env `BUSINESSMAP_TYPE_NAME_MAP`.
  - O preset `bf` (e o `auto` quando projeto = `BF`) agora inclui mapeamento padrão `Task/Tarefa -> História`, útil também para S1NC/SYNC ao usar `--mapping-preset bf`.
  - CLI/help/import/sintaxe continuam válidos.
- Evidence (tests/logs/diff):
  - `python jira_to_businessmap_xlsx.py --help`
  - `python -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- jira_to_businessmap_xlsx.py tasks/todo.md`
- Notes:
  - Se quiser outro vocabulário (ex.: `Bug -> Defeito`, `Épico -> Iniciativa`), basta passar `--type-name-map` com JSON.
- Suggested commit message:
  - `feat(integration): add businessmap type-name mapping with task to historia preset`

## Current Task (BusinessMap BF: preencher Start Date para históricos DONE)
- [x] Ajustar exportador para preencher `Start Date` quando houver `End Date` em itens de status final
- [x] Manter regra semântica (evitar usar data de conclusão como início)
- [x] Validar sintaxe/import/help e registrar review/evidências

## Specification (BusinessMap BF: preencher Start Date para históricos DONE)
- Objetivo: eliminar o erro de validação do BusinessMap `"Data de Início" não definida` em itens `DONE` quando o export envia histórico (`Criado em` + `Data de Término`).
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Itens em status final com `End Date` e `Created at` preenchidos passam a receber `Start Date` fallback (preferencialmente `Created at`) quando não houver data de início melhor.
  - Exportador continua sem usar data de entrada em `DONE` como `Start Date`.
  - Script continua validando `--help`, import e sintaxe.

## Review (BusinessMap BF: preencher Start Date para históricos DONE)
- What was validated:
  - O exportador agora preenche `Start Date` com fallback em `Created at` para itens em status final (`DONE`/`Concluído`) quando existe `End Date` e o início está vazio.
  - A regra anterior (não usar `statuscategorychangedate` de entrada em `DONE` como início) foi mantida.
  - Essa mudança atende exatamente ao erro do validador do BusinessMap (`"Data de Início" não definida`) observado nas linhas concluídas.
- Evidence (tests/logs/diff):
  - `python jira_to_businessmap_xlsx.py --help`
  - `python -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- jira_to_businessmap_xlsx.py tasks/todo.md`
- Suggested commit message:
  - `fix(integration): fill start date for done historical cards in businessmap export`

## Current Task (BusinessMap import BF: corrigir lane inválida + datas históricas DONE)
- [x] Ajustar preset BF para não preencher `Lane name` por padrão (áreas do board não reconhecidas como raias válidas)
- [x] Ampliar mapeamento BF para status de discovery/design/portfolio que ficaram sem `Column name` válido
- [x] Corrigir fallback de `Start Date`/`End Date` para itens em `DONE` no `jira_to_businessmap_xlsx.py`
- [x] Validar CLI/import/sintaxe e registrar review/evidências

## Specification (BusinessMap import BF: corrigir lane inválida + datas históricas DONE)
- Objetivo: eliminar erros de validação do BusinessMap observados no teste BF, evitando `Lane name` inválido e inconsistência de histórico para cartões em `DONE`.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Preset BF automático deixa `Lane name` em branco por padrão (sem erro de raia inválida).
  - Status BF não previstos (ex.: discovery/design/wishlist) passam a mapear para colunas válidas do board BF.
  - Para itens em status final, o exportador não usa data de entrada em `DONE` como `Start Date`; quando aplicável usa como `End Date` fallback.
  - Script continua validando `--help`, import e sintaxe.

## Review (BusinessMap import BF: corrigir lane inválida + datas históricas DONE)
- What was validated:
  - O preset BF de `Lane name` foi desativado (mapa vazio), evitando preencher raias inválidas para o board `TIME BEFINANCE - DELIVERY`.
  - O preset BF de colunas foi ampliado para status observados no teste (`QA / Staging`, `Discovery & Definition`, `Ideação`, `Wishlist`, `Doing Design`, etc.), reduzindo ocorrências de `Coluna (nome) inválida`.
  - A lógica de datas históricas foi corrigida: `statuscategorychangedate` não é mais usado como `Start Date` para status `DONE`; agora ele é usado como fallback de `End Date` quando `resolutiondate` estiver ausente.
  - CLI/help/import/sintaxe continuam válidos após a correção.
- Evidence (tests/logs/diff):
  - `python jira_to_businessmap_xlsx.py --help`
  - `python -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- jira_to_businessmap_xlsx.py tasks/todo.md`
- Notes:
  - Ainda pode haver casos pontuais de status BF não mapeados; nesses casos o BusinessMap continuará sinalizando `Coluna (nome) inválida` e o preset deve ser incrementado com os nomes reais exibidos.
  - Se o board realmente usar raias válidas, elas devem ser configuradas depois com os nomes exatos do BusinessMap (não os rótulos visuais de área).
- Suggested commit message:
  - `fix(integration): correct BF businessmap preset lanes and done history dates`

## Current Task (BusinessMap: split automático em lotes + preset BF)
- [x] Definir comportamento de split automático (`--split-size`) e convenção de nomes `lote-1`, `lote-2`, ...
- [x] Implementar preset padrão BF/BusinessMap (mapeamento status -> `Column name`/`Lane name`) no `jira_to_businessmap_xlsx.py`
- [x] Validar CLI/sintaxe/import e revisar diff
- [x] Registrar review/evidências e sugestão de commit

## Specification (BusinessMap: split automático em lotes + preset BF)
- Objetivo: facilitar a importação no BusinessMap quando há limite de 100 cartões por upload, permitindo que o exportador gere múltiplos arquivos automaticamente e usando preset padrão do quadro BF sem JSON manual.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Script aceita `--split-size N` e, quando `N > 0`, grava múltiplos arquivos `.xlsx` com sufixos `-lote-1`, `-lote-2`, ... sem exceder `N` linhas por arquivo.
  - Script passa a usar preset BF de `status -> Column name` e `status -> Lane name` por padrão (ainda permitindo override por CLI/env).
  - Execução local valida `--help` e import/sintaxe do módulo.

## Review (BusinessMap: split automático em lotes + preset BF)
- What was validated:
  - `jira_to_businessmap_xlsx.py` agora suporta `--split-size` para quebrar automaticamente a saída em múltiplos arquivos `.xlsx`, usando sufixo `-lote-N` no nome do arquivo.
  - Foi adicionado preset embutido `bf` com mapeamento de status Jira para `Column name` e `Lane name` do quadro BusinessMap informado.
  - O preset é aplicado automaticamente em `--mapping-preset auto` quando o export é apenas do projeto `BF` e não há mapeamentos JSON passados por CLI/env; também pode ser forçado com `--mapping-preset bf`.
  - Overrides por CLI/env continuam funcionando (não quebra o fluxo anterior com JSONs customizados).
- Evidence (tests/logs/diff):
  - `python jira_to_businessmap_xlsx.py --help`
  - `python -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- jira_to_businessmap_xlsx.py tasks/todo.md`
- Notes:
  - Exemplo de uso simplificado para BF com limite BusinessMap de 100 cartões: `python jira_to_businessmap_xlsx.py --projects BF --board-name "TIME BEFINANCE - DELIVERY" --split-size 100`
  - Se quiser desabilitar o preset automático e voltar ao comportamento puro, use `--mapping-preset none`.
- Suggested commit message:
  - `feat(integration): add BF businessmap preset and split xlsx batches`

## Current Task (Exportador Jira -> BusinessMap em XLSX)
- [x] Definir mapeamento mínimo Jira -> colunas suportadas do import do BusinessMap (título, descrição, prioridade, owner, tags, datas, localização)
- [x] Implementar script dedicado `jira_to_businessmap_xlsx.py` com CLI, leitura de credenciais/env e exportação `.xlsx`
- [x] Suportar mapeamentos configuráveis (status->Column/Lane, prioridade, owner format, Board/Workflow fixos)
- [x] Validar sintaxe/`--help`, revisar diff e registrar review/evidências

## Specification (Exportador Jira -> BusinessMap em XLSX)
- Objetivo: criar um exportador de dados do Jira para planilha `.xlsx` no padrão de importação do BusinessMap, com headers válidos e transformação básica/configurável dos campos.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Script consulta issues do Jira via API usando variáveis `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`.
  - Gera arquivo `.xlsx` com coluna `Title` (obrigatória) e demais colunas BusinessMap relevantes (ex.: `Description`, `Custom Card ID`, `Priority`, `Owner`, `Tags`, `Deadline`, `Type name`, `Column name`, `Lane name`, `Board name`, `Workflow name`, `Created at`, `Start Date`, `End Date`).
  - Possui parâmetros/configuração para mapear status Jira em `Column name`/`Lane name` e preencher board/workflow padrão.
  - Execução local valida ao menos `--help` e sintaxe/import do módulo (sem depender de acesso real ao Jira).

## Review (Exportador Jira -> BusinessMap em XLSX)
- What was validated:
  - Foi criado o script `jira_to_businessmap_xlsx.py` com CLI para exportar issues do Jira em `.xlsx` com headers válidos do BusinessMap (`Title`, `Description`, `Custom Card ID`, `Priority`, `Owner`, `Tags`, `Deadline`, `Type name`, `Column name`, `Lane name`, `Board name`, `Board ID`, `Workflow name`, `Created at`, `Start Date`, `End Date`, entre outros).
  - O script suporta mapeamentos configuráveis por CLI/env para `status -> Column name`, `status -> Lane name`, prioridade Jira -> prioridade BusinessMap, além de escolha da origem/formato do `Owner`.
  - Há transformação de descrição Jira (ADF -> texto), datas para `YYYY-MM-DD`, tags compostas por fontes configuráveis e suporte opcional à coluna `Size` via custom fields (`JIRA_FIELD_MAP`) para story points/t-shirt.
  - A saída é gerada como `.xlsx` via `pandas + openpyxl`, pronta para importação no BusinessMap.
- Evidence (tests/logs/diff):
  - `python jira_to_businessmap_xlsx.py --help`
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- jira_to_businessmap_xlsx.py tasks/todo.md`
- Notes:
  - Não foi executado teste fim-a-fim contra Jira/BusinessMap nesta etapa (sem credenciais/ambiente de importação no contexto atual).
  - O campo `Owner` no BusinessMap depende do username válido do board; pode exigir ajuste de `--owner-format` (ex.: `email_local`) conforme a configuração da sua conta.
- Suggested commit message:
  - `feat(integration): add jira to businessmap xlsx exporter`

## Current Task (Refatorar layout dos indicadores no Process Mining para alinhamento em até 3 linhas)
- [x] Localizar bloco de KPIs no `dashboard_process_mining.py` e confirmar causa do desalinhamento (grid fixo em 12 colunas)
- [x] Definir ajuste mínimo de layout para distribuir os cards de forma alinhada sem alterar cálculos/callbacks
- [x] Validar sintaxe/import e revisar diff da mudança
- [x] Registrar review/evidências e sugestão de commit

## Specification (Refatorar layout dos indicadores no Process Mining para alinhamento em até 3 linhas)
- Objetivo: reorganizar os cards de indicadores da tela de process mining para evitar a quebra 12+6 com grande espaço vazio e manter leitura alinhada em até 3 linhas.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Os KPIs passam a ser renderizados em grade visualmente alinhada no cenário atual (18 indicadores).
  - A alteração não muda cálculos dos indicadores nem callbacks da tela.
  - O módulo continua importando normalmente.

## Review (Refatorar layout dos indicadores no Process Mining para alinhamento em até 3 linhas)
- What was validated:
  - O bloco `kpi_grid` em `dashboard_process_mining.py` foi mantido intacto nos cálculos/ordem dos indicadores; apenas o layout da grade foi ajustado.
  - A grade passou de `repeat(12, ...)` para `repeat(6, ...)`, o que organiza os 18 cards atuais em 3 linhas de 6 cards (evitando a quebra 12 + 6 com espaço vazio grande).
  - `dashboard_process_mining.py` continua importando normalmente após a alteração.
- Evidence (tests/logs/diff):
  - `python -c "import dashboard_process_mining; print('dashboard_process_mining import ok')"`
  - `git diff -- dashboard_process_mining.py tasks/todo.md` (observação: há mudanças pré-existentes no arquivo; a alteração desta tarefa é a linha do `gridTemplateColumns` do `kpi_grid`)
- Suggested commit message:
  - `fix(process-mining): align kpi cards into 3-row grid`

## Current Task (Alinhar versão do DatePicker local x produção no Vercel)
- [x] Confirmar diferença de versão do Dash entre localhost e produção
- [x] Atualizar pins de dependência para `dash==4.0.0` no deploy
- [x] Tornar `calendar-year-dropdown.js` inofensivo quando o DatePicker novo (com seletores nativos) estiver presente
- [ ] Validar deploy em produção com hard refresh e conferir interação do calendário

## Specification (Alinhar versão do DatePicker local x produção no Vercel)
- Objetivo: fazer a produção usar a mesma versão de componente de calendário que está funcionando no localhost, eliminando divergência de DOM e conflito com hacks JS.
- Escopo:
  - `pyproject.toml`
  - `requirements-vercel.txt`
  - `assets/calendar-year-dropdown.js`
  - `tasks/todo.md`
- Critério de aceite:
  - Produção instala `dash==4.0.0`.
  - Calendário em produção passa a usar o layout novo (igual ao localhost) e permite seleção de ano.
  - JS customizado não injeta dropdown extra no DatePicker novo.


## Current Task (Restaurar seleção de ano no DatePicker do process mining)
- [x] Identificar regressão no componente de calendário (assets JS/CSS vs novo DOM do DatePicker)
- [x] Ajustar `calendar-year-dropdown.js` para suportar seletores antigos e novos do cabeçalho/calendário
- [x] Ajustar CSS do dropdown customizado para manter legibilidade/posicionamento
- [x] Validar import do dashboard e revisar diff dos assets

## Specification (Restaurar seleção de ano no DatePicker do process mining)
- Objetivo: voltar a permitir navegação/seleção de ano no `dcc.DatePickerRange` do `dashboard_process_mining.py` após alteração do componente de calendário.
- Escopo:
  - `assets/calendar-year-dropdown.js`
  - `assets/calendar-fix.css`
  - `tasks/todo.md`
- Critério de aceite:
  - O dropdown customizado de ano volta a ser injetado no calendário.
  - A lógica continua compatível com o DOM legado (`.dash-datepicker-controls`) e com o cabeçalho novo (`caption`/`DayPicker`).
  - Alteração não quebra import do `dashboard_process_mining.py`.

## Review (Restaurar seleção de ano no DatePicker do process mining)
- What was validated:
  - O JS de injeção do ano agora procura containers do calendário em múltiplos seletores (legado e novo) e tenta localizar o input de ano por `.dash-input` ou por `input` com hint de `year/ano`.
  - A leitura do ano atual foi robustecida com fallback no texto do cabeçalho e no texto total do popup.
  - A inserção do dropdown foi ajustada para não falhar quando os botões de navegação ficam em um pai diferente do cabeçalho.
  - CSS do dropdown recebeu ajuste mínimo de margem/alinhamento para o novo layout.
  - `dashboard_process_mining.py` continua importando normalmente.
- Evidence (tests/logs/diff):
  - `git diff -- assets/calendar-year-dropdown.js assets/calendar-fix.css`
  - `python -c "import dashboard_process_mining; print('dashboard_process_mining import ok')"`
- Suggested commit message:
  - `fix(datepicker): restore year selector after calendar component DOM change`

## Current Task (Rede de Petri no dashboard de process mining para análise de gargalos)
- [x] Mapear pontos existentes de artefatos pm4py (`petri`) e métricas de horas/eventos no `dashboard_process_mining.py`
- [x] Implementar gráficos analíticos de rede de Petri (aproximação) + gargalos por transição/etapa no recorte filtrado
- [x] Destacar seção de Rede de Petri no layout do dashboard com orientação de uso para gargalos
- [x] Validar sintaxe/import, revisar diff e registrar evidências

## Specification (Rede de Petri no dashboard de process mining para análise de gargalos)
- Objetivo: disponibilizar visualizações de rede de Petri focadas em gargalos diretamente no `dashboard_process_mining.py`, aproveitando o recorte por data/pessoa e as horas úteis por evento já calculadas.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Dashboard exibe seção explícita de `Rede de Petri e Gargalos do Fluxo`.
  - Existe visualização em formato de rede (aproximação Petri via lugares/transições) com destaque para gargalos.
  - Existem gráficos auxiliares de ranking por transição e/ou etapa para suportar análise de gargalo.
  - Alteração continua funcionando mesmo sem artefato visual pm4py (`-pm4py-petri.png`), usando dados do changelog filtrado.

## Review (Rede de Petri no dashboard de process mining para análise de gargalos)
- What was validated:
  - `dashboard_process_mining.py` ganhou uma seção explícita `Rede de Petri e Gargalos do Fluxo` com 3 gráficos: rede Petri analítica (aproximação por lugares/transições), ranking de gargalos por transição e ranking de gargalos por etapa.
  - As visualizações usam o recorte filtrado atual (data/pessoa) e funcionam com fallback em dados do changelog (`event_hours`) quando não houver bucket de execução (`exec_event_hours`) no recorte.
  - A análise de gargalo prioriza horas úteis em `Espera` por transição e mantém decomposição por bucket (`Execução Ativa`, `Validação/QA`, `Espera`) para leitura operacional.
  - O módulo continua importando normalmente após a alteração.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_process_mining.py').read_text(encoding='utf-8')); print('dashboard_process_mining syntax ok')"`
  - `python -c "import dashboard_process_mining; print('dashboard_process_mining import ok')"`
  - `git diff -- dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): add petri bottleneck network charts to dashboard`

## Current Task (Auditoria de indicadores de portfólio: docs x código)
- [x] Confirmar módulo/arquivo responsável pelos indicadores de portfólio
- [x] Comparar roadmap documentado com indicadores implementados no `dashboard_full.py`
- [x] Identificar pendências reais vs itens já implementados e registrar em documentos do projeto

## Specification (Auditoria de indicadores de portfólio: docs x código)
- Objetivo: avaliar quais indicadores de portfólio ainda não foram implementados, confrontando documentação e código, e registrar o resultado para evitar backlog/documentação desatualizados.
- Escopo:
  - `ROADMAP_INDICADORES_PORTFOLIO.md`
  - `tasks/todo.md`
- Critério de aceite:
  - Fica documentado que o módulo de Portfólio está em `dashboard_full.py`.
  - Fica documentada a divergência entre a matriz do roadmap e o código atual.
  - Ficam listados os indicadores realmente pendentes (principalmente bloqueados por dados/exportador).

## Review (Auditoria de indicadores de portfólio: docs x código)
- What was validated:
  - `dashboard_process_mining.py` não implementa o módulo de Portfólio; a aba e os cálculos de portfólio estão em `dashboard_full.py`.
  - A matriz de `ROADMAP_INDICADORES_PORTFOLIO.md` está parcialmente desatualizada: diversos itens marcados como `Pendente` já têm cálculo/renderização no `dashboard_full.py` (ex.: `% WIP`, `% backlog parado`, fila de decisão, status fora do workflow, concentração, effort x aging, data freshness, mix/balanceamento).
  - As pendências reais concentram-se em indicadores temporais/históricos e estratégicos, bloqueados por ausência de `CreatedAt`/`ResolvedAt`, snapshots históricos ou changelog no exportador `jira_portfolio_to_csv.py`.
  - `% cancelados antes/depois de iniciar` permanece apenas parcial com o snapshot atual (sem timestamps de transição).
- Evidence (tests/logs/diff):
  - `rg -n "Portf|Portfólio|portfolio" dashboard_process_mining.py` (sem ocorrências)
  - `rg -n "Portf|Portfólio|portfolio|Cobertura Estrutural|Indicador" dashboard_full.py`
  - `rg -n "CreatedAt|ResolvedAt|changelog|history|transition|status" jira_portfolio_to_csv.py`
  - leitura da matriz em `ROADMAP_INDICADORES_PORTFOLIO.md` + leitura dos blocos de cálculo/renderização em `dashboard_full.py`
- Notes:
  - Foi adicionada seção de auditoria no roadmap para reconciliar `docs x código` sem reescrever toda a matriz histórica.
- Suggested commit message:
  - `docs(portfolio): record audit reconciling roadmap and implemented indicators`

## Current Task (Indicador explícito de histórias/tasks sem feature tática no Portfólio)
- [x] Identificar lógica existente de histórias/tasks sem vínculo com feature no `dashboard_full.py`
- [x] Adicionar indicador dedicado (% + numerador/denominador) no bloco de Cobertura Estrutural
- [x] Expor contagem em KPI executivo e colunas por TEAM com rótulo explícito
- [x] Validar sintaxe/diff e registrar review/evidências

## Specification (Indicador explícito de histórias/tasks sem feature tática no Portfólio)
- Objetivo: adicionar no painel de Portfólio um indicador com semântica explícita para histórias/tasks (melhorias) sem vínculo com feature do board tático, evitando confusão com o indicador de “órfãos”.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - A seção `Cobertura Estrutural` exibe um novo card `% histórias/tasks (melhorias) sem feature tática`.
  - A tabela por TEAM mostra contagem e percentual correspondentes.
  - O indicador atual `% histórias/tasks órfãos` permanece disponível.

## Current Task (Process mining: abas por domínio + DFG performance PM4Py)
- [x] Separar `dashboard_process_mining.py` em abas por domínio/função (descoberta, gargalos, conformidade, operacional/dados)
- [x] Implementar no exportador `process_mining_jira.py` o artefato `DFG performance` (sheet + PNG + metadados)
- [x] Consumir `PM4PyDFGPerfEdges` e imagem `-pm4py-dfg-performance.png` no `dashboard_process_mining.py`
- [x] Validar sintaxe/import dos módulos alterados e revisar diff

## Specification (Process mining: abas por domínio + DFG performance PM4Py)
- Objetivo: melhorar a navegabilidade do dashboard de process mining com separação por domínio analítico e iniciar a implementação do plano de PM4Py com `DFG performance`, mantendo compatibilidade com fallback sem PM4Py.
- Escopo:
  - `dashboard_process_mining.py`
  - `process_mining_jira.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O dashboard passa a exibir abas por domínio/função com agrupamento coerente das visualizações existentes.
  - O exportador gera dataset `PM4PyDFGPerfEdges` e tenta salvar `-pm4py-dfg-performance.png` quando PM4Py + Graphviz estiverem disponíveis.
  - O dashboard carrega/mostra o DFG performance (gráfico e/ou imagem) quando o artefato existir, sem quebrar quando ausente.

## Review (Process mining: abas por domínio + DFG performance PM4Py)
- What was validated:
  - `dashboard_process_mining.py` foi reorganizado em abas por domínio: `Descoberta`, `Gargalos`, `Conformidade`, `Operacional`, `Dados/Meta`.
  - O dashboard passou a carregar `PM4PyDFGPerfEdges` e o PNG `-pm4py-dfg-performance.png` (quando disponível).
  - O exportador `process_mining_jira.py` agora gera dataset de DFG performance (`pm4py_dfg_perf_edges`) e tenta salvar visual PM4Py de performance com fallback de API/metadados de erro.
  - O import dos módulos continua funcionando após a refatoração.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_process_mining.py').read_text(encoding='utf-8')); ast.parse(pathlib.Path('process_mining_jira.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python -c "import dashboard_process_mining; import process_mining_jira; print('imports ok')"`
  - `git diff -- dashboard_process_mining.py process_mining_jira.py tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): add domain tabs and pm4py performance dfg support`

## Current Task (Process mining: TBR + Alignments + Dotted chart)
- [x] Implementar no exportador `process_mining_jira.py` as sheets `PM4PyTBRResumo` e `PM4PyTBRCasos`
- [x] Implementar no exportador `process_mining_jira.py` as sheets de alignments (`PM4PyAlignResumo`, `PM4PyAlignCasos`, `PM4PyAlignTopMoves`) com limite de casos
- [x] Renderizar TBR e Alignments na aba `Conformidade` de `dashboard_process_mining.py`
- [x] Adicionar `Dotted chart` (Plotly via `EventosFiltrados`) na aba `Gargalos`
- [x] Validar sintaxe/import e revisar diff

## Specification (Process mining: TBR + Alignments + Dotted chart)
- Objetivo: avançar o plano de process mining adicionando conformidade PM4Py (token replay e alignments) ao workbook/dashboard e um dotted chart filtrável para leitura temporal de gargalos.
- Escopo:
  - `process_mining_jira.py`
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O exportador escreve `PM4PyTBRResumo` e `PM4PyTBRCasos` quando PM4Py estiver disponível (com metadados/fallback em caso de erro).
  - O exportador escreve `PM4PyAlignResumo`, `PM4PyAlignCasos` e `PM4PyAlignTopMoves` com limite de casos configurável para evitar execução excessiva.
  - A aba `Conformidade` exibe visualizações/tabelas de TBR e Alignments quando as sheets existirem.
  - A aba `Gargalos` exibe dotted chart Plotly usando `EventosFiltrados` e respeitando filtros de data/pessoa.

## Review (Process mining: TBR + Alignments + Dotted chart)
- What was validated:
  - `process_mining_jira.py` agora aceita `--pm4py-align-max-cases` e tenta exportar `PM4PyTBRResumo`, `PM4PyTBRCasos`, `PM4PyAlignResumo`, `PM4PyAlignCasos`, `PM4PyAlignTopMoves`.
  - O exportador registra metadados de erro/limite para TBR/Alignments sem derrubar a geração do workbook quando PM4Py falha.
  - `dashboard_process_mining.py` passou a carregar as novas sheets, renderizar histogramas/rankings/tabelas de TBR/Alignments na aba `Conformidade` e um dotted chart Plotly na aba `Gargalos`.
  - Os módulos continuam importando normalmente após as alterações.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('process_mining_jira.py').read_text(encoding='utf-8')); ast.parse(pathlib.Path('dashboard_process_mining.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python -c "import process_mining_jira, dashboard_process_mining; print('imports ok')"`
  - `git diff -- process_mining_jira.py dashboard_process_mining.py tasks/todo.md`
- Notes:
  - O ambiente local atual está com instalação de `pm4py` inconsistente (`ModuleNotFoundError: pm4py.util`); portanto a validação funcional dos novos artefatos PM4Py depende de rodar o exportador em ambiente com PM4Py íntegro.
- Suggested commit message:
  - `feat(process-mining): add tbr/alignments exports and conformance visualizations`

## Review (Indicador explícito de histórias/tasks sem feature tática no Portfólio)
- What was validated:
  - `dashboard_full.py` agora cria o KPI `% histórias/tasks (melhorias) sem feature tática` com base em `story_task_sem_feature` (histórias/tasks sem `ParentID` apontando para feature do board tático).
  - O resumo de `Cobertura Estrutural` passou a exibir esse novo card sem remover o KPI existente de `% histórias/tasks órfãos`.
  - A tabela `Cobertura estrutural por TEAM` passou a incluir colunas de contagem e percentual do novo indicador (`StoryTaskSemFeatureTatico` e `% Story/Task sem feature tática`).
  - O conjunto de KPIs executivos também exibe a contagem `Hist./Tasks sem feature tática`.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('dashboard_full syntax ok')"`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Notes:
  - No snapshot de portfólio, este indicador usa vínculo direto com feature via `ParentID` (semântica explícita de feature tática), enquanto `% histórias/tasks órfãos` continua com sua regra atual/fallback downstream.
- Suggested commit message:
  - `feat(portfolio): add explicit story-task without tactical feature KPI`


## Current Task (Smoke test do dashboard_full + split de dependências prod/dev)
- [x] Executar smoke test local das rotas principais do `dashboard_full` e validar abas de serviço
- [x] Separar dependências em `requirements-vercel.txt` e `requirements-dev.txt`
- [x] Manter `requirements.txt` compatível com deploy e registrar evidências

## Specification (Smoke test do dashboard_full + split de dependências prod/dev)
- Objetivo: validar rapidamente que o `dashboard_full` responde nas rotas base após as correções de deploy e separar dependências de produção/local para evitar regressões na Vercel por excesso de pacotes.
- Escopo:
  - `requirements.txt`
  - `requirements-vercel.txt`
  - `requirements-dev.txt`
  - `tasks/todo.md`
- Critério de aceite:
  - Smoke test local retorna `200` em `/`, `/_dash-layout` e `/_dash-dependencies`.
  - Layout contém as abas principais de `SERVICE_TABS`.
  - `requirements.txt` continua sendo entrypoint de instalação (apontando para `requirements-vercel.txt`).
  - `requirements-dev.txt` inclui stack opcional local (`pm4py`) sem impactar produção.

## Review (Smoke test do dashboard_full + split de dependências prod/dev)
- What was validated:
  - Smoke test com `app.server.test_client()` retornou `200` para `/`, `/_dash-layout` e `/_dash-dependencies`.
  - As 13 abas principais listadas em `SERVICE_TABS` foram encontradas no payload do layout (`missing = []`).
  - Dependências foram separadas em arquivos dedicados: produção em `requirements-vercel.txt`, local em `requirements-dev.txt`, com `requirements.txt` delegando para o arquivo de produção.
  - `dashboard_full` continuou respondendo normalmente após a reorganização dos requirements.
- Evidence (tests/logs/diff):
  - `python -c "import dashboard_full as d; c=d.app.server.test_client(); import json; r1=c.get('/'); r2=c.get('/_dash-layout'); r3=c.get('/_dash-dependencies'); ..."`
  - `python -c "import dashboard_full as d; c=d.app.server.test_client(); print(c.get('/').status_code, c.get('/_dash-layout').status_code, c.get('/_dash-dependencies').status_code)"`
  - `git diff -- requirements.txt requirements-vercel.txt requirements-dev.txt tasks/todo.md`
- Notes:
  - Para ambiente local com process mining, instalar via `pip install -r requirements-dev.txt`.
  - Para produção/Vercel, manter `requirements.txt` (que referencia `requirements-vercel.txt`).
- Suggested commit message:
  - `chore(deps): split vercel and local requirements and add dashboard smoke test validation`

## Current Task (Falha de deploy Vercel por falta de espaço ao instalar dependências)
- [x] Diagnosticar logs de runtime da Vercel e identificar erro real (`No space left on device`)
- [x] Remover dependência pesada opcional (`pm4py`) do `requirements.txt` de produção
- [x] Validar import local do `dashboard_full` e registrar mitigação

## Specification (Falha de deploy Vercel por falta de espaço ao instalar dependências)
- Objetivo: reduzir o footprint de dependências instaladas no runtime da Vercel para evitar instalações parciais de `dash/plotly` causadas por `No space left on device`.
- Escopo:
  - `requirements.txt`
  - `tasks/todo.md`
- Critério de aceite:
  - `requirements.txt` não inclui `pm4py` (uso opcional/local).
  - `dashboard_full` continua importando localmente.
  - Fica documentado que os erros de `dash/plotly` eram sintomas de instalação parcial por falta de espaço.

## Review (Falha de deploy Vercel por falta de espaço ao instalar dependências)
- What was validated:
  - Logs da Vercel mostram falha explícita de instalação com `No space left on device` ao copiar arquivos de `dash`, `plotly` e `pytz`, causando ambiente parcial e erros enganosos (`dash._grouping`, `dcc`, `plotly.subplots` ausentes).
  - `pm4py` (e dependências transitivas pesadas como `matplotlib`, `networkx`, `pillow`, `fonttools`) não é necessário para o runtime do `dashboard_full`, então foi removido do `requirements.txt`.
  - `dashboard_full` continua importando localmente após a redução de dependências.
- Evidence (tests/logs/diff):
  - Logs Vercel fornecidos pelo usuário com `No space left on device (os error 28)`
  - `python -c "import dashboard_full; print('dashboard_full import ok')"`
  - `git diff -- requirements.txt tasks/todo.md`
- Notes:
  - Para executar `process_mining_jira.py` com geração de modelos `pm4py`, instalar `pm4py` localmente (fora do deploy Vercel) no ambiente de análise.
- Suggested commit message:
  - `fix(vercel): remove optional pm4py from runtime deps to avoid disk exhaustion`

## Current Task (Falha de import `dash._grouping` no deploy Vercel)
- [x] Diagnosticar traceback de produção e identificar problema de empacotamento/versão do Dash
- [x] Fixar versões compatíveis de dependências web no `requirements.txt`
- [x] Validar import local do `dashboard_full` e registrar evidências

## Specification (Falha de import `dash._grouping` no deploy Vercel)
- Objetivo: estabilizar a instalação de dependências no runtime da Vercel para evitar `ModuleNotFoundError: No module named 'dash._grouping'` durante o import do `dashboard_full`.
- Escopo:
  - `requirements.txt`
  - `tasks/todo.md`
- Critério de aceite:
  - `requirements.txt` fixa versão do `dash` e ranges compatíveis de `plotly`/`Flask`/`Werkzeug`.
  - `dashboard_full` continua importando localmente com o ambiente atual.
  - Correção é compatível com o entrypoint `api/index.py` já ajustado para diagnóstico.

## Review (Falha de import `dash._grouping` no deploy Vercel)
- What was validated:
  - O traceback indica falha no pacote `dash` instalado na Vercel (`dash._validate` tentando importar `dash._grouping` ausente), sintoma de versão/resolução inconsistente.
  - `requirements.txt` foi atualizado para travar `dash==2.18.2` e ranges estáveis de `plotly`, `Flask` e `Werkzeug`, reduzindo risco de incompatibilidades no Python 3.12 da Vercel.
  - `dashboard_full` continua importando localmente após a alteração de dependências.
- Evidence (tests/logs/diff):
  - `python -c "import dashboard_full; print('dashboard_import_ok')"`
  - `git diff -- requirements.txt tasks/todo.md`
- Notes:
  - Para a Vercel aplicar a correção, faça novo deploy com limpeza de cache de build/dependências.
- Suggested commit message:
  - `fix(deps): pin dash stack versions for vercel runtime`

## Current Task (Diagnóstico de falha de startup no deploy Vercel do dashboard_full)
- [x] Reproduzir/diagnosticar padrão de erro `500` em assets do Dash em produção
- [x] Corrigir fallback de `api/index.py` para exibir erro real de inicialização sem quebrar assets do app diagnóstico
- [x] Validar sintaxe/comportamento de fallback e registrar evidências

## Specification (Diagnóstico de falha de startup no deploy Vercel do dashboard_full)
- Objetivo: evitar que falhas de import do `dashboard_full` (ex.: modelo/ENV ausente) se manifestem apenas como erro genérico de assets `500`, expondo uma página diagnóstica com a causa real no deploy Vercel.
- Escopo:
  - `api/index.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Se `dashboard_full` falhar ao importar, a aplicação ainda responde em `/` com página diagnóstica legível.
  - O erro real (mensagem e traceback) fica visível para acelerar diagnóstico.
  - Fallback textual Flask permanece disponível caso a criação do Dash diagnóstico também falhe.

## Review (Diagnóstico de falha de startup no deploy Vercel do dashboard_full)
- What was validated:
  - Identificado que o padrão de console reportado (`500` em `/_dash-component-suites/*` e `assets/*`) é compatível com falha no `import` do módulo alvo em `api/index.py`, que antes caía em fallback Flask retornando `500` para qualquer rota.
  - `api/index.py` agora tenta subir um Dash mínimo com layout de erro e traceback quando a importação do dashboard falha, evitando mascarar a causa como simples falha de assets.
  - Mantido fallback Flask textual como contingência se até o Dash diagnóstico não puder ser criado.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('api/index.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python -c "import os, importlib; os.environ['FLOW_PMO_DASH_MODULE']='module_that_does_not_exist'; m=importlib.import_module('api.index'); print(type(m.app).__name__)"`
  - `python -c "import os, importlib; os.environ['FLOW_PMO_DASH_MODULE']='module_that_does_not_exist_2'; m=importlib.import_module('api.index'); c=m.app.test_client(); r=c.get('/'); print(r.status_code); print(r.get_data(as_text=True)[:220])"`
- Notes:
  - A causa específica no seu deploy provavelmente é falha de startup do `dashboard_full` (muito comum por ausência de `FLOW_PMO_MODEL_URL`/`FLOW_PMO_MODEL_FILE` ou arquivo `.xlsx` inacessível). A página diagnóstica passará a mostrar o erro exato em produção.
- Suggested commit message:
  - `fix(vercel): show dash startup diagnostics instead of generic asset 500s`

## Current Task (Falha no processamento por exportação Jira retornando 0 issues)
- [x] Diagnosticar por que exportadores Jira retornam 0 issues e geram CSVs vazios no `run_all_projects.ps1`
- [x] Corrigir carregamento de credenciais para priorizar `jira_env.txt` (evitar env antiga na sessão)
- [x] Validar diff e registrar review/evidências

## Specification (Falha no processamento por exportação Jira retornando 0 issues)
- Objetivo: eliminar falha recorrente em que a exportação Jira retorna listas vazias por uso involuntário de credenciais antigas presentes na sessão PowerShell/Python, levando o pipeline de métricas a processar CSVs vazios.
- Escopo:
  - `run_all_projects.ps1`
  - `jira_to_pipeline_csv.py`
  - `jira_portfolio_to_csv.py`
  - `tasks/todo.md`
- Critério de aceite:
  - `run_all_projects.ps1` carrega `jira_env.txt` sobrescrevendo variáveis pré-existentes por padrão.
  - Exportadores Python também priorizam `--env-file` sobre variáveis herdadas da sessão.
  - Correção é mínima e não altera JQL/fluxo de exportação quando credenciais já estão corretas.

## Review (Falha no processamento por exportação Jira retornando 0 issues)
- What was validated:
  - A causa provável foi identificada como precedência errada de credenciais: PowerShell e Python preservavam variáveis de ambiente já existentes, ignorando credenciais atualizadas no `jira_env.txt`.
  - `run_all_projects.ps1` agora sobrescreve variáveis existentes ao importar `jira_env.txt` (`OverrideExisting = $true` por padrão).
  - `jira_to_pipeline_csv.py` e `jira_portfolio_to_csv.py` agora carregam `--env-file` com `overwrite=True`, evitando herança acidental de token/email antigos.
  - A mudança é localizada e não altera a lógica de JQL, status map, nem geração de CSV quando as credenciais já estão corretas.
- Evidence (tests/logs/diff):
  - `git diff -- run_all_projects.ps1 jira_to_pipeline_csv.py jira_portfolio_to_csv.py tasks/todo.md`
  - `python -c "import ast, pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in ['jira_to_pipeline_csv.py','jira_portfolio_to_csv.py']]; print('syntax ok')"`
- Notes:
  - Não foi possível validar consulta real ao Jira neste ambiente (sem acesso de rede), então a confirmação final depende de reexecutar `run_all_projects.ps1`.
- Suggested commit message:
  - `fix(jira-export): prioritize env file credentials over stale session variables`

## Current Task (Hierarquia no downstream + indicador exato de órfãos no fluxo operacional)
- [x] Mapear vínculos hierárquicos disponíveis no `jira_to_pipeline_csv.py` além de `ParentID`
- [x] Exportar colunas de hierarquia no downstream (`ParentID`, `ParentTipo` e vínculos inferidos de feature/épico)
- [x] Implementar cálculo do indicador exato de histórias/tasks órfãos no fluxo operacional usando as novas colunas
- [x] Validar sintaxe/diff e registrar review/evidências

## Specification (Hierarquia no downstream + indicador exato de órfãos no fluxo operacional)
- Objetivo: enriquecer o CSV downstream com campos de hierarquia suficientes para calcular com precisão o indicador de `% histórias/tasks órfãos` (sem parent feature e sem vínculo válido com épico/feature).
- Escopo:
  - `jira_to_pipeline_csv.py`
  - `dashboard_full.py` (se necessário para leitura/cálculo)
  - `tasks/todo.md`
- Critério de aceite:
  - CSV downstream passa a exportar `ParentID` e `ParentTipo` (e metadados auxiliares de vínculo hierárquico).
  - Exportador identifica e explicita vínculos alternativos relevantes (ex.: `Principal`/custom field de épico) sem depender apenas de `ParentID`.
  - Existe rotina de cálculo do indicador exato no fluxo operacional baseada nas novas colunas.
  - Alteração permanece retrocompatível para consumidores atuais do downstream.

## Review (Hierarquia no downstream + indicador exato de órfãos no fluxo operacional)
- What was validated:
  - `jira_to_pipeline_csv.py` passou a exportar colunas de hierarquia no CSV downstream (`ParentID`, `ParentTipo`, `ParentTitle`) e vínculos inferidos (`FeatureLinkID`, `EpicLinkID`, tipos e `HierarchyLinkSource`).
  - O exportador agora consolida vínculo com feature/épico a partir de `parent`, `Principal` (quando contém key Jira) e `epic_name` (quando o campo custom retorna key), preservando `Epic Name` textual para diagnóstico.
  - Foi adicionada rotina `compute_storytask_orphan_indicator(...)` que calcula `% histórias/tasks órfãos` usando a hierarquia exportada e imprime o resultado ao final da execução do export.
  - Teste em memória validou a regra de classificação do indicador (casos com parent feature, epic link e órfão sem vínculo).
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_pipeline_csv.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python jira_to_pipeline_csv.py --help`
  - `python -c "import jira_to_pipeline_csv as m; rows=[...]; print(m.compute_storytask_orphan_indicator(rows))"` (retorno esperado em teste sintético)
  - `git diff -- jira_to_pipeline_csv.py tasks/todo.md`
- Notes:
  - O cálculo exato em arquivos downstream já existentes não pode ser refeito retroativamente porque os CSVs atuais não têm `ParentID/ParentTipo` exportados; é necessário regenerar os CSVs com o novo script.
- Suggested commit message:
  - `feat(downstream): export hierarchy links and compute exact story-task orphan indicator`

## Current Task (Padronizar tamanho dos KPIs do Indicador 3 - Resumo Executivo)
- [x] Localizar e ajustar o renderer das caixas de KPIs do `Indicador 3 - Resumo Executivo`
- [x] Padronizar grid/tamanho visual para o mesmo formato dos indicadores grandes do resumo executivo
- [x] Validar sintaxe/diff e registrar review/evidências

## Specification (Padronizar tamanho dos KPIs do Indicador 3 - Resumo Executivo)
- Objetivo: deixar as caixas de KPI do bloco `Indicador 3 - Resumo Executivo` com formato e dimensões visuais consistentes com os cards grandes do topo da aba `Resumo Executivo`.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Cards do `Indicador 3` passam a usar dimensões uniformes (altura/largura visual semelhante aos indicadores grandes).
  - Grid fica responsivo, evitando cards muito estreitos em telas largas.
  - Alteração não muda os valores exibidos nem a regra de cores por tipo.

## Review (Padronizar tamanho dos KPIs do Indicador 3 - Resumo Executivo)
- What was validated:
  - `render_executive_tiles(...)` em `dashboard_full.py` foi refatorado para usar `create_kpi_card(...)`, alinhando o formato visual com os cards grandes do topo (mesmo padrão de card quadrado, centralização e tipografia).
  - O grid do `Indicador 3` passou de colunas estreitas (`minmax(170px, 1fr)`) para um layout responsivo com cards maiores (`minmax(260px, 1fr)`), com `maxWidth` centralizado para evitar excesso de colunas em telas largas.
  - As cores por tipo (`ok/alerta/risco/info`) e os valores exibidos foram preservados.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `git diff -- dashboard_full.py tasks/todo.md` (observado que `dashboard_full.py` já possui outras mudanças não relacionadas no worktree; revisão focada no bloco `render_executive_tiles`)
- Suggested commit message:
  - `style(portfolio): standardize indicador 3 executive KPI card sizing`

## Current Task (Process mining Jira (W1NNER) + painel no dashboard)
- [x] Definir escopo do process mining para W1NNER com tipos História/Task/Bug a partir do changelog detalhado do Jira
- [x] Implementar `process_mining_jira.py` com conformidade básica, retrabalho por item, tempos por status e saída CSV/Excel
- [x] Adicionar painel dedicado no `dashboard_full.py` para vazão por pessoa e retrabalho consumindo o relatório gerado
- [x] Validar sintaxe/diff e registrar evidências/review

## Specification (Process mining Jira (W1NNER) + painel no dashboard)
- Objetivo: criar um fluxo inicial de process mining baseado no changelog detalhado do Jira para o projeto W1NNER (`W1NNR`) e expor um painel dedicado no dashboard com foco em vazão por pessoa e retrabalho.
- Escopo:
  - `process_mining_jira.py`
  - `dashboard_full.py`
  - `requirements.txt`
  - `tasks/todo.md`
- Critério de aceite:
  - Script filtra somente `W1NNER/W1NNR` e tipos `História/Task/Bug`.
  - Gera relatórios de conformidade básica, retrabalho por item, tempos por status e vazão por pessoa em CSV e Excel.
  - `dashboard_full.py` possui aba separada para ler o relatório mais recente e mostrar vazão por pessoa + retrabalho.
  - Alteração falha de forma segura quando o relatório ainda não existe.

## Review (Process mining Jira (W1NNER) + painel no dashboard)
- What was validated:
  - Criado `process_mining_jira.py` para leitura do changelog detalhado (`--detailed-changelog-out`), filtro W1NNER/W1NNR + tipos História/Task/Bug, métricas de conformidade básica/retrabalho/tempos por status e relatórios de vazão por pessoa.
  - Saída em múltiplos CSVs e workbook Excel (`w1nner-process-mining-*.xlsx`) com abas dedicadas para o painel.
  - Nova aba `Process Mining Jira` no `dashboard_full.py` consumindo automaticamente o relatório mais recente e destacando KPIs, vazão por pessoa, vazão semanal e retrabalho.
  - `requirements.txt` atualizado com `pm4py` (uso opcional no script; fallback seguro quando indisponível).
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in ['process_mining_jira.py','dashboard_full.py']]; print('syntax ok')"`
  - `git diff -- process_mining_jira.py dashboard_full.py requirements.txt tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): add W1NNER jira changelog mining script and dashboard panel`

## Current Task (Isolar process mining fora do dashboard de produção)
- [x] Remover temporariamente a aba de process mining do menu do `dashboard_full.py`
- [x] Criar página standalone `dashboard_process_mining.py` para uso local/sandbox
- [x] Validar sintaxe e registrar evidências

## Specification (Isolar process mining fora do dashboard de produção)
- Objetivo: evitar expor a análise de process mining no menu do dashboard principal enquanto a funcionalidade ainda está em validação, mantendo acesso por uma página separada local.
- Escopo:
  - `dashboard_full.py`
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Aba `Process Mining Jira` deixa de aparecer no menu do `dashboard_full.py`.
  - Existe um app standalone com foco em process mining (`dashboard_process_mining.py`) que lê o último `w1nner-process-mining-*.xlsx`.
  - Página standalone mostra vazão por pessoa, retrabalho e tabelas principais.

## Review (Isolar process mining fora do dashboard de produção)
- What was validated:
  - A aba foi removida apenas da lista `SERVICE_TABS` em `dashboard_full.py`, preservando a lógica interna para futura reativação.
  - Criado `dashboard_process_mining.py` como app Dash separado (sandbox), com recarga do último relatório, filtro por período e responsável, gráficos de vazão/retrabalho e tabelas de apoio.
  - Mudança reduz risco de exposição em produção sem perder o trabalho já implementado.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in ['dashboard_full.py','dashboard_process_mining.py']]; print('syntax ok')"`
  - `git diff -- dashboard_full.py dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `chore(process-mining): move jira mining UI to standalone sandbox page`

## Current Task (Gráficos de process mining na página sandbox)
- [x] Carregar abas `EventosFiltrados` e `VariantesTop` no `dashboard_process_mining.py`
- [x] Implementar visualizações de process mining (Sankey de transições, Pareto de variantes, distribuição de conformidade)
- [x] Ajustar porta padrão do app sandbox para `8051` e exibir orientação sobre `pm4py`
- [x] Validar sintaxe

## Specification (Gráficos de process mining na página sandbox)
- Objetivo: enriquecer a página `dashboard_process_mining.py` com visualizações mais próximas de process mining, sem depender da aba no dashboard principal e com fallback quando `pm4py` não estiver instalado.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Página mostra mapa de transições (Sankey) usando `EventosFiltrados`.
  - Página mostra Pareto de variantes (`VariantesTop`) e gráficos de conformidade/retrabalho.
  - App sobe por padrão na porta `8051`.
  - Mensagem de metadados `pm4py_available=False` fica contextualizada para o usuário.

## Review (Gráficos de process mining na página sandbox)
- What was validated:
  - `dashboard_process_mining.py` passou a carregar `VariantesTop` e `EventosFiltrados` do workbook exportado.
  - Foram adicionados gráficos de process mining: Sankey de transições (`From Status` -> `To Status`), Pareto de variantes, distribuição de conformance score, dispersão Lead Time x Retrabalho e volume de eventos por semana.
  - Página exibe banner explicando `pm4py_available=False` e comando de instalação (`pip install pm4py`) sem bloquear as visualizações.
  - App sandbox agora inicia por padrão em `port=8051`, evitando conflito com `dashboard_full.py`.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_process_mining.py').read_text(encoding='utf-8')); print('syntax ok')"`
- Suggested commit message:
  - `feat(process-mining-ui): add sankey and variant charts to sandbox dashboard`

## Current Task (Modelos pm4py + horas por pessoa no fluxo)
- [x] Adicionar geração de artefatos `pm4py` (DFG, Heuristics, Inductive/Petri) no `process_mining_jira.py`
- [x] Adicionar relatório de horas por pessoa e por pessoa-status (proxy por tempo em status) no script
- [x] Exibir modelos/artefatos `pm4py` e gráficos de horas por pessoa no `dashboard_process_mining.py`
- [x] Validar sintaxe e `--help`

## Specification (Modelos pm4py + horas por pessoa no fluxo)
- Objetivo: disponibilizar artefatos clássicos de process mining (DFG, Heuristics Miner, Inductive Miner e Rede de Petri) e uma visão de horas por pessoa no fluxo a partir do changelog do Jira.
- Escopo:
  - `process_mining_jira.py`
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Script gera (quando `pm4py` estiver disponível) arquivos visuais de DFG, Heuristics, Inductive Tree e Petri net com prefixo do relatório.
  - Workbook/CSVs incluem horas por pessoa (`HorasPessoaResumo`) e por pessoa-status (`HorasPessoaStatus`) usando `TempoStatusDias * 24` como proxy.
  - Dashboard sandbox exibe imagens dos modelos `pm4py` quando presentes e gráficos/tabelas de horas por pessoa.

## Review (Modelos pm4py + horas por pessoa no fluxo)
- What was validated:
  - `process_mining_jira.py` passou a gerar datasets adicionais (`HorasPessoaResumo`, `HorasPessoaStatus`, `PM4PyDFGEdges`) e tenta salvar imagens `pm4py` (DFG, Heuristics, Inductive Tree, Petri) sem quebrar o fluxo quando a visualização falha.
  - `dashboard_process_mining.py` carrega os novos datasets, mostra barra de `DFG` (top arestas pm4py), renderiza imagens dos modelos `pm4py` quando existirem e adiciona gráficos/tabelas de horas por pessoa (proxy por tempo em status).
  - O app sandbox preserva fallback quando `pm4py` não estiver instalado, mas passa a aproveitar automaticamente os artefatos quando o relatório os inclui.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; [ast.parse(pathlib.Path(p).read_text(encoding='utf-8')) for p in ['process_mining_jira.py','dashboard_process_mining.py']]; print('syntax ok')"`
  - `python process_mining_jira.py --help`
- Suggested commit message:
  - `feat(process-mining): add pm4py model artifacts and person-hours views`

## Current Task (Heurística de horas úteis + execução ativa vs espera)
- [x] Ajustar filtro temporal do dashboard sandbox para cálculo de horas por interseção de intervalos de eventos
- [x] Implementar heurística de horas úteis (dias úteis + horário comercial + teto diário)
- [x] Separar execução ativa vs execução com espera por status/peso e expor KPIs/gráficos/tabelas
- [x] Validar sintaxe

## Specification (Heurística de horas úteis + execução ativa vs espera)
- Objetivo: aproximar “horas trabalhadas de fato” sem timesheet via heurística baseada em changelog, usando apenas tempo útil no período e ponderação por tipo de etapa de execução.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Filtro de data passa a afetar corretamente horas por evento usando interseção `History Created` → `Next Timestamp`.
  - Dashboard exibe horas de execução úteis no período (soma e média).
  - Dashboard separa execução ativa vs execução com espera e inclui versão ponderada por status.

## Review (Heurística de horas úteis + execução ativa vs espera)
- What was validated:
  - `dashboard_process_mining.py` ganhou cálculo de sobreposição temporal por evento (`compute_overlap_hours`) e horas úteis com dias úteis/janela comercial/teto diário (`business_hours_overlap` / `add_business_hours_overlap`).
  - Novos KPIs e gráficos exibem horas de execução brutas, úteis, ativa vs espera e horas úteis ponderadas por status.
  - Tabelas de execução por pessoa e por pessoa-status passaram a incluir colunas de horas úteis e ponderadas.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_process_mining.py').read_text(encoding='utf-8')); print('syntax ok')"`
- Suggested commit message:
  - `feat(process-mining-ui): add business-hours weighted execution heuristic`

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

## Current Task (Documentar roadmap de indicadores de portfólio)
- [x] Consolidar indicadores já implementados na aba Portfólio
- [x] Registrar matriz de implementação (valor, dados, complexidade)
- [x] Documentar pendências e roadmap técnico por fases
- [x] Registrar riscos/lacunas de dados do snapshot atual

## Review (Documentar roadmap de indicadores de portfólio)
- What was validated:
  - Documento criado com visão consolidada da aba de portfólio, incluindo:
    - indicadores implementados
    - matriz de implementação com status
    - backlog priorizado
    - roadmap por fases (sem/ com evolução do exportador)
    - riscos e limitações do modelo snapshot
  - O documento também registra recomendações para evolução alinhadas a práticas de portfólio (PMI/SAFe/Gartner em nível conceitual).
- Evidence (tests/logs/diff):
  - Arquivo criado: `ROADMAP_INDICADORES_PORTFOLIO.md`
- Suggested commit message:
  - `docs(portfolio): add implementation matrix and roadmap for portfolio indicators`

## Current Task (Process Mining: capacidade normalizada + gargalo no fluxo)
- [x] Definir heurística de capacidade diária normalizada por pessoa (cap 8h/dia) sobre horas úteis por evento
- [x] Implementar agregações e gráficos comparando carga de fluxo vs horas estimadas de trabalho
- [x] Implementar painel de gargalo por status (mediana/p85/carga total) para validar `In Progress` vs `Homologation`
- [x] Validar sintaxe/import do `dashboard_process_mining.py`

## Review (Process Mining: capacidade normalizada + gargalo no fluxo)
- What was validated:
  - `dashboard_process_mining.py` passou a quebrar eventos de execução em slices diários úteis e normalizar por `Responsavel + Dia` com teto de `8h/dia`, reduzindo superestimação quando uma pessoa possui vários cards simultâneos.
  - Novas visões adicionadas:
    - KPIs de horas estimadas normalizadas (total, ponderadas e por bucket Ativa/Validação/QA/Espera)
    - gráficos comparativos `Carga de Fluxo vs Horas Estimadas`
    - gráficos de horas estimadas por pessoa e por etapa do fluxo (stacked por bucket)
  - Painel de gargalo por status adicionado com 3 lentes:
    - tempo útil mediano/p85 por evento
    - carga total de horas úteis no período
    - scatter `mediana x carga total` para triangulação do gargalo
  - O filtro de período continua aplicado no nível de evento (`History Created`) e as horas usam interseção com o intervalo do evento (`History Created` -> `Next Timestamp`).
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_process_mining.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python -c "import dashboard_process_mining; print('import_ok')"`
- Suggested commit message:
  - `feat(process-mining-ui): add normalized person-day capacity heuristic and bottleneck analytics`



## Current Task (Bitbucket API: ler acesso via .env)
- [x] Definir variáveis de acesso Bitbucket em arquivo `.env` e exemplo versionado
- [x] Criar script Python para extrair commits, pull requests e pipelines lendo credenciais do `.env`
- [x] Validar `--help` e execução de smoke test sem rede (`--dry-run`)
- [x] Registrar review/evidências e sugestão de commit

## Specification (Bitbucket API: ler acesso via .env)
- Objetivo: permitir extração de logs de commits, PRs e pipelines do Bitbucket sem hardcode de credenciais, usando variáveis em arquivo `.env`.
- Escopo:
  - `bitbucket_export.py`
  - `.env.example`
  - `.gitignore`
  - `tasks/todo.md`
- Critério de aceite:
  - Script lê `BB_EMAIL`, `BB_TOKEN`, `BB_WORKSPACE`, `BB_REPO` do `.env` por padrão.
  - Suporta override por CLI (`--env-file`, `--workspace`, `--repo`, etc.).
  - Exporta CSV de `commits`, `pullrequests` e `pipelines` com paginação da API Bitbucket (`next`).
  - Possui modo `--dry-run` para validar configuração local sem chamar API.

## Review (Bitbucket API: ler acesso via .env)
- What was validated:
  - Script `bitbucket_export.py` criado com leitura automática de `.env` (ou arquivo via `--env-file`) usando variáveis `BB_EMAIL`, `BB_TOKEN`, `BB_WORKSPACE`, `BB_REPO`.
  - Exportação CSV implementada para `commits`, `pullrequests` e `pipelines` com paginação baseada no campo `next` da API Bitbucket.
  - Arquivo `.env.example` adicionado com as chaves necessárias e `.env` incluído no `.gitignore` para evitar commit de credenciais reais.
  - Script inclui `--dry-run` para validar carregamento de configuração sem chamada de rede.
- Evidence (tests/logs/diff):
  - `python3 bitbucket_export.py --help`
  - `python3 -m py_compile bitbucket_export.py`
  - `python3 bitbucket_export.py --env-file .env.example --dry-run`
  - `git diff -- bitbucket_export.py .env.example .gitignore tasks/todo.md`
- Suggested commit message:
  - `feat(integration): add bitbucket csv exporter with .env-based auth`

## Current Task (Avaliação: cruzamento Jira + Bitbucket para capacidade por pessoa)
- [x] Levantar campos disponíveis nos exportadores de Jira e Bitbucket
- [x] Medir cobertura real dos CSVs Bitbucket disponíveis no workspace
- [x] Classificar métricas em: imediatas, possíveis com aproximação e dependentes de evolução de coleta
- [x] Registrar recomendações de implementação faseada e riscos de qualidade de dados

## Specification (Avaliação: cruzamento Jira + Bitbucket para capacidade por pessoa)
- Objetivo: avaliar viabilidade técnica e confiabilidade de métricas por pessoa (work items + commits/PRs) antes de implementar.
- Escopo:
  - `jira_to_pipeline_csv.py`
  - `bitbucket_export.py`
  - `dashboard_full.py`
  - `w1nner_commits.csv`
  - `w1nner_pullrequests.csv`
  - `w1nner_pipelines.csv`
- Critério de aceite:
  - Diagnóstico explicita o que é medível já com os dados atuais.
  - Diagnóstico explicita limitações de join pessoa-a-pessoa e item-a-item.
  - Diagnóstico sugere sequência de implementação com menor risco de viés.

## Review (Avaliação: cruzamento Jira + Bitbucket para capacidade por pessoa)
- What was validated:
  - Exportador Jira (`jira_to_pipeline_csv.py`) já gera base de itens com `ID`, `Responsável`, datas por etapa e opcional de changelog detalhado com `Author` de transição.
  - Exportador Bitbucket (`bitbucket_export.py`) já gera work item key em commits/PRs/pipelines e dados de revisão (`approved_by`, `changes_requested_by`).
  - Cobertura observada nos CSVs locais (`W1NNER`):
    - `commits`: 22.188 linhas; `primary_work_item_key` em 40,7%.
    - `pullrequests`: 875 linhas; `primary_work_item_key` em 97,5%.
    - `pipelines`: 4.360 linhas; `primary_work_item_key` em 7,7%.
    - Join `pipelines.commit_hash -> commits.hash`: 87,2% de match.
  - Principais riscos para capacidade por pessoa:
    - identidade de pessoa não unificada entre Jira e Bitbucket (display name/email/variações);
    - parte relevante dos commits sem chave Jira;
    - baixa cobertura de chave em pipelines para rastreio item-a-item direto.
- Evidence (tests/logs/diff):
  - `sed -n '1,330p' bitbucket_export.py`
  - `sed -n '1,220p' jira_to_pipeline_csv.py`
  - `python3 - <<'PY' ... profile de cobertura e joins dos 3 CSVs Bitbucket ... PY`
- Suggested commit message:
  - `docs(assessment): map feasible jira-bitbucket capacity metrics and data gaps`

## Current Task (MVP: capacidade por pessoa cruzando Jira + Bitbucket)
- [x] Implementar padronização de identidade por pessoa com mapa de aliases configurável
- [x] Calcular métricas Jira por pessoa no período filtrado da aba Performance
- [x] Consolidar métricas Jira + Bitbucket em ranking único com score proxy
- [x] Exibir seção de capacidade cruzada na aba `Performance do Serviço`
- [x] Validar sintaxe e smoke tests de cálculo/renderização

## Specification (MVP: capacidade por pessoa cruzando Jira + Bitbucket)
- Objetivo: disponibilizar no dashboard um ranking de capacidade por pessoa combinando throughput Jira e atividade técnica no Bitbucket.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Suporte a alias de pessoa via `FLOW_PMO_PERSON_ALIAS_MAP` para reduzir divergência de nomes Jira/Bitbucket.
  - Nova tabela de capacidade cruzada com pelo menos: `Itens Concluídos`, `Itens c/ Evidência Técnica`, `Cobertura Técnica`, `PRs`, `Aprovações`, `Commits`.
  - Seção renderiza dentro da aba `Performance do Serviço` respeitando filtros ativos.

## Review (MVP: capacidade por pessoa cruzando Jira + Bitbucket)
- What was validated:
  - `dashboard_full.py` agora suporta alias de pessoas por variável de ambiente `FLOW_PMO_PERSON_ALIAS_MAP` (json) para canonizar nomes entre Jira e Bitbucket.
  - Foi adicionado cálculo Jira por pessoa no período (`Itens Concluídos`, `Itens Iniciados`, `WIP no Fim`, `Lead Time Mediano`).
  - Foi adicionado consolidado cruzado Jira + Bitbucket com:
    - `Itens com Evidência Técnica` (issue key presente em commits/PRs no período)
    - `Cobertura Técnica (%)`
    - `Score Capacidade (proxy)` para ordenação do ranking.
  - A seção `Contribuições Bitbucket (CSV)` passou a incluir bloco adicional `Capacidade Cruzada (Jira + Bitbucket)` na aba `Performance do Serviço`.
  - A integração foi conectada ao fluxo existente, passando `df_proj` (filtros ativos) para o consolidado cruzado.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... compute_bitbucket_contributor_metrics / compute_jira_person_capacity_metrics / compute_cross_source_capacity_metrics ... PY`
  - `python3 - <<'PY' ... build_bitbucket_contributor_section('W1NNER', start, end, jira_df=df) ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(dashboard): add cross-source capacity ranking per person (jira + bitbucket)`

## Current Task (Hotfix: KeyError 'Pessoa' no consolidado Jira+Bitbucket)
- [x] Reproduzir cenário de dataframe vazio no consolidado cruzado
- [x] Corrigir merge para preservar schema mínimo com coluna `Pessoa`
- [x] Validar cálculo/renderização com Jira vazio, Bitbucket vazio e cenário normal

## Review (Hotfix: KeyError 'Pessoa' no consolidado Jira+Bitbucket)
- What was validated:
  - `compute_cross_source_capacity_metrics` agora garante coluna `Pessoa` nos dataframes de Jira/Bitbucket antes do `pd.merge`.
  - O erro `KeyError: 'Pessoa'` deixa de ocorrer quando uma das fontes está vazia.
  - O render da seção de contribuições/capacidade continua funcional no cenário normal.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... compute_cross_source_capacity_metrics(... logs vazios ...) ... PY`
  - `python3 - <<'PY' ... build_bitbucket_contributor_section('W1NNER', ...) ... PY`
- Suggested commit message:
  - `fix(dashboard): handle empty jira/bitbucket person datasets in cross-source merge`

## Current Task (Fase 2: capacidade semanal por pessoa no cruzamento Jira+Bitbucket)
- [x] Implementar dataframe semanal consolidado por pessoa (`Semana`, `Pessoa`, métricas Jira/Bitbucket)
- [x] Adicionar gráfico de tendência semanal de `Score Capacidade (proxy)` no bloco de capacidade cruzada
- [x] Ajustar seção para funcionar com ausência parcial de dados (somente Jira ou somente Bitbucket)
- [x] Validar sintaxe e smoke tests para cenários normal/parcial

## Specification (Fase 2: capacidade semanal por pessoa no cruzamento Jira+Bitbucket)
- Objetivo: evoluir o MVP para permitir leitura temporal (semanal) da capacidade por pessoa, não apenas acumulado do período.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Função de agregação semanal cruzada disponível no backend da dashboard.
  - Bloco `Capacidade Cruzada (Jira + Bitbucket)` passa a exibir tendência semanal dos top contribuidores.
  - A aba `Performance do Serviço` permanece estável quando uma fonte está vazia.

## Review (Fase 2: capacidade semanal por pessoa no cruzamento Jira+Bitbucket)
- What was validated:
  - `dashboard_full.py` agora possui `compute_cross_source_capacity_weekly_metrics(...)`, consolidando por semana e pessoa:
    - `Itens Concluidos` (Jira por `DataDone`)
    - `PRs Abertos` (PR `created_on`)
    - `Aprovacoes` / `Reprovacoes` (PR `updated_on` + reviewers)
    - `Commits`
    - `Score Capacidade (proxy)`
  - O bloco `Capacidade Cruzada (Jira + Bitbucket)` ganhou gráfico de tendência semanal para as top 5 pessoas do período.
  - `build_bitbucket_contributor_section(...)` foi robustecido para:
    - mostrar painel de Bitbucket quando houver dados;
    - manter o bloco cruzado quando Bitbucket estiver vazio mas Jira existir;
    - retornar mensagem única somente quando ambas as fontes estiverem sem dados.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... compute_cross_source_capacity_weekly_metrics(jira, logs, ...) ... PY`
  - `python3 - <<'PY' ... weekly jira-only / weekly bb-only ... PY`
  - `python3 - <<'PY' ... build_bitbucket_contributor_section(...) ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(dashboard): add weekly cross-source capacity trends per person`

## Current Task (Fase 3: filtros de Top N e métrica semanal na capacidade cruzada)
- [x] Adicionar filtros na UI para `Top N` e `Métrica semanal` da capacidade cruzada
- [x] Propagar filtros no callback principal e na função da seção de contribuições/capacidade
- [x] Aplicar filtros no gráfico semanal (`score`, `itens concluídos`, `commits`, `PRs`)
- [x] Validar renderização com múltiplas combinações de filtros

## Specification (Fase 3: filtros de Top N e métrica semanal na capacidade cruzada)
- Objetivo: tornar a análise de capacidade cruzada mais exploratória, permitindo escolher quantas pessoas comparar e qual métrica semanal observar.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Novos filtros aparecem no painel principal de filtros.
  - Aba `Performance do Serviço` aplica os filtros ao bloco `Capacidade Cruzada (Jira + Bitbucket)`.
  - Gráfico semanal passa a alternar entre métricas: score, itens concluídos, commits e PRs abertos.

## Review (Fase 3: filtros de Top N e métrica semanal na capacidade cruzada)
- What was validated:
  - Filtros adicionados na UI:
    - `filter-capacity-top-n` (3, 5, 8, 10, 15, 20)
    - `filter-capacity-weekly-metric` (`score`, `itens_concluidos`, `commits`, `prs_abertos`)
  - Callback principal `render_tab` atualizado para receber e propagar os dois filtros para `build_bitbucket_contributor_section(...)`.
  - A seção de capacidade cruzada agora usa:
    - `Top N` para limitar ranking e pessoas da série temporal.
    - métrica selecionada para eixo Y do gráfico semanal.
  - Assinatura de `render_tab` preserva defaults para compatibilidade com chamadas internas.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... build_bitbucket_contributor_section(... top_n=3/10, weekly_metric='score/commits/prs_abertos') ... PY`
  - `python3 - <<'PY' ... render_tab('services','tab-performance',..., 8, 'itens_concluidos', '__ALL__') ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(dashboard): add top-n and weekly metric filters for cross-source capacity chart`

## Current Task (Process Mining W1NNER: cruzamento Jira + Bitbucket pelos indicadores do anexo)
- [x] Ler indicadores do anexo PDF e mapear para a página `dashboard_process_mining.py`
- [x] Implementar carga dos logs Bitbucket (`commits`, `pullrequests`, `pipelines`) no dashboard de Process Mining
- [x] Calcular métricas cruzadas por pessoa (itens Jira + atividade técnica Bitbucket + evidência técnica)
- [x] Exibir novos KPIs e visualizações de capacidade integrada na aba `Operacional`
- [x] Validar sintaxe e smoke test com dados reais disponíveis

## Specification (Process Mining W1NNER: cruzamento Jira + Bitbucket pelos indicadores do anexo)
- Objetivo: cruzar os dados Jira/Process Mining com logs do Bitbucket para complementar os indicadores operacionais por pessoa.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Dashboard carrega CSVs Bitbucket do projeto W1NNER com o mesmo padrão usado no dashboard principal.
  - Métricas cruzadas incluem pelo menos: `Commits`, `PRs Merged`, `Aprovações`, `Reprovações`, `Itens c/ Evidência Técnica`, `Cobertura Técnica (%)`, `Score Integrado`.
  - Aba `Operacional` exibe gráfico e tabela por pessoa combinando Jira + Bitbucket.

## Review (Process Mining W1NNER: cruzamento Jira + Bitbucket pelos indicadores do anexo)
- What was validated:
  - `dashboard_process_mining.py` passou a incluir helpers para:
    - carregamento de logs Bitbucket por projeto/prefixo (`FLOW_PMO_BITBUCKET_PREFIX_MAP` + fallback `w1nner`)
    - normalização de nomes de pessoas
    - agregação de métricas Bitbucket por pessoa no período filtrado
    - consolidação Jira + Bitbucket com `Itens c/ Evidência Técnica` e `Cobertura Técnica (%)`.
  - O bloco de KPIs recebeu cartões adicionais de Bitbucket/cross:
    - `Commits (Bitbucket)`, `PRs Merged (Bitbucket)`, `Aprovações PR (Bitbucket)`, `Reprovações PR (Bitbucket)`,
    - `Itens c/ Evidência Técnica`, `Cobertura Técnica`.
  - A aba `Operacional` ganhou:
    - gráfico `Capacidade Integrada por Pessoa (Jira + Bitbucket)`
    - tabela detalhada por pessoa com métricas cruzadas.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_process_mining.py`
  - `python3 - <<'PY' ... load_project_bitbucket_logs('W1NNER') ... PY`
  - `python3 - <<'PY' ... compute_bitbucket_person_metrics(...) ... PY`
  - `python3 - <<'PY' ... compute_pm_bitbucket_cross_metrics(pm_people, pm_cases, ...) ... PY`
  - `git diff -- dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): add jira-bitbucket cross indicators per person in operational view`

## Current Task (Process Mining: visão semanal dos indicadores cruzados Jira+Bitbucket)
- [x] Implementar agregado semanal por pessoa no cruzamento Jira+Bitbucket
- [x] Adicionar filtros de `Top N` e `Métrica semanal` na UI do Process Mining
- [x] Conectar filtros ao callback principal e renderizar tendência semanal na aba `Operacional`
- [x] Validar sintaxe e render callback com dados reais

## Specification (Process Mining: visão semanal dos indicadores cruzados Jira+Bitbucket)
- Objetivo: habilitar tendência semanal por pessoa dos indicadores cruzados no dashboard de Process Mining, em linha com a experiência do `dashboard_full.py`.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Cálculo semanal por pessoa disponível para métricas cruzadas.
  - UI oferece filtros de `Top N` e `Métrica semanal`.
  - Aba `Operacional` exibe gráfico semanal controlado pelos filtros.

## Review (Process Mining: visão semanal dos indicadores cruzados Jira+Bitbucket)
- What was validated:
  - Função `compute_pm_bitbucket_cross_weekly(...)` adicionada para consolidar por `Semana + Pessoa`:
    - `Itens Concluidos`, `Commits`, `PRs Abertos`, `PRs Merged`, `Aprovacoes`, `Reprovacoes`, `Score Integrado`.
  - Novos controles na barra superior:
    - `pm-cross-topn`
    - `pm-cross-weekly-metric`
  - Callback `render_pm(...)` atualizado para receber os novos inputs e usar no gráfico:
    - título dinâmico com métrica e Top N selecionado.
  - Aba `Operacional` passou a exibir gráfico `Tendência Semanal Integrada (...)` abaixo do gráfico de capacidade integrada.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_process_mining.py`
  - `python3 - <<'PY' ... compute_pm_bitbucket_cross_weekly(...) ... PY`
  - `python3 - <<'PY' ... render_pm(..., 8, 'prs_merged') ... PY`
  - `git diff -- dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): add weekly cross-source trend controls and chart`

## Current Task (Process Mining v2: alias robusto + cobertura semanal + PRs declinados semanais)
- [x] Implementar canonicalização de pessoas com `FLOW_PMO_PERSON_ALIAS_MAP`
- [x] Adicionar `PRs Declinados` no agregado semanal integrado
- [x] Adicionar `Itens c/ Evidência Técnica` e `Cobertura Técnica (%)` no agregado semanal
- [x] Expor novas métricas no filtro semanal da UI (`Cobertura Técnica` e `PRs Declinados`)
- [x] Validar callback/renderização com as novas métricas

## Specification (Process Mining v2: alias robusto + cobertura semanal + PRs declinados semanais)
- Objetivo: aumentar robustez do cruzamento Jira+Bitbucket e completar a leitura semanal com qualidade de rastreabilidade e sinal de rejeição de PR.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Pessoas podem ser unificadas por aliases configuráveis entre Jira e Bitbucket.
  - Série semanal inclui `PRs Declinados` por pessoa.
  - Série semanal inclui `Itens c/ Evidência Técnica` e `Cobertura Técnica (%)` por pessoa.
  - Filtro de métrica semanal permite escolher essas novas métricas.

## Review (Process Mining v2: alias robusto + cobertura semanal + PRs declinados semanais)
- What was validated:
  - `dashboard_process_mining.py` agora suporta canonicalização de pessoas via `FLOW_PMO_PERSON_ALIAS_MAP` (com matching por nome normalizado e email).
  - `compute_pm_bitbucket_cross_weekly(...)` passou a calcular:
    - `PRs Declinados`
    - `Itens c/ Evidencia Tecnica`
    - `Cobertura Tecnica (%)`
    - mantendo `Score Integrado` e demais métricas já existentes.
  - Filtro `pm-cross-weekly-metric` ganhou opções:
    - `Cobertura Técnica (%)`
    - `PRs Declinados`
  - Consolidado integrado por pessoa também passou a exibir `PRs Declinados` na tabela e nos totais.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_process_mining.py`
  - `python3 - <<'PY' ... compute_pm_bitbucket_cross_weekly(...): cols incl. PRs Declinados + Cobertura Técnica ... PY`
  - `python3 - <<'PY' ... compute_pm_bitbucket_cross_metrics(...): PRs Declinados nos totais ... PY`
  - `python3 - <<'PY' ... render_pm(..., 'cobertura_tecnica') + render_pm(..., 'prs_declinados') ... PY`
  - `git diff -- dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): add alias-based identity and weekly declined-pr/technical-coverage metrics`

## Current Task (Hotfix Bitbucket export: diffstat 404 por `%0D` no href)
- [x] Diagnosticar 404 no diffstat com URL de `links.diffstat.href` contaminada por CR/LF
- [x] Ajustar exportador para priorizar endpoint canônico por PR id (`/pullrequests/{id}/diffstat`)
- [x] Adicionar sanitização defensiva de URL de diffstat como fallback
- [x] Validar sintaxe e normalização local

## Review (Hotfix Bitbucket export: diffstat 404 por `%0D` no href)
- What was validated:
  - O erro observado (`...diffstat/...:hash%0Dhash?... -> 404`) vem de `href` com revspec malformado.
  - `bitbucket_export.py` agora usa preferencialmente `.../pullrequests/{id}/diffstat`, reduzindo dependência de `href` instável.
  - Foi adicionada função `normalize_diffstat_url(...)` para remover CR/LF e `%0D/%0A` quando houver fallback para URL vinda da API.
  - Exportador segue válido em sintaxe após ajuste.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile bitbucket_export.py`
  - `python3 - <<'PY' ... normalize_diffstat_url('...%0D...') ... PY`
  - `git diff -- bitbucket_export.py tasks/todo.md`
- Suggested commit message:
  - `fix(integration): stabilize bitbucket diffstat lookup using pr endpoint and url sanitization`

## Current Task (Hotfix complementar diffstat: redirect 3xx para URL malformada)
- [x] Diagnosticar que endpoint canônico `/pullrequests/{id}/diffstat` pode redirecionar para URL com `%0D`
- [x] Implementar tratamento manual de redirect em `fetch_pullrequest_volume` com sanitização de `Location`
- [x] Validar com teste local mockado de redirect -> payload diffstat

## Review (Hotfix complementar diffstat: redirect 3xx para URL malformada)
- What was validated:
  - Em alguns PRs, o endpoint canônico responde com redirect para `diffstat/revspec` contendo `%0D`, causando 404 quando seguido cegamente.
  - `fetch_pullrequest_volume` foi alterado para:
    - fazer request com `allow_redirects=False`;
    - ler `Location`, sanitizar URL (removendo `%0D/%0A` e CR/LF), e seguir manualmente;
    - manter paginação de `next` com sanitização.
  - Teste mockado confirmou que o redirect sanitizado remove `%0D` e preserva contagem de `additions/deletions/files_changed`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile bitbucket_export.py`
  - `python3 - <<'PY' ... MockSession redirect 302 -> diffstat payload ... PY`
  - `git diff -- bitbucket_export.py tasks/todo.md`
- Suggested commit message:
  - `fix(integration): follow and sanitize diffstat redirects to avoid malformed %0D urls`

## Current Task (Hotfix ruído operacional: diffstat 404 conhecido)
- [x] Tratar `HTTP 404` em diffstat como ausência de volume (sem warning por PR)
- [x] Manter warning apenas para erros não esperados de rede/API
- [x] Validar sintaxe do exportador

## Review (Hotfix ruído operacional: diffstat 404 conhecido)
- What was validated:
  - `bitbucket_export.py` passou a tratar `requests.HTTPError` com `status_code == 404` no diffstat como caso esperado, retornando colunas de volume vazias sem log de aviso.
  - Erros HTTP diferentes de 404 e falhas de rede continuam gerando warning.
  - Sintaxe do script permanece válida.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile bitbucket_export.py`
  - `git diff -- bitbucket_export.py tasks/todo.md`
- Suggested commit message:
  - `fix(integration): silence expected 404 diffstat misses while keeping other warnings`

## Current Task (Bitbucket export: tolerância a rate limit 429)
- [x] Implementar retry automático para chamadas HTTP do Bitbucket (429/5xx)
- [x] Respeitar cabeçalho `Retry-After` quando presente
- [x] Aplicar retry em paginação principal e coleta de diffstat de PR
- [x] Validar sintaxe e help da CLI

## Specification (Bitbucket export: tolerância a rate limit 429)
- Objetivo: evitar interrupção do export completo quando o Bitbucket retornar `429 Too Many Requests`.
- Escopo:
  - `bitbucket_export.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Requisições fazem retry com backoff para `429` e `5xx`.
  - Se `Retry-After` vier na resposta, o tempo é respeitado.
  - Fluxo de commits/PRs/pipelines e diffstat de PR usam o mesmo mecanismo de retry.
  - Script permanece válido em sintaxe/help.

## Review (Bitbucket export: tolerância a rate limit 429)
- What was validated:
  - Foi adicionado helper de request com retry (`request_with_retry`) com backoff e suporte a `Retry-After`.
  - `iter_paginated` agora usa esse helper para commits/PRs/pipelines.
  - `fetch_pullrequest_volume` também usa o helper para reduzir falhas em `diffstat` sob limitação de taxa.
  - CLI e sintaxe seguem válidas.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile bitbucket_export.py`
  - `python3 bitbucket_export.py --help`
- Suggested commit message:
  - `fix(integration): add retry/backoff for bitbucket 429 and transient 5xx responses`

## Review Addendum (Bitbucket export: tolerância a rate limit 429)
- Additional findings from real run:
  - Mesmo com retry inicial, o export continuou sofrendo 429 em quase todas as páginas de commits de histórico longo.
- Additional changes:
  - Adicionado `cooldown` global entre tentativas quando ocorre `429`.
  - Adicionado pacing contínuo de requests com `--min-request-interval-ms` (default `350ms`).
  - Em `429` sem `Retry-After`, aplica espera mínima conservadora (>=8s) com jitter.
- Suggested commit message (updated):
  - `fix(integration): add global cooldown and request pacing for persistent bitbucket 429 limits`

## Current Task (Gráfico: commits x cartões concluídos por pessoa)
- [x] Definir dataset do gráfico com foco em desconexão Jira-Bitbucket
- [x] Gerar gráfico scatter com destaque dos casos críticos e exportar em HTML
- [x] Validar geração do arquivo e registrar evidências/review

## Specification (Gráfico: commits x cartões concluídos por pessoa)
- Objetivo: criar visual que evidencie a assimetria entre atividade técnica (commits) e vazão de cartões concluídos no Jira.
- Escopo:
  - `scripts/generate_commits_vs_jira_chart.py` (novo)
  - `artifacts/commits_vs_jira_done.html` (novo)
  - `tasks/todo.md`
- Critério de aceite:
  - Scatter com eixo X = commits e eixo Y = cartões concluídos por pessoa.
  - Destaque visual de outliers: alta vazão sem código e alta atividade técnica sem conclusão no Jira.
  - Inclusão de anotações para pessoas-chave citadas no diagnóstico.
  - Artefato HTML gerado localmente e abrível no navegador.

## Review (Gráfico: commits x cartões concluídos por pessoa)
- What was validated:
  - Script novo `scripts/generate_commits_vs_jira_chart.py` criado para cruzar dados de `VazaoPessoaResumo/ConformidadeCasos` com logs Bitbucket e gerar scatter `Commits x Itens Concluidos`.
  - O gráfico classifica automaticamente os quadrantes de desconexão (`Alta vazão sem evidência técnica` e `Atividade técnica sem fechamento Jira`) e anota as pessoas-chave do diagnóstico.
  - Artefato final gerado em `artifacts/commits_vs_jira_done.html` com período do recorte e indicador de cobertura técnica no subtítulo.
- Evidence (tests/logs/diff):
  - `python3 scripts/generate_commits_vs_jira_chart.py --days 30`
  - Saída: `Arquivo gerado: .../artifacts/commits_vs_jira_done.html`
  - Saída (amostra): `Lucas Pizol / Peterson Bem / Gabriel de Oliveira Koehler` em `Atividade técnica sem fechamento Jira`; `Lorraine Caribe` e `Thaís Cabral` em `Alta vazão sem evidência técnica`.
- Suggested commit message:
  - `feat(analytics): add jira-vs-bitbucket commits x done scatter chart with disconnect highlights`

## Current Task (Dashboard Full: incluir relatório commits x cartões Jira)
- [x] Adicionar visual de correlação `Commits x Itens Concluídos` na aba de Process Mining do `dashboard_full.py`
- [x] Destacar padrões de desconexão Jira-Bitbucket com classificação visual e tabelas de outliers
- [x] Validar sintaxe/execução e registrar evidências

## Specification (Dashboard Full: incluir relatório commits x cartões Jira)
- Objetivo: disponibilizar no dashboard principal o relatório de desconexão Jira-Bitbucket já gerado em HTML.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - A aba `tab-process-mining-jira` exibe scatter `Commits (Bitbucket)` no eixo X e `Itens Concluídos (Jira)` no eixo Y por pessoa.
  - O visual diferencia os padrões: alta vazão sem commits e commits sem conclusão no Jira.
  - O bloco apresenta resumo de cobertura técnica e tabelas com principais outliers.

## Review (Dashboard Full: incluir relatório commits x cartões Jira)
- What was validated:
  - Foi adicionada a função `build_pm_commits_vs_jira_report(...)` em `dashboard_full.py`, responsável por cruzar `VazaoPessoaResumo` (Jira PM) com contribuições do Bitbucket no período filtrado.
  - A aba `tab-process-mining-jira` agora renderiza o bloco novo de rastreabilidade com:
    - scatter `Commits (Bitbucket) x Itens Concluídos (Jira)` por pessoa;
    - classificação visual (`Alta vazão sem commits`, `Commits sem conclusão Jira`, `Fluxo conectado`);
    - destaque/anotações para pessoas-chave;
    - resumo de cobertura técnica por `Issue Key` com base em `work_item_keys`/`primary_work_item_key`;
    - duas tabelas de outliers (vazão sem commits e commits sem conclusão Jira).
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... build_pm_commits_vs_jira_report(...) ... print(type(comp).__name__) ... PY`
  - `git diff -- dashboard_full.py`
- Suggested commit message:
  - `feat(process-mining): add jira-vs-bitbucket commits x done traceability report to dashboard_full`

## Current Task (Dashboard Full: aba Process Mining + score percentual de capacidade)
- [x] Tornar a aba `Process Mining Jira` visível na navegação de serviços
- [x] Recalcular `Score Capacidade` como percentual no bloco `Capacidade Cruzada (Jira + Bitbucket)`
- [x] Atualizar tabela/gráficos/filtro semanal para refletir score em `%`
- [x] Validar sintaxe/import após ajuste

## Specification (Dashboard Full: aba Process Mining + score percentual de capacidade)
- Objetivo: corrigir visibilidade da aba de Process Mining e apresentar o score de capacidade em formato percentual.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - `Process Mining Jira` aparece como aba em `SERVICE_TABS`.
  - `Score Capacidade` deixa de ser valor absoluto e passa a ser participação percentual no score ponderado do período.
  - Tabela e gráficos da seção `Capacidade Cruzada` exibem o score em `%`.

## Review (Dashboard Full: aba Process Mining + score percentual de capacidade)
- What was validated:
  - A aba `Process Mining Jira` foi incluída explicitamente em `SERVICE_TABS`.
  - O cálculo de `Score Capacidade` foi alterado para:
    - score bruto = `itens concluídos + PRs abertos + aprovações + reprovações + commits/5`;
    - score percentual = `(score bruto da pessoa / soma dos scores brutos no período) * 100`.
  - A visualização semanal da capacidade também passou a calcular o percentual por semana.
  - A tabela da capacidade cruzada agora mostra o valor formatado com sufixo `%`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import dashboard_full as d; print('import ok')"`
  - `rg -n \"tab-process-mining-jira|Score Capacidade \\(%\\)|proxy bruto\" dashboard_full.py`
- Suggested commit message:
  - `fix(dashboard): expose process mining tab and convert cross-capacity score to percentage`

## Current Task (Ajuste do score percentual de capacidade cruzada)
- [x] Revisar definição de percentual do score de capacidade após feedback do usuário
- [x] Trocar cálculo de participação no total por índice relativo ao maior score do período (0–100%)
- [x] Aplicar a mesma regra no cálculo semanal
- [x] Validar sintaxe e exemplo de saída

## Specification (Ajuste do score percentual de capacidade cruzada)
- Objetivo: tornar o `%` de capacidade mais interpretável no ranking por pessoa.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - `Score Capacidade (%)` usa denominador de máximo score bruto do recorte, e não soma total.
  - Maior score do recorte aparece como `100%`.
  - Série semanal usa a mesma lógica (máximo por semana).

## Review (Ajuste do score percentual de capacidade cruzada)
- What was validated:
  - `compute_cross_source_capacity_metrics` agora calcula `%` como `score_bruto_pessoa / maior_score_bruto_do_período * 100`.
  - `compute_cross_source_capacity_weekly_metrics` passou a usar `maior_score_bruto_da_semana` como denominador.
  - Texto explicativo da seção `Capacidade Cruzada` foi atualizado para refletir a nova regra.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... compute_cross_source_capacity_metrics(...) ... print(max Score Capacidade (%)) ... PY`
  - Evidência: `max 100.0` no recorte testado.
- Suggested commit message:
  - `fix(dashboard): normalize cross-capacity score percentage against period max`

## Current Task (Dashboard Full: visão consolidada planejamento do quarter x execução)
- [x] Definir bloco consolidado com os números-chave do período (01/01 a 25/02)
- [x] Aplicar fórmulas de aderência (entregues/planejados e horas executadas/estimadas no quarter)
- [x] Exibir direcionadores de risco e ação imediata no contexto da aba `Performance do Serviço`
- [x] Validar sintaxe e registrar evidências no review

## Specification (Dashboard Full: visão consolidada planejamento do quarter x execução)
- Objetivo: incluir no `dashboard_full.py` uma visão consolidada que traduza métricas do período em direcionamento operacional, explicitando que a referência de horas é o planejamento do quarter (não capacidade do time).
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Nova seção na aba `Performance do Serviço` com:
    - período analisado (01/01 a 25/02),
    - itens planejados, entregues, em andamento,
    - horas executadas, horas estimadas para o quarter e percentual consumido.
  - Percentuais são calculados por fórmula no código (não texto estático).
  - O texto destaca leitura de aderência entre planejamento macro e execução real.
  - Inclui alertas operacionais: média de 8,11h/dev/dia, 28 bloqueios e necessidade de corte/priorização mais cedo na sprint.
  - Inclui as três perguntas críticas de gestão: previsto, risco e ajuste imediato.

## Review (Dashboard Full: visão consolidada planejamento do quarter x execução)
- What was validated:
  - A aba `Performance do Serviço` ganhou um bloco `Visão consolidada: planejamento do quarter x execução real`.
  - Os percentuais centrais são calculados por fórmula no código:
    - `Entregues (%) = itens_entregues / itens_planejados`
    - `Consumo do estimado (%) = horas_executadas / horas_estimadas_quarter`
  - O texto da seção explicita que a referência de horas é o volume estimado do quarter (não capacidade do time).
  - Foram incluídos direcionadores operacionais e as três perguntas críticas de decisão.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(dashboard): add consolidated quarter-plan-vs-execution view in service performance tab`

## Current Task (Dashboard Full: KeyError no bucket 8-15 no Aging)
- [x] Diagnosticar causa do `KeyError: '8-15'` no `render_aging_buckets`
- [x] Ajustar ordenação/categorização de buckets para recortes com categorias ausentes
- [x] Validar sintaxe e smoke test da função de renderização

## Specification (Dashboard Full: KeyError no bucket 8-15 no Aging)
- Objetivo: eliminar falha de renderização do gráfico de aging por TEAM quando um ou mais buckets não aparecem no dataset filtrado.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - `render_aging_buckets` não lança `KeyError` com buckets ausentes (ex.: sem `8-15`).
  - Ordem visual dos buckets permanece estável para os buckets presentes.
  - Código válido em sintaxe.

## Review (Dashboard Full: KeyError no bucket 8-15 no Aging)
- What was validated:
  - A função `render_aging_buckets` foi ajustada para normalizar `AgingBucket`, tratar valores vazios/`NaN` como `Sem data` e calcular `present_buckets` apenas com categorias existentes no recorte atual.
  - A ordenação visual foi preservada pela ordem canônica (`0-7`, `8-15`, `16-30`, `31-60`, `60+`, `Sem data`), mas limitada aos buckets presentes para evitar o `KeyError` no agrupamento interno do Plotly.
  - O gráfico passou a receber `category_orders={'AgingBucket': present_buckets}` para não forçar grupos inexistentes.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... smoke test com dataframe sem bucket 8-15 ... px.bar(...) ... print('smoke_ok', ...) ... PY`
  - `rg -n "present_buckets|category_orders=\\{'AgingBucket'" dashboard_full.py`
- Suggested commit message:
  - `fix(dashboard): avoid plotly keyerror when aging bucket categories are missing after filters`

## Current Task (Diagnóstico: relatório Estatística com dados incorretos)
- [x] Extrair evidências do PDF e reproduzir os números com o mesmo período/filtros
- [x] Validar consistência entre aba `tab-estatistica`, filtros ativos e métrica de lead time selecionada
- [x] Corrigir a origem da divergência no `dashboard_full.py`
- [x] Validar sintaxe e reproduzir os KPIs após a correção
- [x] Registrar review com causa raiz, evidências e sugestão de commit

## Specification (Diagnóstico: relatório Estatística com dados incorretos)
- Objetivo: identificar e corrigir por que o relatório da aba `Estatística Descritiva` não reflete corretamente os dados do período/filtros selecionados.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - A aba `tab-estatistica` usa a mesma base filtrada do dashboard (incluindo `classe_servico`) em vez de recalcular sobre `fato` bruto.
  - Lead Time da aba passa a usar a métrica selecionada (`LeadTime_Selected_Dias`) e não apenas `LeadTime_Dias`.
  - Throughput/WIP permanecem coerentes com o recorte de período/filtros.
  - Código válido em sintaxe.

## Review (Diagnóstico: relatório Estatística com dados incorretos)
- What was validated:
  - O PDF exportado da aba `Estatística Descritiva` (W1NNER, 01/01/2026 a 31/01/2026) mostrava `Throughput` com dados (`Total de Itens = 88`) e, ao mesmo tempo, `Lead Time` sem dados.
  - A causa raiz foi confirmada em dois pontos:
    - **Dados**: no modelo carregado (`PowerBI_Model_20260302_084834.xlsx`), os 89 itens concluídos no período (88 elegíveis) tinham `LeadTime_Dias` nulo, pois `DataBacklog` estava vazio nesse recorte.
    - **Código**: `tab-estatistica` ignorava o dataframe filtrado + métrica selecionada (`LeadTime_Selected_Dias`) e recalculava em cima de `fato` usando `LeadTime_Dias` fixo.
  - A aba foi corrigida para:
    - usar `df_done = df` (recorte filtrado do callback) para métricas de concluídos;
    - aplicar `LeadTime_Selected_Dias` (fallback para `LeadTime_Dias`);
    - manter WIP em base sem filtro de conclusão, mas com os mesmos filtros ativos, incluindo `classe_servico`.
  - Após correção, no mesmo recorte do PDF:
    - `lead_count = 86`, `lead_mean = 10.13`, `lead_p85 = 20.00`;
    - `throughput_total = 88`, `throughput_weeks = 4`.
- Evidence (tests/logs/diff):
  - `pdftotext '/Users/rodrigoalmeidadeoliveira/Downloads/Dashboard de Métricas (Full)-estatística.pdf' /tmp/dashboard_estatistica.txt`
  - `python3 - <<'PY' ... import dashboard_full as d ... print(d.MODEL_FILE, rows_done_period, lead_non_null) ... PY`
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... d.render_tab(... tab='tab-estatistica' ...) ... print('lead_count', ... ) ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(dashboard): align estatistica tab with filtered lead-time metric and active service filters`

## Current Task (CFD detalhado indisponível em todos os projetos)
- [x] Confirmar causa raiz do aviso de modo detalhado indisponível
- [x] Ajustar descoberta de pastas para incluir `../dados/latest` e `../dados`
- [x] Melhorar mensagem de erro do CFD com diagnóstico acionável por causa
- [x] Validar sintaxe e execução básica do fluxo do CFD

## Specification (CFD detalhado indisponível em todos os projetos)
- Objetivo: tornar o carregamento do downstream detalhado robusto para o layout de pastas do projeto e tornar o erro do CFD explícito para evitar diagnóstico ambíguo.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O loader de dados considera também `../dados/latest` e `../dados` além dos diretórios já existentes.
  - Quando o detalhado estiver indisponível, a UI do CFD mostra uma causa específica (sem CSV, sem concluídos no filtro, sem etapas válidas etc.).
  - Código válido em sintaxe.

## Review (CFD detalhado indisponível em todos os projetos)
- What was validated:
  - A pasta informada pelo usuário foi confirmada: em `.../flow-pmo/dados/latest` existia apenas `portfolio-bt-ns-latest-data.csv`, sem arquivos `*-downstream-*-latest-data.csv` por projeto.
  - `_candidate_data_folders()` passou a considerar explicitamente as pastas de projeto `../dados/latest` e `../dados`, além dos diretórios já existentes.
  - A anotação do CFD para modo detalhado indisponível deixou de ser genérica e agora informa causa específica:
    - sem projeto;
    - sem CSV downstream por projeto;
    - filtro sem itens concluídos;
    - ausência de etapas válidas no CSV.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... import dashboard_full as d; print(d.DATA_FOLDERS); print(d._get_cfd_detailed_unavailable_reason(...)) ... PY`
  - `find '/Users/rodrigoalmeidadeoliveira/.../flow-pmo/dados' -maxdepth 3 -type f -name '*-latest-data.csv'`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(cfd): include project dados/latest in downstream discovery and show precise unavailability reasons`

## Current Task (Publicar downstream latest em pasta central latest)
- [x] Atualizar script macOS para copiar aliases `*-downstream-latest-data.csv` para `../dados/latest`
- [x] Atualizar script PowerShell para copiar aliases `*-downstream-latest-data.csv` para `../dados/latest`
- [x] Validar sintaxe dos scripts alterados no ambiente atual

## Specification (Publicar downstream latest em pasta central latest)
- Objetivo: garantir que toda execução de exportação downstream publique automaticamente os aliases `*-downstream-latest-data.csv` na pasta central `.../flow-pmo/dados/latest`.
- Escopo:
  - `run_all_projects_macos.sh`
  - `run_all_projects.ps1`
  - `tasks/todo.md`
- Critério de aceite:
  - Após gerar `*-data.csv`, o script atualiza `*-latest-data.csv` no `OutDir` e replica o mesmo arquivo para `../dados/latest`.
  - A pasta `../dados/latest` é criada automaticamente quando não existir.
  - Scripts permanecem válidos em sintaxe.

## Review (Publicar downstream latest em pasta central latest)
- What was validated:
  - `run_all_projects_macos.sh` agora define `LATEST_DIR` (com fallback para `../dados/latest` relativo ao script), cria a pasta e replica cada `*-latest-data.csv` downstream para esse destino.
  - `run_all_projects.ps1` recebeu a mesma lógica: resolução de `latestDir` (com override via `FLOW_PMO_LATEST_DIR`), criação da pasta e cópia dos aliases downstream para a pasta central.
  - O comportamento anterior de atualizar `*-latest-data.csv` no `OutDir` foi preservado.
- Evidence (tests/logs/diff):
  - `bash -n run_all_projects_macos.sh`
  - `pwsh` não disponível neste ambiente para validação sintática automática do `.ps1`.
  - `git diff -- run_all_projects_macos.sh run_all_projects.ps1 tasks/todo.md`
- Suggested commit message:
  - `feat(pipeline): always publish downstream latest aliases to central dados/latest folder`

## Current Task (Process Mining Jira não encontrado com latest existente)
- [x] Reproduzir resolução de arquivo do Process Mining nos dashboards
- [x] Corrigir descoberta de pastas candidatas para incluir `../dados/latest` e `artifacts/process_mining`
- [x] Tornar seleção de arquivo robusta (priorizar `w1nner-process-mining-latest.xlsx` e validar workbook)
- [x] Validar carregamento em runtime após ajuste

## Specification (Process Mining Jira não encontrado com latest existente)
- Objetivo: eliminar falso negativo de "Relatório de process mining não encontrado" quando o arquivo `w1nner-process-mining-latest.xlsx` já existe.
- Escopo:
  - `dashboard_full.py`
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Ambos os dashboards consideram também `../dados/latest`, `../dados` e `artifacts/process_mining` na busca.
  - A seleção do arquivo prioriza `w1nner-process-mining-latest.xlsx`.
  - Apenas workbooks válidos (com abas esperadas de process mining) são aceitos.

## Review (Process Mining Jira não encontrado com latest existente)
- What was validated:
  - `dashboard_process_mining.py` não incluía `../dados/latest` na busca padrão; agora inclui.
  - `dashboard_full.py` e `dashboard_process_mining.py` passaram a validar workbook antes de aceitar candidato e priorizam o alias estável `w1nner-process-mining-latest.xlsx`.
  - A busca pós-ajuste resolveu com sucesso para `.../dados/latest/w1nner-process-mining-latest.xlsx`.
- Evidence (tests/logs/diff):
  - `python3 - <<'PY' ... import dashboard_process_mining as d; print(d.DATA_FOLDERS); print(d.find_latest_process_mining_report()) ... PY`
  - `python3 - <<'PY' ... import dashboard_full as d; print(d.DATA_FOLDERS); print(d._find_latest_w1nner_process_mining_excel()) ... PY`
  - `python3 -m py_compile dashboard_full.py dashboard_process_mining.py`
  - `git diff -- dashboard_full.py dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `fix(process-mining): prefer validated latest workbook across dashboards`

## Current Task (Process Mining: KPI de concluídos para itens únicos finalizados)
- [x] Revisar a origem do KPI `Itens Concluídos (período)` na aba `Process Mining Jira` e confirmar divergência com unidade de throughput
- [x] Ajustar cálculo para usar itens únicos finalizados no período (base de casos finalizados)
- [x] Ajustar rótulo/layout do card para refletir a nova semântica de vazão
- [x] Validar comportamento com verificação de sintaxe e inspeção do diff

## Specification (Process Mining: KPI de concluídos para itens únicos finalizados)
- Objetivo: alinhar o KPI principal da aba de Process Mining com a unidade de throughput, substituindo contagem agregada por pessoa por contagem de itens únicos finalizados no período.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O card deixa de usar soma de `Itens Concluidos` por responsável quando houver base de casos e passa a refletir `Issue Key` únicos finalizados no período.
  - O rótulo do KPI explicita `itens únicos finalizados` (sem ambiguidade de unidade).
  - O grid de KPIs mantém layout consistente (cards com mesma largura e quebra adequada em desktop/mobile).
  - Código válido em sintaxe.

## Review (Process Mining: KPI de concluídos para itens únicos finalizados)
- What was validated:
  - O KPI principal da aba `tab-process-mining-jira` foi alterado para priorizar contagem de `Issue Key` únicos da base de casos finalizados (`pm_cases`), com filtro adicional de `Done Final Date` válido quando a coluna existe.
  - O fallback para soma de `Itens Concluidos` por pessoa foi mantido apenas para cenários sem `Issue Key` disponível.
  - O rótulo do card foi atualizado para `Itens Únicos Finalizados (período)`, mantendo o layout em grade com `class_name='three columns'`.
  - A base de `Cobertura Técnica` passou a usar o mesmo conjunto de itens finalizados (`finalized_issue_keys`) para manter unidade coerente com throughput.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py`
- Suggested commit message:
  - `fix(process-mining): align throughput KPI to unique finalized items in period`

