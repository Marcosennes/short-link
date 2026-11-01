# Shortlink

> **EN:** A small URL shortener with click analytics, built as a microservices study project:
> FastAPI services, Kafka messaging, PostgreSQL + MongoDB + Redis, the Transactional Outbox
> pattern, Docker Compose, and unit tests gated on every Pull Request.

Encurtador de URL com analytics de cliques, feito para estudar arquitetura de microsserviços.

| Serviço           | Responsabilidade                                   | Armazenamento |
|-------------------|----------------------------------------------------|---------------|
| link-service      | CRUD de links; publica eventos via **outbox**      | PostgreSQL    |
| redirect-service  | `GET /r/{slug}` → 302; publica cliques             | Redis         |
| analytics-service | Consome cliques e expõe estatísticas               | MongoDB       |

Detalhes e diagramas em [docs/architecture.md](docs/architecture.md).

## Status

- [x] Fase 1: esqueleto, contratos de eventos, infraestrutura no Compose e CI
- [ ] Fase 2: link-service + Postgres + outbox
- [ ] Fase 3: redirect-service + Redis + Kafka
- [ ] Fase 4: analytics-service + MongoDB
- [ ] Fase 5: demo ponta a ponta e ADRs
- [ ] Fase 6 (opcional): redirect-service em Go

## Como rodar

Pré-requisitos: Docker com Compose v2 e [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
docker compose up -d                      # infraestrutura
docker compose --profile tools up -d      # + kafka-ui e mongo-express
```

| Ferramenta        | URL                    |
|-------------------|------------------------|
| Gateway (Traefik) | http://localhost:8000  |
| Traefik dashboard | http://localhost:8081  |
| Kafka UI          | http://localhost:8084  |
| Mongo Express     | http://localhost:8083  |

## Desenvolvimento

```bash
uv sync --all-packages                    # um único venv para todo o workspace
uv run ruff check . && uv run ruff format --check .
uv run pytest libs services               # testes unitários (não precisam de Docker)

```

Cada serviço segue uma arquitetura hexagonal leve (`domain/`, `ports/`, `adapters/`, `api/`).
Os testes unitários usam fakes em memória dos ports, então rodam rápido e sem infraestrutura.

## CI e Pull Requests

O workflow [`.github/workflows/ci.yaml`](.github/workflows/ci.yaml) roda em cada PR para `main`:
lint (ruff), formatação, testes unitários com cobertura mínima de 80% por pacote e build das
imagens Docker.

Para exigir o CI verde antes do merge: **Settings → Branches → Add branch ruleset** para `main`,
habilite *Require a pull request before merging* e *Require status checks to pass*, e
selecione o check **`ci-ok`**.
