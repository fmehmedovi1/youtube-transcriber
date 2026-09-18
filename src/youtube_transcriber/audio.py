"""YouTubeAudioProvider: metadata + audio-only download via yt-dlp.

Isolated adapter so yt-dlp's options/API can evolve without touching the
rest of the pipeline. Never downloads full video when audio suffices.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

import yt_dlp

from .errors import AudioDownloadError, FFmpegNotFoundError, VideoUnavailableError
from .models import VideoMetadata
from .runtime import app_dir, exe_suffix

logger = logging.getLogger(__name__)

WHISPER_SAMPLE_RATE = 16000


def get_ffmpeg_executable() -> Path | str | None:
    """Locate ffmpeg: a `bin/ffmpeg.exe` shipped next to a packaged build
    first, then PATH (the normal dev-mode / brew-installed case).

    PATH hits are returned exactly as `shutil.which` reports them, not
    re-parsed through `Path` — that would renormalize separators and
    mangle the string on Windows.
    """
    bundled = app_dir() / "bin" / f"ffmpeg{exe_suffix()}"
    if bundled.exists():
        return bundled
    return shutil.which("ffmpeg")


def check_ffmpeg_installed() -> bool:
    return get_ffmpeg_executable() is not None


def require_ffmpeg() -> None:
    if not check_ffmpeg_installed():
        raise FFmpegNotFoundError("ffmpeg not found on PATH or bundled bin/")


class YouTubeAudioProvider:
    """Fetches metadata and audio-only downloads for a video."""

    def fetch_metadata(self, video_id: str) -> VideoMetadata | None:
        """Best-effort metadata fetch. Returns None on failure rather than
        raising, since metadata is not required for transcript success.
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:  # noqa: BLE001
            logger.warning("metadata fetch failed video_id=%s err=%s", video_id, exc)
            return None

        logger.info("metadata fetched video_id=%s", video_id)
        return VideoMetadata(
            video_id=video_id,
            title=info.get("title"),
            channel=info.get("channel") or info.get("uploader"),
            duration_seconds=info.get("duration"),
        )

    def download_audio(self, video_id: str, dest_dir: Path) -> Path:
        """Download the smallest reasonable audio-only stream.

        Returns the path to the downloaded audio file (original container,
        not yet converted for whisper.cpp).
        """
        url = f"https://www.youtube.com/watch?v={video_id}"
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_template = str(dest_dir / f"{video_id}.%(ext)s")

        opts = {
            "format": "bestaudio/best",
            "outtmpl": out_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "retries": 2,
        }

        logger.info("audio download started video_id=%s", video_id)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
        except yt_dlp.utils.DownloadError as exc:
            message = str(exc).lower()
            if "private" in message or "unavailable" in message or "removed" in message:
                raise VideoUnavailableError(str(exc)) from exc
            raise AudioDownloadError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise AudioDownloadError(str(exc)) from exc

        path = Path(filename)
        if not path.exists():
            raise AudioDownloadError(f"expected downloaded file not found: {path}")
        return path


def convert_to_whisper_wav(source: Path, dest: Path) -> Path:
    """Convert an audio file to 16kHz mono 16-bit PCM WAV, as whisper.cpp needs."""
    require_ffmpeg()
    dest.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_executable()
    assert ffmpeg_bin is not None  # guaranteed by require_ffmpeg above
    cmd = [
        str(ffmpeg_bin),
        "-y",
        "-i",
        str(source),
        "-ar",
        str(WHISPER_SAMPLE_RATE),
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    logger.info("audio conversion completed source=%s dest=%s", source.name, dest.name)
    if result.returncode != 0 or not dest.exists():
        raise AudioDownloadError(f"ffmpeg conversion failed: {result.stderr[-500:]}")
    return dest
