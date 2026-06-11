"""EP-008.11 (#70) — CommandPump drives command -> result in order (no grpc)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from bbc_sim.bows.downlink.executor import CommandExecutor
from bbc_sim.bows.downlink.models import ControlCommand
from bbc_sim.bows.downlink.pump import CommandPump


async def _stream(cmds: list[ControlCommand]) -> AsyncIterator[ControlCommand]:
    for cmd in cmds:
        yield cmd


async def test_pump_executes_each_command_in_order(fake_bacnet_app) -> None:
    app = fake_bacnet_app()
    pump = CommandPump(CommandExecutor(app, "t"))
    cmds = [ControlCommand(f"c{i}", "p", 1001, 2, i, float(i)) for i in range(3)]

    results = [r async for r in pump.pump(_stream(cmds))]

    assert [r.control_id for r in results] == ["c0", "c1", "c2"]
    assert all(r.success for r in results)
    assert [call[1] for call in app.calls] == ["analogValue,0", "analogValue,1", "analogValue,2"]


async def test_pump_reports_failures_without_stopping(fake_bacnet_app) -> None:
    app = fake_bacnet_app(fail=RuntimeError("boom"))
    pump = CommandPump(CommandExecutor(app, "t"))
    cmds = [ControlCommand("a", "p", 1, 2, 1, 1.0), ControlCommand("b", "p", 1, 2, 2, 2.0)]

    results = [r async for r in pump.pump(_stream(cmds))]

    assert [r.control_id for r in results] == ["a", "b"]
    assert all(not r.success for r in results)  # both reported, stream not torn down
