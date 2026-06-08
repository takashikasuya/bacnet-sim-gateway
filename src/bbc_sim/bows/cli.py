"""BOWS CLI: `bbc-sim bows run`. Registered into the root Typer app."""

from __future__ import annotations

import typer

from bbc_sim.bows.downlink.client import run as run_egress
from bbc_sim.bows.downlink.models import EgressConfig
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
            "memory", "--transport", help="transport URI (mqtt://host:port | memory)"
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

    @bows_app.command("egress")
    def egress(
        endpoint: str = typer.Option(..., "--endpoint", help="Building OS GatewayEgress host:port"),
        gateway_id: str = typer.Option(..., "--gateway-id", "-g", help="upstream gateway id"),
        target: str = typer.Option(..., "--target", "-t", help="B-BC address host:port to write"),
        device: int | None = typer.Option(
            None, "--device", help="target B-BC device instance; rejects commands for others"
        ),
        local: str | None = typer.Option(None, "--local", help="local BACnet bind host:port"),
        insecure: bool = typer.Option(False, "--insecure", help="disable mTLS (dev/loopback only)"),
    ) -> None:
        """Subscribe Building OS GatewayEgress (gRPC) and apply ControlCommands as WriteProperty.

        Needs the optional `grpc` extra: uv sync --extra grpc (ADR-017).
        """
        config = EgressConfig(
            endpoint=endpoint,
            gateway_id=gateway_id,
            target=target,
            device_instance=device,
            local_address=local,
            tls=not insecure,
        )
        scheme = "insecure" if insecure else "mTLS"
        typer.secho(
            f"BOWS egress: {endpoint} ({scheme}) gateway={gateway_id} -> WriteProperty {target} "
            "(Ctrl-C to stop)",
            fg=typer.colors.GREEN,
        )
        try:
            run_egress(config)
        except KeyboardInterrupt:  # pragma: no cover - interactive
            typer.echo("stopped")

    app.add_typer(bows_app, name="bows")
