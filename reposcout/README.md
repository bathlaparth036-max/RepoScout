# RepoScout — Intelligent GitHub Repository Discovery

RepoScout is an intelligent GitHub repository discovery tool built as a Chrome Extension (Manifest V3) powered by a Python FastAPI backend. Developers can enter natural-language requirements (e.g. *"I want a beginner-friendly RAG project using Python, LangChain and FAISS"*), and RepoScout identifies, ranks, and presents relevant repositories.

> **Status:** Performance Optimization & Two-Stage Search Architecture Complete. Multi-backend caching abstraction (in-memory + Redis-ready), two-stage candidate pruning (Stage 1 lightweight filter → Stage 2 top 5 parallel deep analysis), request timeouts, and progressive frontend search status. All 24 backend tests passing.

---

## Query Understanding Pipeline

```
User Natural Language Input
  e.g. "I want a beginner RAG project using Python, LangChain and FAISS"
       ↓
Query Service (backend/app/services/query_service.py)
  + LLM Service Abstraction (OpenAI / Gemini / Ollama / Deterministic Fallback)
       ↓
Structured Requirements Payload (POST /api/query/understand)
  {
    "original_query": "...",
    "keywords": ["RAG"],
    "languages": ["Python"],
    "frameworks": ["LangChain"],
    "libraries": ["FAISS"],
    "databases": [],
    "project_type": "RAG",
    "difficulty": "beginner",
    "requirements": ["RAG architecture", "Python", "LangChain", "FAISS"],
    "github_search_query": "RAG LangChain FAISS language:python"
  }
       ↓
GitHub REST API v3 (GET https://api.github.com/search/repositories?q=...)
       ↓
Chrome Extension Cards (Avatars, Stars, Forks, Topics, Relative Time)
```

---

## Architecture Overview

```
                                      Chrome Browser
                              ┌─────────────────────────────┐
                              │     RepoScout Extension     │
                              │       (Manifest V3)         │
                              │   React 19 + Vite + Lucide  │
                              └──────────────┬──────────────┘
                                             │ HTTP REST / JSON
                                             ▼
                              ┌─────────────────────────────┐
                              │    FastAPI Backend Server   │
                              │      http://localhost:8000  │
                              └──────────────┬──────────────┘
                                             │
      ┌──────────────────────┬───────────────┼───────────────┬──────────────────────┐
      │                      │               │               │                      │
┌─────▼────────┐      ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐        ┌──────▼──────┐
│cache_service │      │query_service│ │github_serv. │ │analysis_serv│        │ranking_serv.│
│ (In-memory / │      │  (Intent &  │ │(REST/GraphQL│ │(Repo quality│        │ (Relevance  │
│  Redis-ready)│      │   Tokens)   │ │  Boundary)  │ │  heuristics)│        │  & Scores)  │
└──────────────┘      └─────────────┘ └─────────────┘ └─────────────┘        └─────────────┘
```

### Key Highlights
- **Clean Service Boundaries:** `github_service`, `query_service`, `analysis_service`, `ranking_service`, and `cache_service` are decoupled and independent.
- **Security-First:** GitHub API credentials remain strictly server-side in backend `.env` and are never exposed to the frontend extension.
- **Manifest V3 Compliant:** Popup bundle uses zero inline scripts and relative asset paths (`./assets/...`).
- **Professional Developer Aesthetic:** High-contrast neutral palette (White, Slate Black, Silver, Neutral Gray) matching modern developer tooling.

---

## Project Structure

