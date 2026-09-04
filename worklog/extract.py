"""品番の自動抽出と、プロセス名からの工程推定（DESIGN.md 9章）。

命名規則が未確認の段階でも動くよう、ルールが1つも無ければ
None を返すだけで例外にはしない。
"""

from __future__ import annotations

import re

from .config import ProcessHint


def extract_style(title: str, style_patterns: list[str]) -> str | None:
    """ウィンドウタイトルから品番らしき文字列を抜き出す。

    config.toml の extract.style_patterns を順に試し、最初に
    マッチしたものを返す。1つもマッチしなければ None。
    """
    if not title:
        return None
    for pattern in style_patterns:
        m = re.search(pattern, title)
        if m:
            return m.group(0)
    return None


def guess_process(process_name: str, hints: list[ProcessHint]) -> str | None:
    """実行ファイル名から工程を推定する（大小文字は無視）。"""
    if not process_name:
        return None
    lowered = process_name.lower()
    for hint in hints:
        for candidate in hint.match_process:
            if candidate.lower() == lowered:
                return hint.name
    return None
