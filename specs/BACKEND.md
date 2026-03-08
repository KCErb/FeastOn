# Conference Language Study App — Backend Specification

## Overview

A Python (FastAPI) server that runs locally on the developer's machine. It serves pre-processed talk data to the frontend, proxies on-demand LLM calls, manages user state, and provides audio clip extraction. All external dependencies are accessed through provider interfaces.

---

## 1. Server Architecture

```
┌──────────────────────────────────────────────────────┐
│                    FastAPI Server                      │
│                                                        │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────────┐ │
│  │  Routes   │  │  Routes   │  │      Routes         │ │
│  │ /api/talks│  │/api/users │  │  /api/analyze       │ │
│  └─────┬─────┘  └─────┬─────┘  └──────────┬──────────┘ │
│        │              │                    │            │
│  ┌─────▼──────────────▼────────────────────▼──────────┐ │
│  │                 Service Layer                       │ │
│  │  TalkService  UserService  AnalysisService          │ │
│  │  AudioService FlashcardService                      │ │
│  └─────┬──────────────┬────────────────────┬──────────┘ │
│        │              │                    │            │
│  ┌─────▼──────┐ ┌─────▼──────┐  ┌─────────▼──────────┐ │
│  │Persistence │ │  Identity  │  │    LLM Provider    │ │
│  │ Provider   │ │  Provider  │  │                    │ │
│  └────────────┘ └────────────┘  └────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

---

## 2. Provider Interfaces (Python)

These are abstract base classes. Each has at least two implementations: a stub for development and a real one for production.

### 2.1 PersistenceProvider

```python
from abc import ABC, abstractmethod
from typing import Any, Optional

class PersistenceProvider(ABC):
    """Stores and retrieves structured data by collection and ID."""

    @abstractmethod
    async def save(self, collection: str, id: str, data: dict) -> None: ...

    @abstractmethod
    async def load(self, collection: str, id: str) -> Optional[dict]: ...

    @abstractmethod
    async def query(self, collection: str, filters: dict) -> list[dict]: ...

    @abstractmethod
    async def delete(self, collection: str, id: str) -> None: ...

    @abstractmethod
    async def list_ids(self, collection: str) -> list[str]: ...
```

**Implementations:**

| Implementation | Storage | When to use |
|---|---|---|
| `JsonFilePersistence` | JSON files on disk in `data/user/` | Default for local dev |
| `SqlitePersistence` | SQLite database | When query performance matters |
| `SupabasePersistence` | Supabase (Postgres) | Future hosted deployment |

The `JsonFilePersistence` stores data as:
```
data/user/{collection}/{id}.json
```

### 2.2 IdentityProvider

```python
class IdentityProvider(ABC):
    """Manages user identity and authentication."""

    @abstractmethod
    async def get_current_user(self, request: Request) -> Optional[User]: ...

    @abstractmethod
    async def create_user(self, display_name: str) -> User: ...

    @abstractmethod
    async def get_preferences(self, user_id: str) -> UserPreferences: ...

    @abstractmethod
    async def save_preferences(self, user_id: str, prefs: UserPreferences) -> None: ...
```

**Implementations:**

| Implementation | Auth mechanism | When to use |
|---|---|---|
| `StubIdentityProvider` | No auth; single hardcoded user or user selected by header | Local dev |
| `MultiUserStubProvider` | User selected by `X-User-Id` header; no password | Family use |
| `SupabaseIdentityProvider` | Supabase Auth (email/password, OAuth) | Future hosted |

The `StubIdentityProvider` returns a default user for all requests:
```python
class StubIdentityProvider(IdentityProvider):
    async def get_current_user(self, request):
        user_id = request.headers.get("X-User-Id", "default-user")
        return User(id=user_id, display_name="Student")
```

### 2.3 LLMProvider

```python
class LLMProvider(ABC):
    """Interfaces with a language model for text analysis."""

    @abstractmethod
    async def analyze_word(
        self, word: str, context: str, language: str, home_language: str
    ) -> WordAnalysis: ...

    @abstractmethod
    async def segment_sentences(
        self, paragraph: str, language: str
    ) -> list[SentenceBoundary]: ...

    @abstractmethod
    async def align_paragraphs(
        self, home_paragraphs: list[str], study_paragraphs: list[str],
        home_lang: str, study_lang: str
    ) -> list[AlignmentGroup]: ...

    @abstractmethod
    async def align_sentences(
        self, home_sentences: list[str], study_sentences: list[str],
        home_lang: str, study_lang: str
    ) -> list[AlignmentGroup]: ...

    @abstractmethod
    async def generate_semantic_map(
        self, home_text: str, study_text: str,
        home_lang: str, study_lang: str
    ) -> SemanticMapResult: ...
