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
- Date: 2026-04-13
- Context: Validação dos campos estruturados que devem contar para a cobertura GMUD.
- User correction: Reforçou que `Cartões Relacionados (GMUD)` também precisa ser considerado, após já cobrar validação de `link` e `Itens de Configuração`.
- Root cause: Eu validei os campos estruturados de GMUD de forma fragmentada, respondendo por campo pedido, em vez de revisar o conjunto completo de evidências estruturadas da GMUD.
- Prevention rule: Ao validar cobertura GMUD, revisar sempre em bloco todos os canais estruturados relevantes (`IssueLink`, `Itens de Configuração`, `Cartões Relacionados`, rollback e links dedicados), não apenas o campo citado na rodada.
- Action added to workflow: Em qualquer ajuste/validação de GMUD, abrir primeiro o mapa completo de evidências estruturadas antes de concluir que a cobertura está correta.

- Date: 2026-04-10
- Context: Ajuste da aba `Throughput Breakdown` para alinhar tabela mensal e gráfico agregado.
- User correction: Informou que o gráfico de barras deveria refletir março, mas estava exibindo valores de um recorte incompatível com a tabela mensal.
- Root cause: Eu deixei o gráfico agregado calculado sobre todo o período filtrado, enquanto a nova tabela foi desenhada em granularidade mensal.
- Prevention rule: Quando uma nova visualização mensal for adicionada ao dashboard, revisar todos os gráficos vizinhos para garantir que usem a mesma granularidade temporal da leitura principal.
- Action added to workflow: Em mudanças de breakdown temporal, validar explicitamente `período inteiro` vs `mês corrente/selecionado` antes de encerrar.

- Date: 2026-04-10
- Context: Pedido para implementar um consolidado mensal por produto na aba `Throughput Breakdown`.
- User correction: Esclareceu que a alteração precisava ser feita no `dashboard_full.py`, não no exportador `dash_board_metricas.py`.
- Root cause: Eu associei `Throughput breakdown` à planilha/exportação por causa do layout de referência e não revalidei primeiro qual superfície do produto o usuário queria alterar.
- Prevention rule: Quando o usuário mencionar uma aba/tela do dashboard, confirmar primeiro o ponto de renderização em `dashboard_full.py` antes de implementar qualquer versão paralela em planilhas, exportadores ou scripts auxiliares.
- Action added to workflow: Em demandas com mockup de tabela/aba, validar explicitamente `dashboard vs workbook/export` antes de abrir a etapa de implementação.

- Date: 2026-04-07
- Context: Integração inicial da régua financeira de custos na aba de portfólio do dashboard.
- User correction: Esclareceu que não quer ler uma planilha externa no dashboard; quer que os dados de custo sejam gerados a partir da extração do Jira e de heurísticas/parâmetros que reproduzam a régua da planilha.
- Root cause: Eu foquei em trazer rapidamente a visualização da planilha para a UI, mas não reavaliei que a fonte desejada pelo usuário era o próprio pipeline analítico do produto, e não um arquivo manual de apoio.
- Prevention rule: Quando o usuário pedir indicadores no dashboard, priorizar sempre geração nativa via dados já extraídos e parâmetros configuráveis; só usar planilha externa como referência transitória se isso for explicitamente aceito.
- Action added to workflow: Em novas integrações financeiras/portfólio no dashboard, validar primeiro `fonte operacional nativa` versus `fonte auxiliar manual` antes de implementar a camada visual.

- Date: 2026-04-07
- Context: Classificação de status no resumo executivo de projetos.
- User correction: Esclareceu que `Cancelado` precisa ser diferente de `Done/Finalizado`.
- Root cause: Eu agrupei estados cancelados e concluídos no mesmo bucket terminal, o que perde uma distinção gerencial importante.
- Prevention rule: Em taxonomias de status executivo, nunca juntar `cancelado` e `concluido` no mesmo bucket sem confirmação explícita do usuário.
- Action added to workflow: Ao resumir status de portfólio/projeto, separar sempre pelo menos `BACKLOG`, `EM ANDAMENTO`, `FINALIZADO` e `CANCELADO` quando essas categorias existirem na origem.

- Date: 2026-04-07
- Context: Primeira versão da V2 do layout final de melhorias consolidou uma linha por colaborador no nível do produto, mas o usuário precisava identificar o épico/feature na própria linha.
- User correction: Esclareceu que, na V2, o `ID do Projeto` precisa ser o `Épico` e/ou `Feature`, e pediu também uma coluna final `Produto`.
- Root cause: Eu mantive a V2 agregada demais no nível do produto operacional e não reavaliei que o identificador de projeto, nesse contexto, precisava subir para o ativo de melhoria (`épico/feature`) e não ficar só no sistema (`BF`, `W1NNR`, `S1NC`, `DT`).
- Prevention rule: Quando o usuário pedir um identificador de projeto/ativo em um layout executivo, validar explicitamente o nível semântico esperado (`produto`, `epico`, `feature`, `historia`, `item`) antes de consolidar a saída.
- Action added to workflow: Em novas saídas CAPEX/portfólio, revisar sempre se a granularidade do layout final está no nível certo de gestão antes de encerrar a implementação.

