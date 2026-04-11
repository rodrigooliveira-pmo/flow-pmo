# Arquitetura do Código — Flow-PMO

**Última atualização:** 2026-03-12
**Status:** Refatoração v2 — pacotes `shared/` e `jira/` extraídos

---

## Estrutura de Módulos

```
flow-pmo/
│
├── shared/                        ← Utilitários compartilhados (Fase 1)
│   ├── __init__.py
│   ├── env_utils.py               ← load_env_file(), parse_json_env()
│   ├── path_utils.py              ← candidate_data_folders(), find_latest_file()
│   └── text_utils.py             ← normalize_text() (unicodedata NFKD)
│
├── jira/                          ← Cliente Jira compartilhado (Fase 2)
│   ├── __init__.py
│   └── client.py                  ← JiraClient (retry, 3-tier fallback v3/v2)
│
├── api/
│   └── index.py                   ← Entry point Vercel (WSGI wrapper)
│
├── dash_board_metricas.py          ← HUB CENTRAL de transformação
├── dashboard_full.py               ← Dashboard Dash principal (entry point)
├── dashboard_process_mining.py     ← Dashboard Process Mining (standalone)
├── dashboard_spaf.py               ← Dashboard SPAF standalone
├── spaf_engine.py                  ← Engine SPAF (loaders + scoring socio-técnico)
│
├── jira_to_pipeline_csv.py         ← Extração Jira → CSVs de fluxo
├── jira_portfolio_to_csv.py        ← Extração Jira → CSV portfólio (BT/NS)
├── jira_to_businessmap_xlsx.py     ← MIGRAÇÃO: Jira → BusinessMap XLSX [*]
│
├── bitbucket_export.py             ← Extração Bitbucket → CSVs dev
├── extract_dev_productivity_data.py ← Orquestrador do bitbucket_export.py
│
├── process_mining_jira.py          ← Análise de process mining (changelog)
├── gerar_powerbi_pbix.py           ← Gerador de template/JSON Power BI
│
├── inspect_csvs.py                 ← Debug: inspeciona cabeçalhos de CSVs
└── run_import_check.py             ← Debug: valida consolidação de dados
```

> **[*]** `jira_to_businessmap_xlsx.py` é um **módulo de migração standalone**
> (Jira → BusinessMap/Kanbanize). Não faz parte do pipeline de métricas.
> Deve permanecer auto-suficiente (sem importar de `shared/` ou `jira/`).

---

## Pipeline de Dados

```
┌─────────────────────────────────────────────────────────────────────┐
│ FONTES EXTERNAS                                                     │
├────────────────────────────┬────────────────────────────────────────┤
│ Jira Cloud API             │ Bitbucket Cloud API                    │
│ (W1NNR, S1NC, BF, DT,      │ (W1NNR, S1NC, BF, DT)                  │
│  BT, NS — portfolio)       │                                        │
└────────────┬───────────────┴────────────────┬───────────────────────┘
             │                                │
  jira_to_pipeline_csv.py         bitbucket_export.py
  jira_portfolio_to_csv.py        extract_dev_productivity_data.py
             │                                │
             ▼                                ▼
  *-downstream-*.csv            {proj}_commits.csv
  *-bottlenecks.csv             {proj}_pullrequests.csv
  portfolio-bt-ns-*.csv         {proj}_pipelines.csv
  *-changelog-detail.csv        (opcional — não integrado ao pipeline)
             │
             ▼
  ┌──────────────────────────────────────────────┐
  │  DATA_FOLDER (OneDrive / env var)            │
  │  Todos os CSVs acumulados por data           │
  └──────────────────────┬───────────────────────┘
                         │
              dash_board_metricas.py  (HUB)
              ────────────────────────
              - Carrega e consolida todos os CSVs
              - Auto-detecção de projeto, encoding, delimitador
              - Calcula métricas semanais de fluxo
              - Modelo dimensional (Dim_* + Fato_Items)
              - Padrões de fluxo e gargalos
                         │
           ┌─────────────┼──────────────────────────┐
           │             │                          │
           ▼             ▼                          ▼
  dashboard_output_   PowerBI_Model_*.xlsx   bottlenecks_
  *.xlsx              (Star Schema)          consolidado_*.xlsx
           │             │
           │    (opcional: changelog detalhado)
           │             │
           │    process_mining_jira.py
           │             │
           │             ▼
           │    *-process-mining-*.xlsx
           │
           ▼
  ┌─────────────────────────────────────────────────────────┐
  │  DASHBOARDS DASH                                        │
  │                                                         │
  │  dashboard_full.py          ← PRINCIPAL (Vercel)        │
  │    • Flow Metrics, Portfólio, Process Mining (tab)      │
  │    • Lê: PowerBI_Model_*.xlsx + portfolio CSV           │
  │                                                         │
  │  dashboard_process_mining.py ← STANDALONE               │
  │    • Process Mining aprofundado                         │
  │    • Lê: *-process-mining-*.xlsx + Bitbucket CSVs       │
  │                                                         │
  │  dashboard_spaf.py            ← STANDALONE               │
  │    • Leitura SPAF 2.0 / socio-técnica                   │
  │    • Lê: PowerBI_Model + Bitbucket CSVs + Process Mining│
  └─────────────────────────────────────────────────────────┘
```

