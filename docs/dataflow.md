# Data Flow Overview

The data movement inside Bytebot follows this pattern:

1. **User interaction** occurs through the Bytebot UI (port 9992).
2. **Bytebot Agent** (port 9991) receives and interprets requests from the UI.
3. The Agent **reads/writes data** to PostgreSQL (5432) for persistent storage.
4. The Agent **uses Redis (6379)** for caching active task states and message queues.
5. The Agent **stores AI embeddings** in Chroma (8001) for semantic search and memory recall.
6. **Bytebot Desktop (9990)** provides system orchestration and GUI control.
7. **Redis Exporter (9121)** provides monitoring metrics for Redis to Grafana or Prometheus.

