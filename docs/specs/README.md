# Specs — Index

`requirements-definition-v1.1.md` を **設計（Specification）の正** とする。本 README は章マップと、実装着手時に切り出す下流設計書の予定。

## 章マップ（requirements-definition-v1.1.md）

| 関心領域 | 章 |
|----------|----|
| 入力仕様（SBCO 列） | §5 |
| YAML 生成・変換ルール・object type 推定 | §6 |
| B-BC モデル / Device Object | §7 |
| BACnet オブジェクト要件 | §8 |
| BACnet サービス要件（北向き） | §9 |
| 必須プロパティ | §10 |
| シミュレーション・Fault | §11 |
| BBMD / サブネット越え | §12 |
| Docker | §13 |
| simulator.yaml サンプル | §14 |
| CLI | §15 |
| 試験シナリオ TS-01〜11（+PRD TS-12〜14） | §16 |
| REST API | §17 |
| MQTT トピック（**南向き**） | §18 |

## 下流設計書（v0.1 素案 — PRD §13 補足より）

すべて v0.1 素案として配置済み。各文書はステータス記号で粒度を示す（✅確定 / 🔧暫定 / ❓未決）。未決事項は各文書末尾に集約。

- [x] [`object-id-numbering.md`](object-id-numbering.md) — instance_no 自動採番ルール（[[ADR-003]][[ADR-007]]）
- [x] [`sbco-to-bacnet-mapping.md`](sbco-to-bacnet-mapping.md) — SBCO→BACnet マッピング（[[ADR-006]][[ADR-007]]）
- [x] [`southbound-binding.md`](southbound-binding.md) — MQTT/ZeroMQ/WoT/gRPC ⇄ BACnet（[[ADR-005]]）
- [x] [`operating-modes.md`](operating-modes.md) — Simulator/Gateway/Combined（[[ADR-002]][[ADR-004]][[ADR-005]]）
- [x] [`pics-bibbs.md`](pics-bibbs.md) — PICS/BIBBs 対応方針
- [x] [`bacnet-service-priority.md`](bacnet-service-priority.md) — サービス実装優先度・状態管理
- [x] [`compose-integration-env.md`](compose-integration-env.md) — Docker Compose 統合試験環境

> これらは v0.1 素案であり ❓未決事項を多く含む。確定し次第ステータス記号を更新し、重要な決定は ADR 化する（未決の要点は `../memory/decisions.md` に集約）。
