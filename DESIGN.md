# Conference Language Study App — Design Document

## 1. Vision Summary

A local-first web application for studying languages through the parallel texts and audio of General Conference addresses from The Church of Jesus Christ of Latter-day Saints. The app leverages the fact that each talk exists as four parallel artifacts — English text, English audio, target-language text, target-language audio — and uses modern speech recognition, forced alignment, and LLM analysis to create a deeply interlinked study experience.

### 1.1 Who It's For

- **Primary:** A multilingual adult studying one or more languages through Conference content they already value.
- **Secondary:** A beginner-level learner who benefits most from interlinear listening (sentence-by-sentence alternation between home and study language audio).
- **Tertiary:** A small community of family/friends who may eventually share the instance.

### 1.2 What It Is Not

- Not a general-purpose language learning app (no gamification, no grammar drills).
- Not a Conference study app (no doctrinal cross-references, no topical indexing).
- Not a translation tool. It reveals the *structure* of existing translations to aid comprehension.

---

## 2. Key Concepts

### 2.1 The Four Source Artifacts

For any talk in any language pair, we start with:

| Artifact | Example |
|----------|---------|
| **Home-language official text** | English text from churchofjesuschrist.org |
| **Home-language audio** | English MP3 of the talk |
| **Study-language official text** | Czech/Chinese text from the same URL with `?lang=ces`/`?lang=zho` |
| **Study-language audio** | Czech/Chinese MP3 of the talk |

The official texts are *not* exact transcripts. They are edited for publication. The audio is a separate performance (original speaker in English; professional interpreter/reader in other languages). This mismatch is a feature, not a bug — we surface it explicitly.

### 2.2 Derived Data Layers

From the four source artifacts, we derive progressively richer layers:

```
Layer 0: Raw sources (text + audio files)
Layer 1: Transcripts — actual word-for-word audio transcription via faster-whisper
Layer 2: Word timestamps — word-level time boundaries via forced alignment (ctc-forced-aligner)
Layer 3: Text↔Transcript diff — marking where official text diverges from spoken audio
Layer 4: Paragraph alignment — 1:1 mapping between home and study language paragraphs
Layer 5: Sentence alignment — N:M mapping of sentences within aligned paragraph groups
Layer 6: Semantic unit mapping — free-form graph linking meaning-equivalent spans across languages
Layer 7: Lexical analysis — per-word dictionary, phonetics (pinyin), register, morphology
```

Layers 0–3 are computed per-language (independently for home and study).  
Layers 4–7 are computed per-language-pair.

### 2.3 The Alignment Graph (Layer 6) — Core Data Model

This is the heart of the app and requires careful design.

**The problem:** Translation is not a word-for-word mapping. A single Czech prefix might correspond to an entire English prepositional phrase. A Chinese four-character idiom might map to a whole English clause. Particles in one language may have no equivalent in the other. Sentence boundaries don't align. Word order differs radically.

**The solution:** A free-form bipartite graph of **text spans** connected by **semantic links**.

```
TextSpan {
  id:          unique identifier
  sentence_id: which aligned sentence group this belongs to
  language:    "eng" | "ces" | "zhs" | etc.
  source:      "official_text" | "transcript"
  start_char:  character offset within the sentence text
  end_char:    character offset (exclusive)
  text:        the actual substring (denormalized for convenience)
  phonetic:    optional pronunciation guide (pinyin, IPA, etc.)
}

SemanticLink {
  id:          unique identifier
  spans:       [span_id, span_id, ...]  // 2 or more spans linked together
  direction:   "bidirectional" | "a_to_b" | "b_to_a"
  link_type:   "equivalent"      // direct meaning match
             | "approximate"     // close but not exact
             | "grammatical"     // structural/syntactic correspondence
             | "idiomatic"       // fixed expression, can't decompose
             | "implicit"        // meaning present in one language, implied in other
  annotation:  optional LLM-generated explanation of the connection
  confidence:  0.0–1.0 (LLM self-assessment)
}
```

