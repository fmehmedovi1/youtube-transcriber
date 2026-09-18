"""Small configuration layer. No API keys — this app uses none.

All settings have sane defaults so the app runs with zero configuration.
Override via environment variables when needed.

Path defaults differ between dev checkout and a packaged (PyInstaller)
build — see runtime.py, the single place that knows about that split.
Dev mode keeps its historical defaults (repo-relative tools/ and models/)
unchanged; packaged mode defaults to the OS user-data directory so
downloaded models and native binaries persist across runs.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .runtime import PROJECT_ROOT, app_dir, exe_suffix, is_frozen, user_data_dir

# Ordered language preference used when the user selects "Auto".
PREFERRED_LANGUAGES = ["bs", "hr", "sr", "en"]

WHISPER_MODELS = ["tiny", "base", "small", "medium"]

# Approximate download sizes for the model-download UI. Not load-bearing —
# only used to tell the user what they're about to download.
WHISPER_MODEL_SIZES_MB = {
    "tiny": 75,
    "base": 142,
    "small": 466,
    "medium": 1500,
}

DEFAULT_PORT = 8501


def _default_whisper_cpp_path() -> Path:
    if is_frozen():
        return app_dir() / "bin" / f"whisper-cli{exe_suffix()}"
    return PROJECT_ROOT / "tools" / "whisper.cpp" / "build" / "bin" / "whisper-cli"


def _default_model_dir() -> Path:
    if is_frozen():
        return user_data_dir() / "models" / "whisper"
    return PROJECT_ROOT / "models" / "whisper"


def _default_temp_dir() -> Path:
    return Path(tempfile.gettempdir()) / "youtube-transcriber"


def _default_log_dir() -> Path:
    if is_frozen():
        return user_data_dir() / "logs"
    return PROJECT_ROOT / "logs"


@dataclass(frozen=True)
class Config:
    whisper_cpp_path: Path = field(
        default_factory=lambda: Path(os.environ["WHISPER_CPP_PATH"])
        if "WHISPER_CPP_PATH" in os.environ
        else _default_whisper_cpp_path()
    )
    whisper_model_dir: Path = field(
        default_factory=lambda: Path(os.environ["WHISPER_MODEL_PATH"])
        if "WHISPER_MODEL_PATH" in os.environ
        else _default_model_dir()
    )
    default_whisper_model: str = field(
        default_factory=lambda: os.environ.get("DEFAULT_WHISPER_MODEL", "small")
    )
    temp_dir: Path = field(
        default_factory=lambda: Path(os.environ["TEMP_DIR"]) / "youtube-transcriber"
        if "TEMP_DIR" in os.environ
        else _default_temp_dir()
    )
    log_dir: Path = field(default_factory=_default_log_dir)

    def model_path(self, model_name: str) -> Path:
        return self.whisper_model_dir / f"ggml-{model_name}.bin"


CONFIG = Config()
