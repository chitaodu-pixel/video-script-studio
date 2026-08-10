from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from video_script_studio.services.media import MediaService


@dataclass(frozen=True, slots=True)
class KokoroVoice:
    display_name: str
    voice_id: str


class KokoroTTSService:
    """CPU-only Chinese neural TTS backed by the local Kokoro v1.1 model."""

    VOICES = (
        KokoroVoice("女声 1 · 清晰自然", "zf_001"),
        KokoroVoice("女声 2 · 柔和自然", "zf_002"),
        KokoroVoice("男声 1 · 稳重自然", "zm_009"),
        KokoroVoice("男声 2 · 清晰自然", "zm_010"),
    )

    def __init__(self, media_service: MediaService | None = None) -> None:
        self.media = media_service or MediaService()
        self._engine = None

    @staticmethod
    def resolve_model_dir() -> Path:
        candidates = [
            Path.cwd() / "models" / "kokoro-v1.1-zh",
            Path(sys.executable).resolve().parent / "models" / "kokoro-v1.1-zh",
            Path(sys.executable).resolve().parent.parent / "models" / "kokoro-v1.1-zh",
        ]
        required = ("kokoro-v1.1-zh.onnx", "voices-v1.1-zh.bin", "config.json")
        for candidate in candidates:
            if candidate.is_dir() and all((candidate / name).is_file() for name in required):
                return candidate
        raise RuntimeError(
            "找不到离线中文声优包。请确认 models\\kokoro-v1.1-zh 中包含模型、声线和配置文件。"
        )

    def voices(self) -> list[KokoroVoice]:
        self.resolve_model_dir()
        return list(self.VOICES)

    def _load_engine(self):
        if self._engine is None:
            from kokoro_onnx import Kokoro

            model_dir = self.resolve_model_dir()
            self._engine = Kokoro(
                str(model_dir / "kokoro-v1.1-zh.onnx"),
                str(model_dir / "voices-v1.1-zh.bin"),
                vocab_config=str(model_dir / "config.json"),
            )
        return self._engine

    @staticmethod
    def _chunk_phonemes(phonemes: str, limit: int = 400) -> list[str]:
        """Keep every model call below Kokoro's 510-token style-vector limit."""
        chunks: list[str] = []
        remaining = phonemes.strip()
        separators = "。！？；，,.!?;\n "
        while len(remaining) > limit:
            window = remaining[: limit + 1]
            split_at = max(window.rfind(mark) for mark in separators)
            if split_at < limit // 2:
                split_at = limit
            else:
                split_at += 1
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            chunks.append(remaining)
        return chunks

    def synthesize_mp3(
        self,
        text: str,
        destination: Path,
        voice: KokoroVoice,
        rate: int = 0,
        pitch: int = 0,
        volume: int = 100,
    ) -> None:
        import soundfile as sf
        from misaki import zh

        if voice not in self.VOICES:
            raise ValueError("离线中文声优信息无效，请重新刷新声优。")
        phonemes, _ = zh.ZHG2P(version="1.1")(text)
        if not phonemes:
            raise ValueError("没有可用于配音的中文文本。")
        import numpy as np

        engine = self._load_engine()
        audio_parts = []
        sample_rate = 24000
        for chunk in self._chunk_phonemes(phonemes):
            samples, sample_rate = engine.create(
                chunk, voice=voice.voice_id, speed=1, is_phonemes=True
            )
            audio_parts.extend((samples, np.zeros(round(sample_rate * 0.12), dtype=np.float32)))
        samples = np.concatenate(audio_parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="video-script-studio-kokoro-") as temp:
            wav_path = Path(temp) / "speech.wav"
            sf.write(wav_path, samples, sample_rate)
            self.media.wav_to_mp3_adjusted(wav_path, destination, rate, pitch, volume)
