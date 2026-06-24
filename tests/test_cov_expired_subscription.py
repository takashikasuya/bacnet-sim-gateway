"""Regression test: no ValueError when COV cancel_handle has just elapsed.

Under heavy northbound load the asyncio event loop can be delayed enough that a
COV subscription's cancel_handle.when() < current_time before send_cov_notifications
runs.  The original bacpypes3 code produces a negative time_remaining which
Unsigned.cast() rejects.  Our monkey-patch in builder.py (applied at import time)
clamps the value to max(1, ...).
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from bacpypes3.local.cov import GenericCriteria
from bacpypes3.local.device import DeviceObject

# builder must be imported before bacpypes3.local.cov so the monkey-patch is
# applied before GenericCriteria is used in these tests.
import bbc_sim.bacnet_objects.builder  # noqa: F401


def _make_detection(sub, *, expired: bool):
    """Build a minimal GenericCriteria instance with one mock subscription."""
    loop = asyncio.get_event_loop()
    sub.cancel_handle = MagicMock()
    sub.cancel_handle.when.return_value = loop.time() - 30.0 if expired else loop.time() + 60.0
    sub.confirmed = False
    sub.client_addr = "127.0.0.1"
    sub.proc_id = 42
    sub.obj_id = ("analog-input", 1)

    dev_mock = MagicMock(spec=DeviceObject)
    dev_mock.objectIdentifier = ("device", 1)

    obj_mock = MagicMock()
    obj_mock._app.objectIdentifier = {("device", 1): dev_mock}
    obj_mock._app.cov_notification = MagicMock()

    detection = object.__new__(GenericCriteria)
    detection.obj = obj_mock
    detection.cov_subscriptions = [sub]
    detection.properties_reported = []
    return detection, obj_mock


@pytest.mark.asyncio
async def test_no_crash_when_cancel_handle_already_elapsed():
    """Expired cancel_handle must clamp time_remaining to 1, not crash."""
    sub = MagicMock()
    detection, obj_mock = _make_detection(sub, expired=True)

    # Before the patch this raised ValueError("unsigned").
    detection.send_cov_notifications(sub)

    obj_mock._app.cov_notification.assert_called_once()
    _cov, request = obj_mock._app.cov_notification.call_args[0]
    assert request.timeRemaining == 1  # exact clamp value, not just "non-negative"


@pytest.mark.asyncio
async def test_permanent_subscription_sends_time_remaining_zero():
    """cancel_handle=None (lifetime=0, indefinite sub) must produce timeRemaining=0."""
    sub = MagicMock()
    dev_mock = MagicMock(spec=DeviceObject)
    dev_mock.objectIdentifier = ("device", 1)

    obj_mock = MagicMock()
    obj_mock._app.objectIdentifier = {("device", 1): dev_mock}
    obj_mock._app.cov_notification = MagicMock()

    detection = object.__new__(GenericCriteria)
    detection.obj = obj_mock
    detection.cov_subscriptions = [sub]
    detection.properties_reported = []

    sub.cancel_handle = None  # permanent / lifetime=0
    sub.confirmed = False
    sub.client_addr = "127.0.0.1"
    sub.proc_id = 99
    sub.obj_id = ("binary-input", 1)

    detection.send_cov_notifications(sub)

    obj_mock._app.cov_notification.assert_called_once()
    _cov, request = obj_mock._app.cov_notification.call_args[0]
    assert request.timeRemaining == 0
