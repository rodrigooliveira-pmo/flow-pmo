# Codex Operating Rules for This Project

## Workflow Orchestration
1. Plan Node Default
- Enter plan mode for any non-trivial task (3+ steps or architectural decisions).
- If execution derails, stop and re-plan immediately.
- Include verification work in the plan, not only implementation.
- Write detailed specs up front to reduce ambiguity.

2. Subagent Strategy
- Use subagents liberally to keep the main context clean.
- Offload research, exploration, and parallel analysis to subagents.
- For complex work, increase parallel exploration via subagents.
- Keep one tack per subagent for focused execution.

3. Self-Improvement Loop
- After any user correction, append the pattern to `tasks/lessons.md`.
- Add explicit rules that prevent repeating the same mistake.
- Iterate on lessons ruthlessly until repeated errors drop.
- Review relevant lessons at the start of each session.

4. Verification Before Done
- Never mark complete without evidence it works.
- Diff behavior between main and changed code when relevant.
- Check quality against staff-level review expectations.
- Run tests, inspect logs, and demonstrate correctness.

5. Demand Elegance (Balanced)
- For non-trivial changes, ask whether a cleaner design exists.
- If a fix feels hacky, rework to an elegant root-cause solution.
- Skip this step for obvious/simple fixes to avoid over-engineering.
- Challenge your own implementation before presenting.

6. Autonomous Bug Fixing
- On bug reports, diagnose and fix directly without hand-holding.
- Use logs, errors, and failing tests as primary evidence.
- Minimize user context switching.
- Fix failing CI tests proactively.

## Task Management
- Plan first: write a checklist in `tasks/todo.md`.
- Verify plan: check in before starting implementation.
- Track progress: mark checklist items done during execution.
- Explain changes: add concise high-level summaries per step.
- Document results: include a review section in `tasks/todo.md`.
- Capture lessons: update `tasks/lessons.md` after user corrections.
- At the end of each prompt execution, generate a suggested commit message text summarizing the change.

## Authentication

- Login via Google OAuth 2.0 implementado em `auth.py` — não reescrever, apenas estender.
- Controle de acesso atual: allowlist estática via `FLOW_PMO_ALLOWED_EMAILS` (env var).
- Futuro: migrar para checagem dinâmica por grupo Workspace via `FLOW_PMO_ALLOWED_GROUP` + service account.
- Redirect URI de produção: `https://flow-pmo.vercel.app/callback` (registrada no Google Cloud Console, projeto `dashboard-fluxo-produtividade`).
- Workspace tem múltiplos domínios (`w1.com.br`, `w1consultoria.com.br`, `w1technology.com.br`) — não validar por sufixo de e-mail nem por `hd == domínio_primário`. Usar `hd` apenas para bloquear contas Gmail pessoais.
- Para rodar localmente: `python -c "from dotenv import load_dotenv; load_dotenv('.env.local'); from api.index import app; app.run(port=3000, debug=True)"`

## Dashboard Refactoring (Modular Architecture)

### Project Structure Changes

**Previous**: Monolithic `dashboard_full.py` (27,610 lines with mixed concerns)

**Current**: Modular package structure under `dashboards/`:
- `dashboards/core/` — Data loading & processing (imports, downloads, filtering)
- `dashboards/metrics/` — Statistical metrics & calculations (percentiles, Weibull, capability)
- `dashboards/components/` — UI component rendering (cards, tables, charts)

### Key Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `core/data_loading.py` | Download/cache models, resolve files | `_download_*`, `load_model_data`, `_resolve_model_file` |
| `core/data_processing.py` | Data transformation & filtering | `apply_portfolio_module_filters`, `resolve_service_class`, `done_time_eligible_mask` |
| `metrics/time_metrics.py` | Time-based metrics & analysis | `time_metric_series`, `exact_empirical_percentile`, `fit_weibull_linearized`, `add_statistical_lines` |
| `components/cards.py` | KPI and metric cards | `create_kpi_card`, `_portfolio_metric_card` |
| `components/tables.py` | Data tables | `create_table`, `create_generic_datatable` |

### Working with the Modular Codebase

