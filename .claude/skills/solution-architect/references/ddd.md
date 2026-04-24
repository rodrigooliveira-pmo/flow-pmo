# DDD Estratégico — Referência

Domain-Driven Design (Eric Evans) na dimensão estratégica trata de como organizar sistemas complexos em torno do domínio de negócio, definindo fronteiras claras entre modelos e como eles se relacionam.

---

## Conceitos Fundamentais

### Ubiquitous Language (Linguagem Ubíqua)
Uma linguagem compartilhada entre desenvolvedores e especialistas de domínio, usada tanto no código quanto nas conversas. Elimina traduções e ambiguidades.

**Sintoma de ausência:** o time fala "Cliente" mas o código tem `User`, `Account`, `Party` — ninguém sabe qual é qual.

**Como aplicar:**
- Identifique os termos que os especialistas de negócio usam naturalmente
- Use esses termos no código (classes, métodos, variáveis)
- Quando surgir ambiguidade, questione se há dois contextos diferentes em jogo

---

### Bounded Context (Contexto Delimitado)
A fronteira explícita dentro da qual um modelo de domínio é definido e consistente. Dentro do contexto, os termos têm significado preciso. Fora dele, o mesmo termo pode significar outra coisa.

**Exemplo:**
```
[Contexto: Vendas]          [Contexto: Suporte]
  Cliente = quem compra       Cliente = quem abriu chamado
  Pedido = transação           Pedido = solicitação de serviço
```

**Regra prática:** se você precisa de um `if` para saber qual tipo de "Cliente" está tratando, provavelmente há dois Bounded Contexts misturados.

---

### Context Map (Mapa de Contextos)
A representação explícita de como os Bounded Contexts se relacionam entre si. Documenta dependências, direção de influência e padrões de integração entre contextos.

#### Padrões de relacionamento entre contextos

| Padrão | Descrição | Quando usar |
|---|---|---|
| **Shared Kernel** | Dois contextos compartilham um submodelo comum | Times que colaboram estreitamente; alto custo de sincronização |
| **Customer-Supplier** | Um contexto (supplier) serve o outro (customer) | Dependência clara de direção; supplier deve considerar necessidades do customer |
| **Conformist** | O downstream adota o modelo do upstream sem questionar | Quando o upstream não negocia (ex: sistema legado, API de terceiro) |
| **Anti-Corruption Layer (ACL)** | Camada de tradução que isola o modelo interno do externo | Quando o modelo externo é ruim ou incompatível com o seu domínio |
| **Open Host Service** | O upstream publica um protocolo aberto para múltiplos consumidores | APIs públicas, integrações com muitos clientes |
| **Published Language** | Linguagem de integração documentada e estável (ex: JSON schema, Protobuf) | Contratos de integração formais entre contextos |
| **Separate Ways** | Dois contextos não se integram — cada um resolve seu próprio problema | Quando a integração custaria mais do que duplicar |
| **Big Ball of Mud** | Sem fronteiras claras; tudo integrado com tudo | ⚠️ Anti-padrão — use para identificar e planejar saída |

#### Exemplo de Context Map em ASCII

```
[Cadastro] ---(Customer-Supplier)---> [Compliance]
     |                                      |
     | (ACL)                                | (Conformist)
     v                                      v
[CVM/Bacen API]                    [Relatórios Regulatórios]

[Vendas] ---(Shared Kernel: Produto)--- [Estoque]
```

---

### Anti-Corruption Layer (ACL)
Uma camada de tradução entre o seu modelo de domínio e um modelo externo (legado, terceiro, ou outro contexto com linguagem diferente). Protege a integridade do seu modelo.

**Estrutura típica:**
```
[Seu Domínio]
     |
[ACL: Tradutor / Adapter]
     |
[Sistema Externo / Legado]
```

**Componentes da ACL:**
- **Translator** — converte objetos do modelo externo para o seu modelo interno
- **Facade** — simplifica a interface do sistema externo
- **Adapter** — adapta a interface técnica (protocolo, formato)

**Quando é necessária:**
- Integração com sistemas legados com modelo de dados ruim
- Consumo de APIs externas (ex: CVM, Bacen) onde você não controla o modelo
- Contexto Conformist onde você quer proteger seu domínio da influência externa

---

### Subdomains (Subdomínios)
Nem todas as partes do negócio merecem o mesmo investimento em modelagem. Classifique:

| Tipo | Descrição | Investimento recomendado |
|---|---|---|
| **Core Domain** | O que diferencia o negócio; vantagem competitiva | Alto — DDD completo, melhor time |
| **Supporting Domain** | Suporta o core mas não é diferencial | Médio — pode ser interno, mas simples |
| **Generic Domain** | Commodity; outros resolvem igual ou melhor | Baixo — compre ou use open source |

**Exemplo (contexto regulatório):**
- Core: motor de análise e classificação de atualizações regulatórias
- Supporting: gestão de usuários, notificações
- Generic: autenticação, email, armazenamento de arquivos

---

## Quando aplicar DDD estratégico

**Proativamente** (o arquiteto deve sugerir sem o usuário pedir):
- O usuário descreve um sistema com múltiplas áreas de negócio que se comunicam
- Há confusão de nomenclatura entre times ou sistemas ("mas o que você chama de X é o que eu chamo de Y")
- Um monolito está sendo quebrado em serviços — os cortes naturais são os Bounded Contexts
- Há integração com sistemas legados ou APIs externas que "contaminam" o modelo interno

**Explicitamente** (quando o usuário pedir):
- Desenhar um Context Map
- Definir Bounded Contexts para um sistema
- Escolher o padrão de integração entre dois contextos
- Avaliar se uma ACL é necessária

---

## DDD + Fowler + Falácias

DDD estratégico se complementa com as outras referências da skill:

| Situação | DDD | Fowler | Falácias |
|---|---|---|---|
| Quebrar monolito | Bounded Contexts definem os cortes | Strangler Fig para a migração | Falácia 1 (rede) e 8 (topologia) para o custo da distribuição |
| Integração entre sistemas | Context Map + ACL | EIP (padrões de mensageria) | Falácia 4 (rede segura) e 5 (topologia não muda) |
| Time novo no domínio | Ubiquitous Language primeiro | — | — |
| Microsserviços | Um serviço por Bounded Context (regra geral) | Microservices patterns de Fowler | Todas as falácias se aplicam |
