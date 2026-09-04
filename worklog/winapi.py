"""Windows API を ctypes で直叩きする薄いラッパ。

pywin32 に依存しないための最小限の関数群。ここだけが Windows に
依存するコードで、watcher からのみ使う（打刻ウィンドウは触らない、
DESIGN.md 13章）。
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def get_foreground_window_title() -> str:
    """前面ウィンドウのタイトルを返す。取得できなければ空文字。"""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_foreground_process_name() -> str:
    """前面ウィンドウを持つプロセスの実行ファイル名（例: EXCEL.EXE）を返す。"""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        buf_len = wintypes.DWORD(260)
        buf = ctypes.create_unicode_buffer(buf_len.value)
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(buf_len))
        if not ok:
            return ""
        path = buf.value
        return path.rsplit("\\", 1)[-1] if path else ""
    finally:
        kernel32.CloseHandle(handle)


def get_idle_seconds() -> float:
    """最後のキーボード/マウス操作からの経過秒数。"""
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    tick_count = kernel32.GetTickCount()
    elapsed_ms = tick_count - info.dwTime
    if elapsed_ms < 0:
        # GetTickCount は約49.7日で折り返す。折り返し直後は0扱いにする。
        return 0.0
    return elapsed_ms / 1000.0
