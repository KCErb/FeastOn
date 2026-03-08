"""
Stage manifest tracking for idempotency and staleness detection.

Each stage writes a manifest alongside its output with:
- Completion timestamp
- Input file hashes
- Prompt version (for LLM stages)

On re-run, the pipeline checks manifests to determine if re-processing is needed.
"""

from pathlib import Path
from pydantic import BaseModel
from datetime import datetime
import hashlib
import json


class StageManifest(BaseModel):
    """Manifest for a completed pipeline stage"""
    stage: int
    completed_at: datetime
    input_hashes: dict[str, str]  # {input_name: hash}
    prompt_version: str | None = None  # for LLM stages
    model_version: str | None = None  # for Whisper stages


def hash_file(path: Path) -> str:
    """Compute SHA256 hash of a file"""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def hash_string(text: str) -> str:
    """Compute SHA256 hash of a string"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_manifest(path: Path, manifest: StageManifest) -> None:
    """Write a manifest to disk"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest.model_dump(mode="json"), f, indent=2, default=str)


def read_manifest(path: Path) -> StageManifest | None:
    """Read a manifest from disk, or None if not found"""
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return StageManifest(**data)


def is_stale(manifest: StageManifest, current_input_hashes: dict[str, str]) -> bool:
    """
    Check if a stage's output is stale.

    Returns True if any input hash has changed.
    """
    for input_name, current_hash in current_input_hashes.items():
        if manifest.input_hashes.get(input_name) != current_hash:
            return True
    return False
