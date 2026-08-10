# AI_DEVELOPMENT_ROADMAP.md

# Local AI Face Search + Public OSINT Platform

## 1. Project Objective

Build a modular web application that allows a user to upload an image and search for **publicly available online profiles and locally indexed faces** that may correspond to the person in the image.

The system must support three search modes:

```text
LOCAL
INTERNET
HYBRID
```

The application must remain useful even when the local face database is empty or contains very little data.

The face-recognition pipeline must run locally.

The OSINT discovery layer will use Agent Reach.

An LLM such as Ollama is optional.

---

# 2. Core Architecture

```text
                         USER
                           │
                           ▼
                    ┌──────────────┐
                    │ Upload Image │
                    └──────┬───────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Face Detection   │
                  │ SCRFD / RetinaFace│
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Face Alignment   │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Face Embedding   │
                  │ ArcFace/InsightFace│
                  └────────┬─────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Search Orchestrator  │
                └──────────┬───────────┘
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
          LOCAL         INTERNET       HYBRID
             │             │             │
             ▼             ▼             ▼
           FAISS       Agent Reach   FAISS + Agent Reach
             │             │             │
             └─────────────┼─────────────┘
                           │
                           ▼
                  Candidate Results
                           │
                           ▼
                  Candidate Images
                           │
                           ▼
                  Local Face Matching
                           │
                           ▼
                    Ranking Engine
                           │
                           ▼
                       Results
```

---

# 3. Search Modes

The system must expose three search modes.

## 3.1 LOCAL

Search only the locally indexed face database.

```text
Image
 ↓
Face Embedding
 ↓
FAISS
 ↓
Local Matches
 ↓
Ranking
```

Internet access:

```text
DISABLED
```

Use this mode when the user has a local dataset.

---

## 3.2 INTERNET

Search public web sources using Agent Reach.

```text
Image
 ↓
Face Embedding
 ↓
Agent Reach
 ↓
Public Candidate Pages
 ↓
Candidate Images
 ↓
Local Face Verification
 ↓
Ranking
```

Local FAISS:

```text
NOT REQUIRED
```

This is the **primary mode during early development** because the project may have little or no local face data.

---

## 3.3 HYBRID

Search both the local database and public internet.

```text
                    Query Image
                         │
                         ▼
                   Face Embedding
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
           FAISS               Agent Reach
              │                     │
              ▼                     ▼
        Local Matches        Public Candidates
              │                     │
              └──────────┬──────────┘
                         ▼
                  Candidate Merger
                         │
                         ▼
                 Face Verification
                         │
                         ▼
                     Ranking
```

Use this mode once the local database becomes useful.

---

# 4. Search Mode UI

After uploading an image, display:

```text
┌─────────────────────────────────────────────┐
│              Choose Search Mode             │
│                                             │
│  ○ Local                                    │
│    Search the local face database           │
│                                             │
│  ● Internet                                 │
│    Search public websites using Agent Reach │
│                                             │
│  ○ Hybrid                                   │
│    Search local database + public web       │
│                                             │
│              [ Start Search ]               │
└─────────────────────────────────────────────┘
```

Default:

```text
INTERNET
```

The default can later be changed in settings.

If the local database is empty, display:

```text
Local database contains no indexed faces.

Internet search is recommended.
```

If the user selects:

```text
HYBRID
```

with an empty local database, the system should automatically skip the FAISS stage instead of failing.

---

# 5. Search Orchestration Layer

Create a dedicated service:

```text
backend/app/search/
```

Structure:

```text
search/

├── orchestrator.py
├── modes.py
├── requests.py
├── results.py
├── local_search.py
├── internet_search.py
└── hybrid_search.py
```

The API layer must NOT contain search-routing logic.

Bad:

```python
if mode == "internet":
    ...
```

inside the API route.

Instead:

```text
API
 ↓
SearchOrchestrator
 ↓
Selected Search Strategy
```

---

# 6. Search Mode Definition

Create:

```text
SearchMode
```

Supported values:

```text
LOCAL
INTERNET
HYBRID
```

Example:

```python
class SearchMode(str, Enum):
    LOCAL = "local"
    INTERNET = "internet"
    HYBRID = "hybrid"
```

---

# 7. Search Orchestrator

Create:

```text
SearchOrchestrator
```

Responsibilities:

* Validate search mode
* Check available capabilities
* Select search strategy
* Execute search
* Merge results
* Pass candidates to verification
* Return normalized results

