# Lessons Learned

Use this file after any user correction.

## Entry Template
- Date:
- Context:
- User correction:
- Root cause:
- Prevention rule:
- Action added to workflow:

## Entries
- Date: 2026-03-05
- Context: Usuário reportou que o gráfico de CFD não estava igual ao de produção.
- User correction: Solicitou alinhamento visual/comportamental do CFD com referência de produção.
- Root cause: O CFD estava com snapshots semanais e interpolação linear, reduzindo fidelidade visual (sem degraus e sem linhas-guia de taxa).
- Prevention rule: Para CFD comparado com ferramenta de produção, usar snapshots diários e renderização em degrau (`line.shape='hv'`) como baseline.
- Action added to workflow: Em qualquer ajuste de CFD, validar explicitamente granularidade temporal, forma da curva e presença de linhas de taxa esperadas.

- Date: 2026-03-03
- Context: Regressao apos deploy no CFD detalhado com mensagem de CSV downstream indisponivel.
- User correction: Reportou que o dashboard passou a exibir erro de ausencia de `*-data.csv` para W1NNER apos deploy.
- Root cause: Parser de `FLOW_PMO_DOWNSTREAM_CSV_URL_MAP` era estrito (`json.loads`) e falhava com valor de env malformado por aspas extras.
- Prevention rule: Para envs JSON criticas de runtime, implementar parse tolerante (normalizacao + fallback) e nao depender de um unico formato perfeito.
- Action added to workflow: Em qualquer leitura de `*_URL_MAP`, testar formatos comuns quebrados antes de retornar vazio.

- Date: 2026-03-03
- Context: Falha no `deploy.py` com erro de token invalido na etapa `whoami`.
- User correction: Reportou erro `You defined "--token", but its contents are invalid` ao executar `python deploy.py`.
- Root cause: O script convertia automaticamente `VERCEL_OIDC_TOKEN` para `VERCEL_TOKEN`, mas o formato OIDC (JWT) e invalido para a Vercel CLI.
- Prevention rule: Nunca mapear automaticamente `VERCEL_OIDC_TOKEN` para `VERCEL_TOKEN`; validar formato de token antes de chamar a CLI.
- Action added to workflow: Em scripts de deploy Vercel, aplicar validacao de `VERCEL_TOKEN` e fallback para sessao local quando o token for invalido.

- Date: 2026-03-03
- Context: Erro no `deploy.py` durante etapa `whoami` em Windows com mensagem `'vercel' nao e reconhecido`.
- User correction: Reportou que o script estava resolvendo `C:\Program Files\nodejs\npx.CMD vercel whoami` e falhando.
- Root cause: Assumi que fallback via `npx vercel` era confiavel; no ambiente real faltava binario/link esperado para resolver `vercel` dentro do npx.
- Prevention rule: Em ferramentas Node locais, priorizar execucao direta da CLI instalada (`node node_modules/<pkg>/dist/index.js`) antes de depender de `npx`.
- Action added to workflow: Sempre verificar `node_modules/.bin/<tool>` e `node_modules/<tool>/dist/index.js` no ambiente alvo quando houver falha de comando.

- Date: 2026-03-03
- Context: Entrega inicial do fluxo de deploy cross-platform para Vercel.
- User correction: Solicitou explicitamente um script Python unico que trate diferencas/excecoes de ambiente e execute deploy completo.
- Root cause: Interpretei "cross-platform" como necessidade de wrappers por SO, em vez de priorizar um unico entrypoint Python com toda a orquestracao.
- Prevention rule: Quando o usuario pedir "script unico", evitar artefatos paralelos e concentrar toda a logica operacional em um unico arquivo.
- Action added to workflow: Em tarefas de automacao/deploy, confirmar no inicio se a entrega esperada e `single-entrypoint` ou `multi-wrapper` antes de implementar.

