"""config.toml の読み込み（DESIGN.md 8-5）。

ファイルが無い、あるいは一部の項目が欠けていても既定値で動く。
設定ミスで打刻ウィンドウやwatcherが起動できない事態を避けるため。
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

from .paths import config_path


def _parse_time(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


@dataclass
class Break:
    name: str
    start: time
    end: time


@dataclass
class Schedule:
    day_start: time = field(default_factory=lambda: time(8, 30))
    day_end: time = field(default_factory=lambda: time(18, 0))
    slot_minutes: int = 15
    breaks: list[Break] = field(default_factory=list)


@dataclass
class Tracking:
    poll_interval_sec: int = 5
    idle_threshold_sec: int = 180
    ask_after_sec: int = 1800


@dataclass
class Button:
    label: str
    process: str
    counts_as_work: bool = True
    inherit_style: bool = True
    color: str | None = None  # 省略時はUI側の既定パレットから自動割当


@dataclass
class ProcessHint:
    name: str
    match_process: list[str] = field(default_factory=list)


@dataclass
class Choices:
    processes: list[str] = field(default_factory=list)


@dataclass
class Extract:
    style_patterns: list[str] = field(default_factory=list)


@dataclass
class Config:
    schedule: Schedule = field(default_factory=Schedule)
    tracking: Tracking = field(default_factory=Tracking)
    buttons: list[Button] = field(default_factory=list)
    extract: Extract = field(default_factory=Extract)
    process_hints: list[ProcessHint] = field(default_factory=list)
    choices: Choices = field(default_factory=Choices)

    @property
    def counts_as_work_processes(self) -> set[str]:
        """work_time に数える工程名（打刻ボタン由来）の集合。"""
        return {b.process for b in self.buttons if b.counts_as_work}

    @property
    def non_work_processes(self) -> set[str]:
        return {b.process for b in self.buttons if not b.counts_as_work}


_DEFAULT_BUTTONS = [
    Button(label="休憩", process="休憩", counts_as_work=False, inherit_style=False),
    Button(label="トワル組み", process="トワル組み", counts_as_work=True, inherit_style=True),
    Button(label="検品・確認", process="検品・確認", counts_as_work=True, inherit_style=True),
    Button(label="打合せ", process="会議・打合せ", counts_as_work=True, inherit_style=False),
]


def _default_config() -> Config:
    return Config(
        schedule=Schedule(
            breaks=[
                Break("昼休み", time(12, 0), time(13, 0)),
            ]
        ),
        buttons=list(_DEFAULT_BUTTONS),
        choices=Choices(
            processes=[
                "パターン", "グレーディング", "修正", "仕様書",
                "トワル組み", "検品・確認", "会議・打合せ", "その他",
            ]
        ),
    )


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        return _default_config()

    with path.open("rb") as f:
        raw = tomllib.load(f)

    default = _default_config()

    sched_raw = raw.get("schedule", {})
    breaks = [
        Break(b["name"], _parse_time(b["start"]), _parse_time(b["end"]))
        for b in sched_raw.get("breaks", [])
    ] or default.schedule.breaks
    schedule = Schedule(
        day_start=_parse_time(sched_raw["day_start"]) if "day_start" in sched_raw else default.schedule.day_start,
        day_end=_parse_time(sched_raw["day_end"]) if "day_end" in sched_raw else default.schedule.day_end,
        slot_minutes=sched_raw.get("slot_minutes", default.schedule.slot_minutes),
        breaks=breaks,
    )

    track_raw = raw.get("tracking", {})
    tracking = Tracking(
        poll_interval_sec=track_raw.get("poll_interval_sec", default.tracking.poll_interval_sec),
        idle_threshold_sec=track_raw.get("idle_threshold_sec", default.tracking.idle_threshold_sec),
        ask_after_sec=track_raw.get("ask_after_sec", default.tracking.ask_after_sec),
    )

    buttons_raw = raw.get("buttons", [])
    buttons = [
        Button(
            label=b["label"],
            process=b.get("process", b["label"]),
            counts_as_work=b.get("counts_as_work", True),
            inherit_style=b.get("inherit_style", True),
            color=b.get("color"),
        )
        for b in buttons_raw
    ] or default.buttons

    extract = Extract(style_patterns=raw.get("extract", {}).get("style_patterns", []))

    process_hints = [
        ProcessHint(name=h["name"], match_process=h.get("match_process", []))
        for h in raw.get("process_hints", [])
    ]

    choices = Choices(processes=raw.get("choices", {}).get("processes", default.choices.processes))

    return Config(
        schedule=schedule,
        tracking=tracking,
        buttons=buttons,
        extract=extract,
        process_hints=process_hints,
        choices=choices,
    )
