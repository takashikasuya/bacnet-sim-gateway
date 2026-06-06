# ADR-003: `gateway_id` ≠ `bbc_id`（混同禁止）

- **Date:** 2026-06-06
- **Status:** Accepted
- **原典:** 要件定義書 §4, §22-3 / PRD CON-3, PR-F-003, PR-NF-009

## Context

SBCO ポイントリストには `gateway_id` 列がある。これは上位ゲートウェイ（接続ゲートウェイ）の識別子である。仮想 B-BC の識別子（`bbc_id`）として `gateway_id` を流用すると、識別不整合とデータ汚染を招く（PRD リスク）。両者は概念レベルで別物である。

## Decision

- `gateway_id` は **ゲートウェイ識別子** としてのみ扱い、`bbc_id` に流用しない。
- `bbc_id` は **設定ファイルまたは環境変数**（`BBC_ID`）で明示的に与える。
- 検証（validate）で両者の混同を機械的に検出・警告する。

## Consequences

- B-BC 識別が入力データから独立し、同一 SBCO リストから異なる `bbc_id` の B-BC を生成できる。
- YAML 上 `gateway_id` は `metadata.gateway_id` に格納され、`bbc.bbc_id` とは別フィールド。
- 最重要原則として AGENTS.md / pitfalls にも明記。
