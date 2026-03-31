## Current Task (Completar KPIs-resumo na série semanal de Serviço e SLA)
- [x] Mapear a tabela semanal atual e comparar com os cards executivos de `Serviço e SLA`
- [x] Incluir na série semanal os indicadores faltantes de lead time (médio/P85), cadência sugerida, vazão e pressão de fluxo
- [x] Validar sintaxe, revisar diff e registrar review com commit sugerido

## Specification (Completar KPIs-resumo na série semanal de Serviço e SLA)
- Objetivo: fazer a seção `Série semanal de apoio` da aba `Serviço e SLA` refletir também os principais KPIs-resumo exibidos no topo, cobrindo especialmente `Lead Time (médio/P85)`, `Cadência sugerida`, `Vazão` e `Pressão de fluxo`.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Estratégia:
  - reaproveitar os cálculos já usados pelos cards executivos da própria aba para evitar divergência semântica
  - enriquecer a tabela semanal apenas com os indicadores que faltam, preservando os já existentes
  - manter os novos valores numéricos/parciais legíveis para o gráfico de tendência acionado ao clicar na linha da tabela
- Critério de aceite:
  - a série semanal passa a exibir os indicadores de `Lead Time médio`, `Lead Time P85`, `Cadência sugerida`, `Vazão` e `Pressão de fluxo` quando houver base suficiente
  - a leitura semanal continua coerente com os cards-resumo da aba `Serviço e SLA`
  - o dashboard continua válido sintaticamente

## Review (Completar KPIs-resumo na série semanal de Serviço e SLA)
- O que foi ajustado:
  - A função `compute_weekly_service_metrics(...)` em `dashboard_full.py` passou a incluir explicitamente a linha semanal `Pressão de Fluxo (ρ)`, reaproveitando a mesma semântica `ρ = chegada / vazão` já usada nos cards executivos da aba.
  - A mesma série semanal passou a expor `Cadência sugerida (λ Weibull, dias)` por semana, calculada a partir do `fit_weibull_linearized(...)` sobre os itens concluídos da semana e mostrada com valor + faixa de leitura (`~ sprint`, `~ 1 mês`, etc.), mantendo coerência com o KPI de cadência do resumo.
  - Os indicadores de `Lead Time` médio, `Lead Time P85` e `Throughput / semana` foram preservados, então a tabela/gráfico semanal agora cobre os KPIs pedidos sem duplicar a lógica dos cards.
- Evidências de validação:
  - `python -m py_compile dashboard_full.py`
  - revisão do diff em `dashboard_full.py` e `tasks/todo.md`
- Risco residual:
  - a validação desta rodada foi estática; ainda não houve smoke test visual no navegador para conferir a leitura final das novas linhas na `Série semanal de apoio`
- Suggested commit message:
  - `feat(service-sla): add weekly pressure and weibull cadence to support series`

## Current Task (Enriquecer a teal de Serviço e SLA com Weibull e frequência de entregas)
- [x] Localizar o bloco executivo da aba `Serviço e SLA` e a fonte dos parâmetros Weibull já calculados
- [x] Incluir no resumo executivo de SLA os parâmetros `Weibull Shape (k)` e `Weibull Lambda/Scale (λ)`
- [x] Complementar a leitura com a frequência de entregas inferida do `scale` do lead time conforme a referência visual do Troy Magennis
- [x] Validar sintaxe, revisar diff e registrar review com commit sugerido

## Specification (Enriquecer a teal de Serviço e SLA com Weibull e frequência de entregas)
- Objetivo: complementar a leitura executiva da aba `Serviço e SLA` com os parâmetros da distribuição Weibull do lead time e com uma interpretação prática da frequência de entregas baseada no parâmetro `scale (λ)`, alinhada à referência fornecida do Troy Magennis.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Estratégia:
  - reaproveitar o cálculo já existente em `fit_weibull_linearized(...)`, evitando duplicidade de lógica estatística
  - enriquecer o bloco executivo/tile de SLA com `shape`, `lambda/scale` e uma leitura textual curta da cadência de entrega
  - traduzir o `scale` para uma faixa operacional compreensível na UI com base na referência visual anexada (`5 ≈ < 1 semana`, `15 ≈ sprint de 2 semanas`, `30 ≈ 1 mês`)
- Critério de aceite:
  - a aba `Serviço e SLA` passa a exibir `Weibull Shape (k)` e `Weibull Lambda/Scale (λ)` quando houver amostra suficiente
  - a leitura executiva inclui a frequência/cadência de entrega derivada do `scale`
  - o dashboard continua válido sintaticamente

## Review (Enriquecer a teal de Serviço e SLA com Weibull e frequência de entregas)
- O que foi ajustado:
  - A aba `Serviço e SLA` passou a calcular a Weibull do `lead_series` do próprio recorte e a exibir, no topo, um card de `Cadência sugerida` com `Weibull Shape (k)` e `Weibull Lambda/Scale (λ)`.
  - O `Resumo executivo do serviço` agora inclui uma leitura textual ligando `k` e `λ` à cadência de entrega, além de uma linha adicional explicando a aproximação do `scale` em relação à referência visual do Troy Magennis.
  - Foi criado um helper dedicado para traduzir o `scale (λ)` em uma faixa operacional simples (`< 1 semana`, `~ sprint de 2 semanas`, `~ 1 mês`, `> 1 mês`) sem duplicar a lógica estatística.
- Evidências de validação:
  - `python -m py_compile dashboard_full.py`
  - revisão do diff em `dashboard_full.py` e `tasks/todo.md`
- Risco residual:
  - a validação desta rodada foi estática; ainda não houve smoke test visual no navegador para conferir quebra de linha do novo card e a leitura final do texto com dados reais
- Suggested commit message:
  - `feat(dashboard): add weibull delivery cadence insights to service sla summary`

## Current Task (Migrar resumo do One Page para Serviço e SLA e remover a aba)
- [x] Adicionar um resumo executivo mínimo em `Serviço e SLA` com foco em SLA/WIP/pressão
- [x] Remover `tab-one-page` da navegação e da renderização do dashboard
- [x] Limpar código órfão do one page, validar sintaxe e registrar review

## Specification (Migrar resumo do One Page para Serviço e SLA e remover a aba)
- Objetivo: absorver a síntese executiva essencial do `One Page Report` na aba `Serviço e SLA` e, depois disso, remover a aba `One Page Report` do dashboard de serviços.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Estratégia:
  - criar em `Serviço e SLA` um bloco curto de leitura executiva com `Pressão (ρ)` e achados principais orientados a SLA/WIP
  - manter nessa aba apenas sinais compatíveis com a semântica de serviço, sem puxar métricas de process mining exclusivas de `W1NNER`
  - retirar `tab-one-page` do menu e do branch de renderização e remover helpers exclusivos que ficarem sem uso
- Critério de aceite:
  - `Serviço e SLA` passa a exibir um resumo executivo mínimo útil sem depender da antiga aba
  - `One Page Report` deixa de aparecer na navegação de serviços
  - o dashboard continua válido sintaticamente após a remoção

## Review (Migrar resumo do One Page para Serviço e SLA e remover a aba)
- O que foi ajustado:
  - `Serviço e SLA` passou a exibir um resumo executivo mínimo com card de `Pressão (ρ)` e um bloco textual de leitura rápida focado em `SLA`, `pressão`, `WIP` e `vazão`.
  - `One Page Report` foi removido de `SERVICE_TABS` e do branch de renderização do dashboard.
  - os helpers visuais e a função `build_dynamic_one_page_report(...)` foram removidos de `dashboard_full.py`, evitando código morto após a retirada da aba.
- Evidências de validação:
  - `rg -n "tab-one-page|build_dynamic_one_page_report|_one_page_|ONE_PAGE_THEME" dashboard_full.py -S` sem resultados
  - `python -m py_compile dashboard_full.py`
  - revisão do diff em `dashboard_full.py` e `tasks/todo.md`
- Risco residual:
  - a validação desta rodada foi estática; ainda não houve smoke test visual no navegador para conferir proporção final dos cards e do bloco executivo em `Serviço e SLA`
- Suggested commit message:
  - `refactor(dashboard): move minimal executive summary to service sla and remove one page tab`

## Current Task (Avaliar remoção da aba One Page Report de serviços)
- [x] Mapear os indicadores e blocos exibidos hoje no `One Page Report`
- [x] Comparar sobreposição com `Serviço e SLA`, `Painel Fluxo`, `Lead Time` e `Process Mining Jira`
- [x] Registrar recomendação, riscos e proposta de redistribuição dos indicadores

## Specification (Avaliar remoção da aba One Page Report de serviços)
- Objetivo: verificar se a aba `One Page Report` de serviços pode ser removida sem perda relevante de leitura operacional, direcionando seus indicadores para abas já existentes.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Estratégia:
  - identificar quais métricas do one page são apenas um resumo de cálculos já existentes
  - separar o que já tem destino natural em `Serviço e SLA` e `Painel Fluxo`
  - destacar os indicadores que, pela semântica, pertencem mais a `Lead Time` ou `Process Mining Jira`
- Critério de aceite:
  - a avaliação aponta se a remoção é tecnicamente viável
  - a recomendação lista explicitamente o destino sugerido para cada grupo de indicadores
  - os riscos de UX/semântica ficam claros antes de qualquer remoção

## Review (Avaliar remoção da aba One Page Report de serviços)
- Recomendação:
  - a aba `One Page Report` pode ser removida do menu de serviços, porque ela é majoritariamente uma camada de consolidação visual sobre cálculos que já existem em outras abas; não encontrei dependência estrutural que obrigue sua permanência.
  - a remoção não deve ser “delete puro”: alguns blocos precisam ser redistribuídos antes para não perder leitura executiva e para evitar misturar métricas de natureza diferente na aba errada.
- Evidências encontradas:
  - a aba é isolada na navegação por `SERVICE_TABS` e pelo branch `if tab == 'tab-one-page'`, ambos em `dashboard_full.py`; isso indica baixo acoplamento de UI para removê-la.
  - os cálculos-base não são exclusivos do one page: `resolve_project_sla_days(...)` também sustenta `Serviço e SLA`, `compute_flow_bottlenecks(...)` também alimenta `Lead Time`, `compute_cross_source_capacity_metrics(...)` já é usado em outros trechos, e as métricas de WIP/pressão já existem no `Painel Fluxo`.
  - parte do one page é degradada por projeto: `Conformidade`, `Retrabalho`, `Composição da Equipe` e derivados de process mining só são populados para `W1NNER`, o que reduz o valor de manter uma aba “executiva” separada para todos os serviços.
- Redistribuição sugerida:
  - `Serviço e SLA`:
    - manter como destino de `SLA de referência`, `Lead Time mediano/P85`, `Throughput do período`, `Itens entregues`, `% dentro do SLA` e uma leitura rápida tipo “achados principais” focada em SLA/WIP.
    - faz sentido incorporar aqui um card explícito de `Pressão (ρ)` porque hoje a aba já mostra chegadas, vazão e WIP, mas não sintetiza isso em um KPI executivo único.
  - `Painel Fluxo`:
    - destino natural para `Pressão de Fluxo`, `WIP Age`, `Tempo para Commit`, `Entradas`, `Throughput`, `Estoque total`, `Previsibilidade`, `Eficiência` e `Razão Valor/Exec`.
    - o painel já possui quase toda essa semântica e thresholds; ele é o melhor lugar para absorver o papel de “resumo operacional do fluxo”.
  - `Lead Time`:
    - `Ranking de Gargalos` não precisa permanecer no one page, porque a aba `Lead Time` já possui tabela e gráfico de gargalos, além de breakdown percentual por etapa.
  - `Process Mining Jira`:
    - `Conformidade`, `Taxa de Retrabalho`, `Cobertura Técnica`, `Composição da Equipe`, `Commits/PRs/Aprovações` e `PR sem Aprovação` se encaixam melhor aqui do que em `Serviço e SLA`.
    - essas métricas têm natureza de conformidade/engenharia e hoje já convivem com KPIs equivalentes nessa aba.
- Riscos e cuidados:
  - se a aba for removida sem adicionar pelo menos um pequeno bloco de “leitura rápida” em `Serviço e SLA`, o usuário perde a síntese textual hoje presente em `Achados Principais`.
  - mover métricas de process mining para `Serviço e SLA` ou `Painel Fluxo` pode poluir a leitura dessas abas com sinais que só existem para `W1NNER`; por semântica e consistência, o melhor é concentrá-las em `Process Mining Jira`.
  - as variáveis `FLOW_PMO_ONE_PAGE_SLA_DAYS` e `FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP` não devem ser removidas junto com a aba, porque o helper `resolve_project_sla_days(...)` continua sendo usado em `Serviço e SLA`.
- Próximo passo sugerido:
  - etapa 1: adicionar em `Serviço e SLA` um bloco executivo curto com `Pressão (ρ)` + “achados principais” de SLA/WIP.
  - etapa 2: confirmar que `Painel Fluxo` já cobre a leitura executiva de fluxo desejada.
  - etapa 3: remover `tab-one-page` de `SERVICE_TABS`, do callback de renderização e, por último, apagar helpers visuais exclusivos que ficarem órfãos.
- Suggested commit message:
  - `docs(dashboard): evaluate removing one page report and remap its service indicators`

## Current Task (Atualizar configurações de ambiente com SLA de serviço)
- [x] Consolidar os valores dos arquivos anexos e do contexto fornecido
- [x] Atualizar os arquivos de ambiente/exemplo relevantes sem espalhar segredos além do necessário
- [x] Revisar diff, validar coerência entre exemplos e documentação e registrar review

## Specification (Atualizar configurações de ambiente com SLA de serviço)
- Objetivo: alinhar as configurações de ambiente do projeto com os valores do `jira_env (1).txt`, manter o arquivo de exemplo coerente e documentar corretamente a configuração de SLA de serviço no Vercel.
- Escopo:
  - `jira_env.txt`
  - `jira_env.example.txt`
  - `.env.example`
  - `DEPLOY_VERCEL.md`
  - `auth.py`
  - `tasks/todo.md`
- Estratégia:
  - aplicar ao `jira_env.txt` os valores adicionais de SLA de serviço presentes no contexto
  - ajustar os exemplos para refletirem o uso atual de `FLOW_PMO_ALLOWED_EMAILS` e os valores de SLA citados pelo usuário
  - incluir na documentação de deploy a orientação explícita sobre `FLOW_PMO_ONE_PAGE_SLA_DAYS` e `FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP`
- Critério de aceite:
  - `jira_env.txt` passa a incluir as variáveis de SLA de serviço com os valores alinhados ao contexto informado
  - `jira_env.example.txt` e `.env.example` deixam instruções consistentes com o fluxo atual do projeto
  - `DEPLOY_VERCEL.md` passa a documentar claramente a configuração dessas variáveis no Vercel

## Review (Atualizar configurações de ambiente com SLA de serviço)
- O que foi ajustado:
  - `jira_env.txt` passou a incluir `FLOW_PMO_ONE_PAGE_SLA_DAYS=5` e `FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP={"W1NNER":5,"S1NC":5,"BEFINANCE":5,"DATA&ANALYTICS":5}`, alinhados ao arquivo anexado, e o bloco duplicado de `BB_EMAIL`/`BB_TOKEN`/`BB_WORKSPACE` foi removido.
  - `jira_env.example.txt` foi expandido para refletir melhor a estrutura de configuração usada no projeto, incluindo variáveis de Bitbucket, diretórios auxiliares e os exemplos atualizados de SLA.
  - `.env.example` foi corrigido com o redirect URI real (`https://flow-pmo.vercel.app/callback` e `http://localhost:3000/callback`), com instruções alinhadas ao uso atual de `FLOW_PMO_ALLOWED_EMAILS` e com as variáveis de SLA para o ambiente da Vercel.
  - `DEPLOY_VERCEL.md` agora documenta explicitamente como cadastrar `FLOW_PMO_ONE_PAGE_SLA_DAYS` e `FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP` em `Settings -> Environment Variables` com scope `Production`, além de registrar o comportamento atual do SLA aging do portfólio.
  - `auth.py` teve apenas o cabeçalho documental ajustado para refletir que `FLOW_PMO_ALLOWED_DOMAIN` é usado como hint/tenant label e que o controle principal atual é a allowlist por e-mail ou, futuramente, por grupo.
- Evidências de validação:
  - revisão do diff em `.env.example`, `DEPLOY_VERCEL.md`, `auth.py`, `jira_env.example.txt`, `jira_env.txt` e `tasks/todo.md`
  - busca dirigida com `rg` confirmando a presença das variáveis `FLOW_PMO_ONE_PAGE_SLA_DAYS`, `FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP`, `FLOW_PMO_ALLOWED_GROUP` e do redirect URI `https://flow-pmo.vercel.app/callback`
  - checagem dirigida em `jira_env.txt` confirmando bloco único de `BB_EMAIL`/`BB_TOKEN`/`BB_WORKSPACE` e presença dos SLAs
- Risco residual:
  - a validação desta rodada foi estática; não houve teste de login OAuth nem publicação real das env vars no painel da Vercel
- Suggested commit message:
  - `docs(env): align sla and auth environment configuration with vercel setup`

## Current Task (Aplicar filtro de etapa no Painel de Fluxo)
- [x] Localizar exatamente onde a aba `Painel Fluxo` ignora o filtro `Etapa de Fluxo (WIP)`
- [x] Corrigir os cálculos de WIP/estoque do `tab-painel-3x3` para respeitar a etapa atual selecionada
- [x] Validar sintaxe, revisar diff e registrar review

## Specification (Aplicar filtro de etapa no Painel de Fluxo)
- Objetivo: fazer a aba `Painel Fluxo` respeitar o filtro `Etapa de Fluxo (WIP)` nos indicadores e análises de WIP/estoque, preservando a semântica já existente do filtro de lead time.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Estratégia:
  - rastrear o callback `tab-painel-3x3` e comparar com as abas que já aplicam `filter-etapa-fluxo`
  - centralizar a filtragem por etapa atual em helper reaproveitável para evitar divergência entre abas
  - aplicar o filtro apenas aos subconjuntos de itens ativos/WIP do painel, sem descartar os concluídos usados nas métricas de lead time
- Critério de aceite:
  - indicadores como `WIP`, `WIP Age (médio)`, `Estoque total` e séries semanais do painel variam conforme a seleção de `Etapa de Fluxo (WIP)`
  - métricas de lead time continuam baseadas em `LeadTime_Selected_Dias`/`Commitment_Selected`
  - o arquivo continua válido sintaticamente

## Review (Aplicar filtro de etapa no Painel de Fluxo)
- O que foi ajustado:
  - [`dashboard_full.py`](c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/dashboard_full.py) ganhou o helper `filter_items_by_current_stage(...)` para centralizar a filtragem pela etapa atual do downstream sem duplicar lógica entre abas.
  - a aba `tab-painel-3x3` passou a aplicar `filter-etapa-fluxo` especificamente nos subconjuntos de WIP/estoque usados em `weekly_df`, `weekly_hist_df`, `df_wip_start` e `df_wip_end`, fazendo com que `WIP`, `WIP Age (médio)` e `Estoque total` respondam à seleção da etapa atual.
  - a base histórica de referência do painel agora também recalcula `Commitment_Selected` via [`dashboard_full.py`](c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/dashboard_full.py), mantendo os thresholds/statuses coerentes com o mesmo filtro de etapas de lead time.
  - as abas que já usavam a mesma semântica (`Fluxo`, `Work Item Age` e `WIP por Pessoa`) passaram a reaproveitar o mesmo helper, reduzindo risco de regressão por regras divergentes.
- Causa raiz encontrada:
  - o callback `render_tab(..., tab='tab-painel-3x3', ...)` recebia `etapa_fluxo`, mas o bloco do painel não aplicava esse filtro aos recortes de WIP/estoque; por isso os números ficavam praticamente invariáveis mesmo com a seleção no dropdown.
- Evidências de validação:
  - `python -m py_compile dashboard_full.py`
  - revisão do diff em `dashboard_full.py` e `tasks/todo.md`
- Risco residual:
  - a validação nesta rodada foi estática; ainda não houve smoke test visual no navegador com a seleção real das etapas
- Suggested commit message:
  - `fix(dashboard): apply current flow stage filter to painel fluxo wip metrics`

## Current Task (Exibir unidade nos indicadores do Painel Fluxo)
- [x] Localizar onde os cards executivos do `Painel Fluxo` descartam a unidade configurada
- [x] Ajustar a renderização para mostrar a unidade do indicador quando ela existir
- [x] Validar sintaxe, revisar diff e registrar review

## Specification (Exibir unidade nos indicadores do Painel Fluxo)
- Objetivo: fazer os cards executivos do `Painel Fluxo` exibirem explicitamente a unidade das métricas temporais e demais métricas que já possuem `unit` configurado.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Estratégia:
  - reaproveitar o campo `unit` já presente no `metric_catalog`
  - corrigir a função de renderização dos cards executivos, em vez de tratar cada indicador manualmente
- Critério de aceite:
  - cards como `Tempo para Commit (P85)` e `WIP Age (médio)` passam a mostrar a unidade visível
  - a mudança não altera o cálculo das métricas
  - o arquivo continua válido sintaticamente

## Review (Exibir unidade nos indicadores do Painel Fluxo)
- O que foi ajustado:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L12020) passou a reaproveitar `metric['unit']` também nos cards executivos do `Painel Fluxo`, exibindo a unidade logo abaixo do valor principal quando ela existir.
  - a correção foi centralizada na montagem dos cards, então indicadores como `Tempo para Commit (P85)` e `WIP Age (médio)` passam a mostrar `dias` sem alterar cálculo, thresholds ou catálogo de métricas.
- Evidências de validação:
  - `python -m py_compile dashboard_full.py`
  - revisão do diff em `dashboard_full.py` e `tasks/todo.md`
- Risco residual:
  - a validação nesta rodada foi estática; ainda não houve inspeção visual no navegador
- Suggested commit message:
  - `fix(dashboard): show units on flow executive indicator cards`

## Current Task (Diagnosticar backlog não comprometido zerado)
- [x] Mapear a regra implementada do indicador no `Painel Fluxo`
- [x] Reproduzir o cálculo com os dados locais e comparar com o backlog visível no fluxo
- [x] Registrar a causa raiz, evidências e sugestão de commit

## Specification (Diagnosticar backlog não comprometido zerado)
- Objetivo: explicar por que o card `Backlog não comprometido` pode exibir `0` mesmo quando há itens em backlog no fluxo visível.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Estratégia:
  - rastrear a formação de `Commitment_Selected` e do snapshot final de backlog
  - confrontar a definição do card com a definição operacional de backlog usada em outras partes do dashboard
  - validar a hipótese com os dados locais disponíveis
- Critério de aceite:
  - a explicação identifica a condição exata que zera o card
  - há evidência no código e, quando possível, nos dados locais

## Review (Diagnosticar backlog não comprometido zerado)
- O que foi ajustado:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L7825) deixou de aceitar o próprio `DataBacklog` como fallback de `Commitment_Selected`; agora o fallback só vale quando a data candidata está estritamente depois da entrada em backlog.
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L552) passou a tratar `To Do`, `Todo` e `Discovery` como etapas backlog-like para o cálculo de compromisso, evitando que esses estágios virem “compromisso” por padrão no fluxo de `DATA&ANALYTICS`.
- Causa raiz encontrada:
  - o card `Backlog não comprometido` usa `df_backlog_end`, que considera backlog apenas quando `Commitment_Selected` está vazio ou depois do fim do período.
  - antes da correção, `Commitment_Selected` era inicializado com `LeadStart_Selected`; quando não havia etapa real de compromisso, esse valor podia cair no próprio `DataBacklog`, fazendo o item parecer comprometido no mesmo instante em que entrou em backlog.
  - com isso, itens ainda em `Triagem`/`Backlog` eram removidos artificialmente do backlog não comprometido e o card podia zerar.
- Evidências de validação:
  - reprodução com os CSVs `latest` locais mostrou itens abertos em backlog sem `Ready to Start`/`In progress`:
    - `W1NNER`: `32`
    - `S1NC`: `101`
    - `BEFINANCE`: `28`
  - validação dirigida da regra antiga vs nova:
    - `S1NC`: `STRICT_UNCOMMITTED=101 | OLD_FALSE_COMMITTED=101 | NEW_STILL_UNCOMMITTED=101`
    - `BEFINANCE`: `STRICT_UNCOMMITTED=28 | OLD_FALSE_COMMITTED=28 | NEW_STILL_UNCOMMITTED=28`
  - validação adicional para `DATA&ANALYTICS` após marcar `To Do`/`Discovery` como backlog-like:
    - `OPEN=158 | OLD_STRICT_UNCOMMITTED=0 | NEW_STRICT_UNCOMMITTED=15`
- Risco residual:
  - não consegui rodar `python -m py_compile` nesta sessão porque o ambiente local está sem um interpretador Python funcional no PATH e o `venv` versionado aponta para um runtime de macOS inexistente no Windows atual.
- Suggested commit message:
  - `fix(flow): stop treating backlog entry as commitment for uncommitted backlog KPI`

## Current Task (Unificar Highest no projeto)
- [x] Mapear onde `Expedite`, `Urgente` e `Higest` ainda são derivados ou exibidos
- [x] Ajustar normalização e labels para usar sempre `Highest`
- [x] Validar sintaxe, revisar diff e confirmar os pontos principais impactados
- [x] Registrar review e sugestão de commit

## Specification (Unificar Highest no projeto)
- Objetivo: padronizar a prioridade/classe mais alta como `Highest` em todo o projeto, eliminando traduções para `Expedite`, `Urgente` e o typo `Higest` em gráficos, filtros e visões derivadas.
- Escopo:
  - `dashboard_full.py`
  - `dash_board_metricas.py`
  - `tasks/todo.md`
- Estratégia:
  - tratar `Higest` como alias de entrada, mas nunca como label de saída
  - remover fallbacks que convertem `Highest` em `Expedite` ou `Urgente`
  - preservar a semântica operacional existente, mantendo regras que detectam a classe/prioridade mais alta mesmo após a troca do rótulo
- Critério de aceite:
  - filtros e datasets derivados passam a expor `Highest` em vez de `Expedite`/`Urgente` quando o caso é a prioridade máxima
  - valores `Higest` continuam sendo reconhecidos, mas são exibidos como `Highest`
  - não surgem erros de sintaxe após a alteração

