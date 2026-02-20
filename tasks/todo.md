# Task Plan

## Current Task
- [x] Define scope and write detailed specification
- [x] Validate plan before implementation
- [x] Implement minimal-impact changes
- [x] Verify behavior (tests/logs/diff)
- [x] Review for elegance and root-cause quality

## Specification
- Objetivo: preparar o projeto para deploy manual na Vercel (Hobby), sem integração CI/CD por commit, com carga de dados compatível com ambiente serverless.
- Restrições: manter impacto mínimo no código do dashboard; não alterar regras de negócio do app.
- Entregáveis:
  - Entrada WSGI para Vercel em `api/index.py`.
  - Configuração `vercel.json` sem auto deploy por commit.
  - Resolver de arquivo de modelo no `dashboard_full.py` compatível com Vercel:
    - caminho por env var,
    - URL por env var (download em `/tmp`),
    - busca em diretórios configuráveis.
  - Busca de CSVs auxiliares em múltiplos diretórios configuráveis.
  - Guia de deploy/manual e variáveis no `DEPLOY_VERCEL.md`.
- Validação:
  - Compilar os arquivos Python alterados.
  - Validar JSON do `vercel.json`.
  - Validar import da entrada `api/index.py`.

## Progress Notes
- Date: 2026-02-20
- Summary: Deploy manual e carga de dados serverless configurados; app agora suporta modelo por caminho local, URL e múltiplas pastas de dados no runtime da Vercel.
- Risks:
  - Sem definir ao menos `FLOW_PMO_MODEL_FILE` ou `FLOW_PMO_MODEL_URL` (ou sem arquivo `PowerBI_Model_*.xlsx` disponível em pasta buscada), o app continuará em fallback de inicialização.

## Review
- What was validated:
  - Sintaxe dos módulos Python alterados.
  - JSON de configuração da Vercel.
  - Entrada WSGI carregando com fallback seguro quando o modelo não está disponível.
- Evidence (tests/logs/diff):
  - `python3 -m py_compile dashboard_full.py api/index.py`
  - `python3 -m json.tool vercel.json >/dev/null`
  - `python3 - <<'PY' ... import api.index ... print(type(entry.app).__name__) ... PY` retornando `Flask`.
- Open issues:
  - Publicar o arquivo de modelo em storage/URL acessível e configurar a variável na Vercel.
