# EP-008: Northbound BOWS Connector — BACnet → Building OS

**Status:** Draft  **Priority:** P1  **MVP:** 2（AMQP/command は MVP-3）

## Goal

仮想 B-BC の北向き BACnet を**クライアントとして取り込み**、テレメトリを Building OS
（`gutp-building-os-oss`）の **BACnet ネイティブスキーマ**に変換して **MQTT** で供給する
コネクタ（**BOWS**）を成立させる。実 Building OS までの連携経路を閉じる。

> BOWS は B-BC の**下流の独立消費者**（[[ADR-014]]）。B-BC 自身の北=BACnet/南=binding（[[ADR-005]]）は不変。

## Acceptance Criteria（対応 PR-F / AC）

- [ ] **BACnet 取得**: Who-Is で B-BC 発見 → object-list 列挙 → present-value をポーリング取得（任意で COV）（PR-F-100 / AC-17）
- [ ] **エンコード**: 取得値を `bacnet-device-message` へ決定的に変換（Device_id / BACnetDevice / ObjectType+InstanceNo / PresentValue / ISO-8601 TimeStamp）。原典スキーマ準拠（PR-F-101 / AC-18 / [[ADR-015]]）
- [ ] **MQTT 配信**: `telemetry/{tenant}/{deviceId}` へ publish。Transport 抽象（[[ADR-013]]）再利用、CI は InMemory フェイク（PR-F-102 / AC-19）
- [ ] **CLI/設定**: `bbc-sim bows run`（対象 B-BC・tenant・device_id 写像・broker URI・interval・認証）。single-loop（[[ADR-010]]）（PR-F-103）
- [ ] **識別子整合**: `Device_id` と BACnet identity を安定発行。`localId={tenant}/{deviceId}`。point_id 解決は Building OS 側（外部依存・PR-F-104）
- [ ] **テスト/統合環境**: loopback B-BC→BOWS→フェイク broker でスキーマ捕捉、実 Mosquitto＋golden fixtures で適合確認、compose 拡張（PR-NF-030〜032）
- [ ] **manual**: 実 Building OS 取り込み（OxiGraph 登録前提）まで疎通

## Future（本エピック範囲外・OPEN issue として起票）

- [ ] AMQP 1.0（Hono northbound, `/telemetry/{tenant}`）トランスポート（PR-F-105）
- [ ] 下り制御: Building OS `device-control`（type=BACnet）→ BACnet WriteProperty 往復（PR-F-106）

## Specs / ADR

仕様: `../../specs/northbound-bows-buildingos.md`。決定: [[ADR-014]]（役割）, [[ADR-015]]（スキーマ/MQTT先行）,
[[ADR-013]]（Transport 再利用）, [[ADR-005]]（B-BC 方向は不変）。

## Issues

テレメトリ先行: #42（取得）, #43（エンコード）, #44（MQTT 配信）, #45（CLI）, #46（識別子）, #47（テスト/統合）。
将来（OPEN）: #48（AMQP/Hono）, #49（下り制御）。

## 再利用

`src/bbc_sim/services/client.py`（whois/RPM/COV/list_objects）, `src/bbc_sim/southbound/transport.py`
（Transport + InMemory）, `src/bbc_sim/southbound/mqtt.py`（MqttTransport）,
`docker/docker-compose.integration.yml` + `docker/mosquitto.conf`。
