# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the Windows (and, incidentally, macOS/Linux)
YouTubeTranscriber executable.

Build with:
    pyinstaller YouTubeTranscriber.spec --noconfirm

Streamlit needs special handling when frozen: it looks up its own version
via importlib.metadata at runtime and ships assorted data files, so a
plain `pyinstaller app.py` does not work. `collect_all("streamlit")` below
pulls in everything PyInstaller's static import analysis can't see on its
own (data files, package metadata, lazily-imported submodules). No other
package in this project needs that treatment — hidden imports are kept to
exactly what's required, not a speculative catch-all list.

Packaging strategy: onedir (COLLECT), not onefile. A onefile build would
re-extract its entire payload — including any bundled native binaries
under bin/ — into a fresh temp directory on every launch, which is both
slower and defeats the purpose of shipping ffmpeg.exe/whisper-cli.exe
alongside the app at a stable path. A folder next to YouTubeTranscriber.exe
is simple to ZIP, simple to extract, and reliable across runs.

Two entry points share the same Analysis: YouTubeTranscriber.exe (no
console window, for normal users) and YouTubeTranscriber-Debug.exe (same
app, with a visible console showing log output, for troubleshooting).

packaging/Run YouTubeTranscriber.bat is deliberately NOT listed in `datas`
below: PyInstaller 6's onedir layout places `datas` entries inside
_internal/, not next to the .exe, so the build scripts
(scripts/build_windows.ps1, .github/workflows/build-windows.yml) copy it
into the dist folder root themselves after this spec runs.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ("app.py", "."),
]
binaries = []
hiddenimports = []

for pkg in ("streamlit",):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# app.py (the Streamlit UI script) is shipped as a plain data file above and
# run via streamlit's bootstrap, not imported by entry_point.py — so
# PyInstaller's static analysis never sees its `from src.youtube_transcriber
# import ...` statements. Force the whole package in explicitly, or modules
# like audio.py/transcript.py/model_manager.py silently go missing from the
# build (ModuleNotFoundError at runtime, tests never catch it).
hiddenimports += collect_submodules("src.youtube_transcriber")

a = Analysis(
    ["packaging/entry_point.py"],
    pathex=[SPECPATH],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YouTubeTranscriber",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,
)

exe_debug = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YouTubeTranscriber-Debug",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    exe_debug,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="YouTubeTranscriber",
)
