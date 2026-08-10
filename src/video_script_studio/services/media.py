from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from video_script_studio.domain.errors import EnvironmentDependencyError, ExternalProcessError
from video_script_studio.services.subprocess_utils import hidden_subprocess_kwargs


SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}


@dataclass(frozen=True, slots=True)
class MediaInfo:
    duration: float
    format_name: str
    size: int


class MediaService:
    def __init__(self, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> None:
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe

    def validate_source(self, source: Path) -> None:
        if not source.is_file():
            raise FileNotFoundError(f"视频文件不存在：{source}")
        if source.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            raise ValueError(f"不支持的视频格式：{source.suffix}")

    def probe(self, source: Path) -> MediaInfo:
        self.validate_source(source)
        args = [
            self.ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration,format_name,size",
            "-of",
            "json",
            str(source),
        ]
        result = self._run(args)
        try:
            data = json.loads(result.stdout)["format"]
            return MediaInfo(float(data["duration"]), data["format_name"], int(data["size"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExternalProcessError("ffprobe 返回了无法解析的媒体信息") from exc

    def extract_wav(self, source: Path, destination: Path, overwrite: bool = True) -> None:
        self.validate_source(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        args = [
            self.ffmpeg,
            "-y" if overwrite else "-n",
            "-i",
            str(source),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(destination),
        ]
        self._run(args)

    def wav_to_mp3(self, source: Path, destination: Path, overwrite: bool = True) -> None:
        if not source.is_file():
            raise FileNotFoundError(f"音频文件不存在：{source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._run(
            [
                self.ffmpeg,
                "-y" if overwrite else "-n",
                "-i",
                str(source),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(destination),
            ]
        )

    @staticmethod
    def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                **hidden_subprocess_kwargs(),
            )
        except FileNotFoundError as exc:
            raise EnvironmentDependencyError(f"找不到外部程序：{args[0]}") from exc
        if result.returncode != 0:
            detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "未知错误"
            raise ExternalProcessError(f"{args[0]} 执行失败：{detail}")
        return result
