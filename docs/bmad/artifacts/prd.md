# PRD — Flow-PMO Dashboard: Refatoração Técnica Incremental

> **Versão:** 1.0  
> **Data:** 2026-04-24  
> **Autor:** John (PM) — BMAD  
> **Status:** [ ] Rascunho  [ ] Em Revisão  [ ] Aprovado  
> **Arquitetura de referência:** `docs/bmad/artifacts/architecture.md`  
> **Tipo de iniciativa:** Dívida técnica / Sustentabilidade de plataforma

---

## 1. Contexto e Problema

### 1.1 Situação Atual

O Flow-PMO Dashboard é um sistema analítico crítico de gestão de portfólio que consolida dados de JIRA Cloud, Bitbucket, Google Workspace e modelos Excel para geração de métricas de lead time, throughput, CAPEX e capacidade de times. Ele é utilizado diariamente por gestores e stakeholders da W1 para tomada de decisão operacional.

O sistema funciona — mas cresceu de forma orgânica e acumulou dívida técnica severa que compromete a capacidade de evolução:

| Indicador | Valor Atual | Referência Saudável |
|-----------|-------------|---------------------|
| LOC do arquivo principal | 29.230 | < 500 por módulo |
| Funções no arquivo principal | 241 | < 20 por módulo |
| Ciclos de dependência | 3 confirmados | 0 |
| Cobertura de testes | 0% | ≥ 80% lógica de domínio |
| Env vars sem validação | 17 | 0 |
| Funções duplicadas (download) | 8+ | 1 (genérica) |

### 1.2 Problema de Negócio

A dívida técnica atual gera três riscos concretos:

1. **Risco de produção silencioso:** Callbacks Dash sem tratamento de erro retornam telas em branco sem notificação. Mudança de coluna no Excel quebra cálculos de métricas sem alertas.
2. **Custo crescente de mudança:** Qualquer feature nova ou correção de bug exige navegar 29k LOC de código entrelaçado. O tempo de desenvolvimento aumenta a cada sprint.
3. **Risco de segurança imediato:** Valores financeiros sensíveis hardcoded em `run_local.py` podem vazar para o repositório.

### 1.3 Hipótese de Solução

Refatoração incremental por extração de domínios funcionais do God Object, sem reescrita total, mantendo o sistema em produção durante toda a transição. Cada sprint entrega valor mensurável em forma de redução de LOC no monolito, cobertura de testes e eliminação de riscos.

---

## 2. Objetivos e Métricas de Sucesso

### 2.1 Objetivos

| # | Objetivo | Por quê |
|---|----------|---------|
| O-1 | Eliminar riscos de segurança imediatos | `run_local.py` com valores financeiros é risco de vazamento |
| O-2 | Remover todos os ciclos de dependência | Bloqueiam testes e análise estática |
| O-3 | Criar cobertura de testes mínima em cálculos críticos | Guardrail contra regressões em métricas de negócio |
| O-4 | Validar configuração em startup | Erros de config detectados antes do primeiro request |
| O-5 | Reduzir `dashboard_full.py` abaixo de 5.000 LOC | Tornar o arquivo navegável e manutenível |
| O-6 | Estabelecer arquitetura em camadas sem violações | Base para evolução sustentável da plataforma |

### 2.2 Métricas de Sucesso (Definition of Done por objetivo)

| Objetivo | Métrica | Meta | Sprint |
|----------|---------|------|--------|
| O-1 | `run_local.py` sem valores hardcoded | 0 secrets no código | Sprint 1 |
| O-2 | `import dashboard_full` em módulos-folha | 0 ocorrências | Sprint 1 |
| O-3 | Cobertura pytest em `metrics/` e `data_processing.py` | ≥ 80% | Sprint 2 |
| O-4 | `os.getenv()` direto fora de `infra/env_config.py` | 0 ocorrências | Sprint 2 |
| O-5 | LOC de `dashboard_full.py` | < 5.000 | Sprint 4 |
| O-6 | Imports cross-camada (Infra → Domain, Domain → Presentation) | 0 violações | Sprint 4 |

---

## 3. Usuários e Personas

> Em refatoração técnica, os usuários primários são os desenvolvedores. Os usuários finais (gestores) não devem perceber diferença de comportamento — a paridade funcional é requisito mandatório.

### P-1: Desenvolvedor do Projeto (persona principal)

- **Perfil:** Engenheiro Python que mantém e evolui o sistema
- **Dor atual:** Navegar 29k LOC para encontrar onde um cálculo de lead time é feito. Medo de alterar código por falta de testes. Tempo gasto debugando falhas silenciosas.
- **Necessidade:** Módulos com responsabilidade clara, testes de regressão que avisam quando algo quebra, erros de configuração detectados cedo.

