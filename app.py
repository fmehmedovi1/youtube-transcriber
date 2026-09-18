"""Streamlit UI. Thin — business logic lives in src/youtube_transcriber."""

from __future__ import annotations

import logging
import sys

import streamlit as st

from src.youtube_transcriber.audio import check_ffmpeg_installed
from src.youtube_transcriber.config import CONFIG, PREFERRED_LANGUAGES, WHISPER_MODELS
from src.youtube_transcriber.errors import TranscriberError
from src.youtube_transcriber.formatting import format_timestamp_hhmmss
from src.youtube_transcriber.model_manager import (
    approximate_size_mb,
    download_model,
    model_is_available,
)
from src.youtube_transcriber.models import SOURCE_LOCAL_WHISPER, TranscriptResult
from src.youtube_transcriber.transcript import TranscriptPipeline
from src.youtube_transcriber.whisper_local import find_model, get_whisper_executable
from src.youtube_transcriber.youtube import extract_video_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")

st.set_page_config(page_title="YouTube Transcript", page_icon="📝", layout="centered")

st.title("YouTube Transcript")
st.caption("Free YouTube captions first, local Whisper fallback. $0 API cost, always.")

if "result" not in st.session_state:
    st.session_state.result = None
if "processing" not in st.session_state:
    st.session_state.processing = False

url = st.text_input("Paste a YouTube URL", placeholder="https://youtube.com/watch?v=...")

col1, col2 = st.columns(2)
with col1:
    language_choice = st.selectbox("Language", ["Auto"] + PREFERRED_LANGUAGES)
with col2:
    default_model_index = (
        WHISPER_MODELS.index(CONFIG.default_whisper_model)
        if CONFIG.default_whisper_model in WHISPER_MODELS
        else WHISPER_MODELS.index("small")
    )
    whisper_model = st.selectbox("Local Whisper model (fallback only)", WHISPER_MODELS, index=default_model_index)

include_timestamps = st.checkbox("Include timestamps", value=False)

if not model_is_available(whisper_model):
    size_mb = approximate_size_mb(whisper_model)
    size_note = f" (~{size_mb} MB)" if size_mb else ""
    with st.expander(f"Local Whisper model '{whisper_model}' is not installed", expanded=False):
        st.write(
            "This model is only needed as a fallback, for videos that don't "
            "already have YouTube captions. If captions are available, "
            "nothing below is required."
        )
        st.write(f"**Model:** {whisper_model} (multilingual)  \n**Cost:** $0 — downloaded once, stored locally, reused for every future transcript{size_note}.")
        if st.button(f"Download model ({whisper_model})", key=f"download_{whisper_model}"):
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def on_progress(downloaded: int, total: int) -> None:
                fraction = (downloaded / total) if total else 0.0
                progress_bar.progress(min(fraction, 1.0))
                status_text.write(f"{downloaded / 1_048_576:.0f} MB downloaded...")

            try:
                download_model(whisper_model, on_progress=on_progress)
            except TranscriberError as exc:
                st.error(exc.user_message)
            else:
                st.success("Whisper model installed successfully.")
                st.rerun()

generate_clicked = st.button(
    "Generate Transcript", type="primary", disabled=st.session_state.processing
)

st.divider()


def _run_pipeline(video_id: str) -> TranscriptResult:
    pipeline = TranscriptPipeline()
    with st.status("Working...", expanded=True) as status:
        def on_progress(message: str) -> None:
            status.update(label=message)
            st.write(message)

        auto = language_choice == "Auto"
        language_code = None if auto else language_choice
        result = pipeline.run(
            video_id,
            language_code=language_code,
            auto_language=auto,
            whisper_model=whisper_model,
            on_progress=on_progress,
        )
        status.update(label="Transcript ready.", state="complete")
    return result


if generate_clicked:
    if not url.strip():
        st.warning("Paste a YouTube URL first.")
    else:
        try:
            video_id = extract_video_id(url)
        except TranscriberError as exc:
            st.error(exc.user_message)
        else:
            st.session_state.processing = True
            try:
                st.session_state.result = _run_pipeline(video_id)
            except TranscriberError as exc:
                logger.warning("pipeline error: %s", exc.detail or exc)
                st.session_state.result = None
                st.error(exc.user_message)
            except Exception as exc:  # noqa: BLE001 - surface unexpected errors, don't hide them
                logger.exception("unexpected error")
                st.session_state.result = None
                st.error(f"Unexpected error: {exc}")
            finally:
                st.session_state.processing = False

result: TranscriptResult | None = st.session_state.result

if result is not None:
    st.subheader(result.title or f"Video {result.video_id}")

    meta_lines = []
    if result.metadata and result.metadata.channel:
        meta_lines.append(f"**Channel:** {result.metadata.channel}")
    if result.metadata and result.metadata.duration_seconds:
        meta_lines.append(f"**Duration:** {format_timestamp_hhmmss(result.metadata.duration_seconds)}")

    if result.source == SOURCE_LOCAL_WHISPER:
        meta_lines.append("**Source:** Local Whisper — processed on this computer")
        meta_lines.append(f"**Model:** {result.whisper_model}")
        if result.language_code:
            meta_lines.append(f"**Detected language:** {result.language_code}")
        meta_lines.append("**Processing:** local")
    else:
        kind = "Auto-generated" if result.is_generated else "Manually created"
        meta_lines.append("**Source:** YouTube captions")
        meta_lines.append(f"**Language:** {result.language} ({result.language_code})")
        meta_lines.append(f"**Caption type:** {kind}")

    meta_lines.append("**Cost:** $0 API usage")
    st.markdown("  \n".join(meta_lines))

    transcript_text = result.to_timestamped_text() if include_timestamps else result.to_plain_text()
    st.text_area("Transcript", value=transcript_text, height=400)

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button(
            "Download TXT",
            data=transcript_text,
            file_name=f"{result.video_id or 'transcript'}.txt",
            mime="text/plain",
        )
    with dl_col2:
        st.download_button(
            "Download SRT",
            data=result.to_srt(),
            file_name=f"{result.video_id or 'transcript'}.srt",
            mime="application/x-subrip",
            disabled=not result.segments,
        )

with st.expander("Local setup status"):
    ffmpeg_ok = check_ffmpeg_installed()
    whisper_ok = get_whisper_executable() is not None
    model_ok = find_model(whisper_model) is not None
    setup_hint = "scripts\\setup_whisper.ps1" if sys.platform == "win32" else "scripts/setup_whisper.sh"
    st.write(f"ffmpeg installed: {'yes' if ffmpeg_ok else 'no — see ' + setup_hint}")
    st.write(f"whisper.cpp built: {'yes' if whisper_ok else 'no — run ' + setup_hint}")
    st.write(f"Model '{whisper_model}' present: {'yes' if model_ok else 'no — use the download button above'}")
    st.divider()
    st.write("**Transcription engine:** Local Whisper (fallback only) — **API cost:** $0")
    st.caption(
        "These are only needed as a fallback when a video has no YouTube captions. "
        "Internet access is used to reach YouTube for captions/audio; Whisper itself "
        "runs entirely on this computer, and no paid transcription service is ever contacted."
    )