Conceptually:

```text
SearchOrchestrator
        │
        ├── LocalSearchService
        │
        ├── InternetSearchService
        │
        └── HybridSearchService
```

---

# 8. Local Search Service

```text
LocalSearchService
```

Responsibilities:

```text
Embedding
 ↓
FAISS Search
 ↓
Similarity
 ↓
Metadata Lookup
 ↓
Local Candidates
```

If FAISS has no indexed vectors:

```text
return []
```

Do NOT throw an application error.

---

# 9. Internet Search Service

```text
InternetSearchService
```

Responsibilities:

```text
Query
 ↓
Agent Reach
 ↓
Candidate URLs
 ↓
Candidate Metadata
 ↓
Candidate Images
```

Agent Reach is the discovery layer.

It does NOT perform facial verification.

---

# 10. Hybrid Search Service

```text
HybridSearchService
```

Workflow:

```text
Query
 │
 ├───────────────┐
 ▼               ▼
Local Search   Internet Search
 │               │
 ▼               ▼
FAISS         Agent Reach
 │               │
 └───────┬───────┘
         ▼
    Result Merger
         │
         ▼
   Deduplication
         │
         ▼
   Face Verification
         │
         ▼
      Ranking
```

The two searches should be independently executable.

If one source fails:

```text
Local succeeds
Internet fails
```

the system should still return the local results.

Likewise:

```text
Local unavailable
Internet succeeds
```

the system should still return internet results.

---

# 11. Search Request

API:

```text
POST /api/v1/search
```

Request:

```json
{
  "image_id": "uuid",
  "mode": "internet"
}
```

Supported:

```text
local
internet
hybrid
```

Optional parameters:

```json
{
  "image_id": "uuid",
  "mode": "hybrid",
  "max_results": 50,
  "sources": [
    "web",
    "github",
    "reddit"
  ]
}
```

---

# 12. Search Response

Normalize all search modes into the same response format.

```json
{
  "search_id": "uuid",
  "mode": "internet",
  "status": "completed",
  "results": [
    {
      "source": "github",
      "url": "https://example.com/profile",
      "display_name": "Example",
      "username": "example",
      "image_url": "https://example.com/avatar.jpg",
      "face_similarity": 0.91,
      "confidence": "high"
    }
  ]
}
```

The frontend should not need to know whether a result came from FAISS or Agent Reach beyond displaying its source.

---

# 13. Search Result Normalization

All providers must return a common internal structure.

```text
SearchResult

├── id
├── source
├── url
├── title
├── username
├── display_name
├── image_urls
├── text
├── discovery_method
├── face_similarity
├── confidence
└── discovered_at
```

This prevents Agent Reach-specific data structures from spreading throughout the application.

---

# 14. Result Deduplication

Hybrid searches can discover the same person/profile through multiple sources.

Implement:

```text
ResultDeduplicator
```

Deduplicate using:

```text
Exact URL
Normalized URL
Username
Profile identifiers
Image hash
Repeated public identifiers
```

Do not merge people solely because they have the same name.

---

# 15. Phase Development Order

The revised development order is:

```text
Phase 0
Environment

        ↓

Phase 1
Project Foundation

        ↓

Phase 2
Image Upload

        ↓

Phase 3
Face Detection

        ↓

Phase 4
Face Preprocessing

        ↓

Phase 5
Face Embeddings

        ↓

Phase 6
FAISS Vector Search

        ↓

Phase 7
Similarity Engine

        ↓

Phase 8
Local Face Database

        ↓

Phase 9
Local Search API

        ↓

Phase 10
Search Orchestration
★ NEW

        ↓

Phase 11
Agent Reach Integration

        ↓

Phase 12
Agent Reach Capability Detection

        ↓

Phase 13
Internet Search

        ↓

Phase 14
Candidate Collection

        ↓

Phase 15
Candidate Image Verification

        ↓

Phase 16
Hybrid Search

        ↓

Phase 17
Result Deduplication

        ↓

Phase 18
Ranking

        ↓

Phase 19
Identity Aggregation

        ↓

Phase 20
Frontend

        ↓

Phase 21
Search History

        ↓

Phase 22
Optional Ollama

        ↓

Phase 23
Security

        ↓

Phase 24
Privacy

        ↓

Phase 25
Testing

        ↓

Phase 26
Performance

        ↓

Phase 27
Deployment
```

---

# 16. Recommended Initial Development Strategy

Because the project currently has little local data:

## Stage 1