- Date: 2026-04-07
- Context: Primeira versao do pipeline CAPEX simplificado entregou bases tecnicas, mas ainda faltava o layout final de negocio pedido pelo usuario.
- User correction: Reforcou que ainda precisava dos dados exatamente no formato `ID do Projeto`, `Descricao do Ativo`, `Colaborador`, `Data do Apontamento das Horas`, `Horas`, `Atividade Desenvolvida`.
- Root cause: Eu tratei as tabelas intermediarias como suficientes porque o modelo interno estava correto, mas nao projetei logo de inicio a camada final no schema executivo consumido pelo negocio.
- Prevention rule: Sempre que o usuario der um layout final explicito, gerar esse layout como artefato principal ou complementar obrigatorio, mesmo que o pipeline interno use tabelas mais ricas para rastreabilidade.
- Action added to workflow: Em novos pipelines analiticos, confirmar cedo `schema interno` versus `schema final de entrega` e validar ambos antes de encerrar a implementacao.

- Date: 2026-04-07
- Context: Redefinição da estratégia do CAPEX mensal após tentativas de extrair worklogs reais do Jira.
- User correction: Indicou que a abordagem baseada em worklogs estava complexa demais e direcionou para um modelo mais simples: extrair projetos/épicos e entregas realizadas, usar a distribuição mensal de pessoas por BU/projeto e estimar horas por tipo de entrega, com process mining em paralelo para calibração.
- Root cause: Eu persisti tempo demais numa rota de extração detalhada de worklogs antes de validar se um modelo operacional mais simples e aderente ao uso gerencial já resolveria o problema.
- Prevention rule: Quando o objetivo for alocação mensal executiva e já existir base de capacidade por pessoa/equipe, priorizar primeiro um modelo simples de estimativa por entregas e distribuição de horas antes de aprofundar integrações detalhadas de apontamento.
- Action added to workflow: Em novas iniciativas de CAPEX/planejamento, comparar explicitamente duas opções no início: `modelo simples por capacidade + entregas` versus `modelo detalhado por apontamentos`, e começar pela menor que entregue valor confiável.

- Date: 2026-04-07
- Context: Implementação inicial do exportador CAPEX mensal baseado em worklogs do Jira.
- User correction: Esclareceu que os épicos estão no board/projeto `BT` e as features também estão em `BT`, então a hierarquia de portfólio relevante para CAPEX está ancorada em `BT`.
- Root cause: Eu concentrei a primeira execução do CAPEX nos projetos operacionais e tratei a hierarquia BT apenas como enriquecimento implícito, sem revalidar se `BT` também precisava entrar explicitamente no escopo da coleta.
- Prevention rule: Quando a demanda envolver épicos/features para CAPEX ou portfólio, validar explicitamente em quais projetos/boards Jira essa hierarquia vive hoje e não assumir que ela está somente nos projetos operacionais.
- Action added to workflow: Em novas extrações CAPEX/portfólio, confirmar sempre o conjunto `projetos operacionais + projeto(s) de portfólio` antes de fechar a JQL e o escopo da coleta.

