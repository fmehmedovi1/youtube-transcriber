"""Centralized PyInstaller-aware path resolution.

Three distinct kinds of paths exist once the app is packaged, and they must
not be confused:

1. Bundled read-only resources (app source, Streamlit static assets) — live
   under ``sys._MEIPASS`` in a packaged build, or the project root in dev.
2. The directory the running executable lives in — used to look for native
   binaries shipped alongside it (``bin/ffmpeg.exe`` etc). In dev this is the
   project root.
3. Persistent, writable, OS-appropriate user data (downloaded Whisper
   models, logs, cache) — must survive across runs and must NOT live inside
   a PyInstaller onefile extraction temp dir, which is wiped after exit.

Every ``getattr(sys, "_MEIPASS", None)`` check belongs in this module, not
scattered through the codebase.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "YouTubeTranscriber"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def is_frozen() -> bool:
    """True when running as a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False))


def bundled_resource_path(relative_path: str = "") -> Path:
    """Path to a read-only resource shipped with the app.

    Packaged mode: resolves inside the PyInstaller bundle (``sys._MEIPASS``
    for onefile, or the executable's own directory for onedir — both are
    exposed via ``_MEIPASS`` by the bootloader). Dev mode: resolves relative
    to the project root, so ``bundled_resource_path("app.py")`` finds the
    checked-out file.
    """
    if is_frozen():
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    else:
        base = PROJECT_ROOT
    return base / relative_path if relative_path else base


def app_dir() -> Path:
    """Directory containing the running executable, or the project root in
    dev. Use this to look for native binaries shipped next to the exe
    (``bin/ffmpeg.exe``, ``bin/whisper-cli.exe``) — NOT for user data, since
    this directory may be read-only (e.g. under Program Files).
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def user_data_dir() -> Path:
    """Persistent, writable, OS-appropriate directory for this app's data
    (downloaded Whisper models, logs, cache). Stable across runs and across
    PyInstaller onefile re-extractions.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / APP_NAME.lower()


def exe_suffix() -> str:
    return ".exe" if sys.platform == "win32" else ""
