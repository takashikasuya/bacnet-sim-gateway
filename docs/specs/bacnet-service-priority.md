# BACnet サービス実装優先度一覧（素案 v0.1）

> 出典: 要件定義書 §9, §12。関連: `pics-bibbs.md`（BIBB 対応）, `sbco-to-bacnet-mapping.md`（オブジェクトモデル）。
> ステータス記号: ✅ 確定 / 🔧 暫定 / ❓ 未決。状態: ☐未着手 ◑実装中 ☑完了。

| 項目 | 内容 |
|------|------|
| 目的 | BACnet サービスの実装順序・優先度・状態を一元管理する |
| 関連要求 | PR-F-020〜028, PR-F-040, PR-F-041 |
| 原典 | 要件定義書 §9, §12 |

## 1. 優先度一覧 ✅

凡例: 優先度 M/S/W（PRD MoSCoW）／状態 ☐未着手 ◑実装中 ☑完了。

| # | サービス | 役割 | BIBB | 優先度 | MVP | 状態 |
|---|----------|------|------|:---:|:---:|:---:|
| 1 | I-Am（Who-Is 応答） | Discovery 応答 | DM-DDB-B | M | 1 | ☐ |
| 2 | ReadProperty | 単一プロパティ読取 | DS-RP-B | M | 1 | ☐ |
| 3 | ReadPropertyMultiple | 複数読取 | DS-RPM-B | M | 1 | ☐ |
| 4 | WriteProperty | 書込（Writable のみ） | DS-WP-B | M | 1 | ☐ |
| 5 | Dynamic Device Binding | 動的デバイス束縛 | DM-DDB-B | M | 1 | ☐ |
| 6 | Dynamic Object Binding | 動的オブジェクト束縛 | DM-DOB-B | M | 1 | ☐ |
| 7 | BBMD / Foreign Device | サブネット越え探索 | （DL） | S | 2 | ☐ |
| 8 | WritePropertyMultiple | 複数書込 | DS-WPM-B | S | 2 | ☐ |
| 9 | I-Have（Who-Has 応答） | オブジェクト探索応答 | DM-DOB-B | S | 2 | ☐ |
| 10 | SubscribeCOV | COV 購読 | DS-COV-B | S | 2 | ☐ |
| 11 | ConfirmedCOVNotification | COV 通知（確認） | DS-COV-B | S | 2 | ☐ |
| 12 | UnconfirmedCOVNotification | COV 通知（非確認） | DS-COVU-B | S | 2 | ☐ |
| 13 | DeviceCommunicationControl | 通信制御 | DM-DCC-B | S | 2 | ☐ |
| 14 | ReinitializeDevice | 再初期化 | DM-RD-B | S | 2 | ☐ |
| 15 | TimeSynchronization | 時刻同期 | DM-TS-B | S | 2 | ☐ |
| 16 | Schedule 系 | スケジュール | SCHED-I-B | W | 3 | ☐ |
| 17 | TrendLog 系 | トレンド | T-VMT-I-B/T-ATR-B | W | 3 | ☐ |
| 18 | Alarm/Event 系 | 警報・イベント | AE-* | W | 3 | ☐ |

## 2. 依存関係 ✅
- #2/#3/#4 は #1 と Device/Object モデル（`sbco-to-bacnet-mapping.md`）に依存。
- #7 は #1 のブロードキャスト挙動に依存。
- #10〜#12（COV）は presentValue/statusFlags 更新経路（南向き telemetry / simulation）に依存。
- #13/#14 は実行時状態（通信有効/再初期化）の管理を要する。

## 3. 実装順序（推奨）✅
```
[MVP-1]  #1 → #5/#6 → #2 → #3 → #4
[MVP-2]  #7 → #9 → #8 → #10/#11/#12 → #13/#14/#15
[MVP-3]  #16 → #17 → #18
```

## 4. 受け入れ対応（PRD §10）✅
| サービス | 受入 |
|----------|------|
| #1 | AC-2 |
| #2 | AC-3 |
| #3 | AC-4 |
| #4 | AC-5（Writable のみ）, AC-9（command 連動） |
| #7 | AC-10 |

## 5. 実装時の確認事項（🔧）
- APDU サイズ / セグメンテーション（`pics-bibbs.md` §5 と整合）。
- エラー応答（BACnet-Error クラス/コード）の網羅。
- WriteProperty の priorityArray / relinquishDefault の扱い（Value 系, `sbco-to-bacnet-mapping.md` §5 ❓）。
- COV の増分しきい値（covIncrement）対応。

## 6. 未決事項（❓）
- COV の対象プロパティ範囲（presentValue/statusFlags 限定か拡張か）
- DeviceCommunicationControl のパスワード要否
- 時刻同期の UTC 版（DM-UTC-B）採否
