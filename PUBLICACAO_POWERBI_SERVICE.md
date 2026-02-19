# 🌐 Publicação no Power BI Service (Nuvem)

**Para compartilhar seus dashboards com o time via web**

---

## 📋 PRÉ-REQUISITOS

- [ ] Licença Power BI Pro (mínimo)
- [ ] Conta Office 365 da empresa
- [ ] Arquivo PBIX criado localmente
- [ ] Arquivo PowerBI_Model_20260211_135700.xlsx

---

## 🚀 PASSO A PASSO - PUBLICAÇÃO BÁSICA

### PASSO 1: Preparar o Relatório PBIX Localmente

```
1. Crie o relatório no Power BI Desktop com:
   - ✓ Dados importados (Mode: Import)
   - ✓ Relacionamentos criados
   - ✓ Medidas DAX definidas
   - ✓ Pelo menos 2 painéis criados
   - ✓ Filtros e slicers funcionando

2. Teste tudo localmente
3. Salve como: Relatorio_Metricas.pbix
```

### PASSO 2: Publicar no Power BI Service

```
4. No Power BI Desktop: Home → Publicar
5. Selecione o Workspace (ou "Meu Workspace" para testar)
6. Aguarde publicação (1-3 minutos)
7. Clique no link para abrir no navegador
```

### PASSO 3: Configurar Atualização de Dados

```
8. Power BI Service → Seu Relatório → Configurações
9. "Configurações de dados" → "Atualização Agendada"
10. Ativar: ✓ Manter dados atualizados
11. Frequência: Diária ou Semanal
12. Horário: 08:00 (fora de horários de pico)
```

---

## 📊 ESTRUTURA RECOMENDADA NO POWER BI SERVICE

### Workspace Sugerido
```
Workspace: "Métricas de Fluxo"

Conteúdo:
├── Datasets
│   └── PowerBI_Model_20260211
│       ├── Fato_Items (2000 registros)
│       ├── Dim_Projeto (4 registros)
│       ├── Dim_Data (400 registros)
│       ├── Dim_Responsavel (50 registros)
│       ├── Dim_Componente (60 registros)
│       ├── Dim_Tipo (5 registros)
│       └── Dim_Prioridade (5 registros)
│
├── Relatórios
│   ├── Dashboard Executivo
│   ├── Saúde do Fluxo
│   ├── Previsibilidade
│   ├── Performance Dimensional
│   ├── Qualidade & Rework
│   ├── Tendências (opcional)
│   ├── Capacidade (opcional)
│   └── Benchmarking (opcional)
│
└── Aplicativos
    └── App: "Métricas Técnicas" (para distribuição)
```

---

## 🔄 ATUALIZAR DADOS NA NUVEM

### Opção 1: Atualização Automática (Recomendada)

**Setup:**
```
1. Salve o arquivo PowerBI_Model_YYYYMMDD.xlsx no OneDrive
2. Power BI Service → Dataset → Configurações
3. "Atualização agendada" → Habilitar
4. Conectar ao arquivo no OneDrive (em vez de arquivo local)
5. Frequência: 1x/semana (terça at 07:00)
```

**Fluxo:**
```
Python Script Executa (Terça 06:00)
        ↓
Gera: PowerBI_Model_YYYYMMDD.xlsx no OneDrive
        ↓
Power BI Atualiza Dataset (07:00)
        ↓
Dashboard Reflete Dados Novos
```

### Opção 2: Atualização Manual

```
1. Execute script Python localmente
2. Salve novo arquivo PowerBI_Model_20260211_135700.xlsx
3. Power BI Desktop → Atualizar dados
4. Republicar (Home → Publicar)
5. Confirmar publicação no navegador
```

### Opção 3: Gateway (Advanced)

Se dados estiverem em SQL Server ou banco externo:
```
1. Instale "Power BI Gateway" no servidor
2. Configure conexão no gateway
3. Power BI Service usará gateway para refresh automático
4. Maior confiabilidade e frequência (até 48x/dia)
```

