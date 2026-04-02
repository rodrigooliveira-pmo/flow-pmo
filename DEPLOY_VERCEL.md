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
- Autenticação Google:
  - `FLOW_PMO_ALLOWED_DOMAIN`: domínio principal usado como hint do Google (`w1.com.br` no projeto atual).
  - `FLOW_PMO_ALLOWED_EMAILS`: allowlist estática legada por e-mail.
  - `FLOW_PMO_ALLOWED_GROUP`: grupo do Google Workspace autorizado.
  - `GOOGLE_SERVICE_ACCOUNT_JSON`: credencial da service account com Domain-Wide Delegation para o Admin SDK Directory API.
  - `GOOGLE_IMPERSONATE_EMAIL`: e-mail de admin/usuário autorizado a ser impersonado pela service account.
  - A checagem por grupo só fica ativa quando `FLOW_PMO_ALLOWED_GROUP`, `GOOGLE_SERVICE_ACCOUNT_JSON` e `GOOGLE_IMPERSONATE_EMAIL` estão preenchidos ao mesmo tempo. Se isso não acontecer, o código continua em `allowlist` estática quando `FLOW_PMO_ALLOWED_EMAILS` estiver definida.
  - `GOOGLE_SERVICE_ACCOUNT_JSON` pode ser informado como JSON puro, JSON com `\n` escapado ou base64 do JSON.
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
- SLA de serviço:
  - `FLOW_PMO_ONE_PAGE_SLA_DAYS`: SLA global padrão em dias para a visão de serviço/Lead Time. Exemplo: `5`.
  - `FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP`: mapa JSON de SLA por projeto. Exemplo: `{"W1NNER":5,"S1NC":5,"BEFINANCE":5,"DATA&ANALYTICS":5}`.

Use essas variáveis no projeto da Vercel para trocar módulo/objeto Dash e fonte de dados sem alterar código.

## Migração de allowlist para grupo
1. Mantenha `FLOW_PMO_ALLOWED_EMAILS` temporariamente durante a transição, para não cortar acesso enquanto valida a nova checagem.
2. Cadastre `FLOW_PMO_ALLOWED_GROUP`, `GOOGLE_SERVICE_ACCOUNT_JSON` e `GOOGLE_IMPERSONATE_EMAIL` no mesmo ambiente (`Preview` e/ou `Production`).
3. Confirme no log de inicialização que o app entrou em `modo grupo`; se as três variáveis não estiverem completas, o bootstrap registra warning e continua usando a allowlist.
4. Só depois de confirmar a validação por grupo remova a allowlist estática, se quiser operar exclusivamente por grupo.

## SLA de serviço no Vercel
1. Acesse `flow-pmo` no dashboard da Vercel.
2. Abra `Settings` → `Environment Variables`.
3. Cadastre `FLOW_PMO_ONE_PAGE_SLA_DAYS` e/ou `FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP` com scope `Production`.

Observações:
- No `FLOW_PMO_ONE_PAGE_SLA_DAYS_MAP`, as chaves dos projetos devem ficar em MAIÚSCULAS.
- O código faz normalização com `.upper()`, então `W1NNER`, `S1NC`, `BEFINANCE` e `DATA&ANALYTICS` devem ser mantidos nesse formato.
- Se você configurar os dois, o mapa por projeto sobrescreve o SLA global nos projetos informados.

## SLA aging do portfólio
- O aging do portfólio não é persistido por ambiente hoje; ele é configurado pela UI no campo de texto da aba `Portfólio`.
- O default atual hardcoded é:

```json
{"tipo":{"Épico":30,"Feature":20},"status":{"Triagem":7,"Backlog":15,"Business Review":10}}
```

- Se quiser outro valor padrão em produção, hoje é preciso alterar o valor inicial do componente `filter-portfolio-sla-aging-json` em `dashboard_full.py` ou expor esse default como variável de ambiente em uma próxima etapa.

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