- Date: 2026-04-07
- Context: Correção do `WIP atual` na aba `Serviço e SLA` após divergência entre recorte por `DataDone` e `Data de criação`.
- User correction: Informou que, ao desmarcar o flag `Usar data de criação do card`, as abas `Work Item Age` e `WIP por Pessoa` também passavam a exibir mensagem de ausência de itens ativos.
- Root cause: Eu corrigi primeiro a semântica de base viva apenas no card de `WIP atual` de `Serviço e SLA`, mas deixei outras abas que também dependem de trabalho ativo (`Work Item Age` e `WIP por Pessoa`) ancoradas no `df` global já recortado por `DataDone`.
- Prevention rule: Sempre que eu corrigir uma métrica/aba baseada em WIP vivo, revisar no mesmo turno todas as outras abas que usam itens ativos (`WIP`, `WIP Age`, `Work Item Age`, `WIP por Pessoa`) para garantir que nenhuma continue dependente do recorte global por `DataDone`.
- Action added to workflow: Em mudanças ligadas ao flag `Usar data de criação do card`, executar checklist cruzado nas abas operacionais com trabalho vivo e validar explicitamente os modos `flag ligado` e `flag desligado`.
- Date: 2026-04-02
- Context: Primeira entrega do filtro multi-seleção de `Criador` no dashboard de serviços.
- User correction: Informou que o campo continuava desabilitado mesmo após atualizar a base, mostrando que o filtro não tinha ficado utilizável no cenário real.
- Root cause: Eu ancorei a habilitação do filtro apenas nas colunas presentes em `Fato_Items` do `PowerBI_Model`, ignorando que o metadado de `Criador` já existia no CSV downstream por projeto e poderia ser usado como fallback operacional.
- Prevention rule: Quando um filtro depender de metadado que pode existir no downstream mas não no modelo consolidado, não bloquear a UI só porque `Fato_Items` não trouxe a coluna; verificar fallback nas fontes auxiliares já consumidas pelo dashboard.
- Action added to workflow: Em novos filtros de metadados (`Criador`, `Reporter`, `labels`, datas de criação), validar sempre duas rotas antes de concluir: `modelo consolidado` e `downstream por projeto`.
- Date: 2026-03-31
- Context: Segunda iteração da leitura de cadência Weibull na aba `Serviço e SLA`.
- User correction: Apontou que `λ=22.7276d` e `λ=22.3702d` receberam cadências diferentes apesar de serem praticamente equivalentes, e pediu faixas explícitas de `1-5`, `5-10`, `10-15`, `15-20`, `20-25`, `25-30` e `>30` dias, com o rótulo `Cadência avaliada`.
- Root cause: Eu usei uma heurística aproximada com cortes vagos (`~ sprint de 2 semanas` vs `~ 1 mês`), o que criou um salto artificial na fronteira sem refletir a proximidade real dos valores de `λ`.
- Prevention rule: Quando o usuário pedir leitura operacional baseada em um parâmetro contínuo como `λ`, evitar buckets vagos com cortes implícitos; usar faixas explícitas e estáveis definidas em unidades reais.
- Action added to workflow: Em classificações heurísticas de métricas contínuas, testar sempre valores imediatamente abaixo e acima das fronteiras para confirmar que a troca de faixa faz sentido operacionalmente.
- Date: 2026-03-31
- Context: Inclusão da cadência Weibull na `Série semanal de apoio` da aba `Serviço e SLA`.
- User correction: Reportou traceback com `numpy.linalg.LinAlgError: SVD did not converge in Linear Least Squares` ao abrir a aba após eu passar a calcular Weibull por semana.
- Root cause: Eu reutilizei `fit_weibull_linearized(...)` corretamente no nível semântico, mas assumi que toda amostra semanal positiva seria numericamente estável para `np.polyfit`; semanas com poucos pontos repetidos ou base degenerada quebraram o ajuste linearizado.
- Prevention rule: Sempre que um ajuste estatístico opcional for aplicado em buckets pequenos (semana, pessoa, tipo, urgência), validar antes se a amostra é regressível e envolver a regressão em fallback defensivo que retorne `None` em vez de derrubar a UI.
- Action added to workflow: Em novos KPIs estatísticos por bucket, fazer smoke test explícito dos cenários `amostra vazia`, `amostra mínima`, `valores repetidos` e `amostra degenerada` antes de concluir.
- Date: 2026-03-31
- Context: Correção dos cards executivos do `Painel Fluxo` após usuário apontar ausência das unidades em indicadores temporais.
- User correction: Informou que indicadores como `Tempo para Commit (P85)` e `WIP Age (médio)` estavam sem unidade visível (`dias`, `semanas`, etc.).
- Root cause: Eu mantive o campo `unit` no `metric_catalog`, mas a renderização dos cards executivos ignorava esse metadado e mostrava apenas título + valor.
- Prevention rule: Sempre que um KPI tiver unidade semântica relevante, validar na UI final se essa unidade aparece visivelmente no card, e não apenas no backend/configuração da métrica.
- Action added to workflow: Em qualquer ajuste de KPIs/cards, revisar explicitamente o trio `rótulo`, `valor` e `unidade` com foco em legibilidade operacional antes de concluir.
- Date: 2026-03-30
- Context: Ajuste visual do histograma de Lead Time após girar os rótulos das linhas de referência para vertical.
- User correction: Informou que, após a rotação dos rótulos, o título do gráfico passou a ser sobrescrito e pediu o título centralizado com mais espaçamento vertical.
- Root cause: Eu corrigi a orientação dos rótulos, mas não reequilibrei o espaço vertical do layout do gráfico; mantive a margem superior curta e o título sem posicionamento explícito.
- Prevention rule: Em ajustes de anotações dentro de gráficos, validar o conjunto completo de layout do cabeçalho após a mudança, incluindo alinhamento do título, margem superior e colisão com labels.
- Action added to workflow: Sempre que eu alterar `annotation_text*` ou `annotation_position` em gráficos Plotly, revisar também `title` e `margin.t` antes de concluir.
- Date: 2026-03-30
- Context: Segunda iteração visual da aba `Work Item Age` após trocar o hero escuro por fundo claro.
- User correction: Informou que a composição ainda estava desproporcional, com o primeiro painel ocupando espaço vertical demais em relação aos demais.
- Root cause: Eu corrigi cor e contraste, mas mantive a mecânica de distribuição vertical do card principal, preservando um vazio interno incompatível com a densidade dos outros painéis.
- Prevention rule: Quando houver um painel principal ao lado de grids de KPIs, comparar não só cor e tamanho externo, mas também a densidade interna de conteúdo e o uso real do espaço vertical.
- Action added to workflow: Em revisões de layout com múltiplos painéis paralelos, inspecionar explicitamente se algum bloco está “esticado” por `flex`/`space-between` ou por ausência de conteúdo equivalente antes de concluir.
- Date: 2026-03-30
- Context: Primeira refatoração visual dos KPIs da aba `Work Item Age`.
- User correction: Informou que a nova composição ficou desproporcional, sem padrão visual com o restante do dashboard e com preferência por fundo claro.
- Root cause: Eu forcei hierarquia visual demais com um bloco hero escuro e pesos muito diferentes entre os cards, sem preservar suficientemente o padrão visual já dominante da aplicação.
- Prevention rule: Em refatorações de layout de dashboards existentes, priorizar primeiro consistência visual e proporção entre cards; só introduzir blocos de alto contraste ou hero panels quando isso for explicitamente pedido.
- Action added to workflow: Em mudanças visuais não triviais, revisar a proposta contra o padrão atual da aplicação antes de concluir, validando especialmente fundo, contraste e equilíbrio proporcional dos KPIs.
- Date: 2026-03-20
- Context: Implementação de login Google OAuth no dashboard Dash/Flask com Google Workspace.
- User correction: O claim `hd` retornado para `@w1consultoria.com.br` é `w1consultoria.com.br`, não `w1.com.br` — validação de domínio por `hd == allowed_domain` bloqueava usuários válidos do Workspace com e-mails em domínios secundários.
- Root cause: Assumi que o claim `hd` sempre retorna o domínio primário do Workspace para todos os usuários. Na prática, o `hd` reflete o domínio do e-mail do usuário, não o domínio primário da organização.
- Prevention rule: Em Workspaces com múltiplos domínios (`w1.com.br`, `w1consultoria.com.br`, `w1technology.com.br`), não comparar `hd == domínio_primário`. Usar `hd` apenas para distinguir contas Workspace de contas Gmail pessoais (verificar `hd` não vazio). O controle de acesso real deve ser feito pela allowlist de e-mails ou checagem de grupo.
- Action added to workflow: Em implementações OAuth com Workspace multi-domínio, validar o fluxo com uma conta de cada domínio antes de concluir. Checar documentação do Google sobre `hd` em organizações multi-domínio.
- Date: 2026-03-20
- Context: Configuração do exportador Jira -> BusinessMap para usar `BUSINESSMAP_SPLIT_SIZE=100` e outros defaults via `jira_env.txt`.
- User correction: Informou que os arquivos não estavam sendo gerados em lotes de 100, apesar da configuração já ter sido adicionada no `jira_env.txt`.
- Root cause: Eu assumi que bastava definir o valor no `jira_env.txt`, mas o `argparse` lia os defaults de `os.getenv(...)` antes do `load_env_file(...)`; portanto, os defaults vindos do arquivo não eram aplicados à CLI.
- Prevention rule: Quando argumentos de CLI usam defaults vindos de env file, carregar o arquivo antes de construir o parser principal ou validar com uma execução real que o default entrou em vigor.
- Action added to workflow: Em qualquer ajuste baseado em `jira_env.txt`/`.env`, verificar explicitamente a ordem de bootstrap (`load_env_file` vs `argparse`) e confirmar o efeito com uma execução real, não só com leitura estática do código.
- Date: 2026-03-12
- Context: Movimentação dos relatórios Bitbucket/capacidade cruzada da aba `Performance do Serviço` para `Produtividade Dev`.
- User correction: Informou que os relatórios saíram da aba antiga, mas não apareceram na aba `Produtividade Dev`.
- Root cause: Eu movi a renderização para dentro do fluxo principal da aba de produtividade, mas mantive retornos antecipados que encerravam a aba antes do bloco novo ser exibido quando não havia dados de produtividade individual.
- Prevention rule: Ao mover blocos entre abas, revisar todos os `return` antecipados do destino e garantir que o novo bloco continue visível nos estados vazios/degradados relevantes.
- Action added to workflow: Em mudanças de navegação/layout, validar explicitamente o cenário `com dados` e `sem dados da seção principal` para confirmar que blocos movidos continuam renderizando.
- Date: 2026-03-12
- Context: Nomeação dos novos cards de fluxo ao separar backlog, WIP e estoque total no `Painel Fluxo`.
- User correction: Apontou que `WIP em progresso` é pleonástico, porque `WIP` já significa `Work In Progress`.
- Root cause: Ao tentar tornar o card autoexplicativo, eu expandi a sigla sem checar que a própria expansão já está embutida no termo operacional usado na área.
- Prevention rule: Em métricas de fluxo, não expandir siglas consagradas de forma redundante (`WIP em progresso`, `Lead Time de tempo`, etc.); preferir o termo canônico do domínio.
- Action added to workflow: Ao revisar nomenclatura de KPIs, validar se o rótulo ficou semanticamente mais claro sem duplicar o significado técnico da sigla.
- Date: 2026-03-12
- Context: Primeira correção do KPI `Tempo para Commit (P85)` no Painel Fluxo após usuário reportar que o valor seguia zerado no cenário real do print.
- User correction: Mostrou que, mesmo após ajustar o default, o KPI continuava `0` porque o filtro ativo ainda incluía explicitamente `Backlog` e `Triagem`.
- Root cause: Eu corrigi apenas a heurística padrão das etapas, mas mantive o cálculo do KPI dependente da menor data selecionada (`LeadStart_Selected`), o que continua colapsando em zero quando backlog-like stages permanecem selecionadas pelo usuário.
- Prevention rule: Quando um KPI usa um subconjunto semântico do mesmo filtro de lead time, validar não só o default do filtro, mas também o comportamento com combinações explícitas que incluam etapas iniciais (`Backlog`, `Triagem`, etc.).
- Action added to workflow: Em ajustes de métricas baseadas em workflow selecionável, sempre reproduzir o cenário real do usuário com a seleção exata das etapas antes de concluir a correção.
- Date: 2026-03-09
- Context: Ajuste da governança de `Expedite` após orientação sobre prioridade `HIGEST`.
- User correction: Pediu que itens classificados com prioridade `HIGEST` fossem tratados como `Expedite`.
- Root cause: A governança de expedite dependia principalmente de `ClasseServico`, e eu não havia alinhado totalmente essa leitura com a variação ortográfica real de prioridade usada nos dados.
- Prevention rule: Quando a regra de urgência depender de prioridade, cobrir explicitamente as variações ortográficas reais observadas no ambiente (`highest`, `higest`, etc.) na resolução canônica.
- Action added to workflow: Em toda regra de classificação operacional baseada em prioridade, validar aliases e typos conhecidos antes de concluir a implementação.
- Date: 2026-03-09
- Context: Correção da aba `Padrões Sistêmicos` após erro em runtime com `KeyError: 'Severidade'`.
- User correction: Reportou traceback mostrando que a aba tentava acessar `details['Severidade']` quando não havia ocorrências de padrões.
- Root cause: Eu tratei o caso vazio no fluxo principal da aba, mas mantive `detect_systemic_patterns(...)` retornando `DataFrame()` sem schema, o que deixou o consumo frágil em acessos por coluna.
- Prevention rule: Helpers que retornam `DataFrame` para consumo por UI devem devolver colunas estáveis mesmo no caso vazio; na camada de renderização, acessos a colunas críticas também devem ser defensivos.
- Action added to workflow: Em qualquer tabela/gráfico novo, validar explicitamente dois cenários no smoke test: `com dados` e `sem linhas`, verificando schema e renderização.
- Date: 2026-03-09
- Context: Ajuste do checklist semanal automatizado para leitura de `WIP`.
- User correction: Indicou que a regra anterior não era operacionalmente adequada e pediu avaliação configurável de `WIP por pessoa`, usando `2 itens por pessoa` como referência inicial.
- Root cause: Eu havia usado uma banda histórica agregada de `WIP`, que pode normalizar cenários evidentemente anômalos em times pequenos.
- Prevention rule: Para alertas de `WIP` operacional, preferir limites ancorados em capacidade explícita do time (`itens por pessoa`, `limite por estágio`, etc.) em vez de apenas bandas históricas agregadas.
- Action added to workflow: Em qualquer checklist de fluxo com `WIP`, validar primeiro se existe uma regra de capacidade mais interpretável pelo usuário antes de recorrer a referência histórica.
- Date: 2026-03-09
- Context: Priorização de backlog após análise de lacunas de métricas de fluxo com base nos artefatos da Cristiane Goncalves.
- User correction: Informou que `Monte Carlo` não será implementado; `SLE` é apenas possibilidade; o foco deve ficar no restante das métricas operacionais de fluxo.
- Root cause: Eu mantive `Monte Carlo` no topo da priorização por aderência ao material de referência, sem ajustar a recomendação à direção explícita de escopo do usuário.
- Prevention rule: Quando o usuário delimitar o backlog por preferência de implementação, tratar imediatamente os itens excluídos como fora de escopo, mesmo que sejam recomendados por frameworks ou materiais externos.
- Action added to workflow: Em revisões de gap/backlog, separar sempre `recomendado pela referência` de `escopo decidido pelo usuário` antes de priorizar próximos passos.
- Date: 2026-03-06
- Context: Diagnóstico do snapshot de portfólio após validar ausência de `ParentID`/`EpicLinkID` no CSV gerado.
- User correction: Esclareceu que as `features` agora estão no mesmo space de portfólio, no mesmo projeto `BT`.
- Root cause: Eu mantive como hipótese principal um problema de relacionamento entre spaces/projetos, sem considerar que a estrutura já havia sido consolidada no mesmo projeto `BT`.
- Prevention rule: Antes de atribuir ausência de hierarquia a fronteiras entre projetos/spaces, confirmar com o usuário ou com a configuração atual do Jira se os níveis já foram unificados no mesmo projeto.
- Action added to workflow: Em diagnósticos de portfólio, validar primeiro a topologia real (`epics/features` no mesmo projeto ou não) e só depois inferir causa para campos de vínculo vazios.
- Date: 2026-04-02
- Context: Orientação de comando para exportação BusinessMap com hierarquia entre épicos, features e histórias.
- User correction: Informou que existe um projeto/space no Jira só de épicos e outro de features, e que esse fluxo já havia sido exportado antes.
- Root cause: Eu me apoiei demais numa lição anterior sobre `features` no mesmo projeto `BT` sem revalidar se aquele contexto continuava valendo para este fluxo específico de exportação BusinessMap.
- Prevention rule: Quando houver histórico conflitante sobre topologia Jira (`mesmo projeto` vs `spaces separados`), confirmar o contexto operacional mais recente do fluxo atual antes de prescrever JQL/comandos.
- Action added to workflow: Em comandos de exportação Jira -> BusinessMap envolvendo portfólio, revisar sempre os projetos/space keys efetivos do fluxo pedido no momento antes de sugerir `--projects` ou `--jql`.
- Date: 2026-04-02
- Context: Geração dos pacotes finais para importação BusinessMap após o usuário pedir a exportação de épicos, features e BeFinance.
- User correction: Informou que os arquivos precisavam ser gerados separados, porque cada conjunto pertence a um quadro diferente no BusinessMap.
- Root cause: Eu foquei primeiro na completude da hierarquia e acabei propondo um XLSX consolidado, sem respeitar a separação operacional por quadro de destino.
- Prevention rule: Em exportações para ferramentas com múltiplos boards/quadro de destino, confirmar sempre se a separação é por tipo/projeto/fluxo antes de consolidar em um único arquivo.
- Action added to workflow: Em toda exportação BusinessMap, validar explicitamente a granularidade de saída esperada (`um arquivo só` vs `arquivos separados por quadro`) antes de executar a geração final.
- Date: 2026-03-06
- Context: Ajuste de nomenclatura do indicador de pendências na aba de Portfólio.
- User correction: Apontou que `Q1/Q2/Q3 Pendências` conflita semanticamente com `Quarter`, gerando leitura ambígua na mesma tela.
- Root cause: Reusei a letra `Q` para buckets de aging sem considerar que o módulo já usa `Q1/Q2/Q3/Q4` para quarter do roadmap.
- Prevention rule: Em telas que já usam `Quarter`, não reutilizar `Q1/Q2/Q3` para outra taxonomia; preferir rótulos funcionais explícitos.
- Action added to workflow: Ao nomear novos indicadores em dashboards, validar colisões de vocabulário com filtros, legendas e eixos já existentes na mesma aba.
- Date: 2026-03-06
- Context: Correção dos filtros da tela de Portfólio após regressão em que só `Quarter` filtrava corretamente.
- User correction: Esclareceu que o filtro da tela deve ser aplicado sobre a coluna `Team` da base de portfólio, não sobre a coluna `Projeto`.
- Root cause: Eu assumi que o filtro global `Projeto` do dashboard deveria casar com `Projeto` também no CSV de portfólio, sem validar a semântica real usada nessa tela.
- Prevention rule: Em telas que usam uma base diferente da base principal, validar no dataset real qual coluna sustenta cada filtro visível antes de implementar o recorte.
- Action added to workflow: Em bugs de filtro, sempre conferir o par `controle da UI -> coluna real da fonte` com uma amostra concreta do CSV/planilha antes de fechar a correção.
- Date: 2026-03-06
- Context: Correção de publicação de artefatos `latest` no macOS após log com caminho híbrido `.../flow-pmo/C:\Users\...`.
- User correction: Pediu que no macOS os aliases fossem gerados em `/Users/rodrigoalmeidadeoliveira/Documents/dados/latest`, sem impactar o fluxo já funcional no Windows.
- Root cause: A resolução de `FLOW_PMO_LATEST_DIR` aceitava cegamente um valor Windows mesmo em runtime macOS, produzindo caminho inválido; além disso o fallback do script macOS apontava para a pasta do projeto em vez de `~/Documents/dados/latest`.
- Prevention rule: Em variáveis de diretório cross-platform, validar se o formato do path é compatível com o SO atual antes de usá-lo; no macOS, nunca reutilizar caminho Windows como override válido.
- Action added to workflow: Sempre testar resolução de diretório com três casos ao mexer em publicação de artefatos: sem env, env nativo válido e env de outro SO.
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

