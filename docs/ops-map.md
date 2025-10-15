# Operations Map

| Service | Role | Port | Depends On |
|----------|------|------|-------------|
| bytebot-ui | Frontend | 9992 | Agent |
| bytebot-agent | Backend | 9991 | Redis, Postgres, Chroma |
| bytebot-desktop | Supervisor | 9990 | Agent |
| bytebot-postgres | Database | 5432 | — |
| infra-redis-1 | Cache | 6379 | — |
| infra-redis-exporter-1 | Metrics | 9121 | Redis |
| infra-chroma-1 | Vector DB | 8001 | — |

This table summarizes your running containers and their connectivity.
