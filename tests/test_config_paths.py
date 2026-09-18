"""Dev-mode vs packaged-mode default path resolution in Config.

Env-var overrides (WHISPER_CPP_PATH etc.) must always win regardless of
frozen state — that's covered separately from the frozen/dev defaults.
"""

from __future__ import annotations

from src.youtube_transcriber import config as config_module
from src.youtube_transcriber.config import Config


def test_dev_mode_whisper_cpp_path_is_repo_relative(monkeypatch):
    monkeypatch.setattr(config_module, "is_frozen", lambda: False)
    cfg = Config()
    assert cfg.whisper_cpp_path == (
        config_module.PROJECT_ROOT / "tools" / "whisper.cpp" / "build" / "bin" / "whisper-cli"
    )


def test_dev_mode_model_dir_is_repo_relative(monkeypatch):
    monkeypatch.setattr(config_module, "is_frozen", lambda: False)
    cfg = Config()
    assert cfg.whisper_model_dir == config_module.PROJECT_ROOT / "models" / "whisper"


def test_packaged_mode_whisper_cpp_path_uses_app_dir_bin(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "is_frozen", lambda: True)
    monkeypatch.setattr(config_module, "app_dir", lambda: tmp_path)
    monkeypatch.setattr(config_module, "exe_suffix", lambda: ".exe")
    cfg = Config()
    assert cfg.whisper_cpp_path == tmp_path / "bin" / "whisper-cli.exe"


def test_packaged_mode_model_dir_uses_user_data_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "is_frozen", lambda: True)
    monkeypatch.setattr(config_module, "user_data_dir", lambda: tmp_path)
    cfg = Config()
    assert cfg.whisper_model_dir == tmp_path / "models" / "whisper"


def test_env_override_wins_even_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(config_module, "is_frozen", lambda: True)
    override = tmp_path / "custom-whisper-cli"
    monkeypatch.setenv("WHISPER_CPP_PATH", str(override))
    cfg = Config()
    assert cfg.whisper_cpp_path == override


def test_model_path_joins_model_dir_and_name():
    cfg = Config()
    assert cfg.model_path("small").name == "ggml-small.bin"
