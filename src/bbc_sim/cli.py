"""bbc-sim command line interface (requirements §15).

Generation/validation commands are implemented here; runtime and client commands
are added by simulator_runtime and services.
"""

from __future__ import annotations

from pathlib import Path

import typer

from bbc_sim.yaml_generator.generator import generate_config
from bbc_sim.yaml_generator.pointlist import read_point_list, validate_point_list
from bbc_sim.yaml_generator.yaml_io import dump_config, validate_config, validate_yaml

app = typer.Typer(help="SBCO BACnet B-BC Simulator / Gateway", no_args_is_help=True)


@app.command("generate-yaml")
def generate_yaml(
    input: Path = typer.Option(..., "--input", "-i", help="SBCO point list CSV"),
    output: Path = typer.Option(..., "--output", "-o", help="simulator.yaml output"),
    bbc_id: str = typer.Option("bbc-local-001", "--bbc-id", help="B-BC id (NOT gateway_id)"),
    bacnet_device_id: int = typer.Option(1001, "--bacnet-device-id"),
) -> None:
    """Generate simulator.yaml from an SBCO point list (aggregated, ADR-011)."""
    points = read_point_list(input)
    config, warnings = generate_config(points, bbc_id=bbc_id, device_id=bacnet_device_id)
    # Inference notes are warnings; structural validation failures must fail the command
    # so automation never treats an unusable simulator.yaml as a success.
    for w in warnings:
        typer.secho(f"warning: {w}", fg=typer.colors.YELLOW, err=True)
    errors = validate_config(config)
    if errors:
        for e in errors:
            typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    dump_config(config, output)
    typer.echo(f"wrote {output} ({len(config.objects)} objects)")


@app.command("validate")
def validate(
    config: Path = typer.Option(..., "--config", "-c", help="simulator.yaml"),
) -> None:
    """Validate a simulator.yaml file."""
    errors = validate_yaml(config)
    _report(errors, ok=f"{config} is valid")


@app.command("validate-point-list")
def validate_pointlist_cmd(
    input: Path = typer.Option(..., "--input", "-i", help="SBCO point list CSV"),
) -> None:
    """Validate an SBCO point list CSV."""
    errors = validate_point_list(input)
    _report(errors, ok=f"{input} is valid")


def _report(errors: list[str], *, ok: str) -> None:
    if errors:
        for e in errors:
            typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    typer.secho(ok, fg=typer.colors.GREEN)


# Runtime, client, and export commands are registered by their modules.
from bbc_sim.export.cli import register as _register_export  # noqa: E402
from bbc_sim.services.cli import register as _register_client  # noqa: E402
from bbc_sim.simulator_runtime.cli import register as _register_runtime  # noqa: E402

_register_runtime(app)
_register_client(app)
_register_export(app)


if __name__ == "__main__":
    app()