## Review (Unificar Highest no projeto)
- O que foi ajustado:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora canonicaliza `Expedite`, `Urgente` e `Higest` para `Highest` antes de derivar `Prioridade`, `ClasseServico`, filtros de portfólio e classificações de urgência
  - filtros e visões derivadas deixaram de reconverter `Highest` para `Expedite`/`Urgente`, inclusive na governança de fast track, nos KPIs e nos gráficos de breakdown
  - [`dash_board_metricas.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dash_board_metricas.py) passou a gerar `Highest` no modelo consolidado e a medir a participação dessa classe sem depender do literal `Expedite`
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py dash_board_metricas.py`
  - `python3 - <<'PY' ... ast.parse(...) ... PY`
  - checagem dirigida da normalização:
    - `Expedite -> Highest`
    - `Urgente -> Highest`
    - `Higest -> Highest`
    - `classify_urgency_label({'ClasseServico': 'Urgente', 'Prioridade': 'Higest'}) -> Highest`
- Risco residual:
  - não houve smoke test visual no navegador nesta rodada; a validação foi estática e por funções isoladas
- Suggested commit message:
  - `refactor(dashboard): unify highest priority labels across filters and charts`

## Current Task (Equalizar densidade dos KPIs em Work Item Age)
- [x] Registrar a nova correção visual em `tasks/lessons.md`
- [x] Ajustar a distribuição vertical do painel principal
- [x] Validar sintaxe e revisar diff
- [x] Registrar review e sugestão de commit

## Specification (Equalizar densidade dos KPIs em Work Item Age)
- Objetivo: remover o vazio vertical do bloco `Itens Ativos` para que os três painéis do topo tenham densidade visual mais equilibrada.
- Escopo:
  - `assets/work-item-age.css`
  - `tasks/todo.md`
  - `tasks/lessons.md`
- Estratégia:
  - eliminar a distribuição vertical com muito espaço sobrando no primeiro painel
  - aproximar a distância entre título, valor, descrição e mini-KPIs
  - preservar a estrutura de agrupamento já criada
- Critério de aceite:
  - o primeiro painel deixa de parecer “esticado”
  - a densidade interna dos três blocos fica mais próxima
  - o visual continua claro e consistente com o dashboard

## Review (Equalizar densidade dos KPIs em Work Item Age)
- O que foi ajustado:
  - o painel `Itens Ativos` em [`assets/work-item-age.css`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/assets/work-item-age.css) deixou de usar distribuição vertical com espaço sobrando e passou a agrupar o conteúdo no topo com espaçamento controlado
  - o valor principal, a legenda e os mini-KPIs foram compactados para aumentar a densidade visual e aproximar o primeiro bloco dos painéis vizinhos
  - os painéis laterais também receberam alinhamento interno mais consistente via `flex` e `gap`, reduzindo diferenças artificiais entre as colunas
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
- Risco residual:
  - ainda não houve inspeção visual no navegador nesta sessão
- Suggested commit message:
  - `refactor(dashboard): equalize work item age panel density`

## Current Task (Reequilibrar layout dos KPIs em Work Item Age)
- [x] Registrar a correção visual do usuário em `tasks/lessons.md`
- [x] Ajustar o layout para fundo claro e proporções mais consistentes
- [x] Validar sintaxe e revisar diff
- [x] Registrar review e sugestão de commit

## Specification (Reequilibrar layout dos KPIs em Work Item Age)
- Objetivo: corrigir o excesso de contraste e a desproporção da refatoração anterior, aproximando a aba `Work Item Age` do padrão visual claro e equilibrado do dashboard.
- Escopo:
  - `assets/work-item-age.css`
  - `tasks/todo.md`
  - `tasks/lessons.md`
- Estratégia:
  - manter a organização semântica criada anteriormente
  - remover o destaque escuro dominante
  - equalizar alturas, espaçamentos e peso visual entre os grupos de KPIs
- Critério de aceite:
  - a seção usa fundo claro
  - os blocos ficam visualmente proporcionais entre si
  - a leitura permanece agrupada, mas com padrão coerente com o restante da aplicação

## Review (Reequilibrar layout dos KPIs em Work Item Age)
- O que foi ajustado:
  - a seção em [`assets/work-item-age.css`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/assets/work-item-age.css) deixou de usar o destaque escuro dominante e passou para superfícies claras compatíveis com o padrão do dashboard
  - o bloco principal de `Itens Ativos` foi rebaixado visualmente para o mesmo idioma dos demais painéis, preservando destaque sem quebrar o conjunto
  - os cards passaram a ter altura mínima, padding e escala tipográfica mais consistentes, reduzindo a sensação de desproporção
  - o layout responsivo foi ajustado para manter grids equilibrados em larguras intermediárias e empilhar apenas quando necessário
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
- Risco residual:
  - continua faltando inspeção visual em navegador nesta sessão
- Suggested commit message:
  - `refactor(dashboard): rebalance work item age kpi layout`

## Current Task (Refatorar layout dos KPIs em Work Item Age)
- [x] Localizar a implementação da aba e revisar restrições do projeto
- [x] Reorganizar os KPIs com hierarquia visual e agrupamento semântico
- [x] Ajustar a responsividade da seção para desktop e mobile
- [x] Validar sintaxe/import e registrar review
- [x] Registrar sugestão de commit

## Specification (Refatorar layout dos KPIs em Work Item Age)
- Objetivo: tornar a leitura dos KPIs da aba `Work Item Age` mais clara e operacional, reduzindo a sensação de cards soltos e melhorando a hierarquia visual do topo da tela.
- Escopo:
  - `dashboard_full.py`
  - `assets/work-item-age.css`
  - `tasks/todo.md`
- Estratégia:
  - substituir a grade uniforme atual por um resumo com bloco principal + grupos de apoio
  - separar semanticamente volume, aging e risco para reduzir ruído visual
  - usar estilos específicos da aba, sem alterar o comportamento das demais telas
- Critério de aceite:
  - a área inicial de `Work Item Age` deixa de exibir os oito KPIs como uma sequência uniforme de cards
  - os indicadores passam a ter hierarquia visual perceptível
- o layout continua legível em larguras menores
- a lógica de cálculo dos indicadores permanece inalterada

## Review (Refatorar layout dos KPIs em Work Item Age)
- O que foi implementado:
  - o topo da aba `Work Item Age` em [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) deixou de usar uma grade uniforme de oito cards
  - a seção agora foi reorganizada em três blocos: destaque principal de volume, painel de envelhecimento e painel de risco operacional
  - o resumo principal passou a destacar `Itens Ativos` com apoio imediato de `Críticos` e `Bloqueados`, reduzindo a dispersão visual dos números mais acionáveis
  - os KPIs de aging e saúde continuam usando a mesma lógica de cálculo, mas com agrupamento semântico e tratamento visual distinto
  - estilos específicos e responsivos foram adicionados em [`assets/work-item-age.css`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/assets/work-item-age.css) sem alterar outras abas
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import dashboard_full; print('import ok')"` falhou por ausência de `dash` no ambiente atual (`ModuleNotFoundError: No module named 'dash'`)
- Risco residual:
  - não houve inspeção visual no navegador nesta rodada
  - a responsividade foi tratada por CSS, mas sem smoke test interativo local por falta do runtime completo
- Suggested commit message:
  - `refactor(dashboard): reorganize work item age kpis`

## Current Task (Unificar visão de serviço/SLA para itens básicos)
- [x] Mapear métricas e regras já existentes no dashboard atual
- [x] Reestruturar a aba principal de serviço para consolidar SLA, vazão e WIP no mesmo lugar
- [x] Exibir lead time por tipo de demanda e por urgência com média e P85
- [x] Exibir vazão por tipo de demanda e por urgência com média e percentis
- [x] Exibir trabalho em progresso com visão operacional do recorte atual
- [x] Validar a renderização por sintaxe/execução local e registrar review
- [x] Registrar sugestão de commit

## Specification (Unificar visão de serviço/SLA para itens básicos)
- Objetivo: permitir leitura rápida, por projeto e período selecionados, dos indicadores principais de serviço para responder perguntas de SLA sem navegar por várias abas redundantes.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Estratégia:
  - reutilizar as regras já existentes de filtro, lead time selecionado, entregas elegíveis, classificação de urgência e WIP
  - concentrar na aba principal de serviço uma visão única com resumo executivo + tabelas/gráficos de SLA por tipo e urgência
  - reduzir a dependência do usuário em alternar entre `Performance do Serviço`, `One Page Report`, `Throughput Breakdown` e painéis auxiliares para obter a leitura operacional básica
- Critério de aceite:
  - com projeto e período filtrados, a tela principal de serviço mostra rapidamente:
    - lead time por tipo de demanda com média e P85
    - lead time por urgência com média e P85
    - vazão por tipo de demanda com média e percentis
    - vazão por urgência com média e percentis
    - WIP atual e aging operacional do WIP
- a implementação reutiliza a lógica existente de filtros e não cria regras paralelas para cálculo das métricas
- a aba fica compreensível sem exigir navegação imediata para outras abas

## Review (Unificar visão de serviço/SLA para itens básicos)
- O que foi implementado:
  - a aba `tab-performance` foi reposicionada como `Serviço e SLA`, deixando de priorizar a visão dispersa de quarter/execução e passando a abrir com uma leitura operacional de SLA
  - o topo agora mostra cards com SLA de referência, lead time médio/P85, vazão média/P85 por bucket do período, itens entregues, WIP atual e percentual dentro do SLA
  - a mesma aba agora traz tabelas explícitas de lead time por tipo de demanda e por urgência, com `Itens`, `Lead Médio`, `Lead P50`, `Lead P85` e `% SLA`
  - a mesma aba agora traz tabelas de vazão por tipo e por urgência, com `Itens Entregues`, `Média/Bucket`, `P50`, `P85` e `Máx Bucket`
  - a mesma aba agora traz WIP atual por tipo e por urgência, com `Itens em WIP`, `Age Médio`, `Age P85` e `Mais Antigo`
  - o quadro semanal antigo foi mantido como série de apoio, em vez de permanecer como fonte principal de leitura
- Reuso de regra de negócio:
  - SLA por projeto foi extraído para `resolve_project_sla_days(...)`
  - a visão nova reutiliza `apply_selected_lead_time_metric(...)`, `build_delivered_items_base(...)`, `time_metric_series(...)`, `weekly_bucket_start(...)` e `classify_urgency_label(...)`
  - isso evitou duplicar critérios de lead time selecionado, elegibilidade de concluídos e classificação de urgência
- Evidências de validação:
  - `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import dashboard_full; print('import ok')"`
  - smoke test do callback principal:
    - `python3 -c "import dashboard_full, pandas as pd; ...; out=dashboard_full.render_tab('services','tab-performance',...); print(type(out).__name__, projeto, start, end)"`
    - resultado: `Div BEFINANCE 2024-05-08 2026-03-19`
- Risco residual:
  - a validação foi de bootstrap e callback em Python; não houve inspeção visual interativa no navegador nesta rodada
- Suggested commit message:
  - `feat(dashboard): unify service SLA view for lead time, throughput and wip`


## Current Task (BusinessMap: gravar datas como células de data do Excel)
- [x] Inspecionar o XLSX gerado e confirmar o tipo real das colunas `Start Date` e `End Date`
- [x] Ajustar o exportador para gravar datas como células de data nativas do Excel
- [x] Validar com novo lote do BeFinance e registrar orientação de reimportação
- [x] Registrar review e sugestão de commit

## Specification (BusinessMap: gravar datas como células de data do Excel)
- Objetivo: eliminar os avisos do BusinessMap que ignoram `Data de Início` e `Data de Término` por incompatibilidade de formato no XLSX.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - `Start Date` e `End Date` deixam de ser gravadas como texto no XLSX.
  - As células dessas colunas passam a ser do tipo data/datetime no Excel com formato consistente.
  - Novo export do BeFinance mantém os lotes de 100 e traz datas compatíveis.

## Review (BusinessMap: gravar datas como células de data do Excel)
- What was validated:
  - O lote anterior gravava `Start Date`/`End Date` como texto (`str`) com `number_format = General`, por exemplo `BF-264` com `2026-03-16` e `2026-03-20`; isso explica o aviso do BusinessMap ao tentar atualizar as datas.
  - [`jira_to_businessmap_xlsx.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_to_businessmap_xlsx.py) agora converte `Deadline`, `Created at`, `Start Date` e `End Date` para datas reais antes do `to_excel` e aplica `number_format = yyyy-mm-dd`.
  - O novo export do BeFinance foi gerado em lotes com arquivos `businessmap-befinance-datesfix-lote-1.xlsx`, `businessmap-befinance-datesfix-lote-2.xlsx` e `businessmap-befinance-datesfix-lote-3.xlsx`.
  - No lote novo, `BF-264` e demais exemplos passaram a sair como `datetime` no Excel, com formato `yyyy-mm-dd`, o que é compatível com importadores que esperam célula de data em vez de texto.
- Evidence (tests/logs/diff):
  - `python3 -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python3 jira_to_businessmap_xlsx.py --projects BF BT --mapping-preset bf --jql 'project IN (BT, BF) AND issuetype IN (Bug, Story, Spike, Support, Task, Tech, "User Story") AND "team[team]" = b87876b2-78cd-4b67-bbcf-37ba395e5f39 ORDER BY created DESC' --out /Users/rodrigoalmeidadeoliveira/Documents/dados/bmap/businessmap-befinance-datesfix.xlsx`
  - `python3 - <<'PY' ... load_workbook('/Users/rodrigoalmeidadeoliveira/Documents/dados/bmap/businessmap-befinance-datesfix-lote-1.xlsx') ... PY`
- Suggested commit message:
  - `fix(integration): write businessmap dates as excel date cells`

## Current Task (BusinessMap: aplicar env-file antes dos defaults da CLI)
- [x] Confirmar a causa raiz do split automático não ter funcionado
- [x] Corrigir a ordem de carregamento do `jira_env.txt` no exportador
- [x] Validar com execução real do BeFinance em lotes de 100
- [x] Registrar review e sugestão de commit

## Specification (BusinessMap: aplicar env-file antes dos defaults da CLI)
- Objetivo: fazer com que os defaults baseados em variáveis de ambiente do exportador reflitam corretamente os valores definidos em `jira_env.txt`.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - `jira_env.txt` é carregado antes da construção dos defaults do `argparse`.
  - `BUSINESSMAP_SPLIT_SIZE=100` passa a valer sem necessidade de informar `--split-size`.
  - Execução real do BeFinance gera arquivos em lotes de até 100 cartões.

## Review (BusinessMap: aplicar env-file antes dos defaults da CLI)
- What was validated:
  - A causa raiz era o carregamento tardio de [`jira_env.txt`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_env.txt): o parser lia `os.getenv(...)` antes de `load_env_file(...)`, então defaults como `BUSINESSMAP_SPLIT_SIZE`, `BUSINESSMAP_OUT_DIR` e outros valores vindos do arquivo não eram aplicados à CLI.
  - [`jira_to_businessmap_xlsx.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_to_businessmap_xlsx.py) agora faz um pré-parse de `--env-file`, carrega o arquivo e só depois monta o parser principal.
  - A execução real do recorte BeFinance em `2026-03-20` passou a respeitar o `BUSINESSMAP_SPLIT_SIZE=100`, gerando `3` arquivos em `/Users/rodrigoalmeidadeoliveira/Documents/dados/bmap`: `businessmap-befinance-lote-1.xlsx`, `businessmap-befinance-lote-2.xlsx` e `businessmap-befinance-lote-3.xlsx`.
- Evidence (tests/logs/diff):
  - `python3 jira_to_businessmap_xlsx.py --help`
  - `python3 -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python3 jira_to_businessmap_xlsx.py --projects BF BT --mapping-preset bf --jql 'project IN (BT, BF) AND issuetype IN (Bug, Story, Spike, Support, Task, Tech, "User Story") AND "team[team]" = b87876b2-78cd-4b67-bbcf-37ba395e5f39 ORDER BY created DESC' --out /Users/rodrigoalmeidadeoliveira/Documents/dados/bmap/businessmap-befinance.xlsx`
- Suggested commit message:
  - `fix(integration): load env file before businessmap cli defaults`

## Current Task (BusinessMap: limitar importação a 100 cartões por arquivo)
- [x] Confirmar se o exportador já suporta divisão em lotes
- [x] Configurar o padrão do projeto para no máximo 100 cartões por arquivo
- [x] Validar help/comportamento e registrar impacto nos comandos
- [x] Registrar review e sugestão de commit

## Specification (BusinessMap: limitar importação a 100 cartões por arquivo)
- Objetivo: garantir que os arquivos gerados para importação no BusinessMap respeitem o limite operacional de até 100 cartões por arquivo.
- Escopo:
  - `jira_env.txt`
  - `tasks/todo.md`
- Critério de aceite:
  - Exportador passa a usar `split-size = 100` por padrão no ambiente do projeto.
  - Quando o total exceder 100 cartões, os arquivos saem separados com sufixo de lote.
  - CLI/help continuam consistentes.

## Review (BusinessMap: limitar importação a 100 cartões por arquivo)
- What was validated:
  - O exportador já tinha suporte nativo a lotes via `--split-size` e usa sufixo `-lote-N` quando o volume excede o limite.
  - [`jira_env.txt`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_env.txt) agora define `BUSINESSMAP_SPLIT_SIZE=100`, tornando o limite padrão do projeto aderente à regra do BusinessMap.
  - Como o recorte BeFinance validado anteriormente retorna `248` itens, a partir desta configuração ele tende a gerar automaticamente `3` arquivos (`100 + 100 + 48`) quando executado sem sobrescrever `--split-size`.
- Evidence (tests/logs/diff):
  - `python3 jira_to_businessmap_xlsx.py --help | rg -n "split-size|100"`
  - `python3 - <<'PY' ... m.load_env_file('jira_env.txt'); print(os.getenv('BUSINESSMAP_SPLIT_SIZE')) ... PY`
- Impacto prático nos comandos:
  - Não precisa acrescentar `--split-size 100` manualmente, a menos que queira sobrescrever o padrão.
  - Os exports podem passar a gerar múltiplos arquivos como `businessmap-befinance-lote-1.xlsx`, `businessmap-befinance-lote-2.xlsx`, etc.
- Suggested commit message:
  - `chore(integration): default businessmap export batches to 100 cards`

## Current Task (BusinessMap: configurar diretório padrão de saída)
- [x] Revisar como o exportador resolve o caminho default dos XLSX
- [x] Configurar o diretório padrão para `/Users/rodrigoalmeidadeoliveira/Documents/dados/bmap`
- [x] Validar help/import/sintaxe e registrar comandos atualizados
- [x] Registrar review e sugestão de commit

## Specification (BusinessMap: configurar diretório padrão de saída)
- Objetivo: fazer com que os arquivos de migração BusinessMap sejam gerados por padrão em `/Users/rodrigoalmeidadeoliveira/Documents/dados/bmap`.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `jira_env.txt`
  - `tasks/todo.md`
- Critério de aceite:
  - Exportador respeita um diretório padrão configurável para os XLSX.
  - `jira_env.txt` aponta para a pasta informada.
  - CLI/help/import/sintaxe continuam válidos.

## Review (BusinessMap: configurar diretório padrão de saída)
- What was validated:
  - [`jira_to_businessmap_xlsx.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_to_businessmap_xlsx.py) agora respeita `BUSINESSMAP_OUT_DIR` ao montar o caminho default de saída.
  - [`jira_env.txt`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_env.txt) foi configurado com `BUSINESSMAP_OUT_DIR=/Users/rodrigoalmeidadeoliveira/Documents/dados/bmap`.
  - A resolução default ficou validada para `BT` em `2026-03-20`: `/Users/rodrigoalmeidadeoliveira/Documents/dados/bmap/businessmap-import-bt-20260320.xlsx`.
- Evidence (tests/logs/diff):
  - `python3 jira_to_businessmap_xlsx.py --help`
  - `python3 -c "import jira_to_businessmap_xlsx as m; m.load_env_file('jira_env.txt'); print(m.default_out_path(['BT']))"`
  - `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
- Comandos atualizados:
  - `python3 jira_to_businessmap_xlsx.py --projects BT --jql 'project = BT AND issuetype = Epic ORDER BY Rank ASC'`
  - `python3 jira_to_businessmap_xlsx.py --projects BT --jql 'project in (10526) AND issuetype in (10254) ORDER BY Rank ASC'`
- Suggested commit message:
  - `feat(integration): allow configurable businessmap output directory`

## Current Task (BusinessMap BF/BT: aceitar JQL completa no exportador)
- [x] Revisar a limitação atual de `--projects` + `--jql-extra` frente à query real de BeFinance
- [x] Ajustar o exportador para aceitar JQL completa com precedência sobre a montagem automática
- [x] Validar help/import/sintaxe e registrar o comando recomendado para a query `BT + BF`
- [x] Registrar review e sugestão de commit

## Specification (BusinessMap BF/BT: aceitar JQL completa no exportador)
- Objetivo: permitir rodar a migração BusinessMap com a JQL exata informada para BeFinance, incluindo `project IN (BT, BF)`, filtro de `issuetype`, filtro de `team[team]` e `ORDER BY` próprio.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Exportador aceita `--jql` completa sem reescrever `project in (...)`.
  - `--jql` tem precedência sobre `--projects` e `--jql-extra`.
  - CLI/help/import/sintaxe continuam válidos.

## Review (BusinessMap BF/BT: aceitar JQL completa no exportador)
- What was validated:
  - [`jira_to_businessmap_xlsx.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_to_businessmap_xlsx.py) agora aceita `--jql` completa com precedência sobre a montagem automática por `--projects` + `--jql-extra`.
  - `--projects` deixou de ser obrigatório quando a consulta completa já vem em `--jql`; quando informado, continua sendo útil para nome de saída/preset.
  - O preset de tipo BF também passou a converter `Story` e `User Story` para `História`, alinhando o export com o recorte real informado.
  - A query real de BeFinance foi executada com sucesso em `2026-03-20`: `248` issues retornadas, com `Column name` somente em `BACKLOG`, `DONE`, `IN PROGRESS`, `READY CODE REVIEW`, `READY TESTING/QA`, `READY TO START`, `STAGING`, `TRIAGEM`.
  - Após o ajuste de tipo, o XLSX dessa query ficou com `Type name` em `História=247` e `Tech=1`; `User Story` deixou de vazar como tipo bruto.
- Evidence (tests/logs/diff):
  - `python3 jira_to_businessmap_xlsx.py --help`
  - `python3 -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python3 jira_to_businessmap_xlsx.py --projects BF BT --mapping-preset bf --jql 'project IN (BT, BF) AND issuetype IN (Bug, Story, Spike, Support, Task, Tech, "User Story") AND "team[team]" = b87876b2-78cd-4b67-bbcf-37ba395e5f39 ORDER BY created DESC' --out /tmp/businessmap-import-befinance-bt-bf-validation.xlsx`
  - `python3 - <<'PY' ... pd.read_excel('/tmp/businessmap-import-befinance-bt-bf-validation.xlsx') ... PY`
- Comando recomendado:
  - `python3 jira_to_businessmap_xlsx.py --projects BF BT --mapping-preset bf --jql 'project IN (BT, BF) AND issuetype IN (Bug, Story, Spike, Support, Task, Tech, "User Story") AND "team[team]" = b87876b2-78cd-4b67-bbcf-37ba395e5f39 ORDER BY created DESC' --out /tmp/businessmap-import-befinance-bt-bf.xlsx`
- Suggested commit message:
  - `feat(integration): support full jql for businessmap export`

## Current Task (BusinessMap BF: alinhar preset aos status reais do Jira)
- [x] Revisar o preset BF do exportador BusinessMap contra os status reais do projeto `BF` no Jira
- [x] Ajustar o preset para cobrir aliases hoje ativos que gerariam coluna inválida
- [x] Validar sintaxe/import e executar um export real amostral para confirmar as colunas geradas
- [x] Registrar review e sugestão de commit

## Specification (BusinessMap BF: alinhar preset aos status reais do Jira)
- Objetivo: garantir que a migração Jira -> BusinessMap do projeto `BF` não gere `Column name` inválida por lacunas no preset embutido.
- Escopo:
  - `jira_to_businessmap_xlsx.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Preset `bf` cobre os status reais atualmente usados em `BF` que hoje escapam do mapeamento.
  - Validação local (`--help`, import, sintaxe) permanece OK.
  - Um export real do projeto `BF` não deixa `READY FOR DEVELOPMENT`, `Cancelled` ou `Cancelada` como `Column name` bruta.

## Review (BusinessMap BF: alinhar preset aos status reais do Jira)
- What was validated:
  - O preset embutido do BF em [`jira_to_businessmap_xlsx.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_to_businessmap_xlsx.py) passou a cobrir explicitamente `READY FOR DEVELOPMENT -> READY TO START` e `Cancelled/Cancelada -> DONE`.
  - A validação contra o Jira do projeto `BF` em `2026-03-20` mostrou 291 issues com estes status reais: `Backlog`, `Triagem`, `READY FOR DEVELOPMENT`, `In Progess`, `Cancelada`, `Ready for code review`, `READY FOR TESTING/QA`, `Staging`, `Concluído`, `Cancelled`, `Development`.
  - O export real gerado em `/tmp/businessmap-import-bf-validation.xlsx` saiu com apenas estas colunas de destino: `BACKLOG`, `DONE`, `IN PROGRESS`, `READY CODE REVIEW`, `READY TESTING/QA`, `READY TO START`, `STAGING`, `TRIAGEM`; não sobrou nenhuma linha com `Column name = READY FOR DEVELOPMENT`, `Cancelled` ou `Cancelada`.
  - Risco remanescente: o BF hoje exporta `Type name` com distribuição `História=233`, `Épico=44`, `Iniciativa=13`, `Tech=1`. Se o board de destino no BusinessMap não tiver esses tipos cadastrados, será preciso passar `--type-name-map` adicional no comando.
- Evidence (tests/logs/diff):
  - `python3 jira_to_businessmap_xlsx.py --help`
  - `python3 -c "import jira_to_businessmap_xlsx; print('import ok')"`
  - `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_businessmap_xlsx.py').read_text(encoding='utf-8')); print('syntax ok')"`
  - `python3 jira_to_businessmap_xlsx.py --projects BF --out /tmp/businessmap-import-bf-validation.xlsx`
  - `python3 - <<'PY' ... pd.read_excel('/tmp/businessmap-import-bf-validation.xlsx') ... PY`
- Suggested commit message:
  - `fix(integration): map current BF jira statuses in businessmap preset`

## Current Task (Avaliar arquitetura de dados e plano de migração de CSV para banco)
- [x] Revisar instruções do projeto e memória operacional relevante
- [x] Mapear fontes atuais de dados, artefatos intermediários e pontos de leitura no dashboard
- [x] Comparar opções de persistência com foco em free tier e aderência ao deploy atual
- [x] Propor arquitetura alvo, estratégia de migração e fases de refatoração
- [x] Registrar revisão e sugestão de commit

## Specification (Avaliar arquitetura de dados e plano de migração de CSV para banco)
- Objetivo: avaliar a arquitetura atual baseada em múltiplos CSVs/XLSX e propor uma reconfiguração para banco de dados com baixo custo operacional, preferencialmente dentro de limites free tier.
- Estratégia:
  - identificar o contrato real de dados hoje consumido pela aplicação, distinguindo extração, materialização analítica e leitura da UI
  - avaliar o acoplamento atual com arquivos locais, aliases `latest`, cache e deploy serverless
  - propor uma arquitetura alvo incremental que reduza risco e preserve o dashboard durante a migração
- Regras:
  - não assumir que trocar CSV por banco resolve sozinho o problema de arquitetura
  - priorizar simplicidade operacional, custo zero ou muito baixo e impacto mínimo no runtime atual
  - incluir verificação e rollback lógico no plano

## Review (Avaliar arquitetura de dados e plano de migração de CSV para banco)
- O que foi confirmado:
  - O projeto opera hoje em três camadas implícitas: exportação Jira/Bitbucket para CSV, consolidação semântica em [`dash_board_metricas.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dash_board_metricas.py) e consumo híbrido no [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py).
  - O dashboard principal não depende só do `PowerBI_Model_latest.xlsx`; ele também consulta CSVs downstream, gargalos, portfólio, Bitbucket e relatórios de process mining para funcionalidades específicas.
  - O acoplamento principal não é apenas com CSV, mas com filesystem + convenções `latest` + fallback por URL/cache efêmero em runtime serverless.
  - O deploy atual usa Vercel Python serverless via [`api/index.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/api/index.py) e [`vercel.json`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/vercel.json), com disco local apenas como cache transitório.
  - Pela semântica do projeto, `Firebase/Firestore` é menos aderente que `Postgres`: o modelo atual já é fortemente tabular/analítico, com fatos, dimensões, filtros combinados e necessidade de joins e materializações.
- Recomendação arquitetural:
  - Adotar `Postgres` gerenciado como sistema de registro e consulta do dashboard.
  - Manter storage de objetos apenas para artefatos pesados e históricos opcionais (`process mining`, exports Excel, snapshots brutos), não como fonte principal de leitura da aplicação.
  - Migrar em camadas: primeiro abstrair acesso a dados no dashboard; depois trocar o backend dessas leituras; por fim reduzir o papel de CSV/XLSX a export/auditoria.
  - Entre opções free tier, `Neon` é a recomendação principal pela aderência a Postgres serverless e ao padrão de acesso do deploy atual; `Supabase` é uma alternativa viável se houver interesse em auth/storage/realtime no mesmo stack; `Firebase` não é a recomendação principal para este caso.
- Evidências usadas:
  - leitura de [`ARQUITETURA_CODIGO.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/ARQUITETURA_CODIGO.md), [`ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md), [`shared/path_utils.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/shared/path_utils.py), [`dash_board_metricas.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dash_board_metricas.py), [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py), [`dashboard_process_mining.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_process_mining.py), [`DEPLOY_VERCEL.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/DEPLOY_VERCEL.md) e [`requirements-vercel.txt`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/requirements-vercel.txt).
  - inspeção de chamadas `pd.read_csv`, `pd.read_excel`, `to_csv`, `to_excel` e resolução de `DATA_FOLDER`/`FLOW_PMO_DATA_DIR` no repositório.
  - validação externa dos limites free tier atuais em documentação oficial de Vercel Blob, Neon, Supabase e Firebase/Firestore.
- Suggested commit message:
  - `docs(architecture): assess csv-to-database migration path for free-tier postgres`

## Current Task (Diagnosticar BeFinance sem registros no painel de Produtividade Dev)
- [x] Verificar fontes usadas por IEF/IED e comparar com os artefatos atuais do BeFinance
- [x] Confirmar se março/2026 tem itens puxados, entregas elegíveis ou apenas transições/cancelamentos
- [x] Ajustar a UI para explicar claramente o cenário de período com itens puxados mas sem entregas elegíveis
- [x] Validar a mensagem no código e registrar revisão

## Review (Diagnosticar BeFinance sem registros no painel de Produtividade Dev)
- O que foi confirmado:
  - A aba `Produtividade Dev` calcula IEF/IED sobre `fato` carregado de `PowerBI_Model_latest.xlsx`, não sobre `process_mining`.
  - No BeFinance, março/2026 tem atividade no downstream (`BF-247` a `BF-252`), mas sem `Itens concluídos` no consolidado.
  - O `process_mining` mais recente contém eventos até `2026-03-19` e um caso terminal `BF-257` em `2026-03-09`, mas esse item não entra como entrega elegível do painel.
  - O painel parecia “sem dados” porque havia itens puxados no período, porém 0 entregas elegíveis para a régua IEF/IED.
- O que foi implementado:
  - `dashboard_full.py` agora exibe um aviso explícito quando o período tem `Itens Puxados > 0` e `Itens Entregues = 0`.
  - As mensagens vazias do IEF e do IED passaram a explicar que houve trabalho puxado, mas não houve entregas elegíveis no recorte.
- Evidências de validação:
  - parsing sintático de `dashboard_full.py` com `ast.parse(...)`
  - inspeção local de `../dados/latest/befinance-downstream-latest-data.csv` e `artifacts/process_mining/befinance-process-mining-latest.xlsx`
- Suggested commit message:
  - `fix(produtividade-dev): explain started-without-delivery periods in IEF/IED`

## Specification (Diagnosticar BeFinance sem registros no painel de Produtividade Dev)
- Objetivo: evitar leitura enganosa de “sem dados” na aba `Produtividade Dev` quando o projeto tem atividade no período, mas nenhuma entrega elegível para calcular IEF/IED.
- Estratégia:
  - manter a lógica atual de elegibilidade de entregas
  - explicitar no painel quando houver `Itens Puxados > 0` e `Itens Entregues = 0`
  - deixar claro que o problema é ausência de entregas elegíveis no recorte, não ausência total de atividade
- Regras:
  - não alterar a definição de IEF/IED
  - tocar apenas a aba `Produtividade Dev`

# Task Plan

## Current Task (Corrigir falso erro no run_process_mining_projects.ps1 ao capturar stdout)
- [x] Registrar a causa do falso negativo no runner
- [x] Corrigir a invocação PowerShell para separar log do comando e exit code
- [x] Validar parser/help e registrar revisão

## Specification (Corrigir falso erro no run_process_mining_projects.ps1 ao capturar stdout)
- Objetivo: impedir que o runner PowerShell interprete a saída textual de um comando Python bem-sucedido como se fosse o valor de retorno/exit code da função.
- Estratégia:
  - manter a saída do comando visível no terminal
  - impedir que stdout/stderr da chamada nativa vá para o valor atribuído pela função
  - continuar retornando apenas o exit code numérico para as verificações do runner
- Regras:
  - não remover logs do comando
  - preservar o diagnóstico já adicionado recentemente

## Review (Corrigir falso erro no run_process_mining_projects.ps1 ao capturar stdout)
- O que foi implementado:
  - `run_process_mining_projects.ps1` deixou de retornar stdout/stderr do comando Python no valor lógico da função `Invoke-PythonScript`.
  - a saída continua visível no terminal, mas agora o runner recebe apenas o `exit code` inteiro para decidir se houve falha.
  - isso elimina o falso negativo em que um comando bem-sucedido era tratado como erro só porque seus logs foram capturados na atribuição.
- Evidências de validação:
  - parser PowerShell sem erros
  - `.\run_process_mining_projects.ps1 -Help` executado com sucesso
  - revisão do diff restrita à função `Invoke-PythonScript`
- Suggested commit message:
  - `fix(runner): stop treating python stdout as exit code`

## Current Task (Melhorar diagnóstico de falhas no run_process_mining_projects.ps1)
- [x] Registrar o ponto de falha e a deficiência de observabilidade no runner
- [x] Ajustar o runner para exibir comando e exit code real das chamadas Python
- [x] Validar help/parser e registrar revisão

## Specification (Melhorar diagnóstico de falhas no run_process_mining_projects.ps1)
- Objetivo: evitar que o runner PowerShell interrompa com mensagem genérica sem expor a causa raiz da falha do script Python chamado.
- Estratégia:
  - centralizar a formatação do comando executado
  - logar a chamada antes da execução
  - incluir o exit code e o comando no erro lançado
- Regras:
  - não mudar o comportamento funcional do pipeline quando ele roda com sucesso
  - manter mensagens curtas, mas suficientes para diagnóstico operacional

## Review (Melhorar diagnóstico de falhas no run_process_mining_projects.ps1)
- O que foi implementado:
  - `run_process_mining_projects.ps1` agora loga explicitamente o comando Python executado em cada etapa (`jira_to_pipeline_csv`, `process_mining_jira`, `bitbucket_export` e `dash_board_metricas`).
  - falhas de inicialização do comando Python passaram a incluir o comando formatado e a mensagem original da exceção.
  - a falha do export Jira passou a informar o `exit code` real, em vez de encerrar só com a mensagem genérica por projeto.
- Evidências de validação:
  - parser PowerShell sem erros após a correção
  - `.\run_process_mining_projects.ps1 -Help` executado com sucesso
- Suggested commit message:
  - `fix(runner): improve python command failure diagnostics`

## Current Task (Fortalecer run_process_mining_projects.ps1 para refresh completo do dashboard)
- [x] Revisar o runner atual e confirmar pontos de extensão seguros
- [x] Implementar fallback robusto de interpretador Python no PowerShell
- [x] Adicionar suporte a `JQL extra` e ajuda de uso
- [x] Adicionar chamada opcional de `dash_board_metricas.py` no final
- [x] Validar sintaxe/ajuda do runner e registrar revisão

## Specification (Fortalecer run_process_mining_projects.ps1 para refresh completo do dashboard)
- Objetivo: fazer o `run_process_mining_projects.ps1` suportar resolução robusta de Python, aceitar filtro JQL extra no export Jira e, opcionalmente, acionar o refresh do `PowerBI_Model_latest.xlsx` para virar um runner mais completo do `dashboard_full`.
- Estratégia:
  - reaproveitar o fluxo atual de downstream + process mining + Bitbucket
  - centralizar a resolução do interpretador Python em helper próprio
  - manter a atualização do modelo consolidado como passo opt-in no final do script
- Regras:
  - não quebrar a execução atual sem parâmetros
  - preservar publicação dos artefatos `latest`
  - garantir que o refresh opcional do modelo use `OutDir`/`LatestDir` coerentes com o restante do runner

## Review (Fortalecer run_process_mining_projects.ps1 para refresh completo do dashboard)
- O que foi implementado:
  - `run_process_mining_projects.ps1` ganhou resolução robusta de Python com fallback por `python`, `python3`, `py -3`, além de caminhos comuns de instalação no Windows.
  - o runner agora aceita `-JqlExtra` e repassa esse filtro para `jira_to_pipeline_csv.py`.
  - foi adicionada ajuda explícita com `-Help`, sem alterar o comportamento padrão do script quando executado sem parâmetros.
  - o runner agora aceita `-RunDashboardModel`, configurando `FLOW_PMO_DATA_DIR`, `DATA_FOLDER` e `FLOW_PMO_LATEST_DIR` para chamar `dash_board_metricas.py` no final e atualizar o `PowerBI_Model_latest.xlsx`.
- Evidências de validação:
  - parser PowerShell sem erros em `run_process_mining_projects.ps1`
  - execução de `.\run_process_mining_projects.ps1 -Help` com saída esperada
  - inspeção do diff em `run_process_mining_projects.ps1` e `tasks/todo.md`
- Suggested commit message:
  - `feat(runner): add python fallback jql filter and optional dashboard model refresh`

## Current Task (Medir retornos para desenvolvimento e cycle time dev)
- [x] Confirmar o melhor ponto de cálculo a partir do changelog detalhado / eventos filtrados
- [x] Implementar métricas de cycle time em `In Progress` / `In Development` no pipeline de process mining
- [x] Implementar relatório de ida e volta `QA/Test/Homolog -> Dev` no pipeline de process mining
- [x] Acrescentar as novas métricas na aba `Produtividade Dev`
- [x] Validar comportamento e registrar revisão

## Specification (Medir retornos para desenvolvimento e cycle time dev)
- Objetivo: extrair dos logs do Jira métricas operacionais de desenvolvimento para apoiar um relatório de retorno para desenvolvimento e enriquecer a aba `Produtividade Dev`.
- Estratégia:
  - usar o changelog detalhado real do Jira já consolidado em `EventosFiltrados`
  - tratar `In Progress`, `In Development`, `Development`, `Doing` e equivalentes como etapa de desenvolvimento
  - tratar status com pistas de `QA`, `test`, `homolog` e `validation` como etapas de teste/validação para detecção de retorno
  - medir o `cycle time` de desenvolvimento pela soma do tempo alocado em etapas de desenvolvimento
  - medir a `ida e volta` pelo intervalo entre a saída de desenvolvimento para teste/QA e o retorno subsequente para desenvolvimento
- Regras:
  - preferir cálculo no pipeline (`process_mining_jira.py`) e consumo simples no dashboard
  - manter a lógica aderente aos timestamps reais do changelog, sem aproximações por datas agregadas
  - expor schema estável mesmo quando não houver ocorrências

## Review (Medir retornos para desenvolvimento e cycle time dev)
- O que foi implementado:
  - `process_mining_jira.py` agora gera datasets explícitos para fluxo de desenvolvimento: `DevFlowResumo`, `DevFlowItens` e `DevFlowRetornos`, todos derivados do changelog real.
  - o cálculo de retorno QA->Dev passou a medir o intervalo entre a entrada em teste/QA/homologação e o retorno subsequente para desenvolvimento, em vez de reaproveitar tempo do status após o retorno.
  - `dashboard_full.py` passou a consumir esses datasets novos com fallback para recálculo a partir de `EventosFiltrados`, preservando compatibilidade com artefatos antigos.
  - a aba `Produtividade Dev` ganhou métricas agregadas por pessoa (`Cycle Time Dev`, `Retornos QA->Dev`, `% cards com retorno`) e um relatório tabular por card com cada loop QA->Dev.
- Evidências de validação:
  - `python -m py_compile dashboard_full.py`
  - `python -m py_compile process_mining_jira.py` executado fora do sandbox após bloqueio do launcher do Python no ambiente restrito
  - revisão do diff local em `process_mining_jira.py` e `dashboard_full.py`
- Suggested commit message:
  - `feat(produtividade-dev): add dev cycle time and qa-to-dev return reporting`

# Task Plan

## Current Task (Portfólio: excluir cancelados de alertas e KPIs)
- [x] Mapear quais KPIs e alertas do módulo de portfólio contam itens cancelados hoje
- [x] Ajustar o snapshot para que KPIs e alertas usem somente itens não cancelados
- [x] Validar estruturalmente a exclusão de cancelados e registrar a limitação do ambiente
- [x] Registrar review com evidências e commit sugerido

## Specification (Portfólio: excluir cancelados de alertas e KPIs)
- Objetivo: fazer com que os alertas e KPIs do dashboard de portfólio considerem apenas itens não cancelados.
- Estratégia:
  - reutilizar a regra central `portfolio_is_cancelled_item(...)`
  - aplicar o filtro no snapshot antes das agregações de épicos/features/filhos
  - propagar o mesmo universo para KPIs, alertas e estruturas derivadas da aba
- Regras:
  - `Features sem story/task` deve ignorar features canceladas
  - `Épicos sem features` deve ignorar épicos cancelados
  - alertas de portfólio não devem abrir ocorrência para item cancelado

## Review (Portfólio: excluir cancelados de alertas e KPIs)
- O que foi implementado:
  - [`dashboard_full.py`](/c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/dashboard_full.py#L3018) agora filtra itens cancelados dentro de `compute_portfolio_snapshot(...)` antes de derivar `epics`, `features` e `children`.
  - a exclusão reutiliza o helper [`portfolio_is_cancelled_item(...)`](/c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/dashboard_full.py#L4677), mantendo a mesma semântica já usada nas visões de roadmap.
  - com isso, contagens como `Épicos sem features`, `Features sem filhos` e os dataframes de alertas passam a nascer do mesmo universo sem cancelados.
- Evidências:
  - o filtro base ficou antes da decomposição: [`dashboard_full.py`](/c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/dashboard_full.py#L3187), [`dashboard_full.py`](/c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/dashboard_full.py#L3188), [`dashboard_full.py`](/c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/dashboard_full.py#L3190)
  - o CSV atual contém itens cancelados reais, por exemplo [`portfolio-bt-ns-latest-data.csv`](/c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/portfolio-bt-ns-latest-data.csv#L9), [`portfolio-bt-ns-latest-data.csv`](/c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/portfolio-bt-ns-latest-data.csv#L55), [`portfolio-bt-ns-latest-data.csv`](/c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/portfolio-bt-ns-latest-data.csv#L206), [`portfolio-bt-ns-latest-data.csv`](/c:/Users/W1%20TI/OneDrive%20-%20W1/Documentos/Python/portfolio-bt-ns-latest-data.csv#L208)
- Limitação de validação:
  - não foi possível executar um smoke test em runtime porque este ambiente não tem um `python.exe` funcional e o `venv` local aponta para um interpretador inexistente em `/opt/homebrew/...`.
- Suggested commit message:
  - `fix(portfolio): exclude cancelled items from portfolio kpis and alerts`

## Current Task (Diagnosticar gráficos de process mining com imagens repetidas)
- [x] Mapear a geração dos PNGs de process mining e os nomes de saída por tipo de gráfico
- [x] Verificar se a repetição acontece na exportação (`process_mining_jira.py`) ou no carregamento da UI (`dashboard_process_mining.py`)
- [x] Confirmar a causa raiz com evidência de código e registrar a revisão

## Specification (Diagnosticar gráficos de process mining com imagens repetidas)
- Objetivo: identificar por que múltiplos gráficos de process mining estão sendo gerados com nomes diferentes, mas exibem a mesma imagem/conteúdo.
- Estratégia:
  - inspecionar a rotina que escreve os PNGs no export
  - inspecionar a rotina que resolve e embute esses arquivos na UI
  - comparar os caminhos e objetos usados em cada exportação
- Regras:
  - priorizar causa raiz no código local, sem assumir problema visual apenas pela UI
  - não alterar comportamento antes de confirmar exatamente onde ocorre a duplicação

## Review (Diagnosticar gráficos de process mining com imagens repetidas)
- O que foi confirmado:
  - [`dashboard_process_mining.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_process_mining.py#L216) apenas carrega cada PNG por sufixo fixo; a UI não reaponta múltiplos cards para o mesmo arquivo.
  - A duplicação estava na exportação em [`process_mining_jira.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/process_mining_jira.py): a rotina chamava `pm4py.save_vis_petri_net(..., variant=..., diagnostics=...)`, mas a versão instalada do PM4Py (`2.7.18`) usa `variant_str` e `log`.
  - Como `variant` e `diagnostics` eram ignorados nessa assinatura, o PM4Py caía no default `wo_decoration`, gravando a mesma Rede de Petri em `petri.png`, `petri-token-freq.png` e `petri-token-perf.png`.
  - O código foi ajustado para usar `variant_str=...` e `log=pm_df`, com fallbacks compatíveis para APIs antigas.
- Evidências de validação:
  - `python3 -m py_compile process_mining_jira.py`
  - comparação dos artefatos exportados já existentes:
    - nos arquivos `*-latest`, `petri.png`, `petri-token-freq.png` e `petri-token-perf.png` tinham exatamente o mesmo hash em todos os projetos
  - replay local com a aba `EventosFiltrados` de [`w1nner-process-mining-latest.xlsx`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/../flow-pmo/artifacts/process_mining/w1nner-process-mining-latest.xlsx):
    - `plain`: `1416707 bytes` / hash `738d0ee5...`
    - `freq`: `1566876 bytes` / hash `0e788080...`
    - `perf`: `1543541 bytes` / hash `80db63d7...`
- Suggested commit message:
  - `fix(process-mining): avoid duplicated images across exported graph views`

## Current Task (Ajustar defaults de issue types para DT no process mining)
- [ ] Mapear onde `process_mining_jira.py` define os `issue types` padrão
- [ ] Implementar defaults automáticos por projeto, com regra explícita para `DT`
- [ ] Preservar override manual via `--issue-types`
- [ ] Validar a resolução dos defaults e registrar revisão

## Specification (Ajustar defaults de issue types para DT no process mining)
- Objetivo: fazer o `process_mining_jira.py` usar automaticamente os tipos corretos do projeto `DT` no runner em lote, sem necessidade de passar `--issue-types` manualmente.
- Estratégia:
  - mover o default de `issue types` para a configuração por projeto
  - manter o CLI aceitando override explícito quando necessário
- Regras:
  - `DT` deve cobrir `Feature`, `Ad-hoc`, `Bug/Incident` e `Tech Task`
  - não quebrar o comportamento atual de `W1NNER`, `S1NC` e `BEFINANCE`

## Review (Ajustar defaults de issue types para DT no process mining)
- O que foi implementado:
  - [`process_mining_jira.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/process_mining_jira.py) passou a resolver `default_issue_types` por projeto dentro de `PROJECT_PROCESS_MINING_CONFIG`.
  - `DT` agora usa automaticamente `Feature`, `Ad-hoc`, `Bug/Incident` e `Tech Task`.
  - `W1NNER`, `S1NC` e `BEFINANCE` mantiveram o default anterior: `História`, `Task`, `Bug`.
  - o argumento `--issue-types` continua funcionando como override manual; quando omitido, o script usa o default do projeto.
  - também foram adicionados aliases normalizados para tipos de `DT`, reduzindo fragilidade em variações textuais como `Ad-hoc`/`ad hoc` e `Bug/Incident`.
- Evidências de validação:
  - `python3 -m py_compile process_mining_jira.py`
  - `python3 - <<'PY' ... resolve_project_process_mining_config(...) ... PY`
    - `W1NNR -> W1NNER ['História', 'Task', 'Bug']`
    - `DT -> DATA&ANALYTICS ['Feature', 'Ad-hoc', 'Bug/Incident', 'Tech Task']`
- Suggested commit message:
  - `fix(process-mining): use project-specific default issue types for dt`

## Current Task (Permitir recorte JQL no runner em lote de process mining)
- [ ] Adicionar suporte a `--jql-extra` no script base `run_process_mining_projects_macos.sh`
- [ ] Propagar `--jql-extra` para o wrapper explícito dos quatro projetos
- [ ] Validar ajuda e o repasse correto do parâmetro

## Specification (Permitir recorte JQL no runner em lote de process mining)
- Objetivo: permitir executar o lote `W1NNER + S1NC + BF + DT` com um filtro JQL adicional para reduzir volume de busca no Jira quando necessário.
- Estratégia:
  - adicionar um parâmetro opcional `--jql-extra`
  - repassar esse parâmetro ao `jira_to_pipeline_csv.py` apenas quando informado
- Regras:
  - manter compatibilidade com a execução atual sem `--jql-extra`
  - não alterar o fluxo dos exports de process mining e Bitbucket

## Review (Permitir recorte JQL no runner em lote de process mining)
- O que foi implementado:
  - [`run_process_mining_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_projects_macos.sh) agora aceita `--jql-extra` e repassa esse filtro ao `jira_to_pipeline_csv.py`.
  - o runner exibe o filtro adicional no log quando o parâmetro é usado.
  - o wrapper [`run_process_mining_w1nner_s1nc_bf_dt_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_w1nner_s1nc_bf_dt_macos.sh) também passou a documentar e aceitar `--jql-extra`.
- Evidências de validação:
  - `bash run_process_mining_projects_macos.sh --help`
  - `bash run_process_mining_w1nner_s1nc_bf_dt_macos.sh --help`
- Suggested commit message:
  - `feat(data): allow extra JQL filter in process mining batch runners`

## Current Task (Criar entrypoint único para W1NNER + S1NC + BF + DT)
- [ ] Confirmar se o script atual já executa exatamente `W1NNR`, `S1NC`, `BF` e `DT`
- [ ] Criar um script wrapper explícito para esse conjunto de projetos
- [ ] Validar o entrypoint novo e registrar revisão com comando de uso

## Specification (Criar entrypoint único para W1NNER + S1NC + BF + DT)
- Objetivo: disponibilizar um script único, explícito e fácil de executar para gerar downstream, process mining e Bitbucket de `W1NNER`, `S1NC`, `BEFINANCE` e `DATA&ANALYTICS`.
- Estratégia:
  - reaproveitar o pipeline existente em vez de duplicar a lógica de exportação
  - criar um wrapper com nome claro e parâmetros repassados ao script base
- Regras:
  - não alterar a lógica funcional do pipeline existente sem necessidade
  - manter compatibilidade com os parâmetros já aceitos pelo script base

## Review (Criar entrypoint único para W1NNER + S1NC + BF + DT)
- O que foi implementado:
  - confirmei que [`run_process_mining_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_projects_macos.sh) já processa exatamente `W1NNR`, `S1NC`, `BF` e `DT`.
  - adicionei o wrapper [`run_process_mining_w1nner_s1nc_bf_dt_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_w1nner_s1nc_bf_dt_macos.sh), que delega para o script base e deixa explícito o entrypoint recomendado para esse lote.
  - o novo arquivo foi marcado como executável para uso direto com `./run_process_mining_w1nner_s1nc_bf_dt_macos.sh`.
- Evidências de validação:
  - `bash run_process_mining_w1nner_s1nc_bf_dt_macos.sh --help`
  - `chmod +x run_process_mining_w1nner_s1nc_bf_dt_macos.sh`
- Suggested commit message:
  - `chore(data): add explicit runner for w1nner s1nc bf dt process mining batch`

## Current Task (Mapear rotinas de geração para process mining e produtividade dev)
- [ ] Identificar quais artefatos o `dashboard_process_mining.py` consome
- [ ] Identificar quais artefatos alimentam a aba `Produtividade Dev` no `dashboard_full.py`
- [ ] Localizar as rotinas/scripts que geram esses artefatos e levantar os parâmetros relevantes
- [ ] Registrar revisão com a sequência recomendada de execução e commit sugerido

## Specification (Mapear rotinas de geração para process mining e produtividade dev)
- Objetivo: responder quais rotinas devem ser executadas para gerar os dados de process mining do `dashboard_process_mining` e os dados usados na aba `Produtividade Dev` do `dashboard_full`, incluindo os parâmetros/variáveis relevantes.
- Escopo:
  - mapear fontes de dados lidas pelos dashboards
  - localizar scripts/entrypoints de geração correspondentes
  - documentar a ordem de execução recomendada e os parâmetros aceitos
- Regras:
  - não alterar comportamento funcional do projeto
  - usar o código local como fonte da resposta

## Review (Mapear rotinas de geração para process mining e produtividade dev)
- O que foi confirmado:
  - [`dashboard_process_mining.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_process_mining.py) consome o arquivo mais recente `w1nner-process-mining-*.xlsx` e também CSVs Bitbucket via `load_project_bitbucket_logs("W1NNER")`.
  - A aba [`Produtividade Dev` em `dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) depende de três fontes:
    - `PowerBI_Model_*.xlsx` para base Jira consolidada
    - `*_commits.csv`, `*_pullrequests.csv`, `*_pipelines.csv` para métricas Bitbucket
    - `*-process-mining-latest.xlsx` para colunas de conformance/rework/QA return e contribuição em gargalo
  - [`run_process_mining_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_projects_macos.sh) já encadeia:
    - `jira_to_pipeline_csv.py` com `--detailed-changelog-out`
    - `process_mining_jira.py`
    - `bitbucket_export.py`
  - O modelo `PowerBI_Model_*.xlsx` é gerado por [`dash_board_metricas.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dash_board_metricas.py), que usa apenas variáveis de ambiente (`FLOW_PMO_DATA_DIR` ou `DATA_FOLDER`) e publica aliases `latest`.
- Evidências de validação:
  - leitura dos entrypoints e dos parsers CLI em `run_process_mining_projects_macos.sh`, `jira_to_pipeline_csv.py`, `process_mining_jira.py`, `bitbucket_export.py` e `dash_board_metricas.py`
  - leitura dos loaders em `dashboard_process_mining.py` e `dashboard_full.py`
- Sequência recomendada:
  - `run_process_mining_projects_macos.sh` para gerar downstream + process mining + Bitbucket
  - `dash_board_metricas.py` para consolidar o `PowerBI_Model_*.xlsx`
- Suggested commit message:
  - `docs(data): map generation routines for process mining and dev productivity inputs`

## Current Task (Separar backlog, WIP e estoque total no Painel Fluxo)
- [x] Mapear no código os conceitos atuais de backlog, compromisso e WIP para definir os três estoques corretamente
- [x] Implementar novos cards e cálculos distintos para backlog não comprometido, WIP em progresso e estoque total do sistema
- [x] Validar a renderização e registrar revisão

## Specification (Separar backlog, WIP e estoque total no Painel Fluxo)
- Objetivo: deixar explícita na aba `Painel Fluxo` a diferença entre `backlog não comprometido`, `WIP em progresso` e `estoque total do sistema`.
- Regras:
  - `Backlog não comprometido`: item em backlog até o fim do período e ainda sem `Commitment_Selected`
  - `WIP em progresso`: item já comprometido até o fim do período e ainda não concluído
  - `Estoque total do sistema`: `backlog não comprometido + WIP em progresso`
  - atualizar os cálculos associados pela Lei de Little com a taxa compatível para cada conceito

## Review (Separar backlog, WIP e estoque total no Painel Fluxo)
- O que foi implementado:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) passou a calcular snapshots semanais e finais separados para `Backlog`, `Compromissos`, `WIP` e `EstoqueTotal`.
  - O painel agora exibe três cards de estoque distintos:
    - `Backlog não comprometido`
    - `WIP`
    - `Estoque total do sistema`
  - A Lei de Little foi desdobrada em três conjuntos coerentes:
    - backlog médio / taxa média de compromisso
    - WIP médio / vazão média semanal
    - estoque médio total / vazão média semanal
  - Também foram adicionadas as taxas necessárias correspondentes:
    - para comprometer backlog
    - para concluir WIP
    - para consumir o estoque total
  - Após validar o caso em que `Backlog atual = 0` mas `Backlog médio > 0`, os cards de estoque deixaram de misturar o valor atual com a conta da Lei de Little na mesma nota; a nota agora mostra apenas a média semanal do período, e os cálculos de Little ficam nos cards próprios.
  - Os textos de apoio da UI passaram a deixar claro qual média e qual taxa estão sendo usadas em cada card.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... render_tab(main_view='services', tab='tab-painel-3x3', ...) ... PY`
    - Resultado observado:
      - `found = ['Backlog não comprometido', 'Estoque total do sistema', 'Taxa necessária para comprometer backlog', 'Tempo médio até compromisso', 'Tempo médio para concluir WIP', 'Tempo médio total no sistema', 'Vazão necessária para concluir WIP', 'Vazão necessária para o estoque total', 'WIP']`
      - `missing = []`
      - `count = 9`
- Suggested commit message:
  - `feat(flow): split backlog, wip and total stock indicators in flow panel`

## Current Task (Separar inventário atual de WIP médio no Painel Fluxo)
- [x] Revisar no código as definições de inventário final, WIP médio semanal e tempos derivados
- [x] Ajustar a UI para distinguir estoque final vs média semanal e explicitar as fórmulas
- [x] Validar a renderização/strings resultantes e registrar review

## Specification (Separar inventário atual de WIP médio no Painel Fluxo)
- Objetivo: eliminar a ambiguidade entre `inventário atual no fim do período` e `WIP médio semanal no período` na aba `Painel Fluxo`.
- Regras:
  - o card de inventário deve deixar claro que representa o estoque final do recorte
  - os cards baseados na Lei de Little devem deixar claro que usam `WIP médio semanal`, não o estoque final
  - manter as fórmulas existentes, apenas alinhando a semântica exibida

## Review (Separar inventário atual de WIP médio no Painel Fluxo)
- O que foi implementado:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora rotula o card de estoque como `Inventário atual (fim do período)` e explicita na nota que ele usa o estoque final.
  - Os cards de Little foram renomeados para `Tempo para consumir WIP médio` e `Vazão necessária para consumir WIP médio`, deixando explícito que usam `WIP médio` do período.
  - As notas agora mostram as contas com a mesma semântica dos cards, reduzindo a ambiguidade entre `108` itens finais e `127.5` itens médios.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... checks = ['Inventário atual (fim do período)', 'Tempo para consumir WIP médio', 'Vazão necessária para consumir WIP médio', 'estoque final:', 'Lei de Little no período: WIP médio'] ... PY`
    - Resultado observado:
      - todos os checks retornaram `True`
- Suggested commit message:
  - `fix(flow): distinguish ending inventory from average wip in flow panel`

## Current Task (Ajustar default de `Tempo para Commit (P85)`)
- [x] Mapear uma regra padrão de etapas de compromisso que represente compromisso real sem quebrar projetos com workflows diferentes
- [x] Implementar a nova heurística no código e registrar o plano em `tasks/todo.md`
- [x] Validar o KPI recalculado no modelo local e documentar o resultado

## Specification (Ajustar default de `Tempo para Commit (P85)`)
- Objetivo: evitar que o KPI `Tempo para Commit (P85)` zere artificialmente por usar `Backlog`/`Triagem` como marco padrão de compromisso.
- Estratégia:
  - priorizar etapas que representam compromisso mais real (`Ready to Start`, `In progress`, `Development`, `Ready`, `To Do`, `Discovery`)
  - só cair para etapas tipo backlog quando não existir alternativa no workflow
- Regras:
  - preservar compatibilidade com projetos de workflow diferente
  - não alterar o cálculo do KPI; apenas a heurística padrão de seleção das etapas

## Review (Ajustar default de `Tempo para Commit (P85)`)
- O que foi implementado:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) passou a priorizar, por padrão, etapas de compromisso mais fortes: `Ready to Start`, `In progress`, `Development`, `Ready`, `To Do` e `Discovery`.
  - A função [`get_default_lead_time_start_stages(...)` em `dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora evita cair em etapas tipo backlog (`Backlog`/`Triagem`) quando existe uma etapa posterior mais representativa de compromisso.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - Validação local com o modelo `PowerBI_Model_20260310_160357.xlsx`:
    - defaults resolvidos:
      - `BEFINANCE` -> `['Ready to Start', 'In progress']`
      - `S1NC` -> `['Ready to Start', 'In progress']`
      - `W1NNER` -> `['Ready to Start', 'In progress']`
      - `DATA&ANALYTICS` -> `['Development', 'To Do', 'Discovery']`
    - resultado agregado no recorte padrão:
      - antes: `Tempo para Commit (P85) = 0 dias`
      - depois: `Tempo para Commit (P85) = 2 dias`
- Suggested commit message:
  - `fix(flow): use real commitment stages for time-to-commit default`

## Current Task (Corrigir `Tempo para Commit (P85)` com seleção explícita de backlog/triagem)
- [x] Reproduzir o cenário do print e medir o `Tempo para Commit (P85)` com as etapas atualmente selecionadas
- [x] Ajustar o cálculo para usar um marco de compromisso real mesmo quando o filtro inclui etapas de backlog/triagem
- [x] Validar o novo resultado no cenário do print e registrar revisão

## Specification (Corrigir `Tempo para Commit (P85)` com seleção explícita de backlog/triagem)
- Objetivo: impedir que o KPI `Tempo para Commit (P85)` zere artificialmente quando o usuário mantém `Backlog`/`Triagem` entre as etapas selecionadas.
- Estratégia:
  - manter o lead time usando a semântica atual do filtro
  - calcular `Tempo para Commit` com a primeira etapa selecionada que acontece estritamente depois de `DataBacklog`
  - ignorar `Backlog`/`Triagem` como marco efetivo de compromisso quando houver etapas posteriores selecionadas
- Regras:
  - preservar fallback para projetos sem downstream ou sem datas suficientes
  - usar o período do próprio marco de compromisso, não o `LeadStart_Selected`

## Review (Corrigir `Tempo para Commit (P85)` com seleção explícita de backlog/triagem)
- O que foi implementado:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) ganhou os helpers `build_time_to_commit_by_selected_stages(...)` e `apply_selected_commitment_metric(...)`.
  - O KPI `Tempo para Commit (P85)` deixou de usar `LeadStart_Selected - DataBacklog` como proxy direta e passou a usar a primeira etapa selecionada que ocorre estritamente após `DataBacklog`.
  - Quando existirem datas downstream suficientes, `Backlog` e `Triagem` deixam de colapsar o KPI em zero; quando não existirem, o cálculo ainda recai para o fallback anterior.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - Reprodução exata do cenário do print:
    - `Projeto = W1NNER`
    - `Período = 2026-02-01 a 2026-02-28`
    - etapas selecionadas = `Ready to Start`, `In progress`, `Triagem`, `Backlog`, `ready code review`, `Code review`, `ready testing/Qa`, `Testing/QA`, `ready homolog`, `Homolog`, `ready for production`
  - Resultado observado:
    - cálculo direto: `P85 = 3 dias`
    - smoke test de renderização: `['Tempo para Commit (P85)', '3', 'dias']`
- Suggested commit message:
  - `fix(flow): compute time to commit after backlog entry`

## Current Task (Diagnosticar `Tempo para Commit (P85) = 0 dias`)
- [x] Localizar a montagem do KPI `Tempo para Commit (P85)` no `Painel Fluxo`
- [x] Verificar quais colunas, filtros e regras de elegibilidade alimentam o cálculo
- [x] Confirmar com os dados locais por que o valor exibido ficou zerado
- [x] Registrar review com explicação do funcionamento e commit sugerido

## Specification (Diagnosticar `Tempo para Commit (P85) = 0 dias`)
- Objetivo: explicar por que o card `Tempo para Commit (P85)` aparece como `0 dias` e documentar como essa métrica é calculada no dashboard.
- Escopo:
  - identificar a fórmula aplicada no código
  - mapear a origem dos campos usados no cálculo
  - validar se o zero vem de ausência de base, de arredondamento visual ou de tempos efetivamente iguais a zero
- Regras:
  - usar o recorte e a lógica real do `Painel Fluxo`
  - não alterar comportamento do código; apenas diagnosticar e explicar com evidências

## Review (Diagnosticar `Tempo para Commit (P85) = 0 dias`)
- O que foi confirmado:
  - O KPI é calculado em [`dashboard_full.py:10375`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L10375) como a diferença, em dias, entre `LeadStart_Selected` e `DataBacklog` para os itens que entraram no período (`df_arrived_period`).
  - O percentil usado é o percentil empírico exato sem interpolação definido em [`dashboard_full.py:5055`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L5055).
  - No estado padrão do painel, a seleção automática de etapas de comprometimento prioriza `Backlog`, `Triagem`, `Ready to Start` e `In progress`, conforme [`dashboard_full.py:594`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L594) e [`dashboard_full.py:6217`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L6217).
  - Com o modelo local atual (`PowerBI_Model_20260310_160357.xlsx`), o recorte padrão gerou `471` tempos válidos para esse KPI e todos foram `0` dias; por isso o P85 também ficou `0`.
  - A causa estrutural é que, para a maior parte dos itens válidos, `LeadStart_Selected` cai na mesma data de `DataBacklog`, então a fórmula `LeadStart_Selected - DataBacklog` resulta em zero.
- Evidências adicionais:
  - A resolução do início selecionado é refeita por [`apply_selected_lead_time_metric(...)` em `dashboard_full.py:6817`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L6817), e a origem dominante no recorte atual é `etapas`.
  - Globalmente, se a etapa for forçada apenas para `In progress`, o mesmo cálculo deixa de ser zero agregado e passa para `P85 = 1 dia`, o que confirma que o zero atual decorre da definição de etapa de comprometimento usada no painel.
- Suggested commit message:
  - `docs(flow): record diagnosis for zero time-to-commit p85`

## Current Task (Adicionar cálculo de tempo para consumir WIP no Painel Fluxo)
- [x] Localizar os cálculos já usados pelo `Painel Fluxo` para `WIP`, `Lead Time` e `Vazão`
- [x] Adicionar no painel os indicadores de semanas para consumir o WIP e vazão semanal necessária via Lei de Little
- [x] Garantir que os cálculos usem apenas o dataset filtrado pela tela
- [x] Validar com compilação/smoke test e registrar review + commit sugerido

## Specification (Adicionar cálculo de tempo para consumir WIP no Painel Fluxo)
- Objetivo: incluir na tela `Painel Fluxo` a estimativa de quanto tempo, em semanas, levará para consumir o estoque em progresso (`WIP`) e a vazão média semanal necessária para isso, usando a Lei de Little.
- Fórmulas:
  - `Lead Time Médio (semanas) = WIP médio semanal / Vazão média semanal`
  - `Vazão média necessária (itens/semana) = WIP médio semanal / Lead Time médio (semanas)`
- Regras:
  - usar os mesmos filtros ativos da tela (`projeto`, `tipo`, `classe de serviço`, `responsável`, período e seleção de etapas de lead time)
  - usar escala de semanas
  - usar `WIP médio semanal` e `vazão média semanal` já coerentes com o recorte do painel
  - usar `Lead Time médio` do recorte filtrado, não percentil

## Review (Adicionar cálculo de tempo para consumir WIP no Painel Fluxo)
- O que foi implementado:
- [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora calcula `Lead Time médio` em semanas a partir do recorte filtrado e elegível para tempo do `Painel Fluxo`.
- A tela `Painel Fluxo` passou a exibir dois novos indicadores de referência:
  - `Tempo para consumir WIP` = `WIP médio semanal / vazão média semanal`
  - `Vazão necessária para consumir WIP` = `WIP médio semanal / Lead Time médio (semanas)`
- Os dois indicadores reutilizam o mesmo dataset já filtrado por período, projeto, tipo, classe de serviço, responsável e seleção de etapas de lead time.
- Após validação do caso reportado, o cálculo foi mantido e a UI foi esclarecida: o card de throughput agora explicita que mostra o total do período e informa a média semanal usada nas fórmulas em semanas; os cards de inventário/WIP passam a mostrar a conta aberta na nota.
- Evidências de validação:
- `python3 -m py_compile dashboard_full.py`
- `python3 - <<'PY' ... render_tab(main_view='services', tab='tab-painel-3x3', start_date='2026-01-01', end_date='2026-02-28', ...) ... PY`
  - Resultado observado:
    - `found_titles = ['Tempo para consumir WIP', 'Vazão necessária para consumir WIP']`
    - `count = 2`
- `python3 - <<'PY' wip=48; throughput_week=6; print(wip/throughput_week) PY`
  - Resultado observado:
    - `expected_weeks = 8.0`
- Conclusão da validação:
  - `16.0 semanas` só é compatível com vazão média semanal de `3.0 itens/semana`
  - o `6` visto no card anterior era `throughput total do período`, não `vazão semanal`
- Suggested commit message:
- `feat(flow): add little law wip depletion indicators to flow panel`

## Current Task (Separar o one page completo em raias por tech team)
- [x] Localizar a montagem da visão `One Page Completo - Roadmap 2026`
- [x] Agrupar os épicos por quarter e por `Team` do portfólio, criando raias por tech team
- [x] Preservar a coluna `Sem target date` e o comportamento atual de status/destaques
- [x] Validar com compilação e smoke test da renderização
- [x] Registrar review e commit sugerido

## Specification (Separar o one page completo em raias por tech team)
- Objetivo: incluir, na visão `One Page Completo - Roadmap 2026`, uma separação em raias por tech team usando o campo `Team` do portfólio.
- Resultado esperado:
  - cada coluna do roadmap (`Q1..Q4` e `Sem target date`) continua existindo
  - dentro de cada coluna, os épicos passam a ser exibidos em seções por `Team`
  - itens sem team definido devem continuar visíveis em uma raia explícita
- Regras:
  - usar a coluna `Team` da base de portfólio
  - manter os destaques já existentes (`Running`, `EXTRA-ONEPAGE`, `Highest`, `Sem target date`)
  - não alterar a lógica de filtragem por quarter já existente

## Review (Separar o one page completo em raias por tech team)
- O que foi implementado:
  - A função [`render_portfolio_roadmap_full_epics_view(...)` em `dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora resolve o campo de time a partir de `Team` do portfólio, com fallback para `team` e normalização de vazios para `Sem TEAM`.
  - Cada coluna do `One Page Completo - Roadmap 2026` passou a renderizar raias por tech team, mantendo dentro de cada raia a separação existente por status (`Running`, `Planning`, `Done`, `Paused`).
  - A coluna `Sem target date` foi preservada e agora também respeita a separação por team.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... render_portfolio_roadmap_full_epics_view(df) ... PY`
    - Resultado observado:
      - `header_count = 5`
      - `column_count = 5`
      - `first_lane = Core Tech`
      - `missing_lane = Core Tech`
      - `has_sem_team = True`
- Suggested commit message:
  - `feat(portfolio): add team swimlanes to full roadmap one-page`

## Current Task (Ocultar projetos cancelados no one page)
- [x] Localizar a regra de montagem do roadmap one page de portfólio
- [x] Excluir itens/projetos cancelados das visões one page
- [x] Validar com compilação e smoke test da renderização
- [x] Registrar review e commit sugerido

## Specification (Ocultar projetos cancelados no one page)
- Objetivo: impedir que projetos cancelados apareçam nas visões `One Page` de portfólio.
- Regras:
  - aplicar a exclusão antes da montagem visual do roadmap
  - considerar sinais de cancelamento em `Status` e `StatusCategoria`
  - manter o restante do comportamento do one page inalterado

## Review (Ocultar projetos cancelados no one page)
- O que foi implementado:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora usa o helper `portfolio_is_cancelled_item(...)` para identificar cancelamento por `Status` e `StatusCategoria`.
  - As visões [`render_portfolio_roadmap_quarter_view(...)`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) e [`render_portfolio_roadmap_full_epics_view(...)`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) passaram a remover itens cancelados antes de montar o one page.
  - Quando o recorte tiver apenas itens cancelados, a UI agora responde com mensagem de ausência de itens ativos em vez de exibir cards cancelados.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... render_portfolio_roadmap_full_epics_view(df) ... PY`
    - Resultado observado:
      - `full_has_active = True`
      - `full_has_cancelled = False`
  - `python3 - <<'PY' ... render_portfolio_roadmap_quarter_view(df) ... PY`
    - Resultado observado:
      - renderização sem erro com dataset contendo item cancelado e ativo
- Suggested commit message:
  - `fix(portfolio): hide cancelled items from one page roadmaps`

## Current Task (Alertar e destacar itens com tag EXTRA-ONEPAGE no portfólio)
- [x] Localizar a montagem da aba de alertas e do relatório one page de portfólio
- [x] Adicionar agregação de alerta por tipo de item para a tag `EXTRA-ONEPAGE`
- [x] Destacar em vermelho os itens marcados com essa tag no one page
- [x] Validar com compilação/smoke test e registrar review

## Specification (Alertar e destacar itens com tag EXTRA-ONEPAGE no portfólio)
- Objetivo: transformar a tag Jira `EXTRA-ONEPAGE` em um sinal explícito na leitura executiva de portfólio.
- Entregas:
  - alerta na aba `Alertas` mostrando total de itens com a tag por tipo de item
  - destaque visual em vermelho no relatório/aba `One Page` para itens com a tag
- Regras:
  - considerar a tag independentemente de maiúsculas/minúsculas
  - usar a base de portfólio já filtrada na tela
  - preservar os alertas e cores já existentes, apenas adicionando o novo destaque

## Review (Alertar e destacar itens com tag EXTRA-ONEPAGE no portfólio)
- O que foi implementado:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora detecta a tag `EXTRA-ONEPAGE` a partir de `ETIQUETA`/`Etiquetas`, com normalização case-insensitive.
  - A aba `Alertas` passou a incluir uma tabela `Itens com tag EXTRA-ONEPAGE por tipo`, além de materializar esses itens no detalhe de alertas com `TipoAlerta = Tag EXTRA-ONEPAGE`.
  - Os KPIs de alertas agora incluem `Itens com tag EXTRA-ONEPAGE`.
  - O `One Page Completo - Roadmap 2026` passou a destacar em vermelho os épicos marcados com essa tag e a exibir um badge `EXTRA-ONEPAGE`.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... snapshot = compute_portfolio_snapshot(df, 'test') ... render_portfolio_roadmap_full_epics_view(df) ... PY`
    - Resultado observado:
      - `summary = [{'TipoItem': 'Epic', 'TotalItens': 1}, {'TipoItem': 'Feature', 'TotalItens': 1}, {'TipoItem': 'Story', 'TotalItens': 1}]`
      - `kpi = [3]` para `Itens com tag EXTRA-ONEPAGE`
      - `alert_types = ['Epic', 'Feature', 'Story']` para o alerta `Tag EXTRA-ONEPAGE`
      - `has_badge = True` na renderização do one page
- Observação:
  - O smoke test gerou apenas `FutureWarning` preexistente de `pandas`, sem falha funcional.
- Suggested commit message:
  - `feat(portfolio): alert and highlight items tagged EXTRA-ONEPAGE`

## Current Task (Expor ETIQUETA/LABELS na extração de portfólio)
- [x] Localizar onde o CSV de portfólio define o schema e mapeia `labels`
- [x] Ajustar a extração para expor explicitamente o campo `ETIQUETA/LABELS` para épicos, features e histórias/tasks
- [x] Preservar compatibilidade com a coluna atual consumida pelo dashboard
- [x] Validar com compilação/smoke test e registrar review

## Specification (Expor ETIQUETA/LABELS na extração de portfólio)
- Objetivo: garantir que a extração de dados de portfólio traga explicitamente o campo de etiquetas do Jira (`labels`) para os itens do portfólio.
- Escopo esperado:
  - épicos
  - features
  - histórias/tasks
- Regras:
  - não remover a coluna atual `Etiquetas` se ela já estiver sendo consumida
  - expor o campo solicitado no CSV gerado
  - manter o comportamento para itens sem labels como valor vazio

## Review (Expor ETIQUETA/LABELS na extração de portfólio)
- O que foi implementado:
  - O exportador [`jira_portfolio_to_csv.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_portfolio_to_csv.py) passou a expor explicitamente a coluna `ETIQUETA` no CSV de portfólio.
  - A coluna existente `Etiquetas` foi preservada como alias compatível, ambas preenchidas a partir de `fields.labels` retornado pelo Jira.
  - Como o exportador monta linhas para todos os tipos retornados no portfólio, o campo passa a sair para épicos, features e histórias/tasks quando existir label no item.
- Evidências de validação:
  - `python3 -m py_compile jira_portfolio_to_csv.py`
  - `python3 -c "import jira_portfolio_to_csv as m; ...; row=m.build_output_row(...); print(row['Tipo']); print(row['ETIQUETA']); print(row['Etiquetas']); print('ETIQUETA' in m.CSV_COLUMNS, 'Etiquetas' in m.CSV_COLUMNS)"`
    - Resultado observado:
      - `Tipo = Story`
      - `ETIQUETA = [portfolio,jira]`
      - `Etiquetas = [portfolio,jira]`
      - as duas colunas existem no schema do CSV
- Suggested commit message:
  - `feat(portfolio): expose jira labels as ETIQUETA in portfolio export`

## Current Task (Destacar épicos sem target date na visão de portfólio)
- [x] Localizar a montagem do grid `One Page Completo - Roadmap 2026`
- [x] Adicionar uma coluna dedicada para itens sem `Target Date`
- [x] Destacar visualmente essa coluna em vermelho
- [x] Validar com compilação e smoke test da renderização

## Specification (Destacar épicos sem target date na visão de portfólio)
- Objetivo: tornar explícitos, na visão de portfólio, os itens sem `Target Date` definido.
- Resultado esperado:
  - uma coluna adicional no grid do roadmap
  - itens sem `Target Date` agrupados nessa coluna
  - destaque visual em vermelho para facilitar leitura executiva
- Regras:
  - não remover o agrupamento atual por quarter
  - preservar ordenação e semântica das colunas `Q1..Q4`
  - considerar `DueDate` vazio como ausência de `Target Date`

## Review (Destacar épicos sem target date na visão de portfólio)
- O que foi implementado:
  - A função [`render_portfolio_roadmap_full_epics_view(...)` em `dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) passou a separar os épicos sem `DueDate` em uma coluna adicional chamada `Sem target date`.
  - A nova coluna foi destacada visualmente em vermelho no cabeçalho, na borda dos cards e com badge textual por item.
  - A visão `Q1..Q4` foi preservada; itens sem data deixaram de ser descartados silenciosamente e agora aparecem explicitamente no mesmo grid executivo.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... render_portfolio_roadmap_full_epics_view(df) ... PY`
    - Resultado observado:
      - `header_count= 5`
      - `headers= ['Q1', 'Q2', 'Q3', 'Q4', 'Sem target date']`
      - `missing_counter= Sem target date: 7`
- Suggested commit message:
  - `feat(portfolio): highlight epics missing target dates in roadmap`

## Current Task (Implementar governança de Fast Track/Expedite e alertas de variabilidade)
- [x] Mapear os sinais já existentes de `ClasseServico/Expedite` e `CV/dispersão`
- [x] Implementar visão explícita de governança Fast Track/Expedite
- [x] Implementar alertas explícitos de variabilidade/dispersão com thresholds operacionais
- [x] Integrar os blocos ao dashboard mantendo coerência com as abas existentes
- [x] Validar com compilação/smoke tests e registrar review

## Specification (Implementar governança de Fast Track/Expedite e alertas de variabilidade)
- Objetivo: transformar sinais já existentes de urgência e variabilidade em capabilities visíveis e acionáveis no dashboard.
- Entregas:
  - governança explícita de `Fast Track/Expedite`
  - alertas explícitos de variabilidade/dispersão
- Regras:
  - reutilizar `ClasseServico`/prioridade já resolvida no projeto
  - usar thresholds operacionais compreensíveis
  - manter a solução no módulo de serviços, preferencialmente junto da leitura sistêmica já existente

## Review (Implementar governança de Fast Track/Expedite e alertas de variabilidade)
- O que foi implementado:
  - A aba [`tab-padroes` em `dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) passou a incluir dois blocos novos:
    - `Governança Fast Track / Expedite`
    - `Alertas Explícitos de Variabilidade / Dispersão`
  - A governança de `Fast Track/Expedite` agora materializa:
    - `% de entradas em expedite`
    - `% de throughput em expedite`
    - quantidade de itens expedite em aberto
    - status da política (`OK`, `Atenção`, `Crítico`)
    - tabela por classe de serviço com `Lead P50` e `Lead P85`
    - alertas textuais específicos para uso indevido de expedite
  - Foram adicionadas configurações operacionais por ambiente:
    - `FLOW_EXPEDITE_TARGET_PCT` (default `20`)
    - `FLOW_EXPEDITE_CRITICAL_PCT` (default `30`)
  - Os alertas explícitos de variabilidade/dispersão agora transformam `CV` em semáforo operacional para:
    - `Lead Time`
    - `Cycle Time`
    - `Throughput Semanal`
  - Também foram adicionados thresholds configuráveis de variabilidade:
    - `FLOW_VARIABILITY_CV_WARN` (default `0.30`)
    - `FLOW_VARIABILITY_CV_CRITICAL` (default `0.50`)
- Decisão de design:
  - Os blocos foram mantidos na aba `Padrões Sistêmicos`, porque dependem da mesma leitura combinada usada por checklist, diagnóstico e padrões por regra.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import dashboard_full as d; kpis, table_df, alerts_df = d.build_expedite_governance_view(...); print(kpis); print(table_df.columns.tolist()); print(alerts_df.columns.tolist())"`
    - Resultado observado:
      - `policy_status: 'OK'`
      - tabela com colunas `Classe de Serviço`, `Itens`, `Lead P50`, `Lead P85`
      - alertas com colunas `Indicador`, `Observado`, `Regra`, `Status`, `Leitura`
  - `python3 -c "import dashboard_full as d; alerts_df, metrics_df = d.build_variability_alerts_view(...); print(alerts_df.columns.tolist()); print(metrics_df.to_dict('records'))"`
    - Resultado observado:
      - métricas de variabilidade geradas para `Lead Time`, `Cycle Time` e `Throughput Semanal`
      - no dataset atual, os três `CV` ficaram marcados como `Crítico`
  - `python3 -c "import dashboard_full as d; out = d.render_tab('services', 'tab-padroes', ...); ..."`
    - Resultado observado:
      - `Div`
      - presença de `Governança Fast Track / Expedite`
      - presença de `Alertas Explícitos de Variabilidade / Dispersão`
  - O smoke test de renderização gerou apenas `FutureWarning` de `plotly/pandas`, sem erro funcional.
- Suggested commit message:
  - `feat(flow): add expedite governance and explicit variability alerts`

## Current Task (Ajustar checklist para WIP por pessoa configurável)
- [x] Localizar a regra atual do checklist semanal para WIP
- [x] Implementar limite configurável de itens em progresso por pessoa
- [x] Atualizar a leitura exibida no checklist e na base semanal
- [x] Validar com compilação/smoke test e registrar review

## Specification (Ajustar checklist para WIP por pessoa configurável)
- Objetivo: substituir, no checklist semanal automatizado, a avaliação genérica de banda histórica de `WIP` por uma regra operacional configurável de `WIP por pessoa`.
- Regra esperada:
  - padrão inicial: `2 itens por pessoa`
  - exemplo de leitura: time com `5` pessoas => limite de `10` itens em progresso
- Requisitos:
  - a regra deve ser configurável sem editar o código
  - o checklist deve mostrar a conta usada (`limite por pessoa x pessoas ativas`)
  - a saída deve explicitar também `WIP por pessoa` observado

## Review (Ajustar checklist para WIP por pessoa configurável)
- O que foi implementado:
  - A avaliação de `WIP` no checklist semanal automatizado deixou de usar apenas banda histórica agregada e passou a usar uma regra operacional configurável de `WIP por pessoa`.
  - Foi adicionada a configuração `FLOW_WEEKLY_WIP_ITEMS_PER_PERSON_LIMIT`, com default `2`.
  - A base semanal agora calcula e expõe:
    - `PessoasAtivas`
    - `WIP_Por_Pessoa`
    - `WIP_Limite_Config`
  - O item do checklist foi reescrito para mostrar:
    - `WIP` total observado
    - `WIP por pessoa` observado
    - conta de referência no formato `limite por pessoa x pessoas ativas = limite total`
  - A tabela diagnóstica também passou a considerar estouro do limite configurado por pessoa como sinal de sobrecarga/saturação.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import dashboard_full as d; checklist, diag, weekly = d.build_weekly_flow_checklist_and_diagnosis(...); ..."`
    - Resultado observado para o item de checklist:
      - `Checklist`: `WIP da semana abaixo do limite configurado por pessoa?`
      - `Status`: `Crítico`
      - `Observado`: `359 itens | 12.82 por pessoa`
      - `Referência`: `2.0 por pessoa x 28 pessoas = 56.0`
  - `python3 -c "import dashboard_full as d; out = d.render_tab('services', 'tab-padroes', ...); print(type(out).__name__)"`
    - Resultado observado: `Div`
- Suggested commit message:
  - `fix(flow): evaluate weekly wip against configurable per-person limit`

## Current Task (Corrigir KeyError de Severidade na aba Padrões Sistêmicos)
- [x] Reproduzir o cenário do traceback e localizar o ponto frágil
- [x] Garantir schema estável quando não houver padrões detectados
- [x] Tornar a renderização defensiva para colunas críticas
- [x] Validar compilação e smoke test

## Review (Corrigir KeyError de Severidade na aba Padrões Sistêmicos)
- O que foi corrigido:
  - [`detect_systemic_patterns(...)` em `dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora retorna `DataFrame`s vazios com colunas estáveis, em vez de `DataFrame()` sem schema.
  - A aba `tab-padroes` passou a tratar de forma defensiva o acesso a `Severidade` e `Semana`.
- Evidências:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import dashboard_full as d; details, summary = d.detect_systemic_patterns(...); print(details.columns.tolist()); print(summary.columns.tolist())"`
    - Resultado observado:
      - `details` com colunas incluindo `Severidade`
      - `summary` com colunas `Padrão`, `Severidade`, `Ocorrências`
  - `python3 -c "import dashboard_full as d; out = d.render_tab('services', 'tab-padroes', ...); print(type(out).__name__)"`
    - Resultado observado: `Div`
- Suggested commit message:
  - `fix(flow): stabilize empty pattern schemas to avoid severity key errors`

## Current Task (Implementar checklist semanal automatizado e tabela diagnóstica prescritiva)
- [x] Mapear o encaixe desses recursos nas abas existentes de fluxo
- [x] Implementar cálculo semanal automatizado com thresholds e referências históricas
- [x] Implementar tabela diagnóstica com padrão observado, diagnóstico provável e ação recomendada
- [x] Integrar a visualização ao dashboard com os filtros já existentes
- [x] Validar com compilação/smoke tests e registrar review

## Specification (Implementar checklist semanal automatizado e tabela diagnóstica prescritiva)
- Objetivo: materializar no dashboard uma camada operacional de leitura do fluxo baseada nos artefatos de referência, sem depender de leitura manual dos gráficos.
- Entregas:
  - checklist semanal automatizado com thresholds explícitos
  - tabela diagnóstica prescritiva com combinação de métricas -> hipótese de problema -> ação recomendada
- Regras:
  - reutilizar as métricas semanais já calculadas no projeto sempre que possível
  - respeitar os filtros ativos atuais
  - manter a solução no módulo de serviços, alinhada às abas de `Saúde do Fluxo` e `Padrões Sistêmicos`

## Review (Implementar checklist semanal automatizado e tabela diagnóstica prescritiva)
- O que foi implementado:
  - A aba [`tab-padroes` em `dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) passou a incluir:
    - `Checklist Semanal Automatizado`
    - `Tabela Diagnóstica Prescritiva`
    - base semanal explícita da revisão automatizada
  - Foi criado um helper dedicado para consolidar sinais semanais de fluxo a partir da base filtrada:
    - `Throughput`
    - `WIP`
    - `Cycle Time` (`P50`, `P85`, média e `CV`)
    - `WIP Age` médio
    - quantidade de itens abertos acima do `Cycle P85`
    - taxa de bloqueio
    - pressão de fluxo
  - O checklist automatizado agora valida a última semana do recorte contra referências históricas:
    - throughput dentro de `±20%` da média
    - cycle time dentro de `+30%` da mediana histórica
    - WIP abaixo da banda de referência (`P85` histórico do recorte)
    - variação semanal de throughput <= `30%`
    - dispersão de cycle time controlada (`CV < 0.30`)
    - correlação adversa `WIP alto + Cycle alto`
    - itens abertos acima do `Cycle P85`
  - A tabela diagnóstica prescritiva foi implementada com padrões observados, diagnóstico provável e ação recomendada, cobrindo cenários como:
    - sobrecarga
    - variabilidade elevada
    - redução de capacidade
    - aceleração acima do limite
    - fluxo saudável
    - saturação progressiva
    - processo inconsistente
    - complexidade/retrabalho
    - bloqueios silenciosos
    - subutilização
- Decisão de design:
  - Em vez de abrir uma aba nova, a solução foi integrada à aba `Padrões Sistêmicos`, porque os dois recursos dependem da mesma leitura semanal combinada de métricas e reforçam a interpretação do que já existe.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import dashboard_full as d; out = d.render_tab('services', 'tab-padroes', '2025-12-01', '2025-12-31', None, None, None, None, [], 5, 'score', d.PROJECT_FILTER_ALL_VALUE, 'ALL', None, None, None, None, None, None, None, None, None, None); ..."`
    - Resultado observado:
      - `Div`
      - `True` para presença de `children`
      - `True` para `Checklist Semanal Automatizado`
      - `True` para `Tabela Diagnóstica Prescritiva`
- Suggested commit message:
  - `feat(flow): add automated weekly checklist and prescriptive diagnostics`

## Current Task (Implementar visão dedicada de Work Item Age)
- [x] Mapear o que já existe de aging/WIP/tempo no dashboard e definir o encaixe da nova aba
- [x] Implementar cálculo operacional de `Work Item Age` para itens ativos no recorte filtrado
- [x] Comparar `Work Item Age` com referência factual de `Cycle Time` do mesmo recorte
- [x] Adicionar visualizações dedicadas, KPIs e tabela detalhada no dashboard
- [x] Validar com compilação/smoke tests e registrar review com evidências

## Specification (Implementar visão dedicada de Work Item Age)
- Objetivo: materializar uma visão operacional explícita de `Work Item Age` no módulo de serviços do dashboard, reaproveitando o que já existe de aging no projeto.
- Resultado esperado:
  - nova aba dedicada no conjunto `Serviços (Value Stream)`
  - cálculo de idade dos itens ativos a partir de `DataInProgress`
  - comparação da idade atual com referência de `Cycle Time` factual do mesmo recorte
  - KPIs, distribuição, ranking dos itens mais envelhecidos, cortes por status/responsável/classe de serviço e tabela detalhada
- Regras:
  - respeitar os filtros ativos já existentes (`período`, `projeto`, `tipo`, `classe_servico`, `responsavel`)
  - não criar conceito novo incompatível com o restante do dashboard; usar a semântica atual de fluxo e de tempos já calculados
  - quando não houver base suficiente de `Cycle Time`, a aba deve continuar funcional e explicitar a limitação

## Review (Implementar visão dedicada de Work Item Age)
- O que foi implementado:
  - Nova aba `Work Item Age` adicionada ao módulo `Serviços (Value Stream)` em [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py).
  - A aba calcula `Work Item Age` de forma operacional para itens ativos, usando `DataInProgress` como início e o menor valor entre `data final do filtro` e `hoje` como snapshot.
  - A saúde dos itens passou a ser classificada por comparação com `Cycle Time` factual do mesmo recorte:
    - `Saudável`: idade <= `Cycle P50`
    - `Atenção`: idade entre `Cycle P50` e `Cycle P85`
    - `Crítico`: idade > `Cycle P85`
    - fallback defensivo para `Sem referência` quando não houver amostra suficiente de `Cycle Time`
  - A nova visão inclui:
    - KPIs de total ativo, idade média/mediana/máxima, críticos, atenção, bloqueados e `% críticos`
    - distribuição do `Work Item Age`
    - faixas de idade por severidade
    - ranking dos itens mais envelhecidos
    - scatter por data de início
    - resumos por severidade, status e responsável
    - tabela detalhada com filtro/ordenação nativos
  - A implementação foi feita de forma defensiva para recortes/fontes em que colunas como `Status`, `Responsavel`, `ClasseServico` ou `Projeto` estejam ausentes.
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import dashboard_full as d; out = d.render_tab('services', 'tab-work-item-age', '2025-12-01', '2025-12-31', None, None, None, None, [], 5, 'score', d.PROJECT_FILTER_ALL_VALUE, 'ALL', None, None, None, None, None, None, None, None, None, None); ..."`
    - Resultado observado:
      - `Div`
      - `True` para presença de `children`
      - `True` para o título `Work Item Age`
      - `16` blocos/children renderizados
  - O smoke test gerou apenas `FutureWarning` de `pandas/plotly`, sem erro funcional de renderização.
- Suggested commit message:
  - `feat(flow): add dedicated work item age tab with cycle time risk classification`

## Current Task (Avaliar lacunas de métricas de fluxo com base nos artefatos da Cristiane Goncalves)
- [x] Registrar a especificação da análise e os artefatos-fonte
- [x] Ler os PDFs e a planilha para extrair métricas de fluxo, visualizações e fórmulas relevantes
- [x] Comparar os artefatos com as métricas e dashboards já implementados no projeto
- [x] Listar lacunas objetivas de implementação, priorizadas por impacto e viabilidade
- [x] Registrar review com evidências e sugerir mensagem de commit

## Specification (Avaliar lacunas de métricas de fluxo com base nos artefatos da Cristiane Goncalves)
- Objetivo: avaliar, usando apenas os artefatos fornecidos pelo usuário e o código/dados atuais do projeto, o que ainda falta implementar especificamente em relação a métricas de fluxo.
- Artefatos-fonte:
  - `/Users/rodrigoalmeidadeoliveira/Downloads/Material+Complementar+-+Dashboards+Ágeis+Aplicados+-+Autora+Cristiane+Goncalves.pdf`
  - `/Users/rodrigoalmeidadeoliveira/Downloads/Planilha+Exercicios+Metricas+Ageis+-+Kit+Estimativas+e+Metricas+Ageis+-+Autora+Cristiane+Goncalves.xlsx`
  - `/Users/rodrigoalmeidadeoliveira/Downloads/Leia+me+Guia-Completo-de-Estimativas-e-Metricas-em-Ambientes-Ageis.pdf`
- Escopo da análise:
  - identificar métricas de fluxo citadas ou exemplificadas nos artefatos
  - verificar aderência no projeto atual (`dashboard_full.py`, exportadores e roadmap de indicadores)
  - produzir lista objetiva de itens faltantes para implementação
- Fora do escopo:
  - implementar mudanças no dashboard nesta tarefa
  - avaliar estimativas/capacidade que não estejam ligadas a fluxo

## Review (Avaliar lacunas de métricas de fluxo com base nos artefatos da Cristiane Goncalves)
- Conclusão executiva:
  - O projeto já cobre uma base forte de métricas de fluxo operacional: `Lead Time`, `Throughput`, `CFD`, `WIP`, análise de gargalos por etapa, saúde do fluxo, padrões sistêmicos, estatística descritiva e capacidade de fila.
  - Comparando com os artefatos da Cristiane Goncalves, o que ainda falta não é o núcleo básico de fluxo, mas sim a camada de previsibilidade probabilística, guardrails operacionais explícitos e playbooks de leitura/ação mais prescritivos.
  - Em termos práticos: o projeto está maduro em observabilidade do fluxo, mas ainda incompleto em previsibilidade baseada em fluxo e em operacionalização dos sinais para decisão.
- O que os artefatos pedem como referência de fluxo:
  - A planilha traz como núcleo de fluxo: `Throughput`, `Cycle Time`, `Lead Time`, `CFD`, `WIP`, `Work Item Age`, `Flow Efficiency` e `Monte Carlo`.
  - O guia complementar reforça leitura integrada via Lei de Little: correlacionar `Throughput`, `WIP`, `Cycle Time`, dispersão do scatterplot e sinais do `CFD`.
  - O mesmo guia também propõe um checklist operacional com thresholds simples:
    - `Throughput` dentro de `±20%` da média histórica
    - `Cycle Time` dentro de `±30%` da mediana histórica
    - `WIP` abaixo de limite explícito
    - variação semanal de throughput acima de `30%`
    - leitura visual do `CFD` e da dispersão do scatterplot
  - No material de entrada (`Leia-me`), a trilha de estudo ainda destaca `SLE`, políticas explícitas, `Fast Track` e gestão de `WIP` para estabilidade.
- Cobertura já existente no projeto:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) já expõe abas de fluxo com:
    - `Lead Time` com distribuição, curva acumulada e scatterplot
    - `Fluxo` com `Lead Time`, `Cycle Time`, `Throughput`, pressão/eficiência de fluxo, bloqueio e gargalos por etapa
    - `CFD` dedicado
    - `Saúde do Fluxo` com chegadas x throughput e tendência de `WIP`
    - `Estatística Descritiva` com percentis e variabilidade de `Lead Time`, `Throughput` e `WIP`
    - `Capacidade de Fila` com modelo `M/M/1`
    - `Padrões Sistêmicos` com heurísticas que já correlacionam `WIP`, throughput, bloqueio, pressão e aging
  - Há sinais parciais de classes de serviço/urgência (`ClasseServico`, `Expedite`) e correlação operacional suficiente para boa parte da leitura sistêmica.
- Lacunas objetivas ainda não implementadas:
  1. `Monte Carlo` de fluxo para previsão probabilística.
     - Não há aba ou cálculo explícito de simulação probabilística por throughput/lead time para responder “quantos itens até data X?” ou “quando terminam N itens?”.
     - Este é o gap mais claro frente à planilha, que trata `Monte Carlo` como métrica principal de previsibilidade.
  2. `SLE` explícito e operacional.
     - O material cita `Service Level Expectation (SLE)`, mas o dashboard hoje mostra percentis e distribuição sem transformar isso em compromisso operacional claro por classe de serviço ou por tipo de demanda.
     - Falta materializar algo como: `SLE atual = 85% dos itens terminam em X dias`, acompanhado de cumprimento do SLE no período.
  3. `Work Item Age` como visão operacional de primeiro nível.
     - O projeto usa aging internamente e em padrões, mas não há uma visão dedicada de `Work Item Age` no fluxo operacional com ranking de itens envelhecidos, faixas de risco e comparação direta contra `Cycle Time` de referência, como a planilha propõe.
     - Hoje isso aparece mais como sinal derivado do que como métrica operacional explícita.
  4. `WIP limit` explícito por etapa/time e monitoramento de violação.
     - Existe `WIP` observado, mas não um contrato visual de `limite definido` versus `WIP atual`, que é um dos checks centrais do material Kanban.
     - Falta permitir configurar limites por estágio/time e mostrar excesso, tempo acima do limite e frequência de violação.
  5. Checklist/alertas semanais prontos para leitura gerencial.
     - O material traz uma camada de interpretação padronizada (`±20%`, `±30%`, variação >`30%`, coerência entre gráficos, barriga no CFD).
     - O projeto já tem os dados, mas ainda não empacota isso como checklist objetivo com status `ok/atenção/crítico`.
  6. Diagnóstico prescritivo baseado em combinação de métricas.
     - Há `Padrões Sistêmicos`, mas ainda não há uma tabela de leitura rápida alinhada ao guia, com padrão observado -> diagnóstico provável -> decisão recomendada.
     - Isso reduziria a distância entre dado e ação.
  7. `Cycle Time` separado por tipo de trabalho em contexto híbrido.
     - O material de dashboards híbridos recomenda separar `Cycle Time` de trabalho planejado versus urgente.
     - O projeto já filtra por `ClasseServico`, mas não expõe comparativo pronto entre fluxo normal e urgente nem `% de capacidade consumida por urgências` como quadro de decisão.
  8. Política de `Fast Track`/`Expedite` como métrica e governança.
     - Existem campos e sinais de `Expedite`, mas falta uma visão explícita de fast track: volume, aging, lead time, impacto no throughput normal e aderência à política.
  9. Dispersão/variabilidade tratada como diagnóstico visível.
     - Há scatterplot e estatística descritiva, mas o critério de dispersão citado no material (`CV < 0.3?`) ainda não aparece como indicador operacional ou alerta nativo.
     - Falta transformar variabilidade em semáforo e recomendação de ação.
- Priorização recomendada de implementação:
  1. `SLE` opcional + `Work Item Age` dedicado + `WIP limit` explícito por etapa
  2. checklist semanal automatizado + tabela diagnóstica prescritiva
  3. comparativos híbridos (`planejado x urgente`) + governança de `Fast Track`
  4. alertas explícitos de variabilidade/dispersão
- Decisão de escopo do usuário nesta sessão:
  - `Monte Carlo` não será implementado.
  - `SLE` ficou como possibilidade, não como item obrigatório.
  - O backlog principal segue com os demais itens operacionais de fluxo.
- Julgamento final por aderência aos artefatos:
  - `Throughput`: atendido
  - `Cycle Time`: atendido, mas falta separação mais explícita por classe de trabalho
  - `Lead Time`: atendido
  - `CFD`: atendido
  - `WIP`: parcialmente atendido, porque falta limite contratado e violação
  - `Work Item Age`: parcialmente atendido, porque falta visão operacional dedicada
  - `Flow Efficiency`: atendido de forma aproximada/operacional
  - `Monte Carlo`: fora do escopo decidido pelo usuário
  - `SLE/Fast Track/políticas explícitas`: parcialmente fora do escopo; `SLE` opcional, demais capabilities ainda pendentes
- Evidências usadas:
  - Planilha em `/Users/rodrigoalmeidadeoliveira/Downloads/Planilha+Exercicios+Metricas+Ageis+-+Kit+Estimativas+e+Metricas+Ageis+-+Autora+Cristiane+Goncalves.xlsx`
    - abas `3.4 Throughput`, `3.5.1 Cycle Time`, `3.5.2 Lead Time`, `3.6 CFD`, `3.7 Monte Carlo`, `5.2.1 WIP`, `5.2.4 Work Item Age`, `5.2.5.a/b Flow`
  - Texto extraído de `/Users/rodrigoalmeidadeoliveira/Downloads/Material+Complementar+-+Dashboards+Ágeis+Aplicados+-+Autora+Cristiane+Goncalves.pdf`
    - seções `4.2 Dashboards em Ambientes Kanban`, `4.3 Dashboards em Ambientes Híbridos`, `5.2 O Poder da Leitura Integrada`, `5.3 Tabela de Diagnóstico`, `5.4 Checklist de Análise Semanal`, `6.3 Métricas de Fluxo`
  - Texto extraído de `/Users/rodrigoalmeidadeoliveira/Downloads/Leia+me+Guia-Completo-de-Estimativas-e-Metricas-em-Ambientes-Ageis.pdf`
    - resumo da trilha com `SLE`, políticas explícitas, `Fast Track` e gestão de `WIP`
  - Código atual em [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py)
    - `SERVICE_TABS`
    - renderização das abas `Lead Time`, `Fluxo`, `CFD`, `Saúde do Fluxo`, `Estatística Descritiva`, `Capacidade de Fila`, `Padrões Sistêmicos`
- Suggested commit message:
  - `docs(tasks): assess remaining flow metrics gaps against Cristiane Goncalves artifacts`

## Current Task (Recalibrar diagnóstico de hierarquia do portfólio BT)
- [x] Registrar a correção do usuário sobre features no mesmo projeto `BT`
- [x] Reavaliar a hipótese principal para vínculos vazios no snapshot
- [x] Atualizar review com próximo foco técnico para exportador/validação

## Review (Recalibrar diagnóstico de hierarquia do portfólio BT)
- O contexto foi corrigido: as `features` agora ficam no mesmo space de portfólio, no mesmo projeto `BT`. Portanto, a ausência de `ParentID`, `FeatureLinkID` e `EpicLinkID` no CSV não deve mais ser interpretada como efeito natural de separação entre projetos/spaces.
- A implicação prática é mais objetiva:
  - o exportador já está lendo o projeto certo, mas o snapshot publicado ainda não está materializando os vínculos esperados dentro do próprio `BT`
  - o próximo diagnóstico deve focar em como os relacionamentos estão representados no Jira atual (`parent`, custom fields como `Principal`/`Epic Name`, ou `issue links`) e se esses campos estão realmente retornando para os tipos `Epic` e `Feature` no projeto `BT`
- Com essa correção, o próximo passo técnico prioritário deixa de ser “conciliar spaces” e passa a ser “descobrir por que os vínculos internos do `BT` não estão chegando ao CSV”.
- Suggested commit message:
  - `docs(tasks): recalibrate portfolio hierarchy diagnosis after BT feature model update`

## Current Task (Avaliar aderência do projeto a Flight Levels)
- [x] Ler o whitepaper e extrair os critérios operacionais de FL1, FL2 e FL3
- [x] Inspecionar os dados e exportadores de portfólio/downstream realmente usados no projeto
- [x] Comparar a implementação atual com os critérios do whitepaper e identificar gaps estruturais
- [x] Registrar evidências, conclusão e próximos passos em uma review objetiva

## Specification (Avaliar aderência do projeto a Flight Levels)
- Objetivo: determinar, com base no whitepaper [`Flight-Levels-Whitepaper-Update-[2026].pdf`](/Users/rodrigoalmeidadeoliveira/Downloads/Flight-Levels-Whitepaper-Update-%5B2026%5D.pdf) e nos dados/exportadores locais, se a estrutura atual implementa adequadamente os três níveis de Flight Levels.
- Escopo da análise:
  - `jira_portfolio_to_csv.py` como fonte do portfólio/hierarquia
  - `jira_to_pipeline_csv.py` e artefatos downstream como fonte do fluxo operacional
  - `dashboard_full.py` como materialização visual/analítica da estrutura
- Critérios de comparação:
  - `FL3`: metas estratégicas explícitas, lógica de priorização, medição de sucesso e conexão com iniciativas
  - `FL2`: coordenação entre times, dependências, fluxo do portfólio/iniciativas e conexão entre estratégia e execução
  - `FL1`: gestão do trabalho diário/entrega por times com visibilidade de fluxo e bloqueios
- Fora do escopo:
  - validar se o modelo Flight Levels está “bonito” visualmente
  - recomendar ferramenta externa; a avaliação deve ser feita apenas sobre a implementação e os dados atuais

## Review (Avaliar aderência do projeto a Flight Levels)
- Conclusão executiva:
  - A implementação atual atende bem `FL1`, atende `FL2` apenas de forma parcial e ainda não atende adequadamente `FL3`.
  - Em termos práticos: o projeto mede execução operacional com boa profundidade, mas ainda não fecha o circuito completo entre estratégia -> coordenação -> execução exigido pelo whitepaper.
- Leitura do whitepaper usada como critério:
  - `FL3`: metas estratégicas explícitas, `OKRs`, lógica de priorização e conexão dessas metas com iniciativas.
  - `FL2`: fluxo de coordenação entre times, iniciativas conectadas à estratégia, dependências e workflows ligados aos times.
  - `FL1`: trabalho diário dos times com workflow visível, progresso e bloqueios.
- Evidência de `FL1` aderente:
  - Os CSVs downstream detalhados existem para `W1NNR`, `S1NC`, `BEFINANCE` e `DATAANALYTICS`, com volume e granularidade operacional reais:
    - `w1nner-downstream-latest-data.csv`: `2064` itens
    - `s1nc-downstream-latest-data.csv`: `1783` itens
    - `befinance-downstream-latest-data.csv`: `194` itens
    - `dataanalytics-downstream-latest-data.csv`: `358` itens
  - Essas bases trazem colunas de workflow por etapa, responsável, timestamps por estágio e sinais de bloqueio.
  - O modelo consolidado [`PowerBI_Model_latest.xlsx`](/Users/rodrigoalmeidadeoliveira/Documents/dados/PowerBI_Model_latest.xlsx) materializa isso em `Fato_Items` com `LeadTime_Dias`, `TempoBacklog_Dias`, `TempoExecucao_Dias`, `TempoBloqueioDias`, `WIP_Dias`, `Bloqueado`.
  - Há bloqueios observáveis nos dados atuais (`Blocked=true`): `W1NNR=14`, `S1NC=17`, `BEFINANCE=1`, `DATAANALYTICS=9`.
- Evidência de `FL2` parcial:
  - O código já tenta sustentar coordenação por hierarquia no portfólio, inclusive com campos como `ParentID`, `ParentTipo`, `FeatureLinkID`, `EpicLinkID`, `HierarchyLinkSource` em [`jira_portfolio_to_csv.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_portfolio_to_csv.py) e no `compute_portfolio_snapshot(...)` de [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py).
  - Porém o snapshot real [`portfolio-bt-ns-latest-data.csv`](/Users/rodrigoalmeidadeoliveira/Documents/dados/portfolio-bt-ns-latest-data.csv) está operando só com `14` colunas e sem vínculos preenchidos:
    - `220` linhas totais
    - `160` épicos
    - `56` features
    - `items_with_valid_parent = 0`
    - `ParentID`, `ParentTipo`, `FeatureLinkID` e `EpicLinkID` vazios no arquivo atual
  - Sem esses vínculos, o dashboard consegue mostrar volume, aging, due date e status por `Team`, mas não consegue coordenar com robustez `épico -> feature -> trabalho tático`, nem expor dependências reais entre times.
  - O próprio roadmap do projeto registra esse bloqueio por dados e exportador em [`ROADMAP_INDICADORES_PORTFOLIO.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/ROADMAP_INDICADORES_PORTFOLIO.md): dependências, CFD de portfólio, throughput de portfólio e tempo de decisão seguem bloqueados.
  - Há também desalinhamento estrutural entre portfólio e execução: o portfólio atual usa IDs `BT-*`, enquanto os fluxos operacionais detalhados estão em `BF-*`, `W1NNR-*`, `S1NC-*`, `DT-*`; isso enfraquece a ligação de coordenação ponta a ponta.
- Evidência de `FL3` insuficiente:
  - O whitepaper exige metas estratégicas, `OKRs`, lógica de priorização e ligação explícita com as iniciativas.
  - O portfólio atual não exporta campos de objetivo/tema estratégico, `OKR`, benefício, sponsor, risco ou dependência.
  - O roadmap interno já documenta esses pontos como bloqueados por dados:
    - `% itens com objetivo estratégico vinculado`
    - `% itens fora do foco estratégico ativo`
    - `Distribuição por tema estratégico`
    - indicadores de benefícios, riscos, dependências e marcos
  - O dashboard tem uma visualização de roadmap por `quarter` e status, mas isso ainda é planejamento temporal de portfólio, não uma camada estratégica FL3 no sentido do whitepaper.
- Julgamento final:
  - `FL1`: adequado
  - `FL2`: parcialmente adequado, mas operacionalmente frágil por falta de vínculo real no snapshot de portfólio e por ausência de dependências explícitas
  - `FL3`: inadequado no estado atual; faltam dados e mecanismos de alinhamento estratégico
- Próximos passos prioritários para aderir melhor a Flight Levels:
  1. Garantir que o `portfolio-bt-ns-latest-data.csv` publicado em `latest` use a versão enriquecida do exportador e materialize `ParentID`, `ParentTipo`, `FeatureLinkID`, `EpicLinkID`, `IssueLink*`.
  2. Criar uma ponte confiável entre o portfólio `BT/NS` e os fluxos de execução `BF/W1NNR/S1NC/DT`, para que `FL2` deixe de ser apenas visual e passe a ser rastreável.
  3. Adicionar no exportador de portfólio campos de `tema/objetivo estratégico`, `owner/sponsor`, `benefício esperado`, `risco`, `milestone/target date`.
  4. Só depois disso faz sentido afirmar aderência mais forte a `FL3`.
- Evidence (docs/data/code inspected):
  - `pdftotext /Users/rodrigoalmeidadeoliveira/Downloads/Flight-Levels-Whitepaper-Update-[2026].pdf -`
  - `python3 - <<'PY' ... portfolio-bt-ns-latest-data.csv ... PY`
  - `python3 - <<'PY' ... *-downstream-latest-data.csv ... PY`
  - `python3 - <<'PY' ... PowerBI_Model_latest.xlsx ... PY`
  - `sed -n '1,260p' jira_portfolio_to_csv.py`
  - `sed -n '1,320p' jira_to_pipeline_csv.py`
  - `sed -n '1950,2065p' dashboard_full.py`
  - `sed -n '5081,5165p' dashboard_full.py`
  - `sed -n '150,180p' ROADMAP_INDICADORES_PORTFOLIO.md`
  - `sed -n '221,275p' ROADMAP_INDICADORES_PORTFOLIO.md`
- Suggested commit message:
  - `docs(tasks): assess current Flight Levels adherence across portfolio and execution data`

## Current Task (Evoluir exportador de portfólio para expor vínculos)
- [x] Inspecionar o exportador atual e comparar com a lógica mais rica de hierarquia já usada no downstream
- [x] Incluir no CSV de portfólio campos de vínculo/hierarquia suficientes para reduzir falso positivo dos alertas técnicos
- [x] Preservar compatibilidade do dashboard com snapshots antigos sem os novos campos
- [x] Validar sintaxe e smoke tests dos helpers novos

## Specification (Evoluir exportador de portfólio para expor vínculos)
- Objetivo: enriquecer [`jira_portfolio_to_csv.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_portfolio_to_csv.py) para materializar no snapshot as informações mínimas de relacionamento que hoje só aparecem no exportador downstream.
- Campos alvo desta evolução:
  - `ParentTitle`
  - `HierarchyLinkSource`
  - `FeatureLinkID`
  - `FeatureLinkTipo`
  - `EpicLinkID`
  - `EpicLinkTipo`
  - `EpicLinkName`
  - `Componentes`
  - `Etiquetas`
  - links tipados agregados (`IssueLinks*`)
- Regras:
  - reaproveitar a semântica de resolução de hierarquia do `jira_to_pipeline_csv.py`
  - manter compatibilidade com snapshots antigos e com ambientes que não têm todos os custom fields
  - não depender de custo nem de método financeiro

## Review (Evoluir exportador de portfólio para expor vínculos)
- What was implemented:
  - [`jira_portfolio_to_csv.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_portfolio_to_csv.py) passou a exportar os novos campos:
    - `ParentTitle`
    - `HierarchyLinkSource`
    - `FeatureLinkID`
    - `FeatureLinkTipo`
    - `EpicLinkID`
    - `EpicLinkTipo`
    - `EpicLinkName`
    - `Componentes`
    - `Etiquetas`
    - `IssueLinkKeys`
    - `IssueLinkTypes`
    - `IssueLinkDetails`
  - A resolução de hierarquia agora reutiliza a mesma semântica defensiva do exportador downstream, incluindo suporte a `principal` e `epic_name` quando estiverem configurados no `JIRA_FIELD_MAP`.
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) foi ajustado para:
    - aceitar snapshots antigos sem esses campos
    - usar `Componentes`, `Etiquetas`, `IssueLinkTypes`, `EpicLinkID`, `FeatureLinkID` e `IssueLinkKeys` quando existirem para melhorar a detecção/vinculação técnica
- Evidence (tests/smoke):
  - `python3 -m py_compile jira_portfolio_to_csv.py dashboard_full.py`
  - `python3 - <<'PY' ... build_output_row(...) ... PY`
    - Resultados observados:
      - `ParentTitle Epic parent`
      - `HierarchyLinkSource parent_epic|epic_name_text`
      - `EpicLinkID BT-100`
      - `IssueLinkKeys BT-321`
      - `IssueLinkTypes relates to`
  - `python3 - <<'PY' ... import dashboard_full as d; snapshot, df, err = d.get_portfolio_snapshot() ... PY`
    - Resultados observados:
      - `error None`
      - `legacy_snapshot_still_loads True`
      - `tech_catalog_cols ['EpicLinkID', 'FeatureLinkID', 'IssueLinkKeys']`
  - Não foi executada exportação real contra o Jira nesta sessão, então a validação foi feita por compilação e smoke test sintético/local.
- Suggested commit message:
  - `feat(portfolio-export): add hierarchy and typed issue link fields to portfolio snapshot`

## Current Task (Remover ambiguidade entre pendências e quarter)
- [x] Localizar os rótulos `Q1/Q2/Q3` usados no indicador de pendências
- [x] Renomear buckets e títulos para faixas de aging explícitas
- [x] Validar sintaxe, revisar diff e registrar evidências

## Review (Remover ambiguidade entre pendências e quarter)
- What was validated:
  - O indicador deixou de reutilizar `Q1/Q2/Q3`, que competiam visualmente com a semântica de `Quarter` usada em outras partes da aba de Portfólio.
  - Os buckets agora aparecem como `Pendências 0-15d`, `Pendências 16-30d` e `Pendências +30d`, com a mesma lógica de cor e a mesma regra de aging anterior.
  - O título e a nota explicativa também passaram a usar `Faixa de Aging`, reduzindo ambiguidade conceitual na leitura da tela.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... compute_portfolio_snapshot(...) ... PY`
    - Resultados: `['Pendências 0-15d', 'Pendências 16-30d']`, `True`, `True`, `True`
  - `git diff -- dashboard_full.py tasks/todo.md tasks/lessons.md`
- Suggested commit message:
  - `fix(portfolio): rename pending buckets to avoid quarter ambiguity`

## Current Task (Implementar fase 1 de alertas de portfólio)
- [x] Mapear o encaixe da nova seção na aba de portfólio do `dashboard_full.py`
- [x] Adicionar cálculos no snapshot para alertas de integridade estrutural, estagnação e prazo
- [x] Adicionar aba/seção visual `Alertas` no módulo de portfólio
- [x] Exibir backlog explícito de prontidão técnica como pendência de contrato de dados
- [x] Validar sintaxe, smoke test local e revisar diff

## Specification (Implementar fase 1 de alertas de portfólio)
- Objetivo: materializar a primeira fase da [`ESPECIFICACAO_ALERTAS_PORTFOLIO.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/ESPECIFICACAO_ALERTAS_PORTFOLIO.md) usando apenas o snapshot atual do portfólio.
- Escopo de implementação:
  - `Épicos sem feature`
  - `Features sem story/task`
  - `Stories/Tasks órfãos`
  - estagnação de épicos e features em `>10`, `>20` e `>30` dias
  - itens vencidos e vencendo em `7`, `14` e `30` dias
  - alertas combinados de prazo + falta de decomposição
- Fora do escopo desta implementação:
  - custos
  - cálculo factual de prontidão técnica por arquitetura/infra/segurança
  - dependências tipadas sem enriquecimento do exportador

## Review (Implementar fase 1 de alertas de portfólio)
- What was implemented:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) passou a calcular no `compute_portfolio_snapshot(...)` os alertas de:
    - `Épico sem feature`
    - `Feature sem story/task`
    - `Story/Task órfão`
    - `Épico parado`
    - `Feature parada`
    - `Item vencido`
    - `Item próximo do vencimento`
    - `Prazo crítico sem decomposição`
  - Os alertas agora geram grupos dedicados no snapshot: detalhe, resumo por indicador, resumo por severidade, agregações por time/projeto, KPIs de topo e nota explícita sobre a pendência de prontidão técnica.
  - A aba `Portfólio` recebeu uma nova temática `Alertas`, com cards de KPI, gráfico de severidade, tabelas por tipo/time/projeto, backlog detalhado de alertas e quadro de limitações para prontidão técnica.
  - Custos ficaram fora desta entrega, conforme a decisão registrada na especificação.
- Evidence (tests/smoke):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... import dashboard_full as d; snapshot, df, err = d.get_portfolio_snapshot(); ... d.render_tab('portfolio', ...) ... PY`
    - Resultados observados:
      - `error None`
      - `detail_rows 389`
      - `kpi_rows 8`
      - `tech_rows 2`
      - `has_alert_tab True`
      - `has_alert_title True`
- Suggested commit message:
  - `feat(portfolio): add first-phase alert panel for structure staleness and due dates`

## Current Task (Implementar fase 2 proxy dos alertas técnicos de portfólio)
- [x] Inspecionar sinais reais disponíveis nas bases para arquitetura, infra e segurança
- [x] Registrar o escopo da fase 2 como proxy explícito baseado no snapshot atual
- [x] Implementar classificação técnica por `TEAM`/título e consolidar alertas por épico
- [x] Exibir no painel a cobertura técnica proxy por épico e o catálogo de itens técnicos detectados
- [x] Validar sintaxe, smoke tests e registrar o comportamento observado nos dados atuais

## Review (Implementar fase 2 proxy dos alertas técnicos de portfólio)
- What was implemented:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) passou a classificar itens técnicos por proxy usando `TEAM` e `Titulo`, com três categorias: `arquitetura`, `infra` e `segurança`.
  - A cobertura técnica do épico agora usa apenas vínculo explícito `ParentID` no próprio snapshot de portfólio; quando não há item técnico classificado e vinculado, o dashboard gera alertas do tipo:
    - `Épico sem item técnico de arquitetura`
    - `Épico sem item técnico de infra`
    - `Épico sem item técnico de seguranca`
    - além dos casos futuros de `... não validado` quando existir item técnico vinculado mas ainda não concluído
  - A aba `Alertas` agora também mostra:
    - `Cobertura técnica proxy por épico`
    - `Catálogo de itens técnicos detectados no snapshot`
    - notas explícitas sobre a limitação do proxy e a ausência de vínculo factual confiável com downstream
- Evidence (tests/smoke/data inspection):
  - `python3 - <<'PY' ... get_portfolio_snapshot(); load_project_downstream_items_csv(...); scan de colunas/samples ... PY`
    - Evidência principal: os épicos do portfólio aparecem como `BT-*`, enquanto os vínculos de downstream explorados localmente não casam com esses IDs; `matched_epics_count 0`
    - Evidência secundária: o snapshot atual já contém sinais de times técnicos como `TECH SECURITY`, `TECH INFRA`, `TECH ARQUITETURA`
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... snapshot['groups']['portfolio_technical_epic_summary'] ... render_tab('portfolio', ...) ... PY`
    - Resultados observados:
      - `tech_epic_summary_rows 136`
      - `tech_catalog_rows 15`
      - `tech_alert_rows 408`
      - `has_tech_summary True`
      - `has_tech_catalog True`
- Key limitation observed:
  - O proxy atual é propositalmente conservador: sem vínculo hierárquico explícito no snapshot, o épico é tratado como sem cobertura técnica mesmo que exista trabalho técnico correlato fora dessa hierarquia. Isso evita falso positivo de “cobertura concluída” sem evidência.
- Suggested commit message:
  - `feat(portfolio): add proxy technical readiness alerts for architecture infra and security`

## Current Task (Especificar indicadores e alertas de portfólio)
- [x] Consolidar regras objetivas para integridade estrutural, estagnação e risco de prazo
- [x] Separar o que é implementável com snapshot atual do que exige enriquecer o exportador
- [x] Deixar custos explicitamente fora da primeira fase por ausência de método e campos
- [x] Registrar a especificação em documento dedicado e referenciar no backlog

## Review (Especificar indicadores e alertas de portfólio)
- What was defined:
  - Foi criada a especificação [`ESPECIFICACAO_ALERTAS_PORTFOLIO.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/ESPECIFICACAO_ALERTAS_PORTFOLIO.md) com definição objetiva de indicadores, regras de severidade e backlog técnico.
  - A fase inicial ficou limitada a alertas implementáveis com o snapshot atual: épicos sem feature, features sem story/task, órfãos, itens parados (>10/>20/>30 dias), itens vencidos/próximos do vencimento e alertas combinados de prazo + falta de decomposição.
  - A trilha de `Prontidão Técnica` foi dividida em duas fases: proxy com sinais já disponíveis no dataset e versão factual após enriquecimento do contrato de dados e cruzamento com downstream.
  - Custos foram explicitamente deixados por último, fora da primeira fase, até existir método e campos confiáveis no portfólio.
- Evidence (artifacts reviewed/created):
  - [`ESPECIFICACAO_ALERTAS_PORTFOLIO.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/ESPECIFICACAO_ALERTAS_PORTFOLIO.md)
  - `rg -n "alerta|alertas|portf[oó]lio|especifica|integridade|estagna|vencimento|target date|custo" -g '!node_modules/**' -g '!artifacts/**' *.md tasks/todo.md tasks/lessons.md`
  - `ls *.md`
- Suggested commit message:
  - `docs(portfolio): specify alert indicators and implementation rules`

## Current Task (Diagnosticar painel de observabilidade do fluxo para portfólio e downstream)
- [x] Revisar memória do projeto e documentação central sobre pipeline, dashboards e fontes de dados
- [x] Confirmar no código como o dashboard principal consome downstream, portfólio, gargalos e process mining
- [x] Mapear o que já existe para observabilidade de fluxo e o que ainda está bloqueado por contrato de dados
- [x] Consolidar proposta de abordagem e lista objetiva de pendências

## Review (Diagnosticar painel de observabilidade do fluxo para portfólio e downstream)
- What was validated:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) já opera como ponto central de observabilidade, combinando `Fato_Items`/`Fato_Gargalos` do `PowerBI_Model_*.xlsx`, CSV snapshot de portfólio e fallbacks para CSV downstream detalhado por projeto.
  - [`run_all_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects_macos.sh) confirma o pipeline operacional atual: exportação downstream por projeto, exportação de portfólio, geração de métricas e publicação de artefatos `latest`.
  - [`jira_to_pipeline_csv.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_to_pipeline_csv.py) fornece granularidade temporal suficiente para observabilidade operacional de downstream, incluindo datas por etapa e vínculos hierárquicos.
  - [`jira_portfolio_to_csv.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/jira_portfolio_to_csv.py) ainda exporta apenas snapshot com `UpdatedAt`, `StatusChangedAt` e `DueDate`; isso sustenta aging/governança, mas não throughput histórico, CFD real ou lead time de portfólio.
  - [`ROADMAP_INDICADORES_PORTFOLIO.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/ROADMAP_INDICADORES_PORTFOLIO.md) continua coerente com o código: boa parte do portfólio snapshot já está implementada, e os gaps mais relevantes continuam ligados à ausência de histórico/eventos no exportador.
- Evidence (docs/code inspected):
  - `sed -n '1,220p' tasks/lessons.md`
  - `sed -n '1,220p' tasks/todo.md`
  - `sed -n '1,260p' ARQUITETURA_E_FUNCIONAMENTO_PROJETO.md`
  - `sed -n '1,260p' ROADMAP_INDICADORES_PORTFOLIO.md`
  - `sed -n '1,260p' dashboard_full.py`
  - `sed -n '340,1320p' dashboard_full.py`
  - `sed -n '1848,2525p' dashboard_full.py`
  - `sed -n '4564,5055p' dashboard_full.py`
  - `sed -n '1,260p' run_all_projects_macos.sh`
  - `sed -n '1,260p' dash_board_metricas.py`
  - `sed -n '1,260p' jira_portfolio_to_csv.py`
  - `sed -n '1,260p' jira_to_pipeline_csv.py`
  - `rg -n "portfolio|downstream|observab|fluxo|Painel de Fluxo|dashboard_full|dash_board_metricas|PowerBI|process mining" -g '!node_modules/**' -g '!artifacts/**'`
- Suggested commit message:
  - `docs(tasks): record observability assessment for portfolio and downstream`

## Current Task (Detalhar pendências de portfólio)
- [x] Inspecionar a regra atual do indicador `Q Pendências por TEAM` no snapshot de portfólio
- [x] Expor na UI a definição operacional de pendência e dos quadrantes Q1/Q2/Q3
- [x] Adicionar detalhamento das pendências por composição e lista de itens
- [x] Validar sintaxe, revisar diff e registrar evidências

## Review (Detalhar pendências de portfólio)
- What was validated:
  - O indicador agora explica na própria UI a regra operacional: pendência é item aberto no snapshot de portfólio e os quadrantes representam faixas de dias sem alteração (`Q1 <= 15`, `Q2 = 16-30`, `Q3 > 30`).
  - Além dos cards por TEAM, a tela passou a mostrar uma tabela de composição das pendências por `Quadrante`, `Tipo` e `StatusCategoria`.
  - A tela também passou a listar os itens que compõem cada pendência, com `Team`, `Projeto`, `Tipo`, `ItemID`, `Título`, `Status`, `DiasSemAlteracao`, `ParentID` e `Link`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... compute_portfolio_snapshot(...) ... PY`
    - Resultados: `pendencias_q_por_time 16 ['Quadrante', 'Team', 'WorkItems']`, `pendencias_breakdown 12 ['Quadrante', 'Tipo', 'StatusCategoria', 'WorkItems']`, `pendencias_detalhe 213 ['Quadrante', 'Team', 'Projeto', 'Tipo', 'ItemID', 'Titulo', 'Status', 'StatusCategoria', 'DiasSemAlteracao', 'ParentID', 'Link']`
  - `git diff --stat -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(portfolio): explain and detail pending items by quadrant`

## Current Task (Mover Bitbucket de run_all_projects para run_process_mining_projects)
- [x] Remover Bitbucket dos scripts `run_all_projects`
- [x] Incluir exportação Bitbucket nos scripts dedicados de process mining
- [x] Validar sintaxe, revisar diff e registrar o novo ponto de execução

## Review (Mover Bitbucket de run_all_projects para run_process_mining_projects)
- What was validated:
  - [`run_all_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects_macos.sh) e [`run_all_projects.ps1`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects.ps1) não têm mais flags, arrays, funções ou etapas de exportação Bitbucket.
  - [`run_process_mining_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_projects_macos.sh) agora exporta Bitbucket logo após cada projeto de process mining e publica `commits`, `pullrequests` e `pipelines` no `LATEST_DIR`.
  - [`run_process_mining_projects.ps1`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_projects.ps1) recebeu a mesma responsabilidade no fluxo Windows.
  - O ponto de execução de Bitbucket passou a ser:
    - macOS: `./run_process_mining_projects_macos.sh`
    - Windows PowerShell: `.\run_process_mining_projects.ps1`
- Evidence (tests/logs/diff):
  - `bash -n run_all_projects_macos.sh`
  - `bash -n run_process_mining_projects_macos.sh`
  - `rg -n "Bitbucket|bitbucket|RUN_BITBUCKET_EXPORT|RunBitbucketExport" run_all_projects_macos.sh run_all_projects.ps1 run_process_mining_projects_macos.sh run_process_mining_projects.ps1`
  - `git diff -- run_all_projects_macos.sh run_all_projects.ps1 run_process_mining_projects_macos.sh run_process_mining_projects.ps1 tasks/todo.md`
- Suggested commit message:
  - `refactor(run-all): move bitbucket export into process mining scripts`

## Current Task (Separar process mining de run_all_projects)
- [x] Mapear onde `run_all_projects` ainda embutia exportação de process mining
- [x] Remover process mining dos scripts `run_all_projects` sem afetar downstream, Bitbucket, portfólio e métricas
- [x] Criar scripts dedicados para process mining em macOS e Windows
- [x] Validar sintaxe, revisar diff e registrar como executar o fluxo separado

## Review (Separar process mining de run_all_projects)
- What was validated:
  - [`run_all_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects_macos.sh) e [`run_all_projects.ps1`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects.ps1) não executam mais process mining nem expõem flags dedicadas a essa etapa.
  - O `run_all_projects` voltou a cuidar apenas de downstream, Bitbucket, portfólio, métricas e abertura do dashboard; o changelog detalhado só é gerado quando `RunDetailedChangelogExport` for explicitamente habilitado.
  - Foram criados [`run_process_mining_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_projects_macos.sh) e [`run_process_mining_projects.ps1`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_projects.ps1), que exportam changelog detalhado por projeto, executam `process_mining_jira.py`, publicam os `*latest*` gerados e seguem adiante quando um projeto não tiver eventos.
  - Uso registrado:
    - macOS: `./run_process_mining_projects_macos.sh`
    - Windows PowerShell: `.\run_process_mining_projects.ps1`
- Evidence (tests/logs/diff):
  - `bash -n run_all_projects_macos.sh`
  - `bash -n run_process_mining_projects_macos.sh`
  - `command -v pwsh >/dev/null 2>&1 && pwsh ... || echo 'pwsh-unavailable'`
    - Resultado no ambiente atual: `pwsh-unavailable`
  - `git diff -- run_all_projects_macos.sh run_all_projects.ps1 run_process_mining_projects_macos.sh run_process_mining_projects.ps1 tasks/todo.md`
  - `git diff --stat -- run_all_projects_macos.sh run_all_projects.ps1 run_process_mining_projects_macos.sh run_process_mining_projects.ps1 tasks/todo.md`
- Suggested commit message:
  - `refactor(run-all): move process mining export into dedicated scripts`

## Current Task (Evitar que process mining bloqueie os latest do dashboard no macOS)
- [x] Confirmar por que `dashboard_output_latest.xlsx`, `bottlenecks_consolidado_latest.xlsx` e `PowerBI_Model_latest.xlsx` não estavam sendo publicados
- [x] Ajustar `run_all_projects_macos.sh` para não abortar o pipeline de métricas quando process mining falhar ou não tiver eventos
- [x] Validar sintaxe, revisar diff e registrar a correção

## Review (Evitar que process mining bloqueie os latest do dashboard no macOS)
- What was validated:
  - Os arquivos pedidos (`dashboard_output_latest.xlsx`, `bottlenecks_consolidado_latest.xlsx`, `PowerBI_Model_latest.xlsx` e `portfolio-bt-ns-latest-data.csv`) dependem da continuação do pipeline após process mining.
  - No log enviado, o script parava em `Gerando process mining para DT... Nenhum evento após filtros`, então nunca chegava na etapa `RUN_METRICS=true`, que é a responsável por gerar os três `.xlsx` latest do dashboard.
  - [`run_all_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects_macos.sh) agora trata falhas de process mining como aviso acumulado (`PROCESS_MINING_FAILURES`) e segue para portfolio e métricas, preservando a geração/publicação dos latest do dashboard.
- Evidence (tests/logs/diff):
  - `bash -n run_all_projects_macos.sh`
  - `rg -n "PROCESS_MINING_FAILURES|process mining falhou|Avisos Process Mining" run_all_projects_macos.sh`
  - `git diff -- run_all_projects_macos.sh tasks/todo.md`
- Suggested commit message:
  - `fix(run-all): keep metrics running when process mining has no data on macos`

## Current Task (Republicar imagens de process mining no latest do run_all macOS)
- [x] Confirmar por que os `.png` de process mining deixaram de aparecer no `LATEST_DIR` após a refatoração
- [x] Ajustar `run_all_projects_macos.sh` para sincronizar os `*latest*` de `artifacts/process_mining` com a pasta latest do pipeline
- [x] Validar sintaxe, revisar diff e registrar a correção

## Review (Republicar imagens de process mining no latest do run_all macOS)
- What was validated:
  - O problema não era geração: os `.png` de process mining continuavam sendo criados em `artifacts/process_mining`, como mostrado no log de `process_mining_jira.py`.
  - Após a refatoração do `run_all_projects_macos.sh`, a etapa de process mining deixou de espelhar os artefatos `*latest*` para o `LATEST_DIR` do pipeline, diferente do que já acontecia com downstream, portfolio e Bitbucket.
  - [`run_all_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects_macos.sh) agora chama `sync_latest_artifacts_from_out_dir "$PROCESS_MINING_OUT_DIR" "$LATEST_DIR"` logo após cada execução de process mining, republicando `.xlsx`, `.csv` e `.png` latest na pasta `latest` que você está conferindo.
- Evidence (tests/logs/diff):
  - `bash -n run_all_projects_macos.sh`
  - `rg -n "sync_latest_artifacts_from_out_dir" run_all_projects_macos.sh`
  - `git diff -- run_all_projects_macos.sh tasks/todo.md`
- Suggested commit message:
  - `fix(run-all): republish process mining latest artifacts into macos latest directory`

## Current Task (Separar extração de process mining no run_all macOS)
- [x] Confirmar onde `run_all_projects_macos.sh` mistura export downstream, changelog, process mining e Bitbucket no mesmo loop
- [x] Refatorar o script para executar process mining em etapa separada dos demais artefatos do dashboard
- [x] Validar sintaxe, revisar diff e registrar a nova orquestração

## Review (Separar extração de process mining no run_all macOS)
- What was validated:
  - [`run_all_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects_macos.sh) deixou de misturar downstream, process mining e Bitbucket no mesmo loop por projeto.
  - A exportação dos artefatos do dashboard ficou isolada em `export_project_dashboard_artifacts`, enquanto process mining roda depois em `run_project_process_mining` usando o changelog detalhado já gerado.
  - A exportação Bitbucket também passou para uma fase separada, então o fluxo ficou sequenciado em: downstream/gargalos/changelog, depois process mining, depois Bitbucket.
- Evidence (tests/logs/diff):
  - `bash -n run_all_projects_macos.sh`
  - `rg -n "Iniciando etapa separada|export_project_dashboard_artifacts|run_project_process_mining|export_project_bitbucket_artifacts" run_all_projects_macos.sh`
  - `git diff -- run_all_projects_macos.sh tasks/todo.md`
- Suggested commit message:
  - `refactor(run-all): split process mining extraction from dashboard artifact export on macos`

## Current Task (Ignorar artefatos csv/xlsx/png no Git)
- [x] Inspecionar o `.gitignore` atual e confirmar o impacto no worktree
- [x] Adicionar regras para ignorar arquivos `.csv`, `.xlsx` e `.png`
- [x] Validar o diff e registrar o resultado na seção de review

## Review (Ignorar artefatos csv/xlsx/png no Git)
- What was validated:
  - [`/.gitignore`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/.gitignore) agora ignora globalmente `*.csv`, `*.xlsx` e `*.png`.
  - O `git status` continua mostrando artefatos já versionados em `artifacts/process_mining`; o novo ignore evita novos arquivos não rastreados dessas extensões, mas não remove do índice arquivos já commitados.
- Evidence (tests/logs/diff):
  - `git diff -- .gitignore tasks/todo.md`
  - `git status --short .gitignore tasks/todo.md artifacts/process_mining`
- Suggested commit message:
  - `chore(gitignore): ignore generated csv xlsx and png artifacts`

## Current Task (Expandir process mining e Bitbucket para S1NC, DATA&ANALITICS e BEFINANCE)
- [x] Mapear os pontos hardcoded de projeto/prefixo no pipeline de process mining, na automação `run_all` e no consumo Bitbucket
- [x] Generalizar `process_mining_jira.py` para aceitar aliases/prefixos por projeto além de W1NNER
- [x] Estender a automação principal para gerar changelog detalhado e artefatos de process mining para S1NC, DATA&ANALITICS e BEFINANCE
- [x] Ajustar a extração Bitbucket para suportar múltiplos projetos, incluindo o caso em que W1NNER e S1NC compartilham o mesmo repositório
- [x] Validar sintaxe, revisar diff e registrar evidências na seção de review

## Review (Expandir process mining e Bitbucket para S1NC, DATA&ANALITICS e BEFINANCE)
- What was validated:
  - `process_mining_jira.py` deixou de assumir W1NNER como único projeto e agora resolve aliases, prefixo de saída e fluxo padrão por projeto para `W1NNR/W1NNER`, `S1NC`, `BF/BEFINANCE` e `DT/DATA&ANALITICS`, incluindo a grafia `DATA&ANALITICS`.
  - `run_all_projects.ps1` e `run_all_projects_macos.sh` passaram a gerar changelog detalhado quando necessário, produzir artefatos de process mining por projeto em `artifacts/process_mining` e disparar exportação Bitbucket por projeto.
  - `bitbucket_export.py` agora aceita `--project`, resolve repo/prefixo por projeto, suporta overrides por env e filtra commits/PRs/pipelines pelos prefixes Jira do projeto; isso separa corretamente `S1NC` de `W1NNER` mesmo compartilhando o repositório `w1nner`.
  - Os consumers de prefixo Bitbucket foram alinhados para `S1NC`, `BEFINANCE` e `DATA&ANALITICS` também no dashboard dedicado e no dashboard principal.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile process_mining_jira.py bitbucket_export.py dashboard_process_mining.py dashboard_full.py`
  - `python3 process_mining_jira.py --help`
  - `python3 bitbucket_export.py --help`
  - `bash -n run_all_projects_macos.sh`
  - `python3 - <<'PY' ... resolve_project_process_mining_config(...) ... PY`
    - Resultados: `W1NNR -> w1nner-process-mining`, `S1NC -> s1nc-process-mining`, `BF -> befinance-process-mining`, `DT/DATA&ANALITICS/DATA&ANALITICS -> dataanalytics-process-mining`
  - `python3 bitbucket_export.py --project S1NC --dry-run`
    - Resultado: `repo=w1nner`, `prefix=s1nc`, `issue_key_prefixes=W1SFT,S1NC`
  - `python3 bitbucket_export.py --project BF --dry-run`
    - Resultado: `repo=befinance`, `prefix=befinance`, `issue_key_prefixes=BF,BEFINANCE`
  - `python3 bitbucket_export.py --project DATA\&ANALITICS --dry-run`
    - Resultado: `repo=dataanalytics`, `prefix=dataanalytics`, `issue_key_prefixes=DT,DA`
  - `python3 - <<'PY' ... work_item_keys_match_project(...) ... PY`
    - Resultados: `S1NC-10` casa com `S1NC/W1SFT`, `W1NNR-10` não casa com `S1NC/W1SFT`, `DA-99` casa com `DT/DA`
  - `git diff -- process_mining_jira.py bitbucket_export.py run_all_projects.ps1 run_all_projects_macos.sh dashboard_process_mining.py dashboard_full.py .env.example tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): expand jira and bitbucket extraction to s1nc befinance and dataanalytics`

## Current Task (Fixar latest do process mining no macOS)
- [x] Inspecionar a resolução atual do diretório `latest` em `process_mining_jira.py`
- [x] Ajustar o pipeline para publicar aliases `latest` no macOS sempre em `/Users/rodrigoalmeidadeoliveira/Documents/dados/latest`
- [x] Preservar o destino atual quando a execução ocorrer em Windows
- [x] Validar a resolução do caminho e registrar evidências

## Review (Fixar latest do process mining no macOS)
- What was validated:
  - `process_mining_jira.py` passou a usar o path fixo `/Users/rodrigoalmeidadeoliveira/Documents/dados/latest` como destino central de aliases `latest` quando executado no macOS.
  - Em macOS, o pipeline de process mining agora ignora `FLOW_PMO_LATEST_DIR` para evitar que overrides desviem a publicação para outro diretório.
  - O comportamento de Windows foi preservado, mantendo o default `C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile process_mining_jira.py`
  - `python3 - <<'PY' ... os.environ['FLOW_PMO_LATEST_DIR']='/tmp/nao-deve-ser-usado'; print(pm._resolve_central_latest_dir(Path('artifacts/process_mining'))) ... PY`
    - Resultado: `/Users/rodrigoalmeidadeoliveira/Documents/dados/latest`
  - `git diff -- process_mining_jira.py tasks/todo.md`
- Suggested commit message:
  - `fix(process-mining): force macos latest artifacts into documents dados latest`

## Current Task (Refazer breakdown de componentes do Lead Time)
- [x] Inspecionar o gráfico atual de breakdown e confirmar quais métricas por componente já estão disponíveis no dataframe
- [x] Atualizar a visualização para destacar ranking por dias médios e participação relativa de cada componente
- [x] Validar sintaxe, revisar diff e registrar evidências da melhoria

## Review (Refazer breakdown de componentes do Lead Time)
- What was validated:
  - O gráfico anterior condensava toda a decomposição em uma única barra empilhada, o que escondia ranking, magnitude relativa e participação de cada componente.
  - A visualização foi substituída por um painel duplo: barras horizontais ordenadas por `Dias médios por componente` e um donut com `Participação no lead time`.
  - Cada componente agora exibe rótulo direto com dias médios e percentual, além de anotação com o `Lead time médio` consolidado.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `improve(flow-efficiency): replace stacked lead-time breakdown with ranked component view`

## Current Task (Refazer gráfico de Eficiência de Fluxo)
- [x] Diagnosticar a inconsistência entre o título do gráfico e os eixos atualmente plotados
- [x] Reestruturar o gráfico para usar semana de referência no eixo temporal e agregação coerente da eficiência de fluxo
- [x] Validar sintaxe, revisar diff e registrar a evidência da correção

## Review (Refazer gráfico de Eficiência de Fluxo)
- What was validated:
  - O gráfico anterior comparava `Eficiencia` com `EficienciaAjustada`, mas ambas tinham exatamente o mesmo valor semanal; por isso a visualização colapsava na diagonal `y=x` e não comunicava evolução por semana.
  - O gráfico foi refeito como combinação semanal: barras para `Chegadas` e `Throughput`, com linha no eixo secundário para `Eficiência de Fluxo (1-ρ)`.
  - A tabela detalhada deixou de expor colunas redundantes (`EficienciaAjustada` e `Diferença Eficiência`) e passou a incluir `SemanaReferencia`.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(flow-efficiency): replace meaningless scatter with weekly efficiency time series`

## Current Task (Corrigir filtros na tela de Portfólio)
- [x] Confirmar quais filtros globais devem afetar o CSV de portfólio e quais colunas/dados estão disponíveis para isso
- [x] Ajustar a montagem do escopo do módulo Portfólio para aplicar projeto, tipo e classe de serviço sem ignorar seleções válidas
- [x] Definir comportamento explícito para filtros sem suporte nativo no CSV de portfólio, evitando fallback silencioso para "Todos"
- [x] Validar sintaxe e executar smoke test local da lógica de filtros do portfólio

## Review (Corrigir filtros na tela de Portfólio)
- What was validated:
  - O módulo Portfólio passou a aplicar o filtro global de `Projeto` sobre a coluna `Team` do CSV de portfólio, por correspondência textual do team.
  - O dropdown específico `TEAM (Portfólio)` passou a listar os valores reais da coluna `Team` e faz recorte exato quando selecionado.
  - `ClasseServico` agora é derivada de `Prioridade` quando o CSV não traz a coluna pronta, permitindo que opções como `Highest` filtrem de fato a tela.
  - O filtro global de `Tipo` agora usa uma canonização própria para o portfólio (`Épico`/`Feature`/`História` -> `Desenvolvimento`, `Support` -> `Suporte`, etc.).
  - Filtros sem suporte no CSV atual, como `Responsável`, deixaram de cair silenciosamente em "Todos os projetos": a tela mostra escopo vazio e um aviso explícito.
  - No snapshot atual, `Projeto=S1NC` retorna os teams `Squad | S1NC` e `TECH S1NC`, enquanto `TEAM (Portfólio)=TECH S1NC` recorta apenas esse team.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... d.apply_portfolio_module_filters(...) ... PY`
    - Resultados: `projeto_S1NC_len 29`, `teams ['Squad | S1NC', 'TECH S1NC']`, `team_exact_len 28`, `team_exact_teams ['TECH S1NC']`, `class_Highest 25 ['Highest'] []`, `responsavel 0 ['O CSV atual de portfólio não possui informação de responsável.']`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(portfolio): filter portfolio by team semantics instead of project column`

## Current Task (Eliminar warning pandas e conflito de porta do dashboard)
- [x] Localizar a origem do `FutureWarning` em `dashboard_full.py`
- [x] Ajustar a normalização numérica para evitar downcast implícito após `fillna`
- [x] Ajustar bootstrap do Dash para usar `serve_locally=True` e procurar porta livre a partir da porta preferida
- [x] Validar sintaxe, comportamento do fallback de porta e diff

## Review (Eliminar warning pandas e conflito de porta do dashboard)
- What was validated:
  - O `FutureWarning` em `quality_por_team` vinha do padrão `Series[object].fillna(0).astype(int)` após `merge`; a coluna passou a ser normalizada com `pd.to_numeric(..., errors='coerce').fillna(0).astype(int)`.
  - O warning do Dash sobre `serve_locally=False` foi eliminado ao inicializar a aplicação com `serve_locally=True`, compatível com execução local em debug.
  - O bootstrap do servidor deixou de depender fixamente da porta `8050`: agora lê `FLOW_PMO_DASH_PORT` ou `PORT`, testa disponibilidade e sobe na próxima porta livre dentro de uma janela de 20 portas.
  - A lógica de fallback foi validada por simulação controlada de `_is_port_available`, já que o sandbox bloqueia `bind()` real em socket de teste.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 -c "import warnings, pandas as pd; s=pd.Series([1, None, '3'], dtype='object'); warnings.simplefilter('error', FutureWarning); out=pd.to_numeric(s, errors='coerce').fillna(0).astype(int); print(out.tolist())"`
    - Resultado: `[1, 0, 3]`
  - `python3 -c "import os, dashboard_full as d; os.environ['FLOW_PMO_DASH_PORT']='8050'; seq=iter([False, True]); d._is_port_available=lambda port, host='127.0.0.1': next(seq); print(d._resolve_dash_runtime_options())"`
    - Resultado: `Porta 8050 ocupada; iniciando Dash em http://127.0.0.1:8051/` e `{'host': '127.0.0.1', 'port': 8051, 'debug': True}`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(dashboard): avoid pandas fillna downcast warning and auto-select a free Dash port`

## Current Task (Corrigir destino `latest` no macOS)
- [x] Diagnosticar por que artefatos `.xlsx` estavam sendo publicados com caminho híbrido macOS + Windows
- [x] Ajustar resolução de `FLOW_PMO_LATEST_DIR` para ignorar path Windows quando executando no macOS
- [x] Padronizar fallback do macOS para `/Users/rodrigoalmeidadeoliveira/Documents/dados/latest` sem alterar o default do Windows
- [x] Validar sintaxe, diff e caminho resolvido

## Current Task (Unificar regra de pressão de fluxo entre telas)
- [x] Confirmar diferenças de regra entre One Page e Capacidade de Fila
- [x] Ajustar Capacidade de Fila para usar `LeadStart_Selected` como chegada e `done_time_eligible_mask` como vazão
- [x] Aplicar filtro de `ClasseServico` também na base da Capacidade de Fila
- [x] Validar sintaxe e revisar diff

## Review (Unificar regra de pressão de fluxo entre telas)
- What was validated:
  - A aba `Capacidade de Fila` passou a usar a mesma semântica de cálculo da pressão do One Page: chegadas por `LeadStart_Selected` e throughput por itens concluídos elegíveis.
  - O filtro de `ClasseServico` também foi aplicado no recorte da aba de capacidade, alinhando os filtros entre telas.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); ast.parse(pathlib.Path('dash_board_metricas.py').read_text(encoding='utf-8')); print('ok')"`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(flow-pressure): align queue capacity rho calculation with one-page rules`

## Current Task (Correção de parse dd/mm para datas de criação)
- [x] Diagnosticar por que itens com `Created` visível no Jira ainda ficavam sem base LT
- [x] Corrigir parse para `dayfirst=True` no preenchimento de `DataCriacaoID` no consolidado
- [x] Corrigir parser flexível do dashboard para tratar `dd/mm/yyyy` sem inversão mês/dia
- [x] Validar sintaxe e teste pontual de parsing (`05/01/2026 -> 2026-01-05`)

## Review (Correção de parse dd/mm para datas de criação)
- What was validated:
  - Causa raiz confirmada: datas textuais `dd/mm/yyyy` estavam sendo lidas em modo padrão (`month-first`) em pontos críticos, causando `Created` posterior ao `Done`.
  - `dash_board_metricas.py` passou a parsear `Created` com `dayfirst=True` ao preencher `DataCriacaoID`.
  - `_coerce_datetime_flexible(...)` em `dashboard_full.py` passou a detectar `dd/mm/yyyy` e parsear com `dayfirst=True`, com normalização de timezone.
  - Teste pontual validou o comportamento: `05/01/2026 -> 2026-01-05`.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); ast.parse(pathlib.Path('dash_board_metricas.py').read_text(encoding='utf-8')); print('ok')"`
  - `python -c "import pandas as pd, dashboard_full as d; s=pd.Series(['05/01/2026','01/05/2026']); print(d._coerce_datetime_flexible(s).astype(str).tolist())"`
  - `git diff -- dashboard_full.py dash_board_metricas.py tasks/todo.md`
- Suggested commit message:
  - `fix(dates): parse dd/mm creation dates with dayfirst to avoid invalid lead-time negatives`

## Current Task (Extrair campo Start date do Jira)
- [x] Confirmar que `BF-207` possui `Start date` visível no Jira e não estava no downstream consolidado
- [x] Ajustar exportador (`jira_to_pipeline_csv.py`) para incluir `Start date` no CSV
- [x] Incluir `startdate` na lista de campos buscados na API Jira
- [x] Atualizar consolidação para priorizar `Start date` na resolução de início quando `In Progress` estiver vazio
- [x] Validar sintaxe das alterações

## Review (Extrair campo Start date do Jira)
- What was validated:
  - O downstream passou a suportar coluna explícita `Start date` no export.
  - A busca de issues agora inclui o campo Jira `startdate` (além de suportar mapeamento customizado `start_date` via `JIRA_FIELD_MAP`).
  - A consolidação (`resolve_in_progress_date`) passou a considerar `Start date` como primeira opção de fallback antes das demais etapas.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_pipeline_csv.py').read_text(encoding='utf-8')); ast.parse(pathlib.Path('dash_board_metricas.py').read_text(encoding='utf-8')); print('ok')"`
  - `rg -n "Start date|startdate|custom_as_date_text|resolve_in_progress_date" jira_to_pipeline_csv.py dash_board_metricas.py`
- Suggested commit message:
  - `feat(jira-export): include Start date and use it as lead-time start fallback`

## Current Task (Extrair start de etapas intermediárias no consolidado)
- [x] Validar caso `BF-207` e localizar coluna de start disponível no downstream
- [x] Ajustar `resolve_in_progress_date` para usar a primeira data válida do workflow quando `In Progress` vier vazio
- [x] Preencher IDs de data no fato (`DataInicioProgressoID`, `DataConclucaoID`, `DataCancelamentoID`) para auditoria
- [x] Validar sintaxe e estimar quantos itens sem base LT passam a ter start via nova regra

## Review (Extrair start de etapas intermediárias no consolidado)
- What was validated:
  - `BF-207` no downstream possui start em `ready homolog = 04/02/2026`, embora `In Progress` esteja vazio.
  - `resolve_in_progress_date` foi atualizado para fallback robusto: se `In Progress` não existir, usa a menor data entre etapas de workflow (excluindo `Done`).
  - O fato passa a preencher `DataInicioProgressoID`, `DataConclucaoID` e `DataCancelamentoID` com timestamps efetivos quando disponíveis.
  - Avaliação no recorte atual dos `84` sem base LT mostrou que `73` já têm start recuperável no downstream com essa regra (restam `11` sem qualquer data de início).
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dash_board_metricas.py').read_text(encoding='utf-8')); print('dash_board_metricas.py ok')"`
  - `python -c "import pandas as pd, dashboard_full as d; ...; print('missing_lt',84,'with_start_in_downstream',73,'without_start_any',11)"`
  - `git diff -- dash_board_metricas.py tasks/todo.md`
- Suggested commit message:
  - `fix(consolidation): recover start date from earliest workflow stage when In Progress is missing`

## Current Task (Recuperar data de criação para itens sem base LT)
- [x] Verificar presença de `S1NC-1885` e disponibilidade de data de criação no consolidado/downstream atual
- [x] Ajustar exportador Jira downstream para incluir coluna `Created`
- [x] Ajustar consolidação (`dash_board_metricas.py`) para preencher `DataCriacaoID` a partir de `Created`
- [x] Validar sintaxe e registrar necessidade de reprocessamento dos CSVs para efeito nos dados atuais

## Review (Recuperar data de criação para itens sem base LT)
- What was validated:
  - `S1NC-1885` existe no consolidado e no downstream, mas atualmente sem data de criação nos dados carregados.
  - O exportador `jira_to_pipeline_csv.py` já consultava o campo Jira `created`, porém não escrevia no CSV; isso foi corrigido com a nova coluna `Created`.
  - A consolidação `dash_board_metricas.py` passou a preencher `DataCriacaoID` com `Created` parseado para datetime.
  - Com essa mudança, o fallback de Lead Time por criação ficará disponível após regerar downstream + consolidado.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('jira_to_pipeline_csv.py').read_text(encoding='utf-8')); ast.parse(pathlib.Path('dash_board_metricas.py').read_text(encoding='utf-8')); print('ok')"`
  - `git diff -- jira_to_pipeline_csv.py dash_board_metricas.py tasks/todo.md`
- Suggested commit message:
  - `feat(data-pipeline): export created date and populate DataCriacaoID for lead-time fallback`

## Current Task (Lead Time: fallback por criação/primeira movimentação)
- [x] Implementar fallback em cadeia para `LeadStart_Selected` (início) com múltiplas fontes de data
- [x] Recalcular `LeadTime_Selected_Dias` quando houver `DataDone` e início resolvido via fallback
- [x] Expor no subtítulo da aba `Lead Time` a quantidade de itens cobertos por fallback
- [x] Validar sintaxe e medir impacto no recorte de fevereiro/2026

## Review (Lead Time: fallback por criação/primeira movimentação)
- What was validated:
  - Foi adicionada resolução flexível de data (`_coerce_datetime_flexible`) com suporte a formatos mistos, inclusive IDs no padrão `YYYYMMDD`.
  - Foi implementada cadeia de fallback de início (`_resolve_lead_start_series`) priorizando etapas selecionadas e, na ausência, campos como `DataInProgress`, `DataBacklog`, criação e primeira movimentação (quando presentes).
  - `apply_selected_lead_time_metric(...)` agora preenche `LeadTime_Selected_Dias` faltante via `DataDone - LeadStart_Selected` (somente valores `>= 0`) e contabiliza `fallback_sample`.
  - No recorte informado, o fallback recuperou 2 itens na amostra de LT (`239 -> 241`); ainda restam itens sem base por ausência real de data de início/criação na fonte consolidada.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('dashboard_full.py ok')"`
  - `python -c "import pandas as pd, dashboard_full as d; ...; print({'delivered':..., 'leadtime_sample':..., 'diff':..., 'fallback_sample':...})"`
    Resultado: `{'delivered': 325, 'leadtime_sample': 241, 'diff': 84, 'fallback_sample': 2}`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(lead-time): add start-date fallback chain and backfill lead-time when done date is available`

## Current Task (Segunda rodada: aderência Lead Time vs Estatística)
- [x] Centralizar o cálculo-base de Lead Time em helper compartilhado entre as abas
- [x] Aplicar a mesma base de cálculo em `tab-lead-time` e `tab-estatistica`
- [x] Expor resumo comparável (Amostra, Média, P50, P85) nas duas abas para validação visual
- [x] Validar sintaxe e validar igualdade numérica no mesmo recorte

## Review (Segunda rodada: aderência Lead Time vs Estatística)
- What was validated:
  - Foi criado o helper `build_lead_time_comparable_scope(...)`, que padroniza elegibilidade, limpeza e estatísticas de Lead Time.
  - A aba `Lead Time` passou a usar esse helper como fonte única para os números-base.
  - A aba `Estatística Descritiva` passou a usar o mesmo helper para tabela e gráficos de Lead Time.
  - As duas abas agora exibem e usam a mesma base comparável (`Amostra`, `Média`, `P50`, `P85`), reduzindo risco de divergência.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `python - <<'PY' ... lead_time_tab {'count': 183, 'mean': 13.3224..., 'p50': 10.0, 'p85': 24.0} ... estatistica_tab {'count': 183, 'mean': 13.3224..., 'p50': 10.0, 'p85': 24.0} ... match_* True ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(lead-time): unify comparable lead-time stats across Lead Time and Estatística tabs`

## Current Task (Lead Time: explicar diferença entre finalizados e amostra válida)
- [x] Verificar por que `LT válido` não igualava `Throughput` no recorte de fevereiro/2026
- [x] Identificar itens finalizados sem base de cálculo de lead time
- [x] Ajustar subtítulo da aba `Lead Time` para explicitar `Finalizados`, `LT válido` e `Sem base LT`
- [x] Validar sintaxe e conferência numérica por projeto

## Review (Lead Time: explicar diferença entre finalizados e amostra válida)
- What was validated:
  - Diferença confirmada no recorte (`2026-02-01` a `2026-02-28`, todos): `Finalizados=325`, `LT válido=239`, `Sem base LT=86`.
  - Causa raiz dos 86: itens com `DataDone` preenchido, porém sem datas de início (`DataBacklog`/`DataInProgress`) e sem `LeadTime_Dias`, inviabilizando cálculo de LT.
  - A UI da aba `Lead Time` foi ajustada para expor explicitamente essa decomposição e evitar leitura de inconsistência de contagem.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('dashboard_full.py ok')"`
  - `python -c "import pandas as pd, dashboard_full as d; ...; print({'finalizados':..., 'lt_valido':..., 'sem_base_lt':...}); print(missing_by_project)"`
    Resultado: `{'finalizados': 325, 'lt_valido': 239, 'sem_base_lt': 86}` e `{'DATA&ANALYTICS': 49, 'S1NC': 18, 'BEFINANCE': 14, 'W1NNER': 5}`.
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(lead-time): show finalized vs valid lead-time sample and missing-base count`

## Current Task (CFD: alinhar visual/comportamento com produção)
- [x] Diagnosticar divergências do CFD atual vs produção (granularidade temporal, forma da curva e linhas de tendência)
- [x] Ajustar snapshots do CFD para base diária no recorte selecionado
- [x] Ajustar traços para formato em degraus e incluir linhas-guia de taxa (`items/day`) no modo detalhado
- [x] Validar sintaxe e revisar diff da alteração

## Review (CFD: alinhar visual/comportamento com produção)
- What was validated:
  - O CFD passou a usar snapshots diários (`freq='D'`) no recorte selecionado, removendo o efeito de linhas semanais triangulares.
  - As bandas do CFD (macro e detalhado) passaram a ser renderizadas em degraus (`line.shape='hv'`), alinhando a leitura visual com a referência de produção.
  - No modo detalhado, foram adicionadas duas linhas-guia de taxa (Triagem e Itens concluídos), com anotações em `items/day`.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(cfd): align chart with production using daily snapshots, step rendering, and rate guide lines`

## Current Task (Consistência de contagem: Entregues x Lead Time x Throughput)
- [x] Rastrear a origem dos números divergentes nas abas `Performance`, `Lead Time` e `Throughput`
- [x] Padronizar base de itens entregues no período (itens elegíveis e deduplicados por item/projeto)
- [x] Aplicar base padronizada no card `Entregues` e no KPI `Throughput Total`
- [x] Ajustar subtítulo de `Lead Time` para explicitar amostra válida sobre total de entregues
- [x] Validar sintaxe e executar conferência numérica no recorte reportado

## Review (Consistência de contagem: Entregues x Lead Time x Throughput)
- What was validated:
  - Causa raiz confirmada: cada aba usava critérios diferentes (linhas vs itens deduplicados, elegibilidade de concluído e amostra de lead time).
  - Foi criada a base única `build_delivered_items_base(...)` para contar entregues com regra consistente:
    - concluídos no recorte ativo,
    - elegíveis (`done_time_eligible_mask`),
    - deduplicados por `Projeto + ItemID` (ou `ItemID`).
  - `Entregues` (Performance) e `Throughput Total` passaram a usar exatamente essa mesma base.
  - `Lead Time` mantém a amostra válida de lead time, mas agora exibe claramente `Amostra Lead Time: X de Y entregues`.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('dashboard_full.py ok')"`
  - `python -c "import pandas as pd, dashboard_full as d; ...; print({'delivered':..., 'throughput_total':..., 'leadtime_sample':...})"`
    Resultado no recorte informado (2026-02-01 a 2026-02-28, Todos): `{'delivered': 325, 'throughput_total': 325, 'leadtime_sample': 239}`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(metrics): unify delivered and throughput counts and clarify lead-time sample base`

## Current Task (Estatística Descritiva: corrigir números com "Todos os projetos")
- [x] Diagnosticar divergência da aba `tab-estatistica` no cenário `Projeto = Todos os projetos`
- [x] Unificar base de dados da aba para aplicar mesmos filtros ativos antes dos cálculos por métrica
- [x] Validar sintaxe e checagem numérica de amostra agregada

## Review (Estatística Descritiva: corrigir números com "Todos os projetos")
- What was validated:
  - A aba `tab-estatistica` passou a calcular os concluídos do período (`df_done`) a partir da mesma base filtrada da própria aba (`df_base`), em vez de misturar bases distintas.
  - O ajuste elimina divergência potencial entre tabela e gráficos no cenário `Todos os projetos`, mantendo consistência com os filtros ativos (`Projeto`, `Tipo`, `Classe Serviço`, `Responsável`).
  - A lógica de Lead Time selecionado por etapas (`LeadTime_Selected_Dias`) foi preservada.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `python - <<'PY' ... done 324 lt 183 mean 13.32 p85 24.0 ... projects in sample ['BEFINANCE', 'DATA&ANALYTICS', 'S1NC', 'W1NNER'] ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(estatistica): align descriptive stats datasets when all-projects filter is selected`

## Current Task (Padrões Sistêmicos: filtro "Todos os projetos" com dados incorretos)
- [x] Diagnosticar a causa raiz da divergência na aba `Padrões Sistêmicos` quando `Projeto = Todos os projetos`
- [x] Ajustar o cálculo para detectar padrões por projeto/semana no escopo filtrado
- [x] Manter compatibilidade para filtro de projeto específico e expor `Projeto` no detalhamento
- [x] Validar sintaxe e revisar o diff

## Review (Padrões Sistêmicos: filtro "Todos os projetos" com dados incorretos)
- What was validated:
  - Causa raiz confirmada: `detect_systemic_patterns(...)` agregava todos os projetos em um único bloco semanal, distorcendo sinais quando o filtro estava em `Todos os projetos`.
  - A detecção passou a iterar por projeto (`groupby('Projeto')`) e calcular sinais por `projeto + semana`, mantendo o mesmo motor de regras.
  - O detalhamento agora inclui a coluna `Projeto`, melhorando rastreabilidade dos sinais na tabela da aba.
  - O comportamento para projeto específico foi preservado (continua retornando um único grupo de projeto).
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(patterns): detect systemic signals per project when all-projects filter is selected`

## Current Task (One Page Completo: legenda com quantidade por situação)
- [x] Localizar a montagem da legenda da Parte 3 na aba `One Page Completo`
- [x] Incluir contagem de épicos por status nos chips da legenda (`Running/Planning/Done/Paused`)
- [x] Validar sintaxe e revisar diff do `dashboard_full.py`

## Review (One Page Completo: legenda com quantidade por situação)
- What was validated:
  - A legenda da visão `One Page Completo - Roadmap 2026` agora exibe contagem por status no formato `Status (n)`.
  - O cálculo das contagens usa o dataframe já filtrado da própria visão (`df['RoadmapStatus']`), mantendo consistência com os épicos exibidos.
  - O escopo foi mantido apenas na função `render_portfolio_roadmap_full_epics_view`, sem alterar outras abas.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py`
  - `git status --short`
- Suggested commit message:
  - `feat(portfolio-one-page): show epic counts in status legend chips`

## Current Task (Filtro de projeto: opção global "Todos os projetos")
- [x] Identificar ponto de montagem do dropdown `filter-projeto` no `dashboard_full.py`
- [x] Incluir opção explícita "Todos os projetos" no filtro e normalizar valor sentinela para escopo global
- [x] Validar sintaxe e registrar review com evidências

## Review (Filtro de projeto: opção global "Todos os projetos")
- What was validated:
  - O dropdown `Projeto` agora inclui a opção explícita `Todos os projetos` no topo e inicia com ela selecionada.
  - Foi adicionada normalização do valor sentinela (`__ALL_PROJECTS__ -> None`) para que a lógica existente de escopo global seja reaproveitada sem regressão.
  - A normalização foi aplicada nos pontos críticos de callback (`update_leadtime_stage_filter_options` e `render_tab`) para evitar filtros indevidos por string sentinela.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(filters): add explicit all-projects option and map sentinel to global scope`

## Current Task (Portfólio: filtro Classe Serviço/Prioridade não filtrando épicos)
- [x] Diagnosticar por que o filtro de prioridade não afetava o módulo de portfólio
- [x] Aplicar filtro `classe_servico` no dataset de portfólio antes de recomputar snapshot
- [x] Corrigir seleção de arquivo para priorizar `portfolio-bt-ns-latest-data.csv`
- [x] Validar presença de `Prioridade` e contagem de `Highest` no snapshot carregado

## Review (Portfólio: filtro Classe Serviço/Prioridade não filtrando épicos)
- What was validated:
  - Causa raiz 1: o branch de Portfólio não aplicava o filtro `classe_servico` ao `df_portfolio_filtered`.
  - Causa raiz 2: o loader escolhia `portfolio-bt-ns-YYYYMMDD-data.csv` por `ctime`, ignorando o alias `latest` que já tinha `Prioridade`.
  - O filtro agora é aplicado ao dataset de portfólio via `ClasseServico <- resolve_service_class('', Prioridade)`.
  - A seleção do arquivo de portfólio agora prioriza explicitamente `portfolio-bt-ns-latest-data.csv`.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `selected ...\\dados\\latest\\portfolio-bt-ns-latest-data.csv`
  - `Prioridade: Medium 179 | Highest 25 | High 4`
  - `highest rows 25` após mapeamento de `ClasseServico`
- Suggested commit message:
  - `fix(portfolio): apply classe_servico filter to portfolio snapshot and prefer latest alias csv`

## Current Task (Dataset portfólio: Prioridade não preenchida)
- [x] Diagnosticar por que a coluna `Prioridade` veio vazia no `portfolio-bt-ns-latest-data.csv`
- [x] Corrigir exportador para solicitar campo Jira `priority`
- [x] Regerar CSV latest e validar distribuição de prioridades

## Review (Dataset portfólio: Prioridade não preenchida)
- What was validated:
  - Causa raiz confirmada: `jira_portfolio_to_csv.py` montava a coluna `Prioridade`, mas a lista `fields` da busca Jira não incluía `priority`.
  - Ajuste aplicado em `fields` para incluir `priority`.
  - Após regeneração do latest, a coluna passou a vir preenchida (`Medium`, `Highest`, `High`), com 25 itens `Highest`.
- Evidence (tests/logs/diff):
  - `python -m py_compile jira_portfolio_to_csv.py`
  - `python jira_portfolio_to_csv.py --projects BT NS --out ...\\portfolio-bt-ns-latest-data.csv`
  - `python -c "... value_counts Prioridade ... highest_like ..."` (resultado: `Highest 25`)
- Suggested commit message:
  - `fix(portfolio-export): request jira priority field so Prioridade is populated in latest csv`

## Current Task (One page: estrela Highest não aparecendo)
- [x] Diagnosticar por que a estrela não aparecia no one page completo
- [x] Adicionar fallback manual por env (`FLOW_PMO_PORTFOLIO_HIGHEST_IDS` e `FLOW_PMO_PORTFOLIO_HIGHEST_TITLES`)
- [x] Incluir `Prioridade` no exportador `jira_portfolio_to_csv.py` para suporte nativo em novas extrações
- [x] Validar sintaxe e renderização com caso de teste

## Review (One page: estrela Highest não aparecendo)
- What was validated:
  - A ausência de estrela no cenário atual foi causada por falta de `Prioridade` no CSV de portfólio atual e ausência de match de IDs com o downstream.
  - O dashboard agora aceita marcação de estrela por lista manual de IDs/títulos via env.
  - O exportador de portfólio passou a incluir a coluna `Prioridade`, permitindo marcação automática em próximas gerações de CSV.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py jira_portfolio_to_csv.py`
  - `python -c "import dashboard_full as d; ...; print('star', '★' in str(node))"` com título manual (resultado `star True`)
- Suggested commit message:
  - `fix(portfolio-roadmap): enable highest-star fallback via env and export priority in portfolio csv`

## Current Task (Portfólio one page: estrela para itens Highest/Higest)
- [x] Adicionar ícone de estrela nos épicos marcados como `Highest/Higest` na aba `One Page Completo`
- [x] Implementar detecção por prioridade no próprio dataset e fallback por IDs de alta prioridade
- [x] Validar sintaxe e renderização

## Review (Portfólio one page: estrela para itens Highest/Higest)
- What was validated:
  - A renderização da linha do épico agora suporta ícone `★` em círculo para itens de prioridade máxima.
  - A detecção considera variações `Highest` e `Higest`.
  - O código permite marcar prioridade alta por coluna `Prioridade` no dataset e por IDs enriquecidos.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `python -c "import dashboard_full as d; ...; print('has_star', '★' in str(node))"`
- Suggested commit message:
  - `feat(portfolio-roadmap): show star icon on highest-priority epics in one-page complete tab`

## Current Task (Portfólio one page completo: separar Running de Planning)
- [x] Corrigir distribuição visual para não misturar itens `Running` com `Planning`
- [x] Ordenar itens `Running` por `% de avanço` dentro de cada quarter
- [x] Validar renderização e sintaxe

## Review (Portfólio one page completo: separar Running de Planning)
- What was validated:
  - A lista de épicos em cada quarter passou a ser segmentada por status (`Running`, `Planning`, `Done`, `Paused`) com cabeçalho por bloco.
  - Os itens `Running` agora aparecem agrupados no topo e ordenados por `% de avanço`.
  - A segunda linha de avanço permanece visível apenas para `Running`.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `python -c "import dashboard_full as d; ...; print('ok', 'Running (' in txt and 'Planning (' in txt)"`
- Suggested commit message:
  - `fix(portfolio-roadmap): separate running and planning blocks and sort running by progress percent`

## Current Task (Portfólio: nova aba one page completo com épicos e % de avanço)
- [x] Criar nova aba temática no Portfólio para exibir o one page completo com nomes dos épicos
- [x] Implementar layout por quarter (Q1..Q4) com lista de épicos e cores pela legenda (`Running`, `Planning`, `Done`, `Paused`)
- [x] Adicionar segunda linha para itens `Running` com `% de avanço` calculado pelo status/coluna de fluxo
- [x] Validar sintaxe e renderização da nova aba

## Review (Portfólio: nova aba one page completo com épicos e % de avanço)
- What was validated:
  - Foi adicionada a aba `One Page Completo` dentro das tabs do módulo Portfólio.
  - A aba usa apenas épicos (`TipoNorm in {epico, epic}`) e distribui por quarter via `DueDate`.
  - Cada épico agora é exibido pelo nome; para itens `Running`, há segunda linha com `% de avanço` e barra visual.
  - O `% de avanço` considera `%` explícito no status e fallback por etapa de fluxo (ex.: `ready for development`, `in progress`, `testing`, `staging`, `ready to delivery`, `done`).
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `python -c "import dashboard_full as d; ...; print('tab_token', 'portfolio-one-page-completo' in str(...))"`
  - Validação de amostra no CSV latest:
    - `Running`: `0%`, `20%`, `80%` com `RoadmapProgressPct` coerente
- Suggested commit message:
  - `feat(portfolio-roadmap): add complete one-page epic view tab with running progress percentage line`

## Current Task (Portfólio roadmap: consistência de Q3/Q4 com DueDate)
- [x] Diagnosticar por que Q3/Q4 exibiam vazio mesmo com `DueDate` preenchido no CSV latest
- [x] Ajustar mapeamento de status para incluir `Triagem/Backlog` como `Planning` no one page roadmap
- [x] Validar distribuição por quarter no arquivo `portfolio-bt-ns-latest-data.csv`

## Review (Portfólio roadmap: consistência de Q3/Q4 com DueDate)
- What was validated:
  - Causa raiz confirmada: itens de Q3/Q4 estavam com status `Triagem` e eram descartados pelo mapeamento estrito anterior.
  - O mapeamento de `Planning` foi ampliado para incluir `Triagem`, `Backlog`, `To Do/Todo`, `Business Review`, `Ready for Development` e `Ready to Start`.
  - A mensagem de vazio foi ajustada para refletir ausência de status mapeado (não ausência de `DueDate`).
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - Validação no CSV latest:
    - `Q1 45 {'Planning': 41, 'Done': 2, 'Running': 2}`
    - `Q2 44 {'Planning': 43, 'Running': 1}`
    - `Q3 27 {'Planning': 27}`
    - `Q4 25 {'Planning': 25}`
- Suggested commit message:
  - `fix(portfolio-roadmap): map triagem/backlog to planning so Q3/Q4 due-date items are shown`

## Current Task (Portfólio: visão roadmap por quarter com legenda de status)
- [x] Definir mapeamento de status para `Planning`, `Running`, `Done` e `Paused` conforme regra solicitada
- [x] Implementar componente visual `One Page - Roadmap 2026` com `Q1..Q4` na aba de Portfólio
- [x] Exibir legenda com contagem por status e cards de projetos por quarter
- [x] Validar sintaxe e execução do novo bloco

## Specification (Portfólio: visão roadmap por quarter com legenda de status)
- Objetivo: adicionar no `dashboard_full.py` uma visão de portfólio por quarter com cores/legenda no padrão solicitado.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - A aba de Portfólio passa a exibir uma seção visual `One Page - Roadmap 2026` com trilha `Q1..Q4`.
  - Regras de status aplicadas:
    - `Planning`: itens em `planning/pllaning` (com fallback para categoria `Backlog`).
    - `Running`: itens `ready to delivery` e status percentuais até `80%` (com fallback para `Em progresso`).
    - `Done`: itens `done/concluído/closed/resolved`.
    - `Paused`: itens com sinalização `blocked/suspend/paused` (prioridade sobre os demais).
  - Legenda exibe contagem por status no recorte ativo.

## Review (Portfólio: visão roadmap por quarter com legenda de status)
- What was validated:
  - Foi criada a nova seção `One Page - Roadmap 2026` dentro do `Resumo Executivo` do portfólio.
  - A nova função aplica o mapeamento de status com prioridade explícita para `Paused`.
  - A visualização mostra `Q1..Q4`, legenda com contagens por status e lista de projetos por quarter com chips coloridos.
  - A base `items_base` passou a carregar `DueDate` quando disponível para classificação de quarter.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `python -c "import dashboard_full as d; s,df,err=d.get_portfolio_snapshot(); ...; node=d.render_portfolio_roadmap_quarter_view(...); print(type(node).__name__)"`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `feat(portfolio): add one-page roadmap by quarter with planning/running/done/paused legend`

## Current Task (Deploy: opcao --force)
- [x] Adicionar argumento `--force` no `deploy.py`
- [x] Encaminhar `--force` para o comando `vercel deploy`
- [x] Validar help/sintaxe

## Review (Deploy: opcao --force)
- What was validated:
  - `deploy.py` agora aceita a flag `--force`.
  - Quando informada, a flag e propagada para `vercel deploy --force`.
- Evidence (tests/logs/diff):
  - `python -m py_compile deploy.py`
  - `python deploy.py --help`
- Suggested commit message:
  - `feat(deploy): add --force option to vercel deploy command`

## Current Task (Deploy: parser tolerante para URL map downstream)
- [x] Diagnosticar motivo da indisponibilidade do modo detalhado apos deploy
- [x] Tornar `_load_downstream_url_map()` tolerante a env JSON malformada
- [x] Validar sintaxe do arquivo alterado

## Specification (Deploy: parser tolerante para URL map downstream)
- Objetivo: impedir falso negativo de "CSV downstream não encontrado" quando `FLOW_PMO_DOWNSTREAM_CSV_URL_MAP` estiver com aspas extras/formato imperfeito.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Criterio de aceite:
  - `FLOW_PMO_DOWNSTREAM_CSV_URL_MAP` continua funcionando em JSON valido.
  - Valor com aspas externas extras tambem e aceito.
  - Em falha de `json.loads`, parser tenta recuperar pares `projeto:url` antes de desistir.

## Review (Deploy: parser tolerante para URL map downstream)
- What was validated:
  - `_load_downstream_url_map()` agora tenta multiplas normalizacoes do raw env antes de desistir.
  - Foi adicionado fallback por regex para recuperar pares `projeto:url` em cenarios malformados.
  - O fluxo de fallback evita retornar `{}` em casos recuperaveis, reduzindo erro de indisponibilidade do modo detalhado.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py`
- Suggested commit message:
  - `fix(cfd): make downstream URL map parsing tolerant to malformed env JSON`

## Current Task (Process Mining: comprometido em horas úteis 8h/dia + cartões únicos)
- [x] Ajustar o gráfico de trabalho comprometido para exibir explicitamente horas úteis normalizadas com teto de 8h/dia
- [x] Adicionar versão do gráfico por quantidade de cartões únicos por pessoa e área
- [x] Atualizar tabela de detalhe para incluir horas úteis e cartões únicos por status
- [x] Validar sintaxe/import e registrar evidências

## Specification (Process Mining: comprometido em horas úteis 8h/dia + cartões únicos)
- Objetivo: evoluir o gráfico de trabalho comprometido por pessoa/área para mostrar a métrica em horas úteis limitadas a 8h/dia e disponibilizar também a leitura por cartões únicos.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O gráfico de horas mostra explicitamente que usa horas úteis normalizadas com teto de 8h por pessoa/dia.
  - Existe um segundo gráfico empilhado por pessoa/área mostrando `cartões únicos`.
  - A tabela de detalhe inclui colunas de horas úteis e cartões únicos por `Responsavel + AreaFluxo + Status`.

## Review (Process Mining: comprometido em horas úteis 8h/dia + cartões únicos)
- What was validated:
  - O gráfico de trabalho comprometido foi ajustado para usar e rotular explicitamente `HorasUteisComprometidas8hDia` (derivada de `HorasUteisNormalizadas`).
  - Foi criado um novo gráfico empilhado por pessoa/área para `CartoesUnicos`.
  - O hover dos dois gráficos passou a mostrar detalhamento por status com horas e quantidade de cards.
  - A tabela de auditoria foi atualizada com `HorasUteisComprometidas8hDia` e `CartoesUnicos`.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_process_mining.py`
  - `python -c "import dashboard_process_mining; print('import ok')"`
  - `git diff -- dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): show committed work in normalized 8h/day useful hours and unique cards view`

## Current Task (Process Mining: trabalho comprometido por pessoa e por área do fluxo)
- [x] Definir mapeamento de status para áreas do fluxo (AREA DEV, AREA QA, Staging)
- [x] Implementar agregação de horas comprometidas por `Responsavel + Area + Status` com base em horas úteis normalizadas
- [x] Adicionar gráfico empilhado por pessoa com cores por área e detalhe de status no hover
- [x] Adicionar tabela de auditoria por pessoa/área/status
- [x] Validar sintaxe/import e registrar review com evidências

## Specification (Process Mining: trabalho comprometido por pessoa e por área do fluxo)
- Objetivo: exibir na aba operacional do dashboard de Process Mining um gráfico de trabalho comprometido por pessoa, segmentado por área do fluxo solicitada pelo usuário.
- Escopo:
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O mapeamento de área considera: `AREA DEV` (`In progress`, `Ready for code review`, `code review`), `AREA QA` (`ready for testing`, `testing/qa`) e `Staging` (`ready for staging`, `staging`, `ready for production`).
  - O gráfico apresenta barras empilhadas horizontais por pessoa com horas comprometidas por área.
  - O dashboard inclui tabela de suporte com o detalhamento `Responsavel + AreaFluxo + Status + HorasComprometidas`.

## Review (Process Mining: trabalho comprometido por pessoa e por área do fluxo)
- What was validated:
  - Foi implementado o mapeamento explícito de status para áreas (`COMMITTED_WORK_AREA_RULES`) com cores dedicadas por área.
  - O cálculo de trabalho comprometido usa `HorasUteisNormalizadas` já existente no fluxo operacional para evitar superestimação por concorrência.
  - Foi adicionado novo gráfico empilhado `Trabalho Comprometido por Pessoa e Área do Fluxo (DEV, QA, Staging)` com hover detalhado por status.
  - Foi adicionada tabela de auditoria `Detalhe do Trabalho Comprometido por Pessoa, Área e Status`.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_process_mining.py`
  - `python -c "import dashboard_process_mining; print('import ok')"`
  - `git diff -- dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): add committed work by person chart split by DEV/QA/Staging areas`

