# FeastOn Pipeline

The batch processing pipeline for FeastOn - study languages through General Conference talks.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Usage

```bash
# Generate all data for a talk
feaston generate <talk-url-or-id> <home-lang> <study-lang>

# Re-run from stage 6 onward
feaston generate <talk-id> eng ces --from 6

# Show processing status
feaston status <talk-id> eng ces

# Invalidate a stage's output
feaston invalidate <talk-id> eng ces --stage 6
```

## Configuration

Create a `.env` file:

```bash
ANTHROPIC_API_KEY=sk-...
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cpu
DATA_DIR=../data
LLM_MODEL=claude-sonnet-4-5-20250514
```
