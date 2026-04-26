"""Tests for transcription and alignment provider interfaces."""

import asyncio
from pathlib import Path

import pytest

from conflang_pipeline.providers.audio_provider import Transcript, TranscriptSegment, TimestampedWord
from conflang_pipeline.providers.transcription_provider import MockTranscriptionProvider
from conflang_pipeline.providers.alignment_provider import MockAlignmentProvider


class TestTranscriptModel:
    def test_roundtrip_serialization(self):
        t = Transcript(
            talk_id="2025-10-test",
            model="test-model",
            language="eng",
            segments=[
                TranscriptSegment(
                    start=0.0,
                    end=2.0,
                    text="Hello world.",
                    words=[
                        TimestampedWord(word="Hello", start=0.0, end=0.5, score=0.95),
                        TimestampedWord(word="world.", start=0.6, end=1.0, score=0.90),
                    ],
                )
            ],
        )
        data = t.model_dump()
        restored = Transcript(**data)
        assert restored.talk_id == "2025-10-test"
        assert restored.segments[0].words[0].word == "Hello"
        assert restored.segments[0].words[1].score == 0.90

    def test_talk_id_optional(self):
        t = Transcript(model="m", language="eng", segments=[])
        assert t.talk_id is None


class TestMockTranscriptionProvider:
    def test_returns_valid_transcript(self):
        provider = MockTranscriptionProvider()
        result = asyncio.run(provider.transcribe(Path("/fake/audio.mp3"), "eng"))
        assert isinstance(result, Transcript)
        assert result.model == "mock-whisper"
        assert result.language == "eng"
        assert len(result.segments) > 0
        assert len(result.segments[0].words) > 0

    def test_model_name(self):
        provider = MockTranscriptionProvider()
        assert provider.model_name == "mock-whisper"


class TestMockAlignmentProvider:
    def test_returns_valid_transcript(self):
        provider = MockAlignmentProvider()
        text = "Hello world today."
        result = asyncio.run(provider.align(Path("/fake/audio.mp3"), text, "eng"))
        assert isinstance(result, Transcript)
        assert result.model == "mock-ctc-aligner"
        assert len(result.segments) == 1
        assert len(result.segments[0].words) == 3

    def test_words_match_input(self):
        provider = MockAlignmentProvider()
        text = "Brothers and sisters."
        result = asyncio.run(provider.align(Path("/fake/audio.mp3"), text, "eng"))
        words = [w.word for w in result.segments[0].words]
        assert words == ["Brothers", "and", "sisters."]

    def test_chinese_character_level(self):
        provider = MockAlignmentProvider()
        text = "弟兄姐妹"
        result = asyncio.run(provider.align(Path("/fake/audio.mp3"), text, "zho"))
        words = [w.word for w in result.segments[0].words]
        assert words == ["弟", "兄", "姐", "妹"]

    def test_timestamps_are_sequential(self):
        provider = MockAlignmentProvider()
        result = asyncio.run(provider.align(Path("/fake/audio.mp3"), "one two three four", "eng"))
        words = result.segments[0].words
        for i in range(1, len(words)):
            assert words[i].start >= words[i - 1].end

    def test_model_name(self):
        provider = MockAlignmentProvider()
        assert provider.model_name == "mock-ctc-aligner"
