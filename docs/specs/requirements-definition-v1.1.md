# SBCO BACnet B-BC Simulator 要件定義書 v1.1

> **位置づけ**: 本書は実装方式・データ構造・CLI 仕様・試験シナリオの **設計 (Specification) の正** とする。
> 上位の製品要求は `../backlog/PRD-v1.4.md` を参照。設計判断の根拠は `../adr/` を参照。

---

## 1. 概要

### 1.1 目的

本システムは、SBCO標準ポイントリストを入力として、

- BACnet B-BC相当の仮想コントローラを生成
- BACnet/IPネットワークへ公開
- BACnet Gateway
- MQTT Gateway
- Eclipse Ditto
- Building OS
- BAS/BEMS
- YABE等のBACnet Explorer

との接続試験を可能とする統合シミュレータである。

本システムは実設備の代替として利用できることを目的とする。

### 1.2 想定利用シーン

**開発環境**

```
Building OS → BACnet Connector → Simulator
```

**Gateway開発**

```
Gateway → BACnet → Simulator
```

**Ditto連携**

```
Ditto → MQTT → BACnet Gateway → Simulator
```

**CI/CD試験**

```
GitHub Actions → Docker → Simulator → Integration Test
```

---

## 2. 対象規格

**BACnet**

- ANSI/ASHRAE 135-2024
- ISO 16484-5

**BACnet試験**

- ANSI/ASHRAE 135.1
- ISO 16484-6

**将来対応**

- BACnet/SC
- BTL適合支援
- PICS出力
- EDE出力

---

## 3. システム構成

```
SBCO Point List
       │
       ▼
YAML Generator
       │
       ▼
simulator.yaml
       │
       ▼
BACnet B-BC Simulator
       │
       ├ BACnet/IP
       ├ REST API
       ├ MQTT
       └ Web UI(Optional)
```

---

## 4. アーキテクチャ

**基本原則**

```
1 Docker Container = 1 B-BC
```

**重要: `gateway_id` ≠ `bbc_id`**

SBCOポイントリストの `gateway_id` はゲートウェイ識別子であり、`bbc_id` には使用しない。

**B-BC識別**

B-BC識別子は設定ファイルまたは環境変数で与える。

```yaml
bbc:
  bbc_id: "bbc-local-001"
```

または

```
BBC_ID=bbc-local-001
```

---

## 5. 入力仕様

**入力形式**

- `point-list.csv`
- `point-list.xlsx`

対象は `smartbuilding_datamodel_builder` repository の SBCO標準ポイントリストとする。
**原典リポジトリ**: https://github.com/smartbuilding-co-creation-organization/smartbuilding_datamodel_builder
（必須列・任意列・BACnet 列の定義はこのリポジトリの仕様に追従する。）

**必須列**

```
gateway_id, point_id, point_name, point_type, point_specification,
writable, device_id, device_name, device_type, site, building,
floor, installation_area, local_id
```

**任意列**

```
interval, unit, min_pres_value, max_pres_value, tags, description, panel
```

**BACnet列**（存在する場合は優先利用する）

```
device_id_bacnet, instance_no_bacnet, object_type_bacnet
```

---

## 6. YAML生成要件

**CLI**

```
bbc-sim generate-yaml \
  --input point-list.csv \
  --output simulator.yaml \
  --bbc-id bbc-local-001 \
  --bacnet-device-id 1001
```

**変換ルール**

| SBCO列 | YAML |
|--------|------|
| gateway_id | metadata.gateway_id |
| device_id | metadata.device_id |
| device_name | metadata.device_name |
| device_type | metadata.device_type |
| point_id | point_id |
| point_name | object_name |
| writable | writable |
| unit | units |
| interval | update.interval |
| building | metadata.building |
| floor | metadata.floor |
| installation_area | metadata.installation_area |

**object type自動推定**

| データ型 | writable | object type |
|----------|----------|-------------|
| float | ReadOnly | AnalogInput |
| float | Writable | AnalogValue |
| bool | ReadOnly | BinaryInput |
| bool | Writable | BinaryValue |
| enum | ReadOnly | MultiStateInput |
| enum | Writable | MultiStateValue |

---

## 7. B-BCモデル

**構造**

```
B-BC
 ├ Device Object
 ├ Analog Objects
 ├ Binary Objects
 └ Multi-state Objects
```

**Device Object 必須プロパティ**

