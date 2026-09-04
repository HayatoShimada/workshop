import unittest

from worklog.config import ProcessHint
from worklog.extract import extract_style, guess_process


class TestExtractStyle(unittest.TestCase):
    def setUp(self):
        self.patterns = [r"\d{2}[ASFW]{2}-[A-Z]{2}-\d{4}"]

    def test_matches_pattern(self):
        title = "25AW-BL-1234_仕様書.xlsx - Excel"
        self.assertEqual(extract_style(title, self.patterns), "25AW-BL-1234")

    def test_no_match_returns_none(self):
        self.assertIsNone(extract_style("受信トレイ - Outlook", self.patterns))

    def test_empty_title(self):
        self.assertIsNone(extract_style("", self.patterns))

    def test_no_patterns_configured(self):
        self.assertIsNone(extract_style("25AW-BL-1234 パターン - AGMS", []))


class TestGuessProcess(unittest.TestCase):
    def setUp(self):
        self.hints = [
            ProcessHint(name="パターン", match_process=["AGMS.exe", "YUKA.exe"]),
            ProcessHint(name="仕様書", match_process=["EXCEL.EXE"]),
        ]

    def test_matches_case_insensitive(self):
        self.assertEqual(guess_process("agms.exe", self.hints), "パターン")
        self.assertEqual(guess_process("EXCEL.EXE", self.hints), "仕様書")

    def test_unknown_process_returns_none(self):
        self.assertIsNone(guess_process("notepad.exe", self.hints))

    def test_empty_process_name(self):
        self.assertIsNone(guess_process("", self.hints))


if __name__ == "__main__":
    unittest.main()
