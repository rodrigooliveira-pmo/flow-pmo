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
