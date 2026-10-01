# Workflow 3: Edge Cases and Failure Handling

What the system should do when inputs or dependencies misbehave. Each branch ends in a clear, honest outcome for the user.

## Ingestion edge cases

```mermaid
flowchart TD
    S["PDF received"] --> F1{"Readable PDF?"}
    F1 -- "corrupt or encrypted" --> R1["Reject: ask for a valid or unlocked file"]
    F1 -- yes --> F2{"File within size and page limits?"}
    F2 -- no --> R2["Reject or process in background with warning"]
    F2 -- yes --> F3{"Same content hash already indexed?"}
    F3 -- yes --> R3["Skip and tell user it is already indexed"]
    F3 -- no --> F4{"Extractable text per page?"}
    F4 -- "none, scanned images" --> OCR["OCR fallback, flag low confidence"]
    F4 -- "partial" --> MIX["Index text pages, warn about empty pages"]
    F4 -- yes --> OK["Chunk, embed, index"]
    OCR --> OK
    MIX --> OK
    OK --> F5{"Embedding call fails?"}
    F5 -- "429 / timeout" --> RT["Retry with backoff"]
    RT --> F6{"Retries exhausted?"}
    F6 -- yes --> PART["Roll back partial chunks, mark document failed"]
    F6 -- no --> OK
    F5 -- no --> DONE["Mark document indexed"]
```

## Question-time edge cases

```mermaid
flowchart TD
    Q["User question"] --> A{"Any documents indexed?"}
    A -- no --> M1["Prompt user to upload a PDF first"]
    A -- yes --> B{"Question empty or too long?"}
    B -- yes --> M2["Validate input, ask to rephrase"]
    B -- no --> C["Retrieve top-k"]
    C --> D{"Relevant chunks found?"}
    D -- "none or low similarity" --> M3["Answer: not in the provided documents"]
    D -- yes --> E{"Context fits model window?"}
    E -- no --> TRIM["Trim lowest-ranked chunks"]
    E -- yes --> G["Generate grounded answer"]
    TRIM --> G
    G --> H{"Azure call succeeds?"}
    H -- "429" --> RT["Backoff, then friendly retry message"]
    H -- "content filter" --> M4["Explain the response was blocked, suggest rephrasing"]
    H -- "timeout" --> M5["Retry once, then show error without losing the question"]
    H -- yes --> I{"Retrieved text contains instructions?"}
    I -- yes --> SAFE["Treat as data only, never follow it"]
    I -- no --> OUT["Answer with filename and page citations"]
    SAFE --> OUT
```

## Concurrency and consistency

```mermaid
sequenceDiagram
    participant U1 as User A
    participant U2 as User B
    participant App
    participant Cache
    participant VDB as Vector DB

    U1->>App: Upload new PDF
    App->>VDB: Upsert chunks
    App->>Cache: Bump collection version
    U2->>App: Ask question (during upload)
    App->>Cache: Lookup with old version key
    Cache-->>App: Hit, answer from previous index
    Note over App,Cache: Acceptable: answer reflects the last completed index
    App-->>U2: Cached answer
    App->>Cache: Version now new, old keys unreachable
    U2->>App: Ask again
    App->>VDB: Retrieve from updated index
    VDB-->>App: Chunks including new PDF
    App-->>U2: Fresh answer
```

## Behaviour summary

| Situation | Expected behaviour |
|---|---|
| Scanned or image-only PDF | OCR fallback, or a clear message that no text was found |
| Duplicate upload | Detected by content hash, no re-embedding |
| Answer not in documents | Explicit "not found" instead of a guess |
| Azure 429 or timeout | Backoff and retry, then a friendly error |
| Content filter trigger | Explain and suggest rephrasing |
| Prompt injection inside a PDF | Retrieved text is data only and never treated as instructions |
| Upload during active queries | Collection version bump, no stale cache hits afterwards |
| Process restart | Local LRU cache is lost by design; Redis keeps it in production |
