"""worklog のコマンドラインエントリポイント（DESIGN.md 7章）。"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date

from .commit import commit_day
from .config import load_config
from .export import export_month
from .export_map import load_export_map
from .paths import committed_dir, processes_hint_path, raw_dir, timeline_csv_path
from .timeline import generate_timeline, write_timeline_csv


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _cmd_watch(args: argparse.Namespace) -> int:
    from .watcher import main as watch_main

    return watch_main()


def _cmd_punch(args: argparse.Namespace) -> int:
    from .ui.punch_window import main as punch_main

    return punch_main()


def _write_processes_hint(config) -> None:
    lines = ["# worklog day で生成されたタイムラインの工程入力候補です。"]
    lines.extend(config.choices.processes)
    processes_hint_path().write_text("\n".join(lines), encoding="utf-8-sig")


def _cmd_day(args: argparse.Namespace) -> int:
    target = args.date or date.today()
    config = load_config()

    out_path = timeline_csv_path(target.isoformat())
    if out_path.exists() and not args.force:
        answer = input(
            f"{out_path} は既に存在します。上書きすると編集内容が消えます。上書きしますか？ [y/N] "
        )
        if answer.strip().lower() != "y":
            print("中止しました。")
            return 1

    rows = generate_timeline(target, config)
    write_timeline_csv(out_path, rows)
    _write_processes_hint(config)

    unresolved = sum(1 for r in rows if r.state == "未記録")
    print(f"タイムラインを出力しました: {out_path}")
    print(f"未記録のスロット: {unresolved} 件（ここだけ入力してください）")

    if not args.no_open:
        try:
            os.startfile(out_path)  # type: ignore[attr-defined]
        except OSError as e:
            print(f"（自動で開けませんでした: {e}。手動でExcelから開いてください）")

    return 0


def _cmd_commit(args: argparse.Namespace) -> int:
    target = args.date or date.today()
    config = load_config()

    try:
        result = commit_day(target, config)
    except FileNotFoundError as e:
        print(str(e))
        return 1

    print(f"{target.isoformat()} を確定しました。")
    if result.unresolved_rows:
        print(f"注意: 未記録のまま残っている時刻があります: {', '.join(result.unresolved_rows)}")
    if result.unknown_processes:
        print(f"注意: config.toml の choices.processes に無い工程があります: {', '.join(result.unknown_processes)}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    config = load_config()
    export_map = load_export_map()
    out_path = export_month(args.month, config, export_map)
    print(f"転記用CSVを出力しました: {out_path}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    raw_dates = sorted(
        {p.name.split("_")[0] for p in raw_dir().glob("*_window.csv")}
        | {p.name.split("_")[0] for p in raw_dir().glob("*_punch.csv")}
    )
    committed_dates = {p.name.split("_timeline.csv")[0] for p in committed_dir().glob("*_timeline.csv")}

    pending = [d for d in raw_dates if d not in committed_dates]
    if not pending:
        print("未確定の日はありません。")
        return 0

    print("未確定の日:")
    for d in pending:
        print(f"  {d}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worklog", description="パタンナーの設計工数記録ツール")
    sub = parser.add_subparsers(dest="command", required=True)

    p_watch = sub.add_parser("watch", help="PC操作の記録を開始する")
    p_watch.set_defaults(func=_cmd_watch)

    p_punch = sub.add_parser("punch", help="打刻ウィンドウを表示する")
    p_punch.set_defaults(func=_cmd_punch)

    p_day = sub.add_parser("day", help="今日のタイムラインCSVを出力してExcelで開く")
    p_day.add_argument("--date", type=_parse_date, default=None, help="対象日 (YYYY-MM-DD)。省略時は今日")
    p_day.add_argument("--no-open", action="store_true", help="Excelで自動的に開かない")
    p_day.add_argument("--force", action="store_true", help="既存のタイムラインを確認なしで上書きする")
    p_day.set_defaults(func=_cmd_day)

    p_commit = sub.add_parser("commit", help="編集済みタイムラインを取り込んで確定する")
    p_commit.add_argument("--date", type=_parse_date, default=None, help="対象日 (YYYY-MM-DD)。省略時は今日")
    p_commit.set_defaults(func=_cmd_commit)

    p_export = sub.add_parser("export", help="転記用CSVを出力する")
    p_export.add_argument("--month", required=True, help="対象月 (YYYY-MM)")
    p_export.set_defaults(func=_cmd_export)

    p_status = sub.add_parser("status", help="未確定の日を一覧表示する")
    p_status.set_defaults(func=_cmd_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
