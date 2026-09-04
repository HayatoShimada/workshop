"""ファイルパスの基準解決。

配布時は exe と同じフォルダを基準にし、開発時はリポジトリのルート
（このファイルの2つ上）を基準にする。data/ と logs/ は必要になった
時点で自動的に作成する。
"""

from __future__ import annotations

import sys
from pathlib import Path


def base_dir() -> Path:
    """設定ファイル・data・logs を置く基準ディレクトリ。"""
    if getattr(sys, "frozen", False):
        # PyInstaller で固めた exe。exe と同じフォルダを基準にする。
        return Path(sys.executable).resolve().parent
    # 開発時: worklog/paths.py の2つ上（リポジトリルート）。
    return Path(__file__).resolve().parent.parent


def _ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    return _ensure(base_dir() / "data")


def raw_dir() -> Path:
    return _ensure(data_dir() / "raw")


def daily_dir() -> Path:
    return _ensure(data_dir() / "daily")


def committed_dir() -> Path:
    return _ensure(data_dir() / "committed")


def export_dir() -> Path:
    return _ensure(data_dir() / "export")


def logs_dir() -> Path:
    return _ensure(base_dir() / "logs")


def state_path() -> Path:
    return data_dir() / "state.json"


def punch_active_path() -> Path:
    """進行中の打刻（GUIが落ちても復旧できるように）。"""
    return data_dir() / "punch_active.json"


def ui_state_path() -> Path:
    """打刻ウィンドウの位置・サイズの記憶。"""
    return data_dir() / "ui_state.json"


def config_path() -> Path:
    return base_dir() / "config.toml"


def export_map_path() -> Path:
    return base_dir() / "export_map.toml"


def window_csv_path(date_str: str) -> Path:
    return raw_dir() / f"{date_str}_window.csv"


def punch_csv_path(date_str: str) -> Path:
    return raw_dir() / f"{date_str}_punch.csv"


def timeline_csv_path(date_str: str) -> Path:
    return daily_dir() / f"{date_str}_timeline.csv"


def committed_csv_path(date_str: str) -> Path:
    return committed_dir() / f"{date_str}_timeline.csv"


def processes_hint_path() -> Path:
    return daily_dir() / "_processes.txt"


def export_csv_path(month_str: str) -> Path:
    return export_dir() / f"{month_str}_worklog.csv"