```
objectIdentifier, objectName, vendorName, vendorIdentifier,
modelName, firmwareRevision, applicationSoftwareVersion
```

---

## 8. BACnetオブジェクト要件

**必須**

```
Device
Analog Input / Analog Output / Analog Value
Binary Input / Binary Output / Binary Value
Multi-state Input / Multi-state Output / Multi-state Value
```

**将来対応**

```
Schedule, Trend Log, Notification Class, Calendar, Accumulator
```

---

## 9. BACnetサービス要件

**Discovery**

- 必須: Who-Is, I-Am
- 推奨: Who-Has, I-Have

**Data Sharing**

- 必須: ReadProperty, ReadPropertyMultiple, WriteProperty
- 推奨: WritePropertyMultiple

**Device Management**

- 必須: Dynamic Device Binding, Dynamic Object Binding
- 推奨: DeviceCommunicationControl, ReinitializeDevice, TimeSynchronization

**COV（フェーズ2）**

- SubscribeCOV, ConfirmedCOVNotification, UnconfirmedCOVNotification

---

## 10. 必須プロパティ

**Common**

```
objectIdentifier, objectName, objectType, description,
presentValue, statusFlags, eventState, outOfService
```

**Analog**

```
units, minPresValue, maxPresValue, resolution
```

**Binary**

```
activeText, inactiveText, polarity
```

**Multi-State**

```
numberOfStates, stateText
```

---

## 11. シミュレーション要件

**Random Walk**

```yaml
update:
  mode: random_walk
```

**Sin Wave**

```yaml
update:
  mode: sinusoidal
```

**Replay**

```yaml
update:
  mode: replay
```

**Scenario**

```yaml
update:
  mode: scenario
```

**Fault Injection**

```yaml
fault:
  enabled: true
```

対応内容: 通信断 / 値凍結 / 異常値 / OutOfService / Fault状態

---

## 12. BBMD要件

**同一サブネット**: Who-Is / I-Am で探索可能。

**異なるサブネット**: BBMD / Foreign Device Registration に対応。

---

## 13. 実行・配布要件

### 13.1 ネイティブ実行（Raspberry Pi / ARM）✅（PR-NF-019/020）

- Docker 非依存でネイティブに動作すること。Raspberry Pi（ARM/ARM64, Linux）を実行環境に含む。
- 配布: `uv` による依存解決＋ `bbc-sim` CLI 実行（`bbc-sim run --config simulator.yaml`）。
- BACnet/IP のブロードキャスト（Who-Is/I-Am）はホスト NIC 上で直接動作する（ネイティブ実行では Docker のネットワーク制約を受けない）。
- 1 ランタイムインスタンス = 1 B-BC（プロセス単位。Docker でもネイティブでも同様）。
- ❓ サポート対象 OS/アーキ（Raspberry Pi OS 64bit / Debian arm64 等）と Python 配布形態（uv / システム Python / 単一バイナリ）は要確定。

### 13.2 Docker（任意の配布手段）✅

**基本**: 1 Container = 1 B-BC ／ **起動**: `docker compose up` ／ **推奨**: `network_mode: host`

> Docker は配布・統合試験の便宜のための手段であり必須ではない（PR-NF-020）。CI や複数 B-BC 同居には Docker / Compose が便利。

---

## 14. simulator.yaml

```yaml
bbc:
  bbc_id: bbc-local-001
  device_id: 1001
  object_name: Local Virtual B-BC
  vendor_name: SBCO Simulator
  vendor_identifier: 999
  model_name: Virtual BBC
network:
  type: bacnet-ip
  bind_address: 0.0.0.0
  port: 47808
objects:
  - point_id: AHU01_SAT
    object_type: analogInput
    object_instance: 1
    object_name: Supply Air Temperature
    present_value: 18.0
    units: degreesCelsius
    writable: false
    metadata:
      gateway_id: gw-001
      device_id: ahu-01
      device_name: AHU-01
      building: building-a
      floor: 10
```

---

## 15. CLI要件

| コマンド | 用途 |
|----------|------|
| `bbc-sim generate-yaml` | YAML生成 |
| `bbc-sim validate` | YAML検証 |
| `bbc-sim run` | 起動 |
| `bbc-sim whois` | Discovery |
| `bbc-sim read-property` | ReadProperty |
| `bbc-sim read-property-multiple` | ReadPropertyMultiple |
| `bbc-sim write-property` | WriteProperty |
| `bbc-sim list-objects` | オブジェクト一覧 |
| `bbc-sim validate-point-list` | ポイントリスト検証 |

