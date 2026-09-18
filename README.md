# YouTube Transcript

Paste a YouTube URL, get a transcript. No paid API involved, ever.

## What it does

1. Validates the URL and extracts the video ID.
2. Checks YouTube for existing captions (manual or auto-generated) and, if
   found, fetches them directly — free, fast, no audio download.
3. If no usable captions exist, downloads audio-only (via `yt-dlp`),
   converts it to the WAV format whisper.cpp needs (via `ffmpeg`), and
   transcribes it **locally** using [whisper.cpp](https://github.com/ggml-org/whisper.cpp).
4. Shows the transcript, labeled with its actual source, and lets you
   copy it or download it as `.txt` / `.srt`.

Captions are always tried first. Audio is only downloaded when captions
are genuinely unavailable.

## Download Windows App

Don't want to run Python? Download the packaged Windows build from
[GitHub Releases](../../releases):

1. Download `YouTubeTranscriber-Windows-x64.zip`.
2. Extract the ZIP.
3. Open `YouTubeTranscriber.exe`.
4. Your browser opens automatically at `http://127.0.0.1:8501`.
5. Paste a YouTube URL and generate a transcript.

No Python, no `pip install`, no `streamlit run` — the executable starts
the app internally and only listens on `127.0.0.1` (never your network).

If this repository has no published release yet, the
[`build-windows`](.github/workflows/build-windows.yml) GitHub Actions
workflow builds the ZIP on every push to `main` and on every tagged
release (`v1.0.0` etc.) — check the Actions tab for the latest build
artifact rather than expecting a link here in advance.

**Windows SmartScreen**: this executable is unsigned (no commercial
code-signing certificate was purchased, to keep distribution at $0), so
Windows may show a SmartScreen warning on first launch. See
[Troubleshooting](#troubleshooting).

**Local Whisper fallback on Windows**: only needed for videos with no
YouTube captions. The packaged build does not bundle `ffmpeg`/`whisper.cpp`
(see [Native dependencies on Windows](#native-dependencies-on-windows));
run `scripts\setup_whisper.ps1` from a source checkout to set them up, or
use the in-app "Download model" button once they're available on PATH.

## Why it costs $0

This app never calls OpenAI, Anthropic, Google Cloud Speech-to-Text, AWS
Transcribe, AssemblyAI, Deepgram, Azure Speech, or any other metered
transcription/LLM API. There is no API key anywhere in this codebase.
When captions aren't available, transcription runs as a local subprocess
(`whisper.cpp`) on your own machine. See **Cost Model** below.

## Requirements

- Python 3.11+ (developed against 3.12)
- `ffmpeg` (for audio conversion — only used on the Whisper fallback path)
- `whisper.cpp`, built locally, with one downloaded ggml model (only used
  on the fallback path)
- Internet connection (to reach YouTube for captions/metadata/audio — this
  is just normal network access, not a paid API)

## Installation

```bash
git clone <this-repo>
cd youtube-transcriber
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Or:

```bash
make setup
```

## Running

```bash
.venv/bin/streamlit run app.py
```

Or:

```bash
make run
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

## Local Whisper setup (fallback path only)

Only needed for videos with no YouTube captions. Run:

```bash
./scripts/setup_whisper.sh small
```

(or `make whisper-setup MODEL=small`). This will:

1. Verify `git`, `cmake`, `make`, and `ffmpeg` are installed.
2. Clone [`ggml-org/whisper.cpp`](https://github.com/ggml-org/whisper.cpp)
   into `tools/whisper.cpp`.
3. Build it locally with CMake (uses your machine's CPU/GPU — Apple
   Silicon gets Metal acceleration automatically, no configuration
   needed).
4. Download one multilingual ggml model into `models/whisper/`.

Pass a different model name (`tiny`, `base`, `small`, `medium`) to choose
a different default. Only one model is downloaded — nothing runs
automatically in the background, and startup never re-downloads it.

Model tradeoffs:

```text
tiny   -> fastest / lower accuracy
base   -> fast / reasonable
small  -> recommended balance (default; multilingual, incl. bs/hr/sr/en)
medium -> slower / better accuracy
```

The default model is multilingual (not an English-only `.en` variant) so
Bosnian/Croatian/Serbian and other languages work out of the box.

If `ffmpeg` is missing on macOS:

```bash
brew install ffmpeg
```

## Cost Model

```text
API cost per transcription: $0
```

- No OpenAI/Anthropic/Google/AWS/Azure/AssemblyAI/Deepgram calls — none of
  those SDKs or keys appear anywhere in this codebase.
- The caption path is a free read of data YouTube already serves publicly.
- The Whisper fallback runs entirely as a local subprocess on your own
  hardware; nothing is uploaded to a third-party transcription service.
- The only real-world costs are the ones you already pay for regardless of
  this app: your internet connection, electricity, and the wear on your
  own compute. There is no metered, per-request charge.

This holds for the packaged Windows build too: it's the same code, running
locally, downloading nothing beyond the (free, open-weight) Whisper model
and its own dependencies. `windows-latest` GitHub Actions runners and
GitHub Releases are both part of GitHub's free tier for public
repositories — no paid CI minutes or paid GitHub feature is required.

## Developer mode vs packaged desktop mode

Two ways to run the exact same application logic — nothing under
`src/youtube_transcriber/` is duplicated between them:

```text
Developer mode        .venv/bin/streamlit run app.py   (this repo, any OS)
Packaged desktop mode  YouTubeTranscriber.exe            (Windows, no Python needed)
```

The packaged mode wraps the same `app.py` with a small launcher
(`src/youtube_transcriber/launcher.py`) that starts Streamlit in-process,
binds `127.0.0.1` only, waits for the server to become ready, opens the
default browser exactly once, and enforces a single running instance via a
PID+port lock file in the OS user-data directory. See `runtime.py` for the
dev-vs-packaged path resolution both modes share.

## Building the Windows executable

**Windows `.exe` builds must be produced on Windows** — PyInstaller does
not cross-compile, so a macOS/Linux machine cannot build or validate the
real `.exe`. This repository's own development happened on macOS; the
Windows build was built and verified on GitHub's `windows-latest` CI
runner, not claimed as locally tested on macOS.

Locally, on a Windows machine:

```powershell
.\scripts\build_windows.ps1
```

This creates/reuses a venv, installs `.[dev,build]` (PyInstaller included),
runs the test suite, builds via `YouTubeTranscriber.spec`, and produces
`dist\YouTubeTranscriber-Windows-x64.zip`.

Packaging notes:

- **onedir, not onefile** (`YouTubeTranscriber.spec`). A onefile build
  re-extracts its whole payload to a fresh temp directory on every launch,
  which is slower and unsuitable for shipping native binaries like
  `ffmpeg.exe`/`whisper-cli.exe` at a stable path. A folder next to the
  `.exe` is simple to ZIP and reliable across runs.
- **Two executables** are produced: `YouTubeTranscriber.exe` (no console,
  for normal users) and `YouTubeTranscriber-Debug.exe` (same app, visible
  console with log output, for troubleshooting).
- No UPX, no obfuscation, no packers — standard, transparent PyInstaller
  output, to avoid tripping antivirus heuristics.

### Native dependencies on Windows

`ffmpeg` and `whisper.cpp` are only needed for the Whisper fallback path
(videos without YouTube captions) — the primary caption path needs neither.
This project ships a **first-run setup script** (`scripts\setup_whisper.ps1`,
mirroring the existing macOS/Linux `scripts/setup_whisper.sh`) rather than
bundling prebuilt `ffmpeg.exe`/`whisper-cli.exe` inside the release ZIP.
Reasoning: reliably cross-building whisper.cpp for Windows and legally
redistributing a static ffmpeg build both need real validation on a
Windows machine, which risks shipping a broken or unverified binary under
time pressure; the setup script instead reuses the exact same
clone-build-download logic already proven on macOS/Linux. The app never
crashes when these are missing — `FFmpegNotFoundError` /
`WhisperNotFoundError` show a clear, actionable message pointing at the
setup script, exactly as they do today outside packaging. `bin/ffmpeg.exe`
/ `bin/whisper-cli.exe` placed next to the packaged `.exe` are picked up
automatically if present (see `get_ffmpeg_executable()` /
`get_whisper_executable()`), so bundling can be added later without any
code changes if a validated Windows binary source is established.

### Whisper models

Never bundled into the executable (multiple models would make the release
huge for no benefit — most transcripts never need Whisper at all). The app
downloads the selected model on first use, into the OS user-data
directory, and reuses it on every future run:

```text
%LOCALAPPDATA%\YouTubeTranscriber\models\ggml-<model>.bin   (Windows, packaged)
~/Library/Application Support/YouTubeTranscriber/models/…   (macOS, packaged)
models/whisper/ggml-<model>.bin                              (dev checkout, any OS)
```

### CI: automatic builds and releases

- [`build-windows.yml`](.github/workflows/build-windows.yml) runs on every
  push/PR to `main`: installs dependencies, runs tests, builds with
  PyInstaller, verifies `YouTubeTranscriber.exe` (and the debug variant)
  actually exist, zips the result, and uploads it as a GitHub Actions
  artifact. The build fails if the `.exe` is missing.
- Pushing a tag like `v1.0.0` additionally publishes
  `YouTubeTranscriber-Windows-x64.zip` to a GitHub Release for that tag —
  no paid GitHub feature involved, just the built-in `GITHUB_TOKEN`.

## Architecture

```text
YouTube URL -> validate -> extract video ID -> fetch metadata (best-effort)
    -> check YouTube captions
         captions found      -> fetch transcript -> RESULT
         captions not found  -> download audio-only -> convert to WAV
                              -> run whisper.cpp locally -> RESULT
```

Code layout:

```text
app.py                        Thin Streamlit UI
src/youtube_transcriber/
  models.py                   TranscriptSegment / TranscriptResult / VideoMetadata
  youtube.py                  URL parsing -> extract_video_id()
  captions.py                 YouTubeCaptionProvider (youtube-transcript-api adapter)
  audio.py                    YouTubeAudioProvider (yt-dlp) + ffmpeg conversion
  whisper_local.py            LocalWhisperTranscriber (whisper.cpp subprocess adapter)
  transcript.py               TranscriptPipeline: fallback routing + cleanup
  formatting.py                Plain text / timestamped text / SRT generation
  config.py                   Env-based configuration, no API keys
  errors.py                   User-facing error categories
  model_manager.py            On-demand Whisper model download (packaged mode)
  runtime.py                  Centralized dev-vs-packaged path resolution
  launcher.py                 Executable entry point: starts Streamlit, opens browser
packaging/entry_point.py      PyInstaller entry script (imports launcher.run)
YouTubeTranscriber.spec       PyInstaller build spec
scripts/build_windows.ps1     One-command Windows build -> dist ZIP
scripts/setup_whisper.ps1     Windows whisper.cpp/model setup (mirrors the .sh version)
.github/workflows/build-windows.yml   CI build + release-on-tag
```

## Troubleshooting

**Windows SmartScreen warning on first launch** — `YouTubeTranscriber.exe`
is an unsigned, self-built executable. This project does not purchase a
commercial code-signing certificate, in order to preserve the $0
distribution requirement. If SmartScreen appears, click "More info" ->
"Run anyway". This is standard for unsigned open-source Windows binaries
and is not a sign the app was tampered with — verify by building it
yourself from source with `scripts\build_windows.ps1` if in doubt.

**ffmpeg missing** — `brew install ffmpeg` (macOS), your distro's package
manager on Linux, or `scripts\setup_whisper.ps1` / `winget install ffmpeg`
on Windows. The app detects this up front and won't crash with a raw
subprocess error.

**whisper.cpp missing / not built** — run `./scripts/setup_whisper.sh`
(macOS/Linux) or `scripts\setup_whisper.ps1` (Windows). The app checks for
the binary before trying to use it and tells you what to run.

**Model missing** — use the in-app "Download model" button (downloads once
into the OS user-data directory and is reused forever after), or run the
same setup script with a model name. The
app won't auto-download a model on every startup; it just tells you it's
missing.

**Captions unavailable** — not an error. The app falls back to local
Whisper automatically (if set up) rather than failing.

**yt-dlp failure / YouTube temporary blocking** — YouTube occasionally
rate-limits or blocks requests. Wait and retry; this affects both the
caption route and the audio-download fallback since both need to reach
the public video.

**Private/deleted/unavailable video** — shown as a clear error. The app
does not attempt to bypass private-video restrictions, authentication, or
DRM, and does not use browser cookies for the normal workflow.

## Tests

```bash
.venv/bin/python -m pytest -q
```

or `make test`. Tests mock all network/subprocess boundaries (YouTube
caption API, yt-dlp, ffmpeg, whisper.cpp) so they don't depend on live
YouTube access or a local Whisper install.

## Privacy

Audio used for Whisper transcription is processed locally on this
computer. It is never uploaded to any transcription provider. Downloaded
audio is written to a temporary directory and deleted after each run,
whether transcription succeeds or fails.
