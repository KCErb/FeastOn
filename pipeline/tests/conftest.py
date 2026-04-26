"""Shared test fixtures for pipeline tests."""

import json
from pathlib import Path

import pytest

from conflang_pipeline.manifest import StageManifest, write_manifest, hash_file, hash_string
from datetime import datetime, timezone


@pytest.fixture
def mock_talk_dir(tmp_path):
    """Create a minimal Stage 1 output directory with audio + text for two languages."""
    talk_dir = tmp_path / "raw" / "2025-10" / "2025-10-test"

    metadata = {
        "talk_id": "2025-10-test",
        "conference_id": "2025-10",
        "session": "Test Session",
        "speaker": "Elder Test",
        "title": {"eng": "Test Talk", "ces": "Testovací proslov"},
        "source_urls": {"eng": "https://example.com/eng", "ces": "https://example.com/ces"},
        "languages_available": ["eng", "ces"],
    }
    talk_dir.mkdir(parents=True, exist_ok=True)
    (talk_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    for lang, text in [
        ("eng", "Brothers and sisters, today I want to talk about faith.\n\nFaith is a principle of power."),
        ("ces", "Bratři a sestry, dnes bych chtěl promluvit o víře.\n\nVíra je princip moci."),
    ]:
        lang_dir = talk_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        (lang_dir / "official_text.txt").write_text(text, encoding="utf-8")
        (lang_dir / "official_text.html").write_text(f"<p>{text}</p>", encoding="utf-8")
        (lang_dir / "audio.mp3").write_bytes(b"FAKE_MP3_AUDIO_DATA")

    # Write Stage 1 manifest
    manifest = StageManifest(
        stage=1,
        completed_at=datetime.now(timezone.utc),
        input_hashes={
            "talk_url": hash_string("https://example.com"),
            "languages": hash_string("ces,eng"),
        },
    )
    write_manifest(talk_dir / "stage1_manifest.json", manifest)

    return talk_dir


@pytest.fixture
def data_dir(tmp_path):
    """Root data directory."""
    return tmp_path
