from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from video_script_studio.domain.models import TranscriptSegment


class TranscriptionService:
    def transcribe(
        self,
        audio_path: Path,
        model_name: str = "small",
        language: str = "zh",
        progress: Callable[[int], None] | None = None,
    ) -> list[TranscriptSegment]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "当前程序未安装 faster-whisper，已停止识别以避免生成错误文案。"
            ) from exc

        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        source, info = model.transcribe(str(audio_path), language=language)
        duration = max(float(getattr(info, "duration", 0.0)), 0.001)
        output = []
        for item in source:
            output.append(TranscriptSegment(float(item.start), float(item.end), item.text.strip()))
            if progress:
                progress(min(100, round(float(item.end) / duration * 100)))
        if progress:
            progress(100)
        return output

    @staticmethod
    def save_segments(path: Path, segments: list[TranscriptSegment]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {"start": segment.start, "end": segment.end, "text": segment.text}
            for segment in segments
        ]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
