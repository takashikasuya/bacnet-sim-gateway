# EP-003: Simulation & Fault Injection (MVP-2)

**Status:** Draft  **Priority:** P1  **MVP:** 2

## Goal

正常系の値生成モードと異常系のフォールトインジェクションを提供し、実設備では困難な異常系の結合試験を再現可能にする（課題 P-2）。

## Acceptance Criteria（対応 AC / 要求）

- [ ] 値生成: Random Walk / Sinusoidal / Replay / Scenario（PR-F-030 / 要件 §11）
- [ ] Fault Injection: 通信断 / 値凍結 / 異常値 / OutOfService / Fault 状態（AC-11 / PR-F-031）
- [ ] REST でシナリオ変更（PR-F-050 / 要件 §17 `POST /simulation/scenario`）
- [ ] COV（SubscribeCOV / Confirmed・Unconfirmed Notification）（PR-F-028）
- [ ] WritePropertyMultiple（PR-F-025）

## Specs / ADR

仕様: 要件 §9（COV）,§11（simulation/fault）,§17（REST）。