**Key properties of this model:**

- A span can be as small as part of a character (for agglutinative morphemes) or as large as an entire clause.
- A span can participate in zero links (a particle with no counterpart) or many links.
- Links can connect more than two spans (e.g., a three-way relationship between an English phrase, a Czech equivalent, and the Chinese equivalent if we ever support 3+ languages simultaneously).
- Links are directional when the mapping is asymmetric.
- Spans reference a *source* (official text vs. transcript) so we can show mappings for what was written and/or what was spoken.

**Spans may overlap.** A word might participate in one link individually and in another link as part of a phrase. Example: in "break a leg," the word "break" might link individually to a study-language word for "break" (the verb), while the full phrase "break a leg" links to the study-language idiom for "good luck." Both are valid and useful.

### 2.4 The Diff Model (Layer 3)

For each language, we align the official text against the transcript to produce a word-level diff:

```
TextDiff {
  paragraph_index: which paragraph
  diff_ops: [
    { type: "equal",   official: "brothers", transcript: "brothers" },
    { type: "replace", official: "and sisters", transcript: "and dear sisters" },
    { type: "insert",  transcript: "uh" },       // filler in audio, not in text
    { type: "delete",  official: "everywhere" },  // in text, not spoken
  ]
}
```

This diff is critical for the reading-while-listening experience: the user sees the official text but the highlight follows the audio. When there's a mismatch, the UI needs to gracefully show what's happening.

---

## 3. Architecture

### 3.1 Guiding Principle: Dependency Injection Everywhere

Every external concern is accessed through a provider interface. The app injects the right implementation at startup. This means:

- **Core logic never imports a concrete implementation.** It imports an interface.
- **Testing uses in-memory stubs.** No database, no network, no filesystem.
- **Early development uses localStorage/JSON files.** Fast iteration, no infrastructure.
- **Production upgrades** (Supabase, SQLite, cloud LLM) are new adapters, not rewrites.

### 3.2 Provider Interfaces

```
┌─────────────────────────────────────────────────────┐
│                    App Core                          │
│  (study UI, flashcards, audio player, exploration)   │
├─────────────────────────────────────────────────────┤
│                 Provider Layer                        │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │ Persistence  │  │   Identity   │  │    LLM     │ │
│  │  Provider    │  │   Provider   │  │  Provider  │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                 │                │         │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌─────┴──────┐ │
│  │ localStorage │  │   Stub       │  │  Claude    │ │
│  │ SQLite       │  │   Supabase   │  │  Ollama    │ │
│  │ Supabase     │  │              │  │  OpenAI    │ │
│  └──────────────┘  └──────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────┘
```

**PersistenceProvider interface:**
```
save(collection: string, id: string, data: any): Promise<void>
load(collection: string, id: string): Promise<any | null>
query(collection: string, filter: FilterCriteria): Promise<any[]>
delete(collection: string, id: string): Promise<void>
```

**IdentityProvider interface:**
```
getCurrentUser(): Promise<User | null>
signIn(credentials: Credentials): Promise<User>
signOut(): Promise<void>
getPreferences(userId: string): Promise<UserPreferences>
savePreferences(userId: string, prefs: UserPreferences): Promise<void>
```

**LLMProvider interface:**
```
analyzeWord(word: string, context: SentenceContext, targetLang: string): Promise<WordAnalysis>
generateSentenceAlignment(homeSentences: string[], studySentences: string[]): Promise<SentenceAlignment>
generateSemanticMapping(homeSentence: string, studySentence: string, langs: LangPair): Promise<SemanticLink[]>
generatePhonetic(text: string, language: string): Promise<string>
```

**TranscriptionProvider interface:**
```
transcribe(audioPath: string, language: string): Promise<Transcript>
```

**AlignmentProvider interface:**
```
align(audioPath: string, text: string, language: string): Promise<Transcript>
```