Build:

```text
Face Detection
       ↓
Face Embedding
       ↓
Internet Search
       ↓
Agent Reach
       ↓
Candidate Collection
       ↓
Face Verification
```

Do not spend significant time building a huge FAISS dataset yet.

---

## Stage 2

Create a small local test dataset:

```text
10–100 faces
```

Use it to validate:

```text
LOCAL
```

mode.

---

## Stage 3

Develop:

```text
HYBRID
```

mode.

---

## Stage 4

As the local database grows:

```text
100
 ↓
1,000
 ↓
10,000
 ↓
100,000+
```

FAISS becomes increasingly useful.

---

# 17. Important Separation of Responsibilities

The architecture must maintain these boundaries:

```text
┌──────────────────────────┐
│ FACE AI                  │
│                          │
│ InsightFace / ArcFace    │
│ SCRFD                    │
│ ONNX Runtime             │
│                          │
│ Determines visual        │
│ similarity               │
└──────────────────────────┘


┌──────────────────────────┐
│ LOCAL SEARCH             │
│                          │
│ FAISS                    │
│ SQLite/PostgreSQL        │
│                          │
│ Searches indexed data    │
└──────────────────────────┘


┌──────────────────────────┐
│ INTERNET OSINT           │
│                          │
│ Agent Reach              │
│                          │
│ Discovers public         │
│ information              │
└──────────────────────────┘


┌──────────────────────────┐
│ OPTIONAL LLM             │
│                          │
│ Ollama                   │
│                          │
│ Summarizes and extracts  │
│ information              │
└──────────────────────────┘
```

---

# 18. Optional Ollama

Ollama remains completely optional.

```text
OLLAMA_ENABLED=false
```

The system must work normally without it.

Use Ollama only after the search pipeline is functional.

Good uses:

```text
Profile summarization
Information extraction
Evidence organization
Duplicate explanation
Natural-language reports
```

Never use it for:

```text
Face detection
Face embedding
Face verification
Similarity calculation
```

---

# 19. Final Search Architecture

```text
                         IMAGE
                           │
                           ▼
                    Face Detection
                           │
                           ▼
                    Face Embedding
                           │
                           ▼
                 Search Orchestrator
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
           LOCAL        INTERNET       HYBRID
             │             │             │
           FAISS        Agent Reach   FAISS + Agent Reach
             │             │             │
             └─────────────┼─────────────┘
                           │
                           ▼
                   Candidate Results
                           │
                           ▼
                   Candidate Images
                           │
                           ▼
                Local Face Verification
                           │
                           ▼
                    Deduplication
                           │
                           ▼
                       Ranking
                           │
                           ▼
                       Results
                           │
                           ▼
                  Optional Ollama
```

---

# 20. Definition of Done

The project is complete when:

* [ ] Local search works
* [ ] Internet search works
* [ ] Hybrid search works
* [ ] Search mode can be selected from the UI
* [ ] Internet mode works with an empty local database
* [ ] Hybrid mode gracefully handles an empty local database
* [ ] Agent Reach is isolated behind an adapter
* [ ] Agent Reach capabilities are detected dynamically
* [ ] Candidate URLs are normalized
* [ ] Candidate images can be processed locally
* [ ] Face verification works locally
* [ ] Results from multiple sources can be deduplicated
* [ ] Results are ranked
* [ ] Local FAISS database can grow independently
* [ ] Ollama remains optional
* [ ] CPU-only operation works
* [ ] Security checks pass
* [ ] Privacy controls exist
* [ ] Tests pass
* [ ] Docker deployment works

---

# 21. AI Coding-Agent Instruction

Before implementing anything:

1. Read `AI_DEVELOPMENT_ROADMAP.md`.
2. Inspect the existing repository.
3. Determine the current phase.
4. Never skip phases.
5. Never implement future phases prematurely.
6. Explain the intended changes.
7. List files that will be created or modified.
8. Implement only the current phase.
9. Run tests.
10. Report the results.
11. Stop before proceeding to the next phase.

The system must remain modular.

The most important architectural rule is:

```text
Search Mode
     ↓
Search Orchestrator
     ↓
┌──────────────┬────────────────┬──────────────┐
│              │                │
LOCAL       INTERNET          HYBRID
│              │                │
FAISS       Agent Reach      FAISS + Agent Reach
```

The application must never assume that a local dataset exists.

The **Internet search mode must be a fully functional first-class mode**, not merely a fallback for LOCAL search.
