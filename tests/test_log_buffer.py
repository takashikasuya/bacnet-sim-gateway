"""EP-007.1 — RingBufferLogHandler and /logs endpoint (PR-F-053)."""

from __future__ import annotations

import logging
import time

import pytest
from fastapi.testclient import TestClient

from bbc_sim.observability.log_buffer import LogEntry, RingBufferLogHandler
from bbc_sim.rest.api import create_app
from bbc_sim.rest.status import StatusProvider
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
def handler() -> RingBufferLogHandler:
    return RingBufferLogHandler(capacity=10)


def _emit(h: RingBufferLogHandler, level: str, msg: str, ts: float | None = None) -> None:
    record = logging.LogRecord(
        name="bbc_sim.test",
        level=getattr(logging, level),
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    if ts is not None:
        record.created = ts
    h.emit(record)


def test_emit_stores_entry(handler):
    _emit(handler, "INFO", "hello")
    assert len(handler.records) == 1
    e = handler.records[0]
    assert isinstance(e, LogEntry)
    assert e.level == "INFO"
    assert e.message == "hello"
    assert e.logger == "bbc_sim.test"


def test_capacity_evicts_oldest(handler):
    for i in range(12):
        _emit(handler, "DEBUG", f"msg{i}")
    assert len(handler.records) == 10
    assert handler.records[0].message == "msg2"
    assert handler.records[-1].message == "msg11"


def test_snapshot_no_filter(handler):
    _emit(handler, "INFO", "a")
    _emit(handler, "WARNING", "b")
    result = handler.snapshot()
    assert len(result) == 2


def test_snapshot_level_filter(handler):
    _emit(handler, "DEBUG", "d")
    _emit(handler, "INFO", "i")
    _emit(handler, "WARNING", "w")
    result = handler.snapshot(level="INFO")
    assert len(result) == 1
    assert result[0].level == "INFO"


def test_snapshot_since_filter(handler):
    now = time.time()
    _emit(handler, "INFO", "old", ts=now - 10)
    _emit(handler, "INFO", "new", ts=now)
    result = handler.snapshot(since=now - 5)
    assert len(result) == 1
    assert result[0].message == "new"


def test_snapshot_limit(handler):
    for i in range(5):
        _emit(handler, "INFO", f"msg{i}")
    result = handler.snapshot(limit=3)
    assert len(result) == 3
    # limit returns the last N entries
    assert result[-1].message == "msg4"


def test_snapshot_empty(handler):
    assert handler.snapshot() == []


@pytest.fixture
def _app_with_logs(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    handler = RingBufferLogHandler(capacity=100)
    status = StatusProvider(
        config=cfg,
        app=bapp,
        bound=False,
        get_manager=lambda: None,
        log_handler=handler,
    )
    client = TestClient(create_app(bapp, cfg, status=status))
    try:
        yield client, handler
    finally:
        bapp.close()


def test_logs_endpoint_empty(_app_with_logs):
    client, _ = _app_with_logs
    resp = client.get("/logs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_logs_endpoint_returns_entries(_app_with_logs):
    client, handler = _app_with_logs
    _emit(handler, "INFO", "test message")
    _emit(handler, "WARNING", "warn message")
    resp = client.get("/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["level"] in ("INFO", "WARNING")


def test_logs_endpoint_level_filter(_app_with_logs):
    client, handler = _app_with_logs
    _emit(handler, "DEBUG", "debug msg")
    _emit(handler, "ERROR", "error msg")
    resp = client.get("/logs?level=ERROR")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["level"] == "ERROR"


def test_logs_endpoint_limit(_app_with_logs):
    client, handler = _app_with_logs
    for i in range(10):
        _emit(handler, "INFO", f"msg{i}")
    resp = client.get("/logs?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_logs_endpoint_no_handler(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    client = TestClient(create_app(bapp, cfg))
    try:
        # no status provider → returns empty list (not 503)
        assert client.get("/logs").json() == []
    finally:
        bapp.close()
