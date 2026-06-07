"""EP-001.6/.8 — run + client CLI registration, validation, and e2e serving."""

from __future__ import annotations

import asyncio
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from bbc_sim.cli import app
from bbc_sim.services.client import build_client, read_property, whois
from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list
from bbc_sim.yaml_generator.yaml_io import dump_config

runner = CliRunner()

EXPECTED_COMMANDS = (
    "generate-yaml",
    "validate",
    "validate-point-list",
    "run",
    "whois",
    "read-property",
    "read-property-multiple",
    "write-property",
    "list-objects",
)


def test_all_commands_registered():
    help_text = runner.invoke(app, ["--help"]).output
    for cmd in EXPECTED_COMMANDS:
        assert cmd in help_text


def test_run_rejects_invalid_config(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("bbc: {}\n", encoding="utf-8")
    result = runner.invoke(app, ["run", "-c", str(bad)])
    assert result.exit_code == 1


@pytest.fixture
def served_config(sample_pointlist, tmp_path, free_port):
    points = read_point_list(sample_pointlist)
    port = free_port()
    cfg, _ = generate_config(points, bbc_id="bbc-local-001", device_id=1001)
    cfg.network.bind_address = "127.0.0.1"
    cfg.network.port = port
    path = tmp_path / "simulator.yaml"
    dump_config(cfg, path)
    return path, port


def test_run_cli_serves_bbc(served_config, free_port):
    # Start `bbc-sim run` as a real subprocess and talk to it with the client.
    path, port = served_config
    proc = subprocess.Popen(
        [sys.executable, "-m", "bbc_sim.cli", "run", "-c", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:

        async def _probe() -> int | None:
            client = build_client(f"127.0.0.1:{free_port()}")
            try:
                for _ in range(20):  # up to ~6s for the datalink to come up
                    found = await whois(client, f"127.0.0.1:{port}")
                    if found:
                        name = await read_property(
                            client, f"127.0.0.1:{port}", "analog-input,1001", "object-name"
                        )
                        assert name == "Supply Air Temperature"
                        return found[0][0]
                    await asyncio.sleep(0.3)
                return None
            finally:
                client.close()

        device_id = asyncio.run(_probe())
        assert device_id == 1001, "B-BC not discovered via CLI-started server"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
