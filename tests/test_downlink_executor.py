"""#74 — ControlCommand(point_id only) -> BACnet WriteProperty executor (no grpc)."""

from __future__ import annotations

import asyncio

import pytest

from bbc_sim.bows.downlink.executor import CommandExecutor, coerce_present_value
from bbc_sim.bows.downlink.models import ControlCommand, ControlResult
from bbc_sim.bows.point_registry import PointRegistry
from bbc_sim.models import BacnetObjectSpec, BacnetObjectType


def _spec(point_id: str, object_type: BacnetObjectType, instance: int) -> BacnetObjectSpec:
    return BacnetObjectSpec(
        point_id=point_id, object_type=object_type, object_instance=instance, object_name=point_id
    )


_REGISTRY = PointRegistry(
    [
        _spec("p-av-7", BacnetObjectType.analogValue, 7),
        _spec("p-bv-3", BacnetObjectType.binaryValue, 3),
        _spec("p-mv-1", BacnetObjectType.multiStateValue, 1),
        _spec("p-ai-1", BacnetObjectType.analogInput, 1),
        _spec("p-bi-2", BacnetObjectType.binaryInput, 2),
        _spec("p-mi-3", BacnetObjectType.multiStateInput, 3),
    ]
)


def _cmd(point_id: str, value: float, priority: int | None = None) -> ControlCommand:
    return ControlCommand("c1", point_id, value, priority)


async def test_analog_write_passes_float_and_priority(fake_bacnet_app) -> None:
    app = fake_bacnet_app()
    res = await CommandExecutor(app, "10.0.0.5:47808", point_registry=_REGISTRY).execute(
        _cmd("p-av-7", 21.5, 10)
    )
    assert res == ControlResult("c1", True, "ok")
    assert app.calls == [("10.0.0.5:47808", "analogValue,7", "present-value", 21.5, 10)]


@pytest.mark.parametrize("value,expected", [(0.8, 1), (1.0, 1), (0.2, 0), (0.0, 0)])
async def test_binary_value_coerced_to_0_or_1(fake_bacnet_app, value: float, expected: int) -> None:
    app = fake_bacnet_app()
    await CommandExecutor(app, "t", point_registry=_REGISTRY).execute(_cmd("p-bv-3", value))
    assert app.calls[0][1:4] == ("binaryValue,3", "present-value", expected)


@pytest.mark.parametrize("value,expected", [(2.6, 3), (1.0, 1), (4.4, 4)])
async def test_multistate_rounded_to_int(fake_bacnet_app, value: float, expected: int) -> None:
    app = fake_bacnet_app()
    await CommandExecutor(app, "t", point_registry=_REGISTRY).execute(_cmd("p-mv-1", value))
    assert app.calls[0][3] == expected
    assert isinstance(app.calls[0][3], int)


@pytest.mark.parametrize("priority", [0, 17, -1, None])
async def test_out_of_range_priority_is_dropped(fake_bacnet_app, priority: int | None) -> None:
    app = fake_bacnet_app()
    await CommandExecutor(app, "t", point_registry=_REGISTRY).execute(_cmd("p-av-7", 1.0, priority))
    assert app.calls[0][4] is None


@pytest.mark.parametrize("priority", [1, 8, 16])
async def test_valid_priority_passed_through(fake_bacnet_app, priority: int) -> None:
    app = fake_bacnet_app()
    await CommandExecutor(app, "t", point_registry=_REGISTRY).execute(_cmd("p-av-7", 1.0, priority))
    assert app.calls[0][4] == priority


async def test_unknown_point_id_fails_without_write(fake_bacnet_app) -> None:
    app = fake_bacnet_app()
    res = await CommandExecutor(app, "t", point_registry=_REGISTRY).execute(
        _cmd("unknown-point", 1.0)
    )
    assert res.success is False
    assert "unknown point_id" in res.response and "unknown-point" in res.response
    assert app.calls == []


@pytest.mark.parametrize(
    "point_id,name",
    [("p-ai-1", "analogInput"), ("p-bi-2", "binaryInput"), ("p-mi-3", "multiStateInput")],
)
async def test_input_objects_rejected_without_write(fake_bacnet_app, point_id, name) -> None:
    app = fake_bacnet_app()
    res = await CommandExecutor(app, "t", point_registry=_REGISTRY).execute(_cmd(point_id, 1.0))
    assert res.success is False
    assert "read-only" in res.response and name in res.response
    assert app.calls == []


async def test_cancellation_is_not_swallowed(fake_bacnet_app) -> None:
    app = fake_bacnet_app(fail=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        await CommandExecutor(app, "t", point_registry=_REGISTRY).execute(_cmd("p-av-7", 1.0))


async def test_write_failure_is_reported_not_raised(fake_bacnet_app) -> None:
    app = fake_bacnet_app(fail=RuntimeError("writeAccessDenied"))
    res = await CommandExecutor(app, "t", point_registry=_REGISTRY).execute(_cmd("p-av-7", 1.0))
    assert res.success is False
    assert "RuntimeError" in res.response and "writeAccessDenied" in res.response


def test_coerce_present_value_by_type() -> None:
    assert coerce_present_value(BacnetObjectType.analogValue, 3) == 3.0
    assert coerce_present_value(BacnetObjectType.binaryOutput, 0.9) == 1
    assert coerce_present_value(BacnetObjectType.multiStateValue, 2.5) == 2
