from __future__ import annotations

import re

from video_script_studio.domain.models import ReplacementRule


def validate_rules(rules: list[ReplacementRule]) -> None:
    enabled = [rule for rule in rules if rule.enabled]
    if any(not rule.source or not rule.target for rule in enabled):
        raise ValueError("启用的替换规则不能包含空值")
    sources = [rule.source for rule in enabled]
    if len(sources) != len(set(sources)):
        raise ValueError("替换规则包含重复的原词")


def apply_replacements(text: str, rules: list[ReplacementRule]) -> str:
    validate_rules(rules)
    mapping = {rule.source: rule.target for rule in rules if rule.enabled}
    if not mapping:
        return text
    pattern = re.compile("|".join(re.escape(key) for key in sorted(mapping, key=len, reverse=True)))
    return pattern.sub(lambda match: mapping[match.group(0)], text)

