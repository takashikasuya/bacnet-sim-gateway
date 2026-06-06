# EP-006: Standards Artifacts & BACnet/SC (MVP-3)

**Status:** Future  **Priority:** P3  **MVP:** 3

## Goal

将来規格・成果物出力に対応し、BTL 適合支援と意味モデル出力まで拡張する。アーキテクチャは初期から後付け可能に設計しておく（PR-NF-010）。

## Acceptance Criteria（対応 AC / 要求）

- [ ] BACnet/SC 対応（PR-F-071）
- [ ] PICS / EDE / IEIEJ CSV 出力（PR-F-072）
- [ ] 将来オブジェクト: Schedule / Trend Log / Notification Class / Calendar / Accumulator（PR-F-070）
- [ ] 意味モデル出力: REC / Brick / QUDT / WoT TD 意味付け / JSON-LD（PR-F-073）
- [ ] WoT 南向きバインディング（PR-F-086 / AC-13）
- [ ] BTL 適合支援

## 実装状況（MVP-3 段階）

| AC | 状態 | 備考 |
|----|------|------|
| PICS / EDE / IEIEJ CSV 出力（PR-F-072） | ✅ 実装 | `bbc-sim export -f pics\|ede\|ieiej` |
| 意味モデル出力 REC/Brick/QUDT/WoT TD/JSON-LD（PR-F-073） | 🔧 一部 | Brick JSON-LD・WoT TD 実装。REC/QUDT は将来 |
| 将来オブジェクト Schedule/TrendLog/NotificationClass/Calendar/Accumulator（PR-F-070） | ⏳ 将来 | object-model 拡張が必要 |
| WoT 南向きバインディング（PR-F-086） | ⏳ 将来 | Transport 抽象（[[ADR-013]]）に WoT を追加して実装可能 |
| BACnet/SC（PR-F-071）・BTL 適合支援 | ⏳ 将来 | bacpypes3 の SC 対応・適合試験が前提 |

> ✅=実装済 / 🔧=一部 / ⏳=将来。export は `src/bbc_sim/export/artifacts.py`。

## Specs / ADR

仕様: 要件 §19。タグの段階構成: [[ADR-006]]（MVP-2 の `tags` の上に重ねる）。意味モデルの Brick 写像: [[ADR-012]]。
