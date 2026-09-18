"""Executable entry point: runs Streamlit in-process, binds localhost only,
opens the browser once the server is ready, and enforces a single running
instance.

This is what YouTubeTranscriber.exe (and `python -m
youtube_transcriber.launcher` in dev) actually runs. It never shells out to
a separate `streamlit` process — that would require a standalone Python
interpreter on PATH, which a packaged build can't assume. Instead it calls
Streamlit's own bootstrap API in-process, so the same code path works
identically in a dev venv and inside a PyInstaller bundle.
"""

from __future__ import annotations

import json
import logging
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from .config import CONFIG, DEFAULT_PORT
from .runtime import bundled_resource_path, user_data_dir

logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
READY_TIMEOUT_SECONDS = 30
LOCK_FILE_NAME = "run.lock"


def server_url(port: int) -> str:
    return f"http://{HOST}:{port}"


def _port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((HOST, port))
        except OSError:
            return False
        return True


def pick_port(preferred: int = DEFAULT_PORT) -> int:
    """Prefer the well-known default port; fall back to any free localhost
    port rather than fighting with whatever else is already using it."""
    if _port_is_free(preferred):
        return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def _lock_file_path() -> Path:
    return user_data_dir() / LOCK_FILE_NAME


def _pid_is_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        import os

        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
    except PermissionError:
        return True


def find_running_instance() -> str | None:
    """Return the URL of an already-running instance, if one is alive."""
    lock_path = _lock_file_path()
    if not lock_path.exists():
        return None
    try:
        data = json.loads(lock_path.read_text())
        pid = int(data["pid"])
        port = int(data["port"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None

    if not _pid_is_alive(pid):
        lock_path.unlink(missing_ok=True)
        return None

    url = server_url(port)
    try:
        urllib.request.urlopen(url, timeout=1)
    except Exception:  # noqa: BLE001 - stale lock, process alive but not our server
        return None
    return url


def _write_lock_file(port: int) -> None:
    import os

    lock_path = _lock_file_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(json.dumps({"pid": os.getpid(), "port": port}))


def _remove_lock_file() -> None:
    _lock_file_path().unlink(missing_ok=True)


def _open_browser_when_ready(url: str, timeout: int = READY_TIMEOUT_SECONDS) -> None:
    """Poll the server and open the browser exactly once it responds.
    Runs in a background thread so it doesn't block the Streamlit server
    (which occupies the main thread)."""

    def _poll() -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen(url, timeout=1)
            except Exception:  # noqa: BLE001 - not ready yet
                time.sleep(0.3)
                continue
            logger.info("server ready, opening browser url=%s", url)
            webbrowser.open(url)
            return
        logger.warning("server did not become ready within %ss", timeout)

    threading.Thread(target=_poll, daemon=True).start()


def _run_streamlit(script_path: Path, port: int) -> None:
    from streamlit.web import bootstrap

    flag_options = {
        "server.port": port,
        "server.address": HOST,
        "server.headless": True,
        "global.developmentMode": False,
        "browser.gatherUsageStats": False,
    }
    bootstrap.load_config_options(flag_options=flag_options)
    bootstrap.run(str(script_path), False, [], flag_options)


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    CONFIG.log_dir.mkdir(parents=True, exist_ok=True)

    existing_url = find_running_instance()
    if existing_url:
        logger.info("existing instance found, opening browser instead of starting a new server")
        webbrowser.open(existing_url)
        return

    port = pick_port()
    url = server_url(port)
    _write_lock_file(port)
    try:
        _open_browser_when_ready(url)
        script_path = bundled_resource_path("app.py")
        _run_streamlit(script_path, port)
    finally:
        _remove_lock_file()


if __name__ == "__main__":
    run()
