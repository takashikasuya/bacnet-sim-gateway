# 運用モード設計書（素案 v0.1）

> 出典: PRD §4。関連: [[ADR-002]]（1container=1BBC）, [[ADR-004]]（単一モデル共有）, [[ADR-005]]（北/南方向）, `southbound-binding.md`。
> ステータス記号: ✅ 確定 / 🔧 暫定 / ❓ 未決。

| 項目 | 内容 |
|------|------|
| 目的 | Simulator / Gateway / Combined の動作・構成・モデル共有・南北責務分離を定義する |
| 関連要求 | PR-F-080, PR-F-081, PR-F-063 / PR-NF-014, PR-NF-016 |
| 原則 | 北向きは常に BACnet/IP。南向きはバインディング（主）。全モードで同一オブジェクトモデルを共有 |

> **2 つの "mode" 軸を混同しないこと。** 本書は **runtime mode**（値の出所: simulator/gateway/combined）を定義する。SBCO device → BACnet device の写像を決める **device-mapping mode**（aggregated/multi-device）は別軸で `device-mapping.md`（[[ADR-011]]）。両者は直交する。

## 1. モード定義（runtime mode）✅

| モード | BACnet 値の出所 | 北向き | 南向き |
|--------|-----------------|--------|--------|
| simulator | 内部生成（update.mode） | BACnet/IP | なし |
| gateway | 南向き binding | BACnet/IP | MQTT/ZeroMQ/WoT/gRPC |
| combined | オブジェクト単位で内部生成 or 南向き | BACnet/IP | 一部 binding |

## 2. レイヤ責務分離 ✅

> 並行性は **single-loop asyncio**（[[ADR-010]]）。下図の全レイヤは同一 event loop 上の async タスクで、Core Object Model は event loop に閉じ込める。

```
┌───────────────── Northbound Adapter (BACnet/IP) ─────────────────┐
│  Who-Is/I-Am, ReadProperty(Multiple), WriteProperty(Multiple), COV │
└───────────────────────────────────────────────────────────────────┘
                        ▲ 読取                    ▼ 書込(command)
┌────────────────── Core Object Model（全モード共有）───────────────┐
│  Device/Analog/Binary/Multi-state, presentValue, statusFlags 等     │
│  値の出所ポリシー: simulate | binding                                │
└───────────────────────────────────────────────────────────────────┘
        ▲ 値更新(telemetry)            ▼ command 送出
┌──── Value Source ────┐   ┌──── Southbound Adapter ────┐
│ Simulation Engine     │   │ MQTT/ZeroMQ/WoT/gRPC        │
│ (random/sin/replay/...)│   │ (southbound-binding.md)     │
└───────────────────────┘   └─────────────────────────────┘
```

- Northbound Adapter は値の出所を意識しない（Core のみ参照）。
- Core は「各オブジェクトの値が simulate か binding か」だけを保持。
- 値更新経路: simulate→Core、または Southbound telemetry→Core。
- command 経路: 北 WriteProperty→Core→（writable かつ binding あれば）Southbound 送出。

## 3. 起動構成 ✅

### 3.1 CLI（PR-F-063）
```
bbc-sim run --config simulator.yaml \
            --mode gateway \
            --enable-binding mqtt,grpc
```
- `--mode` 未指定時は YAML の `runtime.mode`、それも無ければ `simulator`。
- `--enable-binding` で有効化する南向きプロトコルを限定（gateway/combined 時）。

### 3.2 環境変数
`BBC_ID`, `BBC_MODE`, `BBC_ENABLE_BINDING` 等（CLI > 環境変数 > YAML の優先順）。

### 3.3 YAML 拡張（runtime セクション）
```yaml
runtime:
  mode: combined           # simulator | gateway | combined
  enabled_bindings: [mqtt, grpc]
  southbound:
    mqtt: { broker_url: "tcp://mqtt:1883" }
    grpc: { target: "south:50051" }
objects:
  - point_id: AHU01_SAT          # 南向き由来（gateway）
    object_type: analogInput
    binding: { protocol: mqtt, direction: telemetry, telemetry: {...} }
  - point_id: AHU01_SP           # 内部生成（simulator）
    object_type: analogValue
    writable: true
    update: { mode: sinusoidal, interval: 5 }
```

## 4. Combined モードの source 解決規則 ✅

各オブジェクトについて以下で決定（決定的）。

```
if object.binding is present and object.binding.protocol in enabled_bindings:
    source = BINDING            # gateway 動作
else:
    source = SIMULATE           # update.mode に従う（無ければ静的 present_value 保持）
```

- ❓ binding ありだが当該プロトコル無効時の扱い（SIMULATE フォールバック or エラー）を要決定。現案: フォールバック＋警告。

## 5. モード別の有効サービス ✅

| サービス | simulator | gateway | combined |
|----------|:---:|:---:|:---:|
| Who-Is/I-Am, RP/RPM | ✅ | ✅ | ✅ |
| WriteProperty | ✅(内部値更新) | ✅(→南へ command) | ✅(オブジェクト毎) |
| COV（将来） | ✅ | ✅ | ✅ |
| Fault Injection | ✅ | ✅(南断含む) | ✅ |

## 6. ライフサイクル ✅
1. SBCO 読込 → YAML（中間モデル）構築
2. 採番確定（`object-id-numbering.md`）
3. Core Object Model 構築（値の出所ポリシー付与）
4. Northbound Adapter 起動（BACnet/IP bind）
5. mode に応じ Simulation Engine / Southbound Adapter 起動
6. 実行（telemetry 取込・command 送出・BACnet 応答）

## 7. 整合性・一貫性 ✅（PR-NF-016/017）
- 全モードで同一 instance/識別子体系・同一プロパティ集合。
- 同一オブジェクトの南向き値と北向き presentValue の論理一致を保証。

## 8. 未決事項（❓）
- 無効プロトコル binding のフォールバック方針
- combined で同一 point に simulate と binding を併記した場合の優先（現案: binding 優先）
- 南向き接続の起動順序・リトライ（Hono/Broker 未起動時）