**ContentProvider interface:**
```
fetchTalkMetadata(conference: string, session: string, language: string): Promise<TalkMetadata>
fetchTalkText(talkUrl: string, language: string): Promise<string>
fetchTalkAudio(talkUrl: string, language: string): Promise<ArrayBuffer>
```

### 3.3 System Topology

```
┌────────────────────────────────────┐
│         Processing Pipeline         │
│  (Python, runs offline/batch)       │
│                                     │
│  faster-whisper → ctc-aligner → LLM │
│  Produces JSON data files           │
└──────────────┬─────────────────────┘
               │ JSON/SQLite
               ▼
┌────────────────────────────────────┐
│          Backend API Server         │
│  (Python or Node, runs locally)     │
│                                     │
│  Serves processed data              │
│  Proxies on-demand LLM calls        │
│  Manages user state                 │
└──────────────┬─────────────────────┘
               │ REST/WebSocket
               ▼
┌────────────────────────────────────┐
│           Frontend SPA              │
│  (React + TypeScript, browser)      │
│                                     │
│  Study UI, audio player,            │
│  word exploration, flashcards       │
└────────────────────────────────────┘
```

The pipeline is a separate offline process. It produces structured data that the backend serves. This separation means:

- The pipeline can run on a different machine (GPU box) if needed.
- The study app works without running the pipeline.
- Pipeline improvements don't require app changes (just re-process data).

### 3.4 Data Flow

```
1. INGEST
   churchofjesuschrist.org → download text + audio → raw files on disk

2. TRANSCRIBE + ALIGN (per language)
   audio file → faster-whisper → transcript.json (what was spoken)
   audio file + official text → ctc-forced-aligner → aligned_official.json (timestamps for official text)

3. DIFF (per language)
   official text + transcript → word-level diff

4. ALIGN (per language pair)
   home paragraphs + study paragraphs → LLM → paragraph alignment
   home sentences + study sentences → LLM → sentence alignment (N:M)

5. MAP (per aligned sentence group)
   home sentence(s) + study sentence(s) → LLM → semantic unit graph

6. ENRICH (per word/span)
   word + context → LLM → phonetics, dictionary, register analysis
   (This can be on-demand rather than pre-computed)

7. STORE
   All layers → JSON files or SQLite → ready for the backend to serve
```

---

## 4. Data Model

### 4.1 Conference & Talk Metadata

```
Conference {
  id:       "2025-10"
  year:     2025
  month:    10  // 4 = April, 10 = October
  sessions: Session[]
}

Session {
  id:       "2025-10-saturday-morning"
  name:     "Saturday Morning Session"
  talks:    Talk[]
}

Talk {
  id:            "2025-10-saturday-morning-03"
  title:         { eng: "...", ces: "...", zho: "..." }
  speaker:       "Elder So-and-So"
  conference_id: "2025-10"
  session_id:    "2025-10-saturday-morning"
  languages:     ["eng", "ces", "zho"]
}
```

### 4.2 Per-Language Talk Data

```
TalkContent {
  talk_id:    "2025-10-saturday-morning-03"
  language:   "ces"

  official_text: {
    paragraphs: [
      {
        index: 0,
        text: "Bratři a sestry, ...",
        sentences: [
          { index: 0, text: "Bratři a sestry, ...", start_char: 0, end_char: 42 },
          { index: 1, text: "Dnes bych ...", start_char: 43, end_char: 89 },
        ]
      }
    ]
  }

  transcript: {
    words: [
      { text: "Bratři", start_time: 0.0, end_time: 0.35, confidence: 0.97 },
      { text: "a", start_time: 0.36, end_time: 0.40, confidence: 0.99 },
      ...
    ]
    paragraphs: [...] // same structure as official_text, derived from transcript
  }

  text_diff: TextDiff[]  // per-paragraph diff between official and transcript
}
```

### 4.3 Cross-Language Alignment Data

