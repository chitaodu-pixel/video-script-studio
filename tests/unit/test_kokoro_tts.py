from pathlib import Path

from video_script_studio.services.kokoro_tts import KokoroTTSService


def test_offline_neural_voice_list_has_two_female_and_two_male(monkeypatch) -> None:
    monkeypatch.setattr(
        KokoroTTSService, "resolve_model_dir", staticmethod(lambda: Path("models"))
    )

    voices = KokoroTTSService().voices()

    assert [voice.voice_id for voice in voices] == ["zf_001", "zf_002", "zm_009", "zm_010"]
    assert sum(voice.display_name.startswith("女声") for voice in voices) == 2
    assert sum(voice.display_name.startswith("男声") for voice in voices) == 2


def test_long_phonemes_are_split_below_model_limit() -> None:
    chunks = KokoroTTSService._chunk_phonemes("一" * 900)

    assert "".join(chunks) == "一" * 900
    assert max(map(len, chunks)) <= 400
