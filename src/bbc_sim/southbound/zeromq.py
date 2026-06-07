"""ZeroMQ southbound transport (pyzmq async). Real network I/O; tests are integration.

Uses a SUB socket for telemetry (multipart: channel, payload) and a PUB socket for
commands. Both sockets ``connect()`` to the given endpoints (a broker/proxy is expected
to bind). Configurable bind/connect roles are a future enhancement.
"""

from __future__ import annotations

import asyncio
import logging

import zmq
import zmq.asyncio

from bbc_sim.southbound.transport import Handler

_log = logging.getLogger(__name__)


class ZmqTransport:
    """Transport backed by ZeroMQ PUB/SUB sockets."""

    def __init__(self, sub_endpoint: str, pub_endpoint: str) -> None:
        self._ctx = zmq.asyncio.Context.instance()
        self._sub = self._ctx.socket(zmq.SUB)
        self._pub = self._ctx.socket(zmq.PUB)
        self._sub_endpoint = sub_endpoint
        self._pub_endpoint = pub_endpoint
        self._handlers: dict[str, list[Handler]] = {}
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._sub.connect(self._sub_endpoint)
        self._pub.connect(self._pub_endpoint)
        self._task = asyncio.create_task(self._recv_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self._sub.close()
        self._pub.close()

    def subscribe(self, channel: str, handler: Handler) -> None:
        self._handlers.setdefault(channel, []).append(handler)
        self._sub.setsockopt_string(zmq.SUBSCRIBE, channel)

    async def publish(self, channel: str, payload: bytes) -> None:
        await self._pub.send_multipart([channel.encode(), payload])

    async def _recv_loop(self) -> None:
        while True:
            frames = await self._sub.recv_multipart()
            await self._dispatch(frames)

    async def _dispatch(self, frames: list[bytes]) -> None:
        """Route a received multipart message to subscribers.

        Telemetry is exactly (channel, payload); anything else is malformed and is
        logged and skipped rather than allowed to break the receive loop.
        """
        if len(frames) != 2:
            _log.warning("ignoring malformed multipart message with %d frame(s)", len(frames))
            return
        channel_b, payload = frames
        channel = channel_b.decode()
        for handler in self._handlers.get(channel, []):
            await handler(channel, payload)