- Date: 2026-03-02
- Context: Ajuste de score percentual em `Capacidade Cruzada (Jira + Bitbucket)`.
- User correction: Indicou que o cálculo percentual continuava inadequado após a primeira versão.
- Root cause: Interpretei `%` como participação no total do time, mas a leitura esperada era índice relativo por pessoa.
- Prevention rule: Em métricas “em percentual” de ranking individual, confirmar se o denominador esperado é total da equipe, teto/meta, ou máximo do recorte.
- Action added to workflow: Antes de fechar KPI percentual novo, validar explicitamente a interpretação com 3 checks: `maior valor = 100%?`, `soma = 100%?`, `semântica esperada pelo usuário`.

- Date: 2026-03-02
- Context: Inclusão de relatório Jira x Bitbucket no `dashboard_full.py`.
- User correction: Informou que a aba de Process Mining não estava visível e exigiu que o score de capacidade fosse percentual.
- Root cause: Implementei o relatório e o bloco de capacidade sem garantir exposição explícita da aba em `SERVICE_TABS` e mantive score absoluto (`proxy`) em vez de percentual.
- Prevention rule: Sempre validar navegação (tab visível no menu ativo) e unidade de medida pedida pelo usuário (absoluto vs percentual) antes de concluir visualizações.
- Action added to workflow: Em alterações de dashboards, incluir checklist final: (1) aba visível em `SERVICE_TABS`, (2) unidade exibida coerente com pedido, (3) rótulo da métrica alinhado ao cálculo.

- Date: 2026-02-27
- Context: Implementação de ranking cruzado Jira + Bitbucket na aba Performance.
- User correction: Reportou exceção `KeyError: 'Pessoa'` no merge do consolidado (`compute_cross_source_capacity_metrics`).
- Root cause: O merge assumia que o dataframe de métricas Bitbucket sempre teria a coluna `Pessoa`; quando a fonte vinha vazia, a função retornava `DataFrame()` sem schema e o merge quebrava.
- Prevention rule: Em merges de fontes opcionais (Jira/Bitbucket), garantir schema mínimo explícito antes do `pd.merge` (colunas-chave devem existir mesmo com dataframe vazio).
- Action added to workflow: Antes de concluir features de agregação multi-fonte, executar smoke test com cada fonte vazia isoladamente e ambas vazias.

- Date: 2026-02-25
- Context: Divergência do componente de calendário entre localhost e Vercel, com hacks JS quebrando interação em produção.
- User correction: Mostrou que localhost estava com DatePicker novo (mês/ano nativos) enquanto produção continuava com UI antiga e comportamento quebrado.
- Root cause: Ambiente local rodava `dash 4.0.0`, mas produção estava pinada em `dash==2.18.2` (`pyproject.toml` / `requirements-vercel.txt`), criando mismatch de DOM e incompatibilidade com customização em `assets`.
- Prevention rule: Antes de diagnosticar regressão visual entre local e produção, comparar explicitamente versões de runtime/dependências (ex.: `dash.__version__`) e alinhar pins de deploy.
- Action added to workflow: Em bugs de UI no Vercel, verificar primeiro `logs + versão local + versão pinada em pyproject/requirements` antes de iterar em hacks de CSS/JS.

- Date: 2026-02-25
- Context: Correção de regressão no seletor de ano do `DatePickerRange` em `dashboard_process_mining.py` após alteração do componente de calendário.
- User correction: Informou que o controle de datas mudou e não era mais possível escolher o ano no calendário.
- Root cause: O hack de dropdown de ano em `assets/calendar-year-dropdown.js` dependia de seletores DOM antigos (`.dash-datepicker-controls` / header antigo) e deixou de injetar o seletor com o novo layout do DatePicker.
- Prevention rule: Ao customizar componentes de terceiros por DOM/CSS (DatePicker, Dropdown, overlays), implementar seletores com fallback para múltiplas versões e validar o comportamento após upgrades visuais.
- Action added to workflow: Em qualquer ajuste de assets do calendário, revisar seletores JS/CSS contra o DOM atual e testar abertura do calendário com troca de mês e ano.