---

## 16. ローカル連携テスト要件

| TS | 名称 | 確認内容 |
|----|------|----------|
| TS-01 | SBCO CSV → YAML | CSV読込 / 必須列検証 / YAML生成 |
| TS-02 | Discovery | Who-Is / I-Am、YABEから発見可能 |
| TS-03 | ReadProperty | presentValue / units / description |
| TS-04 | ReadPropertyMultiple | RPM が機能する |
| TS-05 | WriteProperty | Writableのみ変更可能 |
| TS-06 | MQTT Gateway | Simulator → BACnet → Gateway → MQTT |
| TS-07 | Ditto | Simulator → BACnet Gateway → MQTT → Ditto |
| TS-08 | Building OS | Simulator → BACnet Connector → Building OS |
| TS-09 | 制御ループ | Application → Ditto → MQTT → Gateway → WriteProperty → Simulator |
| TS-10 | BBMD | 別サブネット探索 |
| TS-11 | Fault Injection | 異常値 / 通信断 / 値停止 / OutOfService |

> PRD v1.4 で TS-12（Combined モード同時公開）/ TS-13（ZeroMQ・WoT・gRPC バインディング）/ TS-14（tags プロパティ）を追加想定。

---

## 17. REST API

**情報取得**

```
GET /devices
GET /devices/{id}
GET /objects
GET /objects/{id}
```

**値変更**

```
POST /objects/{id}/write
```

**シナリオ変更**

```
POST /simulation/scenario
```

---

## 18. MQTT要件

**Telemetry**

```
building/{building}/device/{device}/point/{point}/telemetry
```

**Command**

```
building/{building}/device/{device}/point/{point}/command
```

> PRD v1.2 によりこの MQTT は **サウスバウンド（南向きバインディング）** に位置づけ直された。
> Telemetry を subscribe して BACnet `presentValue` に反映、`command` へ publish。詳細は `../adr/ADR-005-northbound-bacnet-southbound-binding.md`。

---

## 19. 将来拡張

**BACnet**: BACnet/SC, TrendLog, Schedule, Calendar, Alarm/Event

**Building OS**: REC, Brick, QUDT, WoT TD, JSON-LD

**標準成果物**: PICS, EDE, IEIEJ CSV

---

## 20. 成果物

```
docs/
 ├ requirements.md
 ├ architecture.md
 ├ yaml-spec.md
 ├ bacnet-services.md
 ├ test-scenarios.md
config/
 ├ simulator.yaml
 ├ mapping.yaml
docker/
 ├ Dockerfile
 ├ docker-compose.yml
src/
 ├ yaml_generator.py
 ├ simulator_runtime.py
 ├ bacnet_objects.py
 ├ services.py
```

> 本リポジトリでは上記 docs/ 成果物をレイヤモデル（vision/backlog/specs/adr/memory）に再配置している。対応は `../specs/README.md` を参照。

---

## 21. MVP

**MVP-1**

```
SBCO Point List → YAML生成 → 1 B-BC生成 → Who-Is/I-Am
→ ReadProperty → ReadPropertyMultiple → WriteProperty
→ Docker起動 → YABE接続確認
```

**MVP-2**

```
WritePropertyMultiple, COV, MQTT, Ditto, Building OS Connector
```

**MVP-3**

```
BACnet/SC, PICS生成, EDE生成, BTL適合支援
```

---

## 22. 設計上の重要原則

1. SBCO標準ポイントリストを唯一の入力ソースとする
2. 1 Docker Container = 1 B-BC
3. gateway_id と bbc_id を混同しない
4. YAML を中間モデルとする
5. BACnet Gateway、MQTT、Ditto、Building OS との接続試験を第一目的とする
6. 実設備が無くても統合試験可能な環境を提供する
7. 将来的な BACnet/SC、PICS、EDE 出力に拡張可能な設計とする

> これら原則は ADR として `../adr/` に記録（ADR-001〜007）。

### 実装着手時に追加作成を推奨する設計書

- オブジェクトID採番仕様書（instance_no 自動生成ルール）
- SBCO→BACnet マッピング仕様書
- PICS/BIBBs 対応方針
- BACnet サービス実装優先度一覧
- Docker Compose による統合試験環境設計（YABE、MQTT Broker、Ditto含む）