- Date: 2026-03-19
- Context: Execução do `run_process_mining_projects.ps1` falhou com mensagem genérica no primeiro projeto, apesar de o `jira_to_pipeline_csv.py` ter concluído com sucesso e gerado os artefatos.
- User correction: Compartilhou a saída completa mostrando que o CSV e o changelog detalhado foram gerados antes do throw do runner.
- Root cause: A função PowerShell que encapsulava os scripts Python retornava o `exit code`, mas também deixava o stdout do comando seguir pelo success stream; ao atribuir o resultado da função, o caller recebia um array com logs + `0` e interpretava isso como falha.
- Prevention rule: Em wrappers PowerShell que retornam `exit code`, nunca deixar stdout/stderr da chamada nativa compor o valor retornado quando o caller faz atribuição; enviar logs para `Host` e retornar apenas o inteiro final.
- Action added to workflow: Ao criar helpers `Invoke-*` para comandos nativos no PowerShell, validar explicitamente dois cenários: `resultado atribuído a variável` e `resultado não atribuído`, confirmando que o retorno lógico continua sendo apenas o `exit code`.

- Date: 2026-04-09
- Context: Renomeação do filtro principal de `Projeto` para `Time` no `dashboard_full.py`.
- User correction: Apontou que eu alterei apenas o rótulo externo do campo e deixei a opção padrão do dropdown ainda como `Todos os projetos`.
- Root cause: Tratei a mudança como puramente visual no `html.Label(...)` e não percorri os textos dependentes do mesmo componente, especialmente o label global reutilizado nas opções.
- Prevention rule: Quando renomear um filtro na UI, revisar conjuntamente `label do campo`, `opção padrão/all`, `placeholders` e quaisquer labels auxiliares do mesmo componente antes de concluir.
- Action added to workflow: Em ajustes textuais de filtros/dropdowns, executar sempre uma busca pelos labels relacionados e validar a consistência completa do componente, não só do título visível.