### P-2: Stakeholder / Gestor (persona secundária — não impactada negativamente)

- **Perfil:** Gestor que usa o dashboard diariamente para decisões de portfólio
- **Restrição:** Não pode ter nenhuma feature removida, nenhuma métrica alterada, nenhuma degradação de performance.
- **Necessidade:** Sistema continua funcionando identicamente durante toda a refatoração.

---

## 4. Requisitos Funcionais

### Épico 1: Segurança e Fundação (Sprint 1)

> **Meta:** Eliminar riscos críticos e criar a infraestrutura que viabiliza todas as refatorações seguintes.

#### 4.1.1 Remoção de Secrets Hardcoded

- **RF-001:** O arquivo `run_local.py` NÃO DEVE conter valores de configuração sensíveis (URLs de modelos financeiros, custos mensais de times, mapas de portfólio em JSON) hardcoded no código-fonte.
- **RF-002:** Todos os valores atualmente hardcoded em `run_local.py` DEVEM ser migrados para um arquivo `.env.local` excluído do controle de versão via `.gitignore`.
- **RF-003:** O arquivo `.env.local` DEVE ter um template de exemplo `.env.local.example` documentado no repositório com as chaves necessárias e valores fictícios.

#### 4.1.2 Configuração com Validação de Schema

- **RF-004:** DEVE existir um módulo `infra/env_config.py` responsável por toda a leitura de variáveis de ambiente do sistema.
- **RF-005:** O módulo `infra/env_config.py` DEVE usar `pydantic-settings` (`BaseSettings`) para declarar e validar todas as 17+ variáveis de ambiente.
- **RF-006:** O sistema DEVE falhar explicitamente com mensagem de erro clara (`ValueError` ou `ValidationError`) no startup se qualquer variável de ambiente obrigatória estiver ausente ou com formato inválido.
- **RF-007:** Nenhum outro módulo do sistema (fora de `infra/env_config.py`) DEVE conter chamadas diretas a `os.getenv()` ou `os.environ[]` para leitura de configuração de negócio.

#### 4.1.3 Quebra de Ciclos de Dependência

- **RF-008:** O módulo `dashboards/portfolio/functions.py` NÃO DEVE conter nenhum `import` (estático ou dinâmico) de `dashboard_full`.
- **RF-009:** O módulo `dashboards/four_ps/builder.py` NÃO DEVE conter nenhum `import` (estático ou dinâmico) de `dashboard_full`.
- **RF-010:** As funções compartilhadas que atualmente causam os ciclos (ex: `portfolio_roadmap_status_label`) DEVEM ser movidas para módulos de domínio neutros (ex: `dashboards/domain/shared/`).
- **RF-011:** A análise estática via `mypy` ou `ruff` DEVE ser executável sem erros de import circular em toda a base `dashboards/`.

#### 4.1.4 DataLoader Genérico

- **RF-012:** DEVE existir uma classe ou função `DataLoader` em `dashboards/core/data_loading.py` com assinatura `load(url: str, key: str, ttl_seconds: int, parser_fn: Callable) -> Any`.
- **RF-013:** As 8+ funções de download específicas (`_download_model_from_url`, `_download_portfolio_csv_from_url`, etc.) DEVEM ser substituídas por chamadas a `DataLoader.load(...)`.
- **RF-014:** O diretório de cache e o TTL padrão DEVEM ser configuráveis via variáveis de ambiente (ex: `FLOW_PMO_CACHE_DIR`, `FLOW_PMO_CACHE_TTL_SECONDS`), com fallback para `/tmp/flow-pmo-models` e 3600s respectivamente.

---

### Épico 2: Cobertura de Testes e Error Handling (Sprint 2)

> **Meta:** Criar guardrails que detectam regressões e tornam falhas visíveis ao usuário.

#### 4.2.1 Testes de Regressão para Métricas

- **RF-015:** DEVE existir um diretório `tests/` na raiz do projeto com estrutura espelhando `dashboards/`.
- **RF-016:** O módulo `dashboards/metrics/time_metrics.py` DEVE ter cobertura de testes ≥ 80% medida por `pytest-cov`.
- **RF-017:** Os testes de `time_metrics.py` DEVEM usar fixtures CSV com dados de entrada conhecidos e validar os valores de saída esperados (lead time, percentis, Weibull fit) contra resultados pré-calculados.
- **RF-018:** O módulo `dashboards/core/data_processing.py` DEVE ter cobertura de testes ≥ 80%, especialmente as funções de normalização (`normalize_text`, `resolve_service_class`, `_coerce_demand_type`).
- **RF-019:** Os testes DEVEM ser executáveis com `pytest` sem dependências externas (JIRA, S3, Excel real) — todas as fontes de dados externas DEVEM ser mockadas.

