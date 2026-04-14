# Migração de Blob Vercel → Cloudflare R2

**Data:** Abril 2026  
**Motivo:** Limite de banda do plano Hobby da Vercel esgotado (`You have reached your usage limits for this store using the Hobby plan. Access resumes on 14/05/26`). O Cloudflare R2 não cobra egress (transferência de dados para a internet), eliminando esse problema.

---

## 1. Estimativa de Custos

### Perfil de uso do projeto

| Componente | Estimativa | Base |
|---|---|---|
| Arquivos no bucket | ~30 arquivos | Ver `copy_latest_upload.py` |
| Tamanho total | ~500 MB – 1.5 GB | PowerBI_Model + 4 process mining XLSX + ~25 CSVs |
| Writes (Class A) | ~30 por execução do pipeline | 1 `PutObject` por arquivo |
| Reads (Class B) | A cada cold start do Vercel | `GetObject` por arquivo acessado na requisição |

### Projeção mensal

Premissas: pipeline roda 1×/dia, dashboard recebe ~200 requisições/dia, TTL de cache = 300 s, ~10 arquivos lidos por requisição em cold start.

| Métrica | Uso estimado/mês | Free tier | Custo |
|---|---|---|---|
| Storage | ~1 GB-month | 10 GB-month | **$0.00** |
| Class A (uploads) | 30 × 30 = ~900 ops | 1.000.000 ops | **$0.00** |
| Class B (downloads) | 200 req × 10 arq × 30 dias = ~60.000 ops | 10.000.000 ops | **$0.00** |
| Egress | ilimitado | Free | **$0.00** |
| **Total estimado** | | | **$0.00/mês** |

Margem restante do free tier:
- Class B: **0,6%** utilizado
- Class A: **0,09%** utilizado

### Por que usar Standard storage (não Infrequent Access)

| | Standard | Infrequent Access |
|---|---|---|
| Free tier | **Sim** | Não |
| Custo/GB | $0.015 | $0.01 |
| Data retrieval | Grátis | $0.01/GB |
| Class A ops | $4.50/M | $9.00/M |

Para este caso, Infrequent Access seria mais caro: sem free tier e com cobrança por cada leitura. **Usar Standard.**

### Otimização: aumentar TTL de cache

Cada instância Vercel (serverless) tem `/tmp` efêmero. Com o TTL padrão de 300 s, ela re-baixa os arquivos do R2 a cada 5 minutos enquanto está quente. Aumentar para 30 minutos reduz leituras desnecessárias:

```ini
# jira_env.txt e Vercel env vars
FLOW_PMO_REMOTE_CACHE_TTL_SECONDS=1800
```

---

## 2. Pré-requisitos

- Conta Cloudflare (plano Free é suficiente)
- Python com `boto3` instalado: `pip install boto3`
- Acesso ao painel Vercel do projeto

---

## 3. Configuração do Bucket R2

### 3.1 Criar o bucket

1. Acesse **dash.cloudflare.com → R2 Object Storage → Create bucket**
2. Nome: `flow-pmo-data`
3. Localização: **Automatic**
4. Após criar: **Settings → Public access → Allow Access**
5. Anote a URL pública gerada:
   ```
   https://pub-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.r2.dev
   ```

### 3.2 Criar credenciais de API

1. No painel R2 → **Manage R2 API tokens → Create API token**
2. Permissões: **Object Read & Write** (escopado ao bucket `flow-pmo-data`)
3. Salve:
   - Account ID (visível na URL do painel ou em **Overview**)
   - Access Key ID
   - Secret Access Key

---

## 4. Configurar o Pipeline de Upload

Adicione ao `jira_env.txt`:

```ini
# Cloudflare R2 — upload de artefatos
CLOUDFLARE_R2_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
CLOUDFLARE_R2_BUCKET=flow-pmo-data
CLOUDFLARE_R2_ACCESS_KEY_ID=<ACCESS_KEY_ID>
CLOUDFLARE_R2_SECRET_ACCESS_KEY=<SECRET_ACCESS_KEY>
CLOUDFLARE_R2_PUBLIC_BASE_URL=https://pub-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.r2.dev
```

O `run_all_projects.py` já contém a função `upload_to_r2()` que lê essas variáveis e faz upload de todos os arquivos de `latest-upload/` ao final do pipeline.

---

## 5. Primeiro Upload

Execute o pipeline normalmente:

```bash
python run_all_projects.py
```

Ao final, o terminal imprimirá as URLs públicas de todos os arquivos:

```
--- URLs publicas (configure no Vercel) ---
  https://pub-xxx.r2.dev/PowerBI_Model_latest.xlsx
  https://pub-xxx.r2.dev/portfolio-bt-ns-latest-data.csv
  https://pub-xxx.r2.dev/four_ps_kanban.csv
  https://pub-xxx.r2.dev/w1nner-downstream-latest-data.csv
  ... (todos os arquivos)
-------------------------------------------
```

Copie essas URLs — serão usadas na etapa seguinte.

---

## 6. Atualizar Variáveis no Vercel

Acesse **Vercel → Project → Settings → Environment Variables**.

### 6.1 Variáveis simples (valor = uma URL)

Substitua o valor atual pela URL do R2 (`https://pub-xxx.r2.dev/<arquivo>`):

