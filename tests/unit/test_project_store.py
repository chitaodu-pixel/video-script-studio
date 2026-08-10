from video_script_studio.services.project_store import ProjectStore
from video_script_studio.domain.errors import ProjectFormatError
import pytest


def test_project_round_trip(tmp_path) -> None:
    root = tmp_path / "demo"
    store = ProjectStore()
    project = store.create(root, "演示项目")
    loaded = store.load(root)
    assert loaded.project_id == project.project_id
    assert loaded.name == "演示项目"
    assert not (root / "project.json.tmp").exists()


def test_damaged_project_is_reported(tmp_path) -> None:
    root = tmp_path / "damaged"
    root.mkdir()
    (root / "project.json").write_text("{bad json", encoding="utf-8")
    with pytest.raises(ProjectFormatError):
        ProjectStore().load(root)
