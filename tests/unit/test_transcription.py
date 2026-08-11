from pathlib import Path

import pytest

from video_script_studio.domain.models import TranscriptSegment
from video_script_studio.services.transcription import TranscriptionService, format_transcript_text


def test_format_transcript_uses_sentences_pauses_and_line_length() -> None:
    segments = [
        TranscriptSegment(0, 1, "第一句话。"),
        TranscriptSegment(1.1, 2, "第二句没有标点"),
        TranscriptSegment(3.5, 4, "停顿后另起一行"),
    ]

    assert format_transcript_text(segments) == "第一句话。\n第二句没有标点。\n停顿后另起一行。"


def test_format_transcript_wraps_long_unpunctuated_content() -> None:
    segments = [TranscriptSegment(0, 1, "一" * 25), TranscriptSegment(1, 2, "二" * 25)]

    assert format_transcript_text(segments, max_line_characters=45) == "一" * 25 + "，\n" + "二" * 25 + "。"


def test_format_transcript_restores_chinese_punctuation_and_questions() -> None:
    segments = [
        TranscriptSegment(0, 1, "你知道为什么吗?"),
        TranscriptSegment(1.1, 2, "因为这个方法"),
        TranscriptSegment(2.5, 3, "非常重要"),
    ]

    assert format_transcript_text(segments) == "你知道为什么吗？\n因为这个方法，非常重要。"


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
