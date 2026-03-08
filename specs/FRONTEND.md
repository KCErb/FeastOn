# Conference Language Study App — Frontend Specification

## Overview

A React + TypeScript single-page application built with Vite, styled with Tailwind CSS and shadcn/ui components, using TanStack Query for data fetching. Served locally. The frontend consumes pre-processed data from the backend API and provides three primary study modes, a word exploration panel, and a flashcard system. It communicates with the backend via REST API for data retrieval and proxied LLM calls.

---

## 1. Application Shell

### 1.1 Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo/Title]          [Talk Selector ▼]    [User ▼] [⚙]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    Main Content Area                         │
│              (varies by active mode)                         │
│                                                             │
│                                                             │
│                                                             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [▶ Play] [⏪] [⏩] [1.0x ▼] ══════════●══════ 3:42/12:15  │
│                                                             │
│  Mode: [📖 Read & Listen] [🔀 Interlinear] [📝 Cards]      │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Global State

The app maintains the following top-level state:

```typescript
interface AppState {
  // What we're studying
  currentTalk: Talk | null;
  homeLanguage: LanguageCode;        // e.g., "eng"
  studyLanguage: LanguageCode;       // e.g., "ces"

  // Loaded data for current talk
  talkData: {
    homeContent: TalkContent | null;
    studyContent: TalkContent | null;
    alignment: LanguagePairAlignment | null;
    semanticMap: SemanticMap | null;
  };

  // Playback
  playbackState: PlaybackState;

  // UI
  activeMode: "read" | "interlinear" | "cards";
  explorationPanel: ExplorationState | null;  // null = closed

  // User
  user: User;
  preferences: UserPreferences;
}
```

### 1.3 Talk Selector

A dropdown/modal that lets the user browse available conferences and talks:

```
Conference: [October 2025 ▼]
Session:    [Saturday Morning ▼]

Talks:
  ○ Opening Remarks — President Nelson
  ● The Power of Faith — Elder Example    ← selected
  ○ Come Follow Me — Sister Example
  ○ ...
```

Shows only talks that have been fully processed for the user's current language pair.

---

## 2. Mode: Read & Listen

The primary study mode. User reads the study-language text while audio plays, with synchronized word highlighting.

### 2.1 Layout

```
┌─────────────────────────────────────┬──────────────────────────┐
│                                     │                          │
│   Study Language Text               │   Home Language Text     │
│   (primary, larger)                 │   (reference, smaller)   │
│                                     │                          │
│   Bratři a [sestry], dnes bych      │   Brothers and sisters,  │
│   chtěl promluvit o víře.           │   today I want to talk   │
│                                     │   about faith.           │
│   Víra je základním principem       │                          │
│   evangelia Ježíše Krista.          │   Faith is a fundamental │
│                                     │   principle of the       │
│                                     │   gospel of Jesus Christ.│
│                                     │                          │
└─────────────────────────────────────┴──────────────────────────┘
```

The home-language panel is collapsible (toggle in header). Default: shown for beginners, hidden for advanced.

### 2.2 Word Highlighting

As audio plays, the currently spoken word is highlighted in the study-language text panel:

- **Current word:** Bold + background highlight color (e.g., light yellow).
- **Current sentence:** Subtle background tint on the entire sentence.
- **Auto-scroll:** The view auto-scrolls to keep the current sentence visible with some look-ahead (next 2-3 sentences visible below).

**Mapping words to text positions:** The transcript (Layer 2) provides time-stamped words. The diff (Layer 3) maps transcript words to official text words. The highlighting logic is:

```
1. Audio time → find current word in transcript (binary search on timestamps)
2. Current transcript word → find corresponding official text word via diff mapping
3. Highlight that word in the rendered text
```

### 2.3 Diff Indicators

When the audio diverges from the official text:

