"""On-demand Whisper model download.

Models are never bundled into the packaged app (they're large, and most
transcripts never need Whisper at all since YouTube captions cover the
common case). Instead, the app offers a one-time download into
user_data_dir()/models/whisper the first time a model is actually needed,
and reuses it on every future run.

Downloaded from Hugging Face's mirror of ggml-org/whisper.cpp — open
weights, no account, no API key, $0.
"""

from __future__ import annotations

import logging
import urllib.request
from collections.abc import Callable
from pathlib import Path

from .config import CONFIG, WHISPER_MODEL_SIZES_MB, Config
from .errors import TranscriberError
from .whisper_local import find_model

logger = logging.getLogger(__name__)

MODEL_URL_TEMPLATE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{model}.bin"

ProgressFn = Callable[[int, int], None]  # (bytes_downloaded, total_bytes)


class ModelDownloadError(TranscriberError):
    user_message = "Downloading the Whisper model failed. Check your internet connection and try again."


def model_is_available(model_name: str, config: Config = CONFIG) -> bool:
    return find_model(model_name, config) is not None


def approximate_size_mb(model_name: str) -> int | None:
    return WHISPER_MODEL_SIZES_MB.get(model_name)


def download_model(
    model_name: str, config: Config = CONFIG, on_progress: ProgressFn | None = None
) -> Path:
    """Download one ggml model into config.whisper_model_dir.

    Streams to a `.part` file and renames on success, so a failed/cancelled
    download never leaves a corrupt file that looks installed. Never
    re-downloads if the model already exists.
    """
    dest = config.model_path(model_name)
    if dest.exists():
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest.with_suffix(dest.suffix + ".part")
    url = MODEL_URL_TEMPLATE.format(model=model_name)

    logger.info("model download started model=%s url=%s", model_name, url)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with open(part_path, "wb") as f:
                while chunk := response.read(1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress:
                        on_progress(downloaded, total)
    except Exception as exc:  # noqa: BLE001 - network errors of many shapes
        part_path.unlink(missing_ok=True)
        raise ModelDownloadError(str(exc)) from exc

    part_path.rename(dest)
    logger.info("model download finished model=%s dest=%s", model_name, dest)
    return dest
