# System Architecture

This document outlines the architecture of the Bytebot system.

```mermaid
%%{init: {'theme': 'neutral'}}%%
graph TD
    subgraph Bytebot System
        UI[Bytebot UI (Port 9992)]
        Agent[Bytebot Agent (Port 9991)]
        Desktop[Bytebot Desktop (Port 9990)]
        Postgres[(PostgreSQL DB 5432)]
        Redis[(Redis Cache 6379)]
        Chroma[(Chroma Vector DB 8001)]
        Exporter[(Redis Exporter 9121)]
    end

    UI --> Agent
    Agent --> Desktop
    Agent --> Redis
    Agent --> Postgres
    Agent --> Chroma
    Redis --> Exporter
```

The diagram above shows how each service communicates internally in your environment.