---

## 👥 COMPARTILHAR COM O TIME

### Compartilhamento por Workspace

**Acesso Completo (Team Member):**
```
1. Power BI Service → Seu Workspace → Acesso
2. Adicionar usuários (emails)
3. Funcionalidade: "Editor" ou "Contribuinte"
4. Envia convite automaticamente
```

**Acesso Restrito (Read-Only):**
```
1. Power BI Service → Seu Workspace → Acesso
2. Adicionar usuários com função "Visualizador"
3. Podem ver relatórios mas não editar
```

### Compartilhamento por App

**Para distribuição formal para o whole company:**

```
1. Seu Workspace → Criar aplicativo
2. Nome: "Métricas Técnicas"
3. Descrever propósito
4. Selecionar relatórios e dashboards
5. Publicar (Publish app)
6. Share link com time: https://app.powerbi.com/apps/...
7. Usuários instalam como "App" (fácil acesso)
```

---

## 📧 COMPARTILHAMENTO POR EMAIL

```
1. Seu Relatório → Share / Compartilhar
2. Adicionar emails (ex: diretor@empresa.com)
3. Mensagem: "Novo dashboard de métricas - clique para acessar"
4. Nível de permissão: Visualizar ou Editar
5. Enviar
```

---

## 🔐 SEGURANÇA & PERMISSÕES

### Níveis de Acesso

| Função | Pode Ver | Pode Editar | Pode Renovar | Pode Deletar |
|--------|----------|------------|--------------|-------------|
| **Admin** | ✅ | ✅ | ✅ | ✅ |
| **Membro** | ✅ | ✅ | ✅ | ✅ |
| **Contribuinte** | ✅ | ✅ | ❌ | ❌ |
| **Visualizador** | ✅ | ❌ | ❌ | ❌ |

**Recomendação:**
- Você: Admin
- Tech Leads: Membro
- Team: Visualizador (ou Contribuinte se quiserem criar relatórios)

### Row-Level Security (RLS)

Se cada um deve ver apenas seu próprio projeto:

```dax
// Em Dim_Projeto, adicionar coluna "ResponsavelProjeto"
// Criar role "Projeto_W1NNER"
// Filtro RLS: Dim_Projeto[ResponsavelProjeto] = USERNAME()
```

Isso garante que:
- João vê apenas W1NNER
- Maria vê apenas DATA&ANALYTICS
- Etc...

---

## 📱 MOBILE ACCESS

Seus dashboards funcionam no mobile (iPhone/Android):

### Instalar App
```
1. App Store / Google Play
2. Busque "Power BI"
3. Instale (gratuito)
4. Faça login com conta Enterprise
5. Veja seus relatórios no mobile
```

### Criar Layout Mobile

```
Power BI Desktop → View → Mobile Layout
┌─────────────────┐
│   Dashbaord     │
│     Mobile      │
├─────────────────┤
│ [KPI 1]         │
│ [KPI 2]         │
│ [Gráfico]       │
│ [Tabela]        │
└─────────────────┘
```

---

## 🚨 ALERTAS AUTOMÁTICOS

Se tiver Power BI Premium:

```
1. Seu Relatório → Mais opções (...)
2. "Gerenciar Alertas"
3. Criar alerta: "Se Debt Ratio > 40%, notificar-me"
4. Receberá email quando métrica ultrapassar threshold
```

---

## 📈 RELATÓRIOS PAGINÁVEIS (SSRS)

Para exportar como PDF automático (emails semanais):

```
Power BI Service → Criar "Relatório Paginável"
├── Formato: Otimizado para PRINT
├── Configuração: Agendado (toda segunda 09:00)
├── Entrega: Email automático para P.O. e Gerentes
└── Exemplo: Anexar PDF de "Pulse Weekly"
```

---

## 🔗 INTEGRAÇÃO COM TEAMS/SLACK

