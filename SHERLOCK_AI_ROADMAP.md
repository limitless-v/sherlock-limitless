# Sherlock — Full AI Development Roadmap

## Project Goal

Build Sherlock as a local-first public-web image investigation platform.

The user can begin with an image. Sherlock extracts useful non-sensitive signals from the image, searches permitted public sources, investigates discovered pages with controlled web-research tools, correlates public evidence, and presents traceable results.

> **Important:** Sherlock must not infer race/ethnicity or other sensitive personal traits from appearance. It must not use facial recognition as an identity lookup mechanism for unknown people. Results must be based on public, observable evidence such as image matches, OCR, EXIF, public links, usernames, domains, timestamps, and other non-sensitive signals.

---

# 0. Core Principles

The implementing AI MUST follow these principles:

1. **Local-first**
   - Image processing runs locally whenever practical.
   - Ollama is optional.
   - External APIs are used only where necessary for public-web discovery.

2. **Image-only initial input**
   - The user can start with only an image.
   - The system automatically derives useful search context.

3. **Evidence over assumptions**
   - Never claim an account belongs to a person without supporting public evidence.
   - Every result should retain source URLs and evidence.

4. **Non-sensitive search context**
   - EXIF
   - OCR
   - timestamps
   - image hashes
   - landmarks
   - visible text
   - public source metadata
   - public profile links
   - public usernames
   - domains
   - locations explicitly present in metadata or public evidence

5. **Modular architecture**
   - Search providers must be replaceable.
   - Agent Reach is an adapter/provider layer.
   - LLM functionality is optional.

6. **Controlled web research**
   - Respect robots.txt where applicable, rate limits, authentication boundaries, CAPTCHAs, and site terms.
   - Never bypass access controls.

7. **No hallucinated results**
   - If evidence does not exist, report that clearly.

---

# 1. Overall Architecture

```text
                           USER
                            │
                       Upload Image
                            │
                            ▼
                 ┌─────────────────────┐
                 │   Image Pipeline    │
                 └──────────┬──────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
        EXIF               OCR          Visual Context
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  Search Context     │
                 │      Builder        │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  Discovery Engine   │
                 └──────────┬──────────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
        Image Search    Web Search     Local FAISS
             │              │              │
             └──────────────┼──────────────┘
                            │
                            ▼
                    Candidate URLs
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Web Research Agent │
                 └──────────┬──────────┘
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
           Agent Reach    HTTPX      Playwright
                │           │           │
                └───────────┼───────────┘
                            ▼
                  Evidence Extraction
                            │
                            ▼
                  Evidence Correlation
                            │
                            ▼
                    Evidence Graph
                            │
                            ▼
                       Ranking
                            │
                            ▼
                    Results API
                            │
                            ▼
                       Frontend
```

---

# 2. Technology Stack

## Backend

- Python 3.12+
- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL
- asyncpg
- Pydantic
- Pydantic Settings

## AI / Computer Vision

- InsightFace
- ONNX Runtime
- OpenCV
- NumPy
- FAISS

## OCR

Preferred:
- PaddleOCR

Fallback:
- Tesseract

## Web

- HTTPX
- BeautifulSoup
- Playwright
- Agent Reach

## Optional LLM

- Ollama

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

## Infrastructure

- Docker Desktop
- Docker Compose

---

# 3. Repository Structure

