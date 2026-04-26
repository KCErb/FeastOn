"""
Audio Provider interface for transcription and alignment.

Used in pipeline stage 2 for WhisperX transcription and forced alignment.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel


class TimestampedWord(BaseModel):
    """A word with start/end timestamps from forced alignment"""
    word: str
    start: float  # seconds
    end: float
    score: float  # confidence score


class TranscriptSegment(BaseModel):
    """A segment of transcribed audio (typically a sentence or phrase)"""
    start: float
    end: float
    text: str
    words: list[TimestampedWord]


class Transcript(BaseModel):
    """Full transcript with word-level timestamps"""
    talk_id: str | None = None
    model: str  # e.g., "faster-whisper-large-v3"
    language: str
    segments: list[TranscriptSegment]


class AudioProvider(ABC):
    """Interface for audio transcription and alignment"""

    @abstractmethod
    async def transcribe(self, audio_path: Path, language: str) -> Transcript:
        """
        Transcribe audio and perform forced alignment for word-level timestamps.

        This uses WhisperX (Whisper + wav2vec2 alignment).
        """
        pass


class MockAudioProvider(AudioProvider):
    """Stub implementation for testing"""

    async def transcribe(self, audio_path: Path, language: str) -> Transcript:
        """Returns a minimal stub transcript"""
        return Transcript(
            model="mock-whisper",
            language=language,
            segments=[
                TranscriptSegment(
                    start=0.0,
                    end=5.0,
                    text="Mock transcribed audio.",
                    words=[
                        TimestampedWord(word="Mock", start=0.0, end=0.5, score=0.95),
                        TimestampedWord(word="transcribed", start=0.6, end=1.2, score=0.93),
                        TimestampedWord(word="audio.", start=1.3, end=2.0, score=0.97),
                    ]
                )
            ]
        )
