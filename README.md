# atividade-thiago-microservicos-lanchonete

Segue uma versão consolidada, removendo sobreposições e organizando todo o conteúdo em uma única resposta coesa.

---

## 1. Visão geral do projeto

O sistema implementa uma arquitetura de **microserviços** para uma lanchonete, utilizando **FastAPI**, **SQLite** isolado por serviço, **RabbitMQ** para mensageria e **Docker Compose** com health checks independentes. Cada serviço é responsável por um domínio específico: cardápio, pedidos, pagamento e notificação de cozinha.

---

## 2. Tecnologias utilizadas

**Base comum a todos os serviços**
- Python 3.12, FastAPI, Uvicorn, SQLAlchemy (ORM), Pydantic (validação), SQLite (banco de dados local)

**Especificidades por serviço**

| Serviço | Tecnologias adicionais | Finalidade |
|---------|------------------------|------------|
| **cardapio_service** | — | CRUD de itens do cardápio, controle de estoque e disponibilidade |
| **pedidos_service** | `httpx` (HTTP assíncrono), `aio-pika` (publicação no RabbitMQ), `tenacity` (retry) | Orquestra pedidos, comunica-se via HTTP com cardápio e pagamento, publica mensagens de notificação |
| **pagamento_service** | — | Processamento simulado de pagamento (mock com 80% de aprovação) e consulta de status |
| **notificacao_service** | `aio-pika` (consumidor RabbitMQ) | Consome a fila de notificações da cozinha, persiste e expõe API de consulta |

**Infraestrutura**
- Docker e Docker Compose (cada serviço em um container)
- RabbitMQ 3-management como message broker

---

## 3. Estrutura de diretórios e arquivos principais

```
atividade-thiago-microservicos-lanchonete/
├── cardapio_service/
│   ├── app/
│   │   ├── main.py          # Inicializa FastAPI, tabelas e health check
│   │   ├── database.py      # Configuração do SQLite e sessão
│   │   ├── models.py        # Modelo SQLAlchemy (Item)
│   │   ├── schemas.py       # Schemas Pydantic (ItemCreate, ItemResponse, DisponibilidadeResponse)
│   │   └── routes.py        # Endpoints REST do cardápio
│   ├── Dockerfile
│   └── requirements.txt
├── notificacao_service/
│   ├── app/
│   │   ├── main.py          # Inicializa app, tabelas e lança consumidor RabbitMQ
│   │   ├── consumer.py      # Conexão e consumo assíncrono da fila cozinha_notificacao
│   │   ├── database.py      # Configuração do SQLite
│   │   ├── models.py        # Modelo NotificacaoCozinha
│   │   ├── schemas.py       # Schema NotificacaoResponse
│   │   └── routes.py        # Endpoints para listar/marcar notificações
│   ├── Dockerfile
│   └── requirements.txt
├── pagamento_service/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py        # Transacao e FormaPagamento
│   │   ├── schemas.py       # PagamentoRequest, PagamentoResponse
│   │   └── routes.py        # Processa pagamento, consulta, cadastro de formas
│   ├── Dockerfile
│   └── requirements.txt
├── pedidos_service/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── external_services.py  # Chamadas HTTP a cardápio e pagamento, com retry (tenacity)
│   │   ├── models.py             # Pedido e ItemPedido
│   │   ├── schemas.py
│   │   └── routes.py             # Criação, listagem, pagamento, cancelamento de pedidos
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml        # Orquestração dos containers, volumes, redes, healthchecks
├── teste_lanchonete.py        # Script de testes integrados de ponta a ponta
└── README.md
```

---

## 4. Capacidades implementadas (endpoints)

### 4.1 Cardápio (`cardapio_service`) – porta 8001
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Health check |
| GET | `/itens/` | Lista todos os itens |
| GET | `/itens/{item_id}` | Detalhes de um item |
| POST | `/itens/` | Cria um novo item |
| PUT | `/itens/{item_id}` | Atualiza um item |
| DELETE | `/itens/{item_id}` | Remove um item |
| GET | `/itens/{item_id}/disponibilidade` | Retorna `{disponivel, preco}` – usado pelo pedidos_service |

