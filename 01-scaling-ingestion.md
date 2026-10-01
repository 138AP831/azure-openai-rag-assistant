# Workflow 1: Scaling Ingestion

Moving from a single Streamlit process to queue-based, horizontally scalable ingestion. Upload returns immediately, heavy work happens in workers, and the vector store is shared.

```mermaid
flowchart TD
    U["User uploads PDFs"] --> API["API / Streamlit front end"]
    API --> V{"Validate: type, size, page count"}
    V -- invalid --> X["Reject with clear message"]
    V -- valid --> H["Compute content hash"]
    H --> D{"Hash already indexed?"}
    D -- yes --> SK["Skip, reuse existing index"]
    D -- no --> BLOB[("Blob storage: raw PDF")]
    BLOB --> Q[["Ingestion queue"]]
    API --> ST["Return job id, status: queued"]

    Q --> W1["Worker 1"]
    Q --> W2["Worker 2"]
    Q --> WN["Worker N"]

    subgraph Worker["Per-worker pipeline"]
        direction TB
        P["PyMuPDF page extraction"] --> T{"Text found on page?"}
        T -- no --> OCR["OCR fallback"]
        T -- yes --> C["Recursive chunking"]
        OCR --> C
        C --> B["Batch chunks, e.g. 64 per call"]
        B --> E["Azure OpenAI embeddings"]
        E --> R{"429 or transient error?"}
        R -- yes --> BO["Exponential backoff + jitter"]
        BO --> E
        R -- no --> UP["Upsert vectors + metadata"]
    end

    W1 --> Worker
    W2 --> Worker
    WN --> Worker
    UP --> VDB[("Shared vector DB")]
    UP --> META[("Document metadata DB")]
    META --> DONE["Job status: indexed"]
    R -- "retries exhausted" --> DLQ[["Dead letter queue"]]
    DLQ --> ALERT["Alert + manual replay"]
```

## Key decisions

| Concern | Approach |
|---|---|
| Responsiveness | Upload only validates and enqueues; indexing is asynchronous with a pollable job id |
| Idempotency | Content hash prevents re-embedding the same file; upserts use deterministic chunk ids |
| Throughput | Worker count scales with queue depth; embeddings are batched |
| Rate limits | Backoff with jitter; global token-bucket shared across workers |
| Failure isolation | Poison files land in a dead letter queue instead of blocking the queue |
| Consistency | Document is marked `indexed` only after all chunks are upserted |
