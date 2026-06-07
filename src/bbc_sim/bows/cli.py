"""BOWS CLI: `bbc-sim bows run`. Registered into the root Typer app."""

from __future__ import annotations

import typer

from bbc_sim.bows.models import BowsConfig
from bbc_sim.bows.runner import run as run_bows


def register(app: typer.Typer) -> None:
    bows_app = typer.Typer(
        help="BOWS connector — read a B-BC over BACnet and publish to Building OS",
        no_args_is_help=True,
    )

    @bows_app.command("run")
    def run(
        target: str = typer.Option(..., "--target", "-t", help="B-BC address host:port"),
        device_id: str = typer.Option(..., "--device-id", "-d", help="Building OS device id"),
        tenant: str = typer.Option("default", "--tenant", help="Building OS tenant"),
        transport: str = typer.Option(
            "memory",
            "--transport",
            help="transport URI (mqtt://host:port | amqps://host:port | memory)",
        ),
        interval: float = typer.Option(60.0, "--interval", help="poll interval seconds"),
        local: str | None = typer.Option(None, "--local", help="local BACnet bind host:port"),
    ) -> None:
        """Poll the B-BC and publish telemetry/{tenant}/{device_id} to Building OS."""
        config = BowsConfig(
            target=target,
            device_id=device_id,
            tenant=tenant,
            transport_uri=transport,
            interval=interval,
            local_address=local,
        )
        typer.secho(
            f"BOWS: {target} -> {transport} topic telemetry/{tenant}/{device_id} "
            f"(every {interval}s, Ctrl-C to stop)",
            fg=typer.colors.GREEN,
        )
        try:
            run_bows(config)
        except KeyboardInterrupt:  # pragma: no cover - interactive
            typer.echo("stopped")

    app.add_typer(bows_app, name="bows")
