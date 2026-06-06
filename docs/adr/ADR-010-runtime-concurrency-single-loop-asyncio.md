# ADR-010: ランタイム並行性モデル = single-loop asyncio

- **Date:** 2026-06-07
- **Status:** Accepted
- **原典:** [[ADR-009]]（bacpypes3=asyncio）/ operating-modes.md §2 / PR-NF-017

## Context

The simulator runs a BACnet server, a value simulation engine, scenario execution, and future southbound binding adapters. These components share the Core Object Model, including `presentValue`, `statusFlags`, `reliability`, and `outOfService`.

bacpypes3 is asyncio-based ([[ADR-009]]). If any handler blocks the event loop, BACnet service responses may stall, causing intermittent interoperability and CI failures — the exact flakiness the project Vision aims to eliminate.

A thread-based model would expose the shared state to update races: presentValue 更新競合 / Read 中の Write / COV 通知タイミング不整合 / CI でしか出ないフレーク。

## Decision

Use a **single asyncio event loop** as the runtime concurrency model.

- All core runtime components are implemented as async tasks: BACnet service stack, simulation engine, scenario runner, southbound adapters, and the CLI/test harness where applicable.
- The **Core Object Model is confined to the event loop** and must not be directly mutated from other threads.
- Blocking operations are prohibited in BACnet handlers, simulation tasks, scenario tasks, and async adapters.
- If a sync-only external SDK is unavoidable, it must be isolated using `run_in_executor` and communicate with the runtime through `asyncio.Queue` (or an equivalent event-loop-safe boundary). The executor side never mutates the Core Object Model directly:

```
Blocking Adapter → run_in_executor → Adapter Boundary → asyncio.Queue → Event Loop → Core Object Model
```

## Rationale

- Matches bacpypes3's native concurrency model.
- Keeps the Core Object Model single-threaded; no locks around BACnet object state.
- Reduces presentValue update races and CI flakiness.
- Simplifies COV and future event-notification behavior.
- Keeps "1 runtime instance = 1 B-BC" ([[ADR-002]]/[[ADR-008]]) conceptually simple.

## Consequences

**Positive:** no shared-state locking in normal runtime code; predictable update ordering; easier debugging; stable BACnet responses; clean integration with async MQTT (aiomqtt) and `grpc.aio`.

**Negative:** all adapters must be async or carefully wrapped; blocking libraries require explicit isolation; CPU-heavy work must stay out of the loop.

## Rules

- No blocking I/O in the event loop. Use `asyncio.sleep`, not `time.sleep`.
- No long CPU-bound work in BACnet handlers.
- Do not mutate the Core Object Model from executor threads.
- Use `asyncio.Queue` for cross-boundary messages.
- Use timeouts around external async calls; log slow callbacks / handler latency.

## Exception

A blocking southbound adapter may use `run_in_executor` **only if**: no async alternative exists; it is isolated behind an adapter boundary; it never directly mutates the Core Object Model; it reports updates back via a queue; and it has explicit timeout and cancellation behavior.
