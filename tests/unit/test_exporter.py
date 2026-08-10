from video_script_studio.domain.models import TranscriptSegment
from video_script_studio.services.exporter import format_srt_time, render_srt


def test_srt_time_handles_hours() -> None:
    assert format_srt_time(3661.234) == "01:01:01,234"


def test_srt_is_sorted_and_numbered() -> None:
    result = render_srt(
        [TranscriptSegment(2, 3, "第二句"), TranscriptSegment(0, 1.5, "第一句")]
    )
    assert result.startswith("1\n00:00:00,000 --> 00:00:01,500\n第一句")
    assert "2\n00:00:02,000 --> 00:00:03,000\n第二句" in result

