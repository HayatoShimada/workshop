"""ロガー設定。

tkinter は例外が黙って消えることがあるため、未捕捉例外は必ず
logs/{name}.log に書く（DESIGN.md 13章の注意事項）。
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .paths import logs_dir

_configured: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    """logs/{name}.log に書き込むロガーを返す。

    同じ name で複数回呼んでもハンドラは1回だけ付ける。
    また、このロガーに対する未捕捉例外を拾うよう sys.excepthook を
    差し替える（tkinter のメインループ内はこれだけでは拾えないため、
    呼び出し側で個別に try/except することが必須）。
    """
    logger = logging.getLogger(name)

    if name not in _configured:
        logger.setLevel(logging.INFO)
        log_path = logs_dir() / f"{name}.log"
        handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
        logger.propagate = False
        _configured.add(name)

        def _excepthook(exc_type, exc_value, exc_tb, _logger=logger):
            _logger.error("未捕捉の例外", exc_info=(exc_type, exc_value, exc_tb))
            sys.__excepthook__(exc_type, exc_value, exc_tb)

        sys.excepthook = _excepthook

    return logger
