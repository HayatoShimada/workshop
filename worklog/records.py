"""L1 生ログ（window.csv / punch.csv）の行定義と追記・読込（DESIGN.md 8-1, 8-2）。

L1 は上書きせず追記のみ。ヘッダーはファイル新規作成時にだけ書く。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

WINDOW_FIELDS = ["start", "end", "duration_sec", "process", "window_title", "active"]
PUNCH_FIELDS = ["start", "end", "label", "process", "style", "ended_by"]


@dataclass
class WindowRecord:
    start: str
    end: str
    duration_sec: int
    process: str
    window_title: str
    active: bool

    def to_row(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "duration_sec": self.duration_sec,
            "process": self.process,
            "window_title": self.window_title,
            "active": "true" if self.active else "false",
        }


@dataclass
class PunchRecord:
    start: str
    end: str
    label: str
    process: str
    style: str
    ended_by: str  # pc_resume / button / late_input

    def to_row(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "label": self.label,
            "process": self.process,
            "style": self.style,
            "ended_by": self.ended_by,
        }


def _append_row(path: Path, fields: list[str], row: dict) -> None:
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def append_window_record(path: Path, record: WindowRecord) -> None:
    _append_row(path, WINDOW_FIELDS, record.to_row())


def append_punch_record(path: Path, record: PunchRecord) -> None:
    _append_row(path, PUNCH_FIELDS, record.to_row())


def read_window_records(path: Path) -> list[WindowRecord]:
    if not path.exists():
        return []
    records = []
    with path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append(
                WindowRecord(
                    start=row["start"],
                    end=row["end"],
                    duration_sec=int(row["duration_sec"]) if row["duration_sec"] else 0,
                    process=row.get("process", ""),
                    window_title=row.get("window_title", ""),
                    active=row.get("active", "").lower() == "true",
                )
            )
    return records


def read_punch_records(path: Path) -> list[PunchRecord]:
    if not path.exists():
        return []
    records = []
    with path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            records.append(
                PunchRecord(
                    start=row["start"],
                    end=row["end"],
                    label=row.get("label", ""),
                    process=row.get("process", ""),
                    style=row.get("style", ""),
                    ended_by=row.get("ended_by", ""),
                )
            )
    return records
