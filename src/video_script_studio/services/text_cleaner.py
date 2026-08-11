from __future__ import annotations

import re
from dataclasses import dataclass

FILLER_PATTERN = re.compile(r"(?:呃+|嗯+|啊+|就是说|然后呢|其实呢)[，,、 ]*")
PUNCTUATION_PATTERN = re.compile(r"([，。！？；：、])\1+")
SPACE_PATTERN = re.compile(r"[ \t\u3000]+")
BLANK_LINE_PATTERN = re.compile(r"\n{3,}")

COMMON_ASR_CORRECTIONS = (
    ("因该", "应该"),
    ("应为", "因为"),
    ("即然", "既然"),
    ("必竟", "毕竟"),
    ("在坐", "在座"),
    ("帐户", "账户"),
    ("帐号", "账号"),
    ("按装", "安装"),
    ("做用", "作用"),
    ("再接再励", "再接再厉"),
    ("视屏", "视频"),
    ("文安", "文案"),
    ("洗搞", "洗稿"),
    ("像目", "项目"),
)

PHRASE_REPLACEMENTS = (
    ("需要注意的是", "这里要特别留意"),
    ("值得注意的是", "有一点值得留意"),
    ("在这个时候", "到了这一步"),
    ("在这种情况下", "面对这类情况"),
    ("与此同时", "同一时间"),
    ("除此之外", "另外还有一点"),
    ("总的来说", "综合来看"),
    ("换句话说", "从另一个角度讲"),
    ("事实上", "实际情况是"),
    ("很显然", "不难看出"),
    ("但是", "不过"),
    ("因此", "所以"),
    ("因为", "由于"),
    ("如果", "若是"),
    ("通过", "借助"),
    ("使用", "采用"),
    ("这种", "这类"),
    ("这个", "该"),
    ("可以", "能够"),
    ("非常", "十分"),
)


@dataclass(frozen=True, slots=True)
class WashResult:
    text: str
    correction_count: int
    rewrite_count: int
    similarity: float


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = FILLER_PATTERN.sub("", text)
    text = PUNCTUATION_PATTERN.sub(r"\1", text)
    text = SPACE_PATTERN.sub(" ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = BLANK_LINE_PATTERN.sub("\n\n", text)
    return text.strip()


def _replace_counted(text: str, replacements: tuple[tuple[str, str], ...]) -> tuple[str, int]:
    count = 0
    for source, replacement in replacements:
        occurrences = text.count(source)
        if occurrences:
            text = text.replace(source, replacement)
            count += occurrences
    return text, count


def _rewrite_sentence(sentence: str, relatedness: int = 70) -> tuple[str, int]:
    original = sentence
    sentence = re.sub(
        r"^因为(.+?)[，,]所以(.+?)([。！？!?]?)$",
        r"\2，之所以如此，是由于\1\3",
        sentence,
    )
    sentence = re.sub(
        r"^虽然(.+?)[，,](?:但是|但)(.+?)([。！？!?]?)$",
        r"尽管\1，\2\3",
        sentence,
    )
    sentence = re.sub(
        r"^如果(.+?)[，,](?:那么|就)(.+?)([。！？!?]?)$",
        r"要想\2，前提是\1\3",
        sentence,
    )
    sentence = re.sub(
        r"^通过(.+?)[，,]可以(.+?)([。！？!?]?)$",
        r"借助\1，便能\2\3",
        sentence,
    )
    sentence = re.sub(
        r"^(.+?)不仅(.+?)[，,]而且(.+?)([。！？!?]?)$",
        r"\1既\2，也\3\4",
        sentence,
    )
    sentence = re.sub(r"^(?:首先|第一)[，,]", "先来看，", sentence)
    sentence = re.sub(r"^(?:其次|第二)[，,]", "接着来看，", sentence)
    sentence = re.sub(r"^(?:最后|最终)[，,]", "到最后，", sentence)
    # Lower relatedness means a broader set of phrases may be replaced.
    replacement_share = {90: 0.25, 80: 0.5, 70: 1.0, 60: 1.0, 50: 1.0}[relatedness]
    replacement_count = max(1, round(len(PHRASE_REPLACEMENTS) * replacement_share))
    sentence, phrase_count = _replace_counted(sentence, PHRASE_REPLACEMENTS[:replacement_count])
    return sentence, phrase_count + int(sentence != original and phrase_count == 0)


def _ngram_similarity(left: str, right: str, size: int = 4) -> float:
    left = re.sub(r"\s+", "", left)
    right = re.sub(r"\s+", "", right)
    if left == right:
        return 1.0
    if len(left) < size or len(right) < size:
        return 0.0
    a = {left[index : index + size] for index in range(len(left) - size + 1)}
    b = {right[index : index + size] for index in range(len(right) - size + 1)}
    return len(a & b) / max(len(a | b), 1)


def wash_document(text: str, relatedness: int = 70) -> WashResult:
    if relatedness not in (50, 60, 70, 80, 90):
        raise ValueError("相关度必须是 50%、60%、70%、80% 或 90%。")
    cleaned = clean_text(text)
    corrected, correction_count = _replace_counted(cleaned, COMMON_ASR_CORRECTIONS)
    rewritten_sentences = []
    rewrite_count = 0
    for sentence in split_sentences(corrected):
        rewritten, count = _rewrite_sentence(sentence, relatedness)
        rewritten_sentences.append(rewritten)
        rewrite_count += count
    result = "\n".join(rewritten_sentences)
    return WashResult(
        text=result,
        correction_count=correction_count,
        rewrite_count=rewrite_count,
        similarity=_ngram_similarity(cleaned, result),
    )


def wash_text(text: str, relatedness: int = 70) -> str:
    return wash_document(text, relatedness).text


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.findall(r"[^。！？!?\n]+[。！？!?]?", text) if part.strip()]
