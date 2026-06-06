# ADR-013: Southbound transport abstraction

**Status:** Accepted  **Date:** 2026-06-07  **Origin:** EP-002 (PR-NF-015)

## Context

Gateway/Combined modes bind BACnet objects to southbound protocols (MQTT/ZeroMQ/WoT/gRPC, ADR-005). These protocols differ in connection model and payload, but the *binding semantics* are identical: telemetry south→`presentValue`, command north `WriteProperty`→south (southbound-binding.md §1.1). We also need a self-contained test/CI path without external brokers.

## Decision

Introduce a protocol-independent **`Transport`** Protocol (`start/stop/subscribe/publish`) that the binding logic (`SouthboundManager`) depends on. Concrete transports implement it:

- **`InMemoryTransport`** — in-process pub/sub fake; the default for tests and CI.
- **`MqttTransport`** (paho-mqtt), **`ZmqTransport`** (pyzmq) — real network I/O, exercised under the `integration` pytest marker.
- A `make_transport(uri)` factory selects by URI scheme (`memory`, `mqtt://`, `zmq://`).

Value normalization (scale/offset/type/enum) lives in a separate `mapping` module so it is shared across transports. Channel/topic names are derived `local_id`-first (PR-F-090).

## Rationale

- One tested binding core; protocols become thin adapters → low marginal cost per protocol.
- CI stays green and hermetic via `InMemoryTransport`; real brokers are opt-in.
- Keeps the Core Object Model event-loop-confined (ADR-010): threaded transport callbacks (paho) are marshalled back with `run_coroutine_threadsafe`.

## Consequences

- New protocols (WoT, full gRPC) implement `Transport` only; gRPC is deferred (EP-006).
- Binding configuration is per-object (`binding:` in simulator.yaml), at most one per object.
- The abstraction does not model protocol-specific QoS/retain/auth yet (deferred; tracked in decisions.md).
