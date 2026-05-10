"""Central logging configuration — standard library only."""

from __future__ import annotations

import logging
import time


class _UtcFormatter(logging.Formatter):
    converter = time.gmtime


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging once: timestamp, level, logger name, message (UTC)."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        _UtcFormatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
