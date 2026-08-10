from pathlib import Path

import video_script_studio.portable_app as portable_app


def test_resolve_app_root_prefers_working_project(tmp_path, monkeypatch) -> None:
    project = tmp_path / "video-script-studio"
    project.mkdir()
    (project / "models").mkdir()
    monkeypatch.chdir(project)

    assert portable_app.resolve_app_root() == Path.cwd()


def test_resolve_app_root_uses_exe_directory_when_packaged(tmp_path, monkeypatch) -> None:
    executable = tmp_path / "dist" / "VideoScriptStudio.exe"
    monkeypatch.setattr(portable_app.sys, "frozen", True, raising=False)
    monkeypatch.setattr(portable_app.sys, "executable", str(executable))

    assert portable_app.resolve_app_root() == executable.parent
