"""Shared test fixtures."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_pointlist() -> Path:
    """Path to the 29-column SBCO sample point list."""
    return FIXTURES / "sample_pointlist.csv"


def free_udp_port() -> int:
    """Pick a free UDP port for loopback BACnet tests."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def free_port():
    """Return the free_udp_port helper (callable) for tests needing several ports."""
    return free_udp_port
