"""Transport factory: map a URI to a Transport (ADR-013).

- ``memory``                          -> InMemoryTransport (self-contained, default)
- ``mqtt://host:port``                -> MqttTransport
- ``zmq://sub_endpoint|pub_endpoint`` -> ZmqTransport
"""

from __future__ import annotations

from urllib.parse import urlparse

from bbc_sim.southbound.transport import InMemoryTransport, Transport


def make_transport(uri: str) -> Transport:
    if uri in ("memory", "memory://"):
        return InMemoryTransport()
    parsed = urlparse(uri)
    if parsed.scheme == "mqtt":
        from bbc_sim.southbound.mqtt import MqttTransport

        return MqttTransport(parsed.hostname or "127.0.0.1", parsed.port or 1883)
    if parsed.scheme == "zmq":
        from bbc_sim.southbound.zeromq import ZmqTransport

        # zmq://<sub>|<pub>  e.g. zmq://tcp://127.0.0.1:5556|tcp://127.0.0.1:5557
        body = uri[len("zmq://") :]
        sub, _, pub = body.partition("|")
        return ZmqTransport(sub, pub or sub)
    raise ValueError(f"unsupported transport uri: {uri!r}")
