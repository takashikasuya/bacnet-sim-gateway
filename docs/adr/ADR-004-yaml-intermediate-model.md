# ADR-004: YAML を中間モデルとする

- **Date:** 2026-06-06
- **Status:** Accepted
- **原典:** 要件定義書 §3, §6, §14, §22-4 / PRD PR-F-004, PR-NF-008, PR-NF-016

## Context

SBCO 入力から直接 BACnet ランタイムを起動することもできるが、(1) 全モード（Simulator/Gateway/Combined）で同一のオブジェクトモデルを共有する必要があり、(2) 生成結果を人が検証・編集できる中間表現があると試験再現性とデバッグ性が高まる。

## Decision

入力（SBCO）とランタイムの間に **YAML 中間モデル（`simulator.yaml`）** を置く。生成（`generate-yaml`）と検証（`validate`）を分離し、ランタイムは YAML のみを入力とする。全モードがこの YAML 由来の単一オブジェクトモデルを共有する。

## Consequences

- 生成と実行が分離され、CI で生成物を検証・固定できる。
- 南向きバインディングもこの単一モデルから派生（プロトコル非依存、[[ADR-005]]）。
- YAML スキーマの安定性が重要（破壊的変更は要 ADR）。
- 関連: [[ADR-001]], [[ADR-007]]（object type 推定の出力先）。
