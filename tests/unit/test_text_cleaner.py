from video_script_studio.services.text_cleaner import clean_text


def test_clean_text_is_idempotent() -> None:
    source = "  呃  这是测试。。。。\n\n\n下一段  "
    once = clean_text(source)
    assert clean_text(once) == once
    assert "。。" not in once

