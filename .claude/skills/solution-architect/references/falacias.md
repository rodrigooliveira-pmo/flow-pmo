# Referência: As 8 Falácias da Computação Distribuída

*Originalmente atribuídas a Peter Deutsch e James Gosling (Sun Microsystems). Amplamente referenciadas por Fowler e outros arquitetos.*

---

## O que são as falácias?

São suposições incorretas que desenvolvedores frequentemente fazem ao projetar sistemas distribuídos. Cada falácia representa um risco arquitetural real: quando ignorada, causa falhas em produção, degradação de performance, ou sistemas frágeis e difíceis de operar.

**Como usar este checklist:**
- **Greenfield:** percorra as falácias ao revisar um design novo. Para cada uma, pergunte: "O design assume que isso é verdade?"
- **Diagnóstico:** ao investigar um problema em produção, identifique qual falácia foi violada.
- **Trade-off:** use as falácias para embasar decisões — "Estamos assumindo que a rede é confiável; o custo de não assumir isso é X; vale a pena?"

---

## Falácia 1: A rede é confiável

**A suposição:** chamadas remotas funcionam como chamadas locais.

**A realidade:** redes falham. Pacotes são perdidos, conexões são derrubadas, timeouts acontecem. Uma chamada pode falhar *após* ter sido recebida pelo destinatário (falha parcial).

**Sintomas de violação:**
- Ausência de timeout configurado
- Sem retry com backoff exponencial
- Sem tratamento de falha parcial (ex: "paguei mas não recebi confirmação")
- Transações distribuídas sem compensação

**Como mitigar:**
- Sempre configure timeouts explícitos
- Implemente retry com backoff + jitter
- Projete operações como idempotentes quando possível
- Use Circuit Breaker para falhas recorrentes
- Considere o padrão Saga para consistência eventual

---

## Falácia 2: Latência é zero

**A suposição:** chamadas remotas são tão rápidas quanto chamadas locais.

**A realidade:** latência de rede existe e é variável. Uma chamada local leva nanosegundos; uma chamada remota leva milissegundos — e pode variar.

**Sintomas de violação:**
- Arquitetura "chatty" — muitas chamadas pequenas em sequência
- Chamadas síncronas em cadeia (A chama B, que chama C, que chama D)
- Sem caching de dados pouco mutáveis
- Latência total = soma das latências individuais

**Como mitigar:**
- Prefira chamadas "chunky" a chamadas "chatty" — transfira mais dados em menos chamadas
- Use cache para dados estáveis
- Avalie async/messaging para fluxos não críticos
- Meça latência de ponta a ponta, não apenas do serviço

---

## Falácia 3: A banda é infinita

**A suposição:** podemos transferir qualquer volume de dados sem custo.

**A realidade:** banda tem custo financeiro e de latência. Serialização/deserialização tem custo de CPU.

**Sintomas de violação:**
- Transferência de objetos completos quando apenas campos específicos são necessários
- Sem paginação em APIs que retornam coleções
- Payloads grandes sem compressão
- Logs verbosos enviados por rede sem filtragem

**Como mitigar:**
- Projete APIs para retornar apenas o necessário (YAGNI para campos)
- Use paginação e filtros
- Considere compressão (gzip) para payloads grandes
- Use formatos eficientes (Protobuf, Avro) em alta frequência

---

## Falácia 4: A rede é segura

**A suposição:** dados em trânsito estão protegidos por padrão.

**A realidade:** redes internas também podem ser comprometidas. "Defense in depth" — não confie na rede.

**Sintomas de violação:**
- Comunicação interna sem TLS ("é só rede interna")
- Ausência de autenticação entre serviços internos
- Segredos em texto plano em logs ou variáveis de ambiente
- Sem validação de entrada em APIs internas

**Como mitigar:**
- TLS mesmo em comunicação interna (Zero Trust)
- Autenticação entre serviços (mTLS, JWT, service accounts)
- Nunca logue dados sensíveis
- Valide e sanitize entradas em todos os pontos

