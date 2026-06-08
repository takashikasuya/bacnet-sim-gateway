---
name: decisions
description: Index of design decisions (ADRs) and pending choices for the B-BC simulator/gateway
metadata:
  type: project
---

# Design Decisions

> 正式な決定は `../adr/` に記録。本ファイルはその索引と、未決事項のメモ。

## Settled (ADR で記録済み)

| ADR | 決定 | 原典 |
|-----|------|------|
| ADR-001 | SBCO 標準ポイントリストを唯一の入力ソースとする | 要件§5,§22 |
| ADR-002 | 1 Docker Container = 1 B-BC | 要件§4,§13 |
| ADR-003 | `gateway_id` ≠ `bbc_id`（混同禁止・最重要） | 要件§4,§22 |
| ADR-004 | YAML を中間モデルとする（全モード共有） | 要件§6,§14 |
| ADR-005 | 北向き=BACnet/IP、南向き=MQTT/ZeroMQ/WoT/gRPC（v1.2訂正） | PRD v1.2 |
| ADR-006 | セマンティックタグ = BACnet `tags` ＋ Project Haystack | PRD v1.3 |
| ADR-007 | object type をデータ型＋writable から自動推定（BACnet列優先） | 要件§6 |
| ADR-008 | Raspberry Pi/ネイティブ実行をファーストクラス・Docker は任意（1 instance=1 B-BC） | PRD v1.4 |
| ADR-009 | BACnet ライブラリは bacpypes3 に一本化（server/client 両用、asyncio） | decisions.md |
| ADR-010 | ランタイムは single-loop asyncio。Core Object Model は event-loop 閉じ込め・no blocking | decisions.md |
| ADR-011 | device-mapping mode（aggregated/multi-device/auto-partition）。runtime mode と直交。1 instance=1 Virtual B-BC（1..N BACnet Device 公開） | SBCO pointlist |
| ADR-012 | device_type=Brick クラス採用。BACnet セマンティックタグは Brick から導出。SBCO tags 列はビルOS検索タグで別物 | SBCO schema |
| ADR-013 | 南向きは Transport 抽象（subscribe/publish）。InMemory（CI 既定）＋ MQTT/ZeroMQ（integration）。値変換は mapping に集約 | EP-002 |
| ADR-014 | BOWS = 仮想 B-BC の下流の独立 BACnet クライアント消費者。Building OS へ MQTT/AMQP 供給。B-BC の北=BACnet/南=binding（ADR-005）は不変 | EP-008 |
| ADR-015 | Building OS 取り込みは BACnet ネイティブ schema `bacnet-device-message`、MQTT 先行・AMQP 後。Transport 抽象（ADR-013）再利用 | EP-008 |
| ADR-017 | BOWS 下り制御は Building OS GatewayEgress(gRPC) 双方向 stream 購読→BACnet WriteProperty。grpc は optional-extra・遅延 import。ADR-016 §2 を置換 | EP-008 #67 |

## Pending Decisions

- ~~南向きバインディングの内部モデル抽象~~ → 確定（[[ADR-013]]）。残: 各プロトコルの auth/TLS/QoS/retain、gRPC 具象 transport（EP-006）
- **管理 UI（EP-007）の認証・外部公開**: MVP は localhost/LAN・認証なし（REST/UI とも `host=127.0.0.1`）。認証方式・外部公開・ロール（閲覧/操作）は将来 EPIC で決定。決定したら ADR 化
- **BOWS**（EP-008 / `../specs/northbound-bows-buildingos.md`）: deviceId 決定規則 / TimeStamp の出所（B-BC vs コネクタ時計）/ COV vs poll 既定 / 配信保証(QoS/retain)・認証/TLS / AMQP テレメトリ（PR-F-105）。下り制御は確定（[[ADR-017]]・#67、gRPC GatewayEgress）。残: GatewayEgress proto の上流確定差分の同期

### 下流設計書 v0.1 が surface した未決事項（❓）

仕様の素案（`../specs/*.md`）に含まれる主要な未決。確定したら該当 spec を更新し、影響大は ADR 化。

- **採番**（object-id-numbering）: フォールバック Device instance のハッシュ方式・範囲 / バンド採番の採否 / 複数 B-BC 同居時の Device instance 割当
- **マッピング**（sbco-to-bacnet-mapping）: Output 系（AO/BO/MO）採用条件 / point_type→float/bool/enum 正規化 / Analog 既定値（min/max/resolution）/ priorityArray の扱い / enum 状態ラベルの SBCO 格納形式
- **タグ**（ADR-006 詳細）: 採用する BACnet 標準タグ・Haystack タグ集合の確定 / `tags` 列構文（区切り・エスケープ）/ 名前空間表現
- **南向き**（southbound-binding）: 各プロトコルの認証/TLS・ペイロード形式 / ZeroMQ・gRPC の bind/connect 役割 / MQTT retain・QoS
- **モード**（operating-modes）: 無効プロトコル binding のフォールバック / 南向き接続の起動順序・リトライ
- **適合**（pics-bibbs）: 目標 Protocol Revision の確定 / セグメンテーション・最大 APDU 既定 / 任意 BIBB（DM-UTC-B 等）採否 / ASHRAE 223P 連携段階
- **試験環境**（compose-integration-env）: host と bridge の共存可否（分割 compose）/ CI 用 BACnet テスタ選定 / Hono・Ditto のモック化範囲
