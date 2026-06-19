"""Encode BACnet readings into TelemetryFrame dicts for gRPC GatewayIngress (#73).

Each reading is resolved via PointRegistry (point_id canonical identifier).
Readings whose (object_type, instance) is not in the registry are skipped.
Binary values are normalised to 0/1 as required by the contract.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from bbc_sim.bows.models import Reading
from bbc_sim.bows.point_registry import PointRegistry
from bbc_sim.models import BacnetObjectType

_log = logging.getLogger(__name__)

_BINARY_TRUTHY = {"active", "1", "true", "on"}


def _encode_value(object_type: BacnetObjectType, value: Any) -> float | int:
    """Normalise a BACnet present-value to a JSON number for TelemetryFrame."""
    if object_type.is_binary:
        normalized = str(value).strip().lower()
        return 1 if normalized in _BINARY_TRUTHY else 0
    if object_type.is_multistate:
        return int(value)
    return float(value)


def encode_telemetry_frames(
    gateway_id: str,
    readings: list[Reading],
    registry: PointRegistry,
    *,
    now: datetime,
) -> list[dict[str, Any]]:
    """Return one TelemetryFrame dict per reading that has a known point_id.

    Unknown (object_type, instance) pairs are skipped with a debug log.
    Each frame matches the proto TelemetryFrame message shape:
      {gateway_id, point_id, value, timestamp (RFC3339)}.
    """
    frames: list[dict[str, Any]] = []
    for reading in readings:
        point_id = registry.resolve_bacnet(reading.object_type, reading.instance)
        if point_id is None:
            _log.debug(
                "ingress encoder: no point_id for (%s, %d); skipping",
                reading.object_type.value,
                reading.instance,
            )
            continue
        ts = reading.timestamp or now
        frames.append(
            {
                "gateway_id": gateway_id,
                "point_id": point_id,
                "value": _encode_value(reading.object_type, reading.present_value),
                "timestamp": ts.isoformat(),
            }
        )
    return frames
