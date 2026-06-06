# ADR-005: ノースバウンド＝BACnet/IP、サウスバウンド＝MQTT/ZeroMQ/WoT/gRPC

- **Date:** 2026-06-06
- **Status:** Accepted（PRD v1.1 の方向定義を v1.2 で訂正）
- **原典:** PRD v1.2 変更履歴, §1.2, §4, CON-6, CON-7, PR-F-080〜090

## Context

PRD v1.1 では「シミュレータ／ゲートウェイのデュアルモードと多プロトコルバインディング」を導入したが、**どちらが北向き（上位インタフェース）でどちらが南向きか**が曖昧だった。素朴には「BACnet を取り込んで MQTT 等で上位へ出す」と読みがちだが、本製品の上位連携先（Building OS）は **Eclipse Hono 等の接続ゲートウェイが BACnet を取り込む** 前提である。したがって本製品が上位へ提供すべきは BACnet/IP であり、MQTT 等は下位（フィールド側データ源）との接続に使う。

## Decision

- **ノースバウンド（上位インタフェース）= BACnet/IP に限定。** 上位系へは接続ゲートウェイ（Hono 等）経由で取り込まれる。上位プロトコルへの直結はしない（CON-6）。
- **サウスバウンド（下位インタフェース）= MQTT / ZeroMQ / Web of Things / gRPC のバインディング。** 北向きには用いない（CON-7）。
- Gateway モードでは南向きが値の **source of record**：Telemetry（南向き→BACnet `presentValue`→北向き読取）、Command（北向き WriteProperty→南向き送出）。主たる方向はサウスバウンド。
- Simulator モードは南向きを使わず値を内部生成。Combined は両者を混在。

## Consequences

- v1.1 で MQTT を北向き的に捉えていた箇所は無効。要件定義書 §18 の MQTT は南向きと読み替える。
- 南向きバインディングはプロトコル非依存の内部モデルから派生させ、プロトコル追加を容易にする（PR-NF-015）。
- 南向き入力と北向き BACnet `presentValue` の論理一致を試験で担保（PR-NF-017, AC-13）。
- 関連: [[ADR-004]]（単一モデル共有）。