```text
Sherlock/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── config/
│   │   │   └── settings.py
│   │   │
│   │   ├── database/
│   │   │   ├── session.py
│   │   │   ├── models.py
│   │   │   └── repositories/
│   │   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │
│   │   ├── ai/
│   │   │   ├── detection/
│   │   │   ├── preprocessing/
│   │   │   ├── embedding/
│   │   │   ├── matching/
│   │   │   └── vector_db/
│   │   │
│   │   ├── search/
│   │   │   ├── orchestrator.py
│   │   │   ├── modes.py
│   │   │   ├── local_search.py
│   │   │   ├── internet_search.py
│   │   │   └── hybrid_search.py
│   │   │
│   │   ├── discovery/
│   │   │   ├── engine.py
│   │   │   ├── schemas.py
│   │   │   ├── context/
│   │   │   │   ├── builder.py
│   │   │   │   ├── models.py
│   │   │   │   ├── exif.py
│   │   │   │   ├── ocr.py
│   │   │   │   ├── location.py
│   │   │   │   ├── language.py
│   │   │   │   └── keywords.py
│   │   │   ├── image_search/
│   │   │   ├── web_search/
│   │   │   └── providers/
│   │   │
│   │   ├── osint/
│   │   │   └── agent_reach/
│   │   │       ├── client.py
│   │   │       ├── capabilities.py
│   │   │       ├── parser.py
│   │   │       └── normalizer.py
│   │   │
│   │   ├── agents/
│   │   │   └── web_research/
│   │   │       ├── agent.py
│   │   │       ├── planner.py
│   │   │       ├── tools.py
│   │   │       ├── state.py
│   │   │       ├── policies.py
│   │   │       ├── prompts.py
│   │   │       └── schemas.py
│   │   │
│   │   ├── evidence/
│   │   │   ├── graph.py
│   │   │   ├── correlator.py
│   │   │   ├── ranker.py
│   │   │   └── schemas.py
│   │   │
│   │   └── services/
│   │
│   └── tests/
│
├── frontend/
├── data/
│   ├── uploads/
│   ├── candidates/
│   ├── cache/
│   └── results/
├── models/
├── docs/
├── tests/
├── docker-compose.yml
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
└── ROADMAP.md
```

---

# 4. Phase 0 — Environment

## Goal

Create a reproducible development environment.

## Tasks

- Python environment
- Git
- Docker Desktop
- PostgreSQL
- Node.js
- npm
- frontend environment

## Verify

```bash
python --version
docker --version
docker compose version
node --version
npm --version
```

## Done when

All development tools work.

---

# 5. Phase 1 — Backend Foundation

Create:

```text
backend/app/main.py
backend/app/config/
backend/app/api/
```

Implement:

```text
GET /health
```

Expected:

```json
{
  "status": "ok"
}
```

---

# 6. Phase 2 — PostgreSQL

Use Docker PostgreSQL.

Architecture:

```text
FastAPI
   │
SQLAlchemy Async
   │
asyncpg
   │
PostgreSQL
```

Implement:

- database connection
- SQLAlchemy async session
- Alembic
- initial migration

---

# 7. Phase 3 — Image Upload

Implement:

```text
POST /api/v1/images/upload
```

Input:

```text
multipart/form-data
```

Validate:

- JPEG
- PNG
- WEBP
- file size
- MIME type

Store:

```text
data/uploads/
```

Generate:

- image_id
- SHA256
- file size
- dimensions
- MIME type

---

# 8. Phase 4 — Image Preprocessing

Pipeline:

```text
Uploaded Image
      ↓
Decode
      ↓
Validate
      ↓
Normalize
      ↓
Resize
      ↓
Quality checks
```

Use:

- OpenCV
- Pillow
- NumPy

---

# 9. Phase 5 — Face Detection

Use InsightFace.

Pipeline:

```text
Image
 ↓
Face Detection
 ↓
Bounding Box
 ↓
Landmarks
 ↓
Quality Check
```

Store detection metadata.

Do not assume every image contains a usable face.

---

# 10. Phase 6 — Face Embedding

Use an appropriate local InsightFace/ArcFace model.

Pipeline:

```text
Face
 ↓
Alignment
 ↓
Embedding
 ↓
Vector
```

Store embeddings locally.

---

# 11. Phase 7 — FAISS

Implement local vector search.

Support:

```text
add
search
delete
rebuild
```

Pipeline:

```text
Embedding
 ↓
FAISS
 ↓
Nearest Neighbors
 ↓
Similarity Score
```

---

# 12. Phase 8 — Local Database

Create models for:

```text
images
faces
embeddings
searches
search_results
```

Use PostgreSQL for metadata.

Use FAISS for vector indexing.

---

# 13. Phase 9 — Local Search API

Implement:

```text
POST /search/local
```

Flow:

```text
Image
 ↓
Embedding
 ↓
FAISS
 ↓
Results
```

Return:

```json
{
  "mode": "local",
  "results": []
}
```

---

# 14. Phase 10 — Search Orchestrator

Create:

```text
LOCAL
INTERNET
HYBRID
```

Architecture:

```text
SearchOrchestrator
       │
       ├── LocalSearch
       ├── InternetSearch
       └── HybridSearch
```

At this point the original local-search architecture is complete.

---

# 15. Phase 11 — EXIF / Metadata Analysis

Create:

```text
discovery/context/exif.py
```

Extract locally:

- GPS
- timestamp
- camera
- device
- software
- orientation

Convert useful metadata into search context.

Do not expose raw GPS automatically.

---

# 16. Phase 12 — OCR

Implement local OCR.

Extract:

- visible text
- URLs
- usernames
- hashtags
- venue names
- company names
- signs
- language

Example:

```text
Image
 ↓
OCR
 ↓
"Kochi Marine Drive"
 ↓
SearchContext
```

---

# 17. Phase 13 — Image Fingerprinting

Generate:

- SHA256
- pHash
- dHash
- aHash

Purpose:

```text
duplicate detection
near-duplicate detection
image clustering
```

---

# 18. Phase 14 — Visual Context Analysis

Implement local visual analysis for:

- landmarks
- buildings
- venues
- objects
- scene type
- signage

Predictions are search hints, not verified facts.

---

# 19. Phase 15 — Search Context Builder

Combine:

```text
EXIF
OCR
Visual Context
Image Hash
Optional user-provided filters
```

into:

```python
SearchContext
```

Example:

```json
{
  "keywords": [],
  "text": [],
  "location": null,
  "timestamp": null,
  "language": null,
  "image_hash": {}
}
```

The user can still provide only an image.

---

# 20. Phase 16 — Discovery Engine

Create:

```text
DiscoveryEngine
```

Responsibilities:

- generate discovery tasks
- select available providers
- deduplicate results
- normalize candidates

Architecture:

```text
DiscoveryEngine
   │
   ├── ImageSearch
   ├── WebSearch
   ├── LocalSearch
   └── AgentReach
```

---

# 21. Phase 17 — Search Providers

Create provider interfaces.

## Image Search

```python
class ImageSearchProvider:
    async def search(self, image, context):
        ...
```

## Web Search

```python
class WebSearchProvider:
    async def search(self, query, context):
        ...
```

Providers must be replaceable.

Use permitted/public interfaces. Do not bypass search-engine protections.

---

# 22. Phase 18 — Agent Reach Integration

Create:

```text
backend/app/osint/agent_reach/
```

Implement:

```text
AgentReachClient
AgentReachCapabilities
AgentReachParser
AgentReachNormalizer
```

First inspect capabilities:

```bash
agent-reach doctor --json
```

Use the detected capabilities.

Do not assume every source is available.

Agent Reach is a web-access/discovery provider, not the identity engine.

---

# 23. Phase 19 — Web Research Agent

Create:

```text
backend/app/agents/web_research/
```

Input:

```text
Candidate URLs
SearchContext
```

Output:

```text
Evidence
Candidate profiles
Images
Links
Source metadata
```

The agent investigates public pages through controlled tools.

---

# 24. Phase 20 — Agent Tools

Implement controlled tools:

```text
search_web()
fetch_page()
extract_text()
extract_links()
extract_images()
extract_metadata()
find_public_profile_links()
find_external_profiles()
```

The LLM chooses tools.

Python performs the actual operations.

---

# 25. Phase 21 — Agent State

Create:

```python
ResearchState
```

Track:

```text
seed_urls
visited_urls
discovered_urls
queries
images
profiles
evidence
errors
```

Prevent duplicate crawling.

---

# 26. Phase 22 — Crawl Policies

Hard limits:

```text
MAX_PAGES
MAX_DEPTH
MAX_IMAGES
MAX_RUNTIME
MAX_REQUESTS_PER_DOMAIN
```

Respect:

- robots.txt where applicable
- rate limits
- site policies
- authentication boundaries
- CAPTCHAs

Never implement bypass mechanisms.

---

# 27. Phase 23 — Candidate Extraction

Normalize pages into:

```json
{
  "url": "",
  "domain": "",
  "title": "",
  "images": [],
  "links": [],
  "public_identifiers": [],
  "public_profile_links": [],
  "locations": [],
  "dates": []
}
```

Focus on publicly observable information.

---

# 28. Phase 24 — Evidence Graph

Create:

```text
EvidenceGraph
```

Nodes:

```text
Image
URL
Domain
Profile
Username
Website
Organization
Location
```

Edges:

```text
image_found_on
links_to
same_public_identifier
same_image
mentions
published_at
located_at
```

Every edge retains its source.

---

# 29. Phase 25 — Image Correlation

When public images are discovered:

```text
Candidate Image
      ↓
SHA256
pHash
visual similarity
      ↓
Comparison
```

Classify:

```text
exact duplicate
near duplicate
similar
unrelated
```

Use existing local image-processing infrastructure.

---

# 30. Phase 26 — Optional Ollama

Ollama is optional.

Use it for:

- query generation
- page summarization
- entity extraction
- relationship extraction
- evidence classification
- research planning

Architecture:

```text
Web Research Agent
        │
        ▼
      Ollama
        │
        ▼
Structured decision
        │
        ▼
Controlled tool
```

Do not make Ollama a required dependency.

---

# 31. Phase 27 — Evidence Ranking

Create:

```text
EvidenceRanker
```

Strong evidence:

- exact public image match
- explicit public profile link
- same public username
- same public website
- repeated independent sources

Weak evidence:

- generic name
- generic location
- visual similarity alone
- single unverified mention

Separate:

```text
observed evidence
inference
uncertainty
```

Never use race/ethnicity or other sensitive traits as ranking signals.

---

# 32. Phase 28 — Results API

Implement:

```text
GET /search/{search_id}
GET /search/{search_id}/results
GET /search/{search_id}/evidence
```

Example:

```json
{
  "search_id": "...",
  "status": "completed",
  "sources_checked": 24,
  "pages_analyzed": 42,
  "results": []
}
```

---

# 33. Phase 29 — Frontend

Build:

```text
Upload Page
Search Progress
Results
Evidence Graph
Source Details
Search History
Settings
```

Initial UI:

```text
┌──────────────────────────────┐
│                              │
│       Drop image here        │
│                              │
│       [ Browse Image ]       │
│                              │
└──────────────────────────────┘

             [ SEARCH ]
```

---

# 34. Phase 30 — Live Search Progress

Display:

```text
Uploading
   ↓
Analyzing image
   ↓
Extracting metadata
   ↓
Running OCR
   ↓
Building search context
   ↓
Searching public sources
   ↓
Analyzing candidate pages
   ↓
Correlating evidence
   ↓
Ranking
   ↓
Complete
```

---

# 35. Phase 31 — Evidence Dashboard

Display:

```text
Sources Found
Pages Analyzed
Images Found
Public Profile Links
Search Queries
Evidence Connections
```

Each result must show:

```text
Source
URL
Why it was discovered
Evidence
Timestamp where available
Evidence strength
```

---

# 36. Phase 32 — Search History

PostgreSQL stores:

```text
searches
search_context
search_sources
candidates
evidence
```

Allow:

```text
view
delete
export
```

---

# 37. Phase 33 — Caching

Cache:

```text
web responses
search results
image hashes
page metadata
```

Use PostgreSQL initially.

Add Redis only when performance requires it.

---

# 38. Phase 34 — Security

Implement:

```text
file validation
file-size limits
MIME validation
path traversal protection
SSRF protection
URL validation
domain restrictions
request timeouts
rate limiting
```

The research agent must not freely request internal network addresses.

Protect against:

```text
localhost
127.0.0.1
private IP ranges
cloud metadata endpoints
```

unless explicitly required by the application.

---

# 39. Phase 35 — Privacy

Implement:

```text
automatic upload cleanup
configurable retention
search deletion
cache cleanup
metadata controls
```

Keep local processing local whenever possible.

---

# 40. Phase 36 — Testing

## Unit Tests

Test:

```text
EXIF
OCR
hashing
face detection
embedding
FAISS
search context
URL validation
evidence graph
ranking
```

## Integration Tests

Test:

```text
FastAPI → PostgreSQL
FastAPI → FAISS
Discovery → Provider
Agent → Tools
Agent → Evidence
```

## End-to-End

Test:

```text
Upload
 ↓
Analysis
 ↓
Discovery
 ↓
Research
 ↓
Evidence
 ↓
Results
```

---

# 41. Phase 37 — Performance

Measure:

```text
image processing time
embedding time
OCR time
search latency
pages/minute
agent runtime
database queries
FAISS latency
memory usage
```

Optimize only after measuring.

---

# 42. Phase 38 — Docker

Containerize:

```text
frontend
backend
postgres
```

Optional:

```text
ollama
redis
```

Do not add optional services until needed.

---

# 43. Phase 39 — Production

Final architecture:

```text
                        FRONTEND
                           │
                           ▼
                       FastAPI
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
        Image AI       Discovery      Database
             │             │             │
             │             ▼             │
             │       Search Providers   │
             │             │             │
             │        Agent Reach       │
             │             │             │
             │       Research Agent    │
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                    Evidence Engine
                           │
                           ▼
                    Ranking / Results
```

