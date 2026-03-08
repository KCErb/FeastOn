# Conference Language Study App — Pipeline Specification

## Overview

The pipeline is a batch process that transforms raw Conference talk sources into the structured data layers the study app consumes. It runs offline on the developer's machine (MacBook Pro), separate from the web application. Its output is a set of JSON files (one per talk per language pair) that the backend serves.

The pipeline is **idempotent**: running it again on the same inputs produces the same outputs. It is **resumable**: each stage writes its output to disk, so a failure at Stage 5 doesn't require re-running Stages 1–4.

---

## Pipeline Stages

```
Stage 1: Ingest       → raw text + audio files on disk
Stage 2: Transcribe   → timestamped transcript per language
Stage 3: Diff         → official text ↔ transcript differences
Stage 4: Segment      → paragraph and sentence boundaries per language
Stage 5: Align        → cross-language paragraph + sentence alignment
Stage 6: Map          → semantic unit graph per aligned sentence group
Stage 7: Phonetics    → pinyin and IPA for study language text
Stage 8: Package      → consolidated JSON per talk per language pair
```

---

## Stage 1: Ingest

### Input
- Conference identifier (e.g., `2025-10`)
- Language pair (e.g., `eng`/`ces`)

### Process
1. Fetch the conference index page from `churchofjesuschrist.org/study/general-conference/{year}/{month}?lang={lang}`.
2. Parse the page to extract the list of talks with URLs, titles, and speakers.
3. For each talk, for each language:
   a. Fetch the talk page HTML.
   b. Extract the official text content (strip navigation, headers, footers — just the talk body).
   c. Download the MP3 audio file (the audio player URL is embedded in the page or available via a known URL pattern).
4. Save to disk:
   ```
   data/raw/{conference_id}/{talk_id}/
     metadata.json          # title, speaker, URLs, session
     eng/
       official_text.html   # raw HTML of talk body
       official_text.txt    # cleaned plain text, paragraphs separated by \n\n
       audio.mp3
     ces/
       official_text.html
       official_text.txt
       audio.mp3
   ```

### Output Schema: `metadata.json`
```json
{
  "talk_id": "2025-10-saturday-morning-03",
  "conference_id": "2025-10",
  "session": "Saturday Morning",
  "speaker": "Elder Example",
  "title": {
    "eng": "The Power of Faith",
    "ces": "Síla víry"
  },
  "source_urls": {
    "eng": "https://www.churchofjesuschrist.org/study/general-conference/2025/10/...",
    "ces": "https://www.churchofjesuschrist.org/study/general-conference/2025/10/...?lang=ces"
  },
  "languages_available": ["eng", "ces"]
}
```

### Implementation Notes
- The Church website structure is relatively stable. The talk text lives inside an identifiable content container.
- Audio URLs follow a pattern: they are embedded in the page's HTML or available via the media API.
- Be respectful: add delays between requests, cache aggressively, don't re-download what we already have.
- The `official_text.txt` should preserve paragraph breaks (double newline) but strip all HTML formatting. Keep the text as-is (do not normalize Unicode, do not strip diacritics).

---

## Stage 2: Transcribe

### Input
- Audio file: `data/raw/{conference_id}/{talk_id}/{lang}/audio.mp3`
- Language code