- Date: 2026-04-09
- Context: Classificação de `Cost of Delay` entre `Upstream` e `Downstream` na aba `Process Mining & CAPEX`.
- User correction: Esclareceu que as etapas upstream reais incluem o fluxo de épicos/features e colunas de triagem dos fluxos de serviço, com status como `Em Product Discovery`, `Backlog do Produto`, `Priorized/Prioritized`, `In Discovery`, `Ready to Design`, `In Design`, `Definition`, `Planning`, `Design`, `Replenishment`, `Quebra das Histórias`, `Backlog` e `Triagem`.
- Root cause: Eu modelei `Upstream` com uma heurística genérica de fila pré-desenvolvimento sem fechar a taxonomia contra os nomes exatos usados hoje nos quadros e colunas operacionais do time.
- Prevention rule: Em classificações de etapas de fluxo para métricas executivas, não assumir buckets genéricos; validar e codificar explicitamente os status reais mostrados no board atual do usuário antes de concluir.
- Action added to workflow: Ao ajustar taxonomias de fluxo (`upstream/downstream`, `execução/espera`, `planejamento/entrega`), revisar sempre prints/nomes reais de colunas e refletir esses labels explicitamente na função classificadora.

- Date: 2026-04-09
- Context: Refinamento da fronteira entre `Upstream` e `Downstream` no `Cost of Delay`.
- User correction: Esclareceu que etapas como `Staging`, `Ready for Production`, `Ready to Staging`, `Ready for Testing/QA`, `Ready to Homolog` e `Ready for Homolog` ainda pertencem ao `Upstream` da empresa (equipe de produto), e que no nível estratégico de épicos o `Downstream` começa apenas a partir de `Ready to Delivery`.
- Root cause: Eu ainda estava ancorando parte da taxonomia em uma visão genérica de pós-desenvolvimento, em vez da fronteira organizacional real entre upstream de produto e downstream estratégico.
- Prevention rule: Em métricas de fluxo estratégicas, classificar `Upstream` e `Downstream` pela fronteira organizacional/gerencial definida pelo usuário, não por uma interpretação genérica de SDLC.
- Action added to workflow: Quando o usuário explicitar a fronteira organizacional entre áreas do fluxo, refletir isso diretamente nos tokens e revisar os labels mais parecidos que possam cair no bucket errado.

