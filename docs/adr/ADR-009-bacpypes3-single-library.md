# ADR-009: BACnet ライブラリは bacpypes3 に一本化（server / client 両用）

- **Date:** 2026-06-07
- **Status:** Accepted
- **原典:** decisions.md（pending: bacpypes3 vs BAC0）/ PR-NF-019,020（ARM）/ pics-bibbs.md

## Context

本製品は 2 つのロールを持つ。(1) **server**＝Who-Is/ReadProperty/WriteProperty に応答する仮想 B-BC（製品本体・適合性が重要）。(2) **client**＝CLI 検証コマンド（`whois`/`read-property`/`write-property`）と CI テストハーネス（YABE 代替）。

候補は `bacpypes3`（Joel Bender の asyncio 版、純 Python、低レベル制御）と `BAC0`（bacpypes/bacpypes3 上の高レベルラッパ、client/manager 指向）。Raspberry Pi（ARM）ネイティブ実行（[[ADR-008]]）により、依存は ARM 上でビルド/動作できることが条件。

## Decision

**bacpypes3 に一本化**し、server・client の両ロールを同一ライブラリで実装する。

- server/runtime（`bacnet_objects` + `services`）は bacpypes3 で実装。Device/オブジェクトモデルとサービスハンドラを低レベルに制御する。
- CLI の client 系コマンドも bacpypes3 で実装。
- `BAC0` は採用しない。将来 client 側のエルゴノミクスが問題化した場合のみ、**CLI/テスト層に限定**して導入を検討する（server の適合性面には決して持ち込まない）。

## Consequences

- ライブラリ 1 つ＝メンタルモデル 1 つ、検証すべき ARM 依存も 1 つ。
- 適合性クリティカルな server 側で、PICS/BIBBs（`pics-bibbs.md`）が要求するプロパティ集合・エラークラス・サービス挙動を細かく制御できる。
- bacpypes3 は **asyncio** ベース → ランタイム全体（シミュレーション値生成ループ、南向き binding アダプタ）が asyncio と統合する必要がある（次の設計判断へ波及）。
- 純 Python のため ARM ビルドは容易な見込みだが、MVP-1 で Raspberry Pi 上の実動作を確認する（[[ADR-008]] / EP-001 受入）。
