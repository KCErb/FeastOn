"""
FeastOn Pipeline CLI

Processes General Conference talks through 8 stages:
1. Ingest    → download text + audio
2. Transcribe → WhisperX timestamped transcription
3. Diff      → official text ↔ transcript differences
4. Segment   → paragraph and sentence boundaries
5. Align     → cross-language alignment
6. Map       → semantic unit graph (main LLM work)
7. Phonetics → pinyin and IPA
8. Package   → consolidated JSON output
"""

import logging
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()


def _resolve_data_dir(cli_option: str | None) -> Path:
    """Resolve data directory from CLI option, env var, or default."""
    if cli_option:
        return Path(cli_option)
    env_dir = os.environ.get("DATA_DIR")
    if env_dir:
        return Path(env_dir)
    # Default: project root's data/ directory
    return Path(__file__).parent.parent.parent / "data"


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """FeastOn Pipeline - Study languages through Conference talks"""
    pass


@cli.command()
@click.argument("talk_id_or_url")
@click.argument("home_lang")
@click.argument("study_lang")
@click.option("--from", "from_stage", type=int, help="Re-run from this stage onward")
@click.option("--only", type=int, help="Run only this stage")
@click.option("--dry-run", is_flag=True, help="Show what would be processed")
@click.option("--data-dir", type=click.Path(), default=None, help="Data directory")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def generate(
    talk_id_or_url: str,
    home_lang: str,
    study_lang: str,
    from_stage: int | None,
    only: int | None,
    dry_run: bool,
    data_dir: str | None,
    verbose: bool,
):
    """Generate all pipeline data for a talk + language pair"""
    if verbose:
        logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

    data_path = _resolve_data_dir(data_dir)
    languages = list(dict.fromkeys([home_lang, study_lang]))  # deduplicate, preserve order

    click.echo(f"FeastOn Pipeline: {talk_id_or_url}")
    click.echo(f"  Languages: {' + '.join(languages)}")
    click.echo(f"  Data dir:  {data_path}")
    click.echo()

    if dry_run:
        click.echo("Dry run — would process stages:")
        _print_stages(from_stage, only)
        return

    # Determine which stages to run
    def should_run(stage_num: int) -> bool:
        if only is not None:
            return stage_num == only
        if from_stage is not None:
            return stage_num >= from_stage
        return True

    # Stage 1: Ingest
    if should_run(1):
        from .providers.church_content_provider import ChurchContentProvider
        from .stages.ingest import run_ingest

        provider = ChurchContentProvider()
        force = from_stage is not None and from_stage <= 1
        try:
            run_ingest(talk_id_or_url, languages, data_path, provider, force=force)
        except Exception as e:
            click.echo(f"  ✗ Stage 1 (Ingest) failed: {e}", err=True)
            sys.exit(1)
    else:
        click.echo("  · Stage 1 (Ingest): skipped")

    # Stages 2-8: not yet implemented
    stage_names = {
        2: "Transcribe",
        3: "Diff",
        4: "Segment",
        5: "Align",
        6: "Map",
        7: "Phonetics",
        8: "Package",
    }
    for stage_num, name in stage_names.items():
        if should_run(stage_num):
            click.echo(f"  · Stage {stage_num} ({name}): not yet implemented")


def _print_stages(from_stage: int | None, only: int | None):
    """Print which stages would run."""
    stages = [
        "1. Ingest",
        "2. Transcribe",
        "3. Diff",
        "4. Segment",
        "5. Align",
        "6. Map",
        "7. Phonetics",
        "8. Package",
    ]
    for i, stage in enumerate(stages, 1):
        if only is not None:
            marker = "→" if i == only else "·"
        elif from_stage is not None:
            marker = "→" if i >= from_stage else "·"
        else:
            marker = "→"
        click.echo(f"  {marker} {stage}")


@cli.command()
@click.argument("talk_id")
@click.argument("home_lang")
@click.argument("study_lang")
@click.option("--data-dir", type=click.Path(), default=None, help="Data directory")
def status(talk_id: str, home_lang: str, study_lang: str, data_dir: str | None):
    """Show processing status for a talk"""
    from .manifest import read_manifest
    from .talk_url import parse_talk_reference

    data_path = _resolve_data_dir(data_dir)

    try:
        ref = parse_talk_reference(talk_id)
    except ValueError:
        click.echo(f"Error: Could not parse talk reference: {talk_id}", err=True)
        sys.exit(1)

    click.echo(f"Status: {ref.talk_id} ({home_lang} ↔ {study_lang})")
    click.echo()

    # Check Stage 1
    raw_dir = data_path / "raw" / ref.conference_id / ref.talk_id
    manifest = read_manifest(raw_dir / "stage1_manifest.json")
    if manifest:
        click.echo(f"  1. Ingest        [complete] ({manifest.completed_at.strftime('%Y-%m-%d %H:%M')})")
    else:
        click.echo(f"  1. Ingest        [not started]")

    # Stages 2-8: check for manifests
    stage_names = {
        2: "Transcribe",
        3: "Diff",
        4: "Segment",
        5: "Align",
        6: "Map",
        7: "Phonetics",
        8: "Package",
    }
    for stage_num, name in stage_names.items():
        click.echo(f"  {stage_num}. {name:14s} [not started]")


@cli.command()
@click.argument("talk_id")
@click.argument("home_lang")
@click.argument("study_lang")
@click.option("--stage", type=int, required=True, help="Stage to invalidate")
@click.option("--data-dir", type=click.Path(), default=None, help="Data directory")
def invalidate(talk_id: str, home_lang: str, study_lang: str, stage: int, data_dir: str | None):
    """Invalidate a stage's output (mark as stale)"""
    if stage < 1 or stage > 8:
        click.echo("Error: Stage must be between 1 and 8", err=True)
        sys.exit(1)

    from .talk_url import parse_talk_reference

    data_path = _resolve_data_dir(data_dir)

    try:
        ref = parse_talk_reference(talk_id)
    except ValueError:
        click.echo(f"Error: Could not parse talk reference: {talk_id}", err=True)
        sys.exit(1)

    if stage == 1:
        manifest_path = data_path / "raw" / ref.conference_id / ref.talk_id / "stage1_manifest.json"
        if manifest_path.exists():
            manifest_path.unlink()
            click.echo(f"✓ Stage {stage} invalidated for {ref.talk_id}")
        else:
            click.echo(f"Stage {stage} has no manifest to invalidate")
    else:
        click.echo(f"Invalidating stage {stage} for {ref.talk_id} (not yet implemented)")


if __name__ == "__main__":
    cli()
