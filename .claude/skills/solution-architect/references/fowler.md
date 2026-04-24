# Referência: Martin Fowler — Padrões e Princípios

## Índice
1. [PoEAA — Padrões de Aplicações Enterprise](#poeaa)
2. [EIP — Padrões de Integração Enterprise](#eip)
3. [Refactoring — Evolução de Sistemas](#refactoring)
4. [Microservices — Arquitetura Moderna](#microservices)

---

## 1. PoEAA — Padrões de Aplicações Enterprise {#poeaa}
*Fonte: Patterns of Enterprise Application Architecture (2002)*

### Camadas arquiteturais
- **Presentation Layer** — interface com o usuário ou sistema externo
- **Domain Layer** — lógica de negócio
- **Data Source Layer** — persistência e acesso a dados

### Padrões de Domínio
| Padrão | Quando usar |
|---|---|
| **Transaction Script** | Lógica simples, poucos objetos de domínio. Fácil de entender, difícil de escalar. |
| **Domain Model** | Lógica complexa com muitas regras. Objetos ricos em comportamento. |
| **Table Module** | Uma instância por tabela do banco. Bom para lógica orientada a conjuntos de dados. |
| **Service Layer** — define a fronteira da aplicação com um conjunto de operações disponíveis. Coordena respostas da aplicação, delega para o domínio. |

### Padrões de Dados
| Padrão | Descrição |
|---|---|
| **Active Record** | Objeto que encapsula uma linha do banco e contém lógica de domínio. Simples, mas acopla domínio à persistência. |
| **Data Mapper** | Separa objetos de domínio do banco. Mais complexo, mais flexível. |
| **Repository** | Abstrai a coleção de objetos de domínio. Isola o domínio dos detalhes de persistência. |
| **Unit of Work** | Mantém o controle de objetos afetados por uma transação de negócio. |
| **Identity Map** | Garante que cada objeto é carregado apenas uma vez por transação. Evita duplicatas. |
| **Lazy Load** | Carrega dados relacionados apenas quando necessário. Cuidado com N+1. |

### Padrões de Sessão e Estado
- **Client Session State** — estado no cliente (cookie, token). Sem memória no servidor.
- **Server Session State** — estado no servidor. Simples, mas dificulta escalabilidade horizontal.
- **Database Session State** — estado no banco. Escalável, mas mais lento.

---

## 2. EIP — Padrões de Integração Enterprise {#eip}
*Fonte: Enterprise Integration Patterns — Hohpe & Woolf (prefaciado e referenciado por Fowler)*

### Estilos de Integração
1. **File Transfer** — sistemas compartilham arquivos. Simples, mas acoplamento temporal.
2. **Shared Database** — sistemas compartilham banco. Alto acoplamento, difícil de evoluir.
3. **Remote Procedure Invocation** — chamada direta (REST, gRPC). Síncrono, acoplamento de disponibilidade.
4. **Messaging** — comunicação assíncrona via mensagens. Desacoplado, mais complexo.

### Padrões de Mensageria
| Padrão | Uso |
|---|---|
| **Message Channel** | Canal por tipo de mensagem |
| **Message Router** | Roteia mensagens com base no conteúdo |
| **Message Filter** | Remove mensagens que não interessam ao receptor |
| **Message Translator** | Converte formato entre sistemas |
| **Dead Letter Channel** | Canal para mensagens que não puderam ser processadas |
| **Idempotent Receiver** | Receptor que processa a mesma mensagem múltiplas vezes sem efeitos colaterais |
| **Correlation ID** | Identifica quais mensagens pertencem a uma mesma transação |

### Padrões de composição
- **Aggregator** — combina múltiplas mensagens relacionadas em uma só
- **Scatter-Gather** — envia para múltiplos destinatários e agrega respostas
- **Process Manager** — orquestra um fluxo de mensagens com estado (saga)

---

## 3. Refactoring — Evolução de Sistemas {#refactoring}

### Princípios gerais
- Refactoring é mudança de estrutura **sem alterar comportamento observável**
- Faça em pequenos passos, com testes como rede de segurança
- Elimine *code smells* antes de adicionar funcionalidade

### Padrões para sistemas legados e migração
| Padrão | Descrição |
|---|---|
| **Strangler Fig** | Substitui partes do sistema legado incrementalmente. Novo sistema "estrangula" o antigo. |
| **Branch by Abstraction** | Cria abstração sobre o código a ser substituído, implementa novo por baixo, remove o antigo. |
| **Parallel Run** | Executa o sistema antigo e o novo em paralelo para validar equivalência. |
| **Feature Toggle** | Ativa/desativa funcionalidades sem deploy. Útil para migração gradual. |

### Sinais de alerta (code/design smells)
- **Divergent Change** — uma classe muda por razões diferentes → separar responsabilidades
- **Shotgun Surgery** — uma mudança exige edições em muitos lugares → consolidar
- **Feature Envy** — método usa mais dados de outra classe do que da sua → mover
- **God Class / Big Ball of Mud** — classe ou sistema que faz tudo → decompor
- **Primitive Obsession** — usar tipos primitivos onde objetos de valor fariam mais sentido

---

## 4. Microservices — Arquitetura Moderna {#microservices}
*Fonte: martinfowler.com/articles/microservices.html e trabalhos relacionados*

### Definição e características
Microsserviços são serviços pequenos, independentemente deployáveis, organizados em torno de capacidades de negócio, comunicando-se via APIs leves.

**Características-chave:**
- Deployability independente
- Organizado por domínio de negócio (não por camada técnica)
- Dados descentralizados — cada serviço tem seu próprio armazenamento
- Projetado para falha (Design for Failure)
- Automação de infraestrutura (CI/CD, containers)

### Monolito vs. Microsserviços — quando migrar?
Fowler defende o **Monolith First**: comece com monolito modular, migre quando os limites de domínio estiverem claros.

**Migre para microsserviços quando:**
- O time cresceu e há conflito de deploy entre equipes
- Partes do sistema têm requisitos de escala muito diferentes
- Os limites de domínio são bem compreendidos

**Não migre quando:**
- O domínio ainda está sendo explorado
- O time é pequeno
- Não há maturidade operacional (observabilidade, CI/CD, service mesh)

### Padrões de microsserviços relevantes
| Padrão | Descrição |
|---|---|
| **API Gateway** | Ponto de entrada único. Trata autenticação, roteamento, rate limiting. |
| **Backend for Frontend (BFF)** | API Gateway específico para cada tipo de cliente (mobile, web). |
| **Saga** | Gerencia transações distribuídas sem 2PC. Coreografia ou orquestração. |
| **CQRS** | Separa modelo de leitura do modelo de escrita. Útil quando leitura e escrita têm cargas muito diferentes. |
| **Event Sourcing** | Armazena eventos em vez de estado atual. Auditabilidade total, complexidade de query. |
| **Circuit Breaker** | Interrompe chamadas a serviço com falha para evitar cascata. |
| **Sidecar** | Funcionalidades transversais (logs, tracing, segurança) em container separado. |

### Armadilhas comuns
- **Distributed Monolith** — microsserviços acoplados que precisam ser deployados juntos
- **Chatty Services** — muitas chamadas síncronas entre serviços (viola Falácias 1 e 2)
- **Shared Database** — múltiplos serviços acessando o mesmo banco (destrói independência)
- **Premature Decomposition** — separar antes de entender os limites de domínio

---

## 5. Avaliação de Stacks Estruturantes {#stacks}

Stacks estruturantes são plataformas ou produtos que se tornam parte da "espinha dorsal" da arquitetura — API Management, WAF, Service Mesh, Message Broker, ESB, CDN, Identity Provider, etc. A decisão de adotar um desses produtos tem impacto de longo prazo e merece análise rigorosa.

### Framework de avaliação

Para qualquer stack estruturante, avalie as seguintes dimensões:

| Dimensão | Perguntas-chave |
|---|---|
| **Problema resolvido** | Qual problema concreto justifica a adoção? Existe solução mais simples? |
| **Fit arquitetural** | O produto se encaixa no estilo arquitetural atual (monolito, microsserviços, híbrido)? |
| **Falácias cobertas** | Quais falácias ele ajuda a mitigar? Quais pode introduzir ou mascarar? |
| **TCO** | Licença + operação + curva de aprendizado + migração. Custo real vs. custo percebido. |
| **Risco de lock-in** | Quão difícil é sair? Existe alternativa open-source ou padrão aberto? |
| **Maturidade operacional** | O time tem capacidade de operar e evoluir esse produto? |
| **Complexidade adicionada** | O produto simplifica ou adiciona uma nova camada para gerenciar? |

### Principais categorias e trade-offs

#### API Management (ex: Kong, AWS API Gateway, Apigee, Azure APIM)
**Resolve:** autenticação centralizada, rate limiting, roteamento, observabilidade de APIs, versionamento.
**Risco:** pode se tornar um "ESB moderno" se regras de negócio migrarem para ele (antipadrão).
**Quando adotar:** múltiplos consumidores externos, necessidade de controle de acesso e SLA por cliente, portal de developer.
**Quando não adotar:** APIs internas simples com um único consumidor — overhead sem benefício.

#### WAF — Web Application Firewall (ex: AWS WAF, Cloudflare, F5)
**Resolve:** proteção contra ataques na camada de aplicação (OWASP Top 10, DDoS, bots).
**Diferença do API Gateway:** WAF é segurança perimetral (o que entra); API Gateway é roteamento e controle de acesso (quem pode chamar o quê).
**Quando adotar:** APIs expostas publicamente, conformidade com normas de segurança (ISO 27001, PCI, regulatório).
**Complementaridade:** WAF + API Gateway não são excludentes — WAF na borda, Gateway na camada de aplicação.

#### Service Mesh (ex: Istio, Linkerd, Consul Connect)
**Resolve:** mTLS automático entre serviços, observabilidade (tracing distribuído), circuit breaking, traffic shaping.
**Risco:** complexidade operacional alta. Curva de aprendizado significativa. Debugging mais difícil.
**Quando adotar:** muitos microsserviços (10+), necessidade de Zero Trust interno, equipe com maturidade em Kubernetes.
**Quando não adotar:** poucos serviços, time sem experiência em Kubernetes/service mesh — overhead não se justifica.

#### Message Broker vs. ESB
| Critério | Message Broker (ex: Kafka, RabbitMQ) | ESB (ex: MuleSoft, IBM MQ) |
|---|---|---|
| Modelo | Dados fluem; consumidores decidem o que fazer | Orquestração centralizada de integrações |
| Lógica de negócio | Nos consumidores | Pode ficar no ESB (antipadrão "fat ESB") |
| Escala | Alta | Moderada |
| Custo operacional | Médio-alto (Kafka) | Alto (licença + operação) |
| Quando usar | Eventos de domínio, alta vazão, múltiplos consumidores | Integrações legadas com transformações complexas |

**Princípio de Fowler:** prefira "Smart Endpoints, Dumb Pipes" — lógica nos serviços, não na infraestrutura de mensageria.

#### CDN (ex: Cloudflare, AWS CloudFront, Fastly)
**Resolve:** latência para conteúdo estático/cacheable, proteção DDoS, edge computing.
**Quando adotar:** conteúdo público com usuários geograficamente distribuídos, assets estáticos, APIs com respostas cacheáveis.
**Ponto de atenção:** CDN em frente a APIs dinâmicas requer política de cache cuidadosa — respostas desatualizadas podem ser piores que latência.

### Antipadrões comuns em stacks estruturantes
- **"Vamos resolver com um produto"** — produto sem problema claro definido
- **Fat ESB / Fat Gateway** — lógica de negócio migrada para a infraestrutura de integração
- **Vendor lock-in não percebido** — funcionalidades proprietárias sem plano de saída
- **Complexidade acidental** — adicionar Service Mesh para 3 serviços
- **Segurança por produto** — achar que o WAF dispensa validação na aplicação
