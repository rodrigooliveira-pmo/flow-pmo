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
  - `FLOW_PMO_PROCESS_MINING_REPORT_URL`: URL pública fixa para o relatório de process mining (`w1nner-process-mining-latest.xlsx`) consumido em runtime.
  - `FLOW_PMO_BOTTLENECK_CSV_URL_MAP`: mapa JSON de URLs de gargalo por projeto (ex.: `{"W1NNER":"https://.../w1nner-downstream-latest-data_bottlenecks.csv","DATA&ANALYTICS":"https://.../dataanalytics-downstream-latest-data_bottlenecks.csv"}`).
  - `FLOW_PMO_BOTTLENECK_CSV_URL`: fallback legado com URL única; só é aplicado quando o nome do arquivo corresponde ao prefixo do projeto filtrado.
  - `FLOW_PMO_DASHBOARD_OUTPUT_FILE`: caminho do `dashboard_output_*.xlsx`.
  - `FLOW_PMO_DASHBOARD_OUTPUT_URL`: URL pública para baixar o `dashboard_output_*.xlsx` em runtime.
  - `FLOW_PMO_PORTFOLIO_CSV_FILE`: caminho do `portfolio-bt-ns-YYYYMMDD-data.csv`.
  - `FLOW_PMO_PORTFOLIO_CSV_URL`: URL pública para baixar o CSV de portfólio em runtime.
  - `FLOW_PMO_DATA_DIR`: pasta principal para buscar arquivos de dados.
  - `FLOW_PMO_DATA_DIRS`: lista de pastas separadas por `:` (Linux/macOS) para busca de CSVs auxiliares.
  - `DATA_FOLDER`: compatibilidade com configuração legada.

Use essas variáveis no projeto da Vercel para trocar módulo/objeto Dash e fonte de dados sem alterar código.

## Valores que você já pode configurar agora
- Modelo principal:
  - `FLOW_PMO_MODEL_URL=https://<SEU_BLOB_PUBLICO>/PowerBI_Model_latest.xlsx`
- Process Mining (W1NNER):
  - `FLOW_PMO_PROCESS_MINING_REPORT_URL=https://<SEU_BLOB_PUBLICO>/w1nner-process-mining-latest.xlsx`
- Portfólio:
  - `FLOW_PMO_PORTFOLIO_CSV_URL=https://<SEU_BLOB_PUBLICO>/portfolio-bt-ns-latest-data.csv`
- Se quiser subir a versão `dashboard_app.py`:
  - `FLOW_PMO_DASH_MODULE=dashboard_app`
  - `FLOW_PMO_DASHBOARD_OUTPUT_URL=https://<SEU_BLOB_PUBLICO>/dashboard_output_latest.xlsx`

## Fluxo estável (sem trocar variáveis a cada geração)
1. Gere os arquivos normalmente:
   - `run_all_projects_macos.sh` ou `run_all_projects.ps1`
2. O fluxo agora cria automaticamente os arquivos fixos:
   - `PowerBI_Model_latest.xlsx`
   - `portfolio-bt-ns-latest-data.csv`
   - `dashboard_output_latest.xlsx`
3. Faça upload desses arquivos fixos para o Vercel Blob público, sobrescrevendo o mesmo nome.
4. Mantenha as mesmas variáveis de ambiente na Vercel (sem editar URLs a cada geração).

## Observação sobre gargalos
- O dashboard agora lê o ranking de gargalos diretamente da aba `Fato_Gargalos` dentro do `PowerBI_Model_*.xlsx`.
- A aba é gerada automaticamente pelo `dash_board_metricas.py`.
- Fallback legado (CSV de gargalos + cálculo em memória) foi mantido para compatibilidade.