```

**Implementations:**

| Implementation | Backend | When to use |
|---|---|---|
| `AnthropicLLMProvider` | Claude API (Sonnet/Opus) | Default — best quality |
| `OllamaLLMProvider` | Local Ollama instance | Offline / cost-sensitive |
| `CachedLLMProvider` | Wraps any other provider; checks cache first | Always use as wrapper |

The `CachedLLMProvider` is a decorator:
```python
class CachedLLMProvider(LLMProvider):
    def __init__(self, inner: LLMProvider, cache: PersistenceProvider):
        self.inner = inner
        self.cache = cache

    async def analyze_word(self, word, context, language, home_language):
        cache_key = hashlib.sha256(f"{word}:{context}:{language}".encode()).hexdigest()[:16]
        cached = await self.cache.load("word_analysis_cache", cache_key)
        if cached:
            return WordAnalysis(**cached)
        result = await self.inner.analyze_word(word, context, language, home_language)
        await self.cache.save("word_analysis_cache", cache_key, result.dict())
        return result
```

---

## 3. Data Models (Pydantic)

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ─── Talk Data ───

class Talk(BaseModel):
    id: str
    conference_id: str
    session: str
    speaker: str
    title: dict[str, str]        # lang_code → title
    languages: list[str]

class TimestampedWord(BaseModel):
    word: str
    start: float
    end: float
    score: float

class Sentence(BaseModel):
    index: int
    text: str
    start_char: int
    end_char: int

class Paragraph(BaseModel):
    index: int
    text: str
    sentences: list[Sentence]
    word_boundaries: Optional[list[dict]] = None  # Chinese only

class DiffOp(BaseModel):
    type: str  # "equal", "insert", "delete", "replace"
    official_words: Optional[list[str]] = None
    transcript_words: Optional[list[str]] = None

class ParagraphDiff(BaseModel):
    paragraph_index: int
    official_text: str
    transcript_text: str
    ops: list[DiffOp]

class TalkContent(BaseModel):
    talk_id: str
    language: str
    paragraphs: list[Paragraph]
    transcript_words: list[TimestampedWord]
    text_diff: list[ParagraphDiff]
    pinyin: Optional[list[dict]] = None  # Chinese only

# ─── Alignment ───

class AlignmentGroup(BaseModel):
    home: list[int]
    study: list[int]

class SentenceAlignmentBlock(BaseModel):
    paragraph_group_index: int
    groups: list[AlignmentGroup]

class LanguagePairAlignment(BaseModel):
    talk_id: str
    home_language: str
    study_language: str
    paragraph_alignment: list[AlignmentGroup]
    sentence_alignment: list[SentenceAlignmentBlock]

# ─── Semantic Map ───

class TextSpan(BaseModel):
    id: str
    lang: str
    start_char: int
    end_char: int
    text: str
    phonetic: Optional[str] = None

class SemanticLink(BaseModel):
    spans: list[str]
    type: str  # "equivalent", "approximate", "grammatical", "idiomatic", "implicit"
    direction: str  # "bidirectional", "home_to_study", "study_to_home"
    annotation: Optional[str] = None
    confidence: float

class SentenceGroupMap(BaseModel):
    sentence_alignment_ref: dict  # { paragraph_group, group_index }
    home_text: str
    study_text: str
    spans: list[TextSpan]
    links: list[SemanticLink]

class SemanticMap(BaseModel):
    talk_id: str
    home_language: str
    study_language: str
    sentence_groups: list[SentenceGroupMap]

# ─── Word Analysis (on-demand) ───

class WordAnalysis(BaseModel):
    text: str
    language: str
    phonetic: Optional[str] = None
    lemma: Optional[str] = None
    part_of_speech: Optional[str] = None
    morphology: Optional[dict] = None
    definition: Optional[str] = None
    register: Optional[str] = None
    informal_alternatives: Optional[list[str]] = None
    home_equivalent: Optional[str] = None
    related_words: Optional[list[str]] = None
    cached_at: Optional[datetime] = None

# ─── Flashcards ───

class AudioReference(BaseModel):
    talk_id: str
    language: str
    start_time: float
    end_time: float

class CardSide(BaseModel):
    text: Optional[str] = None
    audio_ref: Optional[AudioReference] = None
    language: str
    phonetic: Optional[str] = None
    context: Optional[str] = None

class Flashcard(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    front: CardSide
    back: CardSide
    box: int = 0
    last_reviewed: Optional[datetime] = None

# ─── User ───

class User(BaseModel):
    id: str
    display_name: str

class UserPreferences(BaseModel):
    home_language: str = "eng"
    study_languages: list[str] = ["ces"]
    active_study_language: str = "ces"
    playback_speed: float = 1.0
    interlinear_pause_ms: int = 500
    show_phonetics: bool = True
    show_diff_markers: bool = True
    font_size: str = "medium"
    theme: str = "light"
```