## Current Task (Deploy completo: script Python unico)
- [x] Consolidar o fluxo em um unico script Python `deploy.py`
- [x] Implementar tratamento de ambiente e excecoes por etapa (`whoami`, `link`, `pull`, `deploy`)
- [x] Remover wrappers extras para manter apenas o fluxo Python
- [x] Validar help/sintaxe e registrar review com evidencias

## Specification (Deploy completo: script Python unico)
- Objetivo: disponibilizar um unico script Python para deploy completo na Vercel, com tratamento cross-platform e mensagens claras de falha por etapa.
- Escopo:
  - `deploy.py`
  - `tasks/todo.md`
- Criterio de aceite:
  - Existe apenas um fluxo principal em Python para deploy (`deploy.py`).
  - O script trata Windows/macOS sem wrappers dedicados.
  - O deploy completo inclui prechecks, autenticacao, link opcional do projeto, pull de ambiente e deploy.
  - Erros em qualquer etapa retornam mensagem objetiva de diagnostico.

## Review (Deploy completo: script Python unico)
- What was validated:
  - O fluxo de deploy foi consolidado em `deploy.py` com etapas explicitas: `whoami`, `link`, `pull` e `deploy`.
  - O script detecta ambiente, carrega `.env.local`/`.env`, resolve CLI local/global e trata fallback de token (`VERCEL_OIDC_TOKEN` -> `VERCEL_TOKEN`).
  - O tratamento de excecoes agora retorna erro por etapa com diagnostico objetivo.
  - Wrappers (`deploy.ps1` e `deploy.sh`) foram removidos para manter single-entrypoint em Python.
