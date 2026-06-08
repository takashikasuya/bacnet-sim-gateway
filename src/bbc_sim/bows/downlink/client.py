"""GatewayEgress gRPC down-link client — optional (ADR-017, #67).

grpcio/protobuf are an **optional** dependency (`uv sync --extra grpc`), imported lazily
so this module imports cleanly without them. Uses ``grpc.aio`` so the single asyncio
loop is never blocked (ADR-010 — no thread executor, unlike the AMQP/proton transport).

The client dials out to Building OS as a building-edge client (no inbound ports), opens
one bidirectional stream per gateway with ``Hello{gateway_id}``, executes inbound
``ControlCommand``s as BACnet WriteProperty, and returns ``ControlResult``s. The pure
command->result logic lives in ``executor``/``pump``; here we only adapt proto messages
and manage the channel/reconnect.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from bbc_sim.bows.downlink.backoff import reconnect_delays
from bbc_sim.bows.downlink.executor import CommandExecutor
from bbc_sim.bows.downlink.models import ControlCommand, ControlResult, EgressConfig
from bbc_sim.services.client import build_client, ephemeral_local

_log = logging.getLogger(__name__)

_INSTALL_HINT = "gRPC down-link needs the optional 'grpc' extra — run: uv sync --extra grpc"


def _import_grpc() -> tuple[Any, Any]:
    try:
        import grpc
        from grpc import aio
    except ModuleNotFoundError as exc:  # optional extra not installed
        raise RuntimeError(_INSTALL_HINT) from exc
    return grpc, aio


def _import_stubs() -> tuple[Any, Any]:
    try:
        from bbc_sim.bows.downlink import gateway_egress_pb2 as pb2
        from bbc_sim.bows.downlink import gateway_egress_pb2_grpc as pb2_grpc
    except ModuleNotFoundError as exc:  # stubs import grpc/protobuf at load time
        raise RuntimeError(_INSTALL_HINT) from exc
    return pb2, pb2_grpc


def command_from_proto(msg: Any) -> ControlCommand:
    """Adapt a proto ``ControlCommand`` to the gRPC-free dataclass."""
    return ControlCommand(
        control_id=msg.control_id,
        point_id=msg.point_id,
        bacnet_device=msg.bacnet_device,
        object_type=msg.object_type,
        instance_no=msg.instance_no,
        present_value=msg.present_value,
        priority=msg.priority or None,  # proto uint32 0 -> unset
    )


def result_to_proto(pb2: Any, result: ControlResult) -> Any:
    """Adapt a ControlResult to a proto ``ClientMessage(result=...)``."""
    return pb2.ClientMessage(
        result=pb2.ControlResult(
            control_id=result.control_id,
            success=result.success,
            response=result.response,
        )
    )


def _read_pem(path: str | None) -> bytes | None:
    if not path:
        return None
    with open(path, "rb") as fh:
        return fh.read()


def _channel_credentials(grpc: Any) -> Any:
    """Build mTLS channel credentials from env-injected PEMs (no defaults, ADR-015 §4)."""
    return grpc.ssl_channel_credentials(
        root_certificates=_read_pem(os.environ.get("BOWS_EGRESS_TLS_CA")),
        private_key=_read_pem(os.environ.get("BOWS_EGRESS_TLS_KEY")),
        certificate_chain=_read_pem(os.environ.get("BOWS_EGRESS_TLS_CERT")),
    )


class GatewayEgressClient:
    """Connect to Building OS GatewayEgress and serve down-link control commands."""

    def __init__(self, config: EgressConfig, *, executor: CommandExecutor | None = None) -> None:
        self.config = config
        self._executor = executor
        self._app: Any = None

    def _ensure_executor(self) -> CommandExecutor:
        if self._executor is None:
            self._app = build_client(self.config.local_address or ephemeral_local())
            self._executor = CommandExecutor(self._app, self.config.target)
        return self._executor

    def _channel_options(self) -> list[tuple[str, int]]:
        return [
            ("grpc.keepalive_time_ms", int(self.config.keepalive_s * 1000)),
            ("grpc.keepalive_timeout_ms", 10000),
            ("grpc.keepalive_permit_without_calls", 1),
        ]

    async def serve_stream(self, stub: Any, pb2: Any) -> None:
        """Run one bidi stream: Hello, then command -> WriteProperty -> result."""
        executor = self._ensure_executor()
        outbox: asyncio.Queue[Any] = asyncio.Queue()

        async def requests() -> Any:
            yield pb2.ClientMessage(hello=pb2.Hello(gateway_id=self.config.gateway_id))
            while True:
                item = await outbox.get()
                if item is None:  # sentinel: stream ended
                    return
                yield item

        call = stub.Connect(requests())
        try:
            async for server_msg in call:
                if server_msg.WhichOneof("payload") != "command":
                    continue
                result = await executor.execute(command_from_proto(server_msg.command))
                await outbox.put(result_to_proto(pb2, result))
        finally:
            await outbox.put(None)

    async def _connect_and_serve(self) -> None:
        grpc, aio = _import_grpc()
        pb2, pb2_grpc = _import_stubs()
        options = self._channel_options()
        if self.config.tls:
            channel = aio.secure_channel(
                self.config.endpoint, _channel_credentials(grpc), options=options
            )
        else:
            channel = aio.insecure_channel(self.config.endpoint, options=options)
        try:
            await self.serve_stream(pb2_grpc.GatewayEgressStub(channel), pb2)
        finally:
            await channel.close()

    async def run_forever(self, stop: asyncio.Event | None = None) -> None:
        """Connect, serve, and reconnect with backoff+jitter until ``stop`` is set."""
        stop = stop or asyncio.Event()
        self._ensure_executor()
        delays = reconnect_delays(cap=self.config.max_backoff_s)
        try:
            while not stop.is_set():
                try:
                    await self._connect_and_serve()
                    delays = reconnect_delays(cap=self.config.max_backoff_s)  # clean end: reset
                except Exception:  # noqa: BLE001 - reconnect on any stream/transport failure
                    _log.exception("GatewayEgress stream failed; reconnecting")
                if stop.is_set():
                    break
                try:
                    await asyncio.wait_for(stop.wait(), timeout=next(delays))
                except TimeoutError:
                    pass
        finally:
            if self._app is not None:
                self._app.close()


def run(config: EgressConfig) -> None:
    """Blocking entry point for the CLI."""
    asyncio.run(GatewayEgressClient(config).run_forever())