#### 4.2.2 Error Boundaries nos Callbacks Dash

- **RF-020:** Todos os 9 callbacks `@app.callback` em `dashboard_full.py` DEVEM ter tratamento de exceção explícito.
- **RF-021:** Em caso de erro em um callback, o sistema DEVE exibir uma mensagem de erro informativa no componente afetado (ex: `dcc.Graph` ou `html.Div` com mensagem) ao invés de retornar `None` silenciosamente.
- **RF-022:** Erros em callbacks DEVEM ser registrados em log com traceback completo para facilitar diagnóstico.

#### 4.2.3 Enums de Domínio

- **RF-023:** DEVE existir um módulo `dashboards/domain/enums.py` contendo Enums para: `ServiceClass` (Standard, Expedite, FixedDate, IntangibleJob), `DemandType` (Dev, Support, Issues, BAU), `StatusCategory` (Backlog, InProgress, Waiting, Done).
- **RF-024:** As funções de normalização em `data_processing.py` e `text_utils.py` DEVEM retornar os Enums definidos em RF-023, eliminando strings mágicas.
- **RF-025:** O token com typo `"higest"` em `HIGHEST_ALIAS_TOKENS` e outros typos documentados na análise arquitetural DEVEM ser corrigidos.

#### 4.2.4 Centralização de Configurações de Domínio

- **RF-026:** DEVE existir um módulo `dashboards/domain/config.py` contendo constantes de domínio: faixas de story points, datas de quarter (Q1-2026, Q2-2026, etc.), nomes canônicos de times (`W1NNER`, `S1NC`, etc.).
- **RF-027:** Nenhum módulo fora de `dashboards/domain/config.py` DEVE conter definições duplicadas dessas constantes.

---

### Épico 3: Schema e Contrato de Dados (Sprint 3)

> **Meta:** Tornar erros de schema detectáveis em carga, não silenciosamente em cálculo.

#### 4.3.1 Dataclasses de Domínio

- **RF-028:** DEVE existir um módulo `dashboards/domain/schema.py` com `@dataclass` ou Pydantic models para: `WorkItem`, `DimProject`, `DimType`, `DimPerson`.
- **RF-029:** Os campos obrigatórios e opcionais de cada dataclass DEVEM refletir o schema atual do Excel model (`Fato_Items`, `Dim_Projeto`, `Dim_Tipo`).
- **RF-030:** As dataclasses DEVEM usar tipos Python precisos (ex: `datetime` para datas, `float` para métricas, `Optional[str]` para campos nullable).

#### 4.3.2 Validação de Schema na Carga

- **RF-031:** A função `load_model_data()` em `data_processing.py` DEVE validar a presença de todas as colunas obrigatórias do Excel model após a carga.
- **RF-032:** Se colunas obrigatórias estiverem ausentes, o sistema DEVE lançar uma exceção explícita com a lista de colunas faltantes (ex: `SchemaValidationError: missing columns ['DataDone', 'LeadTime_Dias']`).
- **RF-033:** DEVE existir um `TypedDict` para os DataFrames de entrada das funções de métricas, documentando as colunas esperadas.

---

### Épico 4: Extração de Domínio — Esvaziamento do God Object (Sprint 4)

> **Meta:** Reduzir `dashboard_full.py` abaixo de 5.000 LOC, extraindo domínios de portfólio, finanças e pessoas.

#### 4.4.1 Extração de Callbacks

- **RF-034:** Os 9 callbacks de `dashboard_full.py` DEVEM ser organizados em módulos separados dentro de `dashboards/callbacks/` (ex: `callbacks/portfolio.py`, `callbacks/metrics.py`, `callbacks/people.py`).
- **RF-035:** Cada módulo de callback DEVE registrar suas rotas via função `register_callbacks(app)` chamada no entry point.
- **RF-036:** `dashboard_full.py` NÃO DEVE conter lógica de cálculo de métricas — apenas orquestração de callbacks e layout.

#### 4.4.2 Extração do Domínio de Portfólio

- **RF-037:** Toda lógica de portfólio atualmente em `dashboard_full.py` (filtros, roadmap status, downstream maps, GMUD) DEVE ser movida para `dashboards/domain/portfolio/`.
- **RF-038:** `dashboards/portfolio/functions.py` existente DEVE ser integrado ao novo módulo de domínio, sem duplicação.

#### 4.4.3 Extração dos Domínios de Finanças e Pessoas

