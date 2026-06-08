"""EP-008.9 (#68) — down-link package/client import cleanly without the `grpc` extra.

The pure layer (models/executor/pump/backoff) and the client module must import without
grpcio; grpc is imported lazily only inside the wire methods (ADR-017).
"""

from __future__ import annotations

import importlib


def test_downlink_package_exposes_pure_api() -> None:
    pkg = importlib.import_module("bbc_sim.bows.downlink")
    names = ("CommandExecutor", "CommandPump", "ControlCommand", "ControlResult", "EgressConfig")
    for name in names:
        assert hasattr(pkg, name)


def test_client_module_imports_without_grpc_at_module_level() -> None:
    # The client module pulls grpc only inside _import_grpc/_import_stubs; importing it
    # must not require the optional extra.
    mod = importlib.import_module("bbc_sim.bows.downlink.client")
    assert hasattr(mod, "GatewayEgressClient")


def test_egress_config_defaults() -> None:
    from bbc_sim.bows.downlink.models import EgressConfig

    cfg = EgressConfig(endpoint="bos:443", gateway_id="gw-1", target="10.0.0.5:47808")
    assert cfg.tenant == "default"
    assert cfg.tls is True  # secure by default; --insecure opts out for loopback
    assert cfg.local_address is None
