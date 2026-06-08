"""EP-008.7 (#48) — AMQP/Hono transport mapping (no proton; lazy optional dep)."""

from __future__ import annotations

import pytest

from bbc_sim.southbound.amqp import AmqpTransport, device_id_from_channel, hono_address
from bbc_sim.southbound.factory import make_transport

# ---- pure channel → Hono mapping ----


@pytest.mark.parametrize(
    "channel,address",
    [
        ("telemetry/default/bbc-local-001", "/telemetry/default"),
        ("telemetry/site-a/dev9", "/telemetry/site-a"),
        ("custom/thing", "/custom/thing"),
    ],
)
def test_hono_address(channel, address):
    assert hono_address(channel) == address


@pytest.mark.parametrize(
    "channel,device",
    [
        ("telemetry/default/bbc-local-001", "bbc-local-001"),
        ("telemetry/site-a/dev9", "dev9"),
        ("telemetry/onlytenant", None),
        ("nope", None),
    ],
)
def test_device_id_from_channel(channel, device):
    assert device_id_from_channel(channel) == device


# ---- factory wiring (no proton needed) ----


def test_factory_amqps_tls_default_port():
    t = make_transport("amqps://hono.example")
    assert isinstance(t, AmqpTransport)
    assert (t.host, t.port, t.tls) == ("hono.example", 5671, True)
    assert t.url == "amqps://hono.example:5671"


def test_factory_amqp_plaintext_default_port():
    t = make_transport("amqp://broker:5672")
    assert isinstance(t, AmqpTransport)
    assert (t.host, t.port, t.tls) == ("broker", 5672, False)
    assert t.url == "amqp://broker:5672"


def test_module_imports_without_proton():
    # The module/class must be usable without the optional `amqp` extra installed;
    # proton is only imported inside start()/publish().
    import importlib

    mod = importlib.import_module("bbc_sim.southbound.amqp")
    assert hasattr(mod, "AmqpTransport")


# ---- publish maps channel → address + attributes (proton send stubbed) ----


async def test_publish_maps_channel_to_address_and_attributes(monkeypatch):
    t = AmqpTransport("hono.example", 5671)
    captured: dict[str, object] = {}

    def fake_send(address, payload, attrs):
        captured.update(address=address, payload=payload, attrs=attrs)

    monkeypatch.setattr(t, "_send", fake_send)
    try:
        await t.publish("telemetry/default/bbc-local-001", b"{}")
    finally:
        await t.stop()

    assert captured["address"] == "/telemetry/default"
    assert captured["payload"] == b"{}"
    assert captured["attrs"] == {
        "device_id": "bbc-local-001",
        "orig_address": "telemetry/default/bbc-local-001",
    }


# ---- robustness / fail-fast (PR #66 review) ----


def test_subscribe_raises_not_implemented():
    # AMQP has no receive loop yet; subscribing must fail fast, not silently drop.
    t = AmqpTransport("hono.example")
    with pytest.raises(NotImplementedError):
        t.subscribe("telemetry/default/x", lambda _c, _p: None)
    t._executor.shutdown(wait=False)


def test_send_before_start_raises_runtime_error_not_import_error():
    # _conn is checked before importing proton, so the error is the intended hint,
    # not a ModuleNotFoundError when the optional extra is absent.
    t = AmqpTransport("hono.example")
    with pytest.raises(RuntimeError, match="before start"):
        t._send("/telemetry/default", b"{}", {})
    t._executor.shutdown(wait=False)


async def test_start_requires_both_credentials_or_neither(monkeypatch):
    monkeypatch.setenv("BOWS_AMQP_USER", "devices")
    monkeypatch.delenv("BOWS_AMQP_PASSWORD", raising=False)
    t = AmqpTransport("hono.example")
    try:
        with pytest.raises(RuntimeError, match="must be set together"):
            await t.start()
    finally:
        await t.stop()


async def test_start_without_proton_gives_install_hint(monkeypatch):
    # proton is not installed in CI/dev (optional extra); _connect must surface the
    # actionable install hint rather than a raw ModuleNotFoundError.
    import importlib.util

    if importlib.util.find_spec("proton") is not None:
        pytest.skip("proton installed; install-hint path not exercised")
    monkeypatch.delenv("BOWS_AMQP_USER", raising=False)
    monkeypatch.delenv("BOWS_AMQP_PASSWORD", raising=False)
    t = AmqpTransport("hono.example")
    try:
        with pytest.raises(RuntimeError, match="amqp"):
            await t.start()
    finally:
        await t.stop()


async def test_credentials_read_from_env(monkeypatch):
    monkeypatch.setenv("BOWS_AMQP_USER", "devices")
    monkeypatch.setenv("BOWS_AMQP_PASSWORD", "s3cret")
    t = AmqpTransport("hono.example")
    assert t.user == "devices"
    assert t.password == "s3cret"


async def test_no_default_credentials(monkeypatch):
    monkeypatch.delenv("BOWS_AMQP_USER", raising=False)
    monkeypatch.delenv("BOWS_AMQP_PASSWORD", raising=False)
    t = AmqpTransport("hono.example")
    assert t.user is None and t.password is None  # no baked-in defaults (ADR-016)