```
LanguagePairAlignment {
  talk_id:        "2025-10-saturday-morning-03"
  home_language:   "eng"
  study_language:  "ces"

  paragraph_alignment: [
    { home_paragraphs: [0], study_paragraphs: [0] },
    { home_paragraphs: [1], study_paragraphs: [1] },
    // occasionally: { home_paragraphs: [5, 6], study_paragraphs: [5] }
  ]

  sentence_alignment: [
    {
      paragraph_group_index: 0,
      alignments: [
        { home_sentences: [0], study_sentences: [0] },
        { home_sentences: [1, 2], study_sentences: [1] },  // two English → one Czech
      ]
    }
  ]

  semantic_map: SemanticLink[]   // the full free-form graph (Layer 6)
  text_spans:   TextSpan[]       // all spans referenced by the semantic links
}
```

### 4.4 On-Demand Enrichment (Layer 7)

```
WordAnalysis {
  id:             unique
  text:           "sestry"
  language:       "ces"
  context:        "Bratři a sestry, dnes bych chtěl..."
  talk_id:        "2025-10-saturday-morning-03"

  // From LLM
  phonetic:        "SES-tri"  // IPA or simplified
  lemma:           "sestra"
  part_of_speech:  "noun"
  morphology:      { case: "vocative", number: "plural", gender: "feminine" }
  definition:      "sister (also used as a form of address in church)"
  register:        "formal/religious"
  informal_alt:    "ségra (colloquial)"
  home_equivalent: "sisters"
  related_words:   ["bratr (brother)", "sesterský (sisterly)"]

  // Caching
  cached_at:       timestamp
}
```

### 4.5 Flashcards

```
Flashcard {
  id:          unique
  user_id:     string
  created_at:  timestamp

  front: CardSide
  back:  CardSide

  // Simple box-based review tracking (no complex SRS)
  box:           number  // 0 = new, 1–5 = learned
  last_reviewed: timestamp | null
  next_review:   timestamp | null
}

CardSide {
  // Any combination of these — user chooses what goes where
  text:       string | null          // a word, phrase, or sentence
  audio_ref:  AudioReference | null  // pointer to a time range in a talk's audio
  language:   string
  phonetic:   string | null
  context:    string | null          // surrounding sentence for reference
  image:      string | null          // future: could add images
}

AudioReference {
  talk_id:    string
  language:   string
  start_time: number  // seconds
  end_time:   number  // seconds
}
```

### 4.6 User & Preferences

```
User {
  id:           unique
  display_name: string
  created_at:   timestamp
}

UserPreferences {
  user_id:          string
  home_language:    "eng"
  study_languages:  ["ces", "zho"]   // can study multiple
  active_study_lang: "ces"           // currently selected

  // Study preferences
  playback_speed:       1.0
  interlinear_pause_ms: 500    // pause between language switches
  show_phonetics:       true   // show pinyin/IPA by default
  show_diff_markers:    true   // show transcript↔text differences

  // UI preferences
  font_size:            "medium"
  theme:                "light"
}
```

---

## 5. Key Design Decisions

### 5.1 Pre-computed vs. On-Demand

| Layer | Strategy | Rationale |
|-------|----------|-----------|
| Transcription (L1) | **Pre-computed** | CPU/GPU intensive, deterministic, needs to run once |
| Timestamps (L2) | **Pre-computed** | Same as above |
| Text↔Transcript diff (L3) | **Pre-computed** | Fast to compute, always needed |
| Paragraph alignment (L4) | **Pre-computed** | Cheap LLM call, always needed |
| Sentence alignment (L5) | **Pre-computed** | Moderate LLM call, always needed for interlinear mode |
| Semantic mapping (L6) | **Pre-computed** | Expensive LLM call, but critical for word-click exploration |
| Word analysis (L7) | **On-demand, cached** | Too many words to pre-compute; cache after first request |

### 5.2 Phonetics Strategy

