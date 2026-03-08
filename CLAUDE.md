# CLAUDE.md — FeastOn

## What is this project?

**FeastOn** is a local-first web app for studying languages through General Conference talks from The Church of Jesus Christ of Latter-day Saints.

*Feast upon the words of Christ — in any language.* Each talk exists in parallel across languages (text + audio), and we use Whisper, forced alignment, and LLM analysis to create deeply interlinked study tools.

Read these docs in order for full context:
1. `DESIGN.md` — Architecture, data model, alignment graph, provider interfaces, user flows
2. `specs/PIPELINE.md.md` — Batch processing pipeline (8 stages from raw source to packaged JSON)
3. `specs/BACKEND.md.md` — FastAPI server, provider implementations, API routes
4. `specs/FRONTEND.md.md` — React study UI, three modes, word exploration, flashcards

## Architecture at a Glance

```
feaston CLI (Python)      →  processes one talk at a time → JSON data files
FastAPI backend (Python)  →  serves data + proxies LLM calls
Vite/React frontend (TS)  →  study UI in the browser
```

All three are separate concerns. The pipeline runs independently and produces files the backend serves.

## Tech Stack

- **Frontend:** React + TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend:** Python, FastAPI, Pydantic v2
- **Pipeline:** Python, WhisperX, Anthropic Claude API, jieba (Chinese segmentation)
- **Audio:** HTML5 Audio API (frontend), ffmpeg (backend clip extraction)
- **Storage (now):** JSON files on disk, localStorage in browser
- **Storage (future):** Supabase — the interfaces are ready, just write the adapter

## Core Design Principle: Dependency Injection

Every external concern is accessed through a provider interface. The app injects the right implementation at startup. This is the single most important architectural decision.

**Providers:**
- `PersistenceProvider` — save/load/query/delete by collection+id
- `IdentityProvider` — get current user, manage preferences
- `LLMProvider` — word analysis, alignment, semantic mapping
- `AudioProvider` — transcribe, forced alignment (pipeline only)
- `ContentProvider` — fetch talk text/audio from churchofjesuschrist.org (pipeline only)

**Current implementations:** JSON files, stub identity, Anthropic Claude API (wrapped in CachedLLMProvider).
**Never** import a concrete implementation from core logic. Always go through the interface.

## The Data Model You Must Understand

The heart of the app is 7 layers of derived data from 4 source artifacts (home text, home audio, study text, study audio):

```
Layer 0: Raw sources
Layer 1: Transcripts (Whisper)
Layer 2: Word timestamps (forced alignment)
Layer 3: Text↔transcript diff
Layer 4: Paragraph alignment (cross-language)
Layer 5: Sentence alignment (cross-language, N:M)
Layer 6: Semantic unit mapping — THE CORE — a free-form bipartite graph of TextSpans + SemanticLinks
Layer 7: Per-word lexical analysis (on-demand, cached)
```

**Layer 6 is the key innovation.** It's a graph where spans of text in either language are linked by typed, directional, annotated semantic connections. A span can be a morpheme, word, phrase, or clause. Spans can overlap. Links have types: equivalent, approximate, grammatical, idiomatic, implicit. See DESIGN.md §2.3 for the full data model.

## Pipeline CLI

```bash
feaston generate <talk-id-or-url> <home-lang> <study-lang>
feaston generate <talk-id> eng ces --from 6    # re-run stage 6+
feaston status <talk-id> eng ces               # show stage completion
feaston invalidate <talk-id> eng ces --stage 6 # mark stage stale
```

Idempotent. Each stage writes a manifest with input hashes. Re-runs detect staleness automatically. See specs/PIPELINE.md.md for full stage descriptions, schemas, and LLM prompts.

## Project Layout

