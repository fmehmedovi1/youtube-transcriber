"""User-facing error categories.

Each maps to a short, readable message shown in the UI. Technical detail
(the original exception) is preserved on the instance and logged, never
shown to the user directly.
"""

from __future__ import annotations

import sys


def _setup_hint() -> str:
    if sys.platform == "win32":
        return "run scripts\\setup_whisper.ps1"
    return "run scripts/setup_whisper.sh"


class TranscriberError(Exception):
    """Base class for all errors the UI knows how to render nicely."""

    user_message = "Something went wrong."

    def __init__(self, detail: str | None = None):
        self.detail = detail
        super().__init__(detail or self.user_message)


class InvalidURLError(TranscriberError):
    user_message = "That doesn't look like a valid YouTube URL or video ID."


class VideoUnavailableError(TranscriberError):
    user_message = "This video is unavailable (private, deleted, or region-locked)."


class TemporaryAccessError(TranscriberError):
    user_message = (
        "YouTube temporarily refused the request. This can happen with rate "
        "limiting — wait a bit and try again. Local Whisper fallback also "
        "needs to reach the public video, so it may be affected too."
    )


class NoCaptionsAvailableError(TranscriberError):
    """Not a failure — just means the caption route has nothing to offer.

    Callers should treat this as a signal to try the local Whisper fallback,
    not as an application error.
    """

    user_message = "No usable YouTube captions found for this video."


class FFmpegNotFoundError(TranscriberError):
    def __init__(self, detail: str | None = None):
        if sys.platform == "win32":
            self.user_message = (
                "ffmpeg is not installed. Run scripts\\setup_whisper.ps1, "
                "or install it yourself and make sure it's on PATH."
            )
        else:
            self.user_message = "ffmpeg is not installed. On macOS run: brew install ffmpeg"
        super().__init__(detail)


class WhisperNotFoundError(TranscriberError):
    def __init__(self, detail: str | None = None):
        self.user_message = f"whisper.cpp is not installed/built. {_setup_hint()} to set it up locally."
        super().__init__(detail)


class WhisperModelMissingError(TranscriberError):
    def __init__(self, detail: str | None = None):
        self.user_message = (
            "The local Whisper model isn't downloaded yet. Use the "
            "\"Download model\" button below, or " + _setup_hint() + "."
        )
        super().__init__(detail)


class AudioDownloadError(TranscriberError):
    user_message = "Downloading audio for this video failed."


class LocalTranscriptionError(TranscriberError):
    user_message = "Local Whisper transcription failed."
