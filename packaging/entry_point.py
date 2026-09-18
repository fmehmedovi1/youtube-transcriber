"""PyInstaller entry point. Kept separate from launcher.py itself so the
same launcher module can also be run in dev via `python -m
youtube_transcriber.launcher` without going through this wrapper.
"""

from __future__ import annotations

from src.youtube_transcriber.launcher import run

if __name__ == "__main__":
    run()