- Date: 2026-04-09
- Context: Ajuste fino da taxonomia entre `backlog` e `backlog do produto` no `Cost of Delay`.
- User correction: Esclareceu que `backlog` e `in progress` são etapas de `Downstream`, enquanto `backlog do produto` continua representando etapa de `Upstream`.
- Root cause: Eu estava tratando o token genérico `backlog` como se sempre significasse backlog de produto, sem separar o backlog do board downstream do backlog estratégico de produto.
- Prevention rule: Quando um status genérico aparece em mais de um contexto organizacional, não classificá-lo por substring ampla sem preservar explicitamente as exceções mais específicas do fluxo real.
- Action added to workflow: Em taxonomias por tokens, revisar sempre conflitos entre rótulos genéricos (`backlog`, `design`, `review`) e rótulos específicos (`backlog do produto`, `ready to design`) antes de concluir a classificação.

- Date: 2026-04-09
- Context: Integração do `Cost of Delay` com a camada estratégica BT (épicos/features/histórias).
- User correction: Indicou que há 76 épicos em `Ready to Delivery` no board estratégico BT, apesar de o snapshot local `portfolio-bt-ns-latest-data.csv` do workspace não refletir esse status no momento.
- Root cause: Eu poderia assumir que ausência no artefato local significava ausência no fluxo real, mas o board e o snapshot publicado nem sempre estão no mesmo frescor temporal.
- Prevention rule: Quando o usuário afirmar contagens/status atuais do board que divergem do CSV local, tratar isso como potencial defasagem de artefato e implementar a leitura para a próxima carga, em vez de concluir que o status “não existe”.
- Action added to workflow: Em integrações entre board Jira e snapshots latest, sempre validar separadamente `semântica implementada` e `frescor do artefato local/publicado`.

