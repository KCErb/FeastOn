"""
Stage 1: Ingest — Download talk text + audio from churchofjesuschrist.org.

Downloads official text (HTML + plain) and audio (MP3) for each requested language.
Writes output to data/raw/{conference_id}/{talk_id}/ following the spec structure.
Idempotent: skips if manifest is fresh and all files exist.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..manifest import StageManifest, hash_string, write_manifest, read_manifest, is_stale
from ..providers.content_provider import ContentProvider
from ..talk_url import parse_talk_reference

logger = logging.getLogger(__name__)


def run_ingest(
    talk_url: str,
    languages: list[str],
    data_dir: Path,
    content_provider: ContentProvider,
    force: bool = False,
) -> Path:
    """
    Stage 1: Ingest — Download talk text + audio for specified languages.

    Args:
        talk_url: Full URL or talk ID for the talk.
        languages: Language codes to download (e.g., ["eng", "ces"]).
        data_dir: Root data directory (e.g., ./data).
        content_provider: Provider for fetching content.
        force: If True, re-download even if files exist.

    Returns:
        Path to the talk directory (data/raw/{conference_id}/{talk_id}/).
    """
    return asyncio.run(_run_ingest(talk_url, languages, data_dir, content_provider, force))


async def _run_ingest(
    talk_url: str,
    languages: list[str],
    data_dir: Path,
    content_provider: ContentProvider,
    force: bool,
) -> Path:
    """Async implementation of the ingest stage."""
    ref = parse_talk_reference(talk_url)
    talk_dir = data_dir / "raw" / ref.conference_id / ref.talk_id
    manifest_path = talk_dir / "stage1_manifest.json"

    # Check idempotency
    input_hashes = {
        "talk_url": hash_string(ref.base_url),
        "languages": hash_string(",".join(sorted(languages))),
    }

    if not force:
        existing_manifest = read_manifest(manifest_path)
        if existing_manifest and not is_stale(existing_manifest, input_hashes):
            if _all_files_exist(talk_dir, languages):
                logger.info(f"Stage 1 already complete for {ref.talk_id}, skipping")
                print(f"  ✓ Stage 1 (Ingest): already complete, skipping")
                return talk_dir

    print(f"  → Stage 1 (Ingest): downloading {ref.talk_id} [{', '.join(languages)}]")

    # Fetch metadata
    print(f"    Fetching metadata...")
    metadata = await content_provider.fetch_talk_metadata(talk_url, languages)

    # Fetch text and audio for each language
    for lang in languages:
        lang_dir = talk_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        lang_url = f"{ref.base_url}?lang={lang}"

        # Fetch text (HTML + plain)
        print(f"    [{lang}] Fetching text...")
        text_result = await content_provider.fetch_talk_text(ref.base_url, lang)

        (lang_dir / "official_text.html").write_text(text_result.html, encoding="utf-8")
        (lang_dir / "official_text.txt").write_text(text_result.plain_text, encoding="utf-8")
        logger.info(f"Saved text for {lang}: {len(text_result.plain_text)} chars")

        # Fetch audio
        print(f"    [{lang}] Downloading audio...")
        try:
            audio_data = await content_provider.fetch_talk_audio(ref.base_url, lang)
            (lang_dir / "audio.mp3").write_bytes(audio_data)
            size_mb = len(audio_data) / (1024 * 1024)
            logger.info(f"Saved audio for {lang}: {size_mb:.1f} MB")
            print(f"    [{lang}] Audio: {size_mb:.1f} MB")
        except Exception as e:
            logger.warning(f"Could not download audio for {lang}: {e}")
            print(f"    [{lang}] ⚠ Audio not available: {e}")

    # Write metadata.json
    metadata_dict = {
        "talk_id": metadata.talk_id,
        "conference_id": metadata.conference_id,
        "session": metadata.session,
        "speaker": metadata.speaker,
        "title": metadata.title,
        "source_urls": metadata.source_urls,
        "languages_available": metadata.languages_available,
    }
    talk_dir.mkdir(parents=True, exist_ok=True)
    (talk_dir / "metadata.json").write_text(
        json.dumps(metadata_dict, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write stage manifest
    manifest = StageManifest(
        stage=1,
        completed_at=datetime.now(timezone.utc),
        input_hashes=input_hashes,
    )
    write_manifest(manifest_path, manifest)

    print(f"  ✓ Stage 1 (Ingest): complete → {talk_dir}")
    return talk_dir


def _all_files_exist(talk_dir: Path, languages: list[str]) -> bool:
    """Check if all expected output files exist."""
    if not (talk_dir / "metadata.json").exists():
        return False
    for lang in languages:
        lang_dir = talk_dir / lang
        if not (lang_dir / "official_text.txt").exists():
            return False
        if not (lang_dir / "official_text.html").exists():
            return False
        # Audio is optional — don't require it for completeness
    return True
