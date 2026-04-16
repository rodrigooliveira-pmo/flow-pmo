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

## Variáveis de ambiente necessárias

### Infra (Bitbucket Pipeline / deploy_aws.py)

| Variável               | Descrição                                  | Exemplo                            |
|------------------------|--------------------------------------------|------------------------------------|
| `AWS_ACCOUNT_ID`       | ID numérico da conta AWS                   | `123456789012`                     |
| `AWS_DEFAULT_REGION`   | Região AWS                                 | `us-east-1`                        |
| `ECR_REPOSITORY`       | Nome do repositório ECR                    | `flow-pmo`                         |
| `APP_RUNNER_SERVICE_ARN` | ARN do serviço App Runner                | `arn:aws:apprunner:us-east-1:...`  |
| `AWS_ACCESS_KEY_ID`    | (local) Credencial AWS                     | —                                  |
| `AWS_SECRET_ACCESS_KEY`| (local) Credencial AWS                     | —                                  |

### Aplicação (configurar no App Runner)

Estas variáveis devem ser configuradas como **Environment Variables** no serviço App Runner
(console AWS → App Runner → serviço → Configuration → Environment variables):

| Variável                              | Valor (mesmo da Vercel)                |
|---------------------------------------|----------------------------------------|
| `FLOW_PMO_DASH_MODULE`               | `dashboard_full`                       |
| `FLOW_PMO_DASH_ATTR`                 | `app`                                  |
| `GOOGLE_CLIENT_ID`                   | (id do OAuth)                          |
| `GOOGLE_CLIENT_SECRET`               | (secret do OAuth)                      |
| `FLASK_SECRET_KEY`                   | (chave secreta Flask)                  |
| `FLOW_PMO_ALLOWED_DOMAIN`            | `w1.com.br`                            |
| `FLOW_PMO_ALLOWED_EMAILS`            | (lista de e-mails)                     |
| `FLOW_PMO_ALLOWED_GROUP`             | `sso-dashboardfluxoprodutividade-...`  |
| `FLOW_PMO_MODEL_URL`                 | URL do .xlsx no blob                   |
| `FLOW_PMO_PORTFOLIO_CSV_URL`         | URL CSV portfolio                      |
| `FLOW_PMO_BOTTLENECK_CSV_URL_MAP`    | URL bottlenecks xlsx                   |
| `FLOW_PMO_DOWNSTREAM_CSV_URL_MAP`    | URLs downstream por BU                 |
| `FLOW_PMO_BITBUCKET_CSV_URL_MAP`     | URLs commits/PRs por repo              |
| `FLOW_PMO_PROCESS_MINING_REPORT_URL` | URL process mining xlsx                |
| `FLOW_PMO_REMOTE_CACHE_TTL_SECONDS`  | `0`                                    |
| `FLOW_PMO_ONE_PAGE_SLA_DAYS`         | `5`                                    |
| `FLOW_PMO_PM_COST_PER_HOUR_MAP`      | JSON custo/hora por BU                 |

> **Nota:** As URLs de dados (Vercel Blob Storage) continuam funcionando sem alteração —
> são URLs públicas e não dependem da plataforma de hosting.

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
     --region us-east-1
   ```

3. **IAM Role para ECR** — o App Runner precisa de permissão para pull de imagens
   - Policy: `AmazonEC2ContainerRegistryReadOnly`
   - Trust: `build.apprunner.amazonaws.com`

4. **Bitbucket OIDC** (para pipeline) — permissões de push no ECR e update no App Runner

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

## Pipeline Bitbucket (CI/CD automático)

O `bitbucket-pipelines.yml` executa automaticamente no push para `main`:

1. **Build & Push** — constrói imagem Docker, faz push ao ECR
2. **Deploy** — atualiza o serviço App Runner com a nova imagem
3. **Verify** — consulta o status do serviço após deploy

### Variáveis no Bitbucket

Configurar em **Repository Settings → Pipeline → Variables**:
- `AWS_ACCOUNT_ID`
- `AWS_DEFAULT_REGION`
- `ECR_REPOSITORY`
- `APP_RUNNER_SERVICE_ARN`
- `AWS_ACCESS_KEY_ID` (secured)
- `AWS_SECRET_ACCESS_KEY` (secured)

## Referências

- https://docs.aws.amazon.com/apprunner/latest/dg/service-source-image.html
- https://docs.aws.amazon.com/cli/latest/reference/apprunner/update-service.html
- https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html