- **Substitution:** The official text word gets a dotted underline. Hovering shows a tooltip: "Speaker said: 'hovořit'" (with the transcript word).
- **Insertion (audio has extra words):** A small ⟨+⟩ icon appears between words in the text where the speaker inserted extra words. Hovering shows what was said.
- **Deletion (text has words not spoken):** The skipped word(s) get a faint strikethrough or are dimmed. Hovering confirms "Not spoken in audio."

These indicators are toggleable via user preferences.

### 2.4 Phonetics Display

When `show_phonetics` is enabled:

- **Chinese:** Pinyin appears above each character/word in a smaller font (ruby annotation style).
- **Czech/Spanish:** Phonetics are not shown by default (spelling is mostly phonetic). Available on hover or via word exploration.

```
  dì xiōng    jiě mèi   men
  弟  兄       姐  妹     们  ，今天我想谈谈信心。
```

### 2.5 Clickable Words

Every word in both text panels is clickable. Clicking opens the Exploration Panel (Section 5).

When a word is clicked:
1. The word gets a selection highlight.
2. If a semantic link exists (Layer 6), the corresponding word(s) in the other language panel are also highlighted with a connecting visual (e.g., both words get the same color underline).
3. The Exploration Panel slides open from the right (or bottom on mobile).

---

## 3. Mode: Interlinear Listening

Sentence-by-sentence alternation between study and home language audio.

### 3.1 Layout

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  🔊 Bratři a sestry, dnes bych chtěl promluvit     │   │
│   │     o víře.                                         │   │
│   │                                                     │   │
│   │  🔇 Brothers and sisters, today I want to talk      │   │
│   │     about faith.                                    │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │     Víra je základním principem evangelia.          │   │
│   │                                                     │   │
│   │     Faith is a fundamental principle of the gospel. │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
│   │     (upcoming sentences, dimmed)                    │   │
│   └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Playback Flow

```
1. Play study-language audio for sentence group N
2. Pause for [interlinear_pause_ms] milliseconds (configurable, default 500)
3. Play home-language audio for the aligned sentence group N
4. Pause for [interlinear_pause_ms] milliseconds
5. Advance to sentence group N+1
6. Repeat
```

The user can configure:
- **Which language plays first** (study or home). Default: study first.
- **Pause duration** between languages (slider: 0ms – 3000ms).
- **Pause duration** between sentence pairs (slider: 0ms – 5000ms).
- **Playback speed** (applies to both languages equally, or independently).
- **Skip home language** (just play study language with pauses — for more advanced practice).

### 3.3 Visual State

- The currently playing sentence pair is prominent (full opacity, larger card).
- The speaker icon (🔊/🔇) indicates which language is currently playing.
- Completed sentence pairs scroll up and fade.
- Upcoming sentence pairs are visible but dimmed.
- Words within the active sentence are highlighted as they play (same as Read & Listen mode).

### 3.4 Controls

- **Play/Pause** — standard toggle
- **Previous sentence pair** — go back one pair
- **Next sentence pair** — skip forward one pair
- **Repeat current** — replay the current sentence pair
- Long-press on a sentence pair → opens all words in that pair for exploration

### 3.5 Sentence Audio Playback

Audio for individual sentences is played as time-range seeks within the full talk audio file — no pre-extraction needed. The timestamps from forced alignment (Layer 2) define the range.

```typescript
async function playSentenceAudio(
  audioElement: HTMLAudioElement,
  startTime: number,
  endTime: number,
  speed: number
): Promise<void> {
  audioElement.playbackRate = speed;
  audioElement.currentTime = startTime;
  audioElement.play();
  return new Promise(resolve => {
    const check = () => {
      if (audioElement.currentTime >= endTime) {
        audioElement.pause();
        resolve();
      } else {
        requestAnimationFrame(check);
      }
    };
    check();
  });
}
```

---

## 4. Audio Transport Bar

Persistent at the bottom of the screen across all modes.

### 4.1 Components

```
[▶/⏸] [⏪ 5s] [⏩ 5s] [🔄 repeat] [0.75x ▼] ═══●════════ 3:42 / 12:15
```

