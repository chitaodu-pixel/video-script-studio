import pytest

from video_script_studio.domain.models import ReplacementRule
from video_script_studio.services.replacement import apply_replacements


def test_replacement_does_not_cascade() -> None:
    rules = [ReplacementRule("张伟", "李明"), ReplacementRule("李明", "王强")]
    assert apply_replacements("张伟和李明", rules) == "李明和王强"


def test_longest_source_wins() -> None:
    rules = [ReplacementRule("北京", "广州"), ReplacementRule("北京大学", "中山大学")]
    assert apply_replacements("北京大学在北京", rules) == "中山大学在广州"


def test_duplicate_source_is_rejected() -> None:
    with pytest.raises(ValueError):
        apply_replacements("文本", [ReplacementRule("文", "A"), ReplacementRule("文", "B")])