### Process
1. Run WhisperX on the audio file with the appropriate language model.
2. Obtain word-level timestamps via forced alignment (WhisperX's built-in wav2vec2 alignment).
3. Save the transcript.

### Commands (reference)
```python
import whisperx

model = whisperx.load_model("large-v3", device="cpu", compute_type="int8", language=lang)
audio = whisperx.load_audio(audio_path)
result = model.transcribe(audio, batch_size=4)

# Forced alignment for word-level timestamps
align_model, metadata = whisperx.load_align_model(language_code=lang, device="cpu")
result = whisperx.align(result["segments"], align_model, metadata, audio, device="cpu")
```

### Output Schema: `transcript.json`
```json
{
  "talk_id": "2025-10-saturday-morning-03",
  "language": "ces",
  "model": "whisperx-large-v3",
  "segments": [
    {
      "start": 0.0,
      "end": 4.52,
      "text": "Bratři a sestry, dnes bych chtěl promluvit o víře.",
      "words": [
        { "word": "Bratři", "start": 0.0, "end": 0.35, "score": 0.97 },
        { "word": "a", "start": 0.36, "end": 0.40, "score": 0.99 },
        { "word": "sestry,", "start": 0.41, "end": 0.78, "score": 0.95 },
        { "word": "dnes", "start": 0.85, "end": 1.10, "score": 0.93 }
      ]
    }
  ]
}
```

### Output Location
```
data/processed/{conference_id}/{talk_id}/{lang}/transcript.json
```

### Implementation Notes
- WhisperX on MacBook Pro (Apple Silicon): use `device="cpu"` or `device="mps"` if supported. `compute_type="int8"` reduces memory.
- For Chinese: Whisper produces character-level output. Word segmentation happens later (Stage 4).
- For English: the original speaker's audio. Quality is generally excellent.
- For Czech/Chinese: interpreter audio. Quality varies — some background noise, different speaking pace.
- WhisperX alignment models exist for English, Chinese, Czech, Spanish, and many other languages. Check availability at runtime and fall back to whisper-timestamped if needed.

---

## Stage 3: Diff

### Input
- Official text: `data/raw/{conference_id}/{talk_id}/{lang}/official_text.txt`
- Transcript: `data/processed/{conference_id}/{talk_id}/{lang}/transcript.json`

### Process
1. Reconstruct the full transcript text from segments.
2. Split both official text and transcript into paragraphs (by approximate alignment — use a sliding-window approach since the transcript has no paragraph breaks).
3. For each paragraph pair, perform word-level diff.

### Algorithm
```
1. Flatten transcript words into a single text string.
2. Split official text into paragraphs.
3. For each official paragraph:
   a. Find the best matching region in the transcript text using fuzzy matching
      (e.g., SequenceMatcher or a sliding window with character-level alignment).
   b. Once the paragraph region is identified, perform word-level diff
      (difflib.SequenceMatcher on word lists).
   c. Record the diff operations.
```

### Output Schema: `text_diff.json`
```json
{
  "talk_id": "2025-10-saturday-morning-03",
  "language": "ces",
  "paragraphs": [
    {
      "paragraph_index": 0,
      "official_text": "Bratři a sestry, ...",
      "transcript_text": "Drahí bratři a sestry, ...",
      "ops": [
        { "type": "insert", "transcript_words": ["Drahí"] },
        { "type": "equal", "official_words": ["Bratři", "a", "sestry,"], "transcript_words": ["bratři", "a", "sestry,"] },
        { "type": "replace", "official_words": ["mluvit"], "transcript_words": ["hovořit"] }
      ]
    }
  ]
}
```

### Output Location
```
data/processed/{conference_id}/{talk_id}/{lang}/text_diff.json
```

### Implementation Notes
- The diff is case-insensitive for matching purposes but preserves original casing in the output.
- Punctuation differences (comma vs. period, added commas) are common and should be treated as minor / cosmetic differences rather than content changes.
- This stage doesn't need an LLM — it's pure algorithmic text comparison.

---

## Stage 4: Segment

### Input
- Official text per language
- Transcript per language (for Chinese: pre-word-segmentation)

### Process
1. **Paragraph segmentation:** Already done in ingestion (double newline in `official_text.txt`). Assign stable paragraph indices.
2. **Sentence segmentation:** Use an LLM to split each paragraph into sentences with character offsets.
3. **Chinese word segmentation:** For Chinese text, run word segmentation (jieba or LLM-based) to insert word boundaries.

### LLM Prompt for Sentence Segmentation
```
Given the following paragraph in {language}, identify the sentence boundaries.
Return a JSON array of objects with "text" and "start_char" and "end_char" fields.
Each sentence should be a complete thought. Do not split quoted speech across
sentences unless the original clearly does so.

Paragraph:
{paragraph_text}
```

### Output Schema: `segments.json`
```json
{
  "talk_id": "2025-10-saturday-morning-03",
  "language": "ces",
  "paragraphs": [
    {
      "index": 0,
      "text": "Bratři a sestry, dnes bych chtěl promluvit o víře. Víra je základním principem evangelia.",
      "sentences": [
        {
          "index": 0,
          "text": "Bratři a sestry, dnes bych chtěl promluvit o víře.",
          "start_char": 0,
          "end_char": 51
        },
        {
          "index": 1,
          "text": "Víra je základním principem evangelia.",
          "start_char": 52,
          "end_char": 89
        }
      ],
      "word_boundaries": null
    }
  ]
}
```

For Chinese, `word_boundaries` is populated:
```json
{
  "word_boundaries": [
    { "text": "弟兄", "start_char": 0, "end_char": 2 },
    { "text": "姐妹", "start_char": 2, "end_char": 4 },
    { "text": "们", "start_char": 4, "end_char": 5 },
    { "text": "，", "start_char": 5, "end_char": 6 },
    { "text": "今天", "start_char": 6, "end_char": 8 }
  ]
}
```

### Output Location
```
data/processed/{conference_id}/{talk_id}/{lang}/segments.json
```

---

## Stage 5: Align

### Input
- Segments for home language: `data/processed/.../eng/segments.json`
- Segments for study language: `data/processed/.../ces/segments.json`

### Process

#### Step 5a: Paragraph Alignment
Most paragraphs are 1:1 between languages, but not always. Use an LLM to confirm/adjust.

**LLM Prompt:**
```
You are aligning paragraphs between an English Conference talk and its {study_language} translation.

English paragraphs:
{numbered list of English paragraph first sentences / summaries}

{study_language} paragraphs:
{numbered list of study-language paragraph first sentences / summaries}

Return a JSON array of alignment groups. Each group maps one or more English
paragraph indices to one or more {study_language} paragraph indices.
Most will be 1:1. Occasionally translators merge or split paragraphs.

Example output:
[
  { "home": [0], "study": [0] },
  { "home": [1], "study": [1] },
  { "home": [2, 3], "study": [2] }
]
```

#### Step 5b: Sentence Alignment (within each paragraph group)
For each aligned paragraph group, align sentences. This is more likely to be N:M.

**LLM Prompt:**
```
Within the following aligned paragraph group, align the English sentences with
the {study_language} sentences. Sentences may map 1:1, 1:many, many:1, or many:many.

English sentences:
0: "{sentence_0}"
1: "{sentence_1}"
2: "{sentence_2}"

{study_language} sentences:
0: "{sentence_0}"
1: "{sentence_1}"

Return a JSON array of alignment groups:
[
  { "home": [0], "study": [0] },
  { "home": [1, 2], "study": [1] }
]
```

### Output Schema: `alignment.json`
```json
{
  "talk_id": "2025-10-saturday-morning-03",
  "home_language": "eng",
  "study_language": "ces",
  "paragraph_alignment": [
    { "home": [0], "study": [0] },
    { "home": [1], "study": [1] }
  ],
  "sentence_alignment": [
    {
      "paragraph_group_index": 0,
      "groups": [
        { "home": [0], "study": [0] },
        { "home": [1, 2], "study": [1] }
      ]
    }
  ]
}
```

### Output Location
```
data/processed/{conference_id}/{talk_id}/alignment_{home}_{study}.json
```

---

## Stage 6: Map

### Input
- Alignment data: `alignment_{home}_{study}.json`
- Segmented text for both languages

### Process
For each aligned sentence group, ask the LLM to produce a fine-grained semantic mapping.

**This is the most complex and critical LLM call in the entire pipeline.**

**LLM Prompt:**
```
You are a linguistic analyst creating a detailed semantic mapping between an
English sentence and its {study_language} translation from a Church of Jesus
Christ General Conference talk.

English: "{english_sentence(s)}"
{study_language}: "{study_sentence(s)}"

Create a mapping of semantic units. A semantic unit is the smallest piece of
text that carries a discrete meaning — it could be a single word, part of a
word (a morpheme or prefix), a multi-word phrase, or an idiom.

For each meaning expressed in either language, identify the corresponding
text span(s) in both languages. Some meanings exist in one language but not
the other (e.g., articles, particles, implied subjects).

Return a JSON object with two arrays:

"spans": array of text spans, each with:
  - "id": a short unique identifier (e.g., "s1", "s2")
  - "lang": language code
  - "start_char": start character offset in the sentence
  - "end_char": end character offset (exclusive)
  - "text": the actual text of the span
  - "phonetic": pronunciation guide (REQUIRED for Chinese pinyin with tone marks; optional for others)

"links": array of semantic links, each with:
  - "spans": array of span IDs that are linked
  - "type": one of "equivalent", "approximate", "grammatical", "idiomatic", "implicit"
  - "direction": "bidirectional", "home_to_study", or "study_to_home"
  - "annotation": brief explanation (1-2 sentences) of the relationship,
    especially for non-obvious mappings
  - "confidence": 0.0 to 1.0

Rules:
- Every word/morpheme in both sentences should be covered by at least one span.
- Spans may overlap (a word can be in its own span AND part of a phrase span).
- Use "implicit" type for meaning that is grammatically encoded in one language
  but absent/implied in the other (e.g., Czech verb conjugation encoding the subject).
- Use "grammatical" for structural correspondences that aren't meaning equivalences
  (e.g., a Czech case ending corresponding to an English preposition).
- For Chinese: always provide pinyin with tone marks in the "phonetic" field.
- For Czech: provide IPA or a simplified pronunciation guide if the word
  has non-obvious pronunciation (e.g., ř, ě).

Think carefully about each mapping. This data will be used by language learners.
```

### Output Schema: `semantic_map.json`
```json
{
  "talk_id": "2025-10-saturday-morning-03",
  "home_language": "eng",
  "study_language": "ces",
  "sentence_groups": [
    {
      "sentence_alignment_ref": { "paragraph_group": 0, "group_index": 0 },
      "home_text": "Brothers and sisters, today I want to talk about faith.",
      "study_text": "Bratři a sestry, dnes bych chtěl promluvit o víře.",
      "spans": [
        { "id": "e1", "lang": "eng", "start_char": 0, "end_char": 8, "text": "Brothers" },
        { "id": "e2", "lang": "eng", "start_char": 13, "end_char": 20, "text": "sisters" },
        { "id": "c1", "lang": "ces", "start_char": 0, "end_char": 6, "text": "Bratři", "phonetic": "BRA-tři" },
        { "id": "c2", "lang": "ces", "start_char": 9, "end_char": 15, "text": "sestry", "phonetic": "SES-tri" },
        { "id": "e3", "lang": "eng", "start_char": 22, "end_char": 27, "text": "today" },
        { "id": "c3", "lang": "ces", "start_char": 17, "end_char": 21, "text": "dnes" },
        { "id": "e4", "lang": "eng", "start_char": 28, "end_char": 29, "text": "I" },
        { "id": "c4", "lang": "ces", "start_char": 22, "end_char": 26, "text": "bych", "phonetic": "bikh" },
        { "id": "e5", "lang": "eng", "start_char": 30, "end_char": 34, "text": "want" },
        { "id": "c5", "lang": "ces", "start_char": 27, "end_char": 32, "text": "chtěl" },
        { "id": "e6", "lang": "eng", "start_char": 38, "end_char": 42, "text": "talk" },
        { "id": "c6", "lang": "ces", "start_char": 33, "end_char": 43, "text": "promluvit" },
        { "id": "e7", "lang": "eng", "start_char": 43, "end_char": 48, "text": "about" },
        { "id": "c7", "lang": "ces", "start_char": 44, "end_char": 45, "text": "o" },
        { "id": "e8", "lang": "eng", "start_char": 49, "end_char": 54, "text": "faith" },
        { "id": "c8", "lang": "ces", "start_char": 46, "end_char": 50, "text": "víře", "phonetic": "VEE-rzhe" }
      ],
      "links": [
        { "spans": ["e1", "c1"], "type": "equivalent", "direction": "bidirectional",
          "annotation": "Both are vocative plural forms of 'brother'.", "confidence": 0.98 },
        { "spans": ["e2", "c2"], "type": "equivalent", "direction": "bidirectional",
          "annotation": "Vocative plural of 'sister'.", "confidence": 0.98 },
        { "spans": ["e3", "c3"], "type": "equivalent", "direction": "bidirectional",
          "annotation": null, "confidence": 0.99 },
        { "spans": ["e4", "c4"], "type": "grammatical", "direction": "bidirectional",
          "annotation": "'Bych' is the conditional auxiliary 'would' for first person — it implicitly encodes 'I'. The English 'I' maps partly to this word.",
          "confidence": 0.85 },
        { "spans": ["e5", "c5"], "type": "approximate", "direction": "bidirectional",
          "annotation": "'Chtěl' means 'wanted/would like', combining English 'want' with conditional mood from 'bych'.",
          "confidence": 0.90 },
        { "spans": ["e6", "c6"], "type": "equivalent", "direction": "bidirectional",
          "annotation": "'Promluvit' is a perfective form of 'to speak/talk'.",
          "confidence": 0.95 },
        { "spans": ["e7", "c7"], "type": "equivalent", "direction": "bidirectional",
          "annotation": "Preposition 'about' = 'o' (+ locative case).",
          "confidence": 0.97 },
        { "spans": ["e8", "c8"], "type": "equivalent", "direction": "bidirectional",
          "annotation": "'Víře' is the locative case of 'víra' (faith), triggered by the preposition 'o'. The case ending '-ře' corresponds to the preposition 'about' in English.",
          "confidence": 0.95 }
      ]
    }
  ]
}
```

### Output Location
```
data/processed/{conference_id}/{talk_id}/semantic_map_{home}_{study}.json
```

### Implementation Notes
- **This is the most expensive stage.** Each sentence group requires one LLM call. A typical talk has 80–150 sentence groups. Budget accordingly.
- **Prompt iteration is expected.** The prompt above is a starting point. It will need refinement based on output quality. Consider versioning prompts and storing the prompt version in the output.
- **Chinese requires extra care.** Character offsets in Chinese text need to account for the fact that characters are single code points (no multi-byte confusion at the JSON level, but be careful with Python string slicing vs. byte offsets).
- **Parallelism:** Sentence groups within a talk are independent — they can be processed in parallel up to the LLM rate limit.
- **Cost control:** Consider using a smaller/cheaper model for initial paragraph and sentence alignment (Stage 5) and reserving the best model for semantic mapping (Stage 6).

---

## Stage 7: Phonetics

### Input
- Segmented study-language text
- Semantic map spans (which already have phonetics for key words)

### Process
1. **Chinese:** Generate pinyin for the entire study-language text, not just mapped spans. Use `pypinyin` library or LLM.
2. **Other languages:** Phonetic data is generated on-demand by the frontend (via LLM call) or during Stage 6 for key spans. No bulk processing needed.

### Output Schema: `phonetics.json` (Chinese only)
```json
{
  "talk_id": "2025-10-saturday-morning-03",
  "language": "zho",
  "paragraphs": [
    {
      "index": 0,
      "pinyin": [
        { "char": "弟", "pinyin": "dì" },
        { "char": "兄", "pinyin": "xiōng" },
        { "char": "姐", "pinyin": "jiě" },
        { "char": "妹", "pinyin": "mèi" },
        { "char": "们", "pinyin": "men" }
      ]
    }
  ]
}
```

### Output Location
```
data/processed/{conference_id}/{talk_id}/{lang}/phonetics.json
```

### Implementation Notes
- `pypinyin` is fast and accurate for standard Mandarin. It handles most disambiguation. For truly ambiguous cases (polyphones), an LLM pass can correct.
- IPA generation for Czech/Spanish is less critical — Czech spelling is nearly phonetic, Spanish is fully phonetic. Generate on demand via LLM.

---

## Stage 8: Package

### Input
- All processed files for a talk/language pair

### Process
Consolidate all data into a single JSON file per talk per language pair, plus a single JSON per talk per language for the monolingual data. This reduces the number of file reads the backend needs.

### Output Files
```
data/packaged/{conference_id}/{talk_id}/
  talk_eng.json           # monolingual: text, transcript, diff, segments, phonetics
  talk_ces.json           # monolingual: text, transcript, diff, segments, phonetics
  pair_eng_ces.json       # bilingual: alignment, semantic map
  metadata.json           # talk metadata (copied from Stage 1)
```

Also produce an index file for the conference:
```
data/packaged/{conference_id}/index.json
```
```json
{
  "conference_id": "2025-10",
  "talks": [
    {
      "talk_id": "2025-10-saturday-morning-03",
      "speaker": "Elder Example",
      "title": { "eng": "...", "ces": "..." },
      "languages": ["eng", "ces"],
      "language_pairs": [["eng", "ces"]]
    }
  ]
}
```

---

## Pipeline CLI Interface

The pipeline operates on **one talk at a time**. The primary command is:

```bash
# Generate all data for a single talk + language pair
conflang generate <talk-url-or-id> <home-lang> <study-lang>

# Examples:
conflang generate https://www.churchofjesuschrist.org/study/general-conference/2025/10/35example eng ces
conflang generate 2025-10-saturday-morning-03 eng zhs
```

This command is **idempotent**: running it again skips stages whose output files already exist.

### Stage Control

To re-run specific stages (e.g., after improving prompts), use `--from` and `--invalidate`:

```bash
# Re-run from stage 6 onward (stages 6, 7, 8)
# Automatically invalidates stage 6+ outputs and re-generates them
conflang generate <talk-id> eng ces --from 6

# Invalidate a specific stage's output without re-running (useful for debugging)
conflang invalidate <talk-id> eng ces --stage 6

# Re-run only a single stage (does not cascade)
conflang generate <talk-id> eng ces --only 5

# Show current status: which stages have output, which are stale
conflang status <talk-id> eng ces

# Dry run: show what would be processed
conflang generate <talk-id> eng ces --dry-run
```

### Idempotency & Invalidation Rules

Each stage writes a **manifest** alongside its output:
```json
{
  "stage": 6,
  "completed_at": "2026-03-04T12:00:00Z",
  "input_hashes": {
    "segments_eng": "a1b2c3...",
    "segments_ces": "d4e5f6...",
    "alignment": "g7h8i9..."
  },
  "prompt_version": "v2"
}
```

On re-run, the pipeline checks:
1. Does the output file exist? If not → run.
2. Do the `input_hashes` match the current inputs? If not → stale, re-run.
3. Was `--from N` specified and this stage ≥ N? → re-run.

This means if you re-run Stage 2 (transcribe) with a better Whisper model, the pipeline detects that Stage 3's inputs have changed and automatically re-runs Stage 3+.

### Stage Dependencies

```
Stage 1 (Ingest)     → depends on: nothing
Stage 2 (Transcribe) → depends on: Stage 1
Stage 3 (Diff)       → depends on: Stage 1, Stage 2
Stage 4 (Segment)    → depends on: Stage 1
Stage 5 (Align)      → depends on: Stage 4 (both languages)
Stage 6 (Map)        → depends on: Stage 4, Stage 5
Stage 7 (Phonetics)  → depends on: Stage 4
Stage 8 (Package)    → depends on: all previous stages
```

### Future: Batch Processing

Once the single-talk pipeline is solid, a batch command can process an entire conference:
```bash
# Not yet implemented — future convenience wrapper
conflang generate-conference 2025-10 eng ces
```
This would simply iterate over all talks and call the per-talk pipeline for each.

### Environment Configuration

```bash
# .env file
ANTHROPIC_API_KEY=sk-...          # for LLM calls (Stages 4-7)
WHISPER_MODEL=large-v3             # Whisper model size
WHISPER_DEVICE=cpu                 # or "mps" for Apple Silicon
WHISPER_COMPUTE_TYPE=int8          # memory optimization
DATA_DIR=./data                    # root data directory
LLM_MODEL=claude-sonnet-4-5-20250514  # model for alignment/mapping
LLM_MAX_CONCURRENT=3              # parallel LLM requests
```

---

## Error Handling & Recovery

1. **Stage output files are the checkpoints.** If a stage's output file exists for a given talk/language, that stage is skipped unless `--force` is passed.
2. **Partial failures:** If Stage 6 succeeds for 25 out of 30 talks, the next run picks up the remaining 5.
3. **LLM failures:** Retry with exponential backoff (3 attempts). Log failures. The packaging stage (Stage 8) skips talks with incomplete data and reports what's missing.
4. **Validation:** Each stage validates its output against the expected schema before writing. Invalid output triggers a retry (for LLM stages) or an error (for deterministic stages).

---

## Data Size Estimates

For one conference (≈30 talks), one language pair:

| Data | Approximate Size |
|------|-----------------|
| Audio files (both languages) | ~500 MB |
| Raw text | ~1 MB |
| Transcripts + timestamps | ~5 MB |
| Diffs | ~2 MB |
| Segments | ~2 MB |
| Alignment | ~1 MB |
| Semantic maps | ~20 MB (largest — detailed JSON) |
| Phonetics | ~3 MB (Chinese) |
| Packaged total | ~35 MB (excluding audio) |

LLM API costs for one conference, one language pair (rough estimate):
- Stage 4 (segmentation): ~60 calls → ~$1
- Stage 5 (alignment): ~60 calls → ~$2
- Stage 6 (semantic mapping): ~3000 calls (≈100 sentence groups × 30 talks) → ~$30–60
- Total: ~$35–65 per conference per language pair

Stage 6 dominates cost. Consider using a cheaper model (Haiku) for first-pass mapping and Sonnet/Opus for refinement of low-confidence results.
