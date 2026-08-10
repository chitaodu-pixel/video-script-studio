import json
from pathlib import Path
from subprocess import CompletedProcess

from video_script_studio.services.media import MediaService


def test_probe_uses_argument_list_and_supports_space_path(monkeypatch, tmp_path) -> None:
    source = tmp_path / "中文 视频.mp4"
    source.write_bytes(b"fixture")
    captured = []

    def fake_run(args, **_kwargs):
        captured.append(args)
        payload = {"format": {"duration": "2.5", "format_name": "mov,mp4", "size": "7"}}
        return CompletedProcess(args, 0, json.dumps(payload), "")

    monkeypatch.setattr("subprocess.run", fake_run)
    info = MediaService().probe(source)
    assert info.duration == 2.5
    assert captured[0][-1] == str(source)
    assert isinstance(captured[0], list)


def test_extract_wav_builds_required_pcm_arguments(monkeypatch, tmp_path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fixture")
    destination = tmp_path / "output" / "source.wav"
    captured = []

    def fake_run(args, **_kwargs):
        captured.append(args)
        return CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("subprocess.run", fake_run)
    MediaService().extract_wav(source, destination)
    assert ["-ac", "1", "-ar", "16000"] == captured[0][captured[0].index("-ac") : -1]
    assert captured[0][-1] == str(destination)