| Language | Approach |
|----------|----------|
| Chinese (zho) | Always generate pinyin with tone marks (e.g., "xiōngdì jiěmèi") — essential for learners |
| Czech (ces) | Generate IPA on demand — spelling is mostly phonetic, less critical |
| Spanish (spa) | Generate IPA on demand — similar to Czech |
| Other | IPA on demand, flag as available in UI |

Pinyin for Chinese should be pre-computed at Layer 6 time since it's nearly always wanted.

### 5.3 Language Codes

Use ISO 639-3 codes consistently: `eng`, `ces`, `zhs`, `spa`, etc. These match the Church website's `?lang=` parameter values.

### 5.4 Sentence Segmentation

Sentence boundary detection is language-dependent and imperfect. The pipeline should:
1. Use the paragraph structure from the official HTML as the top-level segmentation.
2. Use an LLM to split paragraphs into sentences (better than regex for Chinese which lacks spaces, and for edge cases in all languages).
3. Store sentence boundaries as character offsets within the paragraph, so they can be revised without re-processing everything above.

### 5.5 Error Budget for Autonomous Mapping

Since the mapping pipeline is fully autonomous (LLM-generated, no human curation), we must design for imperfection:

- Every SemanticLink has a `confidence` score.
- The UI can optionally dim or flag low-confidence links.
- The user can "correct" a link (which saves a user override, not modifying the original pipeline output).
- Future: user corrections could be fed back to improve prompts.

---

## 6. Language-Specific Considerations

### 6.1 Chinese (Mandarin)

- **No word boundaries in text.** Chinese text has no spaces. The pipeline must perform word segmentation (jieba or LLM-based) before any alignment.
- **Pinyin is essential.** Always store and display tone-marked pinyin.
- **Characters vs. words.** A "word" may be 1–4 characters. Individual characters often have independent meanings. The semantic mapping should support both word-level and character-level spans.
- **Simplified vs. Traditional.** The Church publishes both (`zhs` and `zht`). Design for either; start with simplified.
- **Measure words / classifiers.** These grammatical particles map to nothing in English. The semantic link should use `link_type: "grammatical"` for these.

### 6.2 Czech

- **Rich morphology.** Czech has 7 cases, 3 genders, complex verb conjugation. A single Czech word form may encode information that takes several English words to express. The word analysis (Layer 7) needs to surface morphological decomposition.
- **Prefixed verbs.** Czech extensively uses prefixes to modify verb meaning (jít/přijít/odejít/vejít). The semantic mapping should be able to link a prefix to its English meaning contribution.
- **Word order is flexible.** Czech uses grammatical case instead of word order to mark roles. The semantic mapping must not assume linear correspondence.
- **Diacritics matter.** Ensure proper handling of háčky and čárky (ě, š, č, ř, ž, ů, ú, á, é, í, ó, ý, ď, ť, ň).

### 6.3 Spanish

- **Closest to English.** Sentence structure and word count tend to be similar. Alignment will generally be more straightforward.
- **Verb conjugation encodes subject.** "Hablo" = "I speak" — the semantic mapping needs to link the verb ending to the English pronoun.
- **Formal/informal register.** Tú vs. Usted distinction is relevant for Conference content which uses formal register.

---

## 7. User Flows

### 7.1 Study Mode: Read & Listen

1. User selects a talk and study language.
2. App displays the study-language official text.
3. User presses play. Audio begins in study language.
4. Words highlight in sync with audio (using Layer 2 timestamps).
5. Where the audio diverges from the official text (Layer 3 diff), the UI shows a subtle indicator (e.g., a small icon, a different highlight color, or a tooltip saying "speaker said: 'drahí bratři' / text says: 'bratři'").
6. User can pause, rewind, adjust speed.
7. Optionally: show home-language text in a parallel panel.

### 7.2 Study Mode: Interlinear Listening

1. User selects a talk and study language.
2. App plays one sentence in the study language.
3. Brief configurable pause.
4. App plays the aligned sentence(s) in the home language.
5. Brief configurable pause.
6. Repeat for next sentence pair.
7. User controls: play/pause, skip forward/back one sentence pair, adjust speed, adjust pause duration.
8. Text for both languages shown on screen with current sentence highlighted.

