# GraphTech_V1 — DiagramGPT

AI-Assisted Technical Diagram Generation & Collaborative Architecture Studio.

---

## 🌟 Overview

**GraphTech_V1 (DiagramGPT)** transforms natural language architecture requirements and reference images into validated, high-fidelity technical architecture diagrams (Cloud VPC, Microservices, ERD, and State Machine Workflows) with interactive editing, real-time pipeline feedback, and dual-section studio workspaces.

The project is structured as a **monorepo** comprising a modern **Vite + React 19 SPA** frontend and a robust **FastAPI + PostgreSQL (pgvector) + Alembic** backend.

---

## 🚀 Key Features & Studio Capabilities

- **Discover Page & Google Authentication:** Sleek Google-style modal sign-in with instant OAuth session preservation and user isolation.
- **Persistent History Sidebar:** Post-authentication sidebar with session history, search, and quick workspace navigation.
- **Unified Dual-Section Studio:** Side-by-side synchronized chat stream and high-resolution diagram canvas with a seamless hairline resizer (Split, Canvas-only, and Chat-only view modes).
- **6-Stage Visual AI Pipeline:** Progress feedback covering:
  1. *Prompt Understanding & Extraction*
  2. *Embedding & Similarity Search (Reuse Candidate)*
  3. *Complexity Classification*
  4. *Routing & Renderer Selection*
  5. *Diagram Generation (DSL / Code)*
  6. *Deterministic Structural & AST Validation*
- **Interactive Diagram Controls:** Pan, zoom, reset, Mermaid/DSL code toggle, copy-to-clipboard, SVG export, and full-screen lightbox image viewer.
- **Multi-Renderer Target Architecture:** Support for Mermaid CLI, PlantUML, Graphviz, and Schemdraw.

---

## 📁 Monorepo Structure

```
GraphTech_V1-main/
├── frontend/                              # Vite + React 19 SPA (Presentation Layer)
│   ├── src/
│   │   ├── api/                           # Backend API client (client.js)
│   │   ├── assets/                        # Static assets and backgrounds
│   │   ├── components/                    # UI Components
│   │   │   ├── Auth/                      # GoogleAuthModal.jsx
│   │   │   ├── Background/                # CleanBackground.jsx, Background3D.jsx (Three.js)
│   │   │   ├── Chat/                      # ChatPanel.jsx, ChatInput.jsx, MessageBubble.jsx
│   │   │   ├── Home/                      # ChatGPTWelcomeHero.jsx (Discover page)
│   │   │   ├── Modal/                     # FullScreenImageViewer.jsx
│   │   │   ├── Navbar/                    # Navbar.jsx
│   │   │   ├── Sidebar/                   # HistorySidebar.jsx
│   │   │   └── Studio/                    # UnifiedStudioTab.jsx, DiagramViewer.jsx, PipelineProgress.jsx
│   │   ├── data/                          # Diagram samples & mock data
│   │   ├── App.jsx                        # Main Application component
│   │   └── main.jsx                       # Entrypoint
│   ├── .env.example                       # Frontend environment template
│   └── package.json
│
├── backend/                               # FastAPI Application & Migrations
│   ├── alembic/                           # Database migration scripts
│   │   ├── versions/                      # Versioned migrations (0001_initial_schema.py)
│   │   ├── env.py                         # Alembic migration environment
│   │   └── script.py.mako
│   ├── app/
│   │   ├── api/                           # Route controllers (health.py, auth.py, diagrams.py, router.py)
│   │   ├── core/                          # Settings (config.py), database.py, security.py, logging.py
│   │   ├── models/                        # SQLAlchemy models (users.py, diagram_requests.py)
│   │   ├── schemas/                       # Pydantic schemas (health.py, users.py, diagrams.py)
│   │   ├── services/                      # Domain business logic stubs:
│   │   │   ├── auth_service.py            # OAuth & user management
│   │   │   ├── embedding_service.py       # Voyage AI embeddings & pgvector search
│   │   │   ├── generation_service.py      # Groq LLM architecture generator
│   │   │   ├── rendering_service.py       # Multi-renderer compiler
│   │   │   └── validation_service.py      # Deterministic structural & AST validation
│   │   └── main.py                        # FastAPI application factory, CORS, and lifecycle
│   ├── alembic.ini                        # Alembic configuration
│   ├── requirements.txt                   # Python dependencies
│   ├── .env.example                       # Backend environment template
│   └── Dockerfile                         # Backend container definition
│
├── docker-compose.yml                     # PostgreSQL 16 (pgvector) + FastAPI backend
├── Complete_Implementation_Plan.md        # Comprehensive architectural specification
└── README.md
```

