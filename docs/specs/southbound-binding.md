# サウスバウンド・バインディング仕様書（素案 v0.1）

> 出典: 要件定義書 §18。関連: [[ADR-005]]（北/南方向の正）, `operating-modes.md`（source 解決）。
> ステータス記号: ✅ 確定 / 🔧 暫定 / ❓ 未決。

| 項目 | 内容 |
|------|------|
| 目的 | 南向き MQTT / ZeroMQ / Web of Things / gRPC と BACnet オブジェクトの双方向バインディング規約を定義する |
| 関連要求 | PR-F-082〜090 / PR-NF-015, PR-NF-017 / CON-7 |
| 方向 | 主＝サウスバウンド。Telemetry: 南→BACnet presentValue（北向き読取）／Command: 北向き WriteProperty→南へ送出 |

## 1. 共通バインディングモデル ✅

各 BACnet オブジェクトに最大 1 つの binding を関連付ける。

```yaml
objects:
  - point_id: AHU01_SAT
    object_type: analogInput
    object_instance: 1
    binding:
      protocol: mqtt | zeromq | wot | grpc
      direction: telemetry | command | both
      telemetry: { ... }     # 南→BACnet（writable に関わらず可）
      command:   { ... }     # 北 WriteProperty→南（writable=true のみ）
      mapping:
        value_path: "$.value"   # 取り出し位置（JSONPath 等）
        type: real|boolean|unsigned|enum
        scale: 1.0
        offset: 0.0
        enum_map: { "0": "Off", "1": "On" }   # multistate 用
      quality:
        staleness_sec: 30       # 超過で statusFlags/OutOfService 連動
        on_stale: out_of_service | fault | hold
```

### 1.1 データフロー ✅
- Telemetry: 南受信 → `mapping` で正規化 → `presentValue` 更新 → `statusFlags.fresh` 更新 → 北 ReadProperty で取得。
- Command: 北 WriteProperty（Writable）→ `mapping` 逆変換 → 南へ送出。
- 整合性（PR-NF-017）: 同一オブジェクトの南向き入力値と北向き presentValue が論理一致すること。

### 1.2 型変換 ✅
| BACnet | 正規化型 | 南向き表現（既定） |
|--------|----------|--------------------|
| REAL (Analog) | real | number |
| BinaryPV (Binary) | boolean | true/false（または active/inactive 文字列） |
| Unsigned/Enumerated (Multi-state) | unsigned/enum | 整数 or stateText 文字列（enum_map） |

- スケール/オフセット適用順: `bacnet = raw * scale + offset`（command は逆変換）。

## 2. MQTT バインディング ✅（PR-F-084 / MVP-2）

要件定義書 §18 のトピック規則を踏襲（**南向きとして**）。

| 方向 | 動作 | トピック源（§6 の優先順） |
|------|------|------------------|
| telemetry | subscribe | `local_id`（既定）/ 明示設定 / 導出 `building/{building}/device/{device}/point/{point}/telemetry` |
| command | publish | `local_id`（既定）/ 明示設定 / 導出 `.../command` |

ペイロード（JSON 既定）
```json
{ "value": 18.2, "ts": "2026-06-06T01:23:45Z", "quality": "good" }
```
- QoS 既定 1、retain ❓（telemetry は retain=true が便利だが要決定）。
- ペイロード形式（JSON / プレーン値 / SparkplugB）は ❓。既定 JSON。

## 3. ZeroMQ バインディング 🔧（PR-F-085 / MVP-2）

| 方向 | ソケット案 | 備考 |
|------|-----------|------|
| telemetry | SUB（PUB へ connect） | topic フレーム = point_id または上記トピック文字列 |
| command | PUB（または PUSH） | 同上 |

- メッセージ枠組み: `[topic][payload(JSON)]` の 2 フレーム（既定）。
- ❓ SUB/PUB か PUSH/PULL か、bind/connect の役割（本製品が connect 側か bind 側か）を要決定。
- ❓ 読取要求型（REQ/REP）を併設するか。

## 4. Web of Things バインディング 🔧（PR-F-086 / MVP-3）

本製品は **WoT Consumer** として南向き Thing を取り込む。

| WoT Interaction | BACnet 対応 | 方向 |
|-----------------|-------------|------|
| Property (readproperty / observeproperty) | presentValue 更新 | telemetry |
| Property (writeproperty) / Action (invokeaction) | WriteProperty 受領時に実行 | command |
| Event (subscribeevent) | 将来: Notification/COV と連携 | （将来） |

```yaml
binding:
  protocol: wot
  thing_description_url: "http://device/.well-known/wot"
  telemetry: { affordance: "temperature", form: "observeproperty" }
  command:   { affordance: "setpoint", form: "writeproperty" }
```
- ❓ TD の取得方法（URL / ディレクトリ）、セキュリティスキーム、affordance ⇄ point_id の対応表形式。

## 5. gRPC バインディング 🔧（PR-F-087 / MVP-2）

proto 素案（本製品＝クライアント、南向きサービスを呼ぶ案）。
```proto
service SouthboundPoint {
  rpc Read(PointRef) returns (PointValue);                  // telemetry pull
  rpc Subscribe(PointRef) returns (stream PointValue);      // telemetry stream
  rpc Write(WriteRequest) returns (WriteAck);               // command
}
message PointValue { string point_id = 1; double real = 2; bool boolean = 3;
                     uint32 unsigned = 4; string ts = 5; string quality = 6; }
```
- ❓ 本製品が gRPC クライアント（南へ接続）か、サーバ（南が接続）か。現案はクライアント＋streaming subscribe。
- ❓ TLS / 認証。

## 6. 南向きアドレスの決定（local_id 第一）✅（PR-F-090）

南向きアドレス（MQTT topic / ZeroMQ topic / gRPC point ref / WoT affordance）の優先順位:

1. **明示 binding 設定**（`binding.telemetry.topic` 等）があればそれ。
2. 無ければ **SBCO `local_id`**（原典で「BACnet の ObjectID / MQTT の TOPIC」＝設備側アドレスそのもの）。南向きプロトコルに応じて解釈。
3. それも無ければ building/device/point から決定的に**導出**（fallback）。

- Simulator モードでは `local_id` は **metadata のみ**（北の ObjectID は採番 [[ADR-011]] で決まり、local_id とは別物）。
- 南向きは MQTT/ZeroMQ/WoT/gRPC（CON-7）。原典の「local_id=BACnet ObjectID」は実設備が BACnet の場合の話で、本製品の南向き対象外。

## 7. 品質・異常系の連動 ✅
- staleness 超過時に `on_stale` に従い `outOfService=true` または `statusFlags.fault` を設定（フォールトインジェクション PR-F-031 と整合）。
- 南向き接続断 → 対象オブジェクト群を一括 stale 扱い（🔧 粒度要決定）。

## 8. 観測性 ✅
- REST/CLI で各オブジェクトの binding 状態（接続/最終受信時刻/quality）を確認可能（PR-NF-013）。

## 9. 未決事項（❓）
- 各プロトコルの認証/TLS、ペイロード形式の正規仕様
- ZeroMQ/gRPC の bind/connect 役割
- WoT TD の取得・対応付け形式
- retain / QoS / 再送ポリシー
- Combined モードでの binding 有無による source 切替（`operating-modes.md` と整合）
