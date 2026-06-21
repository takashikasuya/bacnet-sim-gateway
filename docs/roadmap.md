# Roadmap

> Outward-facing summary of what works today and what's planned. The detailed
> product requirements live in [`backlog/PRD.md`](backlog/PRD.md); per-MVP epics
> in [`backlog/epic/`](backlog/epic). Status is also tracked in GitHub issues.

## Status: `v0.1.0-alpha`

Experimental. Config schema, CLI, and APIs may change during the `0.x` series.
Not a production controller; not BTL-certified.

## What works today

- **CSV → YAML**: generate a `simulator.yaml` from an SBCO point list
  (aggregated / multi-device mapping, ADR-011); `validate` the model.
- **Simulator mode**: virtual BACnet B-BC over BACnet/IP — Who-Is/I-Am,
  ReadProperty, ReadPropertyMultiple, WriteProperty (writable points), COV,
  dynamic binding.
- **Gateway mode**: southbound **MQTT** and **ZeroMQ** data → BACnet objects
  northbound (in-memory `memory://` transport for CI).
- **Value generation & fault injection**: random_walk / sinusoidal / replay /
  scenario; comm-loss / freeze / abnormal / OutOfService / Fault.
- **Semantic tags**: deterministic Brick→Haystack tag generation; `search_tags`.
- **Standard-artifact export**: `bbc-sim export -f pics|ede|ieiej|jsonld|wot`.
- **Admin UI**: status, value/fault control, point-list reload, logs (localhost,
  no auth — see security notes).
- **BOWS connector** (EP-008): reads the B-BC over BACnet and publishes to
  Building OS (`bacnet-device-message`) via MQTT/AMQP; gRPC downlink control.
- **Runtime**: Raspberry Pi (ARM/ARM64) native first-class; Docker optional.

## Planned / future (MVP-3, `docs/backlog/epic/EP-006`)

- **Future object types** (#28): Schedule / Trend Log / Notification Class /
  Calendar / Accumulator (PR-F-070).
- **WoT southbound binding** (#30, PR-F-086).
- **BACnet/SC** (partial) + **BTL conformance support** (#31, PR-F-071).
- **Semantic model output**: full REC / QUDT (Brick JSON-LD and WoT TD already
  shipped).

## Distribution

- Today: source + GitHub Release; optional Docker image.
- PyPI publishing is **not** an immediate priority during `0.x`.

## Not goals

- Faithful reproduction of real equipment control logic.
- Obtaining formal BTL certification (the simulator only *supports* conformance
  work).
