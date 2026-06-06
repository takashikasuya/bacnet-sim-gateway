# ADR-007: object type をデータ型 ＋ writable から自動推定する

- **Date:** 2026-06-06
- **Status:** Accepted
- **原典:** 要件定義書 §6 / PRD PR-F-005, PR-F-006

## Context

SBCO ポイントを BACnet object type に対応付ける必要がある。すべて人手で指定させると属人化・誤りを招く。一方、SBCO のデータ型と `writable` から大半は機械的に決まる。

## Decision

データ型 ＋ `writable` から object type を自動推定する：

| データ型 | writable | object type |
|----------|----------|-------------|
| float | ReadOnly | AnalogInput |
| float | Writable | AnalogValue |
| bool | ReadOnly | BinaryInput |
| bool | Writable | BinaryValue |
| enum | ReadOnly | MultiStateInput |
| enum | Writable | MultiStateValue |

ただし SBCO に **BACnet 列**（`device_id_bacnet`, `instance_no_bacnet`, `object_type_bacnet`）が存在する場合は、推定より **明示指定を優先** する（PR-F-006）。

## Consequences

- 大半のポイントが追加指定なしで正しい object type になる。
- Output オブジェクト（AO/BO/MO）はこの自動推定表に現れない（Value で表現）。Output が必要なケースは BACnet 列で明示する。
- 推定誤りリスクは BACnet 列優先と検証時の警告で緩和（PRD リスク）。
