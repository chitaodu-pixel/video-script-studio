import pytest

from video_script_studio.services.rewriter import (
    RATIOS,
    count_effective_characters,
    rewrite,
    target_character_count,
)


@pytest.mark.parametrize("ratio", RATIOS)
def test_target_ratios(ratio: float) -> None:
    assert target_character_count("一 二 三 四", ratio) == round(4 * ratio)


def test_character_count_ignores_whitespace_but_counts_punctuation() -> None:
    assert count_effective_characters("你 好。\n") == 3


def test_one_x_is_cleaned_without_fact_changes() -> None:
    result = rewrite("张伟 今年35岁。。", 1.0)
    assert result.text == "张伟 今年35岁。"

