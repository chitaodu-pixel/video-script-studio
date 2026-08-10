from __future__ import annotations

import re

FILLER_PATTERN = re.compile(r"(?<!\w)(?:呃+|嗯+|那个|就是说|然后呢|其实呢)(?!\w)")
PUNCTUATION_PATTERN = re.compile(r"([，。！？；：、])\1+")
SPACE_PATTERN = re.compile(r"[ \t\u3000]+")
BLANK_LINE_PATTERN = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = FILLER_PATTERN.sub("", text)
    text = PUNCTUATION_PATTERN.sub(r"\1", text)
    text = SPACE_PATTERN.sub(" ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = BLANK_LINE_PATTERN.sub("\n\n", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.findall(r"[^。！？!?\n]+[。！？!?]?", text) if part.strip()]

