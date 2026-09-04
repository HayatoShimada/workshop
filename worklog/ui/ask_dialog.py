"""押し忘れの問いかけパネル（DESIGN.md 6章）。

打刻なしで一定時間（ask_after_sec）離席していたことを watcher が
検知した場合に、復帰時にこのパネルを表示する。ボタンを選べば
late_input として遡って記録し、「あとで」を選べば何もしない
（未記録のまま日次確定に回る）。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from datetime import datetime

from ..config import Button


def _fmt_hm(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def build_ask_panel(
    parent: tk.Widget,
    away_start: datetime,
    away_end: datetime,
    buttons: list[Button],
    on_choose: Callable[[Button], None],
    on_later: Callable[[], None],
) -> tk.Frame:
    """押し忘れ問いかけパネルを作って返す。呼び出し側で pack/grid する。"""
    minutes = max(1, round((away_end - away_start).total_seconds() / 60))
    frame = tk.Frame(parent, bg="#fff3cd", bd=1, relief="solid")

    message = f"{_fmt_hm(away_start)} 〜 {_fmt_hm(away_end)} の{minutes}分、離席していました"
    tk.Label(frame, text=message, bg="#fff3cd", font=("Yu Gothic UI", 9), wraplength=380, justify="left").pack(
        fill="x", padx=8, pady=(6, 4)
    )

    btn_row = tk.Frame(frame, bg="#fff3cd")
    btn_row.pack(fill="x", padx=8)
    for button_cfg in buttons:
        b = tk.Button(
            btn_row,
            text=button_cfg.label,
            command=lambda bc=button_cfg: on_choose(bc),
        )
        b.pack(side="left", padx=2, pady=2, fill="x", expand=True)

    later_row = tk.Frame(frame, bg="#fff3cd")
    later_row.pack(fill="x", padx=8, pady=(2, 6))
    tk.Button(later_row, text="あとで（日次確定で入力する）", command=on_later).pack(fill="x")

    return frame
