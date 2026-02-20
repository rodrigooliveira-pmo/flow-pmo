# Deploy manual na Vercel (sem CI/CD por commit)

## O que foi configurado
- Entrada Python para Vercel em `api/index.py`.
- `vercel.json` com `git.deploymentEnabled = false` (sem auto deploy por commit em qualquer branch).
- Tempo máximo da função Python definido em 300s.

## Como publicar quando quiser
1. Instale a CLI da Vercel (uma vez):
   - `npm i -g vercel`
2. Faça login (uma vez):
   - `vercel login`
3. Deploy de preview manual:
   - `vercel`
4. Deploy de produção manual:
   - `vercel --prod`

## Variáveis opcionais
- App:
  - `FLOW_PMO_DASH_MODULE` (default: `dashboard_full`)
  - `FLOW_PMO_DASH_ATTR` (default: `app`)
- Dados:
  - `FLOW_PMO_MODEL_FILE`: caminho do modelo `.xlsx` (absoluto ou relativo ao projeto).
  - `FLOW_PMO_MODEL_URL`: URL pública para baixar o modelo `.xlsx` em runtime.
  - `FLOW_PMO_DASHBOARD_OUTPUT_FILE`: caminho do `dashboard_output_*.xlsx`.
  - `FLOW_PMO_DASHBOARD_OUTPUT_URL`: URL pública para baixar o `dashboard_output_*.xlsx` em runtime.
  - `FLOW_PMO_DATA_DIR`: pasta principal para buscar arquivos de dados.
  - `FLOW_PMO_DATA_DIRS`: lista de pastas separadas por `:` (Linux/macOS) para busca de CSVs auxiliares.
  - `DATA_FOLDER`: compatibilidade com configuração legada.

Use essas variáveis no projeto da Vercel para trocar módulo/objeto Dash e fonte de dados sem alterar código.

## Valores que você já pode configurar agora
- Modelo principal:
  - `FLOW_PMO_MODEL_URL=https://rd1e5wxyg84pnzxf.private.blob.vercel-storage.com/PowerBI_Model_20260220_114501.xlsx`
- Se quiser subir a versão `dashboard_app.py`:
  - `FLOW_PMO_DASH_MODULE=dashboard_app`
  - `FLOW_PMO_DASHBOARD_OUTPUT_URL=https://rd1e5wxyg84pnzxf.private.blob.vercel-storage.com/dashboard_output_20260220_114452.xlsx`
