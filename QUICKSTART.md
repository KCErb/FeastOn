# FeastOn - Quick Start Guide

This guide shows you how to get all three sub-projects running.

**Feast upon the words of Christ — in any language.**

## Prerequisites

- Python 3.11+
- Node.js 18+
- npm

## Setup

### 1. Pipeline CLI

```bash
cd pipeline
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e .
```

Test it:

```bash
feaston --help
feaston generate test-talk eng ces
feaston status test-talk eng ces
```

### 2. Backend API

```bash
cd ../backend
python -m venv venv
source venv/bin/activate
pip install -e .
```

Run the server:

```bash
python run.py
# or
uvicorn conflang_backend.main:app --reload
```

Test it:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "data_dir": "../data"
}
```

### 3. Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Visit http://localhost:5173 in your browser.

You should see:
- Backend connection status (green checkmark)
- Project status dashboard
- "Ready to build features" message

## Architecture Verification

Run all three in separate terminals:

**Terminal 1 (Backend):**

```bash
cd backend
source venv/bin/activate
python run.py
```

**Terminal 2 (Frontend):**

```bash
cd frontend
npm run dev
```

**Terminal 3 (CLI):**

```bash
cd pipeline
source venv/bin/activate
feaston status example-talk eng ces
```

## Provider Interfaces

All external concerns are accessed through provider interfaces:

### Pipeline Providers

- **LLMProvider** — semantic analysis and alignment
- **AudioProvider** — transcription via WhisperX
- **ContentProvider** — fetch talks from churchofjesuschrist.org
- **PersistenceProvider** — save/load pipeline data

See `pipeline/conflang_pipeline/providers/` for implementations.

### Backend Providers

- **PersistenceProvider** — serve processed data (JSON files)
- **IdentityProvider** — user management (stub)
- **LLMProvider** — proxy on-demand word analysis

See `backend/conflang_backend/providers/` for implementations.

### Frontend Providers

- **PersistenceContext** — localStorage for user data
- **IdentityContext** — user preferences

See `frontend/src/providers/` for implementations.

## Next Steps

See CLAUDE.md "What to Build First" section:

1. ✅ **Project skeleton** — Complete
2. → **Pipeline Stage 1 (Ingest)** — Download talk data
3. → **Pipeline Stage 2 (Transcribe)** — WhisperX integration
4. → **Backend data serving** — Load packaged JSON
5. → **Frontend talk viewer** — Display text + audio player
6. → **Audio sync** — Word-level highlighting
7. → **Pipeline Stages 3-7** — Diff, segment, align, map, phonetics
8. → **Word exploration** — Click-to-explore with semantic graph
9. → **Flashcards** — Creation and review

## Project Structure

```
feaston/
├── CLAUDE.md              # Project overview and instructions
├── DESIGN.md              # Architecture and data model
├── QUICKSTART.md          # This file
├── specs/
│   ├── PIPELINE.md       # 8-stage pipeline specification
│   ├── BACKEND.md        # (to be written)
│   └── FRONTEND.md       # (to be written)
│
├── pipeline/             # Python CLI
│   ├── conflang_pipeline/
│   │   ├── providers/    # LLM, Audio, Content, Persistence
│   │   ├── stages/       # 8 pipeline stages (to be implemented)
│   │   ├── manifest.py   # Staleness detection
│   │   └── cli.py        # Click CLI
│   └── pyproject.toml
│
├── backend/              # FastAPI
│   ├── conflang_backend/
│   │   ├── providers/    # Persistence, Identity, LLM
│   │   ├── routes/       # API endpoints
│   │   ├── services/     # Business logic (empty for now)
│   │   ├── models/       # Pydantic schemas (empty for now)
│   │   ├── config.py     # DI setup
│   │   └── main.py       # FastAPI app
│   ├── run.py            # Dev server entry point
│   └── pyproject.toml
│
├── frontend/             # Vite + React + TypeScript
│   ├── src/
│   │   ├── providers/    # React contexts for DI
│   │   ├── components/   # (to be created)
│   │   ├── hooks/        # (to be created)
│   │   ├── lib/          # (to be created)
│   │   ├── types/        # (to be created)
│   │   ├── App.tsx       # Main component
│   │   └── main.tsx      # Entry point
│   ├── tailwind.config.ts
│   ├── vite.config.ts
│   └── package.json
│
└── data/                 # All generated data (gitignored)
    ├── raw/
    ├── processed/
    ├── packaged/
    └── user/
```

## Configuration

Create `.env` files:

**pipeline/.env:**

```bash
ANTHROPIC_API_KEY=sk-...
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cpu
DATA_DIR=../data
LLM_MODEL=claude-sonnet-4-5-20250514
```

**backend/.env:**

```bash
DATA_DIR=../data
ANTHROPIC_API_KEY=sk-...
```

## Testing Strategy

- **Pipeline:** Each stage independently with fixture data
- **Backend:** InMemoryPersistence + MockLLMProvider (no external deps)
- **Frontend:** Component tests for audio sync and diff mapping logic

## Key Design Principles

1. **Dependency Injection** — All providers are interfaces, swappable implementations
2. **Idempotent pipeline** — Re-running produces same output, skips completed stages
3. **Layer separation** — Pipeline → Backend → Frontend are independent
4. **Local-first** — Works entirely offline (except LLM calls)
5. **Language-agnostic core** — Handles English, Czech, Chinese, Spanish, etc.
