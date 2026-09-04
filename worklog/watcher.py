"""worklog watch — PC操作の記録（DESIGN.md 7章・8-1・8-2b・13章）。

poll_interval_sec ごとに前面ウィンドウを見て、同じ状態が続く間は
メモリ上でまとめ、切り替わったら window.csv に1行追記する。
毎ポーリングで state.json を丸ごと書き換える。

Ctrl+C（SIGINT）/ SIGTERM を受けたら進行中の区間を flush してから
終了する（記録を止めても壊れないようにするため）。
"""

from __future__ import annotations

import signal
import time as time_module
from dataclasses import dataclass
from datetime import datetime

from .config import Config, load_config
from .extract import extract_style
from .logs import get_logger
from .paths import window_csv_path
from .records import WindowRecord, append_window_record
from .state import State, push_recent_style, write_state
from .winapi import get_foreground_process_name, get_foreground_window_title, get_idle_seconds

logger = get_logger("watcher")


@dataclass
class _Segment:
    start: datetime
    process: str
    window_title: str
    active: bool


class Watcher:
    """PC操作記録の本体。ステップ実行できるよう run() とは分離してある。"""

    def __init__(self, config: Config):
        self.config = config
        self._segment: _Segment | None = None
        self._recent_styles: list[str] = []
        self._stop = False
        self._last_active_at = ""

    def request_stop(self) -> None:
        self._stop = True

    def _current_snapshot(self, now: datetime) -> tuple[str, str, bool]:
        idle_sec = get_idle_seconds()
        active = idle_sec < self.config.tracking.idle_threshold_sec
        if not active:
            return "", "", False
        title = get_foreground_window_title()
        process = get_foreground_process_name()
        return process, title, True

    def _flush_segment(self, end: datetime, date_str: str) -> None:
        seg = self._segment
        if seg is None:
            return
        duration = int((end - seg.start).total_seconds())
        if duration <= 0:
            self._segment = None
            return
        record = WindowRecord(
            start=seg.start.isoformat(timespec="seconds"),
            end=end.isoformat(timespec="seconds"),
            duration_sec=duration,
            process=seg.process,
            window_title=seg.window_title,
            active=seg.active,
        )
        try:
            append_window_record(window_csv_path(date_str), record)
        except OSError:
            logger.exception("window.csv への書き込みに失敗しました")
        self._segment = None

    def tick(self, now: datetime | None = None) -> None:
        now = now or datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        process, title, active = self._current_snapshot(now)

        seg = self._segment
        changed = (
            seg is None
            or seg.process != process
            or seg.window_title != title
            or seg.active != active
            or seg.start.strftime("%Y-%m-%d") != date_str  # 日付をまたいだら区切る
        )
        if changed:
            self._flush_segment(now, seg.start.strftime("%Y-%m-%d") if seg else date_str)
            self._segment = _Segment(start=now, process=process, window_title=title, active=active)

        idle_sec = get_idle_seconds()
        style = extract_style(title, self.config.extract.style_patterns) if active else None
        if style:
            self._recent_styles = push_recent_style(self._recent_styles, style)

        # last_active_at は「直近で実際に操作していた時刻」。非アクティブの
        # 間も前の値を保持し続ける（打刻ウィンドウが離席の開始時刻として使う）。
        if active:
            self._last_active_at = now.isoformat(timespec="seconds")

        state = State(
            updated_at=now.isoformat(timespec="seconds"),
            active=active,
            idle_sec=round(idle_sec, 1),
            current_style=style if style else (self._recent_styles[0] if self._recent_styles else None),
            recent_styles=self._recent_styles,
            last_active_at=self._last_active_at,
        )
        try:
            write_state(state)
        except OSError:
            logger.exception("state.json への書き込みに失敗しました")

    def shutdown(self, now: datetime | None = None) -> None:
        now = now or datetime.now()
        if self._segment is not None:
            self._flush_segment(now, self._segment.start.strftime("%Y-%m-%d"))

    def run(self) -> None:
        logger.info("watcher 起動")

        def _handle_signal(signum, frame):
            logger.info("停止シグナルを受信 (%s)。区間を確定して終了します", signum)
            self.request_stop()

        signal.signal(signal.SIGINT, _handle_signal)
        try:
            signal.signal(signal.SIGTERM, _handle_signal)
        except (AttributeError, ValueError):
            pass  # SIGTERM が無いプラットフォーム向けの保険

        try:
            while not self._stop:
                try:
                    self.tick()
                except Exception:
                    logger.exception("tick 中に例外が発生しました")
                time_module.sleep(self.config.tracking.poll_interval_sec)
        finally:
            self.shutdown()
            logger.info("watcher 終了")


def main() -> int:
    config = load_config()
    Watcher(config).run()
    return 0
