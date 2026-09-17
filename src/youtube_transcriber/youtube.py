"""YouTube URL parsing. Single place where video IDs get extracted."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from .errors import InvalidURLError

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}


def _looks_like_video_id(candidate: str) -> bool:
    return bool(_VIDEO_ID_RE.match(candidate))


def extract_video_id(url_or_id: str) -> str:
    """Extract an 11-char YouTube video ID from a URL or raw ID.

    Supports watch/shorts/embed URLs, youtu.be short links, and raw IDs.
    Raises InvalidURLError when nothing recognizable is found.
    """
    if not url_or_id or not url_or_id.strip():
        raise InvalidURLError("empty input")

    candidate = url_or_id.strip()

    # Raw video ID, no URL structure at all.
    if _looks_like_video_id(candidate) and "/" not in candidate and "." not in candidate:
        return candidate

    if "://" not in candidate:
        candidate = "https://" + candidate

    try:
        parsed = urlparse(candidate)
    except ValueError as exc:
        raise InvalidURLError(str(exc)) from exc

    host = parsed.netloc.lower()
    path = parsed.path

    if host == "youtu.be":
        video_id = path.lstrip("/").split("/")[0]
        if _looks_like_video_id(video_id):
            return video_id
        raise InvalidURLError(f"unrecognized youtu.be path: {path!r}")

    if host in _HOSTS:
        if path == "/watch":
            query = parse_qs(parsed.query)
            values = query.get("v")
            if values and _looks_like_video_id(values[0]):
                return values[0]
            raise InvalidURLError("missing or invalid 'v' query parameter")

        for prefix in ("/shorts/", "/embed/", "/live/", "/v/"):
            if path.startswith(prefix):
                video_id = path[len(prefix):].split("/")[0]
                if _looks_like_video_id(video_id):
                    return video_id
                raise InvalidURLError(f"unrecognized path segment after {prefix!r}")

        raise InvalidURLError(f"unrecognized YouTube URL path: {path!r}")

    raise InvalidURLError(f"not a YouTube URL: {url_or_id!r}")
