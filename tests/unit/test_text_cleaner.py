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
    source = "因为我们想要使用这个重要方法，所以大家可以发现很多问题。"

    results = {level: wash_document(source, level) for level in (90, 80, 70, 60, 50)}

    assert results[90].text != results[70].text
    assert results[90].text != results[80].text
    assert results[70].text != results[60].text
    assert results[60].text != results[50].text
    assert results[90].similarity > results[70].similarity > results[50].similarity
