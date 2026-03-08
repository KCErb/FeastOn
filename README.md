# FeastOn

A local-first web app for studying languages through General Conference talks from The Church of Jesus Christ of Latter-day Saints.

**Feast upon the words of Christ** — in any language.

## Project Structure

- **pipeline/** — Python CLI (`conflang`) for processing talks
- **backend/** — FastAPI server serving processed data
- **frontend/** — React + TypeScript study UI
- **data/** — All generated data (gitignored)
- **specs/** — Detailed specifications

## Quick Start

### Pipeline CLI

```bash
cd pipeline
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e .
feaston --help
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -e .
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Documentation

Read these in order for full context:

1. `DESIGN.md` — Architecture, data model, provider interfaces
2. `specs/PIPELINE.md` — 8-stage processing pipeline
3. `specs/BACKEND.md` — FastAPI server (if exists)
4. `specs/FRONTEND.md` — React study UI (if exists)