### 7.3 Word Exploration (Click-to-Explore)

1. User clicks/taps any word in the displayed text.
2. App immediately shows (from pre-computed Layer 6):
   - The corresponding word(s)/phrase(s) in the other language, highlighted in the parallel text.
   - The link type and any annotation.
3. App loads (on-demand, cached Layer 7):
   - Dictionary definition, lemma, part of speech.
   - Morphological breakdown (for Czech: case, gender, number; for Chinese: individual character meanings).
   - Phonetic transcription.
   - Register notes and informal alternatives.
   - Related words.
4. User can tap "Add to Flashcard" from this exploration panel to create a card pre-populated with the word, its translation, audio reference, and context sentence.

### 7.4 Flashcard Creation & Review

1. From Word Exploration, user taps "Add to Flashcard."
2. App pre-populates front and back with sensible defaults (e.g., front = study-language word + audio, back = home-language equivalent + definition).
3. User can customize: swap sides, add/remove content, change what's shown.
4. Cards are saved to the user's collection.
5. Review mode: simple sequential or shuffled review. No algorithm — just show the card, flip it, mark "got it" or "missed it."
6. Export to Anki: generate a `.apkg` or `.csv` file with all cards, including audio clips extracted from the talk files.

---

## 8. Technology Stack

| Concern | Choice | Notes |
|---------|--------|-------|
| Frontend | React + TypeScript, Vite, Tailwind CSS, shadcn/ui | TanStack Query for data fetching |
| Backend API | Python FastAPI | WhisperX is Python; keeps pipeline and API in same ecosystem |
| Pipeline | Python CLI (`conflang`) | WhisperX, LLM SDKs, text processing all Python-native |
| Storage (dev) | JSON files + localStorage | Simplest possible start |
| Storage (prod) | SQLite (local) or Supabase (hosted) | Behind PersistenceProvider interface |
| LLM | Anthropic Claude API | Best for nuanced cross-lingual analysis; behind LLMProvider interface |
| Audio transcription | faster-whisper (local, MacBook Pro) | Word-level timestamps, multi-language support |
| Forced alignment | ctc-forced-aligner / MFA | Align known text to audio, 1100+ languages via MMS |
| Audio playback | HTML5 Audio API | Needed for precise time-synced highlighting |
| Diff algorithm | difflib (Python) or diff-match-patch (JS) | Standard word-level diff |
| Chinese word segmentation | jieba (pipeline) or LLM-based | Needed before any Chinese text alignment |

---

## 9. What's Out of Scope (For Now)

- Video playback (audio only).
- More than two languages compared simultaneously.
- Grammar exercises or quizzes.
- Social features (sharing, leaderboards).
- Mobile native app (web-only, but responsive).
- Automated spaced repetition algorithms (simple box system instead).
- Real-time transcription or live conference streaming.
- Handling talks before ~2000 (audio availability varies).

---

## 10. Open Questions for Implementation: Answered by architect

1. **Pipeline CLI (`conflang`):** Simple idempotent CLI. `conflang generate <talk-id> eng ces`. Supports `--from N` to re-run from a stage, `--only N` for a single stage, and automatic staleness detection via input hashes.
2. **LLM prompt design for semantic mapping:** This is the highest-risk area. The prompts for generating Layer 6 mappings need extensive iteration. The spec should define the input/output contract; the prompts themselves will evolve.
3. **Audio clip extraction for flashcards:** ffmpeg extracts time-range clips on demand at export time. No pre-extraction — we don't know what segments are commonly needed yet.
4. **Cache invalidation:** When the pipeline is re-run (improved prompts, new Whisper model), how do we handle previously cached Layer 7 analyses and user-created flashcards that reference old span IDs? Suggest: stable ID generation based on content hashes.
