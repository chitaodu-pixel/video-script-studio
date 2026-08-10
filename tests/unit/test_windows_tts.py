import json
from subprocess import CompletedProcess

from video_script_studio.services.windows_tts import WindowsTTSService


def test_voice_lookup_runs_powershell_without_a_console(monkeypatch) -> None:
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return CompletedProcess(args, 0, json.dumps(["Voice A"]), "")

    monkeypatch.setattr("subprocess.run", fake_run)
    assert WindowsTTSService().voices() == ["Voice A"]
    assert "-NonInteractive" in captured["args"]
    assert captured["kwargs"].get("creationflags", 0) != 0
