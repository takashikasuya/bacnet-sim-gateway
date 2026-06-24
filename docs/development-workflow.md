# Development Workflow

> プロセス層。コードをどう作るかの運用ルール。設計の正は ADR/Spec、製品要求の正は PRD（`backlog/PRD.md`）。本書はそれらを**どう実装に落とすか**だけを定める。AGENTS.md §3 の詳細版。

## 0. 原則

- **テストドリブン**: 失敗するテストを先に書き（TS-*/AC-* を引用）→ 最小実装で green → リファクタ。
- **1 エピック = 1 PR**。`main` への直接 commit/merge/push はしない（AGENTS.md §7）。merge は人間が行う。
- **スコープ厳守**: タスクに直接関係するファイルのみ変更（AGENTS.md §5）。
- **不変条件をコードで守る**: 北向き=BACnet/南向き=binding（ADR-005）、`gateway_id`≠`bbc_id`（ADR-003）、1 instance=1 Virtual B-BC（ADR-002/008/011）、入力は SBCO のみ・YAML が中間モデル（ADR-001/004）。

## 1. ブランチモデル

```
main                         ← 保護。PR 経由のみ。merge は人間。
└── epic/EP-NNN-<slug>        ← エピック単位の作業ブランチ。PR はこれ→main。
    └── (任意) issue/EP-NNN.M-<slug>  ← 大きい issue だけ。通常はエピックブランチに直接コミット。
```

- コミットは issue 単位の論理的なまとまりで。メッセージに `EP-NNN` / `#<issue>` を含める。
- コミット末尾に `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`。

## 2. Issue 分解

1. エピック（`backlog/epic/EP-NNN-*.md`）の AC を読む。
2. AC を**独立に検証可能な単位**へ割る（トレーサーバレット指向：縦に薄く端から端まで通す）。
3. 各 issue は `.github/ISSUE_TEMPLATE/feature.md` で作成し、**PR-F-* / AC-* / TS-* と spec の章**を必ず引用。
4. ラベル `epic:EP-NNN` を付与（`gh label create` 済み前提）。
5. 依存順（採番→モデル→ランタイム→サービス→CLI）で並べる。

`gh` 例:
```bash
gh issue create --title "EP-001.1 SBCO CSV reader + 必須列検証" \
  --label "feature,epic:EP-001" --body-file <(...)
```

## 3. TDD ループ（issue ごと）

1. spec / backlog を読む（AGENTS.md §2）。
2. **Red**: AC/TS を写すテストを書く。落ちることを確認。
3. **Green**: 通す最小実装。
4. **Refactor**: 重複除去・命名整理。テストは緑のまま。
5. `uv run ruff check` / `uv run mypy` / `uv run pytest` を通す。
6. コミット。issue をクローズ（`gh issue close` or PR の `Closes #N`）。

### テスト分類
- **unit**: 生成器・マッピング・検証・採番・タグ。外部 I/O なし。
- **loopback integration**: bacpypes3 のローカルループバックで whois/read/rpm/write を往復（TS-02..05）。
- **`@pytest.mark.integration`**: 実ブローカ/外部系が要るもの。**既定で skip**（CI 無人グリーン維持）。実体は `docker/compose` で手動起動して回す。
- **manual AC**: YABE GUI 接続・ARM 実機・BTL 等、ここで自動化不能なものは PR 本文に「manual」と明記。黙ってスキップしない。

### 外部インフラ方針
EP-002 以降の MQTT/ZeroMQ/gRPC/Hono/Ditto はまず**リポジトリ内フェイク**で自己完結させる（CI 無人グリーン）。実サービスは `docker/compose` ＋ `integration` マーカーで任意。

## 4. Definition of Done（issue）

- 対応 AC を満たす。
- 追加/変更テストが green、既存テストを壊さない。
- 型ヒントあり、ruff/mypy クリーン。
- スコープ外の変更なし。

## 5. レビューゲート（エピック完了時）

- **専用のレビュー・サブエージェント**を起動し、差分＋エピックの AC/spec 参照＋不変条件チェックリストを渡す。
- 観点: 正しさ / 不変条件違反 / テスト網羅 / スコープ逸脱 / 命名・設計。
- 指摘 → 修正 → 再レビューを**クリーンになるまで**反復。結果を PR 本文に要約。
- 注: `/code-review ultra`（ultrareview）はユーザー起動・課金制でプログラムから起動不可。これとは別の、セッション内レビューア。

## 6. PR（エピックごと）

```bash
gh pr create --base main --head epic/EP-NNN-<slug> \
  --title "EP-NNN: <epic name>" --body "..."
```
本文に: 対応 AC/PR-F/TS のチェックリスト、テスト結果、レビュー要約、manual AC、follow-up。**merge はしない**（人間が実施）。

## 7. CI

`.github/workflows/ci.yml`: push/PR で `uv sync` → `ruff check` → `mypy` → `pytest`（`integration` 除く）。エピックごとに job を拡張。

## 8. エピック実行順

EP-001（P0/MVP-1, 完全実装）→ EP-002 → EP-003 → EP-004 → EP-005 → EP-006（P3/MVP-3, 一部は honest に partial）。各エピックで §2→§3→§5→§6 を一巡。
