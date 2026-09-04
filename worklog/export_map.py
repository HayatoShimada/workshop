"""export_map.toml の読み込み（DESIGN.md 8-6）。

社内Excelの列構成が変わっても、このファイルの書き換えだけで
対応できるようにする（コード変更不要）。
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .paths import export_map_path

VALID_SOURCES = {"date", "style", "process", "hours"}


@dataclass
class Format:
    encoding: str = "utf-8-sig"
    delimiter: str = ","
    date_format: str = "%Y/%m/%d"
    round_to: float = 0.25


@dataclass
class Column:
    header: str
    source: str  # date / style / process / hours


@dataclass
class ExportMap:
    format: Format = field(default_factory=Format)
    columns: list[Column] = field(default_factory=list)


def _default_export_map() -> ExportMap:
    return ExportMap(
        format=Format(),
        columns=[
            Column("日付", "date"),
            Column("品番", "style"),
            Column("工程", "process"),
            Column("工数(h)", "hours"),
        ],
    )


def load_export_map(path: Path | None = None) -> ExportMap:
    path = path or export_map_path()
    if not path.exists():
        return _default_export_map()

    with path.open("rb") as f:
        raw = tomllib.load(f)

    default = _default_export_map()
    fmt_raw = raw.get("format", {})
    fmt = Format(
        encoding=fmt_raw.get("encoding", default.format.encoding),
        delimiter=fmt_raw.get("delimiter", default.format.delimiter),
        date_format=fmt_raw.get("date_format", default.format.date_format),
        round_to=fmt_raw.get("round_to", default.format.round_to),
    )

    columns = [
        Column(header=c["header"], source=c["source"])
        for c in raw.get("columns", [])
    ] or default.columns

    for c in columns:
        if c.source not in VALID_SOURCES:
            raise ValueError(
                f"export_map.toml: 不明な source '{c.source}' "
                f"(使えるのは {sorted(VALID_SOURCES)})"
            )

    return ExportMap(format=fmt, columns=columns)