- **Play/Pause** toggle
- **Skip back/forward** 5 seconds (Read & Listen) or 1 sentence pair (Interlinear)
- **Repeat** toggle (repeat current sentence/pair)
- **Speed selector:** 0.5x, 0.75x, 1.0x, 1.25x, 1.5x, 2.0x
- **Progress bar:** draggable scrubber showing position in the talk
- **Time display:** current / total

### 4.2 Behavior by Mode

| Feature | Read & Listen | Interlinear |
|---------|--------------|-------------|
| Audio source | Study language only (or toggle to home) | Alternates per sentence |
| Skip buttons | ±5 seconds | ±1 sentence pair |
| Progress bar | Continuous position in talk | Position by sentence pair index |
| Speed | Single speed for active audio | Applies to both languages |

---

## 5. Exploration Panel

A slide-out panel that appears when the user clicks a word. This is the deep-dive learning interface.

### 5.1 Layout

```
┌─────────────────────────────────────┐
│  ✕ Close                            │
│                                     │
│  sestry                             │
│  /SES-tri/                          │
│  🔊 [play pronunciation]            │
│                                     │
│  ─── Translation ───                │
│  → sisters                          │
│  Link type: equivalent              │
│  "Vocative plural of 'sister'."     │
│                                     │
│  ─── Dictionary ───                 │
│  Lemma: sestra (f.)                 │
│  POS: noun                          │
│  Case: vocative                     │
│  Number: plural                     │
│  Gender: feminine                   │
│                                     │
│  Definition: sister; also a         │
│  form of address in religious       │
│  contexts                           │
│                                     │
│  ─── Register ───                   │
│  Formal/religious                   │
│  Informal: ségra                    │
│                                     │
│  ─── Related ───                    │
│  • bratr (brother)                  │
│  • sesterský (sisterly)             │
│                                     │
│  ─── Context ───                    │
│  "Bratři a [sestry], dnes bych      │
│   chtěl promluvit o víře."          │
│                                     │
│  [➕ Add to Flashcard]              │
│                                     │
└─────────────────────────────────────┘
```

### 5.2 Data Sources

The panel assembles data from two sources:

1. **Immediate (pre-computed, Layer 6):** The semantic link connecting this word to the other language. This appears instantly.
2. **On-demand (LLM call, Layer 7):** Dictionary, morphology, register analysis. This loads asynchronously with a spinner. Once loaded, it's cached in the persistence provider so the same word in the same context is instant next time.

### 5.3 Multi-Span Links

When a word is part of a phrase-level link (e.g., "break a leg" → idiomatic), the panel shows both:
- The individual word link (if any)
- The phrase link, with all constituent words highlighted

```
  ─── As part of phrase ───
  "break a leg" → "zlomte vaz"
  Link type: idiomatic
  "English idiom meaning 'good luck',
   with a direct Czech equivalent."
```

### 5.4 "Add to Flashcard" Flow

When the user taps "Add to Flashcard":

1. A card creation modal appears, pre-populated:
   - **Front:** Study-language word + phonetic + audio clip reference
   - **Back:** Home-language equivalent + definition + context sentence
2. The user can:
   - Swap front/back
   - Edit any field
   - Add/remove fields (e.g., remove audio, add the full sentence)
   - Choose a different audio clip (e.g., the sentence instead of the word)
3. Save → card is stored via PersistenceProvider.

---

## 6. Mode: Flashcards

A simple card review interface. No spaced-repetition algorithm — just boxes.

### 6.1 Card Collection View

