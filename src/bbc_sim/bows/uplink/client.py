"""GatewayIngress gRPC uplink client — optional (ADR-017, #73).

Mirrors the downlink pattern (client.py): grpcio/protobuf are an optional
dependency (`uv sync --extra grpc`). The client dials out to Building OS,
opens one client-streaming RPC per session, encodes BACnet readings into
TelemetryFrames, and streams them upstream.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bbc_sim.bows.downlink.backoff import reconnect_delays
from bbc_sim.bows.point_registry import PointRegistry
from bbc_sim.bows.uplink.encoder import encode_telemetry_frames
from bbc_sim.bows.models import Reading

_log = logging.getLogger(__name__)

_INSTALL_HINT = "gRPC uplink needs the optional 'grpc' extra — run: uv sync --extra grpc"


@dataclass
class IngressConfig:
    """Configuration for a GatewayIngress uplink client run.

    ``endpoint`` is the Building OS GatewayIngress ``host:port``. ``gateway_id`` is
    the upstream gateway identifier — never the B-BC ``bbc_id`` (ADR-003).
    ``point_registry`` is the shared point list for BACnet -> point_id resolution (#73).
    mTLS material is injected from the environment (``BOWS_INGRESS_TLS_CA/CERT/KEY``).
    """

    endpoint: str
    gateway_id: str
    point_registry: PointRegistry
    local_address: str | None = None
    tls: bool = True
    keepalive_s: float = 20.0
    max_backoff_s: float = 30.0


def _import_grpc() -> tuple[Any, Any]:
    try:
        import grpc
        from grpc import aio
    except ModuleNotFoundError as exc:
        raise RuntimeError(_INSTALL_HINT) from exc
    return grpc, aio


def _import_stubs() -> tuple[Any, Any]:
    try:
        from bbc_sim.bows.uplink import gateway_ingress_pb2 as pb2
        from bbc_sim.bows.uplink import gateway_ingress_pb2_grpc as pb2_grpc
    except ModuleNotFoundError as exc:
        raise RuntimeError(_INSTALL_HINT) from exc
    return pb2, pb2_grpc


def _read_pem(path: str | None) -> bytes | None:
    if not path:
        return None
    with open(path, "rb") as fh:
        return fh.read()


def _mtls_pems() -> tuple[bytes | None, bytes, bytes]:
    cert = _read_pem(os.environ.get("BOWS_INGRESS_TLS_CERT"))
    key = _read_pem(os.environ.get("BOWS_INGRESS_TLS_KEY"))
    if cert is None or key is None:
        raise RuntimeError(
            "mTLS requires BOWS_INGRESS_TLS_CERT and BOWS_INGRESS_TLS_KEY"
        )
    return _read_pem(os.environ.get("BOWS_INGRESS_TLS_CA")), cert, key


def _channel_credentials(grpc: Any) -> Any:
    ca, cert, key = _mtls_pems()
    return grpc.ssl_channel_credentials(
        root_certificates=ca, private_key=key, certificate_chain=cert
    )


def _channel_options(config: IngressConfig) -> list[tuple[str, int]]:
    return [
        ("grpc.keepalive_time_ms", int(config.keepalive_s * 1000)),
        ("grpc.keepalive_timeout_ms", 10000),
        ("grpc.keepalive_permit_without_calls", 1),
    ]


class GatewayIngressClient:
    """Stream TelemetryFrames to Building OS GatewayIngress (#73)."""

    def __init__(self, config: IngressConfig) -> None:
        self.config = config

    async def send_readings(self, readings: list[Reading]) -> int:
        """Encode ``readings`` and stream them; return accepted count from StreamAck."""
        frames = encode_telemetry_frames(
            self.config.gateway_id,
            readings,
            self.config.point_registry,
            now=datetime.now(UTC),
        )
        if not frames:
            return 0
        grpc, aio = _import_grpc()
        pb2, pb2_grpc = _import_stubs()
        options = _channel_options(self.config)
        if self.config.tls:
            channel = aio.secure_channel(
                self.config.endpoint, _channel_credentials(grpc), options=options
            )
        else:
            channel = aio.insecure_channel(self.config.endpoint, options=options)
        stub = pb2_grpc.GatewayIngressStub(channel)

        async def _frame_iter() -> Any:
            for frame in frames:
                yield pb2.TelemetryFrame(
                    gateway_id=frame["gateway_id"],
                    point_id=frame["point_id"],
                    value=frame["value"],
                    timestamp=frame["timestamp"],
                )

        try:
            ack = await stub.StreamTelemetry(_frame_iter())
            return int(ack.accepted)
        finally:
            await channel.close()

    async def _connect_and_serve(self) -> None:
        """Single-shot: open the gRPC channel and stream once (subclassable for tests)."""
        await self.send_readings([])  # no-op if no readings; overridden in tests

    async def run_forever(self, stop: asyncio.Event | None = None) -> None:
        """Reconnect with backoff+jitter until ``stop`` is set."""
        stop = stop or asyncio.Event()
        if stop.is_set():
            return
        delays = reconnect_delays(cap=self.config.max_backoff_s)
        while not stop.is_set():
            try:
                await self._connect_and_serve()
                delays = reconnect_delays(cap=self.config.max_backoff_s)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                _log.exception("GatewayIngress stream failed; reconnecting")
            if stop.is_set():
                break
            try:
                await asyncio.wait_for(stop.wait(), timeout=next(delays))
            except TimeoutError:
                pass


def run(config: IngressConfig) -> None:
    """Blocking entry point for the CLI."""
    asyncio.run(GatewayIngressClient(config).run_forever())
