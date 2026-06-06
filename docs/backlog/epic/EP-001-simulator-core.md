# EP-001: Simulator Core (MVP-1)

**Status:** Draft  **Priority:** P0  **MVP:** 1

## Goal

SBCO ポイントリストから仮想 B-BC を生成し、BACnet/IP（北向き）で公開して YABE から探索・読み書きできる最小経路を成立させる。実設備なしで上流開発を開始可能にする。

## Acceptance Criteria（対応 AC / 要求）

- [ ] SBCO CSV → YAML 生成（AC-1 / PR-F-001,004）
- [ ] 必須列検証・`gateway_id`≠`bbc_id` 担保（PR-F-002,003）
- [ ] object type 自動推定＋BACnet 列優先（PR-F-005,006 / [[ADR-007]]）
- [ ] Device + Analog/Binary/Multi-state オブジェクトと必須プロパティ（PR-F-012〜014）
- [ ] Who-Is/I-Am、ReadProperty、ReadPropertyMultiple、WriteProperty（Writable のみ）（AC-2〜5 / PR-F-020〜023）
- [ ] Dynamic Device/Object Binding（PR-F-024）
- [ ] 同一サブネット探索（PR-F-040）
- [ ] CLI: generate-yaml / validate / run / whois / read-property / rpm / write-property / list-objects / validate-point-list（PR-F-060〜062）
- [ ] Docker `docker compose up` 起動・YABE 北向き接続確認（PR-NF-005 / AC-2）

## Specs / ADR

仕様: `../../specs/requirements-definition-v1.1.md` §5–10,§13–16。決定: [[ADR-001]][[ADR-002]][[ADR-003]][[ADR-004]][[ADR-007]]
