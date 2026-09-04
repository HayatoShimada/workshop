"""worklog punch — 離席打刻ウィンドウ（DESIGN.md 6章）。

重要な制約:
- Windows API には一切触れない。state.json を読むだけ（純粋な tkinter）
- state.json が無い・壊れている場合も「品番なし・操作状態不明」として動き続ける
- すべてのコールバックは例外を握りつぶさず logs/punch.log に書く
"""

from __future__ import annotations

import json
import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from ..config import Button, Config, load_config
from ..logs import get_logger
from ..paths import punch_active_path, punch_csv_path, ui_state_path
from ..records import PunchRecord, append_punch_record
from ..state import read_state
from .ask_dialog import build_ask_panel

logger = get_logger("punch")

_PALETTE = ["#e0e0e0", "#bbdefb", "#c8e6c9", "#ffe0b2", "#f8bbd0", "#d1c4e9"]

POLL_MS = 1000


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _clear_json(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        logger.exception("一時ファイルの削除に失敗しました: %s", path)


class ActivePunch:
    """進行中の打刻。GUIが落ちても punch_active.json から復旧できる。"""

    def __init__(self, button: Button, style: str, start: datetime, armed: bool = False):
        self.button = button
        self.style = style
        self.start = start
        self.armed = armed  # True になった後の active復帰でだけ自動終了する

    def to_json(self) -> dict:
        return {
            "label": self.button.label,
            "process": self.button.process,
            "counts_as_work": self.button.counts_as_work,
            "inherit_style": self.button.inherit_style,
            "style": self.style,
            "start": self.start.isoformat(timespec="seconds"),
            "armed": self.armed,
        }

    @classmethod
    def from_json(cls, data: dict, buttons: list[Button]) -> "ActivePunch | None":
        label = data.get("label")
        matched = next((b for b in buttons if b.label == label), None)
        if matched is None:
            matched = Button(
                label=label or "",
                process=data.get("process", label or ""),
                counts_as_work=data.get("counts_as_work", True),
                inherit_style=data.get("inherit_style", True),
            )
        start = _parse_iso(data.get("start", ""))
        if start is None:
            return None
        # クラッシュ後の復旧なので、次にPC操作が確認され次第すぐ自動終了してよい
        return cls(button=matched, style=data.get("style", ""), start=start, armed=True)


class PunchWindow(tk.Tk):
    def __init__(self, config: Config):
        super().__init__()
        self.config_ = config
        self.title("worklog punch")
        self.resizable(True, True)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._safe(self._on_close))

        self._active: ActivePunch | None = None
        self._pending_away_start: str | None = None
        self._last_seen_active: bool | None = None
        self._current_style: str | None = None
        self._recent_styles: list[str] = []
        self._buttons: dict[str, tk.Button] = {}
        self._ask_frame: tk.Frame | None = None
        self._pending_geometry: tuple[int, int, int, int] | None = None
        self._geometry_save_scheduled = False

        self._build_ui()
        self._restore_geometry()
        self._restore_active_punch()
        self.bind("<Configure>", self._safe(self._on_configure))

        self.after(100, self._safe(self._poll))

    # ---- UI 構築 -----------------------------------------------------

    def _build_ui(self) -> None:
        top = tk.Frame(self, padx=6, pady=4)
        top.pack(fill="x")

        self._style_var = tk.StringVar(value="(品番なし)")
        tk.Label(top, text="品番:").pack(side="left")
        self._style_combo = ttk.Combobox(top, textvariable=self._style_var, width=20, values=[])
        self._style_combo.pack(side="left", padx=(4, 0), fill="x", expand=True)
        self._style_combo.bind("<<ComboboxSelected>>", self._safe(self._on_style_selected))

        self._normal_frame = tk.Frame(self, padx=6, pady=4)
        self._normal_frame.pack(fill="both", expand=True)

        self._elapsed_var = tk.StringVar(value="")
        tk.Label(self._normal_frame, textvariable=self._elapsed_var, font=("Yu Gothic UI", 9)).pack(
            anchor="w"
        )

        self._btn_row = tk.Frame(self._normal_frame)
        self._btn_row.pack(fill="both", expand=True)
        for i, button_cfg in enumerate(self.config_.buttons):
            color = button_cfg.color or _PALETTE[i % len(_PALETTE)]
            b = tk.Button(
                self._btn_row,
                text=button_cfg.label,
                bg=color,
                activebackground=color,
                command=self._safe(lambda bc=button_cfg: self._on_button_click(bc)),
            )
            b.pack(side="left", fill="both", expand=True, padx=2, pady=2)
            self._buttons[button_cfg.label] = b

        self._status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self._status_var, fg="#666666", font=("Yu Gothic UI", 8)).pack(
            anchor="w", padx=6, pady=(0, 4)
        )

    # ---- 安全にコールバックを実行する共通ラッパ -----------------------

    def _safe(self, fn):
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                logger.exception("コールバック処理中に例外が発生しました: %s", getattr(fn, "__name__", fn))
                return None

        return wrapper

    # ---- 位置・サイズの記憶 -------------------------------------------

    def _restore_geometry(self) -> None:
        data = _read_json(ui_state_path())
        if data and all(k in data for k in ("x", "y", "width", "height")):
            self.geometry(f"{data['width']}x{data['height']}+{data['x']}+{data['y']}")
            return
        # 既定: 画面右下
        self.update_idletasks()
        width, height = 460, 110
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = sw - width - 20
        y = sh - height - 60
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _on_configure(self, event) -> None:
        if event.widget is not self:
            return
        # 短時間に何度も飛んでくるので直近の値だけ保持し、あとでまとめて書く
        self._pending_geometry = (self.winfo_x(), self.winfo_y(), self.winfo_width(), self.winfo_height())
        if not self._geometry_save_scheduled:
            self._geometry_save_scheduled = True
            self.after(500, self._safe(self._flush_geometry))

    def _flush_geometry(self) -> None:
        self._geometry_save_scheduled = False
        if self._pending_geometry is None:
            return
        x, y, w, h = self._pending_geometry
        _write_json(ui_state_path(), {"x": x, "y": y, "width": w, "height": h})

    # ---- 打刻中の状態の復旧 --------------------------------------------

    def _restore_active_punch(self) -> None:
        data = _read_json(punch_active_path())
        if not data:
            return
        active = ActivePunch.from_json(data, self.config_.buttons)
        if active is None:
            return
        self._active = active
        self._enter_active_visual(active.button)
        self._status_var.set("前回終了時の打刻を復元しました")
        logger.info("進行中の打刻を復元しました: %s", active.button.label)

    # ---- state.json のポーリング ---------------------------------------

    def _poll(self) -> None:
        state = read_state()
        if state is None:
            self._status_var.set("state.json が読めません（watcher未起動？）品番なしで動作中")
            active_now = None
            current_style = None
            recent_styles: list[str] = []
        else:
            self._status_var.set("")
            active_now = state.active
            current_style = state.current_style
            recent_styles = state.recent_styles

        self._update_style_choices(current_style, recent_styles)
        self._handle_activity_transition(active_now)
        self._update_elapsed_label()

        self.after(POLL_MS, self._safe(self._poll))

    def _update_style_choices(self, current_style: str | None, recent_styles: list[str]) -> None:
        self._current_style = current_style
        self._recent_styles = recent_styles
        values = list(recent_styles)
        self._style_combo["values"] = values
        # 打刻中は品番を編集させない（開始時に確定した品番を優先する）
        if self._active is None:
            display = current_style or (values[0] if values else "(品番なし)")
            if self._style_var.get() != display:
                self._style_var.set(display)

    def _on_style_selected(self, event) -> None:
        pass  # StringVar が既に更新されているので追加処理は不要

    def _handle_activity_transition(self, active_now: bool | None) -> None:
        prev = self._last_seen_active
        self._last_seen_active = active_now

        if active_now is None:
            return

        # 非アクティブへ変化した
        if prev is not False and active_now is False:
            if self._active is None and self._pending_away_start is None:
                state = read_state()
                anchor = (state.last_active_at if state else "") or _now_iso()
                self._pending_away_start = anchor

        # アクティブへ変化した（離席からの復帰）
        if prev is False and active_now is True:
            if self._active is not None and self._active.armed:
                self._end_active_punch(ended_by="pc_resume")
            elif self._active is None and self._pending_away_start is not None:
                self._maybe_ask_forgotten(self._pending_away_start)

            self._pending_away_start = None

        # 打刻中に一度でも非アクティブを観測したら、以後の復帰で自動終了してよい
        if self._active is not None and active_now is False:
            self._active.armed = True
            self._persist_active()

    def _maybe_ask_forgotten(self, away_start_iso: str) -> None:
        away_start = _parse_iso(away_start_iso)
        if away_start is None:
            return
        away_end = datetime.now()
        duration = (away_end - away_start).total_seconds()
        if duration <= self.config_.tracking.ask_after_sec:
            return
        self._show_ask_panel(away_start, away_end)

    # ---- 打刻ボタン ------------------------------------------------------

    def _on_button_click(self, button_cfg: Button) -> None:
        if self._active is not None:
            if self._active.button.label == button_cfg.label:
                self._end_active_punch(ended_by="button")
            # 打刻中は他のボタンは無効化されているため通常ここには来ない
            return

        if button_cfg.inherit_style:
            style = self._current_style or self._style_var.get()
            if style == "(品番なし)":
                style = ""
        else:
            style = ""

        active = ActivePunch(button=button_cfg, style=style, start=datetime.now(), armed=False)
        self._active = active
        self._pending_away_start = None
        self._persist_active()
        self._enter_active_visual(button_cfg)
        logger.info("打刻開始: %s (品番=%s)", button_cfg.label, style)

    def _enter_active_visual(self, button_cfg: Button) -> None:
        for label, widget in self._buttons.items():
            if label == button_cfg.label:
                widget.config(relief="sunken")
            else:
                widget.config(state="disabled")
        self._style_combo.config(state="disabled")

    def _leave_active_visual(self) -> None:
        for widget in self._buttons.values():
            widget.config(relief="raised", state="normal")
        self._style_combo.config(state="normal")
        self._elapsed_var.set("")

    def _update_elapsed_label(self) -> None:
        if self._active is None:
            return
        elapsed = int((datetime.now() - self._active.start).total_seconds())
        elapsed = max(0, elapsed)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        label = f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        self._elapsed_var.set(f"{self._active.button.label} 打刻中… 経過 {label}")

    def _end_active_punch(self, ended_by: str) -> None:
        active = self._active
        if active is None:
            return
        record = PunchRecord(
            start=active.start.isoformat(timespec="seconds"),
            end=_now_iso(),
            label=active.button.label,
            process=active.button.process,
            style=active.style,
            ended_by=ended_by,
        )
        try:
            append_punch_record(punch_csv_path(datetime.now().strftime("%Y-%m-%d")), record)
        except OSError:
            logger.exception("punch.csv への書き込みに失敗しました")
        logger.info("打刻終了: %s (ended_by=%s)", active.button.label, ended_by)

        self._active = None
        _clear_json(punch_active_path())
        self._leave_active_visual()

    def _persist_active(self) -> None:
        if self._active is None:
            return
        try:
            _write_json(punch_active_path(), self._active.to_json())
        except OSError:
            logger.exception("punch_active.json への書き込みに失敗しました")

    # ---- 押し忘れ問いかけ --------------------------------------------------

    def _show_ask_panel(self, away_start: datetime, away_end: datetime) -> None:
        if self._ask_frame is not None:
            return
        self._normal_frame.pack_forget()
        self._ask_frame = build_ask_panel(
            self,
            away_start,
            away_end,
            self.config_.buttons,
            on_choose=self._safe(lambda bc: self._on_ask_choice(bc, away_start, away_end)),
            on_later=self._safe(self._on_ask_later),
        )
        self._ask_frame.pack(fill="both", expand=True)
        logger.info("押し忘れの問いかけを表示: %s 〜 %s", away_start, away_end)

    def _hide_ask_panel(self) -> None:
        if self._ask_frame is not None:
            self._ask_frame.destroy()
            self._ask_frame = None
        self._normal_frame.pack(fill="both", expand=True)

    def _on_ask_choice(self, button_cfg: Button, away_start: datetime, away_end: datetime) -> None:
        style = (self._current_style or "") if button_cfg.inherit_style else ""
        record = PunchRecord(
            start=away_start.isoformat(timespec="seconds"),
            end=away_end.isoformat(timespec="seconds"),
            label=button_cfg.label,
            process=button_cfg.process,
            style=style,
            ended_by="late_input",
        )
        try:
            append_punch_record(punch_csv_path(away_start.strftime("%Y-%m-%d")), record)
        except OSError:
            logger.exception("punch.csv (late_input) への書き込みに失敗しました")
        logger.info("押し忘れの後追い入力: %s", button_cfg.label)
        self._hide_ask_panel()

    def _on_ask_later(self) -> None:
        logger.info("押し忘れの問いかけを見送り（日次確定に回す）")
        self._hide_ask_panel()

    # ---- 終了 -------------------------------------------------------------

    def _on_close(self) -> None:
        self._flush_geometry()
        self.destroy()


def main() -> int:
    def _report_callback_exception(exc_type, exc_value, exc_tb):
        logger.error("tkinter コールバック例外", exc_info=(exc_type, exc_value, exc_tb))

    try:
        config = load_config()
        app = PunchWindow(config)
        app.report_callback_exception = _report_callback_exception
        app.mainloop()
    except Exception:
        logger.exception("打刻ウィンドウの起動に失敗しました")
        return 1
    return 0
