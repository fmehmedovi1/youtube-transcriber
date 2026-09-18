"""Executable-lookup behavior for the native dependencies (whisper.cpp,
ffmpeg): configured path, dev-build candidate names, and a packaged
`bin/` directory next to the executable.
"""

from __future__ import annotations

from src.youtube_transcriber import audio, whisper_local
from src.youtube_transcriber.config import Config


def test_get_whisper_executable_finds_configured_path(tmp_path):
    binary = tmp_path / "whisper-cli"
    binary.touch()
    cfg = Config(whisper_cpp_path=binary)
    assert whisper_local.get_whisper_executable(cfg) == binary


def test_get_whisper_executable_falls_back_to_old_name(tmp_path):
    configured = tmp_path / "whisper-cli"  # does not exist
    old_name = tmp_path / "main"
    old_name.touch()
    cfg = Config(whisper_cpp_path=configured)
    assert whisper_local.get_whisper_executable(cfg) == old_name


def test_get_whisper_executable_finds_bundled_bin_next_to_app(tmp_path, monkeypatch):
    configured = tmp_path / "nowhere" / "whisper-cli"  # parent doesn't exist
    cfg = Config(whisper_cpp_path=configured)

    app_root = tmp_path / "packaged-app"
    bundled = app_root / "bin" / "whisper-cli"
    bundled.parent.mkdir(parents=True)
    bundled.touch()

    monkeypatch.setattr(whisper_local, "app_dir", lambda: app_root)
    monkeypatch.setattr(whisper_local, "exe_suffix", lambda: "")

    assert whisper_local.get_whisper_executable(cfg) == bundled


def test_get_whisper_executable_none_when_nothing_found(tmp_path, monkeypatch):
    cfg = Config(whisper_cpp_path=tmp_path / "whisper-cli")
    monkeypatch.setattr(whisper_local, "app_dir", lambda: tmp_path / "no-bin-here")
    assert whisper_local.get_whisper_executable(cfg) is None


def test_get_ffmpeg_executable_prefers_bundled_over_path(tmp_path, monkeypatch):
    app_root = tmp_path / "packaged-app"
    bundled = app_root / "bin" / "ffmpeg"
    bundled.parent.mkdir(parents=True)
    bundled.touch()

    monkeypatch.setattr(audio, "app_dir", lambda: app_root)
    monkeypatch.setattr(audio, "exe_suffix", lambda: "")
    monkeypatch.setattr(audio.shutil, "which", lambda name: "/usr/bin/ffmpeg")

    assert audio.get_ffmpeg_executable() == bundled


def test_get_ffmpeg_executable_falls_back_to_path(tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "app_dir", lambda: tmp_path / "no-bin-here")
    monkeypatch.setattr(audio.shutil, "which", lambda name: "/usr/bin/ffmpeg")

    result = audio.get_ffmpeg_executable()
    assert result is not None
    assert str(result) == "/usr/bin/ffmpeg"


def test_get_ffmpeg_executable_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(audio, "app_dir", lambda: tmp_path / "no-bin-here")
    monkeypatch.setattr(audio.shutil, "which", lambda name: None)
    assert audio.get_ffmpeg_executable() is None
