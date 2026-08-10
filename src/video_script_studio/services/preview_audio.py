from __future__ import annotations

from pathlib import Path


class PreviewAudioStore:
    @staticmethod
    def directory(project_root: Path) -> Path:
        return project_root / "tts" / "previews"

    def files(self, project_root: Path) -> list[Path]:
        directory = self.directory(project_root)
        return [item for item in directory.iterdir() if item.is_file()] if directory.exists() else []

    def clear(self, project_root: Path) -> int:
        deleted = 0
        for item in self.files(project_root):
            try:
                item.unlink()
                deleted += 1
            except OSError:
                continue
        return deleted
