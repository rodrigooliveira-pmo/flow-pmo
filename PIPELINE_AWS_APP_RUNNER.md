# Deploy AWS App Runner — Guia Completo

## Mapeamento Vercel → AWS

| Conceito Vercel             | Equivalente AWS                  |
|-----------------------------|----------------------------------|
| `vercel.json` (builder)     | `Dockerfile` (gunicorn na 8080)  |
| `@vercel/python`            | Python 3.11-slim + pip install   |
| `vercel deploy --prod`      | `python deploy_aws.py`           |
| Vercel Blob Storage (URLs)  | Mesmas URLs públicas (sem troca) |
| Vercel env vars (dashboard) | App Runner env vars (console/CLI)|
| `deploy.py` (Vercel CLI)    | `deploy_aws.py` (AWS CLI+Docker) |

---

## Arquitetura do Deploy

```
Bitbucket (push main)
    │
    ▼
[Step 1] Build & Push Docker Image
    │  docker build → ECR (tag = commit hash)
    ▼
[Step 2] Deploy to AWS App Runner
    │  aws apprunner update-service
    │  → envia nova imagem + env vars + health check config
    ▼
[Step 3] Verify Deployment
    │  polling describe-service (até 10 min)
    │  compara ImageIdentifier ativo com commit esperado
    │  dump CloudWatch logs se rollback detectado
    ▼
App Runner: novo container sobe, health check TCP passa → RUNNING ✅
```

### Imagem Docker

- **Base:** `python:3.11-slim`
- **Servidor WSGI:** `gunicorn` (instalado via `requirements.txt`)
- **Porta:** `8080`
- **CMD:** `gunicorn api.index:app --bind 0.0.0.0:8080 --workers 1 --timeout 300`

> **⚠️ CRÍTICO:** `gunicorn` **deve** estar em `requirements.txt`.  
> O `requirements-vercel.txt` é para o ambiente serverless da Vercel e **não inclui gunicorn**.  
> Sempre que criar um ambiente Docker separado, verificar que o servidor WSGI está no requirements.

---

## Variáveis de ambiente necessárias

### Infra (Bitbucket Pipeline / deploy_aws.py)

| Variável               | Descrição                                  | Exemplo                            |
|------------------------|--------------------------------------------|-------------------------------------|
| `AWS_ACCOUNT_ID`       | ID numérico da conta AWS                   | `919934977141`                     |
| `AWS_DEFAULT_REGION`   | Região AWS                                 | `us-east-1`                        |
| `ECR_REPOSITORY`       | Nome do repositório ECR                    | `flow-pmo`                         |
| `APP_RUNNER_SERVICE_ARN` | ARN do serviço App Runner              | `arn:aws:apprunner:us-east-1:...`  |
| `AWS_OIDC_ROLE_ARN`    | ARN do IAM Role para OIDC do Bitbucket     | `arn:aws:iam::...:role/...`        |

### Aplicação (injetadas no container via pipeline)

As variáveis abaixo são passadas no `source-config.json` gerado pelo Deploy step:

| Variável                              | Valor                                  |
|---------------------------------------|----------------------------------------|
| `FLOW_PMO_DASH_MODULE`               | `dashboard_full`                       |
| `FLOW_PMO_DASH_ATTR`                 | `app`                                  |
| `GOOGLE_CLIENT_ID`                   | (id do OAuth Google)                   |
| `GOOGLE_CLIENT_SECRET`               | (secret do OAuth Google)               |
| `FLASK_SECRET_KEY`                   | (chave secreta Flask)                  |
| `FLOW_PMO_ALLOWED_DOMAIN`            | `w1.com.br`                            |
| `FLOW_PMO_ALLOWED_EMAILS`            | (lista de e-mails separados por vírgula)|
| `FLOW_PMO_ALLOWED_GROUP`             | `sso-dashboardfluxoprodutividade-viewer@w1.com.br` |
| `FLOW_PMO_MODEL_URL`                 | URL pública do `.xlsx` no S3           |
| `FLOW_PMO_PORTFOLIO_CSV_URL`         | URL CSV portfólio no S3                |
| `FLOW_PMO_BOTTLENECK_CSV_URL_MAP`    | URL bottlenecks xlsx no S3             |
| `FLOW_PMO_DOWNSTREAM_CSV_URL_MAP`    | JSON com URLs downstream por BU        |
| `FLOW_PMO_BITBUCKET_CSV_URL_MAP`     | JSON com URLs commits/PRs por repo     |
| `FLOW_PMO_PROCESS_MINING_REPORT_URL` | JSON com URLs process mining por BU    |
| `FLOW_PMO_REMOTE_CACHE_TTL_SECONDS`  | `300`                                  |
| `FLOW_PMO_ONE_PAGE_SLA_DAYS`         | `5`                                    |
| `BITBUCKET_COMMIT`                   | Hash do commit (injetado automaticamente)|