```
┌─────────────────────────────────────────────────────────────┐
│  My Flashcards                           [Export to Anki]    │
│                                                             │
│  Filter: [All ▼]  [Czech ▼]  [October 2025 ▼]              │
│                                                             │
│  Box 0 (New):        12 cards    [Study →]                  │
│  Box 1 (Learning):    8 cards    [Study →]                  │
│  Box 2 (Familiar):    5 cards    [Study →]                  │
│  Box 3 (Known):      15 cards    [Review →]                 │
│                                                             │
│  All cards (40 total)                                       │
│  ┌──────────┬──────────┬──────────┬─────────┐               │
│  │ sestry   │ víra     │ promluvit│ ...     │               │
│  │ sisters  │ faith    │ to speak │         │               │
│  │ Box 1    │ Box 0    │ Box 2    │         │               │
│  └──────────┴──────────┴──────────┴─────────┘               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Review Interface

```
┌─────────────────────────────────────────────────────────────┐
│                        Card 3 of 12                         │
│                                                             │
│                                                             │
│                         víře                                │
│                       /VEE-rzhe/                            │
│                       🔊 [play]                             │
│                                                             │
│               "...promluvit o [víře]."                      │
│                                                             │
│                                                             │
│                    [  Show Answer  ]                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘

                         ↓ tap ↓

┌─────────────────────────────────────────────────────────────┐
│                        Card 3 of 12                         │
│                                                             │
│                         víře                                │
│                       /VEE-rzhe/                            │
│                                                             │
│                    ═══════════════                           │
│                                                             │
│                         faith                               │
│                   (locative of víra)                         │
│                                                             │
│         "Faith is a fundamental principle..."               │
│                                                             │
│                                                             │
│            [ ✗ Missed ]    [ ✓ Got It ]                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Box System

