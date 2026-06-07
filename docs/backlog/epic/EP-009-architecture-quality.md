# EP-009: Architecture & Quality Improvements

**Status:** Draft  **Priority:** P2  **MVP:** 2（技術的負債の返済・横断）

## Goal

EP-001〜008 の実装で蓄積したアーキテクチャ上の負債と品質ギャップを、**振る舞いを変えずに**
（テストで担保しながら）返済する。カプセル化・重複排除・型安全・例外処理・テスト網羅・CI を改善し、
今後のエピック（BOWS=EP-008 ほか）の実装速度と安全性を上げる。

> 本エピックは横断的リファクタリングであり、新しい製品要求は追加しない。各変更は
> 既存テストでリグレッションが無いこと（または新規テストで新挙動）を確認してからマージする。

## Acceptance Criteria（対応 PR-NF / 改善項目）

- [ ] **依存定義の単一化**: dev 依存を 1 テーブルに統一し ruff/mypy を含める。`uv sync` 単体で lint/型/テストが揃う（PR-NF-021）
- [ ] **OID 構築の重複排除**: `spec_to_oid(spec)` ヘルパへ集約（6 箇所）。挙動不変をテストで確認（PR-NF-022）
- [ ] **カプセル化**: `BBCApplication` の writable/command OID をアクセサ経由に。外部モジュールからの private 代入と `# type: ignore` を撤廃（PR-NF-022）
- [ ] **例外処理の厳格化**: `fault._trySet` / southbound telemetry handler の握り潰しを限定捕捉＋ログに（PR-NF-023）
- [ ] **ライブ再読込の完全化**: 非構造変更（tags/metadata 等）の同期、generator 再構築順序の修正（PR-F-056 改 / ADR-004）
- [ ] **型安全**: `runtime`/`rest`/`web` の `Any` を `TYPE_CHECKING` 下の具体型へ。mypy で検出可能に（PR-NF-022）
- [ ] **テスト網羅**: ZeroMQ transport・MQTT transport（paho モック）・REST POST 系（write 異常/scenario/reload/mode）の unit テスト追加（PR-NF-024）
- [ ] **CI 強化**: カバレッジ計測（pytest-cov）と `ruff format --check` を追加（PR-NF-024）
- [ ] **ジェネレータ規約**: 基底 `next()` を `abstractmethod` 化、`engine.rebuild()` の状態リセットを明確化（PR-NF-022）

## Non-Goals（本エピック範囲外）

- 機能追加・API 変更（振る舞いは不変。`/mode` のライブ切替は ADR-010 により対象外のまま）
- southbound MQTT の `asyncio-mqtt` への載せ替え（依存最小化方針＝AGENTS.md §5。スレッド境界はテスト＋ドキュメントで担保）
- CI のマルチ OS / Python マトリクス / ARM ランナー / SBOM / 脆弱性監査（将来。現段階は過剰）

## Specs / ADR

決定: [[ADR-003]]（device_id≠bbc_id 維持）, [[ADR-004]]（再読込）, [[ADR-010]]（single-loop 非ブロッキング維持）,
[[ADR-013]]（Transport 抽象）。新規 PR-NF: PR-NF-021〜024（PRD §9）。

## Issues

EP-009.1 依存単一化（#TBD）, EP-009.2 spec_to_oid 集約（#TBD）, EP-009.3 カプセル化（#TBD）,
EP-009.4 例外処理（#TBD）, EP-009.5 ライブ再読込（#TBD）, EP-009.6 型安全（#TBD）,
EP-009.7 ZeroMQ テスト（#TBD）, EP-009.8 MQTT テスト（#TBD）, EP-009.9 REST POST テスト（#TBD）,
EP-009.10 CI カバレッジ/format（#TBD）, EP-009.11 ジェネレータ規約（#TBD）。
