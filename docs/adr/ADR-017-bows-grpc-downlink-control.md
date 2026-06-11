# ADR-017: BOWS 下り制御は Building OS GatewayEgress(gRPC) 双方向 stream

**Status:** Accepted  **Date:** 2026-06-08  **Origin:** EP-008 継続（#67, user request）

> **Supersedes:** [[ADR-016]] の Decision 2（下り制御を `Transport.subscribe` + `ControlSchema`
> の MQTT/AMQP コマンドチャネルとして実装する案）。AMQP 1.0 telemetry（ADR-016 Decision 1, #48）は
> 本 ADR の影響を受けず有効のまま。
>
> ※ ADR-016 は AMQP telemetry の姉妹 PR（#66, `epic/EP-008-amqp-hono`）で導入される。本 PR は
> それと独立に main から分岐しているため、両者がマージされた時点で ADR-016 §2 に superseded
> バナーを付す（マージ順は問わない）。

## Context

EP-008 の下り制御（Building OS → 仮想 B-BC への WriteProperty）は [[ADR-014]]/[[ADR-015]] と
`docs/specs/northbound-bows-buildingos.md` §7 で将来課題だった。ADR-016 ではこれを BOWS の
consumer パス（`Transport.subscribe` で制御チャネルを購読 → WriteProperty、値解釈は `ControlSchema`）
として暫定設計した。

その後 **Building OS 側（`gutp-building-os-oss`）が下り経路の受け口を gRPC GatewayBridge /
GatewayEgress として設計・issue 化**した（設計: `docs/oss-egress-gateway-bridge-plan.md`、
`gutp-building-os-oss#159`/#163）。上流に gRPC IF を置き、ゲートウェイ（建物エッジ）は
**クラスタ外クライアント**として接続する構成である。よって BOWS の対向実装は MQTT/AMQP コマンド
チャネルではなく **gRPC 双方向 stream クライアント**として作るのが正となった（#67）。

この変更は下り制御の**トランスポートのみ**を差し替えるもので、B-BC の方向不変条件
（[[ADR-005]] 北=BACnet/IP・南=binding）は不変。BOWS は依然 B-BC の**下流クライアント**であり、
WriteProperty は北向き BACnet クライアントとしての書込（[[ADR-014]]）。

## Decision

1. **下り制御 IF は gRPC `GatewayEgress.Connect`（ゲートウェイごと 1 本の双方向 stream）。**
   - BOWS は building-edge の **gRPC クライアント**として上流へダイヤルアウトする
     （インバウンドポート不要・NAT 越え）。接続は `Hello{gateway_id}` で確立。
   - `gateway_id` は上流ゲートウェイ識別子であり **bbc_id にしない**（[[ADR-003]]）。
   - 受信 `ControlCommand{control_id, point_id, bacnet_device, object_type, instance_no,
     present_value, priority}` を **BACnet WriteProperty(present-value)** に変換して対象 B-BC へ
     書込（`services/client.py` 流用、`priority` は書込優先度）。
   - 結果は `ControlResult{control_id, success, response}` で返し、Building OS の `WaitForResult`
     まで通知する。
   - 接続健全性: keepalive、定期 reconnect + jitter、**mTLS**（cluster 外接続）。証明書/資格情報は
     環境変数注入で、**既定値は持たない**（[[ADR-015]] §4 と整合）。

2. **gRPC は optional-extra ＋遅延 import**（[[ADR-016]] の AMQP と同方針）。
   - `pyproject.toml` の `[project.optional-dependencies].grpc = ["grpcio", "protobuf"]`。
     codegen 用 `grpcio-tools` は dev グループ。基本インストール／ARM／CI は不変。
   - 契約は `proto/gateway_egress.proto`。生成スタブは `src/bbc_sim/bows/downlink/` に同梱
     （相対 import に補正）し、`scripts/gen_proto.sh` で再生成。
   - `grpc.aio`（asyncio ネイティブ）を使い、単一イベントループを塞がない（[[ADR-010]]、proton と
     違いスレッド executor 不要）。

3. **責務分離（テスト容易性）。** command→WriteProperty の純ロジック（`executor.py`/`pump.py`/
   `backoff.py`）は **gRPC 非依存・既定 suite でユニットテスト**。実 gRPC ワイヤ（mTLS チャネル・
   bidi ループ・proto 変換、`client.py`）は遅延 import ＋ `@pytest.mark.integration`
   （インプロセス GatewayEgress サーバとのループバック）。

### 値変換（present-value）

| object_type（ASHRAE enum） | BACnet 書込値 |
|----------------------------|---------------|
| analog (0/1/2)             | Real（数値そのまま） |
| binary (3/4/5)             | 0/1（present_value ≥ 0.5 → active） |
| multi-state (13/14/19)     | 状態番号（int 丸め） |

書込対象は **writable オブジェクトのみ**。非 writable / 未知 object_type / BACnet エラーは
`ControlResult{success=false, response=理由}` を返す（接続は落とさず継続）。

## Consequences

- 基本インストールは gRPC 非依存のまま。下り制御利用者のみ `uv sync --extra grpc`。
- 下り制御コマンドの**正の契約**は `gutp-building-os-oss` 側 proto。本リポの
  `proto/gateway_egress.proto` はそれと整合させる対向定義であり、確定差分は同期する（🔧）。
- 実 GatewayEgress 連携は `gutp-building-os-oss#163` と同期して E2E 確認。CI はインプロセス
  ループバックで自己完結（PR-NF-032 と整合）。
- spec `northbound-bows-buildingos.md` §7（下り制御）を ✅/🔧（gRPC GatewayEgress）へ更新。
- ADR-016 の `ControlSchema` / MQTT コマンドチャネル案は本 ADR で無効化。値型の扱いは上表に集約。