### 4.2 Pagamento (`pagamento_service`) – porta 8003
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Health check |
| POST | `/pagamentos/` | Processa pagamento (body: `pedido_id`, `valor`, `forma_pagamento_id`). Simula aprovação com 80% de chance. |
| GET | `/pagamentos/{transacao_id}` | Consulta transação |
| POST | `/pagamentos/formas-pagamento/?nome=...` | Cadastra forma de pagamento |

### 4.3 Pedidos (`pedidos_service`) – porta 8002  
**Header obrigatório: `X-User-Id`**

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Health check |
| POST | `/pedidos/` | Cria pedido (verifica disponibilidade via cardápio, calcula total) |
| GET | `/pedidos/` | Lista pedidos do cliente |
| GET | `/pedidos/{pedido_id}` | Detalhe de um pedido |
| POST | `/pedidos/{pedido_id}/pagar` | Submete pagamento ao pagamento_service; se aprovado, muda status para `PREPARANDO` e publica no RabbitMQ |
| PATCH | `/pedidos/{pedido_id}/cancelar` | Cancela pedido se status = `CRIADO` ou `AGUARDANDO_PAGAMENTO` |

### 4.4 Notificação (`notificacao_service`) – porta 8004
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/health` | Health check |
| GET | `/notificacoes/` | Lista notificações da cozinha (ordem decrescente) |
| POST | `/notificacoes/{id}/marcar-lida` | Marca notificação como lida |

O serviço roda um **consumer assíncrono** que escuta a fila `cozinha_notificacao` (RabbitMQ, routing key `cozinha.notificar`) e persiste as notificações.

---

## 5. Regra de negócio crítica

**“Um pedido só vai para a cozinha após confirmação de pagamento.”**

Fluxo implementado:
1. Cliente cria pedido (`POST /pedidos/`).
2. Cliente paga (`POST /pedidos/{id}/pagar`).
3. O `pedidos_service` calcula o total e chama **sincronamente** (HTTP) o `pagamento_service`.
4. Se a resposta for `APPROVED`:
   - Status do pedido → `PREPARANDO`
   - Publica mensagem **persistente** no RabbitMQ (routing key `cozinha.notificar`)
   - O `notificacao_service` consome a mensagem e grava a notificação
5. Se o pagamento for recusado, o pedido **não** avança para a cozinha.

A comunicação pedidos → pagamento é síncrona; a notificação à cozinha é assíncrona via fila durável.

---

## 6. Checklist de requisitos

- **[x] 4 serviços em portas distintas, cada um com banco/schema isolado**  
  Portas: 8001 (cardápio), 8002 (pedidos), 8003 (pagamento), 8004 (notificação).  
  Volumes Docker independentes: `cardapio_data`, `pedidos_data`, `pagamento_data`, `notificacao_data`.
- **[x] Docker Compose orquestrando todos**  
  `docker-compose.yml` com serviços, rede, volumes, dependências e healthchecks.
- **[x] Fluxo pedido → pagamento via HTTP síncrono**  
  `pedidos_service` chama `pagamento_service` com `httpx` e aguarda resposta.
- **[x] Notificação da cozinha via fila assíncrona**  
  RabbitMQ com exchange `pedidos` (topic), fila `cozinha_notificacao` durável, mensagens persistentes.
- **[x] Health check próprio em cada serviço**  
  Todos implementam `GET /health` e o compose usa `curl` para monitoramento.
- **[x] Experimento: derrubar o serviço de notificação e fazer um pedido**  
  O sistema continua funcionando. O pagamento é processado normalmente; a mensagem permanece na fila do RabbitMQ até que o `notificacao_service` volte. O pedido avança para `PREPARANDO` sem erro.
- **[x] Estratégia de resiliência implementada**  
  Retry com `tenacity` nas chamadas do `pedidos_service` ao cardápio (`obter_disponibilidade`): 3 tentativas com 1 segundo de espera.  
  O consumidor do RabbitMQ também faz reconexão automática com tentativas.
- **[x] Rollback do serviço de pagamento sem afetar outros**  
  Detalhado na seção 9.

---

## 7. Vantagens da arquitetura

- **Isolamento de responsabilidades** – cada serviço cuida do seu domínio, facilitando evolução independente.
- **Comunicação assíncrona** – a cozinha é notificada via fila, desacoplando o fluxo do pedido e aumentando a tolerância a falhas.
- **Tecnolog- **Tecnologias modernas** – Fastias modernas** – FastAPI ofereAPI oferece altoce alto desempenho, desempenho, documentação automática (OpenAPI), documentação automática (OpenAPI), suporte ass suporte assíncrono nativo.íncrono nativo. Pydantic e SQL Pydantic e SQLAlchemy garantem tipagem segura.
Alchemy garantem tipagem segura.
- **Container- **Containerização** – Dockerização** – Docker Compose permite Compose permite subir toda subir toda a stack com um único com a stack com um único comando, comando, com amb ambientes reproientes reprodutíveisdutíveis.
- **Resili.
- **Resiliência na comunicação sência na comunicação síncíncrona** – retrona** – retry nasry nas chamadas a chamadas a cardápio cardápio e pagamento mit e pagamento mitiga falhas temporiga falhas temporárias.
- **Flexárias.
- **Flexibilidade de banibilidade de banco** – varico** – variável `DATABASE_URL`ável `DATABASE_URL` permite trocar SQL permite trocar SQLite por PostgreSQL semite por PostgreSQL sem alterar alterar código.
- ** código.
- **Health checksHealth checks**** integ integrados –rados – pr prontos para orontos para orquestradquestradores eores e monitoramento.

---

##  monitoramento.

---

## 8. Desvantagens8. Desvantagens e maneiras de cont e maneiras de contornar

1. **ornar

1. **Ausência de APIAusência de API Gateway / Gateway / Service Discovery**  
   * Service Discovery**  
   *Problema*Problema*: URLs fixas: URLs fixas internas internas, exp, exposição direosição direta de portas.  
ta de portas.  
   *S   *Solução*: Adicionarolução*: Adicionar um proxy reverso (Tra um proxy reverso (Traefik, NGINXefik, NGINX) ou API) ou API Gateway, e Gateway, e service discovery ( service discovery (Kubernetes ServicesKubernetes Services/Consul).

2. **/Consul).

2. **SQLite em produção**SQLite em produção**  
   *Problema  
   *Problema*: Baixa conc*: Baixa concorrência,orrência, sem replic sem replicação.  
   *ação.  
   *Solução*: MigSolução*: Migrar para PostgreSQL/rar para PostgreSQL/MySQL, jáMySQL, já configur configurável via `DATABASE_URLável via `DATABASE_URL`.

