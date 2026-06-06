# AGENTS.md

> Operating contract for AI agents working in this repository.

---

## 1. Project Overview

SBCO BACnet B-BC Simulator / Gateway — SBCO 標準ポイントリストを唯一の入力として仮想 BACnet B-BC を生成し、**BACnet/IP（北向き）** で公開する統合シミュレータ兼プロトコル変換ゲートウェイ。実設備なしで接続ゲートウェイ（Hono 等）/ Ditto / Building OS との結合試験を CI まで含めて成立させることが第一目的。

- Simulator モード: SBCO → YAML → 仮想 B-BC、値を内部生成して BACnet/IP に北向き公開
- Gateway モード: 南向き（MQTT/ZeroMQ/WoT/gRPC）のデータ源を BACnet オブジェクト化して北向きへ
- 対象: 接続ゲートウェイ / Ditto / Building OS / BAS・BEMS / YABE との結合試験、CI、ハードウェア無し開発

**最重要原則（違反厳禁）:**
- 北向き=BACnet/IP、南向き=MQTT/ZeroMQ/WoT/gRPC（逆にしない / ADR-005）
- `gateway_id` ≠ `bbc_id`（混同しない / ADR-003）
- 1 Docker Container = 1 B-BC（ADR-002）
- 入力は SBCO のみ・YAML が中間モデル（ADR-001, ADR-004）

Tech stack: Python 3.12 · uv · BACnet ライブラリ TBD（bacpypes3 有力）· Docker

---

## 2. Required Reading

Before making architectural decisions:

1. `docs/vision/vision.md` — why this exists and what is out of scope
2. `docs/memory/architecture.md` — system structure and open questions
3. `docs/memory/decisions.md` — settled and pending design choices
4. `docs/adr/` — formal decision records

Before implementing a feature:

5. Relevant `docs/backlog/` item — what and why
6. Relevant `docs/specs/` file — acceptance criteria and API shape
7. `docs/memory/pitfalls.md` — known failure modes

---

## 3. Workflow

1. Read the issue or task.
2. Read the linked spec and backlog item.
3. State your implementation plan before writing code.
4. Implement the minimal change required.
5. Run tests.
6. Report deliverables (see §6).

詳細なプロセス（ブランチモデル・Issue 分解・TDD ループ・レビューゲート・エピック毎 PR・CI）は `docs/development-workflow.md`。テストドリブン・1 エピック=1 PR・`main` 直接 merge 禁止が要点。

When requirements are unclear:

- Ask questions.
- Do not assume.
- Do not invent requirements.

---

## 4. Coding Rules

- Prefer the simplest solution that satisfies the spec.
- Avoid premature abstraction.
- Keep dependencies minimal.
- Follow existing patterns in the codebase.
- Use type hints throughout.
- Use `uv` for dependency management.

---

## 5. Scope Control

Only modify files directly related to the task.

Do not:

- Refactor unrelated code
- Rename modules not mentioned in the task
- Reorganize directory structure
- Add documentation unless the task requires it
- Introduce new dependencies without discussion

---

## 6. Deliverables

After completing a task, report:

- Files changed and why
- Tests executed and results
- Any follow-up work identified

---

## 7. Safety Rules

Never do the following without explicit confirmation:

- Delete data or files
- Execute database migrations
- Push to `main`
- Deploy to any environment
- Modify production configuration
- Send messages to external services