- Date: 2026-02-23
- Context: Unificação de abas de análise no dashboard de serviços.
- User correction: Reportou regressão visual no filtro de data (ano não visível no calendário).
- Root cause: Mudança de UI expôs fragilidade no customizador do DatePicker (`assets/calendar-fix.css` / `calendar-year-dropdown.js`), deixando o dropdown de ano sem texto legível.
- Prevention rule: Após mudanças de layout/abas, validar componentes overlay (DatePicker/Dropdowns) visualmente, não apenas sintaxe.
- Action added to workflow: Em ajustes de navegação, abrir o calendário e verificar cabeçalho/mês/ano antes de concluir.

- Date: 2026-02-23
- Context: Pedido para unificar abas `Análise Dimensional`, `Análise Tipos` e `Análise Eficiência` sob `Análise Fluxo`.
- User correction: Informou que as abas não foram unificadas após minha entrega.
- Root cause: Apliquei a mudança no arquivo errado (`dashboard_app.py`) enquanto a interface em uso era `dashboard_full.py`.
- Prevention rule: Em qualquer alteração de navegação/abas, confirmar o dashboard ativo pelos labels exibidos e pela estrutura de tabs antes de editar.
- Action added to workflow: Comparar labels da UI com `SERVICE_TABS`/`dcc.Tabs` do arquivo alvo e validar no diff que a navegação correta foi alterada.

- Date: 2026-02-23
- Context: Correção de escopo do CFD detalhado após filtrar por IDs do `df_flow`.
- User correction: Informou que o erro persistia porque ainda apareciam itens não finalizados no período filtrado.
- Root cause: Usei IDs de `df_flow` (semântica de fluxo: inclui WIP no período), mas o usuário esperava o recorte de concluídos do filtro global (`df`, filtrado por `DataDone`).
- Prevention rule: Em abas com datasets paralelos (`df` concluídos vs `df_flow` ativos no período), alinhar explicitamente cada gráfico à semântica esperada do usuário e documentar isso no código.
- Action added to workflow: Para CFD detalhado em `tab-fluxo`, usar IDs de `df` quando a expectativa for “concluídos no filtro”; só usar `df_flow` se houver opção explícita de incluir WIP.

- Date: 2026-02-23
- Context: CFD detalhado exato usando CSV downstream por projeto.
- User correction: Indicou que o gráfico estava mostrando itens fora do filtro selecionado (ex.: itens não finalizados no recorte), apesar do período/filtros aplicados na aba.
- Root cause: O modo detalhado lia o CSV downstream inteiro do projeto sem restringir pelos `ItemID`s já filtrados em `df_flow`.
- Prevention rule: Quando uma visualização combina fonte agregada/curada (`fato`) com fonte auxiliar por projeto (CSV downstream), sempre aplicar interseção por ID com o dataset filtrado da tela.
- Action added to workflow: Em gráficos detalhados por CSV downstream, passar explicitamente `ItemID`s filtrados da UI para evitar divergência de escopo.

- Date: 2026-02-23
- Context: Comparação visual do CFD com a ferramenta Actionable Agile.
- User correction: Indicou que o CFD local estava menos legível e com paleta apagada, pedindo um visual mais entendível e cores mais vivas.
- Root cause: A renderização usava preenchimento de curvas cumulativas e paleta genérica/pastel, o que reduzia contraste entre bandas.
- Prevention rule: Em gráficos de áreas empilhadas (especialmente CFD), priorizar `stackgroup`, paleta com alto contraste e `hover x unified` antes de considerar o visual final.
- Action added to workflow: Ao entregar visualizações de fluxo, comparar legibilidade com referência do usuário (cores, legenda, densidade visual, leitura de bandas) e iterar no estilo.

- Date: 2026-02-23
- Context: Ajuste solicitado após adicionar modo detalhado do CFD como estimado por gargalos.
- User correction: Informou que o CSV downstream por projeto (`*_data.csv`) já contém datas por etapa/transição do item, viabilizando CFD detalhado exato.
- Root cause: Assumi limitação do modelo consolidado (`Fato_Items`/`Fato_Gargalos`) sem verificar a fonte downstream por projeto disponível no fluxo atual.
- Prevention rule: Antes de marcar uma visualização como "estimada", verificar explicitamente se há fonte granular alternativa no projeto (CSV downstream, logs de transição, histórico de status).
- Action added to workflow: Para gráficos de fluxo por etapa, checar primeiro `*_data.csv` por projeto e só cair para estimativa quando a fonte granular estiver ausente.

