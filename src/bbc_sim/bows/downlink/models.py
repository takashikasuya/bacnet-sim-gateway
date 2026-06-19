"""Down-link data types (gRPC-free, ADR-017).

These mirror the ``proto/gateway_egress.proto`` messages but carry no protobuf
dependency, so the executor/pump logic is unit-testable without the `grpc` extra. The
gRPC client adapts proto messages to/from these at the wire boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bbc_sim.bows.point_registry import PointRegistry


@dataclass(frozen=True)
class ControlCommand:
    """A down-link write request from Building OS GatewayEgress (#74).

    Building OS resolves the point_id from its digital twin; the GW resolves
    point_id -> (object_type, instance) locally via the shared point list.
    Fields 3-5 (bacnet_device / object_type / instance_no) are reserved in
    the proto schema and no longer carried on the wire.
    """

    control_id: str
    point_id: str
    present_value: float
    priority: int | None = None  # BACnet write priority 1..16; None = unset


@dataclass(frozen=True)
class ControlResult:
    """Outcome of a ControlCommand, correlated by ``control_id``."""

    control_id: str
    success: bool
    response: str = ""


@dataclass
class EgressConfig:
    """Configuration for a GatewayEgress down-link client run.

    ``endpoint`` is the Building OS GatewayEgress ``host:port``. ``gateway_id`` is the
    upstream gateway identifier announced in ``Hello`` — never the B-BC ``bbc_id``
    (ADR-003). ``target`` is the B-BC address (host:port) to write to.
    ``point_registry`` is the shared point list for point_id -> BACnet resolution (#74).
    mTLS material is injected from the environment (``BOWS_EGRESS_TLS_CA/CERT/KEY``).
    """

    endpoint: str
    gateway_id: str
    target: str
    point_registry: PointRegistry = field(default_factory=lambda: PointRegistry([]))
    local_address: str | None = None  # BACnet client bind addr; ephemeral if None
    tls: bool = True
    keepalive_s: float = 20.0
    max_backoff_s: float = 30.0
