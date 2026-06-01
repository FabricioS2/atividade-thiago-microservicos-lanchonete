# atividade-thiago-microservicos-lanchonete

## 1. Visão geral do projeto

O sistema implementa uma arquitetura de **microserviços** para uma lanchonete, utilizando **FastAPI**, **SQLite** isolado por serviço, **RabbitMQ** para mensageria e **Docker Compose** com health checks independentes. Cada serviço é responsável por um domínio específico: cardápio, pedidos, pagamento e notificação de cozinha.

---

## 2. Tecnologias utilizadas

**Base comum a todos os serviços**  
Python 3.12, FastAPI, Uvicorn, SQLAlchemy (ORM), Pydantic (validação), SQLite (banco de dados local)

**Especificidades por serviço**

| Serviço | Tecnologias adicionais | Finalidade |
|---------|------------------------|------------|
| **cardapio_service** | — | CRUD de itens do cardápio, controle de estoque e disponibilidade |
| **pedidos_service** | `httpx` (HTTP assíncrono), `aio-pika` (publicação no RabbitMQ), `tenacity` (retry) | Orquestra pedidos, comunica-se via HTTP com cardápio e pagamento, publica mensagens de notificação |
| **pagamento_service** | — | Processamento simulado de pagamento (mock com 80% de aprovação) e consulta de status |
| **notificacao_service** | `aio-pika` (consumidor RabbitMQ) | Consome a fila de notificações da cozinha, persiste e expõe API de consulta |

**Infraestrutura**  
Docker, Docker Compose (cada serviço em um container) e RabbitMQ 3-management como message broker.

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
├── teste_lanchonete.py       # Script de testes integrados de ponta a ponta
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
- **Tecnologias modernas** – FastAPI oferece alto desempenho, documentação automática (OpenAPI), suporte assíncrono nativo. Pydantic e SQLAlchemy garantem tipagem segura.
- **Containerização** – Docker Compose permite subir toda a stack com um único comando, com ambientes reprodutíveis.

---

## 8. Desvantagens e maneiras de contornar

1. **Ausência de API Gateway / Service Discovery**  
   *Problema*: URLs fixas internas, exposição direta de portas.  
   *Solução*: Adicionar um proxy reverso (Traefik, NGINX) ou API Gateway, e service discovery (Kubernetes Services/Consul).

2. **SQLite em produção**  
   *Problema*: Baixa concorrência, sem replicação.  
   *Solução*: Migrar para PostgreSQL/MySQL, já configurável via `DATABASE_URL`.

3. **Consistência em transações distribuídas**  
   *Problema*: Se RabbitMQ falhar após pagamento aprovado, a notificação não é criada.  
   *Solução*: Padrão **Saga** ou **Outbox** (salvar evento no banco do pedido e publicar em background).

4. **Dependência de inicialização no Compose**  
   *Problema*: `depends_on` não garante que o serviço esteja pronto.  
   *Solução*: Usar `wait-for-it` nos entrypoints, ou lógica de retry já existente.

5. **Escalabilidade vertical limitada**  
   *Problema*: SQLite não escala horizontalmente.  
   *Solução*: Migrar para banco clusterizado e adicionar cache (Redis) para dados de cardápio.

6. **Versionamento de API ausente**  
   *Problema*: Alterações podem quebrar clientes.  
   *Solução*: Prefixar endpoints com `/v1/` ou usar headers de versionamento.