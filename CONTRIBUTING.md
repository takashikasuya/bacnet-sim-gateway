# Contributing to bbc-sim

Thanks for your interest! `bbc-sim` is a SBCO point-list driven BACnet/IP B-BC
simulator and gateway. This guide covers how to set up, test, and submit changes.
It is the human-contributor counterpart to [`AGENTS.md`](AGENTS.md) (the operating
contract for AI agents working in this repo) — read `AGENTS.md` too if you want
the full coding rules and invariants.

> 日本語の方が読みやすい方へ: 各節に日本語の補足を添えています。

## Project status

Experimental, pre-1.0 (`v0.1.x-alpha`). Config schema, CLI, and APIs may change
during the `0.x` series. Not a production controller; not BTL-certified.

## Prerequisites

- **Python 3.12** (the only supported version; CI runs 3.12)
- [**uv**](https://docs.astral.sh/uv/) for environment and dependency management
- Optional: Docker (for the integration test broker and container runs)

## Setup

```bash
uv sync                      # install runtime + dev dependencies
uv run bbc-sim --help        # smoke test the CLI
```

Optional extras (kept out of the base install on purpose):

```bash
uv sync --extra amqp         # BOWS AMQP transport
uv sync --extra grpc         # BOWS gRPC downlink
```

## Quality gates (run before every PR)

```bash
uv run ruff check            # lint
uv run ruff format --check   # formatting
uv run mypy                  # type check
uv run pytest --cov=src/bbc_sim   # unit + loopback tests
```

Integration tests require external services (e.g. Mosquitto) and are skipped by
default. To run them:

```bash
docker run -d --name mosquitto -p 127.0.0.1:1883:1883 \
  -v "$PWD/docker/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro" \
  eclipse-mosquitto:2
uv run pytest -m integration
```

A PR is **Done** when: the relevant acceptance criteria are met, new/changed
tests pass, existing tests still pass, code is typed and ruff/mypy clean, and the
change stays in scope.

## Development workflow

- **Test-driven**: write a failing test first (cite `TS-*` / `AC-*` where
  relevant), make it pass with the minimal change, then refactor.
- **Branching**: never commit directly to `main`. Work on a topic branch and open
  a PR. See [`docs/development-workflow.md`](docs/development-workflow.md).
- **Keep invariants** (these are design bugs if violated):
  - Northbound = BACnet/IP, Southbound = MQTT/ZeroMQ/WoT/gRPC (ADR-005)
  - `gateway_id` ≠ `bbc_id` (ADR-003)
  - 1 container = 1 B-BC (ADR-002)
  - SBCO point list is the only input; YAML is the shared intermediate model
    (ADR-001/004)
- **Commit messages**: include the issue/epic reference (`#123`, `EP-001`) and a
  concise, imperative subject.

## Filing issues

- **Bug report** / **Feature request** templates are provided when you open an
  issue. For BACnet bugs, please include OS/arch, Python/uv versions, the
  bbc-sim version or commit, the BACnet client used, and a config excerpt.
- For open-ended questions, prefer **Discussions** over issues.
- Security problems: **do not** open a public issue — see
  [`SECURITY.md`](SECURITY.md).
- Be respectful and constructive in all project spaces.

## Where the docs live

| You want… | Read |
|-----------|------|
| Why the project exists | `docs/vision/vision.md` |
| Why a design choice was made | `docs/adr/` |
| What to build (product reqs) | `docs/backlog/PRD.md`, `docs/backlog/epic/` |
| How it should behave (spec) | `docs/specs/` |
| Roadmap | `docs/roadmap.md` |
| Troubleshooting | `docs/troubleshooting.md` |