```
reposcout/
├── extension/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx              # Brand logo, version, search/saved tabs, backend health pill
│   │   │   ├── SearchBar.jsx           # Search input with keyboard shortcuts
│   │   │   ├── SuggestionPills.jsx     # Example natural-language query chips
│   │   │   ├── FilterToolbar.jsx       # Dynamic language filter, min match score, sorting criteria
│   │   │   ├── RepositoryList.jsx      # Discovered count & list coordinator
│   │   │   ├── RepositoryCard.jsx      # Individual repository card with bookmark & compare toggles
│   │   │   ├── AnalysisPanel.jsx       # Complete detail view with sequential architecture pipeline
│   │   │   ├── CompareModal.jsx        # Side-by-side multi-repository comparison modal
│   │   │   ├── StatusBanner.jsx        # Network, empty query, & error alerts
│   │   │   └── LoadingSkeleton.jsx     # Clean pulse skeletons with progressive status
│   │   ├── pages/
│   │   │   ├── SearchPage.jsx          # Main discovery view with filter toolbar
│   │   │   └── SavedPage.jsx           # Bookmarked repositories, search, & 1-click Markdown export
│   │   ├── services/
│   │   │   └── api.js                  # Encapsulated REST client
│   │   ├── hooks/
│   │   │   ├── useRepoSearch.js        # Search state, health probe & lifecycle
│   │   │   └── useBookmarks.js         # Chrome storage local bookmarks & export
│   │   ├── utils/
│   │   │   ├── formatters.js           # Number & language styling utilities
│   │   │   └── storage.js              # Chrome local storage & markdown table export
│   │   ├── styles/
│   │   │   └── index.css               # Developer-tool CSS design system
│   │   ├── App.jsx                     # Root application container
│   │   └── main.jsx                    # React 19 mount point
│   ├── public/
│   │   ├── icons/                      # 16px, 48px, 128px extension icons
│   │   └── manifest.json               # Manifest V3 specification
│   ├── manifest.json
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py               # GET /api/health and GET /api/search
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── github_service.py       # GitHub API boundary & mock catalog
│   │   │   ├── query_service.py        # Intent parser & keyword extractor
│   │   │   ├── analysis_service.py     # Code & README inspection boundary
│   │   │   ├── ranking_service.py      # Match percentage & star ranker
│   │   │   └── cache_service.py        # Key-value TTL caching
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── repository.py           # Domain dataclass models
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── health.py               # HealthResponse schema
│   │   │   └── repository.py           # RepositoryItem & SearchResponse
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py               # Pydantic v2 settings & CORS
│   │   └── main.py                     # FastAPI application entry point
│   ├── tests/
│   │   └── test_api.py                 # Pytest suite for API & services
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example
│   └── .env
│
├── README.md
└── .gitignore
```

---

## Getting Started

### Prerequisites
- **Python 3.10+** (tested with Python 3.14)
- **Node.js 18+** & **npm** (tested with Node v26)
- **Google Chrome** (or Chromium-based browser)

---

## 1. Backend Setup & Execution

### Navigate to backend directory:
```bash
cd reposcout/backend
```

### Create and activate a Python virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependencies:
```bash
pip install -r requirements.txt
```

### Configure environment:
```bash
cp .env.example .env
```