---

## Pacote `shared/`

### `shared/env_utils.py`
```python
load_env_file(path, overwrite=True)   # Carrega arquivo KEY=VALUE no os.environ
parse_json_env(name, default)          # Lê variável de ambiente como JSON dict
```

### `shared/path_utils.py`
```python
candidate_data_folders() → list[str]  # Resolve DATA_FOLDER em ordem de prioridade
find_latest_file(folder, prefix, ext) # Retorna arquivo mais recente pelo prefixo
existing_dirs(paths) → list[str]      # Filtra e deduplica diretórios existentes
LEGACY_DATA_FOLDER                    # Caminho OneDrive padrão (Windows/macOS)
```

**Prioridade de resolução de `DATA_FOLDER`:**
1. `FLOW_PMO_DATA_DIR` (env var)
2. `DATA_FOLDER` (env var legado)
3. `FLOW_PMO_DATA_DIRS` (lista separada por pathsep)
4. `<project_root>/dados/latest/`
5. `<project_root>/dados/`
6. `~/Documents/dados` e `~/Documents/Dados`
7. `<project_root>/data/`
8. `<project_root>/`
9. OneDrive legado (Windows: `C:\Users\W1 TI\OneDrive...`; macOS: `~/Library/CloudStorage/OneDrive-W1/...`)

### `shared/text_utils.py`
```python
normalize_text(value) → str   # lowercase + remove acentos (unicodedata NFKD) + colapsa espaços
```

---

## Pacote `jira/`

### `jira/client.py` — `JiraClient`

Cliente HTTP para a API Jira Cloud com:
- **Retry automático** com exponential backoff (padrão: 5 tentativas, fator 1.0)
- **3-tier fallback** por request: POST enhanced → GET enhanced → legacy v3/v2
- **Connection pooling** via `HTTPAdapter` (padrão: 32 conexões)

```python
client = JiraClient(base_url, email, api_token,
                    timeout=60, max_retries=5, backoff_factor=1.0)

client.search_issues(jql, fields, page_size=100, expand=None)
client.get_issue_changelog(issue_key, page_size=100, ...)
client.list_visible_projects()
```

**Usado por:**
- `jira_to_pipeline_csv.py`
- `jira_portfolio_to_csv.py`

**NÃO usado por:**
- `jira_to_businessmap_xlsx.py` (standalone por design)

---

## Seleção de Dashboard (Vercel)

O `api/index.py` seleciona o módulo a servir via env vars:

