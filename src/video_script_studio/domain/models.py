from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError("Transcript segment has an invalid time range")


@dataclass(slots=True)
class ReplacementRule:
    source: str
    target: str
    enabled: bool = True


@dataclass(slots=True)
class Project:
    name: str
    project_id: str = field(default_factory=lambda: str(uuid4()))
    schema_version: int = 1
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    source_media: str | None = None
    language: str = "zh"
    whisper_model: str = "small"
    whisper_compute_type: str = "int8"
    current_text_version: str = "original"
    rewrite_mode: str = "faithful"
    rewrite_ratio: float = 1.0
    tts_voice_id: str | None = None
    tts_rate: int = 180
    tts_volume: float = 1.0
    stage_status: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Project:
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported project schema version")
        allowed = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def touch(self) -> None:
        self.updated_at = utc_now()

    @property
    def source_path(self) -> Path | None:
        return Path(self.source_media) if self.source_media else None

