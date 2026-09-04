import tempfile
import unittest
from datetime import date, time
from pathlib import Path
from unittest.mock import patch

from worklog.config import Break, Config, Extract, ProcessHint, Schedule, Tracking
from worklog.records import PunchRecord, WindowRecord, append_punch_record, append_window_record
from worklog.timeline import STATE_BREAK, STATE_NONE, STATE_PC, STATE_PUNCH, generate_timeline


def _make_config(**overrides) -> Config:
    schedule = Schedule(
        day_start=time(9, 0),
        day_end=time(11, 0),
        slot_minutes=15,
        breaks=[Break("昼休み", time(10, 0), time(10, 15))],
    )
    return Config(
        schedule=schedule,
        tracking=Tracking(),
        buttons=[],
        extract=Extract(style_patterns=[r"\d{2}[ASFW]{2}-[A-Z]{2}-\d{4}"]),
        process_hints=[ProcessHint(name="パターン", match_process=["AGMS.exe"])],
    )


class TestGenerateTimeline(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.window_path = Path(self.tmpdir.name) / "window.csv"
        self.punch_path = Path(self.tmpdir.name) / "punch.csv"
        patcher1 = patch("worklog.timeline.window_csv_path", return_value=self.window_path)
        patcher2 = patch("worklog.timeline.punch_csv_path", return_value=self.punch_path)
        patcher1.start()
        patcher2.start()
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.addCleanup(self.tmpdir.cleanup)

    def test_punch_overrides_pc_activity(self):
        # 同じ時間帯にPC操作と打刻の両方がある場合、打刻を優先する
        append_window_record(
            self.window_path,
            WindowRecord("2026-09-01T09:00:00", "2026-09-01T09:30:00", 1800, "AGMS.exe", "25AW-BL-1234 - AGMS", True),
        )
        append_punch_record(
            self.punch_path,
            PunchRecord("2026-09-01T09:00:00", "2026-09-01T09:30:00", "打合せ", "会議・打合せ", "", "button"),
        )
        config = _make_config()
        rows = generate_timeline(date(2026, 9, 1), config)
        first_two = rows[:2]
        for r in first_two:
            self.assertEqual(r.state, STATE_PUNCH)
            self.assertEqual(r.hint, "打合せ")

    def test_break_slot_is_filled_automatically(self):
        config = _make_config()
        rows = generate_timeline(date(2026, 9, 1), config)
        break_row = next(r for r in rows if r.time_label == "10:00")
        self.assertEqual(break_row.state, STATE_BREAK)
        self.assertEqual(break_row.style, "")

    def test_gap_becomes_unrecorded(self):
        config = _make_config()
        rows = generate_timeline(date(2026, 9, 1), config)
        # window/punch とも何も無いので、休憩スロット以外は全て未記録
        non_break = [r for r in rows if r.state != STATE_BREAK]
        self.assertTrue(all(r.state == STATE_NONE for r in non_break))
        self.assertTrue(all(r.style == "" and r.process == "" for r in non_break))

    def test_pc_row_extracts_style_and_process_hints(self):
        append_window_record(
            self.window_path,
            WindowRecord("2026-09-01T09:00:00", "2026-09-01T09:15:00", 900, "AGMS.exe", "25AW-BL-1234 パターン - AGMS", True),
        )
        config = _make_config()
        rows = generate_timeline(date(2026, 9, 1), config)
        pc_row = rows[0]
        self.assertEqual(pc_row.state, STATE_PC)
        self.assertEqual(pc_row.style, "25AW-BL-1234")
        self.assertEqual(pc_row.process, "パターン")

    def test_inactive_window_segment_does_not_count_as_pc(self):
        append_window_record(
            self.window_path,
            WindowRecord("2026-09-01T09:00:00", "2026-09-01T09:15:00", 900, "", "", False),
        )
        config = _make_config()
        rows = generate_timeline(date(2026, 9, 1), config)
        self.assertEqual(rows[0].state, STATE_NONE)


if __name__ == "__main__":
    unittest.main()
