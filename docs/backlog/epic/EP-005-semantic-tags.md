# EP-005: Semantic Tags (MVP-2)

**Status:** Draft  **Priority:** P2  **MVP:** 2

## Goal

各 BACnet オブジェクトに意味付け（`tags` プロパティ）を載せ、連携先での意味的相互運用の足場を作る。本格オントロジ出力（EP-006）の前段。

## Acceptance Criteria（対応 AC / 要求）

- [ ] `tags` プロパティを設け ReadProperty/RPM で取得可能（PR-F-016）
- [ ] SBCO `tags` 列から決定的に生成（AC-14 / PR-F-017）
- [ ] 語彙 = BACnet 標準タグ ＋ Project Haystack 既定、未知タグは検証で警告し保持（PR-F-018 / PR-NF-018）

## Specs / ADR

決定: [[ADR-006]]。将来の本格意味モデル出力は [[EP-006]]（PR-F-073, MVP-3）。
