# GraphTech_V1 — DiagramGPT

> AI-Assisted Technical Diagram Generation & Collaborative Architecture Studio

---

## 🌟 Overview

**GraphTech_V1 (DiagramGPT)** transforms natural language architecture requirements into validated, high-fidelity technical diagrams — Cloud VPC, Microservices, ERD, CI/CD pipelines, Kubernetes clusters, State Machines, and more.

Built as a **monorepo** with a **Vite + React 19** frontend and a **FastAPI + PostgreSQL (pgvector) + Alembic** backend.

The AI pipeline is a **reuse-first architecture**: every prompt is embedded with Voyage AI and searched against previously generated diagrams before invoking an LLM — keeping generation costs near-zero for common requests.

---

## 🚀 Sprint Progress

| Sprint | Status | Focus |
| :--- | :---: | :--- |
| **Sprint 0** — Foundations | ✅ **Done** | FastAPI skeleton, Google OAuth, real Postgres + pgvector, session handling, Alembic migrations |
| **Sprint 1** — Embeddings & Similarity Search | ✅ **Done** | Voyage AI embeddings, pgvector HNSW index, `/api/diagrams/prepare`, spaCy preprocessing, DB seed |
| **Sprint 2** — Groq Generation & Validation | 🔜 Next | Groq structured JSON, Pydantic validation, complexity scoring |
| **Sprint 3** — Renderer Selection | ⬜ Planned | Mermaid, PlantUML, Graphviz, Schemdraw compilers |
| **Sprint 4** — Output Validation & Repair | ⬜ Planned | SVG reconciliation, auto-repair loop |
| **Sprint 5** — Frontend Full Wiring | ⬜ Planned | Real SSE pipeline events, history UI, OAuth persistence |
| **Sprint 6** — Gemini Path & Hardening | ⬜ Planned | Creative image path, rate limiting, circuit breakers |

---

## 🏗️ Architecture Overview

```
User Prompt
     │
     ▼
┌─────────────────────────────────────────┐
│         POST /api/diagrams/prepare      │  ← Sprint 1 ✅
│                                         │
│  1. spaCy preprocessing (optional flag) │
│  2. Voyage AI → 1024-dim embedding      │
│  3. pgvector HNSW cosine search         │
│     → ranked candidates + scores        │
└─────────────┬───────────────────────────┘
              │
     score ≥ threshold?
              │
        ┌─────┴─────┐
        │ Yes       │ No
        ▼           ▼
    Reuse        Groq LLM         ← Sprint 2 🔜
    existing     generation
    diagram      + Pydantic
                 validation
                     │
                     ▼
              Renderer selection  ← Sprint 3
              (Mermaid/PlantUML/
               Graphviz/Schemdraw)
                     │
                     ▼
              Rendered SVG/PNG    ← Sprint 4
              + validation loop
```

---

## 📁 Project Structure

