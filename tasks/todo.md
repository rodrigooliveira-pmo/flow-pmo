# Task Plan

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
