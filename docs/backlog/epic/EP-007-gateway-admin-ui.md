# EP-007: Gateway Admin UI (MVP-2)

**Status:** Draft  **Priority:** P2  **MVP:** 2

## Goal

ゲートウェイ管理者向けの軽量 Web UI を、既存 REST 制御プレーン（`PR-F-050`）と**同一プロセス・同一ポート**で提供し、点リスト再読込・モード/管理デバイス/オブジェクト確認・値/状態変更・ログ確認・南向きバインディング確認・北向き BACnet/IP 稼働状態確認を 1 画面で完結させる。サーバレンダリング（FastAPI + Jinja2 + HTMX、Node ビルド非依存）で Raspberry Pi ネイティブ実行（[[ADR-008]]）と最小依存を維持する。北向きは BACnet/IP の稼働状態確認のみとし、上流（Hono/Ditto/Building OS）へはプローブしない（[[ADR-005]]）。

## Acceptance Criteria（対応 AC / 要求）

- [ ] 軽量サーバレンダリング Web UI を提供（Jinja2/HTMX、Node 非依存・Pi ネイティブ）（PR-F-052 / [[ADR-008]]）
- [ ] REST で runtime 状態（mode・北向き bind/カウンタ・南向き接続）を取得（AC-15 / PR-F-054 / PR-NF-013）
- [ ] REST/UI で南向きバインディング状態（protocol/address/最終更新/品質）を確認（PR-F-055 / PR-NF-013）
- [ ] REST/UI でログ（検証/バインディング/Fault/BACnet サービス）を閲覧（PR-F-053 / PR-NF-012,013）
- [ ] REST/UI で点リスト再読込（検証→差分→ライブ適用 or 再起動要求）（PR-F-056 / [[ADR-004]]）
- [ ] 値書込・OutOfService・Fault 注入を UI から実行（PR-F-050 / 要件 §17）
- [ ] モード・管理デバイス・オブジェクトを表示（`device_id`≠`bbc_id` を区別）（PR-F-063 / [[ADR-003]]）
- [ ] 初回利用者向けオンボーディング（初回ツアー＋常設 Help ページ＋コンテキストヘルプ＋空状態ガイド）（AC-16 / PR-F-057 / PR-NF-012）
- [ ] 北向き状態はローカル内省のみ・上流プローブなし（[[ADR-005]]）
- [ ] MVP は localhost/LAN・認証なし（外部公開/認証は将来 EPIC）
- [ ] 新規ランタイム依存は jinja2 のみ・HTMX はローカル vendoring（AGENTS.md §5 で明示）

## Specs / ADR

仕様: 要件 §17（REST）。決定: [[ADR-002]][[ADR-003]][[ADR-004]][[ADR-005]][[ADR-008]][[ADR-010]]。認証・外部公開は本 EPIC の範囲外（将来 EPIC）。実装計画（エンドポイント・モジュール構成・Issue 分割・テスト戦略）は本 EPIC の Issue 化時に `.github/ISSUE_TEMPLATE/feature.md` で展開する。
