"""Tests for Stage 2: Transcribe + Align orchestration."""

import json
from pathlib import Path

import pytest

from conflang_pipeline.providers.transcription_provider import MockTranscriptionProvider
from conflang_pipeline.providers.alignment_provider import MockAlignmentProvider
from conflang_pipeline.stages.transcribe import run_transcribe
from conflang_pipeline.manifest import read_manifest


@pytest.fixture
def providers():
    return MockTranscriptionProvider(), MockAlignmentProvider()


class TestRunTranscribe:
    def test_produces_output_files(self, mock_talk_dir, data_dir, providers):
        trans, align = providers
        run_transcribe(mock_talk_dir, ["eng", "ces"], data_dir, trans, align)

        for lang in ["eng", "ces"]:
            out_dir = data_dir / "processed" / "2025-10" / "2025-10-test" / lang
            assert (out_dir / "transcript.json").exists()
            assert (out_dir / "aligned_official.json").exists()
            assert (out_dir / "stage2_manifest.json").exists()

    def test_transcript_json_structure(self, mock_talk_dir, data_dir, providers):
        trans, align = providers
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align)

        out = data_dir / "processed" / "2025-10" / "2025-10-test" / "eng"
        transcript = json.loads((out / "transcript.json").read_text())
        assert transcript["talk_id"] == "2025-10-test"
        assert transcript["language"] == "eng"
        assert transcript["model"] == "mock-whisper"
        assert len(transcript["segments"]) > 0
        assert "words" in transcript["segments"][0]

    def test_aligned_official_json_structure(self, mock_talk_dir, data_dir, providers):
        trans, align = providers
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align)

        out = data_dir / "processed" / "2025-10" / "2025-10-test" / "eng"
        aligned = json.loads((out / "aligned_official.json").read_text())
        assert aligned["talk_id"] == "2025-10-test"
        assert aligned["model"] == "mock-ctc-aligner"
        # Official text has 2 paragraphs → 2 segments
        assert len(aligned["segments"]) == 2

    def test_aligned_words_match_official_text(self, mock_talk_dir, data_dir, providers):
        trans, align = providers
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align)

        out = data_dir / "processed" / "2025-10" / "2025-10-test" / "eng"
        aligned = json.loads((out / "aligned_official.json").read_text())
        all_words = []
        for seg in aligned["segments"]:
            all_words.extend(w["word"] for w in seg["words"])
        official = (mock_talk_dir / "eng" / "official_text.txt").read_text()
        expected_words = official.split()
        assert all_words == expected_words

    def test_idempotent_skip(self, mock_talk_dir, data_dir, providers, capsys):
        trans, align = providers
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align)
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align)
        output = capsys.readouterr().out
        assert "already complete, skipping" in output

    def test_force_rerun(self, mock_talk_dir, data_dir, providers, capsys):
        trans, align = providers
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align)
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align, force=True)
        output = capsys.readouterr().out
        # Should not say "skipping" on second run when forced
        lines = output.strip().split("\n")
        last_lines = [l for l in lines if "Stage 2 (eng)" in l]
        assert "skipping" not in last_lines[-1]

    def test_manifest_has_model_version(self, mock_talk_dir, data_dir, providers):
        trans, align = providers
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align)

        manifest = read_manifest(
            data_dir / "processed" / "2025-10" / "2025-10-test" / "eng" / "stage2_manifest.json"
        )
        assert manifest is not None
        assert manifest.stage == 2
        assert manifest.model_version == "mock-whisper+mock-ctc-aligner"
        assert "audio_file" in manifest.input_hashes
        assert "official_text" in manifest.input_hashes

    def test_missing_audio_skips(self, mock_talk_dir, data_dir, providers, capsys):
        trans, align = providers
        (mock_talk_dir / "eng" / "audio.mp3").unlink()
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align)
        output = capsys.readouterr().out
        assert "no audio file" in output

    def test_missing_audio_no_output(self, mock_talk_dir, data_dir, providers):
        trans, align = providers
        (mock_talk_dir / "eng" / "audio.mp3").unlink()
        run_transcribe(mock_talk_dir, ["eng"], data_dir, trans, align)
        out_dir = data_dir / "processed" / "2025-10" / "2025-10-test" / "eng"
        assert not (out_dir / "transcript.json").exists()
        assert not (out_dir / "stage2_manifest.json").exists()

    def test_processes_multiple_languages(self, mock_talk_dir, data_dir, providers):
        trans, align = providers
        run_transcribe(mock_talk_dir, ["eng", "ces"], data_dir, trans, align)

        for lang in ["eng", "ces"]:
            out_dir = data_dir / "processed" / "2025-10" / "2025-10-test" / lang
            transcript = json.loads((out_dir / "transcript.json").read_text())
            assert transcript["language"] == lang
