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
- Summary: Gargalos agora são gravados na aba `Fato_Gargalos` do `PowerBI_Model_*.xlsx` e o dashboard lê essa aba como fonte primária.
- Risks:
  - Se o modelo em produção não for atualizado, dashboard continuará no fallback legado.

## Review
- What was validated:
  - Sintaxe dos módulos Python alterados.
  - Sintaxe do script bash de orquestração.
  - Diff revisado para garantir prioridade da planilha com fallback preservado.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dash_board_metricas.py dashboard_full.py api/index.py`
  - `bash -n run_all_projects_macos.sh`
  - `git diff -- dash_board_metricas.py dashboard_full.py DEPLOY_VERCEL.md tasks/todo.md`
- Open issues:
  - Arquivos `.pyc` em `__pycache__/` continuam marcados no git neste ambiente (não bloqueia funcionalidade).
