# Troubleshooting

> First-user oriented. For internal/known design failure modes see
> [`memory/pitfalls.md`](memory/pitfalls.md).

## Install / run

**`bbc-sim: command not found`**
Run via uv: `uv run bbc-sim --help`. Make sure `uv sync` completed without errors.

**Import error for `grpc` / `qpid_proton`**
These are optional extras and lazy-imported. Install what you need:
`uv sync --extra grpc` or `uv sync --extra amqp`.

**`generate-yaml` complains about missing columns**
The input must be an SBCO-style point list with the required columns. Validate
the produced model with `uv run bbc-sim validate -c <file>`.
Use `--point-filter all` to include rows with no `device_id_bacnet`.

## BACnet / network

**A BACnet client (YABE etc.) can't see the device**
- BACnet/IP is **UDP/47808**. Confirm the port is open and not already bound by
  another BACnet app on the host.
- `bind_address` in `simulator.yaml` must be reachable from the client. `0.0.0.0`
  binds all interfaces; a specific IP restricts to one.
- Client and simulator must be on the **same broadcast domain** for Who-Is/I-Am,
  or use BBMD / Foreign Device Registration across subnets.
- A host firewall (ufw/iptables, Windows Defender) may block UDP/47808.

**Two BACnet apps on one host conflict**
Only one process can bind UDP/47808 per interface. Stop the other, or bind to a
different interface/port.

**`WriteProperty` is rejected**
Only points marked `writable` accept writes. Check the point's `writable` flag in
the point list / YAML.

## Docker

- BACnet/IP needs `network_mode: host` (already set in `docker/docker-compose.yml`).
  Host networking is **Linux-only**; on **macOS/Windows** Docker Desktop does not
  pass host UDP broadcast through, so BACnet discovery typically won't work —
  prefer native execution there.
- On Linux, ensure no host process already holds UDP/47808.

## Tests

- Default `pytest` skips `@pytest.mark.integration`. Integration tests need an
  external broker — start Mosquitto (see `CONTRIBUTING.md`) and run
  `uv run pytest -m integration`.
