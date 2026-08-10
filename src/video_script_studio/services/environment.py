from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

from video_script_studio.services.subprocess_utils import hidden_subprocess_kwargs


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    name: str
    available: bool
    path: str | None
    version: str | None
    guidance: str | None = None


def _executable_status(name: str, version_args: list[str], guidance: str) -> DependencyStatus:
    path = shutil.which(name)
    if path is None:
        return DependencyStatus(name, False, None, None, guidance)
    try:
        result = subprocess.run(
            [path, *version_args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            **hidden_subprocess_kwargs(),
        )
        first_line = (result.stdout or result.stderr).splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        first_line = "已找到，但无法读取版本"
    return DependencyStatus(name, True, path, first_line)


def check_environment() -> list[DependencyStatus]:
    python_ok = sys.version_info[:2] == (3, 11)
    python = DependencyStatus(
        "Python",
        python_ok,
        sys.executable,
        sys.version.split()[0],
        None if python_ok else "请安装并使用 Python 3.11 x64 创建虚拟环境。",
    )
    return [
        python,
        _executable_status("ffmpeg", ["-version"], "请安装 FFmpeg 并将 bin 目录加入 PATH。"),
        _executable_status("ffprobe", ["-version"], "请安装 FFmpeg 并将 bin 目录加入 PATH。"),
    ]
