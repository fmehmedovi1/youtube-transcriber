"""LocalWhisperProvider: run whisper.cpp locally, no API involved.

whisper.cpp's CLI binary is named `whisper-cli` in current releases (the
older name `main` was renamed upstream). We detect either, preferring the
current name, and fail with setup instructions rather than guessing.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

from .config import CONFIG, Config
from .errors import LocalTranscriptionError, WhisperModelMissingError, WhisperNotFoundError
from .models import SOURCE_LOCAL_WHISPER, TranscriptResult, TranscriptSegment
from .runtime import app_dir, exe_suffix

logger = logging.getLogger(__name__)

# Accepted whisper.cpp CLI binary names, current name first (the older name
# `main` was renamed upstream, but old local builds may still have it).
_CANDIDATE_BINARY_NAMES = ["whisper-cli", "main"]


def get_whisper_executable(config: Config = CONFIG) -> Path | None:
    """Locate the whisper.cpp CLI binary in dev or packaged mode.

    Search order:
    1. The configured path (env override, or the dev-build / packaged
       default computed in config.py).
    2. Candidate binary names next to the configured path (handles the
       `main` -> `whisper-cli` rename).
    3. A `bin/` directory next to the running executable — where a
       packaged Windows build ships `whisper-cli.exe` alongside the app.
    """
    configured = config.whisper_cpp_path
    if configured.exists():
        return configured
    suffix = exe_suffix()
    for name in _CANDIDATE_BINARY_NAMES:
        for candidate_name in {f"{name}{suffix}", name}:
            candidate = configured.parent / candidate_name
            if candidate.exists():
                return candidate

    bundled_bin = app_dir() / "bin"
    for name in _CANDIDATE_BINARY_NAMES:
        for candidate_name in {f"{name}{suffix}", name}:
            candidate = bundled_bin / candidate_name
            if candidate.exists():
                return candidate
    return None


# Back-compat alias — same lookup, kept for callers written before the
# centralized name.
find_whisper_binary = get_whisper_executable


def find_model(model_name: str, config: Config = CONFIG) -> Path | None:
    path = config.model_path(model_name)
    return path if path.exists() else None


class LocalWhisperTranscriber:
    """Runs whisper.cpp as a subprocess and returns structured segments."""

    def __init__(self, model_name: str | None = None, config: Config = CONFIG):
        self.config = config
        self.model_name = model_name or config.default_whisper_model

    def check_ready(self) -> None:
        """Raise a clear, actionable error if whisper.cpp or its model
        aren't set up yet. Called before any transcription attempt."""
        if get_whisper_executable(self.config) is None:
            raise WhisperNotFoundError(
                f"no whisper.cpp binary found at {self.config.whisper_cpp_path} "
                "or nearby. Run scripts/setup_whisper.sh"
            )
        if find_model(self.model_name, self.config) is None:
            raise WhisperModelMissingError(
                f"model {self.model_name!r} not found at "
                f"{self.config.model_path(self.model_name)}. Run scripts/setup_whisper.sh"
            )

    def transcribe(self, wav_path: Path) -> TranscriptResult:
        """Transcribe a 16kHz mono WAV file. Returns a TranscriptResult
        with source=local_whisper.
        """
        self.check_ready()
        binary = get_whisper_executable(self.config)
        model = find_model(self.model_name, self.config)
        assert binary is not None and model is not None  # guaranteed by check_ready

        with tempfile.TemporaryDirectory() as tmp:
            out_prefix = Path(tmp) / "out"
            cmd = [
                str(binary),
                "-m",
                str(model),
                "-f",
                str(wav_path),
                "-l",
                "auto",  # auto-detect spoken language (bs/hr/sr/en/...), never assume English
                "-oj",  # output JSON with segment timing
                "-of",
                str(out_prefix),
                "-nt",  # no per-line timestamps in stdout text, JSON has them
            ]
            logger.info(
                "whisper transcription started model=%s wav=%s", self.model_name, wav_path.name
            )
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            if result.returncode != 0:
                logger.warning("whisper.cpp failed stderr=%s", result.stderr[-1000:])
                raise LocalTranscriptionError(result.stderr[-1000:] or "whisper.cpp exited non-zero")

            json_path = out_prefix.with_suffix(".json")
            if not json_path.exists():
                raise LocalTranscriptionError(
                    f"expected whisper.cpp output not found: {json_path}"
                )
            segments, language_code = self._parse_json_output(json_path)

        return TranscriptResult(
            video_id="",
            source=SOURCE_LOCAL_WHISPER,
            segments=segments,
            language_code=language_code,
            whisper_model=self.model_name,
        )

    @staticmethod
    def _parse_json_output(json_path: Path) -> tuple[list[TranscriptSegment], str | None]:
        try:
            data = json.loads(json_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise LocalTranscriptionError(f"could not parse whisper.cpp output: {exc}") from exc

        language_code = data.get("result", {}).get("language")

        segments: list[TranscriptSegment] = []
        for entry in data.get("transcription", []):
            text = entry.get("text", "").strip()
            if not text:
                continue
            offsets = entry.get("offsets", {})
            start_ms = offsets.get("from", 0)
            end_ms = offsets.get("to", start_ms)
            start = start_ms / 1000.0
            duration = max(0.0, (end_ms - start_ms) / 1000.0)
            segments.append(TranscriptSegment(start=start, duration=duration, text=text))
        return segments, language_code
