"""Runtime CLI command (bbc-sim run). Registered into the root Typer app."""

from __future__ import annotations

from pathlib import Path

import typer

from bbc_sim.models import RuntimeMode
from bbc_sim.simulator_runtime.app import run
from bbc_sim.yaml_generator.yaml_io import load_config, validate_yaml


def register(app: typer.Typer) -> None:
    @app.command("run")
    def run_cmd(
        config: Path = typer.Option(..., "--config", "-c", help="simulator.yaml"),
        mode: RuntimeMode | None = typer.Option(
            None, "--mode", help="override runtime mode (simulator/gateway/combined)"
        ),
        transport: str | None = typer.Option(
            None, "--transport", help="southbound transport URI (mqtt://host:port, zmq://...)"
        ),
    ) -> None:
        """Start the virtual B-BC and serve it on BACnet/IP (northbound)."""
        errors = validate_yaml(config)
        if errors:
            for e in errors:
                typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        cfg = load_config(config)
        if mode is not None:
            cfg.mode = mode
        typer.secho(f"starting B-BC from {config} (Ctrl-C to stop)", fg=typer.colors.GREEN)
        try:
            run(cfg, transport_uri=transport)
        except KeyboardInterrupt:  # pragma: no cover - interactive
            typer.echo("stopped")