3. **Simulação`.

3. **Simulação de de pagamento aleat pagamento aleatória**  
   *Proória**  
   *Problema*: Nãoblema*: Não real realista, falista, falhas interhas intermitentes emmitentes em testes.  
   *S testes.  
   *Solução*: Integrar comolução*: Integrar com gateway de pagamento real ou gateway de pagamento real ou mock mock determin determinístico (ex.:ístico (ex.: baseado no baseado no ID ID da forma de pagamento da forma de pagamento).

4. **Ident).

4. **Identificação frágil (`X-User-Idificação frágil (`X-User-Id`)**  
   *Pro`)**  
   *Problema*blema*: Sem aut: Sem autenticação, vulnerenticação, vulnerável a spoofing.ável a spoofing.  
   *Solução*  
   *Solução*: Implementar aut: Implementar autenticação Jenticação JWT/OWT/OAuth,Auth, valid validar tokensar tokens em um em um middleware.

 middleware.

5. **5. **Observabilidade insObservabilidade insuficiente**  
  uficiente**  
   *Problema*: *Problema*: Logs com Logs com `print`, sem `print`, sem tracing tracing ou métricas.  
   ou métricas.  
   *Solução*: Us *Solução*: Usar logging estruturado,ar logging estruturado, OpenTelemetry + Ja OpenTelemetry + Jaeger, Prometheus +eger, Prometheus + Grafana.

6. ** Grafana.

6. **ConsConsistência emistência em trans transações distribuídas**  
ações distribuídas**  
   *   *Problema*Problema*: Se RabbitMQ fal: Se RabbitMQ falhar após paghar após pagamento aprovado, a notificação não é criamento aprovado, a notificação não é criada.  
   *Sada.  
   *Solução*: Padolução*: Padrão **Srão **Saga** ouaga** ou **Outbox** (sal **Outbox** (salvar evento no banvar evento no banco do pedido eco do pedido e publicar em publicar em background).

7. background).

7. **Dependência de inicial **Dependência de inicialização no Compização no Compose**  
   *Proose**  
   *Problema*: `depends_on` não garblema*: `depends_on` não garante que serviante que serviço esteja pronto.  
ço esteja pronto.  
   *Solução*:   *Solução*: Usar `wait-for-it Usar `wait-for-it` nos entrypoints, ou` nos entrypoints, ou lógica lógica de retry já exist de retry já existente.

8.ente.

8. **Escalabilidade **Escalabilidade vertical limitada**  
   vertical limitada**  
   *Problema *Problema*: SQLite não*: SQLite não escala escala horizontal horizontalmente.  
   *Smente.  
   *Solução*: Migrar paraolução*: Migrar para banco cluster banco clusterizado e adizado e adicionar cache (icionar cache (Redis) para dados deRedis) para dados de cardápio.

 cardápio.

9. **Version9. **Versionamento deamento de API ausente**  
   API ausente**  
   *Proble *Problema*:ma*: Alter Alterações podemações podem quebrar client quebrar clientes.  
   *Ses.  
   *Solução*: Prefixolução*: Prefixar endpointsar endpoints com `/v1/` ou usar headers com `/v1/` ou usar headers de versionamento de versionamento.

10. **Testes.

10. **Testes man manuais e fruais e frágeis**  
   ágeis**  
    *Problema*: *Problema*: Script monolítico Script monolítico,, sem integ sem integração contração contínua.  
    *ínua.  
    *Solução*: AdSolução*: Adotar `pytest`otar `pytest` com `testcontain com `testcontainers`, testesers`, testes de contrato ( de contrato (Pact) e pipelinesPact) e pipelines CI/CD.

---

##  CI/CD.

---

## 9. Rollback do servi9. Rollback do serviço de pagamento semço de pagamento sem impacto impacto nos dem nos demais

Como cadaais

Como cada mic microsserviço érosserviço é independent independente e ae e a comunicação é feita via comunicação é feita via HTTP HTTP, o roll, o rollback éback é seguro:

1 seguro:

1.. Pare Pare apenas o apenas o container de container de pagamento:  
 pagamento:  
   `   `docker-compose stop pagdocker-compose stop pagamento`
2. Substamento`
2. Substitua a imagem pelaitua a imagem pela versão anterior (reb versão anterior (rebuild ou `uild ou `docker tag`).
3.docker tag`).
3. Se o esqu Se o esquema doema do banco SQL banco SQLite foiite foi alter alterado, restaure o arquado, restaure o arquivo de backupivo de backup do volume do volume `pagamento_data `pagamento_data`.
4. Inicie`.
4. Inicie novamente:  
   ` novamente:  
   `docker-compose up -ddocker-compose up -d --no-deps --no-deps pagamento`

O ` pagamento`

O `pedidos_service` continuarápedidos_service` continuará chamando os chamando os mesmos endpoints REST mesmos endpoints REST; se h; se houver erro temporouver erro temporário, o retário, o retry comry com `tenacity` absor `tenacity` absorveve a falha até a falha até o serviço volt o serviço voltar.ar. N Nenhenhum outro serviço é reiniciado, garantumindo **de outro serviço é reiniciado, garantindo **deploy independentploy independente** e **e** e **zerozero downtime downtime** nos** nos demais.
