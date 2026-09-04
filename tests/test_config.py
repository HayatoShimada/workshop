import tempfile
import unittest
from datetime import time
from pathlib import Path

from worklog.config import load_config
from worklog.export_map import load_export_map


class TestConfigDefaults(unittest.TestCase):
    def test_missing_file_returns_default_config(self):
        missing = Path(tempfile.gettempdir()) / "worklog_test_missing_config.toml"
        if missing.exists():
            missing.unlink()
        cfg = load_config(missing)
        self.assertEqual(cfg.schedule.day_start, time(8, 30))
        self.assertEqual(cfg.schedule.slot_minutes, 15)
        self.assertTrue(len(cfg.buttons) > 0)

    def test_partial_file_fills_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                '[schedule]\nday_start = "09:00"\nday_end = "17:00"\n',
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.schedule.day_start, time(9, 0))
            self.assertEqual(cfg.schedule.day_end, time(17, 0))
            # tracking はファイルに無いので既定値のまま
            self.assertEqual(cfg.tracking.idle_threshold_sec, 180)

    def test_buttons_and_counts_as_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.toml"
            path.write_text(
                """
[[buttons]]
label = "休憩"
process = "休憩"
counts_as_work = false
inherit_style = false

[[buttons]]
label = "検品"
process = "検品・確認"
counts_as_work = true
inherit_style = true
""",
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.non_work_processes, {"休憩"})
            self.assertEqual(cfg.counts_as_work_processes, {"検品・確認"})


class TestExportMapDefaults(unittest.TestCase):
    def test_missing_file_returns_default(self):
        missing = Path(tempfile.gettempdir()) / "worklog_test_missing_export_map.toml"
        if missing.exists():
            missing.unlink()
        em = load_export_map(missing)
        self.assertEqual(em.format.encoding, "utf-8-sig")
        self.assertEqual([c.source for c in em.columns], ["date", "style", "process", "hours"])

    def test_invalid_source_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "export_map.toml"
            path.write_text(
                '[[columns]]\nheader = "X"\nsource = "not_a_real_source"\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_export_map(path)


if __name__ == "__main__":
    unittest.main()
