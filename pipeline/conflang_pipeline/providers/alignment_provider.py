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
    def __init__(self, device: str = "cpu"):
        self.device = device
        self._model = None
        self._tokenizer = None

    @property
    def model_name(self) -> str:
        return "ctc-forced-aligner-mms"

    def _ensure_model(self):
        if self._model is not None:
            return
        try:
            import torch
            from ctc_forced_aligner import load_alignment_model
        except ImportError:
            raise ImportError(
                "ctc-forced-aligner is required for alignment. "
                "Install with: pip install -e '.[align]'"
            )
        self._model, self._tokenizer = load_alignment_model(
            device=self.device,
        )

    async def align(self, audio_path: Path, text: str, language: str) -> Transcript:
        import asyncio
        return await asyncio.to_thread(self._align_sync, audio_path, text, language)

    def _align_sync(self, audio_path: Path, text: str, language: str) -> Transcript:
        import torch
        import torchaudio
        from ctc_forced_aligner import (
            generate_emissions,
            get_alignments,
            get_spans,
            load_alignment_model,
            postprocess_results,
            preprocess_text,
        )

        self._ensure_model()

        audio_waveform, sample_rate = torchaudio.load(audio_path)
        if sample_rate != 16000:
            audio_waveform = torchaudio.functional.resample(
                audio_waveform, sample_rate, 16000
            )

        if audio_waveform.shape[0] > 1:
            audio_waveform = audio_waveform.mean(dim=0, keepdim=True)

        emissions, stride = generate_emissions(
            self._model, audio_waveform.to(self.device), batch_size=16
        )

        ctc_lang = CTC_LANG_MAP.get(language, language)
        is_cjk = _is_cjk(language)

        tokens_starred, text_starred = preprocess_text(
            text,
            romanize=not text.isascii(),
            language=ctc_lang,
        )

        segments, scores, blank_id = get_alignments(
            emissions, tokens_starred, self._tokenizer,
        )

        spans = get_spans(tokens_starred, segments, blank_id)

        word_spans = postprocess_results(spans, stride, scores, text_starred)

        # Build original words list for mapping back
        if is_cjk:
            original_tokens = list(text.replace(" ", ""))
        else:
            original_tokens = text.split()

        words = []
        for i, span in enumerate(word_spans):
            word_text = original_tokens[i] if i < len(original_tokens) else span["word"]
            words.append(TimestampedWord(
                word=word_text,
                start=round(span["start"], 3),
                end=round(span["end"], 3),
                score=round(span["score"], 3),
            ))

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
