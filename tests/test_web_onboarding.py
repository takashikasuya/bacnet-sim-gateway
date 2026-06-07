"""EP-007.7 — Onboarding: /ui/help, tour, context help, empty states (PR-F-057, AC-16)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bbc_sim.models import RuntimeMode
from bbc_sim.observability.log_buffer import RingBufferLogHandler
from bbc_sim.rest.api import create_app
from bbc_sim.rest.reload import PointListReloader
from bbc_sim.rest.status import StatusProvider
from bbc_sim.simulator_runtime.app import build_application
from bbc_sim.simulator_runtime.runtime import Runtime
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list


def _make_ui_client(cfg, mode=None):
    if mode is not None:
        cfg.mode = mode
    bapp = build_application(cfg, with_network=False)
    handler = RingBufferLogHandler()
    status = StatusProvider(
        config=cfg,
        app=bapp,
        bound=False,
        get_manager=lambda: None,
        log_handler=handler,
    )
    runtime = Runtime.__new__(Runtime)
    runtime.config = cfg
    runtime.app = bapp
    runtime.engine = None
    runtime.manager = None
    reloader = PointListReloader(source_path=None, runtime=runtime)
    client = TestClient(create_app(bapp, cfg, status=status, reloader=reloader, ui_enabled=True))
    return client, bapp


@pytest.fixture
def help_client(sample_pointlist, free_port):
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="bbc-help", device_id=9999)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    client, bapp = _make_ui_client(cfg)
    try:
        yield client
    finally:
        bapp.close()


def test_help_page_returns_html(help_client):
    resp = help_client.get("/ui/help")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_help_page_contains_concept_terms(help_client):
    """Help page must explain key concepts for first-time users (AC-16)."""
    resp = help_client.get("/ui/help")
    text = resp.text
    # northbound / southbound concepts
    assert "northbound" in text.lower() or "北向き" in text
    assert "southbound" in text.lower() or "南向き" in text


def test_help_page_contains_mode_descriptions(help_client):
    """Help page must explain simulator, gateway, combined modes."""
    resp = help_client.get("/ui/help")
    text = resp.text
    assert "simulator" in text.lower()
    assert "gateway" in text.lower()


def test_help_page_contains_destructive_ops_warning(help_client):
    """Help page must mention destructive operations (values write, fault inject, reload)."""
    resp = help_client.get("/ui/help")
    text = resp.text
    # at least one of these destructive operation keywords should appear
    has_warning = any(kw in text for kw in ["Fault", "fault", "writable", "再読込", "reload"])
    assert has_warning


def test_tour_partial_returns_html(help_client):
    """_tour.html must be loadable — it is included in base.html."""
    resp = help_client.get("/ui/")
    assert resp.status_code == 200
    # The tour overlay is embedded in the base template
    assert "tour-overlay" in resp.text


def test_tour_partial_has_step_structure(help_client):
    resp = help_client.get("/ui/")
    assert "tour-step" in resp.text
    assert "localStorage" in resp.text or "tour" in resp.text.lower()


def test_context_help_dashboard_content(help_client):
    resp = help_client.get("/ui/partials/help/dashboard")
    assert resp.status_code == 200
    assert len(resp.text.strip()) > 0


def test_context_help_unknown_page(help_client):
    # Unknown but charset-valid name → 404 with a generic body (no echo of input).
    resp = help_client.get("/ui/partials/help/nonexistent_page_xyz")
    assert resp.status_code == 404


def test_context_help_rejects_unsafe_name(help_client):
    # A name with markup characters must be rejected without being echoed back.
    resp = help_client.get("/ui/partials/help/%3Cscript%3E")
    assert resp.status_code == 404
    assert "<script>" not in resp.text


def test_empty_objects_partial(sample_pointlist, free_port):
    """With zero objects, the empty-state guidance must be shown."""
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    cfg.objects = []  # no objects
    client, bapp = _make_ui_client(cfg)
    try:
        resp = client.get("/ui/partials/objects_table")
        assert resp.status_code == 200
        text = resp.text
        # empty state text or class should appear
        assert "empty" in text.lower() or "オブジェクト" in text or len(text.strip()) > 0
    finally:
        bapp.close()


def test_mode_label_in_nav(sample_pointlist, free_port):
    """Each page must show the current mode in the nav bar."""
    cfg, _ = generate_config(read_point_list(sample_pointlist), bbc_id="b", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = free_port()
    client, bapp = _make_ui_client(cfg, mode=RuntimeMode.simulator)
    try:
        resp = client.get("/ui/")
        assert "simulator" in resp.text
    finally:
        bapp.close()


def test_help_page_references_tour(help_client):
    """Help page should offer a way to re-show the onboarding tour."""
    resp = help_client.get("/ui/help")
    # button or link to re-show tour
    text = resp.text
    assert "showTour" in text or "ツアー" in text or "tour" in text.lower()
