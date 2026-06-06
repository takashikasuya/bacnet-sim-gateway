# Docker Compose 統合試験環境設計（素案 v0.1）

> 出典: 要件定義書 §13, §16, §20。関連: [[ADR-002]]（1container=1BBC）, [[ADR-005]]（北/南方向）, EP-004。
> ステータス記号: ✅ 確定 / 🔧 暫定 / ❓ 未決。

| 項目 | 内容 |
|------|------|
| 目的 | 統合試験環境（本製品＋YABE＋MQTT Broker＋Eclipse Hono／Ditto＋南向き擬似デバイス）を Compose で構成する |
| 関連要求 | PR-NF-004〜007, PR-F-088, PR-F-089 / AC-1〜13 |
| 原則 | 北向き BACnet/IP は接続ゲートウェイが取り込む。南向き擬似デバイスは MQTT/ZeroMQ/WoT/gRPC で本製品にデータ供給 |

## 1. トポロジ ✅

```
        ┌──────────────┐
        │  Building OS  │ (任意/モック)
        └──────▲────────┘
               │ northbound(AMQP/Kafka)
   ┌───────────┴───────────┐
   │ Eclipse Hono / Ditto   │  ← 北向き BACnet を取り込む接続GW（BACnetコネクタ含む）
   └───────────▲───────────┘
               │ BACnet/IP (UDP 47808)  ← NORTHBOUND
        ┌──────┴───────┐        ┌─────────┐
        │  bbc-sim      │◀──────│  YABE    │ (北向き相互運用確認)
        │ (sim/gateway) │        └─────────┘
        └──────▲───────┘
               │ southbound bindings
   ┌───────────┼───────────────┬───────────────┐
   │           │               │               │
┌──┴───┐  ┌────┴────┐    ┌─────┴────┐    ┌─────┴────┐
│MQTT  │  │ZeroMQ   │    │ WoT Thing │    │ gRPC svc  │  ← 南向き擬似デバイス
│Broker│  │mock dev │    │ mock dev  │    │ mock dev  │
└──────┘  └─────────┘    └───────────┘    └───────────┘
```

## 2. サービス構成 ✅

| サービス | 役割 | 例 |
|----------|------|-----|
| bbc-sim | 本製品（mode 切替） | 自前イメージ |
| mqtt-broker | 南向き MQTT | Eclipse Mosquitto |
| south-mqtt-device | 南向き擬似デバイス（telemetry/command） | 自前スクリプト |
| south-zeromq-device | ZeroMQ 擬似デバイス | 自前スクリプト |
| south-wot-thing | WoT Thing 擬似 | 自前/node-wot |
| south-grpc-device | gRPC 擬似サービス | 自前 |
| hono | 接続ゲートウェイ（北向き取込側） | Eclipse Hono |
| ditto | デジタルツイン | Eclipse Ditto |
| yabe | 北向き BACnet クライアント（手動確認用） | （ホスト実行が一般的） |

> ❓ YABE は Windows GUI のため Compose 同梱が難しい。CI では BACnet テストクライアント（例: BAC0/bacpypes ベースの自前テスター）に置換する案。

## 3. ネットワーク方針 ✅

- BACnet/IP はブロードキャスト（Who-Is/I-Am）を用いるため、北向き検証は `network_mode: host` を推奨（PR-NF-006）。
- 南向き（MQTT/gRPC 等）はユニキャストのため bridge ネットワークで可。
- host と bridge の混在が難しい場合は ❓ 構成を分割（北向き検証用 compose と南向き検証用 compose）する案。

## 4. profiles（試験シナリオ別起動）🔧

Compose profiles で必要サービスのみ起動。

| profile | 対象 TS / AC | 起動サービス |
|---------|--------------|--------------|
| sim-basic | TS-01〜05 / AC-1〜5 | bbc-sim(sim), （yabe/テスター） |
| gw-mqtt | TS-06 / AC-6 | bbc-sim(gateway), mqtt-broker, south-mqtt-device |
| gw-south-all | AC-13 | bbc-sim(gateway), 南向き全 mock |
| north-hono | TS-07,08 / AC-7,8 | bbc-sim, hono, (ditto, building-os-mock) |
| control-loop | TS-09 / AC-9 | bbc-sim(gateway), hono, mqtt-broker, south-mqtt-device |
| bbmd | TS-10 / AC-10 | bbc-sim ×2（別サブネット）, bbmd |
| fault | TS-11 / AC-11 | bbc-sim(+fault injection) |
| combined | AC-12 | bbc-sim(combined), south mocks |

## 5. Compose 雛形（抜粋）🔧
```yaml
services:
  bbc-sim:
    image: sbco/bbc-sim:latest
    network_mode: host          # 北向き BACnet/IP 検証時
    environment:
      BBC_ID: bbc-local-001
      BBC_MODE: gateway
      BBC_ENABLE_BINDING: mqtt
    volumes:
      - ./config/simulator.yaml:/etc/bbc/simulator.yaml:ro
    command: ["run", "--config", "/etc/bbc/simulator.yaml"]

  mqtt-broker:
    image: eclipse-mosquitto:2
    profiles: ["gw-mqtt", "control-loop", "gw-south-all"]
    ports: ["1883:1883"]

  south-mqtt-device:
    build: ./mocks/mqtt-device
    profiles: ["gw-mqtt", "control-loop"]
    depends_on: [mqtt-broker]
```
- ❓ host モードと profiles 下の bridge サービスの共存方式（上記は混在前提だが要検証）。

## 6. CI 連携 ✅（PR-NF-007）
```
GitHub Actions
  └ docker compose --profile gw-mqtt up -d
       └ integration-test（BACnet テスター＋南向き mock 駆動）
            └ アサーション: AC-6 等
  └ docker compose down
```
- テスト合否は AC-* に紐づくアサーションで判定（`bacnet-service-priority.md` §4 参照）。
- ❓ Hono/Ditto は起動が重いため CI では mock 化 or 限定 profile で実行。

## 7. 成果物配置 ✅（要件定義書 §20 と整合）
```
docker/
 ├ Dockerfile
 ├ docker-compose.yml          # profiles 定義
 └ compose.north.yml(任意)     # host モード分割案
config/
 ├ simulator.yaml
 └ mapping.yaml
mocks/
 ├ mqtt-device/
 ├ zeromq-device/
 ├ wot-thing/
 └ grpc-device/
```

## 8. 未決事項（❓）
- 北向き host モードと南向き bridge の共存可否（分割 compose の要否）
- YABE 代替の CI 用 BACnet テスタの選定
- Hono/Ditto/Building OS のモック化範囲
- 複数 B-BC（別サブネット）の BBMD 試験構成
