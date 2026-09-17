from src.youtube_transcriber.models import (
    SOURCE_LOCAL_WHISPER,
    SOURCE_YOUTUBE_AUTO,
    SOURCE_YOUTUBE_MANUAL,
    TranscriptResult,
    TranscriptSegment,
)


def _result(source: str) -> TranscriptResult:
    return TranscriptResult(
        video_id="abc123",
        source=source,
        segments=[
            TranscriptSegment(start=0.0, duration=2.0, text="Hi."),
            TranscriptSegment(start=2.0, duration=2.0, text="Bye."),
        ],
    )


def test_source_label_manual():
    assert "manually" in _result(SOURCE_YOUTUBE_MANUAL).source_label.lower()


def test_source_label_auto():
    assert "auto" in _result(SOURCE_YOUTUBE_AUTO).source_label.lower()


def test_source_label_whisper():
    assert "whisper" in _result(SOURCE_LOCAL_WHISPER).source_label.lower()


def test_to_plain_text_delegates_to_formatting():
    result = _result(SOURCE_YOUTUBE_MANUAL)
    assert "Hi." in result.to_plain_text()


def test_to_timestamped_text_delegates_to_formatting():
    result = _result(SOURCE_YOUTUBE_MANUAL)
    assert "[00:00:00] Hi." in result.to_timestamped_text()


def test_to_srt_delegates_to_formatting():
    result = _result(SOURCE_YOUTUBE_MANUAL)
    assert "00:00:00,000 --> 00:00:02,000" in result.to_srt()


def test_segment_end_property():
    seg = TranscriptSegment(start=1.5, duration=2.5, text="x")
    assert seg.end == 4.0


def test_segment_end_no_duration():
    seg = TranscriptSegment(start=1.5, duration=None, text="x")
    assert seg.end == 1.5
