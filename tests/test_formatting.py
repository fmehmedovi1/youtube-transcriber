from src.youtube_transcriber.formatting import (
    format_timestamp_hhmmss,
    format_timestamp_srt,
    segments_to_plain_text,
    segments_to_srt,
    segments_to_timestamped_text,
)
from src.youtube_transcriber.models import TranscriptSegment


def test_timestamp_hhmmss_zero():
    assert format_timestamp_hhmmss(0) == "00:00:00"


def test_timestamp_hhmmss_59_seconds():
    assert format_timestamp_hhmmss(59) == "00:00:59"


def test_timestamp_hhmmss_60_seconds():
    assert format_timestamp_hhmmss(60) == "00:01:00"


def test_timestamp_hhmmss_one_hour():
    assert format_timestamp_hhmmss(3600) == "01:00:00"


def test_timestamp_hhmmss_over_one_hour():
    assert format_timestamp_hhmmss(3661) == "01:01:01"


def test_timestamp_hhmmss_many_hours():
    assert format_timestamp_hhmmss(7325) == "02:02:05"


def test_timestamp_srt_format():
    assert format_timestamp_srt(4.52) == "00:00:04,520"


def test_timestamp_srt_rounds_up_milliseconds():
    assert format_timestamp_srt(0.9996) == "00:00:01,000"


def _segments():
    return [
        TranscriptSegment(start=0.0, duration=4.0, text="Hello there."),
        TranscriptSegment(start=4.0, duration=4.0, text="How are you?"),
    ]


def test_plain_text_joins_segments():
    text = segments_to_plain_text(_segments())
    assert "Hello there." in text
    assert "How are you?" in text


def test_plain_text_new_paragraph_after_gap():
    segments = [
        TranscriptSegment(start=0.0, duration=2.0, text="First part."),
        TranscriptSegment(start=20.0, duration=2.0, text="Much later part."),
    ]
    text = segments_to_plain_text(segments)
    assert "\n\n" in text


def test_plain_text_dedupes_adjacent_duplicates():
    segments = [
        TranscriptSegment(start=0.0, duration=2.0, text="repeated line"),
        TranscriptSegment(start=2.0, duration=2.0, text="repeated line"),
        TranscriptSegment(start=4.0, duration=2.0, text="new line"),
    ]
    text = segments_to_plain_text(segments)
    assert text.count("repeated line") == 1


def test_timestamped_text_format():
    text = segments_to_timestamped_text(_segments())
    lines = text.splitlines()
    assert lines[0] == "[00:00:00] Hello there."
    assert lines[1] == "[00:00:04] How are you?"


def test_srt_basic_structure():
    srt = segments_to_srt(_segments())
    assert "1\n00:00:00,000 --> 00:00:04,000\nHello there." in srt
    assert "2\n00:00:04,000 --> 00:00:08,000\nHow are you?" in srt


def test_srt_handles_missing_duration():
    segments = [
        TranscriptSegment(start=0.0, duration=None, text="First."),
        TranscriptSegment(start=5.0, duration=None, text="Second."),
    ]
    srt = segments_to_srt(segments)
    assert "00:00:00,000 --> 00:00:05,000" in srt
    # last segment with no duration falls back to a fixed 2s window
    assert "00:00:05,000 --> 00:00:07,000" in srt
