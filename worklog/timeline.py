"""L2 日次タイムラインの生成（DESIGN.md 8-3）。

15分刻みのスロットごとに、状態を 打刻 ＞ 休憩設定 ＞ PC操作 ＞ 未記録
の優先順位で決め、品番・工程のヒントを事前入力する。
本人が実際に手を動かすのは「未記録」の行だけになるよう作る。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date as date_cls
from datetime import datetime, timedelta
from pathlib import Path

from .config import Config
from .extract import extract_style, guess_process
from .paths import punch_csv_path, window_csv_path
from .records import PunchRecord, WindowRecord, read_punch_records, read_window_records

TIMELINE_FIELDS = ["時刻", "状態", "ヒント", "品番", "工程", "メモ"]

STATE_PUNCH = "打刻"
STATE_BREAK = "休憩"
STATE_PC = "PC"
STATE_NONE = "未記録"


@dataclass
class TimelineRow:
    time_label: str
    state: str
    hint: str
    style: str
    process: str
    note: str = ""

    def to_row(self) -> dict:
        return {
            "時刻": self.time_label,
            "状態": self.state,
            "ヒント": self.hint,
            "品番": self.style,
            "工程": self.process,
            "メモ": self.note,
        }


def _overlap_seconds(slot_start: datetime, slot_end: datetime, rec_start: datetime, rec_end: datetime) -> float:
    latest_start = max(slot_start, rec_start)
    earliest_end = min(slot_end, rec_end)
    delta = (earliest_end - latest_start).total_seconds()
    return max(0.0, delta)


def _best_punch(slot_start: datetime, slot_end: datetime, punches: list[PunchRecord]) -> PunchRecord | None:
    best = None
    best_overlap = 0.0
    for p in punches:
        try:
            p_start = datetime.fromisoformat(p.start)
            p_end = datetime.fromisoformat(p.end)
        except ValueError:
            continue
        overlap = _overlap_seconds(slot_start, slot_end, p_start, p_end)
        if overlap > best_overlap:
            best_overlap = overlap
            best = p
    return best


def _best_window(slot_start: datetime, slot_end: datetime, windows: list[WindowRecord]) -> WindowRecord | None:
    best = None
    best_overlap = 0.0
    for w in windows:
        if not w.active:
            continue
        try:
            w_start = datetime.fromisoformat(w.start)
            w_end = datetime.fromisoformat(w.end)
        except ValueError:
            continue
        overlap = _overlap_seconds(slot_start, slot_end, w_start, w_end)
        if overlap > best_overlap:
            best_overlap = overlap
            best = w
    return best


def _is_break(slot_start: datetime, config: Config) -> str | None:
    t = slot_start.time()
    for b in config.schedule.breaks:
        if b.start <= t < b.end:
            return b.name
    return None


def generate_timeline(date: date_cls, config: Config) -> list[TimelineRow]:
    window_records = read_window_records(window_csv_path(date.isoformat()))
    punch_records = read_punch_records(punch_csv_path(date.isoformat()))

    day_start = datetime.combine(date, config.schedule.day_start)
    day_end = datetime.combine(date, config.schedule.day_end)
    slot_delta = timedelta(minutes=config.schedule.slot_minutes)

    rows: list[TimelineRow] = []
    slot_start = day_start
    while slot_start < day_end:
        slot_end = min(slot_start + slot_delta, day_end)
        time_label = slot_start.strftime("%H:%M")

        punch = _best_punch(slot_start, slot_end, punch_records)
        if punch is not None:
            rows.append(TimelineRow(time_label, STATE_PUNCH, punch.label, punch.style, punch.process))
            slot_start = slot_end
            continue

        break_name = _is_break(slot_start, config)
        if break_name is not None:
            rows.append(TimelineRow(time_label, STATE_BREAK, "", "", ""))
            slot_start = slot_end
            continue

        window = _best_window(slot_start, slot_end, window_records)
        if window is not None:
            style = extract_style(window.window_title, config.extract.style_patterns) or ""
            process = guess_process(window.process, config.process_hints) or ""
            rows.append(TimelineRow(time_label, STATE_PC, window.window_title, style, process))
            slot_start = slot_end
            continue

        rows.append(TimelineRow(time_label, STATE_NONE, "", "", ""))
        slot_start = slot_end

    return rows


def write_timeline_csv(path: Path, rows: list[TimelineRow]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=TIMELINE_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_row())


def read_timeline_csv(path: Path) -> list[TimelineRow]:
    rows = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(
                TimelineRow(
                    time_label=r.get("時刻", ""),
                    state=r.get("状態", ""),
                    hint=r.get("ヒント", ""),
                    style=r.get("品番", ""),
                    process=r.get("工程", ""),
                    note=r.get("メモ", ""),
                )
            )
    return rows
