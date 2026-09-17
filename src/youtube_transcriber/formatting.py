"""Deterministic transcript formatting: plain text, timestamped, SRT.

No LLM cleanup here by design (zero-cost requirement) — only whitespace
normalization, adjacent-duplicate removal, and readable joining.
"""

from __future__ import annotations

from .models import TranscriptSegment

# A new paragraph starts when the gap since the previous segment exceeds
# this many seconds, treated as a natural pause in speech.
_PARAGRAPH_GAP_SECONDS = 3.0
# ...or after roughly this many characters, so paragraphs stay readable.
_PARAGRAPH_CHAR_TARGET = 400


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _dedupe_adjacent(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """Drop segments whose cleaned text exactly repeats the previous one.

    Auto-generated captions frequently emit rolling-window duplicates.
    """
    result: list[TranscriptSegment] = []
    last_text = None
    for seg in segments:
        text = _clean_text(seg.text)
        if not text:
            continue
        if text == last_text:
            continue
        result.append(TranscriptSegment(start=seg.start, duration=seg.duration, text=text))
        last_text = text
    return result


def format_timestamp_hhmmss(total_seconds: float) -> str:
    """Format seconds as HH:MM:SS, supporting durations over an hour."""
    total_seconds = max(0, int(round(total_seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_timestamp_srt(total_seconds: float) -> str:
    """Format seconds as SRT's HH:MM:SS,mmm timestamp."""
    total_seconds = max(0.0, total_seconds)
    whole_seconds = int(total_seconds)
    milliseconds = round((total_seconds - whole_seconds) * 1000)
    if milliseconds == 1000:
        milliseconds = 0
        whole_seconds += 1
    hours, remainder = divmod(whole_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def segments_to_plain_text(segments: list[TranscriptSegment]) -> str:
    cleaned = _dedupe_adjacent(segments)
    if not cleaned:
        return ""

    paragraphs: list[list[str]] = [[]]
    char_count = 0
    prev_end = cleaned[0].start

    for seg in cleaned:
        gap = seg.start - prev_end
        current_paragraph_text = " ".join(paragraphs[-1])
        if paragraphs[-1] and (
            gap > _PARAGRAPH_GAP_SECONDS or len(current_paragraph_text) > _PARAGRAPH_CHAR_TARGET
        ):
            paragraphs.append([])
            char_count = 0
        paragraphs[-1].append(seg.text)
        char_count += len(seg.text)
        prev_end = seg.end

    return "\n\n".join(" ".join(p) for p in paragraphs if p)


def segments_to_timestamped_text(segments: list[TranscriptSegment]) -> str:
    cleaned = _dedupe_adjacent(segments)
    lines = [f"[{format_timestamp_hhmmss(seg.start)}] {seg.text}" for seg in cleaned]
    return "\n".join(lines)


def segments_to_srt(segments: list[TranscriptSegment]) -> str:
    cleaned = _dedupe_adjacent(segments)
    blocks = []
    for i, seg in enumerate(cleaned):
        duration = seg.duration
        if duration is None or duration <= 0:
            # No duration info: hold each caption until the next one starts,
            # or 2 seconds for the final segment.
            if i + 1 < len(cleaned):
                duration = max(0.5, cleaned[i + 1].start - seg.start)
            else:
                duration = 2.0
        end = seg.start + duration
        start_ts = format_timestamp_srt(seg.start)
        end_ts = format_timestamp_srt(end)
        blocks.append(f"{i + 1}\n{start_ts} --> {end_ts}\n{seg.text}\n")
    return "\n".join(blocks)
