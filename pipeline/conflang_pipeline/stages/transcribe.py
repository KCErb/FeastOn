"""
Stage 2: Transcribe + Align — Produce timestamped text from audio.

For each language, produces two artifacts:
  - transcript.json: Whisper transcription (what was actually spoken)
  - aligned_official.json: Forced alignment of official text against audio

The difference between these two is a key feature — it surfaces how spoken
and written forms diverge, feeding Stage 3 (diff) and the study UI.

Idempotent: skips if manifest is fresh and all files exist.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from ..manifest import StageManifest, hash_file, hash_string, write_manifest, read_manifest, is_stale
from ..providers.transcription_provider import TranscriptionProvider
from ..providers.alignment_provider import AlignmentProvider

logger = logging.getLogger(__name__)


def run_transcribe(
    talk_dir: Path,
    languages: list[str],
    data_dir: Path,
    transcription_provider: TranscriptionProvider,
    alignment_provider: AlignmentProvider,
    force: bool = False,
) -> Path:
    """
    Stage 2: Transcribe + Align for all requested languages.

    Args:
        talk_dir: Path to raw talk data (data/raw/{conference_id}/{talk_id}/).
        languages: Language codes to process.
        data_dir: Root data directory.
        transcription_provider: Provider for audio-to-text transcription.
        alignment_provider: Provider for aligning known text to audio.
        force: If True, re-process even if manifest is fresh.

    Returns:
        Path to the processed talk directory.
    """
    return asyncio.run(
        _run_transcribe(talk_dir, languages, data_dir,
                        transcription_provider, alignment_provider, force)
    )


async def _run_transcribe(
    talk_dir: Path,
    languages: list[str],
    data_dir: Path,
    transcription_provider: TranscriptionProvider,
    alignment_provider: AlignmentProvider,
    force: bool,
) -> Path:
    metadata = json.loads((talk_dir / "metadata.json").read_text(encoding="utf-8"))
    talk_id = metadata["talk_id"]
    conference_id = metadata["conference_id"]

    output_dir = data_dir / "processed" / conference_id / talk_id

    for lang in languages:
        lang_raw_dir = talk_dir / lang
        lang_out_dir = output_dir / lang
        audio_path = lang_raw_dir / "audio.mp3"
        text_path = lang_raw_dir / "official_text.txt"
        manifest_path = lang_out_dir / "stage2_manifest.json"

        if not audio_path.exists():
            logger.warning(f"No audio file for {lang}, skipping Stage 2")
            print(f"  ⚠ Stage 2 ({lang}): no audio file, skipping")
            continue

        if not text_path.exists():
            logger.warning(f"No official text for {lang}, skipping Stage 2")
            print(f"  ⚠ Stage 2 ({lang}): no official text, skipping")
            continue

        model_version = f"{transcription_provider.model_name}+{alignment_provider.model_name}"
        input_hashes = {
            "audio_file": hash_file(audio_path),
            "official_text": hash_file(text_path),
            "model_version": hash_string(model_version),
        }

        if not force:
            existing_manifest = read_manifest(manifest_path)
            if existing_manifest and not is_stale(existing_manifest, input_hashes):
                if _all_files_exist(lang_out_dir):
                    logger.info(f"Stage 2 already complete for {talk_id}/{lang}, skipping")
                    print(f"  ✓ Stage 2 ({lang}): already complete, skipping")
                    continue

        lang_out_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Transcribe — discover what was actually spoken
        print(f"  → Stage 2 ({lang}): transcribing audio...")
        transcript = await transcription_provider.transcribe(audio_path, lang)
        transcript.talk_id = talk_id

        transcript_path = lang_out_dir / "transcript.json"
        transcript_path.write_text(
            json.dumps(transcript.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        word_count = sum(len(s.words) for s in transcript.segments)
        logger.info(f"Transcribed {talk_id}/{lang}: {len(transcript.segments)} segments, {word_count} words")

        # Step 2: Align official text against audio
        print(f"  → Stage 2 ({lang}): aligning official text...")
        official_text = text_path.read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in official_text.split("\n\n") if p.strip()]

        aligned_segments = []
        aligned_word_count = 0
        failed_paragraphs = 0

        for i, para in enumerate(paragraphs):
            try:
                para_result = await alignment_provider.align(audio_path, para, lang)
                for seg in para_result.segments:
                    aligned_segments.append(seg)
                    aligned_word_count += len(seg.words)
            except Exception as e:
                logger.warning(f"Alignment failed for paragraph {i} in {lang}: {e}")
                failed_paragraphs += 1

        aligned = transcript.__class__(
            talk_id=talk_id,
            model=alignment_provider.model_name,
            language=lang,
            segments=aligned_segments,
        )

        aligned_path = lang_out_dir / "aligned_official.json"
        aligned_path.write_text(
            json.dumps(aligned.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        if failed_paragraphs:
            logger.warning(f"Aligned {talk_id}/{lang}: {failed_paragraphs}/{len(paragraphs)} paragraphs failed")

        # Write manifest
        manifest = StageManifest(
            stage=2,
            completed_at=datetime.now(timezone.utc),
            input_hashes=input_hashes,
            model_version=model_version,
        )
        write_manifest(manifest_path, manifest)

        status = f"{aligned_word_count} words aligned"
        if failed_paragraphs:
            status += f" ({failed_paragraphs} paragraphs failed)"
        print(f"  ✓ Stage 2 ({lang}): {status}")

    return output_dir


def _all_files_exist(lang_out_dir: Path) -> bool:
    return (
        (lang_out_dir / "transcript.json").exists()
        and (lang_out_dir / "aligned_official.json").exists()
    )
