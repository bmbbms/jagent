# Agno-based technical stack

## Target stack

- Agent framework: Agno
- Service framework: FastAPI
- Data foundation: PostgreSQL, pgvector, Redis
- Integration: MCP and internal tools
- High-risk process: workflow plus approval
- Deployment: Docker and Kubernetes

## Runtime boundary

The platform keeps business capabilities as registered `CapabilityAgent`
implementations. `RouterAgent` is responsible for route planning and delegates
execution to an `AgentRuntime`.

Current runtimes:

- `agno`: target runtime. It is selected by default and falls back to local
  execution when Agno is not installed.
- `local`: deterministic local execution for tests and MVP fallback.

This keeps FastAPI routes, capability registration, Nacos discovery, approval,
audit, and persistence independent from the selected Agent runtime.

## Data foundation

The default local URL still uses SQLite for quick startup. Production should set:

```powershell
$env:ACQUIRING_AI_DATABASE_URL="postgresql+psycopg://acquiring_ai:password@postgres:5432/acquiring_ai"
$env:ACQUIRING_AI_REDIS_URL="redis://redis:6379/0"
$env:ACQUIRING_AI_VECTOR_STORE_ENABLED="true"
```

The Docker Compose stack starts PostgreSQL with pgvector and Redis.

## Next implementation order

1. Replace the Agno placeholder with real Agno Agent construction.
2. Convert internal tool catalog entries into Agno tools.
3. Add MCP server loading from `config/mcp.example.json`.
4. Move knowledge retrieval to pgvector.
5. Move distributed conversation/runtime state to Redis.
6. Add Alembic migrations for PostgreSQL.
