"""#73 — gRPC ingress encoder: Reading + PointRegistry -> TelemetryFrame."""

from __future__ import annotations

from datetime import UTC, datetime

from bbc_sim.bows.models import Reading
from bbc_sim.bows.point_registry import PointRegistry
from bbc_sim.bows.uplink.encoder import encode_telemetry_frames
from bbc_sim.models import BacnetObjectSpec, BacnetObjectType


def _spec(point_id: str, object_type: BacnetObjectType, instance: int) -> BacnetObjectSpec:
    return BacnetObjectSpec(
        point_id=point_id, object_type=object_type, object_instance=instance, object_name=point_id
    )


_REGISTRY = PointRegistry(
    [
        _spec("pt-ai-1", BacnetObjectType.analogInput, 1),
        _spec("pt-bv-3", BacnetObjectType.binaryValue, 3),
        _spec("pt-mv-5", BacnetObjectType.multiStateValue, 5),
    ]
)
_TS = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)


def test_analog_reading_encodes_to_frame() -> None:
    readings = [Reading(BacnetObjectType.analogInput, 1, 23.5, _TS)]
    frames = encode_telemetry_frames("gw-001", readings, _REGISTRY, now=_TS)
    assert len(frames) == 1
    assert frames[0]["gateway_id"] == "gw-001"
    assert frames[0]["point_id"] == "pt-ai-1"
    assert frames[0]["value"] == 23.5
    assert frames[0]["timestamp"] == "2025-01-01T12:00:00+00:00"


def test_binary_active_is_encoded_as_1() -> None:
    readings = [Reading(BacnetObjectType.binaryValue, 3, "active")]
    frames = encode_telemetry_frames("gw-1", readings, _REGISTRY, now=_TS)
    assert frames[0]["value"] == 1


def test_binary_inactive_is_encoded_as_0() -> None:
    readings = [Reading(BacnetObjectType.binaryValue, 3, "inactive")]
    frames = encode_telemetry_frames("gw-1", readings, _REGISTRY, now=_TS)
    assert frames[0]["value"] == 0


def test_multistate_value_is_encoded_as_int() -> None:
    readings = [Reading(BacnetObjectType.multiStateValue, 5, 2)]
    frames = encode_telemetry_frames("gw-1", readings, _REGISTRY, now=_TS)
    assert frames[0]["value"] == 2
    assert isinstance(frames[0]["value"], int)


def test_reading_without_timestamp_uses_now() -> None:
    readings = [Reading(BacnetObjectType.analogInput, 1, 1.0, timestamp=None)]
    frames = encode_telemetry_frames("gw-1", readings, _REGISTRY, now=_TS)
    assert frames[0]["timestamp"] == "2025-01-01T12:00:00+00:00"


def test_unknown_bacnet_point_is_skipped() -> None:
    # instance 99 is not in the registry
    readings = [
        Reading(BacnetObjectType.analogInput, 99, 1.0),
        Reading(BacnetObjectType.analogInput, 1, 2.0),  # known
    ]
    frames = encode_telemetry_frames("gw-1", readings, _REGISTRY, now=_TS)
    assert len(frames) == 1
    assert frames[0]["point_id"] == "pt-ai-1"


def test_multiple_readings_encode_to_multiple_frames() -> None:
    readings = [
        Reading(BacnetObjectType.analogInput, 1, 10.0, _TS),
        Reading(BacnetObjectType.binaryValue, 3, "active", _TS),
    ]
    frames = encode_telemetry_frames("gw-1", readings, _REGISTRY, now=_TS)
    assert len(frames) == 2
    assert {f["point_id"] for f in frames} == {"pt-ai-1", "pt-bv-3"}


def test_empty_readings_returns_empty_frames() -> None:
    frames = encode_telemetry_frames("gw-1", [], _REGISTRY, now=_TS)
    assert frames == []
