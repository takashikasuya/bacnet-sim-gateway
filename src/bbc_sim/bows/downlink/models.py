"""Down-link data types (gRPC-free, ADR-017).

These mirror the ``proto/gateway_egress.proto`` messages but carry no protobuf
dependency, so the executor/pump logic is unit-testable without the `grpc` extra. The
gRPC client adapts proto messages to/from these at the wire boundary.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlCommand:
    """A down-link write request resolved by Building OS (GatewayEgress)."""

    control_id: str
    point_id: str
    bacnet_device: int
    object_type: int  # ASHRAE 135 object-type enum (0=AI..19=MV)
    instance_no: int
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
    (ADR-003). ``target`` is the B-BC address (host:port) to write to; ``device_instance``,
    when set, is the device id that target hosts — commands for any other device are
    rejected. mTLS material is injected from the environment
    (``BOWS_EGRESS_TLS_CA/CERT/KEY``); no defaults.
    """

    endpoint: str
    gateway_id: str
    target: str
    device_instance: int | None = None  # if set, enforce ControlCommand.bacnet_device
    local_address: str | None = None  # BACnet client bind addr; ephemeral if None
    tls: bool = True
    keepalive_s: float = 20.0
    max_backoff_s: float = 30.0
