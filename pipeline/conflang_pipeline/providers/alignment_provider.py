"""
Alignment Provider interface — maps known text to audio timestamps.

Used in pipeline Stage 2 for forced alignment of the official published text
against the audio. Produces word-level timestamps for the text the user reads.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from .audio_provider import Transcript, TranscriptSegment, TimestampedWord

CTC_LANG_MAP = {
    "eng": "eng",
    "ces": "ces",
    "zho": "cmn",
    "zhs": "cmn",
    "zht": "cmn",
    "spa": "spa",
    "fra": "fra",
    "deu": "deu",
    "por": "por",
    "ita": "ita",
    "jpn": "jpn",
    "kor": "kor",
    "rus": "rus",
}


def _is_cjk(language: str) -> bool:
    return language in ("zho", "zhs", "zht", "jpn", "kor")


class AlignmentProvider(ABC):
    @abstractmethod
    async def align(self, audio_path: Path, text: str, language: str) -> Transcript:
        """Align known text against audio to produce word-level timestamps."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier for the model used, written into manifests."""
        pass


class CTCForcedAlignmentProvider(AlignmentProvider):
    """Uses torchaudio MMS_FA for CTC forced alignment.

    Aligns the full text against the full audio in a single pass.
    The emission generation step is the bottleneck (~10 min for a 17-min talk on CPU).
    """

    def __init__(self, device: str = "cpu"):
        self.device = device
        self._model = None
        self._dictionary = None
        self._bundle = None

    @property
    def model_name(self) -> str:
        return "torchaudio-mms-fa"

    def _ensure_model(self):
        if self._model is not None:
            return
        try:
            import torch
            import torchaudio
        except ImportError:
            raise ImportError(
                "torch and torchaudio are required for alignment. "
                "Install with: pip install -e '.[align]'"
            )
        import os
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        self._bundle = torchaudio.pipelines.MMS_FA
        self._model = self._bundle.get_model()
        full_dict = self._bundle.get_dict(star=None)
        self._dictionary = {k: v for k, v in full_dict.items() if v != 0}

    async def align(self, audio_path: Path, text: str, language: str) -> Transcript:
        import asyncio
        return await asyncio.to_thread(self._align_sync, audio_path, text, language)

    def _align_sync(self, audio_path: Path, text: str, language: str) -> Transcript:
        import torch
        import torchaudio
        import torchaudio.functional as F

        self._ensure_model()

        is_cjk = _is_cjk(language)
        if is_cjk:
            original_tokens = list(text.replace(" ", "").replace("\n", ""))
        else:
            flat_text = text.replace("\n\n", " ").replace("\n", " ")
            original_tokens = flat_text.split()

        transcript = []
        word_indices = []
        for i, word in enumerate(original_tokens):
            chars = [c.lower() for c in word if c.lower() in self._dictionary]
            if chars:
                transcript.append(chars)
                word_indices.append(i)

        waveform, sr = torchaudio.load(audio_path)
        if sr != self._bundle.sample_rate:
            waveform = torchaudio.functional.resample(waveform, sr, self._bundle.sample_rate)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        with torch.inference_mode():
            emission, _ = self._model(waveform)

        tokenized = [self._dictionary[c] for word in transcript for c in word]
        aligned_tokens, scores = torchaudio.functional.forced_align(
            emission, torch.tensor([tokenized]), blank=0
        )

        token_spans = F.merge_tokens(aligned_tokens[0], scores[0])
        ratio = waveform.size(1) / emission.size(1)

        words = []
        idx = 0
        for i, word_chars in enumerate(transcript):
            n = len(word_chars)
            wts = token_spans[idx:idx + n]
            if wts:
                start = wts[0].start
                end = wts[-1].end
                score = sum(s.score for s in wts) / len(wts)
                words.append(TimestampedWord(
                    word=original_tokens[word_indices[i]],
                    start=round(start * ratio / self._bundle.sample_rate, 3),
                    end=round(end * ratio / self._bundle.sample_rate, 3),
                    score=round(score, 3),
                ))
            idx += n

        segment = TranscriptSegment(
            start=words[0].start if words else 0.0,
            end=words[-1].end if words else 0.0,
            text=text,
            words=words,
        )

        return Transcript(
            model=self.model_name,
            language=language,
            segments=[segment],
        )


class MockAlignmentProvider(AlignmentProvider):
    @property
    def model_name(self) -> str:
        return "mock-ctc-aligner"

    async def align(self, audio_path: Path, text: str, language: str) -> Transcript:
        words_list = list(text.replace(" ", "")) if _is_cjk(language) else text.split()
        timestamped = []
        t = 0.0
        for w in words_list:
            duration = 0.3
            timestamped.append(TimestampedWord(
                word=w, start=round(t, 3), end=round(t + duration, 3), score=0.90,
            ))
            t += duration + 0.05

        return Transcript(
            model=self.model_name,
            language=language,
            segments=[
                TranscriptSegment(
                    start=0.0,
                    end=round(t, 3),
                    text=text,
                    words=timestamped,
                )
            ],
        )
