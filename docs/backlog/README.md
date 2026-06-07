# Backlog — Index

製品要求は `PRD-v1.5.md`（何を・なぜ・どこまで）。Epic は MVP フェーズに対応。

## Epics

| Epic | スコープ | MVP |
|------|----------|-----|
| [EP-001](epic/EP-001-simulator-core.md) | Simulator Core（SBCO→YAML→B-BC→BACnet 北向き、YABE 接続） | 1 |
| [EP-002](epic/EP-002-modes-southbound-binding.md) | モード機構・南向きバインディング（MQTT/ZeroMQ/gRPC） | 2 |
| [EP-003](epic/EP-003-simulation-fault-injection.md) | 値生成・フォールトインジェクション・COV・REST | 2 |
| [EP-004](epic/EP-004-upper-integration.md) | 上位連携（Hono/Ditto/Building OS）・BBMD・CI | 2 |
| [EP-005](epic/EP-005-semantic-tags.md) | セマンティックタグ（BACnet tags ＋ Haystack） | 2 |
| [EP-006](epic/EP-006-standards-artifacts-sc.md) | BACnet/SC・PICS/EDE・意味モデル・WoT | 3 |
| [EP-007](epic/EP-007-gateway-admin-ui.md) | 管理者向け Web UI（状態確認・値/状態変更・点リスト再読込・ログ・バインディング・北向き稼働状態・オンボーディング） | 2 |

> **device-mapping mode（[[ADR-011]] / `../specs/device-mapping.md`）** は runtime mode と直交する横断機能: `aggregated`=MVP-1（EP-001）、`multi-device`=MVP-2（多 Device 公開は BBMD と同マイルストーン＝EP-004）、`auto-partition`=MVP-3（EP-006）。

## 次のアクション

各 Epic を独立 Issue に分解する際は `.github/ISSUE_TEMPLATE/feature.md` を使い、PR-F-* / AC-* / TS-* と spec の章を引用する。
