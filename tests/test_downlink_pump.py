"""EP-008.11 (#70) — CommandPump drives command -> result in order (no grpc)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from bbc_sim.bows.downlink.executor import CommandExecutor
from bbc_sim.bows.downlink.models import ControlCommand
from bbc_sim.bows.downlink.pump import CommandPump
from bbc_sim.bows.point_registry import PointRegistry
from bbc_sim.models import BacnetObjectSpec, BacnetObjectType


def _spec(point_id: str, object_type: BacnetObjectType, instance: int) -> BacnetObjectSpec:
    return BacnetObjectSpec(
        point_id=point_id, object_type=object_type, object_instance=instance, object_name=point_id
    )


_REGISTRY = PointRegistry([_spec(f"p{i}", BacnetObjectType.analogValue, i) for i in range(3)])


async def _stream(cmds: list[ControlCommand]) -> AsyncIterator[ControlCommand]:
    for cmd in cmds:
        yield cmd


async def test_pump_executes_each_command_in_order(fake_bacnet_app) -> None:
    app = fake_bacnet_app()
    pump = CommandPump(CommandExecutor(app, "t", point_registry=_REGISTRY))
    cmds = [ControlCommand(f"c{i}", f"p{i}", float(i)) for i in range(3)]

    results = [r async for r in pump.pump(_stream(cmds))]

    assert [r.control_id for r in results] == ["c0", "c1", "c2"]
    assert all(r.success for r in results)
    assert [call[1] for call in app.calls] == ["analogValue,0", "analogValue,1", "analogValue,2"]


async def test_pump_reports_failures_without_stopping(fake_bacnet_app) -> None:
    app = fake_bacnet_app(fail=RuntimeError("boom"))
    pump = CommandPump(CommandExecutor(app, "t", point_registry=_REGISTRY))
    cmds = [ControlCommand("a", "p0", 1.0), ControlCommand("b", "p1", 2.0)]

    results = [r async for r in pump.pump(_stream(cmds))]

    assert [r.control_id for r in results] == ["a", "b"]
    assert all(not r.success for r in results)  # both reported, stream not torn down