- Evidence (tests/logs/diff):
  - `python -m py_compile deploy.py`
  - `python deploy.py --help`
  - `git status --short`
- Suggested commit message:
  - `feat(deploy): replace wrappers with single complete python deploy script`

## Current Task (Deploy Python: fallback local da Vercel CLI no Windows)
- [x] Diagnosticar erro de autenticacao em `whoami` quando script cai para `npx vercel`
- [x] Ajustar resolucao da CLI para usar `node node_modules/vercel/dist/index.js` quando `node_modules/.bin/vercel.cmd` nao existir
- [x] Validar sintaxe e resolucao de comando no ambiente local

## Specification (Deploy Python: fallback local da Vercel CLI no Windows)
- Objetivo: impedir falha de `whoami` em ambientes onde a instalacao local do pacote `vercel` nao cria `node_modules/.bin/vercel.cmd`.
- Escopo:
  - `deploy.py`
  - `tasks/todo.md`
- Criterio de aceite:
  - `resolve_vercel_bin` retorna CLI local funcional sem depender de `npx` quando `node_modules/vercel/dist/index.js` existir.
  - O comando resolvido no Windows passa a ser `node .../node_modules/vercel/dist/index.js`.
  - O script continua com fallback para `vercel` global e `npx` como ultima opcao.

