"""
Provider interfaces for the pipeline.

All external concerns are accessed through these interfaces.
The pipeline injects concrete implementations at startup.
"""

from .llm_provider import LLMProvider, MockLLMProvider
from .audio_provider import (
    AudioProvider, MockAudioProvider,
    Transcript, TranscriptSegment, TimestampedWord,
)
from .transcription_provider import (
    TranscriptionProvider, FasterWhisperTranscriptionProvider, MockTranscriptionProvider,
)
from .alignment_provider import (
    AlignmentProvider, CTCForcedAlignmentProvider, MockAlignmentProvider,
)
from .content_provider import ContentProvider, MockContentProvider, TalkTextResult
from .church_content_provider import ChurchContentProvider
from .persistence_provider import PersistenceProvider, JSONPersistenceProvider

__all__ = [
    "LLMProvider",
    "MockLLMProvider",
    "AudioProvider",
    "MockAudioProvider",
    "Transcript",
    "TranscriptSegment",
    "TimestampedWord",
    "TranscriptionProvider",
    "FasterWhisperTranscriptionProvider",
    "MockTranscriptionProvider",
    "AlignmentProvider",
    "CTCForcedAlignmentProvider",
    "MockAlignmentProvider",
    "ContentProvider",
    "MockContentProvider",
    "ChurchContentProvider",
    "TalkTextResult",
    "PersistenceProvider",
    "JSONPersistenceProvider",
]