- **RF-039:** Toda lógica de CAPEX e custo de times atualmente em `dashboard_full.py` DEVE ser movida para `dashboards/domain/finance/`.
- **RF-040:** Toda lógica de capacidade e identidade de pessoas atualmente em `dashboard_full.py` DEVE ser movida para `dashboards/domain/people/`.

#### 4.4.4 Reorganização de Layout

- **RF-041:** A estrutura de layout (definição de tabs, páginas, containers HTML) DEVE ser separada em `dashboards/layout/` com um módulo por página/tab.
- **RF-042:** `dashboard_full.py` ao final do Sprint 4 DEVE ter no máximo 5.000 LOC e conter apenas: inicialização do app Dash, registro de callbacks e definição do layout de alto nível.

---

## 5. Requisitos Não Funcionais

- **RNF-001 — Paridade Funcional:** Nenhuma feature existente deve ser removida ou ter comportamento alterado durante a refatoração. Todos os 4 dashboards (Full, Corporativo, SPAF, Process Mining) devem continuar funcionando identicamente para os usuários finais.
- **RNF-002 — Performance:** O tempo de carregamento de qualquer tab NÃO DEVE aumentar mais de 10% em relação ao baseline medido antes de cada sprint de refatoração.
- **RNF-003 — Compatibilidade de Dependências:** Nenhuma nova dependência de runtime poderá ser adicionada sem aprovação explícita, exceto `pydantic-settings` (aprovada em ADR-002) e `pytest` + plugins de teste.
- **RNF-004 — Sem Regressão de Cálculo:** Os valores calculados por `time_metrics.py` e `data_processing.py` após refatoração DEVEM ser numericamente idênticos aos calculados antes, validados pelos testes de regressão do RF-017.
- **RNF-005 — Análise Estática:** Ao final do Sprint 2, o projeto DEVE ser executável com `mypy --strict` (ou configuração equivalente) nos módulos `dashboards/domain/` e `dashboards/infra/` sem erros.
- **RNF-006 — Nenhum Secret em VCS:** O repositório git NÃO DEVE conter nenhum valor sensível (URLs de modelos financeiros, custos de times, tokens de API) em nenhum arquivo rastreado.
- **RNF-007 — Testabilidade:** Qualquer função de domínio (métricas, normalização, filtros de portfólio) DEVE ser testável de forma isolada, sem inicializar o app Dash ou fazer chamadas externas.

---

## 6. Fora do Escopo (Explícito)

Os seguintes itens NÃO fazem parte desta iniciativa de refatoração:

| Item | Justificativa |
|------|--------------|
| Migração de Excel para Parquet/DuckDB | Mudança de fonte de dados; escopo separado (Sprint 5+) |
| Implementação de cache Redis | Requer infra adicional; sprint separado |
| Adição de novas features de dashboard | Zero novas features durante refatoração para controlar risco |
| Reescrita total de `dashboard_full.py` | Risco inaceitável sem cobertura de testes prévia |
| Mudança de stack (ex: substituir Dash por outro framework) | Fora do horizonte desta iniciativa |
| Integração com novos sistemas externos (além dos 4 atuais) | Escopo separado |
| Alteração de regras de negócio de métricas | Escopo de produto, não de refatoração |
| CI/CD automatizado com GitHub Actions | Desejável mas não mandatório nesta fase |

---

## 7. Dependências e Integrações

### 7.1 Dependências Técnicas

| Dependência | Tipo | Sprint | Responsável |
|------------|------|--------|-------------|
| `pydantic-settings` | Nova lib de runtime | Sprint 1 | Dev |
| `pytest` + `pytest-cov` | Nova lib de teste | Sprint 1 | Dev |
| `responses` (mock HTTP) | Nova lib de teste | Sprint 1 | Dev |
| `.env.local` com valores reais | Arquivo de configuração local | Sprint 1 | Dev + stakeholder que conhece os valores |
| Template `.env.local.example` | Documentação | Sprint 1 | Dev |

### 7.2 Dependências de Conhecimento

- **Mapeamento completo das 17 env vars:** Necessário antes de escrever `infra/env_config.py`. Verificar `run_local.py` e `shared/env_utils.py` para inventário completo.
- **Colunas obrigatórias do Excel model:** Necessário antes de implementar RF-031/RF-032. Extrair via inspeção de `data_processing.py` linhas 16–60.

### 7.3 Integrações Externas (sem mudanças)

Todas as 4 integrações externas (JIRA Cloud, Bitbucket, Google Workspace, S3) permanecem inalteradas em interface e comportamento. A refatoração apenas reorganiza o código que as consume — não altera protocolo, autenticação ou dados trocados.

