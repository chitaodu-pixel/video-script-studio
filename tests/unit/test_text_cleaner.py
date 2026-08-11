from video_script_studio.services.text_cleaner import clean_text, wash_document, wash_text


def test_clean_text_is_idempotent() -> None:
    source = "  呃  这是测试。。。。\n\n\n下一段  "
    once = clean_text(source)
    assert clean_text(once) == once
    assert "。。" not in once


def test_clean_text_removes_fillers_inside_chinese_sentence() -> None:
    assert clean_text("今天嗯，然后呢我们开始。") == "今天我们开始。"


def test_wash_text_visibly_paraphrases_without_changing_numbers() -> None:
    source = "如果使用这个方法，可以节省30分钟，但是需要注意的是成本。"
    result = wash_text(source)
    assert result != source
    assert "30" in result
    assert "若是" in result
    assert "采用" in result


def test_wash_document_corrects_asr_error_and_restructures_sentence() -> None:
    source = "因为这个像目使用了新方法，所以可以节省30分钟。"
    result = wash_document(source)
    assert "项目" in result.text
    assert "30" in result.text
    assert result.correction_count == 1
    assert result.rewrite_count > 0
    assert result.similarity < 1


def test_relatedness_controls_replacement_scope() -> None:
    source = "这个方法可以使用，这种方式非常方便。"

    conservative = wash_document(source, 90)
    stronger = wash_document(source, 70)

    assert conservative.text != stronger.text
    assert stronger.rewrite_count > conservative.rewrite_count
