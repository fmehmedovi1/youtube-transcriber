import pytest

from src.youtube_transcriber.errors import InvalidURLError
from src.youtube_transcriber.youtube import extract_video_id

VIDEO_ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com/watch?v={VIDEO_ID}",
        f"https://m.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
        f"https://youtube.com/shorts/{VIDEO_ID}",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
        f"www.youtube.com/watch?v={VIDEO_ID}",
        f"https://www.youtube.com/watch?v={VIDEO_ID}&t=42s",
        VIDEO_ID,
    ],
)
def test_valid_urls(url):
    assert extract_video_id(url) == VIDEO_ID


@pytest.mark.parametrize(
    "bad_input",
    [
        "not a url at all",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "",
        "   ",
        "https://youtube.com/watch?v=short",
        "https://youtu.be/",
        f"https://www.youtube.com/watch?v={VIDEO_ID[:-1]}",
    ],
)
def test_invalid_urls(bad_input):
    with pytest.raises(InvalidURLError):
        extract_video_id(bad_input)
