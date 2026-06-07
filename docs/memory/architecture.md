---
name: architecture
description: System architecture — modes, north/south binding direction, components
metadata:
  type: project
---

# Architecture

> 詳細は PRD v1.5 §4（`../backlog/PRD-v1.5.md`）と要件定義書 §3,§4（`../specs/requirements-definition-v1.1.md`）。

## 連携方向（最重要）

- **ノースバウンド = BACnet/IP**（常に北向き。上位系へは接続ゲートウェイ Hono 等が取り込む）
- **サウスバウンド = MQTT / ZeroMQ / Web of Things / gRPC**（バインディング。Gateway モードの主データ源）

→ 根拠と訂正経緯は [[ADR-005]]。直結はしない（北向き BACnet のみ提供）。

```
[Building OS] ◀ [Eclipse Hono / BACnet コネクタ] ◀──BACnet/IP── [本製品] ──南向き──▶ [フィールド側データ源]
                                                  (NORTHBOUND)            (SOUTHBOUND: MQTT/ZeroMQ/WoT/gRPC)
```

## 運用モード

| モード | BACnet 値の出所 | 北向き | 南向き |
|--------|-----------------|--------|--------|
| Simulator | 内部生成（random walk/sin/replay/scenario） | BACnet/IP | なし |
| Gateway | 南向きプロトコル（source of record） | BACnet/IP | バインディング |
| Combined | 内部生成＋南向き混在 | BACnet/IP | 一部 |

全モードが **YAML 由来の単一オブジェクトモデルを共有**（[[ADR-004]]）。

## 並行性モデル

**single-loop asyncio**（[[ADR-010]]）。BACnet スタック・シミュレーション・シナリオ・南向きアダプタは全て async タスク。Core Object Model（`presentValue` 等の共有状態）は **event loop に閉じ込め**、他スレッドから直接変更しない。blocking 禁止。sync-only SDK は `run_in_executor`＋`asyncio.Queue` 境界で隔離（例外扱い）。

## パイプライン

```
SBCO Point List (CSV/XLSX) → YAML Generator → simulator.yaml → B-BC Runtime → BACnet/IP
```

## コンポーネント（要件§20 想定）

| Component | 責務 |
|-----------|------|
| `yaml_generator` | SBCO → YAML 変換・object type 推定（[[ADR-007]]） |
| `simulator_runtime` | YAML から B-BC を起動・値生成・モード制御 |
| `bacnet_objects` | Device/Analog/Binary/Multi-state オブジェクトとプロパティ |
| `services` | BACnet サービス（Who-Is/Read/Write/RPM/COV…） |
| （南向き）binding 層 | プロトコル非依存モデル → MQTT/ZeroMQ/WoT/gRPC |
| `bows`（EP-008） | **下流の独立コネクタ**: 仮想 B-BC を BACnet で読み、`bacnet-device-message` に変換し MQTT/AMQP で Building OS へ供給（[[ADR-014]][[ADR-015]]） |

### BOWS の位置（北向きの 1 つ上のレイヤ）

```
[仮想 B-BC] ──BACnet/IP(北)──▶ [BOWS] ──MQTT/AMQP──▶ [Building OS]
  (bbc-sim, ADR-005)            BACnet client + publisher   (gutp-building-os-oss)
```
BOWS の MQTT/AMQP は B-BC のインターフェースではなく**コネクタ→Building OS のリンク**。B-BC の方向定義（[[ADR-005]]）は不変。

> 代表的な通信フローのシーケンス図は `../specs/communication-sequences.md` を参照。

## 主要制約

- 1 ランタイムインスタンス = 1 B-BC（コンテナ/プロセス共通・[[ADR-002]][[ADR-008]]）
- `gateway_id` ≠ `bbc_id`（[[ADR-003]]）
- 入力は SBCO のみ（[[ADR-001]]）
- BACnet/IP（UDP 47808）、Docker 時は `network_mode: host` 推奨
- 規格: ANSI/ASHRAE 135-2024 / ISO 16484-5

## 実行環境・配布

- **Raspberry Pi（ARM/ARM64, Linux）でネイティブ実行をファーストクラス**（[[ADR-008]]）。`uv` ＋ `bbc-sim` CLI。
- Docker / docker compose は任意の配布・統合試験手段（必須ではない）。
- → BACnet ライブラリ・依存は ARM 上でビルド/動作できること。

## 入力ソース（原典）

- SBCO 標準ポイントリスト: https://github.com/smartbuilding-co-creation-organization/smartbuilding_datamodel_builder
- 列定義はこのリポジトリに追従（[[ADR-001]]）。詳細は [[sbco-datamodel-builder-repo]]。
- SBCO オントロジ（`schema/building_model.*`）は **Brick + RealEstateCore (REC) ベース**（device=`brick:Equipment`、point=`brick:Point`、Haystack 参照なし）。device_type は Brick クラス採用、BACnet セマンティックタグは Brick から導出（[[ADR-012]]）。

## Technology Stack

- Language: Python 3.12 / uv
- BACnet library: **bacpypes3**（server/client 両用、asyncio。[[ADR-009]]。ARM 実動作は MVP-1 で確認）
- 南向き: MQTT（Mosquitto/EMQX）, ZeroMQ, WoT, gRPC
- Config: YAML
- 配布: ネイティブ（uv, Raspberry Pi）＋ Docker（任意）

## Open Questions

- [x] BACnet ライブラリ → bacpypes3（[[ADR-009]]）。残: ARM 実動作確認（MVP-1）
- [ ] 南向き内部モデルの抽象 API（MVP-2）
- [ ] instance_no 自動採番ルール
- [ ] サポート対象 OS/アーキと Python 配布形態（要件§13.1）