## Review (Deploy Python: fallback local da Vercel CLI no Windows)
- What was validated:
  - O script agora detecta `node_modules/vercel/dist/index.js` e executa a CLI via `node`, cobrindo o cenário sem `.bin/vercel.cmd`.
  - O fallback `npx` foi mantido como ultima alternativa, com `--yes`.
  - A validacao local mostrou que o resolvedor nao aponta mais para `npx vercel` nesse repositório.
- Evidence (tests/logs/diff):
  - `python -m py_compile deploy.py`
  - `python deploy.py preview --yes --dry-run`
  - `python -c "import deploy; from pathlib import Path; print(' '.join(deploy.resolve_vercel_bin(Path('.').resolve())))"`
- Suggested commit message:
  - `fix(deploy): use local vercel dist cli via node when .bin wrapper is missing`

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
- [x] Ajustar estilos dos botões `Portfólio` e `Serviços (Value Stream)` para centralização e tamanho maior
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
  - Botões `Portfólio` e `Serviços (Value Stream)` ficaram maiores (`height`, `minWidth`, `fontSize`) e com centralização explícita via `display:flex`, `alignItems:center`, `justifyContent:center`.
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

## Current Task (Tela Principal com Menu Portfólio/Serviços)
- [x] Definir especificação e plano da navegação principal
- [x] Implementar tela principal com 2 botões (`Portfólio` e `Serviços (Value Stream)`)
- [x] Separar acesso ao `Portfólio` das demais abas (Value Stream)
- [x] Validar sintaxe e revisar diff