- **Box 0 (New):** Card has never been reviewed.
- **Box 1–4:** Progressive familiarity.
- **Got It:** Card moves up one box.
- **Missed:** Card moves back to Box 1 (not Box 0 — it's no longer "new").
- No scheduling. The user chooses which box to study. Cards within a box are shuffled.

### 6.4 Anki Export

"Export to Anki" generates a `.csv` file (tab-separated) compatible with Anki import:

```
front_text\tfront_audio\tback_text\tback_context\ttags
víře\t[sound:vire_clip.mp3]\tfaith (locative of víra)\tpromluvit o víře\tczech::conference::2025-10
```

Audio clips are extracted from the talk audio files (using ffmpeg via the backend) and bundled alongside the CSV. The user imports into Anki manually.

Future: generate proper `.apkg` files (Anki's SQLite-based format) for a smoother import with media.

---

## 7. Settings Panel

Accessible via the ⚙ gear icon.

### 7.1 User Profile

```
Display Name: [John            ]
Home Language: [English (eng)  ▼]
Study Languages: ☑ Czech (ces)  ☑ Chinese (zho)  ☐ Spanish (spa)
Active Study Language: [Czech ▼]
```

### 7.2 Study Preferences

```
─── Audio ───
Default playback speed:     [1.0x ▼]
Interlinear pause (ms):     [═══●══] 500ms
Interlinear order:          [Study first ▼]

─── Display ───
Show phonetics by default:  [●] On   [ ] Off
Show diff markers:          [●] On   [ ] Off
Font size:                  [Small] [●Medium] [Large]
Theme:                      [●Light] [Dark]

─── Home language panel ───
Show in Read & Listen mode: [●] On   [ ] Off
Default width:              [═══●══] 40%
```

---

## 8. Component Hierarchy

```
App
├── Header
│   ├── TalkSelector (dropdown → modal on mobile)
│   ├── UserMenu
│   └── SettingsButton
│
├── MainContent
│   ├── ReadListenMode
│   │   ├── StudyTextPanel
│   │   │   ├── ParagraphBlock (repeated)
│   │   │   │   ├── SentenceSpan (repeated)
│   │   │   │   │   └── ClickableWord (repeated)
│   │   │   │   │       ├── WordHighlight (audio sync)
│   │   │   │   │       ├── DiffIndicator (optional)
│   │   │   │   │       └── PhoneticAnnotation (optional, ruby)
│   │   │   │   └── DiffInsertionMarker (optional, between words)
│   │   │   └── AutoScroller
│   │   └── HomeTextPanel (collapsible)
│   │       └── (same structure as StudyTextPanel)
│   │
│   ├── InterlinearMode
│   │   ├── SentencePairCard (repeated)
│   │   │   ├── StudySentence
│   │   │   │   └── ClickableWord (repeated)
│   │   │   ├── HomeSentence
│   │   │   │   └── ClickableWord (repeated)
│   │   │   └── PlaybackStateIndicator (🔊/🔇)
│   │   ├── InterlinearControls
│   │   │   ├── PauseDurationSlider
│   │   │   └── LanguageOrderToggle
│   │   └── SentenceNavigator
│   │
│   └── FlashcardMode
│       ├── CardCollectionView
│       │   ├── BoxSummary (repeated per box)
│       │   ├── CardGrid
│       │   └── AnkiExportButton
│       └── CardReviewView
│           ├── CardDisplay (front/back flip)
│           ├── AudioPlayButton
│           └── ReviewButtons (Got It / Missed)
│
├── ExplorationPanel (slide-out, global)
│   ├── WordHeader (word, phonetic, play button)
│   ├── TranslationSection (from semantic map)
│   ├── DictionarySection (on-demand LLM, with spinner)
│   ├── MorphologySection
│   ├── RegisterSection
│   ├── RelatedWordsSection
│   ├── ContextSection
│   └── AddToFlashcardButton → FlashcardCreationModal
│
├── AudioTransportBar (persistent)
│   ├── PlayPauseButton
│   ├── SkipButtons
│   ├── SpeedSelector
│   ├── ProgressScrubber
│   └── TimeDisplay
│
└── SettingsPanel (modal/drawer)
    ├── ProfileSection
    └── PreferencesSection
```

---

## 9. API Contract (Frontend ↔ Backend)

The frontend expects these REST endpoints from the backend:

### 9.1 Conference & Talk Browsing

```
GET /api/conferences
  → { conferences: [{ id, year, month, talks_count }] }

GET /api/conferences/{conference_id}
  → { conference_id, sessions: [{ id, name, talks: [{ id, speaker, title, languages }] }] }
```

### 9.2 Talk Data

```
GET /api/talks/{talk_id}/content/{language}
  → TalkContent (text, transcript, diff, segments, phonetics)

GET /api/talks/{talk_id}/alignment/{home_lang}/{study_lang}
  → LanguagePairAlignment (paragraph alignment, sentence alignment)

GET /api/talks/{talk_id}/semantic-map/{home_lang}/{study_lang}
  → SemanticMap (spans + links for all sentence groups)
```

### 9.3 Audio

```
GET /api/talks/{talk_id}/audio/{language}
  → audio/mpeg stream (full talk audio)

GET /api/talks/{talk_id}/audio/{language}/clip?start={s}&end={s}
  → audio/mpeg stream (extracted clip, for flashcard audio)
```

### 9.4 On-Demand Word Analysis

```
POST /api/analyze/word
  Body: { word, context_sentence, language, talk_id }
  → WordAnalysis (dictionary, morphology, register, etc.)
```

This endpoint checks the cache first, then calls the LLM if not cached.

### 9.5 Flashcards

```
GET    /api/users/{user_id}/flashcards?lang={lang}&conference={id}&box={n}
POST   /api/users/{user_id}/flashcards
PUT    /api/users/{user_id}/flashcards/{card_id}
DELETE /api/users/{user_id}/flashcards/{card_id}
POST   /api/users/{user_id}/flashcards/{card_id}/review
  Body: { result: "got_it" | "missed" }

GET    /api/users/{user_id}/flashcards/export?format=anki_csv
  → text/csv download with audio clips as zip
```

### 9.6 User & Preferences

```
GET  /api/users/current
PUT  /api/users/current/preferences
```

---

## 10. Key Frontend Behaviors

### 10.1 Audio-Text Synchronization Algorithm

```typescript
class AudioTextSync {
  private timestampedWords: TimestampedWord[];  // from transcript
  private diffMapping: DiffMapping;              // transcript word → official text word
  private currentIndex: number = 0;

  // Called on each animation frame while audio is playing
  onTimeUpdate(currentTime: number): HighlightState {
    // Binary search for the current word in timestamped array
    const wordIndex = this.findWordAtTime(currentTime);

    if (wordIndex === this.currentIndex) return null; // no change
    this.currentIndex = wordIndex;

    const transcriptWord = this.timestampedWords[wordIndex];
    const officialTextPosition = this.diffMapping.transcriptToOfficial(wordIndex);

    return {
      // Which word to highlight in the official text
      paragraphIndex: officialTextPosition.paragraph,
      sentenceIndex: officialTextPosition.sentence,
      wordIndex: officialTextPosition.word,

      // Whether this word has a diff (mismatch between audio and text)
      diffType: officialTextPosition.diffType, // "equal" | "replace" | "insert" | null

      // The currently playing sentence (for sentence-level tint)
      activeSentence: officialTextPosition.sentence,
    };
  }
}
```

### 10.2 Cross-Language Highlight on Click

When a word is clicked in either language panel:

```typescript
function onWordClick(spanId: string, language: string) {
  // Find all semantic links that include this span
  const links = semanticMap.links.filter(link =>
    link.spans.includes(spanId)
  );

  // Collect all linked spans in the OTHER language
  const linkedSpans = links.flatMap(link =>
    link.spans
      .filter(id => semanticMap.getSpan(id).lang !== language)
  );

  // Highlight the clicked word
  setHighlighted(spanId, 'primary');

  // Highlight corresponding words in the other language
  linkedSpans.forEach(id => setHighlighted(id, 'secondary'));

  // Open exploration panel
  openExploration(spanId, links);
}
```

### 10.3 Interlinear Playback State Machine

```
States:
  IDLE           → user hasn't started
  PLAYING_STUDY  → study language sentence is playing
  PAUSE_1        → pause between study and home
  PLAYING_HOME   → home language sentence is playing
  PAUSE_2        → pause between sentence pairs
  COMPLETE       → reached end of talk

Transitions:
  IDLE → PLAYING_STUDY           (user presses play)
  PLAYING_STUDY → PAUSE_1        (study audio for sentence ends)
  PAUSE_1 → PLAYING_HOME         (pause timer expires)
  PLAYING_HOME → PAUSE_2         (home audio for sentence ends)
  PAUSE_2 → PLAYING_STUDY        (advance to next pair, pause timer expires)
  PAUSE_2 → COMPLETE             (no more pairs)

  Any state → IDLE               (user presses pause)
  Any state → [adjusted state]   (user skips forward/back)
```

### 10.4 Responsive Design

- **Desktop (>1024px):** Side-by-side panels, exploration panel as right drawer.
- **Tablet (768–1024px):** Stacked panels or side-by-side with narrower home panel.
- **Mobile (<768px):** Single panel with tab to switch languages. Exploration panel as bottom sheet.

The audio transport bar is always visible and fixed to the bottom.

---

## 11. Offline Considerations

For the initial version, the app requires a network connection to the local backend (which is always available since it's localhost). The LLM calls for word analysis (Section 5.2) require internet.

If offline mode becomes a priority later:
- Pre-cache all talk data in the browser (service worker + IndexedDB).
- Pre-compute word analyses for the most common N words per talk.
- Flashcard review works offline with syncing on reconnect.

---

## 12. Accessibility

- All interactive elements are keyboard-navigable.
- Audio controls respond to standard keyboard shortcuts (space = play/pause, arrow keys = skip).
- Word highlighting uses both color AND a secondary indicator (bold, underline) for color-blind users.
- Phonetic annotations use proper `<ruby>` / `<rt>` HTML tags for screen reader compatibility.
- Font size is adjustable. Minimum touch target: 44×44px on mobile.
- High contrast mode available through the theme setting.
