"""Fallback routing tests: captions available -> Whisper never runs, and
vice versa. Also verifies temp file cleanup after success and failure.

All external boundaries (caption API, yt-dlp, ffmpeg, whisper.cpp) are
mocked so these tests never touch the network or a real subprocess.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.youtube_transcriber.config import Config
from src.youtube_transcriber.errors import LocalTranscriptionError, NoCaptionsAvailableError
from src.youtube_transcriber.models import (
    SOURCE_LOCAL_WHISPER,
    SOURCE_YOUTUBE_MANUAL,
    TranscriptResult,
    TranscriptSegment,
)
from src.youtube_transcriber.transcript import TranscriptPipeline


@pytest.fixture
def temp_config():
    temp_dir = Path(tempfile.mkdtemp())
    yield Config(temp_dir=temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def _fake_caption_result():
    return TranscriptResult(
        video_id="vid1",
        source=SOURCE_YOUTUBE_MANUAL,
        segments=[TranscriptSegment(start=0.0, duration=1.0, text="hi")],
        language="English",
        language_code="en",
        is_generated=False,
    )


def _fake_whisper_result():
    return TranscriptResult(
        video_id="",
        source=SOURCE_LOCAL_WHISPER,
        segments=[TranscriptSegment(start=0.0, duration=1.0, text="hi")],
        whisper_model="small",
    )


def test_captions_available_whisper_not_called(temp_config, monkeypatch):
    caption_provider = MagicMock()
    caption_provider.fetch.return_value = _fake_caption_result()
    audio_provider = MagicMock()
    audio_provider.fetch_metadata.return_value = None
    whisper = MagicMock()
    whisper_factory = MagicMock(return_value=whisper)

    monkeypatch.setattr("src.youtube_transcriber.transcript.require_ffmpeg", MagicMock())

    pipeline = TranscriptPipeline(
        config=temp_config,
        caption_provider=caption_provider,
        audio_provider=audio_provider,
        whisper_factory=whisper_factory,
    )

    result = pipeline.run("vid1")

    assert result.source == SOURCE_YOUTUBE_MANUAL
    audio_provider.download_audio.assert_not_called()
    whisper_factory.assert_not_called()
    whisper.transcribe.assert_not_called()


def test_captions_unavailable_whisper_called(temp_config, monkeypatch):
    caption_provider = MagicMock()
    caption_provider.fetch.side_effect = NoCaptionsAvailableError("none")
    audio_provider = MagicMock()
    audio_provider.fetch_metadata.return_value = None

    downloaded_path = temp_config.temp_dir / "download-marker.webm"

    def fake_download(video_id, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "audio.webm"
        path.write_bytes(b"fake audio")
        return path

    audio_provider.download_audio.side_effect = fake_download

    whisper = MagicMock()
    whisper.transcribe.return_value = _fake_whisper_result()
    whisper_factory = MagicMock(return_value=whisper)

    monkeypatch.setattr("src.youtube_transcriber.transcript.require_ffmpeg", MagicMock())

    def fake_convert(source, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"fake wav")
        return dest

    monkeypatch.setattr("src.youtube_transcriber.transcript.convert_to_whisper_wav", fake_convert)

    pipeline = TranscriptPipeline(
        config=temp_config,
        caption_provider=caption_provider,
        audio_provider=audio_provider,
        whisper_factory=whisper_factory,
    )

    result = pipeline.run("vid2")

    assert result.source == SOURCE_LOCAL_WHISPER
    audio_provider.download_audio.assert_called_once()
    whisper.transcribe.assert_called_once()
    assert result.video_id == "vid2"


def test_temp_files_cleaned_up_after_success(temp_config, monkeypatch):
    caption_provider = MagicMock()
    caption_provider.fetch.side_effect = NoCaptionsAvailableError("none")
    audio_provider = MagicMock()
    audio_provider.fetch_metadata.return_value = None

    job_dirs: list[Path] = []

    def fake_download(video_id, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        job_dirs.append(dest_dir)
        path = dest_dir / "audio.webm"
        path.write_bytes(b"fake audio")
        return path

    audio_provider.download_audio.side_effect = fake_download

    whisper = MagicMock()
    whisper.transcribe.return_value = _fake_whisper_result()
    whisper_factory = MagicMock(return_value=whisper)

    monkeypatch.setattr("src.youtube_transcriber.transcript.require_ffmpeg", MagicMock())

    def fake_convert(source, dest):
        dest.write_bytes(b"fake wav")
        return dest

    monkeypatch.setattr("src.youtube_transcriber.transcript.convert_to_whisper_wav", fake_convert)

    pipeline = TranscriptPipeline(
        config=temp_config,
        caption_provider=caption_provider,
        audio_provider=audio_provider,
        whisper_factory=whisper_factory,
    )

    pipeline.run("vid3")

    assert not job_dirs[0].exists()


def test_temp_files_cleaned_up_after_transcription_error(temp_config, monkeypatch):
    caption_provider = MagicMock()
    caption_provider.fetch.side_effect = NoCaptionsAvailableError("none")
    audio_provider = MagicMock()
    audio_provider.fetch_metadata.return_value = None

    job_dirs: list[Path] = []

    def fake_download(video_id, dest_dir):
        dest_dir.mkdir(parents=True, exist_ok=True)
        job_dirs.append(dest_dir)
        path = dest_dir / "audio.webm"
        path.write_bytes(b"fake audio")
        return path

    audio_provider.download_audio.side_effect = fake_download

    whisper = MagicMock()
    whisper.transcribe.side_effect = LocalTranscriptionError("boom")
    whisper_factory = MagicMock(return_value=whisper)

    monkeypatch.setattr("src.youtube_transcriber.transcript.require_ffmpeg", MagicMock())

    def fake_convert(source, dest):
        dest.write_bytes(b"fake wav")
        return dest

    monkeypatch.setattr("src.youtube_transcriber.transcript.convert_to_whisper_wav", fake_convert)

    pipeline = TranscriptPipeline(
        config=temp_config,
        caption_provider=caption_provider,
        audio_provider=audio_provider,
        whisper_factory=whisper_factory,
    )

    with pytest.raises(LocalTranscriptionError):
        pipeline.run("vid4")

    assert not job_dirs[0].exists()