- Date: 2026-02-23
- Context: Entrega inicial de CFD na aba de fluxo atendeu parcialmente, mas ficou em macrofases.
- User correction: Pediu opção de detalhamento por etapas do fluxo, alinhada ao gráfico de gargalos.
- Root cause: Implementei primeiro com granularidade macro (Backlog/Em Progresso/Pronto) sem expor uma opção de detalhamento e sem alinhar explicitamente com a estrutura de etapas já usada em gargalos.
- Prevention rule: Ao criar visualização nova baseada em fluxo, validar antes se o usuário espera granularidade macro ou por etapa e alinhar com os artefatos existentes (`Fato_Gargalos`) quando houver referência visual/funcional.
- Action added to workflow: Em pedidos de gráficos de fluxo, comparar a nova visualização com os gráficos de gargalo/etapas existentes e oferecer modo macro + detalhado quando os dados suportarem.

- Date: 2026-02-20
- Context: Diagnóstico de gargalos em produção ainda divergente após ajustes de status.
- User correction: Indicou que "ainda não funcionou" e forneceu CSVs corretos em `/Users/.../Documents/dados`.
- Root cause: Pipeline de métricas gerava `PowerBI_Model_latest.xlsx` lendo pasta fixa diferente (`OneDrive.../Documentos/Dados`), então `Fato_Gargalos` não incorporava os CSVs recém-gerados.
- Prevention rule: Nunca assumir um único diretório hardcoded para dados; sempre priorizar `FLOW_PMO_DATA_DIR`/`DATA_FOLDER` e alinhar scripts de exportação e métricas para o mesmo `OUT_DIR`.
- Action added to workflow: Antes de concluir diagnóstico de dados, validar explicitamente "origem dos artefatos lidos" vs "origem dos artefatos gerados" e comparar conteúdo da aba `Fato_Gargalos` no `PowerBI_Model_latest.xlsx`.

- Date: 2026-02-20
- Context: Fluxo de gargalo do projeto DT estava divergindo do fluxo real por tipo de demanda.
- User correction: Informou dois workflows distintos para DT (melhorias vs ad-hoc/bug/incidente), com etapas e transições específicas.
- Root cause: Exportador usava uma única ordem de etapas por projeto, sem distinguir tipo de item dentro do DT.
- Prevention rule: Sempre validar se um projeto possui múltiplos workflows por tipo de issue antes de consolidar gargalo por etapa.
- Action added to workflow: Para DT, calcular gargalo com `stage_order` por linha (`Tipo de Problema`) e manter override explícito via `JIRA_STATUS_MAP` quando necessário.

- Date: 2026-02-20
- Context: Solicitação para preservar decisões do projeto e evitar regressões por contexto perdido.
- User correction: Reforçou que devo salvar decisões na memória do projeto e consultá-la sempre antes de propor ou alterar algo.
- Root cause: Alterações rápidas ao longo do dia podem quebrar coerência entre decisões anteriores (fonte de dados, fallbacks, fluxo por projeto).
- Prevention rule: Antes de qualquer proposta/edição, revisar `tasks/lessons.md` e os blocos de review/decisões em `tasks/todo.md`.
- Action added to workflow: Tornar obrigatório no início de cada tarefa: (1) leitura de memória do projeto, (2) confirmação da fonte ativa (`MODEL_FILE`/env), (3) validação de aderência às decisões já registradas.

- Date: 2026-02-20
- Context: Fluxos por projeto não estavam sendo aplicados mesmo após ajuste no código do exportador.
- User correction: Cobrou confirmação de gravação correta na `Fato_Gargalos` com fluxos adequados.
- Root cause: `JIRA_STATUS_MAP` do `jira_env.txt` sobrescrevia automaticamente a resolução dinâmica de fluxo por projeto/tipo.
- Prevention rule: Em execução automatizada multi-projeto, não permitir que `JIRA_STATUS_MAP` global force um fluxo único sem intenção explícita.
- Action added to workflow: Criar e usar `JIRA_IGNORE_STATUS_MAP=1` nos scripts `run_all_projects_*` durante exportação downstream e validar no log a quantidade de etapas por projeto.

