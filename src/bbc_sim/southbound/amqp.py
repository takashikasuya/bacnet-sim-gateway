"""AMQP 1.0 (Eclipse Hono northbound) southbound transport — optional (ADR-016).

`python-qpid-proton` is an **optional** dependency (`uv sync --extra amqp`); it is
imported lazily inside the methods that need it, so this module imports cleanly without
it. Blocking proton calls run in a thread executor so the single asyncio loop is never
blocked (ADR-010).

The channel→Hono mapping (`telemetry/{tenant}/{deviceId}` → address `/telemetry/{tenant}`
plus `device_id`/`orig_address` message properties) is pure and unit-tested; the real
proton round-trip is integration-marked + manual.
"""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from bbc_sim.southbound.transport import Handler

_log = logging.getLogger(__name__)

_INSTALL_HINT = "AMQP transport needs the optional 'amqp' extra — run: uv sync --extra amqp"


def hono_address(channel: str) -> str:
    """Map a BOWS channel ``telemetry/{tenant}/{deviceId}`` to a Hono address.

    Hono telemetry is addressed by tenant (``/telemetry/{tenant}``); the device is
    carried as a message property, not in the address.
    """
    parts = channel.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "telemetry":
        return f"/telemetry/{parts[1]}"
    return "/" + channel.strip("/")


def device_id_from_channel(channel: str) -> str | None:
    """Extract ``deviceId`` from ``telemetry/{tenant}/{deviceId}`` (else None)."""
    parts = channel.strip("/").split("/")
    if len(parts) >= 3 and parts[0] == "telemetry":
        return parts[2]
    return None


class AmqpTransport:
    """Publish telemetry to Hono northbound over AMQP 1.0.

    Credentials/TLS are injected from the environment (``BOWS_AMQP_USER`` /
    ``BOWS_AMQP_PASSWORD``); no defaults are baked into code or docs (ADR-015 §4 /
    ADR-016).
    """

    def __init__(self, host: str, port: int = 5671, *, tls: bool = True) -> None:
        self.host = host
        self.port = port
        self.tls = tls
        self.user = os.environ.get("BOWS_AMQP_USER")
        self.password = os.environ.get("BOWS_AMQP_PASSWORD")
        self._conn: Any = None
        # qpid-proton's BlockingConnection is not safe for concurrent multi-thread
        # use, so serialize every proton call onto one dedicated worker thread.
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="bows-amqp")

    @property
    def url(self) -> str:
        scheme = "amqps" if self.tls else "amqp"
        return f"{scheme}://{self.host}:{self.port}"

    async def _run(self, fn: Any, *args: Any) -> Any:
        return await asyncio.get_running_loop().run_in_executor(self._executor, fn, *args)

    async def start(self) -> None:
        await self._run(self._connect)

    def _connect(self) -> None:
        if (self.user is None) != (self.password is None):
            raise RuntimeError("BOWS_AMQP_USER and BOWS_AMQP_PASSWORD must be set together")
        try:
            from proton.utils import BlockingConnection  # lazy: optional dep
        except ModuleNotFoundError as exc:
            raise RuntimeError(_INSTALL_HINT) from exc
        opts: dict[str, Any] = {}
        if self.user is not None:
            opts["user"] = self.user
            opts["password"] = self.password
        self._conn = BlockingConnection(self.url, **opts)

    async def stop(self) -> None:
        if self._conn is not None:
            await self._run(self._close)
        self._executor.shutdown(wait=False)

    def _close(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            conn.close()

    def subscribe(self, channel: str, handler: Handler) -> None:
        # Telemetry is publish-only; there is no AMQP receive loop yet. Fail fast rather
        # than silently dropping inbound messages — down-link/subscribe is EP-008 #49.
        raise NotImplementedError(
            "AmqpTransport is telemetry publish-only; down-link/subscribe is EP-008 #49"
        )

    async def publish(self, channel: str, payload: bytes) -> None:
        address = hono_address(channel)
        attrs = {"device_id": device_id_from_channel(channel), "orig_address": channel}
        await self._run(self._send, address, payload, attrs)

    def _send(self, address: str, payload: bytes, attrs: dict[str, Any]) -> None:
        if self._conn is None:
            raise RuntimeError("AmqpTransport.publish() called before start()")
        try:
            from proton import Message  # lazy: optional dep
        except ModuleNotFoundError as exc:
            raise RuntimeError(_INSTALL_HINT) from exc
        sender = self._conn.create_sender(address)
        try:
            msg = Message(body=payload)
            msg.properties = {k: v for k, v in attrs.items() if v is not None}
            sender.send(msg)
        finally:
            sender.close()
