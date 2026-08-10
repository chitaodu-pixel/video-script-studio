from __future__ import annotations

import json
import os
from pathlib import Path

from video_script_studio.domain.errors import ProjectFormatError
from video_script_studio.domain.models import Project


PROJECT_DIRS = (
    "media",
    "audio",
    "transcript",
    "rewrite",
    "tts",
    "exports",
    "logs",
)


class ProjectStore:
    def create(self, root: Path, name: str) -> Project:
        root.mkdir(parents=True, exist_ok=False)
        for directory in PROJECT_DIRS:
            (root / directory).mkdir()
        project = Project(name=name)
        self.save(root, project)
        return project

    def save(self, root: Path, project: Project) -> None:
        root.mkdir(parents=True, exist_ok=True)
        for directory in PROJECT_DIRS:
            (root / directory).mkdir(exist_ok=True)
        project.touch()
        target = root / "project.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(project.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, target)

    def load(self, root: Path) -> Project:
        path = root / "project.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Project.from_dict(data)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ProjectFormatError(f"无法打开项目文件：{path}") from exc