- Date: 2026-02-20
- Context: Gargalo de W1NNER sem etapa `In Progress` no relatório final.
- User correction: Indicou ausência de `In Progress` no gráfico/tabela gerados.
- Root cause: Mapeamento legado de `In Progress` não cobria variações reais de status (ex.: `Development`, `In Development`, `Doing`), gerando zero pares `In Progress -> Ready for code review`.
- Prevention rule: Para cada fluxo legado, validar cobertura de aliases reais de status e checar explicitamente pares consecutivos críticos.
- Action added to workflow: Após cada ajuste de status map, reprocessar 1 projeto alvo e validar presença das etapas esperadas em `Fato_Gargalos` (não só no CSV intermediário).

- Date: 2026-02-23
- Context: Usuário reportou persistência de erro no KPI `Lead Time P85` do Painel de Fluxo e inconsistência com a tela Performance do Serviço.
- User correction: Mostrou evidências de que o dashboard ainda exibia `Lead Time P85 = 2.0 dias` e valores incompatíveis com o comportamento de cycle time esperado.
- Root cause: Eu corrigi percentis e elegibilidade, mas não validei a semântica do indicador exibido; as telas operacionais continuavam usando `LeadTime_Dias` com amostra ínfima (W1NNER tinha apenas 2 itens com `DataBacklog` preenchido no período).
- Prevention rule: Antes de concluir correção de percentis/KPI, validar também cobertura amostral da métrica (`n`) e confirmar se a tela operacional deve usar `Lead Time` ou `Cycle Time`.
- Action added to workflow: Para KPIs percentílicos de tempo, sempre verificar e registrar `(métrica, filtro, n da amostra)` e alinhar o rótulo da UI à métrica real usada.

- Date: 2026-02-23
- Context: Ajuste de KPI de tempo após tentativa de resolver inconsistência usando Cycle Time.
- User correction: Reforçou que o conceito correto para o dashboard é `Lead Time` (comprometimento até finalização), não `Cycle Time`.
- Root cause: Eu corrigi a inconsistência operacional trocando a métrica, mas isso contrariou a definição de negócio do usuário.
- Prevention rule: Em divergência entre qualidade estatística e definição de negócio, preservar primeiro a métrica de negócio e corrigir a instrumentação (filtro, cobertura, amostra), não trocar o conceito.
- Action added to workflow: Quando houver discrepância de KPI de tempo, confirmar explicitamente se o problema é de conceito (`Lead` vs `Cycle`) ou de parametrização de etapas antes de alterar rótulos/semântica.

- Date: 2026-02-23
- Context: Solicitação para criar aba de Lead Time com referência visual; a entrega foi aplicada em arquivo de dashboard errado.
- User correction: Informou que a aba de Lead Time não estava aparecendo.
- Root cause: Implementei a aba em `dashboard_app.py` sem confirmar qual aplicação o usuário estava executando (provavelmente `dashboard_full.py`).
- Prevention rule: Antes de alterar UI com abas/páginas, confirmar o entrypoint em uso (script de execução/arquivo aberto) e aplicar no dashboard certo.
- Action added to workflow: Em pedidos de interface, validar primeiro o arquivo ativo (`dashboard_full.py` vs `dashboard_app.py`) com o usuário ou pelo fluxo de execução local.

- Date: 2026-02-23
- Context: Usuário informou que o filtro de etapas ainda não afetava 100% o Painel após correção inicial.
- User correction: Pediu revisão detalhada dos KPIs/gráficos do Painel porque os números continuavam praticamente iguais.
- Root cause: A correção inicial aplicou o filtro às métricas de Lead Time, mas deixou indicadores de referência (demanda/entrada/tempo para commit) presos à semântica antiga (`DataInProgress` / backlog fixo).
- Prevention rule: Quando um filtro semântico redefine o “início do fluxo”, revisar também todos os KPIs/gráficos derivados de chegada/compromisso no mesmo painel, não apenas percentis de lead time.
- Action added to workflow: Em filtros de etapa/fluxo, mapear por aba quais métricas usam data de início, data de fim e WIP para validar dependência correta do filtro.

