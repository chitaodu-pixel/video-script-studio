from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Callable

from video_script_studio.domain.models import TranscriptSegment


class TranscriptionService:
    @staticmethod
    def resolve_model(model_name: str) -> str:
        if Path(model_name).is_dir():
            return model_name
        configured = os.environ.get("VSS_WHISPER_MODEL")
        candidates = [
            Path(configured) if configured else None,
            Path.cwd() / "models" / f"faster-whisper-{model_name}",
            Path(sys.executable).resolve().parent.parent / "models" / f"faster-whisper-{model_name}",
        ]
        required = ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt")
        for candidate in candidates:
            if candidate and candidate.is_dir() and all((candidate / name).is_file() for name in required):
                return str(candidate)
        raise RuntimeError(
            "找不到本地 Whisper 模型。请确认模型位于 "
            f"models\\faster-whisper-{model_name}，并且包含 config.json、model.bin、"
            "tokenizer.json 和 vocabulary.txt。"
        )

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
                "当前程序未安装 faster-whisper，已停止识别，以避免生成错误文案。"
            ) from exc

        model_path = self.resolve_model(model_name)
        model = WhisperModel(model_path, device="cpu", compute_type="int8")
        source, info = model.transcribe(str(audio_path), language=language, beam_size=5, vad_filter=True)
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
