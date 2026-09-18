"""Tests for the centralized PyInstaller path-resolution helpers.

These never require PyInstaller itself — they just simulate frozen mode by
monkeypatching sys.frozen / sys._MEIPASS / sys.platform, the same
attributes the real PyInstaller bootloader sets.
"""

from __future__ import annotations

from pathlib import Path

from src.youtube_transcriber import runtime


def test_is_frozen_false_in_dev(monkeypatch):
    monkeypatch.delattr(runtime.sys, "frozen", raising=False)
    assert runtime.is_frozen() is False


def test_is_frozen_true_when_pyinstaller_sets_it(monkeypatch):
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)
    assert runtime.is_frozen() is True


def test_bundled_resource_path_dev_mode_uses_project_root(monkeypatch):
    monkeypatch.delattr(runtime.sys, "frozen", raising=False)
    result = runtime.bundled_resource_path("app.py")
    assert result == runtime.PROJECT_ROOT / "app.py"


def test_bundled_resource_path_packaged_mode_uses_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime.sys, "_MEIPASS", str(tmp_path), raising=False)
    result = runtime.bundled_resource_path("app.py")
    assert result == tmp_path / "app.py"


def test_app_dir_dev_mode_is_project_root(monkeypatch):
    monkeypatch.delattr(runtime.sys, "frozen", raising=False)
    assert runtime.app_dir() == runtime.PROJECT_ROOT


def test_app_dir_packaged_mode_is_executable_dir(monkeypatch, tmp_path):
    fake_exe = tmp_path / "YouTubeTranscriber.exe"
    fake_exe.touch()
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime.sys, "executable", str(fake_exe))
    assert runtime.app_dir() == tmp_path


def test_user_data_dir_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert runtime.user_data_dir() == tmp_path / "YouTubeTranscriber"


def test_user_data_dir_windows_falls_back_without_localappdata(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.sys, "platform", "win32")
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    result = runtime.user_data_dir()
    assert result == tmp_path / "AppData" / "Local" / "YouTubeTranscriber"


def test_user_data_dir_macos(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.sys, "platform", "darwin")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    result = runtime.user_data_dir()
    assert result == tmp_path / "Library" / "Application Support" / "YouTubeTranscriber"


def test_user_data_dir_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.sys, "platform", "linux")
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    result = runtime.user_data_dir()
    assert result == tmp_path / ".local" / "share" / "youtubetranscriber"


def test_exe_suffix_windows(monkeypatch):
    monkeypatch.setattr(runtime.sys, "platform", "win32")
    assert runtime.exe_suffix() == ".exe"


def test_exe_suffix_non_windows(monkeypatch):
    monkeypatch.setattr(runtime.sys, "platform", "darwin")
    assert runtime.exe_suffix() == ""
