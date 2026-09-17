"""Structured domain types shared across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

# Possible TranscriptResult.source values
SOURCE_YOUTUBE_MANUAL = "youtube_manual"
SOURCE_YOUTUBE_AUTO = "youtube_auto"
SOURCE_LOCAL_WHISPER = "local_whisper"


@dataclass
class TranscriptSegment:
    start: float
    duration: float | None
    text: str

    @property
    def end(self) -> float:
        return self.start + (self.duration or 0.0)


@dataclass
class VideoMetadata:
    video_id: str
    title: str | None = None
    channel: str | None = None
    duration_seconds: float | None = None


@dataclass
class TranscriptResult:
    video_id: str
    source: str
    segments: list[TranscriptSegment]
    title: str | None = None
    language: str | None = None
    language_code: str | None = None
    is_generated: bool | None = None  # True = auto-generated captions
    whisper_model: str | None = None
    metadata: VideoMetadata | None = field(default=None)

    @property
    def source_label(self) -> str:
        return {
            SOURCE_YOUTUBE_MANUAL: "YouTube captions (manually created)",
            SOURCE_YOUTUBE_AUTO: "YouTube captions (auto-generated)",
            SOURCE_LOCAL_WHISPER: "Local Whisper",
        }.get(self.source, self.source)

    def to_plain_text(self) -> str:
        from .formatting import segments_to_plain_text

        return segments_to_plain_text(self.segments)

    def to_timestamped_text(self) -> str:
        from .formatting import segments_to_timestamped_text

        return segments_to_timestamped_text(self.segments)

    def to_srt(self) -> str:
        from .formatting import segments_to_srt

        return segments_to_srt(self.segments)