---

## Falácia 5: A topologia não muda

**A suposição:** os endereços IP e a estrutura da rede são estáveis.

**A realidade:** IPs mudam, serviços são movidos, containers são recriados, instâncias sobem e caem.

**Sintomas de violação:**
- IPs hardcoded em configuração
- Sem service discovery
- Dependência de hostnames fixos sem DNS dinâmico
- Deploys que quebram porque "o serviço X mudou de IP"

**Como mitigar:**
- Use service discovery (Kubernetes DNS, Consul, etc.)
- Configure por nome de serviço, não por IP
- Implemente health checks e atualize endpoints dinamicamente
- Projete para que instâncias possam ser substituídas a qualquer momento

---

## Falácia 6: Existe apenas um administrador

**A suposição:** uma pessoa (ou equipe) controla todo o sistema.

**A realidade:** sistemas distribuídos pertencem a múltiplos times, com diferentes prioridades, ciclos de deploy, e responsabilidades.

**Sintomas de violação:**
- Contratos de API sem versionamento
- Mudanças breaking sem processo de deprecação
- Dependência implícita de comportamento não documentado
- "Só avise o time X antes de mudar"

**Como mitigar:**
- Versione suas APIs explicitamente
- Documente contratos (OpenAPI, AsyncAPI)
- Implemente Consumer-Driven Contract Testing
- Estabeleça SLOs e comunique mudanças com antecedência
- Trate cada serviço como um produto com contrato público

---

## Falácia 7: O custo de transporte é zero

**A suposição:** chamar serviços remotos não tem custo além do tempo de resposta.

**A realidade:** chamadas remotas têm custo financeiro (infra, cloud), custo de serialização, custo de autenticação, e overhead de protocolo.

**Sintomas de violação:**
- Milhares de chamadas pequenas que poderiam ser batched
- Reprocessamento desnecessário de dados já disponíveis
- Sem cache em pontos onde os dados raramente mudam
- Arquitetura que ignora custo de egress em nuvem

**Como mitigar:**
- Meça e monitore custo de chamadas entre serviços
- Use batch onde faz sentido
- Cache dados estáveis próximo ao consumidor
- Considere colocar serviços com alta comunicação na mesma região/zona

---

## Falácia 8: A rede é homogênea

**A suposição:** todos os componentes usam os mesmos protocolos, formatos e capacidades de rede.

**A realidade:** sistemas reais integram tecnologias diferentes — legado, terceiros, mobile, IoT, cloud, on-premise — com diferentes capacidades e limitações.

**Sintomas de violação:**
- API que assume JSON mas o sistema legado só fala XML/SOAP
- Protocolo que assume HTTP/2 mas o cliente só suporta HTTP/1.1
- Encoding hardcoded (UTF-8) sem negociação de conteúdo
- Suposição de que todos os clientes têm banda similar

**Como mitigar:**
- Use camadas de tradução (API Gateway, Message Translator)
- Negocie formato e versão de protocolo explicitamente
- Projete para o "menor denominador comum" em integrações externas
- Documente e teste compatibilidade com diferentes clientes

---

## Resumo — Checklist rápido

| # | Falácia | Pergunta de checklist |
|---|---|---|
| 1 | Rede confiável | O sistema trata falhas de chamadas remotas explicitamente? |
| 2 | Latência zero | Há chamadas em cadeia que somam latências? Existe caching? |
| 3 | Banda infinita | Os payloads são dimensionados? Há paginação? |
| 4 | Rede segura | Comunicação interna tem autenticação e criptografia? |
| 5 | Topologia fixa | IPs são hardcoded? Há service discovery? |
| 6 | Um administrador | APIs são versionadas? Contratos são documentados? |
| 7 | Transporte gratuito | O custo de chamadas remotas é considerado no design? |
| 8 | Rede homogênea | O sistema lida com clientes e protocolos heterogêneos? |