---

## 4. API Routes

### 4.1 Conference & Talk Browsing

```python
@app.get("/api/conferences")
async def list_conferences() -> list[ConferenceSummary]:
    """List all available conferences with talk counts."""

@app.get("/api/conferences/{conference_id}")
async def get_conference(conference_id: str) -> ConferenceDetail:
    """Get full conference details including sessions and talk list."""
```

**Implementation:** Read from `data/packaged/{conference_id}/index.json`.

### 4.2 Talk Data

```python
@app.get("/api/talks/{talk_id}/content/{language}")
async def get_talk_content(talk_id: str, language: str) -> TalkContent:
    """Get monolingual talk data: text, transcript, diff, segments, phonetics."""

@app.get("/api/talks/{talk_id}/alignment/{home_lang}/{study_lang}")
async def get_alignment(talk_id: str, home_lang: str, study_lang: str) -> LanguagePairAlignment:
    """Get cross-language paragraph and sentence alignment."""

@app.get("/api/talks/{talk_id}/semantic-map/{home_lang}/{study_lang}")
async def get_semantic_map(talk_id: str, home_lang: str, study_lang: str) -> SemanticMap:
    """Get the full semantic mapping graph for all sentence groups."""
```

**Implementation:** Read from `data/packaged/{conference_id}/{talk_id}/` files.
Parse the `talk_id` to derive the conference_id (format: `{conference_id}-{session}-{number}`).

### 4.3 Audio

```python
@app.get("/api/talks/{talk_id}/audio/{language}")
async def stream_audio(talk_id: str, language: str) -> StreamingResponse:
    """Stream the full talk audio file."""

@app.get("/api/talks/{talk_id}/audio/{language}/clip")
async def get_audio_clip(
    talk_id: str, language: str, start: float, end: float
) -> StreamingResponse:
    """Extract and return an audio clip between start and end times (seconds)."""
```

**Audio clip extraction** uses ffmpeg:
```python
import subprocess
import tempfile

async def extract_clip(audio_path: str, start: float, end: float) -> bytes:
    duration = end - start
    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(start),
            "-t", str(duration),
            "-c:a", "libmp3lame",
            "-q:a", "4",
            tmp.name
        ], capture_output=True, check=True)
        return tmp.read()
```

Note: For simple playback in the frontend, the clip endpoint is not needed — the frontend plays time ranges from the full audio. The clip endpoint is for flashcard audio export.

### 4.4 Word Analysis (On-Demand)

```python
@app.post("/api/analyze/word")
async def analyze_word(request: WordAnalysisRequest) -> WordAnalysis:
    """
    Get detailed analysis of a word in context.
    Checks cache first, then calls LLM if not cached.
    """
```

**Request body:**
```json
{
  "word": "víře",
  "context_sentence": "Bratři a sestry, dnes bych chtěl promluvit o víře.",
  "language": "ces",
  "home_language": "eng",
  "talk_id": "2025-10-saturday-morning-03"
}
```

### 4.5 Flashcards

```python
@app.get("/api/users/{user_id}/flashcards")
async def list_flashcards(
    user_id: str, lang: str = None, conference: str = None, box: int = None
) -> list[Flashcard]:
    """List user's flashcards with optional filters."""

@app.post("/api/users/{user_id}/flashcards")
async def create_flashcard(user_id: str, card: FlashcardCreate) -> Flashcard:
    """Create a new flashcard."""

@app.put("/api/users/{user_id}/flashcards/{card_id}")
async def update_flashcard(user_id: str, card_id: str, updates: FlashcardUpdate) -> Flashcard:
    """Update a flashcard (edit content or move box)."""

@app.delete("/api/users/{user_id}/flashcards/{card_id}")
async def delete_flashcard(user_id: str, card_id: str) -> None:
    """Delete a flashcard."""

@app.post("/api/users/{user_id}/flashcards/{card_id}/review")
async def review_flashcard(user_id: str, card_id: str, result: ReviewResult) -> Flashcard:
    """Record a review result (got_it or missed) and update the card's box."""
```

**Review logic:**
```python
async def review_flashcard(user_id, card_id, result):
    card = await persistence.load("flashcards", card_id)
    if result.result == "got_it":
        card["box"] = min(card["box"] + 1, 4)
    elif result.result == "missed":
        card["box"] = max(1, card["box"])  # back to box 1, not 0
    card["last_reviewed"] = datetime.utcnow().isoformat()
    await persistence.save("flashcards", card_id, card)
    return card
```

### 4.6 Anki Export

```python
@app.get("/api/users/{user_id}/flashcards/export")
async def export_flashcards(
    user_id: str, format: str = "anki_csv"
) -> StreamingResponse:
    """
    Export flashcards as Anki-compatible CSV + audio clips in a ZIP.
    """
```