| Variável Vercel | Arquivo no R2 |
|---|---|
| `FLOW_PMO_MODEL_URL` | `PowerBI_Model_latest.xlsx` |
| `FLOW_PMO_PORTFOLIO_CSV_URL` | `portfolio-bt-ns-latest-data.csv` |
| `FLOW_PMO_FOUR_PS_KANBAN_CSV_URL` *(nova — adicionar)* | `four_ps_kanban.csv` |
| `FLOW_PMO_PROCESS_MINING_REPORT_URL` | `w1nner-process-mining-latest.xlsx` |
| `FLOW_PMO_CAPEX_SUMMARY_URL` | `capex-summary-latest.csv` |
| `FLOW_PMO_CAPEX_RAW_URL` | `capex-raw-latest.csv` |
| `FLOW_PMO_GMUD_INDEX_URL` | `gmud-coverage-index-latest.csv` |
| `FLOW_PMO_GMUD_WEEKLY_URL` | `gmud-coverage-weekly-latest.csv` |
| `FLOW_PMO_GMUD_ITEMS_URL` | `gmud-coverage-items-latest.csv` |

### 6.2 Variáveis JSON — substituir BASE por `https://pub-xxx.r2.dev`

**`FLOW_PMO_DOWNSTREAM_CSV_URL_MAP`**
```json
{"W1NNER":"BASE/w1nner-downstream-latest-data.csv","S1NC":"BASE/s1nc-downstream-latest-data.csv","BF":"BASE/befinance-downstream-latest-data.csv","DT":"BASE/dataanalytics-downstream-latest-data.csv"}
```

**`FLOW_PMO_BOTTLENECK_CSV_URL_MAP`**
```json
{"W1NNR":"BASE/w1nner-downstream-latest-data_bottlenecks.csv","S1NC":"BASE/s1nc-downstream-latest-data_bottlenecks.csv","BF":"BASE/befinance-downstream-latest-data_bottlenecks.csv","DT":"BASE/dataanalytics-downstream-latest-data_bottlenecks.csv"}
```

**`FLOW_PMO_BITBUCKET_CSV_URL_MAP`**
```json
{"w1nner_commits":"BASE/w1nner_commits.csv","w1nner_pullrequests":"BASE/w1nner_pullrequests.csv","w1nner_pipelines":"BASE/w1nner_pipelines.csv","s1nc_commits":"BASE/s1nc_commits.csv","s1nc_pullrequests":"BASE/s1nc_pullrequests.csv","s1nc_pipelines":"BASE/s1nc_pipelines.csv","befinance_commits":"BASE/befinance_commits.csv","befinance_pullrequests":"BASE/befinance_pullrequests.csv","befinance_pipelines":"BASE/befinance_pipelines.csv","dataanalytics_commits":"BASE/dataanalytics_commits.csv","dataanalytics_pullrequests":"BASE/dataanalytics_pullrequests.csv","dataanalytics_pipelines":"BASE/dataanalytics_pipelines.csv"}
```

**`FLOW_PMO_PM_EXCEL_URL_MAP`**
```json
{"w1nner":"BASE/w1nner-process-mining-latest.xlsx","s1nc":"BASE/s1nc-process-mining-latest.xlsx","befinance":"BASE/befinance-process-mining-latest.xlsx","dataanalytics":"BASE/dataanalytics-process-mining-latest.xlsx"}
```

### 6.3 Variáveis que NÃO precisam mudar

| Variável | Motivo |
|---|---|
| `FLOW_PMO_ONE_PAGE_SLA_DAYS` | Valor numérico |
| `FLOW_PMO_REMOTE_CACHE_TTL_SECONDS` | Valor numérico (considere aumentar para 1800) |
| `FLOW_PMO_ALLOWED_DOMAIN` | Domínio OAuth |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth Google |
| `FLASK_SECRET_KEY` | Chave de sessão |
| `FLOWMETRICS_READ_WRITE_TOKEN` | Token Vercel Blob — remover após validação |
| `BLOB_READ_WRITE_TOKEN` | Token Vercel Blob — remover após validação |

---

## 7. Validação

1. Faça redeploy no Vercel (ou aguarde o próximo deploy automático)
2. Abra o dashboard e verifique se todos os dados carregam sem erro 403
3. Monitore os logs Vercel nas primeiras requisições (Functions → Logs)
4. Após confirmar funcionamento: remova `FLOWMETRICS_READ_WRITE_TOKEN` e `BLOB_READ_WRITE_TOKEN` do Vercel

---

## 8. Checklist de Migração

- [ ] Bucket R2 criado com acesso público habilitado
- [ ] API token R2 gerado com permissão Read & Write
- [ ] `boto3` instalado (`pip install boto3`)
- [ ] Variáveis `CLOUDFLARE_R2_*` adicionadas ao `jira_env.txt`
- [ ] Pipeline executado (`python run_all_projects.py`) — upload OK
- [ ] URLs públicas copiadas do terminal
- [ ] 9 variáveis simples atualizadas no Vercel
- [ ] 4 variáveis JSON atualizadas no Vercel
- [ ] `FLOW_PMO_FOUR_PS_KANBAN_CSV_URL` adicionada (nova)
- [ ] `FLOW_PMO_REMOTE_CACHE_TTL_SECONDS=1800` atualizada (opcional)
- [ ] Redeploy no Vercel realizado
- [ ] Dashboard validado em produção
- [ ] `FLOWMETRICS_READ_WRITE_TOKEN` removida
- [ ] `BLOB_READ_WRITE_TOKEN` removida

---

## 9. Referências

- [Cloudflare R2 Pricing](https://developers.cloudflare.com/r2/pricing/)
- [R2 S3-compatible API](https://developers.cloudflare.com/r2/api/s3/api/)
- `run_all_projects.py` → função `upload_to_r2()`
- `dashboards/core/data_loading.py` → função `_refresh_remote_cache_file()`
