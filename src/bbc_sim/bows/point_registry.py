"""Shared point list registry for BOWS ingress and egress resolution (#73, #74).

Provides bidirectional lookup between point_id (Building OS canonical identifier)
and BACnet (object_type, instance) — the GW-side shared point list (ADR-014).
"""

from __future__ import annotations

from bbc_sim.models import BacnetObjectSpec, BacnetObjectType


class PointRegistry:
    """Bidirectional lookup: point_id <-> (BacnetObjectType, instance).

    Built from the simulator.yaml object list and shared between ingress (uplink
    encoding) and egress (ControlCommand resolution). Immutable after construction.
    """

    def __init__(self, specs: list[BacnetObjectSpec]) -> None:
        self._by_point_id: dict[str, tuple[BacnetObjectType, int]] = {
            s.point_id: (s.object_type, s.object_instance) for s in specs
        }
        self._by_bacnet: dict[tuple[BacnetObjectType, int], str] = {
            (s.object_type, s.object_instance): s.point_id for s in specs
        }

    def resolve_point_id(self, point_id: str) -> tuple[BacnetObjectType, int] | None:
        """Return (object_type, instance) for a known point_id, else None."""
        return self._by_point_id.get(point_id)

    def resolve_bacnet(self, object_type: BacnetObjectType, instance: int) -> str | None:
        """Return the point_id for a known (object_type, instance) pair, else None."""
        return self._by_bacnet.get((object_type, instance))