| Variável | Padrão | Descrição |
|---|---|---|
| `FLOW_PMO_DASH_MODULE` | `dashboard_full` | Módulo Python do dashboard |
| `FLOW_PMO_DASH_ATTR` | `app` | Atributo Dash dentro do módulo |

**Exemplos:**
```bash
# Dashboard principal (padrão)
FLOW_PMO_DASH_MODULE=dashboard_full

# Process Mining standalone
FLOW_PMO_DASH_MODULE=dashboard_process_mining

# SPAF standalone
FLOW_PMO_DASH_MODULE=dashboard_spaf
```

---

## Variáveis de Ambiente Relevantes

### Dados e Caminhos
| Variável | Descrição |
|---|---|
| `FLOW_PMO_DATA_DIR` | Pasta única de dados (alta prioridade) |
| `FLOW_PMO_DATA_DIRS` | Lista de pastas de dados (pathsep) |
| `DATA_FOLDER` | Override legado de pasta de dados |
| `FLOW_PMO_LATEST_DIR` | Pasta de saída para arquivos gerados |

### Jira
| Variável | Descrição |
|---|---|
| `JIRA_BASE_URL` | URL da instância Jira Cloud |
| `JIRA_EMAIL` | E-mail do usuário Jira |
| `JIRA_API_TOKEN` | API token do Jira Cloud |
| `JIRA_FIELD_MAP` | JSON mapeando campos custom (team, epic_name, etc.) |
| `JIRA_STATUS_MAP` | JSON mapeando status → estágio do fluxo |

### Bitbucket
| Variável | Descrição |
|---|---|
| `BB_EMAIL` | E-mail Atlassian |
| `BB_TOKEN` | App Password / API token Bitbucket |
| `BB_WORKSPACE` | Slug do workspace (ex: `w1consultoria`) |

### Dashboards
| Variável | Descrição |
|---|---|
| `FLOW_PMO_DASH_MODULE` | Módulo do dashboard a servir |
| `FLOW_PMO_DASHBOARD_OUTPUT_URL` | URL remota do `dashboard_output_*.xlsx` |
| `FLOW_PMO_PROCESS_MINING_REPORT_URL` | URL remota do report de process mining |

---

## Como Executar

### 1. Exportar dados do Jira
```bash
python jira_to_pipeline_csv.py --projects W1NNR S1NC BF DT
python jira_portfolio_to_csv.py --projects BT NS
```

### 2. Exportar dados do Bitbucket (opcional)
```bash
python extract_dev_productivity_data.py --since-days 90
```

### 3. Gerar métricas e modelo Power BI
```bash
python dash_board_metricas.py
```

### 4. Iniciar dashboard local
```bash
python dashboard_full.py
# ou process mining standalone:
python dashboard_process_mining.py
```

### 5. Process Mining (se changelog detalhado disponível)
```bash
python process_mining_jira.py --project W1NNR \
  --changelog w1nner-changelog-detail.csv
```

### 6. Migração para BusinessMap (quando necessário)
```bash
python jira_to_businessmap_xlsx.py --projects W1NNR \
  --board-name "Meu Board" --workflow-name "Workflow Padrão"
```

---

## Notas de Manutenção

- **`jira_to_businessmap_xlsx.py`** — módulo de migração standalone. Não remover nem integrar ao pipeline. Deve permanecer auto-suficiente para ser executado isoladamente.
- **`gerar_powerbi_pbix.py`** — gera JSON/HTML descritivos, não PBIX real. Mantido como referência.
- **`inspect_csvs.py` e `run_import_check.py`** — scripts de debug. Não fazem parte do pipeline de produção.
- **`shared/`** — ao adicionar novos módulos de extração, importar `load_env_file`, `candidate_data_folders` e `normalize_text` daqui em vez de reimplementar.
- **`jira/client.py`** — ao adicionar novos scripts de extração Jira, usar `JiraClient` em vez de criar sessões HTTP manuais.
