"""YouTubeCaptionProvider: fetch existing YouTube captions, for free.

Isolated behind this adapter so the youtube_transcript_api integration can
change without touching the rest of the pipeline. Built against
youtube-transcript-api 1.x's instance-based API (YouTubeTranscriptApi().list
/ .fetch), not the older static-method interface used in outdated tutorials.
"""

from __future__ import annotations

import logging

from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    YouTubeTranscriptApi,
)
from youtube_transcript_api._transcripts import Transcript, TranscriptList

from .config import PREFERRED_LANGUAGES
from .errors import NoCaptionsAvailableError, TemporaryAccessError, VideoUnavailableError
from .models import SOURCE_YOUTUBE_AUTO, SOURCE_YOUTUBE_MANUAL, TranscriptResult, TranscriptSegment

logger = logging.getLogger(__name__)


class AvailableTranscript:
    """Lightweight description of one selectable transcript, for the UI."""

    def __init__(self, transcript: Transcript):
        self.language = transcript.language
        self.language_code = transcript.language_code
        self.is_generated = transcript.is_generated
        self._transcript = transcript

    def __repr__(self) -> str:
        kind = "auto" if self.is_generated else "manual"
        return f"{self.language} ({self.language_code}, {kind})"


class YouTubeCaptionProvider:
    """Discovers and fetches existing YouTube captions for a video."""

    def __init__(self) -> None:
        self._api = YouTubeTranscriptApi()

    def list_available(self, video_id: str) -> list[AvailableTranscript]:
        """List transcripts YouTube has for this video. Empty if disabled."""
        try:
            transcript_list: TranscriptList = self._api.list(video_id)
        except TranscriptsDisabled:
            logger.info("caption lookup unavailable: transcripts disabled video_id=%s", video_id)
            return []
        except VideoUnavailable as exc:
            logger.info("video unavailable video_id=%s", video_id)
            raise VideoUnavailableError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - network/library errors, treated as transient
            logger.warning("caption lookup transient error video_id=%s err=%s", video_id, exc)
            raise TemporaryAccessError(str(exc)) from exc

        return [AvailableTranscript(t) for t in transcript_list]

    def fetch(
        self, video_id: str, language_code: str | None = None, auto: bool = False
    ) -> TranscriptResult:
        """Fetch a transcript.

        If language_code is given, fetch that exact language. Otherwise
        (auto=True) walk PREFERRED_LANGUAGES, then fall back to whatever is
        available first.
        """
        available = self.list_available(video_id)
        if not available:
            raise NoCaptionsAvailableError("no transcripts listed for this video")

        chosen = self._select(available, language_code, auto)
        try:
            fetched = chosen._transcript.fetch()
        except NoTranscriptFound as exc:
            raise NoCaptionsAvailableError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            logger.warning("caption fetch transient error video_id=%s err=%s", video_id, exc)
            raise TemporaryAccessError(str(exc)) from exc

        segments = [
            TranscriptSegment(start=s.start, duration=s.duration, text=s.text) for s in fetched
        ]
        source = SOURCE_YOUTUBE_AUTO if chosen.is_generated else SOURCE_YOUTUBE_MANUAL
        logger.info(
            "caption source selected video_id=%s lang=%s generated=%s",
            video_id,
            chosen.language_code,
            chosen.is_generated,
        )
        return TranscriptResult(
            video_id=video_id,
            source=source,
            segments=segments,
            language=chosen.language,
            language_code=chosen.language_code,
            is_generated=chosen.is_generated,
        )

    @staticmethod
    def _select(
        available: list[AvailableTranscript], language_code: str | None, auto: bool
    ) -> AvailableTranscript:
        if language_code and not auto:
            for t in available:
                if t.language_code == language_code:
                    return t
            raise NoCaptionsAvailableError(f"no transcript in language {language_code!r}")

        by_code = {t.language_code: t for t in available}
        for preferred in PREFERRED_LANGUAGES:
            if preferred in by_code:
                return by_code[preferred]
            for code, t in by_code.items():
                if code.startswith(preferred):
                    return t

        return available[0]