> **Nota:** As URLs de dados (S3 público) continuam funcionando sem alteração —
> são URLs públicas e não dependem da plataforma de hosting.

---

## Configuração do Health Check (App Runner)

O `dashboard_full.py` é um módulo pesado (~1.4MB) que demora para importar.  
O health check deve ser tolerante o suficiente para o gunicorn terminar a inicialização.

```bash
# Configuração atual no update-service
--health-check-configuration \
  "Protocol=TCP,Interval=10,Timeout=10,HealthyThreshold=1,UnhealthyThreshold=10"
# → 100 segundos de tolerância antes de declarar unhealthy
```

| Parâmetro           | Valor | Significado                              |
|---------------------|-------|------------------------------------------|
| Protocol            | TCP   | Verifica apenas se a porta 8080 está aberta |
| Interval            | 10s   | Checar a cada 10 segundos                |
| Timeout             | 10s   | Cada check tem 10s para responder        |
| HealthyThreshold    | 1     | 1 check OK = saudável                    |
| UnhealthyThreshold  | 10    | 10 falhas consecutivas = rollback        |

---

## Pré-requisitos AWS

1. **Repositório ECR** — armazena as imagens Docker
   ```bash
   aws ecr create-repository --repository-name flow-pmo --region us-east-1
   ```

2. **Serviço App Runner** — criado via console ou CLI, apontando para o ECR
   ```bash
   aws apprunner create-service \
     --service-name flow-pmo \
     --source-configuration '{
       "AuthenticationConfiguration": {
         "AccessRoleArn": "arn:aws:iam::ACCOUNT_ID:role/AppRunnerECRAccess"
       },
       "ImageRepository": {
         "ImageIdentifier": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/flow-pmo:latest",
         "ImageRepositoryType": "ECR",
         "ImageConfiguration": {
           "Port": "8080",
           "RuntimeEnvironmentVariables": {
             "FLOW_PMO_DASH_MODULE": "dashboard_full"
           }
         }
       }
     }' \
     --instance-configuration '{"Cpu":"1024","Memory":"2048"}' \
     --health-check-configuration '{"Protocol":"TCP","Interval":10,"Timeout":10,"HealthyThreshold":1,"UnhealthyThreshold":10}' \
     --region us-east-1
   ```

3. **IAM Role para ECR** — o App Runner precisa de permissão para pull de imagens
   - Policy: `AmazonEC2ContainerRegistryReadOnly`
   - Trust: `build.apprunner.amazonaws.com`

4. **Bitbucket OIDC** — autenticação sem credenciais estáticas
   - Configurar `oidc: true` nos steps e usar `AWS_OIDC_ROLE_ARN`
   - Trust policy no IAM Role deve incluir o provider OIDC do Bitbucket

---

## Pipeline Bitbucket (CI/CD automático)

O `bitbucket-pipelines.yml` executa automaticamente no push para `main`.

### Step 1 — Build & Push Docker Image

- Usa `atlassian/default-image:3` + serviço Docker
- Constrói a imagem tagueada com o **commit hash completo**
- Faz push ao ECR via pipe `atlassian/aws-ecr-push-image:2.6.0`

### Step 2 — Deploy to AWS App Runner

- Usa `amazon/aws-cli:2.15.0`
- Gera `/tmp/source-config.json` via heredoc bash com todas as env vars
- Executa `aws apprunner update-service` com:
  - Imagem tagueada com o commit
  - Todas as variáveis de ambiente da aplicação
  - Configuração de health check tolerante (100s)

### Step 3 — Verify Deployment

- Aguarda 60s inicial (container precisa subir)
- Polling até 40 tentativas (× 15s = ~10 minutos máximo)
- **Verifica a imagem ativa**, não apenas o status (`RUNNING` pode ser versão antiga!)
- Detecta rollback: `RUNNING` + imagem diferente do commit esperado
- Se rollback detectado por 3× seguidas: dumpa últimos 50 logs do CloudWatch e falha

#### Verificar commit em produção

```bash
curl https://k5ipb3jmhj.us-east-1.awsapprunner.com/_version
# {"commit": "31acaf6...", "status": "ok"}
```

### Variáveis no Bitbucket

Configurar em **Repository Settings → Pipeline → Variables**:

