"""EP-008.10 (#69) — ControlCommand -> BACnet WriteProperty executor (no grpc)."""

from __future__ import annotations

import pytest

from bbc_sim.bows.downlink.executor import CommandExecutor, coerce_present_value
from bbc_sim.bows.downlink.models import ControlCommand, ControlResult
from bbc_sim.models import BacnetObjectType

# ASHRAE object-type enums used below: 2=analogValue, 5=binaryValue, 19=multiStateValue.


def _cmd(
    object_type: int, instance: int, value: float, priority: int | None = None
) -> ControlCommand:
    return ControlCommand("c1", "p1", 1001, object_type, instance, value, priority)


async def test_analog_write_passes_float_and_priority(fake_bacnet_app) -> None:
    app = fake_bacnet_app()
    res = await CommandExecutor(app, "10.0.0.5:47808").execute(_cmd(2, 7, 21.5, 10))
    assert res == ControlResult("c1", True, "ok")
    assert app.calls == [("10.0.0.5:47808", "analogValue,7", "present-value", 21.5, 10)]


@pytest.mark.parametrize("value,expected", [(0.8, 1), (1.0, 1), (0.2, 0), (0.0, 0)])
async def test_binary_value_coerced_to_0_or_1(fake_bacnet_app, value: float, expected: int) -> None:
    app = fake_bacnet_app()
    await CommandExecutor(app, "t").execute(_cmd(5, 3, value))
    assert app.calls[0][1:4] == ("binaryValue,3", "present-value", expected)


@pytest.mark.parametrize("value,expected", [(2.6, 3), (1.0, 1), (4.4, 4)])
async def test_multistate_rounded_to_int(fake_bacnet_app, value: float, expected: int) -> None:
    app = fake_bacnet_app()
    await CommandExecutor(app, "t").execute(_cmd(19, 1, value))
    assert app.calls[0][3] == expected
    assert isinstance(app.calls[0][3], int)


@pytest.mark.parametrize("priority", [0, 17, -1, None])
async def test_out_of_range_priority_is_dropped(fake_bacnet_app, priority: int | None) -> None:
    app = fake_bacnet_app()
    await CommandExecutor(app, "t").execute(_cmd(2, 1, 1.0, priority))
    assert app.calls[0][4] is None


@pytest.mark.parametrize("priority", [1, 8, 16])
async def test_valid_priority_passed_through(fake_bacnet_app, priority: int) -> None:
    app = fake_bacnet_app()
    await CommandExecutor(app, "t").execute(_cmd(2, 1, 1.0, priority))
    assert app.calls[0][4] == priority


async def test_unknown_object_type_fails_without_write(fake_bacnet_app) -> None:
    app = fake_bacnet_app()
    res = await CommandExecutor(app, "t").execute(_cmd(99, 1, 1.0))
    assert res.success is False
    assert "unknown object_type 99" in res.response
    assert app.calls == []  # never attempted a write


async def test_write_failure_is_reported_not_raised(fake_bacnet_app) -> None:
    app = fake_bacnet_app(fail=RuntimeError("writeAccessDenied"))
    res = await CommandExecutor(app, "t").execute(_cmd(2, 1, 1.0))
    assert res.success is False
    assert "RuntimeError" in res.response and "writeAccessDenied" in res.response


def test_coerce_present_value_by_type() -> None:
    assert coerce_present_value(BacnetObjectType.analogValue, 3) == 3.0
    assert coerce_present_value(BacnetObjectType.binaryOutput, 0.9) == 1
    assert coerce_present_value(BacnetObjectType.multiStateValue, 2.5) == 2
