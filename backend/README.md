# FeastOn Backend

FastAPI server for FeastOn - study languages through General Conference talks.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Run

```bash
uvicorn main:app --reload
```

Visit http://localhost:8000/docs for API documentation.

## Configuration

Create a `.env` file:

```bash
DATA_DIR=../data
ANTHROPIC_API_KEY=sk-...
```

## API Endpoints

- `GET /health` — Health check
- `GET /api/talks` — List available talks
- `GET /api/talks/{talk_id}` — Get talk data
- `POST /api/analyze-word` — On-demand word analysis (proxies to LLM)