---

## 🗺️ Agile Sprint Roadmap

The backend and pipeline integration are organized into systematic, testable sprints:

| Sprint | Goal / Focus Area | Key Deliverables |
| :--- | :--- | :--- |
| **Sprint 0** (Completed) | **Foundations & Skeleton** | Monorepo layout, FastAPI skeleton, CORS, SQLAlchemy models with pgvector, Alembic initial migration, Docker Compose, frontend health client. |
| **Sprint 1** | **Ingestion, Embeddings & Similarity Search** | Voyage AI (1024-dim) embedding generation, pgvector top-k cosine similarity query for diagram reuse, optional spaCy text preprocessing. |
| **Sprint 2** | **Groq Generation & Schema Validation** | Groq structured JSON generation, Pydantic validation (no orphan edges / disconnected graphs), independent metric-based complexity scoring. |
| **Sprint 3** | **Renderer Selection & Multi-Compiler** | Diagram type detection (ERD, VPC, Microservice, State Machine), deterministic JSON→DSL compiler (Mermaid, PlantUML, Graphviz, Schemdraw). |
| **Sprint 4** | **Output Validation & Repair Loop** | Rendered SVG/PNG structural reconciliation against input JSON, bounded auto-repair and retry loop (max 2 retries). |
| **Sprint 5** | **Frontend Full Wiring & History** | Replace frontend mock timeouts with real SSE / polling progress events, Google OAuth session persistence, PostgreSQL chat history. |
| **Sprint 6** | **Gemini Creative Path & Hardening** | Dedicated creative image path via Gemini, rate limiting, request deduplication / idempotency, and timeout circuit breakers. |

---

## 🛠️ Getting Started & Local Development

### Prerequisites
- **Node.js** (v18+) & **npm**
- **Python** (v3.11+)
- **Docker** & **Docker Compose** (optional, for containerized PostgreSQL with `pgvector`)

---

### Method 1: Running with Docker Compose

To boot PostgreSQL (with the `pgvector` extension) and the FastAPI backend in containers:

```bash
# Start PostgreSQL (pgvector) and FastAPI backend
docker compose up -d

# Verify backend health
curl http://localhost:8000/health
# Response: {"status": "ok"}
```

Then start the frontend:
```bash
cd frontend
npm install
npm run dev
```

---

### Method 2: Manual Local Setup

#### 1. Backend Setup

```bash
cd backend

# Create and activate Python virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Backend Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

#### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create environment configuration
cp .env.example .env

# Start Vite development server
npm run dev
```

- **Frontend Application:** [http://localhost:5173](http://localhost:5173)

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/graphtech` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `your-google-client-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET`| Google OAuth Client Secret | `your-google-client-secret` |
| `VOYAGE_API_KEY` | Voyage AI API key for embeddings | `your-voyage-api-key` |
| `GROQ_API_KEY` | Groq API key for structured generation | `your-groq-api-key` |
| `GEMINI_API_KEY` | Gemini API key for creative image path | `your-gemini-api-key` |
| `SESSION_SECRET` | Secret key for auth sessions / tokens | `supersecret-session-key` |
| `CORS_ORIGINS` | Permitted frontend origins | `["http://localhost:5173", "http://127.0.0.1:5173"]` |
| `HOST` / `PORT` | FastAPI server binding | `0.0.0.0` / `8000` |

### Frontend (`frontend/.env`)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base URL of the FastAPI backend | `http://localhost:8000` |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth Client ID | `your-google-client-id.apps.googleusercontent.com` |

---

## 🗄️ Database Schema & Alembic

The database uses PostgreSQL with the `pgvector` extension:

- **`users` Table:** Stores authenticated user identities (`id`, `email`, `name`, `avatar_url`, `created_at`).
- **`diagram_requests` Table:** Stores prompts, vector embeddings (`Vector(1024)`), generated structured JSON (`JSONB`), complexity metrics, renderer choices, execution statuses, and output artifact paths.

### Managing Migrations

```bash
cd backend

# Apply migrations
alembic upgrade head

# Rollback one revision
alembic downgrade -1

# Generate a new migration after editing models
alembic revision --autogenerate -m "describe_changes"
```
