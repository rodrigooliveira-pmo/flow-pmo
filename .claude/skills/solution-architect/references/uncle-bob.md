# Referência: Robert C. Martin (Uncle Bob), Corpo Técnico Completo

*Base consolidada a partir de Clean Code (2008), The Clean Coder (2011), Clean Architecture (2017), Clean Agile (2019) e artigos publicados em [blog.cleancoder.com](https://blog.cleancoder.com).*

---

## Índice

1. [SOLID, princípios de design de classes](#solid)
2. [Component Principles, princípios de componentes](#components)
3. [Clean Architecture, a regra de dependência](#clean-arch)
4. [Screaming Architecture](#screaming)
5. [Clean Code, disciplinas de codificação](#clean-code)
6. [TDD, disciplina de teste primeiro](#tdd)
7. [Clean Coder, profissionalismo](#clean-coder)
8. [Clean Agile, retorno às raízes técnicas](#clean-agile)
9. [Integração com Fowler, DDD, Falácias e C4](#integracao)

---

## 1. SOLID, princípios de design de classes {#solid}

Os cinco princípios SOLID orientam o design orientado a objetos no nível da classe e do módulo, buscando código tolerante a mudanças, testável e compreensível.

### 1.1 SRP, Single Responsibility Principle

**Enunciado moderno:** um módulo deve ter uma, e apenas uma, razão para mudar, sendo essa razão um ator de negócio específico.

**Sintomas de violação:**
- Classe que muda por razões de marketing e de financeiro ao mesmo tempo.
- Métodos de cálculo, persistência e formatação vivendo na mesma classe.
- Commits frequentes no mesmo arquivo por times diferentes.

**Como aplicar:**
- Identifique os atores (quem pede mudanças nesse código) e separe por ator.
- Extraia classes por responsabilidade, mantendo fachada coesa quando necessário.
- Use Facade para orquestrar sem reintroduzir o acoplamento.

**Armadilha comum:** confundir SRP com "classe pequena". Tamanho é consequência, não critério.

---

### 1.2 OCP, Open/Closed Principle

**Enunciado:** entidades devem estar abertas para extensão, porém fechadas para modificação.

**Sintomas de violação:**
- Cadeias de `if/else` ou `switch` crescendo a cada novo caso de negócio.
- Alteração de classe estável para cada novo tipo de produto, canal ou cliente.
- Regressões recorrentes em código maduro.

**Como aplicar:**
- Use polimorfismo em substituição a condicionais sobre tipo.
- Proteja os módulos de alto nível contra variações dos módulos de baixo nível.
- Defina pontos de extensão onde a variabilidade é conhecida (Strategy, Template Method, Plugin).

**Armadilha comum:** antecipar variabilidade inexistente, criando abstrações especulativas. Prefira introduzir OCP no segundo ou terceiro caso semelhante (regra de três).

---

### 1.3 LSP, Liskov Substitution Principle

**Enunciado:** subtipos devem ser substituíveis pelos seus tipos base sem alterar a correção do programa.

**Sintomas de violação:**
- Subclasse lançando `UnsupportedOperationException`.
- Código do cliente checando o tipo concreto com `instanceof` antes de agir.
- Pré-condições fortalecidas ou pós-condições enfraquecidas em subclasses.
- Classe `Quadrado` herdando de `Retângulo` e sobrescrevendo setters para manter igualdade de lados.

**Como aplicar:**
- Valide contratos explicitamente (pré, pós e invariantes).
- Prefira composição a herança quando o relacionamento não for genuinamente "é um".
- Modele diferenças semânticas com interfaces distintas, não hierarquias forçadas.

---

### 1.4 ISP, Interface Segregation Principle

**Enunciado:** nenhum cliente deve ser forçado a depender de métodos que não usa.

**Sintomas de violação:**
- Interfaces com dezenas de métodos usadas parcialmente por cada cliente.
- Recompilação em cascata por mudança em método irrelevante ao chamador.
- Acoplamento transitivo via interface gorda.

**Como aplicar:**
- Decomponha interfaces gordas em interfaces coesas por papel (role interfaces).
- Cada cliente depende apenas do que usa; um mesmo objeto pode implementar várias interfaces pequenas.
- Em linguagens dinâmicas, ISP se manifesta evitando dependência de métodos não utilizados.

---

### 1.5 DIP, Dependency Inversion Principle

**Enunciado:** módulos de alto nível não devem depender de módulos de baixo nível; ambos devem depender de abstrações. Abstrações não devem depender de detalhes; detalhes devem depender de abstrações.

**Sintomas de violação:**
- Regra de negócio importando ORM, driver de banco, cliente HTTP ou biblioteca de framework.
- Impossibilidade de testar caso de uso sem subir infraestrutura.
- Troca de banco ou fila exige alterar o domínio.

**Como aplicar:**
- Defina interfaces no lado do consumidor (domínio), implementando-as na borda (infra).
- Use injeção de dependência; evite `new` de objetos voláteis dentro do núcleo.
- DIP é o mecanismo técnico que torna a Clean Architecture possível.

**Regra prática:** se você consegue trocar o banco por um stub em memória sem tocar no caso de uso, DIP está bem aplicado.

---

## 2. Component Principles {#components}

Componentes, no sentido de Uncle Bob, são unidades de deploy: JARs, DLLs, gems, pacotes Python, módulos npm. Os princípios dividem-se em coesão (o que está dentro) e acoplamento (como se relacionam).

### 2.1 Coesão de componentes

| Princípio | Sigla | Essência |
|---|---|---|
| Reuse/Release Equivalence | **REP** | A unidade de reúso é a unidade de release. O que é reusado precisa ser versionado e lançado. |
| Common Closure | **CCP** | Classes que mudam juntas, pelas mesmas razões e ao mesmo tempo, ficam no mesmo componente. |
| Common Reuse | **CRP** | Classes que são usadas juntas ficam juntas; não force clientes a depender do que não usam. |

**Tensão entre os três:** REP e CCP pressionam por componentes maiores; CRP pressiona por componentes menores. O arquiteto balanceia conforme a fase do sistema: projetos novos costumam priorizar CCP (facilitando evolução); projetos maduros migram rumo a CRP (facilitando reúso).

**Analogia do diagrama de tensão (Uncle Bob):** os três princípios formam um triângulo; escolher dois penaliza o terceiro.

---

### 2.2 Acoplamento de componentes

| Princípio | Sigla | Essência |
|---|---|---|
| Acyclic Dependencies | **ADP** | O grafo de dependência entre componentes deve ser acíclico. |
| Stable Dependencies | **SDP** | Dependa sempre na direção da estabilidade. |
| Stable Abstractions | **SAP** | Componentes estáveis devem ser abstratos; componentes instáveis devem ser concretos. |

**ADP, como quebrar ciclos:**
1. Aplicar DIP, introduzindo interface no componente dependente.
2. Criar componente novo com as abstrações compartilhadas.
3. Mover o ponto de dependência comum para cima na hierarquia.

**SDP, como medir estabilidade:**
- Fan-in: número de classes de fora que dependem deste componente.
- Fan-out: número de classes que este componente usa de fora.
- Instabilidade **I = Fan-out / (Fan-in + Fan-out)**. Valor próximo de 0 indica componente estável; próximo de 1, instável.

**SAP, abstração e estabilidade juntas:**
- Abstração **A = interfaces ou classes abstratas / total de classes do componente**.
- Na "main sequence" (linha principal), **A + I ≈ 1**. Componentes longe dessa linha estão em zona de dor (estável e concreto, difícil de mudar) ou zona de inutilidade (abstrato e instável, sem uso).

---

## 3. Clean Architecture, a regra de dependência {#clean-arch}

A Clean Architecture é a síntese de várias arquiteturas em camadas (Hexagonal de Cockburn, Onion de Palermo, BCE de Jacobson, DCI), extraindo o que têm em comum: **a regra de dependência**.

### 3.1 Os círculos concêntricos

```
+------------------------------------------------------------+
|  Frameworks & Drivers                                      |
|  (Web, DB, UI, Devices, External Interfaces)               |
|  +------------------------------------------------------+  |
|  |  Interface Adapters                                  |  |
|  |  (Controllers, Presenters, Gateways, Repositories)   |  |
|  |  +------------------------------------------------+  |  |
|  |  |  Use Cases / Application Business Rules        |  |  |
|  |  |  (Interactors, orquestração de fluxos)         |  |  |
|  |  |  +------------------------------------------+  |  |  |
|  |  |  |  Entities / Enterprise Business Rules    |  |  |  |
|  |  |  |  (objetos de domínio, invariantes)       |  |  |  |
|  |  |  +------------------------------------------+  |  |  |
|  |  +------------------------------------------------+  |  |
|  +------------------------------------------------------+  |
+------------------------------------------------------------+

Setas de dependência apontam sempre para dentro.
```

### 3.2 Responsabilidades por camada

| Camada | Contém | Não pode conhecer |
|---|---|---|
| Entities | Regras de negócio que sobrevivem à aplicação; objetos com invariantes de domínio | Use cases, adapters, frameworks |
| Use Cases | Fluxos específicos da aplicação; orquestração de Entities | Adapters, UI, banco, framework |
| Interface Adapters | Controllers, Presenters, Gateways, Repositories; tradutores entre mundo externo e casos de uso | Detalhes de framework, driver de banco |
| Frameworks & Drivers | Web framework, ORM, broker, device, SDKs externos | Nada "acima"; só serve de detalhe plugável |

### 3.3 Regra de dependência

- Dependências do código-fonte apontam apenas para dentro.
- Nenhum nome declarado em anel externo pode ser citado em anel interno.
- Dados que cruzam fronteiras são estruturas simples, não objetos de framework nem entidades de ORM.

### 3.4 Como atravessar fronteiras sem violar a regra

Use **inversão de dependência**: a camada interna define a interface; a externa a implementa. Exemplo canônico, o padrão do Presenter:

```
[Use Case]  ---(interface OutputPort)---  [Presenter na camada Adapter]

Use Case chama OutputPort.present(dto).
Presenter implementa OutputPort e formata para a UI.
A seta de dependência aponta do Presenter para o OutputPort (para dentro).
```

### 3.5 Testabilidade como consequência

Se a regra de dependência é respeitada, casos de uso testam-se sem banco, sem HTTP, sem UI e sem frameworks. Testes lentos e frágeis indicam violação da regra.

---

## 4. Screaming Architecture {#screaming}

**Princípio:** ao olhar a estrutura de pastas e nomes do repositório, o sistema deve "gritar" seu propósito de negócio, não o framework que o implementa.

### Antipadrão, estrutura por tipo técnico

```
src/
├── controllers/
├── models/
├── services/
├── repositories/
└── dtos/
```

Esta estrutura conta que é uma aplicação MVC. Não conta o que o sistema faz.

### Padrão, estrutura por capacidade de negócio

```
src/
├── cadastro-regulatorio/
│   ├── casos-de-uso/
│   ├── entidades/
│   └── adaptadores/
├── compliance/
│   ├── casos-de-uso/
│   ├── entidades/
│   └── adaptadores/
└── notificacao/
    ├── casos-de-uso/
    ├── entidades/
    └── adaptadores/
```

Agora o repositório diz que este é um sistema de gestão regulatória, e não apenas um Spring, Rails ou FastAPI.

### Implicações

- Framework vira detalhe plugável, confinado aos adaptadores.
- Onboarding de novos desenvolvedores melhora, pois o mapa mental do negócio é imediato.
- Identificação de Bounded Contexts fica direta (ver `ddd.md`).

---

## 5. Clean Code, disciplinas de codificação {#clean-code}

### 5.1 Nomes significativos

- Revele intenção: `dias_desde_modificacao`, não `d`.
- Evite desinformação: não chame de `Lista` algo que não é lista.
- Faça distinções significativas, evitando `a1`, `a2`, `ProductInfo` vs `ProductData`.
- Nomes pronunciáveis e pesquisáveis; constantes com nome, não números mágicos.
- Nomes de classes são substantivos; nomes de métodos são verbos.

### 5.2 Funções

- Pequenas, fazendo uma única coisa, com um único nível de abstração.
- Regra do escoteiro: deixe o campo mais limpo do que encontrou.
- Poucos argumentos, preferencialmente zero, um ou dois; evite flags booleanas (indicam duas funções disfarçadas).
- Separe comandos de consultas (Command-Query Separation).
- Exceções em vez de códigos de erro; blocos `try/catch` isolados em funções próprias.
- Não repita (DRY), porém sem forçar abstração prematura.

### 5.3 Comentários

- Bons comentários são último recurso; o código deve explicar-se.
- Comentários úteis: intenção de negócio difícil de codificar, avisos de consequência, TODO com rastreabilidade, documentação pública de APIs.
- Comentários ruins: redundantes, obrigatórios, de diário, ruidosos, comentários que explicam código ruim (o certo é reescrever o código).

### 5.4 Formatação

- Consistência com o time é mais importante do que preferência individual.
- Dependentes verticais próximos; conceitos relacionados agrupados.
- Linhas curtas (limite razoável em torno de 100 a 120 colunas).
- Indentação consistente, sem quebras artificiais.

### 5.5 Objetos e estruturas de dados

Objetos escondem dados e expõem comportamento; estruturas de dados expõem dados e não têm comportamento. Cada um resolve um tipo de mudança com facilidade:

| Mudança | Objetos | Estruturas de dados |
|---|---|---|
| Novos tipos | Fácil (polimorfismo) | Difícil (altera todas funções) |
| Novas funções | Difícil (altera todos tipos) | Fácil (nova função isolada) |

Escolha conforme o eixo de mudança dominante. Lei de Demeter aplica-se a objetos, não a estruturas de dados.

### 5.6 Tratamento de erros

- Use exceções, não códigos de retorno.
- Forneça contexto nas exceções (o que, onde, por quê).
- Defina classes de exceção por necessidade do chamador, não por fonte.
- Use Null Object em vez de retornar `null`; jamais passe `null` como argumento.

### 5.7 Fronteiras

- Código de terceiros vive atrás de adaptadores próprios.
- Aprenda bibliotecas com testes de aprendizado (learning tests).
- Defina a interface que você deseja, adaptando a biblioteca a ela.

### 5.8 Classes

- Pequenas, medidas por responsabilidades, não por linhas.
- Alta coesão: métodos usam muitos dos campos da classe.
- Organização em ordem de leitura: campos públicos, campos privados, funções públicas, funções privadas.

### 5.9 Code Smells de Uncle Bob (complementares aos de Fowler)

| Smell | Descrição |
|---|---|
| Rigidez | Sistema difícil de mudar; mudanças simples disparam cascatas. |
| Fragilidade | Mudanças quebram pontos não relacionados. |
| Imobilidade | Partes não podem ser reutilizadas em outro projeto. |
| Viscosidade | É mais fácil fazer errado do que certo no ambiente atual. |
| Complexidade desnecessária | Infraestrutura para necessidades imaginárias. |
| Repetição desnecessária | Mesmo código em lugares múltiplos. |
| Opacidade | Código difícil de entender. |

---

## 6. TDD, disciplina de teste primeiro {#tdd}

### 6.1 As três leis

1. Não escreva código de produção sem antes haver um teste falhando.
2. Não escreva mais de um teste do que o necessário para falhar, incluindo falha de compilação.
3. Não escreva mais código de produção do que o necessário para passar o teste falhando.

### 6.2 Ciclo Red-Green-Refactor

- **Red:** escreva o teste menor possível que falha.
- **Green:** escreva o código mínimo para passar, mesmo que feio.
- **Refactor:** melhore a estrutura sem mudar o comportamento, mantendo todos os testes verdes.

Ciclos de segundos a minutos. Evite ciclos de horas.

### 6.3 Testes limpos, regra F.I.R.S.T.

- **Fast:** rápidos, rodando aos milhares em segundos.
- **Independent:** independentes entre si, sem ordem de execução.
- **Repeatable:** repetíveis em qualquer ambiente.
- **Self-validating:** passam ou falham; sem inspeção manual.
- **Timely:** escritos no momento certo, imediatamente antes do código de produção.

### 6.4 Pirâmide e diamante de testes

- Muitos testes unitários, alguns de integração, poucos de ponta a ponta.
- Testes unitários atravessam apenas a camada de Use Cases ou Entities, sem banco ou HTTP.
- Testes de integração validam adaptadores e bordas.
- Testes ponta a ponta validam fluxos críticos, operados com parcimônia pelo custo.

### 6.5 Humble Object

Separe lógica testável da difícil de testar. O objeto humilde (ex.: view) contém o mínimo, delegando a lógica para um objeto testável (ex.: presenter).

### 6.6 Benefícios verificáveis

- Regressão controlada, pois mudança que quebra é detectada em segundos.
- Design emergente, pois testes forçam baixo acoplamento e alta coesão.
- Documentação executável, pois o teste descreve comportamento esperado.
- Coragem para refatorar, ativo decisivo contra dívida técnica.

### 6.7 TDD em legado

- Caracterize o comportamento atual com testes antes de mudar (ver Feathers, Working Effectively with Legacy Code).
- Use "sprout" (novos métodos ou classes testadas) e "wrap" (embrulhar o legado com camada testada).
- Introduza seams (costuras) para quebrar dependências duras.

---

## 7. Clean Coder, profissionalismo {#clean-coder}

### 7.1 Responsabilidade profissional

- Digitar código que funciona é o mínimo; a responsabilidade estende-se à qualidade contínua.
- Você é responsável pelos bugs que entrega; meta razoável é tender a zero, não conviver.

### 7.2 Dizer "não"

- Profissionais negociam prazos, escopo e abordagens; não aceitam o impossível para evitar conflito.
- Dizer "vou tentar" sem plano é compromisso vago, evitado pelo profissional.

### 7.3 Dizer "sim"

- Compromisso real tem três partes: "eu vou", "até quando", e "se não cumprir, aviso imediatamente".

### 7.4 Estimativas

- Use faixas: otimista (O), nominal (N), pessimista (P).
- PERT simplificado: média esperada **E = (O + 4N + P) / 6**; desvio **SD = (P - O) / 6**.
- Estimativa não é compromisso; compromisso é compromisso.

### 7.5 Pressão

- Sob pressão, apegue-se às disciplinas, não as abandone.
- TDD, refactoring e clean code protegem o entregável quando o ambiente empurra o contrário.

### 7.6 Prática deliberada

- Katas, pair programming, contribuição a projetos, leitura contínua.
- Responsabilidade pela própria carreira, não delegada ao empregador.

### 7.7 Colaboração

- Pair programming como prática regular, não exceção.
- Mentoria em duas vias: seniores ensinam, juniores renovam.

---

## 8. Clean Agile, retorno às raízes técnicas {#clean-agile}

### 8.1 Tese central

Ágil sem disciplina técnica degrada em "Scrum cerimonial": cerimônias preservadas, qualidade corroída. O agile original (Snowbird, 2001) nasceu com XP como espinha dorsal técnica.

### 8.2 Círculo de práticas do XP

- **Práticas de negócio:** planning game, small releases, metáfora, acceptance tests.
- **Práticas de time:** metáfora, sustainable pace, collective ownership, continuous integration.
- **Práticas técnicas:** TDD, refactoring, simple design, pair programming.

A omissão das práticas técnicas quebra o sistema inteiro.

### 8.3 Simple design, quatro regras de Kent Beck

1. Passa em todos os testes.
2. Revela a intenção.
3. Sem duplicação.
4. Mínimo de elementos.

Aplicadas nessa ordem de prioridade.

### 8.4 Métricas honestas

- Velocity é ferramenta de previsibilidade, não de avaliação individual.
- Escolher entre escopo, prazo, qualidade e pessoas: qualidade é sempre o pior a sacrificar, pois volta como dívida com juros compostos.

---

## 9. Integração com Fowler, DDD, Falácias e C4 {#integracao}

### 9.1 Uncle Bob + Fowler

| Tema | Uncle Bob | Fowler |
|---|---|---|
| Evolução de código | Clean Code, SOLID | Refactoring (catálogo de transformações) |
| Design de aplicação | Clean Architecture, Entities, Use Cases | PoEAA (Domain Model, Service Layer, Repository) |
| Quebra de monolito | CCP, CRP, DIP | Strangler Fig, Branch by Abstraction |
| Microsserviços | CCP, REP, ADP nos cortes | Padrões de microservices |

### 9.2 Uncle Bob + DDD

- Entities de Uncle Bob correspondem ao domínio tático de Evans (Entity, Value Object, Aggregate).
- Bounded Contexts do DDD mapeiam naturalmente para componentes CCP.
- Screaming Architecture manifesta o Ubiquitous Language no nível da estrutura do repositório.
- ACL de DDD é aplicação direta de DIP e do conceito de fronteira de Uncle Bob.

### 9.3 Uncle Bob + Falácias

| Falácia | Princípio Uncle Bob que ajuda |
|---|---|
| 1, rede confiável | Humble Object na borda; casos de uso testados sem rede |
| 2, latência zero | DIP isolando chamadas remotas atrás de interface, permitindo batching e cache |
| 4, rede segura | Fronteiras claras (adapters) centralizam segurança |
| 5, topologia fixa | Detalhes de endereço vivem em Frameworks & Drivers, não no domínio |
| 6, um administrador | ISP e contratos estáveis reduzem impacto de mudança entre times |
| 8, rede homogênea | Adapters traduzem protocolos; domínio permanece imune |

### 9.4 Uncle Bob + C4

- **C4 nível 1 (Context):** capacidades de negócio visíveis, condizente com Screaming Architecture.
- **C4 nível 2 (Container):** componentes macro; fronteiras de Clean Architecture aparecem como containers distintos quando justificado.
- **C4 nível 3 (Component):** coesão CCP/CRP justifica o agrupamento.
- **C4 nível 4 (Code):** SOLID rege as classes no interior dos componentes.

---

## 10. Checklist rápido de diagnóstico

Ao revisar um sistema, pergunte:

1. Posso rodar os testes do domínio sem banco, rede, UI e framework?
2. As regras de negócio dependem apenas de abstrações definidas nelas mesmas?
3. A estrutura de pastas "grita" o domínio, ou o framework?
4. Os componentes formam grafo acíclico?
5. As classes têm uma razão para mudar, ligada a um ator?
6. Existem condicionais sobre tipo que polimorfismo resolveria?
7. Interfaces obrigam clientes a conhecer métodos inúteis?
8. Subclasses honram o contrato do tipo base sem surpresas?
9. Testes são rápidos, independentes e determinísticos?
10. Qualidade técnica está sendo negociada sob pressão?

Cada "não" é oportunidade de refatoração priorizada.

---

## Fontes e leituras recomendadas

- Martin, Robert C. **Clean Code: A Handbook of Agile Software Craftsmanship**. Prentice Hall, 2008.
- Martin, Robert C. **The Clean Coder: A Code of Conduct for Professional Programmers**. Prentice Hall, 2011.
- Martin, Robert C. **Clean Architecture: A Craftsman's Guide to Software Structure and Design**. Prentice Hall, 2017.
- Martin, Robert C. **Clean Agile: Back to Basics**. Prentice Hall, 2019.
- Blog oficial: [blog.cleancoder.com](https://blog.cleancoder.com).
- Artigo seminal: [The Clean Architecture (2012)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html).
- Artigo seminal: [Screaming Architecture (2011)](https://blog.cleancoder.com/uncle-bob/2011/09/30/Screaming-Architecture.html).
- Leitura complementar sobre legado: Feathers, Michael. **Working Effectively with Legacy Code**. Prentice Hall, 2004.
