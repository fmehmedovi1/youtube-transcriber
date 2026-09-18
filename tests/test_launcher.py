"""Launcher tests: port selection, server URL generation, and the
single-instance lock file — the pieces that don't require actually
starting Streamlit.
"""

from __future__ import annotations

import json
import os
import socket

from src.youtube_transcriber import launcher


def test_server_url_format():
    assert launcher.server_url(8501) == "http://127.0.0.1:8501"


def test_pick_port_returns_preferred_when_free():
    # Use an uncommon high port so this test is unaffected by anything
    # else already listening on 8501 in a dev environment.
    port = launcher.pick_port(preferred=58231)
    assert port == 58231


def test_pick_port_falls_back_when_preferred_is_taken():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen(1)
        taken_port = occupied.getsockname()[1]

        picked = launcher.pick_port(preferred=taken_port)
        assert picked != taken_port


def test_find_running_instance_none_when_no_lock_file(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "_lock_file_path", lambda: tmp_path / "run.lock")
    assert launcher.find_running_instance() is None


def test_find_running_instance_none_when_pid_dead(monkeypatch, tmp_path):
    lock_path = tmp_path / "run.lock"
    lock_path.write_text(json.dumps({"pid": 999999999, "port": 8501}))
    monkeypatch.setattr(launcher, "_lock_file_path", lambda: lock_path)
    assert launcher.find_running_instance() is None
    assert not lock_path.exists()  # stale lock cleaned up


def test_find_running_instance_none_when_server_not_responding(monkeypatch, tmp_path):
    lock_path = tmp_path / "run.lock"
    lock_path.write_text(json.dumps({"pid": os.getpid(), "port": 58232}))
    monkeypatch.setattr(launcher, "_lock_file_path", lambda: lock_path)
    # Our own pid is alive, but nothing is listening on 58232.
    assert launcher.find_running_instance() is None


def test_write_and_remove_lock_file_roundtrip(monkeypatch, tmp_path):
    lock_path = tmp_path / "run.lock"
    monkeypatch.setattr(launcher, "_lock_file_path", lambda: lock_path)

    launcher._write_lock_file(8501)
    assert lock_path.exists()
    data = json.loads(lock_path.read_text())
    assert data["port"] == 8501
    assert data["pid"] == os.getpid()

    launcher._remove_lock_file()
    assert not lock_path.exists()