### Run the FastAPI backend server:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend is now running at:
- **Health Check:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **Interactive OpenAPI Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Sample Search Query:** [http://127.0.0.1:8000/api/search?q=RAG](http://127.0.0.1:8000/api/search?q=RAG)

### Run Backend Tests:
```bash
pytest -v
```

---

## 2. Frontend Setup & Build

### Navigate to extension directory:
```bash
cd reposcout/extension
```

### Install npm packages:
```bash
npm install
```

### Option A — Build the Chrome Extension bundle (Recommended for Chrome):
```bash
npm run build
```
This compiles the extension into `reposcout/extension/dist/` containing `manifest.json`, `index.html`, `assets/`, and `icons/`.

### Option B — Run Vite Dev Server for interactive UI prototyping in browser:
```bash
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser to inspect the UI with Hot Module Replacement (HMR).

---

## 3. How to Load the Extension in Google Chrome

1. Open **Google Chrome**.
2. In the URL address bar, navigate to:
   ```
   chrome://extensions
   ```
3. Enable **Developer mode** toggle in the top-right corner.
4. Click the **"Load unpacked"** button in the top-left toolbar.
5. Select the built extension directory:
   ```
   <PATH_TO_PROJECT>/reposcout/extension/dist
   ```
6. The **RepoScout - GitHub Discovery** card will appear in your extensions list.
7. Click the **Extensions puzzle piece** icon in Chrome's top-right toolbar and pin **RepoScout**.
8. Click the RepoScout icon to open the popup.

> **Tip:** If you make frontend code changes, run `npm run build` inside `reposcout/extension/`, then click the circular **Reload** icon on the RepoScout card at `chrome://extensions`.

---

## API Contract Reference

### 1. Health Check
`GET /api/health`

**Response:**
```json
{
  "status": "ok",
  "service": "reposcout"
}
```

### 2. Repository Search
`GET /api/search?q={query}`

**Example:**
`GET /api/search?q=I%20want%20a%20beginner-friendly%20RAG%20project%20using%20Python,%20LangChain%20and%20FAISS.`

**Response (HTTP 200 OK):**
```json
{
  "query": "RAG",
  "total_count": 622796,
  "results": [
    {
      "name": "ragflow",
      "full_name": "infiniflow/ragflow",
      "owner": "infiniflow",
      "owner_avatar_url": "https://avatars.githubusercontent.com/u/69962740?v=4",
      "description": "RAGFlow is an agent-native database: a Retrieval-Augmented Generation (RAG) engine that grew into context infrastructure.",
      "url": "https://github.com/infiniflow/ragflow",
      "html_url": "https://github.com/infiniflow/ragflow",
      "clone_url": "https://github.com/infiniflow/ragflow.git",
      "stars": 93652,
      "forks": 8420,
      "language": "Go",
      "topics": ["rag", "deep-learning", "agent", "llm"],
      "updated_at": "2026-11-06T06:00:00Z",
      "created_at": "2023-12-05T08:12:00Z",
      "open_issues": 142,
      "default_branch": "main",
      "match_score": null,
      "github_url": "https://github.com/infiniflow/ragflow",
      "match_percentage": null
    }
  ]
}
```

**Validation Error (HTTP 400 Bad Request):**
```json
{
  "detail": "Search query parameter 'q' must not be empty."
}
```

---

### 3. Repository Architecture & Tech Stack Analysis
`GET /api/repository/analyze?repo={owner}/{name}&refresh={bool}` (or `?owner={owner}&repo={name}`)

**Example:**
`GET /api/repository/analyze?repo=infiniflow/ragflow`

**Response (HTTP 200 OK):**
```json
{
  "repository": "infiniflow/ragflow",
  "technologies": ["Hugging Face", "React", "Docker", "PostgreSQL", "Redis", "Go", "TypeScript"],
  "languages": ["Go", "TypeScript", "C++", "Python"],
  "frameworks": ["React"],
  "libraries": ["Hugging Face", "Docker"],
  "databases": ["PostgreSQL", "Redis"],
  "apis": ["REST API"],
  "architecture_components": ["document loading", "text splitting/chunking", "retrieval", "reranking"],
  "project_type": "Retrieval-Augmented Generation (RAG) System",
  "documentation_quality": "High",
  "activity_status": "Active (Updated recently)",
  "completeness_status": "High (Tests, Docker, and manifests verified)",
  "difficulty": "Advanced",
  "strengths": [
    "Complete end-to-end pipeline implementation (document loading, text splitting/chunking, retrieval)",
    "Containerized deployment support (Dockerfile / Docker Compose detected)",
    "Automated test coverage present in repository",
    "Extensive documentation with clear setup and usage instructions",
    "Strong community adoption (93,655 GitHub stars)"
  ],
  "limitations": [
    "High volume of open issues (1,333 open issues)"
  ],
  "owner": "infiniflow",
  "name": "ragflow",
  "stars": 93655,
  "forks": 11243,
  "html_url": "https://github.com/infiniflow/ragflow",
  "default_branch": "main",
  "total_files_analyzed": 46,
  "detected_dependency_files": ["Dockerfile", "go.mod", "pyproject.toml"]
}
```

---

### 4. Intelligent Ranked Search
`POST /api/search/ranked`

Executes the full pipeline:
`Natural-language query → Query understanding → GitHub search → Repository analysis → Intelligent Ranking → Sorted Results`

**Scoring Model (100% Total):**
- Requirement match: 30%
- Technology match: 20%
- Architecture match: 20%
- Documentation quality: 10%
- Repository activity: 10%
- Popularity: 5%
- Project completeness: 5%

**Request:**
```json
{
  "query": "I want a beginner RAG project using Python and LangChain"
}
```

**Response (HTTP 200 OK):**
```json
{
  "query": "I want a beginner RAG project using Python and LangChain",
  "total_count": 31132,
  "results": [
    {
      "name": "rag-api",
      "full_name": "LibreChat-AI/rag-api",
      "owner": "LibreChat-AI",
      "description": "ID-based RAG FastAPI: Integration with Langchain and PostgreSQL/pgvector",
      "url": "https://github.com/LibreChat-AI/rag-api",
      "stars": 918,
      "forks": 413,
      "language": "Python",
      "topics": ["fastapi", "langchain", "pgvector", "python", "rag"],
      "match_score": 99,
      "score_breakdown": {
        "requirement_match": 30,
        "technology_match": 20,
        "architecture_match": 20,
        "documentation": 10,
        "activity": 10,
        "popularity": 4,
        "completeness": 5
      },
      "matches": [
        "RAG architecture",
        "Python",
        "LangChain"
      ],
      "missing": [],
      "why_it_matches": "Satisfies all 3/3 requested requirements (RAG architecture, Python, LangChain). Features high-quality documentation."
    }
  ]
}
```

---

## Caching & Performance Architecture

RepoScout incorporates a multi-tier caching system and a **Two-Stage Search Pipeline** to minimize expensive GitHub REST API calls and LLM inference while maintaining sub-second query latency.

### 1. Storage Abstraction (`cache_service.py`)
- **`BaseCacheBackend`**: Clean abstract interface (`get`, `set`, `delete`, `clear`, `exists`).
- **`InMemoryCacheBackend`**: Thread-safe in-memory cache with TTL expiration and automatic LRU pruning (default for local development and unit tests).
- **`RedisCacheBackend`**: Production-ready Redis client with native TTL expiration; automatically activates when `REDIS_URL` is set in `.env` and falls back to memory if Redis is unreachable.

### 2. Standardized Cache Keys & TTLs
| Key Pattern | Scope | Default TTL |
| :--- | :--- | :--- |
| `github_search:<query>` | GitHub candidate searches | 600s (10 min) |
| `repository:<owner>:<repo>` | Repository metadata | 1800s (30 min) |
| `analysis:<owner>:<repo>` | Deep architecture & tech analysis | 3600s (1 hour) |
| `readme:<owner>:<repo>` | Raw README documentation | 3600s (1 hour) |
| `tech_detection:<owner>:<repo>` | Extracted frameworks & tools | 3600s (1 hour) |
| `ranking:<query_hash>` | End-to-end ranked search payloads | 600s (10 min) |

### 3. Two-Stage Search Architecture
```
User Search Query
       ↓
Cache Hit Check (ranking:<query_hash>) ──[HIT: ~10ms]──> Instant Response
       ↓ [MISS]
Query Understanding (Fast Path / LLM)
       ↓
Stage 1: GitHub Search (up to 30 candidate repositories)
       ↓
Lightweight In-Memory Filtering (Metadata, Topics, Primary Language, Stars)
       ↓
Select Top 5 Candidates
       ↓
Stage 2: Deep Analysis (README, Tree, Manifests, Architecture)
  ↳ Parallel execution via asyncio.gather with timeout protection
       ↓
Multi-Factor Relevance Scoring across all candidates
       ↓
Sorted Results & Cache Write
```

---

## Testing & Quality Assurance
Run backend test suite:
```bash
cd reposcout/backend
.venv/bin/pytest -v
```
Verifies 24 test suites covering health checks, natural language query understanding, candidate search, RAG architecture detection, repository analysis, scoring breakdown, explainability, sorting order, cache refresh, Redis fallback, TTL expiration, and Two-Stage search constraints.

