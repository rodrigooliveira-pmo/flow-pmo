Indicadores default
Estrutura de Abas Criadas:

1. Dashboard (Original + APRIMORAMENTOS)
   - Projeto, Week Start
   - Desenvolvimento, Defeitos, Outro:
     * Taxa chegada, Throughput, WIP, WIP Age
     * Lead Time, P85 Lead Time
     * Eficiência Simples (original)
     * Eficiência Ajustada (desconta bloqueios e espera)
   - % Demanda de Falha / % Demanda de Valor

2. Adv - Fluxo (APRIMORADO)
   - Cycle Time Médio e Mediano
   - Tempo em Backlog Médio
   - Tempo até Primeiro Movimento
   - Eficiência Ajustada (desconta tempo de bloqueio e espera)
   - Tempo de Bloqueio Médio
   - Tempo de Espera Intermediária Médio
   - Taxa de Bloqueio (%)

3. Adv - Estabilidade
   - Desvio Padrão do Throughput
   - Coeficiente de Variação (%)
   - Lead Time P50, P75, P95
   - Intervalo de Confiança 95%

4. Adv - Saúde Fluxo
   - Taxa Conclusão (%)
   - Ratio Chegada/Throughput
   - Crescimento WIP (%)
   - Itens Vencidos

5. Adv - Qualidade
   - Debt Ratio (% Defeitos)
   - Razão Valor/Custo
   - Eficiência Média

6. Análise Dimensional
   - Throughput por Projeto, Responsável, Componente, Prioridade
   - Taxa de Defeitos por dimensão

7. Análise Tipos
   - % por Tipo de Problema (Bug, Feature, Tarefa, Suporte)
   - Lead Time por Tipo
   - Throughput por Subtipo

8. Tendências
   - Throughput semanal e média móvel (4 semanas)
   - Trend Direction (↑ ↓ →)
   - WIP e Lead Time média móvel

9. Tendências Completas (NOVO)
   - Throughput com Trend e Momentum
   - WIP com Trend e Momentum
   - Lead Time com Trend e Momentum
   - Cycle Time (média móvel 4s)
   - Backlog Time (média móvel 4s)
   - Eficiência com análise de tendência
   - P85 Lead Time com média móvel

10. Throughput por Tipo (NOVO)
   - Throughput semanal segmentado por tipo de item
   - P85 Lead Time por tipo
   - Eficiência por tipo
   - Trend Direction (↑ ↓ →) para cada tipo
   - Momentum (aceleração/desaceleração)

11. Análise Eficiência (NOVO - Detalhado por Item)
   - ID, Projeto, Tipo de trabalho
   - Lead Time com breakdown por componente:
     * Tempo em Backlog (Sprint Backlog → In Progress)
     * Tempo de Execução (In Progress → Done)
     * Tempo de Bloqueio (Blocked Days)
     * Tempo em Espera Intermediária (Ready to..., Staging, etc.)
     * Outros Tempos (não contabilizados)
   - Eficiência Simples vs Ajustada
   - Diferença de Eficiência (ganho com ajuste)
   - Detalhes de fontes de espera

12. WIP por Pessoa
   - WIP Médio semanal por pessoa
   - WIP Máximo durante a semana
   - Items Ativos no fim da semana
   - Segmentado por Projeto e Responsável



   DIMENSÕES (Dimension Tables):
  - Dim_Projeto: 4 registros
  - Dim_Data: 1079 registros
  - Dim_Tipo: 3 registros
  - Dim_Responsavel: 40 registros
  - Dim_Prioridade: 5 registros

FATOS (Fact Table):
  - Fato_Items: 4188 registros (work items)

Colunas Principais da Tabela de Fatos:
  - Chaves Estrangeiras: ProjetoID, TipoID, ResponsavelID, ComponenteID, PrioridadeID
  - Métricas: LeadTime_Dias, TempoBacklog_Dias, TempoExecucao_Dias, Eficiencia
  - Indicadores: Concluido, Bloqueado, StoryPoints

======================================================================
RELACIONAMENTOS SUGERIDOS NO PODER BI:
======================================================================
Fato_Items[ProjetoID] → Dim_Projeto[ProjetoID]
Fato_Items[TipoID] → Dim_Tipo[TipoID]
Fato_Items[ResponsavelID] → Dim_Responsavel[ResponsavelID]
Fato_Items[ComponenteID] → Dim_Componente[ComponenteID]
Fato_Items[PrioridadeID] → Dim_Prioridade[PrioridadeID]
Fato_Items[DataDone] → Dim_Data[Data] (para análises por data)