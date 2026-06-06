---
name: architecture
description: System architecture — modes, north/south binding direction, components
metadata:
  type: project
---

# Architecture

> 詳細は PRD v1.3 §4（`../backlog/PRD-v1.3.md`）と要件定義書 §3,§4（`../specs/requirements-definition-v1.1.md`）。

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

## 主要制約

- 1 Container = 1 B-BC（[[ADR-002]]）
- `gateway_id` ≠ `bbc_id`（[[ADR-003]]）
- 入力は SBCO のみ（[[ADR-001]]）
- BACnet/IP（UDP 47808）、`network_mode: host` 推奨
- 規格: ANSI/ASHRAE 135-2024 / ISO 16484-5

## Technology Stack

- Language: Python 3.12 / uv
- BACnet library: TBD（bacpypes3 が有力。decisions.md 参照）
- 南向き: MQTT（Mosquitto/EMQX）, ZeroMQ, WoT, gRPC
- Config: YAML
- 配布: Docker / docker compose

## Open Questions

- [ ] BACnet ライブラリ（bacpypes3 vs BAC0）— decisions.md 参照
- [ ] 南向き内部モデルの抽象 API（MVP-2）
- [ ] instance_no 自動採番ルール
