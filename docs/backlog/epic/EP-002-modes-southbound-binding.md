# EP-002: Operating Modes & Southbound Binding (MVP-2)

**Status:** Draft  **Priority:** P1  **MVP:** 2

## Goal

動作モード（simulator/gateway/combined）機構を導入し、南向きプロトコル（MQTT/ZeroMQ/gRPC、WoT は MVP-3）のデータ源を BACnet オブジェクト化して北向きへ公開する。プロトコル変換ハブとして成立させる。

## Acceptance Criteria（対応 AC / 要求）

- [ ] 起動時にモード選択（PR-F-080,063）
- [ ] Simulator/Gateway が同一オブジェクトモデルを共有（PR-F-081 / PR-NF-016）
- [ ] 双方向バインディング：Telemetry 南向き→BACnet、Command 北向き→南向き（PR-F-082,083）
- [ ] MQTT 南向きバインディング（subscribe telemetry / publish command）（AC-6 / PR-F-084）
- [ ] ZeroMQ / gRPC 南向きバインディング（AC-13 / PR-F-085,087）
- [ ] トピック/エンドポイント名を BACnet オブジェクトから一貫導出（PR-F-090）
- [ ] Combined モードで内部生成＋南向きを同一 BACnet/IP に同時公開（AC-12 / PR-F-080,081）
- [ ] 南向き入力と北向き presentValue の論理一致（AC-13 / PR-NF-017）

## Specs / ADR

方向定義: [[ADR-005]]。MQTT トピック: 要件 §18。プロトコル非依存内部モデル: PR-NF-015。
