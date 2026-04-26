"""
Transcription Provider interface — converts audio to text with word timestamps.

Used in pipeline Stage 2 for discovering what was actually spoken in the audio.
The transcript may differ from the official published text.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from .audio_provider import Transcript, TranscriptSegment, TimestampedWord

WHISPER_LANG_MAP = {
    "eng": "en",
    "ces": "cs",
    "zho": "zh",
    "zhs": "zh",
    "zht": "zh",
    "spa": "es",
    "fra": "fr",
    "deu": "de",
    "por": "pt",
    "ita": "it",
    "jpn": "ja",
    "kor": "ko",
    "rus": "ru",
}


class TranscriptionProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path, language: str) -> Transcript:
        """Transcribe audio to text with word-level timestamps."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier for the model used, written into manifests."""
        pass


class FasterWhisperTranscriptionProvider(TranscriptionProvider):
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    @property
    def model_name(self) -> str:
        return f"faster-whisper-{self.model_size}"

    def _ensure_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise ImportError(
                    "faster-whisper is required for transcription. "
                    "Install with: pip install -e '.[transcribe]'"
                )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )

    async def transcribe(self, audio_path: Path, language: str) -> Transcript:
        import asyncio
        return await asyncio.to_thread(self._transcribe_sync, audio_path, language)

    def _transcribe_sync(self, audio_path: Path, language: str) -> Transcript:
        self._ensure_model()
        whisper_lang = WHISPER_LANG_MAP.get(language, language[:2])

        segments_iter, info = self._model.transcribe(
            str(audio_path),
            language=whisper_lang,
            word_timestamps=True,
            beam_size=5,
        )

        segments = []
        for seg in segments_iter:
            words = []
            if seg.words:
                for w in seg.words:
                    words.append(TimestampedWord(
                        word=w.word.strip(),
                        start=round(w.start, 3),
                        end=round(w.end, 3),
                        score=round(w.probability, 3),
                    ))
            segments.append(TranscriptSegment(
                start=round(seg.start, 3),
                end=round(seg.end, 3),
                text=seg.text.strip(),
                words=words,
            ))

        return Transcript(
            model=self.model_name,
            language=language,
            segments=segments,
        )


class MockTranscriptionProvider(TranscriptionProvider):
    @property
    def model_name(self) -> str:
        return "mock-whisper"

    async def transcribe(self, audio_path: Path, language: str) -> Transcript:
        return Transcript(
            model=self.model_name,
            language=language,
            segments=[
                TranscriptSegment(
                    start=0.0,
                    end=5.0,
                    text="Mock transcribed audio segment.",
                    words=[
                        TimestampedWord(word="Mock", start=0.0, end=0.5, score=0.95),
                        TimestampedWord(word="transcribed", start=0.6, end=1.2, score=0.93),
                        TimestampedWord(word="audio", start=1.3, end=1.8, score=0.97),
                        TimestampedWord(word="segment.", start=1.9, end=2.5, score=0.94),
                    ],
                )
            ],
        )
