"""EP-008.12 (#71, #74) — GatewayEgress gRPC loopback (real grpc.aio, integration).

Spins an in-process GatewayEgress server, runs the real client against it, and asserts
the full Hello -> ControlCommand -> WriteProperty -> ControlResult round-trip with the
new point_id-only contract (#74). Marked integration so the default suite stays grpc-free.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

grpc_aio = pytest.importorskip("grpc.aio")

from bbc_sim.bows.downlink import gateway_egress_pb2 as pb2  # noqa: E402
from bbc_sim.bows.downlink import gateway_egress_pb2_grpc as pb2_grpc  # noqa: E402
from bbc_sim.bows.downlink.client import (  # noqa: E402
    GatewayEgressClient,
    command_from_proto,
    result_to_proto,
)
from bbc_sim.bows.downlink.executor import CommandExecutor  # noqa: E402
from bbc_sim.bows.downlink.models import ControlResult, EgressConfig  # noqa: E402
from bbc_sim.bows.point_registry import PointRegistry  # noqa: E402
from bbc_sim.models import BacnetObjectSpec, BacnetObjectType  # noqa: E402

pytestmark = pytest.mark.integration


def _spec(point_id: str, object_type: BacnetObjectType, instance: int) -> BacnetObjectSpec:
    return BacnetObjectSpec(
        point_id=point_id, object_type=object_type, object_instance=instance, object_name=point_id
    )


class _Servicer(pb2_grpc.GatewayEgressServicer):
    def __init__(self, commands: list[Any]) -> None:
        self.hello: str | None = None
        self.results: list[Any] = []
        self._commands = commands

    async def Connect(self, request_iterator: Any, context: Any) -> Any:
        iterator = request_iterator.__aiter__()
        first = await iterator.__anext__()
        self.hello = first.hello.gateway_id
        for command in self._commands:
            yield pb2.ServerMessage(command=command)
        async for msg in iterator:
            if msg.WhichOneof("payload") == "result":
                self.results.append(msg.result)
                break


async def test_loopback_command_writes_property_and_returns_result(fake_bacnet_app) -> None:
    registry = PointRegistry([_spec("p1", BacnetObjectType.analogValue, 7)])
    command = pb2.ControlCommand(
        control_id="c1",
        point_id="p1",
        present_value=21.5,
        priority=10,
    )
    servicer = _Servicer([command])
    server = grpc_aio.server()
    pb2_grpc.add_GatewayEgressServicer_to_server(servicer, server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    app = fake_bacnet_app()
    config = EgressConfig(
        endpoint=f"127.0.0.1:{port}",
        gateway_id="gw-1",
        target="bbc:47808",
        point_registry=registry,
        tls=False,
    )
    client = GatewayEgressClient(
        config, executor=CommandExecutor(app, "bbc:47808", point_registry=registry)
    )
    try:
        await asyncio.wait_for(client._connect_and_serve(), timeout=10)
    finally:
        await server.stop(grace=None)

    assert servicer.hello == "gw-1"
    assert app.calls == [("bbc:47808", "analogValue,7", "present-value", 21.5, 10)]
    assert servicer.results and servicer.results[0].control_id == "c1"
    assert servicer.results[0].success is True


def test_proto_adapters_round_trip() -> None:
    proto_cmd = pb2.ControlCommand(
        control_id="c9",
        point_id="p9",
        present_value=1.0,
        priority=0,
    )
    cmd = command_from_proto(proto_cmd)
    assert cmd.point_id == "p9"
    assert cmd.present_value == 1.0
    assert cmd.priority is None  # proto 0 -> unset

    client_msg = result_to_proto(pb2, ControlResult("c9", True, "ok"))
    assert client_msg.WhichOneof("payload") == "result"
    assert client_msg.result.control_id == "c9" and client_msg.result.success is True