```
GraphTech_V1-main/
├── frontend/                          # Vite + React 19 SPA
│   ├── src/
│   │   ├── api/                       # Backend API client
│   │   ├── components/
│   │   │   ├── Auth/                  # Google OAuth modal
│   │   │   ├── Background/            # Three.js 3D background
│   │   │   ├── Chat/                  # Chat panel + message bubbles
│   │   │   ├── Home/                  # Discover / welcome page
│   │   │   ├── Navbar/                # Top navigation
│   │   │   ├── Sidebar/               # History sidebar
│   │   │   └── Studio/                # Dual-pane diagram studio
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
│
├── backend/                           # FastAPI + SQLAlchemy + pgvector
│   ├── alembic/
│   │   └── versions/
│   │       ├── 0001_initial_schema.py # users + diagram_requests tables
│   │       ├── 0002_add_google_id.py  # google_id column on users
│   │       └── 0003_vector_index.py   # HNSW index on embedding column ✅ Sprint 1
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py                # Google OAuth 2.0 flow
│   │   │   ├── diagrams.py            # /prepare endpoint (Sprint 1) ✅
│   │   │   ├── health.py
│   │   │   ├── me.py
│   │   │   └── router.py
│   │   ├── core/
│   │   │   ├── config.py              # All settings + feature flags
│   │   │   ├── database.py
│   │   │   ├── logging.py
│   │   │   └── security.py            # JWT creation + validation
│   │   ├── models/
│   │   │   ├── users.py
│   │   │   └── diagram_requests.py    # Vector(1024) embedding column
│   │   ├── schemas/
│   │   │   ├── diagrams.py            # PrepareRequest/Response schemas ✅
│   │   │   ├── health.py
│   │   │   └── users.py
│   │   ├── services/
│   │   │   ├── embedding_service.py   # Voyage AI client + pgvector search ✅
│   │   │   ├── preprocessing_service.py # spaCy NLP pipeline ✅
│   │   │   ├── generation_service.py  # Groq LLM (Sprint 2)
│   │   │   ├── rendering_service.py   # Multi-renderer (Sprint 3)
│   │   │   └── validation_service.py  # Structural validation (Sprint 4)
│   │   └── main.py
│   ├── scripts/
│   │   └── seed_diagrams.py           # Seeds 8 real diagrams with Voyage embeddings ✅
│   ├── tests/
│   │   ├── conftest.py                # SQLite test fixtures
│   │   ├── test_auth_flow.py          # Sprint 0: OAuth + session tests
│   │   ├── test_db.py                 # Sprint 0: DB schema tests
│   │   ├── test_embedding_service.py  # Sprint 1: Voyage client unit tests ✅
│   │   ├── test_prepare_endpoint.py   # Sprint 1: /prepare endpoint tests ✅
│   │   └── test_similarity_search.py  # Sprint 1: pgvector integration tests ✅
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
│
├── docker-compose.yml
├── Complete_Implementation_Plan.md
└── README.md
```

---

## 🛠️ Local Development Setup

### Prerequisites

