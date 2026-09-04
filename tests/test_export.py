import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from worklog.config import Button, Config, Schedule
from worklog.export import aggregate_month, write_export_csv
from worklog.export_map import Column, ExportMap, Format
from worklog.timeline import TimelineRow, write_timeline_csv


def _make_config() -> Config:
    return Config(
        schedule=Schedule(slot_minutes=15),
        buttons=[
            Button(label="休憩", process="休憩", counts_as_work=False, inherit_style=False),
            Button(label="トワル組み", process="トワル組み", counts_as_work=True, inherit_style=True),
        ],
    )


class TestAggregateMonth(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.committed_dir = Path(self.tmpdir.name)
        patcher = patch("worklog.export.committed_dir", return_value=self.committed_dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)

    def _write_day(self, date_str: str, rows: list[TimelineRow]) -> None:
        write_timeline_csv(self.committed_dir / f"{date_str}_timeline.csv", rows)

    def test_excludes_break_and_unrecorded(self):
        rows = [
            TimelineRow("08:30", "PC", "", "25AW-BL-1234", "パターン"),
            TimelineRow("08:45", "休憩", "", "", ""),
            TimelineRow("09:00", "未記録", "", "", ""),
        ]
        self._write_day("2026-09-01", rows)
        result = aggregate_month("2026-09", _make_config())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].process, "パターン")
        self.assertAlmostEqual(result[0].hours, 0.25)

    def test_excludes_counts_as_work_false(self):
        rows = [
            TimelineRow("08:30", "打刻", "休憩", "", "休憩"),
        ]
        self._write_day("2026-09-01", rows)
        result = aggregate_month("2026-09", _make_config())
        self.assertEqual(result, [])

    def test_keeps_work_with_empty_style(self):
        # inherit_style=false のボタン由来で品番が空でも、work_time は残す
        rows = [TimelineRow("08:30", "打刻", "打合せ", "", "会議・打合せ")]
        self._write_day("2026-09-01", rows)
        result = aggregate_month("2026-09", _make_config())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].style, "")
        self.assertEqual(result[0].process, "会議・打合せ")

    def test_aggregates_multiple_slots_same_key(self):
        rows = [
            TimelineRow("08:30", "打刻", "", "25AW-BL-1234", "トワル組み"),
            TimelineRow("08:45", "打刻", "", "25AW-BL-1234", "トワル組み"),
            TimelineRow("09:00", "打刻", "", "25AW-BL-1234", "トワル組み"),
        ]
        self._write_day("2026-09-01", rows)
        result = aggregate_month("2026-09", _make_config())
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0].hours, 0.75)

    def test_only_matching_month_included(self):
        self._write_day("2026-08-31", [TimelineRow("08:30", "PC", "", "S1", "パターン")])
        self._write_day("2026-09-01", [TimelineRow("08:30", "PC", "", "S2", "パターン")])
        result = aggregate_month("2026-09", _make_config())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].style, "S2")


class TestWriteExportCsv(unittest.TestCase):
    def test_columns_and_rounding_follow_export_map(self):
        from worklog.export import ExportRow
        from datetime import date

        export_map = ExportMap(
            format=Format(encoding="utf-8", delimiter=",", date_format="%Y-%m-%d", round_to=0.25),
            columns=[Column("工程", "process"), Column("時間", "hours")],
        )
        rows = [ExportRow(date=date(2026, 9, 1), style="S1", process="パターン", hours=1.2499)]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.csv"
            write_export_csv(out, rows, export_map)
            content = out.read_text(encoding="utf-8")
        lines = content.strip().splitlines()
        self.assertEqual(lines[0], "工程,時間")
        self.assertEqual(lines[1], "パターン,1.25")


if __name__ == "__main__":
    unittest.main()
