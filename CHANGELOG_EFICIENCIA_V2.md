# 📋 Changelog - Versão 2.0: Eficiência de Fluxo Aprimorada

**Data:** 12 de fevereiro de 2026  
**Versão Anterior:** 1.1 (Com WIP por Pessoa)  
**Versão Atual:** 2.0 (Com Eficiência Ajustada e Análise de Bloqueios)

---

## 🎯 Objetivo da v2.0

Aprimorar o indicador de **Eficiência de Fluxo** para que ele:
- Diferencie entre problemas do team vs problemas externos
- Considere tempos de bloqueio e espera intermediária
- Permitir diagnóstico mais preciso de gargalos
- Oferecer análise item-por-item do Lead Time Breakdown

---

## ✨ Principais Mudanças

### 1. Novas Funções Python

#### `detect_wait_stage_columns(df)`
- Detecta automaticamente colunas de espera ("Ready to...", "Staging", etc)
- Reutilizável para análises futuras

#### `calculate_enhanced_efficiency(row, wait_columns)`
- Calcula eficiência ajustada considerando:
  - Tempo de Bloqueio (Blocked Days)
  - Tempo em Espera Intermediária (filas em estágios)
- Fórmula: `Execution Time / (Lead Time - Blocked Days - Wait Stage Days)`
- Valores protegidos entre 0.0 e 2.0

#### `generate_efficiency_wait_time_analysis(consolidated_data)`
- Gera relatório detalhado item-por-item
- Mostra breakdown completo de Lead Time para cada item
- Compara Eficiência Simples vs Ajustada
- Identifica fontes de desperdício

### 2. Novos Campos na Tabela de Fatos
(Arquivo: PowerBI_Model_YYYYMMDD.xlsx)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `TempoBloqueioDias` | Número | Dias que item esteve bloqueado (via Blocked Days) |
| `TempoEsperaIntermediariaDias` | Número | Dias em filas intermediárias (Ready to..., Staging) |
| `EficienciaAjustada` | Número (0-2) | Execution/(Lead Time - Blocked - Wait) |

### 3. Novas Abas em Relatório Excel

#### Aba: "Análise Eficiência" (NOVA)
- **Granularidade:** Item-por-item
- **Colunas-chave:**
  - Lead Time Breakdown (Backlog + Execution + Blocked + Wait + Outros)
  - Eficiência Simples vs Ajustada
  - Diferença de Eficiência (ganho com ajuste)
  - Detalhes de Espera (quais estágios fizeram fila)
  
- **Uso:** Identificar items problemáticos e padrões de desperdício

#### Aba: "Dashboard" (ATUALIZADA)
- **Nova coluna:** `{Tipo} - Eficiência Ajustada` (semanal)
- Permite acompanhar a métrica ao longo do tempo
- Exemplo: "Desenvolvimento - Eficiência Ajustada" por semana

#### Aba: "Adv - Fluxo" (EXPANDIDA)
- **Novas métricas:**
  - Eficiência Ajustada Média
  - Tempo de Bloqueio Médio
  - Tempo de Espera Intermediária Médio
- Agora fornece visão completa de onde o tempo é gasto

### 4. Melhorias na Função `generate_consolidated_dashboard()`

**Antes:**
```python
avg_efficiency = np.mean(effs)  # Apenas eficiência simples
```

**Depois:**
```python
avg_efficiency = np.mean(effs_simple)           # Simples
avg_efficiency_adjusted = np.mean(effs_adjusted) # Ajustada (NOVO)
```

---

## 📊 Exemplos de Uso

### Cenário 1: Item Bloqueado Externamente
```
Item W1-100
Lead Time: 18 dias
├─ Backlog: 2 dias
├─ Execution: 4 dias ← Trabalho real
├─ Blocked: 10 dias ⚠️ (aguardando infra)
├─ Wait Intermediate: 1 dia
└─ Outros: 1 dia

Eficiência Simples: 4/18 = 22%
Eficiência Ajustada: 4/(18-10-1) = 4/7 = 57%

Conclusão: Team executou bem (57%), problema foi externo.
```

