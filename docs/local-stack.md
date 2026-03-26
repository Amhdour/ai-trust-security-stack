# Local Development Stack (Codespaces)

This stack is **development-focused** and intentionally minimal. It is not production hardened.

## Services
- control-plane dashboard homepage
- postgres (Langfuse backing database)
- keycloak
- envoy
- opa
- vault (dev mode)
- qdrant
- langfuse
- grafana
- superset

Compose file: `compose/docker-compose.yml`

## 1) Configure environment

```bash
cp compose/.env.example compose/.env
```

Update placeholder values in `compose/.env` before starting.

## 2) Start the stack

```bash
docker compose --env-file compose/.env -f compose/docker-compose.yml up -d
```

To stream logs:

```bash
docker compose --env-file compose/.env -f compose/docker-compose.yml logs -f
```

## 3) Stop the stack

```bash
docker compose --env-file compose/.env -f compose/docker-compose.yml down
```

To also remove named volumes:

```bash
docker compose --env-file compose/.env -f compose/docker-compose.yml down -v
```

## Service endpoints (default local ports)
- Control plane dashboard: `http://localhost:3000`
- Keycloak: `http://localhost:8080`
- Envoy: `http://localhost:10000`
- OPA: `http://localhost:8181`
- Vault: `http://localhost:8200`
- Qdrant: `http://localhost:6333`
- Langfuse: `http://localhost:3002`
- Grafana: `http://localhost:3001`
- Superset: `http://localhost:8088`

## Notes
- The dashboard is the main landing page and aggregates posture from repo-owned artifacts plus supporting services.
- Secrets are provided via environment variables and placeholders only.
- `vault` is configured in `-dev` mode for local development.
- Langfuse uses the local `db` PostgreSQL service by default.
- Superset loads its local config from `compose/superset/superset_config.py`.