---

# 44. Final AI Decision Flow

```text
START
 │
 ▼
Image uploaded?
 │
 ├── NO → validation error
 │
 └── YES
      │
      ▼
Validate image
      │
      ▼
Extract metadata
      │
      ▼
Run OCR
      │
      ▼
Generate image fingerprints
      │
      ▼
Run visual context analysis
      │
      ▼
Build SearchContext
      │
      ▼
Determine search mode
      │
      ├── LOCAL
      │      ↓
      │    FAISS
      │
      ├── INTERNET
      │      ↓
      │    Discovery Engine
      │
      └── HYBRID
             ↓
       Local + Discovery
             │
             ▼
       Candidate URLs
             │
             ▼
       Web Research Agent
             │
             ▼
       Controlled Tools
             │
             ▼
       Evidence Extraction
             │
             ▼
       Candidate Images
             │
             ▼
       Image Correlation
             │
             ▼
       Evidence Graph
             │
             ▼
          Ranking
             │
             ▼
          Results
```

---

# 45. Development Order

The AI MUST implement phases sequentially.

```text
✅ Phase 0   Environment
✅ Phase 1   Foundation
✅ Phase 2   Image Upload
✅ Phase 3   Face Detection
✅ Phase 4   Preprocessing
✅ Phase 5   Embeddings
✅ Phase 6   FAISS
✅ Phase 7   Similarity
✅ Phase 8   Local DB
✅ Phase 9   Local Search
✅ Phase 10  Search Orchestration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Phase 11  EXIF / Metadata
✅ Phase 12  OCR
✅ Phase 13  Image Fingerprinting
✅ Phase 14  Visual Context
✅ Phase 15  Search Context
✅ Phase 16  Discovery Engine
✅ Phase 17  Search Providers
✅ Phase 18  Agent Reach
✅ Phase 19  Web Research Agent
✅ Phase 20  Agent Tools
✅ Phase 21  Agent State
✅ Phase 22  Crawl Policies
✅ Phase 23  Candidate Extraction
✅ Phase 24  Evidence Graph
✅ Phase 25  Image Correlation
▶ Phase 26  Ollama [OPTIONAL]
✅ Phase 27  Evidence Ranking
▶ Phase 28  Results API
▶ Phase 29  Frontend
▶ Phase 30  Progress UI
▶ Phase 31  Evidence Dashboard
▶ Phase 32  Search History
▶ Phase 33  Caching
▶ Phase 34  Security
▶ Phase 35  Privacy
▶ Phase 36  Testing
▶ Phase 37  Performance
▶ Phase 38  Docker
▶ Phase 39  Production
```

---

# 46. Mandatory AI Implementation Workflow

For EVERY phase, the coding AI MUST:

1. Inspect the existing repository.
2. Inspect the previous phase implementation.
3. Do not rewrite working modules unnecessarily.
4. Implement only the current phase.
5. Add or update tests.
6. Run the relevant tests.
7. Fix regressions.
8. Update documentation.
9. Report exactly what changed.
10. Report files created/modified.
11. Report commands/tests executed.
12. Report any known limitations.
13. Stop after completing the current phase.
14. Wait for the user to explicitly request the next phase.

## Critical Rule

**Do not automatically implement future phases.**

If asked to implement Phase 12, implement Phase 12 only.

Do not implement Phase 13, 14, 15, etc. unless explicitly requested.

---

# 47. Definition of Done

A phase is complete only when:

```text
[ ] Implementation exists
[ ] Existing functionality still works
[ ] Tests pass
[ ] Error handling exists
[ ] Configuration is documented
[ ] No secrets are hard-coded
[ ] Documentation is updated
[ ] Git diff has been reviewed
[ ] No unnecessary dependencies were added
```

---

# 48. Final Project Objective

The finished Sherlock system should provide:

```text
Image
  ↓
Local analysis
  ↓
Search context
  ↓
Public-web discovery
  ↓
Agent Reach
  ↓
Controlled web research
  ↓
Public evidence
  ↓
Image correlation
  ↓
Evidence graph
  ↓
Ranked, traceable results
```

The system should be:

- local-first
- modular
- testable
- explainable
- evidence-driven
- privacy-conscious
- provider-independent
- LLM-optional
- Docker-ready
