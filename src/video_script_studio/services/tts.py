from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Voice:
    voice_id: str
    name: str


class LocalTTSService:
    def __init__(self) -> None:
        import pyttsx3

        self.engine = pyttsx3.init()

    def voices(self) -> list[Voice]:
        return [Voice(item.id, item.name) for item in self.engine.getProperty("voices")]

    def synthesize(
        self, text: str, destination: Path, voice_id: str | None, rate: int, volume: float
    ) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if voice_id:
            self.engine.setProperty("voice", voice_id)
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", max(0.0, min(1.0, volume)))
        self.engine.save_to_file(text, str(destination))
        self.engine.runAndWait()

