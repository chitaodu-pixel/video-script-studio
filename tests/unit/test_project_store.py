from video_script_studio.services.project_store import ProjectStore


def test_project_round_trip(tmp_path) -> None:
    root = tmp_path / "demo"
    store = ProjectStore()
    project = store.create(root, "演示项目")
    loaded = store.load(root)
    assert loaded.project_id == project.project_id
    assert loaded.name == "演示项目"
    assert not (root / "project.json.tmp").exists()

