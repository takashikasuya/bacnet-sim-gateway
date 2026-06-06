# ADR-007: object type は object_type_bacnet を優先し、無ければ推定（推定時は警告）

- **Date:** 2026-06-06（**改訂 2026-06-07**: SBCO 原典に合わせ推定根拠を変更）
- **Status:** Accepted
- **原典:** 要件定義書 §6 / PRD PR-F-005, PR-F-006 / SBCO pointlist.md

## Context

SBCO ポイントを BACnet object type に対応付ける必要がある。

当初は「データ型(float/bool/enum) ＋ writable」から推定する想定だった。しかし SBCO 原典（pointlist.md）を確認した結果、`point_type` は **意味的プロファイル名**（温度/湿度/空調制御 等）であり **データ型ではない**。データ型を直接表す列は存在せず、実データでは `object_type_bacnet`（例 `Analog-Input`）が**ほぼ常に明示**されている。

## Decision

**`object_type_bacnet` の明示を本筋**とし、無い場合のみ他列から推定する。推定に頼った時点で**検証警告**を出し、ポイントリストの明示化を促す。

優先順位:

1. **`object_type_bacnet` があれば正規化して採用**（`Analog-Input`→`analogInput` 等）。最優先（PR-F-006）。
2. 無ければ推定（推定したら **警告**: 「object_type_bacnet を明示してください」）:
   - `labels` 数 ≥ 3 → MultiState{Input|Value}
   - `labels` 数 == 2 → Binary{Input|Value}（例 `開&&閉`）
   - 数値 `unit` あり または `point_specification` ∈ {Measurement, Metering, Setpoint} → Analog{Input|Value}
   - `point_specification` ∈ {Status, Alarm} かつ数値 unit 無し → Binary{Input|Value}
   - それ以外 → Analog にフォールバック ＋ **警告**
3. Input ⇄ Value: `writable=false`→Input、`writable=true`→Value。
4. **Output 系（AO/BO/MO）は推定で生成しない**。必要なら `object_type_bacnet` で明示（明示が本筋なので警告ではなく仕様）。
5. 整合性警告: `point_specification` ∈ {Command, Setpoint} なのに `writable=false` 等の矛盾は警告。

## Consequences

- 実データ（object_type_bacnet 明示）はそのまま正しく対応付く。
- 明示が無いケースでも `labels` 個数が multistate(≥3)/binary(==2) を明快に切り分ける。
- 推定はあくまで保険であり、走るたびに警告でポイントリスト明示化を促す → 属人的な推定依存を防ぐ。
- Output は明示専用（推定の曖昧さを持ち込まない）。
- 詳細ルールは `../specs/sbco-to-bacnet-mapping.md` §2。
