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

import click
from pathlib import Path
import sys


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
def generate(talk_id_or_url: str, home_lang: str, study_lang: str, from_stage: int | None, only: int | None, dry_run: bool):
    """Generate all pipeline data for a talk + language pair"""
    click.echo(f"feaston generate: {talk_id_or_url} ({home_lang} → {study_lang})")

    if from_stage:
        click.echo(f"  Re-running from stage {from_stage}")
    if only:
        click.echo(f"  Running only stage {only}")
    if dry_run:
        click.echo("  (dry run mode)")

    click.echo("\nPipeline stages:")
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
    for stage in stages:
        click.echo(f"  {stage}")

    click.echo("\n✓ Pipeline skeleton ready (stages not yet implemented)")


@cli.command()
@click.argument("talk_id")
@click.argument("home_lang")
@click.argument("study_lang")
def status(talk_id: str, home_lang: str, study_lang: str):
    """Show processing status for a talk"""
    click.echo(f"Status: {talk_id} ({home_lang} ↔ {study_lang})")
    click.echo("\nStages:")
    stages = [
        ("1. Ingest", "not started"),
        ("2. Transcribe", "not started"),
        ("3. Diff", "not started"),
        ("4. Segment", "not started"),
        ("5. Align", "not started"),
        ("6. Map", "not started"),
        ("7. Phonetics", "not started"),
        ("8. Package", "not started"),
    ]
    for stage, status_text in stages:
        click.echo(f"  {stage:20s} [{status_text}]")


@cli.command()
@click.argument("talk_id")
@click.argument("home_lang")
@click.argument("study_lang")
@click.option("--stage", type=int, required=True, help="Stage to invalidate")
def invalidate(talk_id: str, home_lang: str, study_lang: str, stage: int):
    """Invalidate a stage's output (mark as stale)"""
    if stage < 1 or stage > 8:
        click.echo(f"Error: Stage must be between 1 and 8", err=True)
        sys.exit(1)

    click.echo(f"Invalidating stage {stage} for {talk_id} ({home_lang} ↔ {study_lang})")
    click.echo("✓ Stage marked as stale (staleness tracking not yet implemented)")


if __name__ == "__main__":
    cli()