- Date: 2026-04-09
- Context: Investigação do snapshot BT sem `Ready to Delivery`, apesar do board estratégico mostrar essa coluna com épicos.
- User correction: Esclareceu que a referência correta para esse estágio estratégico é a coluna do board BT (`project = BT AND issuetype = Epic`), não necessariamente o `status.name` cru retornado pela search API.
- Root cause: Eu poderia tratar `Status` exportado no CSV como equivalente à coluna visível do board, mas o exportador atual salva apenas `fields.status.name` e não consulta a configuração/agregação da board Agile.
- Prevention rule: Quando o usuário fizer referência a uma coluna específica de board Jira, não assumir equivalência com `issue.status`; validar cedo se a fonte atual lê `status` puro ou metadados da board.
- Action added to workflow: Em investigações envolvendo divergência entre board e snapshot Jira, sempre comparar explicitamente `JQL do exportador`, `campo exportado` e `semântica da board/coluna` antes de concluir.

- Date: 2026-04-09
- Context: Ajuste da camada estratégica BT no `Cost of Delay` após confirmar o mapeamento real do board.
- User correction: Confirmou que, no board estratégico BT, a coluna `Ready to Delivery` mapeia o status cru `Triagem`.
- Root cause: Eu ainda estava usando o `Status` cru do snapshot estratégico diretamente no dashboard, sem aplicar a tradução de coluna de board já conhecida para o fluxo BT.
- Prevention rule: Quando um board Jira usa colunas de negócio que agrupam statuses crus, aplicar a tradução na camada analítica antes de exibir fase/direção executiva.
- Action added to workflow: Em visões analíticas estratégicas BT, revisar sempre se a fase exibida deve vir de `status.name` ou de um mapeamento de coluna de board acordado com o usuário.

- Date: 2026-04-09
- Context: Refino da taxonomia do `Cost of Delay` para o estágio estratégico `Ready to Delivery`.
- User correction: Reforçou que `Ready to Delivery` deve ser tratado como `Downstream` no modelo de custo de atraso.
- Root cause: Embora a heurística já cobrisse esse token, a regra ainda estava implícita dentro de uma lista ampla e podia ficar opaca em futuras revisões da taxonomia.
- Prevention rule: Quando uma etapa estratégica for central para a leitura executiva, preferir uma regra explícita no classificador em vez de depender apenas de matching genérico por tokens.
- Action added to workflow: Em taxonomias executivas com forte semântica de negócio, promover os estágios críticos para branches explícitos e validar o resultado com smoke test direcionado.

- Date: 2026-04-09
- Context: Classificação das colunas percentuais (`0%`, `20%`, `40%`, `60%`, `80%`, `100%`) do fluxo de épicos estratégico no `Cost of Delay`.
- User correction: Esclareceu que essas colunas de `% de avanço` pertencem ao `Downstream`, embora estivessem aparecendo em `Upstream` no gráfico.
- Root cause: O classificador tratava esses rótulos percentuais como casos desconhecidos e caía no bucket default `Upstream`.
- Prevention rule: Quando um board estratégico usar etapas percentuais como fases explícitas do fluxo, classificá-las por regra dedicada em vez de deixá-las cair no default.
- Action added to workflow: Em taxonomias de fluxo BT, revisar sempre status percentuais e outros rótulos curtos/sintéticos que não casam com tokens textuais tradicionais.

- Date: 2026-04-09
- Context: Primeira publicação da aba `Cobertura GMUD` no dashboard usando os artefatos `gmud-coverage-*`.
- User correction: Reportou que em produção os CSVs GMUD não eram encontrados, porque a aba exigia `FLOW_PMO_GMUD_*` dedicadas ou arquivos locais e não reaproveitava a mesma base pública já usada pelos outros artefatos latest.
- Root cause: Eu validei o loader com envs explícitas e arquivos sintéticos, mas não fechei a última milha de deploy para o ambiente Vercel, onde a convenção operacional é derivar vários artefatos a partir de um mesmo blob/base pública.
- Prevention rule: Quando eu adicionar um novo artefato latest consumido pelo dashboard, preciso validar também a estratégia de descoberta remota em produção e não apenas o caminho local ou por env explícita.
- Action added to workflow: Em novas integrações de CSV/XLSX remotos, sempre revisar se o loader herda a convenção de URL/base pública já adotada pelo dashboard antes de concluir a entrega.

