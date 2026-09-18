"""Model download tests. Network is mocked — never touches Hugging Face."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest

from src.youtube_transcriber import model_manager
from src.youtube_transcriber.config import Config


def test_model_is_available_false_when_missing(tmp_path):
    cfg = Config(whisper_model_dir=tmp_path)
    assert model_manager.model_is_available("small", cfg) is False


def test_model_is_available_true_when_present(tmp_path):
    cfg = Config(whisper_model_dir=tmp_path)
    cfg.model_path("small").touch()
    assert model_manager.model_is_available("small", cfg) is True


def test_approximate_size_mb_known_model():
    assert model_manager.approximate_size_mb("small") == 466


def test_approximate_size_mb_unknown_model():
    assert model_manager.approximate_size_mb("not-a-real-model") is None


def test_download_model_skips_if_already_present(tmp_path):
    cfg = Config(whisper_model_dir=tmp_path)
    dest = cfg.model_path("small")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"already here")

    with patch("src.youtube_transcriber.model_manager.urllib.request.urlopen") as mock_open:
        result = model_manager.download_model("small", cfg)

    mock_open.assert_not_called()
    assert result == dest
    assert dest.read_bytes() == b"already here"


def test_download_model_writes_file_and_reports_progress(tmp_path):
    cfg = Config(whisper_model_dir=tmp_path)
    fake_response = io.BytesIO(b"x" * 100)
    fake_response.headers = {"Content-Length": "100"}

    mock_ctx = MagicMock()
    mock_ctx.__enter__.return_value = fake_response

    progress_calls = []

    with patch("src.youtube_transcriber.model_manager.urllib.request.urlopen", return_value=mock_ctx):
        result = model_manager.download_model(
            "tiny", cfg, on_progress=lambda d, t: progress_calls.append((d, t))
        )

    assert result == cfg.model_path("tiny")
    assert result.read_bytes() == b"x" * 100
    assert progress_calls[-1] == (100, 100)
    assert not result.with_suffix(result.suffix + ".part").exists()


def test_download_model_cleans_up_partial_file_on_failure(tmp_path):
    cfg = Config(whisper_model_dir=tmp_path)

    with patch(
        "src.youtube_transcriber.model_manager.urllib.request.urlopen",
        side_effect=OSError("network down"),
    ):
        with pytest.raises(model_manager.ModelDownloadError):
            model_manager.download_model("base", cfg)

    dest = cfg.model_path("base")
    assert not dest.exists()
    assert not dest.with_suffix(dest.suffix + ".part").exists()