1. **Locate function**: Search in appropriate module under `dashboards/`
2. **Update imports**: Ensure function is exported in module `__init__.py` and imported in `dashboard_full.py`
3. **Test imports**: Run `python -c "from dashboard_full import function_name"` to verify
4. **Avoid duplication**: Check if function already exists in a module before creating new one

### Import Export Checklist

When moving a function to a module:
- [ ] Function exists in correct module file (e.g., `dashboards/core/data_processing.py`)
- [ ] Function is exported from module's `__init__.py` (e.g., `from .data_processing import function_name`)
- [ ] Function is imported in `dashboard_full.py` from the module (e.g., `from dashboards.core import function_name`)
- [ ] Test import verification passes

### Expected Error Scenarios & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `NameError: name 'func' is not defined` | Function moved but import missing | Add to `dashboard_full.py` imports from module |
| `ImportError: cannot import name 'func'` | Function not exported from module | Add to module's `__init__.py` |
| Circular dependency warnings | Modules importing each other | Check dependency direction; `core` → `metrics` → `components` |

---

## Deploy — AWS App Runner (CI/CD)

> Documentação completa: `PIPELINE_AWS_APP_RUNNER.md`

### Ambiente de Produção

- **Plataforma:** AWS App Runner (ECR + Bitbucket Pipelines)
- **URL:** `https://k5ipb3jmhj.us-east-1.awsapprunner.com`
- **Service ARN:** `arn:aws:apprunner:us-east-1:919934977141:service/flow-pmo/94e15617551a4ccf8005f012a43cd4df`
- **Log Group CloudWatch:** `/aws/apprunner/flow-pmo/94e15617551a4ccf8005f012a43cd4df/application`

### Regras críticas para o Dockerfile / requirements

- `gunicorn` **obrigatoriamente** em `requirements.txt` (não em `requirements-vercel.txt`)
- `requirements-vercel.txt` é para o ambiente serverless da Vercel — **não inclui gunicorn**
- Ao alterar dependências do container, verificar que o `CMD` do Dockerfile tem seus executáveis instalados
- CMD atual: `gunicorn api.index:app --bind 0.0.0.0:8080 --workers 1 --timeout 300`

### Como verificar o commit em produção

```bash
curl https://k5ipb3jmhj.us-east-1.awsapprunner.com/_version
# {"commit": "abc123...", "status": "ok"}
```

### Diagnóstico de rollback silencioso

O App Runner reverte para a versão anterior quando o container falha, mas mantém `Status: RUNNING`.
Para verificar se há rollback:

```bash
aws apprunner describe-service \
  --service-arn "$APP_RUNNER_SERVICE_ARN" \
  --region us-east-1 \
  --query "Service.SourceConfiguration.ImageRepository.ImageIdentifier" \
  --output text
# Comparar com o commit atual — se diferente, houve rollback
```

Para ver o erro do container:
```bash
aws logs filter-log-events \
  --log-group-name "/aws/apprunner/flow-pmo/94e15617551a4ccf8005f012a43cd4df/application" \
  --start-time $(date -d '10 minutes ago' +%s000) \
  --region us-east-1 \
  --query "events[*].message" --output text | tail -50
```

### Causas conhecidas de rollback

| Erro | Causa | Solução |
|------|-------|---------|
| `exec: "gunicorn": not found` | gunicorn ausente do requirements.txt | Adicionar `gunicorn>=21.2,<24` |
| Health check timeout | dashboard_full.py demora para importar | UnhealthyThreshold=10 (100s tolerância) |
| OOM kill | Múltiplos workers consumindo >2GB | `--workers 1` no gunicorn |

### Rotas públicas (sem autenticação)

As rotas abaixo estão em `auth.py` → `_PUBLIC_PREFIXES` e não exigem login:
- `/_version` — retorna commit hash em produção (usado pelo pipeline para verificação)
- `/_healthz` — health check alternativo

---

## Core Principles
- Simplicity first: solve with minimal complexity and minimal surface area.
- No laziness: find root causes, avoid temporary patches.
- Minimal impact: touch only what is necessary to avoid regressions.
