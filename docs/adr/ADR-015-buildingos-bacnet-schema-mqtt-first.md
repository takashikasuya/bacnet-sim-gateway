# ADR-015: Building OS ingestion via BACnet-native schema, MQTT-first

**Status:** Accepted  **Date:** 2026-06-07  **Origin:** EP-008（user request）

## Context

Building OS（`gutp-building-os-oss`）はテレメトリ取り込みに **2 つのトランスポート**
（MQTT=Mosquitto、AMQP 1.0=Hono northbound）と、デバイス種別ごとの**生スキーマ**を持つ。
そのうち **BACnet 専用スキーマ** `bacnet-device-message.json`（NATS 経路 `building-os.raw.bacnet`）が
存在し、BACnet の Device/ObjectType/Instance と PresentValue を保持したまま取り込める。
Building OS は `localId = {tenant}/{deviceId}` から **point_id をサーバ側（OxiGraph/SPARQL）で解決**する。

## Decision

BOWS（[[ADR-014]]）が Building OS へ送るテレメトリは、

1. **BACnet ネイティブスキーマ `bacnet-device-message` を採用**（汎用 `valid-message` ではなく）。
   BACnet identity（Device 番号・ObjectType・InstanceNo・PresentValue・TimeStamp）を保持し、
   point_id 解決は Building OS 側に委ねる。
2. **MQTT（Mosquitto）を先行実装**。トピックは `telemetry/{tenant}/{deviceId}`。
   **AMQP 1.0（Hono northbound, `/telemetry/{tenant}`）は後続**。
3. 配信は **`southbound/transport.py` の Transport 抽象を再利用**（[[ADR-013]]）。CI は InMemory
   フェイクで自己完結、実 Mosquitto は `integration` マーカーで任意実行。

詳細マッピングは `../specs/northbound-bows-buildingos.md`。

## Rationale

- BACnet ネイティブスキーマは情報損失が最小で、Building OS が正規化（point_id 解決）を担うため
  コネクタ側にオントロジ依存を持ち込まない。
- MQTT 先行は最小構成で自己完結（Mosquitto は既存 compose/CI に存在）。AMQP/Hono は同抽象に
  もう 1 実装を足すだけで追加できる。

## Consequences

- コネクタは `Device_id` と BACnet オブジェクト identity を**安定して**発行する必要がある
  （Building OS 側 OxiGraph 登録と整合させるため）。
- `PresentValue` は数値型（schema は `number`）。binary/multistate は数値（0/1・状態番号）で送る。
- AMQP/Hono トランスポートと下り制御（device-control→WriteProperty）は将来 issue。
- スキーマは外部リポジトリ起源のため drift リスクあり → spec に verbatim 引用し integration テストで
  Building OS の golden fixtures に対して検証する。
