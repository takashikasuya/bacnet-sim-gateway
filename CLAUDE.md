# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read AGENTS.md first

`AGENTS.md` is the operating contract for this repo (workflow, coding rules, scope control, safety rules). It is intentionally short — read it before doing anything. This file covers only what AGENTS.md does not: the document architecture and the project's current stage.

## Current stage: docs-only

There is **no code, build system, or tests yet**. This repository currently holds the design documents for the *SBCO BACnet B-BC Simulator / Gateway*. Do not invent build/lint/test commands — none exist. The first implementation work is `EP-001` (MVP-1) under `docs/backlog/epic/`.

When code lands, the intended shape (per `docs/specs/requirements-definition-v1.1.md` §20) is: Python 3.12 + `uv`, a `bbc-sim` CLI, `src/` (`yaml_generator`, `simulator_runtime`, `bacnet_objects`, `services`), `config/` (`simulator.yaml`, `mapping.yaml`), and `docker/`. BACnet library is still undecided (bacpypes3 vs BAC0 — see `docs/memory/decisions.md`).

**Runtime target:** native execution on Raspberry Pi (ARM/ARM64) is first-class; Docker is optional (`ADR-008`). Do not hard-depend on Docker, and ensure dependencies build on ARM.

## Document architecture (the big picture)

Docs are organized as layers, each answering a different question. **Do not mix layers.** Reading order:

```
Vision → Memory → ADR → Backlog → Spec → Issue
```

| Layer | Path | Answers | Authority |
|-------|------|---------|-----------|
| Vision | `docs/vision/vision.md` | なぜ作るか | — |
| Memory | `docs/memory/` | 知っておくべきこと（architecture, decisions index, pitfalls, BACnet domain） | — |
| ADR | `docs/adr/ADR-001..008` | なぜその設計か | **設計判断の正** |
| Backlog | `docs/backlog/` | 何を作るか（`PRD.md` ＝製品要求、`epic/EP-001..006` ＝ MVP 別） | **製品要求の正** |
| Spec | `docs/specs/` | どう振る舞うか | **設計の正** |

Two source documents are the detailed sources of truth; the layer files navigate to them without duplicating:
- `docs/backlog/PRD.md` — product requirements (PR-F-*, PR-NF-*, AC-*, MVP phases)
- `docs/specs/requirements-definition-v1.1.md` — behavior/CLI/data spec. The 7 downstream design docs in `docs/specs/` (numbering, mapping, southbound-binding, operating-modes, pics-bibbs, service-priority, compose) are **v0.1 drafts** carrying status markers: ✅ confirmed / 🔧 tentative / ❓ undecided. Open ❓ items are aggregated in `docs/memory/decisions.md` — check there before deciding anything that looks open.

Requirement IDs (`PR-F-005`), acceptance IDs (`AC-6`), test scenarios (`TS-01`), and ADRs (`ADR-005`) are the cross-referencing vocabulary used throughout. When breaking an epic into issues, cite these in `.github/ISSUE_TEMPLATE/feature.md`.

## Non-negotiable invariants

These are easy to get backwards and are enforced across the design. Violating them is a design bug, not a style choice:

- **Northbound = BACnet/IP; Southbound = MQTT/ZeroMQ/WoT/gRPC.** MQTT is *not* a north/output interface of the B-BC (corrected in PRD v1.2 — see `ADR-005`). The product exposes BACnet upward; upper systems (Building OS) ingest it via a connection gateway (Hono). **Note (EP-008):** the **BOWS** connector (`ADR-014`) is a *separate downstream consumer* that reads the B-BC over BACnet and publishes to Building OS via MQTT/AMQP — that MQTT is the connector→Building OS link, one layer above the B-BC, and does **not** change this invariant.
- **`gateway_id` ≠ `bbc_id`.** `gateway_id` is the upstream gateway identifier and must never be used as the B-BC id (`ADR-003`).
- **1 Docker container = 1 B-BC** (`ADR-002`).
- **SBCO point list is the only input; YAML is the shared intermediate model** across all modes (`ADR-001`, `ADR-004`).

## Memory note

Project memory at `~/.claude/projects/-home-takashi-projects-gutp-bacnet-sim-gateway/memory/` records the same invariants and the doc layout. The user is methodical about the layered doc model and keeping AGENTS.md lean (≤200 lines) — keep architecture/decisions/requirements in their own layers, not in AGENTS.md.
