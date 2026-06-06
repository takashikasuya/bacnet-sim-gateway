# ADR-012: device_type は Brick クラスを採用し、BACnet セマンティックタグは Brick から導出する

- **Date:** 2026-06-07
- **Status:** Accepted
- **関連:** [[ADR-006]]（BACnet タグ語彙＝Haystack を改訂・補完）/ PR-F-016,017,073
- **原典:** SBCO `schema/building_model.shacl.ttl`（`brick:Equipment`/`brick:Point`、REC 併用、Haystack 参照 0）/ pointlist.md（device_type＝Equipment 拡張クラス）

## Context

「BACnet のセマンティックタグ」と「ビル OS が扱う意味モデル」は別物である。SBCO 原典オントロジを確認したところ、データモデル側は **Brick + RealEstateCore (REC) ベース**（`brick:Equipment` を device、`brick:Point` を point とし、`rec:` プロパティを併用。Haystack 参照は無い）。一方、BACnet 標準の `tags` プロパティは ASHRAE/Haystack 由来の語彙が自然（[[ADR-006]]）。

当初 [[ADR-006]] は BACnet `tags` を **SBCO `tags` 列から生成**する想定だったが、実データの `tags` 列は日本語の自由検索タグ（`温度&&会議室`）で、セマンティックタグの生成源には不適。

## Decision

1. **device_type / point_type は Brick クラスを採用**する（SBCO オントロジに準拠。device_type → `brick:Equipment` サブクラス、point_type → `brick:Point` サブクラス）。
2. **BACnet セマンティックタグ（`tags` プロパティ）は Brick クラスから決定的に導出**する（Brick→Haystack タグ写像）。SBCO の自由記述 `tags` 列は生成源にしない。
3. **SBCO `tags` 列はビル OS 検索タグ**として `metadata`（例 `metadata.search_tags`）に verbatim 保持する（BACnet セマンティックタグとは別概念）。
4. 語彙方針（[[ADR-006]]: BACnet 標準＋Haystack）は **BACnet 側で維持**。生成が Brick 由来のため出力タグは語彙整合的。
5. 将来の意味モデル出力（PR-F-073, MVP-3）は **Brick/REC**（SBCO オントロジ）を正とする。

## Consequences

- device_type/point_type → Brick クラス → Haystack タグ集合の **写像テーブル（seed）**が必要（MVP-2、`sbco-to-bacnet-mapping.md`）。❓ 初期マッピング範囲は要確定。
- BACnet タグはビル OS の Brick モデルと一貫した起点（Brick クラス）から導出されるため、両層の意味的整合が取りやすい。
- [[ADR-006]] の生成源（PR-F-017）を改訂（tags 列 → Brick 由来）。語彙ポリシーは不変。
- Brick→Haystack の対応は版差・粒度差があるため、写像は明示テーブルで管理（自動推測しない）。