### Compartilhar no Teams

```
1. Relatório no Power BI → Compartilhar
2. Selecionar Teams channel
3. Pré-visualização automática no chat
4. Clique rápido para abrir no Power BI
```

### Conectar com Slack

```
1. Power BI Workspace → Configurações
2. "Integração Slack"
3. Conectar workspace Slack
4. Publicar alertas e relatórios
```

---

## 🎯 CHECKLIST PRÉ-PRODUÇÃO

Antes de publicar para o time:

- [ ] Todos os dados carregados corretamente
- [ ] Novembro 2024-2025 histórico disponível
- [ ] Relacionamentos testados (sem erros)
- [ ] Medidas DAX calculando corretamente
- [ ] 2-3 painéis principais prontos
- [ ] Filtros cruzados funcionando
- [ ] Paleta de cores consistente
- [ ] Labels clara em todos os gráficos
- [ ] Performance OK (< 3s para carregar)
- [ ] Publicado em Workspace (não "Meu Workspace")
- [ ] Acesso compartilhado com team
- [ ] Atualização agendada configurada

---

## ⚠️ PROBLEMAS COMUNS E SOLUÇÕES

### "Dataset falha ao atualizar"
```
Causa: Arquivo no OneD drive foi movido/deletado
Solução: 
1. Power BI Service → Dataset → Configurações
2. "Credenciais da fonte de dados"
3. Apontar para novo arquivo
```

### "Relatório carrega muito lentamente"
```
Causa: Muitos dados / muitos relacionamentos
Solução:
1. Aumentar capacidade (Power BI Premium)
2. Adicionar agregações
3. Reduzir período de dados históricos
```

### "Alguns usuários veem "?" nos números"
```
Causa: Permissão de dataset insuficiente
Solução:
1. Workspace → Acessar → Adicionar usuários
2. Dar "Contribuinte" no mínimo
```

---

## 🚀 PRÓXIMO PASSO: AUTOMAÇÃO PYTHON

Para atualizar automaticamente via script:

```python
# Schedule script to run weekly
# cron: 0 6 * * 2 (Tuesday 06:00)

import subprocess
subprocess.run([
    "python", 
    "dash_board_metricas.py"
])

# Salva novo arquivo em OneDrive
# Power BI atualiza automaticamente
```

---

## 📊 EXEMPLO DE ESTRUTURA FINAL

```
Power BI Service
│
├── Workspace: "Métricas Técnicas"
│   ├── Dataset: PowerBI_Model (atualizado 1x/semana)
│   │
│   ├── Relatórios:
│   │   ├── 📊 Pulse Executivo (C-Level)
│   │   ├── 📊 Saúde do Fluxo (Daily monitoring)
│   │   ├── 📊 Previsibilidade (For planning)
│   │   └── 📊 Performance (Team ranking)
│   │
│   └── Acesso:
│       ├── CEO: Admin
│       ├── Engineering Managers: Membro
│       ├── Tech Leads: Contribuinte
│       └── Team: Visualizador
│
└── App: "Métricas Técnicas"
    (Distributed to all staff)
```

---

## 💡 DICAS FINAIS

✅ Comece com um workspace privado (teste)  
✅ Conclua os 2 primeiros painéis antes de compartilhar  
✅ Peça feedback logo (iterate rápido)  
✅ Publica incrementalmente (não espere perfeição)  
✅ Mantenha dados sempre atualizados (confiança)  
✅ Documente cada métrica (evita dúvidas)  
✅ Treine o time (15 minutos é suficiente)  

---

**Toda esta infraestrutura está pronta. Você pode publicar hoje mesmo!**

Tempo estimado de publicação: **15 minutos**  
Tempo para compartilhar com team: **5 minutos**

---

**Gerado em:** 2026-02-11  
**Versão:** 1.0  
**Status:** ✅ PRONTO PARA PUBLICAÇÃO

