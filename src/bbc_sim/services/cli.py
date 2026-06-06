"""Client CLI commands (whois/read-property/...). Registered into the root Typer app."""

from __future__ import annotations

import asyncio

import typer

from bbc_sim.services import client

_TARGET = typer.Option(..., "--target", "-t", help="B-BC address host:port")
_LOCAL = typer.Option(None, "--local", "-l", help="local bind host:port (default ephemeral)")


def _local_or_ephemeral(local: str | None) -> str:
    return local or client.ephemeral_local()


def register(app: typer.Typer) -> None:
    @app.command("whois")
    def whois(
        target: str = _TARGET,
        local: str | None = _LOCAL,
        low: int | None = typer.Option(None, "--low"),
        high: int | None = typer.Option(None, "--high"),
    ) -> None:
        """Discover devices via Who-Is / I-Am."""

        async def _run() -> None:
            async with client.client_app(_local_or_ephemeral(local)) as app_:
                found = await client.whois(app_, target, low, high)
                for dev_id, addr in found:
                    typer.echo(f"device {dev_id} @ {addr}")
                if not found:
                    typer.secho("no devices found", fg=typer.colors.YELLOW)

        asyncio.run(_run())

    @app.command("read-property")
    def read_property(
        objid: str = typer.Argument(..., help="e.g. analog-input,1001"),
        prop: str = typer.Argument("present-value"),
        target: str = _TARGET,
        local: str | None = _LOCAL,
    ) -> None:
        """ReadProperty a single property."""

        async def _run() -> None:
            async with client.client_app(_local_or_ephemeral(local)) as app_:
                value = await client.read_property(app_, target, objid, prop)
                typer.echo(f"{objid} {prop} = {value}")

        asyncio.run(_run())

    @app.command("read-property-multiple")
    def read_property_multiple(
        objid: str = typer.Argument(...),
        props: list[str] = typer.Argument(None),
        target: str = _TARGET,
        local: str | None = _LOCAL,
    ) -> None:
        """ReadPropertyMultiple for one object."""

        async def _run() -> None:
            wanted = props or ["present-value", "units", "object-name"]
            async with client.client_app(_local_or_ephemeral(local)) as app_:
                results = await client.read_property_multiple(app_, target, objid, wanted)
                for _oid, prop, _idx, value in results:
                    typer.echo(f"{prop} = {value}")

        asyncio.run(_run())

    @app.command("write-property")
    def write_property(
        objid: str = typer.Argument(...),
        value: str = typer.Argument(..., help="value (numeric or text)"),
        prop: str = typer.Argument("present-value"),
        target: str = _TARGET,
        local: str | None = _LOCAL,
    ) -> None:
        """WriteProperty (writable objects only)."""

        async def _run() -> None:
            async with client.client_app(_local_or_ephemeral(local)) as app_:
                await client.write_property(app_, target, objid, _coerce(value), prop)
                typer.secho(f"wrote {objid} {prop} = {value}", fg=typer.colors.GREEN)

        asyncio.run(_run())

    @app.command("list-objects")
    def list_objects(
        target: str = _TARGET,
        local: str | None = _LOCAL,
    ) -> None:
        """List the object identifiers of the target B-BC."""

        async def _run() -> None:
            async with client.client_app(_local_or_ephemeral(local)) as app_:
                for obj in await client.list_objects(app_, target):
                    typer.echo(obj)

        asyncio.run(_run())


def _coerce(value: str) -> object:
    """Best-effort coerce a CLI string to int/float, else keep the string."""
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            continue
    return value
