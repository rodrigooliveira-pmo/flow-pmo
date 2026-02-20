# Task Plan

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
