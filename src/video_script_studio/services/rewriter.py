from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from video_script_studio.services.text_cleaner import clean_text, split_sentences

RATIOS = (0.5, 0.75, 1.0, 1.5, 2.0)


def count_effective_characters(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def target_character_count(text: str, ratio: float) -> int:
    if ratio not in RATIOS:
        raise ValueError(f"不支持的字数倍率：{ratio}")
    return round(count_effective_characters(text) * ratio)


@dataclass(frozen=True, slots=True)
class RewriteResult:
    text: str
    source_count: int
    target_count: int
    actual_count: int
    within_tolerance: bool


def _keywords(sentences: list[str]) -> Counter[str]:
    chars = (char for sentence in sentences for char in sentence if "\u4e00" <= char <= "\u9fff")
    return Counter(chars)


def _compress(sentences: list[str], target: int) -> str:
    if not sentences:
        return ""
    frequencies = _keywords(sentences)
    scored = []
    for index, sentence in enumerate(sentences):
        content = re.sub(r"\W", "", sentence)
        score = sum(frequencies[char] for char in content) / max(len(content), 1)
        if index in (0, len(sentences) - 1):
            score *= 1.25
        scored.append((score, index, sentence))
    selected: list[tuple[int, str]] = []
    used = 0
    for _, index, sentence in sorted(scored, reverse=True):
        length = count_effective_characters(sentence)
        if used + length <= target or not selected:
            selected.append((index, sentence))
            used += length
    return "".join(sentence for _, sentence in sorted(selected))


def _expand(text: str, target: int) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return text
    additions = [
        "换句话说，这一点仍然要以原文已经给出的事实为基础。",
        "从上下文来看，前后的原因与结果需要放在一起理解。",
        "这里需要强调的是，相关人物、时间和事件并没有发生变化。",
        "综合这些信息，可以更清楚地看到原文想要表达的重点。",
    ]
    output: list[str] = []
    addition_index = 0
    for sentence in sentences:
        output.append(sentence)
        if count_effective_characters("".join(output)) < target:
            output.append(additions[addition_index % len(additions)])
            addition_index += 1
    while count_effective_characters("".join(output)) < target:
        output.append(additions[addition_index % len(additions)])
        addition_index += 1
    return "".join(output)


def rewrite(text: str, ratio: float, mode: str = "faithful", tolerance: float = 0.10) -> RewriteResult:
    cleaned = clean_text(text)
    source_count = count_effective_characters(cleaned)
    target = target_character_count(cleaned, ratio)
    if ratio < 1:
        result = _compress(split_sentences(cleaned), target)
    elif ratio == 1:
        result = cleaned
    else:
        result = _expand(cleaned, target)
    actual = count_effective_characters(result)
    allowed = max(1, math.ceil(target * tolerance))
    return RewriteResult(result, source_count, target, actual, abs(actual - target) <= allowed)