## Specification (Tela Principal com Menu Portfólio/Serviços)
- Objetivo: criar uma tela principal que funcione como menu de entrada, com dois botões para abrir `Portfólio` ou `Serviços (Value Stream)`.
- Escopo:
  - `dashboard_full.py` (layout e callbacks de navegação).
- Restrições:
  - Manter o conteúdo atual das abas sem refatoração ampla.
  - `Portfólio` deve ficar acessível separado das demais abas de serviço.
- Critério de aceite:
  - Tela inicial aparece com 2 botões.
  - Botão `Portfólio` abre somente a visão de portfólio.
  - Botão `Serviços (Value Stream)` abre o conjunto das abas operacionais.
  - Usuário consegue voltar ao menu principal.

## Review (Tela Principal com Menu Portfólio/Serviços)
- What was validated:
  - Dashboard passa a abrir em uma tela principal com os botões `Portfólio` e `Serviços (Value Stream)`.
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

## Current Task (Centralizar publicação de todos os arquivos latest em Dados/latest)
- [x] Rastrear scripts e módulos que geram artefatos `latest`
- [x] Ajustar orquestradores (`run_all_projects.ps1` e `run_all_projects_macos.sh`) para sincronizar todos os `*latest*` para pasta central
- [x] Ajustar geradores (`dash_board_metricas.py` e `process_mining_jira.py`) para publicar `latest` também na pasta central
- [x] Documentar variável de ambiente `FLOW_PMO_LATEST_DIR` no `.env.example`
- [x] Validar sintaxe dos arquivos alterados

