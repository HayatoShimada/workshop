"""worklog commit — 編集済みタイムラインの取り込み（DESIGN.md 7章）。

本人が Excel で編集した data/daily/*_timeline.csv を読み、
data/committed/*_timeline.csv として確定コピーを保存する。
L1（生ログ）は一切変更しない。
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import date as date_cls

from .config import Config
from .paths import committed_csv_path, timeline_csv_path
from .timeline import STATE_NONE, read_timeline_csv


@dataclass
class CommitResult:
    committed: bool
    unresolved_rows: list[str]  # 状態=未記録 のまま残っている時刻
    unknown_processes: list[str]  # choices.processes に無い工程名


def commit_day(date: date_cls, config: Config) -> CommitResult:
    src = timeline_csv_path(date.isoformat())
    if not src.exists():
        raise FileNotFoundError(
            f"タイムラインが見つかりません: {src}  先に 'worklog day --date {date.isoformat()}' を実行してください"
        )

    rows = read_timeline_csv(src)

    unresolved = [r.time_label for r in rows if r.state == STATE_NONE and not (r.style and r.process)]
    known_processes = set(config.choices.processes) | {b.process for b in config.buttons}
    unknown = sorted(
        {r.process for r in rows if r.process and r.process not in known_processes}
    )

    dst = committed_csv_path(date.isoformat())
    shutil.copyfile(src, dst)

    return CommitResult(committed=True, unresolved_rows=unresolved, unknown_processes=unknown)
