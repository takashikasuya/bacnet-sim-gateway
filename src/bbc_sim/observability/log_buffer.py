"""Ring-buffer log handler for the admin UI (EP-007.1, PR-F-053).

emit() appends a LogEntry to a bounded deque — no I/O, no locks beyond CPython's
deque-append atomicity.  Formatting is deferred to snapshot() so the hot path stays
a bare struct fill (ADR-010: must not block the asyncio loop).
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class LogEntry:
    ts: float    # time.time() at record creation
    level: str   # LEVELNAME string
    logger: str  # record.name
    message: str # formatted message (no exc_info)


class RingBufferLogHandler(logging.Handler):
    def __init__(self, capacity: int = 1000) -> None:
        super().__init__()
        self.records: deque[LogEntry] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:  # noqa: BLE001
            msg = record.getMessage()
        self.records.append(
            LogEntry(ts=record.created, level=record.levelname,
                     logger=record.name, message=msg)
        )

    def snapshot(
        self,
        level: str | None = None,
        since: float | None = None,
        limit: int | None = None,
    ) -> list[LogEntry]:
        """Return filtered, time-ordered entries (newest-last)."""
        entries: list[LogEntry] = []
        for e in self.records:
            if level and e.level != level.upper():
                continue
            if since is not None and e.ts <= since:
                continue
            entries.append(e)
        return entries[-limit:] if limit is not None else entries