### Cenário 2: Item em Fila
```
Item BF-045
Lead Time: 15 dias
├─ Backlog: 3 dias
├─ Execution: 3 dias ← Trabalho real
├─ Blocked: 0 dias
├─ Wait Intermediate: 7 dias ⚠️ (fila em QA)
└─ Outros: 2 dias

Eficiência Simples: 3/15 = 20%
Eficiência Ajustada: 3/(15-0-7) = 3/8 = 37%

Conclusão: Gargalo de teste. Aumentar capacidade de QA.
```

### Cenário 3: Fluxo Saudável
```
Item S1-010
Lead Time: 10 dias
├─ Backlog: 1 dia
├─ Execution: 7 dias ← Trabalho real
├─ Blocked: 0 dias
├─ Wait Intermediate: 0 dias
└─ Outros: 2 dias

Eficiência Simples: 7/10 = 70% ✓
Eficiência Ajustada: 7/10 = 70% ✓

Conclusão: Fluxo limpo, team executando bem.
```

---

## 🔧 Arquivos Alterados

### Python (dash_board_metricas.py)

**Adições:**
- Linhas 22-71: Funções `detect_wait_stage_columns()` e `calculate_enhanced_efficiency()`
- Linhas 522-610: Função `generate_efficiency_wait_time_analysis()`
- Linhas 310-327: Cálculo de eficiência ajustada em `generate_consolidated_dashboard()`
- Linhas 480-530: Novos campos em `generate_advanced_flow_metrics()`
- Linhas 1725-1730: Chamada para gerar análise de eficiência
- Linhas 1763-1765: Salvar aba "Análise Eficiência" no Excel

**Alterações:**
- Função `generate_consolidated_dashboard()`: Agora calcula DUAS eficiências (simples + ajustada)
- Função `process_multiple_csv_files()`: Agora inclui aba "Análise Eficiência" no relatório

### Documentação (Markdown)

**Novos Arquivos:**
- `INDICADORES_EFICIENCIA_DETALHADO.md` - Documentação técnica completa

**Arquivos Atualizados:**
- `RESUMO_EXECUTIVO.md` - Adicionou referências às novas métricas
- `ARQUITETURA_MODELO.md` - Adicionou novos campos na tabela de fatos
- `INSTRUCOES_POWERBI.md` - Adicionou seção sobre novo painel e exemplos
- `CHANGELOG_EFICIENCIA_V2.md` - Este arquivo

---

## 📈 Impacto para Usuários

### Dashboard Excel (dashboard_output_*.xlsx)

**Antes:** 10 abas
**Depois:** 11 abas (+ "Análise Eficiência")

**Antes:** 2 métricas de eficiência por item
**Depois:** 3 métricas + breakdown de tempos

### Power BI

**Opção 1: Continuar com v1.1**
- Tudo funciona igual
- Power BI não será afetado
- Falta a nova análise de bloqueios

**Opção 2: Atualizar para v2.0** (RECOMENDADO)
1. Execute `dash_board_metricas.py` versão 2.0
2. Importar novo `PowerBI_Model_*.xlsx` no Power BI
3. Adicionar medidas DAX para Eficiência Ajustada
4. Criar novo painel "Eficiência de Fluxo"
5. Usar análise para identificar gargalos

---

## 🔄 Como Atualizar

### Para Usuários Python

1. **Backup dos dados antigos:**
   ```
   Copiar C:\Users\W1 TI\OneDrive - W1\Documentos\Dados\PowerBI_Model_*.xlsx
   Para: C:\backup\powerbI_model_v1_backup.xlsx
   ```

2. **Execute o novo script:**
   ```powershell
   cd "C:\Users\W1 TI\OneDrive - W1\Documentos\Python"
   python dash_board_metricas.py
   ```

