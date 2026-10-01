# Workflow 2: Scaling the Query Path

Stateless application replicas behind a load balancer, with a shared Redis cache, per-user rate limits and tracing on every stage.

```mermaid
flowchart TD
    C["Clients"] --> LB["Load balancer"]
    LB --> A1["App replica 1"]
    LB --> A2["App replica 2"]
    LB --> AN["App replica N"]

    A1 --> AUTH{"Authenticated?"}
    AUTH -- no --> E401["401 Unauthorized"]
    AUTH -- yes --> RL{"Within rate limit?"}
    RL -- no --> E429["429 with Retry-After"]
    RL -- yes --> NORM["Normalize question"]

    NORM --> KEY["Cache key = tenant + collection version + question hash"]
    KEY --> RC[("Redis cache")]
    RC --> HIT{"Hit?"}
    HIT -- yes --> OUT["Return cached answer + sources"]
    HIT -- no --> EMB["Embed question"]

    EMB --> VS[("Shared vector DB, read replicas")]
    VS --> TOPK["Top-k chunks with scores"]
    TOPK --> TH{"Best score above threshold?"}
    TH -- no --> NOANS["Return: not found in documents"]
    TH -- yes --> RER["Optional reranker"]
    RER --> LLM["Azure OpenAI chat, streamed"]
    LLM --> GUARD{"Answer cites retrieved context?"}
    GUARD -- no --> NOANS
    GUARD -- yes --> STORE["Write to Redis with TTL"]
    STORE --> OUT

    subgraph Observability
        direction LR
        TR["Tracing"] --- MET["Latency + token metrics"] --- LOG["Audit log"]
    end
    A1 -.-> Observability
    LLM -.-> Observability
```

## Cache key design

```mermaid
flowchart LR
    T["tenant id"] --> K["cache key"]
    CV["collection version"] --> K
    Q["normalized question hash"] --> K
    K --> R[("Redis, TTL")]
    UPL["New upload or delete"] -->|"bumps"| CV
```

Bumping the collection version on any upload or delete invalidates old answers without scanning or deleting keys.

## Scaling levers

| Bottleneck | Lever |
|---|---|
| Azure OpenAI throughput | Provisioned throughput, multiple deployments, regional failover |
| Retrieval latency | Vector DB read replicas, tuned HNSW parameters, metadata filters |
| Token cost | Lower `TOP_K`, reranking, answer cache with TTL |
| Perceived latency | Stream tokens to the UI as they arrive |
| Noisy neighbours | Per-tenant rate limits and quotas |