## Specification (Centralizar publicação de todos os arquivos latest em Dados/latest)
- Objetivo: garantir que todos os artefatos com nome `latest` (downstream, bottlenecks, portfolio, PowerBI model, dashboard output e process mining) sejam publicados em `C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest`.
- Escopo:
  - `run_all_projects.ps1`
  - `run_all_projects_macos.sh`
  - `dash_board_metricas.py`
  - `process_mining_jira.py`
  - `.env.example`
- Critério de aceite:
  - Todo arquivo contendo `latest` gerado no `OutDir` do pipeline é replicado para a pasta central de `latest`.
  - `process_mining_jira.py` publica aliases `-latest` também na pasta central.
  - `FLOW_PMO_LATEST_DIR` continua suportado como override explícito.
  - Código válido em sintaxe.

## Current Task (W1NNER ausente no seletor de projeto em produção)
- [x] Diagnosticar por logs e código por que `W1NNER` não entra em `Dim_Projeto`
- [x] Corrigir seleção de CSV `latest` para ignorar artefatos derivados que não são insumo de workflow
- [x] Validar carregamento de 4 projetos e registrar evidências

## Specification (W1NNER ausente no seletor de projeto em produção)
- Objetivo: impedir que arquivos derivados (ex.: `w1nner-process-mining-*.csv`) concorram como dataset principal do projeto na consolidação de métricas.
- Escopo:
  - `dash_board_metricas.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O seletor de latest por projeto não escolhe mais arquivos `process-mining`, `executive_report`, `portfolio` ou `multi-downstream`.
  - O arquivo `w1nner-downstream-<data>-data.csv` volta a ser carregado no consolidado quando existir.
  - A consolidação final volta a ter `Successfully loaded data for 4 projects` no cenário com W1NNER/S1NC/BEFINANCE/DATA&ANALYTICS.

## Review (W1NNER ausente no seletor de projeto em produção)
- What was validated:
  - Causa raiz confirmada: `select_latest_csv_per_project(...)` usava detecção por nome e permitia que `w1nner-process-mining-...-pm4py_tbr_summary.csv` vencesse o `w1nner-downstream-...-data.csv` por ter timestamp mais recente.
  - Foi adicionado filtro explícito de insumo de workflow no seletor, excluindo artefatos derivados (`process-mining`, `executive_report`, `portfolio-bt-ns`, `multi-downstream`, além de `bottleneck`).
  - Na execução de validação, o resumo passou a listar `w1nner-downstream-20260303-data.csv: OK` e `Successfully loaded data for 4 projects`.
- Evidence (tests/logs/diff):
  - `python -m py_compile dash_board_metricas.py`
  - `python -c "import dash_board_metricas"` (execução completa acionada pelo módulo; log confirmou `Selected 4 latest CSV files` e `Successfully loaded data for 4 projects`, incluindo `w1nner-downstream-20260303-data.csv`)
  - `git diff -- dash_board_metricas.py tasks/todo.md`
- Suggested commit message:
  - `fix(metrics): prevent process-mining csv from overriding W1NNER downstream latest selection`

## Current Task (Produção: dados W1NNER zerados com Process Mining atualizado)
- [x] Diagnosticar divergência entre aba de serviço e aba de process mining em produção
- [x] Corrigir cache de downloads remotos para URLs estáveis `*latest*`
- [x] Validar sintaxe e registrar evidências

## Specification (Produção: dados W1NNER zerados com Process Mining atualizado)
- Objetivo: evitar uso indefinido de arquivos antigos em `/tmp` quando as variáveis de ambiente apontam para URLs fixas (`...latest...`) que mudam de conteúdo sem mudar a URL.
- Escopo:
  - `dashboard_full.py`
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Download remoto (`FLOW_PMO_MODEL_URL`, downstream, bottlenecks, portfolio e process mining) respeita TTL de cache e revalida periodicamente.
  - Com URL estável, a aplicação deixa de ficar presa ao primeiro arquivo baixado na instância.
  - TTL configurável via `FLOW_PMO_REMOTE_CACHE_TTL_SECONDS` (default 300s).

## Review (Produção: dados W1NNER zerados com Process Mining atualizado)
- What was validated:
  - Causa provável confirmada no código: os métodos `_download_*_from_url(...)` baixavam apenas quando o arquivo ainda não existia em `/tmp`, mantendo conteúdo potencialmente antigo enquanto a instância estivesse quente.
  - Foi implementado refresh por TTL (`FLOW_PMO_REMOTE_CACHE_TTL_SECONDS`, padrão 300s) com download para arquivo temporário e `os.replace(...)` atômico.
  - Ajuste aplicado em `dashboard_full.py` (modelo, downstream, bottlenecks, portfolio, process mining) e em `dashboard_process_mining.py` (process mining).
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py dashboard_process_mining.py`
  - `git diff -- dashboard_full.py dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `fix(cache): refresh remote latest artifacts with TTL to avoid stale production data`

## Current Task (Process Mining: barras sobrepostas de cards puxados para In Development por faixa de story points)
- [x] Definir extração de eventos de entrada em desenvolvimento por `Issue Key` e pessoa
- [x] Enriquecer eventos com story points via join com downstream `*-latest-data.csv`
- [x] Classificar faixas de story points e senioridade para comparação Senior x Junior
- [x] Implementar gráfico de barras sobrepostas na aba `Process Mining Jira` do `dashboard_full.py`
- [x] Expor tabela de apoio e KPIs de cards/SP puxados para desenvolvimento
- [x] Validar sintaxe e revisar diff final

## Specification (Process Mining: barras sobrepostas de cards puxados para In Development por faixa de story points)
- Objetivo: medir quantos cards foram puxados para `In Development` por pessoa, quebrar por faixas de story points e permitir comparação de volume/complexidade entre perfis de senioridade.
- Escopo:
  - `dashboard_full.py`
  - `.env.example`
  - `tasks/todo.md`
- Critério de aceite:
  - O cálculo usa eventos de changelog (`EventosFiltrados`) para detectar quem puxou o card para desenvolvimento.
  - Story points são adicionados por `Issue Key` a partir do downstream de itens (`load_project_downstream_items_csv('W1NNER')`).
  - Existe gráfico por pessoa com volume de cards puxados quebrado por faixas de story points.
  - Existe apoio em tabela com detalhe por item/pessoa/faixa.
  - Variável opcional de configuração de senioridade está documentada.
  - Código válido em sintaxe.

## Review (Process Mining: barras sobrepostas de cards puxados para In Development por faixa de story points)
- What was validated:
  - Implementada nova base `pm_pull_dev` na aba `tab-process-mining-jira` usando primeiro evento de entrada em desenvolvimento por `Issue Key` (status alvo normalizado: `in progress`, `in development`, `development`, `doing`, `desenvolvimento`).
  - Enriquecimento de complexidade implementado com join em downstream W1NNER por `Issue Key` e fallback `Story point estimate` quando `Story Points` ausente.
  - Adicionadas faixas de story points (`Sem estimativa`, `0`, `1`, `2-3`, `5`, `8`, `13+`) e classificação de senioridade por variável de ambiente `FLOW_PMO_PERSON_SENIORITY_MAP`.
  - Gráfico ajustado para mostrar todas as pessoas com volume de cards puxados quebrado por faixa de story points (barras empilhadas por pessoa).
  - Adicionados KPIs `Cards Puxados p/ Dev` e `SP Puxados p/ Dev` e tabela detalhada dos itens puxados.
  - Documentada variável de ambiente opcional de senioridade em `.env.example`.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py .env.example tasks/todo.md`
- Suggested commit message:
  - `feat(process-mining): add overlay chart of cards pulled to development by story point band and seniority`

## Current Task (Process Mining: garantir aderência total dos gráficos ao filtro de data)
- [x] Diagnosticar por que pessoas sem atividade recente continuavam aparecendo em alguns gráficos
- [x] Recalcular datasets visuais a partir das bases já filtradas por data (`pm_cases` e `pm_events`)
- [x] Ajustar gráficos/tabelas da aba Process Mining para usar os datasets recalculados
- [x] Validar sintaxe e revisar diff

## Specification (Process Mining: garantir aderência total dos gráficos ao filtro de data)
- Objetivo: fazer com que os gráficos da aba `Process Mining Jira` respeitem estritamente o período selecionado nos filtros de data da tela.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
  - `tasks/lessons.md`
- Critério de aceite:
  - Gráficos de vazão por pessoa, vazão semanal, retrabalho, tempos por status e distribuição de variantes usam apenas registros dentro do recorte de data ativo.
  - Indicadores de horas por pessoa/status e DFG também passam a refletir somente eventos filtrados pelo período.
  - Não há dependência de agregados pré-calculados em aba quando estes não respeitarem o filtro atual.
  - Código válido em sintaxe.

## Review (Process Mining: garantir aderência total dos gráficos ao filtro de data)
- What was validated:
  - A causa raiz foi confirmada: parte dos gráficos usava abas agregadas do workbook (`VazaoPessoaResumo`, `VazaoPessoaSemanal`, `TemposPorStatus`, `DFG`) sem recomputar após aplicar filtro de data no dashboard.
  - Foi implementado recálculo em runtime dos datasets de gráficos a partir de `pm_cases` e `pm_events` já filtrados por data/responsável.
  - `pm_people`, `pm_weekly`, `pm_status`, `pm_hours_people`, `pm_hours_status`, `pm_dfg_edges`, `pm_dfg_perf_edges` e `pm_variants` agora são reconstruídos no escopo filtrado antes da montagem dos gráficos.
  - O gráfico de cards puxados por pessoa/faixa continua derivado de `pm_events` filtrado e permanece aderente ao período selecionado.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md tasks/lessons.md`
- Suggested commit message:
  - `fix(process-mining): recompute chart datasets from date-filtered events/cases`

## Current Task (Lead Time: respeitar filtros da tela em "Todos os projetos")
- [x] Diagnosticar por que a aba `Lead Time` perdia amostra quando `Projeto = Todos`
- [x] Ajustar `apply_selected_lead_time_metric(...)` para calcular lead time factual por projeto no escopo filtrado
- [x] Manter fallback por linha para `LeadTime_Dias/DataBacklog` quando não houver downstream do projeto
- [x] Validar sintaxe e revisar diff

## Specification (Lead Time: respeitar filtros da tela em "Todos os projetos")
- Objetivo: garantir que o gráfico da aba `Lead Time` reflita todas as demandas do recorte filtrado na tela quando `Todos os projetos` estiver selecionado.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - Com `Projeto = Todos os projetos`, o cálculo de `LeadTime_Selected_Dias` tenta usar downstream por projeto para os itens no recorte.
  - Quando não houver mapa factual para um item/projeto, o valor cai para fallback do modelo (`LeadTime_Dias`/`DataBacklog`) sem excluir o item por erro de merge.
  - Merge de mapa factual evita colisão de `ItemID` entre projetos distintos.
  - Código válido em sintaxe.

## Review (Lead Time: respeitar filtros da tela em "Todos os projetos")
- What was validated:
  - Causa raiz confirmada no código: `apply_selected_lead_time_metric(...)` fazia fallback imediato para `LeadTime_Dias` quando `projeto` era `None`, reduzindo amostra na aba `Lead Time`.
  - Implementado cálculo factual multi-projeto no mesmo escopo filtrado, iterando projetos presentes em `df` e concatenando mapas de lead time por projeto.
  - Merge ajustado para usar `Projeto + ItemID` quando possível, evitando colisão de IDs iguais entre projetos.
  - `LeadTime_Selected_Dias` e `LeadStart_Selected` agora usam `combine_first(...)`, preservando fallback por item onde não houver dado factual.
  - Metadado `label` foi adicionado no retorno de `leadtime_meta` para refletir origem do cálculo no subtítulo.
- Evidence (tests/logs/diff):
  - `git diff -- dashboard_full.py tasks/todo.md`
  - Validação estática local do trecho alterado em `dashboard_full.py` (sem execução completa do app).
- Suggested commit message:
  - `fix(lead-time): compute selected lead time across all projects and preserve per-item fallback`

## Current Task (Unificar filtro de Projeto entre Serviços e Portfólio)
- [x] Mapear origem dos dois filtros (`filter-projeto` e `filter-portfolio-team`) no `dashboard_full.py`
- [x] Padronizar o filtro de Portfólio para lista de projetos (mesmos nomes do filtro principal)
- [x] Sincronizar seleção do filtro principal de projeto para o filtro de Portfólio
- [x] Aplicar recorte de `Projeto` no dataset de Portfólio usando o mesmo valor efetivo
- [x] Validar sintaxe e revisar diff final

## Specification (Unificar filtro de Projeto entre Serviços e Portfólio)
- Objetivo: fazer com que a seleção de projeto (ex.: `W1NNER`) aplique no módulo de Serviços e no módulo de Portfólio com a mesma nomenclatura.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - O dropdown de Portfólio exibe projetos (não teams), com opção `Todos os projetos`.
  - Ao selecionar um projeto no filtro principal, o filtro de Portfólio reflete a mesma seleção.
  - A aba de Portfólio passa a filtrar por coluna `Projeto` no mesmo valor selecionado.
  - Código válido em sintaxe.

## Review (Unificar filtro de Projeto entre Serviços e Portfólio)
- What was validated:
  - A causa raiz foi confirmada: o filtro secundário de Portfólio usava `Team`, o que criava duas semânticas diferentes para o usuário.
  - O dropdown secundário foi convertido para `Projeto (Portfólio)` com a mesma base de nomes do filtro principal.
  - Foi adicionado callback de sincronização para refletir imediatamente a seleção de `filter-projeto` no filtro de Portfólio.
  - O recorte do dataset de Portfólio passou a aplicar `Projeto` (normalizado) antes da recomputação do snapshot.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(filters): unify project filter between services and portfolio views`

## Current Task (Ocultar campo Projeto (Portfólio) da tela)
- [x] Identificar o bloco de layout do dropdown `Projeto (Portfólio)` no `dashboard_full.py`
- [x] Remover o campo da interface visual mantendo o estado interno/callbacks
- [x] Validar sintaxe e revisar diff final

## Review (Ocultar campo Projeto (Portfólio) da tela)
- What was validated:
  - O campo `Projeto (Portfólio)` foi removido da renderização visual (`display: none`) mantendo o componente para não quebrar callbacks existentes.
  - A sincronização e o filtro unificado por projeto permanecem ativos por trás da tela.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `chore(ui): hide portfolio project filter from dashboard controls`

## Current Task (Produção: CFD detalhado acusando downstream não encontrado após mudanças de filtros)
- [x] Localizar origem da mensagem na aba `CFD` e validar função de carga downstream
- [x] Tornar a detecção de CSV downstream mais tolerante a variações de prefixo/nome em produção
- [x] Validar sintaxe e revisar diff final

## Review (Produção: CFD detalhado acusando downstream não encontrado após mudanças de filtros)
- What was validated:
  - A mensagem vem de `_get_cfd_detailed_unavailable_reason(...)` quando `load_project_downstream_items_csv(...)` retorna vazio.
  - A carga downstream foi reforçada para aceitar múltiplos prefixos candidatos por projeto (`<prefix>-downstream`, `<prefix>` e prefixo bitbucket), reduzindo falso negativo de descoberta de arquivo.
  - Foi adicionado fallback seguro para `FLOW_PMO_DOWNSTREAM_CSV_URL` em ambientes single-project, mesmo quando o nome do arquivo não segue exatamente o prefixo esperado.
  - A seleção de `latest` agora considera múltiplos aliases (`<prefix>-latest-data.csv`) em vez de um único nome rígido.
- Evidence (tests/logs/diff):
  - `python -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(cfd): make downstream csv discovery resilient to project prefix variants in production`

## Current Task (Portfólio: One Page Completo vazio após unificação de filtros)
- [x] Reproduzir o cenário em que a aba Portfólio recebe `projeto` global fora do escopo BT/NS
- [x] Ajustar resolução de projeto efetivo no módulo de Portfólio para priorizar filtro próprio da aba
- [x] Permitir herança do filtro global apenas quando o projeto existir no CSV de Portfólio
- [x] Validar sintaxe e comportamento com `projeto='W1NNER'`

## Review (Portfólio: One Page Completo vazio após unificação de filtros)
- What was validated:
  - Causa raiz confirmada: no Portfólio, o código priorizava `projeto` global (`effective_portfolio_project = projeto or portfolio_project`), o que zerava o dataset quando o projeto global não era BT/NS.
  - Implementado filtro efetivo por escopo: primeiro usa `portfolio_project` (quando válido no CSV de Portfólio) e só usa `projeto` global se ele também existir no escopo de `Projeto` do Portfólio.
  - Com isso, o “One Page Completo - Roadmap 2026” não cai indevidamente em “Sem itens de portfólio...” quando o usuário está com projeto global de Serviços.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('syntax_ok')"`
  - `python -c "import os; os.environ['FLOW_PMO_PORTFOLIO_CSV_FILE']='portfolio-bt-ns-latest-data.csv'; os.environ.pop('FLOW_PMO_PORTFOLIO_CSV_URL', None); import dashboard_full as d; comp=d.render_tab(main_view='portfolio', tab=d.PORTFOLIO_TAB_VALUE, start_date='2026-01-01', end_date='2026-12-31', projeto='W1NNER', tipo=None, classe_servico=None, responsavel=None, leadtime_stages=None, capacity_top_n=5, capacity_weekly_metric='score', portfolio_team=d.PROJECT_FILTER_ALL_VALUE, portfolio_quarter='ALL'); txt=str(comp); print('has_empty_msg', 'Sem itens de portfólio para montar o roadmap completo.' in txt)"`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(portfolio): avoid empty one-page roadmap when global project filter is outside portfolio scope`

## Current Task (Portfólio: One Page esvaziava após filtro global de Classe de Serviço)
- [x] Reproduzir cenário com `classe_servico='Expedite'` na aba Portfólio
- [x] Remover acoplamento do Portfólio ao filtro global de Classe de Serviço
- [x] Validar sintaxe e validar que o One Page não exibe mensagem de vazio indevida

## Review (Portfólio: One Page esvaziava após filtro global de Classe de Serviço)
- What was validated:
  - Causa raiz confirmada: a aba Portfólio aplicava `classe_servico` global no dataframe de portfólio.
  - No CSV atual de portfólio, as classes derivadas são `Medium/Highest/High`; ao selecionar classes do módulo de Serviços (ex.: `Expedite`), o filtro zerava os dados do One Page.
  - O filtro de `Classe de Serviço` foi desacoplado do Portfólio para preservar a taxonomia do módulo.
- Evidence (tests/logs/diff):
  - `python -c "import ast, pathlib; ast.parse(pathlib.Path('dashboard_full.py').read_text(encoding='utf-8')); print('syntax_ok')"`
  - `python -c "import os; os.environ['FLOW_PMO_PORTFOLIO_CSV_FILE']='portfolio-bt-ns-latest-data.csv'; import dashboard_full as d; c=d.render_tab('portfolio',d.PORTFOLIO_TAB_VALUE,'2026-01-01','2026-12-31',None,None,'Expedite',None,None,5,'score',d.PROJECT_FILTER_ALL_VALUE,'ALL'); t=str(c); print('empty_msg', 'Sem itens de portfólio para montar o roadmap completo.' in t)"`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(portfolio): ignore global service-class filter in portfolio one-page roadmap`

## Current Task (Dashboard Full: KeyError no bucket 31-60 na fila de decisão)
- [x] Confirmar a causa raiz do `KeyError: '31-60'` em `render_decision_queue`
- [x] Ajustar a ordenação dos buckets para considerar apenas categorias presentes no recorte
- [x] Validar sintaxe e executar smoke test do gráfico com buckets ausentes
- [x] Registrar review e sugestão de commit

## Review (Dashboard Full: KeyError no bucket 31-60 na fila de decisão)
- What was validated:
  - A causa raiz foi confirmada em `render_decision_queue`: o código fixava a ordem categórica completa (`0-7` a `60+`) mesmo quando o dataframe filtrado não continha todos os buckets.
  - O Plotly Express fazia agrupamento interno por categoria e disparava `KeyError` ao tentar resolver bucket ausente como `31-60`.
  - A função passou a normalizar `AgingBucketDecision`, calcular `present_buckets` na ordem canônica e enviar essa ordem via `category_orders`, sem forçar categorias inexistentes.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `python3 - <<'PY' ... smoke test com df sem bucket 31-60 ... px.bar(..., category_orders={'AgingBucketDecision': ['0-7','8-15']}) ... print('smoke_ok') ... PY`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `fix(dashboard): avoid plotly keyerror when decision-queue aging buckets are missing`

## Review (Corrigir destino `latest` no macOS)
- What was validated:
  - A causa raiz do caminho híbrido foi confirmada em `dash_board_metricas.py`: `FLOW_PMO_LATEST_DIR` era aceito sem validar compatibilidade com o SO atual.
  - `run_all_projects_macos.sh` agora usa como fallback `~/Documents/dados/latest` e descarta override em formato Windows quando executado no macOS.
  - `dash_board_metricas.py` e `process_mining_jira.py` passaram a aplicar a mesma proteção: no macOS, se `FLOW_PMO_LATEST_DIR` vier como `C:\...`, o código ignora esse valor e usa o diretório nativo do Mac.
  - O default do Windows (`C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest`) foi preservado.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dash_board_metricas.py process_mining_jira.py`
  - `bash -n run_all_projects_macos.sh`
  - `/bin/bash -lc 'LATEST_DIR="C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\latest"; if [[ "$LATEST_DIR" =~ ^[A-Za-z]:[\\/].* ]]; then echo "$HOME/Documents/dados/latest"; else echo "$LATEST_DIR"; fi'`
    - Resultado: `/Users/rodrigoalmeidadeoliveira/Documents/dados/latest`
  - `git diff -- dash_board_metricas.py process_mining_jira.py run_all_projects_macos.sh tasks/todo.md tasks/lessons.md`
- Suggested commit message:
  - `fix(latest-paths): ignore windows latest dir overrides on macos and default to Documents/dados/latest`

## Current Task (Deploy Vercel: ignorar `FLOW_PMO_MODEL_FILE` em formato Windows no runtime Linux)
- [x] Confirmar a origem do path absoluto Windows durante o deploy na Vercel
- [x] Sanitizar resolução de `FLOW_PMO_MODEL_FILE` para rejeitar caminho incompatível com o SO atual
- [x] Aplicar a mesma proteção à descoberta de diretórios de dados para evitar falsos candidatos
- [x] Validar com compilação e smoke test simulando env Windows em runtime não-Windows
- [x] Registrar review e sugestão de commit

## Specification (Deploy Vercel: ignorar `FLOW_PMO_MODEL_FILE` em formato Windows no runtime Linux)
- Objetivo: impedir que o deploy/runtime da Vercel falhe quando uma variável de ambiente aponta para um caminho absoluto Windows incompatível com o ambiente Linux do build.
- Escopo:
  - `dashboard_full.py`
  - `dashboard_process_mining.py`
  - `tasks/todo.md`
  - Critério de aceite:
  - Se `FLOW_PMO_MODEL_FILE` estiver em formato `C:\...` e o runtime não for Windows, o app ignora esse override e segue para URL/fallbacks locais compatíveis.
  - Se `FLOW_PMO_DATA_DIR` ou `FLOW_PMO_DATA_DIRS` trouxerem caminhos absolutos de outro SO, eles não entram na lista de candidatos.
  - O comportamento atual em Windows permanece preservado.
  - Código válido em sintaxe.

## Review (Deploy Vercel: ignorar `FLOW_PMO_MODEL_FILE` em formato Windows no runtime Linux)
- What was validated:
  - A causa raiz foi confirmada no entrypoint [`api/index.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/api/index.py): o deploy importa `dashboard_full` no runtime Linux da Vercel, e `_resolve_model_file(...)` falhava ao aceitar `FLOW_PMO_MODEL_FILE=C:\...`.
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora sanitiza paths absolutos incompatíveis com o SO atual antes de considerar `FLOW_PMO_MODEL_FILE`, `FLOW_PMO_DATA_DIR`, `FLOW_PMO_DATA_DIRS` e `DATA_FOLDER`.
  - [`dashboard_process_mining.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_process_mining.py) recebeu a mesma proteção para manter a descoberta de diretórios consistente em runtime não-Windows.
  - Em runtime não-Windows, `C:\Users\W1 TI\...` passa a ser ignorado em vez de virar erro fatal de import/build.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py dashboard_process_mining.py`
  - `python3 - <<'PY' ... exec(prefix de dashboard_full.py) ... _sanitize_os_path('C:\\Users\\W1 TI\\...') -> <ignored> ... _resolve_model_file([]) ... FileNotFoundError sem reutilizar o path Windows ... PY`
  - `git diff -- dashboard_full.py dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `fix(deploy): ignore cross-platform absolute paths in model and data env overrides`

## Current Task (Deploy Vercel: excluir scripts operacionais do bundle Python)
- [x] Confirmar que `FLOW_PMO_MODEL_FILE` não existe nas envs remotas da Vercel
- [x] Restringir o bundle da função Python a arquivos necessários ao runtime do dashboard
- [x] Validar sintaxe do `vercel.json`
- [x] Registrar review e sugestão de commit

## Specification (Deploy Vercel: excluir scripts operacionais do bundle Python)
- Objetivo: evitar que o builder Python da Vercel analise/empacote scripts auxiliares de geração de artefatos, reduzindo falsos positivos de paths absolutos fora do projeto.
- Escopo:
  - `vercel.json`
  - `tasks/todo.md`
- Critério de aceite:
  - `api/index.py` continua como entrypoint único da função Python.
  - Scripts operacionais (`dash_board_metricas.py`, `process_mining_jira.py`, exportadores Jira e CSVs históricos) deixam de entrar no bundle da função.
  - `vercel.json` permanece válido em sintaxe.

## Review (Deploy Vercel: excluir scripts operacionais do bundle Python)
- What was validated:
  - `vercel env ls production` confirmou que o projeto remoto não possui `FLOW_PMO_MODEL_FILE`; a origem do path absoluto não é uma env remota atual.
  - [`vercel.json`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/vercel.json) passou a usar `builds[0].config.excludeFiles` para remover do bundle scripts de geração/importação e CSVs históricos que não participam do runtime servido por [`api/index.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/api/index.py).
  - [`/.vercelignore`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/.vercelignore) passou a excluir do upload artefatos locais, CSVs/XLSX, docs e scripts operacionais; o upload caiu de `32.1MB` para `340B` e o build remoto baixou `21 deployment files` em vez de `237`.
  - Após reduzir o upload ao runtime real do dashboard, o deploy remoto concluiu sem o erro `absolute path: C:/Users/W1 TI/OneDrive - W1/Documentos/Dados/latest/PowerBI_Model_latest.xlsx`.