- Date: 2026-04-09
- Context: Após o ajuste do fallback automático de GMUD, a produção continuou exibindo a mensagem antiga de erro.
- User correction: Indicou que, mesmo com os arquivos carregados, a instância em produção seguia mostrando o texto anterior sem o trecho novo de descoberta automática.
- Root cause: Eu foquei na correção de código e na validação local, mas não evidenciei logo de saída que o projeto usa deploy manual na Vercel e que mensagens antigas em produção são um forte sinal de build ainda não publicado.
- Prevention rule: Quando eu corrigir comportamento de runtime em um projeto com deploy manual, devo sempre comparar o texto/assinatura visível em produção com o código atual para distinguir rapidamente `bug de lógica` de `deploy desatualizado`.
- Action added to workflow: Em incidentes de produção após mudanças de dashboard, verificar cedo `mensagem atual no código`, `modo de deploy` e `última publicação` antes de concluir que a lógica nova não funcionou.

- Date: 2026-04-09
- Context: Primeira versão da cobertura GMUD cruzou `CHG` apenas por links explícitos e por menções diretas a chaves Jira.
- User correction: Mostrou no dashboard que nenhuma GMUD estava sendo relacionada às entregas, apesar de existirem tickets `CHG` válidos.
- Root cause: Eu assumi que as GMUDs citariam `issue keys` diretamente (`W1NNR-123`, `S1NC-456`, etc.), mas na prática os tickets `CHG` desta operação descrevem a mudança majoritariamente em linguagem natural no `summary/description`.
- Prevention rule: Em correlações entre change requests e itens de entrega, não presumir que a rastreabilidade virá sempre por chave explícita; validar cedo se a origem usa texto natural e preparar uma camada controlada de similaridade semântica/título.
- Action added to workflow: Em novos cruzamentos Jira x change management, amostrar tickets reais do projeto de mudanças antes de fechar a régua de matching, checando `links`, `issue keys`, `texto livre` e `comentários`.

- Date: 2026-04-09
- Context: Após a primeira correção de matching por similaridade, o usuário trouxe o exemplo do `CHG-33`, onde as chaves reais estavam visíveis no Jira mas ainda não apareciam no pipeline.
- User correction: Mostrou que o ticket continha links explícitos para `S1NC-2020`, `S1NC-1951` e `S1NC-2057` junto do plano de rollback.
- Root cause: Eu concentrei a extração em `summary`, `description`, `issuelinks` e `comment`, mas não considerei que a operação estava registrando a rastreabilidade em `customfield_*` ricos e ADF com links fora do payload básico do search.
- Prevention rule: Em tickets Jira com campos ricos operacionais (implantação, rollback, evidências), não assumir que o `search` com campos básicos é suficiente; validar o JSON completo de uma issue real antes de concluir que a informação não existe.
- Action added to workflow: Em integrações Jira baseadas em ADF/rich text, sempre testar um caso real com `get_issue(..., fields=*all)` para mapear `customfield_*`, `marks.link`, `inlineCard` e demais nós onde links podem ficar escondidos.

- Date: 2026-04-09
- Context: Expansão da cobertura GMUD para os blocos visuais `Linked work items`, `Key details` e `Itens de Configuração`.
- User correction: Pediu explicitamente para pesquisar também nesses campos estruturados da GMUD, não só em comentário e texto geral.
- Root cause: Mesmo após enriquecer a extração de texto, eu ainda tratava parte desses dados como texto genérico, sem elevá-los a uma fonte estruturada explícita no modelo de correlação.
- Prevention rule: Quando a UI do Jira evidencia blocos estruturados de rastreabilidade, modelá-los explicitamente no pipeline com nomes e semântica próprios, em vez de depender apenas de um corpus textual agregado.
- Action added to workflow: Em integrações futuras com Jira Service Management/Change, sempre mapear a tela para a API em três camadas: `links nativos`, `custom fields estruturados` e `texto livre`.

- Date: 2026-04-13
- Context: Inclusão do novo filtro `Tipo original Jira` na barra principal do dashboard.
- User correction: Esclareceu que o filtro novo precisava permitir `Todos`, um ou múltiplos tipos selecionados, e não somente seleção única.
- Root cause: Eu repliquei o padrão visual mais simples do filtro anterior e não reavaliei a interação completa esperada para o novo controle antes de fechar a primeira versão.
- Prevention rule: Quando o usuário pedir um novo filtro em tela, confirmar na primeira implementação se ele precisa suportar `todos`, seleção única e multiseleção, em vez de assumir modo simples.
- Action added to workflow: Em novas mudanças de filtros, revisar explicitamente `opção todos`, `multi-select` e `resumo textual do escopo` antes de concluir.

- Date: 2026-04-13
- Context: Ajuste do indicador semanal `Demanda de Falha x Demanda de Valor` após inclusão do filtro `Tipo original Jira`.
- User correction: Esclareceu que o indicador precisava respeitar o filtro novo e usar a taxonomia original do Jira: `Épico/Feature/História` como valor, `Bug/Suporte/Outro` como falha e `Task` fora da conta.
- Root cause: Eu mantive o cálculo legado baseado em `TipoDemanda`, que não refletia a semântica do filtro novo nem excluía `Task` do denominador.
- Prevention rule: Quando um novo filtro introduzir uma taxonomia mais granular, revisar imediatamente KPIs derivados que ainda dependem da classificação agregada anterior.
- Action added to workflow: Em toda mudança de taxonomia/filtro, auditar explicitamente métricas percentuais e breakdowns que usam buckets de classificação antes de encerrar.