```
feaston/
├── CLAUDE.md                 # You are here
├── DESIGN.md                 # Architecture & data model
├── specs/
│   ├── PIPELINE.md          # Pipeline spec
│   ├── BACKEND.md           # Backend spec
│   └── FRONTEND.md          # Frontend spec
│
├── pipeline/                 # Python — the conflang CLI
│   ├── cli.py                # Entry point (click or argparse)
│   ├── stages/
│   │   ├── ingest.py         # Stage 1: download from churchofjesuschrist.org
│   │   ├── transcribe.py     # Stage 2: WhisperX
│   │   ├── diff.py           # Stage 3: official text ↔ transcript
│   │   ├── segment.py        # Stage 4: paragraph + sentence boundaries
│   │   ├── align.py          # Stage 5: cross-language alignment
│   │   ├── map.py            # Stage 6: semantic unit graph (main LLM work)
│   │   ├── phonetics.py      # Stage 7: pinyin, IPA
│   │   └── package.py        # Stage 8: consolidate to serving format
│   ├── manifest.py           # Staleness detection + input hashing
│   └── providers/            # LLM, audio, content providers
│
├── backend/                  # Python FastAPI
│   ├── main.py
│   ├── config.py             # DI setup
│   ├── providers/            # PersistenceProvider, IdentityProvider, LLMProvider
│   ├── services/             # Business logic
│   ├── routes/               # API endpoints
│   └── models/               # Pydantic schemas
│
├── frontend/                 # Vite + React + TypeScript
│   ├── src/
│   │   ├── components/       # React components (see specs/FRONTEND.md §8 for hierarchy)
│   │   ├── hooks/            # TanStack Query hooks, audio sync hook
│   │   ├── providers/        # React context for DI (persistence, identity)
│   │   ├── lib/              # Pure logic: diff mapping, audio sync algorithm
│   │   └── types/            # TypeScript types matching backend Pydantic models
│   ├── index.html
│   ├── tailwind.config.ts
│   └── vite.config.ts
│
└── data/                     # All generated data (gitignored)
    ├── raw/                  # Stage 1 output: downloaded text + audio
    ├── processed/            # Stages 2-7 output: per-stage JSON files
    ├── packaged/             # Stage 8 output: consolidated JSON for backend
    └── user/                 # User data: flashcards, preferences, analysis cache
```

## Language Codes

Use ISO 639-3 consistently everywhere: `eng`, `ces` (Czech), `zho` (Chinese — generic), `zhs` (simplified), `zht` (traditional), `spa` (Spanish). These match the Church website's `?lang=` parameter.

## Language-Specific Gotchas

- **Chinese has no spaces.** Word segmentation (jieba or LLM) must run before any alignment. Character offsets are code points, not bytes.
- **Chinese needs pinyin always.** Pre-compute at Stage 7 for the full text. Use `pypinyin` or LLM.
- **Czech has 7 cases.** A single word form encodes information that takes several English words. The semantic mapping must handle this (link_type: "grammatical" or "implicit").
  - Furthermore, students of cases will benefit if the case-ending were linked to the English preposition (for example) that matches.
- **Czech diacritics matter.** ě š č ř ž ů ú á é í ó ý ď ť ň — never strip or normalize these.
- **The official text ≠ the audio transcript.** This is by design. The diff (Layer 3) surfaces the mismatches, and the UI shows them gracefully.
- There are many many more of these in many languages! These are just a few examples that highlight why the stage 6 map is so flexible. We try to create generic concepts, not over-fit to one language. Many languages may need a phonetic guide to help students, many languages will need to map parts of words to whole words.

## What to Build First

1. **Pipeline Stage 1 (Ingest):** Get one talk's text + audio for eng + one study language downloaded and structured on disk.
2. **Pipeline Stage 2 (Transcribe):** Run WhisperX, get timestamped words.
3. **Backend skeleton:** FastAPI serving the raw talk data at the API endpoints.
4. **Frontend skeleton:** Vite app that loads a talk and displays text with the audio transport bar.
5. **Audio sync:** Wire up word-level highlighting in Read & Listen mode.
6. **Pipeline Stages 3-5:** Diff, segment, align.
7. **Interlinear mode** in the frontend.
8. **Pipeline Stage 6 (Map):** The big one — semantic unit graph.
9. **Word exploration panel** using the semantic map.
10. **Flashcards.**

Each step produces a usable increment. After step 5 you can study by reading and listening with word highlighting. After step 7 your wife can do interlinear listening. Steps 8-10 add the deep learning features.

## Testing Strategy

- **Pipeline stages:** Test each stage independently with a fixture talk (save one talk's intermediate outputs as test fixtures).
- **Backend:** Use `InMemoryPersistence` and `MockLLMProvider` — zero external dependencies.
- **Frontend:** Component tests for the audio sync algorithm and diff mapping logic. These are the most complex pure-logic pieces.

## Things NOT to Do

- Don't build auth. Use the stub identity provider (X-User-Id header).
- Don't pre-extract audio clips. Play time ranges from the full file.
- Don't build spaced repetition. Simple box system (0-4), user picks which box to study.
- Don't scrape the whole conference. One talk at a time.
- Don't try to make the semantic mapping perfect. It has confidence scores. Ship it and iterate prompts.
