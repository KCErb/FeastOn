"""
Real ContentProvider implementation that fetches talk data from churchofjesuschrist.org.

Scrapes talk pages for text, metadata, and audio URLs.
Rate-limited to be respectful of the Church website.
"""

import asyncio
import base64
import json
import logging
import re
import time

import requests
from bs4 import BeautifulSoup, Tag

from .content_provider import ContentProvider, TalkMetadata, TalkTextResult

logger = logging.getLogger(__name__)


class ChurchContentProvider(ContentProvider):
    """Fetches Conference talk content from churchofjesuschrist.org."""

    def __init__(self, delay_seconds: float = 1.5, timeout: int = 30):
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self._last_request_time: float = 0.0
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "FeastOn/0.1.0 (language study tool)",
                "Accept-Language": "en",
            }
        )

    def _rate_limit(self) -> None:
        """Enforce minimum delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)
        self._last_request_time = time.time()

    def _fetch_page(self, url: str, lang: str) -> BeautifulSoup:
        """Fetch a page and return parsed HTML. Retries up to 3 times."""
        self._rate_limit()
        full_url = f"{url}?lang={lang}" if "?" not in url else url

        for attempt in range(3):
            try:
                resp = self._session.get(full_url, timeout=self.timeout)
                resp.raise_for_status()
                # Force UTF-8 — the site is UTF-8 but doesn't always declare it,
                # causing requests to default to ISO-8859-1
                resp.encoding = "utf-8"
                return BeautifulSoup(resp.text, "lxml")
            except requests.RequestException as e:
                if attempt == 2:
                    raise
                wait = 2 ** (attempt + 1)
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)

    def _extract_body_html(self, soup: BeautifulSoup) -> str:
        """Extract the raw HTML of the body-block div."""
        body = soup.select_one("div.body-block")
        if not body:
            raise ValueError("Could not find div.body-block in page HTML")
        return str(body)

    def _extract_plain_text(self, soup: BeautifulSoup) -> str:
        """Extract clean plain text from body-block, paragraphs separated by \\n\\n."""
        body = soup.select_one("div.body-block")
        if not body:
            raise ValueError("Could not find div.body-block in page HTML")

        # Work on a copy so we don't mutate the original
        body = BeautifulSoup(str(body), "lxml").select_one("div.body-block")

        # Remove footnote markers
        for el in body.select("a.note-ref"):
            el.decompose()
        for el in body.select("sup.marker"):
            el.decompose()

        # Extract text from paragraphs and section headers
        paragraphs = []
        for el in body.find_all(["p", "h2", "h3"]):
            # Skip if inside footer.notes
            if el.find_parent("footer"):
                continue
            text = el.get_text(separator=" ", strip=True)
            if text:
                paragraphs.append(text)

        return "\n\n".join(paragraphs)

    def _extract_audio_url(self, soup: BeautifulSoup, lang: str, slug: str) -> str | None:
        """Extract MP3 audio URL from __INITIAL_STATE__ (base64-encoded JSON)."""
        for script in soup.find_all("script"):
            script_text = script.string or ""
            if "__INITIAL_STATE__" not in script_text:
                continue

            # Extract the base64-encoded value
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*"([^"]+)"', script_text)
            if not match:
                # Try without quotes (raw JSON assignment)
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.+\})', script_text, re.DOTALL)
                if match:
                    try:
                        state = json.loads(match.group(1))
                        return self._find_audio_in_state(state, lang, slug)
                    except json.JSONDecodeError:
                        pass
                continue

            try:
                decoded = base64.b64decode(match.group(1)).decode("utf-8")
                state = json.loads(decoded)
                return self._find_audio_in_state(state, lang, slug)
            except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to decode __INITIAL_STATE__: {e}")
                continue

        logger.warning(f"Could not find audio URL for {lang}/{slug}")
        return None

    def _find_audio_in_state(self, state: dict, lang: str, slug: str) -> str | None:
        """Navigate the __INITIAL_STATE__ JSON to find the audio mediaUrl."""
        # Try the content store path
        content_store = state.get("reader", {}).get("contentStore", {})
        # The key pattern varies; try common formats
        for key_pattern in [
            f"/{lang}/general-conference/{slug}",
            slug,
        ]:
            for key, value in content_store.items():
                if key_pattern in key:
                    audio_list = value.get("meta", {}).get("audio", [])
                    if audio_list and isinstance(audio_list, list):
                        url = audio_list[0].get("mediaUrl")
                        if url:
                            return url

        # Fallback: search entire JSON for mediaUrl pattern
        json_str = json.dumps(state)
        match = re.search(r'"mediaUrl"\s*:\s*"(https://[^"]+\.mp3)"', json_str)
        if match:
            return match.group(1)

        return None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the talk title from the page."""
        h1 = soup.select_one("article#main h1")
        if h1:
            return h1.get_text(strip=True)
        # Fallback
        h1 = soup.select_one("h1")
        return h1.get_text(strip=True) if h1 else "Unknown Title"

    def _extract_speaker(self, soup: BeautifulSoup) -> str:
        """Extract the speaker name."""
        author = soup.select_one("p.author-name")
        if author:
            name = author.get_text(strip=True)
            # Remove "By " prefix if present
            if name.startswith("By "):
                name = name[3:]
            return name
        return "Unknown Speaker"

    def _extract_session(self, soup: BeautifulSoup, talk_slug: str) -> str:
        """Extract the session name from the TOC nav sidebar."""
        nav = soup.select_one("nav")
        if not nav:
            return "Unknown Session"

        # Find the link whose href contains our talk slug
        talk_link = nav.select_one(f'a[href*="/{talk_slug}"]')
        if not talk_link:
            return "Unknown Session"

        # Walk up: talk_link -> li -> ul -> li (session container)
        parent_ul = talk_link.find_parent("ul")
        if not parent_ul:
            return "Unknown Session"

        parent_li = parent_ul.find_parent("li")
        if not parent_li:
            return "Unknown Session"

        # The session link is the first <a> child of the session <li>
        session_link = parent_li.find("a", recursive=False)
        if session_link:
            text = session_link.get_text(strip=True)
            if text:
                return text

        return "Unknown Session"

    async def fetch_talk_metadata(self, url: str, languages: list[str]) -> TalkMetadata:
        """Fetch metadata by loading each language page."""
        from ..talk_url import parse_talk_reference

        ref = parse_talk_reference(url)
        titles = {}
        source_urls = {}
        speaker = "Unknown Speaker"
        session = "Unknown Session"

        for lang in languages:
            soup = await asyncio.to_thread(self._fetch_page, ref.base_url, lang)
            titles[lang] = self._extract_title(soup)
            source_urls[lang] = f"{ref.base_url}?lang={lang}"

            # Use English page for speaker/session (most reliable)
            if lang == "eng" or speaker == "Unknown Speaker":
                speaker = self._extract_speaker(soup)
            if lang == "eng" or session == "Unknown Session":
                session = self._extract_session(soup, ref.talk_slug)

        return TalkMetadata(
            talk_id=ref.talk_id,
            conference_id=ref.conference_id,
            session=session,
            speaker=speaker,
            title=titles,
            source_urls=source_urls,
            languages_available=languages,
        )

    async def fetch_talk_text(self, url: str, language: str) -> TalkTextResult:
        """Fetch talk text as both HTML and plain text."""
        soup = await asyncio.to_thread(self._fetch_page, url, language)
        html = self._extract_body_html(soup)
        plain_text = self._extract_plain_text(soup)
        return TalkTextResult(html=html, plain_text=plain_text)

    async def fetch_talk_audio(self, url: str, language: str) -> bytes:
        """Fetch the MP3 audio data for a talk."""
        # First, load the page to find the audio URL
        soup = await asyncio.to_thread(self._fetch_page, url, language)

        # Extract slug from URL for content store lookup
        slug = url.rstrip("/").split("/")[-1].split("?")[0]
        audio_url = self._extract_audio_url(soup, language, slug)

        if not audio_url:
            raise ValueError(f"Could not find audio URL for {language} at {url}")

        # Download the audio file
        self._rate_limit()
        logger.info(f"Downloading audio: {audio_url}")
        resp = await asyncio.to_thread(
            self._session.get, audio_url, timeout=120  # longer timeout for audio
        )
        resp.raise_for_status()
        return resp.content
