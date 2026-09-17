"""User-facing error categories.

Each maps to a short, readable message shown in the UI. Technical detail
(the original exception) is preserved on the instance and logged, never
shown to the user directly.
"""

from __future__ import annotations


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
    user_message = (
        "ffmpeg is not installed. On macOS run: brew install ffmpeg"
    )


class WhisperNotFoundError(TranscriberError):
    user_message = (
        "whisper.cpp is not installed/built. Run scripts/setup_whisper.sh "
        "to set it up locally."
    )


class WhisperModelMissingError(TranscriberError):
    user_message = (
        "The configured local Whisper model is missing. Run "
        "scripts/setup_whisper.sh to download it."
    )


class AudioDownloadError(TranscriberError):
    user_message = "Downloading audio for this video failed."


class LocalTranscriptionError(TranscriberError):
    user_message = "Local Whisper transcription failed."
