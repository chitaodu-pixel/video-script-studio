from pathlib import Path

import pytest

from video_script_studio.services.transcription import TranscriptionService


def test_resolve_model_uses_configured_local_directory(monkeypatch, tmp_path) -> None:
    model = tmp_path / "model"
    model.mkdir()
    for name in ("config.json", "model.bin", "tokenizer.json", "vocabulary.txt"):
        (model / name).write_bytes(b"fixture")
    monkeypatch.setenv("VSS_WHISPER_MODEL", str(model))
    assert TranscriptionService.resolve_model("small") == str(model)


def test_resolve_model_rejects_incomplete_directory(monkeypatch, tmp_path) -> None:
    model = tmp_path / "incomplete"
    model.mkdir()
    (model / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("VSS_WHISPER_MODEL", str(model))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.executable", str(tmp_path / "bin" / "app.exe"))
    with pytest.raises(RuntimeError, match="找不到本地 Whisper 模型"):
        TranscriptionService.resolve_model("small")
