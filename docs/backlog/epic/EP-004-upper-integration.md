# EP-004: Upper-System Integration (MVP-2)

**Status:** Draft  **Priority:** P1  **MVP:** 2

## Goal

北向き BACnet/IP を接続ゲートウェイ（Eclipse Hono 等）/ Ditto が取り込み、Building OS まで通る連携経路をエンドツーエンドで成立させる（第一目的 G-3）。サブネット越え探索にも対応。

## Acceptance Criteria（対応 AC / 要求）

- [ ] 北向き BACnet を Hono 等が取り込める形で提供（AC-7 / PR-F-088）
- [ ] Ditto 連携を阻害しない（AC-7 / PR-F-089）
- [ ] Building OS まで取得経路が通る（AC-8 / PR-NF-004,014）
- [ ] 制御ループ往復：上位→北向き WriteProperty→南向きコマンド（AC-9 / PR-F-023,083）
- [ ] BBMD / Foreign Device Registration で異サブネット探索（AC-10 / PR-F-041）
- [ ] Docker Compose 統合試験環境（YABE / MQTT Broker / Hono / Ditto / 南向き擬似デバイス）
- [ ] GitHub Actions で結合試験を自動実行（PR-NF-007）

## Specs / ADR

経路定義: 要件 §16 TS-06〜10。前提: PRD §9。方向: [[ADR-005]]。
