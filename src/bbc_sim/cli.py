"""bbc-sim command line interface (requirements §15).

Generation/validation commands are implemented here; runtime and client commands
are added by simulator_runtime and services.
"""

from __future__ import annotations

from pathlib import Path

import typer

from bbc_sim.models import DeviceMappingMode, PointFilter
from bbc_sim.yaml_generator.generator import generate_config, generate_multi_device_config
from bbc_sim.yaml_generator.pointlist import read_point_list, validate_point_list
from bbc_sim.yaml_generator.yaml_io import (
    dump_config,
    dump_multi_device_config,
    validate_config,
    validate_multi_device_config,
    validate_yaml,
)

app = typer.Typer(help="SBCO BACnet B-BC Simulator / Gateway", no_args_is_help=True)


@app.command("generate-yaml")
def generate_yaml(
    input: Path = typer.Option(..., "--input", "-i", help="SBCO point list CSV"),
    output: Path = typer.Option(..., "--output", "-o", help="simulator.yaml output"),
    bbc_id: str = typer.Option("bbc-local-001", "--bbc-id", help="B-BC id (NOT gateway_id)"),
    bacnet_device_id: int = typer.Option(1001, "--bacnet-device-id"),
    point_filter: PointFilter = typer.Option(
        PointFilter.bacnet,
        "--point-filter",
        help="'bacnet' (default): skip rows with no device_id_bacnet; 'all': include every row",
    ),
    device_mapping: DeviceMappingMode = typer.Option(
        DeviceMappingMode.aggregated,
        "--device-mapping",
        help=(
            "'aggregated' (default): all points into one BACnet Device; "
            "'multi-device': one Device per device_id_bacnet (ADR-011)"
        ),
    ),
    default_update_mode: str | None = typer.Option(
        None,
        "--default-update-mode",
        help=(
            "Apply an update mode to every object "
            "(random_walk / sinusoidal / replay / scenario). Omit to leave values static."
        ),
    ),
) -> None:
    """Generate simulator.yaml from an SBCO point list (ADR-011)."""
    points = read_point_list(input)
    if point_filter == PointFilter.bacnet:
        before = len(points)
        points = [p for p in points if p.device_id_bacnet]
        skipped = before - len(points)
        if skipped:
            typer.echo(
                f"skipped {skipped} point(s) with no device_id_bacnet (--point-filter bacnet)"
            )

    if device_mapping == DeviceMappingMode.multi_device:
        multi_config, warnings = generate_multi_device_config(
            points,
            base_bbc_id=bbc_id,
            base_device_id=bacnet_device_id,
            default_update_mode=default_update_mode,
        )
        for w in warnings:
            typer.secho(f"warning: {w}", fg=typer.colors.YELLOW, err=True)
        errors = validate_multi_device_config(multi_config)
        if errors:
            for e in errors:
                typer.secho(f"error: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        dump_multi_device_config(multi_config, output)
        total = sum(len(d.objects) for d in multi_config.devices)
        typer.echo(f"wrote {output} ({len(multi_config.devices)} devices, {total} objects)")
        return

    config, warnings = generate_config(
        points,
        bbc_id=bbc_id,
        device_id=bacnet_device_id,
        default_update_mode=default_update_mode,
    )
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


# Runtime, client, export, and BOWS commands are registered by their modules.
from bbc_sim.bows.cli import register as _register_bows  # noqa: E402
from bbc_sim.export.cli import register as _register_export  # noqa: E402
from bbc_sim.services.cli import register as _register_client  # noqa: E402
from bbc_sim.simulator_runtime.cli import register as _register_runtime  # noqa: E402

_register_runtime(app)
_register_client(app)
_register_export(app)
_register_bows(app)


if __name__ == "__main__":
    app()
