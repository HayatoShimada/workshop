"""worklog export --month — 転記用CSVの出力（DESIGN.md 8-4, 8-6）。

data/committed/ の当月分を (日付, 品番, 工程) で集計する。
counts_as_work=false の工程（休憩など）と、品番・工程が空の行
（休憩・未記録の状態）は出力しない。列構成は export_map.toml から
組み立てるので、社内Excelの列が変わってもコード変更は不要。
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_cls
from pathlib import Path

from .config import Config
from .export_map import ExportMap
from .paths import committed_dir, export_csv_path
from .timeline import STATE_BREAK, STATE_NONE, read_timeline_csv


@dataclass
class ExportRow:
    date: date_cls
    style: str
    process: str
    hours: float


def _committed_files_for_month(month: str) -> list[Path]:
    prefix_dir = committed_dir()
    return sorted(p for p in prefix_dir.glob(f"{month}-*_timeline.csv") if p.is_file())


def aggregate_month(month: str, config: Config) -> list[ExportRow]:
    """month は 'YYYY-MM' 形式。"""
    slot_hours = config.schedule.slot_minutes / 60.0
    totals: dict[tuple[date_cls, str, str], float] = defaultdict(float)

    for path in _committed_files_for_month(month):
        date_str = path.name.split("_timeline.csv")[0]
        try:
            day = date_cls.fromisoformat(date_str)
        except ValueError:
            continue

        for row in read_timeline_csv(path):
            if row.state in (STATE_BREAK, STATE_NONE):
                continue
            if not row.process:
                # 工程が無い（未記録・休憩など）行は集計しない。
                # 品番が空でも工程があれば集計する（例: 打合せは品番と
                # 紐付かないことが多いが、counts_as_work=true の作業時間
                # を落とすと DESIGN.md 1章の「精度が上がる」に反する）。
                continue
            if row.process in config.non_work_processes:
                continue
            totals[(day, row.style, row.process)] += slot_hours

    return [
        ExportRow(date=d, style=style, process=process, hours=round(hours, 4))
        for (d, style, process), hours in sorted(totals.items())
    ]


def _round_to(value: float, step: float) -> float:
    if step <= 0:
        return value
    return round(value / step) * step


def _row_value(row: ExportRow, source: str, export_map: ExportMap) -> str:
    if source == "date":
        return row.date.strftime(export_map.format.date_format)
    if source == "style":
        return row.style
    if source == "process":
        return row.process
    if source == "hours":
        hours = _round_to(row.hours, export_map.format.round_to)
        # 0.25 刻みなら小数第2位まで、綺麗な値なら余計な0を付けない
        text = f"{hours:.2f}".rstrip("0").rstrip(".")
        return text if text else "0"
    raise ValueError(f"未知の source: {source}")


def write_export_csv(path: Path, rows: list[ExportRow], export_map: ExportMap) -> None:
    with path.open("w", newline="", encoding=export_map.format.encoding) as f:
        writer = csv.writer(f, delimiter=export_map.format.delimiter)
        writer.writerow([c.header for c in export_map.columns])
        for row in rows:
            writer.writerow([_row_value(row, c.source, export_map) for c in export_map.columns])


def export_month(month: str, config: Config, export_map: ExportMap) -> Path:
    rows = aggregate_month(month, config)
    out_path = export_csv_path(month)
    write_export_csv(out_path, rows, export_map)
    return out_path