- Date: 2026-02-23
- Context: Usuário pediu que WIP e WIP Age também fossem afetados pelo filtro de etapas no Painel.
- User correction: Informou explicitamente que WIP/WIP Age representam trabalho vivo e devem usar a mesma semântica de início selecionado.
- Root cause: Mantive `WIP` e `WIP Age` ancorados em `DataInProgress`, enquanto o painel já estava adotando `LeadStart_Selected` para outras métricas de compromisso.
- Prevention rule: Se o filtro redefine "quando o trabalho entra no fluxo medido", aplicar isso também às métricas de WIP/WIP Age da mesma tela (salvo regra de negócio explícita em contrário).
- Action added to workflow: Em auditorias de filtros semânticos, testar separadamente impacto em `Lead Time`, `Chegadas`, `WIP` e `WIP Age`.

- Date: 2026-02-27
- Context: Primeiro teste real do exportador Bitbucket retornou `400 Invalid pagelen` no endpoint de pull requests.
- User correction: Mostrou execução com erro em `.../pullrequests?pagelen=100`.
- Root cause: Assumi limite uniforme de `pagelen=100` para todos os endpoints, mas o endpoint de PR rejeitou esse valor.
- Prevention rule: Em integrações Bitbucket, usar `pagelen` conservador (`<=50`) por padrão para compatibilidade entre endpoints.
- Action added to workflow: Ao implementar paginação Bitbucket, validar limites por endpoint ou começar com `pagelen=50` antes de otimizações.

- Date: 2026-02-27
- Context: Execução real do exportador Bitbucket com histórico completo interrompida em página alta de commits.
- User correction: Reportou erro `429 Too Many Requests` no endpoint de commits (`page=440`) e pediu continuidade prática da implementação.
- Root cause: O fluxo de paginação fazia `raise_for_status()` direto, sem retry/backoff para limite de taxa temporário.
- Prevention rule: Em integrações paginadas com APIs externas, tratar `429` e `5xx` com retry exponencial e suporte a `Retry-After` antes de considerar falha fatal.
- Action added to workflow: Para novos conectores HTTP, criar helper central de request resiliente e reutilizar em todos os pontos de chamada.

- Date: 2026-02-27
- Context: Exportador ainda sofria 429 contínuo mesmo com retry/backoff curto.
- User correction: Compartilhou log longo mostrando 429 recorrente por página durante commits históricos.
- Root cause: Retry sem pacing global permitia retomar cedo demais, mantendo o cliente preso no limite de taxa da janela da API.
- Prevention rule: Para APIs com rate limit por janela, combinar retry com throttling contínuo (intervalo mínimo entre requests) e cooldown global após 429.
- Action added to workflow: Em conectores HTTP de alto volume, expor parâmetro de pacing (`min-request-interval`) e definir default conservador.

- Date: 2026-03-04
- Context: Nova visão de roadmap por quarter no portfólio apresentou distribuição incorreta (concentração artificial em `Planning`/`Q1`).
- User correction: Informou que a distribuição exibida não estava correta.
- Root cause: Usei fallback amplo de status (`Backlog`/`Em progresso`) para classificar `Planning`/`Running`, o que inflou a legenda fora da regra pedida; também havia fallback implícito de quarter para o selecionado.
- Prevention rule: Em visões executivas com legenda explícita, aplicar mapeamento estrito ao vocabulário solicitado e não inferir categorias extras sem validação do usuário.
- Action added to workflow: Ao criar roadmap por quarter, validar com tabela de conferência `Status original -> Status da legenda -> Quarter` antes de fechar.