---

## 8. Riscos e Mitigações

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|-------|--------------|---------|-----------|
| R-1 | Refatoração quebra cálculo de métrica sem ser detectada | Média | Alto | Testes de regressão com fixtures antes de qualquer extração (RF-015 a RF-019) |
| R-2 | Ciclos de dependência mais profundos que os 3 identificados | Média | Médio | Executar análise completa com `pydeps` ou `importlab` antes do Sprint 1 |
| R-3 | `dashboard_full.py` tem dependências implícitas em estado global | Alta | Alto | Mapear todos os `global` e variáveis de módulo antes de extrair callbacks |
| R-4 | Migração de `.env.local` quebra ambiente de desenvolvimento de outros devs | Baixa | Alto | Documentar `.env.local.example` + comunicar mudança antes de merge |
| R-5 | Pydantic Settings incompatível com alguma env var de formato especial | Baixa | Médio | Testar parsing de JSON em env vars com `pydantic-settings` antes de adotar |
| R-6 | Tempo de refatoração subestimado, features ficam represadas | Média | Médio | Timebox fixo por sprint; priorizar O-1 a O-4 acima de O-5 e O-6 |
| R-7 | Regressão de performance por overhead de dataclasses (RF-028) | Baixa | Médio | Usar TypedDict em vez de dataclasses onde DataFrame é passado diretamente |

---

## 9. Critérios de Aceite Globais

Um sprint de refatoração só é considerado concluído quando **todos** os seguintes critérios forem atendidos:

- [ ] **CA-01:** O dashboard funciona end-to-end em ambiente local após as mudanças (todas as tabs carregam, todos os filtros funcionam).
- [ ] **CA-02:** Nenhum teste existente (se houver) regrediu. Todos os novos testes passam.
- [ ] **CA-03:** `git grep "import dashboard_full"` retorna zero resultados em módulos-folha (após Sprint 1).
- [ ] **CA-04:** `git grep "os.getenv\|os.environ"` retorna zero resultados fora de `infra/env_config.py` (após Sprint 2).
- [ ] **CA-05:** `git grep -r "hardcoded_value"` — nenhum valor financeiro (URLs de modelos, custos mensais) aparece em arquivos rastreados pelo git.
- [ ] **CA-06:** `pytest --cov=dashboards/metrics --cov=dashboards/core tests/` reporta ≥ 80% de cobertura nas linhas cobertas (após Sprint 2).
- [ ] **CA-07:** `dashboard_full.py` tem menos de 5.000 LOC ao final do Sprint 4 (`wc -l dashboard_full.py`).
- [ ] **CA-08:** Código review aprovado por pelo menos um par antes de cada merge de sprint.

---

## 10. Glossário

| Termo | Definição |
|-------|-----------|
| **God Object** | Anti-pattern onde um único módulo concentra responsabilidades de múltiplos domínios. Aqui: `dashboard_full.py`. |
| **Ciclo de dependência** | Situação onde módulo A importa B que importa A (direta ou indiretamente), impedindo análise estática e testes isolados. |
| **Lead Time** | Tempo total desde a criação de um item no JIRA até sua conclusão (`DataDone - DataCriacao`). |
| **Cycle Time** | Tempo desde o início do trabalho ativo até a conclusão do item. |
| **Classe de Serviço** | Categorização de prioridade de um item: Standard, Expedite, Fixed Date, Intangible Job. |
| **ETL Pipeline** | Extract-Transform-Load: padrão de carregamento de dados (baixar → transformar → cachear → renderizar). |
| **Monolito Modular** | Arquitetura onde o sistema é deployado como um único processo mas organizado internamente em módulos com separação de responsabilidades. |
| **DataLoader genérico** | Componente que abstrai download, hashing e cache de qualquer fonte de dados, parametrizável por parser. |
| **Pydantic Settings** | Biblioteca Python que usa modelos Pydantic para ler e validar variáveis de ambiente com type safety. |
| **WorkItem** | Entidade de domínio representando um item de trabalho (issue JIRA) com todos seus atributos calculados e normalizados. |
| **Shim de importação** | `__init__.py` que re-exporta funções de nova localização para manter compatibilidade com imports existentes durante migração incremental. |
| **TypedDict** | Tipo Python que define um dicionário com chaves e tipos esperados, usado para documentar schemas de DataFrames. |

---

## Changelog

| Versão | Data | Autor | Alterações |
|--------|------|-------|------------|
| 1.0 | 2026-04-24 | John (PM) — BMAD | Versão inicial baseada na análise arquitetural retroativa de Winston. |