| Variável | Tipo |
|----------|------|
| `AWS_ACCOUNT_ID` | Normal |
| `AWS_DEFAULT_REGION` | Normal |
| `ECR_REPOSITORY` | Normal |
| `APP_RUNNER_SERVICE_ARN` | Normal |
| `AWS_OIDC_ROLE_ARN` | Normal |
| `GOOGLE_CLIENT_ID` | Secured |
| `GOOGLE_CLIENT_SECRET` | Secured |
| `FLASK_SECRET_KEY` | Secured |
| `FLOW_PMO_ALLOWED_EMAILS` | Secured |
| `BLOB_READ_WRITE_TOKEN` | Secured |
| `FLOWMETRICS_READ_WRITE_TOKEN` | Secured |
| `VERCEL_OIDC_TOKEN` | Secured |

---

## Deploy local (via script)

```bash
# Deploy completo (build + push + update App Runner)
python deploy_aws.py

# Apenas build local (sem push)
python deploy_aws.py --skip-push

# Push ao ECR sem atualizar App Runner
python deploy_aws.py --skip-deploy

# Deploy e aguardar até RUNNING
python deploy_aws.py --wait

# Dry run (visualizar passos)
python deploy_aws.py --dry-run

# Tag específica
python deploy_aws.py --tag v1.2.3

# Build sem cache
python deploy_aws.py --no-cache
```

---

## Diagnóstico de Problemas

### Sintoma: pipeline reporta sucesso mas site não atualiza

**Causa provável:** App Runner fez rollback silencioso.

O App Runner reverte para a versão anterior quando o container novo não passa o health check, mas mantém `Status: RUNNING`. O pipeline antigo só checava o status, não a imagem ativa — por isso reportava sucesso.

**Como verificar:**
```bash
aws apprunner describe-service \
  --service-arn "$APP_RUNNER_SERVICE_ARN" \
  --region us-east-1 \
  --query "Service.SourceConfiguration.ImageRepository.ImageIdentifier" \
  --output text
```
Comparar com o commit do último push. Se for diferente → rollback.

**Como ver o erro do container:**
```bash
aws logs filter-log-events \
  --log-group-name "/aws/apprunner/flow-pmo/94e15617551a4ccf8005f012a43cd4df/application" \
  --start-time $(date -d '10 minutes ago' +%s000) \
  --region us-east-1 \
  --query "events[*].message" \
  --output text | tail -50
```

### Causas conhecidas de rollback

| Erro | Causa | Solução |
|------|-------|---------|
| `exec: "gunicorn": executable file not found in $PATH` | `gunicorn` ausente do `requirements.txt` | Adicionar `gunicorn>=21.2,<24` ao `requirements.txt` |
| Container não responde no health check timeout | `dashboard_full.py` demora para importar | Health check: `UnhealthyThreshold=10` (100s de tolerância) |
| OOM (Out of Memory) | Múltiplos workers consumindo >2GB | Usar `--workers 1` no gunicorn |
| `ImportError` ou `SyntaxError` | Erro em código Python | Ver logs CloudWatch acima |

---

## Incidente 2026-04-17 — Rollback Silencioso

### Resumo

Todos os deploys reportavam sucesso no pipeline, mas o site nunca atualizava desde a primeira configuração do App Runner.

### Causa Raiz

`gunicorn` não estava instalado na imagem Docker:
```
exec: "gunicorn": executable file not found in $PATH
```

O `requirements.txt` incluía apenas `-r requirements-vercel.txt`, que foi criado para o ambiente serverless da Vercel **sem gunicorn**. O `CMD` do Dockerfile chamava gunicorn, mas ele nunca era instalado.

### Por que não era detectado

O Verify step original verificava apenas `Status == RUNNING`. Após rollback, o App Runner fica em `RUNNING` com a **imagem anterior**, e o pipeline concluía com sucesso falso.

### Correções Aplicadas

1. **`requirements.txt`** — adicionado `gunicorn>=21.2,<24`
2. **Dockerfile** — `--timeout 300`, `--workers 1`, `--graceful-timeout 60`
3. **`bitbucket-pipelines.yml`** — health check tolerante (100s) + Verify determinístico por imagem + dump CloudWatch
4. **`api/index.py`** — endpoint `/_version` para verificação do commit em produção
5. **`auth.py`** — `/_version` e `/_healthz` adicionados à lista de rotas públicas

---

## Referências

- https://docs.aws.amazon.com/apprunner/latest/dg/service-source-image.html
- https://docs.aws.amazon.com/cli/latest/reference/apprunner/update-service.html
- https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html
- https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html
