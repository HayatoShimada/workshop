"""worklog のコマンドラインエントリポイント（DESIGN.md 7章）。"""

from __future__ import annotations

import argparse
import sys


def _cmd_watch(args: argparse.Namespace) -> int:
    from .watcher import main as watch_main
    return watch_main()


def _cmd_punch(args: argparse.Namespace) -> int:
    from .ui.punch_window import main as punch_main
    return punch_main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worklog", description="パタンナーの設計工数記録ツール")
    sub = parser.add_subparsers(dest="command", required=True)

    p_watch = sub.add_parser("watch", help="PC操作の記録を開始する")
    p_watch.set_defaults(func=_cmd_watch)

    p_punch = sub.add_parser("punch", help="打刻ウィンドウを表示する")
    p_punch.set_defaults(func=_cmd_punch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
