# ADR-014: Northbound BOWS connector as a separate downstream consumer

**Status:** Accepted  **Date:** 2026-06-07  **Origin:** EP-007（user request）

## Context

実 Building OS 連携の検証には、仮想 B-BC が公開する北向き BACnet を取り込み、テレメトリを
MQTT/AMQP に変換して Building OS（`gutp-building-os-oss`）へ供給する**接続ゲートウェイ**が要る。
旧 vision ではこれを Non-Goal としていたが、検証経路を閉じるため本リポジトリのスコープに加える。

ここで方向の混同が起きやすい。bbc-sim 本体の不変条件は **北向き=BACnet/IP・南向き=binding**（[[ADR-005]]）で、
「MQTT は北向き出力ではない」。一方コネクタは MQTT/AMQP を Building OS への**出力**に使う。

## Decision

**BOWS** を、仮想 B-BC の**下流に位置する独立した BACnet クライアント**として定義する。

- BOWS は仮想 B-BC を **BACnet で読む消費者**（Who-Is/ReadProperty(Multiple)/COV）。
- BOWS の Building OS への出力（MQTT/AMQP）は **B-BC より 1 つ上のレイヤのリンク**であり、
  **bbc-sim 自身のインターフェースではない**。よって [[ADR-005]] は不変（B-BC の北=BACnet/南=binding は不変）。
- 実装は本リポジトリの新パッケージ `src/bbc_sim/bows/` ＋ CLI `bbc-sim bows run`。
- `gateway_id ≠ bbc_id`（[[ADR-003]]）、入力は SBCO のみ（[[ADR-001]]）は引き続き不変。

```
[仮想 B-BC] ──BACnet/IP(北)──▶ [BOWS コネクタ] ──MQTT/AMQP──▶ [Building OS]
   (bbc-sim, ADR-005)            (BACnet client + publisher)     (gutp-building-os-oss)
```

## Rationale

- 役割分離: BOWS を B-BC とは別の消費者として切り出すことで、ADR-005 の方向定義を侵さずに
  接続ゲートウェイ機能を実現できる。
- 再利用: 取得は `services/client.py`、配信は `southbound/transport.py` の Transport 抽象
  （[[ADR-013]]）を流用できる。

## Consequences

- vision の Non-Goal「接続ゲートウェイ自体の実装」を撤回（スコープ拡大）。
- スキーマ・トランスポートの具体は [[ADR-015]]。
- 下り（Building OS→B-BC への制御）は将来課題（telemetry 先行）。
- Building OS 側の point_id 解決（OxiGraph）はコネクタのスコープ外（整合 ID 発行のみ）。