3. **Novos arquivos serão gerados:**
   - `PowerBI_Model_20260212_HHMMSS.xlsx` (com novos campos)
   - `dashboard_output_20260212_HHMMSS.xlsx` (com 11 abas)

### Para Usuários Power BI

1. **Atualizar data source:**
   - Power BI Desktop > Get Data > Excel
   - Selecionar novo arquivo PowerBI_Model_*.xlsx

2. **Atualizar relacionamentos:**
   - Os mesmos relacionamentos funcionam
   - Nenhuma mudança necessária

3. **Adicionar novas medidas DAX (Opcional):**
   ```dax
   Eficiencia Ajustada Media = 
   AVERAGEX(Fato_Items, 
     DIVIDE(
       Fato_Items[TempoExecucao_Dias],
       MAX(1, Fato_Items[LeadTime_Dias] - 
           IFERROR(Fato_Items[TempoBloqueioDias], 0) - 
           IFERROR(Fato_Items[TempoEsperaIntermediariaDias], 0))
     )
   )
   ```

4. **Criar novo painel (Opcional):**
   - Nova página "Eficiência de Fluxo"
   - Visualizações recomendadas em `INDICADORES_EFICIENCIA_DETALHADO.md`

---

## ⚠️ Notas Importantes

### Compatibilidade Retroativa
- ✅ v2.0 gera todos os campos de v1.1 (WIP_Dias, EmWIP, etc)
- ✅ Arquivos v1.0 e v1.1 continuam funcionando
- ✅ Não é necessário descartar dados antigos

### Detecção de Colunas de Espera
- A função `detect_wait_stage_columns()` busca palavras-chave:
  - "ready", "staging", "waiting", "pending", "queue", "hold"
- Se seu rastreamento usar outros nomes, adicionar manualmente
- Editar arquivo: Abrir arquivo CSV e procurar por nomes de colunas

### Dados Históricos
- ⚠️ Campos de bloqueio/espera SÓ serão calculados para items com dados completos
- Se um item não tiver coluna "Blocked Days", o sistema usa 0
- Se não houver colunas de espera, o sistema detectará automaticamente

---

## 📚 Documentação Relacionada

| Documento | Propósito |
|-----------|----------|
| `INDICADORES_EFICIENCIA_DETALHADO.md` | **NOVO** - Guia técnico completo da nova métrica |
| `RESUMO_EXECUTIVO.md` | Visão geral da solução (ATUALIZADO) |
| `ARQUITETURA_MODELO.md` | Estrutura de dados (ATUALIZADO) |
| `INSTRUCOES_POWERBI.md` | Guia Power BI (ATUALIZADO) |
| `MEDIDAS_DAX.txt` | Medidas DAX (pode precisar adicionar novas) |

---

## 🎯 Próximas Melhorias Consideradas

1. **Análise de Causas Raiz:** Machine learning para identificar padrões de bloqueios
2. **Previsão de Unblock:** Estimar quanto tempo até item saindo de bloqueio
3. **Automação de Alertas:** Notificar quando bloqueio > 5 dias
4. **Integração com Slack:** Postar status de items críticos
5. **Dashboard Mobile:** Versão adaptada para celular

---

## 📞 Suporte

**Dúvidas sobre v2.0?**
- Consulte: `INDICADORES_EFICIENCIA_DETALHADO.md`
- Seção: "Como Interpretar os Resultados"

**Issue: Números não parecem corretos?**
- Verifique se coluna "Blocked Days" existe no CSV original
- Se não, o sistema assumirá 0 bloqueios

**Quer reverter para v1.1?**
- Use backup criado antes da atualização
- Reexecute script antigo

---

**Versão:** 2.0  
**Status:** ✅ Pronto para produção  
**Data de Liberação:** 2026-02-12  
**Próxima revisão:** 2026-02-19
