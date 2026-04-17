# Auditoria de Redundância Funcional — Flow PMO

Data: 2026-04-17

## Resumo Executivo

O `dashboard_full.py` usa funções estatísticas centralizadas (`exact_empirical_percentile`, `time_metric_series`, `add_statistical_lines`) importadas de `dashboards/metrics/time_metrics.py` em **87 pontos** do código. A camada de cálculo estatístico está bem consolidada. O problema real de redundância está em **como** diferentes abas recalculam o mesmo dado sem compartilhar lógica de filtro e escopo.

---

## Padrão Identificado: "Fonte da Verdade" vs. Variações

### Lead Time

| Coluna | Semântica | Usado em |
|---|---|---|
| `LeadTime_Dias` | Lead time cru do modelo (DataBacklog → DataDone) | aba Throughput Breakdown, Estatística, fallback geral |
| `LeadTime_Selected_Dias` | Lead time recalculado com início selecionado pelo filtro de etapas | Serviço e SLA, Lead Time, Work Item Age, WIP, Painel Fluxo |
| `LeadTime_Custom_Dias` | Lead time com datas customizadas de etapas do downstream | aba Análise Fluxo (CFD detalhado) |

**Problema:** Quando uma aba usa `LeadTime_Dias` e outra usa `LeadTime_Selected_Dias` para "o mesmo gráfico", os números divergem. Isso confunde o usuário.

**Funções que recalculam lead time de forma similar mas com pequenas diferenças:**

1. `compute_weekly_service_metrics` (linha ~14853) — calcula LT por semana para Serviço e SLA
2. `build_service_lead_time_breakdown` (linha ~10348) — calcula LT por dimensão (tipo, responsável, etc.)
3. `build_lead_time_comparable_scope` (importada de `time_metrics`) — calcula LT por escopo comparável
4. Dentro de `render_tab → tab-lead-time` — recalcula percentis inline sem chamar função dedicada
5. Dentro de `render_tab → tab-corporativo` — via `layout_corporativo` que chama funções do módulo `corporativo_metrics.py`

**Redundância real:** As abas `tab-lead-time` e `tab-performance` calculam os mesmos percentis (P50, P85) do mesmo DataFrame filtrado. A diferença é só visual (uma exibe histograma, a outra exibe scatter + SLA).

---

### Throughput

| Função | Uso | Aba |
|---|---|---|
| `build_monthly_product_throughput_breakdown` | Throughput por produto/mês | tab-throughput-breakdown |
| `build_service_throughput_breakdown` | Throughput por dimensão (semanal) | tab-performance |
| `build_throughput_breakdown` | Throughput genérico por dimensão | tab-performance (seções alternativas) |
| `filter_done_to_month` + `build_period_evolution_sustainability_breakdown` | Throughput do mês atual | tab-throughput-breakdown |
| `build_monthly_throughput_percentage_by_type` (em time_metrics) | Throughput % por tipo/mês | tab-corporativo |
| `compute_weekly_service_metrics` | Throughput semanal | tab-performance |

**Observação:** 3 funções diferentes calculam throughput de formas ligeiramente distintas:
- `build_service_throughput_breakdown` agrupa por `bucket_freq='W-MON'` (semana)
- `build_monthly_product_throughput_breakdown` agrupa por mês e produto
- `build_throughput_breakdown` é genérica mas não temporal — só conta por dimensão

---

## Problemas Concretos de Redundância

### 1. Cálculo inline de percentis (não usa `exact_empirical_percentile`)

Existem pontos onde o código calcula `.quantile(0.85)` diretamente em vez de usar `exact_empirical_percentile`:

```python
# Exemplo de padrão ruim (visto em render_tab → tab-estatistica):
lt_p85 = df['LeadTime_Dias'].quantile(0.85)
# Deveria ser:
lt_p85 = exact_empirical_percentile(df['LeadTime_Dias'].dropna(), 0.85)
```

A função `exact_empirical_percentile` garante cálculo correto sem interpolação. `.quantile()` do pandas usa interpolação linear por padrão — o que pode divergir para amostras pequenas.

### 2. Recálculo de `weekly_hist_df` em múltiplos pontos

`compute_weekly_service_metrics` é chamada várias vezes com os mesmos argumentos dentro de `render_tab` para abas diferentes. O resultado não é cacheado entre chamadas da mesma requisição.

### 3. `LeadTime_Dias` vs `LeadTime_Selected_Dias` sem controle

Em `tab-throughput-breakdown`, o throughput é calculado corretamente, mas o lead time de referência (exibido como "Lead Time Médio do Período") usa `LeadTime_Dias` (cru) enquanto a aba `tab-performance` para o mesmo projeto no mesmo período usa `LeadTime_Selected_Dias` (filtrado). O usuário vê dois números diferentes para "lead time" dependendo de qual aba está olhando.

---

## Recomendações (para próxima fase)

### Quick wins (sem refatoração de render_tab)

1. **Criar `_compute_lt_percentiles(df, col='LeadTime_Selected_Dias')`** em `dashboards/metrics/time_metrics.py`:
   - Encapsula o padrão `exact_empirical_percentile(time_metric_series(df, col), p)`
   - Reduz duplicação de 20+ chamadas inline

2. **Padronizar `lead_col` padrão como `LeadTime_Selected_Dias`** em `build_service_lead_time_breakdown`:
   - Já está assim, mas adicionar validação explícita quando a coluna está ausente e fallback para `LeadTime_Dias`

3. **Documentar no código** quais abas usam qual coluna de lead time via constante:
   ```python
   LEAD_TIME_DISPLAY_COL = 'LeadTime_Selected_Dias'  # coluna padrão para display
   LEAD_TIME_BASE_COL = 'LeadTime_Dias'              # coluna cru do modelo
   ```

### Médio prazo (requer refatoração de render_tab)

4. **Criar `_prepare_service_metrics_payload(df, start_ts, end_ts, projeto, ...)`**:
   - Calcula percentis, throughput semanal e métricas de fluxo UMA vez
   - Todas as abas de serviço consomem o mesmo payload em cache

5. **Unificar as 3 funções de throughput** em uma única `build_throughput_series(df, freq, dimension_col)`:
   - Parametrizada por frequência (semanal, mensal, anual) e dimensão (tipo, produto, responsável)

---

## Arquivos Envolvidos

- `dashboard_full.py` — onde o problema vive
- `dashboards/metrics/time_metrics.py` — fonte da verdade para cálculos estatísticos (bem feito)
- `dashboards/metrics/corporativo_metrics.py` — métricas corporativas (bem feito, isolado)
- `dashboards/portfolio/functions.py` — portfólio (bem isolado, sem redundância com serviços)
