"""Ring-buffer log handler for the admin UI (EP-007.1, PR-F-053).

emit() stores the record's plain message via record.getMessage() and appends a
LogEntry to a bounded deque — no formatter, no exception formatting, no I/O on the
hot path (ADR-010: must not block the asyncio loop).  snapshot() (the cold read
path) copies the deque under the handler lock before filtering so a concurrent emit
cannot raise "deque mutated during iteration".
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class LogEntry:
    ts: float  # time.time() at record creation
    level: str  # LEVELNAME string
    logger: str  # record.name
    message: str  # plain message (no formatter, no exc_info)


class RingBufferLogHandler(logging.Handler):
    def __init__(self, capacity: int = 1000) -> None:
        super().__init__()
        self.records: deque[LogEntry] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001 - never let a bad record kill the loop
            msg = str(record.msg)
        self.records.append(
            LogEntry(ts=record.created, level=record.levelname, logger=record.name, message=msg)
        )

    def snapshot(
        self,
        level: str | None = None,
        since: float | None = None,
        limit: int | None = None,
    ) -> list[LogEntry]:
        """Return filtered, time-ordered entries (newest-last).

        Copies the deque under the handler lock first so a concurrent emit() cannot
        mutate it mid-iteration.
        """
        with self.lock:  # type: ignore[union-attr]  # Handler.lock is set in __init__
            items = list(self.records)
        entries: list[LogEntry] = []
        for e in items:
            if level and e.level != level.upper():
                continue
            if since is not None and e.ts <= since:
                continue
            entries.append(e)
        return entries[-limit:] if limit is not None else entries
