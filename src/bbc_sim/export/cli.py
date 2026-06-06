"""Export CLI command (bbc-sim export). Registered into the root Typer app."""

from __future__ import annotations

from pathlib import Path

import typer

from bbc_sim.export.artifacts import FORMATS, export
from bbc_sim.yaml_generator.yaml_io import load_config


def register(app: typer.Typer) -> None:
    @app.command("export")
    def export_cmd(
        fmt: str = typer.Option(..., "--format", "-f", help=f"one of: {', '.join(FORMATS)}"),
        config: Path = typer.Option(..., "--config", "-c", help="simulator.yaml"),
        output: Path | None = typer.Option(None, "--output", "-o", help="output file"),
    ) -> None:
        """Export a standards artifact / semantic model (EDE, IEIEJ, PICS, JSON-LD, WoT)."""
        if fmt not in FORMATS:
            typer.secho(f"error: unknown format {fmt!r}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        text = export(load_config(config), fmt)
        if output is not None:
            output.write_text(text, encoding="utf-8")
            typer.secho(f"wrote {output}", fg=typer.colors.GREEN)
        else:
            typer.echo(text)
