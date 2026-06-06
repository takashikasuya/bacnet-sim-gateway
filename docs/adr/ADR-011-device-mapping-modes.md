# ADR-011: 設備マッピングモード（aggregated / multi-device / auto-partition）

- **Date:** 2026-06-07
- **Status:** Accepted
- **改訂対象:** [[ADR-002]], [[ADR-008]]（「1 instance = 1 B-BC」のカーディナリティを改訂）
- **原典:** SBCO pointlist.md（device_id_bacnet は設備ごと）/ PRD §5 ペルソナ, §7

## Context

SBCO ポイントリストは本来 `B-OWS → Gateway → BACnet Device（VAV/AHU/Meter/Sensor）→ Point` を表現し、行ごとの `device_id_bacnet` は **実設備の BACnet Device** である。すなわち 1 つの点リストは **複数の BACnet Device** を含む。

一方で本製品の用途は分かれる:
- **Building OS / Ditto / MQTT 試験**: 何台の Device が見えるかより、**全ポイントが見えるか**が重要。500〜5000 点を一括で扱いたい。
- **Gateway / Discovery 試験**: 実設備のトポロジ（Device が何台見えるか）の忠実再現が重要。

加えて、1 つの BACnet Device に 5000 オブジェクトを載せると、Gateway によっては `ReadPropertyMultiple` が極端に重くなる。

## Decision

**device-mapping mode** を導入する。これは **runtime mode（simulator/gateway/combined, [[ADR-005]]）とは直交** する第 2 の軸である。

1 ランタイムインスタンス = **1 Virtual B-BC**。Virtual B-BC は mode に応じて **1..N 個の BACnet Device** を公開する（N>1 は BACnet 仮想ネットワーク + ルータで実現）。

| mode | 写像 | BACnet Device 数 | MVP |
|------|------|------------------|-----|
| `aggregated` | 点リスト全体 → 1 Virtual B-BC | 1 | **1** |
| `multi-device` | SBCO `device_id_bacnet` ごと → 各 BACnet Device（実設備忠実） | N | 2 |
| `auto-partition` | Device の object 数が上限超過時に分割 | 自動 | 3 |

```yaml
device_mapping:
  mode: aggregated          # aggregated | multi-device
  auto_partition: true      # MVP-3
limits:
  max_objects_per_device: 1000
```

- **aggregated**: 全ポイントを 1 BACnet Device の objects とする。`device_id_bacnet`/`instance_no_bacnet` は跨設備で衝突しうるため **採番し直す**（multi-device では尊重）。BACnet Device id は CLI `--bacnet-device-id`（＝ Virtual B-BC の id）。GW001/GW002 を跨いだ集約も可。
- **multi-device**: `device_id_bacnet` ごとに Device を生成し、`instance_no_bacnet` を尊重。複数 Device の同一ホスト公開には仮想ネットワーク/ルータ・アドレス設計が必要 → BBMD（PR-F-041）と同一マイルストーン。
- **auto-partition**: `objects > max_objects_per_device` の Device を `Virtual Device #1..#N` に自動分割。

### ペルソナ指針（PRD §5）
- **Building OS 開発者 → `aggregated`**（ポイント網羅が主眼）
- **Gateway 開発者 → `multi-device`**（実設備トポロジ忠実）

### 制約（明記）
- **`aggregated` モードは Discovery 試験・Device 構成試験に使用しない**（1 Device しか見えないため実トポロジを隠す）。これらは `multi-device` を使う。

## Consequences

- generator は点リストを device 単位にグループ化できる。CLI `--bacnet-device-id` は aggregated/partition の基底 Device id。
- object-id 採番は **(virtual) device 単位**にスコープする（`object-id-numbering.md` 改訂）。aggregated は跨設備衝突回避のため再採番。
- ADR-002/008 の「1 instance = 1 B-BC」を「1 instance = 1 Virtual B-BC（1..N BACnet Device を公開）」に改訂。Device レベルの独立性はルーティングで担保。
- 大規模点リストの RPM 性能問題を auto-partition で緩和。
- multi-device/auto-partition の多 Device 公開は仮想ネットワーク+ルータ実装に依存（[[ADR-010]] の single-loop 上で動作）。
