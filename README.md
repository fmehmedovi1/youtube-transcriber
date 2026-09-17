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
```

## Troubleshooting

**ffmpeg missing** — `brew install ffmpeg` (macOS) or your distro's
package manager on Linux. The app detects this up front and won't crash
with a raw subprocess error.

**whisper.cpp missing / not built** — run `./scripts/setup_whisper.sh`.
The app checks for the binary before trying to use it and tells you what
to run.

**Model missing** — same fix: `./scripts/setup_whisper.sh <model>`. The
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
