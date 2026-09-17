"""Small configuration layer. No API keys — this app uses none.

All settings have sane defaults so the app runs with zero configuration.
Override via environment variables when needed.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Ordered language preference used when the user selects "Auto".
PREFERRED_LANGUAGES = ["bs", "hr", "sr", "en"]

WHISPER_MODELS = ["tiny", "base", "small", "medium"]


@dataclass(frozen=True)
class Config:
    whisper_cpp_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get(
                "WHISPER_CPP_PATH",
                str(PROJECT_ROOT / "tools" / "whisper.cpp" / "build" / "bin" / "whisper-cli"),
            )
        )
    )
    whisper_model_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("WHISPER_MODEL_PATH", str(PROJECT_ROOT / "models" / "whisper"))
        )
    )
    default_whisper_model: str = field(
        default_factory=lambda: os.environ.get("DEFAULT_WHISPER_MODEL", "small")
    )
    temp_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("TEMP_DIR", tempfile.gettempdir()))
        / "youtube-transcriber"
    )

    def model_path(self, model_name: str) -> Path:
        return self.whisper_model_dir / f"ggml-{model_name}.bin"


CONFIG = Config()
