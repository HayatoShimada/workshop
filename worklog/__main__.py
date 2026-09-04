"""python -m worklog <command> のエントリポイント。

PyInstallerで --windowed（コンソール無し）でビルドした worklogw.exe から
watch / punch を起動する場合、sys.stdout / sys.stderr が None になる。
argparse などが標準出力・エラー出力に書き込もうとして例外にならないよう、
その場合は os.devnull へ差し替えておく（watch/punch自体はログファイルに
書くので、標準出力は使わない）。
"""

import os
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from .cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
