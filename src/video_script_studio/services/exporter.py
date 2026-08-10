from __future__ import annotations

from pathlib import Path

from video_script_studio.domain.models import TranscriptSegment


def format_srt_time(seconds: float) -> str:
    if seconds < 0:
        raise ValueError("SRT 时间不能为负数")
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def render_srt(segments: list[TranscriptSegment]) -> str:
    ordered = sorted(segments, key=lambda segment: segment.start)
    blocks = []
    for index, segment in enumerate(ordered, start=1):
        blocks.append(
            f"{index}\n{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}\n"
            f"{segment.text.strip()}"
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def export_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)