- **Python** 3.11+
- **Node.js** 18+ & npm
- **PostgreSQL** 14+ with the **pgvector** extension installed
- A **Voyage AI** API key — [get one free at dash.voyageai.com](https://dash.voyageai.com/) (200M tokens free, no card needed)
- A **Google OAuth** Client ID & Secret — [Google Cloud Console](https://console.cloud.google.com/)

---

### 1. Clone & configure

```bash
git clone <repo-url>
cd GraphTech_V1-main
```

---

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model (for optional preprocessing)
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
# → Edit .env and fill in DATABASE_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, VOYAGE_API_KEY

# Apply all DB migrations (creates tables + HNSW vector index)
alembic upgrade head

# Seed the database with 8 real diagram examples + Voyage embeddings
python scripts/seed_diagrams.py

# Start the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

| Endpoint | URL |
|---|---|
| Health check | http://localhost:8000/health |
| Swagger UI (API docs) | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

**Frontend:** http://localhost:5173

---

### 4. Docker Compose (alternative — PostgreSQL only)

```bash
docker compose up -d        # starts PostgreSQL with pgvector
# then run backend manually as above
```

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
| :--- | :---: | :--- |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `GOOGLE_CLIENT_ID` | ✅ | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | Google OAuth Client Secret |
| `SESSION_SECRET` | ✅ | Long random JWT signing secret |
| `VOYAGE_API_KEY` | ✅ Sprint 1 | Voyage AI key for embeddings |
| `VOYAGE_MODEL` | — | Default: `voyage-3-large` |
| `VOYAGE_TIMEOUT_SECONDS` | — | Default: `15.0` |
| `VOYAGE_MAX_RETRIES` | — | Default: `3` |
| `SIMILARITY_THRESHOLD` | — | Cosine score cutoff. Default: `0.75` |
| `SIMILARITY_TOP_K` | — | Max candidates returned. Default: `5` |
| `ENABLE_SPACY_PREPROCESSING` | — | Toggle spaCy NLP stage. Default: `false` |
| `GROQ_API_KEY` | 🔜 Sprint 2 | Groq LLM key |
| `GEMINI_API_KEY` | 🔜 Sprint 6 | Gemini creative path key |
| `CORS_ORIGINS` | — | Default: `["http://localhost:5173"]` |
| `HOST` / `PORT` | — | Default: `0.0.0.0` / `8000` |

### Frontend (`frontend/.env`)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | FastAPI backend URL | `http://localhost:8000` |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth Client ID | — |

---

## 🗄️ Database

PostgreSQL with `pgvector` extension.

### Tables

| Table | Purpose |
|---|---|
| `users` | Authenticated users (Google OAuth) — `id`, `email`, `name`, `avatar_url`, `google_id` |
| `diagram_requests` | Diagram history — `prompt`, `embedding` (Vector 1024), `structured_json` (JSONB), `complexity`, `renderer`, `status`, `output_path` |

### Indexes

| Index | Type | Column | Purpose |
|---|---|---|---|
| `diagram_requests_pkey` | B-tree | `id` | Primary key |
| `ix_diagram_requests_user_id` | B-tree | `user_id` | Filter by user |
| `idx_diagram_requests_embedding_hnsw` | **HNSW** | `embedding` | Fast cosine similarity search |

### Alembic migration commands

```bash
alembic upgrade head          # apply all migrations
alembic downgrade -1          # roll back one
alembic revision --autogenerate -m "my change"  # create new migration
```

---

## 🧪 Running Tests

```bash
cd backend

# All unit tests (no Voyage API key needed)
pytest tests/ --ignore=tests/test_similarity_search.py -v

# Full suite including pgvector integration (requires VOYAGE_API_KEY)
pytest tests/ -v
```

**Current test count: 32 passing** (Sprint 0 + Sprint 1)

| File | Tests | Needs API key? |
|---|---|---|
| `test_auth_flow.py` | 6 | No |
| `test_db.py` | 6 | No |
| `test_embedding_service.py` | 9 | No (mocked) |
| `test_prepare_endpoint.py` | 11 | No (mocked) |
| `test_similarity_search.py` | 4 | Yes (auto-skipped if absent) |

---

## 🔌 API Endpoints

### Implemented (Sprint 0 + Sprint 1)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Service health check |
| `GET` | `/api/health` | — | API health check |
| `GET` | `/api/auth/google/login` | — | Redirect to Google consent |
| `GET` | `/api/auth/google/callback` | — | OAuth callback, sets JWT cookie |
| `GET` | `/api/auth/session` | Cookie | Returns current user |
| `POST` | `/api/auth/logout` | Cookie | Clears session cookie |
| `GET` | `/api/me` | Cookie | Current user profile |
| `GET` | `/api/diagrams/` | — | Placeholder (Sprint 5) |
| `POST` | `/api/diagrams/prepare` | — | **Sprint 1** — preprocess → embed → similarity search |

### Coming soon

| Method | Path | Sprint | Description |
|---|---|---|---|
| `POST` | `/api/diagrams/generate` | Sprint 2 | Full generation pipeline |
| `GET` | `/api/diagrams/{id}` | Sprint 5 | Retrieve saved diagram |
| `GET` | `/api/diagrams/history` | Sprint 5 | User diagram history |

---

## 🔑 Getting API Keys

### Voyage AI (Sprint 1 — Embeddings)
1. Go to [dash.voyageai.com](https://dash.voyageai.com/)
2. Sign up with Google or GitHub (one click)
3. Navigate to **API Keys** → **Create new secret key**
4. Copy the key (`pa-xxxxxxxx`) into `backend/.env` as `VOYAGE_API_KEY`
5. **Free tier:** 200 million tokens — no credit card required

### Google OAuth (Sprint 0 — Auth)
1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Create **OAuth 2.0 Client ID** (Web application)
3. Add `http://localhost:8000/api/auth/google/callback` to Authorized Redirect URIs
4. Copy Client ID and Secret into `backend/.env`

---

## 📄 License

MIT
