"""
URL parsing utilities for Church of Jesus Christ General Conference talks.

Handles bidirectional mapping between:
- Full URLs: https://www.churchofjesuschrist.org/study/general-conference/2025/10/58oaks?lang=eng
- Talk IDs: 2025-10-58oaks
- Components: conference_id="2025-10", talk_slug="58oaks"
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

BASE_URL = "https://www.churchofjesuschrist.org/study/general-conference"


@dataclass
class TalkReference:
    """Parsed reference to a specific talk."""

    conference_id: str  # e.g., "2025-10"
    talk_slug: str  # e.g., "58oaks"
    talk_id: str  # e.g., "2025-10-58oaks"
    base_url: str  # URL without lang param


def parse_talk_reference(talk_id_or_url: str) -> TalkReference:
    """
    Parse a talk URL or talk ID into a TalkReference.

    Accepts:
      - Full URL: https://www.churchofjesuschrist.org/study/general-conference/2025/10/58oaks?lang=eng
      - Talk ID: 2025-10-58oaks

    Returns: TalkReference with all fields populated.
    Raises: ValueError if the input cannot be parsed.
    """
    if talk_id_or_url.startswith("http"):
        return _parse_url(talk_id_or_url)
    else:
        return _parse_talk_id(talk_id_or_url)


def _parse_url(url: str) -> TalkReference:
    """Parse a full Church website URL."""
    parsed = urlparse(url)
    # Path: /study/general-conference/{year}/{month}/{slug}
    parts = parsed.path.strip("/").split("/")

    if len(parts) < 5 or parts[0] != "study" or parts[1] != "general-conference":
        raise ValueError(
            f"URL does not match expected pattern "
            f"(/study/general-conference/YEAR/MONTH/SLUG): {url}"
        )

    year = parts[2]
    month = parts[3]
    slug = parts[4]

    if not re.match(r"^\d{4}$", year) or month not in ("04", "10"):
        raise ValueError(f"Invalid conference year/month in URL: {year}/{month}")

    conference_id = f"{year}-{month}"
    talk_id = f"{conference_id}-{slug}"
    base_url = f"{BASE_URL}/{year}/{month}/{slug}"

    return TalkReference(
        conference_id=conference_id,
        talk_slug=slug,
        talk_id=talk_id,
        base_url=base_url,
    )


def _parse_talk_id(talk_id: str) -> TalkReference:
    """Parse a talk ID like '2025-10-58oaks'."""
    match = re.match(r"^(\d{4})-(04|10)-(.+)$", talk_id)
    if not match:
        raise ValueError(
            f"Talk ID must be in format YYYY-MM-slug (e.g., 2025-10-58oaks): {talk_id}"
        )

    year, month, slug = match.groups()
    conference_id = f"{year}-{month}"
    base_url = f"{BASE_URL}/{year}/{month}/{slug}"

    return TalkReference(
        conference_id=conference_id,
        talk_slug=slug,
        talk_id=talk_id,
        base_url=base_url,
    )


def make_talk_url(conference_id: str, talk_slug: str, lang: str) -> str:
    """Construct a talk URL from components."""
    year, month = conference_id.split("-")
    return f"{BASE_URL}/{year}/{month}/{talk_slug}?lang={lang}"


def make_conference_url(conference_id: str, lang: str) -> str:
    """Construct a conference index URL."""
    year, month = conference_id.split("-")
    return f"{BASE_URL}/{year}/{month}?lang={lang}"
