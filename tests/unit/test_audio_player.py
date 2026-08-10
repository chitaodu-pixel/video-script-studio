from pathlib import Path

from video_script_studio.services.audio_player import WindowsAudioPlayer


def test_player_opens_mp3_and_starts_from_beginning(monkeypatch, tmp_path) -> None:
    audio = tmp_path / "试听 文件.mp3"
    audio.write_bytes(b"fixture")
    player = WindowsAudioPlayer()
    commands = []
    monkeypatch.setattr(player, "stop", lambda: commands.append("stop"))
    monkeypatch.setattr(player, "_send", lambda command: commands.append(command) or "")
    player.play(audio)
    assert commands[0] == "stop"
    assert commands[1] == f'open "{audio}" type mpegvideo alias {player.ALIAS}'
    assert commands[2] == f"play {player.ALIAS} from 0"


def test_player_rejects_missing_audio(tmp_path) -> None:
    player = WindowsAudioPlayer()
    missing = Path(tmp_path / "missing.mp3")
    try:
        player.play(missing)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing audio should fail")
