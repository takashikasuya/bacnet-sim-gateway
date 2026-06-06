# EP-005: Semantic Tags (MVP-2)

**Status:** Draft  **Priority:** P2  **MVP:** 2

## Goal

各 BACnet オブジェクトに意味付け（`tags` プロパティ）を載せ、連携先での意味的相互運用の足場を作る。本格オントロジ出力（EP-006）の前段。

## Acceptance Criteria（対応 AC / 要求）

- [ ] `tags` プロパティを設け ReadProperty/RPM で取得可能（PR-F-016）
- [ ] **device_type/point_type の Brick クラスから決定的に生成**（Brick→Haystack seed 写像）（AC-14 / PR-F-017 / [[ADR-012]]）
- [ ] SBCO `tags` 列は `metadata.search_tags` に verbatim 保持（検索タグ・別概念）
- [ ] 語彙 = BACnet 標準タグ ＋ Project Haystack（PR-F-018 / PR-NF-018）

## Specs / ADR

決定: [[ADR-006]]（語彙）, [[ADR-012]]（Brick 由来生成）。device_type→Brick 写像 seed が前提。将来の本格意味モデル出力（Brick/REC）は [[EP-006]]（PR-F-073, MVP-3）。
