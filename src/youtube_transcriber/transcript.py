"""Pipeline orchestration: captions first, local Whisper only if needed.

Fallback routing is deliberately narrow. We fall back to Whisper only when
captions are genuinely absent (NoCaptionsAvailableError) — not on arbitrary
exceptions. Video-unavailable and transient-access errors propagate as
themselves so the UI can show the right message, and programming errors are
never silently swallowed into a Whisper run.
"""

from __future__ import annotations

import logging
import shutil
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from .audio import YouTubeAudioProvider, convert_to_whisper_wav, require_ffmpeg
from .captions import YouTubeCaptionProvider
from .config import CONFIG, Config
from .errors import NoCaptionsAvailableError
from .models import TranscriptResult, VideoMetadata
from .whisper_local import LocalWhisperTranscriber

logger = logging.getLogger(__name__)

ProgressFn = Callable[[str], None]


def _noop_progress(_message: str) -> None:
    return None


class TranscriptPipeline:
    def __init__(
        self,
        config: Config = CONFIG,
        caption_provider: YouTubeCaptionProvider | None = None,
        audio_provider: YouTubeAudioProvider | None = None,
        whisper_factory: Callable[[str], LocalWhisperTranscriber] | None = None,
    ):
        self.config = config
        self.captions = caption_provider or YouTubeCaptionProvider()
        self.audio = audio_provider or YouTubeAudioProvider()
        self.whisper_factory = whisper_factory or (
            lambda model_name: LocalWhisperTranscriber(model_name=model_name, config=config)
        )

    def get_metadata(self, video_id: str) -> VideoMetadata | None:
        return self.audio.fetch_metadata(video_id)

    def run(
        self,
        video_id: str,
        language_code: str | None = None,
        auto_language: bool = True,
        whisper_model: str | None = None,
        on_progress: ProgressFn = _noop_progress,
    ) -> TranscriptResult:
        on_progress("Checking YouTube captions...")
        try:
            result = self.captions.fetch(video_id, language_code=language_code, auto=auto_language)
            logger.info("caption source selected video_id=%s", video_id)
            return self._attach_metadata(result, video_id)
        except NoCaptionsAvailableError:
            logger.info("caption lookup unavailable, falling back video_id=%s", video_id)
            on_progress("No usable YouTube captions found.")
            on_progress("Preparing local transcription...")

        # Fall back to local Whisper. Only NoCaptionsAvailableError reaches
        # here; VideoUnavailableError / TemporaryAccessError propagate up.
        require_ffmpeg()
        transcriber = self.whisper_factory(whisper_model or self.config.default_whisper_model)
        transcriber.check_ready()

        work_dir = self.config.temp_dir / f"job-{uuid.uuid4().hex[:12]}"
        raw_audio_path: Path | None = None
        wav_path: Path | None = None
        try:
            on_progress("Downloading audio...")
            raw_audio_path = self.audio.download_audio(video_id, work_dir)

            on_progress("Converting audio...")
            wav_path = work_dir / "audio.wav"
            convert_to_whisper_wav(raw_audio_path, wav_path)

            on_progress("Transcribing locally with Whisper — no paid API used...")
            start = time.monotonic()
            result = transcriber.transcribe(wav_path)
            elapsed = time.monotonic() - start
            logger.info("whisper transcription finished video_id=%s elapsed=%.1fs", video_id, elapsed)

            result.video_id = video_id
            return self._attach_metadata(result, video_id)
        finally:
            if work_dir.exists():
                shutil.rmtree(work_dir, ignore_errors=True)
                logger.info("temporary files cleaned video_id=%s dir=%s", video_id, work_dir)

    def _attach_metadata(self, result: TranscriptResult, video_id: str) -> TranscriptResult:
        metadata = self.get_metadata(video_id)
        if metadata is not None:
            result.title = result.title or metadata.title
            result.metadata = metadata
        return result