**Export process:**
1. Retrieve all flashcards for the user.
2. For each card with an `audio_ref`, extract the audio clip via ffmpeg.
3. Generate a TSV file with columns: front, back, audio_file, tags.
4. Bundle the TSV + audio clips into a ZIP.
5. Return the ZIP as a download.

### 4.7 User & Preferences

```python
@app.get("/api/users/current")
async def get_current_user(request: Request) -> User:
    """Get the current user (determined by IdentityProvider)."""

@app.get("/api/users/current/preferences")
async def get_preferences(request: Request) -> UserPreferences:
    """Get the current user's preferences."""

@app.put("/api/users/current/preferences")
async def update_preferences(request: Request, prefs: UserPreferences) -> UserPreferences:
    """Update the current user's preferences."""
```

---

## 5. Dependency Injection Setup

```python
# config.py
from enum import Enum

class Environment(Enum):
    DEV = "dev"
    TEST = "test"
    PROD = "prod"

def create_providers(env: Environment) -> dict:
    if env == Environment.TEST:
        return {
            "persistence": InMemoryPersistence(),
            "identity": StubIdentityProvider(),
            "llm": MockLLMProvider(),
        }
    elif env == Environment.DEV:
        persistence = JsonFilePersistence(base_dir="./data/user")
        return {
            "persistence": persistence,
            "identity": MultiUserStubProvider(persistence),
            "llm": CachedLLMProvider(
                inner=AnthropicLLMProvider(model="claude-sonnet-4-5-20250514"),
                cache=persistence,
            ),
        }
    elif env == Environment.PROD:
        persistence = SupabasePersistence(url=..., key=...)
        return {
            "persistence": persistence,
            "identity": SupabaseIdentityProvider(url=..., key=...),
            "llm": CachedLLMProvider(
                inner=AnthropicLLMProvider(model="claude-sonnet-4-5-20250514"),
                cache=persistence,
            ),
        }

# main.py
from fastapi import FastAPI, Depends

app = FastAPI()
providers = create_providers(Environment.DEV)

def get_persistence() -> PersistenceProvider:
    return providers["persistence"]

def get_identity() -> IdentityProvider:
    return providers["identity"]

def get_llm() -> LLMProvider:
    return providers["llm"]

# Routes use dependency injection
@app.post("/api/analyze/word")
async def analyze_word(
    request: WordAnalysisRequest,
    llm: LLMProvider = Depends(get_llm),
):
    return await llm.analyze_word(
        request.word, request.context_sentence,
        request.language, request.home_language
    )
```

---

## 6. File Layout

```
backend/
├── main.py                    # FastAPI app entry point
├── config.py                  # Environment + provider setup
├── requirements.txt
│
├── providers/
│   ├── __init__.py
│   ├── persistence.py         # ABC + JsonFile + InMemory implementations
│   ├── identity.py            # ABC + Stub + MultiUserStub implementations
│   └── llm.py                 # ABC + Anthropic + Cached implementations
│
├── services/
│   ├── __init__.py
│   ├── talk_service.py        # Talk data loading and serving
│   ├── audio_service.py       # Audio streaming and clip extraction
│   ├── analysis_service.py    # On-demand word analysis orchestration
│   ├── flashcard_service.py   # Flashcard CRUD and review logic
│   └── export_service.py      # Anki export
│
├── routes/
│   ├── __init__.py
│   ├── conferences.py         # /api/conferences/*
│   ├── talks.py               # /api/talks/*
│   ├── analysis.py            # /api/analyze/*
│   ├── flashcards.py          # /api/users/*/flashcards/*
│   └── users.py               # /api/users/*
│
├── models/
│   ├── __init__.py
│   └── schemas.py             # All Pydantic models
│
└── tests/
    ├── test_talk_service.py
    ├── test_flashcard_service.py
    └── conftest.py            # Fixtures with InMemory providers
```

---

## 7. Startup & CORS

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Conference Language Study")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve audio files directly
app.mount("/audio", StaticFiles(directory="data/raw"), name="audio")

# Include route modules
from routes import conferences, talks, analysis, flashcards, users
app.include_router(conferences.router, prefix="/api")
app.include_router(talks.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(flashcards.router, prefix="/api")
app.include_router(users.router, prefix="/api")
```

**Run locally:**
```bash
cd backend
pip install fastapi uvicorn anthropic pydantic
uvicorn main:app --reload --port 8000
```

---

## 8. Dependencies

```
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
anthropic>=0.40.0      # for AnthropicLLMProvider
python-multipart       # for file uploads if needed
aiofiles               # for async file serving
```

Optional (for future provider implementations):
```
supabase               # for SupabasePersistence
aiosqlite              # for SqlitePersistence
```

System dependencies:
```
ffmpeg                 # for audio clip extraction (must be on PATH)
```
