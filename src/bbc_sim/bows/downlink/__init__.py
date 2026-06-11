"""BOWS down-link control — Building OS GatewayEgress(gRPC) → BACnet WriteProperty.

Pure logic (models/executor/pump/backoff) is gRPC-free and imports cleanly without the
optional `grpc` extra; the real gRPC wire lives in ``client`` and imports grpcio lazily
(ADR-017, EP-008 #67).
"""

from bbc_sim.bows.downlink.executor import CommandExecutor
from bbc_sim.bows.downlink.models import ControlCommand, ControlResult, EgressConfig
from bbc_sim.bows.downlink.pump import CommandPump

__all__ = [
    "CommandExecutor",
    "CommandPump",
    "ControlCommand",
    "ControlResult",
    "EgressConfig",
]