- Date: 2026-03-04
- Context: Filtro `Classe Serviço (Prioridade)` não impactava os épicos no módulo de Portfólio.
- User correction: Reportou que o filtro de prioridades não estava filtrando os épicos no dashboard.
- Root cause: O branch `tab-portfolio` não aplicava `classe_servico` sobre `df_portfolio_filtered`; além disso o loader priorizava arquivo datado em vez do alias `latest` com dados atualizados.
- Prevention rule: Para filtros globais expostos na UI, validar explicitamente aplicação em cada módulo (serviços e portfólio) e confirmar a fonte de dados efetivamente carregada.
- Action added to workflow: Em regressões de filtro, registrar evidência mínima: `arquivo selecionado`, `contagem antes/depois do filtro` e `colunas-base do filtro`.

- Date: 2026-03-04
- Context: Usuário pediu estrela para itens `Highest/Higest`, mas a UI não exibiu nenhum destaque.
- User correction: Reportou explicitamente que a estrela não estava aparecendo.
- Root cause: O CSV de portfólio consumido pelo dashboard não tinha coluna `Prioridade`, e o fallback por IDs não casava com a base downstream disponível.
- Prevention rule: Antes de depender de um campo de negócio na UI, validar presença do campo na fonte ativa e preparar fallback configurável quando a fonte estiver incompleta.
- Action added to workflow: Em componentes de destaque por atributo (prioridade, risco etc.), sempre incluir fallback por configuração (`env`) e teste de render com dado sintético.

- Date: 2026-03-04
- Context: Solicitação de destacar com estrela os itens `Highest/Higest` no one page completo.
- User correction: Indicou explicitamente que os projetos marcados como `Higest` devem exibir o ícone de estrela conforme referência visual.
- Root cause: A visualização não tinha suporte de destaque visual para prioridade máxima no nível do épico.
- Prevention rule: Sempre que houver categoria executiva explícita (ex.: `Highest`), refletir isso com sinal visual dedicado na UI, não apenas por texto.
- Action added to workflow: Em ajustes de roadmap visual, revisar checklist de realce: `cores`, `ícones de prioridade`, `ordenação por criticidade`.

- Date: 2026-03-04
- Context: One page roadmap exibiu vazio em Q3/Q4 apesar de `DueDate` preenchido no CSV latest.
- User correction: Reportou inconsistência e evidenciou que os épicos tinham `DueDate` populado na planilha.
- Root cause: O mapeamento de legenda estava estrito demais e descartava itens com status `Triagem`, que representam planejamento no portfólio atual.
- Prevention rule: Antes de concluir um mapeamento semântico de status, validar distribuição por status real do CSV em cada quarter (Q1..Q4), não apenas no quarter inicial.
- Action added to workflow: Em mudanças de mapeamento de legenda, executar checklist de reconciliação: `count por quarter`, `count por status original` e `count por status mapeado`.

- Date: 2026-03-03
- Context: Ajuste do gráfico de Process Mining para análise de cards puxados por faixa de story points.
- User correction: Solicitou que o gráfico mostrasse todas as pessoas com volume de cards puxados separado em faixas de story points.
- Root cause: Eu implementei primeiro a visão agregada por faixa/senioridade, mas não priorizei a pergunta operacional principal por pessoa.
- Prevention rule: Em pedidos de visualização, validar explicitamente o eixo principal (quem/tempo/faixa) antes de finalizar.
- Action added to workflow: Para novos gráficos de breakdown, conferir checklist: `dimensão principal pedida`, `segmentação secundária` e `unidade no eixo Y`.

- Date: 2026-03-03
- Context: Gráficos do Process Mining exibindo pessoas fora do período selecionado na tela.
- User correction: Solicitou que os gráficos se atenham aos filtros de data aplicados.
- Root cause: Eu usei datasets agregados da planilha de process mining para alguns gráficos sem recomputar após os filtros de data no dashboard.
- Prevention rule: Em dashboards com filtros temporais, evitar usar agregados pré-computados sem recorte; preferir recomputar no runtime a partir da base filtrada.
- Action added to workflow: Para cada gráfico novo/alterado, validar explicitamente: `fonte pós-filtro`, `janela temporal aplicada` e `consistência com a seleção de datas da UI`.
