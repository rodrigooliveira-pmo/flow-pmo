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
