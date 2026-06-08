"""Drive command -> result (gRPC-free, ADR-017).

Consumes an async stream of ControlCommands, executes each, and yields the
ControlResults in order. Kept independent of gRPC so the bidi loop's business logic is
unit-testable; the wire client adapts proto messages to/from these streams.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from bbc_sim.bows.downlink.executor import CommandExecutor
from bbc_sim.bows.downlink.models import ControlCommand, ControlResult


class CommandPump:
    """Sequentially execute inbound commands (single-loop, ADR-010)."""

    def __init__(self, executor: CommandExecutor) -> None:
        self._executor = executor

    async def pump(self, commands: AsyncIterator[ControlCommand]) -> AsyncIterator[ControlResult]:
        async for cmd in commands:
            yield await self._executor.execute(cmd)
