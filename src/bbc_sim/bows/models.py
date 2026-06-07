"""BOWS data types: a single BACnet reading and connector config (EP-008)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bbc_sim.models import BacnetObjectType


@dataclass
class Reading:
    """One acquired BACnet object value to forward to Building OS."""

    object_type: BacnetObjectType
    instance: int
    present_value: Any
    timestamp: datetime | None = None


@dataclass
class BowsConfig:
    """Configuration for a BOWS connector run.

    `target` is the B-BC address (host:port). `device_id` is the Building OS device
    identifier (string); `localId = {tenant}/{device_id}` is resolved server-side to
    point_id (OxiGraph) — out of connector scope (ADR-014/015).
    """

    target: str
    device_id: str
    tenant: str = "default"
    transport_uri: str = "memory"
    interval: float = 60.0
    local_address: str | None = None  # BACnet client bind addr; ephemeral if None
