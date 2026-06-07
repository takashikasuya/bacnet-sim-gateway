# BOWS コネクタ仕様書 — BACnet → Building OS（素案 v0.1）

> 出典: Building OS `gutp-building-os-oss`（取り込みスキーマ）。関連: [[ADR-014]]（BOWS 役割）,
> [[ADR-015]]（スキーマ/トランスポート）, [[ADR-013]]（Transport 抽象）, [[ADR-005]]（B-BC 方向）。
> ステータス記号: ✅ 確定 / 🔧 暫定 / ❓ 未決。

| 項目 | 内容 |
|------|------|
| 目的 | 仮想 B-BC の北向き BACnet を取り込み、テレメトリを MQTT/AMQP で Building OS へ供給する規約を定義 |
| 関連要求 | PR-F-100〜106 / PR-NF-030〜032 / AC-17〜19 |
| 原典スキーマ | `gutp-building-os-oss` `DotNet/BuildingOS.Shared/Defines/Schemas/bacnet-device-message.json` |
| 位置づけ | B-BC の**下流**の独立消費者（[[ADR-014]]）。B-BC 自身の北=BACnet/南=binding は不変 |

## 1. 全体フロー ✅

```
[仮想 B-BC] ──BACnet/IP── ▶ [BOWS] ── encode ──▶ bacnet-device-message ── MQTT publish ──▶ [Building OS]
  Who-Is / RPM / COV          (acquire)             (§3 スキーマ)        telemetry/{tenant}/{deviceId}
```

## 2. 取得（Acquisition）✅（reuse: `src/bbc_sim/services/client.py`）

- **Discovery**: `whois(app, target)` で対象 B-BC（device instance, address）を取得。
- **列挙**: `list_objects(app, target)` で object-list を取得する（同関数は object-list を**そのまま**返す）。コネクタ側で device / network-port オブジェクトを**除外**してから読取対象とする。
- **読取**: `read_property_multiple` で各オブジェクトの `present-value`（必要に応じ `units`/`object-name`）を取得。
- **更新方式**: 既定はポーリング（`interval` 秒）🔧。`subscribe_cov` による COV 駆動は任意（❓ 既定の採否）。
- B-BC は読み取り対象（BACnet クライアントとして動作）。書込（下り制御）は本仕様の対象外（§7）。

## 3. エンコード（bacnet-device-message）✅（[[ADR-015]]）

各 BACnet オブジェクトを 1 つの `ValueString[]` 要素へ写像し、デバイス単位で配列に束ねる。

| 取得値 | スキーマ項目 |
|--------|--------------|
| 取得時刻（ISO-8601 + TZ） | `ValueString[].TimeStamp` |
| BACnet device instance | `ValueString[].BACnetDevice` |
| object type 名（`AnalogInput` 等） | `ValueString[].BACnetObject._base` |
| object type enum（0=AI,1=AO,2=AV,3=BI,4=BO,5=BV,13=MI,14=MO,19=MV） | `BACnetObject._value.ObjectType` |
| object instance | `BACnetObject._value.InstanceNo` |
| present-value（数値） | `ValueString[].Properties.PresentValue` |
| コネクタが発行する device 識別子 | トップレベル `Device_id` |

> `PresentValue` は **数値型**（原典スキーマ `number`）。binary は 0/1、multi-state は状態番号（1..N）で送る。
> `TimeStamp` の出所（B-BC 値の取得時刻 vs コネクタ時計）は ❓。

### 3.1 原典スキーマ（verbatim — 正は原典リポ）✅

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["Device_id", "ValueString"],
    "properties": {
      "Device_id": { "type": "string" },
      "ValueString": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["TimeStamp", "BACnetDevice", "BACnetObject", "Properties"],
          "properties": {
            "TimeStamp": { "type": "string", "format": "date-time" },
            "BACnetDevice": { "type": "integer" },
            "BACnetObject": {
              "type": "object",
              "required": ["_base", "_value"],
              "properties": {
                "_base": { "type": "string" },
                "_value": {
                  "type": "object",
                  "required": ["ObjectType", "InstanceNo"],
                  "properties": {
                    "ObjectType": { "type": "integer" },
                    "InstanceNo": { "type": "integer" }
                  }
                }
              }
            },
            "Properties": {
              "type": "object",
              "required": ["PresentValue"],
              "properties": { "PresentValue": { "type": "number" } }
            }
          }
        }
      }
    }
  }
}
```

### 3.2 生成例

```json
[
  { "Device_id": "bbc-local-001",
    "ValueString": [
      { "TimeStamp": "2026-06-07T12:00:00+09:00",
        "BACnetDevice": 1001,
        "BACnetObject": { "_base": "AnalogInput", "_value": { "ObjectType": 0, "InstanceNo": 1001 } },
        "Properties": { "PresentValue": 21.5 } }
    ] }
]
```

## 4. トランスポート / トピック ✅（MQTT 先行・[[ADR-015]]）

- **MQTT（Mosquitto）**: `telemetry/{tenant}/{deviceId}` に publish。`tenant` 既定 `default`。
  認証は user/pass を**外部 secret（環境変数 / secret store）から注入**する。仕様・実装ともに
  **既定パスワードは持たない**（資格情報を文書やコードに固定しない）🔧。
- 配信は `southbound/transport.py` の `Transport` を再利用（InMemory=CI、`MqttTransport`=実機）。
- **AMQP 1.0（Hono northbound）**: アドレス `/telemetry/{tenant}`、メッセージ属性 `device_id` /
  `orig_address`。後続実装（§7, 将来 issue）。

## 5. 識別子（Identity）✅

- Building OS は `localId = {tenant}/{deviceId}` から **point_id をサーバ側（OxiGraph）で解決**する。
- コネクタは `Device_id`（=deviceId）と BACnet オブジェクト identity を**安定発行**する責務のみ。
  point_id 登録・オントロジ整備は Building OS 側（外部依存・本仕様スコープ外）。
- deviceId の決め方（B-BC の bbc_id／device instance／設定マッピング）は 🔧（既定: 設定で明示、無ければ bbc_id）。

## 6. 検証ルール ✅

- 生成 JSON が §3.1 スキーマに適合（必須項目・型）。
- ObjectType enum がオブジェクト型と一致。
- TimeStamp が ISO-8601（TZ 付き）。
- integration: 実 Mosquitto に publish → Building OS の golden fixtures（**Building OS 側リポジトリ `gutp-building-os-oss` の** `tests/golden/`。本リポジトリ内のパスではない）と整合確認。

## 7. 将来（本仕様の対象外）❓

- **AMQP/Hono トランスポート**（`/telemetry/{tenant}`）。
- **下り制御**: Building OS `POST /api/device-control`（type=BACnet）→ BACnet WriteProperty で
  仮想 B-BC を制御する往復ループ。
- 配信保証（at-least-once/QoS/retain）、バッチング/レート制御、TLS/認証の本番設定。
