# ADR-006: セマンティックタグは BACnet `tags` ＋ Project Haystack を既定とする

- **Date:** 2026-06-06
- **Status:** Accepted（PRD v1.3 で追加）
- **原典:** PRD v1.3 変更履歴, PR-F-016〜018, PR-NF-018

## Context

連携先（Building OS）での意味的相互運用のため、各点に意味付け（タグ）が要る。本格的なオントロジ出力（Brick / REC / QUDT / ASHRAE 223P / JSON-LD）は重く、MVP-3 の将来機能（PR-F-073）である。一方で、BACnet には 135-2016 以降 `tags` プロパティ（name＋任意 value のタグ集合）があり、軽量に意味付けを北向きへ載せられる。

## Decision

- 各 BACnet オブジェクトに **`tags` プロパティ** を設け、ReadProperty/RPM で取得可能にする。
- `tags` は SBCO `tags` 列から **決定的に** 生成する。
- タグ語彙は **BACnet 標準タグ ＋ Project Haystack** を既定とし、将来 ASHRAE 223P へ連携する。
- 未知タグは検証で警告し、独自タグとして保持する。

## Consequences

- 意味付けの近接実装を MVP-2 で BACnet ネイティブに実現し、本格オントロジ出力（PR-F-073, MVP-3）を上に重ねる段階構成になる。
- タグ語彙の一貫適用が相互運用性に直結（PR-NF-018）。
- 関連: 将来 [[improve-codebase-architecture]] 的な意味モデル拡張。
