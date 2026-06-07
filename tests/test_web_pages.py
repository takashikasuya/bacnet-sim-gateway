"""EP-007.6 — Web UI page rendering (PR-F-052, AC-15)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bbc_sim.observability.log_buffer import RingBufferLogHandler
from bbc_sim.rest.api import create_app
from bbc_sim.rest.reload import PointListReloader
from bbc_sim.rest.status import StatusProvider
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.simulator_runtime.runtime import Runtime
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


@pytest.fixture
def ui_client(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="bbc-ui", device_id=8001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    bapp = build_application(cfg, with_network=False)
    handler = RingBufferLogHandler()
    status = StatusProvider(
        config=cfg,
        app=bapp,
        bound=True,
        get_manager=lambda: None,
        log_handler=handler,
    )
    # minimal runtime stub for reloader
    runtime = Runtime.__new__(Runtime)
    runtime.config = cfg
    runtime.app = bapp
    runtime.engine = None
    runtime.manager = None
    reloader = PointListReloader(source_path=None, runtime=runtime)
    client = TestClient(
        create_app(bapp, cfg, status=status, reloader=reloader, ui_enabled=True),
        raise_server_exceptions=True,
    )
    try:
        yield client, cfg
    finally:
        bapp.close()


def _assert_html(resp, keyword: str | None = None) -> None:
    assert resp.status_code == 200
    ct = resp.headers.get("content-type", "")
    assert "text/html" in ct
    if keyword:
        assert keyword in resp.text


@pytest.mark.parametrize(
    "path,keyword",
    [
        ("/ui/", "Dashboard"),
        ("/ui/devices", "デバイス"),
        ("/ui/bindings", "バインディング"),
        ("/ui/status", "northbound"),
        ("/ui/logs", "ログ"),
        ("/ui/pointlist", "点リスト"),
        ("/ui/help", "ヘルプ"),
    ],
)
def test_page_returns_html(ui_client, path, keyword):
    client, _ = ui_client
    resp = client.get(path)
    _assert_html(resp, keyword)


def test_object_detail_page(ui_client):
    client, cfg = ui_client
    pid = cfg.objects[0].point_id
    resp = client.get(f"/ui/objects/{pid}")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert pid in resp.text


def test_object_detail_not_found(ui_client):
    client, _ = ui_client
    resp = client.get("/ui/objects/NONEXISTENT")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "partial,keyword",
    [
        ("/ui/partials/tiles", ""),
        ("/ui/partials/objects_table", "point_id"),
        ("/ui/partials/bindings_table", ""),
        ("/ui/partials/counters", ""),
        ("/ui/partials/logtail", ""),
    ],
)
def test_partials_return_html(ui_client, partial, keyword):
    client, _ = ui_client
    resp = client.get(partial)
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_dashboard_shows_bbc_and_device_id(ui_client):
    """Dashboard must show both bbc_id and device_id (ADR-003)."""
    client, cfg = ui_client
    resp = client.get("/ui/")
    assert "bbc-ui" in resp.text  # bbc_id
    assert "8001" in resp.text  # device_id


def test_pointlist_reload_post_returns_html(ui_client):
    client, _ = ui_client
    resp = client.post("/ui/pointlist/reload")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_context_help_partials(ui_client):
    client, _ = ui_client
    for page in ("dashboard", "devices", "bindings", "status", "logs", "pointlist"):
        resp = client.get(f"/ui/partials/help/{page}")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