- Evidence (tests/logs/diff):
  - `./node_modules/.bin/vercel env ls production`
  - `python3 - <<'PY' ... json.loads(Path("vercel.json").read_text()) ... print("vercel_json_ok") ... PY`
  - `python3 deploy.py --no-link --yes`
  - Deploy bem-sucedido:
    - `Production: https://flow-4h1fymfq6-rodrigooliveira-pmos-projects.vercel.app`
    - `Aliased: https://flow-pmo.vercel.app`
  - `git diff -- vercel.json dashboard_full.py dashboard_process_mining.py tasks/todo.md`
- Suggested commit message:
  - `fix(vercel): ignore cross-platform path overrides and exclude local artifacts from deploy bundle`

## Current Task (Diagnosticar por que artefatos latest pararam no run_all_projects)
- [x] Mapear no código a ordem de execução entre exportação Jira, Bitbucket, portfólio e métricas no `run_all_projects_macos.sh`
- [x] Comparar timestamps dos artefatos `latest` gerados em `~/Documents/Dados` e publicados em `~/Documents/dados/latest`
- [x] Identificar o ponto exato onde a execução mais recente interrompeu o pipeline
- [x] Registrar a causa raiz com evidências e sugestão de correção

## Review (Diagnosticar por que artefatos latest pararam no run_all_projects)
- What was validated:
  - [`run_all_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects_macos.sh) executa Bitbucket dentro do loop de projetos e só roda portfólio/métricas depois disso; como o script usa `set -euo pipefail`, qualquer falha nessa etapa aborta o restante.
  - Os quatro artefatos citados continuam existindo tanto em [`/Users/rodrigoalmeidadeoliveira/Documents/Dados`]( /Users/rodrigoalmeidadeoliveira/Documents/Dados) quanto em [`/Users/rodrigoalmeidadeoliveira/Documents/dados/latest`]( /Users/rodrigoalmeidadeoliveira/Documents/dados/latest), mas ficaram parados no timestamp `2026-03-06 08:49`, mostrando que não deixaram de ser gerados historicamente; a execução mais recente apenas não chegou nessa etapa.
  - A evidência de interrupção está em [`/Users/rodrigoalmeidadeoliveira/Documents/Dados/w1nner_pipelines.csv.tmp`](/Users/rodrigoalmeidadeoliveira/Documents/Dados/w1nner_pipelines.csv.tmp), atualizado às `12:04` sem promoção para `w1nner_pipelines.csv`; isso combina com o fluxo de [`bitbucket_export.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/bitbucket_export.py), que grava em `.tmp` e só faz `replace()` no arquivo final se a exportação terminar sem exceção.
  - Conclusão: o `run_all_projects` passou a parar antes de `portfolio` e `dash_board_metricas.py` porque a exportação de pipelines do Bitbucket para `W1NNER` falhou/interrompeu; por isso `dashboard_output_latest.xlsx`, `bottlenecks_consolidado_latest.xlsx`, `PowerBI_Model_latest.xlsx` e `portfolio-bt-ns-latest-data.csv` não foram atualizados após `08:49`.
- Evidence (tests/logs/diff):
  - `rg -n "RUN_BITBUCKET_EXPORT|RUN_PORTFOLIO_EXPORT|RUN_METRICS|set -euo pipefail|publish_latest_artifact|sync_latest_artifacts_from_out_dir" run_all_projects_macos.sh`
  - `find "$HOME/Documents/Dados" -maxdepth 1 -type f \( -name 'dashboard_output_latest.xlsx' -o -name 'bottlenecks_consolidado_latest.xlsx' -o -name 'PowerBI_Model_latest.xlsx' -o -name 'portfolio-bt-ns-latest-data.csv' \) | sort`
  - `find "$HOME/Documents/dados/latest" -maxdepth 1 -type f \( -name 'dashboard_output_latest.xlsx' -o -name 'bottlenecks_consolidado_latest.xlsx' -o -name 'PowerBI_Model_latest.xlsx' -o -name 'portfolio-bt-ns-latest-data.csv' \) | sort`
  - `ls -lt "$HOME/Documents/Dados" | sed -n '1,40p'`
  - `python3 - <<'PY' ... Path.home()/Documents/Dados/w1nner_pipelines.csv.tmp ... print(first_bytes) ... PY`
- Suggested commit message:
  - `fix(run-all): prevent bitbucket pipeline export failures from blocking metrics artifacts`

## Current Task (Permitir que run_all continue após falha no Bitbucket)
- [x] Revisar a orquestração Bitbucket nos scripts macOS e Windows
- [x] Tornar a exportação Bitbucket não bloqueante para preservar portfólio e métricas
- [x] Validar sintaxe/comportamento possível no ambiente atual
- [x] Registrar review com evidências e sugestão de commit

## Review (Permitir que run_all continue após falha no Bitbucket)
- What was validated:
  - [`run_all_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects_macos.sh) agora captura falha do `bitbucket_export.py` por projeto, emite aviso em `stderr`, acumula um resumo em `BITBUCKET_FAILURES` e segue para as etapas de portfólio e métricas.
  - [`run_all_projects.ps1`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros%20computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects.ps1) recebeu a mesma proteção: falhas de Bitbucket agora viram `Write-Warning` e não mais `throw`, preservando o restante do pipeline.
  - A publicação dos CSVs Bitbucket em `latest` continua ocorrendo apenas quando a exportação daquele projeto termina com sucesso; em caso de falha, o comportamento muda só no ponto certo: não bloquear os quatro artefatos principais (`portfolio-bt-ns-latest-data.csv`, `dashboard_output_latest.xlsx`, `bottlenecks_consolidado_latest.xlsx`, `PowerBI_Model_latest.xlsx`).
- Evidence (tests/logs/diff):
  - `bash -n run_all_projects_macos.sh`
  - `python3 - <<'PY' ... assert needles no run_all_projects_macos.sh ... PY`
  - `python3 - <<'PY' ... assert needles no run_all_projects.ps1 ... PY`
  - Limitação: `pwsh` não está instalado neste ambiente, então não foi possível fazer parse/smoke test automatizado do `.ps1`.
  - `git diff -- run_all_projects_macos.sh run_all_projects.ps1 tasks/todo.md`
- Suggested commit message:
  - `fix(run-all): keep portfolio and metrics generation running when bitbucket export fails`

## Current Task (Dashboard Full: mover relatórios Bitbucket para Produtividade Dev)
- [x] Localizar onde os relatórios `Contribuições Bitbucket (CSV)` e `Capacidade Cruzada (Jira + Bitbucket)` são renderizados
- [x] Remover esses blocos da aba `Performance do Serviço`
- [x] Renderizar os mesmos relatórios na aba `Produtividade Dev`
- [x] Validar sintaxe e registrar review com evidências

## Specification (Dashboard Full: mover relatórios Bitbucket para Produtividade Dev)
- Objetivo: deixar a aba `Performance do Serviço` focada nos indicadores operacionais do serviço e concentrar os relatórios técnicos por pessoa na aba `Produtividade Dev`.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Critério de aceite:
  - `Contribuições Bitbucket (CSV)` deixa de aparecer em `tab-performance`.
  - `Capacidade Cruzada (Jira + Bitbucket)` deixa de aparecer em `tab-performance`.
  - Os dois relatórios passam a aparecer em `tab-produtividade-dev` com os mesmos filtros ativos do período/projeto.

## Review (Dashboard Full: mover relatórios Bitbucket para Produtividade Dev)
- What was validated:
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) deixou de anexar `build_bitbucket_contributor_section(...)` ao retorno da `tab-performance`.
  - [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py) agora monta o mesmo bloco dentro da `tab-produtividade-dev`, usando os filtros ativos de período/projeto e o mesmo `jira_df` filtrado da aba.
  - Os retornos antecipados da aba `Produtividade Dev` também passaram a incluir o bloco movido; assim, o relatório continua visível mesmo quando a parte de produtividade individual não tem dados suficientes no filtro atual.
  - A mudança foi restrita à composição das abas; o conteúdo da função `build_bitbucket_contributor_section(...)` permaneceu intacto.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py`
  - `git diff -- dashboard_full.py tasks/todo.md`
- Suggested commit message:
  - `refactor(dashboard): move bitbucket contribution reports to produtividade dev tab`
# Current Task (Rastrear logs Bitbucket e identificação de tickets Jira)
- [x] Localizar no projeto onde os logs do Bitbucket são extraídos e carregados
- [x] Verificar se commits/PRs carregam ou derivam algum identificador de ticket Jira
- [x] Consolidar evidências do rastreio e registrar review

# Specification (Rastrear logs Bitbucket e identificação de tickets Jira)
- Objetivo: identificar no código onde o projeto recupera logs do Bitbucket e confirmar se existe associação explícita com IDs/chaves de tickets Jira.
- Escopo:
  - extração Bitbucket
  - carregamento dos CSVs derivados
  - funções de cruzamento Jira + Bitbucket
- Regras:
  - não alterar comportamento do projeto
  - responder com evidências de código e caminhos de arquivo

# Review (Rastrear logs Bitbucket e identificação de tickets Jira)
- O que foi confirmado:
  - A recuperação dos logs do Bitbucket é feita por [`bitbucket_export.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/bitbucket_export.py), consultando a API do Bitbucket para `commits`, `pullrequests` e `pipelines`.
  - O projeto já tem identificação explícita de tickets Jira nesses logs:
    - regex de chave: [`WORK_ITEM_KEY_RE` em `bitbucket_export.py:25`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/bitbucket_export.py#L25)
    - prefixos aceitos por projeto: [`PROJECT_BITBUCKET_DEFAULTS` em `bitbucket_export.py:32`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/bitbucket_export.py#L32)
    - extração das chaves em texto livre: [`extract_work_item_keys(...)` em `bitbucket_export.py:196`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/bitbucket_export.py#L196)
    - filtro por projeto usando prefixo Jira: [`row_matches_project(...)` em `bitbucket_export.py:763`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/bitbucket_export.py#L763)
  - As chaves Jira são persistidas nos CSVs exportados:
    - commits: colunas `work_item_keys` e `primary_work_item_key` em [`bitbucket_export.py:343`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/bitbucket_export.py#L343)
    - pull requests: mesmas colunas em [`bitbucket_export.py:367`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/bitbucket_export.py#L367)
    - pipelines: mesmas colunas em [`bitbucket_export.py:576`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/bitbucket_export.py#L576)
  - O carregamento posterior desses logs ocorre em:
    - [`dashboard_full.py:911`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L911)
    - [`dashboard_process_mining.py:378`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_process_mining.py#L378)
  - O vínculo Bitbucket -> Jira é efetivamente usado no analytics:
    - o dashboard agrega `work_item_keys`/`primary_work_item_key` dos logs Bitbucket para formar `tech_keys` em [`dashboard_process_mining.py:549`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_process_mining.py#L549)
    - depois compara essas chaves com `Issue Key` dos casos Jira para calcular `Itens c/ Evidencia Tecnica` e `Cobertura Tecnica (%)` em [`dashboard_process_mining.py:572`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_process_mining.py#L572)
    - há lógica equivalente no dashboard principal, comparando `ItemID/ID` do Jira com as chaves extraídas do Bitbucket em [`dashboard_full.py:1161`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L1161) e [`dashboard_full.py:1775`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L1775)
  - O script [`scripts/generate_commits_vs_jira_chart.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/scripts/generate_commits_vs_jira_chart.py) consome exatamente esse cruzamento via `load_project_bitbucket_logs(...)` + `compute_pm_bitbucket_cross_metrics(...)`.
- Conclusão:
  - Sim, existe identificação de ID/chave de ticket Jira nos logs Bitbucket.
  - Essa identificação não vem de um campo nativo da API Bitbucket ligado ao Jira; ela é inferida por padrão textual (`ABC-123`) em commit message, título de PR, source/destination branch e nome da ref de pipeline.
  - Depois de inferida, a chave é armazenada e usada para cruzar com `Issue Key` do Jira no dashboard/process mining.
- Suggested commit message:
  - `docs(bitbucket): record jira issue-key linkage in bitbucket log flow`

# Current Task (Mostrar exemplos reais de sucesso e falha no vínculo Jira x Bitbucket)
- [ ] Localizar os artefatos locais consumidos pelo dashboard para Jira e Bitbucket
- [ ] Extrair exemplos de `Issue Key` com evidência técnica no Bitbucket
- [ ] Extrair exemplos de `Issue Key` concluídas no Jira sem evidência técnica
- [ ] Registrar review com os exemplos encontrados

# Specification (Mostrar exemplos reais de sucesso e falha no vínculo Jira x Bitbucket)
- Objetivo: demonstrar com dados locais exemplos concretos em que o relacionamento por `Issue Key` funcionou e exemplos em que falhou.
- Escopo:
  - artefatos locais de process mining / Jira
  - CSVs Bitbucket carregados pelo dashboard
  - vínculo por `Issue Key`/`work_item_keys`
- Regras:
  - não alterar comportamento
  - priorizar exemplos do recorte usado pelos dashboards

# Review (Mostrar exemplos reais de sucesso e falha no vínculo Jira x Bitbucket)
- Artefatos usados:
  - [`artifacts/process_mining/w1nner-process-mining-latest.xlsx`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/artifacts/process_mining/w1nner-process-mining-latest.xlsx)
  - [`w1nner_commits.csv`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/w1nner_commits.csv)
  - [`w1nner_pullrequests.csv`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/w1nner_pullrequests.csv)
- Método:
  - Recorte validado: `2026-02-12` a `2026-03-13`.
  - Critério de sucesso: `Issue Key` concluída no Jira e também presente em `work_item_keys`/`primary_work_item_key` de commits ou PRs do Bitbucket.
  - Critério de falha: item concluído no Jira sem nenhuma chave correspondente no Bitbucket no recorte, ou chave no Bitbucket sem item concluído correspondente no recorte.
- Resultado agregado do recorte:
  - `114` cards concluídos no Jira.
  - `5` com evidência técnica no Bitbucket.
  - `109` sem evidência técnica no Bitbucket.
- Exemplos de sucesso:
  - `W1NNR-2161`: concluído em `2026-03-03`, autor final `Lara Junqueira Alvarenga`; apareceu no commit `W1NNR-2161 Fix analysis views crash on contact routes (missing client_id)` e no PR `W1NNR-2161 Fix analysis views crash on contact routes (missing client_id)`.
  - `W1NNR-2110`: concluído em `2026-02-24`; apareceu em commits `W1NNR-2110 Fix pipeline specs errors` e `W1NNR-2110 Fix client match service`.
  - `W1NNR-2144`: concluído em `2026-02-23`; apareceu no commit `W1NNR-2144 Prevents CommercialProposal...` e em PR com a mesma chave.
  - `W1NNR-2157`: concluído em `2026-02-23`; apareceu em dois commits e em um PR com a chave `W1NNR-2157`.
  - `W1NNR-2147`: concluído em `2026-02-20`; apareceu em commit e PR com a chave `W1NNR-2147`.
- Exemplos de falha (Jira concluído sem evidência Bitbucket no recorte):
  - `W1NNR-22`: concluído em `2026-03-06`, sem ocorrência da chave nos logs Bitbucket do recorte.
  - `W1NNR-13`: concluído em `2026-03-06`, sem ocorrência da chave nos logs Bitbucket do recorte.
  - `W1NNR-407`: concluído em `2026-03-06`, sem ocorrência da chave nos logs Bitbucket do recorte.
  - `W1NNR-409`: concluído em `2026-03-06`, sem ocorrência da chave nos logs Bitbucket do recorte.
  - `W1NNR-410`: concluído em `2026-03-06`, sem ocorrência da chave nos logs Bitbucket do recorte.
- Exemplos de falha no sentido oposto (atividade Bitbucket sem item concluído correspondente no recorte):
  - `W1NNR-2124`: apareceu em commit no Bitbucket em `2026-02-27`, mas não entre os cards concluídos do recorte.
  - `W1NNR-2173`: apareceu em commit no Bitbucket em `2026-02-27`, mas não entre os cards concluídos do recorte.
  - `W1NNR-2172`: apareceu em commit no Bitbucket em `2026-02-27`, mas não entre os cards concluídos do recorte.
  - `W1NNR-2040`: apareceu em commit no Bitbucket em `2026-02-27`, mas não entre os cards concluídos do recorte.
  - `S1NC-1958`: apareceu em commit no Bitbucket em `2026-02-27` e nem existe na planilha Jira `ConformidadeCasos` carregada para esse relatório W1NNER.
- Suggested commit message:
  - `docs(traceability): record local success and failure examples for jira-bitbucket linkage`

## Current Task (Incluir `User Story` na recuperação dos itens)
- [x] Localizar o filtro/lista de tipos usado na recuperação padrão dos itens
- [x] Incluir `User Story` sem alterar os demais tipos já suportados
- [x] Validar a resolução do filtro e registrar a revisão

## Specification (Incluir `User Story` na recuperação dos itens)
- Objetivo: garantir que a recuperação padrão de itens também considere o `work item type` `User Story`.
- Estratégia:
  - ajustar apenas a lista padrão de tipos no fluxo que atualmente considera `História`, `Task` e `Bug`
  - manter compatibilidade com aliases e override manual existentes
- Regras:
  - não remover tipos já suportados
  - evitar mudanças colaterais fora do fluxo de recuperação afetado

## Review (Incluir `User Story` na recuperação dos itens)
- O que foi implementado:
  - [`process_mining_jira.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/process_mining_jira.py) agora inclui `User Story` nos `default_issue_types` dos projetos legados `W1NNER`, `S1NC` e `BEFINANCE`.
  - O mapa `ISSUE_TYPE_ALIASES` também passou a tratar `User Story` como equivalente de `História`/`story`, preservando compatibilidade com os nomes já usados no CSV.
  - O fallback defensivo de `allowed_types` e o fallback de `default_issue_types` no `main()` também foram atualizados para não deixar `User Story` de fora em cenários sem configuração explícita.
- Evidências de validação:
  - leitura do diff em [`process_mining_jira.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/process_mining_jira.py), confirmando a inclusão em quatro pontos do fluxo de filtro
  - Limitação: a validação automatizada com `python -m py_compile process_mining_jira.py` não pôde ser executada neste ambiente porque o executável `python.exe` não iniciou (`ResourceUnavailable` no launcher do Windows).
- Suggested commit message:
  - `fix(process-mining): include user story in default item recovery`

## Current Task (Produtividade Dev: retorno para desenvolvimento e cycle time dev)
- [x] Confirmar a melhor fonte para medir ida e volta QA/teste -> desenvolvimento e o cycle time de desenvolvimento
- [x] Implementar agregação das novas métricas por pessoa sem quebrar a aba `Produtividade Dev`
- [x] Expor as métricas novas na tabela/KPIs da aba `Produtividade Dev`
- [x] Validar com compilação, inspeção do diff e registrar review

## Specification (Produtividade Dev: retorno para desenvolvimento e cycle time dev)
- Objetivo: avaliar e implementar a extração, a partir dos logs/histórico Jira já processados pelo projeto, de métricas de retorno para desenvolvimento após teste/QA e de cycle time de desenvolvimento, exibindo o resultado na aba `Produtividade Dev`.
- Estratégia:
  - reutilizar os artefatos de process mining/Jira já consumidos pelo dashboard em vez de introduzir uma fonte paralela na UI
  - medir por desenvolvedor os retornos QA/teste -> desenvolvimento e o tempo acumulado em etapas de desenvolvimento
  - integrar essas métricas ao `per_dev` da aba `tab-produtividade-dev`
- Regras:
  - manter compatibilidade com os filtros atuais da aba
  - evitar dupla contagem quando o mesmo item passa mais de uma vez por desenvolvimento
  - preservar as métricas já existentes e limitar o impacto ao fluxo de produtividade dev

## Review (Produtividade Dev: retorno para desenvolvimento e cycle time dev)
- O que foi implementado:
  - `process_mining_jira.py` passou a gerar métricas por item para `Cycle Time Dev` e para o loop completo de retorno `QA/Test/Homolog -> Dev`, além do detalhe `RetornoDevLoops` para relatório.
  - `dashboard_full.py` passou a reutilizar uma função única de resolução da pessoa do dev (`DevExecutor` com fallback para `Responsavel`) tanto na base Jira quanto no cruzamento com process mining.
  - A aba `Produtividade Dev` agora consolida `ConformidadeCasos` e `EventosFiltrados` dos relatórios `*-process-mining-latest.xlsx` para calcular:
    - `Cycle Time Dev Mediano (dias)` e `Cycle Time Dev Médio (dias)` a partir da soma de `TempoStatusDias` nas etapas normalizadas de desenvolvimento (`In Progress`, `In Development`, `Development`, `Doing` e equivalentes).
    - `Retornos QA->Dev`, `Cards com Retorno QA->Dev`, `% Cards com Retorno QA->Dev` e `Tempo Retorno QA->Dev Mediano (dias)` a partir do intervalo completo entre a saída de desenvolvimento para teste/QA e o retorno subsequente para desenvolvimento.
  - Os novos indicadores foram adicionados aos mini-KPIs do topo e à tabela/ranking da aba `Produtividade Dev`, sem alterar a lógica de score existente (`Score Integrado`, `IED`, `IEF`).
- Evidências de validação:
  - inspeção do diff em `process_mining_jira.py`, `dashboard_full.py` e `tasks/todo.md`
  - revisão estática dos trechos alterados para confirmar o encadeamento `Dev -> QA/Teste -> Dev` e a soma de `TempoStatusDias` em estágios de desenvolvimento
  - Limitação: nem `python -m py_compile` nem o smoke test sintético via `python -` puderam ser executados neste ambiente por falha do launcher `C:\\Users\\W1 TI\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe` (`ResourceUnavailable`).
- Suggested commit message:
  - `feat(produtividade-dev): add development cycle and qa return metrics`

## Current Task (Reequilibrar o cabeçalho do histograma de Lead Time)
- [x] Registrar a correção visual em `tasks/lessons.md`
- [x] Centralizar o título e ampliar o espaçamento superior do histograma
- [x] Validar sintaxe, revisar diff e registrar review

## Specification (Reequilibrar o cabeçalho do histograma de Lead Time)
- Objetivo: impedir que os rótulos verticais das linhas de referência sobrescrevam o título do histograma de Lead Time.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
  - `tasks/lessons.md`
- Estratégia:
  - definir o título do gráfico com posicionamento central explícito
  - aumentar a margem superior e o `pad` inferior do título para criar folga visual equivalente a cerca de três linhas
- Critério de aceite:
  - o título fica centralizado
  - o cabeçalho deixa de colidir com os rótulos verticais
  - o arquivo continua válido sintaticamente

## Review (Reequilibrar o cabeçalho do histograma de Lead Time)
- O que foi ajustado:
  - o histograma em [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L9478) agora usa `title=dict(...)` com `x=0.5` e `xanchor='center'` para centralizar o título
  - o mesmo bloco passou a usar `title.pad.b=48` e `margin.t=160`, abrindo espaço vertical adicional entre o título e a área do gráfico para evitar sobreposição com os rótulos verticais
  - a lição correspondente foi registrada em [`tasks/lessons.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/tasks/lessons.md)
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
- Risco residual:
  - a validação continua estática; não houve inspeção visual no navegador nesta sessão
- Suggested commit message:
  - `fix(dashboard): center lead time histogram title and add top spacing`

## Current Task (Melhorar legibilidade das linhas no histograma de Lead Time)
- [x] Localizar a configuração do histograma e das anotações das linhas de referência
- [x] Alterar a orientação dos textos das linhas para vertical
- [x] Validar sintaxe, revisar diff e registrar review

## Specification (Melhorar legibilidade das linhas no histograma de Lead Time)
- Objetivo: melhorar a leitura das anotações das linhas de percentis/média no histograma de Lead Time, reduzindo a sobreposição horizontal no topo do gráfico.
- Escopo:
  - `dashboard_full.py`
  - `tasks/todo.md`
- Estratégia:
  - ajustar apenas a orientação dos textos das `vlines` do histograma
  - preservar cores, posição das linhas e demais configurações do gráfico
- Critério de aceite:
  - os textos de `P50`, `P75`, `P85`, `P95` e `Média` passam a aparecer na vertical
  - a mudança afeta somente o histograma de Lead Time
  - o arquivo continua válido sintaticamente

## Review (Melhorar legibilidade das linhas no histograma de Lead Time)
- O que foi ajustado:
  - o histograma de Lead Time em [`dashboard_full.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/dashboard_full.py#L9469) passou a usar `annotation_textangle=90` nas `vlines` de `P50`, `P75`, `P85`, `P95` e `Média`
  - a mudança preserva as linhas, cores e posicionamento existentes, alterando apenas a orientação dos rótulos para reduzir a colisão horizontal no topo do gráfico
- Evidências de validação:
  - `python3 -m py_compile dashboard_full.py`
- Risco residual:
  - não houve inspeção visual no navegador nesta sessão; a validação foi estática
- Suggested commit message:
  - `fix(dashboard): rotate lead time histogram reference labels`

## Current Task (Publicar pacote `latest-upload` com artefatos esperados)
- [x] Mapear os artefatos finais esperados pelo dashboard e o fluxo atual de publicação `latest`
- [x] Implementar script dedicado para consolidar os arquivos esperados em `latest/latest-upload`
- [x] Acionar a consolidação ao final dos runners macOS e Windows relevantes
- [x] Validar a causa dos arquivos `latest` fora da pasta central e registrar review

## Specification (Publicar pacote `latest-upload` com artefatos esperados)
- Objetivo: copiar ao final da execução os artefatos operacionais esperados pelo dashboard para uma subpasta `latest-upload` dentro da pasta central `latest`, preservando o fluxo atual de geração dos aliases `latest`.
- Escopo:
  - `PowerBI_Model_latest.xlsx`
  - `portfolio-bt-ns-latest-data.csv`
  - `*-process-mining-latest.xlsx` dos quatro projetos
  - `*-downstream-latest-data.csv` dos quatro projetos
  - `*-downstream-latest-data_bottlenecks.csv` dos quatro projetos
  - `*_commits.csv`, `*_pullrequests.csv`, `*_pipelines.csv` de `w1nner`, `befinance`, `dataanalytics` e `s1nc` como opcional
- Estratégia:
  - usar a pasta central `latest` como fonte única para a cópia final, para evitar duplicar regras de origem em cada runner
  - manter os aliases `latest` no `OUT_DIR` quando eles fizerem parte do fluxo atual dos scripts
  - produzir uma subpasta limpa e previsível `latest/latest-upload` com somente os arquivos necessários para upload
- Regras:
  - não remover o comportamento atual que mantém aliases `latest` também em `OUT_DIR`
  - tratar os arquivos de Bitbucket de `s1nc` como opcionais
  - falhar apenas quando um artefato obrigatório estiver ausente

## Review (Publicar pacote `latest-upload` com artefatos esperados)
- O que foi implementado:
  - [`copy_latest_upload.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/copy_latest_upload.py) agora consolida os artefatos operacionais esperados a partir da pasta central `latest` e monta a subpasta `latest-upload`.
  - os runners [`run_all_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects_macos.sh), [`run_all_projects.ps1`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_all_projects.ps1), [`run_process_mining_projects_macos.sh`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_projects_macos.sh) e [`run_process_mining_projects.ps1`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/run_process_mining_projects.ps1) passaram a atualizar `latest/latest-upload` ao final da execução.
  - o script copia como obrigatórios `PowerBI_Model_latest.xlsx`, `portfolio-bt-ns-latest-data.csv`, os quatro `*-process-mining-latest.xlsx`, os quatro downstreams `*-latest-data.csv`, os quatro gargalos `*-latest-data_bottlenecks.csv` e os CSVs Bitbucket de `w1nner`, `befinance` e `dataanalytics`; os arquivos de `s1nc` ficaram opcionais.
  - a consolidação usa a pasta central `latest` como fonte única. Isso evita replicar regras de origem em cada runner e mantém o pacote de upload desacoplado do diretório operacional de saída.
- Causa confirmada dos arquivos `latest` fora da pasta central:
  - isso não era um erro isolado: os runners já atualizavam aliases `latest` dentro do `OUT_DIR` (`/Users/rodrigoalmeidadeoliveira/Documents/dados`) e depois publicavam uma cópia na pasta central `latest`.
  - além disso, consumidores importantes como `dash_board_metricas.py`, `extract_dev_productivity_data.py` e os loaders baseados em [`shared/path_utils.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/shared/path_utils.py) ainda priorizam `FLOW_PMO_DATA_DIR` / `DATA_FOLDER`, que nos runners apontam para `OUT_DIR`.
  - conclusão: os arquivos `latest` fora de `latest` fazem parte do desenho atual do pipeline; `latest` atua como pasta estável de publicação/espelho, não como única origem operacional.
- Evidências de validação:
  - `python3 -m py_compile copy_latest_upload.py`
  - `bash -n run_all_projects_macos.sh`
  - `bash -n run_process_mining_projects_macos.sh`
  - parse de PowerShell com `System.Management.Automation.Language.Parser` para `run_all_projects.ps1` e `run_process_mining_projects.ps1`
  - teste real do consolidator: `python3 copy_latest_upload.py --source-dir /Users/rodrigoalmeidadeoliveira/Documents/dados/latest --dest-dir /tmp/flow-pmo-latest-upload-test --clean-dest --strict`, copiando `26` arquivos com sucesso
- Suggested commit message:
  - `feat(latest-upload): package required dashboard artifacts after runner execution`
## Current Task (Paper: empirical validation with anonymized production data)
- [x] Map the production metrics already available in the project and define the empirical dataset contract
- [x] Implement anonymized aggregation/figure generation under `paper/`
- [x] Update the article text to add empirical validation, anonymization, and production-backed results
- [x] Verify generated artifacts and compile the paper
- [x] Record review and suggested commit message

## Specification (Paper: empirical validation with anonymized production data)
- Goal: extend the paper from a synthetic-only framework evaluation to a framework paper with an empirical validation section based on anonymized production telemetry.
- Scope:
  - `paper/paper.tex`
  - `paper/paper_draft.md`
  - new/updated support scripts under `paper/`
  - `tasks/todo.md`
- Acceptance criteria:
  - The manuscript adds an empirical validation section describing real Jira, Bitbucket, process-mining, QA-return, and bottleneck data.
  - The manuscript explicitly documents anonymization and disclosure-control rules suitable for LGPD-safe reporting.
  - The repository gains a repeatable script that produces anonymized team/cohort/quarter aggregates and production-safe figures.
  - The manuscript references only aggregated production outputs, not named individuals or raw identifiers.
  - The paper still compiles after the changes.

## Review (Paper: empirical validation with anonymized production data)
- What was validated:
  - [`paper/generate_empirical_validation.py`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/paper/generate_empirical_validation.py) now reuses the real dashboard pipeline (`dashboard_full.py`) to aggregate Jira, Bitbucket, process-mining, QA-return, and bottleneck metrics into anonymized team-quarter outputs.
  - The script writes disclosure-controlled artifacts under [`paper/generated`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/paper/generated) and [`paper/figures`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/paper/figures), including new empirical figures `fig5` to `fig8`.
  - [`paper/paper.tex`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/paper/paper.tex) now includes a reframed abstract and contributions, a dedicated empirical-validation section, explicit LGPD-safe anonymization/disclosure rules, and production-backed results that consume the generated anonymized artifacts.
  - [`paper/paper_draft.md`](/Users/rodrigoalmeidadeoliveira/Library/CloudStorage/GoogleDrive-rodrigoalmeidadeoliveira@gmail.com/Outros computadores/Notebook/Python/Projetos/flow-pmo/flow-pmo/paper/paper_draft.md) was aligned at the framing level so the markdown draft no longer conflicts with the LaTeX paper's core thesis.
  - The empirical run in the current environment produced 4 anonymized team-quarter observations; after disclosure control the published output collapsed into a single stable alias (`Team A`), which is consistent with the `n < 5` suppression rule applied to smaller groups.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile paper/generate_empirical_validation.py paper/generate_synthetic_data.py paper/generate_figures.py`
  - `python3 paper/generate_empirical_validation.py`
  - `pdflatex -interaction=nonstopmode -halt-on-error paper.tex`
  - `pdflatex -interaction=nonstopmode -halt-on-error paper.tex`
- Residual risks:
  - The current production snapshot yields only one published cohort after suppression, so the empirical visuals are privacy-safe but less diverse than the ideal multi-team version.
  - `paper.tex` compiles cleanly, but still reports some overfull `\hbox` warnings in long paragraphs; these are typographic, not functional.
- Suggested commit message:
  - `feat(paper): add anonymized production-data validation to flowpmo article`
