# Arquitetura

```mermaid
flowchart LR
    client([cliente]) --> gw[Traefik gateway]
    gw -->|/api/links| link[link-service]
    gw -->|/r/:slug| redirect[redirect-service]
    gw -->|/api/stats| analytics[analytics-service]

    link --- pg[(PostgreSQL)]
    link -. outbox-relay .-> k1{{link.events}}
    k1 --> redirect
    redirect --- redis[(Redis)]
    redirect -.miss.-> link
    redirect --> k2{{link.clicks}}
    k2 --> analytics
    analytics --- mongo[(MongoDB)]
```

## Transactional Outbox (link-service)

Problema: gravar o link no Postgres **e** publicar o evento no Kafka são duas operações em
sistemas diferentes. Se o processo cair entre elas, o banco e o barramento divergem.

Solução:

1. Na mesma transação, o link-service grava o link **e** uma linha na tabela `outbox`.
2. O `outbox-relay` lê as linhas pendentes (`SELECT ... FOR UPDATE SKIP LOCKED`), publica no
   Kafka e marca como publicadas.
3. Se o relay cair depois de publicar e antes de marcar, o evento é republicado. Por isso a
   entrega é *at-least-once* e os consumidores precisam ser idempotentes (`event_id`).

```mermaid
sequenceDiagram
    participant API as link-service
    participant DB as PostgreSQL
    participant R as outbox-relay
    participant K as Kafka
    API->>DB: BEGIN; INSERT link; INSERT outbox; COMMIT
    loop polling
        R->>DB: SELECT pending FOR UPDATE SKIP LOCKED
        R->>K: publish link.created
        R->>DB: UPDATE outbox SET published_at = now()
    end
```

## Por que não há outbox no redirect-service?

Ele não tem banco transacional e perder um clique ocasional é aceitável para analytics.
Então ele publica `link.clicked` direto no Kafka, sem bloquear a resposta 302.

## Contratos

Os eventos ficam em [`libs/contracts`](../libs/contracts). Todos usam o mesmo envelope:
`event_id`, `event_type`, `occurred_at`, `version` e `payload`.

| Tópico        | Evento         | Produtor          | Consumidor        |
|---------------|----------------|-------------------|-------------------|
| `link.events` | `link.created` | link-service      | redirect-service  |
| `link.events` | `link.deleted` | link-service      | redirect-service  |
| `link.clicks` | `link.clicked` | redirect-service  | analytics-service |
