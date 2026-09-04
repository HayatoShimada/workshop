"""state.json の読み書き（DESIGN.md 8-2b）。

watcher が書き、打刻ウィンドウが読むだけの一方向ファイル。
キー名は DESIGN.md の形式ちょうどに合わせる（打刻ウィンドウ側が
このキー名に依存しているため、勝手に変えない）。

書き込みは一時ファイル + os.replace でアトミックに行い、
読む側が書きかけの壊れた JSON を掴まないようにする。
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime

from .paths import state_path


@dataclass
class State:
    updated_at: str = ""
    active: bool = False
    idle_sec: float = 0.0
    current_style: str | None = None
    recent_styles: list[str] = field(default_factory=list)
    last_active_at: str = ""


def write_state(state: State) -> None:
    path = state_path()
    tmp_path = path.with_suffix(".json.tmp")
    payload = asdict(state)
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def read_state() -> State | None:
    """state.json を読む。無い・壊れている場合は None を返す。

    打刻ウィンドウ側はこれが None のとき「品番なし・操作状態不明」
    として動作を続ける（watcher が落ちても打刻はできる）。
    """
    path = state_path()
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return State(
            updated_at=raw.get("updated_at", ""),
            active=bool(raw.get("active", False)),
            idle_sec=float(raw.get("idle_sec", 0.0)),
            current_style=raw.get("current_style"),
            recent_styles=list(raw.get("recent_styles", [])),
            last_active_at=raw.get("last_active_at", ""),
        )
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return None


def push_recent_style(recent: list[str], style: str | None, limit: int = 5) -> list[str]:
    """MRU（最近使った順）で品番リストを更新する。"""
    if not style:
        return recent
    updated = [style] + [s for s in recent if s != style]
    return updated[:limit]
